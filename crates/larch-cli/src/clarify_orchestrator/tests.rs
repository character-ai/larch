//! Offline coverage for the `design clarify` phase machine (#8587).

#[cfg(test)]
mod clarify_orchestrator_tests {
    use super::super::*;
    use crate::clarify_commands::{GhComment, RepoResolveError};
    use std::cell::RefCell;
    use std::collections::BTreeSet;
    use tempfile::TempDir;

    /// A scripted GitHub-effects double for the orchestrator.
    #[derive(Default)]
    struct FakeEffects {
        comments: Vec<(u64, String)>,
        fail_state: bool,
        post_fails: bool,
        label_fails: bool,
    }

    impl ClarifyEffects for FakeEffects {
        fn resolve_repo(&self, repo: Option<&str>) -> Result<String, RepoResolveError> {
            Ok(repo.unwrap_or("owner/repo").to_owned())
        }

        fn list_comments(&self, _repo: &str, _issue: u64) -> Result<Vec<GhComment>, String> {
            if self.fail_state {
                return Err("boom".to_owned());
            }
            Ok(self
                .comments
                .iter()
                .map(|(id, body)| GhComment {
                    id: *id,
                    body: body.clone(),
                    url: String::new(),
                })
                .collect())
        }

        fn post_comment(&self, _repo: &str, _issue: u64, body: &str) -> Result<GhComment, String> {
            if self.post_fails {
                return Err("post failed".to_owned());
            }
            Ok(GhComment {
                id: 1,
                body: body.to_owned(),
                url: "https://github.com/o/r/issues/7#issuecomment-1".to_owned(),
            })
        }

        fn issue_labels(&self, _repo: &str, _issue: u64) -> Result<Vec<String>, String> {
            Ok(vec![CLARIFY_LABEL_NAME_TEST.to_owned()])
        }

        fn create_clarify_label(&self, _repo: &str) -> Result<(), String> {
            Ok(())
        }

        fn set_issue_labels(
            &self,
            _repo: &str,
            _issue: u64,
            _labels: BTreeSet<String>,
        ) -> Result<(), String> {
            if self.label_fails {
                return Err("label failed".to_owned());
            }
            Ok(())
        }
    }

    const CLARIFY_LABEL_NAME_TEST: &str = "needs-design-clarification";

    /// A scripted sibling runner recording calls and returning queued outputs.
    struct FakeRunner {
        larch_calls: RefCell<Vec<Vec<String>>>,
        python_calls: RefCell<Vec<Vec<String>>>,
        larch_stdout: RefCell<Vec<String>>,
        python_stdout: RefCell<Vec<String>>,
        larch_failures: RefCell<BTreeMap<String, i32>>,
    }

    impl FakeRunner {
        fn new() -> Self {
            Self {
                larch_calls: RefCell::new(Vec::new()),
                python_calls: RefCell::new(Vec::new()),
                larch_stdout: RefCell::new(Vec::new()),
                python_stdout: RefCell::new(Vec::new()),
                larch_failures: RefCell::new(BTreeMap::new()),
            }
        }

        fn queue_larch(self, stdout: &[&str]) -> Self {
            *self.larch_stdout.borrow_mut() = stdout.iter().map(|s| (*s).to_owned()).collect();
            self
        }

        #[allow(dead_code)]
        fn queue_python(self, stdout: &[&str]) -> Self {
            *self.python_stdout.borrow_mut() = stdout.iter().map(|s| (*s).to_owned()).collect();
            self
        }

        /// Answer the `"<verb> <subverb>"` call with a non-zero exit code.
        fn failing(self, verb: &str, rc: i32) -> Self {
            let _prior = self.larch_failures.borrow_mut().insert(verb.to_owned(), rc);
            self
        }

        fn larch_verbs(&self) -> Vec<(String, String)> {
            self.larch_calls
                .borrow()
                .iter()
                .filter_map(|call| Some((call.first()?.clone(), call.get(1)?.clone())))
                .collect()
        }
    }

