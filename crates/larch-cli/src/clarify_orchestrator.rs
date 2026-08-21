//! The `design clarify` Step 0b fetch/publish orchestrator (#8587).
//!
//! Ported from `python/larch/design/clarify.py`'s `design_clarify_main`. The
//! fetch phase reads the open clarify request into the design tmpdir; the
//! publish phase redacts and republishes the resolved plan, posts the response,
//! removes the label, publishes the design log, and renames the tracking issue.
//! GitHub effects run behind [`ClarifyEffects`]; sibling verbs run behind
//! [`SiblingRunner`] so the phase machine stays provable offline.

use std::collections::BTreeMap;
use std::ffi::OsString;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::ExitCode;
use std::time::Duration;

use larch_core::{
    ChildEnvironment, DESIGN_RAW_RATING_BASENAME, DIFFICULTY_RECORD_BASENAME, DifficultyRating,
    ProcessOutput, build_design_record, plan_difficulty, read_rating_file, redact_secrets_only,
    rewrite_plan_difficulty, validate_rating_object, write_record_map,
};

use crate::clarify_commands::{
    ClarifyEffects, LiveEffects, clarify_comment_fetch, clarify_comment_post, clarify_label,
    clarify_state, is_positive_int_text,
};
use crate::design_step0_commands::{
    Env, atomic_write_string, clarify_failure_stage_args, exit_from_i32, load_source_env,
    phase_driver_read_result_env, require_design_tmpdir, stage_terminal_state_bridge,
};
use crate::github_repository_resolution::validate_repo_slug;
use crate::implement_dispatch_commands::{delegate_verified_larch, run_verified_larch_env_in};
use crate::python_verb::{plugin_root_directory, run_python_verb};

/// Environment keys the source-env merge carries into the driver.
const CLARIFY_ENV_ALLOW: [&str; 5] = [
    "CLAUDE_PLUGIN_ROOT",
    "DESIGN_TMPDIR",
    "SESSION_ID",
    "ISSUE_NUMBER",
    "REPO",
];
/// Keys read back from the fetch-phase request-state sidecar.
const REQUEST_STATE_ALLOW: [&str; 6] = [
    "REQUEST_ID",
    "REQUEST_BODY_FILE",
    "PLAN_FILE",
    "RESPONSE_FILE",
    "ISSUE_NUMBER",
    "REPO",
];
/// The one key recovered from the Step 0 route-state sidecar.
const ROUTE_STATE_ALLOW: [&str; 1] = ["REPO"];
/// Keys any clarify result-env write may carry.
const CLARIFY_RESULT_ENV_ALLOW: [&str; 13] = [
    "CLARIFY_FETCH_STATUS",
    "CLARIFY_PUBLISH_STATUS",
    "ISSUE_NUMBER",
    "PLAN_FILE",
    "PLAN_WRITE_OK",
    "PUBLISH_OK",
    "RENAMED",
    "REPO",
    "REQUEST_BODY_FILE",
    "REQUEST_ID",
    "RESPONSE_FILE",
    "STATE",
    "SUMMARY_OUTCOME",
];

/// Timeout for a delegated sibling verb, matching the Python phase driver.
const SIBLING_TIMEOUT: Duration = Duration::from_secs(120);

/// The parsed `design clarify` argv.
struct DesignClarifyArgs {
    session_env_path: String,
    claude_pid: String,
    phase: String,
    issue: String,
}

/// One captured sibling-verb run: exit code and decoded streams.
pub struct CapturedRun {
    pub(crate) rc: i32,
    pub(crate) stdout: String,
    pub(crate) stderr: String,
}

impl CapturedRun {
    pub(crate) fn from_output(output: Result<ProcessOutput, String>) -> Self {
        match output {
            Ok(output) => {
                let (rc, stdout, stderr) = output.decoded_streams();
                Self { rc, stdout, stderr }
            }
            // A dispatch failure (verified-bootstrap or spawn error) carries no
            // child streams; keep its detail on stderr so the failure sidecars
            // this run writes are not empty and undiagnosable.
            Err(error) => Self {
                rc: 1,
                stdout: String::new(),
                stderr: error,
            },
        }
    }
}

/// Every sibling verb the orchestrator drives, behind one seam.
pub trait SiblingRunner {
    /// Run one Rust-owned verb through the verified bootstrap.
    fn run_larch(&self, args: &[OsString]) -> CapturedRun;
    /// Run one still-Python verb through the dispatcher.
    fn run_python(&self, args: &[OsString]) -> CapturedRun;

    /// Run one Rust-owned verb with scoped environment additions.
    ///
    /// The default ignores the additions so an offline stub only has to answer
    /// the two base methods; the live runner forwards them.
    fn run_larch_env(
        &self,
        args: &[OsString],
        _environment: &[(ChildEnvironment, OsString)],
    ) -> CapturedRun {
        self.run_larch(args)
    }
}

