//! Enforce service-adapter ownership and runtime CLI independence.
//!
//! Concrete GitHub and Google clients, arbitrary service request surfaces, and
//! the `gcloud` service CLI stay confined to `crates/larch-adapters`. Production
//! skills and scripts must not invoke `gcloud` or leak a service credential into
//! a child environment. The service inventories must name each concrete-client
//! owner so ownership never drifts away from its documentation. The clean-install
//! `gh` bootstrap in `scripts/larch.sh` is a separate installer surface and is
//! not a runtime service caller; see `docs/github-service-inventory.md`.

use std::{
    collections::{BTreeMap, BTreeSet},
    path::Path as StdPath,
    sync::LazyLock,
};

use proc_macro2::{TokenStream, TokenTree};
use regex::Regex;
use serde::Deserialize;
use syn::{Attribute, ItemFn, ItemImpl, ItemMod, ItemUse, LitStr, Macro, UseTree, visit};
use tree_sitter::Node;

use crate::{
    Finding, LintError, PathSelector, RepoPath, Repository, Rule, RuleMetadata, RuleOutput,
    suppression,
    syntax::{FenceState, MarkdownDocument, RustSyntax, parse_bash},
};

use super::{larch_runtime_entrypoint::is_production_surface, syn_helpers};

const NAME: &str = "service-ownership";
const DESCRIPTION: &str = "Confine service clients, request surfaces, and CLIs to the adapter boundary";
const SUPPRESSION: &str = "lint-service-ownership";

const ADAPTERS_PREFIX: &str = "crates/larch-adapters/";
const GITHUB_INVENTORY: &str = "docs/github-service-inventory.md";
const GOOGLE_INVENTORY: &str = "docs/google-service-inventory.md";
const COMMAND_REGISTRY: &str = "crates/larch-lint/data/command-registry.toml";
const INVENTORY_START: &str = "<!-- github-service-ownership:start -->";
const INVENTORY_END: &str = "<!-- github-service-ownership:end -->";
const INVENTORY_HEADER: &str = "operation\tadapter_owner\tcurrent_owner\tmigration_issues\timplementation_parity\tconsumer_cutover\tpython_removal\tcommands";
const CHIEF_MIGRATION_OWNER: &str = "#7687";
const REQUIRED_OPERATION_GROUPS: [&str; 10] = [
    "actions",
    "attestations",
    "comments",
    "issue-dependencies",
    "issues",
    "labels",
    "pull-requests",
    "release-consumers",
    "releases",
    "repository-metadata",
];

/// Concrete HTTP and service client crates that only the adapter crate may use.
const CLIENT_CRATES: [&str; 7] = ["octocrab", "reqwest", "hyper", "ureq", "isahc", "surf", "curl"];
/// Service request hosts that must not appear as string literals outside the adapter.
const SERVICE_HOSTS: [&str; 4] = [
    "api.github.com",
    "uploads.github.com",
    "githubusercontent.com",
    "googleapis.com",
];
/// Service credentials that must never enter a spawned child environment.
const CHILD_CREDENTIALS: [&str; 12] = [
    "AUTHORIZATION",
    "CLOUDSDK_AUTH_ACCESS_TOKEN",
    "CLOUDSDK_AUTH_REFRESH_TOKEN",
    "CLOUDSDK_CONFIG",
    "GH_ENTERPRISE_TOKEN",
    "LARCH_GH_TOKEN",
    "GH_TOKEN",
    "GITHUB_ENTERPRISE_TOKEN",
    "GITHUB_TOKEN",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_API_KEY",
    "GOOGLE_OAUTH_ACCESS_TOKEN",
];

const GCLOUD_MESSAGE: &str =
    "production runtime must not invoke the gcloud CLI; use the Rust Google adapter";
const DUPLICATE_GITHUB: &str =
    "duplicate concrete GitHub client owner; Octocrab must be constructed by one adapter module";
