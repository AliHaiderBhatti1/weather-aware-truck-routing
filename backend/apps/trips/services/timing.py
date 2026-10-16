"""Tiny stage timer that renders as a ``Server-Timing`` header for DevTools."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager


class StageTimer:
    def __init__(self) -> None:
        self.stages: list[tuple[str, float]] = []
        self._started = time.perf_counter()

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            self.stages.append((name, (time.perf_counter() - start) * 1000))

    @property
    def total_ms(self) -> float:
        return (time.perf_counter() - self._started) * 1000

    def header(self) -> str:
        parts = [f"{name};dur={ms:.0f}" for name, ms in self.stages]
        parts.append(f"total;dur={self.total_ms:.0f}")
        return ", ".join(parts)

    def summary(self) -> str:
        return " ".join(f"{name}={ms:.0f}ms" for name, ms in self.stages)
