/*
 * Снимок локальной базы WhatsApp Desktop и её медиа в каталог, который контейнер бота
 * монтирует только на чтение. Запускается launchd-агентом раз в 2 минуты.
 *
 * Отдельный исполняемый файл, а не скрипт: «Полный доступ к диску» выдаётся ровно ему,
 * а не /bin/sh или интерпретатору. rsync запускается дочерним процессом и наследует доступ.
 *
 * Ход:
 *   1. База открывается только на чтение; нет доступа — ошибка в лог, снимок не трогается.
 *   2. Изменились ChatStorage.sqlite или -wal (mtime, размер) — копия через SQLite backup API
 *      во временный файл, журнал delete, quick_check, атомарная подмена rename.
 *   3. rsync Message/Media/ без превью *.thumb, *.mmsthumb и аватаров Profile/; пустые каталоги
 *      (в которых были одни превью) не переносятся.
 *   4. Метка snapshot_at — время, на которое снимок сверен с источником.
 *
 * Аргумент (необязательный) — каталог снимка; по умолчанию ~/docker/personal_assistant/whatsapp.
 */
#include <errno.h>
#include <fcntl.h>
#include <spawn.h>
#include <sqlite3.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define WATCHDOG_SECONDS 100
#define SOURCE_RELATIVE "Library/Group Containers/group.net.whatsapp.WhatsApp.shared"
#define DEFAULT_DEST_RELATIVE "docker/personal_assistant/whatsapp"
#define DB_NAME "ChatStorage.sqlite"
#define RSYNC_PATH "/usr/bin/rsync"

extern char **environ;

static void log_line(const char *level, const char *format, ...) {
    char stamp[32];
    time_t now = time(NULL);
    struct tm utc;
    gmtime_r(&now, &utc);
    strftime(stamp, sizeof stamp, "%Y-%m-%dT%H:%M:%SZ", &utc);
    fprintf(stderr, "%s whatsapp_snapshot %s: ", stamp, level);
    va_list args;
    va_start(args, format);
    vfprintf(stderr, format, args);
    va_end(args);
    fputc('\n', stderr);
}

static void join(char *out, size_t size, const char *left, const char *right) {
    if ((size_t)snprintf(out, size, "%s/%s", left, right) >= size) {
        log_line("error", "слишком длинный путь: %s/%s", left, right);
        exit(1);
    }
}

static int mkdir_p(const char *path) {
    char buffer[4096];
    if (strlen(path) >= sizeof buffer) {
        return -1;
    }
    strcpy(buffer, path);
    for (char *cursor = buffer + 1; *cursor; cursor++) {
        if (*cursor == '/') {
            *cursor = '\0';
            if (mkdir(buffer, 0755) != 0 && errno != EEXIST) {
                return -1;
            }
            *cursor = '/';
        }
    }
    if (mkdir(buffer, 0755) != 0 && errno != EEXIST) {
        return -1;
    }
    return 0;
}

static int fsync_path(const char *path) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        return -1;
    }
    int result = fsync(fd);
    close(fd);
    return result;
}

static int write_atomically(const char *dir, const char *name, const char *content) {
    char target[4096];
    char temporary[4096];
    join(target, sizeof target, dir, name);
    if ((size_t)snprintf(temporary, sizeof temporary, "%s/.%s.tmp", dir, name) >= sizeof temporary) {
        return -1;
    }
    FILE *file = fopen(temporary, "w");
    if (file == NULL) {
        return -1;
    }
    int failed = fputs(content, file) < 0;
    failed |= fflush(file) != 0;
    failed |= fsync(fileno(file)) != 0;
    failed |= fclose(file) != 0;
    if (failed || chmod(temporary, 0644) != 0 || rename(temporary, target) != 0) {
        unlink(temporary);
        return -1;
    }
    return 0;
}

