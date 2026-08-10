//! The Rust owner for the ten `/combine-issues` compatibility verbs.
//!
//! The planning verbs deliberately keep their JSON documents as data: issue
//! text is parsed only for the small dependency grammars below, and every live
//! read and write enters the typed GitHub service.  A combined issue is never
//! allowed to make its sources disappear before its native blocker edges have
//! been copied and verified.

use std::{
    collections::{BTreeMap, BTreeSet},
    ffi::OsString,
    fs,
    io::Write as _,
    path::Path,
    process::ExitCode,
};

use larch_adapters::github::{DependencyEdge, DependencyRef, IssueMutationOwner};
use larch_core::{
    GitHubCloseReason, GitHubIssue, GitHubIssueList, GitHubIssueState, GitHubRepositoryRef,
    GitHubService as _, IssueCreateRequest, deps_compact_json, deps_flat_error,
    json_positive_integer, parse_prose_blockers, parse_prose_blocks, positive_integer,
};
use serde_json::{Map, Value, json};
use tempfile::NamedTempFile;

use crate::{
    argparse_compat::{ParsedCommandLine, missing, parse_with_flags, usage_error},
    blocker_commands::resolve_repo_for,
    github_repository_resolution::repository_ref,
    github_service::with_github_service,
    issue_mutation_support::{authorization_request, authorized, create_with_rollback, flat_error},
};

const USAGE_EXIT: u8 = 2;
const ERROR_CHARS: usize = 500;
const BUSY_PREFIXES: [&str; 6] = [
    "[DESIGNING] ",
    "[IMPLEMENTING] ",
    "[DONE] ",
    "[STALLED] ",
    "[DEBATING] ",
    "[DEBATED] ",
];

/// Dispatch one raw compatibility command from the clap boundary.
pub fn dispatch(verb: &str, arguments: &[OsString]) -> ExitCode {
    match verb {
        "fetch" => fetch(arguments),
        "fetch-deps" => fetch_deps(arguments),
        "list-open" => list_open(arguments),
        "close-eligible" => close_eligible(arguments),
        "plan-inherited" => plan_inherited(arguments),
        "prose-audit" => prose_audit(arguments),
        "plan-audit" => plan_audit(arguments),
        "apply" => apply(arguments),
        "close-sources" => close_sources(arguments),
        "close-stale" => close_stale(arguments),
        _ => ExitCode::from(USAGE_EXIT),
    }
}

fn parsed(
    arguments: &[OsString],
    options: &[&'static str],
    flags: &[&'static str],
    required: &[&'static str],
    usage: &str,
    program: &str,
) -> Result<ParsedCommandLine, ExitCode> {
    let command = parse_with_flags(arguments, options, flags, 0);
    if let Some(error) = command.error() {
        return Err(usage_error(usage, program, &error, USAGE_EXIT));
    }
    let absent: Vec<(&str, bool)> = required
        .iter()
        .map(|name| (*name, command.value(name).is_some()))
        .collect();
    if absent.iter().any(|(_name, present)| !present) {
        return Err(usage_error(usage, program, &missing(&absent), USAGE_EXIT));
    }
    Ok(command)
}

fn value(command: &ParsedCommandLine, name: &str) -> String {
    command
        .value(name)
        .map(|item| item.to_string_lossy().into_owned())
        .unwrap_or_default()
}

fn failure(message: impl AsRef<str>) -> ExitCode {
    eprintln!("ERROR={}", flat_error(message.as_ref(), ERROR_CHARS));
    ExitCode::FAILURE
}

fn emit_json(value: &Value) -> ExitCode {
    println!("{}", deps_compact_json(value));
    ExitCode::SUCCESS
}

const fn bool_text(value: bool) -> &'static str {
    if value { "true" } else { "false" }
}

fn clean_row(value: &str) -> String {
    value.replace(['\n', '\r'], " ")
}

fn issue_numbers(raw: &str, name: &str) -> Result<Vec<u64>, String> {
    if raw.trim().is_empty() {
        return Err(format!("{name} must contain at least one positive integer"));
    }
    let mut result = Vec::new();
    for part in raw.split(',') {
        let token = part.trim();
        let Some(number) = positive_integer(token) else {
            return Err(format!(
                "{name} values must be positive integers: '{token}'"
            ));
        };
        if !result.contains(&number) {
            result.push(number);
        }
    }
    Ok(result)
}

fn read_json(path: &str, description: &str) -> Result<Value, String> {
    let text = fs::read_to_string(path).map_err(|error| {
        if error.kind() == std::io::ErrorKind::NotFound {
            format!("{description}: file not found: {path}")
        } else {
            format!("{description}: could not read {path}: {error}")
        }
    })?;
    serde_json::from_str(&text).map_err(|error| format!("{description}: invalid JSON: {error}"))
}

fn status_ok(value: &Value, description: &str) -> Result<(), String> {
    if let Some(status) = value.get("status")
        && status.as_str().unwrap_or_default() != "ok"
    {
        return Err(format!("{description}: status is {status:?}"));
    }
    Ok(())
}

fn source_map(value: &Value) -> Result<BTreeMap<u64, Vec<u64>>, String> {
    let object = value
        .as_object()
        .ok_or_else(|| "source-to-combined JSON must be an object".to_owned())?;
    let mut result = BTreeMap::new();
    for (raw_source, raw_hosts) in object {
        let Some(source) = positive_integer(raw_source) else {
            return Err("source-to-combined keys must be positive integers".to_owned());
        };
        let values: Vec<&Value> = raw_hosts
            .as_array()
            .map_or_else(|| vec![raw_hosts], |items| items.iter().collect());
        let mut hosts = Vec::new();
        for item in values {
            let Some(host) = json_positive_integer(Some(item)) else {
                return Err("source-to-combined values must be positive integers or lists of positive integers".to_owned());
            };
            if !hosts.contains(&host) {
                hosts.push(host);
            }
        }
        if hosts.is_empty() {
            return Err("source-to-combined values must not be empty".to_owned());
        }
        result.insert(source, hosts);
    }
    Ok(result)
}

fn normal_edge(value: Option<&Value>, description: &str) -> Result<(u64, u64), String> {
    let Some(items) = value.and_then(Value::as_array) else {
        return Err(format!(
            "{description}: edge must be [client_issue, blocker_issue]"
        ));
    };
    if items.len() != 2 {
        return Err(format!(
            "{description}: edge must be [client_issue, blocker_issue]"
        ));
    }
    let (Some(client), Some(blocker)) = (
        json_positive_integer(items.first()),
        json_positive_integer(items.get(1)),
    ) else {
        return Err(format!(
            "{description}: edge values must be positive integers"
        ));
    };
    Ok((client, blocker))
}

fn edge_value(edge: (u64, u64)) -> Value {
    json!([edge.0, edge.1])
}

fn edge_key(edge: (u64, u64)) -> String {
    format!("{}:{}", edge.0, edge.1)
}

fn title_is_oos(title: &str) -> bool {
    title
        .strip_prefix("[OOS]")
        .is_some_and(|suffix| suffix.chars().next().is_some_and(char::is_whitespace))
}

fn title_is_busy(title: &str) -> bool {
    title.starts_with("[LOCKED]")
        || BUSY_PREFIXES.iter().any(|prefix| title.starts_with(prefix))
        || ["[PLANNED]", "[IN PROGRESS]"].iter().any(|prefix| {
            title
                .strip_prefix(prefix)
                .is_some_and(|suffix| suffix.chars().next().is_some_and(char::is_whitespace))
        })
}

const fn state_text(state: GitHubIssueState) -> &'static str {
    match state {
        GitHubIssueState::Open => "open",
        GitHubIssueState::Closed => "closed",
        GitHubIssueState::All => "",
    }
}

fn issue_row(issue: GitHubIssue) -> Value {
    json!({
        "number": issue.number,
        "title": issue.title,
        "state": state_text(issue.state),
        "labels": issue.labels.into_iter().filter_map(|label| (!label.name.is_empty()).then_some(label.name)).collect::<Vec<_>>(),
        "body": issue.body,
    })
}

fn open_rows(value: &Value) -> Result<Vec<Value>, String> {
    let empty = Value::Array(Vec::new());
    let items = value
        .as_object()
        .map_or(value, |object| object.get("issues").unwrap_or(&empty))
        .as_array()
        .ok_or_else(|| "open-issues JSON must contain an issues list".to_owned())?;
    let mut rows = Vec::new();
    for item in items {
        let Some(object) = item.as_object() else {
            continue;
        };
        let Some(number) = json_positive_integer(object.get("number")) else {
            continue;
        };
        rows.push(json!({
            "number": number,
            "title": object.get("title").and_then(Value::as_str).unwrap_or_default(),
            "state": object.get("state").and_then(Value::as_str).unwrap_or_default(),
            "labels": object.get("labels").cloned().unwrap_or_else(|| json!([])),
            "body": object.get("body").and_then(Value::as_str).unwrap_or_default(),
        }));
    }
    Ok(rows)
}

fn combined_rows(value: &Value) -> Result<Vec<Value>, String> {
    let items = value
        .as_array()
        .ok_or_else(|| "combined-issues JSON must be a list".to_owned())?;
    let mut rows = Vec::new();
    for item in items {
        let object = item
            .as_object()
            .ok_or_else(|| "combined-issues entries must be objects".to_owned())?;
        let Some(number) = json_positive_integer(object.get("number")) else {
            return Err("combined-issues entries require positive integer number".to_owned());
        };
        let source_values = object
            .get("source_issues")
            .cloned()
            .unwrap_or_else(|| json!([]));
        let Some(source_values) = source_values.as_array() else {
            return Err("combined-issues source_issues must be a list".to_owned());
        };
        let mut sources: Vec<u64> = source_values
            .iter()
            .filter_map(|item| json_positive_integer(Some(item)))
            .collect();
        sources.sort_unstable();
        rows.push(json!({
            "number": number,
            "title": object.get("title").and_then(Value::as_str).unwrap_or_default(),
            "state": "open",
            "labels": object.get("labels").cloned().unwrap_or_else(|| json!([])),
            "body": object.get("body").and_then(Value::as_str).unwrap_or_default(),
            "source_issues": sources,
        }));
    }
    Ok(rows)
}

fn metadata(open: &[Value], combined: &[Value]) -> BTreeMap<u64, Value> {
    let mut result = BTreeMap::new();
    for row in combined.iter().chain(open) {
        if let Some(number) = json_positive_integer(row.get("number")) {
            result.insert(number, row.clone());
        }
    }
    result
}

fn row_text(row: Option<&Value>, field: &str) -> String {
    row.and_then(|item| item.get(field))
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_owned()
}

fn classify_edge(
    edge: (u64, u64),
    metadata: &BTreeMap<u64, Value>,
    combined_oos: &BTreeSet<u64>,
) -> (&'static str, &'static str) {
    let (Some(client), Some(blocker)) = (metadata.get(&edge.0), metadata.get(&edge.1)) else {
        return ("unknown", "missing issue metadata");
    };
    if !row_text(Some(client), "state").eq_ignore_ascii_case("open") {
        return ("unknown", "client issue is not known open");
    }
    let blocker_state = row_text(Some(blocker), "state");
    if blocker_state.eq_ignore_ascii_case("closed") {
        return (
            "satisfied",
            "blocker issue already closed (dependency satisfied)",
        );
    }
    if !blocker_state.eq_ignore_ascii_case("open") {
        return ("unknown", "blocker issue is not known open");
    }
    if combined_oos.contains(&edge.1) && !title_is_oos(&row_text(Some(client), "title")) {
        return (
            "exception",
            "non-OOS open issue would be blocked by a newly combined [OOS] issue",
        );
    }
    (
        "safe",
        "edge does not block a non-OOS issue on newly combined [OOS] work",
    )
}

fn combined_oos(combined: &[Value], metadata: &BTreeMap<u64, Value>) -> BTreeSet<u64> {
    combined
        .iter()
        .filter_map(|row| json_positive_integer(row.get("number")))
        .filter(|number| title_is_oos(&row_text(metadata.get(number), "title")))
        .collect()
}

fn dependency_numbers(items: &[DependencyRef]) -> Vec<u64> {
    let mut numbers: Vec<u64> = items.iter().map(DependencyRef::issue_number).collect();
    numbers.sort_unstable();
    numbers.dedup();
    numbers
}

fn dependency_warning_code(direction: &str, malformed: bool, message: &str) -> &'static str {
    if malformed {
        return "dependency_json_invalid";
    }
    let message = message.to_ascii_lowercase();
    if direction == "blocking"
        && ["404", "not found", "unavailable", "preview"]
            .iter()
            .any(|needle| message.contains(needle))
    {
        "blocking_endpoint_unavailable"
    } else {
        "dependency_read_failed"
    }
}

