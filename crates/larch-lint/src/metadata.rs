use std::collections::{BTreeMap, BTreeSet};

use serde::Deserialize;

use crate::{LintError, Repository, Rule, RuleRegistry};

const MIGRATION_LEDGER_PREFIX: &str = "crates/larch-lint/migration-ledger/";
const MIGRATION_LEDGER_SUFFIX: &str = ".toml";

/// Static rule facts owned beside a rule implementation.
#[derive(Debug)]
pub struct RuleMetadata {
    name: &'static str,
    description: &'static str,
    migration_ledger: &'static str,
}

impl RuleMetadata {
    /// Construct metadata for one independently maintained rule.
    #[must_use]
    pub const fn new(
        name: &'static str,
        description: &'static str,
        migration_ledger: &'static str,
    ) -> Self {
        Self {
            name,
            description,
            migration_ledger,
        }
    }

    /// Return the stable rule name.
    #[must_use]
    pub const fn name(&self) -> &'static str {
        self.name
    }

    /// Return the stable human-facing description.
    #[must_use]
    pub const fn description(&self) -> &'static str {
        self.description
    }

    /// Return the tracked per-rule migration-ledger path.
    #[must_use]
    pub const fn migration_ledger(&self) -> &'static str {
        self.migration_ledger
    }
}

/// A distributed registration that binds one rule to its metadata.
pub struct RuleRegistration {
    metadata: &'static RuleMetadata,
    rule: &'static dyn Rule,
}

impl RuleRegistration {
    /// Construct one inventory entry.
    #[must_use]
    pub const fn new(metadata: &'static RuleMetadata, rule: &'static dyn Rule) -> Self {
        Self { metadata, rule }
    }

    /// Return the registration's immutable metadata.
    #[must_use]
    pub const fn metadata(&self) -> &'static RuleMetadata {
        self.metadata
    }

    /// Return the registered rule.
    #[must_use]
    pub const fn rule(&self) -> &'static dyn Rule {
        self.rule
    }
}

inventory::collect!(RuleRegistration);

/// Build the deterministic registry from every linked, distributed rule.
///
/// # Errors
///
/// Returns an error for missing metadata, mismatched rule facts, duplicate
/// registrations, or invalid rule names.
pub fn registered_rule_registry() -> Result<RuleRegistry<'static>, LintError> {
    registry_from_registrations(inventory::iter::<RuleRegistration>)
}

fn registry_from_registrations(
    registrations: impl IntoIterator<Item = &'static RuleRegistration>,
) -> Result<RuleRegistry<'static>, LintError> {
    let registrations: Vec<&RuleRegistration> = registrations.into_iter().collect();
    let mut rules = Vec::with_capacity(registrations.len());
    for registration in registrations {
        let metadata = registration.metadata();
        let rule = registration.rule();
        if metadata.name() != rule.name() {
            return Err(LintError::new(format!(
                "registered metadata name {} does not match rule name {}",
                metadata.name(),
                rule.name()
            )));
        }
        if metadata.description() != rule.description() {
            return Err(LintError::new(format!(
                "registered metadata description for {} does not match the rule",
                metadata.name()
            )));
        }
        rules.push(rule);
    }
    RuleRegistry::from_static(rules)
}

/// Validate the tracked, one-file-per-rule migration ledger.
///
/// # Errors
///
/// Returns an error for missing, duplicate, malformed, or stale ledger records.
pub fn validate_migration_ledger(
    repository: &Repository,
    registry: &RuleRegistry<'_>,
) -> Result<(), LintError> {
    let expected: BTreeMap<&str, &str> = inventory::iter::<RuleRegistration>
        .into_iter()
        .map(|registration| {
            let metadata = registration.metadata();
            (metadata.name(), metadata.migration_ledger())
        })
        .collect();
    if expected.len() != registry.iter().count() {
        return Err(LintError::new(
            "registered rule metadata does not match the rule registry",
        ));
    }
    let actual_paths: BTreeSet<&str> = repository
        .paths()
        .iter()
        .map(crate::RepoPath::as_str)
        .filter(|path| {
            path.starts_with(MIGRATION_LEDGER_PREFIX) && path.ends_with(MIGRATION_LEDGER_SUFFIX)
        })
        .collect();
    let expected_paths: BTreeSet<&str> = expected.values().copied().collect();

    if let Some(path) = expected_paths.difference(&actual_paths).next() {
        return Err(LintError::new(format!(
            "missing migration-ledger record: {path}"
        )));
    }
    let mut records = Vec::with_capacity(actual_paths.len());
    for path in &actual_paths {
        let content = repository.read_utf8(&crate::RepoPath::from_trusted(path))?;
        let rule_name = parse_ledger_rule(path, &content)?;
        records.push((*path, rule_name));
    }

    let mut recorded = BTreeSet::new();
    for (_, rule_name) in &records {
        if !recorded.insert(rule_name) {
            return Err(LintError::new(format!(
                "duplicate migration-ledger rule record: {rule_name}"
            )));
        }
    }
    for (path, rule_name) in records {
        let expected_path = expected.get(rule_name.as_str()).ok_or_else(|| {
            LintError::new(format!("stale migration-ledger rule record: {rule_name}"))
        })?;
        let canonical_path = ledger_path_for_rule(&rule_name);
        if *expected_path != canonical_path {
            return Err(LintError::new(format!(
                "metadata for {rule_name} must name {canonical_path}"
            )));
        }
        if *expected_path != path {
            return Err(LintError::new(format!(
                "migration-ledger record {path} must be named {expected_path}"
            )));
        }
    }
    if let Some(path) = actual_paths.difference(&expected_paths).next() {
        return Err(LintError::new(format!(
            "stale migration-ledger record: {path}"
        )));
    }
    Ok(())
}