    impl SiblingRunner for FakeRunner {
        fn run_larch(&self, args: &[OsString]) -> CapturedRun {
            let call: Vec<String> = args
                .iter()
                .map(|a| a.to_string_lossy().into_owned())
                .collect();
            let verb = call.iter().take(2).cloned().collect::<Vec<_>>().join(" ");
            self.larch_calls.borrow_mut().push(call);
            let stdout = if self.larch_stdout.borrow().is_empty() {
                String::new()
            } else {
                self.larch_stdout.borrow_mut().remove(0)
            };
            let rc = self
                .larch_failures
                .borrow()
                .get(&verb)
                .copied()
                .unwrap_or_default();
            CapturedRun {
                rc,
                stdout,
                stderr: if rc == 0 {
                    String::new()
                } else {
                    format!("{verb} failed\n")
                },
            }
        }

        fn run_python(&self, args: &[OsString]) -> CapturedRun {
            let call: Vec<String> = args
                .iter()
                .map(|a| a.to_string_lossy().into_owned())
                .collect();
            self.python_calls.borrow_mut().push(call);
            let stdout = if self.python_stdout.borrow().is_empty() {
                String::new()
            } else {
                self.python_stdout.borrow_mut().remove(0)
            };
            CapturedRun {
                rc: 0,
                stdout,
                stderr: String::new(),
            }
        }
    }

    fn args(phase: &str) -> DesignClarifyArgs {
        DesignClarifyArgs {
            session_env_path: String::new(),
            claude_pid: String::new(),
            phase: phase.to_owned(),
            issue: "7".to_owned(),
        }
    }

    fn env_with_repo(dir: &Path) -> Env {
        let mut env: Env = BTreeMap::new();
        let _ = env.insert("REPO".to_owned(), "owner/repo".to_owned());
        let _ = env.insert("SESSION_ID".to_owned(), "RUN1".to_owned());
        let _ = env.insert("DESIGN_TMPDIR".to_owned(), dir.display().to_string());
        env
    }

    fn seed_publish(dir: &Path) {
        fs::write(
            dir.join("clarify-plan.md"),
            "## Plan\n\nDo it.\n\ndifficulty: MODERATE\n",
        )
        .unwrap();
        fs::write(dir.join("clarify-response.md"), "Response.\n").unwrap();
        let request = [
            "REQUEST_ID=2",
            &format!(
                "REQUEST_BODY_FILE={}",
                dir.join("clarify-request.md").display()
            ),
            &format!("PLAN_FILE={}", dir.join("clarify-plan.md").display()),
            &format!(
                "RESPONSE_FILE={}",
                dir.join("clarify-response.md").display()
            ),
            "ISSUE_NUMBER=7",
            "REPO=owner/repo",
            "",
        ]
        .join("\n");
        fs::write(dir.join(".design-clarify-request.env"), request).unwrap();
        fs::write(dir.join("final-summary.md"), "rendered summary\n").unwrap();
    }

    #[test]
    fn fetch_happy_path_writes_request_and_result_envs() {
        let dir = TempDir::new().unwrap();
        let effects = FakeEffects {
            comments: vec![(
                44,
                "<!-- larch:clarify-request id=4 -->\nquestion\n".to_owned(),
            )],
            ..FakeEffects::default()
        };
        let runner = FakeRunner::new();
        let mut env = env_with_repo(dir.path());
        let code = design_clarify_run(&effects, &runner, &args("fetch"), &mut env, dir.path());
        assert!(matches!(code, ExitCode { .. }));
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-fetch-result.env")).unwrap();
        assert!(result.contains("CLARIFY_FETCH_STATUS=ok\n"));
        assert!(result.contains("REQUEST_ID=4\n"));
        assert!(result.contains("REPO=owner/repo\n"));
        assert_eq!(
            fs::read_to_string(dir.path().join("clarify-request.md")).unwrap(),
            "question\n"
        );
        let request_env =
            fs::read_to_string(dir.path().join(".design-clarify-request.env")).unwrap();
        assert!(request_env.contains("REQUEST_ID=4\n"));
        assert!(!request_env.contains("CLARIFY_FETCH_STATUS"));
    }

    #[test]
    fn fetch_result_env_write_failure_does_not_report_success() {
        let dir = TempDir::new().unwrap();
        // A symlink at the request-state sidecar makes write_result_env refuse,
        // so the driver must not go on to write the fetch-result env or claim ok.
        std::os::unix::fs::symlink(
            dir.path().join("elsewhere.env"),
            dir.path().join(".design-clarify-request.env"),
        )
        .unwrap();
        let effects = FakeEffects {
            comments: vec![(44, "<!-- larch:clarify-request id=4 -->\nq\n".to_owned())],
            ..FakeEffects::default()
        };
        let runner = FakeRunner::new();
        let mut env = env_with_repo(dir.path());
        let _ = design_clarify_run(&effects, &runner, &args("fetch"), &mut env, dir.path());
        assert!(!dir.path().join(".design-clarify-fetch-result.env").exists());
    }

