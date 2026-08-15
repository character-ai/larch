//! Shared evidence helpers for the Python-free command boundary rules.
//!
//! Closure rules share command-row parsing as well as two Python-retirement
//! facts: no selector is registered in `python/larch/cli.py`, and no retired
//! module-level entrypoint survives in the Python module the ledger records.
//! This module owns that evidence so sibling rules do not duplicate it.

use std::sync::LazyLock;

use regex::Regex;
use toml::{Value, map::Map};

use crate::{Finding, LintError, RepoPath, Repository};

const PYTHON_REGISTRY_PATH: &str = "python/larch/cli.py";

type RegistryTable = Map<String, Value>;

/// One parsed command-registry row shared by Python-free closure rules.
pub(super) struct RegistryCommand<'a> {
    table: &'a RegistryTable,
    pub(super) domain: &'a str,
    pub(super) verb: &'a str,
    pub(super) selector: String,
}

impl<'a> RegistryCommand<'a> {
    pub(super) fn parse(value: &'a Value) -> Option<Self> {
        let table = value.as_table()?;
        let domain = registry_text(table, "domain");
        let verb = registry_text(table, "verb");
        Some(Self {
            table,
            domain,
            verb,
            selector: [domain, verb].join(" "),
        })
    }

    pub(super) fn text(&self, key: &str) -> Option<&str> {
        self.table.get(key).and_then(Value::as_str)
    }

    pub(super) fn integer(&self, key: &str) -> Option<i64> {
        self.table.get(key).and_then(Value::as_integer)
    }

    pub(super) fn has_final_cutover(&self) -> bool {
        [
            ("owner", "rust"),
            ("implementation_parity", "complete"),
            ("consumer_cutover", "complete"),
            ("python_removal", "complete"),
        ]
        .into_iter()
        .all(|(key, expected)| self.text(key) == Some(expected))
    }
}

fn registry_text<'a>(table: &'a RegistryTable, key: &str) -> &'a str {
    table.get(key).and_then(Value::as_str).unwrap_or_default()
}

static PYTHON_REGISTRATION: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"\(\s*["'](?P<domain>[a-z0-9-]+)["']\s*,\s*["'](?P<verb>[a-z0-9-]+)["']\s*\)\s*:"#)
        .expect("Python registration expression is valid")
});

/// Report every `python/larch/cli.py` registration whose selector the caller
/// still owns in Rust.
///
/// # Errors
/// Propagates a read failure for the Python command registry.
pub(super) fn check_python_registry(
    repository: &Repository,
    in_scope: &dyn Fn(&str, &str) -> bool,
    message: &dyn Fn(&str, &str) -> String,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    let path = RepoPath::from_trusted(PYTHON_REGISTRY_PATH);
    if repository.paths().binary_search(&path).is_err() {
        return Ok(());
    }
    let source = repository.read_utf8(&path)?;
    for captures in PYTHON_REGISTRATION.captures_iter(&source) {
        let domain = &captures["domain"];
        let verb = &captures["verb"];
        if !in_scope(domain, verb) {
            continue;
        }
        findings.push(Finding::new(
            PYTHON_REGISTRY_PATH,
            offset_line_number(&source, captures.get(0).expect("whole capture").start()),
            message(domain, verb),
        ));
    }
    Ok(())
}

/// Report every retired Python target whose module still defines the entry
/// point at module level.
///
/// # Errors
/// Propagates a read failure for a tracked Python module.
pub(super) fn check_retired_entrypoints(
    repository: &Repository,
    targets: &[(String, String)],
    message: &dyn Fn(&str, &str) -> String,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    let mut seen: Vec<&(String, String)> = targets.iter().collect();
    seen.sort_unstable();
    seen.dedup();
    for (module, function) in seen {
        let module_path = format!("python/{}.py", module.replace('.', "/"));
        let path = RepoPath::from_trusted(&module_path);
        if repository.paths().binary_search(&path).is_err() {
            continue;
        }
        let source = repository.read_utf8(&path)?;
        let definition = Regex::new(&format!(
            r"(?m)^(?:async +)?def +{} *\(",
            regex::escape(function)
        ))
        .expect("escaped Python function expression is valid");
        for matched in definition.find_iter(&source) {
            findings.push(Finding::new(
                &module_path,
                offset_line_number(&source, matched.start()),
                message(module, function),
            ));
        }
    }
    Ok(())
}

/// Return the one-based line that contains `offset`.
pub(super) fn offset_line_number(source: &str, offset: usize) -> u32 {
    u32::try_from(source[..offset].bytes().filter(|byte| *byte == b'\n').count() + 1)
        .unwrap_or(u32::MAX)
}
