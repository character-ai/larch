//! `oos file`, the post-ship accepted-OOS filing driver.
//!
//! One run's accepted, non-security out-of-scope observations become public
//! GitHub issues here: the batch is composed, optionally combined by Codex,
//! capped, ordered by its file-conflict edges, and filed one item at a time
//! with the tracking issue and the intra-batch edges wired behind each create.
//!
//! Two properties dominate the design. Filing is *resumable*: every durable
//! record — the sentinel, the run-log OOS batch, and each block's own
//! `Filed URL` field — is read back before anything is filed, so an interrupted
//! run refiles nothing. And filing is *accountable*: a failure mid-batch closes
//! the issues this pass created, keeps the ones an earlier pass filed, and
//! reports the exact partial counters rather than a bare failure.
//!
//! Everything that leaves this process goes through [`FilingGateway`], so every
//! decision above is unit-tested against a double rather than a live clone.
//! Composition itself belongs to [`larch_core::issue`].
//!
//! Ports `larch.issue.oos_filer`.

use std::{
    collections::{BTreeMap, HashMap, HashSet},
    env,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use larch_adapters::github::{IssueMutationOwner, LiveMutationRequest};
use larch_core::{
    AcceptedBlock, AcceptedSource, FILE_CONFLICT_DEFAULT_CLUSTER_CAP,
    FILE_CONFLICT_DEFAULT_GLOBAL_CAP, FiledIssue, GitHubLabelCreate, GitHubRepositoryRef,
    GitHubService as _, IssueMutationRequest, ManifestDocument, OOS_CORRECTNESS_LABEL,
    OOS_CORRECTNESS_LABEL_COLOR, OOS_CORRECTNESS_LABEL_DESCRIPTION, ParsedItem,
    combined_block_count, dedupe_filed, ensure_ascii_json, is_capped_rollup_body,
    ndjson_filed_evidence, parse_intra_batch_deps, parse_issue_input, priority_by_combined_item,
    priority_urls, read_universal_newlines, render_blocks, render_oos_ndjson,
    render_recovery_evidence, render_sentinel, sanitize_public_text, sentinel_urls,
    split_persisted_matches, split_to_github_limit, stable_ids_by_combined_item,
    summarize_to_github_limit, topological_create_order, unsigned_integer,
    validate_issue_cap_input, working_batch, wrap_oos_body,
};
use larch_core::{ChildEnvironment, ExternalProgram, LarchProgram};

use crate::{
    argparse_compat::{missing, parse_with_flags, usage_error as argparse_usage_error},
    child_process::{bounded_request, run_bounded},
    github_repository_resolution::repository_ref,
    github_service::{ServiceFailure, with_github_service},
    issue_create_commands::{CreateSpec, create_issue},
    issue_dependency_commands::{EdgeAuthorization, apply_blocked_by, in_process_edge},
    issue_mutation_support::authorization_request,
    oos_commands::{
        FAILURE_SITE, append_failure_log, append_run_log_warning, atomic_write, cap_batch,
        checkpoint, conflict_cap, issue_cap_value, materialize, read_state, resolve_design_path,
        state_value, write_conflict_deps,
    },
    runtime_entrypoint::plugin_root_directory,
};

/// Usage line an unusable `oos file` command line is refused with.
const FILE_USAGE: &str = concat!(
    "usage: cli.py oos file [-h] --implement-tmpdir IMPLEMENT_TMPDIR [--repo REPO]\n",
    "                       [--issue-number ISSUE_NUMBER] [--codex-timeout CODEX_TIMEOUT]\n",
    "                       [--context-file CONTEXT_FILE]",
);
/// Exit code a rejected command line reports.
const VALIDATION_FAILED_RC: u8 = 2;
/// Exit code the disposition checkpoint reports for a pending security sidecar.
const SECURITY_SIDECAR_RC: u8 = 3;
/// The largest issue body GitHub accepts, in bytes.
const GITHUB_ISSUE_BODY_MAX_BYTES: usize = 65_536;
/// Directory under the session root that every published body part lands in.
const BODIES_DIR: &str = "oos-issue-bodies";
/// The composed batch every filing pass reads.
const COMBINED_FILE: &str = "oos-combined.md";
/// The run's filing sentinel.
const SENTINEL_FILE: &str = "oos-issues-created.md";
/// Marker prefix a carve-out run records instead of a live URL.
const SKIPPED_URL_PREFIX: &str = "skipped://oos/";
/// Deadline the combine launcher assumes when the caller names an unusable one.
const COMBINE_DEFAULT_TIMEOUT_SECONDS: u64 = 300;
/// Headroom over the launcher's own deadline, so it reports its own timeout.
const COMBINE_TIMEOUT_MARGIN: Duration = Duration::from_secs(60);
/// Grace the combine child gets to exit after cancellation.
const COMBINE_SHUTDOWN_GRACE: Duration = Duration::from_secs(5);
/// How many bytes of the combine child's streams are retained.
const COMBINE_OUTPUT_LIMIT: usize = 64 * 1024;

// ---------------------------------------------------------------------------
// Effect seam
// ---------------------------------------------------------------------------

/// One issue this pass asked the filing owner to create.
pub struct CreateRequest<'a> {
    /// The public issue title, already sanitized.
    pub title: &'a str,
    /// Path of the body part this issue publishes.
    pub body_file: &'a Path,
    /// Labels to request; unknown ones are dropped by the owner.
    pub labels: Vec<String>,
    /// The repository slug the issue is filed in.
    pub repo: &'a str,
}

/// One created issue, as its caller-visible identity.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct CreatedRow {
    /// The issue number, or zero when GitHub returned none.
    pub number: u64,
    /// The issue URL, or empty when GitHub returned none.
    pub url: String,
}

/// Everything `oos file` does outside this process.
///
/// The driver never touches GitHub, Codex, or the disposition gate directly, so
/// its ordering, cleanup, and accounting decisions are exercised in process.
pub trait FilingGateway {
    /// Confirm the tracking issue exists before anything is filed against it.
    fn probe_blocker(&self, repo: &str, issue_number: &str) -> Result<(), String>;
    /// File one issue.
    fn create(&self, request: &CreateRequest<'_>) -> Result<CreatedRow, String>;
    /// Record `client` as blocked by `blocker`.
    fn link_blocked_by(&self, repo: &str, client: u64, blocker: u64) -> Result<(), String>;
    /// Close one issue this pass created but could not finish wiring.
    fn close_orphan(&self, repo: &str, issue: u64);
    /// Provision the high-risk OOS label in the repository.
    fn ensure_priority_label(&self, repo: &str) -> Result<(), String>;
    /// Add the high-risk OOS label to one filed issue and prove it stuck.
    fn apply_priority_label(&self, repo: &str, url: &str) -> Result<(), String>;
    /// Report whether the Codex combine step can run at all.
    fn codex_available(&self) -> bool;
    /// Ask Codex to combine the batch, writing its answer to `output`.
    fn combine(
        &self,
        prompt: &Path,
        output: &Path,
        timeout: &str,
        tmpdir: &Path,
    ) -> Result<(), String>;
    /// Run the run's OOS disposition checkpoint and report its exit code.
    fn disposition_checkpoint(&self, tmpdir: &Path) -> u8;
}

/// The production gateway, bound to one run's live-mutation authorization.
pub struct LiveFiling {
    context_file: String,
    run_id: String,
    trusted_root: String,
}

impl LiveFiling {
    /// Resolve one repository slug, refusing an unusable one by name.
    fn repository(repo: &str) -> Result<GitHubRepositoryRef, String> {
        repository_ref(repo).map_err(|_error| format!("repository slug is invalid: {repo}"))
    }
}

/// Provision the shared high-risk OOS label through the typed GitHub service.
pub fn ensure_priority_label(repo: &str) -> Result<(), String> {
    let repository = LiveFiling::repository(repo)?;
    let request = GitHubLabelCreate {
        repo: repository.clone(),
        name: OOS_CORRECTNESS_LABEL.to_owned(),
        color: OOS_CORRECTNESS_LABEL_COLOR.to_owned(),
        description: OOS_CORRECTNESS_LABEL_DESCRIPTION.to_owned(),
    };
    match with_github_service(async |service, cancellation| {
        if service
            .list_labels(&repository, cancellation)
            .await
            .is_ok_and(|labels| labels.iter().any(|label| label.name == request.name))
        {
            return Ok(Ok(()));
        }
        Ok(service
            .create_label(&request, cancellation)
            .await
            .map(|_label| ())
            .map_err(|error| error.to_string()))
    }) {
        Ok(result) => result,
        Err(ServiceFailure::Setup(detail) | ServiceFailure::Operation(detail)) => Err(detail),
    }
}

/// Parse an exact issue URL only when it names the selected repository.
fn priority_issue_number(repository: &GitHubRepositoryRef, url: &str) -> Option<u64> {
    let mut segments = url.strip_prefix("https://github.com/")?.split('/');
    let owner = segments.next()?;
    let name = segments.next()?;
    let kind = segments.next()?;
    let number = segments.next()?;
    if segments.next().is_some()
        || !owner.eq_ignore_ascii_case(repository.owner())
        || !name.eq_ignore_ascii_case(repository.name())
        || kind != "issues"
    {
        return None;
    }
    unsigned_integer(number)
}

/// Add the shared high-risk label and verify the issue mutation by read-back.
pub fn apply_priority_label(
    repo: &str,
    url: &str,
    authorization: &LiveMutationRequest<'_>,
) -> Result<(), String> {
    let repository = LiveFiling::repository(repo)?;
    let number = priority_issue_number(&repository, url)
        .ok_or_else(|| format!("issue URL does not belong to {repo}: {url}"))?;
    match with_github_service(async |service, cancellation| {
        let owner = IssueMutationOwner::new(service);
        let snapshot = match owner.read_snapshot(&repository, number, cancellation).await {
            Ok(snapshot) => snapshot,
            Err(error) => return Ok(Err(error.to_string())),
        };
        let mut labels = snapshot.labels.clone();
        let _added = labels.insert(OOS_CORRECTNESS_LABEL.to_owned());
        Ok(owner
            .apply(
                cancellation,
                authorization,
                &IssueMutationRequest::replace_labels(&snapshot, labels),
            )
            .await
            .map(|_verified| ())
            .map_err(|error| error.to_string()))
    }) {
        Ok(result) => result,
        Err(ServiceFailure::Setup(detail) | ServiceFailure::Operation(detail)) => Err(detail),
    }
}

impl FilingGateway for LiveFiling {
    fn probe_blocker(&self, repo: &str, issue_number: &str) -> Result<(), String> {
        let repository = Self::repository(repo)?;
        let number = unsigned_integer(issue_number)
            .ok_or_else(|| format!("blocker issue is not a number: {issue_number}"))?;
        match with_github_service(async |service, cancellation| {
            Ok(service.issue(&repository, number, cancellation).await)
        }) {
            Ok(Ok(issue)) if issue.number == number => Ok(()),
            Ok(Ok(_mismatched)) => Err("blocker issue probe returned another issue".to_owned()),
            Ok(Err(error)) => Err(error.to_string()),
            Err(ServiceFailure::Setup(detail) | ServiceFailure::Operation(detail)) => Err(detail),
        }
    }

