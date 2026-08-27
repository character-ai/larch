//! Keep GitHub issue field mutation behind the typed issue-mutation owner.

use std::{collections::BTreeSet, path::Path};

use syn::{
    Expr, ExprCall, ExprMethodCall, ItemFn, ItemMod, ItemUse, UseTree,
    spanned::Spanned,
    visit::{self, Visit},
};

use crate::{
    Finding, LintError, Repository, Rule, RuleMetadata, RuleOutput,
    syntax::{
        RustSyntax, ShellCommand, json_shell_commands, markdown_shell_commands,
        shell_commands_from_tree,
    },
};

const NAME: &str = "issue-mutation-owner";
const DESCRIPTION: &str = "Reject raw GitHub issue field mutation outside the typed owner";
const RUST_OWNER: &str = "crates/larch-adapters/src/github/issue_mutation.rs";
// The semantic `GitHubService` transport necessarily invokes Octocrab itself.
const RUST_TRANSPORT_ADAPTER: &str = "crates/larch-adapters/src/github_rest.rs";
const OWNER_GUIDANCE: &str = "use larch_adapters::github::IssueMutationOwner";

const GRAPHQL_MUTATIONS: &[&str] = &[
    "updateIssue",
    "addLabelsToLabelable",
    "removeLabelsFromLabelable",
];
const RUST_WRITE_METHODS: &[&str] = &["edit_issue", "add_label", "remove_label"];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/issue-mutation-owner.toml",
);

#[derive(Debug)]
pub struct IssueMutationOwnerRule;

pub static RULE: IssueMutationOwnerRule = IssueMutationOwnerRule;

impl Rule for IssueMutationOwnerRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let mut findings = Vec::new();
        for path in repository.paths() {
            let path_text = path.as_str();
            if matches!(path_text, RUST_OWNER | RUST_TRANSPORT_ADAPTER)
                || is_fixture(path_text)
            {
                continue;
            }
            let Some(surface) = surface(path_text) else {
                continue;
            };
            let source = repository.read_utf8(path)?;
            findings.extend(match surface {
                Surface::Rust => check_rust(path_text, &source)?,
                Surface::Shell => {
                    let syntax = repository.bash_syntax(path)?;
                    check_commands(path_text, shell_commands_from_tree(&syntax, &source, 0))?
                }
                Surface::Markdown => check_markdown(path_text, &source)?,
                Surface::Json => check_json(path_text, &source)?,
            });
        }
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

#[derive(Clone, Copy)]
enum Surface {
    Rust,
    Shell,
    Markdown,
    Json,
}

fn surface(path: &str) -> Option<Surface> {
    let extension = Path::new(path).extension()?.to_str()?;
    if path.starts_with("crates/")
        && !path.starts_with("crates/larch-lint/")
        && extension.eq_ignore_ascii_case("rs")
    {
        return Some(Surface::Rust);
    }
    if path.starts_with("skills/") || path.starts_with("agents/") {
        if extension.eq_ignore_ascii_case("md") {
            return Some(Surface::Markdown);
        }
        if extension.eq_ignore_ascii_case("sh") {
            return Some(Surface::Shell);
        }
    }
    if path.starts_with("hooks/") {
        if extension.eq_ignore_ascii_case("json") {
            return Some(Surface::Json);
        }
        if extension.eq_ignore_ascii_case("sh") {
            return Some(Surface::Shell);
        }
    }
    if path.starts_with("scripts/") && extension.eq_ignore_ascii_case("sh") {
        return Some(Surface::Shell);
    }
    None
}

fn is_fixture(path: &str) -> bool {
    path.split('/')
        .any(|part| matches!(part, "tests" | "fixtures"))
        || path.rsplit('/').next().is_some_and(|name| {
            name.starts_with("test-") || name.starts_with("test_") || name.ends_with("_test.py")
        })
}

#[derive(Clone, Eq, Ord, PartialEq, PartialOrd)]
enum MutationKind {
    Rust(String),
    Cli,
    Rest,
    GraphQl(&'static str),
}

impl MutationKind {
    fn message(self) -> String {
        match self {
            Self::Rust(name) => {
                format!("raw Rust issue field mutation {name}; {OWNER_GUIDANCE}")
            }
            Self::Cli => format!("raw gh issue edit argv; {OWNER_GUIDANCE}"),
            Self::Rest => format!("raw issue REST PATCH; {OWNER_GUIDANCE}"),
            Self::GraphQl(name) => {
                format!("raw issue GraphQL mutation {name}; {OWNER_GUIDANCE}")
            }
        }
    }
}

fn check_rust(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    let syntax = RustSyntax::parse(path, source)?;
    let mut imports = RustMutationVisitor::default();
    imports.visit_file(syntax.file());
    let mut visitor = RustMutationVisitor {
        github_service_aliases: imports.github_service_aliases,
        github_service_glob: imports.github_service_glob,
        matches: BTreeSet::new(),
    };
    visitor.visit_file(syntax.file());
    visitor
        .matches
        .into_iter()
        .map(|(line, kind)| Ok(Finding::new(path, line, kind.message())))
        .collect()
}

#[derive(Default)]
struct RustMutationVisitor {
    github_service_aliases: BTreeSet<String>,
    github_service_glob: bool,
    matches: BTreeSet<(u32, MutationKind)>,
}

impl<'ast> Visit<'ast> for RustMutationVisitor {
    fn visit_item_use(&mut self, item: &'ast ItemUse) {
        collect_github_service_aliases(
            &item.tree,
            false,
            &mut self.github_service_aliases,
            &mut self.github_service_glob,
        );
        visit::visit_item_use(self, item);
    }

