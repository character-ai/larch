//! Golden fixtures for the pure migration-audit report core.

use larch_core::{
    CommandAuditKey, DONE_PREFIX, DependencySnapshot, ImplementationLease, MigrationAuditDefect,
    MigrationAuditRequest, MigrationAuditSnapshot, MigrationIssueSnapshot, PlanAuditEvidence,
    PlanReceipt, RepositoryAuditFinding, RepositoryFindingSource, RustLineBudgetDeviation,
    ScopeFile, ScopeSnapshot, build_command_audit_issue, build_migration_audit_report,
    compose_named_block, hash_blocker_rows, hash_owner_rows, hash_plan_block,
    parse_rust_line_budget_deviation, render_command_audit_input, render_migration_audit_json,
    render_migration_audit_table, upsert_implementation_lease, upsert_receipt,
    validate_plan_facets,
};

const TIME: &str = "2026-07-19T12:00:00Z";

fn head() -> String {
    "a".repeat(40)
}
fn plan() -> String {
    "## Plan\n\n### Closed decisions and ownership\n\n- Use the existing validator.\n\n### Ordered implementation\n\n1. Compose the report.\n\n## Files to modify/create\n\n### UPDATED: README.md\n\n## Acceptance\n\n- The report is stable.\n\n## Breaking changes and migration\n\nNone.\n\ndiff_lines: 10\n".to_owned()
}
fn scope() -> ScopeSnapshot {
    ScopeSnapshot {
        sha: head(),
        files: vec![ScopeFile {
            path: "README.md".into(),
            object_id: head(),
        }],
    }
}
fn issue(number: u64, title: &str, state: &str, body: impl Into<String>) -> MigrationIssueSnapshot {
    MigrationIssueSnapshot {
        number,
        title: title.into(),
        state: state.into(),
        body: body.into(),
        updated_at: TIME.into(),
    }
}
fn leaf(number: u64) -> MigrationIssueSnapshot {
    let inner = plan();
    let receipt = PlanReceipt {
        plan_sha256: hash_plan_block(&inner),
        base_sha: head(),
        blockers_sha256: hash_blocker_rows(&[]),
        owners_sha256: hash_owner_rows(&[]),
    };
    issue(
        number,
        &format!("[LEAF OF 7779] Fixture {number}"),
        "open",
        upsert_receipt(
            &format!(
                "Chief umbrella: #7687.\nNative blockers: none.\n{}",
                compose_named_block("plan", &inner)
            ),
            &receipt,
        )
        .unwrap(),
    )
}
fn evidence(issue: u64, defects: &[&str]) -> PlanAuditEvidence {
    PlanAuditEvidence {
        issue,
        defects: defects.iter().map(|value| (*value).into()).collect(),
        base_scope: Some(scope()),
        head_scope: Some(scope()),
    }
}
fn dependencies(numbers: &[u64]) -> Vec<DependencySnapshot> {
    numbers
        .iter()
        .map(|issue| DependencySnapshot {
            issue: *issue,
            blockers: vec![],
        })
        .collect()
}
fn snapshot(
    open_issues: Vec<MigrationIssueSnapshot>,
    dependencies: Vec<DependencySnapshot>,
    closed_issues: Vec<MigrationIssueSnapshot>,
) -> MigrationAuditSnapshot {
    MigrationAuditSnapshot {
        repository: "owner/repo".into(),
        chief_issue: 7687,
        snapshot_timestamp: TIME.into(),
        head_sha: head(),
        open_issues,
        referenced_issues: vec![],
        dependencies,
        open_pr_branches: vec![],
        closed_issues,
    }
}
const fn request(
    snapshot: MigrationAuditSnapshot,
    plans: Vec<PlanAuditEvidence>,
) -> MigrationAuditRequest {
    MigrationAuditRequest {
        snapshot,
        plans,
        repository_findings: vec![],
    }
}
fn closed(number: u64, label: &str, body: impl Into<String>) -> MigrationIssueSnapshot {
    issue(
        number,
        &format!("{DONE_PREFIX}[LEAF OF 7779] {label}"),
        "closed",
        body,
    )
}
fn with_plan(plan: &str) -> String {
    format!(
        "Chief umbrella: #7687.\n{}",
        compose_named_block("plan", plan)
    )
}