const DUPLICATE_GOOGLE: &str =
    "duplicate concrete Google client owner; google-cloud-auth must be used by one adapter module";
const GRAPHQL_MESSAGE: &str = "GraphQL document appears outside crates/larch-adapters";
const GENERIC_GITHUB_CREDENTIAL: &str =
    "GitHub service must not read caller-supplied GH_TOKEN or GITHUB_TOKEN as a credential fallback";

static GRAPHQL: LazyLock<Regex> = LazyLock::new(|| {
    // Allow a named operation and a variable or directive preamble before the
    // selection set, so `query GetRepo($owner:String!){...}` is recognized.
    Regex::new(r"(?s)^\s*(?:query|mutation|subscription)\b[^({]*[({]")
        .expect("GraphQL operation expression is valid")
});

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/service-ownership.toml",
);

#[derive(Debug)]
pub struct ServiceOwnershipRule;

pub static RULE: ServiceOwnershipRule = ServiceOwnershipRule;

crate::register_rule!(METADATA, RULE);

impl Rule for ServiceOwnershipRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let mut findings = Vec::new();
        check_non_adapter_rust(repository, &mut findings)?;
        let (github_owners, google_owners) = check_client_owners(repository, &mut findings)?;
        check_inventory(repository, GITHUB_INVENTORY, &github_owners, &mut findings)?;
        check_inventory(repository, GOOGLE_INVENTORY, &google_owners, &mut findings)?;
        check_github_operation_inventory(repository, &mut findings)?;
        check_shell_surfaces(repository, &mut findings)?;
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

#[derive(Debug, Deserialize)]
struct OwnershipLedger {
    #[serde(default)]
    commands: Vec<OwnershipCommand>,
}

#[derive(Debug, Deserialize)]
struct OwnershipCommand {
    domain: String,
    verb: String,
    owner: String,
    implementation_parity: String,
    consumer_cutover: String,
    python_removal: String,
    migration_issue: u64,
}

fn check_github_operation_inventory(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    let inventory_path = RepoPath::from_trusted(GITHUB_INVENTORY);
    if repository.paths().binary_search(&inventory_path).is_err() {
        return Ok(());
    }
    let content = repository.read_utf8(&inventory_path)?;
    let lines: Vec<&str> = content.lines().collect();
    let Some(start) = lines.iter().position(|line| line.trim() == INVENTORY_START) else {
        findings.push(Finding::new(
            GITHUB_INVENTORY,
            1,
            "GitHub service ownership matrix is missing",
        ));
        return Ok(());
    };
    let Some(relative_end) = lines[start + 1..]
        .iter()
        .position(|line| line.trim() == INVENTORY_END)
    else {
        findings.push(Finding::new(
            GITHUB_INVENTORY,
            to_u32(start + 1),
            "GitHub service ownership matrix is unterminated",
        ));
        return Ok(());
    };
    let end = start + 1 + relative_end;
    let ledger = read_ownership_commands(repository)?;
    let mut rows = BTreeSet::new();
    let mut saw_header = false;
    for (index, raw) in lines[start + 1..end].iter().enumerate() {
        let line_number = start + index + 2;
        let line = raw.trim();
        if line.is_empty() || line.starts_with("```") {
            continue;
        }
        if !saw_header {
            saw_header = true;
            if line != INVENTORY_HEADER {
                findings.push(Finding::new(
                    GITHUB_INVENTORY,
                    to_u32(line_number),
                    "GitHub service ownership matrix has an invalid header",
                ));
            }
            continue;
        }
        let columns: Vec<&str> = raw.split('\t').collect();
        if columns.len() != 8 {
            findings.push(Finding::new(
                GITHUB_INVENTORY,
                to_u32(line_number),
                "GitHub service ownership row must contain exactly eight tab-separated fields",
            ));
            continue;
        }
        let operation = columns[0].trim();
        if !rows.insert(operation.to_owned()) {
            findings.push(Finding::new(
                GITHUB_INVENTORY,
                to_u32(line_number),
                format!("duplicate GitHub service operation owner `{operation}`"),
            ));
        }
        validate_operation_row(repository, &ledger, &columns, line_number, findings);
    }
    if !saw_header {
        findings.push(Finding::new(
            GITHUB_INVENTORY,
            to_u32(start + 1),
            "GitHub service ownership matrix is empty",
        ));
    }
    for required in REQUIRED_OPERATION_GROUPS {
        if !rows.contains(required) {
            findings.push(Finding::new(
                GITHUB_INVENTORY,
                to_u32(start + 1),
                format!("GitHub service operation `{required}` is missing from the ownership matrix"),
            ));
        }
    }
    Ok(())
}

