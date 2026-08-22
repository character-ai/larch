//! Rust-owned continuation of `/implement` Step 0 bootstrap.
//!
//! The public `bootstrap invoke` command creates or restores the session in
//! `bootstrap_commands`; this module completes the same command's tracking,
//! plan, coder-selection, resume, and routing contract.  Keeping this private
//! implementation boundary avoids a second public command or an owner bridge.

use crate::{
    agent_commands,
    bootstrap_commands::{BootstrapOptions, BootstrapState, ROUTING_KEYS, write_base_session_env},
    bootstrap_support::{first_kv_value, remove_session_file, valid_run_id, write_session_text},
    dirty_tree_commands, github_repository_resolution,
    launcher_support::{
        confine_regular_read_checked, read_confined_bytes_checked as read_confined_bytes,
    },
    push_network,
    runtime_entrypoint::run_verified_larch,
    tracking_issue_commands::post_issue_in_process,
};
use larch_adapters::{
    CheckoutRequest, FetchRequest, GitCli, GitCliPolicy, GitRef, GitRefspec, GitRemote,
    GixRepository, TemporaryRoot, TokioProcessRunner,
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    CodexGateMessage, CrStrip, DegradedToolsResult, DuplicatePolicy, KvDocument, ParseOptions,
    ProcessOutput, RepositoryRead, Revision, compose_plan_goals_test, redact, role_default,
    single_line as core_single_line,
};
use sha2::{Digest as _, Sha256};
use std::{
    collections::BTreeMap,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

const CONTRACT_FAILURE: u8 = 2;
const RECEIPT_SCOPE_DRIFT_MAX_BYTES: usize = 64 * 1024;
const RECEIPT_SCOPE_DRIFT_MAX_ROWS: usize = 128;

/// Complete the public bootstrap command after its session infrastructure is ready.
pub fn run(mut state: BootstrapState, options: &BootstrapOptions) -> ExitCode {
    normalize_state_defaults(&mut state);
    let result = run_after_infrastructure(&mut state, options);
    let mut values = match result {
        Ok(()) => final_values(&state, options),
        Err(failure) => return emit_failure(&failure, &state.implement_tmpdir),
    };
    let tmpdir = values.get("IMPLEMENT_TMPDIR").cloned().unwrap_or_default();
    if tmpdir.is_empty() {
        eprintln!("bootstrap invoke: bootstrap success missing IMPLEMENT_TMPDIR");
        return ExitCode::from(1);
    }

    let routing_file = Path::new(&tmpdir).join("bootstrap-routing.env");
    if options.resume() {
        preserve_resume_routing(&mut values, &routing_file);
        restore_resume_coder(&mut values, &routing_file, Path::new(&tmpdir));
    }
    let continue_tail_attempted = continue_predicate(&values);
    let tail = match run_absorbed_continue_tail(&values, options) {
        Ok(tail) => tail,
        Err(failure) => return emit_failure(&failure, &tmpdir),
    };
    for (key, value) in tail.routing {
        if !value.is_empty() {
            values.insert(key, value);
        }
    }
    values.insert(
        "BOOTSTRAP_NEXT".to_owned(),
        bootstrap_next(&values, continue_tail_attempted).to_owned(),
    );
    let envelope = envelope_text(&values);

    if let Err(error) = merge_ship_seed_input(&tmpdir, options, &values) {
        eprintln!("bootstrap invoke: could not write ship-seed-input.env ({error})");
        if !options.resume() {
            return ExitCode::from(CONTRACT_FAILURE);
        }
    }

    if routing_file.is_symlink() {
        eprintln!(
            "bootstrap invoke: refusing to overwrite symlinked bootstrap-routing.env (stdout envelope emitted)"
        );
        emit_envelope(&envelope, &tail.advisory_lines);
        return ExitCode::SUCCESS;
    }
    if routing_file.exists() && !routing_file.is_file() {
        eprintln!(
            "bootstrap invoke: refusing to overwrite non-regular bootstrap-routing.env (stdout envelope emitted)"
        );
        emit_envelope(&envelope, &tail.advisory_lines);
        return ExitCode::SUCCESS;
    }
    if let Err(error) = write_session_file(&tmpdir, "bootstrap-routing.env", &envelope) {
        eprintln!(
            "bootstrap invoke: could not write bootstrap-routing.env ({error}); stdout envelope emitted"
        );
        emit_envelope(&envelope, &tail.advisory_lines);
        return ExitCode::SUCCESS;
    }
    emit_envelope(&envelope, &tail.advisory_lines);
    ExitCode::SUCCESS
}

#[derive(Clone, Debug)]
struct ContinuationFailure {
    step: String,
    detail: String,
}

impl ContinuationFailure {
    fn new(step: impl Into<String>, detail: impl Into<String>) -> Self {
        Self {
            step: step.into(),
            detail: detail.into(),
        }
    }
}

#[derive(Default)]
struct ContinueTailResult {
    routing: BTreeMap<String, String>,
    advisory_lines: Vec<String>,
}

fn normalize_state_defaults(state: &mut BootstrapState) {
    if state.repo_unavailable.is_empty() {
        "false".clone_into(&mut state.repo_unavailable);
    }
    if state.deferred.is_empty() {
        "false".clone_into(&mut state.deferred);
    }
    if state.stall_tracking.is_empty() {
        "false".clone_into(&mut state.stall_tracking);
    }
}

fn run_after_infrastructure(
    state: &mut BootstrapState,
    options: &BootstrapOptions,
) -> Result<(), ContinuationFailure> {
    phase_tracking(state, options)?;
    if valid_run_id(&state.run_id) {
        write_base_session_env(state, options)
            .map_err(|error| ContinuationFailure::new("write-session-env", error))?;
    }
    if state.implement_bail_reason.is_empty()
        && state.stall_tracking != "true"
        && state.repo_unavailable != "true"
    {
        phase_plan(state, options)?;
    }
    if state.implement_bail_reason.is_empty() && state.stall_tracking != "true" && !options.resume()
    {
        phase_coder(state, options);
    }
    Ok(())
}

fn phase_tracking(
    state: &mut BootstrapState,
    options: &BootstrapOptions,
) -> Result<(), ContinuationFailure> {
    if state.repo_unavailable == "true" {
        "repo-unavailable-skip".clone_into(&mut state.branch_selected);
        "true".clone_into(&mut state.deferred);
        return Ok(());
    }
    if options.forked_target == "true" {
        "forked-target-skip".clone_into(&mut state.branch_selected);
        "true".clone_into(&mut state.deferred);
        return Ok(());
    }

    let sentinel = Path::new(&state.implement_tmpdir).join("parent-issue.md");
    if regular_file(&sentinel) {
        let read = run_verified_larch(&[
            OsString::from("tracking-issue"),
            OsString::from("read"),
            OsString::from("--sentinel"),
            sentinel.into_os_string(),
        ]);
        if let Ok(output) = read
            && output.status().success()
        {
            let values = output_values(&output);
            let issue = values.get("ISSUE_NUMBER").cloned().unwrap_or_default();
            let run_id = values.get("RUN_ID").cloned().unwrap_or_default();
            if values.get("ADOPTED").is_some_and(|value| value == "true") {
                if !options.issue_number.is_empty() && issue != options.issue_number {
                    if options.resume() {
                        return Err(ContinuationFailure::new(
                            "resume-plan-tail-sentinel",
                            "issue mismatch",
                        ));
                    }
                    remove_session_file(&state.implement_tmpdir, "parent-issue.md").map_err(
                        |error| {
                            ContinuationFailure::new(
                                "tracking-sentinel-reset",
                                format!("could not safely reset tracking sentinel: {error}"),
                            )
                        },
                    )?;
                } else if options.issue_number.is_empty() {
                    return Err(ContinuationFailure::new(
                        "issue-number-required-for-resume",
                        "issue number missing",
                    ));
                } else if valid_issue(&issue) && valid_run_id(&run_id) {
                    "branch-1-resume".clone_into(&mut state.branch_selected);
                    state.issue_number_resolved = issue;
                    state.run_id = run_id;
                    if options.resume() {
                        return Ok(());
                    }
                    if dirty_or_unknown()? {
                        "dirty-tree".clone_into(&mut state.implement_bail_reason);
                        return Ok(());
                    }
                    let _ignored = perform_tracking_side_effects(state, options, false)?;
                    return Ok(());
                }
            }
        } else if options.resume() {
            return Err(ContinuationFailure::new(
                "resume-plan-tail-sentinel",
                "sentinel unavailable",
            ));
        }
    } else if options.resume()
        && !(regular_file(&Path::new(&state.implement_tmpdir).join("plan.txt"))
            && regular_file(&Path::new(&state.implement_tmpdir).join("feature-description.txt")))
    {
        return Err(ContinuationFailure::new(
            "resume-plan-tail-sentinel",
            "session artifacts unavailable",
        ));
    }
    if options.issue_number.is_empty() {
        return Ok(());
    }
    if options.resume() && regular_file(&Path::new(&state.implement_tmpdir).join("plan.txt")) {
        state
            .issue_number_resolved
            .clone_from(&options.issue_number);
        state.run_id = resolve_run_id(state, options);
        "branch-2-adopt".clone_into(&mut state.branch_selected);
        "true".clone_into(&mut state.deferred);
        return Ok(());
    }

    adopt_tracking_issue(state, options)
}

fn adopt_tracking_issue(
    state: &mut BootstrapState,
    options: &BootstrapOptions,
) -> Result<(), ContinuationFailure> {
    let output = run_verified_larch(&[
        OsString::from("issue"),
        OsString::from("state"),
        OsString::from("--issue"),
        OsString::from(&options.issue_number),
    ])
    .map_err(|error| ContinuationFailure::new("get-issue-state", error))?;
    if !output.status().success() {
        return Err(ContinuationFailure::new(
            "get-issue-state",
            String::from_utf8_lossy(output.stderr()).into_owned(),
        ));
    }
    let values = output_values(&output);
    if values.get("IS_PR").is_some_and(|value| value == "true") {
        "adopted-issue-is-pr".clone_into(&mut state.implement_bail_reason);
        return Ok(());
    }
    match values.get("STATE").map(String::as_str) {
        Some("CLOSED") => {
            "adopted-issue-closed".clone_into(&mut state.implement_bail_reason);
            return Ok(());
        }
        Some("OPEN") => {}
        _ => {
            return Err(ContinuationFailure::new(
                "get-issue-state",
                "unusable issue state",
            ));
        }
    }
    if dirty_or_unknown()? {
        "dirty-tree".clone_into(&mut state.implement_bail_reason);
        return Ok(());
    }
    state
        .issue_number_resolved
        .clone_from(&options.issue_number);
    state.run_id = resolve_run_id(state, options);
    "branch-2-adopt".clone_into(&mut state.branch_selected);
    let _ignored = perform_tracking_side_effects(state, options, true)?;
    Ok(())
}

fn perform_tracking_side_effects(
    state: &mut BootstrapState,
    options: &BootstrapOptions,
    write_sentinel: bool,
) -> Result<bool, ContinuationFailure> {
    if !valid_issue(&state.issue_number_resolved) {
        tracking_bail(state, "invalid issue number", "");
        return Ok(false);
    }
    if !valid_run_id(&state.run_id) {
        tracking_bail(state, "invalid or empty run id", "");
        return Ok(false);
    }
    write_base_session_env(state, options)
        .map_err(|error| ContinuationFailure::new("write-session-env", error))?;
    let init = run_verified_larch(&[
        OsString::from("run-log"),
        OsString::from("init"),
        OsString::from("--log-root"),
        Path::new(&state.implement_tmpdir)
            .join("larch-logs")
            .into_os_string(),
        OsString::from("--skill"),
        OsString::from("implement"),
        OsString::from("--run-id"),
        OsString::from(&state.run_id),
        OsString::from("--issue"),
        OsString::from(&state.issue_number_resolved),
    ]);
    if !init.is_ok_and(|output| output.status().success()) {
        tracking_bail(state, "run-log init failed", "");
        return Ok(false);
    }
    let prior = difficulty_prior(options);
    persist_difficulty_prior(state, &prior);
    write_initial_difficulty_record(state, options, &prior);
    publish_plan_review_tally(state, options);
    if !persist_run_flags(state, options) {
        return Ok(false);
    }
    if !post_tracking_summary(state, options, write_sentinel)? {
        "true".clone_into(&mut state.deferred);
        return Ok(false);
    }
    Ok(true)
}

fn tracking_bail(state: &mut BootstrapState, detail: &str, result: &str) {
    "true".clone_into(&mut state.stall_tracking);
    "tracking-init-failed".clone_into(&mut state.implement_bail_reason);
    if !state.implement_tmpdir.is_empty() {
        let text = redact(&format!("{detail}\n{result}")).text().to_owned();
        let _ignored = write_session_file(
            &state.implement_tmpdir,
            "tracking-init-failed.stderr.log",
            &text,
        );
    }
}

fn persist_run_flags(state: &mut BootstrapState, options: &BootstrapOptions) -> bool {
    let output = run_verified_larch(&[
        OsString::from("session"),
        OsString::from("persist-run-flags"),
        OsString::from("--implement-tmpdir"),
        OsString::from(&state.implement_tmpdir),
        OsString::from("--no-issues"),
        OsString::from("false"),
        OsString::from("--force-requested"),
        OsString::from(&options.force_requested),
        OsString::from("--self-review-requested"),
        OsString::from(&options.self_review_requested),
        OsString::from("--self-implement-requested"),
        OsString::from(&options.self_implement_requested),
        OsString::from("--difficulty-override"),
        OsString::from(&options.difficulty_override),
    ]);
    if output.is_ok_and(|output| output.status().success()) {
        true
    } else {
        "true".clone_into(&mut state.stall_tracking);
        "run-flags-persist-failed".clone_into(&mut state.implement_bail_reason);
        false
    }
}

fn difficulty_prior(options: &BootstrapOptions) -> String {
    if options.preflight_tmpdir.is_empty() {
        return String::new();
    }
    let plan = Path::new(&options.preflight_tmpdir).join("plan-from-issue.txt");
    let Ok(prior) = crate::difficulty_commands::extract_plan_difficulty(&plan) else {
        return String::new();
    };
    if valid_difficulty(&prior) {
        prior
    } else {
        String::new()
    }
}

fn persist_difficulty_prior(state: &BootstrapState, prior: &str) {
    if state.implement_tmpdir.is_empty() {
        return;
    }
    let value = if valid_difficulty(prior) { prior } else { "" };
    let _ignored = write_session_file(
        &state.implement_tmpdir,
        "difficulty-prior.env",
        &format!("DESIGN_DIFFICULTY={value}\n"),
    );
}

fn write_initial_difficulty_record(
    state: &BootstrapState,
    options: &BootstrapOptions,
    prior: &str,
) {
    if state.implement_tmpdir.is_empty() || !valid_run_id(&state.run_id) {
        return;
    }
    let record = Path::new(&state.implement_tmpdir).join("difficulty-rating.json");
    if crate::difficulty_commands::write_bootstrap_record(
        &record,
        prior,
        &options.difficulty_override,
    )
    .is_err()
    {
        return;
    }
    let _ignored = run_verified_larch(&[
        OsString::from("run-log"),
        OsString::from("write"),
        OsString::from("--log-root"),
        Path::new(&state.implement_tmpdir)
            .join("larch-logs")
            .into_os_string(),
        OsString::from("--skill"),
        OsString::from("implement"),
        OsString::from("--run-id"),
        OsString::from(&state.run_id),
        OsString::from("--batch"),
        OsString::from("difficulty-rating"),
        OsString::from("--input-file"),
        record.into_os_string(),
    ]);
}

fn publish_plan_review_tally(state: &BootstrapState, options: &BootstrapOptions) {
    if !valid_run_id(&state.run_id) || state.implement_tmpdir.is_empty() {
        return;
    }
    let preflight = Path::new(&options.preflight_tmpdir);
    let candidates = [
        preflight.join("plan-review-tally.json"),
        preflight.join("voting-tally.json"),
        Path::new(&state.implement_tmpdir).join("plan-review-tally.json"),
    ];
    let source = candidates
        .into_iter()
        .find(|candidate| regular_file(candidate))
        .unwrap_or_else(|| Path::new(&state.implement_tmpdir).join("plan-review-tally-stub.json"));
    if !regular_file(&source) {
        let stub = concat!(
            "{\"schema_version\":2,\"phase\":\"plan-review\",\"batch\":\"plan-review-tally\",",
            "\"mode\":\"simple\",\"rounds\":0,\"accepted_count\":0,\"rejected_count\":0,",
            "\"exonerated_count\":0,\"body\":\"Plan review completed in the /design phase; see the /design run artifacts for the ballots. No plan-review voting ran in this /implement run.\"}"
        );
        if write_session_file(&state.implement_tmpdir, "plan-review-tally-stub.json", stub).is_err()
        {
            return;
        }
    }
    let _ignored = run_verified_larch(&[
        OsString::from("run-log"),
        OsString::from("write"),
        OsString::from("--log-root"),
        Path::new(&state.implement_tmpdir)
            .join("larch-logs")
            .into_os_string(),
        OsString::from("--skill"),
        OsString::from("implement"),
        OsString::from("--run-id"),
        OsString::from(&state.run_id),
        OsString::from("--batch"),
        OsString::from("plan-review-tally"),
        OsString::from("--input-file"),
        source.into_os_string(),
    ]);
}

fn post_tracking_summary(
    state: &BootstrapState,
    options: &BootstrapOptions,
    write_sentinel: bool,
) -> Result<bool, ContinuationFailure> {
    post_issue_in_process(
        &state.implement_tmpdir,
        &state.issue_number_resolved,
        &state.run_id,
        &options.force_requested,
        write_sentinel,
    )
    .map_err(|error| ContinuationFailure::new("internal-error", error))
}

fn dirty_or_unknown() -> Result<bool, ContinuationFailure> {
    let output = run_verified_larch(&[OsString::from("dirty-tree"), OsString::from("checkpoint")])
        .map_err(|error| ContinuationFailure::new("internal-error", error))?;
    if !output.status().success() {
        return Ok(true);
    }
    let status = output_values(&output)
        .get("STATUS")
        .cloned()
        .unwrap_or_default();
    Ok(matches!(status.as_str(), "dirty" | "unknown"))
}

#[allow(clippy::too_many_lines)] // The plan, branch, and lease steps are one ordered compatibility transaction.
fn phase_plan(
    state: &mut BootstrapState,
    options: &BootstrapOptions,
) -> Result<(), ContinuationFailure> {
    state.plan_file = Path::new(&state.implement_tmpdir)
        .join("plan.txt")
        .display()
        .to_string();
    let feature_file = Path::new(&state.implement_tmpdir).join("feature-description.txt");
    if options.resume() {
        if !append_force_bypass(state, options) {
            return Err(ContinuationFailure::new(
                "force-bypass-log",
                "could not preserve force bypass evidence",
            ));
        }
        if !persist_run_flags(state, options) {
            return Ok(());
        }
    } else if !materialize_initial_plan(state, options, &feature_file)? {
        return Ok(());
    }
    if !append_receipt_scope_drift(state, options) {
        return Err(ContinuationFailure::new(
            "receipt-scope-drift-log",
            "could not preserve receipt scope-drift evidence",
        ));
    }
    if dirty_or_unknown()? {
        "dirty-tree".clone_into(&mut state.implement_bail_reason);
        return Ok(());
    }
    if !create_feature_branch(state, options, &feature_file) {
        return Ok(());
    }
    state.branch_name = current_branch(state);
    // A forked target performs no local branch mutation or tracking-lease
    // activation, so it can safely continue from a detached checkout (as CI
    // does). Normal implementation remains fail-closed without a branch.
    if state.branch_name.is_empty() && options.forked_target != "true" {
        mark_branch_create_failed(state);
        return Ok(());
    }
    if options.forked_target != "true" && !activate_tracking_lease(state, options) {
        return Ok(());
    }
    write_plan_artifacts(state, options, &feature_file)?;
    eprintln!("→ step0: branch {} + plan logged", state.branch_name);
    Ok(())
}

#[allow(clippy::too_many_lines)] // Copying the reviewed plan and issue snapshot is one compatibility transaction.
fn materialize_initial_plan(
    state: &mut BootstrapState,
    options: &BootstrapOptions,
    _feature_file: &Path,
) -> Result<bool, ContinuationFailure> {
    let snapshot = Path::new(&state.implement_tmpdir).join("untracked-baseline.z");
    if !regular_file(&snapshot) {
        let _ignored = (|| {
            let root = TemporaryRoot::resolve(Some(Path::new(&state.implement_tmpdir))).ok()?;
            let repo_root = repository_root(state)?;
            dirty_tree_commands::capture_untracked_baseline_for_review(&root, &snapshot, &repo_root)
                .then_some(())
        })();
    }
    if !append_force_bypass(state, options) {
        return Err(ContinuationFailure::new(
            "force-bypass-log",
            "could not preserve force bypass evidence",
        ));
    }
    let plan_source = Path::new(&options.preflight_tmpdir).join("plan-from-issue.txt");
    let plan_text = match read_regular_text(&plan_source) {
        Ok(text) => text,
        Err(error) => {
            let _ignored = write_session_file(
                &state.implement_tmpdir,
                "copy-plan.stderr.log",
                &format!("{}\n", redact(&error).text()),
            );
            return Err(ContinuationFailure::new("copy-plan", error));
        }
    };
    persist_difficulty_prior(state, &difficulty_prior(options));
    write_session_file(
        &state.implement_tmpdir,
        "plan.txt",
        &strip_plan_provenance_headers(&plan_text),
    )
    .map_err(|error| ContinuationFailure::new("copy-plan", error))?;

    if options.forked_target == "true" && options.upstream_repo.is_empty() {
        let _ignored = write_session_file(
            &state.implement_tmpdir,
            "gh-issue-view.stderr.log",
            "--forked requires UPSTREAM_REPO before gh issue view\n",
        );
        return Err(ContinuationFailure::new(
            "gh-issue-view",
            "forked target is missing its upstream repository",
        ));
    }
    let issue = issue_for(state, options);
    let repository = issue_repository(state, options);
    if !valid_issue(&issue) || repository.is_empty() {
        let detail = "issue context requires an issue number and repository";
        let _ignored = write_session_file(
            &state.implement_tmpdir,
            "gh-issue-view.stderr.log",
            &format!("{detail}\n"),
        );
        return Err(ContinuationFailure::new("gh-issue-view", detail));
    }
    let context = run_verified_larch(&[
        OsString::from("issue"),
        OsString::from("context"),
        OsString::from("--issue"),
        OsString::from(&issue),
        OsString::from("--repo"),
        OsString::from(&repository),
        OsString::from("--tmpdir"),
        OsString::from(&state.implement_tmpdir),
    ]);
    let context = match context {
        Ok(output) if output.status().success() => output,
        Ok(output) => {
            let stderr = String::from_utf8_lossy(output.stderr());
            let detail = redact(&stderr).text().to_owned();
            let _ignored =
                write_session_file(&state.implement_tmpdir, "gh-issue-view.stderr.log", &detail);
            return Err(ContinuationFailure::new("gh-issue-view", detail));
        }
        Err(error) => {
            let detail = redact(&error).text().to_owned();
            let _ignored =
                write_session_file(&state.implement_tmpdir, "gh-issue-view.stderr.log", &detail);
            return Err(ContinuationFailure::new("gh-issue-view", detail));
        }
    };
    let context_values = output_values(&context);
    let title_path = context_values.get("TITLE_FILE").map_or_else(
        || Path::new(&state.implement_tmpdir).join("upstream-issue-title.txt"),
        PathBuf::from,
    );
    let body_path = context_values.get("BODY_FILE").map_or_else(
        || Path::new(&state.implement_tmpdir).join("upstream-issue-body.txt"),
        PathBuf::from,
    );
    let title = read_regular_text(&title_path)
        .map_err(|error| ContinuationFailure::new("gh-issue-view", error))?;
    let body = read_regular_text(&body_path)
        .map_err(|error| ContinuationFailure::new("gh-issue-view", error))?;
    write_session_file(
        &state.implement_tmpdir,
        "feature-description.txt",
        &format!("{title}\n\n{body}"),
    )
    .map_err(|error| ContinuationFailure::new("gh-issue-view", error))?;
    Ok(persist_run_flags(state, options))
}

fn append_force_bypass(state: &BootstrapState, options: &BootstrapOptions) -> bool {
    if options.force_requested != "true" || options.preflight_tmpdir.is_empty() {
        return true;
    }
    let source = Path::new(&options.preflight_tmpdir).join("force-bypass.log");
    let sentinel = Path::new(&state.implement_tmpdir).join(".force-bypass-log-consumed");
    let Ok(source_present) = safe_regular_file_present(&source) else {
        return false;
    };
    let Ok(sentinel_present) = safe_regular_file_present(&sentinel) else {
        return false;
    };
    if !source_present || sentinel_present {
        return true;
    }
    let Ok(text) = read_regular_text(&source) else {
        return false;
    };
    let issue = issue_for(state, options);
    let valid = !text.trim().is_empty()
        && text
            .lines()
            .filter(|line| !line.trim().is_empty())
            .all(|line| {
                let Some(rest) = line.trim().strip_prefix("BYPASS kind=") else {
                    return false;
                };
                let Some((kind, issue_part)) = rest.split_once(" issue=") else {
                    return false;
                };
                kind == "missing-designed-prefix" && issue_part == issue
            });
    if !valid {
        let diagnostic = "force-bypass.invalid-format.redacted.log";
        if write_session_file(
            &state.implement_tmpdir,
            diagnostic,
            &format!("Invalid force bypass log redacted.\nEXPECTED_ISSUE={issue}\nEXIT_CODE=99\n"),
        )
        .is_err()
        {
            return false;
        }
        if !append_failure_with_entry_fallback(
            state,
            "implement-bootstrap force-bypass-log",
            "/implement --force preflight",
            "99",
            "Warnings",
            diagnostic,
            "invalid-format",
        ) {
            return false;
        }
    }
    write_session_file(&state.implement_tmpdir, ".force-bypass-log-consumed", "").is_ok()
}

fn append_receipt_scope_drift(state: &BootstrapState, options: &BootstrapOptions) -> bool {
    if options.preflight_tmpdir.is_empty() {
        return true;
    }
    let source = Path::new(&options.preflight_tmpdir).join("receipt-scope-drift.md");
    let sentinel = Path::new(&state.implement_tmpdir).join(".receipt-scope-drift-consumed");
    let Ok(source_present) = safe_regular_file_present(&source) else {
        return false;
    };
    let Ok(sentinel_present) = safe_regular_file_present(&sentinel) else {
        return false;
    };
    if !source_present || sentinel_present {
        return true;
    }
    let Ok(metadata) = fs::metadata(&source) else {
        return false;
    };
    if metadata.len() > RECEIPT_SCOPE_DRIFT_MAX_BYTES as u64 {
        return false;
    }
    let Ok(entry) = read_regular_text(&source) else {
        return false;
    };
    if !valid_receipt_scope_drift(&entry) {
        return false;
    }
    if write_session_file(&state.implement_tmpdir, "receipt-scope-drift.md", &entry).is_err() {
        return false;
    }
    let output = run_verified_larch(&[
        OsString::from("run-log"),
        OsString::from("append-entry"),
        OsString::from("--log"),
        Path::new(&state.implement_tmpdir)
            .join("execution-issues.md")
            .into_os_string(),
        OsString::from("--category"),
        OsString::from("Warnings"),
        OsString::from("--entry-file"),
        Path::new(&state.implement_tmpdir)
            .join("receipt-scope-drift.md")
            .into_os_string(),
    ]);
    if !output.is_ok_and(|result| {
        result.status().success()
            && output_values(&result)
                .get("APPENDED")
                .is_some_and(|value| value == "true")
    }) {
        return false;
    }
    write_session_file(&state.implement_tmpdir, ".receipt-scope-drift-consumed", "").is_ok()
}

fn valid_receipt_scope_drift(entry: &str) -> bool {
    let lines: Vec<&str> = entry.lines().collect();
    if lines.len() < 7
        || lines.len() > RECEIPT_SCOPE_DRIFT_MAX_ROWS + 6
        || lines[0] != "- **Preflight plan-receipt scope refresh**: semantic materiality passed."
        || !receipt_scope_sha_line(lines[1], "  - Receipt base: `")
        || !receipt_scope_sha_line(lines[2], "  - Reviewed target: `")
        || lines[3] != "  - Scope diff (JSON-quoted name-status rows):"
        || lines[4] != "    ```text"
        || lines.last() != Some(&"    ```")
    {
        return false;
    }
    lines[5..lines.len() - 1].iter().all(|line| {
        line.strip_prefix("    ")
            .and_then(|row| serde_json::from_str::<String>(row).ok())
            .is_some()
    })
}

fn receipt_scope_sha_line(line: &str, prefix: &str) -> bool {
    line.strip_prefix(prefix)
        .and_then(|value| value.strip_suffix('`'))
        .is_some_and(|sha| {
            sha.len() == 40
                && sha
                    .bytes()
                    .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
        })
}

fn append_failure_with_entry_fallback(
    state: &BootstrapState,
    site: &str,
    tool: &str,
    exit_code: &str,
    category: &str,
    output_file: &str,
    status_label: &str,
) -> bool {
    let log = Path::new(&state.implement_tmpdir).join("execution-issues.md");
    let output = run_verified_larch(&[
        OsString::from("run-log"),
        OsString::from("append-failure"),
        OsString::from("--log"),
        log.clone().into_os_string(),
        OsString::from("--site"),
        OsString::from(site),
        OsString::from("--tool"),
        OsString::from(tool),
        OsString::from("--exit-code"),
        OsString::from(exit_code),
        OsString::from("--category"),
        OsString::from(category),
        OsString::from("--output-file"),
        Path::new(&state.implement_tmpdir)
            .join(output_file)
            .into_os_string(),
        OsString::from("--status-label"),
        OsString::from(status_label),
        OsString::from("--redact"),
    ]);
    if output.is_ok_and(|result| result.status().success()) {
        return true;
    }
    let fallback = format!(
        "- **Step {site}: {tool} {status_label} (exit {exit_code}; append-failure fallback)**:\n  ```\nno diagnostics captured\n  ```\n"
    );
    run_verified_larch(&[
        OsString::from("run-log"),
        OsString::from("append-entry"),
        OsString::from("--log"),
        log.into_os_string(),
        OsString::from("--category"),
        OsString::from(category),
        OsString::from("--entry"),
        OsString::from(fallback),
    ])
    .is_ok_and(|result| result.status().success())
}

fn strip_plan_provenance_headers(text: &str) -> String {
    let lines: Vec<&str> = text.split_inclusive('\n').collect();
    if lines.is_empty() {
        return text.to_owned();
    }
    let mut end = lines.len();
    while end > 0 && logical_line(lines[end - 1]).trim().is_empty() {
        end -= 1;
    }
    let mut index = end;
    let mut trailers: Vec<(usize, &str)> = Vec::new();
    while index > 0 {
        let Some(key) = valid_trailer_key(logical_line(lines[index - 1])) else {
            break;
        };
        trailers.push((index - 1, key));
        index -= 1;
    }
    trailers.reverse();
    if trailers.last().is_none_or(|(_, key)| *key != "diff_lines") {
        return text.to_owned();
    }
    let remove: Vec<usize> = trailers
        .into_iter()
        .filter_map(|(line, key)| {
            matches!(key, "review_status" | "rounds_completed" | "difficulty").then_some(line)
        })
        .collect();
    if remove.is_empty() {
        return text.to_owned();
    }
    lines
        .iter()
        .enumerate()
        .filter_map(|(line, value)| (!remove.contains(&line)).then_some(*value))
        .collect()
}

fn logical_line(line: &str) -> &str {
    let without_newline = line.strip_suffix('\n').unwrap_or(line);
    without_newline
        .strip_suffix('\r')
        .unwrap_or(without_newline)
}

fn valid_trailer_key(line: &str) -> Option<&str> {
    let (key, value) = line.split_once(": ")?;
    if value.is_empty() {
        return None;
    }
    match key {
        "review_status" => (!value.trim().is_empty()).then_some(key),
        "rounds_completed" | "diff_lines" => value
            .bytes()
            .all(|byte| byte.is_ascii_digit())
            .then_some(key),
        "difficulty" => valid_difficulty(value).then_some(key),
        "diff_added" | "diff_deleted" => value
            .bytes()
            .all(|byte| byte.is_ascii_digit())
            .then_some(key),
        "mechanical_churn" => matches!(value, "true" | "false").then_some(key),
        "oversize_override" => (value == "operator").then_some(key),
        _ => None,
    }
}

fn mark_branch_create_failed(state: &mut BootstrapState) {
    "true".clone_into(&mut state.stall_tracking);
    "branch-create-failed".clone_into(&mut state.implement_bail_reason);
}

fn create_feature_branch(
    state: &mut BootstrapState,
    options: &BootstrapOptions,
    feature_file: &Path,
) -> bool {
    if options.forked_target == "true"
        || state.is_user_branch == "true"
        || !regular_file(feature_file)
    {
        return true;
    }
    let raw = read_regular_lossy(feature_file)
        .lines()
        .next()
        .unwrap_or("issue")
        .to_owned();
    let slug = branch_slug(&raw);
    let branch = if state.user_prefix.is_empty() || state.issue_number_resolved.is_empty() {
        String::new()
    } else {
        format!(
            "{}/{slug}-{}",
            state.user_prefix, state.issue_number_resolved
        )
    };
    if branch.is_empty() {
        return true;
    }
    let Some(cwd) = repository_root(state) else {
        mark_branch_create_failed(state);
        return false;
    };
    let Ok(remote) = GitRemote::new("origin") else {
        mark_branch_create_failed(state);
        return false;
    };
    let Ok(refspec) = GitRefspec::new("refs/heads/main:refs/remotes/origin/main") else {
        mark_branch_create_failed(state);
        return false;
    };
    let Ok(name) = GitRef::new(&branch) else {
        mark_branch_create_failed(state);
        return false;
    };
    let Ok(base) = GitRef::new("origin/main") else {
        mark_branch_create_failed(state);
        return false;
    };
    let Ok(policy) = GitCliPolicy::new(cwd) else {
        mark_branch_create_failed(state);
        return false;
    };
    let Ok(runtime) = LarchRuntime::new() else {
        mark_branch_create_failed(state);
        return false;
    };
    let runner = TokioProcessRunner::default();
    let git = GitCli::new(&runner, policy);
    let cancellation = Cancellation::new();
    let created = runtime
        .block_on(git.fetch(
            FetchRequest {
                remote,
                refspec: Some(refspec),
                quiet: true,
                no_tags: false,
            },
            &cancellation,
        ))
        .and_then(|_| {
            runtime.block_on(git.checkout(
                CheckoutRequest::Branch {
                    create: true,
                    force: false,
                    no_track: true,
                    name,
                    start_point: Some(base),
                },
                &cancellation,
            ))
        });
    if created.is_err() {
        mark_branch_create_failed(state);
        return false;
    }
    "created".clone_into(&mut state.branch_action);
    true
}

fn write_plan_artifacts(
    state: &BootstrapState,
    options: &BootstrapOptions,
    feature_file: &Path,
) -> Result<(), ContinuationFailure> {
    let plan_text = read_regular_text(Path::new(&state.plan_file))
        .map_err(|error| ContinuationFailure::new("internal-error", error))?;
    let feature = read_regular_lossy(feature_file);
    let title = feature
        .lines()
        .next()
        .filter(|value| !value.is_empty())
        .unwrap_or("planned change");
    let issue = issue_for(state, options);
    let goal = format!("Implement issue #{issue}: {title}.");
    let plan_goals = compose_plan_goals_test(&plan_text, &goal);
    write_session_file(&state.implement_tmpdir, "plan-goals-test.md", &plan_goals)
        .map_err(|error| ContinuationFailure::new("internal-error", error))?;
    write_session_file(&state.implement_tmpdir, "run-step1-plan-log.out", "")
        .map_err(|error| ContinuationFailure::new("internal-error", error))?;
    if valid_run_id(&state.run_id) {
        let _ignored = run_verified_larch(&[
            OsString::from("run-log"),
            OsString::from("write"),
            OsString::from("--log-root"),
            Path::new(&state.implement_tmpdir)
                .join("larch-logs")
                .into_os_string(),
            OsString::from("--skill"),
            OsString::from("implement"),
            OsString::from("--run-id"),
            OsString::from(&state.run_id),
            OsString::from("--batch"),
            OsString::from("plan-goals-test"),
            OsString::from("--input-file"),
            Path::new(&state.implement_tmpdir)
                .join("plan-goals-test.md")
                .into_os_string(),
        ]);
    }
    publish_plan_review_tally(state, options);
    upsert_plan_summary(state, options);
    Ok(())
}

fn upsert_plan_summary(state: &BootstrapState, options: &BootstrapOptions) {
    let issue = issue_for(state, options);
    if !valid_issue(&issue) || !valid_run_id(&state.run_id) || state.plan_file.is_empty() {
        return;
    }
    let Ok(plan) = read_regular_text(Path::new(&state.plan_file)) else {
        return;
    };
    let content: String = plan.chars().take(12_000).collect();
    if write_session_file(&state.implement_tmpdir, "summary-plan.md", &content).is_err() {
        return;
    }
    let repository = issue_repository(state, options);
    let mut arguments = vec![
        OsString::from("tracking-issue"),
        OsString::from("upsert-summary"),
        OsString::from("--issue"),
        OsString::from(issue),
        OsString::from("--marker"),
        OsString::from(format!("<!-- larch:plan v1 runid={} -->", state.run_id)),
        OsString::from("--content-file"),
        Path::new(&state.implement_tmpdir)
            .join("summary-plan.md")
            .into_os_string(),
    ];
    if !repository.is_empty() {
        arguments.extend([OsString::from("--repo"), OsString::from(repository)]);
    }
    let _ignored = run_verified_larch(&arguments);
}

#[allow(clippy::too_many_lines)] // The admission and compensating stall transition must remain adjacent.
fn activate_tracking_lease(state: &mut BootstrapState, options: &BootstrapOptions) -> bool {
    let repository = issue_repository(state, options);
    let mut activated = false;
    let pre_body = "tracking-lease-pre-body.md";
    let post_body = "tracking-lease-post-body.md";
    let result = (|| -> Result<(), String> {
        if repository.is_empty() {
            return Err("repository unavailable for implementation lease".to_owned());
        }
        let repo_root =
            repository_root(state).ok_or_else(|| "repository root is unavailable".to_owned())?;
        let base_sha = resolve_revision_sha(&repo_root, "origin/main")?;
        let issue_json = Path::new(&options.preflight_tmpdir).join("issue.json");
        let snapshot = read_regular_text(&issue_json)?;
        let snapshot: serde_json::Value = serde_json::from_str(&snapshot)
            .map_err(|_| "preflight issue freshness identity unavailable".to_owned())?;
        let expected_updated_at = snapshot
            .get("updatedAt")
            .and_then(serde_json::Value::as_str)
            .filter(|value| !value.is_empty())
            .ok_or_else(|| "preflight issue freshness identity unavailable".to_owned())?;
        let expected_body = snapshot
            .get("body")
            .and_then(serde_json::Value::as_str)
            .filter(|value| !value.is_empty())
            .ok_or_else(|| "preflight issue freshness identity unavailable".to_owned())?;
        let expected_title = snapshot
            .get("title")
            .and_then(serde_json::Value::as_str)
            .filter(|value| !value.is_empty())
            .ok_or_else(|| "preflight issue freshness identity unavailable".to_owned())?;
        let labels = preflight_labels_sha256(snapshot.get("labels"))?;
        write_session_file(&state.implement_tmpdir, pre_body, expected_body)?;
        if !governance_gate(
            &state.issue_number_resolved,
            &repository,
            &Path::new(&state.implement_tmpdir).join(pre_body),
            &repo_root,
            &base_sha,
        ) {
            return Err("implementation-lease-admission-refused".to_owned());
        }
        let renamed = run_verified_larch(&[
            OsString::from("tracking-issue"),
            OsString::from("rename"),
            OsString::from("--issue"),
            OsString::from(&state.issue_number_resolved),
            OsString::from("--state"),
            OsString::from("implementing"),
            OsString::from("--repo"),
            OsString::from(&repository),
            OsString::from("--run-id"),
            OsString::from(&state.run_id),
            OsString::from("--lease-branch"),
            OsString::from(&state.branch_name),
            OsString::from("--head-sha"),
            OsString::from(&base_sha),
            OsString::from("--expected-updated-at"),
            OsString::from(expected_updated_at),
            OsString::from("--expected-body-sha256"),
            OsString::from(sha256_text(expected_body)),
            OsString::from("--expected-title-sha256"),
            OsString::from(sha256_text(expected_title)),
            OsString::from("--expected-labels-sha256"),
            OsString::from(labels),
        ])
        .map_err(|error| format!("tracking-issue rename failed: {error}"))?;
        if !renamed.status().success() {
            return Err("tracking-issue rename failed".to_owned());
        }
        activated = true;
        write_session_file(&state.implement_tmpdir, post_body, "").map_err(|error| {
            format!("tracking-issue post-admission output preparation failed: {error}")
        })?;
        let post_body = Path::new(&state.implement_tmpdir).join(post_body);
        let post = run_verified_larch(&[
            OsString::from("tracking-issue"),
            OsString::from("read"),
            OsString::from("--issue"),
            OsString::from(&state.issue_number_resolved),
            OsString::from("--repo"),
            OsString::from(&repository),
            OsString::from("--body-out"),
            post_body.clone().into_os_string(),
        ])
        .map_err(|error| format!("tracking-issue post-admission read failed: {error}"))?;
        if !post.status().success() || !regular_file(&post_body) {
            return Err("tracking-issue post-admission read failed".to_owned());
        }
        if !governance_gate(
            &state.issue_number_resolved,
            &repository,
            &post_body,
            &repo_root,
            &base_sha,
        ) {
            return Err("implementation-lease-post-admission-refused".to_owned());
        }
        Ok(())
    })();
    let cleanup = [pre_body, post_body]
        .into_iter()
        .map(|name| remove_session_file(&state.implement_tmpdir, name))
        .find_map(Result::err);
    if result.is_ok() && cleanup.is_none() {
        return true;
    }
    if activated {
        let _ignored = run_verified_larch(&[
            OsString::from("tracking-issue"),
            OsString::from("rename"),
            OsString::from("--issue"),
            OsString::from(&state.issue_number_resolved),
            OsString::from("--state"),
            OsString::from("stalled"),
            OsString::from("--repo"),
            OsString::from(&repository),
            OsString::from("--run-id"),
            OsString::from(&state.run_id),
        ]);
    }
    tracking_bail(
        state,
        "implementation lease activation failed",
        &result
            .err()
            .or_else(|| cleanup.map(|error| format!("lease evidence cleanup failed: {error}")))
            .unwrap_or_default(),
    );
    false
}

fn governance_gate(
    issue: &str,
    repository: &str,
    body_file: &Path,
    repo_root: &Path,
    head_sha: &str,
) -> bool {
    let Ok(output) = crate::python_verb::run_python_verb(
        crate::implement_preflight_commands::governance_gate_argv(
            issue, repository, body_file, repo_root, head_sha,
        ),
        Duration::from_secs(120),
    ) else {
        return false;
    };
    output.status().success()
        && parse_kv(&String::from_utf8_lossy(output.stdout()))
            .get("GOVERNANCE_OK")
            .is_some_and(|value| value == "true")
}

fn preflight_labels_sha256(value: Option<&serde_json::Value>) -> Result<String, String> {
    let Some(rows) = value.and_then(serde_json::Value::as_array) else {
        return Err("preflight issue labels unavailable".to_owned());
    };
    let mut names = Vec::new();
    for row in rows {
        let name = row
            .get("name")
            .and_then(serde_json::Value::as_str)
            .filter(|value| !value.is_empty())
            .ok_or_else(|| "preflight issue labels unavailable".to_owned())?;
        names.push(name.to_owned());
    }
    names.sort();
    if names.windows(2).any(|pair| pair[0] == pair[1]) {
        return Err("preflight issue labels unavailable".to_owned());
    }
    let mut digest = Sha256::new();
    for name in names {
        let encoded = name.as_bytes();
        digest.update((encoded.len() as u64).to_be_bytes());
        digest.update(encoded);
    }
    Ok(format!("{:x}", digest.finalize()))
}

/// Resolve one declared base scope through `gix` (issue #7671).
pub fn resolve_revision_sha(repo_root: &Path, revision: &str) -> Result<String, String> {
    let repository = GixRepository::open(repo_root).map_err(|error| error.to_string())?;
    repository
        .resolve_revision(&Revision::new(revision.as_bytes().to_vec()))
        .map(|object| object.to_hex())
        .map_err(|error| error.to_string())
}

fn sha256_text(text: &str) -> String {
    format!("{:x}", Sha256::digest(text.as_bytes()))
}

fn issue_for(state: &BootstrapState, options: &BootstrapOptions) -> String {
    if state.issue_number_resolved.is_empty() {
        options.issue_number.clone()
    } else {
        state.issue_number_resolved.clone()
    }
}

fn issue_repository(state: &BootstrapState, options: &BootstrapOptions) -> String {
    if options.forked_target == "true" {
        return options.upstream_repo.clone();
    }
    if !state.repo.is_empty() {
        return state.repo.clone();
    }
    github_repository_resolution::ambient_repo().unwrap_or_default()
}

fn repository_root(state: &BootstrapState) -> Option<PathBuf> {
    let persisted = read_session_value(&state.implement_tmpdir, "session-env.sh", "REPO_ROOT");
    if !persisted.is_empty() {
        let root = PathBuf::from(persisted);
        return root.is_absolute().then_some(root);
    }
    resolve_repo_root()
}

fn current_branch(state: &BootstrapState) -> String {
    repository_root(state)
        .and_then(|root| push_network::current_branch_from(&root))
        .unwrap_or_default()
}

fn branch_slug(raw: &str) -> String {
    let transformed: String = raw
        .to_ascii_lowercase()
        .chars()
        .map(|character| {
            if character.is_ascii_lowercase() || character.is_ascii_digit() {
                character
            } else {
                '-'
            }
        })
        .collect();
    let mut collapsed = String::new();
    let mut previous_dash = false;
    for character in transformed.chars() {
        if character == '-' {
            if !previous_dash {
                collapsed.push(character);
            }
            previous_dash = true;
        } else {
            collapsed.push(character);
            previous_dash = false;
        }
    }
    let shortened: String = collapsed
        .trim_matches('-')
        .chars()
        .take(40)
        .collect::<String>()
        .trim_end_matches('-')
        .to_owned();
    if shortened.is_empty() {
        "issue".to_owned()
    } else {
        shortened
    }
}

fn phase_coder(state: &mut BootstrapState, options: &BootstrapOptions) {
    if !state.implement_bail_reason.is_empty()
        || state.stall_tracking == "true"
        || state.repo_unavailable == "true"
        || state.plan_file.is_empty()
        || !regular_file(Path::new(&state.plan_file))
        || !regular_file(&Path::new(&state.implement_tmpdir).join("feature-description.txt"))
    {
        return;
    }
    if options.self_implement_requested == "true" || options.coder_opt == "claude" {
        "claude".clone_into(&mut state.coder);
        eprintln!("→ step0: coder={}", state.coder);
        return;
    }
    let order: &[&str] = match options.coder_opt.as_str() {
        "codex" => &["codex", "cursor", "claude"],
        "cursor" => &["cursor", "codex", "claude"],
        _ => coder_order_for_difficulty(&state.implement_tmpdir),
    };
    state.coder = order
        .iter()
        .copied()
        .find(|candidate| match *candidate {
            "codex" => state.codex_available == "true",
            "cursor" => state.cursor_available == "true",
            "claude" => true,
            _ => false,
        })
        .unwrap_or("claude")
        .to_owned();
    if state.coder == "claude" {
        "true".clone_into(&mut state.coder_fallback);
    }
    if matches!(options.coder_opt.as_str(), "codex" | "cursor")
        && state.coder != options.coder_opt
        && !coder_available(state, &options.coder_opt)
    {
        record_explicit_coder_unavailable(state, &options.coder_opt, &state.coder);
    }
    if state.coder_fallback == "true" {
        record_coder_fallback(state);
    }
    eprintln!("→ step0: coder={}", state.coder);
}

fn coder_order_for_difficulty(tmpdir: &str) -> &'static [&'static str] {
    let override_tier = read_session_value(tmpdir, "run-flags.sh", "DIFFICULTY_OVERRIDE");
    let prior = read_session_value(tmpdir, "difficulty-prior.env", "DESIGN_DIFFICULTY");
    coder_order_for_tier(
        if valid_difficulty(&override_tier) {
            override_tier
        } else {
            prior
        }
        .as_str(),
    )
}

