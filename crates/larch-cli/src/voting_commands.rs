use crate::{
    argparse_compat::{
        ParsedCommandLine, looks_like_option, missing, parse_with_flags,
        parse_with_flags_and_exact, python_io_error, python_repr, resolve_option,
        split_inline_option, usage_error, write_stdout,
    },
    run_log_entry_commands::{FailureRecordRequest, record_execution_failure},
};
#[rustfmt::skip]
use larch_adapters::{PathIntent, TemporaryRoot, absolute_lexical, assert_no_symlink_path_or_ancestors, atomic_write_utf8, ensure_directory_chain, parent_directory, write_confined_file};
use larch_core::review::{
    FINDINGS_CLASSIFICATION_HEADER, TallyRecordFields, VoterPathsFilePolicy, VoterRowLayout,
    VoterSlotState, accept_finding, alias_ballot_id, ballot_blocks, ballot_parse_text,
    classify_unbounded_result, code_review_classification_header,
    compose_self_review_findings_from_tally_json, compose_self_review_findings_jsonl,
    compose_tally_record_json, false_positive_match, panel_tier, parse_judge_vote_text,
    reviewer_for_block_text, scoreboard_scores_from_tsv, vote_for_id_text, voter_status_rows,
};
use larch_core::{
    file_line_regex, is_security_block_text, python_bigint, python_float, redact,
    trim_python_whitespace, universal_newlines,
};
use regex::Regex;
use sha2::{Digest as _, Sha256};
use std::{
    collections::{BTreeSet, HashSet},
    env,
    ffi::OsString,
    fs,
    io::{self, Read as _, Write as _},
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
    let normalized = python_path_text(path);
    let mut aliases = BTreeSet::from([text, normalized]);
    for candidate in aliases.clone() {
        if let Some(suffix) = candidate.strip_prefix("/private/var/") { aliases.insert(format!("/var/{suffix}")); }
        else if let Some(suffix) = candidate.strip_prefix("/var/") { aliases.insert(format!("/private/var/{suffix}")); }
    }
    aliases
}
#[rustfmt::skip]
fn python_path_text(path: &Path) -> String { let text = path.to_string_lossy(); let mut normalized = path.components().filter(|component| !matches!(component, std::path::Component::CurDir)).collect::<PathBuf>().to_string_lossy().into_owned(); if text.starts_with("//") && !text.starts_with("///") { normalized.insert(0, '/'); } else if normalized.is_empty() { normalized.push('.'); } normalized }
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

