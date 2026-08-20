//! Rust owner for the four `/design` terminal-state and failure-report verbs
//! (#8580).
//!
//! Atomically replaces the Python registrations for `design read-result-env`,
//! `design stage-terminal-state`, `design failure-report`, and `design
//! step-final-summary`. The frozen Python reference lives under
//! `fixtures/rust-parity/design_terminal_frozen/`.
//!
//! The port follows the byte-frozen parity precedent of the sibling
//! `design_step1_commands.rs` (#8579) and reuses the Step 0 wrapper library
//! (`design_step0_commands.rs`) plus the `python_verb` seam for the still-Python
//! `design render-final-summary` (#8581) and `design log-publish` (#8592)
//! neighbors. The Rust `stall-recovery` owners are reached in-process the same
//! way the frozen Python module reached them: by re-invoking the larch
//! entrypoint through the [`Step0Runner`] subprocess seam.

use std::{
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::{SystemTime, UNIX_EPOCH},
};

use larch_adapters::github::{IssueMutationOwner, LiveMutationRequest, check_live_mutation_auth};
use larch_adapters::validate_design_tmpdir;
use larch_core::{
    GitHubCloseReason, KvDocument, ParseOptions, cleanup_cache_sessions_root, redact_outbound,
};

use crate::{
    blocker_commands::resolve_repo_for,
    design_commands::{PAUSE_LOAD_TIMEOUT, quote_single},
    design_step0_commands::{
        ChildOutcome, Env, LiveStep0Runner, Step0Runner, env_get, exit_from_i32, load_wrapper_env,
        parse_wrapper_args, require_plugin_root, utf8_arguments,
    },
    github_repository_resolution::repository_ref,
    github_service::with_github_service,
    python_verb::run_python_verb,
    voter_calibration_commands::resolve_like_python,
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const RECONCILE_PUBLISH_TAIL_MARKER: &str = "<!-- larch-reconcile:failed-publish-tail -->";
const BGJOB_TMP_SUBDIR: &str = "bgjob";
const BGJOB_RESULT_ENV_SUFFIX: &str = ".result.env";
const DESIGN_PUBLISH_RESULT_FILE: &str = ".design-publish-result.env";
const LIVE_MUTATION_REFUSAL_REASON: &str = "unauthorized-mutation";
const ENV_FINAL_SUMMARY_PATH: &str = "FINAL_SUMMARY_PATH";
const ENV_FINAL_SUMMARY_READY: &str = "FINAL_SUMMARY_READY";
const LARCH_FINAL_SUMMARY_BEGIN_MARKER: &str = "LARCH_FINAL_SUMMARY_BEGIN";
const LARCH_FINAL_SUMMARY_END_MARKER: &str = "LARCH_FINAL_SUMMARY_END";
const STEP3_ESCALATION_FAILURE_STATUSES: [&str; 4] = [
    "panel-failed",
    "panel-init-failed",
    "tally-error",
    "degraded-empty-collector",
];
const TERMINAL_PUBLISH_DIAGNOSTIC_BYTE_CAP: u64 = 4096;
const TERMINAL_PUBLISH_DIAGNOSTIC_CHAR_CAP: usize = 500;

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

/// Mirror `_core_diagnostic`: one operator-visible diagnostic line to stderr.
/// The frozen module runs the message through redaction and control-character
/// sanitization; both are the identity for the fixed ASCII diagnostics these
/// verbs emit, matching the `eprintln!` precedent of the sibling design owners.
fn core_diagnostic(message: &str) {
    eprintln!("{}", sanitize_diagnostic_line(message));
}

/// Port of `logging_util.sanitize_diagnostic_line`: strip C0 control bytes and
/// DEL from one diagnostic line.
fn sanitize_diagnostic_line(text: &str) -> String {
    text.chars()
        .filter(|character| *character >= ' ' && *character != '\u{7f}')
        .collect()
}

/// Port of `_stall_args`.
fn stall_args(design_tmpdir: &Path) -> Vec<String> {
    vec![
        "--profile".to_owned(),
        "generic".to_owned(),
        "--artifact-prefix".to_owned(),
        "design-failure".to_owned(),
        "--implement-tmpdir".to_owned(),
        design_tmpdir.display().to_string(),
    ]
}

/// Port of `_run_stall_rust`: run one `stall-recovery <verb>` child through the
/// entrypoint seam and optionally capture its streams to the given files.
fn run_stall(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    verb: &str,
    args: &[String],
    stdout_path: Option<&Path>,
    stderr_path: Option<&Path>,
) -> i32 {
    let mut child_args = vec!["stall-recovery".to_owned(), verb.to_owned()];
    child_args.extend(args.iter().cloned());
    let outcome = runner.run(plugin_root, &child_args, &[], false);
    if let Some(path) = stdout_path
        && fs::write(path, &outcome.stdout).is_err()
    {
        return 1;
    }
    if let Some(path) = stderr_path
        && fs::write(path, &outcome.stderr).is_err()
    {
        return 1;
    }
    outcome.code
}

/// Port of `_run_stall_rust_capture`.
fn run_stall_capture(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    verb: &str,
    args: &[String],
) -> ChildOutcome {
    let mut child_args = vec!["stall-recovery".to_owned(), verb.to_owned()];
    child_args.extend(args.iter().cloned());
    runner.run(plugin_root, &child_args, &[], false)
}

/// Port of `_valid_var_name`.
fn valid_var_name(value: &str) -> bool {
    let mut chars = value.chars();
    match chars.next() {
        None => false,
        Some(first) if first.is_ascii_digit() => false,
        Some(first) if !(first.is_alphanumeric() || first == '_') => false,
        Some(_) => value.chars().all(|c| c.is_alphanumeric() || c == '_'),
    }
}

/// Port of `_validate_design_tmpdir_arg`: validate against the allowlist, then
/// require the resolved path to name a directory.
fn validate_core_design_tmpdir(candidate: &str) -> Result<PathBuf, String> {
    validate_design_tmpdir(
        candidate,
        std::env::var_os("TMPDIR").as_deref(),
        &cleanup_cache_sessions_root(
            std::env::var_os("XDG_CACHE_HOME").as_deref(),
            std::env::var_os("HOME").as_deref(),
        ),
    )?;
    let path = resolve_like_python(Path::new(candidate));
    if path.is_dir() {
        Ok(path)
    } else {
        Err("design-tmpdir: path must name a directory".to_owned())
    }
}

/// Port of `phase_driver_read_result_env`: CR-free, allowlisted, order-preserving.
fn phase_driver_read_result_env(
    path: &Path,
    allowed: &[String],
) -> Result<Vec<(String, String)>, ()> {
    if is_symlink(path) || !path.is_file() {
        return Err(());
    }
    let raw = match fs::read(path) {
        Ok(bytes) => String::from_utf8_lossy(&bytes).into_owned(),
        Err(_error) => return Err(()),
    };
    let cleaned: Vec<&str> = raw
        .split('\n')
        .filter(|line| !line.contains('\r'))
        .collect();
    let text = cleaned.join("\n");
    let document =
        KvDocument::parse(&text, ParseOptions::legacy()).expect("legacy parser is non-rejecting");
    Ok(document
        .rows()
        .iter()
        .filter(|row| allowed.iter().any(|key| key == row.key()))
        .map(|row| (row.key().to_owned(), row.value().to_owned()))
        .collect())
}

fn is_symlink(path: &Path) -> bool {
    fs::symlink_metadata(path).is_ok_and(|meta| meta.file_type().is_symlink())
}

/// First `KEY=` value with `_read_env_value` semantics: symlink/non-file/error
/// yield the default; an empty value also yields the default.
fn read_env_value(path: &Path, key: &str, default: &str) -> String {
    if is_symlink(path) || !path.is_file() {
        return default.to_owned();
    }
    let Ok(bytes) = fs::read(path) else {
        return default.to_owned();
    };
    let text = String::from_utf8_lossy(&bytes);
    let prefix = format!("{key}=");
    for line in text.split('\n') {
        if let Some(value) = line.strip_prefix(&prefix) {
            return if value.is_empty() {
                default.to_owned()
            } else {
                value.to_owned()
            };
        }
    }
    default.to_owned()
}

/// Last non-empty `KEY=` value with `_read_env_value_last` semantics.
fn read_env_value_last(path: &Path, key: &str, default: &str) -> String {
    if is_symlink(path) || !path.is_file() {
        return default.to_owned();
    }
    let Ok(bytes) = fs::read(path) else {
        return default.to_owned();
    };
    let text = String::from_utf8_lossy(&bytes);
    let prefix = format!("{key}=");
    let mut found = default.to_owned();
    for line in text.split('\n') {
        if let Some(value) = line.strip_prefix(&prefix)
            && !value.is_empty()
        {
            value.clone_into(&mut found);
        }
    }
    found
}

/// Port of `_read_env_values`: allowlisted, last-non-empty, default-backed.
fn read_env_values(path: &Path, defaults: &[(&str, &str)]) -> Vec<(String, String)> {
    let mut out: Vec<(String, String)> = defaults
        .iter()
        .map(|(key, value)| ((*key).to_owned(), (*value).to_owned()))
        .collect();
    if is_symlink(path) || !path.is_file() {
        return out;
    }
    let Ok(bytes) = fs::read(path) else {
        return out;
    };
    let text = String::from_utf8_lossy(&bytes);
    for line in text.split('\n') {
        if line.is_empty() {
            continue;
        }
        let Some((key, value)) = line.split_once('=') else {
            continue;
        };
        if value.is_empty() {
            continue;
        }
        if let Some(slot) = out
            .iter_mut()
            .find(|(existing, _)| existing == key && defaults.iter().any(|(d, _)| *d == key))
        {
            value.clone_into(&mut slot.1);
        }
    }
    out
}

fn env_value<'a>(rows: &'a [(String, String)], key: &str) -> &'a str {
    rows.iter()
        .find(|(existing, _)| existing == key)
        .map_or("", |(_, value)| value.as_str())
}

/// Port of `_copy_if_file`.
fn copy_if_file(source: &Path, dest: &Path) {
    if source.is_file() && !is_symlink(source) {
        let _ = fs::copy(source, dest);
    }
}

/// UTC `%Y-%m-%dT%H:%M:%SZ` stamp for the terminal-state wire file. The parity
/// harness normalizes RFC 3339 timestamps, so only the format is load-bearing.
fn utc_now_stamp() -> String {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let days = i64::try_from(secs / 86_400).unwrap_or(0);
    let rem = secs % 86_400;
    let (hour, minute, second) = (rem / 3600, (rem % 3600) / 60, rem % 60);
    let (year, month, day) = civil_from_days(days);
    format!("{year:04}-{month:02}-{day:02}T{hour:02}:{minute:02}:{second:02}Z")
}

/// Howard Hinnant's `civil_from_days` algorithm.
const fn civil_from_days(days: i64) -> (i64, i64, i64) {
    let z = days + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let year = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = doy - (153 * mp + 2) / 5 + 1;
    let month = if mp < 10 { mp + 3 } else { mp - 9 };
    (if month <= 2 { year + 1 } else { year }, month, day)
}

// ---------------------------------------------------------------------------
// read-result-env
// ---------------------------------------------------------------------------

fn read_result_env_usage() {
    eprintln!(
        "usage: read-result-env.sh --input PATH [--fallback-input PATH] --allow KEY ... --output PATH"
    );
}

struct ReadResultEnvArgs {
    input_path: String,
    fallback_input: String,
    allow: Vec<String>,
    output_path: String,
    extra: bool,
}