fn coder_order_for_tier(tier: &str) -> &'static [&'static str] {
    const CURSOR_FIRST: &[&str] = &["cursor", "codex", "claude"];
    const CODEX_FIRST: &[&str] = &["codex", "cursor", "claude"];
    match tier {
        "TRIVIAL" | "MODERATE" => CURSOR_FIRST,
        "HARD" => CODEX_FIRST,
        _ => role_default("implement.step2_coder")
            .map(|role| role.order)
            .unwrap_or(CODEX_FIRST),
    }
}

fn coder_available(state: &BootstrapState, candidate: &str) -> bool {
    match candidate {
        "codex" => state.codex_available == "true",
        "cursor" => state.cursor_available == "true",
        "claude" => true,
        _ => false,
    }
}

fn record_coder_fallback(state: &BootstrapState) {
    if state.implement_tmpdir.is_empty() {
        return;
    }
    let warning = "**⚠ Cursor and Codex unavailable — implementing with Claude subagent (larch:claude-implementer).**";
    eprintln!("{warning}");
    let file = "coder-fallback-warning.txt";
    let _ignored = write_session_file(
        &state.implement_tmpdir,
        file,
        &format!("{warning}\nREASON=requested external coder unavailable\n"),
    );
    let _ignored = append_failure_with_entry_fallback(
        state,
        "implement-bootstrap coder-select",
        "phase_coder_select",
        "0",
        "Warnings",
        file,
        "fallback",
    );
    if valid_run_id(&state.run_id) {
        let _ignored = run_verified_larch(&[
            OsString::from("run-log"),
            OsString::from("manifest"),
            OsString::from("--log-root"),
            Path::new(&state.implement_tmpdir)
                .join("larch-logs")
                .into_os_string(),
            OsString::from("--skill"),
            OsString::from("implement"),
            OsString::from("--run-id"),
            OsString::from(&state.run_id),
            OsString::from("--field"),
            OsString::from("coder_fallback=true"),
        ]);
    }
}