    fn create(&self, request: &CreateRequest<'_>) -> Result<CreatedRow, String> {
        create_issue(&CreateSpec {
            title: request.title,
            title_prefix: "[OOS]",
            body_file: request.body_file,
            labels: &request.labels,
            repo: request.repo,
            context_file: &self.context_file,
            run_id: &self.run_id,
            trusted_root: &self.trusted_root,
            assign_authenticated_user: false,
        })
        .map(|created| CreatedRow {
            number: created.number,
            url: created.url,
        })
    }

    fn link_blocked_by(&self, repo: &str, client: u64, blocker: u64) -> Result<(), String> {
        apply_blocked_by(&in_process_edge(
            Self::repository(repo)?,
            client,
            blocker,
            EdgeAuthorization::Session {
                context_file: &self.context_file,
                run_id: &self.run_id,
                trusted_root: &self.trusted_root,
            },
        ))
    }

    fn close_orphan(&self, repo: &str, issue: u64) {
        let Ok(repository) = Self::repository(repo) else {
            return;
        };
        let _closed = with_github_service(async |service, cancellation| {
            IssueMutationOwner::new(service)
                .close_not_planned(cancellation, &repository, issue)
                .await
        });
    }

    fn ensure_priority_label(&self, repo: &str) -> Result<(), String> {
        ensure_priority_label(repo)
    }

    fn apply_priority_label(&self, repo: &str, url: &str) -> Result<(), String> {
        let authorization =
            authorization_request(&self.context_file, &self.run_id, &self.trusted_root, false);
        apply_priority_label(repo, url, &authorization)
    }

    fn codex_available(&self) -> bool {
        for name in ["LARCH_OOS_CODEX_BINARY_FOUND", "CODEX_BINARY_FOUND"] {
            match env::var(name).unwrap_or_default().to_lowercase().as_str() {
                "true" | "1" | "yes" => return true,
                "false" | "0" | "no" => return false,
                _other => {}
            }
        }
        codex_on_path()
    }

    fn combine(
        &self,
        prompt: &Path,
        output: &Path,
        timeout: &str,
        tmpdir: &Path,
    ) -> Result<(), String> {
        // The Codex boundary stays a process boundary: `agent launch-codex-exec`
        // owns the sandbox, the deadline, and the usage accounting, and it
        // publishes its own rows, so it runs as a bounded captured child of the
        // verified executable rather than in this verb's contract stream.
        let workdir = env::current_dir().map_err(|error| error.to_string())?;
        let root = plugin_root_directory().ok_or("could not resolve the plugin root")?;
        let program = LarchProgram::binary(&root)
            .map_err(|_error| "could not resolve the larch executable")?;
        let arguments: Vec<OsString> = [
            OsString::from("agent"),
            OsString::from("launch-codex-exec"),
            OsString::from("--output"),
            output.as_os_str().to_owned(),
            OsString::from("--timeout"),
            OsString::from(timeout),
            OsString::from("--prompt-file"),
            prompt.as_os_str().to_owned(),
            OsString::from("--sandbox"),
            OsString::from("read-only"),
            OsString::from("--workdir"),
            workdir.into_os_string(),
            OsString::from("--add-dir"),
            tmpdir.as_os_str().to_owned(),
        ]
        .into_iter()
        .collect();
        let seconds = timeout.parse().unwrap_or(COMBINE_DEFAULT_TIMEOUT_SECONDS);
        let request = bounded_request(
            ExternalProgram::Larch(program),
            arguments,
            Duration::from_secs(seconds).saturating_add(COMBINE_TIMEOUT_MARGIN),
            COMBINE_SHUTDOWN_GRACE,
            COMBINE_OUTPUT_LIMIT,
        )
        .map(|request| {
            request.with_environment(ChildEnvironment::ClaudePluginRoot, root.into_os_string())
        })?;
        let output = run_bounded(request)?;
        if output.status().code() == Some(0) {
            Ok(())
        } else {
            Err("codex combine launcher failed".to_owned())
        }
    }

    fn disposition_checkpoint(&self, tmpdir: &Path) -> u8 {
        checkpoint(tmpdir, None)
    }
}

/// Report whether a `codex` executable is reachable on `PATH`.
fn codex_on_path() -> bool {
    let Ok(path) = env::var("PATH") else {
        return false;
    };
    env::split_paths(&path).any(|directory| {
        let candidate = directory.join("codex");
        candidate.metadata().is_ok_and(|data| data.is_file())
    })
}

// ---------------------------------------------------------------------------
// Result payload
// ---------------------------------------------------------------------------

/// The one JSON object `oos file` publishes, in its documented field order.
#[derive(Debug, Default)]
struct Payload {
    status: String,
    reason: Option<String>,
    failure_mode: Option<String>,
    accepted_count: usize,
    filed_count: usize,
    deduplicated_count: usize,
    urls: Vec<String>,
    run_statistics_written: bool,
    step9a1_stamped: bool,
}

impl Payload {
    /// Build one payload from the run's filed records.
    fn from_filed(status: &str, accepted_count: usize, filed: &[FiledIssue]) -> Self {
        Self {
            status: status.to_owned(),
            accepted_count,
            filed_count: filed.len(),
            deduplicated_count: filed.iter().filter(|issue| issue.duplicate).count(),
            urls: filed.iter().map(|issue| issue.url.clone()).collect(),
            ..Self::default()
        }
    }

    /// Render the payload as one line of JSON.
    fn render(&self) -> String {
        let mut fields: Vec<String> = vec![field("status", &json_string(&self.status))];
        if let Some(reason) = &self.reason {
            fields.push(field("reason", &json_string(reason)));
        }
        if let Some(mode) = &self.failure_mode {
            fields.push(field("failure_mode", &json_string(mode)));
        }
        fields.push(field("accepted_count", &self.accepted_count.to_string()));
        fields.push(field("filed_count", &self.filed_count.to_string()));
        fields.push(field(
            "deduplicated_count",
            &self.deduplicated_count.to_string(),
        ));
        let urls: Vec<String> = self.urls.iter().map(|url| json_string(url)).collect();
        fields.push(field("urls", &format!("[{}]", urls.join(","))));
        fields.push(field(
            "run_statistics_written",
            &self.run_statistics_written.to_string(),
        ));
        fields.push(field("step9a1_stamped", &self.step9a1_stamped.to_string()));
        ensure_ascii_json(&format!("{{{}}}", fields.join(",")))
    }
}

/// Render one `"key":value` JSON member.
fn field(key: &str, value: &str) -> String {
    format!("\"{key}\":{value}")
}

/// Render one JSON string literal.
fn json_string(value: &str) -> String {
    serde_json::Value::String(value.to_owned()).to_string()
}

// ---------------------------------------------------------------------------
// Command entry
// ---------------------------------------------------------------------------

/// Run `oos file`.
pub fn file(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &[
            "--implement-tmpdir",
            "--repo",
            "--issue-number",
            "--codex-timeout",
            "--context-file",
        ],
        &[],
        0,
    );
    if let Some(error) = parsed.error() {
        return argparse_usage_error(FILE_USAGE, "cli.py oos file", &error, VALIDATION_FAILED_RC);
    }
    let Some(tmpdir) = parsed.value("--implement-tmpdir") else {
        return argparse_usage_error(
            FILE_USAGE,
            "cli.py oos file",
            &missing(&[("--implement-tmpdir", false)]),
            VALIDATION_FAILED_RC,
        );
    };
    let tmpdir = PathBuf::from(tmpdir.to_owned());
    let text = |option: &str| -> String {
        parsed
            .value(option)
            .map(|value| value.to_string_lossy().into_owned())
            .unwrap_or_default()
    };
    let codex_timeout = text("--codex-timeout");
    let request = FileRequest {
        repo: text("--repo"),
        issue_number: text("--issue-number"),
        codex_timeout: if codex_timeout.is_empty() {
            "300".to_owned()
        } else {
            codex_timeout
        },
        context_file: text("--context-file"),
    };
    let state = read_state(&tmpdir.join("ship-pr-state.sh"));
    let run_id = run_id(&tmpdir, &state);
    let context_file = if request.context_file.is_empty() {
        tmpdir.join("session-env.sh").to_string_lossy().into_owned()
    } else {
        request.context_file.clone()
    };
    let trusted_root = tmpdir.to_string_lossy().into_owned();
    let gateway = LiveFiling {
        context_file: context_file.clone(),
        run_id: run_id.clone(),
        trusted_root: trusted_root.clone(),
    };
    let authorization = authorization_request(&context_file, &run_id, &trusted_root, false);
    if let Err(reason) = crate::issue_mutation_support::authorized(&authorization) {
        return publish(
            1,
            &Payload {
                status: "authorization-refused".to_owned(),
                reason: Some(reason.to_owned()),
                ..Payload::default()
            },
        );
    }
    let run = Session {
        tmpdir,
        run_id,
        state,
        request,
    };
    let (code, payload) = drive(&run, &gateway);
    publish(code, &payload)
}

