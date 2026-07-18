//! Enforce shell contracts previously owned by Python lints.
//!
//! # Crate survey (issue #7610)
//!
//! | Need | Candidates | Selection |
//! |---|---|---|
//! | Bash structure | `tree-sitter-bash`, `brush-parser`, line regexes | Reuse the workspace's maintained `tree-sitter-bash` grammar. It identifies commands, redirections, comments, and heredoc bodies without a second Bash parser. |
//! | Legacy line compatibility | grammar fields alone, bounded source checks | The historic contracts define an exact preamble line and a same-line, reason-bearing suppression. Keep small source-line checks only for those contract literals; the grammar still owns command and heredoc recognition. |

use std::{collections::BTreeMap, sync::LazyLock};

use regex::Regex;
use tree_sitter::{Node, Parser};

use crate::{Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput};

const RAW_STDERR_NAME: &str = "no-raw-stderr-after-quiet-init";
const RAW_STDERR_DESCRIPTION: &str = "Reject raw stderr diagnostics after larch_quiet_init";
const HARNESS_NAME: &str = "harness-session-env";
const HARNESS_DESCRIPTION: &str = "Require shell harnesses to neutralize inherited session state";
const SESSION_ENV_PREAMBLE: &str =
    "unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR";
const RAW_STDERR_MESSAGE: &str =
    "S041/no-raw-stderr-after-quiet-init: raw echo/printf/cat stderr after larch_quiet_init; use larch_err/larch_errf";
const HARNESS_MESSAGE: &str =
    "missing required session-neutralization preamble before the first command";
const SESSION_VARIABLES: [&str; 5] = [
    "IMPLEMENT_TMPDIR",
    "DESIGN_TMPDIR",
    "REVIEW_TMPDIR",
    "RESEARCH_TMPDIR",
    "SESSION_TMPDIR",
];

static SUPPRESSION: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"#\s*lint-harness-session-env:\s*ok\s+\S(?:.*\S)?\s*$")
        .expect("session-env suppression expression is valid")
});

pub static RAW_STDERR_METADATA: RuleMetadata = RuleMetadata::new(
    RAW_STDERR_NAME,
    RAW_STDERR_DESCRIPTION,
    "crates/larch-lint/migration-ledger/no-raw-stderr-after-quiet-init.toml",
);
pub static HARNESS_METADATA: RuleMetadata = RuleMetadata::new(
    HARNESS_NAME,
    HARNESS_DESCRIPTION,
    "crates/larch-lint/migration-ledger/harness-session-env.toml",
);

#[derive(Debug)]
pub struct RawStderrRule;

#[derive(Debug)]
pub struct HarnessSessionEnvRule;

pub static RAW_STDERR_RULE: RawStderrRule = RawStderrRule;
pub static HARNESS_RULE: HarnessSessionEnvRule = HarnessSessionEnvRule;

