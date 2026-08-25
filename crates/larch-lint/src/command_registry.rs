//! Canonical Rust command ownership and production-caller registry.

use std::{
    collections::{BTreeMap, BTreeSet},
    fmt::Write as _,
    fs::{self, OpenOptions},
    io::Write as _,
    path::Path,
    process,
    sync::{Arc, LazyLock},
};

use regex::Regex;
use serde::Deserialize;

use crate::{
    Finding, LintError, RepoPath, Repository, Rule, RuleDispatchPriority, RuleMetadata, RuleOutput,
    repository::AnalysisCache,
};

const NAME: &str = "command-registry";
const DESCRIPTION: &str = "Validate Rust command ownership and production caller inventory";
const LEDGER_PATH: &str = "crates/larch-lint/data/command-registry.toml";
const CLEAN_INSTALL_CASES_PATH: &str = "crates/larch-cli/tests/clean_install.rs";
const HOOKS_PATH: &str = "hooks/hooks.json";
const SCHEMA_VERSION: u32 = 3;
const CHIEF_MIGRATION_ISSUE: u64 = 7687;
const MIGRATION_UMBRELLA_ISSUES: std::ops::RangeInclusive<u64> = 7673..=7687;

static HOOK_PATH: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"\$\{CLAUDE_PLUGIN_ROOT\}/(?P<path>[^\"\s]+)"#)
        .expect("hook command path expression is valid")
});
static CLEAN_INSTALL_CASE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r#"CleanInstallCase::new\(\s*\"(?P<id>[a-z0-9-]+)\"\s*,\s*\"(?P<domain>[a-z0-9-]+)\"\s*,\s*\"(?P<verb>[a-z0-9-]+)\"\s*,?\s*\)"#,
    )
    .expect("clean-install case expression is valid")
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

    fn dispatch_priority(&self) -> RuleDispatchPriority {
        RuleDispatchPriority::Early
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let analysis = repository.command_registry_analysis();
        let ledger = analysis.ledger(repository)?;
        let callers = analysis.callers(repository)?;
        let clean_install_cases = analysis.clean_install_cases(repository)?;
        validate_ledger(&ledger, &callers, &clean_install_cases)
    }
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
    machine_stdout: bool,
    owner: Owner,
    planning_issue: u64,
    migration_issue: u64,
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
    Rust,
    Retired,
}

impl Owner {
    const fn as_str(self) -> &'static str {
        match self {
            Self::Rust => "rust",
            Self::Retired => "retired",
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(deny_unknown_fields)]
struct CallerRecord {
    path: String,
    kind: CallerKind,
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
}

impl CallerKind {
    const fn as_str(self) -> &'static str {
        match self {
            Self::Skill => "skill",
            Self::Hook => "hook",
            Self::Script => "script",
            Self::Ci => "ci",
            Self::Agent => "agent",
        }
    }
}

/// Shared immutable command-registry facts for one repository snapshot.
pub struct CommandRegistryAnalysis {
    ledger: AnalysisCache<Ledger>,
    clean_install_cases: AnalysisCache<BTreeMap<String, CommandKey>>,
    caller_inventory: AnalysisCache<Vec<CallerRecord>>,
}

impl CommandRegistryAnalysis {
    pub(crate) const fn new() -> Self {
        Self {
            ledger: AnalysisCache::new(),
            clean_install_cases: AnalysisCache::new(),
            caller_inventory: AnalysisCache::new(),
        }
    }

    fn ledger(&self, repository: &Repository) -> Result<Arc<Ledger>, LintError> {
        self.ledger.get_or_init(|| read_ledger(repository))
    }

    fn clean_install_cases(
        &self,
        repository: &Repository,
    ) -> Result<Arc<BTreeMap<String, CommandKey>>, LintError> {
        self.clean_install_cases
            .get_or_init(|| read_clean_install_cases(repository))
    }

