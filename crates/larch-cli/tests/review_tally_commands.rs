use std::{
    fs,
    path::{Path, PathBuf},
    process::{Command, Output},
};

use sha2::{Digest as _, Sha256};
use tempfile::TempDir;

fn run(arguments: &[&str], sandbox: &Path) -> Output {
    run_with_environment(arguments, sandbox, &[])
}

fn run_with_environment(
    arguments: &[&str],
    sandbox: &Path,
    environment: &[(&str, &str)],
) -> Output {
    let mut command = Command::new(env!("CARGO_BIN_EXE_larch"));
    command
        .arg("review")
        .args(arguments)
        .current_dir(sandbox)
        .env_remove("LARCH_QUIET_ACTIVE")
        .env_remove("LARCH_QUIET_PID")
        .env_remove("LARCH_QUIET_DISABLE")
        .env_remove("LARCH_EXECUTION_ISSUES_LOG")
        .env_remove("SESSION_ENV_PATH")
        .env_remove("IMPLEMENT_TMPDIR");
    for (key, value) in environment {
        command.env(key, value);
    }
    command.output().expect("run Rust review tally command")
}

fn repository_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(Path::parent)
        .map(Path::to_path_buf)
        .expect("repository root from manifest directory")
}

fn ballot(reviewer: &str, heading: &str) -> String {
    format!(
        "### {heading}\n\n- **Reviewer(s)**: {reviewer}\n- **Location**: src/lib.rs:12\n- **Concern**: concrete concern\n"
    )
}

fn vote(item: &str, value: &str, severity: &str) -> String {
    format!("{item}: {value} CORRECTNESS=true SEVERITY={severity} QUALITY=good UNCERTAIN=false\n")
}

fn tally_arguments<'a>(ballot: &'a Path, review: &'a Path, voters: &'a [&'a Path]) -> Vec<String> {
    let mut arguments = vec![
        "tally-code-votes".to_owned(),
        "--ballot-file".to_owned(),
        ballot.display().to_string(),
        "--review-tmpdir".to_owned(),
        review.display().to_string(),
        "--round-num".to_owned(),
        "1".to_owned(),
        "--voter-files".to_owned(),
    ];
    arguments.extend(voters.iter().map(|path| path.display().to_string()));
    arguments.extend([
        "--voter-tools".to_owned(),
        "validity".to_owned(),
        "fidelity".to_owned(),
        "pragmatism".to_owned(),
    ]);
    arguments
}

