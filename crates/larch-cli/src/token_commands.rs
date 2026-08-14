//! `token` recording and staging verbs.
//!
//! Owns ledger mutation, sidecar staging, and research-lane telemetry for the
//! commands migrated by #8506. Remaining analytical `token` verbs stay Python
//! until their own leaves cut over.

use std::{
    collections::BTreeMap,
    env, fs,
    io::Write as _,
    path::{Path, PathBuf},
    process::ExitCode,
    time::SystemTime,
};

use chrono::{DateTime, Utc};
use larch_adapters::read_kv_raw;
use larch_core::report::{
    active_ledger_vendor, contains_dotdot, default_ledger_basename, lane_sidecar_body,
    lane_sidecar_name, mark_line, parse_token_record_sidecar, render_lane_report,
    resolve_under_roots, sha256_hex, sidecar_ndjson_line, validate_lane_phase,
    validate_total_tokens, vendor_line,
};
use std::ffi::OsString;

#[cfg(unix)]
use std::os::unix::fs::OpenOptionsExt as _;

use crate::ledger_append::{append_locked_line, restore_owner_only_permissions};

/// Record one step mark in the resolved token ledger.
pub fn mark(arguments: &[OsString]) -> ExitCode {
    mark_with_env(arguments, &[])
}

/// Record one step mark, resolving the ledger with caller-supplied env overrides.
///
/// Launchers learn session identity from files rather than from their own
/// environment. Passing those rows here reaches the resolver the same way the
/// retired Python child process did.
pub fn mark_with_env(arguments: &[OsString], overrides: &[(&str, String)]) -> ExitCode {
    let (rest, ledger) = match split_ledger(arguments) {
        Ok(value) => value,
        Err(message) => {
            eprintln!("token mark: {message}");
            return ExitCode::from(1);
        }
    };
    let Some(step) = rest.first().filter(|value| !value.is_empty()) else {
        eprintln!("token mark requires <step>");
        return ExitCode::from(1);
    };
    if mark_step(step, ledger.as_deref(), overrides) {
        ExitCode::SUCCESS
    } else {
        ExitCode::from(1)
    }
}

/// Record one vendor usage row in the resolved token ledger.
pub fn record_vendor(arguments: &[OsString]) -> ExitCode {
    let (rest, ledger) = match split_ledger(arguments) {
        Ok(value) => value,
        Err(message) => {
            eprintln!("token record-vendor: {message}");
            return ExitCode::from(1);
        }
    };
    let Some(vendor) = rest.first().filter(|value| !value.is_empty()) else {
        eprintln!("token record-vendor requires <vendor>");
        return ExitCode::from(1);
    };
    let mut vals = VendorValues::default();
    for option in rest.iter().skip(1) {
        let Some((key, value)) = option.split_once('=') else {
            eprintln!("token record-vendor: unknown argument: {option}");
            return ExitCode::from(1);
        };
        match key {
            "raw" => value.clone_into(&mut vals.raw),
            "model" => value.clone_into(&mut vals.model),
            "input" | "output" | "cache_read" | "cache_create" | "total" => {
                if !value.bytes().all(|byte| byte.is_ascii_digit()) {
                    eprintln!("token record-vendor: {key} must be a non-negative integer");
                    return ExitCode::from(1);
                }
                let parsed = value.parse::<u64>().unwrap_or(0);
                match key {
                    "input" => vals.input = parsed,
                    "output" => vals.output = parsed,
                    "cache_read" => vals.cache_read = parsed,
                    "cache_create" => vals.cache_create = parsed,
                    "total" => vals.total = parsed,
                    _ => {}
                }
            }
            _ => {
                eprintln!("token record-vendor: unknown argument: {option}");
                return ExitCode::from(1);
            }
        }
    }
    match record_vendor_values(vendor, &vals, ledger.as_deref()) {
        RecordOutcome::Ok => ExitCode::SUCCESS,
        RecordOutcome::Usage(message) => {
            eprintln!("token record-vendor: {message}");
            ExitCode::from(1)
        }
    }
}

/// Best-effort vendor append used by launchers that must not fail the vendor run.
pub fn record_vendor_best_effort(arguments: impl IntoIterator<Item = OsString>) {
    let values: Vec<OsString> = arguments.into_iter().collect();
    let _ignored = record_vendor(&values);
}

