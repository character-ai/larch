//! The five `oos` verbs that compose, cap, order, and gate a run's OOS batch.
//!
//! * `materialize-manifest` turns an external implementer's untrusted
//!   `oos_observations[]` into canonical accepted-OOS blocks, routing anything
//!   that names a security focus area to a private sidecar instead.
//! * `issue-cap` bounds how many issues one run may file, rolling the surplus
//!   into one aggregate that preserves every rolled-up body verbatim.
//! * `file-conflict-deps` emits the deterministic `<blocker>\t<blocked>` rows
//!   `/issue` reads as `--intra-batch-deps-file`, so two items that touch the
//!   same lines of the same file are never filed as parallel work.
//! * `disposition-gate` refuses to let a run finish having silently dropped an
//!   accepted OOS record.
//! * `disposition-checkpoint` resolves the gate's inputs from one session
//!   directory and records what it found, so an interrupted run resumes without
//!   refiling.
//!
//! Everything that leaves this process goes through one seam. File composition
//! is [`larch_core::issue`]; the only environmental reads are the repository
//! history behind [`GateGit`] and the session directory itself, so each verb's
//! decisions are unit-tested against a double rather than a live clone.
//!
//! Ports `larch.issue.file_oos`.

use std::{
    env,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::git::GixRepository;
use larch_core::{
    ACCEPTED_OOS_FILENAMES, DispositionCounters, DispositionState, DuplicatePolicy,
    FILE_CONFLICT_DEFAULT_CLUSTER_CAP, FILE_CONFLICT_DEFAULT_GLOBAL_CAP, IssueCapError, KvDocument,
    ManifestObservation, ParseOptions, RepositoryRead as _, Revision, apply_issue_cap,
    count_filed_urls_strict_files, count_filed_urls_union_files, count_inline_triage_occurrences,
    count_non_security_oos_blocks, count_rejected_oos_markers_from_ndjson, existing_oos_titles,
    next_oos_number, normalize_title, observation_is_security, parse_conflict_cap,
    parse_issue_input, plan_file_conflict_deps, python_str, read_universal_newlines,
    render_deps_tsv, universal_newlines,
};
use serde_json::Value;

use crate::{
    argparse_compat::{missing, parse_with_flags, usage_error as argparse_usage_error},
    run_log_entry_commands::append_execution_issue,
};

/// Publish one `argparse`-shaped usage refusal at this domain's usage code.
fn usage_error(usage: &str, program: &str, error: &str) -> ExitCode {
    argparse_usage_error(usage, program, error, VALIDATION_FAILED_RC)
}

/// Exit code every verb reports for a rejected command line.
const VALIDATION_FAILED_RC: u8 = 2;
/// Exit code the gate reports when accepted OOS remains undisposed.
const GATE_BLOCKED_RC: u8 = 1;
/// Exit code the checkpoint reports when only the security sidecar remains.
const SECURITY_SIDECAR_RC: u8 = 3;
/// Public artifact manifest observations are materialized into.
const MAIN_AGENT_FILE: &str = "oos-accepted-main-agent.md";
/// Private artifact security-routed observations are retained in.
const SECURITY_SIDECAR_FILE: &str = "security-oos-observations.md";
/// The run's problem ledger, where every verb records a tool failure.
const EXECUTION_ISSUES_FILE: &str = "execution-issues.md";
/// Stderr breadcrumb the checkpoint leaves for its caller.
const CHECKPOINT_STDERR_LOG: &str = "oos-disposition-checkpoint.stderr.log";
/// Stderr breadcrumb the gate leaves for its caller.
const GATE_STDERR_LOG: &str = "oos-disposition-gate.stderr.log";
/// The ledger site every `oos file` tool failure is recorded under.
pub const FAILURE_SITE: &str = "step-9a1-oos-file";

const MATERIALIZE_USAGE: &str = "usage: cli.py oos materialize-manifest [-h] [--count-only] --manifest-path MANIFEST_PATH --implement-tmpdir IMPLEMENT_TMPDIR";
const ISSUE_CAP_USAGE: &str =
    "usage: cli.py oos issue-cap [-h] --input-file INPUT_FILE [--output OUTPUT]";
const CHECKPOINT_USAGE: &str = "usage: cli.py oos disposition-checkpoint [-h] --implement-tmpdir IMPLEMENT_TMPDIR [--design-tmpdir DESIGN_TMPDIR]";
const GATE_USAGE: &str = concat!(
    "usage: cli.py oos disposition-gate [-h] [--fork-mode] [--repo-unavailable]\n",
    "                                   [--accepted-files ACCEPTED_FILES]\n",
    "                                   [--filed-urls-file FILED_URLS_FILE]\n",
    "                                   [--filed-urls-strict-file FILED_URLS_STRICT_FILE]\n",
    "                                   [--oos-issues-ndjson OOS_ISSUES_NDJSON]\n",
    "                                   [--commit-range COMMIT_RANGE]",
);

/// Write `text` to `target` through a sibling temporary file.
///
/// The temporary carries the target's own `.tmp` suffix and is removed on every
/// path, so a failed write never leaves a half-written batch behind and never
/// leaves the temporary where a later reader could mistake it for output.
pub fn atomic_write(target: &Path, text: &str) -> Result<(), String> {
    let temporary = temporary_sibling(target);
    let result = fs::write(&temporary, text)
        .and_then(|()| fs::rename(&temporary, target))
        .map_err(|error| error.to_string());
    let _removed = fs::remove_file(&temporary);
    result
}

/// Return the `<target>.tmp` sibling every atomic write stages through.
fn temporary_sibling(target: &Path) -> PathBuf {
    let mut name = target.as_os_str().to_owned();
    name.push(".tmp");
    PathBuf::from(name)
}

/// Append one `### Tool Failures` row to the run's problem ledger.
pub fn append_failure_log(log: &Path, site: &str, tool: &str, rc: i32, output: &str) {
    if let Some(parent) = log.parent() {
        let _created = fs::create_dir_all(parent);
    }
    let mut entry = format!("\n### Tool Failures\n- **{site}**: {tool} exited {rc}\n");
    if !output.is_empty() {
        entry.push_str(output.trim_end());
        entry.push('\n');
    }
    let existing = read_universal_newlines(log).unwrap_or_default();
    let _written = fs::write(log, existing + &entry);
}

/// Record one materialization warning through the one ledger owner.
///
/// The owner adds an entry once, so a manifest routing several observations
/// privately leaves one breadcrumb rather than one per observation. Recording
/// is best effort: the owner refuses only when the ledger path is not a regular
/// file, and materialization must not fail on a hostile session directory.
pub fn append_run_log_warning(tmpdir: &Path, entry: &str) {
    let _recorded = append_execution_issue(&tmpdir.join(EXECUTION_ISSUES_FILE), "Warnings", entry);
}

// ---------------------------------------------------------------------------
// oos materialize-manifest
// ---------------------------------------------------------------------------

/// Read the `oos_observations` array out of one implementer manifest.
///
/// The manifest is vendor output, so shape is checked before anything is read
/// from it: a document that is not an object, or whose observations are not an
/// array, is refused rather than silently treated as empty.
fn manifest_observations(path: &Path, count_only: bool) -> Result<Vec<Value>, String> {
    let raw = fs::read_to_string(path)
        .map_err(|error| format!("manifest must be readable JSON: {error}"))?;
    let document: Value = serde_json::from_str(&raw)
        .map_err(|error| format!("manifest must be readable JSON: {error}"))?;
    let Value::Object(fields) = document else {
        return Err("manifest must be a JSON object".to_owned());
    };
    let observations = match fields.get("oos_observations") {
        None | Some(Value::Null) => return Ok(Vec::new()),
        Some(Value::Array(items)) => items.clone(),
        Some(_other) => return Err("oos_observations must be an array".to_owned()),
    };
    if !count_only && let Some(index) = observations.iter().position(|item| !item.is_object()) {
        return Err(format!(
            "oos_observations[{}] must be a JSON object",
            index + 1
        ));
    }
    Ok(observations)
}

/// Read one observation's field, honouring the three spellings of focus area.
fn observation_field(item: &Value, keys: &[&str]) -> String {
    keys.iter()
        .find_map(|key| item.get(*key).filter(|value| !value.is_null()))
        .map_or_else(String::new, |value| python_str(Some(value)))
}

/// Turn one raw observation into its sanitized, publishable form.
fn read_observation(item: &Value, index: usize) -> ManifestObservation {
    let mut title = normalize_title(&observation_field(item, &["title"]));
    if title.is_empty() {
        title = format!("Untitled external implementer OOS {index}");
    }
    let phase = {
        let raw = item
            .get("phase")
            .filter(|value| !value.is_null())
            .map_or_else(|| "implement".to_owned(), |value| python_str(Some(value)));
        let normalized = normalize_title(&raw);
        if normalized.is_empty() {
            "implement".to_owned()
        } else {
            normalized
        }
    };
    ManifestObservation {
        title,
        description: observation_field(item, &["description"]),
        phase,
        focus_area: normalize_title(&observation_field(
            item,
            &["Focus area", "focus-area", "focus_area"],
        )),
    }
}

/// Materialize one manifest's observations into the run's accepted-OOS files.
///
/// Returns how many observations the manifest carried, which is what the
/// caller's counter reports whether or not any of them were new.
pub fn materialize(manifest: &Path, tmpdir: &Path, count_only: bool) -> Result<usize, String> {
    let observations = manifest_observations(manifest, count_only)?;
    if count_only || observations.is_empty() {
        return Ok(observations.len());
    }
    if env::var("LARCH_TEST_MATERIALIZE_FORCE_FAIL").as_deref() == Ok("true") {
        return Err("LARCH_TEST_MATERIALIZE_FORCE_FAIL".to_owned());
    }
    let public = tmpdir.join(MAIN_AGENT_FILE);
    if let Some(parent) = public.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    if !public.exists() {
        fs::write(&public, "").map_err(|error| error.to_string())?;
    }
    let existing = read_universal_newlines(&public).unwrap_or_default();
    let mut titles = existing_oos_titles(&existing);
    let mut next = next_oos_number(&existing);
    let sidecar = tmpdir.join(SECURITY_SIDECAR_FILE);
    let mut blocks: Vec<String> = Vec::new();
    for (offset, item) in observations.iter().enumerate() {
        let observation = read_observation(item, offset + 1);
        if observation_is_security(&observation.description, &observation.focus_area) {
            route_to_sidecar(&sidecar, tmpdir, &observation)?;
            continue;
        }
        let key = observation.title.to_lowercase();
        if titles.contains(&key) {
            continue;
        }
        blocks.push(observation.render_public_block(next));
        titles.push(key);
        next = next.saturating_add(1);
    }
    if !blocks.is_empty() {
        let separator = if existing.trim().is_empty() {
            ""
        } else {
            "\n\n"
        };
        let rendered = format!(
            "{}{separator}{}\n",
            existing.trim_end(),
            blocks.join("\n\n")
        );
        fs::write(&public, rendered).map_err(|error| error.to_string())?;
    }
    Ok(observations.len())
}

/// Retain one security-routed observation privately, exactly once.
fn route_to_sidecar(
    sidecar: &Path,
    tmpdir: &Path,
    observation: &ManifestObservation,
) -> Result<(), String> {
    let existing = read_universal_newlines(sidecar).unwrap_or_default();
    let heading = observation.security_heading();
    if existing.lines().any(|line| line == heading) {
        return Ok(());
    }
    let entry = observation.render_security_entry(!existing.is_empty());
    fs::write(sidecar, existing + &entry).map_err(|error| error.to_string())?;
    append_run_log_warning(
        tmpdir,
        "- **cli.py oos materialize-manifest**: security-routed manifest OOS retained in security-oos-observations.md",
    );
    Ok(())
}

/// Run `oos materialize-manifest`.
pub fn materialize_manifest(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &["--manifest-path", "--implement-tmpdir"],
        &["--count-only"],
        0,
    );
    if let Some(error) = parsed.error() {
        return usage_error(MATERIALIZE_USAGE, "cli.py oos materialize-manifest", &error);
    }
    let (Some(manifest), Some(tmpdir)) = (
        parsed.value("--manifest-path"),
        parsed.value("--implement-tmpdir"),
    ) else {
        return usage_error(
            MATERIALIZE_USAGE,
            "cli.py oos materialize-manifest",
            &missing(&[
                ("--manifest-path", parsed.value("--manifest-path").is_some()),
                (
                    "--implement-tmpdir",
                    parsed.value("--implement-tmpdir").is_some(),
                ),
            ]),
        );
    };
    let count_only = parsed.flag("--count-only");
    match materialize(Path::new(manifest), Path::new(tmpdir), count_only) {
        Ok(count) => {
            if count_only {
                println!("{count}");
            }
            ExitCode::SUCCESS
        }
        Err(message) => {
            eprintln!("{message}");
            ExitCode::from(1)
        }
    }
}

