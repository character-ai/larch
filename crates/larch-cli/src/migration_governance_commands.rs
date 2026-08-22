//! Typed effect adapter for migration governance and plan-receipt refresh.
//!
//! The policy is owned by `larch-core`. This module gathers bounded GitHub and
//! Git evidence, applies the one authorized receipt mutation, and preserves the
//! retired Python commands' machine-readable output and exit codes.

use std::{
    collections::{BTreeSet, HashMap},
    ffi::{OsStr, OsString},
    fmt::Write as _,
    path::Path,
    process::ExitCode,
};

use chrono::Utc;
use larch_adapters::{
    ExactDiffRequest, GitPath as GitCliPath, GitRef, GixRepository, PathIntent, RepositoryRoot,
    TemporaryRoot, assert_no_symlink_path_or_ancestors, atomic_write_utf8,
    github::{IssueMutationOwner, OctocrabGitHubService},
    runtime::Cancellation,
};
use larch_core::{
    BlockerSnapshotRow, FreshnessVerdict, GitHubIssue, GitHubIssueState, GitHubRepositoryRef,
    GitHubService, GovernanceGateVerdict, GovernanceIssueSnapshot, IssueMutationSnapshot,
    OrderedJson, OwnerAdmissionRequest, OwnerAdmissionVerdict, PLAN_MARKER, ParityVerdict,
    PlanReceipt, REASON_BLOCKER_READ_UNAVAILABLE, REASON_PLAN_BASE_SCOPE_UNAVAILABLE,
    REASON_STALE_PLAN_BASE_SCOPE, ReceiptFreshnessRequest, RepositoryName, RepositoryRead,
    Revision, ScopeFile, ScopeSnapshot, compare_blocker_parity, declared_scope_paths,
    evaluate_governance_gate, evaluate_owner_admission, format_gate_refusal, hash_blocker_rows,
    hash_owner_rows, hash_plan_block, parse_named_block, parse_native_blocker_refs,
    parse_owner_block, parse_receipt, python_json_dumps, redact_secrets_only, upsert_receipt,
    validate_receipt_freshness,
};

use crate::{
    argparse_compat::{absolute_path, parse_required_with_help},
    design_publish_commands::receipt_blocker_rows,
    git_command_runtime::GitCommandRuntime,
    github_repository_resolution::{repository_ref, repository_repo},
    github_service::{ServiceFailure, list_exhaustive_issues_for_state, with_github_service},
    issue_mutation_support::{authorization_request, flat_error},
    issue_wire_commands::named_block_mutation_request,
};

const GATE_PROGRAM: &str = "larch issue governance-gate";
const GATE_USAGE: &str = "usage: larch issue governance-gate [-h] --issue ISSUE --repo REPO --body-file\n                                   BODY_FILE --repo-root REPO_ROOT --head-sha\n                                   HEAD_SHA [--preflight-envelope]";
const GATE_HELP: &str = "usage: larch issue governance-gate [-h] --issue ISSUE --repo REPO --body-file\n                                   BODY_FILE --repo-root REPO_ROOT --head-sha\n                                   HEAD_SHA [--preflight-envelope]\n\noptions:\n  -h, --help            show this help message and exit\n  --issue ISSUE\n  --repo REPO\n  --body-file BODY_FILE\n  --repo-root REPO_ROOT\n  --head-sha HEAD_SHA\n  --preflight-envelope";
const REFRESH_PROGRAM: &str = "larch plan-receipt refresh";
const REFRESH_USAGE: &str = "usage: larch plan-receipt refresh [-h] --issue ISSUE [--repo REPO] --repo-root\n                                  REPO_ROOT --preflight-tmpdir\n                                  PREFLIGHT_TMPDIR --base-ref BASE_REF\n                                  --previous-base-sha PREVIOUS_BASE_SHA\n                                  --base-sha BASE_SHA";
const REFRESH_HELP: &str = "usage: larch plan-receipt refresh [-h] --issue ISSUE [--repo REPO] --repo-root\n                                  REPO_ROOT --preflight-tmpdir\n                                  PREFLIGHT_TMPDIR --base-ref BASE_REF\n                                  --previous-base-sha PREVIOUS_BASE_SHA\n                                  --base-sha BASE_SHA\n\noptions:\n  -h, --help            show this help message and exit\n  --issue ISSUE\n  --repo REPO\n  --repo-root REPO_ROOT\n  --preflight-tmpdir PREFLIGHT_TMPDIR\n  --base-ref BASE_REF\n  --previous-base-sha PREVIOUS_BASE_SHA\n  --base-sha BASE_SHA";
const MAX_SCOPE_FILES: usize = 20_000;
const MAX_SCOPE_DIFF_ROWS: usize = 128;

struct GateArguments {
    issue: u64,
    repository: GitHubRepositoryRef,
    body: String,
    repo_root: RepositoryRoot,
    head_sha: String,
    envelope: bool,
}

struct RefreshArguments {
    issue: u64,
    repository: String,
    repo_root: RepositoryRoot,
    preflight_root: TemporaryRoot,
    base_ref: String,
    previous_base_sha: String,
    base_sha: String,
}

struct RemoteGateEvidence {
    blocker_rows: Vec<BlockerSnapshotRow>,
    parity: ParityVerdict,
    owners: OwnerAdmissionVerdict,
}

