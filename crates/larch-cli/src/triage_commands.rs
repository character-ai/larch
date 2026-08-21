//! The `/triage` verbs: immutable-main evidence, bounded probes, and the one
//! verified issue mutation a verdict is allowed to publish.
//!
//! `/triage` is the pre-`/design` verification skill. It reads an existing
//! report whose body, comments, and cited logs are written by anyone, proves or
//! refutes the diagnosis against evidence, and then makes at most one issue
//! change. Everything here exists to keep those three phases apart:
//!
//! * `inspect` reads code and logs only through an immutable object. A moving
//!   reference is resolved to the exact commit it names before anything is
//!   read, and the read itself is a blob lookup in that commit's tree — never
//!   the working tree, never a mutable local branch.
//! * `probe` is the only executable reproduction surface. The name and the
//!   argument shape come from a fixed allowlist, the child runs with an
//!   argument vector and no shell, its environment is the runtime's own closed
//!   inheritance allowlist, and its output is bounded and sanitized.
//! * `apply` is fail-closed. Verification runs before every mutation and again
//!   between mutations, every write goes through the shared issue-mutation
//!   owner's compare-and-swap, and a security classification, a protected
//!   lifecycle state, or a stale snapshot refuses the write rather than
//!   racing it.
//!
//! Issue text, probe output, and repository content are untrusted (G-Sec-2):
//! they are classified, redacted, and republished, never interpreted. Outbound
//! prose is refused when the scrub cannot prove itself (G-Sec-3).

use crate::{
    argparse_compat::{ParsedCommandLine, parse_with_flags},
    child_process::{bounded_request, run_bounded_detailed},
    github_repository_resolution::repository_ref,
    github_service::{ServiceFailure, with_github_service},
    issue_mutation_support::{authorization_request, authorized},
};
use larch_adapters::{
    FetchRequest, GitCli, GitCliPolicy, GitRef, GitRefspec, GitRemote, GixRepository,
    TokioProcessRunner,
    github::{IssueMutationOwner, OctocrabGitHubService},
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    GitHubIssueState, GitHubRepositoryRef, GitHubService, IssueMutationField, IssueMutationRequest,
    IssueMutationSnapshot, MAX_TRIAGE_EVIDENCE_BYTES, MAX_TRIAGE_PROBE_BYTES, ObjectHash, ObjectId,
    ObjectKind, ProcessCancellation, ProcessErrorKind, RepositoryRead, Revision,
    TRIAGE_PROBE_TIMEOUT_SECONDS, TRIAGE_TMP_PREFIX, TRIAGE_VERDICT_COMMENT_PREFIX,
    TriageProbeError, TriageSanitizeError, emit_kv, is_python_whitespace, redact_outbound,
    replace_triage_block, sanitize_triage_outbound, strip_triage_lifecycle_prefixes,
    triage_label_is_security, triage_probe_command, triage_text_is_security_sensitive,
    triage_title_has_lifecycle_prefix, triaged_title, validate_triage_evidence_path,
};
use std::{
    collections::BTreeSet,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

/// Exit code for an unusable command line or an unusable local input.
const EXIT_USAGE: u8 = 2;
/// Exit code for a live mutation the authorization gate refused.
const EXIT_AUTHORIZATION: u8 = 3;
/// Exit code for an issue that moved since the verified snapshot.
const EXIT_STALE: u8 = 4;
/// Exit code for an issue whose lifecycle or classification forbids the write.
const EXIT_PROTECTED: u8 = 5;
/// Exit code for outbound prose the redaction pass would not publish.
const EXIT_REDACTION: u8 = 6;
/// Exit code for a mutation GitHub refused.
const EXIT_MUTATION: u8 = 7;
/// Exit code for a postcondition the read-back did not prove.
const EXIT_POSTCONDITION: u8 = 8;
/// Characters of a diagnostic one contract row carries.
const DIAGNOSTIC_CHARS: usize = 1000;
/// Bytes a probe child may buffer before the runtime stops reading.
const PROBE_CAPTURE_LIMIT: usize = 1024 * 1024;
/// Grace a probe child gets between its deadline and its termination.
const PROBE_SHUTDOWN_GRACE: Duration = Duration::from_secs(2);
/// Exit code Python's runner reported for a probe that ran out of time.
const PROBE_TIMEOUT_EXIT_CODE: i32 = 124;
/// Exit code Python's runner reported for a probe whose program is absent.
const PROBE_MISSING_EXIT_CODE: i32 = 127;
/// Hexadecimal characters in the only object hash a citation may name.
const SHA_CHARS: usize = 40;
/// Fields one `ls-remote` line carries for an exact reference.
const LS_REMOTE_FIELDS: usize = 2;
/// The canonical temporary root a triage session is confined to (G-Sec-4).
const TMP_ROOT: &str = "/tmp";
/// Verdicts that close the issue rather than republishing its body.
const CLOSE_VERDICTS: [&str; 3] = ["already-fixed", "invalid", "duplicate"];
/// Every verdict `--verdict` accepts, in the order `argparse` printed them.
const VERDICTS: [&str; 5] = [
    "valid",
    "already-fixed",
    "duplicate",
    "invalid",
    "inconclusive",
];

const INSPECT_USAGE: &str = concat!(
    "usage: triage inspect [-h] [--repo-root REPO_ROOT] [--ref REF] [--path PATH]\n",
    "                      [--max-bytes MAX_BYTES]",
);
const INSPECT_HELP: &str = concat!(
    "usage: triage inspect [-h] [--repo-root REPO_ROOT] [--ref REF] [--path PATH]\n",
    "                      [--max-bytes MAX_BYTES]\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --repo-root REPO_ROOT\n",
    "  --ref REF\n",
    "  --path PATH\n",
    "  --max-bytes MAX_BYTES\n",
);
const PROBE_USAGE: &str =
    "usage: triage probe [-h] --name NAME [--arg ARG] [--max-bytes MAX_BYTES]";
const PROBE_HELP: &str = concat!(
    "usage: triage probe [-h] --name NAME [--arg ARG] [--max-bytes MAX_BYTES]\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --name NAME\n",
    "  --arg ARG\n",
    "  --max-bytes MAX_BYTES\n",
);
const APPLY_USAGE: &str = concat!(
    "usage: triage apply [-h] --repo REPO --verdict\n",
    "                    {valid,already-fixed,duplicate,invalid,inconclusive}\n",
    "                    --expected-updated-at EXPECTED_UPDATED_AT --triage-root\n",
    "                    TRIAGE_ROOT [--body-file BODY_FILE]\n",
    "                    [--comment-file COMMENT_FILE]\n",
    "                    [--canonical-duplicate CANONICAL_DUPLICATE]\n",
    "                    [--operator-invoked]\n",
    "                    issue",
);
const APPLY_HELP: &str = concat!(
    "usage: triage apply [-h] --repo REPO --verdict\n",
    "                    {valid,already-fixed,duplicate,invalid,inconclusive}\n",
    "                    --expected-updated-at EXPECTED_UPDATED_AT --triage-root\n",
    "                    TRIAGE_ROOT [--body-file BODY_FILE]\n",
    "                    [--comment-file COMMENT_FILE]\n",
    "                    [--canonical-duplicate CANONICAL_DUPLICATE]\n",
    "                    [--operator-invoked]\n",
    "                    issue\n",
    "\n",
    "positional arguments:\n",
    "  issue\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --repo REPO\n",
    "  --verdict {valid,already-fixed,duplicate,invalid,inconclusive}\n",
    "  --expected-updated-at EXPECTED_UPDATED_AT\n",
    "  --triage-root TRIAGE_ROOT\n",
    "  --body-file BODY_FILE\n",
    "  --comment-file COMMENT_FILE\n",
    "  --canonical-duplicate CANONICAL_DUPLICATE\n",
    "  --operator-invoked\n",
);

/// One user-safe triage failure with the stable exit class its caller branches on.
#[derive(Clone, Debug, Eq, PartialEq)]
struct TriageError {
    message: String,
    code: u8,
}

impl TriageError {
    fn new(message: impl Into<String>, code: u8) -> Self {
        Self {
            message: message.into(),
            code,
        }
    }

    /// Name the failure class the `TRIAGE_FAILURE=` row publishes.
    const fn kind(&self) -> &'static str {
        match self.code {
            EXIT_AUTHORIZATION => "authorization",
            EXIT_STALE => "stale-snapshot",
            EXIT_PROTECTED => "protected-state",
            EXIT_REDACTION => "redaction",
            EXIT_MUTATION => "mutation",
            EXIT_POSTCONDITION => "postcondition",
            _ => "validation",
        }
    }
}

/// Collapse one diagnostic into a single redacted, printable contract value.
fn flat(message: &str) -> String {
    redact_outbound(message)
        .replace(['\r', '\n'], " ")
        .trim_matches(is_python_whitespace)
        .chars()
        .take(DIAGNOSTIC_CHARS)
        .collect()
}

/// Report one `argparse` refusal the way the Python entrypoints did.
///
/// `argparse` writes both lines to stderr and raises `SystemExit(2)`, which
/// every triage entrypoint turned into its usage exit code without publishing a
/// contract row.
fn argparse_error(usage: &str, program: &str, error: &str) -> ExitCode {
    eprintln!("{usage}");
    eprintln!("{program}: error: {error}");
    ExitCode::from(EXIT_USAGE)
}

/// Print an `argparse` help block, which still exits `2` here.
///
/// The Python entrypoints caught every `SystemExit`, including the successful
/// one `--help` raises, and returned their usage exit code from the handler.
fn argparse_help(help: &str) -> ExitCode {
    print!("{help}");
    ExitCode::from(EXIT_USAGE)
}

fn help_requested(parsed: &ParsedCommandLine) -> bool {
    parsed.flag("--help") || parsed.flag("-h")
}

const fn bool_text(value: bool) -> &'static str {
    if value { "true" } else { "false" }
}

/// Read one option the way `argparse`'s `type=int` did, or report it unusable.
fn integer_option(parsed: &ParsedCommandLine, option: &'static str) -> Result<Option<i64>, ()> {
    let Some(raw) = parsed.value(option) else {
        return Ok(None);
    };
    raw.to_string_lossy()
        .trim_matches(is_python_whitespace)
        .parse::<i64>()
        .map(Some)
        .map_err(|_| ())
}

/// Render the `argparse` diagnostic for an option that is not an integer.
fn invalid_int(parsed: &ParsedCommandLine, option: &str) -> String {
    format!(
        "argument {option}: invalid int value: '{}'",
        parsed.value(option).unwrap_or_default().to_string_lossy()
    )
}

// ------------------------------------------------------------------- inspect

/// One validated immutable-evidence request.
struct InspectRequest {
    repo_root: PathBuf,
    reference: String,
    path: Option<String>,
    max_bytes: usize,
}