/// Append one active-ledger vendor row from a KEY=value sidecar.
pub fn record_vendor_sidecar(arguments: &[OsString]) -> ExitCode {
    let (rest, ledger) = match split_ledger(arguments) {
        Ok(value) => value,
        Err(message) => {
            eprintln!("token record-vendor-sidecar: {message}");
            return ExitCode::from(2);
        }
    };
    let options = flag_map(&rest);
    let input_path = options.get("--input").map(PathBuf::from);
    match record_vendor_from_sidecar(input_path.as_deref(), ledger.as_deref()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("token record-vendor-sidecar: {message}");
            ExitCode::from(2)
        }
    }
}

/// Best-effort sidecar→ledger append for launchers.
pub fn record_vendor_sidecar_best_effort(arguments: impl IntoIterator<Item = OsString>) {
    let values: Vec<OsString> = arguments.into_iter().collect();
    let _ignored = record_vendor_sidecar(&values);
}

/// Append one staging NDJSON row from a KEY=value sidecar.
pub fn append_record(arguments: &[OsString]) -> ExitCode {
    let options = flag_map(
        &arguments
            .iter()
            .map(|value| value.to_string_lossy().into_owned())
            .collect::<Vec<_>>(),
    );
    let Some(tmpdir) = options.get("--tmpdir").map(PathBuf::from) else {
        eprintln!("token append-record: '--tmpdir'");
        return ExitCode::from(2);
    };
    let input_path = options.get("--input").map(PathBuf::from);
    match append_token_record_from_sidecar(input_path.as_deref(), &tmpdir) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("token append-record: {message}");
            ExitCode::from(2)
        }
    }
}

/// Print the resolved ledger path and its raw contents.
pub fn dump(arguments: &[OsString]) -> ExitCode {
    let (_rest, ledger) = match split_ledger(arguments) {
        Ok(value) => value,
        Err(message) => {
            eprintln!("token dump: {message}");
            return ExitCode::from(1);
        }
    };
    let path = match resolve_token_ledger_path(ledger.as_deref(), &[]) {
        Ok(path) => path,
        Err(message) => {
            eprintln!("token dump: {message}");
            return ExitCode::from(1);
        }
    };
    let Some(path) = path else {
        return ExitCode::SUCCESS;
    };
    println!("{}", path.display());
    if path.is_file()
        && fs::metadata(&path)
            .map(|metadata| metadata.len() > 0)
            .unwrap_or(false)
    {
        match fs::read_to_string(&path) {
            Ok(text) => print!("{text}"),
            Err(error) => eprintln!("token dump: {error}"),
        }
    }
    ExitCode::SUCCESS
}

/// Write one research/validation lane token sidecar.
pub fn lane_write(arguments: &[OsString]) -> ExitCode {
    let options = flag_map(
        &arguments
            .iter()
            .map(|value| value.to_string_lossy().into_owned())
            .collect::<Vec<_>>(),
    );
    for required in ["--dir", "--phase", "--lane", "--tool", "--total-tokens"] {
        if !options.contains_key(required) {
            eprintln!("token lane-write: '{required}'");
            return ExitCode::from(1);
        }
    }
    let dir = options["--dir"].as_str();
    let phase = options["--phase"].as_str();
    let lane = options["--lane"].as_str();
    let tool = options["--tool"].as_str();
    let total_tokens = options["--total-tokens"].as_str();
    match write_lane(Path::new(dir), phase, lane, tool, total_tokens) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("token lane-write: {message}");
            ExitCode::from(1)
        }
    }
}

/// Render the research lane token-spend summary.
pub fn lane_report(arguments: &[OsString]) -> ExitCode {
    let options = flag_map(
        &arguments
            .iter()
            .map(|value| value.to_string_lossy().into_owned())
            .collect::<Vec<_>>(),
    );
    let Some(dir) = options.get("--dir") else {
        eprintln!("token lane-report: '--dir'");
        return ExitCode::from(1);
    };
    match report_lane(Path::new(dir)) {
        Ok(text) => {
            println!("{text}");
            ExitCode::SUCCESS
        }
        Err(message) => {
            eprintln!("token lane-report: {message}");
            ExitCode::from(1)
        }
    }
}

