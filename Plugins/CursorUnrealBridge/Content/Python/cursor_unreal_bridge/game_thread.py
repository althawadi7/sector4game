"""Run callables safely on the Unreal Editor / game thread."""

from __future__ import annotations

import queue
import threading
import traceback
import uuid
from typing import Any, Callable

import unreal

_job_queue: queue.Queue = queue.Queue()
_tick_handle = None
_lock = threading.Lock()
_tls = threading.local()


class _Job:
    def __init__(self, fn: Callable[[], Any]):
        self.fn = fn
        self.event = threading.Event()
        self.result: Any = None
        self.error: str | None = None
        self.job_id = uuid.uuid4().hex


def _process_queue(_delta_time: float) -> None:
    # Nested calls inside a queued job must run immediately.
    _tls.on_game_thread = True
    try:
        while True:
            try:
                job: _Job = _job_queue.get_nowait()
            except queue.Empty:
                break
            try:
                job.result = job.fn()
            except Exception:
                job.error = traceback.format_exc()
            finally:
                job.event.set()
    finally:
        _tls.on_game_thread = False


def ensure_tick() -> None:
    global _tick_handle
    with _lock:
        if _tick_handle is None:
            _tick_handle = unreal.register_slate_post_tick_callback(_process_queue)


def mark_http_worker(is_worker: bool = True) -> None:
    """HTTP handler threads must set this so work is marshaled to the game thread."""
    _tls.is_http_worker = bool(is_worker)


def run_on_game_thread(fn: Callable[[], Any], timeout: float = 120.0) -> Any:
    """Run fn on the editor/game thread.

    - Already inside a queued job -> call immediately (re-entrant)
    - Called from Unreal Python console / init (not HTTP worker) -> call immediately
    - Called from HTTP worker thread -> queue + wait for slate tick
    """
    if getattr(_tls, "on_game_thread", False):
        return fn()

    # Unreal py / py.file / init scripts already run on the game thread.
    # Only HTTP worker threads need marshaling.
    if not getattr(_tls, "is_http_worker", False):
        return fn()

    ensure_tick()
    job = _Job(fn)
    _job_queue.put(job)
    if not job.event.wait(timeout=timeout):
        raise TimeoutError(f"Unreal game-thread job timed out after {timeout}s")
    if job.error:
        raise RuntimeError(job.error)
    return job.result