fn record_explicit_coder_unavailable(state: &BootstrapState, requested: &str, selected: &str) {
    if state.implement_tmpdir.is_empty() {
        return;
    }
    let warning =
        format!("**⚠ Requested {requested} implementer unavailable — using {selected}.**");
    eprintln!("{warning}");
    let file = format!("{requested}-unavailable-warning.txt");
    let _ignored = write_session_file(
        &state.implement_tmpdir,
        &file,
        &format!("{warning}\nREQUESTED={requested}\nSELECTED={selected}\n"),
    );
    let _ignored = append_failure_with_entry_fallback(
        state,
        "implement-bootstrap coder-select",
        "phase_coder_select",
        "0",
        "Warnings",
        &file,
        "fallback",
    );
}

fn final_values(state: &BootstrapState, options: &BootstrapOptions) -> BTreeMap<String, String> {
    let mut values = BTreeMap::new();
    let repo_root = repository_root(state)
        .map(|path| path.display().to_string())
        .unwrap_or_default();
    for (key, value) in [
        ("CURRENT_BRANCH", &state.current_branch),
        ("IS_MAIN", &state.is_main),
        ("IS_USER_BRANCH", &state.is_user_branch),
        ("USER_PREFIX", &state.user_prefix),
        ("ENTRY_GATE", &state.entry_gate),
        ("SKIP_BRANCH_CHECK", &state.skip_branch_check),
        ("IMPLEMENT_TMPDIR", &state.implement_tmpdir),
        ("SESSION_ID", &state.session_id),
        ("CLAUDE_BINARY_FOUND", &state.claude_binary_found),
        ("CODEX_BINARY_FOUND", &state.codex_binary_found),
        ("CURSOR_BINARY_FOUND", &state.cursor_binary_found),
        ("REPO", &state.repo),
        ("REPO_UNAVAILABLE", &state.repo_unavailable),
        ("REPO_ROOT", &repo_root),
        ("codex_available", &state.codex_available),
        ("cursor_available", &state.cursor_available),
        (
            "ISSUE_NUMBER",
            if state.issue_number_resolved.is_empty() {
                &options.issue_number
            } else {
                &state.issue_number_resolved
            },
        ),
        ("RUN_ID", &state.run_id),
        ("BRANCH_SELECTED", &state.branch_selected),
        ("DEFERRED", &state.deferred),
        ("STALL_TRACKING", &state.stall_tracking),
        ("BRANCH_NAME", &state.branch_name),
        ("BRANCH_ACTION", &state.branch_action),
        ("PLAN_FILE", &state.plan_file),
        ("FORCE_REQUESTED", &options.force_requested),
        ("SELF_REVIEW_REQUESTED", &options.self_review_requested),
        (
            "SELF_IMPLEMENT_REQUESTED",
            &options.self_implement_requested,
        ),
        ("DIFFICULTY_OVERRIDE", &options.difficulty_override),
        ("coder", &state.coder),
        ("coder_fallback", &state.coder_fallback),
        ("IMPLEMENT_BAIL_REASON", &state.implement_bail_reason),
    ] {
        if !value.is_empty() {
            values.insert(key.to_owned(), single_line(value));
        }
    }
    values
}