/// Evaluate the shared migration-governance gate.
pub fn governance_gate(arguments: &[OsString]) -> ExitCode {
    let request = match parse_gate_arguments(arguments) {
        Ok(request) => request,
        Err(code) => return code,
    };
    let verdict = evaluate_live_gate(&request);
    if request.envelope {
        emit_preflight_envelope(&verdict);
        return if verdict.ok() || permits_semantic_revalidation(&verdict) {
            ExitCode::SUCCESS
        } else {
            ExitCode::FAILURE
        };
    }
    println!("GOVERNANCE_OK={}", verdict.ok());
    if verdict.ok() {
        ExitCode::SUCCESS
    } else {
        let reasons = verdict.blocking_reasons();
        eprintln!(
            "GOVERNANCE_REASONS={}",
            if reasons.is_empty() {
                "unknown".to_owned()
            } else {
                reasons.join(",")
            }
        );
        ExitCode::FAILURE
    }
}

fn parse_gate_arguments(arguments: &[OsString]) -> Result<GateArguments, ExitCode> {
    let parsed = parse_required_with_help(
        arguments,
        GATE_PROGRAM,
        GATE_USAGE,
        GATE_HELP,
        &[
            "--issue",
            "--repo",
            "--body-file",
            "--repo-root",
            "--head-sha",
        ],
        &["--preflight-envelope"],
        &[
            "--issue",
            "--repo",
            "--body-file",
            "--repo-root",
            "--head-sha",
        ],
    )?;
    let envelope = parsed.flag("--preflight-envelope");
    let issue =
        positive_issue(parsed.value("--issue")).map_err(|detail| gate_error(&detail, envelope))?;
    let repository_text = text_value(parsed.value("--repo"));
    let repository = repository_ref(&repository_text)
        .map_err(|()| gate_error("--repo must be exactly owner/name", envelope))?;
    let head_sha = text_value(parsed.value("--head-sha"));
    if !lower_sha1(&head_sha) {
        return Err(gate_error(
            "--head-sha must be a 40-character hexadecimal SHA",
            envelope,
        ));
    }
    let root_path = absolute_path(Path::new(parsed.value("--repo-root").unwrap_or_default()))
        .map_err(|error| gate_error(&error.to_string(), envelope))?;
    assert_no_symlink_path_or_ancestors(&root_path)
        .map_err(|error| gate_error(&error, envelope))?;
    let repo_root = RepositoryRoot::resolve(Some(&root_path))
        .map_err(|error| gate_error(&error.to_string(), envelope))?;
    let body_path = absolute_path(Path::new(parsed.value("--body-file").unwrap_or_default()))
        .map_err(|error| gate_error(&error.to_string(), envelope))?;
    assert_no_symlink_path_or_ancestors(&body_path)
        .map_err(|error| gate_error(&error, envelope))?;
    let body_parent = body_path
        .parent()
        .ok_or_else(|| gate_error("governance body path is invalid", envelope))?;
    let body_root = TemporaryRoot::resolve(Some(body_parent))
        .map_err(|error| gate_error(&error.to_string(), envelope))?;
    let body_relative = body_path
        .strip_prefix(body_parent)
        .map_err(|_| gate_error("governance body path is invalid", envelope))?;
    let body_file = body_root
        .confine(body_relative, PathIntent::Read)
        .map_err(|error| gate_error(&error.to_string(), envelope))?;
    let body = larch_adapters::read_utf8(&body_file)
        .map_err(|error| gate_error(&error.to_string(), envelope))?;
    Ok(GateArguments {
        issue,
        repository,
        body,
        repo_root,
        head_sha,
        envelope,
    })
}

fn gate_error(detail: &str, envelope: bool) -> ExitCode {
    let detail = flat_error(detail, 500);
    println!("GOVERNANCE_OK=false");
    if envelope {
        println!("ENVELOPE_ERROR={detail}");
    }
    eprintln!("ERROR: governance-gate: {detail}");
    ExitCode::from(2)
}

fn evaluate_live_gate(request: &GateArguments) -> GovernanceGateVerdict {
    let remote = with_github_service(async |service, cancellation| {
        Ok(collect_gate_evidence(service, cancellation, request).await)
    });
    let remote = match remote {
        Ok(evidence) => evidence,
        Err(ServiceFailure::Setup(_) | ServiceFailure::Operation(_)) => unavailable_evidence(),
    };
    if remote.parity.reasons == [REASON_BLOCKER_READ_UNAVAILABLE] {
        return evaluate_governance_gate(
            remote.parity,
            FreshnessVerdict {
                reasons: Vec::new(),
            },
            OwnerAdmissionVerdict::default(),
        );
    }
    let freshness = receipt_freshness(request, &remote.blocker_rows);
    evaluate_governance_gate(remote.parity, freshness, remote.owners)
}

async fn collect_gate_evidence(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    request: &GateArguments,
) -> RemoteGateEvidence {
    let Ok(native) = service
        .list_blocked_by(
            cancellation,
            request.repository.owner(),
            request.repository.name(),
            request.issue,
        )
        .await
    else {
        return unavailable_evidence();
    };
    let native_numbers = native
        .iter()
        .map(larch_adapters::github::DependencyRef::issue_number)
        .collect::<BTreeSet<_>>();
    if native_numbers.contains(&0) {
        return unavailable_evidence();
    }
    let body_numbers = parse_native_blocker_refs(&request.body)
        .into_iter()
        .collect::<BTreeSet<_>>();
    let owner = IssueMutationOwner::new(service);
    let mut snapshots = HashMap::new();
    for number in native_numbers.union(&body_numbers).copied() {
        let Ok(snapshot) = owner
            .read_snapshot(&request.repository, number, cancellation)
            .await
        else {
            return unavailable_evidence();
        };
        snapshots.insert(number, blocker_row(&snapshot));
    }
    let blocker_rows = snapshots.values().cloned().collect::<BTreeSet<_>>();
    let native_rows = native_numbers
        .iter()
        .filter_map(|number| snapshots.get(number).cloned())
        .collect::<Vec<_>>();
    let body_rows = body_numbers
        .iter()
        .filter_map(|number| snapshots.get(number).cloned())
        .collect::<Vec<_>>();
    let parity = compare_blocker_parity(&body_rows, &native_rows);
    let owners = collect_owner_evidence(service, cancellation, request).await;
    RemoteGateEvidence {
        blocker_rows: blocker_rows.into_iter().collect(),
        parity,
        owners,
    }
}