fn valid_request() -> MigrationAuditRequest {
    request(
        snapshot(vec![leaf(10)], dependencies(&[10]), vec![]),
        vec![evidence(10, &[])],
    )
}

#[test]
fn report_json_matches_the_current_empty_report_golden() {
    let report = build_migration_audit_report(&request(
        snapshot(vec![leaf(10)], dependencies(&[10]), vec![]),
        vec![evidence(10, &[])],
    ))
    .unwrap();
    assert_eq!(
        render_migration_audit_json(&report),
        "{\"chief_issue\":7687,\"counts\":{\"active_owner_conflicts\":0,\"clean_install_coverage_gaps\":0,\"executable_leaves\":1,\"historical_managed_leaves\":0,\"historical_missing_plan_evidence\":0,\"historical_recorded_rust_line_budget_deviations\":0,\"historical_unverified_rust_line_budgets\":0,\"missing_caller_surfaces\":0,\"missing_or_stale_blockers\":0,\"production_runtime_escape_hatches\":0,\"python_retirement_violations\":0,\"registry_state_violations\":0,\"stale_implementation_leases\":0,\"valid_plans\":1},\"findings\":[],\"issues\":[{\"finding_reasons\":[],\"number\":10,\"plan_valid\":true}],\"repository\":\"owner/repo\",\"schema_version\":2,\"snapshot_timestamp\":\"2026-07-19T12:00:00Z\"}\n"
    );
    assert_eq!(
        render_migration_audit_table(&report),
        concat!(
            "Migration governance audit\n\n",
            "executable leaves                                1\n",
            "valid plans                                      1\n",
            "historical managed leaves                        0\n",
            "historical missing plan evidence                 0\n",
            "historical unverified rust line budgets          0\n",
            "historical recorded rust line budget deviations  0\n",
            "missing or stale blockers                        0\n",
            "active owner conflicts                           0\n",
            "stale implementation leases                      0\n",
            "registry state violations                        0\n",
            "missing caller surfaces                          0\n",
            "python retirement violations                     0\n",
            "clean install coverage gaps                      0\n",
            "production runtime escape hatches                0\n"
        )
    );
}

#[test]
fn owner_conflicts_and_missing_reuse_sources_are_snapshot_findings() {
    let owner_block = "<!-- larch:owners:start -->\nCOMMAND\tissue\tmigration-audit\nCREATE\tshared-owner\tREADME.md\nREUSE\treused-owner\t#99\tREADME.md\n<!-- larch:owners:end -->\n";
    let managed = issue(
        11,
        "[LEAF OF 7779] Owned fixture",
        "open",
        format!(
            "Chief umbrella: #7687.\nNative blockers: none.\n{}\n{owner_block}",
            compose_named_block("plan", &plan())
        ),
    );
    let active = issue(
        12,
        "[IMPLEMENTING] Existing owner",
        "open",
        "<!-- larch:owners:start -->\nCOMMAND\tissue\tmigration-audit\nCREATE\tshared-owner\tREADME.md\n<!-- larch:owners:end -->\n",
    );
    let report = build_migration_audit_report(&request(
        snapshot(vec![managed, active], dependencies(&[11]), vec![]),
        vec![evidence(11, &[])],
    ))
    .unwrap();
    let reasons = report
        .findings
        .iter()
        .map(|finding| finding.reason.as_str())
        .collect::<Vec<_>>();
    assert!(reasons.contains(&"active-owner-conflict owner=shared-owner issue=#12"));
    assert!(reasons.contains(&"reuse-source-unavailable owner=reused-owner issue=#99"));
}

