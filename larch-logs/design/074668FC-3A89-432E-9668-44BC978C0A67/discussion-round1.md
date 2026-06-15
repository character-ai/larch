## Decision 1: python/design_legacy.py focused-target scope
- **Question**: Should python/design_legacy.py get a focused pytest mapping in checks.py?
- **Resolution**: No dedicated test file exists (python/test_design_legacy.py is absent). Leave design_legacy.py on the broad python/*.py fallback. test_checks.py should assert this explicitly.
- **Source**: codebase

## Decision 2: Item 6 anti-polling pin scope
- **Question**: Does test-implement-anti-polling-rule.sh line 75 pin still match live SKILL.md?
- **Resolution**: Pin 'Step 5 invokes **one** `skills/implement/scripts/step-5-review.sh`' matches SKILL.md line 584 exactly. Item 6 is verify-only; no code change needed.
- **Source**: codebase

## Decision 3: docs/skills.md existence for Item 9
- **Question**: Does docs/skills.md exist, or must it be created?
- **Resolution**: docs/skills.md exists. Update in place with a /bug section.
- **Source**: codebase

## Decision 4: New harness shard placement
- **Question**: Which shards should test-design-step1d5 and test-design-log-ship go in?
- **Resolution**: test-design-step1d5 → test-harnesses-19 (near test-design-step-validator-autofix). test-design-log-ship → test-harnesses-13 (near test-design-log-publish).
- **Source**: codebase

## Decision 5: Item 5 fix scope
- **Question**: What exactly needs to change to fix the dynamic archetype cap parity?
- **Resolution**: step-5-review.sh validates dynamic_archetypes_cap but does not export it before exec. review_and_fix.py reads os.environ.get("LARCH_DYNAMIC_ARCHETYPES_MAX") first, then re-resolves from session-env.sh. Adding export LARCH_DYNAMIC_ARCHETYPES_MAX="$dynamic_archetypes_cap" before exec makes banner and executor use the same value. No resolver logic change needed in Python.
- **Source**: codebase
