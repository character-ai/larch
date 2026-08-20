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
    }

    impl FakeRunner {
        fn new() -> Self {
            Self {
                larch_calls: RefCell::new(Vec::new()),
                python_calls: RefCell::new(Vec::new()),
                larch_stdout: RefCell::new(Vec::new()),
                python_stdout: RefCell::new(Vec::new()),
            }
        }

        fn queue_larch(self, stdout: &[&str]) -> Self {
            *self.larch_stdout.borrow_mut() = stdout.iter().map(|s| (*s).to_owned()).collect();
            self
        }

        fn queue_python(self, stdout: &[&str]) -> Self {
            *self.python_stdout.borrow_mut() = stdout.iter().map(|s| (*s).to_owned()).collect();
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
            self.larch_calls.borrow_mut().push(call);
            let stdout = if self.larch_stdout.borrow().is_empty() {
                String::new()
            } else {
                self.larch_stdout.borrow_mut().remove(0)
            };
            CapturedRun {
                rc: 0,
                stdout,
                stderr: String::new(),
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
        let runner = FakeRunner::new()
            .queue_larch(&["", "", "", "RENAMED=true\n"])
            .queue_python(&["PUBLISH_OK=true\n"]);
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
        let runner = FakeRunner::new().queue_python(&["PUBLISH_OK=true\n"]);
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
        assert!(write_result_env(&link, &[("REQUEST_ID", "1")]).is_err());
        assert!(write_result_env(&target, &[("REQUEST_ID", "bad\nvalue")]).is_err());
        assert!(write_result_env(&target, &[("UNEXPECTED", "1")]).is_err());
        write_result_env(&target, &[("REQUEST_ID", "1"), ("PLAN_FILE", "2")]).unwrap();
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
        assert!(publish_artifact_ok(present.to_str().unwrap()));
        assert!(!publish_artifact_ok(
            dir.path().join("absent").to_str().unwrap()
        ));
        let empty = dir.path().join("empty.md");
        fs::write(&empty, "").unwrap();
        assert!(!publish_artifact_ok(empty.to_str().unwrap()));
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
