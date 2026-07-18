//! Require literal timing task kinds to use the canonical allow-list.
//!
//! # Crate survey (issue #7612)
//!
//! | Need | Selection |
//! |---|---|
//! | Shell and Markdown text | Reuse repository discovery and the workspace regex engine. |
//! | Rust command construction | Reuse `command_arguments` static array and builder analysis. |
//! | Rust CLI defaults | Reuse `syn` attribute parsing for Clap's `arg` attributes. |
//!
//! The canonical policy remains `TIMING_TASK_KINDS_ALLOWED` in Python. This
//! rule reads that source directly so Rust discovers literals without copying
//! the allow-list into a second owner.

use std::{
    collections::{BTreeMap, BTreeSet},
    path::Path,
    sync::LazyLock,
};

use regex::Regex;
use syn::{Attribute, ExprArray, ExprMethodCall, Field, LitStr, spanned::Spanned, visit::Visit};

use crate::{Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput, syntax::RustSyntax};

use super::command_arguments::{Argument, BuilderCommand, Constants, array_arguments, record_builder_from_method};

const NAME: &str = "timing-task-kind-allowlist";
const DESCRIPTION: &str = "Require literal timing task kinds to appear in the canonical allow-list";
const ALLOWLIST_PATH: &str = "python/larch/report/timing.py";
const TIMING_FLAG: &str = "--timing-task-kind";

static TEXT_KIND: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"--timing-task-kind\s+([A-Za-z0-9][A-Za-z0-9_-]*)")
        .expect("timing task kind expression is valid")
});
static ALLOWLIST_BODY: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?s)TIMING_TASK_KINDS_ALLOWED\s*:[^=]*=\s*frozenset\s*\(\s*\{(?P<body>.*?)\}\s*\)")
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

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let paths: Vec<_> = repository
            .paths()
            .iter()
            .filter(|path| is_text_scope(path.as_str()) || is_rust_scope(path.as_str()))
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
            } else if is_rust_scope(path.as_str()) {
                findings.extend(check_rust(path.as_str(), &source, &allowed)?);
            }
        }
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

struct RustVisitor<'syntax> {
    constants: &'syntax Constants<'syntax>,
    arrays: BTreeMap<usize, String>,
    builders: BTreeMap<proc_macro2::LineColumn, BuilderCommand>,
    defaults: BTreeMap<usize, String>,
}

impl<'syntax> RustVisitor<'syntax> {
    const fn new(constants: &'syntax Constants<'syntax>) -> Self {
        Self {
            constants,
            arrays: BTreeMap::new(),
            builders: BTreeMap::new(),
            defaults: BTreeMap::new(),
        }
    }

    fn finish(self) -> BTreeMap<usize, String> {
        let mut kinds = self.arrays;
        kinds.extend(self.defaults);
        for candidate in self.builders.into_values() {
            if let Some(kind) = kind_after_flag(&candidate.arguments) {
                kinds.insert(candidate.root_span.start().line, kind);
            }
        }
        kinds
    }
}

impl<'ast> Visit<'ast> for RustVisitor<'_> {
    fn visit_expr_array(&mut self, array: &'ast ExprArray) {
        if let Some(kind) = kind_after_flag(&array_arguments(self.constants, array)) {
            self.arrays.insert(array.span().start().line, kind);
        }
        syn::visit::visit_expr_array(self, array);
    }

    fn visit_expr_method_call(&mut self, method: &'ast ExprMethodCall) {
        record_builder_from_method(self.constants, &mut self.builders, method);
        syn::visit::visit_expr_method_call(self, method);
    }

    fn visit_field(&mut self, field: &'ast Field) {
        if let Some(kind) = clap_default(field) {
            self.defaults.insert(field.span().start().line, kind);
        }
        syn::visit::visit_field(self, field);
    }

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
            timing_long = meta
                .value()
                .ok()
                .and_then(|value| value.parse::<LitStr>().ok())
                .is_none_or(|value| value.value() == "timing-task-kind");
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

fn number(path: &str, line: usize) -> Result<u32, LintError> {
    u32::try_from(line).map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))
}

fn has_lowercase_extension(path: &str, expected: &str) -> bool {
    Path::new(path)
        .extension()
        .is_some_and(|extension| extension == expected)
}
