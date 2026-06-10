## Decision 1: gh.py label wrapper placement
- **Question**: Should issue_label_add/remove/label_create be public in gh.py or private in clarify.py?
- **Resolution**: Public functions in gh.py, following the existing module pattern.
- **Source**: user

## Decision 2: Reference update breadth
- **Question**: Are AGENTS.md, SECURITY.md, get-issue-context.sh (comment) in scope?
- **Resolution**: Yes — update all references so make lint passes after scripts are retired.
- **Source**: user
