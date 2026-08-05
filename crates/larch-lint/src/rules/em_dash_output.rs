//! Reject em dashes in larch-authored output literals.
//!
//! This rule owns the Markdown template, Rust output macro, and production
//! Python output-sink scopes. Python uses the workspace tree-sitter grammar so
//! imported `logging_util` sinks and `BreadcrumbWriter` aliases retain the
//! former compatibility rule's ownership without keeping a second runner.

use std::{collections::BTreeSet, sync::LazyLock};

use proc_macro2::{TokenStream, TokenTree};
use regex::Regex;
use syn::visit::{self, Visit};
use tree_sitter::Node;

use crate::{
    Finding, LintError, PathSelector, Repository, Rule, RuleMetadata, RuleOutput,
    suppression,
    syntax::{FenceState, MarkdownDocument, is_production_python_path, parse_python},
};

use super::rust_scan;

const NAME: &str = "em-dash-output";
const DESCRIPTION: &str = "Reject em dashes in Markdown templates and output sinks";
const EM_DASH: char = '\u{2014}';
const SUPPRESSION_TOKEN: &str = "lint-em-dash-output";
const RUST_OUTPUT_MACROS: [&str; 4] = ["print", "println", "eprint", "eprintln"];
const PYTHON_NAME_SINKS: [&str; 10] = [
    "print",
    "_emit",
    "_diag",
    "_err",
    "_core_diagnostic",
    "emit",
    "emit_kv",
    "diagnostic",
    "_plain_diagnostic",
    "_emit_kv",
];
const LOGGING_UTIL_SINKS: [&str; 3] = ["emit", "emit_kv", "diagnostic"];

