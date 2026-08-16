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

fn larch() -> Command {
    Command::new(env!("CARGO_BIN_EXE_larch"))
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
    write_exec(
        &launcher,
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
mechanical_churn: false
diff_lines: 1
EOF
exit 0
"#,
    );
    let driver = root.join("driver.sh");
    write_exec(
        &driver,
        "#!/bin/sh\nprintf 'EMIT_PLAN_STATUS=ok\\n'\nexit 0\n",
    );

    let output = larch()
        .args([
            "plan",
            "revise-waterfall",
            "--design-tmpdir",
            root.to_str().unwrap(),
            "--plan-file",
            plan.to_str().unwrap(),
            "--findings-file",
            findings.to_str().unwrap(),
            "--feature-file",
            feature.to_str().unwrap(),
            "--round-num",
            "2",
            "--codex-binary-found",
            "true",
            "--cursor-binary-found",
            "false",
            "--timeout",
            "5",
            "--patch-format",
            "file-replacement",
        ])
        .env("LARCH_TEST_LAUNCH_CODEX_REVIEW", &launcher)
        .env("LARCH_TEST_LAUNCH_CLAUDE_REVIEW", &launcher)
        .env("LARCH_TEST_DESIGN_DRIVER", &driver)
        .output()
        .expect("run revise");
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