fn ledger_path_for_rule(name: &str) -> String {
    format!("{MIGRATION_LEDGER_PREFIX}{name}{MIGRATION_LEDGER_SUFFIX}")
}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct GrandfatheredFinding {
    pub path: String,
    pub function: String,
    pub constant: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawLedger {
    rule: String,
    #[serde(default)]
    grandfathered: Vec<RawGrandfatheredFinding>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawGrandfatheredFinding {
    path: String,
    function: String,
    constant: String,
    reason: String,
}

struct ParsedLedger {
    rule: String,
    grandfathered: BTreeSet<GrandfatheredFinding>,
}

fn parse_ledger_rule(path: &str, content: &str) -> Result<String, LintError> {
    Ok(parse_ledger(path, content)?.rule)
}

fn parse_ledger(path: &str, content: &str) -> Result<ParsedLedger, LintError> {
    let raw: RawLedger = toml::from_str(content)
        .map_err(|error| LintError::new(format!("{path}: invalid TOML: {error}")))?;
    let mut grandfathered = BTreeSet::new();
    for row in raw.grandfathered {
        if [&row.path, &row.function, &row.constant, &row.reason]
            .into_iter()
            .any(|value| value.trim().is_empty() || value.contains(['\n', '\r']))
        {
            return Err(LintError::new(format!(
                "{path}: grandfathered rows need single-line path, function, constant, and reason"
            )));
        }
        let finding = GrandfatheredFinding {
            path: row.path,
            function: row.function,
            constant: row.constant,
        };
        if !grandfathered.insert(finding.clone()) {
            return Err(LintError::new(format!(
                "{path}: duplicate grandfathered row for {}::{} {}",
                finding.path, finding.function, finding.constant
            )));
        }
    }
    Ok(ParsedLedger {
        rule: raw.rule,
        grandfathered,
    })
}

pub fn grandfathered_findings(
    repository: &Repository,
    path: &str,
    expected_rule: &str,
) -> Result<BTreeSet<GrandfatheredFinding>, LintError> {
    let content = repository.read_required_utf8(
        &crate::RepoPath::from_trusted(path),
        format!("missing migration-ledger record: {path}"),
    )?;
    let ledger = parse_ledger(path, &content)?;
    if ledger.rule != expected_rule {
        return Err(LintError::new(format!(
            "{path}: rule must be {expected_rule}"
        )));
    }
    Ok(ledger.grandfathered)
}

#[cfg(test)]
mod tests {
    use super::{RuleMetadata, RuleRegistration, registry_from_registrations};
    use crate::{LintError, Repository, Rule, RuleOutput};

    #[derive(Debug)]
    struct DriftRule;

    impl Rule for DriftRule {
        fn name(&self) -> &'static str {
            "actual-rule"
        }

        fn description(&self) -> &'static str {
            "actual rule"
        }

        fn check(&self, _repository: &Repository) -> Result<RuleOutput, LintError> {
            Ok(RuleOutput::clean())
        }
    }

    static DRIFT_METADATA: RuleMetadata = RuleMetadata::new(
        "metadata-rule",
        "actual rule",
        "crates/larch-lint/migration-ledger/metadata-rule.toml",
    );
    static DRIFT_RULE: DriftRule = DriftRule;
    static DRIFT_REGISTRATION: RuleRegistration =
        RuleRegistration::new(&DRIFT_METADATA, &DRIFT_RULE);

    #[test]
    fn registration_drift_is_rejected_before_rules_run() {
        let Err(error) = registry_from_registrations([&DRIFT_REGISTRATION]) else {
            panic!("metadata and rule names unexpectedly agreed");
        };
        assert_eq!(
            error.to_string(),
            "registered metadata name metadata-rule does not match rule name actual-rule"
        );
    }
}
