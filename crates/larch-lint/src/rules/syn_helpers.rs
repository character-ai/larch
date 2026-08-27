//! Small shared `syn` helpers for rule implementations.

use std::collections::BTreeSet;

use proc_macro2::{TokenStream, TokenTree};
use syn::{Attribute, Expr, Meta, Pat, UseTree};

/// Imported spellings that resolve to `std` or Tokio's process `Command`.
#[derive(Clone, Default)]
pub(super) struct ProcessCommandAliases {
    command_aliases: BTreeSet<String>,
    process_aliases: BTreeSet<String>,
}

impl ProcessCommandAliases {
    /// Record one `use` tree, including grouped and renamed imports.
    pub(super) fn collect_use(&mut self, tree: &UseTree) {
        self.collect_use_with_prefix(tree, &[]);
    }

    fn collect_use_with_prefix(&mut self, tree: &UseTree, prefix: &[String]) {
        match tree {
            UseTree::Path(path) => {
                let mut next = prefix.to_vec();
                next.push(path.ident.to_string());
                self.collect_use_with_prefix(&path.tree, &next);
            }
            UseTree::Name(name) => {
                self.record_import(prefix, &name.ident.to_string(), &name.ident.to_string());
            }
            UseTree::Rename(rename) => self.record_import(
                prefix,
                &rename.ident.to_string(),
                &rename.rename.to_string(),
            ),
            UseTree::Glob(_)
                if matches!(prefix, [root, process] if (root == "std" || root == "tokio") && process == "process") =>
            {
                let _ = self.command_aliases.insert("Command".to_owned());
            }
            UseTree::Group(group) => {
                for item in &group.items {
                    self.collect_use_with_prefix(item, prefix);
                }
            }
            UseTree::Glob(_) => {}
        }
    }

    fn record_import(&mut self, prefix: &[String], imported: &str, local: &str) {
        let mut full = prefix.to_vec();
        if imported != "self" {
            full.push(imported.to_owned());
        }
        if matches!(full.as_slice(), [root, process, command] if (root == "std" || root == "tokio") && process == "process" && command == "Command")
        {
            let _ = self.command_aliases.insert(local.to_owned());
        }
        if matches!(full.as_slice(), [root, process] if (root == "std" || root == "tokio") && process == "process")
        {
            let _ = self.process_aliases.insert(local.to_owned());
        }
    }

    /// Return whether a path resolves to a process `Command::new` constructor.
    pub(super) fn is_constructor_path(&self, path: &syn::Path) -> bool {
        let segments: Vec<String> = path
            .segments
            .iter()
            .map(|segment| segment.ident.to_string())
            .collect();
        if segments.last().is_none_or(|segment| segment != "new") {
            return false;
        }
        let prefix = &segments[..segments.len().saturating_sub(1)];
        matches!(prefix, [root, process, command] if (root == "std" || root == "tokio") && process == "process" && command == "Command")
            || prefix.len() == 1 && self.command_aliases.contains(&prefix[0])
            || matches!(prefix, [process, command] if command == "Command" && self.process_aliases.contains(process))
    }
}

/// Return whether an item is available only under a `test` cfg predicate.
pub(super) fn has_cfg_test(attributes: &[Attribute]) -> bool {
    attributes.iter().any(|attribute| {
        attribute.path().is_ident("cfg")
            && matches!(&attribute.meta, Meta::List(list) if tokens_have_test_ident(&list.tokens))
    })
}

fn tokens_have_test_ident(tokens: &TokenStream) -> bool {
    tokens.clone().into_iter().any(|token| match token {
        TokenTree::Ident(ident) => ident == "test",
        TokenTree::Group(group) => tokens_have_test_ident(&group.stream()),
        _ => false,
    })
}

/// Return the simple identifier bound by a pattern, if any.
#[must_use]
pub(super) fn pattern_name(pattern: &Pat) -> Option<String> {
    match pattern {
        Pat::Ident(ident) => Some(ident.ident.to_string()),
        Pat::Type(typed) => pattern_name(&typed.pat),
        _ => None,
    }
}

/// Return a string literal expression's value.
#[must_use]
pub(super) fn string_literal(expression: &Expr) -> Option<String> {
    match expression {
        Expr::Lit(literal) => match &literal.lit {
            syn::Lit::Str(value) => Some(value.value()),
            _ => None,
        },
        Expr::Reference(reference) => string_literal(&reference.expr),
        Expr::Paren(parenthesized) => string_literal(&parenthesized.expr),
        _ => None,
    }
}
