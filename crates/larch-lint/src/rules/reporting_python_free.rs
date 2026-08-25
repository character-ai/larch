//! Enforce the closed run-log, report, and rendering ownership boundary.
//!
//! Umbrella #7683 migrated every committed run-log command, every user-facing
//! report renderer, and the diagram, chart, and transcript renderers. This rule
//! pins that final command set so a later change cannot restore a Python
//! registration, a superseded Python entrypoint, or an unmigrated row that
//! still names the closed umbrella as its roadmap owner.

use std::{collections::BTreeSet, path::Path, sync::LazyLock};

use regex::Regex;
use toml::Value;

use crate::{Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput};

use super::python_boundary::{check_python_registry, check_retired_entrypoints};

const NAME: &str = "reporting-python-free";
const DESCRIPTION: &str =
    "Enforce Rust-only run-log, report, and rendering ownership for umbrella #7683";
const COMMAND_REGISTRY_PATH: &str = "crates/larch-lint/data/command-registry.toml";
const REPORTING_AUTHORITY_PATH: &str = "crates/larch-cli/src/run_log_commands.rs";
const UMBRELLA_ISSUE: i64 = 7683;
const PYTHON_RUNTIME_PREFIX: &str = "python/larch/";
const PYTHON_MANIFEST_READER_PATH: &str = "python/larch/report/run_log_manifest.py";
const PYTHON_RUN_LOG_FACADE_PATH: &str = "python/larch/report/run_logs.py";
const PYTHON_SHIP_RECOVERY_PATH: &str = "python/larch/implement/ship_recovery.py";
const PYTHON_PROGRESS_READER_PATH: &str = "python/larch/report/progress_file.py";
const PYTHON_TIMING_COMPAT_PATH: &str = "python/larch/report/timing.py";
const PYTHON_MANIFEST_WRITER_PATHS: &[&str] = &[
    PYTHON_MANIFEST_READER_PATH,
    PYTHON_RUN_LOG_FACADE_PATH,
    PYTHON_SHIP_RECOVERY_PATH,
];

static MANIFEST_WRITER_DEFINITION: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?m)^(?:async\s+)?def\s+(?P<function>_?write_manifest(?:_v2)?|_?update_manifest(?:_v2)?|init_run|update_manifest|load_or_recover_manifest(?:_checked)?|_?recover_manifest(?:_from_run_dir)?|log_manifest_update)\s*\(",
    )
    .expect("manifest writer definition expression is valid")
});

static MANIFEST_WRITER_CALL: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?x)
        (?P<target>
            (?:run_log_manifest\s*\.\s*(?:_?write_manifest(?:_v2)?|_?update_manifest(?:_v2)?|init_run|update_manifest|load_or_recover_manifest(?:_checked)?))
            |(?:run_logs\s*\.\s*log_manifest_update)
            |(?:_?update_manifest_v2|log_manifest_update|init_run|update_manifest|load_or_recover_manifest(?:_checked)?|_?recover_manifest(?:_from_run_dir)?)
        )\s*\(",
    )
    .expect("manifest writer call expression is valid")
});

static MANIFEST_DURABLE_WRITE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?:\.(?:write_text|write_bytes|replace|rename)\s*\()|(?:_?atomic_write\s*\()")
        .expect("manifest durable write expression is valid")
});

static PROGRESS_WRITER_DEFINITION: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?m)^(?:async\s+)?def\s+(?P<function>activate_run|deactivate_run|clear_active_run|append_breadcrumb(?:_for_run)?|cleanup_old_progress_files)\s*\(",
    )
    .expect("progress writer definition expression is valid")
});

static PROGRESS_WRITER_CALL: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?x)
        (?P<target>
            (?:(?:_?progress_file)\s*\.\s*(?:activate_run|deactivate_run|clear_active_run|append_breadcrumb(?:_for_run)?|cleanup_old_progress_files))
            |(?:activate_run|deactivate_run|clear_active_run|append_breadcrumb(?:_for_run)?|cleanup_old_progress_files)
        )\s*\(",
    )
    .expect("progress writer call expression is valid")
});

