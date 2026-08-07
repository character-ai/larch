use std::{
    collections::BTreeMap,
    fmt,
    sync::{
        Mutex,
        atomic::{AtomicUsize, Ordering},
    },
    time::Instant,
};

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
    /// Return this outcome as a process status for [`std::process::ExitCode`].
    #[must_use]
    pub const fn as_u8(self) -> u8 {
        self as u8
    }

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

/// Diagnostics for one completed rule that do not fail the command.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct RuleOutput {
    findings: Vec<Finding>,
    warnings: Vec<String>,
    contract_lines: Vec<String>,
}

impl RuleOutput {
    /// Construct a completed rule output.
    #[must_use]
    pub const fn new(findings: Vec<Finding>, warnings: Vec<String>) -> Self {
        Self {
            findings,
            warnings,
            contract_lines: Vec::new(),
        }
    }

    /// Construct an output with machine-readable lines for direct invocation.
    #[must_use]
    pub const fn with_contract(
        findings: Vec<Finding>,
        warnings: Vec<String>,
        contract_lines: Vec<String>,
    ) -> Self {
        Self {
            findings,
            warnings,
            contract_lines,
        }
    }

    /// Construct an output containing only findings.
    #[must_use]
    pub const fn from_findings(findings: Vec<Finding>) -> Self {
        Self::new(findings, Vec::new())
    }

    /// Construct a clean output.
    #[must_use]
    pub const fn clean() -> Self {
        Self {
            findings: Vec::new(),
            warnings: Vec::new(),
            contract_lines: Vec::new(),
        }
    }

    /// Return the rule violations.
    #[must_use]
    pub fn findings(&self) -> &[Finding] {
        &self.findings
    }
}

/// The combined report emitted by one or more rules.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct LintReport {
    findings: Vec<Finding>,
    warnings: Vec<String>,
    contract_lines: Vec<String>,
    rule_timings: Vec<RuleTiming>,
}

impl LintReport {
    /// Return sorted rule violations.
    #[must_use]
    pub fn findings(&self) -> &[Finding] {
        &self.findings
    }

    /// Return sorted non-failing diagnostics.
    #[must_use]
    pub fn warnings(&self) -> &[String] {
        &self.warnings
    }

    /// Return direct-invocation machine-readable lines.
    #[must_use]
    pub fn contract_lines(&self) -> &[String] {
        &self.contract_lines
    }

    /// Return per-rule elapsed times in deterministic rule-name order.
    #[must_use]
    pub fn rule_timings(&self) -> &[RuleTiming] {
        &self.rule_timings
    }
}

/// One completed rule's elapsed time.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RuleTiming {
    name: String,
    milliseconds: u128,
}

impl RuleTiming {
    fn new(name: impl Into<String>, milliseconds: u128) -> Self {
        Self {
            name: name.into(),
            milliseconds,
        }
    }

    /// Return the registered rule name.
    #[must_use]
    pub fn name(&self) -> &str {
        &self.name
    }

    /// Return elapsed wall-clock time in milliseconds.
    #[must_use]
    pub const fn milliseconds(&self) -> u128 {
        self.milliseconds
    }
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
    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError>;
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
                    .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-')
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

const MAX_PARALLEL_RULES: usize = 4;

struct CompletedRule {
    index: usize,
    name: &'static str,
    elapsed_milliseconds: u128,
    result: Result<RuleOutput, LintError>,
}

/// Run rules against a discovered repository and return sorted findings.
///
/// # Errors
///
/// Returns an error when any rule cannot produce a trustworthy result.
pub fn run<'rule>(
    repository: &Repository,
    rules: impl IntoIterator<Item = &'rule dyn Rule>,
) -> Result<LintReport, LintError> {
    let rules: Vec<&dyn Rule> = rules.into_iter().collect();
    let completed = run_rules(repository, &rules);
    let mut report = LintReport::default();
    for completed_rule in completed {
        let output = completed_rule.result?;
        report.findings.extend(output.findings);
        report.warnings.extend(output.warnings);
        report.contract_lines.extend(output.contract_lines);
        report.rule_timings.push(RuleTiming::new(
            completed_rule.name,
            completed_rule.elapsed_milliseconds,
        ));
    }
    report.findings.sort();
    report.findings.dedup();
    report.warnings.sort();
    report.warnings.dedup();
    report
        .rule_timings
        .sort_by(|left, right| left.name.cmp(&right.name));
    Ok(report)
}

