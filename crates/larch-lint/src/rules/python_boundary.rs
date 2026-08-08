//! Shared evidence helpers for the Python-free command boundary rules.
//!
//! `release-python-free` and `reporting-python-free` both prove the same two
//! facts about a closed command set: no selector is registered in
//! `python/larch/cli.py`, and no retired module-level entrypoint survives in
//! the Python module the ledger still records. This module owns that evidence
//! so neither rule grows a second copy of it.

use std::sync::LazyLock;

use regex::Regex;

use crate::{Finding, LintError, RepoPath, Repository};

const PYTHON_REGISTRY_PATH: &str = "python/larch/cli.py";

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
