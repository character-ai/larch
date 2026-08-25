#[cfg(unix)]
mod tests {
    use std::{
        fs,
        os::unix::fs::{PermissionsExt as _, symlink},
        path::{Path, PathBuf},
        process::{Command, Output},
    };

    use larch_core::shell_quote;
    use tempfile::TempDir;

    struct Fixture {
        sandbox: TempDir,
        root: PathBuf,
        fake_binary: PathBuf,
        session_env: PathBuf,
    }

    fn repo() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../..")
            .canonicalize()
            .expect("repository root")
    }

    fn host_target() -> &'static str {
        match (std::env::consts::OS, std::env::consts::ARCH) {
            ("macos", "aarch64") => "aarch64-apple-darwin",
            ("macos", "x86_64") => "x86_64-apple-darwin",
            ("linux", "aarch64") => "aarch64-unknown-linux-gnu",
            ("linux", "x86_64") => "x86_64-unknown-linux-gnu",
            pair => panic!("unsupported test host: {pair:?}"),
        }
    }

    fn write_executable(path: &Path, body: &str) {
        fs::write(path, body).expect("write executable");
        let mut permissions = fs::metadata(path).expect("metadata").permissions();
        permissions.set_mode(0o755);
        fs::set_permissions(path, permissions).expect("chmod executable");
    }

    fn fake_binary_body() -> String {
        let actual = shell_quote(env!("CARGO_BIN_EXE_larch"));
        format!(
            r#"#!/usr/bin/env bash
set -u
ACTUAL={actual}
if [[ "${{1:-}}" == --version ]]; then
  printf '%s\n' 'larch {version}'
  exit 0
fi
if [[ "${{1:-}}" == bootstrap && "${{2:-}}" == self-check ]]; then
  printf '%s\n' '{{"schema_version":1,"version":"{version}","target":"{target}"}}'
  exit 0
fi
if [[ -n "${{DESIGN_TMPDIR:-}}" ]]; then
  printf '%s\n' "$*" >>"$DESIGN_TMPDIR/child-commands.log"
fi
if [[ "${{1:-}}" == design && "${{2:-}}" == pause-save ]]; then
  shift 2
  printf '%s' 'PAUSE_STUB_ARGS='
  previous=''
  for argument in "$@"; do
    if [[ "$previous" == --issue && -z "$argument" ]]; then exit 7; fi
    printf '<%s>' "$argument"
    previous=$argument
  done
  printf '\n'
  exit 0
fi
if [[ "${{1:-}}" == render && "${{2:-}}" == scope-anchor ]]; then
  exec "$ACTUAL" "$@"
fi
if [[ "${{1:-}}" == plan-review && "${{2:-}}" == persist-retally-env ]]; then
  exec "$ACTUAL" "$@"
fi
if [[ "${{1:-}}" == run-log && "${{2:-}}" == append-failure ]]; then
  shift 2
  log='' category='' output_file=''
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --log) log=$2; shift 2 ;;
      --category) category=$2; shift 2 ;;
      --output-file) output_file=$2; shift 2 ;;
      *) shift ;;
    esac
  done
  {{ printf '### %s\n\n' "$category"; [[ ! -f "$output_file" ]] || command cat "$output_file"; }} >>"$log"
  printf 'APPENDED=true\nLOG=%s\n' "$log"
  exit 0
fi
if [[ "${{1:-}}" == voting && "${{2:-}}" == findings-classification-header ]]; then
  printf 'finding_id\tfinding_reviewers\tvoting_result\n'
  exit 0
fi
if [[ "${{1:-}}" == timing && "${{2:-}}" == record-round ]]; then
  exit 0
fi
if [[ "${{1:-}}" == plan-review && "${{2:-}}" == tally ]]; then
  shift 2
  ballot='' design='' voter='' classification=''
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --ballot-file) ballot=$2; shift 2 ;;
      --design-tmpdir) design=$2; shift 2 ;;
      --voter) voter=${{2#*:}}; shift 2 ;;
      --findings-classification-out) classification=$2; shift 2 ;;
      *) shift ;;
    esac
  done
  if [[ -f "$design/.tally-empty-exit-2" ]]; then exit 2; fi
  : >"$design/accepted-plan-findings.md"
  : >"$design/rejected-findings.md"
  : >"$design/oos.md"
  if command grep -Eq '^FINDING_1:[[:space:]]*YES' "$voter"; then
    command cp "$ballot" "$design/accepted-plan-findings.md"
  fi
  printf 'finding_id\tfinding_reviewers\tvoting_result\n' >"$classification"
  printf '# Plan Review Voting Tally\n' >"$design/voting-tally.md"
  printf 'TALLY_PLAN_REVIEW_STATUS=ok\nVOTING_TALLY_FILE=%s/voting-tally.md\n' "$design"
  if [[ -f "$design/.tally-ok-exit-2" ]]; then exit 2; fi
  exit 0
