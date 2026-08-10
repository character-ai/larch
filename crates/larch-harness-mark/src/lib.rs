//! Dependency-free inherited-stdio timing wrapper for developer and CI harnesses.
//!
//! This is deliberately separate from the released CLI so a fresh harness runner
//! does not compile the full product just to begin measuring a child command.

use std::{
    env,
    ffi::OsString,
    io,
    process::{Command, ExitCode},
    time::{Duration, SystemTime, UNIX_EPOCH},
};

/// Prefix for the existing child-duration row.
pub const HARNESS_TIMING_SENTINEL: &str = "LARCH_HARNESS_TIMING";
/// Prefix for the pre-child Cargo/bootstrap duration row.
pub const HARNESS_BOOTSTRAP_SENTINEL: &str = "LARCH_HARNESS_BOOTSTRAP";
/// Environment value sampled by the Makefile immediately before Cargo starts.
pub const HARNESS_BOOTSTRAP_START_NS_ENV: &str = "LARCH_HARNESS_BOOTSTRAP_START_NS";
/// Environment value describing whether the isolated binary already existed.
pub const HARNESS_BOOTSTRAP_KIND_ENV: &str = "LARCH_HARNESS_BOOTSTRAP_KIND";

const NANOSECONDS_PER_SECOND: u128 = 1_000_000_000;
const USAGE: &str = "timing harness-mark requires --label <label> -- <command> [args...]";

/// Run one harness child, emit its duration, and return its process exit code.
#[must_use]
pub fn harness_mark(arguments: &[OsString]) -> ExitCode {
    let values: Vec<String> = arguments
        .iter()
        .map(|value| value.to_string_lossy().into_owned())
        .collect();
    let Some((label, command)) = parse_arguments(&values) else {
        eprintln!("{USAGE}");
        return ExitCode::from(2);
    };

    emit_bootstrap_diagnostic(label);
    let started = SystemTime::now();
    let code = launch_child(command);
    let elapsed = started.elapsed().unwrap_or_default().as_secs_f64();
    println!("{HARNESS_TIMING_SENTINEL}\t{label}\t{elapsed:.2}s");
    ExitCode::from(code)
}

fn parse_arguments(values: &[String]) -> Option<(&str, &[String])> {
    let parsed = if values.first().is_some_and(|first| first == "--label") {
        (values.len() >= 4 && values[2] == "--").then_some((values[1].as_str(), &values[3..]))
    } else if values.len() >= 3 && values[1] == "--" {
        Some((values[0].as_str(), &values[2..]))
    } else if values.len() >= 2 {
        Some((values[0].as_str(), &values[1..]))
    } else {
        None
    };
    parsed.filter(|(_, command)| !command.is_empty())
}

fn emit_bootstrap_diagnostic(label: &str) {
    let Some(started) = bootstrap_started_at() else {
        return;
    };
    let Ok(elapsed) = SystemTime::now().duration_since(started) else {
        return;
    };
    println!(
        "{HARNESS_BOOTSTRAP_SENTINEL}\t{label}\t{}\t{:.2}s",
        bootstrap_kind(),
        elapsed.as_secs_f64()
    );
}

fn bootstrap_started_at() -> Option<SystemTime> {
    let raw = env::var(HARNESS_BOOTSTRAP_START_NS_ENV).ok()?;
    let nanoseconds = raw.parse::<u128>().ok()?;
    let seconds = u64::try_from(nanoseconds / NANOSECONDS_PER_SECOND).ok()?;
    let subsecond_nanoseconds = u32::try_from(nanoseconds % NANOSECONDS_PER_SECOND).ok()?;
    UNIX_EPOCH.checked_add(Duration::new(seconds, subsecond_nanoseconds))
}

fn bootstrap_kind() -> &'static str {
    match env::var(HARNESS_BOOTSTRAP_KIND_ENV).as_deref() {
        Ok("cold") => "cold",
        Ok("warm") => "warm",
        _ => "unknown",
    }
}

fn launch_child(command: &[String]) -> u8 {
    let Some(program) = command.first() else {
        return 2;
    };
    // The wrapper must inherit the caller's stdio and exit code verbatim; the
    // shared capturing runner cannot represent that arbitrary child contract.
    let launch = Command::new(program) // lint-subprocess-via-runner: ok dependency-free harness wrapper inherits arbitrary child stdio and exit status
        .args(&command[1..])
        .env_remove(HARNESS_BOOTSTRAP_START_NS_ENV)
        .env_remove(HARNESS_BOOTSTRAP_KIND_ENV)
        .status();
    match launch {
        Ok(status) => u8::try_from(status.code().unwrap_or(1)).unwrap_or(1),
        Err(error) => {
            eprintln!("timing harness-mark: {error}");
            match error.kind() {
                io::ErrorKind::PermissionDenied => 126,
                io::ErrorKind::NotFound => 127,
                _ => 1,
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::parse_arguments;

    #[test]
    fn parser_keeps_the_legacy_and_named_label_shapes() {
        let named = vec![
            "--label".to_owned(),
            "unit".to_owned(),
            "--".to_owned(),
            "true".to_owned(),
        ];
        let legacy = vec!["unit".to_owned(), "true".to_owned()];
        assert_eq!(parse_arguments(&named), Some(("unit", &named[3..])));
        assert_eq!(parse_arguments(&legacy), Some(("unit", &legacy[1..])));
    }

    #[test]
    fn parser_rejects_a_missing_child_command() {
        let named = vec!["--label".to_owned(), "unit".to_owned(), "--".to_owned()];
        assert_eq!(parse_arguments(&named), None);
    }
}
