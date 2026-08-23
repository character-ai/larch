//! Enforce the closed review-command and Python-package boundary for #7679.

use std::{collections::BTreeMap, path::Path};

use toml::Value;

use crate::{
    Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput, command_registry,
};

use super::python_boundary::RegistryCommand;

const NAME: &str = "review-python-free";
const DESCRIPTION: &str =
    "Enforce final Rust review-command ownership and retirement of the Python review package";
const COMMAND_REGISTRY_PATH: &str = "crates/larch-lint/data/command-registry.toml";
const REVIEW_AUTHORITY_PATH: &str = "crates/larch-cli/src/review_commands.rs";
const REVIEW_PLANNING_ISSUE: i64 = 7679;
const PYTHON_REVIEW_ROOT: &str = "python/larch/review/";

#[derive(Clone, Copy)]
struct ExpectedCommand {
    domain: &'static str,
    verb: &'static str,
    migration_issue: i64,
    planning_issue: i64,
}

impl ExpectedCommand {
    const fn new(
        domain: &'static str,
        verb: &'static str,
        migration_issue: i64,
        planning_issue: i64,
    ) -> Self {
        Self {
            domain,
            verb,
            migration_issue,
            planning_issue,
        }
    }

    fn selector(self) -> String {
        format!("{} {}", self.domain, self.verb)
    }

    fn matches(self, domain: &str, verb: &str) -> bool {
        self.domain == domain && self.verb == verb
    }
}

#[derive(Clone, Copy)]
struct HandoffCommand {
    domain: &'static str,
    verb: &'static str,
    planning_issue: i64,
}

impl HandoffCommand {
    const fn new(domain: &'static str, verb: &'static str, planning_issue: i64) -> Self {
        Self {
            domain,
            verb,
            planning_issue,
        }
    }

    fn selector(self) -> String {
        format!("{} {}", self.domain, self.verb)
    }

    fn matches(self, domain: &str, verb: &str) -> bool {
        self.domain == domain && self.verb == verb
    }
}

