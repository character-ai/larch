"""Build auditable labels for literal specialized-structure assertions."""
from __future__ import annotations

import ast
from pathlib import Path


_LABEL_ARGUMENT = {
    "require": 2,
    "require_text": 2,
    "forbid": 2,
    "require_near": 3,
}


def assertion_labels(path: str | Path) -> frozenset[str]:
    """Return every literal assertion label declared by a specialized port."""
    source_path = Path(path)
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    labels: set[str] = set()
    for call in ast.walk(tree):
        if not isinstance(call, ast.Call):
            continue
        if isinstance(call.func, ast.Name):
            index = _LABEL_ARGUMENT.get(call.func.id)
            if index is not None and len(call.args) > index:
                argument = call.args[index]
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    labels.add(argument.value)
            continue
        if (
            isinstance(call.func, ast.Attribute)
            and call.func.attr == "append"
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
        ):
            labels.add(call.args[0].value)
    return frozenset(labels)
