## Decision 1: Command scope
- **Question**: Which commands does this apply to (`/design`, `/implement`, others)?
- **Resolution**: Just `/design` and `/implement`. `/research` and others stay as-is.
- **Source**: user

## Decision 2: Reset-on-failure scope
- **Question**: Should the rename be reset to the original title on subsequent cancel or failure paths?
- **Resolution**: No reset logic. User clarified the original issue body was misspoken on this aspect.
- **Source**: user

## Decision 3: Constraint — rename must follow eligibility validation
- **Question**: Where is the rename allowed to fire relative to eligibility validation?
- **Resolution**: Rename must happen AFTER the step that validates the issue's eligibility to be worked on, because one aspect of that validation is detecting a pre-existing `[IMPLEMENTING]`/`[DESIGNING]`/`[DONE]` prefix; renaming before validation would corrupt that signal.
- **Source**: user

## Decision 4: `/design` rename position
- **Question**: Should the `[DESIGNING]` rename in `/design` move earlier than Step 0b sub-step 5.5?
- **Resolution**: No change. The current position (sub-step 5.5) is acceptable — it already follows the lifecycle-prefix filter (2.5) and re-entry guard (2.6), and keeps the rename gated behind the clarify/already-planned/tier-gate operator branches so their cancels don't leave `[DESIGNING]` on the title.
- **Source**: user

## Decision 5: `/implement` rename position
- **Question**: Should the `[IMPLEMENTING]` rename in `implement-bootstrap.sh` move earlier than the end of `phase_tracking`?
- **Resolution**: Yes. Move the rename to immediately after `get-issue-state.sh` validates `STATE=OPEN`/`IS_PR=false`, BEFORE `run_larch_log_init` writes any larch-logs and BEFORE `post-tracking-issue.sh` posts the adoption comment. Applies to both Branch 1 (resume) and Branch 2 (adopt) paths.
- **Source**: user
