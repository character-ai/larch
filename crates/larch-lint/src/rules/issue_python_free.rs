//! Enforce the closed issue-domain ownership boundary.
//!
//! Umbrella #7682 migrated its issue, triage, umbrella, tracking, OOS,
//! dependency, combination, and issue-analysis command leaves. This rule pins
//! those completed command rows and keeps the deliberately retained Python
//! libraries assigned to their receiving umbrellas.

use std::{collections::BTreeSet, path::Path};

use toml::{Value, map::Map};

use crate::{Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput};

use super::python_boundary::{check_python_registry, check_retired_entrypoints};

const NAME: &str = "issue-python-free";
const DESCRIPTION: &str =
    "Enforce Rust-only completed issue-domain commands and explicit Python hand-offs for umbrella #7682";
const COMMAND_REGISTRY_PATH: &str = "crates/larch-lint/data/command-registry.toml";
const ISSUE_AUTHORITY_PATH: &str = "crates/larch-cli/src/issue_commands.rs";
const UMBRELLA_ISSUE: i64 = 7682;
const PYTHON_ISSUE_ROOT: &str = "python/larch/issue/";
const PYTHON_ISSUE_INIT: &str = "python/larch/issue/__init__.py";
const TRACKING_PYTHON_MODULE: &str = "python/larch/issue/tracking_issue.py";
const RUST_RUNTIME_FACADE: &str = "python/larch/core/rust_runtime.py";
const RETIRED_TRACKING_CALLS: [&str; 14] = [
    "tracking_issue.append_comment",
    "tracking_issue.create_issue",
    "tracking_issue.initialize_implementation_lease",
    "tracking_issue.mark_false_positive",
    "tracking_issue.read(",
    "tracking_issue.read_sentinel",
    "tracking_issue.refresh_implementation_lease",
    "tracking_issue.rename_terminal_with_lease",
    "tracking_issue.rename_with_details",
    "tracking_issue.rename(",
    "tracking_issue.upsert_marker_comment",
    "tracking_issue.upsert_marker_summary",
    "tracking_issue.upsert_summary",
    "tracking_issue.upsert_token_report",
];
const TRACKING_RUNTIME_WRAPPERS: [&str; 9] = [
    "def tracking_issue_append_comment(",
    "def tracking_issue_create(",
    "def tracking_issue_mark_false_positive(",
    "def tracking_issue_read(",
    "def tracking_issue_read_body(",
    "def tracking_issue_read_marker(",
    "def tracking_issue_read_sentinel(",
    "def tracking_issue_rename(",
    "def tracking_issue_upsert_summary(",
];

struct ExpectedCommand {
    domain: &'static str,
    verb: &'static str,
    migration_issue: i64,
    planning_issue: i64,
    python_module: &'static str,
    python_function: &'static str,
}

impl ExpectedCommand {
    const fn new(
        domain: &'static str,
        verb: &'static str,
        migration_issue: i64,
        planning_issue: i64,
        python_module: &'static str,
        python_function: &'static str,
    ) -> Self {
        Self {
            domain,
            verb,
            migration_issue,
            planning_issue,
            python_module,
            python_function,
        }
    }

    fn selector(&self) -> String {
        format!("{} {}", self.domain, self.verb)
    }

    fn matches(&self, domain: &str, verb: &str) -> bool {
        self.domain == domain && self.verb == verb
    }

    fn retired_python_target(&self) -> (String, String) {
        (
            self.python_module.to_owned(),
            self.python_function.to_owned(),
        )
    }
}

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

    fn selector(&self) -> String {
        format!("{} {}", self.domain, self.verb)
    }
}

struct RetainedModule {
    path: &'static str,
    planning_issue: i64,
}

type RegistryTable = Map<String, Value>;

/// A command-registry row with its selector parsed once for the issue-domain
/// audit. Keeping this representation local makes the audit's three-way
/// ownership decision explicit: completed leaf, named hand-off, or stale
/// umbrella ownership.
struct RegistryCommand<'a> {
    table: &'a RegistryTable,
    domain: &'a str,
    verb: &'a str,
    selector: String,
}

