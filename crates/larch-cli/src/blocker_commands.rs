//! `blocker all-open` and the shared open-blocker discovery it exposes.
//!
//! Discovery reads native GitHub issue dependencies first and falls back to
//! prose keywords in the issue body and comments only when the native edge set
//! is empty. Every read fails open: a transport, authorization, or contract
//! failure yields no blockers rather than a refusal, preserving the historical
//! posture `/implement` documents as known limitation D3.

use crate::github_repository_resolution::{ambient_repo, repository_ref};
use larch_adapters::{
    NoopProcessObserver, TokioProcessRunner,
    github::OctocrabGitHubService,
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    GitHubIssueState, GitHubRepositoryRef, GitHubService, emit_kv, parse_prose_blockers,
};
use std::{env, ffi::OsString, process::ExitCode, sync::Arc};

/// Emit the space-joined open blockers for one issue.
///
/// The verb always exits `0`. An unusable issue number, an unresolvable
/// repository, and a failed GitHub read are all reported as an empty
/// `BLOCKERS` row.
pub fn all_open(arguments: &[OsString]) -> ExitCode {
    let (issue, repo) = parse_all_open_arguments(arguments);
    let blockers = issue
        .and_then(|issue| resolve_repo_for(repo.as_deref()).map(|repo| open_blockers(issue, &repo)))
        .unwrap_or_default();
    emit_blockers(&blockers);
    ExitCode::SUCCESS
}

/// Emit the `BLOCKERS` row the way every consumer parses it.
pub fn emit_blockers(blockers: &[u64]) {
    emit_kv("BLOCKERS", &render_blockers(blockers));
}

/// Render the blocker list as the single space-joined value of its row.
fn render_blockers(blockers: &[u64]) -> String {
    blockers
        .iter()
        .map(u64::to_string)
        .collect::<Vec<_>>()
        .join(" ")
}

/// Resolve the repository slug an explicit flag names, or the ambient one.
///
/// Returns `None` when neither is available, which callers report as "no
/// blockers" rather than as a failure.
pub fn resolve_repo_for(explicit: Option<&str>) -> Option<String> {
    explicit
        .filter(|repo| !repo.is_empty())
        .map(str::to_owned)
        .or_else(ambient_repo)
}

/// Return the open blockers for `issue`, native edges first, then prose.
///
/// Every failure path yields an empty list.
#[must_use]
pub fn open_blockers(issue: u64, repo: &str) -> Vec<u64> {
    let Ok(reference) = repository_ref(repo) else {
        return Vec::new();
    };
    let Ok(working_directory) = env::current_dir() else {
        return Vec::new();
    };
    let Ok(runtime) = LarchRuntime::new() else {
        return Vec::new();
    };
    runtime.block_on(async {
        let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
        let cancellation = Cancellation::new();
        let Ok(service) =
            OctocrabGitHubService::from_gh(&runner, &working_directory, &cancellation).await
        else {
            return Vec::new();
        };
        let native = native_open_blockers(&service, &reference, issue, &cancellation).await;
        if native.is_empty() {
            prose_open_blockers(&service, &reference, issue, &cancellation).await
        } else {
            native
        }
    })
}

async fn native_open_blockers(
    service: &OctocrabGitHubService,
    repo: &GitHubRepositoryRef,
    issue: u64,
    cancellation: &Cancellation,
) -> Vec<u64> {
    let Ok(edges) = service
        .list_blocked_by(cancellation, repo.owner(), repo.name(), issue)
        .await
    else {
        return Vec::new();
    };
    let mut open: Vec<u64> = edges
        .into_iter()
        .filter(larch_adapters::github::DependencyRef::is_open)
        .map(|edge| edge.issue_number())
        .collect();
    open.sort_unstable();
    open.dedup();
    open
}

async fn prose_open_blockers(
    service: &OctocrabGitHubService,
    repo: &GitHubRepositoryRef,
    issue: u64,
    cancellation: &Cancellation,
) -> Vec<u64> {
    let mut documents = Vec::new();
    if let Ok(subject) = service.issue(repo, issue, cancellation).await {
        documents.push(subject.body);
    }
    if let Ok(comments) = service.list_comments(repo, issue, cancellation).await {
        documents.extend(comments.into_iter().map(|comment| comment.body));
    }
    let mut open = Vec::new();
    for candidate in prose_candidates(&documents, issue) {
        if let Ok(referenced) = service.issue(repo, candidate, cancellation).await
            && referenced.state == GitHubIssueState::Open
        {
            open.push(candidate);
        }
    }
    open
}

