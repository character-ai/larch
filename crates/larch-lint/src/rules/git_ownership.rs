//! Enforce the final local-Git ownership and compatibility boundary.

use std::{
    collections::{BTreeMap, BTreeSet},
    path::Path,
    sync::LazyLock,
};

use regex::Regex;
use syn::{
    Expr, ExprCall, FnArg, ImplItem, ImplItemFn, ItemConst, ItemFn, ItemImpl, ItemMod, ItemStatic,
    ItemUse, Pat, Signature, Type, Visibility,
    parse::Parser as _,
    punctuated::Punctuated,
    spanned::Spanned,
    visit::{self, Visit},
};
use toml::Value;
use tree_sitter::Node;

use crate::{
    Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput, command_registry,
    syntax,
};

use super::syn_helpers;

const NAME: &str = "git-ownership";
const DESCRIPTION: &str =
    "Validate Git operation inventory, gix ownership, and the closed CLI exception set";
pub(super) const INVENTORY_PATH: &str = "docs/git-operation-inventory.md";
const COMMAND_REGISTRY_PATH: &str = "crates/larch-lint/data/command-registry.toml";
const GIX_OWNER: &str = "crates/larch-adapters/src/git/repository.rs";
const CLI_OWNER: &str = "crates/larch-adapters/src/git/mod.rs";
const CLI_REQUESTS_PATH: &str = "crates/larch-adapters/src/git/ops.rs";
const CLI_OPERATIONS_PATH: &str = "crates/larch-core/src/process.rs";
const LINT_BOOTSTRAP: &str = "crates/larch-lint/src/repository.rs";
const TEST_SUPPORT_PREFIX: &str = "crates/larch-test-support/";
const MATRIX_START: &str = "<!-- git-ownership-matrix:start -->";
const MATRIX_END: &str = "<!-- git-ownership-matrix:end -->";

const CLOSED_CLI_OPERATIONS: [&str; 27] = [
    "Add", "Apply", "BranchMutation", "Checkout", "Clean", "Clone", "Commit",
    "ConfigMutation", "ExactDiff", "Fetch", "Init", "InterpretTrailers", "LsRemote",
    "Merge", "Pull", "Push", "Rebase", "RemoteMutation", "Reset", "Restore", "Rm",
    "SparseCheckout", "Stash", "SubmoduleUpdate", "TagMutation", "Version", "Worktree",
];

const CLOSED_CLI_REQUESTS: [&str; 27] = [
    "AddRequest",
    "ApplyRequest",
    "BranchMutationRequest",
    "CheckoutRequest",
    "CleanRequest",
    "CloneRequest",
    "CommitRequest",
    "ConfigMutationRequest",
    "ExactDiffRequest",
    "FetchRequest",
    "InitRequest",
    "InterpretTrailersRequest",
    "LsRemoteRequest",
    "MergeRequest",
    "PullRequest",
    "PushRequest",
    "RebaseRequest",
    "RemoteMutationRequest",
    "ResetRequest",
    "RestoreRequest",
    "RmRequest",
    "SparseCheckoutRequest",
    "StashRequest",
    "SubmoduleRequest",
    "TagMutationRequest",
    "VersionRequest",
    "WorktreeRequest",
];

const CLOSED_CLI_METHODS: [(&str, &str); 26] = [
    ("add", "AddRequest"),
    ("apply", "ApplyRequest"),
    ("branch_mutation", "BranchMutationRequest"),
    ("checkout", "CheckoutRequest"),
    ("clean", "CleanRequest"),
    ("clone_repository", "CloneRequest"),
    ("commit", "CommitRequest"),
    ("config_mutation", "ConfigMutationRequest"),
    ("exact_diff", "ExactDiffRequest"),
    ("fetch", "FetchRequest"),
    ("init", "InitRequest"),
    ("interpret_trailers", "InterpretTrailersRequest"),
    ("ls_remote", "LsRemoteRequest"),
    ("merge", "MergeRequest"),
    ("pull", "PullRequest"),
    ("push", "PushRequest"),
    ("rebase", "RebaseRequest"),
    ("remote_mutation", "RemoteMutationRequest"),
    ("reset", "ResetRequest"),
    ("restore", "RestoreRequest"),
    ("rm", "RmRequest"),
    ("sparse_checkout", "SparseCheckoutRequest"),
    ("stash", "StashRequest"),
    ("submodule", "SubmoduleRequest"),
    ("tag_mutation", "TagMutationRequest"),
    ("worktree", "WorktreeRequest"),
];

const GIT_UMBRELLA_COMMANDS: [&str; 22] = [
    "git amend-add", "git branch-info", "git check-main-sync", "git check-phantom-dirty",
    "git check-remote-branch", "git checkout-ours", "git clean-tree", "git commit",
    "git conflict-files", "git count-commits", "git current-branch", "git phantom-probe",
    "git rebase-abort", "git rebase-skip", "git show-stage", "git snapshot-untracked",
    "git stage", "git sync-local-main", "push branch", "push checkpoint-probe", "push force",
    "push rebase",
];

const GIT_UMBRELLA_ISSUES: [u64; 8] = [7734, 7735, 7756, 7757, 7758, 7759, 7760, 7762];
const LATER_DOMAIN_ISSUES: [u64; 12] = [
    7674, 7676, 7677, 7678, 7679, 7680, 7681, 7682, 7683, 7684, 7685, 7686,
];

const RETIRED_PUSH_REBASE_SYMBOLS: [&str; 5] = [
    "RebasePushResult",
    "_rebase_push_force_with_lease",
    "_rebase_push_jitter_sleep",
    "_transient_retry_git_result",
    "rebase_push",
];

