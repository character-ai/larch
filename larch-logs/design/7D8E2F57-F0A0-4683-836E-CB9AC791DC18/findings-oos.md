### OOS_1: Shell `printf` skip breadcrumbs with U+2014 sit outside both `python/larch/**` and the planned markdown `Print:`/`⏩` scanner
- **Description**: Shell `printf` skip breadcrumbs with U+2014 sit outside both `python/larch/**` and the planned markdown `Print:`/`⏩` scanner. Scenario: `⏩ 18a: stall recovery — no stall detected` still reaches operators from Bash wrappers; enabling only the planned lint leaves this path unguarded
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-18.sh:168
- **Phase**: design



### OOS_2: Shell-emitted Step 5 breadcrumb still contains U+2014 outside the planned markdown scanner.
- **Description**: Shell-emitted Step 5 breadcrumb still contains U+2014 outside the planned markdown scanner.. Scenario: `printf '> **🔶 /implement 5: code review — review-and-fix …'` is user-visible output but is not under `python/larch/**` or `skills/**/*.md` `Print:`/`⏩` rules, so the new lint will not guard it.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-5-review.sh:263
- **Phase**: design



### OOS_3: `logging_util.BreadcrumbWriter().emit` is another operator-visible output path not named in the sink list.
- **Description**: `logging_util.BreadcrumbWriter().emit` is another operator-visible output path not named in the sink list.. Scenario: BreadcrumbWriter.emit routes progress text to stdout or quiet logs across ship, finalize, rendering, and design helpers. The plan names `logging_util.emit`/`diagnostic` but not this method; future breadcrumb edits could add U+2014 without lint coverage. Current call sites appear clean.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/core/logging_util.py:163-180
- **Phase**: design



### OOS_4: Shell printf breadcrumbs fall outside em-dash-output lint scope
- **Description**: Shell printf breadcrumbs fall outside em-dash-output lint scope. Scenario: step-5-review.sh still printf-emits a 🔶 breadcrumb with U+2014 while the plan scopes the new lint to python/larch output calls and skill-markdown Print:/⏩ lines only. Python dispatch_commit_route.py duplicates the string and belongs in the runtime scrub, but the shell path can still emit banned punctuation at Step 5 entry.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-5-review.sh:263
- **Phase**: design



### OOS_5: Meta-prose still documents the old MANDATORY separator shape
- **Description**: Meta-prose still documents the old MANDATORY separator shape. Scenario: skill-design-principles.md and research reference headers describe the directive as MANDATORY — READ ENTIRE FILE in documentation text, not as emitted Print:/⏩ output. The new lint excludes this prose, so CI will not fail, but docs will describe a separator the lock retires.
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/shared/skill-design-principles.md:27-119
- **Phase**: design



