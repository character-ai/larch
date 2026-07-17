//! Reject hard gates that optional metadata can disable.
//!
//! # Analysis boundary
//!
//! This rule uses `syn`'s maintained expression visitor and a deliberately
//! narrow, lexical data-flow model: a hard-trigger binding becomes available
//! after its declaration and remains available in nested blocks. That is the
//! smallest model that distinguishes a prior hard decision from unrelated
//! metadata validation without pretending to prove arbitrary Rust control
//! flow. The fixture matrix pins every supported adverse and safe shape.

use std::collections::BTreeSet;

use proc_macro2::Span;
use syn::{
    BinOp, Block, Expr, ExprField, ExprIf, ExprLit, ExprPath, ItemFn, Lit, Local, Member, Pat,
    Stmt,
    spanned::Spanned,
    visit::{self, Visit},
};

use crate::{
    Finding, LintError, PathSelector, Repository, Rule, RuleMetadata, RuleOutput,
    suppression::reason,
    syntax::RustSyntax,
};

const NAME: &str = "self-disarmable-gate";
const DESCRIPTION: &str =
    "Reject optional metadata that suppresses a design size or publish hard gate";
const SUPPRESSION_TOKEN: &str = "lint-self-disarmable-gate";
const METADATA_FIELDS: &[&str] = &["diff_added", "mechanical_churn"];
const HARD_TOKENS: &[&str] = &[
    "size_diff",
    "size_trigger",
    "hard_trigger",
    "publish_trigger",
    "reasons",
    "size_diff_raw",
    "size_diff_lines",
    "size_diff_added",
];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/self-disarmable-gate.toml",
);

#[derive(Debug)]
pub struct SelfDisarmableGateRule;

pub static RULE: SelfDisarmableGateRule = SelfDisarmableGateRule;

impl Rule for SelfDisarmableGateRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let selector = PathSelector::new(&["**/*.rs"], &[])?;
        let mut findings = Vec::new();
        for path in selector.select(repository) {
            let source = repository.read_utf8(path)?;
            let syntax = RustSyntax::parse(path.as_str(), &source)?;
            let mut visitor = RuleVisitor::new(path.as_str(), &source);
            visitor.visit_file(syntax.file());
            findings.extend(visitor.finish()?);
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

struct RuleVisitor<'source> {
    path: &'source str,
    source: &'source str,
    findings: Vec<PendingFinding>,
}

impl<'source> RuleVisitor<'source> {
    const fn new(path: &'source str, source: &'source str) -> Self {
        Self {
            path,
            source,
            findings: Vec::new(),
        }
    }

    fn finish(self) -> Result<Vec<Finding>, LintError> {
        let mut findings = Vec::new();
        for pending in self.findings {
            if suppressed(self.path, self.source, pending.line)? {
                continue;
            }
            findings.push(Finding::new(self.path, pending.line, pending.message));
        }
        findings.sort();
        findings.dedup();
        Ok(findings)
    }
}

impl<'ast> Visit<'ast> for RuleVisitor<'_> {
    fn visit_item_fn(&mut self, function: &'ast ItemFn) {
        let mut scanner = FunctionScanner::new(&mut self.findings);
        scanner.scan_function(function);
        visit::visit_item_fn(self, function);
    }
}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
struct PendingFinding {
    line: u32,
    message: String,
}

struct FunctionScanner<'findings> {
    findings: &'findings mut Vec<PendingFinding>,
}

impl<'findings> FunctionScanner<'findings> {
    const fn new(findings: &'findings mut Vec<PendingFinding>) -> Self {
        Self { findings }
    }

    fn scan_function(&mut self, function: &ItemFn) {
        let mut hard_names = function
            .sig
            .inputs
            .iter()
            .filter_map(|argument| match argument {
                syn::FnArg::Typed(typed) => pattern_name(&typed.pat),
                syn::FnArg::Receiver(_) => None,
            })
            .filter(|name| looks_like_hard_trigger(name))
            .collect();
        self.scan_block(&function.block, &mut hard_names);
    }

