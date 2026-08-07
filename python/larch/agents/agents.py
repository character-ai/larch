# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false, reportPrivateUsage=false, reportUnusedImport=false
"""Agent launcher helpers, CLI entrypoints, and failure classification.

Implementation is split across sibling modules by responsibility:
- _types: shared types, constants, IO utilities
- _launch_failure: failure classification, model args
- _failure_diag: usage parsing, failure diagnostics
- _run_external: external agent runner, shared launcher helpers
- _auth: cursor auth, probe helpers, reviewer check, degraded tools
- _ci_launcher: CI and implement launchers
- _claude_runner: claude subprocess runner and waterfall
"""

from __future__ import annotations

# pylint: disable=W0614,W0611,W0401  # wildcard and named imports are intentional re-exports for backward compat
from larch.agents._types import *  # noqa: F403
from larch.agents._launch_failure import *  # noqa: F403
from larch.agents._failure_diag import *  # noqa: F403
from larch.agents._run_external import *  # noqa: F403
from larch.agents._auth import *  # noqa: F403
from larch.agents._ci_launcher import *  # noqa: F403
from larch.agents._claude_runner import *  # noqa: F403

# Private symbols not exported by __all__ (or no __all__) — explicit re-exports
# so callers using `from larch.agents.agents import _foo` continue to work.
from larch.agents._types import (  # noqa: F401
    _PARSE_RE,
    _REFUSAL_RE,
    _QUOTA_RE,
    _CLAUDE_AUTH_FAST_FAIL_WINDOW,
    _CLAUDE_DEGRADED_AUTH_RE,
    _CLAUDE_STDERR_SCAN_TAIL_BYTES,
    _AUTH_RE,
    _SAFE_META_PATH_RE,
    _CTRL_RE,
    _PLUGIN_ROOT,
    _PY_CLI,
    _CURSOR_AUTH_MAX_ATTEMPTS,
    _MAX_CONTEXT_FILES,
    _MAX_CLAUDE_TIMEOUT,
    _DEFAULT_CURSOR_CI_STALL_THRESHOLD,
    _TOML_CLOSED_STRING_DELIMITER_COUNT,
    _AUTH_RETRY_RC,
    _PROBE_NO_RETRY_RC,
    _SESSION_CAPTURE_FAILED_RC,
    _CURSOR_PREFLIGHT_AUTH_RC,
    _CLAUDE_REVIEW_READ_ONLY_PREAMBLE,
    _CURSOR_DEGRADED_OUTPUT_TOKEN_FLOOR,
    _CURSOR_DEGRADED_RESULT_BYTES_CEILING,
    _CURSOR_NO_WORK_INPUT_TOKEN_FLOOR,
    _err,
    _emit,
    _read_text,
    _write,
    _append,
    _parse_positive_or_zero_int,
    _is_positive_int,
    _valid_model_token,
    _validate_meta_path,
    _sanitize_tool_label,
    _json_array,
    _plugin_root,
    _env_int,
)
from larch.agents._launch_failure import (  # noqa: F401
    _fallback_launcher_exit,
    _parse_launcher_exit_value,
    _read_launcher_done,
    _launcher_failure_class_from_text,
)
from larch.agents._failure_diag import (  # noqa: F401
    _truncate_utf8_bytes,
    _failed_agent_tail_lines_default,
    _tail_redacted,
    _write_stderr_tail,
    _vendor_failure_diag_cap,
    _failure_diag_section_body,
    _compose_failure_diag,
    _review_failure_auth_paths,
    _implement_failure_auth_paths,
    _num,
    _first_not_none,
    _stderr_tail_from_less_specific_carrier,
    _failure_diagnostic_source_candidates,
)
from larch.agents._run_external import (  # noqa: F401
    _positive_int_env,
    _nonnegative_float_env,
    _cursor_ci_stall_sidecar_dir,
    _git_status_excerpt,
    _tree_latest_mtime,
    _stall_channel_progress,
    _emit_elapsed_minute_if_needed,
    _terminate_child_processes_first,
    _write_cursor_ci_stall_artifacts,
    _prepare_run_external_agent_files,
    _positive_int_ctx,
    _emit_claude_subprocess_failure_fields,
    _record_usage_from_events,
    _mirror_codex_quota_from_events,
    _CODEX_POLICY_REJECTION_TAIL_BYTES,
    _CODEX_POLICY_REJECTION_EXCERPT_BYTES,
    _CODEX_EXEC_COMMAND_FAILED_RE,
    _CODEX_POLICY_BLOCKED_RE,
    _codex_policy_rejection_excerpt,
    _read_tail_update,
    _codex_policy_watch_path,
    _stop_policy_rejected_process,
    _codex_policy_rejection_fast_fail,
    _policy_rejection_marker_present,
    _codex_env_key_enabled,
    _codex_auth_args,
    _strip_codex_config,
    _prepare_codex_home,
    _ci_failure_source,
    _resolve_execution_issues_log,
    _append_ci_failure,
    _append_vendor_failure_diagnostics,
    _write_preflight_bundle,
    _trust_config_arg,
    _git_toplevel,
    _read_keepalive_clone_path,
    _clone_path_from_session_tmpdir,
    _clone_path_from_parent_walk,
    _resolve_review_codex_workdir,
    _auth_retry_limit,
    _is_unclassified_empty_startup_failure,
    _temporary_env,
    _record_launch_timing,
    _finalize_launch,
    _post_codex_events,
    _emit_token_record_if_present,
    _record_usage_from_events_and_emit_token,
    _write_timeout_stall_json,
    _run_external_agent_with_auth_retries,
    _record_cursor_usage_from_output,
    _under,
    _promote_inner_done,
    _CODEX_REVIEW_STRICT_PREAMBLE,
    _CURSOR_SANDBOX_ENFORCEMENT_LINE,
    _CURSOR_REVIEW_STRICT_PREAMBLE,
    _REVIEW_MAX_TRANSIENT_RETRIES,
    _COLLECTOR_NS_STRONG_HEADER,
)
from larch.agents._auth import (  # noqa: F401
    _probe_tmpdir,
    _probe_user,
    _probe_stamp_path,
    _resolved_codex_review_model,
    _codex_probe_identity,
    _codex_gate_detail_path,
    _read_codex_gate_detail,
    _codex_gate_detail_max_age,
    _current_codex_gate_detail,
    _read_plugin_version_best_effort,
    resolve_model_pins,
)
from larch.agents._ci_launcher import (  # noqa: F401
    _implement_parser,
    _validate_implement_common,
    _path_under,
    _canonical_existing_nonsymlink_dir,
    _validate_codex_implement_paths,
    _hydrate_implement_session_env,
    _implement_resume_block,
    _strip_frontmatter_body,
    _implement_prompt,
    _emit_implement_launcher_envelope,
    _implement_token_budget_hit,
    _append_implement_launch_failure,
    _record_implement_timing,
    _record_cursor_implement_usage,
    _validate_lint_fix_args,
    _emit_ci_launcher_result,
    _append_implement_failure_if_nonzero,
    _safe_codex_home_dir,
)
from larch.agents._claude_runner import (  # noqa: F401
    _canonical,
    _validate_context_file,
    _validate_prompt_file,
    _validate_claude_output,
    _root_allowed_for_context,
    _read_file_tail_text,
    _run_claude_with_stdin,
    _claude_token_raw,
    _record_claude_sub_usage,
    _record_claude_ci_usage,
    _render_context_files,
    _with_claude_read_only_preamble,
    _DEFAULT_SCRIPTS_DIR,
    _TOKEN_SIDECAR_ENV_UNSET,
    LaunchFn,
)