/// Resolve and read evidence only through an immutable fixed-origin object.
pub fn inspect(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &["--repo-root", "--ref", "--path", "--max-bytes"],
        &["-h", "--help"],
        0,
    );
    if let Some(error) = parsed.value_error() {
        return argparse_error(INSPECT_USAGE, "triage inspect", error);
    }
    if help_requested(&parsed) {
        return argparse_help(INSPECT_HELP);
    }
    if let Some(error) = parsed.error() {
        return argparse_error(INSPECT_USAGE, "triage inspect", &error);
    }
    let Ok(max_bytes) = integer_option(&parsed, "--max-bytes") else {
        return argparse_error(
            INSPECT_USAGE,
            "triage inspect",
            &invalid_int(&parsed, "--max-bytes"),
        );
    };
    match run_inspect(&parsed, max_bytes) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            emit_kv("EVIDENCE_STATUS", "gap");
            emit_kv("EVIDENCE_GAP", &flat(&error.message));
            ExitCode::from(error.code)
        }
    }
}

fn run_inspect(parsed: &ParsedCommandLine, max_bytes: Option<i64>) -> Result<(), TriageError> {
    // Python read the default through `Path(args.repo_root)`, where an empty
    // `--repo-root` is `Path("")`, whose `resolve()` is the working directory.
    let repo_root = PathBuf::from(
        parsed
            .value("--repo-root")
            .map(|value| value.to_string_lossy().into_owned())
            .filter(|value| !value.is_empty())
            .unwrap_or_else(|| ".".to_owned()),
    );
    let repo_root = fs::canonicalize(&repo_root)
        .map_err(|_| TriageError::new("--repo-root is not a directory", EXIT_USAGE))?;
    if !repo_root.is_dir() {
        return Err(TriageError::new(
            "--repo-root is not a directory",
            EXIT_USAGE,
        ));
    }
    // Python branched on `if args.path`, so an empty `--path` reads as absent.
    let path = match parsed.value("--path").filter(|value| !value.is_empty()) {
        None => None,
        Some(raw) => Some(
            validate_triage_evidence_path(&raw.to_string_lossy())
                .ok_or_else(|| evidence_path_refusal(&raw.to_string_lossy()))?,
        ),
    };
    let max_bytes =
        max_bytes.unwrap_or_else(|| i64::try_from(MAX_TRIAGE_EVIDENCE_BYTES).unwrap_or(i64::MAX));
    if max_bytes < 1 || max_bytes > i64::try_from(MAX_TRIAGE_EVIDENCE_BYTES).unwrap_or(i64::MAX) {
        return Err(TriageError::new(
            "--max-bytes is outside the supported evidence cap",
            EXIT_USAGE,
        ));
    }
    let request = InspectRequest {
        repo_root,
        reference: parsed.value("--ref").map_or_else(
            || "refs/heads/main".to_owned(),
            |value| value.to_string_lossy().into_owned(),
        ),
        path,
        max_bytes: usize::try_from(max_bytes).unwrap_or(MAX_TRIAGE_EVIDENCE_BYTES),
    };
    let slug = origin_slug(&request)?;
    let (sha, source_ref) = resolve_reference(&request)?;
    emit_kv("EVIDENCE_STATUS", "ok");
    emit_kv("REPOSITORY", &slug);
    emit_kv("IMMUTABLE_SHA", &sha);
    emit_kv("SOURCE_REF", &source_ref);
    let Some(path) = request.path.as_deref() else {
        emit_kv("EVIDENCE_TRUNCATED", "false");
        return Ok(());
    };
    let blob = read_blob(&request, &sha, path)?;
    // Python decoded the blob with `errors="replace"` and only then bounded the
    // encoded bytes, so an undecodable byte counts as its replacement rather
    // than as itself.
    let decoded = String::from_utf8_lossy(&blob);
    let encoded = decoded.as_bytes();
    let truncated = encoded.len() > request.max_bytes;
    let content =
        String::from_utf8_lossy(&encoded[..encoded.len().min(request.max_bytes)]).into_owned();
    emit_kv("EVIDENCE_PATH", path);
    emit_kv("EVIDENCE_TRUNCATED", bool_text(truncated));
    println!("EVIDENCE_CONTENT_BEGIN");
    let redacted = redact_outbound(&content);
    if content.ends_with('\n') {
        print!("{redacted}");
    } else {
        println!("{redacted}");
    }
    println!("EVIDENCE_CONTENT_END");
    Ok(())
}

/// Name the exact refusal an unusable evidence path takes.
fn evidence_path_refusal(value: &str) -> TriageError {
    if value.is_empty() || value.contains('\0') || value.contains('\\') {
        return TriageError::new("evidence path is invalid", EXIT_USAGE);
    }
    TriageError::new(
        "evidence path must be a bounded repository-relative path",
        EXIT_USAGE,
    )
}

/// Read the fixed origin remote and report the GitHub slug it names.
fn origin_slug(request: &InspectRequest) -> Result<String, TriageError> {
    let repository = open_repository(request)?;
    let remotes = repository
        .remotes()
        .map_err(|_| TriageError::new("fixed origin remote is unavailable", EXIT_POSTCONDITION))?;
    let url = remotes
        .into_iter()
        .find(|remote| remote.name == b"origin")
        .and_then(|remote| remote.fetch_url)
        .ok_or_else(|| {
            TriageError::new("fixed origin remote is unavailable", EXIT_POSTCONDITION)
        })?;
    github_slug(&String::from_utf8_lossy(&url)).ok_or_else(|| {
        TriageError::new(
            "origin is not a validated GitHub repository remote",
            EXIT_POSTCONDITION,
        )
    })
}

/// Return the `owner/name` slug one GitHub remote URL names.
fn github_slug(url: &str) -> Option<String> {
    let trimmed = url.trim_matches(is_python_whitespace);
    let rest = [
        "https://github.com/",
        "git@github.com:",
        "ssh://git@github.com/",
    ]
    .into_iter()
    .find_map(|prefix| trimmed.strip_prefix(prefix))?;
    let slug = rest.strip_suffix(".git").unwrap_or(rest);
    let (owner, name) = slug.split_once('/')?;
    let usable = |part: &str| {
        !part.is_empty()
            && part
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
    };
    (usable(owner) && usable(name) && !name.contains('/')).then(|| slug.to_owned())
}

/// Resolve the cited reference to the immutable commit it names.
fn resolve_reference(request: &InspectRequest) -> Result<(String, String), TriageError> {
    if request.reference == "main" || request.reference == "refs/heads/main" {
        let sha = resolve_origin_main(request)?;
        ensure_commit(request, &sha, "immutable main object is unavailable")?;
        return Ok((sha, "refs/heads/main".to_owned()));
    }
    if is_object_hash(&request.reference) {
        let sha = request.reference.to_ascii_lowercase();
        ensure_commit(request, &sha, "cited immutable commit is unavailable")?;
        return Ok((sha.clone(), sha));
    }
    if pull_request_head(&request.reference).is_some() {
        return Ok((resolve_pull_head(request)?, request.reference.clone()));
    }
    Err(TriageError::new(
        "ref must be main, a full commit SHA, or refs/pull/<N>/head",
        EXIT_USAGE,
    ))
}

fn is_object_hash(value: &str) -> bool {
    value.len() == SHA_CHARS && value.bytes().all(|byte| byte.is_ascii_hexdigit())
}

/// Return the pull-request number a `refs/pull/<N>/head` reference names.
fn pull_request_head(reference: &str) -> Option<u64> {
    let digits = reference
        .strip_prefix("refs/pull/")?
        .strip_suffix("/head")?;
    (!digits.starts_with('0') && !digits.is_empty() && digits.bytes().all(|b| b.is_ascii_digit()))
        .then(|| digits.parse::<u64>().ok())
        .flatten()
}

/// Ask the fixed origin for the exact object `refs/heads/main` points at.
fn resolve_origin_main(request: &InspectRequest) -> Result<String, TriageError> {
    let unresolved = || {
        TriageError::new(
            "exact origin refs/heads/main could not be resolved",
            EXIT_POSTCONDITION,
        )
    };
    let listed = git_ls_remote(request).map_err(|()| unresolved())?;
    let fields: Vec<&str> = listed.split_whitespace().collect();
    match fields.as_slice() {
        [sha, reference]
            if fields.len() == LS_REMOTE_FIELDS
                && is_object_hash(sha)
                && *reference == "refs/heads/main" =>
        {
            Ok(sha.to_ascii_lowercase())
        }
        _ => Err(unresolved()),
    }
}

/// Fetch and resolve a cited pull-request head to its immutable commit.
fn resolve_pull_head(request: &InspectRequest) -> Result<String, TriageError> {
    git_fetch(request, &request.reference).map_err(|()| {
        TriageError::new("cited pull-request ref is unavailable", EXIT_POSTCONDITION)
    })?;
    let unresolved = || {
        TriageError::new(
            "cited pull-request ref did not resolve immutably",
            EXIT_POSTCONDITION,
        )
    };
    let repository = open_repository(request)?;
    let object = repository
        .resolve_revision(&Revision::new(b"FETCH_HEAD".to_vec()))
        .map_err(|_| unresolved())?;
    let sha = object.to_hex();
    object_is_commit(&repository, &sha)
        .then_some(sha)
        .ok_or_else(unresolved)
}

/// Prove the named commit is present locally, fetching it once if it is not.
fn ensure_commit(
    request: &InspectRequest,
    sha: &str,
    unavailable: &'static str,
) -> Result<(), TriageError> {
    if object_is_commit(&open_repository(request)?, sha) {
        return Ok(());
    }
    git_fetch(request, sha).map_err(|()| TriageError::new(unavailable, EXIT_POSTCONDITION))?;
    // The fetch wrote new objects, so the repository is reopened before the
    // second look rather than answering from the first handle's packed state.
    object_is_commit(&open_repository(request)?, sha)
        .then_some(())
        .ok_or_else(|| TriageError::new(unavailable, EXIT_POSTCONDITION))
}

fn object_is_commit(repository: &GixRepository, sha: &str) -> bool {
    decode_object_id(sha).is_some_and(|id| {
        repository
            .object(&id)
            .ok()
            .flatten()
            .is_some_and(|object| object.kind == ObjectKind::Commit)
    })
}

fn decode_object_id(sha: &str) -> Option<ObjectId> {
    let digest: Option<Vec<u8>> = (0..sha.len() / 2)
        .map(|index| u8::from_str_radix(sha.get(index * 2..index * 2 + 2)?, 16).ok())
        .collect();
    ObjectId::new(ObjectHash::Sha1, digest?).ok()
}

/// Read one repository-relative path out of the immutable commit's tree.
fn read_blob(request: &InspectRequest, sha: &str, path: &str) -> Result<Vec<u8>, TriageError> {
    let missing = || {
        TriageError::new(
            "evidence path is missing from the immutable commit",
            EXIT_POSTCONDITION,
        )
    };
    let repository = open_repository(request)?;
    let id = decode_object_id(sha).ok_or_else(missing)?;
    repository
        .blob_at_commit(&id, &larch_core::GitPath::new(path.as_bytes().to_vec()))
        .map_err(|_| missing())?
        .ok_or_else(missing)
}

