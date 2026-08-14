//! Canonical Python-to-Rust command ownership and production-caller ledger.

use std::{
    collections::{BTreeMap, BTreeSet, HashMap},
    fmt::Write as _,
    fs::{self, OpenOptions},
    io::Write as _,
    path::Path,
    process,
    sync::{Arc, LazyLock},
};

use regex::Regex;
use serde::Deserialize;
use tree_sitter::{Node, Tree};

use crate::{Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput, syntax};

const NAME: &str = "command-registry";
const DESCRIPTION: &str =
    "Validate command ownership, migration state, and production caller inventory";
const LEDGER_PATH: &str = "crates/larch-lint/data/command-registry.toml";
const CLEAN_INSTALL_CASES_PATH: &str = "crates/larch-cli/tests/parity.rs";
const PYTHON_REGISTRY_PATH: &str = "python/larch/cli.py";
const HOOKS_PATH: &str = "hooks/hooks.json";
const SCHEMA_VERSION: u32 = 2;
const CHIEF_MIGRATION_ISSUE: u64 = 7687;
const MIGRATION_UMBRELLA_ISSUES: std::ops::RangeInclusive<u64> = 7673..=7687;
const TRACKING_PURE_FUNCTIONS: [&str; 4] = [
    "_drop_issue_footer",
    "link_pr_closes",
    "link_pr_for_disposition",
    "link_pr_part_of",
];
const TRACKING_PURE_METHODS: [&str; 6] = ["join", "pop", "rstrip", "splitlines", "strip", "split"];

struct IssuePythonBoundary {
    module: &'static str,
    selector: &'static str,
    allowed_functions: &'static [&'static str],
    module_must_be_absent: bool,
}

const ISSUE_PYTHON_BOUNDARIES: [IssuePythonBoundary; 2] = [
    IssuePythonBoundary {
        module: "larch.issue.execution_issues",
        selector: "execution-issues *",
        allowed_functions: &[],
        module_must_be_absent: true,
    },
    IssuePythonBoundary {
        module: "larch.issue.tracking_issue",
        selector: "tracking-issue *",
        allowed_functions: &TRACKING_PURE_FUNCTIONS,
        module_must_be_absent: false,
    },
];

static PYTHON_ROW: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r#"(?m)^\s*\(\"(?P<domain>[a-z0-9-]+)\",\s*\"(?P<verb>[a-z0-9-]+)\"\):\s*\(\s*\"(?P<module>[A-Za-z0-9_.]+)\",\s*\"(?P<function>[A-Za-z0-9_]+)\",\s*(?P<machine>True|False),?\s*\),"#,
    )
    .expect("Python command registry row expression is valid")
});
static PYTHON_KEY: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"(?m)^\s*\(\"[a-z0-9-]+\",\s*\"[a-z0-9-]+\"\):"#)
        .expect("Python command registry key expression is valid")
});
static HOOK_PATH: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"\$\{CLAUDE_PLUGIN_ROOT\}/(?P<path>[^\"\s]+)"#)
        .expect("hook command path expression is valid")
});
static CLEAN_INSTALL_CASE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r#"CleanInstallCase::new\(\s*\"(?P<id>[a-z0-9-]+)\"\s*,\s*\"(?P<domain>[a-z0-9-]+)\"\s*,\s*\"(?P<verb>[a-z0-9-]+)\"\s*,?\s*\)"#,
    )
    .expect("clean-install parity case expression is valid")
});

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/command-registry.toml",
);

#[derive(Debug)]
pub struct CommandRegistryRule;

pub static RULE: CommandRegistryRule = CommandRegistryRule;

impl Rule for CommandRegistryRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let ledger = read_ledger(repository)?;
        let python = read_python_registry(repository)?;
        let known = ledger.commands.iter().map(CommandRecord::key).collect();
        let retirement_records = completed_python_retirement_records(&ledger);
        let python_sources = read_python_sources(repository, &retirement_records, true)?;
        let callers = discover_callers(repository, &known, Some(&python_sources))?;
        let clean_install_cases = read_clean_install_cases(repository)?;
        validate_ledger(
            &ledger,
            &python,
            &callers,
            &python_sources,
            &clean_install_cases,
        )
    }
}

/// Re-run the canonical Python-retirement proof for one migration family.
///
/// Rules that pin a completed migration call this helper instead of copying
/// the syntax-aware import, reference, and call analysis owned here.
pub fn python_retirement_findings_for_issues(
    repository: &Repository,
    migration_issues: &[u64],
) -> Result<Vec<Finding>, LintError> {
    let ledger = read_ledger(repository)?;
    let python = read_python_registry(repository)?;
    let retirement_checks = retirement_checks(ledger.commands.iter().filter(|record| {
        record
            .migration_issue
            .is_some_and(|issue| migration_issues.contains(&issue))
    }));
    let source_retirement_records = completed_python_retirement_records(&ledger);
    let python_sources = read_python_sources(repository, &source_retirement_records, true)?;
    let mut findings = Vec::new();
    validate_python_retirements(&retirement_checks, &python, &python_sources, &mut findings);
    Ok(findings)
}

/// Return every command selector the canonical ledger recognizes.
///
/// Migration-audit uses this typed projection when it renders command evidence;
/// keeping the TOML import here prevents a second, subtly different registry
/// parser at the command boundary.
///
/// # Errors
///
/// Returns an error when the command registry is unavailable or malformed.
pub fn command_audit_selectors(
    repository: &Repository,
) -> Result<Vec<CommandAuditSelector>, LintError> {
    let ledger = read_ledger(repository)?;
    let commands = command_map(&ledger)?;
    Ok(commands
        .keys()
        .map(|key| CommandAuditSelector {
            domain: key.domain.clone(),
            verb: key.verb.clone(),
        })
        .collect())
}

/// Discover live in-process Python ownership of corrected issue commands.
///
/// `issue-python-free` consumes the same facts that feed the command caller
/// ledger, so its closeout proof cannot drift from caller discovery.
pub fn issue_in_process_python_findings(
    repository: &Repository,
) -> Result<Vec<Finding>, LintError> {
    let mut findings = Vec::new();
    for path in repository.paths() {
        if !is_production_issue_python_path(path.as_str()) {
            continue;
        }
        let source = repository.read_utf8(path)?;
        if !issue_python_boundary_candidate(path.as_str(), &source) {
            continue;
        }
        for selector in extract_issue_in_process_selectors(path.as_str(), &source)? {
            findings.push(finding(format!(
                "python-command-equivalent-still-owned {selector}: {}",
                path.as_str()
            )));
        }
    }
    findings.sort();
    findings.dedup();
    Ok(findings)
}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct CommandAuditSelector {
    pub domain: String,
    pub verb: String,
}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
struct CommandKey {
    domain: String,
    verb: String,
}

impl CommandKey {
    fn new(domain: &str, verb: &str) -> Self {
        Self {
            domain: domain.to_owned(),
            verb: verb.to_owned(),
        }
    }