/// Every command migrated by an executable leaf of #7679.
const EXPECTED_COMMANDS: [ExpectedCommand; 79] = [
    ExpectedCommand::new("calibration-replay", "rebuild-ballot", 8439, 7679),
    ExpectedCommand::new("calibration-replay", "run-replay", 8439, 7679),
    ExpectedCommand::new("calibration-replay", "validate-manifest", 8439, 7679),
    ExpectedCommand::new("plan-review", "continuation", 8449, 7679),
    ExpectedCommand::new("plan-review", "drift-baseline", 8449, 7679),
    ExpectedCommand::new("plan-review", "emit", 8448, 7679),
    ExpectedCommand::new("plan-review", "emit-rejected", 8448, 7679),
    ExpectedCommand::new("plan-review", "filter-gate-b-skipped", 8448, 7679),
    ExpectedCommand::new("plan-review", "finalize", 8449, 7679),
    ExpectedCommand::new("plan-review", "gate-b-counts", 8448, 7679),
    ExpectedCommand::new("plan-review", "gate-b-dedup", 8448, 7679),
    ExpectedCommand::new("plan-review", "gate-b-finding-line", 8448, 7679),
    ExpectedCommand::new("plan-review", "json-get-bool", 8449, 7679),
    ExpectedCommand::new("plan-review", "normalize-status", 8449, 7679),
    ExpectedCommand::new("plan-review", "panel-dispatch", 8446, 7679),
    ExpectedCommand::new("plan-review", "persist-accepted-audit", 8448, 7679),
    ExpectedCommand::new("plan-review", "persist-retally-env", 8449, 7679),
    ExpectedCommand::new("plan-review", "persist-round-start-s", 8449, 7679),
    ExpectedCommand::new("plan-review", "prelaunch-failure", 8449, 7679),
    ExpectedCommand::new("plan-review", "preview", 8449, 7679),
    ExpectedCommand::new("plan-review", "round-artifact-included", 8449, 7679),
    ExpectedCommand::new("plan-review", "round-revise-artifact-excluded", 8449, 7679),
    ExpectedCommand::new("plan-review", "round-revise-artifact-included", 8449, 7679),
    ExpectedCommand::new("plan-review", "run", 8449, 7679),
    ExpectedCommand::new("plan-review", "snapshot-pre-review", 8448, 7679),
    ExpectedCommand::new("plan-review", "step3-entry", 8449, 7679),
    ExpectedCommand::new("plan-review", "step3-entry-preview", 8449, 7679),
    ExpectedCommand::new("plan-review", "step3-entry-state", 8449, 7679),
    ExpectedCommand::new("plan-review", "step3-gate-b-bypass", 8449, 7679),
    ExpectedCommand::new("plan-review", "step3-mav", 8449, 7679),
    ExpectedCommand::new("plan-review", "step3-state", 8449, 7679),
    ExpectedCommand::new("plan-review", "step35", 8449, 7679),
    ExpectedCommand::new("plan-review", "step3b-tail", 8449, 7679),
    ExpectedCommand::new("plan-review", "tally", 8448, 7679),
    ExpectedCommand::new("plan-review", "voter-dispatch", 8446, 7679),
    ExpectedCommand::new("review", "aggregate-findings", 8443, 7679),
    ExpectedCommand::new("review", "check-reviewer-failure-threshold", 8442, 7679),
    ExpectedCommand::new("review", "collect-findings", 8442, 7679),
    ExpectedCommand::new("review", "compose-findings", 8445, 7679),
    ExpectedCommand::new("review", "core", 8445, 7679),
    ExpectedCommand::new("review", "dispatch-panel", 8441, 7679),
    ExpectedCommand::new("review", "emit-tally", 8444, 7679),
    ExpectedCommand::new("review", "gather-context", 8440, 7679),
    ExpectedCommand::new("review", "log-phase", 8444, 7679),
    ExpectedCommand::new("review", "prune-nit-findings", 8443, 7679),
    ExpectedCommand::new("review", "reviewer-prune", 8443, 7679),
    ExpectedCommand::new("review", "tally-code-votes", 8444, 7679),
    ExpectedCommand::new("review-and-fix", "apply-findings", 8451, 7679),
    ExpectedCommand::new("review-and-fix", "check-changes", 8451, 7679),
    ExpectedCommand::new("review-and-fix", "commit-fixes", 8451, 7679),
    ExpectedCommand::new("review-and-fix", "normalize-status", 8451, 7679),
    ExpectedCommand::new("review-and-fix", "step5", 8451, 7679),
    ExpectedCommand::new("review-and-fix", "write-pre-self-review-snapshot", 8451, 7679),
    ExpectedCommand::new("review-and-fix", "write-rejected", 8451, 7679),
    ExpectedCommand::new("review-and-fix", "write-self-review-tally", 8451, 7679),
    ExpectedCommand::new("voter-calibration", "snapshot", 8439, 7679),
    ExpectedCommand::new("voting", "accept-finding", 8437, 7679),
    ExpectedCommand::new("voting", "ballot-parse", 8437, 7679),
    ExpectedCommand::new("voting", "classify-result", 8437, 7679),
    ExpectedCommand::new("voting", "code-review-classification-header", 8437, 7679),
    ExpectedCommand::new("voting", "compose-tally-record", 8438, 7679),
    ExpectedCommand::new("voting", "degraded-warning", 8438, 7679),
    ExpectedCommand::new("voting", "effective-judges", 8438, 7679),
    ExpectedCommand::new("voting", "false-positive-match", 8437, 7679),
    ExpectedCommand::new("voting", "file-line-regex", 8437, 7679),
    ExpectedCommand::new("voting", "findings-classification-header", 8437, 7679),
    ExpectedCommand::new("voting", "is-security-block", 8437, 7679),
    ExpectedCommand::new("voting", "panel-tier", 8437, 7679),
    ExpectedCommand::new("voting", "parse-judge-vote", 8437, 7679),
    ExpectedCommand::new("voting", "parse-rate-check", 8437, 7679),
    ExpectedCommand::new("voting", "parse-rate-diag-matches", 8437, 7679),
    ExpectedCommand::new("voting", "parse-rate-retry", 8437, 7679),
    ExpectedCommand::new("voting", "reviewer-for-block", 8437, 7679),
    ExpectedCommand::new("voting", "scoreboard", 8438, 7679),
    ExpectedCommand::new("voting", "split-ballot", 8437, 7679),
    ExpectedCommand::new("voting", "tally-vote", 8438, 7679),
    ExpectedCommand::new("voting", "vote-for-id", 8437, 7679),
    ExpectedCommand::new("voting", "voter-status-block", 8438, 7679),
    ExpectedCommand::new("voting", "write-tally", 8438, 7679),
];

