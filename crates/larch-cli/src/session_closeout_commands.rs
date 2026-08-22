//! Rust-owned closeout commands for local implementation sessions.
//!
//! The command keeps the historical cleanup contract intentionally small: it
//! switches to `main`, refreshes it from `origin`, then removes the completed
//! feature branch. Every Git mutation is represented by the typed adapter.

use larch_adapters::{
    BranchMutationRequest, CheckoutRequest, FetchRequest, GitCli, GitCliPolicy, GitRef, GitRefspec,
    GitRemote, GixRepository, NoopProcessObserver, PullRequest, TokioProcessRunner,
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{Head, ReferenceKind, RepositoryRead, Revision};
use std::{env, ffi::OsString, path::Path, process::ExitCode, sync::Arc};

const USAGE: &str = "Usage: local-cleanup.sh --branch BRANCH_NAME";
const RETRY_ATTEMPTS: usize = 3;

/// Run `session local-cleanup` with the historic session-finalization envelope.
pub fn local_cleanup(arguments: &[OsString]) -> ExitCode {
    let branch = match branch_argument(arguments) {
        Ok(branch) => branch,
        Err(ArgumentError::Missing) => {
            eprintln!("ERROR: --branch is required");
            eprintln!("{USAGE}");
            return ExitCode::from(1);
        }
        Err(ArgumentError::Invalid) => {
            eprintln!("{USAGE}");
            return ExitCode::from(1);
        }
    };
    if branch == "main" {
        eprintln!("ERROR: --branch must not be 'main'");
        return ExitCode::from(1);
    }

    let mut outcome = CleanupOutcome::default();
    let Ok(cwd) = env::current_dir() else {
        eprintln!("🔄 Switching to main...");
        eprintln!("❌ Failed to checkout main");
        outcome.emit();
        return ExitCode::SUCCESS;
    };

    eprintln!("🔄 Switching to main...");
    if !run_git(&cwd, LocalCleanupGit::CheckoutMain) {
        eprintln!("❌ Failed to checkout main");
        outcome.current_branch = current_branch(&cwd);
        outcome.emit();
        return ExitCode::SUCCESS;
    }
    "main".clone_into(&mut outcome.current_branch);

    eprintln!("🔄 Fetching origin main...");
    if !retry_git(&cwd, LocalCleanupGit::FetchMain) {
        eprintln!("⚠ Failed to fetch origin main (continuing)");
    }
    eprintln!("🔄 Fast-forwarding local main from origin/main...");
    if !retry_git(&cwd, LocalCleanupGit::PullMain) {
        emit_pull_failure(&cwd);
        outcome.emit();
        return ExitCode::SUCCESS;
    }

    match branch_state(&cwd, &branch) {
        BranchState::Missing => {
            eprintln!("Local branch {branch} was already deleted");
            outcome.cleanup_success = true;
        }
        BranchState::Error => eprintln!("❌ Failed to check local branch {branch}"),
        BranchState::Exists => {
            eprintln!("🔄 Deleting local branch {branch}...");
            if run_git(&cwd, LocalCleanupGit::DeleteBranch(&branch)) {
                outcome.cleanup_success = true;
                outcome.branch_deleted = true;
            } else {
                eprintln!("❌ Failed to delete local branch {branch}");
            }
        }
    }
    if outcome.cleanup_success {
        eprintln!("✅ Local cleanup complete");
    }
    outcome.emit();
    ExitCode::SUCCESS
}

#[derive(Default)]
struct CleanupOutcome {
    cleanup_success: bool,
    current_branch: String,
    branch_deleted: bool,
}

impl CleanupOutcome {
    fn emit(&self) {
        println!("CLEANUP_SUCCESS={}", self.cleanup_success);
        println!(
            "CURRENT_BRANCH={}",
            if self.current_branch.is_empty() {
                "unknown"
            } else {
                &self.current_branch
            }
        );
        println!("BRANCH_DELETED={}", self.branch_deleted);
    }
}

enum ArgumentError {
    Missing,
    Invalid,
}

fn branch_argument(arguments: &[OsString]) -> Result<String, ArgumentError> {
    let strings = arguments
        .iter()
        .map(|argument| argument.to_str().map(str::to_owned))
        .collect::<Option<Vec<_>>>()
        .ok_or(ArgumentError::Invalid)?;
    let mut branch = None;
    let mut index = 0;
    while index < strings.len() {
        let argument = &strings[index];
        if argument == "--branch" {
            let Some(value) = strings.get(index + 1) else {
                return Err(ArgumentError::Missing);
            };
            if value.starts_with('-') {
                return Err(ArgumentError::Missing);
            }
            branch = Some(value.clone());
            index += 2;
            continue;
        }
        if let Some(value) = argument.strip_prefix("--branch=") {
            branch = Some(value.to_owned());
            index += 1;
            continue;
        }
        return Err(ArgumentError::Invalid);
    }
    branch
        .filter(|value| !value.is_empty())
        .ok_or(ArgumentError::Missing)
}

#[derive(Clone, Copy)]
enum LocalCleanupGit<'a> {
    CheckoutMain,
    FetchMain,
    PullMain,
    DeleteBranch(&'a str),
}

fn retry_git(cwd: &Path, operation: LocalCleanupGit<'_>) -> bool {
    (0..RETRY_ATTEMPTS).any(|_| match operation {
        LocalCleanupGit::FetchMain => run_git(cwd, LocalCleanupGit::FetchMain),
        LocalCleanupGit::PullMain => run_git(cwd, LocalCleanupGit::PullMain),
        LocalCleanupGit::CheckoutMain | LocalCleanupGit::DeleteBranch(_) => false,
    })
}

fn run_git(cwd: &Path, operation: LocalCleanupGit<'_>) -> bool {
    let Ok(policy) = GitCliPolicy::new(cwd.to_path_buf()) else {
        return false;
    };
    let Ok(runtime) = LarchRuntime::current_thread() else {
        return false;
    };
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    let git = GitCli::new(&runner, policy);
    let cancellation = Cancellation::new();
    runtime.block_on(async {
        match operation {
            LocalCleanupGit::CheckoutMain => {
                let Ok(name) = GitRef::new("main") else {
                    return false;
                };
                git.checkout(
                    CheckoutRequest::Branch {
                        create: false,
                        force: false,
                        no_track: false,
                        name,
                        start_point: None,
                    },
                    &cancellation,
                )
                .await
                .is_ok()
            }
            LocalCleanupGit::FetchMain => {
                let (Ok(remote), Ok(refspec)) = (GitRemote::new("origin"), GitRefspec::new("main"))
                else {
                    return false;
                };
                git.fetch(
                    FetchRequest {
                        remote,
                        refspec: Some(refspec),
                        quiet: false,
                        no_tags: false,
                        mode: larch_adapters::FetchMode::Standard,
                    },
                    &cancellation,
                )
                .await
                .is_ok()
            }
            LocalCleanupGit::PullMain => {
                let (Ok(remote), Ok(refspec)) = (GitRemote::new("origin"), GitRefspec::new("main"))
                else {
                    return false;
                };
                git.pull(
                    PullRequest {
                        remote,
                        refspec: Some(refspec),
                        fast_forward_only: true,
                    },
                    &cancellation,
                )
                .await
                .is_ok()
            }
            LocalCleanupGit::DeleteBranch(branch) => {
                let Ok(name) = GitRef::new(branch) else {
                    return false;
                };
                git.branch_mutation(
                    BranchMutationRequest::Delete { force: true, name },
                    &cancellation,
                )
                .await
                .is_ok()
            }
        }
    })
}

fn current_branch(cwd: &Path) -> String {
    GixRepository::discover(cwd)
        .ok()
        .and_then(|repository| repository.head().ok())
        .and_then(|head| match head {
            Head::Symbolic { name, .. } => name
                .as_bytes()
                .strip_prefix(b"refs/heads/")
                .map(|branch| String::from_utf8_lossy(branch).into_owned()),
            Head::Detached { .. } | Head::Unborn { .. } => None,
        })
        .filter(|branch| !branch.is_empty())
        .unwrap_or_else(|| "unknown".to_owned())
}

enum BranchState {
    Exists,
    Missing,
    Error,
}

fn branch_state(cwd: &Path, branch: &str) -> BranchState {
    if GitRef::new(branch).is_err() {
        return BranchState::Error;
    }
    let Ok(repository) = GixRepository::discover(cwd) else {
        return BranchState::Error;
    };
    let Ok(references) = repository.references() else {
        return BranchState::Error;
    };
    let wanted = format!("refs/heads/{branch}");
    if references.iter().any(|reference| {
        reference.kind == ReferenceKind::LocalBranch
            && reference.name.as_bytes() == wanted.as_bytes()
    }) {
        BranchState::Exists
    } else {
        BranchState::Missing
    }
}

fn emit_pull_failure(cwd: &Path) {
    let ahead = ahead_of_origin(cwd);
    if ahead > 0 {
        eprintln!(
            "❌ Failed to pull origin main; local main is ahead of origin/main by {ahead} commit(s). Push or reconcile local main before retrying."
        );
    } else {
        eprintln!("❌ Failed to pull origin main");
    }
}

/// Count commits by which local `HEAD` is ahead of `origin/main`.
pub fn ahead_of_origin(cwd: &Path) -> u64 {
    GixRepository::discover(cwd)
        .ok()
        .and_then(|repository| {
            let origin_main = repository
                .resolve_revision(&Revision::new("origin/main"))
                .ok()?;
            let head = repository.resolve_revision(&Revision::new("HEAD")).ok()?;
            repository.commit_count_range(&origin_main, &head).ok()
        })
        .unwrap_or(0)
}
