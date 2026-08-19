//! Rust owners for the `/implement` Step 18 and Step 19 finalization
//! checkpoints: `step-18`, `step-18-gate-logs-flush`, and `step-19`.
//!
//! The stall gate, the terminal logs flush, run-log terminalization, and the
//! teardown forward all keep their exact `KEY=value` grammars, exit codes, and
//! wire files. Sibling Rust verbs stay child processes through the verified
//! `scripts/larch.sh` bootstrap; `implement-finalize teardown` is still
//! Python-owned and is reached through the one `python_verb` seam.

use std::{
    collections::BTreeMap,
    env,
    ffi::OsString,
    fs,
    io::Write as _,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use larch_adapters::{
    absolute_lexical, assert_no_symlink_path_or_ancestors,
    stall_recovery::abandoned_checks_stall_step, write_confined_file,
};
use larch_core::{
    ChildEnvironment, DuplicatePolicy, KvDocument, ParseOptions, ProcessOutput,
    implement::first_kv_value, parse_preterminal_outcome_label, split_one_shell_token,
};

use crate::{
    argparse_compat::{choice_error, parse_required_with_help, usage_error},
    implement_child_seam::resolve_plugin_root,
    implement_dispatch_commands::{opt_string, rehydrate_session, run_verified_larch_env_in},
    python_verb::run_python_verb,
    run_log_entry_commands::append_execution_issue,
};

const STEP18_PROG: &str = "cli.py implement step-18";
const STEP18_USAGE: &str = "usage: cli.py implement step-18 [-h] [--phase {gate,logs-flush}]\n                                [--stall-tracking-memory STALL_TRACKING_MEMORY]\n                                [--step17-emitted {true,false}]\n";
const STEP18_HELP: &str = "usage: cli.py implement step-18 [-h] [--phase {gate,logs-flush}]\n                                [--stall-tracking-memory STALL_TRACKING_MEMORY]\n                                [--step17-emitted {true,false}]\n\noptions:\n  -h, --help            show this help message and exit\n  --phase {gate,logs-flush}\n  --stall-tracking-memory STALL_TRACKING_MEMORY\n  --step17-emitted {true,false}\n";

const COMPOSITE_PROG: &str = "cli.py implement step-18-gate-logs-flush";
const COMPOSITE_USAGE: &str = "usage: cli.py implement step-18-gate-logs-flush [-h]\n                                                [--implement-tmpdir IMPLEMENT_TMPDIR]\n                                                [--stall-tracking-memory STALL_TRACKING_MEMORY]\n                                                [--step17-emitted {true,false}]\n";
const COMPOSITE_HELP: &str = "usage: cli.py implement step-18-gate-logs-flush [-h]\n                                                [--implement-tmpdir IMPLEMENT_TMPDIR]\n                                                [--stall-tracking-memory STALL_TRACKING_MEMORY]\n                                                [--step17-emitted {true,false}]\n\noptions:\n  -h, --help            show this help message and exit\n  --implement-tmpdir IMPLEMENT_TMPDIR\n  --stall-tracking-memory STALL_TRACKING_MEMORY\n  --step17-emitted {true,false}\n";

const STEP19_PROG: &str = "cli.py implement step-19";
const STEP19_USAGE: &str =
    "usage: cli.py implement step-19 [-h] [--implement-tmpdir IMPLEMENT_TMPDIR]\n";
const STEP19_HELP: &str = "usage: cli.py implement step-19 [-h] [--implement-tmpdir IMPLEMENT_TMPDIR]\n\noptions:\n  -h, --help            show this help message and exit\n  --implement-tmpdir IMPLEMENT_TMPDIR\n";

const EXIT_INTERNAL_ERROR: i32 = 1;
const TEARDOWN_TIMEOUT: Duration = Duration::from_secs(900);
const REFUSAL_REASON: &str = "step18-terminal-shipping-without-pr";
const REFUSAL_ENTRY: &str = "- **Step 18 terminal gate**: refused terminal `shipping` without PR evidence; preserved the session for stall recovery.";
const TRUTHY: &[&str] = &[
    "1", "true", "TRUE", "True", "yes", "YES", "Yes", "on", "ON", "On",
];

// ---------------------------------------------------------------------------
// Shared readers and child spawns
// ---------------------------------------------------------------------------

fn emit(key: &str, value: &str) {
    println!("{key}={value}");
}

fn read_kv_file(path: &Path, key: &str, default: &str) -> String {
    if !path.is_file() {
        return default.to_owned();
    }
    fs::read(path)
        .ok()
        .and_then(|bytes| first_kv_value(&String::from_utf8_lossy(&bytes), key))
        .unwrap_or_else(|| default.to_owned())
}

fn parse_kv(text: &str) -> BTreeMap<String, String> {
    KvDocument::parse(text, ParseOptions::legacy()).map_or_else(
        |_error| BTreeMap::new(),
        |document| document.select(DuplicatePolicy::Last),
    )
}

fn value_or(rows: &BTreeMap<String, String>, key: &str, default: &str) -> String {
    match rows.get(key) {
        Some(value) if !value.is_empty() => value.clone(),
        _ => default.to_owned(),
    }
}

fn touch(path: &Path) {
    let _ = fs::OpenOptions::new().create(true).append(true).open(path);
}

/// Resolve the plugin root the way the retired Python owner rehydrated it.
fn rehydrate_plugin_root(tmpdir: &Path) -> PathBuf {
    if let Ok(root) = env::var("CLAUDE_PLUGIN_ROOT")
        && !root.is_empty()
    {
        return PathBuf::from(root);
    }
    let recorded = first_kv_value(
        &fs::read_to_string(tmpdir.join("plugin-root.env")).unwrap_or_default(),
        "CLAUDE_PLUGIN_ROOT",
    )
    .filter(|value| !value.is_empty())
    .or_else(|| {
        first_kv_value(
            &fs::read_to_string(tmpdir.join("session-env.sh")).unwrap_or_default(),
            "LARCH_CLAUDE_PLUGIN_ROOT",
        )
        .filter(|value| !value.is_empty())
    });
    recorded.map_or_else(
        || resolve_plugin_root().unwrap_or_default(),
        PathBuf::from,
    )
}

/// Run one sibling Rust verb through the verified bootstrap and capture it.
fn larch(
    root: &Path,
    tmpdir: &Path,
    args: &[&str],
    cwd: Option<&Path>,
    extra: &[(ChildEnvironment, OsString)],
) -> Result<ProcessOutput, String> {
    let command: Vec<OsString> = args.iter().map(OsString::from).collect();
    let here = env::current_dir().map_err(|error| error.to_string())?;
    let mut environment = vec![(
        ChildEnvironment::ImplementTmpdir,
        OsString::from(tmpdir.as_os_str()),
    )];
    environment.extend_from_slice(extra);
    run_verified_larch_env_in(cwd.unwrap_or(&here), root, &command, &environment)
}

fn relay_stderr(output: &ProcessOutput) {
    if !output.stderr().is_empty() {
        let _ = std::io::stderr().write_all(output.stderr());
    }
}

// ---------------------------------------------------------------------------
// Stall layers
// ---------------------------------------------------------------------------

struct StallLayers {
    memory: String,
    disk: String,
    finalize: String,
    session: String,
    abandoned_marker: String,
}

fn stall_layer_active(value: &str) -> bool {
    !value.is_empty() && value != "false"
}

fn resolve_stall_memory_layer(argument: &str) -> String {
    if argument == "true" || argument == "false" {
        return argument.to_owned();
    }
    if argument.is_empty() {
        let recorded = env::var("STALL_TRACKING").unwrap_or_default();
        return if recorded.is_empty() {
            "false".to_owned()
        } else {
            recorded
        };
    }
    argument.to_owned()
}

fn resolve_stall_layers(tmpdir: &Path, memory_argument: &str) -> StallLayers {
    StallLayers {
        memory: resolve_stall_memory_layer(memory_argument),
        disk: read_kv_file(&tmpdir.join("ship-pr-state.sh"), "STALL_TRACKING", "false"),
        finalize: read_kv_file(&tmpdir.join("finalize-state.sh"), "STALL_TRACKING", "false"),
        session: read_kv_file(&tmpdir.join("session-env.sh"), "STALL_TRACKING", "false"),
        abandoned_marker: if abandoned_checks_stall_step(tmpdir).is_some() {
            "true".to_owned()
        } else {
            "false".to_owned()
        },
    }
}

impl StallLayers {
    fn any_active(&self) -> bool {
        [
            &self.memory,
            &self.disk,
            &self.finalize,
            &self.session,
            &self.abandoned_marker,
        ]
        .iter()
        .any(|value| stall_layer_active(value))
    }
}

// ---------------------------------------------------------------------------
// finalize-state read and merged write
// ---------------------------------------------------------------------------

fn is_finalize_key(key: &str) -> bool {
    let mut bytes = key.bytes();
    bytes
        .next()
        .is_some_and(|first| first.is_ascii_uppercase() || first == b'_')
        && bytes.all(|byte| byte.is_ascii_uppercase() || byte.is_ascii_digit() || byte == b'_')
}

fn read_finalize_state(path: &Path) -> Result<BTreeMap<String, String>, String> {
    if !path.is_file() {
        return Ok(BTreeMap::new());
    }
    let text = fs::read(path)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .map_err(|error| format!("{error}"))?;
    if text.contains('\r') {
        return Err(format!(
            "session env file contains carriage return: {}",
            path.display()
        ));
    }
    let mut options = ParseOptions::legacy();
    options.comments = larch_core::CommentPolicy::Skip;
    let document = KvDocument::parse(&text, options).map_err(|error| format!("{error}"))?;
    let mut state = BTreeMap::new();
    for row in document.rows() {
        if !is_finalize_key(row.key()) {
            continue;
        }
        let decoded =
            split_one_shell_token(row.value()).unwrap_or_else(|| row.value().to_owned());
        let _ = state.insert(row.key().to_owned(), decoded);
    }
    Ok(state)
}

fn write_finalize_state_merged(path: &Path, state: &BTreeMap<String, String>) -> Result<(), String> {
    let mut text = String::new();
    for (key, value) in state {
        if !is_finalize_key(key) {
            return Err(format!("invalid finalize-state key: {key}"));
        }
        if value.contains(['\n', '\r']) {
            return Err(format!("finalize-state value for {key} contains a newline"));
        }
        text.push_str(key);
        text.push('=');
        text.push_str(value);
        text.push('\n');
    }
    write_confined_file(path, &text, 0o600, "finalize-state")
}

// ---------------------------------------------------------------------------
// Terminal run-log completion
// ---------------------------------------------------------------------------

fn terminal_publication_suppressed(tmpdir: &Path) -> bool {
    ["finalize-state.sh", "run-flags.sh", "session-env.sh"]
        .iter()
        .any(|name| read_kv_file(&tmpdir.join(name), "NO_LOGS_COMMIT", "false") == "true")
}

fn terminal_publication_repo_root(tmpdir: &Path) -> Option<PathBuf> {
    for name in ["session-env.sh", "ship-pr-state.sh", "finalize-state.sh"] {
        let raw = read_kv_file(&tmpdir.join(name), "REPO_ROOT", "");
        let raw = raw.trim();
        if raw.is_empty() {
            continue;
        }
        let root = PathBuf::from(raw);
        if !root.is_absolute() {
            continue;
        }
        let absolute = absolute_lexical(&root);
        if assert_no_symlink_path_or_ancestors(&absolute).is_err() {
            continue;
        }
        if fs::symlink_metadata(&absolute).is_ok_and(|metadata| metadata.is_dir()) {
            return Some(absolute);
        }
    }
    None
}

fn terminal_lifecycle_action(tmpdir: &Path, wfr_rc: &str) -> &'static str {
    if wfr_rc != "0" {
        return "failure";
    }
    let summary = tmpdir.join("summary-final.md");
    if !summary.is_file() {
        return "failure";
    }
    let text = fs::read(&summary)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .unwrap_or_default();
    let Some(label) = parse_preterminal_outcome_label(&text) else {
        return "failure";
    };
    if label.contains("cancel") {
        return "cancel";
    }
    if ["bail", "fail", "stall"]
        .iter()
        .any(|token| label.contains(token))
    {
        return "failure";
    }
    "finalize"
}

