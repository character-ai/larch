//! Rust owner for the complete `ship pr` lifecycle (#8628).
//!
//! Fresh and resumed runs share one durable state machine. The owner prepares
//! and pushes the feature branch, evaluates the architectural and migration
//! gates, reconciles PR creation, waits for CI, delegates the separately owned
//! merge and finalize verbs, and verifies post-merge health. A merged or closed
//! PR is classified before any checkout or Git mutation (I-Ship-1).

use std::{
    collections::BTreeMap,
    env,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use larch_adapters::{
    FetchRequest, ForceWithLease, GitRef, GitRefspec, GitRemote, GixRepository, LsRemoteRequest,
    PushRequest, RebaseRequest,
    github::{GitHubOperationError, PullRequest, PullRequestSpec, PullRequestState},
};
use larch_core::{
    AssessmentKind, ChildEnvironment, DuplicatePolicy, Head, KvDocument, ParseOptions,
    RepositoryRead, Revision, ShipOutcome, ShipPrBody, ShipResult, ShipState, StatusOptions,
    compose_ship_pr_body, current_ship_assessment, ensure_under, guideline_active_exception,
    materialize, private_atomic_write, redact_outbound, ship_pr_title, validate_run_id,
    validate_ship_result_env,
};
use serde_json::Value;

use crate::{
    architectural_assessment_commands::LiveAssessmentGit,
    argparse_compat::{ParsedCommandLine, parse_required_with_help},
    git_command_runtime::GitCommandRuntime,
    github_repository_resolution::{remote_slug, repository_ref},
    github_service::with_github_service,
    implement_child_seam::{
        delegate_larch_with_environment, delegate_larch_with_options, delegate_merge_wait,
        delegate_python, verify_merge_wait,
    },
    implement_scope_disposition_commands::{ship_pr_disposition, validate_ship_disposition},
    ship_commands::validate_tmpdir,
};

const PROGRAM: &str = "cli.py";
const USAGE: &str = concat!(
    "usage: cli.py [-h] [--branch BRANCH] [--issue ISSUE] [--repo REPO]\n",
    "              [--run-id RUN_ID] [--tmpdir TMPDIR]\n",
    "              [--manifest-path MANIFEST_PATH] [--state-file STATE_FILE]\n",
    "              [--tool-label TOOL_LABEL] [--merge MERGE] [--draft DRAFT]\n",
    "              [--forked FORKED] [--repo-unavailable REPO_UNAVAILABLE]\n",
    "              [--no-admin-fallback NO_ADMIN_FALLBACK]\n",
    "              [--no-logs-commit [NO_LOGS_COMMIT]]\n",
    "              [--expected-session-id EXPECTED_SESSION_ID]\n",
    "              [--expected-tmpdir-basename-prefix EXPECTED_TMPDIR_BASENAME_PREFIX]\n",
    "              [--result-env-path RESULT_ENV_PATH]",
);
const HELP: &str = concat!(
    "usage: cli.py [-h] [--branch BRANCH] [--issue ISSUE] [--repo REPO]\n",
    "              [--run-id RUN_ID] [--tmpdir TMPDIR]\n",
    "              [--manifest-path MANIFEST_PATH] [--state-file STATE_FILE]\n",
    "              [--tool-label TOOL_LABEL] [--merge MERGE] [--draft DRAFT]\n",
    "              [--forked FORKED] [--repo-unavailable REPO_UNAVAILABLE]\n",
    "              [--no-admin-fallback NO_ADMIN_FALLBACK]\n",
    "              [--no-logs-commit [NO_LOGS_COMMIT]]\n",
    "              [--expected-session-id EXPECTED_SESSION_ID]\n",
    "              [--expected-tmpdir-basename-prefix EXPECTED_TMPDIR_BASENAME_PREFIX]\n",
    "              [--result-env-path RESULT_ENV_PATH]\n\n",
    "Run the Rust ship-pr driver\n\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --branch BRANCH\n  --issue ISSUE\n  --repo REPO\n  --run-id RUN_ID\n",
    "  --tmpdir TMPDIR\n  --manifest-path MANIFEST_PATH\n  --state-file STATE_FILE\n",
    "  --tool-label TOOL_LABEL\n  --merge MERGE\n  --draft DRAFT\n  --forked FORKED\n",
    "  --repo-unavailable REPO_UNAVAILABLE\n  --no-admin-fallback NO_ADMIN_FALLBACK\n",
    "  --no-logs-commit [NO_LOGS_COMMIT]\n  --expected-session-id EXPECTED_SESSION_ID\n",
    "  --expected-tmpdir-basename-prefix EXPECTED_TMPDIR_BASENAME_PREFIX\n",
    "  --result-env-path RESULT_ENV_PATH",
);
#[rustfmt::skip]
const OPTIONS: &[&str] = &[
    "--branch", "--issue", "--repo", "--run-id", "--tmpdir", "--manifest-path",
    "--state-file", "--tool-label", "--merge", "--draft", "--forked",
    "--repo-unavailable", "--no-admin-fallback", "--no-logs-commit",
    "--expected-session-id", "--expected-tmpdir-basename-prefix", "--result-env-path",
];
const DEFAULT_TEST_PLAN: &str = "- [ ] `make py-lint`\n- [ ] `make py-test`\n";
const MANIFEST_LIMIT: u64 = 1024 * 1024;
const CI_WAIT_SECONDS: u64 = 1_800;
const MERGE_WAIT_SECONDS: u64 = 7_500;
const MERGE_LOOP_LIMIT: u64 = 50;
const PHASE14_FLAG: &str = "ship-pr-rrr-after-phase14.flag";
const RESUME_PHASE: &str = "ship-pr-rrr-phase14";
const RESUME_CALLER: &str = "ship_pr_pre_push";

#[allow(clippy::struct_excessive_bools)] // Mirrors independent switches in the frozen CLI wire.
struct ShipPrContext {
    branch: String,
    issue: u64,
    repo: String,
    run_id: String,
    tmpdir: PathBuf,
    state_file: PathBuf,
    manifest: Option<PathBuf>,
    merge: bool,
    draft: bool,
    forked: bool,
    repo_unavailable: bool,
    no_admin_fallback: bool,
    no_logs_commit: bool,
    pr_title: String,
    summary: String,
    mermaid: String,
    test_plan: String,
    result_env: Option<PathBuf>,
    resume: ResumeState,
}

#[derive(Default)]
struct ResumeState {
    phase: String,
    resume_phase: String,
    caller_kind: String,
    pr_number: Option<u64>,
    pr_url: String,
    merge_result: String,
    iteration: u64,
    rebase_count: u64,
    fix_attempts: u64,
    transient_retries: u64,
}

struct AssessmentNotes {
    invariants: String,
    guidelines: String,
}

#[derive(Debug)]
enum DriverFailure {
    Result(Box<ShipResult>),
    Conflict { detail: String, files: String },
}

/// Run the Rust ship PR owner.
pub fn pr(arguments: &[OsString]) -> ExitCode {
    let normalized = normalize_optional_bool(arguments);
    let parsed =
        match parse_required_with_help(&normalized, PROGRAM, USAGE, HELP, OPTIONS, &[], &[]) {
            Ok(parsed) => parsed,
            Err(code) if code == ExitCode::SUCCESS => return code,
            Err(_) => {
                return emit(
                    &ShipResult {
                        outcome: ShipOutcome::InternalError,
                        detail: "argparse failed with exit 2".to_owned(),
                        ..ShipResult::default()
                    },
                    None,
                    None,
                );
            }
        };
    let context = match ShipPrContext::load(&parsed) {
        Ok(context) => context,
        Err(result) => return emit(&result, None, None),
    };
    if let Some(path) = context.result_env.as_deref()
        && let Err(error) = validate_ship_result_env(path, &context.tmpdir)
    {
        return emit(
            &internal(format!("invalid ship result env: {error}")),
            None,
            None,
        );
    }
    let (mut result, active_handoff) = match run(&context) {
        Ok(result) => (Box::new(result), false),
        Err(DriverFailure::Result(result)) => (result, false),
        Err(DriverFailure::Conflict { detail, files }) => {
            let updates = [
                ("PHASE", "rebase".to_owned()),
                ("RESUME_PHASE", "ship-pr-rrr-phase14".to_owned()),
                ("CALLER_KIND", "ship_pr_pre_push".to_owned()),
                ("CONFLICT_FILES", files),
                ("STALL_TRACKING", "true".to_owned()),
                ("STALL_STEP", "rebase-failed".to_owned()),
            ];
            if let Err(error) = patch_state(&context, &updates) {
                (internal(error), false)
            } else {
                (stalled(detail), true)
            }
        }
    };
    hydrate_result_identity(&context, &mut result);
    if result.outcome == ShipOutcome::Stalled && !active_handoff {
        let step = slug(&result.detail);
        let phase = state_value(&context, "PHASE");
        let merge_result = state_value(&context, "MERGE_RESULT");
        let mut updates = vec![
            ("STALL_TRACKING", "true".to_owned()),
            ("STALL_STEP", step),
            ("EXIT_CODE", "4".to_owned()),
        ];
        if !preserves_resume_phase(&phase, &merge_result) {
            updates.push(("PHASE", "stalled".to_owned()));
        }
        if let Err(error) = patch_state(&context, &updates) {
            result = internal(error);
        }
    }
    emit(
        &result,
        context.result_env.as_deref(),
        Some(&context.tmpdir),
    )
}

#[allow(clippy::too_many_lines)] // Fresh PR preparation and its state transitions are one transaction.
fn run(context: &ShipPrContext) -> Result<ShipResult, DriverFailure> {
    let repo_root = env::current_dir()
        .ok()
        .and_then(|path| fs::canonicalize(path).ok())
        .ok_or_else(|| DriverFailure::Result(stalled("cwd is not in a repo")))?;
    if let Some(number) = context.resume.pr_number {
        return run_resume(context, &repo_root, number);
    }
    run_fresh(context, &repo_root)
}

#[allow(clippy::too_many_lines)] // Fresh PR preparation and its state transitions are one transaction.
fn run_fresh(context: &ShipPrContext, repo_root: &Path) -> Result<ShipResult, DriverFailure> {
    validate_checkout(context, repo_root).map_err(DriverFailure::Result)?;
    let mut clear = terminal_clear_updates();
    clear.extend([
        ("PHASE", "pr-prep".to_owned()),
        ("EXIT_CODE", String::new()),
    ]);
    patch_state(context, &clear).map_err(|error| DriverFailure::Result(internal(error)))?;
    prepare_branch(context, repo_root)?;
    if context.resume.resume_phase == RESUME_PHASE && context.resume.caller_kind == RESUME_CALLER {
        patch_state(
            context,
            &[
                ("RESUME_PHASE", String::new()),
                ("CALLER_KIND", String::new()),
                ("CONFLICT_FILES", String::new()),
            ],
        )
        .map_err(|error| DriverFailure::Result(internal(error)))?;
    }
    patch_state(context, &[("PHASE", "assessments".to_owned())])
        .map_err(|error| DriverFailure::Result(internal(error)))?;
    let assessments = assessment_gate(context, repo_root)?;
    if context.repo_unavailable {
        patch_done(context).map_err(|error| DriverFailure::Result(internal(error)))?;
        return Ok(ShipResult {
            detail: "local-only".to_owned(),
            ..ShipResult::default()
        });
    }
    let gate = validate_ship_disposition(&context.tmpdir, repo_root, context.manifest.as_deref())
        .map_err(|error| DriverFailure::Result(stalled(error)))?;
    if !gate.ok {
        return Err(DriverFailure::Result(Box::new(ShipResult {
            outcome: ShipOutcome::NeedsUserInput,
            needs_user_reason: "scope-disposition".to_owned(),
            detail: gate.reason,
            ..ShipResult::default()
        })));
    }
    governance_gate(context, repo_root)?;
    let (title, body) = pull_request_content(context, repo_root, &assessments)?;
    patch_state(context, &[("PHASE", "pr-create".to_owned())])
        .map_err(|error| DriverFailure::Result(internal(error)))?;
    push_branch(context, repo_root)?;
    let (number, created) = ensure_pull_request(context, &title, &body)?;
    let number_i64 = i64::try_from(number)
        .map_err(|_| DriverFailure::Result(internal("pull request number exceeds result wire")))?;
    let url = format!("https://github.com/{}/pull/{number}", context.repo);
    let phase = if context.merge && !context.draft && !context.forked {
        "ci-initial"
    } else {
        "done"
    };
    let mut updates = vec![
        ("PHASE", phase.to_owned()),
        ("PR_NUMBER", number.to_string()),
        ("PR_URL", url.clone()),
        ("PR_TITLE", title),
        ("PR_CLOSED", "false".to_owned()),
    ];
    if phase == "done" {
        updates.extend(terminal_clear_updates());
    }
    patch_state(context, &updates).map_err(|error| DriverFailure::Result(internal(error)))?;
    let result = ShipResult {
        pr_number: Some(number_i64),
        pr_url: url,
        detail: if created { "created" } else { "existing" }.to_owned(),
        ..ShipResult::default()
    };
    if phase == "done" {
        Ok(result)
    } else {
        run_merge_loop(context, repo_root, number, result.pr_url)
    }
}

#[allow(clippy::too_many_lines)] // Resume branches mirror the durable phase wire one for one.
fn run_resume(
    context: &ShipPrContext,
    repo_root: &Path,
    number: u64,
) -> Result<ShipResult, DriverFailure> {
    let pull_request = read_pull_request(context, number)?;
    let url = format!("https://github.com/{}/pull/{number}", context.repo);
    if !context.resume.pr_url.is_empty() && context.resume.pr_url != url {
        return Err(DriverFailure::Result(stalled(
            "persisted pull request URL does not match repository identity",
        )));
    }
    if pull_request.base_ref() != "main" {
        return Err(DriverFailure::Result(stalled(
            "pull request base does not match main",
        )));
    }
    if pull_request.merged() {
        if context.resume.phase == "emergency-repair" {
            let repair_branch = state_value(context, "EMERGENCY_REPAIR_BRANCH");
            let repair_head = state_value(context, "MAIN_REPAIR_HEAD");
            if repair_branch.is_empty() && !repair_head.is_empty() {
                if let Some(result) = main_health_gate(context, Some(&repair_head), true)? {
                    return Err(DriverFailure::Result(Box::new(result)));
                }
                return finalize_postmerge(context, number, url, effective_merge_result(context));
            }
            return Err(DriverFailure::Result(Box::new(ShipResult {
                outcome: ShipOutcome::NeedsUserInput,
                needs_user_reason: "postmerge-main-ci-fail".to_owned(),
                failed_run_id: state_value(context, "MAIN_REPAIR_RUN_ID"),
                pr_number: result_number(number)?,
                pr_url: url,
                merge_result: effective_merge_result(context),
                detail: "post-merge emergency repair remains in progress".to_owned(),
                original_branch_forbidden: "true".to_owned(),
                main_repair_run_id: state_value(context, "MAIN_REPAIR_RUN_ID"),
                main_repair_head: state_value(context, "MAIN_REPAIR_HEAD"),
                ..ShipResult::default()
            })));
        }
        if context.resume.phase == "done" {
            if context.merge && !context.draft {
                return finalize_postmerge(context, number, url, effective_merge_result(context));
            }
            return Ok(ShipResult {
                pr_number: result_number(number)?,
                pr_url: url,
                merge_result: effective_merge_result(context),
                detail: "already-complete".to_owned(),
                ..ShipResult::default()
            });
        }
        return postmerge(context, &pull_request, number, url);
    }
    if pull_request.state() == PullRequestState::Closed {
        return Err(DriverFailure::Result(stalled(
            "PR is closed but was not merged; refusing pre-merge mutations",
        )));
    }
    if pull_request.head_ref() != context.branch {
        let detail = format!(
            "PR head {} does not match checkout {}",
            pull_request.head_ref(),
            context.branch
        );
        patch_needs_user(context, "checkout-mismatch", &detail, "pr-resume")?;
        return Err(DriverFailure::Result(Box::new(ShipResult {
            outcome: ShipOutcome::NeedsUserInput,
            needs_user_reason: "checkout-mismatch".to_owned(),
            detail,
            ..ShipResult::default()
        })));
    }
    if context.resume.merge_result == "queued" {
        return finish_queued_merge(context, number, url);
    }
    validate_checkout(context, repo_root).map_err(DriverFailure::Result)?;
    let phase14 = context.tmpdir.join(PHASE14_FLAG);
    let active_handoff =
        context.resume.resume_phase == RESUME_PHASE && context.resume.caller_kind == RESUME_CALLER;
    if context.resume.resume_phase == RESUME_PHASE && !active_handoff {
        return Err(DriverFailure::Result(Box::new(ShipResult {
            outcome: ShipOutcome::NeedsUserInput,
            needs_user_reason: "unsupported-rebase-continuation".to_owned(),
            pr_number: result_number(number)?,
            pr_url: url,
            detail: "ship driver cannot resume the unresolved rebase-conflict continuation"
                .to_owned(),
            ..ShipResult::default()
        })));
    }
    if active_handoff && !safe_regular(&phase14) {
        private_atomic_write(
            &phase14,
            "RESUME_PHASE=ship-pr-rrr-phase14\n",
            &context.tmpdir,
        )
        .map_err(|error| DriverFailure::Result(internal(error.to_string())))?;
    }
    if safe_regular(&phase14) {
        rebase_for_merge(context, repo_root, number, context.resume.rebase_count)?;
        fs::remove_file(&phase14).map_err(|error| {
            DriverFailure::Result(internal(format!("cannot clear phase14 flag: {error}")))
        })?;
    } else {
        reconcile_open_pull_request(context, repo_root, number)?;
    }
    if !context.merge
        || context.draft
        || context.forked
        || context.repo_unavailable
        || pull_request.draft()
    {
        patch_done(context).map_err(|error| DriverFailure::Result(internal(error)))?;
        return Ok(ShipResult {
            pr_number: result_number(number)?,
            pr_url: url,
            detail: "existing".to_owned(),
            ..ShipResult::default()
        });
    }
    run_merge_loop(context, repo_root, number, url)
}

#[allow(clippy::too_many_lines, clippy::cognitive_complexity)] // Each branch is a frozen CI/merge action.
fn run_merge_loop(
    context: &ShipPrContext,
    repo_root: &Path,
    number: u64,
    url: String,
) -> Result<ShipResult, DriverFailure> {
    let mut iteration = state_counter(context, "ITERATION", context.resume.iteration);
    let mut rebase_count = state_counter(context, "REBASE_COUNT", context.resume.rebase_count);
    let fix_attempts = state_counter(context, "FIX_ATTEMPTS", context.resume.fix_attempts);
    loop {
        if iteration > MERGE_LOOP_LIMIT {
            return Err(DriverFailure::Result(stalled(
                "merge loop iteration cap reached",
            )));
        }
        #[rustfmt::skip]
        let progress = [
            ("PHASE", "ci-initial".to_owned()), ("ITERATION", iteration.to_string()),
            ("REBASE_COUNT", rebase_count.to_string()), ("FIX_ATTEMPTS", fix_attempts.to_string()),
            ("TRANSIENT_RETRIES", context.resume.transient_retries.to_string()),
        ];
        patch_state(context, &progress).map_err(|error| DriverFailure::Result(internal(error)))?;
        let fields = wait_for_ci(context, number, iteration, rebase_count, fix_attempts)?;
        match required_field(&fields, "ACTION")? {
            "already_merged" => {
                let pull_request = read_pull_request(context, number)?;
                if !pull_request.merged() {
                    return Err(DriverFailure::Result(stalled(
                        "CI reported a merge that the pull-request read did not confirm",
                    )));
                }
                return postmerge(context, &pull_request, number, url);
            }
            "rebase" | "rebase_then_evaluate" => {
                rebase_for_merge(context, repo_root, number, rebase_count)?;
                rebase_count = rebase_count.saturating_add(1);
                iteration = iteration.saturating_add(1);
            }
            "wait" => iteration = iteration.saturating_add(1),
            "evaluate_failure" => {
                return ci_failure(
                    context,
                    number,
                    url,
                    fields
                        .get("FAILED_RUN_ID")
                        .map(String::as_str)
                        .unwrap_or_default(),
                );
            }
            "merge" => {
                if let Some(result) = main_health_gate(context, None, false)? {
                    return Err(DriverFailure::Result(Box::new(result)));
                }
                match submit_merge(context, number)? {
                    MergeDisposition::Merged(result) => {
                        let pull_request = read_pull_request(context, number)?;
                        if !pull_request.merged() {
                            return Err(DriverFailure::Result(stalled(
                                "merge mutation was not confirmed by a typed read-back",
                            )));
                        }
                        patch_state(context, &[("MERGE_RESULT", result)])
                            .map_err(|error| DriverFailure::Result(internal(error)))?;
                        return postmerge(context, &pull_request, number, url);
                    }
                    MergeDisposition::Queued => {
                        patch_state(
                            context,
                            &[
                                ("PHASE", "merge".to_owned()),
                                ("MERGE_RESULT", "queued".to_owned()),
                                ("PR_CLOSED", "false".to_owned()),
                            ],
                        )
                        .map_err(|error| DriverFailure::Result(internal(error)))?;
                        return finish_queued_merge(context, number, url);
                    }
                    MergeDisposition::Rebase => {
                        rebase_for_merge(context, repo_root, number, rebase_count)?;
                        rebase_count = rebase_count.saturating_add(1);
                        iteration = iteration.saturating_add(1);
                    }
                    MergeDisposition::Retry => {
                        iteration = iteration.saturating_add(1);
                        if iteration.saturating_sub(context.resume.iteration) >= 3 {
                            return Err(DriverFailure::Result(stalled(
                                "merge CI remained not ready after three reconciliations",
                            )));
                        }
                    }
                    MergeDisposition::NeedsReview(detail) => {
                        patch_needs_user(context, "review-required", &detail, "merge")?;
                        return Err(DriverFailure::Result(Box::new(ShipResult {
                            outcome: ShipOutcome::NeedsUserInput,
                            needs_user_reason: "review-required".to_owned(),
                            pr_number: result_number(number)?,
                            pr_url: url,
                            detail,
                            ..ShipResult::default()
                        })));
                    }
                    MergeDisposition::Stalled(detail, result) => {
                        let durable_result = match result.as_str() {
                            "version_already_published"
                            | "policy_denied"
                            | "admin_failed"
                            | "error" => result.clone(),
                            _ => "error".to_owned(),
                        };
                        patch_state(context, &[("MERGE_RESULT", durable_result)])
                            .map_err(|error| DriverFailure::Result(internal(error)))?;
                        return Err(DriverFailure::Result(Box::new(ShipResult {
                            outcome: ShipOutcome::Stalled,
                            merge_result: result,
                            detail,
                            ..ShipResult::default()
                        })));
                    }
                }
            }
            "bail" => {
                let reason = fields
                    .get("BAIL_REASON")
                    .map(String::as_str)
                    .filter(|value| !value.is_empty())
                    .unwrap_or("ci-wait-bailed");
                if reason == "no-ci-checks-observed"
                    && (fields.get("BEHIND_COUNT").is_some_and(|value| value != "0")
                        || fields.get("CONFLICTED").is_some_and(|value| truthy(value)))
                {
                    private_atomic_write(
                        &context.tmpdir.join(PHASE14_FLAG),
                        "RESUME_PHASE=ship-pr-rrr-phase14\nREASON=no-ci-checks-observed\n",
                        &context.tmpdir,
                    )
                    .map_err(|error| DriverFailure::Result(internal(error.to_string())))?;
                }
                if reason == "fix-attempts-exhausted" {
                    patch_needs_user(context, reason, reason, "ci-initial")?;
                    return Err(DriverFailure::Result(Box::new(escalation_handoff(
                        ShipResult {
                            outcome: ShipOutcome::NeedsUserInput,
                            needs_user_reason: reason.to_owned(),
                            pr_number: result_number(number)?,
                            pr_url: url,
                            detail: reason.to_owned(),
                            ..ShipResult::default()
                        },
                        reason,
                        "ci-initial",
                    ))));
                }
                return Err(DriverFailure::Result(stalled(reason)));
            }
            action => {
                return Err(DriverFailure::Result(internal(format!(
                    "unsupported CI action: {action}"
                ))));
            }
        }
    }
}

#[derive(Debug, Eq, PartialEq)]
enum MergeDisposition {
    Merged(String),
    Queued,
    Rebase,
    Retry,
    NeedsReview(String),
    Stalled(String, String),
}

fn submit_merge(context: &ShipPrContext, number: u64) -> Result<MergeDisposition, DriverFailure> {
    let mut arguments = vec![
        "merge".into(),
        "pr".into(),
        "--pr".into(),
        number.to_string().into(),
        "--repo".into(),
        context.repo.clone().into(),
    ];
    if context.no_admin_fallback {
        arguments.push("--no-admin-fallback".into());
    }
    let output = delegate_larch_with_options(&arguments, &[], Duration::from_secs(600))
        .map_err(|error| DriverFailure::Result(internal(error)))?;
    let fields = output_fields(output.stdout())?;
    classify_merge(&fields).map_err(|error| DriverFailure::Result(internal(error)))
}

fn classify_merge(fields: &BTreeMap<String, String>) -> Result<MergeDisposition, String> {
    let result = fields
        .get("MERGE_RESULT")
        .map(String::as_str)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| "missing result field: MERGE_RESULT".to_owned())?;
    let detail = safe_detail(fields.get("ERROR").map(String::as_str).unwrap_or_default());
    Ok(match result {
        "merged" | "admin_merged" | "already_merged" => MergeDisposition::Merged(result.to_owned()),
        "queued" => MergeDisposition::Queued,
        "main_advanced" => MergeDisposition::Rebase,
        "ci_not_ready" => MergeDisposition::Retry,
        "review_required" => MergeDisposition::NeedsReview(if detail.is_empty() {
            "PR requires approving review".to_owned()
        } else {
            detail
        }),
        other => MergeDisposition::Stalled(
            if detail.is_empty() {
                format!("merge did not complete: {other}")
            } else {
                detail
            },
            other.to_owned(),
        ),
    })
}

