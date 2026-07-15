### OOS_7: [OUT_OF_SCOPE] Deep-cap truncation ordering is intentional
- **Reviewer(s)**: dyn-dyn-runtime-evidence
- **Severity**: nit
- **Concern**: Runtime failure evidence correctly takes precedence over `DEEP_TRUNCATED`; this is not a defect.

### OOS_8: [OUT_OF_SCOPE] Same-run stale-binding validation appears sound
- **Reviewer(s)**: dyn-dyn-runtime-evidence
- **Severity**: nit
- **Concern**: The expected `(issue, cache_key, fix_sha)` binding check appears to reject stale runtime results correctly.
