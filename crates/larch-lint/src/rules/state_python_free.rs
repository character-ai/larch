//! Enforce the completed session and background-job ownership boundary.
//!
//! Umbrella #7677 closed the command rows that used to be implemented by the
//! Python state and background-job packages. The remaining Python helpers are
//! deliberately narrow libraries until #7681 ports their last callers.

use std::{collections::BTreeSet, path::Path};

use toml::{Value, map::Map};

use crate::{Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput};

use super::python_boundary::{check_python_registry, check_retired_entrypoints};

const NAME: &str = "state-python-free";
const DESCRIPTION: &str =
    "Enforce Rust-only completed session and background-job commands for umbrella #7677";
const COMMAND_REGISTRY_PATH: &str = "crates/larch-lint/data/command-registry.toml";
const SESSION_AUTHORITY_PATH: &str = "crates/larch-cli/src/session_closeout_commands.rs";
const STALL_AUTHORITY_PATH: &str = "crates/larch-cli/src/stall_recovery_commands.rs";
const UMBRELLA_ISSUE: i64 = 7677;
const EXPECTED_COMMAND_COUNT: usize = 58;
const MIGRATION_LEAVES: &[i64] = &[8056, 8057, 8058, 8059, 8060, 8061, 8062, 8063, 8064, 8065, 8066, 8067, 8068];
const RETIRED_MODULES: &[&str] = &[
    "python/larch/state/admission.py",
    "python/larch/state/dirty_tree.py",
    "python/larch/state/stall_recovery.py",
    "python/larch/state/_state_mgmt.py",
    "python/larch/state/_escalation.py",
    "python/larch/state/_report.py",
    "python/larch/state/_corpus.py",
    "python/larch/state/_detail_log.py",
    "python/larch/state/_classify.py",
    "python/larch/state/_normalize.py",
    "python/larch/state/closeout.py",
    "python/larch/core/cleanup_skill.py",
    "python/larch/core/kv_cli.py",
];

/// The exact Python helpers whose remaining consumers are owned by #7681.
const RETAINED_MODULES: &[&str] = &[
    "python/larch/state/__init__.py",
    "python/larch/state/_tokens.py",
    "python/larch/state/_validate.py",
    "python/larch/state/session_env.py",
    "python/larch/bgjob/__init__.py",
    "python/larch/bgjob/model.py",
    "python/larch/bgjob/registry.py",
    "python/larch/core/process_identity.py",
];

type RegistryTable = Map<String, Value>;

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/state-python-free.toml",
);

#[derive(Debug)]
pub struct StatePythonFreeRule;

pub static RULE: StatePythonFreeRule = StatePythonFreeRule;

crate::register_rule!(METADATA, RULE);

impl Rule for StatePythonFreeRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let authority_present = [SESSION_AUTHORITY_PATH, STALL_AUTHORITY_PATH].iter().any(|path| {
            repository
                .paths()
                .binary_search(&RepoPath::from_trusted(path))
                .is_ok()
        });
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
        let scoped: Vec<&RegistryTable> = commands
            .iter()
            .filter_map(Value::as_table)
            .filter(|table| table_integer(table, "planning_issue") == Some(UMBRELLA_ISSUE))
            .collect();
        if !authority_present && scoped.is_empty() {
            return Ok(RuleOutput::default());
        }

        let mut findings = Vec::new();
        let targets = check_registry_rows(&scoped, &mut findings);
        check_python_registry(
            repository,
            &|domain, verb| scoped.iter().any(|table| selector(table) == (domain, verb)),
            &|domain, verb| format!("completed #7677 command remains registered in Python: {domain} {verb}"),
            &mut findings,
        )?;
        check_retired_entrypoints(
            repository,
            &targets,
            &|module, function| {
                format!("superseded #7677 Python implementation remains: {module}.{function}")
            },
            &mut findings,
        )?;
        check_retired_surface(repository, &mut findings);
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

fn check_registry_rows(
    scoped: &[&RegistryTable],
    findings: &mut Vec<Finding>,
) -> Vec<(String, String)> {
    if scoped.len() != EXPECTED_COMMAND_COUNT {
        findings.push(registry_finding(format!(
            "#7677 command ledger count drift: expected {EXPECTED_COMMAND_COUNT}, found {}",
            scoped.len()
        )));
    }
    let mut selectors = BTreeSet::new();
    let mut targets = Vec::new();
    for table in scoped {
        let (domain, verb) = selector(table);
        let selector = format!("{domain} {verb}");
        if !selectors.insert(selector.clone()) {
            findings.push(registry_finding(format!("duplicate #7677 command row: {selector}")));
        }
        let complete = [
            ("owner", "rust"),
            ("implementation_parity", "complete"),
            ("consumer_cutover", "complete"),
            ("python_removal", "complete"),
        ]
        .into_iter()
        .all(|(key, expected)| table_text(table, key) == expected);
        if !complete {
            findings.push(registry_finding(format!(
                "non-final #7677 command row: {selector}"
            )));
        }
        let migration_issue = table_integer(table, "migration_issue");
        if !migration_issue.is_some_and(|issue| MIGRATION_LEAVES.contains(&issue)) {
            findings.push(registry_finding(format!(
                "#7677 command must name an executable migration leaf: {selector}"
            )));
        }
        let module = table_text(table, "python_module");
        let function = table_text(table, "python_function");
        if module.is_empty() || function.is_empty() {
            findings.push(registry_finding(format!(
                "#7677 command lost its retired Python target: {selector}"
            )));
        } else {
            targets.push((module.to_owned(), function.to_owned()));
        }
    }
    targets
}

fn check_retired_surface(repository: &Repository, findings: &mut Vec<Finding>) {
    for path in RETIRED_MODULES {
        if repository
            .paths()
            .binary_search(&RepoPath::from_trusted(path))
            .is_ok()
        {
            findings.push(Finding::new(
                *path,
                1,
                "superseded #7677 Python module returned",
            ));
        }
    }
    for path in repository.paths() {
        let relative = path.as_str();
        if relative.starts_with("python/tests/state/") || relative.starts_with("python/tests/bgjob/") {
            findings.push(Finding::new(
                relative,
                1,
                "retired #7677 Python test surface returned",
            ));
        }
        if is_state_or_bgjob_module(relative) && !RETAINED_MODULES.contains(&relative) {
            findings.push(Finding::new(
                relative,
                1,
                "unapproved Python state or background-job implementation; final removal is owned by #7681",
            ));
        }
    }
}

fn is_state_or_bgjob_module(path: &str) -> bool {
    (path.starts_with("python/larch/state/") || path.starts_with("python/larch/bgjob/"))
        && Path::new(path)
            .extension()
            .is_some_and(|extension| extension.eq_ignore_ascii_case("py"))
}

fn table_text<'a>(table: &'a RegistryTable, key: &str) -> &'a str {
    table.get(key).and_then(Value::as_str).unwrap_or_default()
}

fn table_integer(table: &RegistryTable, key: &str) -> Option<i64> {
    table.get(key).and_then(Value::as_integer)
}

fn selector(table: &RegistryTable) -> (&str, &str) {
    (table_text(table, "domain"), table_text(table, "verb"))
}

fn registry_finding(message: String) -> Finding {
    Finding::new(COMMAND_REGISTRY_PATH, 1, message)
}
