### FINDING_1: Duplicated Step 0 routing-envelope parse blocks
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-parse-block-duplication-output.txt
- **Severity**: important
- **Concern**: Plan acceptance called for one shared bootstrap-routing.env parse path, but initial Step 0 and dirty-tree recovery each embed near-identical parse logic (~52 lines): `_inv_routing_keys`, helpers, symlink guard, file-first read, `_inv_apply_routing_line_if_empty` case arms, stdout fallback, and export. The copies are byte-identical except pre-parse `unset` asymmetry, but nothing prevents one-sided edits (symlink guard, empty-key handling, new keys) from diverging initial vs resume routing while tests that only pin the key string still pass. `_inv_apply_routing_line_if_empty` also duplicates the canonical key list as explicit case arms (four coordinated edit sites per new consumer). Factor to a shared script/block and/or structural pins asserting parity and absence of extra parse definitions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-parse-block-duplication-output.txt: Collapse to a single definition — e.g. extract `scripts/parse-bootstrap-routing-envelope.sh` (accepting stdout + optional `--preserve-coder` for resume) or one SKILL bash block both call sites reference — and add structural pins that fail if `_inv_apply_routing_line()` appears more than once or if the two `_inv_routing_keys` literals diverge.


### FINDING_12: Global `set +e` count pin is too weak
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-implement-structure.sh` global `set +e` count pin can be diluted by unrelated SKILL fences; removing `set +e` before one invoke call might not fail CI while Step 0 exit-2 propagation breaks. Remove global count pin or restrict grep to the step:0 region.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: Empty routing key can break `printf -v` allowlist
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: File-first parse uses `printf -v` with a substring allowlist; empty `_inv_key` makes pattern `*" "*` match any spaced list. Malformed `bootstrap-routing.env` lines can hit `printf -v` with an empty name and abort Step 0 instead of ignoring the line. Require non-empty strict identifier keys before `printf -v`; mirror in `implement-bootstrap-invoke.sh` `_inv_emit_routing_kv`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_16: SKILL should exit on non-2 wrapper rc before parse (symlink/rc=1 path)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 0 only handles wrapper exit 2; other non-zero rc (e.g. 1 after bootstrap success when `bootstrap-routing.env` is a symlink) falls through to envelope parse with empty stdout. Dirty-tree resume can clear `IMPLEMENT_TMPDIR` from empty `_inv_out`, skip file parse, and mis-route despite updated session-env. Add `if [ "$_inv_rc" -ne 0 ]; then exit "$_inv_rc"; fi` after the exit-2 check at both wrapper call sites before unset/parse; pin in `test-implement-structure.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_17: Resume vs initial `unset` coder asymmetry is undocumented and unpinned
- **Reviewer(s)**: dyn-parse-block-duplication-output.txt
- **Severity**: latent
- **Concern**: Initial Step 0 `unset` clears `coder`/`coder_fallback`; dirty-tree resume omits them to preserve implementer selection (`implement-bootstrap-invoke.md:51`). SKILL does not annotate this; blocks look copy-paste identical; structure test only greps for `bootstrap-routing.env`, not preserve semantics. A maintainer syncing blocks could add `coder` to resume `unset` and break dirty-tree continuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parse-block-duplication-output.txt: Either move the preserve-vs-clear policy into the extracted parse helper (flag-driven) or pin the asymmetry explicitly in `scripts/test-implement-structure.sh` (e.g. assert initial unset includes `coder coder_fallback`, resume unset excludes them) and add a one-line comment at `skills/implement/SKILL.md:414` pointing at the contract.


### FINDING_18: Structural harness overclaims “shared parse” without parity pins
- **Reviewer(s)**: dyn-parse-block-duplication-output.txt
- **Severity**: latent
- **Concern**: `test-implement-structure.sh` / `.md` prose implies a shared parse with stdout fallback, but the test only `grep -Fq 'bootstrap-routing.env'`. It does not assert identical `_inv_routing_keys` literals across fences, helper-body parity, duplicate `_inv_apply_routing_line` definitions, or resume `unset` asymmetry (partially mitigated elsewhere by key-list match only).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parse-block-duplication-output.txt: Extend `scripts/test-implement-structure.sh` with pins for exactly two wrapper call sites, two identical `_inv_routing_keys` strings, absent third `_inv_apply_routing_line()` definitions beyond the two expected blocks (or zero if extracted to a script), and the initial/resume `unset` asymmetry above.


### FINDING_19: `docs/linting.md` missing `test-implement-bootstrap-invoke` row
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Makefile wires `test-implement-bootstrap-invoke` into harness shards but `docs/linting.md` still documents only `test-implement-bootstrap`, hiding the new offline harness from contributors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_20: Structural pins omit inverted checks for removed `_ib_*` helpers
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `test-implement-structure.sh` does not pin absence of `_ib_kv_scan()` and `_ib_handle_bootstrap_exit2()` in SKILL.md though plan acceptance lists them as removed; partial reintroduction could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_5: Wrapper fails before stdout when `bootstrap-routing.env` is a symlink
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: On bootstrap success, if `bootstrap-routing.env` is a symlink or non-regular file, the wrapper can exit 1 before printing the stdout routing envelope. Bootstrap and session-env may succeed, but the orchestrator gets empty stdout, unsets routing keys, and mis-routes Step 0. Emit the filtered envelope on stdout whenever bootstrap succeeds; warn on stderr if the file cannot be written; do not fail before stdout emission. Extend the invoke harness to assert stdout on the symlink case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_6: SKILL exits on symlink instead of stdout envelope fallback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: SKILL Step 0 exits 1 when `bootstrap-routing.env` is a symlink instead of skipping file parse and using the wrapper stdout envelope per plan. Even with wrapper stdout fixed, the symlink guard can exit before parsing `_inv_out`, so dual-transport fallback never runs. Replace exit 1 with skip-file-parse and parse `_inv_out` only (and/or require a regular file).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_7: Exit-2 handler omits several `STEP_FAILED` values
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `implement-bootstrap-invoke.sh` exit-2 handler lacks arms for `create-branch`, `write-session-env`, and `emergency-bypass-log` that `implement-bootstrap.sh` can emit. Bootstrap exit 2 with those failures yields exit 2 and empty stdout but no stderr operator message (silent Step 0 abort). Add case arms or a default `*)` branch printing `STEP_FAILED` and a generic abort line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Harness does not assert `emergency_requested=false` forwarding
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-implement-bootstrap-invoke.sh` does not assert `emergency_requested=false` is forwarded as `--emergency-requested false`; wrapper could omit `false` and bootstrap would not receive an explicit non-emergency flag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


