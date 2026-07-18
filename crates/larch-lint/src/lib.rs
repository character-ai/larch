//! Shared execution support for larch repository-policy rules.
//!
//! This crate owns the command contract, tracked-file discovery,
//! repository-relative path selection, shared syntax support, and testable
//! rule execution. Rules register from their own modules; no central registry
//! must change when a later rule is added.

mod cli;
mod command_registry;
mod metadata;
mod repository;
mod runner;
pub mod suppression;
pub mod syntax;

mod rules {
    automod::dir!("src/rules");
}

pub use cli::run_cli;
pub use command_registry::{render_command_progress, sync_command_registry};
pub use metadata::{
    RuleMetadata, RuleRegistration, registered_rule_registry, validate_migration_ledger,
};
pub use repository::{Git, GitCli, PathSelector, RepoPath, Repository};
pub use runner::{
    ExitCode, Finding, LintError, LintReport, Rule, RuleOutput, RuleRegistry, finding_exit_code,
    render_contract_lines, run,
};

/// Register a static rule and its co-located metadata without editing a shared
/// registry. The matching migration-ledger record is verified before a rule
/// run can complete.
#[macro_export]
macro_rules! register_rule {
    ($metadata:ident, $rule:ident) => {
        inventory::submit! {
            $crate::RuleRegistration::new(&$metadata, &$rule)
        }
    };
}