    fn scan_block(&mut self, block: &Block, hard_names: &mut BTreeSet<String>) {
        for statement in &block.stmts {
            self.scan_statement(statement, hard_names);
        }
    }

    fn scan_statement(&mut self, statement: &Stmt, hard_names: &mut BTreeSet<String>) {
        match statement {
            Stmt::Local(local) => self.scan_local(local, hard_names),
            Stmt::Expr(Expr::If(if_expression), _) => self.scan_if(if_expression, hard_names),
            Stmt::Expr(Expr::Block(block), _) => self.scan_block(&block.block, hard_names),
            _ => {}
        }
    }

    fn scan_local(&mut self, local: &Local, hard_names: &mut BTreeSet<String>) {
        let Some(name) = pattern_name(&local.pat) else {
            return;
        };
        let Some(initializer) = &local.init else {
            return;
        };
        let target_is_hard = hard_names.contains(&name) || looks_like_hard_trigger(&name);
        let value = ungroup(&initializer.expr);
        if let Expr::If(if_expression) = value
            && target_is_hard
            && let Some(field) = metadata_field(&if_expression.cond)
            && if_has_false_branch(if_expression)
        {
            self.record(
                local.span(),
                format!(
                    "author-controlled metadata field {field:?} replaces a hard trigger via conditional expression"
                ),
            );
        }
        if let Expr::Binary(binary) = value
            && target_is_hard
            && matches!(binary.op, BinOp::And(_))
            && negated_metadata_operand(&binary.left).or_else(|| negated_metadata_operand(&binary.right)).is_some()
        {
            let field = negated_metadata_operand(&binary.left)
                .or_else(|| negated_metadata_operand(&binary.right))
                .expect("metadata field checked above");
            self.record(
                local.span(),
                format!("author-controlled metadata field {field:?} AND-negates a hard trigger"),
            );
        }
        if looks_like_hard_trigger(&name) || contains_inline_hard_trigger(value) {
            hard_names.insert(name);
        }
        if let Expr::If(if_expression) = value {
            self.scan_if(if_expression, hard_names);
        }
    }

    fn scan_if(&mut self, if_expression: &ExprIf, hard_names: &mut BTreeSet<String>) {
        if let Some(field) = metadata_field(&if_expression.cond)
            && is_suppression_condition(&if_expression.cond)
        {
            let hard_context = !hard_names.is_empty() || contains_inline_hard_trigger(&if_expression.cond);
            if hard_context
                && (block_returns(&if_expression.then_branch)
                    || block_clears_hard_gate(&if_expression.then_branch, hard_names))
            {
                self.record(
                    if_expression.if_token.span,
                    format!(
                        "author-controlled metadata field {field:?} disarms or short-circuits a hard gate"
                    ),
                );
            }
        }
        let mut branch_hard_names = hard_names.clone();
        self.scan_block(&if_expression.then_branch, &mut branch_hard_names);
        if let Some((_, alternative)) = &if_expression.else_branch {
            self.scan_expression_branch(alternative, hard_names);
        }
    }

    fn scan_expression_branch(&mut self, expression: &Expr, hard_names: &mut BTreeSet<String>) {
        match ungroup(expression) {
            Expr::If(if_expression) => self.scan_if(if_expression, hard_names),
            Expr::Block(block) => self.scan_block(&block.block, hard_names),
            _ => {}
        }
    }

    fn record(&mut self, span: Span, message: String) {
        let line = u32::try_from(span.start().line).unwrap_or(u32::MAX);
        self.findings.push(PendingFinding { line, message });
    }
}

fn pattern_name(pattern: &Pat) -> Option<String> {
    match pattern {
        Pat::Ident(ident) => Some(ident.ident.to_string()),
        Pat::Type(typed) => pattern_name(&typed.pat),
        _ => None,
    }
}

fn expression_name(expression: &Expr) -> Option<String> {
    match ungroup(expression) {
        Expr::Path(ExprPath { path, .. }) if path.segments.len() == 1 => {
            path.segments.first().map(|segment| segment.ident.to_string())
        }
        _ => None,
    }
}

