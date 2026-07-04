## Decision 1: Step 5 detach infrastructure
- **Question**: Does review-and-fix step5 have --new-process-group or loop-identity support?
- **Resolution**: No. Must add --new-process-group to review-and-fix step5 in Python, plus new CLI verbs (review-and-fix write-loop-identity, await-loop-identity, normalize-status) using implement-specific config constants.
- **Source**: codebase (review_and_fix.py line 637; plan_review.py line 336; config.py lines 163–164)

## Decision 2: Step 8 treatment
- **Question**: Does Step 8 need code changes or documentation only?
- **Resolution**: Documentation only. persist_handoff writes rc=143 on SIGTERM exit; the .step-8-ship-handoff.rc hook sentinel is read by ship route-exit which handles rc=143 correctly; confirmed by #6213 larch6 incident.
- **Source**: codebase (step-8-ship.sh:21–43; step-8-ship.md lines 13–15)

## Decision 3: Orphan cap scope
- **Question**: Should orphan cap apply to Step 3 only, or also Step 5?
- **Resolution**: Both. Step 5 with full detach-and-reattach also needs an orphan cap on its detached loop.
- **Source**: user choice (Step 5 full detach) + issue requirement (orphan cap for detached loops)

## Decision 4: Hard constraint: separate identity paths for Step 5
- **Question**: Can Step 5 share DESIGN_STEP3_LOOP_IDENTITY_FILE and DESIGN_STEP3_WRAPPER_DETACHED_FILE?
- **Resolution**: No. Need separate IMPLEMENT_STEP5_LOOP_IDENTITY_FILE and IMPLEMENT_STEP5_WRAPPER_DETACHED_FILE constants in config.py.
- **Source**: codebase (config.py lines 163–164; process_identity.py line 447 uses design-specific path)
