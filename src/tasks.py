from datetime import UTC, datetime

from src.logger import task_id_var


_registry: dict[str, dict[str, str]] = {}


def register(task_id: str, description: str) -> None:
    """Register a task, or update its description, and tag the logs with its id."""
    task_id_var.set(task_id)
    if task_id in _registry:
        _registry[task_id]["description"] = description
    else:
        _registry[task_id] = {
            "description": description,
            "started_at": datetime.now(UTC).isoformat(),
        }


def unregister(task_id: str) -> None:
    _registry.pop(task_id, None)
    task_id_var.set(None)


def snapshot() -> dict[str, dict[str, str]]:
    return dict(_registry)
