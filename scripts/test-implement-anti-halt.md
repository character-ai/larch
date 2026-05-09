# scripts/test-implement-anti-halt.sh — contract

`scripts/test-implement-anti-halt.sh` is a freestanding regression harness that asserts `/implement` retains the halt-prone step-boundary continuation literals for Step 2→3, Step 4→5, Step 7a→8, Step 12→14, and the Step 14→18 wind-down sequence. It also pins the shared `skills/shared/subskill-invocation.md` "Step-boundary anti-halt" section as the single source of truth for the canonical blockquote form.

The harness is wired into `make lint` via the `test-implement-anti-halt` Makefile target. When adding, renaming, or removing a halt-prone `/implement` boundary, update this harness and the corresponding SKILL.md boundary reminder in the same PR.