fn resolve_run_id(state: &BootstrapState, options: &BootstrapOptions) -> String {
    for value in [&options.run_id, &state.run_id] {
        if valid_run_id(value) {
            return (*value).clone();
        }
    }
    let session = read_regular_lossy(&Path::new(&state.implement_tmpdir).join("session-id"));
    let candidate = session.trim();
    if valid_run_id(candidate) {
        candidate.to_owned()
    } else if valid_run_id(&state.session_id) {
        state.session_id.clone()
    } else {
        String::new()
    }
}

fn continue_predicate(values: &BTreeMap<String, String>) -> bool {
    values
        .get("IMPLEMENT_BAIL_REASON")
        .is_none_or(String::is_empty)
        && values
            .get("STALL_TRACKING")
            .is_none_or(|value| value != "true")
        && !step2_blockers(values)
        && values.get("coder").is_some_and(|value| !value.is_empty())
}

fn step2_blockers(values: &BTreeMap<String, String>) -> bool {
    if values
        .get("REPO_UNAVAILABLE")
        .is_some_and(|value| value == "true")
    {
        return true;
    }
    let Some(plan) = values.get("PLAN_FILE").filter(|value| !value.is_empty()) else {
        return true;
    };
    if !regular_file(Path::new(plan)) {
        return true;
    }
    let Some(tmpdir) = values
        .get("IMPLEMENT_TMPDIR")
        .filter(|value| !value.is_empty())
    else {
        return false;
    };
    let root = Path::new(tmpdir);
    !regular_file(&root.join("plan.txt")) || !regular_file(&root.join("feature-description.txt"))
}

