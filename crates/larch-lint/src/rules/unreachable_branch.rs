//! Detect branches contradicted by an earlier return of the same value.
//!
//! `syn` supplies the maintained Rust grammar and spans. `rustc`'s
//! `unreachable_code` lint and Clippy catch general unreachable code, but they
//! do not express larch's intentionally narrower policy: only report a later
//! branch when a preceding same-condition return proves that branch cannot
//! execute and the branch returns the same value. This visitor therefore keeps
//! only those return-derived facts; it is not a general control-flow analyser.

use std::collections::BTreeSet;

use proc_macro2::Span;
use syn::{
    Block, Expr, ExprIf, ExprMatch, ExprReturn, ImplItemFn, ItemFn, Pat, Stmt, TraitItemFn,
    spanned::Spanned,
    visit::{self, Visit},
};

use crate::{
    Finding, LintError, PathSelector, Repository, Rule, RuleMetadata, RuleOutput,
    suppression::reason as suppression_reason,
    syntax::RustSyntax,
};

const NAME: &str = "unreachable-branch";
const DESCRIPTION: &str = "Detect branches contradicted by earlier same-value returns";
const SUPPRESSION: &str = "lint-unreachable-branch";
const RUST_SOURCES: &[&str] = &["**/*.rs"];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/unreachable-branch.toml",
);

#[derive(Debug)]
pub struct UnreachableBranchRule;

pub static RULE: UnreachableBranchRule = UnreachableBranchRule;

impl Rule for UnreachableBranchRule {
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
            let source = repository.read_utf8(path)?;
            let syntax = RustSyntax::parse(path.as_str(), &source)?;
            let mut visitor = BranchVisitor::new(path.as_str(), &source);
            visitor.visit_file(syntax.file());
            findings.extend(visitor.into_findings()?);
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

#[derive(Clone, Default)]
struct PathState {
    impossible: BTreeSet<String>,
    proofs: BTreeSet<ReturnProof>,
}

impl PathState {
    fn with_return(&self, condition: String, returned: String) -> Self {
        let mut next = self.clone();
        let _ = next.impossible.insert(condition.clone());
        let _ = next.proofs.insert(ReturnProof {
            condition,
            returned,
        });
        next
    }

    fn invalidated() -> Self {
        Self::default()
    }
}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
struct ReturnProof {
    condition: String,
    returned: String,
}

struct BranchVisitor<'source> {
    error: Option<LintError>,
    findings: Vec<Finding>,
    path: &'source str,
    source: &'source str,
}

impl<'source> BranchVisitor<'source> {
    const fn new(path: &'source str, source: &'source str) -> Self {
        Self {
            error: None,
            findings: Vec::new(),
            path,
            source,
        }
    }

    fn into_findings(self) -> Result<Vec<Finding>, LintError> {
        if let Some(error) = self.error {
            return Err(error);
        }
        Ok(self.findings)
    }

    fn scan_function(&mut self, block: &Block) {
        if self.error.is_none()
            && let Err(error) = self.scan_block(block, PathState::default())
        {
            self.error = Some(error);
        }
    }

    fn scan_block(&mut self, block: &Block, mut state: PathState) -> Result<(), LintError> {
        for (index, statement) in block.stmts.iter().enumerate() {
            match statement {
                Stmt::Expr(Expr::Return(returned), _) => {
                    let value = return_value(returned, self.source)?;
                    self.scan_unreachable_tail(&block.stmts[index + 1..], &value)?;
                    return Ok(());
                }
                Stmt::Expr(Expr::If(branch), _) => {
                    state = self.scan_if(branch, state)?;
                    if if_always_returns(branch) {
                        return Ok(());
                    }
                }
                Stmt::Expr(Expr::Match(branch), _) => {
                    state = Self::scan_match(branch, state, self.source)?;
                }
                Stmt::Local(_) | Stmt::Expr(Expr::Assign(_), _) => {
                    state = PathState::invalidated();
                }
                Stmt::Item(_) => {}
                Stmt::Macro(_) | Stmt::Expr(_, _) => {
                    // An arbitrary expression may mutate a value named by a
                    // tracked condition through an alias or a mutable borrow.
                    // Clearing facts here preserves the rule's proof-only scope.
                    state = PathState::invalidated();
                }
            }
        }
        Ok(())
    }

