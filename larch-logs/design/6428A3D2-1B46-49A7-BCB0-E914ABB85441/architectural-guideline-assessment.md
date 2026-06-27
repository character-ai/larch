Architectural-guideline deviations (final plan):

- G-Cfg-1 (wire-literals in config.py): the new `detail_log_skipped=failure-detail-log-*` tokens are kept local to `stall_recovery.py`, matching the existing inline `failure-detail-log-invalid`. Deviate-when applies: module-private, no active cross-module consumer (confirmed: the generic token has zero active consumers). Acceptable; plan drafting may group them as a module-level Final.
- G-IO-1 (route writes through larch.io): the oversize sidecar and ledger-row writes follow the surrounding `record_escalation` convention (fd-based no-follow write for the sidecar, existing bare writes for marker/fallback) rather than larch.io helpers. The fd-based no-follow write is a deliberate symlink-safety choice (G-Py-8 re-verify is honored).
- G-Py-3 (domain types vs stringly-typed): the classifier returns a bare reason-token string; single-purpose helper, deviate-when applies.

Honored, not deviations:
- G-Py-4 (fail loudly/closed): hard_fail is preserved for total-recording failures (token validation, unsafe ledger/fallback/marker paths, canonical+fallback both failing). The optional-detail-log soft path is the sanctioned "documented, narrow degraded path the caller explicitly handles".
- G-Py-8 (re-verify postcondition): the oversize sidecar is re-verified (inside tmpdir, not a symlink, regular, within cap) before its path is recorded.