    fn callers(&self, repository: &Repository) -> Result<Arc<Vec<CallerRecord>>, LintError> {
        let ledger = self.ledger(repository)?;
        let known = ledger.commands.iter().map(CommandRecord::key).collect();
        self.caller_inventory
            .get_or_init(|| discover_callers(repository, &known))
    }
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
    parse_ledger(&required_utf8(repository, LEDGER_PATH)?)
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

fn required_utf8(repository: &Repository, path: &str) -> Result<String, LintError> {
    let path = RepoPath::from_trusted(path);
    if repository.paths().binary_search(&path).is_err() {
        return Err(LintError::new(format!("{path}: required file is missing")));
    }
    repository.read_utf8(&path).map(|source| source.to_string())
}

fn validate_ledger(
    ledger: &Ledger,
    live_callers: &[CallerRecord],
    clean_install_cases: &BTreeMap<String, CommandKey>,
) -> Result<RuleOutput, LintError> {
    let commands = command_map(ledger)?;
    validate_clean_install_references(&commands, clean_install_cases)?;
    let callers = caller_map(&ledger.callers)?;
    validate_caller_selectors(&callers, &commands)?;
    let live_callers = caller_map(live_callers)?;
    let mut findings = Vec::new();
    for (key, record) in &commands {
        validate_command_state(key, record, &callers, &mut findings);
        validate_clean_install_coverage(
            key,
            record,
            &live_callers,
            clean_install_cases,
            &mut findings,
        );
    }
    compare_callers(&callers, &live_callers, &mut findings);
    Ok(RuleOutput::from_findings(findings))
}

fn command_map(ledger: &Ledger) -> Result<BTreeMap<CommandKey, &CommandRecord>, LintError> {
    let mut commands = BTreeMap::new();
    for command in &ledger.commands {
        validate_token("domain", &command.domain)?;
        validate_token("verb", &command.verb)?;
        if command.planning_issue == 0 {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}: {} has no responsible planning issue",
                command.key().selector()
            )));
        }
        if command.planning_issue == CHIEF_MIGRATION_ISSUE {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}: {} delegates planning ownership to chief umbrella #{CHIEF_MIGRATION_ISSUE}",
                command.key().selector()
            )));
        }
        if command.migration_issue == 0
            || MIGRATION_UMBRELLA_ISSUES.contains(&command.migration_issue)
        {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}: {} lacks an exact non-umbrella migration leaf",
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
    if record.owner != Owner::Rust || matching_callers(key, callers).is_empty() {
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
        validate_sorted_unique(&caller.path, &caller.rust)?;
    }
    Ok(mapped)
}