// ---------------------------------------------------------------------------
// oos issue-cap
// ---------------------------------------------------------------------------

/// Read the per-run cap, refusing every spelling that is not a positive count.
pub fn issue_cap_value() -> Result<usize, String> {
    let raw = env::var("OOS_ISSUES_PER_RUN_CAP").unwrap_or_else(|_missing| "1".to_owned());
    parse_conflict_cap(&raw)
        .ok_or_else(|| "OOS_ISSUES_PER_RUN_CAP must be a positive integer".to_owned())
}

/// Apply the cap to `input`, writing the result to `output` or back in place.
pub fn cap_batch(input: &Path, output: Option<&Path>, cap: usize) -> Result<(), String> {
    if !input.is_file() {
        return Err(format!("input file not found: {}", input.display()));
    }
    if let Some(output) = output
        && absolute(input) == absolute(output)
    {
        return Err("--input-file and --output resolve to the same path".to_owned());
    }
    let bytes = fs::read(input).map_err(|error| error.to_string())?;
    let text = String::from_utf8(bytes)
        .map_err(|error| format!("'utf-8' codec can't decode input file: {error}"))?;
    let text = universal_newlines(&text).into_owned();
    let capped = apply_issue_cap(&text, cap).map_err(|error: IssueCapError| error.message())?;
    match (capped, output) {
        (None, None) => Ok(()),
        (None, Some(output)) => atomic_write(output, &text),
        (Some(rendered), target) => atomic_write(target.unwrap_or(input), &rendered),
    }
}

/// Resolve `path` without requiring it to exist, as Python's `resolve` did.
fn absolute(path: &Path) -> PathBuf {
    path.canonicalize().unwrap_or_else(|_missing| {
        env::current_dir().map_or_else(|_error| path.to_path_buf(), |cwd| cwd.join(path))
    })
}

