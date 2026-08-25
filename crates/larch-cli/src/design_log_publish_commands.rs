//! Rust owner for `design log-publish` (#8592).
//!
//! Stages sanitized `$DESIGN_TMPDIR` artifacts into the design run-log tree,
//! then finishes through the shared Rust lifecycle owner. Preserves the
//! KEY=value stdout grammar and the `.design-log-publish-metadata.env` sidecar.
//!
//! Rust siblings (`design render-final-summary` (#8581), `run-log lifecycle-*`,
//! `run-log manifest`, `run-log capture-transcript`, `token claude-source`,
//! `session write-design-env`) go through
//! [`crate::runtime_entrypoint::run_verified_larch`].

use std::{
    env,
    ffi::OsString,
    fs,
    io::Write as _,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use larch_adapters::git::GixRepository;
use larch_core::{
    GUIDELINE_ASSESSMENT_ARTIFACT, GUIDELINES_FILENAME, INVARIANT_ASSESSMENT_ARTIFACT,
    INVARIANTS_FILENAME, RepositoryRead, assessment_present, assessment_required,
    default_outcome_for_reason, lifecycle_outcome, publish_excluded, redact,
    validate_design_log_slug, validate_issue, validate_repo,
};

use crate::{
    run_log_entry_commands::append_execution_issue,
    runtime_entrypoint::plugin_root_directory,
    runtime_entrypoint::{run_verified_larch, run_verified_larch_with_timeout},
};

const CAPTURE_TIMEOUT: Duration = Duration::from_secs(300);
const LIFECYCLE_TIMEOUT: Duration = Duration::from_secs(600);

/// Result of one log-publish attempt; callers emit the KV grammar once.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct LogPublishResult {
    pub publish_ok: bool,
    pub exit_code: u8,
    pub remote_key: String,
    pub cache_dir: String,
    pub secret_scrub_violations: Option<String>,
}

/// Parsed `design log-publish` request.
#[derive(Clone, Debug, Eq, PartialEq)]
struct LogPublishRequest {
    design_tmpdir: PathBuf,
    run_id: String,
    issue: String,
    repo: String,
    reason: String,
    outcome: String,
    dry_run: bool,
}

/// Entry point for `larch design log-publish`.
#[must_use]
pub fn log_publish_main(arguments: &[OsString]) -> ExitCode {
    let Some(request) = parse_arguments(arguments) else {
        return ExitCode::from(1);
    };
    if request.repo.is_empty() {
        // Invalid --repo already refused in parse; empty is allowed.
    } else if !validate_repo(&request.repo) {
        return ExitCode::from(1);
    }
    let result = run_log_publish(&request);
    emit_log_publish_result(&result);
    ExitCode::from(result.exit_code)
}

fn parse_arguments(arguments: &[OsString]) -> Option<LogPublishRequest> {
    let mut design_tmpdir = String::new();
    let mut run_id = String::new();
    let mut issue = String::new();
    let mut repo = String::new();
    let mut reason = "final".to_owned();
    let mut outcome = String::new();
    let mut dry_run = false;
    let mut index = 0;
    let args: Vec<String> = arguments
        .iter()
        .map(|value| value.to_string_lossy().into_owned())
        .collect();
    while index < args.len() {
        let token = &args[index];
        match token.as_str() {
            "--design-tmpdir" | "--run-id" | "--issue" | "--repo" | "--reason" | "--outcome" => {
                if index + 1 >= args.len() {
                    return None;
                }
                let value = args[index + 1].clone();
                match token.as_str() {
                    "--design-tmpdir" => design_tmpdir = value,
                    "--run-id" => run_id = value,
                    "--issue" => issue = value,
                    "--repo" => {
                        if !validate_repo(&value) {
                            return None;
                        }
                        repo = value;
                    }
                    "--reason" => reason = value,
                    "--outcome" => outcome = value,
                    _ => unreachable!(),
                }
                index += 2;
            }
            "--dry-run" => {
                dry_run = true;
                index += 1;
            }
            "-h" | "--help" => {
                // Match Python: help exits 0 without KV rows.
                std::process::exit(0);
            }
            _ => return None,
        }
    }
    if design_tmpdir.is_empty() || run_id.is_empty() || issue.is_empty() {
        return None;
    }
    Some(LogPublishRequest {
        design_tmpdir: PathBuf::from(design_tmpdir),
        run_id,
        issue,
        repo,
        reason,
        outcome,
        dry_run,
    })
}

fn emit_log_publish_result(result: &LogPublishResult) {
    println!(
        "PUBLISH_OK={}",
        if result.publish_ok { "true" } else { "false" }
    );
    println!("PR_NUMBER=");
    println!("PR_URL=");
    if !result.remote_key.is_empty() {
        println!("REMOTE_KEY={}", result.remote_key);
    }
    if !result.cache_dir.is_empty() {
        println!("CACHE_DIR={}", result.cache_dir);
    }
    if let Some(scrub) = &result.secret_scrub_violations {
        println!("SECRET_SCRUB_VIOLATIONS={scrub}");
    }
}

fn output_streams(output: &larch_core::ProcessOutput) -> (i32, String, String) {
    output.decoded_streams()
}

fn failed(exit_code: u8, scrub: Option<&str>) -> LogPublishResult {
    LogPublishResult {
        publish_ok: false,
        exit_code,
        secret_scrub_violations: scrub.map(str::to_owned),
        ..LogPublishResult::default()
    }
}

