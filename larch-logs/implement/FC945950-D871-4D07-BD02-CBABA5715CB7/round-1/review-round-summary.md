# Review Round 1

- Mode: `diff`
- 2 accepted, 3 rejected (2 neutral)

## Accepted Findings

### FINDING_1: `_has_violation` false negatives for multi-positional signatures
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_has_violation` treats any `*args` (`args.vararg`) or existing keyword-only parameters as compliant, instead of requiring a bare `*` separator. Functions with two or more non-`self`/`cls` positional parameters before the star (e.g. `def helper(a, b, *_):`, `def f(a, b, *, c)`, mixed `*args` shapes) pass lint without baseline records. Known examples such as `python/agents.py:446-454` (`classify_launch_failure` accepting `launcher_exit` and `sidecar` positionally) and `python/file_oos.py:675` / `716` are missing from `python/keyword-only-baseline.json`. New violations of this shape evade #5002 enforcement while `make py-lint-main` stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_3: External API and callback carve-outs not implemented
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Plan-required external-API and callback carve-outs are not implemented beyond dunder exclusion. Callback-shaped definitions are baselined warnings instead of excluded. Fixed-signature overrides such as `python/clarify.py:79-83` (`argparse.ArgumentParser.exit`) remain in `python/keyword-only-baseline.json` rather than being explicitly exempted. No pragma, allowlist metadata, or documented waiver path exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt: Address the concern above.


