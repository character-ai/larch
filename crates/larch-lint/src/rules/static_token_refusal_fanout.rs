//! Flag functions that fan one static refusal token out across many branches.

use std::{
    collections::{BTreeMap, BTreeSet},
    path::{Path, PathBuf},
};

use syn::{
    Attribute, Block, Expr, ExprCall, ExprClosure, ExprMethodCall, Fields, Item, ItemConst,
    ItemStruct, Meta, Pat, Type, Visibility,
    spanned::Spanned,
    visit::{self, Visit},
};

use crate::{
    Finding, LintError, PathSelector, Repository, Rule, RuleDispatchPriority, RuleMetadata,
    RuleOutput,
    metadata::{GrandfatheredFinding, grandfathered_findings},
    suppression::reason as suppression_reason,
    syntax::RustSyntax,
};

use super::syn_helpers;

const NAME: &str = "static-token-refusal-fanout";
const DESCRIPTION: &str =
    "Flag functions that return one static refusal token from three or more distinct branches";
const LEDGER_PATH: &str =
    "crates/larch-lint/migration-ledger/static-token-refusal-fanout.toml";
const SUPPRESSION: &str = "lint-static-token-refusal-fanout";
const RUST_SOURCES: &[&str] = &["crates/*/src/**/*.rs"];

pub static METADATA: RuleMetadata = RuleMetadata::new(NAME, DESCRIPTION, LEDGER_PATH);

#[derive(Debug)]
pub struct StaticTokenRefusalFanoutRule;

pub static RULE: StaticTokenRefusalFanoutRule = StaticTokenRefusalFanoutRule;

impl Rule for StaticTokenRefusalFanoutRule {
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
        let baseline = grandfathered_findings(repository, LEDGER_PATH, NAME)?;
        let sources = load_sources(repository)?;
        let mut types = BTreeMap::<String, BTreeSet<String>>::new();
        for source in &sources {
            walk_items(&source.syntax.file().items, &mut |item| {
                if let Item::Struct(item) = item
                    && is_refusal_type(item)
                {
                    let _ = types
                        .entry(source.crate_name.clone())
                        .or_default()
                        .insert(item.ident.to_string());
                }
            });
        }
        let mut constants = BTreeMap::<String, BTreeSet<String>>::new();
        for source in &sources {
            let crate_types = types.get(&source.crate_name).cloned().unwrap_or_default();
            walk_items(&source.syntax.file().items, &mut |item| {
                if let Item::Const(item) = item
                    && is_refusal_constant(item, &crate_types)
                {
                    let _ = constants
                        .entry(source.crate_name.clone())
                        .or_default()
                        .insert(item.ident.to_string());
                }
            });
        }

        let mut violations = Vec::new();
        for source in &sources {
            let crate_constants = constants.get(&source.crate_name).cloned().unwrap_or_default();
            let mut visitor = FunctionVisitor::new(&crate_constants);
            visitor.visit_file(source.syntax.file());
            violations.extend(analyze_functions(
                &source.path,
                &source.text,
                visitor.functions,
            )?);
        }
        Ok(RuleOutput::from_findings(apply_baseline(violations, baseline)))
    }
}

crate::register_rule!(METADATA, RULE);

struct SourceFile {
    path: String,
    crate_name: String,
    text: String,
    syntax: RustSyntax,
}

fn load_sources(repository: &Repository) -> Result<Vec<SourceFile>, LintError> {
    let selector = PathSelector::new(RUST_SOURCES, &[])?;
    let mut sources: Vec<SourceFile> = selector
        .select(repository)
        .into_iter()
        .map(|path| {
            let text = repository.read_utf8(path)?.to_string();
            let crate_name = path
                .as_str()
                .split('/')
                .nth(1)
                .ok_or_else(|| LintError::new(format!("{path}: missing crate path component")))?
                .to_owned();
            let syntax = RustSyntax::parse(path.as_str(), &text)?;
            Ok(SourceFile {
                path: path.as_str().to_owned(),
                crate_name,
                text,
                syntax,
            })
        })
        .collect::<Result<_, _>>()?;
    let excluded: BTreeSet<String> = sources
        .iter()
        .flat_map(out_of_line_test_paths)
        .collect();
    sources.retain(|source| !excluded.contains(&source.path));
    Ok(sources)
}