static PROGRESS_DURABLE_WRITE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?x)
        \.(?:write_text|write_bytes|unlink|replace|rename|mkdir|touch)\s*\(
        |os\s*\.\s*(?:open|unlink|mkdir|replace|remove|rmdir)\s*\(",
    )
    .expect("progress durable write expression is valid")
});

static TIMING_WRITER_DEFINITION: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?m)^(?:class\s+(?P<class>TimingLedger)\b|(?:async\s+)?def\s+(?P<function>mark|record_vendor_task|record_round|_append)\s*\()",
    )
    .expect("timing writer definition expression is valid")
});

static TIMING_WRITER_CALL: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?x)
        (?P<target>
            (?:from\s+larch\.report\.timing\s+import\s+[^\n]*(?:\bTimingLedger\b|\b(?:mark|record_vendor_task|record_round|_append)\b|\*))
            |(?:\b(?:_?timing\s*\.\s*)?TimingLedger\s*\()
            |(?:\b_?timing\s*\.\s*(?:mark|record_vendor_task|record_round|_append)\s*\()
        )",
    )
    .expect("timing writer call expression is valid")
});

static TIMING_DURABLE_WRITE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?x)
        \.(?:write|write_text|write_bytes|unlink|replace|rename|mkdir|touch)\s*\(
        |os\s*\.\s*(?:open|unlink|mkdir|replace|remove|rmdir)\s*\(",
    )
    .expect("timing durable write expression is valid")
});

#[derive(Clone, Copy, Eq, PartialEq)]
enum ExpectedOwner {
    Rust,
    Retired,
}

impl ExpectedOwner {
    const fn owner(self) -> &'static str {
        match self {
            Self::Rust => "rust",
            Self::Retired => "retired",
        }
    }

}

struct ExpectedCommand {
    domain: &'static str,
    verb: &'static str,
    migration_issue: i64,
    owner: ExpectedOwner,
    python_module: &'static str,
    python_function: &'static str,
}

impl ExpectedCommand {
    const fn new(
        domain: &'static str,
        verb: &'static str,
        migration_issue: i64,
        owner: ExpectedOwner,
        python_module: &'static str,
        python_function: &'static str,
    ) -> Self {
        Self {
            domain,
            verb,
            migration_issue,
            owner,
            python_module,
            python_function,
        }
    }

    fn selector(&self) -> String {
        format!("{} {}", self.domain, self.verb)
    }
}

use ExpectedOwner::{Retired, Rust};

