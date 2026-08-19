//! End-to-end coverage for the three migrated `scout` verbs (#8582).
//!
//! The retired Python owner reached Cursor and Claude through
//! `scripts/larch.sh`, so every tier here is replaced by an executable shell
//! fixture named through the same environment overrides the owner honored. That
//! keeps the real staging, prompt, salvage, and wire plumbing under test without
//! contacting a vendor service.
//!
//! Test names carry the `plan_wrapper_` or `dynamic_` prefix the two
//! `test-scout-*` harness targets slice on, mirroring the retired
//! `-k plan_wrapper` / `-k 'not plan_wrapper'` split.

#![cfg(unix)]

use std::{fs, os::unix::fs::PermissionsExt as _, path::Path};

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

const ROLE_DYNAMIC: &str = "review.dynamic_archetype_scout";
const ROLE_PLAN: &str = "design.plan_archetype_scout";
const EMPTY_MANIFEST: &str = "{\"archetypes\":[]}\n";

fn scout(root: &Path) -> AssertCommand {
    let mut command = AssertCommand::cargo_bin("larch").expect("larch binary should build");
    command.current_dir(root);
    command.env_remove("CLAUDE_PLUGIN_ROOT");
    command.env_remove("SESSION_ENV_PATH");
    command
}

/// This clone, which the plan wrapper needs to reach `plan scope-paths`.
///
/// The wrapper derives its scope list through the verified `scripts/larch.sh`
/// bootstrap exactly as the retired owner did, so that one sibling is real.
fn plugin_root() -> &'static Path {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(Path::parent)
        .expect("crates/larch-cli sits two levels below the clone root")
}

/// A plan wrapper invocation whose verified bootstrap resolves to this clone.
///
/// A dev clone ships no installed `bin/larch`, so the bootstrap needs the
/// built binary named explicitly, exactly as the `test-*` harness targets do.
fn plan_wrapper(root: &Path) -> AssertCommand {
    let mut command = scout(root);
    command.env("CLAUDE_PLUGIN_ROOT", plugin_root());
    command.env(
        "LARCH_BINARY",
        assert_cmd::cargo::cargo_bin("larch").as_os_str(),
    );
    command
}

/// Publish an executable shell fixture standing in for one launcher tier.
fn launcher(root: &Path, name: &str, body: &str) -> String {
    let path = root.join(name);
    fs::write(&path, body).expect("write launcher fixture");
    fs::set_permissions(&path, fs::Permissions::from_mode(0o755)).expect("launcher permissions");
    path.display().to_string()
}

/// One archetype row the shared validator accepts.
fn row(name: &str, focus: &str) -> String {
    format!(
        "{{\"name\":\"{name}\",\"focus_area\":\"{focus}\",\"weight\":2,\"rationale\":\"Worth a slot.\",\"prompt_body\":\"Inspect the seams.\"}}"
    )
}

fn manifest(rows: &[String]) -> String {
    format!("{{\"archetypes\":[{}]}}", rows.join(","))
}

fn read(path: &Path) -> String {
    fs::read_to_string(path).unwrap_or_default()
}

#[test]
fn plan_wrapper_filter_manifest_honors_each_panel_mode() {
    let root = TempDir::new().expect("temp");
    let source = root.path().join("src.json");
    let output = root.path().join("out.json");
    fs::write(
        &source,
        manifest(&[
            row("arch", "risk-integration"),
            row("deep-risk", "risk-integration"),
        ]),
    )
    .expect("source");

    // `arch` is reserved for the static plan-review panel only, so the two
    // modes keep different survivors from the same input.
    let review = scout(root.path())
        .args([
            "scout",
            "filter-manifest",
            source.to_str().expect("utf8"),
            output.to_str().expect("utf8"),
            "--mode",
            "review",
            "--max-archetypes",
            "1",
        ])
        .assert()
        .success();
    let review_stdout = String::from_utf8_lossy(&review.get_output().stdout).into_owned();
    assert!(review_stdout.contains("SCOUT_STATUS=ok"));
    assert!(review_stdout.contains("SCOUT_ARCHETYPE_COUNT=1"));
    assert!(review_stdout.contains(&format!("SCOUT_MANIFEST={}", output.display())));
    assert!(read(&output).contains("\"name\":\"arch\""));

    let plan = scout(root.path())
        .args([
            "scout",
            "filter-manifest",
            source.to_str().expect("utf8"),
            output.to_str().expect("utf8"),
            "--mode",
            "plan-review",
            "--max-archetypes",
            "1",
        ])
        .assert()
        .success();
    let plan_stdout = String::from_utf8_lossy(&plan.get_output().stdout).into_owned();
    assert!(plan_stdout.contains("WARN=reserved archetype name: arch"));
    assert!(read(&output).contains("\"name\":\"deep-risk\""));
}

