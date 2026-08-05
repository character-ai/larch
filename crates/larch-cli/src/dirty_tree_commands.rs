//! Rust owner for legacy-compatible dirty-tree checkpoint commands.

use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    ffi::{OsStr, OsString},
    fs,
    io::{self, Read as _, Write as _},
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::git::GixRepository;
use larch_core::{RepositoryStatus, StatusOptions};

use crate::valid_meta_path;

const BASELINE_USAGE: &str =
    "usage: dirty-tree baseline [-h] --baseline BASELINE [--sidecar SIDECAR]\n";
const CHECKPOINT_USAGE: &str =
    "usage: dirty-tree checkpoint [-h] [--sidecar SIDECAR] [--cwd CWD]\n";
const SCOPE_CHECK_USAGE: &str = concat!(
    "usage: dirty-tree scope-check [-h] --plan-file PLAN_FILE --paths-file\n",
    "                              PATHS_FILE\n",
);
const SCOPE_MARKER_USAGE: &str = "usage: dirty-tree scope-marker [-h] [--file FILE]\n";

const BASELINE_HELP: &str = concat!(
    "usage: dirty-tree baseline [-h] --baseline BASELINE [--sidecar SIDECAR]\n",
    "\n",
    "options:\n",
    "  -h, --help           show this help message and exit\n",
    "  --baseline BASELINE\n",
    "  --sidecar SIDECAR\n",
);
const CHECKPOINT_HELP: &str = concat!(
    "usage: dirty-tree checkpoint [-h] [--sidecar SIDECAR] [--cwd CWD]\n",
    "\n",
    "options:\n",
    "  -h, --help         show this help message and exit\n",
    "  --sidecar SIDECAR\n",
    "  --cwd CWD\n",
);
const SCOPE_CHECK_HELP: &str = concat!(
    "usage: dirty-tree scope-check [-h] --plan-file PLAN_FILE --paths-file\n",
    "                              PATHS_FILE\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --plan-file PLAN_FILE\n",
    "  --paths-file PATHS_FILE\n",
);
const SCOPE_MARKER_HELP: &str = concat!(
    "usage: dirty-tree scope-marker [-h] [--file FILE]\n",
    "\n",
    "options:\n",
    "  -h, --help   show this help message and exit\n",
    "  --file FILE\n",
);

#[derive(Default)]
struct ParsedOptions {
    help: bool,
    values: BTreeMap<&'static str, OsString>,
    extras: Vec<OsString>,
}

struct ResultDetails {
    reason: Option<&'static str>,
    baseline_state: Option<&'static str>,
    tracked_paths_file: Option<PathBuf>,
    new_untracked_paths_file: Option<PathBuf>,
}

impl ResultDetails {
    const fn checkpoint(reason: Option<&'static str>) -> Self {
        Self {
            reason,
            baseline_state: None,
            tracked_paths_file: None,
            new_untracked_paths_file: None,
        }
    }

    const fn baseline(reason: Option<&'static str>, baseline_state: &'static str) -> Self {
        Self {
            reason,
            baseline_state: Some(baseline_state),
            tracked_paths_file: None,
            new_untracked_paths_file: None,
        }
    }
}

/// Implement the `dirty-tree baseline` compatibility command.
pub fn baseline(arguments: &[OsString]) -> ExitCode {
    let options = match parse_options(arguments, &["--baseline", "--sidecar"]) {
        Ok(options) if options.help => {
            print!("{BASELINE_HELP}");
            return baseline_argv_error(None);
        }
        Ok(options) => options,
        Err(error) => return baseline_argv_error(Some(&error)),
    };
    let Some(baseline_path) = option_path(&options, "--baseline") else {
        return baseline_argv_error(Some("the following arguments are required: --baseline"));
    };
    if !options.extras.is_empty() {
        return baseline_argv_error(Some(&unrecognized_arguments(&options.extras)));
    }
    let sidecar = option_nonempty_path(&options, "--sidecar");
    let output_sidecar = sidecar
        .as_deref()
        .filter(|path| valid_meta_path(path.as_os_str()));
    let lines = baseline_lines(&baseline_path, sidecar.as_deref(), None);
    publish(&lines, output_sidecar);
    ExitCode::SUCCESS
}

