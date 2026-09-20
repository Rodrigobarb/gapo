import asyncio
import functools
from typing import Any, Callable, ParamSpec, TypeVar
from collections import deque
import time

P = ParamSpec("P")
T = TypeVar("T")


def throttle(calls_per_second: float):
    min_interval = 1.0 / calls_per_second
    last_call = 0.0

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            nonlocal last_call
            elapsed = time.monotonic() - last_call
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            last_call = time.monotonic()
            return func(*args, **kwargs)
        return wrapper
    return decorator


async def async_throttle(calls_per_second: float):
    min_interval = 1.0 / calls_per_second
    last_call = 0.0

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            nonlocal last_call
            elapsed = time.monotonic() - last_call
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
            last_call = time.monotonic()
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def debounce(wait_seconds: float):
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        timer: asyncio.Task | None = None

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            nonlocal timer
            if timer and not timer.done():
                timer.cancel()
            
            async def delayed():
                await asyncio.sleep(wait_seconds)
                return await func(*args, **kwargs)
            
            timer = asyncio.create_task(delayed())
            return await timer
        return wrapper
    return decorator


class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: float):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls: deque[float] = deque()

    async def acquire(self) -> None:
        now = time.monotonic()
        while self.calls and now - self.calls[0] > self.window_seconds:
            self.calls.popleft()
        
        if len(self.calls) >= self.max_calls:
            oldest = self.calls[0]
            wait_time = self.window_seconds - (now - oldest)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            return await self.acquire()
        
        self.calls.append(now)

    def acquire_sync(self) -> None:
        now = time.monotonic()
        while self.calls and now - self.calls[0] > self.window_seconds:
            self.calls.popleft()
        
        if len(self.calls) >= self.max_calls:
            oldest = self.calls[0]
            wait_time = self.window_seconds - (now - oldest)
            if wait_time > 0:
                time.sleep(wait_time)
            return self.acquire_sync()
        
        self.calls.append(now)


class AsyncCache:
    def __init__(self, ttl_seconds: float = 300, max_size: int = 1000):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._cache: dict[str, tuple[Any, float]] = {}

    async def get(self, key: str) -> Any | None:
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.monotonic() - timestamp < self.ttl:
                return value
            else:
                del self._cache[key]
        return None

    async def set(self, key: str, value: Any) -> None:
        if len(self._cache) >= self.max_size:
            oldest = min(self._cache.items(), key=lambda x: x[1][1])
            del self._cache[oldest[0]]
        self._cache[key] = (value, time.monotonic())

    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    async def clear(self) -> None:
        self._cache.clear()