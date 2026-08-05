//! Shared `argparse`-compatible argument handling for migrated Python commands.
//!
//! The Python commands this crate replaces were parsed by `argparse`, and their
//! callers branch on exit codes and on the exact usage and error text. These
//! helpers own the shared spelling rules — inline `--name=value`, unambiguous
//! prefix abbreviation, negative-number values, and `unrecognized arguments`
//! rendering — so each command module states only its own option table.

use std::{
    ffi::{OsStr, OsString},
    io::{self, Write as _},
    process::ExitCode,
};

/// One command line as `argparse` would have interpreted it.
#[derive(Debug, Default)]
pub struct ParsedCommandLine {
    values: Vec<(&'static str, OsString)>,
    positionals: Vec<OsString>,
    unrecognized: Vec<OsString>,
    error: Option<String>,
}

impl ParsedCommandLine {
    /// Return the last value supplied for `option`, matching last-wins semantics.
    pub fn value(&self, option: &str) -> Option<&OsStr> {
        self.values
            .iter()
            .rev()
            .find(|(name, _value)| *name == option)
            .map(|(_name, value)| value.as_os_str())
    }

    /// Return the positional argument at `index`, when one was supplied.
    #[must_use]
    pub fn positional(&self, index: usize) -> Option<&OsStr> {
        self.positionals.get(index).map(OsString::as_os_str)
    }