    fn selector(&self) -> String {
        format!("{} {}", self.domain, self.verb)
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(deny_unknown_fields)]
struct Ledger {
    schema_version: u32,
    #[serde(default)]
    commands: Vec<CommandRecord>,
    #[serde(default)]
    callers: Vec<CallerRecord>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(deny_unknown_fields)]
struct CommandRecord {
    domain: String,
    verb: String,
    python_module: String,
    python_function: String,
    machine_stdout: bool,
    owner: Owner,
    implementation_parity: Parity,
    consumer_cutover: Completion,
    python_removal: Completion,
    planning_issue: u64,
    #[serde(default)]
    migration_issue: Option<u64>,
    #[serde(default)]
    clean_install_test: Option<String>,
}

impl CommandRecord {
    fn key(&self) -> CommandKey {
        CommandKey::new(&self.domain, &self.verb)
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq)]
#[serde(rename_all = "kebab-case")]
enum Owner {
    Python,
    Rust,
    Retired,
}

impl Owner {
    const fn as_str(self) -> &'static str {
        match self {
            Self::Python => "python",
            Self::Rust => "rust",
            Self::Retired => "retired",
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq)]
#[serde(rename_all = "kebab-case")]
enum Parity {
    Pending,
    Complete,
    NotApplicable,
}

impl Parity {
    const fn as_str(self) -> &'static str {
        match self {
            Self::Pending => "pending",
            Self::Complete => "complete",
            Self::NotApplicable => "not-applicable",
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq)]
#[serde(rename_all = "kebab-case")]
enum Completion {
    Pending,
    Complete,
}

impl Completion {
    const fn as_str(self) -> &'static str {
        match self {
            Self::Pending => "pending",
            Self::Complete => "complete",
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(deny_unknown_fields)]
struct CallerRecord {
    path: String,
    kind: CallerKind,
    #[serde(default)]
    python: Vec<String>,
    #[serde(default)]
    rust: Vec<String>,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd)]
#[serde(rename_all = "kebab-case")]
enum CallerKind {
    Skill,
    Hook,
    Script,
    Ci,
    Agent,
    PythonRuntime,
}

impl CallerKind {
    const fn as_str(self) -> &'static str {
        match self {
            Self::Skill => "skill",
            Self::Hook => "hook",
            Self::Script => "script",
            Self::Ci => "ci",
            Self::Agent => "agent",
            Self::PythonRuntime => "python-runtime",
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct PythonCommand {
    module: String,
    function: String,
    machine_stdout: bool,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(deny_unknown_fields)]
struct MigrationIssueAuditInput {
    schema_version: u32,
    rollout_enabled: bool,
    #[serde(default)]
    issues: Vec<MigrationIssueRecord>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(deny_unknown_fields)]
struct MigrationIssueRecord {
    number: u64,
    state: IssueState,
    executable_leaf: bool,
    command: Option<CommandKeyRecord>,
    #[serde(default)]
    plan_commands: Vec<CommandKeyRecord>,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq)]
#[serde(rename_all = "lowercase")]
enum IssueState {
    Open,
    Closed,
}

#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd)]
#[serde(deny_unknown_fields)]
struct CommandKeyRecord {
    domain: String,
    verb: String,
}

impl CommandKeyRecord {
    fn key(&self) -> CommandKey {
        CommandKey::new(&self.domain, &self.verb)
    }
}

fn read_ledger(repository: &Repository) -> Result<Ledger, LintError> {
    let content = required_utf8(repository, LEDGER_PATH)?;
    parse_ledger(&content)
}

fn parse_ledger(content: &str) -> Result<Ledger, LintError> {
    let ledger: Ledger = toml::from_str(content)
        .map_err(|error| LintError::new(format!("{LEDGER_PATH}: invalid TOML: {error}")))?;
    if ledger.schema_version != SCHEMA_VERSION {
        return Err(LintError::new(format!(
            "{LEDGER_PATH}: unsupported schema_version {}; expected {SCHEMA_VERSION}",
            ledger.schema_version
        )));
    }
    Ok(ledger)
}

fn read_clean_install_cases(
    repository: &Repository,
) -> Result<BTreeMap<String, CommandKey>, LintError> {
    let source = required_utf8(repository, CLEAN_INSTALL_CASES_PATH)?;
    let table_start = source.find("const CLEAN_INSTALL_CASES:").ok_or_else(|| {
        LintError::new(format!(
            "{CLEAN_INSTALL_CASES_PATH}: missing CLEAN_INSTALL_CASES table"
        ))
    })?;
    let table_tail = &source[table_start..];
    let table_end = table_tail.find("];").ok_or_else(|| {
        LintError::new(format!(
            "{CLEAN_INSTALL_CASES_PATH}: unterminated CLEAN_INSTALL_CASES table"
        ))
    })?;
    let table = &table_tail[..table_end + 2];
    let mut by_id = BTreeMap::new();
    let mut by_selector = BTreeMap::new();
    for captures in CLEAN_INSTALL_CASE.captures_iter(table) {
        let id = captures["id"].to_owned();
        let key = CommandKey::new(&captures["domain"], &captures["verb"]);
        if by_id.insert(id.clone(), key.clone()).is_some() {
            return Err(LintError::new(format!(
                "{CLEAN_INSTALL_CASES_PATH}: duplicate clean-install fixture id {id}"
            )));
        }
        if let Some(previous) = by_selector.insert(key.clone(), id.clone()) {
            return Err(LintError::new(format!(
                "{CLEAN_INSTALL_CASES_PATH}: duplicate clean-install selector {} in {previous} and {id}",
                key.selector()
            )));
        }
    }
    let syntactic_rows = table.matches("CleanInstallCase::new(").count();
    if syntactic_rows != by_id.len() {
        return Err(LintError::new(format!(
            "{CLEAN_INSTALL_CASES_PATH}: parsed {} of {syntactic_rows} clean-install fixture rows",
            by_id.len()
        )));
    }
    if by_id.is_empty() {
        return Err(LintError::new(format!(
            "{CLEAN_INSTALL_CASES_PATH}: clean-install fixture table is empty"
        )));
    }
    Ok(by_id)
}

/// Return every registered Python `lint <verb>` name from `python/larch/cli.py`.
///
/// Shared with the python-lint-disposition rule so the verb inventory has one
/// importer for the `_REGISTRY` shape.
pub fn registered_python_lint_verbs(
    repository: &Repository,
) -> Result<BTreeSet<String>, LintError> {
    let python = read_python_registry(repository)?;
    Ok(python
        .into_keys()
        .filter(|key| key.domain == "lint")
        .map(|key| key.verb)
        .collect())
}

/// Return every `domain verb` selector the command registry marks Rust-owned.
///
/// Shared with developer-tooling migration guards so caller drift detection
/// cannot diverge from the ownership ledger importer.
pub fn rust_owned_selectors(repository: &Repository) -> Result<BTreeSet<String>, LintError> {
    let ledger = read_ledger(repository)?;
    Ok(ledger
        .commands
        .iter()
        .filter(|record| record.owner == Owner::Rust)
        .map(|record| record.key().selector())
        .collect())
}

/// Prove that one developer-tooling planning umbrella has no remaining
/// command-level migration debt.
///
/// This is deliberately narrower than [`CommandRegistryRule`]'s normal
/// whole-ledger validation: a closure guard needs an affirmative proof for
/// every row assigned to one umbrella, including the live Python registry,
/// Python implementation references, and production caller inventory. Keeping
/// the parsing and syntax-aware retirement checks here prevents a sibling rule
/// from growing a second command-registry parser.
pub fn planning_issue_closure_findings(
    repository: &Repository,
    planning_issue: u64,
) -> Result<Vec<Finding>, LintError> {
    let ledger = read_ledger(repository)?;
    let records = ledger
        .commands
        .iter()
        .filter(|record| record.planning_issue == planning_issue)
        .collect::<Vec<_>>();
    let mut findings = Vec::new();
    for record in &records {
        let selector = record.key().selector();
        if record.owner != Owner::Rust {
            findings.push(finding(format!(
                "planning issue #{planning_issue} command {selector} is not Rust-owned"
            )));
        }
        if record.implementation_parity != Parity::Complete {
            findings.push(finding(format!(
                "planning issue #{planning_issue} command {selector} has incomplete implementation parity"
            )));
        }
        if record.consumer_cutover != Completion::Complete {
            findings.push(finding(format!(
                "planning issue #{planning_issue} command {selector} has incomplete consumer cutover"
            )));
        }
        if record.python_removal != Completion::Complete {
            findings.push(finding(format!(
                "planning issue #{planning_issue} command {selector} has incomplete Python removal"
            )));
        }
        if !record
            .migration_issue
            .is_some_and(|issue| issue != 0 && !MIGRATION_UMBRELLA_ISSUES.contains(&issue))
        {
            findings.push(finding(format!(
                "planning issue #{planning_issue} command {selector} lacks an exact non-umbrella migration leaf"
            )));
        }
    }

    let known = ledger.commands.iter().map(CommandRecord::key).collect();
    let python = read_python_registry(repository)?;
    let python_sources = read_python_sources(repository, &records, true)?;
    let retirement_checks = retirement_checks(records.iter().copied());
    validate_python_retirements(&retirement_checks, &python, &python_sources, &mut findings);
    let callers = discover_callers(repository, &known, Some(&python_sources))?;
    let callers = caller_map(&callers)?;
    for record in &records {
        let key = record.key();
        for caller in matching_callers(&key, &callers, Runtime::Python) {
            findings.push(finding(format!(
                "planning issue #{planning_issue} command {} retains a Python production caller: {caller}",
                key.selector()
            )));
        }
    }
    findings.sort();
    findings.dedup();
    Ok(findings)
}

/// Extract `domain verb` selectors that follow a `python/cli.py` marker.
///
/// Shared with developer-tooling guards so Makefile, workflow, pre-commit, and
/// script scans use the same selector grammar as the command-registry caller
/// inventory.
pub fn python_cli_selectors(content: &str) -> Vec<String> {
    extract_selectors(content, "python/cli.py")
}

fn read_python_registry(
    repository: &Repository,
) -> Result<BTreeMap<CommandKey, PythonCommand>, LintError> {
    let source = required_utf8(repository, PYTHON_REGISTRY_PATH)?;
    parse_python_registry(&source)
}

fn parse_python_registry(source: &str) -> Result<BTreeMap<CommandKey, PythonCommand>, LintError> {
    let start = source.find("_REGISTRY:").ok_or_else(|| {
        LintError::new(format!(
            "{PYTHON_REGISTRY_PATH}: missing _REGISTRY declaration"
        ))
    })?;
    let tail = &source[start..];
    let end = tail.find("\n}\n").ok_or_else(|| {
        LintError::new(format!(
            "{PYTHON_REGISTRY_PATH}: unterminated _REGISTRY declaration"
        ))
    })?;
    let registry = &tail[..end + 2];
    let syntactic_rows = PYTHON_KEY.find_iter(registry).count();
    let mut commands = BTreeMap::new();
    for captures in PYTHON_ROW.captures_iter(registry) {
        let key = CommandKey::new(&captures["domain"], &captures["verb"]);
        let command = PythonCommand {
            module: captures["module"].to_owned(),
            function: captures["function"].to_owned(),
            machine_stdout: &captures["machine"] == "True",
        };
        if commands.insert(key.clone(), command).is_some() {
            return Err(LintError::new(format!(
                "{PYTHON_REGISTRY_PATH}: duplicate command {}",
                key.selector()
            )));
        }
    }
    if commands.len() != syntactic_rows {
        return Err(LintError::new(format!(
            "{PYTHON_REGISTRY_PATH}: parsed {} of {syntactic_rows} command rows; update the Rust importer for the new source shape",
            commands.len()
        )));
    }
    if commands.is_empty() {
        return Err(LintError::new(format!(
            "{PYTHON_REGISTRY_PATH}: command registry is empty"
        )));
    }
    Ok(commands)
}

fn required_utf8(repository: &Repository, path: &str) -> Result<String, LintError> {
    let path = RepoPath::from_trusted(path);
    if repository.paths().binary_search(&path).is_err() {
        return Err(LintError::new(format!("{path}: required file is missing")));
    }
    repository.read_utf8(&path).map(|source| source.to_string())
}

fn validate_ledger(
    ledger: &Ledger,
    python: &BTreeMap<CommandKey, PythonCommand>,
    live_callers: &[CallerRecord],
    python_sources: &[PythonSource],
    clean_install_cases: &BTreeMap<String, CommandKey>,
) -> Result<RuleOutput, LintError> {
    let commands = command_map(ledger)?;
    validate_clean_install_references(&commands, clean_install_cases)?;
    let callers = caller_map(&ledger.callers)?;
    validate_caller_selectors(&callers, &commands)?;
    let live_callers = caller_map(live_callers)?;
    let mut findings = Vec::new();

    for key in python.keys() {
        if !commands.contains_key(key) {
            findings.push(finding(format!(
                "Python registry command {} is missing from the ownership ledger",
                key.selector()
            )));
        }
    }
    for (key, record) in &commands {
        validate_command_state(key, record, python.get(key), &callers, &mut findings);
        validate_clean_install_coverage(
            key,
            record,
            &live_callers,
            clean_install_cases,
            &mut findings,
        );
    }
    let retirement_checks = retirement_checks(
        commands
            .values()
            .copied()
            .filter(|record| record.python_removal == Completion::Complete),
    );
    validate_python_retirements(&retirement_checks, python, python_sources, &mut findings);
    compare_callers(&callers, &live_callers, &mut findings);
    Ok(RuleOutput::from_findings(findings))
}

fn command_map(ledger: &Ledger) -> Result<BTreeMap<CommandKey, &CommandRecord>, LintError> {
    let mut commands = BTreeMap::new();
    for command in &ledger.commands {
        validate_token("domain", &command.domain)?;
        validate_token("verb", &command.verb)?;
        if command.python_module.is_empty() || command.python_function.is_empty() {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}: {} must retain non-empty Python target metadata",
                command.key().selector()
            )));
        }
        if command.planning_issue == 0 {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}: {} has no responsible planning issue",
                command.key().selector()
            )));
        }
        if command.planning_issue == CHIEF_MIGRATION_ISSUE {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}: {} delegates planning ownership to chief umbrella #{CHIEF_MIGRATION_ISSUE}; name the domain roadmap owner or completed leaf",
                command.key().selector()
            )));
        }
        if let Some(issue) = command.migration_issue {
            if issue == 0 || MIGRATION_UMBRELLA_ISSUES.contains(&issue) {
                return Err(LintError::new(format!(
                    "{LEDGER_PATH}: {} assigns atomic migration ownership to umbrella #{issue}; name an executable leaf",
                    command.key().selector()
                )));
            }
        } else if command.owner != Owner::Python
            || command.consumer_cutover == Completion::Complete
            || command.python_removal == Completion::Complete
        {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}: {} completed migration state without an exact migration leaf",
                command.key().selector()
            )));
        }
        if let Some(fixture) = &command.clean_install_test {
            validate_token("clean_install_test", fixture)?;
        }
        let key = command.key();
        if commands.insert(key.clone(), command).is_some() {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}: duplicate ownership row for {}",
                key.selector()
            )));
        }
    }
    Ok(commands)
}

