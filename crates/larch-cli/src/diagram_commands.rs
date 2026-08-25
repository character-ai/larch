//! Rust-owned diagram commands.
//!
//! Hosts the Mermaid sanitizer and marker-comment diagram upsert alongside the
//! shared Rust owner for `diagram code-flow` (#8839) and
//! `implement code-flow-diagram` (#8933).
//!
//! `diagram code-flow` ports Python `larch.git.pr_body.generate_code_flow_diagram` +
//! `generate_code_flow_diagram_main`: resolve the committed diff, author the
//! prompt, launch `agent launch-claude-subprocess` (honoring the
//! `LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS` override), retry transient failures with
//! the `code-flow-diagram.retried` sidecar, capture bounded failure logs through
//! the reused `report::diagram_log` owner, sanitize the candidate with the reused
//! `ship_pr` mermaid validator, and emit the `STATUS`/`DIAGRAM_FILE`/`SKIP_REASON`
//! KV contract. `/implement` Step 7a and both CLI selectors reach this
//! in-process owner, satisfying I-Cutover-1 with no bridge.

use std::{
    collections::BTreeSet,
    env,
    ffi::OsString,
    fs,
    io::{self, Read as _},
    path::{Path, PathBuf},
    process::{Command, ExitCode, Stdio},
    sync::LazyLock,
    thread,
    time::Duration,
};

use larch_adapters::GixRepository;
use larch_core::{
    DIAGRAMS_COMMENT_MARKER, ProcessOutput, RepositoryRead as _, Revision, code_flow_reject_reason,
    design::extract_diagram_sections,
    emit_kv,
    mermaid::inspect_mermaid,
    read_kv_from_text, redact,
    report::{sanitize_diagram_capture, strip_diagram_sections, write_bounded_diagram_failure_log},
};
use regex::Regex;

use crate::{
    argparse_compat::{ParsedCommandLine, parse_required_with_help, parse_with_flags},
    launcher_support::read_confined_bytes_checked,
    runtime_entrypoint::run_verified_larch,
    tracking_issue_commands::{
        read_summary_content, summary_marker_valid, upsert_summary_content_rows,
    },
};

const MERMAID_OPTIONS: &[&str] = &["--input", "--warnings-log", "--warnings-step"];
const DIAGRAM_OPTIONS: &[&str] = &[
    "--issue",
    "--repo",
    "--architecture-file",
    "--code-flow-file",
    "--marker",
];

/// Inspect a Mermaid fragment or Markdown document.
pub fn mermaid_sanitize(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(arguments, MERMAID_OPTIONS, &["--from-md"], 0);
    if parsed.error().is_some() || parsed.value_error().is_some() {
        println!("STATUS=internal-error\nERROR=usage: unknown flag");
        return ExitCode::from(2);
    }
    let input = value(&parsed, "--input");
    let text = if input.is_empty() {
        let mut text = String::new();
        if io::stdin().read_to_string(&mut text).is_err() {
            println!("STATUS=internal-error\nERROR=unreadable input");
            return ExitCode::from(2);
        }
        text
    } else {
        let path = Path::new(&input);
        let Ok(text) = read_regular_lossy(path, false) else {
            println!("STATUS=internal-error\nERROR=unreadable input");
            return ExitCode::from(2);
        };
        text
    };
    let first_nonblank = text
        .lines()
        .find(|line| !line.trim().is_empty())
        .unwrap_or("");
    let from_markdown = parsed.flag("--from-md") || first_nonblank == "```mermaid";
    let (fences, reasons) = inspect_mermaid(&text, from_markdown);
    if reasons.is_empty() {
        println!("STATUS=ok");
    } else {
        println!("STATUS=rejected");
        for reason in &reasons {
            println!(
                "REASON_TOKEN={} fence={} line={}",
                reason.token, reason.fence, reason.line
            );
        }
    }
    println!("FENCE_COUNT={}", fences.len());
    if from_markdown {
        for (index, fence) in fences.iter().enumerate() {
            println!("FENCE_{}_HEADING={}", index + 1, fence.heading);
        }
    }
    if reasons.is_empty() {
        ExitCode::SUCCESS
    } else {
        append_mermaid_warning(&parsed, &reasons);
        ExitCode::FAILURE
    }
}

fn append_mermaid_warning(
    parsed: &ParsedCommandLine,
    reasons: &[larch_core::mermaid::MermaidReason],
) {
    let log = value(parsed, "--warnings-log");
    if log.is_empty() {
        return;
    }
    let tokens = reasons
        .iter()
        .map(|reason| reason.token)
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect::<Vec<_>>()
        .join(" ");
    let step = value(parsed, "--warnings-step");
    let step = if step.is_empty() { "unknown" } else { &step };
    let entry = format!("- **Step {step} — mermaid sanitizer rejected:** {tokens}");
    let _ignored = run_verified_larch(&[
        "run-log".into(),
        "append-entry".into(),
        "--log".into(),
        log.into(),
        "--category".into(),
        "Warnings".into(),
        "--entry".into(),
        entry.into(),
    ]);
}

/// Preserve or replace Architecture and Code Flow sections in one comment.
pub fn diagrams_upsert(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        DIAGRAM_OPTIONS,
        &[
            "--clear-architecture",
            "--clear-code-flow",
            "--allow-external-paths",
            "--dry-run",
        ],
        0,
    );
    if parsed.error().is_some() || parsed.value_error().is_some() {
        return upsert_failure("2", 1);
    }
    match diagrams_upsert_result(&parsed) {
        Ok(output) => {
            print!("{}", output.body);
            emit_upsert_rows(
                output.status,
                &output.comment_url,
                output.updated,
                output.architecture_source,
                output.code_flow_source,
            );
            ExitCode::SUCCESS
        }
        Err((message, code)) => upsert_failure(&message, code),
    }
}

