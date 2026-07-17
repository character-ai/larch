//! Enforce the future Rust scratch-directory and tmpdir-fallback policy.
//!
//! `syn` supplies the Rust grammar and expression traversal. The custom logic
//! below is deliberately limited to larch's two policy decisions: the one
//! scratch owner for ambient temporary directories, and the configured
//! environment fallback required when consuming `args.tmpdir`.

use std::collections::{BTreeMap, BTreeSet};

use syn::{
    Expr, ExprCall, ExprField, ExprMethodCall, ExprPath, File, Item, ItemMod, Path, UseTree,
    visit::{self, Visit},
};

use crate::{
    Finding, LintError, PathSelector, Repository, Rule, RuleMetadata, RuleOutput,
    suppression::reason as suppression_reason,
};

const TEMPFILE_DIR_NAME: &str = "tempfile-dir";
const TMPDIR_FALLBACK_NAME: &str = "tmpdir-arg-env-fallback";
const TEMPFILE_DIR_DESCRIPTION: &str = "Require the scratch owner for ambient temporary directories";
const TMPDIR_FALLBACK_DESCRIPTION: &str = "Require an environment fallback for args.tmpdir";
const RUST_SOURCES: &[&str] = &["crates/**/src/**/*.rs"];
const RUST_TESTS: &[&str] = &["crates/**/tests/**/*.rs"];
const SCRATCH_OWNER: &str = "crates/larch/src/scratch.rs";
const TMPDIR_FIELD: &str = "args.tmpdir";
const ENV_TMPDIR_CONSTANT: &str = "ENV_IMPLEMENT_TMPDIR";

pub static TEMPFILE_DIR_METADATA: RuleMetadata = RuleMetadata::new(
    TEMPFILE_DIR_NAME,
    TEMPFILE_DIR_DESCRIPTION,
    "crates/larch-lint/migration-ledger/tempfile-dir.toml",
);

pub static TMPDIR_FALLBACK_METADATA: RuleMetadata = RuleMetadata::new(
    TMPDIR_FALLBACK_NAME,
    TMPDIR_FALLBACK_DESCRIPTION,
    "crates/larch-lint/migration-ledger/tmpdir-arg-env-fallback.toml",
);

#[derive(Debug)]
pub struct TempfileDirRule;

#[derive(Debug)]
pub struct TmpdirFallbackRule;

pub static TEMPFILE_DIR_RULE: TempfileDirRule = TempfileDirRule;
pub static TMPDIR_FALLBACK_RULE: TmpdirFallbackRule = TmpdirFallbackRule;

