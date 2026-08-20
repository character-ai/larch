//! The `clarify state|comment-fetch|comment-post|label` verbs (#8587).
//!
//! These are the clarification round-trip primitives the `/design` Step 0b loop
//! and the `/implement` preflight audit call. Ported from
//! `python/larch/design/clarify.py`; the pure state machine lives in
//! `larch_core::design::clarify`, and every GitHub effect sits behind the
//! [`ClarifyEffects`] seam so the verbs stay provable offline.
//!
//! The `design clarify` fetch/publish orchestrator that drives these verbs from
//! the design phase lives in `clarify_orchestrator`.

use std::collections::BTreeSet;
use std::ffi::OsString;
use std::fs;
use std::path::Path;
use std::process::ExitCode;

use larch_adapters::github::{IssueMutationOwner, OctocrabGitHubService};
use larch_adapters::runtime::Cancellation;
use larch_core::{
    CLARIFY_LABEL_COLOR, CLARIFY_LABEL_DESCRIPTION, CLARIFY_LABEL_NAME, ClarifyState,
    GitHubLabelCreate, GitHubService, IssueMutationRequest, emit_kv, evaluate_comment_bodies,
    redact, request_body_remainder,
};

use crate::github_repository_resolution::{
    ResolutionStatus, ambient_repo_resolution, repository_ref, validate_repo_slug,
};
use crate::github_service::{ServiceFailure, with_github_service};
use crate::issue_mutation_support::authorization_request;

/// One issue comment reduced to the fields the clarify verbs report.
pub struct GhComment {
    pub id: u64,
    pub body: String,
    pub url: String,
}

/// Why ambient or explicit repository resolution refused a slug.
pub enum RepoResolveError {
    /// A present slug failed validation.
    Invalid,
    /// No repository could be determined at all.
    Unresolved,
}

/// Every GitHub effect the clarify verbs perform, behind one seam.
pub trait ClarifyEffects {
    /// Resolve the target repository from an explicit `--repo` or the checkout.
    fn resolve_repo(&self, repo: Option<&str>) -> Result<String, RepoResolveError>;
    /// List every comment on one issue.
    fn list_comments(&self, repo: &str, issue: u64) -> Result<Vec<GhComment>, String>;
    /// Post one comment, reporting its id and URL.
    fn post_comment(&self, repo: &str, issue: u64, body: &str) -> Result<GhComment, String>;
    /// Read one issue's current label names.
    fn issue_labels(&self, repo: &str, issue: u64) -> Result<Vec<String>, String>;
    /// Idempotently create the clarification label in one repository.
    fn create_clarify_label(&self, repo: &str) -> Result<(), String>;
    /// Replace one issue's label set with `labels`.
    fn set_issue_labels(
        &self,
        repo: &str,
        issue: u64,
        labels: BTreeSet<String>,
    ) -> Result<(), String>;
}

/// How a clarify verb failed, mapped to a KEY=value row and exit code.
#[derive(Debug)]
pub enum ClarifyError {
    /// A boundary or input error: `FAILED=true`, `ERROR=<token>`, exit 1.
    Validation(String),
    /// Repository resolution found nothing: exit 2.
    Unresolved,
    /// A transport or redaction failure carrying a redacted detail: exit 2.
    Ship(String),
}

impl ClarifyError {
    fn validation(token: &str) -> Self {
        Self::Validation(token.to_owned())
    }
}

/// True when `value` is a non-zero run of ASCII digits.
pub fn is_positive_int_text(value: &str) -> bool {
    !value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit()) && value != "0"
}

/// Validate `value` as positive-integer text, raising `token` otherwise.
fn ensure_positive(value: &str, token: &str) -> Result<u64, ClarifyError> {
    if is_positive_int_text(value) {
        value.parse().map_err(|_| ClarifyError::validation(token))
    } else {
        Err(ClarifyError::validation(token))
    }
}

/// Resolve the repository, mapping resolution failures to clarify errors.
fn resolve_repo(effects: &dyn ClarifyEffects, repo: Option<&str>) -> Result<String, ClarifyError> {
    effects.resolve_repo(repo).map_err(|error| match error {
        RepoResolveError::Invalid => ClarifyError::validation("invalid-repo"),
        RepoResolveError::Unresolved => ClarifyError::Unresolved,
    })
}

/// Collapse a value to one KEY=value-safe line: trimmed, CR/LF replaced.
fn kv_safe(text: &str) -> String {
    text.trim().replace(['\r', '\n'], " ")
}

// ---------------------------------------------------------------------------
// clarify state
// ---------------------------------------------------------------------------

/// Evaluate the clarify thread state for one issue.
pub fn clarify_state(
    effects: &dyn ClarifyEffects,
    issue: &str,
    repo: Option<&str>,
) -> Result<ClarifyState, ClarifyError> {
    let number = ensure_positive(issue, "invalid-issue")?;
    let resolved = resolve_repo(effects, repo)?;
    let comments = effects
        .list_comments(&resolved, number)
        .map_err(ClarifyError::Ship)?;
    Ok(evaluate_comment_bodies(
        comments.iter().map(|comment| &comment.body),
    ))
}

// ---------------------------------------------------------------------------
// clarify comment-fetch
// ---------------------------------------------------------------------------