fn open_repository(request: &InspectRequest) -> Result<GixRepository, TriageError> {
    GixRepository::discover(&request.repo_root)
        .map_err(|_| TriageError::new("fixed origin remote is unavailable", EXIT_POSTCONDITION))
}

fn git_ls_remote(request: &InspectRequest) -> Result<String, ()> {
    let reference = GitRef::new("refs/heads/main").map_err(|_| ())?;
    let result = run_git(request, |git, cancellation| {
        Box::pin(async move {
            git.ls_remote(
                larch_adapters::LsRemoteRequest {
                    remote: GitRemote::new("origin").map_err(|_| ())?,
                    patterns: vec![reference],
                    heads: false,
                    exit_code: true,
                },
                cancellation,
            )
            .await
            .map_err(|_| ())
        })
    })?;
    Ok(result)
}

fn git_fetch(request: &InspectRequest, refspec: &str) -> Result<String, ()> {
    let refspec = GitRefspec::new(refspec).map_err(|_| ())?;
    run_git(request, |git, cancellation| {
        Box::pin(async move {
            git.fetch(
                FetchRequest {
                    remote: GitRemote::new("origin").map_err(|_| ())?,
                    refspec: Some(refspec),
                    quiet: false,
                    no_tags: true,
                },
                cancellation,
            )
            .await
            .map_err(|_| ())
        })
    })
}

/// Run one bounded Git compatibility operation and return its stdout.
fn run_git<F>(request: &InspectRequest, operation: F) -> Result<String, ()>
where
    F: for<'a> FnOnce(
        &'a GitCli<'a, TokioProcessRunner>,
        &'a Cancellation,
    ) -> std::pin::Pin<
        Box<dyn Future<Output = Result<larch_adapters::GitCliResult, ()>> + 'a>,
    >,
{
    let policy = GitCliPolicy::new(request.repo_root.clone()).map_err(|_| ())?;
    let runtime = LarchRuntime::current_thread().map_err(|_| ())?;
    runtime.block_on(async {
        let runner = TokioProcessRunner::default();
        let cancellation = Cancellation::new();
        let git = GitCli::new(&runner, policy);
        let result = operation(&git, &cancellation).await?;
        Ok(String::from_utf8_lossy(result.output().stdout()).into_owned())
    })
}

// --------------------------------------------------------------------- probe

/// Run one fixed, no-shell, bounded, credential-free reproduction probe.
pub fn probe(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &["--name", "--arg", "--max-bytes"],
        &["-h", "--help"],
        0,
    );
    if let Some(error) = parsed.value_error() {
        return argparse_error(PROBE_USAGE, "triage probe", error);
    }
    if help_requested(&parsed) {
        return argparse_help(PROBE_HELP);
    }
    if parsed.value("--name").is_none() {
        return argparse_error(
            PROBE_USAGE,
            "triage probe",
            "the following arguments are required: --name",
        );
    }
    if let Some(error) = parsed.error() {
        return argparse_error(PROBE_USAGE, "triage probe", &error);
    }
    let Ok(max_bytes) = integer_option(&parsed, "--max-bytes") else {
        return argparse_error(
            PROBE_USAGE,
            "triage probe",
            &invalid_int(&parsed, "--max-bytes"),
        );
    };
    match run_probe(&parsed, max_bytes) {
        Ok(code) => code,
        Err(error) => {
            emit_kv("PROBE_STATUS", "rejected");
            emit_kv("PROBE_FAILURE", &flat(&error.message));
            ExitCode::from(error.code)
        }
    }
}

fn run_probe(parsed: &ParsedCommandLine, max_bytes: Option<i64>) -> Result<ExitCode, TriageError> {
    let cap = i64::try_from(MAX_TRIAGE_PROBE_BYTES).unwrap_or(i64::MAX);
    let max_bytes = max_bytes.unwrap_or(cap);
    if max_bytes < 1 || max_bytes > cap {
        return Err(TriageError::new(
            "--max-bytes is outside the supported probe cap",
            EXIT_USAGE,
        ));
    }
    let max_bytes = usize::try_from(max_bytes).unwrap_or(MAX_TRIAGE_PROBE_BYTES);
    let name = parsed
        .value("--name")
        .unwrap_or_default()
        .to_string_lossy()
        .into_owned();
    let values: Vec<String> = parsed
        .values("--arg")
        .into_iter()
        .map(|value| value.to_string_lossy().into_owned())
        .collect();
    let approved = triage_probe_command(&name, &values).map_err(|error| {
        TriageError::new(
            match error {
                TriageProbeError::ShellSyntax => "probe arguments contain forbidden shell syntax",
                TriageProbeError::NotAllowed => {
                    "probe name or arguments are not in the fixed read-only allowlist"
                }
            },
            EXIT_USAGE,
        )
    })?;
    let (code, combined) = run_probe_child(approved)?;
    let encoded = combined.into_bytes();
    let truncated = encoded.len() > max_bytes;
    let output = String::from_utf8_lossy(&encoded[..encoded.len().min(max_bytes)]).into_owned();
    emit_kv(
        "PROBE_STATUS",
        if code == 0 { "completed" } else { "failed" },
    );
    emit_kv("PROBE_EXIT_CODE", &code.to_string());
    emit_kv("PROBE_TRUNCATED", bool_text(truncated));
    println!("PROBE_OUTPUT_BEGIN");
    let sanitized = sanitize_triage_outbound(&output, false).map_err(sanitize_error)?;
    if output.ends_with('\n') {
        print!("{sanitized}");
    } else {
        println!("{sanitized}");
    }
    println!("PROBE_OUTPUT_END");
    Ok(if code == 0 {
        ExitCode::SUCCESS
    } else {
        ExitCode::from(EXIT_POSTCONDITION)
    })
}

/// Launch one approved probe and report its exit code and combined output.
fn run_probe_child(approved: larch_core::TriageProbe) -> Result<(i32, String), TriageError> {
    let executable = approved.program.executable().to_string_lossy().into_owned();
    let request = bounded_request(
        approved.program,
        approved.arguments,
        Duration::from_secs(TRIAGE_PROBE_TIMEOUT_SECONDS),
        PROBE_SHUTDOWN_GRACE,
        PROBE_CAPTURE_LIMIT,
    )
    .map_err(|error| TriageError::new(error, EXIT_USAGE))?;
    match run_bounded_detailed(request) {
        Ok(output) => Ok((
            output.status().code().unwrap_or(PROBE_MISSING_EXIT_CODE),
            combined_text(output.stdout(), output.stderr()),
        )),
        Err(error) => match error.kind() {
            // Python's runner killed a probe past its deadline, kept whatever
            // the child had already written, and reported the timeout code.
            ProcessErrorKind::TimedOut => Ok((
                PROBE_TIMEOUT_EXIT_CODE,
                error.output().map_or_else(String::new, |output| {
                    combined_text(output.stdout(), output.stderr())
                }),
            )),
            // An absent probe executable was a captured result, not a crash.
            ProcessErrorKind::Spawn => Ok((
                PROBE_MISSING_EXIT_CODE,
                format!("{executable}: command not found\n"),
            )),
            _ => Err(TriageError::new(
                error.message().to_owned(),
                EXIT_POSTCONDITION,
            )),
        },
    }
}

fn combined_text(stdout: &[u8], stderr: &[u8]) -> String {
    format!(
        "{}{}",
        String::from_utf8_lossy(stdout),
        String::from_utf8_lossy(stderr)
    )
}

/// Report one refused sanitation with the class and text Python published.
fn sanitize_error(error: TriageSanitizeError) -> TriageError {
    match error {
        TriageSanitizeError::Artifact => TriageError::new(
            "triage artifact must contain only one validated triage block",
            EXIT_REDACTION,
        ),
        TriageSanitizeError::Malformed => {
            TriageError::new("malformed helper-owned triage block", EXIT_PROTECTED)
        }
        TriageSanitizeError::Unverified => TriageError::new(
            "outbound PII redaction could not be verified",
            EXIT_REDACTION,
        ),
    }
}

// --------------------------------------------------------------------- apply

/// One validated `triage apply` command line.
struct ApplyRequest {
    issue: u64,
    repository: GitHubRepositoryRef,
    verdict: String,
    expected_updated_at: String,
    artifact_text: String,
    canonical: Option<u64>,
}

/// Apply one verified verdict with per-mutation compare-and-swap checks.
pub fn apply(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &[
            "--repo",
            "--verdict",
            "--expected-updated-at",
            "--triage-root",
            "--body-file",
            "--comment-file",
            "--canonical-duplicate",
        ],
        &["-h", "--help", "--operator-invoked"],
        1,
    );
    if let Some(refusal) = apply_line_refusal(&parsed) {
        return refusal;
    }
    match run_apply(&parsed) {
        Ok(code) => code,
        Err(error) => {
            eprintln!("TRIAGE_FAILURE={}", error.kind());
            eprintln!("ERROR={}", flat(&error.message));
            emit_kv("ISSUE_UPDATED", "false");
            ExitCode::from(error.code)
        }
    }
}

/// Report the `argparse`-shaped refusals the apply command line can take.
fn apply_line_refusal(parsed: &ParsedCommandLine) -> Option<ExitCode> {
    if let Some(error) = parsed.value_error() {
        return Some(argparse_error(APPLY_USAGE, "triage apply", error));
    }
    if help_requested(parsed) {
        return Some(argparse_help(APPLY_HELP));
    }
    if let Some(verdict) = parsed.value("--verdict")
        && !VERDICTS.contains(&verdict.to_string_lossy().as_ref())
    {
        return Some(argparse_error(
            APPLY_USAGE,
            "triage apply",
            &format!(
                "argument --verdict: invalid choice: '{}' (choose from {})",
                verdict.to_string_lossy(),
                VERDICTS.map(|value| format!("'{value}'")).join(", ")
            ),
        ));
    }
    // `argparse` reports missing arguments in declaration order, and the
    // positional was declared ahead of every option.
    let mut missing: Vec<&str> = Vec::new();
    if parsed.positional(0).is_none() {
        missing.push("issue");
    }
    missing.extend(
        [
            "--repo",
            "--verdict",
            "--expected-updated-at",
            "--triage-root",
        ]
        .into_iter()
        .filter(|option| parsed.value(option).is_none()),
    );
    if !missing.is_empty() {
        return Some(argparse_error(
            APPLY_USAGE,
            "triage apply",
            &format!(
                "the following arguments are required: {}",
                missing.join(", ")
            ),
        ));
    }
    if let Some(error) = parsed.error() {
        return Some(argparse_error(APPLY_USAGE, "triage apply", &error));
    }
    for (option, raw) in [
        ("issue", parsed.positional(0)),
        (
            "--canonical-duplicate",
            parsed.value("--canonical-duplicate"),
        ),
    ] {
        if let Some(raw) = raw
            && raw
                .to_string_lossy()
                .trim_matches(is_python_whitespace)
                .parse::<i64>()
                .is_err()
        {
            return Some(argparse_error(
                APPLY_USAGE,
                "triage apply",
                &format!(
                    "argument {option}: invalid int value: '{}'",
                    raw.to_string_lossy()
                ),
            ));
        }
    }
    None
}

