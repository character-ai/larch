## Decision 1: Non-auth retry budget API surface
- **Question**: Should a new dedicated `LARCH_PROBE_RETRIES` env var control the transient non-auth retry count, or reuse `LARCH_EXTERNAL_AUTH_RETRIES`?
- **Resolution**: New `LARCH_PROBE_RETRIES` env var, default 2. Keeps auth-retry and transient-retry budgets separately configurable; avoids conflating tuning of auth retries with transient-failure resilience.
- **Source**: user

## Decision 2: Negative caching scope
- **Question**: Is enabling a non-zero default for `LARCH_PROBE_NEGATIVE_TTL_SECONDS` in scope for this fix?
- **Resolution**: Out of scope. This PR focuses solely on the bounded retry before declaring probe-failed. Negative caching is a separate follow-up, as cautioned by the issue itself.
- **Source**: user
