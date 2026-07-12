## Decision 1: LintRule fields
- **Question**: What fields should `LintRule` hold?
- **Resolution**: Frozen dataclass: `rule_id: str`, `description: str`, `detect: Callable[[SourceFile], list[Finding]]`, `syntax_policy: Literal['fail', 'skip']`, `suppression_token: str`
- **Source**: user

## Decision 2: paths parameter semantics
- **Question**: When `paths` is supplied to `run_rule`, how should it work?
- **Resolution**: Filter git-discovered tracked files to only those matching the supplied paths; git ls-files --cached still runs
- **Source**: user
