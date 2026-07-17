use std::{collections::BTreeMap, fmt};

use crate::repository::Repository;

/// Stable process outcomes for the lint command.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(i32)]
pub enum ExitCode {
    /// No rule reported a violation.
    Clean = 0,
    /// At least one rule reported a violation.
    Findings = 1,
    /// The command could not establish a trustworthy result.
    Error = 2,
}

impl ExitCode {
    /// Return this outcome as a process status.
    #[must_use]
    pub const fn as_i32(self) -> i32 {
        self as i32
    }
}

/// One stable, human-readable rule violation.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct Finding {
    path: String,
    line: u32,
    message: String,
}

impl Finding {
    /// Construct a finding for a repository-relative path and one-based line.
    #[must_use]
    pub fn new(path: impl Into<String>, line: u32, message: impl Into<String>) -> Self {
        Self {
            path: path.into(),
            line,
            message: message.into(),
        }
    }
}

impl fmt::Display for Finding {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}:{}: {}", self.path, self.line, self.message)
    }
}

/// A deterministic failure that prevents a rule result from being trusted.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LintError(String);

impl LintError {
    /// Construct a diagnostic-safe error message.
    #[must_use]
    pub fn new(message: impl Into<String>) -> Self {
        Self(message.into())
    }
}

impl fmt::Display for LintError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.0.fmt(formatter)
    }
}

impl std::error::Error for LintError {}

/// A larch policy rule.
pub trait Rule: Sync {
    /// Return the unique command-line rule name.
    fn name(&self) -> &'static str;

    /// Return a concise user-facing description.
    fn description(&self) -> &'static str;

    /// Check one validated repository snapshot.
    ///
    /// # Errors
    ///
    /// Returns an error when the rule cannot produce a trustworthy result.
    fn check(&self, repository: &Repository) -> Result<Vec<Finding>, LintError>;
}

/// An immutable, name-indexed set of rules.
pub struct RuleRegistry<'rule> {
    rules: BTreeMap<&'static str, &'rule dyn Rule>,
}

impl<'rule> RuleRegistry<'rule> {
    /// Build a registry and reject duplicate or malformed rule names.
    ///
    /// # Errors
    ///
    /// Returns an error when a rule name is malformed or duplicated.
    pub fn new(rules: &'rule [&'rule dyn Rule]) -> Result<Self, LintError> {
        Self::from_rules(rules.iter().copied())
    }

    fn from_rules(rules: impl IntoIterator<Item = &'rule dyn Rule>) -> Result<Self, LintError> {
        let mut registered = BTreeMap::new();
        for rule in rules {
            let name = rule.name();
            if name.is_empty()
                || !name
                    .bytes()
                    .all(|byte| byte.is_ascii_lowercase() || byte == b'-')
            {
                return Err(LintError::new(format!("invalid rule name: {name:?}")));
            }
            if registered.insert(name, rule).is_some() {
                return Err(LintError::new(format!("duplicate rule name: {name}")));
            }
        }
        Ok(Self { rules: registered })
    }

    /// Return the named rule, if it is registered.
    #[must_use]
    pub fn get(&self, name: &str) -> Option<&dyn Rule> {
        self.rules.get(name).copied()
    }

    /// Iterate rules in stable name order.
    pub fn iter(&self) -> impl Iterator<Item = &dyn Rule> {
        self.rules.values().copied()
    }
}

impl RuleRegistry<'static> {
    /// Build a registry from distributed static registrations.
    ///
    /// # Errors
    ///
    /// Returns an error when a rule name is malformed or duplicated.
    pub fn from_static(
        rules: impl IntoIterator<Item = &'static dyn Rule>,
    ) -> Result<Self, LintError> {
        Self::from_rules(rules)
    }
}

/// Run rules against a discovered repository and return sorted findings.
///
/// # Errors
///
/// Returns an error when any rule cannot produce a trustworthy result.
pub fn run<'rule>(
    repository: &Repository,
    rules: impl IntoIterator<Item = &'rule dyn Rule>,
) -> Result<Vec<Finding>, LintError> {
    let mut findings = Vec::new();
    for rule in rules {
        findings.extend(rule.check(repository)?);
    }
    findings.sort();
    findings.dedup();
    Ok(findings)
}

/// Return the process outcome associated with a completed rule run.
#[must_use]
pub const fn finding_exit_code(findings: &[Finding]) -> ExitCode {
    if findings.is_empty() {
        ExitCode::Clean
    } else {
        ExitCode::Findings
    }
}

/// Print findings in the command's stable format.
pub fn render_findings(
    findings: &[Finding],
    output: &mut impl std::io::Write,
) -> Result<(), LintError> {
    for finding in findings {
        writeln!(output, "{finding}")
            .map_err(|error| LintError::new(format!("cannot write finding: {error}")))?;
    }
    Ok(())
}

/// Print a deterministic rule list.
pub fn render_rule_list(
    registry: &RuleRegistry<'_>,
    output: &mut impl std::io::Write,
) -> Result<(), LintError> {
    for rule in registry.iter() {
        writeln!(output, "{}\t{}", rule.name(), rule.description())
            .map_err(|error| LintError::new(format!("cannot write rule list: {error}")))?;
    }
    Ok(())
}

/// Render an error to the command's diagnostic stream.
pub fn render_error(error: &LintError, output: &mut impl std::io::Write) -> ExitCode {
    let _ = writeln!(output, "larch-lint: error: {error}");
    ExitCode::Error
}

#[cfg(test)]
mod tests {
    use super::{Finding, LintError, Rule, RuleRegistry};
    use crate::repository::Repository;

    #[derive(Debug)]
    struct FixtureRule;

    impl Rule for FixtureRule {
        fn name(&self) -> &'static str {
            "fixture"
        }

        fn description(&self) -> &'static str {
            "fixture rule"
        }

        fn check(&self, _repository: &Repository) -> Result<Vec<Finding>, LintError> {
            Ok(vec![
                Finding::new("z.md", 1, "later"),
                Finding::new("a.md", 2, "first"),
            ])
        }
    }

    #[test]
    fn registry_rejects_duplicate_names() {
        let rule = FixtureRule;
        assert!(RuleRegistry::new(&[&rule, &rule]).is_err());
    }

    #[test]
    fn findings_have_the_nonzero_exit_code() {
        assert_eq!(
            super::finding_exit_code(&[Finding::new("a.md", 1, "fixture")]),
            super::ExitCode::Findings
        );
    }
}
