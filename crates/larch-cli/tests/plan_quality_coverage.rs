//! Extra coverage for plan-quality CLI paths that need child-process env.

use std::{
    fs,
    os::unix::fs::PermissionsExt,
    path::{Path, PathBuf},
    process::Command,
    sync::atomic::{AtomicU64, Ordering},
    time::{SystemTime, UNIX_EPOCH},
};

fn unique_root(label: &str) -> PathBuf {
    static COUNTER: AtomicU64 = AtomicU64::new(0);
    let n = COUNTER.fetch_add(1, Ordering::Relaxed);
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_nanos())
        .unwrap_or(0);
    let root = PathBuf::from("/tmp").join(format!(
        "larch-pqc-{label}-{}-{nanos}-{n}",
        std::process::id()
    ));
    let _ = fs::remove_dir_all(&root);
    fs::create_dir_all(&root).expect("create root");
    root
}

fn write_exec(path: &Path, body: &str) {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).expect("mkdir");
    }
    fs::write(path, body).expect("write");
    let mut perms = fs::metadata(path).expect("meta").permissions();
    perms.set_mode(0o755);
    fs::set_permissions(path, perms).expect("chmod");
}

const fn mini_plan() -> &'static str {
    "### NEW: fixture\n\n1. Touch `scripts/noop.sh`.\n\ndifficulty: HARD\nmechanical_churn: false\ndiff_lines: 1\n"
}

fn write_replacement_launcher(path: &Path, mechanical_churn: &str) {
    write_exec(
        path,
        &format!(
            r#"#!/bin/sh
out=""
while [ "$#" -gt 0 ]; do
  if [ "$1" = "--output" ]; then
    out="$2"
    shift 2
    continue
  fi
  shift
done
cat >"$out" <<'EOF'
## Plan
### NEW: fixture

1. Touch `scripts/noop.sh`.

difficulty: HARD
mechanical_churn: {mechanical_churn}
diff_lines: 1
EOF
"#
        ),
    );
}

fn larch() -> Command {
    Command::new(env!("CARGO_BIN_EXE_larch"))
}

fn repo_root() -> &'static Path {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(Path::parent)
        .expect("repository root")
}

#[test]
fn check_size_reports_five_rust_module_surfaces_and_trips() {
    let root = unique_root("rust-surfaces");
    fs::write(
        root.join("plan.txt"),
        "### UPDATED: crates/larch-core/src/design/plan_quality.rs\n\
         ### UPDATED: crates/larch-core/src/issue/mod.rs\n\
         ### UPDATED: crates/larch-cli/src/analyze_bugs_commands.rs\n\
         ### UPDATED: crates/larch-adapters/src/github/client.rs\n\
         ### UPDATED: crates/larch-lint/tests/plan_surfaces.rs\n\
         difficulty: HARD\n\
         diff_lines: 1\n",
    )
    .expect("write plan");
    fs::write(
        root.join("drift-baseline.env"),
        "BASELINE_PLAN_LINES=6\nBASELINE_DIFF_LINES=1\n",
    )
    .expect("write drift baseline");

    let output = larch()
        .args(["plan", "check-size", "--design-tmpdir"])
        .arg(&root)
        .output()
        .expect("run check-size");
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        output.status.success(),
        "stderr={}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(stdout.lines().any(|line| line == "SURFACES_TOUCHED=5"));
    assert!(stdout.lines().any(|line| line == "SIZE_TRIGGER_FIRED=true"));
    assert!(stdout.lines().any(|line| line == "TRIGGER_REASONS=surfaces"));

    let _ = fs::remove_dir_all(root);
}

