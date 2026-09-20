import asyncio
from collections import defaultdict
from typing import Callable, Any
from gapo.core.logging import get_logger

logger = get_logger("events")


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._running = False

    def subscribe(self, event_type: str, callback: Callable) -> None:
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed {callback.__name__} to {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    async def publish(self, event_type: str, data: Any = None) -> None:
        if event_type not in self._subscribers:
            return

        tasks = []
        for callback in self._subscribers[event_type]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(callback(data))
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Error in event handler {callback.__name__}: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def publish_sync(self, event_type: str, data: Any = None) -> None:
        if event_type not in self._subscribers:
            return

        for callback in self._subscribers[event_type]:
            try:
                if not asyncio.iscoroutinefunction(callback):
                    callback(data)
                else:
                    logger.warning(f"Sync publish called with async handler {callback.__name__}")
            except Exception as e:
                logger.error(f"Error in sync event handler {callback.__name__}: {e}")


event_bus = EventBus()


async def start_event_bus():
    logger.info("Event bus started")


async def stop_event_bus():
    logger.info("Event bus stopped")