fn run_apply(parsed: &ParsedCommandLine) -> Result<ExitCode, TriageError> {
    let verdict = parsed
        .value("--verdict")
        .unwrap_or_default()
        .to_string_lossy()
        .into_owned();
    let issue = parsed
        .positional(0)
        .unwrap_or_default()
        .to_string_lossy()
        .trim_matches(is_python_whitespace)
        .parse::<i64>()
        .unwrap_or_default();
    let repository = parsed
        .value("--repo")
        .unwrap_or_default()
        .to_string_lossy()
        .into_owned();
    let invalid_identity =
        || TriageError::new("issue and repository arguments are invalid", EXIT_USAGE);
    if issue < 1 {
        return Err(invalid_identity());
    }
    let repository = repository_ref(&repository).map_err(|_error| invalid_identity())?;
    let expected_updated_at = parsed
        .value("--expected-updated-at")
        .unwrap_or_default()
        .to_string_lossy()
        .into_owned();
    if !is_utc_timestamp(&expected_updated_at) {
        return Err(TriageError::new(
            "--expected-updated-at must be an ISO-8601 UTC timestamp",
            EXIT_USAGE,
        ));
    }
    if verdict == "inconclusive" {
        emit_kv("TRIAGE_VERDICT", "inconclusive");
        emit_kv("ISSUE_UPDATED", "false");
        emit_kv("TRIAGE_FAILURE", "none");
        return Ok(ExitCode::SUCCESS);
    }
    let authorization = authorization_request("", "", "", parsed.flag("--operator-invoked"));
    if let Err(reason) = authorized(&authorization) {
        return Err(TriageError::new(
            format!("live mutation authorization refused: {reason}"),
            EXIT_AUTHORIZATION,
        ));
    }
    let root = canonical_triage_root(
        &parsed
            .value("--triage-root")
            .unwrap_or_default()
            .to_string_lossy(),
    )?;
    let selected = if verdict == "valid" {
        parsed.value("--body-file")
    } else {
        parsed.value("--comment-file")
    };
    let selected = selected.filter(|value| !value.is_empty()).ok_or_else(|| {
        TriageError::new(
            "verdict requires the matching body/comment artifact",
            EXIT_USAGE,
        )
    })?;
    let artifact = confined_artifact(&selected.to_string_lossy(), &root)?;
    let artifact_text = fs::read(&artifact)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .map_err(|error| TriageError::new(error.to_string(), EXIT_USAGE))?;
    let request = ApplyRequest {
        issue: u64::try_from(issue).map_err(|_| invalid_identity())?,
        repository,
        verdict,
        expected_updated_at,
        artifact_text,
        canonical: canonical_duplicate(parsed)?,
    };
    apply_verified(&request)
}

/// Read `--canonical-duplicate` as the positive issue number it must name.
///
/// The scanner already proved the value is an integer, so anything left is a
/// number no issue can carry. Python passed it on and let the canonical read
/// fail; refusing here reports the same verdict without a wasted request.
fn canonical_duplicate(parsed: &ParsedCommandLine) -> Result<Option<u64>, TriageError> {
    let Some(raw) = parsed.value("--canonical-duplicate") else {
        return Ok(None);
    };
    raw.to_string_lossy()
        .trim_matches(is_python_whitespace)
        .parse::<u64>()
        .ok()
        .filter(|number| *number > 0)
        .map(Some)
        .ok_or_else(|| {
            TriageError::new("canonical duplicate could not be verified", EXIT_PROTECTED)
        })
}

/// Accept only the ISO-8601 UTC spelling GitHub publishes.
fn is_utc_timestamp(value: &str) -> bool {
    let Some(rest) = value.strip_suffix('Z') else {
        return false;
    };
    let (date_time, fraction) = rest
        .split_once('.')
        .map_or((rest, None), |(head, tail)| (head, Some(tail)));
    if fraction.is_some_and(|tail| tail.is_empty() || !tail.bytes().all(|b| b.is_ascii_digit())) {
        return false;
    }
    let shape = "0000-00-00T00:00:00";
    date_time.len() == shape.len()
        && date_time
            .bytes()
            .zip(shape.bytes())
            .all(|(byte, template)| {
                if template == b'0' {
                    byte.is_ascii_digit()
                } else {
                    byte == template
                }
            })
}

/// Confine the session root to a canonical `/tmp/claude-triage-*` directory.
fn canonical_triage_root(value: &str) -> Result<PathBuf, TriageError> {
    let refusal = || {
        TriageError::new(
            "triage root must be an existing regular directory",
            EXIT_USAGE,
        )
    };
    let root = Path::new(value);
    if !root.is_absolute() {
        return Err(refusal());
    }
    let metadata = fs::symlink_metadata(root).map_err(|_| refusal())?;
    if metadata.is_symlink() || !metadata.is_dir() {
        return Err(refusal());
    }
    let resolved = fs::canonicalize(root).map_err(|_| refusal())?;
    let tmp_root = fs::canonicalize(TMP_ROOT).map_err(|_| refusal())?;
    let named = resolved
        .file_name()
        .is_some_and(|name| name.to_string_lossy().starts_with(TRIAGE_TMP_PREFIX));
    if resolved.parent() != Some(tmp_root.as_path()) || !named {
        return Err(TriageError::new(
            "triage root must be a canonical /tmp/claude-triage-* directory",
            EXIT_USAGE,
        ));
    }
    Ok(resolved)
}

/// Accept only a regular, non-symlink artifact directly inside the session root.
fn confined_artifact(value: &str, root: &Path) -> Result<PathBuf, TriageError> {
    let refusal = || {
        TriageError::new(
            "triage artifact must be a regular non-symlink file",
            EXIT_USAGE,
        )
    };
    let path = Path::new(value);
    if !path.is_absolute() {
        return Err(refusal());
    }
    let metadata = fs::symlink_metadata(path).map_err(|_| refusal())?;
    if metadata.is_symlink() || !metadata.is_file() {
        return Err(refusal());
    }
    let resolved = fs::canonicalize(path).map_err(|_| refusal())?;
    if resolved.parent() != Some(root) {
        return Err(TriageError::new(
            "triage artifact escaped the canonical triage root",
            EXIT_USAGE,
        ));
    }
    Ok(resolved)
}

/// The canonical issue state every triage compare-and-swap boundary reads.
#[derive(Clone, Debug, Eq, PartialEq)]
struct TriageSnapshot {
    snapshot: IssueMutationSnapshot,
    url: String,
    comments: Vec<String>,
}

impl TriageSnapshot {
    fn title(&self) -> &str {
        &self.snapshot.title
    }

    fn body(&self) -> &str {
        &self.snapshot.body
    }

    fn updated_at(&self) -> &str {
        &self.snapshot.updated_at
    }
}

/// Run the whole verdict against one GitHub client, then publish its rows.
fn apply_verified(request: &ApplyRequest) -> Result<ExitCode, TriageError> {
    let outcome = with_github_service(async |service, cancellation| {
        let effects = LiveIssueEffects {
            service,
            owner: IssueMutationOwner::new(service),
            cancellation,
            repository: request.repository.clone(),
        };
        Ok(TriageSession {
            effects: &effects,
            request,
        }
        .run()
        .await)
    });
    let updated = match outcome {
        Err(ServiceFailure::Setup(detail) | ServiceFailure::Operation(detail)) => {
            return Err(TriageError::new(detail, EXIT_MUTATION));
        }
        Ok(result) => result?,
    };
    emit_kv("TRIAGE_VERDICT", &request.verdict);
    emit_kv("ISSUE_UPDATED", bool_text(updated.changed));
    emit_kv("TRIAGE_FAILURE", "none");
    emit_kv("UPDATED_AT", &updated.updated_at);
    Ok(ExitCode::SUCCESS)
}

/// What one completed verdict reports about the issue it verified.
#[derive(Debug)]
struct AppliedVerdict {
    changed: bool,
    updated_at: String,
}

/// The four GitHub effects one verdict performs, behind one seam.
///
/// The verdict logic below is the part that must be provable: it decides when
/// to refuse, in what order to re-verify, and what proof each write needs. That
/// reasoning is only reachable by a test if the transport is replaceable, so
/// every request the session makes goes through this trait and the live
/// implementation carries no decisions of its own.
trait IssueEffects: Sync {
    /// Read one canonical snapshot, with its comment bodies.
    fn read(&self, issue: u64) -> impl Future<Output = Result<TriageSnapshot, TriageError>> + Send;
    /// Apply one compare-and-swap through the shared issue-mutation owner.
    fn mutate(
        &self,
        request: &IssueMutationRequest,
    ) -> impl Future<Output = Result<(), TriageError>> + Send;
    /// Publish one comment body verbatim.
    fn comment(
        &self,
        issue: u64,
        body: &str,
    ) -> impl Future<Output = Result<(), TriageError>> + Send;
    /// Close one issue as not planned.
    fn close(&self, issue: u64) -> impl Future<Output = Result<(), TriageError>> + Send;
}

/// The live effects, bound to one authenticated client and one repository.
struct LiveIssueEffects<'a> {
    service: &'a OctocrabGitHubService,
    owner: IssueMutationOwner<'a>,
    cancellation: &'a dyn ProcessCancellation,
    repository: GitHubRepositoryRef,
}

impl IssueEffects for LiveIssueEffects<'_> {
    async fn read(&self, issue: u64) -> Result<TriageSnapshot, TriageError> {
        let subject = self
            .service
            .issue(&self.repository, issue, self.cancellation)
            .await
            .map_err(|error| {
                TriageError::new(format!("issue snapshot failed: {error}"), EXIT_MUTATION)
            })?;
        let comments = self
            .service
            .list_comments(&self.repository, issue, self.cancellation)
            .await
            .map_err(|_| TriageError::new("issue comments could not be read", EXIT_PROTECTED))?;
        compose_snapshot(
            &self.repository,
            issue,
            subject,
            comments.into_iter().map(|comment| comment.body).collect(),
        )
    }

    /// The command line already passed the live-mutation gate, so the owner's
    /// own check is satisfied here in operator mode rather than re-deriving a
    /// session context this verb never receives.
    async fn mutate(&self, request: &IssueMutationRequest) -> Result<(), TriageError> {
        let authorization = authorization_request("", "", "", true);
        self.owner
            .apply(self.cancellation, &authorization, request)
            .await
            .map(|_| ())
            .map_err(|error| TriageError::new(error.to_string(), EXIT_MUTATION))
    }

    async fn comment(&self, issue: u64, body: &str) -> Result<(), TriageError> {
        self.service
            .create_comment(&self.repository, issue, body, self.cancellation)
            .await
            .map(|_| ())
            .map_err(|error| {
                TriageError::new(
                    format!("triage verification comment failed: {error}"),
                    EXIT_MUTATION,
                )
            })
    }

    async fn close(&self, issue: u64) -> Result<(), TriageError> {
        self.owner
            .close_not_planned(self.cancellation, &self.repository, issue)
            .await
            .map_err(|detail| {
                TriageError::new(
                    format!("triage issue close failed: {detail}"),
                    EXIT_MUTATION,
                )
            })
    }
}