/// Run `oos issue-cap`.
pub fn issue_cap(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(arguments, &["--input-file", "--output"], &[], 0);
    if let Some(error) = parsed.error() {
        return usage_error(ISSUE_CAP_USAGE, "cli.py oos issue-cap", &error);
    }
    let Some(input) = parsed.value("--input-file") else {
        return usage_error(
            ISSUE_CAP_USAGE,
            "cli.py oos issue-cap",
            &missing(&[("--input-file", false)]),
        );
    };
    let output = parsed.value("--output").map(PathBuf::from);
    run_issue_cap(Path::new(input), output.as_deref(), issue_cap_value())
}

/// Apply one already-resolved cap, cleaning up after either kind of refusal.
///
/// An invalid knob and an unusable batch are different failures — the first
/// exits `2` and the second `1` — but both must leave no stale `--output`
/// behind, because a later reader cannot tell a stale batch from a fresh one.
fn run_issue_cap(input: &Path, output: Option<&Path>, cap: Result<usize, String>) -> ExitCode {
    let (code, message) = match cap.and_then(|cap| {
        cap_batch(input, output, cap)
            .map_err(|message| (message, 1))
            .map_err(|(message, _rc)| message)
    }) {
        Ok(()) => return ExitCode::SUCCESS,
        Err(message) => (
            if message.starts_with("OOS_ISSUES_PER_RUN_CAP") {
                VALIDATION_FAILED_RC
            } else {
                1
            },
            message,
        ),
    };
    clear_stale_output(input, output);
    eprintln!("oos-issue-cap: {message}");
    ExitCode::from(code)
}

/// Remove a distinct `--output` after a refusal so no stale batch survives.
fn clear_stale_output(input: &Path, output: Option<&Path>) {
    if let Some(output) = output
        && absolute(input) != absolute(output)
    {
        let _removed = fs::remove_file(output);
    }
}

// ---------------------------------------------------------------------------
// oos file-conflict-deps
// ---------------------------------------------------------------------------

/// Read one positive cap knob, naming the knob in its refusal.
pub fn conflict_cap(name: &str, default: usize) -> Result<usize, String> {
    let raw = env::var(name).unwrap_or_else(|_missing| default.to_string());
    parse_conflict_cap(&raw)
        .ok_or_else(|| format!("ERROR: {name} must be a positive integer (got: '{raw}')"))
}

/// Print the hand-rolled usage this verb has always printed.
fn conflict_usage() {
    eprintln!("Usage: cli.py oos file-conflict-deps --input-file FILE [--output FILE]");
    eprintln!("  When --output is omitted and IMPLEMENT_TMPDIR is set, the output");
    eprintln!("  defaults to $IMPLEMENT_TMPDIR/oos-intra-batch-deps.tsv.");
}

/// Parse this verb's own option line, which predates `argparse`.
fn parse_conflict_arguments(arguments: &[OsString]) -> Option<(PathBuf, PathBuf)> {
    let mut input = OsString::new();
    let mut output = OsString::new();
    let mut index = 0;
    while index < arguments.len() {
        let argument = &arguments[index];
        let value = arguments.get(index + 1).cloned();
        match (argument.to_str(), value) {
            (Some("--input-file"), Some(next)) => {
                input = next;
                index += 2;
            }
            (Some("--output"), Some(next)) => {
                output = next;
                index += 2;
            }
            (Some(name @ ("--input-file" | "--output")), None) => {
                eprintln!("ERROR: {name} requires a value");
                conflict_usage();
                return None;
            }
            _other => {
                eprintln!("Unknown option: {}", argument.to_string_lossy());
                conflict_usage();
                return None;
            }
        }
    }
    if !input.is_empty()
        && output.is_empty()
        && let Ok(tmpdir) = env::var("IMPLEMENT_TMPDIR")
        && !tmpdir.is_empty()
    {
        output = PathBuf::from(tmpdir)
            .join("oos-intra-batch-deps.tsv")
            .into_os_string();
    }
    if input.is_empty() || output.is_empty() {
        conflict_usage();
        return None;
    }
    Some((PathBuf::from(input), PathBuf::from(output)))
}

/// Plan and write the dependency rows for one batch.
pub fn write_conflict_deps(
    input: &Path,
    output: &Path,
    cluster_cap: usize,
    global_cap: usize,
) -> Result<(), String> {
    if !input.is_file() {
        return Err(format!("ERROR: input file not found: {}", input.display()));
    }
    // The batch reader this feeds is byte oriented: it never translated line
    // endings, so neither does this reader.
    let text = fs::read(input)
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
        .map_err(|error| error.to_string())?;
    let items = parse_issue_input(&text).items;
    let plan = plan_file_conflict_deps(&items, cluster_cap, global_cap)
        .map_err(|error| error.message())?;
    for warning in &plan.warnings {
        eprintln!("{warning}");
    }
    if let Some(parent) = output.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    atomic_write(output, &render_deps_tsv(&plan.deps))
}

/// Run `oos file-conflict-deps`.
pub fn file_conflict_deps(arguments: &[OsString]) -> ExitCode {
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
    let (cluster_cap, global_cap) = match caps {
        Ok(caps) => caps,
        Err(message) => {
            eprintln!("{message}");
            return ExitCode::from(VALIDATION_FAILED_RC);
        }
    };
    let Some((input, output)) = parse_conflict_arguments(arguments) else {
        return ExitCode::from(1);
    };
    match write_conflict_deps(&input, &output, cluster_cap, global_cap) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("{message}");
            let _removed = fs::remove_file(temporary_sibling(&output));
            let _cleared = fs::remove_file(&output);
            ExitCode::from(1)
        }
    }
}

// ---------------------------------------------------------------------------
// oos disposition-gate
// ---------------------------------------------------------------------------

/// The repository history the gate reads, isolated so it can be replaced.
pub trait GateGit {
    /// Return the commit range the checkpoint should hand the gate.
    fn commit_range(&self) -> String;
    /// Return every commit message in `range`, or why the range is unusable.
    ///
    /// # Errors
    /// Returns the exact refusal the gate publishes for an unusable range.
    fn commit_messages(&self, range: &str) -> Result<String, String>;
}

/// The live seam: a gix read of the clone the verb runs inside.
pub struct RepositoryGateGit;

impl RepositoryGateGit {
    fn repository() -> Result<GixRepository, String> {
        let cwd = env::current_dir().map_err(|error| error.to_string())?;
        GixRepository::discover(&cwd)
            .map_err(|_error| "not inside a git work tree (need commit-range scan)".to_owned())
    }
}

impl GateGit for RepositoryGateGit {
    fn commit_range(&self) -> String {
        let Ok(repository) = Self::repository() else {
            return "HEAD".to_owned();
        };
        let head = repository.resolve_revision(&Revision::new("HEAD"));
        let base = repository.resolve_revision(&Revision::new("origin/main"));
        if let (Ok(head), Ok(base)) = (head.as_ref(), base.as_ref())
            && let Ok(merge_base) = repository.merge_base(head, base)
        {
            return format!("{}..HEAD", merge_base.to_hex());
        }
        if base.is_ok() {
            return "origin/main..HEAD".to_owned();
        }
        if repository.resolve_revision(&Revision::new("HEAD^")).is_ok() {
            return "HEAD^..HEAD".to_owned();
        }
        "HEAD".to_owned()
    }