impl<'a> RegistryCommand<'a> {
    fn parse(value: &'a Value) -> Option<Self> {
        let table = value.as_table()?;
        let domain = registry_text(table, "domain");
        let verb = registry_text(table, "verb");
        Some(Self {
            table,
            domain,
            verb,
            selector: [domain, verb].join(" "),
        })
    }

    fn text(&self, key: &str) -> Option<&str> {
        self.table.get(key).and_then(Value::as_str)
    }

    fn integer(&self, key: &str) -> Option<i64> {
        self.table.get(key).and_then(Value::as_integer)
    }

    fn has_final_cutover(&self) -> bool {
        [
            ("owner", "rust"),
            ("implementation_parity", "complete"),
            ("consumer_cutover", "complete"),
            ("python_removal", "complete"),
        ]
        .into_iter()
        .all(|(key, expected)| self.text(key) == Some(expected))
    }
}

fn registry_text<'a>(table: &'a RegistryTable, key: &str) -> &'a str {
    table.get(key).and_then(Value::as_str).unwrap_or_default()
}

impl RetainedModule {
    const fn new(path: &'static str, planning_issue: i64) -> Self {
        Self {
            path,
            planning_issue,
        }
    }
}

/// Every command cut over by a #7682 executable leaf. Some rows intentionally
/// name #7680 because the design workflow owns their remaining consumers.
const EXPECTED_COMMANDS: [ExpectedCommand; 96] = [
    ExpectedCommand::new("analyze-bugs", "ledger", 8184, 7682, "larch.issue.analyze_bugs", "ledger_main"),
    ExpectedCommand::new("analyze-bugs", "prefetch", 8184, 7682, "larch.issue.analyze_bugs", "prefetch_main"),
    ExpectedCommand::new("analyze-bugs", "report", 8185, 7682, "larch.issue.analyze_bugs", "report_main"),
    ExpectedCommand::new("analyze-bugs", "runtime", 8185, 7682, "larch.issue.analyze_bugs", "runtime_main"),
    ExpectedCommand::new("analyze-issues", "analyze", 8183, 7682, "larch.issue.analyze_issues", "analyze_main"),
    ExpectedCommand::new("analyze-issues", "fetch", 8183, 7682, "larch.issue.analyze_issues", "fetch_main"),
    ExpectedCommand::new("analyze-issues", "run", 8183, 7682, "larch.issue.analyze_issues", "run_main"),
    ExpectedCommand::new("audit-runs", "bugs-backlog-nudge", 8189, 7682, "larch.issue.audit_runs", "bugs_backlog_nudge_main"),
    ExpectedCommand::new("audit-runs", "close-priors", 8189, 7682, "larch.issue.audit_runs", "close_priors_main"),
    ExpectedCommand::new("audit-runs", "compute-counters", 8188, 7682, "larch.issue.audit_runs", "compute_counters_main"),
    ExpectedCommand::new("audit-runs", "map-runs", 8188, 7682, "larch.issue.audit_runs", "map_runs_main"),
    ExpectedCommand::new("audit-runs", "pacific-timestamp", 8188, 7682, "larch.issue.audit_runs", "pacific_timestamp_main"),
    ExpectedCommand::new("audit-runs", "preflight", 8188, 7682, "larch.issue.audit_runs", "preflight_main"),
    ExpectedCommand::new("audit-runs", "resolve-prs", 8188, 7682, "larch.issue.audit_runs", "resolve_prs_main"),
    ExpectedCommand::new("audit-runs", "scan-run", 8188, 7682, "larch.issue.audit_runs", "scan_run_main"),
    ExpectedCommand::new("audit-runs", "title", 8189, 7682, "larch.issue.audit_runs", "title_main"),
    ExpectedCommand::new("audit-runs", "title-match", 8189, 7682, "larch.issue.audit_runs", "title_match_main"),
    ExpectedCommand::new("block-issue", "add-blocked-by", 8170, 7682, "larch.issue.issue_block", "add_blocked_by_main"),
    ExpectedCommand::new("block-issue", "remove-blocked-by", 8170, 7682, "larch.issue.issue_block", "remove_blocked_by_main"),
    ExpectedCommand::new("combine-issues", "apply", 8181, 7682, "larch.issue.combine_issues", "apply_main"),
    ExpectedCommand::new("combine-issues", "close-eligible", 8181, 7682, "larch.issue.combine_issues", "close_eligible_main"),
    ExpectedCommand::new("combine-issues", "close-sources", 8181, 7682, "larch.issue.combine_issues", "close_sources_main"),
    ExpectedCommand::new("combine-issues", "close-stale", 8181, 7682, "larch.issue.combine_issues", "close_stale_main"),
    ExpectedCommand::new("combine-issues", "fetch", 8181, 7682, "larch.issue.combine_issues", "fetch_main"),
    ExpectedCommand::new("combine-issues", "fetch-deps", 8181, 7682, "larch.issue.combine_issues", "fetch_deps_main"),
    ExpectedCommand::new("combine-issues", "list-open", 8181, 7682, "larch.issue.combine_issues", "list_open_main"),
    ExpectedCommand::new("combine-issues", "plan-audit", 8181, 7682, "larch.issue.combine_issues", "plan_audit_main"),
    ExpectedCommand::new("combine-issues", "plan-inherited", 8181, 7682, "larch.issue.combine_issues", "plan_inherited_main"),
    ExpectedCommand::new("combine-issues", "prose-audit", 8181, 7682, "larch.issue.combine_issues", "prose_audit_main"),
    ExpectedCommand::new("deps", "apply", 8180, 7682, "larch.issue.deps_audit", "apply_main"),
    ExpectedCommand::new("deps", "explicit-refs", 8180, 7682, "larch.issue.deps_audit", "explicit_refs_main"),
    ExpectedCommand::new("deps", "fetch", 8180, 7682, "larch.issue.deps_audit", "fetch_main"),
    ExpectedCommand::new("deps", "plan", 8180, 7682, "larch.issue.deps_audit", "plan_main"),
    ExpectedCommand::new("deps", "resolve-repo", 8180, 7682, "larch.issue.deps_audit", "resolve_repo_main"),
    ExpectedCommand::new("deps", "write-proposals", 8180, 7682, "larch.issue.deps_audit", "write_proposals_main"),
    ExpectedCommand::new("execution-issues", "append", 8176, 7682, "larch.issue.execution_issues", "append_execution_issue_main"),
    ExpectedCommand::new("execution-issues", "flush", 8176, 7682, "larch.issue.execution_issues", "flush_execution_issues_main"),
    ExpectedCommand::new("execution-issues", "flush-safety-net", 8176, 7682, "larch.issue.execution_issues", "flush_execution_issues_safety_net_main"),
    ExpectedCommand::new("execution-issues", "refresh", 8176, 7682, "larch.issue.execution_issues", "refresh_execution_issues_main"),
    ExpectedCommand::new("issue", "add-blocked-by", 8170, 7682, "larch.issue.issue_create", "add_blocked_by_main"),
    ExpectedCommand::new("issue", "add-sub-issue", 8170, 7682, "larch.issue.issue_create", "add_sub_issue_main"),
    ExpectedCommand::new("issue", "allocate-candidates", 8168, 7682, "larch.issue.issue_create", "allocate_candidates_main"),
    ExpectedCommand::new("issue", "cleanup-failed", 8169, 7682, "larch.issue.issue_create", "cleanup_failed_main"),
    ExpectedCommand::new("issue", "context", 8167, 7682, "larch.issue.issue_query", "issue_context_main"),
    ExpectedCommand::new("issue", "create-one", 8169, 7682, "larch.issue.issue_create", "create_one_main"),
    ExpectedCommand::new("issue", "fetch-issue-details", 8168, 7682, "larch.issue.issue_create", "fetch_issue_details_main"),
    ExpectedCommand::new("issue", "info", 8167, 7682, "larch.issue.issue_query", "issue_info_main"),
    ExpectedCommand::new("issue", "insert-signal-marker", 8171, 7682, "larch.issue.issue_wire", "issue_insert_signal_marker_main"),
    ExpectedCommand::new("issue", "list-issues", 8168, 7682, "larch.issue.issue_create", "list_issues_main"),
    ExpectedCommand::new("issue", "parse-input", 8168, 7682, "larch.issue.issue_create", "parse_input_main"),
    ExpectedCommand::new("issue", "state", 8167, 7682, "larch.issue.issue_query", "issue_state_main"),
    ExpectedCommand::new("issue", "title-archival-jq", 8171, 7682, "larch.issue.issue_wire", "issue_title_archival_jq_main"),
    ExpectedCommand::new("issue", "title-eligibility", 8171, 7682, "larch.issue.issue_wire", "issue_title_eligibility_main"),
    ExpectedCommand::new("issue", "write-sentinel", 8169, 7682, "larch.issue.issue_create", "write_sentinel_main"),
    ExpectedCommand::new("learn-from-bugs", "check-proposals", 8187, 7682, "larch.issue.learn_from_bugs", "check_proposals_main"),
    ExpectedCommand::new("learn-from-bugs", "coverage-index", 8186, 7682, "larch.issue.learn_from_bugs", "coverage_index_main"),
    ExpectedCommand::new("learn-from-bugs", "filing-deps", 8187, 7682, "larch.issue.learn_from_bugs", "filing_deps_main"),
    ExpectedCommand::new("learn-from-bugs", "prepare", 8186, 7682, "larch.issue.learn_from_bugs", "prepare_main"),
    ExpectedCommand::new("learn-from-bugs", "read-state", 8186, 7682, "larch.issue.learn_from_bugs", "read_state_main"),
    ExpectedCommand::new("learn-from-bugs", "resolve-zones", 8186, 7682, "larch.issue.learn_from_bugs", "resolve_zones_main"),
    ExpectedCommand::new("learn-from-bugs", "state-publish", 8187, 7682, "larch.issue.learn_from_bugs", "state_publish_main"),
    ExpectedCommand::new("learn-from-bugs", "validate-report", 8187, 7682, "larch.issue.learn_from_bugs", "validate_report_main"),
    ExpectedCommand::new("learn-from-bugs", "verify-origin", 8187, 7682, "larch.issue.learn_from_bugs", "verify_origin_main"),
    ExpectedCommand::new("learn-from-bugs", "write-state", 8186, 7682, "larch.issue.learn_from_bugs", "write_state_main"),
    ExpectedCommand::new("named-block", "write", 8171, 7682, "larch.issue.issue_wire", "named_block_write_main"),
    ExpectedCommand::new("oos", "disposition-checkpoint", 8178, 7680, "larch.issue.file_oos", "disposition_checkpoint_main"),
    ExpectedCommand::new("oos", "disposition-gate", 8178, 7680, "larch.issue.file_oos", "disposition_gate_main"),
    ExpectedCommand::new("oos", "file", 8179, 7680, "larch.issue.oos_filer", "cmd_file"),
    ExpectedCommand::new("oos", "file-conflict-deps", 8178, 7680, "larch.issue.file_oos", "file_conflict_deps_main"),
    ExpectedCommand::new("oos", "issue-cap", 8178, 7680, "larch.issue.file_oos", "issue_cap_main"),
    ExpectedCommand::new("oos", "materialize-manifest", 8178, 7680, "larch.issue.file_oos", "materialize_manifest_main"),
    ExpectedCommand::new("plan", "scope-paths", 8171, 7680, "larch.issue.issue_wire", "plan_scope_paths_main"),
    ExpectedCommand::new("plan-block", "read", 8171, 7680, "larch.issue.issue_wire", "plan_block_read_main"),
    ExpectedCommand::new("plan-block", "strip-body", 8171, 7680, "larch.issue.issue_wire", "plan_block_strip_body_main"),
    ExpectedCommand::new("plan-block", "write", 8171, 7680, "larch.issue.issue_wire", "plan_block_write_main"),
    ExpectedCommand::new("tracking-issue", "append-comment", 8346, 7682, "larch.issue.tracking_issue", "append_comment_main"),
    ExpectedCommand::new("tracking-issue", "create-issue", 8346, 7682, "larch.issue.tracking_issue", "create_issue_main"),
    ExpectedCommand::new("tracking-issue", "mark-false-positive", 8346, 7682, "larch.issue.tracking_issue", "mark_false_positive_main"),
    ExpectedCommand::new("tracking-issue", "read", 8346, 7682, "larch.issue.tracking_issue", "read_main"),
    ExpectedCommand::new("tracking-issue", "rename", 8346, 7682, "larch.issue.tracking_issue", "rename_main"),
    ExpectedCommand::new("tracking-issue", "upsert-summary", 8346, 7682, "larch.issue.tracking_issue", "upsert_summary_main"),
    ExpectedCommand::new("triage", "apply", 8172, 7682, "larch.issue.triage", "apply_main"),
    ExpectedCommand::new("triage", "inspect", 8172, 7682, "larch.issue.triage", "inspect_main"),
    ExpectedCommand::new("triage", "probe", 8172, 7682, "larch.issue.triage", "probe_main"),
    ExpectedCommand::new("umbrella", "mark-in-flight", 8173, 7682, "larch.issue.umbrella", "mark_in_flight_main"),
    ExpectedCommand::new("umbrella", "mutate", 8174, 7682, "larch.issue.umbrella", "mutate_main"),
    ExpectedCommand::new("umbrella", "persist-proposal", 8173, 7682, "larch.issue.umbrella", "persist_proposal_main"),
    ExpectedCommand::new("umbrella", "prepare", 8173, 7682, "larch.issue.umbrella", "prepare_main"),
    ExpectedCommand::new("umbrella", "reconcile-in-flight", 8173, 7682, "larch.issue.umbrella", "reconcile_in_flight_main"),
    ExpectedCommand::new("umbrella", "record-resolved", 8173, 7682, "larch.issue.umbrella", "record_resolved_main"),
    ExpectedCommand::new("umbrella", "verify", 8174, 7682, "larch.issue.umbrella", "verify_main"),
    ExpectedCommand::new("umbrella", "verify-completion", 8174, 7682, "larch.issue.umbrella", "verify_completion_main"),
    ExpectedCommand::new("untrusted", "content-block", 8171, 7682, "larch.issue.issue_wire", "untrusted_content_block_main"),
    ExpectedCommand::new("untrusted", "file-block", 8171, 7682, "larch.issue.issue_wire", "untrusted_file_block_main"),
    ExpectedCommand::new("untrusted", "redact-stream", 8171, 7682, "larch.issue.issue_wire", "untrusted_redact_stream_main"),
    ExpectedCommand::new("untrusted", "xml-escape-attr", 8171, 7682, "larch.issue.issue_wire", "untrusted_xml_escape_attr_main"),
];