fn ungroup(expression: &Expr) -> &Expr {
    match expression {
        Expr::Group(group) => ungroup(&group.expr),
        Expr::Paren(parenthesized) => ungroup(&parenthesized.expr),
        _ => expression,
    }
}

fn looks_like_hard_trigger(name: &str) -> bool {
    let lowered = name.to_ascii_lowercase();
    HARD_TOKENS.iter().any(|token| lowered.contains(token))
}

fn metadata_field(expression: &Expr) -> Option<&'static str> {
    struct MetadataVisitor {
        field: Option<&'static str>,
    }

    impl<'ast> Visit<'ast> for MetadataVisitor {
        fn visit_expr_field(&mut self, field: &'ast ExprField) {
            if self.field.is_none()
                && let Member::Named(member) = &field.member
            {
                self.field = METADATA_FIELDS
                    .iter()
                    .copied()
                    .find(|candidate| member == *candidate);
            }
            visit::visit_expr_field(self, field);
        }
    }

    let mut visitor = MetadataVisitor { field: None };
    visitor.visit_expr(expression);
    visitor.field
}

fn contains_inline_hard_trigger(expression: &Expr) -> bool {
    struct HardTriggerVisitor {
        found: bool,
    }

    impl<'ast> Visit<'ast> for HardTriggerVisitor {
        fn visit_expr_binary(&mut self, binary: &'ast syn::ExprBinary) {
            if is_comparison_operator(&binary.op)
                && (contains_inline_name(&binary.left) || contains_inline_name(&binary.right))
            {
                self.found = true;
            }
            visit::visit_expr_binary(self, binary);
        }

        fn visit_expr_path(&mut self, path: &'ast ExprPath) {
            if path
                .path
                .segments
                .last()
                .is_some_and(|segment| looks_like_hard_trigger(&segment.ident.to_string()))
            {
                self.found = true;
            }
            visit::visit_expr_path(self, path);
        }
    }

    let mut visitor = HardTriggerVisitor { found: false };
    visitor.visit_expr(expression);
    visitor.found
}

fn contains_inline_name(expression: &Expr) -> bool {
    struct InlineNameVisitor {
        found: bool,
    }

    impl<'ast> Visit<'ast> for InlineNameVisitor {
        fn visit_expr_path(&mut self, path: &'ast ExprPath) {
            if path.path.segments.last().is_some_and(|segment| {
                let name = segment.ident.to_string().to_ascii_lowercase();
                ["diff", "line", "size", "plan"]
                    .iter()
                    .any(|token| name.contains(token))
            }) {
                self.found = true;
            }
            visit::visit_expr_path(self, path);
        }
    }

    let mut visitor = InlineNameVisitor { found: false };
    visitor.visit_expr(expression);
    visitor.found
}

const fn is_comparison_operator(operator: &BinOp) -> bool {
    matches!(
        operator,
        BinOp::Eq(_) | BinOp::Ne(_) | BinOp::Lt(_) | BinOp::Le(_) | BinOp::Gt(_) | BinOp::Ge(_)
    )
}

fn negated_metadata_operand(expression: &Expr) -> Option<&'static str> {
    match ungroup(expression) {
        Expr::Unary(unary) if matches!(unary.op, syn::UnOp::Not(_)) => metadata_field(&unary.expr),
        _ => None,
    }
}

fn is_false(expression: &Expr) -> bool {
    matches!(ungroup(expression), Expr::Lit(ExprLit { lit: Lit::Bool(value), .. }) if !value.value)
}

fn if_has_false_branch(if_expression: &ExprIf) -> bool {
    block_last_is_false(&if_expression.then_branch) || if_expression
        .else_branch
        .as_ref()
        .is_some_and(|(_, expression)| expression_is_false(expression))
}

fn expression_is_false(expression: &Expr) -> bool {
    is_false(expression)
        || matches!(ungroup(expression), Expr::Block(block) if block_last_is_false(&block.block))
}

fn block_last_is_false(block: &Block) -> bool {
    block.stmts.last().is_some_and(|statement| match statement {
        Stmt::Expr(expression, None) => is_false(expression),
        _ => false,
    })
}