fn run_absorbed_continue_tail(
    values: &BTreeMap<String, String>,
    options: &BootstrapOptions,
) -> Result<ContinueTailResult, ContinuationFailure> {
    if !continue_predicate(values) {
        return Ok(ContinueTailResult::default());
    }
    let tmpdir = values
        .get("IMPLEMENT_TMPDIR")
        .filter(|value| !value.is_empty())
        .ok_or_else(|| {
            ContinuationFailure::new("absorbed-continue-tail", "IMPLEMENT_TMPDIR is missing")
        })?;
    if options.self_subagents_only() {
        let (probe_routing, advisory_lines) = run_1r_probe(&options.forked_target)?;
        let mut routing = BTreeMap::from([
            ("DEGRADED".to_owned(), "false".to_owned()),
            ("BOTH_DOWN".to_owned(), "false".to_owned()),
            ("DEGRADED_PROMPT_REQUIRED".to_owned(), "false".to_owned()),
        ]);
        routing.extend(probe_routing);
        remove_route_if_step2_blocked(values, &mut routing);
        return Ok(ContinueTailResult {
            routing,
            advisory_lines,
        });
    }

    let probe = refresh_gate_probe(options)?;
    let gate_detail =
        agent_commands::current_codex_probe_detail(&probe.codex_binary_found, &probe.codex_present)
            .map(CodexGateMessage::new);
    let gate = DegradedToolsResult::classify(
        &probe.codex_binary_found,
        &probe.codex_present,
        &probe.cursor_binary_found,
        &probe.cursor_present,
        "implement",
        gate_detail.as_ref(),
    );
    let mut routing = BTreeMap::from([
        ("DEGRADED".to_owned(), bool_text(gate.degraded()).to_owned()),
        ("CODEX_STATE".to_owned(), gate.codex_state().to_owned()),
        ("CURSOR_STATE".to_owned(), gate.cursor_state().to_owned()),
        ("DEGRADED_PROMPT_REQUIRED".to_owned(), "false".to_owned()),
        (
            "BOTH_DOWN".to_owned(),
            bool_text(gate.both_down()).to_owned(),
        ),
    ]);
    if gate.both_down() {
        routing.insert("DEGRADED_HARD_FAIL".to_owned(), "true".to_owned());
    }
    if gate.presence_input_empty() {
        append_presence_input_warning(tmpdir);
    }

    if gate.degraded() {
        let explanation = gate.explanation();
        if explanation.is_empty() {
            return Err(ContinuationFailure::new(
                "absorbed-degraded-explanation-missing",
                "degraded tools gate returned no explanation",
            ));
        }
        let explanation_text = explanation.join("\n");
        if gate.both_down() {
            for line in explanation {
                eprintln!("{line}");
            }
            return Err(ContinuationFailure::new(
                "degraded-both-down-hard-fail",
                explanation_text,
            ));
        }
        let sentinel = Path::new(tmpdir).join(".degraded-tools-gate-prompted");
        if !regular_file(&sentinel) {
            for line in explanation {
                eprintln!("{line}");
            }
            routing.insert("DEGRADED_PROMPT_REQUIRED".to_owned(), "true".to_owned());
            return Ok(ContinueTailResult {
                routing,
                advisory_lines: Vec::new(),
            });
        }
    }

    let (probe_routing, advisory_lines) = run_1r_probe(&options.forked_target)?;
    routing.extend(probe_routing);
    remove_route_if_step2_blocked(values, &mut routing);
    Ok(ContinueTailResult {
        routing,
        advisory_lines,
    })
}