fn run_rules(repository: &Repository, rules: &[&dyn Rule]) -> Vec<CompletedRule> {
    let worker_count = rules.len().min(MAX_PARALLEL_RULES);
    if worker_count == 0 {
        return Vec::new();
    }
    let next = AtomicUsize::new(0);
    let completed = Mutex::new(Vec::with_capacity(rules.len()));
    std::thread::scope(|scope| {
        for _ in 0..worker_count {
            scope.spawn(|| {
                loop {
                    let index = next.fetch_add(1, Ordering::Relaxed);
                    let Some(rule) = rules.get(index).copied() else {
                        break;
                    };
                    let started = Instant::now();
                    let result = rule.check(repository);
                    let elapsed_milliseconds = started.elapsed().as_millis();
                    completed
                        .lock()
                        .expect("rule completion lock is not poisoned")
                        .push(CompletedRule {
                            index,
                            name: rule.name(),
                            elapsed_milliseconds,
                            result,
                        });
                }
            });
        }
    });
    let mut completed = completed
        .into_inner()
        .expect("rule completion lock is not poisoned");
    completed.sort_by_key(|completed_rule| completed_rule.index);
    completed
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

/// Print non-failing diagnostics in a stable format.
pub fn render_warnings(
    warnings: &[String],
    output: &mut impl std::io::Write,
) -> Result<(), LintError> {
    for warning in warnings {
        writeln!(output, "warning: {warning}")
            .map_err(|error| LintError::new(format!("cannot write warning: {error}")))?;
    }
    Ok(())
}

/// Print machine-readable direct-invocation contract lines.
///
/// # Errors
///
/// Returns an error when the output stream cannot be written.
pub fn render_contract_lines(
    contract_lines: &[String],
    output: &mut impl std::io::Write,
) -> Result<(), LintError> {
    for line in contract_lines {
        writeln!(output, "{line}")
            .map_err(|error| LintError::new(format!("cannot write contract line: {error}")))?;
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
    use std::path::{Path, PathBuf};

    use super::{Finding, LintError, Rule, RuleOutput, RuleRegistry};
    use crate::repository::{Git, Repository};

    #[derive(Debug)]
    struct FixtureRule;

    impl Rule for FixtureRule {
        fn name(&self) -> &'static str {
            "fixture"
        }

        fn description(&self) -> &'static str {
            "fixture rule"
        }

        fn check(&self, _repository: &Repository) -> Result<RuleOutput, LintError> {
            Ok(RuleOutput::from_findings(vec![
                Finding::new("z.md", 1, "later"),
                Finding::new("a.md", 2, "first"),
            ]))
        }
    }

    #[derive(Debug)]
    struct NamedFixtureRule {
        name: &'static str,
    }

    impl Rule for NamedFixtureRule {
        fn name(&self) -> &'static str {
            self.name
        }

        fn description(&self) -> &'static str {
            "named fixture rule"
        }

        fn check(&self, _repository: &Repository) -> Result<RuleOutput, LintError> {
            Ok(RuleOutput::from_findings(vec![Finding::new(
                format!("{}.md", self.name),
                1,
                self.name,
            )]))
        }
    }

    #[derive(Debug)]
    struct FakeGit {
        root: PathBuf,
    }

    impl Git for FakeGit {
        fn repository_root(&self, _cwd: &Path) -> Result<PathBuf, LintError> {
            Ok(self.root.clone())
        }

        fn tracked_paths(&self, _root: &Path) -> Result<Vec<u8>, LintError> {
            Ok(b"fixture.md\0".to_vec())
        }
    }

    fn fixture_repository() -> Repository {
        let temporary = tempfile::tempdir().expect("tempdir");
        std::fs::write(temporary.path().join("fixture.md"), "fixture\n").expect("write fixture");
        Repository::discover(
            &FakeGit {
                root: temporary.path().to_path_buf(),
            },
            temporary.path(),
        )
        .expect("discover fixture repository")
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

    #[test]
    fn parallel_rule_completion_keeps_report_order_deterministic() {
        let repository = fixture_repository();
        let zulu = NamedFixtureRule { name: "zulu" };
        let alpha = NamedFixtureRule { name: "alpha" };
        let middle = NamedFixtureRule { name: "middle" };

        let report = super::run(&repository, [&zulu as &dyn Rule, &alpha, &middle])
            .expect("run fixture rules");
        let findings: Vec<String> = report.findings().iter().map(ToString::to_string).collect();
        assert_eq!(
            findings,
            [
                "alpha.md:1: alpha",
                "middle.md:1: middle",
                "zulu.md:1: zulu"
            ]
        );
        let timing_names: Vec<&str> = report
            .rule_timings()
            .iter()
            .map(super::RuleTiming::name)
            .collect();
        assert_eq!(timing_names, ["alpha", "middle", "zulu"]);
    }
}
