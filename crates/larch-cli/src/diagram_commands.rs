//! Rust-owned Mermaid sanitizer and marker-comment diagram upsert.

use std::{
    collections::BTreeSet,
    env,
    ffi::OsString,
    fs,
    io::{self, Read as _},
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_core::{
    DIAGRAMS_COMMENT_MARKER, design::extract_diagram_sections, mermaid::inspect_mermaid, redact,
};

use crate::{
    argparse_compat::{ParsedCommandLine, parse_with_flags},
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
            "../../../fixtures/rust-parity/goldens/diagrams-upsert-conflict-replay.golden.json"
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