/// Publish the payload and report the process exit code.
fn publish(code: u8, payload: &Payload) -> ExitCode {
    println!("{}", payload.render());
    ExitCode::from(code)
}

/// One usable `oos file` command line.
struct FileRequest {
    repo: String,
    issue_number: String,
    codex_timeout: String,
    context_file: String,
}

/// Everything one filing pass resolved before it decided anything.
struct Session {
    tmpdir: PathBuf,
    run_id: String,
    state: Vec<(String, String)>,
    request: FileRequest,
}

impl Session {
    /// The repository slug this run files into.
    fn repo(&self) -> String {
        if self.request.repo.is_empty() {
            state_value(&self.state, "REPO")
        } else {
            self.request.repo.clone()
        }
    }

    /// The tracking issue every filed issue is recorded as blocked by.
    fn issue_number(&self) -> String {
        if self.request.issue_number.is_empty() {
            state_value(&self.state, "ISSUE_NUMBER")
        } else {
            self.request.issue_number.clone()
        }
    }

    /// Whether this run may not file public issues at all.
    fn carve_out(&self) -> Option<&'static str> {
        if state_value(&self.state, "REPO_UNAVAILABLE") == "true" {
            Some("Skipped — repo unavailable")
        } else if state_value(&self.state, "FORKED_TARGET") == "true" {
            Some("Skipped — forked target")
        } else {
            None
        }
    }

    /// The run's log directory, where the batch and statistics land.
    fn run_dir(&self) -> PathBuf {
        self.tmpdir
            .join("larch-logs")
            .join("implement")
            .join(&self.run_id)
    }

    /// Record one tool failure in the run's problem ledger.
    fn fail(&self, tool: &str, rc: i32, output: &str) {
        append_failure_log(
            &self.tmpdir.join("execution-issues.md"),
            FAILURE_SITE,
            tool,
            rc,
            output,
        );
    }

    /// Record one filing warning in the run's problem ledger.
    fn warn(&self, message: &str) {
        append_run_log_warning(&self.tmpdir, &format!("- **oos file**: {message}"));
    }
}

/// Resolve the run id the way the filer always has.
fn run_id(tmpdir: &Path, state: &[(String, String)]) -> String {
    let recorded = state_value(state, "RUN_ID");
    if !recorded.is_empty() {
        return recorded;
    }
    read_universal_newlines(&tmpdir.join("session-id"))
        .map(|text| text.trim().to_owned())
        .filter(|text| !text.is_empty())
        .unwrap_or_else(|| "unknown".to_owned())
}

// ---------------------------------------------------------------------------
// The filing pass
// ---------------------------------------------------------------------------

/// The accepted-OOS artifacts one run reads, in the order it reads them.
fn accepted_input_paths(tmpdir: &Path) -> Vec<PathBuf> {
    let design_tmpdir = env::var("DESIGN_TMPDIR").ok().map(PathBuf::from);
    vec![
        tmpdir.join("oos-accepted-main-agent.md"),
        resolve_design_path(tmpdir, design_tmpdir.as_deref()),
        tmpdir.join("oos-accepted-review.md"),
    ]
}

/// Read the run's accepted-OOS artifacts into pending blocks and filed URLs.
fn read_working_batch(tmpdir: &Path) -> (Vec<AcceptedBlock>, Vec<FiledIssue>) {
    let mut stems: Vec<String> = Vec::new();
    let mut texts: Vec<String> = Vec::new();
    for path in accepted_input_paths(tmpdir) {
        if !path.is_file() {
            continue;
        }
        let Some(text) = read_universal_newlines(&path) else {
            continue;
        };
        stems.push(
            path.file_stem()
                .map(|stem| stem.to_string_lossy().into_owned())
                .unwrap_or_default(),
        );
        texts.push(text);
    }
    let sources: Vec<AcceptedSource<'_>> = stems
        .iter()
        .zip(texts.iter())
        .map(|(source_key, text)| AcceptedSource {
            source_key,
            text: text.as_str(),
        })
        .collect();
    working_batch(&sources)
}

/// Recover every filed issue the run's durable records already carry.
fn persisted_filed_evidence(run: &Session) -> Vec<FiledIssue> {
    let mut filed = read_universal_newlines(&run.tmpdir.join(SENTINEL_FILE))
        .map(|text| sentinel_urls(&text))
        .unwrap_or_default();
    filed.extend(
        read_universal_newlines(&run.run_dir().join("oos-issues.ndjson"))
            .map(|text| ndjson_filed_evidence(&text))
            .unwrap_or_default(),
    );
    dedupe_filed(filed)
}

/// Write the synthetic accepted-OOS artifact recovered evidence binds to.
fn materialize_recovery_evidence(tmpdir: &Path, filed: &[FiledIssue]) {
    if accepted_input_paths(tmpdir)
        .iter()
        .any(|path| path.is_file())
    {
        return;
    }
    let _written = fs::write(
        tmpdir.join("oos-accepted-main-agent.md"),
        render_recovery_evidence(filed),
    );
}

/// What one filing pass decided about the batch before it filed anything.
struct Recovered {
    pending: Vec<AcceptedBlock>,
    all_blocks: Vec<AcceptedBlock>,
    persisted: Vec<FiledIssue>,
    already: Vec<FiledIssue>,
}

/// Bind durable evidence to the pending batch, re-reading a recovered session.
fn recover_persisted_blocks(
    run: &Session,
    all_blocks: Vec<AcceptedBlock>,
    already: Vec<FiledIssue>,
) -> Recovered {
    let persisted = persisted_filed_evidence(run);
    let (pending, matched) = split_persisted_matches(&all_blocks, &persisted);
    let mut already = dedupe_filed([already, matched].concat());
    if persisted.is_empty()
        || accepted_input_paths(&run.tmpdir)
            .iter()
            .any(|path| path.is_file())
    {
        return Recovered {
            pending,
            all_blocks,
            persisted,
            already,
        };
    }
    materialize_recovery_evidence(
        &run.tmpdir,
        &dedupe_filed([persisted.clone(), already.clone()].concat()),
    );
    let (all_blocks, recovery_already) = read_working_batch(&run.tmpdir);
    let (pending, matched_recovery) = split_persisted_matches(&all_blocks, &persisted);
    already = dedupe_filed([already, recovery_already, matched_recovery].concat());
    Recovered {
        pending,
        all_blocks,
        persisted,
        already,
    }
}

/// Drive one filing pass end to end.
fn drive(run: &Session, gateway: &dyn FilingGateway) -> (u8, Payload) {
    let manifest_path = state_value(&run.state, "MANIFEST_PATH");
    if !manifest_path.is_empty()
        && Path::new(&manifest_path).is_file()
        && let Err(error) = materialize(Path::new(&manifest_path), &run.tmpdir, false)
    {
        run.warn(&format!("manifest OOS materialization failed: {error}"));
    }
    let (all_blocks, already) = read_working_batch(&run.tmpdir);
    let accepted_count = all_blocks.len() + already.len();
    let recovered = recover_persisted_blocks(run, all_blocks, already);
    let combined_path = run.tmpdir.join(COMBINED_FILE);
    let combined_text = read_universal_newlines(&combined_path);
    let stable_ids = combined_text
        .as_ref()
        .map(|text| stable_ids_by_combined_item(&recovered.all_blocks, text))
        .unwrap_or_default();

    let repo = run.repo();
    let carve_out = run.carve_out();
    if (!recovered.persisted.is_empty() || !recovered.already.is_empty()) && carve_out.is_none() {
        let filed = dedupe_filed([recovered.persisted.clone(), recovered.already.clone()].concat());
        if !backfill_priority_labels(
            run,
            gateway,
            &repo,
            &filed,
            &recovered.all_blocks,
            combined_text.as_deref(),
            &stable_ids,
        ) {
            return (
                1,
                Payload::from_filed("priority_label_backfill_failed", accepted_count, &filed),
            );
        }
    }

    if !recovered.persisted.is_empty()
        && recovered.pending.is_empty()
        && recovered.already.is_empty()
    {
        let filed = recovered.persisted;
        materialize_recovery_evidence(&run.tmpdir, &filed);
        write_oos_ndjson(run, &filed, "Recovered from sentinel");
        return after_checkpoint(
            run,
            gateway,
            &filed,
            "idempotent",
            accepted_count.max(filed.len()),
            None,
            true,
        );
    }

    if recovered.pending.is_empty() {
        let filed = if recovered.persisted.is_empty() {
            recovered.already
        } else {
            dedupe_filed([recovered.persisted, recovered.already].concat())
        };
        let status = if filed.is_empty() {
            "empty"
        } else {
            "already_filed"
        };
        if !filed.is_empty() {
            write_oos_ndjson(run, &filed, "Already filed");
        }
        return after_checkpoint(run, gateway, &filed, status, accepted_count, None, true);
    }

    if let Some(status) = carve_out {
        let filed: Vec<FiledIssue> = recovered
            .pending
            .iter()
            .enumerate()
            .map(|(offset, block)| FiledIssue {
                title: block.title.clone(),
                url: format!("{SKIPPED_URL_PREFIX}{}", offset + 1),
                stable_id: block.stable_id.clone(),
                ..FiledIssue::default()
            })
            .collect();
        write_oos_ndjson(run, &filed, status);
        return after_checkpoint(
            run,
            gateway,
            &filed,
            "skipped",
            accepted_count,
            Some(0),
            true,
        );
    }

    file_batch(run, gateway, &repo, &recovered, accepted_count)
}