#[test]
fn plan_quality_help_and_usage_errors_name_larch() {
    let plan_verbs = [
        "auto-fix-commands",
        "check-size",
        "compose-goals-test",
        "optional-trailers",
        "parse-commands",
        "revise-waterfall",
        "set-oversize-override",
        "validate",
        "validate-commands",
    ];
    for verb in plan_verbs {
        let output = larch()
            .args(["plan", verb, "--help"])
            .output()
            .expect("run plan help");
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);
        assert!(output.status.success(), "verb={verb} stderr={stderr}");
        assert!(
            stdout.starts_with(&format!("usage: larch plan {verb} ")),
            "verb={verb} stdout={stdout}"
        );
        assert!(!stdout.contains("cli.py"), "verb={verb} stdout={stdout}");
        assert!(stderr.is_empty(), "verb={verb} stderr={stderr}");
    }

    for verb in [
        "auto-fix-commands",
        "check-size",
        "compose-goals-test",
        "optional-trailers",
        "parse-commands",
        "revise-waterfall",
        "set-oversize-override",
        "validate",
        "validate-commands",
    ] {
        let output = larch()
            .args(["plan", verb])
            .output()
            .expect("run plan usage error");
        let stderr = String::from_utf8_lossy(&output.stderr);
        assert_eq!(output.status.code(), Some(2), "verb={verb} stderr={stderr}");
        assert!(
            stderr.starts_with(&format!("usage: larch plan {verb} ")),
            "verb={verb} stderr={stderr}"
        );
        assert!(!stderr.contains("cli.py"), "verb={verb} stderr={stderr}");
    }
}

#[test]
fn plan_review_step35_help_and_usage_errors_name_larch() {
    let step35_help = larch()
        .args(["plan-review", "step35", "--help"])
        .env("CLAUDE_PLUGIN_ROOT", repo_root())
        .output()
        .expect("run step35 help");
    assert!(step35_help.status.success());
    assert_eq!(
        String::from_utf8_lossy(&step35_help.stdout),
        "usage: larch plan-review step35 [-h] --design-tmpdir DESIGN_TMPDIR\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n"
    );
    assert!(step35_help.stderr.is_empty());

    let step35_error = larch()
        .args(["plan-review", "step35"])
        .env("CLAUDE_PLUGIN_ROOT", repo_root())
        .output()
        .expect("run step35 usage error");
    let step35_stderr = String::from_utf8_lossy(&step35_error.stderr);
    assert_eq!(step35_error.status.code(), Some(2));
    assert!(
        step35_stderr.starts_with(
            "usage: larch plan-review step35 [-h] --design-tmpdir DESIGN_TMPDIR\n"
        ),
        "{step35_stderr}"
    );
    assert!(!step35_stderr.contains("cli.py"), "{step35_stderr}");
}

#[test]
fn step2b_postplan_help_precedes_environment_validation() {
    let postplan_help = larch()
        .args(["design", "step2b-postplan", "--help"])
        .env("CLAUDE_PLUGIN_ROOT", repo_root())
        .env_remove("DESIGN_TMPDIR")
        .output()
        .expect("run step2b-postplan help");
    let postplan_stdout = String::from_utf8_lossy(&postplan_help.stdout);
    assert!(postplan_help.status.success());
    assert!(
        postplan_stdout.starts_with("usage: larch design step2b-postplan [-h] "),
        "{postplan_stdout}"
    );
    assert!(!postplan_stdout.contains("cli.py"), "{postplan_stdout}");
    assert!(postplan_help.stderr.is_empty());

    let delimited_help = larch()
        .args(["design", "step2b-postplan", "--", "--help"])
        .env("CLAUDE_PLUGIN_ROOT", repo_root())
        .env_remove("DESIGN_TMPDIR")
        .output()
        .expect("run delimited step2b-postplan help token");
    assert_eq!(delimited_help.status.code(), Some(1));
    assert!(delimited_help.stdout.is_empty());
    assert_eq!(
        String::from_utf8_lossy(&delimited_help.stderr),
        "/design Step 2b postplan: DESIGN_TMPDIR required\n"
    );
}

#[test]
fn plan_quality_help_assets_do_not_name_the_retired_python_entry() {
    let help_root = Path::new(env!("CARGO_MANIFEST_DIR")).join("assets/plan-quality-help");
    for entry in fs::read_dir(help_root).expect("read plan-quality help assets") {
        let path = entry.expect("help asset entry").path();
        if !path.is_file() {
            continue;
        }
        let text = fs::read_to_string(&path).expect("read plan-quality help asset");
        assert!(!text.contains("cli.py"), "asset={}", path.display());
    }
}