    #[test]
    fn fetch_unexpected_state_stages_failure() {
        let dir = TempDir::new().unwrap();
        let effects = FakeEffects::default();
        let runner = FakeRunner::new();
        let mut env = env_with_repo(dir.path());
        let _ = design_clarify_run(&effects, &runner, &args("fetch"), &mut env, dir.path());
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-fetch-result.env")).unwrap();
        assert!(result.contains("CLARIFY_FETCH_STATUS=unexpected-state\n"));
        assert!(result.contains("SUMMARY_OUTCOME=failed-clarify\n"));
    }

    #[test]
    fn fetch_state_error_is_state_failed() {
        let dir = TempDir::new().unwrap();
        let effects = FakeEffects {
            fail_state: true,
            ..FakeEffects::default()
        };
        let runner = FakeRunner::new();
        let mut env = env_with_repo(dir.path());
        let _ = design_clarify_run(&effects, &runner, &args("fetch"), &mut env, dir.path());
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-fetch-result.env")).unwrap();
        assert!(result.contains("CLARIFY_FETCH_STATUS=state-failed\n"));
    }

    #[test]
    fn publish_happy_path_publishes_and_renames() {
        let dir = TempDir::new().unwrap();
        seed_publish(dir.path());
        let effects = FakeEffects::default();
        // named-block, sync-labels, run-log write, log-publish, upsert-summary, rename
        let runner =
            FakeRunner::new().queue_larch(&["", "", "", "PUBLISH_OK=true\n", "", "RENAMED=true\n"]);
        let mut env = env_with_repo(dir.path());
        let _ = design_clarify_run(&effects, &runner, &args("publish"), &mut env, dir.path());
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-publish-result.env")).unwrap();
        assert!(
            result.contains("CLARIFY_PUBLISH_STATUS=ok\n"),
            "got: {result}"
        );
        assert!(result.contains("PUBLISH_OK=true\n"));
        let verbs = runner.larch_verbs();
        assert!(verbs.contains(&("named-block".to_owned(), "write".to_owned())));
        assert!(verbs.contains(&("difficulty".to_owned(), "sync-labels".to_owned())));
        assert!(verbs.contains(&("tracking-issue".to_owned(), "upsert-summary".to_owned())));
        assert!(verbs.contains(&("tracking-issue".to_owned(), "rename".to_owned())));
        assert!(
            !fs::read_to_string(dir.path().join("clarify-plan.redacted.md"))
                .unwrap()
                .contains("REDACTED-TOKEN")
        );
    }

    #[test]
    fn publish_invalid_request_id_exits_two_without_result_env() {
        let dir = TempDir::new().unwrap();
        seed_publish(dir.path());
        fs::write(
            dir.path().join(".design-clarify-request.env"),
            "REQUEST_ID=0\nISSUE_NUMBER=7\nREPO=owner/repo\n",
        )
        .unwrap();
        let effects = FakeEffects::default();
        let runner = FakeRunner::new();
        let mut env = env_with_repo(dir.path());
        let _ = design_clarify_run(&effects, &runner, &args("publish"), &mut env, dir.path());
        assert!(
            !dir.path()
                .join(".design-clarify-publish-result.env")
                .exists()
        );
        assert!(runner.larch_calls.borrow().is_empty());
    }

    #[test]
    fn publish_missing_plan_artifact_fails() {
        let dir = TempDir::new().unwrap();
        seed_publish(dir.path());
        fs::remove_file(dir.path().join("clarify-plan.md")).unwrap();
        let effects = FakeEffects::default();
        let runner = FakeRunner::new();
        let mut env = env_with_repo(dir.path());
        let _ = design_clarify_run(&effects, &runner, &args("publish"), &mut env, dir.path());
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-publish-result.env")).unwrap();
        assert!(result.contains("CLARIFY_PUBLISH_STATUS=missing-artifact\n"));
    }

