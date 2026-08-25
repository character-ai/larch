//! Enforce the closed vendor-agent command and Python-package boundary for #7678.

use std::collections::BTreeSet;

use toml::Value;

use crate::{
    Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput, command_registry,
};

use super::python_boundary::{
    RegistryCommand, check_python_registry, check_retired_entrypoints,
};

const NAME: &str = "agent-python-free";
const DESCRIPTION: &str =
    "Enforce final Rust vendor-agent ownership and retirement of Python agent surfaces";
const COMMAND_REGISTRY_PATH: &str = "crates/larch-lint/data/command-registry.toml";
const AGENT_AUTHORITY_PATH: &str = "crates/larch-cli/src/agent_commands.rs";
const PLANNING_ISSUE: i64 = 7678;

#[derive(Clone, Copy)]
struct ExpectedCommand {
    domain: &'static str,
    verb: &'static str,
    migration_issue: i64,
}

impl ExpectedCommand {
    const fn new(domain: &'static str, verb: &'static str, migration_issue: i64) -> Self {
        Self {
            domain,
            verb,
            migration_issue,
        }
    }

    fn selector(self) -> String {
        format!("{} {}", self.domain, self.verb)
    }
}

const EXPECTED_COMMANDS: &[ExpectedCommand] = &[
    ExpectedCommand::new("agent", "check-reviewers", 8108),
    ExpectedCommand::new("agent", "classify-diff", 8118),
    ExpectedCommand::new("agent", "collect-results", 8119),
    ExpectedCommand::new("agent", "compose-collector-failure-log", 8118),
    ExpectedCommand::new("agent", "cursor-auth-preflight", 8106),
    ExpectedCommand::new("agent", "cursor-wrap-prompt", 8107),
    ExpectedCommand::new("agent", "degraded-tools-gate", 8108),
    ExpectedCommand::new("agent", "dispatch-voters", 8117),
    ExpectedCommand::new("agent", "dispatch-waterfall", 8116),
    ExpectedCommand::new("agent", "external-tool-registry", 8107),
    ExpectedCommand::new("agent", "gather-branch-context", 8118),
    ExpectedCommand::new("agent", "launch-claude-ci", 8111),
    ExpectedCommand::new("agent", "launch-claude-drafter", 8113),
    ExpectedCommand::new("agent", "launch-claude-lint-fix", 8112),
    ExpectedCommand::new("agent", "launch-claude-review", 8110),
    ExpectedCommand::new("agent", "launch-claude-review-fix", 8112),
    ExpectedCommand::new("agent", "launch-claude-subprocess", 8110),
    ExpectedCommand::new("agent", "launch-codex-ci", 8111),
    ExpectedCommand::new("agent", "launch-codex-drafter", 8113),
    ExpectedCommand::new("agent", "launch-codex-exec", 8113),
    ExpectedCommand::new("agent", "launch-codex-implement", 8112),
    ExpectedCommand::new("agent", "launch-cursor-ci", 8111),
    ExpectedCommand::new("agent", "launch-cursor-implement", 8112),
    ExpectedCommand::new("agent", "launch-review", 8115),
    ExpectedCommand::new("agent", "model-args", 8107),
    ExpectedCommand::new("agent", "parse-codex-usage", 8105),
    ExpectedCommand::new("agent", "read-claude-model", 8107),
    ExpectedCommand::new("agent", "resolve-model-pins", 8108),
    ExpectedCommand::new("agent", "run-external-agent", 8109),
    ExpectedCommand::new("agent", "run-negotiation-round", 8113),
    ExpectedCommand::new("agent", "wait-reviewers", 8118),
    ExpectedCommand::new("external-defaults", "docs", 8107),
    ExpectedCommand::new("external-defaults", "resolve-vendor", 8107),
    ExpectedCommand::new("external-defaults", "role", 8107),
    ExpectedCommand::new("slack", "issue-announce", 8107),
];
const RETIRED_ROOTS: &[&str] = &[
    "python/larch/agents/",
    "python/tests/agents/",
    "plugin/python/larch/agents/",
];
const RETIRED_FILES: &[&str] = &[
    "python/larch/core/external_defaults.py",
    "python/tests/core/test_external_role_defaults.py",
    "python/tests/test_conftest_session_isolation.py",
    "plugin/python/larch/core/external_defaults.py",
];
const RETIRED_REFERENCES: &[&str] = &[
    "larch.agents",
    "python/larch/agents",
    "python/tests/agents",
    "larch.core.external_defaults",
    "python/larch/core/external_defaults",
    "test_external_role_defaults.py",
    "test_conftest_session_isolation.py",
    "python/cli.py agent ",
    "python/cli.py external-defaults ",
    "python/cli.py slack issue-announce",
];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/agent-python-free.toml",
);

#[derive(Debug)]
pub struct AgentPythonFreeRule;

pub static RULE: AgentPythonFreeRule = AgentPythonFreeRule;

crate::register_rule!(METADATA, RULE);