#[derive(Default)]
struct GateProbeState {
    codex_binary_found: String,
    cursor_binary_found: String,
    codex_present: String,
    cursor_present: String,
}

fn refresh_gate_probe(options: &BootstrapOptions) -> Result<GateProbeState, ContinuationFailure> {
    let environment = BTreeMap::new();
    let result = agent_commands::check_reviewers_with_environment(
        options.skip_codex_probe,
        options.skip_cursor_probe,
        &environment,
    )
    .or_else(|_| {
        agent_commands::check_reviewers_with_environment(
            options.skip_codex_probe,
            options.skip_cursor_probe,
            &environment,
        )
    })
    .map_err(|error| ContinuationFailure::new("absorbed-gate-probe-refresh-failed", error))?;
    Ok(GateProbeState {
        codex_binary_found: bool_text(result.codex_binary_found()).to_owned(),
        cursor_binary_found: bool_text(result.cursor_binary_found()).to_owned(),
        codex_present: bool_text(result.codex_present()).to_owned(),
        cursor_present: bool_text(result.cursor_present()).to_owned(),
    })
}

fn append_presence_input_warning(tmpdir: &str) {
    let _ignored = run_verified_larch(&[
        OsString::from("run-log"),
        OsString::from("append-entry"),
        OsString::from("--log"),
        Path::new(tmpdir)
            .join("execution-issues.md")
            .into_os_string(),
        OsString::from("--category"),
        OsString::from("Warnings"),
        OsString::from("--entry"),
        OsString::from(
            "- **Step 0 degraded-tools gate**: PRESENCE_INPUT_EMPTY=true (caller rehydration warning)\n",
        ),
    ]);
}

fn run_1r_probe(
    forked_target: &str,
) -> Result<(BTreeMap<String, String>, Vec<String>), ContinuationFailure> {
    let output = run_verified_larch(&[
        OsString::from("push"),
        OsString::from("checkpoint-probe"),
        OsString::from("1.r"),
        OsString::from("plan materialization"),
        OsString::from("--forked-target"),
        OsString::from(if forked_target == "true" {
            "true"
        } else {
            "false"
        }),
    ])
    .map_err(|error| ContinuationFailure::new("absorbed-continue-tail", error))?;
    Ok(normalize_1r_probe_output(
        &String::from_utf8_lossy(output.stdout()),
        &String::from_utf8_lossy(output.stderr()),
        output.status().code().unwrap_or(1),
    ))
}

fn normalize_1r_probe_output(
    stdout: &str,
    stderr: &str,
    exit_code: i32,
) -> (BTreeMap<String, String>, Vec<String>) {
    let mut routing = BTreeMap::new();
    let mut advisory_lines = Vec::new();
    for line in stdout.lines() {
        if line.starts_with("PHANTOM_") {
            advisory_lines.push(line.to_owned());
        }
    }
    if let Ok(document) = KvDocument::parse(
        stdout,
        ParseOptions {
            cr_strip: CrStrip::Suffix,
            ..ParseOptions::legacy()
        },
    ) {
        for row in document.rows() {
            if ROUTING_KEYS.contains(&row.key()) {
                routing.insert(row.key().to_owned(), row.value().to_owned());
            }
        }
    }
    routing.insert("REBASE_RC".to_owned(), exit_code.to_string());
    let route = routing.get("ROUTE").map_or("", String::as_str);
    if !matches!(route, "continue" | "conflict" | "bail") {
        routing.insert("ROUTE".to_owned(), "bail".to_owned());
        routing.insert("CHECKPOINT_NEXT".to_owned(), "load-routing".to_owned());
        routing
            .entry("REBASE_OUTCOME".to_owned())
            .or_insert_with(|| "failed".to_owned());
        let diagnostic = if stderr.is_empty() {
            format!("probe rc {exit_code}")
        } else {
            core_single_line(stderr)
        };
        routing.insert(
            "REBASE_ERROR".to_owned(),
            redact(&diagnostic).text().to_owned(),
        );
    } else if !matches!(
        routing.get("CHECKPOINT_NEXT").map_or("", String::as_str),
        "continue" | "load-routing"
    ) {
        routing.insert("CHECKPOINT_NEXT".to_owned(), "load-routing".to_owned());
    }
    (routing, advisory_lines)
}

fn remove_route_if_step2_blocked(
    values: &BTreeMap<String, String>,
    routing: &mut BTreeMap<String, String>,
) {
    let mut combined = values.clone();
    combined.extend(routing.clone());
    if step2_blockers(&combined) {
        routing.remove("ROUTE");
    }
}

const fn bool_text(value: bool) -> &'static str {
    if value { "true" } else { "false" }
}

