use std::{
    fs,
    path::Path,
    process::{Command, Output},
};
use tempfile::TempDir;

const FIXTURES: &str = "python/test_fixtures/plan-fidelity-calibration";
const RUNS: [(&str, u64, &str); 4] = [
    ("66A96EAD-3088-4750-AE3A-64A0E11EABBD", 2, "FINDING_10"),
    ("3ED15A95-C722-4ABE-904C-729E1A730C5D", 1, "FINDING_10"),
    ("33A6D738-B665-43BE-B89E-EDA96E7C887E", 1, "FINDING_3"),
    ("E79F3F0B-4459-48FB-8241-5DDB90ABF050", 2, "FINDING_1"),
];

fn invoke(root: &Path, args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(args)
        .current_dir(root)
        .env_remove("LARCH_VOTER_CALIBRATION_WINDOW")
        .envs([
            ("LARCH_CONSUMER_REPO", ""),
            ("CLAUDE_PROJECT_DIR", ""),
            ("REPO_ROOT", ""),
            ("CLAUDE_PLUGIN_ROOT", ""),
        ])
        .output()
        .unwrap()
}

fn copy_tree(source: &Path, target: &Path) {
    fs::create_dir_all(target).unwrap();
    for entry in fs::read_dir(source).unwrap() {
        let entry = entry.unwrap();
        let target = target.join(entry.file_name());
        if entry.file_type().unwrap().is_dir() {
            copy_tree(&entry.path(), &target);
        } else {
            fs::copy(entry.path(), target).unwrap();
        }
    }
}

fn seed(root: &Path) {
    let repo = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    copy_tree(&repo.join(FIXTURES), &root.join(FIXTURES));
    for (run, round, _) in RUNS {
        let target = root.join(format!("larch-logs/implement/{run}/round-{round}"));
        fs::create_dir_all(&target).unwrap();
        fs::copy(
            root.join(format!(
                "{FIXTURES}/classifications/{run}-round-{round}.tsv"
            )),
            target.join("findings-classification.tsv"),
        )
        .unwrap();
    }
}