/// Parse the `read-result-env` argv like the frozen `argparse` parser: bind
/// `--input`/`--fallback-input`/`--output` (repeatable `--allow`), treat any
/// other token as `extra`. A trailing value-less option mirrors `argparse`'s
/// `SystemExit` (`None`).
fn parse_read_result_env_args(argv: &[String]) -> Option<ReadResultEnvArgs> {
    let mut parsed = ReadResultEnvArgs {
        input_path: String::new(),
        fallback_input: String::new(),
        allow: Vec::new(),
        output_path: String::new(),
        extra: false,
    };
    let mut index = 0;
    while index < argv.len() {
        let token = argv[index].as_str();
        let (name, inline_value) = match token.split_once('=') {
            Some((name, value)) if name.starts_with("--") => (name, Some(value.to_owned())),
            _ => (token, None),
        };
        let bound = matches!(
            name,
            "--input" | "--fallback-input" | "--allow" | "--output"
        );
        if bound {
            let value = if let Some(value) = inline_value {
                value
            } else {
                index += 1;
                match argv.get(index) {
                    Some(value) => value.clone(),
                    None => return None,
                }
            };
            match name {
                "--input" => parsed.input_path = value,
                "--fallback-input" => parsed.fallback_input = value,
                "--allow" => parsed.allow.push(value),
                _ => parsed.output_path = value,
            }
            index += 1;
            continue;
        }
        parsed.extra = true;
        index += 1;
    }
    Some(parsed)
}

/// Port of `_classify_input`.
fn classify_input(path: &Path) -> &'static str {
    if is_symlink(path) {
        "symlink"
    } else if !path.exists() {
        "missing"
    } else if !path.is_file() {
        "nonregular"
    } else {
        "regular"
    }
}

/// Port of `_preferred_bgjob_result_input`.
fn preferred_bgjob_result_input(input_path: &Path) -> Option<PathBuf> {
    let name = input_path.file_name()?.to_string_lossy().into_owned();
    let step = match name.as_str() {
        ".design-step4-tail-result.env" => "design-step4-tail",
        ".design-step5c-status.env" => "design-step5c",
        ".design-step-final-summary-result.env" => "design-step-final-summary",
        _ => return None,
    };
    let candidate = input_path
        .parent()?
        .join(BGJOB_TMP_SUBDIR)
        .join(format!("{step}{BGJOB_RESULT_ENV_SUFFIX}"));
    if classify_input(&candidate) == "regular" {
        Some(candidate)
    } else {
        None
    }
}

/// Port of `_resolve_read_result_env_source`.
fn resolve_read_result_env_source(
    input_path: &Path,
    fallback_path: Option<&Path>,
) -> (Option<PathBuf>, String) {
    if let Some(preferred) = preferred_bgjob_result_input(input_path) {
        return (Some(preferred), String::new());
    }
    let primary_kind = classify_input(input_path);
    if primary_kind == "regular" {
        return (Some(input_path.to_path_buf()), String::new());
    }
    let Some(fallback_path) = fallback_path else {
        return (None, String::new());
    };
    let mut warning = String::new();
    if primary_kind == "symlink" {
        if input_path
            .to_string_lossy()
            .ends_with(".design-init-runparams-result.env")
        {
            "**⚠ Step 0b: design-init-runparams result env is a symlink; refusing to source**"
                .clone_into(&mut warning);
        } else {
            warning = format!(
                "WARN=read-result-env input is a symlink; refusing primary path: {}",
                input_path.display()
            );
        }
    }
    if is_symlink(fallback_path) || !fallback_path.is_file() {
        return (None, warning);
    }
    (Some(fallback_path.to_path_buf()), warning)
}

/// Port of `_replay_warn_error`: emit each `WARN`/`ERROR` row to stdout.
fn replay_warn_error(path: &Path) {
    let Ok(bytes) = fs::read(path) else {
        return;
    };
    let text = String::from_utf8_lossy(&bytes);
    let document =
        KvDocument::parse(&text, ParseOptions::legacy()).expect("legacy parser is non-rejecting");
    for row in document.rows() {
        if row.key() == "WARN" || row.key() == "ERROR" {
            println!("{}={}", row.key(), row.value());
        }
    }
}

/// The `read-result-env` entry point.
pub fn read_result_env(arguments: &[OsString]) -> ExitCode {
    let argv = utf8_arguments(arguments);
    let Some(parsed) = parse_read_result_env_args(&argv) else {
        read_result_env_usage();
        return ExitCode::from(1);
    };
    if parsed.extra
        || parsed.input_path.is_empty()
        || parsed.output_path.is_empty()
        || parsed.allow.iter().any(|key| !valid_var_name(key))
    {
        read_result_env_usage();
        return ExitCode::from(1);
    }
    let input_path = PathBuf::from(&parsed.input_path);
    let fallback_path = if parsed.fallback_input.is_empty() {
        None
    } else {
        Some(PathBuf::from(&parsed.fallback_input))
    };
    let (source_path, warning) =
        resolve_read_result_env_source(&input_path, fallback_path.as_deref());
    if !warning.is_empty() {
        println!("{warning}");
    }
    let Some(source_path) = source_path else {
        return ExitCode::from(1);
    };
    let output_path = PathBuf::from(&parsed.output_path);
    let parent = match output_path.parent() {
        Some(parent) if parent.is_dir() => parent.to_path_buf(),
        _ => return ExitCode::from(1),
    };
    // Atomic tempfile write, mirroring `tempfile.mkstemp` + `replace`.
    let output_name = output_path
        .file_name()
        .map_or_else(String::new, |name| name.to_string_lossy().into_owned());
    let temp = parent.join(format!(
        ".{output_name}.{}.{}",
        std::process::id(),
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(0)
    ));
    replay_warn_error(&source_path);
    let Ok(pairs) = phase_driver_read_result_env(&source_path, &parsed.allow) else {
        return ExitCode::from(1);
    };
    let mut body = String::new();
    for (key, value) in &pairs {
        body.push_str(key);
        body.push('=');
        body.push_str(&quote_single(value));
        body.push('\n');
    }
    if fs::write(&temp, &body).is_err() {
        let _ = fs::remove_file(&temp);
        return ExitCode::from(1);
    }
    if fs::rename(&temp, &output_path).is_err() {
        let _ = fs::remove_file(&temp);
        return ExitCode::from(1);
    }
    ExitCode::SUCCESS
}

// ---------------------------------------------------------------------------
// stage-terminal-state
// ---------------------------------------------------------------------------

const STAGE_ERR_PREFIX: &str = "design-stage-terminal-state.sh:";

struct StageArgs {
    design_tmpdir: String,
    outcome: String,
    step: String,
    phase: String,
    site: String,
    trigger: String,
    bail_reason: String,
    exit_code: String,
    source_script: String,
    failure_detail_log: String,
    root_cause_hint: String,
    summary_outcome: String,
    evidence_ref: String,
    extras: Vec<(String, String)>,
    extra_token: Option<String>,
    missing_required: bool,
}

const STAGE_VALUE_FLAGS: [&str; 24] = [
    "--design-tmpdir",
    "--outcome",
    "--step",
    "--phase",
    "--site",
    "--trigger",
    "--bail-reason",
    "--exit-code",
    "--source-script",
    "--failure-detail-log",
    "--root-cause-hint",
    "--summary-outcome",
    "--evidence-ref",
    "--publish-attempt-id",
    "--publish-rc-source",
    "--latest-phase",
    "--plan-write-ok",
    "--publish-ok",
    "--renamed",
    "--log-publish-attempted",
    "--log-publish-completed",
    "--designed-admission-ready",
    "--pr-url",
    "--recovery-branch",
];

const STAGE_EXTRA_FLAGS: [(&str, &str); 11] = [
    ("--publish-attempt-id", "PUBLISH_ATTEMPT_ID"),
    ("--publish-rc-source", "PUBLISH_RC_SOURCE"),
    ("--latest-phase", "LATEST_PHASE"),
    ("--plan-write-ok", "PLAN_WRITE_OK"),
    ("--publish-ok", "PUBLISH_OK"),
    ("--renamed", "RENAMED"),
    ("--log-publish-attempted", "LOG_PUBLISH_ATTEMPTED"),
    ("--log-publish-completed", "LOG_PUBLISH_COMPLETED"),
    ("--designed-admission-ready", "DESIGNED_ADMISSION_READY"),
    ("--pr-url", "PR_URL"),
    ("--recovery-branch", "RECOVERY_BRANCH"),
];

#[allow(clippy::too_many_lines)] // One argparse namespace ported flag for flag.
fn parse_stage_args(argv: &[String]) -> Option<StageArgs> {
    let mut parsed = StageArgs {
        design_tmpdir: String::new(),
        outcome: String::new(),
        step: String::new(),
        phase: String::new(),
        site: String::new(),
        trigger: String::new(),
        bail_reason: String::new(),
        exit_code: String::new(),
        source_script: String::new(),
        failure_detail_log: String::new(),
        root_cause_hint: String::new(),
        summary_outcome: String::new(),
        evidence_ref: String::new(),
        extras: Vec::new(),
        extra_token: None,
        missing_required: false,
    };
    let mut seen: std::collections::BTreeMap<String, String> = std::collections::BTreeMap::new();
    let mut index = 0;
    while index < argv.len() {
        let token = argv[index].as_str();
        let (name, inline_value) = match token.split_once('=') {
            Some((name, value)) if name.starts_with("--") => (name, Some(value.to_owned())),
            _ => (token, None),
        };
        if STAGE_VALUE_FLAGS.contains(&name) {
            let value = if let Some(value) = inline_value {
                value
            } else {
                index += 1;
                match argv.get(index) {
                    Some(value) => value.clone(),
                    None => return None,
                }
            };
            let _ = seen.insert(name.to_owned(), value);
            index += 1;
            continue;
        }
        if parsed.extra_token.is_none() {
            parsed.extra_token = Some(token.to_owned());
        }
        index += 1;
    }
    let get = |key: &str| seen.get(key).cloned().unwrap_or_default();
    // argparse required=True flags: absence raises SystemExit(2).
    for required in [
        "--design-tmpdir",
        "--outcome",
        "--step",
        "--phase",
        "--site",
        "--trigger",
        "--bail-reason",
        "--exit-code",
        "--source-script",
    ] {
        if !seen.contains_key(required) {
            parsed.missing_required = true;
        }
    }
    parsed.design_tmpdir = get("--design-tmpdir");
    parsed.outcome = get("--outcome");
    parsed.step = get("--step");
    parsed.phase = get("--phase");
    parsed.site = get("--site");
    parsed.trigger = get("--trigger");
    parsed.bail_reason = get("--bail-reason");
    parsed.exit_code = get("--exit-code");
    parsed.source_script = get("--source-script");
    parsed.failure_detail_log = get("--failure-detail-log");
    parsed.root_cause_hint = get("--root-cause-hint");
    parsed.summary_outcome = get("--summary-outcome");
    parsed.evidence_ref = get("--evidence-ref");
    for (flag, key) in STAGE_EXTRA_FLAGS {
        parsed.extras.push((key.to_owned(), get(flag)));
    }
    Some(parsed)
}

/// Port of `_safe_failure_detail_log`.
fn safe_failure_detail_log(raw: &str, design_tmpdir: &Path) -> Result<(), String> {
    if raw.is_empty() {
        return Ok(());
    }
    let candidate = Path::new(raw);
    let resolved = resolve_like_python(candidate);
    let under = resolved == design_tmpdir
        || resolved
            .ancestors()
            .any(|ancestor| ancestor == design_tmpdir);
    if !under {
        return Err("--failure-detail-log must be under --design-tmpdir".to_owned());
    }
    if is_symlink(candidate) {
        return Err("--failure-detail-log must not be a symlink".to_owned());
    }
    if !candidate.is_file() {
        return Err("--failure-detail-log must be a regular file".to_owned());
    }
    if !readable(candidate) {
        return Err("--failure-detail-log must be readable".to_owned());
    }
    Ok(())
}

fn readable(path: &Path) -> bool {
    fs::File::open(path).is_ok()
}

