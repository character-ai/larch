//! Reject em dashes in larch-authored Markdown templates and Rust output sinks.
//!
//! The Python compatibility rule retains its Python AST scope. This rule owns
//! the Markdown template scope and Rust output macro scope through the shared
//! Markdown and Rust syntax abstractions.

use std::sync::LazyLock;

use proc_macro2::{TokenStream, TokenTree};
use regex::Regex;
use syn::visit::{self, Visit};

use crate::{
    Finding, LintError, PathSelector, Repository, Rule, RuleMetadata, RuleOutput,
    suppression,
    syntax::{FenceState, MarkdownDocument},
};

use super::rust_scan;

const NAME: &str = "em-dash-output";
const DESCRIPTION: &str = "Reject em dashes in Markdown templates and Rust output sinks";
const EM_DASH: char = '\u{2014}';
const SUPPRESSION_TOKEN: &str = "lint-em-dash-output";
const RUST_OUTPUT_MACROS: [&str; 4] = ["print", "println", "eprint", "eprintln"];

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
