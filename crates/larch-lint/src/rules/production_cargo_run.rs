//! Reject Cargo and target-directory execution from production runtime surfaces.

use std::path::Path;

use crate::{
    Finding, LintError, Repository, Rule, RuleMetadata, RuleOutput,
    syntax::{
        ShellCommand, json_shell_commands, markdown_shell_commands, shell_commands_from_tree,
    },
};

use super::larch_runtime_entrypoint::is_production_surface;

pub(super) use crate::syntax::executable_index;

const NAME: &str = "production-cargo-run";
const DESCRIPTION: &str = "Reject production Cargo and target-directory larch execution";
const MESSAGE: &str =
    "production runtime must use scripts/larch.sh; cargo and target-directory execution are development-only";

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/production-cargo-run.toml",
);

#[derive(Debug)]
pub struct ProductionCargoRunRule;

pub static RULE: ProductionCargoRunRule = ProductionCargoRunRule;

impl Rule for ProductionCargoRunRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let mut findings = Vec::new();
        for path in repository.paths() {
            let path_text = path.as_str();
            if !is_production_surface(path_text) || is_fixture_surface(path_text) {
                continue;
            }
            let source = repository.read_utf8(path)?;
            let extension = extension(path_text).unwrap_or("");
            findings.extend(if extension.eq_ignore_ascii_case("sh") {
                let syntax = repository.bash_syntax(path)?;
                check_commands(path_text, shell_commands_from_tree(&syntax, &source, 0))?
            } else if extension.eq_ignore_ascii_case("md") {
                check_markdown(path_text, &source)?
            } else if extension.eq_ignore_ascii_case("json") {
                check_json(path_text, &source)?
            } else {
                Vec::new()
            });
        }
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

fn extension(path: &str) -> Option<&str> {
    Path::new(path).extension()?.to_str()
}

pub(super) fn is_fixture_surface(path: &str) -> bool {
    path.split('/').any(|part| part == "fixtures")
        || path
            .rsplit('/')
            .next()
            .is_some_and(|name| name.starts_with("test-"))
}

fn check_commands(path: &str, commands: Vec<ShellCommand>) -> Result<Vec<Finding>, LintError> {
    commands
        .into_iter()
        .filter(|command| prohibited_argv(command.words()))
        .map(|command| {
            let number = u32::try_from(command.line())
                .map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))?;
            Ok(Finding::new(path, number, MESSAGE))
        })
        .collect()
}

fn prohibited_argv(words: &[String]) -> bool {
    let Some(index) = executable_index(words) else {
        return false;
    };
    let program = &words[index];
    if is_target_larch(program) {
        return true;
    }
    is_cargo(program)
        && cargo_subcommand(words, index).is_some_and(|word| matches!(word, "run" | "install"))
}

fn cargo_subcommand(words: &[String], cargo_index: usize) -> Option<&str> {
    words[cargo_index + 1..]
        .iter()
        .find(|word| !word.starts_with('-'))
        .map(String::as_str)
}

fn is_cargo(word: &str) -> bool {
    word.rsplit('/').next().is_some_and(|name| matches!(name, "cargo" | "cargo.exe"))
}

fn is_target_larch(word: &str) -> bool {
    let normalized = word
        .replace('\\', "/")
        .trim_start_matches("./")
        .to_ascii_lowercase();
    normalized.ends_with("target/debug/larch")
        || normalized.ends_with("target/debug/larch.exe")
        || normalized.ends_with("target/release/larch")
        || normalized.ends_with("target/release/larch.exe")
}

fn check_markdown(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    check_commands(path, markdown_shell_commands(source)?)
}

fn check_json(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    check_commands(path, json_shell_commands(path, source)?)
}

#[cfg(test)]
mod tests {
    use super::{is_target_larch, prohibited_argv};

    #[test]
    fn recognizes_platform_target_paths() {
        assert!(is_target_larch(r"C:\repo\target\debug\larch.exe"));
        assert!(is_target_larch("./target/release/larch"));
    }

    #[test]
    fn does_not_treat_command_arguments_as_executables() {
        let words = ["echo".to_owned(), "cargo".to_owned(), "run".to_owned()];
        assert!(!prohibited_argv(&words));
        let cargo_metadata = [
            "cargo".to_owned(),
            "metadata".to_owned(),
            "--filter-platform".to_owned(),
            "cargo".to_owned(),
            "run".to_owned(),
        ];
        assert!(!prohibited_argv(&cargo_metadata));
    }
}
