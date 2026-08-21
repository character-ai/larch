//! Offline phase-machine tests for `design publish`.
//!
//! Every sibling verb answers from a recorded script, so the ported phase
//! order, refusal codes, and result-env rows are provable without GitHub, git,
//! or a Python interpreter.

#[cfg(test)]
mod design_publish_commands_tests {
    use std::cell::RefCell;
    use std::collections::HashMap;
    use std::fs;
    use std::path::Path;

    use larch_core::AssessmentKind;
    use tempfile::TempDir;

    use super::super::{
        PUBLISH_RESULT_FILE, PublishArgs, RC_FAILED, RC_REFUSED, ReceiptWriter, parse_publish_args,
        publish_core,
    };
    use crate::clarify_orchestrator::{CapturedRun, SiblingRunner};
    use crate::design_step0_commands::phase_driver_read_result_env;

    /// A receipt writer that records its call and answers from a fixed script.
    struct ScriptReceipt {
        detail: Option<&'static str>,
        calls: RefCell<u32>,
    }

    impl ScriptReceipt {
        const fn ok() -> Self {
            Self {
                detail: None,
                calls: RefCell::new(0),
            }
        }

        const fn failing(detail: &'static str) -> Self {
            Self {
                detail: Some(detail),
                calls: RefCell::new(0),
            }
        }
    }

    impl ReceiptWriter for ScriptReceipt {
        fn persist(&self, _repo: &str, _issue: u64, _repo_root: &Path) -> Result<(), String> {
            *self.calls.borrow_mut() += 1;
            self.detail.map_or(Ok(()), |detail| Err(detail.to_owned()))
        }
    }

    /// A composed plan that satisfies the executable-plan contract.
    ///
    /// `AGENTS.md` is tracked in every checkout, so the M2 path facet resolves
    /// against the ambient index the phase machine reads.
    const CONTRACT_PLAN: &str = concat!(
        "## Plan\n\n",
        "### Closed decisions and ownership\n\n",
        "- Publish keeps one owner.\n\n",
        "### Ordered implementation\n\n",
        "1. Write the plan block.\n",
        "2. Rename the tracking issue.\n\n",
        "## Files to modify/create\n\n",
        "### UPDATED: AGENTS.md\n\n",
        "## Acceptance\n\n",
        "- The publish rows stay allowlisted.\n\n",
        "## Breaking changes and migration\n\n",
        "None.\n\n",
        "diff_lines: 12\n",
    );

    /// A recorded sibling runner: verb prefix to `(rc, stdout, stderr)`.
    struct ScriptRunner {
        replies: HashMap<String, (i32, String, String)>,
        calls: RefCell<Vec<String>>,
        larch_calls: RefCell<Vec<String>>,
    }

    impl ScriptRunner {
        fn new(replies: &[(&str, i32, &str)]) -> Self {
            Self {
                replies: replies
                    .iter()
                    .map(|(verb, rc, stdout)| {
                        (
                            (*verb).to_owned(),
                            (*rc, (*stdout).to_owned(), String::new()),
                        )
                    })
                    .collect(),
                calls: RefCell::new(Vec::new()),
                larch_calls: RefCell::new(Vec::new()),
            }
        }

        /// A runner whose matched verb also answers on stderr.
        fn with_stderr(replies: &[(&str, i32, &str)], verb: &str, stderr: &str) -> Self {
            let mut runner = Self::new(replies);
            if let Some(reply) = runner.replies.get_mut(verb) {
                reply.2 = stderr.to_owned();
            }
            runner
        }

        fn reply(&self, args: &[std::ffi::OsString], larch: bool) -> CapturedRun {
            let joined = args
                .iter()
                .map(|arg| arg.to_string_lossy().into_owned())
                .collect::<Vec<_>>()
                .join(" ");
            self.calls.borrow_mut().push(joined.clone());
            if larch {
                self.larch_calls.borrow_mut().push(joined.clone());
            }
            let matched = self
                .replies
                .iter()
                .find(|(verb, _reply)| joined.starts_with(verb.as_str()))
                .map(|(_verb, reply)| reply.clone());
            let (rc, stdout, stderr) = matched.unwrap_or((0, String::new(), String::new()));
            CapturedRun { rc, stdout, stderr }
        }

        fn ran(&self, prefix: &str) -> bool {
            self.calls
                .borrow()
                .iter()
                .any(|call| call.starts_with(prefix))
        }

        /// Whether the verb ran through the Rust-owned bootstrap, not `cli.py`.
        fn ran_larch(&self, prefix: &str) -> bool {
            self.larch_calls
                .borrow()
                .iter()
                .any(|call| call.starts_with(prefix))
        }

        /// The first recorded argv for `prefix`, or an empty string.
        fn call(&self, prefix: &str) -> String {
            self.calls
                .borrow()
                .iter()
                .find(|call| call.starts_with(prefix))
                .cloned()
                .unwrap_or_default()
        }
    }

    impl SiblingRunner for ScriptRunner {
        fn run_larch(&self, args: &[std::ffi::OsString]) -> CapturedRun {
            self.reply(args, true)
        }

        fn run_python(&self, args: &[std::ffi::OsString]) -> CapturedRun {
            self.reply(args, false)
        }
    }

    /// One design tmpdir prepared to the state publish expects at entry.
    struct Session {
        _root: TempDir,
        tmpdir: std::path::PathBuf,
    }

    impl Session {
        fn new() -> Self {
            let root = TempDir::new().expect("temporary root");
            let tmpdir = root.path().join("design");
            fs::create_dir_all(tmpdir.join(".completed")).expect("completed dir");
            fs::write(tmpdir.join(".completed").join("step-5b"), b"").expect("step-5b sentinel");
            fs::write(tmpdir.join(".completed").join("step-3"), b"").expect("step-3 sentinel");
            fs::write(tmpdir.join("plan.txt"), CONTRACT_PLAN).expect("plan.txt");
            fs::write(tmpdir.join("composed-plan.md"), CONTRACT_PLAN).expect("composed plan");
            fs::write(tmpdir.join("architecture-diagram.skipped"), b"")
                .expect("diagram skip marker");
            fs::write(tmpdir.join(".completed").join("step-5b.5"), b"")
                .expect("step-5b.5 sentinel");
            Self {
                _root: root,
                tmpdir,
            }
        }

        fn args(&self) -> PublishArgs {
            PublishArgs {
                design_tmpdir: self.tmpdir.display().to_string(),
                issue: "8591".to_owned(),
                session_id: String::new(),
                claude_pid: "4242".to_owned(),
                repo: String::new(),
                skip_validate: true,
            }
        }

        fn result_env(&self) -> String {
            fs::read_to_string(self.tmpdir.join(PUBLISH_RESULT_FILE)).unwrap_or_default()
        }

        /// Write one design-tmpdir artifact.
        fn write(&self, name: &str, body: &str) {
            fs::write(self.tmpdir.join(name), body).expect("design artifact");
        }

        /// Read one design-tmpdir artifact, empty when absent.
        fn read(&self, name: &str) -> String {
            fs::read_to_string(self.tmpdir.join(name)).unwrap_or_default()
        }

        fn exists(&self, name: &str) -> bool {
            self.tmpdir.join(name).is_file()
        }

        fn remove(&self, name: &str) {
            fs::remove_file(self.tmpdir.join(name)).expect("unlink design artifact");
        }

        fn write_review_provenance(&self, status: &str, rounds: u32) {
            fs::write(
                self.tmpdir.join(".step3-review-result.env"),
                format!("STEP3_REVIEW_LOOP_STATUS={status}\nROUNDS_COMPLETED={rounds}\n"),
            )
            .expect("review provenance");
        }