fn bootstrap_next(
    values: &BTreeMap<String, String>,
    continue_tail_attempted: bool,
) -> &'static str {
    if values
        .get("DEGRADED_PROMPT_REQUIRED")
        .is_some_and(|value| value == "true")
    {
        return "degraded-prompt";
    }
    let route = values.get("ROUTE").map_or("", String::as_str);
    let bail = values
        .get("IMPLEMENT_BAIL_REASON")
        .map_or("", String::as_str);
    if matches!(route, "conflict" | "bail") && !step2_blockers(values) {
        "rebase-routing"
    } else if bail == "dirty-tree" {
        "dirty-recovery"
    } else if step2_blockers(values)
        || !bail.is_empty()
        || values.get("STALL_TRACKING").is_some_and(|v| v == "true")
    {
        "cleanup"
    } else if continue_tail_attempted && !matches!(route, "continue" | "conflict" | "bail") {
        "rebase-routing"
    } else if route == "continue" && values.get("coder").is_some_and(|value| !value.is_empty()) {
        "step2"
    } else {
        "cleanup"
    }
}

fn preserve_resume_routing(values: &mut BTreeMap<String, String>, routing_file: &Path) {
    let prior = parse_routing_file(routing_file);
    for key in ["coder", "coder_fallback"] {
        if values.get(key).is_none_or(String::is_empty)
            && let Some(value) = prior.get(key).filter(|value| !value.is_empty())
        {
            values.insert(key.to_owned(), value.clone());
        }
    }
}

fn restore_resume_coder(values: &mut BTreeMap<String, String>, routing_file: &Path, tmpdir: &Path) {
    if values.get("coder").is_some_and(|value| !value.is_empty()) {
        return;
    }
    for source in [
        routing_file.to_path_buf(),
        tmpdir.join("session-env.sh"),
        tmpdir.join("run-flags.sh"),
    ] {
        for key in ["coder", "coder_fallback"] {
            if values.get(key).is_none_or(String::is_empty)
                && let Some(value) = parse_routing_file(&source)
                    .get(key)
                    .filter(|value| !value.is_empty())
            {
                values.insert(key.to_owned(), value.clone());
            }
        }
        if values.get("coder").is_some_and(|value| !value.is_empty()) {
            return;
        }
    }
    for source in [tmpdir.join("session-env.sh"), tmpdir.join("run-flags.sh")] {
        if values.get("coder").is_none_or(String::is_empty) {
            let coder = read_session_value_from_path(&source, "coder");
            if matches!(coder.as_str(), "claude" | "codex" | "cursor") {
                values.insert("coder".to_owned(), coder);
            }
        }
        if values.get("coder_fallback").is_none_or(String::is_empty) {
            let fallback = read_session_value_from_path(&source, "coder_fallback");
            if !fallback.is_empty() {
                values.insert("coder_fallback".to_owned(), fallback);
            }
        }
        if values.get("coder").is_some_and(|value| !value.is_empty()) {
            return;
        }
    }
}

fn parse_routing_file(path: &Path) -> BTreeMap<String, String> {
    if !regular_file(path) {
        return BTreeMap::new();
    }
    parse_kv(&read_regular_lossy(path))
}

fn merge_ship_seed_input(
    tmpdir: &str,
    options: &BootstrapOptions,
    values: &BTreeMap<String, String>,
) -> Result<(), String> {
    let path = Path::new(tmpdir).join("ship-seed-input.env");
    let mut data = if regular_file(&path) {
        parse_kv(&read_regular_lossy(&path))
    } else {
        BTreeMap::new()
    };
    for (key, value) in [
        ("MERGE", options.merge_requested.clone()),
        ("DRAFT", options.draft_requested.clone()),
        ("FORKED_TARGET", options.forked_target.clone()),
        ("NO_ADMIN_FALLBACK", options.no_admin_fallback.clone()),
        ("NO_LOGS_COMMIT", options.no_logs_commit.clone()),
        ("DIFFICULTY_OVERRIDE", options.difficulty_override.clone()),
        (
            "DEFERRED",
            values
                .get("DEFERRED")
                .cloned()
                .unwrap_or_else(|| "false".to_owned()),
        ),
    ] {
        if !options.resume() || data.get(key).is_none_or(String::is_empty) {
            data.insert(key.to_owned(), value);
        }
    }
    let ordered = [
        "MERGE",
        "DRAFT",
        "FORKED_TARGET",
        "NO_ADMIN_FALLBACK",
        "NO_LOGS_COMMIT",
        "DIFFICULTY_OVERRIDE",
        "DEFERRED",
        "MANIFEST_PATH",
        "TOOL_LABEL",
    ];
    let text = ordered
        .iter()
        .filter_map(|key| data.get(*key).map(|value| format!("{key}={value}\n")))
        .collect::<String>();
    write_session_file(tmpdir, "ship-seed-input.env", &text)
}

fn envelope_text(values: &BTreeMap<String, String>) -> String {
    ROUTING_KEYS
        .iter()
        .filter_map(|key| {
            values
                .get(*key)
                .filter(|value| !value.is_empty())
                .map(|value| format!("{key}={value}\n"))
        })
        .collect()
}

fn emit_envelope(envelope: &str, advisory: &[String]) {
    print!("{envelope}");
    for line in advisory {
        println!("{line}");
    }
}

fn emit_failure(failure: &ContinuationFailure, tmpdir: &str) -> ExitCode {
    eprintln!("STEP_FAILED={}", failure.step);
    if failure.step == "absorbed-degraded-gate" && !failure.detail.trim().is_empty() {
        eprintln!("{}", failure.detail.trim_end());
    }
    let message = match failure.step.as_str() {
        "session-entry-gate" => {
            "**⚠ /implement: internal Step 0 contract violation in session-entry-gate.sh. Aborting.**"
        }
        "session-setup" => {
            "**⚠ /implement requires clean main to start. To continue, choose one of: (a) `git checkout main && git status` clean → re-run; (b) check out or create a `<USER_PREFIX>/*` feature branch and re-run. This bypass covers branch position and main-sync only; stash cleanliness still applies on feature branches; (c) commit or stash uncommitted changes on `main` first; (d) clear a non-empty stash with `git stash pop` to restore and commit, or `git stash drop` to discard.**"
        }
        "get-issue-state" => {
            "**⚠ /implement Step 0 tracking: could not verify the adopted issue state. Aborting.**"
        }
        "issue-number-required-for-resume" => {
            "**⚠ /implement Step 0 tracking: --issue-number is required to resume an adopted tracking sentinel. Re-run `/implement <issue-N>` for the sentinel's issue.**"
        }
        "copy-plan" => {
            "**⚠ /implement Step 0 plan materialization: could not copy the preflight plan into the implement session. Aborting.**"
        }
        "gh-issue-view" => {
            "**⚠ /implement Step 0 plan materialization: could not read the issue title/body. Aborting.**"
        }
        "resume-plan-tail-sentinel" => {
            "**⚠ /implement Step 0 dirty-tree recovery: the resume tail could not validate tracking state from the existing session artifacts. Restore or inspect `$IMPLEMENT_TMPDIR`, then restart `/implement`.**"
        }
        "create-branch" => {
            "**⚠ /implement Step 0: could not verify branch state before bootstrap. Aborting.**"
        }
        "write-session-env" => {
            "**⚠ /implement Step 0: could not write session environment. Aborting.**"
        }
        "larch-run" => "**⚠ /implement Step 0: could not write the session launcher. Aborting.**",
        "degraded-both-down-hard-fail" => {
            "**⚠ /implement Step 0: both Codex and Cursor are unavailable after health probes. Aborting.**"
        }
        "force-bypass-log" => {
            "**⚠ /implement Step 0: force bypass log handling failed. Aborting.**"
        }
        "receipt-scope-drift-log" => {
            "**⚠ /implement Step 0: receipt scope-drift evidence handling failed. Aborting.**"
        }
        _ => "",
    };
    if matches!(failure.step.as_str(), "copy-plan" | "gh-issue-view") && !tmpdir.is_empty() {
        let file = if failure.step == "copy-plan" {
            "copy-plan.stderr.log"
        } else {
            "gh-issue-view.stderr.log"
        };
        let diagnostic = redact(&read_regular_lossy(&Path::new(tmpdir).join(file)))
            .text()
            .to_owned();
        if !diagnostic.is_empty() {
            eprint!("{diagnostic}");
        }
    }
    if message.is_empty() {
        eprintln!(
            "**⚠ /implement Step 0 bootstrap failed at step={}. Aborting.**",
            if failure.step.is_empty() {
                "unknown"
            } else {
                &failure.step
            }
        );
    } else {
        eprintln!("{message}");
    }
    ExitCode::from(CONTRACT_FAILURE)
}

fn write_session_file(tmpdir: &str, name: &str, text: &str) -> Result<(), String> {
    write_session_text(tmpdir, name, text, 0o600)
}

fn read_regular_lossy(path: &Path) -> String {
    read_confined_bytes(path)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .unwrap_or_default()
}

fn read_regular_text(path: &Path) -> Result<String, String> {
    read_confined_bytes(path).map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
}

fn regular_file(path: &Path) -> bool {
    safe_regular_file_present(path).unwrap_or(false)
}

fn safe_regular_file_present(path: &Path) -> Result<bool, String> {
    if !path.is_absolute() {
        return Err(format!("{}: path must be absolute", path.display()));
    }
    if path.parent().is_none() {
        return Err(format!("{}: path has no parent", path.display()));
    }
    match fs::symlink_metadata(path) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(false),
        Err(error) => return Err(format!("{}: {error}", path.display())),
        Ok(_) => {}
    }
    confine_regular_read_checked(path).map(|_| true)
}

fn output_values(output: &ProcessOutput) -> BTreeMap<String, String> {
    parse_kv(&String::from_utf8_lossy(output.stdout()))
}

fn valid_issue(value: &str) -> bool {
    !value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit())
}

fn valid_difficulty(value: &str) -> bool {
    matches!(value, "TRIVIAL" | "MODERATE" | "HARD")
}

fn read_session_value(tmpdir: &str, file: &str, key: &str) -> String {
    read_session_value_from_path(&Path::new(tmpdir).join(file), key)
}

fn read_session_value_from_path(path: &Path, key: &str) -> String {
    first_kv_value(&read_regular_lossy(path), key, CrStrip::Suffix)
}

fn parse_kv(text: &str) -> BTreeMap<String, String> {
    KvDocument::parse(
        text,
        ParseOptions {
            cr_strip: CrStrip::Suffix,
            ..ParseOptions::legacy()
        },
    )
    .map_or_else(
        |_| BTreeMap::new(),
        |document| {
            document
                .select(DuplicatePolicy::Last)
                .into_iter()
                .filter(|(key, _)| {
                    !key.is_empty()
                        && key
                            .bytes()
                            .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_')
                })
                .collect()
        },
    )
}

fn single_line(value: &str) -> String {
    value.replace(['\n', '\r'], " ")
}

