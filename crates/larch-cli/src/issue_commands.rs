//! `issue state`, `issue info`, and `issue context`.
//!
//! Three single-issue reads that route through the typed GitHub adapter. Each
//! keeps the hand-rolled option scanner its Python predecessor used, because
//! callers branch on the exact `KEY=value` rows and exit codes those scanners
//! produce; none of the three was ever an `argparse` command.
//!
//! Fetched titles, bodies, and URLs are untrusted data (G-Sec-2). They are
//! written to files or published as KV values, never interpreted, and a value
//! that could forge a contract-stream row fails closed instead of reaching
//! `emit_kv` (G-IO-2).

use crate::{
    argparse_compat::{absolute_path, write_stdout},
    blocker_commands::resolve_repo_for,
    github_repository_resolution::repository_ref,
    github_service::{ServiceFailure, with_github_service},
};
use larch_adapters::{PathIntent, TemporaryRoot, atomic_write_utf8, ensure_directory_chain};
use larch_core::{
    GitHubIssue, GitHubIssueState, GitHubOperationErrorKind, GitHubService, emit_kv, redact,
    single_line,
};
use std::{
    ffi::OsString,
    path::{Path, PathBuf},
    process::ExitCode,
};

/// The legacy usage line, still spelled with the retired script's name because
/// `/implement` transcripts and operator muscle memory quote it verbatim.
const CONTEXT_USAGE: &str = "Usage: get-issue-context.sh --issue N --repo OWNER/REPO --tmpdir PATH";
const TITLE_FILE_NAME: &str = "upstream-issue-title.txt";
const BODY_FILE_NAME: &str = "upstream-issue-body.txt";
/// Issue context lands in a session tmpdir and holds untrusted body text, so it
/// is owner-only (G-Sec-4). The Python predecessor used the ambient umask.
const CONTEXT_FILE_MODE: u32 = 0o600;
/// A value-taking option ended the line: report it without any contract row.
const CONTEXT_MISSING_VALUE_RC: u8 = 1;
/// The line is unusable: print the usage block to stderr.
const CONTEXT_USAGE_RC: u8 = 2;

// ------------------------------------------------------------------ issue state

/// Emit `STATE`, `URL`, and `IS_PR` for one issue.
///
/// Exits `0` on a completed read and `1` on any refusal, which is reported as
/// the `FAILED=true` / `ERROR=` envelope every caller already parses.
pub fn state(arguments: &[OsString]) -> ExitCode {
    let (issue, repo) = match parse_state_arguments(arguments) {
        StateArguments::Valid { issue, repo } => (issue, repo),
        StateArguments::Invalid(error) => return emit_failed(&error),
    };
    let Some(repo) = resolve_repo_for(repo.as_deref()) else {
        return emit_failed(&read_failure("could not resolve repo"));
    };
    match read_issue(&repo, &issue) {
        Err(detail) => emit_failed(&read_failure(&detail)),
        Ok(subject) => emit_state(&subject),
    }
}

/// One `issue state` command line, as its scanner reads it.
#[derive(Clone, Debug, Eq, PartialEq)]
enum StateArguments {
    Valid { issue: String, repo: Option<String> },
    Invalid(String),
}

/// Scan the exact option pairs `issue state` accepts.
///
/// Only the exact spellings `--issue` and `--repo` are options; there is no
/// inline `--name=value` form and no abbreviation. A value that itself starts
/// with `--` reads as a missing value, and any other token stops the scan with
/// an unknown-flag refusal.
fn parse_state_arguments(arguments: &[OsString]) -> StateArguments {
    let mut issue = String::new();
    let mut repo: Option<String> = None;
    let mut index = 0;
    while index < arguments.len() {
        let token = arguments[index].to_string_lossy().into_owned();
        let option = match token.as_str() {
            "--issue" | "--repo" => token.as_str(),
            other => return StateArguments::Invalid(format!("unknown flag: {other}")),
        };
        let Some(value) = arguments
            .get(index + 1)
            .map(|value| value.to_string_lossy().into_owned())
            .filter(|value| !value.starts_with("--"))
        else {
            return StateArguments::Invalid(format!("{option} requires a value"));
        };
        if option == "--issue" {
            issue = value;
        } else {
            repo = Some(value);
        }
        index += 2;
    }
    if issue.is_empty() {
        return StateArguments::Invalid("--issue is required".to_owned());
    }
    if !issue.bytes().all(|byte| byte.is_ascii_digit()) {
        return StateArguments::Invalid("--issue must be numeric".to_owned());
    }
    StateArguments::Valid { issue, repo }
}