fn validate_sorted_unique(path: &str, selectors: &[String]) -> Result<(), LintError> {
    if selectors.windows(2).any(|pair| pair[0] >= pair[1]) {
        return Err(LintError::new(format!(
            "{LEDGER_PATH}: {path} selectors must be sorted and unique"
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
        for selector in &caller.rust {
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
    callers: &BTreeMap<String, &CallerRecord>,
    findings: &mut Vec<Finding>,
) {
    if record.owner == Owner::Retired {
        let callers = matching_callers(key, callers);
        if !callers.is_empty() {
            findings.push(finding(format!(
                "retired command {} has live callers: {}",
                key.selector(),
                callers.join(", ")
            )));
        }
    }
}

fn matching_callers(key: &CommandKey, callers: &BTreeMap<String, &CallerRecord>) -> Vec<String> {
    callers
        .values()
        .filter(|caller| {
            caller
                .rust
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
) -> Result<Vec<CallerRecord>, LintError> {
    let hook_paths = discover_hook_paths(repository)?;
    let mut callers = Vec::new();
    for path in repository.paths() {
        let Some(kind) = classify_caller(path.as_str(), &hook_paths) else {
            continue;
        };
        let content = repository.read_utf8(path)?;
        let mut rust = filter_selectors(extract_selectors(&content, "bin/larch"), known);
        for marker in [
            "scripts/larch.sh",
            "target/release/larch",
            "target/$TARGET/release/larch",
        ] {
            for selector in filter_selectors(extract_selectors(&content, marker), known) {
                if !rust.contains(&selector) {
                    rust.push(selector);
                }
            }
        }
        rust.sort();
        if rust.is_empty() {
            continue;
        }
        callers.push(CallerRecord {
            path: path.as_str().to_owned(),
            kind,
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

#[derive(Clone, Debug)]
struct VariableBinding {
    name: String,
    prefix_domain: Option<String>,
}

fn extract_selectors(content: &str, marker: &str) -> Vec<String> {
    if !content.contains(marker) {
        return Vec::new();
    }
    let normalized = content.replace("\\\r\n", " ").replace("\\\n", " ");
    let mut selectors = BTreeSet::new();
    let mut bindings = Vec::new();
    for line in normalized.lines() {
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

/// Return every command selector the canonical registry recognizes.
///
/// # Errors
///
/// Returns an error when the registry is unavailable, malformed, or contains
/// duplicate selectors.
pub fn command_audit_selectors(
    repository: &Repository,
) -> Result<Vec<CommandAuditSelector>, LintError> {
    let ledger = repository.command_registry_analysis().ledger(repository)?;
    let commands = command_map(&ledger)?;
    Ok(commands
        .keys()
        .map(|key| CommandAuditSelector {
            domain: key.domain.clone(),
            verb: key.verb.clone(),
        })
        .collect())
}

/// Return every selector the registry marks Rust-owned.
pub fn rust_owned_selectors(repository: &Repository) -> Result<BTreeSet<String>, LintError> {
    let ledger = repository.command_registry_analysis().ledger(repository)?;
    Ok(ledger
        .commands
        .iter()
        .filter(|record| record.owner == Owner::Rust)
        .map(|record| record.key().selector())
        .collect())
}

/// Prove that one planning umbrella contains only final Rust-owned commands.
pub fn planning_issue_closure_findings(
    repository: &Repository,
    planning_issue: u64,
) -> Result<Vec<Finding>, LintError> {
    let ledger = repository.command_registry_analysis().ledger(repository)?;
    let mut findings = Vec::new();
    for record in ledger
        .commands
        .iter()
        .filter(|record| record.planning_issue == planning_issue)
    {
        let selector = record.key().selector();
        if record.owner != Owner::Rust {
            findings.push(finding(format!(
                "planning issue #{planning_issue} command {selector} is not Rust-owned"
            )));
        }
        if record.migration_issue == 0
            || MIGRATION_UMBRELLA_ISSUES.contains(&record.migration_issue)
        {
            findings.push(finding(format!(
                "planning issue #{planning_issue} command {selector} lacks an exact non-umbrella migration leaf"
            )));
        }
    }
    findings.sort();
    findings.dedup();
    Ok(findings)
}

/// Return whether the registry has at least one row for one planning issue.
pub fn planning_issue_has_command_rows(
    repository: &Repository,
    planning_issue: u64,
) -> Result<bool, LintError> {
    let ledger = repository.command_registry_analysis().ledger(repository)?;
    Ok(ledger
        .commands
        .iter()
        .any(|record| record.planning_issue == planning_issue))
}

/// Extract selectors that follow a retired `python/cli.py` marker.
pub fn python_cli_selectors(content: &str) -> Vec<String> {
    extract_selectors(content, "python/cli.py")
}

/// Refresh the Rust production-caller inventory while preserving command ownership.
///
/// # Errors
///
/// Returns an error when the registry or caller inventory is invalid, or when
/// the refreshed registry cannot be written atomically.
pub fn sync_command_registry(repository: &Repository) -> Result<String, LintError> {
    let mut ledger = read_ledger(repository)?;
    let _ = command_map(&ledger)?;
    let known = ledger.commands.iter().map(CommandRecord::key).collect();
    ledger.callers = discover_callers(repository, &known)?;
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
        LintError::new(format!("{relative}: canonical registry path has no parent"))
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
        fs::rename(&temporary, &target).map_err(|error| {
            LintError::new(format!("{relative}: cannot replace registry: {error}"))
        })
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
        let _ = writeln!(output, "machine_stdout = {}", command.machine_stdout);
        let _ = writeln!(output, "owner = {:?}", command.owner.as_str());
        let _ = writeln!(output, "planning_issue = {}", command.planning_issue);
        let _ = writeln!(output, "migration_issue = {}", command.migration_issue);
        if let Some(fixture) = &command.clean_install_test {
            let _ = writeln!(output, "clean_install_test = {fixture:?}");
        }
    }
    for caller in &ledger.callers {
        output.push_str("\n[[callers]]\n");
        let _ = writeln!(output, "path = {:?}", caller.path);
        let _ = writeln!(output, "kind = {:?}", caller.kind.as_str());
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

/// Compare canonical issue command evidence with registry ownership.
///
/// # Errors
///
/// Returns an error when the input file cannot be read, its JSON contract is
/// invalid, or the command registry cannot be validated.
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

/// Compare rendered migration-issue command evidence with the registry.
///
/// # Errors
///
/// Returns an error when the JSON contract, issue rows, command selectors, or
/// command registry is invalid.
pub fn audit_migration_issue_commands_content(
    repository: &Repository,
    content: &str,
) -> Result<RuleOutput, LintError> {
    let input: MigrationIssueAuditInput = serde_json::from_str(content)
        .map_err(|error| LintError::new(format!("invalid migration issue audit JSON: {error}")))?;
    if input.schema_version != 1 {
        return Err(LintError::new(format!(
            "unsupported schema_version {}; expected 1",
            input.schema_version
        )));
    }
    let ledger = repository.command_registry_analysis().ledger(repository)?;
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
                .is_some_and(|record| record.migration_issue == issue.number);
            let plan_mentions = issue.plan_commands.binary_search(command).is_ok();
            if !registry_matches || !plan_mentions {
                let _ = findings.insert(migration_issue_drift(issue.number, &key));
            }
        }
    }
    if input.rollout_enabled {
        for (key, record) in &commands {
            let Some(issue) = issues.get(&record.migration_issue) else {
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

/// Render deterministic Markdown summary data for the Rust command registry.
///
/// # Errors
///
/// Returns an error when the registry, caller inventory, or clean-install
/// matrix is unavailable or inconsistent.
pub fn render_command_progress(repository: &Repository) -> Result<String, LintError> {
    let analysis = repository.command_registry_analysis();
    let ledger = analysis.ledger(repository)?;
    let live_callers = analysis.callers(repository)?;
    let clean_install_cases = analysis.clean_install_cases(repository)?;
    let validation = validate_ledger(&ledger, &live_callers, &clean_install_cases)?;
    if let Some(finding) = validation.findings().first() {
        return Err(LintError::new(format!(
            "cannot render summary from an invalid command registry: {finding}"
        )));
    }
    let commands = command_map(&ledger)?;
    let total = commands.len();
    let rust_owned = commands
        .values()
        .filter(|record| record.owner == Owner::Rust)
        .count();
    let retired = total - rust_owned;
    let machine_stdout = commands
        .values()
        .filter(|record| record.machine_stdout)
        .count();
    let mut by_issue: BTreeMap<u64, (usize, usize, usize)> = BTreeMap::new();
    for record in commands.values() {
        let row = by_issue.entry(record.planning_issue).or_default();
        row.0 += 1;
        row.1 += usize::from(record.owner == Owner::Rust);
        row.2 += usize::from(record.owner == Owner::Retired);
    }
    let mut output = format!(
        "## Rust command registry\n\n| Metric | Count |\n| --- | ---: |\n| Registered commands | {total} |\n| Rust-owned commands | {rust_owned} |\n| Retired commands | {retired} |\n| Machine-stdout commands | {machine_stdout} |\n| Production caller paths | {} |\n\n| Planning issue | Commands | Rust-owned | Retired |\n| --- | ---: | ---: | ---: |\n",
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
    use super::{CommandRegistryRule, planning_issue_closure_findings};
    use crate::{GitCli, Repository, Rule};
    use std::{path::PathBuf, sync::Arc};

    fn workspace_root() -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .ancestors()
            .nth(2)
            .expect("workspace root")
            .to_path_buf()
    }

    #[test]
    fn shared_analysis_is_reused_and_rule_output_is_deterministic() {
        let root = workspace_root();
        let repository = Repository::discover(&GitCli, &root).expect("repository");
        let first_callers = repository
            .command_registry_analysis()
            .callers(&repository)
            .expect("first callers");
        let second_callers = repository
            .command_registry_analysis()
            .callers(&repository)
            .expect("second callers");
        assert!(Arc::ptr_eq(&first_callers, &second_callers));

        let first = CommandRegistryRule
            .check(&repository)
            .expect("first command-registry output");
        let second = CommandRegistryRule
            .check(&repository)
            .expect("reused command-registry output");
        assert_eq!(first, second);
        assert!(
            planning_issue_closure_findings(&repository, 7685)
                .expect("closure proof")
                .is_empty()
        );
    }
}

crate::register_rule!(METADATA, RULE);
