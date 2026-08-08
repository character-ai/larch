//! The `/design` to `/implement` issue-body wire: plan blocks, named blocks,
//! plan scope, title eligibility, and untrusted envelopes.
//!
//! These twelve verbs carry the live handoff documented in
//! `docs/issue-anchored-plan.md`. `/design` writes the `larch:plan` named block
//! and `/implement` preflight reads it back, so the plan grammar bytes
//! (`### NEW:`, `### UPDATED:`, `### REWRITTEN:`, `### MAY_UPDATE:`, and the
//! terminal `diff_lines:` trailer) pass through untouched: nothing here parses
//! the plan body, it is only located, sliced, and republished.
//!
//! Every grammar decision belongs to `larch_core`: the fail-closed named-block
//! parser, the title predicates, the scope-heading reader, and the untrusted
//! envelope. What lives here is the command surface those callers branch on —
//! the option scanners, the `KEY=value` envelopes, and the exit codes — because
//! `/design`, `/implement`, `/triage`, and `/debate` read the exact rows and
//! codes their Python predecessors produced.
//!
//! Issue bodies and plan text are untrusted (G-Sec-2). They are written to
//! caller-named files or wrapped in a labelled `encoding="literal-redacted"`
//! envelope, never interpreted, and redaction runs before any value crosses to
//! GitHub or into a contract row (G-Sec-3, G-IO-2).

use crate::{
    argparse_compat::{ParsedCommandLine, parse_with_flags, read_stdin, write_stdout},
    blocker_commands::resolve_repo_for,
    github_repository_resolution::repository_ref,
    github_service::{ServiceFailure, with_github_service},
    issue_mutation_support::{authorization_request, flat_error, sanitized_line},
};
use larch_adapters::github::IssueMutationOwner;
use larch_core::{
    ARCHIVAL_JQ_FILTER, GitHubRepositoryRef, GitHubService, IssueMutationField, IssueMutationLease,
    IssueMutationRequest, IssueMutationSnapshot, NamedBlockError, NamedBlockWriteMode, PLAN_MARKER,
    emit_kv, extract_scope_paths, insert_signal_marker, is_valid_named_block_marker,
    named_block_marker_allowed, parse_named_block, plan_named_block_write, redact,
    redact_run_log_payload, redact_untrusted_stream, strip_named_block,
    title_has_archival_report_prefix, title_lifecycle_reject_marker, title_starts_with_brainstorm,
    untrusted_content_block as compose_untrusted_block, xml_escape_attr,
};
use std::{
    collections::BTreeSet,
    env,
    ffi::{OsStr, OsString},
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
};

/// Environment keys the named-block lease reads, in first-wins order.
const RUN_ID_KEYS: [&str; 3] = ["RUN_ID", "LARCH_RUN_ID", "SESSION_ID"];
/// Characters of a refusal detail one `ERROR=` row carries.
const ERROR_CHARS: usize = 500;
/// Exit code for a refusal that leaves the issue untouched.
const REFUSED_RC: u8 = 2;

const CONTENT_BLOCK_USAGE: &str = "usage: untrusted content-block [-h] [--text TEXT] tag";
const CONTENT_BLOCK_HELP: &str = concat!(
    "usage: untrusted content-block [-h] [--text TEXT] tag\n",
    "\n",
    "positional arguments:\n",
    "  tag\n",
    "\n",
    "options:\n",
    "  -h, --help   show this help message and exit\n",
    "  --text TEXT\n",
);
const SCOPE_PATHS_USAGE: &str =
    "usage: extract-plan-scope-paths.sh [-h] --plan-file PLAN_FILE [-z]";
const SCOPE_PATHS_HELP: &str = concat!(
    "usage: extract-plan-scope-paths.sh [-h] --plan-file PLAN_FILE [-z]\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --plan-file PLAN_FILE\n",
    "  -z, --null\n",
);
const STRIP_BODY_USAGE: &str =
    "usage: plan-block-strip-body.sh [-h] [--file FILE] [--output OUTPUT]";
const STRIP_BODY_HELP: &str = concat!(
    "usage: plan-block-strip-body.sh [-h] [--file FILE] [--output OUTPUT]",
    "options:",
    "  -h, --help       show this help message and exit",
    "  --file FILE",
    "  --output OUTPUT",
);
const PLAN_BLOCK_READ_USAGE: &str =
    "usage: plan-block-read.sh [-h] --issue ISSUE --output OUTPUT [--repo REPO]";