fn out_of_line_test_paths(source: &SourceFile) -> Vec<String> {
    let source_path = Path::new(&source.path);
    let parent = source_path.parent().unwrap_or_else(|| Path::new(""));
    let stem = source_path.file_stem().and_then(|stem| stem.to_str()).unwrap_or("");
    let default_parent = if matches!(stem, "lib" | "main" | "mod") {
        parent.to_path_buf()
    } else {
        parent.join(stem)
    };
    source
        .syntax
        .file()
        .items
        .iter()
        .filter_map(|item| match item {
            Item::Mod(module)
                if module.content.is_none() && syn_helpers::has_cfg_test(&module.attrs) =>
            {
                Some((module, explicit_module_path(&module.attrs)))
            }
            _ => None,
        })
        .flat_map(|(module, explicit)| {
            explicit.map_or_else(
                || {
                    vec![
                        default_parent.join(format!("{}.rs", module.ident)),
                        default_parent.join(module.ident.to_string()).join("mod.rs"),
                    ]
                },
                |path| vec![parent.join(path)],
            )
        })
        .map(|path| path.to_string_lossy().replace('\\', "/"))
        .collect()
}

fn explicit_module_path(attributes: &[Attribute]) -> Option<PathBuf> {
    attributes.iter().find_map(|attribute| match &attribute.meta {
        Meta::NameValue(value) if value.path.is_ident("path") => {
            syn_helpers::string_literal(&value.value).map(PathBuf::from)
        }
        _ => None,
    })
}

fn walk_items(items: &[Item], visit_item: &mut impl FnMut(&Item)) {
    for item in items {
        if let Item::Mod(module) = item {
            if syn_helpers::has_cfg_test(&module.attrs) {
                continue;
            }
            if let Some((_, nested)) = &module.content {
                walk_items(nested, visit_item);
            }
        }
        visit_item(item);
    }
}

fn is_refusal_type(item: &ItemStruct) -> bool {
    let Fields::Unnamed(fields) = &item.fields else {
        return false;
    };
    let Some(field) = fields.unnamed.first().filter(|_| fields.unnamed.len() == 1) else {
        return false;
    };
    let Type::Reference(reference) = &field.ty else {
        return false;
    };
    matches!(item.vis, Visibility::Public(_))
        && reference.mutability.is_none()
        && reference.lifetime.as_ref().is_some_and(|life| life.ident == "static")
        && type_ident(&reference.elem).as_deref() == Some("str")
}

fn is_refusal_constant(item: &ItemConst, types: &BTreeSet<String>) -> bool {
    let Some(type_name) = type_ident(&item.ty).filter(|name| types.contains(name)) else {
        return false;
    };
    let Expr::Call(call) = peel_expr(&item.expr) else {
        return false;
    };
    matches!(item.vis, Visibility::Public(_))
        && path_ident(&call.func).is_some_and(|name| name == type_name)
        && call.args.len() == 1
        && call
            .args
            .first()
            .is_some_and(|argument| syn_helpers::string_literal(argument).is_some())
}

fn type_ident(item: &Type) -> Option<String> {
    let Type::Path(path) = item else { return None };
    (path.qself.is_none() && path.path.segments.len() == 1)
        .then(|| path.path.segments[0].ident.to_string())
}

fn path_ident(expression: &Expr) -> Option<String> {
    let Expr::Path(path) = peel_expr(expression) else {
        return None;
    };
    path.path.segments.last().map(|segment| segment.ident.to_string())
}

fn peel_expr(mut expression: &Expr) -> &Expr {
    loop {
        expression = match expression {
            Expr::Group(group) => &group.expr,
            Expr::Paren(paren) => &paren.expr,
            _ => return expression,
        };
    }
}

#[derive(Debug)]
struct Violation {
    key: GrandfatheredFinding,
    line: u32,
    count: usize,
}

fn apply_baseline(
    violations: Vec<Violation>,
    mut baseline: BTreeSet<GrandfatheredFinding>,
) -> Vec<Finding> {
    let mut findings = Vec::new();
    for violation in violations {
        if baseline.remove(&violation.key) {
            continue;
        }
        findings.push(Finding::new(
            &violation.key.path,
            violation.line,
            format!(
                "{} returns {} from {} distinct branches; give each branch its own reason or name the offending element",
                violation.key.function, violation.key.constant, violation.count
            ),
        ));
    }
    findings.extend(baseline.into_iter().map(|row| {
        Finding::new(
            LEDGER_PATH,
            1,
            format!(
                "stale grandfathered row for {}::{} {}",
                row.path, row.function, row.constant
            ),
        )
    }));
    findings
}

struct FunctionAnalysis {
    name: String,
    line: usize,
    sites: Vec<(String, usize)>,
}

struct FunctionVisitor<'constants> {
    constants: &'constants BTreeSet<String>,
    functions: Vec<FunctionAnalysis>,
}

impl<'constants> FunctionVisitor<'constants> {
    const fn new(constants: &'constants BTreeSet<String>) -> Self {
        Self {
            constants,
            functions: Vec::new(),
        }
    }

    fn scan(&mut self, name: &str, line: usize, block: &Block) {
        let mut sites = SiteVisitor::new(self.constants);
        sites.visit_block(block);
        self.functions.push(FunctionAnalysis {
            name: name.to_owned(),
            line,
            sites: sites.sites,
        });
    }
}