fn write_terminalization_record(tmpdir: &Path, publication: &str) -> bool {
    write_confined_file(
        &tmpdir.join(".run-log-terminalized"),
        &format!(
            "RUN_LOG_TERMINALIZED=true\nRUN_LOG_PUBLICATION={publication}\nLIFECYCLE_TERMINALIZED=true\n"
        ),
        0o600,
        "run-log terminalization record",
    )
    .is_ok()
}

fn prepare_terminal_snapshot(
    root: &Path,
    tmpdir: &Path,
    run_id: &str,
    suppressed: bool,
    repo_root: Option<&Path>,
) -> i32 {
    if run_id.is_empty() {
        eprintln!("Step 18: run-log publication failed: LARCH_RUN_ID is unavailable");
        emit("RUN_LOG_FINAL_FLUSH_OK", "false");
        emit("RUN_LOG_PUBLISH_OK", "false");
        return EXIT_INTERNAL_ERROR;
    }
    let tmpdir_text = tmpdir.to_string_lossy().into_owned();
    let repo_root_text = repo_root.map(|path| path.to_string_lossy().into_owned());
    let mut args = vec![
        "run-log",
        "prepare-terminal-snapshot",
        "--implement-tmpdir",
        tmpdir_text.as_str(),
        "--run-id",
        run_id,
        "--no-logs-commit",
        if suppressed { "true" } else { "false" },
    ];
    if let Some(text) = repo_root_text.as_deref() {
        args.extend(["--repo-root", text]);
    }
    let Ok(prepare) = larch(root, tmpdir, &args, repo_root, &[]) else {
        eprintln!("Step 18: terminal snapshot preparation failed (rc=1); the session staging tree was retained for retry.");
        emit("RUN_LOG_FINAL_FLUSH_OK", "false");
        emit("RUN_LOG_PUBLISH_OK", "false");
        return EXIT_INTERNAL_ERROR;
    };
    relay_stderr(&prepare);
    let stdout = String::from_utf8_lossy(prepare.stdout()).into_owned();
    for line in stdout.lines() {
        if line.starts_with("SESSION_TRANSCRIPT_STATUS=") || line.starts_with("TERMINAL_SNAPSHOT_")
        {
            println!("{line}");
        }
    }
    let code = prepare.status().code().unwrap_or(EXIT_INTERNAL_ERROR);
    let prepared =
        code == 0 && parse_kv(&stdout).get("TERMINAL_SNAPSHOT_STATUS").map(String::as_str)
            == Some("prepared");
    if !prepared {
        eprintln!(
            "Step 18: terminal snapshot preparation failed (rc={code}); the session staging tree was retained for retry."
        );
        emit("RUN_LOG_FINAL_FLUSH_OK", "false");
        emit("RUN_LOG_PUBLISH_OK", "false");
        return if code == 0 { EXIT_INTERNAL_ERROR } else { code };
    }
    emit("RUN_LOG_FINAL_FLUSH_OK", "true");
    0
}