#[test]
fn tally_preserves_three_slot_mixed_outcomes_and_ledger_wire() {
    let sandbox = TempDir::new().expect("create sandbox");
    let review = sandbox.path().join("review");
    fs::create_dir_all(&review).expect("create review directory");
    let ballot_path = sandbox.path().join("ballot.md");
    fs::write(&ballot_path, ballot("alice", "FINDING_1: a finding")).expect("write ballot");
    let voters = [
        sandbox.path().join("v1.txt"),
        sandbox.path().join("v2.txt"),
        sandbox.path().join("v3.txt"),
    ];
    fs::write(&voters[0], vote("FINDING_1", "YES", "minor")).expect("write voter one");
    fs::write(&voters[1], vote("FINDING_1", "NO", "minor")).expect("write voter two");
    fs::write(&voters[2], vote("FINDING_1", "YES", "major")).expect("write voter three");
    let arguments = tally_arguments(&ballot_path, &review, &[&voters[0], &voters[1], &voters[2]]);
    let borrowed = arguments.iter().map(String::as_str).collect::<Vec<_>>();
    let output = run(&borrowed, sandbox.path());
    assert!(
        output.status.success(),
        "stdout: {}\nstderr: {}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8(output.stdout).expect("stdout UTF-8");
    assert!(stdout.contains("TALLY_STATUS=ok\n"));
    assert!(stdout.contains("ACCEPTED_COUNT=1\n"));
    assert!(stdout.contains("VOTER_COUNT=3\n"));
    assert!(stdout.contains("UNDER_QUORUM_COUNT=0\n"));
    let classification = fs::read_to_string(review.join("findings-classification-round-1.tsv"))
        .expect("read classification");
    assert_eq!(classification.lines().count(), 2);
    assert!(classification.contains("FINDING_1\talice\taccepted\tYES"));
    assert!(classification.contains("\tvalidity\tNO"));
    assert!(classification.ends_with("\tin_scope\n"));
    assert_eq!(
        fs::read_to_string(review.join("review-tally.env")).expect("read tally env"),
        "FINDING_1_ACCEPTED=true\nFINDING_1_OUTCOME=accepted\nACCEPTED_COUNT=1\nREJECTED_COUNT=0\nEXONERATED_COUNT=0\nNEUTRAL_COUNT=0\nOOS_ACCEPTED_COUNT=0\nOOS_REJECTED_COUNT=0\n",
    );
    let ledger = fs::read_to_string(review.join("findings-ledger.tsv")).expect("read ledger");
    assert!(ledger.starts_with(
        "round\tfinding_id\ttitle\tfile_line\toutcome\tvote_tally\treason\n1\tFINDING_1\ta finding"
    ));
    assert!(ledger.contains("\taccepted\tYES=2/3\tconcrete concern\n"));
}

#[test]
fn commands_report_the_complete_argparse_required_option_set() {
    let sandbox = TempDir::new().expect("create sandbox");
    for (arguments, required) in [
        (vec!["tally-code-votes"], "--ballot-file, --review-tmpdir"),
        (
            vec!["emit-tally"],
            "--tally-file, --accepted-findings-file, --oos-file, --review-tmpdir, --mode",
        ),
        (
            vec!["log-phase"],
            "--run-id, --batch, --action, --payload-file",
        ),
    ] {
        let output = run(&arguments, sandbox.path());
        assert_eq!(output.status.code(), Some(2));
        assert!(
            String::from_utf8(output.stderr)
                .expect("stderr UTF-8")
                .contains(required),
            "missing required-set diagnostic for {}",
            arguments[0]
        );
    }
}

#[test]
fn tally_all_rejects_writes_the_legacy_rejected_record() {
    let sandbox = TempDir::new().expect("create sandbox");
    let review = sandbox.path().join("review");
    fs::create_dir_all(&review).expect("create review directory");
    let ballot_path = sandbox.path().join("ballot.md");
    fs::write(&ballot_path, ballot("alice", "FINDING_1: rejected finding")).expect("write ballot");
    let voters = [
        sandbox.path().join("v1.txt"),
        sandbox.path().join("v2.txt"),
        sandbox.path().join("v3.txt"),
    ];
    for voter in &voters {
        fs::write(voter, vote("FINDING_1", "NO", "minor")).expect("write rejection vote");
    }
    let arguments = tally_arguments(&ballot_path, &review, &[&voters[0], &voters[1], &voters[2]]);
    let borrowed = arguments.iter().map(String::as_str).collect::<Vec<_>>();
    let output = run(&borrowed, sandbox.path());
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        String::from_utf8(output.stdout)
            .expect("stdout UTF-8")
            .contains("REJECTED_COUNT=1\n")
    );
    let tally = fs::read_to_string(review.join("review-tally.env")).expect("read tally env");
    assert!(tally.contains("FINDING_1_OUTCOME=rejected\n"));
    assert!(tally.contains("FINDING_1_REJECTED_SUBTYPE=true_rejected\n"));
    assert!(
        fs::read_to_string(review.join("rejected-findings.md"))
            .expect("read rejected artifact")
            .contains("Vote tally: YES=0 NO=3 JUDGE_ERROR=0")
    );
}

#[test]
fn tally_zero_effective_panel_keeps_slot_columns_and_requires_main_agent() {
    let sandbox = TempDir::new().expect("create sandbox");
    let review = sandbox.path().join("review");
    fs::create_dir_all(&review).expect("create review directory");
    let ballot_path = sandbox.path().join("ballot.md");
    fs::write(&ballot_path, ballot("alice", "FINDING_1: a finding")).expect("write ballot");
    let voters = [
        sandbox.path().join("v1.txt"),
        sandbox.path().join("v2.txt"),
        sandbox.path().join("v3.txt"),
    ];
    for voter in &voters {
        fs::write(voter, "narrative only\n").expect("write narrative voter");
    }
    let arguments = tally_arguments(&ballot_path, &review, &[&voters[0], &voters[1], &voters[2]]);
    let borrowed = arguments.iter().map(String::as_str).collect::<Vec<_>>();
    let output = run(&borrowed, sandbox.path());
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8(output.stdout).expect("stdout UTF-8");
    assert!(stdout.contains("TALLY_STATUS=main-agent-vote-required\n"));
    assert!(stdout.contains("ELIGIBLE_VOTER_COUNT=3\n"));
    assert!(stdout.contains("PARSE_FAILED_COUNT=3\n"));
    assert!(
        stdout
            .contains("VOTING_SKIPPED_WARNING=**⚠ Degraded code-review panel: 0 judges available.")
    );
    let classification = fs::read_to_string(review.join("findings-classification-round-1.tsv"))
        .expect("read classification");
    let row = classification
        .lines()
        .nth(1)
        .expect("one classification row");
    assert_eq!(row.split('\t').count(), 22);
    assert!(row.ends_with("\tin_scope"));
    assert_eq!(
        fs::read_to_string(review.join("review-tally.env")).expect("read tally env"),
        ""
    );
}