fn run_file_replacement_revise(
    root: &Path,
    plan: &Path,
    findings: &Path,
    feature: &Path,
    round: u64,
    launcher: &Path,
    driver: &Path,
) -> std::process::Output {
    let mut command = larch();
    command
        .args(["plan", "revise-waterfall", "--design-tmpdir"])
        .arg(root)
        .arg("--plan-file")
        .arg(plan)
        .arg("--findings-file")
        .arg(findings)
        .arg("--feature-file")
        .arg(feature)
        .args([
            "--round-num",
            &round.to_string(),
            "--codex-binary-found",
            "true",
            "--cursor-binary-found",
            "false",
            "--timeout",
            "5",
            "--patch-format",
            "file-replacement",
        ])
        .env("LARCH_TEST_LAUNCH_CODEX_REVIEW", launcher)
        .env("LARCH_TEST_LAUNCH_CLAUDE_REVIEW", launcher)
        .env("LARCH_TEST_DESIGN_DRIVER", driver)
        .output()
        .expect("run revise")
}

#[test]
fn auto_fix_commands_dispatch_and_validate_success_path() {
    let root = unique_root("autofix-ok");
    let plan = root.join("plan.txt");
    fs::write(&plan, mini_plan()).expect("plan");
    fs::write(root.join("validate-plan-commands.log"), "prior\n").expect("log");

    let dispatch = root.join("dispatch.sh");
    write_exec(
        &dispatch,
        "#!/bin/sh\n# consume args; leave plan unchanged\nexit 0\n",
    );
    let validate = root.join("validate.sh");
    write_exec(
        &validate,
        "#!/bin/sh\nprintf 'VALIDATE_STATUS=ok\\n'\nexit 0\n",
    );

    let output = larch()
        .args([
            "plan",
            "auto-fix-commands",
            "--design-tmpdir",
            root.to_str().unwrap(),
            "--plan-file",
            plan.to_str().unwrap(),
            "--codex-binary-found",
            "true",
            "--cursor-binary-found",
            "false",
            "--max-attempts",
            "1",
            "--timeout",
            "5",
            "--site",
            "coverage site",
        ])
        .env("LARCH_AUTOFIX_DISPATCH_SH", &dispatch)
        .env("LARCH_AUTOFIX_VALIDATE_PLAN_SH", &validate)
        .output()
        .expect("run auto-fix");
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        output.status.success(),
        "stderr={}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(stdout.contains("AUTOFIX_STATUS=ok"), "{stdout}");
    assert!(stdout.contains("FIXED_BY=codex"), "{stdout}");
    let _ = fs::remove_dir_all(&root);
}

#[test]
fn auto_fix_commands_dispatch_failure_exhausts() {
    let root = unique_root("autofix-fail");
    let plan = root.join("plan.txt");
    fs::write(&plan, mini_plan()).expect("plan");

    let dispatch = root.join("dispatch.sh");
    write_exec(&dispatch, "#!/bin/sh\nexit 7\n");

    let output = larch()
        .args([
            "plan",
            "auto-fix-commands",
            "--design-tmpdir",
            root.to_str().unwrap(),
            "--plan-file",
            plan.to_str().unwrap(),
            "--codex-binary-found",
            "true",
            "--cursor-binary-found",
            "true",
            "--max-attempts",
            "2",
            "--timeout",
            "5",
        ])
        .env("LARCH_AUTOFIX_DISPATCH_SH", &dispatch)
        .output()
        .expect("run auto-fix");
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(output.status.success());
    assert!(stdout.contains("AUTOFIX_STATUS=exhausted"), "{stdout}");
    assert!(
        stdout.contains("FINAL_VALIDATE_STATUS=dispatch-failed"),
        "{stdout}"
    );
    let _ = fs::remove_dir_all(&root);
}

#[test]
fn revise_waterfall_with_launch_override_file_replacement() {
    let root = unique_root("revise-ok");
    let plan = root.join("plan.txt");
    let findings = root.join("findings.md");
    let feature = root.join("feature.txt");
    fs::write(&plan, mini_plan()).expect("plan");
    fs::write(&findings, "finding\n").expect("findings");
    fs::write(&feature, "feature\n").expect("feature");

    let launcher = root.join("launch.sh");
    // Args include --output <path>; write a replacement plan there.
    write_replacement_launcher(&launcher, "false");
    let driver = root.join("driver.sh");
    write_exec(
        &driver,
        "#!/bin/sh\nprintf 'EMIT_PLAN_STATUS=ok\\n'\nexit 0\n",
    );

    let output =
        run_file_replacement_revise(&root, &plan, &findings, &feature, 2, &launcher, &driver);
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        output.status.success(),
        "stderr={}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        stdout.contains("REVISE_STATUS=ok") || stdout.contains("REVISE_STATUS=ok-fallback"),
        "{stdout}"
    );
    let _ = fs::remove_dir_all(&root);
}