/// Implement the `dirty-tree checkpoint` compatibility command.
pub fn checkpoint(arguments: &[OsString]) -> ExitCode {
    let options = match parse_options(arguments, &["--sidecar", "--cwd"]) {
        Ok(options) if options.help => {
            print!("{CHECKPOINT_HELP}");
            return checkpoint_argv_error(None);
        }
        Ok(options) => options,
        Err(error) => return checkpoint_argv_error(Some(&error)),
    };
    if !options.extras.is_empty() {
        return checkpoint_argv_error(Some(&unrecognized_arguments(&options.extras)));
    }
    let sidecar = option_nonempty_path(&options, "--sidecar");
    let output_sidecar = sidecar
        .as_deref()
        .filter(|path| valid_meta_path(path.as_os_str()));
    let cwd = option_nonempty_path(&options, "--cwd").or_else(consumer_repository);
    let lines = checkpoint_lines(cwd.as_deref());
    publish(&lines, output_sidecar);
    ExitCode::SUCCESS
}

/// Implement the `dirty-tree scope-check` compatibility command.
pub fn scope_check(arguments: &[OsString]) -> ExitCode {
    let options = match parse_options(arguments, &["--plan-file", "--paths-file"]) {
        Ok(options) if options.help => {
            print!("{SCOPE_CHECK_HELP}");
            return ExitCode::SUCCESS;
        }
        Ok(options) => options,
        Err(error) => {
            return scope_usage_error(SCOPE_CHECK_USAGE, "dirty-tree scope-check", &error);
        }
    };
    let plan = option_path(&options, "--plan-file");
    let paths = option_path(&options, "--paths-file");
    if plan.is_none() || paths.is_none() {
        let missing = [
            plan.is_none().then_some("--plan-file"),
            paths.is_none().then_some("--paths-file"),
        ]
        .into_iter()
        .flatten()
        .collect::<Vec<_>>()
        .join(", ");
        return scope_usage_error(
            SCOPE_CHECK_USAGE,
            "dirty-tree scope-check",
            &format!("the following arguments are required: {missing}"),
        );
    }
    if !options.extras.is_empty() {
        return scope_usage_error(
            SCOPE_CHECK_USAGE,
            "dirty-tree scope-check",
            &unrecognized_arguments(&options.extras),
        );
    }
    let plan = plan.expect("missing plan file returned above");
    let paths = paths.expect("missing paths file returned above");
    if !plan.is_file() {
        eprintln!(
            "dirty-tree scope-check: plan file not found: {}",
            plan.display()
        );
        return ExitCode::from(2);
    }
    if !paths.is_file() {
        eprintln!(
            "dirty-tree scope-check: recovery paths file not found: {}",
            paths.display()
        );
        return ExitCode::from(2);
    }
    let plan_text = match fs::read(&plan) {
        Ok(bytes) => String::from_utf8_lossy(&bytes).into_owned(),
        Err(error) => return scope_read_error(&error),
    };
    let path_bytes = match fs::read(&paths) {
        Ok(bytes) => bytes,
        Err(error) => return scope_read_error(&error),
    };
    let scope = extract_scope_paths(&plan_text)
        .into_iter()
        .map(String::into_bytes)
        .collect::<BTreeSet<_>>();
    let out_of_scope = path_bytes
        .split(|byte| *byte == b'\0')
        .filter(|path| !path.is_empty() && !scope.contains(*path))
        .collect::<Vec<_>>();
    if out_of_scope.is_empty() {
        return ExitCode::SUCCESS;
    }
    let mut stderr = io::stderr().lock();
    for path in out_of_scope {
        let _ = stderr.write_all(path);
        let _ = stderr.write_all(b"\n");
    }
    ExitCode::FAILURE
}