#[test]
fn classifications_and_rendering_are_order_independent() {
    let valid = leaf(10);
    let blocker = issue(2, "blocker", "open", "");
    let bad = issue(
        11,
        "[IMPLEMENTING] [LEAF OF 7779] Bad",
        "open",
        "Chief umbrella: #7.\nChief umbrella: #7687.\nNative blocker: #2.\nsecret=fixture-secret\n",
    );
    let plans = vec![evidence(10, &[]), evidence(11, &["missing-plan-block"])];
    let mut first = request(
        snapshot(
            vec![valid.clone(), bad.clone(), blocker.clone()],
            dependencies(&[10, 11]),
            vec![],
        ),
        plans.clone(),
    );
    let mut second = request(
        snapshot(vec![blocker, bad, valid], dependencies(&[11, 10]), vec![]),
        plans.into_iter().rev().collect(),
    );
    second.repository_findings = [
        (
            RepositoryFindingSource::ProductionRuntime,
            "runtime finding",
        ),
        (
            RepositoryFindingSource::CommandRegistry,
            "clean-install-coverage-missing x y",
        ),
        (
            RepositoryFindingSource::CommandRegistry,
            "production caller x is missing from the ledger",
        ),
        (
            RepositoryFindingSource::CommandRegistry,
            "python-entrypoint-still-called x: y",
        ),
        (
            RepositoryFindingSource::CommandRegistry,
            "non-atomic-rust-owner x y",
        ),
    ]
    .into_iter()
    .map(|(source, reason)| RepositoryAuditFinding {
        source,
        reason: reason.into(),
    })
    .rev()
    .collect();
    first.repository_findings = second.repository_findings.clone();
    let rendered = render_migration_audit_json(&build_migration_audit_report(&first).unwrap());
    assert_eq!(
        rendered,
        render_migration_audit_json(&build_migration_audit_report(&second).unwrap())
    );
    for needle in [
        "\"missing_or_stale_blockers\":2",
        "\"registry_state_violations\":1",
        "\"valid_plans\":1",
    ] {
        assert!(rendered.contains(needle), "{rendered}");
    }
    assert!(!rendered.contains("fixture-secret"));
}

#[test]
fn historical_evidence_is_report_only_and_inherits_the_chief() {
    let budget = plan().replace("diff_lines: 10\n", &format!("## Rust line budget deviation\n\n- Split decision: retain this leaf as one PR\n- Rationale: The wire cannot split safely.\n- Base SHA: {}\n- Head SHA: {}\n- Added non-generated Rust lines: 1501\n\ndiff_lines: 10\n", head(), head()));
    let closed = vec![
        closed(12, "Missing", "Chief umbrella: #7687.\n"),
        closed(13, "No budget", with_plan(&plan())),
        closed(14, "Budget", with_plan(&budget)),
        closed(
            15,
            "Inherited",
            "This is a leaf of umbrella #7779. Read the umbrella in full before acting.\n",
        ),
    ];
    let parent = issue(
        7779,
        "[IMPLEMENTING] [UMBRELLA] Fixture",
        "open",
        "This umbrella is part of #7687, **[CHIEF UMBRELLA] Fixture**.\n",
    );
    let report =
        build_migration_audit_report(&request(snapshot(vec![parent], vec![], closed), vec![]))
            .unwrap();
    let rendered = render_migration_audit_json(&report);
    for needle in [
        "\"historical_managed_leaves\":4",
        "\"historical_missing_plan_evidence\":2",
        "\"historical_unverified_rust_line_budgets\":1",
        "\"historical_recorded_rust_line_budget_deviations\":1",
    ] {
        assert!(rendered.contains(needle), "{rendered}");
    }
    assert!(report.findings.is_empty());
    assert_eq!(report.issues.len(), 4);
}

#[test]
fn malformed_snapshots_and_optional_audit_evidence_fail_closed() {
    let duplicate = request(
        snapshot(
            vec![leaf(10)],
            dependencies(&[10]),
            vec![issue(10, "done", "closed", "")],
        ),
        vec![evidence(10, &[])],
    );
    assert_eq!(
        build_migration_audit_report(&duplicate),
        Err(MigrationAuditDefect::DUPLICATE_ISSUE_SNAPSHOT)
    );
    let valid = format!(
        "## Rust line budget deviation\n\n- Split decision: retain this leaf as one PR\n- Rationale: Atomic wire change.\n- Base SHA: {}\n- Head SHA: {}\n- Added non-generated Rust lines: 1501\n",
        head(),
        "b".repeat(40)
    );
    assert_eq!(
        parse_rust_line_budget_deviation(&valid).deviation,
        Some(RustLineBudgetDeviation {
            split_decision: "retain this leaf as one PR".into(),
            rationale: "Atomic wire change.".into(),
            base_sha: head(),
            head_sha: "b".repeat(40),
            added_lines: 1501
        })
    );
    assert_eq!(
        parse_rust_line_budget_deviation(
            "## Rust line budget deviation\n\n- Split decision: split it\n"
        )
        .defects,
        vec!["malformed-rust-line-budget-deviation"]
    );
    let command_issue = issue(
        10,
        "fixture",
        "open",
        format!(
            "{}\n<!-- larch:owners:start -->\nCOMMAND\tissue\tmigration-audit\nCREATE\tfixture-owner\tREADME.md\n<!-- larch:owners:end -->\n",
            compose_named_block("plan", "Run issue\tmigration-audit.")
        ),
    );
    let row = build_command_audit_issue(
        &command_issue,
        true,
        &[CommandAuditKey {
            domain: "issue".into(),
            verb: "migration-audit".into(),
        }],
    )
    .unwrap();
    assert_eq!(
        render_command_audit_input(&[row], true).unwrap(),
        "{\"issues\":[{\"command\":{\"domain\":\"issue\",\"verb\":\"migration-audit\"},\"executable_leaf\":true,\"number\":10,\"plan_commands\":[{\"domain\":\"issue\",\"verb\":\"migration-audit\"}],\"state\":\"open\"}],\"rollout_enabled\":true,\"schema_version\":1}\n"
    );
}