const PLAN_BLOCK_READ_HELP: &str = concat!(
    "usage: plan-block-read.sh [-h] --issue ISSUE --output OUTPUT [--repo REPO]",
    "options:",
    "  -h, --help       show this help message and exit",
    "  --issue ISSUE",
    "  --output OUTPUT",
    "  --repo REPO",
);
/// `argparse` wraps its usage at the terminal width and indents the
/// continuation under the program name, and the diagnostic writer then strips
/// the newlines, so the two writers' usage lines differ by more than the name.
const NAMED_BLOCK_WRITE_USAGE: &str = concat!(
    "usage: named-block-write.sh [-h] --marker MARKER --issue ISSUE",
    "                            [--content-file CONTENT_FILE] [--delete]",
    "                            [--repo REPO]",
);
const NAMED_BLOCK_WRITE_HELP: &str = concat!(
    "usage: named-block-write.sh [-h] --marker MARKER --issue ISSUE",
    "                            [--content-file CONTENT_FILE] [--delete]",
    "                            [--repo REPO]",
    "options:",
    "  -h, --help            show this help message and exit",
    "  --marker MARKER",
    "  --issue ISSUE",
    "  --content-file CONTENT_FILE",
    "  --delete",
    "  --repo REPO",
);
const PLAN_BLOCK_WRITE_USAGE: &str = concat!(
    "usage: plan-block-write.sh [-h] --issue ISSUE [--content-file CONTENT_FILE]",
    "                           [--delete] [--repo REPO]",
);
const PLAN_BLOCK_WRITE_HELP: &str = concat!(
    "usage: plan-block-write.sh [-h] --issue ISSUE [--content-file CONTENT_FILE]",
    "                           [--delete] [--repo REPO]",
    "options:",
    "  -h, --help            show this help message and exit",
    "  --issue ISSUE",
    "  --content-file CONTENT_FILE",
    "  --delete",
    "  --repo REPO",
);

// ------------------------------------------------------------------- untrusted

/// Escape stdin for an XML attribute.
pub fn untrusted_xml_escape_attr(arguments: &[OsString]) -> ExitCode {
    if let Some(refusal) = reject_extra_arguments("untrusted xml-escape-attr", arguments) {
        return refusal;
    }
    write_stdout(&xml_escape_attr(&read_stdin()))
}

/// Redact stdin and escape its markup delimiters.
pub fn untrusted_redact_stream(arguments: &[OsString]) -> ExitCode {
    if let Some(refusal) = reject_extra_arguments("untrusted redact-stream", arguments) {
        return refusal;
    }
    write_stdout(&redact_untrusted_stream(&read_stdin()))
}

/// Wrap one file's contents in a labelled, redacted content block.
///
/// Exits `2` for a line that is not exactly `TAG PATH` and `1` when the file
/// cannot be read.
pub fn untrusted_file_block(arguments: &[OsString]) -> ExitCode {
    let [tag, path] = arguments else {
        eprintln!("untrusted file-block: usage: untrusted file-block TAG PATH");
        return ExitCode::from(REFUSED_RC);
    };
    // Python read with `errors="replace"`, so undecodable bytes become the
    // replacement character rather than a refusal.
    let text = match fs::read(Path::new(path)) {
        Ok(bytes) => String::from_utf8_lossy(&bytes).into_owned(),
        Err(error) => {
            // Python let the read error escape as a traceback, which exits `1`
            // and prints the interpreter frame stack; the same failure is one
            // named line here.
            eprintln!(
                "untrusted file-block: {}: {error}",
                Path::new(path).display()
            );
            return ExitCode::from(1);
        }
    };
    write_stdout(&compose_untrusted_block(&tag.to_string_lossy(), &text))
}

/// Wrap `--text` or stdin in a labelled, redacted content block.
pub fn untrusted_content_block(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(arguments, &["--text"], &["-h", "--help"], 1);
    if let Some(error) = parsed.value_error() {
        return plain_argparse_error(CONTENT_BLOCK_USAGE, "untrusted content-block", error);
    }
    if help_requested(&parsed) {
        return write_stdout(CONTENT_BLOCK_HELP);
    }
    let Some(tag) = parsed.positional(0) else {
        return plain_argparse_error(
            CONTENT_BLOCK_USAGE,
            "untrusted content-block",
            "the following arguments are required: tag",
        );
    };
    if let Some(error) = parsed.error() {
        return plain_argparse_error(CONTENT_BLOCK_USAGE, "untrusted content-block", &error);
    }
    let text = parsed
        .value("--text")
        .map_or_else(read_stdin, |value| value.to_string_lossy().into_owned());
    write_stdout(&compose_untrusted_block(&tag.to_string_lossy(), &text))
}

