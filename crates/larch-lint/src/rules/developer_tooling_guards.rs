//! Migration guards for the developer-tooling surface (issues #8101 and #8345).
//!
//! # Crate survey (issue #8101)
//!
//! | Need | Candidates | Selection |
//! |---|---|---|
//! | Rust-owned verb set | fresh TOML walk, shared command-registry importer | Reuse [`crate::command_registry::rust_owned_selectors`]. |
//! | `python/cli.py` selector scan | local regex, shared extract_selectors | Reuse [`crate::command_registry::python_cli_selectors`]. |
//! | Shell and prompt argv discovery | line substrings, shared shell/Markdown parsers | Reuse [`crate::syntax::shell_commands`] and [`crate::syntax::markdown_shell_commands`]. |
//! | Python child-process discovery | local tree walk, production cargo guard | Reuse [`super::production_cargo_run::python_subprocess_call_lines`]. |
//! | Git inventory closure | fresh Markdown parser, Git ownership rule | Reuse the narrow inventory query from [`super::git_ownership`]. |
//! | Disposition retire modules | new TSV, shared ledger reader | Read the #8095 disposition TSV; derive `python/larch/lint/lint_<verb>.py` for unregistered `retire` rows. |

use std::{collections::BTreeSet, path::Path};

use crate::{
    Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput, command_registry,
    syntax,
};

use super::{
    git_ownership,
    production_cargo_run::{executable_index, python_subprocess_call_lines},
};
use super::python_lint_disposition::is_verb_token;

const RUST_OWNED_NAME: &str = "developer-tooling-rust-owned-python";
const RUST_OWNED_DESCRIPTION: &str =
    "Reject python/cli.py callers of Rust-owned commands on developer tooling surfaces";
const PROCESS_NAME: &str = "developer-tooling-crate-process";
const PROCESS_DESCRIPTION: &str =
    "Reject developer-tooling child processes for crate-owned capabilities";
const INVENTORY_CLOSURE_NAME: &str = "developer-tooling-7685-closure";
const INVENTORY_CLOSURE_DESCRIPTION: &str =
    "Reject unresolved Git-operation inventory rows owned by #7685";
const RETIRED_NAME: &str = "retired-disposition-module";
const RETIRED_DESCRIPTION: &str =
    "Reject leftover modules for unregistered retire disposition rows";

const DISPOSITION_PATH: &str = "crates/larch-lint/data/python-lint-disposition.tsv";
const RESIDUAL_BASH_PATH: &str = "scripts/residual-bash-paths.txt";
const RELEASE_WORKFLOW_PATH: &str = ".github/workflows/rust-release-assets.yaml";
const GITHUB_AUTH_CONFIG_PATH: &str = ".github/actions/github-auth-config/action.yaml";
const CLEAN_INSTALL_BOOTSTRAP_PATH: &str = "scripts/larch.sh";
const FAILURE_REPORT_PATH: &str = "scripts/file-failure-report-cross-repo.sh";
const SUBMODULE_GUARD_PATH: &str = "scripts/block-submodule-edit.sh";
const STALE_PLUGIN_PATH: &str = "scripts/check-stale-plugin.sh";
const SESSIONSTART_HEALTH_PATH: &str = "scripts/sessionstart-health.sh";
const COMBINE_ISSUES_SEARCH_PATH: &str =
    "skills/combine-issues/scripts/search-implementing-issue.sh";
const STAGED_GUIDELINES_PATH: &str =
    "skills/implement/scripts/step-architectural-guidelines-write-staged.sh";
const MAKEFILE_PATH: &str = "Makefile";
const PRE_COMMIT_PATH: &str = ".pre-commit-config.yaml";
const OTHER_DOMAIN_SKILL_PREFIXES: [&str; 2] = [
    ".claude/skills/audit-runs/",
    ".claude/skills/release/",
];

/// Child-process executables a Rust crate already owns. Vendor products stay
/// permitted; only explicit, manifest-backed boundary exceptions remain.
const CRATE_OWNED_PROGRAMS: [&str; 3] = ["gcloud", "gh", "git"];
const EXTERNAL_PRODUCTS: [&str; 3] = ["claude", "codex", "cursor"];

