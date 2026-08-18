//! Rust owner for the `/fluff-analysis` CLI surface.
//!
//! Mirrors the retired Python analyzer's argparse contract: identical usage,
//! help, typed-option errors, `WARN:` cutoff diagnostics, `wrote FILE` on
//! stderr for `--out`, and exit `2` for a missing or unsynchronizable log
//! root.

use std::{env, ffi::OsString, fs, path::PathBuf, process::ExitCode};

use larch_core::{FluffOptions, parse_cutoff_text, parse_larch_version_tuple};

use crate::{
    argparse_compat::{
        optional_out_path, parse_with_flags, python_repr, usage_error, write_stdout,
    },
    run_log_publication_commands::{synchronized_corpus_root, synchronized_repository_root},
};

const PROGRAM: &str = "fluff-analysis analyze";
const USAGE: &str = "usage: fluff-analysis analyze [-h] [--log-root LOG_ROOT] [--sessions-dir SESSIONS_DIR] [--include-in-progress] [--inprogress-since INPROGRESS_SINCE] [--cutoff CUTOFF] [--since-version X.Y.Z] [--min-group MIN_GROUP] [--out OUT] [--post-only-tags]";
const HELP: &str = "\
usage: fluff-analysis analyze [-h] [--log-root LOG_ROOT] [--sessions-dir SESSIONS_DIR] [--include-in-progress] [--inprogress-since INPROGRESS_SINCE] [--cutoff CUTOFF] [--since-version X.Y.Z] [--min-group MIN_GROUP] [--out OUT] [--post-only-tags]

Analyze review fluff from synchronized larch run logs.

options:
  -h, --help            show this help message and exit
  --log-root LOG_ROOT   offline fixture corpus override; default synchronizes
                        the current repository cache
  --sessions-dir SESSIONS_DIR
                        larch session cache dir (for --include-in-progress)
  --include-in-progress
                        also read in-progress design session temp dirs (racy
                        snapshot)
  --inprogress-since INPROGRESS_SINCE
                        ISO8601 lower bound for in-progress session mtime
  --cutoff CUTOFF       ISO8601 timestamp enabling a pre/post comparison
                        section
  --since-version X.Y.Z
                        larch_version threshold enabling version-based
                        pre/post comparison
  --min-group MIN_GROUP
                        minimum findings for a semantic group to appear
                        (default 20)
  --out OUT             write report to FILE instead of stdout
  --post-only-tags      compute semantic tags only for post-cutoff/version
                        records; pre-period records get empty tags (faster
                        corpus scans)";

const VALUE_OPTIONS: [&str; 7] = [
    "--log-root",
    "--sessions-dir",
    "--inprogress-since",
    "--cutoff",
    "--since-version",
    "--min-group",
    "--out",
];
const FLAG_OPTIONS: [&str; 4] = ["--include-in-progress", "--post-only-tags", "-h", "--help"];

/// Analyze review fluff over one synchronized or explicit run-log corpus.
#[must_use]
pub fn analyze(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(arguments, &VALUE_OPTIONS, &FLAG_OPTIONS, 0);
    if parsed.flag("-h") || parsed.flag("--help") {
        println!("{HELP}");
        return ExitCode::SUCCESS;
    }
    let (min_group, since_version) = match parse_typed_options(&parsed) {
        Ok(values) => values,
        Err(code) => return code,
    };
    if let Some(error) = parsed.value_error() {
        return usage_error(USAGE, PROGRAM, error, 2);
    }
    if let Some(error) = parsed.error() {
        return usage_error(USAGE, PROGRAM, &error, 2);
    }

    let explicit_root = parsed
        .value("--log-root")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from);
    let log_root = match explicit_root {
        Some(root) => root,
        None => match default_log_root() {
            Ok(root) => root,
            Err(error) => {
                eprintln!("ERROR: {error}");
                return ExitCode::from(2);
            }
        },
    };
    if !log_root.is_dir() {
        eprintln!("ERROR: log root not found: {}", log_root.display());
        return ExitCode::from(2);
    }

    let cutoff = parse_time_option(
        parsed
            .value("--cutoff")
            .map(|value| value.to_string_lossy().into_owned()),
    );
    let inprogress_min = parse_time_option(
        parsed
            .value("--inprogress-since")
            .map(|value| value.to_string_lossy().into_owned()),
    )
    .map(larch_core::PyTimestamp::epoch_seconds);

    let sessions_dir = parsed
        .value("--sessions-dir")
        .map_or_else(default_sessions_dir, |value| {
            PathBuf::from(value.to_owned())
        });

    let report = larch_core::fluff_analysis_report(&FluffOptions {
        log_root,
        sessions_dir,
        include_in_progress: parsed.flag("--include-in-progress"),
        cutoff,
        inprogress_min,
        since_version,
        min_group,
        post_only_tags: parsed.flag("--post-only-tags"),
    });

    let Some(output) = optional_out_path(&parsed) else {
        return write_stdout(&report);
    };
    if let Err(error) = fs::write(&output, report) {
        eprintln!("{error}");
        return ExitCode::FAILURE;
    }
    eprintln!("wrote {}", output.display());
    ExitCode::SUCCESS
}