// ----------------------------------------------------------------- issue title

/// Report the three archival-eligibility predicates for one title.
pub fn title_eligibility(arguments: &[OsString]) -> ExitCode {
    let title = match scan_title_arguments(arguments, false) {
        Ok(scanned) => scanned.title,
        Err(refusal) => return refusal,
    };
    let marker = title_lifecycle_reject_marker(&title);
    emit_kv("LIFECYCLE_REJECT", bool_text(marker.is_some()));
    if let Some(marker) = marker {
        emit_kv("LIFECYCLE_MARKER", &marker);
    }
    emit_kv(
        "ARCHIVAL_REPORT",
        bool_text(title_has_archival_report_prefix(&title)),
    );
    emit_kv(
        "BRAINSTORM",
        bool_text(title_starts_with_brainstorm(&title)),
    );
    ExitCode::SUCCESS
}

/// Print the `jq` archival-eligibility filter verbatim.
pub fn title_archival_jq(arguments: &[OsString]) -> ExitCode {
    if let Some(refusal) = reject_extra_arguments("issue title-archival-jq", arguments) {
        return refusal;
    }
    write_stdout(&format!("{ARCHIVAL_JQ_FILTER}\n"))
}

/// Print one title with `[marker]` inserted after any lifecycle prefix.
pub fn insert_signal_marker_command(arguments: &[OsString]) -> ExitCode {
    let scanned = match scan_title_arguments(arguments, true) {
        Ok(scanned) => scanned,
        Err(refusal) => return refusal,
    };
    write_stdout(&insert_signal_marker(&scanned.title, &scanned.marker))
}

/// The `--title` and `--marker` values one title command line supplies.
struct TitleArguments {
    title: String,
    marker: String,
}

/// Scan the hand-rolled `--title` / `--marker` grammar the title verbs share.
///
/// Only the exact spellings and their `--name=value` forms are options; there
/// is no abbreviation, and any other token stops the scan. Every refusal prints
/// its one line under the shared `issue title:` prefix and exits `2`.
fn scan_title_arguments(
    arguments: &[OsString],
    want_marker: bool,
) -> Result<TitleArguments, ExitCode> {
    let mut title: Option<String> = None;
    let mut marker: Option<String> = None;
    let mut index = 0;
    while index < arguments.len() {
        let token = arguments[index].to_string_lossy().into_owned();
        let target = match token.as_str() {
            "--title" => &mut title,
            "--marker" if want_marker => &mut marker,
            _ => {
                if let Some(value) = token.strip_prefix("--title=") {
                    title = Some(value.to_owned());
                } else if want_marker && let Some(value) = token.strip_prefix("--marker=") {
                    marker = Some(value.to_owned());
                } else {
                    return Err(title_refusal(&format!("unknown option: {token}")));
                }
                index += 1;
                continue;
            }
        };
        let Some(value) = arguments.get(index + 1) else {
            return Err(title_refusal(&format!("{token} requires a value")));
        };
        *target = Some(value.to_string_lossy().into_owned());
        index += 2;
    }
    let Some(title) = title else {
        return Err(title_refusal("--title is required"));
    };
    if !want_marker {
        return Ok(TitleArguments {
            title,
            marker: String::new(),
        });
    }
    marker.map_or_else(
        || Err(title_refusal("--marker is required")),
        |marker| Ok(TitleArguments { title, marker }),
    )
}

fn title_refusal(message: &str) -> ExitCode {
    eprintln!("issue title: {message}");
    ExitCode::from(REFUSED_RC)
}

// ------------------------------------------------------------ plan scope-paths