fn validate_clean_install_references(
    commands: &BTreeMap<CommandKey, &CommandRecord>,
    cases: &BTreeMap<String, CommandKey>,
) -> Result<(), LintError> {
    let mut claimed = BTreeMap::new();
    for (key, command) in commands {
        let Some(fixture) = &command.clean_install_test else {
            continue;
        };
        if let Some(previous) = claimed.insert(fixture, key) {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}: duplicate clean_install_test {fixture:?} for {} and {}",
                previous.selector(),
                key.selector()
            )));
        }
        if !cases.contains_key(fixture) {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}: {} references unknown clean_install_test {fixture:?}",
                key.selector()
            )));
        }
    }
    Ok(())
}

fn validate_clean_install_coverage(
    key: &CommandKey,
    record: &CommandRecord,
    callers: &BTreeMap<String, &CallerRecord>,
    cases: &BTreeMap<String, CommandKey>,
    findings: &mut Vec<Finding>,
) {
    if record.owner != Owner::Rust || matching_callers(key, callers, Runtime::Rust).is_empty() {
        return;
    }
    let covered = record
        .clean_install_test
        .as_ref()
        .and_then(|fixture| cases.get(fixture))
        .is_some_and(|fixture_key| fixture_key == key);
    if !covered {
        findings.push(finding(format!(
            "clean-install-coverage-missing {}",
            key.selector()
        )));
    }
}

fn caller_map(callers: &[CallerRecord]) -> Result<BTreeMap<String, &CallerRecord>, LintError> {
    let mut mapped = BTreeMap::new();
    for caller in callers {
        if caller.path.is_empty()
            || Path::new(&caller.path).is_absolute()
            || caller
                .path
                .split('/')
                .any(|part| part == ".." || part.is_empty())
        {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}: unsafe caller path {:?}",
                caller.path
            )));
        }
        if mapped.insert(caller.path.clone(), caller).is_some() {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}: duplicate caller row for {}",
                caller.path
            )));
        }
        validate_sorted_unique(&caller.path, "python", &caller.python)?;
        validate_sorted_unique(&caller.path, "rust", &caller.rust)?;
    }
    Ok(mapped)
}

fn validate_sorted_unique(
    path: &str,
    runtime: &str,
    selectors: &[String],
) -> Result<(), LintError> {
    if selectors.windows(2).any(|pair| pair[0] >= pair[1]) {
        return Err(LintError::new(format!(
            "{LEDGER_PATH}: {path} {runtime} selectors must be sorted and unique"
        )));
    }
    Ok(())
}

fn validate_caller_selectors(
    callers: &BTreeMap<String, &CallerRecord>,
    commands: &BTreeMap<CommandKey, &CommandRecord>,
) -> Result<(), LintError> {
    let domains: BTreeSet<&str> = commands.keys().map(|key| key.domain.as_str()).collect();
    for caller in callers.values() {
        for selector in caller.python.iter().chain(&caller.rust) {
            let (domain, verb) = parse_selector(selector)?;
            if verb == "*" {
                if !domains.contains(domain) {
                    return Err(LintError::new(format!(
                        "{LEDGER_PATH}: {} references unknown command domain {domain}",
                        caller.path
                    )));
                }
            } else if !commands.contains_key(&CommandKey::new(domain, verb)) {
                return Err(LintError::new(format!(
                    "{LEDGER_PATH}: {} references unknown command {selector}",
                    caller.path
                )));
            }
        }
    }
    Ok(())
}

fn validate_command_state(
    key: &CommandKey,
    record: &CommandRecord,
    python: Option<&PythonCommand>,
    callers: &BTreeMap<String, &CallerRecord>,
    findings: &mut Vec<Finding>,
) {
    if let Some(python) = python {
        if record.python_module != python.module
            || record.python_function != python.function
            || record.machine_stdout != python.machine_stdout
        {
            findings.push(finding(format!(
                "{} Python target or machine-stdout metadata is stale",
                key.selector()
            )));
        }
    } else if record.owner == Owner::Python || record.python_removal == Completion::Pending {
        findings.push(finding(format!(
            "{} is absent from Python but its ownership or removal state is pending",
            key.selector()
        )));
    }

    let python_callers = matching_callers(key, callers, Runtime::Python);
    let rust_callers = matching_callers(key, callers, Runtime::Rust);
    match record.owner {
        Owner::Python => {
            if record.implementation_parity == Parity::NotApplicable
                || record.consumer_cutover != Completion::Pending
                || record.python_removal != Completion::Pending
            {
                findings.push(finding(format!(
                    "{} has an invalid Python-owned migration state",
                    key.selector()
                )));
            }
            if !rust_callers.is_empty() {
                findings.push(finding(format!(
                    "{} is Python-owned but has Rust callers: {}",
                    key.selector(),
                    rust_callers.join(", ")
                )));
            }
        }
        Owner::Rust => {
            if record.implementation_parity != Parity::Complete
                || record.consumer_cutover != Completion::Complete
            {
                findings.push(finding(format!(
                    "{} is Rust-owned without completed parity and consumer cutover",
                    key.selector()
                )));
            }
            if record.python_removal != Completion::Complete {
                findings.push(finding(format!(
                    "non-atomic-rust-owner {}: python removal is not complete",
                    key.selector()
                )));
            }
            if !python_callers.is_empty() {
                findings.push(finding(format!(
                    "{} cannot cut over to Rust while legacy callers remain: {}",
                    key.selector(),
                    python_callers.join(", ")
                )));
            }
        }
        Owner::Retired => {
            if record.implementation_parity != Parity::NotApplicable
                || record.consumer_cutover != Completion::Complete
                || record.python_removal != Completion::Complete
                || !python_callers.is_empty()
                || !rust_callers.is_empty()
            {
                findings.push(finding(format!(
                    "{} has an invalid retired migration state or live caller",
                    key.selector()
                )));
            }
        }
    }
}

#[derive(Clone, Copy)]
enum Runtime {
    Python,
    Rust,
}

fn matching_callers(
    key: &CommandKey,
    callers: &BTreeMap<String, &CallerRecord>,
    runtime: Runtime,
) -> Vec<String> {
    callers
        .values()
        .filter(|caller| {
            let selectors = match runtime {
                Runtime::Python => &caller.python,
                Runtime::Rust => &caller.rust,
            };
            selectors
                .iter()
                .any(|selector| selector_matches(selector, key))
        })
        .map(|caller| caller.path.clone())
        .collect()
}

fn selector_matches(selector: &str, key: &CommandKey) -> bool {
    parse_selector(selector)
        .is_ok_and(|(domain, verb)| domain == key.domain && (verb == "*" || verb == key.verb))
}

fn parse_selector(selector: &str) -> Result<(&str, &str), LintError> {
    let mut words = selector.split(' ');
    let domain = words.next().unwrap_or_default();
    let verb = words.next().unwrap_or_default();
    if words.next().is_some() || !valid_token(domain) || !(valid_token(verb) || verb == "*") {
        return Err(LintError::new(format!(
            "{LEDGER_PATH}: invalid command selector {selector:?}"
        )));
    }
    Ok((domain, verb))
}

fn validate_token(label: &str, token: &str) -> Result<(), LintError> {
    if valid_token(token) {
        Ok(())
    } else {
        Err(LintError::new(format!(
            "{LEDGER_PATH}: invalid {label} token {token:?}"
        )))
    }
}

fn valid_token(token: &str) -> bool {
    !token.is_empty()
        && token
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-')
}