/// Commands that are deliberately outside #7682's closed boundary.
const HANDOFF_COMMANDS: [HandoffCommand; 21] = [
    HandoffCommand::new("analyze-issues", "render-chart", 7683),
    HandoffCommand::new("clarify", "comment-fetch", 7680),
    HandoffCommand::new("clarify", "comment-post", 7680),
    HandoffCommand::new("clarify", "label", 7680),
    HandoffCommand::new("clarify", "state", 7680),
    HandoffCommand::new("issue", "migration-audit", 7685),
    HandoffCommand::new("oos", "normalize-header", 7679),
    HandoffCommand::new("oos", "serialize", 7679),
    HandoffCommand::new("rejected-analysis", "finalize", 7684),
    HandoffCommand::new("rejected-analysis", "ingest-verdict", 7684),
    HandoffCommand::new("rejected-analysis", "prepare", 7684),
    HandoffCommand::new("rejected-analysis", "record", 7684),
    HandoffCommand::new("render", "run-summary", 7680),
    HandoffCommand::new("token", "cost", 7684),
    HandoffCommand::new("token", "render-cost-line", 7684),
    HandoffCommand::new("tracking", "post-issue", 7681),
    HandoffCommand::new("validate-merged", "ingest-finder", 7684),
    HandoffCommand::new("validate-merged", "ingest-refuter", 7684),
    HandoffCommand::new("validate-merged", "prepare", 7684),
    HandoffCommand::new("validate-merged", "report", 7684),
    HandoffCommand::new("validate-merged", "write-state", 7684),
];

