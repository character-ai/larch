//! Require heading-regex matching over Markdown lines to consult fence state.
//!
//! # Crate survey (issue #7621)
//!
//! | Need | Candidates | Selection |
//! |---|---|---|
//! | Rust syntax | workspace `syn`, `ra_ap_syntax` | Use `syn` visitors, as the existing Rust rules do. The rule needs only construction, alias, loop, and call shapes. |
//! | Markdown structure | workspace `pulldown-cmark`, `comrak` | Reuse `MarkdownDocument::lines` and its `FenceState`; `CommonMark` events alone do not retain line membership for diagnostics. |
//! | Heading patterns | workspace `regex`, handwritten scanner | Use `regex` for the stable heading-pattern predicate. Custom analysis joins that predicate to the shared fence-state contract. |
//!
//! The Rust corpus starts with zero debt. This rule therefore has no baseline.

use std::collections::BTreeSet;

use regex::Regex;
use syn::{
    Expr, ExprCall, ExprForLoop, ExprIf, ExprMethodCall, ItemFn, ItemUse, Local, Pat, Stmt,
    UseTree,
    visit::{self, Visit},
};

use crate::{
    Finding, LintError, PathSelector, RepoPath, Repository, Rule, RuleMetadata, RuleOutput,
    suppression::reason,
    syntax::RustSyntax,
};

const NAME: &str = "markdown-heading-fence-state";
const DESCRIPTION: &str = "Require fence-aware Markdown heading regex parsing";
const SUPPRESSION_TOKEN: &str = "lint-markdown-heading-fence-state";
const MATCH_METHODS: &[&str] = &[
    "is_match",
    "find",
    "find_iter",
    "captures",
    "captures_iter",
    "shortest_match",
    "split",
    "splitn",
    "replace",
    "replace_all",
];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/markdown-heading-fence-state.toml",
);

#[derive(Debug)]
pub struct MarkdownHeadingFenceStateRule;

pub static RULE: MarkdownHeadingFenceStateRule = MarkdownHeadingFenceStateRule;

impl Rule for MarkdownHeadingFenceStateRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let selector = PathSelector::new(&["crates/**/*.rs"], &[])?;
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
    let bindings = Bindings::collect(syntax.file());
    let mut visitor = LoopVisitor {
        bindings: &bindings,
        lines: BTreeSet::new(),
    };
    visitor.visit_file(syntax.file());
    resolve_findings(path.as_str(), &source, visitor.lines)
}

fn resolve_findings(path: &str, source: &str, lines: BTreeSet<u32>) -> Result<Vec<Finding>, LintError> {
    let source_lines: Vec<&str> = source.lines().collect();
    let mut findings = Vec::new();
    for line in lines {
        let index = usize::try_from(line.saturating_sub(1))
            .map_err(|_| LintError::new(format!("{path}: line number is out of range")))?;
        let text = source_lines
            .get(index)
            .ok_or_else(|| LintError::new(format!("{path}: finding line {line} is outside source")))?;
        if reason(text, SUPPRESSION_TOKEN)?.is_none() {
            findings.push(Finding::new(
                path,
                line,
                "applies a Markdown heading regex to lines without fence-state gating",
            ));
        }
    }
    Ok(findings)
}

#[derive(Default)]
struct Bindings {
    regexes: BTreeSet<String>,
    regex_types: BTreeSet<String>,
    line_iterators: BTreeSet<String>,
    fence_helpers: BTreeSet<String>,
}

impl Bindings {
    fn collect(file: &syn::File) -> Self {
        let mut bindings = Self {
            regex_types: ["Regex".to_owned(), "RegexBuilder".to_owned()]
                .into_iter()
                .collect(),
            ..Self::default()
        };
        let mut visitor = BindingVisitor {
            bindings: &mut bindings,
        };
        visitor.visit_file(file);
        bindings
    }
}

struct BindingVisitor<'bindings> {
    bindings: &'bindings mut Bindings,
}

impl<'ast> Visit<'ast> for BindingVisitor<'_> {
    fn visit_local(&mut self, node: &'ast Local) {
        if let (Some(name), Some(initializer)) = (pattern_name(&node.pat), &node.init) {
            if is_regex_expression(
                &initializer.expr,
                &self.bindings.regexes,
                &self.bindings.regex_types,
            ) {
                self.bindings.regexes.insert(name.clone());
            }
            if is_line_iteration(&initializer.expr, &self.bindings.line_iterators) {
                self.bindings.line_iterators.insert(name);
            }
        }
        visit::visit_local(self, node);
    }

    fn visit_item_fn(&mut self, node: &'ast ItemFn) {
        if function_checks_fence_state(node) {
            self.bindings.fence_helpers.insert(node.sig.ident.to_string());
        }
        if function_constructs_heading_regex(node, &self.bindings.regex_types) {
            self.bindings.regexes.insert(node.sig.ident.to_string());
        }
        visit::visit_item_fn(self, node);
    }

    fn visit_item_use(&mut self, node: &'ast ItemUse) {
        collect_regex_aliases(&node.tree, false, &mut self.bindings.regex_types);
        visit::visit_item_use(self, node);
    }
}