/// Implement the `dirty-tree scope-marker` compatibility command.
pub fn scope_marker(arguments: &[OsString]) -> ExitCode {
    let options = match parse_options(arguments, &["--file"]) {
        Ok(options) if options.help => {
            print!("{SCOPE_MARKER_HELP}");
            return ExitCode::SUCCESS;
        }
        Ok(options) => options,
        Err(error) => {
            return scope_usage_error(SCOPE_MARKER_USAGE, "dirty-tree scope-marker", &error);
        }
    };
    let file = option_path(&options, "--file").unwrap_or_else(|| PathBuf::from("-"));
    if !options.extras.is_empty() {
        return scope_usage_error(
            SCOPE_MARKER_USAGE,
            "dirty-tree scope-marker",
            &unrecognized_arguments(&options.extras),
        );
    }
    let bytes = if file.as_os_str().is_empty() || file == Path::new("-") {
        let mut input = Vec::new();
        if io::stdin().read_to_end(&mut input).is_err() {
            return ExitCode::FAILURE;
        }
        input
    } else {
        match fs::read(file) {
            Ok(bytes) => bytes,
            Err(_) => return ExitCode::FAILURE,
        }
    };
    if has_scope_reduction_marker(&String::from_utf8_lossy(&bytes)) {
        ExitCode::SUCCESS
    } else {
        ExitCode::FAILURE
    }
}

fn baseline_lines(baseline_path: &Path, sidecar: Option<&Path>, cwd: Option<&Path>) -> Vec<String> {
    if sidecar.is_some_and(|path| !valid_meta_path(path.as_os_str())) {
        return result_lines(
            "unknown",
            "baseline",
            ResultDetails::baseline(Some("bad-sidecar-path"), "missing"),
        );
    }
    if !valid_meta_path(baseline_path.as_os_str()) {
        return result_lines(
            "unknown",
            "baseline",
            ResultDetails::baseline(Some("bad-baseline-path"), "missing"),
        );
    }
    let Ok(status) = repository_status(cwd) else {
        return result_lines(
            "unknown",
            "baseline",
            ResultDetails::baseline(Some("git-status-failed"), "missing"),
        );
    };
    let tracked = tracked_paths(&status);
    let current_untracked = untracked_paths(&status);
    let baseline_state = if baseline_path.is_file() {
        "present"
    } else {
        "missing"
    };
    let prefix = sidecar.map_or_else(default_prefix, Path::to_path_buf);
    let mut details = ResultDetails::baseline(None, baseline_state);
    if !tracked.is_empty() {
        let tracked_path = path_with_suffix(&prefix, ".tracked-paths");
        if !write_nul_paths(&tracked_path, &tracked) {
            return result_lines(
                "unknown",
                "baseline",
                ResultDetails::baseline(Some("tracked-paths-write-failed"), baseline_state),
            );
        }
        details.tracked_paths_file = Some(tracked_path);
    }
    let new_untracked = match new_untracked_paths(baseline_path, &current_untracked, baseline_state)
    {
        Ok(paths) => paths,
        Err(reason) => {
            details.reason = Some(reason);
            return result_lines("unknown", "baseline", details);
        }
    };
    if !new_untracked.is_empty() {
        let untracked_path = path_with_suffix(&prefix, ".new-untracked-paths");
        if !write_nul_paths(&untracked_path, &new_untracked) {
            details.reason = Some("new-untracked-paths-write-failed");
            return result_lines("unknown", "baseline", details);
        }
        details.new_untracked_paths_file = Some(untracked_path);
    }
    if details.tracked_paths_file.is_some() || details.new_untracked_paths_file.is_some() {
        details.reason = Some("working-tree-dirty");
        return result_lines("dirty", "baseline", details);
    }
    result_lines("clean", "baseline", details)
}

fn checkpoint_lines(cwd: Option<&Path>) -> Vec<String> {
    match repository_status(cwd) {
        Ok(status) if status.is_dirty() => result_lines(
            "dirty",
            "checkpoint",
            ResultDetails::checkpoint(Some("checkpoint-dirty")),
        ),
        Ok(_) => result_lines("clean", "checkpoint", ResultDetails::checkpoint(None)),
        Err(_) => result_lines(
            "unknown",
            "checkpoint",
            ResultDetails::checkpoint(Some("git-status-failed")),
        ),
    }
}

fn repository_status(cwd: Option<&Path>) -> Result<RepositoryStatus, larch_core::RepositoryError> {
    GixRepository::discover(cwd.unwrap_or_else(|| Path::new(".")))?
        .local_status(&StatusOptions::default())
}