/// Port of `_safe_evidence_ref`.
fn safe_evidence_ref(raw: &str) -> Result<(), String> {
    if raw.is_empty() {
        return Ok(());
    }
    let has_control = raw.contains('\n') || raw.contains('\r');
    let has_unsafe_prefix =
        raw.starts_with("http://") || raw.starts_with("https://") || raw.starts_with('/');
    let has_unsafe_body = raw.contains("..") || raw.contains(' ') || raw.contains('`');
    if has_control || has_unsafe_prefix || has_unsafe_body {
        return Err("--evidence-ref is not a safe token".to_owned());
    }
    Ok(())
}

/// The `stage-terminal-state` entry point.
pub fn stage_terminal_state(arguments: &[OsString]) -> ExitCode {
    stage_terminal_state_with(arguments, &LiveStep0Runner)
}

fn stage_terminal_state_with(arguments: &[OsString], runner: &dyn Step0Runner) -> ExitCode {
    let argv = utf8_arguments(arguments);
    // `stage_terminal_state_main`: extract `--design-tmpdir` and validate before
    // dispatch, matching the frozen wrapper's pre-quiet validation.
    let mut design_tmpdir_arg = String::new();
    if argv.len() >= 2 {
        for index in 0..argv.len() - 1 {
            if argv[index] == "--design-tmpdir" {
                design_tmpdir_arg.clone_from(&argv[index + 1]);
                break;
            }
        }
    }
    if let Err(message) = validate_core_design_tmpdir(&design_tmpdir_arg) {
        eprintln!("{STAGE_ERR_PREFIX} {message}");
        return ExitCode::from(2);
    }
    let plugin_root = PathBuf::from(std::env::var_os("CLAUDE_PLUGIN_ROOT").unwrap_or_default());
    let (code, _rows) = stage_terminal_state_core(runner, &plugin_root, &argv);
    exit_from_i32(code)
}

#[allow(clippy::too_many_lines)] // The `stage_terminal_state_core` body ported branch for branch.
fn stage_terminal_state_core(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    argv: &[String],
) -> (i32, Vec<String>) {
    let Some(parsed) = parse_stage_args(argv) else {
        return (2, Vec::new());
    };
    if let Some(extra) = &parsed.extra_token {
        core_diagnostic(&format!("{STAGE_ERR_PREFIX} unknown option: {extra}"));
        return (2, Vec::new());
    }
    if parsed.missing_required {
        return (2, Vec::new());
    }
    let design_tmpdir = match validate_core_design_tmpdir(&parsed.design_tmpdir) {
        Ok(path) => path,
        Err(message) => {
            core_diagnostic(&format!("{STAGE_ERR_PREFIX} {message}"));
            return (2, Vec::new());
        }
    };
    let required = [
        ("outcome", &parsed.outcome),
        ("step", &parsed.step),
        ("phase", &parsed.phase),
        ("site", &parsed.site),
        ("trigger", &parsed.trigger),
        ("bail", &parsed.bail_reason),
        ("source-script", &parsed.source_script),
    ];
    let base = stall_args(&design_tmpdir);
    for (kind, value) in required {
        if value.is_empty() {
            core_diagnostic(&format!("{STAGE_ERR_PREFIX} {kind} is required"));
            return (2, Vec::new());
        }
        let mut token_args = base.clone();
        token_args.extend([
            "--token-kind".to_owned(),
            kind.to_owned(),
            "--value".to_owned(),
            value.clone(),
        ]);
        if run_stall(
            runner,
            plugin_root,
            "validate-token",
            &token_args,
            None,
            None,
        ) != 0
        {
            core_diagnostic(&format!(
                "{STAGE_ERR_PREFIX} {kind} is not a valid token: {value}"
            ));
            return (2, Vec::new());
        }
    }
    for (kind, value) in [
        ("root-cause", &parsed.root_cause_hint),
        ("outcome", &parsed.summary_outcome),
    ] {
        if value.is_empty() {
            continue;
        }
        let mut token_args = base.clone();
        token_args.extend([
            "--token-kind".to_owned(),
            kind.to_owned(),
            "--value".to_owned(),
            value.clone(),
        ]);
        if run_stall(
            runner,
            plugin_root,
            "validate-token",
            &token_args,
            None,
            None,
        ) != 0
        {
            core_diagnostic(&format!(
                "{STAGE_ERR_PREFIX} {kind} is not a valid token: {value}"
            ));
            return (2, Vec::new());
        }
    }
    if parsed.exit_code != "unknown" && !parsed.exit_code.chars().all(|c| c.is_ascii_digit()) {
        core_diagnostic(&format!(
            "{STAGE_ERR_PREFIX} --exit-code must be an integer or unknown"
        ));
        return (2, Vec::new());
    }
    if let Err(message) = safe_failure_detail_log(&parsed.failure_detail_log, &design_tmpdir) {
        core_diagnostic(&format!("{STAGE_ERR_PREFIX} {message}"));
        return (2, Vec::new());
    }
    if let Err(message) = safe_evidence_ref(&parsed.evidence_ref) {
        core_diagnostic(&format!("{STAGE_ERR_PREFIX} {message}"));
        return (2, Vec::new());
    }
    let state_file = design_tmpdir.join("design-failure-terminal-state.env");
    if state_file.exists() || is_symlink(&state_file) {
        if is_symlink(&state_file) || !state_file.is_file() {
            core_diagnostic(&format!(
                "{STAGE_ERR_PREFIX} existing terminal state is unsafe"
            ));
            return (2, Vec::new());
        }
        let old = read_env_values(
            &state_file,
            &[("FAILURE_OUTCOME", ""), ("SITE", ""), ("TRIGGER", "")],
        );
        if env_value(&old, "FAILURE_OUTCOME") != parsed.outcome
            || env_value(&old, "SITE") != parsed.site
            || env_value(&old, "TRIGGER") != parsed.trigger
        {
            let rows = vec![
                ("STAGED".to_owned(), "false".to_owned()),
                ("PRESERVED".to_owned(), "true".to_owned()),
                (
                    "TERMINAL_STATE_FILE".to_owned(),
                    state_file.display().to_string(),
                ),
            ];
            emit_rows(&rows);
            return (0, rows.iter().map(|(k, v)| format!("{k}={v}")).collect());
        }
    }
    let candidate = design_tmpdir.join(format!(
        "design-failure-terminal-state.env.candidate.{}",
        std::process::id()
    ));
    let mut lines: Vec<String> = vec![
        "DESIGN_FAILURE_VERSION=1".to_owned(),
        "DESIGN_FAILURE_KIND=terminal".to_owned(),
        format!("FAILURE_OUTCOME={}", parsed.outcome),
        format!("STALL_STEP={}", parsed.step),
        format!("PHASE={}", parsed.phase),
        format!("SITE={}", parsed.site),
        format!("TRIGGER={}", parsed.trigger),
        format!("BAIL_REASON={}", parsed.bail_reason),
        format!("EXIT_CODE={}", parsed.exit_code),
        format!("FAILURE_DETAIL_LOG={}", parsed.failure_detail_log),
        format!("SOURCE_SCRIPT={}", parsed.source_script),
    ];
    if !parsed.root_cause_hint.is_empty() {
        lines.push(format!("ROOT_CAUSE_HINT={}", parsed.root_cause_hint));
    }
    if !parsed.summary_outcome.is_empty() {
        lines.push(format!("SUMMARY_OUTCOME={}", parsed.summary_outcome));
    }
    for (key, value) in &parsed.extras {
        if !value.is_empty() {
            lines.push(format!("{key}={value}"));
        }
    }
    lines.push(format!("OCCURRED_AT={}", utc_now_stamp()));
    if !parsed.evidence_ref.is_empty() {
        lines.push(format!("EVIDENCE_REF={}", parsed.evidence_ref));
    }
    let body = format!("{}\n", lines.join("\n"));
    if fs::write(&candidate, &body).is_err() {
        core_diagnostic(&format!(
            "{STAGE_ERR_PREFIX} candidate terminal state failed validation"
        ));
        return (2, Vec::new());
    }
    let mut validate_args = base;
    validate_args.extend([
        "--primary-state-file".to_owned(),
        candidate.display().to_string(),
    ]);
    if run_stall(
        runner,
        plugin_root,
        "validate-terminal-state",
        &validate_args,
        None,
        None,
    ) != 0
    {
        let _ = fs::remove_file(&candidate);
        core_diagnostic(&format!(
            "{STAGE_ERR_PREFIX} candidate terminal state failed validation"
        ));
        return (2, Vec::new());
    }
    let _ = fs::rename(&candidate, &state_file);
    let rows = vec![
        ("STAGED".to_owned(), "true".to_owned()),
        (
            "TERMINAL_STATE_FILE".to_owned(),
            state_file.display().to_string(),
        ),
    ];
    emit_rows(&rows);
    (0, rows.iter().map(|(k, v)| format!("{k}={v}")).collect())
}

/// Emit `KEY=value` rows to stdout, mirroring `_emit_core_kvs`.
fn emit_rows(rows: &[(String, String)]) {
    for (key, value) in rows {
        println!("{key}={value}");
    }
}

// ---------------------------------------------------------------------------
// failure-report
// ---------------------------------------------------------------------------

const FAILURE_ERR_PREFIX: &str = "design-failure-report.sh:";

/// The `failure-report` entry point.
pub fn failure_report(arguments: &[OsString]) -> ExitCode {
    failure_report_with(arguments, &LiveStep0Runner)
}

fn failure_report_with(arguments: &[OsString], runner: &dyn Step0Runner) -> ExitCode {
    let argv = utf8_arguments(arguments);
    let mut design_tmpdir_arg = String::new();
    if argv.len() >= 2 {
        for index in 0..argv.len() - 1 {
            if argv[index] == "--design-tmpdir" {
                design_tmpdir_arg.clone_from(&argv[index + 1]);
                break;
            }
        }
    }
    if let Err(message) = validate_core_design_tmpdir(&design_tmpdir_arg) {
        eprintln!("{FAILURE_ERR_PREFIX} {message}");
        return ExitCode::from(2);
    }
    let plugin_root = PathBuf::from(std::env::var_os("CLAUDE_PLUGIN_ROOT").unwrap_or_default());
    let (code, _rows) = failure_report_core(runner, &plugin_root, &argv);
    exit_from_i32(code)
}

struct FailureArgs {
    design_tmpdir: String,
    outcome: String,
    repo: String,
    extra: Option<String>,
}

fn parse_failure_args(argv: &[String]) -> FailureArgs {
    let mut parsed = FailureArgs {
        design_tmpdir: String::new(),
        outcome: String::new(),
        repo: String::new(),
        extra: None,
    };
    let mut index = 0;
    while index < argv.len() {
        let token = argv[index].as_str();
        let (name, inline_value) = match token.split_once('=') {
            Some((name, value)) if name.starts_with("--") => (name, Some(value.to_owned())),
            _ => (token, None),
        };
        if matches!(
            name,
            "--design-tmpdir" | "--outcome" | "--repo" | "--issue" | "--run-id"
        ) {
            let value = inline_value.unwrap_or_else(|| {
                index += 1;
                argv.get(index).cloned().unwrap_or_default()
            });
            match name {
                "--design-tmpdir" => parsed.design_tmpdir = value,
                "--outcome" => parsed.outcome = value,
                "--repo" => parsed.repo = value,
                _ => {}
            }
            index += 1;
            continue;
        }
        if parsed.extra.is_none() {
            parsed.extra = Some(token.to_owned());
        }
        index += 1;
    }
    parsed
}

/// Terminal-state paths and derived artifact paths for one failure report.
struct FailureCtx<'a> {
    runner: &'a dyn Step0Runner,
    plugin_root: PathBuf,
    design_tmpdir: PathBuf,
    outcome: String,
    repo: String,
}