/// Publish the three rows in the order every consumer reads them.
///
/// `IS_PR` comes from the typed pull-request marker rather than the legacy
/// `"/pull/" in url` substring test. The two agree on every GitHub response —
/// a pull request's `html_url` always carries the `/pull/` segment — and the
/// typed marker cannot be spoofed by an issue whose URL merely contains it.
fn emit_state(subject: &GitHubIssue) -> ExitCode {
    if !kv_safe(&subject.url) {
        return emit_failed(&read_failure("issue url contained a line break"));
    }
    emit_kv("STATE", state_text(subject.state));
    emit_kv("URL", &subject.url);
    emit_kv(
        "IS_PR",
        if subject.is_pull_request {
            "true"
        } else {
            "false"
        },
    );
    ExitCode::SUCCESS
}

// ------------------------------------------------------------------- issue info

/// Emit `VALUE` for one issue field, reporting every refusal as an empty value.
///
/// Exits `0` in every case except a value-taking option that ended the line,
/// which exits `1` and emits nothing at all.
pub fn info(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_info_arguments(arguments);
    let Some(request) = parsed.request() else {
        return match parsed {
            InfoArguments::MissingValue => ExitCode::from(1),
            InfoArguments::Scanned { .. } => emit_value(""),
        };
    };
    emit_value(&read_field(&request))
}

/// One `issue info` command line, as its scanner reads it.
#[derive(Clone, Debug, Eq, PartialEq)]
enum InfoArguments {
    /// A value-taking option ended the line.
    MissingValue,
    Scanned {
        issue: String,
        field: String,
        repo: String,
        /// An unrecognized token appeared; the scan continued past it.
        unknown: bool,
    },
}

