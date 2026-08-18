//! Enforce the closed analytics ownership boundary for issue #7684.
//!
//! The command, service, and Git projections stay owned by their respective
//! rules. This rule composes those syntax-aware queries and adds the two
//! shipped analyzer prompt entrypoints that were formerly standalone Python
//! scripts.

use crate::{
    Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput, command_registry,
    syntax,
};

use super::{git_ownership, issue_python_free, service_ownership};

const NAME: &str = "analytics-7684-closure";
const DESCRIPTION: &str =
    "Reject incomplete command, analyzer-entrypoint, GitHub-service, and Git ownership evidence for #7684";
const PLANNING_ISSUE: u64 = 7684;

struct AnalyzerEntrypoint {
    skill_path: &'static str,
    domain: &'static str,
    verb: &'static str,
    retired_script: &'static str,
}

const ANALYZER_ENTRYPOINTS: [AnalyzerEntrypoint; 2] = [
    AnalyzerEntrypoint {
        skill_path: "skills/fluff-analysis/SKILL.md",
        domain: "fluff-analysis",
        verb: "analyze",
        retired_script: "skills/fluff-analysis/scripts/fluff-analysis.py",
    },
    AnalyzerEntrypoint {
        skill_path: "skills/voter-calibration/SKILL.md",
        domain: "voter-calibration",
        verb: "analyze",
        retired_script: "skills/voter-calibration/scripts/voter-calibration.py",
    },
];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/analytics-7684-closure.toml",
);

#[derive(Debug)]
pub struct Analytics7684ClosureRule;

pub static RULE: Analytics7684ClosureRule = Analytics7684ClosureRule;

crate::register_rule!(METADATA, RULE);

impl Rule for Analytics7684ClosureRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let retained_modules = issue_python_free::retained_module_paths_for_issue(7684);
        let boundary_is_present = command_registry::planning_issue_has_command_rows(
            repository,
            PLANNING_ISSUE,
        )? || !retained_modules.is_empty()
            || ANALYZER_ENTRYPOINTS.iter().any(|entrypoint| {
                repository
                    .paths()
                    .binary_search(&RepoPath::from_trusted(entrypoint.skill_path))
                    .is_ok()
            });
        if !boundary_is_present {
            return Ok(RuleOutput::default());
        }

        let mut findings = command_registry::planning_issue_closure_findings(repository, PLANNING_ISSUE)?;
        findings.extend(retained_module_closure_findings(retained_modules));
        findings.extend(
            service_ownership::unresolved_github_service_operations_for_issue(
                repository,
                PLANNING_ISSUE,
            )?
            .into_iter()
            .map(|(operation, line)| {
                Finding::new(
                    "docs/github-service-inventory.md",
                    line,
                    format!(
                        "GitHub service inventory still has incomplete #{PLANNING_ISSUE} ownership for operation: {operation}"
                    ),
                )
            }),
        );
        require_git_inventory(repository)?;
        findings.extend(
            git_ownership::unresolved_later_domain_paths(repository, PLANNING_ISSUE)?
                .into_iter()
                .map(|path| {
                    Finding::new(
                        git_ownership::INVENTORY_PATH,
                        1,
                        format!(
                            "Git-operation inventory still has unresolved later-domain #{PLANNING_ISSUE} row: {path}"
                        ),
                    )
                }),
        );
        for entrypoint in &ANALYZER_ENTRYPOINTS {
            analyzer_entrypoint_findings(repository, entrypoint, &mut findings)?;
        }
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

fn retained_module_closure_findings(paths: impl IntoIterator<Item = &'static str>) -> Vec<Finding> {
    paths
        .into_iter()
        .map(|path| {
            Finding::new(
                path,
                1,
                format!("planning issue #{PLANNING_ISSUE} retains Python module ownership"),
            )
        })
        .collect()
}

fn require_git_inventory(repository: &Repository) -> Result<(), LintError> {
    let path = RepoPath::from_trusted(git_ownership::INVENTORY_PATH);
    if repository.paths().binary_search(&path).is_err() {
        return Err(LintError::new(format!(
            "{}: required Git operation ownership matrix is missing",
            git_ownership::INVENTORY_PATH
        )));
    }
    Ok(())
}

fn analyzer_entrypoint_findings(
    repository: &Repository,
    entrypoint: &AnalyzerEntrypoint,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    let skill_path = RepoPath::from_trusted(entrypoint.skill_path);
    if repository.paths().binary_search(&skill_path).is_err() {
        findings.push(Finding::new(
            entrypoint.skill_path,
            1,
            format!(
                "shipped analytics entrypoint is missing; expected Rust owner {} {}",
                entrypoint.domain, entrypoint.verb
            ),
        ));
        return Ok(());
    }

    let source = repository.read_utf8(&skill_path)?;
    let commands = syntax::markdown_shell_commands(&source)?;
    if !commands
        .iter()
        .any(|command| invokes_rust_owner(command.words(), entrypoint))
    {
        findings.push(Finding::new(
            entrypoint.skill_path,
            1,
            format!(
                "shipped analytics entrypoint does not invoke its Rust owner: {} {}",
                entrypoint.domain, entrypoint.verb
            ),
        ));
    }
    for command in commands {
        if invokes_retired_python_analyzer(command.words(), entrypoint.retired_script) {
            findings.push(Finding::new(
                entrypoint.skill_path,
                u32::try_from(command.line()).map_err(|_| {
                    LintError::new(format!(
                        "{}: command line is out of range",
                        entrypoint.skill_path
                    ))
                })?,
                format!(
                    "shipped analytics entrypoint directly invokes retired Python analyzer: {}",
                    entrypoint.retired_script
                ),
            ));
        }
    }

    let retired_script = RepoPath::from_trusted(entrypoint.retired_script);
    if repository.paths().binary_search(&retired_script).is_ok() {
        findings.push(Finding::new(
            entrypoint.retired_script,
            1,
            "superseded shipped Python analyzer remains",
        ));
    }
    Ok(())
}

fn invokes_rust_owner(words: &[String], entrypoint: &AnalyzerEntrypoint) -> bool {
    words.windows(3).any(|window| {
        is_larch_script(&window[0])
            && window[1] == entrypoint.domain
            && window[2] == entrypoint.verb
    })
}

fn is_larch_script(word: &str) -> bool {
    word == "scripts/larch.sh" || word.ends_with("/scripts/larch.sh")
}

fn invokes_retired_python_analyzer(words: &[String], retired_script: &str) -> bool {
    words.iter().any(|word| word.ends_with(retired_script))
}

#[cfg(test)]
mod tests {
    use super::{PLANNING_ISSUE, invokes_retired_python_analyzer, retained_module_closure_findings};
    use crate::Finding;

    #[test]
    fn reports_retained_analytics_module_ownership() {
        assert_eq!(
            retained_module_closure_findings(["python/larch/issue/_report.py"]),
            vec![Finding::new(
                "python/larch/issue/_report.py",
                1,
                format!("planning issue #{PLANNING_ISSUE} retains Python module ownership"),
            )]
        );
    }

    #[test]
    fn recognizes_a_retired_analyzer_with_a_non_python_wrapper() {
        let words = vec![
            "uv".to_owned(),
            "run".to_owned(),
            "${CLAUDE_PLUGIN_ROOT}/skills/fluff-analysis/scripts/fluff-analysis.py".to_owned(),
        ];
        assert!(invokes_retired_python_analyzer(
            &words,
            "skills/fluff-analysis/scripts/fluff-analysis.py"
        ));
    }
}