/// The complete #7683 command set: 46 rows that still name the umbrella as
/// their roadmap owner plus the nine rows its leaves migrated for an earlier
/// roadmap owner.
const EXPECTED_COMMANDS: [ExpectedCommand; 55] = [
    ExpectedCommand::new("analyze-issues", "render-chart", 8092, Rust, "larch.rendering.render_chart", "render_chart_main"),
    ExpectedCommand::new("final-report", "step18b", 8090, Rust, "larch.report.final_report", "step18b_final_report_main"),
    ExpectedCommand::new("final-report", "write", 8090, Rust, "larch.report.final_report", "write_final_report_main"),
    ExpectedCommand::new("gantt", "render", 8092, Rust, "larch.rendering.gantt", "gantt_render_main"),
    ExpectedCommand::new("progress", "activate", 8084, Rust, "larch.report.progress_file", "progress_activate_main"),
    ExpectedCommand::new("progress", "cleanup", 8290, Rust, "larch.report.progress_file", "cleanup_old_progress_files"),
    ExpectedCommand::new("progress", "clear", 8084, Rust, "larch.report.progress_file", "progress_clear_main"),
    ExpectedCommand::new("progress", "deactivate", 8084, Rust, "larch.report.progress_file", "progress_deactivate_main"),
    ExpectedCommand::new("progress", "install-statusline", 8084, Rust, "larch.report.statusline_install", "install_statusline_main"),
    ExpectedCommand::new("progress", "note", 8084, Rust, "larch.report.progress_file", "progress_note_main"),
    ExpectedCommand::new("progress", "render-phase-detail", 8085, Rust, "larch.report.progress_report", "render_phase_detail_main"),
    ExpectedCommand::new("progress", "session-reset", 8084, Rust, "larch.report.statusline", "session_reset_main"),
    ExpectedCommand::new("progress", "statusline", 8084, Rust, "larch.report.statusline", "statusline_main"),
    ExpectedCommand::new("progress", "write-design-round-meta", 8085, Rust, "larch.report.progress_report", "write_design_round_meta_main"),
    ExpectedCommand::new("progress", "write-implement-round-meta", 8085, Rust, "larch.report.progress_report", "write_implement_round_meta_main"),
    ExpectedCommand::new("report-tokens", "analyze", 8088, Rust, "larch.report.report_tokens_cli", "main"),
    ExpectedCommand::new("run-log", "append", 8073, Rust, "larch.report.run_logs", "larch_log_append_main"),
    ExpectedCommand::new("run-log", "append-entry", 8073, Rust, "larch.report.run_logs", "append_entry_main"),
    ExpectedCommand::new("run-log", "append-failure", 8073, Rust, "larch.report.run_logs", "append_failure_main"),
    ExpectedCommand::new("run-log", "archive", 8079, Rust, "larch.report.run_log_archive", "main"),
    ExpectedCommand::new("run-log", "capture-transcript", 8078, Rust, "larch.report.run_log_flush", "capture_transcript_main"),
    ExpectedCommand::new("run-log", "checkpoint", 8078, Rust, "larch.report.run_log_flush", "run_log_checkpoint_main"),
    ExpectedCommand::new("run-log", "cleanup-implement-logs", 8082, Rust, "larch.report.cleanup_implement_logs", "main"),
    ExpectedCommand::new("run-log", "exists", 8073, Rust, "larch.report.run_logs", "larch_log_exists_main"),
    ExpectedCommand::new("run-log", "flush", 7995, Retired, "larch.report.run_log_flush", "larch_log_flush_main"),
    ExpectedCommand::new("run-log", "init", 8073, Rust, "larch.report.run_logs", "larch_log_init_main"),
    ExpectedCommand::new("run-log", "lifecycle-cancel", 8077, Rust, "larch.report.run_lifecycle", "cancel_main"),
    ExpectedCommand::new("run-log", "lifecycle-early-return", 8077, Rust, "larch.report.run_lifecycle", "early_return_main"),
    ExpectedCommand::new("run-log", "lifecycle-failure", 8077, Rust, "larch.report.run_lifecycle", "failure_main"),
    ExpectedCommand::new("run-log", "lifecycle-finalize", 8077, Rust, "larch.report.run_lifecycle", "finalize_main"),
    ExpectedCommand::new("run-log", "lifecycle-start", 8077, Rust, "larch.report.run_lifecycle", "start_main"),
    ExpectedCommand::new("run-log", "manifest", 8072, Rust, "larch.report.run_logs", "larch_log_manifest_main"),
    ExpectedCommand::new("run-log", "materialize", 8079, Rust, "larch.report.run_log_archive", "materialize_main"),
    ExpectedCommand::new("run-log", "migrate-layout", 8081, Rust, "larch.report.run_log_layout_migration", "main"),
    ExpectedCommand::new("run-log", "prepare-terminal-snapshot", 8078, Rust, "larch.report.run_log_flush", "terminal_snapshot_main"),
    ExpectedCommand::new("run-log", "publish", 8080, Rust, "larch.report.run_log_publish", "main"),
    ExpectedCommand::new("run-log", "publish-breadcrumbs", 8074, Rust, "larch.report.run_log_commit", "publish_breadcrumbs_main"),
    ExpectedCommand::new("run-log", "refresh", 8078, Rust, "larch.report.run_log_flush", "refresh_run_logs_main"),
    ExpectedCommand::new("run-log", "render-session-transcript", 8091, Rust, "larch.rendering.render_session_transcript", "main"),
    ExpectedCommand::new("run-log", "retro-fix-cursor", 8081, Rust, "larch.report.retro_fix_cursor", "main"),
    ExpectedCommand::new("run-log", "retro-v3-sweep", 8081, Rust, "larch.report.retro_v3_sweep", "main"),
    ExpectedCommand::new("run-log", "storage-preflight", 8076, Rust, "larch.report.storage_config", "storage_preflight_main"),
    ExpectedCommand::new("run-log", "sync", 8080, Rust, "larch.report.run_log_sync", "main"),
    ExpectedCommand::new("run-log", "validate-run-id", 8071, Rust, "larch.report.run_logs", "larch_log_validate_run_id_main"),
    ExpectedCommand::new("run-log", "verify-completeness", 8073, Rust, "larch.report.run_logs", "verify_completeness_main"),
    ExpectedCommand::new("run-log", "write", 8073, Rust, "larch.report.run_logs", "larch_log_write_main"),
    ExpectedCommand::new("run-log", "write-round", 8073, Rust, "larch.report.run_logs", "larch_log_write_round_main"),
    ExpectedCommand::new("timing", "dump", 8083, Rust, "larch.report.timing", "timing_dump_main"),
    ExpectedCommand::new("timing", "harness-mark", 8083, Rust, "larch.report.timing", "timing_harness_mark_main"),
    ExpectedCommand::new("timing", "mark", 8083, Rust, "larch.report.timing", "timing_mark_main"),
    ExpectedCommand::new("timing", "record-round", 8083, Rust, "larch.report.timing", "timing_record_round_main"),
    ExpectedCommand::new("timing", "record-vendor-task", 8083, Rust, "larch.report.timing", "timing_record_vendor_task_main"),
    ExpectedCommand::new("timing", "report", 8083, Rust, "larch.report.timing", "timing_report_main"),
    ExpectedCommand::new("timing", "task-kinds", 8083, Rust, "larch.report.timing", "timing_task_kinds_main"),
    ExpectedCommand::new("timing", "telemetry-mark", 8083, Rust, "larch.report.timing", "timing_telemetry_mark_main"),
];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/reporting-python-free.toml",
);