#[derive(Clone, Debug)]
enum RecordOutcome {
    Ok,
    Usage(String),
}

#[derive(Clone, Debug, Default)]
struct VendorValues {
    input: u64,
    output: u64,
    cache_read: u64,
    cache_create: u64,
    total: u64,
    raw: String,
    model: String,
}

fn mark_step(step: &str, ledger: Option<&str>, overrides: &[(&str, String)]) -> bool {
    let path = match resolve_token_ledger_path(ledger, overrides) {
        Ok(Some(path)) => path,
        Ok(None) => return true,
        Err(message) => {
            eprintln!("token mark: {message}");
            return false;
        }
    };
    let line = mark_line(step, &timestamp_utc());
    match append_jsonl(&path, &line) {
        Ok(()) => true,
        Err(AppendError::Invalid(message)) => {
            eprintln!("token mark: {message}");
            false
        }
        Err(AppendError::Io(error)) => {
            eprintln!("token mark: write skipped: {error}");
            true
        }
    }
}

fn record_vendor_values(vendor: &str, vals: &VendorValues, ledger: Option<&str>) -> RecordOutcome {
    let path = match resolve_token_ledger_path(ledger, &[]) {
        Ok(Some(path)) => path,
        Ok(None) => return RecordOutcome::Ok,
        Err(message) => return RecordOutcome::Usage(message),
    };
    let line = match vendor_line(
        vendor,
        vals.input,
        vals.output,
        vals.cache_read,
        vals.cache_create,
        vals.total,
        &vals.raw,
        &vals.model,
        &timestamp_utc(),
    ) {
        Ok(line) => line,
        Err(message) => return RecordOutcome::Usage(message),
    };
    match append_jsonl(&path, &line) {
        Ok(()) => RecordOutcome::Ok,
        Err(AppendError::Invalid(message)) => RecordOutcome::Usage(message),
        Err(AppendError::Io(error)) => {
            eprintln!("token record-vendor: write skipped: {error}");
            RecordOutcome::Ok
        }
    }
}

fn record_vendor_from_sidecar(
    input_path: Option<&Path>,
    ledger: Option<&str>,
) -> Result<(), String> {
    let Some(input_path) = input_path else {
        return Ok(());
    };
    let Some(payload) = read_sidecar_payload(input_path) else {
        return Ok(());
    };
    let mut vendor = payload.tool.clone();
    if vendor == "claude" {
        "claude_sub".clone_into(&mut vendor);
    }
    let Some(active) = active_ledger_vendor(&vendor) else {
        let raw_tool = raw_tool_from_sidecar(input_path);
        let raw_note = if !raw_tool.is_empty() && raw_tool != vendor {
            format!(" (raw TOOL={raw_tool})")
        } else {
            String::new()
        };
        eprintln!(
            "token record-vendor-sidecar: unsupported TOOL={vendor}{raw_note}; active-ledger append skipped for {}",
            input_path.display()
        );
        return Ok(());
    };
    let Some(path) = resolve_token_ledger_path(ledger, &[])? else {
        return Ok(());
    };
    let line = vendor_line(
        active,
        payload.input,
        payload.output,
        payload.cache_read,
        payload.cache_create,
        payload.total,
        &payload.raw,
        &payload.model,
        &timestamp_utc(),
    )?;
    if let Err(error) = append_jsonl(&path, &line) {
        match error {
            AppendError::Invalid(message) => return Err(message),
            AppendError::Io(error) => {
                eprintln!("token record-vendor: write skipped: {error}");
            }
        }
    }
    Ok(())
}

fn append_token_record_from_sidecar(
    input_path: Option<&Path>,
    tmpdir: &Path,
) -> Result<(), String> {
    if !tmpdir.is_dir() {
        return Err("--tmpdir must exist".to_owned());
    }
    let Some(input_path) = input_path else {
        return Ok(());
    };
    let Some(payload) = read_sidecar_payload(input_path) else {
        let absent_or_empty = !input_path.is_file()
            || fs::metadata(input_path)
                .map(|metadata| metadata.len() == 0)
                .unwrap_or(true);
        if absent_or_empty && !tmpdir.join("execution-issues.md").exists() {
            eprintln!(
                "append token record: token sidecar absent: {}",
                input_path.display()
            );
        }
        return Ok(());
    };
    let target = tmpdir.join("token-report.ndjson");
    append_plain(&target, &sidecar_ndjson_line(&payload)).map_err(|error| error.to_string())?;
    Ok(())
}

