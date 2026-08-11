//! `session` environment and run-flag writer verbs.
//!
//! Each verb keeps the exit codes, stream routing, and diagnostic text its shell
//! and Python callers depend on. Ambient state — environment, home, process
//! identity — is read here, at the composition root, and passed into the core
//! rules and adapter effects explicitly.

use crate::argparse_compat::{ParsedCommandLine, parse, parse_with_flags, write_stdout};
use crate::python_verb::run_python_verb_best_effort;
use larch_adapters::{
    assert_no_symlink_ancestors, assert_no_symlink_path_or_ancestors, create_directories,
    is_allowed_session_tmpdir, is_directory, is_regular_file, lock_session_activity,
    parent_directory, publish_symlink, read_kv_raw, recover_prior_bool, recover_prior_design_value,
    remove_file_if_present, resolve_allow_missing, resolve_trusted_design_env_source,
    safe_output_parent, validate_design_tmpdir, write_confined_file, writer_target_allowed,
};
use larch_core::{
    DIFFICULTY_CHOICES, RESTORE_FINALIZE_KEYS, RUN_FLAG_KEYS, RunParams, WRITE_DESIGN_ENV_KEYS,
    WRITE_ENV_KEYS, allowed_session_roots, cleanup_cache_sessions_root, design_run_launcher_text,
    export_line, external_timeout, implement_run_launcher_text, is_bool, is_strict_run_id,
    is_valid_claude_pid, is_valid_plugin_root_value, is_valid_repo_value, is_valid_run_id,
    is_valid_session_id, kv_text, parse_bool_arg, plugin_root_env_text, posix_path_display, redact,
    restore_finalize_default, run_params_json, session_pointer_root, validate_no_newlines,
    validate_path_arg_value, validate_repo_root_value, validate_writer_keys,
};
use std::{
    env,
    ffi::{OsStr, OsString},
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    thread,
    time::Duration,
};

const WRITE_ENV_USAGE: &str = concat!(
    "usage: session write-env [--output OUTPUT] [--repo REPO]\n",
    "                         [--repo-root REPO_ROOT]\n",
    "                         [--repo-unavailable REPO_UNAVAILABLE]\n",
    "                         [--codex-present CODEX_PRESENT]\n",
    "                         [--cursor-present CURSOR_PRESENT]\n",
    "                         [--codex-available CODEX_AVAILABLE]\n",
    "                         [--cursor-available CURSOR_AVAILABLE]\n",
    "                         [--claude-binary-found CLAUDE_BINARY_FOUND]\n",
    "                         [--codex-binary-found CODEX_BINARY_FOUND]\n",
    "                         [--cursor-binary-found CURSOR_BINARY_FOUND]\n",
    "                         [--auto-mode AUTO_MODE]\n",
    "                         [--forked-target FORKED_TARGET]\n",
    "                         [--timing-ledger TIMING_LEDGER]\n",
    "                         [--token-session-id TOKEN_SESSION_ID]\n",
    "                         [--claude-source-file CLAUDE_SOURCE_FILE]\n",
    "                         [--prev-implement-tmpdir PREV_IMPLEMENT_TMPDIR]\n",
    "                         [--dynamic-archetypes DYNAMIC_ARCHETYPES]\n",
    "                         [--run-id RUN_ID]\n",
    "                         [--live-mutation-ok LIVE_MUTATION_OK]\n",
    "                         [--plugin-root-only] [--value VALUE]\n",
);
const WRITE_DESIGN_ENV_USAGE: &str = concat!(
    "usage: session write-design-env [--output OUTPUT]\n",
    "                                [--design-tmpdir DESIGN_TMPDIR]\n",
    "                                [--session-id SESSION_ID] [--run-id RUN_ID]\n",
    "                                [--codex-present CODEX_PRESENT]\n",
    "                                [--cursor-present CURSOR_PRESENT]\n",
    "                                [--codex-available CODEX_AVAILABLE]\n",
    "                                [--cursor-available CURSOR_AVAILABLE]\n",
    "                                [--codex-binary-found CODEX_BINARY_FOUND]\n",
    "                                [--cursor-binary-found CURSOR_BINARY_FOUND]\n",
    "                                [--repo REPO] [--repo-root REPO_ROOT]\n",
    "                                [--issue-number ISSUE_NUMBER]\n",
    "                                [--claude-pid CLAUDE_PID]\n",
    "                                [--claude-source-file CLAUDE_SOURCE_FILE]\n",
    "                                [--live-mutation-ok LIVE_MUTATION_OK]\n",
);
const WRITE_IMPLEMENT_ENV_USAGE: &str = concat!(
    "usage: session write-implement-env [--claude-pid CLAUDE_PID]\n",
    "                                   [--implement-tmpdir IMPLEMENT_TMPDIR]\n",
    "                                   [--cwd CWD]\n",
);
const CLEAR_IMPLEMENT_POINTER_USAGE: &str =
    "usage: session clear-implement-pointer [--claude-pid CLAUDE_PID]\n";
