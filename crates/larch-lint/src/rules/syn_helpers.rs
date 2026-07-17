//! Small shared `syn` helpers for rule implementations.

use syn::{Expr, Pat};

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