fn tracked_paths(status: &RepositoryStatus) -> BTreeSet<Vec<u8>> {
    status
        .tree_to_index
        .paths()
        .chain(status.index_to_worktree.paths())
        .chain(status.unmerged.iter().map(|entry| &entry.path))
        .map(|path| path.as_bytes().to_vec())
        .collect()
}

fn untracked_paths(status: &RepositoryStatus) -> BTreeSet<Vec<u8>> {
    status
        .untracked
        .iter()
        .map(|path| path.as_bytes().to_vec())
        .collect()
}

fn new_untracked_paths(
    baseline_path: &Path,
    current: &BTreeSet<Vec<u8>>,
    baseline_state: &'static str,
) -> Result<BTreeSet<Vec<u8>>, &'static str> {
    if baseline_state == "missing" {
        return if current.is_empty() {
            Ok(BTreeSet::new())
        } else {
            Err("baseline-missing-untracked-ambiguous")
        };
    }
    let baseline = fs::read(baseline_path).map_err(|_| "baseline-sort-failed")?;
    let known = split_nul(&baseline);
    Ok(current.difference(&known).cloned().collect())
}

fn split_nul(bytes: &[u8]) -> BTreeSet<Vec<u8>> {
    bytes
        .split(|byte| *byte == b'\0')
        .filter(|path| !path.is_empty())
        .map(ToOwned::to_owned)
        .collect()
}

fn write_nul_paths(path: &Path, paths: &BTreeSet<Vec<u8>>) -> bool {
    let mut data = Vec::new();
    for item in paths {
        data.extend_from_slice(item);
        data.push(b'\0');
    }
    write_atomic(path, &data)
}

fn default_prefix() -> PathBuf {
    env::temp_dir().join(format!("larch-mid-run-dirty-tree.{}", std::process::id()))
}

fn path_with_suffix(path: &Path, suffix: &str) -> PathBuf {
    let mut value = path.as_os_str().to_os_string();
    value.push(suffix);
    PathBuf::from(value)
}

fn write_atomic(path: &Path, data: &[u8]) -> bool {
    let mut temporary_name = path.file_name().map_or_else(OsString::new, OsString::from);
    temporary_name.push(format!(".tmp.{}", std::process::id()));
    let temporary = path.with_file_name(temporary_name);
    if fs::write(&temporary, data)
        .and_then(|()| fs::rename(&temporary, path))
        .is_ok()
    {
        true
    } else {
        let _ = fs::remove_file(temporary);
        false
    }
}

fn result_lines(status: &str, mode: &str, details: ResultDetails) -> Vec<String> {
    let mut lines = vec![format!("STATUS={status}"), format!("MODE={mode}")];
    if mode == "baseline" {
        lines.push(format!(
            "UNTRACKED_BASELINE={}",
            details.baseline_state.unwrap_or("missing")
        ));
    }
    if let Some(path) = details.tracked_paths_file {
        lines.push(format!("TRACKED_PATHS_FILE={}", path.display()));
    }
    if let Some(path) = details.new_untracked_paths_file {
        lines.push(format!("NEW_UNTRACKED_PATHS_FILE={}", path.display()));
    }
    if status != "clean" || details.reason.is_some() {
        lines.push(format!("REASON={}", details.reason.unwrap_or("unknown")));
    }
    lines
}

fn publish(lines: &[String], sidecar: Option<&Path>) {
    let text = format!("{}\n", lines.join("\n"));
    print!("{text}");
    if let Some(path) = sidecar {
        let _ = write_atomic(path, text.as_bytes());
    }
}

fn consumer_repository() -> Option<PathBuf> {
    env::var_os("LARCH_CONSUMER_REPO")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
}