const PERSIST_RUN_FLAGS_USAGE: &str = concat!(
    "usage: session persist-run-flags [--implement-tmpdir IMPLEMENT_TMPDIR]\n",
    "                                 [--quick-mode QUICK_MODE]\n",
    "                                 [--no-issues NO_ISSUES]\n",
    "                                 [--force-requested FORCE_REQUESTED]\n",
    "                                 [--self-review-requested SELF_REVIEW_REQUESTED]\n",
    "                                 [--self-implement-requested SELF_IMPLEMENT_REQUESTED]\n",
    "                                 [--difficulty-override DIFFICULTY_OVERRIDE]\n",
);
const WRITE_RUN_PARAMS_USAGE: &str = concat!(
    "usage: session write-run-params [--output OUTPUT]\n",
    "                                [--partition-requested PARTITION_REQUESTED]\n",
    "                                [--brainstorm-requested BRAINSTORM_REQUESTED]\n",
    "                                [--approve-requested APPROVE_REQUESTED]\n",
    "                                [--skip-approve-requested SKIP_APPROVE_REQUESTED]\n",
    "                                [--difficulty DIFFICULTY]\n",
);
const RESTORE_FINALIZE_STATE_USAGE: &str =
    "usage: session restore-finalize-state [--implement-tmpdir IMPLEMENT_TMPDIR]\n";
const RESOLVE_TRUSTED_DESIGN_ENV_USAGE: &str = concat!(
    "usage: session resolve-trusted-design-env --session-env-path SESSION_ENV_PATH\n",
    "                                          [--claude-pid CLAUDE_PID]\n",
);

const WRITE_ENV_OPTIONS: &[&str] = &[
    "--output",
    "--repo",
    "--repo-root",
    "--repo-unavailable",
    "--codex-present",
    "--cursor-present",
    "--codex-available",
    "--cursor-available",
    "--claude-binary-found",
    "--codex-binary-found",
    "--cursor-binary-found",
    "--auto-mode",
    "--forked-target",
    "--timing-ledger",
    "--token-session-id",
    "--claude-source-file",
    "--prev-implement-tmpdir",
    "--dynamic-archetypes",
    "--run-id",
    "--live-mutation-ok",
    "--value",
];
const WRITE_DESIGN_ENV_OPTIONS: &[&str] = &[
    "--output",
    "--design-tmpdir",
    "--session-id",
    "--run-id",
    "--codex-present",
    "--cursor-present",
    "--codex-available",
    "--cursor-available",
    "--codex-binary-found",
    "--cursor-binary-found",
    "--repo",
    "--repo-root",
    "--issue-number",
    "--claude-pid",
    "--claude-source-file",
    "--live-mutation-ok",
];
/// Boolean-valued `write-env` flags, validated only when non-empty.
const WRITE_ENV_BOOLEAN_FLAGS: &[&str] = &[
    "--codex-present",
    "--cursor-present",
    "--codex-available",
    "--cursor-available",
    "--claude-binary-found",
    "--codex-binary-found",
    "--cursor-binary-found",
    "--auto-mode",
    "--live-mutation-ok",
];
/// Boolean-valued `write-design-env` flags, validated only when non-empty.
const WRITE_DESIGN_ENV_BOOLEAN_FLAGS: &[&str] = &[
    "--codex-present",
    "--cursor-present",
    "--codex-available",
    "--cursor-available",
    "--codex-binary-found",
    "--cursor-binary-found",
    "--live-mutation-ok",
];
const DESIGN_ENV_HEADER: &str = concat!(
    "#!/usr/bin/env bash\n",
    "# /design session env — generated by session_env.py. Do not edit.\n",
);
const TEST_PAUSE_BEFORE_POINTER_PUBLICATION: &str =
    "LARCH_TEST_SESSION_POINTER_PAUSE_BEFORE_PUBLICATION";
const TEST_POINTER_PUBLICATION_PAUSE_MARKER: &str = ".larch-session-pointer-publication-paused";
const TEST_POINTER_PAUSE_INTERVAL: Duration = Duration::from_millis(10);

/// Validate and atomically publish an `/implement` session-env file.
pub fn write_env(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(arguments, WRITE_ENV_OPTIONS, &["--plugin-root-only"], 0);
    if let Some(error) = parsed.error() {
        emit_usage_error(WRITE_ENV_USAGE, "session write-env", &error);
        return ExitCode::FAILURE;
    }
    finish(write_env_from_parsed(&parsed))
}

/// Run the existing session-env writer for `session setup` without emitting.
///
/// Setup publishes its ordered stdout envelope before writer diagnostics, just
/// as the former subprocess composition did.  This helper keeps the write and
/// validation owner in this module while returning that later diagnostic to
/// the setup composition root.
pub fn write_env_for_setup(arguments: &[OsString]) -> Result<(), String> {
    let parsed = parse_with_flags(arguments, WRITE_ENV_OPTIONS, &["--plugin-root-only"], 0);
    if let Some(error) = parsed.error() {
        return Err(redact(&format!(
            "{WRITE_ENV_USAGE}session write-env: error: {error}"
        ))
        .text()
        .to_owned());
    }
    write_env_from_parsed(&parsed)
        .map_err(|error| redact(&format!("ERROR={error}")).text().to_owned())
}

fn write_env_from_parsed(parsed: &ParsedCommandLine) -> Result<(), String> {
    let output = text(parsed.value("--output"));
    if output.is_empty() {
        return Err(MISSING_WRITE_ENV_ARGUMENTS.to_owned());
    }
    let out_path = PathBuf::from(&output);
    if parsed.flag("--plugin-root-only") {
        let value = text(parsed.value("--value"));
        if !is_valid_plugin_root_value(&value) {
            return Ok(());
        }
        return write_plugin_root_env(&out_path, &value);
    }
    let rows = write_env_rows(parsed)?;
    validate_writer_keys(&rows, &WRITE_ENV_KEYS)?;
    validate_no_newlines(&rows)?;
    if output == "/dev/null" {
        return Ok(());
    }
    confirm_writable_session_target(&out_path, &output)?;
    write_confined_file(&out_path, &render_kv(&rows)?, 0o600, "session-env")?;
    // The sidecar is written only when the row set carries a plugin root,
    // which is exactly when the environment supplied a valid one.
    let Some((_key, plugin_root)) = rows
        .iter()
        .find(|(key, _value)| *key == "LARCH_CLAUDE_PLUGIN_ROOT")
    else {
        return Ok(());
    };
    write_plugin_root_env(
        &parent_directory(&out_path).join("plugin-root.env"),
        plugin_root,
    )
}