async fn collect_owner_evidence(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    request: &GateArguments,
) -> OwnerAdmissionVerdict {
    let parsed_owners = parse_owner_block(&request.body);
    let repository = RepositoryName::parse(format!(
        "{}/{}",
        request.repository.owner(),
        request.repository.name()
    ))
    .expect("GitHubRepositoryRef is a valid repository name");
    if parsed_owners.block.is_none() {
        return evaluate_owner_admission(&OwnerAdmissionRequest {
            issue: request.issue,
            body: request.body.clone(),
            reuse_sources: Vec::new(),
            active_issues: Some(Vec::new()),
            open_pr_branches: Some(Vec::new()),
            now: Utc::now(),
            repository,
        });
    }
    let source_numbers = parsed_owners
        .block
        .as_ref()
        .map_or_else(BTreeSet::new, |block| {
            block
                .owners
                .iter()
                .filter_map(|row| row.source_issue)
                .collect()
        });
    let mut reuse_sources = Vec::new();
    for number in source_numbers {
        if let Ok(issue) = service
            .issue(&request.repository, number, cancellation)
            .await
            && let Some(snapshot) = governance_issue(&issue)
        {
            reuse_sources.push(snapshot);
        }
    }
    let active_issues = list_exhaustive_issues_for_state(
        service,
        cancellation,
        &request.repository,
        GitHubIssueState::Open,
    )
    .await
    .ok()
    .and_then(|issues| issues.iter().map(governance_issue).collect());
    let open_pr_branches = service
        .list_release_open_pull_requests(
            cancellation,
            request.repository.owner(),
            request.repository.name(),
        )
        .await
        .ok()
        .and_then(|pulls| {
            (!pulls.iter().any(|pull| pull.head_ref.is_empty()))
                .then(|| pulls.into_iter().map(|pull| pull.head_ref).collect())
        });
    evaluate_owner_admission(&OwnerAdmissionRequest {
        issue: request.issue,
        body: request.body.clone(),
        reuse_sources,
        active_issues,
        open_pr_branches,
        now: Utc::now(),
        repository,
    })
}

fn unavailable_evidence() -> RemoteGateEvidence {
    RemoteGateEvidence {
        blocker_rows: Vec::new(),
        parity: ParityVerdict {
            reasons: vec![REASON_BLOCKER_READ_UNAVAILABLE.to_owned()],
        },
        owners: OwnerAdmissionVerdict::default(),
    }
}

fn blocker_row(snapshot: &IssueMutationSnapshot) -> BlockerSnapshotRow {
    BlockerSnapshotRow {
        number: snapshot.issue,
        state: state_lower(snapshot.state).to_owned(),
        updated_at: snapshot.updated_at.clone(),
    }
}

fn governance_issue(issue: &GitHubIssue) -> Option<GovernanceIssueSnapshot> {
    (issue.number > 0 && issue.state != GitHubIssueState::All).then(|| GovernanceIssueSnapshot {
        number: issue.number,
        title: issue.title.clone(),
        state: state_lower(issue.state).to_owned(),
        body: issue.body.clone(),
    })
}

fn receipt_freshness(
    request: &GateArguments,
    blocker_rows: &[BlockerSnapshotRow],
) -> FreshnessVerdict {
    let mut scope_failed = false;
    let (base_scope, head_scope) = parse_named_block(&request.body, PLAN_MARKER)
        .ok()
        .flatten()
        .zip(parse_receipt(&request.body))
        .map_or((None, None), |(plan, receipt)| {
            if let Ok(scopes) =
                receipt_scopes(&request.repo_root, &plan, &receipt, &request.head_sha)
            {
                (Some(scopes.0), Some(scopes.1))
            } else {
                scope_failed = true;
                (None, None)
            }
        });
    let mut verdict = validate_receipt_freshness(&ReceiptFreshnessRequest {
        body: request.body.clone(),
        blocker_rows: blocker_rows.to_vec(),
        base_scope,
        head_scope,
    });
    if scope_failed {
        for reason in &mut verdict.reasons {
            if reason == REASON_STALE_PLAN_BASE_SCOPE {
                REASON_PLAN_BASE_SCOPE_UNAVAILABLE.clone_into(reason);
            }
        }
    }
    verdict
}

fn receipt_scopes(
    root: &RepositoryRoot,
    plan: &str,
    receipt: &PlanReceipt,
    head_sha: &str,
) -> Result<(ScopeSnapshot, ScopeSnapshot), ()> {
    let repository = GixRepository::open(root.path()).map_err(|_| ())?;
    let base = repository
        .resolve_revision(&Revision::new(receipt.base_sha.as_bytes()))
        .map_err(|_| ())?;
    let head = repository
        .resolve_revision(&Revision::new(head_sha.as_bytes()))
        .map_err(|_| ())?;
    Ok((
        scope_snapshot(&repository, &base, plan)?,
        scope_snapshot(&repository, &head, plan)?,
    ))
}

