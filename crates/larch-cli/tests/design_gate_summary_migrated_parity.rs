//! Golden-driven black-box parity for the migrated `/design` render verbs (#8581).
//!
//! The recorded goldens came from the frozen pre-cutover Python owner at
//! `fixtures/rust-parity/design_gate_summary_migrated_reference.py`. After
//! #8901 retired its shared Python dependencies, each case runs the Rust owner
//! in an isolated sandbox and checks stdout, stderr, exit status, and wire files
//! against that recorded contract.
//!
//! Scope note: the `render-final-summary` cases seed a `manifest.json` so the
//! `render run-summary` identity line is deterministic (its live fallback reads
//! the ambient Claude transcript, which the sandbox does not provide). Cases
//! cover the pure gate matrix, the gate error paths, and the pre/post enrichment,
//! missing-assessment, guideline-exception, and OOS/exec-issue summary branches.

#[path = "support/parity.rs"]
#[allow(dead_code)]
mod parity_support;

use std::{
    env,
    fs,
    path::{Path, PathBuf},
    process::Command,
};

use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_rust_golden_case};

fn repository_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("canonical repository root")
}

fn fixture_directory() -> PathBuf {
    repository_root().join("fixtures/rust-parity")
}

fn python_executable() -> PathBuf {
    env::split_paths(&env::var_os("PATH").expect("PATH"))
        .map(|directory| directory.join("python3"))
        .find(|candidate| candidate.is_file())
        .and_then(|candidate| candidate.canonicalize().ok())
        .expect("python3 on PATH")
}

fn parity_case(
    name: &'static str,
    reference_tail: &[String],
    rust_tail: &[String],
    seeds: Vec<SeedFile>,
) -> ParityCase {
    let root = repository_root();
    let reference = fixture_directory().join("design_gate_summary_migrated_reference.py");
    let python_path = root.join("python");
    let plugin_root = root.to_string_lossy().into_owned();
    let path = env::var("PATH").expect("PATH");
    let binary = env!("CARGO_BIN_EXE_larch");

    let python = Program::new(python_executable())
        .args(
            std::iter::once(reference.to_string_lossy().into_owned())
                .chain(reference_tail.iter().cloned()),
        )
        .env("PYTHONPATH", &python_path.to_string_lossy())
        .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
        // The frozen reference routes every larch child (timing report, run-log
        // writes, the failure-report gate) at the built binary.
        .env("LARCH_BINARY", binary)
        .env("LARCH_QUIET_DISABLE", "1")
        .env("LARCH_TEST_TIMING_NOW", "1787000000")
        .env("COLUMNS", "1000")
        .env("PATH", &path);
    let rust = Program::new(binary)
        .args(rust_tail.iter().cloned())
        .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
        .env("LARCH_BINARY", binary)
        .env("LARCH_QUIET_DISABLE", "1")
        .env("LARCH_TEST_TIMING_NOW", "1787000000")
        .env("COLUMNS", "1000")
        .env("PATH", &path);
    ParityCase {
        name,
        python,
        rust,
        seed_files: seeds,
        side_effect_records: Vec::new(),
        normalization: vec![
            NormalizationRule::SandboxRoot,
            NormalizationRule::Rfc3339Utc,
            NormalizationRule::ProcessIdentity,
        ],
    }
}

fn args(values: &[&str]) -> Vec<String> {
    values.iter().map(|value| (*value).to_owned()).collect()
}

const DESIGN_RELATIVE: &str = "design";
const MANIFEST_JSON: &str =
    "{\"main_model\": \"claude-opus-4-8\", \"larch_version\": \"57.0.7\", \"effort\": \"high\"}\n";
const TOKEN_REPORT_LEDGER: &str =
    include_str!("../../larch-core/tests/fixtures/token_scan/ledger.jsonl");
const TOKEN_REPORT_TRANSCRIPT: &str =
    include_str!("../../larch-core/tests/fixtures/token_scan/transcript.jsonl");

fn design_dir_seed() -> Vec<SeedFile> {
    vec![SeedFile::text(&format!("{DESIGN_RELATIVE}/.keep"), "")]
}

fn design_manifest_seed() -> Vec<SeedFile> {
    let mut seeds = design_dir_seed();
    seeds.push(SeedFile::text(
        &format!("{DESIGN_RELATIVE}/manifest.json"),
        MANIFEST_JSON,
    ));
    seeds
}

// ---------------------------------------------------------------------- gate

fn gate_case(name: &'static str, tail: &[&str], seeds: Vec<SeedFile>) -> ParityCase {
    let reference_tail = {
        let mut v = args(&["render-gate"]);
        v.extend(tail.iter().map(|value| (*value).to_owned()));
        v
    };
    let rust_tail = {
        let mut v = args(&["design", "render-gate"]);
        v.extend(tail.iter().map(|value| (*value).to_owned()));
        v
    };
    parity_case(name, &reference_tail, &rust_tail, seeds)
}

