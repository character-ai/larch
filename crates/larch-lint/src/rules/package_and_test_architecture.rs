//! Enforce future-state Rust package, test, and report-renderer architecture.
//!
//! # Crate survey and module-graph gap analysis (issue #7625)
//!
//! | Need | Candidates | Selection |
//! |------|------------|-----------|
//! | Workspace package graph | workspace `cargo_metadata`, `guppy` | Use `cargo_metadata`. It exposes direct package dependencies and dependency kinds without adding guppy's broader graph-analysis surface. |
//! | Rust syntax and test attributes | workspace `syn`, `ra_ap_syntax` | Use `syn`, already selected by #7604. It retains test attributes and source identities needed for findings. |
//! | Rust module graph | maintained module-graph crates, `ra_ap_syntax` | No selected workspace dependency provides a stable, Cargo-aware module graph with `#[path]`, re-exports, and test cfg evaluation. Adding one is prohibited for an independent C13 leaf by #7632's dependency contract. The rules therefore do not infer a bespoke complete module graph: Cargo owns package edges, while `syn` checks source-local test and renderer contracts. This is sufficient for the approved architecture and fails closed on invalid Rust. |
//!
//! The Rust corpus starts with zero accepted debt. The legacy Python rules stay
//! active until their Python scopes are extinct.

use std::collections::BTreeSet;

use cargo_metadata::{DependencyKind, MetadataCommand};
use syn::{
    parse::Parser,
    punctuated::Punctuated,
    visit::{self, Visit},
    Attribute, ExprPath, ItemFn, ItemMod, Meta, Path, Token, UseTree,
};

use crate::{
    Finding, LintError, PathSelector, RepoPath, Repository, Rule, RuleMetadata, RuleOutput,
    suppression,
    syntax::RustSyntax,
};

const PACKAGE_LAYERING_NAME: &str = "layering";
const PACKAGE_LAYERING_DESCRIPTION: &str =
    "Require Rust workspace packages to follow the larch dependency tiers";
const WORKSPACE_DEPENDENCY_POLICY_NAME: &str = "workspace-dependency-policy";
const WORKSPACE_DEPENDENCY_POLICY_DESCRIPTION: &str =
    "Require member dependencies to inherit versions and features from the workspace";
const TEST_LAYOUT_NAME: &str = "flat-tests";
const TEST_LAYOUT_DESCRIPTION: &str =
    "Require Rust tests to use crate-local cfg(test) modules or integration tests";
const RENDERER_GOLDEN_TESTS_NAME: &str = "renderer-golden-tests";
const RENDERER_GOLDEN_TESTS_DESCRIPTION: &str =
    "Require Rust report renderer helpers to have explicit golden-test references";
const RUST_SOURCES: &[&str] = &["crates/**/*.rs"];

pub static PACKAGE_LAYERING_METADATA: RuleMetadata = RuleMetadata::new(
    PACKAGE_LAYERING_NAME,
    PACKAGE_LAYERING_DESCRIPTION,
    "crates/larch-lint/migration-ledger/layering.toml",
);
pub static TEST_LAYOUT_METADATA: RuleMetadata = RuleMetadata::new(
    TEST_LAYOUT_NAME,
    TEST_LAYOUT_DESCRIPTION,
    "crates/larch-lint/migration-ledger/flat-tests.toml",
);
pub static WORKSPACE_DEPENDENCY_POLICY_METADATA: RuleMetadata = RuleMetadata::new(
    WORKSPACE_DEPENDENCY_POLICY_NAME,
    WORKSPACE_DEPENDENCY_POLICY_DESCRIPTION,
    "crates/larch-lint/migration-ledger/workspace-dependency-policy.toml",
);
pub static RENDERER_GOLDEN_TESTS_METADATA: RuleMetadata = RuleMetadata::new(
    RENDERER_GOLDEN_TESTS_NAME,
    RENDERER_GOLDEN_TESTS_DESCRIPTION,
    "crates/larch-lint/migration-ledger/renderer-golden-tests.toml",
);

#[derive(Debug)]
pub struct PackageLayeringRule;
#[derive(Debug)]
pub struct WorkspaceDependencyPolicyRule;
#[derive(Debug)]
pub struct TestLayoutRule;
#[derive(Debug)]
pub struct RendererGoldenTestsRule;

pub static PACKAGE_LAYERING_RULE: PackageLayeringRule = PackageLayeringRule;
pub static WORKSPACE_DEPENDENCY_POLICY_RULE: WorkspaceDependencyPolicyRule =
    WorkspaceDependencyPolicyRule;