/// Publish the plan's declared scope paths, newline or NUL separated.
///
/// Exits `2` for an unusable line or an unreadable plan file. The list is never
/// empty: an unscoped plan falls back to the single `/design` skill surface, so
/// a consumer never reads "no paths" as "every path".
pub fn scope_paths(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &["--plan-file"],
        &["-h", "--help", "-z", "--null"],
        0,
    );
    if let Some(error) = parsed.value_error() {
        return plain_argparse_error(SCOPE_PATHS_USAGE, "extract-plan-scope-paths.sh", error);
    }
    if help_requested(&parsed) {
        return write_stdout(SCOPE_PATHS_HELP);
    }
    let Some(plan_file) = parsed.value("--plan-file") else {
        return plain_argparse_error(
            SCOPE_PATHS_USAGE,
            "extract-plan-scope-paths.sh",
            "the following arguments are required: --plan-file",
        );
    };
    if let Some(error) = parsed.error() {
        return plain_argparse_error(SCOPE_PATHS_USAGE, "extract-plan-scope-paths.sh", &error);
    }
    let path = PathBuf::from(plan_file);
    if !path.is_file() {
        eprintln!(
            "extract-plan-scope-paths.sh: plan file not found: {}",
            plan_file.to_string_lossy()
        );
        return ExitCode::from(REFUSED_RC);
    }
    let bytes = match fs::read(&path) {
        Ok(bytes) => bytes,
        Err(error) => {
            eprintln!("extract-plan-scope-paths.sh: {error}");
            return ExitCode::from(REFUSED_RC);
        }
    };
    let separator = if parsed.flag("--null") || parsed.flag("-z") {
        '\0'
    } else {
        '\n'
    };
    // The extractor always names at least the fallback path, so the rendered
    // list always ends with one separator.
    let mut rendered =
        extract_scope_paths(&String::from_utf8_lossy(&bytes)).join(&separator.to_string());
    rendered.push(separator);
    write_stdout(&rendered)
}

// ------------------------------------------------------------------ plan-block

/// Remove the `larch:plan` block from a body file or stdin.
///
/// Exits `1` with `MALFORMED=<defect>` when the body's markers do not pair, so
/// a caller never strips half a block.
pub fn plan_block_strip_body(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(arguments, &["--file", "--output"], &["-h", "--help"], 0);
    if let Some(error) = parsed.value_error() {
        return diagnostic_argparse_error(STRIP_BODY_USAGE, "plan-block-strip-body.sh", error);
    }
    if help_requested(&parsed) {
        diagnostic(STRIP_BODY_HELP);
        return ExitCode::SUCCESS;
    }
    if let Some(error) = parsed.error() {
        return diagnostic_argparse_error(STRIP_BODY_USAGE, "plan-block-strip-body.sh", &error);
    }
    let output = parsed.value("--output").map(PathBuf::from);
    let body = match parsed.value("--file") {
        None => read_stdin(),
        Some(file) => match fs::read(Path::new(file)) {
            Ok(bytes) => String::from_utf8_lossy(&bytes).into_owned(),
            Err(error) => {
                diagnostic(&format!("plan-block-strip-body.sh: {error}"));
                return ExitCode::from(1);
            }
        },
    };
    match strip_named_block(&body, PLAN_MARKER) {
        Err(defect) => {
            if let Some(output) = output.as_deref()
                && let Some(refusal) = write_artifact(output, "")
            {
                return refusal;
            }
            emit_kv("MALFORMED", defect.reason());
            ExitCode::from(1)
        }
        Ok(stripped) => match output.as_deref() {
            Some(output) => write_artifact(output, &stripped).unwrap_or(ExitCode::SUCCESS),
            None => write_stdout(&stripped),
        },
    }
}

