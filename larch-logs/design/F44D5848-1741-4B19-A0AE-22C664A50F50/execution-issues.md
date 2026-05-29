### Warnings

- **Step design Step 3 (env recovery) — plan-review-loop.sh / write-design-current-env.sh failed (exit 1)**:
  ```
plan-review-loop.sh exited rc=1 at line 83 (--codex-present "${2:?}"): CODEX_PRESENT/CURSOR_PRESENT empty.
Cause: write-design-current-env.sh regenerates source-env.sh from scratch and only emits presence/availability keys when their flags are passed; the Step 0b sub-step 6 and Step 0b 5.5-bis refreshes omit them, so source-env.sh lost CODEX_PRESENT/CURSOR_PRESENT/CODEX_AVAILABLE/CURSOR_AVAILABLE; Step 3 driver sources that file and passes empty --codex-present.
Recovery: re-ran write-design-current-env.sh with all four presence/availability flags; reset review-round-count.txt to 0; re-ran the Step 3 panel.
Tangential to issue #3190 (Gate B passive-summary prompt removal).
  ```