/// The package initializer is structural. Every other top-level issue module
/// must name the umbrella responsible for its next cutover.
const RETAINED_MODULES: [RetainedModule; 21] = [
    RetainedModule::new("python/larch/issue/_ground_truth.py", 7684),
    RetainedModule::new("python/larch/issue/_oos.py", 7684),
    RetainedModule::new("python/larch/issue/_report.py", 7684),
    RetainedModule::new("python/larch/issue/_util.py", 7684),
    RetainedModule::new("python/larch/issue/analyze_bugs.py", 7684),
    RetainedModule::new("python/larch/issue/execution_issues.py", 7681),
    RetainedModule::new("python/larch/issue/file_oos.py", 7680),
    RetainedModule::new("python/larch/issue/issue_block.py", 7685),
    RetainedModule::new("python/larch/issue/issue_blocks.py", 7680),
    RetainedModule::new("python/larch/issue/issue_create.py", 7680),
    RetainedModule::new("python/larch/issue/issue_mutation.py", 7680),
    RetainedModule::new("python/larch/issue/issue_wire.py", 7680),
    RetainedModule::new("python/larch/issue/migration_governance.py", 7685),
    RetainedModule::new("python/larch/issue/oos.py", 7679),
    RetainedModule::new("python/larch/issue/oos_disposition.py", 7680),
    RetainedModule::new("python/larch/issue/oos_priority.py", 7680),
    RetainedModule::new("python/larch/issue/open_rows.py", 7685),
    RetainedModule::new("python/larch/issue/rejected_analysis.py", 7684),
    RetainedModule::new("python/larch/issue/title_match.py", 7680),
    RetainedModule::new("python/larch/issue/tracking_issue.py", 7681),
    RetainedModule::new("python/larch/issue/validate_merged.py", 7684),
];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/issue-python-free.toml",
);

