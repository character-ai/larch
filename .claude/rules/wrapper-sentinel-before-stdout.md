---
paths:
  - skills/*/scripts/*review*.sh
  - skills/*/scripts/*step*.sh
  - python/larch/design/design_lifecycle.py
  - python/larch/design/design_terminal.py
  - python/larch/design/design_core.py
---
# Wrapper Sentinel Ordering

A background wrapper must write its terminal sentinel and remove `.bg-wait-active` before its final stdout flush. The harness fires `<task-notification>` on stdout activity, not process exit, so any stdout emitted before the sentinel exists creates a window where the orchestrator probes and finds nothing (#5418, #6080). When replacing an EXIT trap mid-script, the replacement must retain marker removal and sentinel writing; a sentinel-only replacement trap caused a permanent hook-denial loop (#6268).
