### OOS_1: Module docstring still documents scan-only surface after Piece 2 (G-Py-6)
- **Description**: Module docstring still documents scan-only surface after Piece 2 (G-Py-6). Scenario: After baseline I/O lands, the top-level docstring will contradict run_rule write/check behavior and mislead later rule migrations
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/lint/engine.py:1-6
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: Plan names typed baseline rows but not frozen dataclass carriers (G-Py-1)
- **Description**: Plan names typed baseline rows but not frozen dataclass carriers (G-Py-1). Scenario: Projection helpers may use mutable dicts or TypedDict rows and drift from the engine's frozen Finding/SourceFile model
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/lint/engine.py
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_3: run_rule keyword option names are unspecified for downstream CLI wiring (G-Wire-1)
- **Description**: run_rule keyword option names are unspecified for downstream CLI wiring (G-Wire-1). Scenario: Piece 3 registration must guess parameter names for --write-baseline, --strict-stale, and initial reason, risking a second rename when CLI dispatch is added
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/lint/engine.py:472-477
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