fn record_suppressed_terminalization(tmpdir: &Path) -> i32 {
    emit("RUN_LOG_PUBLISH_SKIPPED", "no-logs-commit");
    emit("RUN_LOG_PUBLICATION", "skipped-suppressed");
    emit("LIFECYCLE_FLUSHED", "false");
    emit("LIFECYCLE_TERMINALIZED", "true");
    if !write_terminalization_record(tmpdir, "skipped-suppressed") {
        eprintln!("Step 18: suppressed terminalization could not be recorded for cleanup.");
        emit("RUN_LOG_PUBLISH_OK", "false");
        return EXIT_INTERNAL_ERROR;
    }
    emit("RUN_LOG_PUBLISH_OK", "true");
    0
}

fn publish_terminal_archive(
    root: &Path,
    tmpdir: &Path,
    run_id: &str,
    lifecycle_action: &str,
) -> i32 {
    let Some(repo_root) = terminal_publication_repo_root(tmpdir) else {
        eprintln!("Step 18: run-log publication failed: persisted REPO_ROOT is unavailable");
        emit("RUN_LOG_PUBLISH_OK", "false");
        return EXIT_INTERNAL_ERROR;
    };
    let verb = match lifecycle_action {
        "cancel" => "lifecycle-cancel",
        "failure" => "lifecycle-failure",
        _ => "lifecycle-finalize",
    };
    let repo_root_text = repo_root.to_string_lossy().into_owned();
    let publish = larch(
        root,
        tmpdir,
        &[
            "run-log",
            verb,
            "--repo-root",
            repo_root_text.as_str(),
            "--skill",
            "implement",
            "--run-id",
            run_id,
        ],
        Some(&repo_root),
        &[],
    );
    let (code, stdout) = match publish {
        Ok(output) => {
            relay_stderr(&output);
            (
                output.status().code().unwrap_or(EXIT_INTERNAL_ERROR),
                String::from_utf8_lossy(output.stdout()).into_owned(),
            )
        }
        Err(message) => {
            eprintln!("{message}");
            (EXIT_INTERNAL_ERROR, String::new())
        }
    };
    let values = parse_kv(&stdout);
    let publication = values.get("RUN_LOG_PUBLICATION").cloned().unwrap_or_default();
    let cache_dir = values.get("CACHE_DIR").filter(|value| !value.is_empty());
    let remote_key = values.get("REMOTE_KEY").is_some_and(|key| !key.is_empty());
    let published = publication == "published"
        && values.get("LIFECYCLE_FLUSHED").map(String::as_str) == Some("true")
        && remote_key
        && cache_dir.is_some_and(|value| Path::new(value).is_dir());
    let skipped_disabled = publication == "skipped-disabled"
        && values.get("LIFECYCLE_FLUSHED").map(String::as_str) == Some("false")
        && !remote_key
        && cache_dir.is_none();
    let postcondition_ok = code == 0
        && values.get("LIFECYCLE_TERMINALIZED").map(String::as_str) == Some("true")
        && (published || skipped_disabled);
    if !postcondition_ok {
        eprintln!(
            "Step 18: run-log publication failed (rc={code}); durable pending state and the session staging tree were retained for retry."
        );
        emit("RUN_LOG_PUBLISH_OK", "false");
        return if code == 0 { EXIT_INTERNAL_ERROR } else { code };
    }
    if !write_terminalization_record(tmpdir, &publication) {
        eprintln!(
            "Step 18: run-log publication succeeded, but terminalization could not be recorded for cleanup."
        );
        emit("RUN_LOG_PUBLISH_OK", "false");
        return EXIT_INTERNAL_ERROR;
    }
    if !stdout.is_empty() {
        print!("{stdout}");
        if !stdout.ends_with('\n') {
            println!();
        }
        let _ = std::io::stdout().flush();
    }
    emit("RUN_LOG_PUBLISH_OK", "true");
    0
}

