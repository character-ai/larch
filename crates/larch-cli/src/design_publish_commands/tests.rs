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

    /// A recorded sibling runner: verb prefix to `(rc, stdout)`.
    struct ScriptRunner {
        replies: HashMap<String, (i32, String)>,
        calls: RefCell<Vec<String>>,
    }

    impl ScriptRunner {
        fn new(replies: &[(&str, i32, &str)]) -> Self {
            Self {
                replies: replies
                    .iter()
                    .map(|(verb, rc, stdout)| ((*verb).to_owned(), (*rc, (*stdout).to_owned())))
                    .collect(),
                calls: RefCell::new(Vec::new()),
            }
        }

        fn reply(&self, args: &[std::ffi::OsString]) -> CapturedRun {
            let joined = args
                .iter()
                .map(|arg| arg.to_string_lossy().into_owned())
                .collect::<Vec<_>>()
                .join(" ");
            self.calls.borrow_mut().push(joined.clone());
            let matched = self
                .replies
                .iter()
                .find(|(verb, _reply)| joined.starts_with(verb.as_str()))
                .map(|(_verb, reply)| reply.clone());
            let (rc, stdout) = matched.unwrap_or((0, String::new()));
            CapturedRun {
                rc,
                stdout,
                stderr: String::new(),
            }
        }

        fn ran(&self, prefix: &str) -> bool {
            self.calls
                .borrow()
                .iter()
                .any(|call| call.starts_with(prefix))
        }
    }

    impl SiblingRunner for ScriptRunner {
        fn run_larch(&self, args: &[std::ffi::OsString]) -> CapturedRun {
            self.reply(args)
        }

        fn run_python(&self, args: &[std::ffi::OsString]) -> CapturedRun {
            self.reply(args)
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
    }

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
        assert!(runner.ran("design pause-save"));
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
        let runner = ScriptRunner::new(&[SIZE_OK]);

        let _rc = publish_core(&runner, &ScriptReceipt::ok(), &session.args());

        assert!(runner.ran("design compose-plan-md"));
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

    /// `Path` is only used through the helpers above; keep the import honest.
    const _: fn(&Path) -> bool = super::super::nonempty_file;
}