/// Collect the distinct, sorted blocker references `documents` declare.
///
/// The subject issue never blocks itself, and a reference repeated across the
/// body and its comments is read once.
fn prose_candidates(documents: &[String], issue: u64) -> Vec<u64> {
    let mut candidates: Vec<u64> = Vec::new();
    for document in documents {
        for reference in parse_prose_blockers(document) {
            if reference != issue && !candidates.contains(&reference) {
                candidates.push(reference);
            }
        }
    }
    candidates.sort_unstable();
    candidates
}

/// Scan the legacy hand-rolled option pairs, ignoring every other token.
///
/// A trailing `--issue` or `--repo` with no value drops that option, matching
/// the legacy scanner rather than raising a usage error.
fn parse_all_open_arguments(arguments: &[OsString]) -> (Option<u64>, Option<String>) {
    let mut issue = None;
    let mut repo = None;
    let mut index = 0;
    while index < arguments.len() {
        let token = arguments[index].to_string_lossy().into_owned();
        index += 1;
        let Some(value) = arguments.get(index) else {
            if token == "--issue" {
                return (None, repo);
            }
            if token == "--repo" {
                return (issue, None);
            }
            continue;
        };
        match token.as_str() {
            "--issue" => {
                issue = larch_core::normal_issue(&value.to_string_lossy());
                index += 1;
            }
            "--repo" => {
                repo = Some(value.to_string_lossy().into_owned());
                index += 1;
            }
            _ => {}
        }
    }
    (issue, repo)
}

#[cfg(test)]
mod tests {
    use super::{parse_all_open_arguments, prose_candidates, render_blockers, resolve_repo_for};
    use std::ffi::OsString;

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    fn documents(values: &[&str]) -> Vec<String> {
        values.iter().map(|value| (*value).to_owned()).collect()
    }

    #[test]
    fn prose_candidates_dedupe_across_documents_and_drop_the_subject() {
        let found = prose_candidates(
            &documents(&[
                "Blocked by #12 and Depends on #9",
                "Requires #12",
                "Depends on #8059",
            ]),
            8059,
        );

        assert_eq!(found, vec![9, 12], "sorted, distinct, never self-blocking");
        assert!(prose_candidates(&documents(&["no references here"]), 8059).is_empty());
        assert!(prose_candidates(&[], 8059).is_empty());
    }

    #[test]
    fn an_explicit_repo_short_circuits_ambient_resolution() {
        assert_eq!(
            resolve_repo_for(Some("owner/repo")).as_deref(),
            Some("owner/repo")
        );
        // An empty flag value falls through to the ambient probe, so it is not
        // asserted here; only the short-circuit is environment independent.
    }

    #[test]
    fn the_blockers_row_joins_with_single_spaces() {
        // An empty list must still render an empty value, not a missing row:
        // consumers branch on `BLOCKERS=` being present and empty.
        assert_eq!(render_blockers(&[]), "");
        assert_eq!(render_blockers(&[7]), "7");
        assert_eq!(render_blockers(&[7, 9, 11]), "7 9 11");
    }

    #[test]
    fn the_scanner_reads_pairs_and_skips_unknown_tokens() {
        let (issue, repo) = parse_all_open_arguments(&arguments(&[
            "noise", "--issue", "42", "more", "--repo", "o/r",
        ]));

        assert_eq!(issue, Some(42));
        assert_eq!(repo.as_deref(), Some("o/r"));
    }

    #[test]
    fn a_trailing_option_drops_its_own_value_only() {
        let (issue, repo) = parse_all_open_arguments(&arguments(&["--repo", "o/r", "--issue"]));
        assert_eq!(issue, None);
        assert_eq!(repo.as_deref(), Some("o/r"));

        let (issue, repo) = parse_all_open_arguments(&arguments(&["--issue", "7", "--repo"]));
        assert_eq!(issue, Some(7));
        assert_eq!(repo, None);
    }

    #[test]
    fn a_non_positive_issue_reads_as_absent() {
        assert_eq!(
            parse_all_open_arguments(&arguments(&["--issue", "abc"])).0,
            None
        );
        assert_eq!(
            parse_all_open_arguments(&arguments(&["--issue", "0"])).0,
            None
        );
    }
}