fn finish_queued_merge(
    context: &ShipPrContext,
    number: u64,
    url: String,
) -> Result<ShipResult, DriverFailure> {
    let output = delegate_merge_wait(
        number,
        &context.repo,
        Duration::from_secs(MERGE_WAIT_SECONDS),
    )
    .map_err(|error| DriverFailure::Result(stalled(error)))?;
    verify_merge_wait(&output).map_err(|error| DriverFailure::Result(stalled(error)))?;
    let pull_request = read_pull_request(context, number)?;
    if !pull_request.merged() {
        return Err(DriverFailure::Result(stalled(
            "merge queue completion was not confirmed by a typed read-back",
        )));
    }
    patch_state(context, &[("MERGE_RESULT", "merged".to_owned())])
        .map_err(|error| DriverFailure::Result(internal(error)))?;
    postmerge(context, &pull_request, number, url)
}

fn rebase_for_merge(
    context: &ShipPrContext,
    repo_root: &Path,
    number: u64,
    rebase_count: u64,
) -> Result<(), DriverFailure> {
    patch_state(context, &[("PHASE", "rebase".to_owned())])
        .map_err(|error| DriverFailure::Result(internal(error)))?;
    refresh_run_log(context, false);
    prepare_branch(context, repo_root)?;
    push_branch(context, repo_root)?;
    reconcile_open_pull_request(context, repo_root, number)?;
    patch_state(
        context,
        &[
            ("PHASE", "ci-initial".to_owned()),
            ("REBASE_COUNT", rebase_count.saturating_add(1).to_string()),
            ("RESUME_PHASE", String::new()),
            ("CALLER_KIND", String::new()),
            ("CONFLICT_FILES", String::new()),
        ],
    )
    .map_err(|error| DriverFailure::Result(internal(error)))
}

