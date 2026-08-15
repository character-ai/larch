#[rustfmt::skip]
mod tests {
#![allow(clippy::cognitive_complexity)] // Compact parity scenarios intentionally keep each frozen command transaction together.
use sha2::{Digest as _, Sha256};
use std::{fs, path::{Path, PathBuf}, process::{Command, Output}};
#[cfg(unix)] use std::os::unix::fs::{PermissionsExt, symlink};
use tempfile::TempDir;

fn fixture(name: &str) -> PathBuf { Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/plan_review").join(name) }
fn strings(values: &[&str]) -> Vec<String> { values.iter().map(|value| (*value).to_owned()).collect() }
fn run(root: &Path, verb: &str, extra: &[String]) -> Output {
    let mut arguments = strings(&["plan-review", verb, "--design-tmpdir"]);
    arguments.push(root.display().to_string()); arguments.extend_from_slice(extra);
    Command::new(env!("CARGO_BIN_EXE_larch")).args(arguments).env("LARCH_QUIET_DISABLE", "1").output().expect("run larch")
}
fn stdout(output: &Output) -> String { String::from_utf8_lossy(&output.stdout).into_owned() }
fn stderr(output: &Output) -> String { String::from_utf8_lossy(&output.stderr).into_owned() }
fn text(path: impl AsRef<Path>) -> String { fs::read_to_string(path).expect("read fixture artifact") }

#[test]
fn argparse_help_bytes_match_the_retired_owners() {
    let sandbox = TempDir::new().expect("sandbox");
    for (verb, expected) in [
        ("emit", "usage: cli.py plan-review emit [-h] --design-tmpdir DESIGN_TMPDIR\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n"),
        ("emit-rejected", "usage: cli.py plan-review emit-rejected [-h] --design-tmpdir DESIGN_TMPDIR\n                                        [--report-framing]\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --report-framing\n"),
        ("gate-b-counts", "usage: cli.py plan-review gate-b-counts [-h] --design-tmpdir DESIGN_TMPDIR\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n"),
        ("gate-b-finding-line", "usage: cli.py plan-review gate-b-finding-line [-h] --design-tmpdir\n                                              DESIGN_TMPDIR --finding-id\n                                              FINDING_ID [--ordinal ORDINAL]\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --finding-id FINDING_ID\n  --ordinal ORDINAL\n"),
        ("gate-b-dedup", "usage: cli.py plan-review gate-b-dedup [-h] --design-tmpdir DESIGN_TMPDIR\n                                       [--snapshot-trailers] [--dedup]\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --snapshot-trailers\n  --dedup\n"),
        ("snapshot-pre-review", "usage: cli.py [-h] --design-tmpdir DESIGN_TMPDIR\n\nSnapshot plan.txt before a /design Step 3 review entry\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n"),
        ("filter-gate-b-skipped", "usage: cli.py [-h] --design-tmpdir DESIGN_TMPDIR --accepted ACCEPTED\n              --rejected REJECTED\n\nFilter Gate B one-by-one skipped findings from accepted findings\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --accepted ACCEPTED\n  --rejected REJECTED\n"),
        ("persist-accepted-audit", "usage: cli.py [-h] --design-tmpdir DESIGN_TMPDIR\n              (--assessment {clean} | --assessment-file ASSESSMENT_FILE)\n\nPersist the Gate C accepted-findings audit\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --assessment {clean}\n  --assessment-file ASSESSMENT_FILE\n"),
    ] { let result = run(sandbox.path(), verb, &strings(&["--help"])); assert!(result.status.success()); assert_eq!(stdout(&result), expected); assert!(stderr(&result).is_empty()); }
    let before = run(sandbox.path(), "gate-b-finding-line", &strings(&["--finding-id", "abc", "--help"])); assert_eq!(before.status.code(), Some(2)); assert!(stdout(&before).is_empty());
    let after = run(sandbox.path(), "gate-b-finding-line", &strings(&["--help", "--finding-id", "abc"])); assert!(after.status.success()); assert!(stderr(&after).is_empty());
    let conflict = run(sandbox.path(), "persist-accepted-audit", &strings(&["--assessment", "clean", "--assessment-file", "x", "--help"])); assert_eq!(conflict.status.code(), Some(2)); assert!(stdout(&conflict).is_empty());
}

#[test]
fn recorded_tally_round_matches_python_golden_bytes() {
    let sandbox = TempDir::new().expect("sandbox"); let design = sandbox.path().join("design"); fs::create_dir(&design).expect("design directory");
    let mut options = vec!["--ballot-file".into(), fixture("ballot.md").display().to_string()];
    for (slot, name) in [(1, "voter-1.txt"), (2, "voter-2.txt"), (3, "voter-3.txt")] {
        options.extend(["--voter".into(), format!("{slot}:codex-{}:{}", ["validity", "plan-fidelity", "pragmatism"][slot - 1], fixture(name).display())]);
    }
    let result = run(&design, "tally", &options); assert!(result.status.success(), "{}", String::from_utf8_lossy(&result.stderr));
    assert_eq!(stdout(&result), format!("TALLY_PLAN_REVIEW_STATUS=ok\nVOTING_TALLY_FILE={}\n", design.join("voting-tally.md").display()));
    for (actual, golden) in [
        (design.join("voting-tally.md"), "voting-tally.golden.md"),
        (design.join("plan-review/round-1/findings-classification.tsv"), "findings-classification.golden.tsv"),
        (design.join("findings-ledger.tsv"), "findings-ledger.golden.tsv"),
    ] { assert_eq!(fs::read(actual).expect("actual bytes"), fs::read(fixture(golden)).expect("golden bytes")); }
    for (name, needle) in [("accepted-plan-findings.md", "Parser contract"), ("rejected-findings.md", "Naming cleanup"), ("oos-accepted-design.md", "Follow-up docs")] {
        assert!(text(design.join(name)).contains(needle));
    }
    assert!(run(&design, "tally", &options).status.success());
    assert_eq!(text(design.join("accepted-plan-findings-all.md")).matches("### FINDING_1:").count(), 1);
    assert_eq!(text(design.join("oos-accepted-design.md")).matches("### OOS_1:").count(), 1);
    let bonus_design = sandbox.path().join("bonus"); fs::create_dir(&bonus_design).expect("bonus design"); let bonus = Command::new(env!("CARGO_BIN_EXE_larch")).args(["plan-review", "tally", "--design-tmpdir"]).arg(&bonus_design).args(&options).env("LARCH_QUIET_DISABLE", "1").env("LARCH_UNIQUE_FINDER_BONUS", "1_0").output().expect("bonus tally"); assert!(bonus.status.success()); let bonus_tally = text(bonus_design.join("voting-tally.md")); assert!(bonus_tally.contains("| Codex-Correctness | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 12 |")); assert!(bonus_tally.contains("received +10 each"));
}

#[test]
fn gate_b_lines_and_dedup_wire_are_frozen() {
    let sandbox = TempDir::new().expect("sandbox"); fs::copy(fixture("accepted.md"), sandbox.path().join("accepted-plan-findings.md")).expect("accepted");
    assert_eq!(stdout(&run(sandbox.path(), "gate-b-counts", &[])), "ACCEPTED_COUNT=2\nHIGH_ACCEPTED_COUNT=1\nMEDIUM_ACCEPTED_COUNT=0\nLOW_ACCEPTED_COUNT=1\nCRITICAL_ACCEPTED_COUNT=0\nGATE_B_SEVERITY_MODE=structured\nFINDING_IDS=4,9\n");
    assert_eq!(stdout(&run(sandbox.path(), "gate-b-finding-line", &strings(&["--finding-id", "9"]))), "FINDING_ID=9\nDISPLAY_SEVERITY=Low\nREVIEWER_TEXT=Cursor-Quality\nCONCERN_EXCERPT=Naming style only.\nONE_BY_ONE_ORDINAL=2\nONE_BY_ONE_TOTAL=2\nONE_BY_ONE_HEADER=Finding 2/2\nONE_BY_ONE_PROMPT_LINE=FINDING_9 [Low] — Cursor-Quality: Naming style only.. Apply this finding to the plan?\n");
    let invalid = run(sandbox.path(), "gate-b-finding-line", &strings(&["--finding-id", "0"])); assert_eq!(invalid.status.code(), Some(2)); assert!(stderr(&invalid).contains("argument --finding-id: requires a non-empty positive integer")); assert!(!stderr(&invalid).contains(": '0'"));
    let huge = run(sandbox.path(), "gate-b-finding-line", &strings(&["--finding-id", "18446744073709551616"])); assert_eq!(huge.status.code(), Some(1)); assert!(stderr(&huge).contains("unknown finding id FINDING_18446744073709551616"));
    for options in [strings(&["--finding-id", "abc", "--finding-id", "4"]), strings(&["--finding-id", "4", "--ordinal", "abc", "--ordinal", "1"])] { assert_eq!(run(sandbox.path(), "gate-b-finding-line", &options).status.code(), Some(2)); }
    assert_eq!(stdout(&run(sandbox.path(), "gate-b-counts", &strings(&["--preview"]))), "## Plan Review Findings: Review\n\nFINDING_4 | High | Codex-Correctness, Cursor-Architecture | Primary code path has functional incorrectness.\nFINDING_9 | Low | Cursor-Quality | Naming style only.\n");
    fs::write(sandbox.path().join("accepted-plan-findings.md"), "### FINDING_1: Unicode lines\n- **Severity**: major\n- **Reviewer**: Codex\n- **Concern**: first\u{2028}second\u{1f}\n").expect("unicode concern"); let unicode = stdout(&run(sandbox.path(), "gate-b-finding-line", &strings(&["--finding-id", "1"]))); assert!(unicode.contains("CONCERN_EXCERPT=first second\n")); assert!(!unicode.contains('\u{2028}') && !unicode.contains('\u{1f}'));
    fs::write(sandbox.path().join("accepted-plan-findings.md"), "### FINDING_18446744073709551616: Large\n- **Severity**: major\n- **Reviewer**: Codex\n- **Concern**: Primary code path fails.\n").expect("large accepted id");
    assert_eq!(stdout(&run(sandbox.path(), "gate-b-counts", &[])), "ACCEPTED_COUNT=1\nHIGH_ACCEPTED_COUNT=1\nMEDIUM_ACCEPTED_COUNT=0\nLOW_ACCEPTED_COUNT=0\nCRITICAL_ACCEPTED_COUNT=0\nGATE_B_SEVERITY_MODE=structured\nFINDING_IDS=18446744073709551616\n");
    fs::write(sandbox.path().join("accepted-plan-findings.md"), "### FINDING_000: Zero\n- \u{1f}**Severity**: major\n- \u{1f}**Reviewer**: Codex\n- \u{1f}**Concern**: Primary code path fails.\n").expect("zero accepted id");
    assert_eq!(stdout(&run(sandbox.path(), "gate-b-counts", &[])), "ACCEPTED_COUNT=1\nHIGH_ACCEPTED_COUNT=1\nMEDIUM_ACCEPTED_COUNT=0\nLOW_ACCEPTED_COUNT=0\nCRITICAL_ACCEPTED_COUNT=0\nGATE_B_SEVERITY_MODE=structured\nFINDING_IDS=0\n");
    fs::write(sandbox.path().join("plan.txt"), "body\nbody\ndiff_added:\u{1f}10\u{1f}\ndiff_lines: 20\n").expect("plan");
    assert_eq!(stdout(&run(sandbox.path(), "gate-b-dedup", &strings(&["--snapshot-trailers"]))), "GATE_B_DEDUP_STATUS=snapshot-ok\n");
    assert_eq!(text(sandbox.path().join(".gate-b-optional-trailer-keys.values")), "diff_added=10\n");
    assert_eq!(stdout(&run(sandbox.path(), "gate-b-dedup", &strings(&["--dedup"]))), "dedup-sweep: removed 1 duplicate line(s) from plan.txt\nGATE_B_DEDUP_STATUS=ok\n");
    assert_eq!(text(sandbox.path().join("plan.txt")), "body\ndiff_added:\u{1f}10\u{1f}\ndiff_lines: 20\n");
    fs::write(sandbox.path().join("plan.txt"), "body\u{2028}body\ndiff_lines: 1\n").expect("unicode lines"); assert!(run(sandbox.path(), "gate-b-dedup", &strings(&["--snapshot-trailers"])).status.success()); assert_eq!(stdout(&run(sandbox.path(), "gate-b-dedup", &strings(&["--dedup"]))), "dedup-sweep: removed 1 duplicate line(s) from plan.txt\nGATE_B_DEDUP_STATUS=ok\n"); assert_eq!(text(sandbox.path().join("plan.txt")), "body\ndiff_lines: 1\n");
    let loose = "## Plan\noversize_override: operator\nbody\ndiff_lines: 1\n"; fs::write(sandbox.path().join("plan.txt"), loose).expect("loose override"); fs::write(sandbox.path().join(".gate-b-oversize-override.sha256"), format!("{:x}\n", Sha256::digest(loose.as_bytes()))).expect("authority"); assert!(run(sandbox.path(), "gate-b-dedup", &strings(&["--snapshot-trailers"])).status.success()); assert!(run(sandbox.path(), "gate-b-dedup", &strings(&["--dedup"])).status.success()); assert!(!sandbox.path().join(".gate-b-oversize-override.sha256").exists());
    fs::create_dir(sandbox.path().join(".gate-b-oversize-override.sha256")).expect("authority directory");
    let failed = run(sandbox.path(), "gate-b-dedup", &strings(&["--dedup"])); assert_eq!(failed.status.code(), Some(1)); assert!(stdout(&failed).is_empty());
}

#[test]
fn accepted_audit_round_trip_and_filter_are_exact() {
    let sandbox = TempDir::new().expect("sandbox"); fs::write(sandbox.path().join("plan.txt"), "initial\r\nplan\r\n").expect("plan");
    assert!(run(sandbox.path(), "snapshot-pre-review", &[]).status.success()); assert_eq!(text(sandbox.path().join("plan-before-review.txt")), "initial\nplan\n");
    let accepted = sandbox.path().join("accepted.md"); let rejected = sandbox.path().join("rejected.md");
    fs::write(&accepted, "### FINDING_1: Keep\n- **Concern**: keep\u{1c}\n\n### FINDING_2: Skip\n- **Concern**: skip\n\n").expect("accepted");
    fs::write(&rejected, "### FINDING_2: Skip\n- **Concern**: skip\n- **Reason**: rejected by user during one-by-one review\n\n").expect("rejected");
    let filter_options = vec!["--accepted".into(), accepted.display().to_string(), "--rejected".into(), rejected.display().to_string()];
    assert_eq!(stdout(&run(sandbox.path(), "filter-gate-b-skipped", &filter_options)), "### FINDING_1: Keep\n- **Concern**: keep\n\n");
    let sidecar = sandbox.path().join("assessment.sidecar"); fs::write(&sidecar, "mild-disagree:\r\nnote").expect("sidecar");
    let conflicting = run(sandbox.path(), "persist-accepted-audit", &["--assessment".into(), "clean".into(), "--assessment-file".into(), sidecar.display().to_string()]); assert_eq!(conflicting.status.code(), Some(2)); assert!(stderr(&conflicting).contains("argument --assessment-file: not allowed with argument --assessment"));
    for options in [vec!["--assessment".into(), "bad".into(), "--assessment".into(), "clean".into()], vec!["--assessment=".into()], vec!["--assessment=clean".into(), format!("--assessment-file={}", sidecar.display())]] { assert_eq!(run(sandbox.path(), "persist-accepted-audit", &options).status.code(), Some(2)); }
    assert_eq!(stdout(&run(sandbox.path(), "persist-accepted-audit", &["--assessment-file".into(), sidecar.display().to_string()])), "ACCEPTED_AUDIT_STATUS=ok\n");
    assert_eq!(text(sandbox.path().join("accepted-plan-findings-audit.md")), "mild-disagree:\nnote\n");
    fs::write(&sidecar, "\u{1c}note\u{1c}").expect("Python whitespace"); assert!(run(sandbox.path(), "persist-accepted-audit", &["--assessment-file".into(), sidecar.display().to_string()]).status.success()); assert_eq!(text(sandbox.path().join("accepted-plan-findings-audit.md")), "note\n");
}

#[test]
fn degraded_tally_modes_preserve_the_frozen_contract() {
    for (voter, status, tier) in [(None, "main-agent-vote-required", "main-agent-required"), (Some("voter-1.txt"), "ok", "main-agent-adjudicated")] {
        let sandbox = TempDir::new().expect("sandbox"); let design = sandbox.path().join("design"); fs::create_dir(&design).expect("design");
        let mut options = vec!["--ballot-file".into(), fixture("ballot.md").display().to_string()];
        if let Some(name) = voter { options.extend(["--voter".into(), format!("MainAgent:{}", fixture(name).display())]); }
        let result = run(&design, "tally", &options); assert!(result.status.success(), "{}", String::from_utf8_lossy(&result.stderr));
        assert!(stdout(&result).contains(&format!("TALLY_PLAN_REVIEW_STATUS={status}\n"))); assert!(text(design.join("voting-tally.md")).contains(&format!("Panel tier: {tier}.")));
        let classification = text(design.join("plan-review/round-1/findings-classification.tsv"));
        assert_eq!(classification.lines().count(), 4); assert!(classification.lines().skip(1).all(|line| line.contains("\trejected\t")));
        assert_eq!(design.join("findings-ledger.tsv").exists(), voter.is_some());
    }
    let sandbox = TempDir::new().expect("sandbox"); let design = sandbox.path().join("design"); fs::create_dir(&design).expect("design");
    let invalid = run(&design, "tally", &["--ballot-file".into(), fixture("ballot.md").display().to_string(), "--voter".into(), "1:".into()]); assert_eq!(invalid.status.code(), Some(2)); assert!(stdout(&invalid).ends_with("TALLY_PLAN_REVIEW_STATUS=tally-error\n")); assert!(stderr(&invalid).contains("voter file is missing or unreadable:")); assert!(text(design.join("voting-tally.md")).contains("voter file unreadable: ; no votes tallied"));
    let empty_tool = run(&design, "tally", &["--ballot-file".into(), fixture("ballot.md").display().to_string(), "--voter".into(), format!("1::{}", fixture("voter-1.txt").display())]); assert_eq!(empty_tool.status.code(), Some(2)); assert!(stderr(&empty_tool).contains("voter file is missing or unreadable: :"));
    let sandbox = TempDir::new().expect("sandbox"); let design = sandbox.path().join("design"); fs::create_dir(&design).expect("design"); let conflict = run(&design, "tally", &["--ballot-file".into(), design.join("missing-ballot.md").display().to_string(), "--voter".into(), "1:missing".into(), "--voter-files".into(), String::new()]); assert_eq!(conflict.status.code(), Some(2)); assert!(stderr(&conflict).contains("--voter and --voter-files are mutually exclusive")); assert!(!stderr(&conflict).contains("ballot file is missing")); assert!(design.join("voting-tally.md").is_file()); assert!(!design.join("plan-review/round-1/findings-classification.tsv").exists());
    let ballot = design.join("whitespace-ballot.md"); fs::write(&ballot, "### FINDING_1: Whitespace\n- **Reviewer**: Codex\n\u{1f}- **Severity**: major\n- **Concern**: Primary path.\n").expect("whitespace ballot"); let whitespace = run(&design, "tally", &["--ballot-file".into(), ballot.display().to_string()]); assert!(whitespace.status.success()); let classification = text(design.join("plan-review/round-1/findings-classification.tsv")); assert!(classification.contains("\tmajor\tin_scope\n"), "{classification:?}");
    let sandbox = TempDir::new().expect("sandbox"); let design = sandbox.path().join("design"); fs::create_dir(&design).expect("design"); fs::create_dir(design.join("voting-tally.md")).expect("tally directory"); let write_failure = run(&design, "tally", &["--ballot-file".into(), fixture("ballot.md").display().to_string(), "--voter".into(), "1:missing".into()]); assert_eq!(write_failure.status.code(), Some(2)); assert!(stdout(&write_failure).contains("VOTING_TALLY_FILE=")); assert!(stderr(&write_failure).contains("tally-plan-review: unexpected error: [Errno 21] Is a directory:")); assert!(!design.join("plan-review/round-1/findings-classification.tsv").exists());
    let sandbox = TempDir::new().expect("sandbox"); let design = sandbox.path().join("design"); fs::create_dir(&design).expect("design");
    let ballot = design.join("large-ballot.md"); let voter = design.join("large-voter.txt"); fs::write(&ballot, "### FINDING_18446744073709551616: Large\n- **Reviewer**: Codex\n- **Severity**: major\n- **Concern**: Primary path.\n\n### FINDING_1: Small\n- **Reviewer**: Cursor\n- **Severity**: major\n- **Concern**: Primary path.\n").expect("large ballot"); fs::write(&voter, "FINDING_1: YES\nFINDING_18446744073709551616: YES\n").expect("large voter");
    let ordered = run(&design, "tally", &["--ballot-file".into(), ballot.display().to_string(), "--voter".into(), format!("1:{}", voter.display())]); assert!(ordered.status.success(), "{}", stderr(&ordered)); let tally = text(design.join("voting-tally.md")); assert!(tally.find("| FINDING_1 |").expect("small row") < tally.find("| FINDING_18446744073709551616 |").expect("large row"));
    let sandbox = TempDir::new().expect("sandbox"); let design = sandbox.path().join("design"); fs::create_dir(&design).expect("design"); let ballot = design.join("labels-ballot.md"); let first = design.join("first.txt"); let second = design.join("second.txt"); fs::write(&ballot, "### FINDING_1: Labels\n- **Reviewer**: codex-validity codex-plan-fidelity\n- **Severity**: major\n- **Concern**: Primary path.\n").expect("labels ballot"); fs::write(&first, "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n").expect("first vote"); fs::write(&second, "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n").expect("second vote");
    assert!(run(&design, "tally", &["--ballot-file".into(), ballot.display().to_string(), "--voter".into(), format!("1:codex-validity:{}", first.display()), "--voter".into(), format!("2:codex-plan-fidelity:{}", second.display())]).status.success()); let tally = text(design.join("voting-tally.md")); assert!(tally.contains("| codex-validity | 1 | 1 |")); assert!(tally.contains("| codex-plan-fidelity | 1 | 1 |")); assert!(!tally.contains("| codex-validity codex-plan-fidelity |"));
}

#[test]
fn neutral_proposer_map_validation_preserves_failure_side_effects() {
    let sandbox = TempDir::new().expect("sandbox"); let missing_design = sandbox.path().join("missing"); fs::create_dir(&missing_design).expect("missing design"); let missing_ballot = missing_design.join("ballot.md"); let ballot_text = "### FINDING_1: Neutral\n\u{1f}- **Reviewer**: Anonymous\n- **Severity**: major\n- **Concern**: Primary path.\n"; fs::write(&missing_ballot, ballot_text).expect("missing ballot"); let missing = run(&missing_design, "tally", &["--ballot-file".into(), missing_ballot.display().to_string(), "--voter".into(), format!("1:{}", fixture("voter-1.txt").display())]); assert_eq!(missing.status.code(), Some(2)); assert!(stderr(&missing).contains("missing proposer map entry for neutralized item FINDING_1")); assert!(stdout(&missing).contains("VOTING_TALLY_FILE=")); assert!(missing_design.join("voting-tally.md").is_file()); assert!(missing_design.join("plan-review/round-1/findings-classification.tsv").is_file());
    let design = sandbox.path().join("design"); fs::create_dir(&design).expect("design"); let ballot = design.join("ballot.md"); let map = design.join("proposer-map.tsv"); fs::write(&ballot, ballot_text).expect("ballot"); let hash = format!("{:x}", Sha256::digest(ballot_text.as_bytes()));
    let options = || vec!["--ballot-file".into(), ballot.display().to_string(), "--proposer-map-file".into(), map.display().to_string(), "--voter".into(), format!("1:{}", fixture("voter-1.txt").display())];
    fs::write(&map, "# neutral_ballot_sha256=stale\nFINDING_1\tCodex\t- **Reviewer**: Codex\n").expect("stale map"); let mut stale_options = options(); stale_options.extend(["--voter-files".into(), fixture("voter-2.txt").display().to_string()]); let stale = run(&design, "tally", &stale_options); assert_eq!(stale.status.code(), Some(2)); assert_eq!(stdout(&stale), "TALLY_PLAN_REVIEW_STATUS=tally-error\n"); assert!(stderr(&stale).contains("proposer map stale for current ballot\ntally-plan-review: unexpected error:")); assert!(!design.join("voting-tally.md").exists()); assert!(!design.join("plan-review/round-1/findings-classification.tsv").exists());
    fs::write(&map, format!("# neutral_ballot_sha256={hash}\nFINDING_1\t**anonymous**\t- **Reviewer**: Codex\n")).expect("anonymous map"); assert_eq!(run(&design, "tally", &options()).status.code(), Some(2));
    fs::write(&map, format!("# neutral_ballot_sha256={hash}\nFINDING_1\tCodex\t- **Reviewer**: Codex\nFINDING_\tCursor\t- **Reviewer**: Cursor\n")).expect("valid map"); assert!(run(&design, "tally", &options()).status.success()); assert!(text(design.join("accepted-plan-findings.md")).contains("FINDING_1"));
}

#[cfg(unix)]
#[test]
fn classification_output_rejects_a_symlinked_parent() {
    let sandbox = TempDir::new().expect("sandbox"); let design = sandbox.path().join("design"); let escape = sandbox.path().join("escape"); fs::create_dir(&design).expect("design"); fs::create_dir(&escape).expect("escape"); symlink(&escape, design.join("plan-review")).expect("parent symlink");
    let result = run(&design, "tally", &["--ballot-file".into(), fixture("ballot.md").display().to_string()]); assert_eq!(result.status.code(), Some(2)); assert!(!escape.join("round-1/findings-classification.tsv").exists());
}

#[test]
fn emit_and_rejected_findings_bytes_are_frozen() {
    let sandbox = TempDir::new().expect("sandbox"); fs::write(sandbox.path().join("plan.txt"), "# Plan\n\ndiff_lines: 42\n").expect("plan");
    assert_eq!(stdout(&run(sandbox.path(), "emit", &[])), "EMIT_PLAN_STATUS=ok\nDIFF_LINES=42\n"); assert_eq!(text(sandbox.path().join("diff-lines.txt")), "42\n");
    fs::write(sandbox.path().join("plan.txt"), "body\ndiff_lines: 18446744073709551616\n").expect("large diff lines"); assert_eq!(stdout(&run(sandbox.path(), "emit", &[])), "EMIT_PLAN_STATUS=ok\nDIFF_LINES=18446744073709551616\n"); assert_eq!(text(sandbox.path().join("diff-lines.txt")), "18446744073709551616\n");
    let tagged = "### FINDING_1: Covered\n- **Concern**: [ALREADY_ADDRESSED] already covered\n\n"; let fresh = "### FINDING_2: Fresh\n- **Concern**: still open\n\n";
    fs::write(sandbox.path().join("rejected-findings.md"), format!("{tagged}{fresh}")).expect("rejected");
    assert_eq!(stdout(&run(sandbox.path(), "emit-rejected", &[])), fresh); assert_eq!(text(sandbox.path().join("rejected-findings.md")), format!("{tagged}{fresh}"));
    let covered = tagged.replace("[ALREADY_ADDRESSED] ", ""); fs::write(sandbox.path().join("rejected-findings.md"), &covered).expect("covered rejected"); fs::write(sandbox.path().join(".step3-already-addressed-finding-keys.tsv"), "\u{1f}already covered\u{1f}\n").expect("covered ledger"); assert!(stdout(&run(sandbox.path(), "emit-rejected", &[])).is_empty());
    fs::write(sandbox.path().join("rejected-findings.md"), fresh).expect("fresh rejected");
    assert_eq!(stdout(&run(sandbox.path(), "emit-rejected", &strings(&["--report-framing"]))), format!("## Considered Plan Review Suggestions (Not Adopted)\n\nThese reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.\n\n{fresh}"));
    #[cfg(unix)] {
        let path = sandbox.path().join("rejected-findings.md"); let mut permissions = fs::metadata(&path).expect("metadata").permissions(); permissions.set_mode(0o000); fs::set_permissions(&path, permissions).expect("make unreadable");
        let unreadable = run(sandbox.path(), "emit-rejected", &[]); let mut permissions = fs::metadata(&path).expect("metadata").permissions(); permissions.set_mode(0o600); fs::set_permissions(&path, permissions).expect("restore permissions");
        assert_eq!(unreadable.status.code(), Some(1)); assert!(stdout(&unreadable).is_empty());
    }
}
}