/// The result of a `comment-fetch`: the gh comment id and the written path.
pub struct FetchResult {
    pub comment_id: String,
    pub body_file: String,
}

/// Write the request body identified by `comment_id` to `out_file`.
pub fn clarify_comment_fetch(
    effects: &dyn ClarifyEffects,
    issue: &str,
    comment_id: &str,
    out_file: &str,
    repo: Option<&str>,
) -> Result<FetchResult, ClarifyError> {
    let number = ensure_positive(issue, "invalid-issue")?;
    let comment_id_text = ensure_positive(comment_id, "invalid-id").map(|_| comment_id)?;
    let resolved = resolve_repo(effects, repo)?;
    let comments = effects
        .list_comments(&resolved, number)
        .map_err(ClarifyError::Ship)?;
    for comment in &comments {
        if let Some(remainder) = request_body_remainder(&comment.body, comment_id_text) {
            write_request_body(out_file, &remainder)?;
            return Ok(FetchResult {
                comment_id: comment.id.to_string(),
                body_file: out_file.to_owned(),
            });
        }
    }
    Err(ClarifyError::Validation(format!(
        "request comment not found: <!-- larch:clarify-request id={comment_id_text} -->"
    )))
}

/// Atomically write the fetched request body, refusing symlink/dir targets.
fn write_request_body(out_file: &str, content: &str) -> Result<(), ClarifyError> {
    let path = Path::new(out_file);
    if path.is_dir() {
        return Err(ClarifyError::validation("write-target-directory"));
    }
    if path.is_symlink() {
        return Err(ClarifyError::validation("write-target-symlink"));
    }
    let name = path.file_name().map_or_else(
        || ".clarify".to_owned(),
        |value| value.to_string_lossy().into_owned(),
    );
    let temporary = path.with_file_name(format!(".{name}.{}.tmp", std::process::id()));
    let written = fs::write(&temporary, content).and_then(|()| fs::rename(&temporary, path));
    if written.is_err() {
        let _ = fs::remove_file(&temporary);
        return Err(ClarifyError::validation("write-failed"));
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// clarify comment-post
// ---------------------------------------------------------------------------

/// The result of a `comment-post`: posting state, id, URL, and marker.
pub struct PostResult {
    pub posted: bool,
    pub comment_id: String,
    pub comment_url: String,
    pub marker: String,
}

/// Post a clarify request or response comment carrying the marker for `id`.
pub fn clarify_comment_post(
    effects: &dyn ClarifyEffects,
    issue: &str,
    kind: &str,
    comment_id: &str,
    content_file: &str,
    repo: Option<&str>,
) -> Result<PostResult, ClarifyError> {
    let number = ensure_positive(issue, "invalid-issue")?;
    if kind != "request" && kind != "response" {
        return Err(ClarifyError::validation("invalid-kind"));
    }
    let comment_id_text = ensure_positive(comment_id, "invalid-id").map(|_| comment_id)?;
    let content = read_content_file(content_file)?;
    let resolved = resolve_repo(effects, repo)?;
    let marker = format!("<!-- larch:clarify-{kind} id={comment_id_text} -->");
    let body = format!("{marker}\n{content}");
    let redacted = redact(&body);
    if redacted.text().contains("[content truncated") {
        return Err(ClarifyError::Ship("redaction failed".to_owned()));
    }
    let posted = effects
        .post_comment(&resolved, number, redacted.text())
        .map_err(ClarifyError::Ship)?;
    let parsed_id = parse_issue_comment_id(&posted.url);
    Ok(PostResult {
        posted: true,
        comment_id: parsed_id,
        comment_url: kv_safe(&posted.url),
        marker,
    })
}

/// Read a UTF-8 content file, mapping I/O and encoding failures to tokens.
fn read_content_file(content_file: &str) -> Result<String, ClarifyError> {
    let path = Path::new(content_file);
    if !path.is_file() {
        return Err(ClarifyError::Validation(format!(
            "content file not found: {content_file}"
        )));
    }
    match fs::read(path) {
        Ok(bytes) => String::from_utf8(bytes).map_err(|_| {
            ClarifyError::Validation(format!("content file is not valid utf-8: {content_file}"))
        }),
        Err(_error) => Err(ClarifyError::Validation(format!(
            "content file not found: {content_file}"
        ))),
    }
}

/// Extract the `issuecomment-<id>` suffix a posted comment URL carries.
fn parse_issue_comment_id(url: &str) -> String {
    let Some(index) = url.find("issuecomment-") else {
        return String::new();
    };
    let tail = &url[index + "issuecomment-".len()..];
    let digits: String = tail.chars().take_while(char::is_ascii_digit).collect();
    digits
}

// ---------------------------------------------------------------------------
// clarify label
// ---------------------------------------------------------------------------

/// The result of a `label` flip: whether it changed, the action, the label.
pub struct LabelResult {
    pub changed: bool,
    pub action: String,
    pub label: String,
}

/// Add or remove the clarification label on one issue.
pub fn clarify_label(
    effects: &dyn ClarifyEffects,
    issue: &str,
    action: &str,
    repo: Option<&str>,
    create_if_missing: bool,
) -> Result<LabelResult, ClarifyError> {
    let number = ensure_positive(issue, "invalid-issue")?;
    if action != "add" && action != "remove" {
        return Err(ClarifyError::validation("invalid-action"));
    }
    let resolved = resolve_repo(effects, repo)?;
    let labels = effects
        .issue_labels(&resolved, number)
        .map_err(ClarifyError::Ship)?;
    let has_label = labels.iter().any(|name| name == CLARIFY_LABEL_NAME);

    if action == "add" {
        if has_label {
            return Ok(unchanged("add"));
        }
        if create_if_missing {
            effects
                .create_clarify_label(&resolved)
                .map_err(ClarifyError::Ship)?;
        }
        let mut desired: BTreeSet<String> = labels.into_iter().collect();
        let _inserted = desired.insert(CLARIFY_LABEL_NAME.to_owned());
        effects
            .set_issue_labels(&resolved, number, desired)
            .map_err(ClarifyError::Ship)?;
        return Ok(changed("add"));
    }

    if !has_label {
        return Ok(unchanged("remove"));
    }
    let desired: BTreeSet<String> = labels
        .into_iter()
        .filter(|name| name != CLARIFY_LABEL_NAME)
        .collect();
    effects
        .set_issue_labels(&resolved, number, desired)
        .map_err(ClarifyError::Ship)?;
    Ok(changed("remove"))
}

fn changed(action: &str) -> LabelResult {
    LabelResult {
        changed: true,
        action: action.to_owned(),
        label: CLARIFY_LABEL_NAME.to_owned(),
    }
}

fn unchanged(action: &str) -> LabelResult {
    LabelResult {
        changed: false,
        action: action.to_owned(),
        label: CLARIFY_LABEL_NAME.to_owned(),
    }
}

// ---------------------------------------------------------------------------
// Live GitHub effects
// ---------------------------------------------------------------------------

/// The live effects: typed reads and field-scoped writes on one client.
pub struct LiveEffects;

fn gh_comment(comment: larch_core::GitHubComment) -> GhComment {
    GhComment {
        id: comment.id,
        body: comment.body,
        url: comment.url,
    }
}

/// Run one operation against the typed repository identity a verb named.
fn with_repo<T>(
    repo: &str,
    issue: u64,
    operation: impl AsyncFnOnce(
        &OctocrabGitHubService,
        &Cancellation,
        &larch_core::GitHubRepositoryRef,
        u64,
    ) -> Result<T, String>,
) -> Result<T, String> {
    let reference = repository_ref(repo).map_err(|()| "invalid-identity".to_owned())?;
    with_github_service(async |service, cancellation| {
        operation(service, cancellation, &reference, issue).await
    })
    .map_err(service_detail)
}

fn service_detail(failure: ServiceFailure) -> String {
    match failure {
        ServiceFailure::Setup(detail) | ServiceFailure::Operation(detail) => detail,
    }
}

impl ClarifyEffects for LiveEffects {
    fn resolve_repo(&self, repo: Option<&str>) -> Result<String, RepoResolveError> {
        if let Some(slug) = repo {
            if validate_repo_slug(slug) {
                return Ok(slug.to_owned());
            }
            return Err(RepoResolveError::Invalid);
        }
        let resolution = ambient_repo_resolution();
        match resolution.status {
            ResolutionStatus::Valid => Ok(resolution.candidate),
            ResolutionStatus::Invalid => Err(RepoResolveError::Invalid),
            ResolutionStatus::Absent => Err(RepoResolveError::Unresolved),
        }
    }

    fn list_comments(&self, repo: &str, issue: u64) -> Result<Vec<GhComment>, String> {
        with_repo(repo, issue, async |service, cancel, reference, number| {
            service
                .list_comments(reference, number, cancel)
                .await
                .map(|comments| comments.into_iter().map(gh_comment).collect())
                .map_err(|error| error.to_string())
        })
    }

    fn post_comment(&self, repo: &str, issue: u64, body: &str) -> Result<GhComment, String> {
        let authorization = authorization_request("", "", "", true);
        with_repo(repo, issue, async |service, cancel, reference, number| {
            let owner = IssueMutationOwner::new(service);
            let posted = owner
                .create_comment(cancel, &authorization, reference, number, body)
                .await
                .map_err(|error| error.reason().to_owned())?;
            Ok(gh_comment(posted))
        })
    }

    fn issue_labels(&self, repo: &str, issue: u64) -> Result<Vec<String>, String> {
        with_repo(repo, issue, async |service, cancel, reference, number| {
            IssueMutationOwner::new(service)
                .read_snapshot(reference, number, cancel)
                .await
                .map(|snapshot| snapshot.labels.into_iter().collect())
                .map_err(|error| error.to_string())
        })
    }

    fn create_clarify_label(&self, repo: &str) -> Result<(), String> {
        with_repo(repo, 1, async |service, cancel, reference, _number| {
            let request = GitHubLabelCreate {
                repo: reference.clone(),
                name: CLARIFY_LABEL_NAME.to_owned(),
                color: CLARIFY_LABEL_COLOR.to_owned(),
                description: CLARIFY_LABEL_DESCRIPTION.to_owned(),
            };
            service
                .create_label(&request, cancel)
                .await
                .map(|_label| ())
                .map_err(|error| error.to_string())
        })
    }

    fn set_issue_labels(
        &self,
        repo: &str,
        issue: u64,
        labels: BTreeSet<String>,
    ) -> Result<(), String> {
        with_repo(repo, issue, async |service, cancel, reference, number| {
            let owner = IssueMutationOwner::new(service);
            let snapshot = owner
                .read_snapshot(reference, number, cancel)
                .await
                .map_err(|error| error.to_string())?;
            owner
                .apply(
                    cancel,
                    &authorization_request("", "", "", true),
                    &IssueMutationRequest::replace_labels(&snapshot, labels.clone()),
                )
                .await
                .map(|_verified| ())
                .map_err(|error| error.to_string())
        })
    }
}

// ---------------------------------------------------------------------------
// KEY=value emission + error mapping
// ---------------------------------------------------------------------------

/// Redact a transport error and cap it to the KEY=value budget.
fn redact_gh_error(text: &str) -> String {
    let redacted = redact(text);
    if redacted.text().contains("[content truncated") {
        return "gh stderr redaction unavailable".to_owned();
    }
    let flat = redacted.text().replace(['\r', '\n'], " ");
    flat.chars().take(500).collect()
}

/// Emit the shared failure rows and map a clarify error to an exit code.
fn emit_clarify_error(error: &ClarifyError) -> ExitCode {
    match error {
        ClarifyError::Validation(token) => {
            emit_kv("FAILED", "true");
            emit_kv("ERROR", token);
            ExitCode::from(1)
        }
        ClarifyError::Unresolved => {
            emit_kv("FAILED", "true");
            emit_kv("ERROR", "could not determine repo");
            ExitCode::from(2)
        }
        ClarifyError::Ship(detail) => {
            emit_kv("FAILED", "true");
            emit_kv("ERROR", &redact_gh_error(detail));
            ExitCode::from(2)
        }
    }
}

// ---------------------------------------------------------------------------
// argv parsing
// ---------------------------------------------------------------------------

/// A minimal `--flag value` / `--flag` parser for the clarify verbs.
struct ParsedArgs {
    values: std::collections::BTreeMap<String, String>,
    switches: BTreeSet<String>,
    help: bool,
    ok: bool,
}

fn parse_args(argv: &[OsString], value_flags: &[&str], switch_flags: &[&str]) -> ParsedArgs {
    let mut values = std::collections::BTreeMap::new();
    let mut switches = BTreeSet::new();
    let mut help = false;
    let mut ok = true;
    let mut index = 0;
    let tokens: Vec<String> = argv
        .iter()
        .map(|token| token.to_string_lossy().into_owned())
        .collect();
    while index < tokens.len() {
        let token = &tokens[index];
        if token == "-h" || token == "--help" {
            help = true;
            break;
        }
        if switch_flags.contains(&token.as_str()) {
            let _inserted = switches.insert(token.clone());
            index += 1;
        } else if value_flags.contains(&token.as_str()) {
            let Some(value) = tokens.get(index + 1) else {
                ok = false;
                break;
            };
            let _prior = values.insert(token.clone(), value.clone());
            index += 2;
        } else {
            ok = false;
            break;
        }
    }
    ParsedArgs {
        values,
        switches,
        help,
        ok,
    }
}

/// Validate the CLI `--issue` argument, printing a stderr message on refusal.
fn cli_issue_ok(issue: &str, verb: &str) -> bool {
    if is_positive_int_text(issue) {
        true
    } else {
        eprintln!("clarify-{verb}.sh: --issue must be a positive integer");
        false
    }
}

// ---------------------------------------------------------------------------
// verb entrypoints
// ---------------------------------------------------------------------------

/// The `clarify state` entrypoint.
pub fn clarify_state_main(argv: &[OsString]) -> ExitCode {
    clarify_state_main_with(&LiveEffects, argv)
}

/// The `clarify comment-fetch` entrypoint.
pub fn clarify_comment_fetch_main(argv: &[OsString]) -> ExitCode {
    clarify_comment_fetch_main_with(&LiveEffects, argv)
}

/// The `clarify comment-post` entrypoint.
pub fn clarify_comment_post_main(argv: &[OsString]) -> ExitCode {
    clarify_comment_post_main_with(&LiveEffects, argv)
}

/// The `clarify label` entrypoint.
pub fn clarify_label_main(argv: &[OsString]) -> ExitCode {
    clarify_label_main_with(&LiveEffects, argv)
}

fn clarify_state_main_with(effects: &dyn ClarifyEffects, argv: &[OsString]) -> ExitCode {
    let parsed = parse_args(argv, &["--issue", "--repo"], &[]);
    if parsed.help {
        eprintln!("clarify state --issue <N> [--repo OWNER/REPO]");
        return ExitCode::from(0);
    }
    let Some(issue) = parsed
        .values
        .get("--issue")
        .filter(|value| !value.is_empty())
    else {
        eprintln!("clarify state --issue <N> [--repo OWNER/REPO]");
        return ExitCode::from(1);
    };
    if !parsed.ok || !cli_issue_ok(issue, "state") {
        return ExitCode::from(1);
    }
    let repo = parsed.values.get("--repo").map(String::as_str);
    match clarify_state(effects, issue, repo) {
        Ok(state) => {
            emit_kv("STATE", &state.state);
            emit_kv("LAST_REQUEST_ID", &state.last_request_id);
            emit_kv("LAST_RESPONSE_ID", &state.last_response_id);
            ExitCode::from(0)
        }
        Err(error) => emit_clarify_error(&error),
    }
}

/// The `clarify comment-fetch` implementation over an injected effects seam.
fn clarify_comment_fetch_main_with(effects: &dyn ClarifyEffects, argv: &[OsString]) -> ExitCode {
    let parsed = parse_args(argv, &["--issue", "--id", "--out", "--repo"], &[]);
    if parsed.help {
        eprintln!("clarify comment-fetch --issue <N> --id <N> --out <path> [--repo OWNER/REPO]");
        return ExitCode::from(0);
    }
    let required = ["--issue", "--id", "--out"];
    if required
        .iter()
        .any(|flag| parsed.values.get(*flag).is_none_or(String::is_empty))
    {
        eprintln!("clarify comment-fetch --issue <N> --id <N> --out <path> [--repo OWNER/REPO]");
        return ExitCode::from(1);
    }
    let issue = &parsed.values["--issue"];
    if !parsed.ok || !cli_issue_ok(issue, "comment-fetch") {
        return ExitCode::from(1);
    }
    let repo = parsed.values.get("--repo").map(String::as_str);
    match clarify_comment_fetch(
        effects,
        issue,
        &parsed.values["--id"],
        &parsed.values["--out"],
        repo,
    ) {
        Ok(result) => {
            emit_kv("FETCHED", "true");
            emit_kv("COMMENT_ID", &result.comment_id);
            emit_kv("BODY_FILE", &result.body_file);
            ExitCode::from(0)
        }
        Err(error) => emit_clarify_error(&error),
    }
}

/// The `clarify comment-post` implementation over an injected effects seam.
fn clarify_comment_post_main_with(effects: &dyn ClarifyEffects, argv: &[OsString]) -> ExitCode {
    let parsed = parse_args(
        argv,
        &["--issue", "--kind", "--id", "--content-file", "--repo"],
        &[],
    );
    if parsed.help {
        eprintln!(
            "clarify comment-post --issue <N> --kind request|response --id <N> --content-file <path> [--repo OWNER/REPO]"
        );
        return ExitCode::from(0);
    }
    let required = ["--issue", "--kind", "--id", "--content-file"];
    if required
        .iter()
        .any(|flag| parsed.values.get(*flag).is_none_or(String::is_empty))
    {
        eprintln!(
            "clarify comment-post --issue <N> --kind request|response --id <N> --content-file <path> [--repo OWNER/REPO]"
        );
        return ExitCode::from(1);
    }
    let issue = &parsed.values["--issue"];
    if !parsed.ok || !cli_issue_ok(issue, "comment-post") {
        return ExitCode::from(1);
    }
    let repo = parsed.values.get("--repo").map(String::as_str);
    match clarify_comment_post(
        effects,
        issue,
        &parsed.values["--kind"],
        &parsed.values["--id"],
        &parsed.values["--content-file"],
        repo,
    ) {
        Ok(result) => {
            emit_kv("POSTED", bool_text(result.posted));
            emit_kv("COMMENT_ID", &result.comment_id);
            emit_kv("COMMENT_URL", &result.comment_url);
            emit_kv("MARKER", &result.marker);
            ExitCode::from(0)
        }
        Err(error) => emit_clarify_error(&error),
    }
}

/// The `clarify label` implementation over an injected effects seam.
fn clarify_label_main_with(effects: &dyn ClarifyEffects, argv: &[OsString]) -> ExitCode {
    let parsed = parse_args(
        argv,
        &["--issue", "--action", "--repo"],
        &["--create-if-missing"],
    );
    if parsed.help {
        eprintln!(
            "clarify label --issue <N> --action add|remove [--create-if-missing] [--repo OWNER/REPO]"
        );
        return ExitCode::from(0);
    }
    let required = ["--issue", "--action"];
    if required
        .iter()
        .any(|flag| parsed.values.get(*flag).is_none_or(String::is_empty))
    {
        eprintln!(
            "clarify label --issue <N> --action add|remove [--create-if-missing] [--repo OWNER/REPO]"
        );
        return ExitCode::from(1);
    }
    let issue = &parsed.values["--issue"];
    if !parsed.ok || !cli_issue_ok(issue, "label") {
        return ExitCode::from(1);
    }
    let action = &parsed.values["--action"];
    if action != "add" && action != "remove" {
        eprintln!("clarify-label.sh: --action must be add or remove");
        return ExitCode::from(1);
    }
    let repo = parsed.values.get("--repo").map(String::as_str);
    match clarify_label(
        effects,
        issue,
        action,
        repo,
        parsed.switches.contains("--create-if-missing"),
    ) {
        Ok(result) => {
            emit_kv("CHANGED", bool_text(result.changed));
            emit_kv("ACTION", &result.action);
            emit_kv("LABEL", &result.label);
            ExitCode::from(0)
        }
        Err(error) => emit_clarify_error(&error),
    }
}

const fn bool_text(value: bool) -> &'static str {
    if value { "true" } else { "false" }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;

    #[derive(Default)]
    struct FakeEffects {
        repo: Option<Result<String, u8>>,
        comments: Vec<(u64, String, String)>,
        labels: Vec<String>,
        posts: RefCell<Vec<String>>,
        label_ops: RefCell<Vec<String>>,
        post_url: String,
        post_error: Option<String>,
        label_error: Option<String>,
    }

    impl FakeEffects {
        fn with_repo() -> Self {
            Self {
                repo: Some(Ok("o/r".to_owned())),
                post_url: "https://github.com/o/r/issues/7#issuecomment-123".to_owned(),
                ..Self::default()
            }
        }
    }

    impl ClarifyEffects for FakeEffects {
        fn resolve_repo(&self, repo: Option<&str>) -> Result<String, RepoResolveError> {
            if let Some(slug) = repo {
                if validate_repo_slug(slug) {
                    return Ok(slug.to_owned());
                }
                return Err(RepoResolveError::Invalid);
            }
            match &self.repo {
                Some(Ok(slug)) => Ok(slug.clone()),
                Some(Err(1)) => Err(RepoResolveError::Invalid),
                _ => Err(RepoResolveError::Unresolved),
            }
        }

        fn list_comments(&self, _repo: &str, _issue: u64) -> Result<Vec<GhComment>, String> {
            Ok(self
                .comments
                .iter()
                .map(|(id, body, url)| GhComment {
                    id: *id,
                    body: body.clone(),
                    url: url.clone(),
                })
                .collect())
        }

        fn post_comment(&self, _repo: &str, _issue: u64, body: &str) -> Result<GhComment, String> {
            self.posts.borrow_mut().push(body.to_owned());
            if let Some(error) = &self.post_error {
                return Err(error.clone());
            }
            Ok(GhComment {
                id: 999,
                body: body.to_owned(),
                url: self.post_url.clone(),
            })
        }

        fn issue_labels(&self, _repo: &str, _issue: u64) -> Result<Vec<String>, String> {
            Ok(self.labels.clone())
        }

        fn create_clarify_label(&self, _repo: &str) -> Result<(), String> {
            self.label_ops.borrow_mut().push("create".to_owned());
            Ok(())
        }

        fn set_issue_labels(
            &self,
            _repo: &str,
            _issue: u64,
            labels: BTreeSet<String>,
        ) -> Result<(), String> {
            self.label_ops.borrow_mut().push(format!(
                "set:{}",
                labels.into_iter().collect::<Vec<_>>().join(",")
            ));
            if let Some(error) = &self.label_error {
                return Err(error.clone());
            }
            Ok(())
        }
    }

    fn comment(id: u64, body: &str) -> (u64, String, String) {
        (id, body.to_owned(), String::new())
    }

    fn err_token(result: Result<impl Sized, ClarifyError>) -> String {
        match result {
            Ok(_) => panic!("expected error"),
            Err(ClarifyError::Validation(token)) => token,
            Err(ClarifyError::Unresolved) => "unresolved".to_owned(),
            Err(ClarifyError::Ship(detail)) => format!("ship:{detail}"),
        }
    }

    #[test]
    fn state_reads_thread() {
        let effects = FakeEffects {
            comments: vec![
                comment(1, "<!-- larch:clarify-request id=1 -->"),
                comment(2, "<!-- larch:clarify-response id=1 -->"),
            ],
            ..FakeEffects::with_repo()
        };
        let state = clarify_state(&effects, "7", Some("o/r")).unwrap();
        assert_eq!(state.state, "response-pending");
    }

    #[test]
    fn state_rejects_bad_issue_and_repo() {
        let effects = FakeEffects::with_repo();
        assert_eq!(
            err_token(clarify_state(&effects, "0", Some("o/r"))),
            "invalid-issue"
        );
        assert_eq!(
            err_token(clarify_state(&effects, "7", Some("bad..repo"))),
            "invalid-repo"
        );
    }

    #[test]
    fn state_unresolved_repo_is_distinct() {
        let effects = FakeEffects {
            repo: Some(Err(2)),
            ..FakeEffects::default()
        };
        assert!(matches!(
            clarify_state(&effects, "7", None),
            Err(ClarifyError::Unresolved)
        ));
    }

    #[test]
    fn fetch_writes_request_body_without_stdout() {
        let dir = tempfile::tempdir().unwrap();
        let out = dir.path().join("request.md");
        let effects = FakeEffects {
            comments: vec![
                comment(1, "<!-- larch:clarify-request id=1 -->\nsecret\nline two"),
                comment(3, "<!-- larch:clarify-request id=2 -->\nlatest question"),
            ],
            ..FakeEffects::with_repo()
        };
        let result =
            clarify_comment_fetch(&effects, "7", "2", out.to_str().unwrap(), Some("o/r")).unwrap();
        assert_eq!(result.comment_id, "3");
        assert_eq!(fs::read_to_string(&out).unwrap(), "latest question");
    }

    #[test]
    fn fetch_missing_request_fails() {
        let dir = tempfile::tempdir().unwrap();
        let out = dir.path().join("request.md");
        let effects = FakeEffects {
            comments: vec![comment(1, "<!-- larch:clarify-request id=1 -->\nq")],
            ..FakeEffects::with_repo()
        };
        assert!(
            err_token(clarify_comment_fetch(
                &effects,
                "7",
                "2",
                out.to_str().unwrap(),
                Some("o/r")
            ))
            .starts_with("request comment not found")
        );
        assert!(!out.exists());
    }

    #[test]
    fn fetch_invalid_id_is_invalid_id() {
        let dir = tempfile::tempdir().unwrap();
        let out = dir.path().join("request.md");
        let effects = FakeEffects::with_repo();
        assert_eq!(
            err_token(clarify_comment_fetch(
                &effects,
                "7",
                "0",
                out.to_str().unwrap(),
                Some("o/r")
            )),
            "invalid-id"
        );
    }

    #[test]
    fn post_redacts_body_and_parses_id() {
        let dir = tempfile::tempdir().unwrap();
        let content = dir.path().join("content.md");
        let secret = format!("sk-{}", "a".repeat(25));
        fs::write(&content, format!("hello {secret}")).unwrap();
        let effects = FakeEffects::with_repo();
        let result = clarify_comment_post(
            &effects,
            "7",
            "request",
            "1",
            content.to_str().unwrap(),
            Some("o/r"),
        )
        .unwrap();
        assert_eq!(result.comment_id, "123");
        assert_eq!(result.marker, "<!-- larch:clarify-request id=1 -->");
        let posted = effects.posts.borrow();
        assert_eq!(posted.len(), 1);
        assert!(!posted[0].contains(&secret));
    }

    #[test]
    fn post_response_kind_and_parse_miss() {
        let dir = tempfile::tempdir().unwrap();
        let content = dir.path().join("content.md");
        fs::write(&content, "body").unwrap();
        let effects = FakeEffects {
            post_url: "not a url".to_owned(),
            ..FakeEffects::with_repo()
        };
        let result = clarify_comment_post(
            &effects,
            "7",
            "response",
            "2",
            content.to_str().unwrap(),
            Some("o/r"),
        )
        .unwrap();
        assert_eq!(result.comment_id, "");
        assert_eq!(result.comment_url, "not a url");
        assert_eq!(result.marker, "<!-- larch:clarify-response id=2 -->");
    }

    #[test]
    fn post_validates_content_file_before_repo() {
        let effects = FakeEffects {
            repo: Some(Err(2)),
            ..FakeEffects::default()
        };
        assert_eq!(
            err_token(clarify_comment_post(
                &effects,
                "7",
                "request",
                "1",
                "missing.md",
                None
            )),
            "content file not found: missing.md"
        );
        assert!(effects.posts.borrow().is_empty());
    }

    #[test]
    fn post_rejects_bad_kind_and_id() {
        let dir = tempfile::tempdir().unwrap();
        let content = dir.path().join("content.md");
        fs::write(&content, "body").unwrap();
        let effects = FakeEffects::with_repo();
        assert_eq!(
            err_token(clarify_comment_post(
                &effects,
                "7",
                "bad",
                "1",
                content.to_str().unwrap(),
                Some("o/r")
            )),
            "invalid-kind"
        );
        assert_eq!(
            err_token(clarify_comment_post(
                &effects,
                "7",
                "request",
                "0",
                content.to_str().unwrap(),
                Some("o/r")
            )),
            "invalid-id"
        );
    }

    #[test]
    fn post_non_utf8_content_fails() {
        let dir = tempfile::tempdir().unwrap();
        let content = dir.path().join("content.bin");
        fs::write(&content, [0xff, 0xfe, 0xfd]).unwrap();
        let effects = FakeEffects::with_repo();
        assert!(
            err_token(clarify_comment_post(
                &effects,
                "7",
                "request",
                "1",
                content.to_str().unwrap(),
                Some("o/r")
            ))
            .contains("utf-8")
        );
    }

    #[test]
    fn label_add_creates_and_sets() {
        let effects = FakeEffects::with_repo();
        let result = clarify_label(&effects, "7", "add", Some("o/r"), true).unwrap();
        assert!(result.changed);
        assert_eq!(result.label, CLARIFY_LABEL_NAME);
        let ops = effects.label_ops.borrow();
        assert_eq!(ops[0], "create");
        assert_eq!(ops[1], format!("set:{CLARIFY_LABEL_NAME}"));
    }

    #[test]
    fn label_add_present_skips() {
        let effects = FakeEffects {
            labels: vec![CLARIFY_LABEL_NAME.to_owned()],
            ..FakeEffects::with_repo()
        };
        let result = clarify_label(&effects, "7", "add", Some("o/r"), true).unwrap();
        assert!(!result.changed);
        assert!(effects.label_ops.borrow().is_empty());
    }

    #[test]
    fn label_case_difference_is_absent() {
        let effects = FakeEffects {
            labels: vec!["Needs-Design-Clarification".to_owned()],
            ..FakeEffects::with_repo()
        };
        assert!(
            clarify_label(&effects, "7", "add", Some("o/r"), false)
                .unwrap()
                .changed
        );
        let effects = FakeEffects {
            labels: vec!["Needs-Design-Clarification".to_owned()],
            ..FakeEffects::with_repo()
        };
        assert!(
            !clarify_label(&effects, "7", "remove", Some("o/r"), false)
                .unwrap()
                .changed
        );
    }

    #[test]
    fn label_remove_present_sets_without_label() {
        let effects = FakeEffects {
            labels: vec![CLARIFY_LABEL_NAME.to_owned(), "keep".to_owned()],
            ..FakeEffects::with_repo()
        };
        let result = clarify_label(&effects, "7", "remove", Some("o/r"), false).unwrap();
        assert!(result.changed);
        assert_eq!(effects.label_ops.borrow()[0], "set:keep");
    }

    #[test]
    fn label_set_failure_is_ship() {
        let effects = FakeEffects {
            label_error: Some("boom".to_owned()),
            ..FakeEffects::with_repo()
        };
        assert_eq!(
            err_token(clarify_label(&effects, "7", "add", Some("o/r"), false)),
            "ship:boom"
        );
    }

    #[test]
    fn redact_gh_error_caps_length() {
        let secret = format!("ghp_{}", "a".repeat(25));
        let long = format!("{secret}{}", "x".repeat(600));
        let out = redact_gh_error(&long);
        assert!(!out.contains(&secret));
        assert!(out.len() <= 500);
    }

    #[test]
    fn positive_int_text_matches_python() {
        assert!(is_positive_int_text("1"));
        assert!(!is_positive_int_text("0"));
        assert!(!is_positive_int_text("abc"));
        assert!(!is_positive_int_text(""));
    }

    fn argv(parts: &[&str]) -> Vec<OsString> {
        parts.iter().map(OsString::from).collect()
    }

    #[test]
    fn state_main_covers_success_and_arg_errors() {
        let effects = FakeEffects {
            comments: vec![comment(1, "<!-- larch:clarify-request id=1 -->")],
            ..FakeEffects::with_repo()
        };
        // Success emits STATE rows; error/usage/help branches return early.
        let _ok = clarify_state_main_with(&effects, &argv(&["--issue", "7", "--repo", "o/r"]));
        let _bad_issue = clarify_state_main_with(&effects, &argv(&["--issue", "0"]));
        let _missing = clarify_state_main_with(&effects, &argv(&[]));
        let _help = clarify_state_main_with(&effects, &argv(&["--help"]));
        let _unknown = clarify_state_main_with(&effects, &argv(&["--issue", "7", "--nope"]));
    }

    #[test]
    fn comment_fetch_main_writes_file_and_maps_arg_errors() {
        let dir = tempfile::tempdir().unwrap();
        let out = dir.path().join("req.md");
        let effects = FakeEffects {
            comments: vec![comment(9, "<!-- larch:clarify-request id=2 -->\nbody text")],
            ..FakeEffects::with_repo()
        };
        let _ok = clarify_comment_fetch_main_with(
            &effects,
            &argv(&[
                "--issue",
                "7",
                "--id",
                "2",
                "--out",
                out.to_str().unwrap(),
                "--repo",
                "o/r",
            ]),
        );
        assert_eq!(fs::read_to_string(&out).unwrap(), "body text");
        let _missing =
            clarify_comment_fetch_main_with(&effects, &argv(&["--issue", "7", "--id", "2"]));
        let _bad_issue = clarify_comment_fetch_main_with(
            &effects,
            &argv(&["--issue", "0", "--id", "2", "--out", "x"]),
        );
        let _help = clarify_comment_fetch_main_with(&effects, &argv(&["--help"]));
    }

    #[test]
    fn comment_post_main_covers_success_and_arg_errors() {
        let dir = tempfile::tempdir().unwrap();
        let content = dir.path().join("c.md");
        fs::write(&content, "hello").unwrap();
        let effects = FakeEffects::with_repo();
        let _ok = clarify_comment_post_main_with(
            &effects,
            &argv(&[
                "--issue",
                "7",
                "--kind",
                "request",
                "--id",
                "1",
                "--content-file",
                content.to_str().unwrap(),
                "--repo",
                "o/r",
            ]),
        );
        assert_eq!(effects.posts.borrow().len(), 1);
        let _missing =
            clarify_comment_post_main_with(&effects, &argv(&["--issue", "7", "--kind", "request"]));
        let _bad_issue = clarify_comment_post_main_with(
            &effects,
            &argv(&[
                "--issue",
                "0",
                "--kind",
                "request",
                "--id",
                "1",
                "--content-file",
                "x",
            ]),
        );
        let _help = clarify_comment_post_main_with(&effects, &argv(&["--help"]));
    }

    #[test]
    fn label_main_covers_success_and_arg_errors() {
        let effects = FakeEffects::with_repo();
        let _ok = clarify_label_main_with(
            &effects,
            &argv(&[
                "--issue",
                "7",
                "--action",
                "add",
                "--create-if-missing",
                "--repo",
                "o/r",
            ]),
        );
        assert!(!effects.label_ops.borrow().is_empty());
        let _bad_action =
            clarify_label_main_with(&effects, &argv(&["--issue", "7", "--action", "bad"]));
        let _missing = clarify_label_main_with(&effects, &argv(&["--issue", "7"]));
        let _bad_issue =
            clarify_label_main_with(&effects, &argv(&["--issue", "0", "--action", "add"]));
        let _help = clarify_label_main_with(&effects, &argv(&["--help"]));
    }
}
