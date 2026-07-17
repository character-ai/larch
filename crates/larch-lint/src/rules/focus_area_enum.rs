//! Keep the reviewer focus-area enum security-complete at every documented callsite.

use std::sync::LazyLock;

use regex::Regex;

use crate::{Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput};

const NAME: &str = "focus-area-enum";
const DESCRIPTION: &str = "Require security in documented reviewer focus-area enumerations";
const BACKTICKED_FILES: &[&str] = &[
    "skills/shared/reviewer-templates.md",
    "agents/code-reviewer.md",
    "agents/reviewer-structure.md",
    "agents/reviewer-correctness.md",
    "agents/reviewer-testing.md",
    "agents/reviewer-security.md",
    "agents/reviewer-edge-cases.md",
    "agents/reviewer-plan-fidelity.md",
    "agents/reviewer-code-robustness.md",
    "docs/review-agents.md",
];
const UNQUOTED_FILES: &[&str] = &[
    "skills/review/SKILL.md",
    "python/larch/rendering/rendering.py",
    "skills/design/SKILL.md",
];

static BACKTICKED_ENUM: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"`code-quality`.*`risk-integration`.*`correctness`.*`architecture`")
        .expect("backticked focus-area expression is valid")
});

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/focus-area-enum.toml",
);

#[derive(Debug)]
pub struct FocusAreaEnumRule;

pub static RULE: FocusAreaEnumRule = FocusAreaEnumRule;

impl Rule for FocusAreaEnumRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let mut findings = Vec::new();
        check_files(
            repository,
            BACKTICKED_FILES,
            |line| BACKTICKED_ENUM.is_match(line),
            "backticked",
            &mut findings,
        )?;
        check_files(
            repository,
            UNQUOTED_FILES,
            |line| line.contains("code-quality / risk-integration / correctness / architecture"),
            "unquoted",
            &mut findings,
        )?;
        Ok(RuleOutput::from_findings(findings))
    }
}

fn check_files<M>(
    repository: &Repository,
    paths: &[&str],
    predicate: M,
    style: &str,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError>
where
    M: Fn(&str) -> bool,
{
    for path in paths {
        let repository_path = RepoPath::from_trusted(path);
        if repository.paths().binary_search(&repository_path).is_err() {
            findings.push(Finding::new(*path, 1, "expected file is missing"));
            continue;
        }
        let source = repository.read_utf8(&repository_path)?;
        let mut found = false;
        for (index, line) in source.lines().enumerate() {
            if !predicate(line) {
                continue;
            }
            found = true;
            if line.contains("security") {
                continue;
            }
            findings.push(Finding::new(
                *path,
                u32::try_from(index + 1)
                    .map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))?,
                format!("{style} focus-area enumeration does not include security"),
            ));
        }
        if !found {
            findings.push(Finding::new(
                *path,
                1,
                format!("no {style} focus-area enumeration found"),
            ));
        }
    }
    Ok(())
}

crate::register_rule!(METADATA, RULE);