/// Validate every `write-env` flag and compose its rows in wire order.
fn write_env_rows(parsed: &ParsedCommandLine) -> Result<Vec<(&'static str, String)>, String> {
    let flag = |name: &str| text(parsed.value(name));
    let Some(repo_unavailable) = parsed.value("--repo-unavailable").map(text_of) else {
        return Err(MISSING_WRITE_ENV_ARGUMENTS.to_owned());
    };
    for name in WRITE_ENV_BOOLEAN_FLAGS {
        let value = flag(name);
        if !value.is_empty() {
            parse_bool_arg(&value, name)?;
        }
    }
    let forked_target = parsed
        .value("--forked-target")
        .map_or_else(|| "false".to_owned(), text_of);
    parse_bool_arg(&forked_target, "--forked-target")?;
    let token_session_id = flag("--token-session-id");
    if !token_session_id.is_empty() && !is_valid_session_id(&token_session_id) {
        return Err("Invalid --token-session-id: must match ^[A-Za-z0-9_.-]{1,128}$".to_owned());
    }
    let claude_source_file = flag("--claude-source-file");
    let timing_ledger = flag("--timing-ledger");
    validate_path_arg_value(&claude_source_file, "--claude-source-file")?;
    validate_path_arg_value(&timing_ledger, "--timing-ledger")?;
    let prev_implement_tmpdir = flag("--prev-implement-tmpdir");
    if !prev_implement_tmpdir.is_empty() {
        validate_path_arg_value(&prev_implement_tmpdir, "--prev-implement-tmpdir")?;
        if !prev_implement_tmpdir.starts_with('/') {
            return Err("Invalid --prev-implement-tmpdir: must be an absolute path".to_owned());
        }
    }
    // `CLAUDE_PLUGIN_ROOT` is validated here, between the path flags and the
    // remaining value flags, exactly where the legacy writer validated it.
    let plugin_root = validated_plugin_root()?;
    let dynamic_archetypes = flag("--dynamic-archetypes");
    if !dynamic_archetypes.is_empty() && dynamic_archetypes != "0" && dynamic_archetypes != "1" {
        return Err("Invalid --dynamic-archetypes: must be an integer from 0 to 1".to_owned());
    }
    let run_id = flag("--run-id");
    if !run_id.is_empty() && !is_valid_run_id(&run_id) {
        return Err(INVALID_RUN_ID.to_owned());
    }
    let mut rows: Vec<(&str, String)> = vec![
        ("REPO", flag("--repo")),
        ("REPO_UNAVAILABLE", repo_unavailable),
        ("FORKED_TARGET", forked_target),
        ("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", health_timeout()),
    ];
    for (key, value) in [
        ("CLAUDE_BINARY_FOUND", flag("--claude-binary-found")),
        ("CODEX_BINARY_FOUND", flag("--codex-binary-found")),
        ("CURSOR_BINARY_FOUND", flag("--cursor-binary-found")),
        ("LARCH_AUTO_MODE", flag("--auto-mode")),
        ("LARCH_TIMING_LEDGER", timing_ledger),
        ("LARCH_TOKEN_SESSION_ID", token_session_id),
        ("LARCH_CLAUDE_SOURCE_FILE", claude_source_file),
        ("PREV_IMPLEMENT_TMPDIR", prev_implement_tmpdir),
        ("LARCH_DYNAMIC_ARCHETYPES_MAX", dynamic_archetypes),
        ("LARCH_RUN_ID", run_id),
        ("LARCH_LIVE_MUTATION_OK", flag("--live-mutation-ok")),
        (
            "REPO_ROOT",
            resolve_write_env_repo_root(&flag("--repo-root"))?,
        ),
        ("LARCH_CLAUDE_PLUGIN_ROOT", plugin_root),
    ] {
        if !value.is_empty() {
            rows.push((key, value));
        }
    }
    Ok(rows)
}

/// Validate and atomically publish a `/design` session-env file and its pointer.
pub fn write_design_env(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(arguments, WRITE_DESIGN_ENV_OPTIONS, 0);
    if let Some(error) = parsed.error() {
        emit_usage_error(WRITE_DESIGN_ENV_USAGE, "session write-design-env", &error);
        return ExitCode::FAILURE;
    }
    let claude_pid = text(parsed.value("--claude-pid"));
    let result = (|| -> Result<(), String> {
        let out_path = validated_design_target(&parsed)?;
        let plugin_root = validated_plugin_root()?;
        if !claude_pid.is_empty() && plugin_root.is_empty() {
            return Err("Missing CLAUDE_PLUGIN_ROOT: required when --claude-pid is set".to_owned());
        }
        let rows = design_env_rows(&parsed, arguments, &out_path, &plugin_root)?;
        validate_writer_keys(&rows, &WRITE_DESIGN_ENV_KEYS)?;
        validate_no_newlines(&rows)?;
        let mut rendered = DESIGN_ENV_HEADER.to_owned();
        for (key, value) in &rows {
            rendered.push_str(&export_line(key, value));
        }
        write_confined_file(&out_path, &rendered, 0o600, "design session-env")?;
        let pointer_root = sessions_directory();
        let _activity_lock = lock_session_activity(&pointer_root)?;
        test_pause_before_pointer_publication(&pointer_root)?;
        if !is_regular_file(&out_path) {
            return Err(
                "design session-env target disappeared before pointer publication".to_owned(),
            );
        }
        let pointer = design_pointer_path(&claude_pid);
        if claude_pid.is_empty() {
            breadcrumb(
                "WARNING=write-design-current-env.sh: --claude-pid omitted; using legacy current-design-env.sh symlink (transition shim; pass --claude-pid)",
            );
        }
        assert_no_symlink_ancestors(&pointer)?;
        create_directories(&parent_directory(&pointer))?;
        publish_symlink(&pointer, &out_path, std::process::id())?;
        if claude_pid.is_empty() {
            return Ok(());
        }
        write_design_run_script(&claude_pid, &plugin_root)
    })();
    finish(result)
}

