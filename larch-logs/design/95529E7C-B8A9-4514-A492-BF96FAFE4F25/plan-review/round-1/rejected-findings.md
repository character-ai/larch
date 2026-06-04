### [Plan Review] FINDING_5

### FINDING_5: Explicit empty `--repo` behavior diverges from documented hub-default fallback
- **Reviewer(s)**: Codex-dyn-caller-compat
- **Severity**: latent
- **Concern**: The plan says empty `--repo` is treated as no repo, but the current argv parser rejects an explicit empty `--repo` value before the proposed `validate_repo` call can run. Docs or tests may claim `--repo ""` falls back to the hub default, while direct users actually get a structural argv failure with no `PUBLISH_OK` stream; in-repo callers already omit empty repos via `${REPO:+--repo "$REPO"}`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-caller-compat: Keep the minimum change: document and test omitted --repo as the hub-default path, and treat explicit empty --repo as invalid/required-value exit 1 rather than changing the parser to accept it.

