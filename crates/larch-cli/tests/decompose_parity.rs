//! Black-box parity for the `decompose` panel and aggregate verbs (#8588).
//!
//! The two orchestration verbs shell out to the decomposition waterfall; a stub
//! script injected through the documented `DECOMPOSE_*_WATERFALL_SH` seam lets
//! this test drive them offline exactly as the retired Python tests did.

use std::{fs, path::Path, process::Command};

#[cfg(unix)]
use std::os::unix::fs::PermissionsExt as _;

use tempfile::TempDir;

fn repo_root() -> std::path::PathBuf {
    fs::canonicalize(Path::new(env!("CARGO_MANIFEST_DIR")).join("..").join(".."))
        .expect("repo root canonicalizes")
}

fn write_stub(path: &Path) {
    fs::write(
        path,
        "#!/usr/bin/env bash\n\
         set -euo pipefail\n\
         slots=\"\"\n\
         while [[ $# -gt 0 ]]; do if [[ $1 == --slots-file ]]; then slots=$2; shift 2; else shift; fi; done\n\
         paths=$(mktemp)\n\
         while IFS= read -r row; do\n\
           [[ -z \"$row\" ]] && continue\n\
           out=$(printf '%s' \"$row\" | sed -n 's/.*\"output\":\"\\([^\"]*\\)\".*/\\1/p')\n\
           printf '## Recommendation\\nsplit\\n' > \"$out\"\n\
           printf '%s\\n' \"$out\" >> \"$paths\"\n\
         done < \"$slots\"\n\
         printf 'DISPATCH_OK=true\\nFALLBACK_COUNT=0\\nCOMBINED_FALLBACK_COUNT=0\\nSTATIC_DISPATCH_OK=true\\nALL_OUTPUT_FILES_PATH=%s\\n' \"$paths\"\n",
    )
    .expect("write stub");
    #[cfg(unix)]
    fs::set_permissions(path, fs::Permissions::from_mode(0o755)).expect("chmod stub");
}

#[test]
#[cfg(unix)]
fn panel_and_aggregate_dispatch_with_stub_waterfall() {
    let temp = TempDir::new().expect("tempdir");
    let design = temp.path().join("design");
    fs::create_dir_all(&design).expect("design dir");
    fs::write(design.join("feature-description.txt"), "Feature\n").expect("feature");
    fs::write(design.join("plan.txt"), "## Plan\n").expect("plan");
    let stub = temp.path().join("waterfall.sh");
    write_stub(&stub);
    let root = repo_root();

    let panel = Command::new(env!("CARGO_BIN_EXE_larch"))
        .env("CLAUDE_PLUGIN_ROOT", &root)
        .env("DECOMPOSE_PANEL_WATERFALL_SH", &stub)
        .args([
            "decompose",
            "panel-dispatch",
            "--design-tmpdir",
            design.to_str().unwrap(),
            "--codex-binary-found",
            "true",
            "--cursor-binary-found",
            "true",
            "--mode",
            "plan",
            "--plan-file",
            design.join("plan.txt").to_str().unwrap(),
            "--timeout",
            "30",
        ])
        .output()
        .expect("panel-dispatch runs");
    assert!(
        panel.status.success(),
        "panel stderr: {}",
        String::from_utf8_lossy(&panel.stderr)
    );
    let panel_stdout = String::from_utf8_lossy(&panel.stdout);
    assert!(
        panel_stdout.contains("DISPATCH_OK=true"),
        "stdout: {panel_stdout}"
    );
    assert!(
        panel_stdout.contains("ALL_OUTPUT_FILES_PATH="),
        "stdout: {panel_stdout}"
    );
    assert!(
        panel_stdout.contains("PANEL_STATUS=ok"),
        "stdout: {panel_stdout}"
    );

    let panel_outputs = design.join("decompose").join("panel-outputs.ndjson");
    let panel_body = fs::read_to_string(&panel_outputs).expect("panel outputs");
    let rows: Vec<&str> = panel_body.lines().filter(|line| !line.is_empty()).collect();
    assert_eq!(rows.len(), 8, "expected 8 panel rows");
    assert!(
        rows.iter().all(|row| row.contains("\"status\":\"ok\"")),
        "rows: {rows:?}"
    );

    let aggregate = Command::new(env!("CARGO_BIN_EXE_larch"))
        .env("CLAUDE_PLUGIN_ROOT", &root)
        .env("DECOMPOSE_AGGREGATE_WATERFALL_SH", &stub)
        .args([
            "decompose",
            "aggregate",
            "--design-tmpdir",
            design.to_str().unwrap(),
            "--panel-outputs-file",
            panel_outputs.to_str().unwrap(),
            "--codex-binary-found",
            "true",
            "--cursor-binary-found",
            "true",
            "--output",
            design.join("partition.md").to_str().unwrap(),
            "--timeout",
            "30",
        ])
        .output()
        .expect("aggregate runs");
    assert!(
        aggregate.status.success(),
        "aggregate stderr: {}",
        String::from_utf8_lossy(&aggregate.stderr)
    );
    let aggregate_stdout = String::from_utf8_lossy(&aggregate.stdout);
    assert!(
        aggregate_stdout.contains("AGGREGATOR_STATUS=ok"),
        "stdout: {aggregate_stdout}"
    );
    assert!(
        design.join("partition.md").is_file(),
        "merged partition written"
    );
}