    #[test]
    fn publish_comment_failure_reports_failed_clarify() {
        let dir = TempDir::new().unwrap();
        seed_publish(dir.path());
        let effects = FakeEffects {
            post_fails: true,
            ..FakeEffects::default()
        };
        // named-block, sync-labels, run-log write, log-publish, upsert-summary
        let runner = FakeRunner::new().queue_larch(&["", "", "", "PUBLISH_OK=true\n", ""]);
        let mut env = env_with_repo(dir.path());
        let _ = design_clarify_run(&effects, &runner, &args("publish"), &mut env, dir.path());
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-publish-result.env")).unwrap();
        assert!(result.contains("CLARIFY_PUBLISH_STATUS=comment-post-failed\n"));
        let verbs = runner.larch_verbs();
        assert!(verbs.contains(&("tracking-issue".to_owned(), "upsert-summary".to_owned())));
        assert!(!verbs.contains(&("tracking-issue".to_owned(), "rename".to_owned())));
    }

    #[test]
    fn publish_missing_session_skips_publish() {
        let dir = TempDir::new().unwrap();
        seed_publish(dir.path());
        let effects = FakeEffects::default();
        let runner = FakeRunner::new();
        let mut env = env_with_repo(dir.path());
        let _ = env.remove("SESSION_ID");
        let _ = design_clarify_run(&effects, &runner, &args("publish"), &mut env, dir.path());
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-publish-result.env")).unwrap();
        assert!(result.contains("PUBLISH_OK=false\n"));
        let verbs = runner.larch_verbs();
        assert!(!verbs.contains(&("tracking-issue".to_owned(), "rename".to_owned())));
    }

    #[test]
    fn route_state_symlink_failure_is_phase_split() {
        let dir = TempDir::new().unwrap();
        fs::write(dir.path().join("target.env"), "REPO=owner/repo\n").unwrap();
        std::os::unix::fs::symlink(
            dir.path().join("target.env"),
            dir.path().join(".design-step0-route-state.env"),
        )
        .unwrap();
        let effects = FakeEffects::default();
        let runner = FakeRunner::new();
        let mut env: Env = BTreeMap::new();
        let _ = env.insert("DESIGN_TMPDIR".to_owned(), dir.path().display().to_string());
        let _ = design_clarify_run(&effects, &runner, &args("publish"), &mut env, dir.path());
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-publish-result.env")).unwrap();
        assert!(result.contains("CLARIFY_PUBLISH_STATUS=route-state-read-failed\n"));
    }

    #[test]
    fn write_result_env_rejects_symlink_newline_and_unlisted_key() {
        let dir = TempDir::new().unwrap();
        let target = dir.path().join("result.env");
        let link = dir.path().join("link.env");
        std::os::unix::fs::symlink(&target, &link).unwrap();
        let allow = &CLARIFY_RESULT_ENV_ALLOW;
        assert!(write_result_env(&link, &[("REQUEST_ID", "1")], allow).is_err());
        assert!(write_result_env(&target, &[("REQUEST_ID", "bad\nvalue")], allow).is_err());
        assert!(write_result_env(&target, &[("UNEXPECTED", "1")], allow).is_err());
        write_result_env(&target, &[("REQUEST_ID", "1"), ("PLAN_FILE", "2")], allow).unwrap();
        assert_eq!(
            fs::read_to_string(&target).unwrap(),
            "REQUEST_ID=1\nPLAN_FILE=2\n"
        );
    }

    #[test]
    fn parse_args_requires_phase_and_positive_issue() {
        assert!(parse_design_clarify_args(&osargs(&["--issue", "7"])).is_err());
        assert!(parse_design_clarify_args(&osargs(&["--phase", "fetch", "--issue", "0"])).is_err());
        assert!(parse_design_clarify_args(&osargs(&["--phase", "bogus", "--issue", "7"])).is_err());
        assert!(parse_design_clarify_args(&osargs(&["--unknown", "x"])).is_err());
        assert!(parse_design_clarify_args(&osargs(&["--issue"])).is_err());
        assert!(parse_design_clarify_args(&osargs(&["--help"])).is_err());
        assert!(
            parse_design_clarify_args(&osargs(&[
                "--phase",
                "publish",
                "--issue",
                "7",
                "--claude-pid",
                "x",
            ]))
            .is_err()
        );
        let parsed = parse_design_clarify_args(&osargs(&[
            "--phase",
            "publish",
            "--issue",
            "7",
            "--claude-pid",
            "42",
        ]))
        .unwrap();
        assert_eq!(parsed.phase, "publish");
        assert_eq!(parsed.claude_pid, "42");
    }