fn dependency_entry(data: &Value, source: u64) -> Option<&Value> {
    match data.get("issues")? {
        Value::Object(rows) => rows.get(&source.to_string()).filter(|row| row.is_object()),
        Value::Array(rows) => rows.iter().find(|row| {
            row.is_object()
                && ["source_issue", "number"].iter().any(|field| {
                    json_positive_integer(row.get(*field)).is_some_and(|number| number == source)
                })
        }),
        _ => None,
    }
}

fn resolve_repo(explicit: &str) -> Result<(String, GitHubRepositoryRef), String> {
    let Some(repo) = resolve_repo_for((!explicit.is_empty()).then_some(explicit)) else {
        return Err("Could not determine repository".to_owned());
    };
    let reference =
        repository_ref(&repo).map_err(|()| "Could not determine repository".to_owned())?;
    Ok((repo, reference))
}

// ---------------------------------------------------------------------------
// Fetchers
// ---------------------------------------------------------------------------

fn fetch(arguments: &[OsString]) -> ExitCode {
    let command = match parsed(
        arguments,
        &["--repo"],
        &["--oos"],
        &[],
        "usage: cli.py combine-issues fetch [-h] [--repo REPO] [--oos]",
        "cli.py combine-issues fetch",
    ) {
        Ok(command) => command,
        Err(exit) => return exit,
    };
    let (repo, reference) = match resolve_repo(&value(&command, "--repo")) {
        Ok(resolved) => resolved,
        Err(error) => return failure(error),
    };
    let oos = command.flag("--oos");
    let listed = with_github_service(async |service, cancellation| {
        let request = GitHubIssueList {
            repo: reference,
            state: GitHubIssueState::Open,
            labels: Vec::new(),
            limit: service.transport_policy().limits().items().min(200),
        };
        service
            .list_issues(&request, cancellation)
            .await
            .map_err(|error| error.to_string())
    });
    let Ok(listed) = listed else {
        return failure(format!("Failed to fetch issues from {repo}"));
    };
    let filtered: Vec<Value> = listed
        .into_iter()
        .filter(|issue| !issue.is_pull_request && issue.state == GitHubIssueState::Open)
        .filter(|issue| {
            if oos {
                title_is_oos(&issue.title)
            } else {
                !title_is_busy(&issue.title)
            }
        })
        .map(|issue| {
            json!({
                "number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "labels": issue.labels.into_iter().filter_map(|label| (!label.name.is_empty()).then_some(label.name)).collect::<Vec<_>>(),
            })
        })
        .collect();
    let count = filtered.len();
    let mut file = match NamedTempFile::with_prefix_in("combine-issues-", "/tmp") {
        Ok(file) => file,
        Err(error) => return failure(error.to_string()),
    };
    let payload = deps_compact_json(&Value::Array(filtered));
    if file.write_all(payload.as_bytes()).is_err() || file.write_all(b"\n").is_err() {
        return failure("Could not write combined issue snapshot");
    }
    let path = match file.into_temp_path().keep() {
        Ok(path) => path,
        Err(error) => return failure(error.error.to_string()),
    };
    println!("ISSUES_FILE={}", path.display());
    println!("COUNT={count}");
    ExitCode::SUCCESS
}

fn fetch_deps(arguments: &[OsString]) -> ExitCode {
    let command = match parsed(
        arguments,
        &["--repo", "--issues"],
        &[],
        &["--issues"],
        "usage: cli.py combine-issues fetch-deps [-h] [--repo REPO] --issues ISSUES",
        "cli.py combine-issues fetch-deps",
    ) {
        Ok(command) => command,
        Err(exit) => return exit,
    };
    let issues = match issue_numbers(&value(&command, "--issues"), "--issues") {
        Ok(issues) => issues,
        Err(error) => return failure(error),
    };
    let (_repo, reference) = match resolve_repo(&value(&command, "--repo")) {
        Ok(resolved) => resolved,
        Err(error) => return failure(error),
    };
    let result = with_github_service(async |service, cancellation| {
        let mut entries = Map::new();
        let mut failed = Vec::new();
        let mut warnings = Vec::new();
        for issue in issues {
            let mut read_ok = true;
            let mut blocked_by = Vec::new();
            let mut blocking = Vec::new();
            for (direction, target) in [("blocked_by", false), ("blocking", true)] {
                let read = if target {
                    service
                        .list_blocking(cancellation, reference.owner(), reference.name(), issue)
                        .await
                } else {
                    service
                        .list_blocked_by(cancellation, reference.owner(), reference.name(), issue)
                        .await
                };
                match read {
                    Ok(items) => {
                        if target {
                            blocking = dependency_numbers(&items);
                        } else {
                            blocked_by = dependency_numbers(&items);
                        }
                    }
                    Err(error) => {
                        read_ok = false;
                        let message = deps_flat_error(&error.to_string(), ERROR_CHARS);
                        let code = dependency_warning_code(
                            direction,
                            matches!(
                                error,
                                larch_adapters::github::GitHubOperationError::Malformed(_)
                            ),
                            &message,
                        );
                        failed.push(json!({"source_issue": issue, "direction": direction, "error": message}));
                        warnings.push(json!({"source_issue": issue, "direction": direction, "code": code, "message": message}));
                    }
                }
            }
            entries.insert(
                issue.to_string(),
                json!({"blocked_by": blocked_by, "blocking": blocking, "read_ok": read_ok}),
            );
        }
        Ok(
            json!({"status": "ok", "issues": entries, "failed_issue_reads": failed, "warnings": warnings}),
        )
    });
    match result {
        Ok(payload) => emit_json(&payload),
        Err(error) => failure(error.into_detail()),
    }
}

fn list_open(arguments: &[OsString]) -> ExitCode {
    let command = match parsed(
        arguments,
        &["--repo"],
        &[],
        &[],
        "usage: cli.py combine-issues list-open [-h] [--repo REPO]",
        "cli.py combine-issues list-open",
    ) {
        Ok(command) => command,
        Err(exit) => return exit,
    };
    let (_repo, reference) = match resolve_repo(&value(&command, "--repo")) {
        Ok(resolved) => resolved,
        Err(error) => return failure(error),
    };
    let result = with_github_service(async |service, cancellation| {
        let request = GitHubIssueList {
            repo: reference,
            state: GitHubIssueState::Open,
            labels: Vec::new(),
            limit: service.transport_policy().limits().items(),
        };
        service
            .list_issues(&request, cancellation)
            .await
            .map(|issues| {
                let mut rows: Vec<Value> = issues
                    .into_iter()
                    .filter(|issue| !issue.is_pull_request && issue.state == GitHubIssueState::Open)
                    .map(issue_row)
                    .collect();
                rows.sort_by_key(|row| {
                    json_positive_integer(row.get("number")).unwrap_or_default()
                });
                json!({"status": "ok", "issues": rows, "warnings": []})
            })
            .map_err(|error| {
                let code = if matches!(
                    error.kind(),
                    larch_core::GitHubOperationErrorKind::MalformedResponse
                ) {
                    "json_invalid"
                } else {
                    "gh_api_failed"
                };
                format!("{code}:{error}")
            })
    });
    match result {
        Ok(payload) => emit_json(&payload),
        Err(error) => {
            let detail = error.into_detail();
            let (code, message) = detail
                .split_once(':')
                .unwrap_or(("gh_api_failed", "failed to list open issues"));
            let payload = json!({
                "status": "failed",
                "issues": [],
                "warnings": [{"code": code, "message": if code == "json_invalid" { message } else { "failed to list open issues" }}],
            });
            let _ = emit_json(&payload);
            ExitCode::FAILURE
        }
    }
}

// ---------------------------------------------------------------------------
// Pure planning commands
// ---------------------------------------------------------------------------

#[allow(clippy::too_many_lines)] // One ordered compatibility planner keeps the legacy wire fields adjacent.
fn plan_inherited(arguments: &[OsString]) -> ExitCode {
    let command = match parsed(
        arguments,
        &[
            "--deps-file",
            "--source-to-combined-file",
            "--open-issues-file",
            "--combined-issues-file",
            "--repo",
        ],
        &[],
        &[
            "--deps-file",
            "--source-to-combined-file",
            "--open-issues-file",
            "--combined-issues-file",
        ],
        "usage: cli.py combine-issues plan-inherited [-h] --deps-file DEPS_FILE --source-to-combined-file SOURCE_TO_COMBINED_FILE --open-issues-file OPEN_ISSUES_FILE --combined-issues-file COMBINED_ISSUES_FILE [--repo REPO]",
        "cli.py combine-issues plan-inherited",
    ) {
        Ok(command) => command,
        Err(exit) => return exit,
    };
    let deps = match read_json(&value(&command, "--deps-file"), "deps-file") {
        Ok(data) => data,
        Err(error) => return failure(error),
    };
    let mapping = match read_json(
        &value(&command, "--source-to-combined-file"),
        "source-to-combined-file",
    )
    .and_then(|data| source_map(&data))
    {
        Ok(data) => data,
        Err(error) => return failure(error),
    };
    let open_data = match read_json(&value(&command, "--open-issues-file"), "open-issues-file") {
        Ok(data) => data,
        Err(error) => return failure(error),
    };
    let combined_data = match read_json(
        &value(&command, "--combined-issues-file"),
        "combined-issues-file",
    ) {
        Ok(data) => data,
        Err(error) => return failure(error),
    };
    if let Err(error) =
        status_ok(&deps, "deps-file").and_then(|()| status_ok(&open_data, "open-issues-file"))
    {
        return failure(error);
    }
    let open = match open_rows(&open_data) {
        Ok(rows) => rows,
        Err(error) => return failure(error),
    };
    let combined = match combined_rows(&combined_data) {
        Ok(rows) => rows,
        Err(error) => return failure(error),
    };
    let mut meta = metadata(&open, &combined);
    let oos = combined_oos(&combined, &meta);
    let mut edges: BTreeMap<(u64, u64), BTreeSet<u64>> = BTreeMap::new();
    let mut eligibility: BTreeMap<u64, Vec<String>> = BTreeMap::new();
    let mut self_skipped = 0_u64;
    let mut duplicates = 0_u64;
    let mut warnings = deps
        .get("warnings")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    for (source, hosts) in &mapping {
        let entry = dependency_entry(&deps, *source);
        if !entry
            .and_then(|item| item.get("read_ok"))
            .and_then(Value::as_bool)
            .unwrap_or(false)
        {
            eligibility
                .entry(*source)
                .or_default()
                .push("dependency_read_failed".to_owned());
        }
        let mut add = |client: u64, blocker: u64| {
            if client == blocker {
                self_skipped += 1;
                return;
            }
            let sources = edges.entry((client, blocker)).or_default();
            if !sources.is_empty() {
                duplicates += 1;
            }
            sources.insert(*source);
        };
        for blocker in entry
            .and_then(|item| item.get("blocked_by"))
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
            .filter_map(|item| json_positive_integer(Some(item)))
        {
            for host in hosts {
                for blocker_host in mapping
                    .get(&blocker)
                    .cloned()
                    .unwrap_or_else(|| vec![blocker])
                {
                    add(*host, blocker_host);
                }
            }
        }
        for client in entry
            .and_then(|item| item.get("blocking"))
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
            .filter_map(|item| json_positive_integer(Some(item)))
        {
            for client_host in mapping
                .get(&client)
                .cloned()
                .unwrap_or_else(|| vec![client])
            {
                for host in hosts {
                    add(client_host, *host);
                }
            }
        }
    }
    let explicit_repo = value(&command, "--repo");
    if !explicit_repo.is_empty() {
        match resolve_repo(&explicit_repo) {
            Ok((_repo, reference)) => {
                let missing: Vec<u64> = edges
                    .keys()
                    .map(|edge| edge.1)
                    .filter(|issue| !meta.contains_key(issue))
                    .collect::<BTreeSet<_>>()
                    .into_iter()
                    .collect();
                let refreshed = with_github_service(async |service, cancellation| {
                    let mut rows: Vec<(u64, Result<Value, String>)> = Vec::new();
                    for issue in missing {
                        rows.push((
                            issue,
                            service
                                .issue(&reference, issue, cancellation)
                                .await
                                .map(issue_row)
                                .map_err(|error| deps_flat_error(&error.to_string(), ERROR_CHARS)),
                        ));
                    }
                    Ok::<_, String>(rows)
                });
                match refreshed {
                    Ok(rows) => {
                        for (issue, row) in rows {
                            match row {
                                Ok(row) => {
                                    meta.insert(issue, row);
                                }
                                Err(message) => warnings.push(json!({
                                    "issue": issue,
                                    "code": "blocker_state_read_failed",
                                    "message": message,
                                })),
                            }
                        }
                    }
                    Err(error) => {
                        warnings.push(json!({
                            "code": "blocker_state_read_failed",
                            "message": deps_flat_error(&error.into_detail(), ERROR_CHARS),
                        }));
                    }
                }
            }
            Err(_) => warnings.push(json!({"code": "repo_resolve_failed", "message": "Could not determine repository for blocker enrichment"})),
        }
    }
    let mut safe = Vec::new();
    let mut exception = Vec::new();
    let mut satisfied = Vec::new();
    let mut unknown = Vec::new();
    let mut provenance = Map::new();
    for (edge, sources) in edges {
        let sources: Vec<u64> = sources.into_iter().collect();
        provenance.insert(edge_key(edge), json!(sources));
        let (bucket, reason) = classify_edge(edge, &meta, &oos);
        let record = json!({
            "edge": edge_value(edge), "client_issue": edge.0, "blocker_issue": edge.1,
            "source_issues": sources, "reason": reason,
            "client_title": row_text(meta.get(&edge.0), "title"),
            "blocker_title": row_text(meta.get(&edge.1), "title"),
        });
        match bucket {
            "safe" => safe.push(record),
            "exception" => exception.push(record),
            "satisfied" => satisfied.push(record),
            _ => {
                for source in record
                    .get("source_issues")
                    .and_then(Value::as_array)
                    .into_iter()
                    .flatten()
                    .filter_map(|item| json_positive_integer(Some(item)))
                {
                    let reasons = eligibility.entry(source).or_default();
                    if !reasons
                        .iter()
                        .any(|reason| reason == "unknown_inherited_classification")
                    {
                        reasons.push("unknown_inherited_classification".to_owned());
                    }
                }
                unknown.push(record);
            }
        }
    }
    let initial: Map<String, Value> = mapping
        .keys()
        .map(|source| {
            let reasons = eligibility.remove(source).unwrap_or_default();
            (
                source.to_string(),
                json!({"eligible": reasons.is_empty(), "reasons": reasons}),
            )
        })
        .collect();
    emit_json(&json!({
        "status": "ok", "safe_edges": safe, "exception_edges": exception,
        "satisfied_edges": satisfied, "unknown_edges": unknown,
        "edge_provenance": provenance, "per_source_initial_eligibility": initial,
        "self_edges_skipped": self_skipped, "duplicate_edges_skipped": duplicates,
        "warnings": warnings,
    }))
}