fn read_ownership_commands(
    repository: &Repository,
) -> Result<BTreeMap<String, OwnershipCommand>, LintError> {
    let path = RepoPath::from_trusted(COMMAND_REGISTRY);
    let content = repository.read_utf8(&path)?;
    let ledger: OwnershipLedger = toml::from_str(&content).map_err(|error| {
        LintError::new(format!("{COMMAND_REGISTRY}: invalid TOML: {error}"))
    })?;
    Ok(ledger
        .commands
        .into_iter()
        .map(|command| (format!("{} {}", command.domain, command.verb), command))
        .collect())
}

fn validate_operation_row(
    repository: &Repository,
    ledger: &BTreeMap<String, OwnershipCommand>,
    columns: &[&str],
    line_number: usize,
    findings: &mut Vec<Finding>,
) {
    let operation = columns[0].trim();
    let adapter = columns[1].trim();
    let owner = columns[2].trim();
    let migration_issues = columns[3].trim();
    let parity = columns[4].trim();
    let cutover = columns[5].trim();
    let removal = columns[6].trim();
    let selectors = columns[7].trim();
    if operation.is_empty() || !operation.bytes().all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-') {
        inventory_finding(line_number, "GitHub service operation key is invalid", findings);
    }
    let adapter_path = RepoPath::from_trusted(adapter);
    if !adapter.starts_with(ADAPTERS_PREFIX)
        || repository.paths().binary_search(&adapter_path).is_err()
    {
        inventory_finding(
            line_number,
            format!("GitHub service adapter owner `{adapter}` is not a tracked adapter path"),
            findings,
        );
    }
    if !matches!(owner, "python" | "rust" | "retired") {
        inventory_finding(line_number, "GitHub service current owner is invalid", findings);
    }
    let issues: BTreeSet<u64> = migration_issues
        .split(',')
        .filter_map(|value| value.strip_prefix('#')?.parse().ok())
        .collect();
    if issues.is_empty()
        || issues.len() != migration_issues.split(',').count()
        || migration_issues.split(',').any(|value| value == CHIEF_MIGRATION_OWNER)
    {
        inventory_finding(
            line_number,
            "GitHub service migration owner must name concrete issues and must not delegate to #7687",
            findings,
        );
    }
    if !matches!(parity, "pending" | "complete" | "not-applicable")
        || !matches!(cutover, "pending" | "complete")
        || !matches!(removal, "pending" | "complete")
    {
        inventory_finding(line_number, "GitHub service migration state is invalid", findings);
    }
    let (commands, unknown_selectors) = expand_inventory_selectors(selectors, ledger);
    for selector in unknown_selectors {
        inventory_finding(
            line_number,
            format!("GitHub service ownership row names unknown command selector `{selector}`"),
            findings,
        );
    }
    if commands.is_empty() {
        inventory_finding(
            line_number,
            "GitHub service ownership row names no production command",
            findings,
        );
        return;
    }
    for command in commands {
        if command.owner != owner
            || command.implementation_parity != parity
            || command.consumer_cutover != cutover
            || command.python_removal != removal
            || !issues.contains(&command.migration_issue)
        {
            inventory_finding(
                line_number,
                format!(
                    "GitHub service ownership row falsely claims migration state for {} {}",
                    command.domain, command.verb
                ),
                findings,
            );
        }
    }
}