impl Rule for TempfileDirRule {
    fn name(&self) -> &'static str {
        TEMPFILE_DIR_NAME
    }

    fn description(&self) -> &'static str {
        TEMPFILE_DIR_DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let selector = PathSelector::new(RUST_SOURCES, RUST_TESTS)?;
        let mut findings = Vec::new();
        for path in selector.select(repository) {
            if path.as_str() == SCRATCH_OWNER {
                continue;
            }
            let source = repository.read_utf8(path)?;
            let file = syn::parse_file(&source).map_err(|error| {
                LintError::new(format!("{}: invalid Rust syntax: {error}", path.as_str()))
            })?;
            let aliases = TempfileAliases::from_file(&file);
            let mut visitor = PolicyVisitor::new(&source, path.as_str(), aliases);
            visitor.visit_file(&file);
            findings.extend(visitor.tempfile_findings()?);
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

impl Rule for TmpdirFallbackRule {
    fn name(&self) -> &'static str {
        TMPDIR_FALLBACK_NAME
    }

    fn description(&self) -> &'static str {
        TMPDIR_FALLBACK_DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let selector = PathSelector::new(RUST_SOURCES, RUST_TESTS)?;
        let mut findings = Vec::new();
        for path in selector.select(repository) {
            let source = repository.read_utf8(path)?;
            let file = syn::parse_file(&source).map_err(|error| {
                LintError::new(format!("{}: invalid Rust syntax: {error}", path.as_str()))
            })?;
            let aliases = TempfileAliases::from_file(&file);
            let mut visitor = PolicyVisitor::new(&source, path.as_str(), aliases);
            visitor.visit_file(&file);
            findings.extend(visitor.tmpdir_findings()?);
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(TEMPFILE_DIR_METADATA, TEMPFILE_DIR_RULE);
crate::register_rule!(TMPDIR_FALLBACK_METADATA, TMPDIR_FALLBACK_RULE);

#[derive(Default)]
struct TempfileAliases {
    builders: BTreeSet<String>,
    constructors: BTreeSet<String>,
    tempdir_functions: BTreeSet<String>,
}

impl TempfileAliases {
    fn from_file(file: &File) -> Self {
        let mut aliases = Self::default();
        for item in &file.items {
            if let Item::Use(item_use) = item {
                collect_tempfile_aliases(&item_use.tree, &mut Vec::new(), &mut aliases);
            }
        }
        aliases
    }
}

fn collect_tempfile_aliases(tree: &UseTree, prefix: &mut Vec<String>, aliases: &mut TempfileAliases) {
    match tree {
        UseTree::Path(path) => {
            prefix.push(path.ident.to_string());
            collect_tempfile_aliases(&path.tree, prefix, aliases);
            let _ = prefix.pop();
        }
        UseTree::Group(group) => {
            for item in &group.items {
                collect_tempfile_aliases(item, prefix, aliases);
            }
        }
        UseTree::Name(name) if prefix.first().is_some_and(|part| part == "tempfile") => {
            record_alias(&name.ident.to_string(), &name.ident.to_string(), aliases);
        }
        UseTree::Rename(rename) if prefix.first().is_some_and(|part| part == "tempfile") => {
            record_alias(&rename.ident.to_string(), &rename.rename.to_string(), aliases);
        }
        UseTree::Glob(_) | UseTree::Name(_) | UseTree::Rename(_) => {}
    }
}

fn record_alias(original: &str, alias: &str, aliases: &mut TempfileAliases) {
    match original {
        "Builder" => {
            let _ = aliases.builders.insert(alias.to_owned());
        }
        "TempDir" => {
            let _ = aliases.constructors.insert(alias.to_owned());
        }
        "tempdir" => {
            let _ = aliases.tempdir_functions.insert(alias.to_owned());
        }
        _ => {}
    }
}

struct PolicyVisitor<'source> {
    aliases: TempfileAliases,
    path: &'source str,
    source: &'source str,
    tempfile: Vec<TempfileCandidate>,
    tmpdir: Vec<usize>,
    tmpdir_seen: usize,
}

impl<'source> PolicyVisitor<'source> {
    const fn new(source: &'source str, path: &'source str, aliases: TempfileAliases) -> Self {
        Self {
            aliases,
            path,
            source,
            tempfile: Vec::new(),
            tmpdir: Vec::new(),
            tmpdir_seen: 0,
        }
    }

    fn tempfile_findings(&self) -> Result<Vec<Finding>, LintError> {
        let mut occurrences = BTreeMap::new();
        let mut findings = Vec::new();
        for candidate in &self.tempfile {
            let needle = candidate.needle();
            let line = line_for_occurrence(
                self.source,
                &needle,
                occurrences.entry(needle.clone()).or_insert(0),
            )?;
            if suppression_reason(source_line(self.source, line)?, TEMPFILE_DIR_NAME)?.is_none() {
                findings.push(Finding::new(
                    self.path,
                    line,
                    "ambient temporary directory; use the scratch owner",
                ));
            }
        }
        Ok(findings)
    }

    fn tmpdir_findings(&self) -> Result<Vec<Finding>, LintError> {
        let mut findings = Vec::new();
        for occurrence in &self.tmpdir {
            let mut source_occurrence = *occurrence;
            let line = line_for_occurrence(
                self.source,
                TMPDIR_FIELD,
                &mut source_occurrence,
            )?;
            if suppression_reason(source_line(self.source, line)?, TMPDIR_FALLBACK_NAME)?.is_none() {
                findings.push(Finding::new(
                    self.path,
                    line,
                    "direct args.tmpdir consumption; use ENV_IMPLEMENT_TMPDIR fallback",
                ));
            }
        }
        Ok(findings)
    }

    fn record_tempfile(&mut self, candidate: TempfileCandidate) {
        self.tempfile.push(candidate);
    }

    const fn next_tmpdir_occurrence(&mut self) -> usize {
        let occurrence = self.tmpdir_seen;
        self.tmpdir_seen += 1;
        occurrence
    }

    fn record_tmpdir(&mut self, occurrence: usize) {
        self.tmpdir.push(occurrence);
    }
}

impl<'ast> Visit<'ast> for PolicyVisitor<'_> {
    fn visit_item_mod(&mut self, item: &'ast ItemMod) {
        if item.attrs.iter().any(is_test_configuration) {
            return;
        }
        visit::visit_item_mod(self, item);
    }

    fn visit_expr_call(&mut self, call: &'ast ExprCall) {
        if let Some(candidate) = ambient_constructor(call, &self.aliases) {
            self.record_tempfile(candidate);
        }
        visit::visit_expr_call(self, call);
    }

    fn visit_expr_method_call(&mut self, call: &'ast ExprMethodCall) {
        if let Some(candidate) = ambient_builder(call, &self.aliases) {
            self.record_tempfile(candidate);
        }
        if is_args_tmpdir_or_view(&call.receiver) {
            let occurrence = self.next_tmpdir_occurrence();
            if !is_safe_tmpdir_fallback(call) {
                self.record_tmpdir(occurrence);
            }
            for argument in &call.args {
                self.visit_expr(argument);
            }
            return;
        }
        visit::visit_expr_method_call(self, call);
    }

    fn visit_expr_field(&mut self, field: &'ast ExprField) {
        if is_args_tmpdir_field(field) {
            let occurrence = self.next_tmpdir_occurrence();
            self.record_tmpdir(occurrence);
            return;
        }
        visit::visit_expr_field(self, field);
    }
}