impl FailureCtx<'_> {
    fn path(&self, name: &str) -> PathBuf {
        self.design_tmpdir.join(name)
    }

    fn base(&self) -> Vec<String> {
        stall_args(&self.design_tmpdir)
    }

    fn compose_env(&self) -> PathBuf {
        self.path("design-failure-compose.env")
    }

    fn compose_env_key(&self, key: &str) -> String {
        let compose = self.compose_env();
        if key == "STALL_RECOVERY_REPORT_STATUS" {
            read_env_value_last(&compose, key, "")
        } else {
            read_env_value(&compose, key, "")
        }
    }

    fn append_run_log_audit(&self, reason: &str) {
        let detail = self.path("design-failure-audit.log");
        let _ = fs::write(&detail, format!("design failure report audit: {reason}\n"));
        self.append_failure(
            "design failure report",
            "design-failure-report.sh",
            "0",
            "Warnings",
            &detail,
        );
    }

    fn append_failure(
        &self,
        site: &str,
        tool: &str,
        exit_code: &str,
        category: &str,
        output_file: &Path,
    ) {
        let args = vec![
            "run-log".to_owned(),
            "append-failure".to_owned(),
            "--log".to_owned(),
            self.path("execution-issues.md").display().to_string(),
            "--site".to_owned(),
            site.to_owned(),
            "--tool".to_owned(),
            tool.to_owned(),
            "--exit-code".to_owned(),
            exit_code.to_owned(),
            "--category".to_owned(),
            category.to_owned(),
            "--output-file".to_owned(),
            output_file.display().to_string(),
            "--redact".to_owned(),
        ];
        let _ = self.runner.run(&self.plugin_root, &args, &[], false);
    }

    fn write_operator_action_audit(&self, reason: &str) {
        let operator_sentinel = self.path("design-failure-operator-action.env");
        let operator_chat = self.path("design-failure-operator-action-chat.md");
        let _ = fs::write(
            &operator_sentinel,
            format!(
                "DESIGN_FAILURE_OPERATOR_ACTION=true\nREASON={reason}\nOUTCOME={}\n",
                self.outcome
            ),
        );
        let _ = fs::write(
            &operator_chat,
            format!(
                "**\u{2139} /design auto-report skipped:** operator action or cancellation outcome `{}`.\n\nNo public larch bug was filed. The skip was recorded in the run log.\n",
                self.outcome
            ),
        );
        self.append_run_log_audit(&format!("operator-action:{reason}"));
    }

    fn write_fallback_chat(&self, reason: &str) {
        let chat_print = self.path("design-failure-chat-print.md");
        let _ = fs::write(
            &chat_print,
            format!(
                "### {} /design report fallback required\n\nThe /design failure reporter could not safely file an issue.\n\n| Field | Value |\n|---|---|\n| Outcome | `{}` |\n| Reason | `{reason}` |\n\nUse the local artifacts in `DESIGN_TMPDIR` to investigate. This fallback contains no log tail.\n",
                bug_prefix(),
                self.outcome
            ),
        );
        println!("DESIGN_FAILURE_REPORT_DECISION=fallback-print-required");
        println!("DESIGN_FAILURE_REPORT_REASON={reason}");
        println!("DESIGN_FAILURE_REPORT_ARTIFACT={}", chat_print.display());
    }

    fn tier_a_forked(&self) -> bool {
        for name in ["ship-pr-state.sh", "finalize-state.sh", "source-env.sh"] {
            let value = read_env_value(&self.path(name), "FORKED_TARGET", "");
            if !value.is_empty() {
                return matches!(value.as_str(), "true" | "1" | "yes" | "TRUE" | "True");
            }
        }
        false
    }

    fn resolve_working_tree_root(&self) -> String {
        for key in ["CLAUDE_PROJECT_DIR", "REPO_ROOT"] {
            if let Ok(value) = std::env::var(key)
                && !value.is_empty()
            {
                return value;
            }
        }
        let root = read_env_value(&self.path("source-env.sh"), "REPO_ROOT", "");
        if !root.is_empty() {
            return root;
        }
        // `repo_root_probe`: git rev-parse --show-toplevel.
        std::process::Command::new("git") // lint-subprocess-via-runner: ok mirrors the frozen repo_root_probe git toplevel probe
            .args(["rev-parse", "--show-toplevel"])
            .output()
            .ok()
            .filter(|out| out.status.success())
            .map(|out| String::from_utf8_lossy(&out.stdout).trim().to_owned())
            .unwrap_or_default()
    }

    fn tier_a_eligible(&self) -> bool {
        if self.tier_a_forked() {
            return false;
        }
        let root = self.resolve_working_tree_root();
        if root.is_empty() {
            return false;
        }
        let mut args = self.base();
        args.extend(["--working-tree-root".to_owned(), root]);
        let result = run_stall_capture(self.runner, &self.plugin_root, "is-larch-dev-clone", &args);
        result.code == 0
            && result
                .stdout
                .lines()
                .any(|line| line == "LARCH_DEV_CLONE=true")
    }

    fn report_surface(&self) -> &'static str {
        if self.tier_a_eligible() {
            "issue-input"
        } else {
            "chat-print"
        }
    }

    fn report_output_file(&self, surface: &str) -> PathBuf {
        if surface == "issue-input" {
            self.path("design-failure-issue-input.md")
        } else {
            self.path("design-failure-chat-print.md")
        }
    }

    fn populate_sensitive(&self, class_path: Option<&Path>) -> bool {
        let default_class = self.path("design-failure-classification.env");
        let seed = self.path("design-failure-classification.seed.env");
        let actual_class = class_path.map_or(default_class, Path::to_path_buf);
        let actual_class = if actual_class.is_file() {
            actual_class
        } else {
            let _ = fs::write(&seed, "");
            seed
        };
        let mut args = self.base();
        args.extend([
            "--sensitive-corpus-file".to_owned(),
            self.path("design-failure-sensitive-corpus.env")
                .display()
                .to_string(),
            "--classification-file".to_owned(),
            actual_class.display().to_string(),
            "--attempts-file".to_owned(),
            self.path("design-failure-attempts.env")
                .display()
                .to_string(),
            "--escalation-ledger-file".to_owned(),
            self.path("design-failure-escalation-ledger.tsv")
                .display()
                .to_string(),
            "--escalation-fallback-file".to_owned(),
            self.path("design-failure-escalation-fallback.tsv")
                .display()
                .to_string(),
            "--record-failure-marker".to_owned(),
            self.path("design-failure-escalation-record-failure.env")
                .display()
                .to_string(),
        ]);
        run_stall(
            self.runner,
            &self.plugin_root,
            "populate-sensitive-corpus",
            &args,
            Some(&self.path("design-failure-populate-sensitive.stdout.log")),
            Some(&self.path("design-failure-populate-sensitive.stderr.log")),
        ) == 0
    }
}

const fn bug_prefix() -> &'static str {
    "[BUG]"
}

/// Port of `_emit_skip`.
fn emit_skip(reason: &str) {
    println!("DESIGN_FAILURE_REPORT_DECISION=skip");
    println!("DESIGN_FAILURE_REPORT_REASON={reason}");
}

#[allow(clippy::too_many_lines)] // The `failure_report_core` state machine ported branch for branch.
fn failure_report_core(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    argv: &[String],
) -> (i32, Vec<String>) {
    let parsed = parse_failure_args(argv);
    if let Some(extra) = &parsed.extra {
        core_diagnostic(&format!("{FAILURE_ERR_PREFIX} unknown option: {extra}"));
        return (2, Vec::new());
    }
    let design_tmpdir = match validate_core_design_tmpdir(&parsed.design_tmpdir) {
        Ok(path) => path,
        Err(message) => {
            core_diagnostic(&format!("{FAILURE_ERR_PREFIX} {message}"));
            return (2, Vec::new());
        }
    };
    let ctx = FailureCtx {
        runner,
        plugin_root: plugin_root.to_path_buf(),
        design_tmpdir,
        outcome: parsed.outcome.clone(),
        repo: parsed.repo.clone(),
    };
    let outcome = parsed.outcome.as_str();
    let terminal_state = ctx.path("design-failure-terminal-state.env");
    let terminal_sentinel = ctx.path("design-failure-terminal-report.env");
    let escalation_sentinel = ctx.path("design-failure-escalation-success.env");
    let operator_sentinel = ctx.path("design-failure-operator-action.env");
    let operator_chat = ctx.path("design-failure-operator-action-chat.md");

    if reconcile_failed_publish_tail_report(&ctx, &terminal_sentinel, outcome) {
        return (0, Vec::new());
    }
    if terminal_sentinel.exists() {
        emit_skip("terminal-sentinel-present");
        return (0, Vec::new());
    }
    if escalation_sentinel.exists() {
        emit_skip("escalation-sentinel-present");
        return (0, Vec::new());
    }
    if outcome.starts_with("cancelled-") {
        ctx.write_operator_action_audit("cancelled-outcome");
        println!("DESIGN_FAILURE_REPORT_DECISION=operator-action-skip");
        println!("DESIGN_FAILURE_REPORT_ARTIFACT={}", operator_chat.display());
        return (0, Vec::new());
    }
    let terminal_outcomes = [
        "failed-plan-write",
        "failed-publish",
        "failed-postplan",
        "failed-clarify",
        "failed-judge-panel",
        "failed-publish-tail",
    ];
    if terminal_outcomes.contains(&outcome) {
        return failure_report_terminal(&ctx, &terminal_state);
    }
    if outcome != "approved" && outcome != "approved-partition" {
        emit_skip("outcome-not-success-allowlist");
        return (0, Vec::new());
    }
    if operator_sentinel.exists() {
        let chat_empty = operator_chat
            .metadata()
            .map(|m| m.len() == 0)
            .unwrap_or(true);
        if chat_empty {
            ctx.write_operator_action_audit("operator-sentinel-present");
        }
        emit_skip("operator-action");
        return (0, Vec::new());
    }
    if !escalation_evidence_present(&ctx) {
        emit_skip("no-escalation-evidence");
        return (0, Vec::new());
    }
    failure_report_escalation(&ctx)
}

#[allow(clippy::too_many_lines)] // The terminal-failure branch ported branch for branch.
fn failure_report_terminal(ctx: &FailureCtx, terminal_state: &Path) -> (i32, Vec<String>) {
    if !terminal_state.exists() {
        ctx.write_fallback_chat("missing-terminal-state");
        return (0, Vec::new());
    }
    let mut validate_args = ctx.base();
    validate_args.extend([
        "--primary-state-file".to_owned(),
        terminal_state.display().to_string(),
    ]);
    if run_stall(
        ctx.runner,
        &ctx.plugin_root,
        "validate-terminal-state",
        &validate_args,
        None,
        Some(&ctx.path("design-failure-validate-terminal-state.stderr.log")),
    ) != 0
    {
        ctx.append_run_log_audit("invalid-terminal-state");
        ctx.write_fallback_chat("invalid-terminal-state");
        return (0, Vec::new());
    }
    let state = read_env_values(
        terminal_state,
        &[("FAILURE_OUTCOME", ""), ("SUMMARY_OUTCOME", "")],
    );
    let failure_outcome = env_value(&state, "FAILURE_OUTCOME");
    if !failure_outcome.is_empty() && failure_outcome != ctx.outcome {
        ctx.append_run_log_audit("terminal-state-outcome-mismatch");
        ctx.write_fallback_chat("terminal-state-outcome-mismatch");
        return (0, Vec::new());
    }
    let summary_outcome = env_value(&state, "SUMMARY_OUTCOME");
    if !summary_outcome.is_empty() && summary_outcome != ctx.outcome {
        ctx.append_run_log_audit("terminal-state-summary-mismatch");
        ctx.write_fallback_chat("terminal-state-summary-mismatch");
        return (0, Vec::new());
    }
    prepare_root_cause(ctx, "terminal");
    let mut init_args = ctx.base();
    init_args.extend([
        "--attempts-file".to_owned(),
        ctx.path("design-failure-attempts.env")
            .display()
            .to_string(),
    ]);
    let _ = run_stall(
        ctx.runner,
        &ctx.plugin_root,
        "init-attempts",
        &init_args,
        None,
        None,
    );
    let classify_out = ctx.path("design-failure-classify.env");
    let mut classify_args = ctx.base();
    classify_args.extend(state_overrides(ctx));
    let _ = run_stall(
        ctx.runner,
        &ctx.plugin_root,
        "classify",
        &classify_args,
        Some(&classify_out),
        None,
    );
    let class_file = ctx.path("design-failure-classification.env");
    let _ = fs::copy(&classify_out, &class_file);
    let surface = ctx.report_surface();
    let output = ctx.report_output_file(surface);
    if !ctx.populate_sensitive(Some(&class_file)) {
        ctx.append_run_log_audit("populate-sensitive-corpus-failed");
        ctx.write_fallback_chat("populate-sensitive-corpus-failed");
        return (0, Vec::new());
    }
    let mut compose_args = ctx.base();
    compose_args.extend(state_overrides(ctx));
    compose_args.extend([
        "--report-kind".to_owned(),
        "terminal-failure".to_owned(),
        "--surface".to_owned(),
        surface.to_owned(),
        "--classification-file".to_owned(),
        class_file.display().to_string(),
        "--attempts-file".to_owned(),
        ctx.path("design-failure-attempts.env")
            .display()
            .to_string(),
        "--root-cause-file".to_owned(),
        ctx.path("design-failure-root-cause.md")
            .display()
            .to_string(),
        "--bounded-root-cause-file".to_owned(),
        ctx.path("design-failure-bounded-root-cause.md")
            .display()
            .to_string(),
        "--sensitive-corpus-file".to_owned(),
        ctx.path("design-failure-sensitive-corpus.env")
            .display()
            .to_string(),
        "--output-file".to_owned(),
        output.display().to_string(),
    ]);
    let rc = run_stall(
        ctx.runner,
        &ctx.plugin_root,
        "compose-report",
        &compose_args,
        Some(&ctx.compose_env()),
        Some(&ctx.path("design-failure-compose.stderr.log")),
    );
    if rc != 0 {
        ctx.append_run_log_audit("terminal-compose-failed");
        ctx.write_fallback_chat("terminal-compose-failed");
        return (0, Vec::new());
    }
    ctx.populate_sensitive(Some(&class_file));
    if surface == "issue-input" {
        file_tier_a_after_compose(ctx, &output);
    }
    handle_compose_outcome(
        ctx,
        "terminal-failure",
        "terminal-failure",
        &ctx.path("design-failure-terminal-report.env"),
        surface,
        &output,
    );
    (0, Vec::new())
}

