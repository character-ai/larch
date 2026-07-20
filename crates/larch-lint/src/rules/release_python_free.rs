//! Enforce the final Python-free release and upgrade command boundary.

use std::{collections::BTreeSet, path::Path, sync::LazyLock};

use regex::Regex;
use toml::Value;

use crate::{
    Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput,
    syntax::{ShellCommand, markdown_shell_commands, shell_commands},
};

use super::larch_runtime_entrypoint::is_production_surface;
use super::production_cargo_run::executable_index;

const NAME: &str = "release-python-free";
const DESCRIPTION: &str =
    "Enforce Rust-only release and upgrade ownership, callers, and implementations";
const COMMAND_REGISTRY_PATH: &str = "crates/larch-lint/data/command-registry.toml";
const PYTHON_REGISTRY_PATH: &str = "python/larch/cli.py";
const RELEASE_AUTHORITY_PATH: &str = "crates/larch-cli/src/release_assets.rs";
const BOOTSTRAP_PATH: &str = "scripts/larch.sh";
const RELEASE_WORKFLOW_PATH: &str = ".github/workflows/rust-release-assets.yaml";

struct ExpectedCommand {
    domain: &'static str,
    verb: &'static str,
    issue: i64,
    clean_install_test: Option<&'static str>,
}

const EXPECTED_COMMANDS: [ExpectedCommand; 19] = [
    ExpectedCommand::new("plugin", "read-version", 7749, Some("clean-install-plugin-read-version")),
    ExpectedCommand::new("release", "asset-candidate", 7747, Some("clean-install-release-asset-candidate")),
    ExpectedCommand::new("release", "asset-run", 7751, None),
    ExpectedCommand::new("release", "classify-bump", 7749, Some("clean-install-release-classify-bump")),
    ExpectedCommand::new("release", "collect-assets", 7747, Some("clean-install-release-collect-assets")),
    ExpectedCommand::new("release", "ensure-policy", 7751, None),
    ExpectedCommand::new("release", "finish", 7752, None),
    ExpectedCommand::new("release", "package-asset", 7747, Some("clean-install-release-package-asset")),
    ExpectedCommand::new("release", "plugin-runtime", 7748, Some("clean-install-release-plugin-runtime")),
    ExpectedCommand::new("release", "prepare", 7749, Some("clean-install-release-prepare")),
    ExpectedCommand::new("release", "promote", 7752, None),
    ExpectedCommand::new("release", "promote-latest", 7752, None),
    ExpectedCommand::new("release", "set-version", 7750, Some("clean-install-release-set-version")),
    ExpectedCommand::new("release", "stage", 7751, None),
    ExpectedCommand::new("release", "validate-assets", 7747, Some("clean-install-release-validate-assets")),
    ExpectedCommand::new("release", "validate-draft", 7751, None),
    ExpectedCommand::new("upgrade-larch", "release-step7-root", 7753, Some("clean-install-upgrade-larch-release-step7-root")),
    ExpectedCommand::new("upgrade-larch", "run", 7753, Some("clean-install-upgrade-larch-run")),
    ExpectedCommand::new("upgrade-larch", "sparse-dirs", 7753, Some("clean-install-upgrade-larch-sparse-dirs")),
];

impl ExpectedCommand {
    const fn new(
        domain: &'static str,
        verb: &'static str,
        issue: i64,
        clean_install_test: Option<&'static str>,
    ) -> Self {
        Self {
            domain,
            verb,
            issue,
            clean_install_test,
        }
    }

    fn selector(&self) -> String {
        format!("{} {}", self.domain, self.verb)
    }
}

static DIRECT_BINARY: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?:^|[^A-Za-z0-9_.-])bin/larch(?:$|[^A-Za-z0-9_.-])")
        .expect("direct larch binary expression is valid")
});
static SEGMENTED_BINARY: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"[\"']bin[\"']\s*(?:/|,)\s*[\"']larch[\"']"#)
        .expect("segmented larch binary expression is valid")
});
static RUST_GH_PROCESS: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"Command::new\s*\(\s*[\"']gh[\"']"#)
        .expect("Rust gh process expression is valid")
});
static PYTHON_GH_PROCESS: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r#"(?:subprocess\.)?(?:run|Popen|call|check_call|check_output)\s*\(\s*(?:args\s*=\s*)?[\[(]\s*[\"']gh[\"']"#,
    )
    .expect("Python gh process expression is valid")
});
static PYTHON_REGISTRATION: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r#"\(\s*[\"'](?P<domain>release|upgrade-larch|plugin)[\"']\s*,\s*[\"'](?P<verb>[a-z0-9-]+)[\"']\s*\)\s*:"#,
    )
    .expect("Python release registration expression is valid")
});

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/release-python-free.toml",
);

