//! Require explicit variant routing instead of boolean status shortcuts.
//!
//! # Crate survey (issue #7624)
//!
//! | Need | Candidates | Selection |
//! |---|---|---|
//! | Rust syntax and traversal | workspace `syn`, compiler/Clippy | Use the workspace's maintained `syn` parser and visitors. Compiler and Clippy can verify types but cannot express larch's same-function terminal-routing policy. |
//! | Data flow | `rust-analyzer` internals, custom analysis | Do not add a compiler-internal dependency for this lexical, same-function policy. Custom code only relates explicit variants to boolean shortcuts in the same function. |
//! | Baseline | serialized debt ledger | No baseline is needed: the Rust corpus starts clean and this rule runs in the existing Rust CI gate. |

use std::collections::BTreeSet;

use proc_macro2::Span;
use syn::{
    BinOp, Expr, ExprBinary, ExprCall, ExprLet, ExprMatch, ExprMethodCall, Lit, Pat,
    parse::{Parse, ParseStream},
    spanned::Spanned,
    visit::{self, Visit},
    Macro, Token,
};

use crate::{
    Finding, LintError, PathSelector, RepoPath, Repository, Rule, RuleMetadata, RuleOutput,
    suppression::reason as suppression_reason,
    syntax::RustSyntax,
};

const NAME: &str = "status-routing";
const DESCRIPTION: &str =
    "Require explicit Option, Result, and status-enum variant routing instead of boolean shortcuts";
const SUPPRESSION_TOKEN: &str = "lint-status-routing";
const RUST_SOURCES: &[&str] = &["crates/**/src/**/*.rs"];
const STATUS_SUFFIXES: &[&str] = &["status", "verdict", "result", "outcome"];
const BOOLEAN_SHORTCUTS: &[&str] = &[
    "is_empty",
    "is_err",
    "is_none",
    "is_ok",
    "is_some",
];
const VIEW_ADAPTERS: &[&str] = &["as_deref", "as_deref_mut", "as_mut", "as_ref"];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/status-routing.toml",
);

#[derive(Debug)]
pub struct StatusRoutingRule;

pub static RULE: StatusRoutingRule = StatusRoutingRule;

impl Rule for StatusRoutingRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let selector = PathSelector::new(RUST_SOURCES, &[])?;
        let mut findings = Vec::new();
        for path in selector.select(repository) {
            findings.extend(check_rust_file(repository, path)?);
        }
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

fn check_rust_file(repository: &Repository, path: &RepoPath) -> Result<Vec<Finding>, LintError> {
    let source = repository.read_utf8(path)?;
    let syntax = RustSyntax::parse(path.as_str(), &source)?;
    let mut functions = FunctionVisitor::default();
    functions.visit_file(syntax.file());

    let mut findings = Vec::new();
    for analysis in functions.analyses {
        for shortcut in analysis.shortcuts {
            if !analysis.evidenced.contains(&shortcut.candidate) {
                continue;
            }
            let line = span_line(path.as_str(), shortcut.span)?;
            if suppression_reason(source_line(&source, line)?, SUPPRESSION_TOKEN)?.is_some() {
                continue;
            }
            findings.push(Finding::new(
                path.as_str(),
                line,
                format!(
                    "boolean shortcut {} on routed {}; use an explicit variant pattern",
                    shortcut.adapter, shortcut.candidate.0
                ),
            ));
        }
    }
    Ok(findings)
}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
struct Candidate(String);

struct Shortcut {
    candidate: Candidate,
    adapter: &'static str,
    span: Span,
}

#[derive(Default)]
struct FunctionVisitor {
    analyses: Vec<FunctionAnalysis>,
}

struct FunctionAnalysis {
    evidenced: BTreeSet<Candidate>,
    shortcuts: Vec<Shortcut>,
}

impl<'ast> Visit<'ast> for FunctionVisitor {
    fn visit_item_fn(&mut self, node: &'ast syn::ItemFn) {
        self.analyze_block(&node.block);
        visit::visit_item_fn(self, node);
    }

    fn visit_impl_item_fn(&mut self, node: &'ast syn::ImplItemFn) {
        self.analyze_block(&node.block);
        visit::visit_impl_item_fn(self, node);
    }

    fn visit_trait_item_fn(&mut self, node: &'ast syn::TraitItemFn) {
        if let Some(block) = &node.default {
            self.analyze_block(block);
        }
        visit::visit_trait_item_fn(self, node);
    }
}