/// The fields one usable `issue info` line asks for.
#[derive(Clone, Debug, Eq, PartialEq)]
struct InfoRequest {
    issue: String,
    field: InfoField,
    repo: String,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum InfoField {
    State,
    Url,
}

impl InfoArguments {
    /// Return the request only when the line names a readable field.
    ///
    /// An unrecognized token, a missing issue, and an unsupported field are all
    /// reported the same way: no read, and an empty `VALUE`.
    fn request(&self) -> Option<InfoRequest> {
        let Self::Scanned {
            issue,
            field,
            repo,
            unknown,
        } = self
        else {
            return None;
        };
        if *unknown || issue.is_empty() {
            return None;
        }
        let field = match field.as_str() {
            "state" => InfoField::State,
            "url" => InfoField::Url,
            _ => return None,
        };
        Some(InfoRequest {
            issue: issue.clone(),
            field,
            repo: repo.clone(),
        })
    }
}

/// Scan the option pairs `issue info` accepts.
///
/// Unlike `issue state`, an option here consumes the next token whatever it
/// looks like, and an unrecognized token is skipped rather than fatal.
fn parse_info_arguments(arguments: &[OsString]) -> InfoArguments {
    let mut issue = String::new();
    let mut field = String::new();
    let mut repo = String::new();
    let mut unknown = false;
    let mut index = 0;
    while index < arguments.len() {
        let token = arguments[index].to_string_lossy().into_owned();
        let target = match token.as_str() {
            "--issue" => &mut issue,
            "--field" => &mut field,
            "--repo" => &mut repo,
            _ => {
                unknown = true;
                index += 1;
                continue;
            }
        };
        let Some(value) = arguments.get(index + 1) else {
            return InfoArguments::MissingValue;
        };
        *target = value.to_string_lossy().into_owned();
        index += 2;
    }
    InfoArguments::Scanned {
        issue,
        field,
        repo,
        unknown,
    }
}

/// Read one field, reporting every failure as the absent value.
fn read_field(request: &InfoRequest) -> String {
    let Some(repo) = resolve_repo_for(Some(request.repo.as_str())) else {
        return String::new();
    };
    let Ok(subject) = read_issue(&repo, &request.issue) else {
        return String::new();
    };
    match request.field {
        InfoField::State => state_text(subject.state).to_owned(),
        InfoField::Url => subject.url,
    }
}

/// Emit the single `VALUE` row, reporting an unsafe value as absent.
fn emit_value(value: &str) -> ExitCode {
    emit_kv("VALUE", if kv_safe(value) { value } else { "" });
    ExitCode::SUCCESS
}

// ---------------------------------------------------------------- issue context

/// Materialize one issue's title and body into a caller-named directory.
///
/// Exits `0` after publishing both files, `1` for a value-taking option that
/// ended the line or a failed read or write, and `2` for an unusable line.
pub fn context(arguments: &[OsString]) -> ExitCode {
    match parse_context_arguments(arguments) {
        ContextArguments::Help => write_stdout(&format!("{CONTEXT_USAGE}\n")),
        ContextArguments::MissingValue => ExitCode::from(CONTEXT_MISSING_VALUE_RC),
        ContextArguments::Usage => {
            eprintln!("{CONTEXT_USAGE}");
            ExitCode::from(CONTEXT_USAGE_RC)
        }
        ContextArguments::Valid {
            issue,
            repo,
            tmpdir,
        } => publish_context(&issue, &repo, &tmpdir),
    }
}

/// One `issue context` command line, as its scanner reads it.
#[derive(Clone, Debug, Eq, PartialEq)]
enum ContextArguments {
    Help,
    MissingValue,
    Usage,
    Valid {
        issue: String,
        repo: String,
        tmpdir: PathBuf,
    },
}

/// Scan and validate the option pairs `issue context` requires.
///
/// `--help` wins at a token position, so it is only honored when it is not
/// already being consumed as some option's value.
fn parse_context_arguments(arguments: &[OsString]) -> ContextArguments {
    let mut issue = String::new();
    let mut repo = String::new();
    let mut tmpdir = String::new();
    let mut index = 0;
    while index < arguments.len() {
        let token = arguments[index].to_string_lossy().into_owned();
        if token == "--help" {
            return ContextArguments::Help;
        }
        let target = match token.as_str() {
            "--issue" => &mut issue,
            "--repo" => &mut repo,
            "--tmpdir" => &mut tmpdir,
            _ => return ContextArguments::Usage,
        };
        let Some(value) = arguments.get(index + 1) else {
            return ContextArguments::MissingValue;
        };
        *target = value.to_string_lossy().into_owned();
        index += 2;
    }
    if !positive_issue_text(&issue) || !valid_context_repo(&repo) || tmpdir.is_empty() {
        return ContextArguments::Usage;
    }
    ContextArguments::Valid {
        issue,
        repo,
        tmpdir: PathBuf::from(tmpdir),
    }
}

/// Match the legacy `[1-9][0-9]*` issue spelling.
fn positive_issue_text(issue: &str) -> bool {
    issue.bytes().all(|byte| byte.is_ascii_digit()) && !issue.starts_with('0') && !issue.is_empty()
}

/// Match the legacy `[A-Za-z0-9._-]+/[A-Za-z0-9._-]+` repository spelling.
fn valid_context_repo(repo: &str) -> bool {
    let Some((owner, name)) = repo.split_once('/') else {
        return false;
    };
    context_repo_part(owner) && context_repo_part(name)
}

fn context_repo_part(part: &str) -> bool {
    !part.is_empty()
        && part
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
}

fn publish_context(issue: &str, repo: &str, tmpdir: &Path) -> ExitCode {
    let subject = match read_issue(repo, issue) {
        Ok(subject) => subject,
        Err(detail) => return emit_failed(&read_failure(&detail)),
    };
    let title_file = tmpdir.join(TITLE_FILE_NAME);
    let body_file = tmpdir.join(BODY_FILE_NAME);
    let (Some(title_row), Some(body_row)) = (kv_path(&title_file), kv_path(&body_file)) else {
        return emit_failed("issue context write failed: context path is not a usable value");
    };
    if let Err(detail) = write_context_files(tmpdir, &subject.title, &subject.body) {
        return emit_failed(&detail);
    }
    emit_kv("TITLE_FILE", &title_row);
    emit_kv("BODY_FILE", &body_row);
    ExitCode::SUCCESS
}

/// Publish both artifacts below a confined, non-symlinked temporary root.
fn write_context_files(tmpdir: &Path, title: &str, body: &str) -> Result<(), String> {
    let absolute = absolute_path(tmpdir).map_err(|error| write_failure(&error))?;
    ensure_directory_chain(&absolute).map_err(|error| write_failure(&error))?;
    let root = TemporaryRoot::resolve(Some(&absolute)).map_err(|error| write_failure(&error))?;
    for (name, text) in [(TITLE_FILE_NAME, title), (BODY_FILE_NAME, body)] {
        let target = root
            .confine(name, PathIntent::Write)
            .map_err(|error| write_failure(&error))?;
        atomic_write_utf8(&target, text, CONTEXT_FILE_MODE)
            .map_err(|error| write_failure(&error))?;
    }
    Ok(())
}

fn write_failure(error: &impl ToString) -> String {
    format!("issue context write failed: {}", error.to_string())
}

// ----------------------------------------------------------------------- shared

/// Read one issue through the typed GitHub adapter.
///
/// `issue` arrives as text because the legacy scanners validated its spelling,
/// not its magnitude; a value too large to be an issue number is reported the
/// same way an unreachable API is.
fn read_issue(repo: &str, issue: &str) -> Result<GitHubIssue, String> {
    let number = issue
        .parse::<u64>()
        .map_err(|_| "issue number is out of range".to_owned())?;
    let reference = repository_ref(repo).map_err(|()| "repository slug is invalid".to_owned())?;
    with_github_service(async |service, cancellation| {
        service
            .issue(&reference, number, cancellation)
            .await
            .map_err(|error| read_reason(error.kind()).to_owned())
    })
    .map_err(ServiceFailure::into_detail)
}

/// Render the operator-facing reason for one refused read.
///
/// The typed error's own text is the transport crate's terse label — a `404`
/// renders as the bare word `GitHub` — so the classified kind carries the
/// meaning instead. Every reason is fixed text, so a refusal can neither leak
/// a credential nor vary between runs.
const fn read_reason(kind: GitHubOperationErrorKind) -> &'static str {
    match kind {
        GitHubOperationErrorKind::InvalidInput => "GitHub rejected the request",
        GitHubOperationErrorKind::Authentication => "GitHub authentication failed",
        GitHubOperationErrorKind::Permission => "GitHub permission denied",
        GitHubOperationErrorKind::SsoRequired => "GitHub SSO authorization is required",
        GitHubOperationErrorKind::NotFound => "issue not found",
        GitHubOperationErrorKind::RateLimited => "GitHub rate limit reached",
        GitHubOperationErrorKind::MalformedResponse => "GitHub response was malformed",
        GitHubOperationErrorKind::LimitExceeded => "GitHub response exceeded its bounded limit",
        GitHubOperationErrorKind::Transport => "GitHub is unreachable",
        GitHubOperationErrorKind::AmbiguousMutation => "GitHub read completed ambiguously",
        GitHubOperationErrorKind::Cancelled => "GitHub read was cancelled",
        GitHubOperationErrorKind::DeadlineExceeded => "GitHub read exceeded its deadline",
    }
}