    fn scan_if(&mut self, branch: &ExprIf, state: PathState) -> Result<PathState, LintError> {
        let condition = expression_key(&branch.cond, self.source)?;
        if let Some(returned) = block_return_value(&branch.then_branch, self.source)? {
            self.record_if_contradiction(branch, &condition, &returned, &state)?;
            self.scan_block(&branch.then_branch, state.clone())?;
            let next = state.with_return(condition, returned);
            if let Some((_, else_branch)) = &branch.else_branch {
                if let Expr::If(nested) = else_branch.as_ref() {
                    return self.scan_if(nested, next);
                }
                self.scan_else_branch(else_branch, next.clone())?;
            }
            return Ok(next);
        }

        self.scan_block(&branch.then_branch, state.clone())?;
        if let Some((_, else_branch)) = &branch.else_branch {
            self.scan_else_branch(else_branch, state.clone())?;
        }
        Ok(state)
    }

    fn scan_else_branch(&mut self, branch: &Expr, state: PathState) -> Result<(), LintError> {
        match branch {
            Expr::If(nested) => {
                let _ = self.scan_if(nested, state)?;
            }
            Expr::Block(block) => self.scan_block(&block.block, state)?,
            _ => {}
        }
        Ok(())
    }

    fn scan_match(
        branch: &ExprMatch,
        state: PathState,
        source: &str,
    ) -> Result<PathState, LintError> {
        let condition = expression_key(&branch.expr, source)?;
        let mut next = state;
        for arm in &branch.arms {
            if arm.guard.is_some() || !is_true_pattern(&arm.pat) {
                continue;
            }
            let Some(returned) = expression_return_value(&arm.body, source)? else {
                continue;
            };
            next = next.with_return(condition.clone(), returned);
        }
        Ok(next)
    }

    fn record_if_contradiction(
        &mut self,
        branch: &ExprIf,
        condition: &str,
        returned: &str,
        state: &PathState,
    ) -> Result<(), LintError> {
        let proved = state.impossible.contains(condition)
            && state.proofs.contains(&ReturnProof {
                condition: condition.to_owned(),
                returned: returned.to_owned(),
            });
        if !proved {
            return Ok(());
        }
        let line = span_line(branch.if_token.span)?;
        if suppression_reason(source_line(self.source, line, self.path)?, SUPPRESSION)?.is_none() {
            self.findings.push(Finding::new(
                self.path,
                line,
                "branch is contradicted by an earlier return of the same value",
            ));
        }
        Ok(())
    }

    fn scan_unreachable_tail(&mut self, statements: &[Stmt], returned: &str) -> Result<(), LintError> {
        for statement in statements {
            let Stmt::Expr(Expr::If(branch), _) = statement else {
                continue;
            };
            let Some(candidate) = block_return_value(&branch.then_branch, self.source)? else {
                continue;
            };
            if candidate == returned {
                let line = span_line(branch.if_token.span)?;
                if suppression_reason(source_line(self.source, line, self.path)?, SUPPRESSION)?.is_none() {
                    self.findings.push(Finding::new(
                        self.path,
                        line,
                        "branch is contradicted by an earlier return of the same value",
                    ));
                }
            }
        }
        Ok(())
    }
}

impl<'ast> Visit<'ast> for BranchVisitor<'_> {
    fn visit_item_fn(&mut self, function: &'ast ItemFn) {
        self.scan_function(&function.block);
        visit::visit_item_fn(self, function);
    }

    fn visit_impl_item_fn(&mut self, function: &'ast ImplItemFn) {
        self.scan_function(&function.block);
        visit::visit_impl_item_fn(self, function);
    }

    fn visit_trait_item_fn(&mut self, function: &'ast TraitItemFn) {
        if let Some(block) = &function.default {
            self.scan_function(block);
        }
        visit::visit_trait_item_fn(self, function);
    }
}