#[test]
fn revise_waterfall_records_bounded_emit_plan_driver_failure() {
    let root = unique_root("revise-driver-failure");
    let plan = root.join("plan.txt");
    let findings = root.join("findings.md");
    let feature = root.join("feature.txt");
    fs::write(&plan, mini_plan()).expect("plan");
    fs::write(&findings, "finding\n").expect("findings");
    fs::write(&feature, "feature\n").expect("feature");

    let launcher = root.join("launch.sh");
    write_replacement_launcher(&launcher, "false");
    let driver = root.join("driver.sh");
    write_exec(
        &driver,
        r#"#!/bin/sh
i=0
while [ "$i" -lt 600 ]; do
  printf 'stdout-padding-%04d\n' "$i"
  printf 'stderr-padding-%04d\n' "$i" >&2
  i=$((i + 1))
done
printf 'driver stdout tail\n'
printf 'driver stderr tail\n' >&2
exit 7
"#,
    );

    let output =
        run_file_replacement_revise(&root, &plan, &findings, &feature, 3, &launcher, &driver);
    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(output.status.success(), "stderr={stderr}");
    assert!(
        stdout.contains("REVISE_TIER_1_STATUS=emit-plan-failed\n"),
        "{stdout}"
    );
    assert!(
        stdout.contains("REVISE_TIER_1_REASON=driver-exit-7\n"),
        "{stdout}"
    );
    assert!(stderr.contains(&driver.display().to_string()), "{stderr}");
    assert!(stderr.contains("status=7"), "{stderr}");
    assert!(stderr.contains("driver stdout tail"), "{stderr}");
    assert!(stderr.contains("driver stderr tail"), "{stderr}");
    assert!(stderr.contains("earlier bytes"), "{stderr}");

    let revise_dir = root.join("plan-review/round-3/revise");
    let revise_env = fs::read_to_string(revise_dir.join("revise.env")).expect("revise.env");
    assert!(
        revise_env.contains("REVISE_TIER_1_REASON=driver-exit-7\n"),
        "{revise_env}"
    );
    let log = revise_dir.join("emit-plan-gate.log");
    let log_text = fs::read_to_string(&log).expect("emit-plan gate log");
    assert!(
        log_text.contains(&driver.display().to_string()),
        "{log_text}"
    );
    assert!(log_text.contains("status=7"), "{log_text}");
    assert!(log_text.contains("driver stdout tail"), "{log_text}");
    assert!(log_text.contains("driver stderr tail"), "{log_text}");
    assert!(log_text.contains("earlier bytes"), "{log_text}");
    assert!(log_text.len() < 20_000, "log was not bounded");
    assert_eq!(
        fs::read_to_string(&plan).expect("restored plan"),
        mini_plan()
    );
    let _ = fs::remove_dir_all(&root);
}

#[test]
fn revise_waterfall_names_invalid_mechanical_churn_reason() {
    let root = unique_root("revise-invalid-mechanical-churn");
    let plan = root.join("plan.txt");
    let findings = root.join("findings.md");
    let feature = root.join("feature.txt");
    fs::write(&plan, mini_plan()).expect("plan");
    fs::write(&findings, "finding\n").expect("findings");
    fs::write(&feature, "feature\n").expect("feature");

    let launcher = root.join("launch.sh");
    write_replacement_launcher(&launcher, "25");
    let driver = root.join("driver.sh");
    write_exec(&driver, "#!/bin/sh\nprintf 'EMIT_PLAN_STATUS=ok\\n'\n");

    let output =
        run_file_replacement_revise(&root, &plan, &findings, &feature, 4, &launcher, &driver);
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        output.status.success(),
        "stderr={}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        stdout.contains("REVISE_TIER_1_STATUS=invalid-patch\n"),
        "{stdout}"
    );
    assert!(
        stdout.contains("REVISE_TIER_1_REASON=invalid-mechanical-churn\n"),
        "{stdout}"
    );
    assert!(
        stdout.contains("REVISE_STATUS=failed-validation\n"),
        "{stdout}"
    );
    let revise_env =
        fs::read_to_string(root.join("plan-review/round-4/revise/revise.env")).expect("revise.env");
    assert!(
        revise_env.contains("REVISE_TIER_1_REASON=invalid-mechanical-churn\n"),
        "{revise_env}"
    );
    assert_eq!(
        fs::read_to_string(&plan).expect("restored plan"),
        mini_plan()
    );
    let _ = fs::remove_dir_all(&root);
}

