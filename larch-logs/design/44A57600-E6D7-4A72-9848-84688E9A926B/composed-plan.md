## Plan

## Approach

- Add two **Python AST linters** under `python/`.
- Mirror `python/lint_keyword_only.py`:
  - `--root`
  - `--write`
  - canonical sorted baseline JSON
  - optional exemptions JSON with validated row shape and non-empty `reason`
  - inline pragma with required reason
  - exit `0` clean or baselined only
  - exit `1` new violation
  - exit `2` tool or baseline failure
- **Scan recursively** over all production modules under `python/**/*.py`, not only top-level `python/*.py`.
- Baseline all current violations with a **required non-empty `reason` on every baseline record**.
- Do not edit existing production modules to fix violations in this PR.

## Files to modify/create

### NEW: python/lint_subprocess_via_runner.py

Implement `python3 python/cli.py lint subprocess-via-runner`.

**Scope:**

- Recursively scan production modules under `python/**/*.py`.
- Normalize `file` paths as POSIX paths relative to `python/` (for example `plan_quality.py`, `analysis/codex_role_costs.py`).
- Exclude:
  - `proc.py` (only `python/proc.py`)
  - `config.py` is not excluded for subprocess linter
  - `test_*.py` at any depth
  - `conftest.py`, `test_support.py`, `review_test_support.py` (same helper filenames as `lint_keyword_only.py`)
- Skip symlinks.
- Use a recursive enumerator over `python/**/*.py`; do **not** copy `lint_keyword_only.iter_source_files` top-level `glob("*.py")`.

**Detection:**

- Flag direct calls to:
  - `subprocess.run`
  - `subprocess.Popen`
  - `subprocess.check_output`
  - `subprocess.call`
- Use AST only.
- Match only `subprocess.<name>` attribute calls. Do not chase imported aliases in v1.

**Occurrence identity:**

- `occurrence` is the **1-based index** of each matching subprocess call site within the same `qualified_symbol`.
- Count **all** matching call sites in **source order** within the enclosing function/method/class body.
- Assign occurrence by **lexical pre-order traversal**: walk `node.body` lists in declaration order, recurse into nested bodies in source order. Do **not** use `ast.walk` for occurrence numbering.
- Compute occurrence **before** inline-pragma filtering, exemption filtering, or baseline comparison.
- Pragma and exemptions suppress reporting only; they do **not** renumber sibling occurrences.

**Baseline:**

- Use `python/subprocess-via-runner-baseline.json`.
- Required record keys (exact set; reject unknown keys):
  - `file`
  - `qualified_symbol`
  - `callee`
  - `occurrence`
  - `reason` (non-empty string)
- **Identity key** for baseline matching, exemption scoping (when applicable), and `--write` reason preservation: `(file, qualified_symbol, callee, occurrence)` — all structural fields except `reason`.
- Sort canonically by identity key.
- `--write` regenerates structural fields from the live tree.
- On `--write`, **preserve** existing `reason` values for records whose identity key matches the committed baseline.
- When the baseline file is absent, accept optional `--initial-reason <text>` to stamp every emitted record once for bootstrap.
- When a live finding has no preserved reason and no `--initial-reason`, fail closed with exit `2` and list keys needing reasons.
- `load_baseline` rejects records with missing keys, extra keys, or missing or empty `reason`.
- Reject duplicate live identity keys before write or check, and reject duplicate baseline identity keys on load, matching `lint_complexity_baseline.py`.

**Exemptions:**

- Use optional `python/subprocess-via-runner-exemptions.json` (top-level JSON array).
- Each exemption row must have **exactly** these keys (reject unknown keys with exit `2`):
  - `file` — non-empty POSIX path relative to `python/`
  - `reason` — non-empty string
- File-level exemption suppresses **all** subprocess findings in that module.
- Validate non-empty `file` and `reason` on load; reject rows missing either field with exit `2`.
- Inline suppression (separate from JSON exemptions):
  - `# lint-subprocess-via-runner: ok <reason>`
- Accept inline suppression on the same physical line as the call, and a standalone comment immediately before the call.

**Output:**