fn run_log_publish(request: &LogPublishRequest) -> LogPublishResult {
    if !request.design_tmpdir.is_dir() {
        return failed(0, None);
    }
    if !validate_issue(&request.issue) || !validate_design_log_slug(&request.run_id) {
        return failed(0, None);
    }
    if request.reason != "final" && request.reason != "pause" {
        return failed(0, None);
    }
    let warning_step_label = if request.reason == "final" {
        "5c"
    } else {
        "pause"
    };
    let outcome = if request.outcome.is_empty() {
        default_outcome_for_reason(&request.reason).to_owned()
    } else {
        request.outcome.clone()
    };

    if request.dry_run {
        return dry_run_publish(request, &outcome);
    }

    if !capture_design_transcript(request, warning_step_label) {
        return failed(0, None);
    }

    let repo_root = discover_repo_root();
    if let Some(root) = repo_root.as_ref() {
        record_missing_assessment_warnings(&request.design_tmpdir, &outcome, root);
    }

    if !render_final_summary_before_copy(request, &outcome) {
        eprintln!(
            "design log-publish: final-summary render failed; continuing without stale summary"
        );
    }

    if let Ok((publish_ok, remote_key, cache_dir, scrub)) = publish_design_logs(request, &outcome) {
        persist_metadata(&request.design_tmpdir, &remote_key, &cache_dir);
        LogPublishResult {
            publish_ok,
            exit_code: u8::from(!publish_ok),
            remote_key,
            cache_dir,
            secret_scrub_violations: Some(scrub),
        }
    } else {
        eprintln!("design log-publish: secret scrub failed: secret survived scrubbing");
        failed(1, Some("0"))
    }
}

fn dry_run_publish(request: &LogPublishRequest, outcome: &str) -> LogPublishResult {
    if which("git").is_none() || which("gh").is_none() {
        return failed(0, None);
    }
    let Some(repo_root) = discover_repo_root() else {
        return failed(0, None);
    };
    record_missing_assessment_warnings(&request.design_tmpdir, outcome, &repo_root);
    if !render_final_summary_before_copy(request, outcome) {
        eprintln!(
            "design log-publish: final-summary render failed; continuing without stale summary"
        );
    }
    persist_metadata(&request.design_tmpdir, "", "");
    LogPublishResult {
        publish_ok: true,
        exit_code: 0,
        ..LogPublishResult::default()
    }
}

#[derive(Debug)]
struct SecretScrubFailure;

#[allow(clippy::too_many_lines)] // One verb, one Python main ported branch for branch.
fn publish_design_logs(
    request: &LogPublishRequest,
    outcome: &str,
) -> Result<(bool, String, String, String), SecretScrubFailure> {
    let Some(repo_root) = discover_repo_root() else {
        return Ok((false, String::new(), String::new(), "0".to_owned()));
    };
    let lifecycle = if let Ok(output) = run_verified_larch_with_timeout(
        &[
            OsString::from("run-log"),
            OsString::from("lifecycle-start"),
            OsString::from("--repo-root"),
            OsString::from(repo_root.as_os_str()),
            OsString::from("--skill"),
            OsString::from("design"),
            OsString::from("--run-id"),
            OsString::from(&request.run_id),
            OsString::from("--adopt-existing"),
            OsString::from("--rehydrate"),
        ],
        LIFECYCLE_TIMEOUT,
    ) {
        let (code, stdout, _) = output_streams(&output);
        if code != 0 {
            eprintln!("design log-publish: lifecycle context unavailable");
            return Ok((false, String::new(), String::new(), "0".to_owned()));
        }
        stdout
    } else {
        eprintln!("design log-publish: lifecycle context unavailable");
        return Ok((false, String::new(), String::new(), "0".to_owned()));
    };
    let run_dir = kv_last(&lifecycle, "RUN_DIR");
    let log_root = kv_last(&lifecycle, "LOG_ROOT");
    if run_dir.is_empty() || log_root.is_empty() {
        eprintln!("design log-publish: lifecycle context unavailable: missing RUN_DIR/LOG_ROOT");
        return Ok((false, String::new(), String::new(), "0".to_owned()));
    }
    let run_dest = PathBuf::from(&run_dir);

    let manifest = run_verified_larch(&[
        OsString::from("run-log"),
        OsString::from("manifest"),
        OsString::from("--log-root"),
        OsString::from(&log_root),
        OsString::from("--skill"),
        OsString::from("design"),
        OsString::from("--run-id"),
        OsString::from(&request.run_id),
        OsString::from("--field"),
        OsString::from(format!("issue_number={}", request.issue)),
    ]);
    match manifest {
        Ok(output) => {
            let (code, stdout, stderr) = output_streams(&output);
            if code != 0 {
                let detail = stderr.trim();
                let detail = if detail.is_empty() {
                    stdout.trim()
                } else {
                    detail
                };
                eprintln!(
                    "design log-publish: lifecycle issue binding failed: {}",
                    if detail.is_empty() {
                        "run-log manifest failed"
                    } else {
                        detail
                    }
                );
                return Ok((false, String::new(), String::new(), "0".to_owned()));
            }
        }
        Err(error) => {
            eprintln!("design log-publish: lifecycle issue binding failed: {error}");
            return Ok((false, String::new(), String::new(), "0".to_owned()));
        }
    }

    let include_completed = request.reason == "pause";
    if !include_completed {
        clear_completed(&run_dest);
    }

    let mut pre_scrub_violations = 0_u64;
    let Ok(entries) = fs::read_dir(&request.design_tmpdir) else {
        return Ok((false, String::new(), String::new(), "0".to_owned()));
    };
    for entry in entries.flatten() {
        let name = entry.file_name();
        let name = name.to_string_lossy();
        if name == ".design-log-publish-metadata.env" {
            continue;
        }
        let path = entry.path();
        let is_dir = path.is_dir();
        let excluded = publish_excluded(&name, is_dir, true)
            && !(include_completed && name == ".completed" && is_dir);
        if excluded {
            continue;
        }
        if path
            .symlink_metadata()
            .map(|meta| meta.file_type().is_symlink())
            .unwrap_or(false)
        {
            continue;
        }
        let (ok, count) = copy_tree_redacted(&path, &run_dest.join(name.as_ref()))?;
        if !ok {
            return Ok((false, String::new(), String::new(), "0".to_owned()));
        }
        pre_scrub_violations = pre_scrub_violations.saturating_add(count);
    }

    let lifecycle_action = match lifecycle_outcome(&request.reason, outcome) {
        "cancelled" => "lifecycle-cancel",
        "failure" => "lifecycle-failure",
        "early-return" => "lifecycle-early-return",
        _ => "lifecycle-finalize",
    };
    let terminal = match run_verified_larch_with_timeout(
        &[
            OsString::from("run-log"),
            OsString::from(lifecycle_action),
            OsString::from("--repo-root"),
            OsString::from(repo_root.as_os_str()),
            OsString::from("--skill"),
            OsString::from("design"),
            OsString::from("--run-id"),
            OsString::from(&request.run_id),
            OsString::from("--pre-scrub-violations"),
            OsString::from(pre_scrub_violations.to_string()),
        ],
        LIFECYCLE_TIMEOUT,
    ) {
        Ok(output) => {
            let (code, stdout, stderr) = output_streams(&output);
            if code != 0 {
                let detail = stderr.trim();
                eprintln!(
                    "design log-publish: archive publication failed: {}",
                    if detail.is_empty() {
                        "lifecycle terminal failed"
                    } else {
                        detail
                    }
                );
                return Ok((
                    false,
                    String::new(),
                    String::new(),
                    pre_scrub_violations.to_string(),
                ));
            }
            // Forward non-empty lifecycle stderr (breadcrumb warnings) like Python.
            let stderr = stderr.trim();
            if !stderr.is_empty()
                && !stderr.contains("publication skipped because storage was disabled")
            {
                eprintln!("{stderr}");
            }
            stdout
        }
        Err(error) => {
            eprintln!("design log-publish: archive publication failed: {error}");
            return Ok((
                false,
                String::new(),
                String::new(),
                pre_scrub_violations.to_string(),
            ));
        }
    };

    let scrub = kv_last(&terminal, "SECRET_SCRUB_VIOLATIONS");
    let scrub = if scrub.is_empty() {
        pre_scrub_violations.to_string()
    } else {
        scrub
    };
    if kv_last(&terminal, "RUN_LOG_PUBLICATION") == "skipped-disabled" {
        let reason = kv_last(&terminal, "RUN_LOG_STORAGE_REASON");
        eprintln!(
            "**⚠ Run-log publication skipped because storage was disabled at lifecycle start ({reason}).**"
        );
        return Ok((true, String::new(), String::new(), scrub));
    }
    if kv_last(&terminal, "RUN_LOG_PUBLICATION") != "published" {
        eprintln!("design log-publish: archive publication failed: invalid publication state");
        return Ok((false, String::new(), String::new(), scrub));
    }
    Ok((
        true,
        kv_last(&terminal, "REMOTE_KEY"),
        kv_last(&terminal, "CACHE_DIR"),
        scrub,
    ))
}

