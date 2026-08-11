//! Effect-free migration-audit snapshot classification and report rendering.
//!
//! Command adapters collect evidence; this module classifies supplied snapshots
//! with the shared migration-governance policy.

use std::{
    collections::{BTreeMap, BTreeSet},
    error::Error,
    fmt,
    sync::LazyLock,
};

use chrono::{DateTime, NaiveDateTime, Utc};
use regex::Regex;
use serde::Serialize;

use crate::{
    BlockerSnapshotRow, GovernanceIssueSnapshot, OwnerAdmissionRequest, ReceiptFreshnessRequest,
    RepositoryName, ScopeSnapshot, audit_stale_implementation_leases, balanced_fence_line_indices,
    compare_blocker_parity, ensure_ascii_json, evaluate_owner_admission, issue_plan_marker_defect,
    normalize_state, parse_named_block, parse_native_blocker_refs,
};

pub const MIGRATION_AUDIT_SCHEMA_VERSION: u64 = 2;

pub const MIGRATION_AUDIT_COUNT_KEYS: [&str; 14] = [
    "executable_leaves",
    "valid_plans",
    "historical_managed_leaves",
    "historical_missing_plan_evidence",
    "historical_unverified_rust_line_budgets",
    "historical_recorded_rust_line_budget_deviations",
    "missing_or_stale_blockers",
    "active_owner_conflicts",
    "stale_implementation_leases",
    "registry_state_violations",
    "missing_caller_surfaces",
    "python_retirement_violations",
    "clean_install_coverage_gaps",
    "production_runtime_escape_hatches",
];

pub const PLAN_DEFECT_TOKENS: [&str; 12] = [
    "missing-plan-block",
    "multiple-plan-blocks",
    "missing-firm-scope",
    "missing-ordered-implementation",
    "missing-acceptance",
    "missing-closed-decisions",
    "missing-breaking-migration",
    "missing-diff-lines",
    "empty-plan-glob",
    "missing-updated-plan-path",
    "existing-new-plan-path",
    "unsafe-plan-path",
];

const RUST_LINE_BUDGET_DEVIATION_HEADING: &str = "## Rust line budget deviation";
const RUST_LINE_BUDGET_SPLIT_DECISION: &str = "retain this leaf as one PR";