#[test]
fn tally_holds_security_oos_artifacts_out_of_public_files() {
    let sandbox = TempDir::new().expect("create sandbox");
    let parent = sandbox.path().join("implement");
    let review = parent.join("round-1");
    fs::create_dir_all(&review).expect("create review directory");
    let session_env = parent.join("session-env.sh");
    fs::write(&session_env, "RUN_ID=run-1\n").expect("write session env");
    let ballot_path = sandbox.path().join("ballot.md");
    fs::write(
        &ballot_path,
        ballot("alice", "FINDING_1: [OOS] [security] credential exposure"),
    )
    .expect("write ballot");
    let voter = sandbox.path().join("v1.txt");
    fs::write(&voter, vote("FINDING_1", "YES", "major")).expect("write voter");
    let arguments = [
        "tally-code-votes",
        "--ballot-file",
        ballot_path.to_str().expect("ballot path"),
        "--review-tmpdir",
        review.to_str().expect("review path"),
        "--session-env-path",
        session_env.to_str().expect("session env path"),
        "--voter-files",
        voter.to_str().expect("voter path"),
    ];
    let output = run(&arguments, sandbox.path());
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        fs::read_to_string(parent.join("security-oos-observations.md"))
            .expect("read private security artifact")
            .contains("credential exposure")
    );
    assert_eq!(
        fs::read_to_string(review.join("oos.md")).expect("read public OOS artifact"),
        ""
    );
    assert_eq!(
        fs::read_to_string(parent.join("oos-accepted-review.md"))
            .expect("read public accepted OOS artifact"),
        ""
    );
}

#[test]
fn tally_restores_neutralized_reviewer_from_a_valid_proposer_map() {
    let sandbox = TempDir::new().expect("create sandbox");
    let review = sandbox.path().join("review");
    fs::create_dir_all(&review).expect("create review directory");
    let ballot_path = sandbox.path().join("ballot.md");
    let ballot_text = "### FINDING_1: neutralized finding\n\n- **Reviewer**: anonymous\n- **Concern**: concrete concern\n";
    fs::write(&ballot_path, ballot_text).expect("write neutralized ballot");
    let proposer_map = review.join("proposer-map.tsv");
    fs::write(
        &proposer_map,
        format!(
            "# neutral_ballot_sha256={:x}\nitem_id\treviewer\treviewer_line\nFINDING_1\talice-output.txt\t- **Reviewer**: alice-output.txt\n",
            Sha256::digest(ballot_text.as_bytes())
        ),
    )
    .expect("write proposer map");
    let voter = sandbox.path().join("voter.txt");
    fs::write(&voter, vote("FINDING_1", "YES", "minor")).expect("write voter");
    let arguments = [
        "tally-code-votes",
        "--ballot-file",
        ballot_path.to_str().expect("ballot path"),
        "--review-tmpdir",
        review.to_str().expect("review path"),
        "--voter-files",
        voter.to_str().expect("voter path"),
    ];
    let output = run(&arguments, sandbox.path());
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let accepted =
        fs::read_to_string(review.join("accepted-findings.md")).expect("read accepted artifact");
    assert!(accepted.contains("**Reviewer**: alice-output.txt"));
    assert!(!accepted.contains("**Reviewer**: anonymous"));
    let classification = fs::read_to_string(review.join("findings-classification-round-1.tsv"))
        .expect("read classification");
    assert!(classification.contains("FINDING_1\talice-output.txt\taccepted"));
}

