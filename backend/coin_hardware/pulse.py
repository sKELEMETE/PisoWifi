from __future__ import annotations

import threading
import time
from collections.abc import Callable


class PulseBurstGrouper:
    """Groups debounced GPIO edges into one coin pulse burst."""

    def __init__(
        self,
        callback: Callable[[int, object | None], None],
        debounce_ms: int,
        inter_pulse_gap_ms: int,
        context_factory: Callable[[], object | None] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.callback = callback
        self.debounce_seconds = debounce_ms / 1000
        self.gap_seconds = inter_pulse_gap_ms / 1000
        self.context_factory = context_factory or (lambda: None)
        self.clock = clock
        self._last_edge: float | None = None
        self._count = 0
        self._context: object | None = None
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def add_edge(self, timestamp: float | None = None) -> bool:
        now = self.clock() if timestamp is None else timestamp
        with self._lock:
            if self._last_edge is not None and now - self._last_edge < self.debounce_seconds:
                return False
            if self._count == 0:
                self._context = self.context_factory()
            self._last_edge = now
            self._count += 1
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self.gap_seconds, self.flush)
            self._timer.daemon = True
            self._timer.start()
            return True

    def flush(self) -> int:
        with self._lock:
            count = self._count
            context = self._context
            self._count = 0
            self._context = None
            self._last_edge = None
            self._timer = None
        if count:
            self.callback(count, context)
        return count

    def close(self) -> None:
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None


def map_pulse_count(pulse_count: int, mapping: dict[int, int]) -> int | None:
    return mapping.get(pulse_count)