/// Render the legacy state token for one issue.
///
/// `All` is a request-side list filter that a single-issue read never returns.
/// Rendering it as the empty state keeps the row present and keeps every
/// consumer's `OPEN`/`CLOSED` comparison failing closed.
const fn state_text(state: GitHubIssueState) -> &'static str {
    match state {
        GitHubIssueState::Open => "OPEN",
        GitHubIssueState::Closed => "CLOSED",
        GitHubIssueState::All => "",
    }
}

/// Prefix a refusal with the phrase every legacy consumer's log carries.
fn read_failure(detail: &str) -> String {
    format!("gh issue view failed: {detail}")
}

/// Publish the refusal envelope every consumer of these verbs parses.
///
/// The detail is scrubbed before it reaches the contract stream: a refusal can
/// carry an adapter diagnostic or a session path, and the legacy `issue
/// context` refusal already redacted its own (G-Sec-3).
fn emit_failed(message: &str) -> ExitCode {
    emit_kv("FAILED", "true");
    emit_kv("ERROR", &single_line(redact(message).text()));
    ExitCode::from(1)
}

/// Return whether a value can be published without forging a contract row.
fn kv_safe(value: &str) -> bool {
    !value.contains(['\n', '\r'])
}

/// Render a path as a publishable KV value, rejecting one that cannot be.
fn kv_path(path: &Path) -> Option<String> {
    let text = path.to_str()?.to_owned();
    kv_safe(&text).then_some(text)
}

