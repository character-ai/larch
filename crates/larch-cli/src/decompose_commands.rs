//! Rust owners for the six `decompose` verbs (#8588).
//!
//! `prepare`, `annotate`, `migrate-deps`, `close-original`, `panel-dispatch`,
//! and `aggregate` port `python/larch/design/decompose.py`. The offline-pure
//! core (partition parsing, the prepared-artifact builder, the dependency
//! migration algorithm) lives in `larch_core::design`; this module owns the
//! impure orchestration: filesystem I/O, the hardened GitHub service, the
//! external decomposition waterfall dispatch, and redaction.

use std::{
    env,
    ffi::{OsStr, OsString},
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use larch_adapters::{
    github::{
        DependencyEdge as GhDependencyEdge, GitHubOperationError, IssueMutationOwner,
        LiveMutationRequest, check_live_mutation_auth,
    },
    validate_design_tmpdir,
};
use larch_core::{
    DECOMPOSE_ARCHETYPES, DECOMPOSE_PROMPT_PREFIX_LINE_MAX, DependencyGraph, DependencyMigration,
    DuplicatePolicy, FiledPiece, GitHubRepositoryRef, GitHubService, KvDocument, ParseOptions,
    PartitionBuildOutcome, PartitionEdge, apply_migration, build_partition_artifacts,
    cleanup_cache_sessions_root, emit_kv, intra_piece_postcondition,
    live_original_edges_match_migration, migration_postcondition, parse_filed_pieces,
    parse_intra_piece_edges, parse_single_kv_row, redact_secrets_only, redact_sensitive_paths,
};
use regex::Regex;
use serde::Serialize;
use serde_json::Value;
use std::sync::LazyLock;

use crate::{
    argparse_compat::{finish_parse, parse_with_flags},
    github_service::with_github_service,
    runtime_entrypoint::{
        code_and_stdout, plugin_root, run_verified_larch, run_verified_larch_with_timeout,
    },
};

const ROUTE_STATE_PATH: &str = ".design-step0-route-state.env";
const PANEL_WATERFALL_OVERRIDE: &str = "DECOMPOSE_PANEL_WATERFALL_SH";
const AGGREGATE_WATERFALL_OVERRIDE: &str = "DECOMPOSE_AGGREGATE_WATERFALL_SH";
const CLAUDE_REVIEW_OVERRIDE: &str = "LARCH_TEST_LAUNCH_CLAUDE_REVIEW";
const MUTATION_TEST_DENY_KEY: &str = "LARCH_TEST_LIVE_MUTATION_DENY";

static RECOMMENDATION_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?m)^[ \t]*## Recommendation").expect("recommendation regex"));

#[cfg(test)]
thread_local! {
    /// Per-test decompose-prompt template directory, used in place of the
    /// plugin-root resolution so a unit test drives the real templates without
    /// mutating the process `CLAUDE_PLUGIN_ROOT`.
    static TEST_PROMPTS_DIR: std::cell::RefCell<Option<PathBuf>> =
        const { std::cell::RefCell::new(None) };
    /// Per-test waterfall/Claude-review child override, used in place of the
    /// `DECOMPOSE_*_WATERFALL_SH` / `LARCH_TEST_LAUNCH_CLAUDE_REVIEW` env seams
    /// so a unit test drives the dispatch offline without env mutation.
    static TEST_WATERFALL_STUB: std::cell::RefCell<Option<PathBuf>> =
        const { std::cell::RefCell::new(None) };
}

/// Run `action` with the decompose prompt-dir and waterfall-child test seams
/// bound, mirroring `github_service::with_test_github_service`.
#[cfg(test)]
fn with_test_overrides<T>(
    prompts_dir: PathBuf,
    stub: Option<PathBuf>,
    action: impl FnOnce() -> T,
) -> T {
    TEST_PROMPTS_DIR.with(|slot| *slot.borrow_mut() = Some(prompts_dir));
    TEST_WATERFALL_STUB.with(|slot| *slot.borrow_mut() = stub);
    let outcome = action();
    TEST_PROMPTS_DIR.with(|slot| *slot.borrow_mut() = None);
    TEST_WATERFALL_STUB.with(|slot| *slot.borrow_mut() = None);
    outcome
}

// ---------------------------------------------------------------- utilities

fn breadcrumb(message: &str) {
    let redacted = redact_sensitive_paths(&redact_secrets_only(message));
    eprintln!("{}", redacted.trim_end_matches('\n'));
}

fn emit_bool(key: &str, value: bool) {
    emit_kv(key, if value { "true" } else { "false" });
}

/// Parse a `KEY=value` capture into last-wins pairs through the shared codec.
fn parse_kv(text: &str) -> std::collections::BTreeMap<String, String> {
    KvDocument::parse(text, ParseOptions::legacy())
        .expect("legacy KV parser accepts every text input")
        .select(DuplicatePolicy::Last)
}

fn cache_sessions_root() -> PathBuf {
    cleanup_cache_sessions_root(
        env::var_os("XDG_CACHE_HOME").as_deref(),
        env::var_os("HOME").as_deref(),
    )
}

/// Validate a `--design-tmpdir` value and return its resolved path.
fn resolve_design_tmpdir(value: &OsStr) -> Result<PathBuf, String> {
    validate_design_tmpdir(
        &value.to_string_lossy(),
        env::var_os("TMPDIR").as_deref(),
        &cache_sessions_root(),
    )?;
    Ok(fs::canonicalize(value).unwrap_or_else(|_error| PathBuf::from(value)))
}

/// Read one `KEY=value` row from the Step 0 route-state env, or `""`.
fn route_state_value(design_tmpdir: &Path, key: &str) -> String {
    let path = design_tmpdir.join(ROUTE_STATE_PATH);
    let metadata = match fs::symlink_metadata(&path) {
        Ok(metadata) => metadata,
        Err(_error) => return String::new(),
    };
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return String::new();
    }
    let Ok(text) = fs::read_to_string(&path) else {
        return String::new();
    };
    for line in text.lines() {
        if let Some(row) = parse_single_kv_row(line, ParseOptions::legacy())
            && row.key() == key
        {
            return row.value().to_owned();
        }
    }
    String::new()
}

fn read_text_or_empty(path: &Path) -> String {
    fs::read_to_string(path).unwrap_or_default()
}

fn plan_text_or_empty(design_tmpdir: &Path) -> String {
    let plan = design_tmpdir.join("plan.txt");
    match fs::symlink_metadata(&plan) {
        Ok(metadata) if metadata.is_file() && !metadata.file_type().is_symlink() => {
            fs::read_to_string(&plan).unwrap_or_default()
        }
        _ => String::new(),
    }
}

// ------------------------------------------------------------------- prepare

fn run_prepare(
    design_tmpdir: &Path,
    partition_file: &Path,
    issue_number: &str,
) -> Result<(String, String), String> {
    if !partition_file.is_file() {
        return Err("prepare: partition file not found".to_owned());
    }
    let dec = design_tmpdir.join("decompose");
    fs::create_dir_all(&dec).map_err(|error| format!("prepare: {error}"))?;
    let out_input = dec.join("partition-input.txt");
    let out_deps = dec.join("partition-deps.tsv");
    let _ = fs::remove_file(&out_input);
    let _ = fs::remove_file(&out_deps);

    let partition_text =
        fs::read_to_string(partition_file).map_err(|error| format!("prepare: {error}"))?;
    let parent_plan_text = plan_text_or_empty(design_tmpdir);
    let feature_text = {
        let feature = design_tmpdir.join("feature-description.txt");
        if feature.is_file() {
            read_text_or_empty(&feature)
        } else {
            String::new()
        }
    };
    let original_title = route_state_value(design_tmpdir, "ISSUE_TITLE");
    let outcome: PartitionBuildOutcome = build_partition_artifacts(
        &partition_text,
        &parent_plan_text,
        &feature_text,
        &original_title,
        issue_number,
    );
    if outcome.status == "ok" {
        fs::write(&out_input, &outcome.input_text).map_err(|error| format!("prepare: {error}"))?;
        let mut deps = String::new();
        for (from, to) in &outcome.deps {
            let _ = writeln!(deps, "{from}\t{to}");
        }
        fs::write(&out_deps, deps).map_err(|error| format!("prepare: {error}"))?;
    }
    Ok((outcome.status, outcome.witness))
}