#[derive(Debug)]
struct DiagramOutput {
    body: String,
    status: &'static str,
    comment_url: String,
    updated: bool,
    architecture_source: &'static str,
    code_flow_source: &'static str,
}

#[allow(clippy::too_many_lines)] // The ordered legacy validation and output pipeline is byte-sensitive.
fn diagrams_upsert_result(parsed: &ParsedCommandLine) -> Result<DiagramOutput, (String, u8)> {
    let issue = value(parsed, "--issue");
    if issue.is_empty() || !issue.chars().all(|character| character.is_ascii_digit()) {
        return Err(("invalid issue".to_owned(), 1));
    }
    let marker = value(parsed, "--marker");
    let marker = if marker.is_empty() {
        DIAGRAMS_COMMENT_MARKER
    } else {
        &marker
    };
    if !summary_marker_valid(marker) {
        return Err((format!("invalid marker: {marker}"), 1));
    }
    let architecture_file = value(parsed, "--architecture-file");
    let code_flow_file = value(parsed, "--code-flow-file");
    let clear_architecture = parsed.flag("--clear-architecture");
    let clear_code_flow = parsed.flag("--clear-code-flow");
    if !architecture_file.is_empty() && clear_architecture {
        return Err((
            "--architecture-file and --clear-architecture are mutually exclusive".to_owned(),
            1,
        ));
    }
    if !code_flow_file.is_empty() && clear_code_flow {
        return Err((
            "--code-flow-file and --clear-code-flow are mutually exclusive".to_owned(),
            1,
        ));
    }
    if architecture_file.is_empty()
        && code_flow_file.is_empty()
        && !clear_architecture
        && !clear_code_flow
    {
        return Err(("at least one section mode is required".to_owned(), 1));
    }
    if !parsed.flag("--allow-external-paths") {
        assert_temporary_path("architecture", &architecture_file)?;
        assert_temporary_path("code-flow", &code_flow_file)?;
    }
    let repository = value(parsed, "--repo");
    let repository = (!repository.is_empty()).then_some(repository.as_str());
    let dry_run = parsed.flag("--dry-run");
    let require_temporary = !parsed.flag("--allow-external-paths");
    let existing = if dry_run {
        None
    } else {
        read_summary_content(&issue, marker, repository).map_err(|error| (error, 2))?
    };
    let (architecture_existing, code_flow_existing) =
        extract_diagram_sections(existing.as_deref().unwrap_or(""))
            .map_err(|error| (error.to_owned(), 2))?;
    let (architecture, architecture_source) = resolve_section(
        "architecture",
        &architecture_file,
        clear_architecture,
        &architecture_existing,
        require_temporary,
    )?;
    let (code_flow, code_flow_source) = resolve_section(
        "code-flow",
        &code_flow_file,
        clear_code_flow,
        &code_flow_existing,
        require_temporary,
    )?;
    sanitize_section("architecture", &architecture)?;
    sanitize_section("code-flow", &code_flow)?;
    let sections = [architecture.as_str(), code_flow.as_str()]
        .into_iter()
        .filter(|section| !section.is_empty())
        .collect::<Vec<_>>()
        .join("\n\n");
    let sections = redact(&sections).text().trim_end_matches('\n').to_owned();
    if dry_run {
        return Ok(DiagramOutput {
            body: format!("{marker}\n\n{sections}\n\n--- content-file ---\n{sections}"),
            status: "ok",
            comment_url: String::new(),
            updated: false,
            architecture_source,
            code_flow_source,
        });
    }
    if sections.is_empty() && existing.is_none() {
        return Ok(DiagramOutput {
            body: String::new(),
            status: "no-op",
            comment_url: String::new(),
            updated: false,
            architecture_source: cleared_to_absent(architecture_source),
            code_flow_source: cleared_to_absent(code_flow_source),
        });
    }
    let rows = upsert_summary_content_rows(&issue, marker, &sections, repository, true)
        .map_err(|error| (error, 2))?;
    Ok(DiagramOutput {
        body: String::new(),
        status: "ok",
        comment_url: row_value(&rows, "COMMENT_URL"),
        updated: row_value(&rows, "UPDATED") == "true",
        architecture_source,
        code_flow_source,
    })
}

fn value(parsed: &ParsedCommandLine, name: &str) -> String {
    parsed
        .value(name)
        .map_or_else(String::new, |value| value.to_string_lossy().into_owned())
}

fn resolve_section(
    label: &str,
    new_file: &str,
    clear: bool,
    existing: &str,
    require_temporary: bool,
) -> Result<(String, &'static str), (String, u8)> {
    if clear {
        return Ok((String::new(), "cleared"));
    }
    if !new_file.is_empty()
        && Path::new(new_file).is_file()
        && fs::metadata(new_file).is_ok_and(|metadata| metadata.len() > 0)
    {
        return Ok((
            read_regular_lossy(Path::new(new_file), require_temporary)
                .map_err(|()| (format!("{label} file not readable"), 1))?
                .trim_end_matches('\n')
                .to_owned(),
            "new",
        ));
    }
    if !existing.is_empty() {
        return Ok((existing.to_owned(), "preserved"));
    }
    Ok((String::new(), "absent"))
}

