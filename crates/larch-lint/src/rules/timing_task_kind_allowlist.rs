//! Require literal timing task kinds to use the canonical allow-list.
//!
//! # Crate survey (issue #7612)
//!
//! | Need | Selection |
//! |---|---|
//! | Shell and Markdown text | Reuse repository discovery and the workspace regex engine. |
//! | Rust command construction | Reuse `command_arguments` static array and builder analysis. |
//! | Rust CLI defaults | Reuse `syn` attribute parsing for Clap's `arg` attributes. |
//! | Python argv and defaults | Reuse the workspace `tree-sitter-python` grammar. |
//!
//! The canonical policy is Rust's `TIMING_TASK_KINDS_ALLOWED`. This rule reads
//! that source directly so Python, shell, Markdown, and Rust consumers all
//! validate against the one timing owner. Python argv and default shapes that
//! cannot prove a finite literal set fail closed. The recognized environment
//! fallback forms retain the runtime timing-token grammar for the environment
//! value while validating their static fallback here.

use std::{
    collections::{BTreeMap, BTreeSet},
    path::Path,
    sync::LazyLock,
};

use regex::Regex;
use syn::{
    Attribute, Expr, ExprArray, ExprCall, ExprMethodCall, Field, LitStr, spanned::Spanned,
    visit::Visit,
};
use tree_sitter::Node;

use crate::{
    Finding, LintError, RepoPath, Repository, Rule, RuleDispatchPriority, RuleMetadata,
    RuleOutput, syntax::RustSyntax,
};

use super::command_arguments::{Argument, BuilderCommand, Constants, array_arguments, record_builder_from_method};

const NAME: &str = "timing-task-kind-allowlist";
const DESCRIPTION: &str = "Require literal timing task kinds to appear in the canonical allow-list";
const ALLOWLIST_PATH: &str = "crates/larch-core/src/report/timing.rs";
const TIMING_FLAG: &str = "--timing-task-kind";

static TEXT_KIND: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"--timing-task-kind\s+([A-Za-z0-9][A-Za-z0-9_-]*)")
        .expect("timing task kind expression is valid")
});
static ALLOWLIST_BODY: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?s)TIMING_TASK_KINDS_ALLOWED\s*:\s*\[&str;\s*\d+\]\s*=\s*\[(?P<body>.*?)\];")
        .expect("canonical allow-list expression is valid")
});
static QUOTED_KIND: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"[\"']([a-z][a-z0-9-]{0,63})[\"']"#).expect("quoted kind expression is valid")
});

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/timing-task-kind-allowlist.toml",
);

#[derive(Debug)]
pub struct TimingTaskKindAllowlistRule;

pub static RULE: TimingTaskKindAllowlistRule = TimingTaskKindAllowlistRule;

impl Rule for TimingTaskKindAllowlistRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn dispatch_priority(&self) -> RuleDispatchPriority {
        RuleDispatchPriority::Early
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let paths: Vec<_> = repository
            .paths()
            .iter()
            .filter(|path| {
                is_text_scope(path.as_str())
                    || is_python_scope(path.as_str())
                    || is_rust_scope(path.as_str())
            })
            .collect();
        if paths.is_empty() {
            return Ok(RuleOutput::from_findings(Vec::new()));
        }
        let allowed = allowed_kinds(repository)?;
        let mut findings = Vec::new();
        for path in paths {
            let source = repository.read_utf8(path)?;
            if is_text_scope(path.as_str()) {
                findings.extend(check_text(path.as_str(), &source, &allowed)?);
            } else if is_python_scope(path.as_str()) {
                let syntax = repository.python_syntax(path)?;
                findings.extend(check_python(path.as_str(), &source, &syntax, &allowed)?);
            } else if is_rust_scope(path.as_str()) {
                findings.extend(check_rust(path.as_str(), &source, &allowed)?);
            }
        }
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

fn allowed_kinds(repository: &Repository) -> Result<BTreeSet<String>, LintError> {
    let path = RepoPath::from_trusted(ALLOWLIST_PATH);
    let source = repository.read_required_utf8(&path, format!("missing canonical timing allow-list: {ALLOWLIST_PATH}"))?;
    let body = ALLOWLIST_BODY
        .captures(&source)
        .and_then(|captures| captures.name("body"))
        .ok_or_else(|| LintError::new(format!("cannot parse canonical timing allow-list: {ALLOWLIST_PATH}")))?
        .as_str();
    let kinds: BTreeSet<String> = QUOTED_KIND
        .captures_iter(body)
        .filter_map(|captures| captures.get(1))
        .map(|capture| capture.as_str().to_owned())
        .collect();
    if kinds.is_empty() {
        return Err(LintError::new(format!("canonical timing allow-list is empty: {ALLOWLIST_PATH}")));
    }
    Ok(kinds)
}

fn is_text_scope(path: &str) -> bool {
    if path.contains("larch-logs/") || path.contains("test_fixtures/") {
        return false;
    }
    let parts: Vec<&str> = path.split('/').collect();
    let filename = parts.last().copied().unwrap_or("");
    if filename.starts_with("test-") || filename.starts_with("test_") {
        return false;
    }
    matches!(parts.as_slice(), ["skills", _, "SKILL.md"])
        || matches!(parts.as_slice(), ["skills", _, "references", ..])
            && has_lowercase_extension(path, "md")
        || matches!(parts.as_slice(), ["skills", _, "scripts", ..])
            && has_lowercase_extension(path, "sh")
}

fn is_rust_scope(path: &str) -> bool {
    path.starts_with("crates/") && has_lowercase_extension(path, "rs")
}

fn is_python_scope(path: &str) -> bool {
    if !path.starts_with("python/larch/") || !has_lowercase_extension(path, "py") {
        return false;
    }
    let mut parts = path.split('/');
    if parts.any(|part| part == "larch-logs" || part == "test_fixtures") {
        return false;
    }
    let filename = path.rsplit('/').next().unwrap_or("");
    !filename.starts_with("test-") && !filename.starts_with("test_")
}

fn check_text(path: &str, source: &str, allowed: &BTreeSet<String>) -> Result<Vec<Finding>, LintError> {
    let mut findings = Vec::new();
    for matched in TEXT_KIND.captures_iter(source) {
        let Some(kind) = matched.get(1).map(|capture| capture.as_str()) else {
            continue;
        };
        if !allowed.contains(kind) {
            let start = matched.get(0).map_or(0, |capture| capture.start());
            let line = source[..start].bytes().filter(|byte| *byte == b'\n').count() + 1;
            findings.push(Finding::new(path, number(path, line)?, missing_message(kind)));
        }
    }
    Ok(findings)
}

fn check_rust(path: &str, source: &str, allowed: &BTreeSet<String>) -> Result<Vec<Finding>, LintError> {
    let syntax = RustSyntax::parse(path, source)?;
    let constants = Constants::from_file(syntax.file());
    let mut visitor = RustVisitor::new(&constants);
    visitor.visit_file(syntax.file());
    visitor
        .finish()
        .into_iter()
        .filter(|(_, kind)| !allowed.contains(kind))
        .map(|(line, kind)| Ok(Finding::new(path, number(path, line)?, missing_message(&kind))))
        .collect()
}

fn check_python(
    path: &str,
    source: &str,
    syntax: &tree_sitter::Tree,
    allowed: &BTreeSet<String>,
) -> Result<Vec<Finding>, LintError> {
    if syntax.root_node().has_error() {
        return Err(LintError::new(format!("{path}: invalid Python syntax")));
    }
    let mut candidates = Vec::new();
    collect_python_candidates(syntax.root_node(), source, &mut candidates);
    candidates
        .into_iter()
        .filter_map(|(line, kind)| match kind {
            Some(kind) if allowed.contains(&kind) => None,
            Some(kind) => Some((line, missing_message(&kind))),
            None => Some((line, dynamic_message())),
        })
        .map(|(line, message)| Ok(Finding::new(path, number(path, line)?, message)))
        .collect()
}

fn collect_python_candidates(
    node: Node<'_>,
    source: &str,
    candidates: &mut Vec<(usize, Option<String>)>,
) {
    match node.kind() {
        "list" | "tuple" => collect_python_sequence(node, source, candidates),
        "call" => collect_python_argparse_default(node, source, candidates),
        _ => {}
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_python_candidates(child, source, candidates);
    }
}

fn collect_python_sequence(
    node: Node<'_>,
    source: &str,
    candidates: &mut Vec<(usize, Option<String>)>,
) {
    let mut cursor = node.walk();
    let elements: Vec<_> = node.named_children(&mut cursor).collect();
    for (index, element) in elements.iter().copied().enumerate() {
        if python_static_string(element, source).as_deref() != Some(TIMING_FLAG) {
            continue;
        }
        let value = elements.get(index + 1).copied();
        let line = value.unwrap_or(element).start_position().row + 1;
        candidates.push((line, value.and_then(|value| nonempty_python_string(value, source))));
    }
}

fn collect_python_argparse_default(
    call: Node<'_>,
    source: &str,
    candidates: &mut Vec<(usize, Option<String>)>,
) {
    let Some(function) = call.child_by_field_name("function") else {
        return;
    };
    if function.kind() != "attribute"
        || function
            .child_by_field_name("attribute")
            .and_then(|attribute| node_text(attribute, source))
            != Some("add_argument")
    {
        return;
    }
    let Some(arguments) = call.child_by_field_name("arguments") else {
        return;
    };
    let mut cursor = arguments.walk();
    let values: Vec<_> = arguments.named_children(&mut cursor).collect();
    let first_positional = values
        .iter()
        .copied()
        .find(|argument| argument.kind() != "keyword_argument");
    if first_positional.and_then(|node| python_static_string(node, source)).as_deref()
        != Some(TIMING_FLAG)
    {
        return;
    }
    for argument in values {
        if argument.kind() != "keyword_argument"
            || argument
                .child_by_field_name("name")
                .and_then(|name| node_text(name, source))
                != Some("default")
        {
            continue;
        }
        if let Some(value) = argument.child_by_field_name("value")
            && !collect_python_default_literals(value, source, candidates)
        {
            candidates.push((value.start_position().row + 1, None));
        }
    }
}

fn collect_python_default_literals(
    node: Node<'_>,
    source: &str,
    candidates: &mut Vec<(usize, Option<String>)>,
) -> bool {
    if let Some(kind) = python_static_string(node, source) {
        if kind.is_empty() {
            return false;
        }
        remember_python_kind(candidates, node, kind);
        return true;
    }
    match node.kind() {
        "boolean_operator" if node.child_by_field_name("operator").and_then(|operator| node_text(operator, source)) == Some("or") => {
            let left = node
                .child_by_field_name("left")
                .is_some_and(|left| collect_python_default_literals(left, source, candidates));
            let right = node
                .child_by_field_name("right")
                .is_some_and(|right| collect_python_default_literals(right, source, candidates));
            left && right
        }
        "conditional_expression" => {
            let mut cursor = node.walk();
            let branches: Vec<_> = node.named_children(&mut cursor).collect();
            let body = branches
                .first()
                .is_some_and(|body| collect_python_default_literals(*body, source, candidates));
            let otherwise = branches.len() > 1
                && branches
                    .last()
                    .is_some_and(|otherwise| collect_python_default_literals(*otherwise, source, candidates));
            body && otherwise
        }
        "call" => collect_python_environment_fallback(node, source, candidates),
        "parenthesized_expression" => {
            let mut cursor = node.walk();
            node.named_children(&mut cursor)
                .next()
                .is_some_and(|value| collect_python_default_literals(value, source, candidates))
        }
        _ => false,
    }
}

fn collect_python_environment_fallback(
    call: Node<'_>,
    source: &str,
    candidates: &mut Vec<(usize, Option<String>)>,
) -> bool {
    let Some(function) = call.child_by_field_name("function") else {
        return false;
    };
    if function.kind() != "attribute"
        || !function
            .child_by_field_name("attribute")
            .and_then(|attribute| node_text(attribute, source))
            .is_some_and(|attribute| matches!(attribute, "get" | "getenv"))
    {
        return false;
    }
    let Some(arguments) = call.child_by_field_name("arguments") else {
        return false;
    };
    let mut cursor = arguments.walk();
    let positional: Vec<_> = arguments
        .named_children(&mut cursor)
        .filter(|argument| argument.kind() != "keyword_argument")
        .collect();
    let Some(fallback) = positional.get(1).copied() else {
        return false;
    };
    let Some(kind) = python_static_string(fallback, source) else {
        return false;
    };
    if !kind.is_empty() {
        remember_python_kind(candidates, fallback, kind);
    }
    true
}

fn remember_python_kind(
    candidates: &mut Vec<(usize, Option<String>)>,
    node: Node<'_>,
    kind: String,
) {
    candidates.push((node.start_position().row + 1, Some(kind)));
}

fn nonempty_python_string(node: Node<'_>, source: &str) -> Option<String> {
    python_static_string(node, source).filter(|value| !value.is_empty())
}

fn python_static_string(node: Node<'_>, source: &str) -> Option<String> {
    if node.kind() == "concatenated_string" {
        let mut value = String::new();
        let mut cursor = node.walk();
        for child in node.named_children(&mut cursor) {
            value.push_str(&python_static_string(child, source)?);
        }
        return Some(value);
    }
    if node.kind() != "string" {
        return None;
    }
    let raw = node_text(node, source)?.trim();
    let quote = raw.find(['\'', '"'])?;
    if raw[..quote].bytes().any(|byte| matches!(byte, b'b' | b'B' | b'f' | b'F')) {
        return None;
    }
    let delimiter = if raw[quote..].starts_with("\"\"\"") || raw[quote..].starts_with("'''") {
        &raw[quote..quote + 3]
    } else {
        &raw[quote..=quote]
    };
    let content = raw[quote + delimiter.len()..].strip_suffix(delimiter)?;
    if content.contains('\\') {
        return None;
    }
    Some(content.to_owned())
}

fn node_text<'source>(node: Node<'_>, source: &'source str) -> Option<&'source str> {
    source.get(node.byte_range())
}

struct RustVisitor<'syntax> {
    constants: &'syntax Constants<'syntax>,
    arrays: BTreeMap<usize, String>,
    builders: BTreeMap<proc_macro2::LineColumn, BuilderCommand>,
    constructors: Vec<(usize, String)>,
    defaults: BTreeMap<usize, String>,
}

