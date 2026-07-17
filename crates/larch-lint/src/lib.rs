//! Shared execution support for larch repository-policy rules.
//!
//! Rules are registered by the next foundation stage. This crate owns the
//! command contract, tracked-file discovery, repository-relative path
//! selection, diagnostics, and testable rule execution.

mod cli;
mod repository;
mod runner;

pub use cli::run_cli;
pub use repository::{Git, GitCli, PathSelector, RepoPath, Repository};
pub use runner::{ExitCode, Finding, LintError, Rule, RuleRegistry, finding_exit_code, run};