fn reconcile_open_pull_request(
    context: &ShipPrContext,
    repo_root: &Path,
    expected_number: u64,
) -> Result<(), DriverFailure> {
    patch_state(context, &[("PHASE", "assessments".to_owned())])
        .map_err(|error| DriverFailure::Result(internal(error)))?;
    let assessments = assessment_gate(context, repo_root)?;
    let gate = validate_ship_disposition(&context.tmpdir, repo_root, context.manifest.as_deref())
        .map_err(|error| DriverFailure::Result(stalled(error)))?;
    if !gate.ok {
        return Err(DriverFailure::Result(Box::new(ShipResult {
            outcome: ShipOutcome::NeedsUserInput,
            needs_user_reason: "scope-disposition".to_owned(),
            detail: gate.reason,
            ..ShipResult::default()
        })));
    }
    governance_gate(context, repo_root)?;
    let (title, body) = pull_request_content(context, repo_root, &assessments)?;
    let (number, _created) = ensure_pull_request(context, &title, &body)?;
    if number != expected_number {
        return Err(DriverFailure::Result(stalled(
            "open PR reconciliation changed pull request identity",
        )));
    }
    let mut updates = terminal_clear_updates();
    updates.extend([
        ("PR_CLOSED", "false".to_owned()),
        ("PR_NUMBER", number.to_string()),
        (
            "PR_URL",
            format!("https://github.com/{}/pull/{number}", context.repo),
        ),
        ("PR_TITLE", title),
        ("MERGE_RESULT", String::new()),
    ]);
    patch_state(context, &updates).map_err(|error| DriverFailure::Result(internal(error)))
}

fn wait_for_ci(
    context: &ShipPrContext,
    number: u64,
    iteration: u64,
    rebase_count: u64,
    fix_attempts: u64,
) -> Result<BTreeMap<String, String>, DriverFailure> {
    let startup_deadline = if iteration == 0 && rebase_count == 0 && fix_attempts == 0 {
        "300"
    } else {
        "0"
    };
    let base_remote = if context.forked { "upstream" } else { "origin" };
    #[rustfmt::skip]
    let arguments = vec![
        "ci".into(), "wait".into(), "--pr".into(), number.to_string().into(),
        "--repo".into(), context.repo.clone().into(), "--base-remote".into(), base_remote.into(),
        "--base-ref".into(), "main".into(), "--empty-checks-grace".into(), "0".into(),
        "--empty-checks-startup-deadline".into(), startup_deadline.into(),
        "--iteration".into(), iteration.to_string().into(), "--rebase-count".into(), rebase_count.to_string().into(),
        "--fix-attempts".into(), fix_attempts.to_string().into(), "--timeout".into(), CI_WAIT_SECONDS.to_string().into(),
    ];
    let output = delegate_larch_with_options(
        &arguments,
        &[early_tmpdir_environment(context)],
        Duration::from_secs(CI_WAIT_SECONDS + 180),
    )
    .map_err(|error| DriverFailure::Result(stalled(error)))?;
    if !output.status().success() {
        return Err(DriverFailure::Result(stalled(
            "CI wait command exited without a verdict",
        )));
    }
    let fields = output_fields(output.stdout())?;
    for key in [
        "ACTION",
        "CI_STATUS",
        "BEHIND_COUNT",
        "CONFLICTED",
        "FAILED_RUN_ID",
        "BAIL_REASON",
        "ITERATION",
        "ELAPSED",
    ] {
        if !fields.contains_key(key) {
            return Err(DriverFailure::Result(internal(format!(
                "CI wait result is missing {key}"
            ))));
        }
    }
    Ok(fields)
}

fn ci_failure(
    context: &ShipPrContext,
    number: u64,
    url: String,
    failed_run_id: &str,
) -> Result<ShipResult, DriverFailure> {
    let reason = "first-fixer-non-health";
    #[rustfmt::skip]
    let failure = [
        ("PHASE", "stalled".to_owned()), ("STALL_TRACKING", "true".to_owned()),
        ("STALL_STEP", reason.to_owned()), ("BAIL_REASON", reason.to_owned()),
        ("BAIL_NEEDS_USER_INPUT", "true".to_owned()), ("FAILED_RUN_ID", failed_run_id.to_owned()),
        ("EXIT_CODE", "3".to_owned()),
    ];
    patch_state(context, &failure).map_err(|error| DriverFailure::Result(internal(error)))?;
    let mut result = ShipResult {
        outcome: ShipOutcome::NeedsUserInput,
        needs_user_reason: reason.to_owned(),
        failed_run_id: failed_run_id.to_owned(),
        pr_number: result_number(number)?,
        pr_url: url,
        detail: reason.to_owned(),
        ..ShipResult::default()
    };
    if !failed_run_id.is_empty() && failed_run_id.bytes().all(|byte| byte.is_ascii_digit()) {
        let output_path = context.tmpdir.join(format!("ci-errors-{failed_run_id}.md"));
        let output = delegate_larch_with_environment(
            &[
                "ci".into(),
                "distill-log".into(),
                "--run-id".into(),
                failed_run_id.into(),
                "--repo".into(),
                context.repo.clone().into(),
                "--output".into(),
                output_path.as_os_str().into(),
            ],
            &[early_tmpdir_environment(context)],
        );
        if let Ok(output) = output {
            let fields = output_fields(output.stdout()).unwrap_or_default();
            result.failed_jobs_count = fields
                .get("FAILED_JOBS_COUNT")
                .and_then(|value| value.parse::<i64>().ok())
                .unwrap_or(0);
            if output.status().success() && fields.get("STATUS").map(String::as_str) == Some("ok") {
                result.ci_errors_file = output_path.display().to_string();
            } else {
                result.ci_errors_distill_class = fields
                    .get("BAIL_CLASS")
                    .cloned()
                    .unwrap_or_else(|| "distill-failed".to_owned());
            }
        } else {
            "distill-exception".clone_into(&mut result.ci_errors_distill_class);
        }
    }
    Ok(escalation_handoff(result, reason, "ci-initial"))
}

fn postmerge(
    context: &ShipPrContext,
    pull_request: &PullRequest,
    number: u64,
    url: String,
) -> Result<ShipResult, DriverFailure> {
    if !pull_request.merged() || pull_request.number() != number {
        return Err(DriverFailure::Result(stalled(
            "postmerge requires a confirmed merged pull request",
        )));
    }
    let merge_result = effective_merge_result(context);
    let mut updates = terminal_clear_updates();
    updates.extend([
        ("PHASE", "postmerge-push-watch".to_owned()),
        ("PR_CLOSED", "true".to_owned()),
        ("PR_NUMBER", number.to_string()),
        ("PR_URL", url.clone()),
        ("MERGE_RESULT", merge_result.clone()),
    ]);
    patch_state(context, &updates).map_err(|error| DriverFailure::Result(internal(error)))?;
    if let Some(result) = main_health_gate(context, pull_request.merge_commit_oid(), true)? {
        return Err(DriverFailure::Result(Box::new(result)));
    }
    finalize_postmerge(context, number, url, merge_result)
}