impl Rule for AgentPythonFreeRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let authority_present = repository
            .paths()
            .binary_search(&RepoPath::from_trusted(AGENT_AUTHORITY_PATH))
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

        let source = repository.read_utf8(&registry_path)?;
        let registry: Value = toml::from_str(&source).map_err(|error| {
            LintError::new(format!("{COMMAND_REGISTRY_PATH}: invalid TOML: {error}"))
        })?;
        let commands = registry
            .get("commands")
            .and_then(Value::as_array)
            .ok_or_else(|| LintError::new(format!("{COMMAND_REGISTRY_PATH}: missing commands")))?;
        let scoped = commands
            .iter()
            .filter_map(RegistryCommand::parse)
            .filter(|command| command.integer("planning_issue") == Some(PLANNING_ISSUE))
            .collect::<Vec<_>>();
        if !authority_present && scoped.is_empty() {
            return Ok(RuleOutput::default());
        }

        let mut findings = command_registry::planning_issue_closure_findings(
            repository,
            PLANNING_ISSUE as u64,
        )?;
        check_registry_rows(&scoped, &mut findings);
        check_python_registry(
            repository,
            &|domain, verb| {
                scoped
                    .iter()
                    .any(|command| command.domain == domain && command.verb == verb)
            },
            &|domain, verb| {
                format!("retired vendor-agent command remains registered in Python: {domain} {verb}")
            },
            &mut findings,
        )?;
        let targets = scoped
            .iter()
            .filter_map(|command| {
                Some((
                    command.text("python_module")?.to_owned(),
                    command.text("python_function")?.to_owned(),
                ))
            })
            .collect::<Vec<_>>();
        check_retired_entrypoints(
            repository,
            &targets,
            &|module, function| {
                format!("retired vendor-agent Python entry point returned: {module}.{function}")
            },
            &mut findings,
        )?;
        check_retired_surfaces(repository, &mut findings)?;
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

fn check_registry_rows(scoped: &[RegistryCommand<'_>], findings: &mut Vec<Finding>) {
    if scoped.len() != EXPECTED_COMMANDS.len() {
        findings.push(registry_finding(format!(
            "#7678 command ledger count drift: expected {}, found {}",
            EXPECTED_COMMANDS.len(),
            scoped.len()
        )));
    }
    let mut seen = BTreeSet::new();
    for command in scoped {
        if !command.has_final_cutover() {
            findings.push(registry_finding(format!(
                "non-final #7678 command row: {}",
                command.selector
            )));
        }
        let Some(expected) = EXPECTED_COMMANDS
            .iter()
            .find(|expected| expected.domain == command.domain && expected.verb == command.verb)
        else {
            findings.push(registry_finding(format!(
                "unexpected #7678 command row: {}",
                command.selector
            )));
            continue;
        };
        if !seen.insert(command.selector.clone()) {
            findings.push(registry_finding(format!(
                "duplicate #7678 command row: {}",
                command.selector
            )));
        }
        if command.integer("migration_issue") != Some(expected.migration_issue) {
            findings.push(registry_finding(format!(
                "#7678 command has the wrong migration leaf: {}",
                command.selector
            )));
        }
    }
    for expected in EXPECTED_COMMANDS {
        let selector = expected.selector();
        if !seen.contains(&selector) {
            findings.push(registry_finding(format!(
                "missing #7678 command row: {selector}"
            )));
        }
    }
}

fn check_retired_surfaces(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    for path in repository.paths() {
        let relative = path.as_str();
        if RETIRED_ROOTS.iter().any(|root| relative.starts_with(root))
            || RETIRED_FILES.contains(&relative)
        {
            findings.push(Finding::new(
                relative,
                1,
                "retired Python vendor-agent surface returned",
            ));
            continue;
        }
        if !is_live_runtime_or_tooling_path(relative) {
            continue;
        }
        let source = repository.read_utf8(path)?;
        for (index, line) in source.lines().enumerate() {
            if RETIRED_REFERENCES.iter().any(|marker| line.contains(marker)) {
                findings.push(Finding::new(
                    relative,
                    u32::try_from(index + 1).unwrap_or(u32::MAX),
                    "live runtime or tooling still references the retired Python vendor-agent surface",
                ));
            }
        }
    }
    Ok(())
}

fn is_live_runtime_or_tooling_path(path: &str) -> bool {
    path == "Makefile"
        || path == "agent-lint.toml"
        || path == ".pre-commit-config.yaml"
        || [
            "agents/",
            "hooks/",
            "python/larch/",
            "scripts/",
            "skills/",
            ".claude/skills/",
            ".claude-plugin/",
            "plugin/agents/",
            "plugin/hooks/",
            "plugin/python/larch/",
            "plugin/scripts/",
            "plugin/skills/",
        ]
        .iter()
        .any(|prefix| path.starts_with(prefix))
}

fn registry_finding(message: String) -> Finding {
    Finding::new(COMMAND_REGISTRY_PATH, 1, message)
}