fn failure_report_escalation(ctx: &FailureCtx) -> (i32, Vec<String>) {
    prepare_root_cause(ctx, "escalation");
    let mut init_args = ctx.base();
    init_args.extend([
        "--attempts-file".to_owned(),
        ctx.path("design-failure-attempts.env")
            .display()
            .to_string(),
    ]);
    let _ = run_stall(
        ctx.runner,
        &ctx.plugin_root,
        "init-attempts",
        &init_args,
        None,
        None,
    );
    let surface = ctx.report_surface();
    let output = ctx.report_output_file(surface);
    if !ctx.populate_sensitive(None) {
        ctx.append_run_log_audit("populate-sensitive-corpus-failed");
        ctx.write_fallback_chat("populate-sensitive-corpus-failed");
        return (0, Vec::new());
    }
    let mut compose_args = ctx.base();
    compose_args.extend([
        "--report-kind".to_owned(),
        "escalation-success".to_owned(),
        "--surface".to_owned(),
        surface.to_owned(),
        "--attempts-file".to_owned(),
        ctx.path("design-failure-attempts.env")
            .display()
            .to_string(),
        "--escalation-ledger-file".to_owned(),
        ctx.path("design-failure-escalation-ledger.tsv")
            .display()
            .to_string(),
        "--escalation-fallback-file".to_owned(),
        ctx.path("design-failure-escalation-fallback.tsv")
            .display()
            .to_string(),
        "--record-failure-marker".to_owned(),
        ctx.path("design-failure-escalation-record-failure.env")
            .display()
            .to_string(),
        "--root-cause-file".to_owned(),
        ctx.path("design-failure-root-cause.md")
            .display()
            .to_string(),
        "--bounded-root-cause-file".to_owned(),
        ctx.path("design-failure-bounded-root-cause.md")
            .display()
            .to_string(),
        "--sensitive-corpus-file".to_owned(),
        ctx.path("design-failure-sensitive-corpus.env")
            .display()
            .to_string(),
        "--output-file".to_owned(),
        output.display().to_string(),
    ]);
    let rc = run_stall(
        ctx.runner,
        &ctx.plugin_root,
        "compose-report",
        &compose_args,
        Some(&ctx.compose_env()),
        Some(&ctx.path("design-failure-compose.stderr.log")),
    );
    if rc != 0 {
        ctx.append_run_log_audit("escalation-compose-failed");
        ctx.write_fallback_chat("escalation-compose-failed");
        return (0, Vec::new());
    }
    ctx.populate_sensitive(None);
    if surface == "issue-input" {
        file_tier_a_after_compose(ctx, &output);
    }
    handle_compose_outcome(
        ctx,
        "escalation-success",
        "escalation-success",
        &ctx.path("design-failure-escalation-success.env"),
        surface,
        &output,
    );
    (0, Vec::new())
}

fn state_overrides(ctx: &FailureCtx) -> Vec<String> {
    let mut out = vec![
        "--primary-state-file".to_owned(),
        ctx.path("design-failure-terminal-state.env")
            .display()
            .to_string(),
        "--session-env-file".to_owned(),
        ctx.path("source-env.sh").display().to_string(),
    ];
    let finalize = ctx.path("finalize-state.sh");
    if finalize.is_file() {
        out.extend([
            "--finalize-state-file".to_owned(),
            finalize.display().to_string(),
        ]);
    }
    out
}

fn safe_root_summary_from_state(ctx: &FailureCtx) -> String {
    let terminal_state = ctx.path("design-failure-terminal-state.env");
    let values = read_env_values(
        &terminal_state,
        &[
            ("SITE", "unknown"),
            ("TRIGGER", "unknown"),
            ("FAILURE_OUTCOME", &ctx.outcome),
        ],
    );
    format!(
        "{} at {} via {}\n",
        env_value(&values, "FAILURE_OUTCOME"),
        env_value(&values, "SITE"),
        env_value(&values, "TRIGGER"),
    )
}

fn prepare_root_cause(ctx: &FailureCtx, kind: &str) {
    let terminal_state = ctx.path("design-failure-terminal-state.env");
    let root_file = ctx.path("design-failure-root-cause.md");
    let bounded_root_file = ctx.path("design-failure-bounded-root-cause.md");
    let (verdict, summary) = if kind == "terminal" {
        let hint = read_env_value(&terminal_state, "ROOT_CAUSE_HINT", "");
        let verdict = if matches!(
            hint.as_str(),
            "larch-defect" | "environment" | "operator-action"
        ) {
            hint
        } else {
            "larch-defect".to_owned()
        };
        (
            verdict,
            safe_root_summary_from_state(ctx)
                .trim_end_matches('\n')
                .to_owned(),
        )
    } else {
        (
            "larch-defect".to_owned(),
            "design escalation reached main-agent recovery".to_owned(),
        )
    };
    let _ = fs::write(
        &root_file,
        format!(
            "verdict={verdict}\nconfidence=medium\nsummary={summary}\n\nThe reporter used bounded /design state tokens and local ledger evidence only.\n"
        ),
    );
    let _ = fs::copy(&root_file, &bounded_root_file);
    ctx.populate_sensitive(None);
}

/// Port of `_ledger_row_has_escalation_evidence`.
fn ledger_row_has_escalation_evidence(row: &str) -> bool {
    let normalized = row.replace('\t', "\n");
    let document = KvDocument::parse(&normalized, ParseOptions::legacy())
        .expect("legacy parser is non-rejecting");
    let mut site = "";
    let mut trigger = "";
    for kv in document.rows() {
        match kv.key() {
            "site" => site = kv.value(),
            "trigger" => trigger = kv.value(),
            _ => {}
        }
    }
    if site.is_empty() || trigger.is_empty() {
        return false;
    }
    if site != "step3-review" {
        return true;
    }
    STEP3_ESCALATION_FAILURE_STATUSES.contains(&trigger)
}

fn ledger_file_has_escalation_evidence(path: &Path) -> bool {
    if is_symlink(path) || !path.is_file() {
        return false;
    }
    let Ok(bytes) = fs::read(path) else {
        return false;
    };
    let text = String::from_utf8_lossy(&bytes);
    text.lines().any(ledger_row_has_escalation_evidence)
}

fn escalation_evidence_present(ctx: &FailureCtx) -> bool {
    let ledger = ctx.path("design-failure-escalation-ledger.tsv");
    let fallback = ctx.path("design-failure-escalation-fallback.tsv");
    let marker = ctx.path("design-failure-escalation-record-failure.env");
    if ledger_file_has_escalation_evidence(&ledger) {
        return true;
    }
    if ledger_file_has_escalation_evidence(&fallback) {
        return true;
    }
    if marker.metadata().map(|m| m.len() > 0).unwrap_or(false) {
        return true;
    }
    let ex = ctx.path("execution-issues.md");
    if !ex.is_file() {
        return false;
    }
    let Ok(bytes) = fs::read(&ex) else {
        return false;
    };
    let text = String::from_utf8_lossy(&bytes);
    text.lines().any(|line| {
        let trimmed = line.trim_end();
        (trimmed.starts_with("## Tool Failure: record-escalation")
            || trimmed.starts_with("### Tool Failure: record-escalation"))
            && (trimmed == "## Tool Failure: record-escalation"
                || trimmed == "### Tool Failure: record-escalation"
                || trimmed
                    .trim_start_matches('#')
                    .trim_start()
                    .starts_with("Tool Failure: record-escalation "))
    })
}

fn panel_failure_evidence_present(ctx: &FailureCtx) -> bool {
    let terminal_state = ctx.path("design-failure-terminal-state.env");
    if terminal_state.is_file()
        && !is_symlink(&terminal_state)
        && let Ok(bytes) = fs::read(&terminal_state)
    {
        let text = String::from_utf8_lossy(&bytes);
        for line in text.lines() {
            if line == "TRIGGER=panel-failed"
                || line == "TRIGGER=panel-init-failed"
                || line == "BAIL_REASON=panel-failed"
                || line == "BAIL_REASON=panel-init-failed"
            {
                return true;
            }
        }
    }
    for name in [
        "design-failure-escalation-ledger.tsv",
        "design-failure-escalation-fallback.tsv",
        "design-failure-escalation-record-failure.env",
        "execution-issues.md",
    ] {
        let path = ctx.path(name);
        if path.is_file()
            && let Ok(bytes) = fs::read(&path)
        {
            let text = String::from_utf8_lossy(&bytes);
            if text.contains("panel-failed") || text.contains("panel-init-failed") {
                return true;
            }
        }
    }
    false
}

fn file_tier_a_after_compose(ctx: &FailureCtx, body_file: &Path) {
    if !ctx
        .compose_env_key("STALL_RECOVERY_REPORT_STATUS")
        .is_empty()
    {
        return;
    }
    let source_env = ctx.path("source-env.sh");
    let context_file = if source_env.is_file() {
        Some(source_env.as_path())
    } else {
        None
    };
    let run_id = read_env_value(&source_env, "LARCH_RUN_ID", "");
    let decision = check_live_mutation_auth(&LiveMutationRequest {
        context_file,
        operator_mode: false,
        run_id: &run_id,
        trusted_root: Some(&ctx.design_tmpdir),
        test_deny: false,
    });
    if !decision.is_authorized() {
        append_fallback(
            ctx,
            &format!("{LIVE_MUTATION_REFUSAL_REASON}:reporter-unauthorized"),
        );
        return;
    }
    let mut dedup_argv = ctx.base();
    dedup_argv.extend([
        "--body-file".to_owned(),
        body_file.display().to_string(),
        "--create-after-dedup".to_owned(),
        "true".to_owned(),
    ]);
    if let Some(context) = context_file {
        dedup_argv.extend(["--context-file".to_owned(), context.display().to_string()]);
    }
    let dedup_env = ctx.path("design-failure-tier-a-dedup.env");
    let fallback_reason = if run_stall(
        ctx.runner,
        &ctx.plugin_root,
        "dedup-tier-a-report",
        &dedup_argv,
        Some(&dedup_env),
        Some(&ctx.path("design-failure-tier-a-dedup.stderr.log")),
    ) != 0
    {
        "tier-a-dedup-helper-failed".to_owned()
    } else {
        let status = read_env_value(&dedup_env, "STALL_RECOVERY_REPORT_STATUS", "");
        if matches!(
            status.as_str(),
            "dedup-comment" | "dry-run" | "fallback-print-required" | "filed" | "printed"
        ) {
            append_env_file(&ctx.compose_env(), &dedup_env);
            return;
        }
        let clean_status = clean_status_token(&status);
        if clean_status.is_empty() {
            "tier-a-dedup-status-unexpected".to_owned()
        } else {
            format!("tier-a-dedup-status-unexpected:{clean_status}")
        }
    };
    if !fallback_reason.is_empty() {
        append_fallback(ctx, &fallback_reason);
    }
}