- Warn for baselined findings.
- Fail only for live findings absent from baseline and exemptions.
- Include file, qualified symbol, callee, occurrence, and a clear message.

### NEW: python/subprocess-via-runner-baseline.json

Generate with:

- `python3 python/cli.py lint subprocess-via-runner --write --initial-reason 'grandfathered direct subprocess usage pre-G-Py-9 ratchet'`

Commit the generated baseline.

Do not hand-edit structural fields (`file`, `qualified_symbol`, `callee`, `occurrence`).

Per-record `reason` values may be refined before commit when bootstrap used a shared initial reason, but every committed record must keep a validated non-empty `reason`.

### NEW: python/subprocess-via-runner-exemptions.json

Create as a JSON array.

Populate only true CLI-glue or entrypoint exemptions with `{file, reason}` rows.

Use `[]` if no file-level exemptions are needed after baseline generation.

### NEW: python/test_lint_subprocess_via_runner.py

Add pytest coverage for:

- Direct `subprocess.run` in production source is detected.
- `subprocess.Popen`, `check_output`, and `call` are detected.
- `proc.py` is skipped.
- Nested production modules (for example under `python/analysis/`) are scanned.
- `test_*.py` and helper test files are skipped at any depth.
- Two direct subprocess calls in the same function receive **distinct** `occurrence` values (`1` and `2`) and stable canonical ordering (fixture modeled on `plan_quality.py` timing helpers).
- `occurrence` is assigned before pragma suppression and remains stable when a sibling call is pragma-suppressed.
- Baseline suppresses existing findings but still emits warnings.
- Baseline records without `reason` or with empty `reason` fail load with exit `2`.
- Baseline records with missing or extra keys fail load with exit `2`.
- Duplicate live identity keys and duplicate baseline identity keys fail with exit `2`.
- A new finding not in baseline exits `1`.
- `--write` emits canonical sorted JSON and preserves matching `reason` values.
- `--write` without preserved reasons and without `--initial-reason` exits `2`.
- Absent baseline file plus `--write --initial-reason ...` bootstrap succeeds and writes canonical JSON.
- Exemption rows require non-empty `file` and `reason`; missing or empty `file` fails load with exit `2`.
- Exemption rows with missing or empty `reason` fail load with exit `2`.
- Exemption rows with unknown keys fail load with exit `2`.
- A matching file-level exemption suppresses all subprocess findings in that module.
- Inline pragma requires a reason and suppresses only the intended call.
- Malformed baseline JSON exits `2` with a clear error message.
- Malformed exemptions JSON exits `2` with a clear error message.
- Syntax errors or unreadable files follow the existing linter fail or skip convention chosen from `lint_keyword_only.py`.

### NEW: python/lint_env_via_config_constant.py

Implement `python3 python/cli.py lint env-via-config-constant`.

**Scope:**

- Recursively scan production modules under `python/**/*.py`, same enumerator and helper-file exclusions as the subprocess linter.
- Exclude:
  - `config.py` (only `python/config.py`)
  - `proc.py` is not excluded for env linter
  - `test_*.py` at any depth; `conftest.py`, `test_support.py`, `review_test_support.py`
- Validate `file` paths on baseline and exemption load using the same POSIX-relative-to-`python/` normalization.

**Config parsing:**

- Parse `python/config.py` once per run.
- Build `env_value -> ENV_CONSTANT_NAME` from:
  - `ast.AnnAssign`, for `ENV_*: Final = "VALUE"`
  - `ast.Assign`, for `ENV_* = "VALUE"`
- When duplicate `ENV_*` values map to one literal in a synthetic fixture config, fail closed with exit `2`.
- When bootstrapping against live `config.py` that already contains duplicate values, pick the first sorted constant name and document that choice in a test.

**Detection:**

- Flag bare literal env access when the literal matches a known config constant value:
  - `os.environ.get(<literal>)` (`access: get`)
  - `os.environ.get(<literal>, ...)` with any default argument (`access: get`) — match by **first argument only**
  - `os.environ["X"]` in **Load** context (`access: subscript_load`)
  - `os.environ["X"]` in **Store** context (`access: subscript_store`)