fn is_test_configuration(attribute: &syn::Attribute) -> bool {
    attribute.path().is_ident("cfg") && attribute.meta.require_list().is_ok_and(|list| list.tokens.to_string() == "test")
}

#[derive(Clone, Debug)]
enum TempfileCandidate {
    Builder(String),
    Constructor(String),
    Function(String),
}

impl TempfileCandidate {
    fn needle(&self) -> String {
        match self {
            Self::Builder(name) => format!(".{name}("),
            Self::Constructor(name) => format!("{name}::new("),
            Self::Function(name) => format!("{name}("),
        }
    }
}

fn ambient_constructor(call: &ExprCall, aliases: &TempfileAliases) -> Option<TempfileCandidate> {
    let Expr::Path(path) = call.func.as_ref() else {
        return None;
    };
    let last = path.path.segments.last()?.ident.to_string();
    if is_tempfile_function(&path.path, aliases) {
        Some(TempfileCandidate::Function(last))
    } else if is_tempdir_new(&path.path, aliases) {
        Some(TempfileCandidate::Constructor(path.path.segments.first()?.ident.to_string()))
    } else {
        None
    }
}

fn ambient_builder(call: &ExprMethodCall, aliases: &TempfileAliases) -> Option<TempfileCandidate> {
    if call.method != "tempdir" || !is_builder_new(&call.receiver, aliases) {
        return None;
    }
    Some(TempfileCandidate::Builder("tempdir".to_owned()))
}

fn is_tempfile_function(path: &Path, aliases: &TempfileAliases) -> bool {
    let last = path.segments.last().map(|segment| segment.ident.to_string());
    let directly_qualified = path.segments.len() >= 2
        && path.segments.first().is_some_and(|segment| segment.ident == "tempfile")
        && last.as_deref() == Some("tempdir");
    directly_qualified
        || (path.segments.len() == 1
            && last.is_some_and(|name| aliases.tempdir_functions.contains(&name)))
}

fn is_tempdir_new(path: &Path, aliases: &TempfileAliases) -> bool {
    if path.segments.last().is_none_or(|segment| segment.ident != "new") {
        return false;
    }
    let Some(owner) = path.segments.iter().nth_back(1).map(|segment| segment.ident.to_string()) else {
        return false;
    };
    (path.segments.len() >= 3 && path.segments.first().is_some_and(|segment| segment.ident == "tempfile") && owner == "TempDir")
        || (path.segments.len() == 2 && aliases.constructors.contains(&owner))
}

fn is_builder_new(expression: &Expr, aliases: &TempfileAliases) -> bool {
    let Expr::Call(call) = expression else {
        return false;
    };
    let Expr::Path(path) = call.func.as_ref() else {
        return false;
    };
    if path.path.segments.last().is_none_or(|segment| segment.ident != "new") {
        return false;
    }
    let Some(owner) = path.path.segments.iter().nth_back(1).map(|segment| segment.ident.to_string()) else {
        return false;
    };
    (path.path.segments.len() >= 3 && path.path.segments.first().is_some_and(|segment| segment.ident == "tempfile") && owner == "Builder")
        || (path.path.segments.len() == 2 && aliases.builders.contains(&owner))
}

fn is_args_tmpdir(expression: &Expr) -> bool {
    matches!(expression, Expr::Field(field) if is_args_tmpdir_field(field))
}

fn is_args_tmpdir_or_view(expression: &Expr) -> bool {
    is_args_tmpdir(expression)
        || matches!(expression, Expr::MethodCall(call)
            if matches!(call.method.to_string().as_str(), "as_deref" | "as_ref" | "clone")
                && is_args_tmpdir_or_view(&call.receiver))
}

fn is_args_tmpdir_field(field: &ExprField) -> bool {
    matches!(&field.member, syn::Member::Named(member) if member == "tmpdir")
        && matches!(field.base.as_ref(), Expr::Path(ExprPath { path, .. }) if path.is_ident("args"))
}

fn is_safe_tmpdir_fallback(call: &ExprMethodCall) -> bool {
    matches!(call.method.to_string().as_str(), "or" | "or_else" | "unwrap_or" | "unwrap_or_else")
        && call.args.iter().any(contains_configured_env_fallback)
}