#[derive(Debug)]
pub struct ReportingPythonFreeRule;

pub static RULE: ReportingPythonFreeRule = ReportingPythonFreeRule;

crate::register_rule!(METADATA, RULE);

impl Rule for ReportingPythonFreeRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let authority_present = repository
            .paths()
            .binary_search(&RepoPath::from_trusted(REPORTING_AUTHORITY_PATH))
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

        let mut findings = Vec::new();
        check_registry_rows(commands, &mut findings);
        check_python_registrations(repository, &mut findings)?;
        check_python_entrypoints(repository, &mut findings)?;
        check_manifest_writer_boundary(repository, &mut findings)?;
        check_progress_writer_boundary(repository, &mut findings)?;
        check_timing_writer_boundary(repository, &mut findings)?;
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

fn check_manifest_writer_boundary(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    for path in repository.paths() {
        let relative = path.as_str();
        if !relative.starts_with(PYTHON_RUNTIME_PREFIX)
            || !Path::new(relative)
                .extension()
                .is_some_and(|extension| extension.eq_ignore_ascii_case("py"))
        {
            continue;
        }
        let source = repository.read_utf8(path)?;
        if PYTHON_MANIFEST_WRITER_PATHS.contains(&relative) {
            for matched in MANIFEST_WRITER_DEFINITION.captures_iter(&source) {
                let whole = matched
                    .get(0)
                    .expect("whole manifest writer definition capture");
                findings.push(Finding::new(
                    relative,
                    super::python_boundary::offset_line_number(&source, whole.start()),
                    format!(
                        "production Python run-log manifest writer remains: {}",
                        &matched["function"]
                    ),
                ));
            }
        } else {
            for matched in MANIFEST_WRITER_CALL.captures_iter(&source) {
                let whole = matched.get(0).expect("whole manifest writer call capture");
                let target: String = matched["target"]
                    .chars()
                    .filter(|character| !character.is_whitespace())
                    .collect();
                findings.push(Finding::new(
                    relative,
                    super::python_boundary::offset_line_number(&source, whole.start()),
                    format!("production Python caller bypasses Rust run-log manifest owner: {target}"),
                ));
            }
        }
        if relative == PYTHON_MANIFEST_READER_PATH {
            for matched in MANIFEST_DURABLE_WRITE.find_iter(&source) {
                findings.push(Finding::new(
                    relative,
                    super::python_boundary::offset_line_number(&source, matched.start()),
                    "production Python manifest compatibility module performs a durable write",
                ));
            }
        }
    }
    Ok(())
}