fn write_lane(
    root: &Path,
    phase: &str,
    lane: &str,
    tool: &str,
    total_tokens: &str,
) -> Result<(), String> {
    validate_research_dir(root)?;
    validate_lane_phase(phase)?;
    validate_total_tokens(total_tokens)?;
    fs::create_dir_all(root).map_err(|error| error.to_string())?;
    let path = root.join(lane_sidecar_name(phase, lane));
    fs::write(&path, lane_sidecar_body(phase, lane, tool, total_tokens))
        .map_err(|error| error.to_string())
}

fn report_lane(root: &Path) -> Result<String, String> {
    validate_research_dir(root)?;
    if !root.is_dir() {
        return Ok(render_lane_report(
            &BTreeMap::new(),
            &BTreeMap::new(),
            &BTreeMap::new(),
            &BTreeMap::new(),
            0.0,
            true,
        ));
    }
    let mut lanes: BTreeMap<&'static str, Vec<String>> =
        BTreeMap::from([("research", Vec::new()), ("validation", Vec::new())]);
    let mut totals: BTreeMap<&'static str, u64> =
        BTreeMap::from([("research", 0), ("validation", 0)]);
    let mut measured: BTreeMap<&'static str, u64> =
        BTreeMap::from([("research", 0), ("validation", 0)]);
    let mut unknown: BTreeMap<&'static str, u64> =
        BTreeMap::from([("research", 0), ("validation", 0)]);
    let mut entries = fs::read_dir(root)
        .map_err(|error| error.to_string())?
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| {
            path.file_name()
                .and_then(|name| name.to_str())
                .is_some_and(|name| name.starts_with("lane-tokens-"))
                && path.extension().is_some_and(|ext| ext == "txt")
        })
        .collect::<Vec<_>>();
    entries.sort();
    for sidecar in entries {
        let Ok(rows) = read_kv_raw(&sidecar) else {
            continue;
        };
        let kv: BTreeMap<String, String> = rows.into_iter().collect::<BTreeMap<_, _>>();
        let phase = kv.get("PHASE").map_or("", String::as_str);
        let phase_key = match phase {
            "research" => "research",
            "validation" => "validation",
            _ => continue,
        };
        lanes
            .entry(phase_key)
            .or_default()
            .push(kv.get("LANE").cloned().unwrap_or_default());
        let total = kv.get("TOTAL_TOKENS").map_or("", String::as_str);
        if !total.is_empty() && total.bytes().all(|byte: u8| byte.is_ascii_digit()) {
            *totals.entry(phase_key).or_default() += total.parse::<u64>().unwrap_or(0);
            *measured.entry(phase_key).or_default() += 1;
        } else {
            *unknown.entry(phase_key).or_default() += 1;
        }
    }
    let rate = env::var("LARCH_TOKEN_RATE_PER_M")
        .ok()
        .and_then(|raw| raw.parse::<f64>().ok())
        .unwrap_or(0.0);
    Ok(render_lane_report(
        &lanes, &totals, &measured, &unknown, rate, false,
    ))
}

fn read_sidecar_payload(path: &Path) -> Option<larch_core::report::TokenSidecarPayload> {
    if !path.is_file()
        || fs::metadata(path)
            .map(|metadata| metadata.len() == 0)
            .unwrap_or(true)
    {
        return None;
    }
    let rows = read_kv_raw(path).ok()?;
    let kv: BTreeMap<String, String> = rows.into_iter().collect();
    parse_token_record_sidecar(&kv)
}

fn raw_tool_from_sidecar(path: &Path) -> String {
    read_kv_raw(path)
        .ok()
        .into_iter()
        .flatten()
        .find_map(|(key, value)| (key == "TOOL").then_some(value))
        .unwrap_or_default()
}