fn records_by_edge(value: &Value, key: &str) -> Result<BTreeMap<(u64, u64), Vec<Value>>, String> {
    let rows = value
        .as_object()
        .and_then(|object| object.get(key))
        .and_then(Value::as_array)
        .ok_or_else(|| format!("{key} JSON must be an object with {key} list"))?;
    let mut result: BTreeMap<(u64, u64), Vec<Value>> = BTreeMap::new();
    for row in rows {
        if !row.is_object() {
            return Err(format!("{key} entries must be objects"));
        }
        let edge = normal_edge(row.get("edge"), key)?;
        result.entry(edge).or_default().push(row.clone());
    }
    Ok(result)
}

fn source_issues(record: &Value) -> Vec<u64> {
    let mut sources: Vec<u64> = record
        .get("source_issues")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter_map(|item| {
            (!item.is_object())
                .then(|| json_positive_integer(Some(item)))
                .flatten()
        })
        .collect();
    sources.sort_unstable();
    sources
}

fn write_outcome(rows: Option<&Vec<Value>>, phases: &[&str]) -> &'static str {
    let mut failed = false;
    for row in rows.into_iter().flatten() {
        if !phases.contains(&row.get("phase").and_then(Value::as_str).unwrap_or_default()) {
            continue;
        }
        match row
            .get("status")
            .and_then(Value::as_str)
            .unwrap_or_default()
        {
            "written" | "already_present" => return "success",
            "failed" | "unresolved" => failed = true,
            _ => {}
        }
    }
    if failed { "failed" } else { "missing" }
}

fn edge_decision(rows: Option<&Vec<Value>>) -> &'static str {
    let mut rows = rows.into_iter().flatten();
    if rows
        .clone()
        .any(|row| row.get("decision").and_then(Value::as_str) == Some("unresolved"))
    {
        return "unresolved";
    }
    if rows
        .clone()
        .any(|row| row.get("decision").and_then(Value::as_str) == Some("approved"))
    {
        return "approved";
    }
    if rows.any(|row| row.get("decision").and_then(Value::as_str) == Some("rejected")) {
        "rejected"
    } else {
        "missing"
    }
}