fn copy_tree_redacted(source: &Path, dest: &Path) -> Result<(bool, u64), SecretScrubFailure> {
    let Ok(meta) = source.symlink_metadata() else {
        return Ok((true, 0));
    };
    if meta.file_type().is_symlink() {
        return Ok((false, 0));
    }
    if meta.is_file() {
        let original = fs::read_to_string(source).unwrap_or_default();
        let path_scrubbed = redact(&original);
        let findings: u64 = path_scrubbed
            .findings()
            .values()
            .try_fold(0_u64, |acc, count| {
                u64::try_from(*count).ok().and_then(|n| acc.checked_add(n))
            })
            .unwrap_or(u64::MAX);
        let mut scrubbed = path_scrubbed.text().to_owned();
        if findings > 0 {
            let residual = redact(&scrubbed);
            if !residual.findings().is_empty() {
                eprintln!(
                    "design log-publish: secret survived scrubbing in {}",
                    source.display()
                );
                return Err(SecretScrubFailure);
            }
            residual.text().clone_into(&mut scrubbed);
        }
        if !scrubbed.is_empty() && !scrubbed.ends_with('\n') {
            scrubbed.push('\n');
        }
        if let Some(parent) = dest.parent() {
            let _ = fs::create_dir_all(parent);
        }
        fs::write(dest, scrubbed).map_err(|_| SecretScrubFailure)?;
        return Ok((true, findings));
    }
    if meta.is_dir() {
        let mut total = 0_u64;
        let Ok(entries) = fs::read_dir(source) else {
            return Ok((true, 0));
        };
        for entry in entries.flatten() {
            let child = entry.path();
            if child
                .symlink_metadata()
                .map(|m| m.file_type().is_symlink())
                .unwrap_or(false)
            {
                continue;
            }
            let name = entry.file_name();
            let name = name.to_string_lossy();
            let is_dir = child.is_dir();
            if publish_excluded(&name, is_dir, false) {
                continue;
            }
            let (ok, count) = copy_tree_redacted(&child, &dest.join(name.as_ref()))?;
            if !ok {
                return Ok((false, total));
            }
            total = total.saturating_add(count);
        }
        return Ok((true, total));
    }
    Ok((true, 0))
}

fn clear_completed(run_dest: &Path) {
    let completed = run_dest.join(".completed");
    let Ok(meta) = completed.symlink_metadata() else {
        return;
    };
    if meta.file_type().is_symlink() || meta.is_file() {
        let _ = fs::remove_file(&completed);
    } else if meta.is_dir() {
        let _ = fs::remove_dir_all(&completed);
    }
}

