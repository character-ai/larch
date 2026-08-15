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

fn write_emit_tally_artifacts(parent: &Path, review: &Path) -> (PathBuf, PathBuf, PathBuf) {
    let tally = review.join("review-tally.env");
    let accepted = review.join("accepted-findings.md");
    let oos = review.join("oos.md");
    fs::write(
        &tally,
        "ACCEPTED_COUNT=1\nREJECTED_COUNT=1\nNEUTRAL_COUNT=0\nOOS_ACCEPTED_COUNT=1\n",
    )
    .expect("write tally");
    fs::write(&accepted, "### FINDING_1: accepted\n").expect("write accepted findings");
    fs::write(
        review.join("rejected-findings.md"),
        "### FINDING_2: preserved rejection\n",
    )
    .expect("write rejected findings");
    fs::write(
        &oos,
        concat!(
            "### OOS_7: public follow-up\n",
            "- **Description**: preserve the accepted OOS artifact.\n",
            "Vote tally: Result=accepted Fileable=true\n",
        ),
    )
    .expect("write OOS artifact");
    fs::write(
        review.join("cursor-specialist-output.txt"),
        "review output\n",
    )
    .expect("write reviewer output");
    fs::write(
        parent.join("oos-accepted-main-agent.md"),
        "### OOS_9: parent follow-up\n- **Concern**: publish this too.\n",
    )
    .expect("write parent OOS artifact");
    fs::write(
        parent.join("oos-aggregate-pool.md"),
        concat!(
            "### OOS_10: pooled follow-up\n",
            "- **Concern**: publish the pooled item.\n",
            "Vote tally: Result=accepted Fileable=true\n",
        ),
    )
    .expect("write aggregate pool");
    (tally, accepted, oos)
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
fn emit_tally_uses_voting_tally_artifact_summary_without_metadata() {
    let sandbox = TempDir::new().expect("create sandbox");
    let review = sandbox.path().join("review");
    fs::create_dir_all(&review).expect("create review directory");
    let tally = review.join("review-tally.env");
    let accepted = review.join("accepted-findings.md");
    let oos = review.join("oos.md");
    fs::write(
        &tally,
        "FINDING_1_ACCEPTED=true\nFINDING_2_ACCEPTED=false\n",
    )
    .expect("write tally");
    fs::write(&accepted, "").expect("write accepted");
    fs::write(&oos, "").expect("write OOS");
    fs::write(
        review.join("voting-tally.md"),
        concat!(
            "# Code Review Voting Tally\n\n",
            "## Findings\n\n",
            "| Item | YES | NO | JERR | Result |\n",
            "|---|---:|---:|---:|---|\n",
            "| FINDING_1 | 2 | 1 | 0 | accepted |\n",
            "| FINDING_2 | 1 | 2 | 0 | rejected |\n",
            "| FINDING_3 | 1 | 1 | 1 | neutral |\n",
            "| OOS_1 | 2 | 1 | 0 | accepted |\n",
            "\n## Voter Agreement Scoreboard\n",
        ),
    )
    .expect("write voting tally");
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
    assert!(
        fs::read_to_string(review.join("review-round-summary.md"))
            .expect("read round summary")
            .contains("1 accepted, 1 rejected (1 neutral)"),
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

#[test]
fn tally_emits_manifest_yield_and_dead_scoreboard_rows() {
    let sandbox = TempDir::new().expect("create sandbox");
    let review = sandbox.path().join("review");
    fs::create_dir_all(&review).expect("create review directory");
    let ballot_path = review.join("ballot.md");
    fs::write(
        &ballot_path,
        "### FINDING_1: In-scope issue\n- **Reviewer**: cursor-specialist-correctness-output.txt\n- **Concern**: real bug\n- **Suggested revision**: fix it\n",
    )
    .expect("write ballot");
    let live = review.join("cursor-specialist-correctness-output.txt");
    let dead = review.join("cursor-specialist-testing-output.txt");
    let generalist = review.join("codex-generalist-output.txt");
    let dynamic = review.join("dyn-risk-output.txt");
    let forced = review.join("cursor-specialist-plan-fidelity-forced-output.txt");
    let generic = review.join("custom-output.txt");
    fs::write(
        &live,
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
    )
    .expect("write live vote");
    fs::write(&dead, "narrative only\n").expect("write dead vote");
    let manifest = review.join("panel.ndjson");
    fs::write(
        &manifest,
        format!(
            concat!(
                "{{\"slot\":\"correctness\",\"tool\":\"cursor\",\"output\":\"{}\",\"focus_area\":\"correctness\",\"weight\":\"1\"}}\n",
                "{{\"slot\":\"testing\",\"tool\":\"cursor\",\"output\":\"{}\",\"focus_area\":\"risk-integration\",\"weight\":\"1\"}}\n",
                "{{\"slot\":\"generalist\",\"tool\":\"codex\",\"output\":\"{}\"}}\n",
                "{{\"slot\":\"dyn-risk\",\"tool\":\"codex\",\"output\":\"{}\",\"weight\":\"2\"}}\n",
                "{{\"slot\":\"plan-fidelity-forced\",\"tool\":\"cursor\",\"output\":\"{}\"}}\n",
                "{{\"slot\":\"\",\"tool\":\"cursor\",\"output\":\"{}\",\"weight\":\"not-a-number\"}}\n",
            ),
            live.display(),
            dead.display(),
            generalist.display(),
            dynamic.display(),
            forced.display(),
            generic.display(),
        ),
    )
    .expect("write manifest");
    let collector = review.join("collector-results.env");
    fs::write(
        &collector,
        format!(
            "REVIEWER_FILE={}\nSTATUS=NOT_SUBSTANTIVE\n\n",
            dead.display()
        ),
    )
    .expect("write collector results");
    let arguments = vec![
        "tally-code-votes".to_owned(),
        "--ballot-file".to_owned(),
        ballot_path.display().to_string(),
        "--review-tmpdir".to_owned(),
        review.display().to_string(),
        "--voter-files".to_owned(),
        live.display().to_string(),
        "--manifest-file".to_owned(),
        manifest.display().to_string(),
        "--collector-results-file".to_owned(),
        collector.display().to_string(),
    ];
    let borrowed = arguments.iter().map(String::as_str).collect::<Vec<_>>();
    let output = run(&borrowed, sandbox.path());
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8(output.stdout).expect("stdout UTF-8");
    assert!(stdout.contains("YIELD_TSV_FILE="));
    let tally = fs::read_to_string(review.join("voting-tally.md")).expect("read voting tally");
    assert!(tally.contains("cursor-specialist-testing"));
    assert!(tally.contains("STATUS=NOT_SUBSTANTIVE"));
    let yield_tsv =
        fs::read_to_string(review.join("scout-archetype-yield.tsv")).expect("read archetype yield");
    assert!(yield_tsv.contains("correctness\tcorrectness\t1\t1"));
    assert!(yield_tsv.contains("generic\tcode-quality\t1\t0\t0\t0\tn/a"));
    assert!(yield_tsv.contains("plan-fidelity-forced\tarchitecture\t1\t0\t0\t0\tn/a"));
}

#[test]
fn tally_records_mixed_scoreboard_and_oos_outcomes() {
    let sandbox = TempDir::new().expect("create sandbox");
    let review = sandbox.path().join("review");
    fs::create_dir_all(&review).expect("create review directory");
    let ballot_path = review.join("ballot.md");
    fs::write(
        &ballot_path,
        concat!(
            "### FINDING_1: Major in-scope\n- **Reviewer**: Codex-Correctness\n- **Concern**: major bug\n\n",
            "### FINDING_2: Minor in-scope\n- **Reviewer**: Cursor-Testing\n- **Concern**: minor bug\n\n",
            "### FINDING_3: Co-proposed major\n- **Reviewer(s)**: Codex-Arch, Cursor-Testing\n- **Concern**: shared bug\n\n",
            "### FINDING_4: Neutral in-scope\n- **Reviewer**: Codex-Neutral\n- **Concern**: borderline bug\n\n",
            "### OOS_1: [OUT_OF_SCOPE] accepted follow-up\n- **Reviewer**: Codex-Edge\n- **Concern**: future work\n\n",
            "### OOS_2: [OUT_OF_SCOPE] rejected follow-up\n- **Reviewer**: Codex-OOS-Neutral\n- **Concern**: future work\n",
        ),
    )
    .expect("write ballot");
    let voters = [
        review.join("v1.txt"),
        review.join("v2.txt"),
        review.join("v3.txt"),
    ];
    fs::write(
        &voters[0],
        concat!(
            "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
            "FINDING_2: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
            "FINDING_3: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
            "FINDING_4: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
            "OOS_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
            "OOS_2: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
        ),
    )
    .expect("write first vote");
    fs::write(
        &voters[1],
        concat!(
            "FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
            "FINDING_2: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
            "FINDING_3: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
            "FINDING_4: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n",
            "OOS_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
            "OOS_2: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n",
        ),
    )
    .expect("write second vote");
    fs::write(
        &voters[2],
        concat!(
            "FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
            "FINDING_2: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
            "FINDING_3: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
            "OOS_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
            "OOS_2: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n",
        ),
    )
    .expect("write third vote");
    let arguments = tally_arguments(&ballot_path, &review, &[&voters[0], &voters[1], &voters[2]]);
    let borrowed = arguments.iter().map(String::as_str).collect::<Vec<_>>();
    let output = run(&borrowed, sandbox.path());
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8(output.stdout).expect("stdout UTF-8");
    assert!(stdout.contains("OOS_ACCEPTED_COUNT=1\n"));
    assert!(stdout.contains("OOS_REJECTED_COUNT=1\n"));
    let tally = fs::read_to_string(review.join("voting-tally.md")).expect("read voting tally");
    for reviewer in [
        "Codex-Correctness",
        "Cursor-Testing",
        "Codex-Arch",
        "Codex-Neutral",
        "Codex-Edge",
        "Codex-OOS-Neutral",
    ] {
        assert!(
            tally.contains(reviewer),
            "missing scoreboard row for {reviewer}"
        );
    }
    let classification = fs::read_to_string(review.join("findings-classification-round-1.tsv"))
        .expect("read classification");
    assert!(classification.contains("FINDING_4\tCodex-Neutral\tneutral"));
    assert!(classification.contains("OOS_1\tCodex-Edge\taccepted"));
    assert!(
        classification.contains("OOS_2\tCodex-OOS-Neutral\tneutral"),
        "{classification}"
    );
}

#[test]
fn tally_marks_partial_quorum_and_scope_drift() {
    let sandbox = TempDir::new().expect("create sandbox");
    let review = sandbox.path().join("review");
    fs::create_dir_all(&review).expect("create review directory");
    let ballot_path = review.join("ballot.md");
    let ballot = concat!(
        "### FINDING_1: In-scope finding 1 — `docs/linting.md:22`\n- **Reviewer**: Cursor-Correctness\n- **Concern**: bug 1\n\n",
        "### FINDING_2: In-scope finding 2\n- **Reviewer**: Cursor-Correctness\n- **Concern**: bug 2\n\n",
        "### FINDING_3: In-scope finding 3\n- **Reviewer**: Cursor-Correctness\n- **Concern**: bug 3\n\n",
        "### FINDING_4: In-scope finding 4\n- **Reviewer**: Cursor-Correctness\n- **Concern**: bug 4\n\n",
        "### FINDING_5: In-scope finding 5\n- **Reviewer**: Cursor-Correctness\n- **Concern**: bug 5\n\n",
    );
    fs::write(&ballot_path, ballot).expect("write ballot");
    let scope = review.join("scope-files.txt");
    fs::write(&scope, "python/cli.py\n").expect("write scope");
    let voters = [
        review.join("v1.txt"),
        review.join("v2.txt"),
        review.join("v3.txt"),
    ];
    let full = concat!(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
        "FINDING_2: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
        "FINDING_3: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
        "FINDING_4: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
        "FINDING_5: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
    );
    let partial = concat!(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
        "FINDING_2: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
        "FINDING_3: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
        "FINDING_4: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
    );
    fs::write(&voters[0], full).expect("write full vote");
    fs::write(&voters[1], partial).expect("write second partial vote");
    fs::write(&voters[2], partial).expect("write third partial vote");
    let mut arguments =
        tally_arguments(&ballot_path, &review, &[&voters[0], &voters[1], &voters[2]]);
    arguments.extend(["--scope-files".to_owned(), scope.display().to_string()]);
    let borrowed = arguments.iter().map(String::as_str).collect::<Vec<_>>();
    let output = run(&borrowed, sandbox.path());
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8(output.stdout).expect("stdout UTF-8");
    assert!(stdout.contains("UNDER_QUORUM_COUNT=1\n"));
    assert!(stdout.contains("UNDER_QUORUM_ITEMS=FINDING_5\n"));
    assert!(stdout.contains("OUT_OF_SCOPE_DRIFT_COUNT=1\n"));
    let tally = fs::read_to_string(review.join("voting-tally.md")).expect("read voting tally");
    assert!(tally.contains("decided below the 2-of-3 panel quorum"));
    assert!(tally.contains("| FINDING_5 | 1 | 0 | 2 | neutral |"));
    assert!(
        fs::read_to_string(review.join("oos.md"))
            .expect("read OOS output")
            .contains("docs/linting.md:22"),
    );
}

#[test]
fn tally_restores_neutralized_proposer_and_rejects_missing_map_rows() {
    let sandbox = TempDir::new().expect("create sandbox");
    let ballot = concat!(
        "### FINDING_1: First in-scope finding\n",
        "- **Reviewer**: anonymous\n",
        "- **Concern**: concrete concern\n",
        "- **Suggested revision**: revision\n",
    );
    let ballot_path = sandbox.path().join("neutral-ballot.md");
    fs::write(&ballot_path, ballot).expect("write neutral ballot");
    let map_path = sandbox.path().join("proposer-map.tsv");
    fs::write(
        &map_path,
        format!(
            "# neutral_ballot_sha256={:x}\nFINDING_1\tCodex-Structure\t- **Reviewer**: Codex-Structure\n",
            Sha256::digest(ballot.as_bytes())
        ),
    )
    .expect("write proposer map");
    let voter = sandbox.path().join("v1.txt");
    fs::write(
        &voter,
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
    )
    .expect("write vote");
    let review = sandbox.path().join("review");
    fs::create_dir_all(&review).expect("create review directory");
    let arguments = vec![
        "tally-code-votes".to_owned(),
        "--ballot-file".to_owned(),
        ballot_path.display().to_string(),
        "--review-tmpdir".to_owned(),
        review.display().to_string(),
        "--voter-files".to_owned(),
        voter.display().to_string(),
        "--proposer-map-file".to_owned(),
        map_path.display().to_string(),
    ];
    let borrowed = arguments.iter().map(String::as_str).collect::<Vec<_>>();
    let output = run(&borrowed, sandbox.path());
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let accepted =
        fs::read_to_string(review.join("accepted-findings.md")).expect("read accepted findings");
    assert!(accepted.contains("- **Reviewer**: Codex-Structure"));
    assert!(!accepted.contains("anonymous"));

    let invalid_map = sandbox.path().join("invalid-proposer-map.tsv");
    fs::write(
        &invalid_map,
        format!(
            "# neutral_ballot_sha256={:x}\n",
            Sha256::digest(ballot.as_bytes())
        ),
    )
    .expect("write invalid proposer map");
    let invalid_review = sandbox.path().join("invalid-review");
    fs::create_dir_all(&invalid_review).expect("create invalid review directory");
    let invalid_arguments = vec![
        "tally-code-votes".to_owned(),
        "--ballot-file".to_owned(),
        ballot_path.display().to_string(),
        "--review-tmpdir".to_owned(),
        invalid_review.display().to_string(),
        "--voter-files".to_owned(),
        voter.display().to_string(),
        "--proposer-map-file".to_owned(),
        invalid_map.display().to_string(),
    ];
    let borrowed = invalid_arguments
        .iter()
        .map(String::as_str)
        .collect::<Vec<_>>();
    let output = run(&borrowed, sandbox.path());
    assert_eq!(output.status.code(), Some(2));
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("proposer map item mismatch"),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
}

#[test]
fn tally_keeps_security_oos_private_and_seeds_public_oos_numbering() {
    let sandbox = TempDir::new().expect("create sandbox");
    let parent = sandbox.path().join("implement");
    let review = parent.join("round-2");
    fs::create_dir_all(&review).expect("create review directory");
    let session_env = parent.join("session-env.sh");
    fs::write(&session_env, "").expect("write session environment");
    fs::write(
        parent.join("accumulated-oos.md"),
        "### OOS_1: [OUT_OF_SCOPE] previous follow-up\n- **Reviewer**: previous\n",
    )
    .expect("write accumulated OOS");
    let ballot_path = review.join("ballot.md");
    fs::write(
        &ballot_path,
        concat!(
            "### FINDING_1: [OUT_OF_SCOPE] security cleanup\n",
            "- **Reviewer**: Codex-Security\n",
            "- **focus-area**: security\n",
            "- **Concern**: keep this private\n\n",
            "### FINDING_2: [OUT_OF_SCOPE] public follow-up\n",
            "- **Reviewer**: Codex-Structure\n",
            "- **Concern**: publish this\n",
        ),
    )
    .expect("write ballot");
    let voters = [
        review.join("v1.txt"),
        review.join("v2.txt"),
        review.join("v3.txt"),
    ];
    let vote_text = concat!(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
        "FINDING_2: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
    );
    for voter in &voters {
        fs::write(voter, vote_text).expect("write vote");
    }
    let mut arguments =
        tally_arguments(&ballot_path, &review, &[&voters[0], &voters[1], &voters[2]]);
    arguments.extend([
        "--session-env-path".to_owned(),
        session_env.display().to_string(),
    ]);
    let borrowed = arguments.iter().map(String::as_str).collect::<Vec<_>>();
    let output = run(&borrowed, sandbox.path());
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8(output.stdout).expect("stdout UTF-8");
    assert!(stdout.contains("OOS_ACCEPTED_COUNT=1\n"));
    let security = fs::read_to_string(parent.join("security-oos-observations.md"))
        .expect("read private security observations");
    assert!(security.contains("security cleanup"));
    let pool = fs::read_to_string(parent.join("oos-aggregate-pool.md")).expect("read public pool");
    assert!(pool.contains("public follow-up"));
    assert!(!pool.contains("security cleanup"));
    let accepted =
        fs::read_to_string(review.join("oos-accepted-review.md")).expect("read accepted OOS");
    assert!(
        accepted.contains("### OOS_2: [OUT_OF_SCOPE] public follow-up"),
        "{accepted}"
    );
    assert!(!accepted.contains("security cleanup"));
}

#[test]
fn tally_degrades_three_slots_without_losing_unique_finder_credit() {
    let sandbox = TempDir::new().expect("create sandbox");
    let review = sandbox.path().join("review");
    fs::create_dir_all(&review).expect("create review directory");
    let ballot_path = review.join("ballot.md");
    fs::write(
        &ballot_path,
        ballot(
            "cursor-specialist-correctness-output.txt",
            "FINDING_1: sole finding",
        ),
    )
    .expect("write ballot");
    let voters = [
        review.join("v1.txt"),
        review.join("v2.txt"),
        review.join("v3.txt"),
    ];
    fs::write(&voters[0], vote("FINDING_1", "YES", "major")).expect("write live vote");
    fs::write(&voters[1], "narrative only\n").expect("write failed vote");
    fs::write(&voters[2], "narrative only\n").expect("write failed vote");
    let mut arguments =
        tally_arguments(&ballot_path, &review, &[&voters[0], &voters[1], &voters[2]]);
    arguments.extend([
        "--codex-available".to_owned(),
        "true".to_owned(),
        "--not-substantive-count".to_owned(),
        "2".to_owned(),
    ]);
    let borrowed = arguments.iter().map(String::as_str).collect::<Vec<_>>();
    let output = run_with_environment(
        &borrowed,
        sandbox.path(),
        &[("LARCH_UNIQUE_FINDER_BONUS", "0.5")],
    );
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8(output.stdout).expect("stdout UTF-8");
    assert!(stdout.contains("VOTER_COUNT=1\n"));
    assert!(stdout.contains("PARSE_FAILED_COUNT=2\n"));
    let tally = fs::read_to_string(review.join("voting-tally.md")).expect("read voting tally");
    assert!(tally.contains("Degraded code-review panel: 1 judge(s) available"));
    assert!(tally.contains("2 reviewer slot(s) emitted narrative-only output"));
    assert!(tally.contains("**Unique finder bonus active:** 1 accepted in-scope sole-finder"));
    assert!(tally.contains("| cursor-specialist-correctness | 1 | 1 | 0 | 0 |"));
}

#[test]
fn tally_and_emit_reject_invalid_safety_boundaries() {
    let sandbox = TempDir::new().expect("create sandbox");
    let review = sandbox.path().join("review");
    fs::create_dir_all(&review).expect("create review directory");
    let ballot_path = review.join("ballot.md");
    fs::write(&ballot_path, ballot("alice", "FINDING_1: a finding")).expect("write ballot");
    let missing_manifest = review.join("missing.ndjson");
    let invalid_manifest = [
        "tally-code-votes",
        "--ballot-file",
        ballot_path.to_str().expect("ballot path"),
        "--review-tmpdir",
        review.to_str().expect("review path"),
        "--manifest-file",
        missing_manifest.to_str().expect("manifest path"),
    ];
    let output = run(&invalid_manifest, sandbox.path());
    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("--manifest-file must name a file"));
    let invalid_round = [
        "tally-code-votes",
        "--ballot-file",
        ballot_path.to_str().expect("ballot path"),
        "--review-tmpdir",
        review.to_str().expect("review path"),
        "--round-num",
        "0",
    ];
    let output = run(&invalid_round, sandbox.path());
    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("positive integer"));
    let one_voter = review.join("voter.txt");
    fs::write(&one_voter, vote("FINDING_1", "YES", "minor")).expect("write voter");
    let invalid_slots = [
        "tally-code-votes",
        "--ballot-file",
        ballot_path.to_str().expect("ballot path"),
        "--review-tmpdir",
        review.to_str().expect("review path"),
        "--voter-files",
        one_voter.to_str().expect("voter path"),
        "--voter-tools",
        "codex",
    ];
    let output = run(&invalid_slots, sandbox.path());
    assert_eq!(output.status.code(), Some(2));
    assert!(
        String::from_utf8_lossy(&output.stderr)
            .contains("requires exactly three --voter-files and three tool labels")
    );

    let tally = review.join("review-tally.env");
    let accepted = review.join("accepted-findings.md");
    let oos = review.join("oos.md");
    fs::write(&tally, "OOS_ACCEPTED_COUNT=2\n").expect("write tally");
    fs::write(&accepted, "").expect("write accepted findings");
    fs::write(&oos, "").expect("write OOS artifact");
    fs::write(
        review.join("oos-accepted-review.md"),
        "### OOS_1: already accepted\n- **Concern**: retain\n",
    )
    .expect("write partial accepted OOS sink");
    let emit = [
        "emit-tally",
        "--tally-file",
        tally.to_str().expect("tally path"),
        "--accepted-findings-file",
        accepted.to_str().expect("accepted path"),
        "--oos-file",
        oos.to_str().expect("OOS path"),
        "--review-tmpdir",
        review.to_str().expect("review path"),
        "--mode",
        "description",
    ];
    let output = run(&emit, sandbox.path());
    assert_eq!(output.status.code(), Some(1));
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("refusing destructive rebuild"),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let invalid_panel = [
        "emit-tally",
        "--tally-file",
        tally.to_str().expect("tally path"),
        "--accepted-findings-file",
        accepted.to_str().expect("accepted path"),
        "--oos-file",
        oos.to_str().expect("OOS path"),
        "--review-tmpdir",
        review.to_str().expect("review path"),
        "--mode",
        "diff",
        "--dynamic-slots",
        "not-a-number",
    ];
    let output = run(&invalid_panel, sandbox.path());
    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("must be non-negative integers"));
}

