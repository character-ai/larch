//! Fail-closed discovery of the merge-group producer for trusted cache publication,
//! plus candidate staging and verification for main-cache publication.

mod candidate;

pub use candidate::{
    CandidateContract, CandidateError, CandidateMember, CandidateRequest, CandidateSource,
    VerifiedCandidate, parse_maximum_bytes, parse_source, parse_tool_versions, promote_candidate,
    stage_candidate, verify_candidate,
};

use crate::{
    GitHubActionsError, GitHubActionsErrorKind, GitHubActionsService, GitHubRepositoryRef,
    ProcessCancellation, ReleaseSourceCommit, WorkflowJob, WorkflowRun, WorkflowRunFilters,
};

const CI_WORKFLOW: &str = "ci.yaml";
const COMPLETED: &str = "completed";
const MERGE_GROUP: &str = "merge_group";
const SUCCESS: &str = "success";
const MAX_SOURCE_RUNS: usize = 100;
const REQUIRED_JOBS: [&str; 2] = ["rust-full", "rust-lint"];

/// Resolve the one successful merge-group CI run eligible to publish main caches.
///
/// The selected run must have produced the supplied main SHA, and both cache
/// producers must have completed successfully. Any missing, duplicate, or
/// mismatched evidence refuses publication rather than choosing a nearby run.
///
/// # Errors
///
/// Returns a typed Actions error when the source SHA is malformed, Actions
/// evidence cannot be read, or the exact successful producer cannot be proven.
pub async fn resolve_main_cache_merge_group_source(
    service: &dyn GitHubActionsService,
    repository: &GitHubRepositoryRef,
    source_sha: &str,
    cancellation: &dyn ProcessCancellation,
) -> Result<u64, GitHubActionsError> {
    validate_main_cache_source_sha(source_sha)?;
    let filters = source_filters(source_sha);
    let runs = service
        .list_workflow_runs(repository, &filters, cancellation)
        .await?;
    let run_id = select_source_run(&runs, source_sha)?;
    let jobs = service
        .workflow_jobs(repository, run_id, cancellation)
        .await?;
    verify_required_jobs(&jobs)?;
    Ok(run_id)
}

/// Validate the immutable main SHA used to select trusted cache evidence.
///
/// # Errors
///
/// Returns a typed input error unless the value is a lowercase 40-character
/// Git commit identifier.
pub fn validate_main_cache_source_sha(source_sha: &str) -> Result<(), GitHubActionsError> {
    if source_sha.len() == 40 && ReleaseSourceCommit::parse(source_sha).is_ok() {
        Ok(())
    } else {
        Err(GitHubActionsError::new(
            GitHubActionsErrorKind::InvalidInput,
            "main cache source SHA must be a lowercase 40-character Git commit",
        ))
    }
}

fn source_filters(source_sha: &str) -> WorkflowRunFilters {
    WorkflowRunFilters {
        workflow: Some(CI_WORKFLOW.to_owned()),
        event: Some(MERGE_GROUP.to_owned()),
        status: Some(COMPLETED.to_owned()),
        commit: Some(source_sha.to_owned()),
        limit: MAX_SOURCE_RUNS,
        ..WorkflowRunFilters::default()
    }
}

fn select_source_run(runs: &[WorkflowRun], source_sha: &str) -> Result<u64, GitHubActionsError> {
    let matching = runs
        .iter()
        .filter(|run| {
            run.database_id > 0
                && run.event == MERGE_GROUP
                && run.status == COMPLETED
                && run.conclusion.as_deref() == Some(SUCCESS)
                && run.head_sha == source_sha
        })
        .collect::<Vec<_>>();
    match matching.as_slice() {
        [run] => Ok(run.database_id),
        _ => Err(GitHubActionsError::new(
            GitHubActionsErrorKind::Response,
            "expected exactly one successful CI merge-group run",
        )),
    }
}

fn verify_required_jobs(jobs: &[WorkflowJob]) -> Result<(), GitHubActionsError> {
    let mut successful = jobs
        .iter()
        .filter(|job| {
            REQUIRED_JOBS.contains(&job.name.as_str())
                && job.status == COMPLETED
                && job.conclusion.as_deref() == Some(SUCCESS)
        })
        .map(|job| job.name.as_str())
        .collect::<Vec<_>>();
    successful.sort_unstable();
    if successful.iter().copied().eq(REQUIRED_JOBS.iter().copied()) {
        return Ok(());
    }
    Err(GitHubActionsError::new(
        GitHubActionsErrorKind::Response,
        "successful merge-group producer is missing required Rust jobs",
    ))
}

#[cfg(test)]
mod tests {
    use super::{
        COMPLETED, MERGE_GROUP, REQUIRED_JOBS, SUCCESS, select_source_run, source_filters,
        validate_main_cache_source_sha, verify_required_jobs,
    };
    use crate::{WorkflowJob, WorkflowRun};

    const SHA: &str = "0123456789abcdef0123456789abcdef01234567";

    fn run(id: u64, sha: &str, event: &str, conclusion: Option<&str>) -> WorkflowRun {
        WorkflowRun {
            database_id: id,
            status: COMPLETED.to_owned(),
            conclusion: conclusion.map(str::to_owned),
            head_sha: sha.to_owned(),
            event: event.to_owned(),
            attempt: 1,
        }
    }

    fn job(name: &str, conclusion: Option<&str>) -> WorkflowJob {
        WorkflowJob {
            name: name.to_owned(),
            status: COMPLETED.to_owned(),
            conclusion: conclusion.map(str::to_owned),
            wall_clock_seconds: None,
        }
    }

    #[test]
    fn source_filters_and_selection_bind_the_exact_successful_merge_group_run() {
        let filters = source_filters(SHA);
        assert_eq!(filters.workflow.as_deref(), Some("ci.yaml"));
        assert_eq!(filters.event.as_deref(), Some(MERGE_GROUP));
        assert_eq!(filters.status.as_deref(), Some(COMPLETED));
        assert_eq!(filters.commit.as_deref(), Some(SHA));
        assert_eq!(filters.limit, 100);

        let selected = run(42, SHA, MERGE_GROUP, Some(SUCCESS));
        assert_eq!(
            select_source_run(
                &[
                    run(9, SHA, "pull_request", Some(SUCCESS)),
                    run(
                        10,
                        "fedcba9876543210fedcba9876543210fedcba98",
                        MERGE_GROUP,
                        Some(SUCCESS)
                    ),
                    selected,
                ],
                SHA,
            ),
            Ok(42)
        );
    }

    #[test]
    fn source_resolution_refuses_ambiguous_or_incomplete_evidence() {
        let selected = run(42, SHA, MERGE_GROUP, Some(SUCCESS));
        assert!(select_source_run(&[selected.clone(), selected], SHA).is_err());
        assert!(verify_required_jobs(&[job(REQUIRED_JOBS[0], Some(SUCCESS))]).is_err());
        assert!(
            verify_required_jobs(&[
                job(REQUIRED_JOBS[0], Some(SUCCESS)),
                job(REQUIRED_JOBS[0], Some(SUCCESS)),
                job(REQUIRED_JOBS[1], Some(SUCCESS)),
            ])
            .is_err()
        );
        assert!(validate_main_cache_source_sha(SHA).is_ok());
        assert!(validate_main_cache_source_sha("ABCDEF").is_err());
        assert!(validate_main_cache_source_sha(&SHA.to_uppercase()).is_err());
        assert!(validate_main_cache_source_sha(&"a".repeat(64)).is_err());
    }
}