fn expand_inventory_selectors<'a>(
    selectors: &str,
    ledger: &'a BTreeMap<String, OwnershipCommand>,
) -> (Vec<&'a OwnershipCommand>, Vec<String>) {
    let mut selected = BTreeMap::new();
    let mut unknown = Vec::new();
    for selector in selectors.split(',').map(str::trim) {
        if let Some(domain) = selector.strip_suffix(" *") {
            let prefix = format!("{domain} ");
            let before = selected.len();
            for (key, command) in ledger {
                if key.starts_with(&prefix) {
                    let _ = selected.insert(key.as_str(), command);
                }
            }
            if selected.len() == before {
                unknown.push(selector.to_owned());
            }
        } else if let Some(command) = ledger.get(selector) {
            let _ = selected.insert(selector, command);
        } else {
            unknown.push(selector.to_owned());
        }
    }
    (selected.into_values().collect(), unknown)
}

fn inventory_finding(
    line_number: usize,
    message: impl Into<String>,
    findings: &mut Vec<Finding>,
) {
    findings.push(Finding::new(
        GITHUB_INVENTORY,
        to_u32(line_number),
        message,
    ));
}

// ---------------------------------------------------------------------------
// Checks A and B: concrete clients and request surfaces outside the adapter.
// ---------------------------------------------------------------------------

fn check_non_adapter_rust(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    let selector = PathSelector::new(
        &["crates/*/src/*.rs", "crates/*/src/**/*.rs"],
        &["crates/larch-adapters/**", "crates/larch-lint/**"],
    )?;
    for path in selector.select(repository) {
        let source = repository.read_utf8(path)?;
        let syntax = RustSyntax::parse(path.as_str(), &source)?;
        let mut visitor = BoundaryVisitor::default();
        visit::Visit::visit_file(&mut visitor, syntax.file());
        visitor.hits.sort();
        visitor.hits.dedup();
        for (line, message) in visitor.hits {
            if suppression::number_unless_suppressed(&source, line, SUPPRESSION)?.is_none() {
                continue;
            }
            findings.push(Finding::new(path.as_str(), to_u32(line), message));
        }
    }
    Ok(())
}

#[derive(Default)]
struct BoundaryVisitor {
    hits: Vec<(usize, String)>,
}

impl BoundaryVisitor {
    fn check_string(&mut self, line: usize, value: &str) {
        if let Some(host) = SERVICE_HOSTS.iter().find(|host| value.contains(**host)) {
            self.hits.push((
                line,
                format!("service request host `{host}` appears outside {ADAPTERS_PREFIX}"),
            ));
        } else if is_graphql_document(value) {
            self.hits.push((line, GRAPHQL_MESSAGE.to_owned()));
        }
    }
}

impl<'ast> visit::Visit<'ast> for BoundaryVisitor {
    fn visit_item_use(&mut self, item: &'ast ItemUse) {
        let mut roots = Vec::new();
        use_roots(&item.tree, &mut roots);
        for (root, line) in roots {
            if let Some(client) = client_crate(&root) {
                self.hits.push((line, client_message(&client)));
            }
        }
        visit::visit_item_use(self, item);
    }

    fn visit_path(&mut self, path: &'ast syn::Path) {
        // A bare single-segment path can be a local variable named like a crate;
        // only a qualified `crate::item` path proves a concrete client is in use.
        if path.segments.len() >= 2
            && let Some(segment) = path.segments.first()
            && let Some(client) = client_crate(&segment.ident.to_string())
        {
            self.hits
                .push((segment.ident.span().start().line, client_message(&client)));
        }
        visit::visit_path(self, path);
    }

