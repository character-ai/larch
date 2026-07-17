use std::{collections::BTreeSet, sync::LazyLock};

use regex::Regex;

use crate::{Finding, LintError, PathSelector, RepoPath, Repository, Rule, RuleMetadata, RuleOutput};

const NAME: &str = "bg-wait-coverage";
const DESCRIPTION: &str = "Reject unallowlisted background-launch prose in skills";
const ALLOWLIST_PATH: &str = "crates/larch-lint/config/bg-wait-allowlist.txt";

static BACKGROUND: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"run_in_background\s*:?\s*true")
        .expect("background-launch expression is valid")
});

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/bg-wait-coverage.toml",
);

#[derive(Debug)]
pub struct BgWaitCoverageRule;

pub static RULE: BgWaitCoverageRule = BgWaitCoverageRule;

impl Rule for BgWaitCoverageRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let allowlist = load_allowlist(repository)?;
        let selector = PathSelector::new(&["skills/**/*.md"], &[])?;
        let mut findings = Vec::new();
        for path in selector.select(repository) {
            if allowlist.contains(path.as_str()) {
                continue;
            }
            for (index, line) in repository.read_utf8(path)?.lines().enumerate() {
                if !BACKGROUND.is_match(line)
                    || line.contains("do NOT set")
                    || line.contains("do not set")
                {
                    continue;
                }
                let number = u32::try_from(index + 1).map_err(|_| {
                    LintError::new(format!("{}: line number exceeds u32", path.as_str()))
                })?;
                findings.push(Finding::new(
                    path.as_str(),
                    number,
                    format!("run_in_background is forbidden outside {ALLOWLIST_PATH}"),
                ));
            }
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

fn load_allowlist(repository: &Repository) -> Result<BTreeSet<String>, LintError> {
    let path = RepoPath::from_trusted(ALLOWLIST_PATH);
    let text = repository.read_utf8(&path)?;
    let mut rows = BTreeSet::new();
    for (index, raw) in text.lines().enumerate() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let Some((path, reason)) = line.split_once('\t') else {
            return Err(LintError::new(format!(
                "{ALLOWLIST_PATH}: malformed allowlist row {}",
                index + 1
            )));
        };
        if path.is_empty() || reason.trim().is_empty() {
            return Err(LintError::new(format!(
                "{ALLOWLIST_PATH}: allowlist row needs path and reason {}",
                index + 1
            )));
        }
        if !rows.insert(path.to_owned()) {
            return Err(LintError::new(format!(
                "{ALLOWLIST_PATH}: duplicate allowlist path {path}"
            )));
        }
    }
    Ok(rows)
}

crate::register_rule!(METADATA, RULE);