- Do not flag:
  - `os.environ.get(config.ENV_X)`
  - `os.environ.get(config.ENV_X, ...)`
  - `os.environ[config.ENV_X]` in either Load or Store context
  - literals ending in `_SH`
  - literals with no matching `config.ENV_*` constant

**Occurrence identity:**

- `occurrence` is the **1-based index** of each matching env access site within the same `qualified_symbol`.
- Count **all** matching access sites in **source order** within the enclosing function/method/class body, via the same lexical pre-order traversal as the subprocess linter (not `ast.walk`).
- Identity key includes `access` so Load and Store uses at the same literal position are distinct when both match.

**Baseline:**

- Use `python/env-via-config-constant-baseline.json`.
- Required record keys (exact set; reject unknown keys):
  - `file`
  - `qualified_symbol`
  - `env_name`
  - `constant`
  - `access`
  - `occurrence`
  - `reason` (non-empty string)
- **Identity key** for baseline matching, exemption scoping (when applicable), and `--write` reason preservation: `(file, qualified_symbol, env_name, constant, access, occurrence)` — all structural fields except `reason`.
- Sort canonically by identity key; `--write` regenerates structural fields and preserves matching `reason` values; `--initial-reason` bootstraps an absent baseline.
- `load_baseline` rejects records with missing keys, extra keys, or missing or empty `reason`.
- Reject duplicate live identity keys before write or check, and reject duplicate baseline identity keys on load, matching `lint_complexity_baseline.py`.

**Exemptions:**

- Use optional `python/env-via-config-constant-exemptions.json` (top-level JSON array).
- Allowed keys per row: required `file` and `reason`; optional `env_name` and/or `constant` for finer-grained scope.
- Reject unknown keys and rows with missing or empty required fields with exit `2`.
- **File-only row** (`file` + `reason` only): suppresses all env findings in that module.
- **Scoped row** matching rules:
  - `env_name` only: suppress findings whose bare literal equals that `env_name`.
  - `constant` only: suppress findings mapped to that `ENV_*` constant name.
  - both `env_name` and `constant` present: suppress only when **both** fields match the same finding.
- Inline suppression:
  - `# lint-env-via-config-constant: ok <reason>`
- Accept inline suppression on the same physical line as the access, and a standalone comment immediately before the access.

**Output:**

- Warn for baselined findings.
- Fail only for live findings absent from baseline and exemptions.
- Reference the shared exit `0` / `1` / `2` semantics from Approach.
- Include file, qualified symbol, env name, config constant, access, occurrence, and a clear message.

### NEW: python/env-via-config-constant-baseline.json

Generate with:

- `python3 python/cli.py lint env-via-config-constant --write --initial-reason 'grandfathered bare env literal pre-G-Cfg-2 ratchet'`

Commit the generated baseline.

Do not hand-edit structural fields (`file`, `qualified_symbol`, `env_name`, `constant`, `access`, `occurrence`); every committed record keeps a validated non-empty `reason`.

### NEW: python/env-via-config-constant-exemptions.json

Create as a JSON array.

Populate only true exemptions with `{file, reason}` rows, optionally scoped with `env_name` and/or `constant`.

Use `[]` unless a real exemption is needed.

### NEW: python/test_lint_env_via_config_constant.py

Add pytest coverage for:

- `ENV_*: Final = "VALUE"` is parsed.
- Plain `ENV_* = "VALUE"` is parsed.
- `os.environ.get("VALUE")` is detected.
- `os.environ.get("VALUE", "")` and other defaulted `os.environ.get(<literal>, ...)` forms are detected by first argument.
- `os.environ["VALUE"]` is detected in Load context.
- `os.environ["VALUE"] = ...` is detected in Store context (fixture modeled on `cli.py` `LARCH_QUIET_DISABLE` assignment pattern).
- `os.environ.get(config.ENV_NAME)` is allowed.
- `os.environ.get(config.ENV_NAME, ...)` is allowed.
- `os.environ[config.ENV_NAME]` is allowed in Load and Store contexts.
- `config.py` is skipped.
- Nested production modules are scanned; `config.py` exclusion is path-exact.
- `test_*.py` and helper test files (`conftest.py`, `test_support.py`, `review_test_support.py`) are skipped at any depth.
- `*_SH` literals are skipped.
- Unknown env literals are skipped.
- Two bare env accesses in the same function receive distinct `occurrence` values (`1` and `2`) and stable canonical ordering.
- `occurrence` is assigned before pragma suppression and remains stable when a sibling access is pragma-suppressed.
- Two identical bare env accesses in different `qualified_symbol` values produce distinct baseline rows (no collapse across symbols).
- Baseline records without `reason`, with empty `reason`, or with missing/extra keys fail load with exit `2`; duplicate live and baseline identity keys fail with exit `2`.
- `--initial-reason` bootstrap succeeds when the baseline file is absent.
- A matching file-level exemption suppresses all env findings in that module.
- Scoped exemption matching: `env_name`-only, `constant`-only, and conjunctive `env_name`+`constant` rows suppress only intended findings.
- Inline pragma requires a reason and suppresses only the intended access.
- Duplicate `ENV_*` values mapping to one literal: when bootstrapping against live `config.py`, if duplicates already exist, pick the first sorted constant name and add a test documenting deterministic choice and stable detection; when duplicates are introduced in a synthetic fixture config, fail closed with exit `2` unless the documented first-sorted-wins policy applies.

### UPDATED: python/cli.py

Register two lint verbs:

- `("lint", "subprocess-via-runner"): ("lint_subprocess_via_runner", "main")`
- `("lint", "env-via-config-constant"): ("lint_env_via_config_constant", "main")`

Keep the change local to `_REGISTRY`.

### UPDATED: Makefile

Wire both linters into `py-lint-main` after `keyword-only` or near the other Python ratchets:

- `$(PYTHON) python/cli.py lint subprocess-via-runner`
- `$(PYTHON) python/cli.py lint env-via-config-constant`

Add baseline regeneration targets:

- `regen-subprocess-via-runner-baseline`
- `regen-env-via-config-constant-baseline`

Each regen target passes the bootstrap `--initial-reason` only when the baseline file is absent; document that routine regen preserves per-record reasons.

Update the `.PHONY` line for those targets.

### UPDATED: .pre-commit-config.yaml

Add two local hooks near `lint-keyword-only`:

- `lint-subprocess-via-runner`
- `lint-env-via-config-constant`

Use:

- `language: system`
- `pass_filenames: false`
- `always_run: true`
- `files: ^python/.*\.py$`

Entries:

- `python3 python/cli.py lint subprocess-via-runner`
- `python3 python/cli.py lint env-via-config-constant`

### UPDATED: docs/linting.md

Document both linters in the lint table and add a short Python ratchet subsection mirroring keyword-only / complexity-baseline style.

Include:

- what each linter enforces
- recursive `python/**/*.py` production scope and exclusions
- baseline ratchet behavior
- full baseline identity tuples and required per-record `reason` on grandfathered baseline rows
- occurrence numbering via lexical pre-order (not `ast.walk`)
- `--write` regeneration target names and `--initial-reason` bootstrap semantics
- exemption JSON row shapes (`file` + `reason`; optional `env_name` / `constant` scoping keys for env linter with conjunctive matching when both are present; unknown-key rejection)
- inline pragma names
- defaulted `os.environ.get(<literal>, ...)` detection for env linter
- that existing violations are grandfathered with documented reasons, not silent baseline keys

Avoid hardcoded violation counts in prose (drift-prone); describe the mechanism, not the current tally.

## Edge cases