fn resolve_token_ledger_path(
    ledger: Option<&str>,
    overrides: &[(&str, String)],
) -> Result<Option<PathBuf>, String> {
    let mut env_map: BTreeMap<String, String> = env::vars().collect();
    for (key, value) in overrides {
        let _replaced = env_map.insert((*key).to_owned(), value.clone());
    }
    if let Some(raw) = ledger.filter(|value| !value.is_empty()) {
        return Ok(Some(validate_under_tmp(raw, &env_map)?));
    }
    if let Some(raw) = env_map
        .get("LARCH_TOKEN_LEDGER")
        .filter(|value| !value.is_empty())
        .cloned()
        && let Ok(path) = validate_under_tmp(&raw, &env_map)
    {
        return Ok(Some(path));
    }
    let slug = sha256_hex(&resolve_session_id(&env_map));
    for key in ["IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "RESEARCH_TMPDIR"] {
        if let Some(root) = canonical_dir(env_map.get(key).map_or("", String::as_str)) {
            return Ok(Some(root.join(default_ledger_basename(&slug))));
        }
    }
    if let Some(session_env) = env_map
        .get("SESSION_ENV_PATH")
        .filter(|value| !value.is_empty())
        .cloned()
        && let Some(root) = Path::new(&session_env)
            .parent()
            .and_then(|parent| canonical_dir(parent.to_str().unwrap_or("")))
    {
        return Ok(Some(root.join(default_ledger_basename(&slug))));
    }
    Ok(None)
}

fn validate_under_tmp(raw: &str, env_map: &BTreeMap<String, String>) -> Result<PathBuf, String> {
    let root = tmp_root(env_map).ok_or_else(|| "cannot canonicalize TMPDIR".to_owned())?;
    let mut allowed = vec![root.clone()];
    if let Some(private) = canonical_dir("/private/tmp") {
        allowed.push(private);
    }
    for key in ["IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "RESEARCH_TMPDIR"] {
        if let Some(workflow_root) = canonical_dir(env_map.get(key).map_or("", String::as_str)) {
            allowed.push(workflow_root);
        }
    }
    let candidate = {
        let path = PathBuf::from(raw);
        if path.is_absolute() {
            path
        } else {
            root.join(path)
        }
    };
    if let Some(parent) = candidate
        .parent()
        .filter(|value| !value.as_os_str().is_empty())
    {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    resolve_under_roots(raw, &root, &allowed)
}

fn resolve_session_id(env_map: &BTreeMap<String, String>) -> String {
    if let Some(value) = env_map
        .get("LARCH_TOKEN_SESSION_ID")
        .filter(|value| !value.is_empty())
    {
        return value.clone();
    }
    for key in ["IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "RESEARCH_TMPDIR"] {
        let root = env_map.get(key).map_or("", String::as_str);
        if root.is_empty() {
            continue;
        }
        let candidate = Path::new(root).join("session-id");
        if candidate.is_file() {
            return fs::read_to_string(candidate)
                .unwrap_or_default()
                .trim()
                .to_owned();
        }
    }
    let cwd = env::current_dir()
        .ok()
        .and_then(|path| path.canonicalize().ok())
        .unwrap_or_else(|| PathBuf::from("."));
    sha256_hex(&cwd.to_string_lossy())
}

fn tmp_root(env_map: &BTreeMap<String, String>) -> Option<PathBuf> {
    let raw = env_map
        .get("TMPDIR")
        .filter(|value| !value.is_empty())
        .map_or("/tmp", String::as_str);
    Path::new(raw).canonicalize().ok()
}

fn canonical_dir(path: &str) -> Option<PathBuf> {
    if path.is_empty() {
        return None;
    }
    let candidate = Path::new(path);
    if !candidate.is_dir() {
        return None;
    }
    candidate.canonicalize().ok()
}

fn validate_research_dir(path: &Path) -> Result<(), String> {
    let raw = path.to_string_lossy();
    if raw.is_empty() || contains_dotdot(&raw) {
        return Err(format!(
            "--dir must not contain '..' segments (got: {})",
            path.display()
        ));
    }
    let cache_root = env::var_os("XDG_CACHE_HOME")
        .map_or_else(
            || {
                env::var_os("HOME")
                    .map_or_else(|| PathBuf::from("/"), PathBuf::from)
                    .join(".cache")
            },
            PathBuf::from,
        )
        .join("larch")
        .join("sessions");
    let prefixes = [
        PathBuf::from("/tmp"),
        PathBuf::from("/private/tmp"),
        cache_root.clone(),
    ];
    if !prefixes.iter().any(|prefix| {
        let prefix = prefix.to_string_lossy();
        raw == prefix || raw.starts_with(&format!("{prefix}/"))
    }) {
        return Err(format!(
            "--dir must be under /tmp/, /private/tmp/, or {}/ (got: {})",
            cache_root.display(),
            path.display()
        ));
    }
    let mut probe = path.to_path_buf();
    while !probe.exists() {
        let Some(parent) = probe.parent().map(Path::to_path_buf) else {
            break;
        };
        if parent == probe {
            break;
        }
        probe = parent;
    }
    if !probe.exists() || probe.is_file() {
        return Err(format!(
            "--dir nearest existing ancestor is not a directory: {}",
            probe.display()
        ));
    }
    let resolved = probe
        .canonicalize()
        .map_err(|_error| format!("--dir resolves outside allowed roots: {}", path.display()))?;
    let allowed = prefixes
        .into_iter()
        .filter_map(|prefix| {
            prefix
                .exists()
                .then(|| prefix.canonicalize().ok())
                .flatten()
        })
        .collect::<Vec<_>>();
    if !allowed
        .iter()
        .any(|root| &resolved == root || resolved.starts_with(root))
    {
        return Err(format!(
            "--dir resolves outside allowed roots: {}",
            resolved.display()
        ));
    }
    Ok(())
}

#[derive(Debug)]
enum AppendError {
    Invalid(String),
    Io(String),
}

fn append_jsonl(path: &Path, line: &str) -> Result<(), AppendError> {
    ensure_regular_file(path)?;
    append_locked_line(path, line, "token").map_err(AppendError::Io)?;
    restore_owner_only_permissions(path);
    Ok(())
}

fn append_plain(path: &Path, line: &str) -> Result<(), std::io::Error> {
    fs::OpenOptions::new()
        .append(true)
        .create(true)
        .open(path)
        .and_then(|mut handle| handle.write_all(line.as_bytes()))
}

fn ensure_regular_file(path: &Path) -> Result<(), AppendError> {
    if let Some(parent) = path.parent().filter(|value| !value.as_os_str().is_empty()) {
        fs::create_dir_all(parent).map_err(|error| AppendError::Io(error.to_string()))?;
    }
    if fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_symlink()) {
        return Err(AppendError::Invalid(format!(
            "ledger is a symlink: {}",
            path.display()
        )));
    }
    if path.exists() && !path.is_file() {
        return Err(AppendError::Invalid(format!(
            "ledger exists but is not a regular file: {}",
            path.display()
        )));
    }
    if !path.exists() {
        #[cfg(unix)]
        {
            fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .mode(0o600)
                .open(path)
                .map_err(|error| AppendError::Io(error.to_string()))?;
        }
        #[cfg(not(unix))]
        {
            fs::File::create(path).map_err(|error| AppendError::Io(error.to_string()))?;
        }
    }
    Ok(())
}

