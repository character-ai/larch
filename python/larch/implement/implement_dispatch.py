# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnusedImport=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
# pylint: disable=unused-import
"""/implement Step 2 dispatch, recovery paths, and Step 4 commit helpers.

Re-export shim: all logic lives in the dispatch_* sibling modules.
This file preserves the original public surface for backward compatibility.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import time

from larch.issue import file_oos
from larch.implement import ship

# --- foundational helpers and primitives ---
from larch.implement.dispatch_helpers import (
    GIT_BIN,
    PORCELAIN_MIN_PARTS,
    RESUME_CAP,
    SUMMARY_BULLETS_MAX,
    WRAPPER_VALIDATION_RC,
    RecoveryParse,
    _PLUGIN_ROOT,
    _SAFE_CODERS,
    _binary_available,
    _capture_git_porcelain,
    _capture_postlaunch_porcelain,
    _capture_prelaunch_porcelain,
    _child_stdout_is_claude_fallback,
    _clone_expected_tmpdir_prefix,
    _current_cli_path,
    _derive_clone_tag_full,
    _derive_pathspec_via_recovery_paths,
    _emit_kv,
    _emit_phantom_probe_with_warn,
    _env_value,
    _err,
    _first_nonempty,
    _forward_child_output_to_stderr,
    _forward_result,
    _git,
    _git_stdout,
    _invoke_cli,
    _maybe_mark_step2_telemetry,
    _parse_kv,
    _parse_porcelain_z,
    _pwd_basename,
    _read_kv_file,
    _read_session_key_default,
    _rehydrate_larch_triplet,
    _rehydrate_plugin_root,
    _resolve_repo_root,
    _run,
    _run_cli_forward,
    _session_get,
    _step2_token_mark_eligible,
    _tmpdir_from_env,
    _tracking_sentinel_values,
    _write_bytes_atomic,
    _write_prelaunch_digests,
    _write_step2_telemetry_sentinel,
    _write_text_atomic,
)

# --- leg execution and process management ---
from larch.implement.dispatch_leg_runner import (
    CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS,
    CHECKS_DEADLINE_MS,
    CHECKS_STEP3_BG_WAIT_TIMEOUT_S,
    CHECKS_STEP5_RESUME_OUTER_TIMEOUT_MS,
    TIMING_LEDGER_MIN_COLUMNS,
    CommitRouteOutcome,
    _ACTIVE_LEG_JSON_FILE,
    _ACTIVE_LEG_PGID_FILE,
    _CHECKS_DEADLINE_MS,
    _COMMIT_ROUTE_DEADLINE_MS,
    _COMMIT_ROUTE_FAILURE_LOG_MAX,
    _COMMIT_ROUTE_SUCCESS_OUTCOMES,
    _COMPOSITE_OUTER_SLACK_MS,
    _REBASE_CHECKPOINT_DEADLINE_MS,
    _STEP5_RESUME_COMMIT_RELAY_KEYS,
    _STEP5_RESUME_DEADLINE_MS,
    _LEG_STATE,
    _LegCleanupState,
    _active_leg_pgid_path,
    _active_leg_json_path,
    _active_leg_kill_log_path,
    _clear_active_leg_pgid,
    _clear_active_leg_record,
    _descendants,
    _drain_leg_pipes,
    _finalize_leg_process,
    _install_leg_cleanup_hooks,
    _kill_active_leg,
    _kill_leg_process_group,
    _kill_leg_process_group_targets,
    _leg_signal_handler,
    _publish_active_leg_record,
    _publish_active_leg_pgid,
    _run_cli_capture,
    _run_leg_with_timeout,
    _timeout_stderr,
    _timeout_stdout,
)

# --- ship seed and step 2 post-dispatch ---
from larch.implement.dispatch_ship_seed import (
    _clear_external_dispatch_seed,
    _mark_dispatcher_committed,
    _persist_ship_seed_context,
    _read_ship_seed_lines,
    _seed_kv_nonempty,
    _upsert_seed_kv,
    _write_ship_seed_lines,
)

# --- checks relay, commit route, steps 4-6 ---
from larch.implement.dispatch_commit_route import (
    CommitRouteFailure,
    CommitRouteSite,
    _COMMIT_ROUTE_SITES,
    _STEP4_COMMIT_SITE,
    _checks_pass,
    _checks_relay_line,
    _commit_route_failure_log_path,
    _commit_route_log_failure,
    _commit_route_porcelain_gate,
    _commit_route_run,
    _commit_route_stall,
    _parse_line_anchored_commit_kv,
    _parse_whitespace_kv_line,
    _path_readable_nonempty,
    _pathspec_clean_relative_to_head,
    _read_redacted_message,
    _relay_checks_stdout,
    _relay_commit_kvs,
    _run_4r_rebase_checkpoint,
    _run_7r_rebase_checkpoint,
    _run_commit_route_leg,
    _run_relevant_checks_for_site,
    _run_step4_commit_leg,
    _run_step4_recovery_recompute,
    _seed_durable_stall_state,
    _step4_commit_failure,
    _write_commit_route_failure_log,
    checks_commit_route_main,
    commit_route_main,
)

# --- recovery paths and implement commit ---
from larch.implement.dispatch_recovery import (
    RecoveryPorcelainInputs,
    _commit_usage_fail,
    compute_recovery_paths,
    commit_main,
)

# --- manifest, DispatchState, normalize-coder-scout ---
from larch.implement.dispatch_manifest import (
    DispatchState,
    _append_materialize_oos_failure,
    _clear_external_scout_state,
    _coder_scout_archetype_count,
    _complete_schema_valid,
    _emit_manifest_invalid_or_recover,
    _json_load,
    _manifest_complete_salvageable,
    _manifest_legacy_fingerprint,
    _materialize_oos,
    _normalize_scout,
    _oos_materialize_should_bail,
    _path_under_submodule,
    _post_implementer_safety_reason,
    _sanitize_manifest_obj,
    _submodule_roots,
    _validate_manifest_paths,
    _warn_invalid_coder_scout,
    _write_coder_scout_status,
    _write_prelaunch_baseline,
    normalize_coder_scout,
)
