-- Файлы от рабочих агентов: в журнале только имя и размер, байты не хранятся

ALTER TABLE agent_notifications
    ADD COLUMN file_name TEXT,
    ADD COLUMN file_size BIGINT;
