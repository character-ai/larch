//! Library-only execution support for `larch lint` repository-policy rules.
//!
//! This crate owns the command contract, tracked-file discovery,
//! repository-relative path selection, shared syntax support, and testable
//! rule execution. Rules register from their own modules; no central registry
//! must change when a later rule is added. The `larch` executable links this
//! crate through its composition root; this crate does not ship a binary.

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

#[doc(hidden)]
pub use cli::run_cli_with_io;
pub use cli::{GitleaksArguments, GitleaksMode, LintArguments, LintDispatch, run_cli};
pub use command_registry::{
    CommandAuditSelector, audit_migration_issue_commands, audit_migration_issue_commands_content,
    command_audit_selectors, render_command_progress, sync_command_registry,
};
pub use metadata::{
    RuleMetadata, RuleRegistration, registered_rule_registry, validate_migration_ledger,
};
pub use repository::{Git, GitCli, PathSelector, RepoPath, Repository};
pub use runner::{
    ExitCode, Finding, LintError, LintReport, Rule, RuleDispatchPriority, RuleOutput, RuleRegistry,
    RuleTiming, finding_exit_code, render_contract_lines, run,
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