impl<'syntax> RustVisitor<'syntax> {
    const fn new(constants: &'syntax Constants<'syntax>) -> Self {
        Self {
            constants,
            arrays: BTreeMap::new(),
            builders: BTreeMap::new(),
            constructors: Vec::new(),
            defaults: BTreeMap::new(),
        }
    }

    fn finish(self) -> Vec<(usize, String)> {
        let mut kinds: Vec<_> = self.arrays.into_iter().collect();
        kinds.extend(self.constructors);
        kinds.extend(self.defaults);
        for candidate in self.builders.into_values() {
            if let Some(kind) = kind_after_flag(&candidate.arguments) {
                kinds.push((candidate.root_span.start().line, kind));
            }
        }
        kinds
    }
}

impl<'ast> Visit<'ast> for RustVisitor<'_> {
    fn visit_expr_call(&mut self, call: &'ast ExprCall) {
        if let Some(kind) = timing_task_kind_constructor(self.constants, call) {
            self.constructors.push((call.span().start().line, kind));
        }
        syn::visit::visit_expr_call(self, call);
    }

    fn visit_expr_array(&mut self, array: &'ast ExprArray) {
        record_array_kind(self.constants, &mut self.arrays, array);
        visit_array_children(self, array);
    }

    fn visit_expr_method_call(&mut self, method: &'ast ExprMethodCall) {
        record_builder_from_method(self.constants, &mut self.builders, method);
        visit_method_children(self, method);
    }

    fn visit_field(&mut self, field: &'ast Field) {
        if let Some(kind) = clap_default(field) {
            self.defaults.insert(field.span().start().line, kind);
        }
        syn::visit::visit_field(self, field);
    }

}