    #[test]
    fn pure_helpers_cover_their_branches() {
        assert_eq!(kv_last("A=1\r\nB=2\nB=3\n", "B"), "3");
        assert_eq!(kv_last("A=1\n", "MISSING"), "");
        assert_eq!(osargs(&["a", "b"]).len(), 2);
        let dir = TempDir::new().unwrap();
        let present = dir.path().join("p.md");
        fs::write(&present, "body").unwrap();
        assert!(publish_artifact_ok(&present));
        assert!(!publish_artifact_ok(&dir.path().join("absent")));
        let empty = dir.path().join("empty.md");
        fs::write(&empty, "").unwrap();
        assert!(!publish_artifact_ok(&empty));
        assert_eq!(read_lossy(present.to_str().unwrap()), "body");
        assert_eq!(read_lossy(dir.path().join("absent").to_str().unwrap()), "");
    }

    #[test]
    fn resolve_publish_difficulty_reads_plan_and_sidecar() {
        let dir = TempDir::new().unwrap();
        // No sidecar, difficulty from the plan trailer.
        let (rating, invalid) =
            resolve_publish_difficulty_rating(dir.path(), "## Plan\n\ndifficulty: HARD\n");
        assert!(!invalid);
        assert_eq!(rating.unwrap().adjusted_tier, "HARD");
        // No sidecar and no difficulty metadata -> neither a rating nor invalid.
        let (none, invalid) = resolve_publish_difficulty_rating(dir.path(), "just prose\n");
        assert!(none.is_none() && !invalid);
        // A present-but-unparseable raw sidecar is the invalid case.
        fs::write(
            dir.path().join("design-difficulty-rating.raw.json"),
            "{ not json",
        )
        .unwrap();
        let (none, invalid) = resolve_publish_difficulty_rating(dir.path(), "## Plan\n");
        assert!(none.is_none() && invalid);
    }

    #[test]
    fn a_failed_plan_block_write_stops_before_the_response_comment() {
        let dir = TempDir::new().unwrap();
        seed_publish(dir.path());
        let effects = FakeEffects::default();
        let runner = FakeRunner::new().failing("named-block write", 1);
        let mut env = env_with_repo(dir.path());
        let _ = design_clarify_run(&effects, &runner, &args("publish"), &mut env, dir.path());
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-publish-result.env")).unwrap();
        assert!(result.contains("CLARIFY_PUBLISH_STATUS=plan-write-failed\n"));
        assert!(result.contains("SUMMARY_OUTCOME=failed-plan-write\n"));
        assert!(result.contains("PLAN_WRITE_OK=false\n"));
        assert!(dir.path().join("clarify-plan-write.failure.log").is_file());
        let verbs = runner.larch_verbs();
        assert!(!verbs.contains(&("difficulty".to_owned(), "sync-labels".to_owned())));
    }

    #[test]
    fn an_unreadable_request_state_sidecar_refuses_the_publish_phase() {
        let dir = TempDir::new().unwrap();
        seed_publish(dir.path());
        // A symlinked sidecar is refused at the trust boundary rather than
        // followed, so the publish phase has no request state to act on.
        fs::remove_file(dir.path().join(".design-clarify-request.env")).unwrap();
        std::os::unix::fs::symlink(
            dir.path().join("elsewhere.env"),
            dir.path().join(".design-clarify-request.env"),
        )
        .unwrap();
        let effects = FakeEffects::default();
        let runner = FakeRunner::new();
        let mut env = env_with_repo(dir.path());
        let _ = design_clarify_run(&effects, &runner, &args("publish"), &mut env, dir.path());
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-publish-result.env")).unwrap();
        assert!(result.contains("CLARIFY_PUBLISH_STATUS=missing-request-state\n"));
        assert!(runner.larch_calls.borrow().is_empty());
    }