/// The live runner: verified bootstrap for Rust, cli.py for Python.
pub struct LiveRunner {
    cwd: PathBuf,
    root: PathBuf,
}

impl LiveRunner {
    /// Build the live runner for a working directory and plugin root.
    pub(crate) const fn new(cwd: PathBuf, root: PathBuf) -> Self {
        Self { cwd, root }
    }
}

impl SiblingRunner for LiveRunner {
    fn run_larch(&self, args: &[OsString]) -> CapturedRun {
        CapturedRun::from_output(delegate_verified_larch(&self.cwd, &self.root, args))
    }

    fn run_python(&self, args: &[OsString]) -> CapturedRun {
        CapturedRun::from_output(run_python_verb(args.iter().cloned(), SIBLING_TIMEOUT))
    }

    fn run_larch_env(
        &self,
        args: &[OsString],
        environment: &[(ChildEnvironment, OsString)],
    ) -> CapturedRun {
        CapturedRun::from_output(run_verified_larch_env_in(
            &self.cwd,
            &self.root,
            args,
            environment,
        ))
    }
}

// ---------------------------------------------------------------------------
// small helpers
// ---------------------------------------------------------------------------

/// Build an `OsString` argv from string slices.
fn osargs(parts: &[&str]) -> Vec<OsString> {
    parts.iter().map(OsString::from).collect()
}

/// Last value for `key` in a KEY=value stream, CR-trimmed.
pub fn kv_last(text: &str, key: &str) -> String {
    let prefix = format!("{key}=");
    let mut value = String::new();
    for line in text.split('\n') {
        if let Some(rest) = line.strip_prefix(&prefix) {
            value.clear();
            value.push_str(rest.trim_end_matches('\r'));
        }
    }
    value
}

/// Read a file as UTF-8, replacing invalid bytes.
fn read_lossy(path: &str) -> String {
    fs::read(path).map_or_else(
        |_error| String::new(),
        |bytes| String::from_utf8_lossy(&bytes).into_owned(),
    )
}

/// True when a publish artifact is a non-empty readable regular file.
pub fn publish_artifact_ok(path: &Path) -> bool {
    !path.is_symlink()
        && path.is_file()
        && fs::metadata(path)
            .map(|meta| meta.len() > 0)
            .unwrap_or(false)
}

/// Emit KEY=value rows to stdout, one per line.
fn emit_design_kvs(rows: &[(&str, &str)]) {
    for (key, value) in rows {
        println!("{key}={value}");
    }
}

/// Atomically write allowlisted, newline-free KEY=value rows to a result env.
pub fn write_result_env(path: &Path, rows: &[(&str, &str)], allow: &[&str]) -> Result<(), String> {
    if path.is_symlink() {
        return Err(format!(
            "refusing to write symlink result env: {}",
            path.display()
        ));
    }
    let mut body = String::new();
    for (key, value) in rows {
        if !allow.contains(key) {
            return Err(format!("result env key is not allowlisted: {key}"));
        }
        if value.contains('\n') || value.contains('\r') {
            return Err(format!("result env value contains newline: {key}"));
        }
        body.push_str(key);
        body.push('=');
        body.push_str(value);
        body.push('\n');
    }
    if atomic_write_string(path, &body) {
        Ok(())
    } else {
        Err(format!("failed to write result env: {}", path.display()))
    }
}

/// Build the `named-block write --marker plan` argv both phase machines run.
pub fn plan_named_block_args(
    issue: &str,
    content_file: &Path,
    repo_args: &[String],
) -> Vec<String> {
    let mut args = vec![
        "named-block".to_owned(),
        "write".to_owned(),
        "--marker".to_owned(),
        "plan".to_owned(),
        "--issue".to_owned(),
        issue.to_owned(),
        "--content-file".to_owned(),
        content_file.display().to_string(),
    ];
    args.extend(repo_args.iter().cloned());
    args
}

/// Read allowlisted rows from a result env, or `Err` on a trust-boundary miss.
fn read_result_env(path: &Path, allowed: &[&str]) -> Result<Env, ()> {
    let pairs = phase_driver_read_result_env(path, allowed)?;
    Ok(pairs.into_iter().collect())
}