/// One verdict application, bound to one effects seam and one issue.
struct TriageSession<'a, E: IssueEffects> {
    effects: &'a E,
    request: &'a ApplyRequest,
}

impl<E: IssueEffects> TriageSession<'_, E> {
    async fn run(&self) -> Result<AppliedVerdict, TriageError> {
        let snapshot = self.effects.read(self.request.issue).await?;
        self.check_snapshot(&snapshot)?;
        let final_state = if self.request.verdict == "valid" {
            self.apply_valid(snapshot.clone()).await?
        } else {
            self.apply_close(snapshot.clone()).await?
        };
        Ok(AppliedVerdict {
            changed: final_state != snapshot,
            updated_at: final_state.updated_at().to_owned(),
        })
    }

    /// Refuse the whole verdict when the first snapshot is not mutable.
    fn check_snapshot(&self, snapshot: &TriageSnapshot) -> Result<(), TriageError> {
        if snapshot.updated_at() != self.request.expected_updated_at {
            return Err(TriageError::new(
                "issue changed since the expected snapshot",
                EXIT_STALE,
            ));
        }
        if is_security_sensitive(snapshot)
            || triage_text_is_security_sensitive(&self.request.artifact_text)
        {
            return Err(TriageError::new(
                "security-sensitive issue cannot be mutated publicly",
                EXIT_PROTECTED,
            ));
        }
        let closing = CLOSE_VERDICTS.contains(&self.request.verdict.as_str());
        if has_protected_state(snapshot, closing)? {
            return Err(TriageError::new(
                "issue has protected lifecycle state",
                EXIT_PROTECTED,
            ));
        }
        Ok(())
    }

    /// Re-read the issue and prove it is still the one that was verified.
    async fn recheck(
        &self,
        snapshot: &TriageSnapshot,
        allow_stale_title: bool,
    ) -> Result<TriageSnapshot, TriageError> {
        let current = self.effects.read(self.request.issue).await?;
        recheck_verdict(&current, snapshot, allow_stale_title)?;
        Ok(current)
    }

    /// Prove the mutation advanced the issue's own timestamp.
    async fn read_after_mutation(
        &self,
        previous: &TriageSnapshot,
    ) -> Result<TriageSnapshot, TriageError> {
        let current = self.effects.read(self.request.issue).await?;
        advanced(&current, previous)?;
        Ok(current)
    }

    /// Publish the verified diagnosis into the issue body and tag the title.
    async fn apply_valid(&self, snapshot: TriageSnapshot) -> Result<TriageSnapshot, TriageError> {
        let Some(plan) = plan_valid_update(&snapshot, &self.request.artifact_text)? else {
            return Ok(snapshot);
        };
        let snapshot = self.recheck(&snapshot, false).await?;
        self.effects
            .mutate(&valid_mutation(&snapshot, &plan))
            .await?;
        let current = self.read_after_mutation(&snapshot).await?;
        valid_read_back(&current, &plan)?;
        Ok(current)
    }

    /// Publish one verdict comment, restore the title, and close the issue.
    async fn apply_close(
        &self,
        mut snapshot: TriageSnapshot,
    ) -> Result<TriageSnapshot, TriageError> {
        if self.request.verdict == "duplicate" {
            let canonical = self.request.canonical.ok_or_else(|| {
                TriageError::new(
                    "duplicate verdict requires --canonical-duplicate",
                    EXIT_USAGE,
                )
            })?;
            self.verify_canonical(canonical).await?;
            snapshot = self.recheck(&snapshot, true).await?;
        }
        let plan = plan_close_comment(self.request)?;
        snapshot = self
            .ensure_comment(snapshot, &plan.marker, &plan.published)
            .await?;
        snapshot = self.restore_title(snapshot).await?;
        snapshot = self.recheck(&snapshot, true).await?;
        self.effects.close(self.request.issue).await?;
        let current = self.read_after_mutation(&snapshot).await?;
        close_read_back(&current)?;
        Ok(current)
    }

    /// Prove the cited canonical duplicate is a different, open issue.
    async fn verify_canonical(&self, canonical: u64) -> Result<(), TriageError> {
        if canonical == self.request.issue {
            return Err(TriageError::new(
                "canonical duplicate must differ from the triaged issue",
                EXIT_USAGE,
            ));
        }
        let duplicate = self.effects.read(canonical).await?;
        canonical_is_open(&duplicate, canonical)
    }

    /// Publish the verdict comment exactly once, proving it by read-back.
    async fn ensure_comment(
        &self,
        snapshot: TriageSnapshot,
        marker: &str,
        published: &str,
    ) -> Result<TriageSnapshot, TriageError> {
        if classify_comment(&snapshot.comments, marker, published)? == CommentAction::Present {
            return Ok(snapshot);
        }
        let snapshot = self.recheck(&snapshot, true).await?;
        self.effects.comment(self.request.issue, published).await?;
        let current = self.read_after_mutation(&snapshot).await?;
        comment_read_back(&current, published)?;
        Ok(current)
    }

    /// Peel a stale lifecycle prefix off a title before the issue is closed.
    async fn restore_title(&self, snapshot: TriageSnapshot) -> Result<TriageSnapshot, TriageError> {
        let Some(restored) = restored_title(snapshot.title()) else {
            return Ok(snapshot);
        };
        let snapshot = self.recheck(&snapshot, true).await?;
        self.effects
            .mutate(&title_mutation(&snapshot, &restored))
            .await?;
        let current = self.read_after_mutation(&snapshot).await?;
        if current.title() != restored {
            return Err(TriageError::new(
                "title restoration failed exact read-back",
                EXIT_POSTCONDITION,
            ));
        }
        Ok(current)
    }
}

// ------------------------------------------------------- verdict decisions
//
// Every judgement one verdict makes lives here as a pure function over the
// snapshot it read, so the session above is only the request order and the
// `.await` points. That keeps the fail-closed rules — freshness, security,
// idempotency, and every read-back proof — readable and directly testable.

/// Compose one canonical snapshot, proving it names the requested issue.
fn compose_snapshot(
    repository: &GitHubRepositoryRef,
    issue: u64,
    subject: larch_core::GitHubIssue,
    comments: Vec<String>,
) -> Result<TriageSnapshot, TriageError> {
    if subject.number != issue || subject.updated_at.is_empty() {
        return Err(TriageError::new(
            "issue snapshot is missing required identity fields",
            EXIT_POSTCONDITION,
        ));
    }
    let expected = format!(
        "/{}/{}/issues/{issue}",
        repository.owner(),
        repository.name()
    );
    if url_path(&subject.url).trim_end_matches('/') != expected {
        return Err(TriageError::new(
            "issue snapshot repository or issue identity did not match",
            EXIT_PROTECTED,
        ));
    }
    Ok(TriageSnapshot {
        snapshot: IssueMutationSnapshot {
            repository: repository.clone(),
            issue,
            title: subject.title,
            body: subject.body,
            labels: subject
                .labels
                .iter()
                .map(|label| label.name.clone())
                .collect(),
            state: subject.state,
            updated_at: subject.updated_at,
        },
        url: subject.url,
        comments,
    })
}

/// The body, title, and fields one `valid` verdict would publish.
#[derive(Clone, Debug, Eq, PartialEq)]
struct ValidPlan {
    body: String,
    title: String,
    fields: BTreeSet<IssueMutationField>,
}

/// Compose the `valid` update, or report that the issue already carries it.
fn plan_valid_update(
    snapshot: &TriageSnapshot,
    artifact: &str,
) -> Result<Option<ValidPlan>, TriageError> {
    let block = sanitize_triage_outbound(artifact, true).map_err(sanitize_error)?;
    let body = replace_triage_block(snapshot.body(), &block)
        .map_err(|_| TriageError::new("malformed helper-owned triage block", EXIT_PROTECTED))?;
    let title = triaged_title(snapshot.title());
    if body == snapshot.body() && title == snapshot.title() {
        return Ok(None);
    }
    let mut fields = BTreeSet::new();
    if title != snapshot.title() {
        fields.insert(IssueMutationField::Title);
    }
    if body != snapshot.body() {
        fields.insert(IssueMutationField::Body);
    }
    Ok(Some(ValidPlan {
        body,
        title,
        fields,
    }))
}

/// Build the compare-and-swap the `valid` plan swaps against.
fn valid_mutation(snapshot: &TriageSnapshot, plan: &ValidPlan) -> IssueMutationRequest {
    IssueMutationRequest {
        repository: snapshot.snapshot.repository.clone(),
        issue: snapshot.snapshot.issue,
        expected_updated_at: snapshot.snapshot.updated_at.clone(),
        expected_state: snapshot.snapshot.state,
        fields: plan.fields.clone(),
        title: plan
            .fields
            .contains(&IssueMutationField::Title)
            .then(|| plan.title.clone()),
        body: plan
            .fields
            .contains(&IssueMutationField::Body)
            .then(|| plan.body.clone()),
        labels: None,
        marker: None,
        lease: None,
    }
}

/// Build the title-only compare-and-swap a stale prefix restoration swaps against.
fn title_mutation(snapshot: &TriageSnapshot, title: &str) -> IssueMutationRequest {
    IssueMutationRequest {
        repository: snapshot.snapshot.repository.clone(),
        issue: snapshot.snapshot.issue,
        expected_updated_at: snapshot.snapshot.updated_at.clone(),
        expected_state: snapshot.snapshot.state,
        fields: BTreeSet::from([IssueMutationField::Title]),
        title: Some(title.to_owned()),
        body: None,
        labels: None,
        marker: None,
        lease: None,
    }
}

/// Prove the published issue carries exactly the planned body, title, and state.
fn valid_read_back(current: &TriageSnapshot, plan: &ValidPlan) -> Result<(), TriageError> {
    if current.body() != plan.body
        || current.title() != plan.title
        || current.snapshot.state != GitHubIssueState::Open
    {
        return Err(TriageError::new(
            "triage body update failed exact read-back",
            EXIT_POSTCONDITION,
        ));
    }
    Ok(())
}

/// The marker and the exact comment body one close verdict would publish.
#[derive(Clone, Debug, Eq, PartialEq)]
struct ClosePlan {
    marker: String,
    published: String,
}