impl Rule for RawStderrRule {
    fn name(&self) -> &'static str {
        RAW_STDERR_NAME
    }

    fn description(&self) -> &'static str {
        RAW_STDERR_DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let mut findings = Vec::new();
        for path in repository
            .paths()
            .iter()
            .filter(|path| repository.is_committed(path) && is_runtime_shell_path(path.as_str()))
        {
            let source = repository.read_utf8(path)?;
            findings.extend(raw_stderr_findings(path, &source)?);
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

impl Rule for HarnessSessionEnvRule {
    fn name(&self) -> &'static str {
        HARNESS_NAME
    }

    fn description(&self) -> &'static str {
        HARNESS_DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let mut findings = Vec::new();
        for path in repository
            .paths()
            .iter()
            .filter(|path| repository.is_committed(path) && is_harness_path(path.as_str()))
        {
            let source = repository.read_utf8(path)?;
            if !has_harness_preamble(&source)? && !has_reason_bearing_suppression(&source) {
                findings.push(Finding::new(path.as_str(), 1, HARNESS_MESSAGE));
            }
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(RAW_STDERR_METADATA, RAW_STDERR_RULE);
crate::register_rule!(HARNESS_METADATA, HARNESS_RULE);

fn raw_stderr_findings(path: &RepoPath, source: &str) -> Result<Vec<Finding>, LintError> {
    let tree = parse_shell(source)?;
    let mut rows = BTreeMap::<usize, CommandRows>::new();
    collect_command_rows(tree.root_node(), source, false, &mut rows);
    let source_lines: Vec<&str> = source.lines().collect();
    let mut after_quiet_init = false;
    let mut findings = Vec::new();
    for (row, commands) in rows {
        if !after_quiet_init {
            if commands.has_quiet_init {
                after_quiet_init = true;
            }
            continue;
        }
        if commands.has_raw_stderr
            && source_lines
                .get(row)
                .is_some_and(|line| !unquoted_shell_code(line).contains("larch_err"))
        {
            findings.push(Finding::new(path.as_str(), line_number(row), RAW_STDERR_MESSAGE));
        }
    }
    Ok(findings)
}

fn has_harness_preamble(source: &str) -> Result<bool, LintError> {
    let tree = parse_shell(source)?;
    let Some(first_command) = first_command(tree.root_node()) else {
        return Ok(false);
    };
    Ok(source
        .lines()
        .nth(first_command.start_position().row)
        .is_some_and(|line| line == SESSION_ENV_PREAMBLE))
}

fn parse_shell(source: &str) -> Result<tree_sitter::Tree, LintError> {
    let mut parser = Parser::new();
    parser
        .set_language(&tree_sitter_bash::LANGUAGE.into())
        .map_err(|error| LintError::new(format!("cannot configure Bash parser: {error}")))?;
    parser
        .parse(source, None)
        .ok_or_else(|| LintError::new("cannot parse Bash source"))
}

fn first_command(root: Node<'_>) -> Option<Node<'_>> {
    let mut cursor = root.walk();
    root.named_children(&mut cursor)
        .find(|child| child.kind() != "comment")
}

fn collect_command_rows(
    node: Node<'_>,
    source: &str,
    within_heredoc: bool,
    rows: &mut BTreeMap<usize, CommandRows>,
) {
    let inside_heredoc = within_heredoc || node.kind() == "heredoc_body";
    if node.kind() == "command" && !inside_heredoc {
        let row = rows.entry(node.start_position().row).or_default();
        row.has_quiet_init |= command_name(node, source) == Some("larch_quiet_init");
        row.has_raw_stderr |= is_raw_stderr_command(node, source);
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_command_rows(child, source, inside_heredoc, rows);
    }
}

fn command_name<'source>(node: Node<'_>, source: &'source str) -> Option<&'source str> {
    let name = node.child_by_field_name("name")?;
    source.get(name.byte_range())
}

fn is_raw_stderr_command(node: Node<'_>, source: &str) -> bool {
    matches!(command_name(node, source), Some("echo" | "printf" | "cat"))
        && has_stderr_redirect(node, source)
}

fn has_stderr_redirect(node: Node<'_>, source: &str) -> bool {
    let redirect_owner = match node.parent() {
        Some(parent) if parent.kind() == "redirected_statement" => parent,
        _ => node,
    };
    let mut cursor = redirect_owner.walk();
    redirect_owner
        .named_children(&mut cursor)
        .filter(|child| child.kind() == "file_redirect")
        .any(|redirect| {
            let Some(destination) = redirect.child_by_field_name("destination") else {
                return false;
            };
            source
                .get(redirect.byte_range())
                .is_some_and(|text| text.contains(">&"))
                && source
                    .get(destination.byte_range())
                    .is_some_and(|text| text.trim() == "2")
        })
}

fn has_reason_bearing_suppression(source: &str) -> bool {
    source
        .lines()
        .find(|line| !line.trim_start().starts_with('#') && contains_session_variable(line))
        .is_some_and(|line| SUPPRESSION.is_match(line))
}

fn contains_session_variable(line: &str) -> bool {
    SESSION_VARIABLES.iter().any(|variable| {
        line.match_indices(variable).any(|(start, _)| {
            let end = start + variable.len();
            !line
                .as_bytes()
                .get(start.wrapping_sub(1))
                .is_some_and(|byte| is_word_byte(*byte))
                && !line
                    .as_bytes()
                    .get(end)
                    .is_some_and(|byte| is_word_byte(*byte))
        })
    })
}

fn unquoted_shell_code(line: &str) -> String {
    let mut output = String::with_capacity(line.len());
    let mut quote = None;
    let mut escaped = false;
    for character in line.chars() {
        if let Some(active_quote) = quote {
            output.push(' ');
            if escaped {
                escaped = false;
            } else if character == '\\' && active_quote == '"' {
                escaped = true;
            } else if character == active_quote {
                quote = None;
            }
        } else if matches!(character, '\'' | '"') {
            quote = Some(character);
            output.push(' ');
        } else if character == '#' {
            output.extend(std::iter::repeat_n(' ', line.len() - output.len()));
            break;
        } else {
            output.push(character);
        }
    }
    output
}

fn is_runtime_shell_path(path: &str) -> bool {
    // The legacy Python rule intentionally scopes lowercase `.sh` paths only.
    #[allow(clippy::case_sensitive_file_extension_comparisons)]
    if !path.ends_with(".sh") {
        return false;
    }
    let parts: Vec<&str> = path.split('/').collect();
    matches!(parts.as_slice(), ["scripts" | "hooks", _])
        || matches!(parts.as_slice(), ["skills", _, "scripts", _])
}

fn is_harness_path(path: &str) -> bool {
    let parts: Vec<&str> = path.split('/').collect();
    matches!(parts.as_slice(), ["scripts", filename] if is_test_shell(filename))
        || matches!(parts.as_slice(), ["skills", _, "scripts", filename] if is_test_shell(filename))
}

#[allow(clippy::case_sensitive_file_extension_comparisons)] // Legacy Python glob matched lowercase `.sh` names only.
fn is_test_shell(filename: &str) -> bool {
    filename.starts_with("test-") && filename.ends_with(".sh")
}

const fn is_word_byte(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || byte == b'_'
}

fn line_number(row: usize) -> u32 {
    u32::try_from(row + 1).unwrap_or(u32::MAX)
}

#[derive(Default)]
struct CommandRows {
    has_quiet_init: bool,
    has_raw_stderr: bool,
}