pub static RUST_OWNED_METADATA: RuleMetadata = RuleMetadata::new(
    RUST_OWNED_NAME,
    RUST_OWNED_DESCRIPTION,
    "crates/larch-lint/migration-ledger/developer-tooling-rust-owned-python.toml",
);

pub static PROCESS_METADATA: RuleMetadata = RuleMetadata::new(
    PROCESS_NAME,
    PROCESS_DESCRIPTION,
    "crates/larch-lint/migration-ledger/developer-tooling-crate-process.toml",
);

pub static INVENTORY_CLOSURE_METADATA: RuleMetadata = RuleMetadata::new(
    INVENTORY_CLOSURE_NAME,
    INVENTORY_CLOSURE_DESCRIPTION,
    "crates/larch-lint/migration-ledger/developer-tooling-7685-closure.toml",
);

pub static RETIRED_METADATA: RuleMetadata = RuleMetadata::new(
    RETIRED_NAME,
    RETIRED_DESCRIPTION,
    "crates/larch-lint/migration-ledger/retired-disposition-module.toml",
);

#[derive(Debug)]
pub struct DeveloperToolingRustOwnedPythonRule;

pub static RUST_OWNED_RULE: DeveloperToolingRustOwnedPythonRule =
    DeveloperToolingRustOwnedPythonRule;

#[derive(Debug)]
pub struct DeveloperToolingCrateProcessRule;

pub static PROCESS_RULE: DeveloperToolingCrateProcessRule = DeveloperToolingCrateProcessRule;

#[derive(Debug)]
pub struct DeveloperTooling7685ClosureRule;

pub static INVENTORY_CLOSURE_RULE: DeveloperTooling7685ClosureRule =
    DeveloperTooling7685ClosureRule;

#[derive(Debug)]
pub struct RetiredDispositionModuleRule;

pub static RETIRED_RULE: RetiredDispositionModuleRule = RetiredDispositionModuleRule;

crate::register_rule!(RUST_OWNED_METADATA, RUST_OWNED_RULE);
crate::register_rule!(PROCESS_METADATA, PROCESS_RULE);
crate::register_rule!(INVENTORY_CLOSURE_METADATA, INVENTORY_CLOSURE_RULE);
crate::register_rule!(RETIRED_METADATA, RETIRED_RULE);

impl Rule for DeveloperToolingRustOwnedPythonRule {
    fn name(&self) -> &'static str {
        RUST_OWNED_NAME
    }

    fn description(&self) -> &'static str {
        RUST_OWNED_DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let rust_owned = command_registry::rust_owned_selectors(repository)?;
        if rust_owned.is_empty() {
            return Ok(RuleOutput::default());
        }
        let residual = residual_bash_paths(repository)?;
        let rust_domains: BTreeSet<&str> = rust_owned
            .iter()
            .filter_map(|selector| selector.split_whitespace().next())
            .collect();
        let mut findings = Vec::new();
        for path in developer_tooling_paths(repository, &residual) {
            let source = repository.read_utf8(path)?;
            for selector in command_registry::python_cli_selectors(&source) {
                let matched = if let Some((domain, "*")) = selector.split_once(' ') {
                    rust_domains.contains(domain)
                } else {
                    rust_owned.contains(&selector)
                };
                if !matched {
                    continue;
                }
                let line = first_selector_line(&source, &selector).unwrap_or(1);
                findings.push(Finding::new(
                    path.as_str(),
                    line,
                    format!(
                        "developer tooling invokes python/cli.py {selector}; command registry marks it Rust-owned"
                    ),
                ));
            }
        }
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