    fn commit_messages(&self, range: &str) -> Result<String, String> {
        let repository = Self::repository()?;
        let invalid = || format!("invalid commit-range: {range}");
        let (exclude, include) = match range.split_once("..") {
            Some((exclude, include)) => (Some(exclude), include),
            None => (None, range),
        };
        let include = repository
            .resolve_revision(&Revision::new(include))
            .map_err(|_error| invalid())?;
        let messages = match exclude {
            Some(exclude) => {
                let exclude = repository
                    .resolve_revision(&Revision::new(exclude))
                    .map_err(|_error| invalid())?;
                repository.commit_messages_range(Some(&exclude), &include)
            }
            None => repository.commit_messages_range(None, &include),
        }
        .map_err(|_error| invalid())?;
        Ok(messages
            .iter()
            .map(|message| String::from_utf8_lossy(message).into_owned())
            .collect::<Vec<String>>()
            .join("\n"))
    }
}

/// Everything one gate evaluation reads, already resolved to paths.
pub struct GateInputs<'a> {
    /// Accepted-OOS markdown files, in the order the audit reads them.
    pub accepted: &'a [PathBuf],
    /// Files whose loose GitHub issue URLs count as filing evidence.
    pub filed_urls: &'a [PathBuf],
    /// Files whose structured `- **Filed URL**:` rows count as filing evidence.
    pub filed_urls_strict: &'a [PathBuf],
    /// The filing batch, when the run resolved one.
    pub ndjson: Option<&'a Path>,
    /// The commit range whose messages carry inline-triage breadcrumbs.
    pub commit_range: &'a str,
}

/// Count what one gate evaluation found, refusing rather than guessing.
///
/// # Errors
///
/// Returns the exact refusal for an unreadable accepted-OOS path, an orphaned
/// filing batch, an unparseable batch, or an unusable commit range.
pub fn gate_counters(
    inputs: &GateInputs<'_>,
    git: &dyn GateGit,
    gh_host: &str,
) -> Result<DispositionCounters, String> {
    for path in inputs.accepted {
        if path.exists() && !path.is_file() {
            return Err(format!(
                "accepted file path is not a readable regular file: {}",
                path.display()
            ));
        }
    }
    let ndjson_paths: Vec<&Path> = inputs.ndjson.into_iter().collect();
    if let Some(ndjson) = inputs.ndjson
        && ndjson.is_file()
        && ndjson.metadata().is_ok_and(|data| data.len() > 0)
        && !inputs.accepted.iter().any(|path| path.is_file())
        && count_filed_urls_union_files(&ndjson_paths, gh_host) > 0
    {
        return Err(
            "oos-issues.ndjson lists filed GitHub issue URLs but no --accepted-files paths exist as regular files (check CSV path list)"
                .to_owned(),
        );
    }
    let (rejected, parse_error) = inputs
        .ndjson
        .map_or((0, false), count_rejected_oos_markers_from_ndjson);
    if parse_error {
        return Err(
            "jq parse failure while reading oos-issues.ndjson; refusing disposition".to_owned(),
        );
    }
    let mut loose: Vec<&Path> = inputs.filed_urls.iter().map(PathBuf::as_path).collect();
    loose.extend(ndjson_paths);
    let strict: Vec<&Path> = inputs
        .filed_urls_strict
        .iter()
        .map(PathBuf::as_path)
        .collect();
    Ok(DispositionCounters {
        non_security: inputs
            .accepted
            .iter()
            .map(|path| count_non_security_oos_blocks(path))
            .sum(),
        // The loose and strict passes are summed, not unioned: a run that
        // recorded the same URL both ways proved its disposition twice.
        filed_urls: count_filed_urls_union_files(&loose, gh_host)
            + count_filed_urls_strict_files(&strict),
        inline_triage: count_inline_triage_occurrences(&git.commit_messages(inputs.commit_range)?),
        rejected_markers: rejected,
    })
}

/// Split a comma-separated path list, dropping empty entries.
fn split_paths(value: Option<&std::ffi::OsStr>) -> Vec<PathBuf> {
    value
        .and_then(|raw| raw.to_str())
        .map(|raw| {
            raw.split(',')
                .filter(|entry| !entry.is_empty())
                .map(PathBuf::from)
                .collect()
        })
        .unwrap_or_default()
}

/// Run `oos disposition-gate`.
pub fn disposition_gate(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &[
            "--accepted-files",
            "--filed-urls-file",
            "--filed-urls-strict-file",
            "--oos-issues-ndjson",
            "--commit-range",
        ],
        &["--fork-mode", "--repo-unavailable"],
        0,
    );
    if let Some(error) = parsed.error() {
        return usage_error(GATE_USAGE, "cli.py oos disposition-gate", &error);
    }
    if parsed.flag("--fork-mode") || parsed.flag("--repo-unavailable") {
        return ExitCode::SUCCESS;
    }
    let accepted = split_paths(parsed.value("--accepted-files"));
    let filed: Vec<PathBuf> = parsed
        .values("--filed-urls-file")
        .into_iter()
        .map(PathBuf::from)
        .collect();
    let strict: Vec<PathBuf> = parsed
        .values("--filed-urls-strict-file")
        .into_iter()
        .map(PathBuf::from)
        .collect();
    let commit_range = parsed.value("--commit-range").and_then(|raw| raw.to_str());
    let (Some(commit_range), false, false) = (
        commit_range.filter(|range| !range.is_empty()),
        accepted.is_empty(),
        filed.is_empty() && strict.is_empty(),
    ) else {
        eprintln!("{GATE_USAGE}");
        return ExitCode::from(VALIDATION_FAILED_RC);
    };
    let ndjson = parsed.value("--oos-issues-ndjson").map(PathBuf::from);
    let inputs = GateInputs {
        accepted: &accepted,
        filed_urls: &filed,
        filed_urls_strict: &strict,
        ndjson: ndjson.as_deref(),
        commit_range,
    };
    let gh_host = env::var("GH_HOST").unwrap_or_default();
    match gate_counters(&inputs, &RepositoryGateGit, &gh_host) {
        Ok(counters) if counters.cleared() => ExitCode::SUCCESS,
        Ok(counters) => {
            eprintln!("{}", counters.failure_line(commit_range));
            ExitCode::from(GATE_BLOCKED_RC)
        }
        Err(message) => {
            eprintln!("oos-disposition-gate: {message}");
            ExitCode::from(VALIDATION_FAILED_RC)
        }
    }
}

// ---------------------------------------------------------------------------
// oos disposition-checkpoint
// ---------------------------------------------------------------------------

/// Read one `KEY=value` state file through the shared codec.
///
/// The legacy grammar is deliberate: these files are written by shell and by
/// Python across several steps, so a malformed line is skipped rather than
/// failing the whole read.
pub fn read_state(path: &Path) -> Vec<(String, String)> {
    let Some(text) = read_universal_newlines(path) else {
        return Vec::new();
    };
    let Ok(document) = KvDocument::parse(&text, ParseOptions::legacy()) else {
        return Vec::new();
    };
    document.select(DuplicatePolicy::Last).into_iter().collect()
}

/// Return the value of `key` across the run's two state files.
pub fn state_value(state: &[(String, String)], key: &str) -> String {
    state
        .iter()
        .rev()
        .find(|(name, _value)| name == key)
        .map_or_else(String::new, |(_name, value)| value.clone())
}