fn print_summary_markers(tmpdir: &Path) {
    println!("---LARCH-SUMMARY-FINAL-BEGIN---");
    let Ok(bytes) = fs::read(tmpdir.join("summary-final.md")) else {
        return;
    };
    let body = String::from_utf8_lossy(&bytes);
    print!("{body}");
    if !body.is_empty() && !body.ends_with('\n') {
        println!();
    }
    println!("---LARCH-SUMMARY-FINAL-END---");
    touch(&tmpdir.join(".step17-emitted"));
}

fn complete_terminal_run_log(
    root: &Path,
    tmpdir: &Path,
    run_id: &str,
    emit_body: &str,
    wfr_rc: &str,
) -> i32 {
    let suppressed = terminal_publication_suppressed(tmpdir);
    let repo_root = terminal_publication_repo_root(tmpdir);
    let prepare_rc = prepare_terminal_snapshot(
        root,
        tmpdir,
        run_id,
        suppressed,
        repo_root.as_deref(),
    );
    if prepare_rc != 0 {
        return prepare_rc;
    }
    let publish_rc = if suppressed {
        record_suppressed_terminalization(tmpdir)
    } else {
        publish_terminal_archive(
            root,
            tmpdir,
            run_id,
            terminal_lifecycle_action(tmpdir, wfr_rc),
        )
    };
    if publish_rc != 0 {
        return publish_rc;
    }
    let summary = tmpdir.join("summary-final.md");
    let non_empty = fs::metadata(&summary).is_ok_and(|meta| meta.is_file() && meta.len() > 0);
    if emit_body == "true" && wfr_rc == "0" && non_empty {
        print_summary_markers(tmpdir);
    }
    0
}

// ---------------------------------------------------------------------------
// Step 18 phases
// ---------------------------------------------------------------------------

fn step18_gate(tmpdir: &Path, stall_tracking_memory: &str) -> ExitCode {
    let layers = resolve_stall_layers(tmpdir, stall_tracking_memory);
    emit("STALL_TRACKING_MEMORY", &layers.memory);
    emit("STALL_TRACKING_DISK", &layers.disk);
    emit("STALL_TRACKING_FINALIZE", &layers.finalize);
    emit("STALL_TRACKING_SESSION", &layers.session);
    if [
        &layers.memory,
        &layers.disk,
        &layers.finalize,
        &layers.session,
    ]
    .iter()
    .any(|value| stall_layer_active(value))
    {
        emit("STALL_RECOVERY_REQUIRED", "true");
        return ExitCode::SUCCESS;
    }
    emit("STALL_RECOVERY_REQUIRED", "false");
    println!("⏩ 18a: stall recovery; no stall detected");
    ExitCode::SUCCESS
}