/// Refuse an invalid explicit repository slug with the usage exit code.
fn validate_design_repo(repo: &str) -> Result<(), ExitCode> {
    if !repo.is_empty() && !validate_repo_slug(repo) {
        eprintln!("design-clarify.sh: invalid --repo");
        return Err(ExitCode::from(2));
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// difficulty
// ---------------------------------------------------------------------------

/// Resolve the publish difficulty rating: `(rating, raw_sidecar_invalid)`.
pub fn resolve_publish_difficulty_rating(
    design_tmpdir: &Path,
    plan_text: &str,
) -> (Option<DifficultyRating>, bool) {
    let raw_path = design_tmpdir.join(DESIGN_RAW_RATING_BASENAME);
    if raw_path.exists() || raw_path.is_symlink() {
        return read_rating_file(&raw_path).map_or((None, true), |rating| (Some(rating), false));
    }
    let tier = plan_difficulty(plan_text);
    if tier.is_empty() {
        return (None, false);
    }
    let object = serde_json::json!({
        "predicted_tier": tier,
        "confidence": "medium",
        "rationale": "design plan metadata",
    });
    (validate_rating_object(&object).ok(), false)
}

// ---------------------------------------------------------------------------
// failure logging / staging
// ---------------------------------------------------------------------------

/// Append one best-effort clarify warning through `run-log append-failure`.
fn append_clarify_failure(
    runner: &dyn SiblingRunner,
    design_tmpdir: &Path,
    site: &str,
    tool: &str,
    exit_code: i32,
    output_file: &Path,
) {
    let log = design_tmpdir.join("execution-issues.md");
    let _ignored = runner.run_larch(&osargs(&[
        "run-log",
        "append-failure",
        "--log",
        &log.display().to_string(),
        "--site",
        site,
        "--tool",
        tool,
        "--exit-code",
        &exit_code.to_string(),
        "--category",
        "Warnings",
        "--redact",
        "--output-file",
        &output_file.display().to_string(),
    ]));
}

/// Stage the shared failed-clarify terminal state through the Python driver.
fn stage_failed_clarify(
    runner: &dyn SiblingRunner,
    design_tmpdir: &Path,
    exit_code: i32,
    detail_log: &Path,
) {
    if !detail_log.is_file() {
        let _ = fs::write(detail_log, "clarify failure\n");
    }
    let stdout_log = design_tmpdir.join("design-clarify-stage.stdout.log");
    let stderr_log = design_tmpdir.join("design-clarify-stage.stderr.log");
    // #8580 flipped `design stage-terminal-state` to a Rust owner reached through
    // the larch entrypoint, so the bridge now needs the resolved plugin root.
    let plugin_root = plugin_root_directory().unwrap_or_default();
    let rc = stage_terminal_state_bridge(
        &plugin_root,
        &stdout_log,
        &stderr_log,
        &clarify_failure_stage_args(design_tmpdir, &exit_code.to_string(), detail_log),
    );
    if rc != 0 {
        append_clarify_failure(
            runner,
            design_tmpdir,
            "design Step 0b clarify fetch",
            "design-stage-terminal-state.sh",
            rc,
            &stderr_log,
        );
    }
}

/// Publish the design log and upsert the summary; return the `"true"`/`"false"`.
fn publish_clarify_log_and_summary(
    runner: &dyn SiblingRunner,
    design_tmpdir: &Path,
    issue: &str,
    repo_args: &[String],
    session_id: &str,
    outcome: &str,
) -> String {
    if session_id.is_empty() {
        println!("\n**⚠ /design: SESSION_ID missing; skipping design log publish**");
        return "false".to_owned();
    }
    let mut args = vec![
        "design".to_owned(),
        "log-publish".to_owned(),
        "--design-tmpdir".to_owned(),
        design_tmpdir.display().to_string(),
        "--run-id".to_owned(),
        session_id.to_owned(),
        "--issue".to_owned(),
        issue.to_owned(),
        "--outcome".to_owned(),
        outcome.to_owned(),
    ];
    args.extend(repo_args.iter().cloned());
    let publish = runner.run_larch(&args.iter().map(OsString::from).collect::<Vec<_>>());
    let _ = fs::write(
        design_tmpdir.join("design-log-publish.stdout"),
        &publish.stdout,
    );
    let failure_log = design_tmpdir.join("design-log-publish.failure.log");
    let _ = fs::write(&failure_log, &publish.stderr);
    let parsed_ok = kv_last(&publish.stdout, "PUBLISH_OK");
    let recovery = kv_last(&publish.stdout, "RECOVERY_BRANCH");
    let publish_ok = publish.rc == 0 && parsed_ok == "true" && recovery.is_empty();
    if !publish_ok {
        let failure_exit = if publish.rc != 0 { publish.rc } else { 1 };
        append_clarify_failure(
            runner,
            design_tmpdir,
            "design Step 0b clarify publish",
            "design-log-publish.sh",
            failure_exit,
            &failure_log,
        );
        return "false".to_owned();
    }
    if !upsert_final_summary_from_disk(runner, design_tmpdir, issue, session_id, repo_args) {
        let upsert_log = design_tmpdir.join(format!("summary-upsert.{outcome}.failure.log"));
        let _ = fs::write(
            &upsert_log,
            "tracking-issue upsert-summary failed or final-summary.md missing\n",
        );
        append_clarify_failure(
            runner,
            design_tmpdir,
            "design Step 0b final summary upsert",
            "tracking-issue upsert-summary",
            1,
            &upsert_log,
        );
        return "false".to_owned();
    }
    "true".to_owned()
}

/// Upsert the rendered final summary as the marker-keyed tracking comment.
fn upsert_final_summary_from_disk(
    runner: &dyn SiblingRunner,
    design_tmpdir: &Path,
    issue: &str,
    session_id: &str,
    repo_args: &[String],
) -> bool {
    let summary = design_tmpdir.join("final-summary.md");
    if summary.is_symlink()
        || !summary.is_file()
        || fs::metadata(&summary)
            .map(|meta| meta.len() == 0)
            .unwrap_or(true)
    {
        return false;
    }
    if issue.is_empty() || issue == "0" || session_id.is_empty() {
        return false;
    }
    let marker = format!("<!-- larch:final-summary v1 runid={session_id} -->");
    let mut args = vec![
        "tracking-issue".to_owned(),
        "upsert-summary".to_owned(),
        "--issue".to_owned(),
        issue.to_owned(),
        "--marker".to_owned(),
        marker,
        "--content-file".to_owned(),
        summary.display().to_string(),
    ];
    args.extend(repo_args.iter().cloned());
    runner
        .run_larch(&args.iter().map(OsString::from).collect::<Vec<_>>())
        .rc
        == 0
}

/// Classify the publish status from the `"true"`/`"false"` and its sidecars.
fn clarify_publish_status(design_tmpdir: &Path, publish_ok: &str) -> String {
    if publish_ok == "true" {
        return "ok".to_owned();
    }
    let publish_stdout = design_tmpdir.join("design-log-publish.stdout");
    if publish_stdout.is_file()
        && !kv_last(
            &read_lossy(&publish_stdout.display().to_string()),
            "RECOVERY_BRANCH",
        )
        .is_empty()
    {
        return "log-publish-recovery".to_owned();
    }
    if has_summary_upsert_failure(design_tmpdir) {
        return "summary-upsert-failed".to_owned();
    }
    "log-publish-failed".to_owned()
}

/// True when any `summary-upsert.*.failure.log` sidecar is present.
fn has_summary_upsert_failure(design_tmpdir: &Path) -> bool {
    let Ok(entries) = fs::read_dir(design_tmpdir) else {
        return false;
    };
    entries.flatten().any(|entry| {
        let name = entry.file_name();
        let name = name.to_string_lossy();
        name.starts_with("summary-upsert.") && name.ends_with(".failure.log")
    })
}

// ---------------------------------------------------------------------------
// phase failure emitters
// ---------------------------------------------------------------------------

/// Emit the fetch-phase failure result env, stage terminal state, return 1.
fn fetch_failure(
    runner: &dyn SiblingRunner,
    design_tmpdir: &Path,
    status: &str,
    detail_log: &Path,
    exit_code: i32,
    extra_rows: &[(&str, &str)],
) -> ExitCode {
    let mut rows: Vec<(&str, &str)> = vec![("CLARIFY_FETCH_STATUS", status)];
    rows.extend_from_slice(extra_rows);
    rows.push(("SUMMARY_OUTCOME", "failed-clarify"));
    let _ = write_result_env(
        &design_tmpdir.join(".design-clarify-fetch-result.env"),
        &rows,
        &CLARIFY_RESULT_ENV_ALLOW,
    );
    stage_failed_clarify(runner, design_tmpdir, exit_code, detail_log);
    emit_design_kvs(&rows);
    ExitCode::from(1)
}

/// Emit the publish-phase failure result env and return 1.
fn publish_failure(
    design_tmpdir: &Path,
    status: &str,
    summary: &str,
    extra_rows: &[(&str, &str)],
) -> ExitCode {
    let mut rows: Vec<(&str, &str)> = vec![("CLARIFY_PUBLISH_STATUS", status)];
    rows.extend_from_slice(extra_rows);
    rows.push(("SUMMARY_OUTCOME", summary));
    let _ = write_result_env(
        &design_tmpdir.join(".design-clarify-publish-result.env"),
        &rows,
        &CLARIFY_RESULT_ENV_ALLOW,
    );
    emit_design_kvs(&rows);
    ExitCode::from(1)
}

// ---------------------------------------------------------------------------
// fetch phase
// ---------------------------------------------------------------------------

fn handle_fetch(
    effects: &dyn ClarifyEffects,
    runner: &dyn SiblingRunner,
    args: &DesignClarifyArgs,
    env: &Env,
    design_tmpdir: &Path,
) -> ExitCode {
    let request_body_file = design_tmpdir.join("clarify-request.md");
    let plan_file = design_tmpdir.join("clarify-plan.md");
    let response_file = design_tmpdir.join("clarify-response.md");
    let repo = env
        .get("REPO")
        .filter(|value| !value.is_empty())
        .map(String::as_str);

    let state = match clarify_state(effects, &args.issue, repo) {
        Ok(state) => state,
        Err(error) => {
            let detail = design_tmpdir.join("clarify-state.stderr");
            let _ = fs::write(&detail, format!("{error:?}"));
            return fetch_failure(runner, design_tmpdir, "state-failed", &detail, 1, &[]);
        }
    };
    if state.state != "awaiting-response" || state.last_request_id.is_empty() {
        let detail = design_tmpdir.join("clarify-fetch.failure.log");
        let shown = if state.state.is_empty() {
            "<empty>"
        } else {
            &state.state
        };
        let _ = fs::write(&detail, format!("unexpected clarify state: {shown}\n"));
        return fetch_failure(
            runner,
            design_tmpdir,
            "unexpected-state",
            &detail,
            1,
            &[("STATE", &state.state)],
        );
    }

    let fetched = match clarify_comment_fetch(
        effects,
        &args.issue,
        &state.last_request_id,
        &request_body_file.display().to_string(),
        repo,
    ) {
        Ok(result) => result,
        Err(error) => {
            let detail = design_tmpdir.join("clarify-comment-fetch.stderr");
            let _ = fs::write(&detail, format!("{error:?}"));
            return fetch_failure(runner, design_tmpdir, "fetch-failed", &detail, 1, &[]);
        }
    };
    let _ = fetched;

    let repo_present = env.get("REPO").filter(|value| !value.is_empty()).cloned();
    let request_body = request_body_file.display().to_string();
    let plan = plan_file.display().to_string();
    let response = response_file.display().to_string();
    let mut rows: Vec<(&str, &str)> = vec![
        ("CLARIFY_FETCH_STATUS", "ok"),
        ("REQUEST_ID", &state.last_request_id),
        ("REQUEST_BODY_FILE", &request_body),
        ("PLAN_FILE", &plan),
        ("RESPONSE_FILE", &response),
        ("ISSUE_NUMBER", &args.issue),
    ];
    if let Some(repo) = &repo_present {
        rows.push(("REPO", repo));
    }
    if let Err(error) = write_result_env(
        &design_tmpdir.join(".design-clarify-request.env"),
        &rows[1..],
        &CLARIFY_RESULT_ENV_ALLOW,
    ) {
        return emit_write_failure(&error);
    }
    if let Err(error) = write_result_env(
        &design_tmpdir.join(".design-clarify-fetch-result.env"),
        &rows,
        &CLARIFY_RESULT_ENV_ALLOW,
    ) {
        return emit_write_failure(&error);
    }
    emit_design_kvs(&rows);
    ExitCode::from(0)
}

/// Report a result-env write failure the way the Python owner did: exit 2.
///
/// The retired Python owner raised `_ClarifyValidationError` from
/// `_write_result_env`, which the top-level handler turned into a stderr line
/// and exit 2; a swallowed write here would otherwise report false success.
fn emit_write_failure(error: &str) -> ExitCode {
    eprintln!("design-clarify.sh: {error}");
    ExitCode::from(2)
}

// ---------------------------------------------------------------------------
// publish phase
// ---------------------------------------------------------------------------

fn handle_publish(
    effects: &dyn ClarifyEffects,
    runner: &dyn SiblingRunner,
    args: &DesignClarifyArgs,
    env: &mut Env,
    design_tmpdir: &Path,
) -> ExitCode {
    let Ok(request) = read_result_env(
        &design_tmpdir.join(".design-clarify-request.env"),
        &REQUEST_STATE_ALLOW,
    ) else {
        return publish_failure(
            design_tmpdir,
            "missing-request-state",
            "failed-clarify",
            &[],
        );
    };
    let request_id = request.get("REQUEST_ID").cloned().unwrap_or_default();
    if !is_positive_int_text(&request_id) {
        eprintln!("design-clarify.sh: REQUEST_ID must be a positive integer");
        return ExitCode::from(2);
    }
    if request.get("ISSUE_NUMBER").map(String::as_str) != Some(args.issue.as_str()) {
        return publish_failure(design_tmpdir, "issue-mismatch", "failed-clarify", &[]);
    }
    if let Some(repo) = request.get("REPO") {
        let _ = env.insert("REPO".to_owned(), repo.clone());
    }
    if let Err(code) = validate_design_repo(env.get("REPO").map_or("", String::as_str)) {
        return code;
    }
    let plan_file = request.get("PLAN_FILE").cloned().unwrap_or_default();
    let response_file = request.get("RESPONSE_FILE").cloned().unwrap_or_default();
    if !publish_artifact_ok(Path::new(&plan_file))
        || !publish_artifact_ok(Path::new(&response_file))
    {
        return publish_failure(design_tmpdir, "missing-artifact", "failed-clarify", &[]);
    }

    let (rating, redacted_plan) = match prepare_redacted_plan(design_tmpdir, &plan_file) {
        Ok(pair) => pair,
        Err(code) => return code,
    };

    let repo = env.get("REPO").cloned().unwrap_or_default();
    let repo_args: Vec<String> = if repo.is_empty() {
        Vec::new()
    } else {
        vec!["--repo".to_owned(), repo.clone()]
    };

    let plan_args = plan_named_block_args(&args.issue, &redacted_plan, &repo_args);
    let plan_write = runner.run_larch(&plan_args.iter().map(OsString::from).collect::<Vec<_>>());
    if plan_write.rc != 0 {
        let _ = fs::write(
            design_tmpdir.join("clarify-plan-write.failure.log"),
            "plan-block write failed\n",
        );
        return publish_failure(
            design_tmpdir,
            "plan-write-failed",
            "failed-plan-write",
            &[("PLAN_WRITE_OK", "false")],
        );
    }

    let mut sync_args = vec![
        "difficulty".to_owned(),
        "sync-labels".to_owned(),
        "--issue".to_owned(),
        args.issue.clone(),
        "--tier".to_owned(),
        rating.adjusted_tier.clone(),
    ];
    sync_args.extend(repo_args.iter().cloned());
    let _ = runner.run_larch(&sync_args.iter().map(OsString::from).collect::<Vec<_>>());

    persist_difficulty_record(runner, design_tmpdir, env, &rating);

    let session_id = env.get("SESSION_ID").cloned().unwrap_or_default();
    publish_finalize(&PublishTail {
        effects,
        runner,
        issue: &args.issue,
        design_tmpdir,
        request_id: &request_id,
        response_file: &response_file,
        repo: &repo,
        repo_args: &repo_args,
        session_id: &session_id,
    })
}

/// Redact the plan, resolve and rewrite its difficulty, and stage it on disk.
///
/// Returns the resolved rating and the redacted plan path, or the terminal
/// exit code of the publish failure that its gate produced.
fn prepare_redacted_plan(
    design_tmpdir: &Path,
    plan_file: &str,
) -> Result<(DifficultyRating, PathBuf), ExitCode> {
    let plan_text = read_lossy(plan_file);
    let redacted = redact_secrets_only(&plan_text);
    let (rating, raw_invalid) = resolve_publish_difficulty_rating(design_tmpdir, &plan_text);
    if raw_invalid {
        return Err(publish_failure(
            design_tmpdir,
            "difficulty-sidecar-invalid",
            "failed-plan-write",
            &[],
        ));
    }
    let Some(rating) = rating else {
        return Err(publish_failure(
            design_tmpdir,
            "missing-difficulty",
            "failed-plan-write",
            &[],
        ));
    };
    let redacted = rewrite_plan_difficulty(&redacted, &rating.adjusted_tier);
    let redacted_plan = design_tmpdir.join("clarify-plan.redacted.md");
    let _ = fs::write(&redacted_plan, &redacted);
    if !redacted_plan.is_file()
        || fs::metadata(&redacted_plan)
            .map(|meta| meta.len() == 0)
            .unwrap_or(true)
    {
        return Err(publish_failure(
            design_tmpdir,
            "redact-empty",
            "failed-plan-write",
            &[],
        ));
    }
    Ok((rating, redacted_plan))
}

/// The publish-phase tail: post response, drop label, publish log, rename.
#[derive(Clone, Copy)]
struct PublishTail<'a> {
    effects: &'a dyn ClarifyEffects,
    runner: &'a dyn SiblingRunner,
    issue: &'a str,
    design_tmpdir: &'a Path,
    request_id: &'a str,
    response_file: &'a str,
    repo: &'a str,
    repo_args: &'a [String],
    session_id: &'a str,
}

fn publish_finalize(tail: &PublishTail<'_>) -> ExitCode {
    let PublishTail {
        effects,
        runner,
        issue,
        design_tmpdir,
        request_id,
        response_file,
        repo,
        repo_args,
        session_id,
    } = *tail;
    let repo_opt = if repo.is_empty() { None } else { Some(repo) };

    if clarify_comment_post(
        effects,
        issue,
        "response",
        request_id,
        response_file,
        repo_opt,
    )
    .is_err()
    {
        let publish_ok = publish_clarify_log_and_summary(
            runner,
            design_tmpdir,
            issue,
            repo_args,
            session_id,
            "failed-clarify",
        );
        return publish_failure(
            design_tmpdir,
            "comment-post-failed",
            "failed-clarify",
            &[("PLAN_WRITE_OK", "true"), ("PUBLISH_OK", &publish_ok)],
        );
    }

    if clarify_label(effects, issue, "remove", repo_opt, false).is_err() {
        let publish_ok = publish_clarify_log_and_summary(
            runner,
            design_tmpdir,
            issue,
            repo_args,
            session_id,
            "failed-clarify",
        );
        return publish_failure(
            design_tmpdir,
            "label-remove-failed",
            "failed-clarify",
            &[("PLAN_WRITE_OK", "true"), ("PUBLISH_OK", &publish_ok)],
        );
    }

    let publish_ok = publish_clarify_log_and_summary(
        runner,
        design_tmpdir,
        issue,
        repo_args,
        session_id,
        "cancelled-clarify",
    );

    let renamed = rename_after_publish(
        runner,
        design_tmpdir,
        issue,
        repo_args,
        session_id,
        &publish_ok,
    );

    let status = clarify_publish_status(design_tmpdir, &publish_ok);
    let rows: Vec<(&str, &str)> = vec![
        ("CLARIFY_PUBLISH_STATUS", &status),
        ("PLAN_WRITE_OK", "true"),
        ("PUBLISH_OK", &publish_ok),
        ("RENAMED", &renamed),
        ("SUMMARY_OUTCOME", "cancelled-clarify"),
    ];
    if let Err(error) = write_result_env(
        &design_tmpdir.join(".design-clarify-publish-result.env"),
        &rows,
        &CLARIFY_RESULT_ENV_ALLOW,
    ) {
        return emit_write_failure(&error);
    }
    emit_design_kvs(&rows);
    ExitCode::from(0)
}

/// Rename the tracking issue back to `[DESIGNING]` when the publish landed.
///
/// Returns the `RENAMED` token: the child's own value on success, `"false"`
/// on a failed rename (recorded as a warning), or empty when no rename ran.
fn rename_after_publish(
    runner: &dyn SiblingRunner,
    design_tmpdir: &Path,
    issue: &str,
    repo_args: &[String],
    session_id: &str,
    publish_ok: &str,
) -> String {
    if session_id.is_empty() || publish_ok != "true" {
        return String::new();
    }
    let mut rename_args = vec![
        "tracking-issue".to_owned(),
        "rename".to_owned(),
        "--issue".to_owned(),
        issue.to_owned(),
        "--state".to_owned(),
        "designing".to_owned(),
    ];
    rename_args.extend(repo_args.iter().cloned());
    let rename = runner.run_larch(&rename_args.iter().map(OsString::from).collect::<Vec<_>>());
    if rename.rc == 0 {
        return kv_last(&rename.stdout, "RENAMED");
    }
    let rename_stderr = design_tmpdir.join("clarify-rename.stderr");
    let _ = fs::write(&rename_stderr, &rename.stderr);
    append_clarify_failure(
        runner,
        design_tmpdir,
        "design Step 0b clarify rename",
        "scripts/larch.sh tracking-issue rename",
        rename.rc,
        &rename_stderr,
    );
    "false".to_owned()
}

/// Best-effort difficulty-record persistence and run-log batch write.
fn persist_difficulty_record(
    runner: &dyn SiblingRunner,
    design_tmpdir: &Path,
    env: &Env,
    rating: &DifficultyRating,
) {
    let Ok(record) = build_design_record(rating) else {
        return;
    };
    let record_path = design_tmpdir.join(DIFFICULTY_RECORD_BASENAME);
    if write_record_map(&record_path, &record).is_err() {
        return;
    }
    if let Some(session_id) = env.get("SESSION_ID").filter(|value| !value.is_empty()) {
        let _ = runner.run_larch(&osargs(&[
            "run-log",
            "write",
            "--skill",
            "design",
            "--run-id",
            session_id,
            "--batch",
            "difficulty-rating",
            "--input-file",
            &record_path.display().to_string(),
        ]));
    }
}

// ---------------------------------------------------------------------------
// argv + env
// ---------------------------------------------------------------------------

fn design_clarify_usage() {
    eprintln!("Usage: design-clarify.sh --phase fetch|publish --issue N");
}

fn parse_design_clarify_args(argv: &[OsString]) -> Result<DesignClarifyArgs, ExitCode> {
    let tokens: Vec<String> = argv
        .iter()
        .map(|token| token.to_string_lossy().into_owned())
        .collect();
    let mut data: BTreeMap<&str, String> = BTreeMap::new();
    let known = ["--session-env-path", "--claude-pid", "--phase", "--issue"];
    let mut index = 0;
    while index < tokens.len() {
        let token = tokens[index].as_str();
        if token == "-h" || token == "--help" {
            design_clarify_usage();
            return Err(ExitCode::from(0));
        }
        if let Some(flag) = known.iter().find(|flag| **flag == token) {
            let Some(value) = tokens.get(index + 1) else {
                eprintln!("design-clarify.sh: {token} requires a value");
                return Err(ExitCode::from(2));
            };
            let _prior = data.insert(flag, value.clone());
            index += 2;
        } else {
            design_clarify_usage();
            eprintln!("design-clarify.sh: unknown option: {token}");
            return Err(ExitCode::from(2));
        }
    }
    let phase = data.get("--phase").cloned().unwrap_or_default();
    if phase.is_empty() {
        design_clarify_usage();
        eprintln!("design-clarify.sh: --phase is required");
        return Err(ExitCode::from(2));
    }
    if phase != "fetch" && phase != "publish" {
        eprintln!("design-clarify.sh: --phase must be fetch or publish");
        return Err(ExitCode::from(2));
    }
    let issue = data.get("--issue").cloned().unwrap_or_default();
    if issue.is_empty() {
        design_clarify_usage();
        eprintln!("design-clarify.sh: --issue is required");
        return Err(ExitCode::from(2));
    }
    if !is_positive_int_text(&issue) {
        eprintln!("design-clarify.sh: --issue must be a positive integer");
        return Err(ExitCode::from(2));
    }
    let claude_pid = data.get("--claude-pid").cloned().unwrap_or_default();
    if !claude_pid.is_empty() && !is_positive_int_text(&claude_pid) {
        eprintln!("design-clarify.sh: --claude-pid must be a positive integer");
        return Err(ExitCode::from(2));
    }
    Ok(DesignClarifyArgs {
        session_env_path: data.get("--session-env-path").cloned().unwrap_or_default(),
        claude_pid,
        phase,
        issue,
    })
}

fn build_driver_env(args: &DesignClarifyArgs) -> Result<(Env, PathBuf), ExitCode> {
    let mut env: Env = BTreeMap::new();
    for key in CLARIFY_ENV_ALLOW {
        if let Ok(value) = std::env::var(key) {
            let _ = env.insert(key.to_owned(), value);
        }
    }
    for (key, value) in load_source_env(&args.session_env_path, &args.claude_pid) {
        if CLARIFY_ENV_ALLOW.contains(&key.as_str()) {
            let _ = env.insert(key, value);
        }
    }
    if env.get("CLAUDE_PLUGIN_ROOT").is_none_or(String::is_empty)
        && let Some(root) = plugin_root_directory()
    {
        let _ = env.insert("CLAUDE_PLUGIN_ROOT".to_owned(), root.display().to_string());
    }
    let design_tmpdir = require_design_tmpdir(&env, None)?;
    let _ = env.insert(
        "DESIGN_TMPDIR".to_owned(),
        design_tmpdir.display().to_string(),
    );
    let _ = env.insert("ISSUE_NUMBER".to_owned(), args.issue.clone());
    Ok((env, design_tmpdir))
}

/// Recover `REPO` from the Step 0 route-state sidecar; `false` on a read miss.
fn load_route_state_repo(env: &mut Env, design_tmpdir: &Path) -> bool {
    if env.get("REPO").is_some_and(|value| !value.is_empty()) {
        return true;
    }
    let route_state = design_tmpdir.join(".design-step0-route-state.env");
    if !route_state.exists() {
        return true;
    }
    match read_result_env(&route_state, &ROUTE_STATE_ALLOW) {
        Ok(values) => {
            for (key, value) in values {
                let _ = env.insert(key, value);
            }
            true
        }
        Err(()) => false,
    }
}

/// Run the phase machine against injected effects and sibling runner.
fn design_clarify_run(
    effects: &dyn ClarifyEffects,
    runner: &dyn SiblingRunner,
    args: &DesignClarifyArgs,
    env: &mut Env,
    design_tmpdir: &Path,
) -> ExitCode {
    if !load_route_state_repo(env, design_tmpdir) {
        let route_state_log = design_tmpdir.join("clarify-route-state.failure.log");
        let _ = fs::write(&route_state_log, "could not read route state sidecar\n");
        if args.phase == "fetch" {
            return fetch_failure(
                runner,
                design_tmpdir,
                "route-state-read-failed",
                &route_state_log,
                1,
                &[],
            );
        }
        return publish_failure(
            design_tmpdir,
            "route-state-read-failed",
            "failed-clarify",
            &[],
        );
    }
    if let Err(code) = validate_design_repo(env.get("REPO").map_or("", String::as_str)) {
        return code;
    }
    if design_tmpdir.join(".pause-requested").is_file() {
        let mut pause_args = vec![
            "design".to_owned(),
            "pause-save".to_owned(),
            "--design-tmpdir".to_owned(),
            design_tmpdir.display().to_string(),
            "--issue".to_owned(),
            args.issue.clone(),
        ];
        if let Some(repo) = env.get("REPO").filter(|value| !value.is_empty()) {
            pause_args.push("--repo".to_owned());
            pause_args.push(repo.clone());
        }
        return exit_from_i32(
            runner
                .run_larch(&pause_args.iter().map(OsString::from).collect::<Vec<_>>())
                .rc,
        );
    }
    if args.phase == "fetch" {
        handle_fetch(effects, runner, args, env, design_tmpdir)
    } else {
        handle_publish(effects, runner, args, env, design_tmpdir)
    }
}

/// The `design clarify` entrypoint.
pub fn design_clarify_main(argv: &[OsString]) -> ExitCode {
    let parsed = match parse_design_clarify_args(argv) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let (mut env, design_tmpdir) = match build_driver_env(&parsed) {
        Ok(pair) => pair,
        Err(code) => return code,
    };
    let root = env
        .get("CLAUDE_PLUGIN_ROOT")
        .map(PathBuf::from)
        .or_else(plugin_root_directory)
        .unwrap_or_default();
    let cwd = std::env::current_dir().unwrap_or_else(|_error| PathBuf::from("."));
    let runner = LiveRunner::new(cwd, root);
    design_clarify_run(&LiveEffects, &runner, &parsed, &mut env, &design_tmpdir)
}

#[cfg(test)]
mod tests;