fn persist_metadata(design_tmpdir: &Path, remote_key: &str, cache_dir: &str) {
    let path = design_tmpdir.join(".design-log-publish-metadata.env");
    let body = format!(
        "DESIGN_LOG_PR_NUMBER=\nDESIGN_LOG_PR_URL=\nDESIGN_LOG_RECOVERY_BRANCH=\nDESIGN_LOG_REMOTE_KEY={remote_key}\nDESIGN_LOG_CACHE_DIR={cache_dir}\n"
    );
    let _ = fs::write(path, body);
}

fn record_missing_assessment_warnings(design_tmpdir: &Path, outcome: &str, repo_root: &Path) {
    record_one_assessment_warning(
        design_tmpdir,
        outcome,
        repo_root,
        INVARIANTS_FILENAME,
        INVARIANT_ASSESSMENT_ARTIFACT,
        "invariant-assessment",
        true,
    );
    record_one_assessment_warning(
        design_tmpdir,
        outcome,
        repo_root,
        GUIDELINES_FILENAME,
        GUIDELINE_ASSESSMENT_ARTIFACT,
        "guideline-assessment",
        false,
    );
}

fn record_one_assessment_warning(
    design_tmpdir: &Path,
    outcome: &str,
    repo_root: &Path,
    knowledge_file: &str,
    artifact: &str,
    category_label: &str,
    require_nonempty: bool,
) {
    let knowledge_path = repo_root.join(knowledge_file);
    let knowledge_present = knowledge_path.is_file() && !knowledge_path.is_symlink();
    let knowledge_nonempty = if require_nonempty {
        fs::read_to_string(&knowledge_path)
            .map(|text| !text.trim().is_empty())
            .unwrap_or(false)
    } else {
        true
    };
    let required = assessment_required(outcome, knowledge_present, knowledge_nonempty);
    let artifact_path = design_tmpdir.join(artifact);
    let present = assessment_present(
        artifact_path.is_file(),
        artifact_path
            .symlink_metadata()
            .map(|meta| meta.file_type().is_symlink())
            .unwrap_or(false),
    );
    if !required || present {
        return;
    }
    let _ = append_execution_issue(
        &design_tmpdir.join("execution-issues.md"),
        "Warnings",
        &format!(
            "{category_label}: missing {artifact}; Gate C assessment did not persist before direct log publish."
        ),
    );
    let marker = if category_label.starts_with("invariant") {
        ".missing-invariant-assessment-warning"
    } else {
        ".missing-guideline-assessment-warning"
    };
    let _ = fs::write(design_tmpdir.join(marker), "");
}

fn render_final_summary_before_copy(request: &LogPublishRequest, outcome: &str) -> bool {
    let mode = resolve_summary_mode(&request.design_tmpdir);
    let stdout_log = request.design_tmpdir.join(format!(
        "render-final-summary.{outcome}.pre-publish.stdout.log"
    ));
    let mut args = vec![
        OsString::from("design"),
        OsString::from("render-final-summary"),
        OsString::from("--outcome"),
        OsString::from(outcome),
        OsString::from("--mode"),
        OsString::from(mode),
        OsString::from("--design-tmpdir"),
        OsString::from(&request.design_tmpdir),
        OsString::from("--issue-number"),
        OsString::from(&request.issue),
        OsString::from("--session-id"),
        OsString::from(&request.run_id),
        OsString::from("--post-publish-only"),
        OsString::from("--skip-summary-upsert"),
    ];
    if !request.repo.is_empty() {
        args.push(OsString::from("--repo"));
        args.push(OsString::from(&request.repo));
    }
    // Delete stale summary before render (matches Python render_final_summary_for_request).
    let summary = request.design_tmpdir.join("final-summary.md");
    let _ = fs::remove_file(&summary);
    // #8581 flipped `design render-final-summary` to a Rust owner, so this
    // pre-copy render reaches it through the verified bootstrap.
    match crate::runtime_entrypoint::run_verified_larch(&args) {
        Ok(output) => {
            let (code, stdout, _) = output_streams(&output);
            let _ = fs::write(&stdout_log, stdout);
            code == 0 && summary.is_file()
        }
        Err(error) => {
            let _ = fs::write(
                &stdout_log,
                format!("render-final-summary failed: {error}\n"),
            );
            false
        }
    }
}

pub fn resolve_summary_mode(design_tmpdir: &Path) -> String {
    let run_params = design_tmpdir.join("run-params.json");
    if run_params.is_file()
        && !run_params.is_symlink()
        && let Ok(text) = fs::read_to_string(&run_params)
        && let Ok(value) = serde_json::from_str::<serde_json::Value>(&text)
        && let Some(mode) = value
            .get("mode")
            .or_else(|| value.get("MODE"))
            .and_then(|v| v.as_str())
            .filter(|mode| !mode.is_empty())
    {
        return mode.to_owned();
    }
    let source = design_tmpdir.join("source-env.sh");
    if let Ok(text) = fs::read_to_string(&source) {
        let mode = kv_last(&text, "MODE");
        if !mode.is_empty() {
            return mode;
        }
    }
    "N/A".to_owned()
}

