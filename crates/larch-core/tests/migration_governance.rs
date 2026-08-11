//! Golden fixtures for the effect-free migration-governance admission core.

use chrono::{TimeZone, Utc};
use larch_core::{
    BlockerSnapshotRow, FreshnessVerdict, GovernanceIssueSnapshot, ImplementationLease,
    OwnerAdmissionRequest, OwnerAdmissionVerdict, ParityVerdict, PlanReceipt,
    REASON_MISSING_NATIVE, REASON_STALE_BLOCKER_SNAPSHOT, REASON_STALE_OWNER_SNAPSHOT,
    REASON_STALE_PLAN_BASE_SCOPE, REASON_STALE_PLAN_BODY, ReceiptFreshnessRequest, RepositoryName,
    ScopeFile, ScopeSnapshot, compare_blocker_parity, compose_named_block, declared_scope_paths,
    evaluate_governance_gate, evaluate_owner_admission, format_gate_refusal, hash_blocker_rows,
    hash_owner_rows, hash_plan_block, migration_requires_owner_block, parse_native_blocker_refs,
    parse_owner_block, parse_receipt, upsert_implementation_lease, upsert_receipt,
    validate_receipt_freshness,
};

fn plan(migration: &str) -> String {
    format!(
        "## Closed decisions and ownership\n\n- Fixture plan.\n\n## Files to modify/create\n\n### UPDATED: README.md\n\n## Breaking changes and migration\n\n{migration}\n\ndiff_lines: 12\n"
    )
}
fn owners(rows: &[&str]) -> String {
    format!(
        "<!-- larch:owners:start -->\n{}\n<!-- larch:owners:end -->\n",
        rows.join("\n")
    )
}
fn scope(sha: char, readme: &str, other: &str) -> ScopeSnapshot {
    ScopeSnapshot {
        sha: sha.to_string().repeat(40),
        files: vec![file("README.md", readme), file("OTHER.md", other)],
    }
}
fn file(path: &str, object_id: &str) -> ScopeFile {
    ScopeFile {
        path: path.to_owned(),
        object_id: object_id.to_owned(),
    }
}
#[test]
fn blockers_receipts_and_scope_paths_match_python_fixtures() {
    let refs = parse_native_blocker_refs(
        "Native blockers: #7780 and #7781.\n```\nNative blocker: #1\n```\nNative blocker: #2.\n",
    );
    assert_eq!(refs, vec![2, 7780, 7781]);
    let parity = compare_blocker_parity(
        &[row(10, "open"), row(12, "open")],
        &[row(12, "open"), row(13, "closed"), row(14, "open")],
    );
    assert_eq!(
        parity.reasons,
        vec![
            "missing-native-blocker-edge issue=#10",
            "undocumented-native-blocker-edge issue=#14",
            "closed-blocker-edge-retained issue=#13",
        ]
    );
    assert!(parity.blocking());
    assert_eq!(
        parity.report_only(),
        vec!["closed-blocker-edge-retained issue=#13"]
    );
    let inner = plan("None.");
    let receipt = PlanReceipt {
        plan_sha256: hash_plan_block(&inner),
        base_sha: "a".repeat(40),
        blockers_sha256: hash_blocker_rows(&[]),
        owners_sha256: hash_owner_rows(&[]),
    };
    let body = upsert_receipt(&compose_named_block("plan", &inner), &receipt).unwrap();
    assert_eq!(parse_receipt(&body), Some(receipt.clone()));
    assert_eq!(
        parse_receipt(&upsert_receipt(&body, &receipt).unwrap()),
        Some(receipt)
    );
    assert_eq!(
        declared_scope_paths(
            "### UPDATED: docs/[a-c].md\n### NEW: docs/*.txt\n",
            &[
                "docs/a.md".into(),
                "docs/b.md".into(),
                "docs/c.md".into(),
                "docs/d.txt".into(),
            ],
        ),
        vec!["docs/a.md", "docs/b.md", "docs/c.md", "docs/d.txt"]
    );
}
#[test]
fn freshness_is_snapshot_only_and_detects_each_drift() {
    let inner = plan("None.");
    let draft = format!(
        "{}{}",
        compose_named_block("plan", &inner),
        owners(&[
            "COMMAND\tissue\tmigration-audit",
            "CREATE\tfixture-owner\tREADME.md",
        ])
    );
    let receipt = PlanReceipt {
        plan_sha256: hash_plan_block(&inner),
        base_sha: "a".repeat(40),
        blockers_sha256: hash_blocker_rows(&[]),
        owners_sha256: hash_owner_rows(&parse_owner_block(&draft).raw_rows),
    };
    let body = upsert_receipt(&draft, &receipt).unwrap();
    assert_eq!(
        freshness(
            &draft,
            vec![],
            scope('a', "one", "old"),
            scope('b', "one", "new")
        )
        .reasons,
        vec![REASON_STALE_PLAN_BODY.to_owned()]
    );
    assert!(
        freshness(
            &body,
            vec![],
            scope('a', "one", "old"),
            scope('b', "one", "new")
        )
        .ok()
    );
    for (candidate, rows, head, reason) in [
        (
            body.replace("Fixture", "Drift"),
            vec![],
            scope('b', "one", "new"),
            REASON_STALE_PLAN_BODY,
        ),
        (
            body.replace("fixture-owner", "other-owner"),
            vec![],
            scope('b', "one", "new"),
            REASON_STALE_OWNER_SNAPSHOT,
        ),
        (
            body.clone(),
            vec![row(9, "open")],
            scope('b', "one", "new"),
            REASON_STALE_BLOCKER_SNAPSHOT,
        ),
        (
            body.clone(),
            vec![],
            scope('b', "two", "new"),
            REASON_STALE_PLAN_BASE_SCOPE,
        ),
    ] {
        assert!(
            freshness(&candidate, rows, scope('a', "one", "old"), head)
                .reasons
                .contains(&reason.to_owned())
        );
    }
}
#[test]
fn ownership_admission_handles_reuse_conflicts_and_stale_leases() {
    let source_plan = plan("None.");
    let source_draft = format!(
        "{}{}",
        compose_named_block("plan", &source_plan),
        owners(&["COMMAND\tissue\tsource", "CREATE\treuse-owner\tREADME.md"])
    );
    let source = GovernanceIssueSnapshot {
        number: 6,
        title: "source".to_owned(),
        state: "OPEN".to_owned(),
        body: upsert_receipt(
            &source_draft,
            &PlanReceipt {
                plan_sha256: hash_plan_block(&source_plan),
                base_sha: "a".repeat(40),
                blockers_sha256: hash_blocker_rows(&[]),
                owners_sha256: hash_owner_rows(&parse_owner_block(&source_draft).raw_rows),
            },
        )
        .unwrap(),
    };
    let active_body = upsert_implementation_lease(
        &owners(&[
            "COMMAND\tissue\tother-command",
            "REUSE\tshared-owner\t#6\tREADME.md",
        ]),
        &ImplementationLease {
            run_id: "run-8".to_owned(),
            branch: "feature/pending".to_owned(),
            base: "a".repeat(40),
            plan: "b".repeat(64),
            updated_at: "2026-07-19T00:00:00Z".to_owned(),
        },
    )
    .unwrap();
    let request = OwnerAdmissionRequest {
        issue: 7,
        body: format!(
            "Native blocker: #6.\n{}{}",
            compose_named_block("plan", &plan("None.")),
            owners(&[
                "COMMAND\tissue\tmigration-audit",
                "CREATE\tshared-owner\tREADME.md",
                "REUSE\treuse-owner\t#6\tREADME.md",
            ])
        ),
        reuse_sources: vec![source],
        active_issues: Some(vec![GovernanceIssueSnapshot {
            number: 8,
            title: "[IMPLEMENTING] other".to_owned(),
            state: "open".to_owned(),
            body: active_body,
        }]),
        open_pr_branches: Some(vec![]),
        now: Utc.with_ymd_and_hms(2026, 7, 19, 13, 0, 0).unwrap(),
        repository: RepositoryName::parse("owner/repo").unwrap(),
    };
    let verdict = evaluate_owner_admission(&request);
    assert_eq!(
        verdict.reasons,
        vec!["active-owner-conflict owner=shared-owner issue=#8"]
    );
    assert_eq!(
        verdict.report_only,
        vec!["stale-implementation-lease issue=#8 age_hours=13"]
    );
    assert_eq!(
        verdict.cleanup_commands,
        vec![
            "scripts/larch.sh tracking-issue rename --issue 8 --state stalled --repo owner/repo --run-id run-8"
        ]
    );
    assert_eq!(
        parse_owner_block(&owners(&["CREATE\towner\tREADME.md"])).defects,
        vec!["invalid-owner-command"]
    );
    let no_edge = OwnerAdmissionRequest {
        body: request.body.replacen("Native blocker: #6.\n", "", 1),
        ..request.clone()
    };
    assert!(
        evaluate_owner_admission(&no_edge)
            .reasons
            .contains(&"reuse-missing-native-blocker owner=reuse-owner issue=#6".to_owned())
    );
    let unavailable = OwnerAdmissionRequest {
        reuse_sources: vec![],
        ..request
    };
    assert!(
        evaluate_owner_admission(&unavailable)
            .reasons
            .contains(&"reuse-source-unavailable owner=reuse-owner issue=#6".to_owned())
    );
}
#[test]
fn migration_classifier_and_gate_output_are_stable() {
    for text in [
        "No breaking changes to existing behavior.",
        "The change is additive and uses existing contracts.",
        "None.\n\nConfidence: high",
        "N/A.",
        "No migration is required.",
        "No new shared adapter is created.",
        "There is no need for a new shared adapter.",
        "Add a flag through the existing adapter.",
        "Create adapter tests for existing behavior.",
        "Add client compatibility through the existing adapter.",
    ] {
        assert!(!migration_requires_owner_block(&plan(text)), "{text}");
    }
    for text in [
        "Creates a new shared adapter for migration.",
        "Add a shared registry for command discovery.",
        "Introduce a typed runtime resolver.",
        "A state machine will be created for migration.",
        "A state-machine will be created for migration.",
        "Create a new shared\nadapter for migration.",
        "Create a shared adapter module for migration.",
        "No breaking changes and adds a new shared adapter.",
        "Add through an existing adapter and creates a shared resolver.",
    ] {
        assert!(migration_requires_owner_block(&plan(text)), "{text}");
    }
    let gate = evaluate_governance_gate(
        ParityVerdict {
            reasons: vec![format!("{REASON_MISSING_NATIVE} issue=#10")],
        },
        FreshnessVerdict { reasons: vec![] },
        OwnerAdmissionVerdict::default(),
    );
    assert_eq!(
        format_gate_refusal("preflight", &gate),
        "**❌ preflight: migration governance blocked: `missing-native-blocker-edge issue=#10`.**"
    );
}
fn row(number: u64, state: &str) -> BlockerSnapshotRow {
    BlockerSnapshotRow {
        number,
        state: state.to_owned(),
        updated_at: format!("t{number}"),
    }
}
fn freshness(
    body: &str,
    blocker_rows: Vec<BlockerSnapshotRow>,
    base_scope: ScopeSnapshot,
    head_scope: ScopeSnapshot,
) -> FreshnessVerdict {
    validate_receipt_freshness(&ReceiptFreshnessRequest {
        body: body.to_owned(),
        blocker_rows,
        base_scope: Some(base_scope),
        head_scope: Some(head_scope),
    })
}