fn parse_options(
    arguments: &[OsString],
    allowed: &[&'static str],
) -> Result<ParsedOptions, String> {
    let mut options = ParsedOptions::default();
    let mut index = 0;
    while let Some(argument) = arguments.get(index) {
        if argument == "--" {
            options.extras.extend_from_slice(&arguments[index..]);
            break;
        }
        let text = argument.to_string_lossy();
        let (name, inline) = split_inline_option(&text);
        if name == "-h" || name == "--help" {
            if inline.is_some() {
                return Err("argument -h/--help: ignored explicit argument".to_owned());
            }
            options.help = true;
            index += 1;
            continue;
        }
        let candidates = allowed
            .iter()
            .copied()
            .filter(|candidate| *candidate == name || candidate.starts_with(name))
            .collect::<Vec<_>>();
        let name = match candidates.as_slice() {
            [] => {
                options.extras.push(argument.clone());
                index += 1;
                continue;
            }
            [name] => *name,
            _ => {
                return Err(format!(
                    "ambiguous option: {} could match {}",
                    argument.to_string_lossy(),
                    candidates.join(", ")
                ));
            }
        };
        let value = if let Some(value) = inline {
            OsString::from(value)
        } else {
            index += 1;
            let Some(value) = arguments.get(index) else {
                return Err(format!("argument {name}: expected one argument"));
            };
            if value_looks_like_option(value) {
                return Err(format!("argument {name}: expected one argument"));
            }
            value.clone()
        };
        let _ = options.values.insert(name, value);
        index += 1;
    }
    Ok(options)
}

fn split_inline_option(value: &str) -> (&str, Option<&str>) {
    let Some(index) = value.as_bytes().iter().position(|byte| *byte == b'=') else {
        return (value, None);
    };
    (&value[..index], Some(&value[index + 1..]))
}

fn value_looks_like_option(value: &OsStr) -> bool {
    let bytes = value.as_encoded_bytes();
    bytes.starts_with(b"-") && bytes != b"-" && !negative_number(bytes)
}

fn negative_number(bytes: &[u8]) -> bool {
    let value = &bytes[1..];
    value.iter().all(u8::is_ascii_digit)
        || value
            .iter()
            .position(|byte| *byte == b'.')
            .is_some_and(|index| {
                let (whole, fraction) = value.split_at(index);
                let fraction = &fraction[1..];
                whole.iter().all(u8::is_ascii_digit)
                    && !fraction.is_empty()
                    && fraction.iter().all(u8::is_ascii_digit)
            })
}

fn join_arguments(arguments: &[OsString]) -> String {
    arguments
        .iter()
        .map(|argument| argument.to_string_lossy())
        .collect::<Vec<_>>()
        .join(" ")
}

fn unrecognized_arguments(arguments: &[OsString]) -> String {
    format!("unrecognized arguments: {}", join_arguments(arguments))
}

fn option_path(options: &ParsedOptions, name: &str) -> Option<PathBuf> {
    options.values.get(name).map(PathBuf::from)
}

fn option_nonempty_path(options: &ParsedOptions, name: &str) -> Option<PathBuf> {
    option_path(options, name).filter(|path| !path.as_os_str().is_empty())
}

fn compatibility_error(usage: &str, program: &str, error: &str) {
    eprint!("{usage}");
    eprintln!("{program}: error: {error}");
}

fn baseline_argv_error(error: Option<&str>) -> ExitCode {
    if let Some(error) = error {
        compatibility_error(BASELINE_USAGE, "dirty-tree baseline", error);
    }
    publish(
        &result_lines(
            "unknown",
            "baseline",
            ResultDetails::baseline(Some("argv-error"), "missing"),
        ),
        None,
    );
    ExitCode::SUCCESS
}

fn checkpoint_argv_error(error: Option<&str>) -> ExitCode {
    if let Some(error) = error {
        compatibility_error(CHECKPOINT_USAGE, "dirty-tree checkpoint", error);
    }
    publish(
        &result_lines(
            "unknown",
            "checkpoint",
            ResultDetails::checkpoint(Some("argv-error")),
        ),
        None,
    );
    ExitCode::SUCCESS
}

fn scope_usage_error(usage: &str, program: &str, error: &str) -> ExitCode {
    compatibility_error(usage, program, error);
    ExitCode::from(2)
}

fn scope_read_error(error: &io::Error) -> ExitCode {
    eprintln!("dirty-tree scope-check: {error}");
    ExitCode::from(2)
}

fn extract_scope_paths(plan: &str) -> Vec<String> {
    let lines = visible_plan_lines(plan);
    let has_scope_section = lines
        .iter()
        .any(|line| is_generic_level_two(line) && is_scope_heading(line));
    let mut in_section = !has_scope_section;
    let mut paths = Vec::new();
    for line in lines {
        if is_scope_heading(line) {
            in_section = true;
            continue;
        }
        if in_section && let Some(tail) = recognized_heading_tail(line) {
            for candidate in heading_paths(tail) {
                if !candidate.starts_with('+') && !paths.contains(&candidate) {
                    paths.push(candidate);
                }
            }
            continue;
        }
        if has_scope_section && in_section && is_generic_level_two(line) {
            break;
        }
    }
    if paths.is_empty() {
        vec!["skills/design/SKILL.md".to_owned()]
    } else {
        paths
    }
}

fn visible_plan_lines(text: &str) -> Vec<&str> {
    let lines = text.lines().collect::<Vec<_>>();
    let mut hidden = vec![false; lines.len()];
    let mut opener: Option<(usize, char, usize)> = None;
    for (index, line) in lines.iter().enumerate() {
        let Some((marker, suffix)) = fence_marker(line) else {
            continue;
        };
        let character = marker.as_bytes()[0] as char;
        let length = marker.len();
        match opener {
            None => opener = Some((index, character, length)),
            Some((open_index, open_character, open_length))
                if character == open_character
                    && length >= open_length
                    && suffix.trim().is_empty() =>
            {
                for value in &mut hidden[open_index + 1..index] {
                    *value = true;
                }
                opener = None;
            }
            Some(_) => {}
        }
    }
    lines
        .into_iter()
        .enumerate()
        .filter_map(|(index, line)| {
            (!hidden[index] && fence_marker(line).is_none()).then_some(line)
        })
        .collect()
}

fn fence_marker(line: &str) -> Option<(&str, &str)> {
    let trimmed = line.trim();
    let first = *trimmed.as_bytes().first()?;
    if !matches!(first, b'`' | b'~') {
        return None;
    }
    let length = trimmed.bytes().take_while(|byte| *byte == first).count();
    (length >= 3).then_some((&trimmed[..length], &trimmed[length..]))
}

fn is_scope_heading(line: &str) -> bool {
    let Some(rest) = line.strip_prefix("##") else {
        return false;
    };
    let Some(first) = rest.chars().next() else {
        return false;
    };
    if !first.is_whitespace() {
        return false;
    }
    matches!(
        rest.split_whitespace().collect::<Vec<_>>().as_slice(),
        ["Files", "to", "modify" | "modify/create"]
    )
}

fn is_generic_level_two(line: &str) -> bool {
    let Some(rest) = line.strip_prefix("##") else {
        return false;
    };
    rest.is_empty() || rest.starts_with([' ', '\t'])
}

fn recognized_heading_tail(line: &str) -> Option<&str> {
    let rest = line
        .strip_prefix("###")
        .or_else(|| line.strip_prefix("##"))?;
    let leading = rest.trim_start_matches([' ', '\t']);
    if leading.len() == rest.len() {
        return None;
    }
    let after_kind = ["NEW", "UPDATED", "REWRITTEN", "MAY_UPDATE"]
        .iter()
        .find_map(|kind| leading.strip_prefix(kind))?;
    if let Some(tail) = after_kind.strip_prefix(':') {
        let path = tail.trim_matches([' ', '\t']);
        return (!path.is_empty()).then_some(path);
    }
    let separated = after_kind.trim_start_matches([' ', '\t']);
    if separated.len() == after_kind.len() {
        return None;
    }
    if let Some(tail) = separated.strip_prefix(':') {
        let path = tail.trim_matches([' ', '\t']);
        return (!path.is_empty()).then_some(path);
    }
    let bracket = separated.strip_prefix('[')?;
    let closing = bracket.find(']')?;
    let path = bracket[..closing].trim_matches([' ', '\t']);
    let suffix = bracket[closing + 1..].trim_matches([' ', '\t']);
    (!path.is_empty() && (suffix.is_empty() || suffix == ":")).then_some(path)
}

fn heading_paths(tail: &str) -> Vec<String> {
    let mut paths = backtick_paths(tail);
    if paths.is_empty() {
        let candidate = tail
            .split_whitespace()
            .next()
            .map_or("", |value| {
                value.split_once('(').map_or(value, |(before, _)| before)
            })
            .trim();
        if !candidate.is_empty() {
            paths.push(candidate.to_owned());
        }
    }
    paths
}

fn backtick_paths(tail: &str) -> Vec<String> {
    let mut paths = Vec::new();
    let mut remainder = tail;
    while let Some(open) = remainder.find('`') {
        let after_open = &remainder[open + 1..];
        let Some(close) = after_open.find('`') else {
            break;
        };
        let value = after_open[..close].trim();
        if !value.is_empty() {
            paths.push(value.to_owned());
        }
        remainder = &after_open[close + 1..];
    }
    paths
}

fn has_scope_reduction_marker(text: &str) -> bool {
    let body = strip_code(text);
    body.lines().any(scope_reduction_in_line)
}

fn strip_code(text: &str) -> String {
    let without_fences = remove_fenced_code(text);
    remove_inline_code(&without_fences)
}

fn remove_fenced_code(text: &str) -> String {
    let mut result = String::new();
    let mut remainder = text;
    while let Some(open) = remainder.find("```") {
        result.push_str(&remainder[..open]);
        let after_open = &remainder[open + 3..];
        let Some(close) = after_open.find("```") else {
            result.push_str(&remainder[open..]);
            return result;
        };
        remainder = &after_open[close + 3..];
    }
    result.push_str(remainder);
    result
}

fn remove_inline_code(text: &str) -> String {
    let mut result = String::new();
    let mut remainder = text;
    while let Some(open) = remainder.find('`') {
        result.push_str(&remainder[..open]);
        let after_open = &remainder[open + 1..];
        let Some(close) = after_open.find('`') else {
            result.push_str(&remainder[open..]);
            return result;
        };
        if after_open[..close].contains('\n') {
            result.push('`');
            remainder = after_open;
            continue;
        }
        remainder = &after_open[close + 1..];
    }
    result.push_str(remainder);
    result
}

fn scope_reduction_in_line(line: &str) -> bool {
    let stripped = line.trim();
    canonical_finding_title(stripped)
        .or_else(|| concern_value(stripped))
        .or_else(|| what_value(stripped))
        .is_some_and(is_scope_reduction)
}

fn canonical_finding_title(line: &str) -> Option<&str> {
    let title = line.strip_prefix("###")?;
    let title = title.trim_start_matches([' ', '\t']);
    if title.len() == line.len() - 3 {
        return None;
    }
    let tail = title.strip_prefix("FINDING_")?;
    let colon = tail.find(':')?;
    (!tail[..colon].is_empty() && tail[..colon].bytes().all(|byte| byte.is_ascii_digit()))
        .then_some(tail[colon + 1..].trim())
}

fn concern_value(line: &str) -> Option<&str> {
    let line = line.strip_prefix('-').unwrap_or(line).trim_start();
    let line = line.strip_prefix("**").unwrap_or(line);
    let tail = strip_ascii_case_prefix(line, "Concern")?;
    let tail = tail.strip_prefix("**").unwrap_or(tail);
    tail.strip_prefix(':').map(str::trim_start)
}

fn what_value(line: &str) -> Option<&str> {
    strip_ascii_case_prefix(line, "what:").map(str::trim_start)
}

fn strip_ascii_case_prefix<'a>(value: &'a str, prefix: &str) -> Option<&'a str> {
    value
        .get(..prefix.len())
        .filter(|candidate| candidate.eq_ignore_ascii_case(prefix))
        .map(|_| &value[prefix.len()..])
}

fn is_scope_reduction(value: &str) -> bool {
    let normalized = normalize_candidate(value);
    normalized.starts_with("[SCOPE-REDUCTION]")
}

fn normalize_candidate(value: &str) -> String {
    let stripped = strip_code(value);
    let mut normalized = stripped.split_whitespace().collect::<Vec<_>>().join(" ");
    for severity in ["[important]", "[nit]", "[latent]"] {
        if normalized
            .get(..severity.len())
            .is_some_and(|prefix| prefix.eq_ignore_ascii_case(severity))
        {
            normalized = normalized[severity.len()..].trim_start().to_owned();
            break;
        }
    }
    normalized
}