fn timing_task_kind_constructor(constants: &Constants<'_>, call: &ExprCall) -> Option<String> {
    let Expr::Path(function) = call.func.as_ref() else {
        return None;
    };
    let segments: Vec<_> = function.path.segments.iter().collect();
    let [.., kind, constructor] = segments.as_slice() else {
        return None;
    };
    if kind.ident != "TimingTaskKind" || constructor.ident != "new" || call.args.len() != 1 {
        return None;
    }
    match constants.argument(call.args.first()?) {
        Argument::Static(value) => Some(value),
        Argument::Dynamic => None,
    }
}

fn record_array_kind(
    constants: &Constants<'_>,
    kinds: &mut BTreeMap<usize, String>,
    array: &ExprArray,
) {
    let arguments = array_arguments(constants, array);
    let Some(kind) = kind_after_flag(&arguments) else {
        return;
    };
    let line = array.span().start().line;
    kinds.insert(line, kind);
}

fn visit_array_children(visitor: &mut RustVisitor<'_>, array: &ExprArray) {
    syn::visit::visit_expr_array(visitor, array);
}

fn visit_method_children(visitor: &mut RustVisitor<'_>, method: &ExprMethodCall) {
    syn::visit::visit_expr_method_call(visitor, method);
}

fn kind_after_flag(arguments: &[Argument]) -> Option<String> {
    arguments.windows(2).find_map(|pair| match pair {
        [Argument::Static(flag), Argument::Static(kind)] if flag == TIMING_FLAG => Some(kind.clone()),
        _ => None,
    })
}