pub static TEST_LAYOUT_RULE: TestLayoutRule = TestLayoutRule;
pub static RENDERER_GOLDEN_TESTS_RULE: RendererGoldenTestsRule = RendererGoldenTestsRule;

impl Rule for PackageLayeringRule {
    fn name(&self) -> &'static str { PACKAGE_LAYERING_NAME }
    fn description(&self) -> &'static str { PACKAGE_LAYERING_DESCRIPTION }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        if !repository
            .paths()
            .iter()
            .any(|path| path.as_str() == "Cargo.toml")
        {
            return Ok(RuleOutput::clean());
        }
        let metadata = MetadataCommand::new()
            .current_dir(repository.root())
            .no_deps()
            .exec()
            .map_err(|error| LintError::new(format!("cannot read Cargo workspace metadata: {error}")))?;
        let workspace_names: BTreeSet<_> = metadata
            .workspace_packages()
            .into_iter()
            .map(|package| package.name.as_str())
            .collect();
        let mut findings = Vec::new();
        for package in metadata.workspace_packages() {
            if !known_workspace_package(&package.name) {
                findings.push(Finding::new(
                    manifest_display_path(repository, package.manifest_path.as_std_path()),
                    1,
                    format!(
                        "package {} has no declared layer in ARCHITECTURE.md",
                        package.name
                    ),
                ));
            }
            for dependency in &package.dependencies {
                if dependency.kind == DependencyKind::Development
                    || !workspace_names.contains(dependency.name.as_str())
                {
                    continue;
                }
                if !workspace_dependency_allowed(&package.name, &dependency.name) {
                    findings.push(Finding::new(
                        manifest_display_path(repository, package.manifest_path.as_std_path()),
                        1,
                        format!(
                            "package {} may not depend on {}",
                            package.name, dependency.name
                        ),
                    ));
                }
            }
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

impl Rule for WorkspaceDependencyPolicyRule {
    fn name(&self) -> &'static str {
        WORKSPACE_DEPENDENCY_POLICY_NAME
    }

    fn description(&self) -> &'static str {
        WORKSPACE_DEPENDENCY_POLICY_DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let selector = PathSelector::new(&["crates/*/Cargo.toml"], &[])?;
        let mut findings = Vec::new();
        let root_path = RepoPath::from_trusted("Cargo.toml");
        if repository.paths().contains(&root_path) {
            let content = repository.read_utf8(&root_path)?;
            let manifest = parse_manifest(&root_path, &content)?;
            findings.extend(workspace_dependency_default_findings(&manifest));
        }
        for path in selector.select(repository) {
            let content = repository.read_utf8(path)?;
            let manifest = parse_manifest(path, &content)?;
            if manifest.get("package").is_some() && !package_version_is_inherited(&manifest) {
                findings.push(Finding::new(
                    path.as_str(),
                    1,
                    "package version must inherit from [workspace.package]",
                ));
            }
            for (dependency, value) in manifest_dependencies(&manifest) {
                let inherited = value
                    .as_table()
                    .and_then(|settings| settings.get("workspace"))
                    .and_then(toml::Value::as_bool)
                    .is_some_and(|workspace| workspace);
                if !inherited {
                    findings.push(Finding::new(
                        path.as_str(),
                        1,
                        format!(
                            "dependency {dependency} must inherit its version and features from [workspace.dependencies]"
                        ),
                    ));
                }
            }
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

impl Rule for TestLayoutRule {
    fn name(&self) -> &'static str { TEST_LAYOUT_NAME }
    fn description(&self) -> &'static str { TEST_LAYOUT_DESCRIPTION }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let selector = PathSelector::new(RUST_SOURCES, &[])?;
        let mut findings = Vec::new();
        for path in selector.select(repository) {
            if is_fixture(path.as_str()) {
                continue;
            }
            let source = repository.read_utf8(path)?;
            let syntax = RustSyntax::parse(path.as_str(), &source)?;
            let integration_test = is_integration_test(path.as_str());
            let mut visitor = TestLayoutVisitor::new(integration_test);
            visitor.visit_file(syntax.file());
            findings.extend(resolve_source_findings(
                path.as_str(),
                &source,
                visitor.pending,
                "lint-test-layout",
            )?);
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

impl Rule for RendererGoldenTestsRule {
    fn name(&self) -> &'static str { RENDERER_GOLDEN_TESTS_NAME }
    fn description(&self) -> &'static str { RENDERER_GOLDEN_TESTS_DESCRIPTION }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let selector = PathSelector::new(RUST_SOURCES, &[])?;
        let mut candidates = Vec::new();
        let mut references = BTreeSet::new();
        for path in selector.select(repository) {
            if is_fixture(path.as_str()) {
                continue;
            }
            let source = repository.read_utf8(path)?;
            let syntax = RustSyntax::parse(path.as_str(), &source)?;
            if is_report_source(path.as_str()) {
                let mut visitor = RendererVisitor::default();
                visitor.visit_file(syntax.file());
                candidates.extend(visitor.candidates.into_iter().map(|candidate| Candidate {
                    path: path.as_str().to_owned(),
                    line: candidate.line,
                    name: candidate.name,
                }));
            }
            if is_test_source(path.as_str()) {
                let mut visitor = RendererTestReferenceVisitor::new(is_integration_test(path.as_str()));
                visitor.visit_file(syntax.file());
                references.extend(visitor.references);
            }
        }
        let mut findings = Vec::new();
        for candidate in candidates {
            if references.contains(&candidate.name) {
                continue;
            }
            if suppression_on_line(&repository.read_utf8(&RepoPath::from_trusted(&candidate.path))?, candidate.line, "lint-renderer-golden-tests")? {
                continue;
            }
            findings.push(Finding::new(
                candidate.path,
                candidate.line,
                format!("renderer helper {} lacks an explicit golden-test reference", candidate.name),
            ));
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(PACKAGE_LAYERING_METADATA, PACKAGE_LAYERING_RULE);
crate::register_rule!(
    WORKSPACE_DEPENDENCY_POLICY_METADATA,
    WORKSPACE_DEPENDENCY_POLICY_RULE
);
crate::register_rule!(TEST_LAYOUT_METADATA, TEST_LAYOUT_RULE);
crate::register_rule!(RENDERER_GOLDEN_TESTS_METADATA, RENDERER_GOLDEN_TESTS_RULE);

fn known_workspace_package(name: &str) -> bool {
    matches!(
        name,
        "larch-core"
            | "larch-adapters"
            | "larch-cli"
            | "larch-lint"
            | "larch-test-support"
    )
}

fn workspace_dependency_allowed(importer: &str, dependency: &str) -> bool {
    matches!(
        (importer, dependency),
        ("larch-adapters" | "larch-test-support", "larch-core")
            | ("larch-cli", "larch-core" | "larch-adapters" | "larch-lint")
    )
}

fn manifest_dependencies(manifest: &toml::Table) -> Vec<(&str, &toml::Value)> {
    let mut dependencies = Vec::new();
    append_dependency_tables(manifest, &mut dependencies);
    if let Some(targets) = manifest.get("target").and_then(toml::Value::as_table) {
        for target in targets.values().filter_map(toml::Value::as_table) {
            append_dependency_tables(target, &mut dependencies);
        }
    }
    dependencies
}

fn append_dependency_tables<'a>(
    table: &'a toml::Table,
    dependencies: &mut Vec<(&'a str, &'a toml::Value)>,
) {
    for section in ["dependencies", "dev-dependencies", "build-dependencies"] {
        if let Some(entries) = table.get(section).and_then(toml::Value::as_table) {
            dependencies.extend(entries.iter().map(|(name, value)| (name.as_str(), value)));
        }
    }
}

fn parse_manifest(path: &RepoPath, content: &str) -> Result<toml::Table, LintError> {
    toml::from_str(content)
        .map_err(|error| LintError::new(format!("{}: invalid TOML: {error}", path.as_str())))
}

fn package_version_is_inherited(manifest: &toml::Table) -> bool {
    manifest
        .get("package")
        .and_then(toml::Value::as_table)
        .and_then(|package| package.get("version"))
        .and_then(toml::Value::as_table)
        .and_then(|version| version.get("workspace"))
        .and_then(toml::Value::as_bool)
        .is_some_and(|workspace| workspace)
}

fn workspace_dependency_default_findings(manifest: &toml::Table) -> Vec<Finding> {
    manifest
        .get("workspace")
        .and_then(toml::Value::as_table)
        .and_then(|workspace| workspace.get("dependencies"))
        .and_then(toml::Value::as_table)
        .into_iter()
        .flat_map(toml::Table::iter)
        .filter_map(|(name, value)| {
            let settings = value.as_table()?;
            if settings.contains_key("path")
                || settings
                    .get("default-features")
                    .and_then(toml::Value::as_bool)
                    .is_some_and(|enabled| !enabled)
            {
                return None;
            }
            Some(Finding::new(
                "Cargo.toml",
                1,
                format!(
                    "workspace dependency {name} must set default-features = false"
                ),
            ))
        })
        .collect()
}

fn manifest_display_path(repository: &Repository, manifest: &std::path::Path) -> String {
    manifest
        .strip_prefix(repository.root())
        .map_or_else(|_| manifest.display().to_string(), |path| path.display().to_string())
}

fn is_fixture(path: &str) -> bool {
    path.split('/').any(|part| part == "fixtures")
}

fn is_integration_test(path: &str) -> bool {
    let parts: Vec<_> = path.split('/').collect();
    matches!(parts.as_slice(), ["crates", _, "tests", ..])
}

fn is_test_source(path: &str) -> bool {
    is_integration_test(path) || path.contains("/src/")
}

fn is_report_source(path: &str) -> bool {
    path.starts_with("crates/larch-report/src/")
}

#[derive(Clone, Debug)]
struct PendingFinding {
    line: u32,
    message: &'static str,
}

struct TestLayoutVisitor {
    integration_test: bool,
    cfg_test_depth: usize,
    pending: Vec<PendingFinding>,
}

impl TestLayoutVisitor {
    const fn new(integration_test: bool) -> Self {
        Self { integration_test, cfg_test_depth: 0, pending: Vec::new() }
    }
}

impl<'ast> Visit<'ast> for TestLayoutVisitor {
    fn visit_item_mod(&mut self, node: &'ast ItemMod) {
        let cfg_test = has_cfg_test(&node.attrs);
        if cfg_test {
            self.cfg_test_depth += 1;
        }
        visit::visit_item_mod(self, node);
        if cfg_test {
            self.cfg_test_depth -= 1;
        }
    }

    fn visit_item_fn(&mut self, node: &'ast ItemFn) {
        if has_test_attr(&node.attrs) && !self.integration_test && self.cfg_test_depth == 0 {
            self.pending.push(PendingFinding {
                line: line_from_span(node.sig.ident.span().start().line),
                message: "test is outside a #[cfg(test)] crate-local module",
            });
        }
        visit::visit_item_fn(self, node);
    }
}

#[derive(Default)]
struct RendererVisitor {
    candidates: Vec<RendererCandidate>,
}

#[derive(Clone, Debug)]
struct RendererCandidate {
    line: u32,
    name: String,
}

impl<'ast> Visit<'ast> for RendererVisitor {
    fn visit_item_fn(&mut self, node: &'ast ItemFn) {
        let name = node.sig.ident.to_string();
        if is_renderer_name(&name) {
            self.candidates.push(RendererCandidate {
                line: line_from_span(node.sig.ident.span().start().line),
                name,
            });
        }
    }
}

fn has_test_attr(attributes: &[Attribute]) -> bool {
    attributes.iter().any(|attribute| {
        attribute
            .path()
            .segments
            .last()
            .is_some_and(|segment| segment.ident == "test")
    })
}

fn has_cfg_test(attributes: &[Attribute]) -> bool {
    attributes.iter().any(|attribute| {
        attribute.path().is_ident("cfg")
            && attribute
                .meta
                .require_list()
                .is_ok_and(|list| cfg_tokens_mention_test(&list.tokens))
    })
}

fn cfg_tokens_mention_test(tokens: &proc_macro2::TokenStream) -> bool {
    syn::parse2::<Meta>(tokens.clone()).is_ok_and(|meta| meta_mentions_test(&meta))
}

fn meta_mentions_test(meta: &Meta) -> bool {
    if meta.path().is_ident("test") {
        return true;
    }
    let Meta::List(list) = meta else {
        return false;
    };
    Punctuated::<Meta, Token![,]>::parse_terminated
        .parse2(list.tokens.clone())
        .is_ok_and(|nested| nested.iter().any(meta_mentions_test))
}

fn is_renderer_name(name: &str) -> bool {
    name.starts_with("render_") || name.starts_with("_render_") || name.ends_with("_rows")
}

fn line_from_span(line: usize) -> u32 {
    u32::try_from(line).unwrap_or(u32::MAX)
}

fn resolve_source_findings(
    path: &str,
    source: &str,
    pending: Vec<PendingFinding>,
    token: &str,
) -> Result<Vec<Finding>, LintError> {
    let mut findings = Vec::new();
    for pending in pending {
        if !suppression_on_line(source, pending.line, token)? {
            findings.push(Finding::new(path, pending.line, pending.message));
        }
    }
    Ok(findings)
}

fn suppression_on_line(source: &str, line: u32, token: &str) -> Result<bool, LintError> {
    let index = usize::try_from(line.saturating_sub(1))
        .map_err(|_| LintError::new("source line number cannot fit usize"))?;
    source
        .lines()
        .nth(index)
        .map(|text| suppression::reason(text, token).map(|reason| reason.is_some()))
        .transpose()
        .map(|reason| reason.unwrap_or(false))
}

#[derive(Clone, Debug)]
struct Candidate {
    path: String,
    line: u32,
    name: String,
}

struct RendererTestReferenceVisitor {
    integration_test: bool,
    cfg_test_depth: usize,
    references: BTreeSet<String>,
}

impl RendererTestReferenceVisitor {
    const fn new(integration_test: bool) -> Self {
        Self { integration_test, cfg_test_depth: 0, references: BTreeSet::new() }
    }
}

impl<'ast> Visit<'ast> for RendererTestReferenceVisitor {
    fn visit_item_mod(&mut self, node: &'ast ItemMod) {
        let cfg_test = has_cfg_test(&node.attrs);
        if cfg_test {
            self.cfg_test_depth += 1;
        }
        visit::visit_item_mod(self, node);
        if cfg_test {
            self.cfg_test_depth -= 1;
        }
    }

    fn visit_path(&mut self, node: &'ast Path) {
        if self.integration_test || self.cfg_test_depth > 0 {
            self.references.extend(node.segments.iter().map(|segment| segment.ident.to_string()));
        }
        visit::visit_path(self, node);
    }

    fn visit_expr_path(&mut self, node: &'ast ExprPath) {
        if self.integration_test || self.cfg_test_depth > 0 {
            self.references.extend(node.path.segments.iter().map(|segment| segment.ident.to_string()));
        }
        visit::visit_expr_path(self, node);
    }

    fn visit_use_tree(&mut self, node: &'ast UseTree) {
        if self.integration_test || self.cfg_test_depth > 0 {
            collect_use_tree_identifiers(node, &mut self.references);
        }
        visit::visit_use_tree(self, node);
    }
}

fn collect_use_tree_identifiers(tree: &UseTree, references: &mut BTreeSet<String>) {
    match tree {
        UseTree::Path(path) => {
            references.insert(path.ident.to_string());
            collect_use_tree_identifiers(&path.tree, references);
        }
        UseTree::Name(name) => { references.insert(name.ident.to_string()); }
        UseTree::Rename(rename) => { references.insert(rename.ident.to_string()); }
        UseTree::Group(group) => {
            for tree in &group.items { collect_use_tree_identifiers(tree, references); }
        }
        UseTree::Glob(_) => {}
    }
}

#[cfg(test)]
mod tests {
    use super::{
        has_cfg_test, is_integration_test, is_renderer_name, known_workspace_package,
        workspace_dependency_allowed,
    };

    #[test]
    fn workspace_packages_and_edges_match_the_approved_architecture() {
        assert!(known_workspace_package("larch-core"));
        assert!(known_workspace_package("larch-adapters"));
        assert!(known_workspace_package("larch-cli"));
        assert!(known_workspace_package("larch-lint"));
        assert!(known_workspace_package("larch-test-support"));
        assert!(!known_workspace_package("larch-report"));
        assert!(workspace_dependency_allowed(
            "larch-adapters",
            "larch-core"
        ));
        assert!(workspace_dependency_allowed(
            "larch-cli",
            "larch-adapters"
        ));
        assert!(workspace_dependency_allowed(
            "larch-test-support",
            "larch-core"
        ));
        assert!(!workspace_dependency_allowed(
            "larch-core",
            "larch-adapters"
        ));
        assert!(workspace_dependency_allowed("larch-cli", "larch-lint"));
        assert!(!workspace_dependency_allowed("larch-lint", "larch-core"));
    }

    #[test]
    fn renderer_names_include_private_helpers_and_row_builders() {
        assert!(is_renderer_name("_render_progress"));
        assert!(is_renderer_name("render_progress"));
        assert!(is_renderer_name("vendor_rows"));
        assert!(!is_renderer_name("format_progress"));
    }

    #[test]
    fn cfg_test_accepts_the_standard_module_attribute() {
        let file = syn::parse_file("#[cfg(test)] mod tests {}").expect("parse fixture");
        let syn::Item::Mod(module) = &file.items[0] else { panic!("expected module"); };
        assert!(has_cfg_test(&module.attrs));
    }

    #[test]
    fn cfg_test_accepts_compound_test_conditions() {
        let file = syn::parse_file("#[cfg(any(test, feature = \"fixture\"))] mod tests {}")
            .expect("parse fixture");
        let syn::Item::Mod(module) = &file.items[0] else { panic!("expected module"); };
        assert!(has_cfg_test(&module.attrs));
    }

    #[test]
    fn integration_tests_must_be_at_the_crate_root_tests_directory() {
        assert!(is_integration_test("crates/larch-core/tests/api.rs"));
        assert!(!is_integration_test("crates/larch-core/src/tests/api.rs"));
    }
}