/// Validate every `write-design-env` flag and return its confined output path.
fn validated_design_target(parsed: &ParsedCommandLine) -> Result<PathBuf, String> {
    let flag = |name: &str| text(parsed.value(name));
    let output = flag("--output");
    let design_tmpdir = flag("--design-tmpdir");
    let session_id = flag("--session-id");
    if output.is_empty() || design_tmpdir.is_empty() || session_id.is_empty() {
        return Err(
            "Missing required arguments: --output, --design-tmpdir, --session-id".to_owned(),
        );
    }
    for name in WRITE_DESIGN_ENV_BOOLEAN_FLAGS {
        let value = flag(name);
        if !value.is_empty() {
            parse_bool_arg(&value, name)?;
        }
    }
    let issue_number = flag("--issue-number");
    if !issue_number.is_empty() && !issue_number.chars().all(|digit| digit.is_ascii_digit()) {
        return Err("Invalid --issue-number: must be a non-negative integer".to_owned());
    }
    if !is_valid_repo_value(&flag("--repo")) {
        return Err("Invalid --repo: must match OWNER/REPO".to_owned());
    }
    if !is_valid_session_id(&session_id) {
        return Err("Invalid --session-id: must match ^[A-Za-z0-9_.-]{1,128}$".to_owned());
    }
    let claude_pid = flag("--claude-pid");
    if !claude_pid.is_empty() && !is_valid_claude_pid(&claude_pid) {
        return Err(INVALID_CLAUDE_PID.to_owned());
    }
    validate_path_arg_value(&flag("--claude-source-file"), "--claude-source-file")?;
    validate_design_tmpdir(
        &design_tmpdir,
        env::var_os("TMPDIR").as_deref(),
        &cache_sessions_root(),
    )?;
    let out_path = PathBuf::from(&output);
    if !out_path.is_absolute() {
        return Err("Invalid --output: must be an absolute path".to_owned());
    }
    confirm_writable_session_target(&out_path, &out_path.display().to_string())?;
    Ok(out_path)
}

/// Compose the design session-env rows, recovering prior values as the legacy writer did.
fn design_env_rows(
    parsed: &ParsedCommandLine,
    arguments: &[OsString],
    out_path: &Path,
    plugin_root: &str,
) -> Result<Vec<(&'static str, String)>, String> {
    let flag = |name: &str| text(parsed.value(name));
    let design_tmpdir = flag("--design-tmpdir");
    let mut rows: Vec<(&str, String)> = vec![
        ("DESIGN_TMPDIR", design_tmpdir.clone()),
        ("SESSION_TMPDIR", design_tmpdir),
        ("SESSION_ID", flag("--session-id")),
    ];
    let repo = flag("--repo");
    if !repo.is_empty() {
        rows.push(("REPO", repo));
    }
    let mut repo_root = flag("--repo-root").trim().to_owned();
    if repo_root.is_empty() {
        repo_root = recover_prior_design_value(out_path, "REPO_ROOT")?;
    }
    if repo_root.is_empty() {
        repo_root = fallback_repo_root();
    }
    if !repo_root.is_empty() {
        validate_repo_root_value(&repo_root, "--repo-root")?;
        rows.push(("REPO_ROOT", repo_root));
    }
    let issue_number = flag("--issue-number");
    if !issue_number.is_empty() {
        rows.push(("ISSUE_NUMBER", issue_number));
    }
    let mut run_id = flag("--run-id").trim().to_owned();
    if run_id.is_empty() {
        run_id = recover_prior_design_value(out_path, "LARCH_RUN_ID")?;
    }
    if !run_id.is_empty() {
        if !is_strict_run_id(&run_id) {
            return Err(INVALID_RUN_ID.to_owned());
        }
        rows.push(("LARCH_RUN_ID", run_id));
    }
    for (key, name) in [
        ("CODEX_BINARY_FOUND", "--codex-binary-found"),
        ("CURSOR_BINARY_FOUND", "--cursor-binary-found"),
    ] {
        // An explicitly supplied empty value clears the key; only an omitted
        // flag recovers whatever the prior env file recorded.
        let mut value = flag(name);
        if value.is_empty() && !arguments.iter().any(|argument| argument == name) {
            value = recover_prior_bool(out_path, key)?;
        }
        if !value.is_empty() {
            parse_bool_arg(&value, name)?;
            rows.push((key, value));
        }
    }
    rows.push(("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", health_timeout()));
    let claude_source_file = flag("--claude-source-file");
    if !claude_source_file.is_empty() {
        rows.push(("LARCH_CLAUDE_SOURCE_FILE", claude_source_file));
    }
    if !plugin_root.is_empty() {
        rows.push(("CLAUDE_PLUGIN_ROOT", plugin_root.to_owned()));
    }
    let live_mutation_ok = flag("--live-mutation-ok");
    if !live_mutation_ok.is_empty() {
        rows.push(("LARCH_LIVE_MUTATION_OK", live_mutation_ok));
    } else if is_regular_file(out_path)
        && recover_prior_design_value(out_path, "LARCH_LIVE_MUTATION_OK")? == "true"
    {
        rows.push(("LARCH_LIVE_MUTATION_OK", "true".to_owned()));
    }
    Ok(rows)
}