/// Pending commands that the closeout audit assigned to their live consumer.
const HANDOFF_COMMANDS: [HandoffCommand; 31] = [
    HandoffCommand::new("architectural-assessment", "final-report-sections", 7681),
    HandoffCommand::new("architectural-assessment", "materialize", 7681),
    HandoffCommand::new("architectural-assessment", "sanitize-detail", 7681),
    HandoffCommand::new("architectural-assessment", "submit", 7681),
    HandoffCommand::new("architectural-guidelines", "append-deviation-note", 7681),
    HandoffCommand::new("architectural-guidelines", "invalidate", 7681),
    HandoffCommand::new("architectural-guidelines", "materialize-diff", 7681),
    HandoffCommand::new("architectural-guidelines", "persist-design-assessment", 7680),
    HandoffCommand::new("architectural-guidelines", "pin-note-from-staged", 7681),
    HandoffCommand::new("architectural-guidelines", "prepare", 7681),
    HandoffCommand::new("architectural-guidelines", "prepare-compose", 7681),
    HandoffCommand::new("architectural-guidelines", "present-note", 7680),
    HandoffCommand::new("architectural-guidelines", "read", 7680),
    HandoffCommand::new("architectural-guidelines", "write-compose-assessment", 7681),
    HandoffCommand::new("architectural-guidelines", "write-staged-assessment", 7681),
    HandoffCommand::new("architectural-invariants", "append-deviation-note", 7681),
    HandoffCommand::new("architectural-invariants", "invalidate", 7681),
    HandoffCommand::new("architectural-invariants", "materialize-diff", 7681),
    HandoffCommand::new("architectural-invariants", "persist-design-assessment", 7680),
    HandoffCommand::new("architectural-invariants", "pin-note-from-staged", 7681),
    HandoffCommand::new("architectural-invariants", "prepare", 7681),
    HandoffCommand::new("architectural-invariants", "prepare-compose", 7681),
    HandoffCommand::new("architectural-invariants", "present-note", 7680),
    HandoffCommand::new("architectural-invariants", "read", 7680),
    HandoffCommand::new("architectural-invariants", "write-compose-assessment", 7681),
    HandoffCommand::new("architectural-invariants", "write-staged-assessment", 7681),
    HandoffCommand::new("oos", "normalize-header", 7680),
    HandoffCommand::new("oos", "serialize", 7680),
    HandoffCommand::new("render", "plan-review", 7680),
    HandoffCommand::new("render", "specialist", 7681),
    HandoffCommand::new("render", "voter", 7686),
];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/review-python-free.toml",
);

#[derive(Debug)]
pub struct ReviewPythonFreeRule;

pub static RULE: ReviewPythonFreeRule = ReviewPythonFreeRule;

crate::register_rule!(METADATA, RULE);

impl Rule for ReviewPythonFreeRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let authority_present = repository
            .paths()
            .binary_search(&RepoPath::from_trusted(REVIEW_AUTHORITY_PATH))
            .is_ok();
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
        if !authority_present && !commands.iter().any(is_in_scope_row) {
            return Ok(RuleOutput::default());
        }

        let mut findings = command_registry::planning_issue_closure_findings(
            repository,
            REVIEW_PLANNING_ISSUE as u64,
        )?;
        check_registry_rows(commands, &mut findings);
        check_retired_review_package(repository, &mut findings);
        check_live_runtime_references(repository, &mut findings)?;
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

fn is_in_scope_row(value: &Value) -> bool {
    let Some(table) = value.as_table() else {
        return false;
    };
    let domain = table
        .get("domain")
        .and_then(Value::as_str)
        .unwrap_or_default();
    let verb = table
        .get("verb")
        .and_then(Value::as_str)
        .unwrap_or_default();
    expected_command(domain, verb).is_some()
        || handoff_command(domain, verb).is_some()
        || table.get("planning_issue").and_then(Value::as_integer)
            == Some(REVIEW_PLANNING_ISSUE)
}

fn expected_command(domain: &str, verb: &str) -> Option<ExpectedCommand> {
    EXPECTED_COMMANDS
        .iter()
        .copied()
        .find(|command| command.matches(domain, verb))
}

fn handoff_command(domain: &str, verb: &str) -> Option<HandoffCommand> {
    HANDOFF_COMMANDS
        .iter()
        .copied()
        .find(|command| command.matches(domain, verb))
}