#[derive(Debug)]
pub struct ReleasePythonFreeRule;

pub static RULE: ReleasePythonFreeRule = ReleasePythonFreeRule;

crate::register_rule!(METADATA, RULE);

impl Rule for ReleasePythonFreeRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let authority_present = repository
            .paths()
            .binary_search(&RepoPath::from_trusted(RELEASE_AUTHORITY_PATH))
            .is_ok();
        let registry_path = RepoPath::from_trusted(COMMAND_REGISTRY_PATH);
        if repository.paths().binary_search(&registry_path).is_err() {
            if authority_present {
                return Err(LintError::new(format!(
                    "{COMMAND_REGISTRY_PATH}: required file is missing"
                )));
            }
            return Ok(RuleOutput::default());
        }
        let registry_source = repository.read_utf8(&registry_path)?;
        let registry: Value = toml::from_str(&registry_source).map_err(|error| {
            LintError::new(format!("{COMMAND_REGISTRY_PATH}: invalid TOML: {error}"))
        })?;
        let commands = registry
            .get("commands")
            .and_then(Value::as_array)
            .ok_or_else(|| LintError::new(format!("{COMMAND_REGISTRY_PATH}: missing commands")))?;
        if !authority_present && !commands.iter().any(is_in_scope_row) {
            return Ok(RuleOutput::default());
        }

        let mut findings = Vec::new();
        let python_targets = check_registry_rows(commands, &mut findings);
        check_python_registry(repository, &mut findings)?;
        check_python_implementations(repository, &python_targets, &mut findings)?;
        check_runtime_callers(repository, &mut findings)?;
        check_release_gh_fallbacks(repository, &mut findings)?;
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

fn is_in_scope_row(value: &Value) -> bool {
    value.as_table().is_some_and(|table| {
        let domain = table.get("domain").and_then(Value::as_str).unwrap_or_default();
        let verb = table.get("verb").and_then(Value::as_str).unwrap_or_default();
        is_in_scope(domain, verb)
    })
}

fn is_in_scope(domain: &str, verb: &str) -> bool {
    domain == "release" || domain == "upgrade-larch" || (domain == "plugin" && verb == "read-version")
}

fn expected_command(domain: &str, verb: &str) -> Option<&'static ExpectedCommand> {
    EXPECTED_COMMANDS
        .iter()
        .find(|command| command.domain == domain && command.verb == verb)
}

fn check_registry_rows(
    commands: &[Value],
    findings: &mut Vec<Finding>,
) -> Vec<(String, String)> {
    let mut found = BTreeSet::new();
    let mut python_targets = Vec::new();
    for value in commands {
        let Some(table) = value.as_table() else {
            continue;
        };
        let domain = table.get("domain").and_then(Value::as_str).unwrap_or_default();
        let verb = table.get("verb").and_then(Value::as_str).unwrap_or_default();
        if !is_in_scope(domain, verb) {
            continue;
        }
        let selector = format!("{domain} {verb}");
        let Some(expected) = expected_command(domain, verb) else {
            findings.push(registry_finding(format!(
                "unapproved release-owned command row: {selector}"
            )));
            continue;
        };
        found.insert(selector.clone());
        if !row_has_final_state(table) {
            findings.push(registry_finding(format!(
                "non-final release Python-free command row: {selector}"
            )));
        }
        if table.get("migration_issue").and_then(Value::as_integer) != Some(expected.issue) {
            findings.push(registry_finding(format!(
                "release command migration issue drift: {selector}; expected #{}",
                expected.issue
            )));
        }
        let (python_module, python_function) = expected_python_target(domain, verb)
            .expect("every final release command has retired Python metadata");
        if table.get("python_module").and_then(Value::as_str) != Some(python_module)
            || table.get("python_function").and_then(Value::as_str) != Some(python_function)
        {
            findings.push(registry_finding(format!(
                "release retired Python target drift: {selector}; expected {python_module}.{python_function}"
            )));
        }
        if let Some(fixture) = expected.clean_install_test
            && table.get("clean_install_test").and_then(Value::as_str) != Some(fixture)
        {
            findings.push(registry_finding(format!(
                "release clean-install coverage drift: {selector}; expected {fixture}"
            )));
        }
        python_targets.push((python_module.to_owned(), python_function.to_owned()));
    }
    for expected in &EXPECTED_COMMANDS {
        let selector = expected.selector();
        if !found.contains(&selector) {
            findings.push(registry_finding(format!(
                "missing final release-owned command row: {selector}"
            )));
        }
    }
    python_targets
}

