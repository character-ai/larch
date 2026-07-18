//! Canonical Python-to-Rust command ownership and production-caller ledger.

use std::{
    collections::{BTreeMap, BTreeSet},
    fmt::Write as _,
    fs::{self, OpenOptions},
    io::Write as _,
    path::Path,
    process,
    sync::LazyLock,
};

use regex::Regex;
use serde::Deserialize;

use crate::{Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput};

const NAME: &str = "command-registry";
const DESCRIPTION: &str =
    "Validate command ownership, migration state, and production caller inventory";
const LEDGER_PATH: &str = "crates/larch-lint/data/command-registry.toml";
const PYTHON_REGISTRY_PATH: &str = "python/larch/cli.py";
const HOOKS_PATH: &str = "hooks/hooks.json";
const SCHEMA_VERSION: u32 = 1;

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
        let callers = discover_callers(repository, &known)?;
        validate_ledger(&ledger, &python, &callers)
    }
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
    migration_issue: u64,
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
}

impl CallerKind {
    const fn as_str(self) -> &'static str {
        match self {
            Self::Skill => "skill",
            Self::Hook => "hook",
            Self::Script => "script",
            Self::Ci => "ci",
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct PythonCommand {
    module: String,
    function: String,
    machine_stdout: bool,
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
    repository.read_utf8(&path)
}

fn validate_ledger(
    ledger: &Ledger,
    python: &BTreeMap<CommandKey, PythonCommand>,
    live_callers: &[CallerRecord],
) -> Result<RuleOutput, LintError> {
    let commands = command_map(ledger)?;
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
    }
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
        if command.migration_issue == 0 {
            return Err(LintError::new(format!(
                "{LEDGER_PATH}: {} has no responsible migration issue",
                command.key().selector()
            )));
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
        if record.python_removal == Completion::Complete {
            findings.push(finding(format!(
                "{} claims Python removal but remains registered",
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
) -> Result<Vec<CallerRecord>, LintError> {
    let hook_paths = discover_hook_paths(repository)?;
    let mut callers = Vec::new();
    for path in repository.paths() {
        let Some(kind) = classify_caller(path.as_str(), &hook_paths) else {
            continue;
        };
        let content = repository.read_utf8(path)?;
        let python = filter_selectors(extract_selectors(&content, "python/cli.py"), known);
        let rust = filter_selectors(extract_selectors(&content, "bin/larch"), known);
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
/// issue is assigned only to command pairs not already present in the ledger.
///
/// # Errors
///
/// Returns an error when source discovery, ledger parsing, or the atomic write fails.
pub fn sync_command_registry(
    repository: &Repository,
    migration_issue: u64,
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
                migration_issue,
            });
        record.python_module.clone_from(&source.module);
        record.python_function.clone_from(&source.function);
        record.machine_stdout = source.machine_stdout;
    }
    let known = commands.keys().cloned().collect();
    let ledger = Ledger {
        schema_version: SCHEMA_VERSION,
        commands: commands.into_values().collect(),
        callers: discover_callers(repository, &known)?,
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
        let _ = writeln!(output, "migration_issue = {}", command.migration_issue);
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

/// Render deterministic Markdown progress data for the Chief migration issue.
///
/// # Errors
///
/// Returns an error when the canonical ledger is absent or invalid.
pub fn render_command_progress(repository: &Repository) -> Result<String, LintError> {
    let ledger = read_ledger(repository)?;
    let python = read_python_registry(repository)?;
    let known = ledger.commands.iter().map(CommandRecord::key).collect();
    let live_callers = discover_callers(repository, &known)?;
    let validation = validate_ledger(&ledger, &python, &live_callers)?;
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
    let mut by_issue: BTreeMap<u64, (usize, usize, usize)> = BTreeMap::new();
    for record in commands.values() {
        let row = by_issue.entry(record.migration_issue).or_default();
        row.0 += 1;
        row.1 += usize::from(record.owner == Owner::Rust);
        row.2 += usize::from(record.owner == Owner::Retired);
    }
    let mut output = format!(
        "## Rust command migration progress\n\n| Metric | Complete | Total |\n| --- | ---: | ---: |\n| Rust ownership | {rust_owned} | {total} |\n| Implementation parity | {parity} | {total} |\n| Consumer cutover | {cutover} | {total} |\n| Python removal | {removed} | {total} |\n| Retired commands | {retired} | {total} |\n\nMachine-stdout commands: {machine_stdout}. Production caller paths: {}.\n\n| Migration issue | Commands | Rust-owned | Retired |\n| --- | ---: | ---: | ---: |\n",
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

crate::register_rule!(METADATA, RULE);