static SHELL_GIT: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)(?:^[[:space:]]*|[;&|({][[:space:]]*)git[[:space:]]+(?:(?:-C|-c)[[:space:]]+[^[:space:]]+[[:space:]]+)*(?P<op>--version|[a-z][a-z-]*)")
        .expect("shell Git operation expression is valid")
});
static ARGV_GIT: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"[\[\(][[:space:]]*[\"']git[\"'][[:space:]]*,[[:space:]]*(?:(?:[\"']-(?:C|c)[\"'][[:space:]]*,[[:space:]]*[^,\]\)\r\n]+,[[:space:]]*)?)[\"'](?P<op>--version|[a-z][a-z-]*)[\"']"#)
        .expect("argv Git operation expression is valid")
});
static DYNAMIC_GIT: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"(?:Command::new[[:space:]]*\([[:space:]]*[\"']git[\"']|[\[\(][[:space:]]*[\"']git[\"']|=[[:space:]]*[\[\(][[:space:]]*[\"']git[\"'])"#)
        .expect("dynamic Git program expression is valid")
});
static CLI_VARIANT: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)^    (?P<name>[A-Z][A-Za-z0-9]+),$")
        .expect("Git CLI variant expression is valid")
});
static CLI_REQUEST_MACRO: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"git_op!\((?P<name>[A-Z][A-Za-z0-9]+),[[:space:]]*[A-Z][A-Za-z0-9]+\);")
        .expect("Git CLI request macro expression is valid")
});
static CLI_REQUEST_IMPL: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"impl GitOperation for (?P<name>[A-Z][A-Za-z0-9]+)[[:space:]]*\{")
        .expect("Git CLI request implementation expression is valid")
});
static CLI_METHOD: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)^        (?P<name>[a-z][a-z0-9_]*)\((?P<request>[A-Z][A-Za-z0-9]+)\),?$")
        .expect("Git CLI method expression is valid")
});

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/git-ownership.toml",
);

#[derive(Debug)]
pub struct GitOwnershipRule;

pub static RULE: GitOwnershipRule = GitOwnershipRule;

crate::register_rule!(METADATA, RULE);

impl Rule for GitOwnershipRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let authorities = [
            INVENTORY_PATH,
            GIX_OWNER,
            CLI_OWNER,
            CLI_REQUESTS_PATH,
            CLI_OPERATIONS_PATH,
        ];
        if authorities.iter().all(|authority| {
            repository
                .paths()
                .binary_search(&RepoPath::from_trusted(authority))
                .is_err()
        }) {
            return Ok(RuleOutput::default());
        }
        let mut findings = Vec::new();
        check_concrete_gix_boundary(repository, &mut findings)?;
        check_closed_cli_operations(repository, &mut findings)?;
        check_atomic_command_rows(repository, &mut findings)?;
        findings.extend(command_registry::python_retirement_findings_for_issues(
            repository,
            &GIT_UMBRELLA_ISSUES,
        )?);
        check_retired_push_rebase_symbols(repository, &mut findings)?;
        check_inventory(repository, &mut findings)?;
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct InventoryRow {
    owner: String,
    issue: u64,
    operations: BTreeSet<String>,
}

fn check_concrete_gix_boundary(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    for path in repository.paths() {
        let path_text = path.as_str();
        if !is_rust_source_or_manifest(path_text)
            || path_text == "crates/larch-lint/src/rules/git_ownership.rs"
        {
            continue;
        }
        let source = repository.read_utf8(path)?;
        if !path_text.starts_with("crates/larch-adapters/")
            && (source.contains("gix::") || manifest_depends_on_gix(path_text, &source))
        {
            findings.push(Finding::new(
                path_text,
                1,
                "concrete gix use outside crates/larch-adapters; use the RepositoryRead port",
            ));
        }
        if path_text != LINT_BOOTSTRAP
            && !matches!(path_text, GIX_OWNER | CLI_OWNER)
            && (source.contains("struct GixRepository") || source.contains("struct GitCli"))
        {
            findings.push(Finding::new(
                path_text,
                1,
                "duplicate Git implementation outside crates/larch-adapters",
            ));
        }
        if path_text != CLI_REQUESTS_PATH && source.contains("impl GitOperation for") {
            findings.push(Finding::new(
                path_text,
                1,
                "arbitrary Git operation surface outside the closed adapter",
            ));
        }
    }
    check_rust_git_process_boundary(repository, findings)?;
    Ok(())
}

fn check_rust_git_process_boundary(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    for path in repository.paths() {
        let path_text = path.as_str();
        if !is_rust_production(path_text)
            || path_text == LINT_BOOTSTRAP
            || path_text.starts_with(TEST_SUPPORT_PREFIX)
        {
            continue;
        }
        let source = repository.read_utf8(path)?;
        let syntax = syntax::RustSyntax::parse(path_text, &source)?;
        let mut imports = ProcessImports::default();
        imports.visit_file(syntax.file());
        let mut visitor = RustGitBoundaryVisitor::new(path_text, imports);
        visitor.visit_file(syntax.file());
        for (line, message) in visitor.hits {
            findings.push(Finding::new(path_text, to_u32(line), message));
        }
    }
    Ok(())
}

#[derive(Clone, Default)]
struct ProcessImports {
    aliases: syn_helpers::ProcessCommandAliases,
    git_programs: BTreeSet<String>,
}

