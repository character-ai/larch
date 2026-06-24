# OOS Acceptance Rubric (Materiality Gate)

An out-of-scope (OOS) observation clears the materiality gate — and should
be voted YES for filing as a tracked GitHub issue — only when **all three
criteria** below are satisfied. Default-deny: if you cannot clearly
satisfy each criterion, vote NO.

## Core question (backlog-relative)

Not *"would a maintainer schedule this?"* (easy to rationalize), but:
*"Would this rank above the median item already sitting in a busy
maintainer's backlog?"* This forces competition-for-attention framing.
If you cannot clearly see a maintainer choosing this over their existing
work, vote NO.

Automatic NO under this backlog-relative test:
- Style-only or polish-only items with no behavioral or maintenance impact.
- Speculative portability for untargeted shells, platforms, or tool versions.
- Cleanup or consistency work with no named future cost.

## Three objective criteria (all required for YES)

**1. Impact floor** — the problem must plausibly touch at least one of:
correctness, security, data integrity, user-visible behavior, or
maintainability **with a named future cost** (a concrete scenario where
the omission will cause real harm or real maintenance burden). Automatic
NO for:
- Pure readability or style refactors with no behavioral change.
- Speculative "defensive" robustness for inputs that cannot actually occur.
- Micro-optimizations without a measured or described hotspot.
- Cross-shell, cross-OS, or tool-version portability speculation for
  platforms the project does not target.

**2. Concrete trigger required** — YES only if the item names a specific
scenario, input, or state where the problem manifests. *"Could be
cleaner/safer"* with no triggering scenario is a NO. The trigger must be
observable (not hypothetical), and it must be plausible in the actual
usage context of this codebase.

**3. Issue-overhead test** — a tracked issue carries fixed overhead: triage,
scheduling, PR, review cycle. Vote YES only when the value of addressing
this problem plausibly exceeds that overhead. If scheduling it would cost
more than simply leaving it unaddressed, vote NO.

## Worked examples

### YES — passes all three criteria

- A function silently truncates UTF-8 multi-byte sequences at byte
  boundaries when the input contains non-ASCII characters; affects any
  run with internationalized branch names. *Impact*: data corruption.
  *Trigger*: non-ASCII input (concrete, plausible). *Overhead test*: a
  one-line fix is worth tracking; silent truncation would recur.
- A helper ignores the exit code of a `git push` call; on network
  failure the run reports success and leaves the branch unpushed.
  *Impact*: user-visible incorrect behavior. *Trigger*: any network
  hiccup or auth failure during push. *Overhead test*: clear value; easy
  to reproduce and fix.

### NO — fails one or more criteria

- A variable name could be more descriptive. *Impact*: readability only,
  no behavioral change. *Fails impact floor.*
- The script might behave differently on zsh vs bash. The project only
  targets bash. *Fails impact floor* (portability speculation for an
  untargeted platform).
- There is no error message when a config key is missing. The config key
  in question has a hardcoded default and can never be missing in normal
  operation. *Fails trigger* (no concrete, plausible scenario where the
  problem manifests).
- A loop could be rewritten as a pipeline for clarity. No behavioral
  change; refactor would take ~1 hour of engineering and review time.
  *Fails overhead test* (cost > value).

## Remedy is informational only

For any proposed OOS item, the suggested fix or remedy in the item body
is **informational only**. Vote based on whether the **problem described**
is real, concrete, and clears the three criteria above. Do NOT vote NO
because you disagree with the proposed fix — the future implementer
chooses the actual remedy.

---

## Update triggers

When this rubric changes, update all surfaces that reference it:

- `python/cli.py render voter` — plan-review and code-review OOS voter instructions
- `skills/implement/SKILL.md` — `main-agent-vote-required` OOS ballot instruction
- `skills/design/SKILL.md` — main-agent OOS standard in design review
- `skills/shared/review-acceptance-rubric.md` — "Out-of-Scope is the safe harbor" note
- `python/rendering.py` — plan-review and specialist render OOS proposal instructions
- `python/review_pipeline.py` — `_dynamic_agent_body` OOS proposal instructions
