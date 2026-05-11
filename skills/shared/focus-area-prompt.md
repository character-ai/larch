# Focus Area Prompt

Walk five focus areas - tag each finding with its focus area (one of `code-quality` / `risk-integration` / `correctness` / `architecture` / `security`): (1) Code Quality: bugs, logic, reuse, tests, backward compat, style. (2) Risk/Integration: breaking changes, side effects, thread safety, deployment risks, regressions, CI. (3) Correctness: logic errors, off-by-one, nil handling, type mismatches, races, error paths. (4) Architecture: separation of concerns, contract boundaries, invariants, semantic boundaries. (5) Security: injection, authn/authz, secret handling, crypto, deserialization, SSRF, path traversal, dependency CVEs.

Do NOT modify files.

## Update Triggers

Update this file when review focus-area names, tag literals, or canonical reviewer rubric wording changes. Keep `.github/workflows/ci.yaml` `BACKTICKED_FILES` in sync so the focus-area enum remains mechanically checked.