static PRINT_TEMPLATE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\b(?:P|p)rint:?\s+`([^`\n]*)`").expect("print template expression is valid")
});

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/em-dash-output.toml",
);

#[derive(Debug)]
pub struct EmDashOutputRule;

pub static RULE: EmDashOutputRule = EmDashOutputRule;

impl Rule for EmDashOutputRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let mut findings = Vec::new();
        let markdown = PathSelector::new(&["skills/**/*.md", "agents/**/*.md"], &[])?;
        for path in markdown.select(repository) {
            findings.extend(check_markdown(path.as_str(), &repository.read_utf8(path)?)?);
        }
        let rust = PathSelector::new(&["**/*.rs"], &[])?;
        for path in rust.select(repository) {
            findings.extend(check_rust(path.as_str(), &repository.read_utf8(path)?)?);
        }
        for path in repository.paths() {
            if is_production_python_path(path.as_str()) {
                findings.extend(check_python(path.as_str(), &repository.read_utf8(path)?)?);
            }
        }
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

fn check_markdown(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    let mut findings = Vec::new();
    for line in MarkdownDocument::new(source).lines() {
        let text = line.text();
        if line.fence_state() != FenceState::Outside || text.trim_start().starts_with('>') {
            continue;
        }
        let suppressed = suppression::reason(text, SUPPRESSION_TOKEN)?.is_some();
        if suppressed {
            continue;
        }
        let number = u32::try_from(line.number())
            .map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))?;
        if PRINT_TEMPLATE
            .captures_iter(text)
            .any(|captures| captures.get(1).is_some_and(|content| content.as_str().contains(EM_DASH)))
        {
            findings.push(Finding::new(path, number, "em dash in markdown print literal"));
        }
        if text.trim_start().starts_with('⏩') && text.contains(EM_DASH) {
            findings.push(Finding::new(path, number, "em dash in markdown status line"));
        }
    }
    Ok(findings)
}

fn check_rust(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    rust_scan::findings(path, source, SUPPRESSION_TOKEN, |file| {
        let mut collector = RustOutputCollector::default();
        collector.visit_file(file);
        collector
            .lines
            .into_iter()
            .map(|line| (line, "em dash in Rust output literal".to_owned()))
            .collect()
    })
}

fn check_python(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    // The retired Python rule validated every in-scope suppression marker,
    // including a malformed marker that happens not to share a line with an
    // em dash. Preserve that fail-closed contract before collecting calls.
    for line in source.lines() {
        let _ = suppression::reason(line, SUPPRESSION_TOKEN)?;
    }
    let tree = parse_python(source)?;
    let mut symbols = PythonSymbols::default();
    collect_python_imports(tree.root_node(), source, &mut symbols);
    propagate_python_assignments(tree.root_node(), source, &mut symbols);

    let mut lines = BTreeSet::new();
    collect_python_output_calls(tree.root_node(), source, &symbols, &mut lines);
    lines
        .into_iter()
        .map(|line| {
            if suppression::reason(source.lines().nth(line.saturating_sub(1)).unwrap_or(""), SUPPRESSION_TOKEN)?.is_some() {
                return Ok(None);
            }
            let line = u32::try_from(line)
                .map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))?;
            Ok(Some(Finding::new(path, line, "em dash in Python output literal")))
        })
        .filter_map(Result::transpose)
        .collect()
}

#[derive(Debug)]
struct PythonSymbols {
    sink_names: BTreeSet<String>,
    breadcrumb_writer_names: BTreeSet<String>,
    logging_util_names: BTreeSet<String>,
}

impl Default for PythonSymbols {
    fn default() -> Self {
        Self {
            sink_names: PYTHON_NAME_SINKS.into_iter().map(str::to_owned).collect(),
            breadcrumb_writer_names: ["BreadcrumbWriter", "breadcrumb_writer", "writer"]
                .into_iter()
                .map(str::to_owned)
                .collect(),
            logging_util_names: ["logging_util"].into_iter().map(str::to_owned).collect(),
        }
    }
}

fn collect_python_imports(node: Node<'_>, source: &str, symbols: &mut PythonSymbols) {
    match node.kind() {
        "import_statement" => {
            for item in normalized_import_items(node_text(node, source).strip_prefix("import ").unwrap_or("")) {
                let words: Vec<_> = item.split_whitespace().collect();
                if words.first() == Some(&"larch.core.logging_util") {
                    let name = match words.as_slice() {
                        [_, "as", alias] => *alias,
                        _ => "logging_util",
                    };
                    symbols.logging_util_names.insert(name.to_owned());
                }
            }
        }
        "import_from_statement" => record_python_from_import(node_text(node, source), symbols),
        _ => {
            let mut cursor = node.walk();
            for child in node.named_children(&mut cursor) {
                collect_python_imports(child, source, symbols);
            }
        }
    }
}

fn normalized_import_items(items: &str) -> impl Iterator<Item = &str> {
    items.split(',').map(str::trim)
}

fn record_python_from_import(statement: &str, symbols: &mut PythonSymbols) {
    let normalized = statement.replace(['\n', '(', ')'], " ");
    let normalized = normalized.split_whitespace().collect::<Vec<_>>().join(" ");
    let Some((module, names)) = normalized
        .strip_prefix("from ")
        .and_then(|value| value.split_once(" import "))
    else {
        return;
    };
    for item in normalized_import_items(names) {
        let words: Vec<_> = item.split_whitespace().collect();
        let Some(imported) = words.first().copied() else {
            continue;
        };
        let local = match words.as_slice() {
            [_, "as", alias] => *alias,
            _ => imported,
        };
        match module {
            "larch.core" if imported == "logging_util" => {
                symbols.logging_util_names.insert(local.to_owned());
            }
            "larch.core.logging_util" if LOGGING_UTIL_SINKS.contains(&imported) => {
                symbols.sink_names.insert(local.to_owned());
            }
            "larch.core.logging_util" if imported == "BreadcrumbWriter" => {
                symbols.breadcrumb_writer_names.insert(local.to_owned());
            }
            _ => {}
        }
    }
}

fn propagate_python_assignments(node: Node<'_>, source: &str, symbols: &mut PythonSymbols) {
    let mut assignments = Vec::new();
    collect_nodes(node, "assignment", &mut assignments);
    collect_nodes(node, "augmented_assignment", &mut assignments);
    let mut changed = true;
    while changed {
        changed = false;
        for assignment in &assignments {
            let Some(left) = assignment.child_by_field_name("left") else {
                continue;
            };
            let Some(right) = assignment.child_by_field_name("right") else {
                continue;
            };
            let targets = python_assignment_targets(left, source);
            if targets.is_empty() {
                continue;
            }
            if python_breadcrumb_constructor(right, source, symbols)
                || symbols
                    .breadcrumb_writer_names
                    .contains(node_text(right, source).trim())
            {
                changed |= extend_names(&mut symbols.breadcrumb_writer_names, targets.iter());
            } else if python_logging_sink_reference(right, source, symbols)
                || symbols.sink_names.contains(node_text(right, source).trim())
            {
                changed |= extend_names(&mut symbols.sink_names, targets.iter());
            }
        }
    }
}

fn collect_nodes<'tree>(node: Node<'tree>, kind: &str, nodes: &mut Vec<Node<'tree>>) {
    if node.kind() == kind {
        nodes.push(node);
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_nodes(child, kind, nodes);
    }
}

fn python_assignment_targets(node: Node<'_>, source: &str) -> Vec<String> {
    if node.kind() == "identifier" {
        return vec![node_text(node, source).trim().to_owned()];
    }
    let mut targets = Vec::new();
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        targets.extend(python_assignment_targets(child, source));
    }
    targets
}

fn extend_names<'a>(names: &mut BTreeSet<String>, additions: impl Iterator<Item = &'a String>) -> bool {
    let mut changed = false;
    for addition in additions {
        changed |= names.insert(addition.clone());
    }
    changed
}

fn collect_python_output_calls(
    node: Node<'_>,
    source: &str,
    symbols: &PythonSymbols,
    lines: &mut BTreeSet<usize>,
) {
    if node.kind() == "call" && python_call_is_output_sink(node, source, symbols) {
        collect_call_literal_lines(node, source, lines);
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_python_output_calls(child, source, symbols, lines);
    }
}

fn python_call_is_output_sink(call: Node<'_>, source: &str, symbols: &PythonSymbols) -> bool {
    let Some(function) = call.child_by_field_name("function") else {
        return false;
    };
    let text = node_text(function, source).trim();
    if symbols.sink_names.contains(text) {
        return true;
    }
    if matches!(text, "sys.stdout.write" | "sys.stderr.write") {
        return true;
    }
    let Some((receiver, method)) = text.rsplit_once('.') else {
        return false;
    };
    (method == "emit" && python_breadcrumb_receiver(receiver, symbols))
        || (LOGGING_UTIL_SINKS.contains(&method) && symbols.logging_util_names.contains(receiver))
}

fn python_logging_sink_reference(node: Node<'_>, source: &str, symbols: &PythonSymbols) -> bool {
    let text = node_text(node, source).trim();
    text.rsplit_once('.').is_some_and(|(module, name)| {
        symbols.logging_util_names.contains(module) && LOGGING_UTIL_SINKS.contains(&name)
    })
}

fn python_breadcrumb_constructor(node: Node<'_>, source: &str, symbols: &PythonSymbols) -> bool {
    if node.kind() != "call" {
        return false;
    }
    let Some(function) = node.child_by_field_name("function") else {
        return false;
    };
    python_breadcrumb_constructor_text(node_text(function, source).trim(), symbols)
}

fn python_breadcrumb_constructor_text(text: &str, symbols: &PythonSymbols) -> bool {
    symbols.breadcrumb_writer_names.contains(text)
        || text.rsplit_once('.').is_some_and(|(module, name)| {
            name == "BreadcrumbWriter" && symbols.logging_util_names.contains(module)
        })
}

fn python_breadcrumb_receiver(receiver: &str, symbols: &PythonSymbols) -> bool {
    if symbols.breadcrumb_writer_names.contains(receiver) {
        return true;
    }
    if let Some(constructor) = receiver.strip_suffix(')') {
        let function = constructor.split_once('(').map_or(constructor, |(function, _)| function);
        return python_breadcrumb_constructor_text(function.trim(), symbols);
    }
    false
}

fn collect_call_literal_lines(call: Node<'_>, source: &str, lines: &mut BTreeSet<usize>) {
    let Some(arguments) = call.child_by_field_name("arguments") else {
        return;
    };
    let mut cursor = arguments.walk();
    for argument in arguments.named_children(&mut cursor) {
        let value = if argument.kind() == "keyword_argument" {
            argument.child_by_field_name("value")
        } else {
            Some(argument)
        };
        let Some(value) = value else {
            continue;
        };
        if python_literal_contains_em_dash(value, source) {
            lines.insert(value.start_position().row + 1);
        }
    }
}

fn python_literal_contains_em_dash(node: Node<'_>, source: &str) -> bool {
    if node.kind() == "string" {
        return node_text(node, source).contains(EM_DASH);
    }
    if node.kind() == "concatenated_string" {
        let mut cursor = node.walk();
        return node
            .named_children(&mut cursor)
            .any(|child| python_literal_contains_em_dash(child, source));
    }
    false
}

fn node_text<'source>(node: Node<'_>, source: &'source str) -> &'source str {
    source.get(node.byte_range()).unwrap_or("")
}

#[derive(Default)]
struct RustOutputCollector {
    lines: Vec<usize>,
}

impl RustOutputCollector {
    fn check_macro(&mut self, mac: &syn::Macro) {
        if !macro_name(mac).is_some_and(|name| RUST_OUTPUT_MACROS.contains(&name.as_str())) {
            return;
        }
        self.collect_literals(mac.tokens.clone());
    }

    fn collect_literals(&mut self, tokens: TokenStream) {
        for token in tokens {
            match token {
                TokenTree::Literal(literal) => {
                    if let syn::Lit::Str(text) = syn::Lit::new(literal)
                        && text.value().contains(EM_DASH)
                    {
                        self.lines.push(text.span().start().line);
                    }
                }
                TokenTree::Group(group) => self.collect_literals(group.stream()),
                TokenTree::Ident(_) | TokenTree::Punct(_) => {}
            }
        }
    }
}

impl<'ast> Visit<'ast> for RustOutputCollector {
    fn visit_expr_macro(&mut self, node: &'ast syn::ExprMacro) {
        self.check_macro(&node.mac);
        visit::visit_expr_macro(self, node);
    }

    fn visit_stmt_macro(&mut self, node: &'ast syn::StmtMacro) {
        self.check_macro(&node.mac);
        visit::visit_stmt_macro(self, node);
    }
}

fn macro_name(mac: &syn::Macro) -> Option<String> {
    mac.path.segments.last().map(|segment| segment.ident.to_string())
}

#[cfg(test)]
mod tests {
    use super::{check_markdown, check_rust};

    #[test]
    fn flags_markdown_templates_but_not_quotes_or_fences() {
        let source = "> Print: `quoted \u{2014} template`\n```\nPrint: `fenced \u{2014} template`\n```\nPrint: `bad \u{2014} template`\n⏩ status \u{2014} bad\n";
        let findings = check_markdown("fixture.md", source).expect("scan");
        assert_eq!(findings.len(), 2);
        assert_eq!(findings[0].to_string(), "fixture.md:5: em dash in markdown print literal");
        assert_eq!(findings[1].to_string(), "fixture.md:6: em dash in markdown status line");
    }

    #[test]
    fn flags_all_rust_output_macros() {
        let source = "fn emit() {\n print!(\"bad \u{2014} print\");\n println!(\"bad \u{2014} println\");\n eprint!(\"bad \u{2014} eprint\");\n eprintln!(\"bad \u{2014} eprintln\");\n let _ = format!(\"allowed \u{2014} value\");\n}";
        let findings = check_rust("fixture.rs", source).expect("scan");
        assert_eq!(findings.len(), 4);
        assert!(findings.iter().all(|finding| finding.to_string().contains("em dash in Rust output literal")));
    }

    #[test]
    fn accepts_reasoned_suppressions_and_rejects_empty_ones() {
        assert!(check_rust(
            "fixture.rs",
            "fn emit() { println!(\"bad \u{2014} text\"); // lint-em-dash-output: ok legacy fixture\n}"
        )
        .expect("scan")
        .is_empty());
        assert!(check_markdown(
            "fixture.md",
            "Print: `bad \u{2014} template` <!-- lint-em-dash-output: ok -->"
        )
        .is_err());
    }
}

crate::register_rule!(METADATA, RULE);
