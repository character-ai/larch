//! Rust owner for the four design dialectic candidate commands (#8584).

use std::{
    ffi::{OsStr, OsString},
    fs,
    path::PathBuf,
    process::ExitCode,
};

use larch_adapters::{
    PathIntent, TemporaryRoot, atomic_write_utf8_in, open_confined_read, read_utf8,
};
use larch_core::design::{
    DialecticCandidateSet, dialectic_plan_fingerprint, parse_dialectic_candidates,
    reconcile_dialectic_candidates, render_dialectic_candidates_compact,
    render_dialectic_candidates_pretty,
};
use serde_json::Value;

use crate::argparse_compat::parse_required_with_help;

const AUTO_CANDIDATES: &str = "dialectic-clarifier-candidates.json";
const MANUAL_CANDIDATES: &str = "dialectic-manual-candidates.json";
const RAW_PENDING: &str = ".dialectic-raw-pending.json";
const STATUS_FILE: &str = "dialectic-clarifier-status.json";
const DIGEST_FILE: &str = "dialectic-clarifier-digest.md";
const GENERATION_FILE: &str = "dialectic-clarifier-generation.txt";
const MANUAL_REQUEST: &str = "dialectic-manual-request.txt";

const WRITE_PROGRAM: &str = "cli.py design dialectic-write-candidates";
const WRITE_USAGE: &str = "usage: cli.py design dialectic-write-candidates [-h] --design-tmpdir\n                                                DESIGN_TMPDIR --content-file\n                                                CONTENT_FILE";
const WRITE_HELP: &str = "usage: cli.py design dialectic-write-candidates [-h] --design-tmpdir\n                                                DESIGN_TMPDIR --content-file\n                                                CONTENT_FILE\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --content-file CONTENT_FILE";

const PROMOTE_PROGRAM: &str = "cli.py design dialectic-promote-candidates";
const PROMOTE_USAGE: &str = "usage: cli.py design dialectic-promote-candidates [-h] --design-tmpdir\n                                                  DESIGN_TMPDIR\n                                                  [--raw-dialectic-file RAW_DIALECTIC_FILE]";
const PROMOTE_HELP: &str = "usage: cli.py design dialectic-promote-candidates [-h] --design-tmpdir\n                                                  DESIGN_TMPDIR\n                                                  [--raw-dialectic-file RAW_DIALECTIC_FILE]\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --raw-dialectic-file RAW_DIALECTIC_FILE";

const VALIDATE_PROGRAM: &str = "cli.py design dialectic-validate-candidates";
const VALIDATE_USAGE: &str = "usage: cli.py design dialectic-validate-candidates [-h]\n                                                   [--content-file CONTENT_FILE]\n                                                   [--design-tmpdir DESIGN_TMPDIR]\n                                                   [--require-fingerprint]";
const VALIDATE_HELP: &str = "usage: cli.py design dialectic-validate-candidates [-h]\n                                                   [--content-file CONTENT_FILE]\n                                                   [--design-tmpdir DESIGN_TMPDIR]\n                                                   [--require-fingerprint]\n\noptions:\n  -h, --help            show this help message and exit\n  --content-file CONTENT_FILE\n  --design-tmpdir DESIGN_TMPDIR\n  --require-fingerprint";

const CLEAR_PROGRAM: &str = "cli.py design dialectic-clear-stale";
const CLEAR_USAGE: &str = "usage: cli.py design dialectic-clear-stale [-h] --design-tmpdir DESIGN_TMPDIR\n                                           --reason REASON";
const CLEAR_HELP: &str = "usage: cli.py design dialectic-clear-stale [-h] --design-tmpdir DESIGN_TMPDIR\n                                           --reason REASON\n\noptions:\n  -h, --help            show this help message and exit\n  --design-tmpdir DESIGN_TMPDIR\n  --reason REASON";

#[derive(Clone, Debug)]
struct StatusSidecar {
    kind: String,
    plan_fingerprint: String,
    ordered_candidate_ids: Vec<String>,
    generation: i64,
    state: String,
}