fn clean_status_token(status: &str) -> String {
    let mut collapsed = String::new();
    let mut prev_dash = false;
    for ch in status.chars() {
        if ch.is_ascii_alphanumeric() || matches!(ch, '_' | '.' | ':' | '/' | '+' | '-') {
            collapsed.push(ch);
            prev_dash = false;
        } else if !prev_dash {
            collapsed.push('-');
            prev_dash = true;
        }
    }
    let trimmed = collapsed.trim_matches('-');
    trimmed.chars().take(80).collect()
}

fn append_env_file(compose_env: &Path, source: &Path) {
    if let Ok(bytes) = fs::read(source) {
        let mut existing = fs::read(compose_env).unwrap_or_default();
        existing.extend_from_slice(&bytes);
        let _ = fs::write(compose_env, existing);
    }
}

fn append_fallback(ctx: &FailureCtx, reason: &str) {
    let compose_env = ctx.compose_env();
    let mut existing = fs::read(&compose_env).unwrap_or_default();
    existing.extend_from_slice(b"STALL_RECOVERY_REPORT_STATUS=fallback-print-required\n");
    existing
        .extend_from_slice(format!("STALL_RECOVERY_REPORT_FALLBACK_REASON={reason}\n").as_bytes());
    let _ = fs::write(&compose_env, existing);
}

fn handle_compose_outcome(
    ctx: &FailureCtx,
    kind: &str,
    decision: &str,
    sentinel: &Path,
    last_surface: &str,
    last_output: &Path,
) {
    let mut status = ctx.compose_env_key("STALL_RECOVERY_REPORT_STATUS");
    let last_output_nonempty = last_output.metadata().map(|m| m.len() > 0).unwrap_or(false);
    let retry_evidence_present = panel_failure_evidence_present(ctx)
        || (kind == "escalation-success" && escalation_evidence_present(ctx));
    if status.is_empty() && retry_evidence_present && last_output_nonempty {
        if last_surface == "issue-input" {
            file_tier_a_after_compose(ctx, last_output);
            status = ctx.compose_env_key("STALL_RECOVERY_REPORT_STATUS");
        }
        if status.is_empty() {
            ctx.write_fallback_chat("compose-status-missing");
            return;
        }
    }
    if status == "skipped_operator_action" {
        ctx.write_operator_action_audit(&format!("compose-{kind}"));
        println!("DESIGN_FAILURE_REPORT_DECISION=operator-action-skip");
        println!(
            "DESIGN_FAILURE_REPORT_ARTIFACT={}",
            ctx.path("design-failure-operator-action-chat.md").display()
        );
        return;
    }
    if status == "fallback-print-required" {
        let reason = ctx.compose_env_key("STALL_RECOVERY_REPORT_FALLBACK_REASON");
        let reason = if reason.is_empty() {
            format!("compose-{kind}")
        } else {
            reason
        };
        ctx.write_fallback_chat(&reason);
        return;
    }
    if matches!(
        status.as_str(),
        "filed" | "dry-run" | "dedup-comment" | "no-match" | "lookup-failed-open" | "printed"
    ) {
        copy_if_file(&ctx.compose_env(), sentinel);
        println!("DESIGN_FAILURE_REPORT_DECISION={decision}");
        println!("DESIGN_FAILURE_REPORT_ENV={}", sentinel.display());
        let artifact = ctx.compose_env_key("STALL_RECOVERY_REPORT_ARTIFACT");
        if !artifact.is_empty() {
            println!("DESIGN_FAILURE_REPORT_ARTIFACT={artifact}");
        }
        return;
    }
    if status.is_empty() {
        ctx.write_fallback_chat("compose-status-missing");
    } else {
        ctx.write_fallback_chat(&format!("compose-status-{status}"));
    }
}

// --- reconcile (failed-publish-tail) ---

fn validated_publish_state(design_tmpdir: &Path, path: &Path) -> Option<Vec<(String, String)>> {
    if is_symlink(path) || !path.is_file() {
        return None;
    }
    let resolved_root = resolve_like_python(design_tmpdir);
    let resolved_path = resolve_like_python(path);
    let under = resolved_path == resolved_root
        || resolved_path
            .ancestors()
            .any(|ancestor| ancestor == resolved_root);
    if !under {
        return None;
    }
    let bytes = fs::read(path).ok()?;
    let text = String::from_utf8_lossy(&bytes);
    let mut values: Vec<(String, String)> = Vec::new();
    for raw_line in text.lines() {
        if raw_line.is_empty() || raw_line.starts_with('#') {
            continue;
        }
        let (key, value) = raw_line.split_once('=')?;
        if values.iter().any(|(existing, _)| existing == key) {
            return None;
        }
        values.push((key.to_owned(), value.to_owned()));
    }
    Some(values)
}

fn validated_salvage_publish_result(
    design_tmpdir: &Path,
    path: &Path,
) -> Option<Vec<(String, String)>> {
    let values = validated_publish_state(design_tmpdir, path)?;
    let get = |key: &str| env_value(&values, key).to_owned();
    let attempt_id = get("PUBLISH_ATTEMPT_ID");
    if !(8..=128).contains(&attempt_id.len())
        || !attempt_id
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '_' | '-'))
    {
        return None;
    }
    if !matches!(get("PUBLISH_RC_SOURCE").as_str(), "returned" | "exception") {
        return None;
    }
    if !(get("PLAN_WRITE_OK") == "true"
        && get("RENAMED") == "true"
        && get("LOG_PUBLISH_COMPLETED") == "true")
    {
        return None;
    }
    Some(values)
}

fn salvage_success_proven(design_tmpdir: &Path) -> bool {
    validated_salvage_publish_result(
        design_tmpdir,
        &design_tmpdir.join(DESIGN_PUBLISH_RESULT_FILE),
    )
    .is_some()
}

fn resolve_report_repo(url: &str, fallback: &str) -> String {
    if let Some(idx) = url.find("github.com/") {
        let rest = &url[idx + "github.com/".len()..];
        if let Some(issues_idx) = rest.find("/issues/") {
            let slug = &rest[..issues_idx];
            if slug
                .chars()
                .all(|c| c.is_ascii_alphanumeric() || matches!(c, '_' | '.' | '-' | '/'))
                && slug.matches('/').count() == 1
            {
                return slug.to_owned();
            }
        }
    }
    fallback.to_owned()
}

fn reconcile_failed_publish_tail_report(
    ctx: &FailureCtx,
    terminal_sentinel: &Path,
    outcome: &str,
) -> bool {
    if outcome != "approved" && outcome != "approved-partition" {
        return false;
    }
    if !terminal_sentinel.is_file() {
        return false;
    }
    let reconcile_sentinel = ctx.path("design-failure-reconcile-report.env");
    if read_env_value(&reconcile_sentinel, "STATUS", "") == "reconciled" {
        return false;
    }
    if read_env_value(terminal_sentinel, "STALL_RECOVERY_REPORT_STATUS", "") != "filed" {
        return false;
    }
    let report_issue = read_env_value(terminal_sentinel, "STALL_RECOVERY_REPORT_ISSUE_NUMBER", "");
    if report_issue.is_empty() || !report_issue.chars().all(|c| c.is_ascii_digit()) {
        return false;
    }
    let terminal_state = ctx.path("design-failure-terminal-state.env");
    let Some(terminal_values) = validated_publish_state(&ctx.design_tmpdir, &terminal_state) else {
        return false;
    };
    if env_value(&terminal_values, "TRIGGER") != "publish-tail-failed"
        && env_value(&terminal_values, "FAILURE_OUTCOME") != "failed-publish-tail"
    {
        return false;
    }
    if !salvage_success_proven(&ctx.design_tmpdir) {
        return false;
    }
    let report_repo = resolve_report_repo(
        &read_env_value(terminal_sentinel, "STALL_RECOVERY_REPORT_ISSUE_URL", ""),
        &ctx.repo,
    );
    let (ok, detail) = reconcile_post_recovery_comment(ctx, &report_issue, &report_repo);
    let status = if ok { "reconciled" } else { "reconcile-failed" };
    let _ = fs::write(
        &reconcile_sentinel,
        format!(
            "DESIGN_FAILURE_RECONCILE_REPORT=true\nSTATUS={status}\nREPORT_ISSUE={report_issue}\n{detail}\n"
        ),
    );
    if ok {
        println!("DESIGN_FAILURE_RECONCILE_STATUS=reconciled");
        println!("DESIGN_FAILURE_RECONCILE_REPORT_ISSUE={report_issue}");
        core_diagnostic(&format!(
            "**\u{2139} /design: reconciled prior failed-publish-tail report #{report_issue} after salvage.**"
        ));
    } else {
        let audit = ctx.path("design-failure-reconcile-audit.log");
        let _ = fs::write(&audit, format!("{detail}\n"));
        ctx.append_failure(
            "design failure reconcile",
            "gh issue",
            "1",
            "Warnings",
            &audit,
        );
        let _ = append_execution_issue(
            ctx,
            &format!(
                "failed-publish-tail report #{report_issue} reconcile failed: {detail}; left open for operator review"
            ),
        );
        core_diagnostic(&format!(
            "**\u{26a0} /design: failed-publish-tail report #{report_issue} reconcile failed ({detail}); left open.**"
        ));
    }
    true
}

fn append_execution_issue(ctx: &FailureCtx, message: &str) -> Result<(), ()> {
    // Mirror `_append_execution_issue` via the `run-log append-entry` owner.
    let log = ctx.path("execution-issues.md");
    let args = vec![
        "run-log".to_owned(),
        "append-entry".to_owned(),
        "--log".to_owned(),
        log.display().to_string(),
        "--category".to_owned(),
        "Warnings".to_owned(),
        "--entry".to_owned(),
        message.to_owned(),
    ];
    if ctx.runner.run(&ctx.plugin_root, &args, &[], false).code == 0 {
        Ok(())
    } else {
        Err(())
    }
}

