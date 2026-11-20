from queue import Empty, Full, Queue
from threading import Lock


_subscribers: set[Queue[None]] = set()
_lock = Lock()


def subscribe_campus_events() -> Queue[None]:
    subscriber: Queue[None] = Queue(maxsize=1)
    with _lock:
        _subscribers.add(subscriber)
    return subscriber


def unsubscribe_campus_events(subscriber: Queue[None]) -> None:
    with _lock:
        _subscribers.discard(subscriber)


def publish_campus_refresh() -> None:
    with _lock:
        for subscriber in tuple(_subscribers):
            if subscriber.full():
                try:
                    subscriber.get_nowait()
                except Empty:
                    continue
            try:
                subscriber.put_nowait(None)
            except Full:
                pass