    fn visit_item_mod(&mut self, item: &'ast ItemMod) {
        if !has_test_attribute(&item.attrs) {
            visit::visit_item_mod(self, item);
        }
    }

    fn visit_item_fn(&mut self, item: &'ast ItemFn) {
        if !has_test_attribute(&item.attrs) {
            visit::visit_item_fn(self, item);
        }
    }

    fn visit_expr_call(&mut self, call: &'ast ExprCall) {
        if let Some(method) = qualified_rust_write_method(&call.func, self) {
            self.matches.insert((line_number_span(call.span()), MutationKind::Rust(method)));
        }
        visit::visit_expr_call(self, call);
    }

    fn visit_expr_method_call(&mut self, call: &'ast ExprMethodCall) {
        let method = call.method.to_string();
        if self.can_call_github_service() && RUST_WRITE_METHODS.contains(&method.as_str()) {
            self.matches.insert((line_number_span(call.span()), MutationKind::Rust(method)));
        }
        visit::visit_expr_method_call(self, call);
    }
}

impl RustMutationVisitor {
    fn can_call_github_service(&self) -> bool {
        self.github_service_glob || !self.github_service_aliases.is_empty()
    }
}

fn collect_github_service_aliases(
    tree: &UseTree,
    inside_larch_core: bool,
    aliases: &mut BTreeSet<String>,
    glob: &mut bool,
) {
    match tree {
        UseTree::Path(path) => collect_github_service_aliases(
            &path.tree,
            inside_larch_core || path.ident == "larch_core",
            aliases,
            glob,
        ),
        UseTree::Name(name) if inside_larch_core && name.ident == "GitHubService" => {
            aliases.insert(String::from("GitHubService"));
        }
        UseTree::Rename(rename) if inside_larch_core && rename.ident == "GitHubService" => {
            aliases.insert(rename.rename.to_string());
        }
        UseTree::Glob(_) if inside_larch_core => *glob = true,
        UseTree::Group(group) => {
            for item in &group.items {
                collect_github_service_aliases(item, inside_larch_core, aliases, glob);
            }
        }
        _ => {}
    }
}

fn qualified_rust_write_method(call: &Expr, visitor: &RustMutationVisitor) -> Option<String> {
    let Expr::Path(path) = call else {
        return None;
    };
    let method = path.path.segments.last()?.ident.to_string();
    if !RUST_WRITE_METHODS.contains(&method.as_str()) {
        return None;
    }
    let owner = path
        .path
        .segments
        .iter()
        .rev()
        .nth(1)
        .map(|segment| segment.ident.to_string())?;
    (owner == "GitHubService"
        || visitor.github_service_glob
        || visitor.github_service_aliases.contains(&owner))
    .then_some(method)
}

fn has_test_attribute(attributes: &[syn::Attribute]) -> bool {
    attributes.iter().any(|attribute| {
        attribute
            .path()
            .segments
            .last()
            .is_some_and(|segment| segment.ident == "test")
            || (attribute.path().is_ident("cfg")
                && attribute
                    .meta
                    .require_list()
                    .is_ok_and(|list| list.tokens.to_string().contains("test")))
    })
}

fn line_number_span(span: proc_macro2::Span) -> u32 {
    u32::try_from(span.start().line).unwrap_or(1)
}

fn command_mutation(words: &[String], gh_wrapper: bool) -> Option<MutationKind> {
    if words.windows(3).any(|window| {
        executable_name(&window[0]) == "gh" && window[1] == "issue" && window[2] == "edit"
    }) || (gh_wrapper
        && words
            .windows(2)
            .any(|window| window[0] == "issue" && window[1] == "edit"))
    {
        return Some(MutationKind::Cli);
    }
    if has_patch(words) && words.iter().any(|word| is_issue_endpoint(word)) {
        return Some(MutationKind::Rest);
    }
    GRAPHQL_MUTATIONS
        .iter()
        .copied()
        .find(|mutation| words.iter().any(|word| word.contains(mutation)))
        .map(MutationKind::GraphQl)
}

fn has_patch(words: &[String]) -> bool {
    words.iter().any(|word| word.eq_ignore_ascii_case("PATCH"))
}

fn is_issue_endpoint(word: &str) -> bool {
    let path = word
        .split_once('?')
        .map_or(word, |(path, _)| path)
        .strip_prefix("https://api.github.com/")
        .unwrap_or(word)
        .trim_start_matches('/');
    let parts: Vec<&str> = path.split('/').collect();
    matches!(
        parts.as_slice(),
        ["repos", repository, "issues", issue]
            if repository.starts_with(['{', '$']) && !issue.is_empty()
    ) || matches!(
        parts.as_slice(),
        ["repos", owner, repo, "issues", issue]
            if !owner.is_empty() && !repo.is_empty() && !issue.is_empty()
    )
}

fn check_commands(path: &str, commands: Vec<ShellCommand>) -> Result<Vec<Finding>, LintError> {
    commands
        .into_iter()
        .filter_map(|command| {
            command_mutation(command.words(), false).map(|kind| (command.line(), kind))
        })
        .map(|(line, kind)| Ok(Finding::new(path, line_number(path, line)?, kind.message())))
        .collect()
}

fn executable_name(word: &str) -> &str {
    word.rsplit('/').next().unwrap_or(word)
}

fn check_markdown(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    check_commands(path, markdown_shell_commands(source)?)
}

fn check_json(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    check_commands(path, json_shell_commands(path, source)?)
}

fn line_number(path: &str, line: usize) -> Result<u32, LintError> {
    u32::try_from(line).map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))
}
