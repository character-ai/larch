//! Require larch's authenticated launcher for raw Codex dispatches.
//!
//! # Crate survey (issue #7612)
//!
//! | Need | Selection |
//! |---|---|
//! | Markdown fences | Reuse `MarkdownDocument` fence-state support. |
//! | Shell commands | Reuse the shared tree-sitter Bash parser, retaining only the larch-specific launcher match. |
//! | Rust process builders | Reuse `command_arguments` static builder analysis. |
//! | Python process builders | Reuse the repository UTF-8 snapshot and narrow line grammar retained by the Python owner. |

use std::{collections::BTreeSet, path::Path, sync::LazyLock};

use regex::Regex;
use syn::{ExprMethodCall, visit::Visit};

use crate::{
    Finding, LintError, Repository, Rule, RuleMetadata, RuleOutput,
    suppression::reason,
    syntax::{FenceState, MarkdownDocument, leaf_bash_commands, parse_bash},
};

use super::command_arguments::{Argument, Constants};

const NAME: &str = "codex-exec-auth";
const DESCRIPTION: &str = "Require shared auth wiring for raw Codex dispatches";
const SUPPRESSION_TOKEN: &str = "lint-codex-exec-auth";
const MESSAGE: &str =
    "unwired Codex dispatch without auth wiring; use python3 python/cli.py agent launch-codex-exec";
const PYTHON_MESSAGE: &str =
    "unwired Python Codex dispatch without auth wiring; use python3 python/cli.py agent launch-codex-exec or # lint-codex-exec-auth: ok <reason>";
const REVIEW_CORE_MESSAGE: &str =
    "Step 5 must not subprocess review core; use review_core_capture / review_core_body.review_core";
const ALLOWED_PYTHON_FILE: &str = "python/larch/agents/agents.py";
const REVIEW_CORE_FILES: [&str; 2] = [
    "python/larch/review/review_and_fix.py",
    "python/larch/review/round_runner.py",
];

static CODEX_EXEC: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"(^|[^A-Za-z0-9_])["'\\]?codex["'\\]?\s+exec"#)
        .expect("Codex command expression is valid")
});
static PYTHON_CODEX_EXEC: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"(['\"]codex['\"]\s*,\s*['\"]exec['\"]|['\"]codex\s+exec\b)"#)
        .expect("Python Codex command expression is valid")
});
static REVIEW_CORE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"['\"]review['\"]\s*,\s*['\"]core['\"]|python/cli\.py review core|cli\.py review core"#)
        .expect("review core command expression is valid")
});

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/codex-exec-auth.toml",
);

#[derive(Debug)]
pub struct CodexExecAuthRule;

pub static RULE: CodexExecAuthRule = CodexExecAuthRule;

impl Rule for CodexExecAuthRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let mut findings = Vec::new();
        for path in repository.paths() {
            let source = repository.read_utf8(path)?;
            if is_shell_path(path.as_str()) {
                findings.extend(check_shell(path.as_str(), &source)?);
            } else if is_markdown_path(path.as_str()) {
                findings.extend(check_markdown(path.as_str(), &source)?);
            } else if has_lowercase_extension(path.as_str(), "rs") {
                findings.extend(check_rust(path.as_str(), &source)?);
            } else if is_python_path(path.as_str()) {
                findings.extend(check_python(path.as_str(), &source)?);
            }
        }
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

fn is_shell_path(path: &str) -> bool {
    if !has_lowercase_extension(path, "sh") || path.rsplit('/').next().is_some_and(|name| name.starts_with("test-")) {
        return false;
    }
    let parts: Vec<&str> = path.split('/').collect();
    matches!(parts.as_slice(), ["scripts", _]) || matches!(parts.as_slice(), ["skills", _, "scripts", ..])
}

fn is_markdown_path(path: &str) -> bool {
    (path.starts_with("skills/") || path.starts_with(".claude/skills/")) && has_lowercase_extension(path, "md")
}

fn is_python_path(path: &str) -> bool {
    path.starts_with("python/")
        && !path.starts_with("larch-logs/")
        && has_lowercase_extension(path, "py")
        && !Path::new(path)
            .file_name()
            .and_then(|name| name.to_str())
            .is_some_and(|name| name.starts_with("test_"))
}

fn check_shell(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    let tree = parse_bash(source)?;
    let mut lines = BTreeSet::new();
    for command in leaf_bash_commands(&tree) {
        let text = source.get(command.byte_range()).unwrap_or("");
        if CODEX_EXEC.is_match(text) && !range_suppressed(source, command, SUPPRESSION_TOKEN)? {
            lines.insert(line_number(command.start_position().row));
        }
    }
    Ok(lines
        .into_iter()
        .map(|line| Finding::new(path, line, MESSAGE))
        .collect())
}