#[test]
fn tally_requires_manual_adjudication_when_all_three_slots_are_narrative_only() {
    let sandbox = TempDir::new().expect("create sandbox");
    let parent = sandbox.path().join("implement");
    let review = parent.join("round-1");
    fs::create_dir_all(&review).expect("create review directory");
    let session_env = parent.join("session-env.sh");
    fs::write(&session_env, "RUN_ID=run-1\n").expect("write session environment");
    let ballot_path = review.join("ballot.md");
    fs::write(
        &ballot_path,
        ballot("alice", "FINDING_1: needs a human decision"),
    )
    .expect("write ballot");
    let voters = [
        review.join("v1.txt"),
        review.join("v2.txt"),
        review.join("v3.txt"),
    ];
    for voter in &voters {
        fs::write(voter, "narrative only\n").expect("write narrative vote");
    }
    let mut arguments =
        tally_arguments(&ballot_path, &review, &[&voters[0], &voters[1], &voters[2]]);
    arguments.extend([
        "--session-env-path".to_owned(),
        session_env.display().to_string(),
        "--not-substantive-count".to_owned(),
        "3".to_owned(),
    ]);
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
    assert!(stdout.contains("VOTER_COUNT=0\n"));
    assert!(stdout.contains("PARSE_FAILED_COUNT=3\n"));
    let tally = fs::read_to_string(review.join("voting-tally.md")).expect("read tally");
    assert!(tally.contains("Panel tier: main-agent-required"));
    assert!(tally.contains("3 reviewer slot(s) emitted narrative-only output"));
    assert!(tally.contains("3 voter slot(s) emitted narrative-only output"));
    assert!(
        fs::read_to_string(parent.join("oos-accepted-review.md"))
            .expect("read parent OOS output")
            .is_empty()
    );
}

