//! Reject references to the removed Family-B background-monitor fence.

use crate::{Finding, LintError, PathSelector, Repository, Rule, RuleMetadata, RuleOutput};

const NAME: &str = "p3119-fence-absence";
const DESCRIPTION: &str = "Reject removed Family-B background-monitor tokens in prose";
const TOKENS: &[&str] = &[
    "breadcrumb-monitor.sh",
    "LARCH_DONE_SENTINEL",
    "LARCH_STATUS_FILE",
    "LARCH_PAIRED_PID_FILE",
    "LARCH_BREADCRUMB_STREAM",
    "LARCH_BREADCRUMB_MONITOR_SH",
    "LARCH_BREADCRUMBS_SURFACED_FILE",
    "monitor_rc",
    "larch_quiet_append_done_trap",
    "larch_quiet_write_paired_pid_file",
    "Background pair required",
    "BASH_AUTHORING.md §4",
    "background+monitor invocation",
];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/p3119-fence-absence.toml",
);

#[derive(Debug)]
pub struct P3119FenceAbsenceRule;

pub static RULE: P3119FenceAbsenceRule = P3119FenceAbsenceRule;

impl Rule for P3119FenceAbsenceRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let selector = PathSelector::new(&["**/*.md"], &["larch-logs/**"])?;
        let mut findings = Vec::new();
        for path in selector.select(repository) {
            for (index, line) in repository.read_utf8(path)?.lines().enumerate() {
                for token in TOKENS {
                    if line.contains(token) {
                        findings.push(Finding::new(
                            path.as_str(),
                            u32::try_from(index + 1).map_err(|_| {
                                LintError::new(format!("{}: line number exceeds u32", path.as_str()))
                            })?,
                            format!("still references removed Family-B token: {token}"),
                        ));
                    }
                }
            }
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);
