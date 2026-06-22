### OOS_1: [OUT_OF_SCOPE] No mechanical generator ties per-file grandfather entries to `complexity-baseline.json`
- **Description**: [OUT_OF_SCOPE] No mechanical generator ties per-file grandfather entries to `complexity-baseline.json`. Scenario: Implement-time manual transforms from one ruff JSON scan can desync `python/ruff.toml` per-file ignores and the baseline manifest; failure modes mostly catch post-hoc via CI, but regeneration remains error-prone
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/lint_complexity_baseline.py
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/5041
### OOS_3: No generation/regen entrypoint for baseline or per-file-ignore emission
- **Description**: No generation/regen entrypoint for baseline or per-file-ignore emission. Scenario: Plan requires both artifacts from one audit scan with fail-closed duplicate detection but only specifies compare-mode `main`; manual JSON/TOML transcription is error-prone on intentional debt shrink or ruff pin bumps
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/lint_complexity_baseline.py:132-141
- **Phase**: design