/// Compose, cap, order, and file the pending batch.
fn file_batch(
    run: &Session,
    gateway: &dyn FilingGateway,
    repo: &str,
    recovered: &Recovered,
    accepted_count: usize,
) -> (u8, Payload) {
    let rendered = render_blocks(&recovered.pending);
    let combined_text = maybe_combine_with_codex(run, gateway, &rendered);
    let combined = run.tmpdir.join(COMBINED_FILE);
    if let Err(error) = atomic_write(&combined, &combined_text) {
        run.fail("oos file", 1, &error);
        return (
            1,
            Payload::from_filed("issue_cap_failed", accepted_count, &[]),
        );
    }
    if let Err(error) = enforce_issue_cap(&combined) {
        run.fail("oos issue-cap", 1, &error);
        return (
            1,
            Payload::from_filed("issue_cap_failed", accepted_count, &[]),
        );
    }
    let deps_path = plan_intra_batch_deps(run, &combined);

    // The cap may have rewritten the batch in place, rolling surplus blocks
    // into one aggregate, so identity is mapped from the post-cap file the
    // batch actually files.
    let post_cap_text = read_universal_newlines(&combined).unwrap_or_default();
    let stable_ids = stable_ids_by_combined_item(&recovered.pending, &post_cap_text);
    let priority = priority_by_combined_item(&recovered.pending, &post_cap_text, &stable_ids);

    let batch = run_issue_batch(
        run,
        gateway,
        &BatchInputs {
            repo,
            issue_number: &run.issue_number(),
            combined: &combined,
            deps: deps_path.as_deref(),
            stable_ids: &stable_ids,
            priority: &priority,
        },
    );
    if batch.failures > 0 {
        return report_batch_failure(run, recovered, &batch, accepted_count);
    }
    let filed = dedupe_filed(
        [
            recovered.persisted.clone(),
            recovered.already.clone(),
            batch.filed,
        ]
        .concat(),
    );
    write_sentinel(run, &filed);
    write_oos_ndjson(run, &filed, "Filed");
    after_checkpoint(run, gateway, &filed, "filed", accepted_count, None, true)
}

/// Report one failed batch, preserving whatever it did file.
fn report_batch_failure(
    run: &Session,
    recovered: &Recovered,
    batch: &BatchResult,
    accepted_count: usize,
) -> (u8, Payload) {
    run.fail(
        "issue create-one",
        1,
        &format!("ISSUES_FAILED={}", batch.failures),
    );
    let rolled_up_aggregate = batch.failure_mode == FailureMode::HardCreate
        && batch.filed.len() == 1
        && batch.filed[0].source_stable_ids.len() > 1;
    let partial_priority = matches!(
        batch.failure_mode,
        FailureMode::PriorityLabel | FailureMode::PriorityProvision
    ) && !batch.filed.is_empty();
    if rolled_up_aggregate || partial_priority {
        let filed = dedupe_filed(
            [
                recovered.persisted.clone(),
                recovered.already.clone(),
                batch.filed.clone(),
            ]
            .concat(),
        );
        let status = if rolled_up_aggregate {
            "hard_create_partial_failure".to_owned()
        } else {
            format!("{}_partial_failure", batch.failure_mode.as_str())
        };
        write_sentinel(run, &filed);
        write_oos_ndjson(
            run,
            &filed,
            if rolled_up_aggregate {
                "Hard-create partial failure"
            } else {
                "Priority label partial failure"
            },
        );
        return (1, Payload::from_filed(&status, accepted_count, &filed));
    }
    let mut payload = Payload::from_filed("issue_batch_failed", accepted_count, &batch.filed);
    payload.failure_mode = Some(batch.failure_mode.as_str().to_owned());
    (1, payload)
}

/// Apply the per-run issue cap to the composed batch, in place.
fn enforce_issue_cap(combined: &Path) -> Result<(), String> {
    cap_batch(combined, None, issue_cap_value()?)
}

/// Plan the intra-batch serialization edges, degrading loudly when it cannot.
fn plan_intra_batch_deps(run: &Session, combined: &Path) -> Option<PathBuf> {
    let deps = run.tmpdir.join("oos-intra-batch-deps.tsv");
    let caps = conflict_cap(
        "OOS_FILE_CONFLICT_CLUSTER_CAP",
        FILE_CONFLICT_DEFAULT_CLUSTER_CAP,
    )
    .and_then(|cluster| {
        conflict_cap(
            "OOS_FILE_CONFLICT_GLOBAL_CAP",
            FILE_CONFLICT_DEFAULT_GLOBAL_CAP,
        )
        .map(|global| (cluster, global))
    });
    // The caps refuse at the verb's own validation code, which never removed a
    // caller's file; only a failed plan or write does.
    let (rc, error) = match caps {
        Err(message) => (VALIDATION_FAILED_RC, message),
        Ok((cluster_cap, global_cap)) => {
            match write_conflict_deps(combined, &deps, cluster_cap, global_cap) {
                Ok(()) => {
                    return deps
                        .metadata()
                        .is_ok_and(|data| data.len() > 0)
                        .then_some(deps);
                }
                Err(message) => (1, message),
            }
        }
    };
    let warning = format!(
        "**⚠ /implement: oos-file-conflict pre-pass failed (exit {rc}) — \
         proceeding without caller-supplied serialization edges; review accepted-OOS Descriptions \
         before greenlighting parallel workers**"
    );
    run.warn(&warning);
    run.fail(
        "oos file-conflict-deps",
        i32::from(rc),
        if error.is_empty() { &warning } else { &error },
    );
    if rc == 1 {
        let _removed = fs::remove_file(&deps);
    }
    None
}

/// Ask Codex to combine the batch, keeping the original on any refusal.
fn maybe_combine_with_codex(run: &Session, gateway: &dyn FilingGateway, text: &str) -> String {
    let original_count = combined_block_count(text);
    if original_count <= 1 {
        return text.to_owned();
    }
    let input_path = run.tmpdir.join("oos-combine-input.md");
    let output_path = run.tmpdir.join("oos-combine-codex-output.md");
    let prompt_path = run.tmpdir.join("oos-combine-prompt.md");
    if fs::write(&input_path, text).is_err() {
        return text.to_owned();
    }
    let prompt = format!(
        "Aggressively combine accepted out-of-scope observations unless they are clearly unrelated.\n\
         Return only valid markdown blocks shaped as `### OOS_N:` items.\n\
         Preserve actionable details and do not increase the item count.\n\n\
         Input file: {input}\n\n\
         ## Batch markdown\n\n\
         {batch}\n",
        input = input_path.display(),
        batch = text.trim_end(),
    );
    if fs::write(&prompt_path, prompt).is_err() {
        return text.to_owned();
    }
    if !gateway.codex_available() {
        run.warn("Codex unavailable; filing the pre-combine OOS batch.");
        return text.to_owned();
    }
    if gateway
        .combine(
            &prompt_path,
            &output_path,
            &run.request.codex_timeout,
            &run.tmpdir,
        )
        .is_err()
        || !output_path.is_file()
    {
        run.warn("Codex combine failed; filing the pre-combine OOS batch.");
        return text.to_owned();
    }
    let combined = read_universal_newlines(&output_path).unwrap_or_default();
    if !valid_combined_output(&combined, original_count) {
        run.warn("Codex combine output was invalid; filing the pre-combine OOS batch.");
        return text.to_owned();
    }
    combined
}

/// Report whether Codex returned a usable, non-expanding batch.
fn valid_combined_output(text: &str, original_count: usize) -> bool {
    if text.trim().is_empty() || validate_issue_cap_input(text).is_err() {
        return false;
    }
    let count = combined_block_count(text);
    count > 0 && count <= original_count
}

// ---------------------------------------------------------------------------
// The per-item filing loop
// ---------------------------------------------------------------------------

/// Why one batch stopped short of filing everything it was given.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
enum FailureMode {
    #[default]
    None,
    HardCreate,
    PriorityLabel,
    PriorityProvision,
}