fn compare_callers(
    ledger: &BTreeMap<String, &CallerRecord>,
    live: &BTreeMap<String, &CallerRecord>,
    findings: &mut Vec<Finding>,
) {
    for (path, caller) in live {
        match ledger.get(path) {
            None => findings.push(finding(format!(
                "production caller {path} is missing from the ledger"
            ))),
            Some(record) if *record != *caller => findings.push(finding(format!(
                "production caller {path} has stale kind or command selectors"
            ))),
            Some(_) => {}
        }
    }
    for path in ledger.keys() {
        if !live.contains_key(path) {
            findings.push(finding(format!(
                "ledger caller {path} is no longer a discovered production caller"
            )));
        }
    }
}

fn finding(message: String) -> Finding {
    Finding::new(LEDGER_PATH, 1, message)
}

fn discover_callers(
    repository: &Repository,
    known: &BTreeSet<CommandKey>,
    python_sources: Option<&[PythonSource]>,
) -> Result<Vec<CallerRecord>, LintError> {
    let hook_paths = discover_hook_paths(repository)?;
    let parsed_python: BTreeMap<&str, &PythonSource> = python_sources
        .unwrap_or_default()
        .iter()
        .map(|document| (document.path.as_str(), document))
        .collect();
    let mut callers = Vec::new();
    for path in repository.paths() {
        let Some(kind) = classify_caller(path.as_str(), &hook_paths) else {
            continue;
        };
        let content = repository.read_utf8(path)?;
        let mut python = filter_selectors(extract_selectors(&content, "python/cli.py"), known);
        if is_production_issue_python_path(path.as_str())
            && issue_python_boundary_candidate(path.as_str(), &content)
        {
            let selectors = if let Some(document) = parsed_python.get(path.as_str()) {
                extract_issue_in_process_selectors_from_document(document)
            } else {
                extract_issue_in_process_selectors(path.as_str(), &content)?
            };
            for selector in filter_selectors(selectors, known) {
                if !python.contains(&selector) {
                    python.push(selector);
                }
            }
            python.sort();
        }
        let python_entrypoint_caller = Path::new(path.as_str())
            .extension()
            .is_some_and(|extension| extension.eq_ignore_ascii_case("py"))
            && (content.contains("larch_entrypoint") || content.contains("scripts/larch.sh"));
        let mut rust = if kind == CallerKind::PythonRuntime || python_entrypoint_caller {
            let selectors =
                if !content.contains("larch_entrypoint") && !content.contains("scripts/larch.sh") {
                    Vec::new()
                } else if let Some(document) = parsed_python.get(path.as_str()) {
                    extract_python_rust_selectors_from_tree(document.tree.root_node(), &content)
                } else {
                    extract_python_rust_selectors(path.as_str(), &content)?
                };
            filter_selectors(selectors, known)
        } else {
            filter_selectors(extract_selectors(&content, "bin/larch"), known)
        };
        if kind != CallerKind::PythonRuntime {
            for selector in filter_selectors(extract_selectors(&content, "scripts/larch.sh"), known)
            {
                if !rust.contains(&selector) {
                    rust.push(selector);
                }
            }
        }
        // Release construction workflows invoke the staged host or matrix binary.
        for marker in ["target/release/larch", "target/$TARGET/release/larch"] {
            for selector in filter_selectors(extract_selectors(&content, marker), known) {
                if !rust.contains(&selector) {
                    rust.push(selector);
                }
            }
        }
        rust.sort();
        if python.is_empty() && rust.is_empty() {
            continue;
        }
        callers.push(CallerRecord {
            path: path.as_str().to_owned(),
            kind,
            python,
            rust,
        });
    }
    callers.sort_by(|left, right| left.path.cmp(&right.path));
    Ok(callers)
}

fn filter_selectors(selectors: Vec<String>, known: &BTreeSet<CommandKey>) -> Vec<String> {
    let domains: BTreeSet<&str> = known.iter().map(|key| key.domain.as_str()).collect();
    selectors
        .into_iter()
        .filter(|selector| {
            parse_selector(selector).is_ok_and(|(domain, verb)| {
                (verb == "*" && domains.contains(domain))
                    || known.contains(&CommandKey::new(domain, verb))
            })
        })
        .collect()
}

fn discover_hook_paths(repository: &Repository) -> Result<BTreeSet<String>, LintError> {
    let hooks = required_utf8(repository, HOOKS_PATH)?;
    Ok(HOOK_PATH
        .captures_iter(&hooks)
        .map(|captures| captures["path"].to_owned())
        .collect())
}

fn classify_caller(path: &str, hook_paths: &BTreeSet<String>) -> Option<CallerKind> {
    if hook_paths.contains(path) {
        return Some(CallerKind::Hook);
    }
    let name = path.rsplit('/').next().unwrap_or(path);
    if name.starts_with("test-")
        || path
            .split('/')
            .any(|part| matches!(part, "fixtures" | "tests"))
    {
        return None;
    }
    if path.starts_with("skills/") {
        Some(CallerKind::Skill)
    } else if (path.starts_with("agents/") || path.starts_with(".claude/agents/"))
        && Path::new(path)
            .extension()
            .is_some_and(|extension| extension.eq_ignore_ascii_case("md"))
    {
        Some(CallerKind::Agent)
    } else if path.starts_with("python/larch/")
        && Path::new(path)
            .extension()
            .is_some_and(|extension| extension.eq_ignore_ascii_case("py"))
    {
        Some(CallerKind::PythonRuntime)
    } else if path.starts_with("scripts/")
        && Path::new(path).extension().is_some_and(|extension| {
            extension.eq_ignore_ascii_case("sh") || extension.eq_ignore_ascii_case("py")
        })
    {
        Some(CallerKind::Script)
    } else if path.starts_with(".github/workflows/")
        || matches!(path, "Makefile" | ".pre-commit-config.yaml")
    {
        Some(CallerKind::Ci)
    } else {
        None
    }
}

#[derive(Debug)]
struct PythonSource {
    path: String,
    module: String,
    package: String,
    source: Arc<str>,
    tree: Arc<Tree>,
}

struct RetirementCheck<'record> {
    key: CommandKey,
    record: &'record CommandRecord,
}

#[derive(Clone, Copy, Default)]
struct RetirementDocumentState(u8);

impl RetirementDocumentState {
    const DEFINITION_PRESENT: u8 = 1;
    const IMPORTED: u8 = 1 << 1;
    const REFERENCED: u8 = 1 << 2;
    const CALLED: u8 = 1 << 3;

    const fn mark(&mut self, finding: u8) {
        self.0 |= finding;
    }

    const fn has(self, finding: u8) -> bool {
        self.0 & finding != 0
    }
}

struct PythonDocumentScan<'source> {
    top_level_functions: Vec<&'source str>,
    import_statements: Vec<&'source str>,
    from_import_statements: Vec<&'source str>,
}

#[derive(Default)]
struct PythonBindings {
    direct_symbols: BTreeSet<String>,
    module_aliases: BTreeSet<String>,
    imported: bool,
}

fn issue_python_boundary_candidate(path: &str, source: &str) -> bool {
    ISSUE_PYTHON_BOUNDARIES.iter().any(|boundary| {
        path == format!("python/{}.py", boundary.module.replace('.', "/"))
            || source.contains(
                boundary
                    .module
                    .rsplit('.')
                    .next()
                    .unwrap_or(boundary.module),
            )
    })
}

fn is_production_issue_python_path(path: &str) -> bool {
    let name = path.rsplit('/').next().unwrap_or(path);
    !name.starts_with("test-")
        && !path
            .split('/')
            .any(|part| matches!(part, "fixtures" | "tests"))
        && (syntax::is_production_python_path(path)
            || ["hooks/", "scripts/", "skills/"]
                .iter()
                .any(|prefix| path.starts_with(prefix)))
        && Path::new(path)
            .extension()
            .is_some_and(|extension| extension.eq_ignore_ascii_case("py"))
}

fn extract_issue_in_process_selectors(path: &str, source: &str) -> Result<Vec<String>, LintError> {
    let tree = parse_python(path, source)?;
    let module = path
        .strip_prefix("python/")
        .and_then(|value| value.strip_suffix(".py"))
        .unwrap_or_default()
        .replace('/', ".")
        .trim_end_matches(".__init__")
        .to_owned();
    let package = if path.ends_with("/__init__.py") {
        module.clone()
    } else {
        module
            .rsplit_once('.')
            .map_or_else(String::new, |(parent, _)| parent.to_owned())
    };
    Ok(extract_issue_in_process_selectors_from_tree(
        tree.root_node(),
        source,
        &module,
        &package,
    ))
}

fn extract_issue_in_process_selectors_from_document(document: &PythonSource) -> Vec<String> {
    extract_issue_in_process_selectors_from_tree(
        document.tree.root_node(),
        &document.source,
        &document.module,
        &document.package,
    )
}

fn extract_issue_in_process_selectors_from_tree(
    root: Node<'_>,
    source: &str,
    module: &str,
    package: &str,
) -> Vec<String> {
    ISSUE_PYTHON_BOUNDARIES
        .iter()
        .filter(|boundary| {
            issue_python_boundary_is_violated(root, source, module, package, boundary)
        })
        .map(|boundary| boundary.selector.to_owned())
        .collect()
}

