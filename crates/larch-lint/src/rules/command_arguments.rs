//! `syn`-based resolution for static command arguments used by policy rules.

use std::collections::{BTreeMap, BTreeSet};

use proc_macro2::Span;
use syn::{
    Expr, ExprArray, ExprCall, ExprMethodCall, ExprPath, File, ItemConst, ItemStatic,
    PathArguments,
    spanned::Spanned,
    visit::{self, Visit},
};

use super::syn_helpers;

/// One command argument whose literal value may or may not be statically known.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(super) enum Argument {
    /// A literal string or a constant that resolves to one.
    Static(String),
    /// A dynamic expression whose eventual value is not known to the linter.
    Dynamic,
}

/// A statically recognizable `std::process::Command` builder chain.
#[derive(Clone, Debug)]
pub(super) struct BuilderCommand {
    /// Span of the original `Command::new` construction.
    pub(super) root_span: Span,
    /// Arguments accumulated across the builder calls.
    pub(super) arguments: Vec<Argument>,
}

/// Constants available for resolving literal command arguments.
pub(super) struct Constants<'syntax> {
    values: BTreeMap<String, &'syntax Expr>,
}

impl<'syntax> Constants<'syntax> {
    /// Collect `const` and immutable `static` values from one parsed source file.
    #[must_use]
    pub(super) fn from_file(file: &'syntax File) -> Self {
        let mut collector = ConstantCollector {
            values: BTreeMap::new(),
        };
        collector.visit_file(file);
        Self {
            values: collector.values,
        }
    }

    /// Resolve an expression that represents one ordered argument sequence.
    #[must_use]
    pub(super) fn arguments(&self, expression: &'syntax Expr) -> Option<Vec<Argument>> {
        self.arguments_inner(expression, &mut BTreeSet::new())
    }

    /// Resolve an expression that supplies exactly one command argument.
    #[must_use]
    pub(super) fn argument(&self, expression: &'syntax Expr) -> Argument {
        self.string_inner(expression, &mut BTreeSet::new())
            .map_or(Argument::Dynamic, Argument::Static)
    }

    fn arguments_inner(
        &self,
        expression: &'syntax Expr,
        resolving: &mut BTreeSet<String>,
    ) -> Option<Vec<Argument>> {
        match expression {
            Expr::Array(array) => Some(
                array
                    .elems
                    .iter()
                    .map(|element| self.string_inner(element, resolving))
                    .map(|value| value.map_or(Argument::Dynamic, Argument::Static))
                    .collect(),
            ),
            Expr::Reference(reference) => self.arguments_inner(&reference.expr, resolving),
            Expr::Paren(parenthesized) => self.arguments_inner(&parenthesized.expr, resolving),
            Expr::Path(path) => {
                let name = simple_path_name(path)?;
                let value = self.values.get(&name)?;
                if !resolving.insert(name.clone()) {
                    return None;
                }
                let arguments = self.arguments_inner(value, resolving);
                resolving.remove(&name);
                arguments
            }
            _ => None,
        }
    }

    fn string_inner(
        &self,
        expression: &'syntax Expr,
        resolving: &mut BTreeSet<String>,
    ) -> Option<String> {
        match expression {
            Expr::Path(path) => {
                let name = simple_path_name(path)?;
                let value = self.values.get(&name)?;
                if !resolving.insert(name.clone()) {
                    return None;
                }
                let string = self.string_inner(value, resolving);
                resolving.remove(&name);
                string
            }
            other => syn_helpers::string_literal(other),
        }
    }

    fn builder_command_inner(&self, expression: &'syntax Expr) -> Option<BuilderCommand> {
        match expression {
            Expr::MethodCall(method) => self.extend_builder(method),
            Expr::Call(call) => self.command_new(call),
            Expr::Paren(parenthesized) => self.builder_command_inner(&parenthesized.expr),
            _ => None,
        }
    }

    pub(super) fn extend_builder(&self, method: &'syntax ExprMethodCall) -> Option<BuilderCommand> {
        let mut command = self.builder_command_inner(&method.receiver)?;
        match method.method.to_string().as_str() {
            "arg" => {
                let argument = method.args.first()?;
                if method.args.len() != 1 {
                    return None;
                }
                command.arguments.push(self.argument(argument));
            }
            "args" => {
                let arguments = method.args.first()?;
                if method.args.len() != 1 {
                    return None;
                }
                command.arguments.extend(self.arguments(arguments)?);
            }
            _ => {}
        }
        Some(command)
    }

    fn command_new(&self, call: &'syntax ExprCall) -> Option<BuilderCommand> {
        if !is_command_new(&call.func) || call.args.len() != 1 {
            return None;
        }
        let executable = self.argument(call.args.first()?);
        Some(BuilderCommand {
            root_span: call.func.span(),
            arguments: vec![executable],
        })
    }
}

struct ConstantCollector<'syntax> {
    values: BTreeMap<String, &'syntax Expr>,
}

impl<'ast> Visit<'ast> for ConstantCollector<'ast> {
    fn visit_item_const(&mut self, item: &'ast ItemConst) {
        self.values.insert(item.ident.to_string(), &item.expr);
        visit::visit_item_const(self, item);
    }

    fn visit_item_static(&mut self, item: &'ast ItemStatic) {
        if matches!(item.mutability, syn::StaticMutability::None) {
            self.values.insert(item.ident.to_string(), &item.expr);
        }
        visit::visit_item_static(self, item);
    }
}

fn simple_path_name(path: &ExprPath) -> Option<String> {
    (path.qself.is_none() && path.path.segments.len() == 1)
        .then(|| path.path.segments.first())
        .flatten()
        .filter(|segment| matches!(segment.arguments, PathArguments::None))
        .map(|segment| segment.ident.to_string())
}

fn is_command_new(function: &Expr) -> bool {
    let Expr::Path(path) = function else {
        return false;
    };
    if path.qself.is_some() {
        return false;
    }
    let segments: Vec<_> = path.path.segments.iter().collect();
    if !segments
        .iter()
        .all(|segment| matches!(segment.arguments, PathArguments::None))
    {
        return false;
    }
    match segments.as_slice() {
        [command, new] => command.ident == "Command" && new.ident == "new",
        [process, command, new] => {
            process.ident == "process" && command.ident == "Command" && new.ident == "new"
        }
        [standard, process, command, new] => {
            standard.ident == "std"
                && process.ident == "process"
                && command.ident == "Command"
                && new.ident == "new"
        }
        _ => false,
    }
}

/// Return the arguments from a direct array expression, if it has one.
#[must_use]
pub(super) fn array_arguments<'syntax>(
    constants: &Constants<'syntax>,
    array: &'syntax ExprArray,
) -> Vec<Argument> {
    array
        .elems
        .iter()
        .map(|element| constants.argument(element))
        .collect()
}