#[test] #[rustfmt::skip]
fn recorded_corpus_is_byte_exact_and_read_only() {
    let temp = TempDir::new().unwrap(); let root = temp.path(); seed(root);
    let manifest_before = fs::read(root.join(format!("{FIXTURES}/manifest.tsv"))).unwrap();
    let class_before = fs::read(root.join("larch-logs/implement/66A96EAD-3088-4750-AE3A-64A0E11EABBD/round-2/findings-classification.tsv")).unwrap();
    let output = invoke(root, &["calibration-replay", "run-replay", "--work-dir", "work", "--dry-run"]);
    assert!(output.status.success(), "{}", String::from_utf8_lossy(&output.stdout));
    assert_eq!(output.stdout, include_bytes!("../../../fixtures/rust-calibration/replay-dry-run.golden.txt"));
    for (run, _, finding) in RUNS {
        assert_eq!(fs::read(root.join(format!("work/{run}_{finding}/ballot.txt"))).unwrap(), fs::read(root.join(format!("{FIXTURES}/ballots/{run}_{finding}.ballot.txt"))).unwrap());
    }
    assert_eq!(fs::read(root.join(format!("{FIXTURES}/manifest.tsv"))).unwrap(), manifest_before);
    assert_eq!(fs::read(root.join("larch-logs/implement/66A96EAD-3088-4750-AE3A-64A0E11EABBD/round-2/findings-classification.tsv")).unwrap(), class_before);
    let refused = invoke(root, &["calibration-replay", "run-replay", "--work-dir", "larch-logs/replay", "--dry-run"]); assert_eq!(refused.status.code(), Some(1));
    assert_eq!(refused.stdout, b"REPLAY_STATUS=failed\nERROR=replay output must stay outside synchronized run logs and committed calibration fixtures\n");
    let run_root = format!("larch-logs/implement/{}", RUNS[1].0);
    let bad_fixture = invoke(root, &["calibration-replay", "rebuild-ballot", "--finding-id", "FINDING_10", "--run-root", &run_root, "--round-num", "1", "--fixture-ballot", "../outside"]);
    assert_eq!(bad_fixture.stdout, b"REBUILD_STATUS=failed\nERROR=--fixture-ballot must be a repo-relative path\n");
    #[cfg(unix)] {
        use std::os::unix::fs::symlink;
        symlink(root.join("larch-logs"), root.join("logs-alias")).unwrap();
        let alias = invoke(root, &["calibration-replay", "run-replay", "--work-dir", "logs-alias/replay", "--dry-run"]);
        assert_eq!(alias.stdout, refused.stdout); assert!(!root.join("larch-logs/replay").exists());
        let fixture = format!("{FIXTURES}/ballots/{}_FINDING_10.ballot.txt", RUNS[1].0);
        let rebuild = invoke(root, &["calibration-replay", "rebuild-ballot", "--finding-id", "FINDING_10", "--run-root", &run_root, "--round-num", "1", "--fixture-ballot", &fixture, "--output", "logs-alias/rebuilt"]);
        assert_eq!(rebuild.stdout, b"REBUILD_STATUS=failed\nERROR=replay output must stay outside synchronized run logs and committed calibration fixtures\n"); assert!(!root.join("larch-logs/rebuilt").exists());
        let outside = TempDir::new().unwrap(); fs::create_dir_all(outside.path().join("round-1")).unwrap(); fs::write(outside.path().join("round-1/findings.md"), "### FINDING_1: outside\n").unwrap();
        let linked_id = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"; symlink(outside.path(), root.join(format!("larch-logs/implement/{linked_id}"))).unwrap(); let linked_root = format!("larch-logs/implement/{linked_id}");
        let linked = invoke(root, &["calibration-replay", "rebuild-ballot", "--finding-id", "FINDING_1", "--run-root", &linked_root, "--round-num", "1", "--output", "safe-ballot"]);
        assert!(!linked.status.success()); assert!(String::from_utf8_lossy(&linked.stdout).contains("unsafe synchronized input")); assert!(!root.join("safe-ballot").exists());
    }
}

#[test] #[rustfmt::skip]
fn snapshot_matches_golden() {
    let temp = TempDir::new().unwrap(); let root = temp.path(); assert!(Command::new("git").args(["init", "--quiet"]).current_dir(root).status().unwrap().success());
    let round = root.join("larch-logs/implement/run-a/round-1"); fs::create_dir_all(&round).unwrap();
    fs::write(round.join("findings-classification.tsv"), concat!(
        "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool\n",
        "FINDING_1\treviewer\taccepted\tYES\ttrue\tminor\tgood\tfalse\tclaude\tYES\ttrue\tmajor\tgood\tfalse\tcodex-plan-fidelity\tNO\ttrue\tnit\tgood\tfalse\tcursor-pragmatism\n"
    )).unwrap();
    let output = invoke(root, &["voter-calibration", "snapshot", "--log-root", "larch-logs", "--out", "snapshot.tsv"]);
    assert!(output.status.success(), "{}", String::from_utf8_lossy(&output.stderr));
    assert_eq!(output.stdout, b"CALIBRATION_STATS_FILE=snapshot.tsv\n");
    assert_eq!(fs::read(root.join("snapshot.tsv")).unwrap(), include_bytes!("../../../fixtures/rust-calibration/snapshot.golden.tsv"));
    let nested = root.join("nested"); fs::create_dir(&nested).unwrap(); let default_path = root.join("default-snapshot.tsv"); let default_path_text = default_path.display().to_string();
    let default = invoke(&nested, &["voter-calibration", "snapshot", "--out", &default_path_text]);
    assert!(default.status.success(), "{}", String::from_utf8_lossy(&default.stderr)); assert_eq!(fs::read(default_path).unwrap(), include_bytes!("../../../fixtures/rust-calibration/snapshot.golden.tsv"));
}

