from collections.abc import Callable
from functools import partial
from threading import Lock

from src.chat.albums.album_photo import AlbumPhoto
from src.chat.albums.protocols.i_cancellable_timer import ICancellableTimer
from src.chat.albums.protocols.i_timer_factory import ITimerFactory

AlbumKey = tuple[int, str]


# Telegram присылает альбом отдельными update с общим media_group_id: группа отдаётся
# целиком, когда после её последнего фото прошло quiet_seconds тишины
class AlbumBuffer:
    def __init__(
        self,
        timer_factory: ITimerFactory,
        quiet_seconds: float,
        on_album_ready: Callable[[int, list[AlbumPhoto]], None],
    ) -> None:
        self.timer_factory = timer_factory
        self.quiet_seconds = quiet_seconds
        self.on_album_ready = on_album_ready
        self._lock = Lock()
        self._photos: dict[AlbumKey, list[AlbumPhoto]] = {}
        self._timers: dict[AlbumKey, ICancellableTimer] = {}
        self._generations: dict[AlbumKey, int] = {}

    def add(self, chat_id: int, media_group_id: str, photo: AlbumPhoto) -> None:
        key = (chat_id, media_group_id)
        with self._lock:
            self._photos.setdefault(key, []).append(photo)
            previous_timer = self._timers.get(key)
            if previous_timer is not None:
                previous_timer.cancel()
            generation = self._generations.get(key, 0) + 1
            self._generations[key] = generation
            self._timers[key] = self.timer_factory.start(
                self.quiet_seconds, partial(self._release, key, generation)
            )

    def _release(self, key: AlbumKey, generation: int) -> None:
        with self._lock:
            if self._generations.get(key) != generation:
                return
            photos = self._photos.pop(key)
            del self._timers[key]
            del self._generations[key]
        chat_id, _media_group_id = key
        self.on_album_ready(chat_id, sorted(photos, key=lambda p: p.message_id))