impl<'ast> Visit<'ast> for ProcessImports {
    fn visit_item_mod(&mut self, item: &'ast ItemMod) {
        if !syn_helpers::has_cfg_test(&item.attrs) {
            visit::visit_item_mod(self, item);
        }
    }

    fn visit_item_fn(&mut self, item: &'ast ItemFn) {
        if !syn_helpers::has_cfg_test(&item.attrs) {
            visit::visit_item_fn(self, item);
        }
    }

    fn visit_item_use(&mut self, item: &'ast ItemUse) {
        self.aliases.collect_use(&item.tree);
        visit::visit_item_use(self, item);
    }

    fn visit_item_const(&mut self, item: &'ast ItemConst) {
        if expression_is_git_program(&item.expr, &self.git_programs) {
            let _ = self.git_programs.insert(item.ident.to_string());
        }
        visit::visit_item_const(self, item);
    }

    fn visit_item_static(&mut self, item: &'ast ItemStatic) {
        if expression_is_git_program(&item.expr, &self.git_programs) {
            let _ = self.git_programs.insert(item.ident.to_string());
        }
        visit::visit_item_static(self, item);
    }
}

struct RustGitBoundaryVisitor<'path> {
    path: &'path str,
    imports: ProcessImports,
    hits: Vec<(usize, &'static str)>,
}

impl<'path> RustGitBoundaryVisitor<'path> {
    const fn new(path: &'path str, imports: ProcessImports) -> Self {
        Self {
            path,
            imports,
            hits: Vec::new(),
        }
    }

    fn scan_function(&mut self, function: &ImplItemFn) {
        self.scan_signature_and_block(&function.vis, &function.sig, &function.block);
    }

    fn scan_signature_and_block(
        &mut self,
        visibility: &Visibility,
        signature: &Signature,
        block: &syn::Block,
    ) {
        let is_adapter = matches!(self.path, CLI_OWNER | CLI_REQUESTS_PATH);
        let has_raw_argv = has_raw_argv_parameter(signature);
        if (signature.ident == "run_git"
            && (matches!(visibility, Visibility::Public(_)) || has_raw_argv))
            || (is_adapter && has_raw_argv)
        {
            self.hits.push((
                signature.ident.span().start().line,
                "arbitrary Git operation surface outside the closed typed request families",
            ));
        }
        let allow_typed_request = self.path == CLI_OWNER
            && signature.ident == "run"
            && matches!(visibility, Visibility::Inherited)
            && signature_has_git_operation_bound(signature);
        let mut bindings = FunctionBindings::new(self.imports.clone());
        bindings.visit_block(block);
        bindings.visit_block(block);
        let mut scanner = FunctionGitScanner {
            bindings,
            allow_typed_request,
            hits: Vec::new(),
        };
        scanner.visit_block(block);
        self.hits.extend(scanner.hits);
    }
}

impl<'ast> Visit<'ast> for RustGitBoundaryVisitor<'_> {
    fn visit_item_mod(&mut self, item: &'ast ItemMod) {
        if !syn_helpers::has_cfg_test(&item.attrs) {
            visit::visit_item_mod(self, item);
        }
    }

    fn visit_item_fn(&mut self, item: &'ast ItemFn) {
        if !syn_helpers::has_cfg_test(&item.attrs) {
            self.scan_signature_and_block(&item.vis, &item.sig, &item.block);
        }
    }

    fn visit_impl_item_fn(&mut self, item: &'ast ImplItemFn) {
        if !syn_helpers::has_cfg_test(&item.attrs) {
            self.scan_function(item);
        }
    }
}

struct FunctionBindings {
    imports: ProcessImports,
    constructor_aliases: BTreeSet<String>,
    git_commands: BTreeSet<String>,
}

impl FunctionBindings {
    const fn new(imports: ProcessImports) -> Self {
        Self {
            imports,
            constructor_aliases: BTreeSet::new(),
            git_commands: BTreeSet::new(),
        }
    }

    fn record_local(&mut self, local: &syn::Local) {
        let Some(name) = syn_helpers::pattern_name(&local.pat) else {
            return;
        };
        let Some(initializer) = &local.init else {
            return;
        };
        if expression_is_git_program(&initializer.expr, &self.imports.git_programs) {
            let _ = self.imports.git_programs.insert(name.clone());
        }
        if expression_is_command_constructor(&initializer.expr, &self.imports) {
            let _ = self.constructor_aliases.insert(name.clone());
        }
        if expression_constructs_git(
            &initializer.expr,
            &self.imports,
            &self.constructor_aliases,
        ) {
            let _ = self.git_commands.insert(name);
        }
    }
}

impl<'ast> Visit<'ast> for FunctionBindings {
    fn visit_local(&mut self, local: &'ast syn::Local) {
        self.record_local(local);
        visit::visit_local(self, local);
    }
}

struct FunctionGitScanner {
    bindings: FunctionBindings,
    allow_typed_request: bool,
    hits: Vec<(usize, &'static str)>,
}

impl FunctionGitScanner {
    fn record_direct_process(&mut self, call: &ExprCall) {
        if call_constructs_git(
            call,
            &self.bindings.imports,
            &self.bindings.constructor_aliases,
        ) {
            self.hits.push((
                call.func.span().start().line,
                "direct production Git process; use the typed Git adapter",
            ));
        }
        if is_process_request_constructor(call)
            && call
                .args
                .first()
                .is_some_and(expression_selects_git_program)
            && !self.allow_typed_request
        {
            self.hits.push((
                call.func.span().start().line,
                "raw Git process request outside the one typed adapter runner",
            ));
        }
    }
}

impl<'ast> Visit<'ast> for FunctionGitScanner {
    fn visit_expr_call(&mut self, call: &'ast ExprCall) {
        self.record_direct_process(call);
        visit::visit_expr_call(self, call);
    }