#[test]
#[rustfmt::skip]
fn malformed_manifest_messages_are_frozen() {
    let temp = TempDir::new().unwrap(); let root_buf = fs::canonicalize(temp.path()).unwrap(); let root = root_buf.as_path(); seed(root);
    let run = "3ED15A95-C722-4ABE-904C-729E1A730C5D";
    let plans = root.join(format!("{FIXTURES}/plans")); let diffs = root.join(format!("{FIXTURES}/diffs")); let ballots = root.join(format!("{FIXTURES}/ballots"));
    fs::write(plans.join("empty.plan"), " \n").unwrap(); fs::write(plans.join("pointer.plan"), "See plan.txt.\n").unwrap(); fs::write(plans.join("full.plan"), "## Goal\nship\n## Implementation Plan\ndo it\n").unwrap();
    fs::write(diffs.join("empty.diff"), "\n").unwrap(); fs::write(ballots.join("empty.ballot"), " \n").unwrap(); fs::write(ballots.join("multi.ballot"), "### FINDING_10: one\n### OOS_2: two\n").unwrap(); fs::write(ballots.join("mismatch.ballot"), "### FINDING_9: wrong\n").unwrap(); fs::write(ballots.join("tally.ballot"), "### FINDING_10: old\nVote tally: YES=1/1\n").unwrap();
    fs::write(root.join("outside.plan"), "body\n").unwrap(); fs::write(root.join("outside.diff"), "diff\n").unwrap(); fs::write(root.join("outside.ballot"), "### FINDING_10: outside\n").unwrap();
    let ballot = format!("{FIXTURES}/ballots/{run}_FINDING_10.ballot.txt"); let plan = format!("{FIXTURES}/plans/{run}_FINDING_10.plan.txt"); let diff = format!("{FIXTURES}/diffs/{run}_FINDING_10.diff");
    let row = |finding: &str, run: &str, round: &str, ballot: &str, plan: &str, diff: &str, required: &str| format!("{finding}\t{run}\t{round}\tcodex-plan-fidelity\tcursor-validity\t{ballot}\t{plan}\t{diff}\t{required}\n");
    let cases = [
        (row("", run, "1", &ballot, &plan, &diff, "true"), ("", run, "1"), "finding_id is required".into()),
        (row("FINDING_10", "", "1", &ballot, &plan, &diff, "true"), ("FINDING_10", "", "1"), "run_id and positive numeric round_num are required for FINDING_10".into()),
        (row("FINDING_10", run, "0", &ballot, &plan, &diff, "true"), ("FINDING_10", run, "0"), "run_id and positive numeric round_num are required for FINDING_10".into()),
        (row("FINDING_10", "not-a-run", "1", &ballot, &plan, &diff, "true"), ("FINDING_10", "not-a-run", "1"), "run_id must be a UUID-shaped implement run id: 'not-a-run'".into()),
        (row("FINDING_10", run, "1", &ballot, "../outside.plan", &diff, "true"), ("FINDING_10", run, "1"), "fixture_plan must be a repo-relative path".into()),
        (row("FINDING_10", run, "1", &ballot, "outside.plan", &diff, "true"), ("FINDING_10", run, "1"), format!("fixture_plan must be under {FIXTURES}/plans: {}", root.join("outside.plan").display())),
        (row("FINDING_10", run, "1", &ballot, &format!("{FIXTURES}/plans/missing"), &diff, "true"), ("FINDING_10", run, "1"), format!("fixture_plan is not readable: {}", plans.join("missing").display())),
        (row("FINDING_10", run, "1", &ballot, &format!("{FIXTURES}/plans/empty.plan"), &diff, "true"), ("FINDING_10", run, "1"), format!("fixture_plan is empty: {}", plans.join("empty.plan").display())),
        (row("FINDING_10", run, "1", &ballot, &format!("{FIXTURES}/plans/pointer.plan"), &diff, "true"), ("FINDING_10", run, "1"), format!("fixture_plan is pointer-only, not a replay fixture: {}", plans.join("pointer.plan").display())),
        (row("FINDING_10", run, "1", &ballot, &format!("{FIXTURES}/plans/full.plan"), &diff, "true"), ("FINDING_10", run, "1"), format!("fixture_plan must be an extracted Implementation Plan body, not a full plan-goals document: {}", plans.join("full.plan").display())),
        (row("FINDING_10", run, "1", &ballot, &plan, &diff, "maybe"), ("FINDING_10", run, "1"), "diff_required must be true or false".into()),
        (row("FINDING_10", run, "1", &ballot, &plan, &diff, "false"), ("FINDING_10", run, "1"), "fixture_diff must be empty when diff_required=false for FINDING_10".into()),
        (row("FINDING_10", run, "1", &ballot, &plan, "", "true"), ("FINDING_10", run, "1"), "fixture_diff is required".into()),
        (row("FINDING_10", run, "1", &ballot, &plan, &format!("{FIXTURES}/diffs/missing"), "true"), ("FINDING_10", run, "1"), "fixture_diff is required and must be readable for FINDING_10".into()),
        (row("FINDING_10", run, "1", &ballot, &plan, "outside.diff", "true"), ("FINDING_10", run, "1"), format!("fixture_diff must be under {FIXTURES}/diffs: {}", root.join("outside.diff").display())),
        (row("FINDING_10", run, "1", &ballot, &plan, &format!("{FIXTURES}/diffs/empty.diff"), "true"), ("FINDING_10", run, "1"), format!("fixture_diff is empty: {}", diffs.join("empty.diff").display())),
        (row("FINDING_10", run, "1", &format!("{FIXTURES}/ballots/missing"), &plan, &diff, "true"), ("FINDING_10", run, "1"), format!("fixture_ballot is not readable: {FIXTURES}/ballots/missing")),
        (row("FINDING_10", run, "1", "outside.ballot", &plan, &diff, "true"), ("FINDING_10", run, "1"), format!("fixture_ballot must be under {FIXTURES}/ballots: {}", root.join("outside.ballot").display())),
        (row("FINDING_10", run, "1", &format!("{FIXTURES}/ballots/tally.ballot"), &plan, &diff, "true"), ("FINDING_10", run, "1"), format!("fixture_ballot contains historical vote tally: {}", ballots.join("tally.ballot").display())),
        (row("FINDING_10", run, "1", &format!("{FIXTURES}/ballots/empty.ballot"), &plan, &diff, "true"), ("FINDING_10", run, "1"), format!("fixture_ballot is empty: {}", ballots.join("empty.ballot").display())),
        (row("FINDING_10", run, "1", &format!("{FIXTURES}/ballots/multi.ballot"), &plan, &diff, "true"), ("FINDING_10", run, "1"), format!("fixture_ballot must contain exactly one finding heading: {}", ballots.join("multi.ballot").display())),
        (row("FINDING_10", run, "1", &format!("{FIXTURES}/ballots/mismatch.ballot"), &plan, &diff, "true"), ("FINDING_10", run, "1"), format!("fixture_ballot heading 'FINDING_9' does not match finding_id 'FINDING_10': {}", ballots.join("mismatch.ballot").display())),
        (row("FINDING_10", run, "1", "", &plan, &diff, "true"), ("FINDING_10", run, "1"), format!("no ballot source found for FINDING_10 round 1 under {}", root.join(format!("larch-logs/implement/{run}")).display())),
    ];
    let header = "finding_id\trun_id\tround_num\tv2_tool\tv1_tool\tfixture_ballot\tfixture_plan\tfixture_diff\tdiff_required\n";
    for (data, key, expected) in cases {
        fs::write(root.join("manifest.tsv"), format!("{header}{data}")).unwrap();
        fs::write(root.join("cohort.tsv"), format!("finding_id\trun_id\tround_num\tv2_tool\tv1_tool\n{}\t{}\t{}\tcodex-plan-fidelity\tcursor-validity\n", key.0, key.1, key.2)).unwrap();
        let output = invoke(root, &["calibration-replay", "validate-manifest", "--manifest", "manifest.tsv", "--cohort", "cohort.tsv"]);
        assert_eq!(String::from_utf8(output.stdout).unwrap(), format!("MANIFEST_STATUS=failed\nERROR=row 2: {expected}\n"));
    }
}