impl Rule for DeveloperToolingCrateProcessRule {
    fn name(&self) -> &'static str {
        PROCESS_NAME
    }

    fn description(&self) -> &'static str {
        PROCESS_DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let residual = residual_bash_paths(repository)?;
        let mut findings = Vec::new();
        for path in developer_tooling_paths(repository, &residual) {
            let path_text = path.as_str();
            let source = repository.read_utf8(path)?;
            for hit in crate_process_hits(repository, path, &source)? {
                if documented_process_exception(path_text, &hit.program, &residual) {
                    continue;
                }
                findings.push(Finding::new(
                    path_text,
                    hit.line,
                    format!(
                        "developer tooling spawns {}; a Rust crate already provides this capability",
                        hit.program
                    ),
                ));
            }
        }
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

impl Rule for DeveloperTooling7685ClosureRule {
    fn name(&self) -> &'static str {
        INVENTORY_CLOSURE_NAME
    }

    fn description(&self) -> &'static str {
        INVENTORY_CLOSURE_DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let findings = git_ownership::unresolved_later_domain_paths(repository, 7685)?
            .into_iter()
            .map(|path| {
                Finding::new(
                    git_ownership::INVENTORY_PATH,
                    1,
                    format!("Git-operation inventory still has unresolved later-domain #7685 row: {path}"),
                )
            })
            .collect();
        Ok(RuleOutput::from_findings(findings))
    }
}

impl Rule for RetiredDispositionModuleRule {
    fn name(&self) -> &'static str {
        RETIRED_NAME
    }

    fn description(&self) -> &'static str {
        RETIRED_DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let registered = command_registry::registered_python_lint_verbs(repository)?;
        let rows = read_retire_rows(repository)?;
        let mut findings = Vec::new();
        for row in rows {
            if registered.contains(&row.verb) {
                continue;
            }
            let mut modules = BTreeSet::new();
            modules.insert(lint_module_path(&row.verb));
            for surface in &row.surfaces {
                if looks_like_file(surface) {
                    modules.insert(surface.clone());
                }
            }
            for module in modules {
                if repository.root().join(&module).exists() {
                    findings.push(Finding::new(
                        DISPOSITION_PATH,
                        row.line,
                        format!(
                            "retired disposition module still exists for unregistered lint verb {}: {module}",
                            row.verb
                        ),
                    ));
                }
            }
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

#[derive(Debug)]
struct ProcessHit {
    line: u32,
    program: String,
}

#[derive(Debug)]
struct RetireRow {
    line: u32,
    verb: String,
    surfaces: Vec<String>,
}

fn developer_tooling_paths<'repository>(
    repository: &'repository Repository,
    residual: &BTreeSet<String>,
) -> Vec<&'repository RepoPath> {
    repository
        .paths()
        .iter()
        .filter(|path| {
            let path = path.as_str();
            is_developer_tooling_surface(path) || is_manifest_runtime_surface(path, residual)
        })
        .collect()
}

fn is_developer_tooling_surface(path: &str) -> bool {
    if path == MAKEFILE_PATH || path == PRE_COMMIT_PATH {
        return true;
    }
    if path.starts_with(".github/workflows/") {
        return matches!(extension(path), Some("yml" | "yaml"));
    }
    if path.starts_with(".github/actions/") {
        return matches!(
            path.rsplit('/').next(),
            Some("action.yml" | "action.yaml")
        );
    }
    if path.starts_with("scripts/") {
        return is_non_test_runtime_script(path);
    }
    if path.starts_with(".claude/skills/") {
        return !OTHER_DOMAIN_SKILL_PREFIXES
            .iter()
            .any(|prefix| path.starts_with(prefix))
            && matches!(extension(path), Some("md" | "sh" | "py"));
    }
    false
}

/// Include retained skill runtime scripts only when the canonical residual-Bash
/// manifest names them. Skills outside that manifest have separate owners.
fn is_manifest_runtime_surface(path: &str, residual: &BTreeSet<String>) -> bool {
    path.starts_with("skills/") && residual.contains(path) && is_non_test_runtime_script(path)
}

fn is_non_test_runtime_script(path: &str) -> bool {
    let name = path.rsplit('/').next().unwrap_or(path);
    !name.starts_with("test-")
        && !name.starts_with("test_")
        && !path.contains("/fixtures/")
        && matches!(extension(path), Some("sh" | "py"))
}