fn timestamp_utc() -> String {
    DateTime::<Utc>::from(SystemTime::now())
        .format("%Y-%m-%dT%H:%M:%SZ")
        .to_string()
}

fn split_ledger(arguments: &[OsString]) -> Result<(Vec<String>, Option<String>), String> {
    let mut rest = Vec::new();
    let mut ledger = None;
    let mut index = 0;
    let values: Vec<String> = arguments
        .iter()
        .map(|value| value.to_string_lossy().into_owned())
        .collect();
    while index < values.len() {
        if values[index] == "--ledger" {
            if index + 1 >= values.len() {
                return Err("--ledger requires a value".to_owned());
            }
            ledger = Some(values[index + 1].clone());
            index += 2;
        } else {
            rest.push(values[index].clone());
            index += 1;
        }
    }
    Ok((rest, ledger))
}

fn flag_map(values: &[String]) -> BTreeMap<String, String> {
    let mut options = BTreeMap::new();
    let mut index = 0;
    while index < values.len() {
        let flag = values[index].clone();
        if !flag.starts_with("--") {
            index += 1;
            continue;
        }
        if index + 1 < values.len() && !values[index + 1].starts_with("--") {
            options.insert(flag, values[index + 1].clone());
            index += 2;
        } else {
            options.insert(flag, String::new());
            index += 1;
        }
    }
    options
}