#[must_use]
pub fn effective_judges(arguments: &[OsString]) -> ExitCode {
    let records: Vec<String> = if arguments.is_empty() {
        let mut input = String::new();
        if let Err(error) = io::stdin().read_to_string(&mut input) {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
        larch_core::split_text_lines(&universal_newlines(&input))
            .into_iter()
            .map(str::to_owned)
            .collect()
    } else {
        arguments
            .iter()
            .map(|argument| argument.to_string_lossy().into_owned())
            .collect()
    };
    let count = records
        .iter()
        .filter(|record| {
            if record.is_empty() {
                return false;
            }
            let mut parts = record.split('\t');
            let status = parts.next().unwrap_or("");
            let path = parts.next().unwrap_or("");
            let parse_rate = parts.next().unwrap_or("");
            status != "failed"
                && parse_rate != "NOT_SUBSTANTIVE"
                && !path.is_empty()
                && Path::new(path).is_file()
                && Path::new(path)
                    .metadata()
                    .is_ok_and(|metadata| metadata.len() > 0)
        })
        .count();
    println!("{count}");
    ExitCode::SUCCESS
}

#[rustfmt::skip]
fn integer_value_error(value: &str) -> ExitCode { eprintln!("ValueError: invalid literal for int() with base 10: {}", python_repr(value)); ExitCode::FAILURE }
#[must_use]
pub fn degraded_warning(arguments: &[OsString]) -> ExitCode {
    let values = match positional(
        arguments,
        if arguments.len() == 2 { 2 } else { 3 },
        "usage: degraded-warning <effective> <expected> [reason]",
    ) {
        Ok(values) if matches!(values.len(), 2 | 3) => values,
        _ => return ExitCode::from(2),
    };
    let Some(effective) = python_bigint(&values[0]) else {
        return integer_value_error(&values[0]);
    };
    let Some(expected) = python_bigint(&values[1]) else {
        return integer_value_error(&values[1]);
    };
    if effective < expected {
        let mut warning = format!(
            "**⚠ Degraded plan-review panel: {effective}/{expected} effective judges produced substantive vote output.**"
        );
        if values.get(2).is_some_and(|reason| !reason.is_empty()) {
            warning.push(' ');
            warning.push_str(&values[2]);
        }
        plain_diagnostic(&warning);
        println!("DEGRADED_PANEL_WARNING={warning}");
    }
    ExitCode::SUCCESS
}

#[must_use]
pub fn voter_status_block(arguments: &[OsString]) -> ExitCode {
    let mut row_layout = "plan_review_interleaved".to_owned();
    let mut paths_file_policy = "nonempty".to_owned();
    let mut values = Vec::new();
    let mut index = 0;
    while index < arguments.len() {
        let raw = arguments[index].to_string_lossy();
        if matches!(raw.as_ref(), "--row-layout" | "--paths-file-policy") {
            let Some(value) = arguments.get(index + 1) else {
                eprintln!("usage: voter-status-block <13 positional args>");
                return ExitCode::from(2);
            };
            let value = value.to_string_lossy();
            if raw == "--row-layout" {
                if !matches!(
                    value.as_ref(),
                    "code_review_sequential" | "plan_review_interleaved"
                ) {
                    eprintln!("ERROR=unknown voter row layout: {value}");
                    return ExitCode::from(2);
                }
                row_layout = value.into_owned();
            } else {
                if !matches!(value.as_ref(), "always" | "nonempty") {
                    eprintln!("ERROR=unknown voter paths-file policy: {value}");
                    return ExitCode::from(2);
                }
                paths_file_policy = value.into_owned();
            }
            index += 2;
        } else {
            values.push(raw.into_owned());
            index += 1;
        }
    }
    if values.len() != 13 {
        eprintln!("usage: voter-status-block <13 positional args>");
        return ExitCode::from(2);
    }
    #[rustfmt::skip]
    let row_layout = if row_layout == "code_review_sequential" { VoterRowLayout::CodeReviewSequential } else { VoterRowLayout::PlanReviewInterleaved };
    #[rustfmt::skip]
    let paths_file_policy = if paths_file_policy == "always" { VoterPathsFilePolicy::Always } else { VoterPathsFilePolicy::Nonempty };
    #[rustfmt::skip]
    let voters = values[..12].chunks_exact(4).map(|fields| VoterSlotState { path: fields[0].clone(), tool: fields[1].clone(), status: fields[2].clone(), parse_rate_status: fields[3].clone() }).collect::<Vec<_>>();
    let paths = Path::new(&values[12]);
    #[rustfmt::skip]
    let paths_file_nonempty = matches!(paths_file_policy, VoterPathsFilePolicy::Nonempty) && !values[12].is_empty() && paths.is_file() && paths.metadata().is_ok_and(|metadata| metadata.len() > 0);
    #[rustfmt::skip]
    let rows = voter_status_rows(&voters, &values[12], row_layout, paths_file_policy, paths_file_nonempty).expect("three fixed voter records");
    for (key, value) in rows {
        println!("{key}={value}");
    }
    ExitCode::SUCCESS
}

#[derive(Default)]
struct TallyArguments {
    log_root: String,
    skill: String,
    run_id: String,
    phase: String,
    mode: String,
    rounds: String,
    accepted: String,
    rejected: String,
    exonerated: String,
    body_file: String,
    self_review_findings_file: String,
}
const COMPOSE_TALLY_USAGE: &str = concat!(
    "usage: cli.py --phase PHASE --mode MODE [--rounds ROUNDS]\n",
    "              [--accepted ACCEPTED] [--rejected REJECTED]\n",
    "              [--exonerated EXONERATED] [--neutral NEUTRAL]\n",
    "              [--body-file BODY_FILE]",
);
const WRITE_TALLY_USAGE: &str = concat!(
    "usage: cli.py --log-root LOG_ROOT --skill SKILL --run-id RUN_ID --phase PHASE\n",
    "              --mode MODE [--rounds ROUNDS] [--accepted ACCEPTED]\n",
    "              [--rejected REJECTED] [--exonerated EXONERATED]\n",
    "              [--neutral NEUTRAL] [--body-file BODY_FILE]",
);

fn non_negative(name: &str, raw: &str) -> Result<String, ExitCode> {
    if raw.is_empty()
        || raw != trim_python_whitespace(raw)
        || raw.starts_with('+')
        || raw.starts_with('-')
        || raw.contains('_')
    {
        eprintln!("ERROR={name} must be a non-negative integer: {raw}");
        return Err(ExitCode::from(2));
    }
    let Some(value) = python_bigint(raw) else {
        eprintln!("ERROR={name} must be a non-negative integer: {raw}");
        return Err(ExitCode::from(2));
    };
    Ok(value.to_string())
}

#[allow(clippy::too_many_lines)] // One parser keeps compose/write error precedence byte-compatible.
fn tally_arguments(arguments: &[OsString], require_log: bool) -> Result<TallyArguments, ExitCode> {
    #[rustfmt::skip]
    const COMPOSE_OPTIONS: [&str; 8] = [
        "--phase", "--mode", "--rounds", "--accepted", "--rejected", "--exonerated", "--neutral", "--body-file",
    ];
    #[rustfmt::skip]
    const WRITE_OPTIONS: [&str; 11] = [
        "--log-root", "--skill", "--run-id", "--phase", "--mode", "--rounds", "--accepted",
        "--rejected", "--exonerated", "--neutral", "--body-file",
    ];
    let options = if require_log {
        &WRITE_OPTIONS[..]
    } else {
        &COMPOSE_OPTIONS[..]
    };
    let parsed = if require_log {
        parse_with_flags_and_exact(arguments, options, &["--self-review-findings-file"], &[], 0)
    } else {
        parse_with_flags(arguments, options, &[], 0)
    };
    let usage = if require_log {
        WRITE_TALLY_USAGE
    } else {
        COMPOSE_TALLY_USAGE
    };
    if let Some(error) = parsed.value_error() {
        return Err(usage_error(usage, "cli.py", error, 2));
    }
    let mut required = vec![
        ("--phase", parsed.value("--phase").is_some()),
        ("--mode", parsed.value("--mode").is_some()),
    ];
    if require_log {
        required.splice(
            0..0,
            [
                ("--log-root", parsed.value("--log-root").is_some()),
                ("--skill", parsed.value("--skill").is_some()),
                ("--run-id", parsed.value("--run-id").is_some()),
            ],
        );
    }
    if required.iter().any(|(_name, present)| !present) {
        return Err(usage_error(usage, "cli.py", &missing(&required), 2));
    }
    if let Some(error) = parsed.error() {
        return Err(usage_error(usage, "cli.py", &error, 2));
    }
    let value = |name: &str, fallback: &str| {
        parsed.value(name).map_or_else(
            || fallback.to_owned(),
            |raw| raw.to_string_lossy().into_owned(),
        )
    };
    let phase = value("--phase", "");
    let mode = value("--mode", "");
    let body_file = value("--body-file", "");
    let allowed: &[&str] = if phase == "plan-review" {
        if body_file.is_empty() {
            eprintln!("ERROR=--body-file is required for --phase plan-review");
            return Err(ExitCode::from(2));
        }
        &["simple", "hard"]
    } else if phase == "code-review" {
        &["simple", "hard", "self-review"]
    } else {
        eprintln!("ERROR=--phase must be plan-review or code-review: {phase}");
        return Err(ExitCode::from(2));
    };
    if !allowed.contains(&mode.as_str()) {
        let mut sorted = allowed.to_vec();
        sorted.sort_unstable();
        eprintln!(
            "ERROR=--mode must be one of {} for --phase {phase}: {mode}",
            sorted.join(", ")
        );
        return Err(ExitCode::from(2));
    }
    let rounds = non_negative("--rounds", &value("--rounds", "0"))?;
    let accepted = non_negative("--accepted", &value("--accepted", "0"))?;
    let rejected = non_negative("--rejected", &value("--rejected", "0"))?;
    let exonerated = non_negative("--exonerated", &value("--exonerated", "0"))?;
    let _neutral = non_negative("--neutral", &value("--neutral", "0"))?;
    if !body_file.is_empty() {
        let body = Path::new(&body_file);
        if !body.is_file() {
            eprintln!("ERROR=body file not found: {body_file}");
            return Err(ExitCode::from(2));
        }
        if body.is_symlink() {
            eprintln!("ERROR=body file must not be a symlink: {body_file}");
            return Err(ExitCode::from(2));
        }
    }
    Ok(TallyArguments {
        log_root: value("--log-root", ""),
        skill: value("--skill", ""),
        run_id: value("--run-id", ""),
        phase,
        mode,
        rounds,
        accepted,
        rejected,
        exonerated,
        body_file,
        self_review_findings_file: value("--self-review-findings-file", ""),
    })
}

fn tally_record(arguments: &TallyArguments) -> Result<(String, &'static str), ExitCode> {
    let (batch, body) = if arguments.phase == "plan-review" {
        let bytes = fs::read(&arguments.body_file).map_err(|error| {
            eprintln!("{error}");
            ExitCode::FAILURE
        })?;
        let body = String::from_utf8(bytes).map_err(|error| {
            eprintln!("{error}");
            ExitCode::FAILURE
        })?;
        (
            "plan-review-tally",
            Some(universal_newlines(&body).into_owned()),
        )
    } else {
        ("code-review-tally", None)
    };
    Ok((
        compose_tally_record_json(&TallyRecordFields {
            phase: &arguments.phase,
            batch,
            mode: &arguments.mode,
            rounds: &arguments.rounds,
            accepted: &arguments.accepted,
            rejected: &arguments.rejected,
            exonerated: &arguments.exonerated,
            body: body.as_deref(),
        }),
        batch,
    ))
}

#[must_use]
pub fn compose_tally_record(arguments: &[OsString]) -> ExitCode {
    if arguments
        .first()
        .is_some_and(|argument| argument == "--self-review-tally-file")
    {
        if arguments.len() != 2 {
            return ExitCode::from(2);
        }
        let path = PathBuf::from(&arguments[1]);
        let bytes = match fs::read(path) {
            Ok(bytes) => bytes,
            Err(error) => {
                eprintln!("{error}");
                return ExitCode::FAILURE;
            }
        };
        return write_stdout(&compose_self_review_findings_from_tally_json(
            &String::from_utf8_lossy(&bytes),
        ));
    }
    let parsed = match tally_arguments(arguments, false) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let (record, _batch) = match tally_record(&parsed) {
        Ok(record) => record,
        Err(code) => return code,
    };
    println!("{record}");
    ExitCode::SUCCESS
}

fn tally_stage_parent(log_root: &str) -> Result<PathBuf, ExitCode> {
    let parent = Path::new(log_root)
        .parent()
        .unwrap_or_else(|| Path::new(""));
    if parent.as_os_str().is_empty() || !parent.is_absolute() || parent.parent().is_none() {
        eprintln!(
            "ERROR=unsafe write-tally staging parent: {}",
            parent.display()
        );
        return Err(ExitCode::from(2));
    }
    let mut current = parent;
    loop {
        if current.is_symlink() {
            eprintln!(
                "ERROR=write-tally staging parent must not have symlinked ancestors: {}",
                current.display()
            );
            return Err(ExitCode::from(2));
        }
        let Some(next) = current.parent() else {
            break;
        };
        if next == current {
            break;
        }
        current = next;
    }
    if !parent.exists() {
        eprintln!(
            "ERROR=write-tally staging parent does not exist: {}",
            parent.display()
        );
        return Err(ExitCode::from(2));
    }
    if !parent.is_dir() {
        eprintln!(
            "ERROR=write-tally staging parent is not a directory: {}",
            parent.display()
        );
        return Err(ExitCode::from(2));
    }
    Ok(parent.to_path_buf())
}

fn unrecognized_code_review_header(body_file: &str) -> Result<Option<String>, String> {
    #[rustfmt::skip]
    const ALLOWED: [&str; 9] = [
        "# Rejected Findings", "## Accepted Findings", "## Rejected Code Review Findings", "## Voting Tally",
        "# Code Review Voting Tally", "## Per-finding vote breakdown", "## Reviewer Competition Scoreboard",
        "## Voter Agreement Scoreboard", "## Voter Severity Scoreboard",
    ];
    let bytes = fs::read(body_file).map_err(|error| error.to_string())?;
    let text = String::from_utf8(bytes).map_err(|error| error.to_string())?;
    let mut in_fence = false;
    let round = Regex::new(r"^# Review Round [0-9]+$").expect("static round regex");
    let rejected = Regex::new(r"^### \[rejected\] FINDING_[0-9]+$").expect("static rejected regex");
    let finding = Regex::new(r"^### FINDING_[0-9]+: ").expect("static finding regex");
    let heading = Regex::new(r"^#{1,6}\s").expect("static heading regex");
    for line in larch_core::split_text_lines(&universal_newlines(&text)) {
        if trim_python_whitespace(line).starts_with("```") {
            in_fence = !in_fence;
            continue;
        }
        if in_fence
            || round.is_match(line)
            || line.starts_with("### [Code Review] ")
            || rejected.is_match(line)
            || finding.is_match(line)
            || ALLOWED.contains(&line)
        {
            continue;
        }
        if heading.is_match(line) {
            return Ok(Some(line.to_owned()));
        }
    }
    Ok(None)
}

#[must_use]
pub fn write_tally(arguments: &[OsString]) -> ExitCode {
    let parsed = match tally_arguments(arguments, true) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    if parsed.phase == "code-review" && !parsed.body_file.is_empty() {
        match unrecognized_code_review_header(&parsed.body_file) {
            Ok(Some(header)) => plain_diagnostic(&format!(
                "WARNING=code-review body header validation ignored: unrecognized section header: {header}"
            )),
            Ok(None) => {}
            Err(error) => {
                eprintln!("ERROR=code-review body header validation failed: {error}");
                return ExitCode::from(2);
            }
        }
    }
    let (record, batch) = match tally_record(&parsed) {
        Ok(record) => record,
        Err(code) => return code,
    };
    let parent = match tally_stage_parent(&parsed.log_root) {
        Ok(parent) => parent,
        Err(code) => return code,
    };
    if !parsed.self_review_findings_file.is_empty() {
        if parsed.mode != "self-review" {
            eprintln!("ERROR=--self-review-findings-file requires --mode self-review");
            return ExitCode::from(2);
        }
        let Ok(accepted) = parsed.accepted.parse::<usize>() else {
            eprintln!("ERROR=--accepted is too large for self-review findings");
            return ExitCode::from(2);
        };
        let Ok(rejected) = parsed.rejected.parse::<usize>() else {
            eprintln!("ERROR=--rejected is too large for self-review findings");
            return ExitCode::from(2);
        };
        let root = match TemporaryRoot::resolve(Some(&parent)) {
            Ok(root) => root,
            Err(error) => {
                eprintln!("{error}");
                return ExitCode::from(2);
            }
        };
        let target = match root.confine(&parsed.self_review_findings_file, PathIntent::Write) {
            Ok(target) => target,
            Err(error) => {
                eprintln!("{error}");
                return ExitCode::from(2);
            }
        };
        if let Err(error) = atomic_write_utf8(
            &target,
            &compose_self_review_findings_jsonl(accepted, rejected),
            0o600,
        ) {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
    }
    let mut staged = match tempfile::Builder::new()
        .prefix("write-tally-record.")
        .tempfile_in(parent)
    {
        Ok(file) => file,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
    };
    if let Err(error) = writeln!(staged, "{record}").and_then(|()| staged.flush()) {
        eprintln!("{error}");
        return ExitCode::FAILURE;
    }
    #[rustfmt::skip]
    let staged_path = staged.path().to_string_lossy().into_owned();
    let run_log_arguments = [
        "--log-root",
        &parsed.log_root,
        "--skill",
        &parsed.skill,
        "--run-id",
        &parsed.run_id,
        "--batch",
        batch,
        "--input-file",
        &staged_path,
    ]
    .into_iter()
    .map(OsString::from)
    .collect::<Vec<_>>();
    crate::run_log_entry_commands::write(&run_log_arguments)
}

fn tally_vote_parse(arguments: &[OsString]) -> Result<(String, Vec<String>), ExitCode> {
    const USAGE: &str = "usage: tally-vote [-h] --ballot-file BALLOT_FILE\n                  [--voter-files [VOTER_FILES ...]]";
    let mut ballot = None;
    let mut voters = Vec::new();
    let mut unknown = Vec::new();
    let mut index = 0;
    while index < arguments.len() {
        let raw = arguments[index].to_string_lossy();
        let (name, inline) = split_inline_option(&raw);
        if resolve_option(name, &["-h", "--help"]).is_some() {
            if let Some(value) = inline {
                return Err(usage_error(
                    USAGE,
                    "tally-vote",
                    &format!("argument -h/--help: ignored explicit argument '{value}'"),
                    2,
                ));
            }
            println!(
                "{USAGE}\n\noptions:\n  -h, --help            show this help message and exit\n  --ballot-file BALLOT_FILE\n  --voter-files [VOTER_FILES ...]"
            );
            return Err(ExitCode::SUCCESS);
        } else if resolve_option(name, &["--ballot-file", "--voter-files"]) == Some("--ballot-file")
        {
            let value = inline.map(str::to_owned).or_else(|| {
                arguments
                    .get(index + 1)
                    .filter(|value| !looks_like_option(value))
                    .map(|value| {
                        index += 1;
                        value.to_string_lossy().into_owned()
                    })
            });
            let Some(value) = value else {
                return Err(usage_error(
                    USAGE,
                    "tally-vote",
                    "argument --ballot-file: expected one argument",
                    2,
                ));
            };
            ballot = Some(value);
        } else if resolve_option(name, &["--ballot-file", "--voter-files"]) == Some("--voter-files")
        {
            voters.clear();
            if let Some(value) = inline {
                voters.push(value.to_owned());
                index += 1;
            } else {
                index += 1;
                while index < arguments.len() && !looks_like_option(&arguments[index]) {
                    voters.push(arguments[index].to_string_lossy().into_owned());
                    index += 1;
                }
            }
            index = index.saturating_sub(1);
        } else {
            unknown.push(arguments[index].to_string_lossy().into_owned());
        }
        index += 1;
    }
    let Some(ballot) = ballot else {
        return Err(usage_error(
            USAGE,
            "tally-vote",
            "the following arguments are required: --ballot-file",
            2,
        ));
    };
    if !unknown.is_empty() {
        return Err(usage_error(
            USAGE,
            "tally-vote",
            &format!("unrecognized arguments: {}", unknown.join(" ")),
            2,
        ));
    }
    Ok((ballot, voters))
}

#[must_use]
pub fn tally_vote(arguments: &[OsString]) -> ExitCode {
    let (ballot, voter_files) = match tally_vote_parse(arguments) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let path = Path::new(&ballot);
    if !path.is_file() {
        eprintln!("tally-vote: --ballot-file must name a file");
        return ExitCode::from(2);
    }
    let bytes = match fs::read(path) {
        Ok(bytes) => bytes,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
    };
    let decoded = String::from_utf8_lossy(&bytes);
    let ballot_text = universal_newlines(&decoded);
    let count = ballot_parse_text(&ballot_text)
        .last()
        .and_then(|line| line.strip_prefix("FINDING_COUNT="))
        .and_then(|value| value.parse::<usize>().ok())
        .unwrap_or(0);
    let mut voter_texts = Vec::with_capacity(voter_files.len());
    for voter_file in &voter_files {
        let path = Path::new(voter_file);
        if !path.is_file() {
            voter_texts.push(None);
            continue;
        }
        let bytes = match fs::read(path) {
            Ok(bytes) => bytes,
            Err(error) => {
                eprintln!("{error}");
                return ExitCode::FAILURE;
            }
        };
        let decoded = String::from_utf8_lossy(&bytes);
        voter_texts.push(Some(universal_newlines(&decoded).into_owned()));
    }
    for finding in 1..=count {
        let prefix = format!("FINDING_{finding}");
        let mut yes = 0;
        let mut no = 0;
        for text in voter_texts.iter().flatten() {
            let mut vote = "";
            for line in larch_core::split_text_lines(text) {
                if line.starts_with(&prefix)
                    && line[prefix.len()..]
                        .chars()
                        .next()
                        .is_none_or(|next| !next.is_ascii_digit())
                {
                    if line.contains("YES") {
                        vote = "YES";
                    } else if line.contains("NO") || line.contains("EXONERATE") {
                        vote = "NO";
                    }
                }
            }
            if vote == "YES" {
                yes += 1;
            } else if vote == "NO" {
                no += 1;
            }
        }
        println!(
            "FINDING_{finding}_ACCEPTED={}",
            if voter_files.len() < 2 || yes >= 2 {
                "true"
            } else {
                "false"
            }
        );
        println!("FINDING_{finding}_VOTES_YES={yes}");
        println!("FINDING_{finding}_VOTES_NO={no}");
    }
    println!("FINDING_COUNT={count}");
    ExitCode::SUCCESS
}

fn scoreboard_parse(arguments: &[OsString]) -> Result<ParsedCommandLine, ExitCode> {
    const USAGE: &str = "usage: scoreboard [-h] [--tally-file TALLY_FILE]\n                  [--findings-classification-file FINDINGS_CLASSIFICATION_FILE]\n                  --reviewer-labels REVIEWER_LABELS --output-file OUTPUT_FILE";
    let options = [
        "--tally-file",
        "--findings-classification-file",
        "--reviewer-labels",
        "--output-file",
    ];
    let parsed = parse_with_flags(arguments, &options, &["-h", "--help"], 0);
    if parsed.flag("-h") || parsed.flag("--help") {
        argparse_help(USAGE, &options);
        return Err(ExitCode::SUCCESS);
    }
    if let Some(error) = parsed.value_error() {
        let error = error.replacen("argument --help:", "argument -h/--help:", 1);
        return Err(usage_error(USAGE, "scoreboard", &error, 2));
    }
    let required = [
        (
            "--reviewer-labels",
            parsed.value("--reviewer-labels").is_some(),
        ),
        ("--output-file", parsed.value("--output-file").is_some()),
    ];
    if required.iter().any(|(_name, present)| !present) {
        return Err(usage_error(USAGE, "scoreboard", &missing(&required), 2));
    }
    if let Some(error) = parsed.error() {
        return Err(usage_error(USAGE, "scoreboard", &error, 2));
    }
    Ok(parsed)
}

fn bash_printf_q(value: &str) -> String {
    if value.is_empty() {
        return "''".to_owned();
    }
    value
        .chars()
        .flat_map(|character| {
            if character.is_ascii_alphanumeric() || "_@%+=:,./-".contains(character) {
                vec![character]
            } else {
                vec!['\\', character]
            }
        })
        .collect()
}
fn trim_decimal(mut value: String) -> String {
    if value.contains('.') {
        while value.ends_with('0') {
            value.pop();
        }
        if value.ends_with('.') {
            value.pop();
        }
    }
    value
}
#[rustfmt::skip]
fn format_score(value: f64) -> String { if value == 0.0 { "0".to_owned() } else if value.fract() == 0.0 { format!("{value:.0}") } else if !value.is_finite() { value.to_string().to_ascii_lowercase() } else { let scientific = format!("{value:.5e}"); let (mantissa, raw_exponent) = scientific.split_once('e').expect("Rust scientific float formatting includes an exponent"); let exponent = raw_exponent.parse::<i32>().expect("Rust scientific float formatting uses a decimal exponent"); if (-4..6).contains(&exponent) { let decimal_places = usize::try_from(5 - exponent).unwrap_or(0); trim_decimal(format!("{value:.decimal_places$}")) } else { format!("{}e{exponent:+03}", trim_decimal(mantissa.to_owned())) } } }

#[must_use]
#[allow(clippy::too_many_lines)] // Validation and rendering stay one atomic output transaction.
pub fn scoreboard(arguments: &[OsString]) -> ExitCode {
    let parsed = match scoreboard_parse(arguments) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let output_text = text(&parsed, "--output-file");
    let output = Path::new(&output_text);
    let absolute_output = absolute_lexical(output);
    if let Err(error) = assert_no_symlink_path_or_ancestors(&absolute_output) {
        eprintln!("{error}");
        return ExitCode::FAILURE;
    }
    if let Err(error) = ensure_directory_chain(&parent_directory(&absolute_output)) {
        eprintln!("{error}");
        return ExitCode::from(2);
    }
    let labels: Vec<String> = text(&parsed, "--reviewer-labels")
        .split(',')
        .map(trim_python_whitespace)
        .filter(|label| !label.is_empty())
        .map(str::to_owned)
        .collect();
    let classification = text(&parsed, "--findings-classification-file");
    let scores = if !classification.is_empty() && Path::new(&classification).is_file() {
        let bytes = match fs::read(&classification) {
            Ok(bytes) => bytes,
            Err(error) => {
                eprintln!("{error}");
                return ExitCode::FAILURE;
            }
        };
        let decoded = String::from_utf8_lossy(&bytes);
        let body = universal_newlines(&decoded);
        let bonus = env::var("LARCH_UNIQUE_FINDER_BONUS")
            .ok()
            .and_then(|raw| python_float(trim_python_whitespace(&raw)))
            .filter(|value| *value > 0.0 && value.is_finite())
            .unwrap_or(0.0);
        match scoreboard_scores_from_tsv(&body, &labels, bonus) {
            Ok(scores) => Some(scores),
            Err(error) => {
                eprintln!("{error}");
                return ExitCode::FAILURE;
            }
        }
    } else {
        None
    };
    let tally = text(&parsed, "--tally-file");
    let tally_text = if !tally.is_empty() && Path::new(&tally).is_file() {
        let bytes = match fs::read(&tally) {
            Ok(bytes) => bytes,
            Err(error) => {
                eprintln!("{error}");
                return ExitCode::FAILURE;
            }
        };
        universal_newlines(&String::from_utf8_lossy(&bytes)).into_owned()
    } else {
        String::new()
    };
    let mut rows = vec!["| Reviewer | Score |".to_owned(), "|---|---:|".to_owned()];
    for label in &labels {
        let score = scores.as_ref().map_or_else(
            || {
                larch_core::split_text_lines(&tally_text)
                    .iter()
                    .filter(|line| {
                        line.contains(&format!("REVIEWER={label} "))
                            && line.contains("ACCEPTED=true")
                    })
                    .fold(0.0, |score, _line| score + 1.0)
            },
            |values| values.get(label).copied().unwrap_or(0.0),
        );
        rows.push(format!("| {label} | {} |", format_score(score)));
    }
    if let Err(error) = write_confined_file(
        &absolute_output,
        &format!("{}\n", rows.join("\n")),
        0o600,
        "scoreboard output",
    ) {
        eprintln!("{error}");
        return ExitCode::FAILURE;
    }
    println!(
        "SCOREBOARD_FILE={}",
        bash_printf_q(&python_path_text(output))
    );
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
    #[cfg(unix)]
    #[test]
    #[rustfmt::skip]
    fn scoreboard_refuses_a_symlink_output() { use std::os::unix::fs::symlink; let root = tempfile::TempDir::new().expect("temp root"); let victim = root.path().join("victim"); fs::write(&victim, "keep").expect("victim"); let output = root.path().join("score"); symlink(&victim, &output).expect("symlink"); let args = ["--reviewer-labels", "One", "--output-file", output.to_str().expect("output")].map(OsString::from); assert_eq!(scoreboard(&args), ExitCode::FAILURE); assert_eq!(fs::read_to_string(victim).expect("victim"), "keep"); let victim_dir = root.path().join("victim-dir/existing"); fs::create_dir_all(&victim_dir).expect("victim directory"); let link = root.path().join("link"); symlink(root.path().join("victim-dir"), &link).expect("ancestor symlink"); let escaped = link.join("existing/new/score"); let args = ["--reviewer-labels", "One", "--output-file", escaped.to_str().expect("escaped output")].map(OsString::from); assert_eq!(scoreboard(&args), ExitCode::FAILURE); assert!(!victim_dir.join("new").exists()); }
}