#[derive(Debug)]
pub struct IssuePythonFreeRule;

pub static RULE: IssuePythonFreeRule = IssuePythonFreeRule;

crate::register_rule!(METADATA, RULE);

impl Rule for IssuePythonFreeRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let authority_present = repository
            .paths()
            .binary_search(&RepoPath::from_trusted(ISSUE_AUTHORITY_PATH))
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
        check_tracking_python_boundary(repository, &mut findings)?;
        check_retained_modules(repository, &mut findings);
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

fn check_tracking_python_boundary(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    let tracking_path = RepoPath::from_trusted(TRACKING_PYTHON_MODULE);
    if repository.paths().binary_search(&tracking_path).is_ok() {
        let source = repository.read_utf8(&tracking_path)?;
        for token in [
            "from larch.git import gh",
            "from larch.issue import issue_mutation",
            "gh.",
            "issue_mutation.",
        ] {
            if let Some(offset) = source.find(token) {
                findings.push(Finding::new(
                    TRACKING_PYTHON_MODULE,
                    line_for_offset(&source, offset),
                    format!("superseded Python tracking GitHub behavior returned: {token}"),
                ));
            }
        }
    } else {
        findings.push(Finding::new(
            TRACKING_PYTHON_MODULE,
            1,
            "missing pure tracking-issue compatibility module",
        ));
    }
    for path in repository.paths() {
        let relative = path.as_str();
        if !relative.starts_with("python/larch/")
            || !Path::new(relative)
                .extension()
                .is_some_and(|extension| extension.eq_ignore_ascii_case("py"))
            || relative == TRACKING_PYTHON_MODULE
        {
            continue;
        }
        let source = repository.read_utf8(path)?;
        for token in RETIRED_TRACKING_CALLS {
            if let Some(offset) = source.find(token) {
                findings.push(Finding::new(
                    relative,
                    line_for_offset(&source, offset),
                    format!("production caller bypasses the Rust tracking-issue facade: {token}"),
                ));
            }
        }
        let compact: String = source
            .chars()
            .filter(|character| !character.is_whitespace())
            .collect();
        for token in [
            "_invoke_cli([\"tracking-issue\"",
            "_invoke_cli(['tracking-issue'",
        ] {
            if let Some(offset) = compact.find(token) {
                let compact_character_offset = compact[..offset].chars().count();
                findings.push(Finding::new(
                    relative,
                    line_for_compact_offset(&source, compact_character_offset),
                    "production caller routes a retired tracking command through python/cli.py",
                ));
            }
        }
    }
    let facade_path = RepoPath::from_trusted(RUST_RUNTIME_FACADE);
    if repository.paths().binary_search(&facade_path).is_ok() {
        let source = repository.read_utf8(&facade_path)?;
        for wrapper in TRACKING_RUNTIME_WRAPPERS {
            if !source.contains(wrapper) {
                findings.push(Finding::new(
                    RUST_RUNTIME_FACADE,
                    1,
                    format!("missing typed tracking-issue runtime wrapper: {wrapper}"),
                ));
            }
        }
        for owner_token in ["larch_entrypoint(", "\"tracking-issue\""] {
            if !source.contains(owner_token) {
                findings.push(Finding::new(
                    RUST_RUNTIME_FACADE,
                    1,
                    format!("tracking-issue runtime facade lost its verified owner: {owner_token}"),
                ));
            }
        }
    } else {
        findings.push(Finding::new(
            RUST_RUNTIME_FACADE,
            1,
            "missing typed tracking-issue runtime facade",
        ));
    }
    Ok(())
}