    fn visit_lit_str(&mut self, literal: &'ast LitStr) {
        self.check_string(literal.span().start().line, &literal.value());
        visit::visit_lit_str(self, literal);
    }

    // Attribute literals are documentation and configuration (`#[doc = "…"]`,
    // `#[path = "…"]`), never a service request surface. A doc comment that
    // names a host or GraphQL fragment must not be flagged.
    fn visit_attribute(&mut self, _attribute: &'ast Attribute) {}

    fn visit_macro(&mut self, macro_call: &'ast Macro) {
        let mut strings = Vec::new();
        let mut clients = Vec::new();
        scan_macro_tokens(&macro_call.tokens, &mut strings, &mut clients);
        for (line, value) in strings {
            self.check_string(line, &value);
        }
        for (line, client) in clients {
            self.hits.push((line, client_message(&client)));
        }
        visit::visit_macro(self, macro_call);
    }
}

fn client_crate(name: &str) -> Option<String> {
    if CLIENT_CRATES.contains(&name) || name.starts_with("google_cloud_") {
        Some(name.replace('_', "-"))
    } else {
        None
    }
}

fn client_message(client: &str) -> String {
    format!("concrete service client `{client}` is used outside {ADAPTERS_PREFIX}")
}

fn is_graphql_document(value: &str) -> bool {
    // A GraphQL variable (`$name`) is the precise signal that separates an
    // operation document from prose that merely opens with the keyword.
    GRAPHQL.is_match(value) && value.contains('$') && value.contains('}')
}

fn use_roots(tree: &UseTree, roots: &mut Vec<(String, usize)>) {
    match tree {
        UseTree::Path(path) => roots.push((path.ident.to_string(), path.ident.span().start().line)),
        UseTree::Name(name) => roots.push((name.ident.to_string(), name.ident.span().start().line)),
        UseTree::Rename(rename) => {
            roots.push((rename.ident.to_string(), rename.ident.span().start().line));
        }
        UseTree::Group(group) => {
            for item in &group.items {
                use_roots(item, roots);
            }
        }
        UseTree::Glob(_) => {}
    }
}

fn scan_macro_tokens(
    tokens: &TokenStream,
    strings: &mut Vec<(usize, String)>,
    clients: &mut Vec<(usize, String)>,
) {
    let trees: Vec<TokenTree> = tokens.clone().into_iter().collect();
    for (index, tree) in trees.iter().enumerate() {
        match tree {
            TokenTree::Literal(literal) => {
                if let Ok(parsed) = syn::parse_str::<LitStr>(&literal.to_string()) {
                    strings.push((literal.span().start().line, parsed.value()));
                }
            }
            TokenTree::Ident(ident) => {
                // A client crate used inside a macro body (`lazy_static! { …
                // octocrab::Octocrab … }`) shows up as an ident before a `::`.
                if let Some(client) = client_crate(&ident.to_string())
                    && matches!(trees.get(index + 1), Some(TokenTree::Punct(punct)) if punct.as_char() == ':')
                {
                    clients.push((ident.span().start().line, client));
                }
            }
            TokenTree::Group(group) => scan_macro_tokens(&group.stream(), strings, clients),
            TokenTree::Punct(_) => {}
        }
    }
}

// ---------------------------------------------------------------------------
// Check C: one concrete-client owner per service inside the adapter crate.
// ---------------------------------------------------------------------------

fn check_client_owners(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(Vec<String>, Vec<String>), LintError> {
    let selector = PathSelector::new(
        &[
            "crates/larch-adapters/src/*.rs",
            "crates/larch-adapters/src/**/*.rs",
        ],
        &[],
    )?;
    let mut github = Vec::new();
    let mut google = Vec::new();
    for path in selector.select(repository) {
        let source = repository.read_utf8(path)?;
        let syntax = RustSyntax::parse(path.as_str(), &source)?;
        let mut visitor = OwnerVisitor::default();
        visit::Visit::visit_file(&mut visitor, syntax.file());
        if let Some(line) = visitor.octocrab {
            github.push((path.as_str().to_owned(), line));
        }
        if let Some(line) = visitor.google {
            google.push((path.as_str().to_owned(), line));
        }
        if path.as_str().starts_with("crates/larch-adapters/src/github") {
            for line in visitor.generic_github_credentials {
                findings.push(Finding::new(
                    path.as_str(),
                    to_u32(line),
                    GENERIC_GITHUB_CREDENTIAL,
                ));
            }
        }
    }
    if github.len() > 1 {
        for (path, line) in &github {
            findings.push(Finding::new(path, to_u32(*line), DUPLICATE_GITHUB));
        }
    }
    if google.len() > 1 {
        for (path, line) in &google {
            findings.push(Finding::new(path, to_u32(*line), DUPLICATE_GOOGLE));
        }
    }
    Ok((
        github.into_iter().map(|(path, _)| path).collect(),
        google.into_iter().map(|(path, _)| path).collect(),
    ))
}

#[derive(Default)]
struct OwnerVisitor {
    octocrab: Option<usize>,
    google: Option<usize>,
    generic_github_credentials: Vec<usize>,
}

impl<'ast> visit::Visit<'ast> for OwnerVisitor {
    fn visit_item_mod(&mut self, item: &'ast ItemMod) {
        // Construction inside a `#[cfg(test)]` module builds a fake client, not
        // the production owner, so it does not create a second owner.
        if syn_helpers::has_cfg_test(&item.attrs) {
            return;
        }
        visit::visit_item_mod(self, item);
    }

    fn visit_item_fn(&mut self, item: &'ast ItemFn) {
        if syn_helpers::has_cfg_test(&item.attrs) {
            return;
        }
        visit::visit_item_fn(self, item);
    }

    fn visit_item_impl(&mut self, item: &'ast ItemImpl) {
        if syn_helpers::has_cfg_test(&item.attrs) {
            return;
        }
        visit::visit_item_impl(self, item);
    }

    fn visit_attribute(&mut self, _attribute: &'ast Attribute) {}

    fn visit_item_use(&mut self, item: &'ast ItemUse) {
        let mut roots = Vec::new();
        use_roots(&item.tree, &mut roots);
        if let Some((_, line)) = roots.iter().find(|(root, _)| root == "google_cloud_auth") {
            let _ = self.google.get_or_insert(*line);
        }
        visit::visit_item_use(self, item);
    }

    fn visit_path(&mut self, path: &'ast syn::Path) {
        if let Some(line) = octocrab_builder_line(path) {
            let _ = self.octocrab.get_or_insert(line);
        }
        if path.segments.iter().any(|segment| segment.ident == "google_cloud_auth")
            && let Some(segment) = path.segments.first()
        {
            let _ = self
                .google
                .get_or_insert_with(|| segment.ident.span().start().line);
        }
        if path.segments.iter().any(|segment| {
            matches!(segment.ident.to_string().as_str(), "GH_TOKEN" | "GITHUB_TOKEN")
        }) && let Some(segment) = path.segments.last()
        {
            self.generic_github_credentials
                .push(segment.ident.span().start().line);
        }
        visit::visit_path(self, path);
    }
}

fn octocrab_builder_line(path: &syn::Path) -> Option<usize> {
    let idents: Vec<String> = path
        .segments
        .iter()
        .map(|segment| segment.ident.to_string())
        .collect();
    let constructs = idents
        .windows(2)
        .any(|pair| pair[0] == "Octocrab" && pair[1] == "builder")
        || idents.iter().any(|ident| ident == "OctocrabBuilder");
    constructs.then(|| path.segments.first().map_or(0, |segment| segment.ident.span().start().line))
}

// ---------------------------------------------------------------------------
// Check D: the service inventories name each concrete-client owner.
// ---------------------------------------------------------------------------

fn check_inventory(
    repository: &Repository,
    inventory: &str,
    owners: &[String],
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    if owners.is_empty() {
        return Ok(());
    }
    let path = RepoPath::from_trusted(inventory);
    if repository.paths().binary_search(&path).is_err() {
        findings.push(Finding::new(
            inventory,
            1,
            format!("{inventory} is missing but a concrete service client owner exists"),
        ));
        return Ok(());
    }
    let content = repository.read_utf8(&path)?;
    for owner in owners {
        if !content.contains(owner.as_str()) {
            findings.push(Finding::new(
                inventory,
                1,
                format!("{inventory} does not name the concrete service client owner {owner}"),
            ));
        }
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Check E: gcloud and credential child-environments in production shell.
// ---------------------------------------------------------------------------

fn check_shell_surfaces(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    for path in repository.paths() {
        let path_text = path.as_str();
        if !is_production_surface(path_text) {
            continue;
        }
        let source = repository.read_utf8(path)?;
        match extension(path_text) {
            Some("sh") => scan_shell(path_text, &source, 0, findings)?,
            Some("md") => {
                for (offset, block) in bash_fence_blocks(&source) {
                    scan_shell(path_text, &block, offset, findings)?;
                }
            }
            _ => {}
        }
    }
    Ok(())
}

fn scan_shell(
    path: &str,
    source: &str,
    offset: usize,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    let tree = parse_bash(source)?;
    let mut hits = Vec::new();
    collect_shell_hits(tree.root_node(), source, &mut hits);
    hits.sort();
    hits.dedup();
    for (row, message) in hits {
        let line_text = source.lines().nth(row).unwrap_or("");
        if suppression::reason(line_text, SUPPRESSION)?.is_some() {
            continue;
        }
        findings.push(Finding::new(path, to_u32(row + offset + 1), message));
    }
    Ok(())
}

fn collect_shell_hits(node: Node<'_>, source: &str, hits: &mut Vec<(usize, String)>) {
    match node.kind() {
        "command" => {
            if let Some(name) = node.child_by_field_name("name") {
                let program = program_basename(node_text(name, source));
                if program == "gcloud" {
                    hits.push((name.start_position().row, GCLOUD_MESSAGE.to_owned()));
                } else if EXEC_WRAPPERS.contains(&program.as_str())
                    && let Some(wrapped) = wrapped_executable(node, source)
                    && program_basename(node_text(wrapped, source)) == "gcloud"
                {
                    hits.push((wrapped.start_position().row, GCLOUD_MESSAGE.to_owned()));
                }
                if program == "env" {
                    let mut cursor = node.walk();
                    for argument in node.children_by_field_name("argument", &mut cursor) {
                        if let Some(credential) = credential_in_assignment(node_text(argument, source)) {
                            hits.push((argument.start_position().row, credential_message(&credential)));
                        }
                    }
                }
            }
        }
        "variable_assignment" => {
            if let Some(name) = node.child_by_field_name("name") {
                let variable = node_text(name, source);
                if is_child_credential(variable) {
                    hits.push((name.start_position().row, credential_message(variable)));
                }
            }
        }
        _ => {}
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_shell_hits(child, source, hits);
    }
}

fn credential_in_assignment(word: &str) -> Option<String> {
    let equals = word.find('=')?;
    let name = &word[..equals];
    is_child_credential(name).then(|| name.to_owned())
}

fn is_child_credential(name: &str) -> bool {
    CHILD_CREDENTIALS.contains(&name)
        || name.ends_with("_ACCESS_TOKEN")
        || name.ends_with("_REFRESH_TOKEN")
}

/// Process launchers whose real executable is the first non-option argument, so
/// `sudo gcloud …` and `env FOO=bar gcloud …` do not evade the CLI check.
const EXEC_WRAPPERS: [&str; 6] = ["sudo", "command", "env", "exec", "nohup", "xargs"];

fn wrapped_executable<'tree>(command: Node<'tree>, source: &str) -> Option<Node<'tree>> {
    let mut cursor = command.walk();
    command
        .children_by_field_name("argument", &mut cursor)
        .find(|argument| {
            let text = node_text(*argument, source);
            !text.starts_with('-') && !is_assignment_word(text)
        })
}

fn is_assignment_word(word: &str) -> bool {
    let mut saw_name = false;
    for character in word.chars() {
        if character == '=' {
            return saw_name;
        }
        if character == '_' || character.is_ascii_alphanumeric() {
            saw_name = true;
        } else {
            return false;
        }
    }
    false
}

fn credential_message(credential: &str) -> String {
    format!("service credential {credential} must not enter a child environment")
}

fn bash_fence_blocks(source: &str) -> Vec<(usize, String)> {
    let mut blocks = Vec::new();
    let mut current: Option<(usize, String)> = None;
    for line in MarkdownDocument::new(source).lines() {
        let executable = matches!(
            line.fence_state(),
            FenceState::Inside { language: Some(language) } if is_bash_language(language)
        ) && !line.is_fence_boundary();
        if executable {
            let entry = current.get_or_insert_with(|| (line.number().saturating_sub(1), String::new()));
            entry.1.push_str(line.text());
            entry.1.push('\n');
        } else if let Some(block) = current.take() {
            blocks.push(block);
        }
    }
    if let Some(block) = current.take() {
        blocks.push(block);
    }
    blocks
}

fn is_bash_language(language: &str) -> bool {
    matches!(language.to_ascii_lowercase().as_str(), "bash" | "sh" | "shell")
}

fn program_basename(raw: &str) -> String {
    raw.trim_matches(['"', '\''])
        .rsplit('/')
        .next()
        .unwrap_or(raw)
        .to_owned()
}

fn node_text<'source>(node: Node<'_>, source: &'source str) -> &'source str {
    source.get(node.byte_range()).unwrap_or("")
}

fn extension(path: &str) -> Option<&str> {
    StdPath::new(path).extension()?.to_str()
}

fn to_u32(line: usize) -> u32 {
    u32::try_from(line).unwrap_or(u32::MAX)
}

#[cfg(test)]
mod tests {
    use super::{client_crate, is_graphql_document, program_basename};

    #[test]
    fn client_crate_matches_concrete_clients_and_google_families() {
        assert_eq!(client_crate("octocrab").as_deref(), Some("octocrab"));
        assert_eq!(
            client_crate("google_cloud_auth").as_deref(),
            Some("google-cloud-auth")
        );
        assert_eq!(
            client_crate("google_cloud_storage").as_deref(),
            Some("google-cloud-storage")
        );
        assert_eq!(client_crate("OctocrabGitHubService"), None);
        assert_eq!(client_crate("larch_adapters"), None);
    }

    #[test]
    fn graphql_detection_requires_an_operation_and_a_body() {
        assert!(is_graphql_document(
            "query($owner:String!){repository(owner:$owner){name}}"
        ));
        assert!(is_graphql_document(
            "query GetRepo($owner:String!){repository(owner:$owner){name}}"
        ));
        assert!(is_graphql_document(
            "mutation Close($id:ID!){closeIssue(input:{issueId:$id}){clientMutationId}}"
        ));
        assert!(!is_graphql_document("query {}"));
        assert!(!is_graphql_document("select query from table"));
        assert!(!is_graphql_document("query the settings {cached} for later reuse"));
    }

    #[test]
    fn program_basename_strips_paths_and_quotes() {
        assert_eq!(program_basename("/usr/bin/gcloud"), "gcloud");
        assert_eq!(program_basename("\"gcloud\""), "gcloud");
        assert_eq!(program_basename("gh"), "gh");
    }
}