#[test]
fn plan_wrapper_filter_manifest_refuses_a_malformed_command_line() {
    let root = TempDir::new().expect("temp");
    let source = root.path().join("src.json");
    let output = root.path().join("out.json");
    fs::write(&source, manifest(&[])).expect("source");

    // The retired parser declared no help action, so `--help` reads as an
    // unrecognized optional and the missing positionals refuse first.
    let help = scout(root.path())
        .args(["scout", "filter-manifest", "--help"])
        .assert()
        .code(2);
    let help_stderr = String::from_utf8_lossy(&help.get_output().stderr).into_owned();
    assert!(help_stderr.contains("the following arguments are required: input, output"));
    assert!(help_stderr.contains("scout filter-manifest: 2"));

    for (arguments, expected) in [
        (["--max-archetypes", "2"], "--max-archetypes must be 0-1"),
        (
            ["--mode", "sideways"],
            "--mode must be review or plan-review",
        ),
    ] {
        let refusal = scout(root.path())
            .args(["scout", "filter-manifest"])
            .args([
                source.to_str().expect("utf8"),
                output.to_str().expect("utf8"),
            ])
            .args(arguments)
            .assert()
            .code(2);
        assert!(
            String::from_utf8_lossy(&refusal.get_output().stderr).contains(expected),
            "expected {expected} for {arguments:?}"
        );
    }

    // An unparseable manifest still publishes the empty wire document.
    fs::write(&source, "not json").expect("malformed source");
    let broken = scout(root.path())
        .args([
            "scout",
            "filter-manifest",
            source.to_str().expect("utf8"),
            output.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    assert!(
        String::from_utf8_lossy(&broken.get_output().stdout).contains("SCOUT_STATUS=parse-failed")
    );
    assert_eq!(read(&output), EMPTY_MANIFEST);
}

#[test]
fn plan_wrapper_forwards_its_role_id_and_filters_the_inner_manifest() {
    let root = TempDir::new().expect("temp");
    let plan = root.path().join("plan.txt");
    let description = root.path().join("feature-description.txt");
    let output = root.path().join("plan-scout.json");
    fs::write(&plan, "### NEW: a.rs\nwork\n").expect("plan");
    fs::write(&description, "feature\n").expect("description");

    // The inner scout writes two rows; only the cap-limited survivor may
    // reach the published manifest.
    let record = root.path().join("inner-argv.txt");
    let inner = launcher(
        root.path(),
        "inner-scout.sh",
        &format!(
            "#!/usr/bin/env bash\nprintf '%s\\n' \"$@\" >{}\nwhile [[ $# -gt 0 ]]; do if [[ $1 == --output ]]; then out=$2; shift 2; else shift; fi; done\nprintf '%s' '{}' >\"$out\"\nprintf 'SCOUT_STATUS=ok\\n'\n",
            record.display(),
            manifest(&[
                row("deep-risk", "risk-integration"),
                row("second-risk", "correctness"),
            ])
        ),
    );

    let assertion = plan_wrapper(root.path())
        .env("SCOUT_PLAN_ARCHETYPES_SCOUT_SH", &inner)
        .args([
            "scout",
            "plan-archetypes",
            "--role-id",
            ROLE_PLAN,
            "--plan-file",
            plan.to_str().expect("utf8"),
            "--description-file",
            description.to_str().expect("utf8"),
            "--output",
            output.to_str().expect("utf8"),
            "--session-env-path",
            "",
        ])
        .assert()
        .success();

    let argv = read(&record);
    assert!(
        argv.contains(ROLE_PLAN),
        "the wrapper must forward its own role id: {argv}"
    );
    assert!(argv.contains("--mode\ndescription"));
    let stdout = String::from_utf8_lossy(&assertion.get_output().stdout).into_owned();
    assert!(stdout.contains("SCOUT_STATUS=ok"));
    assert!(stdout.contains("SCOUT_ARCHETYPE_COUNT=1"));
    assert!(stdout.contains(&format!("SCOUT_MANIFEST={}", output.display())));
    assert!(read(&output).contains("deep-risk"));
    assert!(!read(&output).contains("second-risk"));
}

#[test]
fn plan_wrapper_reports_a_failed_inner_scout_and_a_missing_manifest() {
    let root = TempDir::new().expect("temp");
    let plan = root.path().join("plan.txt");
    let description = root.path().join("feature-description.txt");
    fs::write(&plan, "### NEW: a.rs\nwork\n").expect("plan");
    fs::write(&description, "feature\n").expect("description");

    let failing = launcher(
        root.path(),
        "failing-scout.sh",
        "#!/usr/bin/env bash\nprintf 'SCOUT_STATUS=validation-failed\\n'\nexit 1\n",
    );
    let silent = launcher(
        root.path(),
        "silent-scout.sh",
        "#!/usr/bin/env bash\nprintf 'SCOUT_STATUS=ok\\n'\n",
    );

    for (inner, expected, name) in [
        (&failing, "SCOUT_STATUS=validation-failed", "failed.json"),
        (&silent, "SCOUT_STATUS=parse-failed", "missing.json"),
    ] {
        let output = root.path().join(name);
        let assertion = plan_wrapper(root.path())
            .env("SCOUT_PLAN_ARCHETYPES_SCOUT_SH", inner)
            .args([
                "scout",
                "plan-archetypes",
                "--role-id",
                ROLE_PLAN,
                "--plan-file",
                plan.to_str().expect("utf8"),
                "--description-file",
                description.to_str().expect("utf8"),
                "--output",
                output.to_str().expect("utf8"),
                "--session-env-path",
                "",
            ])
            .assert()
            .success();
        assert!(
            String::from_utf8_lossy(&assertion.get_output().stdout).contains(expected),
            "expected {expected} from {inner}"
        );
        assert_eq!(read(&output), EMPTY_MANIFEST);
    }
}

#[test]
fn plan_wrapper_refuses_an_unusable_role_id_and_an_absent_plan() {
    let root = TempDir::new().expect("temp");
    let present = root.path().join("present.txt");
    fs::write(&present, "text\n").expect("present");

    let unknown_role = plan_wrapper(root.path())
        .args([
            "scout",
            "plan-archetypes",
            "--role-id",
            "review.not_a_scout",
            "--plan-file",
            present.to_str().expect("utf8"),
            "--description-file",
            present.to_str().expect("utf8"),
            "--output",
            present.to_str().expect("utf8"),
            "--session-env-path",
            "",
        ])
        .assert()
        .code(2);
    assert!(
        String::from_utf8_lossy(&unknown_role.get_output().stderr).contains(
            "scout-plan-archetypes-wrapper.sh: --role-id must be review.dynamic_archetype_scout or design.plan_archetype_scout"
        )
    );

    let absent_plan = plan_wrapper(root.path())
        .args([
            "scout",
            "plan-archetypes",
            "--role-id",
            ROLE_PLAN,
            "--plan-file",
            root.path().join("absent.txt").to_str().expect("utf8"),
            "--description-file",
            present.to_str().expect("utf8"),
            "--output",
            present.to_str().expect("utf8"),
            "--session-env-path",
            "",
        ])
        .assert()
        .code(2);
    assert!(
        String::from_utf8_lossy(&absent_plan.get_output().stderr).contains("invalid plan-file")
    );
}

#[test]
fn dynamic_archetypes_publishes_the_empty_manifest_without_launching_a_tier() {
    let root = TempDir::new().expect("temp");
    let output = root.path().join("dynamic.json");
    let diff = root.path().join("review.diff");
    fs::write(&diff, "diff --git a/a b/a\n").expect("diff");
    let refuse = launcher(
        root.path(),
        "never.sh",
        "#!/usr/bin/env bash\necho 'a zero cap must not launch a tier' >&2\nexit 1\n",
    );

    let assertion = scout(root.path())
        .env("SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH", &refuse)
        .env("SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH", &refuse)
        .args([
            "scout",
            "dynamic-archetypes",
            "--role-id",
            ROLE_DYNAMIC,
            "--mode",
            "diff",
            "--diff-file",
            diff.to_str().expect("utf8"),
            "--max-archetypes",
            "0",
            "--output",
            output.to_str().expect("utf8"),
        ])
        .assert()
        .success();

    let stdout = String::from_utf8_lossy(&assertion.get_output().stdout).into_owned();
    assert!(stdout.contains("SCOUT_STATUS=empty"));
    assert!(stdout.contains("SCOUT_ARCHETYPE_COUNT=0"));
    assert_eq!(read(&output), EMPTY_MANIFEST);
}

#[test]
fn dynamic_archetypes_falls_back_to_claude_when_cursor_returns_no_manifest() {
    let root = TempDir::new().expect("temp");
    let output = root.path().join("dynamic.json");
    let diff = root.path().join("review.diff");
    fs::write(&diff, "diff --git a/a b/a\n+change\n").expect("diff");

    // Cursor exits cleanly but writes prose, which is a miss rather than a
    // failure, so the waterfall must still reach the Claude tier.
    let cursor = launcher(
        root.path(),
        "cursor.sh",
        "#!/usr/bin/env bash\nwhile [[ $# -gt 0 ]]; do if [[ $1 == --output ]]; then out=$2; shift 2; else shift; fi; done\nprintf 'no manifest here' >\"$out\"\nprintf 'ELAPSED=2\\n'\n",
    );
    let claude = launcher(
        root.path(),
        "claude.sh",
        &format!(
            "#!/usr/bin/env bash\nwhile [[ $# -gt 0 ]]; do if [[ $1 == --output-file ]]; then out=$2; shift 2; else shift; fi; done\nprintf 'prose\\n```json\\n%s\\n```\\n' '{}' >\"$out\"\nprintf 'ELAPSED=3\\n'\n",
            manifest(&[row("api-contract", "correctness")])
        ),
    );

    let assertion = scout(root.path())
        .env("SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH", &cursor)
        .env("SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH", &claude)
        .args([
            "scout",
            "dynamic-archetypes",
            "--role-id",
            ROLE_DYNAMIC,
            "--mode",
            "diff",
            "--diff-file",
            diff.to_str().expect("utf8"),
            "--max-archetypes",
            "4",
            "--output",
            output.to_str().expect("utf8"),
            "--cursor-present",
            "true",
        ])
        .assert()
        .success();

    let stdout = String::from_utf8_lossy(&assertion.get_output().stdout).into_owned();
    assert!(stdout.contains("SCOUT_STATUS=ok"), "{stdout}");
    assert!(stdout.contains("SCOUT_ARCHETYPE_COUNT=1"), "{stdout}");
    assert!(stdout.contains("SCOUT_LATENCY_MS=3000"), "{stdout}");
    // The fenced block is salvaged out of the surrounding prose.
    assert!(read(&output).contains("api-contract"));
    assert!(root.path().join("staged-context/diff.txt").is_file());
}

#[test]
fn dynamic_archetypes_reports_a_failed_tier_and_its_timeout_status() {
    let root = TempDir::new().expect("temp");
    let diff = root.path().join("review.diff");
    fs::write(&diff, "diff --git a/a b/a\n").expect("diff");

    let failing = launcher(
        root.path(),
        "failing.sh",
        "#!/usr/bin/env bash\nprintf 'ELAPSED=1\\n'\nexit 7\n",
    );
    let timing_out = launcher(
        root.path(),
        "timeout.sh",
        "#!/usr/bin/env bash\nwhile [[ $# -gt 0 ]]; do if [[ $1 == --launch-env ]]; then env=$2; shift 2; else shift; fi; done\nprintf 'STATUS=TIMEOUT\\n'\nexit 1\n",
    );

    for (launcher_path, expected, name) in [
        (&failing, "SCOUT_STATUS=claude-failed", "failed.json"),
        (&timing_out, "SCOUT_STATUS=timeout", "timeout.json"),
    ] {
        let output = root.path().join(name);
        let assertion = scout(root.path())
            .env("SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH", launcher_path)
            .args([
                "scout",
                "dynamic-archetypes",
                "--role-id",
                ROLE_DYNAMIC,
                "--mode",
                "diff",
                "--diff-file",
                diff.to_str().expect("utf8"),
                "--max-archetypes",
                "2",
                "--output",
                output.to_str().expect("utf8"),
            ])
            .assert()
            .success();
        assert!(
            String::from_utf8_lossy(&assertion.get_output().stdout).contains(expected),
            "expected {expected} from {launcher_path}"
        );
        assert_eq!(read(&output), EMPTY_MANIFEST);
    }
}

#[test]
fn dynamic_archetypes_refuses_a_malformed_command_line() {
    let root = TempDir::new().expect("temp");
    let output = root.path().join("dynamic.json");
    let diff = root.path().join("review.diff");
    fs::write(&diff, "diff --git a/a b/a\n").expect("diff");
    let base = [
        "scout",
        "dynamic-archetypes",
        "--role-id",
        ROLE_DYNAMIC,
        "--output",
    ];

    for (arguments, expected) in [
        (
            vec!["--mode", "sideways", "--max-archetypes", "2"],
            "--mode must be diff or description",
        ),
        (
            vec!["--mode", "diff", "--max-archetypes", "9"],
            "--max-archetypes must be an integer from 0 to 8",
        ),
        (
            vec!["--mode", "diff", "--max-archetypes", "2"],
            "--diff-file is required for diff mode",
        ),
        (
            vec!["--mode", "description", "--max-archetypes", "2"],
            "--scope-files is required for description mode",
        ),
    ] {
        let refusal = scout(root.path())
            .args(base)
            .arg(output.to_str().expect("utf8"))
            .args(&arguments)
            .assert()
            .code(2);
        let stderr = String::from_utf8_lossy(&refusal.get_output().stderr).into_owned();
        assert!(
            stderr.contains(expected),
            "expected {expected} for {arguments:?}, got {stderr}"
        );
        assert!(stderr.contains("scout-dynamic-archetypes.sh:"));
    }
}