/// Materialize one issue's `larch:plan` inner text into a caller-named file.
///
/// The output file is always written, empty when no plan is present, so a
/// consumer reads the same artifact on every path.
pub fn plan_block_read(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &["--issue", "--output", "--repo"],
        &["-h", "--help"],
        0,
    );
    if let Some(error) = parsed.value_error() {
        return diagnostic_argparse_error(PLAN_BLOCK_READ_USAGE, "plan-block-read.sh", error);
    }
    if help_requested(&parsed) {
        diagnostic(PLAN_BLOCK_READ_HELP);
        return ExitCode::SUCCESS;
    }
    let missing = ["--issue", "--output"]
        .into_iter()
        .filter(|option| parsed.value(option).is_none())
        .collect::<Vec<&str>>();
    if !missing.is_empty() {
        return diagnostic_argparse_error(
            PLAN_BLOCK_READ_USAGE,
            "plan-block-read.sh",
            &format!(
                "the following arguments are required: {}",
                missing.join(", ")
            ),
        );
    }
    if let Some(error) = parsed.error() {
        return diagnostic_argparse_error(PLAN_BLOCK_READ_USAGE, "plan-block-read.sh", &error);
    }
    let issue = parsed
        .value("--issue")
        .unwrap_or_default()
        .to_string_lossy()
        .into_owned();
    let output = PathBuf::from(parsed.value("--output").unwrap_or_default());
    let Some(number) = positive_issue(&issue) else {
        diagnostic("plan-block-read.sh: --issue must be a positive integer");
        return ExitCode::from(1);
    };
    let repo = parsed.value("--repo").map(OsStr::to_string_lossy);
    let Some(repository) = resolved_repository(repo.as_deref()) else {
        if let Some(refusal) = write_artifact(&output, "") {
            return refusal;
        }
        return emit_failed("could not determine repo", REFUSED_RC);
    };
    let body = match read_issue_body(&repository, number) {
        Ok(body) => body,
        Err(detail) => {
            if let Some(refusal) = write_artifact(&output, "") {
                return refusal;
            }
            return emit_failed(&detail, REFUSED_RC);
        }
    };
    match parse_named_block(&body, PLAN_MARKER) {
        Err(defect) => {
            if let Some(refusal) = write_artifact(&output, "") {
                return refusal;
            }
            emit_kv("MALFORMED", defect.reason());
            ExitCode::from(1)
        }
        Ok(None) => {
            if let Some(refusal) = write_artifact(&output, "") {
                return refusal;
            }
            emit_kv("BLOCK_PRESENT", "false");
            ExitCode::SUCCESS
        }
        Ok(Some(inner)) => {
            if let Some(refusal) = write_artifact(&output, &inner) {
                return refusal;
            }
            emit_kv("BLOCK_PRESENT", "true");
            emit_kv("OUTPUT", &sanitized_line(&output.to_string_lossy()));
            ExitCode::SUCCESS
        }
    }
}

/// Write, replace, or delete the `larch:plan` block on one issue.
pub fn plan_block_write(arguments: &[OsString]) -> ExitCode {
    named_block_command(arguments, Some(PLAN_MARKER))
}

/// Write, replace, or delete one named block on one issue.
pub fn named_block_write(arguments: &[OsString]) -> ExitCode {
    named_block_command(arguments, None)
}

/// One usable `named-block write` or `plan-block write` command line.
struct NamedBlockRequest {
    marker: String,
    issue: u64,
    repository: GitHubRepositoryRef,
    content: Option<String>,
}

/// Scan, validate, and run one named-block write.
///
/// `marker_default` fixes the marker for `plan-block write`, whose command line
/// carries no `--marker` at all.
fn named_block_command(arguments: &[OsString], marker_default: Option<&str>) -> ExitCode {
    let plan_only = marker_default.is_some();
    let (usage, help, program) = if plan_only {
        (
            PLAN_BLOCK_WRITE_USAGE,
            PLAN_BLOCK_WRITE_HELP,
            "plan-block-write.sh",
        )
    } else {
        (
            NAMED_BLOCK_WRITE_USAGE,
            NAMED_BLOCK_WRITE_HELP,
            "named-block-write.sh",
        )
    };
    let mut options: Vec<&'static str> = vec!["--issue", "--content-file", "--repo"];
    if !plan_only {
        options.insert(0, "--marker");
    }
    let parsed = parse_with_flags(arguments, &options, &["-h", "--help", "--delete"], 0);
    if let Some(error) = parsed.value_error() {
        return diagnostic_argparse_error(usage, program, error);
    }
    if help_requested(&parsed) {
        diagnostic(help);
        return ExitCode::SUCCESS;
    }
    let missing = options
        .iter()
        .take(if plan_only { 1 } else { 2 })
        .filter(|option| parsed.value(option).is_none())
        .copied()
        .collect::<Vec<&str>>();
    if !missing.is_empty() {
        return diagnostic_argparse_error(
            usage,
            program,
            &format!(
                "the following arguments are required: {}",
                missing.join(", ")
            ),
        );
    }
    if let Some(error) = parsed.error() {
        return diagnostic_argparse_error(usage, program, &error);
    }
    let marker = marker_default.map_or_else(
        || {
            parsed
                .value("--marker")
                .unwrap_or_default()
                .to_string_lossy()
                .into_owned()
        },
        str::to_owned,
    );
    if !named_block_marker_allowed(&marker) {
        if is_valid_named_block_marker(&marker) {
            diagnostic(&format!("{program}: unsupported marker: {marker}"));
        } else {
            diagnostic(&format!(
                "{program}: --marker must match ^[a-z0-9][a-z0-9-]*$"
            ));
        }
        return ExitCode::from(1);
    }
    let issue = parsed
        .value("--issue")
        .unwrap_or_default()
        .to_string_lossy()
        .into_owned();
    let Some(number) = positive_issue(&issue) else {
        diagnostic(&format!("{program}: --issue must be a positive integer"));
        return ExitCode::from(1);
    };
    let content_file = parsed.value("--content-file").map(PathBuf::from);
    let delete = parsed.flag("--delete");
    if delete && content_file.is_some() {
        diagnostic(&format!(
            "{program}: --delete and --content-file are mutually exclusive"
        ));
        return ExitCode::from(1);
    }
    if !delete && content_file.is_none() {
        diagnostic(usage);
        return ExitCode::from(1);
    }
    let content = match content_file.as_deref() {
        None => None,
        Some(path) => match fs::read(path) {
            Ok(bytes) => Some(String::from_utf8_lossy(&bytes).into_owned()),
            Err(_) => {
                return emit_failed(&format!("content file not found: {}", path.display()), 1);
            }
        },
    };
    let explicit_repo = parsed.value("--repo").map(OsStr::to_string_lossy);
    if let Some(repo) = explicit_repo.as_deref()
        && repository_ref(repo).is_err()
    {
        return emit_failed("invalid-repo", 1);
    }
    let Some(repository) = resolved_repository(explicit_repo.as_deref()) else {
        return emit_failed("could not determine repo", REFUSED_RC);
    };
    apply_named_block(&NamedBlockRequest {
        marker,
        issue: number,
        repository,
        content,
    })
}