    /// Return the `argparse` error text, or `None` when the line parsed cleanly.
    #[must_use]
    pub fn error(&self) -> Option<String> {
        if let Some(error) = &self.error {
            return Some(error.clone());
        }
        if self.unrecognized.is_empty() {
            return None;
        }
        Some(format!(
            "unrecognized arguments: {}",
            join_arguments(&self.unrecognized)
        ))
    }
}

/// Parse `arguments` against a closed option table and a positional budget.
///
/// `options` lists the long flags that take exactly one value. `max_positionals`
/// bounds the positional actions the command declares; surplus positionals become
/// `unrecognized arguments`, and a bare `--` is consumed only when the command
/// declares at least one positional, matching `argparse`.
#[must_use]
pub fn parse(
    arguments: &[OsString],
    options: &[&'static str],
    max_positionals: usize,
) -> ParsedCommandLine {
    let mut parsed = ParsedCommandLine::default();
    let mut positional_only = false;
    let mut index = 0;
    while index < arguments.len() {
        let argument = &arguments[index];
        index += 1;
        let text = argument.to_string_lossy();
        if !positional_only && text == "--" {
            positional_only = true;
            if max_positionals == 0 {
                parsed.unrecognized.push(argument.clone());
            }
            continue;
        }
        if positional_only || !looks_like_option(argument) {
            if parsed.positionals.len() < max_positionals {
                parsed.positionals.push(argument.clone());
            } else {
                parsed.unrecognized.push(argument.clone());
            }
            continue;
        }
        let (name, inline) = split_inline_option(&text);
        let Some(option) = resolve_option(name, options) else {
            parsed.unrecognized.push(argument.clone());
            continue;
        };
        let value = if let Some(value) = inline {
            OsString::from(value)
        } else {
            match arguments.get(index) {
                Some(value) if !looks_like_option(value) => {
                    index += 1;
                    value.clone()
                }
                _ => {
                    parsed.error = Some(format!("argument {option}: expected one argument"));
                    return parsed;
                }
            }
        };
        parsed.values.push((option, value));
    }
    parsed
}

/// Resolve a supplied flag spelling to its canonical option name.
///
/// An exact match wins. Otherwise `argparse` accepts an abbreviation only when
/// exactly one option starts with it.
#[must_use]
pub fn resolve_option(name: &str, options: &[&'static str]) -> Option<&'static str> {
    if let Some(exact) = options.iter().find(|option| **option == name) {
        return Some(exact);
    }
    if name.len() <= 2 {
        return None;
    }
    let mut matches = options.iter().filter(|option| option.starts_with(name));
    let first = matches.next()?;
    matches.next().is_none().then_some(*first)
}

/// Split `--name=value` into its parts, leaving a bare flag's value absent.
#[must_use]
pub fn split_inline_option(option: &str) -> (&str, Option<&str>) {
    option
        .split_once('=')
        .map_or((option, None), |(name, value)| (name, Some(value)))
}

/// Return whether `value` reads as an option rather than a negative number.
#[must_use]
pub fn looks_like_option(value: &OsStr) -> bool {
    let text = value.to_string_lossy();
    let negative_number = text.strip_prefix('-').is_some_and(|number| {
        number.bytes().any(|byte| byte.is_ascii_digit())
            && number
                .bytes()
                .all(|byte| byte.is_ascii_digit() || byte == b'.')
            && number.bytes().filter(|byte| *byte == b'.').count() <= 1
            && number
                .split_once('.')
                .is_none_or(|(_whole, fraction)| !fraction.is_empty())
    });
    text.starts_with('-') && !negative_number
}

/// Render arguments the way `argparse` renders an `unrecognized arguments` list.
#[must_use]
pub fn join_arguments(arguments: &[OsString]) -> String {
    arguments
        .iter()
        .map(|argument| argument.to_string_lossy())
        .collect::<Vec<_>>()
        .join(" ")
}

/// Write exact text to stdout, reporting a broken pipe as a failure exit.
pub fn write_stdout(text: &str) -> ExitCode {
    if io::stdout().lock().write_all(text.as_bytes()).is_ok() {
        ExitCode::SUCCESS
    } else {
        ExitCode::FAILURE
    }
}

/// Write exact bytes plus one newline to stdout.
pub fn write_stdout_line(value: &[u8]) -> ExitCode {
    let mut stdout = io::stdout().lock();
    if stdout.write_all(value).is_ok() && stdout.write_all(b"\n").is_ok() {
        ExitCode::SUCCESS
    } else {
        ExitCode::FAILURE
    }
}

#[cfg(test)]
mod tests {
    use super::{join_arguments, looks_like_option, parse, resolve_option, split_inline_option};
    use std::ffi::{OsStr, OsString};

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    #[test]
    fn options_accept_inline_values_and_unambiguous_abbreviations() {
        let parsed = parse(
            &arguments(&["--out=first", "--outp", "second"]),
            &["--output"],
            0,
        );

        assert_eq!(parsed.error(), None);
        assert_eq!(parsed.value("--output"), Some(OsStr::new("second")));
    }

    #[test]
    fn ambiguous_abbreviations_and_unknown_flags_are_unrecognized() {
        assert_eq!(
            resolve_option("--dir", &["--dir", "--directory"]),
            Some("--dir")
        );
        assert_eq!(
            resolve_option("--dire", &["--dir", "--directory"]),
            Some("--directory")
        );
        assert_eq!(resolve_option("--d", &["--dir", "--directory"]), None);

        let parsed = parse(&arguments(&["--bogus", "--dir", "x"]), &["--dir"], 0);

        assert_eq!(
            parsed.error(),
            Some("unrecognized arguments: --bogus".to_owned())
        );
    }

    #[test]
    fn a_missing_value_reports_the_argparse_error_and_stops() {
        let parsed = parse(&arguments(&["--cwd"]), &["--cwd"], 0);

        assert_eq!(
            parsed.error(),
            Some("argument --cwd: expected one argument".to_owned())
        );

        let negative = parse(&arguments(&["--cwd", "-1.5"]), &["--cwd"], 0);

        assert_eq!(negative.value("--cwd"), Some(OsStr::new("-1.5")));
    }

    #[test]
    fn positional_budget_matches_the_declared_actions() {
        let one = parse(&arguments(&["alpha", "beta"]), &[], 1);

        assert_eq!(one.positional(0), Some(OsStr::new("alpha")));
        assert_eq!(one.error(), Some("unrecognized arguments: beta".to_owned()));

        let separator_with_positional = parse(&arguments(&["--", "--alpha"]), &[], 1);

        assert_eq!(
            separator_with_positional.positional(0),
            Some(OsStr::new("--alpha"))
        );
        assert_eq!(separator_with_positional.error(), None);

        let separator_without_positional = parse(&arguments(&["--"]), &[], 0);

        assert_eq!(
            separator_without_positional.error(),
            Some("unrecognized arguments: --".to_owned())
        );
    }

    #[test]
    fn spelling_helpers_match_the_python_boundary() {
        assert_eq!(split_inline_option("--key=value"), ("--key", Some("value")));
        assert_eq!(split_inline_option("--key"), ("--key", None));
        assert!(looks_like_option(OsStr::new("--flag")));
        assert!(!looks_like_option(OsStr::new("-12")));
        assert!(looks_like_option(OsStr::new("-1.2.3")));
        assert_eq!(join_arguments(&arguments(&["a", "b"])), "a b");
    }
}