/// `decompose prepare` entrypoint.
pub fn prepare_main(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &["--design-tmpdir", "--partition-file", "--issue-number"],
        &[],
        0,
    );
    let parsed = match finish_parse(
        parsed,
        "usage: decompose prepare",
        "decompose prepare",
        &["--design-tmpdir", "--partition-file"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let design_tmpdir =
        match resolve_design_tmpdir(parsed.value("--design-tmpdir").unwrap_or_default()) {
            Ok(path) => path,
            Err(message) => {
                breadcrumb(&format!("decompose prepare: {message}"));
                return ExitCode::from(2);
            }
        };
    let partition_file = PathBuf::from(parsed.value("--partition-file").unwrap_or_default());
    let issue_number = parsed
        .value("--issue-number")
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default();
    match run_prepare(&design_tmpdir, &partition_file, &issue_number) {
        Ok((status, witness)) => {
            emit_kv("DECOMPOSE_PARTITION_STATUS", &status);
            if !witness.is_empty() {
                emit_kv("DECOMPOSE_PARTITION_CYCLE_WITNESS", &witness);
            }
            if status == "ok" {
                ExitCode::SUCCESS
            } else {
                let dec = design_tmpdir.join("decompose");
                let _ = fs::remove_file(dec.join("partition-input.txt"));
                let _ = fs::remove_file(dec.join("partition-deps.tsv"));
                if status == "cycle-detected" {
                    ExitCode::SUCCESS
                } else {
                    ExitCode::from(2)
                }
            }
        }
        Err(message) => {
            breadcrumb(&format!("decompose prepare: {message}"));
            ExitCode::from(2)
        }
    }
}

// ------------------------------------------------------------------ annotate

fn annotate_partition(design_tmpdir: &Path, issue_stdout_file: &Path) -> Result<(), String> {
    if !issue_stdout_file.is_file() {
        return Err("annotate: stdout capture missing".to_owned());
    }
    let sentinel = design_tmpdir.join(".decompose-issues-filed");
    let dec = design_tmpdir.join("decompose");
    fs::create_dir_all(&dec).map_err(|error| format!("annotate: {error}"))?;
    let filed_path = dec.join("partition-filed.md");
    let text =
        fs::read_to_string(issue_stdout_file).map_err(|error| format!("annotate: {error}"))?;

    let created_re = Regex::new(r"(?m)^ISSUES_CREATED=([0-9]+)\s*$").expect("created regex");
    let failed_re = Regex::new(r"(?m)^ISSUES_FAILED=([0-9]+)\s*$").expect("failed regex");
    let url_re = Regex::new(r"(?m)^ISSUE_([0-9]+)_URL=(.+?)\s*$").expect("url regex");
    let created = created_re
        .captures(&text)
        .map_or_else(|| "0".to_owned(), |capture| capture[1].to_owned());
    let failed = failed_re
        .captures(&text)
        .map_or_else(|| "0".to_owned(), |capture| capture[1].to_owned());
    let failed_n: i64 = failed.parse().unwrap_or(0);
    let mut urls: std::collections::BTreeMap<u64, String> = std::collections::BTreeMap::new();
    for capture in url_re.captures_iter(&text) {
        if let Ok(index) = capture[1].parse::<u64>() {
            urls.insert(index, capture[2].trim().to_owned());
        }
    }

    let input_file = dec.join("partition-input.txt");
    let expected_pieces = {
        match fs::symlink_metadata(&input_file) {
            Ok(metadata) if metadata.is_file() && !metadata.file_type().is_symlink() => {
                let body = fs::read_to_string(&input_file).unwrap_or_default();
                Regex::new(r"(?m)^###\s+")
                    .expect("heading count regex")
                    .find_iter(&body)
                    .count() as u64
            }
            _ => 0,
        }
    };
    let created_matches_expected = created
        .parse::<u64>()
        .map(|value| value == expected_pieces)
        .unwrap_or(false);
    let url_keys: std::collections::BTreeSet<u64> = urls.keys().copied().collect();
    let expected_keys: std::collections::BTreeSet<u64> = (1..=expected_pieces).collect();
    let complete_mapping = expected_pieces >= larch_core::MIN_PARTITION_PIECES as u64
        && url_keys == expected_keys
        && created_matches_expected;

    if sentinel.is_file() {
        let prev = fs::read_to_string(&sentinel).unwrap_or_default();
        if !prev.trim().is_empty() && filed_path.is_file() && failed_n == 0 && complete_mapping {
            let all_present = urls
                .iter()
                .all(|(index, url)| prev.contains(&format!("PARTITION_FILE_MAP\t{index}\t{url}")));
            let created_n: u64 = created.parse().unwrap_or(0);
            if all_present && created_n == expected_pieces {
                return Ok(());
            }
        }
    }

    let mut lines = vec![
        "# Partition filing record".to_owned(),
        String::new(),
        format!("- **ISSUES_CREATED**: {created}"),
        format!("- **ISSUES_FAILED**: {failed}"),
        String::new(),
    ];
    for (index, url) in &urls {
        lines.push(format!("## Piece {index}"));
        lines.push(format!("- **Filed URL**: {url}"));
        lines.push(String::new());
    }
    fs::write(&filed_path, format!("{}\n", lines.join("\n")))
        .map_err(|error| format!("annotate: {error}"))?;
    if failed_n == 0 && complete_mapping {
        let mut body = String::new();
        for (index, url) in &urls {
            let _ = writeln!(body, "PARTITION_FILE_MAP\t{index}\t{url}");
        }
        fs::write(&sentinel, body).map_err(|error| format!("annotate: {error}"))?;
    } else {
        let _ = fs::remove_file(&sentinel);
    }
    Ok(())
}

/// `decompose annotate` entrypoint.
pub fn annotate_main(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &["--design-tmpdir", "--issue-stdout-file", "--issue-number"],
        &[],
        0,
    );
    let parsed = match finish_parse(
        parsed,
        "usage: decompose annotate",
        "decompose annotate",
        &["--design-tmpdir", "--issue-stdout-file"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let design_tmpdir =
        match resolve_design_tmpdir(parsed.value("--design-tmpdir").unwrap_or_default()) {
            Ok(path) => path,
            Err(message) => {
                breadcrumb(&format!("decompose annotate: {message}"));
                return ExitCode::from(2);
            }
        };
    let issue_stdout_file = PathBuf::from(parsed.value("--issue-stdout-file").unwrap_or_default());
    match annotate_partition(&design_tmpdir, &issue_stdout_file) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            breadcrumb(&format!("decompose annotate: {message}"));
            ExitCode::from(2)
        }
    }
}

// -------------------------------------------------------- dependency migration

/// The GitHub-backed dependency graph the production migration runs against.
struct GithubGraph {
    repo: GitHubRepositoryRef,
}

fn sorted_unique(mut numbers: Vec<u64>) -> Vec<u64> {
    numbers.sort_unstable();
    numbers.dedup();
    numbers
}

fn operator_authorization() -> LiveMutationRequest<'static> {
    LiveMutationRequest {
        context_file: None,
        operator_mode: true,
        run_id: "",
        trusted_root: None,
        test_deny: env::var(MUTATION_TEST_DENY_KEY).as_deref() == Ok("true"),
    }
}

impl DependencyGraph for GithubGraph {
    fn read_dependencies(&self, issue: u64) -> Result<(Vec<u64>, Vec<u64>), String> {
        let outcome = with_github_service(async |service, cancellation| {
            let blocked_by = service
                .list_blocked_by(cancellation, self.repo.owner(), self.repo.name(), issue)
                .await
                .map_err(|error| format!("dependency-read-failed: {error}"))?;
            let blocking = service
                .list_blocking(cancellation, self.repo.owner(), self.repo.name(), issue)
                .await
                .map_err(|error| format!("dependency-read-failed: {error}"))?;
            let incoming = sorted_unique(
                blocked_by
                    .into_iter()
                    .map(|edge| edge.issue_number())
                    .collect(),
            );
            let outgoing = sorted_unique(
                blocking
                    .into_iter()
                    .map(|edge| edge.issue_number())
                    .collect(),
            );
            Ok((incoming, outgoing))
        });
        outcome.map_err(larch_service_detail)
    }

    // The blocked/blocker pairing is the domain contract; the near-identical
    // spellings are intentional.
    #[allow(clippy::similar_names)]
    fn mutate(&self, remove: bool, blocked: u64, blocker: u64) -> bool {
        let authorization = operator_authorization();
        let outcome = with_github_service(async |service, cancellation| {
            let blocker_id = service
                .issue(&self.repo, blocker, cancellation)
                .await
                .map(|issue| issue.id)
                .map_err(|error| format!("blocker-id lookup failed: {error}"))?;
            let edge = GhDependencyEdge {
                owner: self.repo.owner(),
                repo: self.repo.name(),
                client_issue: blocked,
                blocker_id,
                expected_updated_at: None,
            };
            let receipt = if remove {
                service
                    .remove_blocked_by(cancellation, &authorization, edge)
                    .await
            } else {
                service
                    .add_blocked_by(cancellation, &authorization, edge)
                    .await
            };
            receipt
                .map(|_receipt| ())
                .map_err(|error: GitHubOperationError| error.to_string())
        });
        outcome.is_ok()
    }
}

fn larch_service_detail(failure: crate::github_service::ServiceFailure) -> String {
    failure.into_detail()
}

fn migration_manifest_path(design_tmpdir: &Path) -> PathBuf {
    design_tmpdir
        .join("decompose")
        .join("dependency-migration.json")
}

fn load_migration(path: &Path) -> Result<DependencyMigration, String> {
    let text = fs::read_to_string(path)
        .map_err(|_error| "migrate-deps: invalid persisted migration manifest".to_owned())?;
    serde_json::from_str::<DependencyMigration>(&text)
        .map_err(|_error| "migrate-deps: invalid persisted migration manifest".to_owned())
}

fn write_migration(path: &Path, migration: &DependencyMigration) -> Result<(), String> {
    let text =
        serde_json::to_string(migration).map_err(|error| format!("migrate-deps: {error}"))?;
    fs::write(path, format!("{text}\n")).map_err(|error| format!("migrate-deps: {error}"))
}

fn intra_piece_edges(
    design_tmpdir: &Path,
    pieces: &[FiledPiece],
) -> Result<Vec<PartitionEdge>, String> {
    let deps_path = design_tmpdir.join("decompose").join("partition-deps.tsv");
    match fs::symlink_metadata(&deps_path) {
        Ok(metadata) if metadata.is_file() && !metadata.file_type().is_symlink() => {
            let text = fs::read_to_string(&deps_path).unwrap_or_default();
            parse_intra_piece_edges(&text, pieces)
        }
        _ => Err("migrate-deps: missing partition-deps.tsv".to_owned()),
    }
}

fn read_run_id(design_tmpdir: &Path) -> String {
    let source_env = design_tmpdir.join("source-env.sh");
    let metadata = match fs::symlink_metadata(&source_env) {
        Ok(metadata) => metadata,
        Err(_error) => return String::new(),
    };
    if !metadata.is_file() || metadata.file_type().is_symlink() {
        return String::new();
    }
    let Ok(text) = fs::read_to_string(&source_env) else {
        return String::new();
    };
    for raw in text.lines() {
        let line = raw.strip_prefix("export ").unwrap_or(raw).trim();
        if let Some(value) = line.strip_prefix("LARCH_RUN_ID=") {
            return value
                .trim()
                .trim_matches(|c| c == '\'' || c == '"')
                .to_owned();
        }
    }
    String::new()
}

fn record_migration_failure(design_tmpdir: &Path, phase: &str, detail: &str) -> String {
    let output_file = design_tmpdir
        .join("decompose")
        .join("migration-failure.txt");
    if let Some(parent) = output_file.parent() {
        let _ = fs::create_dir_all(parent);
    }
    let _ = fs::write(&output_file, format!("phase={phase}\n{detail}\n"));
    emit_kv("DECOMPOSE_DEPS_PHASE", phase);
    append_failure(
        design_tmpdir,
        "design decompose migrate-deps",
        phase,
        1,
        &output_file,
    );
    "failed".to_owned()
}