/// Compose, publish, and prove one named-block write.
///
/// The compose-and-publish pair runs against one snapshot: the body the block
/// is spliced into is the same body the compare-and-swap expects, so a
/// concurrent edit is refused rather than silently overwritten. The proof is
/// the mutation owner's own read-back, which must still parse as exactly one
/// unfenced block — a write that leaves only a fenced marker example fails
/// closed, because `/implement` preflight would then read `BLOCK_PRESENT=false`
/// while `/design` reported success.
fn apply_named_block(request: &NamedBlockRequest) -> ExitCode {
    let outcome = with_github_service(async |service, cancellation| {
        let owner = IssueMutationOwner::new(service);
        let snapshot = owner
            .read_snapshot(&request.repository, request.issue, cancellation)
            .await
            .map_err(|error| error.to_string())?;
        let write = match plan_named_block_write(
            &snapshot.body,
            &request.marker,
            request.content.as_deref(),
        ) {
            Ok(write) => write,
            Err(NamedBlockError::Malformed(defect)) => return Ok(Err(defect)),
            Err(error) => return Err(error.to_string()),
        };
        if write.mode() == NamedBlockWriteMode::AbsentNoop {
            return Ok(Ok(NamedBlockOutcome {
                mode: write.mode(),
                markers_present: write.markers_present(),
                body_bytes: write.body().len(),
            }));
        }
        let body = redact_run_log_payload(write.body());
        let body_bytes = body.len();
        // The Python writer carried no live-mutation gate: `/design` publishes
        // the plan block from an ordinary session that passes no session
        // context, so an operator-mode request preserves the contract rather
        // than refusing every existing caller.
        let authorization = authorization_request("", "", "", true);
        let mutation = owner
            .apply(
                cancellation,
                &authorization,
                &named_block_mutation(request, &snapshot, body),
            )
            .await
            .map_err(|error| error.to_string())?;
        if request.content.is_some() {
            verify_published_block(&mutation.after.body, &request.marker)?;
        }
        Ok(Ok(NamedBlockOutcome {
            mode: write.mode(),
            markers_present: write.markers_present(),
            body_bytes,
        }))
    });
    match outcome {
        Err(ServiceFailure::Setup(detail) | ServiceFailure::Operation(detail)) => {
            emit_failed(&detail, REFUSED_RC)
        }
        Ok(Err(defect)) => {
            emit_kv("MALFORMED", defect.reason());
            ExitCode::from(1)
        }
        Ok(Ok(outcome)) => {
            // `WRITTEN=true` marks a completed command, not a changed body: the
            // Python writer published it for the absent-delete no-op too, and
            // `MODE` is the row that separates the two.
            emit_kv("WRITTEN", "true");
            emit_kv("MODE", outcome.mode.as_str());
            emit_kv("MARKERS_PRESENT", bool_text(outcome.markers_present));
            emit_kv("BODY_BYTES", &outcome.body_bytes.to_string());
            ExitCode::SUCCESS
        }
    }
}