impl FailureMode {
    /// Render the token the payload reports.
    const fn as_str(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::HardCreate => "hard_create",
            Self::PriorityLabel => "priority_label",
            Self::PriorityProvision => "priority_provision",
        }
    }
}

/// What one batch filed and how it ended.
struct BatchResult {
    filed: Vec<FiledIssue>,
    failures: usize,
    failure_mode: FailureMode,
}

/// Everything the batch loop needs that the run itself does not carry.
struct BatchInputs<'a> {
    repo: &'a str,
    issue_number: &'a str,
    combined: &'a Path,
    deps: Option<&'a Path>,
    stable_ids: &'a BTreeMap<usize, Vec<String>>,
    priority: &'a HashSet<usize>,
}

/// File the composed batch, one item at a time, in dependency order.
fn run_issue_batch(
    run: &Session,
    gateway: &dyn FilingGateway,
    inputs: &BatchInputs<'_>,
) -> BatchResult {
    let bodies_dir = run.tmpdir.join(BODIES_DIR);
    let _created = fs::create_dir_all(&bodies_dir);
    let combined_text = read_universal_newlines(inputs.combined).unwrap_or_default();
    let sanitized = sanitize_public_text(&combined_text);
    if let Err(error) = atomic_write(&bodies_dir.join("oos-combined-sanitized.md"), &sanitized) {
        run.fail("issue parse-input", 1, &error);
        return BatchResult {
            filed: Vec::new(),
            failures: 1,
            failure_mode: FailureMode::HardCreate,
        };
    }
    let items = parse_issue_input(&sanitized).items;
    if let Err(error) = probe_blocker(gateway, inputs) {
        let tool = if inputs.repo.is_empty() {
            "blocker probe"
        } else {
            "gh api blocker probe"
        };
        run.fail(tool, 1, &error);
        return BatchResult {
            filed: Vec::new(),
            failures: 1,
            failure_mode: FailureMode::HardCreate,
        };
    }
    let edges = inputs
        .deps
        .and_then(read_universal_newlines)
        .map(|text| parse_intra_batch_deps(&text))
        .unwrap_or_default();
    let mut state = BatchState {
        filed: Vec::new(),
        failures: 0,
        failure_mode: FailureMode::None,
        priority_label_ready: None,
        issue_numbers: HashMap::new(),
    };
    for item_index in topological_create_order(items.len(), &edges) {
        let Some(item) = items.get(item_index - 1) else {
            continue;
        };
        match file_one_item(run, gateway, inputs, &mut state, item_index, item) {
            ItemOutcome::Continue => {}
            ItemOutcome::Abort => {
                return BatchResult {
                    filed: state.filed,
                    failures: state.failures.max(1),
                    failure_mode: FailureMode::HardCreate,
                };
            }
        }
        let item_edges: Vec<(usize, usize)> = edges
            .iter()
            .copied()
            .filter(|(_blocker, blocked)| *blocked == item_index)
            .collect();
        if !apply_intra_batch_edges(run, gateway, inputs.repo, &item_edges, &state) {
            return BatchResult {
                filed: state.filed,
                failures: 1,
                failure_mode: FailureMode::HardCreate,
            };
        }
    }
    BatchResult {
        filed: state.filed,
        failures: state.failures,
        failure_mode: state.failure_mode,
    }
}

/// Confirm the tracking issue exists, treating a non-numeric one as absent.
fn probe_blocker(gateway: &dyn FilingGateway, inputs: &BatchInputs<'_>) -> Result<(), String> {
    if unsigned_integer(inputs.issue_number).is_none() {
        return Ok(());
    }
    if inputs.repo.is_empty() {
        return Err("missing repo for --blocked-by-issue probe".to_owned());
    }
    gateway.probe_blocker(inputs.repo, inputs.issue_number)
}

/// Mutable state one batch carries across its items.
struct BatchState {
    filed: Vec<FiledIssue>,
    failures: usize,
    failure_mode: FailureMode,
    priority_label_ready: Option<bool>,
    issue_numbers: HashMap<usize, u64>,
}

/// Whether the batch loop may continue after one item.
enum ItemOutcome {
    Continue,
    Abort,
}

/// File every body part of one composed item.
fn file_one_item(
    run: &Session,
    gateway: &dyn FilingGateway,
    inputs: &BatchInputs<'_>,
    state: &mut BatchState,
    item_index: usize,
    item: &ParsedItem,
) -> ItemOutcome {
    let title = sanitize_public_text(&item.title).trim().to_owned();
    // Never publish an empty public issue: a malformed item has no usable
    // Description, and filing it would create an issue with a blank body.
    if item.malformed {
        let named = if title.is_empty() {
            format!("item {item_index}")
        } else {
            title
        };
        run.fail(
            "issue create-one",
            1,
            &format!(
                "skipped malformed accepted-OOS item (empty/unparseable Description); not filing empty public issue: {named}"
            ),
        );
        return ItemOutcome::Continue;
    }
    let item_priority = inputs.priority.contains(&item_index);
    if item_priority && state.priority_label_ready.is_none() {
        state.priority_label_ready = Some(match gateway.ensure_priority_label(inputs.repo) {
            Ok(()) => true,
            Err(error) => {
                run.fail("gh label create", 1, &error);
                false
            }
        });
    }
    if item_priority && state.priority_label_ready == Some(false) {
        state.failures += 1;
        state.failure_mode = FailureMode::PriorityProvision;
        return ItemOutcome::Continue;
    }
    let body_files = body_files_for_item(run, item_index, item);
    let source_ids = inputs
        .stable_ids
        .get(&item_index)
        .cloned()
        .unwrap_or_default();
    let primary_stable = source_ids
        .first()
        .cloned()
        .unwrap_or_else(|| format!("OOS_{item_index}"));
    file_body_parts(
        run,
        gateway,
        inputs,
        state,
        &BodyParts {
            item_index,
            title: &title,
            item_priority,
            body_files: &body_files,
            source_ids: &source_ids,
            primary_stable: &primary_stable,
        },
    )
}

/// One item's published parts, as the filing loop reads them.
struct BodyParts<'a> {
    item_index: usize,
    title: &'a str,
    item_priority: bool,
    body_files: &'a [PathBuf],
    source_ids: &'a [String],
    primary_stable: &'a str,
}

/// File every body part of one item, stopping at the first refusal.
fn file_body_parts(
    run: &Session,
    gateway: &dyn FilingGateway,
    inputs: &BatchInputs<'_>,
    state: &mut BatchState,
    parts: &BodyParts<'_>,
) -> ItemOutcome {
    let BodyParts {
        item_index,
        title,
        item_priority,
        body_files,
        source_ids,
        primary_stable,
    } = *parts;
    let total_parts = body_files.len();
    for (offset, body_file) in body_files.iter().enumerate() {
        let part_index = offset + 1;
        let part_title = if total_parts == 1 {
            title.to_owned()
        } else {
            format!("{title} (part {part_index}/{total_parts})")
        };
        let created = match gateway.create(&CreateRequest {
            title: &part_title,
            body_file,
            labels: if item_priority {
                vec![OOS_CORRECTNESS_LABEL.to_owned()]
            } else {
                Vec::new()
            },
            repo: inputs.repo,
        }) {
            Ok(created) => created,
            Err(_error) => {
                state.failures += 1;
                cleanup_created_issues(gateway, inputs.repo, &state.filed);
                return ItemOutcome::Abort;
            }
        };
        if !created.url.is_empty() {
            let part_stable = if part_index == 1 {
                primary_stable.to_owned()
            } else {
                format!("{primary_stable}:part{part_index}")
            };
            let filed_issue = FiledIssue {
                title: part_title,
                url: created.url.clone(),
                duplicate: false,
                stable_id: part_stable,
                source_stable_ids: if part_index == 1 {
                    source_ids.to_vec()
                } else {
                    Vec::new()
                },
                priority: item_priority,
            };
            if item_priority
                && let Err(error) = gateway.apply_priority_label(inputs.repo, &created.url)
            {
                run.fail("gh issue edit", 1, &error);
                state.failures += 1;
                state.failure_mode = FailureMode::PriorityLabel;
                // The issue exists but is unlabelled: a record recovered from a
                // prior pass is kept, while one this pass created is retracted.
                if filed_issue.duplicate {
                    state.filed.push(filed_issue);
                } else {
                    cleanup_created_issues(
                        gateway,
                        inputs.repo,
                        std::slice::from_ref(&filed_issue),
                    );
                }
                break;
            }
            state.filed.push(filed_issue);
        }
        if part_index == 1 && created.number != 0 {
            let _recorded = state.issue_numbers.insert(item_index, created.number);
        }
        if created.number != 0
            && let Some(blocker) = unsigned_integer(inputs.issue_number)
            && let Err(error) = gateway.link_blocked_by(inputs.repo, created.number, blocker)
        {
            run.fail("issue add-blocked-by", 1, &error);
            cleanup_created_issues(gateway, inputs.repo, &state.filed);
            state.failures = 1;
            return ItemOutcome::Abort;
        }
    }
    ItemOutcome::Continue
}