fn finalize_postmerge(
    context: &ShipPrContext,
    number: u64,
    url: String,
    merge_result: String,
) -> Result<ShipResult, DriverFailure> {
    private_atomic_write(
        &context.tmpdir.join("post-merge-sentinel"),
        &format!("MERGE_RESULT={merge_result}\n"),
        &context.tmpdir,
    )
    .map_err(|error| DriverFailure::Result(internal(error.to_string())))?;
    let bail_file = context.tmpdir.join("final-bail-reason.txt");
    private_atomic_write(&bail_file, "", &context.tmpdir)
        .map_err(|error| DriverFailure::Result(internal(error.to_string())))?;
    let output = delegate_python(
        vec![
            "implement-finalize".into(),
            "postmerge".into(),
            "--state-file".into(),
            context.state_file.as_os_str().into(),
            "--implement-tmpdir".into(),
            context.tmpdir.as_os_str().into(),
            "--final-bail-reason-file".into(),
            bail_file.as_os_str().into(),
        ],
        Duration::from_secs(900),
    )
    .map_err(|error| DriverFailure::Result(stalled(error)))?;
    let fields = output_fields(output.stdout())?;
    if !output.status().success() || fields.get("OUTCOME").map(String::as_str) != Some("OK") {
        let detail = fields
            .get("FINALIZE_WARNINGS")
            .filter(|value| !value.is_empty())
            .cloned()
            .or_else(|| fields.get("STATUS").cloned())
            .unwrap_or_else(|| "postmerge finalization failed".to_owned());
        return Err(DriverFailure::Result(stalled(detail)));
    }
    patch_done(context).map_err(|error| DriverFailure::Result(internal(error)))?;
    refresh_run_log(context, true);
    Ok(ShipResult {
        pr_number: result_number(number)?,
        pr_url: url,
        merge_result,
        detail: fields.get("STATUS").cloned().unwrap_or_default(),
        ..ShipResult::default()
    })
}

#[allow(clippy::too_many_lines)] // Pre- and post-merge outcomes share one fail-closed health classifier.
fn main_health_gate(
    context: &ShipPrContext,
    merged_commit: Option<&str>,
    postmerge: bool,
) -> Result<Option<ShipResult>, DriverFailure> {
    if !safe_regular(&context.tmpdir.join("preflight-tmpdir.env")) {
        return Ok(None);
    }
    if !safe_regular(&context.tmpdir.join("main-health.env")) {
        return Err(DriverFailure::Result(stalled(
            "missing main-health.env; cannot verify default-branch CI health",
        )));
    }
    let commit = resolve_main_health_commit(merged_commit, postmerge)?;
    #[rustfmt::skip]
    let mut arguments = vec![
        "ci".into(), "main-health".into(), "--repo".into(), context.repo.clone().into(),
        "--base-ref".into(), "main".into(), "--commit".into(), commit.clone().into(), "--wait".into(),
    ];
    if postmerge && context.resume.transient_retries > 0 {
        arguments.push("--skip-flap-check".into());
    }
    let output = delegate_larch_with_options(
        &arguments,
        &[early_tmpdir_environment(context)],
        Duration::from_secs(1_000),
    )
    .map_err(|error| DriverFailure::Result(stalled(error)))?;
    let fields = output_fields(output.stdout())?;
    let status = fields.get("MAIN_CI_STATUS").map_or("error", String::as_str);
    if output.status().success() && matches!(status, "pass" | "skip") {
        return Ok(None);
    }
    let failed_run_id = fields
        .get("MAIN_FAILED_RUN_ID")
        .cloned()
        .unwrap_or_default();
    let health_head = fields
        .get("MAIN_HEALTH_HEAD_SHA")
        .filter(|value| valid_oid(value))
        .cloned()
        .unwrap_or(commit);
    let detail = safe_detail(
        fields
            .get("MAIN_HEALTH_DETAIL")
            .map(String::as_str)
            .unwrap_or_default(),
    );
    if status == "fail" {
        if !postmerge && main_health_repair_covers(context, &failed_run_id, &health_head) {
            return Ok(None);
        }
        if postmerge
            && !failed_run_id.is_empty()
            && failed_run_id.bytes().all(|byte| byte.is_ascii_digit())
            && context.resume.transient_retries == 0
            && let Some(result) =
                rerun_postmerge_failure(context, &failed_run_id, &health_head, &detail)?
        {
            return Ok(Some(result));
        }
        let reason = if postmerge {
            "postmerge-main-ci-fail"
        } else {
            "main-ci-fail"
        };
        let step = if postmerge {
            "postmerge-push-watch"
        } else {
            "main-ci"
        };
        patch_needs_user(context, reason, &detail, step)?;
        if postmerge {
            #[rustfmt::skip]
            let repair = [
                ("PHASE", "emergency-repair".to_owned()), ("ORIGINAL_BRANCH_FORBIDDEN", "true".to_owned()),
                ("MAIN_REPAIR_RUN_ID", failed_run_id.clone()), ("MAIN_REPAIR_HEAD", health_head.clone()),
                ("MAIN_HEALTH_HEAD_SHA", health_head.clone()), ("MAIN_HEALTH_REPAIR_COMMITTED", "false".to_owned()),
                ("MAIN_HEALTH_REPAIR_FAILED_RUN_ID", failed_run_id.clone()),
                ("MAIN_HEALTH_REPAIR_BASE_SHA", health_head.clone()), ("MAIN_HEALTH_REPAIR_HEAD", health_head.clone()),
            ];
            patch_state(context, &repair)
                .map_err(|error| DriverFailure::Result(internal(error)))?;
        }
        let recovery_value = |value: &str| {
            if postmerge {
                value.to_owned()
            } else {
                String::new()
            }
        };
        #[rustfmt::skip]
        let result = ShipResult {
            outcome: ShipOutcome::NeedsUserInput,
            needs_user_reason: reason.to_owned(),
            failed_run_id: failed_run_id.clone(),
            pr_number: state_value(context, "PR_NUMBER").parse::<i64>().ok(),
            pr_url: state_value(context, "PR_URL"),
            merge_result: effective_merge_result(context),
            detail: if detail.is_empty() { format!("default-branch CI health is {status}") } else { detail },
            main_health_head_sha: health_head.clone(),
            main_health_repair_committed: recovery_value("false"),
            main_health_repair_failed_run_id: recovery_value(&failed_run_id),
            main_health_repair_base_sha: recovery_value(&health_head),
            main_health_repair_head: recovery_value(&health_head),
            original_branch_forbidden: recovery_value("true"),
            main_repair_run_id: recovery_value(&failed_run_id),
            main_repair_head: recovery_value(&health_head),
            ..ShipResult::default()
        };
        return Ok(Some(if postmerge {
            result
        } else {
            escalation_handoff(result, reason, "main-ci")
        }));
    }
    Err(DriverFailure::Result(stalled(if detail.is_empty() {
        format!("default-branch CI health is {status}")
    } else {
        detail
    })))
}

fn resolve_main_health_commit(
    merged_commit: Option<&str>,
    postmerge: bool,
) -> Result<String, DriverFailure> {
    if let Some(commit) = merged_commit.filter(|commit| !commit.is_empty()) {
        return Ok(commit.to_owned());
    }
    let repo_root = env::current_dir()
        .ok()
        .and_then(|path| fs::canonicalize(path).ok())
        .ok_or_else(|| DriverFailure::Result(stalled("cwd is not in a repo")))?;
    let runtime = GitCommandRuntime::for_repository(&repo_root)
        .map_err(|error| DriverFailure::Result(internal(error)))?;
    runtime
        .runtime
        .block_on(
            runtime.git_cli().fetch(
                FetchRequest {
                    remote: GitRemote::new("origin")
                        .map_err(|error| DriverFailure::Result(stalled(error.to_string())))?,
                    refspec: Some(
                        GitRefspec::new("main")
                            .map_err(|error| DriverFailure::Result(stalled(error.to_string())))?,
                    ),
                    quiet: true,
                    no_tags: false,
                    mode: larch_adapters::FetchMode::Standard,
                },
                &runtime.cancellation,
            ),
        )
        .map_err(|_| {
            DriverFailure::Result(stalled(if postmerge {
                "post-merge push watch could not refresh origin/main"
            } else {
                "pre-merge main-health gate could not refresh origin/main"
            }))
        })?;
    GixRepository::open(&repo_root)
        .and_then(|repository| repository.resolve_revision(&Revision::new(b"origin/main")))
        .map(|commit| commit.to_hex())
        .map_err(|_| {
            DriverFailure::Result(stalled(if postmerge {
                "post-merge push watch could not resolve merged main HEAD"
            } else {
                "pre-merge main-health gate could not resolve origin/main HEAD"
            }))
        })
}

fn rerun_postmerge_failure(
    context: &ShipPrContext,
    failed_run_id: &str,
    commit: &str,
    detail: &str,
) -> Result<Option<ShipResult>, DriverFailure> {
    #[rustfmt::skip]
    let arguments = [
        "ci".into(), "rerun-failed".into(), "--run-id".into(), failed_run_id.into(),
        "--repo".into(), context.repo.clone().into(),
    ];
    let Ok(output) =
        delegate_larch_with_environment(&arguments, &[early_tmpdir_environment(context)])
    else {
        return Ok(None);
    };
    let fields = output_fields(output.stdout()).unwrap_or_default();
    if fields
        .get("RERUN_SUBMITTED")
        .is_some_and(|value| truthy(value))
    {
        #[rustfmt::skip]
        let rerun = [
            ("PHASE", "postmerge-push-watch".to_owned()), ("TRANSIENT_RETRIES", "1".to_owned()),
            ("MAIN_REPAIR_RUN_ID", failed_run_id.to_owned()), ("MAIN_REPAIR_HEAD", commit.to_owned()),
            ("MAIN_HEALTH_HEAD_SHA", commit.to_owned()), ("MAIN_HEALTH_REPAIR_FAILED_RUN_ID", failed_run_id.to_owned()),
            ("MAIN_HEALTH_REPAIR_BASE_SHA", commit.to_owned()), ("MAIN_HEALTH_REPAIR_HEAD", commit.to_owned()),
        ];
        patch_state(context, &rerun).map_err(|error| DriverFailure::Result(internal(error)))?;
        let already_running = fields
            .get("ALREADY_RUNNING")
            .is_some_and(|value| truthy(value));
        return Ok(Some(ShipResult {
            outcome: ShipOutcome::Transient,
            failed_run_id: failed_run_id.to_owned(),
            pr_number: state_value(context, "PR_NUMBER").parse::<i64>().ok(),
            pr_url: state_value(context, "PR_URL"),
            merge_result: effective_merge_result(context),
            detail: if already_running {
                "post-merge push CI failed; rerun already running"
            } else {
                "post-merge push CI failed; rerun submitted"
            }
            .to_owned(),
            main_repair_run_id: failed_run_id.to_owned(),
            main_repair_head: commit.to_owned(),
            ..ShipResult::default()
        }));
    }
    let error = safe_detail(fields.get("ERROR").map(String::as_str).unwrap_or_default());
    if !error.is_empty() {
        patch_state(
            context,
            &[(
                "BAIL_FAILURE_DETAIL_LOG",
                safe_detail(&format!("{detail}; transient rerun failed: {error}")),
            )],
        )
        .map_err(|error| DriverFailure::Result(internal(error)))?;
    }
    Ok(None)
}

fn governance_gate(context: &ShipPrContext, repo_root: &Path) -> Result<(), DriverFailure> {
    if context.repo_unavailable {
        return Ok(());
    }
    let target = repository_ref(&context.repo)
        .map_err(|()| DriverFailure::Result(stalled("invalid repository slug")))?;
    let issue = with_github_service(async |service, cancellation| {
        service
            .issue_read(cancellation, target.owner(), target.name(), context.issue)
            .await
            .map_err(|error| github_error(&error))
    })
    .map_err(|error| DriverFailure::Result(stalled(error.into_detail())))?;
    let body_file = context.tmpdir.join("ship-governance-body.md");
    private_atomic_write(&body_file, &issue.body, &context.tmpdir)
        .map_err(|error| DriverFailure::Result(internal(error.to_string())))?;
    let base_remote = if context.forked { "upstream" } else { "origin" };
    let repository = GixRepository::open(repo_root)
        .map_err(|error| DriverFailure::Result(stalled(error.to_string())))?;
    let base_label = format!("{base_remote}/main");
    let base_sha = repository
        .resolve_revision(&Revision::new(base_label.as_bytes()))
        .map_err(|_| DriverFailure::Result(stalled("migration governance base is unavailable")))?
        .to_hex();
    let arguments = crate::implement_preflight_commands::governance_gate_argv(
        &context.issue.to_string(),
        &context.repo,
        &body_file,
        repo_root,
        &base_sha,
    );
    let output = delegate_larch_with_options(&arguments, &[], Duration::from_secs(180))
        .map_err(|error| DriverFailure::Result(stalled(error)))?;
    let fields = output_fields(output.stdout())?;
    if output.status().success() && fields.get("GOVERNANCE_OK").map(String::as_str) == Some("true")
    {
        Ok(())
    } else {
        Err(DriverFailure::Result(stalled(
            "migration governance blocked or could not be evaluated",
        )))
    }
}