fn scope_snapshot(
    repository: &GixRepository,
    revision: &larch_core::ObjectId,
    plan: &str,
) -> Result<ScopeSnapshot, ()> {
    let files = repository
        .files_at_commit(revision, MAX_SCOPE_FILES)
        .map_err(|_| ())?;
    let tracked = files
        .iter()
        .map(|path| std::str::from_utf8(path.as_bytes()).map(str::to_owned))
        .collect::<Result<Vec<_>, _>>()
        .map_err(|_| ())?;
    let files = declared_scope_paths(plan, &tracked)
        .into_iter()
        .map(|path| {
            let object_id = repository
                .blob_id_at_commit(revision, &larch_core::GitPath::new(path.as_bytes()))
                .map_err(|_| ())?
                .map_or_else(|| "MISSING".to_owned(), |object| object.to_hex());
            Ok(ScopeFile { path, object_id })
        })
        .collect::<Result<Vec<_>, ()>>()?;
    Ok(ScopeSnapshot {
        sha: revision.to_hex(),
        files,
    })
}

fn permits_semantic_revalidation(verdict: &GovernanceGateVerdict) -> bool {
    !verdict.parity.blocking()
        && verdict.owners.ok()
        && verdict.freshness.reasons == [REASON_STALE_PLAN_BASE_SCOPE]
}

fn emit_preflight_envelope(verdict: &GovernanceGateVerdict) {
    println!("GOVERNANCE_OK={}", verdict.ok());
    println!(
        "PERMITS_SEMANTIC_REVALIDATION={}",
        permits_semantic_revalidation(verdict)
    );
    let semantic = verdict
        .freshness
        .reasons
        .iter()
        .filter(|reason| reason.as_str() == REASON_STALE_PLAN_BASE_SCOPE)
        .cloned()
        .collect::<Vec<_>>();
    println!("SEMANTIC_REASONS={}", semantic.join(","));
    println!("BLOCKING_REASONS={}", verdict.blocking_reasons().join(","));
    println!("REPORT_ONLY_COUNT={}", verdict.owners.report_only.len());
    for (index, (token, command)) in verdict
        .owners
        .report_only
        .iter()
        .zip(&verdict.owners.cleanup_commands)
        .enumerate()
    {
        println!("REPORT_ONLY_{index}={}", envelope_line(token));
        println!("CLEANUP_{index}={}", envelope_line(command));
    }
    if !verdict.ok() && !permits_semantic_revalidation(verdict) {
        println!(
            "REFUSAL_TEXT={}",
            envelope_line(&format_gate_refusal("/implement preflight", verdict))
        );
    }
}

/// Refresh a preflight-bound receipt after semantic scope revalidation.
pub fn plan_receipt_refresh(arguments: &[OsString]) -> ExitCode {
    let request = match parse_refresh_arguments(arguments) {
        Ok(request) => request,
        Err(code) => return code,
    };
    match refresh_receipt(&request) {
        Ok(receipt) => {
            println!("PLAN_RECEIPT_REFRESHED=true");
            println!("PLAN_RECEIPT_BASE_SHA={}", receipt.base_sha);
            println!("PLAN_RECEIPT_SNAPSHOT_UPDATED=true");
            println!("PLAN_RECEIPT_SCOPE_DRIFT_LOGGED=true");
            ExitCode::SUCCESS
        }
        Err(detail) => refresh_error(&detail),
    }
}

fn parse_refresh_arguments(arguments: &[OsString]) -> Result<RefreshArguments, ExitCode> {
    let parsed = parse_required_with_help(
        arguments,
        REFRESH_PROGRAM,
        REFRESH_USAGE,
        REFRESH_HELP,
        &[
            "--issue",
            "--repo",
            "--repo-root",
            "--preflight-tmpdir",
            "--base-ref",
            "--previous-base-sha",
            "--base-sha",
        ],
        &[],
        &[
            "--issue",
            "--repo-root",
            "--preflight-tmpdir",
            "--base-ref",
            "--previous-base-sha",
            "--base-sha",
        ],
    )?;
    let fail = |detail: &str| refresh_error(detail);
    let issue = positive_issue(parsed.value("--issue")).map_err(|detail| fail(&detail))?;
    let repository = text_value(parsed.value("--repo"));
    if !repository.is_empty() && repository_ref(&repository).is_err() {
        return Err(fail("--repo must be exactly owner/name"));
    }
    let base_ref = text_value(parsed.value("--base-ref"));
    if !matches!(base_ref.as_str(), "origin/main" | "upstream/main") {
        return Err(fail("--base-ref must be origin/main or upstream/main"));
    }
    let previous_base_sha = text_value(parsed.value("--previous-base-sha"));
    if !lower_sha1(&previous_base_sha) {
        return Err(fail(
            "--previous-base-sha must be a 40-character hexadecimal SHA",
        ));
    }
    let base_sha = text_value(parsed.value("--base-sha"));
    if !lower_sha1(&base_sha) {
        return Err(fail("--base-sha must be a 40-character hexadecimal SHA"));
    }
    let root_path = absolute_path(Path::new(parsed.value("--repo-root").unwrap_or_default()))
        .map_err(|error| fail(&error.to_string()))?;
    assert_no_symlink_path_or_ancestors(&root_path).map_err(|error| fail(&error))?;
    let repo_root =
        RepositoryRoot::resolve(Some(&root_path)).map_err(|error| fail(&error.to_string()))?;
    let preflight_path = absolute_path(Path::new(
        parsed.value("--preflight-tmpdir").unwrap_or_default(),
    ))
    .map_err(|error| fail(&error.to_string()))?;
    assert_no_symlink_path_or_ancestors(&preflight_path).map_err(|error| fail(&error))?;
    let preflight_root =
        TemporaryRoot::resolve(Some(&preflight_path)).map_err(|error| fail(&error.to_string()))?;
    Ok(RefreshArguments {
        issue,
        repository,
        repo_root,
        preflight_root,
        base_ref,
        previous_base_sha,
        base_sha,
    })
}

