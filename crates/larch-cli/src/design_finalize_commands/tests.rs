//! Focused state-machine coverage for the migrated design finalization owner.

#[cfg(test)]
mod design_finalize_commands_tests {
    use std::{
        cell::RefCell,
        collections::{BTreeMap, VecDeque},
        ffi::OsString,
        fs,
        path::{Path, PathBuf},
        process::ExitCode,
    };

    use super::super::*;
    use crate::design_step0_commands::ChildOutcome;

    fn child(code: i32, stdout: &str, stderr: &str) -> ChildOutcome {
        ChildOutcome {
            code,
            stdout: stdout.to_owned(),
            stderr: stderr.to_owned(),
        }
    }

    fn strings(values: &[&str]) -> Vec<String> {
        values.iter().map(|value| (*value).to_owned()).collect()
    }

    fn value_after<'a>(args: &'a [String], flag: &str) -> Option<&'a str> {
        args.iter()
            .position(|arg| arg == flag)
            .and_then(|index| args.get(index + 1))
            .map(String::as_str)
    }

    fn write(path: impl AsRef<Path>, contents: &str) {
        fs::write(path, contents).expect("write fixture");
    }

    #[derive(Default)]
    struct QueueRunner {
        calls: RefCell<Vec<Vec<String>>>,
        replies: RefCell<VecDeque<ChildOutcome>>,
    }

    impl QueueRunner {
        fn new(replies: impl IntoIterator<Item = ChildOutcome>) -> Self {
            Self {
                calls: RefCell::new(Vec::new()),
                replies: RefCell::new(replies.into_iter().collect()),
            }
        }
    }

    impl Step0Runner for QueueRunner {
        fn run(
            &self,
            _plugin_root: &Path,
            args: &[String],
            _env: &[(String, String)],
            _merge_stderr: bool,
        ) -> ChildOutcome {
            self.calls.borrow_mut().push(args.to_vec());
            self.replies
                .borrow_mut()
                .pop_front()
                .unwrap_or_else(|| child(0, "", ""))
        }
    }

    struct PublishRunner {
        code: i32,
        body: String,
        stderr: String,
        persist: bool,
    }

    impl PublishRunner {
        fn new(code: i32, body: &str, stderr: &str, persist: bool) -> Self {
            Self {
                code,
                body: body.to_owned(),
                stderr: stderr.to_owned(),
                persist,
            }
        }
    }

    impl Step0Runner for PublishRunner {
        fn run(
            &self,
            _plugin_root: &Path,
            args: &[String],
            env: &[(String, String)],
            _merge_stderr: bool,
        ) -> ChildOutcome {
            match args.get(1).map(String::as_str) {
                Some("publish") => {
                    let attempt = env
                        .iter()
                        .find(|(key, _)| key == "LARCH_DESIGN_PUBLISH_ATTEMPT_ID")
                        .map_or("", |(_, value)| value);
                    let body = format!("{}PUBLISH_ATTEMPT_ID={attempt}\n", self.body);
                    if self.persist {
                        let root = value_after(args, "--design-tmpdir").expect("design tmpdir");
                        write(Path::new(root).join(".design-publish-result.env"), &body);
                    }
                    child(self.code, &body, &self.stderr)
                }
                Some("render-final-summary") => {
                    let root = value_after(args, "--design-tmpdir").expect("design tmpdir");
                    write(
                        Path::new(root).join("final-summary.md"),
                        "# Final summary\n",
                    );
                    child(0, "", "")
                }
                Some("stage-terminal-state") => child(0, "STAGED=true\n", ""),
                Some("log-publish") => child(0, "PUBLISH_OK=true\nRECOVERY_BRANCH=\n", ""),
                _ => child(0, "", ""),
            }
        }
    }

    fn fixture() -> (tempfile::TempDir, PathBuf, PathBuf) {
        let sandbox = tempfile::tempdir().expect("sandbox");
        let design = sandbox.path().join("design");
        let plugin = sandbox.path().join("plugin");
        fs::create_dir_all(&design).expect("design directory");
        fs::create_dir_all(&plugin).expect("plugin directory");
        (sandbox, design, plugin)
    }

    fn wrapper_args(
        sandbox: &Path,
        design: &Path,
        plugin: &Path,
        session_id: &str,
        claude_pid: &str,
    ) -> Vec<OsString> {
        let source = sandbox.join("session.env");
        write(
            &source,
            &format!(
                "DESIGN_TMPDIR={}\nISSUE_NUMBER=8586\nSESSION_ID={session_id}\nREPO=acme/repo\n",
                design.display()
            ),
        );
        [
            "--session-env-path".into(),
            source.into_os_string(),
            "--plugin-root".into(),
            plugin.as_os_str().to_owned(),
            "--claude-pid".into(),
            claude_pid.into(),
        ]
        .into()
    }

    fn status(values: &[(&str, &str)]) -> BTreeMap<String, String> {
        values
            .iter()
            .map(|(key, value)| ((*key).to_owned(), (*value).to_owned()))
            .collect()
    }

    fn context(session_id: &str, repo: &str) -> StepCtx {
        StepCtx {
            issue: "8586".to_owned(),
            session_id: session_id.to_owned(),
            repo: repo.to_owned(),
            claude_pid: "123".to_owned(),
            standalone_heavy_failed: String::new(),
        }
    }

    #[test]
    fn plan_composition_helpers_cover_headers_trailers_and_acceptance() {
        let (_sandbox, design, _plugin) = fixture();
        assert!(
            split_plan_body_and_trailers(strings(&["one\n", "two\n"]))
                .1
                .is_empty()
        );
        let (body, trailers) =
            split_plan_body_and_trailers(strings(&["## Plan\n", "Body.\n", "diff_lines: 7\n"]));
        assert_eq!(body, strings(&["## Plan\n", "Body.\n"]));
        assert_eq!(trailers, strings(&["diff_lines: 7\n"]));
        assert_eq!(
            strip_leading_plan_header(&strings(&["\n", "## Plan  \r\n", "\n", "Body\n"])),
            strings(&["Body\n"])
        );
        assert!(digits("123") && !digits("") && !digits("12x"));

        let optional = design.join(".gate-b-optional-trailer-keys.values");
        write(
            &optional,
            "diff_added=10\ndiff_deleted=no\nmechanical_churn=true\nmechanical_churn=maybe\noversize_override=operator\nunknown=value\n",
        );
        assert_eq!(optional_trailer_lines(&optional).len(), 3);
        assert!(optional_trailer_lines(&design.join("missing")).is_empty());
        let (peeled_body, peeled) = peel_optional_trailers(strings(&[
            "Body\n",
            "diff_added: 2\n",
            "mechanical_churn: false",
            "\n",
        ]));
        assert_eq!(peeled_body, strings(&["Body\n"]));
        assert_eq!(peeled.len(), 2);

        assert!(
            trailers_from_sidecars(&design, strings(&["Body\n"]))
                .1
                .is_empty()
        );
        write(design.join("diff-lines.txt"), "not-a-number\n");
        assert!(
            trailers_from_sidecars(&design, strings(&["Body\n"]))
                .1
                .is_empty()
        );
        write(design.join("diff-lines.txt"), "42\n");
        assert_eq!(
            trailers_from_sidecars(&design, strings(&["Body\n"]))
                .1
                .last()
                .map(String::as_str),
            Some("diff_lines: 42\n")
        );
        assert_eq!(
            heading_level("### Testing strategy\n", Some("testing STRATEGY")),
            Some(3)
        );
        assert_eq!(heading_level("###No space", None), None);
        assert_eq!(
            heading_level("### Different", Some("Testing strategy")),
            None
        );
        assert!(
            acceptance_section(&strings(&[
                "### Testing strategy\n",
                "\n",
                "- Run the focused suite.\n",
                "### Next\n",
            ]))
            .contains("Run the focused suite")
        );
        assert_eq!(
            acceptance_section(&strings(&["### Testing strategy\n", "### Next\n"])),
            acceptance_section(&strings(&["Body\n"]))
        );

        auto_compose_plan_md(&design);
        write(design.join("plan.txt"), "");
        auto_compose_plan_md(&design);
        assert!(!design.join("composed-plan.md").exists());
        write(
            design.join("plan.txt"),
            "## Plan\n\n### Testing strategy\n\n- Run it.\n\n### Files\n\nBody.\n",
        );
        auto_compose_plan_md(&design);
        let composed = fs::read_to_string(design.join("composed-plan.md")).expect("composition");
        assert!(composed.contains("## Acceptance\n\n- Run it."));
        assert!(composed.ends_with("diff_lines: 42\n"));
        write(design.join("plan.txt"), "replacement\n");
        auto_compose_plan_md(&design);
        assert_eq!(
            fs::read_to_string(design.join("composed-plan.md")).unwrap(),
            composed
        );
        recompose_plan_md(&design);
        assert!(
            fs::read_to_string(design.join("composed-plan.md"))
                .unwrap()
                .contains("replacement")
        );
    }

    #[test]
    fn status_publish_and_tail_helpers_reject_unsafe_inputs() {
        let (_sandbox, design, _plugin) = fixture();
        assert!(validate_tmpdir(design.to_str().unwrap()).is_ok());
        assert!(validate_tmpdir(design.join("missing").to_str().unwrap()).is_err());
        let rows = read_env_rows(
            "PLAN_WRITE_OK=true\r\nPUBLISH_OK=true\nUNKNOWN=no\nPUBLISH_OK=false\n",
            STEP5C_STATUS_ALLOW,
        );
        assert_eq!(get(&env_map(&rows), "PUBLISH_OK"), "false");
        assert_eq!(get(&env_map(&rows), "MISSING"), "");
        let status_path = design.join("status.env");
        write_status(&status_path, &[("PLAN_WRITE_OK".into(), "true".into())]).unwrap();
        assert!(read_env_file(&status_path, STEP5C_STATUS_ALLOW).is_some());
        assert!(read_env_file(&design.join("missing"), STEP5C_STATUS_ALLOW).is_none());

        let mut ctx = context("run-1", "acme/repo");
        ctx.standalone_heavy_failed = "false".into();
        let values = status(&[
            ("PLAN_WRITE_OK", "true"),
            ("PUBLISH_OK", "true"),
            ("VALIDATE_STATUS", "ok"),
        ]);
        assert!(
            early_status_rows(&ctx, "5", true, "", "", false, &values)
                .contains(&("VALIDATE_STATUS".into(), "ok".into()))
        );
        assert!(
            final_status_rows(&ctx, 0, false, true, &values)
                .contains(&("CLEANUP_ELIGIBLE".into(), "true".into()))
        );

        let result = design.join(".design-publish-result.env");
        write(
            &result,
            "PLAN_WRITE_OK=true\nPUBLISH_OK=true\nPUBLISH_ATTEMPT_ID=right\n",
        );
        let (primary, fallback) =
            safe_publish_values(&design, 0, "PUBLISH_OK=false\n", Some("right")).unwrap();
        assert!(!fallback && get(&primary, "PUBLISH_OK") == "true");
        assert!(safe_publish_values(&design, 0, "", Some("wrong")).is_err());
        let (fallback_values, fallback) =
            safe_publish_values(&design, 3, "PLAN_WRITE_OK=false\n", None).unwrap();
        assert!(fallback && get(&fallback_values, "PLAN_WRITE_OK") == "false");
        invalidate_publish_result(&design).unwrap();
        fs::create_dir(&result).unwrap();
        assert!(invalidate_publish_result(&design).is_err());
        fs::remove_dir(&result).unwrap();

        assert_eq!(
            bounded_tail(&"x".repeat(TAIL_BYTE_CAP + 11)).len(),
            TAIL_BYTE_CAP
        );
        assert_eq!(
            copy_tail(&design, "tail.log", "tail contents"),
            "tail contents"
        );
        assert_eq!(phase_tail(&design, "tail.log"), "tail contents");
        assert_eq!(phase_tail(&design, "absent.log"), "");
    }

    #[test]
    fn failure_summary_helpers_cover_staging_and_confinement() {
        let (_sandbox, design, plugin) = fixture();
        write(
            design.join("design-publish-rename.stderr.log"),
            "rename failed\n",
        );
        write(
            design.join("design-publish-log.stderr.log"),
            "log publish failed\n",
        );
        let result = status(&[
            ("LATEST_PHASE", "rename"),
            ("PLAN_WRITE_OK", "true"),
            ("PUBLISH_OK", "false"),
            ("RENAMED", "false"),
            ("LOG_PUBLISH_ATTEMPTED", "true"),
            ("LOG_PUBLISH_COMPLETED", "false"),
            ("PR_URL", "https://example.test/pr/1"),
        ]);
        render_publish_failure_detail(
            &design,
            5,
            "exception",
            &result,
            "publish stdout",
            "Traceback: Error: publish exploded",
        )
        .unwrap();
        let detail = fs::read_to_string(design.join("design-publish-tail.failure.log")).unwrap();
        assert!(detail.contains("traceback=") && detail.contains("[rename_stderr]"));

        for staged in [child(0, "STAGED=false\n", ""), child(9, "", "stage stderr")] {
            let runner = QueueRunner::new([staged]);
            stage_failed_publish_tail(&runner, &plugin, &design, 5, &result);
            assert_eq!(runner.calls.borrow().len(), 2);
        }
        assert!(publish_evidence_present(
            &design,
            "PR_URL=https://example.test/pr/1\n"
        ));
        assert!(!publish_evidence_present(&design, "unrelated\n"));
        write(
            design.join(".design-publish-result.env"),
            "RECOVERY_BRANCH=recovery\n",
        );
        assert!(publish_evidence_present(&design, ""));
        fs::remove_file(design.join(".design-publish-result.env")).unwrap();

        let empty_ctx = context("", "");
        assert!(!try_central_failed_summary(
            &QueueRunner::default(),
            &plugin,
            &design,
            &empty_ctx,
            ""
        ));
        let ctx = context("run-1", "acme/repo");
        write(design.join("final-summary.md"), "summary\n");
        assert!(try_central_failed_summary(
            &QueueRunner::new([
                child(0, "PUBLISH_OK=true\nRECOVERY_BRANCH=\n", ""),
                child(0, "", ""),
            ]),
            &plugin,
            &design,
            &ctx,
            ""
        ));
        assert!(!try_central_failed_summary(
            &QueueRunner::new([child(1, "PUBLISH_OK=false\n", "")]),
            &plugin,
            &design,
            &ctx,
            ""
        ));

        let nested = design.join("nested");
        fs::create_dir(&nested).unwrap();
        assert!(confined_summary_path(&nested.join("summary.md"), &design).is_some());
        assert!(
            confined_summary_path(&design.parent().unwrap().join("outside.md"), &design).is_none()
        );
        let summary = design.join("final-summary.md");
        let alternate = nested.join("summary.md");
        write(&summary, "stale\n");
        write(&alternate, "stale alternate\n");
        assert!(!render_summary(
            &QueueRunner::new([child(1, "", "render failed")]),
            &plugin,
            &design,
            &ctx,
            "failed-publish-tail",
            &alternate,
        ));
        assert!(!summary.exists() && !alternate.exists());
        assert!(render_summary(
            &QueueRunner::new([child(0, "", "")]),
            &plugin,
            &design,
            &ctx,
            "approved",
            &summary,
        ));
        let status_path = design.join(".design-step5c-status.env");
        write_status(&status_path, &[("PLAN_WRITE_OK".into(), "true".into())]).unwrap();
        emit_summary(&design, &summary, &status_path);
        write(&summary, "ready\n");
        emit_summary(&design, &summary, &status_path);
        let rows = env_map(&read_env_file(&status_path, STEP5C_STATUS_ALLOW).unwrap());
        assert_eq!(get(&rows, "FINAL_SUMMARY_READY"), "true");
        failed_publish_finish(
            &PublishRunner::new(2, "", "", false),
            &plugin,
            &design,
            &empty_ctx,
            2,
            "",
            &result,
        );
    }

    #[test]
    fn step5c_error_and_fallback_paths_preserve_status_contract() {
        let (sandbox, design, plugin) = fixture();
        assert_eq!(
            step5c_with(&["--session-env-path".into()], &QueueRunner::default()),
            ExitCode::from(2)
        );
        let args = wrapper_args(sandbox.path(), &design, &plugin, "", "123");
        assert_eq!(
            step5c_with(&args, &QueueRunner::default()),
            ExitCode::from(1)
        );
        fs::create_dir_all(design.join(".completed")).unwrap();
        write(design.join(".completed/step-5b"), "");
        write(design.join(".pause-requested"), "");
        assert_eq!(
            step5c_with(&args, &QueueRunner::new([child(3, "pause\n", "paused\n")])),
            ExitCode::from(3)
        );
        fs::remove_file(design.join(".pause-requested")).unwrap();

        fs::create_dir(design.join(".design-publish-result.env")).unwrap();
        assert_eq!(
            step5c_with(&args, &PublishRunner::new(0, "", "", false)),
            ExitCode::from(1)
        );
        fs::remove_dir(design.join(".design-publish-result.env")).unwrap();
        for code in [2, 9] {
            assert_eq!(
                step5c_with(
                    &args,
                    &PublishRunner::new(code, "", "publish failed", false)
                ),
                ExitCode::from(1)
            );
        }

        let rc3 = PublishRunner::new(3, "PLAN_WRITE_OK=true\nPUBLISH_OK=true\n", "", false);
        assert_eq!(step5c_with(&args, &rc3), ExitCode::SUCCESS);
        let rows = env_map(
            &read_env_file(
                &design.join(".design-step5c-status.env"),
                STEP5C_STATUS_ALLOW,
            )
            .unwrap(),
        );
        assert_eq!(get(&rows, "PUBLISH_STDOUT_FALLBACK"), "true");
        let rc5 = PublishRunner::new(
            5,
            "PLAN_WRITE_OK=false\nPUBLISH_OK=false\nPUBLISH_RC_SOURCE=\n",
            "Traceback: Error: tail failed",
            false,
        );
        assert_eq!(step5c_with(&args, &rc5), ExitCode::from(1));
        assert!(
            fs::read_to_string(design.join("design-publish-tail.failure.log"))
                .unwrap()
                .contains("rc_source=exception")
        );
        assert_eq!(
            step5c_with(
                &args,
                &PublishRunner::new(
                    4,
                    "PLAN_WRITE_OK=false\nPUBLISH_OK=false\nPUBLISH_REFUSE_REASON=unexpected\n",
                    "",
                    false,
                )
            ),
            ExitCode::SUCCESS
        );
        assert_eq!(
            step5c_with(
                &args,
                &PublishRunner::new(0, "PLAN_WRITE_OK=true\nPUBLISH_OK=true\n", "", true)
            ),
            ExitCode::SUCCESS
        );
    }

    #[test]
    fn step6_helpers_cover_pause_preservation_and_prelude() {
        let (sandbox, design, plugin) = fixture();
        let ctx = context("run-1", "acme/repo");
        assert_eq!(
            value_after(&pause_args(&design, &ctx), "--repo"),
            Some("acme/repo")
        );
        assert!(!step6_in_flight(None) && !step6_in_flight(Some(&design)));
        assert_eq!(
            pause_if_requested(&QueueRunner::default(), &plugin, Some(&design), &ctx),
            None
        );
        write(design.join(".pause-requested"), "");
        assert_eq!(
            pause_if_requested(
                &QueueRunner::new([child(4, "pause\n", "pause stderr\n")]),
                &plugin,
                Some(&design),
                &ctx,
            ),
            Some(4)
        );
        fs::remove_file(design.join(".pause-requested")).unwrap();

        for (values, expected) in [
            (status(&[("PLAN_WRITE_OK", "false")]), "plan write"),
            (
                status(&[
                    ("PLAN_WRITE_OK", "true"),
                    ("STANDALONE_HEAVY_FAILED", "true"),
                ]),
                "standalone heavy",
            ),
            (
                status(&[
                    ("PLAN_WRITE_OK", "true"),
                    ("SESSION_ID", "run"),
                    ("PUBLISH_OK", "false"),
                ]),
                "publish did not",
            ),
            (
                status(&[("PLAN_WRITE_OK", "true"), ("CLEANUP_ELIGIBLE", "false")]),
                "cleanup not eligible",
            ),
        ] {
            assert!(preservation_message(&values).unwrap().contains(expected));
        }
        assert!(
            preservation_message(&status(&[
                ("PLAN_WRITE_OK", "true"),
                ("PUBLISH_OK", "true"),
                ("CLEANUP_ELIGIBLE", "true"),
            ]))
            .is_none()
        );
        assert!(matches!(
            step6_request(&["--claude-pid".into()], "design-step6-test.sh"),
            Err(code) if code == ExitCode::from(2)
        ));

        let args = wrapper_args(sandbox.path(), &design, &plugin, "run-1", "123");
        write(
            design.join(".design-step5c-status.env"),
            "PLAN_WRITE_OK=false\nPUBLISH_OK=false\nSESSION_ID=run-1\nCLEANUP_ELIGIBLE=false\n",
        );
        assert_eq!(
            step6_prelude_with(&args, &QueueRunner::default()),
            ExitCode::SUCCESS
        );
        assert_eq!(
            step6_cleanup_with(&args, &QueueRunner::default()),
            ExitCode::SUCCESS
        );
        write(
            design.join(".design-step5c-status.env"),
            "PLAN_WRITE_OK=true\nPUBLISH_OK=true\nSESSION_ID=run-1\nCLEANUP_ELIGIBLE=true\n",
        );
        let timing = QueueRunner::default();
        assert_eq!(step6_prelude_with(&args, &timing), ExitCode::SUCCESS);
        assert!(design.join(".completed/step-5d").is_file());
        assert!(
            timing
                .calls
                .borrow()
                .iter()
                .any(|call| call.first().map(String::as_str) == Some("timing"))
        );
        let invalid_pid = wrapper_args(sandbox.path(), &design, &plugin, "run-1", "bad-pid");
        assert_eq!(
            step6_cleanup_with(&invalid_pid, &QueueRunner::default()),
            ExitCode::from(2)
        );
    }
}