fn check_progress_writer_boundary(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    for path in repository.paths() {
        let relative = path.as_str();
        if !relative.starts_with(PYTHON_RUNTIME_PREFIX)
            || !Path::new(relative)
                .extension()
                .is_some_and(|extension| extension.eq_ignore_ascii_case("py"))
        {
            continue;
        }
        let source = repository.read_utf8(path)?;
        if relative == PYTHON_PROGRESS_READER_PATH {
            for matched in PROGRESS_WRITER_DEFINITION.captures_iter(&source) {
                let whole = matched
                    .get(0)
                    .expect("whole progress writer definition capture");
                findings.push(Finding::new(
                    relative,
                    super::python_boundary::offset_line_number(&source, whole.start()),
                    format!(
                        "production Python progress-state writer remains: {}",
                        &matched["function"]
                    ),
                ));
            }
            for matched in PROGRESS_DURABLE_WRITE.find_iter(&source) {
                findings.push(Finding::new(
                    relative,
                    super::python_boundary::offset_line_number(&source, matched.start()),
                    "production Python progress compatibility module performs a durable write",
                ));
            }
        } else {
            for matched in PROGRESS_WRITER_CALL.captures_iter(&source) {
                let whole = matched.get(0).expect("whole progress writer call capture");
                let target: String = matched["target"]
                    .chars()
                    .filter(|character| !character.is_whitespace())
                    .collect();
                findings.push(Finding::new(
                    relative,
                    super::python_boundary::offset_line_number(&source, whole.start()),
                    format!(
                        "production Python caller bypasses Rust progress-state owner: {target}"
                    ),
                ));
            }
        }
    }
    Ok(())
}

fn check_timing_writer_boundary(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    for path in repository.paths() {
        let relative = path.as_str();
        if !relative.starts_with(PYTHON_RUNTIME_PREFIX)
            || !Path::new(relative)
                .extension()
                .is_some_and(|extension| extension.eq_ignore_ascii_case("py"))
        {
            continue;
        }
        let source = repository.read_utf8(path)?;
        if relative == PYTHON_TIMING_COMPAT_PATH {
            for matched in TIMING_WRITER_DEFINITION.captures_iter(&source) {
                let whole = matched
                    .get(0)
                    .expect("whole timing writer definition capture");
                let name = matched
                    .name("class")
                    .or_else(|| matched.name("function"))
                    .expect("timing writer name capture")
                    .as_str();
                findings.push(Finding::new(
                    relative,
                    super::python_boundary::offset_line_number(&source, whole.start()),
                    format!("production Python timing-ledger writer remains: {name}"),
                ));
            }
            for matched in TIMING_DURABLE_WRITE.find_iter(&source) {
                findings.push(Finding::new(
                    relative,
                    super::python_boundary::offset_line_number(&source, matched.start()),
                    "production Python timing compatibility module performs a durable write",
                ));
            }
        } else {
            for matched in TIMING_WRITER_CALL.captures_iter(&source) {
                let whole = matched.get(0).expect("whole timing writer call capture");
                let target: String = matched["target"]
                    .chars()
                    .filter(|character| !character.is_whitespace())
                    .collect();
                findings.push(Finding::new(
                    relative,
                    super::python_boundary::offset_line_number(&source, whole.start()),
                    format!("production Python caller bypasses Rust timing owner: {target}"),
                ));
            }
        }
    }
    Ok(())
}

