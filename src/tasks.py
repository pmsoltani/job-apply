from datetime import datetime, timezone


_registry: dict[str, dict] = {}


def register(task_id: str, description: str) -> None:
    if task_id in _registry:
        _registry[task_id]["description"] = description
    else:
        _registry[task_id] = {
            "description": description,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }


def unregister(task_id: str) -> None:
    _registry.pop(task_id, None)


def snapshot() -> dict[str, dict]:
    return dict(_registry)