fn refresh_error(detail: &str) -> ExitCode {
    let detail = flat_error(detail, 500);
    println!("PLAN_RECEIPT_REFRESHED=false");
    eprintln!("ERROR: plan-receipt refresh: {detail}");
    ExitCode::from(2)
}

fn refresh_receipt(request: &RefreshArguments) -> Result<PlanReceipt, String> {
    let plan = read_preflight(request, "plan-from-issue.txt")?;
    if plan.is_empty() {
        return Err("preflight plan is empty".to_owned());
    }
    let expected_plan_sha = hash_plan_block(&plan);
    let repository = GixRepository::open(request.repo_root.path())
        .map_err(|_| "repository snapshot unavailable".to_owned())?;
    let repository_slug = resolve_refresh_repository(request, &repository)?;
    let repository_ref = repository_ref(&repository_slug)
        .map_err(|()| "--repo must be exactly owner/name".to_owned())?;
    require_base(&repository, &request.base_ref, &request.base_sha)?;
    let prior = read_prior_receipt(request, &expected_plan_sha)?;
    let scope_drift = render_scope_drift(request, &repository, &plan)?;
    require_base(&repository, &request.base_ref, &request.base_sha)?;
    let (receipt, snapshot) = with_github_service(async |service, cancellation| {
        persist_refreshed_receipt(
            service,
            cancellation,
            &repository_ref,
            request,
            &expected_plan_sha,
            &prior,
        )
        .await
    })
    .map_err(ServiceFailure::into_detail)?;
    require_base(&repository, &request.base_ref, &request.base_sha)?;
    write_preflight_snapshot(request, &snapshot, &scope_drift)?;
    Ok(receipt)
}

fn read_preflight(request: &RefreshArguments, name: &str) -> Result<String, String> {
    let path = request
        .preflight_root
        .confine(name, PathIntent::Read)
        .map_err(|error| error.to_string())?;
    larch_adapters::read_utf8(&path).map_err(|error| error.to_string())
}

fn read_prior_receipt(
    request: &RefreshArguments,
    expected_plan_sha: &str,
) -> Result<PlanReceipt, String> {
    let text = read_preflight(request, "issue.json")?;
    let value: serde_json::Value = serde_json::from_str(&text)
        .map_err(|_| "preflight issue snapshot is invalid".to_owned())?;
    let object = value
        .as_object()
        .ok_or_else(|| "preflight issue snapshot is invalid".to_owned())?;
    let number_matches = match object.get("number") {
        Some(serde_json::Value::Number(number)) => number.as_u64() == Some(request.issue),
        Some(serde_json::Value::String(number)) => number == &request.issue.to_string(),
        _ => false,
    };
    if !number_matches {
        return Err("preflight issue snapshot is invalid".to_owned());
    }
    let body = object
        .get("body")
        .and_then(serde_json::Value::as_str)
        .ok_or_else(|| "preflight issue snapshot is invalid".to_owned())?;
    let receipt = parse_receipt(body)
        .ok_or_else(|| "preflight receipt identity is unavailable".to_owned())?;
    if receipt.base_sha != request.previous_base_sha {
        return Err("preflight receipt base does not match scope revalidation".to_owned());
    }
    if receipt.plan_sha256 != expected_plan_sha {
        return Err("preflight receipt plan does not match checked plan".to_owned());
    }
    Ok(receipt)
}

fn resolve_refresh_repository(
    request: &RefreshArguments,
    repository: &GixRepository,
) -> Result<String, String> {
    if !request.repository.is_empty() {
        return Ok(request.repository.clone());
    }
    repository_repo(repository)
        .ok_or_else(|| "repository slug required to refresh plan receipt".to_owned())
}

fn require_base(repository: &GixRepository, reference: &str, expected: &str) -> Result<(), String> {
    let actual = repository
        .resolve_revision(&Revision::new(reference.as_bytes()))
        .map_err(|_| "plan-receipt-refresh-base-moved".to_owned())?
        .to_hex();
    (actual == expected)
        .then_some(())
        .ok_or_else(|| "plan-receipt-refresh-base-moved".to_owned())
}