fn extension(path: &str) -> Option<&str> {
    Path::new(path).extension()?.to_str()
}

fn residual_bash_paths(repository: &Repository) -> Result<BTreeSet<String>, LintError> {
    let path = RepoPath::from_trusted(RESIDUAL_BASH_PATH);
    if repository.paths().binary_search(&path).is_err() {
        return Ok(BTreeSet::new());
    }
    let source = repository.read_utf8(&path)?;
    Ok(source
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty() && !line.starts_with('#'))
        .map(str::to_owned)
        .collect())
}

fn crate_process_hits(
    repository: &Repository,
    path: &RepoPath,
    source: &str,
) -> Result<Vec<ProcessHit>, LintError> {
    let path_text = path.as_str();
    match extension(path_text) {
        Some("sh") => shell_process_hits(path_text, syntax::shell_commands(source, 0)?),
        Some("md") => shell_process_hits(path_text, syntax::markdown_shell_commands(source)?),
        Some("py") => python_process_hits(repository, path, source),
        Some("yml" | "yaml") => yaml_process_hits(path_text, source),
        _ if path_text == MAKEFILE_PATH => makefile_process_hits(path_text, source),
        _ => Ok(Vec::new()),
    }
}

fn shell_process_hits(
    path: &str,
    commands: Vec<syntax::ShellCommand>,
) -> Result<Vec<ProcessHit>, LintError> {
    commands
        .into_iter()
        .filter_map(|command| {
            prohibited_program(command.words()).map(|program| (command.line(), program))
        })
        .map(|(line, program)| {
            Ok(ProcessHit {
                line: line_u32(path, line)?,
                program,
            })
        })
        .collect()
}

fn python_process_hits(
    repository: &Repository,
    path: &RepoPath,
    source: &str,
) -> Result<Vec<ProcessHit>, LintError> {
    let syntax = repository.python_syntax(path)?;
    let mut hits = Vec::new();
    for expected in CRATE_OWNED_PROGRAMS {
        for line in python_subprocess_call_lines(source, &syntax, |words| {
            prohibited_program(words).as_deref() == Some(expected)
        }) {
            hits.push(ProcessHit {
                line: line_u32(path.as_str(), line)?,
                program: expected.to_owned(),
            });
        }
    }
    Ok(hits)
}

fn makefile_process_hits(path: &str, source: &str) -> Result<Vec<ProcessHit>, LintError> {
    let mut hits = Vec::new();
    for (index, raw_line) in source.lines().enumerate() {
        let Some(recipe) = raw_line.strip_prefix('\t') else {
            continue;
        };
        let recipe = recipe.trim_start_matches(['@', '-', '+']);
        hits.extend(shell_process_hits(path, syntax::shell_commands(recipe, index)?)?);
    }
    Ok(hits)
}

fn yaml_process_hits(path: &str, source: &str) -> Result<Vec<ProcessHit>, LintError> {
    let mut hits = Vec::new();
    for (line, command) in yaml_shell_blocks(source) {
        hits.extend(shell_process_hits(
            path,
            syntax::shell_commands(&command, line.saturating_sub(1))?,
        )?);
    }
    Ok(hits)
}

/// Return static shell-bearing YAML fields while retaining their source lines.
///
/// GitHub workflows and pre-commit configurations use simple `run`, `entry`,
/// and `entrypoint` scalar or block values. Their shell content is always
/// delegated to the maintained Bash parser; this small wrapper only selects
/// the YAML field and preserves indentation-bounded literal blocks.
fn yaml_shell_blocks(source: &str) -> Vec<(usize, String)> {
    let lines: Vec<&str> = source.lines().collect();
    let mut blocks = Vec::new();
    let mut index = 0;
    while index < lines.len() {
        let raw = lines[index];
        let Some((indent, payload)) = yaml_shell_payload(raw) else {
            index += 1;
            continue;
        };
        if matches!(payload, "|" | "|-" | "|+" | ">" | ">-" | ">+") {
            let mut body = String::new();
            let mut first_line = None;
            index += 1;
            while index < lines.len() {
                let candidate = lines[index];
                if !candidate.trim().is_empty() && leading_spaces(candidate) <= indent {
                    break;
                }
                if !candidate.trim().is_empty() {
                    first_line.get_or_insert(index + 1);
                    body.push_str(candidate.trim_start());
                }
                body.push('\n');
                index += 1;
            }
            if let Some(line) = first_line {
                blocks.push((line, body));
            }
            continue;
        }
        if !payload.is_empty() {
            blocks.push((index + 1, unquote_yaml_scalar(payload).to_owned()));
        }
        index += 1;
    }
    blocks
}

