import asyncio
import threading
from collections.abc import Coroutine
from concurrent.futures import wait
from typing import Any

from src.telegram_user.errors.telegram_timeout_error import TelegramTimeoutError


class EventLoopThread:
    def __init__(self, name: str, timeout_seconds: float) -> None:
        self._name = name
        self._timeout_seconds = timeout_seconds
        self._loop: asyncio.AbstractEventLoop | None = None
        self._starting = threading.Lock()

    # Инструменты модели вызываются синхронно изнутри event loop ClaudeSdkProvider:
    # asyncio.run там падает, поэтому Telethon живёт в своём цикле в отдельном потоке.
    def run[T](self, coroutine: Coroutine[Any, Any, T]) -> T:
        future = asyncio.run_coroutine_threadsafe(coroutine, self._running_loop())
        done, _ = wait([future], timeout=self._timeout_seconds)
        if not done:
            future.cancel()
            raise TelegramTimeoutError(self._timeout_seconds)
        return future.result()

    def _running_loop(self) -> asyncio.AbstractEventLoop:
        with self._starting:
            if self._loop is None:
                loop = asyncio.new_event_loop()
                threading.Thread(
                    target=loop.run_forever, name=self._name, daemon=True
                ).start()
                self._loop = loop
            return self._loop