fn is_suppression_condition(expression: &Expr) -> bool {
    match ungroup(expression) {
        Expr::Unary(unary) if matches!(unary.op, syn::UnOp::Not(_)) => metadata_field(&unary.expr).is_some(),
        Expr::Field(_) => metadata_field(expression).is_some(),
        Expr::Binary(binary) if matches!(binary.op, BinOp::Eq(_) | BinOp::Ne(_)) => {
            metadata_field(expression).is_some()
        }
        Expr::Binary(binary) if matches!(binary.op, BinOp::And(_) | BinOp::Or(_)) => {
            is_suppression_condition(&binary.left) || is_suppression_condition(&binary.right)
        }
        _ => false,
    }
}

fn block_returns(block: &Block) -> bool {
    block.stmts.iter().any(|statement| match statement {
        Stmt::Expr(Expr::Return(_), _) => true,
        Stmt::Expr(Expr::If(if_expression), _) => {
            block_returns(&if_expression.then_branch)
                || if_expression
                    .else_branch
                    .as_ref()
                    .is_some_and(|(_, expression)| match ungroup(expression) {
                        Expr::Block(block) => block_returns(&block.block),
                        Expr::If(nested) => block_returns(&nested.then_branch),
                        _ => false,
                    })
        }
        _ => false,
    })
}

fn block_clears_hard_gate(block: &Block, hard_names: &BTreeSet<String>) -> bool {
    block.stmts.iter().any(|statement| match statement {
        Stmt::Expr(Expr::Assign(assignment), _) => {
            expression_name(&assignment.left).is_some_and(|name| hard_names.contains(&name))
                && is_false(&assignment.right)
        }
        Stmt::Expr(Expr::Binary(binary), _) => {
            is_assignment_operator(&binary.op)
                && expression_name(&binary.left).is_some_and(|name| hard_names.contains(&name))
        }
        _ => false,
    })
}

const fn is_assignment_operator(operator: &BinOp) -> bool {
    matches!(
        operator,
        BinOp::AddAssign(_)
            | BinOp::SubAssign(_)
            | BinOp::MulAssign(_)
            | BinOp::DivAssign(_)
            | BinOp::RemAssign(_)
            | BinOp::BitXorAssign(_)
            | BinOp::BitAndAssign(_)
            | BinOp::BitOrAssign(_)
            | BinOp::ShlAssign(_)
            | BinOp::ShrAssign(_)
    )
}

fn suppressed(path: &str, source: &str, line: u32) -> Result<bool, LintError> {
    let index = usize::try_from(line.saturating_sub(1))
        .map_err(|_| LintError::new(format!("{path}: line number is out of range")))?;
    let text = source.lines().nth(index).ok_or_else(|| {
        LintError::new(format!("{path}: finding line {line} is outside the source"))
    })?;
    let Some(reason) = reason(text, SUPPRESSION_TOKEN)? else {
        return Ok(false);
    };
    let lower = reason.as_str().to_ascii_lowercase();
    if lower.contains("gate owner") || lower.contains("owner:") || lower.contains("owner=") {
        Ok(true)
    } else {
        Err(LintError::new(format!(
            "{path}:{line}: {SUPPRESSION_TOKEN} suppression reason must name gate owner"
        )))
    }
}

#[cfg(test)]
mod tests {
    use std::path::{Path, PathBuf};

    use super::SelfDisarmableGateRule;
    use crate::{Git, LintError, Repository, Rule};

    struct Fixture {
        _temporary: tempfile::TempDir,
        repository: Repository,
    }

    struct FakeGit {
        root: PathBuf,
        stream: Vec<u8>,
    }

    impl Git for FakeGit {
        fn repository_root(&self, _cwd: &Path) -> Result<PathBuf, LintError> {
            Ok(self.root.clone())
        }

        fn tracked_paths(&self, _root: &Path) -> Result<Vec<u8>, LintError> {
            Ok(self.stream.clone())
        }
    }

