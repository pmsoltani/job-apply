import logging
from collections.abc import Iterator
from contextlib import contextmanager

from src.configs import c
from src.logger import task_id_var
from src.schemas import TaskStatus


lg = logging.getLogger(c.APP_NAME)

_registry: dict[str, TaskStatus] = {}


def register(task_id: str, description: str) -> None:
    """Register a task, tag the logs with its id, and log its first status."""
    task_id_var.set(task_id)
    _registry[task_id] = TaskStatus(description=description)
    lg.info(description)


def update(description: str) -> None:
    """Set the current task's status, e.g. its progress, and log it."""
    task_id = task_id_var.get()
    if task_id and task_id in _registry:
        _registry[task_id].description = description
    lg.info(description)


def unregister(task_id: str) -> None:
    _registry.pop(task_id, None)
    task_id_var.set(None)


def snapshot() -> dict[str, TaskStatus]:
    return dict(_registry)


@contextmanager
def track(task_id: str, description: str) -> Iterator[None]:
    """Register a task for the block's duration and tag its logs with its id."""
    register(task_id, description)
    try:
        yield
    finally:
        unregister(task_id)


@contextmanager
def background(task_id: str, description: str) -> Iterator[None]:
    """Register a task to run in the background."""
    with track(task_id, description):
        try:
            yield
        except Exception:  # noqa: BLE001 - background-task boundary, traceback is logged
            lg.exception("Task failed.")