#[test]
fn audit_input_validation_rejects_each_untrusted_snapshot_boundary() {
    let mut invalid_chief = valid_request();
    invalid_chief.snapshot.chief_issue = 0;
    assert_eq!(
        build_migration_audit_report(&invalid_chief),
        Err(MigrationAuditDefect::INVALID_CHIEF_ISSUE)
    );

    let mut invalid_head = valid_request();
    invalid_head.snapshot.head_sha = "not-a-git-object".to_owned();
    assert_eq!(
        build_migration_audit_report(&invalid_head),
        Err(MigrationAuditDefect::INVALID_SNAPSHOT_HEAD)
    );

    let mut invalid_issue = valid_request();
    invalid_issue.snapshot.open_issues[0].state = "closed".to_owned();
    assert_eq!(
        build_migration_audit_report(&invalid_issue),
        Err(MigrationAuditDefect::INVALID_ISSUE_SNAPSHOT)
    );

    let mut invalid_plan = valid_request();
    invalid_plan.plans[0].defects = vec!["not-a-plan-defect".to_owned()];
    assert_eq!(
        build_migration_audit_report(&invalid_plan),
        Err(MigrationAuditDefect::INVALID_PLAN_EVIDENCE)
    );

    let mut unexpected_plan = valid_request();
    unexpected_plan.plans[0].issue = 99;
    assert_eq!(
        build_migration_audit_report(&unexpected_plan),
        Err(MigrationAuditDefect::UNEXPECTED_PLAN_EVIDENCE)
    );

    let mut duplicate_plan = valid_request();
    duplicate_plan.plans.push(duplicate_plan.plans[0].clone());
    assert_eq!(
        build_migration_audit_report(&duplicate_plan),
        Err(MigrationAuditDefect::DUPLICATE_PLAN_EVIDENCE)
    );

    let mut missing_plan = valid_request();
    missing_plan.plans.clear();
    assert_eq!(
        build_migration_audit_report(&missing_plan),
        Err(MigrationAuditDefect::MISSING_PLAN_EVIDENCE)
    );

    let mut invalid_dependency = valid_request();
    invalid_dependency.snapshot.dependencies[0].blockers = vec![0];
    assert_eq!(
        build_migration_audit_report(&invalid_dependency),
        Err(MigrationAuditDefect::INVALID_DEPENDENCY_SNAPSHOT)
    );

    let mut duplicate_dependency = valid_request();
    duplicate_dependency
        .snapshot
        .dependencies
        .push(duplicate_dependency.snapshot.dependencies[0].clone());
    assert_eq!(
        build_migration_audit_report(&duplicate_dependency),
        Err(MigrationAuditDefect::DUPLICATE_DEPENDENCY_SNAPSHOT)
    );

    let mut missing_dependency = valid_request();
    missing_dependency.snapshot.dependencies.clear();
    assert_eq!(
        build_migration_audit_report(&missing_dependency),
        Err(MigrationAuditDefect::MISSING_DEPENDENCY_SNAPSHOT)
    );

    let mut invalid_finding = valid_request();
    invalid_finding.repository_findings = vec![RepositoryAuditFinding {
        source: RepositoryFindingSource::CommandRegistry,
        reason: "contains\na newline".to_owned(),
    }];
    assert_eq!(
        build_migration_audit_report(&invalid_finding),
        Err(MigrationAuditDefect::INVALID_REPOSITORY_FINDING)
    );

    assert_eq!(
        build_command_audit_issue(&issue(0, "fixture", "open", ""), false, &[],),
        Err(MigrationAuditDefect::INVALID_COMMAND_AUDIT_ISSUE)
    );
    let duplicate = larch_core::CommandAuditIssue {
        number: 1,
        state: "open".to_owned(),
        executable_leaf: false,
        command: None,
        plan_commands: Vec::new(),
    };
    assert_eq!(
        render_command_audit_input(&[duplicate.clone(), duplicate], false),
        Err(MigrationAuditDefect::DUPLICATE_COMMAND_AUDIT_ISSUE)
    );

    assert_eq!(
        parse_rust_line_budget_deviation(
            "## Rust line budget deviation\n\n## Rust line budget deviation\n"
        )
        .defects,
        vec!["multiple-rust-line-budget-deviations"]
    );
    assert!(
        validate_plan_facets("## Files to modify/create\n\n### MAY_UPDATE: generated.md\n")
            .contains(&"missing-firm-scope".to_owned())
    );
}