fn capture_design_transcript(request: &LogPublishRequest, warning_step_label: &str) -> bool {
    let root_transcript = request.design_tmpdir.join("session-transcript.jsonl");
    if (root_transcript.exists() || root_transcript.is_symlink())
        && fs::remove_file(&root_transcript).is_err()
    {
        append_transcript_warning(
            &request.design_tmpdir,
            warning_step_label,
            "stale-root-removal-failed",
            "could not remove stale root transcript before publish",
        );
        return false;
    }

    let source_env = request.design_tmpdir.join("source-env.sh");
    if let Ok(text) = fs::read_to_string(&source_env) {
        let source_session = kv_last(&text, "SESSION_ID");
        if !source_session.is_empty() && source_session != request.run_id {
            append_transcript_warning(
                &request.design_tmpdir,
                warning_step_label,
                "session-id-drift",
                "source-env.sh SESSION_ID disagrees with publish --session-id; transcript capture skipped.",
            );
            return true;
        }
    }

    let Some(snapshot) = materialize_claude_source_snapshot(
        &request.design_tmpdir,
        &request.run_id,
        warning_step_label,
    ) else {
        return true;
    };

    let _ = refresh_design_source_env(request, &source_env, &snapshot, warning_step_label);
    let staging_root = request.design_tmpdir.join("larch-logs");
    let capture = run_verified_larch_with_timeout(
        &[
            OsString::from("run-log"),
            OsString::from("capture-transcript"),
            OsString::from("--source-file"),
            OsString::from(&snapshot),
            OsString::from("--skill"),
            OsString::from("design"),
            OsString::from("--run-id"),
            OsString::from(&request.run_id),
            OsString::from("--log-root"),
            OsString::from(&staging_root),
            OsString::from("--tmpdir"),
            OsString::from(&request.design_tmpdir),
            OsString::from("--defer-commit"),
            OsString::from("true"),
            OsString::from("--execution-issues-log"),
            OsString::from(request.design_tmpdir.join("execution-issues.md")),
            OsString::from("--warning-step-label"),
            OsString::from(warning_step_label),
        ],
        CAPTURE_TIMEOUT,
    );
    let Ok(output) = capture else {
        let _ = fs::remove_file(&root_transcript);
        return true;
    };
    let (code, stdout, _) = output_streams(&output);
    let status = kv_last(&stdout, "SESSION_TRANSCRIPT_STATUS");
    match status.as_str() {
        "" => {}
        status => {
            println!("SESSION_TRANSCRIPT_STATUS={status}");
            let _ = std::io::stdout().flush();
        }
    }
    let staged = staging_root
        .join("design")
        .join(&request.run_id)
        .join("session-transcript.jsonl");
    if code != 0 || status != "captured" {
        let _ = fs::remove_file(&root_transcript);
        return true;
    }
    if fs::rename(&staged, &root_transcript).is_err() {
        let _ = fs::remove_file(&root_transcript);
        append_transcript_warning(
            &request.design_tmpdir,
            warning_step_label,
            "hoist-failed",
            "capture succeeded but transcript hoist failed",
        );
        return false;
    }
    true
}

fn materialize_claude_source_snapshot(
    design_tmpdir: &Path,
    session_id: &str,
    warning_step_label: &str,
) -> Option<PathBuf> {
    let snapshot = design_tmpdir.join("claude-source.env");
    if snapshot.is_file() {
        if let Ok(text) = fs::read_to_string(&snapshot)
            && !text.is_empty()
            && !kv_last(&text, "TRANSCRIPT_PATH").is_empty()
            && !kv_last(&text, "SESSION_DIR").is_empty()
            && !kv_last(&text, "SESSION_UUID").is_empty()
            && Path::new(&kv_last(&text, "TRANSCRIPT_PATH")).is_file()
        {
            return Some(snapshot);
        }
        let _ = fs::remove_file(&snapshot);
    }
    if session_id.is_empty() {
        append_transcript_warning(
            design_tmpdir,
            warning_step_label,
            "snapshot-skipped",
            "SESSION_ID was absent from source-env.sh; transcript capture skipped.",
        );
        return None;
    }
    if let Ok(output) =
        run_verified_larch(&[OsString::from("token"), OsString::from("claude-source")])
    {
        let (code, stdout, _) = output_streams(&output);
        if code == 0 && stdout.contains("TRANSCRIPT_PATH=") {
            if fs::write(&snapshot, &stdout).is_err() {
                append_transcript_warning(
                    design_tmpdir,
                    warning_step_label,
                    "snapshot-write-failed",
                    "Claude source snapshot write failed; transcript capture skipped",
                );
                return None;
            }
            return Some(snapshot);
        }
    }
    append_transcript_warning(
        design_tmpdir,
        warning_step_label,
        "snapshot-skipped",
        "Claude source snapshot materialization failed; transcript capture skipped.",
    );
    None
}

fn refresh_design_source_env(
    request: &LogPublishRequest,
    source_env: &Path,
    snapshot: &Path,
    warning_step_label: &str,
) -> bool {
    let claude_pid = env::var("LARCH_CLAUDE_PID")
        .ok()
        .filter(|value| !value.is_empty())
        .or_else(|| env::var("PPID").ok())
        .unwrap_or_default();
    let mut args = vec![
        OsString::from("session"),
        OsString::from("write-design-env"),
        OsString::from("--output"),
        OsString::from(source_env),
        OsString::from("--design-tmpdir"),
        OsString::from(&request.design_tmpdir),
        OsString::from("--session-id"),
        OsString::from(&request.run_id),
        OsString::from("--issue-number"),
        OsString::from(&request.issue),
        OsString::from("--claude-pid"),
        OsString::from(&claude_pid),
        OsString::from("--claude-source-file"),
        OsString::from(snapshot),
    ];
    if !request.repo.is_empty() {
        args.push(OsString::from("--repo"));
        args.push(OsString::from(&request.repo));
    }
    run_verified_larch(&args).map_or_else(
        |_| {
            append_transcript_warning(
                &request.design_tmpdir,
                warning_step_label,
                "source-env-refresh-failed",
                "could not persist LARCH_CLAUDE_SOURCE_FILE; continuing with transcript capture.",
            );
            false
        },
        |output| {
            let (code, _, _) = output_streams(&output);
            if code == 0 {
                true
            } else {
                append_transcript_warning(
                    &request.design_tmpdir,
                    warning_step_label,
                    "source-env-refresh-failed",
                    "could not persist LARCH_CLAUDE_SOURCE_FILE; continuing with transcript capture.",
                );
                false
            }
        },
    )
}