/// Port of `_reconcile_post_recovery_comment`. The auth gate and fallback are
/// byte-faithful; the authorized-live gh comment/close runs through the shared
/// `IssueMutationOwner` (a narrow production-only path never exercised offline).
fn reconcile_post_recovery_comment(
    ctx: &FailureCtx,
    report_issue: &str,
    repo: &str,
) -> (bool, String) {
    let source_env = ctx.path("source-env.sh");
    let context_file = if source_env.is_file() {
        Some(source_env.as_path())
    } else {
        None
    };
    let run_id = read_env_value(&source_env, "LARCH_RUN_ID", "");
    let decision = check_live_mutation_auth(&LiveMutationRequest {
        context_file,
        operator_mode: false,
        run_id: &run_id,
        trusted_root: Some(&ctx.design_tmpdir),
        test_deny: false,
    });
    if !decision.is_authorized() {
        return (false, "reconcile-unauthorized".to_owned());
    }
    let body_text = format!(
        "{RECONCILE_PUBLISH_TAIL_MARKER}\n\nThe /design run that filed this terminal report later completed its remaining publish work: the plan was published, the tracking issue was renamed to [DESIGNED], and the run log was published. Closing this auto-filed report as recovered.\n"
    );
    let redacted = redact_outbound(&body_text);
    if redacted.contains("[content truncated") {
        return (false, "redact-secrets failed".to_owned());
    }
    let _ = fs::write(
        ctx.path("design-failure-reconcile-comment.redacted.md"),
        &redacted,
    );
    let Ok(issue_number) = report_issue.parse::<u64>() else {
        return (false, "gh issue comment failed".to_owned());
    };
    let authorization = LiveMutationRequest {
        context_file,
        operator_mode: false,
        run_id: &run_id,
        trusted_root: Some(&ctx.design_tmpdir),
        test_deny: false,
    };
    let repo_arg = if repo.is_empty() { None } else { Some(repo) };
    let result = with_github_service(async |service, cancellation| {
        let Some(slug) = resolve_repo_for(repo_arg) else {
            return Err("gh issue comment failed".to_owned());
        };
        let Ok(reference) = repository_ref(&slug) else {
            return Err("gh issue comment failed".to_owned());
        };
        let owner = IssueMutationOwner::new(service);
        owner
            .close_with_comment(
                cancellation,
                &authorization,
                &reference,
                issue_number,
                GitHubCloseReason::Completed,
                Some(&redacted),
            )
            .await
            .map(|_| ())
            .map_err(|error| error.reason().to_owned())
    });
    match result {
        Ok(()) => (true, "reconciled".to_owned()),
        Err(_error) => (false, "gh issue close failed".to_owned()),
    }
}

// ---------------------------------------------------------------------------
// step-final-summary
// ---------------------------------------------------------------------------

const FINAL_SUMMARY_ERR_PREFIX: &str = "design-step-final-summary.sh:";

/// The five `Ctx` fields step-final-summary reads from the merged mapping.
struct SummaryCtx {
    repo: String,
    issue_number: String,
    session_id: String,
    summary_outcome: String,
    final_summary_path: String,
}

fn summary_ctx(env: &Env) -> SummaryCtx {
    let field = |key: &str| -> String {
        env.get(key)
            .map_or_else(|| std::env::var(key).unwrap_or_default(), String::clone)
    };
    SummaryCtx {
        repo: field("REPO"),
        issue_number: field("ISSUE_NUMBER"),
        session_id: field("SESSION_ID"),
        summary_outcome: field("SUMMARY_OUTCOME"),
        final_summary_path: field(ENV_FINAL_SUMMARY_PATH),
    }
}

fn has_nonempty_final_summary(path: &Path) -> bool {
    !is_symlink(path) && path.is_file() && path.metadata().map(|m| m.len() > 0).unwrap_or(false)
}

/// The `step-final-summary` entry point.
pub fn step_final_summary(arguments: &[OsString]) -> ExitCode {
    step_final_summary_with(arguments, &LiveStep0Runner)
}

fn step_final_summary_with(arguments: &[OsString], runner: &dyn Step0Runner) -> ExitCode {
    let argv = utf8_arguments(arguments);
    let ns = match parse_wrapper_args(&argv) {
        Ok(ns) => ns,
        Err(_code) => {
            // `_parse_common_wrapper_args` ValueError -> exit 2 in the main wrapper.
            return ExitCode::from(2);
        }
    };
    let env = load_wrapper_env(&ns);
    let raw_tmpdir = env_get(&env, "DESIGN_TMPDIR", "");
    if raw_tmpdir.is_empty() {
        core_diagnostic(&format!(
            "{FINAL_SUMMARY_ERR_PREFIX} DESIGN_TMPDIR required"
        ));
        return ExitCode::from(1);
    }
    let design_tmpdir = match validate_core_design_tmpdir(raw_tmpdir) {
        Ok(path) => path,
        Err(message) => {
            core_diagnostic(&format!("{FINAL_SUMMARY_ERR_PREFIX} {message}"));
            return ExitCode::from(1);
        }
    };
    let plugin_root =
        match require_plugin_root(env_get(&env, "CLAUDE_PLUGIN_ROOT", &ns.plugin_root)) {
            Ok(root) => root,
            Err(_code) => PathBuf::from(env_get(&env, "CLAUDE_PLUGIN_ROOT", "")),
        };
    let core_rc = step_final_summary_core(runner, &plugin_root, &env, &design_tmpdir);
    // `step_final_summary_main`: rc 2/3 pass through; else success when the
    // result env landed.
    if core_rc == 2 || core_rc == 3 {
        return exit_from_i32(core_rc);
    }
    let result_env = design_tmpdir.join(".design-step-final-summary-result.env");
    if result_env.is_file() && !is_symlink(&result_env) {
        return ExitCode::SUCCESS;
    }
    exit_from_i32(core_rc)
}

fn step_final_summary_core(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    env: &Env,
    design_tmpdir: &Path,
) -> i32 {
    let ctx = summary_ctx(env);
    let final_summary_path = if ctx.final_summary_path.is_empty() {
        design_tmpdir.join("final-summary.md").display().to_string()
    } else {
        ctx.final_summary_path.clone()
    };
    let disk_final_summary = design_tmpdir.join("final-summary.md");
    if design_tmpdir.join(".pause-requested").is_file() {
        return pause_save(runner, plugin_root, design_tmpdir, &ctx);
    }
    let _ = fs::remove_file(design_tmpdir.join(".design-step-final-summary-result.env"));
    if matches!(
        ctx.summary_outcome.as_str(),
        "cancelled-clarify" | "failed-clarify"
    ) && has_nonempty_final_summary(&disk_final_summary)
    {
        let rc = emit_and_complete_final_summary(
            design_tmpdir,
            &disk_final_summary.display().to_string(),
        );
        try_deactivate_design_run(runner, plugin_root, design_tmpdir);
        return rc;
    }
    if is_terminal_publish_outcome(&ctx.summary_outcome) {
        let rc = run_terminal_publish_final_summary(
            runner,
            plugin_root,
            design_tmpdir,
            &ctx,
            &disk_final_summary,
        );
        try_deactivate_design_run(runner, plugin_root, design_tmpdir);
        return rc;
    }
    let rc = run_rendered_final_summary(design_tmpdir, &ctx, &final_summary_path);
    try_deactivate_design_run(runner, plugin_root, design_tmpdir);
    rc
}

fn is_terminal_publish_outcome(outcome: &str) -> bool {
    outcome.starts_with("cancelled-") && outcome != "cancelled-clarify"
}

fn pause_save(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    ctx: &SummaryCtx,
) -> i32 {
    let mut args = vec![
        "design".to_owned(),
        "pause-save".to_owned(),
        "--design-tmpdir".to_owned(),
        design_tmpdir.display().to_string(),
        "--issue".to_owned(),
        ctx.issue_number.clone(),
    ];
    if !ctx.repo.is_empty() {
        args.extend(["--repo".to_owned(), ctx.repo.clone()]);
    }
    runner.run(plugin_root, &args, &[], false).code
}

/// Port of `_emit_and_complete_final_summary`.
fn emit_and_complete_final_summary(design_tmpdir: &Path, final_summary_path: &str) -> i32 {
    let summary_path = PathBuf::from(final_summary_path);
    if summary_path.is_file()
        && summary_path
            .metadata()
            .map(|m| m.len() > 0)
            .unwrap_or(false)
    {
        println!("{ENV_FINAL_SUMMARY_PATH}={final_summary_path}");
        println!("{LARCH_FINAL_SUMMARY_BEGIN_MARKER}");
        println!("{LARCH_FINAL_SUMMARY_END_MARKER}");
    }
    // Persist readiness KVs into the merge env bgjob DONE promotes (#8462).
    if has_nonempty_final_summary(&summary_path) {
        let rows = format!(
            "{ENV_FINAL_SUMMARY_PATH}={final_summary_path}\n{ENV_FINAL_SUMMARY_READY}=true\n"
        );
        let _ = fs::write(
            design_tmpdir.join(".design-step-final-summary-result.env"),
            rows,
        );
    }
    emit_report_gate_sidecars_from_disk(design_tmpdir);
    0
}

/// Port of `_emit_report_gate_sidecars_from_disk`.
fn emit_report_gate_sidecars_from_disk(design_tmpdir: &Path) {
    let handoff = design_tmpdir.join("design-report-gate-sidecars.md");
    let sidecars = [
        design_tmpdir.join("design-failure-chat-print.md"),
        design_tmpdir.join("design-failure-operator-action-chat.md"),
    ];
    let mut chunks: Vec<String> = Vec::new();
    for sidecar in &sidecars {
        if sidecar.is_file()
            && sidecar.metadata().map(|m| m.len() > 0).unwrap_or(false)
            && let Ok(bytes) = fs::read(sidecar)
        {
            chunks.push(String::from_utf8_lossy(&bytes).into_owned());
        }
    }
    let text = if chunks.is_empty() {
        String::new()
    } else {
        format!("{}\n", chunks.join("\n").trim_end_matches('\n'))
    };
    let _ = fs::write(&handoff, &text);
    if handoff.metadata().map(|m| m.len() > 0).unwrap_or(false) {
        println!("REPORT_GATE_SIDECARS_FILE={}", handoff.display());
    }
}

fn run_terminal_publish_final_summary(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    ctx: &SummaryCtx,
    final_summary_path: &Path,
) -> i32 {
    if ctx.session_id.is_empty() {
        return record_terminal_summary_error(
            design_tmpdir,
            "design log publish skipped for terminal summary because SESSION_ID is missing",
        );
    }
    let (publish_rc, publish_ok) = publish_terminal_final_summary(design_tmpdir, ctx);
    if !publish_ok {
        let detail = terminal_publish_error_detail(design_tmpdir);
        let suffix = if detail.is_empty() {
            String::new()
        } else {
            format!(": {detail}")
        };
        return record_terminal_summary_error(
            design_tmpdir,
            &format!("design log publish failed for terminal summary (exit {publish_rc}){suffix}"),
        );
    }
    if !upsert_final_summary_from_disk(runner, plugin_root, design_tmpdir, ctx, final_summary_path)
    {
        return record_terminal_summary_error(
            design_tmpdir,
            "tracking-issue upsert-summary failed for terminal final summary",
        );
    }
    emit_and_complete_final_summary(design_tmpdir, &final_summary_path.display().to_string())
}

/// Port of `_publish_terminal_final_summary`: run `design log-publish` through
/// the Python seam, capturing streams to the terminal logs, then read
/// `PUBLISH_OK`/`RECOVERY_BRANCH` from its stdout.
fn publish_terminal_final_summary(design_tmpdir: &Path, ctx: &SummaryCtx) -> (i32, bool) {
    let mut args: Vec<OsString> = vec![
        "design".into(),
        "log-publish".into(),
        "--design-tmpdir".into(),
        design_tmpdir.as_os_str().to_owned(),
        "--run-id".into(),
        ctx.session_id.clone().into(),
        "--issue".into(),
        ctx.issue_number.clone().into(),
        "--outcome".into(),
        ctx.summary_outcome.clone().into(),
    ];
    if !ctx.repo.is_empty() {
        args.push("--repo".into());
        args.push(ctx.repo.clone().into());
    }
    let stdout_log = design_tmpdir.join("design-log-publish.terminal.stdout.log");
    let stderr_log = design_tmpdir.join("design-log-publish.terminal.stderr.log");
    match run_python_verb(args, PAUSE_LOAD_TIMEOUT) {
        Ok(output) => {
            let _ = fs::write(&stdout_log, output.stdout());
            let _ = fs::write(&stderr_log, output.stderr());
            let rc = output.status().code().unwrap_or(1);
            let stdout_text = String::from_utf8_lossy(output.stdout()).into_owned();
            let publish_ok = kv_last_value(&stdout_text, "PUBLISH_OK");
            let recovery_branch = kv_last_value(&stdout_text, "RECOVERY_BRANCH");
            (
                rc,
                rc == 0 && publish_ok == "true" && recovery_branch.is_empty(),
            )
        }
        Err(_error) => {
            let _ = fs::write(&stdout_log, b"");
            let _ = fs::write(&stderr_log, b"");
            (1, false)
        }
    }
}