fn read_regular_lossy(path: &Path, require_temporary: bool) -> Result<String, ()> {
    let path = canonical_leaf(path).ok_or(())?;
    if require_temporary && !under_temporary_root(&path) {
        return Err(());
    }
    read_confined_bytes_checked(&path)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .map_err(drop)
}

fn sanitize_section(label: &str, content: &str) -> Result<(), (String, u8)> {
    if content.is_empty() {
        return Ok(());
    }
    let (_fences, reasons) = inspect_mermaid(content, true);
    if reasons.is_empty() {
        Ok(())
    } else {
        Err((format!("mermaid sanitize rejected {label} section"), 1))
    }
}

fn assert_temporary_path(label: &str, value: &str) -> Result<(), (String, u8)> {
    if value.is_empty() {
        return Ok(());
    }
    let path = Path::new(value);
    if !path.is_file()
        || fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_symlink())
    {
        return Err((format!("{label} file not readable"), 1));
    }
    if under_temporary_root(path) {
        return Ok(());
    }
    Err((
        format!(
            "{label} file must be under an allowed temporary root (or pass --allow-external-paths)"
        ),
        1,
    ))
}

fn under_temporary_root(path: &Path) -> bool {
    let Some(canonical) = canonical_leaf(path) else {
        return false;
    };
    let mut roots = vec![PathBuf::from("/tmp"), PathBuf::from("/private/tmp")];
    if let Some(tmpdir) = env::var_os("TMPDIR").filter(|value| !value.is_empty()) {
        roots.push(expand_user(Path::new(&tmpdir)));
    }
    if let Some(xdg) = env::var_os("XDG_CACHE_HOME").filter(|value| !value.is_empty()) {
        roots.push(expand_user(Path::new(&xdg)).join("larch/sessions"));
    }
    if let Some(home) = env::var_os("HOME").filter(|value| !value.is_empty()) {
        roots.push(expand_user(Path::new(&home)).join(".cache/larch/sessions"));
    }
    roots.into_iter().any(|root| {
        let root = canonical_existing_prefix(&root);
        canonical == root || canonical.starts_with(root)
    })
}