fn issue_python_boundary_is_violated(
    root: Node<'_>,
    source: &str,
    module: &str,
    package: &str,
    boundary: &IssuePythonBoundary,
) -> bool {
    if module == boundary.module
        && (boundary.module_must_be_absent
            || !retained_tracking_module_is_pure(root, source, boundary.allowed_functions))
    {
        return true;
    }

    let mut aliases = BTreeSet::from([boundary.module.to_owned()]);
    let mut forbidden_import = false;
    walk_named(root, &mut |node| match node.kind() {
        "import_statement" => {
            let text = node_text(node, source).unwrap_or_default();
            let mut bindings = PythonBindings::default();
            inspect_import_statement(text, boundary.module, &mut bindings);
            aliases.extend(bindings.module_aliases);
            if boundary.module_must_be_absent && imports_exact_module(text, boundary.module) {
                forbidden_import = true;
            }
        }
        "import_from_statement" => {
            let text = node_text(node, source).unwrap_or_default();
            let mut bindings = PythonBindings::default();
            inspect_from_import(text, package, boundary.module, "", &mut bindings);
            aliases.extend(bindings.module_aliases);
            if boundary_from_import_is_forbidden(text, package, boundary) {
                forbidden_import = true;
            }
        }
        _ => {}
    });
    if forbidden_import {
        return true;
    }

    let mut forbidden_reference = false;
    walk_named(root, &mut |node| {
        if forbidden_reference {
            return;
        }
        if boundary.module_must_be_absent
            && node.kind() == "call"
            && dynamic_import_target(node, source).as_deref() == Some(boundary.module)
        {
            forbidden_reference = true;
            return;
        }
        if node.kind() != "attribute"
            || has_ancestor_kind(node, &["import_statement", "import_from_statement"])
        {
            return;
        }
        let attribute = compact_node_text(node, source);
        forbidden_reference = aliases.iter().any(|alias| {
            (boundary.module_must_be_absent && attribute == *alias)
                || attribute
                    .strip_prefix(alias)
                    .and_then(|suffix| suffix.strip_prefix('.'))
                    .and_then(|suffix| suffix.split('.').next())
                    .is_some_and(|function| !boundary.allowed_functions.contains(&function))
        });
    });
    forbidden_reference
}

fn dynamic_import_target(node: Node<'_>, source: &str) -> Option<String> {
    let function = node.child_by_field_name("function")?;
    let function_name = compact_node_text(function, source);
    if function_name != "__import__" && !function_name.ends_with(".import_module") {
        return None;
    }
    node.child_by_field_name("arguments")
        .and_then(|arguments| arguments.named_child(0))
        .and_then(|argument| python_string(argument, source))
}

fn imports_exact_module(text: &str, target_module: &str) -> bool {
    text.trim()
        .strip_prefix("import ")
        .into_iter()
        .flat_map(|body| body.split(','))
        .any(|item| item.split_whitespace().next() == Some(target_module))
}

fn boundary_from_import_is_forbidden(
    text: &str,
    package: &str,
    boundary: &IssuePythonBoundary,
) -> bool {
    let flattened = text.replace(['\n', '\r', '(', ')'], " ");
    let Some(body) = flattened.trim().strip_prefix("from ") else {
        return false;
    };
    let Some((raw_module, imports)) = body.split_once(" import ") else {
        return false;
    };
    let module = resolve_import_module(package, raw_module.trim());
    imports.split(',').any(|item| {
        let name = item.split_whitespace().next().unwrap_or_default();
        if module == boundary.module {
            return name == "*" || !boundary.allowed_functions.contains(&name);
        }
        boundary.module_must_be_absent && format!("{module}.{name}") == boundary.module
    })
}

fn retained_tracking_module_is_pure(
    root: Node<'_>,
    source: &str,
    allowed_functions: &[&str],
) -> bool {
    let mut cursor = root.walk();
    for (index, child) in root.named_children(&mut cursor).enumerate() {
        if child.kind() == "function_definition"
            && child
                .child_by_field_name("name")
                .and_then(|name| node_text(name, source))
                .is_some_and(|name| allowed_functions.contains(&name))
        {
            continue;
        }
        let text = compact_node_text(child, source);
        if (index == 0 && child.kind() == "expression_statement" && text.starts_with(['\'', '"']))
            || (matches!(
                child.kind(),
                "import_from_statement" | "future_import_statement"
            ) && text == "from__future__importannotations")
        {
            continue;
        }
        return false;
    }
    let mut body_is_pure = true;
    walk_named(root, &mut |node| {
        if matches!(
            node.kind(),
            "import_statement" | "import_from_statement" | "future_import_statement"
        ) && compact_node_text(node, source) != "from__future__importannotations"
        {
            body_is_pure = false;
        }
        if node.kind() == "call"
            && let Some(function) = node.child_by_field_name("function")
        {
            let allowed = match function.kind() {
                "identifier" => node_text(function, source)
                    .is_some_and(|name| allowed_functions.contains(&name)),
                "attribute" => function
                    .child_by_field_name("attribute")
                    .and_then(|name| node_text(name, source))
                    .is_some_and(|name| TRACKING_PURE_METHODS.contains(&name)),
                _ => false,
            };
            body_is_pure &= allowed;
        }
    });
    body_is_pure
}

fn parse_python(path: &str, source: &str) -> Result<Tree, LintError> {
    let tree =
        syntax::parse_python(source).map_err(|error| LintError::new(format!("{path}: {error}")))?;
    if tree.root_node().has_error() {
        return Err(LintError::new(format!("{path}: invalid Python syntax")));
    }
    Ok(tree)
}

fn read_python_sources(
    repository: &Repository,
    source_retirement_records: &[&CommandRecord],
    include_runtime_candidates: bool,
) -> Result<Vec<PythonSource>, LintError> {
    let mut sources = Vec::new();
    for path in repository.paths() {
        let path_text = path.as_str();
        if !syntax::is_production_python_path(path_text) {
            continue;
        }
        let source = repository.read_utf8(path)?;
        let module = path_text
            .strip_prefix("python/")
            .and_then(|value| value.strip_suffix(".py"))
            .unwrap_or_default()
            .replace('/', ".")
            .trim_end_matches(".__init__")
            .to_owned();
        let package = if path_text.ends_with("/__init__.py") {
            module.clone()
        } else {
            module
                .rsplit_once('.')
                .map_or_else(String::new, |(parent, _)| parent.to_owned())
        };
        let runtime_candidate = include_runtime_candidates
            && (source.contains("larch_entrypoint") || source.contains("scripts/larch.sh"));
        let source_retirement_candidate =
            source_matches_python_retirement(&module, &source, source_retirement_records);
        let issue_boundary_candidate = issue_python_boundary_candidate(path_text, &source);
        if !runtime_candidate && !source_retirement_candidate && !issue_boundary_candidate {
            continue;
        }
        let tree = repository.python_syntax(path)?;
        if tree.root_node().has_error() {
            return Err(LintError::new(format!(
                "{path_text}: invalid Python syntax"
            )));
        }
        sources.push(PythonSource {
            path: path_text.to_owned(),
            module,
            package,
            source,
            tree,
        });
    }
    Ok(sources)
}

fn source_matches_python_retirement(
    module: &str,
    source: &str,
    retirement_records: &[&CommandRecord],
) -> bool {
    retirement_records
        .iter()
        .any(|record| python_retirement_matches_source(module, source, record))
}

fn completed_python_retirement_records(ledger: &Ledger) -> Vec<&CommandRecord> {
    ledger
        .commands
        .iter()
        .filter(|record| record.python_removal == Completion::Complete)
        .collect()
}

fn retirement_checks<'record>(
    records: impl IntoIterator<Item = &'record CommandRecord>,
) -> Vec<RetirementCheck<'record>> {
    records
        .into_iter()
        .map(|record| RetirementCheck {
            key: record.key(),
            record,
        })
        .collect()
}

fn python_retirement_matches_source(module: &str, source: &str, record: &CommandRecord) -> bool {
    let module_leaf = record
        .python_module
        .rsplit('.')
        .next()
        .unwrap_or(record.python_module.as_str());
    module == record.python_module
        || (source.contains(module_leaf)
            && (source.contains(&record.python_function) || source.contains("import *")))
}

fn validate_python_retirements(
    checks: &[RetirementCheck<'_>],
    python: &BTreeMap<CommandKey, PythonCommand>,
    sources: &[PythonSource],
    findings: &mut Vec<Finding>,
) {
    for check in checks {
        if python.contains_key(&check.key) {
            findings.push(retirement_finding(
                "python-entrypoint-still-present",
                &check.key,
                PYTHON_REGISTRY_PATH,
            ));
        }
    }
    for document in sources {
        let candidates: Vec<_> = checks
            .iter()
            .filter(|check| {
                python_retirement_matches_source(&document.module, &document.source, check.record)
            })
            .collect();
        if candidates.is_empty() {
            continue;
        }
        validate_python_retirement_document(document, &candidates, findings);
    }
}

fn validate_python_retirement_document(
    document: &PythonSource,
    checks: &[&RetirementCheck<'_>],
    findings: &mut Vec<Finding>,
) {
    // Each check passed the legacy source-candidate predicate. Analyze the
    // parsed document as a batch, then project its facts back onto every check.
    let scan = scan_python_imports(document.tree.root_node(), &document.source);
    let mut states = vec![RetirementDocumentState::default(); checks.len()];
    let mut direct_targets: HashMap<String, Vec<usize>> = HashMap::new();
    let mut attribute_targets: HashMap<String, Vec<usize>> = HashMap::new();
    let mut local_call_targets: HashMap<String, Vec<usize>> = HashMap::new();

    for (index, check) in checks.iter().enumerate() {
        let record = check.record;
        if document.module == record.python_module
            && scan
                .top_level_functions
                .contains(&record.python_function.as_str())
        {
            states[index].mark(RetirementDocumentState::DEFINITION_PRESENT);
        }
        let bindings = python_bindings_from_scan(
            &scan,
            &document.package,
            &record.python_module,
            &record.python_function,
        );
        if bindings.imported {
            states[index].mark(RetirementDocumentState::IMPORTED);
        }
        for symbol in bindings.direct_symbols {
            direct_targets.entry(symbol).or_default().push(index);
        }
        for module in bindings.module_aliases {
            attribute_targets
                .entry(format!("{module}.{}", record.python_function))
                .or_default()
                .push(index);
        }
        if document.module == record.python_module {
            local_call_targets
                .entry(record.python_function.clone())
                .or_default()
                .push(index);
        }
    }

    scan_python_symbol_uses(
        document.tree.root_node(),
        &document.source,
        &direct_targets,
        &attribute_targets,
        &local_call_targets,
        &mut states,
    );

    for (check, state) in checks.iter().zip(states) {
        if state.has(RetirementDocumentState::DEFINITION_PRESENT) {
            findings.push(retirement_finding(
                "python-entrypoint-still-present",
                &check.key,
                &document.path,
            ));
        }
        if state.has(RetirementDocumentState::IMPORTED)
            || state.has(RetirementDocumentState::REFERENCED)
        {
            findings.push(retirement_finding(
                "python-entrypoint-still-imported",
                &check.key,
                &document.path,
            ));
        }
        if state.has(RetirementDocumentState::CALLED) {
            findings.push(retirement_finding(
                "python-entrypoint-still-called",
                &check.key,
                &document.path,
            ));
        }
    }
}

fn retirement_finding(token: &str, key: &CommandKey, path: &str) -> Finding {
    finding(format!("{token} {}: {path}", key.selector()))
}

fn scan_python_imports<'source>(
    root: Node<'_>,
    source: &'source str,
) -> PythonDocumentScan<'source> {
    let mut scan = PythonDocumentScan {
        top_level_functions: Vec::new(),
        import_statements: Vec::new(),
        from_import_statements: Vec::new(),
    };
    let mut cursor = root.walk();
    for child in root.named_children(&mut cursor) {
        let definition = if child.kind() == "decorated_definition" {
            child.child_by_field_name("definition")
        } else {
            Some(child)
        };
        if let Some(name) = definition
            .filter(|node| node.kind() == "function_definition")
            .and_then(|node| node.child_by_field_name("name"))
            .and_then(|name| node_text(name, source))
        {
            scan.top_level_functions.push(name);
        }
    }
    walk_named(root, &mut |node| match node.kind() {
        "import_statement" => {
            if let Some(text) = node_text(node, source) {
                scan.import_statements.push(text);
            }
        }
        "import_from_statement" => {
            if let Some(text) = node_text(node, source) {
                scan.from_import_statements.push(text);
            }
        }
        _ => {}
    });
    scan
}