static LEAF_TITLE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\[leaf of [#]?[1-9][0-9]*\]").expect("leaf title expression is valid")
});
static DIRECT_LEAF_OPENING_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^This is a leaf of umbrella #([1-9][0-9]*)\. Read the umbrella in full before acting\.$",
    )
    .expect("direct leaf expression is valid")
});
static SECTION_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^(#{2,3})[ \t]+(.+?)[ \t]*$").expect("section expression is valid")
});
static PLAN_HEADING_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^(?:##|###)[ \t]+(?:NEW|UPDATED|REWRITTEN|MAY_UPDATE)(?:[ \t]*:[ \t]*(.+?)|[ \t]+\[([^]\r\n]+)\][ \t]*:?)[ \t]*$",
    )
    .expect("plan heading expression is valid")
});
static NUMBERED_STEP_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[ \t]*\d+\.[ \t]+\S").expect("numbered step expression is valid")
});
static CLOSED_DECISIONS_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^closed[ \t]+decisions(?:[ \t]+and[ \t]+ownership)?$")
        .expect("closed decisions expression is valid")
});
static ORDERED_IMPLEMENTATION_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^ordered[ \t]+implementation$")
        .expect("ordered implementation expression is valid")
});
static BREAKING_MIGRATION_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^breaking[ \t]+changes[ \t]+and[ \t]+migration$")
        .expect("breaking migration expression is valid")
});
static FINDING_ISSUE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\bissue=#([1-9][0-9]*)\b").expect("finding issue expression is valid")
});
static CHIEF_DIRECT_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"chief[ \t]+umbrella:[ \t]*#([1-9][0-9]*)")
        .expect("chief direct expression is valid")
});
static CHIEF_REVERSED_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"#([1-9][0-9]*)[ \t]+chief[ \t]+umbrella")
        .expect("chief reversed expression is valid")
});
static PARENT_CHIEF_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"#([1-9][0-9]*)[^\r\n]{0,160}\[chief[ \t]+umbrella\]")
        .expect("parent chief expression is valid")
});

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MigrationIssueSnapshot {
    pub number: u64,
    pub title: String,
    pub state: String,
    pub body: String,
    pub updated_at: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DependencySnapshot {
    pub issue: u64,
    pub blockers: Vec<u64>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PlanAuditEvidence {
    pub issue: u64,
    pub defects: Vec<String>,
    pub base_scope: Option<ScopeSnapshot>,
    pub head_scope: Option<ScopeSnapshot>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MigrationAuditSnapshot {
    pub repository: String,
    pub chief_issue: u64,
    pub snapshot_timestamp: String,
    pub head_sha: String,
    pub open_issues: Vec<MigrationIssueSnapshot>,
    pub referenced_issues: Vec<MigrationIssueSnapshot>,
    pub dependencies: Vec<DependencySnapshot>,
    pub open_pr_branches: Vec<String>,
    pub closed_issues: Vec<MigrationIssueSnapshot>,
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum RepositoryFindingSource {
    CommandRegistry,
    ProductionRuntime,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RepositoryAuditFinding {
    pub source: RepositoryFindingSource,
    pub reason: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MigrationAuditRequest {
    pub snapshot: MigrationAuditSnapshot,
    pub plans: Vec<PlanAuditEvidence>,
    pub repository_findings: Vec<RepositoryAuditFinding>,
}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize)]
pub struct CommandAuditKey {
    pub domain: String,
    pub verb: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct CommandAuditIssue {
    pub command: Option<CommandAuditKey>,
    pub executable_leaf: bool,
    pub number: u64,
    pub plan_commands: Vec<CommandAuditKey>,
    pub state: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RustLineBudgetDeviation {
    pub split_decision: String,
    pub rationale: String,
    pub base_sha: String,
    pub head_sha: String,
    pub added_lines: u64,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RustLineBudgetDeviationParse {
    pub deviation: Option<RustLineBudgetDeviation>,
    pub defects: Vec<String>,
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum FindingCategory {
    InvalidPlan,
    MissingOrStaleBlocker,
    OwnerAdmission,
    ActiveOwnerConflict,
    StaleImplementationLease,
    RegistryStateViolation,
    MissingCallerSurface,
    PythonRetirementViolation,
    CleanInstallCoverageGap,
    ProductionRuntimeEscapeHatch,
}

impl FindingCategory {
    const fn order(self) -> u8 {
        self as u8
    }
}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize)]
pub struct AggregateFinding {
    pub category: FindingCategory,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cleanup_command: Option<String>,
    pub issue: Option<u64>,
    pub reason: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct IssueAuditEvidence {
    pub finding_reasons: Vec<String>,
    pub number: u64,
    pub plan_valid: Option<bool>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MigrationAuditReport {
    pub repository: String,
    pub chief_issue: u64,
    pub snapshot_timestamp: String,
    pub counts: Vec<(&'static str, u64)>,
    pub findings: Vec<AggregateFinding>,
    pub issues: Vec<IssueAuditEvidence>,
}

#[derive(Serialize)]
struct AuditJson<'a> {
    chief_issue: u64,
    counts: BTreeMap<&'static str, u64>,
    findings: &'a [AggregateFinding],
    issues: &'a [IssueAuditEvidence],
    repository: &'a str,
    schema_version: u64,
    snapshot_timestamp: &'a str,
}

#[derive(Serialize)]
struct CommandAuditInput<'a> {
    issues: Vec<&'a CommandAuditIssue>,
    rollout_enabled: bool,
    schema_version: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct MigrationAuditDefect(&'static str);

impl MigrationAuditDefect {
    pub const INVALID_REPOSITORY: Self = Self("invalid-migration-audit-repository");
    pub const INVALID_CHIEF_ISSUE: Self = Self("invalid-migration-audit-chief");
    pub const INVALID_SNAPSHOT_TIMESTAMP: Self = Self("invalid-migration-audit-timestamp");
    pub const INVALID_SNAPSHOT_HEAD: Self = Self("invalid-migration-audit-head");
    pub const INVALID_ISSUE_SNAPSHOT: Self = Self("invalid-migration-audit-issue");
    pub const DUPLICATE_ISSUE_SNAPSHOT: Self = Self("duplicate-migration-audit-issue");
    pub const INVALID_DEPENDENCY_SNAPSHOT: Self = Self("invalid-migration-audit-dependency");
    pub const DUPLICATE_DEPENDENCY_SNAPSHOT: Self = Self("duplicate-migration-audit-dependency");
    pub const MISSING_DEPENDENCY_SNAPSHOT: Self = Self("missing-migration-audit-dependency");
    pub const INVALID_PLAN_EVIDENCE: Self = Self("invalid-migration-audit-plan-evidence");
    pub const DUPLICATE_PLAN_EVIDENCE: Self = Self("duplicate-migration-audit-plan-evidence");
    pub const MISSING_PLAN_EVIDENCE: Self = Self("missing-migration-audit-plan-evidence");
    pub const UNEXPECTED_PLAN_EVIDENCE: Self = Self("unexpected-migration-audit-plan-evidence");
    pub const INVALID_REPOSITORY_FINDING: Self = Self("invalid-migration-audit-repository-finding");
    pub const DUPLICATE_COMMAND_AUDIT_ISSUE: Self = Self("duplicate-command-audit-issue");
    pub const INVALID_COMMAND_AUDIT_ISSUE: Self = Self("invalid-command-audit-issue");
    pub const MISSING_REFERENCED_ISSUE: Self = Self("missing-migration-audit-referenced-issue");

    #[must_use]
    pub const fn reason(self) -> &'static str {
        self.0
    }
}

impl fmt::Display for MigrationAuditDefect {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.reason())
    }
}

impl Error for MigrationAuditDefect {}

/// Build the deterministic schema-v2 report from one fully collected snapshot.
///
/// # Errors
///
/// Returns [`MigrationAuditDefect`] when the supplied snapshot cannot prove a
/// complete, unambiguous audit.
pub fn build_migration_audit_report(
    request: &MigrationAuditRequest,
) -> Result<MigrationAuditReport, MigrationAuditDefect> {
    let repository = RepositoryName::parse(request.snapshot.repository.clone())
        .map_err(|_| MigrationAuditDefect::INVALID_REPOSITORY)?;
    if request.snapshot.chief_issue == 0 {
        return Err(MigrationAuditDefect::INVALID_CHIEF_ISSUE);
    }
    if !sha1_hex(&request.snapshot.head_sha) {
        return Err(MigrationAuditDefect::INVALID_SNAPSHOT_HEAD);
    }
    let now = parse_snapshot_time(&request.snapshot.snapshot_timestamp)?;
    let normalized = normalize_snapshot_issues(&request.snapshot)?;
    let executable = executable_leaves(&normalized.open, request.snapshot.chief_issue);
    let plan_evidence = plan_evidence_by_issue(&request.plans, &executable)?;
    let dependencies = dependency_rows_by_issue(&request.snapshot.dependencies, &executable)?;
    validate_repository_findings(&request.repository_findings)?;

    let issue_map = normalized.issue_map;
    let active = governance_issues(&normalized.open);
    let sources = governance_issues(issue_map.values());
    let mut findings = classify_repository_findings(&request.repository_findings);
    let mut plan_validity = audit_current_leaves(
        &executable,
        &CurrentAudit {
            plan_evidence: &plan_evidence,
            dependencies: &dependencies,
            issue_map: &issue_map,
            active: &active,
            sources: &sources,
            repository: &repository,
            now,
        },
        &mut findings,
    )?;

    let historical =
        historical_leaves(&normalized.closed, &issue_map, request.snapshot.chief_issue);
    let historical_evidence = historical_evidence(&historical);
    for (number, valid) in &historical_evidence.plan_validity {
        let _ = plan_validity.insert(*number, *valid);
    }

    findings.extend(
        audit_stale_implementation_leases(
            &repository,
            &active,
            &request.snapshot.open_pr_branches,
            now,
        )
        .into_iter()
        .map(|finding| AggregateFinding {
            category: FindingCategory::StaleImplementationLease,
            issue: finding_issue_number(&finding.token),
            reason: finding.token,
            cleanup_command: Some(finding.cleanup_command),
        }),
    );

    let findings = ordered_findings(findings);
    let counts = count_rows(
        &executable,
        &plan_validity,
        &historical,
        &historical_evidence,
        &findings,
    );
    let issues = issue_evidence(&plan_validity, &historical_evidence.reasons, &findings);
    Ok(MigrationAuditReport {
        repository: repository.as_str().to_owned(),
        chief_issue: request.snapshot.chief_issue,
        snapshot_timestamp: request.snapshot.snapshot_timestamp.clone(),
        counts,
        findings,
        issues,
    })
}

/// Render compact, key-sorted schema-v2 JSON compatible with Python's renderer.
#[must_use]
pub fn render_migration_audit_json(report: &MigrationAuditReport) -> String {
    compact_json(&AuditJson {
        chief_issue: report.chief_issue,
        counts: report.counts.iter().copied().collect(),
        findings: &report.findings,
        issues: &report.issues,
        repository: &report.repository,
        schema_version: MIGRATION_AUDIT_SCHEMA_VERSION,
        snapshot_timestamp: &report.snapshot_timestamp,
    }) + "\n"
}

/// Render the concise human count table.
#[must_use]
pub fn render_migration_audit_table(report: &MigrationAuditReport) -> String {
    let labels = report
        .counts
        .iter()
        .map(|(key, _)| (*key, key.replace('_', " ")))
        .collect::<Vec<_>>();
    let width = labels
        .iter()
        .map(|(_, label)| label.len())
        .max()
        .unwrap_or_default();
    let mut lines = vec!["Migration governance audit".to_owned(), String::new()];
    lines.extend(
        report
            .counts
            .iter()
            .zip(labels)
            .map(|((_, value), (_, label))| format!("{label:width$}  {value}")),
    );
    lines.join("\n") + "\n"
}

/// Build one typed command-registry audit row from canonical issue evidence.
///
/// # Errors
///
/// Returns [`MigrationAuditDefect::INVALID_COMMAND_AUDIT_ISSUE`] for an invalid
/// issue number or state.
pub fn build_command_audit_issue(
    issue: &MigrationIssueSnapshot,
    executable_leaf: bool,
    registry_commands: &[CommandAuditKey],
) -> Result<CommandAuditIssue, MigrationAuditDefect> {
    let state = normalize_state(&issue.state);
    if issue.number == 0 || !matches!(state.as_str(), "open" | "closed") {
        return Err(MigrationAuditDefect::INVALID_COMMAND_AUDIT_ISSUE);
    }
    let parsed_owner = crate::parse_owner_block(&issue.body);
    let command = parsed_owner.block.map(|block| CommandAuditKey {
        domain: block.domain,
        verb: block.verb,
    });
    let plan_commands = parse_named_block(&issue.body, crate::PLAN_MARKER)
        .ok()
        .flatten()
        .map_or_else(Vec::new, |plan| {
            registry_commands
                .iter()
                .filter(|selector| plan_mentions_command(&plan, selector))
                .cloned()
                .collect::<BTreeSet<_>>()
                .into_iter()
                .collect()
        });
    Ok(CommandAuditIssue {
        number: issue.number,
        state,
        executable_leaf,
        command,
        plan_commands,
    })
}

/// Render stable schema-v1 JSON for `command-registry audit`.
///
/// # Errors
///
/// Returns [`MigrationAuditDefect::DUPLICATE_COMMAND_AUDIT_ISSUE`] when rows are
/// not uniquely keyed by issue number.
pub fn render_command_audit_input(
    rows: &[CommandAuditIssue],
    rollout_enabled: bool,
) -> Result<String, MigrationAuditDefect> {
    let mut by_number = BTreeMap::new();
    for row in rows {
        if by_number.insert(row.number, row).is_some() {
            return Err(MigrationAuditDefect::DUPLICATE_COMMAND_AUDIT_ISSUE);
        }
    }
    Ok(compact_json(&CommandAuditInput {
        issues: by_number.into_values().collect(),
        rollout_enabled,
        schema_version: 1,
    }) + "\n")
}

/// Parse the optional durable Rust-line-budget deviation section.
#[must_use]
pub fn parse_rust_line_budget_deviation(plan_inner: &str) -> RustLineBudgetDeviationParse {
    let lines = crate::split_text_lines(plan_inner);
    let fenced = balanced_fence_line_indices(&lines);
    let headings = lines
        .iter()
        .enumerate()
        .filter_map(|(index, line)| {
            (!fenced.contains(&index) && *line == RUST_LINE_BUDGET_DEVIATION_HEADING)
                .then_some(index)
        })
        .collect::<Vec<_>>();
    if headings.is_empty() {
        return RustLineBudgetDeviationParse {
            deviation: None,
            defects: Vec::new(),
        };
    }
    if headings.len() != 1 {
        return RustLineBudgetDeviationParse {
            deviation: None,
            defects: vec!["multiple-rust-line-budget-deviations".to_owned()],
        };
    }
    let start = headings[0] + 1;
    let end = (start..lines.len())
        .find(|index| !fenced.contains(index) && lines[*index].starts_with("## "))
        .unwrap_or(lines.len());
    let fields = budget_fields(&lines[start..end], &fenced, start);
    let Some([split_decision, rationale, base_sha, head_sha, added_lines]) = fields else {
        return malformed_budget();
    };
    if split_decision != RUST_LINE_BUDGET_SPLIT_DECISION
        || crate::trim_python_whitespace(&rationale).is_empty()
        || !sha1_hex(&base_sha)
        || !sha1_hex(&head_sha)
        || !nonnegative_decimal(&added_lines)
    {
        return malformed_budget();
    }
    let Ok(added_lines) = added_lines.parse() else {
        return malformed_budget();
    };
    RustLineBudgetDeviationParse {
        deviation: Some(RustLineBudgetDeviation {
            split_decision,
            rationale,
            base_sha,
            head_sha,
            added_lines,
        }),
        defects: Vec::new(),
    }
}

/// Validate M1 plan facets without repository or filesystem access.
#[must_use]
pub fn validate_plan_facets(plan: &str) -> Vec<String> {
    let mut defects = BTreeSet::new();
    let lines = crate::split_text_lines(plan);
    let fenced = balanced_fence_line_indices(&lines);
    if !lines
        .iter()
        .enumerate()
        .any(|(index, line)| !fenced.contains(&index) && firm_plan_heading(line))
    {
        let _ = defects.insert("missing-firm-scope");
    }
    let sections = sections(&lines, &fenced);
    for (defect, expression) in [
        ("missing-closed-decisions", &*CLOSED_DECISIONS_RE),
        ("missing-breaking-migration", &*BREAKING_MIGRATION_RE),
    ] {
        if !section_has(&sections, expression, |line| {
            !crate::trim_python_whitespace(line).is_empty()
        }) {
            let _ = defects.insert(defect);
        }
    }
    if !section_has(&sections, &ORDERED_IMPLEMENTATION_RE, |line| {
        NUMBERED_STEP_RE.is_match(line)
    }) {
        let _ = defects.insert("missing-ordered-implementation");
    }
    if !sections.iter().any(|section| {
        section.title == "acceptance"
            && section
                .body
                .iter()
                .any(|line| !crate::trim_python_whitespace(line).is_empty())
    }) {
        let _ = defects.insert("missing-acceptance");
    }
    if crate::terminal_diff_lines(plan).is_none() {
        let _ = defects.insert("missing-diff-lines");
    }
    PLAN_DEFECT_TOKENS
        .iter()
        .filter(|token| defects.contains(*token))
        .map(|token| (*token).to_owned())
        .collect()
}

struct NormalizedSnapshot {
    open: Vec<MigrationIssueSnapshot>,
    closed: Vec<MigrationIssueSnapshot>,
    issue_map: BTreeMap<u64, MigrationIssueSnapshot>,
}

struct HistoricalEvidence {
    plan_validity: BTreeMap<u64, bool>,
    reasons: BTreeMap<u64, Vec<String>>,
    recorded_deviations: u64,
}

struct CurrentAudit<'a> {
    plan_evidence: &'a BTreeMap<u64, PlanAuditEvidence>,
    dependencies: &'a BTreeMap<u64, Vec<u64>>,
    issue_map: &'a BTreeMap<u64, MigrationIssueSnapshot>,
    active: &'a [GovernanceIssueSnapshot],
    sources: &'a [GovernanceIssueSnapshot],
    repository: &'a RepositoryName,
    now: DateTime<Utc>,
}

struct PlanSection<'a> {
    title: String,
    body: Vec<&'a str>,
}

fn section_has(
    sections: &[PlanSection<'_>],
    expression: &Regex,
    predicate: impl Fn(&str) -> bool,
) -> bool {
    sections.iter().any(|section| {
        expression.is_match(&section.title) && section.body.iter().any(|line| predicate(line))
    })
}

fn audit_current_leaves(
    leaves: &[MigrationIssueSnapshot],
    context: &CurrentAudit<'_>,
    findings: &mut Vec<AggregateFinding>,
) -> Result<BTreeMap<u64, bool>, MigrationAuditDefect> {
    let mut validity = BTreeMap::new();
    for leaf in leaves {
        let evidence = context
            .plan_evidence
            .get(&leaf.number)
            .ok_or(MigrationAuditDefect::MISSING_PLAN_EVIDENCE)?;
        let _ = validity.insert(leaf.number, evidence.defects.is_empty());
        findings.extend(
            evidence
                .defects
                .iter()
                .cloned()
                .map(|reason| AggregateFinding {
                    category: FindingCategory::InvalidPlan,
                    cleanup_command: None,
                    issue: Some(leaf.number),
                    reason,
                }),
        );

        let native = context
            .dependencies
            .get(&leaf.number)
            .ok_or(MigrationAuditDefect::MISSING_DEPENDENCY_SNAPSHOT)?;
        let body = parse_native_blocker_refs(&leaf.body);
        let all_rows = blocker_rows(native, &body, context.issue_map)?;
        let rows = all_rows
            .iter()
            .map(|row| (row.number, row.clone()))
            .collect::<BTreeMap<_, _>>();
        let parity = compare_blocker_parity(
            &rows_for_numbers(&body, &rows)?,
            &rows_for_numbers(native, &rows)?,
        );
        let freshness = crate::validate_receipt_freshness(&ReceiptFreshnessRequest {
            body: leaf.body.clone(),
            blocker_rows: all_rows,
            base_scope: evidence.base_scope.clone(),
            head_scope: evidence.head_scope.clone(),
        });
        findings.extend(
            parity
                .reasons
                .into_iter()
                .chain(freshness.reasons)
                .map(|reason| AggregateFinding {
                    category: FindingCategory::MissingOrStaleBlocker,
                    cleanup_command: None,
                    issue: Some(leaf.number),
                    reason,
                }),
        );

        let owners = evaluate_owner_admission(&OwnerAdmissionRequest {
            issue: leaf.number,
            body: leaf.body.clone(),
            reuse_sources: context.sources.to_vec(),
            active_issues: Some(context.active.to_vec()),
            open_pr_branches: None,
            now: context.now,
            repository: context.repository.clone(),
        });
        findings.extend(owners.reasons.into_iter().map(|reason| AggregateFinding {
            category: if reason.starts_with("active-owner-conflict ") {
                FindingCategory::ActiveOwnerConflict
            } else {
                FindingCategory::OwnerAdmission
            },
            cleanup_command: None,
            issue: Some(leaf.number),
            reason,
        }));
    }
    Ok(validity)
}

fn normalize_snapshot_issues(
    snapshot: &MigrationAuditSnapshot,
) -> Result<NormalizedSnapshot, MigrationAuditDefect> {
    let open = normalize_issue_group(&snapshot.open_issues, Some("open"))?;
    let closed = normalize_issue_group(&snapshot.closed_issues, Some("closed"))?;
    let referenced = normalize_issue_group(&snapshot.referenced_issues, None)?;
    let mut issue_map = BTreeMap::new();
    for issue in open.iter().chain(&closed).chain(&referenced) {
        if issue_map.insert(issue.number, issue.clone()).is_some() {
            return Err(MigrationAuditDefect::DUPLICATE_ISSUE_SNAPSHOT);
        }
    }
    Ok(NormalizedSnapshot {
        open,
        closed,
        issue_map,
    })
}

fn normalize_issue_group(
    issues: &[MigrationIssueSnapshot],
    expected_state: Option<&str>,
) -> Result<Vec<MigrationIssueSnapshot>, MigrationAuditDefect> {
    let mut normalized = Vec::with_capacity(issues.len());
    for issue in issues {
        let state = normalize_state(&issue.state);
        if issue.number == 0
            || !matches!(state.as_str(), "open" | "closed")
            || expected_state.is_some_and(|expected| state != expected)
        {
            return Err(MigrationAuditDefect::INVALID_ISSUE_SNAPSHOT);
        }
        normalized.push(MigrationIssueSnapshot {
            number: issue.number,
            title: issue.title.clone(),
            state,
            body: issue.body.clone(),
            updated_at: issue.updated_at.clone(),
        });
    }
    normalized.sort_by_key(|issue| issue.number);
    if normalized
        .windows(2)
        .any(|pair| pair[0].number == pair[1].number)
    {
        return Err(MigrationAuditDefect::DUPLICATE_ISSUE_SNAPSHOT);
    }
    Ok(normalized)
}

fn executable_leaves(
    open: &[MigrationIssueSnapshot],
    chief_issue: u64,
) -> Vec<MigrationIssueSnapshot> {
    open.iter()
        .filter(|issue| is_chief_migration_leaf(issue, chief_issue))
        .cloned()
        .collect()
}

fn historical_leaves(
    closed: &[MigrationIssueSnapshot],
    issues: &BTreeMap<u64, MigrationIssueSnapshot>,
    chief_issue: u64,
) -> Vec<MigrationIssueSnapshot> {
    closed
        .iter()
        .filter(|issue| is_historical_chief_leaf(issue, issues, chief_issue))
        .cloned()
        .collect()
}

fn is_chief_migration_leaf(issue: &MigrationIssueSnapshot, chief_issue: u64) -> bool {
    LEAF_TITLE_RE.is_match(&issue.title.to_ascii_lowercase())
        && chief_reference_present(&issue.body, chief_issue)
}

fn is_historical_chief_leaf(
    issue: &MigrationIssueSnapshot,
    issues: &BTreeMap<u64, MigrationIssueSnapshot>,
    chief_issue: u64,
) -> bool {
    is_chief_migration_leaf(issue, chief_issue)
        || direct_parent_umbrella(&issue.body)
            .and_then(|number| issues.get(&number))
            .is_some_and(|parent| parent_declares_chief(&parent.body, chief_issue))
}

fn chief_reference_present(body: &str, chief_issue: u64) -> bool {
    let body = body.to_ascii_lowercase();
    [&*CHIEF_DIRECT_RE, &*CHIEF_REVERSED_RE]
        .into_iter()
        .any(|expression| captures_issue(expression, &body, chief_issue))
}

fn parent_declares_chief(body: &str, chief_issue: u64) -> bool {
    chief_reference_present(body, chief_issue)
        || captures_issue(&PARENT_CHIEF_RE, &body.to_ascii_lowercase(), chief_issue)
}

fn captures_issue(expression: &Regex, text: &str, expected: u64) -> bool {
    expression.captures_iter(text).any(|captures| {
        captures
            .get(1)
            .and_then(|capture| capture.as_str().parse().ok())
            == Some(expected)
    })
}

fn direct_parent_umbrella(body: &str) -> Option<u64> {
    let first = crate::split_text_lines(body).into_iter().next()?;
    DIRECT_LEAF_OPENING_RE
        .captures(first)
        .and_then(|captures| captures.get(1))
        .and_then(|capture| capture.as_str().parse().ok())
}

fn plan_evidence_by_issue(
    evidence: &[PlanAuditEvidence],
    executable: &[MigrationIssueSnapshot],
) -> Result<BTreeMap<u64, PlanAuditEvidence>, MigrationAuditDefect> {
    let executable_numbers = executable
        .iter()
        .map(|issue| issue.number)
        .collect::<BTreeSet<_>>();
    let mut by_issue = BTreeMap::new();
    for row in evidence {
        let found = row
            .defects
            .iter()
            .map(String::as_str)
            .collect::<BTreeSet<_>>();
        if row.issue == 0
            || found.len() != row.defects.len()
            || found
                .iter()
                .any(|defect| !PLAN_DEFECT_TOKENS.contains(defect))
        {
            return Err(MigrationAuditDefect::INVALID_PLAN_EVIDENCE);
        }
        if !executable_numbers.contains(&row.issue) {
            return Err(MigrationAuditDefect::UNEXPECTED_PLAN_EVIDENCE);
        }
        let normalized = PlanAuditEvidence {
            issue: row.issue,
            defects: PLAN_DEFECT_TOKENS
                .iter()
                .filter(|token| found.contains(*token))
                .map(|token| (*token).to_owned())
                .collect(),
            base_scope: row.base_scope.clone(),
            head_scope: row.head_scope.clone(),
        };
        if by_issue.insert(row.issue, normalized).is_some() {
            return Err(MigrationAuditDefect::DUPLICATE_PLAN_EVIDENCE);
        }
    }
    if executable_numbers
        .iter()
        .any(|number| !by_issue.contains_key(number))
    {
        return Err(MigrationAuditDefect::MISSING_PLAN_EVIDENCE);
    }
    Ok(by_issue)
}

fn dependency_rows_by_issue(
    rows: &[DependencySnapshot],
    executable: &[MigrationIssueSnapshot],
) -> Result<BTreeMap<u64, Vec<u64>>, MigrationAuditDefect> {
    let executable_numbers = executable
        .iter()
        .map(|issue| issue.number)
        .collect::<BTreeSet<_>>();
    let mut by_issue = BTreeMap::new();
    for row in rows {
        let blockers = row.blockers.iter().copied().collect::<BTreeSet<_>>();
        if row.issue == 0 || blockers.len() != row.blockers.len() || blockers.contains(&0) {
            return Err(MigrationAuditDefect::INVALID_DEPENDENCY_SNAPSHOT);
        }
        if !executable_numbers.contains(&row.issue) {
            return Err(MigrationAuditDefect::INVALID_DEPENDENCY_SNAPSHOT);
        }
        if by_issue
            .insert(row.issue, blockers.into_iter().collect())
            .is_some()
        {
            return Err(MigrationAuditDefect::DUPLICATE_DEPENDENCY_SNAPSHOT);
        }
    }
    if executable_numbers
        .iter()
        .any(|number| !by_issue.contains_key(number))
    {
        return Err(MigrationAuditDefect::MISSING_DEPENDENCY_SNAPSHOT);
    }
    Ok(by_issue)
}

fn blocker_rows(
    native_numbers: &[u64],
    body_numbers: &[u64],
    issues: &BTreeMap<u64, MigrationIssueSnapshot>,
) -> Result<Vec<BlockerSnapshotRow>, MigrationAuditDefect> {
    native_numbers
        .iter()
        .chain(body_numbers)
        .copied()
        .collect::<BTreeSet<_>>()
        .into_iter()
        .map(|number| {
            let issue = issues
                .get(&number)
                .ok_or(MigrationAuditDefect::MISSING_REFERENCED_ISSUE)?;
            Ok(BlockerSnapshotRow {
                number,
                state: issue.state.clone(),
                updated_at: issue.updated_at.clone(),
            })
        })
        .collect()
}

fn rows_for_numbers(
    numbers: &[u64],
    rows: &BTreeMap<u64, BlockerSnapshotRow>,
) -> Result<Vec<BlockerSnapshotRow>, MigrationAuditDefect> {
    numbers
        .iter()
        .map(|number| {
            rows.get(number)
                .cloned()
                .ok_or(MigrationAuditDefect::MISSING_REFERENCED_ISSUE)
        })
        .collect()
}

fn governance_issues<'a>(
    issues: impl IntoIterator<Item = &'a MigrationIssueSnapshot>,
) -> Vec<GovernanceIssueSnapshot> {
    issues
        .into_iter()
        .map(|issue| GovernanceIssueSnapshot {
            number: issue.number,
            title: issue.title.clone(),
            state: issue.state.clone(),
            body: issue.body.clone(),
        })
        .collect()
}

fn validate_repository_findings(
    findings: &[RepositoryAuditFinding],
) -> Result<(), MigrationAuditDefect> {
    if findings.iter().any(|finding| {
        finding.reason.is_empty()
            || finding.reason.len() > 4096
            || finding.reason.contains(['\r', '\n'])
    }) {
        return Err(MigrationAuditDefect::INVALID_REPOSITORY_FINDING);
    }
    Ok(())
}

fn classify_repository_findings(findings: &[RepositoryAuditFinding]) -> Vec<AggregateFinding> {
    findings
        .iter()
        .map(|finding| AggregateFinding {
            category: match finding.source {
                RepositoryFindingSource::CommandRegistry => {
                    classify_registry_finding(&finding.reason)
                }
                RepositoryFindingSource::ProductionRuntime => {
                    FindingCategory::ProductionRuntimeEscapeHatch
                }
            },
            issue: finding_issue_number(&finding.reason),
            reason: finding.reason.clone(),
            cleanup_command: None,
        })
        .collect()
}

fn classify_registry_finding(reason: &str) -> FindingCategory {
    if reason.contains("clean-install-coverage-missing") {
        FindingCategory::CleanInstallCoverageGap
    } else if reason.contains("python-entrypoint-still-") {
        FindingCategory::PythonRetirementViolation
    } else if reason.starts_with("production caller ")
        || reason.starts_with("ledger caller ")
        || reason.contains("production caller inventory")
    {
        FindingCategory::MissingCallerSurface
    } else {
        FindingCategory::RegistryStateViolation
    }
}

fn finding_issue_number(reason: &str) -> Option<u64> {
    FINDING_ISSUE_RE
        .captures(reason)
        .and_then(|captures| captures.get(1))
        .and_then(|capture| capture.as_str().parse().ok())
}

fn historical_evidence(leaves: &[MigrationIssueSnapshot]) -> HistoricalEvidence {
    let mut evidence = HistoricalEvidence {
        plan_validity: BTreeMap::new(),
        reasons: BTreeMap::new(),
        recorded_deviations: 0,
    };
    for leaf in leaves {
        let defects = historical_plan_defects(&leaf.body);
        let _ = evidence
            .plan_validity
            .insert(leaf.number, defects.is_empty());
        if !defects.is_empty() {
            let _ = evidence.reasons.insert(
                leaf.number,
                vec![format!(
                    "historical-plan-evidence-missing defects={}",
                    defects.join(",")
                )],
            );
            continue;
        }
        let Some(plan) = parse_named_block(&leaf.body, crate::PLAN_MARKER)
            .ok()
            .flatten()
        else {
            let _ = evidence.plan_validity.insert(leaf.number, false);
            let _ = evidence.reasons.insert(
                leaf.number,
                vec!["historical-plan-evidence-missing defects=missing-plan-block".to_owned()],
            );
            continue;
        };
        let budget = parse_rust_line_budget_deviation(&plan);
        if budget.deviation.is_some() && budget.defects.is_empty() {
            evidence.recorded_deviations += 1;
            continue;
        }
        let mut reason = "historical-rust-line-budget-unverified".to_owned();
        if !budget.defects.is_empty() {
            reason.push_str(" defects=");
            reason.push_str(&budget.defects.join(","));
        }
        let _ = evidence.reasons.insert(leaf.number, vec![reason]);
    }
    evidence
}

fn historical_plan_defects(body: &str) -> Vec<String> {
    if let Some(defect) = issue_plan_marker_defect(body) {
        return vec![defect.to_owned()];
    }
    parse_named_block(body, crate::PLAN_MARKER)
        .ok()
        .flatten()
        .map_or_else(
            || vec!["missing-plan-block".to_owned()],
            |plan| validate_plan_facets(&plan),
        )
}

fn ordered_findings(findings: Vec<AggregateFinding>) -> Vec<AggregateFinding> {
    let mut ordered = findings
        .into_iter()
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect::<Vec<_>>();
    ordered.sort_by(|left, right| finding_sort_key(left).cmp(&finding_sort_key(right)));
    ordered
}

fn finding_sort_key(finding: &AggregateFinding) -> (u8, u64, &str, &str) {
    (
        finding.category.order(),
        finding.issue.unwrap_or_default(),
        &finding.reason,
        finding.cleanup_command.as_deref().unwrap_or_default(),
    )
}

fn count_rows(
    executable: &[MigrationIssueSnapshot],
    plan_validity: &BTreeMap<u64, bool>,
    historical: &[MigrationIssueSnapshot],
    historical_evidence: &HistoricalEvidence,
    findings: &[AggregateFinding],
) -> Vec<(&'static str, u64)> {
    // These slots are the frozen order in `MIGRATION_AUDIT_COUNT_KEYS`.
    let mut counts = [0_u64; MIGRATION_AUDIT_COUNT_KEYS.len()];
    counts[0] = executable.len() as u64;
    counts[1] = executable
        .iter()
        .filter(|leaf| plan_validity.get(&leaf.number) == Some(&true))
        .count() as u64;
    counts[2] = historical.len() as u64;
    counts[3] = historical_reason_count(
        &historical_evidence.reasons,
        "historical-plan-evidence-missing",
    );
    counts[4] = historical_reason_count(
        &historical_evidence.reasons,
        "historical-rust-line-budget-unverified",
    );
    counts[5] = historical_evidence.recorded_deviations;
    for finding in findings {
        if let Some(index) = finding_count_index(finding.category) {
            counts[index] += 1;
        }
    }
    MIGRATION_AUDIT_COUNT_KEYS.into_iter().zip(counts).collect()
}

const fn finding_count_index(category: FindingCategory) -> Option<usize> {
    match category {
        FindingCategory::MissingOrStaleBlocker => Some(6),
        FindingCategory::ActiveOwnerConflict => Some(7),
        FindingCategory::StaleImplementationLease => Some(8),
        FindingCategory::RegistryStateViolation => Some(9),
        FindingCategory::MissingCallerSurface => Some(10),
        FindingCategory::PythonRetirementViolation => Some(11),
        FindingCategory::CleanInstallCoverageGap => Some(12),
        FindingCategory::ProductionRuntimeEscapeHatch => Some(13),
        FindingCategory::InvalidPlan | FindingCategory::OwnerAdmission => None,
    }
}

fn historical_reason_count(reasons: &BTreeMap<u64, Vec<String>>, prefix: &str) -> u64 {
    reasons
        .values()
        .flatten()
        .filter(|reason| reason.starts_with(prefix))
        .count() as u64
}

fn issue_evidence(
    plan_validity: &BTreeMap<u64, bool>,
    historical_reasons: &BTreeMap<u64, Vec<String>>,
    findings: &[AggregateFinding],
) -> Vec<IssueAuditEvidence> {
    let numbers = plan_validity
        .keys()
        .copied()
        .chain(findings.iter().filter_map(|finding| finding.issue))
        .collect::<BTreeSet<_>>();
    numbers
        .into_iter()
        .map(|number| IssueAuditEvidence {
            number,
            plan_valid: plan_validity.get(&number).copied(),
            finding_reasons: findings
                .iter()
                .filter(|finding| finding.issue == Some(number))
                .map(|finding| finding.reason.clone())
                .chain(
                    historical_reasons
                        .get(&number)
                        .into_iter()
                        .flatten()
                        .cloned(),
                )
                .collect(),
        })
        .collect()
}

fn compact_json(value: &impl Serialize) -> String {
    let rendered = serde_json::to_string(value).expect("composed migration audit JSON is valid");
    ensure_ascii_json(&rendered)
}

fn plan_mentions_command(plan: &str, selector: &CommandAuditKey) -> bool {
    plan.match_indices(&selector.domain).any(|(start, _)| {
        let bytes = plan.as_bytes();
        if start
            .checked_sub(1)
            .and_then(|index| bytes.get(index))
            .is_some_and(|byte| command_word_byte(*byte))
        {
            return false;
        }
        let between = &bytes[start + selector.domain.len()..];
        let spaces = between
            .iter()
            .take_while(|byte| matches!(byte, b' ' | b'\t'))
            .count();
        let verb_start = start + selector.domain.len() + spaces;
        spaces != 0
            && plan[verb_start..].starts_with(&selector.verb)
            && !bytes
                .get(verb_start + selector.verb.len())
                .is_some_and(|byte| command_word_byte(*byte))
    })
}

const fn command_word_byte(byte: u8) -> bool {
    byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-'
}

fn budget_fields(lines: &[&str], fenced: &BTreeSet<usize>, offset: usize) -> Option<[String; 5]> {
    const PREFIXES: [(&str, usize); 5] = [
        ("- Split decision: ", 0),
        ("- Rationale: ", 1),
        ("- Base SHA: ", 2),
        ("- Head SHA: ", 3),
        ("- Added non-generated Rust lines: ", 4),
    ];
    let mut values = [Vec::new(), Vec::new(), Vec::new(), Vec::new(), Vec::new()];
    for (index, line) in lines.iter().enumerate() {
        if fenced.contains(&(offset + index)) {
            continue;
        }
        for (prefix, field) in PREFIXES {
            if let Some(value) = line.strip_prefix(prefix) {
                values[field].push(crate::trim_python_whitespace(value).to_owned());
                break;
            }
        }
    }
    Some([
        one_value(&mut values[0])?,
        one_value(&mut values[1])?,
        one_value(&mut values[2])?,
        one_value(&mut values[3])?,
        one_value(&mut values[4])?,
    ])
}

fn one_value(values: &mut Vec<String>) -> Option<String> {
    (values.len() == 1).then(|| values.pop()).flatten()
}

fn malformed_budget() -> RustLineBudgetDeviationParse {
    RustLineBudgetDeviationParse {
        deviation: None,
        defects: vec!["malformed-rust-line-budget-deviation".to_owned()],
    }
}

fn firm_plan_heading(line: &str) -> bool {
    PLAN_HEADING_RE.is_match(line)
        && matches!(
            line.split_whitespace()
                .nth(1)
                .map(|kind| kind.trim_end_matches(':')),
            Some("NEW" | "UPDATED" | "REWRITTEN")
        )
}

fn sections<'a>(lines: &[&'a str], fenced: &BTreeSet<usize>) -> Vec<PlanSection<'a>> {
    let headings = lines
        .iter()
        .enumerate()
        .filter(|(index, _)| !fenced.contains(index))
        .filter_map(|(index, line)| {
            let captures = SECTION_RE.captures(line)?;
            let level = captures.get(1)?.as_str().len();
            let title =
                crate::trim_python_whitespace(captures.get(2)?.as_str()).to_ascii_lowercase();
            Some((index, level, title))
        })
        .collect::<Vec<_>>();
    headings
        .iter()
        .enumerate()
        .map(|(position, (start, level, title))| {
            let end = headings[position + 1..]
                .iter()
                .find(|(_, later_level, _)| later_level <= level)
                .map_or(lines.len(), |(index, _, _)| *index);
            PlanSection {
                title: title.clone(),
                body: lines[start + 1..end].to_vec(),
            }
        })
        .collect()
}

fn parse_snapshot_time(value: &str) -> Result<DateTime<Utc>, MigrationAuditDefect> {
    NaiveDateTime::parse_from_str(value, "%Y-%m-%dT%H:%M:%SZ")
        .map(|time| time.and_utc())
        .map_err(|_| MigrationAuditDefect::INVALID_SNAPSHOT_TIMESTAMP)
}

fn sha1_hex(value: &str) -> bool {
    value.len() == 40
        && value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

fn nonnegative_decimal(value: &str) -> bool {
    value == "0"
        || (!value.starts_with('0')
            && !value.is_empty()
            && value.bytes().all(|byte| byte.is_ascii_digit()))
}