fn render_scope_drift(
    request: &RefreshArguments,
    repository: &GixRepository,
    plan: &str,
) -> Result<String, String> {
    let previous = repository
        .resolve_revision(&Revision::new(request.previous_base_sha.as_bytes()))
        .map_err(|_| "base-scope-ls-tree-failed".to_owned())?;
    let target = repository
        .resolve_revision(&Revision::new(request.base_sha.as_bytes()))
        .map_err(|_| "base-scope-ls-tree-failed".to_owned())?;
    let previous_paths = repository
        .files_at_commit(&previous, MAX_SCOPE_FILES)
        .map_err(|_| "base-scope-ls-tree-failed".to_owned())?;
    let target_paths = repository
        .files_at_commit(&target, MAX_SCOPE_FILES)
        .map_err(|_| "base-scope-ls-tree-failed".to_owned())?;
    let tracked = previous_paths
        .iter()
        .chain(&target_paths)
        .map(|path| {
            std::str::from_utf8(path.as_bytes())
                .map(str::to_owned)
                .map_err(|_| "base-scope-ls-tree-failed".to_owned())
        })
        .collect::<Result<BTreeSet<_>, _>>()?
        .into_iter()
        .collect::<Vec<_>>();
    let paths = declared_scope_paths(plan, &tracked);
    let mut rows = if paths.is_empty() {
        vec!["(no declared file paths resolved; scope drift was owner-key-only)".to_owned()]
    } else {
        let runtime = GitCommandRuntime::for_repository(request.repo_root.path())?;
        let result = runtime
            .runtime
            .block_on(
                runtime.git_cli().exact_diff(
                    ExactDiffRequest {
                        cached: false,
                        binary: false,
                        no_ext_diff: true,
                        numstat_z_rename_50: false,
                        unified_context: None,
                        name_only: false,
                        name_status: true,
                        quiet: false,
                        exit_code: false,
                        base: Some(
                            GitRef::new(&request.previous_base_sha)
                                .map_err(|error| error.to_string())?,
                        ),
                        head: Some(
                            GitRef::new(&request.base_sha).map_err(|error| error.to_string())?,
                        ),
                        paths: paths
                            .into_iter()
                            .map(GitCliPath::new)
                            .collect::<Result<Vec<_>, _>>()
                            .map_err(|error| error.to_string())?,
                    },
                    &runtime.cancellation,
                ),
            )
            .map_err(|_| "plan-receipt-scope-diff-failed".to_owned())?;
        if result.truncated() || !result.output().status().success() {
            return Err("plan-receipt-scope-diff-failed".to_owned());
        }
        String::from_utf8_lossy(result.output().stdout())
            .lines()
            .map(str::to_owned)
            .collect()
    };
    if rows.is_empty() {
        rows.push("(no declared path changed)".to_owned());
    }
    if rows.len() > MAX_SCOPE_DIFF_ROWS {
        rows.truncate(MAX_SCOPE_DIFF_ROWS - 1);
        rows.push("[truncated: additional scope-diff rows omitted]".to_owned());
    }
    let indented = render_scope_diff_rows(&rows)?;
    Ok(format!(
        "- **Preflight plan-receipt scope refresh**: semantic materiality passed.\n  - Receipt base: `{}`\n  - Reviewed target: `{}`\n  - Scope diff (JSON-quoted name-status rows):\n    ```text\n{}    ```\n",
        request.previous_base_sha, request.base_sha, indented
    ))
}

fn render_scope_diff_rows(rows: &[String]) -> Result<String, String> {
    let quoted = rows
        .iter()
        .map(serde_json::to_string)
        .collect::<Result<Vec<_>, _>>()
        .map_err(|_| "plan-receipt-scope-diff-redaction-failed".to_owned())?
        .join("\n");
    let redacted = redact_secrets_only(&quoted);
    let rendered_rows = redacted
        .lines()
        .filter(|line| !line.is_empty())
        .map(str::to_owned)
        .collect::<Vec<_>>();
    if rendered_rows.is_empty()
        || rendered_rows.iter().any(|line| {
            serde_json::from_str::<serde_json::Value>(line)
                .ok()
                .and_then(|value| value.as_str().map(str::to_owned))
                .is_none()
        })
    {
        return Err("plan-receipt-scope-diff-redaction-failed".to_owned());
    }
    let mut indented = String::new();
    for row in rendered_rows {
        writeln!(&mut indented, "    {row}").expect("writing to a String cannot fail");
    }
    Ok(indented)
}

async fn persist_refreshed_receipt(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    request: &RefreshArguments,
    expected_plan_sha: &str,
    prior: &PlanReceipt,
) -> Result<(PlanReceipt, IssueMutationSnapshot), String> {
    let owner = IssueMutationOwner::new(service);
    let snapshot = owner
        .read_snapshot(repository, request.issue, cancellation)
        .await
        .map_err(|error| error.reason().to_owned())?;
    if parse_receipt(&snapshot.body).as_ref() != Some(prior) {
        return Err("plan-receipt-refresh-source-receipt-mismatch".to_owned());
    }
    let plan = parse_named_block(&snapshot.body, PLAN_MARKER)
        .ok()
        .flatten()
        .ok_or_else(|| "plan-block-missing-for-receipt".to_owned())?;
    let blocker_rows = receipt_blocker_rows(
        service,
        &owner,
        repository,
        request.issue,
        &snapshot.body,
        cancellation,
    )
    .await?;
    let receipt = PlanReceipt {
        plan_sha256: hash_plan_block(&plan),
        base_sha: request.base_sha.clone(),
        blockers_sha256: hash_blocker_rows(&blocker_rows),
        owners_sha256: hash_owner_rows(&parse_owner_block(&snapshot.body).raw_rows),
    };
    if receipt.plan_sha256 != expected_plan_sha {
        return Err("plan-receipt-refresh-plan-mismatch".to_owned());
    }
    if receipt.plan_sha256 != prior.plan_sha256
        || receipt.blockers_sha256 != prior.blockers_sha256
        || receipt.owners_sha256 != prior.owners_sha256
    {
        return Err("plan-receipt-refresh-governance-input-mismatch".to_owned());
    }
    let updated =
        upsert_receipt(&snapshot.body, &receipt).map_err(|defect| defect.reason().to_owned())?;
    let after = if updated == snapshot.body {
        snapshot
    } else {
        let authorization = authorization_request("", "", "", true);
        owner
            .apply(
                cancellation,
                &authorization,
                &named_block_mutation_request(
                    repository,
                    snapshot.issue,
                    &snapshot,
                    PLAN_MARKER,
                    updated,
                ),
            )
            .await
            .map_err(|error| error.reason().to_owned())?
            .after
    };
    if parse_receipt(&after.body).as_ref() != Some(&receipt) {
        return Err("plan-receipt-readback-mismatch".to_owned());
    }
    let refreshed = owner
        .read_snapshot(repository, request.issue, cancellation)
        .await
        .map_err(|error| error.reason().to_owned())?;
    if parse_receipt(&refreshed.body).as_ref() != Some(&receipt) {
        return Err("plan-receipt-refresh-snapshot-mismatch".to_owned());
    }
    Ok((receipt, refreshed))
}