/// Wire the serialization edges whose blocked item was just filed.
fn apply_intra_batch_edges(
    run: &Session,
    gateway: &dyn FilingGateway,
    repo: &str,
    edges: &[(usize, usize)],
    state: &BatchState,
) -> bool {
    for (blocker_index, blocked_index) in edges {
        let (Some(&upstream), Some(&dependent)) = (
            state.issue_numbers.get(blocker_index),
            state.issue_numbers.get(blocked_index),
        ) else {
            continue;
        };
        if let Err(error) = gateway.link_blocked_by(repo, dependent, upstream) {
            run.fail("issue add-blocked-by", 1, &error);
            cleanup_created_issues(gateway, repo, &state.filed);
            return false;
        }
    }
    true
}

/// Close the issues this pass created, leaving recovered ones alone.
fn cleanup_created_issues(gateway: &dyn FilingGateway, repo: &str, filed: &[FiledIssue]) {
    for issue in filed {
        if issue.url.starts_with(SKIPPED_URL_PREFIX) || issue.duplicate {
            continue;
        }
        let Some(number) = issue.url.rsplit('/').next().and_then(unsigned_integer) else {
            continue;
        };
        gateway.close_orphan(repo, number);
    }
}

/// Write every body part one item publishes and return their paths.
fn body_files_for_item(run: &Session, item_index: usize, item: &ParsedItem) -> Vec<PathBuf> {
    let mut body = sanitize_public_text(&item.body);
    let reviewer = sanitize_public_text(&item.reviewer);
    let phase = sanitize_public_text(if item.phase.is_empty() {
        "implement"
    } else {
        &item.phase
    });
    let vote = sanitize_public_text(if item.vote.is_empty() {
        "N/A"
    } else {
        &item.vote
    });
    if !reviewer.is_empty() || !phase.is_empty() || !vote.is_empty() {
        body = wrap_oos_body(&body, &reviewer, &phase, &vote);
    }
    let out_dir = run.tmpdir.join(BODIES_DIR);
    let _created = fs::create_dir_all(&out_dir);
    // A capped rollup, and every item in a one-issue run, is summarized rather
    // than split: those bodies are already an aggregate, and splitting them
    // would file the follow-up issues the cap exists to prevent.
    if env::var("OOS_ISSUES_PER_RUN_CAP").as_deref() == Ok("1") || is_capped_rollup_body(&body) {
        let out = out_dir.join(format!("oos-body-{item_index}-part1.txt"));
        let _written = fs::write(
            &out,
            summarize_to_github_limit(&body, GITHUB_ISSUE_BODY_MAX_BYTES),
        );
        return vec![out];
    }
    split_to_github_limit(&body, GITHUB_ISSUE_BODY_MAX_BYTES)
        .into_iter()
        .enumerate()
        .map(|(offset, part)| {
            let out = out_dir.join(format!("oos-body-{item_index}-part{}.txt", offset + 1));
            let _written = fs::write(&out, part);
            out
        })
        .collect()
}

// ---------------------------------------------------------------------------
// Durable records and the disposition checkpoint
// ---------------------------------------------------------------------------

/// Write the run's filing sentinel.
fn write_sentinel(run: &Session, filed: &[FiledIssue]) {
    let _written = atomic_write(&run.tmpdir.join(SENTINEL_FILE), &render_sentinel(filed));
}

/// Write the run-log OOS batch.
fn write_oos_ndjson(run: &Session, filed: &[FiledIssue], status: &str) {
    let run_dir = run.run_dir();
    let _created = fs::create_dir_all(&run_dir);
    let _written = fs::write(
        run_dir.join("oos-issues.ndjson"),
        render_oos_ndjson(filed, status),
    );
}

/// Write the run statistics line and report whether it landed.
fn write_run_statistics(run: &Session, filed_count: usize) -> bool {
    let run_dir = run.run_dir();
    let _created = fs::create_dir_all(&run_dir);
    let path = run_dir.join("run-statistics.md");
    fs::write(
        &path,
        format!("Run {}: {filed_count} OOS issue(s) filed.\n", run.run_id),
    )
    .is_ok()
        && path.is_file()
}

/// Stamp `steps_ran.step9a1` on the run manifest, if there is one.
fn stamp_manifest(run: &Session, value: bool) -> bool {
    let path = run.run_dir().join("manifest.json");
    if !path.is_file() {
        return false;
    }
    let Ok(bytes) = fs::read(&path) else {
        return false;
    };
    let Ok(mut document) = ManifestDocument::from_bytes(&bytes) else {
        return false;
    };
    let updates = vec![(
        "steps_ran.step9a1".to_owned(),
        serde_json::Value::Bool(value),
    )];
    if document
        .apply_updates(&updates, chrono::Utc::now().to_rfc3339())
        .is_err()
    {
        return false;
    }
    atomic_write(&path, &format!("{}\n", document.canonical_json())).is_ok()
}

/// Run the disposition checkpoint and record what this pass produced.
fn after_checkpoint(
    run: &Session,
    gateway: &dyn FilingGateway,
    filed: &[FiledIssue],
    status: &str,
    accepted_count: usize,
    filed_count: Option<usize>,
    stamp_value: bool,
) -> (u8, Payload) {
    let code = gateway.disposition_checkpoint(&run.tmpdir);
    let reported = filed_count.unwrap_or(filed.len());
    let mut payload = Payload::from_filed(status, accepted_count, filed);
    payload.filed_count = reported;
    if code == SECURITY_SIDECAR_RC {
        "security_sidecar_present".clone_into(&mut payload.status);
        payload.run_statistics_written = !filed.is_empty() && write_run_statistics(run, reported);
        let _stamped = stamp_manifest(run, false);
        return (SECURITY_SIDECAR_RC, payload);
    }
    if code != 0 {
        "disposition_checkpoint_failed".clone_into(&mut payload.status);
        payload.step9a1_stamped = stamp_manifest(run, false);
        return (if code == 0 { 1 } else { code }, payload);
    }
    payload.run_statistics_written = write_run_statistics(run, reported);
    payload.step9a1_stamped = stamp_manifest(run, stamp_value);
    (0, payload)
}

/// Re-apply the high-risk OOS label to issues an earlier pass filed.
fn backfill_priority_labels(
    run: &Session,
    gateway: &dyn FilingGateway,
    repo: &str,
    filed: &[FiledIssue],
    blocks: &[AcceptedBlock],
    combined_text: Option<&str>,
    stable_ids: &BTreeMap<usize, Vec<String>>,
) -> bool {
    if filed.is_empty() {
        return true;
    }
    let urls = priority_urls(filed, blocks, combined_text, stable_ids);
    if urls.is_empty() {
        return true;
    }
    if let Err(error) = gateway.ensure_priority_label(repo) {
        run.fail("gh label create", 1, &error);
        return false;
    }
    let mut ok = true;
    for url in urls {
        if let Err(error) = gateway.apply_priority_label(repo, &url) {
            run.fail("gh issue edit", 1, &error);
            ok = false;
        }
    }
    ok
}

#[cfg(test)]
mod tests {
    use super::{
        BatchInputs, BatchResult, CreateRequest, CreatedRow, FailureMode, FileRequest,
        FilingGateway, Payload, Recovered, Session, drive, priority_issue_number,
        report_batch_failure, run_issue_batch,
    };
    use larch_core::{AcceptedBlock, FiledIssue, GitHubRepositoryRef};
    use std::{
        cell::RefCell,
        collections::{BTreeMap, HashSet},
        fs,
        path::Path,
    };
    use tempfile::TempDir;

    /// The one surface a scripted gateway refuses, if any.
    #[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
    enum Refuse {
        #[default]
        Nothing,
        Edge,
        LabelProvision,
        LabelApply,
        Probe,
    }

    #[test]
    fn priority_issue_url_is_bound_to_the_selected_repository() {
        let repository = GitHubRepositoryRef::new("character-ai", "larch").expect("repository");
        assert_eq!(
            priority_issue_number(
                &repository,
                "https://github.com/Character-AI/LARCH/issues/8590"
            ),
            Some(8590)
        );
        for url in [
            "https://github.com/other/larch/issues/8590",
            "https://github.com/character-ai/other/issues/8590",
            "https://github.com/character-ai/larch/pull/8590",
            "https://github.com/character-ai/larch/issues/8590?wrong=1",
        ] {
            assert_eq!(priority_issue_number(&repository, url), None, "{url}");
        }
    }

    /// One scripted gateway, recording what the driver asked it to do.
    #[derive(Default)]
    struct FakeGateway {
        created: RefCell<Vec<String>>,
        closed: RefCell<Vec<u64>>,
        edges: RefCell<Vec<(u64, u64)>>,
        labelled: RefCell<Vec<String>>,
        next_number: RefCell<u64>,
        create_fails_at: Option<usize>,
        refuse: Refuse,
        checkpoint_code: u8,
    }

    impl FilingGateway for FakeGateway {
        fn probe_blocker(&self, _repo: &str, _issue_number: &str) -> Result<(), String> {
            if self.refuse == Refuse::Probe {
                Err("probe refused".to_owned())
            } else {
                Ok(())
            }
        }

        fn create(&self, request: &CreateRequest<'_>) -> Result<CreatedRow, String> {
            let position = self.created.borrow().len() + 1;
            if self.create_fails_at == Some(position) {
                return Err("create refused".to_owned());
            }
            self.created.borrow_mut().push(request.title.to_owned());
            let mut next = self.next_number.borrow_mut();
            *next += 1;
            Ok(CreatedRow {
                number: *next,
                url: format!("https://github.com/o/r/issues/{next}"),
            })
        }

