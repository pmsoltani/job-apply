from datetime import UTC, datetime


_registry: dict[str, dict[str, str]] = {}


def register(task_id: str, description: str) -> None:
    if task_id in _registry:
        _registry[task_id]["description"] = description
    else:
        _registry[task_id] = {
            "description": description,
            "started_at": datetime.now(UTC).isoformat(),
        }


def unregister(task_id: str) -> None:
    _registry.pop(task_id, None)


def snapshot() -> dict[str, dict[str, str]]:
    return dict(_registry)