#[test]
fn tally_keeps_a_failed_three_slot_empty_without_shifting_other_slots() {
    let sandbox = TempDir::new().expect("create sandbox");
    let review = sandbox.path().join("review");
    fs::create_dir_all(&review).expect("create review directory");
    let ballot_path = sandbox.path().join("ballot.md");
    fs::write(&ballot_path, ballot("alice", "FINDING_1: a finding")).expect("write ballot");
    let voters = [
        sandbox.path().join("v1.txt"),
        sandbox.path().join("v2.txt"),
        sandbox.path().join("v3.txt"),
    ];
    fs::write(&voters[0], vote("FINDING_1", "YES", "minor")).expect("write voter one");
    fs::write(&voters[1], "narrative only\n").expect("write narrative voter");
    fs::write(&voters[2], vote("FINDING_1", "YES", "major")).expect("write voter three");
    let arguments = tally_arguments(&ballot_path, &review, &[&voters[0], &voters[1], &voters[2]]);
    let borrowed = arguments.iter().map(String::as_str).collect::<Vec<_>>();
    let output = run(&borrowed, sandbox.path());
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8(output.stdout).expect("stdout UTF-8");
    assert!(stdout.contains("VOTER_COUNT=2\n"));
    assert!(stdout.contains("PARSE_FAILED_COUNT=1\n"));
    let row = fs::read_to_string(review.join("findings-classification-round-1.tsv"))
        .expect("read classification")
        .lines()
        .nth(1)
        .expect("classification row")
        .split('\t')
        .map(str::to_owned)
        .collect::<Vec<_>>();
    assert_eq!(row.len(), 22);
    assert_eq!(row[3], "YES");
    assert_eq!(row[8], "validity");
    assert_eq!(row[9], "");
    assert_eq!(row[14], "fidelity");
    assert_eq!(row[15], "YES");
    assert_eq!(row[20], "pragmatism");
}

#[test]
fn tally_reroutes_high_severity_neutral_findings_to_oos() {
    let sandbox = TempDir::new().expect("create sandbox");
    let review = sandbox.path().join("review");
    fs::create_dir_all(&review).expect("create review directory");
    let ballot_path = sandbox.path().join("ballot.md");
    fs::write(
        &ballot_path,
        ballot("alice", "FINDING_1: high-severity neutral finding"),
    )
    .expect("write ballot");
    let voters = [
        sandbox.path().join("v1.txt"),
        sandbox.path().join("v2.txt"),
        sandbox.path().join("v3.txt"),
    ];
    fs::write(&voters[0], vote("FINDING_1", "YES", "major")).expect("write voter one");
    for voter in &voters[1..] {
        fs::write(voter, vote("FINDING_1", "NO", "nit")).expect("write no voter");
    }
    let arguments = [
        "tally-code-votes",
        "--ballot-file",
        ballot_path.to_str().expect("ballot path"),
        "--review-tmpdir",
        review.to_str().expect("review path"),
        "--voter-files",
        voters[0].to_str().expect("voter path"),
        voters[1].to_str().expect("voter path"),
        voters[2].to_str().expect("voter path"),
    ];
    let output = run(&arguments, sandbox.path());
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8(output.stdout).expect("stdout UTF-8");
    assert!(stdout.contains("OOS_REJECTED_COUNT=1\n"));
    let tally = fs::read_to_string(review.join("review-tally.env")).expect("read tally env");
    assert!(tally.contains("FINDING_1_OUTCOME=oos\n"));
    assert!(!tally.contains("FINDING_1_REJECTED_SUBTYPE"));
    let oos = fs::read_to_string(review.join("oos.md")).expect("read OOS artifact");
    assert!(oos.contains("neutral-rescued"));
    assert!(
        fs::read_to_string(review.join("rejected-findings.md"))
            .expect("read rejected artifact")
            .is_empty()
    );
}