fn gate_cases() -> Vec<ParityCase> {
    vec![
        gate_case("design-gate-summary-gate-a", &["--gate", "A"], Vec::new()),
        gate_case(
            "design-gate-summary-gate-a-without-see-full-plan",
            &["--gate", "A", "--without-see-full-plan"],
            Vec::new(),
        ),
        gate_case(
            "design-gate-summary-gate-b-auto-apply",
            &["--gate", "B", "--accepted-count", "3"],
            Vec::new(),
        ),
        gate_case(
            "design-gate-summary-gate-b-approve",
            &["--gate", "B", "--approve-requested", "true"],
            Vec::new(),
        ),
        gate_case("design-gate-summary-gate-c", &["--gate", "C"], Vec::new()),
        gate_case("design-gate-summary-gate-help", &["--help"], Vec::new()),
        gate_case(
            "design-gate-summary-gate-c-panel-failed-escalation",
            &[
                "--gate",
                "C",
                "--panel-failed",
                "true",
                "--accepted-audit-escalation",
                "true",
            ],
            Vec::new(),
        ),
        gate_case(
            "design-gate-summary-gate-c-at-cap",
            &["--gate", "C", "--design-tmpdir", "{sandbox}/design"],
            vec![SeedFile::text(
                &format!("{DESIGN_RELATIVE}/review-round-count.txt"),
                "2",
            )],
        ),
        gate_case(
            "design-gate-summary-gate-c-nonnumeric-warn",
            &["--gate", "C", "--design-tmpdir", "{sandbox}/design"],
            vec![SeedFile::text(
                &format!("{DESIGN_RELATIVE}/review-round-count.txt"),
                "xx",
            )],
        ),
        gate_case(
            "design-gate-summary-gate-b-negative-count-error",
            &["--gate", "B", "--accepted-count", "-1"],
            Vec::new(),
        ),
        gate_case(
            "design-gate-summary-gate-invalid-choice-error",
            &["--gate", "D"],
            Vec::new(),
        ),
        gate_case(
            "design-gate-summary-gate-missing-required-error",
            &[],
            Vec::new(),
        ),
    ]
}

// ------------------------------------------------------------- final-summary

fn summary_case(name: &'static str, tail: &[&str], seeds: Vec<SeedFile>) -> ParityCase {
    let reference_tail = {
        let mut v = args(&["render-final-summary"]);
        v.extend(tail.iter().map(|value| (*value).to_owned()));
        v
    };
    let rust_tail = {
        let mut v = args(&["design", "render-final-summary"]);
        v.extend(tail.iter().map(|value| (*value).to_owned()));
        v
    };
    parity_case(name, &reference_tail, &rust_tail, seeds)
}

#[allow(clippy::too_many_lines)]
fn summary_cases() -> Vec<ParityCase> {
    let mut cases = Vec::new();
    // Unknown outcome: stderr + exit 2, no side effects.
    cases.push(summary_case(
        "design-gate-summary-final-invalid-outcome",
        &[
            "--design-tmpdir",
            "{sandbox}/design",
            "--outcome",
            "bogus-outcome",
        ],
        design_dir_seed(),
    ));
    // pre-phase approved: renders and counts without enrichment.
    cases.push(summary_case(
        "design-gate-summary-final-pre-approved",
        &[
            "--design-tmpdir",
            "{sandbox}/design",
            "--outcome",
            "approved",
            "--mode",
            "N/A",
            "--pre-publish-only",
            "--issue-number",
            "0",
        ],
        design_manifest_seed(),
    ));
    // post-phase approved: full enrichment path over an empty tmpdir.
    cases.push(summary_case(
        "design-gate-summary-final-post-approved",
        &[
            "--design-tmpdir",
            "{sandbox}/design",
            "--outcome",
            "approved",
            "--mode",
            "N/A",
            "--post-publish-only",
            "--issue-number",
            "0",
        ],
        design_manifest_seed(),
    ));
    // post-phase with missing-assessment markers and a Gate C guideline exception.
    {
        let mut seeds = design_manifest_seed();
        seeds.push(SeedFile::text(
            &format!("{DESIGN_RELATIVE}/.missing-invariant-assessment-warning"),
            "",
        ));
        seeds.push(SeedFile::text(
            &format!("{DESIGN_RELATIVE}/.missing-guideline-assessment-warning"),
            "",
        ));
        seeds.push(SeedFile::text(
            &format!("{DESIGN_RELATIVE}/architectural-guideline-assessment.md"),
            "Deviation summary line.\nException: keep the legacy shim for one release (author: main-agent, date: 2026-08-20)\n",
        ));
        cases.push(summary_case(
            "design-gate-summary-final-post-markers-exception",
            &[
                "--design-tmpdir",
                "{sandbox}/design",
                "--outcome",
                "approved",
                "--mode",
                "N/A",
                "--post-publish-only",
                "--issue-number",
                "0",
            ],
            seeds,
        ));
    }
    // post-phase with OOS rows and an execution-issues section to enrich.
    {
        let mut seeds = design_manifest_seed();
        seeds.push(SeedFile::text(
            &format!("{DESIGN_RELATIVE}/oos-issues-created.md"),
            "OOS_FILE_MAP\tfile.py\thttps://github.com/o/r/issues/9\n",
        ));
        seeds.push(SeedFile::text(
            &format!("{DESIGN_RELATIVE}/execution-issues.md"),
            "## Exec Issues\n- **1** thing happened\n",
        ));
        cases.push(summary_case(
            "design-gate-summary-final-post-oos-execissues",
            &[
                "--design-tmpdir",
                "{sandbox}/design",
                "--outcome",
                "approved",
                "--mode",
                "N/A",
                "--post-publish-only",
                "--issue-number",
                "0",
            ],
            seeds,
        ));
    }
    // post-phase skip-summary-upsert with an issue/repo present.
    cases.push(summary_case(
        "design-gate-summary-final-post-skip-upsert",
        &[
            "--design-tmpdir",
            "{sandbox}/design",
            "--outcome",
            "approved",
            "--mode",
            "N/A",
            "--post-publish-only",
            "--skip-summary-upsert",
            "--issue-number",
            "42",
            "--repo",
            "o/r",
        ],
        design_manifest_seed(),
    ));
    cases
}