type SinceVersion = Option<(u64, u64, u64)>;

/// Validate the typed options in consumption order.
///
/// argparse converts a typed value the moment it consumes it, so typed errors
/// on consumed options precede a later missing-value stop and the
/// end-of-parse unrecognized-arguments report.
fn parse_typed_options(
    parsed: &crate::argparse_compat::ParsedCommandLine,
) -> Result<(u64, SinceVersion), ExitCode> {
    let mut min_group: u64 = 20;
    let mut since_version = None;
    for (option, value) in parsed.entries() {
        let value = value.to_string_lossy();
        match *option {
            "--min-group" => match parse_python_int(&value) {
                Some(parsed_value) => min_group = parsed_value.max(1),
                None => {
                    return Err(usage_error(
                        USAGE,
                        PROGRAM,
                        &format!(
                            "argument --min-group: invalid int value: {}",
                            python_repr(&value)
                        ),
                        2,
                    ));
                }
            },
            "--since-version" => {
                if value.is_empty() {
                    // Python `parse_since_version("")` returns None silently.
                    since_version = None;
                } else if let Some(version) = parse_larch_version_tuple(&value) {
                    since_version = Some(version);
                } else {
                    return Err(usage_error(
                        USAGE,
                        PROGRAM,
                        "argument --since-version: expected X.Y.Z",
                        2,
                    ));
                }
            }
            _ => {}
        }
    }
    Ok((min_group, since_version))
}

/// Parse a `--cutoff`-style value with the Python analyzer's warning contract:
/// an unset or empty value is `None`, and an unparseable value warns (always
/// naming `--cutoff`, matching the frozen script) and disables the section.
fn parse_time_option(raw: Option<String>) -> Option<larch_core::PyTimestamp> {
    let raw = raw.filter(|value| !value.is_empty())?;
    let parsed = parse_cutoff_text(&raw);
    if parsed.is_none() {
        eprintln!(
            "WARN: could not parse --cutoff {}; pre/post section disabled",
            python_repr(&raw)
        );
    }
    parsed
}

/// Parse an integer the way Python `int(str)` does through the shared signed
/// parser. Negative values clamp to `0` for the caller's `max(1, …)`.
fn parse_python_int(raw: &str) -> Option<u64> {
    crate::argparse_compat::parse_python_int(raw).map(|value| u64::try_from(value).unwrap_or(0))
}

fn default_sessions_dir() -> PathBuf {
    env::var_os("HOME").map_or_else(
        || PathBuf::from("~/.cache/larch/sessions"),
        |home| PathBuf::from(home).join(".cache/larch/sessions"),
    )
}

fn default_log_root() -> Result<PathBuf, String> {
    synchronized_corpus_root(&synchronized_repository_root()?)
}

#[cfg(test)]
mod tests {
    use super::parse_python_int;

    #[test]
    fn python_int_spellings_parse_like_int() {
        assert_eq!(parse_python_int(" 20 "), Some(20));
        assert_eq!(parse_python_int("+3"), Some(3));
        assert_eq!(parse_python_int("-7"), Some(0));
        assert_eq!(parse_python_int("1_0"), Some(10));
        assert_eq!(parse_python_int(""), None);
        assert_eq!(parse_python_int("_1"), None);
        assert_eq!(parse_python_int("1__0"), None);
        assert_eq!(parse_python_int("1_"), None);
        assert_eq!(parse_python_int("x"), None);
        assert_eq!(parse_python_int("1.5"), None);
    }
}