/// Compose the marked verdict comment, naming the canonical duplicate once.
fn plan_close_comment(request: &ApplyRequest) -> Result<ClosePlan, TriageError> {
    let marker = format!("{TRIAGE_VERDICT_COMMENT_PREFIX}{} -->", request.verdict);
    let mut comment =
        sanitize_triage_outbound(&request.artifact_text, false).map_err(sanitize_error)?;
    if let Some(canonical) = request.canonical.filter(|_| request.verdict == "duplicate")
        && !comment.contains(&format!("#{canonical}"))
    {
        comment = format!("Duplicate of #{canonical}.\n\n{comment}");
    }
    let published = format!("{marker}\n{}", comment.trim());
    Ok(ClosePlan { marker, published })
}

/// Whether the verdict comment still has to be published.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum CommentAction {
    /// The exact comment is already published, so the step is a no-op.
    Present,
    /// No comment carries the marker yet.
    Publish,
}

/// Decide whether to publish the verdict comment, or refuse a conflicting one.
///
/// A different comment already carrying this verdict's marker means another
/// writer reached the issue first, and overwriting or duplicating it would lose
/// that verdict, so the whole apply refuses.
fn classify_comment(
    comments: &[String],
    marker: &str,
    published: &str,
) -> Result<CommentAction, TriageError> {
    if comments.iter().any(|body| body == published) {
        return Ok(CommentAction::Present);
    }
    if comments.iter().any(|body| body.starts_with(marker)) {
        return Err(TriageError::new(
            "conflicting triage verdict marker already exists",
            EXIT_POSTCONDITION,
        ));
    }
    Ok(CommentAction::Publish)
}

/// Prove the published comment came back byte for byte.
fn comment_read_back(current: &TriageSnapshot, published: &str) -> Result<(), TriageError> {
    if current.comments.iter().any(|body| body == published) {
        return Ok(());
    }
    Err(TriageError::new(
        "triage comment failed exact read-back",
        EXIT_POSTCONDITION,
    ))
}

/// Return the title with every stale lifecycle prefix peeled, when that changes it.
fn restored_title(title: &str) -> Option<String> {
    let restored = strip_triage_lifecycle_prefixes(title);
    (restored != title).then_some(restored)
}

/// Re-prove freshness, classification, and lifecycle state before a mutation.
fn recheck_verdict(
    current: &TriageSnapshot,
    previous: &TriageSnapshot,
    allow_stale_title: bool,
) -> Result<(), TriageError> {
    if current.updated_at() != previous.updated_at() {
        return Err(TriageError::new(
            "issue changed before the next mutation",
            EXIT_STALE,
        ));
    }
    if is_security_sensitive(current) {
        return Err(TriageError::new(
            "security-sensitive issue cannot be mutated publicly",
            EXIT_PROTECTED,
        ));
    }
    if has_protected_state(current, allow_stale_title)? {
        return Err(TriageError::new(
            "issue has protected lifecycle state",
            EXIT_PROTECTED,
        ));
    }
    Ok(())
}

/// Prove the mutation advanced the issue's own timestamp.
fn advanced(current: &TriageSnapshot, previous: &TriageSnapshot) -> Result<(), TriageError> {
    if current.updated_at() == previous.updated_at() {
        return Err(TriageError::new(
            "mutation did not advance the issue snapshot",
            EXIT_POSTCONDITION,
        ));
    }
    Ok(())
}

/// Prove the close landed.
fn close_read_back(current: &TriageSnapshot) -> Result<(), TriageError> {
    if current.snapshot.state == GitHubIssueState::Closed {
        return Ok(());
    }
    Err(TriageError::new(
        "issue close failed state/reason read-back",
        EXIT_POSTCONDITION,
    ))
}

/// Prove the cited canonical duplicate is the open issue it claims to be.
fn canonical_is_open(duplicate: &TriageSnapshot, canonical: u64) -> Result<(), TriageError> {
    if duplicate.snapshot.issue == canonical && duplicate.snapshot.state == GitHubIssueState::Open {
        return Ok(());
    }
    Err(TriageError::new(
        "canonical duplicate could not be verified",
        EXIT_PROTECTED,
    ))
}

/// Return whether the issue reads as a security report anywhere.
fn is_security_sensitive(snapshot: &TriageSnapshot) -> bool {
    if snapshot
        .snapshot
        .labels
        .iter()
        .any(|label| triage_label_is_security(label))
    {
        return true;
    }
    let joined = std::iter::once(snapshot.title())
        .chain(std::iter::once(snapshot.body()))
        .chain(snapshot.comments.iter().map(String::as_str))
        .collect::<Vec<&str>>()
        .join("\n");
    triage_text_is_security_sensitive(&joined)
}

/// Return whether the issue's lifecycle state forbids a public mutation.
fn has_protected_state(
    snapshot: &TriageSnapshot,
    allow_stale_title: bool,
) -> Result<bool, TriageError> {
    if snapshot.snapshot.state != GitHubIssueState::Open {
        return Ok(true);
    }
    if snapshot
        .snapshot
        .labels
        .iter()
        .any(|label| label.to_lowercase().contains("clarif"))
    {
        return Ok(true);
    }
    if larch_core::body_has_foreign_larch_marker(snapshot.body())
        .map_err(|_| TriageError::new("malformed helper-owned triage block", EXIT_PROTECTED))?
    {
        return Ok(true);
    }
    Ok(!allow_stale_title && triage_title_has_lifecycle_prefix(snapshot.title()))
}

/// Return the path component of one issue URL, as `urlparse` would.
fn url_path(url: &str) -> &str {
    let rest = url.split_once("://").map_or(url, |(_scheme, rest)| rest);
    rest.find('/').map_or("", |index| {
        let tail = &rest[index..];
        tail.split(['?', '#']).next().unwrap_or(tail)
    })
}

#[cfg(test)]
mod tests {
    use super::{
        AppliedVerdict, ApplyRequest, CommentAction, EXIT_MUTATION, EXIT_POSTCONDITION,
        EXIT_PROTECTED, EXIT_REDACTION, EXIT_STALE, IssueEffects, TriageError, TriageSession,
        TriageSnapshot, advanced, canonical_duplicate, canonical_is_open, classify_comment,
        close_read_back, comment_read_back, compose_snapshot, flat, github_slug,
        has_protected_state, is_security_sensitive, is_utc_timestamp, plan_close_comment,
        plan_valid_update, pull_request_head, recheck_verdict, restored_title, title_mutation,
        url_path, valid_mutation, valid_read_back,
    };
    use crate::argparse_compat::parse_with_flags;
    use larch_adapters::runtime::LarchRuntime;
    use larch_core::{
        BUG_PREFIX, DONE_PREFIX, GitHubIssue, GitHubIssueState, GitHubLabel, GitHubRepositoryRef,
        IssueMutationField, IssueMutationRequest, IssueMutationSnapshot, TRIAGE_MARKER_END,
        TRIAGE_MARKER_START, TRIAGED_TAG,
    };
    use std::{collections::BTreeSet, ffi::OsString, sync::Mutex};

    fn snapshot(title: &str, body: &str, labels: &[&str], comments: &[&str]) -> TriageSnapshot {
        TriageSnapshot {
            snapshot: IssueMutationSnapshot {
                repository: GitHubRepositoryRef::new("owner", "repo").expect("a usable slug"),
                issue: 7,
                title: title.to_owned(),
                body: body.to_owned(),
                labels: labels
                    .iter()
                    .map(|label| (*label).to_owned())
                    .collect::<BTreeSet<String>>(),
                state: GitHubIssueState::Open,
                updated_at: "2026-07-12T10:00:00Z".to_owned(),
            },
            url: "https://github.com/owner/repo/issues/7".to_owned(),
            comments: comments.iter().map(|body| (*body).to_owned()).collect(),
        }
    }

    fn repository() -> GitHubRepositoryRef {
        GitHubRepositoryRef::new("owner", "repo").expect("a usable slug")
    }

    fn subject(number: u64, url: &str) -> GitHubIssue {
        GitHubIssue {
            id: 1,
            number,
            title: "Bug report".to_owned(),
            body: "Original report".to_owned(),
            state: GitHubIssueState::Open,
            state_reason: String::new(),
            url: url.to_owned(),
            author: "reporter".to_owned(),
            assignees: Vec::new(),
            labels: vec![GitHubLabel {
                id: 2,
                name: "bug".to_owned(),
                color: String::new(),
                description: String::new(),
            }],
            comments: 0,
            created_at: String::new(),
            closed_at: String::new(),
            updated_at: "2026-07-12T10:00:00Z".to_owned(),
            is_pull_request: false,
        }
    }

    fn request(verdict: &str, artifact: &str, canonical: Option<u64>) -> ApplyRequest {
        ApplyRequest {
            issue: 7,
            repository: repository(),
            verdict: verdict.to_owned(),
            expected_updated_at: "2026-07-12T10:00:00Z".to_owned(),
            artifact_text: artifact.to_owned(),
            canonical,
        }
    }

    fn moved(snapshot: &TriageSnapshot, updated_at: &str) -> TriageSnapshot {
        let mut moved = snapshot.clone();
        moved.snapshot.updated_at = updated_at.to_owned();
        moved
    }

    #[test]
    fn a_snapshot_is_composed_only_from_a_matching_identity() {
        let composed = compose_snapshot(
            &repository(),
            7,
            subject(7, "https://github.com/owner/repo/issues/7"),
            vec!["hello".to_owned()],
        )
        .unwrap_or_else(|_| panic!("a matching identity"));

        assert_eq!(composed.title(), "Bug report");
        assert_eq!(
            composed.snapshot.labels.iter().next().map(String::as_str),
            Some("bug")
        );
        assert_eq!(composed.comments, vec!["hello".to_owned()]);
        // A different issue number, an absent timestamp, and a URL naming
        // another repository each refuse rather than mutate the wrong issue.
        assert_eq!(
            compose_snapshot(
                &repository(),
                8,
                subject(7, "https://github.com/owner/repo/issues/7"),
                Vec::new()
            )
            .unwrap_err()
            .code,
            EXIT_POSTCONDITION
        );
        let mut undated = subject(7, "https://github.com/owner/repo/issues/7");
        undated.updated_at = String::new();
        assert_eq!(
            compose_snapshot(&repository(), 7, undated, Vec::new())
                .unwrap_err()
                .code,
            EXIT_POSTCONDITION
        );
        assert_eq!(
            compose_snapshot(
                &repository(),
                7,
                subject(7, "https://github.com/other/repo/issues/7"),
                Vec::new()
            )
            .unwrap_err()
            .code,
            EXIT_PROTECTED
        );
    }