fn kv_last_value(text: &str, key: &str) -> String {
    let prefix = format!("{key}=");
    let mut found = String::new();
    for line in text.split('\n') {
        if let Some(value) = line.strip_prefix(&prefix) {
            value.clone_into(&mut found);
        }
    }
    found
}

fn terminal_publish_error_detail(design_tmpdir: &Path) -> String {
    let stderr_log = design_tmpdir.join("design-log-publish.terminal.stderr.log");
    if is_symlink(&stderr_log) || !stderr_log.is_file() {
        return String::new();
    }
    let Ok(meta) = stderr_log.metadata() else {
        return String::new();
    };
    if meta.len() > TERMINAL_PUBLISH_DIAGNOSTIC_BYTE_CAP {
        return "terminal publish diagnostic unavailable because stderr exceeds the bounded scan"
            .to_owned();
    }
    let Ok(bytes) = fs::read(&stderr_log) else {
        return String::new();
    };
    safe_terminal_publish_detail(&String::from_utf8_lossy(&bytes))
}

fn safe_terminal_publish_detail(text: &str) -> String {
    let redacted = redact_outbound(text);
    if redacted.contains("[content truncated") {
        return "terminal publish diagnostic redaction unavailable".to_owned();
    }
    let flattened = sanitize_diagnostic_line(&redacted.replace(['\r', '\n'], " "));
    let flattened = flattened.trim();
    flattened
        .chars()
        .take(TERMINAL_PUBLISH_DIAGNOSTIC_CHAR_CAP)
        .collect()
}

fn record_terminal_summary_error(design_tmpdir: &Path, message: &str) -> i32 {
    println!("ERROR={message}");
    // Best-effort execution issue append via the run-log owner.
    let log = design_tmpdir.join("execution-issues.md");
    let _ = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log)
        .and_then(|mut file| {
            use std::io::Write as _;
            writeln!(file, "Warning: {message}")
        });
    1
}

/// Port of `upsert_final_summary_from_disk`: shell `tracking-issue upsert-summary`.
fn upsert_final_summary_from_disk(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    _design_tmpdir: &Path,
    ctx: &SummaryCtx,
    final_summary_path: &Path,
) -> bool {
    if is_symlink(final_summary_path)
        || !final_summary_path.is_file()
        || final_summary_path
            .metadata()
            .map(|m| m.len() == 0)
            .unwrap_or(true)
    {
        return false;
    }
    if ctx.issue_number.is_empty() || ctx.issue_number == "0" || ctx.session_id.is_empty() {
        return false;
    }
    let marker = format!("<!-- larch:final-summary v1 runid={} -->", ctx.session_id);
    let mut args = vec![
        "tracking-issue".to_owned(),
        "upsert-summary".to_owned(),
        "--issue".to_owned(),
        ctx.issue_number.clone(),
        "--marker".to_owned(),
        marker,
        "--content-file".to_owned(),
        final_summary_path.display().to_string(),
    ];
    if !ctx.repo.is_empty() {
        args.extend(["--repo".to_owned(), ctx.repo.clone()]);
    }
    runner.run(plugin_root, &args, &[], false).code == 0
}

/// Port of `_run_rendered_final_summary` + `_render_final_summary_post_publish`.
fn run_rendered_final_summary(
    design_tmpdir: &Path,
    ctx: &SummaryCtx,
    final_summary_path: &str,
) -> i32 {
    let render_rc = render_final_summary_post_publish(design_tmpdir, ctx);
    if render_rc != 0 {
        return render_rc;
    }
    emit_and_complete_final_summary(design_tmpdir, final_summary_path)
}

fn render_final_summary_post_publish(design_tmpdir: &Path, ctx: &SummaryCtx) -> i32 {
    let mut args: Vec<OsString> = vec![
        "design".into(),
        "render-final-summary".into(),
        "--outcome".into(),
        ctx.summary_outcome.clone().into(),
        "--design-tmpdir".into(),
        design_tmpdir.as_os_str().to_owned(),
        "--issue-number".into(),
        ctx.issue_number.clone().into(),
    ];
    if !ctx.session_id.is_empty() {
        args.push("--session-id".into());
        args.push(ctx.session_id.clone().into());
    }
    args.push("--post-publish-only".into());
    if !ctx.repo.is_empty() {
        args.push("--repo".into());
        args.push(ctx.repo.clone().into());
    }
    let render_stdout = design_tmpdir.join("render-final-summary.stdout.log");
    match run_python_verb(args, PAUSE_LOAD_TIMEOUT) {
        Ok(output) => {
            let _ = fs::write(&render_stdout, output.stdout());
            output.status().code().unwrap_or(1)
        }
        Err(_error) => {
            let log = design_tmpdir.join("execution-issues.md");
            let _ = fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(&log)
                .and_then(|mut file| {
                    use std::io::Write as _;
                    writeln!(file, "Warning: render_final_summary_main failed")
                });
            1
        }
    }
}

/// Port of `_try_deactivate_design_run`: best-effort `progress deactivate`.
fn try_deactivate_design_run(runner: &dyn Step0Runner, plugin_root: &Path, design_tmpdir: &Path) {
    let Some(run_id) = resolve_owned_run_id(design_tmpdir) else {
        return;
    };
    let cwd = std::env::current_dir()
        .map(|path| path.display().to_string())
        .unwrap_or_default();
    let _ = runner.run(
        plugin_root,
        &[
            "progress".to_owned(),
            "deactivate".to_owned(),
            "--repo-root".to_owned(),
            cwd,
            "--run-id".to_owned(),
            run_id,
        ],
        &[],
        false,
    );
}

/// Port of `progress_file.resolve_owned_run_id` for the deactivate path.
fn resolve_owned_run_id(design_tmpdir: &Path) -> Option<String> {
    let mut candidates: Vec<String> = Vec::new();
    if let Ok(value) = std::env::var("LARCH_RUN_ID")
        && !value.is_empty()
    {
        candidates.push(value);
    }
    for name in ["session-env.sh", "source-env.sh"] {
        let Ok(text) = fs::read_to_string(design_tmpdir.join(name)) else {
            continue;
        };
        for line in text.lines() {
            for prefix in ["LARCH_RUN_ID=", "export LARCH_RUN_ID="] {
                if let Some(rest) = line.strip_prefix(prefix) {
                    candidates.push(
                        rest.trim()
                            .trim_matches(|c: char| c == '\'' || c == '"')
                            .to_owned(),
                    );
                }
            }
        }
    }
    candidates
        .into_iter()
        .find(|value| is_valid_owned_run_id(value))
}

fn is_valid_owned_run_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value != "."
        && value != ".."
        && value != "current"
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
}

#[cfg(test)]
mod tests {
    use std::{cell::RefCell, ffi::OsString, fs, path::Path};

    use larch_test_support::{DesignFixture, DesignSession};

    use crate::design_step0_commands::{ChildOutcome, Step0Runner};

    use super::{
        classify_input, clean_status_token, is_terminal_publish_outcome,
        ledger_row_has_escalation_evidence, preferred_bgjob_result_input,
        resolve_read_result_env_source, resolve_report_repo, valid_var_name,
    };

    struct RecordingRunner {
        calls: RefCell<Vec<Vec<String>>>,
        answers: RefCell<Vec<ChildOutcome>>,
    }

    impl RecordingRunner {
        fn new(answers: Vec<ChildOutcome>) -> Self {
            Self {
                calls: RefCell::new(Vec::new()),
                answers: RefCell::new(answers),
            }
        }
    }

    impl Step0Runner for RecordingRunner {
        fn run(
            &self,
            _plugin_root: &Path,
            args: &[String],
            _env: &[(String, String)],
            _merge_stderr: bool,
        ) -> ChildOutcome {
            self.calls.borrow_mut().push(args.to_vec());
            let mut answers = self.answers.borrow_mut();
            if answers.is_empty() {
                ChildOutcome {
                    code: 0,
                    stdout: String::new(),
                    stderr: String::new(),
                }
            } else {
                answers.remove(0)
            }
        }
    }

    fn design_dir() -> DesignSession {
        DesignSession::builder(DesignFixture::Absent)
            .build()
            .expect("design session")
    }

    #[test]
    fn valid_var_name_matches_python() {
        assert!(valid_var_name("FOO_BAR"));
        assert!(valid_var_name("A1"));
        assert!(!valid_var_name("1A"));
        assert!(!valid_var_name(""));
        assert!(!valid_var_name("has-dash"));
    }

    #[test]
    fn classify_input_reports_regular_and_missing() {
        let session = design_dir();
        let file = session.root().join("regular.env");
        fs::write(&file, "K=v\n").expect("write");
        assert_eq!(classify_input(&file), "regular");
        assert_eq!(classify_input(&session.root().join("absent")), "missing");
    }

    #[test]
    fn preferred_bgjob_input_prefers_regular_sidecar() {
        let session = design_dir();
        let root = session.root();
        let bgjob = root.join("bgjob");
        fs::create_dir_all(&bgjob).expect("bgjob dir");
        fs::write(bgjob.join("design-step5c.result.env"), "K=v\n").expect("sidecar");
        let input = root.join(".design-step5c-status.env");
        let preferred = preferred_bgjob_result_input(&input).expect("preferred present");
        assert_eq!(preferred, bgjob.join("design-step5c.result.env"));
    }

    #[test]
    fn resolve_source_warns_on_symlink_primary_with_fallback() {
        let session = design_dir();
        let root = session.root();
        let target = root.join("target.env");
        fs::write(&target, "K=v\n").expect("target");
        let link = root.join("primary.env");
        std::os::unix::fs::symlink(&target, &link).expect("symlink");
        let fallback = root.join("fallback.env");
        fs::write(&fallback, "K=v\n").expect("fallback");
        let (source, warning) = resolve_read_result_env_source(&link, Some(&fallback));
        assert_eq!(source, Some(fallback));
        assert!(warning.starts_with("WARN=read-result-env input is a symlink"));
    }

    #[test]
    fn terminal_publish_outcome_excludes_cancelled_clarify() {
        assert!(is_terminal_publish_outcome("cancelled-operator"));
        assert!(!is_terminal_publish_outcome("cancelled-clarify"));
        assert!(!is_terminal_publish_outcome("approved"));
    }

    #[test]
    fn ledger_row_escalation_evidence_gates_step3_review() {
        assert!(ledger_row_has_escalation_evidence(
            "site=step2\ttrigger=failed"
        ));
        assert!(!ledger_row_has_escalation_evidence(
            "site=step3-review\ttrigger=passed"
        ));
        assert!(ledger_row_has_escalation_evidence(
            "site=step3-review\ttrigger=panel-failed"
        ));
    }

    #[test]
    fn clean_status_token_collapses_unsafe_runs() {
        assert_eq!(clean_status_token("weird status!!"), "weird-status");
        assert_eq!(clean_status_token("filed"), "filed");
    }

    #[test]
    fn resolve_report_repo_extracts_slug_or_fallback() {
        assert_eq!(
            resolve_report_repo("https://github.com/owner/name/issues/5", "fb"),
            "owner/name"
        );
        assert_eq!(resolve_report_repo("not-a-url", "fallback"), "fallback");
    }

    #[test]
    fn stage_unknown_option_is_exit_two() {
        let session = design_dir();
        let runner = RecordingRunner::new(Vec::new());
        let args: Vec<OsString> = [
            "--design-tmpdir",
            session.root().to_str().expect("utf8"),
            "--nope",
        ]
        .iter()
        .map(OsString::from)
        .collect();
        let code = super::stage_terminal_state_with(&args, &runner);
        assert_eq!(code, std::process::ExitCode::from(2));
    }
}