#[test]
fn revise_waterfall_names_no_patch_reason() {
    let root = unique_root("revise-no-patch");
    let plan = root.join("plan.txt");
    let findings = root.join("findings.md");
    let feature = root.join("feature.txt");
    fs::write(&plan, mini_plan()).expect("plan");
    fs::write(&findings, "finding\n").expect("findings");
    fs::write(&feature, "feature\n").expect("feature");

    let launcher = root.join("launch.sh");
    write_exec(&launcher, "#!/bin/sh\nexit 9\n");
    let driver = root.join("driver.sh");
    write_exec(&driver, "#!/bin/sh\nprintf 'EMIT_PLAN_STATUS=ok\\n'\n");
    let output =
        run_file_replacement_revise(&root, &plan, &findings, &feature, 5, &launcher, &driver);
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        output.status.success(),
        "stderr={}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        stdout.contains("REVISE_TIER_1_STATUS=no-patch\n"),
        "{stdout}"
    );
    assert!(
        stdout.contains("REVISE_TIER_1_REASON=launcher-exit-9\n"),
        "{stdout}"
    );
    assert!(
        stdout.contains("REVISE_STATUS=failed-no-patch\n"),
        "{stdout}"
    );
    let revise_env =
        fs::read_to_string(root.join("plan-review/round-5/revise/revise.env")).expect("revise.env");
    assert!(
        revise_env.contains("REVISE_TIER_1_REASON=launcher-exit-9\n"),
        "{revise_env}"
    );
    let _ = fs::remove_dir_all(&root);
}

#[test]
fn validator_autofix_operator_cancel_with_design_tmpdir() {
    let root = unique_root("validator");
    fs::write(root.join("plan.txt"), mini_plan()).expect("plan");
    let output = larch()
        .args(["plan", "validator-autofix", "--operator-cancel"])
        .env("DESIGN_TMPDIR", &root)
        .env("SITE", "design Gate B")
        .output()
        .expect("run validator-autofix");
    assert!(
        output.status.success(),
        "stderr={}",
        String::from_utf8_lossy(&output.stderr)
    );
    let _ = fs::remove_dir_all(&root);
}

#[test]
fn validator_autofix_cycle_cap_and_unavailable() {
    let root = unique_root("validator-cycle");
    fs::write(root.join("plan.txt"), mini_plan()).expect("plan");
    let first = larch()
        .args(["plan", "validator-autofix", "--site", "design Gate B"])
        .env("DESIGN_TMPDIR", &root)
        .env("CODEX_BINARY_FOUND", "false")
        .env("CURSOR_BINARY_FOUND", "false")
        .env("VALIDATE_DEFECT_COUNT", "1")
        .env("VALIDATE_UNSAFE_TOKEN_COUNT", "0")
        .env("VALIDATE_SKIPPED_COUNT", "0")
        .output()
        .expect("first");
    assert!(first.status.success());
    let second = larch()
        .args(["plan", "validator-autofix", "--site", "design Gate B"])
        .env("DESIGN_TMPDIR", &root)
        .env("CODEX_BINARY_FOUND", "false")
        .env("CURSOR_BINARY_FOUND", "false")
        .env("VALIDATE_DEFECT_COUNT", "1")
        .env("VALIDATE_UNSAFE_TOKEN_COUNT", "0")
        .env("VALIDATE_SKIPPED_COUNT", "0")
        .output()
        .expect("second");
    let stdout = String::from_utf8_lossy(&second.stdout);
    assert!(second.status.success());
    assert!(
        stdout.contains("AUTOFIX_STATUS=skipped-cycle-cap")
            || stdout.contains("AUTOFIX_STATUS=unavailable")
            || stdout.contains("AUTOFIX_STATUS=ok"),
        "{stdout}"
    );
    let _ = fs::remove_dir_all(&root);
}
