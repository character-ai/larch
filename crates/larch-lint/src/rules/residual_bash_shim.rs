//! Require each production shell script to be an inventoried residual or a thin larch shim.

use std::sync::LazyLock;

use regex::Regex;

use crate::{
    Finding, LintError, PathSelector, RepoPath, Repository, Rule, RuleMetadata, RuleOutput,
    syntax::{leaf_bash_commands, shell_command_words},
};

use super::{production_cargo_run::is_fixture_surface, residual_bash_manifest};

const NAME: &str = "residual-bash-shim";
const DESCRIPTION: &str = "Require production shell scripts to be residuals or thin larch shims";
const MAX_SHIM_LINES: usize = 25;
const MESSAGE: &str = "production shell script must be listed in scripts/residual-bash-paths.txt or be an at-most-25-line exec-only scripts/larch.sh shim";

static ENV_ASSIGNMENT: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[A-Za-z_][A-Za-z0-9_]*=").expect("environment assignment expression is valid")
});

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/residual-bash-shim.toml",
);

#[derive(Debug)]
pub struct ResidualBashShimRule;

pub static RULE: ResidualBashShimRule = ResidualBashShimRule;

impl Rule for ResidualBashShimRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let residuals = residual_bash_manifest::required_paths(repository)?;
        let shell_scripts = PathSelector::new(&["**/*.sh"], &[])?;
        let mut findings = Vec::new();
        for path in shell_scripts.select(repository) {
            let path_text = path.as_str();
            if is_fixture_surface(path_text) || residuals.contains(path) {
                continue;
            }
            let source = repository.read_utf8(path)?;
            if !is_larch_shim(repository, path, &source)? {
                findings.push(Finding::new(path_text, 1, MESSAGE));
            }
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

fn is_larch_shim(
    repository: &Repository,
    path: &RepoPath,
    source: &str,
) -> Result<bool, LintError> {
    if source.lines().count() > MAX_SHIM_LINES {
        return Ok(false);
    }
    let syntax = repository.bash_syntax(path)?;
    if syntax.root_node().has_error() {
        return Ok(false);
    }
    let mut exec_count = 0;
    for command in leaf_bash_commands(&syntax) {
        let words = shell_command_words(command, source);
        let Some(program) = words.first().map(String::as_str) else {
            return Ok(false);
        };
        if program == "exec" {
            if !execs_larch_bootstrap(&words) {
                return Ok(false);
            }
            exec_count += 1;
        } else if !matches!(
            program,
            "[" | "cd" | "dirname" | "export" | "pwd" | "set" | "test"
        ) {
            return Ok(false);
        }
    }
    Ok(exec_count == 1)
}

fn execs_larch_bootstrap(words: &[String]) -> bool {
    let mut index = 1;
    if words.get(index).is_some_and(|word| word == "env") {
        index += 1;
        while words
            .get(index)
            .is_some_and(|word| ENV_ASSIGNMENT.is_match(word))
        {
            index += 1;
        }
    }
    words.get(index).is_some_and(|program| {
        let program = program.trim_start_matches("./");
        program == "scripts/larch.sh" || program.ends_with("/scripts/larch.sh")
    })
}

crate::register_rule!(METADATA, RULE);