fn clap_default(field: &Field) -> Option<String> {
    let inferred_long = field.ident.as_ref().is_some_and(|ident| ident == "timing_task_kind");
    field.attrs.iter().find_map(|attribute| parse_clap_default(attribute, inferred_long))
}

fn parse_clap_default(attribute: &Attribute, inferred_long: bool) -> Option<String> {
    if !attribute.path().is_ident("arg") {
        return None;
    }
    let mut timing_long = inferred_long;
    let mut default = None;
    let _ = attribute.parse_nested_meta(|meta| {
        if meta.path.is_ident("long") {
            // Bare `long` keeps the field-name inference. An explicit long name
            // is timing-owned only when it is exactly `--timing-task-kind`.
            if let Ok(value) = meta.value() {
                timing_long = value
                    .parse::<LitStr>()
                    .ok()
                    .is_some_and(|literal| literal.value() == "timing-task-kind");
            }
        } else if meta.path.is_ident("default_value") {
            default = meta.value()?.parse::<LitStr>().ok().map(|value| value.value());
        }
        Ok(())
    });
    if timing_long { default } else { None }
}

fn missing_message(kind: &str) -> String {
    format!("missing TIMING_TASK_KINDS_ALLOWED entry for {kind}")
}

fn dynamic_message() -> String {
    "timing task kind must resolve to a static allow-listed literal".to_owned()
}

fn number(path: &str, line: usize) -> Result<u32, LintError> {
    u32::try_from(line).map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))
}

fn has_lowercase_extension(path: &str, expected: &str) -> bool {
    Path::new(path)
        .extension()
        .is_some_and(|extension| extension == expected)
}
