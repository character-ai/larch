## Goal
Implement issue #6173: [IMPLEMENTING] [BUG] /design Step 0-pre phrasing invites an incorrect standalone parse-flags….

## Implementation Plan
## Summary

`skills/design/SKILL.md`'s Step 0-pre section instructs the orchestrator to "Run `python/cli.py design parse-flags`" as though it were a standalone command to execute, then immediately clarifies "do not invoke a separate parse fence" because Step 0a's `step0-session` wrapper already runs the parser internally. Read in isolation, the first clause reads as an executable imperative; the caveat that invalidates that reading arrives only in the same sentence's back half. Following the imperative reading and mimicking the neighboring Step 0a `-- <PUBLIC_ARGV_WORDS>` example produces a real, silent mis-parse: `python3 cli.py design parse-flags -- -s 6158` returns `POSITIONAL_KIND=verbal POSITIONAL_VALUE=-s 6158` instead of recognizing `-s` as `--skip-approve` and `6158` as the issue number.

## Original report

the above mis-interpretation of the command line -s flag

(User-supplied context: during a live `/design -s 6158` run in this conversation, the assistant's first Step 0-pre action was to run `python3 cli.py design parse-flags -- -s 6158` directly as its own Bash fence, copying the `-- <PUBLIC_ARGV_WORDS>` convention shown a few lines later for the unrelated `step0-session` wrapper. This produced `POSITIONAL_KIND=verbal`, `POSITIONAL_VALUE=-s 6158` — i.e., `--skip-approve` and the issue number were both swallowed into garbled verbal text. The assistant caught the wrong output, root-caused it by reading `python/larch/design/design_argv.py` and `python/larch/design/design_step0_env.py`, and re-ran the call without the leading `--`, which correctly produced `SKIP_APPROVE_REQUESTED=true POSITIONAL_KIND=issue POSITIONAL_VALUE=6158`.)

## Reproduction scenario

1. Open `skills/design/SKILL.md` and read only the Step 0-pre section (line ~92): "Run `python/cli.py design parse-flags` as the sole Step 0-pre parser. Render public argv as one shell-quoted word per original token at `<PUBLIC_ARGV_WORDS>`; keep verbal tails positional. Step 0a runs the parser before `session setup`; do not invoke a separate parse fence."
2. Taking the first clause literally, run the command directly, using the `-- <PUBLIC_ARGV_WORDS>` convention modeled two paragraphs later for Step 0a's `step0-session` call:
   ```
   python3 python/cli.py design parse-flags -- -s 6158
   ```
3. Observe the stdout:
   ```
   PARTITION_REQUESTED=false
   BRAINSTORM_REQUESTED=false
   APPROVE_REQUESTED=false
   SKIP_APPROVE_REQUESTED=false
   NO_DEDUP_REQUESTED=false
   RUN_ID=
   DIFFICULTY=
   POSITIONAL_KIND=verbal
   POSITIONAL_VALUE=-s 6158
   ```
4. Compare with the correct invocation (no leading `--`), which matches how `design_step0_env.py` actually shells out to this same verb internally:
   ```
   python3 python/cli.py design parse-flags -s 6158
   ```
   producing the intended:
   ```
   SKIP_APPROVE_REQUESTED=true
   POSITIONAL_KIND=issue
   POSITIONAL_VALUE=6158
   ```

## Expected behavior

Either:
- The orchestrator should never invoke `design parse-flags` as a standalone Bash fence at Step 0-pre in the first place (per the SKILL.md's own "do not invoke a separate parse fence" instruction), and the SKILL.md wording should make that unambiguous on a first read, with no plausible imperative misreading; or
- If a standalone invocation is ever legitimate (for example, manual debugging), the documentation should show the correct invocation syntax (no leading `--`) so nobody mimics the neighboring `step0-session -- <PUBLIC_ARGV_WORDS>` convention, which has different `--`-consumption semantics.

## Observed behavior

The Step 0-pre text's first clause ("Run `python/cli.py design parse-flags` ...") reads as a directly-executable instruction. Combined with the neighboring, superficially similar `step0-session ... -- <PUBLIC_ARGV_WORDS>` example, it invites an incorrect standalone invocation with a leading `--`. Because `--` is a deliberate, documented "stop flag parsing" marker in `design_argv.py` (see `skills/design/references/flags.md` line 27: "`--` stops flag parsing: the next all-digit token becomes the issue id; otherwise the rest becomes literal verbal text."), prefixing it before `-s 6158` causes the entire remainder to be swallowed as literal verbal text, silently dropping `--skip-approve` and misclassifying the issue number as new-issue feature text. Had this actually driven routing (rather than being caught and corrected first), `POSITIONAL_KIND=verbal` would have triggered `/larch:issue` to create a brand-new GitHub issue titled/described as `-s 6158` instead of routing to the intended existing issue #6158 with `--skip-approve` honored.

## Root cause analysis

Two contributing factors, in order of impact:

1. **SKILL.md phrasing/ordering (primary, documentation-only).** Step 0-pre's instruction "Run `python/cli.py design parse-flags` as the sole Step 0-pre parser" is stated as an action before the sentence that clarifies it is not something the orchestrator should invoke separately ("Step 0a runs the parser before `session setup`; do not invoke a separate parse fence"). The clarifying clause is present but trails the imperative-sounding lead, which invites exactly the executable misreading observed here.
2. **No worked example for the (rare) standalone-invocation case.** The only concrete `-- <PUBLIC_ARGV_WORDS>` example near Step 0-pre belongs to the `step0-session` wrapper (`python/larch/design/design_step0.py::step0_session_main` via `_parse_wrapper_args` in `python/larch/design/design_step0_env.py`), which recognizes its own flags (`--claude-pid`, `--plugin-root`, etc.) and treats a literal `--` token as the boundary before the forwarded design argv (`ns.public_argv = args[i + 1:]` — the `--` itself is consumed and never reaches `parse_flags_main`). The raw `design parse-flags` verb has no such wrapper-owned `--` boundary; its own internal subprocess call site (`design_step0_env.py` line ~374: `[sys.executable, cli.py, "design", "parse-flags", "--output", str(out_path), *public_argv]`) never prepends a `--`. Nothing near Step 0-pre shows this distinction, so copying the neighboring wrapper's calling convention is a natural mistake.

The underlying parser behavior in `design_argv.py` (`_apply_double_dash`, `_dispatch_argv_token`) is *not* itself a defect — treating `--` as "stop flag parsing" is a deliberate, documented feature (`flags.md` line 27) that lets an operator force flag-looking text into a literal verbal issue description. I did not find a code-level bug in the parser; the fix most likely belongs in `skills/design/SKILL.md`'s Step 0-pre wording. I flag this uncertainty explicitly since a maintainer may still want defense-in-depth at the parser layer (see Suggested fix(es)).

## Evidence

- `skills/design/SKILL.md:92` — the ambiguous Step 0-pre sentence, in the actual repo (confirmed identical to the installed plugin cache copy at the same relative path).
- `python/larch/design/design_argv.py` — `_apply_double_dash` (around lines 145-153) and `_dispatch_argv_token` (around lines 156-189, notably `if token == "--":` at line 222 in `_dispatch_argv_token`'s caller) implement the "stop flag parsing on `--`" behavior that silently absorbs `-s 6158` into verbal text when a `--` precedes it.
- `python/larch/design/design_step0_env.py` — `_parse_wrapper_args` (around lines 123-169) shows `step0-session`'s own `--`-consuming convention (`if token == "--": ns.public_argv = args[i + 1:]`), and the internal subprocess call at line ~374 (`[sys.executable, cli.py, "design", "parse-flags", "--output", str(out_path), *public_argv]`) confirms the raw verb is invoked with no leading `--` when called correctly.
- `skills/design/references/flags.md:27` — documents `--`'s "stop flag parsing" semantics as intentional, ruling out a parser-level bug.
- `python/tests/design/test_design_argv.py` — every existing test invokes `parse-flags` without a leading `--` token (e.g., `_run_parse("--brainstorm", "123")`, `_run_parse("-s", "-s")`); there is no test exercising a bare/leading `--` before flag-like tokens, so this exact confusion path has no regression coverage either way.
- Live transcript evidence from this session: `python3 cli.py design parse-flags -- -s 6158` returned `POSITIONAL_KIND=verbal POSITIONAL_VALUE=-s 6158`; the corrected `python3 cli.py design parse-flags -s 6158` (no `--`) returned `SKIP_APPROVE_REQUESTED=true POSITIONAL_KIND=issue POSITIONAL_VALUE=6158`.

## Affected files

- `skills/design/SKILL.md` — Step 0-pre section; the ambiguous instruction and missing worked example live here.
- `python/larch/design/design_argv.py` — implements the `--` "stop flag parsing" behavior being misapplied; relevant if a defensive code-level mitigation is chosen instead of or in addition to a documentation fix.
- `python/larch/design/design_step0_env.py` — shows the correct, wrapper-owned `--`-consuming convention that Step 0-pre's neighboring example is drawn from; useful context for whoever rewrites the Step 0-pre wording.
- `skills/design/references/flags.md` — already documents `--`'s intentional semantics; may need a cross-reference note if Step 0-pre gains a worked example.
- `python/tests/design/test_design_argv.py` — currently has no test for a bare leading `--` before flag-like tokens; a regression test would help pin down whichever fix is chosen.

## Suggested fix(es)

- Reorder/reword `skills/design/SKILL.md`'s Step 0-pre section so the "do not invoke a separate parse fence" instruction leads, not trails — e.g., state plainly up front that the orchestrator must NOT run `design parse-flags` as its own Bash fence, and that Step 0a's `step0-session` call performs the parse internally.
- If a standalone invocation is ever legitimate (debugging, future tooling), add one concrete example showing the correct syntax with no leading `--`, explicitly contrasting it with `step0-session`'s wrapper-owned `-- <PUBLIC_ARGV_WORDS>` convention so the two are not conflated.
- Optional defense-in-depth at the code layer: `parse_flags_main` could special-case an argv that is *only* a lone leading `--` followed by tokens that look like known flags (e.g., `-s`, `--brainstorm`) plus a trailing digit run, and emit a distinguishable diagnostic (still verbal, but perhaps a `VALIDATION_ERROR`-style hint) rather than silently succeeding with `POSITIONAL_KIND=verbal`. This must not remove the existing, intentional "force flag-looking text into verbal mode via a leading `--`" escape hatch documented in `flags.md`, so this option needs care and may not be worth the complexity relative to the documentation fix.
- Add a regression test to `python/tests/design/test_design_argv.py` covering `_run_parse("--", "-s", "123")` (or similar) so the exact, intentional behavior is pinned down and any future change to this path is deliberate.

## Open questions

- Should the documentation-only fix be considered sufficient, or does a maintainer want the defensive code-layer diagnostic too? The tradeoff is discoverability of the trap versus preserving the existing verbal-escape feature untouched.
- Is there any other Step 0-pre-adjacent skill text (e.g., `/implement`'s analogous flag-parsing entry, if one exists) that models the same ambiguous "Run X" phrasing before a "don't actually run it separately" caveat, which might benefit from the same wording fix for consistency?

## Test plan
(no test plan section in plan-file)