fn resolve_repo_root() -> Option<PathBuf> {
    for value in [
        std::env::var("CLAUDE_PROJECT_DIR").unwrap_or_default(),
        std::env::var("REPO_ROOT").unwrap_or_default(),
    ] {
        let root = PathBuf::from(value);
        if root.is_absolute() {
            return Some(root);
        }
    }
    let root = std::env::current_dir().ok()?;
    eprintln!("bootstrap invoke: REPO_ROOT missing; using ambient cwd fallback");
    Some(root)
}

#[cfg(test)]
mod tests {
    use super::{
        ContinuationFailure, append_force_bypass, bootstrap_next, coder_order_for_tier,
        emit_failure, normalize_1r_probe_output, phase_coder, read_regular_text,
        strip_plan_provenance_headers, valid_receipt_scope_drift,
    };
    use crate::bootstrap_commands::{BootstrapOptions, BootstrapState, InvokeMode};
    use std::{collections::BTreeMap, fs, process::ExitCode};

    fn test_options() -> BootstrapOptions {
        BootstrapOptions {
            mode: InvokeMode::Initial,
            issue_number: String::new(),
            forked_target: String::new(),
            merge_requested: String::new(),
            draft_requested: String::new(),
            no_admin_fallback: String::new(),
            no_logs_commit: String::new(),
            force_requested: String::new(),
            difficulty_override: String::new(),
            upstream_repo: String::new(),
            run_id: String::new(),
            preflight_tmpdir: String::new(),
            caller_env: String::new(),
            coder_opt: String::new(),
            non_interactive: String::new(),
            self_review_requested: String::new(),
            self_implement_requested: String::new(),
            skip_codex_probe: false,
            skip_cursor_probe: false,
        }
    }

    #[test]
    fn checkpoint_probe_normalizes_malformed_routing_and_keeps_phantom_advisories() {
        let (routing, advisory) = normalize_1r_probe_output(
            "ROUTE=unexpected\nCHECKPOINT_NEXT=continue\nPHANTOM_COUNT=1\nIGNORED=value\n",
            "probe diagnostics\n",
            7,
        );

        assert_eq!(routing.get("REBASE_RC").map(String::as_str), Some("7"));
        assert_eq!(routing.get("ROUTE").map(String::as_str), Some("bail"));
        assert_eq!(
            routing.get("CHECKPOINT_NEXT").map(String::as_str),
            Some("load-routing")
        );
        assert_eq!(
            routing.get("REBASE_OUTCOME").map(String::as_str),
            Some("failed")
        );
        assert!(
            routing
                .get("REBASE_ERROR")
                .is_some_and(|value| value.contains("probe diagnostics"))
        );
        assert_eq!(advisory, vec!["PHANTOM_COUNT=1"]);
    }

    #[test]
    fn checkpoint_probe_preserves_valid_conflict_route_and_fixes_next_directive() {
        let (routing, advisory) = normalize_1r_probe_output(
            "ROUTE=conflict\nCHECKPOINT_NEXT=unexpected\nREBASE_OUTCOME=conflict\n",
            "",
            1,
        );

        assert!(advisory.is_empty());
        assert_eq!(routing.get("ROUTE").map(String::as_str), Some("conflict"));
        assert_eq!(
            routing.get("CHECKPOINT_NEXT").map(String::as_str),
            Some("load-routing")
        );
        assert_eq!(
            routing.get("REBASE_OUTCOME").map(String::as_str),
            Some("conflict")
        );
        assert!(!routing.contains_key("REBASE_ERROR"));
    }

    #[test]
    fn coder_order_uses_difficulty_override_policy_and_role_default_fallback() {
        assert_eq!(
            coder_order_for_tier("TRIVIAL"),
            &["cursor", "codex", "claude"]
        );
        assert_eq!(
            coder_order_for_tier("MODERATE"),
            &["cursor", "codex", "claude"]
        );
        assert_eq!(coder_order_for_tier("HARD"), &["codex", "cursor", "claude"]);
        assert_eq!(coder_order_for_tier(""), &["codex", "cursor", "claude"]);
    }

    #[test]
    fn explicit_unavailable_coder_records_fallback_evidence() {
        let temporary = tempfile::tempdir().expect("temporary bootstrap session");
        let plan = temporary.path().join("plan.txt");
        let feature = temporary.path().join("feature-description.txt");
        fs::write(&plan, "plan\n").expect("write plan");
        fs::write(&feature, "feature\n").expect("write feature");
        let mut state = BootstrapState {
            implement_tmpdir: temporary.path().display().to_string(),
            plan_file: plan.display().to_string(),
            ..BootstrapState::default()
        };
        let mut options = test_options();
        options.coder_opt = "codex".to_owned();

        phase_coder(&mut state, &options);

        assert_eq!(state.coder, "claude");
        assert_eq!(state.coder_fallback, "true");
        assert!(
            fs::read_to_string(temporary.path().join("codex-unavailable-warning.txt"))
                .expect("read requested-coder warning")
                .contains("SELECTED=claude")
        );
        assert!(
            temporary
                .path()
                .join("coder-fallback-warning.txt")
                .is_file()
        );
    }

    #[test]
    fn valid_force_bypass_is_consumed_once() {
        let temporary = tempfile::tempdir().expect("temporary bootstrap session");
        let preflight = tempfile::tempdir().expect("temporary preflight");
        fs::write(
            preflight.path().join("force-bypass.log"),
            "BYPASS kind=missing-designed-prefix issue=8358\n",
        )
        .expect("write force bypass log");
        let state = BootstrapState {
            implement_tmpdir: temporary.path().display().to_string(),
            issue_number_resolved: "8358".to_owned(),
            ..BootstrapState::default()
        };
        let mut options = test_options();
        options.force_requested = "true".to_owned();
        options.preflight_tmpdir = preflight.path().display().to_string();

        assert!(append_force_bypass(&state, &options));
        assert!(
            temporary
                .path()
                .join(".force-bypass-log-consumed")
                .is_file()
        );
        assert!(append_force_bypass(&state, &options));
    }

    #[test]
    fn receipt_scope_drift_requires_bounded_generated_json_rows() {
        let row = serde_json::to_string("M\tREADME.md").expect("serialize JSON row");
        let valid = format!(
            "- **Preflight plan-receipt scope refresh**: semantic materiality passed.\n  - Receipt base: `{}`\n  - Reviewed target: `{}`\n  - Scope diff (JSON-quoted name-status rows):\n    ```text\n    {row}\n    ```\n",
            "a".repeat(40),
            "b".repeat(40),
        );
        assert!(valid_receipt_scope_drift(&valid));
        assert!(!valid_receipt_scope_drift(&valid.replace(&row, "```")));
        assert!(!valid_receipt_scope_drift(&valid.replacen('a', "A", 1)));
        let too_many_rows = valid.replacen(
            "    ```\n",
            &format!("{}    ```\n", format!("    {row}\n").repeat(128)),
            1,
        );
        assert!(!valid_receipt_scope_drift(&too_many_rows));
    }

    #[test]
    fn failure_steps_preserve_the_contract_exit_code() {
        for step in [
            "session-entry-gate",
            "session-setup",
            "get-issue-state",
            "issue-number-required-for-resume",
            "copy-plan",
            "gh-issue-view",
            "resume-plan-tail-sentinel",
            "create-branch",
            "write-session-env",
            "degraded-both-down-hard-fail",
            "force-bypass-log",
            "receipt-scope-drift-log",
            "unknown-step",
        ] {
            assert_eq!(
                emit_failure(&ContinuationFailure::new(step, "detail"), ""),
                ExitCode::from(2),
                "step={step}"
            );
        }
    }

    #[test]
    fn plan_materialization_removes_only_terminal_design_provenance() {
        let plan = concat!(
            "## Goal\n",
            "Keep this implementation detail.\n\n",
            "review_status: approved\n",
            "rounds_completed: 2\n",
            "difficulty: HARD\n",
            "diff_lines: 4\n",
        );

        assert_eq!(
            strip_plan_provenance_headers(plan),
            "## Goal\nKeep this implementation detail.\n\ndiff_lines: 4\n"
        );
    }

    #[test]
    fn plan_materialization_keeps_prose_and_fenced_metadata_outside_final_trailers() {
        let plan = concat!(
            "## Plan\n\n",
            "review_status: prose survives\n",
            "rounds_completed: prose survives\n\n",
            "```text\n",
            "review_status: fenced survives\n",
            "rounds_completed: fenced survives\n",
            "```\n\n",
            "review_status: complete\n",
            "rounds_completed: 5\n",
            "diff_added: 10\n",
            "diff_deleted: 2\n",
            "mechanical_churn: false\n",
            "diff_lines: 10\n",
        );

        let materialized = strip_plan_provenance_headers(plan);
        assert!(materialized.contains("review_status: prose survives"));
        assert!(materialized.contains("rounds_completed: prose survives"));
        assert!(materialized.contains("review_status: fenced survives"));
        assert!(materialized.contains("rounds_completed: fenced survives"));
        assert!(!materialized.contains("review_status: complete"));
        assert!(!materialized.contains("rounds_completed: 5"));
        assert!(materialized.contains("diff_added: 10"));
        assert!(materialized.contains("diff_lines: 10"));
    }

    #[test]
    fn plan_materialization_requires_terminal_metadata_block() {
        let plan = "review_status: complete\nrounds_completed: 2\ndiff_lines: 1\ntrailing prose\n";

        assert_eq!(strip_plan_provenance_headers(plan), plan);
    }

    #[test]
    fn bootstrap_next_routes_only_a_complete_checkpoint_to_step2() {
        let temporary = tempfile::tempdir().expect("temporary bootstrap session");
        let plan = temporary.path().join("plan.txt");
        fs::write(&plan, "plan\n").expect("write plan");
        fs::write(
            temporary.path().join("feature-description.txt"),
            "feature\n",
        )
        .expect("write feature description");
        let mut values = BTreeMap::from([
            (
                "IMPLEMENT_TMPDIR".to_owned(),
                temporary.path().display().to_string(),
            ),
            ("PLAN_FILE".to_owned(), plan.display().to_string()),
            ("coder".to_owned(), "claude".to_owned()),
            ("ROUTE".to_owned(), "continue".to_owned()),
        ]);

        assert_eq!(bootstrap_next(&values, true), "step2");
        values.insert("ROUTE".to_owned(), "conflict".to_owned());
        assert_eq!(bootstrap_next(&values, true), "rebase-routing");
        values.remove("PLAN_FILE");
        assert_eq!(bootstrap_next(&values, true), "cleanup");
    }

    #[cfg(unix)]
    #[test]
    fn session_reader_rejects_a_symlinked_input() {
        let temporary = tempfile::tempdir().expect("temporary bootstrap session");
        let target = temporary.path().join("target.txt");
        fs::write(&target, "trusted\n").expect("write target");
        let link = temporary.path().join("link.txt");
        std::os::unix::fs::symlink(&target, &link).expect("create symlink");

        assert!(read_regular_text(&link).is_err());
    }
}
