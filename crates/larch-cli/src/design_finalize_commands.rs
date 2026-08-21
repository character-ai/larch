//! Rust owner for `/design` Step 5c and Step 6 (#8586).
//!
//! The five lifecycle verbs and the temporary `compose-plan-md` helper move as
//! one ownership unit. Publish, terminal-state, summary, pause, progress, and
//! cleanup work reuse their existing Rust command owners through the verified
//! larch entrypoint. The frozen Python reference lives under
//! `fixtures/rust-parity/design_finalize_frozen/`.

use std::{
    collections::BTreeMap,
    ffi::OsString,
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::SystemProcessIdentityHost;
use larch_core::{
    KvDocument, PUBLISH_RESULT_ENV_ALLOW, ParseOptions, child_liveness, daemon_liveness,
    design::{
        OPTIONAL_SIZE_TRAILER_KEYS, OVERSIZE_OVERRIDE_OPERATOR, match_trailer_line,
        parse_final_trailers, validate_plan_facets,
    },
    has_live_entry, private_atomic_write, read_for, result_env_path, unlink_entry,
    validate_merge_result_env,
};
use uuid::Uuid;

use crate::clarify_orchestrator::write_result_env;
use crate::design_log_publish_commands::resolve_summary_mode;
use crate::design_step0_commands::{
    Env, LiveStep0Runner, Step0Runner, env_get, exit_from_i32, reap_pid_residuals,
    require_plugin_root, resolve_owned_run_id, resolve_persisted_repo_root,
    run_progress_deactivate, run_session_cleanup, utf8_arguments as utf8, validate_claude_pid,
};
use crate::design_step2b_commands::{
    WrapperArgs2b as WrapperArgs, parse_common_wrapper_args as parse_wrapper, print_text,
    rehydrate_env as wrapper_env, resolve_design_tmpdir, touch, validate_design_tmpdir_result,
};
use crate::design_terminal_commands::{STAGE_EXTRA_FLAGS, emit_report_gate_sidecars_from_disk};

const STEP5C_STEP: &str = "design-step5c";
const TAIL_BYTE_CAP: usize = 16_384;
const INFO_ICON: &str = "\u{2139}";

const STEP5C_STATUS_ALLOW: &[&str] = &[
    "ARCHITECTURE_SOURCE",
    "ARCH_GUIDE_ASSESSMENT_ARTIFACT",
    "ARCH_GUIDE_ASSESSMENT_PRESENT",
    "ARCH_GUIDE_ASSESSMENT_REQUIRED",
    "ARCH_GUIDE_ASSESSMENT_STATUS",
    "ARCH_INVARIANT_ASSESSMENT_ARTIFACT",
    "ARCH_INVARIANT_ASSESSMENT_PRESENT",
    "ARCH_INVARIANT_ASSESSMENT_REQUIRED",
    "ARCH_INVARIANT_ASSESSMENT_STATUS",
    "CLEANUP_ELIGIBLE",
    "FINAL_SUMMARY_PATH",
    "FINAL_SUMMARY_READY",
    "LATEST_PHASE",
    "LOG_PUBLISH_ATTEMPTED",
    "LOG_PUBLISH_COMPLETED",
    "PLAN_WRITE_OK",
    "PR_URL",
    "PUBLISH_ATTEMPT_ID",
    "PUBLISH_OK",
    "PUBLISH_RC",
    "PUBLISH_RC_SOURCE",
    "PUBLISH_REFUSE_REASON",
    "PUBLISH_STDOUT_FALLBACK",
    "RECOVERY_BRANCH",
    "RENAMED",
    "SESSION_ID",
    "STANDALONE_HEAVY_FAILED",
    "UPSERT_STATUS",
    "VALIDATE_DEFECT_COUNT",
    "VALIDATE_LOG_FILE",
    "VALIDATE_MISSING_SCRIPT_COUNT",
    "VALIDATE_SKIPPED_COUNT",
    "VALIDATE_STATUS",
    "VALIDATE_UNSAFE_TOKEN_COUNT",
];

const GATE_C_REFUSALS: &[&str] = &[
    "missing-invariant-assessment",
    "missing-guideline-assessment",
    "invariant-violation",
    "invalid-guideline-deviation",
];

struct StepCtx {
    issue: String,
    session_id: String,
    repo: String,
    claude_pid: String,
    standalone_heavy_failed: String,
}

fn validate_tmpdir(raw: &str) -> Result<PathBuf, String> {
    validate_design_tmpdir_result(raw)?;
    let path = resolve_design_tmpdir(raw);
    if !path.is_dir() {
        return Err("design-tmpdir: path must name a directory".to_owned());
    }
    Ok(path)
}

fn read_env_rows(text: &str, allow: &[&str]) -> Vec<(String, String)> {
    let clean = text
        .split('\n')
        .filter(|line| !line.contains('\r'))
        .collect::<Vec<_>>()
        .join("\n");
    let document =
        KvDocument::parse(&clean, ParseOptions::legacy()).expect("legacy KV parsing is infallible");
    document
        .rows()
        .iter()
        .filter(|row| allow.contains(&row.key()))
        .map(|row| (row.key().to_owned(), row.value().to_owned()))
        .collect()
}

fn read_env_file(path: &Path, allow: &[&str]) -> Option<Vec<(String, String)>> {
    if path.is_symlink() || !path.is_file() {
        return None;
    }
    let text = String::from_utf8_lossy(&fs::read(path).ok()?).into_owned();
    Some(read_env_rows(&text, allow))
}

fn env_map(rows: &[(String, String)]) -> BTreeMap<String, String> {
    rows.iter().cloned().collect()
}

fn get<'a>(values: &'a BTreeMap<String, String>, key: &str) -> &'a str {
    values.get(key).map_or("", String::as_str)
}