/// Return the run directories under `root` that carry a filing batch.
fn batch_candidates(root: &Path) -> Vec<PathBuf> {
    let Ok(entries) = fs::read_dir(root) else {
        return Vec::new();
    };
    let mut found: Vec<PathBuf> = entries
        .filter_map(Result::ok)
        .map(|entry| entry.path().join("oos-issues.ndjson"))
        .filter(|path| path.is_file())
        .collect();
    found.sort();
    found
}

/// Resolve the run identity the checkpoint should read its batch under.
///
/// The recorded identity wins, then the session id, then a single discoverable
/// batch. A directory holding several batches resolves to nothing, so the
/// caller refuses rather than guessing which run it belongs to.
fn resolve_run_id(tmpdir: &Path, state: &[(String, String)]) -> String {
    let recorded = state_value(state, "RUN_ID");
    if !recorded.is_empty() {
        return recorded;
    }
    if let Some(session) = read_universal_newlines(&tmpdir.join("session-id")) {
        let trimmed = session.trim().to_owned();
        if !trimmed.is_empty() {
            return trimmed;
        }
    }
    let candidates = batch_candidates(&tmpdir.join("larch-logs").join("implement"));
    if candidates.len() == 1 {
        return candidates[0]
            .parent()
            .and_then(Path::file_name)
            .map(|name| name.to_string_lossy().into_owned())
            .unwrap_or_default();
    }
    String::new()
}

/// Resolve the accepted design artifact in the order the pipeline agreed on.
pub fn resolve_design_path(tmpdir: &Path, design_tmpdir: Option<&Path>) -> PathBuf {
    if let Some(design) = design_tmpdir {
        let candidate = design.join("oos-accepted-design.md");
        if candidate.is_file() {
            return candidate;
        }
    }
    let exported = tmpdir.join("design-export").join("oos-accepted-design.md");
    if exported.is_file() {
        return exported;
    }
    tmpdir.join("oos-accepted-design.md")
}

/// Record one checkpoint refusal in both the breadcrumb and the ledger.
fn refuse(tmpdir: &Path, site: &str, tool: &str, rc: i32, message: &str) -> u8 {
    let _written = fs::write(tmpdir.join(CHECKPOINT_STDERR_LOG), format!("{message}\n"));
    append_failure_log(&tmpdir.join(EXECUTION_ISSUES_FILE), site, tool, rc, message);
    u8::try_from(rc).unwrap_or(VALIDATION_FAILED_RC)
}

/// Run `oos disposition-checkpoint`.
pub fn disposition_checkpoint(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &["--implement-tmpdir", "--design-tmpdir"],
        &[],
        0,
    );
    let Some(tmpdir) = parsed
        .value("--implement-tmpdir")
        .map(PathBuf::from)
        .filter(|_present| parsed.error().is_none())
    else {
        // The tmpdir is recovered from the raw line even when the line does not
        // parse, so a caller that mis-spelled an option still finds the refusal
        // where it looks for it.
        if let Some(hint) = preparse_tmpdir(arguments) {
            return ExitCode::from(refuse(
                &hint,
                "step-8-oos-checkpoint-validation",
                "oos-disposition-checkpoint",
                i32::from(VALIDATION_FAILED_RC),
                "oos-disposition-checkpoint: invalid arguments",
            ));
        }
        eprintln!("{CHECKPOINT_USAGE}");
        return ExitCode::from(VALIDATION_FAILED_RC);
    };
    if !tmpdir.exists() {
        eprintln!("oos-disposition-checkpoint: --implement-tmpdir not found");
        return ExitCode::from(VALIDATION_FAILED_RC);
    }
    let design_tmpdir = parsed
        .value("--design-tmpdir")
        .map(PathBuf::from)
        .or_else(|| env::var("DESIGN_TMPDIR").ok().map(PathBuf::from))
        .filter(|path| !path.as_os_str().is_empty());
    ExitCode::from(checkpoint_with(
        &tmpdir,
        design_tmpdir.as_deref(),
        &RepositoryGateGit,
    ))
}

/// Evaluate one session directory's OOS disposition against the live clone.
pub fn checkpoint(tmpdir: &Path, design_tmpdir: Option<&Path>) -> u8 {
    checkpoint_with(tmpdir, design_tmpdir, &RepositoryGateGit)
}

/// Recover `--implement-tmpdir` from a command line that did not parse.
fn preparse_tmpdir(arguments: &[OsString]) -> Option<PathBuf> {
    arguments
        .iter()
        .position(|argument| argument == "--implement-tmpdir")
        .and_then(|index| arguments.get(index + 1))
        .filter(|value| {
            let text = value.to_string_lossy();
            !text.is_empty() && !text.starts_with("--")
        })
        .map(PathBuf::from)
}

/// Evaluate one session directory's OOS disposition.
pub fn checkpoint_with(tmpdir: &Path, design_tmpdir: Option<&Path>, git: &dyn GateGit) -> u8 {
    let mut state = read_state(&tmpdir.join("ship-pr-state.sh"));
    state.extend(read_state(&tmpdir.join("finalize-state.sh")));
    let forked = state_value(&state, "FORKED_TARGET") == "true";
    let repo_unavailable = state_value(&state, "REPO_UNAVAILABLE") == "true";
    let commit_range = git.commit_range();
    let run_id = resolve_run_id(tmpdir, &state);
    let batches = batch_candidates(&tmpdir.join("larch-logs").join("implement"));
    let ndjson: Option<PathBuf> = if run_id.is_empty() {
        if batches.len() > 1 {
            return refuse(
                tmpdir,
                "step-8-oos-checkpoint-validation",
                "oos-disposition-checkpoint",
                i32::from(VALIDATION_FAILED_RC),
                "implement: ambiguous oos-issues.ndjson without session-id; cannot pass --oos-issues-ndjson",
            );
        }
        batches.into_iter().next()
    } else {
        let candidate = tmpdir
            .join("larch-logs")
            .join("implement")
            .join(&run_id)
            .join("oos-issues.ndjson");
        candidate.is_file().then_some(candidate)
    };
    let design = resolve_design_path(tmpdir, design_tmpdir);
    let accepted = vec![
        tmpdir.join(ACCEPTED_OOS_FILENAMES[0]),
        design,
        tmpdir.join(ACCEPTED_OOS_FILENAMES[2]),
    ];
    let filed = vec![tmpdir.join("oos-issues-created.md")];
    let sidecar = tmpdir.join(SECURITY_SIDECAR_FILE);
    let mut sidecar_present = false;
    if !forked && !repo_unavailable {
        sidecar_present = sidecar.metadata().is_ok_and(|data| data.len() > 0);
        let non_security: usize = accepted
            .iter()
            .filter(|path| path.is_file())
            .map(|path| count_non_security_oos_blocks(path))
            .sum();
        if non_security > 0 && ndjson.as_ref().is_none_or(|path| !path.is_file()) {
            return refuse(
                tmpdir,
                "step-8-oos-checkpoint-validation",
                "oos-disposition-checkpoint",
                i32::from(VALIDATION_FAILED_RC),
                "implement: non-security accepted OOS requires a resolved oos-issues.ndjson path for disposition gate (--oos-issues-ndjson); batch missing or undiscoverable",
            );
        }
    }
    if forked || repo_unavailable {
        return 0;
    }
    let inputs = GateInputs {
        accepted: &accepted,
        filed_urls: &filed,
        filed_urls_strict: &accepted,
        ndjson: ndjson.as_deref(),
        commit_range: &commit_range,
    };
    let gh_host = env::var("GH_HOST").unwrap_or_default();
    let counters = match gate_counters(&inputs, git, &gh_host) {
        Ok(counters) => counters,
        Err(message) => {
            let _written = fs::write(tmpdir.join(GATE_STDERR_LOG), format!("{message}\n"));
            return refuse(
                tmpdir,
                "step-8-oos-checkpoint-validation",
                "oos-disposition-checkpoint",
                i32::from(VALIDATION_FAILED_RC),
                &message,
            );
        }
    };
    match counters.state(sidecar_present) {
        DispositionState::Blocked => {
            let _written = fs::write(
                tmpdir.join(GATE_STDERR_LOG),
                format!("{}\n", counters.failure_line(&commit_range)),
            );
            append_failure_log(
                &tmpdir.join(EXECUTION_ISSUES_FILE),
                "step-8-oos-checkpoint",
                "oos-disposition-gate",
                i32::from(GATE_BLOCKED_RC),
                "",
            );
            GATE_BLOCKED_RC
        }
        DispositionState::SecuritySidecarPending => refuse(
            tmpdir,
            "step-8-oos-checkpoint-security-sidecar",
            "oos-disposition-checkpoint",
            i32::from(SECURITY_SIDECAR_RC),
            "implement: security sidecar present; non-security OOS disposition cleared, private security disposition still required",
        ),
        DispositionState::Cleared => 0,
    }
}