fn line_for_offset(source: &str, offset: usize) -> u32 {
    source[..offset]
        .bytes()
        .filter(|byte| *byte == b'\n')
        .count()
        .saturating_add(1)
        .try_into()
        .unwrap_or(u32::MAX)
}

fn line_for_compact_offset(source: &str, compact_offset: usize) -> u32 {
    let byte_offset = source
        .char_indices()
        .filter(|(_, character)| !character.is_whitespace())
        .nth(compact_offset)
        .map_or(source.len(), |(offset, _)| offset);
    line_for_offset(source, byte_offset)
}

fn is_in_scope_row(value: &Value) -> bool {
    let Some(command) = RegistryCommand::parse(value) else {
        return false;
    };
    expected_command(command.domain, command.verb).is_some()
        || handoff_command(command.domain, command.verb).is_some()
        || command.integer("planning_issue") == Some(UMBRELLA_ISSUE)
}

fn expected_command(domain: &str, verb: &str) -> Option<&'static ExpectedCommand> {
    EXPECTED_COMMANDS
        .iter()
        .find(|command| command.matches(domain, verb))
}

fn handoff_command(domain: &str, verb: &str) -> Option<&'static HandoffCommand> {
    HANDOFF_COMMANDS
        .iter()
        .find(|command| command.domain == domain && command.verb == verb)
}