/// Publish the PID-keyed `/implement` current-env pointer and stable launcher.
pub fn write_implement_env(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(
        arguments,
        &["--claude-pid", "--implement-tmpdir", "--cwd"],
        0,
    );
    if let Some(error) = parsed.error() {
        emit_usage_error(
            WRITE_IMPLEMENT_ENV_USAGE,
            "session write-implement-env",
            &error,
        );
        return ExitCode::FAILURE;
    }
    let claude_pid = text(parsed.value("--claude-pid"));
    let implement_tmpdir = text(parsed.value("--implement-tmpdir"));
    let working_directory = text(parsed.value("--cwd"));
    let result = (|| -> Result<(), String> {
        if !is_valid_claude_pid(&claude_pid) {
            return Err(INVALID_CLAUDE_PID.to_owned());
        }
        let tmpdir = PathBuf::from(&implement_tmpdir);
        if !tmpdir.is_absolute() || !is_directory(&tmpdir) {
            return Err(
                "Invalid --implement-tmpdir: must be an existing absolute directory".to_owned(),
            );
        }
        if !is_allowed_session_tmpdir(&tmpdir, &allowed_roots()) {
            return Err(format!(
                "implement-tmpdir: path must be under /tmp/, /private/tmp/, /var/folders/, or {}/",
                cache_sessions_root().display()
            ));
        }
        let cwd_path = PathBuf::from(&working_directory);
        if !cwd_path.is_absolute() {
            return Err("Invalid --cwd: must be an absolute path".to_owned());
        }
        let repo_cwd = resolve_allow_missing(&cwd_path)
            .unwrap_or(cwd_path)
            .display()
            .to_string();
        let rows: Vec<(&str, String)> = vec![
            ("IMPLEMENT_TMPDIR", tmpdir.display().to_string()),
            ("REPO_CWD", repo_cwd),
            ("SKILL_KIND", "implement".to_owned()),
        ];
        validate_no_newlines(&rows)?;
        let pointer_root = sessions_directory();
        let _activity_lock = lock_session_activity(&pointer_root)?;
        test_pause_before_pointer_publication(&pointer_root)?;
        if !is_directory(&tmpdir) || !is_allowed_session_tmpdir(&tmpdir, &allowed_roots()) {
            return Err(
                "Invalid --implement-tmpdir: directory disappeared before pointer publication"
                    .to_owned(),
            );
        }
        let pointer = implement_pointer_path(&claude_pid);
        assert_no_symlink_path_or_ancestors(&pointer)?;
        create_directories(&parent_directory(&pointer))?;
        assert_no_symlink_path_or_ancestors(&pointer)?;
        write_confined_file(&pointer, &render_kv(&rows)?, 0o600, "implement pointer")?;
        let launcher = sessions_directory().join(format!("implement-run-{claude_pid}.sh"));
        assert_no_symlink_path_or_ancestors(&launcher)?;
        write_confined_file(
            &launcher,
            &implement_run_launcher_text(&claude_pid),
            0o755,
            "implement launcher",
        )
    })();
    finish(result)
}

/// Remove the PID-keyed `/implement` current-env pointer.
pub fn clear_implement_pointer(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(arguments, &["--claude-pid"], 0);
    if let Some(error) = parsed.error() {
        emit_usage_error(
            CLEAR_IMPLEMENT_POINTER_USAGE,
            "session clear-implement-pointer",
            &error,
        );
        return ExitCode::FAILURE;
    }
    let claude_pid = text(parsed.value("--claude-pid"));
    let result = if is_valid_claude_pid(&claude_pid) {
        lock_session_activity(&sessions_directory())
            .and_then(|_activity_lock| remove_file_if_present(&implement_pointer_path(&claude_pid)))
    } else {
        Err(INVALID_CLAUDE_PID.to_owned())
    };
    finish(result)
}