static void source_stamp(const char *db_path, char *out, size_t size) {
    char wal_path[4096];
    struct stat db_stat;
    struct stat wal_stat;
    snprintf(wal_path, sizeof wal_path, "%s-wal", db_path);
    memset(&db_stat, 0, sizeof db_stat);
    memset(&wal_stat, 0, sizeof wal_stat);
    stat(db_path, &db_stat);
    stat(wal_path, &wal_stat);
    snprintf(out, size, "db %lld.%09ld %lld wal %lld.%09ld %lld\n",
             (long long)db_stat.st_mtimespec.tv_sec, db_stat.st_mtimespec.tv_nsec,
             (long long)db_stat.st_size,
             (long long)wal_stat.st_mtimespec.tv_sec, wal_stat.st_mtimespec.tv_nsec,
             (long long)wal_stat.st_size);
}

static int stamp_unchanged(const char *dest, const char *stamp) {
    char stamp_path[4096];
    char db_copy[4096];
    char saved[256] = {0};
    join(stamp_path, sizeof stamp_path, dest, ".source_stamp");
    join(db_copy, sizeof db_copy, dest, DB_NAME);
    if (access(db_copy, F_OK) != 0) {
        return 0;
    }
    FILE *file = fopen(stamp_path, "r");
    if (file == NULL) {
        return 0;
    }
    size_t length = fread(saved, 1, sizeof saved - 1, file);
    fclose(file);
    saved[length] = '\0';
    return strcmp(saved, stamp) == 0;
}

static int single_text_equals(sqlite3 *db, const char *sql, const char *expected) {
    sqlite3_stmt *statement = NULL;
    int matches = 0;
    if (sqlite3_prepare_v2(db, sql, -1, &statement, NULL) == SQLITE_OK &&
        sqlite3_step(statement) == SQLITE_ROW) {
        const unsigned char *value = sqlite3_column_text(statement, 0);
        matches = value != NULL && strcmp((const char *)value, expected) == 0;
    }
    sqlite3_finalize(statement);
    return matches;
}

static int copy_database(sqlite3 *source, const char *dest) {
    char temporary[4096];
    char temporary_journal[4096];
    char temporary_wal[4096];
    char temporary_shm[4096];
    char target[4096];
    join(temporary, sizeof temporary, dest, "." DB_NAME ".tmp");
    join(temporary_journal, sizeof temporary_journal, dest, "." DB_NAME ".tmp-journal");
    join(temporary_wal, sizeof temporary_wal, dest, "." DB_NAME ".tmp-wal");
    join(temporary_shm, sizeof temporary_shm, dest, "." DB_NAME ".tmp-shm");
    join(target, sizeof target, dest, DB_NAME);
    unlink(temporary);
    unlink(temporary_journal);
    unlink(temporary_wal);
    unlink(temporary_shm);

    sqlite3 *copy = NULL;
    if (sqlite3_open_v2(temporary, &copy, SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE, NULL) != SQLITE_OK) {
        log_line("error", "не открыть временную копию %s: %s", temporary, sqlite3_errmsg(copy));
        sqlite3_close(copy);
        return -1;
    }
    sqlite3_backup *backup = sqlite3_backup_init(copy, "main", source, "main");
    if (backup == NULL) {
        log_line("error", "backup_init: %s", sqlite3_errmsg(copy));
        sqlite3_close(copy);
        unlink(temporary);
        return -1;
    }
    int step = sqlite3_backup_step(backup, -1);
    sqlite3_backup_finish(backup);
    if (step != SQLITE_DONE) {
        log_line("error", "backup_step: %s", sqlite3_errstr(step));
        sqlite3_close(copy);
        unlink(temporary);
        return -1;
    }
    int ok = single_text_equals(copy, "PRAGMA journal_mode=DELETE", "delete");
    if (!ok) {
        log_line("error", "копия не перешла в journal_mode=delete");
    } else if (!(ok = single_text_equals(copy, "PRAGMA quick_check", "ok"))) {
        log_line("error", "quick_check копии не ok");
    }
    sqlite3_close(copy);
    unlink(temporary_wal);
    unlink(temporary_shm);
    if (!ok || chmod(temporary, 0644) != 0 || fsync_path(temporary) != 0 || rename(temporary, target) != 0) {
        if (ok) {
            log_line("error", "подмена снимка %s: %s", target, strerror(errno));
        }
        unlink(temporary);
        unlink(temporary_journal);
        return -1;
    }
    fsync_path(dest);
    return 0;
}

