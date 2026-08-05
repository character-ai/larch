//! Keep every Python `lint` verb classified as port, retire, or rust-owned.
//!
//! # Crate survey (issue #8095)
//!
//! | Need | Candidates | Selection |
//! |---|---|---|
//! | Python verb inventory | fresh `_REGISTRY` regex, shared command-registry importer | Reuse [`crate::command_registry::registered_python_lint_verbs`] so the disposition ledger cannot drift from the command-registry importer. |
//! | Ledger parsing | workspace `csv`, handwritten split | Prefer handwritten tab splits. Exact `csv` ReaderBuilder scaffolding would clone the topology TSV helper and trip `duplicate-code`. |
//! | Makefile check-list parse | full Make AST, line scan for `PY_LINT_FAST_CHECKS :=` | Scan the committed Makefile for the master assignment only; shard lists are derived views and stay out of this rule. |

use std::collections::{BTreeMap, BTreeSet};

use crate::{
    Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput,
    command_registry,
};

const NAME: &str = "python-lint-disposition";
const DESCRIPTION: &str =
    "Require a port/retire/rust-owned disposition for every Python lint verb";
const LEDGER_PATH: &str = "crates/larch-lint/data/python-lint-disposition.tsv";
const MAKEFILE_PATH: &str = "Makefile";
const EXPECTED_COLUMNS: usize = 4;
const FAST_CHECKS_PREFIX: &str = "PY_LINT_FAST_CHECKS :=";

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/python-lint-disposition.toml",
);

#[derive(Debug)]
pub struct PythonLintDispositionRule;

pub static RULE: PythonLintDispositionRule = PythonLintDispositionRule;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Disposition {
    Port,
    Retire,
    RustOwned,
}

impl Disposition {
    fn parse(raw: &str) -> Option<Self> {
        match raw {
            "port" => Some(Self::Port),
            "retire" => Some(Self::Retire),
            "rust-owned" => Some(Self::RustOwned),
            _ => None,
        }
    }
}

#[derive(Debug)]
struct LedgerRow {
    line: u32,
    verb: String,
    disposition: Disposition,
    surfaces: Vec<String>,
}

impl Rule for PythonLintDispositionRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let registered = command_registry::registered_python_lint_verbs(repository)?;
        let rows = read_ledger(repository)?;
        let fast_checks = read_fast_checks(repository)?;
        let mut findings = Vec::new();
        let mut by_verb = BTreeMap::<String, &LedgerRow>::new();

        for row in &rows {
            if let Some(previous) = by_verb.insert(row.verb.clone(), row) {
                findings.push(Finding::new(
                    LEDGER_PATH,
                    row.line,
                    format!(
                        "duplicate disposition row for lint verb {}; first seen at line {}",
                        row.verb, previous.line
                    ),
                ));
            }
        }

        for verb in &registered {
            if !by_verb.contains_key(verb) {
                findings.push(Finding::new(
                    LEDGER_PATH,
                    1,
                    format!("missing disposition row for registered lint verb {verb}"),
                ));
            }
        }

        for row in &rows {
            if !registered.contains(&row.verb) {
                findings.push(Finding::new(
                    LEDGER_PATH,
                    row.line,
                    format!(
                        "disposition row names unregistered lint verb {}",
                        row.verb
                    ),
                ));
            }
            if row.disposition == Disposition::Retire
                && fast_checks.contains(&row.verb)
                && surfaces_gone(repository, &row.surfaces)
            {
                findings.push(Finding::new(
                    LEDGER_PATH,
                    row.line,
                    format!(
                        "retire disposition for {} remains in PY_LINT_FAST_CHECKS after target surface {:?} is gone",
                        row.verb, row.surfaces
                    ),
                ));
            }
        }

        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

fn read_ledger(repository: &Repository) -> Result<Vec<LedgerRow>, LintError> {
    let path = RepoPath::from_trusted(LEDGER_PATH);
    let source = repository.read_required_utf8(
        &path,
        format!("disposition ledger not found: {LEDGER_PATH}"),
    )?;
    let mut rows = Vec::new();
    for (index, raw_line) in source.split('\n').enumerate() {
        let line = line_number(index, LEDGER_PATH)?;
        if raw_line.contains('\r') {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}:{line}: CRLF line endings not allowed (use LF)"
            )));
        }
        if raw_line.is_empty() || raw_line.starts_with('#') {
            continue;
        }
        let fields: Vec<&str> = raw_line.split('\t').collect();
        if fields.len() != EXPECTED_COLUMNS
            || fields.iter().any(|field| field.is_empty())
        {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}:{line}: malformed row; expected verb, disposition, target_surface, rationale"
            )));
        }
        let verb = fields[0].to_owned();
        if !is_verb_token(&verb) {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}:{line}: invalid lint verb token {verb:?}"
            )));
        }
        let Some(disposition) = Disposition::parse(fields[1]) else {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}:{line}: disposition must be port, retire, or rust-owned; got {}",
                fields[1]
            )));
        };
        let surfaces = parse_surfaces(fields[2], line)?;
        rows.push(LedgerRow {
            line,
            verb,
            disposition,
            surfaces,
        });
    }
    Ok(rows)
}

fn parse_surfaces(raw: &str, line: u32) -> Result<Vec<String>, LintError> {
    let mut surfaces = Vec::new();
    for part in raw.split(',') {
        let surface = part.trim();
        if surface.is_empty() {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}:{line}: target_surface entry must be non-empty"
            )));
        }
        if surface.starts_with('/')
            || surface.starts_with("./")
            || surface.contains("..")
            || surface.contains('*')
            || surface.contains('?')
            || surface.contains('[')
        {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}:{line}: target_surface must be a plain repo-relative path without globs or traversal: {surface}"
            )));
        }
        surfaces.push(surface.trim_end_matches('/').to_owned());
    }
    if surfaces.is_empty() {
        return Err(LintError::new(format!(
            "{LEDGER_PATH}:{line}: target_surface must list at least one path"
        )));
    }
    Ok(surfaces)
}

fn read_fast_checks(repository: &Repository) -> Result<BTreeSet<String>, LintError> {
    let path = RepoPath::from_trusted(MAKEFILE_PATH);
    if repository.paths().binary_search(&path).is_err() {
        return Ok(BTreeSet::new());
    }
    let source = repository.read_utf8(&path)?;
    let mut checks = BTreeSet::new();
    for (index, raw_line) in source.lines().enumerate() {
        let trimmed = raw_line.trim_start();
        if !trimmed.starts_with(FAST_CHECKS_PREFIX) {
            continue;
        }
        if trimmed.starts_with("PY_LINT_FAST_CHECKS_SHARD_") {
            continue;
        }
        let rest = trimmed[FAST_CHECKS_PREFIX.len()..].trim();
        if rest.is_empty() {
            return Err(LintError::new(format!(
                "{MAKEFILE_PATH}:{}: {FAST_CHECKS_PREFIX} assignment is empty",
                index + 1
            )));
        }
        for token in rest.split_whitespace() {
            checks.insert(token.to_owned());
        }
        return Ok(checks);
    }
    Ok(checks)
}

fn surfaces_gone(repository: &Repository, surfaces: &[String]) -> bool {
    surfaces
        .iter()
        .all(|surface| !repository.root().join(surface).exists())
}

pub(super) fn is_verb_token(token: &str) -> bool {
    !token.is_empty()
        && token
            .chars()
            .all(|ch| ch.is_ascii_lowercase() || ch.is_ascii_digit() || ch == '-')
}

fn line_number(index: usize, path: &str) -> Result<u32, LintError> {
    u32::try_from(index + 1)
        .map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))
}