fn write_preflight_snapshot(
    request: &RefreshArguments,
    snapshot: &IssueMutationSnapshot,
    scope_drift: &str,
) -> Result<(), String> {
    let labels = snapshot
        .labels
        .iter()
        .map(|label| {
            OrderedJson::Object(vec![(
                "name".to_owned(),
                OrderedJson::String(label.clone()),
            )])
        })
        .collect();
    let payload = OrderedJson::Object(vec![
        (
            "body".to_owned(),
            OrderedJson::String(snapshot.body.clone()),
        ),
        ("labels".to_owned(), OrderedJson::Array(labels)),
        (
            "number".to_owned(),
            OrderedJson::Number(serde_json::Number::from(snapshot.issue)),
        ),
        (
            "state".to_owned(),
            OrderedJson::String(state_upper(snapshot.state).to_owned()),
        ),
        (
            "title".to_owned(),
            OrderedJson::String(snapshot.title.clone()),
        ),
        (
            "updatedAt".to_owned(),
            OrderedJson::String(snapshot.updated_at.clone()),
        ),
    ]);
    let issue_json = format!(
        "{}\n",
        python_json_dumps(&payload).map_err(|_| "preflight issue snapshot is invalid".to_owned())?
    );
    let issue_path = request
        .preflight_root
        .confine("issue.json", PathIntent::Write)
        .map_err(|error| error.to_string())?;
    atomic_write_utf8(&issue_path, &issue_json, 0o600).map_err(|error| error.to_string())?;
    let drift_path = request
        .preflight_root
        .confine("receipt-scope-drift.md", PathIntent::Write)
        .map_err(|error| error.to_string())?;
    atomic_write_utf8(&drift_path, scope_drift, 0o600).map_err(|error| error.to_string())
}

fn positive_issue(value: Option<&OsStr>) -> Result<u64, String> {
    let text = text_value(value);
    text.parse::<u64>()
        .ok()
        .filter(|number| *number > 0 && text.bytes().all(|byte| byte.is_ascii_digit()))
        .ok_or_else(|| "--issue must be a positive issue number".to_owned())
}

fn text_value(value: Option<&OsStr>) -> String {
    value.unwrap_or_default().to_string_lossy().into_owned()
}

fn lower_sha1(value: &str) -> bool {
    value.len() == 40
        && value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

fn envelope_line(value: &str) -> String {
    value.split_whitespace().collect::<Vec<_>>().join(" ")
}

const fn state_lower(state: GitHubIssueState) -> &'static str {
    match state {
        GitHubIssueState::Open => "open",
        GitHubIssueState::Closed | GitHubIssueState::All => "closed",
    }
}

const fn state_upper(state: GitHubIssueState) -> &'static str {
    match state {
        GitHubIssueState::Open => "OPEN",
        GitHubIssueState::Closed | GitHubIssueState::All => "CLOSED",
    }
}

#[cfg(test)]
mod tests {
    use super::{governance_gate, plan_receipt_refresh};
    use crate::github_service::with_test_github_service;
    use larch_core::{
        BlockerSnapshotRow, PLAN_MARKER, PlanReceipt, hash_blocker_rows, hash_owner_rows,
        hash_plan_block, parse_named_block, parse_owner_block, upsert_receipt,
    };
    use larch_test_support::{GitFixture, GitRepository, IssueServiceExchange, IssueServiceStub};
    use serde_json::json;
    use std::{ffi::OsString, fs, process::ExitCode, sync::Arc};
    use tempfile::TempDir;

    fn loopback_service(
        exchanges: impl IntoIterator<Item = IssueServiceExchange>,
    ) -> (
        Arc<dyn Fn() -> larch_adapters::github::OctocrabGitHubService + Send + Sync>,
        IssueServiceStub,
    ) {
        let server = IssueServiceStub::start(exchanges).expect("start issue stub");
        let base_url = server.base_url().to_owned();
        let factory = Arc::new(move || {
            larch_adapters::github::OctocrabGitHubService::with_test_base(&base_url)
        });
        (factory, server)
    }

    fn issue_response(number: u64, title: &str, body: &str, updated_at: &str) -> serde_json::Value {
        let mut value: serde_json::Value = serde_json::from_str(include_str!(
            "../../larch-adapters/fixtures/github_issue.json"
        ))
        .expect("valid issue fixture");
        value["id"] = json!(number * 10);
        value["number"] = json!(number);
        value["title"] = json!(title);
        value["body"] = json!(body);
        value["state"] = json!("open");
        value["url"] = json!(format!(
            "https://example.test/repos/owner/repo/issues/{number}"
        ));
        value["repository_url"] = json!("https://example.test/repos/owner/repo");
        value["html_url"] = json!(format!("https://github.com/owner/repo/issues/{number}"));
        value["labels"] = json!([]);
        value["updated_at"] = json!(updated_at);
        value
    }

    fn sha(repository: &GitRepository, reference: &str) -> String {
        let output = repository
            .git(["rev-parse", "--verify", reference])
            .expect("run rev-parse");
        assert!(output.success());
        String::from_utf8_lossy(&output.stdout).trim().to_owned()
    }

    fn receipt(body: &str, base_sha: &str) -> PlanReceipt {
        let plan = parse_named_block(body, PLAN_MARKER)
            .expect("plan parses")
            .expect("plan exists");
        PlanReceipt {
            plan_sha256: hash_plan_block(&plan),
            base_sha: base_sha.to_owned(),
            blockers_sha256: hash_blocker_rows(&[] as &[BlockerSnapshotRow]),
            owners_sha256: hash_owner_rows(&parse_owner_block(body).raw_rows),
        }
    }