#[test]
fn tally_empty_ballot_writes_stable_skipped_artifacts() {
    let sandbox = TempDir::new().expect("create sandbox");
    let review = sandbox.path().join("review");
    fs::create_dir_all(&review).expect("create review directory");
    let ballot_path = sandbox.path().join("ballot.md");
    fs::write(&ballot_path, "").expect("write empty ballot");
    let arguments = [
        "tally-code-votes",
        "--ballot-file",
        ballot_path.to_str().expect("ballot path"),
        "--review-tmpdir",
        review.to_str().expect("review path"),
        "--voter-files",
    ];
    let output = run(&arguments, sandbox.path());
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert_eq!(
        String::from_utf8(output.stdout).expect("stdout UTF-8"),
        format!(
            "TALLY_STATUS=skipped-empty-findings\nACCEPTED_COUNT=0\nREJECTED_COUNT=0\nEXONERATED_COUNT=0\nNEUTRAL_COUNT=0\nOOS_ACCEPTED_COUNT=0\nOOS_REJECTED_COUNT=0\nOUT_OF_SCOPE_DRIFT_COUNT=0\nVOTING_TALLY_FILE={}\nTALLY_FILE={}\nACCEPTED_FINDINGS_FILE={}\nREJECTED_FINDINGS_FILE={}\nOOS_ACCEPTED_FILE={}\nOOS_FILE={}\nTALLY_OK=true\nELIGIBLE_VOTER_COUNT=0\nVOTER_COUNT=0\nPARSE_FAILED_COUNT=0\nFINDINGS_CLASSIFICATION_TSV_FILE={}\n",
            review.join("voting-tally.md").display(),
            review.join("review-tally.env").display(),
            review.join("accepted-findings.md").display(),
            review.join("rejected-findings.md").display(),
            review.join("oos-accepted-review.md").display(),
            review.join("oos.md").display(),
            review.join("findings-classification-round-1.tsv").display(),
        ),
    );
    assert_eq!(
        fs::read_to_string(review.join("voting-tally.md")).expect("read voting tally"),
        "# Code Review Voting Tally\n\nRound skipped: no findings to adjudicate.\n\n## Voter Agreement Scoreboard\n\n| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |\n|---|---|---:|---:|---:|---:|---:|---|\n| undefined | n/a | 0 | 0 | 0 | 0 | n/a | false |\n\nAgreement is undefined when no accepted or rejected finding has at least two parseable YES/NO voter cells.\n\n## Voter Severity Scoreboard\n\n| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |\n|---|---|---:|---:|---:|---:|---:|---:|---:|---|\n| undefined | n/a | 0 | 0 | 0 | 0 | 0 | n/a | n/a | false |\n\nSeverity calibration is undefined when no accepted or rejected finding has at least two parseable YES/NO voter cells.\n",
    );
}

#[test]
fn emit_tally_writes_summary_and_legacy_rejected_fallback() {
    let sandbox = TempDir::new().expect("create sandbox");
    let review = sandbox.path().join("review");
    fs::create_dir_all(&review).expect("create review directory");
    let tally = review.join("review-tally.env");
    let accepted = review.join("accepted-findings.md");
    let oos = review.join("oos.md");
    fs::write(
        &tally,
        "FINDING_1_ACCEPTED=true\nFINDING_2_ACCEPTED=false\nACCEPTED_COUNT=\nREJECTED_COUNT=\n",
    )
    .expect("write tally");
    fs::write(&accepted, "### FINDING_1: accepted\n").expect("write accepted");
    fs::write(&oos, "").expect("write OOS");
    let arguments = [
        "emit-tally",
        "--tally-file",
        tally.to_str().expect("tally path"),
        "--accepted-findings-file",
        accepted.to_str().expect("accepted path"),
        "--oos-file",
        oos.to_str().expect("oos path"),
        "--review-tmpdir",
        review.to_str().expect("review path"),
        "--mode",
        "diff",
    ];
    let output = run(&arguments, sandbox.path());
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8(output.stdout).expect("stdout UTF-8");
    assert!(stdout.contains("EMIT_OK=true\n"));
    assert!(stdout.contains("OOS_FILING_COUNT=0\n"));
    assert_eq!(
        fs::read_to_string(review.join("review-round-summary.md")).expect("read round summary"),
        "# Review Round 1\n\n- Mode: `diff`\n- 1 accepted, 1 rejected (0 neutral)\n\n## Accepted Findings\n\n### FINDING_1: accepted\n",
    );
    assert_eq!(
        fs::read_to_string(review.join("rejected-findings.md")).expect("read rejected fallback"),
        "# Rejected Findings\n\n2:FINDING_2_ACCEPTED=false\n",
    );
    let summary =
        fs::read_to_string(review.join("review-summary.json")).expect("read review summary");
    assert_eq!(
        summary,
        "{\"accepted_count\":1,\"exonerated_count\":0,\"finding_counts\":{\"total_accepted\":1,\"total_exonerated\":0,\"total_neutral\":0,\"total_rejected\":1},\"neutral_count\":0,\"panel\":{\"dynamic_slot_count\":0,\"scout_status\":\"na\",\"static_slot_count\":0,\"total_slot_count\":0},\"rejected_count\":1,\"reviewer_output_paths\":[],\"rounds_completed\":1,\"schema_version\":3}\n"
    );
}