fn resolve_design_root(path: &OsStr) -> Result<TemporaryRoot, String> {
    let path = PathBuf::from(path);
    let valid = fs::symlink_metadata(&path)
        .is_ok_and(|metadata| metadata.is_dir() && !metadata.file_type().is_symlink());
    if !valid {
        return Err("design tmpdir must be an existing non-symlink directory".to_owned());
    }
    let canonical = fs::canonicalize(path)
        .map_err(|_error| "design tmpdir must be an existing non-symlink directory".to_owned())?;
    TemporaryRoot::resolve(Some(&canonical))
        .map_err(|_error| "design tmpdir must be an existing non-symlink directory".to_owned())
}

fn read_root_text(root: &TemporaryRoot, name: &str) -> Result<String, String> {
    let confined = root
        .confine(root.path().join(name), PathIntent::Read)
        .map_err(|error| error.to_string())?;
    read_utf8(&confined).map_err(|error| error.to_string())
}

fn read_root_bytes(root: &TemporaryRoot, name: &str) -> Result<Vec<u8>, String> {
    use std::io::Read as _;

    let confined = root
        .confine(root.path().join(name), PathIntent::Read)
        .map_err(|error| error.to_string())?;
    let mut file = open_confined_read(&confined).map_err(|error| error.to_string())?;
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)
        .map_err(|error| error.to_string())?;
    Ok(bytes)
}

fn root_file_exists(root: &TemporaryRoot, name: &str) -> bool {
    root.confine(root.path().join(name), PathIntent::Read)
        .is_ok()
}

fn write_root_text(root: &TemporaryRoot, name: &str, text: &str) -> Result<(), String> {
    atomic_write_utf8_in(root, &root.path().join(name), text, false, 0o600)
        .map_err(|error| error.to_string())
}

fn unlink_root_file(root: &TemporaryRoot, name: &str) -> Result<(), String> {
    root.revalidate().map_err(|error| error.to_string())?;
    let path = root.path().join(name);
    match fs::remove_file(&path) {
        Ok(()) => root.revalidate().map_err(|error| error.to_string()),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(format!("{}: {error}", path.display())),
    }
}

fn plan_bytes(root: &TemporaryRoot) -> Result<Vec<u8>, String> {
    if !root_file_exists(root, "plan.txt") {
        return Err("plan.txt missing".to_owned());
    }
    read_root_bytes(root, "plan.txt")
}

fn plan_fingerprint(root: &TemporaryRoot) -> Result<String, String> {
    plan_bytes(root).map(|bytes| dialectic_plan_fingerprint(&bytes))
}

fn promote_content(root: &TemporaryRoot, content: &str) -> Result<(), String> {
    let plan = plan_bytes(root)?;
    let fingerprint = dialectic_plan_fingerprint(&plan);
    let candidates = parse_dialectic_candidates(content, Some(&fingerprint), false)
        .map_err(|error| error.to_string())?;
    reconcile_dialectic_candidates(&candidates, &String::from_utf8_lossy(&plan))
        .map_err(|error| error.to_string())?;
    let output =
        render_dialectic_candidates_pretty(&candidates).map_err(|error| error.to_string())?;
    write_root_text(root, AUTO_CANDIDATES, &output)
}

fn kv_safe(value: &str) -> String {
    let mut safe = String::new();
    let mut separator_pending = false;
    for character in value.chars() {
        if character.is_ascii_alphanumeric() || matches!(character, '_' | '.' | ':' | '-') {
            if separator_pending && !safe.is_empty() {
                safe.push('-');
            }
            separator_pending = false;
            safe.push(character);
        } else {
            separator_pending = true;
        }
    }
    let safe = safe.trim_matches('-');
    let safe = safe.get(..safe.len().min(160)).unwrap_or(safe);
    if safe.is_empty() {
        "invalid".to_owned()
    } else {
        safe.to_owned()
    }
}

fn print_write_failure(reason: &str) {
    println!("DIALECTIC_CANDIDATES_WRITTEN=false");
    println!("DIALECTIC_CANDIDATES_FAIL_REASON={}", kv_safe(reason));
}

