use std::sync::LazyLock;

use regex::Regex;

use crate::{
    Finding, LintError, PathSelector, Repository, Rule, RuleMetadata, RuleOutput,
    syntax::{FenceState, MarkdownDocument},
};

const NAME: &str = "literal-counts";
const DESCRIPTION: &str = "Reject drift-prone literal item counts in Markdown";
const MESSAGE: &str = "literal item count drifts when the underlying count changes - prefer structural prose (e.g., \"the panel\", \"the reviewer set\") or add `<!-- lint-literal-counts: allow <reason> -->` on the same line if the count is fixed/historical";

static VIOLATION: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^\s*\d+\s+(assertions|rules|bullets|rows|reviewers|agents|specialists|cases|fields|sections)\b")
        .expect("literal-counts violation expression is valid")
});
static ALLOW_PRAGMA: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"<!--\s*lint-literal-counts:\s*allow\s+(\S.*?)\s*-->")
        .expect("literal-counts allow expression is valid")
});

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/literal-counts.toml",
);

#[derive(Debug)]
pub struct LiteralCountsRule;

pub static RULE: LiteralCountsRule = LiteralCountsRule;

impl Rule for LiteralCountsRule {
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
            let source = repository.read_utf8(path)?;
            let source = source.strip_prefix('\u{feff}').unwrap_or(&source);
            for line in MarkdownDocument::new(source).lines() {
                if line.fence_state() != FenceState::Outside
                    || !VIOLATION.is_match(line.text())
                    || ALLOW_PRAGMA.is_match(line.text())
                {
                    continue;
                }
                let number = u32::try_from(line.number()).map_err(|_| {
                    LintError::new(format!("{}: line number exceeds u32", path.as_str()))
                })?;
                findings.push(Finding::new(path.as_str(), number, MESSAGE));
            }
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);