#[cfg(test)]
mod tests {
    use super::{BODY_FILE_NAME, TITLE_FILE_NAME, write_context_files};
    use super::{
        ContextArguments, InfoArguments, InfoField, StateArguments, kv_path, kv_safe,
        parse_context_arguments, parse_info_arguments, parse_state_arguments, positive_issue_text,
        read_failure, read_reason, state_text, valid_context_repo,
    };
    use larch_core::{GitHubIssueState, GitHubOperationErrorKind};
    use std::{ffi::OsString, fs, os::unix::fs::PermissionsExt as _, path::Path, path::PathBuf};

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    fn valid_state(issue: &str, repo: Option<&str>) -> StateArguments {
        StateArguments::Valid {
            issue: issue.to_owned(),
            repo: repo.map(str::to_owned),
        }
    }

    #[test]
    fn the_state_scanner_reads_both_options_in_either_order() {
        assert_eq!(
            parse_state_arguments(&arguments(&["--issue", "42", "--repo", "o/r"])),
            valid_state("42", Some("o/r"))
        );
        assert_eq!(
            parse_state_arguments(&arguments(&["--repo", "o/r", "--issue", "42"])),
            valid_state("42", Some("o/r"))
        );
        assert_eq!(
            parse_state_arguments(&arguments(&["--issue", "42"])),
            valid_state("42", None)
        );
    }

    #[test]
    fn the_state_scanner_treats_an_option_shaped_value_as_missing() {
        // The legacy scanner rejected `--issue --repo o/r` rather than reading
        // `--repo` as the issue number, so a transposed line stays a refusal.
        assert_eq!(
            parse_state_arguments(&arguments(&["--issue", "--repo", "o/r"])),
            StateArguments::Invalid("--issue requires a value".to_owned())
        );
        assert_eq!(
            parse_state_arguments(&arguments(&["--repo"])),
            StateArguments::Invalid("--repo requires a value".to_owned())
        );
    }

    #[test]
    fn the_state_scanner_refuses_unknown_tokens_and_unusable_issues() {
        assert_eq!(
            parse_state_arguments(&arguments(&["--bogus"])),
            StateArguments::Invalid("unknown flag: --bogus".to_owned())
        );
        // Inline spelling is not an option spelling here; it reads as unknown.
        assert_eq!(
            parse_state_arguments(&arguments(&["--issue=42"])),
            StateArguments::Invalid("unknown flag: --issue=42".to_owned())
        );
        assert_eq!(
            parse_state_arguments(&[]),
            StateArguments::Invalid("--issue is required".to_owned())
        );
        assert_eq!(
            parse_state_arguments(&arguments(&["--issue", "12a"])),
            StateArguments::Invalid("--issue must be numeric".to_owned())
        );
    }

    #[test]
    fn the_info_scanner_skips_unknown_tokens_and_keeps_scanning() {
        let parsed = parse_info_arguments(&arguments(&[
            "noise", "--issue", "7", "--field", "url", "--repo", "o/r",
        ]));

        let request = parsed.request();
        assert!(
            request.is_none(),
            "an unrecognized token suppresses the read"
        );
        assert_eq!(
            parsed,
            InfoArguments::Scanned {
                issue: "7".to_owned(),
                field: "url".to_owned(),
                repo: "o/r".to_owned(),
                unknown: true,
            }
        );
    }

