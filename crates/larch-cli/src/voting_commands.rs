use crate::{
    argparse_compat::{
        ParsedCommandLine, looks_like_option, missing, parse_with_flags, python_io_error,
        python_repr, resolve_option, split_inline_option, usage_error, write_stdout,
    },
    run_log_entry_commands::{FailureRecordRequest, record_execution_failure},
};
use larch_core::review::{
    FINDINGS_CLASSIFICATION_HEADER, accept_finding, alias_ballot_id, ballot_blocks,
    ballot_parse_text, classify_unbounded_result, code_review_classification_header,
    false_positive_match, panel_tier, parse_judge_vote_text, reviewer_for_block_text,
    vote_for_id_text,
};
use larch_core::{
    file_line_regex, is_security_block_text, python_float, redact, universal_newlines,
};
use regex::Regex;
use sha2::{Digest as _, Sha256};
use std::{
    collections::{BTreeSet, HashSet},
    env,
    ffi::OsString,
    fs,
    io::{self, Write as _},
    path::{Path, PathBuf},
    process::ExitCode,
};
#[rustfmt::skip]
const FILE_REGEX_NAMES: [&str; 7] = [
    "any-re", "extensionless-re", "long-exts", "long-re", "short-exts", "short-line-re", "short-path-re",
];
#[rustfmt::skip]
const PARSE_RATE_OPTIONS: [&str; 9] = [
    "--voter-file", "--voter-tool", "--ballot-file", "--id-grammar", "--review-tmpdir",
    "--slot", "--log-mode", "--plugin-root", "--dispatch-label",
];
#[rustfmt::skip]
const PARSE_RATE_REQUIRED: [&str; 5] = ["--voter-file", "--voter-tool", "--ballot-file", "--id-grammar", "--review-tmpdir"];
const PARSE_RATE_CHECK_USAGE: &str = concat!(
    "usage: parse-rate-check [-h] --voter-file VOTER_FILE --voter-tool VOTER_TOOL\n",
    "                        --ballot-file BALLOT_FILE --id-grammar\n",
    "                        {finding-only,finding-oos} --review-tmpdir\n",
    "                        REVIEW_TMPDIR [--slot SLOT] [--log-mode LOG_MODE]\n",
    "                        [--plugin-root PLUGIN_ROOT]\n",
    "                        [--dispatch-label DISPATCH_LABEL]",
);
const PARSE_RATE_RETRY_USAGE: &str = concat!(
    "usage: parse-rate-retry [-h] --voter-file VOTER_FILE --voter-tool VOTER_TOOL\n",
    "                        --ballot-file BALLOT_FILE --id-grammar\n",
    "                        {finding-only,finding-oos} --review-tmpdir\n",
    "                        REVIEW_TMPDIR [--slot SLOT] [--log-mode LOG_MODE]\n",
    "                        [--plugin-root PLUGIN_ROOT]\n",
    "                        [--dispatch-label DISPATCH_LABEL]\n",
    "                        [--prompt-file PROMPT_FILE]\n",
    "                        [--retry-prefix-kind {code,plan}]\n",
    "                        [--launch-mode LAUNCH_MODE]",
);
fn text(parsed: &ParsedCommandLine, option: &str) -> String {
    parsed
        .value(option)
        .map_or_else(String::new, |value| value.to_string_lossy().into_owned())
}
fn positional(arguments: &[OsString], count: usize, usage: &str) -> Result<Vec<String>, ExitCode> {
    if arguments.len() != count {
        eprintln!("{usage}");
        return Err(ExitCode::from(2));
    }
    Ok(arguments
        .iter()
        .map(|value| value.to_string_lossy().into_owned())
        .collect())
}
macro_rules! positionals {
    ($arguments:expr, $count:literal, $usage:literal) => {
        match positional($arguments, $count, $usage) {
            Ok(values) => values,
            Err(code) => return code,
        }
    };
}
fn argparse_help(usage: &str, options: &[&str]) {
    println!("{usage}\n\noptions:\n  -h, --help            show this help message and exit");
    for option in options {
        let metavar = match *option {
            "--id-grammar" => "{finding-only,finding-oos}".to_owned(),
            "--retry-prefix-kind" => "{code,plan}".to_owned(),
            "--name" => format!("{{{}}}", FILE_REGEX_NAMES.join(",")),
            _ => option
                .trim_start_matches('-')
                .replace('-', "_")
                .to_ascii_uppercase(),
        };
        println!("  {option} {metavar}");
    }
}
fn parse_options(
    arguments: &[OsString],
    program: &str,
    usage: &str,
    options: &[&'static str],
    required: &[&str],
    choices: &[(&str, &[&str])],
) -> Result<ParsedCommandLine, ExitCode> {
    let parsed = parse_with_flags(arguments, options, &["-h", "--help"], 0);
    if let Some(error) = choice_error(arguments, options, choices) {
        return Err(usage_error(usage, program, &error, 2));
    }
    if parsed.flag("-h") || parsed.flag("--help") {
        argparse_help(usage, options);
        return Err(ExitCode::SUCCESS);
    }
    if let Some(error) = parsed.value_error() {
        return Err(usage_error(usage, program, error, 2));
    }
    let required_state: Vec<(&str, bool)> = required
        .iter()
        .map(|option| (*option, parsed.value(option).is_some()))
        .collect();
    if required_state.iter().any(|(_option, present)| !present) {
        return Err(usage_error(usage, program, &missing(&required_state), 2));
    }
    if let Some(error) = parsed.error() {
        return Err(usage_error(usage, program, &error, 2));
    }
    Ok(parsed)
}
#[rustfmt::skip]
fn choice_error(arguments: &[OsString], options: &[&'static str], choices: &[(&str, &[&str])]) -> Option<String> {
    let mut index = 0;
    while index < arguments.len() {
        let text = arguments[index].to_string_lossy();
        index += 1;
        if text == "--" { break; }
        if !looks_like_option(&arguments[index - 1]) { continue; }
        let (name, inline) = split_inline_option(&text);
        if resolve_option(name, &["-h", "--help"]).is_some() { break; }
        let Some(option) = resolve_option(name, options) else {
            let matches = options.iter().filter(|candidate| candidate.starts_with(name)).copied().collect::<Vec<_>>();
            if matches.len() > 1 { return Some(format!("ambiguous option: {text} could match {}", matches.join(", "))); }
            continue;
        };
        let value = if let Some(value) = inline {
            value.to_owned()
        } else {
            let value = arguments.get(index)?;
            if looks_like_option(value) { return None; }
            index += 1;
            value.to_string_lossy().into_owned()
        };
        let Some((_option, allowed)) = choices.iter().find(|(choice, _allowed)| *choice == option)
        else {
            continue;
        };
        if !allowed.contains(&value.as_str()) {
            return Some(format!(
                "argument {option}: invalid choice: {} (choose from {})",
                python_repr(&value),
                allowed
                    .iter()
                    .map(|choice| python_repr(choice))
                    .collect::<Vec<_>>()
                    .join(", ")
            ));
        }
    }
    None
}
#[must_use]
pub fn findings_classification_header(arguments: &[OsString]) -> ExitCode {
    if !arguments.is_empty() {
        eprintln!("usage: findings-classification-header");
        return ExitCode::from(2);
    }
    println!("{FINDINGS_CLASSIFICATION_HEADER}");
    ExitCode::SUCCESS
}
#[must_use]
pub fn code_review_classification_header_command(arguments: &[OsString]) -> ExitCode {
    if !arguments.is_empty() {
        eprintln!("usage: code-review-classification-header");
        return ExitCode::from(2);
    }
    println!("{}", code_review_classification_header(true, true));
    ExitCode::SUCCESS
}
#[must_use]
pub fn vote_for_id(arguments: &[OsString]) -> ExitCode {
    let values = positionals!(arguments, 2, "usage: vote-for-id <id> <voter-file>");
    let vote = fs::read(&values[1]).map_or("JUDGE_ERROR", |bytes| {
        let text = String::from_utf8_lossy(&bytes);
        vote_for_id_text(&values[0], &universal_newlines(&text), "")
    });
    println!("{vote}");
    ExitCode::SUCCESS
}
#[must_use]
pub fn reviewer_for_block(arguments: &[OsString]) -> ExitCode {
    let values = positionals!(arguments, 1, "usage: reviewer-for-block <block-file>");
    let reviewer = fs::read(&values[0]).map_or_else(
        |_| "unknown".to_owned(),
        |bytes| reviewer_for_block_text(&universal_newlines(&String::from_utf8_lossy(&bytes))),
    );
    write_stdout(&reviewer)
}
#[must_use]
pub fn is_security_block(arguments: &[OsString]) -> ExitCode {
    let values = positionals!(arguments, 1, "usage: is-security-block <block-file>");
    let path = Path::new(&values[0]);
    let bytes = match fs::read(path) {
        Ok(bytes) => bytes,
        Err(error) => {
            eprintln!("is_security_block: {}", python_io_error(&error, path));
            return ExitCode::from(2);
        }
    };
    let text = match String::from_utf8(bytes) {
        Ok(text) => text,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
    };
    if is_security_block_text(&universal_newlines(&text)) {
        ExitCode::SUCCESS
    } else {
        ExitCode::FAILURE
    }
}
#[must_use]
pub fn accept_finding_command(arguments: &[OsString]) -> ExitCode {
    let values = positionals!(
        arguments,
        4,
        "usage: accept-finding <yes> <no> <exonerate> <eligible>"
    );
    let Some(counts) = values
        .iter()
        .map(|value| larch_core::python_bigint(value))
        .collect::<Option<Vec<_>>>()
    else {
        return ExitCode::FAILURE;
    };
    let yes = &counts[0];
    let eligible = &counts[3];
    if accept_finding(yes, eligible) {
        ExitCode::SUCCESS
    } else {
        ExitCode::FAILURE
    }
}
#[must_use]
pub fn classify_result(arguments: &[OsString]) -> ExitCode {
    let values = positionals!(
        arguments,
        4,
        "usage: classify-result <yes> <no> <exonerate> <eligible>"
    );
    let Some(counts) = values
        .iter()
        .map(|value| larch_core::python_bigint(value))
        .collect::<Option<Vec<_>>>()
    else {
        return ExitCode::FAILURE;
    };
    let yes = &counts[0];
    let eligible = &counts[3];
    write_stdout(classify_unbounded_result(yes, eligible))
}
#[must_use]
pub fn panel_tier_command(arguments: &[OsString]) -> ExitCode {
    let values = positionals!(arguments, 1, "usage: panel-tier <eligible>");
    let Some(eligible) = larch_core::python_bigint(&values[0]) else {
        return ExitCode::FAILURE;
    };
    write_stdout(panel_tier(&eligible))
}
#[must_use]
pub fn split_ballot(arguments: &[OsString]) -> ExitCode {
    let values = positionals!(arguments, 2, "usage: split-ballot <ballot-file> <out-dir>");
    let out_dir = Path::new(&values[1]);
    if let Err(error) = fs::create_dir_all(out_dir) {
        eprintln!("{error}");
        return ExitCode::FAILURE;
    }
    let bytes = match fs::read(&values[0]) {
        Ok(bytes) => bytes,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
    };
    let text = universal_newlines(&String::from_utf8_lossy(&bytes)).into_owned();
    let blocks = match ballot_blocks(&text) {
        Ok(blocks) => blocks,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
    };
    for (item_id, block) in blocks {
        if let Err(error) = fs::write(out_dir.join(format!("{item_id}.md")), block) {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
    }
    ExitCode::SUCCESS
}
#[must_use]
pub fn parse_judge_vote(arguments: &[OsString]) -> ExitCode {
    let values = positionals!(
        arguments,
        2,
        "usage: parse-judge-vote <voter_file> <ballot_id>"
    );
    let path = Path::new(&values[0]);
    let Ok(Some(bytes)) = path.is_file().then(|| fs::read(path)).transpose() else {
        let message = format!(
            "parse-judge-vote: voter file is missing or unreadable: {}",
            values[0]
        );
        eprintln!("{}", redact(&message).text());
        return ExitCode::from(2);
    };
    let decoded = String::from_utf8_lossy(&bytes);
    let text = universal_newlines(&decoded);
    let parsed = parse_judge_vote_text(&values[1], &text, "");
    println!("PARSED_VOTE={}", parsed.vote);
    println!("PARSED_CORRECTNESS={}", parsed.correctness);
    println!("PARSED_SEVERITY={}", parsed.severity);
    println!("PARSED_QUALITY={}", parsed.quality);
    println!("PARSED_UNCERTAIN={}", parsed.uncertain);
    ExitCode::SUCCESS
}
#[rustfmt::skip]
fn diag_path(voter: &Path) -> PathBuf {
    let text = voter.to_string_lossy();
    text.strip_suffix(".txt").map_or_else(|| PathBuf::from(format!("{text}-parse-rate-diag.txt")), |stem| PathBuf::from(format!("{stem}-parse-rate-diag.txt")))
}
fn sha256_file(path: &Path) -> Result<String, std::io::Error> {
    fs::read(path).map(|bytes| format!("{:x}", Sha256::digest(bytes)))
}
#[rustfmt::skip]
fn darwin_aliases(path: &Path) -> BTreeSet<String> {
    let text = path.to_string_lossy().into_owned();
    let mut normalized = path.components().collect::<PathBuf>().to_string_lossy().into_owned();
    if text.starts_with("//") && !text.starts_with("///") { normalized.insert(0, '/'); }
    if normalized.is_empty() { normalized.push('.'); }
    let mut aliases = BTreeSet::from([text, normalized]);
    for candidate in aliases.clone() {
        if let Some(suffix) = candidate.strip_prefix("/private/var/") { aliases.insert(format!("/var/{suffix}")); }
        else if let Some(suffix) = candidate.strip_prefix("/var/") { aliases.insert(format!("/private/var/{suffix}")); }
    }
    aliases
}
#[must_use]
pub fn parse_rate_diag_matches(arguments: &[OsString]) -> ExitCode {
    const USAGE: &str = "usage: parse-rate-diag-matches [-h] --voter-file VOTER_FILE";
    let parsed = match parse_options(
        arguments,
        "parse-rate-diag-matches",
        USAGE,
        &["--voter-file"],
        &["--voter-file"],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let voter = PathBuf::from(text(&parsed, "--voter-file"));
    let diagnostic = diag_path(&voter);
    if !voter.is_file() || !diagnostic.is_file() {
        return ExitCode::FAILURE;
    }
    let diag_text = match fs::read(&diagnostic) {
        Ok(bytes) => String::from_utf8_lossy(&bytes).into_owned(),
        Err(_) => return ExitCode::FAILURE,
    };
    let mut recorded_path = String::new();
    let mut recorded_sha = String::new();
    for line in larch_core::split_text_lines(&diag_text) {
        if recorded_path.is_empty()
            && let Some(value) = line.strip_prefix("voter_file=")
        {
            value.clone_into(&mut recorded_path);
            continue;
        }
        if recorded_sha.is_empty()
            && let Some(value) = line.strip_prefix("voter_sha256=")
        {
            value.clone_into(&mut recorded_sha);
        }
    }
    let path_matches =
        !darwin_aliases(Path::new(&recorded_path)).is_disjoint(&darwin_aliases(&voter));
    let sha_matches = sha256_file(&voter).is_ok_and(|sha| sha == recorded_sha);
    if !recorded_path.is_empty() && !recorded_sha.is_empty() && path_matches && sha_matches {
        ExitCode::SUCCESS
    } else {
        ExitCode::FAILURE
    }
}
fn ballot_ids(path: &Path, grammar: &str) -> Vec<String> {
    let source = if grammar == "finding-oos" {
        r"^(?:###[\s\x{1c}-\x{1f}]+)?((?:FINDING|OOS)_[0-9]+):"
    } else {
        r"^(?:###[\s\x{1c}-\x{1f}]+)?(FINDING_[0-9]+):"
    };
    let pattern = Regex::new(source).expect("static ballot id regex");
    let Ok(bytes) = fs::read(path) else {
        return Vec::new();
    };
    let decoded = String::from_utf8_lossy(&bytes);
    let text = universal_newlines(&decoded);
    let mut seen = BTreeSet::new();
    let mut ids = Vec::new();
    for line in larch_core::split_text_lines(&text) {
        if let Some(captures) = pattern.captures(line) {
            let item_id = captures[1].to_owned();
            if seen.insert(item_id.clone()) {
                ids.push(item_id);
            }
        }
    }
    ids
}
fn parse_threshold() -> f64 {
    env::var("LARCH_VOTER_JUDGE_ERROR_PARSE_THRESHOLD")
        .ok()
        .and_then(|value| python_float(&value))
        .filter(|value| !(*value <= 0.0 || *value > 1.0))
        .unwrap_or(0.8)
}
fn truthy(name: &str) -> bool {
    env::var(name).is_ok_and(|value| {
        matches!(
            value.to_ascii_lowercase().as_str(),
            "1" | "true" | "yes" | "on"
        )
    })
}
fn plain_diagnostic(message: &str) {
    let sanitized: String = message
        .chars()
        .filter(|character| *character >= ' ' && *character != '\u{7f}')
        .collect();
    let mut line = redact(&sanitized).text().trim_end_matches('\n').to_owned();
    line.push('\n');
    if truthy("LARCH_QUIET_ACTIVE")
        && env::var_os("LARCH_QUIET_PID").is_some_and(|value| !value.is_empty())
        && !truthy("LARCH_QUIET_DISABLE")
        && let Ok(mut fd) = fs::OpenOptions::new().write(true).open("/dev/fd/4")
        && fd.write_all(line.as_bytes()).is_ok()
    {
        return;
    }
    eprint!("{line}");
}
fn harness_path(path: &Path) -> bool {
    let text = path.to_string_lossy();
    [
        "test-dispatch-code-voters.",
        "test_agent_voters.",
        "test-dispatch-plan-voters.",
        "test-plan-review-loop.",
        "test-collect-",
        "test-check-",
        "test-tally-",
    ]
    .iter()
    .any(|token| text.contains(token))
}
fn suppress_issue_append(voter: &Path, base: &Path) -> bool {
    voter != base && voter.starts_with(base) && (harness_path(base) || harness_path(voter))
}
#[rustfmt::skip]
fn issues_log(base: &Path, ambient: bool) -> PathBuf {
    if ambient && let Some(path) = env::var_os("LARCH_EXECUTION_ISSUES_LOG").filter(|value| !value.is_empty()) { return PathBuf::from(path); }
    if let Some(path) = env::var_os("SESSION_ENV_PATH").filter(|value| !value.is_empty()) {
        return PathBuf::from(path)
            .parent()
            .unwrap_or_else(|| Path::new(""))
            .join("execution-issues.md");
    }
    if let Some(path) = env::var_os("IMPLEMENT_TMPDIR").filter(|value| !value.is_empty()) {
        return PathBuf::from(path).join("execution-issues.md");
    }
    base.join("execution-issues.md")
}
#[rustfmt::skip]
fn launcher_tool(voter_tool: &str) -> &str {
    if voter_tool.starts_with("codex-") { "codex" } else if voter_tool.starts_with("cursor-") { "cursor" } else { voter_tool }
}
fn parse_rate_tool_label(voter_tool: &str) -> String {
    match launcher_tool(voter_tool) {
        "claude" => "agent launch-claude-review (voter parse-rate check)".to_owned(),
        tool @ ("codex" | "cursor") => format!(
            "agent launch-review --tool {tool} (voter parse-rate check; label {voter_tool})"
        ),
        _ => format!("voter parse-rate check ({voter_tool})"),
    }
}
struct ParseRateRequest {
    voter_file: PathBuf,
    voter_tool: String,
    ballot_file: PathBuf,
    id_grammar: String,
    review_tmpdir: PathBuf,
    slot: String,
    log_mode: String,
    dispatch_label: String,
}
#[allow(clippy::cast_precision_loss)]
fn check_parse_rate(request: &ParseRateRequest, ambient: bool) -> io::Result<&'static str> {
    let Ok(metadata) = request.voter_file.metadata() else {
        return Ok("OK");
    };
    if !metadata.is_file() || metadata.len() == 0 {
        return Ok("OK");
    }
    let ids = ballot_ids(&request.ballot_file, &request.id_grammar);
    if ids.is_empty() {
        return Ok("OK");
    }
    let bytes = fs::read(&request.voter_file)?;
    let decoded = String::from_utf8_lossy(&bytes);
    let text = universal_newlines(&decoded);
    let ballot_id_set: HashSet<String> = ids.iter().cloned().collect();
    let judge_errors = ids
        .iter()
        .filter(|item_id| {
            let alias = alias_ballot_id(item_id, &ballot_id_set);
            let parsed = parse_judge_vote_text(item_id, &text, &alias);
            parsed.vote.is_empty() || parsed.vote == "JUDGE_ERROR"
        })
        .count();
    let threshold = if ambient { parse_threshold() } else { 0.8 };
    let exceeds_threshold = judge_errors as f64 / (ids.len() as f64) >= threshold;
    if !exceeds_threshold {
        if let Err(error) = fs::remove_file(diag_path(&request.voter_file))
            && error.kind() != io::ErrorKind::NotFound
        {
            return Err(error);
        }
        return Ok("OK");
    }
    let diagnostic = diag_path(&request.voter_file);
    let mut aliases: Vec<String> = darwin_aliases(&request.voter_file).into_iter().collect();
    aliases.sort_by_key(|alias| (alias.starts_with("/private/var/"), alias.clone()));
    let prefix_len = bytes.len().min(200);
    let first_bytes = String::from_utf8_lossy(&bytes[..prefix_len]);
    let mut lines = Vec::new();
    if !request.slot.is_empty() {
        lines.push(format!("slot={}", request.slot));
    }
    lines.extend([
        format!("voter_tool={}", request.voter_tool),
        format!("judge_error_count={judge_errors}"),
        format!("total_findings={}", ids.len()),
        format!("total_ballot_items={}", ids.len()),
    ]);
    lines.extend(
        aliases
            .into_iter()
            .map(|alias| format!("voter_file={alias}")),
    );
    lines.extend([
        format!("voter_sha256={:x}", Sha256::digest(&bytes)),
        "--- first 200 bytes of voter output ---".to_owned(),
        first_bytes.into_owned(),
    ]);
    let _ = fs::write(&diagnostic, format!("{}\n", lines.join("\n")));
    if request.log_mode == "log" {
        if ambient {
            plain_diagnostic(&format!(
                "**⚠ Voter {}: {judge_errors}/{} ballot items returned JUDGE_ERROR: voter likely produced prose without FINDING_N:/OOS_N: VOTE lines. Check voter output at {}.**",
                request.voter_tool,
                ids.len(),
                request.voter_file.display(),
            ));
        }
        if !suppress_issue_append(&request.voter_file, &request.review_tmpdir) {
            let log = issues_log(&request.review_tmpdir, ambient);
            let site = format!("{} {}", request.dispatch_label, request.voter_tool);
            let tool = parse_rate_tool_label(&request.voter_tool);
            let diagnostic_text = diagnostic.to_string_lossy().into_owned();
            let _ = record_execution_failure(&FailureRecordRequest {
                log: &log,
                site: &site,
                tool: &tool,
                exit_code: "0",
                category: "Warnings",
                output_file: &diagnostic_text,
                verdict: "",
                retry_count: "",
                transient_retry_count: "",
                status_label: "warning",
                redact: true,
            });
        }
    }
    Ok("NOT_SUBSTANTIVE")
}
fn parse_rate_request(arguments: &[OsString], retry: bool) -> Result<ParseRateRequest, ExitCode> {
    let mut options = PARSE_RATE_OPTIONS.to_vec();
    let (program, usage) = if retry {
        options.extend(["--prompt-file", "--retry-prefix-kind", "--launch-mode"]);
        ("parse-rate-retry", PARSE_RATE_RETRY_USAGE)
    } else {
        ("parse-rate-check", PARSE_RATE_CHECK_USAGE)
    };
    let parsed = parse_options(
        arguments,
        program,
        usage,
        &options,
        &PARSE_RATE_REQUIRED,
        &[
            ("--id-grammar", &["finding-only", "finding-oos"]),
            ("--retry-prefix-kind", &["code", "plan"]),
        ],
    )?;
    let grammar = text(&parsed, "--id-grammar");
    Ok(ParseRateRequest {
        voter_file: PathBuf::from(text(&parsed, "--voter-file")),
        voter_tool: text(&parsed, "--voter-tool"),
        ballot_file: PathBuf::from(text(&parsed, "--ballot-file")),
        id_grammar: grammar,
        review_tmpdir: PathBuf::from(text(&parsed, "--review-tmpdir")),
        slot: text(&parsed, "--slot"),
        log_mode: if retry {
            "log".to_owned()
        } else {
            parsed.value("--log-mode").map_or_else(
                || "log".to_owned(),
                |mode| mode.to_string_lossy().into_owned(),
            )
        },
        dispatch_label: parsed.value("--dispatch-label").map_or_else(
            || "agent dispatch-voters".to_owned(),
            |label| label.to_string_lossy().into_owned(),
        ),
    })
}
#[must_use]
#[rustfmt::skip]
pub fn parse_rate_check(arguments: &[OsString]) -> ExitCode {
    let request = match parse_rate_request(arguments, false) {
        Ok(request) => request, Err(code) => return code,
    };
    match parse_rate_status(&request, true) {
        Ok(status) => { println!("PARSE_RATE_STATUS={status}"); ExitCode::SUCCESS }, Err(code) => code,
    }
}
#[rustfmt::skip]
fn parse_rate_status(request: &ParseRateRequest, ambient: bool) -> Result<&'static str, ExitCode> {
    check_parse_rate(request, ambient).map_err(|error| { if ambient { eprintln!("{error}"); } ExitCode::FAILURE })
}
fn extract_ctx(arguments: &[OsString]) -> Result<Vec<OsString>, ExitCode> {
    let mut rest = Vec::new();
    let mut index = 0;
    while index < arguments.len() {
        let value = arguments[index].to_string_lossy();
        if value == "--ctx" {
            let Some(_context) = arguments.get(index + 1) else {
                eprintln!("parse-rate-retry: --ctx requires a value");
                return Err(ExitCode::from(2));
            };
            index += 2;
        } else if value.starts_with("--ctx=") {
            index += 1;
        } else {
            rest.push(arguments[index].clone());
            index += 1;
        }
    }
    Ok(rest)
}
#[must_use]
#[rustfmt::skip]
pub fn parse_rate_retry(arguments: &[OsString]) -> ExitCode {
    match parse_rate_retry_result(arguments, true) {
        Ok(status) => { println!("{status}"); ExitCode::SUCCESS }, Err(code) => code,
    }
}
pub fn parse_rate_retry_status(arguments: &[OsString]) -> Result<&'static str, ExitCode> {
    parse_rate_retry_result(arguments, false)
}
#[rustfmt::skip]
fn parse_rate_retry_result(arguments: &[OsString], ambient: bool) -> Result<&'static str, ExitCode> {
    let arguments = extract_ctx(arguments)?; let request = parse_rate_request(&arguments, true)?; parse_rate_status(&request, ambient)
}
#[must_use]
pub fn false_positive_match_command(arguments: &[OsString]) -> ExitCode {
    let values = positionals!(arguments, 1, "usage: false-positive-match <text>");
    if false_positive_match(&values[0]) {
        ExitCode::SUCCESS
    } else {
        ExitCode::FAILURE
    }
}
#[must_use]
pub fn file_line_regex_command(arguments: &[OsString]) -> ExitCode {
    const USAGE: &str = concat!(
        "usage: file-line-regex [-h] --name\n",
        "                       {any-re,extensionless-re,long-exts,long-re,short-exts,short-line-re,short-path-re}",
    );
    let parsed = match parse_options(
        arguments,
        "file-line-regex",
        USAGE,
        &["--name"],
        &["--name"],
        &[("--name", &FILE_REGEX_NAMES)],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let name = text(&parsed, "--name");
    let source = file_line_regex(&name).expect("choice was validated");
    println!("{source}");
    ExitCode::SUCCESS
}
#[must_use]
pub fn ballot_parse(arguments: &[OsString]) -> ExitCode {
    const USAGE: &str = "usage: ballot-parse [-h] --ballot-file BALLOT_FILE";
    let parsed = match parse_options(
        arguments,
        "ballot-parse",
        USAGE,
        &["--ballot-file"],
        &["--ballot-file"],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let path = PathBuf::from(text(&parsed, "--ballot-file"));
    if !path.is_file() {
        eprintln!("ballot-parse: --ballot-file must name a file");
        return ExitCode::from(2);
    }
    let bytes = match fs::read(&path) {
        Ok(bytes) => bytes,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
    };
    let decoded = String::from_utf8_lossy(&bytes);
    let text = universal_newlines(&decoded);
    println!("{}", ballot_parse_text(&text).join("\n"));
    ExitCode::SUCCESS
}
#[cfg(test)]
#[rustfmt::skip]
mod tests {
    use super::*;
    #[test]
    fn parse_rate_diag_path_preserves_the_historical_suffix_rule() {
        assert_eq!(diag_path(Path::new("vote.txt")), PathBuf::from("vote-parse-rate-diag.txt"));
        assert_eq!(diag_path(Path::new("vote.md")), PathBuf::from("vote.md-parse-rate-diag.txt"));
    }
    #[test]
    fn harness_suppression_is_confined_to_the_review_tree() {
        assert!(suppress_issue_append(Path::new("/tmp/test-check-one./vote.txt"), Path::new("/tmp/test-check-one.")));
        assert!(!suppress_issue_append(Path::new("/elsewhere/vote.txt"), Path::new("/tmp/test-check-one.")));
    }
}