#[test]
#[cfg(unix)]
fn panel_both_tools_absent_uses_generic_claude() {
    let temp = TempDir::new().expect("tempdir");
    let design = temp.path().join("design");
    fs::create_dir_all(&design).expect("design dir");
    fs::write(design.join("feature-description.txt"), "Feature\n").expect("feature");
    fs::write(design.join("plan.txt"), "## Plan\n").expect("plan");
    let claude = temp.path().join("claude.sh");
    fs::write(
        &claude,
        "#!/usr/bin/env bash\n\
         set -euo pipefail\n\
         out=\"\"\n\
         while [[ $# -gt 0 ]]; do if [[ $1 == --output ]]; then out=$2; shift 2; else shift; fi; done\n\
         printf '## Recommendation\\nGeneric\\n' > \"$out\"\n\
         printf '0\\n' > \"${out}.done\"\n",
    )
    .expect("write claude stub");
    fs::set_permissions(&claude, fs::Permissions::from_mode(0o755)).expect("chmod claude");
    let root = repo_root();

    let panel = Command::new(env!("CARGO_BIN_EXE_larch"))
        .env("CLAUDE_PLUGIN_ROOT", &root)
        .env("LARCH_TEST_LAUNCH_CLAUDE_REVIEW", &claude)
        .args([
            "decompose",
            "panel-dispatch",
            "--design-tmpdir",
            design.to_str().unwrap(),
            "--codex-binary-found",
            "false",
            "--cursor-binary-found",
            "false",
            "--mode",
            "plan",
            "--plan-file",
            design.join("plan.txt").to_str().unwrap(),
            "--timeout",
            "30",
        ])
        .output()
        .expect("panel-dispatch runs");
    assert!(
        panel.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&panel.stderr)
    );
    assert!(String::from_utf8_lossy(&panel.stdout).contains("PANEL_STATUS=ok"));
    let rows = fs::read_to_string(design.join("decompose").join("panel-outputs.ndjson"))
        .expect("panel outputs");
    let rows: Vec<&str> = rows.lines().filter(|line| !line.is_empty()).collect();
    assert_eq!(rows.len(), 1, "generic panel emits one row");
    assert!(
        rows[0].contains("\"archetype\":\"generic\""),
        "row: {}",
        rows[0]
    );
}

#[test]
#[cfg(unix)]
fn aggregate_malformed_ndjson_emits_failed_exactly_once() {
    let temp = TempDir::new().expect("tempdir");
    let design = temp.path().join("design");
    fs::create_dir_all(&design).expect("design dir");
    fs::write(design.join("feature-description.txt"), "Feature\n").expect("feature");
    let panel = design.join("panel.ndjson");
    fs::write(&panel, "not-json\n").expect("malformed panel");

    let aggregate = Command::new(env!("CARGO_BIN_EXE_larch"))
        .env("CLAUDE_PLUGIN_ROOT", repo_root())
        .args([
            "decompose",
            "aggregate",
            "--design-tmpdir",
            design.to_str().unwrap(),
            "--panel-outputs-file",
            panel.to_str().unwrap(),
            "--output",
            design.join("merged.md").to_str().unwrap(),
            "--timeout",
            "30",
        ])
        .output()
        .expect("aggregate runs");
    assert_eq!(aggregate.status.code(), Some(2), "malformed NDJSON exits 2");
    let stdout = String::from_utf8_lossy(&aggregate.stdout);
    assert_eq!(
        stdout.matches("AGGREGATOR_STATUS=failed").count(),
        1,
        "AGGREGATOR_STATUS=failed must appear exactly once; stdout: {stdout}"
    );
}