    #[test]
    fn a_valid_plan_splices_the_block_and_tags_the_title() {
        let base = snapshot(&format!("{BUG_PREFIX} Crash"), "Original report", &[], &[]);
        let plan = plan_valid_update(&base, "## Summary\n\nCorrected.")
            .unwrap_or_else(|_| panic!("a usable artifact"))
            .unwrap_or_else(|| panic!("a change"));

        assert_eq!(plan.title, format!("{BUG_PREFIX} {TRIAGED_TAG} Crash"));
        assert!(
            plan.body.starts_with("Original report\n\n"),
            "{}",
            plan.body
        );
        assert!(plan.body.contains(TRIAGE_MARKER_START), "{}", plan.body);
        assert!(plan.body.contains(TRIAGE_MARKER_END), "{}", plan.body);
        assert_eq!(
            plan.fields,
            BTreeSet::from([IssueMutationField::Title, IssueMutationField::Body])
        );

        // The write is idempotent: re-running against the published issue plans
        // no mutation at all.
        let published = snapshot(&plan.title, &plan.body, &[], &[]);
        assert_eq!(
            plan_valid_update(&published, "## Summary\n\nCorrected."),
            Ok(None)
        );
    }

    #[test]
    fn a_valid_plan_refuses_a_malformed_body_and_a_multi_block_artifact() {
        let broken = snapshot("x", &format!("half {TRIAGE_MARKER_START}"), &[], &[]);
        assert_eq!(
            plan_valid_update(&broken, "notes").unwrap_err().code,
            EXIT_PROTECTED
        );
        let base = snapshot("x", "report", &[], &[]);
        let two_blocks = format!("lead {TRIAGE_MARKER_START}\nnotes\n{TRIAGE_MARKER_END}");
        assert_eq!(
            plan_valid_update(&base, &two_blocks).unwrap_err().code,
            EXIT_REDACTION
        );
    }

    #[test]
    fn a_valid_mutation_swaps_only_the_planned_fields() {
        let base = snapshot("Bug report", "Original report", &[], &[]);
        let plan = plan_valid_update(&base, "notes")
            .unwrap_or_else(|_| panic!("a usable artifact"))
            .unwrap_or_else(|| panic!("a change"));
        let mutation = valid_mutation(&base, &plan);

        assert_eq!(mutation.issue, 7);
        assert_eq!(mutation.expected_updated_at, "2026-07-12T10:00:00Z");
        assert_eq!(mutation.expected_state, GitHubIssueState::Open);
        assert_eq!(mutation.title.as_deref(), Some(plan.title.as_str()));
        assert_eq!(mutation.body.as_deref(), Some(plan.body.as_str()));
        // No named block, no lease, and no labels: this is an ordinary
        // title-and-body swap the owner validates as one.
        assert!(mutation.marker.is_none() && mutation.lease.is_none());
        assert!(mutation.labels.is_none());

        let title_only = title_mutation(&base, "Bug report");
        assert_eq!(
            title_only.fields,
            BTreeSet::from([IssueMutationField::Title])
        );
        assert_eq!(title_only.body, None);
    }

    #[test]
    fn the_valid_read_back_demands_the_exact_published_state() {
        let base = snapshot("Bug report", "Original report", &[], &[]);
        let plan = plan_valid_update(&base, "notes")
            .unwrap_or_else(|_| panic!("a usable artifact"))
            .unwrap_or_else(|| panic!("a change"));
        let published = snapshot(&plan.title, &plan.body, &[], &[]);
        assert_eq!(valid_read_back(&published, &plan), Ok(()));

        let wrong_body = snapshot(&plan.title, "something else", &[], &[]);
        assert_eq!(
            valid_read_back(&wrong_body, &plan).unwrap_err().code,
            EXIT_POSTCONDITION
        );
        let mut closed = published;
        closed.snapshot.state = GitHubIssueState::Closed;
        assert_eq!(
            valid_read_back(&closed, &plan).unwrap_err().code,
            EXIT_POSTCONDITION
        );
    }

    #[test]
    fn a_close_comment_carries_its_marker_and_names_the_duplicate_once() {
        let plan = plan_close_comment(&request("already-fixed", "  verified fixed  ", None))
            .unwrap_or_else(|_| panic!("a usable artifact"));
        assert_eq!(plan.marker, "<!-- larch:triage-verdict:already-fixed -->");
        assert_eq!(plan.published, format!("{}\nverified fixed", plan.marker));

        let duplicate = plan_close_comment(&request("duplicate", "same as before", Some(42)))
            .unwrap_or_else(|_| panic!("a usable artifact"));
        assert!(
            duplicate.published.contains("Duplicate of #42."),
            "{duplicate:?}"
        );

        // A comment that already names the canonical issue is not prefixed twice.
        let named = plan_close_comment(&request("duplicate", "same as #42", Some(42)))
            .unwrap_or_else(|_| panic!("a usable artifact"));
        assert!(!named.published.contains("Duplicate of #42."), "{named:?}");
    }

    #[test]
    fn the_comment_step_is_idempotent_and_refuses_a_conflicting_marker() {
        let marker = "<!-- larch:triage-verdict:invalid -->";
        let published = format!("{marker}\nnot a defect");
        assert_eq!(
            classify_comment(&[], marker, &published),
            Ok(CommentAction::Publish)
        );
        assert_eq!(
            classify_comment(std::slice::from_ref(&published), marker, &published),
            Ok(CommentAction::Present)
        );
        let conflicting = format!("{marker}\nsomeone else's verdict");
        assert_eq!(
            classify_comment(&[conflicting], marker, &published)
                .unwrap_err()
                .code,
            EXIT_POSTCONDITION
        );
    }

    #[test]
    fn every_read_back_proof_refuses_what_it_cannot_see() {
        let base = snapshot("x", "y", &[], &["published".to_owned().as_str()]);
        assert_eq!(comment_read_back(&base, "published"), Ok(()));
        assert_eq!(
            comment_read_back(&base, "missing").unwrap_err().code,
            EXIT_POSTCONDITION
        );
        assert_eq!(close_read_back(&base).unwrap_err().code, EXIT_POSTCONDITION);
        let mut closed = base.clone();
        closed.snapshot.state = GitHubIssueState::Closed;
        assert_eq!(close_read_back(&closed), Ok(()));
        assert_eq!(
            advanced(&moved(&base, "2026-07-12T11:00:00Z"), &base),
            Ok(())
        );
        assert_eq!(advanced(&base, &base).unwrap_err().code, EXIT_POSTCONDITION);
        assert_eq!(canonical_is_open(&base, 7), Ok(()));
        assert_eq!(
            canonical_is_open(&base, 8).unwrap_err().code,
            EXIT_PROTECTED
        );
        assert_eq!(
            canonical_is_open(&closed, 7).unwrap_err().code,
            EXIT_PROTECTED
        );
    }

    #[test]
    fn the_recheck_refuses_a_moved_reclassified_or_protected_issue() {
        let base = snapshot("Bug report", "report", &[], &[]);
        assert_eq!(recheck_verdict(&base, &base, false), Ok(()));
        assert_eq!(
            recheck_verdict(&moved(&base, "2026-07-12T11:00:00Z"), &base, false)
                .unwrap_err()
                .code,
            EXIT_STALE
        );
        let sensitive = snapshot("Bug report", "an RCE in the parser", &[], &[]);
        assert_eq!(
            recheck_verdict(&sensitive, &sensitive, true)
                .unwrap_err()
                .code,
            EXIT_PROTECTED
        );
        let stale_title = snapshot(&format!("{DONE_PREFIX}Bug report"), "report", &[], &[]);
        assert_eq!(
            recheck_verdict(&stale_title, &stale_title, false)
                .unwrap_err()
                .code,
            EXIT_PROTECTED
        );
        assert_eq!(recheck_verdict(&stale_title, &stale_title, true), Ok(()));
    }

    #[test]
    fn a_canonical_duplicate_must_name_a_positive_issue() {
        let line = |values: &[&str]| {
            parse_with_flags(
                &values.iter().map(OsString::from).collect::<Vec<OsString>>(),
                &["--canonical-duplicate"],
                &[],
                0,
            )
        };
        assert_eq!(canonical_duplicate(&line(&[])), Ok(None));
        assert_eq!(
            canonical_duplicate(&line(&["--canonical-duplicate", "42"])),
            Ok(Some(42))
        );
        // `argparse` accepted `0` and a negative number as integers, so the
        // refusal is the verdict the canonical read would have reported.
        for unusable in ["0", "-1"] {
            assert_eq!(
                canonical_duplicate(&line(&["--canonical-duplicate", unusable]))
                    .unwrap_err()
                    .code,
                EXIT_PROTECTED,
                "{unusable}"
            );
        }
    }

    #[test]
    fn a_stale_prefix_is_restored_only_when_it_is_present() {
        assert_eq!(
            restored_title(&format!("{DONE_PREFIX}Bug report")).as_deref(),
            Some("Bug report")
        );
        assert_eq!(restored_title("Bug report"), None);
    }

    /// One scripted GitHub, replaying reads and recording every write.
    ///
    /// Reads are a queue rather than a fixed answer, because the whole point of
    /// the verdict flow is that it re-reads between mutations and must react to
    /// what changed; a test that could not move the issue mid-flight could not
    /// prove the fail-closed half at all.
    struct FakeEffects {
        reads: Mutex<Vec<TriageSnapshot>>,
        writes: Mutex<Vec<String>>,
    }

    impl FakeEffects {
        fn new(reads: Vec<TriageSnapshot>) -> Self {
            Self {
                reads: Mutex::new(reads),
                writes: Mutex::new(Vec::new()),
            }
        }

        fn writes(&self) -> Vec<String> {
            self.writes.lock().expect("writes lock").clone()
        }

        fn record(&self, entry: String) {
            self.writes.lock().expect("writes lock").push(entry);
        }
    }

    impl IssueEffects for FakeEffects {
        async fn read(&self, issue: u64) -> Result<TriageSnapshot, TriageError> {
            let mut reads = self.reads.lock().expect("reads lock");
            if reads.is_empty() {
                return Err(TriageError::new(
                    format!("fixture ran out of reads for issue {issue}"),
                    EXIT_MUTATION,
                ));
            }
            Ok(reads.remove(0))
        }

        async fn mutate(&self, request: &IssueMutationRequest) -> Result<(), TriageError> {
            self.record(format!("mutate:{:?}", request.fields));
            Ok(())
        }

        async fn comment(&self, _issue: u64, body: &str) -> Result<(), TriageError> {
            self.record(format!("comment:{body}"));
            Ok(())
        }

        async fn close(&self, _issue: u64) -> Result<(), TriageError> {
            self.record("close".to_owned());
            Ok(())
        }
    }

    fn run_verdict(
        effects: &FakeEffects,
        request: &ApplyRequest,
    ) -> Result<AppliedVerdict, TriageError> {
        LarchRuntime::current_thread()
            .expect("a test runtime")
            .block_on(TriageSession { effects, request }.run())
    }