fn range_suppressed(source: &str, node: tree_sitter::Node<'_>, token: &str) -> Result<bool, LintError> {
    let start = node.start_position().row;
    let end = node.end_position().row;
    source
        .lines()
        .skip(start)
        .take(end.saturating_sub(start) + 1)
        .try_fold(false, |suppressed, line| {
            Ok(suppressed || reason(line, token)?.is_some())
        })
}

fn check_markdown(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    let mut findings = Vec::new();
    let mut pending = String::new();
    let mut pending_line = 0_usize;
    for line in MarkdownDocument::new(source).lines() {
        let inside_bash = matches!(line.fence_state(), FenceState::Inside { language: Some(language) } if is_bash(language));
        if !inside_bash || line.is_fence_boundary() {
            findings.extend(flush_markdown_line(path, &mut pending, &mut pending_line)?);
            continue;
        }
        if pending.is_empty() {
            pending_line = line.number();
        }
        pending.push_str(line.text());
        if pending.trim_end().ends_with('\\') {
            let length = pending
                .trim_end_matches(char::is_whitespace)
                .strip_suffix('\\')
                .map_or(0, str::len);
            pending.truncate(length);
            pending.push(' ');
            continue;
        }
        findings.extend(flush_markdown_line(path, &mut pending, &mut pending_line)?);
    }
    findings.extend(flush_markdown_line(path, &mut pending, &mut pending_line)?);
    Ok(findings)
}

const fn is_bash(language: &str) -> bool {
    language.eq_ignore_ascii_case("bash")
        || language.eq_ignore_ascii_case("sh")
        || language.eq_ignore_ascii_case("shell")
}

fn flush_markdown_line(
    path: &str,
    pending: &mut String,
    pending_line: &mut usize,
) -> Result<Vec<Finding>, LintError> {
    if pending.is_empty() {
        return Ok(Vec::new());
    }
    let line = std::mem::take(pending);
    let number = std::mem::replace(pending_line, 0);
    if line.trim_start().starts_with('#') || reason(&line, SUPPRESSION_TOKEN)?.is_some() || !CODEX_EXEC.is_match(&line) {
        return Ok(Vec::new());
    }
    let number = u32::try_from(number).map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))?;
    Ok(vec![Finding::new(path, number, MESSAGE)])
}

fn check_rust(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    let syntax = crate::syntax::RustSyntax::parse(path, source)?;
    let constants = Constants::from_file(syntax.file());
    let mut visitor = RustCommandVisitor {
        constants: &constants,
        lines: BTreeSet::new(),
    };
    visitor.visit_file(syntax.file());
    visitor
        .lines
        .into_iter()
        .filter_map(|line| {
            let text = source.lines().nth(line.saturating_sub(1)).unwrap_or("");
            match reason(text, SUPPRESSION_TOKEN) {
                Ok(None) => Some(Ok(Finding::new(path, u32::try_from(line).unwrap_or(u32::MAX), MESSAGE))),
                Ok(Some(_)) => None,
                Err(error) => Some(Err(error)),
            }
        })
        .collect()
}

fn check_python(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    if path == ALLOWED_PYTHON_FILE {
        return Ok(Vec::new());
    }
    let review_core = REVIEW_CORE_FILES.contains(&path);
    let mut findings = Vec::new();
    for (index, line) in source.lines().enumerate() {
        if line.trim_start().starts_with('#') {
            continue;
        }
        if reason(line, SUPPRESSION_TOKEN)?.is_some() {
            continue;
        }
        let line_number = u32::try_from(index + 1)
            .map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))?;
        if PYTHON_CODEX_EXEC.is_match(line) {
            findings.push(Finding::new(path, line_number, PYTHON_MESSAGE));
        }
        if review_core && REVIEW_CORE.is_match(line) {
            findings.push(Finding::new(path, line_number, REVIEW_CORE_MESSAGE));
        }
    }
    Ok(findings)
}

struct RustCommandVisitor<'syntax> {
    constants: &'syntax Constants<'syntax>,
    lines: BTreeSet<usize>,
}

impl<'ast> Visit<'ast> for RustCommandVisitor<'_> {
    fn visit_expr_method_call(&mut self, method: &'ast ExprMethodCall) {
        if let Some(command) = self.constants.extend_builder(method)
            && matches!(command.arguments.as_slice(), [Argument::Static(program), Argument::Static(action), ..] if program == "codex" && action == "exec")
        {
            self.lines.insert(command.root_span.start().line);
        }
        syn::visit::visit_expr_method_call(self, method);
    }
}

fn line_number(row: usize) -> u32 {
    u32::try_from(row + 1).unwrap_or(u32::MAX)
}

fn has_lowercase_extension(path: &str, expected: &str) -> bool {
    Path::new(path)
        .extension()
        .is_some_and(|extension| extension == expected)
}