/// Persist validated `/implement` run flags beside the session tmpdir.
pub fn persist_run_flags(arguments: &[OsString]) -> ExitCode {
    let options: &[&str] = &[
        "--implement-tmpdir",
        "--quick-mode",
        "--no-issues",
        "--force-requested",
        "--self-review-requested",
        "--self-implement-requested",
        "--difficulty-override",
    ];
    let parsed = parse(arguments, options, 0);
    if let Some(error) = parsed.error() {
        emit_usage_error(PERSIST_RUN_FLAGS_USAGE, "session persist-run-flags", &error);
        // The legacy verb caught argparse's SystemExit and reported its code.
        eprintln!("persist-implement-run-flags.sh: 2");
        return ExitCode::from(2);
    }
    let value = |name: &str, fallback: &str| {
        parsed
            .value(name)
            .map_or_else(|| fallback.to_owned(), text_of)
    };
    let result = (|| -> Result<(), String> {
        // `Path("")` is `.` in Python, so an omitted tmpdir reaches the
        // containment check as the working directory rather than failing early.
        let tmpdir = PathBuf::from(match value("--implement-tmpdir", "").as_str() {
            "" => ".".to_owned(),
            supplied => supplied.to_owned(),
        });
        if !is_directory(&tmpdir) {
            return Err("--implement-tmpdir not a directory".to_owned());
        }
        let rows: Vec<(&str, String)> = vec![
            ("QUICK_MODE", value("--quick-mode", "false")),
            ("NO_ISSUES", value("--no-issues", "")),
            ("FORCE_REQUESTED", value("--force-requested", "false")),
            (
                "SELF_REVIEW_REQUESTED",
                value("--self-review-requested", "false"),
            ),
            (
                "SELF_IMPLEMENT_REQUESTED",
                value("--self-implement-requested", "false"),
            ),
            ("DIFFICULTY_OVERRIDE", value("--difficulty-override", "")),
        ];
        for (key, supplied) in rows.iter().take(5) {
            if !is_bool(supplied) {
                return Err(format!(
                    "--{} must be true or false",
                    key.to_lowercase().replace('_', "-")
                ));
            }
        }
        let difficulty = &rows[5].1;
        if !difficulty.is_empty() && !DIFFICULTY_CHOICES.contains(&difficulty.as_str()) {
            return Err(
                "--difficulty-override must be empty, TRIVIAL, MODERATE, or HARD".to_owned(),
            );
        }
        let target = tmpdir.join("run-flags.sh");
        confirm_writable_session_target(&target, &target.display().to_string())?;
        validate_writer_keys(&rows, &RUN_FLAG_KEYS)?;
        validate_no_newlines(&rows)?;
        write_confined_file(&target, &render_kv(&rows)?, 0o600, "run-flags")
    })();
    match result {
        Ok(()) => write_stdout("RUN_FLAGS_PERSISTED=true\n"),
        Err(error) => {
            eprintln!("persist-implement-run-flags.sh: {error}");
            ExitCode::from(2)
        }
    }
}

/// Write the schema v3 `/design` run-params document.
pub fn write_run_params(arguments: &[OsString]) -> ExitCode {
    let options: &[&str] = &[
        "--output",
        "--partition-requested",
        "--brainstorm-requested",
        "--approve-requested",
        "--skip-approve-requested",
        "--difficulty",
    ];
    let parsed = parse(arguments, options, 0);
    if let Some(error) = parsed.error() {
        emit_usage_error(WRITE_RUN_PARAMS_USAGE, "session write-run-params", &error);
        return ExitCode::from(2);
    }
    let flag = |name: &str| text(parsed.value(name));
    let mut directory_missing = false;
    let result = (|| -> Result<(), String> {
        let output = flag("--output");
        if output.is_empty() {
            return Err("missing required flag: --output".to_owned());
        }
        for name in [
            "--partition-requested",
            "--brainstorm-requested",
            "--approve-requested",
            "--skip-approve-requested",
        ] {
            if !arguments.iter().any(|argument| argument == name) {
                continue;
            }
            let value = flag(name);
            if value.is_empty() {
                return Err(format!("invalid {name}: requires a value"));
            }
            if !is_bool(&value) {
                return Err(format!("invalid {name}: {value}"));
            }
        }
        let difficulty = flag("--difficulty");
        if !difficulty.is_empty() && !DIFFICULTY_CHOICES.contains(&difficulty.as_str()) {
            return Err(format!("invalid --difficulty: {difficulty}"));
        }
        let out_path = PathBuf::from(&output);
        if !out_path.is_absolute() {
            return Err(format!("--output must be absolute: {output}"));
        }
        if !writer_target_allowed(&out_path, &allowed_roots()) {
            return Err(format!(
                "output path not under allowed session root: {output}"
            ));
        }
        let parent = parent_directory(&out_path);
        if !is_directory(&parent) {
            directory_missing = true;
            return Err(format!(
                "write-run-params.sh: output directory not found: {}",
                parent.display()
            ));
        }
        if !safe_output_parent(&out_path) {
            return Err(format!(
                "output parent is not a writable directory: {}",
                parent.display()
            ));
        }
        write_confined_file(
            &out_path,
            &run_params_json(RunParams {
                partition_requested: flag("--partition-requested") == "true",
                brainstorm_requested: flag("--brainstorm-requested") == "true",
                approve_requested: flag("--approve-requested") == "true",
                skip_approve_requested: flag("--skip-approve-requested") == "true",
                difficulty_override: &difficulty,
            }),
            0o600,
            "run-params",
        )
    })();
    match result {
        Ok(()) => write_stdout(&format!(
            "RUN_PARAMS_WRITTEN={}\n",
            posix_path_display(&flag("--output"))
        )),
        Err(error) if directory_missing => {
            breadcrumb(&error);
            ExitCode::FAILURE
        }
        Err(error) => {
            breadcrumb(&format!("write-run-params.sh: {error}"));
            ExitCode::from(2)
        }
    }
}