#[cfg(unix)]
#[test]
#[rustfmt::skip]
fn live_replay_uses_verified_dispatch_and_shared_ledger() {
    use std::os::unix::fs::PermissionsExt as _;
    let temp = TempDir::new().unwrap(); let root_buf = fs::canonicalize(temp.path()).unwrap(); let root = root_buf.as_path(); seed(root);
    let run = "66A96EAD-3088-4750-AE3A-64A0E11EABBD"; let run_root = root.join(format!("larch-logs/implement/{run}")); fs::create_dir_all(run_root.join("round-1")).unwrap();
    fs::write(run_root.join("round-1/findings-classification.tsv"), "finding_id\tv2_vote\tv1_vote\tv3_vote\tvoting_result\tscope\nFINDING_ALPHA\tYES\tYES\tNO\taccepted\tin_scope\n").unwrap();
    fs::write(run_root.join("review-findings-full.jsonl"), "{\"id\":\"FINDING_ALPHA\",\"round_num\":\"1\",\"category\":\"Ledger parity\",\"prose_body\":\"### FINDING_ALPHA: Ledger parity\\n\\n- **Concern**: bug in python/calibration_replay.py:100\\n\"}\n").unwrap();
    for name in ["manifest", "cohort"] {
        let source = fs::read_to_string(root.join(format!("{FIXTURES}/{name}.tsv"))).unwrap();
        fs::write(root.join(format!("{name}-one.tsv")), format!("{}\n", source.lines().take(2).collect::<Vec<_>>().join("\n"))).unwrap();
    }
    let plugin = root.join("plugin"); fs::create_dir_all(plugin.join("scripts")).unwrap(); let script = plugin.join("scripts/larch.sh");
    fs::write(&script, "#!/bin/sh\n[ \"${LARCH_VOTER_CALIBRATION_FEEDBACK:-}\" = 0 ] || exit 9\nreview=\nwhile [ $# -gt 0 ]; do case $1 in --review-tmpdir) review=$2; shift 2;; *) shift;; esac; done\nprintf 'FINDING_10: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\\n' >\"$review/codex-plan-fidelity-vote-output.txt\"\nprintf 'VOTER_2_STATUS=launched\\nVOTER_2_PARSE_RATE_STATUS=OK\\nVOTER_2_TOOL=cursor-plan-fidelity\\nVOTER_2_PATH=codex-plan-fidelity-vote-output.txt\\n'\n").unwrap();
    fs::set_permissions(&script, fs::Permissions::from_mode(0o755)).unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_larch")).current_dir(root).env("CLAUDE_PLUGIN_ROOT", &plugin).args(["calibration-replay", "run-replay", "--manifest", "manifest-one.tsv", "--cohort", "cohort-one.tsv", "--work-dir", "work"]).output().unwrap();
    assert!(output.status.success(), "{}", String::from_utf8_lossy(&output.stdout)); assert!(String::from_utf8_lossy(&output.stdout).contains("ROW_1_AFTER_VOTE=YES"));
    assert_eq!(fs::read(root.join(format!("work/{run}_FINDING_10/findings-ledger.tsv"))).unwrap(), include_bytes!("../../../fixtures/rust-calibration/replay-ledger.golden.tsv"));
}
