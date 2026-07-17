//! Require raw Git push construction to include an explicit destination refspec.

use std::collections::{BTreeMap, BTreeSet};

use proc_macro2::LineColumn;
use syn::{ExprArray, ExprMethodCall, spanned::Spanned, visit::Visit};

use crate::{
    Finding, LintError, PathSelector, Repository, Rule, RuleMetadata, RuleOutput,
    suppression::reason,
    syntax::RustSyntax,
};

use super::command_arguments::{Argument, Constants, array_arguments};

const NAME: &str = "git-push-refspec";
const DESCRIPTION: &str = "Require Git push commands to name a destination refspec";
const SUPPRESSION_TOKEN: &str = "lint-git-push-refspec";
const TEST_PREFIX: &str = "crates/larch-lint/tests/";
const COMMAND_ELEMENTS: usize = 2;
const EXPLICIT_OPERANDS: usize = 2;

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/git-push-refspec.toml",
);

#[derive(Debug)]
pub struct GitPushRefspecRule;

pub static RULE: GitPushRefspecRule = GitPushRefspecRule;

impl Rule for GitPushRefspecRule {
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
            let constants = Constants::from_file(syntax.file());
            let mut visitor = PushVisitor::new(&constants);
            visitor.visit_file(syntax.file());
            for line in visitor.finding_lines() {
                if is_suppressed(path.as_str(), &source, line)? {
                    continue;
                }
                findings.push(Finding::new(
                    path.as_str(),
                    line,
                    "contains git push without an explicit destination refspec",
                ));
            }
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

struct PushVisitor<'syntax> {
    constants: &'syntax Constants<'syntax>,
    array_lines: BTreeSet<u32>,
    builders: BTreeMap<LineColumn, BuilderCandidate>,
}

impl<'syntax> PushVisitor<'syntax> {
    const fn new(constants: &'syntax Constants<'syntax>) -> Self {
        Self {
            constants,
            array_lines: BTreeSet::new(),
            builders: BTreeMap::new(),
        }
    }

    fn finding_lines(self) -> BTreeSet<u32> {
        let mut lines = self.array_lines;
        lines.extend(
            self.builders
                .into_values()
                .filter(|candidate| lacks_refspec(&candidate.arguments))
                .map(|candidate| candidate.line),
        );
        lines
    }
}

impl<'ast> Visit<'ast> for PushVisitor<'ast> {
    fn visit_expr_array(&mut self, array: &'ast ExprArray) {
        let arguments = array_arguments(self.constants, array);
        if lacks_refspec(&arguments)
            && let Some(line) = array
                .elems
                .first()
                .and_then(|element| line_number(element.span()))
        {
            self.array_lines.insert(line);
        }
        syn::visit::visit_expr_array(self, array);
    }

    fn visit_expr_method_call(&mut self, method: &'ast ExprMethodCall) {
        if let Some(command) = self.constants.extend_builder(method) {
            let root = command.root_span.start();
            let candidate = BuilderCandidate {
                line: u32::try_from(root.line).unwrap_or(u32::MAX),
                end: method.method.span().end(),
                arguments: command.arguments,
            };
            self.builders
                .entry(root)
                .and_modify(|existing| {
                    if candidate.end > existing.end {
                        *existing = candidate.clone();
                    }
                })
                .or_insert(candidate);
        }
        syn::visit::visit_expr_method_call(self, method);
    }
}

#[derive(Clone)]
struct BuilderCandidate {
    line: u32,
    end: LineColumn,
    arguments: Vec<Argument>,
}

fn lacks_refspec(arguments: &[Argument]) -> bool {
    if arguments.len() < COMMAND_ELEMENTS
        || arguments[0] != Argument::Static("git".to_owned())
        || arguments[1] != Argument::Static("push".to_owned())
    {
        return false;
    }
    arguments[COMMAND_ELEMENTS..]
        .iter()
        .filter(|argument| !matches!(argument, Argument::Static(value) if value.starts_with('-')))
        .count()
        < EXPLICIT_OPERANDS
}

fn line_number(span: proc_macro2::Span) -> Option<u32> {
    u32::try_from(span.start().line).ok()
}

fn is_suppressed(path: &str, source: &str, line: u32) -> Result<bool, LintError> {
    if !path.starts_with(TEST_PREFIX) {
        return Ok(false);
    }
    let line_index = usize::try_from(line.saturating_sub(1))
        .map_err(|_| LintError::new(format!("{path}: line number is out of range")))?;
    let text = source.lines().nth(line_index).ok_or_else(|| {
        LintError::new(format!("{path}: finding line {line} is outside the source"))
    })?;
    Ok(reason(text, SUPPRESSION_TOKEN)?.is_some())
}

crate::register_rule!(METADATA, RULE);