/// Rebuild `finalize-state.sh` from the durable ship-pr state file.
pub fn restore_finalize_state(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(arguments, &["--implement-tmpdir"], 0);
    if let Some(error) = parsed.error() {
        emit_usage_error(
            RESTORE_FINALIZE_STATE_USAGE,
            "session restore-finalize-state",
            &error,
        );
        // The legacy verb caught argparse's SystemExit and reported its code.
        eprintln!("restore-finalize-state.sh: 2");
        return ExitCode::from(2);
    }
    let supplied = text(parsed.value("--implement-tmpdir"));
    let tmpdir = PathBuf::from(&supplied);
    if let Err(error) = validate_restore_tmpdir(&supplied, &tmpdir) {
        eprintln!("restore-finalize-state.sh: {error}");
        return ExitCode::from(2);
    }
    let state_file = tmpdir.join("ship-pr-state.sh");
    let finalize_file = tmpdir.join("finalize-state.sh");
    let bail_reason_file = tmpdir.join("final-bail-reason.txt");
    if !is_regular_file(&state_file) {
        eprintln!(
            "restore-finalize-state.sh: warning: missing ship-pr state file: {}",
            state_file.display()
        );
        return ExitCode::FAILURE;
    }
    let result = (|| -> Result<String, String> {
        let state = read_kv_raw(&state_file).map_err(|error| format!("{error}"))?;
        let existing = read_kv_raw(&finalize_file).map_err(|error| format!("{error}"))?;
        let lookup = |rows: &[(String, String)], key: &str| {
            rows.iter()
                .find(|(name, _value)| name == key)
                .map_or_else(String::new, |(_name, value)| value.clone())
        };
        let keep_stall = lookup(&existing, "STALL_TRACKING") == "true";
        let existing_stall_step = lookup(&existing, "STALL_STEP");
        let mut rows: Vec<(&str, String)> = Vec::with_capacity(RESTORE_FINALIZE_KEYS.len());
        for key in RESTORE_FINALIZE_KEYS {
            let mut value = lookup(&state, key);
            if keep_stall {
                if key == "STALL_TRACKING" {
                    "true".clone_into(&mut value);
                } else if key == "STALL_STEP" && !existing_stall_step.is_empty() {
                    value.clone_from(&existing_stall_step);
                }
            }
            if value.is_empty() {
                value = match lookup(&existing, key) {
                    recovered if recovered.is_empty() => restore_finalize_default(key).to_owned(),
                    recovered => recovered,
                };
            }
            rows.push((key, value));
        }
        validate_no_newlines(&rows)?;
        write_confined_file(&finalize_file, &render_kv(&rows)?, 0o600, "finalize-state")?;
        let bail_reason = lookup(&state, "BAIL_REASON");
        create_directories(&tmpdir)?;
        write_confined_file(&bail_reason_file, &bail_reason, 0o600, "bail reason")?;
        Ok(if bail_reason.is_empty() {
            String::new()
        } else {
            lookup(&state, "RUN_ID")
        })
    })();
    match result {
        Ok(run_id) => {
            if !run_id.is_empty() {
                record_bail_reason(&tmpdir, &run_id, &bail_reason_file);
            }
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("restore-finalize-state.sh: {error}");
            ExitCode::FAILURE
        }
    }
}

/// Resolve a PID-keyed design session-env symlink to a trusted regular file.
pub fn resolve_trusted_design_env(arguments: &[OsString]) -> ExitCode {
    let parsed = parse(arguments, &["--session-env-path", "--claude-pid"], 0);
    // `argparse` reports a missing required option before any unrecognized ones.
    let Some(session_env_path) = parsed.value("--session-env-path").map(text_of) else {
        emit_usage_error(
            RESOLVE_TRUSTED_DESIGN_ENV_USAGE,
            "session resolve-trusted-design-env",
            "the following arguments are required: --session-env-path",
        );
        return ExitCode::from(2);
    };
    if let Some(error) = parsed.error() {
        emit_usage_error(
            RESOLVE_TRUSTED_DESIGN_ENV_USAGE,
            "session resolve-trusted-design-env",
            &error,
        );
        return ExitCode::from(2);
    }
    let claude_pid = text(parsed.value("--claude-pid"));
    if !claude_pid.is_empty() && !is_valid_claude_pid(&claude_pid) {
        eprintln!("{INVALID_CLAUDE_PID}");
        return ExitCode::from(2);
    }
    if claude_pid.is_empty() {
        return ExitCode::FAILURE;
    }
    let path = PathBuf::from(&session_env_path);
    if path != design_pointer_path(&claude_pid) {
        return ExitCode::FAILURE;
    }
    resolve_trusted_design_env_source(&path).map_or(ExitCode::FAILURE, |resolved| {
        write_stdout(&format!("TRUSTED_SOURCE={}\n", resolved.display()))
    })
}

const MISSING_WRITE_ENV_ARGUMENTS: &str =
    "Missing required arguments: --output, --repo-unavailable";
const INVALID_RUN_ID: &str = "Invalid --run-id: must match ^[A-Za-z0-9._-]{1,128}$";
const INVALID_CLAUDE_PID: &str =
    "Invalid --claude-pid: must be a positive integer of at most 7 decimal digits";

fn validate_restore_tmpdir(supplied: &str, tmpdir: &Path) -> Result<(), String> {
    if supplied.is_empty() {
        return Err("--implement-tmpdir is required".to_owned());
    }
    if !is_directory(tmpdir) {
        return Err("--implement-tmpdir must exist".to_owned());
    }
    if !writer_target_allowed(tmpdir, &allowed_roots()) {
        return Err(format!(
            "--implement-tmpdir not under allowed session root: {}",
            tmpdir.display()
        ));
    }
    Ok(())
}

/// Record the durable bail reason through the still-Python run-log writer.
///
/// Best effort by design, matching the legacy verb: the run-log append is
/// observability, and a failure must not fail the state restore that preceded
/// it. This delegation retires when `run-log write` becomes Rust-owned (#7683).
fn record_bail_reason(tmpdir: &Path, run_id: &str, bail_reason_file: &Path) {
    run_python_verb_best_effort([
        OsString::from("run-log"),
        OsString::from("write"),
        OsString::from("--log-root"),
        tmpdir.join("larch-logs").into_os_string(),
        OsString::from("--skill"),
        OsString::from("implement"),
        OsString::from("--run-id"),
        OsString::from(run_id),
        OsString::from("--batch"),
        OsString::from("final-bail-reason"),
        OsString::from("--input-file"),
        bail_reason_file.as_os_str().to_os_string(),
    ]);
}