fn larch(design: &Path, args: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_larch"))
        .env("CLAUDE_PLUGIN_ROOT", repo_root())
        .args(args)
        .env_remove("LARCH_TEST_LIVE_MUTATION_DENY")
        .output()
        .unwrap_or_else(|error| panic!("run larch in {}: {error}", design.display()))
}

#[test]
fn prepare_and_annotate_drive_the_full_verb_path() {
    let temp = TempDir::new().expect("tempdir");
    let design = temp.path().join("design");
    fs::create_dir_all(&design).expect("design dir");
    fs::write(
        design.join("feature-description.txt"),
        "Feature\n### embedded\n",
    )
    .expect("feature");
    let partition = design.join("partition.md");
    fs::write(
        &partition,
        "## Pieces\n\n### Piece 1: Base\n- Scope: base\n- Firm-headings: base/file.py\n- Acceptance: verify base\n- Dependencies: none\n\n### Piece 2: API\n- Scope: api\n- Firm-headings: api/file.py\n- Acceptance: verify api\n- Dependencies: blocked-by Piece 1\n",
    )
    .expect("partition");

    let prepare = larch(
        &design,
        &[
            "decompose",
            "prepare",
            "--design-tmpdir",
            design.to_str().unwrap(),
            "--partition-file",
            partition.to_str().unwrap(),
            "--issue-number",
            "5",
        ],
    );
    assert!(
        prepare.status.success(),
        "prepare stderr: {}",
        String::from_utf8_lossy(&prepare.stderr)
    );
    assert!(String::from_utf8_lossy(&prepare.stdout).contains("DECOMPOSE_PARTITION_STATUS=ok"));
    assert!(design.join("decompose/partition-input.txt").is_file());

    let out = design.join("issue.out");
    fs::write(&out, "ISSUES_CREATED=2\nISSUES_FAILED=0\nISSUE_1_URL=https://github.com/o/r/issues/101\nISSUE_2_URL=https://github.com/o/r/issues/102\n").expect("issue out");
    let annotate = larch(
        &design,
        &[
            "decompose",
            "annotate",
            "--design-tmpdir",
            design.to_str().unwrap(),
            "--issue-stdout-file",
            out.to_str().unwrap(),
        ],
    );
    assert!(
        annotate.status.success(),
        "annotate stderr: {}",
        String::from_utf8_lossy(&annotate.stderr)
    );
    assert!(design.join(".decompose-issues-filed").is_file());
}

#[test]
fn migrate_deps_and_close_original_refuse_before_github() {
    let temp = TempDir::new().expect("tempdir");
    let design = temp.path().join("design");
    fs::create_dir_all(&design).expect("design dir");
    fs::write(design.join("feature-description.txt"), "Feature\n").expect("feature");
    fs::write(design.join("source-env.sh"), "LARCH_RUN_ID=test\n").expect("source env");

    // No live-mutation authorization in the session context -> denied, exit 1.
    let migrate = larch(
        &design,
        &[
            "decompose",
            "migrate-deps",
            "--design-tmpdir",
            design.to_str().unwrap(),
            "--original-issue",
            "99",
            "--repo",
            "o/r",
        ],
    );
    assert_eq!(
        migrate.status.code(),
        Some(1),
        "migrate stderr: {}",
        String::from_utf8_lossy(&migrate.stderr)
    );
    assert!(
        String::from_utf8_lossy(&migrate.stdout)
            .contains("DECOMPOSE_DEPS_STATUS=authorization-denied")
    );

    // No dependency-migration sentinel -> close refuses before any GitHub call, exit 2.
    let close = larch(
        &design,
        &[
            "decompose",
            "close-original",
            "--design-tmpdir",
            design.to_str().unwrap(),
            "--original-issue",
            "99",
            "--repo",
            "o/r",
        ],
    );
    assert_eq!(
        close.status.code(),
        Some(2),
        "close stderr: {}",
        String::from_utf8_lossy(&close.stderr)
    );
}