fn scan_python_symbol_uses(
    root: Node<'_>,
    source: &str,
    direct_targets: &HashMap<String, Vec<usize>>,
    attribute_targets: &HashMap<String, Vec<usize>>,
    local_call_targets: &HashMap<String, Vec<usize>>,
    states: &mut [RetirementDocumentState],
) {
    walk_named(root, &mut |node| {
        if node.kind() == "attribute" {
            let attribute = compact_node_text(node, source);
            if let Some(targets) = attribute_targets.get(&attribute) {
                for target in targets {
                    states[*target].mark(RetirementDocumentState::REFERENCED);
                    if is_call_function(node) {
                        states[*target].mark(RetirementDocumentState::CALLED);
                    }
                }
            }
        } else if node.kind() == "identifier"
            && let Some(name) = node_text(node, source)
            && !has_ancestor_kind(node, &["import_statement", "import_from_statement"])
        {
            let called = is_call_function(node);
            if let Some(targets) = direct_targets.get(name) {
                for target in targets {
                    states[*target].mark(RetirementDocumentState::REFERENCED);
                    if called {
                        states[*target].mark(RetirementDocumentState::CALLED);
                    }
                }
            }
            if called && let Some(targets) = local_call_targets.get(name) {
                for target in targets {
                    states[*target].mark(RetirementDocumentState::CALLED);
                }
            }
        }
    });
}

fn is_call_function(node: Node<'_>) -> bool {
    node.parent().is_some_and(|parent| {
        parent.kind() == "call" && parent.child_by_field_name("function") == Some(node)
    })
}

fn python_bindings(
    root: Node<'_>,
    source: &str,
    current_package: &str,
    target_module: &str,
    target_function: &str,
) -> PythonBindings {
    let mut bindings = PythonBindings::default();
    walk_named(root, &mut |node| match node.kind() {
        "import_statement" => inspect_import_statement(
            node_text(node, source).unwrap_or_default(),
            target_module,
            &mut bindings,
        ),
        "import_from_statement" => inspect_from_import(
            node_text(node, source).unwrap_or_default(),
            current_package,
            target_module,
            target_function,
            &mut bindings,
        ),
        _ => {}
    });
    bindings
}

fn python_bindings_from_scan(
    scan: &PythonDocumentScan<'_>,
    current_package: &str,
    target_module: &str,
    target_function: &str,
) -> PythonBindings {
    let mut bindings = PythonBindings::default();
    for statement in &scan.import_statements {
        inspect_import_statement(statement, target_module, &mut bindings);
    }
    for statement in &scan.from_import_statements {
        inspect_from_import(
            statement,
            current_package,
            target_module,
            target_function,
            &mut bindings,
        );
    }
    bindings
}

fn inspect_import_statement(text: &str, target_module: &str, bindings: &mut PythonBindings) {
    let Some(body) = text.trim().strip_prefix("import ") else {
        return;
    };
    for item in body.split(',') {
        let mut parts = item.split_whitespace();
        let name = parts.next().unwrap_or_default();
        if name != target_module
            && !target_module
                .strip_prefix(name)
                .is_some_and(|suffix| suffix.starts_with('.'))
        {
            continue;
        }
        let alias = match (parts.next(), parts.next()) {
            (Some("as"), Some(alias)) => alias,
            _ => name,
        };
        let suffix = target_module.strip_prefix(name).unwrap_or_default();
        let _ = bindings.module_aliases.insert(format!("{alias}{suffix}"));
    }
}

fn inspect_from_import(
    text: &str,
    current_package: &str,
    target_module: &str,
    target_function: &str,
    bindings: &mut PythonBindings,
) {
    let flattened = text.replace(['\n', '\r', '(', ')'], " ");
    let Some(body) = flattened.trim().strip_prefix("from ") else {
        return;
    };
    let Some((raw_module, imports)) = body.split_once(" import ") else {
        return;
    };
    let module = resolve_import_module(current_package, raw_module.trim());
    for item in imports.split(',') {
        let mut parts = item.split_whitespace();
        let name = parts.next().unwrap_or_default();
        let alias = match (parts.next(), parts.next()) {
            (Some("as"), Some(alias)) => alias,
            _ => name,
        };
        if module == target_module && (name == target_function || name == "*") {
            bindings.imported = true;
            let _ = bindings.direct_symbols.insert(if name == "*" {
                target_function.to_owned()
            } else {
                alias.to_owned()
            });
        }
        let imported_module = format!("{module}.{name}");
        if imported_module == target_module
            || target_module
                .strip_prefix(&imported_module)
                .is_some_and(|suffix| suffix.starts_with('.'))
        {
            let suffix = target_module
                .strip_prefix(&imported_module)
                .unwrap_or_default();
            let _ = bindings.module_aliases.insert(format!("{alias}{suffix}"));
        }
    }
}

fn resolve_import_module(current_package: &str, imported: &str) -> String {
    let dots = imported.bytes().take_while(|byte| *byte == b'.').count();
    if dots == 0 {
        return imported.to_owned();
    }
    let mut parts: Vec<&str> = current_package
        .split('.')
        .filter(|part| !part.is_empty())
        .collect();
    for _ in 1..dots {
        let _ = parts.pop();
    }
    let suffix = &imported[dots..];
    if !suffix.is_empty() {
        parts.push(suffix);
    }
    parts.join(".")
}

fn has_ancestor_kind(mut node: Node<'_>, kinds: &[&str]) -> bool {
    while let Some(parent) = node.parent() {
        if kinds.contains(&parent.kind()) {
            return true;
        }
        node = parent;
    }
    false
}

fn extract_python_rust_selectors(path: &str, source: &str) -> Result<Vec<String>, LintError> {
    let tree = parse_python(path, source)?;
    Ok(extract_python_rust_selectors_from_tree(
        tree.root_node(),
        source,
    ))
}

fn extract_python_rust_selectors_from_tree(root: Node<'_>, source: &str) -> Vec<String> {
    let resolver_bindings = python_bindings(
        root,
        source,
        "",
        "larch.core.repo_roots",
        "larch_entrypoint",
    );
    let mut entrypoint_variables = BTreeSet::new();
    walk_named(root, &mut |node| {
        if node.kind() != "assignment" {
            return;
        }
        let Some(left) = node.child_by_field_name("left") else {
            return;
        };
        let Some(right) = node.child_by_field_name("right") else {
            return;
        };
        if left.kind() == "identifier"
            && contains_entrypoint(right, source, &resolver_bindings, &BTreeSet::new())
            && let Some(name) = node_text(left, source)
        {
            let _ = entrypoint_variables.insert(name.to_owned());
        }
    });
    let mut selectors = BTreeSet::new();
    walk_named(root, &mut |node| {
        if !matches!(node.kind(), "list" | "tuple") {
            return;
        }
        let mut cursor = node.walk();
        let elements: Vec<Node<'_>> = node.named_children(&mut cursor).collect();
        let Some(executable) = elements.first() else {
            return;
        };
        if !contains_entrypoint(
            *executable,
            source,
            &resolver_bindings,
            &entrypoint_variables,
        ) && !is_larch_script_literal(*executable, source)
        {
            return;
        }
        let Some(domain) = elements
            .get(1)
            .and_then(|node| python_string(*node, source))
        else {
            return;
        };
        if !valid_token(&domain) {
            return;
        }
        let selector = elements
            .get(2)
            .and_then(|node| python_string(*node, source))
            .filter(|verb| valid_token(verb))
            .map_or_else(|| format!("{domain} *"), |verb| format!("{domain} {verb}"));
        let _ = selectors.insert(selector);
    });
    selectors.into_iter().collect()
}