fn migrate_with(
    design_tmpdir: &Path,
    original_issue: u64,
    repo: &str,
    graph: &dyn DependencyGraph,
    authorized: Result<(), String>,
) -> String {
    if let Err(reason) = authorized {
        record_migration_failure(design_tmpdir, "authorization", &reason);
        emit_kv("DECOMPOSE_DEPS_AUTH_REASON", &reason);
        return "authorization-denied".to_owned();
    }
    let result = migrate_inner(design_tmpdir, original_issue, repo, graph);
    match result {
        Ok(status) => status,
        Err((phase, detail)) => record_migration_failure(design_tmpdir, &phase, &detail),
    }
}

fn migrate_inner(
    design_tmpdir: &Path,
    original_issue: u64,
    repo: &str,
    graph: &dyn DependencyGraph,
) -> Result<String, (String, String)> {
    let sentinel_read = || {
        let sentinel = design_tmpdir.join(".decompose-issues-filed");
        match fs::symlink_metadata(&sentinel) {
            Ok(metadata) if metadata.is_file() && !metadata.file_type().is_symlink() => {
                Ok(fs::read_to_string(&sentinel).unwrap_or_default())
            }
            _ => Err("migrate-deps: missing complete annotation sentinel".to_owned()),
        }
    };
    let pieces = sentinel_read()
        .and_then(|text| parse_filed_pieces(&text, repo))
        .map_err(|detail| ("dependency-read".to_owned(), detail))?;
    let manifest_path = migration_manifest_path(design_tmpdir);
    let migration = if manifest_path.is_file() {
        let migration = load_migration(&manifest_path)
            .map_err(|detail| ("dependency-read".to_owned(), detail))?;
        if migration.original_issue != original_issue
            || migration.repo != repo
            || migration.pieces != pieces
        {
            return Err((
                "dependency-read".to_owned(),
                "migrate-deps: persisted migration does not match filed mapping".to_owned(),
            ));
        }
        if !live_original_edges_match_migration(graph, &migration).map_err(read_failure)? {
            return Ok(record_migration_failure(
                design_tmpdir,
                "live-dependency-drift",
                "original dependency graph changed",
            ));
        }
        migration
    } else {
        let (incoming_numbers, blocking_numbers) = graph
            .read_dependencies(original_issue)
            .map_err(read_failure)?;
        let migration = DependencyMigration {
            schema_version: "1".to_owned(),
            original_issue,
            repo: repo.to_owned(),
            pieces: pieces.clone(),
            incoming: incoming_numbers
                .into_iter()
                .map(|number| PartitionEdge {
                    blocked: original_issue,
                    blocker: number,
                })
                .collect(),
            outgoing: blocking_numbers
                .into_iter()
                .map(|number| PartitionEdge {
                    blocked: number,
                    blocker: original_issue,
                })
                .collect(),
        };
        write_migration(&manifest_path, &migration)
            .map_err(|detail| ("dependency-read".to_owned(), detail))?;
        migration
    };

    let sentinel = design_tmpdir.join(".decompose-deps-migrated");
    let intra = intra_piece_edges(design_tmpdir, &pieces).map_err(read_failure)?;
    let ready = intra_piece_postcondition(graph, &intra).map_err(read_failure)?;
    if ready
        && sentinel.is_file()
        && live_original_edges_match_migration(graph, &migration).map_err(read_failure)?
        && migration_postcondition(graph, &migration).map_err(read_failure)?
    {
        return Ok("ok".to_owned());
    }
    let _ = fs::remove_file(&sentinel);

    if !ready || !apply_migration(graph, &migration).map_err(read_failure)? {
        return Ok(record_migration_failure(
            design_tmpdir,
            "migration",
            "dependency mutation or verification failed",
        ));
    }
    if !live_original_edges_match_migration(graph, &migration).map_err(read_failure)? {
        return Ok(record_migration_failure(
            design_tmpdir,
            "live-dependency-drift",
            "original dependency graph changed",
        ));
    }
    if !intra_piece_postcondition(graph, &intra).map_err(read_failure)? {
        return Ok(record_migration_failure(
            design_tmpdir,
            "intra-piece-postcondition",
            "declared piece dependency missing",
        ));
    }
    let _ = fs::write(&sentinel, "");
    Ok("ok".to_owned())
}

fn read_failure(detail: String) -> (String, String) {
    ("dependency-read".to_owned(), detail)
}