fi
exit 2
"#,
            version = env!("CARGO_PKG_VERSION"),
            target = host_target(),
        )
    }

    fn session_text(root: &Path, issue: &str, extra: &str) -> String {
        format!(
            "export DESIGN_TMPDIR={}\nexport ISSUE_NUMBER={}\n{extra}",
            shell_quote(&root.display().to_string()),
            shell_quote(issue),
        )
    }

    fn fixture(issue: &str, extra: &str) -> Fixture {
        let sandbox = TempDir::new().expect("sandbox");
        let sandbox_root = sandbox.path().canonicalize().expect("canonical sandbox");
        let root = sandbox_root.join("design");
        fs::create_dir(&root).expect("design root");
        let fake_binary = sandbox_root.join("larch-fixture");
        write_executable(&fake_binary, &fake_binary_body());
        let session_env = root.join("session-env.sh");
        fs::write(&session_env, session_text(&root, issue, extra)).expect("session env");
        Fixture {
            sandbox,
            root,
            fake_binary,
            session_env,
        }
    }

    fn run_with_session(
        fixture: &Fixture,
        phase: &str,
        session_env: &Path,
        home: Option<&Path>,
    ) -> Output {
        let mut command = Command::new(env!("CARGO_BIN_EXE_larch"));
        command
            .args(["plan-review", "step3-mav", "--session-env-path"])
            .arg(session_env)
            .args([
                "--claude-pid",
                "4242",
                "--plugin-root",
                repo().to_str().expect("UTF-8 repo"),
                "--phase",
                phase,
            ])
            .env_remove("CLAUDE_PLUGIN_ROOT")
            .env("LARCH_BINARY", &fixture.fake_binary)
            .env("LARCH_QUIET_DISABLE", "1")
            .env_remove("DESIGN_TMPDIR")
            .env_remove("ISSUE_NUMBER");
        if let Some(home) = home {
            command.env("HOME", home);
        }
        command
            .output()
            .expect("run step3 mav")
    }

    fn run(fixture: &Fixture, phase: &str) -> Output {
        run_with_session(fixture, phase, &fixture.session_env, None)
    }

    fn stdout(output: &Output) -> String {
        String::from_utf8_lossy(&output.stdout).into_owned()
    }

    fn stderr(output: &Output) -> String {
        String::from_utf8_lossy(&output.stderr).into_owned()
    }

    fn text(path: impl AsRef<Path>) -> String {
        fs::read_to_string(path).expect("read text")
    }

    fn write_ballot(root: &Path) {
        fs::write(
            root.join("ballot.txt"),
            "### FINDING_1: Fix parser\n- **Reviewer**: Cursor-Arch\n- focus-area = correctness\n- Concern: parser misses bad input.\n",
        )
        .expect("ballot");
    }

    fn write_result_envs(root: &Path, loop_status: &str, round: &str) {
        fs::write(
            root.join(".step3-plan-review-result.env"),
            format!(
                "LOOP_STATUS=main-agent-vote-required\nTALLY_PLAN_REVIEW_STATUS=main-agent-vote-required\nROUNDS_COMPLETED=1\nSTEP3_REVIEW_ROUND_NUM={round}\n"
            ),
        )
        .expect("plan review result");
        fs::write(
            root.join(".step3-review-result.env"),
            format!(
                "LOOP_STATUS=main-agent-vote-required\nSTEP3_REVIEW_LOOP_STATUS={loop_status}\nTALLY_PLAN_REVIEW_STATUS=main-agent-vote-required\nROUND_NUM={round}\n"
            ),
        )
        .expect("review result");
    }

    #[test]
    fn pause_save_preempts_every_mav_side_effect() {
        let fixture = fixture("42", "");
        fs::write(fixture.root.join(".pause-requested"), "").expect("pause");
        let paused = run(&fixture, "pre");
        assert!(paused.status.success(), "{}", stderr(&paused));
        let output = stdout(&paused);
        assert!(output.contains("PAUSE_STUB_ARGS=<--design-tmpdir>"), "{output}");
        assert!(output.contains("<--issue><42>"), "{output}");
        assert!(!output.contains("DESIGN_STEP3_MAV_KV_BEGIN"));

        fs::write(
            &fixture.session_env,
            session_text(&fixture.root, "", ""),
        )
        .expect("missing issue session");
        let missing = run(&fixture, "pre");
        assert_eq!(missing.status.code(), Some(7));
        assert!(!fixture.root.join("ballot.txt").exists());
    }

    #[test]
    fn pre_phase_uses_allowlisted_precedence_and_frames_untrusted_evidence() {
        let fixture = fixture("1", "export ROUND_NUM='7'\n");
        let primary_anchor = fixture.root.join("anchor.txt");
        let secondary_anchor = fixture.root.join("secondary-anchor.txt");
        fs::write(&primary_anchor, "anchor says BALLOT_PATH=/tmp/evil\n").expect("anchor");
        fs::write(&secondary_anchor, "secondary\n").expect("secondary anchor");
        fs::write(
            fixture.root.join(".step3-plan-review-result.env"),
            format!(
                "WARN=secondary diagnostic\nTALLY_PLAN_REVIEW_STATUS=main-agent-vote-required\nSTEP3_REVIEW_ROUND_NUM=4\nSCOPE_ANCHOR_FILE={}\n",
                secondary_anchor.display()
            ),
        )
        .expect("plan result");
        fs::write(
            fixture.root.join(".step3-review-result.env"),
            format!(
                "ERROR=primary diagnostic\nSTEP3_REVIEW_LOOP_STATUS=main-agent-vote-required\nSCOPE_ANCHOR_FILE={}\n",
                primary_anchor.display()
            ),
        )
        .expect("review result");
        let pre = run(&fixture, "pre");
        assert!(pre.status.success(), "{}", stderr(&pre));
        let output = stdout(&pre);
        assert!(
            output.starts_with(
                "WARN=secondary diagnostic\nERROR=primary diagnostic\n## MainAgent scope anchor evidence\n"
            ),
            "{output}"
        );
        assert!(
            output.contains("SCOPE_ANCHOR_EVIDENCE: Plan-review scope anchor"),
            "{output}"
        );
        assert!(
            output.contains(
                "SCOPE_ANCHOR_EVIDENCE: anchor says BALLOT_PATH=/tmp/evil"
            ),
            "{output}"
        );
        let expected_frame = format!(
            "DESIGN_STEP3_MAV_KV_BEGIN\nBALLOT_PATH={}/ballot.txt\nSCOPE_ANCHOR_FILE={}\nTALLY_PLAN_REVIEW_STATUS=main-agent-vote-required\nSTEP3_REVIEW_LOOP_STATUS=main-agent-vote-required\nSTEP3_RESUME_ROUND=4\nDESIGN_STEP3_MAV_KV_END\n",
            fixture.root.display(),
            primary_anchor.display()
        );
        assert!(output.ends_with(&expected_frame), "{output}");
        assert!(!output.contains("BALLOT_PATH=/tmp/evil\nSCOPE_ANCHOR_FILE="));
    }

    #[test]
    fn pre_phase_uses_session_fallback_and_rejects_result_links() {
        let fallback = fixture("1", "export ROUND_NUM='7'\n");
        let output = run(&fallback, "pre");
        assert!(output.status.success(), "{}", stderr(&output));
        assert!(stdout(&output).contains("STEP3_RESUME_ROUND=7\n"));

        let pointer = fixture("1", "export ROUND_NUM='8'\n");
        let home = pointer
            .root
            .parent()
            .expect("canonical sandbox root")
            .join("home");
        let sessions = home.join(".cache/larch/sessions");
        fs::create_dir_all(&sessions).expect("session pointer parent");
        let current = sessions.join("current-design-env-4242.sh");
        symlink(&pointer.session_env, &current).expect("session pointer");
        let pointer_output = run_with_session(&pointer, "pre", &current, Some(&home));
        assert!(
            pointer_output.status.success(),
            "{}",
            stderr(&pointer_output)
        );
        assert!(
            stdout(&pointer_output).contains("STEP3_RESUME_ROUND=8\n"),
            "{}",
            stdout(&pointer_output)
        );

        let linked = fixture("1", "");
        let target = linked.root.join("target.env");
        fs::write(&target, "ROUND_NUM=1\n").expect("target");
        symlink(&target, linked.root.join(".step3-review-result.env")).expect("result symlink");
        let refused = run(&linked, "pre");
        assert_eq!(refused.status.code(), Some(1));
        assert_eq!(
            stderr(&refused),
            "**⚠ Step 3 MAV: could not read Step 3 result env**\n"
        );

        let outside = fixture("1", "");
        let outside_anchor = outside.sandbox.path().join("outside-anchor.txt");
        fs::write(&outside_anchor, "outside\n").expect("outside anchor");
        fs::write(
            outside.root.join(".step3-review-result.env"),
            format!("SCOPE_ANCHOR_FILE={}\n", outside_anchor.display()),
        )
        .expect("outside result");
        let render_failure = run(&outside, "pre");
        assert!(!render_failure.status.success());
        assert!(
            stdout(&render_failure).starts_with("## MainAgent scope anchor evidence\n")
        );
        assert!(!stderr(&render_failure).contains('\0'));
    }

    #[test]
    fn post_phase_routes_accepted_and_empty_rounds_and_warns_once() {
        let accepted = fixture("1", "");
        fs::create_dir_all(accepted.root.join("plan-review/round-2")).expect("round");
        write_result_envs(&accepted.root, "main-agent-vote-required", "2");
        write_ballot(&accepted.root);
        fs::write(accepted.root.join("voter-main-agent.txt"), "FINDING_1: YES\n")
            .expect("vote");
        fs::write(
            accepted.root.join("plan-review/round-2/round-start-s"),
            "1\n",
        )
        .expect("round start");
        let post = run(&accepted, "post");
        assert!(post.status.success(), "{}", stderr(&post));
        let output = stdout(&post);
        assert_eq!(
            output,
            format!(
                "PERSIST_RETALLY_STATUS=ok\nDESIGN_STEP3_MAV_KV_BEGIN\nTALLY_PLAN_REVIEW_STATUS=ok\nLOOP_STATUS=complete\nACCEPTED_COUNT=1\nPHASE=awaiting-apply\nSTEP3_RESUME_ROUND=2\nSTEP3_REVIEW_LOOP_STATUS=main-agent-vote-required\nDESIGN_STEP3_MAV_KV_END\nTALLY_PLAN_REVIEW_STATUS=ok\nVOTING_TALLY_FILE={}/voting-tally.md\n",
                accepted.root.display()
            )
        );
        assert_eq!(
            text(accepted.root.join(".step3-round-2.phase")),
            "awaiting-apply\n"
        );
        assert!(
            text(accepted.root.join("execution-issues.md"))
                .contains("0-judge plan-review panel")
        );
        assert!(
            text(accepted.root.join("child-commands.log")).contains("timing record-round")
        );
        let warning_before = text(accepted.root.join("execution-issues.md"));
        let again = run(&accepted, "post");
        assert!(again.status.success(), "{}", stderr(&again));
        assert_eq!(
            text(accepted.root.join("execution-issues.md")),
            warning_before
        );

        let empty = fixture("1", "");
        write_result_envs(&empty.root, "main-agent-vote-required", "3");
        write_ballot(&empty.root);
        fs::write(empty.root.join("voter-main-agent.txt"), "FINDING_1: NO\n")
            .expect("vote");
        let zero = run(&empty, "post");
        assert!(zero.status.success(), "{}", stderr(&zero));
        assert!(stdout(&zero).contains("ACCEPTED_COUNT=0\n"));
        assert!(stdout(&zero).contains("PHASE=awaiting-continuation\n"));
        assert_eq!(
            text(empty.root.join(".step3-round-3.phase")),
            "awaiting-continuation\n"
        );
    }

    #[test]
    fn missing_voter_persists_tally_error_and_clears_partial_artifacts() {
        let fixture = fixture("1", "");
        let anchor = fixture.root.join("stale-scope-anchor.txt");
        fs::write(&anchor, "stale anchor\n").expect("anchor");
        fs::write(
            fixture.root.join(".step3-plan-review-result.env"),
            format!(
                "LOOP_STATUS=main-agent-vote-required\nTALLY_PLAN_REVIEW_STATUS=main-agent-vote-required\nSCOPE_ANCHOR_FILE={}\nACCEPTED_COUNT=3\nIMPORTANT_ACCEPTED_COUNT=2\n",
                anchor.display()
            ),
        )
        .expect("plan result");
        fs::write(
            fixture.root.join(".step3-review-result.env"),
            format!(
                "LOOP_STATUS=main-agent-vote-required\nSTEP3_REVIEW_LOOP_STATUS=main-agent-vote-required\nTALLY_PLAN_REVIEW_STATUS=main-agent-vote-required\nROUND_NUM=4\nSCOPE_ANCHOR_FILE={}\nIMPORTANT_ACCEPTED_COUNT=2\n",
                anchor.display()
            ),
        )
        .expect("review result");
        fs::write(
            fixture.root.join("accepted-plan-findings.md"),
            "### FINDING_99: Partial failed re-tally accepted\n- **Concern**: clear me\n",
        )
        .expect("partial accepted");
        write_ballot(&fixture.root);
        let post = run(&fixture, "post");
        assert!(post.status.success(), "{}", stderr(&post));
        let output = stdout(&post);
        assert!(output.contains("NEXT_ACTION=step3b-bypass\n"), "{output}");
        assert!(output.contains("TALLY_PLAN_REVIEW_STATUS=tally-error\n"));
        assert!(output.contains("PHASE=unchanged\n"));
        assert!(!fixture.root.join(".step3-round-4.phase").exists());
        for result in [
            ".step3-plan-review-result.env",
            ".step3-review-result.env",
        ] {
            let body = text(fixture.root.join(result));
            assert!(body.contains("TALLY_PLAN_REVIEW_STATUS=tally-error\n"));
            assert!(body.contains("NEXT_ACTION=step3b-bypass\n"));
            assert!(!body.contains("SCOPE_ANCHOR_FILE="));
        }
        assert_eq!(text(fixture.root.join("accepted-plan-findings.md")), "");
        assert_eq!(
            text(
                fixture
                    .root
                    .join("plan-review/round-4/findings-classification.tsv")
            ),
            "finding_id\tfinding_reviewers\tvoting_result\n"
        );
        assert!(
            text(fixture.root.join("voting-tally.md"))
                .contains("MainAgent voter file unreadable")
        );

        let confined = self::fixture("1", "");
        let round = confined.root.join("plan-review/round-1");
        fs::create_dir_all(&round).expect("round directory");
        let outside = confined.root.parent().expect("sandbox root").join("outside.tsv");
        fs::write(&outside, "outside remains unchanged\n").expect("outside sentinel");
        symlink(&outside, round.join("findings-classification.tsv"))
            .expect("classification symlink");
        let refused = run(&confined, "post");
        assert_eq!(refused.status.code(), Some(1));
        assert_eq!(text(&outside), "outside remains unchanged\n");
    }

    #[test]
    fn artifact_and_resume_rounds_use_distinct_precedence_orders() {
        let precedence = fixture("1", "");
        fs::write(
            precedence.root.join(".step3-review-result.env"),
            "LOOP_STATUS=main-agent-vote-required\nSTEP3_REVIEW_LOOP_STATUS=main-agent-vote-required\nTALLY_PLAN_REVIEW_STATUS=main-agent-vote-required\nFINAL_ROUND_NUM=10\nROUND_NUM=8\nROUNDS_COMPLETED=9\n",
        )
        .expect("round state");
        write_ballot(&precedence.root);
        fs::write(
            precedence.root.join("voter-main-agent.txt"),
            "FINDING_1: YES\n",
        )
            .expect("vote");
        let post = run(&precedence, "post");
        assert!(post.status.success(), "{}", stderr(&post));
        assert!(
            precedence
                .root
                .join("plan-review/round-8/findings-classification.tsv")
                .is_file()
        );
        assert!(!precedence.root.join("plan-review/round-9").exists());
        assert_eq!(
            text(precedence.root.join(".step3-round-10.phase")),
            "awaiting-apply\n"
        );

        let single = fixture("1", "");
        fs::write(
            single.root.join(".step3-review-result.env"),
            "LOOP_STATUS=main-agent-vote-required\nTALLY_PLAN_REVIEW_STATUS=main-agent-vote-required\nROUND_NUM=6\n",
        )
        .expect("single state");
        write_ballot(&single.root);
        fs::write(single.root.join("voter-main-agent.txt"), "not a valid vote\n")
            .expect("malformed vote");
        let before = text(single.root.join("voter-main-agent.txt"));
        let post = run(&single, "post");
        assert!(post.status.success(), "{}", stderr(&post));
        assert!(stdout(&post).contains("PHASE=unchanged\n"));
        assert_eq!(text(single.root.join("voter-main-agent.txt")), before);
        assert!(
            fs::read_dir(&single.root)
                .expect("root listing")
                .all(|entry| !entry
                    .expect("entry")
                    .file_name()
                    .to_string_lossy()
                    .starts_with(".step3-round-"))
        );
    }

    #[test]
    fn invalid_resume_round_and_tally_exit_codes_remain_distinct() {
        let invalid = fixture("1", "");
        fs::write(
            invalid.root.join(".step3-review-result.env"),
            "LOOP_STATUS=main-agent-vote-required\nSTEP3_REVIEW_LOOP_STATUS=main-agent-vote-required\nTALLY_PLAN_REVIEW_STATUS=main-agent-vote-required\n",
        )
        .expect("invalid state");
        write_ballot(&invalid.root);
        fs::write(invalid.root.join("voter-main-agent.txt"), "FINDING_1: YES\n")
            .expect("vote");
        let refused = run(&invalid, "post");
        assert_eq!(refused.status.code(), Some(1));
        assert_eq!(
            stderr(&refused),
            "**⚠ Step 3 MAV: STEP3_RESUME_ROUND missing or invalid**\n"
        );

        let status_ok = fixture("1", "");
        write_result_envs(&status_ok.root, "main-agent-vote-required", "2");
        write_ballot(&status_ok.root);
        fs::write(
            status_ok.root.join("voter-main-agent.txt"),
            "FINDING_1: YES\n",
        )
        .expect("vote");
        fs::write(status_ok.root.join(".tally-ok-exit-2"), "").expect("exit sentinel");
        let exit_two = run(&status_ok, "post");
        assert_eq!(exit_two.status.code(), Some(2));
        assert!(stdout(&exit_two).contains("TALLY_PLAN_REVIEW_STATUS=ok\n"));

        let status_error = fixture("1", "");
        write_result_envs(&status_error.root, "main-agent-vote-required", "2");
        write_ballot(&status_error.root);
        fs::write(
            status_error.root.join("voter-main-agent.txt"),
            "FINDING_1: YES\n",
        )
        .expect("vote");
        fs::write(status_error.root.join(".tally-empty-exit-2"), "")
            .expect("error sentinel");
        let handled = run(&status_error, "post");
        assert!(handled.status.success(), "{}", stderr(&handled));
        assert!(stdout(&handled).contains("NEXT_ACTION=step3b-bypass\n"));
    }

    #[test]
    fn command_usage_and_direct_caller_contract_are_frozen() {
        let help = Command::new(env!("CARGO_BIN_EXE_larch"))
            .args(["plan-review", "step3-mav", "--help"])
            .output()
            .expect("help");
        assert!(help.status.success());
        assert_eq!(
            stderr(&help),
            "usage: design-step3-mav.sh --phase pre|post --session-env-path PATH --claude-pid PID --plugin-root PATH\n"
        );
        let unknown = Command::new(env!("CARGO_BIN_EXE_larch"))
            .args(["plan-review", "step3-mav", "--unknown"])
            .output()
            .expect("unknown");
        assert_eq!(unknown.status.code(), Some(2));
        assert!(stderr(&unknown).starts_with("design-step3-mav.sh: unknown argument: --unknown\n"));

        let invalid_root = fixture("1", "");
        let refused = Command::new(env!("CARGO_BIN_EXE_larch"))
            .args(["plan-review", "step3-mav", "--session-env-path"])
            .arg(&invalid_root.session_env)
            .args(["--claude-pid", "4242", "--plugin-root"])
            .arg(&invalid_root.root)
            .args(["--phase", "pre"])
            .env_remove("CLAUDE_PLUGIN_ROOT")
            .output()
            .expect("invalid explicit plugin root");
        assert_eq!(refused.status.code(), Some(1));
        assert_eq!(
            stderr(&refused),
            "CLAUDE_PLUGIN_ROOT does not contain a safe scripts/larch.sh\n"
        );

        let skill = text(repo().join("skills/design/SKILL.md"));
        let expected = "\"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh\" plan-review step3-mav --session-env-path \"$HOME/.cache/larch/sessions/current-design-env-$PPID.sh\" --claude-pid \"$PPID\" --phase pre";
        assert!(skill.contains(expected), "direct pre caller missing");
        assert!(
            skill.contains(&expected.replace("--phase pre", "--phase post")),
            "direct post caller missing"
        );
        assert!(!skill.contains("design-step3-mav.sh"));
    }
}