fn contains_entrypoint(
    root: Node<'_>,
    source: &str,
    bindings: &PythonBindings,
    variables: &BTreeSet<String>,
) -> bool {
    let mut found = false;
    walk_named(root, &mut |node| {
        if found {
            return;
        }
        if node.kind() == "identifier"
            && node_text(node, source).is_some_and(|name| variables.contains(name))
        {
            found = true;
            return;
        }
        if node.kind() != "call" {
            return;
        }
        let Some(function) = node.child_by_field_name("function") else {
            return;
        };
        if function.kind() == "identifier"
            && node_text(function, source)
                .is_some_and(|name| bindings.direct_symbols.contains(name))
        {
            found = true;
        } else if function.kind() == "attribute" {
            let text = compact_node_text(function, source);
            if bindings
                .module_aliases
                .iter()
                .any(|module| text == format!("{module}.larch_entrypoint"))
            {
                found = true;
            }
        }
    });
    found
}

fn is_larch_script_literal(node: Node<'_>, source: &str) -> bool {
    python_string(node, source)
        .is_some_and(|value| value == "scripts/larch.sh" || value.ends_with("/scripts/larch.sh"))
}

fn python_string(node: Node<'_>, source: &str) -> Option<String> {
    if node.kind() != "string" {
        return None;
    }
    let text = node_text(node, source)?.trim();
    let quote = text.find(['\'', '"'])?;
    let literal = &text[quote..];
    let delimiter = literal.chars().next()?;
    if literal.starts_with(&delimiter.to_string().repeat(3)) || !literal.ends_with(delimiter) {
        return None;
    }
    Some(literal[delimiter.len_utf8()..literal.len() - delimiter.len_utf8()].to_owned())
}

fn compact_node_text(node: Node<'_>, source: &str) -> String {
    compact_text(node_text(node, source).unwrap_or_default())
}

fn compact_text(text: &str) -> String {
    text.chars()
        .filter(|character| !character.is_whitespace())
        .collect()
}

fn node_text<'source>(node: Node<'_>, source: &'source str) -> Option<&'source str> {
    source.get(node.byte_range())
}

fn walk_named(node: Node<'_>, visit: &mut impl FnMut(Node<'_>)) {
    visit(node);
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        walk_named(child, visit);
    }
}

#[derive(Clone, Debug)]
struct VariableBinding {
    name: String,
    prefix_domain: Option<String>,
}

fn extract_selectors(content: &str, marker: &str) -> Vec<String> {
    let normalized = content.replace("\\\r\n", " ").replace("\\\n", " ");
    let mut selectors = BTreeSet::new();
    let mut bindings = Vec::new();
    for line in normalized.lines() {
        if marker == "python/cli.py" && is_legacy_generated_header(line) {
            continue;
        }
        let mut search_start = 0;
        while let Some(relative_index) = line[search_start..].find(marker) {
            let marker_index = search_start + relative_index;
            let after = &line[marker_index + marker.len()..];
            let words = literal_words(after);
            if let Some(domain) = words.first().filter(|word| valid_token(word)) {
                if let Some(verb) = words.get(1).filter(|word| valid_token(word)) {
                    let _ = selectors.insert(format!("{domain} {verb}"));
                } else if line.contains("python3") || line.contains("=(") {
                    let _ = selectors.insert(format!("{domain} *"));
                }
            }
            if let Some(binding) = variable_binding(line, marker_index, words.first()) {
                bindings.push(binding);
            }
            search_start = marker_index + marker.len();
        }
    }
    for binding in bindings {
        for line in normalized.lines() {
            if binding.prefix_domain.is_none() && !line.contains("python3") {
                continue;
            }
            let Some(after) = after_variable_reference(line, &binding.name) else {
                continue;
            };
            let words = literal_words(after);
            if let Some(domain) = &binding.prefix_domain {
                match words.first().filter(|word| valid_token(word)) {
                    Some(verb) => {
                        let _ = selectors.insert(format!("{domain} {verb}"));
                    }
                    None => {
                        let _ = selectors.insert(format!("{domain} *"));
                    }
                }
            } else if let Some(domain) = words.first().filter(|word| valid_token(word)) {
                match words.get(1).filter(|word| valid_token(word)) {
                    Some(verb) => {
                        let _ = selectors.insert(format!("{domain} {verb}"));
                    }
                    None => {
                        let _ = selectors.insert(format!("{domain} *"));
                    }
                }
            }
        }
    }
    selectors.into_iter().collect()
}

fn is_legacy_generated_header(line: &str) -> bool {
    const PREFIX: &str = "<!-- AUTO-GENERATED:";
    const MARKER: &str = "Regenerate via: python3 python/cli.py generate ";
    const SUFFIX: &str = " -->";

    let line = line.trim();
    let Some(verb) = line
        .strip_prefix(PREFIX)
        .and_then(|value| {
            value
                .find(MARKER)
                .map(|offset| &value[offset + MARKER.len()..])
        })
        .and_then(|value| value.strip_suffix(SUFFIX))
    else {
        return false;
    };
    valid_token(verb)
}

fn literal_words(text: &str) -> Vec<String> {
    let mut words = Vec::new();
    let bytes = text.as_bytes();
    let mut index = 0;
    while words.len() < 2 {
        while index < bytes.len() && matches!(bytes[index], b' ' | b'\t' | b'"' | b'\'' | b'`') {
            index += 1;
        }
        if index >= bytes.len()
            || !(bytes[index].is_ascii_lowercase() || bytes[index].is_ascii_digit())
        {
            break;
        }
        let start = index;
        index += 1;
        while index < bytes.len()
            && (bytes[index].is_ascii_lowercase()
                || bytes[index].is_ascii_digit()
                || bytes[index] == b'-')
        {
            index += 1;
        }
        words.push(text[start..index].to_owned());
    }
    words
}

fn variable_binding(
    line: &str,
    marker_index: usize,
    first_word: Option<&String>,
) -> Option<VariableBinding> {
    let equals = line[..marker_index].rfind('=')?;
    let assignment_body = &line[equals + 1..marker_index];
    if first_word.is_some()
        && (!assignment_body.trim_start().starts_with("(python3")
            || assignment_body.trim_start().starts_with("$("))
    {
        return None;
    }
    let before = line[..equals]
        .trim_end_matches(|character: char| character.is_ascii_whitespace() || character == '(');
    let start = before
        .rfind(|character: char| !(character.is_ascii_alphanumeric() || character == '_'))
        .map_or(0, |index| index + 1);
    let name = &before[start..];
    if name.is_empty()
        || !name
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_')
    {
        return None;
    }
    Some(VariableBinding {
        name: name.to_owned(),
        prefix_domain: first_word.filter(|word| valid_token(word)).cloned(),
    })
}

fn after_variable_reference<'content>(line: &'content str, name: &str) -> Option<&'content str> {
    let plain = ["$", name].concat();
    let braced = ["$", "{", name, "}"].concat();
    for needle in [plain, braced] {
        if let Some(index) = line.find(&needle) {
            return Some(&line[index + needle.len()..]);
        }
    }
    None
}

/// Refresh imported Python metadata and production caller rows.
///
/// Existing ownership, status, and issue fields are preserved. The supplied
/// planning issue is assigned only to command pairs not already present in the
/// ledger; their exact migration leaf remains unassigned.
///
/// # Errors
///
/// Returns an error when source discovery, ledger parsing, or the atomic write fails.
pub fn sync_command_registry(
    repository: &Repository,
    planning_issue: u64,
) -> Result<String, LintError> {
    let python = read_python_registry(repository)?;
    let existing = if repository
        .paths()
        .iter()
        .any(|path| path.as_str() == LEDGER_PATH)
    {
        Some(read_ledger(repository)?)
    } else {
        None
    };
    if let Some(ledger) = &existing {
        let _ = command_map(ledger)?;
        let _ = caller_map(&ledger.callers)?;
    }
    let mut commands: BTreeMap<CommandKey, CommandRecord> = existing
        .as_ref()
        .map(|ledger| {
            ledger
                .commands
                .iter()
                .cloned()
                .map(|record| (record.key(), record))
                .collect()
        })
        .unwrap_or_default();
    for (key, source) in &python {
        let record = commands
            .entry(key.clone())
            .or_insert_with(|| CommandRecord {
                domain: key.domain.clone(),
                verb: key.verb.clone(),
                python_module: source.module.clone(),
                python_function: source.function.clone(),
                machine_stdout: source.machine_stdout,
                owner: Owner::Python,
                implementation_parity: Parity::Pending,
                consumer_cutover: Completion::Pending,
                python_removal: Completion::Pending,
                planning_issue,
                migration_issue: None,
                clean_install_test: None,
            });
        record.python_module.clone_from(&source.module);
        record.python_function.clone_from(&source.function);
        record.machine_stdout = source.machine_stdout;
    }
    let known = commands.keys().cloned().collect();
    let ledger = Ledger {
        schema_version: SCHEMA_VERSION,
        commands: commands.into_values().collect(),
        callers: discover_callers(repository, &known, None)?,
    };
    command_map(&ledger)?;
    let rendered = render_ledger(&ledger);
    atomic_write(repository.root(), LEDGER_PATH, rendered.as_bytes())?;
    Ok(format!(
        "COMMAND_REGISTRY_STATUS=synced\nCOMMANDS={}\nCALLERS={}\n",
        ledger.commands.len(),
        ledger.callers.len()
    ))
}

fn atomic_write(root: &Path, relative: &str, content: &[u8]) -> Result<(), LintError> {
    let target = root.join(relative);
    let parent = target.parent().ok_or_else(|| {
        LintError::new(format!("{relative}: canonical ledger path has no parent"))
    })?;
    fs::create_dir_all(parent)
        .map_err(|error| LintError::new(format!("{relative}: cannot create parent: {error}")))?;
    let temporary = parent.join(format!(".command-registry.toml.{}.tmp", process::id()));
    let result = (|| {
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temporary)
            .map_err(|error| {
                LintError::new(format!("{relative}: cannot create temporary file: {error}"))
            })?;
        file.write_all(content)
            .and_then(|()| file.sync_all())
            .map_err(|error| {
                LintError::new(format!("{relative}: cannot write temporary file: {error}"))
            })?;
        fs::rename(&temporary, &target)
            .map_err(|error| LintError::new(format!("{relative}: cannot replace ledger: {error}")))
    })();
    if result.is_err() {
        let _ = fs::remove_file(&temporary);
    }
    result
}