    #[test]
    fn a_request_state_for_another_issue_refuses_the_publish_phase() {
        let dir = TempDir::new().unwrap();
        seed_publish(dir.path());
        fs::write(
            dir.path().join(".design-clarify-request.env"),
            "REQUEST_ID=2\nISSUE_NUMBER=9\nREPO=owner/repo\n",
        )
        .unwrap();
        let effects = FakeEffects::default();
        let runner = FakeRunner::new();
        let mut env = env_with_repo(dir.path());
        let _ = design_clarify_run(&effects, &runner, &args("publish"), &mut env, dir.path());
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-publish-result.env")).unwrap();
        assert!(result.contains("CLARIFY_PUBLISH_STATUS=issue-mismatch\n"));
    }

    #[test]
    fn an_invalid_difficulty_sidecar_refuses_before_the_plan_write() {
        let dir = TempDir::new().unwrap();
        seed_publish(dir.path());
        fs::write(
            dir.path().join("design-difficulty-rating.raw.json"),
            "{ not json",
        )
        .unwrap();
        let effects = FakeEffects::default();
        let runner = FakeRunner::new();
        let mut env = env_with_repo(dir.path());
        let _ = design_clarify_run(&effects, &runner, &args("publish"), &mut env, dir.path());
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-publish-result.env")).unwrap();
        assert!(result.contains("CLARIFY_PUBLISH_STATUS=difficulty-sidecar-invalid\n"));
        assert!(result.contains("SUMMARY_OUTCOME=failed-plan-write\n"));
        assert!(runner.larch_calls.borrow().is_empty());
    }

    #[test]
    fn a_plan_without_difficulty_metadata_refuses_before_the_plan_write() {
        let dir = TempDir::new().unwrap();
        seed_publish(dir.path());
        fs::write(dir.path().join("clarify-plan.md"), "## Plan\n\nDo it.\n").unwrap();
        let effects = FakeEffects::default();
        let runner = FakeRunner::new();
        let mut env = env_with_repo(dir.path());
        let _ = design_clarify_run(&effects, &runner, &args("publish"), &mut env, dir.path());
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-publish-result.env")).unwrap();
        assert!(result.contains("CLARIFY_PUBLISH_STATUS=missing-difficulty\n"));
        assert!(runner.larch_calls.borrow().is_empty());
    }

    #[test]
    fn a_failed_label_removal_reports_its_own_publish_status() {
        let dir = TempDir::new().unwrap();
        seed_publish(dir.path());
        let effects = FakeEffects {
            label_fails: true,
            ..FakeEffects::default()
        };
        // named-block, sync-labels, run-log write, log-publish, upsert-summary
        let runner = FakeRunner::new().queue_larch(&["", "", "", "PUBLISH_OK=true\n", ""]);
        let mut env = env_with_repo(dir.path());
        let _ = design_clarify_run(&effects, &runner, &args("publish"), &mut env, dir.path());
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-publish-result.env")).unwrap();
        assert!(result.contains("CLARIFY_PUBLISH_STATUS=label-remove-failed\n"));
        assert!(result.contains("PLAN_WRITE_OK=true\n"));
        let verbs = runner.larch_verbs();
        assert!(!verbs.contains(&("tracking-issue".to_owned(), "rename".to_owned())));
    }

    #[test]
    fn a_failed_rename_records_a_warning_and_reports_renamed_false() {
        let dir = TempDir::new().unwrap();
        seed_publish(dir.path());
        let effects = FakeEffects::default();
        let runner = FakeRunner::new()
            .queue_larch(&["", "", "", "PUBLISH_OK=true\n", "", ""])
            .failing("tracking-issue rename", 3);
        let mut env = env_with_repo(dir.path());
        let _ = design_clarify_run(&effects, &runner, &args("publish"), &mut env, dir.path());
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-publish-result.env")).unwrap();
        assert!(result.contains("RENAMED=false\n"), "got: {result}");
        assert!(dir.path().join("clarify-rename.stderr").is_file());
        let verbs = runner.larch_verbs();
        assert!(verbs.contains(&("run-log".to_owned(), "append-failure".to_owned())));
    }