fn expected_python_target(domain: &str, verb: &str) -> Option<(&'static str, &'static str)> {
    match (domain, verb) {
        ("plugin", "read-version") => Some(("larch.release.version_bump", "read_plugin_version_main")),
        ("release", "asset-candidate") => Some(("larch.release.assets", "candidate_main")),
        ("release", "asset-run") => Some(("larch.release.release_finish", "asset_run_main")),
        ("release", "classify-bump") => Some(("larch.release.version_bump", "classify_bump_main")),
        ("release", "collect-assets") => Some(("larch.release.assets", "collect_main")),
        ("release", "ensure-policy") => Some(("larch.release.release_finish", "ensure_policy_main")),
        ("release", "finish") => Some(("larch.release.release_finish", "main")),
        ("release", "package-asset") => Some(("larch.release.assets", "package_main")),
        ("release", "plugin-runtime") => Some(("larch.release.plugin_runtime", "main")),
        ("release", "prepare") => Some(("larch.release.release_prepare", "main")),
        ("release", "promote") => Some(("larch.release.promote_release", "promote_main")),
        ("release", "promote-latest") => Some(("larch.release.promote_release", "promote_latest_main")),
        ("release", "set-version") => Some(("larch.release.version_bump", "set_version_main")),
        ("release", "stage") => Some(("larch.release.release_finish", "stage_main")),
        ("release", "validate-assets") => Some(("larch.release.assets", "validate_main")),
        ("release", "validate-draft") => Some(("larch.release.release_finish", "validate_draft_main")),
        ("upgrade-larch", "release-step7-root") => Some(("larch.core.upgrade_larch", "release_step7_root_main")),
        ("upgrade-larch", "run") => Some(("larch.core.upgrade_larch", "run_main")),
        ("upgrade-larch", "sparse-dirs") => Some(("larch.core.upgrade_larch", "sparse_dirs_main")),
        _ => None,
    }
}

fn check_python_registry(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    let path = RepoPath::from_trusted(PYTHON_REGISTRY_PATH);
    if repository.paths().binary_search(&path).is_err() {
        return Ok(());
    }
    let source = repository.read_utf8(&path)?;
    for captures in PYTHON_REGISTRATION.captures_iter(&source) {
        if is_in_scope(&captures["domain"], &captures["verb"]) {
            findings.push(Finding::new(
                PYTHON_REGISTRY_PATH,
                offset_line_number(&source, captures.get(0).expect("whole capture").start()),
                "release-owned command remains registered in Python",
            ));
        }
    }
    Ok(())
}

fn row_has_final_state(table: &toml::Table) -> bool {
    [
        ("owner", "rust"),
        ("implementation_parity", "complete"),
        ("consumer_cutover", "complete"),
        ("python_removal", "complete"),
    ]
    .into_iter()
    .all(|(field, expected)| table.get(field).and_then(Value::as_str) == Some(expected))
}

fn check_python_implementations(
    repository: &Repository,
    targets: &[(String, String)],
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    for (module, function) in targets {
        let module_path = format!("python/{}.py", module.replace('.', "/"));
        let path = RepoPath::from_trusted(&module_path);
        if repository.paths().binary_search(&path).is_err() {
            continue;
        }
        let source = repository.read_utf8(&path)?;
        let definition = Regex::new(&format!(
            r"(?m)^\s*(?:async\s+)?def\s+{}\s*\(",
            regex::escape(function)
        ))
        .expect("escaped Python function expression is valid");
        for matched in definition.find_iter(&source) {
            findings.push(Finding::new(
                &module_path,
                offset_line_number(&source, matched.start()),
                format!("superseded release Python implementation remains: {module}.{function}"),
            ));
        }
    }
    Ok(())
}