fn pull_request_content(
    context: &ShipPrContext,
    repo_root: &Path,
    assessments: &AssessmentNotes,
) -> Result<(String, String), DriverFailure> {
    let disposition = ship_pr_disposition(&context.tmpdir, repo_root, context.manifest.as_deref())
        .map_err(|error| DriverFailure::Result(stalled(error)))?;
    let repository = GixRepository::open(repo_root)
        .map_err(|error| DriverFailure::Result(stalled(error.to_string())))?;
    let head = head_identity(&repository, &context.branch)
        .map_err(|error| DriverFailure::Result(stalled(error)))?;
    let subject = head_subject(&repository, &head);
    let title = ship_pr_title(context.issue, &context.pr_title, &subject);
    let body = compose_ship_pr_body(&ShipPrBody {
        summary: &summary(context),
        mermaid: &context.mermaid,
        test_plan: &context.test_plan,
        architectural_invariants_note: &assessments.invariants,
        architectural_guidelines_note: &assessments.guidelines,
        deferred_inventory: &disposition.deferred_inventory,
        issue_number: context.issue,
        partial: disposition.partial,
    })
    .map_err(|error| DriverFailure::Result(stalled(error)))?;
    Ok((title, body))
}

fn ensure_pull_request(
    context: &ShipPrContext,
    title: &str,
    body: &str,
) -> Result<(u64, bool), DriverFailure> {
    let target = repository_ref(&context.repo)
        .map_err(|()| DriverFailure::Result(stalled("invalid repository slug")))?;
    let head = github_head(context)
        .ok_or_else(|| DriverFailure::Result(stalled("cannot resolve fork head repository")))?;
    let spec = PullRequestSpec {
        owner: target.owner(),
        repo: target.name(),
        head: &head,
        base: "main",
        title,
        body,
        draft: context.draft,
    };
    with_github_service(async |service, cancellation| {
        service
            .ensure_pull_request(cancellation, &spec)
            .await
            .map(|ensured| (ensured.pull_request().number(), ensured.created()))
            .map_err(|error| github_error(&error))
    })
    .map_err(|error| {
        let detail = error.into_detail();
        DriverFailure::Result(detail.strip_prefix("transient:").map_or_else(
            || stalled(detail.as_str()),
            |detail| transient(detail.trim()),
        ))
    })
}

fn read_pull_request(context: &ShipPrContext, number: u64) -> Result<PullRequest, DriverFailure> {
    let target = repository_ref(&context.repo)
        .map_err(|()| DriverFailure::Result(stalled("invalid repository slug")))?;
    let pull_request = with_github_service(async |service, cancellation| {
        service
            .get_pull_request(cancellation, target.owner(), target.name(), number)
            .await
            .map_err(|error| github_error(&error))
    })
    .map_err(|error| {
        let detail = error.into_detail();
        DriverFailure::Result(detail.strip_prefix("transient:").map_or_else(
            || stalled(detail.as_str()),
            |detail| transient(detail.trim()),
        ))
    })?;
    if pull_request.number() != number {
        return Err(DriverFailure::Result(stalled(
            "pull request read returned a mismatched identity",
        )));
    }
    Ok(pull_request)
}

fn output_fields(bytes: &[u8]) -> Result<BTreeMap<String, String>, DriverFailure> {
    KvDocument::parse(&String::from_utf8_lossy(bytes), ParseOptions::legacy())
        .map(|document| document.select(DuplicatePolicy::Last))
        .map_err(|error| DriverFailure::Result(internal(error.to_string())))
}

fn required_field<'a>(
    fields: &'a BTreeMap<String, String>,
    key: &str,
) -> Result<&'a str, DriverFailure> {
    fields
        .get(key)
        .map(String::as_str)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| DriverFailure::Result(internal(format!("missing result field: {key}"))))
}

fn result_number(number: u64) -> Result<Option<i64>, DriverFailure> {
    i64::try_from(number)
        .map(Some)
        .map_err(|_| DriverFailure::Result(internal("pull request number exceeds result wire")))
}

fn effective_merge_result(context: &ShipPrContext) -> String {
    match state_value(context, "MERGE_RESULT").as_str() {
        result @ ("merged" | "admin_merged" | "already_merged") => result.to_owned(),
        _ => "merged".to_owned(),
    }
}

fn state_value(context: &ShipPrContext, key: &str) -> String {
    ShipState::read(&context.state_file)
        .ok()
        .and_then(|state| state.get(key).map(str::to_owned))
        .unwrap_or_default()
}

fn state_counter(context: &ShipPrContext, key: &str, fallback: u64) -> u64 {
    state_value(context, key).parse::<u64>().unwrap_or(fallback)
}

fn hydrate_result_identity(context: &ShipPrContext, result: &mut ShipResult) {
    if result.pr_number.is_none() {
        result.pr_number = state_value(context, "PR_NUMBER").parse::<i64>().ok();
    }
    if result.pr_url.is_empty() {
        result.pr_url = state_value(context, "PR_URL");
    }
    if result.merge_result.is_empty() {
        result.merge_result = state_value(context, "MERGE_RESULT");
    }
}

fn preserves_resume_phase(phase: &str, merge_result: &str) -> bool {
    matches!(phase, "postmerge" | "postmerge-push-watch")
        || (phase == "merge" && merge_result == "queued")
}

fn patch_done(context: &ShipPrContext) -> Result<(), String> {
    let mut updates = terminal_clear_updates();
    updates.extend([
        ("PHASE", "done".to_owned()),
        ("RESUME_PHASE", String::new()),
        ("CALLER_KIND", String::new()),
        ("CONFLICT_FILES", String::new()),
    ]);
    patch_state(context, &updates)
}

fn patch_needs_user(
    context: &ShipPrContext,
    reason: &str,
    detail: &str,
    step: &str,
) -> Result<(), DriverFailure> {
    patch_state(
        context,
        &[
            ("PHASE", "stalled".to_owned()),
            ("STALL_TRACKING", "true".to_owned()),
            ("STALL_STEP", step.to_owned()),
            ("BAIL_REASON", reason.to_owned()),
            ("BAIL_NEEDS_USER_INPUT", "true".to_owned()),
            ("BAIL_FAILURE_DETAIL_LOG", safe_detail(detail)),
            ("EXIT_CODE", "3".to_owned()),
        ],
    )
    .map_err(|error| DriverFailure::Result(internal(error)))
}

#[rustfmt::skip]
fn terminal_clear_updates() -> Vec<(&'static str, String)> {
    vec![
        ("STALL_TRACKING", "false".to_owned()), ("STALL_STEP", String::new()),
        ("EXIT_CODE", "0".to_owned()), ("BAIL_REASON", String::new()),
        ("BAIL_NEEDS_USER_INPUT", "false".to_owned()), ("FAILED_RUN_ID", String::new()),
        ("BAIL_FAILURE_DETAIL_LOG", String::new()),
    ]
}

fn refresh_run_log(context: &ShipPrContext, postmerge: bool) {
    #[rustfmt::skip]
    let mut arguments = vec![
        "run-log".into(), "refresh".into(), "--implement-tmpdir".into(), context.tmpdir.as_os_str().into(),
        "--run-id".into(), context.run_id.clone().into(), "--state-file".into(), context.state_file.as_os_str().into(),
        "--no-logs-commit".into(), context.no_logs_commit.to_string().into(),
        "--forked-target".into(), context.forked.to_string().into(), "--stall-tracking".into(), "false".into(),
    ];
    if postmerge {
        #[rustfmt::skip]
        arguments.extend([
            "--merge-result".into(), effective_merge_result(context).into(),
            "--postmerge".into(), "true".into(), "--render-reports".into(), "true".into(),
        ]);
    }
    let _ignored =
        delegate_larch_with_environment(&arguments, &[early_tmpdir_environment(context)]);
}

fn early_tmpdir_environment(context: &ShipPrContext) -> (ChildEnvironment, OsString) {
    (
        ChildEnvironment::ImplementTmpdir,
        context.tmpdir.as_os_str().to_owned(),
    )
}

fn safe_regular(path: &Path) -> bool {
    fs::symlink_metadata(path)
        .is_ok_and(|metadata| metadata.is_file() && !metadata.file_type().is_symlink())
}

fn safe_detail(detail: &str) -> String {
    let detail = redact_outbound(detail).replace(['\r', '\n'], " ");
    if detail.contains("[content truncated") {
        "redacted".to_owned()
    } else {
        detail.chars().take(500).collect()
    }
}

fn main_health_repair_covers(context: &ShipPrContext, run_id: &str, head: &str) -> bool {
    if run_id.is_empty() || head.is_empty() {
        return false;
    }
    ShipState::read(&context.tmpdir.join("main-health.env")).is_ok_and(|state| {
        state.get("MAIN_HEALTH_REPAIR_COMMITTED") == Some("true")
            && state.get("MAIN_HEALTH_REPAIR_FAILED_RUN_ID") == Some(run_id)
            && state.get("MAIN_HEALTH_REPAIR_BASE_SHA") == Some(head)
    })
}

fn escalation_handoff(mut result: ShipResult, trigger: &str, phase: &str) -> ShipResult {
    result.ledger_ready = true;
    "ship-pr".clone_into(&mut result.ledger_site);
    trigger.clone_into(&mut result.ledger_trigger);
    "8".clone_into(&mut result.ledger_step);
    phase.clone_into(&mut result.ledger_phase);
    "ship-pr".clone_into(&mut result.ledger_dispatcher);
    result.ledger_exit_code = Some(3);
    result.ledger_failure_detail_log = result.ci_errors_file.clone();
    result
}