fn contains_configured_env_fallback(expression: &Expr) -> bool {
    let mut visitor = EnvironmentFallbackVisitor::default();
    visitor.visit_expr(expression);
    visitor.found
}

#[derive(Default)]
struct EnvironmentFallbackVisitor {
    found: bool,
}

impl<'ast> Visit<'ast> for EnvironmentFallbackVisitor {
    fn visit_expr_call(&mut self, call: &'ast ExprCall) {
        if is_environment_call(call) {
            self.found = true;
        }
        visit::visit_expr_call(self, call);
    }
}

fn is_environment_call(call: &ExprCall) -> bool {
    let Expr::Path(path) = call.func.as_ref() else {
        return false;
    };
    matches!(path.path.segments.last().map(|segment| segment.ident.to_string()).as_deref(), Some("var" | "var_os"))
        && call.args.iter().any(contains_environment_constant)
}

fn contains_environment_constant(expression: &Expr) -> bool {
    match expression {
        Expr::Path(path) => path.path.segments.last().is_some_and(|segment| segment.ident == ENV_TMPDIR_CONSTANT),
        Expr::Reference(reference) => contains_environment_constant(&reference.expr),
        Expr::Paren(paren) => contains_environment_constant(&paren.expr),
        _ => false,
    }
}

fn line_for_occurrence(source: &str, needle: &str, occurrence: &mut usize) -> Result<u32, LintError> {
    let target = *occurrence;
    *occurrence += 1;
    source
        .lines()
        .enumerate()
        .filter(|(_, line)| line.contains(needle))
        .nth(target)
        .and_then(|(index, _)| u32::try_from(index + 1).ok())
        .ok_or_else(|| LintError::new(format!("cannot locate policy expression {needle:?}")))
}

fn source_line(source: &str, line: u32) -> Result<&str, LintError> {
    source
        .lines()
        .nth(usize::try_from(line.saturating_sub(1)).map_err(|_| LintError::new("line number does not fit usize"))?)
        .ok_or_else(|| LintError::new(format!("cannot read source line {line}")))
}

#[cfg(test)]
mod tests {
    use super::{
        TempfileAliases, ambient_builder, ambient_constructor, contains_configured_env_fallback,
        is_safe_tmpdir_fallback, is_args_tmpdir_or_view,
    };

    #[test]
    fn recognizes_qualified_and_aliased_tempfile_shapes() {
        let file = syn::parse_file(
            "use tempfile::{tempdir as make_dir, Builder as TempBuilder, TempDir as Directory};\n\
             fn run() { let _ = make_dir(); let _ = Directory::new(); let _ = TempBuilder::new().tempdir(); }",
        )
        .expect("valid fixture");
        let aliases = TempfileAliases::from_file(&file);
        let calls: Vec<_> = file
            .items
            .iter()
            .filter_map(|item| match item { syn::Item::Fn(function) => Some(&function.block.stmts), _ => None })
            .flatten()
            .filter_map(|statement| match statement { syn::Stmt::Local(local) => local.init.as_ref().map(|init| init.expr.as_ref()), _ => None })
            .collect();
        assert!(matches!(calls[0], syn::Expr::Call(call) if ambient_constructor(call, &aliases).is_some()));
        assert!(matches!(calls[1], syn::Expr::Call(call) if ambient_constructor(call, &aliases).is_some()));
        assert!(matches!(calls[2], syn::Expr::MethodCall(call) if ambient_builder(call, &aliases).is_some()));
    }

    #[test]
    fn requires_the_configured_environment_constant() {
        let safe = syn::parse_str("std::env::var_os(config::ENV_IMPLEMENT_TMPDIR)").expect("valid expression");
        let unsafe_value = syn::parse_str("std::env::var_os(\"IMPLEMENT_TMPDIR\")").expect("valid expression");
        assert!(contains_configured_env_fallback(&safe));
        assert!(!contains_configured_env_fallback(&unsafe_value));
    }

    #[test]
    fn recognizes_option_fallback_closures() {
        let expression = syn::parse_str(
            "args.tmpdir.or_else(|| std::env::var_os(config::ENV_IMPLEMENT_TMPDIR))",
        )
        .expect("valid expression");
        let syn::Expr::MethodCall(call) = expression else {
            panic!("expected method call");
        };
        assert!(is_safe_tmpdir_fallback(&call));
    }

    #[test]
    fn recognizes_borrowed_tmpdir_option_views() {
        let expression = syn::parse_str("args.tmpdir.as_deref()")
            .expect("valid expression");
        let syn::Expr::MethodCall(call) = expression else {
            panic!("expected method call");
        };
        assert!(is_args_tmpdir_or_view(&syn::Expr::MethodCall(call)));
    }
}