fn yaml_shell_payload(line: &str) -> Option<(usize, &str)> {
    let indent = leading_spaces(line);
    let mut trimmed = line[indent..].trim_start();
    if let Some(rest) = trimmed.strip_prefix("- ") {
        trimmed = rest;
    }
    for key in ["run", "entry", "entrypoint"] {
        let prefix = format!("{key}:");
        if let Some(payload) = trimmed.strip_prefix(&prefix) {
            return Some((indent, payload.trim()));
        }
    }
    None
}

fn leading_spaces(line: &str) -> usize {
    line.len() - line.trim_start_matches(' ').len()
}

fn unquote_yaml_scalar(value: &str) -> &str {
    if value.len() >= 2
        && ((value.starts_with('"') && value.ends_with('"'))
            || (value.starts_with('\'') && value.ends_with('\'')))
    {
        &value[1..value.len() - 1]
    } else {
        value
    }
}

fn prohibited_program(words: &[String]) -> Option<String> {
    let index = executable_index(words)?;
    let program = words.get(index)?;
    let base = program
        .rsplit('/')
        .next()
        .unwrap_or(program)
        .trim_end_matches(".exe")
        .to_owned();
    if EXTERNAL_PRODUCTS.contains(&base.as_str()) {
        return None;
    }
    CRATE_OWNED_PROGRAMS
        .contains(&base.as_str())
        .then_some(base)
}

fn documented_process_exception(path: &str, program: &str, residual: &BTreeSet<String>) -> bool {
    let manifest_backed = residual.contains(path);
    matches!(
        (path, program),
        (
            RELEASE_WORKFLOW_PATH
                | GITHUB_AUTH_CONFIG_PATH
                | CLEAN_INSTALL_BOOTSTRAP_PATH
                | FAILURE_REPORT_PATH
                | COMBINE_ISSUES_SEARCH_PATH,
            "gh"
        ) | (
            SUBMODULE_GUARD_PATH
                | STALE_PLUGIN_PATH
                | SESSIONSTART_HEALTH_PATH
                | STAGED_GUIDELINES_PATH,
            "git"
        )
    ) && (matches!(path, RELEASE_WORKFLOW_PATH | GITHUB_AUTH_CONFIG_PATH) || manifest_backed)
}

fn first_selector_line(source: &str, selector: &str) -> Option<u32> {
    let mut parts = selector.split_whitespace();
    let domain = parts.next()?;
    let verb = parts.next()?;
    for (index, line) in source.lines().enumerate() {
        if line.contains("python/cli.py") && line.contains(domain) && line.contains(verb) {
            return u32::try_from(index + 1).ok();
        }
    }
    None
}

fn read_retire_rows(repository: &Repository) -> Result<Vec<RetireRow>, LintError> {
    let path = RepoPath::from_trusted(DISPOSITION_PATH);
    if repository.paths().binary_search(&path).is_err() {
        return Ok(Vec::new());
    }
    let source = repository.read_utf8(&path)?;
    let mut rows = Vec::new();
    for (index, raw_line) in source.split('\n').enumerate() {
        let line = line_u32(DISPOSITION_PATH, index + 1)?;
        if raw_line.is_empty() || raw_line.starts_with('#') {
            continue;
        }
        let fields: Vec<&str> = raw_line.split('\t').collect();
        if fields.len() < 3 || fields[1] != "retire" {
            continue;
        }
        let verb = fields[0].to_owned();
        if !is_verb_token(&verb) {
            return Err(LintError::new(format!(
                "{DISPOSITION_PATH}:{line}: invalid lint verb token {verb:?}"
            )));
        }
        let surfaces = fields[2]
            .split(',')
            .map(str::trim)
            .filter(|part| !part.is_empty())
            .map(str::to_owned)
            .collect();
        rows.push(RetireRow {
            line,
            verb,
            surfaces,
        });
    }
    Ok(rows)
}