static int sync_media(const char *source_root, const char *dest) {
    char source_media[4096];
    char dest_media[4096];
    char dest_message[4096];
    struct stat media_stat;
    join(source_media, sizeof source_media, source_root, "Message/Media/");
    join(dest_message, sizeof dest_message, dest, "Message");
    join(dest_media, sizeof dest_media, dest, "Message/Media/");
    if (stat(source_media, &media_stat) != 0) {
        return 0;
    }
    if (mkdir_p(dest_message) != 0) {
        log_line("error", "не создать %s: %s", dest_message, strerror(errno));
        return -1;
    }
    char *arguments[] = {
        RSYNC_PATH, "-rlt", "--delete", "--prune-empty-dirs",
        "--exclude", "*.thumb", "--exclude", "*.mmsthumb", "--exclude", "/Profile/",
        source_media, dest_media, NULL,
    };
    pid_t child;
    int spawn_error = posix_spawn(&child, RSYNC_PATH, NULL, NULL, arguments, environ);
    if (spawn_error != 0) {
        log_line("error", "не запустить rsync: %s", strerror(spawn_error));
        return -1;
    }
    int status = 0;
    while (waitpid(child, &status, 0) < 0) {
        if (errno != EINTR) {
            log_line("error", "waitpid rsync: %s", strerror(errno));
            return -1;
        }
    }
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
        log_line("error", "rsync медиа завершился с кодом %d", WIFEXITED(status) ? WEXITSTATUS(status) : -1);
        return -1;
    }
    return 0;
}

int main(int argc, char **argv) {
    alarm(WATCHDOG_SECONDS);
    umask(022);

    const char *home = getenv("HOME");
    if (home == NULL || *home == '\0') {
        log_line("error", "не задан HOME");
        return 1;
    }
    char source_root[4096];
    char source_db[4096];
    char default_dest[4096];
    join(source_root, sizeof source_root, home, SOURCE_RELATIVE);
    join(source_db, sizeof source_db, source_root, DB_NAME);
    join(default_dest, sizeof default_dest, home, DEFAULT_DEST_RELATIVE);
    const char *dest = argc > 1 ? argv[1] : default_dest;

    if (mkdir_p(dest) != 0) {
        log_line("error", "не создать каталог снимка %s: %s", dest, strerror(errno));
        return 1;
    }

    char stamp[256];
    source_stamp(source_db, stamp, sizeof stamp);

    sqlite3 *source = NULL;
    if (sqlite3_open_v2(source_db, &source, SQLITE_OPEN_READONLY, NULL) != SQLITE_OK ||
        sqlite3_exec(source, "SELECT count(*) FROM sqlite_master", NULL, NULL, NULL) != SQLITE_OK) {
        log_line("error", "нет доступа к базе WhatsApp %s: %s (нужен «Полный доступ к диску» для %s)",
                 source_db, sqlite3_errmsg(source), argv[0]);
        sqlite3_close(source);
        return 1;
    }

    int failed = 0;
    if (!stamp_unchanged(dest, stamp)) {
        struct timespec started;
        struct timespec finished;
        clock_gettime(CLOCK_MONOTONIC, &started);
        if (copy_database(source, dest) != 0) {
            failed = 1;
        } else {
            clock_gettime(CLOCK_MONOTONIC, &finished);
            char stamp_name[] = ".source_stamp";
            if (write_atomically(dest, stamp_name, stamp) != 0) {
                log_line("error", "не записать %s: %s", stamp_name, strerror(errno));
                failed = 1;
            }
            double seconds = (double)(finished.tv_sec - started.tv_sec) +
                             (double)(finished.tv_nsec - started.tv_nsec) / 1e9;
            log_line("info", "база скопирована за %.2f с", seconds);
        }
    }
    sqlite3_close(source);
    if (failed) {
        return 1;
    }

    if (sync_media(source_root, dest) != 0) {
        return 1;
    }

    char snapshot_at[64];
    time_t now = time(NULL);
    struct tm utc;
    gmtime_r(&now, &utc);
    strftime(snapshot_at, sizeof snapshot_at, "%Y-%m-%dT%H:%M:%SZ\n", &utc);
    if (write_atomically(dest, "snapshot_at", snapshot_at) != 0) {
        log_line("error", "не записать метку snapshot_at: %s", strerror(errno));
        return 1;
    }
    return 0;
}