fn render_ledger(ledger: &Ledger) -> String {
    let mut output = format!("schema_version = {}\n", ledger.schema_version);
    for command in &ledger.commands {
        output.push_str("\n[[commands]]\n");
        let _ = writeln!(output, "domain = {:?}", command.domain);
        let _ = writeln!(output, "verb = {:?}", command.verb);
        let _ = writeln!(output, "python_module = {:?}", command.python_module);
        let _ = writeln!(output, "python_function = {:?}", command.python_function);
        let _ = writeln!(output, "machine_stdout = {}", command.machine_stdout);
        let _ = writeln!(output, "owner = {:?}", command.owner.as_str());
        let _ = writeln!(
            output,
            "implementation_parity = {:?}",
            command.implementation_parity.as_str()
        );
        let _ = writeln!(
            output,
            "consumer_cutover = {:?}",
            command.consumer_cutover.as_str()
        );
        let _ = writeln!(
            output,
            "python_removal = {:?}",
            command.python_removal.as_str()
        );
        let _ = writeln!(output, "planning_issue = {}", command.planning_issue);
        if let Some(issue) = command.migration_issue {
            let _ = writeln!(output, "migration_issue = {issue}");
        }
        if let Some(fixture) = &command.clean_install_test {
            let _ = writeln!(output, "clean_install_test = {fixture:?}");
        }
    }
    for caller in &ledger.callers {
        output.push_str("\n[[callers]]\n");
        let _ = writeln!(output, "path = {:?}", caller.path);
        let _ = writeln!(output, "kind = {:?}", caller.kind.as_str());
        let _ = writeln!(output, "python = {}", render_array(&caller.python));
        let _ = writeln!(output, "rust = {}", render_array(&caller.rust));
    }
    output
}

fn render_array(values: &[String]) -> String {
    format!(
        "[{}]",
        values
            .iter()
            .map(|value| format!("{value:?}"))
            .collect::<Vec<_>>()
            .join(", ")
    )
}

/// Compare canonical issue command evidence with registry migration ownership.
///
/// # Errors
///
/// Returns an error when the audit input or command registry is malformed.
pub fn audit_migration_issue_commands(
    repository: &Repository,
    input_path: &Path,
) -> Result<RuleOutput, LintError> {
    let content = fs::read_to_string(input_path).map_err(|error| {
        LintError::new(format!(
            "{}: cannot read migration issue audit input: {error}",
            input_path.display()
        ))
    })?;
    audit_migration_issue_commands_content(repository, &content)
        .map_err(|error| LintError::new(format!("{}: {error}", input_path.display())))
}

/// Compare rendered migration-issue command evidence with the ledger.
///
/// The in-process migration-audit adapter owns its private snapshot bytes, so
/// this content entry point avoids reopening a temporary path merely to hand
/// data between two Rust owners.
///
/// # Errors
///
/// Returns an error when the supplied audit JSON or command registry is malformed.
pub fn audit_migration_issue_commands_content(
    repository: &Repository,
    content: &str,
) -> Result<RuleOutput, LintError> {
    let input: MigrationIssueAuditInput = serde_json::from_str(content)
        .map_err(|error| LintError::new(format!("invalid migration issue audit JSON: {error}",)))?;
    if input.schema_version != 1 {
        return Err(LintError::new(format!(
            "unsupported schema_version {}; expected 1",
            input.schema_version
        )));
    }
    let ledger = read_ledger(repository)?;
    let commands = command_map(&ledger)?;
    let mut issues = BTreeMap::new();
    for issue in &input.issues {
        if issue.number == 0 || issues.insert(issue.number, issue).is_some() {
            return Err(LintError::new("issue numbers must be positive and unique"));
        }
        if let Some(command) = &issue.command {
            validate_token("audit command domain", &command.domain)?;
            validate_token("audit command verb", &command.verb)?;
        }
        let mut previous = None;
        for command in &issue.plan_commands {
            validate_token("plan command domain", &command.domain)?;
            validate_token("plan command verb", &command.verb)?;
            if previous.is_some_and(|value| value >= command) {
                return Err(LintError::new(format!(
                    "issue #{} plan_commands must be sorted and unique",
                    issue.number
                )));
            }
            previous = Some(command);
        }
    }

    let mut findings = BTreeSet::new();
    for issue in &input.issues {
        if let Some(command) = &issue.command {
            let key = command.key();
            let registry_matches = commands
                .get(&key)
                .is_some_and(|record| record.migration_issue == Some(issue.number));
            let plan_mentions = issue.plan_commands.binary_search(command).is_ok();
            if !registry_matches || !plan_mentions {
                let _ = findings.insert(migration_issue_drift(issue.number, &key));
            }
        }
    }
    if input.rollout_enabled {
        for (key, record) in &commands {
            let Some(migration_issue) = record.migration_issue else {
                continue;
            };
            let Some(issue) = issues.get(&migration_issue) else {
                continue;
            };
            if issue.state != IssueState::Open || !issue.executable_leaf {
                continue;
            }
            if issue.command.as_ref().map(CommandKeyRecord::key).as_ref() != Some(key) {
                let _ = findings.insert(migration_issue_drift(issue.number, key));
            }
        }
    }
    Ok(RuleOutput::from_findings(findings.into_iter().collect()))
}

fn migration_issue_drift(issue: u64, key: &CommandKey) -> Finding {
    finding(format!(
        "migration-issue-command-drift issue=#{issue} command={}",
        key.selector()
    ))
}

/// Render deterministic Markdown progress data for the Chief migration issue.
///
/// # Errors
///
/// Returns an error when the canonical ledger is absent or invalid.
pub fn render_command_progress(repository: &Repository) -> Result<String, LintError> {
    let ledger = read_ledger(repository)?;
    let python = read_python_registry(repository)?;
    let known = ledger.commands.iter().map(CommandRecord::key).collect();
    let retirement_records = completed_python_retirement_records(&ledger);
    let python_sources = read_python_sources(repository, &retirement_records, true)?;
    let live_callers = discover_callers(repository, &known, Some(&python_sources))?;
    let clean_install_cases = read_clean_install_cases(repository)?;
    let validation = validate_ledger(
        &ledger,
        &python,
        &live_callers,
        &python_sources,
        &clean_install_cases,
    )?;
    if let Some(finding) = validation.findings().first() {
        return Err(LintError::new(format!(
            "cannot render progress from an invalid command registry: {finding}"
        )));
    }
    let commands = command_map(&ledger)?;
    let total = commands.len();
    let rust_owned = commands
        .values()
        .filter(|record| record.owner == Owner::Rust)
        .count();
    let retired = commands
        .values()
        .filter(|record| record.owner == Owner::Retired)
        .count();
    let parity = commands
        .values()
        .filter(|record| record.implementation_parity == Parity::Complete)
        .count();
    let cutover = commands
        .values()
        .filter(|record| record.consumer_cutover == Completion::Complete)
        .count();
    let removed = commands
        .values()
        .filter(|record| record.python_removal == Completion::Complete)
        .count();
    let machine_stdout = commands
        .values()
        .filter(|record| record.machine_stdout)
        .count();
    let exact_leaf_assignments = commands
        .values()
        .filter(|record| record.migration_issue.is_some())
        .count();
    let mut by_issue: BTreeMap<u64, (usize, usize, usize)> = BTreeMap::new();
    for record in commands.values() {
        let row = by_issue.entry(record.planning_issue).or_default();
        row.0 += 1;
        row.1 += usize::from(record.owner == Owner::Rust);
        row.2 += usize::from(record.owner == Owner::Retired);
    }
    let mut output = format!(
        "## Rust command migration progress\n\n| Metric | Complete | Total |\n| --- | ---: | ---: |\n| Rust ownership | {rust_owned} | {total} |\n| Implementation parity | {parity} | {total} |\n| Consumer cutover | {cutover} | {total} |\n| Python removal | {removed} | {total} |\n| Retired commands | {retired} | {total} |\n| Exact migration-leaf assignments | {exact_leaf_assignments} | {total} |\n\nMachine-stdout commands: {machine_stdout}. Production caller paths: {}.\n\n| Planning issue | Commands | Rust-owned | Retired |\n| --- | ---: | ---: | ---: |\n",
        ledger.callers.len()
    );
    for (issue, (count, issue_rust, issue_retired)) in by_issue {
        let _ = writeln!(
            output,
            "| #{issue} | {count} | {issue_rust} | {issue_retired} |"
        );
    }
    Ok(output)
}

#[cfg(test)]
mod tests {
    use super::{planning_issue_closure_findings, python_cli_selectors};
    use crate::{GitCli, Repository};
    use std::path::PathBuf;

    fn workspace_root() -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .ancestors()
            .nth(2)
            .expect("workspace root")
            .to_path_buf()
    }

    #[test]
    fn frozen_generated_headers_are_provenance_not_python_callers() {
        let content = "<!-- AUTO-GENERATED: Derived from agents/_implementer-base.md. Regenerate via: python3 python/cli.py generate codex-implementer -->\n<!-- AUTO-GENERATED: Regenerate via: python3 python/cli.py generate code-reviewer-agent -->\npython3 python/cli.py generate check\n";

        assert_eq!(python_cli_selectors(content), vec!["generate check"]);
    }

    #[test]
    fn planning_issue_7685_closure_is_proven_by_the_live_registry_and_callers() {
        let root = workspace_root();
        let repository = Repository::discover(&GitCli, &root).expect("repository");

        assert!(
            planning_issue_closure_findings(&repository, 7685)
                .expect("closure proof")
                .is_empty()
        );
    }
}

crate::register_rule!(METADATA, RULE);