    fn fixture(source: &str) -> Fixture {
        let temporary = tempfile::tempdir().expect("tempdir");
        let path = temporary.path().join("crates/demo/src/gate.rs");
        std::fs::create_dir_all(path.parent().expect("parent")).expect("parents");
        std::fs::write(&path, source).expect("source");
        let repository = Repository::discover(
            &FakeGit {
                root: temporary.path().to_path_buf(),
                stream: b"crates/demo/src/gate.rs\0".to_vec(),
            },
            temporary.path(),
        )
        .expect("repository");
        Fixture {
            _temporary: temporary,
            repository,
        }
    }

    #[test]
    fn adverse_fixture_matrix_is_rejected() {
        for source in [
            "fn assess(meta: Meta, hard: bool) -> bool { let size_diff_raw = hard; if meta.mechanical_churn { return false; } size_diff_raw }",
            "fn assess(meta: Meta, hard: bool) -> bool { let size_diff_raw = if meta.mechanical_churn { false } else { hard }; size_diff_raw }",
            "fn assess(meta: Meta, hard: bool) -> bool { let size_diff_raw = if meta.mechanical_churn { hard } else { false }; size_diff_raw }",
            "fn assess(meta: Meta, hard: bool) -> bool { let size_diff_raw = hard && !meta.diff_added; size_diff_raw }",
            "fn assess(meta: Meta, size_diff_raw: bool) -> bool { if meta.mechanical_churn || size_diff_raw { return false; } size_diff_raw }",
            "fn assess(meta: Meta, size_diff_raw: bool, enabled: bool) -> bool { let hard_trigger = size_diff_raw; if enabled { if meta.mechanical_churn { return false; } } hard_trigger }",
            "fn assess(meta: Meta, diff_lines: usize) -> bool { if meta.mechanical_churn || diff_lines > 100 { return false; } true }",
            "fn assess(meta: Meta, mut hard_trigger: bool) -> bool { if meta.mechanical_churn { hard_trigger = false; } hard_trigger }",
            "fn publish(meta: Meta, publish_trigger: bool) -> bool { if meta.mechanical_churn { return false; } publish_trigger }",
        ] {
            let fixture = fixture(source);
            assert_eq!(
                SelfDisarmableGateRule
                    .check(&fixture.repository)
                    .expect("check")
                    .findings()
                    .len(),
                1,
                "source={source}"
            );
        }
    }

    #[test]
    fn safe_fixture_matrix_is_clean() {
        for source in [
            "fn assess(meta: Meta, diff_lines: usize) -> (bool, bool) { let size_diff_added = meta.diff_added && diff_lines > 10; let size_diff_lines = diff_lines > 10; let size_diff_raw = size_diff_added || size_diff_lines; let soft = meta.mechanical_churn && size_diff_raw; (size_diff_raw, soft) }",
            "fn validate(meta: Meta) -> bool { if !meta.mechanical_churn { return true; } false }",
            "fn check(meta: Meta) -> bool { if meta.mechanical_churn { return false; } let hard_trigger = true; hard_trigger }",
            "fn publish(meta: Meta, publish_trigger: bool) -> bool { let advisory = meta.mechanical_churn && publish_trigger; publish_trigger || advisory }",
        ] {
            let fixture = fixture(source);
            assert!(
                SelfDisarmableGateRule
                    .check(&fixture.repository)
                    .expect("check")
                    .findings()
                    .is_empty(),
                "source={source}"
            );
        }
    }

    #[test]
    fn suppression_requires_a_gate_owner_reason() {
        let missing_owner = fixture(
            "fn assess(meta: Meta, hard: bool) -> bool { let size_diff_raw = hard; if meta.mechanical_churn { // lint-self-disarmable-gate: ok intentional\n return false; } size_diff_raw }",
        );
        assert!(SelfDisarmableGateRule.check(&missing_owner.repository).is_err());

        let valid = fixture(
            "fn assess(meta: Meta, hard: bool) -> bool { let size_diff_raw = hard; if meta.mechanical_churn { // lint-self-disarmable-gate: ok gate owner: plan_quality\n return false; } size_diff_raw }",
        );
        assert!(
            SelfDisarmableGateRule
                .check(&valid.repository)
                .expect("check")
                .findings()
                .is_empty()
        );
    }
}