        fn link_blocked_by(&self, _repo: &str, client: u64, blocker: u64) -> Result<(), String> {
            if self.refuse == Refuse::Edge {
                return Err("edge refused".to_owned());
            }
            self.edges.borrow_mut().push((client, blocker));
            Ok(())
        }

        fn close_orphan(&self, _repo: &str, issue: u64) {
            self.closed.borrow_mut().push(issue);
        }

        fn ensure_priority_label(&self, _repo: &str) -> Result<(), String> {
            if self.refuse == Refuse::LabelProvision {
                Err("label provisioning refused".to_owned())
            } else {
                Ok(())
            }
        }

        fn apply_priority_label(&self, _repo: &str, url: &str) -> Result<(), String> {
            if self.refuse == Refuse::LabelApply {
                return Err("label application refused".to_owned());
            }
            self.labelled.borrow_mut().push(url.to_owned());
            Ok(())
        }

        fn codex_available(&self) -> bool {
            false
        }

        fn combine(
            &self,
            _prompt: &Path,
            _output: &Path,
            _timeout: &str,
            _tmpdir: &Path,
        ) -> Result<(), String> {
            Err("codex unavailable".to_owned())
        }

        fn disposition_checkpoint(&self, _tmpdir: &Path) -> u8 {
            self.checkpoint_code
        }
    }

    fn run_for(tmpdir: &TempDir) -> Session {
        Session {
            tmpdir: tmpdir.path().to_owned(),
            run_id: "run-1".to_owned(),
            state: vec![("REPO".to_owned(), "o/r".to_owned())],
            request: FileRequest {
                repo: String::new(),
                issue_number: String::new(),
                codex_timeout: "300".to_owned(),
                context_file: String::new(),
            },
        }
    }

    fn write_accepted(tmpdir: &TempDir, text: &str) {
        fs::write(tmpdir.path().join("oos-accepted-main-agent.md"), text)
            .expect("write accepted artifact");
    }

    const TWO_BLOCKS: &str = "### OOS_1: First finding\n- **Description**: alpha\n\n\
                              ### OOS_2: Second finding\n- **Description**: beta\n";

    #[test]
    fn an_empty_session_reports_empty_and_stamps_nothing() {
        let tmpdir = TempDir::new().expect("session directory");
        let gateway = FakeGateway::default();
        let (code, payload) = drive(&run_for(&tmpdir), &gateway);
        assert_eq!(code, 0);
        assert_eq!(payload.status, "empty");
        assert_eq!(payload.accepted_count, 0);
        assert!(payload.run_statistics_written);
        assert!(!payload.step9a1_stamped);
        assert!(gateway.created.borrow().is_empty());
    }

    #[test]
    fn a_carve_out_records_placeholders_without_filing() {
        let tmpdir = TempDir::new().expect("session directory");
        write_accepted(&tmpdir, TWO_BLOCKS);
        let mut run = run_for(&tmpdir);
        run.state
            .push(("FORKED_TARGET".to_owned(), "true".to_owned()));
        let gateway = FakeGateway::default();
        let (code, payload) = drive(&run, &gateway);
        assert_eq!(code, 0);
        assert_eq!(payload.status, "skipped");
        assert_eq!(payload.filed_count, 0);
        assert_eq!(payload.urls.len(), 2);
        assert!(payload.urls[0].starts_with("skipped://oos/"));
        assert!(gateway.created.borrow().is_empty());
    }

    #[test]
    fn a_full_pass_files_records_and_stamps() {
        let tmpdir = TempDir::new().expect("session directory");
        write_accepted(&tmpdir, TWO_BLOCKS);
        // The default cap of one rolls the batch into a single aggregate.
        let gateway = FakeGateway::default();
        let (code, payload) = drive(&run_for(&tmpdir), &gateway);
        assert_eq!(code, 0, "payload={}", payload.render());
        assert_eq!(payload.status, "filed");
        assert_eq!(payload.accepted_count, 2);
        assert_eq!(gateway.created.borrow().len(), 1);
        let sentinel = fs::read_to_string(tmpdir.path().join("oos-issues-created.md"))
            .expect("sentinel written");
        assert!(sentinel.contains("- **Filed**: 1"));
        let ndjson = fs::read_to_string(
            tmpdir
                .path()
                .join("larch-logs/implement/run-1/oos-issues.ndjson"),
        )
        .expect("batch written");
        assert!(ndjson.contains("\"category\":\"OOS\""));
    }

    #[test]
    fn a_resumed_run_refiles_nothing_already_recorded() {
        let tmpdir = TempDir::new().expect("session directory");
        write_accepted(
            &tmpdir,
            "### OOS_1: First finding\n- **Description**: alpha\n- **Filed URL**: https://github.com/o/r/issues/11\n",
        );
        let gateway = FakeGateway::default();
        let (code, payload) = drive(&run_for(&tmpdir), &gateway);
        assert_eq!(code, 0);
        assert_eq!(payload.status, "already_filed");
        assert_eq!(payload.filed_count, 1);
        assert_eq!(payload.deduplicated_count, 1);
        assert!(gateway.created.borrow().is_empty());
    }

    #[test]
    fn sentinel_evidence_alone_reports_an_idempotent_rerun() {
        let tmpdir = TempDir::new().expect("session directory");
        // Nothing public remains pending, so only the sentinel has anything to say.
        write_accepted(
            &tmpdir,
            "### OOS_1: [security] Private only\n- **Description**: d\n",
        );
        fs::write(
            tmpdir.path().join("oos-issues-created.md"),
            "- **Title**: Recovered\n- **Filed URL**: https://github.com/o/r/issues/12\n- **Filed**: 1\n",
        )
        .expect("write sentinel");
        let gateway = FakeGateway::default();
        let (code, payload) = drive(&run_for(&tmpdir), &gateway);
        assert_eq!(code, 0);
        assert_eq!(payload.status, "idempotent");
        assert_eq!(payload.urls, vec!["https://github.com/o/r/issues/12"]);
        assert!(gateway.created.borrow().is_empty());
    }

    #[test]
    fn a_pruned_session_rebuilds_its_evidence_from_the_sentinel() {
        let tmpdir = TempDir::new().expect("session directory");
        fs::write(
            tmpdir.path().join("oos-issues-created.md"),
            "- **Title**: Recovered\n- **Filed URL**: https://github.com/o/r/issues/12\n- **Filed**: 1\n",
        )
        .expect("write sentinel");
        let gateway = FakeGateway::default();
        let (code, payload) = drive(&run_for(&tmpdir), &gateway);
        assert_eq!(code, 0);
        assert_eq!(payload.status, "already_filed");
        assert!(
            tmpdir.path().join("oos-accepted-main-agent.md").is_file(),
            "recovery evidence materialized"
        );
        assert!(gateway.created.borrow().is_empty());
    }

    #[test]
    fn a_pending_security_sidecar_stops_before_statistics() {
        let tmpdir = TempDir::new().expect("session directory");
        write_accepted(&tmpdir, TWO_BLOCKS);
        let gateway = FakeGateway {
            checkpoint_code: 3,
            ..FakeGateway::default()
        };
        let (code, payload) = drive(&run_for(&tmpdir), &gateway);
        assert_eq!(code, 3);
        assert_eq!(payload.status, "security_sidecar_present");
        assert!(payload.run_statistics_written);
        assert!(!payload.step9a1_stamped);
    }

    #[test]
    fn a_refused_checkpoint_reports_its_own_code() {
        let tmpdir = TempDir::new().expect("session directory");
        let gateway = FakeGateway {
            checkpoint_code: 1,
            ..FakeGateway::default()
        };
        let (code, payload) = drive(&run_for(&tmpdir), &gateway);
        assert_eq!(code, 1);
        assert_eq!(payload.status, "disposition_checkpoint_failed");
        assert!(!payload.run_statistics_written);
    }

    #[test]
    fn a_failed_create_closes_what_the_pass_already_filed() {
        let tmpdir = TempDir::new().expect("session directory");
        let run = run_for(&tmpdir);
        let combined = tmpdir.path().join("combined.md");
        fs::write(&combined, TWO_BLOCKS).expect("write combined");
        let gateway = FakeGateway {
            create_fails_at: Some(2),
            ..FakeGateway::default()
        };
        let result = run_issue_batch(
            &run,
            &gateway,
            &BatchInputs {
                repo: "o/r",
                issue_number: "",
                combined: &combined,
                deps: None,
                stable_ids: &BTreeMap::new(),
                priority: &HashSet::new(),
            },
        );
        assert_eq!(result.failures, 1);
        assert_eq!(result.failure_mode, FailureMode::HardCreate);
        assert_eq!(result.filed.len(), 1);
        assert_eq!(gateway.closed.borrow().len(), 1);
    }