fn check_registry_rows(commands: &[Value], findings: &mut Vec<Finding>) {
    let rows = commands
        .iter()
        .filter_map(RegistryCommand::parse)
        .map(|command| (command.selector.clone(), command))
        .collect::<BTreeMap<_, _>>();
    for expected in EXPECTED_COMMANDS {
        let selector = expected.selector();
        let Some(command) = rows.get(&selector) else {
            findings.push(registry_finding(format!(
                "missing final review command row: {selector}"
            )));
            continue;
        };
        if !command.has_final_cutover() {
            findings.push(registry_finding(format!(
                "non-final review command row: {selector}; expected Rust ownership with complete parity, cutover, and Python removal"
            )));
        }
        if command.integer("migration_issue") != Some(expected.migration_issue) {
            findings.push(registry_finding(format!(
                "review-command migration leaf drift: {selector}; expected #{}",
                expected.migration_issue
            )));
        }
        if command.integer("planning_issue") != Some(expected.planning_issue) {
            findings.push(registry_finding(format!(
                "review-command planning owner drift: {selector}; expected #{}",
                expected.planning_issue
            )));
        }
    }
    for handoff in HANDOFF_COMMANDS {
        let selector = handoff.selector();
        let Some(command) = rows.get(&selector) else {
            findings.push(registry_finding(format!(
                "missing review-command hand-off row: {selector}"
            )));
            continue;
        };
        if command.integer("planning_issue") != Some(handoff.planning_issue) {
            findings.push(registry_finding(format!(
                "review-command hand-off drift: {selector}; expected #{}",
                handoff.planning_issue
            )));
        }
    }
    for command in rows.values() {
        if command.integer("planning_issue") == Some(REVIEW_PLANNING_ISSUE)
            && expected_command(command.domain, command.verb).is_none()
        {
            findings.push(registry_finding(format!(
                "unclosed #{REVIEW_PLANNING_ISSUE} ledger row: {}; name the umbrella that owns its migration",
                command.selector
            )));
        }
    }
}

fn check_retired_review_package(repository: &Repository, findings: &mut Vec<Finding>) {
    for path in repository.paths() {
        let relative = path.as_str();
        if relative.starts_with(PYTHON_REVIEW_ROOT)
            && Path::new(relative)
                .extension()
                .is_some_and(|extension| extension.eq_ignore_ascii_case("py"))
            && repository.root().join(relative).is_file()
        {
            findings.push(Finding::new(
                relative,
                1,
                "superseded Python review package source remains",
            ));
        }
    }
}

fn check_live_runtime_references(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    for path in repository.paths() {
        let relative = path.as_str();
        if !is_live_runtime_source(relative) || !repository.root().join(relative).is_file() {
            continue;
        }
        let source = repository.read_utf8(path)?;
        for (index, line) in source.lines().enumerate() {
            if line.contains("larch.review") || line.contains("python/larch/review") {
                findings.push(Finding::new(
                    relative,
                    u32::try_from(index + 1).unwrap_or(u32::MAX),
                    "live runtime source references the retired Python review package",
                ));
            }
        }
    }
    Ok(())
}

fn is_live_runtime_source(path: &str) -> bool {
    if path == "python/larch/cli.py" {
        return true;
    }
    if path == "hooks/hooks.json" {
        return true;
    }
    if path.starts_with("python/larch/") {
        return Path::new(path)
            .extension()
            .is_some_and(|extension| extension.eq_ignore_ascii_case("py"));
    }
    ["skills/", "hooks/", "scripts/"]
        .iter()
        .any(|prefix| path.starts_with(prefix))
        && [".md", ".py", ".sh"]
            .iter()
            .any(|suffix| path.ends_with(suffix))
}

fn registry_finding(message: String) -> Finding {
    Finding::new(COMMAND_REGISTRY_PATH, 1, message)
}

#[cfg(test)]
mod tests {
    use super::{EXPECTED_COMMANDS, HANDOFF_COMMANDS};

    #[test]
    fn pins_unique_review_commands_and_handoffs() {
        let mut expected = EXPECTED_COMMANDS
            .iter()
            .map(|command| command.selector())
            .collect::<Vec<_>>();
        let expected_count = expected.len();
        expected.sort();
        expected.dedup();
        assert_eq!(expected.len(), expected_count);

        let mut handoffs = HANDOFF_COMMANDS
            .iter()
            .map(|command| command.selector())
            .collect::<Vec<_>>();
        let handoff_count = handoffs.len();
        handoffs.sort();
        handoffs.dedup();
        assert_eq!(handoffs.len(), handoff_count);
        assert!(expected.iter().all(|selector| !handoffs.contains(selector)));
    }
}