    #[test]
    fn a_valid_verdict_publishes_the_block_and_proves_the_read_back() {
        let before = snapshot("Bug report", "Original report", &[], &[]);
        let plan = plan_valid_update(&before, "Corrected.")
            .unwrap_or_else(|_| panic!("a usable artifact"))
            .unwrap_or_else(|| panic!("a change"));
        let mut after = snapshot(&plan.title, &plan.body, &[], &[]);
        after.snapshot.updated_at = "2026-07-12T11:00:00Z".to_owned();
        // First read, the pre-mutation recheck, then the read-back.
        let effects = FakeEffects::new(vec![before.clone(), before, after]);
        let request = request("valid", "Corrected.", None);

        let applied = run_verdict(&effects, &request).unwrap_or_else(|error| panic!("{error:?}"));

        assert!(applied.changed);
        assert_eq!(applied.updated_at, "2026-07-12T11:00:00Z");
        assert_eq!(
            effects.writes(),
            vec!["mutate:{Title, Body}".to_owned()],
            "exactly one swap, carrying both changed fields"
        );
    }

    #[test]
    fn an_already_triaged_issue_is_left_untouched() {
        let before = snapshot("Bug report", "Original report", &[], &[]);
        let plan = plan_valid_update(&before, "Corrected.")
            .unwrap_or_else(|_| panic!("a usable artifact"))
            .unwrap_or_else(|| panic!("a change"));
        let published = snapshot(&plan.title, &plan.body, &[], &[]);
        let effects = FakeEffects::new(vec![published]);

        let applied = run_verdict(&effects, &request("valid", "Corrected.", None))
            .unwrap_or_else(|error| panic!("{error:?}"));

        assert!(!applied.changed);
        assert!(effects.writes().is_empty(), "a re-run writes nothing");
    }

    #[test]
    fn a_close_verdict_comments_restores_the_title_and_closes() {
        let stale = snapshot(&format!("{DONE_PREFIX}Bug report"), "report", &[], &[]);
        let plan = plan_close_comment(&request("already-fixed", "verified fixed", None))
            .unwrap_or_else(|_| panic!("a usable artifact"));
        let commented = {
            let mut moved = stale.clone();
            moved.snapshot.updated_at = "2026-07-12T11:00:00Z".to_owned();
            moved.comments = vec![plan.published.clone()];
            moved
        };
        let restored = {
            let mut moved = commented.clone();
            moved.snapshot.title = "Bug report".to_owned();
            moved.snapshot.updated_at = "2026-07-12T12:00:00Z".to_owned();
            moved
        };
        let closed = {
            let mut moved = restored.clone();
            moved.snapshot.state = GitHubIssueState::Closed;
            moved.snapshot.updated_at = "2026-07-12T13:00:00Z".to_owned();
            moved
        };
        let effects = FakeEffects::new(vec![
            stale.clone(),     // first read
            stale,             // recheck before the comment
            commented.clone(), // comment read-back
            commented,         // recheck before the title restoration
            restored.clone(),  // title read-back
            restored,          // recheck before the close
            closed,            // close read-back
        ]);

        let applied = run_verdict(&effects, &request("already-fixed", "verified fixed", None))
            .unwrap_or_else(|error| panic!("{error:?}"));

        assert!(applied.changed);
        assert_eq!(
            effects.writes(),
            vec![
                format!("comment:{}", plan.published),
                "mutate:{Title}".to_owned(),
                "close".to_owned(),
            ],
            "comment, then the title restoration, then the close"
        );
    }

    #[test]
    fn a_duplicate_verdict_verifies_the_canonical_issue_first() {
        let base = snapshot("Bug report", "report", &[], &[]);
        let canonical = {
            let mut other = base.clone();
            other.snapshot.issue = 42;
            other.url = "https://github.com/owner/repo/issues/42".to_owned();
            other
        };
        // The canonical read is refused, so nothing is ever published.
        let closed_canonical = {
            let mut other = canonical;
            other.snapshot.state = GitHubIssueState::Closed;
            other
        };
        let effects = FakeEffects::new(vec![base, closed_canonical]);

        let error =
            run_verdict(&effects, &request("duplicate", "same as #42", Some(42))).unwrap_err();

        assert_eq!(error.code, EXIT_PROTECTED);
        assert!(
            effects.writes().is_empty(),
            "a refused duplicate writes nothing"
        );
    }

    #[test]
    fn a_verdict_refuses_when_the_issue_moves_before_the_mutation() {
        let before = snapshot("Bug report", "Original report", &[], &[]);
        let moved_on = moved(&before, "2026-07-12T11:00:00Z");
        let effects = FakeEffects::new(vec![before, moved_on]);

        let error = run_verdict(&effects, &request("valid", "Corrected.", None)).unwrap_err();

        assert_eq!(error.code, EXIT_STALE);
        assert!(
            effects.writes().is_empty(),
            "a stale issue is never written"
        );
    }

    #[test]
    fn a_verdict_refuses_a_security_report_before_its_first_write() {
        let sensitive = snapshot("Bug report", "an RCE in the parser", &[], &[]);
        let effects = FakeEffects::new(vec![sensitive]);

        let error = run_verdict(&effects, &request("valid", "Corrected.", None)).unwrap_err();

        assert_eq!(error.code, EXIT_PROTECTED);
        assert!(effects.writes().is_empty());
    }

    #[test]
    fn a_verdict_refuses_a_read_back_that_does_not_carry_the_write() {
        let before = snapshot("Bug report", "Original report", &[], &[]);
        // The read-back moved but published something else entirely.
        let wrong = moved(
            &snapshot("Bug report", "someone else's body", &[], &[]),
            "2026-07-12T11:00:00Z",
        );
        let effects = FakeEffects::new(vec![before.clone(), before, wrong]);

        let error = run_verdict(&effects, &request("valid", "Corrected.", None)).unwrap_err();

        assert_eq!(error.code, EXIT_POSTCONDITION);
    }

    #[test]
    fn a_verdict_refuses_a_mutation_that_did_not_advance_the_issue() {
        let before = snapshot("Bug report", "Original report", &[], &[]);
        let effects = FakeEffects::new(vec![before.clone(), before.clone(), before]);

        let error = run_verdict(&effects, &request("valid", "Corrected.", None)).unwrap_err();

        assert_eq!(error.code, EXIT_POSTCONDITION);
    }

    #[test]
    fn an_already_published_verdict_comment_is_not_published_twice() {
        let plan = plan_close_comment(&request("invalid", "not a defect", None))
            .unwrap_or_else(|_| panic!("a usable artifact"));
        let commented = snapshot("Bug report", "report", &[], &[&plan.published]);
        let closed = {
            let mut moved = commented.clone();
            moved.snapshot.state = GitHubIssueState::Closed;
            moved.snapshot.updated_at = "2026-07-12T11:00:00Z".to_owned();
            moved
        };
        let effects = FakeEffects::new(vec![
            commented.clone(),
            commented, // recheck before the close
            closed,    // close read-back
        ]);

        let applied = run_verdict(&effects, &request("invalid", "not a defect", None))
            .unwrap_or_else(|error| panic!("{error:?}"));

        assert!(applied.changed);
        assert_eq!(
            effects.writes(),
            vec!["close".to_owned()],
            "the comment step is a no-op and the title needs no restoration"
        );
    }

    #[test]
    fn a_diagnostic_is_redacted_flattened_and_bounded() {
        assert_eq!(flat("  one\ntwo\r three  "), "one two  three");
        assert_eq!(
            flat("token ghp_abcdefghijklmnopqrstuvwxyz0123456789"),
            "token <REDACTED-TOKEN>"
        );
        assert_eq!(flat(&"x".repeat(1200)).chars().count(), 1000);
    }

    #[test]
    fn only_a_github_remote_yields_a_slug() {
        for url in [
            "https://github.com/character-ai/larch.git",
            "git@github.com:character-ai/larch",
            "ssh://git@github.com/character-ai/larch.git",
        ] {
            assert_eq!(
                github_slug(url).as_deref(),
                Some("character-ai/larch"),
                "{url}"
            );
        }
        for url in [
            "https://gitlab.com/a/b.git",
            "https://github.com/onlyowner",
            "https://github.com/a/b/c",
            "",
        ] {
            assert_eq!(github_slug(url), None, "{url}");
        }
    }

    #[test]
    fn only_an_immutable_pull_head_is_accepted() {
        assert_eq!(pull_request_head("refs/pull/42/head"), Some(42));
        for reference in [
            "refs/pull/0/head",
            "refs/pull/01/head",
            "refs/pull//head",
            "refs/pull/42/merge",
            "refs/heads/main",
        ] {
            assert_eq!(pull_request_head(reference), None, "{reference}");
        }
    }

    #[test]
    fn only_the_utc_spelling_is_a_snapshot_timestamp() {
        assert!(is_utc_timestamp("2026-07-12T10:00:00Z"));
        assert!(is_utc_timestamp("2026-07-12T10:00:00.123456Z"));
        for value in [
            "2026-07-12T10:00:00",
            "2026-07-12T10:00:00+00:00",
            "2026-07-12 10:00:00Z",
            "2026-07-12T10:00:00.Z",
            "",
        ] {
            assert!(!is_utc_timestamp(value), "{value}");
        }
    }

    #[test]
    fn a_security_classification_comes_from_any_surface() {
        assert!(is_security_sensitive(&snapshot(
            "x",
            "y",
            &["security"],
            &[]
        )));
        assert!(is_security_sensitive(&snapshot(
            "x",
            "y",
            &[],
            &["an RCE here"]
        )));
        assert!(is_security_sensitive(&snapshot(
            "token exposure",
            "y",
            &[],
            &[]
        )));
        assert!(!is_security_sensitive(&snapshot(
            "x",
            "y",
            &["bug"],
            &["fine"]
        )));
    }

    #[test]
    fn protected_state_covers_lifecycle_labels_and_foreign_markers() {
        let stale = format!("{DONE_PREFIX}x");
        assert_eq!(
            has_protected_state(&snapshot(&stale, "y", &[], &[]), false),
            Ok(true)
        );
        // A close verdict restores the title itself, so a stale prefix is not
        // protection there.
        assert_eq!(
            has_protected_state(&snapshot(&stale, "y", &[], &[]), true),
            Ok(false)
        );
        assert_eq!(
            has_protected_state(&snapshot("x", "y", &["needs-clarification"], &[]), true),
            Ok(true)
        );
        assert_eq!(
            has_protected_state(&snapshot("x", "<!-- larch:plan:start -->", &[], &[]), true),
            Ok(true)
        );
        assert_eq!(
            has_protected_state(&snapshot("x", "y", &[], &[]), false),
            Ok(false)
        );
    }

    #[test]
    fn an_issue_url_yields_only_its_path() {
        assert_eq!(
            url_path("https://github.com/owner/repo/issues/7"),
            "/owner/repo/issues/7"
        );
        assert_eq!(
            url_path("https://github.com/owner/repo/issues/7?x=1"),
            "/owner/repo/issues/7"
        );
        assert_eq!(url_path("https://github.com"), "");
    }
}