    #[test]
    fn a_rolled_up_create_failure_preserves_the_filed_aggregate() {
        let tmpdir = TempDir::new().expect("session directory");
        let run = run_for(&tmpdir);
        let recovered = Recovered {
            pending: Vec::new(),
            all_blocks: Vec::new(),
            persisted: Vec::new(),
            already: Vec::new(),
        };
        let filed = FiledIssue {
            title: "Combined finding".to_owned(),
            url: "https://github.com/o/r/issues/17".to_owned(),
            source_stable_ids: vec!["OOS_1".to_owned(), "OOS_2".to_owned()],
            ..FiledIssue::default()
        };
        let batch = BatchResult {
            filed: vec![filed],
            failures: 1,
            failure_mode: FailureMode::HardCreate,
        };

        let (code, payload) = report_batch_failure(&run, &recovered, &batch, 2);

        assert_eq!(code, 1);
        assert_eq!(payload.status, "hard_create_partial_failure");
        assert_eq!(payload.filed_count, 1);
        assert_eq!(FailureMode::HardCreate.as_str(), "hard_create");
        assert_eq!(FailureMode::None.as_str(), "none");
        let sentinel = fs::read_to_string(tmpdir.path().join("oos-issues-created.md"))
            .expect("sentinel written");
        assert!(sentinel.contains("https://github.com/o/r/issues/17"));
        let ndjson = fs::read_to_string(
            tmpdir
                .path()
                .join("larch-logs/implement/run-1/oos-issues.ndjson"),
        )
        .expect("batch written");
        assert!(ndjson.contains("Hard-create partial failure"));
    }

    #[test]
    fn a_priority_failure_preserves_the_filed_issue() {
        let tmpdir = TempDir::new().expect("session directory");
        let run = run_for(&tmpdir);
        let recovered = Recovered {
            pending: Vec::new(),
            all_blocks: Vec::new(),
            persisted: Vec::new(),
            already: Vec::new(),
        };
        let batch = BatchResult {
            filed: vec![FiledIssue {
                title: "Priority finding".to_owned(),
                url: "https://github.com/o/r/issues/18".to_owned(),
                ..FiledIssue::default()
            }],
            failures: 1,
            failure_mode: FailureMode::PriorityLabel,
        };

        let (code, payload) = report_batch_failure(&run, &recovered, &batch, 1);

        assert_eq!(code, 1);
        assert_eq!(payload.status, "priority_label_partial_failure");
        assert_eq!(payload.filed_count, 1);
        let sentinel = fs::read_to_string(tmpdir.path().join("oos-issues-created.md"))
            .expect("sentinel written");
        assert!(sentinel.contains("https://github.com/o/r/issues/18"));
        let ndjson = fs::read_to_string(
            tmpdir
                .path()
                .join("larch-logs/implement/run-1/oos-issues.ndjson"),
        )
        .expect("batch written");
        assert!(ndjson.contains("Priority label partial failure"));
    }

    #[test]
    fn an_unprovisionable_label_is_a_priority_provision_failure() {
        let tmpdir = TempDir::new().expect("session directory");
        write_accepted(
            &tmpdir,
            "### OOS_1: Correctness risk\n- **Description**: alpha\n- **focus-area**: correctness\n",
        );
        let gateway = FakeGateway {
            refuse: Refuse::LabelProvision,
            ..FakeGateway::default()
        };
        let (code, payload) = drive(&run_for(&tmpdir), &gateway);
        assert_eq!(code, 1);
        assert_eq!(payload.status, "issue_batch_failed");
        assert_eq!(payload.failure_mode.as_deref(), Some("priority_provision"));
        assert!(gateway.created.borrow().is_empty());
    }

    #[test]
    fn an_unapplied_label_retracts_the_issue_it_could_not_label() {
        let tmpdir = TempDir::new().expect("session directory");
        write_accepted(
            &tmpdir,
            "### OOS_1: Correctness risk\n- **Description**: alpha\n- **focus-area**: correctness\n",
        );
        let gateway = FakeGateway {
            refuse: Refuse::LabelApply,
            ..FakeGateway::default()
        };
        let (code, payload) = drive(&run_for(&tmpdir), &gateway);
        assert_eq!(code, 1);
        assert_eq!(payload.status, "issue_batch_failed");
        assert_eq!(payload.failure_mode.as_deref(), Some("priority_label"));
        assert_eq!(gateway.closed.borrow().len(), 1);
    }

    #[test]
    fn a_malformed_item_is_skipped_rather_than_filed_empty() {
        let tmpdir = TempDir::new().expect("session directory");
        let run = run_for(&tmpdir);
        let combined = tmpdir.path().join("combined.md");
        fs::write(&combined, "### OOS_1: Empty one\n").expect("write combined");
        let gateway = FakeGateway::default();
        let result = run_issue_batch(
            &run,
            &gateway,
            &BatchInputs {
                repo: "o/r",
                issue_number: "",
                combined: &combined,
                deps: None,
                stable_ids: &BTreeMap::new(),
                priority: &HashSet::new(),
            },
        );
        assert!(result.filed.is_empty());
        assert_eq!(result.failure_mode, FailureMode::None);
        assert!(gateway.created.borrow().is_empty());
        let ledger =
            fs::read_to_string(tmpdir.path().join("execution-issues.md")).expect("ledger written");
        assert!(ledger.contains("skipped malformed accepted-OOS item"));
    }

    #[test]
    fn a_refused_blocker_probe_stops_the_batch() {
        let tmpdir = TempDir::new().expect("session directory");
        let run = run_for(&tmpdir);
        let combined = tmpdir.path().join("combined.md");
        fs::write(&combined, "### OOS_1: One\n- **Description**: a\n").expect("write combined");
        let gateway = FakeGateway {
            refuse: Refuse::Probe,
            ..FakeGateway::default()
        };
        let result = run_issue_batch(
            &run,
            &gateway,
            &BatchInputs {
                repo: "o/r",
                issue_number: "42",
                combined: &combined,
                deps: None,
                stable_ids: &BTreeMap::new(),
                priority: &HashSet::new(),
            },
        );
        assert_eq!(result.failures, 1);
        assert_eq!(result.failure_mode, FailureMode::HardCreate);
        assert!(gateway.created.borrow().is_empty());
    }

    #[test]
    fn a_failed_edge_closes_the_issue_it_could_not_wire() {
        let tmpdir = TempDir::new().expect("session directory");
        let run = run_for(&tmpdir);
        let combined = tmpdir.path().join("combined.md");
        fs::write(&combined, "### OOS_1: One\n- **Description**: a\n").expect("write combined");
        let gateway = FakeGateway {
            refuse: Refuse::Edge,
            ..FakeGateway::default()
        };
        let result = run_issue_batch(
            &run,
            &gateway,
            &BatchInputs {
                repo: "o/r",
                issue_number: "42",
                combined: &combined,
                deps: None,
                stable_ids: &BTreeMap::new(),
                priority: &HashSet::new(),
            },
        );
        assert_eq!(result.failures, 1);
        assert_eq!(gateway.closed.borrow().len(), 1);
    }

    #[test]
    fn intra_batch_edges_file_in_dependency_order() {
        let tmpdir = TempDir::new().expect("session directory");
        let run = run_for(&tmpdir);
        let combined = tmpdir.path().join("combined.md");
        fs::write(
            &combined,
            "### OOS_1: One\n- **Description**: a\n\n### OOS_2: Two\n- **Description**: b\n",
        )
        .expect("write combined");
        let deps = tmpdir.path().join("deps.tsv");
        fs::write(&deps, "2\t1\n").expect("write deps");
        let gateway = FakeGateway::default();
        let result = run_issue_batch(
            &run,
            &gateway,
            &BatchInputs {
                repo: "o/r",
                issue_number: "",
                combined: &combined,
                deps: Some(&deps),
                stable_ids: &BTreeMap::new(),
                priority: &HashSet::new(),
            },
        );
        assert_eq!(result.filed.len(), 2);
        assert_eq!(gateway.created.borrow()[0], "Two");
        assert_eq!(gateway.edges.borrow().as_slice(), &[(2, 1)]);
    }

    #[test]
    fn a_failed_backfill_refuses_before_anything_is_filed() {
        let tmpdir = TempDir::new().expect("session directory");
        write_accepted(
            &tmpdir,
            "### OOS_1: Correctness risk\n- **Description**: alpha\n- **focus-area**: correctness\n- **Filed URL**: https://github.com/o/r/issues/7\n",
        );
        let gateway = FakeGateway {
            refuse: Refuse::LabelProvision,
            ..FakeGateway::default()
        };
        let (code, payload) = drive(&run_for(&tmpdir), &gateway);
        assert_eq!(code, 1);
        assert_eq!(payload.status, "priority_label_backfill_failed");
        assert_eq!(payload.filed_count, 1);
    }

    #[test]
    fn the_payload_renders_its_documented_field_order() {
        let payload = Payload {
            status: "filed".to_owned(),
            accepted_count: 2,
            filed_count: 1,
            urls: vec!["https://github.com/o/r/issues/1".to_owned()],
            ..Payload::default()
        };
        assert_eq!(
            payload.render(),
            "{\"status\":\"filed\",\"accepted_count\":2,\"filed_count\":1,\"deduplicated_count\":0,\"urls\":[\"https://github.com/o/r/issues/1\"],\"run_statistics_written\":false,\"step9a1_stamped\":false}"
        );
    }

    #[test]
    fn payload_from_filed_counts_recovered_records() {
        let filed = vec![
            FiledIssue {
                url: "u1".to_owned(),
                duplicate: true,
                ..FiledIssue::default()
            },
            FiledIssue {
                url: "u2".to_owned(),
                ..FiledIssue::default()
            },
        ];
        let payload = Payload::from_filed("filed", 3, &filed);
        assert_eq!(payload.deduplicated_count, 1);
        assert_eq!(payload.filed_count, 2);
        assert_eq!(payload.accepted_count, 3);
    }

    #[test]
    fn accepted_blocks_default_to_no_priority() {
        assert!(!AcceptedBlock::default().priority);
    }
}