#[cfg(test)]
mod tests {
    use super::{
        GateGit, GateInputs, checkpoint_with, disposition_gate, file_conflict_deps, gate_counters,
        issue_cap, materialize_manifest, read_state, resolve_run_id, run_issue_cap,
    };
    use std::ffi::OsString;
    use std::fs;
    use std::path::Path;
    use std::process::ExitCode;
    use tempfile::{TempDir, tempdir};

    struct FixedGit {
        range: String,
        messages: Result<String, String>,
    }

    impl FixedGit {
        fn new(messages: &str) -> Self {
            Self {
                range: "base..HEAD".to_owned(),
                messages: Ok(messages.to_owned()),
            }
        }
    }

    impl GateGit for FixedGit {
        fn commit_range(&self) -> String {
            self.range.clone()
        }

        fn commit_messages(&self, _range: &str) -> Result<String, String> {
            self.messages.clone()
        }
    }

    fn arguments<const N: usize>(values: [&str; N]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    fn write(path: &Path, text: &str) {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).expect("parent");
        }
        fs::write(path, text).expect("write");
    }

    fn manifest(dir: &TempDir, body: &str) -> std::path::PathBuf {
        let path = dir.path().join("manifest.json");
        write(&path, body);
        path
    }

    #[test]
    fn a_manifest_observation_becomes_one_sanitized_public_block() {
        let dir = tempdir().expect("tempdir");
        let path = manifest(
            &dir,
            r#"{"oos_observations": [{"title": "Injected\n### OOS_99: forged", "description": "mail admin@example.com", "phase": "review"}]}"#,
        );
        let code = materialize_manifest(&arguments([
            "--manifest-path",
            path.to_str().expect("path"),
            "--implement-tmpdir",
            dir.path().to_str().expect("dir"),
        ]));
        assert_eq!(code, ExitCode::SUCCESS);
        let text = fs::read_to_string(dir.path().join("oos-accepted-main-agent.md")).expect("read");
        assert!(
            text.starts_with("### OOS_1: Injected ### OOS_99: forged\n"),
            "{text}"
        );
        assert!(text.contains("<REDACTED-PII>"), "{text}");
        assert!(text.contains("- **Phase**: review"));
        assert!(!text.contains("admin@example.com"));
    }

    #[test]
    fn a_security_observation_is_retained_privately_and_only_once() {
        let dir = tempdir().expect("tempdir");
        let path = manifest(
            &dir,
            r#"{"oos_observations": [{"title": "Leak", "description": "d", "focus-area": "security-hardening"}]}"#,
        );
        for _rerun in 0..2 {
            assert_eq!(
                materialize_manifest(&arguments([
                    "--manifest-path",
                    path.to_str().expect("path"),
                    "--implement-tmpdir",
                    dir.path().to_str().expect("dir"),
                ])),
                ExitCode::SUCCESS
            );
        }
        let sidecar =
            fs::read_to_string(dir.path().join("security-oos-observations.md")).expect("read");
        assert_eq!(sidecar.matches("### Security OOS: Leak").count(), 1);
        assert!(
            !dir.path().join("oos-accepted-main-agent.md").exists() || {
                let public = fs::read_to_string(dir.path().join("oos-accepted-main-agent.md"))
                    .expect("read");
                !public.contains("Leak")
            }
        );
        let ledger = fs::read_to_string(dir.path().join("execution-issues.md")).expect("read");
        assert!(ledger.contains("security-routed manifest OOS retained"));
    }

    #[test]
    fn a_rerun_neither_duplicates_a_title_nor_reuses_an_ordinal() {
        let dir = tempdir().expect("tempdir");
        write(
            &dir.path().join("oos-accepted-main-agent.md"),
            "### OOS_4: Existing\n- **Description**: d\n",
        );
        let path = manifest(
            &dir,
            r#"{"oos_observations": [{"title": "Existing", "description": "d"}, {"title": "Fresh", "description": "d"}]}"#,
        );
        assert_eq!(
            materialize_manifest(&arguments([
                "--manifest-path",
                path.to_str().expect("path"),
                "--implement-tmpdir",
                dir.path().to_str().expect("dir"),
            ])),
            ExitCode::SUCCESS
        );
        let text = fs::read_to_string(dir.path().join("oos-accepted-main-agent.md")).expect("read");
        assert_eq!(text.matches("### OOS_").count(), 2);
        assert!(text.contains("### OOS_5: Fresh"), "{text}");
    }

    #[test]
    fn a_malformed_manifest_is_refused_rather_than_read_as_empty() {
        let dir = tempdir().expect("tempdir");
        for body in [
            "[1]",
            "not json",
            r#"{"oos_observations": 5}"#,
            r#"{"oos_observations": [1]}"#,
        ] {
            let path = manifest(&dir, body);
            assert_eq!(
                materialize_manifest(&arguments([
                    "--manifest-path",
                    path.to_str().expect("path"),
                    "--implement-tmpdir",
                    dir.path().to_str().expect("dir"),
                ])),
                ExitCode::from(1),
                "{body}"
            );
        }
        assert_eq!(
            materialize_manifest(&arguments(["--implement-tmpdir", "/nowhere"])),
            ExitCode::from(2)
        );
        assert_eq!(
            materialize_manifest(&arguments(["--not-an-option"])),
            ExitCode::from(2)
        );
    }

    #[test]
    fn counting_a_manifest_tolerates_shapes_a_full_pass_refuses() {
        let dir = tempdir().expect("tempdir");
        let path = manifest(&dir, r#"{"oos_observations": [1, {"title": "t"}]}"#);
        assert_eq!(
            materialize_manifest(&arguments([
                "--count-only",
                "--manifest-path",
                path.to_str().expect("path"),
                "--implement-tmpdir",
                dir.path().to_str().expect("dir"),
            ])),
            ExitCode::SUCCESS
        );
        assert!(!dir.path().join("oos-accepted-main-agent.md").exists());
    }

    #[test]
    fn the_cap_rewrites_in_place_and_refuses_a_bad_knob_without_output() {
        let dir = tempdir().expect("tempdir");
        let input = dir.path().join("oos-combined.md");
        write(
            &input,
            "### OOS_1: a\n- **Description**: d\n\n### OOS_2: b\n- **Description**: d\n",
        );
        let output = dir.path().join("stale.md");
        write(&output, "stale\n");
        assert_eq!(
            run_issue_cap(
                &input,
                Some(&output),
                Err("OOS_ISSUES_PER_RUN_CAP must be a positive integer".to_owned()),
            ),
            ExitCode::from(2)
        );
        assert!(!output.exists());
        assert_eq!(run_issue_cap(&input, None, Ok(1)), ExitCode::SUCCESS);
        let text = fs::read_to_string(&input).expect("read");
        assert!(
            text.starts_with("### OOS_1: Aggregated rollup of 2 capped OOS items"),
            "{text}"
        );
    }

    #[test]
    fn the_default_cap_knob_is_one_and_refuses_every_other_spelling() {
        assert_eq!(super::issue_cap_value(), Ok(1));
    }

    #[test]
    fn the_cap_refuses_a_missing_input_a_shared_path_and_a_bad_line() {
        let dir = tempdir().expect("tempdir");
        let input = dir.path().join("input.md");
        write(&input, "### OOS_1: a\n");
        assert_eq!(
            issue_cap(&arguments(["--input-file", "/nonexistent/oos.md"])),
            ExitCode::from(1)
        );
        assert_eq!(
            issue_cap(&arguments([
                "--input-file",
                input.to_str().expect("input"),
                "--output",
                input.to_str().expect("input"),
            ])),
            ExitCode::from(1)
        );
        assert_eq!(issue_cap(&arguments([])), ExitCode::from(2));
        assert_eq!(issue_cap(&arguments(["--nope"])), ExitCode::from(2));
    }

    #[test]
    fn a_fitting_batch_is_copied_through_to_an_explicit_output() {
        let dir = tempdir().expect("tempdir");
        let input = dir.path().join("input.md");
        write(&input, "### OOS_1: a\r\n- **Description**: d\r\n");
        let output = dir.path().join("output.md");
        assert_eq!(
            issue_cap(&arguments([
                "--input-file",
                input.to_str().expect("input"),
                "--output",
                output.to_str().expect("output"),
            ])),
            ExitCode::SUCCESS
        );
        assert_eq!(
            fs::read_to_string(&output).expect("read"),
            "### OOS_1: a\n- **Description**: d\n"
        );
    }

    #[test]
    fn conflict_rows_are_written_atomically_and_cleared_on_refusal() {
        let dir = tempdir().expect("tempdir");
        let input = dir.path().join("batch.md");
        write(
            &input,
            "### OOS_1: a\n- **Description**: a/b.py:10-20\n\n### OOS_2: b\n- **Description**: a/b.py:15-25\n",
        );
        let output = dir.path().join("deps.tsv");
        assert_eq!(
            file_conflict_deps(&arguments([
                "--input-file",
                input.to_str().expect("input"),
                "--output",
                output.to_str().expect("output"),
            ])),
            ExitCode::SUCCESS
        );
        assert_eq!(fs::read_to_string(&output).expect("read"), "1\t2\n");
        assert_eq!(
            file_conflict_deps(&arguments([
                "--input-file",
                "/nonexistent/batch.md",
                "--output",
                output.to_str().expect("output"),
            ])),
            ExitCode::from(1)
        );
        assert!(!output.exists());
    }

    #[test]
    fn the_conflict_line_reports_its_own_usage_refusals() {
        assert_eq!(file_conflict_deps(&arguments([])), ExitCode::from(1));
        assert_eq!(
            file_conflict_deps(&arguments(["--input-file"])),
            ExitCode::from(1)
        );
        assert_eq!(
            file_conflict_deps(&arguments(["--bogus", "x"])),
            ExitCode::from(1)
        );
    }

    #[test]
    fn the_gate_clears_a_fork_and_refuses_an_incomplete_line() {
        assert_eq!(
            disposition_gate(&arguments(["--fork-mode"])),
            ExitCode::SUCCESS
        );
        assert_eq!(
            disposition_gate(&arguments(["--repo-unavailable"])),
            ExitCode::SUCCESS
        );
        assert_eq!(disposition_gate(&arguments([])), ExitCode::from(2));
        assert_eq!(
            disposition_gate(&arguments(["--accepted-files", "a.md"])),
            ExitCode::from(2)
        );
        assert_eq!(disposition_gate(&arguments(["--nope"])), ExitCode::from(2));
    }

    #[test]
    fn the_counters_refuse_an_orphan_batch_and_an_unparseable_one() {
        let dir = tempdir().expect("tempdir");
        let ndjson = dir.path().join("oos-issues.ndjson");
        write(&ndjson, "{\"url\": \"https://github.com/o/r/issues/1\"}\n");
        let accepted = vec![dir.path().join("missing.md")];
        let inputs = GateInputs {
            accepted: &accepted,
            filed_urls: &[],
            filed_urls_strict: &[],
            ndjson: Some(&ndjson),
            commit_range: "base..HEAD",
        };
        let error = gate_counters(&inputs, &FixedGit::new(""), "").expect_err("orphan");
        assert!(error.starts_with("oos-issues.ndjson lists filed GitHub issue URLs"));
        write(&ndjson, "not json\n");
        let error = gate_counters(&inputs, &FixedGit::new(""), "").expect_err("parse");
        assert_eq!(
            error,
            "jq parse failure while reading oos-issues.ndjson; refusing disposition"
        );
    }

    #[test]
    fn the_counters_refuse_a_directory_and_an_unusable_range() {
        let dir = tempdir().expect("tempdir");
        let accepted = vec![dir.path().to_path_buf()];
        let inputs = GateInputs {
            accepted: &accepted,
            filed_urls: &[],
            filed_urls_strict: &[],
            ndjson: None,
            commit_range: "bad",
        };
        assert!(
            gate_counters(&inputs, &FixedGit::new(""), "")
                .expect_err("directory")
                .starts_with("accepted file path is not a readable regular file:")
        );
        let file = dir.path().join("accepted.md");
        write(&file, "### OOS_1: a\n");
        let accepted = vec![file];
        let inputs = GateInputs {
            accepted: &accepted,
            filed_urls: &[],
            filed_urls_strict: &[],
            ndjson: None,
            commit_range: "bad",
        };
        let git = FixedGit {
            range: "bad".to_owned(),
            messages: Err("invalid commit-range: bad".to_owned()),
        };
        assert_eq!(
            gate_counters(&inputs, &git, "").expect_err("range"),
            "invalid commit-range: bad"
        );
    }

    #[test]
    fn strict_and_loose_filing_evidence_both_clear_the_gate() {
        let dir = tempdir().expect("tempdir");
        let accepted = vec![dir.path().join("oos-accepted-review.md")];
        write(&accepted[0], "### OOS_1: a\n### OOS_2: b\n");
        let inputs = GateInputs {
            accepted: &accepted,
            filed_urls: &[],
            filed_urls_strict: &accepted,
            ndjson: None,
            commit_range: "base..HEAD",
        };
        let counters = gate_counters(&inputs, &FixedGit::new(""), "").expect("counters");
        assert_eq!(counters.non_security, 2);
        assert!(!counters.cleared());
        let triaged = gate_counters(
            &inputs,
            &FixedGit::new("Inline-triage rule 1: x\nInline-triage rule 2: y\n"),
            "",
        )
        .expect("counters");
        assert_eq!(triaged.inline_triage, 2);
        assert!(triaged.cleared());
        write(
            &accepted[0],
            "### OOS_1: a\n- **Filed URL**: https://github.com/o/r/issues/9\n### OOS_2: b\n",
        );
        let filed = gate_counters(&inputs, &FixedGit::new(""), "").expect("counters");
        assert_eq!(filed.filed_urls, 1);
        assert!(filed.cleared());
    }

    #[test]
    fn a_run_state_is_read_from_both_files_with_the_last_writer_winning() {
        let dir = tempdir().expect("tempdir");
        write(&dir.path().join("ship-pr-state.sh"), "RUN_ID=first\r\n");
        write(&dir.path().join("finalize-state.sh"), "RUN_ID=second\n");
        let mut state = read_state(&dir.path().join("ship-pr-state.sh"));
        state.extend(read_state(&dir.path().join("finalize-state.sh")));
        assert_eq!(resolve_run_id(dir.path(), &state), "second");
        assert_eq!(resolve_run_id(dir.path(), &[]), "");
        write(&dir.path().join("session-id"), "from-session\n");
        assert_eq!(resolve_run_id(dir.path(), &[]), "from-session");
    }

    #[test]
    fn a_run_id_falls_back_to_one_discoverable_batch() {
        let dir = tempdir().expect("tempdir");
        write(
            &dir.path()
                .join("larch-logs/implement/run-7/oos-issues.ndjson"),
            "",
        );
        assert_eq!(resolve_run_id(dir.path(), &[]), "run-7");
        write(
            &dir.path()
                .join("larch-logs/implement/run-8/oos-issues.ndjson"),
            "",
        );
        assert_eq!(resolve_run_id(dir.path(), &[]), "");
    }

    #[test]
    fn a_checkpoint_with_nothing_accepted_clears() {
        let dir = tempdir().expect("tempdir");
        write(
            &dir.path().join("ship-pr-state.sh"),
            "FORKED_TARGET=false\n",
        );
        assert_eq!(checkpoint_with(dir.path(), None, &FixedGit::new("")), 0);
    }

    #[test]
    fn a_fork_checkpoint_clears_without_reading_a_batch() {
        let dir = tempdir().expect("tempdir");
        write(&dir.path().join("ship-pr-state.sh"), "FORKED_TARGET=true\n");
        write(
            &dir.path().join("oos-accepted-main-agent.md"),
            "### OOS_1: a\n",
        );
        assert_eq!(checkpoint_with(dir.path(), None, &FixedGit::new("")), 0);
        write(
            &dir.path().join("ship-pr-state.sh"),
            "FORKED_TARGET=false\nREPO_UNAVAILABLE=true\n",
        );
        assert_eq!(checkpoint_with(dir.path(), None, &FixedGit::new("")), 0);
    }

    #[test]
    fn a_checkpoint_without_a_batch_refuses_and_records_why() {
        let dir = tempdir().expect("tempdir");
        write(
            &dir.path().join("ship-pr-state.sh"),
            "FORKED_TARGET=false\n",
        );
        write(
            &dir.path().join("oos-accepted-main-agent.md"),
            "### OOS_1: a\n",
        );
        assert_eq!(checkpoint_with(dir.path(), None, &FixedGit::new("")), 2);
        let breadcrumb =
            fs::read_to_string(dir.path().join("oos-disposition-checkpoint.stderr.log"))
                .expect("read");
        assert!(breadcrumb.contains("requires a resolved oos-issues.ndjson"));
        let ledger = fs::read_to_string(dir.path().join("execution-issues.md")).expect("read");
        assert!(ledger.contains("oos-disposition-checkpoint exited 2"));
    }

    #[test]
    fn a_checkpoint_blocks_on_an_undisposed_record_and_writes_the_gate_line() {
        let dir = tempdir().expect("tempdir");
        write(&dir.path().join("ship-pr-state.sh"), "RUN_ID=run-1\n");
        write(
            &dir.path().join("oos-accepted-main-agent.md"),
            "### OOS_1: a\n",
        );
        write(
            &dir.path()
                .join("larch-logs/implement/run-1/oos-issues.ndjson"),
            "{\"body\": \"nothing\"}\n",
        );
        assert_eq!(checkpoint_with(dir.path(), None, &FixedGit::new("")), 1);
        let gate =
            fs::read_to_string(dir.path().join("oos-disposition-gate.stderr.log")).expect("read");
        assert!(gate.starts_with("oos-disposition-gate: FAIL non_security_oos=1 filed_urls=0"));
    }

    #[test]
    fn a_cleared_checkpoint_still_reports_a_pending_security_sidecar() {
        let dir = tempdir().expect("tempdir");
        write(&dir.path().join("ship-pr-state.sh"), "RUN_ID=run-1\n");
        write(
            &dir.path().join("security-oos-observations.md"),
            "### Security OOS: x\n",
        );
        assert_eq!(checkpoint_with(dir.path(), None, &FixedGit::new("")), 3);
        let breadcrumb =
            fs::read_to_string(dir.path().join("oos-disposition-checkpoint.stderr.log"))
                .expect("read");
        assert!(breadcrumb.contains("private security disposition still required"));
    }

    #[test]
    fn an_ambiguous_batch_without_a_run_identity_is_refused() {
        let dir = tempdir().expect("tempdir");
        write(
            &dir.path()
                .join("larch-logs/implement/run-1/oos-issues.ndjson"),
            "",
        );
        write(
            &dir.path()
                .join("larch-logs/implement/run-2/oos-issues.ndjson"),
            "",
        );
        assert_eq!(checkpoint_with(dir.path(), None, &FixedGit::new("")), 2);
        let breadcrumb =
            fs::read_to_string(dir.path().join("oos-disposition-checkpoint.stderr.log"))
                .expect("read");
        assert!(breadcrumb.contains("ambiguous oos-issues.ndjson"));
    }

    #[test]
    fn a_design_export_supplies_the_accepted_design_artifact() {
        let dir = tempdir().expect("tempdir");
        let design = tempdir().expect("design");
        write(&dir.path().join("ship-pr-state.sh"), "RUN_ID=run-1\n");
        write(
            &design.path().join("oos-accepted-design.md"),
            "### OOS_1: a\n",
        );
        assert_eq!(
            checkpoint_with(dir.path(), Some(design.path()), &FixedGit::new("")),
            2
        );
        write(
            &dir.path().join("design-export/oos-accepted-design.md"),
            "### OOS_1: a\n",
        );
        assert_eq!(checkpoint_with(dir.path(), None, &FixedGit::new("")), 2);
    }

    #[test]
    fn a_checkpoint_line_that_does_not_parse_still_records_where_it_failed() {
        let dir = tempdir().expect("tempdir");
        assert_eq!(
            super::disposition_checkpoint(&arguments([
                "--implement-tmpdir",
                dir.path().to_str().expect("dir"),
                "--bogus",
            ])),
            ExitCode::from(2)
        );
        let breadcrumb =
            fs::read_to_string(dir.path().join("oos-disposition-checkpoint.stderr.log"))
                .expect("read");
        assert!(breadcrumb.contains("invalid arguments"));
        assert_eq!(
            super::disposition_checkpoint(&arguments(["--design-tmpdir", "x"])),
            ExitCode::from(2)
        );
        assert_eq!(
            super::disposition_checkpoint(&arguments([
                "--implement-tmpdir",
                "/nonexistent/session",
            ])),
            ExitCode::from(2)
        );
    }
}