#[test]
fn audit_reports_stale_leases_historical_budget_defects_and_ambiguous_evidence() {
    assert_eq!(
        MigrationAuditDefect::INVALID_CHIEF_ISSUE.reason(),
        "invalid-migration-audit-chief"
    );
    assert_eq!(
        MigrationAuditDefect::INVALID_CHIEF_ISSUE.to_string(),
        "invalid-migration-audit-chief"
    );

    let stale_lease = upsert_implementation_lease(
        "",
        &ImplementationLease {
            run_id: "run-1".to_owned(),
            branch: "feature/stale".to_owned(),
            base: head(),
            plan: "b".repeat(64),
            updated_at: "2026-07-18T00:00:00Z".to_owned(),
        },
    )
    .expect("render lease");
    let active = issue(11, "[IMPLEMENTING] stale", "open", stale_lease);
    let report = build_migration_audit_report(&request(
        snapshot(vec![leaf(10), active], dependencies(&[10]), vec![]),
        vec![evidence(10, &[])],
    ))
    .expect("stale lease report");
    assert!(report.findings.iter().any(|finding| {
        finding.category == larch_core::FindingCategory::StaleImplementationLease
            && finding.cleanup_command.is_some()
    }));

    let malformed_budget = plan().replace(
        "diff_lines: 10\n",
        &format!(
            "## Rust line budget deviation\n\n- Split decision: retain this leaf as one PR\n- Rationale: Fixture.\n- Base SHA: {}\n- Head SHA: {}\n- Added non-generated Rust lines: -1\n\ndiff_lines: 10\n",
            head(),
            head(),
        ),
    );
    let historical = closed(12, "Malformed budget", with_plan(&malformed_budget));
    let report = build_migration_audit_report(&request(
        snapshot(vec![leaf(10)], dependencies(&[10]), vec![historical]),
        vec![evidence(10, &[])],
    ))
    .expect("historical report");
    assert!(
        report.issues.iter().any(|issue| {
            issue.number == 12
                && issue.finding_reasons.iter().any(|reason| {
                    reason.contains("historical-rust-line-budget-unverified defects=")
                })
        }),
        "{:?}",
        report.issues
    );

    let malformed_budget = format!(
        "## Rust line budget deviation\n\n- Split decision: retain this leaf as one PR\n- Rationale: Fixture.\n- Base SHA: {}\n- Head SHA: {}\n- Added non-generated Rust lines: no\n",
        head(),
        head(),
    );
    assert_eq!(
        parse_rust_line_budget_deviation(&malformed_budget).defects,
        vec!["malformed-rust-line-budget-deviation"]
    );

    let duplicate_leaf = request(
        snapshot(vec![leaf(10), leaf(10)], dependencies(&[10]), vec![]),
        vec![evidence(10, &[])],
    );
    assert_eq!(
        build_migration_audit_report(&duplicate_leaf),
        Err(MigrationAuditDefect::DUPLICATE_ISSUE_SNAPSHOT)
    );
    let mut duplicate_blocker = valid_request();
    duplicate_blocker.snapshot.dependencies[0].blockers = vec![7, 7];
    assert_eq!(
        build_migration_audit_report(&duplicate_blocker),
        Err(MigrationAuditDefect::INVALID_DEPENDENCY_SNAPSHOT)
    );

    let command_issue = issue(
        20,
        "fixture",
        "open",
        compose_named_block(
            "plan",
            "unissue migration-audit must not count as a command.",
        ),
    );
    assert!(
        build_command_audit_issue(
            &command_issue,
            false,
            &[CommandAuditKey {
                domain: "issue".to_owned(),
                verb: "migration-audit".to_owned(),
            }],
        )
        .expect("command audit issue")
        .plan_commands
        .is_empty()
    );
}