fn pattern_name(pattern: &Pat) -> Option<String> {
    match pattern {
        Pat::Ident(ident) => Some(ident.ident.to_string()),
        Pat::Type(typed) => pattern_name(&typed.pat),
        _ => None,
    }
}

fn is_regex_expression(
    expression: &Expr,
    regexes: &BTreeSet<String>,
    regex_types: &BTreeSet<String>,
) -> bool {
    if heading_regex_construction(expression, regex_types) {
        return true;
    }
    match strip_expression(expression) {
        Expr::Path(path) => path
            .path
            .get_ident()
            .is_some_and(|ident| regexes.contains(&ident.to_string())),
        Expr::Call(call) => expression_path(&call.func)
            .and_then(|path| path.path.get_ident())
            .is_some_and(|ident| regexes.contains(&ident.to_string())),
        _ => false,
    }
}

fn strip_expression(expression: &Expr) -> &Expr {
    match expression {
        Expr::Paren(paren) => strip_expression(&paren.expr),
        Expr::Reference(reference) => strip_expression(&reference.expr),
        Expr::Try(try_expression) => strip_expression(&try_expression.expr),
        Expr::MethodCall(call)
            if matches!(call.method.to_string().as_str(), "unwrap" | "expect" | "clone" | "as_ref") =>
        {
            strip_expression(&call.receiver)
        }
        _ => expression,
    }
}

fn heading_regex_construction(expression: &Expr, regex_types: &BTreeSet<String>) -> bool {
    let Expr::Call(ExprCall { func, args, .. }) = strip_expression(expression) else {
        return false;
    };
    let Some(segment) = expression_path(func).and_then(|path| path.path.segments.last()) else {
        return false;
    };
    segment.ident == "new"
        && expression_path(func)
            .and_then(|path| path.path.segments.iter().rev().nth(1))
            .is_some_and(|type_segment| regex_types.contains(&type_segment.ident.to_string()))
        && args
            .first()
            .and_then(string_literal)
            .is_some_and(|pattern| is_heading_pattern(&pattern))
}

const fn expression_path(expression: &Expr) -> Option<&syn::ExprPath> {
    match expression {
        Expr::Path(path) => Some(path),
        _ => None,
    }
}

fn string_literal(expression: &Expr) -> Option<String> {
    match expression {
        Expr::Lit(literal) => match &literal.lit {
            syn::Lit::Str(value) => Some(value.value()),
            _ => None,
        },
        _ => None,
    }
}

fn is_heading_pattern(pattern: &str) -> bool {
    let expression = r"^(?:\^|\\A)\s*(?:#\{1,6\}|#{1,6})(?:\\s|\[\\s|[ \t])";
    Regex::new(expression)
        .expect("heading-pattern predicate is valid")
        .is_match(pattern)
}

fn is_line_iteration(expression: &Expr, iterators: &BTreeSet<String>) -> bool {
    match strip_expression(expression) {
        Expr::MethodCall(call) if call.method == "lines" => true,
        Expr::MethodCall(call) if matches!(call.method.to_string().as_str(), "enumerate" | "iter") => {
            is_line_iteration(&call.receiver, iterators)
        }
        Expr::Path(path) => path
            .path
            .get_ident()
            .is_some_and(|ident| iterators.contains(&ident.to_string())),
        _ => false,
    }
}

fn collect_regex_aliases(tree: &UseTree, in_regex_module: bool, aliases: &mut BTreeSet<String>) {
    match tree {
        UseTree::Path(path) => collect_regex_aliases(
            &path.tree,
            in_regex_module || path.ident == "regex",
            aliases,
        ),
        UseTree::Name(name) if in_regex_module && matches!(name.ident.to_string().as_str(), "Regex" | "RegexBuilder") => {
            aliases.insert(name.ident.to_string());
        }
        UseTree::Rename(rename)
            if in_regex_module
                && matches!(rename.ident.to_string().as_str(), "Regex" | "RegexBuilder") =>
        {
            aliases.insert(rename.rename.to_string());
        }
        UseTree::Group(group) => {
            for item in &group.items {
                collect_regex_aliases(item, in_regex_module, aliases);
            }
        }
        UseTree::Glob(_) | UseTree::Name(_) | UseTree::Rename(_) => {}
    }
}

