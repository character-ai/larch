# test-oos-disposition-gate.sh

Delegation smoke for `oos-disposition-gate.sh` and `oos-disposition-checkpoint.sh`. Gate and checkpoint **behavior** live in `python/tests/issue/test_file_oos.py` under the `disposition_gate` pytest selector. This smoke must not re-exercise disposition logic.

## Smoke scope (both wrappers)

| Assertion | Coverage |
|-----------|----------|
| `CLAUDE_PLUGIN_ROOT` override selects `$CLAUDE_PLUGIN_ROOT/python/cli.py` | smoke |
| Repo-root fallback when `CLAUDE_PLUGIN_ROOT` is unset | smoke |
| Exact route `python/cli.py oos disposition-gate` | smoke (gate) |
| Exact route `python/cli.py oos disposition-checkpoint` | smoke (checkpoint) |
| Argument forwarding (including multi-arg) | smoke |
| Exit-status forwarding | smoke |
| Stdout / stderr passthrough unchanged | smoke |

## Assertion-parity map (former Bash harness → pytest / smoke)

| Former Bash assertion | Authority |
|-----------------------|-----------|
| fork-mode skips without full args | `test_disposition_gate_fork_mode_skips_without_full_args` |
| repo-unavailable skips | `test_disposition_gate_repo_unavailable_skips_without_full_args` |
| missing --commit-range is exit 2 | `test_disposition_gate_missing_commit_range_is_exit_2` |
| accepted path exists but is not a regular file is exit 2 | `test_disposition_gate_accepted_path_not_regular_file_is_exit_2` |
| filed URLs in oos-issues.ndjson without any accepted file path is exit 2 | `test_disposition_gate_orphan_ndjson_without_accepted_file` |
| no OOS blocks passes | `test_disposition_gate_no_oos_blocks_passes` |
| non-security OOS with filed URL passes | `test_disposition_gate_non_security_with_filed_url_passes` |
| security-only accepted block passes without URLs | `test_disposition_gate_security_only_passes_without_urls` |
| security-hardening focus-area passes without URLs | `test_disposition_gate_security_hardening_focus_area_passes_without_urls` |
| unbulleted security focus-area passes without URLs | `test_disposition_gate_unbulleted_security_focus_area_passes_without_urls` |
| python non-security counter excludes unbulleted security focus-area | same test (count assertion) |
| non-security OOS without disposition fails | `test_disposition_gate_non_security_without_disposition_fails` |
| legacy tagged FINDING header without disposition fails | `test_disposition_gate_legacy_tagged_finding_without_disposition_fails` |
| legacy trailing-tag FINDING header without disposition fails | `test_disposition_gate_legacy_trailing_tag_finding_without_disposition_fails` |
| legacy tagged FINDING header with filed URL passes | `test_disposition_gate_legacy_tagged_finding_with_filed_url_passes` |
| invalid commit-range yields exit 2 | `test_disposition_gate_invalid_commit_range_yields_exit_2` |
| description prose mentioning focus-area=security still requires disposition | `test_disposition_gate_description_prose_focus_area_security_current_classifier` (documents current shared classifier: token match → non_security=0 / exit 0) |
| rejected OOS markers in ndjson satisfy gate without URLs | `test_disposition_gate_rejected_oos_markers_in_ndjson_satisfy` |
| filed issue URL only in oos-issues ndjson passes via union | `test_disposition_gate_filed_url_only_in_ndjson_passes_via_union` |
| two OOS blocks satisfied by two inline-triage lines | `test_disposition_gate_two_oos_satisfied_by_two_inline_triage_lines` |
| two OOS entries + single filed URL passes | `test_disposition_gate_two_oos_single_filed_url_passes` |
| off-host issues URL is not counted as filed | `test_disposition_gate_off_host_issues_url_not_counted` |
| two --filed-urls-file union passes for two OOS blocks | `test_disposition_gate_two_filed_urls_file_union_passes` |
| S1 strict-file mode ignores incidental issue URL | `test_disposition_gate_s1_strict_file_ignores_incidental_issue_url` |
| S1 loose-file mode still counts incidental issue URL | `test_disposition_gate_s1_loose_file_counts_incidental_issue_url` |
| S2 two Filed URL field lines via strict-file pass | `test_disposition_gate_s2_two_filed_url_field_lines_via_strict_pass` |
| S2b strict Filed URL with trailing note passes | `test_disposition_gate_s2b_strict_filed_url_with_trailing_note_passes` |
| S3 strict plus loose union passes for two OOS blocks | `test_disposition_gate_s3_strict_plus_loose_union_passes` |
| checkpoint proceed with empty accepted OOS | `test_disposition_gate_checkpoint_proceed_with_empty_accepted_oos` |
| checkpoint proceed with filed URL | `test_disposition_gate_checkpoint_proceed_with_filed_url` |
| checkpoint disposition gap exit 1 + Tool Failures log | `test_disposition_gate_checkpoint_disposition_gap_exit_1_logs_tool_failures` |
| checkpoint legacy FINDING disposition gap + Tool Failures | `test_disposition_gate_checkpoint_legacy_finding_disposition_gap_logs_tool_failures` |
| checkpoint fork-mode skip | `test_disposition_gate_checkpoint_fork_mode_skip` |
| checkpoint repo-unavailable skip | `test_disposition_gate_checkpoint_repo_unavailable_skip` |
| checkpoint ndjson RUN_ID-keyed rejection satisfies | `test_disposition_gate_checkpoint_ndjson_run_id_keyed_rejection_satisfies` |
| checkpoint stale RUN_ID rejects foreign ndjson fallback | `test_disposition_gate_checkpoint_stale_run_id_rejects_foreign_ndjson` |
| checkpoint single ndjson find-fallback | `test_disposition_gate_checkpoint_single_ndjson_find_fallback` |
| checkpoint ambiguous ndjson exit 2 + validation log | `test_disposition_gate_checkpoint_ambiguous_ndjson_exit_2` |
| checkpoint precondition missing ndjson exit 2 | `test_disposition_gate_checkpoint_precondition_missing_ndjson_exit_2` |
| checkpoint gate validation exit 2 + gate stderr | `test_disposition_gate_checkpoint_gate_validation_exit_2_uses_gate_stderr` |
| checkpoint merge-base absent uses origin/main..HEAD | `test_disposition_gate_checkpoint_merge_base_absent_logs_origin_main_range` / `test_disposition_gate_checkpoint_uses_origin_main_when_merge_base_absent` |
| checkpoint origin/main absent uses HEAD | `test_disposition_gate_checkpoint_origin_main_absent_logs_head_range` |
| checkpoint design-tmpdir strict URL passes | `test_disposition_gate_checkpoint_design_tmpdir_strict_url_passes` |
| checkpoint design-tmpdir unresolved OOS fails | `test_disposition_gate_checkpoint_design_tmpdir_unresolved_oos_fails` |
| checkpoint design-export fallback passes | `test_disposition_gate_checkpoint_design_export_fallback_passes` |
| checkpoint design-export unresolved OOS fails | `test_disposition_gate_checkpoint_design_export_unresolved_oos_fails` |
| checkpoint missing design-tmpdir value exit 2 | `test_disposition_gate_checkpoint_missing_design_tmpdir_value_exit_2` |
| checkpoint security sidecar exit 3 + private-disposition log | `test_disposition_gate_checkpoint_security_sidecar_returns_rc3` / `test_disposition_gate_checkpoint_security_sidecar_logs_private_disposition` |
| checkpoint wrapper plugin-root / routing / argv / exit / stdio | smoke rows above |
| gate wrapper plugin-root / routing / argv / exit / stdio | smoke rows above |
| reduced Bash smoke succeeds | `test_disposition_gate_delegation_smoke_script_succeeds` |

This map contains no Bash-only behavior rows.

## Commands

```text
make test-oos-disposition-gate
make lint-bash32
shellcheck skills/implement/scripts/test-oos-disposition-gate.sh
```