    #[test]
    fn a_failed_log_publish_records_a_warning_and_reports_publish_false() {
        let dir = TempDir::new().unwrap();
        seed_publish(dir.path());
        let effects = FakeEffects::default();
        let runner = FakeRunner::new().failing("design log-publish", 2);
        let mut env = env_with_repo(dir.path());
        let _ = design_clarify_run(&effects, &runner, &args("publish"), &mut env, dir.path());
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-publish-result.env")).unwrap();
        assert!(result.contains("PUBLISH_OK=false\n"), "got: {result}");
        assert!(result.contains("CLARIFY_PUBLISH_STATUS=log-publish-failed\n"));
        assert!(dir.path().join("design-log-publish.failure.log").is_file());
        let verbs = runner.larch_verbs();
        assert!(verbs.contains(&("run-log".to_owned(), "append-failure".to_owned())));
        // A failed log publish must not go on to rename the tracking issue.
        assert!(!verbs.contains(&("tracking-issue".to_owned(), "rename".to_owned())));
    }

    #[test]
    fn a_failed_summary_upsert_is_reported_separately_from_the_log_publish() {
        let dir = TempDir::new().unwrap();
        seed_publish(dir.path());
        let effects = FakeEffects::default();
        let runner = FakeRunner::new()
            .queue_larch(&["", "", "", "PUBLISH_OK=true\n"])
            .failing("tracking-issue upsert-summary", 1);
        let mut env = env_with_repo(dir.path());
        let _ = design_clarify_run(&effects, &runner, &args("publish"), &mut env, dir.path());
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-publish-result.env")).unwrap();
        assert!(result.contains("PUBLISH_OK=false\n"), "got: {result}");
        assert!(result.contains("CLARIFY_PUBLISH_STATUS=summary-upsert-failed\n"));
        assert!(
            dir.path()
                .join("summary-upsert.cancelled-clarify.failure.log")
                .is_file()
        );
    }

    #[test]
    fn a_final_summary_upsert_needs_a_readable_summary_and_a_run_identity() {
        let dir = TempDir::new().unwrap();
        let runner = FakeRunner::new();
        // No final-summary.md on disk at all.
        assert!(!upsert_final_summary_from_disk(
            &runner,
            dir.path(),
            "7",
            "RUN1",
            &[]
        ));
        fs::write(dir.path().join("final-summary.md"), "rendered\n").unwrap();
        // A present summary still needs a real issue and run identity.
        assert!(!upsert_final_summary_from_disk(
            &runner,
            dir.path(),
            "0",
            "RUN1",
            &[]
        ));
        assert!(!upsert_final_summary_from_disk(
            &runner,
            dir.path(),
            "7",
            "",
            &[]
        ));
        assert!(upsert_final_summary_from_disk(
            &runner,
            dir.path(),
            "7",
            "RUN1",
            &[]
        ));
    }

    #[test]
    fn an_unwritable_request_body_target_is_a_fetch_failure() {
        let dir = TempDir::new().unwrap();
        // A directory where the request body belongs makes the fetch write fail.
        fs::create_dir(dir.path().join("clarify-request.md")).unwrap();
        let effects = FakeEffects {
            comments: vec![(44, "<!-- larch:clarify-request id=4 -->\nq\n".to_owned())],
            ..FakeEffects::default()
        };
        let runner = FakeRunner::new();
        let mut env = env_with_repo(dir.path());
        let _ = design_clarify_run(&effects, &runner, &args("fetch"), &mut env, dir.path());
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-fetch-result.env")).unwrap();
        assert!(
            result.contains("CLARIFY_FETCH_STATUS=fetch-failed\n"),
            "got: {result}"
        );
    }

    #[test]
    fn a_pause_request_hands_the_phase_off_to_pause_save() {
        let dir = TempDir::new().unwrap();
        seed_publish(dir.path());
        fs::write(dir.path().join(".pause-requested"), "").unwrap();
        let effects = FakeEffects::default();
        let runner = FakeRunner::new();
        let mut env = env_with_repo(dir.path());
        let _ = design_clarify_run(&effects, &runner, &args("publish"), &mut env, dir.path());
        let python = runner.python_calls.borrow();
        let pause = python.first().expect("pause-save runs");
        assert_eq!(pause[0], "design");
        assert_eq!(pause[1], "pause-save");
        assert!(pause.contains(&"--repo".to_owned()));
        assert!(pause.contains(&"owner/repo".to_owned()));
        // The pause hand-off replaces the publish phase entirely.
        assert!(runner.larch_calls.borrow().is_empty());
        assert!(
            !dir.path()
                .join(".design-clarify-publish-result.env")
                .exists()
        );
    }