fn lint_module_path(verb: &str) -> String {
    format!("python/larch/lint/lint_{}.py", verb.replace('-', "_"))
}

fn looks_like_file(surface: &str) -> bool {
    Path::new(surface).extension().is_some()
}

fn line_u32(path: &str, line: usize) -> Result<u32, LintError> {
    u32::try_from(line).map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))
}

#[cfg(test)]
mod tests {
    use super::{
        executable_index, is_developer_tooling_surface, is_manifest_runtime_surface,
        lint_module_path, looks_like_file, prohibited_program, yaml_shell_blocks,
    };
    use std::collections::BTreeSet;

    #[test]
    fn scopes_developer_tooling_surfaces() {
        assert!(is_developer_tooling_surface("Makefile"));
        assert!(is_developer_tooling_surface(".pre-commit-config.yaml"));
        assert!(is_developer_tooling_surface(".github/workflows/ci.yaml"));
        assert!(is_developer_tooling_surface(
            ".github/actions/github-auth-config/action.yaml"
        ));
        assert!(is_developer_tooling_surface("scripts/example.sh"));
        assert!(is_developer_tooling_surface(".claude/skills/larch-size/SKILL.md"));
        assert!(!is_developer_tooling_surface("scripts/test-example.sh"));
        assert!(!is_developer_tooling_surface(".claude/skills/release/SKILL.md"));
        assert!(!is_developer_tooling_surface("skills/design/SKILL.md"));
        assert!(!is_developer_tooling_surface("python/larch/cli.py"));

        let residual = BTreeSet::from(["skills/design/scripts/design-clarify.sh".to_owned()]);
        assert!(is_manifest_runtime_surface(
            "skills/design/scripts/design-clarify.sh",
            &residual,
        ));
        assert!(!is_manifest_runtime_surface(
            "skills/design/scripts/unlisted.sh",
            &residual,
        ));
        assert!(!is_manifest_runtime_surface(
            "skills/design/scripts/test-design-clarify.sh",
            &residual,
        ));
    }

    #[test]
    fn rejects_crate_owned_programs_and_keeps_vendors() {
        assert_eq!(
            prohibited_program(&["gcloud".into(), "auth".into()]),
            Some("gcloud".into())
        );
        assert_eq!(
            prohibited_program(&["env".into(), "FOO=1".into(), "gh".into(), "api".into()]),
            Some("gh".into())
        );
        assert_eq!(prohibited_program(&["claude".into(), "-p".into()]), None);
        assert_eq!(prohibited_program(&["codex".into(), "exec".into()]), None);
        assert_eq!(prohibited_program(&["cursor".into(), "agent".into()]), None);
        assert_eq!(
            prohibited_program(&["git".into(), "status".into()]),
            Some("git".into())
        );
    }

    #[test]
    fn finds_scalar_and_block_yaml_commands() {
        assert_eq!(
            yaml_shell_blocks("entry: gh api /user\nrun: |\n  git status\n"),
            vec![
                (1, "gh api /user".to_owned()),
                (3, "git status\n".to_owned()),
            ]
        );
    }

    #[test]
    fn derives_retire_module_paths() {
        assert_eq!(
            lint_module_path("self-disarmable-gate"),
            "python/larch/lint/lint_self_disarmable_gate.py"
        );
        assert!(looks_like_file("python/larch/lint/lint_flat_tests.py"));
        assert!(!looks_like_file("python/larch/lint"));
        assert_eq!(
            executable_index(&["sudo".into(), "gh".into()]),
            Some(1)
        );
    }
}
