### FINDING_3: [OUT_OF_SCOPE] code-quality: docs/linting.md (not in diff)
[nit] make test-apply-bump description omits regression case. Docs lag harness unless updated elsewhere. Update linting.md when editing docs next.

### FINDING_4: [OUT_OF_SCOPE] correctness: .claude/skills/bump-version/scripts/classify-bump.sh:219-225
[nit] Leading-zero version segments and bash arithmetic. Unusual version strings could confuse MAJ/MIN/PAT arithmetic; pre-existing. No change required for this PR scope.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: docs/linting.md
[nit] make test-apply-bump narrative omits new regression case File not modified; central doc drifts from scripts/test-apply-bump.md case 8 Update linting doc row when convenient