fn write_status(path: &Path, rows: &[(String, String)]) -> Result<(), String> {
    let borrowed = rows
        .iter()
        .map(|(key, value)| (key.as_str(), value.as_str()))
        .collect::<Vec<_>>();
    write_result_env(path, &borrowed, STEP5C_STATUS_ALLOW)?;
    let verified = read_env_file(path, STEP5C_STATUS_ALLOW)
        .map(|found| env_map(&found))
        .ok_or_else(|| "step 5c status write verification failed".to_owned())?;
    if rows
        .iter()
        .any(|(key, value)| verified.get(key) != Some(value))
    {
        return Err("step 5c status write verification failed".to_owned());
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// composed-plan.md
// ---------------------------------------------------------------------------

fn split_plan_body_and_trailers(lines: Vec<String>) -> (Vec<String>, Vec<String>) {
    let text = lines.concat();
    let trailers = parse_final_trailers(&text, true);
    if trailers.matches.is_empty() {
        return (lines, Vec::new());
    }
    let start = trailers.start_line.saturating_sub(1);
    (lines[..start].to_vec(), lines[start..].to_vec())
}

fn strip_leading_plan_header(body: &[String]) -> Vec<String> {
    let mut index = 0;
    while body.get(index).is_some_and(|line| line.trim().is_empty()) {
        index += 1;
    }
    if body
        .get(index)
        .is_some_and(|line| line.trim_end_matches(['\r', '\n']).trim_end().eq("## Plan"))
    {
        index += 1;
        while body.get(index).is_some_and(|line| line.trim().is_empty()) {
            index += 1;
        }
    }
    body[index..].to_vec()
}

fn digits(value: &str) -> bool {
    !value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit())
}

fn optional_trailer_lines(path: &Path) -> Vec<String> {
    let Ok(raw) = fs::read_to_string(path) else {
        return Vec::new();
    };
    let mut lines = Vec::new();
    for item in raw.lines() {
        let parsed = read_env_rows(item.trim(), &OPTIONAL_SIZE_TRAILER_KEYS);
        let Some((key, value)) = parsed.last() else {
            continue;
        };
        let valid = match key.as_str() {
            "diff_added" | "diff_deleted" => digits(value),
            "mechanical_churn" => matches!(value.as_str(), "true" | "false"),
            "oversize_override" => value == OVERSIZE_OVERRIDE_OPERATOR,
            _ => false,
        };
        if valid {
            lines.push(format!("{key}: {value}\n"));
        }
    }
    lines
}

fn peel_optional_trailers(mut body: Vec<String>) -> (Vec<String>, Vec<String>) {
    let mut peeled = Vec::new();
    while let Some(line) = body.last() {
        let stripped = line.trim_end_matches(['\r', '\n']);
        if stripped.trim().is_empty() {
            let _ = body.pop();
            continue;
        }
        let Some(matched) = match_trailer_line(stripped) else {
            break;
        };
        if !OPTIONAL_SIZE_TRAILER_KEYS.contains(&matched.key.as_str()) {
            break;
        }
        let mut line = body.pop().unwrap_or_default();
        if !line.ends_with('\n') {
            line.push('\n');
        }
        peeled.insert(0, line);
    }
    (body, peeled)
}

fn trailers_from_sidecars(design_tmpdir: &Path, body: Vec<String>) -> (Vec<String>, Vec<String>) {
    let diff_path = design_tmpdir.join("diff-lines.txt");
    let Ok(diff) = fs::read_to_string(diff_path) else {
        return (body, Vec::new());
    };
    let diff = diff.trim();
    if !digits(diff) {
        return (body, Vec::new());
    }
    let mut optional =
        optional_trailer_lines(&design_tmpdir.join(".gate-b-optional-trailer-keys.values"));
    let trimmed = if optional.is_empty() {
        let (trimmed, peeled) = peel_optional_trailers(body);
        optional = peeled;
        trimmed
    } else {
        body
    };
    optional.push(format!("diff_lines: {diff}\n"));
    (trimmed, optional)
}

fn heading_level(line: &str, expected: Option<&str>) -> Option<usize> {
    let line = line.trim_end_matches(['\r', '\n']);
    let level = line.bytes().take_while(|byte| *byte == b'#').count();
    if level == 0
        || !line
            .as_bytes()
            .get(level)
            .is_some_and(u8::is_ascii_whitespace)
    {
        return None;
    }
    let title = line[level..].trim();
    if expected.is_none_or(|value| title.eq_ignore_ascii_case(value)) {
        Some(level)
    } else {
        None
    }
}

fn acceptance_section(body: &[String]) -> String {
    let Some((start, level)) = body.iter().enumerate().find_map(|(index, line)| {
        heading_level(line, Some("Testing strategy")).map(|n| (index, n))
    }) else {
        return "## Acceptance\n\nSee Testing strategy in plan.".to_owned();
    };
    let mut content = Vec::new();
    for line in &body[start + 1..] {
        if heading_level(line, None).is_some_and(|next| next <= level) {
            break;
        }
        content.push(line.as_str());
    }
    let text = content.concat();
    let text = text.trim();
    if text.is_empty() {
        "## Acceptance\n\nSee Testing strategy in plan.".to_owned()
    } else {
        format!("## Acceptance\n\n{text}")
    }
}

fn auto_compose_plan_md(design_tmpdir: &Path) {
    let composed = design_tmpdir.join("composed-plan.md");
    if composed.is_file() && composed.metadata().is_ok_and(|metadata| metadata.len() > 0) {
        return;
    }
    let plan = design_tmpdir.join("plan.txt");
    if !plan.is_file() || plan.metadata().map_or(true, |metadata| metadata.len() == 0) {
        eprintln!(
            "**⚠ Step 5c auto-compose: plan.txt missing or empty: compose composed-plan.md manually before retrying**"
        );
        return;
    }
    let Ok(raw) = fs::read(&plan) else {
        eprintln!("**⚠ Step 5c auto-compose: could not read plan.txt**");
        return;
    };
    let raw = String::from_utf8_lossy(&raw).into_owned();
    let lines = raw.split_inclusive('\n').map(str::to_owned).collect();
    let (mut body, mut trailers) = split_plan_body_and_trailers(lines);
    if trailers.is_empty() {
        (body, trailers) = trailers_from_sidecars(design_tmpdir, body);
    }
    body = strip_leading_plan_header(&body);
    let body_text = body.concat();
    let body_text = body_text.trim_end();
    let acceptance = if validate_plan_facets(&raw)
        .defects
        .contains(&"missing-acceptance")
    {
        format!("\n{}\n", acceptance_section(&body))
    } else {
        String::new()
    };
    let trailer_text = trailers.concat();
    let trailer_text = trailer_text.trim_end_matches('\n');
    let mut text = format!("## Plan\n\n{body_text}\n{acceptance}");
    if !trailer_text.is_empty() {
        text.push('\n');
        text.push_str(trailer_text);
        text.push('\n');
    }
    if let Err(error) = fs::write(&composed, text) {
        eprintln!("**⚠ Step 5c auto-compose: failed to write composed-plan.md: {error}**");
        return;
    }
    eprintln!("**⚠ Step 5c: composed-plan.md was absent; auto-composed from plan.txt**");
}

/// Remove stale composition and rebuild it from the canonical plan artifacts.
pub fn recompose_plan_md(design_tmpdir: &Path) {
    let _ = fs::remove_file(design_tmpdir.join("composed-plan.md"));
    auto_compose_plan_md(design_tmpdir);
}

pub fn compose_plan_md(arguments: &[OsString]) -> ExitCode {
    let argv = utf8(arguments);
    if argv.len() != 2 || argv[0] != "--design-tmpdir" {
        eprintln!("usage: cli.py design compose-plan-md --design-tmpdir DIR");
        return ExitCode::from(2);
    }
    let design_tmpdir = PathBuf::from(&argv[1]);
    let plan = design_tmpdir.join("plan.txt");
    if !plan.is_file() || plan.metadata().map_or(true, |metadata| metadata.len() == 0) {
        return ExitCode::SUCCESS;
    }
    recompose_plan_md(&design_tmpdir);
    ExitCode::SUCCESS
}

// ---------------------------------------------------------------------------
// Step 5c
// ---------------------------------------------------------------------------

fn step_ctx(env: &Env, parsed: &WrapperArgs) -> StepCtx {
    StepCtx {
        issue: env_get(env, "ISSUE_NUMBER", "").to_owned(),
        session_id: env_get(env, "SESSION_ID", "").to_owned(),
        repo: env_get(env, "REPO", "").to_owned(),
        claude_pid: if parsed.claude_pid.is_empty() {
            std::env::var("CLAUDE_PID").unwrap_or_default()
        } else {
            parsed.claude_pid.clone()
        },
        standalone_heavy_failed: env_get(env, "STANDALONE_HEAVY_FAILED", "").to_owned(),
    }
}

fn early_status_rows(
    ctx: &StepCtx,
    publish_rc: &str,
    stdout_fallback: bool,
    plan_write_ok: &str,
    publish_ok: &str,
    cleanup_eligible: bool,
    result: &BTreeMap<String, String>,
) -> Vec<(String, String)> {
    let mut rows = vec![
        ("PLAN_WRITE_OK".to_owned(), plan_write_ok.to_owned()),
        ("PUBLISH_OK".to_owned(), publish_ok.to_owned()),
        (
            "STANDALONE_HEAVY_FAILED".to_owned(),
            ctx.standalone_heavy_failed.clone(),
        ),
        ("SESSION_ID".to_owned(), ctx.session_id.clone()),
        ("PUBLISH_RC".to_owned(), publish_rc.to_owned()),
        (
            "PUBLISH_STDOUT_FALLBACK".to_owned(),
            stdout_fallback.to_string(),
        ),
        ("CLEANUP_ELIGIBLE".to_owned(), cleanup_eligible.to_string()),
    ];
    for key in [
        "VALIDATE_STATUS",
        "VALIDATE_DEFECT_COUNT",
        "VALIDATE_SKIPPED_COUNT",
        "VALIDATE_UNSAFE_TOKEN_COUNT",
        "VALIDATE_MISSING_SCRIPT_COUNT",
        "VALIDATE_LOG_FILE",
        "FINAL_SUMMARY_PATH",
        "PUBLISH_ATTEMPT_ID",
        "PUBLISH_RC_SOURCE",
        "LATEST_PHASE",
        "LOG_PUBLISH_ATTEMPTED",
        "LOG_PUBLISH_COMPLETED",
        "RENAMED",
        "PR_URL",
        "RECOVERY_BRANCH",
    ] {
        rows.push((key.to_owned(), get(result, key).to_owned()));
    }
    rows
}

fn final_status_rows(
    ctx: &StepCtx,
    publish_rc: i32,
    stdout_fallback: bool,
    cleanup_eligible: bool,
    result: &BTreeMap<String, String>,
) -> Vec<(String, String)> {
    let mut rows = vec![
        ("PUBLISH_RC".to_owned(), publish_rc.to_string()),
        (
            "PLAN_WRITE_OK".to_owned(),
            get(result, "PLAN_WRITE_OK").to_owned(),
        ),
        (
            "PUBLISH_OK".to_owned(),
            get(result, "PUBLISH_OK").to_owned(),
        ),
        (
            "STANDALONE_HEAVY_FAILED".to_owned(),
            ctx.standalone_heavy_failed.clone(),
        ),
        ("SESSION_ID".to_owned(), ctx.session_id.clone()),
        (
            "PUBLISH_STDOUT_FALLBACK".to_owned(),
            stdout_fallback.to_string(),
        ),
    ];
    for key in [
        "VALIDATE_STATUS",
        "VALIDATE_DEFECT_COUNT",
        "VALIDATE_SKIPPED_COUNT",
        "VALIDATE_UNSAFE_TOKEN_COUNT",
        "VALIDATE_MISSING_SCRIPT_COUNT",
        "VALIDATE_LOG_FILE",
        "PUBLISH_REFUSE_REASON",
        "ARCH_INVARIANT_ASSESSMENT_REQUIRED",
        "ARCH_INVARIANT_ASSESSMENT_PRESENT",
        "ARCH_INVARIANT_ASSESSMENT_STATUS",
        "ARCH_INVARIANT_ASSESSMENT_ARTIFACT",
        "ARCH_GUIDE_ASSESSMENT_REQUIRED",
        "ARCH_GUIDE_ASSESSMENT_PRESENT",
        "ARCH_GUIDE_ASSESSMENT_STATUS",
        "ARCH_GUIDE_ASSESSMENT_ARTIFACT",
        "FINAL_SUMMARY_PATH",
        "UPSERT_STATUS",
        "ARCHITECTURE_SOURCE",
    ] {
        rows.push((key.to_owned(), get(result, key).to_owned()));
    }
    rows.push(("CLEANUP_ELIGIBLE".to_owned(), cleanup_eligible.to_string()));
    rows
}

fn invalidate_publish_result(design_tmpdir: &Path) -> Result<(), String> {
    let result = design_tmpdir.join(".design-publish-result.env");
    if result.is_symlink() || (result.exists() && !result.is_file()) {
        return Err("prior publish result is unsafe".to_owned());
    }
    if result.exists() {
        let tombstone = design_tmpdir.join(format!(
            ".design-publish-result.env.invalid.{}",
            std::process::id()
        ));
        fs::rename(&result, &tombstone).map_err(|error| error.to_string())?;
        fs::remove_file(tombstone).map_err(|error| error.to_string())?;
    }
    Ok(())
}

fn safe_publish_values(
    design_tmpdir: &Path,
    publish_rc: i32,
    stdout: &str,
    attempt_id: Option<&str>,
) -> Result<(BTreeMap<String, String>, bool), ()> {
    let fallback = matches!(publish_rc, 1 | 3 | 4);
    let primary = read_env_file(
        &design_tmpdir.join(".design-publish-result.env"),
        &PUBLISH_RESULT_ENV_ALLOW,
    );
    let rows = if fallback {
        read_env_rows(stdout, &PUBLISH_RESULT_ENV_ALLOW)
    } else {
        primary.unwrap_or_else(|| read_env_rows(stdout, &PUBLISH_RESULT_ENV_ALLOW))
    };
    let values = env_map(&rows);
    if attempt_id.is_some_and(|expected| get(&values, "PUBLISH_ATTEMPT_ID") != expected) {
        return Err(());
    }
    Ok((values, fallback))
}

fn bounded_tail(text: &str) -> String {
    let bytes = text.as_bytes();
    String::from_utf8_lossy(&bytes[bytes.len().saturating_sub(TAIL_BYTE_CAP)..]).into_owned()
}

fn copy_tail(design_tmpdir: &Path, name: &str, text: &str) -> String {
    let tail = bounded_tail(text);
    let path = design_tmpdir.join(name);
    if private_atomic_write(&path, &tail, design_tmpdir).is_err() {
        return String::new();
    }
    fs::read_to_string(path).unwrap_or_default()
}

fn phase_tail(design_tmpdir: &Path, name: &str) -> String {
    let path = design_tmpdir.join(name);
    if path.is_symlink() || !path.is_file() {
        return String::new();
    }
    bounded_tail(&String::from_utf8_lossy(
        &fs::read(path).unwrap_or_default(),
    ))
}

fn render_publish_failure_detail(
    design_tmpdir: &Path,
    publish_rc: i32,
    source: &str,
    result: &BTreeMap<String, String>,
    stdout_tail: &str,
    stderr_tail: &str,
) -> Result<(), String> {
    let mut lines = vec![
        format!("exit_code={publish_rc}"),
        format!("rc_source={source}"),
        format!("latest_phase={}", get(result, "LATEST_PHASE")),
    ];
    for key in [
        "PLAN_WRITE_OK",
        "PUBLISH_OK",
        "RENAMED",
        "LOG_PUBLISH_ATTEMPTED",
        "LOG_PUBLISH_COMPLETED",
    ] {
        lines.push(format!("{}={}", key.to_ascii_lowercase(), get(result, key)));
    }
    if let Some(traceback) = stderr_tail
        .lines()
        .find(|line| line.starts_with("Traceback") || line.contains("Error:"))
    {
        lines.push(format!(
            "traceback={}",
            traceback.chars().take(512).collect::<String>()
        ));
    }
    for (label, text) in [
        ("step5c_stderr", stderr_tail.to_owned()),
        (
            "rename_stderr",
            phase_tail(design_tmpdir, "design-publish-rename.stderr.log"),
        ),
        (
            "log_publish_stderr",
            phase_tail(design_tmpdir, "design-publish-log.stderr.log"),
        ),
        ("step5c_stdout", stdout_tail.to_owned()),
    ] {
        if !text.is_empty() {
            lines.push(format!("[{label}]"));
            lines.push(bounded_tail(&text));
        }
    }
    let path = design_tmpdir.join("design-publish-tail.failure.log");
    private_atomic_write(&path, &format!("{}\n", lines.join("\n")), design_tmpdir)
        .map_err(|error| error.to_string())
}

fn append_failure(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    site: &str,
    tool: &str,
    exit_code: i32,
    output: &Path,
) {
    let _ = runner.run(
        plugin_root,
        &[
            "run-log".to_owned(),
            "append-failure".to_owned(),
            "--log".to_owned(),
            design_tmpdir
                .join("execution-issues.md")
                .display()
                .to_string(),
            "--site".to_owned(),
            site.to_owned(),
            "--tool".to_owned(),
            tool.to_owned(),
            "--exit-code".to_owned(),
            exit_code.to_string(),
            "--category".to_owned(),
            "Warnings".to_owned(),
            "--output-file".to_owned(),
            output.display().to_string(),
            "--redact".to_owned(),
        ],
        &[],
        false,
    );
}

fn stage_failed_publish_tail(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    publish_rc: i32,
    result: &BTreeMap<String, String>,
) {
    let detail = design_tmpdir.join("design-publish-tail.failure.log");
    if !detail.is_file() {
        let _ = private_atomic_write(
            &detail,
            &format!("design-publish.sh failed (exit {publish_rc})\n"),
            design_tmpdir,
        );
    }
    let mut args = vec![
        "design".to_owned(),
        "stage-terminal-state".to_owned(),
        "--design-tmpdir".to_owned(),
        design_tmpdir.display().to_string(),
        "--outcome".to_owned(),
        "failed-publish-tail".to_owned(),
        "--step".to_owned(),
        "publish".to_owned(),
        "--phase".to_owned(),
        "publish".to_owned(),
        "--site".to_owned(),
        "design-publish".to_owned(),
        "--trigger".to_owned(),
        "publish-tail-failed".to_owned(),
        "--bail-reason".to_owned(),
        "publish-tail-failed".to_owned(),
        "--exit-code".to_owned(),
        publish_rc.to_string(),
        "--source-script".to_owned(),
        "design-step5c".to_owned(),
        "--summary-outcome".to_owned(),
        "failed-publish-tail".to_owned(),
        "--failure-detail-log".to_owned(),
        detail.display().to_string(),
    ];
    for (flag, key) in STAGE_EXTRA_FLAGS {
        if !get(result, key).is_empty() {
            args.extend([flag.to_owned(), get(result, key).to_owned()]);
        }
    }
    let staged = runner.run(plugin_root, &args, &[], false);
    let stdout_log = design_tmpdir.join("design-stage-terminal-state.stdout.log");
    let stderr_log = design_tmpdir.join("design-stage-terminal-state.stderr.log");
    let _ = fs::write(&stdout_log, &staged.stdout);
    let _ = fs::write(&stderr_log, &staged.stderr);
    if get(
        &env_map(&read_env_rows(&staged.stdout, &["STAGED"])),
        "STAGED",
    ) == "false"
    {
        append_failure(
            runner,
            plugin_root,
            design_tmpdir,
            "design Step 5c publish-tail staging",
            "design-stage-terminal-state.sh",
            0,
            &stdout_log,
        );
    } else if staged.code != 0 {
        append_failure(
            runner,
            plugin_root,
            design_tmpdir,
            "design Step 5c publish-tail staging",
            "design-stage-terminal-state.sh",
            staged.code,
            &stderr_log,
        );
    }
}

fn publish_evidence_present(design_tmpdir: &Path, stdout: &str) -> bool {
    let mut texts = vec![stdout.to_owned()];
    if let Ok(text) = fs::read_to_string(design_tmpdir.join(".design-publish-result.env")) {
        texts.push(text);
    }
    texts.iter().any(|text| {
        ["PUBLISH_OK=", "PR_URL=", "RECOVERY_BRANCH="]
            .iter()
            .any(|key| text.contains(key))
    })
}

fn try_central_failed_summary(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    ctx: &StepCtx,
    publish_stdout: &str,
) -> bool {
    if publish_evidence_present(design_tmpdir, publish_stdout) || ctx.session_id.is_empty() {
        return false;
    }
    let mut args = vec![
        "design".to_owned(),
        "log-publish".to_owned(),
        "--design-tmpdir".to_owned(),
        design_tmpdir.display().to_string(),
        "--run-id".to_owned(),
        ctx.session_id.clone(),
        "--issue".to_owned(),
        ctx.issue.clone(),
        "--outcome".to_owned(),
        "failed-publish-tail".to_owned(),
    ];
    if !ctx.repo.is_empty() {
        args.extend(["--repo".to_owned(), ctx.repo.clone()]);
    }
    let publish = runner.run(plugin_root, &args, &[], false);
    let _ = fs::write(
        design_tmpdir.join("design-log-publish.terminal.stdout.log"),
        &publish.stdout,
    );
    let _ = fs::write(
        design_tmpdir.join("design-log-publish.terminal.stderr.log"),
        &publish.stderr,
    );
    let values = env_map(&read_env_rows(
        &publish.stdout,
        &["PUBLISH_OK", "RECOVERY_BRANCH"],
    ));
    if publish.code != 0
        || get(&values, "PUBLISH_OK") != "true"
        || !get(&values, "RECOVERY_BRANCH").is_empty()
    {
        return false;
    }
    let summary = design_tmpdir.join("final-summary.md");
    if summary.is_symlink()
        || !summary.is_file()
        || summary
            .metadata()
            .map_or(true, |metadata| metadata.len() == 0)
        || ctx.issue.is_empty()
        || ctx.issue == "0"
    {
        return false;
    }
    let marker = format!("<!-- larch:final-summary v1 runid={} -->", ctx.session_id);
    let mut upsert = vec![
        "tracking-issue".to_owned(),
        "upsert-summary".to_owned(),
        "--issue".to_owned(),
        ctx.issue.clone(),
        "--marker".to_owned(),
        marker,
        "--content-file".to_owned(),
        summary.display().to_string(),
    ];
    if !ctx.repo.is_empty() {
        upsert.extend(["--repo".to_owned(), ctx.repo.clone()]);
    }
    runner.run(plugin_root, &upsert, &[], false).code == 0
}

fn confined_summary_path(path: &Path, design_tmpdir: &Path) -> Option<PathBuf> {
    let root = fs::canonicalize(design_tmpdir).ok()?;
    let parent = path
        .parent()
        .filter(|value| !value.as_os_str().is_empty())?;
    let parent = fs::canonicalize(parent).ok()?;
    if !parent.starts_with(&root) {
        return None;
    }
    Some(parent.join(path.file_name()?))
}

fn render_summary(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    ctx: &StepCtx,
    outcome: &str,
    final_summary_path: &Path,
) -> bool {
    let disk_summary = design_tmpdir.join("final-summary.md");
    let _ = fs::remove_file(&disk_summary);
    let confined_summary = confined_summary_path(final_summary_path, design_tmpdir);
    if confined_summary.as_ref() != Some(&disk_summary)
        && let Some(path) = &confined_summary
    {
        let _ = fs::remove_file(path);
    }
    let mut args = vec![
        "design".to_owned(),
        "render-final-summary".to_owned(),
        "--outcome".to_owned(),
        outcome.to_owned(),
        "--mode".to_owned(),
        resolve_summary_mode(design_tmpdir),
        "--design-tmpdir".to_owned(),
        design_tmpdir.display().to_string(),
        "--issue-number".to_owned(),
        ctx.issue.clone(),
    ];
    if !ctx.session_id.is_empty() {
        args.extend(["--session-id".to_owned(), ctx.session_id.clone()]);
    }
    args.push("--post-publish-only".to_owned());
    if !ctx.repo.is_empty() {
        args.extend(["--repo".to_owned(), ctx.repo.clone()]);
    }
    let rendered = runner.run(plugin_root, &args, &[], false);
    let stdout = design_tmpdir.join(format!("render-final-summary.{outcome}.stdout.log"));
    let stderr = stdout.with_file_name(format!(
        "{}.stderr",
        stdout.file_name().unwrap_or_default().to_string_lossy()
    ));
    let _ = fs::write(stdout, &rendered.stdout);
    let _ = fs::write(stderr, &rendered.stderr);
    if rendered.code != 0 {
        let _ = fs::remove_file(disk_summary);
        if let Some(path) = confined_summary {
            let _ = fs::remove_file(path);
        }
        return false;
    }
    true
}

fn emit_summary(design_tmpdir: &Path, summary: &Path, status_path: &Path) {
    if !summary.is_file()
        || summary
            .metadata()
            .map_or(true, |metadata| metadata.len() == 0)
    {
        return;
    }
    println!("FINAL_SUMMARY_PATH={}", summary.display());
    println!("LARCH_FINAL_SUMMARY_BEGIN");
    println!("LARCH_FINAL_SUMMARY_END");
    if summary.is_symlink() {
        return;
    }
    let ready = vec![
        (
            "FINAL_SUMMARY_PATH".to_owned(),
            summary.display().to_string(),
        ),
        ("FINAL_SUMMARY_READY".to_owned(), "true".to_owned()),
    ];
    let _ = write_status(
        &design_tmpdir.join(".design-step-final-summary-result.env"),
        &ready,
    );
    let Some(mut rows) = read_env_file(status_path, STEP5C_STATUS_ALLOW) else {
        return;
    };
    rows.retain(|(key, _)| !matches!(key.as_str(), "FINAL_SUMMARY_PATH" | "FINAL_SUMMARY_READY"));
    rows.extend(ready);
    let _ = write_status(status_path, &rows);
}

fn failed_publish_finish(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    ctx: &StepCtx,
    publish_rc: i32,
    publish_stdout: &str,
    result: &BTreeMap<String, String>,
) {
    stage_failed_publish_tail(runner, plugin_root, design_tmpdir, publish_rc, result);
    let central =
        try_central_failed_summary(runner, plugin_root, design_tmpdir, ctx, publish_stdout);
    let summary = design_tmpdir.join("final-summary.md");
    if central
        || render_summary(
            runner,
            plugin_root,
            design_tmpdir,
            ctx,
            "failed-publish-tail",
            &summary,
        )
    {
        emit_summary(
            design_tmpdir,
            &summary,
            &design_tmpdir.join(".design-step5c-status.env"),
        );
    }
    emit_report_gate_sidecars_from_disk(design_tmpdir);
}

#[allow(clippy::too_many_lines)] // The ordered publish and recovery branches form one compatibility state machine.
fn step5c_with(arguments: &[OsString], runner: &dyn Step0Runner) -> ExitCode {
    let argv = utf8(arguments);
    let parsed = match parse_wrapper(&argv) {
        Ok(parsed) => parsed,
        Err(message) => {
            eprintln!("design-step5c.sh: {message}");
            return ExitCode::from(2);
        }
    };
    let env = wrapper_env(&parsed);
    let raw_tmpdir = env_get(&env, "DESIGN_TMPDIR", "");
    if raw_tmpdir.is_empty() {
        eprintln!("/design Step 5c: DESIGN_TMPDIR required");
        return ExitCode::from(1);
    }
    let design_tmpdir = match validate_tmpdir(raw_tmpdir) {
        Ok(path) => path,
        Err(message) => {
            eprintln!("design-step5c.sh: {message}");
            return ExitCode::from(1);
        }
    };
    let plugin_root = match require_plugin_root(env_get(&env, "CLAUDE_PLUGIN_ROOT", "")) {
        Ok(path) => path,
        Err(code) => return code,
    };
    let ctx = step_ctx(&env, &parsed);
    let status_path = design_tmpdir.join(".design-step5c-status.env");
    let empty = BTreeMap::new();
    if !design_tmpdir.join(".completed/step-5b").is_file() {
        eprintln!(
            "**⚠ Step 5c: missing .completed/step-5b: OOS filing incomplete; repair Step 5b before publish**"
        );
        let rows = early_status_rows(&ctx, "not-run", false, "", "", false, &empty);
        if let Err(error) = write_status(&status_path, &rows) {
            eprintln!("design-step5c.sh: {error}");
        }
        return ExitCode::from(1);
    }
    if design_tmpdir.join(".pause-requested").is_file() {
        let pause = runner.run(&plugin_root, &pause_args(&design_tmpdir, &ctx), &[], false);
        print_text(&pause.stdout);
        eprint!("{}", pause.stderr);
        let rows = early_status_rows(&ctx, "not-run", false, "", "", false, &empty);
        let _ = write_status(&status_path, &rows);
        println!("STEP5C_STATUS=pause-save");
        return exit_from_i32(pause.code);
    }

    auto_compose_plan_md(&design_tmpdir);
    let mut publish_args = vec![
        "design".to_owned(),
        "publish".to_owned(),
        "--design-tmpdir".to_owned(),
        design_tmpdir.display().to_string(),
        "--issue".to_owned(),
        ctx.issue.clone(),
        "--session-id".to_owned(),
        ctx.session_id.clone(),
        "--claude-pid".to_owned(),
        ctx.claude_pid.clone(),
    ];
    if !ctx.repo.is_empty() {
        publish_args.extend(["--repo".to_owned(), ctx.repo.clone()]);
    }
    if parsed.skip_validate {
        publish_args.push("--skip-validate".to_owned());
    }
    if let Err(error) = invalidate_publish_result(&design_tmpdir) {
        eprintln!("**⚠ Step 5c: prior publish result invalidation failed: {error}**");
        let rows = early_status_rows(&ctx, "5", false, "", "", false, &empty);
        let _ = write_status(&status_path, &rows);
        stage_failed_publish_tail(runner, &plugin_root, &design_tmpdir, 5, &empty);
        return ExitCode::from(1);
    }
    let token = Uuid::new_v4().simple().to_string();
    let attempt_id = format!("{}-{}", std::process::id(), &token[..24]);
    let publish = runner.run(
        &plugin_root,
        &publish_args,
        &[(
            "LARCH_DESIGN_PUBLISH_ATTEMPT_ID".to_owned(),
            attempt_id.clone(),
        )],
        false,
    );
    let publish_rc = publish.code;

    if publish_rc == 2 || !matches!(publish_rc, 0..=5) {
        let rows = early_status_rows(&ctx, &publish_rc.to_string(), false, "", "", false, &empty);
        let _ = write_status(&status_path, &rows);
        failed_publish_finish(
            runner,
            &plugin_root,
            &design_tmpdir,
            &ctx,
            publish_rc,
            &publish.stdout,
            &empty,
        );
        if publish_rc == 2 {
            eprintln!(
                "**⚠ Step 5c: design-publish.sh configuration error (exit 2); aborting /design**"
            );
        } else {
            eprintln!(
                "**⚠ Step 5c: design-publish.sh failed (exit {publish_rc}); aborting /design**"
            );
        }
        return ExitCode::from(1);
    }
    if publish_rc == 5 {
        let stdout_tail = copy_tail(
            &design_tmpdir,
            "design-publish-tail.stdout.log",
            &publish.stdout,
        );
        let stderr_tail = copy_tail(
            &design_tmpdir,
            "design-publish-tail.stderr.log",
            &publish.stderr,
        );
        let mut result = safe_publish_values(
            &design_tmpdir,
            publish_rc,
            &publish.stdout,
            Some(&attempt_id),
        )
        .map_or_else(|()| BTreeMap::new(), |(values, _)| values);
        if !matches!(get(&result, "PUBLISH_RC_SOURCE"), "returned" | "exception") {
            let source = if stderr_tail.contains("Traceback") {
                "exception"
            } else {
                "returned"
            };
            let _ = result.insert("PUBLISH_RC_SOURCE".to_owned(), source.to_owned());
        }
        if let Err(error) = render_publish_failure_detail(
            &design_tmpdir,
            publish_rc,
            get(&result, "PUBLISH_RC_SOURCE"),
            &result,
            &stdout_tail,
            &stderr_tail,
        ) {
            append_failure(
                runner,
                &plugin_root,
                &design_tmpdir,
                "design publish tail",
                "tail persistence",
                1,
                &design_tmpdir.join("design-publish-tail.stderr.log"),
            );
            eprintln!("**⚠ Step 5c: publish-tail diagnostic persistence failed: {error}**");
        }
        let rows = early_status_rows(
            &ctx,
            "5",
            false,
            get(&result, "PLAN_WRITE_OK"),
            get(&result, "PUBLISH_OK"),
            false,
            &result,
        );
        let _ = write_status(&status_path, &rows);
        failed_publish_finish(
            runner,
            &plugin_root,
            &design_tmpdir,
            &ctx,
            5,
            &publish.stdout,
            &result,
        );
        eprintln!("**⚠ Step 5c: design-publish.sh failed (exit 5); aborting /design**");
        return ExitCode::from(1);
    }
    if publish_rc == 3 {
        eprintln!(
            "**⚠ Step 5c: design-publish.sh result-env write failed (exit 3); continuing with stdout parse**"
        );
    }
    let Ok((result, fallback)) =
        safe_publish_values(&design_tmpdir, publish_rc, &publish.stdout, None)
    else {
        eprintln!(
            "**⚠ Step 5c: design-publish result env missing or unreadable; aborting /design**"
        );
        let rows = early_status_rows(
            &ctx,
            &publish_rc.to_string(),
            matches!(publish_rc, 1 | 3 | 4),
            "",
            "",
            false,
            &empty,
        );
        let _ = write_status(&status_path, &rows);
        return ExitCode::from(1);
    };
    let plan_write_ok = get(&result, "PLAN_WRITE_OK");
    let publish_ok = get(&result, "PUBLISH_OK");
    let cleanup_eligible = publish_rc != 4
        && plan_write_ok == "true"
        && ctx.standalone_heavy_failed != "true"
        && (ctx.session_id.is_empty() || publish_ok == "true");
    let rows = final_status_rows(&ctx, publish_rc, fallback, cleanup_eligible, &result);
    if let Err(error) = write_status(&status_path, &rows) {
        eprintln!("design-step5c.sh: {error}");
        return ExitCode::from(1);
    }
    for (key, value) in &rows {
        println!("{key}={value}");
    }
    if publish_rc == 4 {
        let refusal = get(&result, "PUBLISH_REFUSE_REASON");
        let status = if GATE_C_REFUSALS.contains(&refusal) {
            refusal
        } else {
            "validator-defects"
        };
        println!("STEP5C_STATUS={status}");
        emit_report_gate_sidecars_from_disk(&design_tmpdir);
        return ExitCode::SUCCESS;
    }
    if plan_write_ok == "true" {
        touch(&design_tmpdir.join(".completed/step-5c"));
    }
    let outcome = if plan_write_ok == "true" {
        "approved"
    } else {
        "failed-plan-write"
    };
    let summary = if get(&result, "FINAL_SUMMARY_PATH").is_empty() {
        design_tmpdir.join("final-summary.md")
    } else {
        PathBuf::from(get(&result, "FINAL_SUMMARY_PATH"))
    };
    if render_summary(
        runner,
        &plugin_root,
        &design_tmpdir,
        &ctx,
        outcome,
        &summary,
    ) {
        emit_summary(&design_tmpdir, &summary, &status_path);
    }
    emit_report_gate_sidecars_from_disk(&design_tmpdir);
    ExitCode::SUCCESS
}

pub fn step5c(arguments: &[OsString]) -> ExitCode {
    let child_suffix = arguments.len() >= 3
        && arguments[arguments.len() - 3] == "--bgjob-child"
        && arguments[arguments.len() - 2] == "--merge-result-env"
        && !arguments[arguments.len() - 1].is_empty();
    let invalid_child_control = arguments.iter().enumerate().any(|(index, arg)| {
        (arg == "--bgjob-child" || arg == "--merge-result-env")
            && !(child_suffix && (index == arguments.len() - 3 || index == arguments.len() - 2))
    });
    if invalid_child_control {
        eprintln!("design-step5c.sh: adapter child controls must be one terminal suffix");
        return ExitCode::from(2);
    }
    let core_arguments = if child_suffix {
        &arguments[..arguments.len() - 3]
    } else {
        arguments
    };
    let result = step5c_with(core_arguments, &LiveStep0Runner);
    if !child_suffix {
        return result;
    }
    let Ok(parsed) = parse_wrapper(&utf8(core_arguments)) else {
        return ExitCode::from(1);
    };
    let env = wrapper_env(&parsed);
    let tmpdir = PathBuf::from(env_get(&env, "DESIGN_TMPDIR", ""));
    let merge_env = PathBuf::from(&arguments[arguments.len() - 1]);
    let required = [
        "PUBLISH_RC",
        "PLAN_WRITE_OK",
        "PUBLISH_OK",
        "VALIDATE_STATUS",
        "FINAL_SUMMARY_PATH",
        "CLEANUP_ELIGIBLE",
    ];
    let Some(rows) = read_env_file(
        &tmpdir.join(".design-step5c-status.env"),
        STEP5C_STATUS_ALLOW,
    )
    .filter(|rows| {
        required
            .iter()
            .all(|key| rows.iter().any(|row| row.0 == *key))
    }) else {
        return ExitCode::from(1);
    };
    let mut body = String::new();
    for (key, value) in &rows {
        let _ = writeln!(&mut body, "{key}={value}");
    }
    let Ok(merge_env) = validate_merge_result_env(&merge_env, &tmpdir) else {
        return ExitCode::from(1);
    };
    if private_atomic_write(&merge_env, &body, &tmpdir).is_err() {
        return ExitCode::from(1);
    }
    result
}

fn pause_args(design_tmpdir: &Path, ctx: &StepCtx) -> Vec<String> {
    let mut args = vec![
        "design".to_owned(),
        "pause-save".to_owned(),
        "--design-tmpdir".to_owned(),
        design_tmpdir.display().to_string(),
        "--issue".to_owned(),
        ctx.issue.clone(),
    ];
    if !ctx.repo.is_empty() {
        args.extend(["--repo".to_owned(), ctx.repo.clone()]);
    }
    args
}

// ---------------------------------------------------------------------------
// Step 6
// ---------------------------------------------------------------------------

fn step6_in_flight(design_tmpdir: Option<&Path>) -> bool {
    let Some(design_tmpdir) = design_tmpdir else {
        return false;
    };
    if result_env_path(design_tmpdir, STEP5C_STEP)
        .is_ok_and(|path| path.is_file() && !path.is_symlink())
    {
        return false;
    }
    let run_id = resolve_owned_run_id(design_tmpdir);
    let Ok((path, entry)) = read_for(design_tmpdir, STEP5C_STEP, run_id.as_deref()) else {
        return false;
    };
    let Some(entry) = entry else {
        return false;
    };
    let host = SystemProcessIdentityHost::new();
    if child_liveness(&host, &entry).live || daemon_liveness(&host, &entry).live {
        return true;
    }
    unlink_entry(&path);
    false
}

fn pause_if_requested(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: Option<&Path>,
    ctx: &StepCtx,
) -> Option<i32> {
    let design_tmpdir = design_tmpdir?;
    if !design_tmpdir.join(".pause-requested").is_file() {
        return None;
    }
    let pause = runner.run(plugin_root, &pause_args(design_tmpdir, ctx), &[], false);
    print_text(&pause.stdout);
    eprint!("{}", pause.stderr);
    Some(pause.code)
}

fn step6_request(arguments: &[OsString], prefix: &str) -> Result<(WrapperArgs, Env), ExitCode> {
    let argv = utf8(arguments);
    let parsed = parse_wrapper(&argv).map_err(|message| {
        eprintln!("{prefix}: {message}");
        ExitCode::from(2)
    })?;
    let env = wrapper_env(&parsed);
    Ok((parsed, env))
}

fn step6_prelude_with(arguments: &[OsString], runner: &dyn Step0Runner) -> ExitCode {
    let (parsed, env) = match step6_request(arguments, "design-step6-prelude.sh") {
        Ok(request) => request,
        Err(code) => return code,
    };
    let raw = env_get(&env, "DESIGN_TMPDIR", "");
    let design_tmpdir = (!raw.is_empty()).then(|| PathBuf::from(raw));
    let root = PathBuf::from(env_get(&env, "CLAUDE_PLUGIN_ROOT", ""));
    let ctx = step_ctx(&env, &parsed);
    if let Some(code) = pause_if_requested(runner, &root, design_tmpdir.as_deref(), &ctx) {
        return exit_from_i32(code);
    }
    if step6_in_flight(design_tmpdir.as_deref()) {
        eprintln!(
            "**⚠ Step 6 prelude: design-step5c.sh appears still in-flight; run bgjob wait for design-step5c before Step 6.**"
        );
        return ExitCode::from(1);
    }
    let Some(design_tmpdir) = design_tmpdir else {
        println!(
            "**{INFO_ICON} Step 6 prelude: missing Step 5c status sidecar; skipping step-5d write.**"
        );
        println!("STEP6_PRELUDE_STATUS=skipped");
        return ExitCode::SUCCESS;
    };
    let sidecar = design_tmpdir.join(".design-step5c-status.env");
    let Some(status) = read_env_file(&sidecar, STEP5C_STATUS_ALLOW).map(|rows| env_map(&rows))
    else {
        println!(
            "**{INFO_ICON} Step 6 prelude: missing Step 5c status sidecar; skipping step-5d write.**"
        );
        println!("STEP6_PRELUDE_STATUS=skipped");
        return ExitCode::SUCCESS;
    };
    let reason = if get(&status, "PLAN_WRITE_OK") != "true" {
        Some("plan write did not succeed")
    } else if !get(&status, "SESSION_ID").is_empty() && get(&status, "PUBLISH_OK") != "true" {
        Some("publish did not complete")
    } else if get(&status, "CLEANUP_ELIGIBLE") == "false" {
        Some("cleanup not eligible per Step 5c status")
    } else {
        None
    };
    if let Some(reason) = reason {
        println!("**{INFO_ICON} Step 6 prelude: {reason}; skipping step-5d write.**");
        println!("STEP6_PRELUDE_STATUS=skipped");
        return ExitCode::SUCCESS;
    }
    let design_tmpdir = match validate_tmpdir(raw) {
        Ok(path) => path,
        Err(message) => {
            eprintln!("design-step6-prelude.sh: {message}");
            return ExitCode::from(1);
        }
    };
    touch(&design_tmpdir.join(".completed/step-5d"));
    if let Some(code) = pause_if_requested(runner, &root, Some(&design_tmpdir), &ctx) {
        return exit_from_i32(code);
    }
    let _ = runner.run(
        &root,
        &[
            "timing".to_owned(),
            "mark".to_owned(),
            "design Step 6 — cleanup".to_owned(),
        ],
        &[("LARCH_TIMING_SKILL".to_owned(), "design".to_owned())],
        false,
    );
    ExitCode::SUCCESS
}

pub fn step6_prelude(arguments: &[OsString]) -> ExitCode {
    step6_prelude_with(arguments, &LiveStep0Runner)
}

fn preservation_message(status: &BTreeMap<String, String>) -> Option<String> {
    if get(status, "PLAN_WRITE_OK") != "true" {
        return Some(format!(
            "**{INFO_ICON} Step 6: plan write did not succeed; preserving $DESIGN_TMPDIR.**"
        ));
    }
    if get(status, "STANDALONE_HEAVY_FAILED") == "true" {
        return Some(format!(
            "**{INFO_ICON} Step 6: standalone heavy failed; preserving $DESIGN_TMPDIR.**"
        ));
    }
    if !get(status, "SESSION_ID").is_empty() && get(status, "PUBLISH_OK") != "true" {
        return Some(format!(
            "**{INFO_ICON} Step 6: publish did not complete; preserving $DESIGN_TMPDIR for recovery.**"
        ));
    }
    if get(status, "CLEANUP_ELIGIBLE") == "false" {
        return Some(format!(
            "**{INFO_ICON} Step 6: cleanup not eligible per Step 5c status; preserving $DESIGN_TMPDIR.**"
        ));
    }
    None
}

fn step6_cleanup_with(arguments: &[OsString], runner: &dyn Step0Runner) -> ExitCode {
    let (parsed, env) = match step6_request(arguments, "design-step6-cleanup.sh") {
        Ok(request) => request,
        Err(code) => return code,
    };
    let raw = env_get(&env, "DESIGN_TMPDIR", "");
    let design_tmpdir = (!raw.is_empty()).then(|| PathBuf::from(raw));
    let root_raw = env_get(&env, "CLAUDE_PLUGIN_ROOT", "");
    let root = PathBuf::from(root_raw);
    let ctx = step_ctx(&env, &parsed);
    if let Some(code) = pause_if_requested(runner, &root, design_tmpdir.as_deref(), &ctx) {
        return exit_from_i32(code);
    }
    if step6_in_flight(design_tmpdir.as_deref()) {
        eprintln!(
            "**⚠ Step 6: design-step5c.sh appears still in-flight; run bgjob wait for design-step5c before Step 6.**"
        );
        return ExitCode::from(1);
    }
    let Some(design_tmpdir) = design_tmpdir else {
        println!(
            "**{INFO_ICON} Step 6: missing Step 5c status sidecar; preserving $DESIGN_TMPDIR for recovery.**"
        );
        println!("CLEANUP_STATUS=preserved");
        return ExitCode::SUCCESS;
    };
    let sidecar = design_tmpdir.join(".design-step5c-status.env");
    let Some(status) = read_env_file(&sidecar, STEP5C_STATUS_ALLOW).map(|rows| env_map(&rows))
    else {
        println!(
            "**{INFO_ICON} Step 6: missing Step 5c status sidecar; preserving $DESIGN_TMPDIR for recovery.**"
        );
        println!("CLEANUP_STATUS=preserved");
        return ExitCode::SUCCESS;
    };
    if let Some(message) = preservation_message(&status) {
        println!("{message}");
        println!("CLEANUP_STATUS=preserved");
        return ExitCode::SUCCESS;
    }
    if let Err(message) = validate_claude_pid(&parsed.claude_pid) {
        eprintln!("design-step6-cleanup.sh: {message}");
        return ExitCode::from(2);
    }
    let design_tmpdir = match validate_tmpdir(raw) {
        Ok(path) => path,
        Err(message) => {
            eprintln!("design-step6-cleanup.sh: {message}");
            return ExitCode::from(1);
        }
    };
    let plugin_root = match require_plugin_root(env_get(&env, "CLAUDE_PLUGIN_ROOT", "")) {
        Ok(path) => path,
        Err(code) => return code,
    };
    touch(&design_tmpdir.join(".completed/step-6"));
    if let Some(run_id) = resolve_owned_run_id(&design_tmpdir) {
        let repo_root = resolve_persisted_repo_root(&design_tmpdir)
            .or_else(|| std::env::current_dir().ok())
            .unwrap_or_else(|| PathBuf::from("."));
        let host = SystemProcessIdentityHost::new();
        if !has_live_entry(&host, &repo_root, &run_id) {
            run_progress_deactivate(runner, &plugin_root, &repo_root, &run_id);
        }
    }
    let cleanup = run_session_cleanup(runner, &plugin_root, &design_tmpdir);
    print_text(&cleanup.stdout);
    eprint!("{}", cleanup.stderr);
    if cleanup.code != 0 {
        return exit_from_i32(cleanup.code);
    }
    if let Err(message) = reap_pid_residuals(&parsed.claude_pid) {
        eprintln!("design-step6-cleanup.sh: {message}");
        return ExitCode::from(1);
    }
    ExitCode::SUCCESS
}

pub fn step6_cleanup(arguments: &[OsString]) -> ExitCode {
    step6_cleanup_with(arguments, &LiveStep0Runner)
}

pub fn step6(arguments: &[OsString]) -> ExitCode {
    let argv = utf8(arguments);
    let parsed = match parse_wrapper(&argv) {
        Ok(parsed) => parsed,
        Err(message) => {
            eprintln!("design-step6.sh: {message}");
            return ExitCode::from(2);
        }
    };
    let env = wrapper_env(&parsed);
    let raw = env_get(&env, "DESIGN_TMPDIR", "");
    let pause_complete = validate_tmpdir(raw)
        .ok()
        .map(|path| path.join(".pause-save-complete"));
    if let Some(path) = &pause_complete {
        let _ = fs::remove_file(path);
    }
    let prelude = step6_prelude_with(arguments, &LiveStep0Runner);
    if prelude != ExitCode::SUCCESS {
        return prelude;
    }
    if pause_complete.is_some_and(|path| path.is_file()) {
        return ExitCode::SUCCESS;
    }
    step6_cleanup_with(arguments, &LiveStep0Runner)
}
