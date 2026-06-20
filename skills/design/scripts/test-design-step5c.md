# test-design-step5c.sh

## Purpose

Offline smoke harness for the `design-step5c.sh` thin wrapper.

## Primary coverage

- Confirms the wrapper delegates to `python/cli.py design step5c`.
- Confirms wrapper argv passthrough is preserved.
- Confirms non-zero Python entrypoint exits propagate through the wrapper.

## Edit-in-sync rules

Update this harness when `design-step5c.sh` changes its delegation target or accepted wrapper argv contract. Step 5c orchestration behavior is covered in `python/test_design_lifecycle.py`.