impl ShipPrContext {
    #[allow(clippy::too_many_lines)] // Loading the frozen argparse, env, and state overlay is one boundary.
    fn load(parsed: &ParsedCommandLine) -> Result<Self, Box<ShipResult>> {
        let arg = |name: &str| {
            parsed
                .value(name)
                .map(|value| value.to_string_lossy().into_owned())
        };
        let text = |name: &str, env_names: &[&str]| {
            arg(name)
                .filter(|value| !value.is_empty())
                .unwrap_or_else(|| {
                    env_names
                        .iter()
                        .find_map(|name| env::var(name).ok().filter(|value| !value.is_empty()))
                        .unwrap_or_default()
                })
        };
        let tmpdir = PathBuf::from(text("--tmpdir", &["IMPLEMENT_TMPDIR"]));
        validate_tmpdir(&tmpdir).map_err(stalled)?;
        let tmpdir = fs::canonicalize(&tmpdir).map_err(|_| stalled("invalid implement tmpdir"))?;
        let supplied_state = text("--state-file", &["SHIP_PR_STATE_FILE"]);
        let state_file = if supplied_state.is_empty() {
            tmpdir.join("ship-pr-state.sh")
        } else {
            PathBuf::from(supplied_state)
        };
        let state_file = ensure_under(&state_file, &tmpdir, "ship state")
            .map_err(|_| stalled("invalid state_file"))?;
        let state = ShipState::read(&state_file)
            .and_then(|state| state.render().map(|_| state))
            .map_err(|error| internal(error.to_string()))?;
        let overlay = |key: &str, fallback: String| {
            state
                .get(key)
                .filter(|value| !value.is_empty())
                .map_or(fallback, str::to_owned)
        };
        let branch = overlay("BRANCH_NAME", text("--branch", &["BRANCH_NAME", "BRANCH"]));
        let issue_text = overlay("ISSUE_NUMBER", text("--issue", &["ISSUE_NUMBER", "ISSUE"]));
        let issue = issue_text
            .parse::<u64>()
            .ok()
            .filter(|issue| *issue > 0)
            .ok_or_else(|| stalled("invalid issue number for PR ensure"))?;
        let supplied_repo = text("--repo", &["REPO"]);
        if let Some(saved) = state.get("REPO").filter(|value| !value.is_empty())
            && !supplied_repo.is_empty()
            && saved != supplied_repo
        {
            return Err(stalled("state REPO does not match context repo"));
        }
        let repo = overlay("REPO", supplied_repo);
        repository_ref(&repo).map_err(|()| stalled("invalid repository slug"))?;
        let supplied_run_id = text("--run-id", &["RUN_ID", "LARCH_RUN_ID"]);
        if let Some(saved) = state.get("RUN_ID").filter(|value| !value.is_empty())
            && !supplied_run_id.is_empty()
            && saved != supplied_run_id
        {
            return Err(stalled("state RUN_ID does not match context run id"));
        }
        let run_id = overlay("RUN_ID", supplied_run_id);
        validate_run_id(&run_id).map_err(|error| stalled(error.to_string()))?;
        let bool_value = |option: &str, env_names: &[&str], state_key: &str| {
            state
                .get(state_key)
                .filter(|value| !value.is_empty())
                .map_or_else(
                    || {
                        arg(option).map_or_else(
                            || {
                                env_names.iter().any(|name| {
                                    env::var(name).ok().is_some_and(|value| truthy(&value))
                                })
                            },
                            |argument| truthy(&argument),
                        )
                    },
                    truthy,
                )
        };
        let counter = |key: &str| {
            let raw = state.get(key).unwrap_or("0");
            raw.parse::<u64>()
                .map_err(|_| stalled(format!("invalid ship state {key}")))
        };
        let pr_number = match state.get("PR_NUMBER").unwrap_or_default() {
            "" => None,
            raw => Some(
                raw.parse::<u64>()
                    .ok()
                    .filter(|number| *number > 0)
                    .ok_or_else(|| stalled("invalid ship state PR_NUMBER"))?,
            ),
        };
        let manifest_text = overlay("MANIFEST_PATH", text("--manifest-path", &["MANIFEST_PATH"]));
        let result_env_text = text("--result-env-path", &[]);
        Ok(Self {
            branch,
            issue,
            repo,
            run_id,
            tmpdir,
            state_file,
            manifest: (!manifest_text.is_empty()).then(|| PathBuf::from(manifest_text)),
            merge: bool_value("--merge", &["MERGE"], "MERGE"),
            draft: bool_value("--draft", &["DRAFT"], "DRAFT"),
            forked: bool_value("--forked", &["FORKED_TARGET", "FORKED"], "FORKED_TARGET"),
            repo_unavailable: bool_value(
                "--repo-unavailable",
                &["REPO_UNAVAILABLE"],
                "REPO_UNAVAILABLE",
            ),
            no_admin_fallback: bool_value(
                "--no-admin-fallback",
                &["NO_ADMIN_FALLBACK"],
                "NO_ADMIN_FALLBACK",
            ),
            no_logs_commit: bool_value("--no-logs-commit", &["NO_LOGS_COMMIT"], "NO_LOGS_COMMIT"),
            pr_title: overlay("PR_TITLE", env::var("PR_TITLE").unwrap_or_default()),
            summary: env::var("PR_SUMMARY").unwrap_or_default(),
            mermaid: env::var("PR_MERMAID").unwrap_or_default(),
            test_plan: env::var("PR_TEST_PLAN")
                .ok()
                .filter(|value| !value.is_empty())
                .unwrap_or_else(|| DEFAULT_TEST_PLAN.to_owned()),
            result_env: (!result_env_text.is_empty()).then(|| PathBuf::from(result_env_text)),
            resume: ResumeState {
                phase: state.get("PHASE").unwrap_or_default().to_owned(),
                resume_phase: state.get("RESUME_PHASE").unwrap_or_default().to_owned(),
                caller_kind: state.get("CALLER_KIND").unwrap_or_default().to_owned(),
                pr_number,
                pr_url: state.get("PR_URL").unwrap_or_default().to_owned(),
                merge_result: state.get("MERGE_RESULT").unwrap_or_default().to_owned(),
                iteration: counter("ITERATION")?,
                rebase_count: counter("REBASE_COUNT")?,
                fix_attempts: counter("FIX_ATTEMPTS")?,
                transient_retries: counter("TRANSIENT_RETRIES")?,
            },
        })
    }
}

fn validate_checkout(context: &ShipPrContext, repo_root: &Path) -> Result<(), Box<ShipResult>> {
    let repository = GixRepository::open(repo_root).map_err(|error| stalled(error.to_string()))?;
    let _head = head_identity(&repository, &context.branch).map_err(stalled)?;
    if matches!(context.branch.as_str(), "main" | "master") && !context.forked {
        return Err(stalled("protected branch"));
    }
    let status = repository
        .local_status(&StatusOptions::default())
        .map_err(|error| stalled(error.to_string()))?;
    if status.is_dirty() {
        return Err(stalled("dirty worktree before PR create"));
    }
    Ok(())
}

fn head_identity(repository: &GixRepository, branch: &str) -> Result<larch_core::ObjectId, String> {
    match repository.head().map_err(|error| error.to_string())? {
        Head::Symbolic { name, target }
            if name.as_bytes() == format!("refs/heads/{branch}").as_bytes() =>
        {
            Ok(target)
        }
        Head::Symbolic { .. } => Err("wrong branch".to_owned()),
        Head::Detached { .. } | Head::Unborn { .. } => {
            Err("detached HEAD or no current branch".to_owned())
        }
    }
}

pub fn head_subject(repository: &GixRepository, head: &larch_core::ObjectId) -> String {
    repository
        .walk_commits(head, 1)
        .ok()
        .and_then(|commits| commits.first().map(|commit| commit.subject.clone()))
        .map(|subject| String::from_utf8_lossy(&subject).trim().to_owned())
        .unwrap_or_default()
}

