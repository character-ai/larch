//! `gantt render` and `analyze-issues render-chart`.
//!
//! Both verbs were thin `argparse` front ends over a pure renderer, so this
//! module owns only the command line: the exact usage and error text callers
//! branch on, the file and stdin reads, and the single `print()` each verb
//! emitted. The renderers live in `larch_core::report`.

use std::{
    ffi::OsString,
    fs, io,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_core::{
    python_int,
    report::{
        gantt::{self, MAX_WIDTH},
        growth_chart,
    },
};

use crate::argparse_compat::{parse, python_io_error, write_stdout};

const GANTT_PROGRAM: &str = "cli.py gantt render";
const GANTT_USAGE: &str = "usage: cli.py gantt render [-h] --window-start-s WINDOW_START_S --window-end-s\n                           WINDOW_END_S --rows-tsv ROWS_TSV [--width WIDTH]";
const GANTT_HELP: &str = "usage: cli.py gantt render [-h] --window-start-s WINDOW_START_S --window-end-s\n                           WINDOW_END_S --rows-tsv ROWS_TSV [--width WIDTH]\n\noptions:\n  -h, --help            show this help message and exit\n  --window-start-s WINDOW_START_S\n  --window-end-s WINDOW_END_S\n  --rows-tsv ROWS_TSV\n  --width WIDTH\n";
const GANTT_OPTIONS: &[&str] = &[
    "--window-start-s",
    "--window-end-s",
    "--rows-tsv",
    "--width",
];
const GANTT_INTEGER_OPTIONS: &[&str] = &["--window-start-s", "--window-end-s", "--width"];

const CHART_PROGRAM: &str = "cli.py";
const CHART_USAGE: &str = "usage: cli.py [-h] [path]";
const CHART_HELP: &str = "usage: cli.py [-h] [path]\n\npositional arguments:\n  path\n\noptions:\n  -h, --help  show this help message and exit\n";

/// Render a rows TSV as a plain ASCII Gantt chart on stdout.
pub fn gantt_render(arguments: &[OsString]) -> ExitCode {
    // `argparse` consumes tokens left to right, so `-h` fires only after every
    // option before it has been consumed and converted. Parsing that prefix
    // alone reproduces the order: a conversion failure on an earlier option
    // wins over the help action, and the missing-required and surplus-argument
    // checks run after the whole line, so neither reaches a help request.
    let help_index = arguments.iter().position(is_help_token);
    let parsed = parse(
        &arguments[..help_index.unwrap_or(arguments.len())],
        GANTT_OPTIONS,
        0,
    );
    for (option, value) in parsed.entries() {
        if !GANTT_INTEGER_OPTIONS.contains(option) {
            continue;
        }
        let text = value.to_string_lossy();
        if python_int(&text).is_none() {
            return gantt_usage_error(&format!("argument {option}: invalid int value: '{text}'"));
        }
    }
    if let Some(error) = parsed.value_error() {
        return gantt_usage_error(error);
    }
    if help_index.is_some() {
        return write_stdout(GANTT_HELP);
    }
    let missing: Vec<&str> = GANTT_OPTIONS
        .iter()
        .filter(|option| **option != "--width" && parsed.value(option).is_none())
        .copied()
        .collect();
    if !missing.is_empty() {
        return gantt_usage_error(&format!(
            "the following arguments are required: {}",
            missing.join(", ")
        ));
    }
    if let Some(error) = parsed.error() {
        return gantt_usage_error(&error);
    }
    let integer = |option: &str| {
        parsed
            .value(option)
            .and_then(|value| python_int(&value.to_string_lossy()))
    };
    let width = integer("--width");
    if let Some(width) = width {
        if width < 1 {
            eprintln!("ERROR: --width must be positive");
            return ExitCode::from(2);
        }
        if width > MAX_WIDTH {
            eprintln!("ERROR: --width must be at most {MAX_WIDTH}");
            return ExitCode::from(2);
        }
    }
    let Some(rows_tsv) = parsed.value("--rows-tsv").map(PathBuf::from) else {
        return gantt_usage_error("the following arguments are required: --rows-tsv");
    };
    let text = match read_text_replacing(&rows_tsv) {
        Ok(text) => text,
        Err(error) => {
            eprintln!(
                "ERROR: cannot read rows TSV: {}",
                python_io_error(&error, &rows_tsv)
            );
            return ExitCode::from(2);
        }
    };
    let rows = match gantt::parse_rows_tsv(&text) {
        Ok(rows) => rows,
        Err(error) => {
            eprintln!("ERROR: {error}");
            return ExitCode::from(2);
        }
    };
    let chart = gantt::render_gantt(
        integer("--window-start-s").unwrap_or_default(),
        integer("--window-end-s").unwrap_or_default(),
        &rows,
        width,
    );
    if chart.is_empty() {
        return ExitCode::SUCCESS;
    }
    write_stdout(&format!("{chart}\n"))
}

/// Render a cumulative-growth chart from a TSV path or stdin.
pub fn render_chart(arguments: &[OsString]) -> ExitCode {
    // `render-chart` declares no value-taking option, so the only refusal is
    // the surplus-argument check `argparse` runs after the help action.
    if arguments.iter().any(is_help_token) {
        return write_stdout(CHART_HELP);
    }
    let parsed = parse(arguments, &[], 1);
    if let Some(error) = parsed.error() {
        eprintln!("{CHART_USAGE}\n{CHART_PROGRAM}: error: {error}");
        return ExitCode::from(2);
    }
    // The Python owner raised `OSError` or `UnicodeDecodeError` here and exited
    // on the traceback; these report one bounded line at the same exit code.
    let source = parsed
        .positional(0)
        .filter(|path| !path.is_empty())
        .map(PathBuf::from);
    let text = match read_strict_utf8(source.as_deref()) {
        Ok(text) => text,
        Err(message) => {
            eprintln!("ERROR: {message}");
            return ExitCode::FAILURE;
        }
    };
    let (buckets, rows) = match growth_chart::parse_tsv(&text) {
        Ok(parsed) => parsed,
        Err(error) => {
            eprintln!("ERROR: {error}");
            return ExitCode::FAILURE;
        }
    };
    write_stdout(&format!(
        "{}\n",
        growth_chart::render_chart(&buckets, &rows)
    ))
}

fn gantt_usage_error(error: &str) -> ExitCode {
    eprintln!("{GANTT_USAGE}\n{GANTT_PROGRAM}: error: {error}");
    ExitCode::from(2)
}

fn is_help_token(argument: &OsString) -> bool {
    matches!(argument.to_string_lossy().as_ref(), "-h" | "--help")
}

/// Read one path, or standard input, refusing bytes Python's decoder refused.
fn read_strict_utf8(path: Option<&Path>) -> Result<String, String> {
    let (bytes, source) = if let Some(path) = path {
        (
            fs::read(path).map_err(|error| python_io_error(&error, path))?,
            path.display().to_string(),
        )
    } else {
        let mut buffer = Vec::new();
        io::Read::read_to_end(&mut io::stdin().lock(), &mut buffer)
            .map_err(|error| error.to_string())?;
        (buffer, "standard input".to_owned())
    };
    String::from_utf8(bytes).map_err(|_error| format!("cannot decode {source} as UTF-8"))
}

/// Read a file the way Python's `read_text(errors="replace")` does.
fn read_text_replacing(path: &Path) -> io::Result<String> {
    Ok(String::from_utf8_lossy(&fs::read(path)?).into_owned())
}