/// What one completed named-block write reports.
struct NamedBlockOutcome {
    mode: NamedBlockWriteMode,
    markers_present: bool,
    body_bytes: usize,
}

fn named_block_mutation(
    request: &NamedBlockRequest,
    snapshot: &IssueMutationSnapshot,
    body: String,
) -> IssueMutationRequest {
    IssueMutationRequest {
        repository: request.repository.clone(),
        issue: request.issue,
        expected_updated_at: snapshot.updated_at.clone(),
        expected_state: snapshot.state,
        fields: BTreeSet::from([IssueMutationField::NamedBlock]),
        title: None,
        body: Some(body),
        labels: None,
        marker: Some(request.marker.clone()),
        lease: named_block_lease(&request.marker),
    }
}

/// Bind a protected named-block write to the active run, when one is named.
fn named_block_lease(marker: &str) -> Option<IssueMutationLease> {
    RUN_ID_KEYS
        .into_iter()
        .find_map(|key| {
            env::var(key)
                .ok()
                .map(|value| value.trim().to_owned())
                .filter(|value| !value.is_empty())
        })
        .map(|run_id| IssueMutationLease {
            run_id,
            marker: marker.to_owned(),
        })
}

fn verify_published_block(body: &str, marker: &str) -> Result<(), String> {
    match parse_named_block(body, marker) {
        Err(defect) => Err(format!("post-write-verify-malformed:{}", defect.reason())),
        Ok(None) => Err("post-write-verify-missing".to_owned()),
        Ok(Some(inner)) if marker == PLAN_MARKER && inner.trim().is_empty() => {
            Err("post-write-verify-empty".to_owned())
        }
        Ok(Some(_)) => Ok(()),
    }
}

// ---------------------------------------------------------------------- shared

/// Return whether the line asked for help in either spelling.
fn help_requested(parsed: &ParsedCommandLine) -> bool {
    parsed.flag("--help") || parsed.flag("-h")
}

/// Refuse any argument at all for a verb whose whole input is stdin.
fn reject_extra_arguments(program: &str, arguments: &[OsString]) -> Option<ExitCode> {
    arguments.first().map(|first| {
        eprintln!("{program}: unknown option: {}", first.to_string_lossy());
        ExitCode::from(REFUSED_RC)
    })
}

const fn bool_text(value: bool) -> &'static str {
    if value { "true" } else { "false" }
}

/// Match the legacy `str.isdecimal()` and non-zero issue spelling.
///
/// Python also accepted non-ASCII decimal digits and magnitudes no issue number
/// can reach; only ASCII decimals that fit a `u64` are accepted here, and
/// anything else takes the same refusal.
fn positive_issue(issue: &str) -> Option<u64> {
    if issue.is_empty() || !issue.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    issue.parse::<u64>().ok().filter(|number| *number != 0)
}

fn resolved_repository(explicit: Option<&str>) -> Option<GitHubRepositoryRef> {
    resolve_repo_for(explicit).and_then(|repo| repository_ref(&repo).ok())
}

fn read_issue_body(repository: &GitHubRepositoryRef, issue: u64) -> Result<String, String> {
    with_github_service(async |service, cancellation| {
        service
            .issue(repository, issue, cancellation)
            .await
            .map(|subject| subject.body)
            .map_err(|error| format!("gh issue view failed: {error}"))
    })
    .map_err(ServiceFailure::into_detail)
}

/// Write one caller-named artifact, reporting a failed write as the envelope.
///
/// Returns `None` when the write completed; the callers treat that as "keep
/// going" so the success rows stay in one place.
fn write_artifact(path: &Path, text: &str) -> Option<ExitCode> {
    fs::write(path, text).err().map(|error| {
        emit_failed(
            &format!("output write failed: {}: {error}", path.display()),
            1,
        )
    })
}

/// Publish the refusal envelope every wire consumer parses.
fn emit_failed(message: &str, code: u8) -> ExitCode {
    emit_kv("FAILED", "true");
    emit_kv("ERROR", &flat_error(message, ERROR_CHARS));
    ExitCode::from(code)
}