    fn visit_expr_method_call(&mut self, call: &'ast syn::ExprMethodCall) {
        let forwards_generic_argv = call.method == "args"
            && matches!(&*call.receiver, Expr::Path(path) if path.path.segments.last().is_some_and(|segment| self.bindings.git_commands.contains(&segment.ident.to_string())))
            && call.args.first().is_some_and(|argument| {
                !matches!(argument, Expr::Array(_) | Expr::Lit(_))
            });
        if forwards_generic_argv {
            self.hits.push((
                call.method.span().start().line,
                "generic argv forwarding to Git; use a closed typed request family",
            ));
        }
        visit::visit_expr_method_call(self, call);
    }

    fn visit_expr_array(&mut self, array: &'ast syn::ExprArray) {
        if array
            .elems
            .first()
            .is_some_and(|value| expression_is_git_program(value, &self.bindings.imports.git_programs))
        {
            self.hits.push((
                array.bracket_token.span.open().start().line,
                "raw production Git argv; use a closed typed request family",
            ));
        }
        visit::visit_expr_array(self, array);
    }

    fn visit_macro(&mut self, macro_call: &'ast syn::Macro) {
        if macro_call.path.is_ident("vec")
            && let Ok(arguments) =
                Punctuated::<Expr, syn::Token![,]>::parse_terminated.parse2(macro_call.tokens.clone())
            && arguments.first().is_some_and(|value| {
                expression_is_git_program(value, &self.bindings.imports.git_programs)
            })
        {
            self.hits.push((
                macro_call.path.span().start().line,
                "raw production Git argv; use a closed typed request family",
            ));
        }
        visit::visit_macro(self, macro_call);
    }
}

fn expression_is_command_constructor(expression: &Expr, imports: &ProcessImports) -> bool {
    let Expr::Path(path) = expression else {
        return false;
    };
    is_command_constructor_path(&path.path, imports)
}

fn expression_constructs_git(
    expression: &Expr,
    imports: &ProcessImports,
    constructor_aliases: &BTreeSet<String>,
) -> bool {
    matches!(expression, Expr::Call(call) if call_constructs_git(call, imports, constructor_aliases))
}

fn call_constructs_git(
    call: &ExprCall,
    imports: &ProcessImports,
    constructor_aliases: &BTreeSet<String>,
) -> bool {
    let Expr::Path(function) = &*call.func else {
        return false;
    };
    let is_constructor = is_command_constructor_path(&function.path, imports)
        || (function.path.segments.len() == 1
            && constructor_aliases.contains(&function.path.segments[0].ident.to_string()));
    is_constructor
        && call
            .args
            .first()
            .is_some_and(|value| expression_is_git_program(value, &imports.git_programs))
}

fn is_command_constructor_path(path: &syn::Path, imports: &ProcessImports) -> bool {
    imports.aliases.is_constructor_path(path)
}

fn expression_is_git_program(expression: &Expr, bindings: &BTreeSet<String>) -> bool {
    match expression {
        Expr::Lit(literal) => {
            matches!(&literal.lit, syn::Lit::Str(value) if value.value() == "git")
        }
        Expr::Path(path) => path.path.segments.last().is_some_and(|segment| {
            bindings.contains(&segment.ident.to_string())
        }),
        Expr::Call(call) => call
            .args
            .first()
            .is_some_and(|value| expression_is_git_program(value, bindings)),
        Expr::Group(group) => expression_is_git_program(&group.expr, bindings),
        Expr::Paren(paren) => expression_is_git_program(&paren.expr, bindings),
        Expr::Reference(reference) => expression_is_git_program(&reference.expr, bindings),
        _ => false,
    }
}

fn expression_selects_git_program(expression: &Expr) -> bool {
    match expression {
        Expr::Call(call) => {
            let Expr::Path(path) = &*call.func else {
                return false;
            };
            let segments: Vec<String> = path
                .path
                .segments
                .iter()
                .map(|segment| segment.ident.to_string())
                .collect();
            segments.ends_with(&["ExternalProgram".to_owned(), "Git".to_owned()])
        }
        Expr::Group(group) => expression_selects_git_program(&group.expr),
        Expr::Paren(paren) => expression_selects_git_program(&paren.expr),
        _ => false,
    }
}

fn is_process_request_constructor(call: &ExprCall) -> bool {
    let Expr::Path(path) = &*call.func else {
        return false;
    };
    let segments: Vec<String> = path
        .path
        .segments
        .iter()
        .map(|segment| segment.ident.to_string())
        .collect();
    segments.ends_with(&["ProcessRequest".to_owned(), "new".to_owned()])
}

fn has_raw_argv_parameter(signature: &Signature) -> bool {
    signature.inputs.iter().any(|argument| {
        let FnArg::Typed(argument) = argument else {
            return false;
        };
        let Pat::Ident(pattern) = &*argument.pat else {
            return false;
        };
        matches!(pattern.ident.to_string().as_str(), "args" | "argv" | "arguments")
    })
}

fn signature_has_git_operation_bound(signature: &Signature) -> bool {
    let direct = signature.generics.params.iter().any(|parameter| {
        let syn::GenericParam::Type(parameter) = parameter else {
            return false;
        };
        parameter.bounds.iter().any(|bound| {
            matches!(bound, syn::TypeParamBound::Trait(bound) if bound.path.is_ident("GitOperation"))
        })
    });
    direct
        || signature
            .generics
            .where_clause
            .as_ref()
            .is_some_and(|clause| {
                clause.predicates.iter().any(|predicate| {
                    matches!(predicate, syn::WherePredicate::Type(predicate) if predicate.bounds.iter().any(|bound| matches!(bound, syn::TypeParamBound::Trait(bound) if bound.path.is_ident("GitOperation"))))
                })
            })
}

fn to_u32(line: usize) -> u32 {
    u32::try_from(line).unwrap_or(u32::MAX)
}

fn is_rust_source_or_manifest(path: &str) -> bool {
    path.starts_with("crates/")
        && (Path::new(path)
            .extension()
            .is_some_and(|extension| extension.eq_ignore_ascii_case("rs"))
            || path.ends_with("Cargo.toml"))
        && !path.split('/').any(|part| part == "tests")
}

fn manifest_depends_on_gix(path: &str, source: &str) -> bool {
    path.ends_with("Cargo.toml")
        && source.lines().any(|line| {
            let line = line.trim_start();
            line.starts_with("gix =") || line.starts_with("gix.")
        })
}

fn check_closed_cli_operations(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    let source = required_utf8(repository, CLI_OPERATIONS_PATH)?;
    let start = source.find("pub enum GitCliOperation {").ok_or_else(|| {
        LintError::new(format!("{CLI_OPERATIONS_PATH}: missing GitCliOperation enum"))
    })?;
    let tail = &source[start..];
    let end = tail.find("\n}").ok_or_else(|| {
        LintError::new(format!("{CLI_OPERATIONS_PATH}: unterminated GitCliOperation enum"))
    })?;
    let actual: BTreeSet<&str> = CLI_VARIANT
        .captures_iter(&tail[..end])
        .map(|capture| capture.name("name").expect("named capture").as_str())
        .collect();
    let expected: BTreeSet<&str> = CLOSED_CLI_OPERATIONS.into_iter().collect();
    if actual != expected {
        findings.push(Finding::new(
            CLI_OPERATIONS_PATH,
            1,
            format!(
                "GitCliOperation drifted from the closed #7671 exception set: expected {expected:?}, found {actual:?}"
            ),
        ));
    }
    let requests = required_utf8(repository, CLI_REQUESTS_PATH)?;
    let actual_requests: BTreeSet<&str> = CLI_REQUEST_MACRO
        .captures_iter(&requests)
        .chain(CLI_REQUEST_IMPL.captures_iter(&requests))
        .map(|capture| capture.name("name").expect("named capture").as_str())
        .collect();
    let expected_requests: BTreeSet<&str> = CLOSED_CLI_REQUESTS.into_iter().collect();
    if actual_requests != expected_requests {
        findings.push(Finding::new(
            CLI_REQUESTS_PATH,
            1,
            format!(
                "Git CLI request families drifted from the closed #7671 set: expected {expected_requests:?}, found {actual_requests:?}"
            ),
        ));
    }
    check_closed_cli_public_surface(repository, &requests, findings)?;
    Ok(())
}

fn check_closed_cli_public_surface(
    repository: &Repository,
    requests: &str,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    let owner = required_utf8(repository, CLI_OWNER)?;
    let actual_methods: BTreeSet<(String, String)> = CLI_METHOD
        .captures_iter(&owner)
        .map(|capture| {
            (
                capture.name("name").expect("named capture").as_str().to_owned(),
                capture
                    .name("request")
                    .expect("named capture")
                    .as_str()
                    .to_owned(),
            )
        })
        .collect();
    let expected_methods: BTreeSet<(String, String)> = CLOSED_CLI_METHODS
        .into_iter()
        .map(|(name, request)| (name.to_owned(), request.to_owned()))
        .collect();
    if actual_methods != expected_methods {
        findings.push(Finding::new(
            CLI_OWNER,
            1,
            format!(
                "GitCli public methods drifted from the closed typed request families: expected {expected_methods:?}, found {actual_methods:?}"
            ),
        ));
    }
    let syntax = syntax::RustSyntax::parse(CLI_OWNER, &owner)?;
    let mut public_methods = GitCliPublicMethodVisitor::default();
    public_methods.visit_file(syntax.file());
    let expected_explicit: BTreeSet<String> = ["new", "version", "working_directory"]
        .into_iter()
        .map(str::to_owned)
        .collect();
    if public_methods.names != expected_explicit {
        findings.push(Finding::new(
            CLI_OWNER,
            1,
            format!(
                "GitCli explicit public surface drifted: expected {expected_explicit:?}, found {:?}",
                public_methods.names
            ),
        ));
    }
    if !owner.contains("pub async fn $name(") {
        findings.push(Finding::new(
            CLI_OWNER,
            1,
            "GitCli typed request methods must remain public",
        ));
    }
    if !requests.contains("pub(super) trait GitOperation") {
        findings.push(Finding::new(
            CLI_REQUESTS_PATH,
            1,
            "GitOperation must remain private to the adapter module",
        ));
    }
    let request_syntax = syntax::RustSyntax::parse(CLI_REQUESTS_PATH, requests)?;
    let mut public_functions = PublicFreeFunctionVisitor::default();
    public_functions.visit_file(request_syntax.file());
    if !public_functions.names.is_empty() {
        findings.push(Finding::new(
            CLI_REQUESTS_PATH,
            1,
            format!(
                "public free functions bypass the closed Git request surface: {:?}",
                public_functions.names
            ),
        ));
    }
    Ok(())
}

#[derive(Default)]
struct GitCliPublicMethodVisitor {
    names: BTreeSet<String>,
}

impl<'ast> Visit<'ast> for GitCliPublicMethodVisitor {
    fn visit_item_impl(&mut self, item: &'ast ItemImpl) {
        let Type::Path(self_type) = &*item.self_ty else {
            return;
        };
        if self_type.path.segments.last().is_none_or(|segment| segment.ident != "GitCli") {
            return;
        }
        for child in &item.items {
            if let ImplItem::Fn(function) = child
                && matches!(function.vis, Visibility::Public(_))
            {
                let _ = self.names.insert(function.sig.ident.to_string());
            }
        }
    }
}

#[derive(Default)]
struct PublicFreeFunctionVisitor {
    names: BTreeSet<String>,
}

impl<'ast> Visit<'ast> for PublicFreeFunctionVisitor {
    fn visit_item_mod(&mut self, item: &'ast ItemMod) {
        if !syn_helpers::has_cfg_test(&item.attrs) {
            visit::visit_item_mod(self, item);
        }
    }