fn all_cases() -> Vec<ParityCase> {
    let mut cases = Vec::new();
    cases.extend(gate_cases());
    cases.extend(summary_cases());
    cases
}

#[test]
fn design_gate_summary_migrated_parity() {
    let goldens = fixture_directory().join("goldens");
    for case in all_cases() {
        let golden = goldens.join(format!("{}.golden.json", case.name));
        if let Err(error) = assert_rust_golden_case(&case, &golden) {
            panic!("{error}");
        }
    }
}

#[test]
fn design_gate_summary_refreshes_token_report_and_consumes_buckets() {
    let directory = tempfile::tempdir().expect("temporary root");
    let root = directory.path().canonicalize().expect("canonical root");
    let design_tmpdir = root.join(DESIGN_RELATIVE);
    fs::create_dir(&design_tmpdir).expect("design tmpdir");
    fs::write(design_tmpdir.join("manifest.json"), MANIFEST_JSON).expect("manifest");

    let ledger = root.join("token-ledger.jsonl");
    let transcript = root.join("transcript.jsonl");
    let source = root.join("claude-source.env");
    fs::write(&ledger, TOKEN_REPORT_LEDGER).expect("token ledger");
    fs::write(&transcript, TOKEN_REPORT_TRANSCRIPT).expect("Claude transcript");
    fs::write(
        &source,
        format!(
            "TRANSCRIPT_PATH={}\nSESSION_DIR={}\nSESSION_UUID=fixture-session\n",
            transcript.display(),
            root.display()
        ),
    )
    .expect("Claude source snapshot");

    let binary = env!("CARGO_BIN_EXE_larch");
    let output = Command::new(binary)
        .current_dir(&root)
        .env("CLAUDE_PLUGIN_ROOT", repository_root())
        .env("LARCH_BINARY", binary)
        .env("LARCH_CLAUDE_SOURCE_FILE", &source)
        .env("LARCH_QUIET_DISABLE", "1")
        .env("LARCH_TOKEN_LEDGER", &ledger)
        .env("DESIGN_TMPDIR", &design_tmpdir)
        .env("SESSION_ID", "design-token-refresh")
        .env("TMPDIR", &root)
        .args([
            "design",
            "render-final-summary",
            "--design-tmpdir",
            design_tmpdir.to_str().expect("design tmpdir UTF-8"),
            "--outcome",
            "approved",
            "--mode",
            "N/A",
            "--pre-publish-only",
            "--issue-number",
            "0",
        ])
        .output()
        .expect("render final summary");
    assert!(
        output.status.success(),
        "stdout={}\nstderr={}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );

    let report_path = design_tmpdir.join("token-report-final.json");
    let report: serde_json::Value = serde_json::from_str(
        &fs::read_to_string(&report_path).expect("refreshed token report"),
    )
    .expect("token report JSON");
    assert_eq!(report["BUCKETS_codex"]["input"], 1007);

    let summary = fs::read_to_string(design_tmpdir.join("final-summary.md"))
        .expect("rendered final summary");
    assert!(summary.contains("Tokens: 2k"), "{summary}");
    assert!(!summary.contains("- **Cost**: N/A"), "{summary}");
}