impl<'ast> Visit<'ast> for FunctionVisitor<'_> {
    fn visit_item_mod(&mut self, item: &'ast syn::ItemMod) {
        if !syn_helpers::has_cfg_test(&item.attrs) {
            visit::visit_item_mod(self, item);
        }
    }

    fn visit_item_fn(&mut self, item: &'ast syn::ItemFn) {
        self.scan(
            &item.sig.ident.to_string(),
            item.sig.fn_token.span.start().line,
            &item.block,
        );
        visit::visit_item_fn(self, item);
    }

    fn visit_impl_item_fn(&mut self, item: &'ast syn::ImplItemFn) {
        self.scan(
            &item.sig.ident.to_string(),
            item.sig.fn_token.span.start().line,
            &item.block,
        );
        visit::visit_impl_item_fn(self, item);
    }

    fn visit_trait_item_fn(&mut self, item: &'ast syn::TraitItemFn) {
        if let Some(block) = &item.default {
            self.scan(
                &item.sig.ident.to_string(),
                item.sig.fn_token.span.start().line,
                block,
            );
        }
        visit::visit_trait_item_fn(self, item);
    }
}

struct SiteVisitor<'constants> {
    constants: &'constants BTreeSet<String>,
    sites: Vec<(String, usize)>,
}

impl<'constants> SiteVisitor<'constants> {
    const fn new(constants: &'constants BTreeSet<String>) -> Self {
        Self {
            constants,
            sites: Vec::new(),
        }
    }

    fn record(&mut self, expression: &Expr, line: usize) {
        if let Some(name) = path_ident(expression).filter(|name| self.constants.contains(name)) {
            self.sites.push((name, line));
        }
    }
}

impl<'ast> Visit<'ast> for SiteVisitor<'_> {
    fn visit_item_fn(&mut self, _item: &'ast syn::ItemFn) {}
    fn visit_impl_item_fn(&mut self, _item: &'ast syn::ImplItemFn) {}
    fn visit_trait_item_fn(&mut self, _item: &'ast syn::TraitItemFn) {}

    fn visit_expr_call(&mut self, call: &'ast ExprCall) {
        if path_ident(&call.func).as_deref() == Some("Err")
            && call.args.len() == 1
            && let Some(argument) = call.args.first()
        {
            self.record(argument, call.span().start().line);
        }
        visit::visit_expr_call(self, call);
    }

    fn visit_expr_method_call(&mut self, call: &'ast ExprMethodCall) {
        if let Some(argument) = call.args.first().filter(|_| call.args.len() == 1) {
            match call.method.to_string().as_str() {
                "ok_or" => self.record(argument, call.span().start().line),
                "ok_or_else" => {
                    if let Some(closure) = closure(argument).filter(|closure| closure.inputs.is_empty()) {
                        self.record(&closure.body, call.span().start().line);
                    }
                }
                "map_err" => {
                    if let Some(closure) = closure(argument).filter(|closure| {
                        closure.inputs.len() == 1
                            && closure.inputs.first().is_some_and(ignored_pattern)
                    }) {
                        self.record(&closure.body, call.span().start().line);
                    }
                }
                _ => {}
            }
        }
        visit::visit_expr_method_call(self, call);
    }
}

fn closure(expression: &Expr) -> Option<&ExprClosure> {
    let Expr::Closure(closure) = peel_expr(expression) else {
        return None;
    };
    Some(closure)
}

fn ignored_pattern(pattern: &Pat) -> bool {
    matches!(pattern, Pat::Wild(_))
        || syn_helpers::pattern_name(pattern).is_some_and(|name| name.starts_with('_'))
}

fn analyze_functions(
    path: &str,
    source: &str,
    functions: Vec<FunctionAnalysis>,
) -> Result<Vec<Violation>, LintError> {
    let lines: Vec<&str> = source.lines().collect();
    let mut violations = Vec::new();
    for function in functions {
        let mut counts = BTreeMap::<String, usize>::new();
        for (constant, line) in function.sites {
            let text = lines
                .get(line.saturating_sub(1))
                .ok_or_else(|| LintError::new(format!("{path}: source line {line} is missing")))?;
            if suppression_reason(text, SUPPRESSION)?.is_none() {
                *counts.entry(constant).or_default() += 1;
            }
        }
        for (constant, count) in counts.into_iter().filter(|(_, count)| *count >= 3) {
            violations.push(Violation {
                key: GrandfatheredFinding {
                    path: path.to_owned(),
                    function: function.name.clone(),
                    constant,
                },
                line: u32::try_from(function.line)
                    .map_err(|_| LintError::new("source line number exceeds u32"))?,
                count,
            });
        }
    }
    Ok(violations)
}