    fn visit_item_fn(&mut self, item: &'ast ItemFn) {
        if !syn_helpers::has_cfg_test(&item.attrs) && matches!(item.vis, Visibility::Public(_)) {
            let _ = self.names.insert(item.sig.ident.to_string());
        }
    }
}

fn check_atomic_command_rows(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    let source = required_utf8(repository, COMMAND_REGISTRY_PATH)?;
    let value: Value = toml::from_str(&source).map_err(|error| {
        LintError::new(format!("{COMMAND_REGISTRY_PATH}: invalid TOML: {error}"))
    })?;
    let commands = value
        .get("commands")
        .and_then(Value::as_array)
        .ok_or_else(|| LintError::new(format!("{COMMAND_REGISTRY_PATH}: missing commands")))?;
    let expected: BTreeSet<&str> = GIT_UMBRELLA_COMMANDS.into_iter().collect();
    let mut actual = BTreeSet::new();
    for command in commands {
        let Some(table) = command.as_table() else {
            continue;
        };
        let issue = table
            .get("migration_issue")
            .and_then(Value::as_integer)
            .and_then(|value| u64::try_from(value).ok());
        if !issue.is_some_and(|value| GIT_UMBRELLA_ISSUES.contains(&value)) {
            continue;
        }
        let domain = table.get("domain").and_then(Value::as_str).unwrap_or_default();
        let verb = table.get("verb").and_then(Value::as_str).unwrap_or_default();
        let selector = format!("{domain} {verb}");
        let final_state = table.get("owner").and_then(Value::as_str) == Some("rust")
            && table.get("implementation_parity").and_then(Value::as_str) == Some("complete")
            && table.get("consumer_cutover").and_then(Value::as_str) == Some("complete")
            && table.get("python_removal").and_then(Value::as_str) == Some("complete");
        if !final_state {
            findings.push(Finding::new(
                COMMAND_REGISTRY_PATH,
                1,
                format!("non-atomic final Git command row: {selector}"),
            ));
        }
        let _ = actual.insert(selector);
    }
    let actual_refs: BTreeSet<&str> = actual.iter().map(String::as_str).collect();
    if actual_refs != expected {
        findings.push(Finding::new(
            COMMAND_REGISTRY_PATH,
            1,
            format!(
                "#7675 command set drifted: expected {expected:?}, found {actual_refs:?}"
            ),
        ));
    }
    Ok(())
}

fn check_retired_push_rebase_symbols(
    repository: &Repository,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    for path in repository.paths() {
        let path_text = path.as_str();
        if !syntax::is_production_python_path(path_text) {
            continue;
        }
        let source = repository.read_utf8(path)?;
        if !RETIRED_PUSH_REBASE_SYMBOLS
            .iter()
            .any(|symbol| source.contains(symbol))
        {
            continue;
        }
        let tree = repository.python_syntax(path)?;
        collect_retired_python_identifiers(tree.root_node(), &source, path_text, findings);
    }
    Ok(())
}

fn collect_retired_python_identifiers(
    node: Node<'_>,
    source: &str,
    path: &str,
    findings: &mut Vec<Finding>,
) {
    if node.kind() == "identifier"
        && let Ok(identifier) = node.utf8_text(source.as_bytes())
        && RETIRED_PUSH_REBASE_SYMBOLS.contains(&identifier)
    {
        findings.push(Finding::new(
            path,
            to_u32(node.start_position().row + 1),
            format!("retired push rebase Python state-machine symbol: {identifier}"),
        ));
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_retired_python_identifiers(child, source, path, findings);
    }
}

fn check_inventory(repository: &Repository, findings: &mut Vec<Finding>) -> Result<(), LintError> {
    let inventory = parse_inventory(&required_utf8(repository, INVENTORY_PATH)?)?;
    let detected = detect_surfaces(repository)?;
    for (path, row) in &detected {
        match inventory.get(path) {
            None => findings.push(Finding::new(
                INVENTORY_PATH,
                1,
                format!(
                    "production Git surface is missing from the matrix: {path}\t{}\t#{}\t{}",
                    row.owner,
                    row.issue,
                    join_operations(&row.operations)
                ),
            )),
            Some(recorded) if recorded != row => findings.push(Finding::new(
                INVENTORY_PATH,
                1,
                format!(
                    "production Git surface has stale ownership or operations: {path}; expected {}\t#{}\t{}",
                    row.owner,
                    row.issue,
                    join_operations(&row.operations)
                ),
            )),
            Some(_) => {}
        }
    }
    for path in inventory.keys() {
        if !detected.contains_key(path) {
            findings.push(Finding::new(
                INVENTORY_PATH,
                1,
                format!("matrix row is no longer a detected production Git surface: {path}"),
            ));
        }
    }
    Ok(())
}

/// Return canonical inventory paths that still defer to one later-domain issue.
///
/// This deliberately exposes only the parsed query needed by sibling closure
/// rules. The inventory grammar, validation, and Markdown marker ownership
/// remain private to this module.
pub(super) fn unresolved_later_domain_paths(
    repository: &Repository,
    issue: u64,
) -> Result<Vec<String>, LintError> {
    let path = RepoPath::from_trusted(INVENTORY_PATH);
    if repository.paths().binary_search(&path).is_err() {
        return Ok(Vec::new());
    }
    let inventory = parse_inventory(&repository.read_utf8(&path)?)?;
    Ok(inventory
        .into_iter()
        .filter_map(|(path, row)| {
            (row.owner == "later-domain" && row.issue == issue).then_some(path)
        })
        .collect())
}

fn parse_inventory(source: &str) -> Result<BTreeMap<String, InventoryRow>, LintError> {
    let start = source.find(MATRIX_START).ok_or_else(|| {
        LintError::new(format!("{INVENTORY_PATH}: missing {MATRIX_START}"))
    })? + MATRIX_START.len();
    let tail = &source[start..];
    let end = tail.find(MATRIX_END).ok_or_else(|| {
        LintError::new(format!("{INVENTORY_PATH}: missing {MATRIX_END}"))
    })?;
    let mut rows = BTreeMap::new();
    for (offset, line) in tail[..end].lines().enumerate() {
        let line = line.trim();
        if line.is_empty() || line.starts_with("```") || line.starts_with("surface\t") {
            continue;
        }
        let fields: Vec<&str> = line.split('\t').collect();
        if fields.len() != 4 {
            return Err(LintError::new(format!(
                "{INVENTORY_PATH}:{}: expected four tab-separated fields",
                offset + 1
            )));
        }
        let path = fields[0];
        if path.is_empty() || Path::new(path).is_absolute() || path.split('/').any(|part| part.is_empty() || part == "..") {
            return Err(LintError::new(format!("{INVENTORY_PATH}: unsafe surface path {path:?}")));
        }
        let owner = fields[1];
        let issue = fields[2].strip_prefix('#').and_then(|value| value.parse::<u64>().ok())
            .ok_or_else(|| LintError::new(format!("{INVENTORY_PATH}: invalid issue {}", fields[2])))?;
        validate_owner(owner, issue)?;
        let operations: BTreeSet<String> = fields[3]
            .split(',')
            .map(str::trim)
            .filter(|operation| !operation.is_empty())
            .map(str::to_owned)
            .collect();
        if operations.is_empty() || join_operations(&operations) != fields[3] {
            return Err(LintError::new(format!(
                "{INVENTORY_PATH}: operations for {path} must be sorted, unique, and comma-separated"
            )));
        }
        if rows.insert(path.to_owned(), InventoryRow { owner: owner.to_owned(), issue, operations }).is_some() {
            return Err(LintError::new(format!("{INVENTORY_PATH}: duplicate surface {path}")));
        }
    }
    Ok(rows)
}

fn validate_owner(owner: &str, issue: u64) -> Result<(), LintError> {
    let valid = match owner {
        "gix-read" | "git-cli" => issue == 7671,
        "bootstrap" => issue == 7736,
        "later-domain" => LATER_DOMAIN_ISSUES.contains(&issue),
        _ => false,
    };
    if valid {
        Ok(())
    } else {
        Err(LintError::new(format!(
            "{INVENTORY_PATH}: invalid owner/issue pair {owner} #{issue}"
        )))
    }
}

fn detect_surfaces(repository: &Repository) -> Result<BTreeMap<String, InventoryRow>, LintError> {
    let mut surfaces = BTreeMap::new();
    insert_fixed_surface(&mut surfaces, GIX_OWNER, "gix-read", 7671, &["concrete-gix-owner"]);
    insert_fixed_surface(&mut surfaces, CLI_OWNER, "git-cli", 7671, &["closed-cli-owner"]);
    insert_fixed_surface(&mut surfaces, LINT_BOOTSTRAP, "bootstrap", 7736, &["repository-discovery", "tracked-paths"]);
    for path in repository.paths() {
        let path_text = path.as_str();
        if !is_production_surface(path_text) || matches!(path_text, GIX_OWNER | CLI_OWNER | LINT_BOOTSTRAP) {
            continue;
        }
        let source = repository.read_utf8(path)?;
        let mut operations = if is_rust_production(path_text) {
            BTreeSet::new()
        } else {
            direct_git_operations(&source)
        };
        let uses_read_port = path_text.starts_with("crates/larch-cli/src/")
            && (source.contains("GixRepository") || source.contains("RepositoryRead"))
            ;
        let uses_cli_port = path_text.starts_with("crates/larch-cli/src/")
            && source.contains("GitCli");
        if uses_read_port {
            let _ = operations.insert("typed-read".to_owned());
        }
        if uses_cli_port {
            let _ = operations.insert("typed-cli".to_owned());
        }
        let (owner, issue) = if uses_cli_port {
            ("git-cli", 7671)
        } else if uses_read_port {
            ("gix-read", 7671)
        } else {
            ("later-domain", later_domain_issue(path_text))
        };
        if !operations.is_empty() {
            let _ = surfaces.insert(path_text.to_owned(), InventoryRow { owner: owner.to_owned(), issue, operations });
        }
    }
    Ok(surfaces)
}

fn insert_fixed_surface(
    surfaces: &mut BTreeMap<String, InventoryRow>,
    path: &str,
    owner: &str,
    issue: u64,
    operations: &[&str],
) {
    let _ = surfaces.insert(path.to_owned(), InventoryRow {
        owner: owner.to_owned(),
        issue,
        operations: operations.iter().map(|operation| (*operation).to_owned()).collect(),
    });
}

fn direct_git_operations(source: &str) -> BTreeSet<String> {
    let mut operations = BTreeSet::new();
    for capture in SHELL_GIT.captures_iter(source).chain(ARGV_GIT.captures_iter(source)) {
        let operation = capture.name("op").expect("named capture").as_str();
        if is_git_subcommand(operation) {
            let _ = operations.insert(operation.to_owned());
        }
    }
    if DYNAMIC_GIT.is_match(source) && operations.is_empty() {
        let _ = operations.insert("dynamic".to_owned());
    }
    operations
}

fn is_git_subcommand(value: &str) -> bool {
    matches!(
        value,
        "--version"
            | "add"
            | "apply"
            | "branch"
            | "cat-file"
            | "check-ref-format"
            | "checkout"
            | "clean"
            | "clone"
            | "commit"
            | "config"
            | "diff"
            | "diff-tree"
            | "fetch"
            | "fsck"
            | "grep"
            | "init"
            | "interpret-trailers"
            | "log"
            | "ls-files"
            | "ls-remote"
            | "ls-tree"
            | "merge"
            | "merge-base"
            | "pull"
            | "push"
            | "rebase"
            | "remote"
            | "reset"
            | "restore"
            | "rev-list"
            | "rev-parse"
            | "rm"
            | "show"
            | "show-ref"
            | "sparse-checkout"
            | "stash"
            | "status"
            | "submodule"
            | "symbolic-ref"
            | "tag"
            | "worktree"
    )
}

fn is_production_surface(path: &str) -> bool {
    if is_rust_production(path) {
        return true;
    }
    let extension = Path::new(path).extension().and_then(|value| value.to_str()).unwrap_or_default();
    let runtime = path.starts_with("python/larch/") && extension == "py"
        || (path.starts_with("skills/") || path.starts_with(".claude/skills/")
            || path.starts_with("agents/") || path.starts_with(".claude/agents/"))
            && matches!(extension, "md" | "sh" | "py")
        || path.starts_with("hooks/") && matches!(extension, "json" | "sh")
        || path.starts_with("scripts/") && matches!(extension, "sh" | "py")
        || path.starts_with(".github/workflows/") && matches!(extension, "yml" | "yaml")
        || matches!(path, "Makefile" | ".pre-commit-config.yaml");
    runtime && !path.split('/').any(|part| part == "tests" || part == "fixtures")
        && !path.rsplit('/').next().is_some_and(|name| name.starts_with("test-") || name.starts_with("test_"))
}

fn is_rust_production(path: &str) -> bool {
    path.starts_with("crates/")
        && path.contains("/src/")
        && Path::new(path)
            .extension()
            .is_some_and(|extension| extension.eq_ignore_ascii_case("rs"))
        && !path.ends_with("/tests.rs")
}

fn later_domain_issue(path: &str) -> u64 {
    if path.contains("/release/")
        || path.starts_with(".claude/skills/release/")
        || path.contains("upgrade-larch")
        || path.contains("check-stale-plugin")
    {
        7674
    } else if path == "python/larch/git/gh.py" {
        7676
    } else if path.contains("/state/")
        || path.contains("sessionstart-health")
        || path.contains("block-submodule-edit")
    {
        7677
    } else if path.contains("/agents/") || path.starts_with("agents/") {
        7678
    } else if path.contains("/review/") || path.starts_with("skills/review") {
        7679
    } else if path.contains("/design/") || path.starts_with("skills/design") {
        7680
    } else if path.contains("/implement/") || path.starts_with("skills/implement")
        || path.starts_with("python/larch/git/")
    {
        7681
    } else if let Some(issue) = super::issue_python_free::retained_module_owner(path) {
        u64::try_from(issue).expect("retained issue-domain owner is positive")
    } else if path.contains("/issue/") || path.contains("forked") || path.starts_with("skills/triage") {
        7682
    } else if path.contains("/report/") || path.contains("/rendering/") {
        7683
    } else if path.contains("/research/") || path.starts_with("skills/research")
        || path.contains("analyze-bugs") || path.contains("learn-from-bugs")
    {
        7684
    } else if path.contains("/lint/")
        || path.contains("rebalance-tests")
        || path.contains("agnix")
        || path.contains("larch-size")
        || path.starts_with(".github/workflows/")
        || path == "Makefile"
    {
        7685
    } else if path.contains("fluff-analysis")
        || path.contains("voter-calibration")
        || path.contains("audit-runs")
    {
        7684
    } else {
        7686
    }
}

fn join_operations(operations: &BTreeSet<String>) -> String {
    operations.iter().cloned().collect::<Vec<_>>().join(",")
}

fn required_utf8(repository: &Repository, path: &str) -> Result<String, LintError> {
    let path = RepoPath::from_trusted(path);
    repository
        .read_required_utf8(&path, format!("{path}: required file is missing"))
        .map(|source| source.to_string())
}