#[test]
fn emit_tally_promotes_non_security_main_agent_oos_to_the_parent_sink() {
    let sandbox = TempDir::new().expect("create sandbox");
    let parent = sandbox.path().join("implement");
    let review = parent.join("round-1");
    fs::create_dir_all(&review).expect("create review directory");
    let session_env = parent.join("session-env.sh");
    fs::write(&session_env, "RUN_ID=run-1\n").expect("write session env");
    let tally = review.join("review-tally.env");
    let accepted = review.join("accepted-findings.md");
    let oos = review.join("oos.md");
    fs::write(
        &tally,
        "ACCEPTED_COUNT=0\nREJECTED_COUNT=0\nNEUTRAL_COUNT=0\nOOS_ACCEPTED_COUNT=0\n",
    )
    .expect("write tally");
    fs::write(&accepted, "").expect("write accepted artifact");
    fs::write(&oos, "").expect("write OOS artifact");
    fs::write(
        parent.join("oos-accepted-main-agent.md"),
        "### OOS_12: non-security parent finding\n- **Concern**: preserve this finding.\n",
    )
    .expect("write parent OOS artifact");
    let arguments = [
        "emit-tally",
        "--tally-file",
        tally.to_str().expect("tally path"),
        "--accepted-findings-file",
        accepted.to_str().expect("accepted path"),
        "--oos-file",
        oos.to_str().expect("OOS path"),
        "--review-tmpdir",
        review.to_str().expect("review path"),
        "--session-env-path",
        session_env.to_str().expect("session env path"),
        "--round",
        "1",
        "--mode",
        "diff",
    ];
    let output = run(&arguments, sandbox.path());
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let sink =
        fs::read_to_string(review.join("oos-accepted-review.md")).expect("read promoted OOS sink");
    assert!(sink.contains("### OOS_1: non-security parent finding"));
    assert_eq!(
        fs::read_to_string(parent.join("oos-accepted-review.md")).expect("read parent copy"),
        sink
    );
}

#[test]
fn log_phase_rejects_unregistered_batches_before_bootstrap() {
    let sandbox = TempDir::new().expect("create sandbox");
    let payload = sandbox.path().join("payload.md");
    fs::write(&payload, "payload\n").expect("write payload");
    let arguments = [
        "log-phase",
        "--run-id",
        "run",
        "--batch",
        "not-registered",
        "--action",
        "write",
        "--payload-file",
        payload.to_str().expect("payload path"),
    ];
    let output = run(&arguments, sandbox.path());
    assert_eq!(output.status.code(), Some(2));
    assert_eq!(
        output.stderr,
        b"log-phase: unregistered review batch: not-registered\n"
    );
}

#[test]
fn log_phase_writes_registered_batch_through_verified_bootstrap() {
    let sandbox = TempDir::new().expect("create sandbox");
    let payload = sandbox.path().join("payload.md");
    let log_root = sandbox.path().join("logs");
    fs::write(&payload, "# Review Context\n").expect("write payload");
    let plugin_root = repository_root();
    let plugin_root = plugin_root.to_str().expect("plugin root UTF-8");
    let arguments = [
        "log-phase",
        "--run-id",
        "run-1",
        "--batch",
        "review-context",
        "--action",
        "write",
        "--payload-file",
        payload.to_str().expect("payload path"),
        "--log-root",
        log_root.to_str().expect("log root path"),
    ];
    let output = run_with_environment(
        &arguments,
        sandbox.path(),
        &[
            ("CLAUDE_PLUGIN_ROOT", plugin_root),
            ("LARCH_BINARY", env!("CARGO_BIN_EXE_larch")),
        ],
    );
    assert!(
        output.status.success(),
        "stdout: {}\nstderr: {}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(log_root.join("review").join("run-1").is_dir());
}