    #[test]
    fn the_info_scanner_accepts_option_shaped_values() {
        // Unlike `issue state`, this scanner consumes the next token whatever it
        // looks like, so a nonsense value still parses and simply reads nothing.
        let parsed = parse_info_arguments(&arguments(&["--issue", "--repo", "--field", "state"]));

        let request = parsed.request().expect("a usable line");
        assert_eq!(request.issue, "--repo");
        assert_eq!(request.field, InfoField::State);
        assert_eq!(request.repo, "");
    }

    #[test]
    fn the_info_scanner_reports_a_trailing_option_as_missing_value() {
        assert_eq!(
            parse_info_arguments(&arguments(&["--issue", "7", "--field"])),
            InfoArguments::MissingValue
        );
        assert_eq!(
            parse_info_arguments(&arguments(&["--issue"])).request(),
            None
        );
    }

    #[test]
    fn only_state_and_url_are_readable_fields() {
        for field in ["state", "url"] {
            let parsed = parse_info_arguments(&arguments(&["--issue", "7", "--field", field]));
            assert!(parsed.request().is_some(), "{field}");
        }
        for field in ["", "title", "body", "STATE"] {
            let parsed = parse_info_arguments(&arguments(&["--issue", "7", "--field", field]));
            assert!(parsed.request().is_none(), "{field}");
        }
        let missing_issue = parse_info_arguments(&arguments(&["--field", "state"]));
        assert!(missing_issue.request().is_none());
    }

    #[test]
    fn the_context_scanner_requires_every_option() {
        assert_eq!(
            parse_context_arguments(&arguments(&[
                "--issue", "7", "--repo", "o/r", "--tmpdir", "/t"
            ])),
            ContextArguments::Valid {
                issue: "7".to_owned(),
                repo: "o/r".to_owned(),
                tmpdir: PathBuf::from("/t"),
            }
        );
        for line in [
            &["--issue", "7", "--repo", "o/r"][..],
            &["--repo", "o/r", "--tmpdir", "/t"][..],
            &["--issue", "7", "--tmpdir", "/t"][..],
            &[][..],
        ] {
            assert_eq!(
                parse_context_arguments(&arguments(line)),
                ContextArguments::Usage,
                "{line:?}"
            );
        }
    }

    #[test]
    fn the_context_scanner_separates_its_three_refusals() {
        assert_eq!(
            parse_context_arguments(&arguments(&["--help"])),
            ContextArguments::Help
        );
        // `--help` after a value-taking option is that option's value, not help.
        assert_eq!(
            parse_context_arguments(&arguments(&["--issue", "--help"])),
            ContextArguments::Usage
        );
        assert_eq!(
            parse_context_arguments(&arguments(&["--issue"])),
            ContextArguments::MissingValue
        );
        assert_eq!(
            parse_context_arguments(&arguments(&["--bogus", "x"])),
            ContextArguments::Usage
        );
    }

    #[test]
    fn context_validates_the_issue_and_repository_spellings() {
        assert!(positive_issue_text("7"));
        assert!(positive_issue_text("8167"));
        for issue in ["", "0", "07", "-1", "7a", " 7"] {
            assert!(!positive_issue_text(issue), "{issue}");
        }
        assert!(valid_context_repo("character-ai/larch"));
        assert!(valid_context_repo("o_1.x/r-2"));
        for repo in ["", "owner", "owner/", "/repo", "o/r/x", "o r/x", "o/r\n"] {
            assert!(!valid_context_repo(repo), "{repo}");
        }
    }

    #[test]
    fn states_render_as_the_legacy_tokens() {
        assert_eq!(state_text(GitHubIssueState::Open), "OPEN");
        assert_eq!(state_text(GitHubIssueState::Closed), "CLOSED");
        // A single-issue read never yields the list-side filter, and an empty
        // token keeps every consumer's OPEN comparison failing closed.
        assert_eq!(state_text(GitHubIssueState::All), "");
    }

    #[test]
    fn refusals_carry_the_phrase_consumers_grep_for() {
        assert_eq!(
            read_failure("could not resolve repo"),
            "gh issue view failed: could not resolve repo"
        );
    }