impl FunctionVisitor {
    fn analyze_block(&mut self, block: &syn::Block) {
        let mut evidence = ScopeEvidence::default();
        evidence.visit_block(block);
        let mut shortcuts = ScopeShortcuts::default();
        shortcuts.visit_block(block);
        self.analyses.push(FunctionAnalysis {
            evidenced: evidence.candidates,
            shortcuts: shortcuts.shortcuts,
        });
    }
}

#[derive(Default)]
struct ScopeEvidence {
    candidates: BTreeSet<Candidate>,
}

impl<'ast> Visit<'ast> for ScopeEvidence {
    fn visit_item_fn(&mut self, _node: &'ast syn::ItemFn) {}

    fn visit_impl_item_fn(&mut self, _node: &'ast syn::ImplItemFn) {}

    fn visit_trait_item_fn(&mut self, _node: &'ast syn::TraitItemFn) {}

    fn visit_expr_closure(&mut self, _node: &'ast syn::ExprClosure) {}

    fn visit_expr_binary(&mut self, node: &'ast ExprBinary) {
        if is_equality(&node.op) {
            self.record_comparison(&node.left, &node.right);
            self.record_comparison(&node.right, &node.left);
        }
        visit::visit_expr_binary(self, node);
    }

    fn visit_expr_match(&mut self, node: &'ast ExprMatch) {
        if let Some(candidate) = status_candidate(&node.expr)
            && node.arms.iter().any(|arm| explicit_variant_pattern(&arm.pat))
        {
            let _ = self.candidates.insert(candidate);
        }
        visit::visit_expr_match(self, node);
    }

    fn visit_expr_let(&mut self, node: &'ast ExprLet) {
        if explicit_variant_pattern(&node.pat)
            && let Some(candidate) = status_candidate(&node.expr)
        {
            let _ = self.candidates.insert(candidate);
        }
        visit::visit_expr_let(self, node);
    }

    fn visit_expr_macro(&mut self, node: &'ast syn::ExprMacro) {
        if let Some(candidate) = matches_macro_candidate(&node.mac) {
            let _ = self.candidates.insert(candidate);
        }
        visit::visit_expr_macro(self, node);
    }
}

impl ScopeEvidence {
    fn record_comparison(&mut self, candidate_expr: &Expr, member_expr: &Expr) {
        if explicit_variant_expr(member_expr)
            && let Some(candidate) = status_candidate(candidate_expr)
        {
            let _ = self.candidates.insert(candidate);
        }
    }
}

#[derive(Default)]
struct ScopeShortcuts {
    shortcuts: Vec<Shortcut>,
}

impl<'ast> Visit<'ast> for ScopeShortcuts {
    fn visit_item_fn(&mut self, _node: &'ast syn::ItemFn) {}

    fn visit_impl_item_fn(&mut self, _node: &'ast syn::ImplItemFn) {}

    fn visit_trait_item_fn(&mut self, _node: &'ast syn::TraitItemFn) {}

    fn visit_expr_closure(&mut self, _node: &'ast syn::ExprClosure) {}

    fn visit_expr_method_call(&mut self, node: &'ast ExprMethodCall) {
        let method = node.method.to_string();
        if BOOLEAN_SHORTCUTS.contains(&method.as_str()) {
            self.record(receiver_candidate(&node.receiver), method.as_str(), node.span());
        }
        visit::visit_expr_method_call(self, node);
    }

    fn visit_expr_call(&mut self, node: &'ast ExprCall) {
        if let Some(adapter) = function_adapter(&node.func)
            && let Some(argument) = node.args.first()
        {
            self.record(receiver_candidate(argument), adapter, node.span());
        }
        visit::visit_expr_call(self, node);
    }
}

impl ScopeShortcuts {
    fn record(&mut self, candidate: Option<Candidate>, adapter: &str, span: Span) {
        let Some(candidate) = candidate else {
            return;
        };
        let adapter = match adapter {
            "bool::from" => "bool::from",
            "Into::<bool>::into" => "Into::<bool>::into",
            "is_empty" => "is_empty",
            "is_err" => "is_err",
            "is_none" => "is_none",
            "is_ok" => "is_ok",
            "is_some" => "is_some",
            _ => return,
        };
        self.shortcuts.push(Shortcut {
            candidate,
            adapter,
            span,
        });
    }
}

const fn is_equality(operator: &BinOp) -> bool {
    matches!(operator, BinOp::Eq(_) | BinOp::Ne(_))
}

fn status_candidate(expr: &Expr) -> Option<Candidate> {
    let segments = candidate_segments(expr)?;
    let name = segments.last()?;
    if STATUS_SUFFIXES
        .iter()
        .any(|suffix| name.to_ascii_lowercase().ends_with(suffix))
    {
        Some(Candidate(segments.join(".")))
    } else {
        None
    }
}

fn receiver_candidate(expr: &Expr) -> Option<Candidate> {
    match expr {
        Expr::MethodCall(call) if VIEW_ADAPTERS.contains(&call.method.to_string().as_str()) => {
            receiver_candidate(&call.receiver)
        }
        Expr::Paren(paren) => receiver_candidate(&paren.expr),
        Expr::Reference(reference) => receiver_candidate(&reference.expr),
        _ => status_candidate(expr),
    }
}

fn candidate_segments(expr: &Expr) -> Option<Vec<String>> {
    match expr {
        Expr::Path(path) if path.qself.is_none() => Some(
            path.path
                .segments
                .iter()
                .map(|segment| segment.ident.to_string())
                .collect(),
        ),
        Expr::Field(field) => {
            let mut segments = candidate_segments(&field.base)?;
            let syn::Member::Named(member) = &field.member else {
                return None;
            };
            segments.push(member.to_string());
            Some(segments)
        }
        Expr::Paren(paren) => candidate_segments(&paren.expr),
        Expr::Reference(reference) => candidate_segments(&reference.expr),
        _ => None,
    }
}

fn explicit_variant_expr(expr: &Expr) -> bool {
    match expr {
        Expr::Lit(literal) => matches!(&literal.lit, Lit::Str(value) if !value.value().is_empty()),
        Expr::Path(path) => path.qself.is_none() && path.path.segments.len() > 1,
        _ => false,
    }
}

fn explicit_variant_pattern(pattern: &Pat) -> bool {
    match pattern {
        Pat::Path(path) => path.qself.is_none() && path.path.segments.len() > 1,
        Pat::TupleStruct(tuple) => !tuple.path.segments.is_empty(),
        Pat::Struct(structure) => !structure.path.segments.is_empty(),
        Pat::Or(or) => or.cases.iter().any(explicit_variant_pattern),
        Pat::Paren(paren) => explicit_variant_pattern(&paren.pat),
        _ => false,
    }
}

struct MatchesArguments {
    expression: Expr,
    _comma: Token![,],
    pattern: Pat,
}

impl Parse for MatchesArguments {
    fn parse(input: ParseStream<'_>) -> syn::Result<Self> {
        Ok(Self {
            expression: input.parse()?,
            _comma: input.parse()?,
            pattern: input.call(Pat::parse_multi_with_leading_vert)?,
        })
    }
}

fn matches_macro_candidate(mac: &Macro) -> Option<Candidate> {
    if mac.path.segments.last()?.ident != "matches" {
        return None;
    }
    let arguments = syn::parse2::<MatchesArguments>(mac.tokens.clone()).ok()?;
    explicit_variant_pattern(&arguments.pattern).then(|| status_candidate(&arguments.expression))?
}

fn function_adapter(expr: &Expr) -> Option<&'static str> {
    let Expr::Path(path) = expr else {
        return None;
    };
    let names: Vec<String> = path
        .path
        .segments
        .iter()
        .map(|segment| segment.ident.to_string())
        .collect();
    if names.as_slice() == ["bool", "from"] {
        Some("bool::from")
    } else if names.last().is_some_and(|name| name == "into")
        && names.iter().any(|name| name == "Into")
    {
        Some("Into::<bool>::into")
    } else if names
        .last()
        .is_some_and(|name| BOOLEAN_SHORTCUTS.contains(&name.as_str()))
    {
        names.last().map(String::as_str).and_then(|name| match name {
            "is_empty" => Some("is_empty"),
            "is_err" => Some("is_err"),
            "is_none" => Some("is_none"),
            "is_ok" => Some("is_ok"),
            "is_some" => Some("is_some"),
            _ => None,
        })
    } else {
        None
    }
}

fn span_line(path: &str, span: Span) -> Result<u32, LintError> {
    u32::try_from(span.start().line)
        .map_err(|_| LintError::new(format!("{path}: source line is out of range")))
}

fn source_line(source: &str, line: u32) -> Result<&str, LintError> {
    let index = usize::try_from(line.saturating_sub(1))
        .map_err(|_| LintError::new("source line is out of range"))?;
    source
        .lines()
        .nth(index)
        .ok_or_else(|| LintError::new(format!("source line {line} is outside the source")))
}