#[test]
fn audit_rejects_remaining_untrusted_snapshot_and_budget_forms() {
    let mut invalid_repository = valid_request();
    invalid_repository.snapshot.repository = "owner/repo/extra".to_owned();
    assert_eq!(
        build_migration_audit_report(&invalid_repository),
        Err(MigrationAuditDefect::INVALID_REPOSITORY)
    );

    let mut invalid_timestamp = valid_request();
    invalid_timestamp.snapshot.snapshot_timestamp = "not-a-timestamp".to_owned();
    assert_eq!(
        build_migration_audit_report(&invalid_timestamp),
        Err(MigrationAuditDefect::INVALID_SNAPSHOT_TIMESTAMP)
    );

    let mut invalid_referenced_issue = valid_request();
    invalid_referenced_issue.snapshot.referenced_issues = vec![issue(99, "fixture", "all", "")];
    assert_eq!(
        build_migration_audit_report(&invalid_referenced_issue),
        Err(MigrationAuditDefect::INVALID_ISSUE_SNAPSHOT)
    );

    let mut misplaced_dependency = valid_request();
    misplaced_dependency.snapshot.dependencies[0].issue = 99;
    assert_eq!(
        build_migration_audit_report(&misplaced_dependency),
        Err(MigrationAuditDefect::INVALID_DEPENDENCY_SNAPSHOT)
    );

    let mut missing_referenced_issue = valid_request();
    missing_referenced_issue.snapshot.open_issues[0]
        .body
        .push_str("\nNative blocker: #99\n");
    missing_referenced_issue.snapshot.dependencies[0].blockers = vec![99];
    assert_eq!(
        build_migration_audit_report(&missing_referenced_issue),
        Err(MigrationAuditDefect::MISSING_REFERENCED_ISSUE)
    );

    for reason in [String::new(), "\r".to_owned(), "x".repeat(4097)] {
        let mut invalid_finding = valid_request();
        invalid_finding.repository_findings = vec![RepositoryAuditFinding {
            source: RepositoryFindingSource::CommandRegistry,
            reason,
        }];
        assert_eq!(
            build_migration_audit_report(&invalid_finding),
            Err(MigrationAuditDefect::INVALID_REPOSITORY_FINDING)
        );
    }

    assert_eq!(
        build_command_audit_issue(&issue(1, "fixture", "unknown", ""), false, &[]),
        Err(MigrationAuditDefect::INVALID_COMMAND_AUDIT_ISSUE)
    );

    let overflowing_budget = format!(
        "## Rust line budget deviation\n\n- Split decision: retain this leaf as one PR\n- Rationale: Fixture.\n- Base SHA: {}\n- Head SHA: {}\n- Added non-generated Rust lines: 18446744073709551616\n",
        head(),
        head(),
    );
    assert_eq!(
        parse_rust_line_budget_deviation(&overflowing_budget).defects,
        vec!["malformed-rust-line-budget-deviation"]
    );

    let fenced_budget = format!(
        "## Rust line budget deviation\n\n```text\n- Split decision: split this leaf\n- Added non-generated Rust lines: 1\n```\n- Split decision: retain this leaf as one PR\n- Rationale: Fence contents are not plan evidence.\n- Base SHA: {}\n- Head SHA: {}\n- Added non-generated Rust lines: 1\n",
        head(),
        head(),
    );
    assert!(
        parse_rust_line_budget_deviation(&fenced_budget)
            .deviation
            .is_some()
    );
}