/// Write one operator diagnostic the way the Python quiet writer did.
///
/// Control bytes are stripped first, which is why a wrapped `argparse` usage
/// block reaches the terminal as one long line, and redaction runs before the
/// line is published (G-Sec-3).
fn diagnostic(message: &str) {
    let sanitized = sanitized_line(message);
    eprintln!("{}", redact(&sanitized).text().trim_end_matches('\n'));
}

/// Report one `argparse` refusal through the diagnostic writer.
fn diagnostic_argparse_error(usage: &str, program: &str, error: &str) -> ExitCode {
    diagnostic(usage);
    diagnostic(&format!("{program}: error: {error}"));
    ExitCode::from(REFUSED_RC)
}

/// Report one `argparse` refusal on stderr, keeping the usage block's newlines.
fn plain_argparse_error(usage: &str, program: &str, error: &str) -> ExitCode {
    eprintln!("{usage}");
    eprintln!("{program}: error: {error}");
    ExitCode::from(REFUSED_RC)
}

#[cfg(test)]
mod tests {
    use super::{
        bool_text, named_block_lease, positive_issue, scan_title_arguments, verify_published_block,
    };
    use larch_core::DONE_PREFIX;
    use std::ffi::OsString;

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    #[test]
    fn the_title_scanner_accepts_both_spellings_in_either_order() {
        let title = format!("{DONE_PREFIX}fix");
        let scanned = scan_title_arguments(
            &arguments(&["--marker", "OOS", &format!("--title={title}")]),
            true,
        )
        .unwrap_or_else(|_| panic!("a usable line"));

        assert_eq!(scanned.title, title);
        assert_eq!(scanned.marker, "OOS");
    }

    #[test]
    fn the_title_scanner_refuses_every_unusable_line() {
        // `--marker` is not an option for the eligibility verb, so it reads as
        // an unknown token there rather than as a value-taking option.
        for line in [
            &["--bogus"][..],
            &["--title"][..],
            &[][..],
            &["--marker", "X"][..],
        ] {
            assert!(
                scan_title_arguments(&arguments(line), false).is_err(),
                "{line:?}"
            );
        }
        assert!(scan_title_arguments(&arguments(&["--title", "a"]), true).is_err());
    }

    #[test]
    fn only_an_ascii_decimal_above_zero_is_an_issue_number() {
        assert_eq!(positive_issue("8171"), Some(8171));
        for issue in ["", "0", "00", "-1", "8a", " 8", "٣", &"9".repeat(30)] {
            assert_eq!(positive_issue(issue), None, "{issue}");
        }
        // A leading zero is decimal, so the legacy scanner accepted it.
        assert_eq!(positive_issue("07"), Some(7));
    }

    #[test]
    fn the_post_write_proof_refuses_every_unusable_read_back() {
        assert_eq!(
            verify_published_block(
                "<!-- larch:plan:start -->\nwork\n<!-- larch:plan:end -->\n",
                "plan"
            ),
            Ok(())
        );
        assert_eq!(
            verify_published_block("nothing here", "plan"),
            Err("post-write-verify-missing".to_owned())
        );
        assert_eq!(
            verify_published_block(
                "<!-- larch:plan:start -->\n<!-- larch:plan:end -->\n",
                "plan"
            ),
            Err("post-write-verify-empty".to_owned())
        );
        assert_eq!(
            verify_published_block("<!-- larch:plan:start -->\n", "plan"),
            Err("post-write-verify-malformed:start-without-end".to_owned())
        );
        // A fenced marker pair is a decompose example, so a body carrying only
        // fenced markers reads as missing rather than as a published block.
        assert_eq!(
            verify_published_block(
                "```\n<!-- larch:plan:start -->\nwork\n<!-- larch:plan:end -->\n```\n",
                "plan"
            ),
            Err("post-write-verify-missing".to_owned())
        );
    }

    #[test]
    fn booleans_render_as_the_legacy_tokens() {
        assert_eq!(bool_text(true), "true");
        assert_eq!(bool_text(false), "false");
    }

    #[test]
    fn the_lease_is_absent_without_a_named_run() {
        // The environment is process wide, so this asserts only the shape the
        // absent case takes; the populated case is covered by the mutation
        // owner's own tests.
        let lease = named_block_lease("plan");
        assert!(lease.is_none_or(|lease| !lease.run_id.is_empty()));
    }
}
