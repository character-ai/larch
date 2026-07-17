use crate::{Finding, LintError, PathSelector, Repository, Rule, RuleMetadata, RuleOutput};

const NAME: &str = "fixture";
const DESCRIPTION: &str = "Validate decentralized rule registration";

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/fixture.toml",
);

#[derive(Debug)]
pub struct FixtureRule;

pub static RULE: FixtureRule = FixtureRule;

impl Rule for FixtureRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let selector = PathSelector::new(&["fixtures/**/*.fixture"], &[])?;
        let mut findings = Vec::new();
        for path in selector.select(repository) {
            for (index, line) in repository.read_utf8(path)?.lines().enumerate() {
                if line == "forbidden" {
                    let line_number = u32::try_from(index + 1).map_err(|_| {
                        LintError::new(format!("{}: line number exceeds u32", path.as_str()))
                    })?;
                    findings.push(Finding::new(path.as_str(), line_number, "fixture violation"));
                }
            }
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);