fn function_checks_fence_state(function: &ItemFn) -> bool {
    function
        .block
        .stmts
        .last()
        .is_some_and(statement_returns_outside_fence)
}

fn function_constructs_heading_regex(function: &ItemFn, regex_types: &BTreeSet<String>) -> bool {
    let mut visitor = ConstructionVisitor {
        found: false,
        regex_types,
    };
    visitor.visit_block(&function.block);
    visitor.found
}

fn statement_returns_outside_fence(statement: &Stmt) -> bool {
    let expression = match statement {
        Stmt::Expr(Expr::Return(return_expression), _) => return_expression.expr.as_deref(),
        Stmt::Expr(expression, _) => Some(expression),
        Stmt::Local(_) | Stmt::Item(_) | Stmt::Macro(_) => None,
    };
    expression.is_some_and(is_outside_fence_comparison)
}

fn is_outside_fence_comparison(expression: &Expr) -> bool {
    matches!(expression, Expr::Binary(binary) if matches!(binary.op, syn::BinOp::Eq(_))
        && ((is_fence_state_call(&binary.left) && is_outside_state(&binary.right))
            || (is_fence_state_call(&binary.right) && is_outside_state(&binary.left))))
}

struct ConstructionVisitor<'types> {
    found: bool,
    regex_types: &'types BTreeSet<String>,
}

impl<'ast> Visit<'ast> for ConstructionVisitor<'_> {
    fn visit_expr(&mut self, node: &'ast Expr) {
        if heading_regex_construction(node, self.regex_types) {
            self.found = true;
        }
        visit::visit_expr(self, node);
    }
}

struct LoopVisitor<'bindings> {
    bindings: &'bindings Bindings,
    lines: BTreeSet<u32>,
}

impl<'ast> Visit<'ast> for LoopVisitor<'_> {
    fn visit_expr_for_loop(&mut self, node: &'ast ExprForLoop) {
        if is_line_iteration(&node.expr, &self.bindings.line_iterators) {
            let names = pattern_names(&node.pat);
            let mut scanner = BlockScanner {
                bindings: self.bindings,
                line_names: &names,
                findings: &mut self.lines,
            };
            scanner.scan_block(&node.body, false);
        }
        visit::visit_expr_for_loop(self, node);
    }
}

fn pattern_names(pattern: &Pat) -> BTreeSet<String> {
    let mut names = BTreeSet::new();
    collect_pattern_names(pattern, &mut names);
    names
}

fn collect_pattern_names(pattern: &Pat, names: &mut BTreeSet<String>) {
    match pattern {
        Pat::Ident(ident) => {
            names.insert(ident.ident.to_string());
        }
        Pat::Tuple(tuple) => {
            for element in &tuple.elems {
                collect_pattern_names(element, names);
            }
        }
        Pat::Type(typed) => collect_pattern_names(&typed.pat, names),
        _ => {}
    }
}

struct BlockScanner<'bindings, 'names, 'findings> {
    bindings: &'bindings Bindings,
    line_names: &'names BTreeSet<String>,
    findings: &'findings mut BTreeSet<u32>,
}

impl BlockScanner<'_, '_, '_> {
    fn scan_block(&mut self, block: &syn::Block, initially_safe: bool) {
        let mut safe = initially_safe;
        for statement in &block.stmts {
            self.scan_statement(statement, safe);
            if statement_skips_fenced_line(statement, self.line_names, self.bindings) {
                safe = true;
            }
        }
    }

    fn scan_statement(&mut self, statement: &Stmt, safe: bool) {
        match statement {
            Stmt::Expr(expression, _) => self.scan_expression(expression, safe),
            Stmt::Local(local) => {
                if let Some(initializer) = &local.init {
                    self.scan_expression(&initializer.expr, safe);
                }
            }
            Stmt::Item(_) | Stmt::Macro(_) => {}
        }
    }

    fn scan_expression(&mut self, expression: &Expr, safe: bool) {
        if let Expr::If(if_expression) = expression {
            self.scan_if(if_expression, safe);
            return;
        }
        let mut visitor = MatchVisitor {
            bindings: self.bindings,
            line_names: self.line_names,
            safe,
            findings: self.findings,
        };
        visitor.visit_expr(expression);
    }

    fn scan_if(&mut self, expression: &ExprIf, inherited_safe: bool) {
        let guarded = inherited_safe || is_fence_guard(&expression.cond, self.line_names, self.bindings);
        let mut condition = MatchVisitor {
            bindings: self.bindings,
            line_names: self.line_names,
            safe: guarded,
            findings: self.findings,
        };
        condition.visit_expr(&expression.cond);
        self.scan_block(&expression.then_branch, guarded);
        if let Some((_, otherwise)) = &expression.else_branch {
            self.scan_expression(otherwise, inherited_safe);
        }
    }
}

