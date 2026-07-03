### Deviation: G-Py-1 (composite data as frozen dataclasses)
- The plan changes `_pin_and_load_guidelines_note`'s return type to a bare `tuple[str, bool]` (note text, warning_logged) instead of a frozen dataclass.
- Rationale: a two-element, locally-scoped return consumed at a single call site in `ship.py`. G-Py-1 carves out scalar returns and calls `frozen=True` adoption "aspirational today" in this repo. Left as implementer judgment rather than mandated, to keep the diff minimal for a narrowly-scoped bug fix.