    #[test]
    fn clean_gate_uses_typed_remote_snapshots_and_local_scope() {
        let repository = GitRepository::builder(GitFixture::Refs)
            .build()
            .expect("git fixture");
        let body = "<!-- larch:plan:start -->\n## Breaking changes and migration\n\nNone.\n<!-- larch:plan:end -->\n";
        let body_file = repository.root().join("gate-body.md");
        fs::write(&body_file, body).expect("write body");
        let (github, server) = loopback_service([IssueServiceExchange::json(
            "GET",
            "/repos/owner/repo/issues/7/dependencies/blocked_by",
            200,
            b"[]".to_vec(),
        )
        .expect("dependency response")]);
        let arguments = [
            "--issue".into(),
            "7".into(),
            "--repo".into(),
            "owner/repo".into(),
            "--body-file".into(),
            body_file.into_os_string(),
            "--repo-root".into(),
            repository.root().as_os_str().into(),
            "--head-sha".into(),
            sha(&repository, "HEAD").into(),
        ];

        let code = with_test_github_service(github, || governance_gate(&arguments));

        assert_eq!(code, ExitCode::SUCCESS);
        assert_eq!(server.finish().expect("stub completed").len(), 1);
    }

    #[test]
    #[allow(clippy::too_many_lines)] // One ordered mutation exchange verifies CAS, read-back, and refreshed evidence.
    fn refresh_mutates_only_the_plan_block_and_rewrites_preflight_evidence() {
        let repository = GitRepository::builder(GitFixture::Refs)
            .build()
            .expect("git fixture");
        let previous_base = sha(&repository, "HEAD");
        repository
            .write("second.txt", b"second\n")
            .expect("write second file");
        assert!(
            repository
                .git(["add", "second.txt"])
                .expect("git add")
                .success()
        );
        assert!(
            repository
                .git(["commit", "--quiet", "-m", "second"])
                .expect("git commit")
                .success()
        );
        assert!(
            repository
                .git(["update-ref", "refs/remotes/origin/main", "HEAD"])
                .expect("update base ref")
                .success()
        );
        let base_sha = sha(&repository, "origin/main");
        let plan = "### UPDATED: tracked.txt\n\nKeep the tracked fixture stable.\n\n## Breaking changes and migration\n\nNone.\n";
        let seed =
            format!("Before.\n<!-- larch:plan:start -->\n{plan}<!-- larch:plan:end -->\nAfter.\n");
        let prior = receipt(&seed, &previous_base);
        let old_body = upsert_receipt(&seed, &prior).expect("old receipt");
        let next = receipt(&old_body, &base_sha);
        let new_body = upsert_receipt(&old_body, &next).expect("new receipt");
        let preflight = TempDir::new().expect("preflight root");
        fs::write(preflight.path().join("plan-from-issue.txt"), plan).expect("write plan");
        fs::write(
            preflight.path().join("issue.json"),
            format!(
                "{}\n",
                json!({
                    "body": old_body,
                    "labels": [],
                    "number": "7",
                    "state": "OPEN",
                    "title": "[DESIGNED] refresh",
                    "updatedAt": "2026-08-20T00:00:00Z"
                })
            ),
        )
        .expect("write issue snapshot");
        let old_issue = issue_response(7, "[DESIGNED] refresh", &old_body, "2026-08-20T00:00:00Z");
        let new_issue = issue_response(7, "[DESIGNED] refresh", &new_body, "2026-08-20T00:00:01Z");
        let (github, server) = loopback_service([
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/7",
                200,
                serde_json::to_vec(&old_issue).expect("old issue"),
            )
            .expect("initial read"),
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/7/dependencies/blocked_by",
                200,
                b"[]".to_vec(),
            )
            .expect("dependency read"),
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/7",
                200,
                serde_json::to_vec(&old_issue).expect("CAS issue"),
            )
            .expect("CAS read"),
            IssueServiceExchange::json(
                "PATCH",
                "/repos/owner/repo/issues/7",
                200,
                serde_json::to_vec(&new_issue).expect("mutation issue"),
            )
            .expect("mutation"),
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/7",
                200,
                serde_json::to_vec(&new_issue).expect("read-back issue"),
            )
            .expect("mutation read-back"),
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/7",
                200,
                serde_json::to_vec(&new_issue).expect("snapshot issue"),
            )
            .expect("snapshot read-back"),
        ]);
        let arguments: Vec<OsString> = vec![
            "--issue".into(),
            "7".into(),
            "--repo".into(),
            "owner/repo".into(),
            "--repo-root".into(),
            repository.root().as_os_str().into(),
            "--preflight-tmpdir".into(),
            preflight.path().as_os_str().into(),
            "--base-ref".into(),
            "origin/main".into(),
            "--previous-base-sha".into(),
            previous_base.into(),
            "--base-sha".into(),
            base_sha.clone().into(),
        ];

        let code = with_test_github_service(github, || plan_receipt_refresh(&arguments));

        assert_eq!(code, ExitCode::SUCCESS);
        assert_eq!(server.finish().expect("stub completed").len(), 6);
        let refreshed: serde_json::Value = serde_json::from_str(
            &fs::read_to_string(preflight.path().join("issue.json")).expect("refreshed issue"),
        )
        .expect("valid refreshed issue JSON");
        assert_eq!(refreshed["body"], new_body);
        assert_eq!(refreshed["updatedAt"], "2026-08-20T00:00:01Z");
        let drift = fs::read_to_string(preflight.path().join("receipt-scope-drift.md"))
            .expect("scope drift");
        assert!(drift.contains(&base_sha));
        assert!(drift.contains("no declared path changed"));
    }
}