fn append_failure_best_effort(root: &Path, tmpdir: &Path, rc: i32, log: &Path) {
    if !log.is_file() && fs::write(log, b"").is_err() {
        return;
    }
    let issues = tmpdir.join("execution-issues.md");
    let issues_text = issues.to_string_lossy().into_owned();
    let log_text = log.to_string_lossy().into_owned();
    let code = rc.to_string();
    let _ = larch(
        root,
        tmpdir,
        &[
            "run-log",
            "append-failure",
            "--log",
            issues_text.as_str(),
            "--site",
            "Step 18b — final-report",
            "--tool",
            "scripts/larch.sh final-report step18b",
            "--exit-code",
            code.as_str(),
            "--category",
            "Tool Failures",
            "--output-file",
            log_text.as_str(),
            "--redact",
        ],
        None,
        &[],
    );
}

fn mark_token_and_timing(root: &Path, tmpdir: &Path) {
    let timing_environment = [
        (ChildEnvironment::DesignTmpdir, OsString::new()),
        (
            ChildEnvironment::LarchTimingSkill,
            OsString::from("implement"),
        ),
    ];
    let _ = larch(
        root,
        tmpdir,
        &["token", "report", "--since-last-mark", "--terse"],
        None,
        &[],
    );
    for args in [
        vec!["timing", "report", "--since-last-mark", "--terse"],
        vec!["token", "mark", "Step 18 — logs flush"],
        vec!["timing", "mark", "Step 18 — logs flush"],
    ] {
        let _ = larch(root, tmpdir, &args, None, &timing_environment);
    }
}

fn step18_logs_flush(root: &Path, tmpdir: &Path, step17_emitted: &str) -> i32 {
    if step17_emitted == "true" {
        touch(&tmpdir.join(".step17-emitted"));
    }
    let step18b_out = tmpdir.join("step18b-final-report.stdout");
    let step18b_err = tmpdir.join("step18b-final-report.stderr");
    let _ = fs::write(&step18b_err, b"");
    let tmpdir_text = tmpdir.to_string_lossy().into_owned();
    let result = larch(
        root,
        tmpdir,
        &[
            "final-report",
            "step18b",
            "--implement-tmpdir",
            tmpdir_text.as_str(),
            "--step17-emitted",
            step17_emitted,
        ],
        None,
        &[],
    );
    let (rc, stdout, stderr) = match result {
        Ok(output) => (
            output.status().code().unwrap_or(EXIT_INTERNAL_ERROR),
            String::from_utf8_lossy(output.stdout()).into_owned(),
            output.stderr().to_vec(),
        ),
        Err(message) => (EXIT_INTERNAL_ERROR, String::new(), message.into_bytes()),
    };
    let _ = fs::write(&step18b_out, stdout.as_bytes());
    if !stderr.is_empty() {
        let _ = fs::write(&step18b_err, &stderr);
    }
    let values = parse_kv(&stdout);
    let emit_body = value_or(&values, "EMIT_BODY", "false");
    let wfr_rc = value_or(&values, "WFR_RC", &rc.to_string());
    let step17_present = value_or(&values, "STEP17_EMITTED_PRESENT", "false");
    let snapshot_ok = value_or(&values, "SNAPSHOT_OK", "absent");
    let wfr_error = values.get("ERROR").cloned().unwrap_or_default();
    if rc != 0 {
        append_failure_best_effort(root, tmpdir, rc, &step18b_err);
    }
    emit("EMIT_BODY", &emit_body);
    emit("WFR_RC", &wfr_rc);
    emit("STEP17_EMITTED_PRESENT", &step17_present);
    emit("SNAPSHOT_OK", &snapshot_ok);
    emit("ERROR", &wfr_error);
    if wfr_rc != "0" {
        let reason = if wfr_error.is_empty() {
            "render failed (no reason surfaced)"
        } else {
            wfr_error.as_str()
        };
        eprintln!("**⚠ Step 18: final report render failed (WFR_RC={wfr_rc}): {reason}.**");
    }
    mark_token_and_timing(root, tmpdir);
    let run_id = env::var("RUN_ID").ok().filter(|value| !value.is_empty()).unwrap_or_else(|| {
        read_kv_file(&tmpdir.join("session-env.sh"), "LARCH_RUN_ID", "")
    });
    complete_terminal_run_log(root, tmpdir, &run_id, &emit_body, &wfr_rc)
}

fn exit_code(rc: i32) -> ExitCode {
    ExitCode::from(u8::try_from(rc).unwrap_or(1))
}

