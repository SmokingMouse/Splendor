from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable


class TrainingRunner:
    def __init__(self, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="train-run")

    def submit(self, fn: Callable[[], None]) -> None:
        self._executor.submit(fn)


runner = TrainingRunner(max_workers=2)