fn is_in_scope_row(value: &Value) -> bool {
    value.as_table().is_some_and(|table| {
        let field = |name: &str| table.get(name).and_then(Value::as_str).unwrap_or_default();
        expected_command(&format!("{} {}", field("domain"), field("verb"))).is_some()
            || table.get("planning_issue").and_then(Value::as_integer) == Some(UMBRELLA_ISSUE)
    })
}

fn expected_command(selector: &str) -> Option<&'static ExpectedCommand> {
    EXPECTED_COMMANDS
        .iter()
        .find(|command| command.selector() == selector)
}

fn check_registry_rows(commands: &[Value], findings: &mut Vec<Finding>) {
    let mut found = BTreeSet::new();
    for value in commands {
        let Some(table) = value.as_table() else {
            continue;
        };
        let field = |name: &str| table.get(name).and_then(Value::as_str).unwrap_or_default();
        let domain = field("domain");
        let verb = field("verb");
        let selector = format!("{domain} {verb}");
        let Some(expected) = expected_command(&selector) else {
            if table.get("planning_issue").and_then(Value::as_integer) == Some(UMBRELLA_ISSUE) {
                findings.push(registry_finding(format!(
                    "unclosed #{UMBRELLA_ISSUE} ledger row: {selector}; name the umbrella that owns its migration"
                )));
            }
            continue;
        };
        found.insert(selector.clone());
        if field("owner") != expected.owner.owner() {
            findings.push(registry_finding(format!(
                "non-final reporting command row: {selector}; expected owner {}",
                expected.owner.owner()
            )));
        }
        if table.get("migration_issue").and_then(Value::as_integer) != Some(expected.migration_issue)
        {
            findings.push(registry_finding(format!(
                "reporting command migration issue drift: {selector}; expected #{}",
                expected.migration_issue
            )));
        }
    }
    for expected in &EXPECTED_COMMANDS {
        let selector = expected.selector();
        if !found.contains(&selector) {
            findings.push(registry_finding(format!(
                "missing final reporting-owned command row: {selector}"
            )));
        }
    }
}

fn check_python_registrations(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    check_python_registry(
        repository,
        &|domain, verb| expected_command(&format!("{domain} {verb}")).is_some(),
        &|domain, verb| {
            format!("reporting-owned command remains registered in Python: {domain} {verb}")
        },
        findings,
    )
}

fn check_python_entrypoints(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    let targets: Vec<(String, String)> = EXPECTED_COMMANDS
        .iter()
        .map(|command| {
            (
                command.python_module.to_owned(),
                command.python_function.to_owned(),
            )
        })
        .collect();
    check_retired_entrypoints(
        repository,
        &targets,
        &|module, function| {
            format!("superseded reporting Python entrypoint remains: {module}.{function}")
        },
        findings,
    )
}

fn registry_finding(message: String) -> Finding {
    Finding::new(COMMAND_REGISTRY_PATH, 1, message)
}


#[cfg(test)]
mod tests {
    use super::{EXPECTED_COMMANDS, ExpectedOwner, expected_command};

    #[test]
    fn pins_one_row_for_every_selector() {
        let mut selectors: Vec<String> = EXPECTED_COMMANDS
            .iter()
            .map(super::ExpectedCommand::selector)
            .collect();
        let total = selectors.len();
        selectors.sort();
        selectors.dedup();
        assert_eq!(selectors.len(), total);
    }

    #[test]
    fn resolves_expected_rows_by_selector() {
        let flush = expected_command("run-log flush").expect("retired run-log flush row");
        assert!(matches!(flush.owner, ExpectedOwner::Retired));
        assert!(expected_command("token cost").is_none());
    }
}