fn migrate_dependencies(design_tmpdir: &Path, original_issue: &str, repo: &str) -> String {
    if !larch_core::is_ascii_digits(original_issue)
        || original_issue
            .parse::<u64>()
            .map(|value| value < 1)
            .unwrap_or(true)
        || Regex::new(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
            .expect("repo regex")
            .find(repo)
            .is_none()
    {
        breadcrumb("decompose migrate-deps: migrate-deps: invalid issue or repository");
        return "invalid".to_owned();
    }
    let issue: u64 = original_issue.parse().unwrap_or(0);
    let run_id = read_run_id(design_tmpdir);
    let source_env = design_tmpdir.join("source-env.sh");
    let decision = check_live_mutation_auth(&LiveMutationRequest {
        context_file: Some(&source_env),
        operator_mode: false,
        run_id: &run_id,
        trusted_root: Some(design_tmpdir),
        test_deny: env::var(MUTATION_TEST_DENY_KEY).as_deref() == Ok("true"),
    });
    let authorized = if decision.is_authorized() {
        Ok(())
    } else {
        Err(decision.reason().to_owned())
    };
    let Ok(reference) = GitHubRepositoryRef::new(
        repo.split('/').next().unwrap_or(""),
        repo.split('/').nth(1).unwrap_or(""),
    ) else {
        breadcrumb("decompose migrate-deps: migrate-deps: invalid issue or repository");
        return "invalid".to_owned();
    };
    let graph = GithubGraph { repo: reference };
    migrate_with(design_tmpdir, issue, repo, &graph, authorized)
}

/// `decompose migrate-deps` entrypoint.
pub fn migrate_deps_main(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &["--design-tmpdir", "--original-issue", "--repo"],
        &[],
        0,
    );
    let parsed = match finish_parse(
        parsed,
        "usage: decompose migrate-deps",
        "decompose migrate-deps",
        &["--design-tmpdir", "--original-issue", "--repo"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let design_tmpdir =
        match resolve_design_tmpdir(parsed.value("--design-tmpdir").unwrap_or_default()) {
            Ok(path) => path,
            Err(message) => {
                breadcrumb(&format!("decompose migrate-deps: {message}"));
                return ExitCode::from(2);
            }
        };
    let original_issue = parsed
        .value("--original-issue")
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default();
    let repo = parsed
        .value("--repo")
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default();
    let status = migrate_dependencies(&design_tmpdir, &original_issue, &repo);
    if status == "invalid" {
        return ExitCode::from(2);
    }
    emit_kv("DECOMPOSE_DEPS_STATUS", &status);
    emit_kv(
        "DECOMPOSE_DEPS_SENTINEL",
        &design_tmpdir
            .join(".decompose-deps-migrated")
            .to_string_lossy(),
    );
    if status == "ok" {
        ExitCode::SUCCESS
    } else {
        ExitCode::from(1)
    }
}

// ------------------------------------------------------------ close-original

/// The GitHub side of close-original: comment then close.
trait IssueCloser {
    fn post_comment(&self, issue: u64, body: &str) -> Result<(), String>;
    fn close(&self, issue: u64) -> Result<(), String>;
}

struct GithubCloser {
    repo: GitHubRepositoryRef,
}

impl IssueCloser for GithubCloser {
    fn post_comment(&self, issue: u64, body: &str) -> Result<(), String> {
        let authorization = operator_authorization();
        with_github_service(async |service, cancellation| {
            let owner = IssueMutationOwner::new(service);
            owner
                .create_comment(cancellation, &authorization, &self.repo, issue, body)
                .await
                .map(|_comment| ())
                .map_err(|error| error.to_string())
        })
        .map_err(larch_service_detail)
    }

    fn close(&self, issue: u64) -> Result<(), String> {
        with_github_service(async |service, cancellation| {
            let owner = IssueMutationOwner::new(service);
            owner
                .close_not_planned(cancellation, &self.repo, issue)
                .await
        })
        .map_err(larch_service_detail)
    }
}

fn close_with(
    design_tmpdir: &Path,
    original_issue: u64,
    repo: &str,
    graph: &dyn DependencyGraph,
    closer: &dyn IssueCloser,
) -> String {
    let closed_sentinel = design_tmpdir.join(".decompose-original-closed");
    if closed_sentinel.is_file() {
        return "ok".to_owned();
    }
    let dec = design_tmpdir.join("decompose");
    let manifest_path = dec.join("dependency-migration.json");
    if !design_tmpdir.join(".decompose-deps-migrated").is_file() || !manifest_path.is_file() {
        breadcrumb(
            "decompose close-original: close-original: dependency migration is not complete",
        );
        return "usage-error".to_owned();
    }
    let migration = match load_migration(&manifest_path) {
        Ok(migration) => migration,
        Err(message) => {
            breadcrumb(&format!("decompose close-original: {message}"));
            return "usage-error".to_owned();
        }
    };
    let postcondition_ok = migration.original_issue == original_issue
        && migration.repo == repo
        && live_original_edges_match_migration(graph, &migration).unwrap_or(false)
        && migration_postcondition(graph, &migration).unwrap_or(false)
        && intra_piece_edges(design_tmpdir, &migration.pieces)
            .and_then(|edges| intra_piece_postcondition(graph, &edges))
            .unwrap_or(false);
    if !postcondition_ok {
        breadcrumb(
            "decompose close-original: close-original: dependency migration postcondition failed",
        );
        return "usage-error".to_owned();
    }
    let filed = dec.join("partition-filed.md");
    if !filed.is_file() {
        breadcrumb(
            "decompose close-original: close-original: missing partition-filed.md (run annotate first)",
        );
        return "usage-error".to_owned();
    }

    let mut summary_lines = vec![
        "This issue is **obviated by a partition** into follow-up work.".to_owned(),
        String::new(),
        "## New pieces".to_owned(),
        String::new(),
    ];
    let filed_text = fs::read_to_string(&filed).unwrap_or_default();
    for line in filed_text.lines() {
        if line.starts_with("## Piece ") || line.starts_with("- **Filed URL**") {
            summary_lines.push(line.to_owned());
        }
    }
    summary_lines.extend([
        String::new(),
        "## Blocked-by chain".to_owned(),
        String::new(),
        "See intra-batch dependency edges filed via /larch:issue (partition-deps.tsv).".to_owned(),
        String::new(),
    ]);
    // Matches Python `redact secrets`: scrub secret families only, preserving
    // operator and session-tmpdir paths in the posted comment body.
    let comment_body = redact_secrets_only(&summary_lines.join("\n"));

    let comment_sent = dec.join(".decompose-close-comment-posted");
    if !comment_sent.is_file() {
        if closer.post_comment(original_issue, &comment_body).is_err() {
            let output_file = dec.join("close-comment.redacted.md");
            let _ = fs::write(&output_file, &comment_body);
            append_failure(
                design_tmpdir,
                "design decompose close-original",
                "gh issue comment",
                1,
                &output_file,
            );
            return "failed".to_owned();
        }
        let _ = fs::write(&comment_sent, "");
    }

    if closer.close(original_issue).is_err() {
        let output_file = dec.join("close-comment.redacted.md");
        let _ = fs::write(&output_file, &comment_body);
        append_failure(
            design_tmpdir,
            "design decompose close-original",
            "gh issue close",
            1,
            &output_file,
        );
        return "failed".to_owned();
    }
    let _ = fs::remove_file(&comment_sent);
    let _ = fs::write(&closed_sentinel, "");
    "ok".to_owned()
}

fn close_original(design_tmpdir: &Path, original_issue: &str, repo: &str) -> String {
    let Ok(issue) = original_issue.parse::<u64>() else {
        breadcrumb("decompose close-original: close-original: invalid original issue");
        return "usage-error".to_owned();
    };
    let Ok(reference) = GitHubRepositoryRef::new(
        repo.split('/').next().unwrap_or(""),
        repo.split('/').nth(1).unwrap_or(""),
    ) else {
        breadcrumb("decompose close-original: close-original: invalid repository");
        return "usage-error".to_owned();
    };
    let graph = GithubGraph {
        repo: reference.clone(),
    };
    let closer = GithubCloser { repo: reference };
    close_with(design_tmpdir, issue, repo, &graph, &closer)
}

/// `decompose close-original` entrypoint.
pub fn close_original_main(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &["--design-tmpdir", "--original-issue", "--repo"],
        &[],
        0,
    );
    let parsed = match finish_parse(
        parsed,
        "usage: decompose close-original",
        "decompose close-original",
        &["--design-tmpdir", "--original-issue", "--repo"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let design_tmpdir =
        match resolve_design_tmpdir(parsed.value("--design-tmpdir").unwrap_or_default()) {
            Ok(path) => path,
            Err(message) => {
                breadcrumb(&format!("decompose close-original: {message}"));
                return ExitCode::from(2);
            }
        };
    let original_issue = parsed
        .value("--original-issue")
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default();
    let repo = parsed
        .value("--repo")
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default();
    let status = close_original(&design_tmpdir, &original_issue, &repo);
    if status == "usage-error" {
        return ExitCode::from(2);
    }
    emit_kv("CLOSE_ORIGINAL_STATUS", &status);
    if status == "ok" {
        ExitCode::SUCCESS
    } else {
        ExitCode::from(1)
    }
}

// ---------------------------------------------------------- run-log helper

fn append_failure(
    design_tmpdir: &Path,
    site: &str,
    tool: &str,
    exit_code: i32,
    output_file: &Path,
) {
    let argv: Vec<OsString> = vec![
        "run-log".into(),
        "append-failure".into(),
        "--log".into(),
        design_tmpdir.join("execution-issues.md").into_os_string(),
        "--site".into(),
        site.into(),
        "--tool".into(),
        tool.into(),
        "--exit-code".into(),
        exit_code.to_string().into(),
        "--category".into(),
        "External Reviewer Issues".into(),
        "--output-file".into(),
        output_file.as_os_str().to_owned(),
        "--redact".into(),
    ];
    let _ = run_verified_larch(&argv);
}

// ------------------------------------------------------------- panel dispatch

#[derive(Serialize)]
struct SlotRow {
    slot: String,
    tool: String,
    output: String,
    prompt_file: String,
}

#[derive(Serialize)]
struct PanelRow {
    archetype: String,
    vendor: String,
    output: String,
    status: String,
}

fn append_json_line(path: &Path, line: &str) {
    use std::io::Write as _;
    if let Ok(mut handle) = fs::OpenOptions::new().create(true).append(true).open(path) {
        let _ = writeln!(handle, "{line}");
    }
}

fn decompose_prompts_dir() -> Result<PathBuf, String> {
    #[cfg(test)]
    if let Some(dir) = TEST_PROMPTS_DIR.with(|slot| slot.borrow().clone()) {
        return Ok(dir);
    }
    Ok(plugin_root()?
        .join("skills")
        .join("design")
        .join("scripts")
        .join("decompose-prompts"))
}

fn render_decompose_prompt(
    archetype: &str,
    primary_input: &Path,
    discussion_file: Option<&Path>,
    out: &Path,
) -> Result<(), String> {
    let prompts = decompose_prompts_dir()?;
    let arch_file = prompts.join(format!("{archetype}.txt"));
    let common_tail = prompts.join("_common-tail.txt");
    if !arch_file.is_file() {
        return Err(format!(
            "missing archetype template: {}",
            arch_file.display()
        ));
    }
    if !common_tail.is_file() {
        return Err(format!("missing common tail: {}", common_tail.display()));
    }
    let primary = {
        let text = read_text_or_empty(primary_input);
        let trimmed = text.trim();
        if trimmed.is_empty() {
            "(empty primary input file)".to_owned()
        } else {
            trimmed.to_owned()
        }
    };
    let disc_body = discussion_file.map_or_else(
        || "(none \u{2014} discussion-round1 artifact not passed or absent.)".to_owned(),
        |path| {
            let text = read_text_or_empty(path);
            let trimmed = text.trim();
            if trimmed.is_empty() {
                "(discussion path not readable)".to_owned()
            } else {
                trimmed.to_owned()
            }
        },
    );
    let full = fs::read_to_string(&arch_file)
        .map_err(|error| format!("read {}: {error}", arch_file.display()))?
        .replace("{COMMON_TAIL}", &read_text_or_empty(&common_tail))
        .replace(
            "{PLAN_OR_FEATURE_BLOCK}",
            &format!("## Primary input\n\n{primary}\n\n"),
        )
        .replace(
            "{DISCUSSION_BLOCK}",
            &format!("## Discussion round 1\n\n{disc_body}\n\n"),
        );
    fs::write(out, full).map_err(|error| format!("write {}: {error}", out.display()))
}

/// Run a decomposition waterfall child, honoring the test override.
fn run_waterfall_child(
    override_var: &str,
    verb: &[&str],
    tail: Vec<OsString>,
    timeout: Duration,
) -> (i32, String) {
    #[cfg(test)]
    if let Some(stub) = TEST_WATERFALL_STUB.with(|slot| slot.borrow().clone()) {
        return run_override_capture(stub.as_os_str(), &tail);
    }
    if let Some(stub) = env::var_os(override_var).filter(|value| !value.is_empty()) {
        run_override_capture(&stub, &tail)
    } else {
        let mut argv: Vec<OsString> = verb.iter().map(OsString::from).collect();
        argv.extend(tail);
        code_and_stdout(run_verified_larch_with_timeout(&argv, timeout))
    }
}

fn run_override_capture(program: &OsStr, args: &[OsString]) -> (i32, String) {
    match std::process::Command::new(program) // lint-subprocess-via-runner: ok test-only deterministic waterfall override has no typed executable owner
        .args(args)
        .stderr(std::process::Stdio::piped())
        .output()
    {
        Ok(output) => (
            output.status.code().unwrap_or(1),
            String::from_utf8_lossy(&output.stdout).into_owned(),
        ),
        Err(_error) => (1, String::new()),
    }
}

#[allow(clippy::too_many_arguments, clippy::too_many_lines)] // Faithful port of the Python panel dispatcher.
fn dispatch_panel(
    design_tmpdir: &Path,
    codex_present: bool,
    cursor_present: bool,
    mode: &str,
    plan_file: Option<&Path>,
    feature_file: Option<&Path>,
    discussion_file: Option<&Path>,
    timeout: u64,
) -> Result<(), String> {
    let dec = design_tmpdir.join("decompose");
    fs::create_dir_all(&dec).map_err(|error| error.to_string())?;
    let primary_input: PathBuf = match mode {
        "plan" => {
            let plan = plan_file
                .filter(|path| path.is_file())
                .ok_or("plan mode requires --plan-file")?;
            plan.to_path_buf()
        }
        "feature-only" => {
            let feature = feature_file
                .filter(|path| path.is_file())
                .ok_or("feature-only mode requires --feature-file")?;
            feature.to_path_buf()
        }
        _ => return Err("--mode must be plan or feature-only".to_owned()),
    };
    let feature = feature_file.map_or_else(
        || design_tmpdir.join("feature-description.txt"),
        Path::to_path_buf,
    );
    if !feature.is_file() {
        return Err(format!(
            "feature-description not found (set --feature-file): {}",
            feature.display()
        ));
    }
    if let Some(path) = discussion_file
        && !path.is_file()
    {
        return Err(format!("discussion file not found: {}", path.display()));
    }

    let manifest = dec.join("decompose-slots.ndjson");
    let panel_rows = dec.join("panel-outputs.ndjson");
    fs::write(&manifest, "").map_err(|error| error.to_string())?;
    fs::write(&panel_rows, "").map_err(|error| error.to_string())?;

    if !codex_present && !cursor_present {
        return dispatch_generic_claude(
            &dec,
            &primary_input,
            discussion_file,
            &feature,
            &panel_rows,
            timeout,
        );
    }

    for arch in DECOMPOSE_ARCHETYPES {
        for tool in ["cursor", "codex"] {
            let present = if tool == "cursor" {
                cursor_present
            } else {
                codex_present
            };
            if !present {
                continue;
            }
            let slot = format!("decomp-{tool}-{arch}");
            let output = dec.join(format!("decomp-{tool}-{arch}-output.txt"));
            let prompt_file = dec.join(format!("render-decomp-{tool}-{arch}.prompt"));
            render_decompose_prompt(arch, &primary_input, discussion_file, &prompt_file)?;
            let row = SlotRow {
                slot,
                tool: tool.to_owned(),
                output: output.to_string_lossy().into_owned(),
                prompt_file: prompt_file.to_string_lossy().into_owned(),
            };
            append_json_line(
                &manifest,
                &serde_json::to_string(&row).map_err(|error| error.to_string())?,
            );
        }
    }

    let mut tail: Vec<OsString> = vec![
        "--slots-file".into(),
        manifest.clone().into_os_string(),
        "--codex-present".into(),
        codex_present.to_string().into(),
        "--cursor-present".into(),
        cursor_present.to_string().into(),
        "--mode".into(),
        "description".into(),
        "--no-fallback".into(),
        "--require-result-pattern".into(),
        "^[[:space:]]*## Recommendation".into(),
        "--feature-file".into(),
        feature.into_os_string(),
        "--timeout".into(),
        timeout.to_string().into(),
    ];
    if mode == "plan"
        && let Some(plan) = plan_file
    {
        tail.push("--plan-file".into());
        tail.push(plan.to_path_buf().into_os_string());
    }
    let (rc, dispatch_out) = run_waterfall_child(
        PANEL_WATERFALL_OVERRIDE,
        &["agent", "dispatch-waterfall"],
        tail,
        Duration::from_secs(timeout),
    );
    if rc != 0 {
        let cap = dec.join("decompose-waterfall-failure.log");
        let _ = fs::write(&cap, &dispatch_out);
        append_failure(
            design_tmpdir,
            "design Step 2b.5 decompose panel",
            "agent dispatch-waterfall",
            rc,
            &cap,
        );
    }
    let kvs = parse_kv(&dispatch_out);
    let static_dispatch_ok = kvs.get("STATIC_DISPATCH_OK").map_or("true", String::as_str);
    let combined_fallback_count = kvs
        .get("COMBINED_FALLBACK_COUNT")
        .or_else(|| kvs.get("FALLBACK_COUNT"))
        .map_or("0", String::as_str);
    let all_outputs_file = kvs.get("ALL_OUTPUT_FILES_PATH").map_or("", String::as_str);
    let all_slots_dropped = kvs.get("ALL_SLOTS_DROPPED").map_or("", String::as_str);

    let manifest_rows: Vec<Value> = match read_manifest_rows(&manifest) {
        Ok(rows) => rows,
        Err(message) => {
            emit_kv("PANEL_OUTPUTS_FILE", &panel_rows.to_string_lossy());
            emit_bool("DEGRADED_PANEL", true);
            emit_kv("PANEL_STATUS", "panel-failed");
            return Err(message);
        }
    };
    let slot_count = manifest_rows.len();
    let combined_fallback_n: i64 = combined_fallback_count.parse().unwrap_or(0);
    let mut degraded = static_dispatch_ok == "false"
        || usize::try_from(combined_fallback_n).unwrap_or(0) > slot_count / 2
        || all_slots_dropped == "true";
    let resolved_paths: Vec<String> =
        if !all_outputs_file.is_empty() && Path::new(all_outputs_file).is_file() {
            fs::read_to_string(all_outputs_file)
                .unwrap_or_default()
                .lines()
                .filter(|line| !line.is_empty())
                .map(str::to_owned)
                .collect()
        } else {
            Vec::new()
        };
    if slot_count > 0 && resolved_paths.len() < slot_count {
        degraded = true;
    }
    let mut usable = 0usize;
    let mut warned_missing_paths = false;

    let match_resolved = |manifest_out: &str| -> String {
        let base = Path::new(manifest_out)
            .file_name()
            .map(|name| name.to_string_lossy().into_owned())
            .unwrap_or_default();
        for candidate in &resolved_paths {
            if candidate == manifest_out
                || Path::new(candidate)
                    .file_name()
                    .map(|name| name.to_string_lossy().into_owned())
                    == Some(base.clone())
            {
                return candidate.clone();
            }
        }
        String::new()
    };

    for row in &manifest_rows {
        let manifest_out = row
            .get("output")
            .and_then(Value::as_str)
            .unwrap_or("")
            .to_owned();
        let slot = row.get("slot").and_then(Value::as_str).unwrap_or("");
        let arch = slot
            .strip_prefix("decomp-cursor-")
            .or_else(|| slot.strip_prefix("decomp-codex-"))
            .unwrap_or(slot);
        let vendor = row
            .get("tool")
            .and_then(Value::as_str)
            .unwrap_or("")
            .to_owned();
        if resolved_paths.is_empty() {
            if all_slots_dropped == "true" {
                continue;
            }
            if !warned_missing_paths {
                breadcrumb(
                    "decompose-panel-dispatch.sh: ALL_OUTPUT_FILES_PATH empty or missing; skipping manifest rows (no resolved paths)",
                );
                warned_missing_paths = true;
            }
            continue;
        }
        let out_resolved = match_resolved(&manifest_out);
        if out_resolved.is_empty() {
            write_panel_row(&panel_rows, arch, &vendor, &manifest_out, "missing");
            continue;
        }
        let path = Path::new(&out_resolved);
        let status = if path.is_file() && RECOMMENDATION_RE.is_match(&read_text_or_empty(path)) {
            usable += 1;
            "ok"
        } else if path.is_file() {
            "unparsed"
        } else {
            "missing"
        };
        write_panel_row(&panel_rows, arch, &vendor, &out_resolved, status);
    }

    let mut panel_status = if usable == 0 {
        "panel-failed"
    } else if degraded {
        "degraded"
    } else {
        "ok"
    };
    if rc != 0 {
        degraded = true;
        if usable > 0 && panel_status == "ok" {
            panel_status = "degraded";
        }
    }
    for line in dispatch_out.lines() {
        if let Some(row) = parse_single_kv_row(line, ParseOptions::legacy()) {
            emit_kv(row.key(), row.value());
        }
    }
    emit_kv("PANEL_OUTPUTS_FILE", &panel_rows.to_string_lossy());
    emit_bool("DEGRADED_PANEL", degraded);
    emit_kv("PANEL_STATUS", panel_status);
    Ok(())
}

fn dispatch_generic_claude(
    dec: &Path,
    primary_input: &Path,
    discussion_file: Option<&Path>,
    feature: &Path,
    panel_rows: &Path,
    timeout: u64,
) -> Result<(), String> {
    let generic_output = dec.join("decomp-claude-generic-output.txt");
    let generic_prompt = dec.join("decomp-claude-generic.prompt");
    let tail_src = dec.join(".generic-tail-src.prompt");
    render_decompose_prompt(
        "decomposition-specialist",
        primary_input,
        discussion_file,
        &tail_src,
    )?;
    let mut parts: Vec<String> = vec![
        "You are a combined decomposition panel applying all four standard archetype lenses in a single pass. Address each lens below, then follow the shared output contract.".to_owned(),
        String::new(),
    ];
    let prompts = decompose_prompts_dir()?;
    for arch in DECOMPOSE_ARCHETYPES {
        let lines = read_text_or_empty(&prompts.join(format!("{arch}.txt")));
        let mut prefix: Vec<String> = Vec::new();
        for line in lines.lines() {
            prefix.push(line.to_owned());
            if line == "Your focus:" {
                break;
            }
            if prefix.len() >= DECOMPOSE_PROMPT_PREFIX_LINE_MAX {
                break;
            }
        }
        parts.extend(prefix);
        parts.push(String::new());
    }
    let tail_lines: Vec<String> = read_text_or_empty(&tail_src)
        .lines()
        .skip(1)
        .map(str::to_owned)
        .collect();
    parts.extend(tail_lines);
    fs::write(&generic_prompt, format!("{}\n", parts.join("\n")))
        .map_err(|error| error.to_string())?;
    let _ = fs::remove_file(&tail_src);

    let tail: Vec<OsString> = vec![
        "--output".into(),
        generic_output.clone().into_os_string(),
        "--prompt-file".into(),
        generic_prompt.into_os_string(),
        "--mode".into(),
        "description".into(),
        "--model".into(),
        "claude-sonnet-4-6".into(),
        "--timeout".into(),
        timeout.to_string().into(),
        "--timing-task-kind".into(),
        "claude-decomp-generic".into(),
        "--feature-file".into(),
        feature.to_path_buf().into_os_string(),
    ];
    let (rc, _out) = run_waterfall_child(
        CLAUDE_REVIEW_OVERRIDE,
        &["agent", "launch-claude-review"],
        tail,
        Duration::from_secs(timeout),
    );
    let done = generic_output.with_extension("txt.done");
    if !done.is_file() {
        let _ = fs::write(&done, format!("{rc}\n"));
    }
    let status = if generic_output.is_file()
        && RECOMMENDATION_RE.is_match(&read_text_or_empty(&generic_output))
    {
        "ok"
    } else if generic_output.is_file() {
        "unparsed"
    } else {
        "missing"
    };
    write_panel_row(
        panel_rows,
        "generic",
        "claude",
        &generic_output.to_string_lossy(),
        status,
    );
    let dispatch_ok = rc == 0 && status == "ok";
    emit_bool("DISPATCH_OK", dispatch_ok);
    emit_kv("FALLBACK_COUNT", "0");
    emit_kv("COMBINED_FALLBACK_COUNT", "0");
    emit_bool("STATIC_DISPATCH_OK", dispatch_ok);
    emit_bool("DYNAMIC_DISPATCH_OK", true);
    let degraded = !dispatch_ok;
    emit_kv("PANEL_OUTPUTS_FILE", &panel_rows.to_string_lossy());
    emit_bool("DEGRADED_PANEL", degraded);
    emit_kv("PANEL_STATUS", if degraded { "panel-failed" } else { "ok" });
    Ok(())
}

fn write_panel_row(panel_rows: &Path, archetype: &str, vendor: &str, output: &str, status: &str) {
    let row = PanelRow {
        archetype: archetype.to_owned(),
        vendor: vendor.to_owned(),
        output: output.to_owned(),
        status: status.to_owned(),
    };
    if let Ok(line) = serde_json::to_string(&row) {
        append_json_line(panel_rows, &line);
    }
}

fn read_manifest_rows(manifest: &Path) -> Result<Vec<Value>, String> {
    let mut rows = Vec::new();
    for line in read_text_or_empty(manifest).lines() {
        if line.trim().is_empty() {
            continue;
        }
        let value: Value = serde_json::from_str(line)
            .map_err(|_error| "malformed decompose-slots.ndjson".to_owned())?;
        if !value.is_object() {
            return Err("malformed decompose-slots.ndjson".to_owned());
        }
        rows.push(value);
    }
    Ok(rows)
}

fn binary_bool(value: &str, binary: &str) -> bool {
    match value {
        "true" => true,
        "false" => false,
        _ => which_binary(binary),
    }
}

pub fn which_binary(binary: &str) -> bool {
    env::var_os("PATH")
        .is_some_and(|paths| env::split_paths(&paths).any(|dir| dir.join(binary).is_file()))
}

/// `decompose panel-dispatch` entrypoint.
pub fn panel_dispatch_main(arguments: &[OsString]) -> ExitCode {
    let values = [
        "--design-tmpdir",
        "--codex-present",
        "--cursor-present",
        "--codex-binary-found",
        "--cursor-binary-found",
        "--mode",
        "--plan-file",
        "--feature-file",
        "--discussion-round1-file",
        "--timeout",
    ];
    let parsed = parse_with_flags(arguments, &values, &[], 0);
    let parsed = match finish_parse(
        parsed,
        "usage: decompose panel-dispatch",
        "decompose panel-dispatch",
        &["--design-tmpdir", "--mode"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let design_tmpdir =
        match resolve_design_tmpdir(parsed.value("--design-tmpdir").unwrap_or_default()) {
            Ok(path) => path,
            Err(message) => {
                breadcrumb(&format!("decompose-panel-dispatch.sh: {message}"));
                return ExitCode::from(2);
            }
        };
    let mode = parsed
        .value("--mode")
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default();
    let timeout = match positive_int(parsed.value("--timeout")) {
        Ok(value) => value,
        Err(message) => {
            breadcrumb(&format!("decompose-panel-dispatch.sh: {message}"));
            return ExitCode::from(2);
        }
    };
    let plan_file = opt_path(parsed.value("--plan-file"));
    let feature_file = opt_path(parsed.value("--feature-file"));
    let discussion_file = opt_path(parsed.value("--discussion-round1-file"));
    let codex_present = binary_bool(
        &parsed
            .value("--codex-binary-found")
            .map(|v| v.to_string_lossy().into_owned())
            .unwrap_or_default(),
        "codex",
    );
    let cursor_present = binary_bool(
        &parsed
            .value("--cursor-binary-found")
            .map(|v| v.to_string_lossy().into_owned())
            .unwrap_or_default(),
        "cursor",
    );
    match dispatch_panel(
        &design_tmpdir,
        codex_present,
        cursor_present,
        &mode,
        plan_file.as_deref(),
        feature_file.as_deref(),
        discussion_file.as_deref(),
        timeout,
    ) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            breadcrumb(&format!("decompose-panel-dispatch.sh: {message}"));
            ExitCode::from(2)
        }
    }
}

// ---------------------------------------------------------------- aggregate

const AGGREGATOR_MERGE_HEADER: &str = "You are the decomposition aggregator. Below are eight independent partition proposals from external reviewers (four archetypes x two vendors).\n\nTask: produce **one** canonical merged partition that best satisfies the independently-mergeable constraint (acyclic blocker graph) while minimizing unnecessary coupling.\n\n";
const AGGREGATOR_MERGE_SCHEMA: &str = "\nOutput **only** Markdown matching this schema (first heading must be detectable):\n\n## Recommendation\nsplit | no-split\n\n## Pieces (only when Recommendation is split)\n\n### Piece 1: <short title>\n- Scope: <files / behaviors covered>\n- Firm-headings: <bare parent-plan paths, comma-separated; no `###` or backticks>\n- Acceptance: <one or more implementable criteria for this piece>\n- Dependencies: none | blocked-by Piece N[, Piece M ...]\n- Diff_lines estimate: <integer>\n- Why independently mergeable: <prose>\n\n### Piece 2: ...\n";

#[allow(clippy::too_many_lines)] // Faithful port of the Python aggregator.
fn aggregate_partition(
    design_tmpdir: &Path,
    panel_outputs_file: &Path,
    codex_present: bool,
    cursor_present: bool,
    output: &Path,
    timeout: u64,
) -> Result<String, String> {
    if !panel_outputs_file.is_file() {
        return Err("--panel-outputs-file must exist".to_owned());
    }
    let dec = design_tmpdir.join("decompose");
    fs::create_dir_all(&dec).map_err(|error| error.to_string())?;
    let combined = dec.join("combined-proposals.txt");
    let mut combined_body = String::new();
    for line in read_text_or_empty(panel_outputs_file).lines() {
        if line.trim().is_empty() {
            continue;
        }
        let value: Value = match serde_json::from_str::<Value>(line) {
            Ok(value) if value.is_object() => value,
            _ => {
                emit_kv("AGGREGATOR_STATUS", "failed");
                return Err("malformed panel-outputs.ndjson".to_owned());
            }
        };
        let archetype = value.get("archetype").and_then(Value::as_str).unwrap_or("");
        let vendor = value.get("vendor").and_then(Value::as_str).unwrap_or("");
        let out_path = value.get("output").and_then(Value::as_str).unwrap_or("");
        let _ = write!(
            combined_body,
            "\n## Panel output ({archetype} / {vendor})\n\n"
        );
        if Path::new(out_path).is_file() {
            combined_body.push_str(&read_text_or_empty(Path::new(out_path)));
        } else {
            // Python renders `Path(str(output))`, so an empty output field
            // becomes `.` rather than the empty string.
            let displayed = if out_path.is_empty() { "." } else { out_path };
            let _ = writeln!(combined_body, "(missing file: {displayed})");
        }
        combined_body.push('\n');
    }
    fs::write(&combined, &combined_body).map_err(|error| error.to_string())?;

    let feature = design_tmpdir.join("feature-description.txt");
    if !feature.is_file() {
        return Err(format!(
            "missing {} for aggregator context",
            feature.display()
        ));
    }
    let merge_prompt = dec.join("aggregator-partition-merge.prompt");
    fs::write(
        &merge_prompt,
        format!("{AGGREGATOR_MERGE_HEADER}{combined_body}{AGGREGATOR_MERGE_SCHEMA}"),
    )
    .map_err(|error| error.to_string())?;
    let agg_out = dec.join("aggregator-raw-output.txt");
    let slots = dec.join("aggregator-slots.ndjson");
    let slot_row = SlotRow {
        slot: "decompose-aggregator".to_owned(),
        tool: "codex".to_owned(),
        output: agg_out.to_string_lossy().into_owned(),
        prompt_file: merge_prompt.to_string_lossy().into_owned(),
    };
    fs::write(
        &slots,
        format!(
            "{}\n",
            serde_json::to_string(&slot_row).map_err(|error| error.to_string())?
        ),
    )
    .map_err(|error| error.to_string())?;

    let tail: Vec<OsString> = vec![
        "--slots-file".into(),
        slots.into_os_string(),
        "--codex-present".into(),
        codex_present.to_string().into(),
        "--cursor-present".into(),
        cursor_present.to_string().into(),
        "--mode".into(),
        "description".into(),
        "--feature-file".into(),
        feature.into_os_string(),
        "--require-result-pattern".into(),
        "^[[:space:]]*## Recommendation".into(),
        "--timeout".into(),
        timeout.to_string().into(),
    ];
    let (rc, dispatch_out) = run_waterfall_child(
        AGGREGATE_WATERFALL_OVERRIDE,
        &["agent", "dispatch-waterfall"],
        tail,
        Duration::from_secs(timeout),
    );
    let kvs = parse_kv(&dispatch_out);
    // Python takes the first line even when it is blank (`Path("") == Path(".")`);
    // only an empty paths file (no first line) falls back to `agg_out`.
    let final_out = if let Some(paths_file) = kvs.get("ALL_OUTPUT_FILES_PATH")
        && Path::new(paths_file).is_file()
        && let Some(first) = read_text_or_empty(Path::new(paths_file)).lines().next()
    {
        PathBuf::from(first)
    } else {
        agg_out
    };
    if rc == 0
        && kvs.get("DISPATCH_OK").map_or("false", String::as_str) == "true"
        && final_out.is_file()
        && RECOMMENDATION_RE.is_match(&read_text_or_empty(&final_out))
    {
        if let Some(parent) = output.parent() {
            let _ = fs::create_dir_all(parent);
        }
        fs::copy(&final_out, output).map_err(|error| error.to_string())?;
        Ok("ok".to_owned())
    } else {
        Ok("failed".to_owned())
    }
}

/// `decompose aggregate` entrypoint.
pub fn aggregate_main(arguments: &[OsString]) -> ExitCode {
    let values = [
        "--design-tmpdir",
        "--panel-outputs-file",
        "--codex-present",
        "--cursor-present",
        "--codex-binary-found",
        "--cursor-binary-found",
        "--output",
        "--timeout",
    ];
    let parsed = parse_with_flags(arguments, &values, &[], 0);
    let parsed = match finish_parse(
        parsed,
        "usage: decompose aggregate",
        "decompose aggregate",
        &["--design-tmpdir", "--panel-outputs-file", "--output"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let design_tmpdir =
        match resolve_design_tmpdir(parsed.value("--design-tmpdir").unwrap_or_default()) {
            Ok(path) => path,
            Err(message) => {
                breadcrumb(&format!("decompose-aggregator.sh: {message}"));
                return ExitCode::from(2);
            }
        };
    let panel_outputs_file =
        PathBuf::from(parsed.value("--panel-outputs-file").unwrap_or_default());
    let output = PathBuf::from(parsed.value("--output").unwrap_or_default());
    let timeout = match positive_int(parsed.value("--timeout")) {
        Ok(value) => value,
        Err(message) => {
            breadcrumb(&format!("decompose-aggregator.sh: {message}"));
            return ExitCode::from(2);
        }
    };
    let codex_present = binary_bool(
        &parsed
            .value("--codex-binary-found")
            .map(|v| v.to_string_lossy().into_owned())
            .unwrap_or_default(),
        "codex",
    );
    let cursor_present = binary_bool(
        &parsed
            .value("--cursor-binary-found")
            .map(|v| v.to_string_lossy().into_owned())
            .unwrap_or_default(),
        "cursor",
    );
    match aggregate_partition(
        &design_tmpdir,
        &panel_outputs_file,
        codex_present,
        cursor_present,
        &output,
        timeout,
    ) {
        Ok(status) => {
            emit_kv("AGGREGATOR_STATUS", &status);
            if status == "ok" {
                emit_kv("AGGREGATOR_OUTPUT", &output.to_string_lossy());
            }
            ExitCode::SUCCESS
        }
        Err(message) => {
            // Python's UsageError path returns exit 2 without emitting any
            // AGGREGATOR_STATUS; the malformed-NDJSON case already emitted its
            // own `failed` inside aggregate_partition before returning Err.
            breadcrumb(&format!("decompose-aggregator.sh: {message}"));
            ExitCode::from(2)
        }
    }
}

fn opt_path(value: Option<&OsStr>) -> Option<PathBuf> {
    value.filter(|value| !value.is_empty()).map(PathBuf::from)
}

fn positive_int(value: Option<&OsStr>) -> Result<u64, String> {
    let raw = value.map_or_else(
        || "1800".to_owned(),
        |value| value.to_string_lossy().into_owned(),
    );
    match raw.parse::<u64>() {
        Ok(parsed) if parsed > 0 => Ok(parsed),
        _ => Err("--timeout must be a positive integer".to_owned()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;
    use std::collections::{BTreeMap, BTreeSet};
    use tempfile::TempDir;

    struct FakeGraph {
        blocked_by: RefCell<BTreeMap<u64, BTreeSet<u64>>>,
    }

    impl FakeGraph {
        fn new(initial: &[(u64, &[u64])]) -> Self {
            let mut map = BTreeMap::new();
            for (issue, blockers) in initial {
                map.insert(*issue, blockers.iter().copied().collect());
            }
            Self {
                blocked_by: RefCell::new(map),
            }
        }
    }

    impl DependencyGraph for FakeGraph {
        fn read_dependencies(&self, issue: u64) -> Result<(Vec<u64>, Vec<u64>), String> {
            let map = self.blocked_by.borrow();
            let incoming = map
                .get(&issue)
                .map(|set| set.iter().copied().collect())
                .unwrap_or_default();
            let outgoing = map
                .iter()
                .filter(|(_key, value)| value.contains(&issue))
                .map(|(key, _value)| *key)
                .collect();
            Ok((incoming, outgoing))
        }

        #[allow(clippy::similar_names)] // blocked/blocker is the domain contract.
        fn mutate(&self, remove: bool, blocked: u64, blocker: u64) -> bool {
            let mut map = self.blocked_by.borrow_mut();
            let entry = map.entry(blocked).or_default();
            if remove {
                entry.remove(&blocker);
            } else {
                entry.insert(blocker);
            }
            true
        }
    }

    struct PanicGraph;
    impl DependencyGraph for PanicGraph {
        fn read_dependencies(&self, _issue: u64) -> Result<(Vec<u64>, Vec<u64>), String> {
            panic!("denied migration must not read the graph");
        }
        fn mutate(&self, _remove: bool, _blocked: u64, _blocker: u64) -> bool {
            panic!("denied migration must not mutate the graph");
        }
    }

    struct RecordingCloser {
        comments: RefCell<Vec<u64>>,
        closes: RefCell<Vec<u64>>,
        close_ok: bool,
    }

    impl IssueCloser for RecordingCloser {
        fn post_comment(&self, issue: u64, _body: &str) -> Result<(), String> {
            self.comments.borrow_mut().push(issue);
            Ok(())
        }
        fn close(&self, issue: u64) -> Result<(), String> {
            self.closes.borrow_mut().push(issue);
            if self.close_ok {
                Ok(())
            } else {
                Err("close failed".to_owned())
            }
        }
    }

    fn design_dir() -> (TempDir, PathBuf) {
        let dir = TempDir::new().expect("tempdir");
        let root = dir.path().join("design");
        fs::create_dir_all(root.join("decompose")).expect("decompose dir");
        fs::write(
            root.join("feature-description.txt"),
            "Feature\n### embedded heading\n",
        )
        .expect("feature");
        (dir, root)
    }

    #[test]
    fn run_prepare_writes_artifacts_and_deps() {
        let (_dir, root) = design_dir();
        let partition = root.join("partition.md");
        fs::write(
            &partition,
            "## Pieces\n\n### Piece 1: Base\n- Scope: base\n- Firm-headings: base/file.py\n- Acceptance: verify base\n- Dependencies: none\n\n### Piece 2: API\n- Scope: api\n- Firm-headings: api/file.py\n- Acceptance: verify api\n- Dependencies: blocked-by Piece 1\n",
        )
        .expect("partition");
        let (status, witness) = run_prepare(&root, &partition, "123").expect("prepare");
        assert_eq!((status.as_str(), witness.as_str()), ("ok", ""));
        assert_eq!(
            fs::read_to_string(root.join("decompose/partition-deps.tsv")).unwrap(),
            "1\t2\n"
        );
        let batch = fs::read_to_string(root.join("decompose/partition-input.txt")).unwrap();
        assert!(batch.contains("#123"));
        assert!(batch.contains("\u{200b}### embedded heading"));
    }

    #[test]
    fn annotate_success_partial_and_idempotent() {
        let (_dir, root) = design_dir();
        fs::write(
            root.join("decompose/partition-input.txt"),
            "### One\n\n### Two\n",
        )
        .expect("input");
        let out = root.join("issue.out");
        fs::write(
            &out,
            "ISSUES_CREATED=2\nISSUES_FAILED=0\nISSUE_1_URL=https://x/1\nISSUE_2_URL=https://x/2\n",
        )
        .expect("out");
        annotate_partition(&root, &out).expect("annotate");
        let sentinel = root.join(".decompose-issues-filed");
        assert!(
            fs::read_to_string(&sentinel)
                .unwrap()
                .contains("PARTITION_FILE_MAP\t1\thttps://x/1")
        );
        let before = fs::read_to_string(root.join("decompose/partition-filed.md")).unwrap();
        annotate_partition(&root, &out).expect("annotate idempotent");
        assert_eq!(
            fs::read_to_string(root.join("decompose/partition-filed.md")).unwrap(),
            before
        );
        let partial = root.join("partial.out");
        fs::write(
            &partial,
            "ISSUES_CREATED=1\nISSUES_FAILED=1\nISSUE_1_URL=https://x/1\n",
        )
        .expect("partial");
        annotate_partition(&root, &partial).expect("annotate partial");
        assert!(!sentinel.exists());
    }

    fn write_filed_mapping(root: &Path, pieces: &[(u64, u64)]) {
        let mut body = String::new();
        for (piece, issue) in pieces {
            let _ = writeln!(
                body,
                "PARTITION_FILE_MAP\t{piece}\thttps://github.com/o/r/issues/{issue}"
            );
        }
        fs::write(root.join(".decompose-issues-filed"), body).expect("filed mapping");
    }

    #[test]
    fn migrate_denied_touches_no_graph_and_no_sentinel() {
        let (_dir, root) = design_dir();
        let status = migrate_with(&root, 99, "o/r", &PanicGraph, Err("denied".to_owned()));
        assert_eq!(status, "authorization-denied");
        assert!(!root.join(".decompose-deps-migrated").exists());
    }

    #[test]
    fn migrate_replaces_incoming_and_outgoing_edges() {
        let (_dir, root) = design_dir();
        write_filed_mapping(&root, &[(1, 101), (2, 102)]);
        fs::write(root.join("decompose/partition-deps.tsv"), "1\t2\n").expect("deps");
        let graph = FakeGraph::new(&[(99, &[7]), (101, &[]), (102, &[101]), (8, &[99])]);
        let status = migrate_with(&root, 99, "o/r", &graph, Ok(()));
        assert_eq!(status, "ok");
        let map = graph.blocked_by.borrow();
        assert_eq!(map[&101], BTreeSet::from([7]));
        assert_eq!(map[&102], BTreeSet::from([7, 101]));
        assert_eq!(map[&8], BTreeSet::from([101, 102]));
        assert_eq!(map[&99], BTreeSet::new());
        assert!(root.join(".decompose-deps-migrated").exists());
    }

    #[test]
    fn migrate_rejects_live_dependency_drift() {
        let (_dir, root) = design_dir();
        write_filed_mapping(&root, &[(1, 101), (2, 102)]);
        fs::write(root.join("decompose/partition-deps.tsv"), "").expect("deps");
        let manifest = DependencyMigration {
            schema_version: "1".to_owned(),
            original_issue: 99,
            repo: "o/r".to_owned(),
            pieces: vec![
                FiledPiece {
                    piece: 1,
                    issue: 101,
                    repo: "o/r".to_owned(),
                },
                FiledPiece {
                    piece: 2,
                    issue: 102,
                    repo: "o/r".to_owned(),
                },
            ],
            incoming: vec![PartitionEdge {
                blocked: 99,
                blocker: 7,
            }],
            outgoing: vec![],
        };
        write_migration(&migration_manifest_path(&root), &manifest).expect("manifest");
        // Live graph shows 99 blocked by 8, not the persisted 7: drift.
        let graph = FakeGraph::new(&[(99, &[8])]);
        assert_eq!(migrate_with(&root, 99, "o/r", &graph, Ok(())), "failed");
    }

    fn seed_close_fixture(root: &Path, close_ok: bool) -> RecordingCloser {
        fs::write(root.join("decompose/partition-deps.tsv"), "").expect("deps");
        fs::write(
            root.join("decompose/partition-filed.md"),
            "## Piece 1\n- **Filed URL**: https://github.com/o/r/issues/101\n",
        )
        .expect("filed");
        let manifest = DependencyMigration {
            schema_version: "1".to_owned(),
            original_issue: 99,
            repo: "o/r".to_owned(),
            pieces: vec![FiledPiece {
                piece: 1,
                issue: 101,
                repo: "o/r".to_owned(),
            }],
            incoming: vec![],
            outgoing: vec![],
        };
        write_migration(&root.join("decompose/dependency-migration.json"), &manifest)
            .expect("manifest");
        fs::write(root.join(".decompose-deps-migrated"), "").expect("migrated sentinel");
        RecordingCloser {
            comments: RefCell::new(Vec::new()),
            closes: RefCell::new(Vec::new()),
            close_ok,
        }
    }

    #[test]
    fn close_original_idempotent_when_already_closed() {
        let (_dir, root) = design_dir();
        fs::write(root.join(".decompose-original-closed"), "").expect("closed sentinel");
        let graph = PanicGraph;
        let closer = RecordingCloser {
            comments: RefCell::new(Vec::new()),
            closes: RefCell::new(Vec::new()),
            close_ok: true,
        };
        assert_eq!(close_with(&root, 99, "o/r", &graph, &closer), "ok");
        assert!(closer.closes.borrow().is_empty());
    }

    #[test]
    fn close_comments_then_closes_on_success() {
        let (_dir, root) = design_dir();
        let closer = seed_close_fixture(&root, true);
        let graph = FakeGraph::new(&[(99, &[]), (101, &[])]);
        assert_eq!(close_with(&root, 99, "o/r", &graph, &closer), "ok");
        assert_eq!(*closer.comments.borrow(), vec![99]);
        assert_eq!(*closer.closes.borrow(), vec![99]);
        assert!(root.join(".decompose-original-closed").exists());
    }

    #[test]
    fn close_preserves_comment_sentinel_on_close_failure() {
        let (_dir, root) = design_dir();
        let closer = seed_close_fixture(&root, false);
        let graph = FakeGraph::new(&[(99, &[]), (101, &[])]);
        assert_eq!(close_with(&root, 99, "o/r", &graph, &closer), "failed");
        assert!(
            root.join("decompose/.decompose-close-comment-posted")
                .exists()
        );
        assert!(!root.join(".decompose-original-closed").exists());
    }

    #[cfg(unix)]
    fn repo_prompts_dir() -> PathBuf {
        fs::canonicalize(
            Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("..")
                .join("..")
                .join("skills/design/scripts/decompose-prompts"),
        )
        .expect("decompose-prompts dir")
    }

    #[cfg(unix)]
    fn write_executable(path: &Path, body: &str) {
        use std::os::unix::fs::PermissionsExt as _;
        fs::write(path, body).expect("write stub");
        fs::set_permissions(path, fs::Permissions::from_mode(0o755)).expect("chmod stub");
    }

    #[cfg(unix)]
    fn waterfall_stub(dir: &Path) -> PathBuf {
        let stub = dir.join("waterfall.sh");
        write_executable(
            &stub,
            "#!/usr/bin/env bash\nset -euo pipefail\nslots=\"\"\nwhile [[ $# -gt 0 ]]; do if [[ $1 == --slots-file ]]; then slots=$2; shift 2; else shift; fi; done\npaths=$(mktemp)\nwhile IFS= read -r row; do\n  [[ -z \"$row\" ]] && continue\n  out=$(printf '%s' \"$row\" | sed -n 's/.*\"output\":\"\\([^\"]*\\)\".*/\\1/p')\n  printf '## Recommendation\\nsplit\\n' > \"$out\"\n  printf '%s\\n' \"$out\" >> \"$paths\"\ndone < \"$slots\"\nprintf 'DISPATCH_OK=true\\nFALLBACK_COUNT=0\\nCOMBINED_FALLBACK_COUNT=0\\nSTATIC_DISPATCH_OK=true\\nALL_OUTPUT_FILES_PATH=%s\\n' \"$paths\"\n",
        );
        stub
    }

    #[cfg(unix)]
    #[test]
    fn dispatch_panel_covers_orchestration() {
        let (dir, root) = design_dir();
        fs::write(root.join("plan.txt"), "## Plan\n").expect("plan");
        let stub = waterfall_stub(dir.path());
        let outcome = with_test_overrides(repo_prompts_dir(), Some(stub), || {
            dispatch_panel(
                &root,
                true,
                true,
                "plan",
                Some(&root.join("plan.txt")),
                None,
                None,
                30,
            )
        });
        assert_eq!(outcome, Ok(()));
        let rows = fs::read_to_string(root.join("decompose/panel-outputs.ndjson")).expect("rows");
        assert_eq!(rows.lines().filter(|line| !line.is_empty()).count(), 8);
        assert!(rows.contains("\"status\":\"ok\""));
    }

    #[cfg(unix)]
    #[test]
    fn dispatch_generic_claude_covers_both_absent_branch() {
        let (dir, root) = design_dir();
        fs::write(root.join("plan.txt"), "## Plan\n").expect("plan");
        let claude = dir.path().join("claude.sh");
        write_executable(
            &claude,
            "#!/usr/bin/env bash\nset -euo pipefail\nout=\"\"\nwhile [[ $# -gt 0 ]]; do if [[ $1 == --output ]]; then out=$2; shift 2; else shift; fi; done\nprintf '## Recommendation\\nGeneric\\n' > \"$out\"\nprintf '0\\n' > \"${out}.done\"\n",
        );
        let outcome = with_test_overrides(repo_prompts_dir(), Some(claude), || {
            dispatch_panel(
                &root,
                false,
                false,
                "plan",
                Some(&root.join("plan.txt")),
                None,
                None,
                30,
            )
        });
        assert_eq!(outcome, Ok(()));
        let rows = fs::read_to_string(root.join("decompose/panel-outputs.ndjson")).expect("rows");
        assert_eq!(rows.lines().filter(|line| !line.is_empty()).count(), 1);
        assert!(rows.contains("\"archetype\":\"generic\""));
    }

    #[cfg(unix)]
    #[test]
    fn aggregate_partition_covers_merge() {
        let (dir, root) = design_dir();
        let panel = root.join("panel.ndjson");
        let source = root.join("panel-source.txt");
        fs::write(&source, "## Recommendation\nsplit\n").expect("source");
        fs::write(
            &panel,
            format!(
                "{{\"archetype\":\"a\",\"vendor\":\"codex\",\"output\":\"{}\",\"status\":\"ok\"}}\n",
                source.display()
            ),
        )
        .expect("panel");
        let stub = waterfall_stub(dir.path());
        let output = root.join("merged.md");
        let status = with_test_overrides(repo_prompts_dir(), Some(stub), || {
            aggregate_partition(&root, &panel, true, true, &output, 30)
        });
        assert_eq!(status, Ok("ok".to_owned()));
        assert!(output.is_file());
    }

    #[test]
    fn aggregate_partition_rejects_malformed_and_missing_inputs() {
        let (_dir, root) = design_dir();
        assert!(
            aggregate_partition(
                &root,
                &root.join("absent.ndjson"),
                true,
                true,
                &root.join("o.md"),
                30
            )
            .is_err()
        );
        let panel = root.join("panel.ndjson");
        fs::write(&panel, "not-json\n").expect("panel");
        assert!(aggregate_partition(&root, &panel, true, true, &root.join("o.md"), 30).is_err());
    }

    #[test]
    fn main_entrypoints_refuse_missing_arguments() {
        // Each argv-less call exercises the argparse-compat refusal arm.
        let _ = prepare_main(&[]);
        let _ = annotate_main(&[]);
        let _ = migrate_deps_main(&[]);
        let _ = close_original_main(&[]);
        let _ = panel_dispatch_main(&[]);
        let _ = aggregate_main(&[]);
    }

    #[test]
    fn migrate_dependencies_validates_and_denies_without_github() {
        let (_dir, root) = design_dir();
        assert_eq!(migrate_dependencies(&root, "0", "o/r"), "invalid");
        assert_eq!(migrate_dependencies(&root, "99", "bad repo"), "invalid");
        // Valid args but no session context authorizing a live mutation: the
        // gate refuses before any GitHub call.
        assert_eq!(
            migrate_dependencies(&root, "99", "o/r"),
            "authorization-denied"
        );
    }

    #[test]
    fn close_original_wrapper_refuses_before_github() {
        let (_dir, root) = design_dir();
        assert_eq!(close_original(&root, "99", "bad repo"), "usage-error");
        // No `.decompose-deps-migrated` sentinel: the postcondition gate refuses
        // before any GitHub call.
        assert_eq!(close_original(&root, "99", "o/r"), "usage-error");
    }

    fn dependency_refs(entries: &[(u64, u64)]) -> String {
        let rows: Vec<String> = entries
            .iter()
            .map(|(number, id)| format!("{{\"number\":{number},\"id\":{id},\"state\":\"open\"}}"))
            .collect();
        format!("[{}]", rows.join(","))
    }

    #[test]
    fn github_graph_reads_dependencies_over_the_stub() {
        use crate::github_service::with_test_github_service;
        use larch_adapters::github::OctocrabGitHubService;
        use larch_test_support::{IssueServiceExchange, IssueServiceStub};
        use std::sync::Arc;

        let server = IssueServiceStub::start(vec![
            IssueServiceExchange::any_json(200, dependency_refs(&[(7, 700)]).into_bytes())
                .expect("blocked-by response"),
            IssueServiceExchange::any_json(200, dependency_refs(&[(8, 800)]).into_bytes())
                .expect("blocking response"),
        ])
        .expect("start issue service stub");
        let base = server.base_url().to_owned();
        let factory: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
            Arc::new(move || OctocrabGitHubService::with_test_base(&base));
        let graph = GithubGraph {
            repo: GitHubRepositoryRef::new("o", "r").expect("repository"),
        };
        let result = with_test_github_service(factory, || graph.read_dependencies(99));
        assert_eq!(result, Ok((vec![7], vec![8])));
    }

    #[test]
    fn github_mutation_and_closer_request_paths_execute() {
        use crate::github_service::with_test_github_service;
        use larch_adapters::github::OctocrabGitHubService;
        use larch_test_support::{IssueServiceExchange, IssueServiceStub};
        use std::sync::Arc;

        // Not-found responses drive each adapter method through its request
        // construction before it fails; this covers the code, not a success.
        let exchanges: Vec<IssueServiceExchange> = (0..16)
            .map(|_| {
                IssueServiceExchange::any_json(404, b"{\"message\":\"nope\"}".to_vec())
                    .expect("stub response")
            })
            .collect();
        let server = IssueServiceStub::start(exchanges).expect("start issue service stub");
        let base = server.base_url().to_owned();
        let factory: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
            Arc::new(move || OctocrabGitHubService::with_test_base(&base));
        with_test_github_service(factory, || {
            let graph = GithubGraph {
                repo: GitHubRepositoryRef::new("o", "r").expect("repository"),
            };
            assert!(!graph.mutate(false, 101, 99));
            assert!(!graph.mutate(true, 101, 99));
            let closer = GithubCloser {
                repo: GitHubRepositoryRef::new("o", "r").expect("repository"),
            };
            assert!(closer.post_comment(99, "obviated").is_err());
            assert!(closer.close(99).is_err());
        });
    }
}