/// Validate and normalize a candidate payload from a file or stdin.
pub fn validate_candidates(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        VALIDATE_PROGRAM,
        VALIDATE_USAGE,
        VALIDATE_HELP,
        &["--content-file", "--design-tmpdir"],
        &["--require-fingerprint"],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let content = if let Some(path) = parsed.value("--content-file") {
        match fs::read_to_string(path) {
            Ok(content) => content,
            Err(error) => {
                eprintln!("{error}");
                return ExitCode::FAILURE;
            }
        }
    } else {
        let mut content = String::new();
        if let Err(error) = std::io::Read::read_to_string(&mut std::io::stdin(), &mut content) {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
        content
    };
    let fingerprint = match parsed.value("--design-tmpdir") {
        Some(path) => match resolve_design_root(path).and_then(|root| plan_fingerprint(&root)) {
            Ok(fingerprint) => Some(fingerprint),
            Err(error) => {
                eprintln!("{error}");
                return ExitCode::FAILURE;
            }
        },
        None => None,
    };
    match parse_dialectic_candidates(
        &content,
        fingerprint.as_deref(),
        parsed.flag("--require-fingerprint"),
    ) {
        Ok(candidates) => {
            let output = match render_dialectic_candidates_compact(&candidates) {
                Ok(output) => output,
                Err(error) => {
                    eprintln!("{error}");
                    return ExitCode::FAILURE;
                }
            };
            println!("DIALECTIC_CANDIDATES_VALID=true");
            println!("{output}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            println!("DIALECTIC_CANDIDATES_VALID=false");
            println!(
                "DIALECTIC_CANDIDATES_FAIL_REASON={}",
                kv_safe(&error.to_string())
            );
            ExitCode::FAILURE
        }
    }
}

/// Promote the pending drafter sidecar against the current plan, fail-open.
pub fn promote_candidates(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        PROMOTE_PROGRAM,
        PROMOTE_USAGE,
        PROMOTE_HELP,
        &["--design-tmpdir", "--raw-dialectic-file"],
        &[],
        &["--design-tmpdir"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let root = match resolve_design_root(parsed.value("--design-tmpdir").expect("required option"))
    {
        Ok(root) => root,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
    };
    let raw = parsed
        .value("--raw-dialectic-file")
        .map_or_else(|| root.path().join(RAW_PENDING), PathBuf::from);
    if !fs::metadata(&raw).is_ok_and(|metadata| metadata.is_file()) {
        print_write_failure("absent");
        return ExitCode::SUCCESS;
    }
    let result = fs::read_to_string(&raw)
        .map_err(|error| error.to_string())
        .and_then(|content| promote_content(&root, &content));
    if let Err(error) = result {
        print_write_failure(&error);
        return ExitCode::SUCCESS;
    }
    if let Err(error) = fs::remove_file(&raw)
        && error.kind() != std::io::ErrorKind::NotFound
    {
        eprintln!("{}: {error}", raw.display());
        return ExitCode::FAILURE;
    }
    println!("DIALECTIC_CANDIDATES_WRITTEN=true");
    ExitCode::SUCCESS
}

/// Write candidate JSON from a required content file.
pub fn write_candidates(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        WRITE_PROGRAM,
        WRITE_USAGE,
        WRITE_HELP,
        &["--design-tmpdir", "--content-file"],
        &[],
        &["--design-tmpdir", "--content-file"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let root = match resolve_design_root(parsed.value("--design-tmpdir").expect("required option"))
    {
        Ok(root) => root,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
    };
    let source = parsed.value("--content-file").expect("required option");
    if !fs::metadata(source).is_ok_and(|metadata| metadata.is_file()) {
        print_write_failure("content-file-missing");
        return ExitCode::from(2);
    }
    let result = fs::read_to_string(source)
        .map_err(|error| error.to_string())
        .and_then(|content| promote_content(&root, &content));
    match result {
        Ok(()) => {
            println!("DIALECTIC_CANDIDATES_WRITTEN=true");
            ExitCode::SUCCESS
        }
        Err(error) => {
            print_write_failure(&error);
            ExitCode::from(2)
        }
    }
}

fn candidate_set(
    root: &TemporaryRoot,
    name: &str,
    fingerprint: &str,
) -> Option<DialecticCandidateSet> {
    let content = read_root_text(root, name).ok()?;
    parse_dialectic_candidates(&content, Some(fingerprint), true).ok()
}

fn read_generation(root: &TemporaryRoot) -> i64 {
    read_root_text(root, GENERATION_FILE)
        .ok()
        .and_then(|text| text.trim().parse::<i64>().ok())
        .unwrap_or_default()
        .max(0)
}

fn parse_python_int(text: &str) -> Option<i64> {
    let text = text.trim();
    let digits = text
        .strip_prefix(['+', '-'])
        .filter(|digits| !digits.is_empty())
        .unwrap_or(text);
    let bytes = digits.as_bytes();
    if bytes.is_empty()
        || !bytes.iter().enumerate().all(|(index, byte)| {
            byte.is_ascii_digit()
                || (*byte == b'_'
                    && index > 0
                    && index + 1 < bytes.len()
                    && bytes[index - 1].is_ascii_digit()
                    && bytes[index + 1].is_ascii_digit())
        })
    {
        return None;
    }
    text.replace('_', "").parse().ok()
}

fn python_int(value: Option<&Value>) -> i64 {
    match value {
        Some(Value::Bool(value)) => i64::from(*value),
        Some(Value::Number(value)) => value
            .as_i64()
            .or_else(|| value.as_u64().and_then(|value| i64::try_from(value).ok()))
            .or_else(|| {
                let value = value.as_f64()?;
                value
                    .is_finite()
                    .then(|| value.trunc().to_string().parse().ok())
                    .flatten()
            })
            .unwrap_or_default(),
        Some(Value::String(value)) => parse_python_int(value).unwrap_or_default(),
        _ => 0,
    }
}

fn status_from_file(root: &TemporaryRoot) -> Option<StatusSidecar> {
    let payload: Value = serde_json::from_str(&read_root_text(root, STATUS_FILE).ok()?).ok()?;
    let object = payload.as_object()?;
    let ids = object.get("ordered_candidate_ids")?.as_array()?;
    let ordered_candidate_ids = ids
        .iter()
        .map(Value::as_str)
        .collect::<Option<Vec<_>>>()?
        .into_iter()
        .map(str::to_owned)
        .collect();
    let generation = python_int(object.get("generation"));
    let state = match object.get("state") {
        Some(Value::String(state)) => state.clone(),
        Some(_) => return None,
        None => String::new(),
    };
    Some(StatusSidecar {
        kind: object.get("kind")?.as_str()?.to_owned(),
        plan_fingerprint: object.get("plan_fingerprint")?.as_str()?.to_owned(),
        ordered_candidate_ids,
        generation,
        state,
    })
}

fn preserve_manual_status(root: &TemporaryRoot, fingerprint: &str) -> bool {
    let Some(manual) = candidate_set(root, MANUAL_CANDIDATES, fingerprint) else {
        return false;
    };
    let Some(status) = status_from_file(root) else {
        return false;
    };
    root_file_exists(root, DIGEST_FILE)
        && status.kind == "manual"
        && status.plan_fingerprint == manual.plan_fingerprint
        && status.ordered_candidate_ids == manual.ordered_ids()
        && status.generation == read_generation(root)
        && matches!(status.state.as_str(), "complete" | "fallback")
}

fn clear_stale(root: &TemporaryRoot) -> Result<(), String> {
    let fingerprint = plan_fingerprint(root).ok();
    let auto_valid = fingerprint
        .as_deref()
        .and_then(|current| candidate_set(root, AUTO_CANDIDATES, current))
        .is_some();
    if !auto_valid {
        unlink_root_file(root, AUTO_CANDIDATES)?;
    }
    let manual_preserved = fingerprint
        .as_deref()
        .is_some_and(|current| preserve_manual_status(root, current));
    let status_valid = status_from_file(root).is_some_and(|status| {
        fingerprint.as_deref() == Some(status.plan_fingerprint.as_str())
            && ((status.kind == "auto" && auto_valid)
                || (status.kind == "manual" && manual_preserved))
    });
    if !status_valid {
        unlink_root_file(root, STATUS_FILE)?;
        unlink_root_file(root, DIGEST_FILE)?;
    }
    if !manual_preserved {
        unlink_root_file(root, MANUAL_CANDIDATES)?;
        unlink_root_file(root, MANUAL_REQUEST)?;
    }
    Ok(())
}

/// Remove stale candidate artifacts while retaining the pre-promotion raw file.
pub fn clear_stale_candidates(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        CLEAR_PROGRAM,
        CLEAR_USAGE,
        CLEAR_HELP,
        &["--design-tmpdir", "--reason"],
        &[],
        &["--design-tmpdir", "--reason"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let result = resolve_design_root(parsed.value("--design-tmpdir").expect("required option"))
        .and_then(|root| clear_stale(&root));
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("dialectic-clear-stale: {error}");
            ExitCode::from(2)
        }
    }
}
