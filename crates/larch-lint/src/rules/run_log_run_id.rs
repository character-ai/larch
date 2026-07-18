//! Reject committed run-log directories that use a non-unique placeholder id.
//!
//! # Crate survey (issue #7608)
//!
//! | Need | Candidates | Selection |
//! |---|---|---|
//! | Repository discovery | shared `Repository`, direct `git` calls | Reuse the shared snapshot to inspect only committed paths. |
//! | Placeholder grammar | workspace `regex`, UUID parsing | Use `regex` for the existing narrow `run-<N>` rejection. UUID parsing would reject valid non-placeholder session identifiers and change the contract. |

use std::sync::LazyLock;

use regex::Regex;

use crate::{Finding, LintError, Repository, Rule, RuleMetadata, RuleOutput};

const NAME: &str = "run-log-run-id";
const DESCRIPTION: &str = "Reject non-unique placeholder run-log run-ids";

static PLACEHOLDER_PATH: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^larch-logs/(implement|design|review)/run-[0-9]+(?:/|$)")
        .expect("placeholder run-log path expression is valid")
});

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/run-log-run-id.toml",
);

#[derive(Debug)]
pub struct RunLogRunIdRule;

pub static RULE: RunLogRunIdRule = RunLogRunIdRule;

impl Rule for RunLogRunIdRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let findings = repository
            .paths()
            .iter()
            .filter(|path| repository.is_committed(path) && PLACEHOLDER_PATH.is_match(path.as_str()))
            .map(|path| {
                Finding::new(
                    path.as_str(),
                    1,
                    "committed run-log directory uses a non-unique placeholder run-id (issue #4397); use the unique session run-id, not run-<N>",
                )
            })
            .collect();
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);
