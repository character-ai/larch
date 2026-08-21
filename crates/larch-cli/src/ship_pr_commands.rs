//! Rust parity implementation of the fresh `ship pr` path (#8626).
//!
//! The command is compiled into the Rust CLI while the migration registry
//! keeps the production verb Python-owned. It prepares a clean branch, runs
//! the architectural gates, composes and redacts the PR body, pushes with an
//! exact lease, reconciles PR creation, and publishes the CI hand-off state.
//! Merge, resume, and post-merge recovery remain with cutover leaf #8628.

use std::{
    env,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::{
    FetchRequest, ForceWithLease, GitRef, GitRefspec, GitRemote, GixRepository, LsRemoteRequest,
    PushRequest, RebaseRequest,
    github::{GitHubOperationError, PullRequestSpec},
};
use larch_core::{
    AssessmentKind, Head, RepositoryRead, Revision, ShipOutcome, ShipPrBody, ShipResult, ShipState,
    StatusOptions, compose_ship_pr_body, current_ship_assessment, ensure_under,
    guideline_active_exception, materialize, redact_outbound, ship_pr_title, validate_run_id,
    validate_ship_result_env,
};
use serde_json::Value;

use crate::{
    architectural_assessment_commands::LiveAssessmentGit,
    argparse_compat::{ParsedCommandLine, parse_required_with_help},
    git_command_runtime::GitCommandRuntime,
    github_repository_resolution::{remote_slug, repository_ref},
    github_service::with_github_service,
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
    "Run the Python ship-pr driver\n\n",
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

#[allow(clippy::struct_excessive_bools)] // Mirrors independent switches in the frozen CLI wire.
struct ShipPrContext {
    branch: String,
    issue: u64,
    repo: String,
    tmpdir: PathBuf,
    state_file: PathBuf,
    manifest: Option<PathBuf>,
    merge: bool,
    draft: bool,
    forked: bool,
    repo_unavailable: bool,
    pr_title: String,
    summary: String,
    mermaid: String,
    test_plan: String,
    result_env: Option<PathBuf>,
}

struct AssessmentNotes {
    invariants: String,
    guidelines: String,
}

enum DriverFailure {
    Result(Box<ShipResult>),
    Conflict { detail: String, files: String },
}

/// Run the fresh Rust ship PR parity path.
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
    if result.outcome == ShipOutcome::Stalled && !active_handoff {
        let step = slug(&result.detail);
        if let Err(error) = patch_state(
            &context,
            &[
                ("PHASE", "stalled".to_owned()),
                ("STALL_TRACKING", "true".to_owned()),
                ("STALL_STEP", step),
                ("EXIT_CODE", "4".to_owned()),
            ],
        ) {
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
    validate_checkout(context, &repo_root).map_err(DriverFailure::Result)?;
    patch_state(
        context,
        &[
            ("PHASE", "pr-prep".to_owned()),
            ("STALL_TRACKING", "false".to_owned()),
            ("STALL_STEP", String::new()),
            ("EXIT_CODE", String::new()),
            ("BAIL_REASON", String::new()),
            ("BAIL_NEEDS_USER_INPUT", "false".to_owned()),
            ("FAILED_RUN_ID", String::new()),
            ("BAIL_FAILURE_DETAIL_LOG", String::new()),
        ],
    )
    .map_err(|error| DriverFailure::Result(internal(error)))?;
    prepare_branch(context, &repo_root)?;
    patch_state(context, &[("PHASE", "assessments".to_owned())])
        .map_err(|error| DriverFailure::Result(internal(error)))?;
    let assessments = assessment_gate(context, &repo_root)?;
    if context.repo_unavailable {
        patch_state(
            context,
            &[
                ("PHASE", "done".to_owned()),
                ("STALL_TRACKING", "false".to_owned()),
                ("STALL_STEP", String::new()),
                ("EXIT_CODE", "0".to_owned()),
                ("BAIL_REASON", String::new()),
                ("BAIL_NEEDS_USER_INPUT", "false".to_owned()),
                ("FAILED_RUN_ID", String::new()),
                ("BAIL_FAILURE_DETAIL_LOG", String::new()),
            ],
        )
        .map_err(|error| DriverFailure::Result(internal(error)))?;
        return Ok(ShipResult {
            detail: "local-only".to_owned(),
            ..ShipResult::default()
        });
    }
    let gate = validate_ship_disposition(&context.tmpdir, &repo_root, context.manifest.as_deref())
        .map_err(|error| DriverFailure::Result(stalled(error)))?;
    if !gate.ok {
        return Err(DriverFailure::Result(Box::new(ShipResult {
            outcome: ShipOutcome::NeedsUserInput,
            needs_user_reason: "scope-disposition".to_owned(),
            detail: gate.reason,
            ..ShipResult::default()
        })));
    }
    let disposition = ship_pr_disposition(&context.tmpdir, &repo_root, context.manifest.as_deref())
        .map_err(|error| DriverFailure::Result(stalled(error)))?;
    let repository = GixRepository::open(&repo_root)
        .map_err(|error| DriverFailure::Result(stalled(error.to_string())))?;
    let head = head_identity(&repository, &context.branch)
        .map_err(|error| DriverFailure::Result(stalled(error)))?;
    let subject = repository
        .walk_commits(&head, 1)
        .ok()
        .and_then(|commits| commits.first().map(|commit| commit.subject.clone()))
        .map(|subject| String::from_utf8_lossy(&subject).trim().to_owned())
        .unwrap_or_default();
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
    let target = repository_ref(&context.repo)
        .map_err(|()| DriverFailure::Result(stalled("invalid repository slug")))?;
    let head_label = github_head(context)
        .ok_or_else(|| DriverFailure::Result(stalled("cannot resolve fork head repository")))?;
    patch_state(context, &[("PHASE", "pr-create".to_owned())])
        .map_err(|error| DriverFailure::Result(internal(error)))?;
    push_branch(context, &repo_root)?;
    let spec = PullRequestSpec {
        owner: target.owner(),
        repo: target.name(),
        head: &head_label,
        base: "main",
        title: &title,
        body: &body,
        draft: context.draft,
    };
    let ensured = with_github_service(async |service, cancellation| {
        service
            .ensure_pull_request(cancellation, &spec)
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
    let number = ensured.pull_request().number();
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
        updates.extend([
            ("STALL_TRACKING", "false".to_owned()),
            ("STALL_STEP", String::new()),
            ("EXIT_CODE", "0".to_owned()),
            ("BAIL_REASON", String::new()),
            ("BAIL_NEEDS_USER_INPUT", "false".to_owned()),
            ("FAILED_RUN_ID", String::new()),
            ("BAIL_FAILURE_DETAIL_LOG", String::new()),
        ]);
    }
    patch_state(context, &updates).map_err(|error| DriverFailure::Result(internal(error)))?;
    Ok(ShipResult {
        pr_number: Some(number_i64),
        pr_url: url,
        detail: if ensured.created() {
            "created"
        } else {
            "existing"
        }
        .to_owned(),
        ..ShipResult::default()
    })
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
        let repo = overlay("REPO", text("--repo", &["REPO"]));
        repository_ref(&repo).map_err(|()| stalled("invalid repository slug"))?;
        let run_id = overlay("RUN_ID", text("--run-id", &["RUN_ID", "LARCH_RUN_ID"]));
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
        if state
            .get("PR_NUMBER")
            .is_some_and(|number| !number.is_empty())
        {
            return Err(Box::new(ShipResult {
                outcome: ShipOutcome::NeedsUserInput,
                needs_user_reason: "unsupported-rebase-continuation".to_owned(),
                detail: "Rust parity driver does not own open-PR resume before #8628".to_owned(),
                ..ShipResult::default()
            }));
        }
        let manifest_text = overlay("MANIFEST_PATH", text("--manifest-path", &["MANIFEST_PATH"]));
        let result_env_text = text("--result-env-path", &[]);
        Ok(Self {
            branch,
            issue,
            repo,
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
            pr_title: overlay("PR_TITLE", env::var("PR_TITLE").unwrap_or_default()),
            summary: env::var("PR_SUMMARY").unwrap_or_default(),
            mermaid: env::var("PR_MERMAID").unwrap_or_default(),
            test_plan: env::var("PR_TEST_PLAN")
                .ok()
                .filter(|value| !value.is_empty())
                .unwrap_or_else(|| DEFAULT_TEST_PLAN.to_owned()),
            result_env: (!result_env_text.is_empty()).then(|| PathBuf::from(result_env_text)),
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
    let _aborted = runtime.runtime.block_on(
        runtime
            .git_cli()
            .rebase(RebaseRequest::Abort, &runtime.cancellation),
    );
    let detail = if files.is_empty() {
        "rebase failed".to_owned()
    } else {
        format!("rebase failed; conflicts in: {}", files.join(", "))
    };
    if files.is_empty() {
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
                remote: remote.clone(),
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
                remote,
                refspec,
                force_with_lease,
                set_upstream: true,
            },
            &runtime.cancellation,
        ))
        .map_err(|_| DriverFailure::Result(stalled("branch push failed before PR create")))?;
    Ok(())
}

fn patch_state(context: &ShipPrContext, updates: &[(&str, String)]) -> Result<(), String> {
    let mut state = ShipState::read(&context.state_file).map_err(|error| error.to_string())?;
    for (key, value) in updates {
        state
            .set(key, value.clone())
            .map_err(|error| error.to_string())?;
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
    matches!(value.len(), 40 | 64)
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
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