- **Nested functions and methods:** resolve the nearest enclosing qualified symbol for stable baseline keys.
- **Recursive tree layout:** `python/analysis/*.py` and any future nested production packages are in scope; only the explicit exclusion list is skipped.
- **Multiple calls in one function:** `occurrence` indexes all matching sites in source order within the qualified symbol before any suppression, using lexical pre-order over `node.body` (not `ast.walk`); identity never uses line numbers.
- **Pragma on one of several sibling calls:** sibling occurrences keep their pre-suppression ordinals.
- **Malformed baseline or exemptions JSON:** exit `2`.
- **Missing exemptions file:** treat as empty.
- **Baseline record missing or empty `reason`, or missing/extra keys:** exit `2` on load (both linters); exit `2` on `--write` when reasons cannot be preserved.
- **Duplicate identity keys (live or baseline):** exit `2` (both linters).
- **Duplicate config env values:** fail closed with exit `2` on synthetic fixture configs; when bootstrapping against live `config.py` that already contains duplicate values, pick the first sorted constant name and document that choice in a test.
- **Pragma without reason:** do not suppress. Report a clear error or violation.
- **Syntax errors in scanned files:** follow the convention from `lint_keyword_only.py`; do not invent a different policy.
- **Env scoped exemptions:** `env_name`-only and `constant`-only rows must not be interpreted as file-wide suppression; conjunctive matching applies only when both optional keys are present.
- **Defaulted `os.environ.get`:** first-argument literal matching must flag `os.environ.get("TMPDIR", "")` and similar forms.

## Failure modes

- **Baselines hide too much:** keep records more granular than file-only. Use qualified symbol, access kind (env linter), callee (subprocess linter), and pre-suppression occurrence.
- **Line churn causes baseline churn:** avoid raw line numbers in baseline identities; occurrence is positional within symbol, not line-based.
- **Occurrence renumbering on unrelated edits:** occurrence counts all matching sites before suppression using lexical pre-order so traversal order is stable; inserting a new call shifts later ordinals by design; document that removing grandfathered calls requires baseline cleanup, not automatic renumber preservation.
- **AST walk reorders siblings:** using `ast.walk` for occurrence would renumber calls unpredictably; lexical pre-order over `node.body` avoids that failure mode.
- **CLI-glue exemptions become a dumping ground:** require non-empty `file` and `reason` on every exemption row; keep subprocess exemptions file-scoped only.
- **Env linter flags harness variables:** skip unknown literals and `*_SH` values as agreed.
- **Env linter misses assignments or defaulted gets:** Store-context `os.environ[...]` and `os.environ.get("X", default)` must be flagged alongside the Load/zero-arg forms.
- **Nested modules escape enforcement:** recursive scan plus `^python/.*\.py$` pre-commit filter closes the gap.
- **Incomplete baseline schema:** full identity-tuple validation on load prevents cross-symbol collapse or unstable ratchet matching.
- **Ambiguous scoped exemptions:** explicit conjunctive matching rules prevent over- or under-suppression.

## Testing strategy

Run:

- `python3 -m pytest python/test_lint_subprocess_via_runner.py python/test_lint_env_via_config_constant.py`
- `make regen-subprocess-via-runner-baseline`
- `make regen-env-via-config-constant-baseline`
- `make py-lint-main`
- `make py-test`
- `make lint`

## Acceptance

- Both new lint CLI verbs (`lint subprocess-via-runner`, `lint env-via-config-constant`) exist and run.
- Each linter ships a regression harness (`test_lint_*.py`, auto-discovered by `make py-test`) and is wired into the lint targets.
- An allowlist / suppression mechanism with inline reason exists: baseline JSON with required per-record `reason`, optional exemptions JSON with `reason`, and inline `# lint-<name>: ok <reason>` pragma.
- Existing violations are grandfathered into the baselines with documented reasons (no existing module logic edited).
- Both baselines regenerate byte-stably on a clean tree when no live findings changed.
- A synthetic new violation fails in pytest; repeated-call occurrence fixtures pass for both linters.
- Malformed baseline / exemptions JSON, missing/extra keys, blank `reason`, and duplicate identity keys all exit `2` in pytest (both linters).
- Env linter detects defaulted `os.environ.get(<literal>, ...)`, Store-context assignments, and nested `python/analysis/*.py` modules; scoped exemption conjunctive matching and duplicate `ENV_*` value policy are covered.
- Pre-commit includes both hooks with the recursive `^python/.*\.py$` filter.
- **CI coverage is achieved through the existing `python-lint` job (`make py-lint-main`) and `python-tests` job (`make py-test`); no `.github/workflows/ci.yaml` edit is required.**

review_status: complete
rounds_completed: 5
diff_lines: 4250