#[test]
fn emit_tally_rebuilds_oos_and_publishes_complete_parent_artifacts() {
    let sandbox = TempDir::new().expect("create sandbox");
    let parent = sandbox.path().join("implement");
    let review = parent.join("round-2");
    fs::create_dir_all(&review).expect("create review directory");
    let session_env = parent.join("session-env.sh");
    fs::write(&session_env, "RUN_ID=run-2\n").expect("write session environment");
    let (tally, accepted, oos) = write_emit_tally_artifacts(&parent, &review);
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
        session_env.to_str().expect("session environment path"),
        "--implement-tmpdir",
        parent.to_str().expect("implement path"),
        "--round",
        "2",
        "--mode",
        "diff",
        "--scout-status",
        "ready",
        "--dynamic-slots",
        "2",
        "--static-slot-count",
        "3",
    ];
    let output = run(&arguments, sandbox.path());
    assert!(
        output.status.success(),
        "stdout: {}\nstderr: {}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8(output.stdout).expect("stdout UTF-8");
    assert!(stdout.contains("EMIT_OK=true\n"));
    assert!(stdout.contains("OOS_FILING_COUNT=3\n"));
    let sink = fs::read_to_string(review.join("oos-accepted-review.md")).expect("read OOS sink");
    assert!(sink.contains("### OOS_1: public follow-up"));
    assert!(sink.contains("### OOS_2: parent follow-up"));
    assert!(sink.contains("### OOS_3: pooled follow-up"));
    assert_eq!(
        fs::read_to_string(parent.join("oos-accepted-review.md")).expect("read copied OOS sink"),
        sink
    );
    assert_eq!(
        fs::read_to_string(parent.join("rejected-findings-full.md"))
            .expect("read full rejected findings"),
        "### FINDING_2: preserved rejection\n"
    );
    let summary =
        fs::read_to_string(parent.join("review-summary.json")).expect("read copied review summary");
    assert!(summary.contains("\"rounds_completed\":2"));
    assert!(summary.contains("\"dynamic_slot_count\":2"));
    assert!(summary.contains("cursor-specialist-output.txt"));
    assert!(parent.join("review-round-summary.md").is_file());
}