fn block_return_value(block: &Block, source: &str) -> Result<Option<String>, LintError> {
    for statement in block.stmts.iter().rev() {
        match statement {
            Stmt::Expr(Expr::Return(returned), _) => return return_value(returned, source).map(Some),
            Stmt::Item(_) => {}
            Stmt::Local(_) | Stmt::Macro(_) | Stmt::Expr(_, _) => return Ok(None),
        }
    }
    Ok(None)
}

fn expression_return_value(expression: &Expr, source: &str) -> Result<Option<String>, LintError> {
    match expression {
        Expr::Return(returned) => return_value(returned, source).map(Some),
        Expr::Block(block) => block_return_value(&block.block, source),
        _ => Ok(None),
    }
}

fn return_value(returned: &ExprReturn, source: &str) -> Result<String, LintError> {
    let Some(expression) = &returned.expr else {
        return Ok("()".to_owned());
    };
    expression_key(expression, source)
}

fn if_always_returns(branch: &ExprIf) -> bool {
    block_return_value_without_source(&branch.then_branch)
        && branch
            .else_branch
            .as_ref()
            .is_some_and(|(_, branch)| match branch.as_ref() {
                Expr::If(nested) => if_always_returns(nested),
                Expr::Block(block) => block_return_value_without_source(&block.block),
                _ => false,
            })
}

fn block_return_value_without_source(block: &Block) -> bool {
    block.stmts.iter().rev().any(|statement| {
        matches!(statement, Stmt::Expr(Expr::Return(_), _))
    })
}

const fn is_true_pattern(pattern: &Pat) -> bool {
    matches!(
        pattern,
        Pat::Lit(literal) if matches!(&literal.lit, syn::Lit::Bool(boolean) if boolean.value)
    )
}

fn expression_key(expression: &Expr, source: &str) -> Result<String, LintError> {
    let text = span_text(expression.span(), source)?;
    let normalized: String = text.chars().filter(|character| !character.is_whitespace()).collect();
    if normalized.is_empty() {
        return Err(LintError::new("cannot normalize an empty Rust expression"));
    }
    Ok(normalized)
}

fn span_text(span: Span, source: &str) -> Result<String, LintError> {
    let start = span.start();
    let end = span.end();
    let lines: Vec<&str> = source.lines().collect();
    let start_index = start.line.saturating_sub(1);
    let end_index = end.line.saturating_sub(1);
    let first = lines
        .get(start_index)
        .ok_or_else(|| LintError::new("expression span start line is outside the source"))?;
    let last = lines
        .get(end_index)
        .ok_or_else(|| LintError::new("expression span end line is outside the source"))?;
    if start_index == end_index {
        return first
            .get(start.column..end.column)
            .map(str::to_owned)
            .ok_or_else(|| LintError::new("expression span columns are outside the source"));
    }
    let mut text = first
        .get(start.column..)
        .ok_or_else(|| LintError::new("expression span start column is outside the source"))?
        .to_owned();
    for line in &lines[start_index + 1..end_index] {
        text.push('\n');
        text.push_str(line);
    }
    text.push('\n');
    text.push_str(
        last.get(..end.column)
            .ok_or_else(|| LintError::new("expression span end column is outside the source"))?,
    );
    Ok(text)
}

fn span_line(span: Span) -> Result<u32, LintError> {
    u32::try_from(span.start().line)
        .map_err(|_| LintError::new("source line number exceeds u32"))
}

fn source_line<'source>(source: &'source str, line: u32, path: &str) -> Result<&'source str, LintError> {
    source
        .lines()
        .nth(usize::try_from(line.saturating_sub(1)).map_err(|_| {
            LintError::new(format!("{path}: source line number exceeds usize"))
        })?)
        .ok_or_else(|| LintError::new(format!("{path}: source line {line} is missing")))
}