fn check_runtime_callers(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    for path in repository.paths() {
        let path_text = path.as_str();
        if !is_release_runtime_surface(path_text) {
            continue;
        }
        let source = repository.read_utf8(path)?;
        if path_text == BOOTSTRAP_PATH {
            for (index, line) in source.lines().enumerate() {
                if line.contains("python") && !line.trim_start().starts_with('#') {
                    findings.push(Finding::new(
                        path_text,
                        line_number(index),
                        "scripts/larch.sh contains a Python runtime fallback",
                    ));
                }
            }
            continue;
        }
        for (index, line) in source.lines().enumerate() {
            if DIRECT_BINARY.is_match(line) || SEGMENTED_BINARY.is_match(line) {
                findings.push(Finding::new(
                    path_text,
                    line_number(index),
                    "direct bin/larch release runtime entrypoint; use scripts/larch.sh",
                ));
            }
        }
        let commands = match Path::new(path_text).extension().and_then(|value| value.to_str()) {
            Some(extension) if extension.eq_ignore_ascii_case("md") => {
                markdown_shell_commands(&source)?
            }
            Some(extension) if extension.eq_ignore_ascii_case("sh") => shell_commands(&source, 0)?,
            _ => Vec::new(),
        };
        check_shell_commands(path_text, &commands, findings);
        if path_text == RELEASE_WORKFLOW_PATH {
            check_workflow_python_selectors(&source, findings);
        }
    }
    Ok(())
}

fn check_shell_commands(path: &str, commands: &[ShellCommand], findings: &mut Vec<Finding>) {
    for command in commands {
        let words = command.words();
        let Some((domain, verb)) = words.windows(2).find_map(|pair| {
            expected_command(&pair[0], &pair[1])
                .is_some()
                .then_some((pair[0].as_str(), pair[1].as_str()))
        }) else {
            continue;
        };
        let executable = executable_index(words)
            .and_then(|index| words.get(index))
            .map_or("", String::as_str);
        if !executable.ends_with("scripts/larch.sh") {
            findings.push(Finding::new(
                path,
                u32::try_from(command.line()).unwrap_or(u32::MAX),
                format!(
                    "release command caller bypasses scripts/larch.sh: {domain} {verb}"
                ),
            ));
        }
    }
}

fn check_workflow_python_selectors(source: &str, findings: &mut Vec<Finding>) {
    let normalized = source.replace("\\\r\n", " ").replace("\\\n", " ");
    for (index, line) in normalized.lines().enumerate() {
        if line.contains("python")
            && line.contains("cli.py")
            && EXPECTED_COMMANDS
                .iter()
                .any(|command| line.contains(&command.selector()))
        {
            findings.push(Finding::new(
                RELEASE_WORKFLOW_PATH,
                line_number(index),
                "release workflow contains a Python selector or fallback",
            ));
        }
    }
}

fn check_release_gh_fallbacks(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    for path in repository.paths() {
        let path_text = path.as_str();
        if !is_release_implementation(path_text) {
            continue;
        }
        let source = repository.read_utf8(path)?;
        for expression in [&*RUST_GH_PROCESS, &*PYTHON_GH_PROCESS] {
            for matched in expression.find_iter(&source) {
                findings.push(Finding::new(
                    path_text,
                    offset_line_number(&source, matched.start()),
                    "release implementation invokes gh directly; use the typed GitHub service",
                ));
            }
        }
    }
    Ok(())
}

fn is_release_runtime_surface(path: &str) -> bool {
    is_production_surface(path) || path == RELEASE_WORKFLOW_PATH
}

fn is_release_implementation(path: &str) -> bool {
    (path.starts_with("crates/larch-cli/src/release") && has_extension(path, "rs"))
        || (path.starts_with("crates/larch-cli/src/upgrade") && has_extension(path, "rs"))
        || (path.starts_with("crates/larch-adapters/src/upgrade") && has_extension(path, "rs"))
        || path == "crates/larch-adapters/src/github/release.rs"
        || (path.starts_with("python/larch/release/") && has_extension(path, "py"))
        || path == "python/larch/core/upgrade_larch.py"
}

fn has_extension(path: &str, expected: &str) -> bool {
    Path::new(path)
        .extension()
        .is_some_and(|extension| extension.eq_ignore_ascii_case(expected))
}

fn registry_finding(message: String) -> Finding {
    Finding::new(COMMAND_REGISTRY_PATH, 1, message)
}

fn line_number(index: usize) -> u32 {
    u32::try_from(index + 1).unwrap_or(u32::MAX)
}

fn offset_line_number(source: &str, offset: usize) -> u32 {
    u32::try_from(source[..offset].bytes().filter(|byte| *byte == b'\n').count() + 1)
        .unwrap_or(u32::MAX)
}