#[allow(clippy::too_many_lines)] // Eligibility must retain its ordered fail-closed reason accumulation.
fn close_eligible(arguments: &[OsString]) -> ExitCode {
    let command = match parsed(
        arguments,
        &[
            "--inherited-plan-file",
            "--write-results-file",
            "--exception-decisions-file",
            "--source-to-combined-file",
            "--blocked-sources-file",
        ],
        &[],
        &[
            "--inherited-plan-file",
            "--write-results-file",
            "--exception-decisions-file",
            "--source-to-combined-file",
            "--blocked-sources-file",
        ],
        "usage: cli.py combine-issues close-eligible [-h] --inherited-plan-file INHERITED_PLAN_FILE --write-results-file WRITE_RESULTS_FILE --exception-decisions-file EXCEPTION_DECISIONS_FILE --source-to-combined-file SOURCE_TO_COMBINED_FILE --blocked-sources-file BLOCKED_SOURCES_FILE",
        "cli.py combine-issues close-eligible",
    ) {
        Ok(command) => command,
        Err(exit) => return exit,
    };
    let plan = match read_json(
        &value(&command, "--inherited-plan-file"),
        "inherited-plan-file",
    ) {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    let writes = match read_json(
        &value(&command, "--write-results-file"),
        "write-results-file",
    )
    .and_then(|value| records_by_edge(&value, "write_results"))
    {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    let decisions = match read_json(
        &value(&command, "--exception-decisions-file"),
        "exception-decisions-file",
    )
    .and_then(|value| records_by_edge(&value, "decisions"))
    {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    let mapping = match read_json(
        &value(&command, "--source-to-combined-file"),
        "source-to-combined-file",
    )
    .and_then(|value| source_map(&value))
    {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    let blocked = match read_json(
        &value(&command, "--blocked-sources-file"),
        "blocked-sources-file",
    ) {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    if !plan.is_object() {
        return failure("inherited plan must be an object");
    }
    if plan.get("status").and_then(Value::as_str) != Some("ok") {
        return failure("inherited-plan-file: status must be 'ok'");
    }
    let Some(initial) = plan
        .get("per_source_initial_eligibility")
        .and_then(Value::as_object)
    else {
        return failure("inherited-plan-file: per_source_initial_eligibility must be an object");
    };
    let missing: Vec<String> = mapping
        .keys()
        .filter(|source| {
            !initial
                .get(&source.to_string())
                .is_some_and(Value::is_object)
        })
        .map(u64::to_string)
        .collect();
    if !missing.is_empty() {
        return failure(format!(
            "inherited-plan-file: missing per_source_initial_eligibility for source issues: {}",
            missing.join(",")
        ));
    }
    let Some(blocked_object) = blocked.as_object() else {
        return failure("blocked-sources JSON must be an object with blocked_sources list");
    };
    let empty_blocked = Value::Array(Vec::new());
    let blocked_rows = blocked_object
        .get("blocked_sources")
        .unwrap_or(&empty_blocked);
    let Some(blocked_rows) = blocked_rows.as_array() else {
        return failure("blocked-sources JSON must be an object with blocked_sources list");
    };
    let mut reasons: BTreeMap<u64, Vec<String>> =
        mapping.keys().map(|source| (*source, Vec::new())).collect();
    let mut blocked_sources = BTreeSet::new();
    for row in blocked_rows {
        if let Some(source) = row
            .get("source_issue")
            .and_then(|item| json_positive_integer(Some(item)))
        {
            blocked_sources.insert(source);
            reasons.entry(source).or_default().push(
                row.get("reason")
                    .and_then(Value::as_str)
                    .unwrap_or("blocked_source")
                    .to_owned(),
            );
        }
    }
    for (raw_source, state) in initial {
        let Some(source) = positive_integer(raw_source) else {
            continue;
        };
        if !state
            .get("eligible")
            .and_then(Value::as_bool)
            .unwrap_or(true)
        {
            let source_reasons = state
                .get("reasons")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_else(|| vec![json!("initially_ineligible")]);
            reasons.entry(source).or_default().extend(
                source_reasons
                    .into_iter()
                    .map(|item| item.as_str().unwrap_or_default().to_owned()),
            );
        }
    }
    for row in plan
        .get("unknown_edges")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
    {
        if !row.is_object() {
            continue;
        }
        let edge = match normal_edge(row.get("edge"), "unknown_edges") {
            Ok(edge) => edge,
            Err(error) => return failure(error),
        };
        for source in source_issues(row) {
            reasons.entry(source).or_default().push(format!(
                "unknown_inherited_classification:{}",
                edge_key(edge)
            ));
        }
    }
    for row in plan
        .get("safe_edges")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
    {
        if !row.is_object() {
            continue;
        }
        let edge = match normal_edge(row.get("edge"), "safe_edges") {
            Ok(edge) => edge,
            Err(error) => return failure(error),
        };
        if write_outcome(
            writes.get(&edge),
            &["inherited_safe", "inherited_reclassified_safe"],
        ) != "success"
        {
            for source in source_issues(row) {
                reasons.entry(source).or_default().push(format!(
                    "inherited_safe_write_missing_or_failed:{}",
                    edge_key(edge)
                ));
            }
        }
    }
    for row in plan
        .get("exception_edges")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
    {
        if !row.is_object() {
            continue;
        }
        let edge = match normal_edge(row.get("edge"), "exception_edges") {
            Ok(edge) => edge,
            Err(error) => return failure(error),
        };
        let decision = edge_decision(decisions.get(&edge));
        let outcome = write_outcome(
            writes.get(&edge),
            &["inherited_exception", "inherited_reclassified_exception"],
        );
        for source in source_issues(row) {
            let reason = match (decision, outcome) {
                (_, "failed") => Some(format!(
                    "inherited_exception_write_failed:{}",
                    edge_key(edge)
                )),
                ("rejected", _) => Some(format!("inherited_exception_rejected:{}", edge_key(edge))),
                ("approved", "success") => None,
                ("approved", _) => Some(format!(
                    "approved_exception_write_missing_or_failed:{}",
                    edge_key(edge)
                )),
                ("unresolved", _) => {
                    Some(format!("inherited_exception_unresolved:{}", edge_key(edge)))
                }
                _ => Some(format!(
                    "inherited_exception_decision_missing:{}",
                    edge_key(edge)
                )),
            };
            if let Some(reason) = reason {
                reasons.entry(source).or_default().push(reason);
            }
        }
    }
    let mut eligible: BTreeMap<u64, Vec<u64>> = BTreeMap::new();
    let mut ineligible = Vec::new();
    for (source, hosts) in &mapping {
        let mut active: Vec<String> = reasons
            .get(source)
            .cloned()
            .unwrap_or_default()
            .into_iter()
            .filter(|reason| !reason.starts_with("inherited_exception_rejected:"))
            .collect();
        if hosts.len() != 1 {
            active.push("multi_combined_host_closure_unsupported".to_owned());
            reasons
                .entry(*source)
                .or_default()
                .push("multi_combined_host_closure_unsupported".to_owned());
        }
        if blocked_sources.contains(source) || !active.is_empty() {
            ineligible.push(*source);
        } else {
            eligible.entry(hosts[0]).or_default().push(*source);
        }
    }
    let eligible_count = eligible.values().map(Vec::len).sum::<usize>();
    let ineligible_count = ineligible.len();
    let eligible_value: Map<String, Value> = eligible
        .into_iter()
        .map(|(host, sources)| (host.to_string(), json!(sources)))
        .collect();
    let reason_value: Map<String, Value> = reasons
        .into_iter()
        .map(|(source, values)| (source.to_string(), json!(values)))
        .collect();
    emit_json(&json!({
        "eligible_by_combined": eligible_value,
        "ineligible_sources": ineligible,
        "reasons": reason_value,
        "counts": {"eligible_sources": eligible_count, "ineligible_sources": ineligible_count, "blocked_sources": blocked_sources.len()},
    }))
}

fn candidate_rows(value: &Value, description: &str) -> Result<Vec<Value>, String> {
    let empty = Value::Array(Vec::new());
    let rows = value
        .as_object()
        .map_or(value, |object| object.get("candidates").unwrap_or(&empty))
        .as_array()
        .ok_or_else(|| format!("{description}: expected candidate list"))?;
    for row in rows {
        if !row.is_object() {
            return Err(format!("{description}: candidate entries must be objects"));
        }
        normal_edge(row.get("edge"), description)?;
    }
    Ok(rows.clone())
}

fn edges_from_file(value: &Value, description: &str) -> Result<BTreeSet<(u64, u64)>, String> {
    let rows = value
        .as_array()
        .ok_or_else(|| format!("{description}: expected a JSON list"))?;
    rows.iter()
        .map(|row| normal_edge(Some(row), description))
        .collect()
}

#[allow(clippy::too_many_lines)] // Candidate merging and policy classification share one ordered wire contract.
fn plan_audit(arguments: &[OsString]) -> ExitCode {
    let command = match parsed(
        arguments,
        &[
            "--prose-candidates-file",
            "--tier2-candidates-file",
            "--existing-edges-file",
            "--decided-edges-file",
            "--open-issues-file",
            "--combined-issues-file",
        ],
        &[],
        &[
            "--prose-candidates-file",
            "--tier2-candidates-file",
            "--existing-edges-file",
            "--decided-edges-file",
            "--open-issues-file",
            "--combined-issues-file",
        ],
        "usage: cli.py combine-issues plan-audit [-h] --prose-candidates-file PROSE_CANDIDATES_FILE --tier2-candidates-file TIER2_CANDIDATES_FILE --existing-edges-file EXISTING_EDGES_FILE --decided-edges-file DECIDED_EDGES_FILE --open-issues-file OPEN_ISSUES_FILE --combined-issues-file COMBINED_ISSUES_FILE",
        "cli.py combine-issues plan-audit",
    ) {
        Ok(command) => command,
        Err(exit) => return exit,
    };
    let prose = match read_json(
        &value(&command, "--prose-candidates-file"),
        "prose-candidates-file",
    )
    .and_then(|value| candidate_rows(&value, "prose-candidates-file"))
    {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    let tier2 = match read_json(
        &value(&command, "--tier2-candidates-file"),
        "tier2-candidates-file",
    )
    .and_then(|value| candidate_rows(&value, "tier2-candidates-file"))
    {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    let existing = match read_json(
        &value(&command, "--existing-edges-file"),
        "existing-edges-file",
    )
    .and_then(|value| edges_from_file(&value, "existing-edges-file"))
    {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    let decisions = match read_json(
        &value(&command, "--decided-edges-file"),
        "decided-edges-file",
    )
    .and_then(|value| records_by_edge(&value, "decisions"))
    {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    let open_data = match read_json(&value(&command, "--open-issues-file"), "open-issues-file") {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    let combined_data = match read_json(
        &value(&command, "--combined-issues-file"),
        "combined-issues-file",
    ) {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    if let Err(error) = status_ok(&open_data, "open-issues-file") {
        return failure(error);
    }
    let open = match open_rows(&open_data) {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    let combined = match combined_rows(&combined_data) {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    let meta = metadata(&open, &combined);
    let oos = combined_oos(&combined, &meta);
    let mut merged: BTreeMap<(u64, u64), (Value, bool)> = BTreeMap::new();
    let mut duplicate = 0_u64;
    for (row, is_tier2) in prose
        .into_iter()
        .map(|row| (row, false))
        .chain(tier2.into_iter().map(|row| (row, true)))
    {
        let edge = match normal_edge(row.get("edge"), "candidate") {
            Ok(edge) => edge,
            Err(error) => return failure(error),
        };
        let decisions_for_edge = decisions.get(&edge);
        let rejected_or_unresolved = decisions_for_edge.is_some_and(|rows| {
            rows.iter().any(|row| {
                matches!(
                    row.get("decision").and_then(Value::as_str),
                    Some("rejected" | "unresolved")
                )
            })
        });
        if existing.contains(&edge) || rejected_or_unresolved {
            duplicate += 1;
            continue;
        }
        match merged.get(&edge) {
            // The Python wire lets any semantic-tagged candidate supersede an
            // earlier non-semantic candidate.  Its origin still matters below
            // for the Tier-2 policy gate, but not for this dedupe choice.
            Some((previous, _))
                if !(row.get("source_kind").and_then(Value::as_str) == Some("tier2_semantic")
                    && previous.get("source_kind").and_then(Value::as_str)
                        != Some("tier2_semantic")) =>
            {
                duplicate += 1;
            }
            Some(_) => {
                duplicate += 1;
                merged.insert(edge, (row, is_tier2));
            }
            None => {
                merged.insert(edge, (row, is_tier2));
            }
        }
    }
    let mut auto = Vec::new();
    let mut approval = Vec::new();
    let mut rejected = Vec::new();
    for (edge, (row, is_tier2)) in merged {
        let (bucket, default_reason) = classify_edge(edge, &meta, &oos);
        let mut output = row.as_object().cloned().unwrap_or_default();
        output.insert("client_issue".to_owned(), json!(edge.0));
        output.insert("blocker_issue".to_owned(), json!(edge.1));
        let reason = row
            .get("reason")
            .and_then(Value::as_str)
            .filter(|reason| !reason.is_empty())
            .unwrap_or(default_reason);
        output.insert("reason".to_owned(), json!(reason));
        let source_kind = row
            .get("source_kind")
            .and_then(Value::as_str)
            .unwrap_or_default();
        if is_tier2 && source_kind != "tier2_semantic" {
            output.insert(
                "policy_reason".to_owned(),
                json!("tier2 candidate must declare source_kind=tier2_semantic"),
            );
            rejected.push(Value::Object(output));
        } else if source_kind == "tier2_semantic"
            && !["low", "medium", "high"].contains(
                &row.get("confidence")
                    .and_then(Value::as_str)
                    .unwrap_or_default(),
            )
        {
            output.insert(
                "policy_reason".to_owned(),
                json!("tier2 candidate missing low, medium, or high confidence"),
            );
            rejected.push(Value::Object(output));
        } else if bucket == "unknown" {
            output.insert("policy_reason".to_owned(), json!(default_reason));
            rejected.push(Value::Object(output));
        } else if source_kind == "tier2_semantic" || bucket == "exception" {
            output.insert(
                "approval_reason".to_owned(),
                json!(if source_kind == "tier2_semantic" {
                    "Tier-2 semantic edge requires approval"
                } else {
                    default_reason
                }),
            );
            approval.push(Value::Object(output));
        } else {
            auto.push(Value::Object(output));
        }
    }
    emit_json(
        &json!({"auto_write_edges": auto, "approval_required_edges": approval, "policy_rejected_edges": rejected, "duplicate_edges_skipped": duplicate, "warnings": []}),
    )
}

// ---------------------------------------------------------------------------
// Prose audit
// ---------------------------------------------------------------------------

#[allow(clippy::too_many_lines)] // The scan's stable source order is part of the published candidate evidence.
fn prose_audit(arguments: &[OsString]) -> ExitCode {
    let command = match parsed(
        arguments,
        &[
            "--repo",
            "--combined-issues",
            "--open-issues-file",
            "--existing-edges-file",
            "--source-to-combined-file",
        ],
        &[],
        &[
            "--repo",
            "--combined-issues",
            "--open-issues-file",
            "--existing-edges-file",
            "--source-to-combined-file",
        ],
        "usage: cli.py combine-issues prose-audit [-h] --repo REPO --combined-issues COMBINED_ISSUES --open-issues-file OPEN_ISSUES_FILE --existing-edges-file EXISTING_EDGES_FILE --source-to-combined-file SOURCE_TO_COMBINED_FILE",
        "cli.py combine-issues prose-audit",
    ) {
        Ok(command) => command,
        Err(exit) => return exit,
    };
    let combined = match issue_numbers(&value(&command, "--combined-issues"), "--combined-issues") {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    let open_data = match read_json(&value(&command, "--open-issues-file"), "open-issues-file") {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    if let Err(error) = status_ok(&open_data, "open-issues-file") {
        return failure(error);
    }
    let open = match open_rows(&open_data) {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    let existing = match read_json(
        &value(&command, "--existing-edges-file"),
        "existing-edges-file",
    )
    .and_then(|value| edges_from_file(&value, "existing-edges-file"))
    {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    let mapping = match read_json(
        &value(&command, "--source-to-combined-file"),
        "source-to-combined-file",
    )
    .and_then(|value| source_map(&value))
    {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    let (_repo, reference) = match resolve_repo(&value(&command, "--repo")) {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    let combined_set: BTreeSet<u64> = combined.iter().copied().collect();
    let mut initial = metadata(&open, &[]);
    for number in &combined {
        initial.entry(*number).or_insert_with(
            || json!({"number": number, "title": "", "state": "", "labels": [], "body": ""}),
        );
    }
    let scan: BTreeSet<u64> = initial.keys().copied().collect();
    let result = with_github_service(async |service, cancellation| {
        let mut meta = initial;
        for issue in &scan {
            let item = service
                .issue(&reference, *issue, cancellation)
                .await
                .map_err(|error| format!("issue_view_failed:{issue}:{error}"))?;
            meta.insert(*issue, issue_row(item));
        }
        let mut candidates = Vec::new();
        let mut seen = BTreeSet::new();
        for issue in &scan {
            if !row_text(meta.get(issue), "state").eq_ignore_ascii_case("open") {
                continue;
            }
            let mut documents = vec![(row_text(meta.get(issue), "body"), None)];
            let comments = service
                .list_comments(&reference, *issue, cancellation)
                .await
                .map_err(|error| format!("comments_read_failed:{issue}:{error}"))?;
            documents.extend(
                comments
                    .into_iter()
                    .map(|comment| (comment.body, Some(comment.id))),
            );
            for (text, comment_id) in documents {
                for (reference_issue, kind) in parse_prose_blockers(&text)
                    .into_iter()
                    .map(|number| (number, "blocked_by"))
                    .chain(
                        parse_prose_blocks(&text)
                            .into_iter()
                            .map(|number| (number, "blocks")),
                    )
                {
                    let current_hosts = mapping.get(issue).cloned().unwrap_or_else(|| vec![*issue]);
                    let reference_hosts = mapping
                        .get(&reference_issue)
                        .cloned()
                        .unwrap_or_else(|| vec![reference_issue]);
                    for current in &current_hosts {
                        for mapped_reference in &reference_hosts {
                            let edge = if kind == "blocked_by" {
                                (*current, *mapped_reference)
                            } else {
                                (*mapped_reference, *current)
                            };
                            if edge.0 == edge.1
                                || existing.contains(&edge)
                                || seen.contains(&edge)
                                || !meta.contains_key(&edge.0)
                                || !meta.contains_key(&edge.1)
                                || !row_text(meta.get(&edge.0), "state")
                                    .eq_ignore_ascii_case("open")
                                || !row_text(meta.get(&edge.1), "state")
                                    .eq_ignore_ascii_case("open")
                                || (!combined_set.contains(&edge.0)
                                    && !combined_set.contains(&edge.1))
                            {
                                continue;
                            }
                            let mut row = Map::new();
                            row.insert("edge".to_owned(), edge_value(edge));
                            row.insert("source_kind".to_owned(), json!("tier1_prose"));
                            row.insert("confidence".to_owned(), json!("explicit"));
                            row.insert(
                                "evidence_kind".to_owned(),
                                json!(if comment_id.is_some() {
                                    "comment"
                                } else {
                                    "body"
                                }),
                            );
                            row.insert("evidence_issue".to_owned(), json!(issue));
                            row.insert("reason".to_owned(), json!(if kind == "blocked_by" { format!("issue #{current} prose says it is blocked by #{mapped_reference}") } else { format!("issue #{current} prose says it blocks #{mapped_reference}") }));
                            if let Some(comment_id) = comment_id {
                                row.insert("evidence_comment_id".to_owned(), json!(comment_id));
                            }
                            seen.insert(edge);
                            candidates.push(Value::Object(row));
                        }
                    }
                }
            }
        }
        Ok(json!({"status": "ok", "candidates": candidates, "warnings": []}))
    });
    match result {
        Ok(payload) => emit_json(&payload),
        Err(error) => {
            let detail = error.into_detail();
            let mut parts = detail.splitn(3, ':');
            let code = parts.next().unwrap_or("issue_view_failed");
            let issue = parts
                .next()
                .and_then(|value| value.parse::<u64>().ok())
                .unwrap_or_default();
            let payload = json!({"status": "failed", "candidates": [], "warnings": [{"issue": issue, "code": code, "message": code.replace('_', " ")} ]});
            let _ = emit_json(&payload);
            ExitCode::FAILURE
        }
    }
}

// ---------------------------------------------------------------------------
// Live mutations
// ---------------------------------------------------------------------------

#[derive(Clone)]
struct MutationArguments {
    context_file: String,
    run_id: String,
    trusted_root: String,
    operator_invoked: bool,
}

fn mutation_arguments(command: &ParsedCommandLine) -> MutationArguments {
    MutationArguments {
        context_file: value(command, "--context-file"),
        run_id: value(command, "--run-id"),
        trusted_root: value(command, "--trusted-root"),
        operator_invoked: command.flag("--operator-invoked"),
    }
}

fn ensure_authorized(arguments: &MutationArguments) -> Result<(), String> {
    authorized(&authorization_request(
        &arguments.context_file,
        &arguments.run_id,
        &arguments.trusted_root,
        arguments.operator_invoked,
    ))
    .map_err(|reason| format!("unauthorized-mutation:{reason}"))
}

fn combined_comment(source: u64, combined: u64) -> String {
    format!(
        "Combined into #{combined}\n\n<!-- larch:combined-away source=#{source} target=#{combined} -->"
    )
}

fn blockers_by_number(items: &[DependencyRef]) -> BTreeMap<u64, u64> {
    items
        .iter()
        .map(|item| (item.issue_number(), item.issue_id()))
        .collect()
}

#[allow(clippy::too_many_lines)] // Creation, edge transfer, and source closure are one fail-closed transaction.
fn apply(arguments: &[OsString]) -> ExitCode {
    let options = [
        "--title",
        "--body-file",
        "--source-issues",
        "--repo",
        "--context-file",
        "--run-id",
        "--trusted-root",
    ];
    let flags = ["--dry-run", "--defer-close", "--operator-invoked"];
    let command = match parsed(
        arguments,
        &options,
        &flags,
        &["--title", "--body-file", "--source-issues"],
        "usage: cli.py combine-issues apply [-h] --title TITLE --body-file BODY_FILE --source-issues SOURCE_ISSUES [--repo REPO] [--dry-run] [--defer-close]",
        "cli.py combine-issues apply",
    ) {
        Ok(command) => command,
        Err(exit) => return exit,
    };
    let body_path = value(&command, "--body-file");
    let body = match fs::read_to_string(&body_path) {
        Ok(body) if Path::new(&body_path).is_file() => body,
        _ => return failure(format!("Missing or unreadable --body-file: {body_path}")),
    };
    let (_repo, reference) = match resolve_repo(&value(&command, "--repo")) {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    let raw_sources = value(&command, "--source-issues");
    if raw_sources.split(',').all(|item| item.trim().is_empty()) {
        return failure("No source issues provided");
    }
    let sources = match issue_numbers(&raw_sources, "--source-issues") {
        Ok(value) => value,
        Err(error) => return failure(error),
    };
    let source_set: BTreeSet<u64> = sources.iter().copied().collect();
    let title = value(&command, "--title");
    if command.flag("--dry-run") {
        println!("DRY_RUN=true");
        println!("WOULD_CREATE={}", clean_row(&title));
        println!(
            "WOULD_CLOSE={} issues: {}",
            sources.len(),
            sources
                .iter()
                .map(u64::to_string)
                .collect::<Vec<_>>()
                .join(",")
        );
        if command.flag("--defer-close") {
            println!("CLOSING_DEFERRED=true");
        }
        return ExitCode::SUCCESS;
    }
    let mutation = mutation_arguments(&command);
    if let Err(error) = ensure_authorized(&mutation) {
        return failure(error);
    }
    let defer_close = command.flag("--defer-close");
    let result = with_github_service(async |service, cancellation| {
        let authorization = authorization_request(
            &mutation.context_file,
            &mutation.run_id,
            &mutation.trusted_root,
            mutation.operator_invoked,
        );
        // Read every dependency before creating an issue. A transient or
        // unavailable endpoint therefore cannot leave an untracked partial
        // combination behind, and closed dependencies remain part of the
        // combined issue's native graph history.
        let mut inherited: BTreeMap<u64, u64> = BTreeMap::new();
        if !defer_close {
            for source in &sources {
                let dependencies = service
                    .list_blocked_by(cancellation, reference.owner(), reference.name(), *source)
                    .await
                    .map_err(|error| {
                        format!("cannot verify source #{source} dependencies: {error}")
                    })?;
                inherited.extend(blockers_by_number(&dependencies));
            }
        }
        let request = IssueCreateRequest {
            repository: reference.clone(),
            title: title.clone(),
            body: body.clone(),
            labels: Vec::new(),
        };
        let created = create_with_rollback(service, cancellation, &authorization, &request)
            .await
            .map_err(|(error, rollback)| {
                let rollback = rollback
                    .map(|(issue, outcome)| {
                        format!("; orphan #{issue} rollback={}", outcome.is_ok())
                    })
                    .unwrap_or_default();
                format!("{}{}", error.message(), rollback)
            })?;
        let mut applied = 0_usize;
        let mut failed = Vec::new();
        let mut combined_blocker_ids = BTreeSet::new();
        if !defer_close {
            for (blocker_number, blocker_id) in &inherited {
                let edge = DependencyEdge {
                    owner: reference.owner(),
                    repo: reference.name(),
                    client_issue: created.number,
                    blocker_id: *blocker_id,
                    expected_updated_at: None,
                };
                match service
                    .add_blocked_by(cancellation, &authorization, edge)
                    .await
                {
                    Ok(_) => applied += 1,
                    Err(error) => failed.push(format!(
                        "#{blocker_number}: {}",
                        deps_flat_error(&error.to_string(), ERROR_CHARS)
                    )),
                }
            }
            // The dependency adapter already proves each write.  One final
            // aggregate read catches a partial batch before any source close.
            if failed.is_empty() {
                match service
                    .list_blocked_by(
                        cancellation,
                        reference.owner(),
                        reference.name(),
                        created.number,
                    )
                    .await
                {
                    Ok(current) => {
                        let current_ids: BTreeSet<u64> =
                            current.iter().map(DependencyRef::issue_id).collect();
                        combined_blocker_ids.clone_from(&current_ids);
                        for (number, id) in &inherited {
                            if !current_ids.contains(id) {
                                failed.push(format!(
                                    "#{number}: missing from combined dependency read-back"
                                ));
                            }
                        }
                    }
                    Err(error) => failed.push(format!(
                        "combined dependency read-back failed: {}",
                        deps_flat_error(&error.to_string(), ERROR_CHARS)
                    )),
                }
            }
        }
        let created_value = json!({"number": created.number, "url": created.url, "id": created.id});
        if !failed.is_empty() {
            return Ok(
                json!({"created": created_value, "inherited": inherited.len(), "applied": applied, "failed": failed, "closed": 0_usize, "partial": true}),
            );
        }
        if defer_close {
            return Ok(
                json!({"created": created_value, "inherited": inherited.len(), "applied": applied, "closed": 0_usize, "partial": false}),
            );
        }
        let owner = IssueMutationOwner::new(service);
        let mut closed = 0_usize;
        let mut warnings = Vec::new();
        for source in &sources {
            let Ok(source_blockers) = service
                .list_blocked_by(cancellation, reference.owner(), reference.name(), *source)
                .await
            else {
                warnings.push(format!(
                    "Skipped #{source}: could not verify source dependency state"
                ));
                continue;
            };
            if let Some(missing) = source_blockers
                .iter()
                .filter(|blocker| blocker.is_open())
                .find(|blocker| {
                    !source_set.contains(&blocker.issue_number())
                        && !combined_blocker_ids.contains(&blocker.issue_id())
                })
            {
                warnings.push(format!(
                    "Skipped #{source}: combined issue is missing inherited blocker #{}",
                    missing.issue_number()
                ));
                continue;
            }
            match owner
                .close_with_comment(
                    cancellation,
                    &authorization,
                    &reference,
                    *source,
                    GitHubCloseReason::Completed,
                    Some(&combined_comment(*source, created.number)),
                )
                .await
            {
                Ok(_) => closed += 1,
                Err(error) => {
                    warnings.push(format!("Failed to close #{source}: {}", error.reason()));
                }
            }
        }
        Ok(
            json!({"created": created_value, "inherited": inherited.len(), "applied": applied, "closed": closed, "warnings": warnings, "partial": !warnings.is_empty()}),
        )
    });
    let payload = match result {
        Ok(payload) => payload,
        Err(error) => return failure(error.into_detail()),
    };
    let created = payload.get("created").expect("created receipt is present");
    let combined = created
        .get("number")
        .and_then(Value::as_u64)
        .unwrap_or_default();
    let url = created
        .get("url")
        .and_then(Value::as_str)
        .unwrap_or_default();
    let safe_url = flat_error(url, ERROR_CHARS);
    println!("DRY_RUN=false");
    println!("COMBINED_ISSUE={combined}");
    if defer_close {
        let mapping: Map<String, Value> = sources
            .iter()
            .map(|source| (source.to_string(), json!(combined)))
            .collect();
        println!(
            "SOURCE_ISSUES={}",
            sources
                .iter()
                .map(u64::to_string)
                .collect::<Vec<_>>()
                .join(",")
        );
        println!(
            "SOURCE_TO_COMBINED_JSON_FRAGMENT={}",
            serde_json::to_string(&Value::Object(mapping)).expect("mapping serializes")
        );
        println!("CLOSING_DEFERRED=true");
        println!("CLOSED_ISSUES=0");
        return ExitCode::SUCCESS;
    }
    if let Some(failed) = payload.get("failed").and_then(Value::as_array)
        && !failed.is_empty()
    {
        println!("COMBINED_URL={safe_url}");
        eprintln!(
            "WARNING=Combined issue dependency transfer is partial: {}",
            failed
                .iter()
                .filter_map(Value::as_str)
                .collect::<Vec<_>>()
                .join("; ")
        );
        println!(
            "INHERITED_EDGES={}",
            payload
                .get("inherited")
                .and_then(Value::as_u64)
                .unwrap_or_default()
        );
        println!(
            "APPLIED_EDGES={}",
            payload
                .get("applied")
                .and_then(Value::as_u64)
                .unwrap_or_default()
        );
        println!("CLOSED_ISSUES=0");
        println!("PARTIAL=true");
        return ExitCode::SUCCESS;
    }
    if payload.get("partial").and_then(Value::as_bool) == Some(true)
        && let Some(warnings) = payload.get("warnings").and_then(Value::as_array)
        && !warnings.is_empty()
    {
        eprintln!(
            "WARNING={}",
            warnings
                .iter()
                .filter_map(Value::as_str)
                .collect::<Vec<_>>()
                .join("; ")
        );
        // A close can fail after the combined issue and every inherited edge
        // have committed.  Keep that durable reference on the contract stream
        // so the operator can recover the surviving partial combination.
        println!("COMBINED_URL={safe_url}");
        println!("PARTIAL=true");
    }
    println!(
        "CLOSED_ISSUES={}",
        payload
            .get("closed")
            .and_then(Value::as_u64)
            .unwrap_or_default()
    );
    ExitCode::SUCCESS
}

fn close_sources(arguments: &[OsString]) -> ExitCode {
    close_batch(arguments, true)
}

fn close_stale(arguments: &[OsString]) -> ExitCode {
    close_batch(arguments, false)
}

#[allow(clippy::too_many_lines)] // Batch closure keeps preflight, evidence, and each durable result in order.
fn close_batch(arguments: &[OsString], combined_mode: bool) -> ExitCode {
    let (options, required, usage, program) = if combined_mode {
        (
            &[
                "--repo",
                "--combined-issue",
                "--source-issues",
                "--context-file",
                "--run-id",
                "--trusted-root",
            ][..],
            &["--combined-issue", "--source-issues"][..],
            "usage: cli.py combine-issues close-sources [-h] [--repo REPO] --combined-issue COMBINED_ISSUE --source-issues SOURCE_ISSUES",
            "cli.py combine-issues close-sources",
        )
    } else {
        (
            &[
                "--issues",
                "--repo",
                "--reason",
                "--comment-file",
                "--context-file",
                "--run-id",
                "--trusted-root",
            ][..],
            &["--issues", "--reason"][..],
            "usage: cli.py combine-issues close-stale [-h] --issues ISSUES [--repo REPO] --reason REASON [--comment-file COMMENT_FILE] [--dry-run]",
            "cli.py combine-issues close-stale",
        )
    };
    let flags: &[&str] = if combined_mode {
        &["--operator-invoked"]
    } else {
        &["--dry-run", "--operator-invoked"]
    };
    let command = match parsed(arguments, options, flags, required, usage, program) {
        Ok(command) => command,
        Err(exit) => return exit,
    };
    let raw_sources = if combined_mode {
        value(&command, "--source-issues")
    } else {
        value(&command, "--issues")
    };
    let name = if combined_mode {
        "--source-issues"
    } else {
        "--issues"
    };
    let reason = value(&command, "--reason");
    if !combined_mode && !["completed", "not planned"].contains(&reason.as_str()) {
        return failure("--reason must be one of: completed, not planned");
    }
    // Python resolved the post-combination repository before it parsed the
    // source CSV. Preserve that failure ordering while the stale-close path
    // keeps its dry-run free of repository access.
    let resolved_combined_repo = if combined_mode {
        match resolve_repo(&value(&command, "--repo")) {
            Ok(value) => Some(value),
            Err(error) => return failure(error),
        }
    } else {
        None
    };
    let sources = match issue_numbers(&raw_sources, name) {
        Ok(sources) => sources,
        Err(error) => return failure(error),
    };
    let source_set: BTreeSet<u64> = sources.iter().copied().collect();
    let comment = if combined_mode {
        None
    } else {
        let path = value(&command, "--comment-file");
        if path.is_empty() {
            None
        } else {
            match fs::read_to_string(&path) {
                Ok(value) if Path::new(&path).is_file() => Some(value),
                _ => return failure(format!("Missing or unreadable --comment-file: {path}")),
            }
        }
    };
    if !combined_mode && command.flag("--dry-run") {
        println!("DRY_RUN=true");
        println!(
            "WOULD_CLOSE={}",
            sources
                .iter()
                .map(u64::to_string)
                .collect::<Vec<_>>()
                .join(",")
        );
        println!("CLOSED_ISSUES=0");
        println!("PARTIAL=false");
        return ExitCode::SUCCESS;
    }
    let (_repo, reference) = match resolved_combined_repo {
        Some(value) => value,
        None => match resolve_repo(&value(&command, "--repo")) {
            Ok(value) => value,
            Err(error) => return failure(error),
        },
    };
    let combined = if combined_mode {
        match positive_integer(&value(&command, "--combined-issue")) {
            Some(value) => Some(value),
            None => return failure("--combined-issue must be a positive integer"),
        }
    } else {
        None
    };
    let mutation = mutation_arguments(&command);
    if let Err(error) = ensure_authorized(&mutation) {
        return failure(error);
    }
    let result = with_github_service(async |service, cancellation| {
        let authorization = authorization_request(
            &mutation.context_file,
            &mutation.run_id,
            &mutation.trusted_root,
            mutation.operator_invoked,
        );
        let mut warnings = Vec::new();
        let combined_blockers = if let Some(combined) = combined {
            match service.issue(&reference, combined, cancellation).await {
                Err(_) => {
                    warnings.push(
                        "Skipped source closure: could not refresh combined issue state".to_owned(),
                    );
                    return Ok((0_usize, warnings));
                }
                Ok(target) if target.state != GitHubIssueState::Open => {
                    warnings.push(format!(
                        "Skipped source closure: combined issue is not open ({})",
                        state_text(target.state)
                    ));
                    return Ok((0_usize, warnings));
                }
                Ok(_) => {
                    let Ok(items) = service
                        .list_blocked_by(
                            cancellation,
                            reference.owner(),
                            reference.name(),
                            combined,
                        )
                        .await
                    else {
                        warnings.push(
                            "Skipped source closure: could not verify combined issue dependencies"
                                .to_owned(),
                        );
                        return Ok((0_usize, warnings));
                    };
                    Some(
                        items
                            .into_iter()
                            .map(|blocker| blocker.issue_id())
                            .collect::<BTreeSet<_>>(),
                    )
                }
            }
        } else {
            None
        };
        let owner = IssueMutationOwner::new(service);
        let mut closed = 0_usize;
        for source in &sources {
            let current = service.issue(&reference, *source, cancellation).await;
            let skip = match current {
                Err(_) => Some("could not refresh source issue state".to_owned()),
                Ok(issue) if issue.state != GitHubIssueState::Open => Some(format!(
                    "source issue is not open ({})",
                    state_text(issue.state)
                )),
                Ok(issue) if title_is_busy(&issue.title) => {
                    Some("source issue has busy title prefix".to_owned())
                }
                Ok(_) => None,
            };
            if let Some(skip) = skip {
                warnings.push(format!("Skipped #{source}: {skip}"));
                continue;
            }
            if let Some(target_blockers) = &combined_blockers {
                let Ok(inherited) = service
                    .list_blocked_by(cancellation, reference.owner(), reference.name(), *source)
                    .await
                else {
                    warnings.push(format!(
                        "Skipped #{source}: could not verify source dependency state"
                    ));
                    continue;
                };
                if let Some(missing) =
                    inherited
                        .iter()
                        .filter(|blocker| blocker.is_open())
                        .find(|blocker| {
                            !source_set.contains(&blocker.issue_number())
                                && !target_blockers.contains(&blocker.issue_id())
                        })
                {
                    warnings.push(format!(
                        "Skipped #{source}: combined issue is missing inherited blocker #{}",
                        missing.issue_number()
                    ));
                    continue;
                }
            }
            let close_reason = if reason == "not planned" {
                GitHubCloseReason::NotPlanned
            } else {
                GitHubCloseReason::Completed
            };
            let note = combined
                .map(|target| combined_comment(*source, target))
                .or_else(|| comment.clone());
            match owner
                .close_with_comment(
                    cancellation,
                    &authorization,
                    &reference,
                    *source,
                    close_reason,
                    note.as_deref(),
                )
                .await
            {
                Ok(_) => closed += 1,
                Err(error) => {
                    warnings.push(format!("Failed to close #{source}: {}", error.reason()));
                }
            }
        }
        Ok((closed, warnings))
    });
    let (closed, warnings) = match result {
        Ok(value) => value,
        Err(error) => return failure(error.into_detail()),
    };
    if !warnings.is_empty() {
        eprintln!("WARNING={}", warnings.join("; "));
    }
    println!("CLOSED_ISSUES={closed}");
    println!("PARTIAL={}", bool_text(!warnings.is_empty()));
    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests {
    use super::{
        apply, bool_text, candidate_rows, classify_edge, close_sources, combined_comment,
        combined_rows, dependency_entry, dependency_warning_code, dispatch, edges_from_file, fetch,
        fetch_deps, issue_numbers, list_open, normal_edge, open_rows, plan_inherited, prose_audit,
        read_json, records_by_edge, source_map, state_text, status_ok, title_is_busy, title_is_oos,
        write_outcome,
    };
    use crate::github_service::with_test_github_service;
    use larch_adapters::github::OctocrabGitHubService;
    use larch_core::GitHubIssueState;
    use larch_test_support::{IssueServiceExchange, IssueServiceStub};
    use serde_json::{Value, json};
    use std::{
        collections::{BTreeMap, BTreeSet},
        ffi::OsString,
        fs,
        path::PathBuf,
        process::ExitCode,
        sync::Arc,
    };
    use tempfile::TempDir;

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    #[allow(clippy::needless_pass_by_value)] // Inline JSON fixtures keep the request sequence readable.
    fn response(status: u16, body: Value) -> IssueServiceExchange {
        IssueServiceExchange::any_json(status, body.to_string()).expect("valid response")
    }

    fn service(
        exchanges: impl IntoIterator<Item = IssueServiceExchange>,
    ) -> (
        Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync>,
        IssueServiceStub,
    ) {
        let server = IssueServiceStub::start(exchanges).expect("start issue service stub");
        let base_url = server.base_url().to_owned();
        let factory: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
            Arc::new(move || OctocrabGitHubService::with_test_base(&base_url));
        (factory, server)
    }

    fn issue(number: u64, id: u64, title: &str, body: &str, state: &str) -> Value {
        let mut value: Value = serde_json::from_str(include_str!(
            "../../larch-adapters/fixtures/github_issue.json"
        ))
        .expect("valid issue fixture");
        value["id"] = json!(id);
        value["number"] = json!(number);
        value["title"] = json!(title);
        value["body"] = json!(body);
        value["state"] = json!(state);
        value["updated_at"] = json!("2026-07-19T00:00:00Z");
        if state == "closed" {
            value["closed_at"] = json!("2026-07-19T00:01:00Z");
        }
        value
    }

    fn created_issue(number: u64, id: u64, title: &str, body: &str) -> Value {
        let mut value = issue(number, id, title, body, "open");
        value["html_url"] = json!(format!("https://github.com/o/r/issues/{number}"));
        value["labels"] = json!([]);
        value
    }

    fn comment(body: &str) -> Value {
        let issue = issue(1, 10, "source", "", "open");
        json!({
            "id": 11,
            "node_id": "C_11",
            "url": "https://example.invalid/comments/11",
            "html_url": "https://example.invalid/issues/1#issuecomment-11",
            "body": body,
            "user": issue["user"],
            "created_at": "2026-07-19T00:00:00Z",
            "updated_at": "2026-07-19T00:00:00Z"
        })
    }

    fn write_json(temp: &TempDir, name: &str, value: &Value) -> String {
        let path = temp.path().join(name);
        fs::write(&path, serde_json::to_vec(value).expect("JSON fixture")).expect("write fixture");
        path.to_string_lossy().into_owned()
    }

    fn fetch_snapshots() -> BTreeSet<PathBuf> {
        fs::read_dir("/tmp")
            .expect("read temporary directory")
            .flatten()
            .map(|entry| entry.path())
            .filter(|path| {
                path.file_name()
                    .and_then(|name| name.to_str())
                    .is_some_and(|name| name.starts_with("combine-issues-"))
            })
            .collect()
    }

    #[test]
    fn title_filter_keeps_designed_and_rejects_legacy_busy_titles() {
        assert!(!title_is_busy("[DESIGNED] ready"));
        assert!(title_is_busy("[IN PROGRESS] old run"));
        assert!(title_is_busy("[IN PROGRESS]\told run"));
        assert!(title_is_busy("[LOCKED] no"));
        assert!(title_is_oos("[OOS]\tready"));
    }

    #[test]
    fn source_map_promotes_scalars_and_deduplicates_hosts() {
        let map = source_map(&json!({"1": [100, 100], "2": 101})).expect("valid map");
        assert_eq!(map.get(&1), Some(&vec![100]));
        assert_eq!(map.get(&2), Some(&vec![101]));
        assert_eq!(issue_numbers("1, 2,1", "--issues"), Ok(vec![1, 2]));
    }

    #[test]
    fn blocking_endpoint_failures_keep_the_python_warning_vocabulary() {
        for detail in ["404", "Not Found", "unavailable", "preview required"] {
            assert_eq!(
                dependency_warning_code("blocking", false, detail),
                "blocking_endpoint_unavailable"
            );
        }
        assert_eq!(
            dependency_warning_code("blocked_by", false, "404"),
            "dependency_read_failed"
        );
        assert_eq!(
            dependency_warning_code("blocking", true, "anything"),
            "dependency_json_invalid"
        );
    }

    #[test]
    fn inherited_classifier_preserves_oos_exception_boundary() {
        let meta = BTreeMap::from([
            (5, json!({"title": "normal", "state": "open"})),
            (100, json!({"title": "[OOS] combined", "state": "open"})),
        ]);
        assert_eq!(
            classify_edge((5, 100), &meta, &BTreeSet::from([100])).0,
            "exception"
        );
        assert_eq!(classify_edge((100, 5), &meta, &BTreeSet::new()).0, "safe");
    }

    #[test]
    #[allow(clippy::cognitive_complexity)] // One compact malformed-input table proves each parser boundary.
    fn compatibility_helpers_refuse_malformed_documents() {
        assert_eq!(dispatch("unknown", &[]), ExitCode::from(2));
        assert!(issue_numbers("", "--issues").is_err());
        assert!(issue_numbers("1,no", "--issues").is_err());
        assert!(read_json("/tmp/larch-combine-missing.json", "fixture").is_err());
        assert!(status_ok(&json!({"status":"failed"}), "fixture").is_err());
        assert!(source_map(&json!({"zero": 1})).is_err());
        assert!(source_map(&json!({"1": "not-a-number"})).is_err());
        assert!(source_map(&json!({"1": []})).is_err());
        assert!(normal_edge(None, "edge").is_err());
        assert!(normal_edge(Some(&json!([1])), "edge").is_err());
        assert!(normal_edge(Some(&json!([1, "no"])), "edge").is_err());
        assert_eq!(state_text(GitHubIssueState::Closed), "closed");
        assert_eq!(state_text(GitHubIssueState::All), "");
        assert_eq!(bool_text(true), "true");
        assert_eq!(bool_text(false), "false");

        let open = open_rows(&json!([{}, {"number": 7}])).expect("tolerant open rows");
        assert_eq!(open.len(), 1);
        assert!(open_rows(&json!(true)).is_err());
        assert!(combined_rows(&json!([1])).is_err());
        assert!(combined_rows(&json!([{"number": 0}])).is_err());
        assert!(combined_rows(&json!([{"number": 1, "source_issues": {}}])).is_err());

        let dependencies = json!({"issues":[{"source_issue":3}, {"number":4}]});
        assert!(dependency_entry(&dependencies, 3).is_some());
        assert!(dependency_entry(&dependencies, 4).is_some());
        assert!(dependency_entry(&json!({"issues": null}), 3).is_none());
        assert!(records_by_edge(&json!({"records":[1]}), "records").is_err());
        assert!(candidate_rows(&json!({"candidates":[1]}), "candidates").is_err());
        assert!(edges_from_file(&json!({}), "edges").is_err());

        let outcomes = vec![
            json!({"phase":"different", "status":"written"}),
            json!({"phase":"selected", "status":"other"}),
        ];
        assert_eq!(write_outcome(Some(&outcomes), &["selected"]), "missing");
    }

    #[test]
    fn typed_fetchers_run_against_the_loopback_service() {
        let before = fetch_snapshots();
        let (github, server) = service([response(
            200,
            json!([issue(2, 20, "Ready", "Issue body", "open")]),
        )]);
        assert_eq!(
            with_test_github_service(github, || fetch(&arguments(&["--repo", "o/r"]))),
            ExitCode::SUCCESS
        );
        let created: Vec<PathBuf> = fetch_snapshots().difference(&before).cloned().collect();
        assert_eq!(created.len(), 1, "fetch should publish one snapshot");
        for path in created {
            fs::remove_file(path).expect("remove fetch snapshot");
        }
        assert_eq!(server.finish().expect("stub finished").len(), 1);

        let before = fetch_snapshots();
        let (github, server) = service([response(
            200,
            json!([issue(4, 40, "[OOS] Ready", "Issue body", "open")]),
        )]);
        assert_eq!(
            with_test_github_service(github, || {
                fetch(&arguments(&["--repo", "o/r", "--oos"]))
            }),
            ExitCode::SUCCESS
        );
        let created: Vec<PathBuf> = fetch_snapshots().difference(&before).cloned().collect();
        assert_eq!(created.len(), 1, "OOS fetch should publish one snapshot");
        for path in created {
            fs::remove_file(path).expect("remove OOS fetch snapshot");
        }
        assert_eq!(server.finish().expect("stub finished").len(), 1);

        let (github, server) = service([response(404, json!({"message": "unavailable"}))]);
        assert_eq!(
            with_test_github_service(github, || fetch(&arguments(&["--repo", "o/r"]))),
            ExitCode::FAILURE
        );
        assert_eq!(server.finish().expect("stub finished").len(), 1);

        let (github, server) = service([response(
            200,
            json!([issue(3, 30, "Ready", "Issue body", "open")]),
        )]);
        assert_eq!(
            with_test_github_service(github, || { list_open(&arguments(&["--repo", "o/r"])) }),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 1);

        let (github, server) = service([response(200, json!({"unexpected": "object"}))]);
        assert_eq!(
            with_test_github_service(github, || { list_open(&arguments(&["--repo", "o/r"])) }),
            ExitCode::FAILURE
        );
        assert_eq!(server.finish().expect("stub finished").len(), 1);

        let (github, server) = service([response(404, json!({"message": "not found"}))]);
        assert_eq!(
            with_test_github_service(github, || { list_open(&arguments(&["--repo", "o/r"])) }),
            ExitCode::FAILURE
        );
        assert_eq!(server.finish().expect("stub finished").len(), 1);

        let (github, server) = service([
            response(
                200,
                json!([{"number": 7, "id": 70}, {"number": 5, "id": 50}]),
            ),
            response(200, json!([{"number": 9, "id": 90}])),
        ]);
        assert_eq!(
            with_test_github_service(github, || {
                fetch_deps(&arguments(&["--repo", "o/r", "--issues", "1"]))
            }),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 2);

        let (github, server) = service([
            response(200, json!({"unexpected": "object"})),
            response(200, json!([])),
        ]);
        assert_eq!(
            with_test_github_service(github, || {
                fetch_deps(&arguments(&["--repo", "o/r", "--issues", "1"]))
            }),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 2);

        let (github, server) = service([
            response(404, json!({"message": "dependency endpoint missing"})),
            response(200, json!([])),
        ]);
        assert_eq!(
            with_test_github_service(github, || {
                fetch_deps(&arguments(&["--repo", "o/r", "--issues", "1"]))
            }),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 2);
    }

    #[test]
    fn inherited_plan_enriches_missing_blocker_metadata_with_the_typed_service() {
        let temp = TempDir::new().expect("tempdir");
        let deps = write_json(
            &temp,
            "deps.json",
            &json!({"status":"ok","issues":{"1":{"blocked_by":[9],"blocking":[],"read_ok":true}}}),
        );
        let mapping = write_json(&temp, "mapping.json", &json!({"1":100}));
        let open = write_json(&temp, "open.json", &json!({"status":"ok","issues":[]}));
        let combined = write_json(
            &temp,
            "combined.json",
            &json!([{"number":100,"title":"Combined","source_issues":[1]}]),
        );
        let (github, server) = service([response(200, issue(9, 90, "blocker", "", "open"))]);
        assert_eq!(
            with_test_github_service(github, || {
                plan_inherited(&arguments(&[
                    "--repo",
                    "o/r",
                    "--deps-file",
                    &deps,
                    "--source-to-combined-file",
                    &mapping,
                    "--open-issues-file",
                    &open,
                    "--combined-issues-file",
                    &combined,
                ]))
            }),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 1);
    }

    #[test]
    fn prose_audit_scans_typed_issue_and_comment_evidence() {
        let temp = TempDir::new().expect("tempdir");
        let open = write_json(
            &temp,
            "open.json",
            &json!({"status":"ok","issues":[
                {"number":1,"title":"one","state":"open"},
                {"number":2,"title":"two","state":"open"},
                {"number":3,"title":"three","state":"open"}
            ]}),
        );
        let existing = write_json(&temp, "existing.json", &json!([]));
        let mapping = write_json(&temp, "mapping.json", &json!({"1":100,"2":200,"3":300}));
        let (github, server) = service([
            response(200, issue(1, 10, "one", "Blocked by #2", "open")),
            response(200, issue(2, 20, "two", "Blocks #1", "open")),
            response(200, issue(3, 30, "three", "Blocks #1", "open")),
            response(200, issue(100, 1000, "combined one", "", "open")),
            response(200, issue(200, 2000, "combined two", "", "open")),
            response(200, issue(300, 3000, "combined three", "", "open")),
            response(200, json!([comment("Blocks #3")])),
            response(200, json!([])),
            response(200, json!([])),
            response(200, json!([])),
            response(200, json!([])),
            response(200, json!([])),
        ]);
        assert_eq!(
            with_test_github_service(github, || {
                prose_audit(&arguments(&[
                    "--repo",
                    "o/r",
                    "--combined-issues",
                    "100,200,300",
                    "--open-issues-file",
                    &open,
                    "--existing-edges-file",
                    &existing,
                    "--source-to-combined-file",
                    &mapping,
                ]))
            }),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 12);

        let empty_open = write_json(
            &temp,
            "empty-open.json",
            &json!({"status":"ok","issues":[]}),
        );
        let empty_mapping = write_json(&temp, "empty-mapping.json", &json!({}));
        let (github, server) = service([response(404, json!({"message": "not found"}))]);
        assert_eq!(
            with_test_github_service(github, || {
                prose_audit(&arguments(&[
                    "--repo",
                    "o/r",
                    "--combined-issues",
                    "100",
                    "--open-issues-file",
                    &empty_open,
                    "--existing-edges-file",
                    &existing,
                    "--source-to-combined-file",
                    &empty_mapping,
                ]))
            }),
            ExitCode::FAILURE
        );
        assert_eq!(server.finish().expect("stub finished").len(), 1);

        let (github, server) = service([
            response(200, issue(100, 1000, "combined", "", "open")),
            response(404, json!({"message": "comments unavailable"})),
        ]);
        assert_eq!(
            with_test_github_service(github, || {
                prose_audit(&arguments(&[
                    "--repo",
                    "o/r",
                    "--combined-issues",
                    "100",
                    "--open-issues-file",
                    &empty_open,
                    "--existing-edges-file",
                    &existing,
                    "--source-to-combined-file",
                    &empty_mapping,
                ]))
            }),
            ExitCode::FAILURE
        );
        assert_eq!(server.finish().expect("stub finished").len(), 2);
    }

    #[test]
    #[allow(clippy::too_many_lines)] // One ordered exchange sequence proves the apply checkpoints.
    fn apply_transfers_edges_before_closing_sources_and_reports_partial_transfers() {
        let temp = TempDir::new().expect("tempdir");
        let body = temp.path().join("body.md");
        fs::write(&body, "Combined body\n").expect("write body");
        let body = body.to_string_lossy().into_owned();
        let combined = created_issue(100, 1000, "Combined", "Combined body\n");
        let source = issue(1, 10, "source", "Source body", "open");
        let closed = issue(1, 10, "source", "Source body", "closed");
        let note = combined_comment(1, 100);
        let (github, server) = service([
            response(200, json!([{"number": 3, "id": 30}])),
            response(201, combined.clone()),
            response(200, combined.clone()),
            response(200, json!([])),
            response(201, json!({})),
            response(200, json!([{"number": 3, "id": 30}])),
            response(200, json!([{"number": 3, "id": 30}])),
            response(200, json!([{"number": 3, "id": 30}])),
            response(200, source),
            response(201, comment(&note)),
            response(200, closed),
        ]);
        assert_eq!(
            with_test_github_service(github, || {
                apply(&arguments(&[
                    "--repo",
                    "o/r",
                    "--title",
                    "Combined",
                    "--body-file",
                    &body,
                    "--source-issues",
                    "1",
                    "--operator-invoked",
                ]))
            }),
            ExitCode::SUCCESS
        );
        let requests = server.finish().expect("stub finished");
        assert_eq!(requests.len(), 11);
        assert_eq!(
            requests[1].method, "POST",
            "create follows dependency reads"
        );
        assert_eq!(requests[4].method, "POST", "edge transfer is a mutation");
        assert_eq!(requests[9].method, "POST", "source close records a comment");
        assert_eq!(
            requests[10].method, "PATCH",
            "source closes after edge read-back"
        );

        let (github, server) = service([
            response(201, combined.clone()),
            response(200, combined.clone()),
        ]);
        assert_eq!(
            with_test_github_service(github, || {
                apply(&arguments(&[
                    "--repo",
                    "o/r",
                    "--title",
                    "Combined",
                    "--body-file",
                    &body,
                    "--source-issues",
                    "1",
                    "--defer-close",
                    "--operator-invoked",
                ]))
            }),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 2);

        let (github, server) = service([
            response(200, json!([{"number": 3, "id": 30}])),
            response(201, combined.clone()),
            response(200, combined),
            response(200, json!([])),
            response(404, json!({"message": "dependency endpoint unavailable"})),
        ]);
        assert_eq!(
            with_test_github_service(github, || {
                apply(&arguments(&[
                    "--repo",
                    "o/r",
                    "--title",
                    "Combined",
                    "--body-file",
                    &body,
                    "--source-issues",
                    "1",
                    "--operator-invoked",
                ]))
            }),
            ExitCode::SUCCESS
        );
        let requests = server.finish().expect("stub finished");
        assert_eq!(
            requests.len(),
            5,
            "partial transfer must not close its source"
        );
        assert!(requests.iter().all(|request| request.method != "PATCH"));

        let combined = created_issue(101, 1010, "Combined", "Combined body\n");
        let (github, server) = service([
            response(200, json!([])),
            response(201, combined.clone()),
            response(200, combined),
            response(200, json!([])),
            response(200, json!([{"number": 9, "id": 90, "state": "open"}])),
        ]);
        assert_eq!(
            with_test_github_service(github, || {
                apply(&arguments(&[
                    "--repo",
                    "o/r",
                    "--title",
                    "Combined",
                    "--body-file",
                    &body,
                    "--source-issues",
                    "1",
                    "--operator-invoked",
                ]))
            }),
            ExitCode::SUCCESS
        );
        let requests = server.finish().expect("stub finished");
        assert_eq!(requests.len(), 5);
        assert!(requests.iter().all(|request| request.method != "PATCH"));
    }

    #[test]
    #[allow(clippy::too_many_lines)] // Each failed checkpoint must prove that no source was closed.
    fn apply_fails_closed_across_each_live_checkpoint() {
        let temp = TempDir::new().expect("tempdir");
        let body = temp.path().join("body.md");
        fs::write(&body, "Combined body\n").expect("write body");
        let body = body.to_string_lossy().into_owned();
        let apply_args = [
            "--repo",
            "o/r",
            "--title",
            "Combined",
            "--body-file",
            body.as_str(),
            "--source-issues",
            "1",
            "--operator-invoked",
        ];

        assert_eq!(
            apply(&arguments(&[
                "--repo",
                "o/r",
                "--title",
                "Combined",
                "--body-file",
                &body,
                "--source-issues",
                "1",
            ])),
            ExitCode::FAILURE
        );

        let (github, server) = service([response(500, json!({"message": "unavailable"}))]);
        assert_eq!(
            with_test_github_service(github, || apply(&arguments(&apply_args))),
            ExitCode::FAILURE
        );
        assert_eq!(server.finish().expect("stub finished").len(), 1);

        let (github, server) = service([
            response(200, json!([])),
            response(500, json!({"message": "create unavailable"})),
        ]);
        assert_eq!(
            with_test_github_service(github, || apply(&arguments(&apply_args))),
            ExitCode::FAILURE
        );
        assert_eq!(server.finish().expect("stub finished").len(), 2);

        let combined = created_issue(102, 1020, "Combined", "Combined body\n");
        let (github, server) = service([
            response(200, json!([{"number": 3, "id": 30}])),
            response(201, combined.clone()),
            response(200, combined),
            response(200, json!([])),
            response(201, json!({})),
            response(200, json!([{"number": 3, "id": 30}])),
            response(200, json!([])),
        ]);
        assert_eq!(
            with_test_github_service(github, || apply(&arguments(&apply_args))),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 7);

        let combined = created_issue(103, 1030, "Combined", "Combined body\n");
        let (github, server) = service([
            response(200, json!([{"number": 3, "id": 30}])),
            response(201, combined.clone()),
            response(200, combined),
            response(200, json!([])),
            response(201, json!({})),
            response(200, json!([{"number": 3, "id": 30}])),
            response(500, json!({"message": "read-back unavailable"})),
        ]);
        assert_eq!(
            with_test_github_service(github, || apply(&arguments(&apply_args))),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 7);

        let combined = created_issue(104, 1040, "Combined", "Combined body\n");
        let (github, server) = service([
            response(200, json!([{"number": 3, "id": 30}])),
            response(201, combined.clone()),
            response(200, combined),
            response(200, json!([])),
            response(201, json!({})),
            response(200, json!([{"number": 3, "id": 30}])),
            response(200, json!([{"number": 3, "id": 30}])),
            response(500, json!({"message": "source dependencies unavailable"})),
        ]);
        assert_eq!(
            with_test_github_service(github, || apply(&arguments(&apply_args))),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 8);

        let note = combined_comment(1, 105);
        let combined = created_issue(105, 1050, "Combined", "Combined body\n");
        let (github, server) = service([
            response(200, json!([{"number": 3, "id": 30}])),
            response(201, combined.clone()),
            response(200, combined),
            response(200, json!([])),
            response(201, json!({})),
            response(200, json!([{"number": 3, "id": 30}])),
            response(200, json!([{"number": 3, "id": 30}])),
            response(200, json!([{"number": 3, "id": 30}])),
            response(200, issue(1, 10, "source", "", "open")),
            response(201, comment(&note)),
            response(500, json!({"message": "close unavailable"})),
            response(200, issue(1, 10, "source", "", "open")),
        ]);
        assert_eq!(
            with_test_github_service(github, || apply(&arguments(&apply_args))),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 12);
    }

    #[test]
    #[allow(clippy::cognitive_complexity, clippy::too_many_lines)] // Closure cases share the typed loopback sequence.
    fn close_commands_verify_sources_with_the_loopback_service() {
        let source = issue(1, 10, "source", "Source body", "open");
        let closed = issue(1, 10, "source", "Source body", "closed");
        let note = combined_comment(1, 100);
        let (github, server) = service([
            response(200, issue(100, 1000, "combined", "", "open")),
            response(200, json!([{"number": 3, "id": 30}])),
            response(200, source.clone()),
            response(200, json!([{"number": 3, "id": 30}])),
            response(200, source.clone()),
            response(201, comment(&note)),
            response(200, closed.clone()),
        ]);
        assert_eq!(
            with_test_github_service(github, || {
                close_sources(&arguments(&[
                    "--repo",
                    "o/r",
                    "--combined-issue",
                    "100",
                    "--source-issues",
                    "1",
                    "--operator-invoked",
                ]))
            }),
            ExitCode::SUCCESS
        );
        let requests = server.finish().expect("stub finished");
        assert_eq!(requests.len(), 7);
        assert_eq!(requests[5].method, "POST");
        assert_eq!(requests[6].method, "PATCH");

        let (github, server) = service([
            response(200, source.clone()),
            response(200, source),
            response(200, closed),
        ]);
        assert_eq!(
            with_test_github_service(github, || {
                super::close_stale(&arguments(&[
                    "--repo",
                    "o/r",
                    "--issues",
                    "1",
                    "--reason",
                    "completed",
                    "--operator-invoked",
                ]))
            }),
            ExitCode::SUCCESS
        );
        let requests = server.finish().expect("stub finished");
        assert_eq!(requests.len(), 3);
        assert_eq!(requests[2].method, "PATCH");

        let (github, server) = service([response(200, issue(100, 1000, "combined", "", "closed"))]);
        assert_eq!(
            with_test_github_service(github, || {
                close_sources(&arguments(&[
                    "--repo",
                    "o/r",
                    "--combined-issue",
                    "100",
                    "--source-issues",
                    "1",
                    "--operator-invoked",
                ]))
            }),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 1);

        let (github, server) = service([
            response(200, issue(100, 1000, "combined", "", "open")),
            response(200, json!([])),
            response(200, issue(1, 10, "[IN PROGRESS] source", "", "open")),
        ]);
        assert_eq!(
            with_test_github_service(github, || {
                close_sources(&arguments(&[
                    "--repo",
                    "o/r",
                    "--combined-issue",
                    "100",
                    "--source-issues",
                    "1",
                    "--operator-invoked",
                ]))
            }),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 3);

        let (github, server) = service([
            response(200, issue(100, 1000, "combined", "", "open")),
            response(200, json!([])),
            response(200, issue(1, 10, "source", "", "open")),
            response(200, json!([{"number": 9, "id": 90, "state": "open"}])),
        ]);
        assert_eq!(
            with_test_github_service(github, || {
                close_sources(&arguments(&[
                    "--repo",
                    "o/r",
                    "--combined-issue",
                    "100",
                    "--source-issues",
                    "1",
                    "--operator-invoked",
                ]))
            }),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 4);

        let (github, server) = service([
            response(200, issue(100, 1000, "combined", "", "open")),
            response(200, json!([])),
            response(200, issue(1, 10, "source", "", "open")),
            response(404, json!({"message": "dependency endpoint unavailable"})),
        ]);
        assert_eq!(
            with_test_github_service(github, || {
                close_sources(&arguments(&[
                    "--repo",
                    "o/r",
                    "--combined-issue",
                    "100",
                    "--source-issues",
                    "1",
                    "--operator-invoked",
                ]))
            }),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 4);

        assert_eq!(
            close_sources(&arguments(&[
                "--repo",
                "o/r",
                "--combined-issue",
                "100",
                "--source-issues",
                "1",
            ])),
            ExitCode::FAILURE
        );

        let close_args = [
            "--repo",
            "o/r",
            "--combined-issue",
            "100",
            "--source-issues",
            "1",
            "--operator-invoked",
        ];
        let (github, server) = service([response(404, json!({"message": "not found"}))]);
        assert_eq!(
            with_test_github_service(github, || close_sources(&arguments(&close_args))),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 1);

        let (github, server) = service([
            response(200, issue(100, 1000, "combined", "", "open")),
            response(404, json!({"message": "dependency endpoint unavailable"})),
        ]);
        assert_eq!(
            with_test_github_service(github, || close_sources(&arguments(&close_args))),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 2);

        let (github, server) = service([
            response(200, issue(100, 1000, "combined", "", "open")),
            response(200, json!([])),
            response(404, json!({"message": "source unavailable"})),
        ]);
        assert_eq!(
            with_test_github_service(github, || close_sources(&arguments(&close_args))),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 3);

        let (github, server) = service([
            response(200, issue(100, 1000, "combined", "", "open")),
            response(200, json!([])),
            response(200, issue(1, 10, "source", "", "closed")),
        ]);
        assert_eq!(
            with_test_github_service(github, || close_sources(&arguments(&close_args))),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 3);

        let stale_args = [
            "--repo",
            "o/r",
            "--issues",
            "1",
            "--reason",
            "not planned",
            "--operator-invoked",
        ];
        let (github, server) = service([
            response(200, issue(1, 10, "source", "", "open")),
            response(200, issue(1, 10, "source", "", "closed")),
        ]);
        assert_eq!(
            with_test_github_service(github, || { super::close_stale(&arguments(&stale_args)) }),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 2);

        let (github, server) = service([
            response(200, issue(1, 10, "source", "", "open")),
            response(200, issue(1, 10, "source", "", "open")),
            response(500, json!({"message": "close unavailable"})),
            response(200, issue(1, 10, "source", "", "open")),
        ]);
        assert_eq!(
            with_test_github_service(github, || { super::close_stale(&arguments(&stale_args)) }),
            ExitCode::SUCCESS
        );
        assert_eq!(server.finish().expect("stub finished").len(), 4);
    }
}