fn canonical_leaf(path: &Path) -> Option<PathBuf> {
    let parent = path
        .parent()
        .filter(|path| !path.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    Some(fs::canonicalize(parent).ok()?.join(path.file_name()?))
}

fn canonical_existing_prefix(path: &Path) -> PathBuf {
    let mut ancestor = path;
    let mut tail = Vec::new();
    while !ancestor.exists() {
        let Some(name) = ancestor.file_name() else {
            break;
        };
        tail.push(name.to_owned());
        let Some(parent) = ancestor.parent() else {
            break;
        };
        ancestor = parent;
    }
    let mut resolved = fs::canonicalize(ancestor).unwrap_or_else(|_| ancestor.to_path_buf());
    for component in tail.into_iter().rev() {
        resolved.push(component);
    }
    resolved
}

fn expand_user(path: &Path) -> PathBuf {
    let text = path.to_string_lossy();
    if text == "~" {
        return env::var_os("HOME").map_or_else(|| path.to_path_buf(), PathBuf::from);
    }
    if let Some(tail) = text.strip_prefix("~/")
        && let Some(home) = env::var_os("HOME")
    {
        return PathBuf::from(home).join(tail);
    }
    path.to_path_buf()
}

fn row_value(rows: &[(&'static str, String)], key: &str) -> String {
    rows.iter()
        .rev()
        .find(|(name, _)| *name == key)
        .map_or_else(String::new, |(_, value)| value.clone())
}

fn cleared_to_absent(source: &'static str) -> &'static str {
    if source == "cleared" {
        "absent"
    } else {
        source
    }
}

fn emit_upsert_rows(
    status: &str,
    comment_url: &str,
    updated: bool,
    architecture_source: &str,
    code_flow_source: &str,
) {
    println!("UPSERT_STATUS={status}");
    println!("COMMENT_URL={comment_url}");
    println!("UPDATED={}", if updated { "true" } else { "false" });
    println!("ARCHITECTURE_SOURCE={architecture_source}");
    println!("CODE_FLOW_SOURCE={code_flow_source}");
}

fn upsert_failure(message: &str, code: u8) -> ExitCode {
    emit_upsert_rows("failed", "", false, "absent", "absent");
    println!("ERROR={}", message.replace(['\n', '\r'], " "));
    ExitCode::from(code)
}

const CODE_FLOW_PROG: &str = "cli.py diagram code-flow";
const CODE_FLOW_USAGE: &str = "usage: cli.py diagram code-flow [-h] --implement-tmpdir IMPLEMENT_TMPDIR\n                                [--model MODEL] [--base-remote BASE_REMOTE]\n                                [--base-ref BASE_REF]";
const CODE_FLOW_HELP: &str = "usage: cli.py diagram code-flow [-h] --implement-tmpdir IMPLEMENT_TMPDIR\n                                [--model MODEL] [--base-remote BASE_REMOTE]\n                                [--base-ref BASE_REF]\n\noptions:\n  -h, --help            show this help message and exit\n  --implement-tmpdir IMPLEMENT_TMPDIR\n  --model MODEL\n  --base-remote BASE_REMOTE\n  --base-ref BASE_REF\n";

const IMPLEMENT_CODE_FLOW_USAGE: &str = "Usage: scripts/larch.sh implement code-flow-diagram --implement-tmpdir PATH [--model claude-sonnet-4-6] [--base-remote NAME] [--base-ref BRANCH]";

const DEFAULT_MODEL: &str = "claude-sonnet-4-6";
const CODE_FLOW_DIAGRAM_TIMEOUT_SECONDS: u32 = 180;
const MAX_DIAGRAM_RETRIES: usize = 4;
const DIAGRAM_RETRY_DELAY_SECONDS: u64 = 10;
const DIAGRAM_FAILURE_TAIL_LIMIT: usize = 200;
const EXIT_TIMEOUT: i32 = 124;

static LAUNCHER_FAILURE_LABEL_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[A-Za-z0-9_-]+$").expect("static launcher-label regex"));
static WHITESPACE_RUN: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"\s+").expect("static whitespace-run regex"));

/// The outcome of one code-flow generation attempt.
pub struct CodeFlowDiagramResult {
    /// Process exit code (`1` on generation-failed or empty-generation, else `0`).
    pub exit_code: i32,
    /// Contract status (`ok`, `skipped`, or `failed`).
    pub status: String,
    /// Path to the accepted diagram file, empty unless `status == "ok"`.
    pub diagram_file: String,
    /// Skip or failure reason token, empty on success.
    pub reason: String,
}

#[cfg(test)]
type DiagramHook =
    std::sync::Arc<dyn Fn(&Path, &str, &str, &str) -> CodeFlowDiagramResult + Send + Sync>;

#[cfg(test)]
std::thread_local! {
    static TEST_DIAGRAM: std::cell::RefCell<Option<DiagramHook>> = const { std::cell::RefCell::new(None) };
}

/// Answer every `generate_code_flow_diagram` call from `hook` (test only).
#[cfg(test)]
pub fn install_test_diagram(
    hook: impl Fn(&Path, &str, &str, &str) -> CodeFlowDiagramResult + Send + Sync + 'static,
) {
    TEST_DIAGRAM.with(|slot| *slot.borrow_mut() = Some(std::sync::Arc::new(hook)));
}

/// `diagram code-flow` CLI handler.
pub fn code_flow(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        CODE_FLOW_PROG,
        CODE_FLOW_USAGE,
        CODE_FLOW_HELP,
        &[
            "--implement-tmpdir",
            "--model",
            "--base-remote",
            "--base-ref",
        ],
        &[],
        &["--implement-tmpdir"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let value = |name: &str, default: &str| -> String {
        parsed
            .value(name)
            .map(|value| value.to_string_lossy().into_owned())
            .filter(|value| !value.is_empty())
            .unwrap_or_else(|| default.to_owned())
    };
    let tmpdir = PathBuf::from(value("--implement-tmpdir", ""));
    let model = value("--model", DEFAULT_MODEL);
    let base_remote = value("--base-remote", "origin");
    let base_ref = value("--base-ref", "main");
    let result = generate_code_flow_diagram(&tmpdir, &model, &base_remote, &base_ref);
    emit_kv("STATUS", &result.status);
    emit_kv("DIAGRAM_FILE", &result.diagram_file);
    emit_kv("SKIP_REASON", &result.reason);
    ExitCode::from(u8::try_from(result.exit_code).unwrap_or(1))
}

/// `implement code-flow-diagram` CLI handler.
///
/// This preserves the retired Bash helper's option validation and machine
/// stdout envelope while delegating generation to the existing Rust owner.
pub fn implement_code_flow_diagram(arguments: &[OsString]) -> ExitCode {
    let mut tmpdir = OsString::new();
    let mut model = OsString::from(DEFAULT_MODEL);
    let mut base_remote = OsString::from("origin");
    let mut base_ref = OsString::from("main");
    let mut index = 0;
    while index < arguments.len() {
        let option = arguments[index].to_string_lossy();
        match option.as_ref() {
            "--implement-tmpdir" | "--model" | "--base-remote" | "--base-ref" => {
                let Some(value) = arguments.get(index + 1) else {
                    return implement_code_flow_usage_failure(&format!(
                        "{option} requires a value"
                    ));
                };
                match option.as_ref() {
                    "--implement-tmpdir" => tmpdir.clone_from(value),
                    "--model" => model.clone_from(value),
                    "--base-remote" => base_remote.clone_from(value),
                    "--base-ref" => base_ref.clone_from(value),
                    _ => unreachable!("matched code-flow option"),
                }
                index += 2;
            }
            "--help" => {
                eprintln!("{IMPLEMENT_CODE_FLOW_USAGE}");
                return ExitCode::SUCCESS;
            }
            _ => {
                return implement_code_flow_usage_failure(&format!("unknown option: {option}"));
            }
        }
    }

    if tmpdir.is_empty() {
        return implement_code_flow_usage_failure("--implement-tmpdir is required");
    }
    let tmpdir = PathBuf::from(tmpdir);
    if !tmpdir.is_absolute() {
        return implement_code_flow_usage_failure("--implement-tmpdir must be absolute");
    }
    let model = model.to_string_lossy();
    let base_remote = base_remote.to_string_lossy();
    let base_ref = base_ref.to_string_lossy();
    if !valid_code_flow_base_component(&base_remote) {
        return implement_code_flow_usage_failure("--base-remote must match ^[A-Za-z0-9._/-]+$");
    }
    if !valid_code_flow_base_component(&base_ref) {
        return implement_code_flow_usage_failure("--base-ref must match ^[A-Za-z0-9._/-]+$");
    }
    if fs::create_dir_all(&tmpdir).is_err() {
        emit_code_flow_result(&CodeFlowDiagramResult {
            exit_code: 1,
            status: "failed".to_owned(),
            diagram_file: String::new(),
            reason: "tmpdir-unavailable".to_owned(),
        });
        return ExitCode::FAILURE;
    }

    let result = generate_code_flow_diagram(&tmpdir, &model, &base_remote, &base_ref);
    emit_code_flow_result(&result);
    ExitCode::from(u8::try_from(result.exit_code).unwrap_or(1))
}

fn valid_code_flow_base_component(value: &str) -> bool {
    !value.is_empty()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'/' | b'-'))
}

fn implement_code_flow_usage_failure(reason: &str) -> ExitCode {
    eprintln!("{IMPLEMENT_CODE_FLOW_USAGE}");
    emit_code_flow_result(&CodeFlowDiagramResult {
        exit_code: 2,
        status: "failed".to_owned(),
        diagram_file: String::new(),
        reason: reason.replace(['\n', '\r'], " "),
    });
    ExitCode::from(2)
}

fn emit_code_flow_result(result: &CodeFlowDiagramResult) {
    emit_kv("STATUS", &result.status);
    emit_kv("DIAGRAM_FILE", &result.diagram_file);
    emit_kv("SKIP_REASON", &result.reason);
}

/// Generate the committed-diff code-flow diagram (Python `generate_code_flow_diagram`).
pub fn generate_code_flow_diagram(
    tmpdir: &Path,
    model: &str,
    base_remote: &str,
    base_ref: &str,
) -> CodeFlowDiagramResult {
    #[cfg(test)]
    if let Some(hook) = TEST_DIAGRAM.with(|slot| slot.borrow().clone()) {
        return hook(tmpdir, model, base_remote, base_ref);
    }
    let _ = fs::create_dir_all(tmpdir);
    let raw = tmpdir.join("code-flow-diagram.raw.md");
    let candidate = tmpdir.join("code-flow-diagram.candidate.md");
    let diagram = tmpdir.join("code-flow-diagram.md");
    let prompt_path = tmpdir.join("code-flow-prompt.md");
    let failure_log = tmpdir.join("code-flow-diagram.failure.log");
    let retry_sidecar = tmpdir.join("code-flow-diagram.retried");
    let raw_failure = tmpdir.join("code-flow-diagram.raw-failure.log");
    let launch_stdout = tmpdir.join("code-flow-launch.out");
    let launch_stderr = tmpdir.join("code-flow-launch.err");
    let sanitizer_log = tmpdir.join("code-flow-sanitizer.failure.log");

    let changed = resolve_changed_files(base_remote, base_ref);
    let mut prompt_lines = vec![
        "Generate a concise Mermaid code-flow diagram for the committed implementation diff."
            .to_owned(),
        "Return markdown containing exactly one `## Code Flow Diagram` heading and one mermaid fence."
            .to_owned(),
        "Focus on runtime calls, data flow, and control flow. Avoid structural architecture duplication."
            .to_owned(),
        String::new(),
        "Changed files:".to_owned(),
    ];
    prompt_lines.extend(changed);
    prompt_lines.push(String::new());
    let _ = fs::write(&prompt_path, prompt_lines.join("\n"));
    let _ = fs::remove_file(&failure_log);

    let launch = run_diagram_subprocess(model, &prompt_path, &raw, &retry_sidecar);
    let _ = fs::write(&launch_stdout, &launch.stdout);
    let _ = fs::write(&launch_stderr, &launch.stderr);
    if launch.code != 0 {
        return launch_failure_result(tmpdir, &failure_log, &raw_failure, &raw, &launch);
    }
    finalize_candidate(
        &raw,
        &candidate,
        &diagram,
        &failure_log,
        &raw_failure,
        &sanitizer_log,
    )
}

/// Compose the `generation-failed` result and write the bounded failure log
/// (Python `generate_code_flow_diagram` non-zero branch).
fn launch_failure_result(
    tmpdir: &Path,
    failure_log: &Path,
    raw_failure: &Path,
    raw: &Path,
    launch: &LaunchOutcome,
) -> CodeFlowDiagramResult {
    let raw_capture_ok = fs::write(
        raw_failure,
        format!("stderr:\n{}\nstdout:\n{}\n", launch.stderr, launch.stdout),
    )
    .is_ok();
    let stderr = diagram_stderr_from_sidecar(raw, &launch.stderr);
    let (diagnostic, tail) = diagram_failure_capture(launch.code, &stderr);
    let failure_label = launcher_failure_label(&launch.stdout);
    let mut reason = if failure_label.is_empty() {
        format!("generation-failed rc={} tail={tail}", launch.code)
    } else {
        format!(
            "generation-failed {failure_label} rc={} tail={tail}",
            launch.code
        )
    };
    let write_result: std::io::Result<()> = (|| {
        if raw_capture_ok {
            let bounded = write_bounded_diagram_failure_log(
                tmpdir,
                "implement Step 7a",
                &reason,
                &launch.code.to_string(),
                Some(raw_failure),
            )?;
            if bounded != *failure_log {
                let body = fs::read_to_string(&bounded)?;
                fs::write(failure_log, body)?;
            }
            let _ = fs::remove_file(raw_failure);
            Ok(())
        } else {
            fs::write(failure_log, &diagnostic)
        }
    })();
    if write_result.is_err() {
        reason = format!("{reason} log-write-failed");
    }
    CodeFlowDiagramResult {
        exit_code: 1,
        status: "failed".to_owned(),
        diagram_file: String::new(),
        reason,
    }
}

/// Sanitize the generated candidate and finalize the diagram (Python
/// `generate_code_flow_diagram` success branch).
fn finalize_candidate(
    raw: &Path,
    candidate: &Path,
    diagram: &Path,
    failure_log: &Path,
    raw_failure: &Path,
    sanitizer_log: &Path,
) -> CodeFlowDiagramResult {
    let empty_generation = || CodeFlowDiagramResult {
        exit_code: 1,
        status: "failed".to_owned(),
        diagram_file: String::new(),
        reason: "empty-generation".to_owned(),
    };
    if !file_has_bytes(raw) {
        return empty_generation();
    }
    let Ok(raw_bytes) = fs::read(raw) else {
        return empty_generation();
    };
    if fs::write(candidate, &raw_bytes).is_err() {
        return CodeFlowDiagramResult {
            exit_code: 1,
            status: "failed".to_owned(),
            diagram_file: String::new(),
            reason: "candidate-write-failed".to_owned(),
        };
    }
    let text = String::from_utf8_lossy(&raw_bytes);
    let rejection = code_flow_reject_reason(&text);
    let sanitizer_record = rejection.map_or_else(
        || "STATUS=ok\n".to_owned(),
        |reason| format!("STATUS=rejected\nREASON_TOKEN={reason}\n"),
    );
    let _ = fs::write(sanitizer_log, sanitizer_record);
    rejection.map_or_else(
        || {
            if fs::rename(candidate, diagram).is_err() {
                return CodeFlowDiagramResult {
                    exit_code: 1,
                    status: "failed".to_owned(),
                    diagram_file: String::new(),
                    reason: "candidate-write-failed".to_owned(),
                };
            }
            let _ = fs::remove_file(failure_log);
            let _ = fs::remove_file(raw_failure);
            CodeFlowDiagramResult {
                exit_code: 0,
                status: "ok".to_owned(),
                diagram_file: diagram.display().to_string(),
                reason: String::new(),
            }
        },
        |reason| {
            let _ = fs::remove_file(candidate);
            CodeFlowDiagramResult {
                exit_code: 0,
                status: "skipped".to_owned(),
                diagram_file: String::new(),
                reason: reason.to_owned(),
            }
        },
    )
}

/// One completed launch attempt: exit code and captured streams.
struct LaunchOutcome {
    code: i32,
    stdout: String,
    stderr: String,
}

/// Run the launcher, retrying transient failures (Python `_run_diagram_subprocess`).
fn run_diagram_subprocess(
    model: &str,
    prompt_path: &Path,
    raw: &Path,
    retry_sidecar: &Path,
) -> LaunchOutcome {
    let mut outcome = launch_once(model, prompt_path, raw);
    if !needs_diagram_retry(outcome.code, raw) {
        return outcome;
    }
    let first_rc = outcome.code;
    let mut retry_rcs: Vec<i32> = Vec::new();
    for _ in 1..=MAX_DIAGRAM_RETRIES {
        thread::sleep(Duration::from_secs(retry_delay_seconds()));
        let _ = fs::remove_file(raw);
        outcome = launch_once(model, prompt_path, raw);
        retry_rcs.push(outcome.code);
        if !needs_diagram_retry(outcome.code, raw) {
            break;
        }
    }
    let mut lines = vec![format!("FIRST_RC={first_rc}")];
    for (index, rc) in retry_rcs.iter().enumerate() {
        lines.push(format!("RETRY_{}_RC={rc}", index + 1));
    }
    lines.push(format!("RETRIES={}", retry_rcs.len()));
    let _ = fs::write(retry_sidecar, lines.join("\n") + "\n");
    outcome
}

/// Retry delay, overridable only in debug/test builds so parity tests stay fast.
fn retry_delay_seconds() -> u64 {
    #[cfg(debug_assertions)]
    if let Ok(value) = env::var("LARCH_TEST_DIAGRAM_RETRY_DELAY_SECONDS")
        && let Ok(seconds) = value.trim().parse::<u64>()
    {
        return seconds;
    }
    DIAGRAM_RETRY_DELAY_SECONDS
}

/// Whether the attempt warrants a retry (Python `_needs_diagram_retry`).
fn needs_diagram_retry(code: i32, raw: &Path) -> bool {
    code == EXIT_TIMEOUT
        || fs::metadata(raw).is_ok_and(|metadata| metadata.is_file() && metadata.len() == 0)
}

/// Launch one code-flow subprocess (Python `_code_flow_launch_cmd` + `subprocess.run`).
fn launch_once(model: &str, prompt_path: &Path, raw: &Path) -> LaunchOutcome {
    let cwd = env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    let tail: Vec<OsString> = vec![
        OsString::from("--model"),
        OsString::from(model),
        OsString::from("--prompt-file"),
        prompt_path.as_os_str().to_owned(),
        OsString::from("--output-file"),
        raw.as_os_str().to_owned(),
        OsString::from("--timeout"),
        OsString::from(CODE_FLOW_DIAGRAM_TIMEOUT_SECONDS.to_string()),
        OsString::from("--allow-root"),
        cwd.as_os_str().to_owned(),
        OsString::from("--timing-task-kind"),
        OsString::from("implement-code-flow"),
    ];
    if let Some(launcher) =
        env::var_os("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS").filter(|value| !value.is_empty())
    {
        let output = Command::new(&launcher) // lint-subprocess-via-runner: ok the override names an operator-supplied launcher double, which has no typed first-party program
            .args(&tail)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .output();
        return match output {
            Ok(output) => LaunchOutcome {
                code: output.status.code().unwrap_or(1),
                stdout: String::from_utf8_lossy(&output.stdout).into_owned(),
                stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
            },
            Err(_error) => LaunchOutcome {
                code: 1,
                stdout: String::new(),
                stderr: String::new(),
            },
        };
    }
    let mut argv: Vec<OsString> = vec![
        OsString::from("agent"),
        OsString::from("launch-claude-subprocess"),
    ];
    argv.extend(tail);
    launch_from_output(run_verified_larch(&argv))
}

/// Reduce a verified-larch result to a `LaunchOutcome`.
fn launch_from_output(result: Result<ProcessOutput, String>) -> LaunchOutcome {
    let Ok(output) = result else {
        return LaunchOutcome {
            code: 1,
            stdout: String::new(),
            stderr: String::new(),
        };
    };
    let stdout = String::from_utf8_lossy(output.stdout()).into_owned();
    let stderr = String::from_utf8_lossy(output.stderr()).into_owned();
    let code = output.status().code().unwrap_or(1);
    LaunchOutcome {
        code,
        stdout,
        stderr,
    }
}

/// Prefer the `.stderr` sidecar the launcher writes (Python `_diagram_stderr_from_sidecar`).
fn diagram_stderr_from_sidecar(raw: &Path, fallback: &str) -> String {
    let mut sidecar = raw.as_os_str().to_owned();
    sidecar.push(".stderr");
    let text = fs::read(PathBuf::from(sidecar))
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .unwrap_or_default();
    if text.is_empty() {
        fallback.to_owned()
    } else {
        text
    }
}

/// Reduce launcher stderr to `(diagnostic, bounded-tail)` (Python `_diagram_failure_capture`).
fn diagram_failure_capture(returncode: i32, stderr: &str) -> (String, String) {
    let tail_source = format!("stderr:\n{stderr}\n");
    let stripped = strip_diagram_sections(&tail_source);
    let capture = redact(&stripped).text().to_owned();
    let sanitized = sanitize_diagram_capture(&capture);
    let collapsed = WHITESPACE_RUN.replace_all(&sanitized, " ");
    let collapsed = collapsed.trim();
    let mut collapsed = if collapsed.is_empty() {
        "no-output".to_owned()
    } else {
        collapsed.to_owned()
    };
    if collapsed.chars().count() > DIAGRAM_FAILURE_TAIL_LIMIT {
        let keep = DIAGRAM_FAILURE_TAIL_LIMIT - 3;
        let tail: String = collapsed
            .chars()
            .skip(collapsed.chars().count() - keep)
            .collect();
        collapsed = format!("...{tail}");
    }
    (format!("returncode: {returncode}\n{sanitized}"), collapsed)
}

/// Compose the `LAUNCHER_FAILURE_CLASS/REASON` label (Python `_launcher_failure_label`).
fn launcher_failure_label(stdout: &str) -> String {
    let failure_class = read_kv_from_text(stdout, "LAUNCHER_FAILURE_CLASS").unwrap_or_default();
    let failure_reason = read_kv_from_text(stdout, "LAUNCHER_FAILURE_REASON").unwrap_or_default();
    let failure_class = failure_class.trim();
    let failure_reason = failure_reason.trim();
    if failure_class.is_empty()
        || failure_reason.is_empty()
        || !LAUNCHER_FAILURE_LABEL_RE.is_match(failure_class)
        || !LAUNCHER_FAILURE_LABEL_RE.is_match(failure_reason)
    {
        return String::new();
    }
    format!("{failure_class}/{failure_reason}")
}

/// Whether a path is a regular file with a nonzero length.
fn file_has_bytes(path: &Path) -> bool {
    fs::metadata(path).is_ok_and(|metadata| metadata.is_file() && metadata.len() > 0)
}

/// Resolve the committed changed-file list for the prompt (Python git merge-base + diff).
fn resolve_changed_files(base_remote: &str, base_ref: &str) -> Vec<String> {
    let Ok(cwd) = env::current_dir() else {
        return Vec::new();
    };
    let Ok(repository) = GixRepository::discover(&cwd) else {
        return Vec::new();
    };
    let head = repository.resolve_revision(&Revision::new(b"HEAD".to_vec()));
    let base_target = format!("{base_remote}/{base_ref}");
    let merge_ref = repository
        .resolve_revision(&Revision::new(base_target.into_bytes()))
        .ok()
        .zip(head.as_ref().ok())
        .and_then(|(base, head)| repository.merge_base(&base, head).ok())
        .map(|oid| oid.to_hex())
        .or_else(|| {
            repository
                .resolve_revision(&Revision::new(b"HEAD~1".to_vec()))
                .ok()
                .map(|oid| oid.to_hex())
        })
        .unwrap_or_else(|| "HEAD".to_owned());
    diff_names(&repository, &merge_ref, "HEAD").unwrap_or_default()
}

/// Ported `git diff --name-only <base>..<head>` over resolved commit trees.
fn diff_names(repository: &GixRepository, base: &str, head: &str) -> Result<Vec<String>, ()> {
    let tree = |revision: &str| {
        repository
            .resolve_revision(&Revision::new(format!("{revision}^{{tree}}").into_bytes()))
            .map_err(|_error| ())
    };
    let changes = repository
        .tree_changes(&tree(base)?, &tree(head)?)
        .map_err(|_error| ())?;
    Ok(changes
        .paths()
        .map(|path| String::from_utf8_lossy(path.as_bytes()).into_owned())
        .collect())
}

#[cfg(test)]
mod tests {
    use std::{ffi::OsString, fs, sync::Arc};

    use larch_adapters::github::OctocrabGitHubService;
    use larch_test_support::{IssueServiceExchange, IssueServiceStub};
    use serde_json::{Value, json};
    use tempfile::TempDir;

    use crate::github_service::with_test_github_service;

    use super::{DIAGRAM_OPTIONS, diagrams_upsert_result};

    const MARKER: &str = larch_core::DIAGRAMS_COMMENT_MARKER;
    const ARCHITECTURE: &str =
        "## Architecture Diagram\n\n```mermaid\nflowchart TD\n  A[Root]\n```";
    const CODE_FLOW: &str =
        "## Code Flow Diagram\n\n```mermaid\nflowchart LR\n  A[Start] --> B[Done]\n```";
    fn comment(id: u64, body: &str) -> Value {
        let issue: Value = serde_json::from_str(include_str!(
            "../../larch-adapters/fixtures/github_issue.json"
        ))
        .expect("issue fixture");
        let repository_url = issue["repository_url"]
            .as_str()
            .expect("issue fixture repository URL");
        json!({
            "id": id,
            "node_id": format!("C_{id}"),
            "url": format!("{repository_url}/issues/comments/{id}"),
            "html_url": format!("https://github.com/owner/repo/issues/42#issuecomment-{id}"),
            "body": body,
            "user": issue["user"],
            "created_at": "2026-08-23T00:00:00Z",
            "updated_at": "2026-08-23T00:00:00Z",
        })
    }
    fn service(
        exchanges: impl IntoIterator<Item = IssueServiceExchange>,
    ) -> (
        Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync>,
        IssueServiceStub,
    ) {
        let server = IssueServiceStub::start(exchanges).expect("issue stub");
        let base = server.base_url().to_owned();
        let factory = Arc::new(move || OctocrabGitHubService::with_test_base(&base));
        (factory, server)
    }
    fn parsed(code_file: &str) -> crate::argparse_compat::ParsedCommandLine {
        let arguments = [
            "--issue",
            "42",
            "--repo",
            "owner/repo",
            "--code-flow-file",
            code_file,
            "--allow-external-paths",
        ]
        .map(OsString::from);
        crate::argparse_compat::parse_with_flags(
            &arguments,
            DIAGRAM_OPTIONS,
            &[
                "--clear-architecture",
                "--clear-code-flow",
                "--allow-external-paths",
                "--dry-run",
            ],
            0,
        )
    }

    #[test]
    fn live_upsert_is_authorized_and_requires_exact_readback() {
        let root = TempDir::new().expect("tempdir");
        let code = root.path().join("code.md");
        fs::write(&code, format!("{CODE_FLOW}\n")).expect("code flow");
        let old = format!("{MARKER}\n\n{ARCHITECTURE}");
        let next = format!("{MARKER}\n\n{ARCHITECTURE}\n\n{CODE_FLOW}");
        let comments = |body: &str| json!([comment(11, body)]).to_string();
        let (factory, server) = service([
            IssueServiceExchange::any_json(200, comments(&old)).expect("initial read"),
            IssueServiceExchange::any_json(200, comments(&old)).expect("ownership read"),
            IssueServiceExchange::any_json(200, comment(11, &next).to_string())
                .expect("mutation echo"),
            IssueServiceExchange::any_json(200, comments(&next)).expect("exact readback"),
        ]);

        let output = with_test_github_service(factory, || {
            diagrams_upsert_result(&parsed(&code.to_string_lossy()))
        })
        .expect("upsert succeeds");
        let requests = server.finish().expect("stub completed");

        assert_eq!(output.status, "ok");
        assert!(output.updated);
        assert_eq!(
            output.comment_url,
            "https://github.com/owner/repo/issues/42#issuecomment-11"
        );
        assert_eq!(
            requests.len(),
            4,
            "discovery, authorization-owned mutation, and readback"
        );
        let mutation: Value = serde_json::from_slice(&requests[2].body.bytes).expect("mutation");
        assert_eq!(mutation["body"], next);
    }

    #[test]
    fn a_racing_duplicate_marker_refuses_before_mutation() {
        let root = TempDir::new().expect("tempdir");
        let code = root.path().join("code.md");
        fs::write(&code, format!("{CODE_FLOW}\n")).expect("code flow");
        let old = format!("{MARKER}\n\n{ARCHITECTURE}");
        let (factory, server) = service([
            IssueServiceExchange::any_json(200, json!([comment(11, &old)]).to_string())
                .expect("initial read"),
            IssueServiceExchange::any_json(
                200,
                json!([comment(11, &old), comment(12, &old)]).to_string(),
            )
            .expect("racing conflict"),
        ]);

        let failure = with_test_github_service(factory, || {
            diagrams_upsert_result(&parsed(&code.to_string_lossy()))
        })
        .expect_err("duplicate marker must refuse");

        let golden: Value = serde_json::from_str(include_str!(
            "../tests/fixtures/diagrams-upsert-conflict-replay.golden.json"
        ))
        .expect("conflict replay golden");
        assert_eq!(golden["exit_code"], failure.1);
        assert_eq!(golden["files"]["code.md"]["text"], format!("{CODE_FLOW}\n"));
        assert_eq!(
            golden["stdout"]["text"],
            format!(
                "UPSERT_STATUS=failed\nCOMMENT_URL=\nUPDATED=false\nARCHITECTURE_SOURCE=absent\nCODE_FLOW_SOURCE=absent\nERROR={}\n",
                failure.0
            )
        );
        assert_eq!(golden["stderr"]["text"], "");
        assert_eq!(server.finish().expect("stub completed").len(), 2);
    }
}