fn write_plugin_root_env(output: &Path, value: &str) -> Result<(), String> {
    if value.is_empty() || !is_valid_plugin_root_value(value) {
        return Ok(());
    }
    let parent = parent_directory(output);
    if !is_directory(&parent) {
        return Err(format!(
            "plugin-root.env parent is not a directory: {}",
            parent.display()
        ));
    }
    write_confined_file(
        output,
        &plugin_root_env_text(value),
        0o600,
        "plugin-root.env",
    )
}

fn write_design_run_script(pid: &str, plugin_root: &str) -> Result<(), String> {
    let launcher = sessions_directory().join(format!("design-run-{pid}.sh"));
    create_directories(&parent_directory(&launcher))?;
    assert_no_symlink_path_or_ancestors(&launcher)?;
    write_confined_file(
        &launcher,
        &design_run_launcher_text(pid, plugin_root),
        0o755,
        "design launcher",
    )
}

/// Read the external health-check timeout override from the environment.
fn health_timeout() -> String {
    external_timeout(
        env::var("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT")
            .ok()
            .as_deref(),
    )
}

/// Read and validate `CLAUDE_PLUGIN_ROOT`, which both writers persist.
fn validated_plugin_root() -> Result<String, String> {
    let plugin_root = environment_value("CLAUDE_PLUGIN_ROOT");
    if !plugin_root.is_empty() && !is_valid_plugin_root_value(&plugin_root) {
        return Err(
            "Invalid CLAUDE_PLUGIN_ROOT: must be an absolute path matching ^[A-Za-z0-9_./~+-]{1,512}$"
                .to_owned(),
        );
    }
    Ok(plugin_root)
}

fn confirm_writable_session_target(target: &Path, reported: &str) -> Result<(), String> {
    if !writer_target_allowed(target, &allowed_roots()) {
        return Err(format!(
            "output path not under allowed session root: {reported}"
        ));
    }
    if !safe_output_parent(target) {
        return Err(format!(
            "output parent is not a writable directory: {}",
            parent_directory(target).display()
        ));
    }
    Ok(())
}

fn resolve_write_env_repo_root(explicit: &str) -> Result<String, String> {
    let mut repo_root = explicit.trim().to_owned();
    if repo_root.is_empty() {
        repo_root = fallback_repo_root();
    }
    validate_repo_root_value(&repo_root, "--repo-root")?;
    Ok(repo_root)
}

fn fallback_repo_root() -> String {
    let project_directory = environment_value("CLAUDE_PROJECT_DIR").trim().to_owned();
    if project_directory.is_empty() {
        environment_value("REPO_ROOT").trim().to_owned()
    } else {
        project_directory
    }
}

fn render_kv(rows: &[(&str, String)]) -> Result<String, String> {
    let borrowed = rows
        .iter()
        .map(|(key, value)| (*key, value.as_str()))
        .collect::<Vec<_>>();
    kv_text(&borrowed).map_err(|error| format!("{error}"))
}

fn sessions_directory() -> PathBuf {
    session_pointer_root(env::var_os("HOME").as_deref())
}

/// Expose a deterministic publication boundary for race tests while holding
/// the same lease cleanup uses. Normal callers never enter this branch.
fn test_pause_before_pointer_publication(pointer_root: &Path) -> Result<(), String> {
    if env::var(TEST_PAUSE_BEFORE_POINTER_PUBLICATION).as_deref() != Ok("true") {
        return Ok(());
    }
    let marker = pointer_root.join(TEST_POINTER_PUBLICATION_PAUSE_MARKER);
    write_confined_file(
        &marker,
        "paused\n",
        0o600,
        "session pointer publication test marker",
    )?;
    while fs::symlink_metadata(&marker).is_ok() {
        thread::sleep(TEST_POINTER_PAUSE_INTERVAL);
    }
    Ok(())
}

fn design_pointer_path(pid: &str) -> PathBuf {
    sessions_directory().join(if pid.is_empty() {
        "current-design-env.sh".to_owned()
    } else {
        format!("current-design-env-{pid}.sh")
    })
}

fn implement_pointer_path(pid: &str) -> PathBuf {
    sessions_directory().join(format!("current-implement-env-{pid}.sh"))
}

fn cache_sessions_root() -> PathBuf {
    cleanup_cache_sessions_root(
        env::var_os("XDG_CACHE_HOME").as_deref(),
        env::var_os("HOME").as_deref(),
    )
}

fn allowed_roots() -> [PathBuf; 5] {
    allowed_session_roots(
        env::var_os("XDG_CACHE_HOME").as_deref(),
        env::var_os("HOME").as_deref(),
    )
}

fn environment_value(key: &str) -> String {
    env::var(key).unwrap_or_default()
}

fn text(value: Option<&OsStr>) -> String {
    value.map(text_of).unwrap_or_default()
}

fn text_of(value: &OsStr) -> String {
    value.to_string_lossy().into_owned()
}

/// Report a writer failure on the breadcrumb stream, redacted as the writer redacts.
fn breadcrumb(message: &str) {
    eprintln!("{}", redact(message).text());
}

fn finish(result: Result<(), String>) -> ExitCode {
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            breadcrumb(&format!("ERROR={error}"));
            ExitCode::FAILURE
        }
    }
}

/// Reproduce the two-line `argparse` usage-error block on stderr.
fn emit_usage_error(usage: &str, program: &str, error: &str) {
    eprintln!("{usage}{program}: error: {error}");
}