fn prepare_branch(context: &ShipPrContext, repo_root: &Path) -> Result<(), DriverFailure> {
    let remote_name = if context.forked { "upstream" } else { "origin" };
    let runtime = GitCommandRuntime::for_repository(repo_root)
        .map_err(|error| DriverFailure::Result(internal(error)))?;
    let remote = GitRemote::new(remote_name)
        .map_err(|error| DriverFailure::Result(stalled(error.to_string())))?;
    let main = GitRefspec::new("main")
        .map_err(|error| DriverFailure::Result(stalled(error.to_string())))?;
    runtime
        .runtime
        .block_on(runtime.git_cli().fetch(
            FetchRequest {
                remote,
                refspec: Some(main),
                quiet: false,
                no_tags: false,
                mode: larch_adapters::FetchMode::Standard,
            },
            &runtime.cancellation,
        ))
        .map_err(|_| DriverFailure::Result(transient("fetch failed")))?;
    let repository = GixRepository::open(repo_root)
        .map_err(|error| DriverFailure::Result(stalled(error.to_string())))?;
    let head = repository
        .resolve_revision(&Revision::new(b"HEAD"))
        .map_err(|error| DriverFailure::Result(stalled(error.to_string())))?;
    let base_label = format!("{remote_name}/main");
    let base = repository
        .resolve_revision(&Revision::new(base_label.as_bytes()))
        .map_err(|_| DriverFailure::Result(stalled("could not resolve merge base")))?;
    if repository
        .is_ancestor(&base, &head)
        .map_err(|error| DriverFailure::Result(stalled(error.to_string())))?
    {
        return Ok(());
    }
    let upstream = GitRef::new(base_label)
        .map_err(|error| DriverFailure::Result(stalled(error.to_string())))?;
    if runtime
        .runtime
        .block_on(runtime.git_cli().rebase(
            RebaseRequest::Start {
                onto: None,
                upstream,
                branch: None,
            },
            &runtime.cancellation,
        ))
        .is_ok()
    {
        return Ok(());
    }
    let files = GixRepository::open(repo_root)
        .ok()
        .and_then(|repository| repository.local_status(&StatusOptions::default()).ok())
        .map(|status| {
            status
                .unmerged
                .iter()
                .map(|entry| String::from_utf8_lossy(entry.path.as_bytes()).into_owned())
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();
    let detail = if files.is_empty() {
        "rebase failed".to_owned()
    } else {
        format!("rebase failed; conflicts in: {}", files.join(", "))
    };
    if files.is_empty() {
        let _aborted = runtime.runtime.block_on(
            runtime
                .git_cli()
                .rebase(RebaseRequest::Abort, &runtime.cancellation),
        );
        Err(DriverFailure::Result(stalled(detail)))
    } else {
        Err(DriverFailure::Conflict {
            detail,
            files: files.join(","),
        })
    }
}

fn assessment_gate(
    context: &ShipPrContext,
    repo_root: &Path,
) -> Result<AssessmentNotes, DriverFailure> {
    let base_remote = if context.forked { "upstream" } else { "origin" };
    let git = LiveAssessmentGit::for_base_remote(base_remote);
    let (statuses, pending) = materialize(
        &["invariants", "guidelines"],
        repo_root,
        &context.tmpdir,
        &git,
    )
    .map_err(|error| DriverFailure::Result(stalled(error)))?;
    if statuses.values().any(|status| status == "log-pending") {
        return Err(DriverFailure::Result(stalled(
            "architectural guideline warning log is pending",
        )));
    }
    if !pending.is_empty() {
        return Err(DriverFailure::Result(Box::new(ShipResult {
            outcome: ShipOutcome::NeedsUserInput,
            needs_user_reason: "architectural-assessments".to_owned(),
            detail: pending
                .iter()
                .map(|evidence| evidence.kind.key())
                .collect::<Vec<_>>()
                .join(","),
            ..ShipResult::default()
        })));
    }
    let repository = GixRepository::open(repo_root)
        .map_err(|error| DriverFailure::Result(stalled(error.to_string())))?;
    let head = repository
        .resolve_revision(&Revision::new(b"HEAD"))
        .map_err(|error| DriverFailure::Result(stalled(error.to_string())))?
        .to_hex();
    let mut notes = AssessmentNotes {
        invariants: String::new(),
        guidelines: String::new(),
    };
    let mut missing = Vec::new();
    for kind in [AssessmentKind::Invariants, AssessmentKind::Guidelines] {
        let base_ref = format!("{base_remote}/main");
        let Some(assessment) =
            current_ship_assessment(kind, repo_root, &context.tmpdir, &head, &base_ref, &git)
                .map_err(|error| DriverFailure::Result(stalled(error)))?
        else {
            missing.push(kind.key());
            continue;
        };
        if kind == AssessmentKind::Invariants && assessment.state == "violation" {
            return Err(DriverFailure::Result(Box::new(ShipResult {
                outcome: ShipOutcome::NeedsUserInput,
                needs_user_reason: "architectural-invariants-violation".to_owned(),
                detail: assessment.assessment,
                ..ShipResult::default()
            })));
        }
        if kind == AssessmentKind::Guidelines
            && assessment.state == "deviation"
            && guideline_active_exception(&assessment.assessment).is_none()
        {
            return Err(DriverFailure::Result(Box::new(ShipResult {
                outcome: ShipOutcome::NeedsUserInput,
                needs_user_reason: "architectural-guideline-deviation-unresolved".to_owned(),
                detail: assessment.assessment,
                ..ShipResult::default()
            })));
        }
        if kind == AssessmentKind::Invariants {
            notes.invariants = assessment.assessment;
        } else {
            notes.guidelines = assessment.assessment;
        }
    }
    if !missing.is_empty() {
        return Err(DriverFailure::Result(Box::new(ShipResult {
            outcome: ShipOutcome::NeedsUserInput,
            needs_user_reason: "architectural-assessments".to_owned(),
            detail: missing.join(","),
            ..ShipResult::default()
        })));
    }
    Ok(notes)
}

fn push_branch(context: &ShipPrContext, repo_root: &Path) -> Result<(), DriverFailure> {
    validate_checkout(context, repo_root).map_err(DriverFailure::Result)?;
    let runtime = GitCommandRuntime::for_repository(repo_root)
        .map_err(|error| DriverFailure::Result(internal(error)))?;
    let remote = GitRemote::new("origin")
        .map_err(|error| DriverFailure::Result(stalled(error.to_string())))?;
    let reference_text = format!("refs/heads/{}", context.branch);
    let reference = GitRef::new(&reference_text)
        .map_err(|error| DriverFailure::Result(stalled(error.to_string())))?;
    let probe = runtime
        .runtime
        .block_on(runtime.git_cli().ls_remote(
            LsRemoteRequest {
                remote: larch_adapters::GitLsRemoteTarget::Configured(remote.clone()),
                patterns: vec![reference.clone()],
                heads: true,
                exit_code: false,
            },
            &runtime.cancellation,
        ))
        .map_err(|_| DriverFailure::Result(stalled("remote branch probe failed")))?;
    let output = String::from_utf8_lossy(probe.output().stdout());
    let fields = output.split_whitespace().collect::<Vec<_>>();
    let oid = match fields.as_slice() {
        [] => None,
        [oid, observed] if valid_oid(oid) && *observed == reference_text => Some((*oid).to_owned()),
        _ => {
            return Err(DriverFailure::Result(stalled(
                "remote branch probe returned an invalid ref",
            )));
        }
    };
    let force_with_lease = match oid {
        Some(oid) => Some(ForceWithLease::Expecting {
            reference,
            oid: GitRef::new(oid)
                .map_err(|error| DriverFailure::Result(stalled(error.to_string())))?,
        }),
        None => Some(ForceWithLease::ExpectingAbsent { reference }),
    };
    let refspec = GitRefspec::new(format!("HEAD:refs/heads/{}", context.branch))
        .map_err(|error| DriverFailure::Result(stalled(error.to_string())))?;
    runtime
        .runtime
        .block_on(runtime.git_cli().push(
            PushRequest {
                remote: larch_adapters::GitPushTarget::Configured(remote),
                refspecs: vec![refspec],
                force_with_lease,
                set_upstream: true,
                prune: false,
            },
            &runtime.cancellation,
        ))
        .map_err(|_| DriverFailure::Result(stalled("branch push failed before PR create")))?;
    Ok(())
}

fn patch_state(context: &ShipPrContext, updates: &[(&str, String)]) -> Result<(), String> {
    let mut state = ShipState::read(&context.state_file).map_err(|error| error.to_string())?;
    for (key, value) in updates {
        if *key == "CONFLICT_FILES" && value.is_empty() {
            state.remove(key).map_err(|error| error.to_string())?;
        } else {
            state
                .set(key, value.clone())
                .map_err(|error| error.to_string())?;
        }
    }
    state
        .write(&context.state_file, &context.tmpdir)
        .map_err(|error| error.to_string())
}

fn summary(context: &ShipPrContext) -> String {
    if !context.summary.is_empty() {
        return context.summary.clone();
    }
    let Some(path) = context.manifest.as_deref() else {
        return "- Implement requested changes.\n".to_owned();
    };
    let regular = fs::symlink_metadata(path).is_ok_and(|metadata| {
        metadata.is_file() && !metadata.file_type().is_symlink() && metadata.len() <= MANIFEST_LIMIT
    });
    if regular
        && let Ok(text) = fs::read_to_string(path)
        && let Ok(Value::Object(manifest)) = serde_json::from_str::<Value>(&text)
        && let Some(Value::Array(items)) = manifest.get("summary_bullets")
        && !items.is_empty()
    {
        return format!(
            "{}\n",
            items
                .iter()
                .filter_map(Value::as_str)
                .map(|item| format!("- {item}"))
                .collect::<Vec<_>>()
                .join("\n")
        );
    }
    "- Implement requested changes.\n".to_owned()
}

fn github_head(context: &ShipPrContext) -> Option<String> {
    if !context.forked {
        return Some(context.branch.clone());
    }
    let origin = remote_slug("origin")?;
    let owner = origin.split_once('/')?.0;
    Some(format!("{owner}:{}", context.branch))
}

fn github_error(error: &GitHubOperationError) -> String {
    match error {
        GitHubOperationError::Unreachable(_)
        | GitHubOperationError::RateLimited
        | GitHubOperationError::DeadlineExceeded => format!("transient:{error}"),
        _ => error.to_string(),
    }
}

fn normalize_optional_bool(arguments: &[OsString]) -> Vec<OsString> {
    let mut normalized = Vec::with_capacity(arguments.len() + 1);
    for (index, argument) in arguments.iter().enumerate() {
        normalized.push(argument.clone());
        if argument == "--no-logs-commit"
            && arguments
                .get(index + 1)
                .is_none_or(|next| next.to_string_lossy().starts_with('-'))
        {
            normalized.push(OsString::from("true"));
        }
    }
    normalized
}

fn emit(result: &ShipResult, sink: Option<&Path>, tmpdir: Option<&Path>) -> ExitCode {
    let json = match result.driver_json() {
        Ok(json) => json,
        Err(error) => {
            eprintln!("ship pr: result emit failed: {error}");
            return ExitCode::from(1);
        }
    };
    if let (Some(path), Some(tmpdir)) = (sink, tmpdir)
        && let Err(error) = ShipResult::from_json(&json)
            .and_then(|redacted| redacted.write_result_env(path, tmpdir))
    {
        eprintln!("ship pr: result-env emit failed: {error}");
        return ExitCode::from(1);
    }
    println!("{json}");
    ExitCode::from(u8::try_from(result.outcome.exit_code().value()).unwrap_or(1))
}

fn stalled(detail: impl Into<String>) -> Box<ShipResult> {
    Box::new(ShipResult {
        outcome: ShipOutcome::Stalled,
        detail: detail.into(),
        ..ShipResult::default()
    })
}

fn transient(detail: impl Into<String>) -> Box<ShipResult> {
    Box::new(ShipResult {
        outcome: ShipOutcome::Transient,
        detail: detail.into(),
        ..ShipResult::default()
    })
}

fn internal(detail: impl Into<String>) -> Box<ShipResult> {
    Box::new(ShipResult {
        outcome: ShipOutcome::InternalError,
        detail: detail.into(),
        ..ShipResult::default()
    })
}

fn truthy(value: &str) -> bool {
    matches!(
        value.trim().to_ascii_lowercase().as_str(),
        "1" | "true" | "yes" | "on"
    )
}

fn valid_oid(value: &str) -> bool {
    let supported_width = value.len() == 40 || value.len() == 64;
    supported_width
        && value
            .as_bytes()
            .iter()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

fn slug(detail: &str) -> String {
    let mut slug = redact_outbound(detail)
        .chars()
        .map(|character| {
            if character.is_ascii_alphanumeric() {
                character.to_ascii_lowercase()
            } else {
                '-'
            }
        })
        .collect::<String>();
    while slug.contains("--") {
        slug = slug.replace("--", "-");
    }
    let slug = slug.trim_matches('-');
    let slug = slug.chars().take(80).collect::<String>();
    if slug.is_empty() {
        "stalled".to_owned()
    } else {
        slug
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        github_service::with_test_github_service,
        implement_child_seam::{clear_hooks, install_larch, install_python},
    };
    use larch_adapters::github::OctocrabGitHubService;
    use larch_core::{ProcessOutput, ProcessStatus};
    use larch_test_support::{IssueServiceExchange, IssueServiceStub};
    use serde_json::json;
    use std::sync::Arc;
    use tempfile::TempDir;

    fn output(code: i32, stdout: &str) -> ProcessOutput {
        ProcessOutput::new(
            ProcessStatus::new(code == 0, Some(code)),
            stdout.as_bytes().to_vec(),
            Vec::new(),
            false,
            false,
        )
    }

    #[rustfmt::skip]
    fn fixture() -> (TempDir, ShipPrContext) {
        let root = TempDir::new().expect("fixture");
        let tmpdir = root.path().join("claude-implement-ship-unit");
        fs::create_dir(&tmpdir).expect("tmpdir");
        let state_file = tmpdir.join("ship-pr-state.sh");
        fs::write(&state_file, concat!(
            "BRANCH_NAME=feature/ship\nISSUE_NUMBER=12\nREPO=owner/repo\nRUN_ID=run-a\n",
            "MERGE=true\nDRAFT=false\nFORKED_TARGET=false\nREPO_UNAVAILABLE=false\n",
            "ITERATION=0\nREBASE_COUNT=0\nFIX_ATTEMPTS=0\nTRANSIENT_RETRIES=0\n",
        )).expect("state");
        let context = ShipPrContext {
            branch: "feature/ship".to_owned(), issue: 12, repo: "owner/repo".to_owned(),
            run_id: "run-a".to_owned(), tmpdir, state_file, manifest: None, merge: true,
            draft: false, forked: false, repo_unavailable: false, no_admin_fallback: false,
            no_logs_commit: false, pr_title: String::new(), summary: String::new(),
            mermaid: String::new(), test_plan: DEFAULT_TEST_PLAN.to_owned(), result_env: None,
            resume: ResumeState::default(),
        };
        (root, context)
    }

    fn pull_request(number: u64, state: &str, merged: bool, body: &str) -> String {
        json!({
            "number": number, "state": state, "title": "Ship", "body": body,
            "head": { "ref": "feature/ship", "label": "owner:feature/ship" },
            "base": { "ref": "main" }, "draft": false, "merged": merged,
            "merge_commit_sha": merged.then_some("1111111111111111111111111111111111111111"),
        })
        .to_string()
    }

    fn service(
        responses: impl IntoIterator<Item = (u16, String)>,
    ) -> (
        Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync>,
        IssueServiceStub,
    ) {
        let exchanges = responses
            .into_iter()
            .map(|(status, body)| {
                IssueServiceExchange::any_json(status, body.into_bytes()).expect("response")
            })
            .collect::<Vec<_>>();
        let server = IssueServiceStub::start(exchanges).expect("stub");
        let base = server.base_url().to_owned();
        let factory: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
            Arc::new(move || OctocrabGitHubService::with_test_base(&base));
        (factory, server)
    }

    fn result(error: DriverFailure) -> Box<ShipResult> {
        match error {
            DriverFailure::Result(result) => result,
            DriverFailure::Conflict { .. } => panic!("unexpected conflict"),
        }
    }

    #[test]
    fn merge_results_preserve_retry_handoff_and_failure_classes() {
        let fields = |result: &str, error: &str| {
            BTreeMap::from([
                ("MERGE_RESULT".to_owned(), result.to_owned()),
                ("ERROR".to_owned(), error.to_owned()),
            ])
        };
        assert_eq!(
            classify_merge(&fields("queued", "")),
            Ok(MergeDisposition::Queued)
        );
        assert_eq!(
            classify_merge(&fields("main_advanced", "")),
            Ok(MergeDisposition::Rebase)
        );
        assert_eq!(
            classify_merge(&fields("review_required", "approval missing")),
            Ok(MergeDisposition::NeedsReview("approval missing".to_owned()))
        );
        assert_eq!(
            classify_merge(&fields("version_already_published", "release exists")),
            Ok(MergeDisposition::Stalled(
                "release exists".to_owned(),
                "version_already_published".to_owned()
            ))
        );
        assert_eq!(
            classify_merge(&fields("ci_not_ready", "")),
            Ok(MergeDisposition::Retry)
        );
        assert_eq!(
            classify_merge(&fields("review_required", "")),
            Ok(MergeDisposition::NeedsReview(
                "PR requires approving review".to_owned()
            ))
        );
        assert_eq!(
            classify_merge(&fields("other", "")),
            Ok(MergeDisposition::Stalled(
                "merge did not complete: other".to_owned(),
                "other".to_owned()
            ))
        );
        assert!(classify_merge(&BTreeMap::new()).is_err());
    }

    #[test]
    fn terminal_stalls_retain_only_live_queue_and_postmerge_resume_points() {
        assert!(preserves_resume_phase("merge", "queued"));
        assert!(preserves_resume_phase("postmerge", "merged"));
        assert!(preserves_resume_phase(
            "postmerge-push-watch",
            "admin_merged"
        ));
        assert!(!preserves_resume_phase("merge", "error"));
        assert!(!preserves_resume_phase("ci-initial", ""));
    }

    #[test]
    fn durable_context_and_wire_helpers_fail_closed() {
        let (_root, context) = fixture();
        let arguments = normalize_optional_bool(&[
            "--tmpdir".into(),
            context.tmpdir.as_os_str().into(),
            "--state-file".into(),
            context.state_file.as_os_str().into(),
            "--no-logs-commit".into(),
        ]);
        let parsed = parse_required_with_help(&arguments, PROGRAM, USAGE, HELP, OPTIONS, &[], &[])
            .expect("arguments");
        let loaded = ShipPrContext::load(&parsed).expect("durable context");
        assert_eq!(loaded.branch, "feature/ship");
        assert!(loaded.merge && loaded.no_logs_commit);

        patch_state(
            &context,
            &[
                ("PR_NUMBER", "12".to_owned()),
                ("PR_URL", "https://github.com/owner/repo/pull/12".to_owned()),
                ("MERGE_RESULT", "queued".to_owned()),
                ("CONFLICT_FILES", String::new()),
            ],
        )
        .expect("patch");
        assert_eq!(state_counter(&context, "PR_NUMBER", 0), 12);
        let mut hydrated = ShipResult::default();
        hydrate_result_identity(&context, &mut hydrated);
        assert_eq!(hydrated.pr_number, Some(12));
        assert_eq!(hydrated.merge_result, "queued");
        patch_needs_user(&context, "review-required", "line\nbreak", "merge").expect("needs user");
        assert_eq!(
            state_value(&context, "BAIL_FAILURE_DETAIL_LOG"),
            "line break"
        );
        patch_done(&context).expect("done");
        assert_eq!(state_value(&context, "PHASE"), "done");
        assert_eq!(state_value(&context, "BAIL_REASON"), "");

        let fields = output_fields(b"A=first\nA=last\n").expect("wire");
        assert_eq!(required_field(&fields, "A").expect("field"), "last");
        assert!(required_field(&fields, "MISSING").is_err());
        assert_eq!(result_number(7).expect("number"), Some(7));
        assert!(result_number(u64::MAX).is_err());
        assert!(truthy(" YES ") && !truthy("no"));
        assert!(valid_oid(&"a".repeat(40)) && !valid_oid(&"A".repeat(40)));
        assert_eq!(slug("***"), "stalled");
        assert_eq!(safe_detail("a\rb\nc"), "a b c");
        assert_eq!(github_head(&context).as_deref(), Some("feature/ship"));
        assert_eq!(summary(&context), "- Implement requested changes.\n");

        let mut escalated = escalation_handoff(ShipResult::default(), "trigger", "phase");
        assert!(escalated.ledger_ready);
        assert_eq!(escalated.ledger_trigger, "trigger");
        escalated.pr_number = None;
        assert_eq!(effective_merge_result(&context), "merged");
    }

    #[test]
    fn typed_pull_request_boundaries_validate_identity_and_body() {
        let (_root, context) = fixture();
        let open = pull_request(12, "open", false, "Body");
        let (factory, server) = service([
            (200, format!("[{open}]")),
            (200, pull_request(12, "open", false, "Body")),
        ]);
        let ensured =
            with_test_github_service(factory, || ensure_pull_request(&context, "Title", "Body"))
                .unwrap_or_else(|error| {
                    panic!("ensure failed: {error:?}; requests={:?}", server.requests())
                });
        assert_eq!(ensured, (12, false));
        server.join().expect("stub completed");

        let (factory, server) = service([(200, pull_request(13, "open", false, ""))]);
        let mismatch = with_test_github_service(factory, || read_pull_request(&context, 12))
            .expect_err("identity mismatch");
        assert_eq!(result(mismatch).outcome, ShipOutcome::Stalled);
        server.join().expect("stub completed");
    }

    #[test]
    fn resumed_pull_requests_classify_terminal_identity_before_mutation() {
        let (_root, mut context) = fixture();
        context.merge = false;
        context.resume.phase = "done".to_owned();
        context.resume.pr_number = Some(12);
        let (factory, server) = service([(200, pull_request(12, "closed", true, ""))]);
        let complete =
            with_test_github_service(factory, || run_resume(&context, &context.tmpdir, 12))
                .expect("already complete");
        assert_eq!(complete.detail, "already-complete");
        server.join().expect("stub completed");

        let (factory, server) = service([(200, pull_request(12, "closed", false, ""))]);
        let closed =
            with_test_github_service(factory, || run_resume(&context, &context.tmpdir, 12))
                .expect_err("closed without merge");
        assert_eq!(result(closed).outcome, ShipOutcome::Stalled);
        server.join().expect("stub completed");

        let wrong_head = pull_request(12, "open", false, "").replace("feature/ship", "other");
        let (factory, server) = service([(200, wrong_head)]);
        let mismatch =
            with_test_github_service(factory, || run_resume(&context, &context.tmpdir, 12))
                .expect_err("wrong head");
        assert_eq!(result(mismatch).needs_user_reason, "checkout-mismatch");
        server.join().expect("stub completed");
    }

    #[test]
    fn ci_failure_and_main_health_publish_typed_handoffs() {
        let (_root, context) = fixture();
        install_larch(|arguments, _environment| {
            let command = arguments
                .iter()
                .map(|value| value.to_string_lossy())
                .collect::<Vec<_>>();
            if command.get(1).is_some_and(|value| value == "wait") {
                Ok(output(
                    0,
                    concat!(
                        "ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nCONFLICTED=false\n",
                        "FAILED_RUN_ID=123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n",
                    ),
                ))
            } else {
                Ok(output(0, "FAILED_JOBS_COUNT=2\nSTATUS=ok\n"))
            }
        });
        let fields = wait_for_ci(&context, 12, 0, 0, 0).expect("CI verdict");
        assert_eq!(
            fields.get("ACTION").map(String::as_str),
            Some("evaluate_failure")
        );
        let failure = ci_failure(&context, 12, "url".to_owned(), "123").expect("handoff");
        assert_eq!(failure.failed_jobs_count, 2);
        assert!(failure.ledger_ready);

        fs::write(context.tmpdir.join("preflight-tmpdir.env"), "READY=true\n").expect("preflight");
        fs::write(
            context.tmpdir.join("main-health.env"),
            "MAIN_HEALTH_REPAIR_COMMITTED=false\n",
        )
        .expect("health state");
        install_larch(|arguments, _environment| {
            let command = arguments
                .iter()
                .map(|value| value.to_string_lossy())
                .collect::<Vec<_>>();
            if command.get(1).is_some_and(|value| value == "main-health") {
                Ok(output(
                    1,
                    concat!(
                        "MAIN_CI_STATUS=fail\nMAIN_FAILED_RUN_ID=456\n",
                        "MAIN_HEALTH_HEAD_SHA=1111111111111111111111111111111111111111\n",
                        "MAIN_HEALTH_DETAIL=main failed\n",
                    ),
                ))
            } else {
                Ok(output(0, "RERUN_SUBMITTED=true\nALREADY_RUNNING=false\n"))
            }
        });
        let premerge = main_health_gate(
            &context,
            Some("1111111111111111111111111111111111111111"),
            false,
        )
        .expect("classified")
        .expect("failure result");
        assert_eq!(premerge.needs_user_reason, "main-ci-fail");
        let postmerge = main_health_gate(
            &context,
            Some("1111111111111111111111111111111111111111"),
            true,
        )
        .expect("classified")
        .expect("transient result");
        assert_eq!(postmerge.outcome, ShipOutcome::Transient);
        clear_hooks();
    }

    #[test]
    fn merge_loop_completes_direct_and_queued_merges() {
        for disposition in ["merged", "queued"] {
            let (_root, context) = fixture();
            let selected = disposition.to_owned();
            install_larch(move |arguments, _environment| {
                let command = arguments
                    .iter()
                    .map(|value| value.to_string_lossy())
                    .collect::<Vec<_>>();
                match command
                    .iter()
                    .map(AsRef::as_ref)
                    .take(2)
                    .collect::<Vec<_>>()
                    .as_slice()
                {
                    ["ci", "wait"] => Ok(output(
                        0,
                        concat!(
                            "ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nCONFLICTED=false\n",
                            "FAILED_RUN_ID=\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n",
                        ),
                    )),
                    ["merge", "pr"] => Ok(output(0, &format!("MERGE_RESULT={selected}\n"))),
                    ["merge", "wait"] => Ok(output(0, "MERGE_RESULT=merged\n")),
                    ["run-log", "refresh"] => Ok(output(0, "")),
                    other => panic!("unexpected larch child: {other:?}"),
                }
            });
            install_python(move |arguments| {
                let command = arguments
                    .iter()
                    .map(|value| value.to_string_lossy())
                    .collect::<Vec<_>>();
                match command.first().map(AsRef::as_ref) {
                    Some("implement-finalize") => Ok(output(0, "OUTCOME=OK\nSTATUS=complete\n")),
                    other => panic!("unexpected child: {other:?}"),
                }
            });
            let (factory, server) = service([(200, pull_request(12, "closed", true, ""))]);
            let completed = with_test_github_service(factory, || {
                run_merge_loop(
                    &context,
                    &context.tmpdir,
                    12,
                    "https://github.com/owner/repo/pull/12".to_owned(),
                )
            })
            .expect("merge completion");
            assert_eq!(completed.pr_number, Some(12));
            assert_eq!(completed.merge_result, "merged");
            assert_eq!(state_value(&context, "PHASE"), "done");
            server.join().expect("stub completed");
            clear_hooks();
        }
    }

    #[test]
    fn merge_loop_classifies_bails_retries_and_unknown_actions() {
        for (action, bail_reason, merge_result, expected) in [
            ("evaluate_failure", "", "", ShipOutcome::NeedsUserInput),
            (
                "bail",
                "fix-attempts-exhausted",
                "",
                ShipOutcome::NeedsUserInput,
            ),
            ("unknown", "", "", ShipOutcome::InternalError),
            ("merge", "", "review_required", ShipOutcome::NeedsUserInput),
            ("merge", "", "other", ShipOutcome::Stalled),
            ("merge", "", "ci_not_ready", ShipOutcome::Stalled),
        ] {
            let (_root, context) = fixture();
            let selected_action = action.to_owned();
            let selected_bail = bail_reason.to_owned();
            let selected_merge = merge_result.to_owned();
            install_larch(move |arguments, _environment| {
                match arguments
                    .iter()
                    .filter_map(|value| value.to_str())
                    .take(2)
                    .collect::<Vec<_>>()
                    .as_slice()
                {
                    ["ci", "wait"] => Ok(output(
                        0,
                        &format!(
                            "ACTION={selected_action}\nCI_STATUS=fail\nBEHIND_COUNT=0\nCONFLICTED=false\nFAILED_RUN_ID=not-numeric\nBAIL_REASON={selected_bail}\nITERATION=0\nELAPSED=1\n"
                        ),
                    )),
                    ["merge", "pr"] => Ok(output(0, &format!("MERGE_RESULT={selected_merge}\n"))),
                    other => panic!("unexpected larch child: {other:?}"),
                }
            });
            let classified = run_merge_loop(
                &context,
                &context.tmpdir,
                12,
                "https://github.com/owner/repo/pull/12".to_owned(),
            );
            let outcome = match classified {
                Ok(result) => result.outcome,
                Err(error) => result(error).outcome,
            };
            assert_eq!(outcome, expected, "{action}/{merge_result}");
            if merge_result == "other" {
                assert_eq!(state_value(&context, "MERGE_RESULT"), "error");
            }
            clear_hooks();
        }

        let (_root, context) = fixture();
        patch_state(&context, &[("ITERATION", "51".to_owned())]).expect("iteration");
        let capped = run_merge_loop(
            &context,
            &context.tmpdir,
            12,
            "https://github.com/owner/repo/pull/12".to_owned(),
        )
        .expect_err("iteration cap");
        assert_eq!(result(capped).outcome, ShipOutcome::Stalled);
    }
}