struct MatchVisitor<'bindings, 'names, 'findings> {
    bindings: &'bindings Bindings,
    line_names: &'names BTreeSet<String>,
    safe: bool,
    findings: &'findings mut BTreeSet<u32>,
}

impl<'ast> Visit<'ast> for MatchVisitor<'_, '_, '_> {
    fn visit_expr_method_call(&mut self, node: &'ast ExprMethodCall) {
        if !self.safe
            && MATCH_METHODS.contains(&node.method.to_string().as_str())
            && is_regex_expression(
                &node.receiver,
                &self.bindings.regexes,
                &self.bindings.regex_types,
            )
            && node.args.first().is_some_and(|argument| is_line_value(argument, self.line_names))
        {
            self.findings.insert(line_number(node.method.span()));
        }
        visit::visit_expr_method_call(self, node);
    }
}

fn is_line_value(expression: &Expr, names: &BTreeSet<String>) -> bool {
    match strip_expression(expression) {
        Expr::Path(path) => path
            .path
            .get_ident()
            .is_some_and(|ident| names.contains(&ident.to_string())),
        Expr::MethodCall(call) if call.method == "text" => is_line_value(&call.receiver, names),
        _ => false,
    }
}

fn is_fence_guard(expression: &Expr, names: &BTreeSet<String>, bindings: &Bindings) -> bool {
    match expression {
        Expr::Binary(binary) if matches!(binary.op, syn::BinOp::And(_)) => {
            is_fence_guard(&binary.left, names, bindings) || is_fence_guard(&binary.right, names, bindings)
        }
        Expr::Binary(binary) if matches!(binary.op, syn::BinOp::Eq(_)) => {
            (is_fence_state(&binary.left, names) && is_outside_state(&binary.right))
                || (is_fence_state(&binary.right, names) && is_outside_state(&binary.left))
        }
        Expr::Call(call) => is_fence_helper_call(call, names, bindings),
        Expr::Paren(paren) => is_fence_guard(&paren.expr, names, bindings),
        _ => false,
    }
}

fn statement_skips_fenced_line(statement: &Stmt, names: &BTreeSet<String>, bindings: &Bindings) -> bool {
    let Stmt::Expr(Expr::If(if_expression), _) = statement else {
        return false;
    };
    contains_continue(&if_expression.then_branch)
        && is_fenced_condition(&if_expression.cond, names, bindings)
}

fn contains_continue(block: &syn::Block) -> bool {
    block
        .stmts
        .iter()
        .any(|statement| matches!(statement, Stmt::Expr(Expr::Continue(_), _)))
}

fn is_fenced_condition(expression: &Expr, names: &BTreeSet<String>, bindings: &Bindings) -> bool {
    match expression {
        Expr::Binary(binary) if matches!(binary.op, syn::BinOp::Ne(_)) => {
            (is_fence_state(&binary.left, names) && is_outside_state(&binary.right))
                || (is_fence_state(&binary.right, names) && is_outside_state(&binary.left))
        }
        Expr::Unary(unary) if matches!(unary.op, syn::UnOp::Not(_)) => {
            is_fence_guard(&unary.expr, names, bindings)
        }
        Expr::Paren(paren) => is_fenced_condition(&paren.expr, names, bindings),
        _ => false,
    }
}

fn is_fence_helper_call(call: &ExprCall, names: &BTreeSet<String>, bindings: &Bindings) -> bool {
    expression_path(&call.func)
        .and_then(|path| path.path.get_ident())
        .is_some_and(|ident| bindings.fence_helpers.contains(&ident.to_string()))
        && call.args.first().is_some_and(|argument| is_line_value(argument, names))
}

fn is_fence_state(expression: &Expr, names: &BTreeSet<String>) -> bool {
    is_fence_state_call(expression)
        && matches!(expression, Expr::MethodCall(call) if is_line_value(&call.receiver, names))
}

fn is_fence_state_call(expression: &Expr) -> bool {
    matches!(expression, Expr::MethodCall(call) if call.method == "fence_state")
}

fn is_outside_state(expression: &Expr) -> bool {
    matches!(expression, Expr::Path(path) if path.path.segments.last().is_some_and(|segment| segment.ident == "Outside"))
}

fn line_number(span: proc_macro2::Span) -> u32 {
    u32::try_from(span.start().line).unwrap_or(u32::MAX)
}
