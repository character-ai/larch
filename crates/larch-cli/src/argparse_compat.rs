//! Shared `argparse`-compatible argument handling for migrated Python commands.
//!
//! The Python commands this crate replaces were parsed by `argparse`, and their
//! callers branch on exit codes and on the exact usage and error text. These
//! helpers own the shared spelling rules — inline `--name=value`, unambiguous
//! prefix abbreviation, negative-number values, and `unrecognized arguments`
//! rendering — so each command module states only its own option table.

use std::{
    env,
    ffi::{OsStr, OsString},
    fmt::Write as _,
    io::{self, Read as _, Write as _},
    path::{Path, PathBuf},
    process::ExitCode,
};
#[rustfmt::skip]
static PYTHON_NONPRINTABLE: std::sync::LazyLock<regex::Regex> = std::sync::LazyLock::new(|| regex::Regex::new(r"^[\p{C}\p{Z}]$").expect("static Python printability regex"));

/// One command line as `argparse` would have interpreted it.
#[derive(Debug, Default)]
pub struct ParsedCommandLine {
    values: Vec<(&'static str, OsString)>,
    positionals: Vec<OsString>,
    flags: Vec<&'static str>,
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

    /// Return every value supplied for `option`, in command-line order.
    ///
    /// This is `argparse`'s `action="append"`, where a repeated option collects
    /// rather than overwrites.
    #[must_use]
    pub fn values(&self, option: &str) -> Vec<&OsStr> {
        self.values
            .iter()
            .filter(|(name, _value)| *name == option)
            .map(|(_name, value)| value.as_os_str())
            .collect()
    }

    /// Return every `(option, value)` pair in command-line order.
    ///
    /// `argparse` converts a typed value the moment it consumes it, so a command
    /// whose options declare `type=int` must report the first bad spelling on
    /// the line rather than the first bad option in its table.
    #[must_use]
    pub fn entries(&self) -> &[(&'static str, OsString)] {
        &self.values
    }

    /// Return whether a valueless `store_true` flag was supplied.
    #[must_use]
    pub fn flag(&self, name: &str) -> bool {
        self.flags.contains(&name)
    }

    /// Return the positional argument at `index`, when one was supplied.
    #[must_use]
    pub fn positional(&self, index: usize) -> Option<&OsStr> {
        self.positionals.get(index).map(OsString::as_os_str)
    }

    /// Return only the error `argparse` raises while consuming the line.
    ///
    /// This precedes the required-argument and unrecognized-argument checks, so
    /// a command with required options reports it first, exactly as `argparse`
    /// does when it fails mid-parse.
    #[must_use]
    pub fn value_error(&self) -> Option<&str> {
        self.error.as_deref()
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

/// Render the `argparse` message for the required options that were absent.
#[must_use]
pub fn missing(options: &[(&str, bool)]) -> String {
    let absent: Vec<&str> = options
        .iter()
        .filter(|(_name, present)| !present)
        .map(|(name, _present)| *name)
        .collect();
    format!(
        "the following arguments are required: {}",
        absent.join(", ")
    )
}

/// Publish one `argparse`-shaped usage refusal under `code`.
pub fn usage_error(usage: &str, program: &str, error: &str, code: u8) -> ExitCode {
    eprintln!("{usage}\n{program}: error: {error}");
    ExitCode::from(code)
}

/// Parse a flag-and-value command surface with shared `argparse` ordering.
///
/// Help wins only after the parser has consumed the preceding command line;
/// required arguments precede surplus-argument diagnostics.
pub fn parse_required_with_help(
    arguments: &[OsString],
    program: &str,
    usage: &str,
    help: &str,
    values: &[&'static str],
    flags: &[&'static str],
    required: &[&str],
) -> Result<ParsedCommandLine, ExitCode> {
    let mut all_flags = flags.to_vec();
    all_flags.extend(["-h", "--help"]);
    parse_required_with_help_mode(
        parse_with_flags(arguments, values, &all_flags, 0),
        program,
        usage,
        help,
        required,
        true,
    )
}

/// Parse a compatibility surface that accepts future caller-owned options.
///
/// Help, missing values, and required options retain the shared `argparse`
/// ordering, while surplus options remain available for wrapper evolution.
pub fn parse_required_with_help_allow_unknown(
    arguments: &[OsString],
    program: &str,
    usage: &str,
    help: &str,
    values: &[&'static str],
    flags: &[&'static str],
    required: &[&str],
) -> Result<ParsedCommandLine, ExitCode> {
    let mut all_flags = flags.to_vec();
    all_flags.extend(["-h", "--help"]);
    parse_required_with_help_mode(
        parse_with_flags(arguments, values, &all_flags, 0),
        program,
        usage,
        help,
        required,
        false,
    )
}

fn parse_required_with_help_mode(
    parsed: ParsedCommandLine,
    program: &str,
    usage: &str,
    help: &str,
    required: &[&str],
    reject_unknown: bool,
) -> Result<ParsedCommandLine, ExitCode> {
    if parsed.flag("-h") || parsed.flag("--help") {
        println!("{help}");
        return Err(ExitCode::SUCCESS);
    }
    if let Some(error) = parsed.value_error() {
        return Err(usage_error(usage, program, error, 2));
    }
    let states: Vec<_> = required
        .iter()
        .map(|name| (*name, parsed.value(name).is_some()))
        .collect();
    if states.iter().any(|(_, present)| !present) {
        return Err(usage_error(usage, program, &missing(&states), 2));
    }
    if reject_unknown && let Some(error) = parsed.error() {
        return Err(usage_error(usage, program, &error, 2));
    }
    Ok(parsed)
}

/// Refuse a parsed line that is missing required options or still has errors.
pub fn finish_parse(
    parsed: ParsedCommandLine,
    usage: &str,
    program: &str,
    required: &[&str],
) -> Result<ParsedCommandLine, ExitCode> {
    if let Some(error) = parsed.value_error() {
        return Err(usage_error(usage, program, error, 2));
    }
    let required_state: Vec<(&str, bool)> = required
        .iter()
        .map(|option| (*option, parsed.value(option).is_some()))
        .collect();
    if required_state.iter().any(|(_option, present)| !present) {
        return Err(usage_error(usage, program, &missing(&required_state), 2));
    }
    if let Some(error) = parsed.error() {
        return Err(usage_error(usage, program, &error, 2));
    }
    Ok(parsed)
}

/// Return the first `argparse` invalid-choice or ambiguous-option error.
#[must_use]
pub fn choice_error(
    arguments: &[OsString],
    options: &[&'static str],
    choices: &[(&str, &[&str])],
) -> Option<String> {
    let mut index = 0;
    while index < arguments.len() {
        let text = arguments[index].to_string_lossy();
        index += 1;
        if text == "--" {
            break;
        }
        if !looks_like_option(&arguments[index - 1]) {
            continue;
        }
        let (name, inline) = split_inline_option(&text);
        if resolve_option(name, &["-h", "--help"]).is_some() {
            break;
        }
        let Some(option) = resolve_option(name, options) else {
            let matches = options
                .iter()
                .filter(|candidate| candidate.starts_with(name))
                .copied()
                .collect::<Vec<_>>();
            if matches.len() > 1 {
                return Some(format!(
                    "ambiguous option: {text} could match {}",
                    matches.join(", ")
                ));
            }
            continue;
        };
        let value = if let Some(value) = inline {
            value.to_owned()
        } else {
            let value = arguments.get(index)?;
            if looks_like_option(value) {
                return None;
            }
            index += 1;
            value.to_string_lossy().into_owned()
        };
        let Some((_option, allowed)) = choices.iter().find(|(choice, _allowed)| *choice == option)
        else {
            continue;
        };
        if !allowed.contains(&value.as_str()) {
            return Some(format!(
                "argument {option}: invalid choice: {} (choose from {})",
                python_repr(&value),
                allowed
                    .iter()
                    .map(|choice| python_repr(choice))
                    .collect::<Vec<_>>()
                    .join(", ")
            ));
        }
    }
    None
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
    parse_with_flags(arguments, options, &[], max_positionals)
}

/// Parse `arguments` where `flags` name valueless `store_true` actions.
///
/// A flag supplied as `--name=value` is the `argparse` "ignored explicit
/// argument" error, not a value assignment.
#[must_use]
pub fn parse_with_flags(
    arguments: &[OsString],
    options: &[&'static str],
    flags: &[&'static str],
    max_positionals: usize,
) -> ParsedCommandLine {
    parse_with_flags_and_exact(arguments, options, &[], flags, max_positionals)
}

/// Parse with additional value options that require their complete spelling.
///
/// This lets a migrated command extend a retired `argparse` surface without
/// making an existing abbreviation ambiguous.
#[must_use]
pub fn parse_with_flags_and_exact(
    arguments: &[OsString],
    options: &[&'static str],
    exact_options: &[&'static str],
    flags: &[&'static str],
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
        if let Some(flag) = resolve_option(name, flags) {
            if let Some(value) = inline {
                parsed.error = Some(format!(
                    "argument {flag}: ignored explicit argument '{value}'"
                ));
                return parsed;
            }
            parsed.flags.push(flag);
            continue;
        }
        let exact = exact_options
            .iter()
            .find(|option| **option == name)
            .copied();
        let Some(option) = exact.or_else(|| resolve_option(name, options)) else {
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

/// Take an option's inline value, or consume the next positional argument.
///
/// `index` advances past a consumed value so the caller's loop stays in step.
///
/// # Errors
///
/// Returns `missing` when a value-taking option ends the argument list.
pub fn take_option_value(
    values: &[String],
    index: &mut usize,
    inline: Option<&str>,
    missing: &'static str,
) -> Result<String, &'static str> {
    if let Some(value) = inline {
        return Ok(value.to_owned());
    }
    *index += 1;
    values.get(*index).cloned().ok_or(missing)
}

/// Decode every argument as UTF-8 for a compatibility parser.
///
/// # Errors
///
/// Returns `invalid` when any argument is not valid UTF-8.
pub fn utf8_arguments(
    arguments: &[OsString],
    invalid: &'static str,
) -> Result<Vec<String>, &'static str> {
    arguments
        .iter()
        .map(|argument| argument.to_str().map(str::to_owned).ok_or(invalid))
        .collect()
}

/// Return whether `value` reads as an option rather than a value.
///
/// Mirrors `argparse._parse_optional`: a `-`-prefixed token is a value when it
/// looks like a negative number, or when it contains a space. No declared long
/// option contains a space, so the space rule can never hide a real flag, and
/// it is what lets `--entry "- **Step 2 …**"` pass a leading-dash bullet.
#[must_use]
pub fn looks_like_option(value: &OsStr) -> bool {
    let text = value.to_string_lossy();
    if text == "-" || text.contains(' ') {
        return false;
    }
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

/// Report argparse `unrecognized arguments` using the shared option/flag tables.
#[must_use]
pub fn unrecognized_arguments(
    arguments: &[OsString],
    options: &[&str],
    flags: &[&str],
) -> Option<String> {
    let mut unknown = Vec::new();
    let mut positionals_only = false;
    let mut index = 0;
    while let Some(argument) = arguments.get(index) {
        let text = argument.to_string_lossy();
        if !positionals_only && text == "--" {
            positionals_only = true;
            unknown.push(argument.clone());
        } else if !positionals_only {
            let (name, inline) = split_inline_option(&text);
            if options.contains(&name) {
                if inline.is_none()
                    && arguments
                        .get(index + 1)
                        .is_some_and(|value| !looks_like_option(value))
                {
                    index += 1;
                }
            } else if !flags.contains(&name) {
                unknown.push(argument.clone());
            }
        } else {
            unknown.push(argument.clone());
        }
        index += 1;
    }
    (!unknown.is_empty()).then(|| format!("unrecognized arguments: {}", join_arguments(&unknown)))
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

/// Render a string with Python `repr` quoting and diagnostic-safe escapes.
#[must_use]
#[rustfmt::skip]
pub fn python_repr(value: &str) -> String {
    let quote = if value.contains('\'') && !value.contains('"') { '"' } else { '\'' };
    let mut output = String::from(quote);
    for character in value.chars() {
        match character {
            '\\' => output.push_str("\\\\"), '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"), '\t' => output.push_str("\\t"),
            '\u{08}' => output.push_str("\\x08"), '\u{0c}' => output.push_str("\\x0c"),
            escaped if escaped == quote => { output.push('\\'); output.push(escaped); }
            escaped if escaped != ' ' && PYTHON_NONPRINTABLE.is_match(&escaped.to_string()) => {
                let code = escaped as u32;
                let (prefix, width) = if code <= 0xff { ('x', 2) }
                    else if code <= 0xffff { ('u', 4) } else { ('U', 8) };
                output.push('\\'); output.push(prefix);
                let _ = write!(output, "{code:0width$x}");
            }
            other => output.push(other),
        }
    }
    output.push(quote);
    output
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

/// Read all of stdin as text, treating an unreadable or non-UTF-8 stream as the
/// bytes it could recover.
///
/// A command that reads stdin is fed by a heredoc or a pipe, so a read failure
/// is an empty payload rather than a reason to refuse.
#[must_use]
pub fn read_stdin() -> String {
    let mut buffer = Vec::new();
    let _read = io::stdin().lock().read_to_end(&mut buffer);
    String::from_utf8_lossy(&buffer).into_owned()
}

/// Render an I/O failure the way Python renders `OSError`.
///
/// Every command ported from a Python owner that let an `OSError` reach its
/// message text needs this spelling, so it lives beside the other `argparse`
/// compatibility helpers rather than once per command module.
#[must_use]
pub fn python_io_error(error: &io::Error, path: &Path) -> String {
    let Some(code) = error.raw_os_error() else {
        return error.to_string();
    };
    let rendered = error.to_string();
    let detail = rendered.split(" (os error ").next().unwrap_or("I/O error");
    format!(
        "[Errno {code}] {detail}: {}",
        python_repr(&path.to_string_lossy())
    )
}

/// Resolve a caller-supplied path against the working directory.
///
/// # Errors
///
/// Returns the working-directory lookup failure.
pub fn absolute_path(path: &Path) -> Result<PathBuf, io::Error> {
    if path.is_absolute() {
        Ok(path.to_path_buf())
    } else {
        Ok(env::current_dir()?.join(path))
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
        assert!(!looks_like_option(OsStr::new("- **Step 2: tool failed**")));
        assert_eq!(join_arguments(&arguments(&["a", "b"])), "a b");
    }
}
