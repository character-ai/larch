## Pieces

### Piece 1: /triage scratch-write token guard
- Scope: Extend `scripts/deny-edit-write.sh` to recognize a `triage` activation token; document the consumer in `scripts/deny-edit-write.md`; add triage-token activation, cross-token isolation, inactive, stale, repository-denial, and canonical `/tmp` allowance cases to `scripts/test-deny-edit-write.sh`. Preserves the existing fail-closed canonical `/tmp` policy and token isolation.
- Firm-headings: `### UPDATED: scripts/deny-edit-write.sh`, `### UPDATED: scripts/deny-edit-write.md`, `### UPDATED: scripts/test-deny-edit-write.sh`
- Acceptance: `bash scripts/test-deny-edit-write.sh` passes; triage token activates scratch writes only under the canonical triage temp dir; other tokens and inactive/stale states stay fail-closed.
- Dependencies: none
- Size estimate: ~80 diff lines

### Piece 2: /triage skill + helper + tests + docs/security sweep
- Scope: New `skills/triage/SKILL.md`; new `python/larch/issue/triage.py` typed mutation/verification helper; register the verb in `python/larch/cli.py`; `python/tests/issue/test_triage.py`; `scripts/test-triage-structure.sh` + `.md`; `scripts/residual-bash-paths.txt`; `Makefile` shard; `README.md`, `docs/skills.md`, `AGENTS.md`, `SECURITY.md` companion sweep.
- Firm-headings: `### NEW: skills/triage/SKILL.md`, `### NEW: python/larch/issue/triage.py`, `### UPDATED: python/larch/cli.py`, `### NEW: python/tests/issue/test_triage.py`, `### NEW: scripts/test-triage-structure.sh`, `### NEW: scripts/test-triage-structure.md`, `### UPDATED: scripts/residual-bash-paths.txt`, `### UPDATED: Makefile`, `### UPDATED: README.md`, `### UPDATED: docs/skills.md`, `### UPDATED: AGENTS.md`, `### UPDATED: SECURITY.md`
- Acceptance: `pytest python/tests/issue/test_triage.py` and `bash scripts/test-triage-structure.sh` pass; `--report-only` makes zero GitHub calls; each verdict re-verifies its mutated surface; docs/security sweep complete.
- Dependencies: blocked-by Piece 1
- Size estimate: ~1190 diff lines