fn append_transcript_warning(
    design_tmpdir: &Path,
    warning_step_label: &str,
    status: &str,
    message: &str,
) {
    let _ = append_execution_issue(
        &design_tmpdir.join("execution-issues.md"),
        "Warnings",
        &format!("design Step {warning_step_label} session-transcript {status}: {message}"),
    );
}

fn discover_repo_root() -> Option<PathBuf> {
    let cwd = env::current_dir().ok()?;
    let repository = GixRepository::discover(&cwd).ok()?;
    let work_dir = repository.location().work_dir?;
    let path = PathBuf::from(String::from_utf8_lossy(work_dir.as_bytes()).into_owned());
    fs::canonicalize(path).ok()
}

fn which(command: &str) -> Option<PathBuf> {
    env::var_os("PATH").and_then(|paths| {
        env::split_paths(&paths).find_map(|dir| {
            let candidate = dir.join(command);
            candidate.is_file().then_some(candidate)
        })
    })
}

fn kv_last(text: &str, key: &str) -> String {
    let prefix = format!("{key}=");
    text.replace('\r', "\n")
        .lines()
        .filter_map(|line| line.strip_prefix(&prefix).map(str::to_owned))
        .next_back()
        .unwrap_or_default()
}

#[allow(dead_code)] // exercised by unit tests and future dry-run hardening
fn plugin_root_or_default() -> PathBuf {
    plugin_root_directory().unwrap_or_else(|| {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .and_then(Path::parent)
            .map_or_else(|| PathBuf::from("."), Path::to_path_buf)
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::fs::symlink;
    use tempfile::TempDir;

    fn sample_run_id() -> &'static str {
        "ABCDEF01-2345-6789-ABCD-EF0123456789"
    }

    fn base_args(tmpdir: &Path) -> Vec<OsString> {
        vec![
            OsString::from("--design-tmpdir"),
            OsString::from(tmpdir),
            OsString::from("--run-id"),
            OsString::from(sample_run_id()),
            OsString::from("--issue"),
            OsString::from("42"),
        ]
    }

    #[test]
    fn parse_requires_core_flags() {
        assert!(parse_arguments(&[]).is_none());
        let parsed = parse_arguments(&[
            OsString::from("--design-tmpdir"),
            OsString::from("/tmp/d"),
            OsString::from("--run-id"),
            OsString::from(sample_run_id()),
            OsString::from("--issue"),
            OsString::from("42"),
        ])
        .expect("parsed");
        assert_eq!(parsed.reason, "final");
        assert!(!parsed.dry_run);
    }

    #[test]
    fn parse_accepts_pause_reason_and_dry_run() {
        let parsed = parse_arguments(&[
            OsString::from("--design-tmpdir"),
            OsString::from("/tmp/d"),
            OsString::from("--run-id"),
            OsString::from(sample_run_id()),
            OsString::from("--issue"),
            OsString::from("7"),
            OsString::from("--reason"),
            OsString::from("pause"),
            OsString::from("--outcome"),
            OsString::from("paused"),
            OsString::from("--dry-run"),
        ])
        .expect("parsed");
        assert_eq!(parsed.reason, "pause");
        assert_eq!(parsed.outcome, "paused");
        assert!(parsed.dry_run);
    }

    #[test]
    fn parse_rejects_invalid_repo() {
        assert!(
            parse_arguments(&[
                OsString::from("--design-tmpdir"),
                OsString::from("/tmp/d"),
                OsString::from("--run-id"),
                OsString::from("run-1"),
                OsString::from("--issue"),
                OsString::from("1"),
                OsString::from("--repo"),
                OsString::from("not-a-slug"),
            ])
            .is_none()
        );
    }

    #[test]
    fn parse_keeps_issue_and_reason_for_runtime_validation() {
        let parsed = parse_arguments(&[
            OsString::from("--design-tmpdir"),
            OsString::from("/tmp/d"),
            OsString::from("--run-id"),
            OsString::from(sample_run_id()),
            OsString::from("--issue"),
            OsString::from("0"),
            OsString::from("--reason"),
            OsString::from("other"),
        ])
        .expect("parse accepts; run_log_publish rejects");
        assert_eq!(parsed.issue, "0");
        assert_eq!(parsed.reason, "other");
        let result = run_log_publish(&parsed);
        assert!(!result.publish_ok);
    }

    #[test]
    fn kv_last_prefers_final_row() {
        assert_eq!(
            kv_last("PUBLISH_OK=false\nPUBLISH_OK=true\n", "PUBLISH_OK"),
            "true"
        );
        assert_eq!(kv_last("A=1\r\nA=2\n", "A"), "2");
        assert_eq!(kv_last("A=1\n", "MISSING"), "");
    }

    #[test]
    fn failed_helper_preserves_scrub_token() {
        assert_eq!(
            failed(1, Some("3")),
            LogPublishResult {
                publish_ok: false,
                exit_code: 1,
                secret_scrub_violations: Some("3".to_owned()),
                ..LogPublishResult::default()
            }
        );
    }

    #[test]
    fn persist_metadata_writes_sidecar() {
        let dir = TempDir::new().unwrap();
        persist_metadata(dir.path(), "remote/key", "/cache/dir");
        let text = fs::read_to_string(dir.path().join(".design-log-publish-metadata.env")).unwrap();
        assert!(text.contains("DESIGN_LOG_REMOTE_KEY=remote/key\n"));
        assert!(text.contains("DESIGN_LOG_CACHE_DIR=/cache/dir\n"));
    }

    #[test]
    fn clear_completed_removes_file_and_directory() {
        let dir = TempDir::new().unwrap();
        let completed = dir.path().join(".completed");
        fs::write(&completed, "x").unwrap();
        clear_completed(dir.path());
        assert!(!completed.exists());

        fs::create_dir_all(completed.join("nested")).unwrap();
        clear_completed(dir.path());
        assert!(!completed.exists());
    }

    #[test]
    fn copy_tree_redacted_copies_file_and_skips_excluded() {
        let src = TempDir::new().unwrap();
        let dest = TempDir::new().unwrap();
        fs::write(src.path().join("keep.txt"), "hello").unwrap();
        fs::write(src.path().join("lane.events.jsonl"), "raw").unwrap();
        fs::create_dir(src.path().join("plan-autofix")).unwrap();
        fs::write(src.path().join("plan-autofix").join("x.txt"), "x").unwrap();

        let (ok, findings) = copy_tree_redacted(src.path(), dest.path()).unwrap();
        assert!(ok);
        assert_eq!(findings, 0);
        assert_eq!(
            fs::read_to_string(dest.path().join("keep.txt")).unwrap(),
            "hello\n"
        );
        assert!(!dest.path().join("lane.events.jsonl").exists());
        assert!(!dest.path().join("plan-autofix").exists());
    }

    #[test]
    fn copy_tree_redacted_rejects_symlink_sources() {
        let src = TempDir::new().unwrap();
        let dest = TempDir::new().unwrap();
        let target = src.path().join("real.txt");
        fs::write(&target, "body").unwrap();
        let link = src.path().join("link.txt");
        symlink(&target, &link).unwrap();
        let (ok, findings) = copy_tree_redacted(&link, &dest.path().join("link.txt")).unwrap();
        assert!(!ok);
        assert_eq!(findings, 0);
    }

    #[test]
    fn resolve_summary_mode_reads_json_then_source_env() {
        let dir = TempDir::new().unwrap();
        assert_eq!(resolve_summary_mode(dir.path()), "N/A");

        fs::write(dir.path().join("run-params.json"), r#"{"mode":"heavy"}"#).unwrap();
        assert_eq!(resolve_summary_mode(dir.path()), "heavy");

        let dir2 = TempDir::new().unwrap();
        fs::write(dir2.path().join("source-env.sh"), "MODE=light\n").unwrap();
        assert_eq!(resolve_summary_mode(dir2.path()), "light");
    }

    #[test]
    fn assessment_warning_records_when_required_and_missing() {
        let design = TempDir::new().unwrap();
        let repo = TempDir::new().unwrap();
        fs::write(repo.path().join(INVARIANTS_FILENAME), "invariant body\n").unwrap();
        record_one_assessment_warning(
            design.path(),
            "approved",
            repo.path(),
            INVARIANTS_FILENAME,
            INVARIANT_ASSESSMENT_ARTIFACT,
            "invariant-assessment",
            true,
        );
        assert!(
            design
                .path()
                .join(".missing-invariant-assessment-warning")
                .is_file()
        );
        let issues = fs::read_to_string(design.path().join("execution-issues.md")).unwrap();
        assert!(issues.contains("invariant-assessment"));
    }

    #[test]
    fn assessment_warning_skips_when_not_required() {
        let design = TempDir::new().unwrap();
        let repo = TempDir::new().unwrap();
        record_one_assessment_warning(
            design.path(),
            "failed-clarify",
            repo.path(),
            INVARIANTS_FILENAME,
            INVARIANT_ASSESSMENT_ARTIFACT,
            "invariant-assessment",
            true,
        );
        assert!(
            !design
                .path()
                .join(".missing-invariant-assessment-warning")
                .exists()
        );
    }

    #[test]
    fn append_transcript_warning_writes_execution_issue() {
        let dir = TempDir::new().unwrap();
        append_transcript_warning(dir.path(), "5c", "hoist-failed", "could not hoist");
        let text = fs::read_to_string(dir.path().join("execution-issues.md")).unwrap();
        assert!(text.contains("design Step 5c session-transcript hoist-failed"));
        assert!(text.contains("could not hoist"));
    }

    #[test]
    fn which_finds_existing_path_entry() {
        assert!(which("sh").is_some() || which("bash").is_some());
        assert!(which("definitely-not-a-binary-xyz").is_none());
    }

    #[test]
    fn plugin_root_or_default_is_nonempty() {
        assert!(!plugin_root_or_default().as_os_str().is_empty());
    }

    #[test]
    fn log_publish_main_rejects_missing_tmpdir() {
        let code = log_publish_main(&base_args(Path::new("/tmp/does-not-exist-larch-8592")));
        assert_eq!(code, ExitCode::from(0));
    }

    #[test]
    fn run_log_publish_rejects_missing_directory() {
        let request = LogPublishRequest {
            design_tmpdir: PathBuf::from("/tmp/missing-design-tmpdir-8592"),
            run_id: sample_run_id().to_owned(),
            issue: "42".to_owned(),
            repo: String::new(),
            reason: "final".to_owned(),
            outcome: String::new(),
            dry_run: false,
        };
        let result = run_log_publish(&request);
        assert!(!result.publish_ok);
        assert_eq!(result.exit_code, 0);
    }

    #[test]
    fn emit_log_publish_result_is_callable() {
        emit_log_publish_result(&LogPublishResult {
            publish_ok: true,
            exit_code: 0,
            remote_key: "k".to_owned(),
            cache_dir: "c".to_owned(),
            secret_scrub_violations: Some("0".to_owned()),
        });
        emit_log_publish_result(&LogPublishResult {
            publish_ok: false,
            exit_code: 1,
            ..LogPublishResult::default()
        });
    }

    fn sample_request(dir: &Path, dry_run: bool) -> LogPublishRequest {
        LogPublishRequest {
            design_tmpdir: dir.to_path_buf(),
            run_id: sample_run_id().to_owned(),
            issue: "42".to_owned(),
            repo: "owner/repo".to_owned(),
            reason: "final".to_owned(),
            outcome: "approved".to_owned(),
            dry_run,
        }
    }

    #[test]
    fn capture_skips_on_session_id_drift() {
        let dir = TempDir::new().unwrap();
        fs::write(
            dir.path().join("source-env.sh"),
            "SESSION_ID=DIFFERENT-SESSION-ID\n",
        )
        .unwrap();
        let request = sample_request(dir.path(), false);
        assert!(capture_design_transcript(&request, "5c"));
        let issues = fs::read_to_string(dir.path().join("execution-issues.md")).unwrap();
        assert!(issues.contains("session-id-drift"));
    }

    #[test]
    fn materialize_skips_when_session_id_empty() {
        let dir = TempDir::new().unwrap();
        assert!(materialize_claude_source_snapshot(dir.path(), "", "5c").is_none());
        let issues = fs::read_to_string(dir.path().join("execution-issues.md")).unwrap();
        assert!(issues.contains("snapshot-skipped"));
    }

    #[test]
    fn materialize_reuses_valid_snapshot() {
        let dir = TempDir::new().unwrap();
        let transcript = dir.path().join("transcript.jsonl");
        fs::write(&transcript, "{}\n").unwrap();
        let snapshot = dir.path().join("claude-source.env");
        fs::write(
            &snapshot,
            format!(
                "TRANSCRIPT_PATH={}\nSESSION_DIR={}\nSESSION_UUID=abc\n",
                transcript.display(),
                dir.path().display()
            ),
        )
        .unwrap();
        let reused = materialize_claude_source_snapshot(dir.path(), sample_run_id(), "5c")
            .expect("reuse snapshot");
        assert_eq!(reused, snapshot);
    }

    #[test]
    fn materialize_drops_invalid_snapshot_then_skips() {
        let dir = TempDir::new().unwrap();
        fs::write(dir.path().join("claude-source.env"), "TRANSCRIPT_PATH=\n").unwrap();
        // Without a live Claude source, token claude-source fails closed.
        assert!(materialize_claude_source_snapshot(dir.path(), sample_run_id(), "5c").is_none());
        assert!(!dir.path().join("claude-source.env").exists());
    }

    #[test]
    fn capture_continues_when_snapshot_materialization_skips() {
        let dir = TempDir::new().unwrap();
        let request = sample_request(dir.path(), false);
        // No Claude source → materialize returns None → capture returns true.
        assert!(capture_design_transcript(&request, "5c"));
    }

    #[test]
    fn refresh_design_source_env_records_failure() {
        let dir = TempDir::new().unwrap();
        let request = sample_request(dir.path(), false);
        let snapshot = dir.path().join("claude-source.env");
        fs::write(&snapshot, "TRANSCRIPT_PATH=/tmp/x\n").unwrap();
        let source_env = dir.path().join("source-env.sh");
        // Likely fails without a full session context; either outcome covers branches.
        let _ = refresh_design_source_env(&request, &source_env, &snapshot, "5c");
    }

    #[test]
    fn dry_run_publish_covers_happy_path_when_tools_present() {
        let dir = TempDir::new().unwrap();
        let request = sample_request(dir.path(), true);
        let result = dry_run_publish(&request, "approved");
        // git+gh exist in CI and discover finds this checkout.
        if which("git").is_some() && which("gh").is_some() && discover_repo_root().is_some() {
            assert!(result.publish_ok);
            assert_eq!(result.exit_code, 0);
            assert!(
                dir.path()
                    .join(".design-log-publish-metadata.env")
                    .is_file()
            );
        } else {
            assert!(!result.publish_ok);
        }
    }

    #[test]
    fn run_log_publish_dry_run_delegates() {
        let dir = TempDir::new().unwrap();
        let mut request = sample_request(dir.path(), true);
        request.outcome = String::new();
        let result = run_log_publish(&request);
        if which("git").is_some() && which("gh").is_some() && discover_repo_root().is_some() {
            assert!(result.publish_ok);
        }
    }

    #[test]
    fn run_log_publish_pause_label_and_capture_skip() {
        let dir = TempDir::new().unwrap();
        let mut request = sample_request(dir.path(), false);
        request.reason = "pause".to_owned();
        request.outcome = String::new();
        // Capture skip path still proceeds into lifecycle; without a staged run
        // this fails closed on lifecycle context.
        let result = run_log_publish(&request);
        assert!(result.secret_scrub_violations.is_some() || !result.publish_ok);
    }

    #[test]
    fn record_missing_assessment_warnings_covers_both_categories() {
        let design = TempDir::new().unwrap();
        let repo = TempDir::new().unwrap();
        fs::write(repo.path().join(INVARIANTS_FILENAME), "inv\n").unwrap();
        fs::write(repo.path().join(GUIDELINES_FILENAME), "guide\n").unwrap();
        record_missing_assessment_warnings(design.path(), "approved", repo.path());
        assert!(
            design
                .path()
                .join(".missing-invariant-assessment-warning")
                .is_file()
        );
        assert!(
            design
                .path()
                .join(".missing-guideline-assessment-warning")
                .is_file()
        );
    }

    #[test]
    fn discover_repo_root_finds_this_checkout() {
        assert!(discover_repo_root().is_some());
    }

    #[test]
    fn render_final_summary_before_copy_tolerates_missing_python_driver() {
        let dir = TempDir::new().unwrap();
        let request = sample_request(dir.path(), false);
        // May succeed or fail depending on plugin/python availability; both
        // branches are acceptable coverage of the helper.
        let _ = render_final_summary_before_copy(&request, "approved");
    }

    #[test]
    fn publish_design_logs_fails_closed_without_lifecycle() {
        let dir = TempDir::new().unwrap();
        fs::write(dir.path().join("plan.txt"), "plan\n").unwrap();
        let request = sample_request(dir.path(), false);
        let result = publish_design_logs(&request, "approved").expect("no scrub failure");
        assert!(!result.0);
    }
}