    #[test]
    fn every_read_refusal_names_its_cause_in_fixed_text() {
        // A missing issue is the refusal operators hit most, and the transport
        // crate renders its 404 as the bare word `GitHub`, so the mapping is
        // what makes the row readable at all.
        assert_eq!(
            read_reason(GitHubOperationErrorKind::NotFound),
            "issue not found"
        );
        for kind in [
            GitHubOperationErrorKind::InvalidInput,
            GitHubOperationErrorKind::Authentication,
            GitHubOperationErrorKind::Permission,
            GitHubOperationErrorKind::SsoRequired,
            GitHubOperationErrorKind::NotFound,
            GitHubOperationErrorKind::RateLimited,
            GitHubOperationErrorKind::MalformedResponse,
            GitHubOperationErrorKind::LimitExceeded,
            GitHubOperationErrorKind::Transport,
            GitHubOperationErrorKind::AmbiguousMutation,
            GitHubOperationErrorKind::Cancelled,
            GitHubOperationErrorKind::DeadlineExceeded,
        ] {
            let reason = read_reason(kind);
            assert!(!reason.is_empty(), "{kind:?}");
            assert!(kv_safe(reason), "{kind:?}");
        }
    }

    #[test]
    fn a_value_carrying_a_line_break_is_never_publishable() {
        assert!(kv_safe("https://github.com/o/r/issues/1"));
        assert!(!kv_safe("first\nERROR=forged"));
        assert!(!kv_safe("first\rsecond"));
        assert_eq!(
            kv_path(Path::new("/t/upstream-issue-title.txt")).as_deref(),
            Some("/t/upstream-issue-title.txt")
        );
        assert_eq!(kv_path(Path::new("/t/a\nb")), None);
    }

    // Publication needs a GitHub read no hermetic parity sandbox can serve, so
    // the write half is proven here instead.
    #[test]
    fn context_publication_creates_the_directory_and_both_owner_only_files() {
        let sandbox = tempfile::tempdir().expect("temporary directory");
        // A missing nested target exercises the directory-chain creation the
        // legacy `mkdir(parents=True, exist_ok=True)` performed.
        let tmpdir = sandbox.path().join("run").join("context");

        write_context_files(&tmpdir, "A title", "A body\nwith two lines\n")
            .expect("publication should succeed");

        let title = tmpdir.join(TITLE_FILE_NAME);
        let body = tmpdir.join(BODY_FILE_NAME);
        assert_eq!(fs::read_to_string(&title).expect("title"), "A title");
        assert_eq!(
            fs::read_to_string(&body).expect("body"),
            "A body\nwith two lines\n"
        );
        for artifact in [&title, &body] {
            let mode = fs::metadata(artifact)
                .expect("metadata")
                .permissions()
                .mode()
                & 0o777;
            assert_eq!(mode, 0o600, "{}", artifact.display());
        }
        // Republishing over the existing artifacts stays idempotent, and leaves
        // no partial temporary file behind.
        write_context_files(&tmpdir, "Second", "").expect("republication should succeed");
        assert_eq!(fs::read_to_string(&title).expect("title"), "Second");
        assert_eq!(fs::read_to_string(&body).expect("body"), "");
        let published: Vec<String> = fs::read_dir(&tmpdir)
            .expect("directory")
            .map(|entry| {
                entry
                    .expect("entry")
                    .file_name()
                    .to_string_lossy()
                    .into_owned()
            })
            .collect();
        assert_eq!(published.len(), 2, "{published:?}");
    }

    #[test]
    fn context_publication_refuses_a_symlinked_root() {
        let sandbox = tempfile::tempdir().expect("temporary directory");
        let real = sandbox.path().join("real");
        fs::create_dir(&real).expect("real directory");
        let linked = sandbox.path().join("linked");
        std::os::unix::fs::symlink(&real, &linked).expect("symlink");

        let refusal = write_context_files(&linked, "title", "body")
            .expect_err("a symlinked root must be refused");

        assert!(
            refusal.starts_with("issue context write failed: "),
            "{refusal}"
        );
        assert!(!real.join(TITLE_FILE_NAME).exists());
    }
}