        /// Persist the clean Gate C notes both assessment gates demand.
        fn write_clean_assessments(&self) {
            for kind in [AssessmentKind::Invariants, AssessmentKind::Guidelines] {
                fs::write(
                    self.tmpdir.join(kind.design_assessment_filename()),
                    format!("{}\n", kind.clean_presentation_note()),
                )
                .expect("assessment note");
            }
        }

        /// A session whose provenance and Gate C notes clear every pre-write gate.
        fn ready() -> Self {
            let session = Self::new();
            session.write_review_provenance("complete", 1);
            session.write_clean_assessments();
            session
        }

        /// A reviewed session with no Gate C notes, for the assessment ladder.
        fn reviewed() -> Self {
            let session = Self::new();
            session.write_review_provenance("complete", 1);
            session
        }

        /// Persist one Gate C note, replacing whatever that kind already had.
        fn write_assessment(&self, kind: AssessmentKind, note: &str) {
            self.write(kind.design_assessment_filename(), note);
        }

        /// Reopen the Step 5b.5 gate with one diagram candidate to sanitize.
        fn stage_diagram_candidate(&self, body: &str) {
            self.remove(".completed/step-5b.5");
            self.remove("architecture-diagram.skipped");
            self.write("architecture-diagram.candidate.md", body);
        }
    }

    /// A note whose cited invariant identifier classifies it as a violation.
    const INVARIANT_VIOLATION_NOTE: &str = "I-Core-1 is violated by this plan.\n";
    /// A note whose cited guideline identifier classifies it as a deviation.
    const GUIDELINE_DEVIATION_NOTE: &str = "G-Py-4 applies to this plan.\n";

    /// The plan-size reply publish needs to reach the gates.
    const SIZE_OK: (&str, i32, &str) = (
        "plan check-size",
        0,
        "PLAN_SIZE_STATUS=ok\nSIZE_TRIGGER_FIRED=false\n",
    );

    fn env_value(text: &str, key: &str) -> String {
        super::super::kv_last(text, key)
    }

