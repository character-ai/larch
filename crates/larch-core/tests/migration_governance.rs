//! Golden fixtures for the effect-free migration-governance admission core.

use chrono::{TimeZone, Utc};
use larch_core::{
    BlockerSnapshotRow, FreshnessVerdict, GovernanceIssueSnapshot, ImplementationLease,
    OwnerAdmissionRequest, OwnerAdmissionVerdict, ParityVerdict, PlanReceipt, PlanScopeDeclaration,
    PlanScopeKind, REASON_MISSING_NATIVE, REASON_STALE_BLOCKER_SNAPSHOT,
    REASON_STALE_OWNER_SNAPSHOT, REASON_STALE_PLAN_BASE_SCOPE, REASON_STALE_PLAN_BODY,
    ReceiptFreshnessRequest, RepositoryName, ScopeFile, ScopeFingerprintDefect, ScopeSnapshot,
    compare_blocker_parity, compose_named_block, compute_scope_fingerprint, declared_scope_paths,
    evaluate_governance_gate, evaluate_owner_admission, format_gate_refusal, hash_blocker_rows,
    hash_owner_rows, hash_plan_block, migration_requires_owner_block, parse_native_blocker_refs,
    parse_owner_block, parse_receipt, plan_scope_declarations, render_receipt,
    upsert_implementation_lease, upsert_receipt, validate_receipt_freshness,
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
    assert_eq!(
        plan_scope_declarations(
            "### UPDATED: `docs/a b.md` (generated)\n### NEW: docs/*.txt\n```markdown\n### REWRITTEN: ignored.md\n```\n",
        ),
        vec![
            PlanScopeDeclaration {
                kind: PlanScopeKind::Updated,
                path: "docs/a b.md".to_owned(),
            },
            PlanScopeDeclaration {
                kind: PlanScopeKind::New,
                path: "docs/*.txt".to_owned(),
            },
        ]
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

#[test]
fn migration_evidence_rejects_malformed_receipts_owner_rows_and_scope_identity() {
    let valid_receipt = PlanReceipt {
        plan_sha256: "a".repeat(64),
        base_sha: "b".repeat(40),
        blockers_sha256: "c".repeat(64),
        owners_sha256: "d".repeat(64),
    };
    assert_receipt_and_repository_validation(&valid_receipt);
    assert_owner_block_validation();
    assert_scope_identity_validation();
}

fn assert_receipt_and_repository_validation(valid_receipt: &PlanReceipt) {
    assert_eq!(
        render_receipt(&PlanReceipt {
            base_sha: "invalid".to_owned(),
            ..valid_receipt.clone()
        })
        .expect_err("invalid receipt fields must not render")
        .to_string(),
        "invalid-plan-receipt-fields"
    );
    assert_eq!(
        upsert_receipt("no plan block\n", valid_receipt)
            .expect_err("receipt cannot be attached without a plan")
            .to_string(),
        "plan-block-missing"
    );
    assert!(parse_receipt(
        "<!-- larch:plan-receipt v1 plan_sha256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa base_sha=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb blockers_sha256=cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc owners_sha256=dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd -->\n<!-- larch:plan-receipt v1 plan_sha256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa base_sha=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb blockers_sha256=cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc owners_sha256=dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd -->"
    )
    .is_none());

    for invalid in [
        "owner",
        "owner/repo/extra",
        " owner/repo",
        "owner/",
        "owner/repo ",
    ] {
        assert_eq!(
            RepositoryName::parse(invalid)
                .expect_err("repository must have a strict owner/name shape")
                .to_string(),
            "invalid-repository-name"
        );
    }
}

fn assert_owner_block_validation() {
    let malformed = parse_owner_block(
        "<!-- larch:owners:start -->\nCREATE\towner\t../escape\nCOMMAND\tissue\tmigration-audit\nCREATE\towner\tREADME.md\n<!-- larch:owners:end -->",
    );
    assert!(
        malformed
            .defects
            .contains(&"invalid-owner-command".to_owned())
    );
    assert!(
        malformed
            .defects
            .contains(&"duplicate-owner-key".to_owned())
    );
    assert!(
        malformed
            .defects
            .contains(&"unsafe-owner-target".to_owned())
    );
    assert!(
        malformed
            .defects
            .contains(&"unsorted-owner-rows".to_owned())
    );
    assert_eq!(
        parse_owner_block("<!-- larch:owners:start -->\n<!-- larch:owners:start -->").defects,
        vec!["malformed-owner-block"]
    );
}

fn assert_scope_identity_validation() {
    assert_eq!(
        plan_scope_declarations("### REWRITTEN: docs/rewrite.md\n### MAY_UPDATE [docs/maybe.md]\n",),
        vec![
            PlanScopeDeclaration {
                kind: PlanScopeKind::Rewritten,
                path: "docs/rewrite.md".to_owned(),
            },
            PlanScopeDeclaration {
                kind: PlanScopeKind::MayUpdate,
                path: "docs/maybe.md".to_owned(),
            },
        ]
    );
    assert_eq!(
        declared_scope_paths(
            "### UPDATED: docs/[!x].md\n### UPDATED: ../outside.md\n",
            &["docs/a.md".to_owned(), "docs/x.md".to_owned()],
        ),
        vec!["docs/a.md"]
    );
    assert_eq!(
        compute_scope_fingerprint(
            "### UPDATED: README.md",
            &[],
            &ScopeSnapshot {
                sha: "invalid".to_owned(),
                files: Vec::new(),
            },
        ),
        Err(ScopeFingerprintDefect::InvalidSha)
    );
    assert_eq!(
        compute_scope_fingerprint(
            "### UPDATED: README.md",
            &[],
            &ScopeSnapshot {
                sha: "a".repeat(40),
                files: vec![file("README.md", "one"), file("README.md", "two")],
            },
        ),
        Err(ScopeFingerprintDefect::ContradictoryFileIdentity)
    );
}

#[test]
fn migration_governance_fail_closed_branches_remain_explicit_and_fence_aware() {
    assert_receipt_and_parser_fail_closed();
    assert_scope_gate_and_freshness_fail_closed();
    assert_owner_admission_fails_closed_without_complete_evidence();
}

fn assert_receipt_and_parser_fail_closed() {
    let receipt = PlanReceipt {
        plan_sha256: "a".repeat(64),
        base_sha: "b".repeat(40),
        blockers_sha256: "c".repeat(64),
        owners_sha256: "d".repeat(64),
    };
    assert_eq!(
        upsert_receipt("<!-- larch:plan:start -->\nunclosed\n", &receipt)
            .expect_err("malformed plan blocks cannot accept a receipt")
            .to_string(),
        "plan-block-malformed"
    );
    let plan_block = compose_named_block("plan", &plan("None."));
    let body = format!(
        "{plan_block}\n\n<!-- larch:plan-receipt v1 plan_sha256={} base_sha={} blockers_sha256={} owners_sha256={} -->\n\ntrailing\n",
        "a".repeat(64),
        "b".repeat(40),
        "c".repeat(64),
        "d".repeat(64),
    );
    let rewritten = upsert_receipt(&body, &receipt).expect("replace prior receipt");
    assert_eq!(rewritten.matches("larch:plan-receipt").count(), 1);
    assert!(rewritten.ends_with("\n\ntrailing\n"));

    assert_eq!(
        parse_native_blocker_refs("```\nNative blockers: #1\n```\nNative blockers: #2\n"),
        vec![2]
    );
    assert_eq!(
        parse_owner_block(
            "<!-- larch:owners:start -->\nCOMMAND\tissue\tmigration-audit\nCOMMAND\tissue\tmigration-audit\n<!-- larch:owners:end -->",
        )
        .defects,
        vec![
            "duplicate-owner-row".to_owned(),
            "invalid-owner-command".to_owned(),
            "missing-owner-row".to_owned(),
        ]
    );
    assert!(parse_owner_block(
        "<!-- larch:owners:start -->\nCOMMAND\tissue\tmigration-audit\nCREATE\tinvalid key\tREADME.md\n<!-- larch:owners:end -->",
    )
    .defects
    .contains(&"invalid-owner-key".to_owned()));
}

fn assert_scope_gate_and_freshness_fail_closed() {
    assert_eq!(
        declared_scope_paths(
            "### UPDATED: docs/?.md\n### UPDATED: docs/[.md\n",
            &["docs/a.md".to_owned(), "docs/[.md".to_owned()],
        ),
        vec!["docs/[.md".to_owned(), "docs/a.md".to_owned()]
    );

    let clean_parity = ParityVerdict {
        reasons: Vec::new(),
    };
    let clean_freshness = FreshnessVerdict {
        reasons: Vec::new(),
    };
    assert!(!clean_parity.blocking());
    assert!(clean_freshness.ok());
    assert!(
        evaluate_governance_gate(
            clean_parity.clone(),
            clean_freshness.clone(),
            OwnerAdmissionVerdict::default(),
        )
        .ok()
    );
    assert_eq!(
        format_gate_refusal(
            "preflight",
            &evaluate_governance_gate(
                clean_parity,
                clean_freshness,
                OwnerAdmissionVerdict::default(),
            ),
        ),
        "**❌ preflight: migration governance blocked: `unknown`.**"
    );
    assert_eq!(
        validate_receipt_freshness(&ReceiptFreshnessRequest {
            body: "no receipt".to_owned(),
            blocker_rows: Vec::new(),
            base_scope: None,
            head_scope: None,
        })
        .reasons,
        vec![REASON_STALE_PLAN_BODY.to_owned()]
    );
}

fn assert_owner_admission_fails_closed_without_complete_evidence() {
    let migration_plan = plan("Create a new shared adapter.");
    let base_request =
        |body: String, active_issues: Option<Vec<GovernanceIssueSnapshot>>| OwnerAdmissionRequest {
            issue: 7,
            body,
            reuse_sources: Vec::new(),
            active_issues,
            open_pr_branches: None,
            now: Utc.with_ymd_and_hms(2026, 7, 19, 0, 0, 0).unwrap(),
            repository: RepositoryName::parse("owner/repo").unwrap(),
        };
    assert!(
        evaluate_owner_admission(&base_request(
            compose_named_block("plan", &migration_plan),
            Some(Vec::new()),
        ))
        .reasons
        .contains(&"missing-owner-block".to_owned())
    );
    let complete_owners = owners(&[
        "COMMAND\tissue\tmigration-audit",
        "CREATE\tfixture-owner\tREADME.md",
    ]);
    assert!(
        evaluate_owner_admission(&base_request(
            format!(
                "{}{}",
                compose_named_block("plan", &migration_plan),
                complete_owners
            ),
            None,
        ))
        .reasons
        .contains(&"owner-scan-unavailable".to_owned())
    );
}

#[test]
fn reuse_and_active_owner_evidence_require_valid_snapshots_not_title_heuristics() {
    let now = Utc.with_ymd_and_hms(2026, 7, 19, 0, 0, 0).unwrap();
    let repository = RepositoryName::parse("owner/repo").unwrap();
    let reuse_body = format!(
        "Native blocker: #8.\n{}{}",
        compose_named_block("plan", &plan("None.")),
        owners(&[
            "COMMAND\tissue\tmigration-audit",
            "REUSE\tsnapshot-owner\t#8\tREADME.md",
        ])
    );
    let invalid_source = GovernanceIssueSnapshot {
        number: 8,
        title: "source".to_owned(),
        state: "open".to_owned(),
        body: owners(&[
            "COMMAND\tissue\tmigration-audit",
            "CREATE\tsnapshot-owner\tREADME.md",
        ]),
    };
    let verdict = evaluate_owner_admission(&OwnerAdmissionRequest {
        issue: 7,
        body: reuse_body,
        reuse_sources: vec![invalid_source],
        active_issues: Some(Vec::new()),
        open_pr_branches: None,
        now,
        repository: repository.clone(),
    });
    assert!(
        verdict
            .reasons
            .contains(&"reuse-owner-snapshot-invalid owner=snapshot-owner issue=#8".to_owned())
    );

    let current_body = format!(
        "{}{}",
        compose_named_block("plan", &plan("None.")),
        owners(&[
            "COMMAND\tissue\tmigration-audit",
            "CREATE\tshared-owner\tREADME.md",
        ])
    );
    let malformed_active = GovernanceIssueSnapshot {
        number: 9,
        title: "[IMPLEMENTING] malformed owner block".to_owned(),
        state: "open".to_owned(),
        body: owners(&[
            "COMMAND\tissue\tmigration-audit",
            "CREATE\tshared-owner\tREADME.md",
            "CREATE\tshared-owner\tREADME.md",
        ]),
    };
    let lease_active = GovernanceIssueSnapshot {
        number: 10,
        title: "ordinary title".to_owned(),
        state: "open".to_owned(),
        body: upsert_implementation_lease(
            &owners(&[
                "COMMAND\tissue\tmigration-audit",
                "CREATE\tshared-owner\tREADME.md",
            ]),
            &ImplementationLease {
                run_id: "run-10".to_owned(),
                branch: "feature/active".to_owned(),
                base: "a".repeat(40),
                plan: "b".repeat(64),
                updated_at: "2026-07-19T00:00:00Z".to_owned(),
            },
        )
        .expect("lease"),
    };
    let verdict = evaluate_owner_admission(&OwnerAdmissionRequest {
        issue: 7,
        body: current_body,
        reuse_sources: Vec::new(),
        active_issues: Some(vec![malformed_active, lease_active]),
        open_pr_branches: None,
        now,
        repository,
    });
    assert!(
        verdict
            .reasons
            .contains(&"active-owner-conflict owner=shared-owner issue=#9".to_owned())
    );
    assert!(
        verdict
            .reasons
            .contains(&"active-owner-conflict owner=shared-owner issue=#10".to_owned())
    );
}

#[test]
fn governance_parsers_keep_fences_globs_and_owner_targets_fail_closed() {
    let empty = parse_owner_block("<!-- larch:owners:start -->\n\n<!-- larch:owners:end -->");
    assert!(empty.defects.contains(&"invalid-owner-row".to_owned()));
    assert!(empty.defects.contains(&"invalid-owner-command".to_owned()));
    assert!(empty.defects.contains(&"missing-owner-row".to_owned()));

    let invalid_command = parse_owner_block(
        "<!-- larch:owners:start -->\nCOMMAND\tbad domain\tmigration-audit\nCREATE\towner\tREADME.md\n<!-- larch:owners:end -->",
    );
    assert!(
        invalid_command
            .defects
            .contains(&"invalid-owner-command".to_owned())
    );

    for target in ["README.md::bad symbol", "README.md::first::second"] {
        assert!(parse_owner_block(&format!(
            "<!-- larch:owners:start -->\nCOMMAND\tissue\tmigration-audit\nCREATE\towner\t{target}\n<!-- larch:owners:end -->"
        ))
        .defects
        .contains(&"unsafe-owner-target".to_owned()));
    }

    assert_eq!(
        declared_scope_paths(
            "### UPDATED: docs/*\n### UPDATED: docs/[ab].md\n",
            &[
                "docs/a.md".to_owned(),
                "docs/b.md".to_owned(),
                "docs/nested/c.md".to_owned(),
                "notes.md".to_owned(),
            ],
        ),
        vec!["docs/a.md", "docs/b.md", "docs/nested/c.md"]
    );

    let receipt = render_receipt(&PlanReceipt {
        plan_sha256: "a".repeat(64),
        base_sha: "b".repeat(40),
        blockers_sha256: "c".repeat(64),
        owners_sha256: "d".repeat(64),
    })
    .expect("valid receipt");
    assert_eq!(
        validate_receipt_freshness(&ReceiptFreshnessRequest {
            body: receipt,
            blocker_rows: Vec::new(),
            base_scope: None,
            head_scope: None,
        })
        .reasons,
        vec![REASON_STALE_PLAN_BODY.to_owned()]
    );

    assert!(!migration_requires_owner_block(&plan(
        "```text\nCreate a new shared adapter.\n```\n\nNone."
    )));
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