/// `implement step-18` compatibility command.
pub fn step_18(arguments: &[OsString]) -> ExitCode {
    if let Some(error) = choice_error(
        arguments,
        &[
            "--phase",
            "--stall-tracking-memory",
            "--step17-emitted",
            "-h",
            "--help",
        ],
        &[
            ("--phase", &["gate", "logs-flush"]),
            ("--step17-emitted", &["true", "false"]),
        ],
    ) {
        return usage_error(STEP18_USAGE, STEP18_PROG, &error, 2);
    }
    let parsed = match parse_required_with_help(
        arguments,
        STEP18_PROG,
        STEP18_USAGE,
        STEP18_HELP,
        &["--phase", "--stall-tracking-memory", "--step17-emitted"],
        &[],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let raw_tmpdir = env::var("IMPLEMENT_TMPDIR").unwrap_or_default();
    if raw_tmpdir.is_empty() {
        eprintln!("implement step-18: IMPLEMENT_TMPDIR is required");
        return ExitCode::from(2);
    }
    let tmpdir = PathBuf::from(raw_tmpdir);
    let root = rehydrate_plugin_root(&tmpdir);
    if !root.is_dir() {
        eprintln!("step-18: CLAUDE_PLUGIN_ROOT not found: {}", root.display());
        return ExitCode::from(2);
    }
    rehydrate_session(&tmpdir);
    let phase = parsed
        .value("--phase")
        .map_or_else(|| "gate".to_owned(), |value| {
            value.to_string_lossy().into_owned()
        });
    if phase == "gate" {
        return step18_gate(
            &tmpdir,
            &opt_string(parsed.value("--stall-tracking-memory")),
        );
    }
    let step17_emitted = parsed
        .value("--step17-emitted")
        .map_or_else(|| "false".to_owned(), |value| {
            value.to_string_lossy().into_owned()
        });
    exit_code(step18_logs_flush(&root, &tmpdir, &step17_emitted))
}

// ---------------------------------------------------------------------------
// step-18-gate-logs-flush
// ---------------------------------------------------------------------------

fn record_terminal_shipping_refusal(tmpdir: &Path) -> bool {
    let state_path = tmpdir.join("finalize-state.sh");
    if fs::symlink_metadata(&state_path)
        .is_ok_and(|metadata| metadata.file_type().is_symlink())
    {
        return false;
    }
    let expected: [(&str, &str); 6] = [
        ("BAIL_REASON", REFUSAL_REASON),
        ("EXIT_CODE", "1"),
        ("PHASE", "stalled"),
        ("STALL_STEP", "8"),
        ("STALL_TRACKING", "true"),
        ("STEP18_GATE_REFUSAL", REFUSAL_REASON),
    ];
    let Ok(mut state) = read_finalize_state(&state_path) else {
        return false;
    };
    for (key, value) in expected {
        let _ = state.insert(key.to_owned(), value.to_owned());
    }
    if write_finalize_state_merged(&state_path, &state).is_err() {
        return false;
    }
    let Ok(persisted) = read_finalize_state(&state_path) else {
        return false;
    };
    if expected
        .iter()
        .any(|(key, value)| persisted.get(*key).map(String::as_str) != Some(*value))
    {
        return false;
    }
    let issue_log = tmpdir.join("execution-issues.md");
    if append_execution_issue(&issue_log, "Tool Failures", REFUSAL_ENTRY).is_err() {
        return false;
    }
    fs::read_to_string(&issue_log).is_ok_and(|text| text.contains(REFUSAL_ENTRY))
}

/// `implement step-18-gate-logs-flush` compatibility command.
pub fn step_18_gate_logs_flush(arguments: &[OsString]) -> ExitCode {
    if let Some(error) = choice_error(
        arguments,
        &[
            "--implement-tmpdir",
            "--stall-tracking-memory",
            "--step17-emitted",
            "-h",
            "--help",
        ],
        &[("--step17-emitted", &["true", "false"])],
    ) {
        return usage_error(COMPOSITE_USAGE, COMPOSITE_PROG, &error, 2);
    }
    let parsed = match parse_required_with_help(
        arguments,
        COMPOSITE_PROG,
        COMPOSITE_USAGE,
        COMPOSITE_HELP,
        &[
            "--implement-tmpdir",
            "--stall-tracking-memory",
            "--step17-emitted",
        ],
        &[],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let raw_tmpdir = {
        let supplied = opt_string(parsed.value("--implement-tmpdir"));
        if supplied.is_empty() {
            env::var("IMPLEMENT_TMPDIR").unwrap_or_default()
        } else {
            supplied
        }
    };
    if raw_tmpdir.is_empty() {
        eprintln!(
            "implement step-18-gate-logs-flush: --implement-tmpdir is required or IMPLEMENT_TMPDIR must be set"
        );
        return ExitCode::from(2);
    }
    let tmpdir = PathBuf::from(raw_tmpdir);
    let root = rehydrate_plugin_root(&tmpdir);
    rehydrate_session(&tmpdir);
    let layers = resolve_stall_layers(
        &tmpdir,
        &opt_string(parsed.value("--stall-tracking-memory")),
    );
    emit("STALL_TRACKING_MEMORY", &layers.memory);
    emit("STALL_TRACKING_DISK", &layers.disk);
    emit("STALL_TRACKING_FINALIZE", &layers.finalize);
    emit("STALL_TRACKING_SESSION", &layers.session);
    emit("STALL_TRACKING_ABANDONED_MARKER", &layers.abandoned_marker);
    if layers.any_active() {
        emit("STALL_RECOVERY_REQUIRED", "true");
        emit("NEXT_ACTION", "stall-recovery");
        return ExitCode::SUCCESS;
    }
    println!("⏩ 18a: stall recovery; no stall detected");
    let normalized = normalize_outcome(&root, &tmpdir, &layers.memory);
    if normalized.get("IMPLEMENT_NORMALIZED_OUTCOME").map(String::as_str) == Some("shipping")
        && normalized
            .get("IMPLEMENT_PR_NUMBER")
            .is_none_or(|value| value.trim().is_empty())
    {
        let persisted = record_terminal_shipping_refusal(&tmpdir);
        emit(
            "STALL_RECOVERY_REQUIRED",
            if persisted { "true" } else { "unknown" },
        );
        emit("TERMINAL_FINALIZE_REFUSED", "true");
        emit("STATUS", "blocked");
        emit("OUTCOME", "stalled");
        emit("NEXT_ACTION", "tool-failure");
        if !persisted {
            eprintln!(
                "implement step-18-gate-logs-flush: cannot persist terminal shipping refusal"
            );
        }
        return exit_code(EXIT_INTERNAL_ERROR);
    }
    emit("STALL_RECOVERY_REQUIRED", "false");
    let step17_emitted = parsed
        .value("--step17-emitted")
        .map_or_else(|| "false".to_owned(), |value| {
            value.to_string_lossy().into_owned()
        });
    let rc = step18_logs_flush(&root, &tmpdir, &step17_emitted);
    emit(
        "NEXT_ACTION",
        if rc == 0 {
            "logs-flush-done"
        } else {
            "logs-flush-failed"
        },
    );
    exit_code(rc)
}

fn normalize_outcome(root: &Path, tmpdir: &Path, memory_layer: &str) -> BTreeMap<String, String> {
    let tmpdir_text = tmpdir.to_string_lossy().into_owned();
    let Ok(output) = larch(
        root,
        tmpdir,
        &[
            "stall-recovery",
            "normalize-outcome",
            "--implement-tmpdir",
            tmpdir_text.as_str(),
            "--in-memory-stall-tracking",
            memory_layer,
        ],
        None,
        &[],
    ) else {
        return BTreeMap::new();
    };
    relay_stderr(&output);
    let stdout = String::from_utf8_lossy(output.stdout()).into_owned();
    if !stdout.is_empty() {
        print!("{stdout}");
        let _ = std::io::stdout().flush();
    }
    if output.status().code() == Some(0) {
        parse_kv(&stdout)
    } else {
        BTreeMap::new()
    }
}

// ---------------------------------------------------------------------------
// step-19
// ---------------------------------------------------------------------------

fn should_restore_finalize(tmpdir: &Path) -> bool {
    let ship_state = tmpdir.join("ship-pr-state.sh");
    if !ship_state.is_file() {
        return false;
    }
    let finalize_state = tmpdir.join("finalize-state.sh");
    if !finalize_state.is_file() {
        return true;
    }
    let ship_stall = read_kv_file(&ship_state, "STALL_TRACKING", "false");
    let ship_bail = read_kv_file(&ship_state, "BAIL_NEEDS_USER_INPUT", "false");
    if TRUTHY.contains(&ship_stall.as_str()) || TRUTHY.contains(&ship_bail.as_str()) {
        return true;
    }
    let ship_step = read_kv_file(&ship_state, "STALL_STEP", "");
    let final_step = read_kv_file(&finalize_state, "STALL_STEP", "");
    !ship_step.is_empty() && ship_step != final_step
}

fn terminalization_record_valid(tmpdir: &Path) -> bool {
    let record = tmpdir.join(".run-log-terminalized");
    if !fs::symlink_metadata(&record).is_ok_and(|metadata| metadata.is_file()) {
        return false;
    }
    read_kv_file(&record, "RUN_LOG_TERMINALIZED", "false") == "true"
        && read_kv_file(&record, "LIFECYCLE_TERMINALIZED", "false") == "true"
}

/// `implement step-19` compatibility command.
pub fn step_19(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        STEP19_PROG,
        STEP19_USAGE,
        STEP19_HELP,
        &["--implement-tmpdir"],
        &[],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let raw_tmpdir = {
        let supplied = opt_string(parsed.value("--implement-tmpdir"));
        if supplied.is_empty() {
            env::var("IMPLEMENT_TMPDIR").unwrap_or_default()
        } else {
            supplied
        }
    };
    if raw_tmpdir.is_empty() {
        eprintln!(
            "implement step-19: --implement-tmpdir is required or IMPLEMENT_TMPDIR must be set"
        );
        return ExitCode::from(2);
    }
    let tmpdir = PathBuf::from(raw_tmpdir);
    let root = rehydrate_plugin_root(&tmpdir);
    if !root.is_dir() {
        eprintln!("step-19: CLAUDE_PLUGIN_ROOT not found: {}", root.display());
        return ExitCode::from(2);
    }
    rehydrate_session(&tmpdir);
    if !terminalization_record_valid(&tmpdir) {
        eprintln!("Step 19: cleanup refused because Step 18 run-log terminalization is not recorded.");
        emit("CLEANUP_BLOCKED", "run-log-not-terminalized");
        return exit_code(EXIT_INTERNAL_ERROR);
    }
    let tmpdir_text = tmpdir.to_string_lossy().into_owned();
    if should_restore_finalize(&tmpdir) {
        let restored = larch(
            &root,
            &tmpdir,
            &[
                "session",
                "restore-finalize-state",
                "--implement-tmpdir",
                tmpdir_text.as_str(),
            ],
            None,
            &[],
        );
        if !restored.is_ok_and(|output| output.status().code() == Some(0)) {
            eprintln!("**⚠ Step 19: restore-finalize-state failed; proceeding to teardown.**");
        }
    }
    let claude_pid = env::var("LARCH_CLAUDE_PID")
        .ok()
        .filter(|value| !value.is_empty())
        .unwrap_or_else(current_parent_pid);
    let _ = larch(
        &root,
        &tmpdir,
        &[
            "session",
            "clear-implement-pointer",
            "--claude-pid",
            claude_pid.as_str(),
        ],
        None,
        &[],
    );
    let state_file = tmpdir.join("finalize-state.sh");
    let teardown = run_python_verb(
        [
            OsString::from("implement-finalize"),
            OsString::from("teardown"),
            OsString::from("--state-file"),
            OsString::from(state_file.as_os_str()),
            OsString::from("--implement-tmpdir"),
            OsString::from(tmpdir.as_os_str()),
        ],
        TEARDOWN_TIMEOUT,
    );
    match teardown {
        Ok(output) => {
            if !output.stdout().is_empty() {
                let _ = std::io::stdout().write_all(output.stdout());
                let _ = std::io::stdout().flush();
            }
            relay_stderr(&output);
            exit_code(output.status().code().unwrap_or(EXIT_INTERNAL_ERROR))
        }
        Err(message) => {
            eprintln!("{message}");
            exit_code(EXIT_INTERNAL_ERROR)
        }
    }
}

fn current_parent_pid() -> String {
    #[cfg(unix)]
    {
        nix::unistd::getppid().as_raw().to_string()
    }
    #[cfg(not(unix))]
    {
        String::new()
    }
}

#[cfg(test)]
mod tests {
    use super::{
        is_finalize_key, read_finalize_state, resolve_stall_memory_layer, should_restore_finalize,
        stall_layer_active, terminal_lifecycle_action, terminalization_record_valid,
        write_finalize_state_merged,
    };
    use std::{collections::BTreeMap, fs};
    use tempfile::TempDir;

    #[test]
    fn stall_layer_predicate_matches_the_python_truthiness() {
        assert!(!stall_layer_active(""));
        assert!(!stall_layer_active("false"));
        for value in ["true", "1", "yes", "arbitrary"] {
            assert!(stall_layer_active(value), "{value} must be active");
        }
    }

    #[test]
    fn memory_layer_prefers_the_explicit_argument() {
        assert_eq!(resolve_stall_memory_layer("true"), "true");
        assert_eq!(resolve_stall_memory_layer("false"), "false");
        assert_eq!(resolve_stall_memory_layer("maybe"), "maybe");
    }

    #[test]
    fn finalize_state_round_trips_unquoted_sorted_rows() {
        let root = TempDir::new().expect("temp");
        let path = root.path().join("finalize-state.sh");
        fs::write(&path, "# comment\nZ='last'\nA=\"first\"\nbad-key=x\nZ=second\n")
            .expect("write");
        let state = read_finalize_state(&path).expect("read");
        assert_eq!(state.get("A").map(String::as_str), Some("first"));
        assert_eq!(state.get("Z").map(String::as_str), Some("second"));
        assert!(!state.contains_key("bad-key"));
        let mut merged: BTreeMap<String, String> = state;
        let _ = merged.insert("BAIL_REASON".to_owned(), "why".to_owned());
        write_finalize_state_merged(&path, &merged).expect("write merged");
        assert_eq!(
            fs::read_to_string(&path).expect("read back"),
            "A=first\nBAIL_REASON=why\nZ=second\n"
        );
        assert!(is_finalize_key("_A0"));
        assert!(!is_finalize_key("0A"));
    }

    #[test]
    fn lifecycle_action_follows_the_preterminal_label() {
        let root = TempDir::new().expect("temp");
        assert_eq!(terminal_lifecycle_action(root.path(), "7"), "failure");
        assert_eq!(terminal_lifecycle_action(root.path(), "0"), "failure");
        let summary = root.path().join("summary-final.md");
        fs::write(&summary, "## /implement run R1: shipped\n").expect("write");
        assert_eq!(terminal_lifecycle_action(root.path(), "0"), "finalize");
        fs::write(&summary, "## /implement run R1: cancelled\n").expect("write");
        assert_eq!(terminal_lifecycle_action(root.path(), "0"), "cancel");
        fs::write(&summary, "## /implement run R1: stalled\n").expect("write");
        assert_eq!(terminal_lifecycle_action(root.path(), "0"), "failure");
    }

    #[test]
    fn step19_restore_and_terminalization_gates() {
        let root = TempDir::new().expect("temp");
        assert!(!should_restore_finalize(root.path()));
        fs::write(
            root.path().join("ship-pr-state.sh"),
            "STALL_TRACKING=false\nBAIL_NEEDS_USER_INPUT=false\nSTALL_STEP=\n",
        )
        .expect("write");
        assert!(should_restore_finalize(root.path()), "missing finalize state");
        fs::write(
            root.path().join("finalize-state.sh"),
            "STALL_TRACKING=false\nSTALL_STEP=\n",
        )
        .expect("write");
        assert!(!should_restore_finalize(root.path()));
        fs::write(
            root.path().join("ship-pr-state.sh"),
            "STALL_TRACKING=false\nBAIL_NEEDS_USER_INPUT=false\nSTALL_STEP=ship\n",
        )
        .expect("write");
        assert!(should_restore_finalize(root.path()), "stall step mismatch");
        assert!(!terminalization_record_valid(root.path()));
        fs::write(
            root.path().join(".run-log-terminalized"),
            "RUN_LOG_TERMINALIZED=true\nRUN_LOG_PUBLICATION=published\nLIFECYCLE_TERMINALIZED=true\n",
        )
        .expect("write");
        assert!(terminalization_record_valid(root.path()));
    }
}