    #[test]
    fn absent_step_5b_sentinel_fails_before_any_sibling_runs() {
        let session = Session::new();
        fs::remove_file(session.tmpdir.join(".completed").join("step-5b"))
            .expect("unlink sentinel");
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, RC_FAILED);
        assert!(runner.calls.borrow().is_empty());
        assert!(session.result_env().is_empty());
    }

    #[test]
    fn empty_composed_plan_refuses_with_the_validate_defect_rows() {
        let session = Session::new();
        fs::write(session.tmpdir.join("composed-plan.md"), "").expect("truncate composed plan");
        fs::write(session.tmpdir.join("plan.txt"), "").expect("truncate source plan");
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, RC_REFUSED);
        let recorded = session.result_env();
        assert_eq!(env_value(&recorded, "VALIDATE_STATUS"), "defects-found");
        assert_eq!(env_value(&recorded, "VALIDATE_DEFECT_COUNT"), "1");
        assert_eq!(env_value(&recorded, "PLAN_WRITE_OK"), "false");
    }

    #[test]
    fn blocked_review_provenance_refuses_before_the_plan_write() {
        let session = Session::new();
        session.write_review_provenance("panel-skipped", 0);
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, RC_REFUSED);
        let recorded = session.result_env();
        assert_eq!(
            env_value(&recorded, "PUBLISH_REFUSE_REASON"),
            "review-provenance:panel-skipped"
        );
        assert!(!runner.ran("named-block write"));
    }

    #[test]
    fn oversize_plan_without_an_override_refuses_with_the_size_reason() {
        let session = Session::ready();
        let runner = ScriptRunner::new(&[(
            "plan check-size",
            0,
            "PLAN_SIZE_STATUS=ok\nSIZE_TRIGGER_FIRED=true\n",
        )]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, RC_REFUSED);
        assert_eq!(
            env_value(&session.result_env(), "PUBLISH_REFUSE_REASON"),
            "oversize-no-override"
        );
        assert!(!runner.ran("named-block write"));
    }

    #[test]
    fn a_failed_size_check_refuses_rather_than_publishing() {
        let session = Session::ready();
        let runner = ScriptRunner::new(&[("plan check-size", 1, "")]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, RC_REFUSED);
        assert_eq!(
            env_value(&session.result_env(), "PUBLISH_REFUSE_REASON"),
            "size-check-failed"
        );
    }

    #[test]
    fn a_pause_request_hands_the_publish_off_to_pause_save() {
        let session = Session::ready();
        fs::write(session.tmpdir.join(".pause-requested"), b"").expect("pause request");
        let runner = ScriptRunner::new(&[SIZE_OK, ("design pause-save", 7, "")]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, 7);
        assert!(runner.ran_larch("design pause-save"));
        assert!(!runner.ran("named-block write"));
    }

    #[test]
    fn a_failed_plan_write_stages_the_terminal_state_and_reports_exit_one() {
        let session = Session::ready();
        let runner = ScriptRunner::new(&[SIZE_OK, ("named-block write", 1, "")]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, 1);
        let recorded = session.result_env();
        assert_eq!(env_value(&recorded, "PLAN_WRITE_OK"), "false");
        assert!(!runner.ran("tracking-issue rename"));
        assert!(
            session
                .tmpdir
                .join("design-plan-write.failure.log")
                .is_file()
        );
    }

    #[test]
    fn every_checkpointed_row_stays_inside_the_publish_allowlist() {
        let session = Session::ready();
        let runner = ScriptRunner::new(&[
            SIZE_OK,
            (
                "tracking-issue rename",
                0,
                "RENAMED=true\nNEW_TITLE=[DESIGNED] example\n",
            ),
            ("diagrams upsert", 0, "UPSERT_STATUS=ok\n"),
        ]);

        let receipt = ScriptReceipt::ok();
        let rc = publish_core(&runner, &receipt, &session.args());

        assert_eq!(rc, 0);
        assert_eq!(*receipt.calls.borrow(), 1);
        let recorded = session.result_env();
        // The shared reader drops any key outside the allowlist, so an equal row
        // count proves publish emitted nothing the wire contract forbids.
        let allowlisted = phase_driver_read_result_env(
            &session.tmpdir.join(PUBLISH_RESULT_FILE),
            &larch_core::PUBLISH_RESULT_ENV_ALLOW,
        )
        .expect("result env reads");
        assert_eq!(
            allowlisted.len(),
            recorded.lines().filter(|line| !line.is_empty()).count(),
            "result env carries a row outside the publish allowlist"
        );
        assert_eq!(env_value(&recorded, "PLAN_WRITE_OK"), "true");
        assert_eq!(env_value(&recorded, "LATEST_PHASE"), "complete");
        assert_eq!(env_value(&recorded, "DESIGNED_ADMISSION_READY"), "true");
        assert_eq!(env_value(&recorded, "VALIDATE_STATUS"), "skipped");
    }

    #[test]
    fn a_failed_receipt_write_reverts_the_plan_write_row_and_reports_exit_one() {
        let session = Session::ready();
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let rc = publish_core(
            &runner,
            &ScriptReceipt::failing("plan-receipt-readback-mismatch"),
            &session.args(),
        );

        assert_eq!(rc, 1);
        let recorded = session.result_env();
        assert_eq!(env_value(&recorded, "PLAN_WRITE_OK"), "false");
        assert!(!runner.ran("tracking-issue rename"));
    }

    #[test]
    fn the_argv_scanner_accepts_the_documented_publish_line() {
        let parsed = parse_publish_args(&[
            "--design-tmpdir".into(),
            "/tmp/design".into(),
            "--issue".into(),
            "8591".into(),
            "--session-id".into(),
            "".into(),
            "--claude-pid".into(),
            "4242".into(),
            "--skip-validate".into(),
        ])
        .expect("documented argv");

        assert_eq!(parsed.issue, "8591");
        assert!(parsed.session_id.is_empty());
        assert!(parsed.skip_validate);
    }

    #[test]
    fn the_argv_scanner_rejects_the_malformed_publish_lines() {
        for argv in [
            vec!["--issue".into(), "8591".into()],
            vec![
                "--design-tmpdir".into(),
                "/tmp/design".into(),
                "--issue".into(),
                "0".into(),
                "--session-id".into(),
                "".into(),
                "--claude-pid".into(),
                "4242".into(),
            ],
            vec![
                "--design-tmpdir".into(),
                "/tmp/design".into(),
                "--issue".into(),
                "8591".into(),
                "--claude-pid".into(),
                "4242".into(),
            ],
            vec![
                "--design-tmpdir".into(),
                "/tmp/design".into(),
                "--issue".into(),
                "8591".into(),
                "--session-id".into(),
                "".into(),
                "--claude-pid".into(),
                "4242".into(),
                "--repo".into(),
                "not-a-slug".into(),
            ],
        ] {
            assert_eq!(parse_publish_args(&argv).err(), Some(RC_FAILED));
        }
    }

    #[test]
    fn the_help_flag_exits_zero_without_publishing() {
        assert_eq!(parse_publish_args(&["--help".into()]).err(), Some(0));
        assert_eq!(parse_publish_args(&["-h".into()]).err(), Some(0));
    }

    #[test]
    fn a_missing_diagram_artifact_after_the_sentinel_only_warns() {
        let session = Session::ready();
        fs::remove_file(session.tmpdir.join("architecture-diagram.skipped"))
            .expect("unlink marker");
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, 0);
        assert!(!runner.ran("diagrams upsert"));
        let warnings = fs::read_to_string(session.tmpdir.join("execution-issues.md"))
            .expect("execution issues ledger");
        assert!(warnings.contains("diagram-artifact-missing-after-step5b5"));
    }

    #[test]
    fn a_stale_composed_plan_is_recomposed_before_the_gates_run() {
        let session = Session::ready();
        session.write("composed-plan.md", "stale\n");
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let _rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert!(!runner.ran("design compose-plan-md"));
        let composed = session.read("composed-plan.md");
        assert!(!composed.contains("stale"));
        assert!(composed.contains("### Closed decisions and ownership"));
        assert!(composed.contains("review_status: complete"));
    }

    #[test]
    fn the_bounded_phase_stderr_sidecar_keeps_only_its_tail() {
        let root = TempDir::new().expect("temporary root");
        let long = "x".repeat(super::super::TAIL_BYTE_CAP + 512);
        fs::create_dir_all(root.path()).expect("tmpdir");

        super::super::write_bounded_phase_stderr(root.path(), "tail.log", &long);

        let written = fs::read(root.path().join("tail.log")).expect("tail sidecar");
        assert_eq!(written.len(), super::super::TAIL_BYTE_CAP);
    }

    #[test]
    fn a_symlinked_result_env_is_refused_rather_than_followed() {
        let root = TempDir::new().expect("temporary root");
        let target = root.path().join("target.env");
        let link = root.path().join("link.env");
        fs::write(&target, "").expect("target");
        std::os::unix::fs::symlink(&target, &link).expect("symlink");

        let rows = super::super::Rows(vec![("PUBLISH_OK".to_owned(), "true".to_owned())]);

        assert!(super::super::write_publish_result_env(&link, &rows).is_err());
    }

    #[test]
    fn a_row_outside_the_allowlist_is_refused_by_the_result_env_writer() {
        let root = TempDir::new().expect("temporary root");
        let rows = super::super::Rows(vec![("NOT_ALLOWED".to_owned(), "x".to_owned())]);

        assert!(
            super::super::write_publish_result_env(&root.path().join("out.env"), &rows).is_err()
        );
    }

    /// Confirm the publish rows never leak a newline into the result env.
    #[test]
    fn a_newline_in_a_row_value_is_refused_by_the_result_env_writer() {
        let root = TempDir::new().expect("temporary root");
        let rows = super::super::Rows(vec![("NEW_TITLE".to_owned(), "a\nb".to_owned())]);

        assert!(
            super::super::write_publish_result_env(&root.path().join("out.env"), &rows).is_err()
        );
    }

    // -----------------------------------------------------------------------
    // Gate C assessment ladder and the executable-plan contract
    // -----------------------------------------------------------------------

    #[test]
    fn a_missing_invariant_assessment_refuses_with_its_gate_c_row_block() {
        let session = Session::reviewed();
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, RC_REFUSED);
        let recorded = session.result_env();
        assert_eq!(
            env_value(&recorded, "PUBLISH_REFUSE_REASON"),
            "missing-invariant-assessment"
        );
        assert_eq!(
            env_value(&recorded, "ARCH_INVARIANT_ASSESSMENT_REQUIRED"),
            "true"
        );
        assert_eq!(
            env_value(&recorded, "ARCH_INVARIANT_ASSESSMENT_PRESENT"),
            "false"
        );
        assert_eq!(
            env_value(&recorded, "ARCH_INVARIANT_ASSESSMENT_STATUS"),
            "missing"
        );
        assert_eq!(
            env_value(&recorded, "ARCH_INVARIANT_ASSESSMENT_ARTIFACT"),
            "architectural-invariant-assessment.md"
        );
        // The refusal resets the validate rows the skip had already recorded.
        assert_eq!(env_value(&recorded, "VALIDATE_STATUS"), "not-run");
        assert!(!runner.ran("named-block write"));
    }

    #[test]
    fn a_persisted_invariant_violation_refuses_before_the_plan_write() {
        let session = Session::reviewed();
        session.write_assessment(AssessmentKind::Invariants, INVARIANT_VIOLATION_NOTE);
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, RC_REFUSED);
        let recorded = session.result_env();
        assert_eq!(
            env_value(&recorded, "PUBLISH_REFUSE_REASON"),
            "invariant-violation"
        );
        assert_eq!(
            env_value(&recorded, "ARCH_INVARIANT_ASSESSMENT_STATUS"),
            "violation"
        );
        assert_eq!(
            env_value(&recorded, "ARCH_INVARIANT_ASSESSMENT_PRESENT"),
            "true"
        );
        assert!(!runner.ran("named-block write"));
    }

    #[test]
    fn a_missing_guideline_assessment_refuses_after_a_clean_invariant_note() {
        let session = Session::reviewed();
        session.write_assessment(
            AssessmentKind::Invariants,
            &format!("{}\n", AssessmentKind::Invariants.clean_presentation_note()),
        );
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, RC_REFUSED);
        let recorded = session.result_env();
        assert_eq!(
            env_value(&recorded, "PUBLISH_REFUSE_REASON"),
            "missing-guideline-assessment"
        );
        assert_eq!(
            env_value(&recorded, "ARCH_GUIDE_ASSESSMENT_STATUS"),
            "missing"
        );
        assert_eq!(
            env_value(&recorded, "ARCH_GUIDE_ASSESSMENT_ARTIFACT"),
            "architectural-guideline-assessment.md"
        );
        assert!(!runner.ran("named-block write"));
    }

    #[test]
    fn a_guideline_deviation_without_an_exception_refuses_before_the_plan_write() {
        let session = Session::reviewed();
        session.write_assessment(
            AssessmentKind::Invariants,
            &format!("{}\n", AssessmentKind::Invariants.clean_presentation_note()),
        );
        session.write_assessment(AssessmentKind::Guidelines, GUIDELINE_DEVIATION_NOTE);
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, RC_REFUSED);
        let recorded = session.result_env();
        assert_eq!(
            env_value(&recorded, "PUBLISH_REFUSE_REASON"),
            "invalid-guideline-deviation"
        );
        assert_eq!(
            env_value(&recorded, "ARCH_GUIDE_ASSESSMENT_STATUS"),
            "deviation"
        );
        assert_eq!(
            env_value(&recorded, "ARCH_GUIDE_ASSESSMENT_PRESENT"),
            "true"
        );
        assert!(!runner.ran("named-block write"));
    }

    #[test]
    fn a_documented_exception_lets_a_guideline_deviation_publish() {
        let session = Session::ready();
        session.write_assessment(
            AssessmentKind::Guidelines,
            "G-Py-4 applies to this plan.\n\
             Exception: ported verbatim (author: main-agent, date: 2026-07-13)\n",
        );
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, 0);
        assert!(runner.ran("named-block write"));
    }

    #[test]
    fn an_untracked_updated_path_refuses_with_the_plan_contract_defect() {
        let session = Session::ready();
        let plan = CONTRACT_PLAN.replace(
            "### UPDATED: AGENTS.md",
            "### UPDATED: docs/design-publish-untracked-8591.md",
        );
        session.write("plan.txt", &plan);
        session.write("composed-plan.md", &plan);
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, RC_REFUSED);
        let recorded = session.result_env();
        assert_eq!(
            env_value(&recorded, "PUBLISH_REFUSE_REASON"),
            "plan-contract:missing-updated-plan-path"
        );
        assert_eq!(env_value(&recorded, "VALIDATE_STATUS"), "defects-found");
        assert_eq!(env_value(&recorded, "VALIDATE_DEFECT_COUNT"), "1");
        assert!(!runner.ran("named-block write"));
    }

    // -----------------------------------------------------------------------
    // Step 5b.5 diagram sanitize gate
    // -----------------------------------------------------------------------

    #[test]
    fn an_accepted_diagram_candidate_is_promoted_and_upserted_from_its_file() {
        let session = Session::ready();
        session.stage_diagram_candidate("```mermaid\ngraph TD;\n  a --> b;\n```\n");
        session.write("architecture-diagram-sanitizer.failure.log", "stale\n");
        let runner = ScriptRunner::new(&[
            SIZE_OK,
            ("mermaid sanitize", 0, "STATUS=ok\n"),
            (
                "diagrams upsert",
                0,
                "UPSERT_STATUS=ok\nARCHITECTURE_SOURCE=design-tmpdir\n",
            ),
        ]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, 0);
        assert!(session.exists("architecture-diagram.md"));
        assert!(!session.exists("architecture-diagram.candidate.md"));
        assert!(session.exists(".completed/step-5b.5"));
        // Promotion clears the stale skip and failure sidecars.
        assert!(!session.exists("architecture-diagram.skipped"));
        assert!(!session.exists("architecture-diagram-sanitizer.failure.log"));
        assert!(
            runner
                .call("diagrams upsert")
                .contains("--architecture-file")
        );
        let recorded = session.result_env();
        assert_eq!(env_value(&recorded, "UPSERT_STATUS"), "ok");
        assert_eq!(env_value(&recorded, "ARCHITECTURE_SOURCE"), "design-tmpdir");
    }

    #[test]
    fn a_rejected_diagram_candidate_is_skipped_with_its_reason_token() {
        let session = Session::ready();
        session.stage_diagram_candidate("```mermaid\ngraph TD;\n```\n");
        let runner = ScriptRunner::new(&[
            SIZE_OK,
            (
                "mermaid sanitize",
                0,
                "STATUS=rejected\nREASON_TOKEN=unsafe-node\n",
            ),
        ]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, 0);
        assert!(session.exists("architecture-diagram.skipped"));
        assert!(!session.exists("architecture-diagram.candidate.md"));
        let failure = session.read("architecture-diagram-sanitizer.failure.log");
        assert!(failure.contains("reason=sanitizer-rejected:unsafe-node"));
        assert!(failure.contains("site=design Step 5b.5"));
        assert!(
            session
                .read("execution-issues.md")
                .contains("sanitizer-rejected:unsafe-node")
        );
        // A skipped diagram clears the issue's Architecture section.
        assert!(
            runner
                .call("diagrams upsert")
                .contains("--clear-architecture")
        );
    }

    #[test]
    fn a_missing_diagram_candidate_skips_the_gate_without_running_the_sanitizer() {
        let session = Session::ready();
        session.remove(".completed/step-5b.5");
        session.remove("architecture-diagram.skipped");
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, 0);
        assert!(!runner.ran("mermaid sanitize"));
        let failure = session.read("architecture-diagram-sanitizer.failure.log");
        assert!(failure.contains("reason=candidate-missing"));
        assert!(failure.contains("exit-code=2"));
        assert!(session.exists(".completed/step-5b.5"));
    }

    #[test]
    fn a_diagram_skip_that_cannot_be_recorded_fails_the_publish() {
        let session = Session::ready();
        session.remove(".completed/step-5b.5");
        session.remove("architecture-diagram.skipped");
        // A directory in the marker's place makes the skip write fail closed.
        fs::create_dir(session.tmpdir.join("architecture-diagram.skipped"))
            .expect("marker directory");
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, RC_FAILED);
        assert!(!runner.ran("named-block write"));
    }

    // -----------------------------------------------------------------------
    // plan validate
    // -----------------------------------------------------------------------

    /// The publish argv with `plan validate` left enabled.
    fn validating_args(session: &Session) -> PublishArgs {
        let mut args = session.args();
        args.skip_validate = false;
        args
    }

    #[test]
    fn an_ok_validate_status_records_its_rows_and_lets_publish_continue() {
        let session = Session::ready();
        let runner = ScriptRunner::new(&[
            SIZE_OK,
            (
                "plan validate",
                0,
                "VALIDATE_STATUS=ok\nVALIDATE_DEFECT_COUNT=0\nVALIDATE_SKIPPED_COUNT=2\n\
                 VALIDATE_UNSAFE_TOKEN_COUNT=0\n",
            ),
        ]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &validating_args(&session));

        assert_eq!(rc, 0);
        let recorded = session.result_env();
        assert_eq!(env_value(&recorded, "VALIDATE_STATUS"), "ok");
        assert_eq!(env_value(&recorded, "VALIDATE_SKIPPED_COUNT"), "2");
        assert_eq!(env_value(&recorded, "VALIDATE_MISSING_SCRIPT_COUNT"), "0");
        assert!(runner.ran("plan validate"));
    }

    #[test]
    fn validate_defects_refuse_and_carry_the_missing_script_count() {
        let session = Session::ready();
        session.write(
            "validate-plan-commands.log",
            "DEFECT plan kind=missing-script path=scripts/a.sh\n\
             DEFECT plan kind=unsafe-token path=scripts/b.sh\n\
             DEFECT plan kind=missing-script path=scripts/c.sh\n",
        );
        let log = session
            .tmpdir
            .join("validate-plan-commands.log")
            .display()
            .to_string();
        let runner = ScriptRunner::new(&[
            SIZE_OK,
            (
                "plan validate",
                0,
                &format!(
                    "VALIDATE_STATUS=defects-found\nVALIDATE_DEFECT_COUNT=3\n\
                     VALIDATE_UNSAFE_TOKEN_COUNT=1\nVALIDATE_LOG_FILE={log}\n"
                ),
            ),
        ]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &validating_args(&session));

        assert_eq!(rc, RC_REFUSED);
        let recorded = session.result_env();
        assert_eq!(env_value(&recorded, "VALIDATE_STATUS"), "defects-found");
        assert_eq!(env_value(&recorded, "VALIDATE_DEFECT_COUNT"), "3");
        assert_eq!(env_value(&recorded, "VALIDATE_UNSAFE_TOKEN_COUNT"), "1");
        assert_eq!(env_value(&recorded, "VALIDATE_MISSING_SCRIPT_COUNT"), "2");
        assert_eq!(env_value(&recorded, "VALIDATE_LOG_FILE"), log);
        assert!(!runner.ran("named-block write"));
    }

    #[test]
    fn a_validate_status_that_is_neither_ok_nor_defects_found_fails_hard() {
        let session = Session::ready();
        let runner = ScriptRunner::new(&[SIZE_OK, ("plan validate", 0, "VALIDATE_STATUS=error\n")]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &validating_args(&session));

        assert_eq!(rc, RC_FAILED);
        assert!(!runner.ran("named-block write"));
    }

    #[test]
    fn a_silent_validate_run_falls_back_to_the_not_run_rows_and_fails() {
        let session = Session::ready();
        let runner = ScriptRunner::new(&[SIZE_OK, ("plan validate", 1, "")]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &validating_args(&session));

        assert_eq!(rc, RC_FAILED);
        assert!(!runner.ran("named-block write"));
    }

    // -----------------------------------------------------------------------
    // log publish
    // -----------------------------------------------------------------------

    /// The publish argv with a session id and an explicit repository slug.
    fn publishing_args(session: &Session) -> PublishArgs {
        let mut args = session.args();
        args.session_id = "run-2026-08-20-design-publish".to_owned();
        args.repo = "agent-sh/larch".to_owned();
        args
    }

    #[test]
    fn a_successful_log_publish_records_its_rows_through_the_rust_verb() {
        let session = Session::ready();
        let runner = ScriptRunner::new(&[
            SIZE_OK,
            (
                "design log-publish",
                0,
                "PUBLISH_OK=true\nPR_NUMBER=8754\nPR_URL=https://example.invalid/pr/8754\n\
                 REMOTE_KEY=origin\nCACHE_DIR=/tmp/larch-logs-cache\n",
            ),
        ]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &publishing_args(&session));

        assert_eq!(rc, 0);
        let recorded = session.result_env();
        assert_eq!(env_value(&recorded, "LOG_PUBLISH_ATTEMPTED"), "true");
        assert_eq!(env_value(&recorded, "LOG_PUBLISH_COMPLETED"), "true");
        assert_eq!(env_value(&recorded, "PUBLISH_OK"), "true");
        assert_eq!(env_value(&recorded, "PR_NUMBER"), "8754");
        assert_eq!(
            env_value(&recorded, "PR_URL"),
            "https://example.invalid/pr/8754"
        );
        assert_eq!(env_value(&recorded, "REMOTE_KEY"), "origin");
        assert_eq!(env_value(&recorded, "CACHE_DIR"), "/tmp/larch-logs-cache");
        assert_eq!(env_value(&recorded, "LATEST_PHASE"), "complete");
        // #8592 moved log publication into the Rust verb, so it must not reach
        // the Python dispatcher, and it carries the run id, outcome, and repo.
        assert!(runner.ran_larch("design log-publish"));
        let argv = runner.call("design log-publish");
        assert!(argv.contains("--run-id run-2026-08-20-design-publish"));
        assert!(argv.contains("--outcome approved"));
        assert!(argv.contains("--repo agent-sh/larch"));
        assert!(argv.contains("--issue 8591"));
    }

    #[test]
    fn a_failed_log_publish_without_a_recovery_branch_fails_at_its_phase() {
        let session = Session::ready();
        let runner = ScriptRunner::with_stderr(
            &[SIZE_OK, ("design log-publish", 1, "PUBLISH_OK=false\n")],
            "design log-publish",
            "remote rejected the log push\n",
        );

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &publishing_args(&session));

        assert_eq!(rc, RC_FAILED);
        let recorded = session.result_env();
        assert_eq!(env_value(&recorded, "LATEST_PHASE"), "log-publish-failed");
        assert_eq!(env_value(&recorded, "PUBLISH_OK"), "false");
        assert_eq!(env_value(&recorded, "LOG_PUBLISH_COMPLETED"), "false");
        assert!(
            session
                .read("design-publish-log.stderr.log")
                .contains("remote rejected the log push")
        );
    }

    #[test]
    fn a_recovery_branch_keeps_a_failed_log_push_from_failing_the_publish() {
        let session = Session::ready();
        let runner = ScriptRunner::new(&[
            SIZE_OK,
            (
                "design log-publish",
                1,
                "PUBLISH_OK=true\nRECOVERY_BRANCH=larch-logs-recovery-8591\n",
            ),
        ]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &publishing_args(&session));

        assert_eq!(rc, 0);
        let recorded = session.result_env();
        assert_eq!(
            env_value(&recorded, "RECOVERY_BRANCH"),
            "larch-logs-recovery-8591"
        );
        assert_eq!(
            env_value(&recorded, "LOG_RECOVERY_BRANCH"),
            "larch-logs-recovery-8591"
        );
        assert_eq!(env_value(&recorded, "LOG_PUBLISH_COMPLETED"), "true");
    }

    #[test]
    fn an_unpublished_log_ends_the_publish_at_zero_without_completing_it() {
        let session = Session::ready();
        let runner = ScriptRunner::new(&[SIZE_OK, ("design log-publish", 0, "PUBLISH_OK=false\n")]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &publishing_args(&session));

        assert_eq!(rc, 0);
        let recorded = session.result_env();
        assert_eq!(env_value(&recorded, "PUBLISH_OK"), "false");
        assert_eq!(env_value(&recorded, "LOG_PUBLISH_ATTEMPTED"), "true");
        assert_eq!(env_value(&recorded, "LOG_PUBLISH_COMPLETED"), "false");
    }

    #[test]
    fn a_scrubbed_secret_is_reported_without_failing_the_publish() {
        let session = Session::ready();
        let runner = ScriptRunner::new(&[
            SIZE_OK,
            (
                "design log-publish",
                0,
                "PUBLISH_OK=true\nSECRET_SCRUB_VIOLATIONS=2\n",
            ),
        ]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &publishing_args(&session));

        assert_eq!(rc, 0);
        assert_eq!(
            env_value(&session.result_env(), "LOG_PUBLISH_COMPLETED"),
            "true"
        );
    }

    #[test]
    fn a_failed_plan_write_publishes_its_logs_under_the_failure_outcome() {
        let session = Session::ready();
        let runner = ScriptRunner::new(&[
            SIZE_OK,
            ("named-block write", 1, ""),
            ("design log-publish", 0, "PUBLISH_OK=false\n"),
        ]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &publishing_args(&session));

        assert_eq!(rc, 1);
        assert!(runner.ran_larch("design log-publish"));
        assert!(
            runner
                .call("design log-publish")
                .contains("--outcome failed-plan-write")
        );
        assert_eq!(env_value(&session.result_env(), "PLAN_WRITE_OK"), "false");
    }

    // -----------------------------------------------------------------------
    // difficulty
    // -----------------------------------------------------------------------

    /// A raw design rating whose low confidence bumps `MODERATE` to `HARD`.
    const RAW_RATING: &str = concat!(
        "{\"predicted_tier\": \"MODERATE\", \"confidence\": \"low\", ",
        "\"rationale\": \"design plan metadata\"}\n"
    );

    #[test]
    fn a_raw_rating_syncs_the_label_writes_the_record_and_its_run_log_batch() {
        let session = Session::ready();
        session.write("design-difficulty-rating.raw.json", RAW_RATING);
        // `difficulty write-record` owns the record, so the recorded runner
        // cannot create it; publish only writes the batch when it exists.
        session.write("difficulty-rating.json", "{}\n");
        session.write("run-id.txt", "run-2026-08-20-design-publish\n");
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, 0);
        assert!(
            runner
                .call("difficulty sync-labels")
                .contains("--tier HARD")
        );
        let record = runner.call("difficulty write-record");
        assert!(record.contains("--design-tier HARD"));
        assert!(record.contains("--raw-rating-file"));
        assert!(record.contains("--design-raw-rating-file"));
        let batch = runner.call("run-log write");
        assert!(batch.contains("--batch difficulty-rating"));
        assert!(batch.contains("--skill design"));
        // The adjusted tier is spliced back into the published plan.
        assert!(
            session
                .read("composed-plan.md")
                .contains("difficulty: HARD")
        );
    }

    #[test]
    fn a_failed_difficulty_record_write_skips_the_run_log_batch() {
        let session = Session::ready();
        session.write("design-difficulty-rating.raw.json", RAW_RATING);
        session.write("difficulty-rating.json", "{}\n");
        let runner = ScriptRunner::new(&[SIZE_OK, ("difficulty write-record", 1, "")]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, 0);
        assert!(runner.ran("difficulty sync-labels"));
        assert!(!runner.ran("run-log write"));
    }

    #[test]
    fn a_recorded_rating_without_a_run_id_writes_no_run_log_batch() {
        let session = Session::ready();
        session.write("design-difficulty-rating.raw.json", RAW_RATING);
        session.write("difficulty-rating.json", "{}\n");
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, 0);
        // Without `run-id.txt` the batch needs an ambient run id.
        let ambient = std::env::var("RUN_ID").unwrap_or_default();
        assert_eq!(runner.ran("run-log write"), !ambient.is_empty());
    }

    #[test]
    fn an_unreadable_raw_rating_fails_the_publish_before_the_plan_write() {
        let session = Session::ready();
        session.write("design-difficulty-rating.raw.json", "not json\n");
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, RC_FAILED);
        assert!(!runner.ran("named-block write"));
    }

    // -----------------------------------------------------------------------
    // diagram upsert, pause, and the remaining hard failures
    // -----------------------------------------------------------------------

    #[test]
    fn a_failed_diagram_upsert_appends_a_redacted_run_log_failure() {
        let session = Session::ready();
        let runner = ScriptRunner::with_stderr(
            &[SIZE_OK, ("diagrams upsert", 1, "UPSERT_STATUS=failed\n")],
            "diagrams upsert",
            "diagram comment upsert failed\n",
        );

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, 0);
        assert_eq!(env_value(&session.result_env(), "UPSERT_STATUS"), "failed");
        let appended = runner.call("run-log append-failure");
        assert!(appended.contains("--redact"));
        assert!(appended.contains("--site design Step 5c.5"));
        assert!(
            session
                .read("diagrams-architecture-upsert.stderr")
                .contains("diagram comment upsert failed")
        );
    }

    #[test]
    fn a_pause_request_forwards_the_repository_slug_to_pause_save() {
        let session = Session::ready();
        session.write(".pause-requested", "");
        let runner = ScriptRunner::new(&[SIZE_OK, ("design pause-save", 0, "")]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &publishing_args(&session));

        assert_eq!(rc, 0);
        assert!(runner.ran_larch("design pause-save"));
        assert!(
            runner
                .call("design pause-save")
                .contains("--repo agent-sh/larch")
        );
    }

    #[test]
    fn a_size_check_without_a_trigger_row_refuses_as_a_failed_check() {
        let session = Session::ready();
        let runner = ScriptRunner::new(&[("plan check-size", 0, "PLAN_SIZE_STATUS=ok\n")]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, RC_REFUSED);
        assert_eq!(
            env_value(&session.result_env(), "PUBLISH_REFUSE_REASON"),
            "size-check-failed"
        );
    }

    #[test]
    fn a_symlinked_checkpoint_target_fails_the_publish_at_initialization() {
        let session = Session::ready();
        std::os::unix::fs::symlink(
            session.tmpdir.join("elsewhere.env"),
            session.tmpdir.join(PUBLISH_RESULT_FILE),
        )
        .expect("symlinked result env");
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, RC_FAILED);
        assert!(runner.calls.borrow().is_empty());
    }

    #[test]
    fn a_redacted_plan_that_cannot_be_written_fails_before_the_plan_write() {
        let session = Session::ready();
        fs::create_dir(session.tmpdir.join("composed-plan.redacted.md"))
            .expect("redacted plan directory");
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert_eq!(rc, RC_FAILED);
        assert!(!runner.ran("named-block write"));
    }

    // -----------------------------------------------------------------------
    // receipt seam and argv helpers
    // -----------------------------------------------------------------------

    #[test]
    fn only_the_protected_refusals_widen_a_receipt_write_to_the_whole_body() {
        for protected in [
            "missing-lease",
            "protected-body",
            "lease-run-mismatch",
            "foreign-lease-body-change",
            "foreign-marker-or-body-change",
            "invalid-lease",
            "invalid-named-block-request",
        ] {
            assert!(
                super::super::is_protected_named_block_refusal(protected),
                "{protected} is a protected-mutation refusal"
            );
        }
        for transient in ["stale-snapshot", "github-unreachable", "readback-mismatch"] {
            assert!(
                !super::super::is_protected_named_block_refusal(transient),
                "{transient} must not widen into a body write"
            );
        }
    }

    #[test]
    fn the_receipt_mutation_requests_the_named_block_before_the_body() {
        let repository =
            crate::github_repository_resolution::repository_ref("agent-sh/larch").expect("slug");
        let snapshot = larch_core::IssueMutationSnapshot {
            repository: repository.clone(),
            issue: 8591,
            title: "[DESIGNING] publish".to_owned(),
            body: "body".to_owned(),
            labels: std::collections::BTreeSet::new(),
            state: larch_core::GitHubIssueState::Open,
            updated_at: "2026-08-20T00:00:00Z".to_owned(),
        };

        let block =
            super::super::receipt_mutation(&repository, &snapshot, "updated".to_owned(), true);
        assert_eq!(block.marker.as_deref(), Some(larch_core::PLAN_MARKER));
        assert!(
            block
                .fields
                .contains(&larch_core::IssueMutationField::NamedBlock)
        );
        assert_eq!(block.expected_updated_at, snapshot.updated_at);
        assert_eq!(block.issue, 8591);

        let body =
            super::super::receipt_mutation(&repository, &snapshot, "updated".to_owned(), false);
        assert!(body.marker.is_none());
        assert!(body.lease.is_none());
        assert!(body.fields.contains(&larch_core::IssueMutationField::Body));
    }

    #[test]
    fn the_receipt_snapshot_state_maps_to_the_recorded_blocker_spelling() {
        assert_eq!(
            super::super::state_token(larch_core::GitHubIssueState::Open),
            "open"
        );
        assert_eq!(
            super::super::state_token(larch_core::GitHubIssueState::Closed),
            "closed"
        );
    }

    #[test]
    fn the_plan_named_block_lease_binds_to_the_ambient_run_id() {
        let lease = super::super::plan_named_block_lease();
        let ambient = ["RUN_ID", "LARCH_RUN_ID", "SESSION_ID"]
            .iter()
            .any(|key| std::env::var(key).is_ok_and(|value| !value.trim().is_empty()));
        assert_eq!(lease.is_some(), ambient);
        if let Some(lease) = lease {
            assert_eq!(lease.marker, larch_core::PLAN_MARKER);
            assert!(!lease.run_id.is_empty());
        }
    }

    #[test]
    fn an_offline_run_reports_whether_issue_mutation_is_denied() {
        let declared = std::env::var("LARCH_ISSUE_MUTATION_DENY").unwrap_or_default();
        let expected = matches!(
            declared.trim().to_lowercase().as_str(),
            "1" | "true" | "yes" | "on"
        );
        assert_eq!(super::super::mutation_denied(), expected);
    }

    #[test]
    fn a_minted_attempt_id_matches_the_durable_sidecar_grammar() {
        let hex = super::super::random_hex();
        assert_eq!(hex.len(), 16);
        assert!(hex.bytes().all(|byte| byte.is_ascii_hexdigit()));
        let attempt = super::super::resolve_attempt_id().expect("minted attempt id");
        assert!(larch_core::is_publish_attempt_id(&attempt));
    }

    #[test]
    fn the_failure_stage_argv_carries_only_the_publish_rows_that_are_set() {
        let root = TempDir::new().expect("temporary root");
        let rows = super::super::Rows(vec![
            (
                "PUBLISH_ATTEMPT_ID".to_owned(),
                "direct-1-abcdef01".to_owned(),
            ),
            ("LATEST_PHASE".to_owned(), "plan-write".to_owned()),
            ("PR_URL".to_owned(), String::new()),
        ]);

        let args = super::super::publish_failure_stage_args(
            root.path(),
            &rows,
            &root.path().join("detail.log"),
        );

        assert!(args.contains(&"--publish-attempt-id".to_owned()));
        assert!(args.contains(&"direct-1-abcdef01".to_owned()));
        assert!(args.contains(&"--latest-phase".to_owned()));
        assert!(!args.contains(&"--pr-url".to_owned()));
        assert!(args.contains(&"--bail-reason".to_owned()));
    }

    #[test]
    fn a_symlinked_phase_stderr_sidecar_is_refused_rather_than_followed() {
        let root = TempDir::new().expect("temporary root");
        let target = root.path().join("target.log");
        fs::write(&target, "original\n").expect("target");
        std::os::unix::fs::symlink(&target, root.path().join("rename.stderr.log"))
            .expect("symlink");

        super::super::write_bounded_phase_stderr(root.path(), "rename.stderr.log", "captured\n");

        assert_eq!(
            fs::read_to_string(&target).expect("target reads"),
            "original\n"
        );
    }

    #[test]
    fn the_argv_scanner_rejects_an_unknown_flag_and_a_missing_value() {
        assert_eq!(
            parse_publish_args(&["--not-a-flag".into()]).err(),
            Some(RC_FAILED)
        );
        assert_eq!(
            parse_publish_args(&["--issue".into()]).err(),
            Some(RC_FAILED)
        );
    }

    #[test]
    fn the_publish_entrypoint_reports_the_help_exit_code_without_publishing() {
        let code = super::super::design_publish_main(&["--help".into()]);
        assert_eq!(
            format!("{code:?}"),
            format!("{:?}", std::process::ExitCode::from(0_u8))
        );
    }

    /// Build one complete typed issue response for the loopback GitHub service.
    fn issue_response(number: u64, body: &str) -> serde_json::Value {
        let mut value: serde_json::Value = serde_json::from_str(include_str!(
            "../../../larch-adapters/fixtures/github_issue.json"
        ))
        .expect("valid issue fixture");
        value["id"] = serde_json::json!(number * 10);
        value["number"] = serde_json::json!(number);
        value["title"] = serde_json::json!("[DESIGNING] publish the plan");
        value["body"] = serde_json::json!(body);
        value["state"] = serde_json::json!("open");
        value["url"] = serde_json::json!(format!(
            "https://example.test/repos/owner/repo/issues/{number}"
        ));
        value["repository_url"] = serde_json::json!("https://example.test/repos/owner/repo");
        value["html_url"] =
            serde_json::json!(format!("https://github.com/owner/repo/issues/{number}"));
        value["labels"] = serde_json::json!([]);
        value["updated_at"] = serde_json::json!("2026-08-20T00:00:00Z");
        value
    }

    /// Start one loopback-only typed GitHub service for a receipt unit test.
    fn loopback_service(
        exchanges: impl IntoIterator<Item = larch_test_support::IssueServiceExchange>,
    ) -> (
        std::sync::Arc<dyn Fn() -> larch_adapters::github::OctocrabGitHubService + Send + Sync>,
        larch_test_support::IssueServiceStub,
    ) {
        let server =
            larch_test_support::IssueServiceStub::start(exchanges).expect("start issue stub");
        let base_url = server.base_url().to_owned();
        let factory: std::sync::Arc<
            dyn Fn() -> larch_adapters::github::OctocrabGitHubService + Send + Sync,
        > = std::sync::Arc::new(move || {
            larch_adapters::github::OctocrabGitHubService::with_test_base(&base_url)
        });
        (factory, server)
    }

    /// The receipt the publish path computes for one body and base commit.
    fn receipt_for(
        body: &str,
        base_sha: &str,
        blockers: &[larch_core::BlockerSnapshotRow],
    ) -> larch_core::PlanReceipt {
        let plan_inner = larch_core::parse_named_block(body, larch_core::PLAN_MARKER)
            .expect("plan block parses")
            .expect("plan block present");
        larch_core::PlanReceipt {
            plan_sha256: larch_core::hash_plan_block(&plan_inner),
            base_sha: base_sha.to_owned(),
            blockers_sha256: larch_core::hash_blocker_rows(blockers),
            owners_sha256: larch_core::hash_owner_rows(
                &larch_core::parse_owner_block(body).raw_rows,
            ),
        }
    }

    /// Drive a body to the fixed point where its receipt is already current.
    fn body_with_current_receipt(
        seed: &str,
        base_sha: &str,
        blockers: &[larch_core::BlockerSnapshotRow],
    ) -> String {
        let mut body = seed.to_owned();
        for _attempt in 0..4 {
            let next = larch_core::upsert_receipt(&body, &receipt_for(&body, base_sha, blockers))
                .expect("receipt upserts");
            if next == body {
                break;
            }
            body = next;
        }
        assert_eq!(
            larch_core::parse_receipt(&body).as_ref(),
            Some(&receipt_for(&body, base_sha, blockers)),
            "the served body must already carry the computed receipt"
        );
        body
    }

    #[test]
    fn an_already_current_receipt_read_verifies_without_a_second_mutation() {
        let repository =
            larch_test_support::GitRepository::builder(larch_test_support::GitFixture::Refs)
                .build()
                .expect("git fixture");
        let base_sha = crate::implement_bootstrap_continuation::resolve_revision_sha(
            repository.root(),
            "HEAD",
        )
        .expect("HEAD resolves");

        // Drive the receipt to its fixed point so the served body already
        // carries exactly the receipt this publish would compute. The write
        // then collapses to the read-verify branch and never mutates.
        let body = body_with_current_receipt(
            "<!-- larch:plan:start -->\n## Plan\n\n1. Do it.\n<!-- larch:plan:end -->\n",
            &base_sha,
            &[],
        );

        let (github, server) = loopback_service([
            larch_test_support::IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/8591",
                200,
                serde_json::to_vec(&issue_response(8591, &body)).expect("issue body"),
            )
            .expect("issue exchange"),
            larch_test_support::IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/8591/dependencies/blocked_by",
                200,
                b"[]".to_vec(),
            )
            .expect("dependency exchange"),
        ]);

        let outcome = crate::github_service::with_test_github_service(github, || {
            super::super::persist_published_plan_receipt("owner/repo", 8591, repository.root())
        });

        assert_eq!(outcome, Ok(()));
        let requests = server.finish().expect("stub completed");
        assert_eq!(requests.len(), 2);
        assert!(
            requests.iter().all(|request| request.method == "GET"),
            "an already-current receipt performs no mutation"
        );
    }

    #[test]
    fn a_body_without_a_plan_block_refuses_the_receipt_write() {
        let repository =
            larch_test_support::GitRepository::builder(larch_test_support::GitFixture::Refs)
                .build()
                .expect("git fixture");
        let (github, server) = loopback_service([larch_test_support::IssueServiceExchange::json(
            "GET",
            "/repos/owner/repo/issues/8591",
            200,
            serde_json::to_vec(&issue_response(8591, "No plan block here.\n")).expect("issue body"),
        )
        .expect("issue exchange")]);

        let outcome = crate::github_service::with_test_github_service(github, || {
            super::super::persist_published_plan_receipt("owner/repo", 8591, repository.root())
        });

        assert_eq!(outcome, Err("plan-block-missing-for-receipt".to_owned()));
        assert_eq!(server.finish().expect("stub completed").len(), 1);
    }

    #[test]
    fn a_documented_blocker_is_read_into_the_receipt_freshness_rows() {
        let repository =
            larch_test_support::GitRepository::builder(larch_test_support::GitFixture::Refs)
                .build()
                .expect("git fixture");
        let base_sha = crate::implement_bootstrap_continuation::resolve_revision_sha(
            repository.root(),
            "HEAD",
        )
        .expect("HEAD resolves");
        // A body-documented blocker contributes the same freshness row a native
        // `blocked_by` edge would, so its own snapshot is read and hashed.
        let blockers = [larch_core::BlockerSnapshotRow {
            number: 4242,
            state: "open".to_owned(),
            updated_at: "2026-08-20T00:00:00Z".to_owned(),
        }];
        let body = body_with_current_receipt(
            "Native blockers: #4242\n\
             <!-- larch:plan:start -->\n## Plan\n\n1. Do it.\n<!-- larch:plan:end -->\n",
            &base_sha,
            &blockers,
        );

        let (github, server) = loopback_service([
            larch_test_support::IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/8591",
                200,
                serde_json::to_vec(&issue_response(8591, &body)).expect("issue body"),
            )
            .expect("issue exchange"),
            larch_test_support::IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/8591/dependencies/blocked_by",
                200,
                b"[]".to_vec(),
            )
            .expect("dependency exchange"),
            larch_test_support::IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/4242",
                200,
                serde_json::to_vec(&issue_response(4242, "blocker body")).expect("blocker body"),
            )
            .expect("blocker exchange"),
        ]);

        let outcome = crate::github_service::with_test_github_service(github, || {
            super::super::persist_published_plan_receipt("owner/repo", 8591, repository.root())
        });

        assert_eq!(outcome, Ok(()));
        let requests = server.finish().expect("stub completed");
        assert!(
            requests
                .iter()
                .any(|request| request.path.ends_with("/issues/4242")),
            "the documented blocker must be read: {requests:?}"
        );
    }

    #[test]
    fn a_receipt_write_outside_a_repository_reports_its_setup_failure() {
        let root = TempDir::new().expect("temporary root");
        // The live writer resolves the base commit before it contacts GitHub,
        // so a directory that is not a checkout fails without any network use.
        let outcome = super::super::LiveReceiptWriter.persist("owner/repo", 8591, root.path());
        assert!(
            outcome.is_err(),
            "a non-repository cannot supply a base sha"
        );
    }

    #[test]
    fn a_failed_log_publish_reports_its_own_checkpoint_and_result_env_failures() {
        let session = Session::ready();
        // A symlinked result env is refused, so both the failure checkpoint and
        // the unpublished-log write must report rather than claim success.
        std::os::unix::fs::symlink(
            session.tmpdir.as_path().join("elsewhere.env"),
            session.tmpdir.as_path().join("refused.env"),
        )
        .expect("symlink");
        let result_env = session.tmpdir.as_path().join("refused.env");
        let context = super::super::LogPublishContext {
            design_tmpdir: session.tmpdir.as_path(),
            session_id: "RUN1",
            issue: "8591",
            repo: "owner/repo",
        };

        let failed = ScriptRunner::new(&[("design log-publish", 2, "")]);
        let mut rows = super::super::Rows(Vec::new());
        assert_eq!(
            super::super::run_log_publish(
                &failed,
                &context,
                &mut rows,
                &result_env,
                "approved",
                true
            ),
            Some(RC_FAILED)
        );
        assert_eq!(rows.get("PUBLISH_OK"), "false");

        let unpublished = ScriptRunner::new(&[("design log-publish", 0, "PUBLISH_OK=false\n")]);
        let mut rows = super::super::Rows(Vec::new());
        assert_eq!(
            super::super::run_log_publish(
                &unpublished,
                &context,
                &mut rows,
                &result_env,
                "approved",
                true
            ),
            Some(super::super::RC_RESULT_ENV)
        );
    }

    #[test]
    fn a_failed_plan_write_reports_a_refused_result_env_rather_than_exit_one() {
        let session = Session::ready();
        std::os::unix::fs::symlink(
            session.tmpdir.as_path().join("elsewhere.env"),
            session.tmpdir.as_path().join("refused.env"),
        )
        .expect("symlink");
        let runner = ScriptRunner::new(&[]);
        let mut rows = super::super::Rows(Vec::new());

        let code = super::super::finalize_failed_plan_write(
            &runner,
            None,
            session.tmpdir.as_path(),
            &mut rows,
            &session.tmpdir.as_path().join("refused.env"),
        );

        assert_eq!(code, super::super::RC_RESULT_ENV);
    }

    #[test]
    fn an_unwritable_composed_plan_fails_the_provenance_splice() {
        let session = Session::ready();
        // A directory where the composed plan belongs makes the splice write
        // fail, which must end the publish rather than proceed with stale text.
        fs::create_dir(session.tmpdir.as_path().join("composed-plan.dir"))
            .expect("occupy the composed plan path");
        let paths = super::super::PublishPaths {
            design_tmpdir: session.tmpdir.as_path().to_path_buf(),
            result_env: session.tmpdir.as_path().join(PUBLISH_RESULT_FILE),
            composed_plan: session.tmpdir.as_path().join("composed-plan.dir"),
            repo_root: session.tmpdir.as_path().to_path_buf(),
        };
        let provenance = larch_core::ReviewProvenance {
            status: "approved".to_owned(),
            rounds_completed: 2,
            present: true,
        };

        assert_eq!(
            super::super::stage_plan_text(&paths, &provenance).err(),
            Some(RC_FAILED)
        );
    }

    /// `Path` is only used through the helpers above; keep the import honest.
    const _: fn(&Path) -> bool = super::super::nonempty_file;
}