    #[test]
    fn an_unreadable_route_state_fails_the_fetch_phase_at_its_own_site() {
        let dir = TempDir::new().unwrap();
        fs::write(dir.path().join("target.env"), "REPO=owner/repo\n").unwrap();
        std::os::unix::fs::symlink(
            dir.path().join("target.env"),
            dir.path().join(".design-step0-route-state.env"),
        )
        .unwrap();
        let effects = FakeEffects::default();
        let runner = FakeRunner::new();
        let mut env: Env = BTreeMap::new();
        let _ = env.insert("DESIGN_TMPDIR".to_owned(), dir.path().display().to_string());
        let _ = design_clarify_run(&effects, &runner, &args("fetch"), &mut env, dir.path());
        let result =
            fs::read_to_string(dir.path().join(".design-clarify-fetch-result.env")).unwrap();
        assert!(result.contains("CLARIFY_FETCH_STATUS=route-state-read-failed\n"));
        assert!(dir.path().join("clarify-route-state.failure.log").is_file());
    }

    #[test]
    fn an_invalid_repository_slug_is_a_usage_refusal_in_either_phase() {
        let dir = TempDir::new().unwrap();
        let effects = FakeEffects::default();
        let runner = FakeRunner::new();
        for phase in ["fetch", "publish"] {
            let mut env = env_with_repo(dir.path());
            let _ = env.insert("REPO".to_owned(), "not a slug".to_owned());
            let _ = design_clarify_run(&effects, &runner, &args(phase), &mut env, dir.path());
        }
        // A usage refusal writes no phase result env and runs no sibling verb.
        assert!(runner.larch_calls.borrow().is_empty());
        assert!(!dir.path().join(".design-clarify-fetch-result.env").exists());
        assert!(
            !dir.path()
                .join(".design-clarify-publish-result.env")
                .exists()
        );
    }

    #[test]
    fn a_dispatch_failure_becomes_a_captured_run_carrying_its_detail() {
        let dispatched = CapturedRun::from_output(Ok(ProcessOutput::new(
            larch_core::ProcessStatus::new(false, Some(7)),
            b"OUT=1\n".to_vec(),
            b"warned\n".to_vec(),
            false,
            false,
        )));
        assert_eq!(dispatched.rc, 7);
        assert_eq!(dispatched.stdout, "OUT=1\n");
        assert_eq!(dispatched.stderr, "warned\n");
        // A dispatch that never produced a child keeps its detail on stderr so
        // the failure sidecars the caller writes are diagnosable.
        let failed = CapturedRun::from_output(Err("verified bootstrap missing".to_owned()));
        assert_eq!(failed.rc, 1);
        assert!(failed.stdout.is_empty());
        assert_eq!(failed.stderr, "verified bootstrap missing");
    }

    #[test]
    fn a_result_env_write_reports_a_failed_rename_rather_than_claiming_success() {
        let dir = TempDir::new().unwrap();
        // A directory at the destination cannot be replaced by the temp file.
        let occupied = dir.path().join("occupied.env");
        fs::create_dir(&occupied).unwrap();
        let error = write_result_env(&occupied, &[("REQUEST_ID", "1")], &CLARIFY_RESULT_ENV_ALLOW)
            .expect_err("a directory cannot be replaced by the result env");
        assert!(!error.is_empty());
        // The abandoned temp file is cleaned up rather than left behind.
        let leftovers: Vec<_> = fs::read_dir(dir.path())
            .unwrap()
            .flatten()
            .filter(|entry| entry.file_name().to_string_lossy().ends_with(".tmp"))
            .collect();
        assert!(leftovers.is_empty(), "temp file left behind");
    }

    #[test]
    fn clarify_publish_status_precedence() {
        let dir = TempDir::new().unwrap();
        assert_eq!(clarify_publish_status(dir.path(), "true"), "ok");
        assert_eq!(
            clarify_publish_status(dir.path(), "false"),
            "log-publish-failed"
        );
        fs::write(dir.path().join("summary-upsert.x.failure.log"), "x").unwrap();
        assert_eq!(
            clarify_publish_status(dir.path(), "false"),
            "summary-upsert-failed"
        );
        fs::write(
            dir.path().join("design-log-publish.stdout"),
            "RECOVERY_BRANCH=r\n",
        )
        .unwrap();
        assert_eq!(
            clarify_publish_status(dir.path(), "false"),
            "log-publish-recovery"
        );
    }
}