fn check_registry_rows(commands: &[Value], findings: &mut Vec<Finding>) {
    let mut found = BTreeSet::new();
    let mut handoffs = BTreeSet::new();
    for command in commands.iter().filter_map(RegistryCommand::parse) {
        if let Some(expected) = expected_command(command.domain, command.verb) {
            found.insert(command.selector.clone());
            if !command.has_final_cutover() {
                findings.push(registry_finding(format!(
                    "non-final issue-domain command row: {}; expected Rust ownership with complete parity, cutover, and Python removal",
                    command.selector
                )));
            }
            if command.integer("migration_issue") != Some(expected.migration_issue) {
                findings.push(registry_finding(format!(
                    "issue-domain migration leaf drift: {}; expected #{}",
                    command.selector,
                    expected.migration_issue
                )));
            }
            if command.integer("planning_issue") != Some(expected.planning_issue) {
                findings.push(registry_finding(format!(
                    "issue-domain planning owner drift: {}; expected #{}",
                    command.selector,
                    expected.planning_issue
                )));
            }
            if command.text("python_module") != Some(expected.python_module)
                || command.text("python_function") != Some(expected.python_function)
            {
                findings.push(registry_finding(format!(
                    "issue-domain retired Python target drift: {}; expected {}.{}",
                    command.selector,
                    expected.python_module, expected.python_function
                )));
            }
            continue;
        }
        if let Some(handoff) = handoff_command(command.domain, command.verb) {
            handoffs.insert(command.selector.clone());
            if command.integer("planning_issue") != Some(handoff.planning_issue) {
                findings.push(registry_finding(format!(
                    "issue-domain hand-off drift: {}; expected #{}",
                    command.selector,
                    handoff.planning_issue
                )));
            }
            continue;
        }
        if command.integer("planning_issue") == Some(UMBRELLA_ISSUE) {
            findings.push(registry_finding(format!(
                "unclosed #{UMBRELLA_ISSUE} ledger row: {}; name the umbrella that owns its migration",
                command.selector
            )));
        }
    }
    for expected in EXPECTED_COMMANDS {
        let selector = expected.selector();
        if !found.contains(&selector) {
            findings.push(registry_finding(format!(
                "missing final issue-domain command row: {selector}"
            )));
        }
    }
    for handoff in HANDOFF_COMMANDS {
        let selector = handoff.selector();
        if !handoffs.contains(&selector) {
            findings.push(registry_finding(format!(
                "missing issue-domain hand-off row: {selector}"
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
        &|domain, verb| expected_command(domain, verb).is_some(),
        &|domain, verb| {
            format!("issue-domain command remains registered in Python: {domain} {verb}")
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
        .map(ExpectedCommand::retired_python_target)
        .collect();
    check_retired_entrypoints(
        repository,
        &targets,
        &|module, function| {
            format!("superseded issue-domain Python entrypoint remains: {module}.{function}")
        },
        findings,
    )
}

fn check_retained_modules(repository: &Repository, findings: &mut Vec<Finding>) {
    for path in repository.paths() {
        let relative = path.as_str();
        if !is_top_level_issue_module(relative) || relative == PYTHON_ISSUE_INIT {
            continue;
        }
        if retained_module_owner(relative).is_none() {
            findings.push(Finding::new(
                relative,
                1,
                "unowned retained issue-domain Python module; name its receiving umbrella",
            ));
        }
    }
}

fn is_top_level_issue_module(path: &str) -> bool {
    path.strip_prefix(PYTHON_ISSUE_ROOT)
        .is_some_and(|name| {
            Path::new(name)
                .extension()
                .is_some_and(|extension| extension.eq_ignore_ascii_case("py"))
                && !name.contains('/')
        })
}

pub(super) fn retained_module_owner(path: &str) -> Option<i64> {
    RETAINED_MODULES
        .iter()
        .find(|module| module.path == path)
        .map(|module| module.planning_issue)
}

fn registry_finding(message: String) -> Finding {
    Finding::new(COMMAND_REGISTRY_PATH, 1, message)
}

#[cfg(test)]
mod tests {
    use super::{EXPECTED_COMMANDS, HANDOFF_COMMANDS, RETAINED_MODULES};

    #[test]
    fn pins_unique_selectors_and_owned_retained_modules() {
        let mut selectors: Vec<String> = EXPECTED_COMMANDS
            .iter()
            .map(super::ExpectedCommand::selector)
            .collect();
        let total = selectors.len();
        selectors.sort();
        selectors.dedup();
        assert_eq!(selectors.len(), total);

        let mut handoffs: Vec<String> = HANDOFF_COMMANDS
            .iter()
            .map(super::HandoffCommand::selector)
            .collect();
        let handoff_total = handoffs.len();
        handoffs.sort();
        handoffs.dedup();
        assert_eq!(handoffs.len(), handoff_total);
        assert!(RETAINED_MODULES.iter().all(|module| {
            matches!(
                module.planning_issue,
                7679 | 7680 | 7681 | 7684 | 7685
            )
        }));
    }
}
