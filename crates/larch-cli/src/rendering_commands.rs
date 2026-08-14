//! `gantt render`, `analyze-issues render-chart`, and `generate`.
//!
//! Both verbs were thin `argparse` front ends over a pure renderer, so this
//! module owns only the command line: the exact usage and error text callers
//! branch on, the file and stdin reads, and the single `print()` each verb
//! emitted. The renderers live in `larch_core::report`.

use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    ffi::OsString,
    fmt::Write as _,
    fs,
    io::{self, Write as _},
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::{GixRepository, RepositoryRoot};
use larch_core::{
    RepositoryRead, python_int,
    report::{
        gantt::{self, MAX_WIDTH},
        growth_chart,
    },
    review::render_wire_values,
};
use regex::Regex;
use sha2::{Digest, Sha256};
use tempfile::NamedTempFile;

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

const GENERATE_USAGE: &str = "Usage: generate <registered-verb> [--check]";
const GENERATOR_COLUMN_COUNT: usize = 2;
const TOPOLOGY_COLUMN_COUNT: usize = 4;
const MIN_TOPOLOGY_VALUE_LEN: usize = 3;
const REVIEWER_PROVENANCE: &str = "<!-- Derived from skills/shared/reviewer-templates.md -->";
const FOCUS_AREA_VALUES: &[&str] = &[
    "code-quality",
    "risk-integration",
    "correctness",
    "architecture",
    "security",
];
const FINDING_SCOPE_VALUES: &[&str] = &["in_scope", "out_of_scope"];

struct Reviewer {
    verb: &'static str,
    section: &'static str,
    output: &'static str,
    frontmatter: &'static str,
}

const REVIEWERS: &[Reviewer] = &[
    Reviewer {
        verb: "code-reviewer-agent",
        section: "## Reviewer: Code Reviewer",
        output: "agents/code-reviewer.md",
        frontmatter: r"---
name: code-reviewer
description: Unified code reviewer combining code quality (bugs, reuse, tests, backward compat, style), risk/integration (breaking changes, thread safety, deployment, regressions, CI), correctness (logic errors, off-by-one, nil, types, races, errors, math), architecture (separation of concerns, contract boundaries, invariants, semantic boundaries), and security (injection, authn/authz, secrets, crypto, deserialization, SSRF, path traversal, dependency CVEs).
model: sonnet
tools:
  - Read
  - Grep
  - Glob
---",
    },
    Reviewer {
        verb: "reviewer-plan-fidelity-agent",
        section: "## Reviewer: Plan Fidelity",
        output: "agents/reviewer-plan-fidelity.md",
        frontmatter: r#"---
name: reviewer-plan-fidelity
description: "Specialist code reviewer concentrating on plan fidelity: plan-to-implementation traceability, completeness against design requirements, correctness against stated intent, stale replacement surfaces, generated artifact coverage, and explicit loud failure when the design plan is missing."
model: sonnet
tools:
  - Read
  - Grep
  - Glob
---"#,
    },
    Reviewer {
        verb: "reviewer-code-robustness-agent",
        section: "## Reviewer: Code Robustness",
        output: "agents/reviewer-code-robustness.md",
        frontmatter: r#"---
name: reviewer-code-robustness
description: "Specialist code reviewer concentrating on code robustness: edge cases, boundary behavior, failure recovery, partial failure, resource cleanup, retry/idempotency, silent data corruption, and invariants at failure boundaries. Does not require or expect a design plan."
model: sonnet
tools:
  - Read
  - Grep
  - Glob
---"#,
    },
    Reviewer {
        verb: "reviewer-security-structure-tests-agent",
        section: "## Reviewer: Security + Structure + Tests",
        output: "agents/reviewer-security-structure-tests.md",
        frontmatter: r#"---
name: reviewer-security-structure-tests
description: "Specialist code reviewer concentrating on security, structure/maintainability, and tests/CI: injection, authn/authz, secret handling, crypto, deserialization, SSRF, path traversal, dependency CVEs, code reuse, KISS, style consistency, backward compatibility, single-responsibility, test coverage gaps, missing assertions, CI workflow correctness, deployment risks, and regression risk."
model: sonnet
tools:
  - Read
  - Grep
  - Glob
---"#,
    },
    Reviewer {
        verb: "reviewer-structure-agent",
        section: "## Reviewer: Structure",
        output: "agents/reviewer-structure.md",
        frontmatter: r#"---
name: reviewer-structure
description: "Specialist code reviewer concentrating on structure, KISS, and maintainability."
model: sonnet
tools:
  - Read
  - Grep
  - Glob
---"#,
    },
    Reviewer {
        verb: "reviewer-correctness-agent",
        section: "## Reviewer: Correctness",
        output: "agents/reviewer-correctness.md",
        frontmatter: r#"---
name: reviewer-correctness
description: "Specialist code reviewer concentrating on correctness and logic."
model: sonnet
tools:
  - Read
  - Grep
  - Glob
---"#,
    },
    Reviewer {
        verb: "reviewer-testing-agent",
        section: "## Reviewer: Testing",
        output: "agents/reviewer-testing.md",
        frontmatter: r#"---
name: reviewer-testing
description: "Specialist code reviewer concentrating on tests, CI, and regression risk."
model: sonnet
tools:
  - Read
  - Grep
  - Glob
---"#,
    },
    Reviewer {
        verb: "reviewer-security-agent",
        section: "## Reviewer: Security",
        output: "agents/reviewer-security.md",
        frontmatter: r#"---
name: reviewer-security
description: "Specialist code reviewer concentrating on security and trust boundaries."
model: sonnet
tools:
  - Read
  - Grep
  - Glob
---"#,
    },
    Reviewer {
        verb: "reviewer-edge-cases-agent",
        section: "## Reviewer: Edge Cases",
        output: "agents/reviewer-edge-cases.md",
        frontmatter: r#"---
name: reviewer-edge-cases
description: "Specialist code reviewer concentrating on edge cases, failure recovery, and security."
model: sonnet
tools:
  - Read
  - Grep
  - Glob
---"#,
    },
];

#[derive(Debug)]
struct GeneratorRow {
    command: String,
    verb: String,
    output: String,
}

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

/// Generate or verify one committed developer artifact.
pub fn generate(arguments: &[OsString]) -> ExitCode {
    let Some((verb, remainder)) = arguments.split_first() else {
        eprintln!("{GENERATE_USAGE}");
        return ExitCode::from(2);
    };
    let Some(verb) = verb.to_str() else {
        eprintln!("{GENERATE_USAGE}");
        return ExitCode::from(2);
    };
    if verb == "check" {
        if !remainder.is_empty() {
            eprintln!("Usage: generate check");
            return ExitCode::from(2);
        }
        return match repository_root().and_then(|root| generate_check(&root)) {
            Ok(()) => ExitCode::SUCCESS,
            Err(error) => generate_failure(&error),
        };
    }
    if !is_generator_verb(verb) {
        eprintln!("{GENERATE_USAGE}");
        return ExitCode::from(2);
    }
    let check = match check_mode(remainder) {
        Ok(check) => check,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::from(2);
        }
    };
    let result = repository_root().and_then(|root| {
        let tracked = if verb == "topology-docs" {
            Some(tracked_paths(&root)?)
        } else {
            None
        };
        generate_one(&root, tracked.as_ref(), verb, check)
    });
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => generate_failure(&error),
    }
}

fn generate_failure(error: &str) -> ExitCode {
    eprintln!("ERROR: {error}");
    ExitCode::FAILURE
}

fn check_mode(arguments: &[OsString]) -> Result<bool, &'static str> {
    match arguments {
        [] => Ok(false),
        [argument] if argument == "--check" => Ok(true),
        _ => Err("Usage: [--check]"),
    }
}

fn repository_root() -> Result<PathBuf, String> {
    let current =
        env::current_dir().map_err(|error| format!("cannot resolve current directory: {error}"))?;
    let repository = GixRepository::discover(&current)
        .map_err(|_| "generate: not inside a git work tree".to_owned())?;
    let location = repository.location();
    let work_dir = location
        .work_dir
        .ok_or_else(|| "generate: not inside a git work tree".to_owned())?;
    let work_dir = PathBuf::from(String::from_utf8_lossy(work_dir.as_bytes()).into_owned());
    RepositoryRoot::resolve(Some(&work_dir))
        .map(|root| root.path().to_owned())
        .map_err(|_| "generate: not inside a git work tree".to_owned())
}

fn tracked_paths(root: &Path) -> Result<BTreeSet<Vec<u8>>, String> {
    GixRepository::open(root)
        .map_err(|_| "generate: cannot read git index".to_owned())?
        .tracked_paths()
        .map_err(|_| "generate: cannot read git index".to_owned())
        .map(|paths| {
            paths
                .into_iter()
                .map(|path| path.as_bytes().to_vec())
                .collect()
        })
}

fn is_generator_verb(verb: &str) -> bool {
    REVIEWERS.iter().any(|reviewer| reviewer.verb == verb)
        || matches!(
            verb,
            "pre-rendered-reviewer-prompts"
                | "codex-implementer"
                | "cursor-implementer"
                | "topology-docs"
        )
}

fn generate_one(
    root: &Path,
    tracked: Option<&BTreeSet<Vec<u8>>>,
    verb: &str,
    check: bool,
) -> Result<(), String> {
    if let Some(reviewer) = REVIEWERS.iter().find(|reviewer| reviewer.verb == verb) {
        let target = root.join(reviewer.output);
        return diff_or_write(
            &target,
            &reviewer_text(root, reviewer)?,
            check,
            reviewer.verb,
        );
    }
    match verb {
        "pre-rendered-reviewer-prompts" => generate_pre_rendered_reviewer_prompts(root, check),
        "codex-implementer" => diff_or_write(
            &root.join("skills/implement/prompts/codex-implementer.md"),
            &implementer_text(root, "codex")?,
            check,
            verb,
        ),
        "cursor-implementer" => diff_or_write(
            &root.join("skills/implement/prompts/cursor-implementer.md"),
            &implementer_text(root, "cursor")?,
            check,
            verb,
        ),
        "topology-docs" => {
            let tracked =
                tracked.ok_or_else(|| "generate: missing tracked-path context".to_owned())?;
            let target = env::var_os("LARCH_TOPOLOGY_DOC")
                .map_or_else(|| root.join("docs/topology.md"), PathBuf::from);
            diff_or_write(&target, &topology_text(root, tracked)?, check, verb)
        }
        _ => Err(format!("unknown generator verb: {verb}")),
    }
}

fn legacy_invocation(verb: &str) -> String {
    format!("python3 python/cli.py generate {verb}")
}

fn reviewer_text(root: &Path, reviewer: &Reviewer) -> Result<String, String> {
    let template = root.join("skills/shared/reviewer-templates.md");
    let body = if reviewer.verb == "code-reviewer-agent" {
        code_reviewer_body(&template, reviewer.section)?
    } else {
        specialist_reviewer_body(&template, reviewer.section)?
    };
    let header = format!(
        "<!-- AUTO-GENERATED: Regenerate via: {} -->\n{REVIEWER_PROVENANCE}",
        legacy_invocation(reviewer.verb)
    );
    Ok(format!("{}\n\n{header}\n\n{body}\n", reviewer.frontmatter))
}

fn specialist_reviewer_body(template: &Path, section: &str) -> Result<String, String> {
    let body = extract_generated_body(template, Some(section))?;
    let marker = "\n## Necessity gate (in-scope findings)";
    let Some((unique, _)) = body.split_once(marker) else {
        return Err(format!(
            "ERROR: specialist template lacks canonical split marker: {section}"
        ));
    };
    let shared = extract_template_fragment(template, "SPECIALIST_SHARED_SECTIONS")?;
    Ok(format!(
        "{}\n\n{}",
        render_wire_value_placeholders(unique.trim_end()),
        render_wire_value_placeholders(&shared)
    ))
}

fn code_reviewer_body(template: &Path, section: &str) -> Result<String, String> {
    let body = extract_generated_body(template, Some(section))?
        .replace("{REVIEW_TARGET}", "code, plans, or conflict resolutions");
    let mut lines = Vec::new();
    let mut skip_blank = false;
    for line in body.lines() {
        if line == "{CONTEXT_BLOCK}" {
            skip_blank = true;
            continue;
        }
        if skip_blank {
            skip_blank = false;
            if line.is_empty() {
                continue;
            }
        }
        lines.push(line);
    }
    replace_output_instruction(
        &lines.join("\n"),
        &[
            "File path and line number(s) (if reviewing code) or the specific concern (if reviewing a plan)",
            "What the issue is",
            "Suggested fix (be specific)",
        ],
        &[
            "File path and line number(s) or the specific concern (use `<expected-path>:1` for absent-artifact observations)",
            "What the issue is",
            "Suggested fix",
        ],
    )
    .map(|text| render_wire_value_placeholders(&text))
}

fn render_wire_value_placeholders(text: &str) -> String {
    text.replace(
        "{FOCUS_AREA_VALUES}",
        &render_wire_values(FOCUS_AREA_VALUES, "/", true),
    )
    .replace(
        "{FOCUS_AREA_VALUES_BARE}",
        &render_wire_values(FOCUS_AREA_VALUES, "/", false),
    )
    .replace(
        "{FINDING_SCOPE_VALUES}",
        &render_wire_values(FINDING_SCOPE_VALUES, "/", true),
    )
}

fn extract_generated_body(template: &Path, heading: Option<&str>) -> Result<String, String> {
    let text = read_text(template)?;
    let mut in_section = heading.is_none();
    let mut in_body = false;
    let mut found = false;
    let mut skipped_open = false;
    let mut body = Vec::new();
    for line in text.lines() {
        if heading.is_some_and(|heading| line == heading) {
            in_section = true;
            continue;
        }
        if found {
            continue;
        }
        if in_section && line.contains("<!-- BEGIN GENERATED_BODY -->") {
            in_body = true;
            skipped_open = false;
            continue;
        }
        if in_body && line.contains("<!-- END GENERATED_BODY -->") {
            in_body = false;
            in_section = false;
            found = true;
            continue;
        }
        if in_body {
            if skipped_open {
                body.push(line);
            } else {
                skipped_open = true;
            }
        }
    }
    let label = heading.unwrap_or("GENERATED_BODY");
    if !found || body.is_empty() {
        return Err(format!(
            "ERROR: no content found for {label} between BEGIN/END GENERATED_BODY markers"
        ));
    }
    if body.last() != Some(&"```") {
        return Err(format!(
            "ERROR: expected outer close fence ``` as last line inside GENERATED_BODY markers; got: {}",
            body.last().copied().unwrap_or_default()
        ));
    }
    let _ = body.pop();
    Ok(body.join("\n"))
}

fn extract_template_fragment(template: &Path, name: &str) -> Result<String, String> {
    let text = read_text(template)?;
    let begin = format!("<!-- BEGIN {name} -->\n");
    let end = format!("\n<!-- END {name} -->");
    let Some(start) = text.find(&begin).map(|offset| offset + begin.len()) else {
        return Err(format!(
            "ERROR: no content found for canonical fragment {name}"
        ));
    };
    let Some(end) = text[start..].find(&end).map(|offset| start + offset) else {
        return Err(format!(
            "ERROR: no content found for canonical fragment {name}"
        ));
    };
    let fragment = text[start..end].trim();
    if fragment.is_empty() {
        return Err(format!(
            "ERROR: no content found for canonical fragment {name}"
        ));
    }
    Ok(fragment.to_owned())
}

fn replace_output_instruction(
    body: &str,
    inscope: &[&str],
    oos: &[&str],
) -> Result<String, String> {
    let mut output = Vec::new();
    let mut section = "";
    for line in body.lines() {
        match line {
            "### In-Scope Findings" => {
                section = "in_scope";
                output.push(line.to_owned());
            }
            "### Out-of-Scope Observations" => {
                section = "oos";
                output.push(line.to_owned());
            }
            "- {OUTPUT_INSTRUCTION}" => match section {
                "in_scope" => output.extend(inscope.iter().map(|item| format!("- {item}"))),
                "oos" => output.extend(oos.iter().map(|item| format!("- {item}"))),
                _ => {
                    return Err(
                        "{OUTPUT_INSTRUCTION} encountered outside a known section".to_owned()
                    );
                }
            },
            _ => output.push(line.to_owned()),
        }
    }
    Ok(output.join("\n"))
}

fn implementer_text(root: &Path, kind: &str) -> Result<String, String> {
    let base = read_text(&root.join("agents/_implementer-base.md"))?;
    match kind {
        "codex" => {
            let header = format!(
                r#"---
name: codex-implementer
description: Codex implementer system prompt for /implement Step 2. Produces working-tree edits plus a structured manifest; the dispatcher commits with manifest.commit_message. Loaded as --agent-prompt by scripts/larch.sh agent launch-codex-implement; not invoked as a Claude subagent.
---

<!-- AUTO-GENERATED: Derived from agents/_implementer-base.md. Regenerate via: {} -->

# Codex implementer (system prompt)

You are the Codex implementer for `/implement` Step 2. Turn the written plan into working-tree edits plus a structured manifest, then exit cleanly. The dispatcher commits for you with `git add -A && git commit -F …` using `manifest.commit_message`; you do NOT commit.

You are a non-interactive subprocess. The orchestrator does NOT read your transcript. Before exit, atomically write these orchestration files:

- `<MANIFEST_PATH>` — `manifest.json`, mandatory. Schema and rules: `skills/implement/references/codex-manifest-schema.md`.
- `<QA_PENDING_PATH>` — `qa-pending.json`, written ONLY when you set `manifest.status=needs_qa`.
- `<SCOUT_MANIFEST_PATH>` — optional best-effort `scout-coder-manifest.json`.

The dispatcher passes the paths as arguments. Always write `<path>.tmp` first, then `mv <path>.tmp <path>` so a crash leaves "no file" instead of "half a JSON document."

You edit the working tree, write the manifest, and exit. The dispatcher reads `manifest.commit_message` and commits after you exit, preserving `workspace-write` sandbox semantics that forbid `.git/` writes.

"#,
                legacy_invocation("codex-implementer")
            );
            let rendered = base
                .replace("TOOL_COMMIT_STDERR", "codex-commit-stderr.txt")
                .replace(" `TOOL_MODIFIED_HISTORY` is dispatcher-emitted only.", "");
            let expression = Regex::new(r"(?m)^2\. \*\*NEVER `git add`.*$")
                .map_err(|error| error.to_string())?;
            let rendered = expression.replace(
                &rendered,
                "2. **NEVER `git add` or `git commit`.** Committing is the dispatcher's job. Your output is the working-tree edits plus `manifest.json`. Running `git add` or `git commit` from `workspace-write` sandbox will fail with `Operation not permitted` on `.git/index.lock` anyway, so just do not try.",
            );
            Ok(format!("{header}{rendered}"))
        }
        "cursor" => {
            let header = format!(
                r#"---
name: cursor-implementer
description: Cursor implementer system prompt for /implement Step 2. Produces working-tree edits plus a structured manifest; the dispatcher commits with manifest.commit_message. Loaded as --agent-prompt by scripts/larch.sh agent launch-cursor-implement; not invoked as a Claude subagent.
---

<!-- AUTO-GENERATED: Derived from agents/_implementer-base.md. Regenerate via: {} -->

# Cursor implementer (system prompt)

You are the Cursor implementer for `/implement` Step 2. Turn the written plan into working-tree edits plus a structured manifest, then exit cleanly. The dispatcher commits for you with `git add -A && git commit -F …` using `manifest.commit_message`; you do NOT commit.

You are a non-interactive subprocess. The orchestrator does NOT read your transcript. Before exit, atomically write these orchestration files:

- `<MANIFEST_PATH>` — `manifest.json`, mandatory. Schema and rules: `skills/implement/references/codex-manifest-schema.md`.
- `<QA_PENDING_PATH>` — `qa-pending.json`, written ONLY when you set `manifest.status=needs_qa`.
- `<SCOUT_MANIFEST_PATH>` — optional best-effort `scout-coder-manifest.json`.

The dispatcher passes the paths as arguments. Always write `<path>.tmp` first, then `mv <path>.tmp <path>` so a crash leaves "no file" instead of "half a JSON document."

You edit the working tree, write the manifest, and exit. The dispatcher reads `manifest.commit_message` and commits after you exit.

Cursor lacks Codex's `workspace-write` sandbox. The dispatcher asserts `HEAD == BASELINE_SHA` before committing for you; any `git commit` you produce triggers `cursor-modified-history` and preserves partial work for operator inspection.

## Shared guardrails

The section below, Inputs through Style, is generated from the Cursor implementer template; `make test-implement-structure` assertion (24) enforces the structure.

"#,
                legacy_invocation("cursor-implementer")
            );
            let rendered = base
                .replace("TOOL_MODIFIED_HISTORY", "cursor-modified-history")
                .replace("TOOL_COMMIT_STDERR", "cursor-commit-stderr.txt");
            Ok(format!(
                "{header}{}",
                remove_cursor_interactive_guard(&rendered)
            ))
        }
        _ => Err(format!("unknown implementer kind: {kind}")),
    }
}

fn remove_cursor_interactive_guard(text: &str) -> String {
    const START: &str =
        "9. **NEVER spawn or maintain persistent interactive subprocess sessions.**";
    let mut offset = 0;
    while let Some(relative) = text[offset..].find(START) {
        let start = offset + relative;
        if start == 0 || text.as_bytes()[start - 1] == b'\n' {
            let after_start = start + START.len();
            if let Some(relative_end) = text[after_start..].find("\n10.") {
                let end = after_start + relative_end + 1;
                let mut output = String::with_capacity(text.len() - (end - start));
                output.push_str(&text[..start]);
                output.push_str(&text[end..]);
                return output;
            }
            return text.to_owned();
        }
        offset = start + START.len();
    }
    text.to_owned()
}

fn generate_pre_rendered_reviewer_prompts(root: &Path, check: bool) -> Result<(), String> {
    let expected = pre_rendered_reviewer_files(root)?;
    let output = root.join("agents/pre-rendered");
    if check {
        let actual = directory_files(&output)?;
        let expected_bytes = expected
            .iter()
            .map(|(name, contents)| (name.clone(), contents.as_bytes().to_vec()))
            .collect();
        if actual != expected_bytes {
            return Err("agents/pre-rendered is out of sync with agents/reviewer-*.md.".to_owned());
        }
        return Ok(());
    }
    fs::create_dir_all(&output)
        .map_err(|error| format!("cannot create {}: {error}", output.display()))?;
    for entry in fs::read_dir(&output)
        .map_err(|error| format!("cannot read {}: {error}", output.display()))?
    {
        let entry = entry.map_err(|error| format!("cannot read {}: {error}", output.display()))?;
        let name = entry.file_name();
        let Some(name) = name.to_str() else {
            continue;
        };
        if (name.starts_with("reviewer-") && name.ends_with("-body.txt")) || name == ".manifest" {
            fs::remove_file(entry.path())
                .map_err(|error| format!("cannot remove {}: {error}", entry.path().display()))?;
        }
    }
    for (name, contents) in expected {
        write_text_atomic(&output.join(name), &contents)?;
    }
    Ok(())
}

fn pre_rendered_reviewer_files(root: &Path) -> Result<BTreeMap<String, String>, String> {
    let agents = root.join("agents");
    let mut sources = Vec::new();
    for entry in fs::read_dir(&agents)
        .map_err(|error| format!("cannot read {}: {error}", agents.display()))?
    {
        let entry = entry.map_err(|error| format!("cannot read {}: {error}", agents.display()))?;
        let name = entry.file_name();
        let Some(name) = name.to_str() else {
            continue;
        };
        if name.starts_with("reviewer-")
            && name.strip_suffix(".md").is_some()
            && entry.path().is_file()
        {
            sources.push(entry.path());
        }
    }
    sources.sort();
    let mut output = BTreeMap::new();
    for source in sources {
        let body = frontmatter_body(&source)?;
        if body.is_empty() {
            let relative = source.strip_prefix(root).unwrap_or(&source);
            return Err(format!(
                "generate-pre-rendered-reviewer-prompts.sh: empty body in {}",
                relative.display()
            ));
        }
        let stem = source
            .file_stem()
            .and_then(|stem| stem.to_str())
            .ok_or_else(|| format!("invalid reviewer path: {}", source.display()))?;
        output.insert(format!("{stem}-body.txt"), body);
    }
    let mut manifest = format!(
        "# Generated by {}. Do not edit.\n",
        legacy_invocation("pre-rendered-reviewer-prompts")
    );
    for (name, contents) in &output {
        let _ = writeln!(
            manifest,
            "{}  agents/pre-rendered/{name}",
            sha256_text(contents)
        );
    }
    output.insert(".manifest".to_owned(), manifest);
    Ok(output)
}

fn frontmatter_body(path: &Path) -> Result<String, String> {
    let text = read_text(path)?;
    let lines: Vec<&str> = text.lines().collect();
    let mut fences = 0;
    for (index, line) in lines.iter().enumerate() {
        if line
            .strip_prefix("---")
            .is_some_and(|suffix| suffix.trim().is_empty())
        {
            fences += 1;
            if fences == 2 {
                return Ok(lines[index + 1..].join("\n"));
            }
        }
    }
    Ok(String::new())
}

fn directory_files(path: &Path) -> Result<BTreeMap<String, Vec<u8>>, String> {
    if !path.is_dir() {
        return Ok(BTreeMap::new());
    }
    let mut files = BTreeMap::new();
    collect_directory_files(path, path, &mut files)?;
    Ok(files)
}

fn collect_directory_files(
    root: &Path,
    directory: &Path,
    files: &mut BTreeMap<String, Vec<u8>>,
) -> Result<(), String> {
    for entry in fs::read_dir(directory)
        .map_err(|error| format!("cannot read {}: {error}", directory.display()))?
    {
        let entry =
            entry.map_err(|error| format!("cannot read {}: {error}", directory.display()))?;
        let path = entry.path();
        if path.is_dir() {
            collect_directory_files(root, &path, files)?;
        } else if path.is_file() {
            let relative = path
                .strip_prefix(root)
                .map_err(|_| format!("cannot relativize {}", path.display()))?
                .to_string_lossy()
                .replace('\\', "/");
            files.insert(
                relative,
                fs::read(&path)
                    .map_err(|error| format!("cannot read {}: {error}", path.display()))?,
            );
        }
    }
    Ok(())
}

fn sha256_text(text: &str) -> String {
    let mut digest = Sha256::new();
    digest.update(text.as_bytes());
    format!("{:x}", digest.finalize())
}

fn read_text(path: &Path) -> Result<String, String> {
    fs::read_to_string(path).map_err(|error| format!("cannot read {}: {error}", path.display()))
}

fn diff_or_write(target: &Path, expected: &str, check: bool, label: &str) -> Result<(), String> {
    if check {
        let current = match fs::read_to_string(target) {
            Ok(current) => current,
            Err(error) if error.kind() == io::ErrorKind::NotFound => String::new(),
            Err(error) => return Err(format!("cannot read {}: {error}", target.display())),
        };
        if current != expected {
            return Err(format!(
                "{label} is out of sync. Run: {}",
                legacy_invocation(label)
            ));
        }
        return Ok(());
    }
    write_text_atomic(target, expected)
}

fn write_text_atomic(target: &Path, text: &str) -> Result<(), String> {
    let parent = target
        .parent()
        .ok_or_else(|| format!("cannot determine parent for {}", target.display()))?;
    let mut temporary = NamedTempFile::new_in(parent).map_err(|error| {
        format!(
            "cannot create temporary file near {}: {error}",
            target.display()
        )
    })?;
    temporary
        .write_all(text.as_bytes())
        .and_then(|()| temporary.as_file().sync_all())
        .map_err(|error| format!("cannot write {}: {error}", target.display()))?;
    temporary
        .persist(target)
        .map_err(|error| format!("cannot replace {}: {}", target.display(), error.error))?;
    Ok(())
}

fn topology_text(root: &Path, tracked: &BTreeSet<Vec<u8>>) -> Result<String, String> {
    let topology_path = env::var_os("LARCH_TOPOLOGY_TSV")
        .map_or_else(|| root.join("skills/shared/topology.tsv"), PathBuf::from);
    let text = read_text(&topology_path)?;
    let mut rows = Vec::new();
    let mut seen_keys = BTreeSet::new();
    let mut seen_anchors = BTreeSet::new();
    for (row, line) in physical_lines(&text, "row ")? {
        let columns: Vec<&str> = line.split('\t').collect();
        if columns.len() != TOPOLOGY_COLUMN_COUNT
            || columns[0].is_empty()
            || columns[1].is_empty()
            || columns[3].is_empty()
        {
            return Err(format!(
                "row {row}: malformed row; expected exactly four tab-separated columns with key, value, and runtime_authority non-empty"
            ));
        }
        let [key, value, composition, runtime] = columns.as_slice() else {
            return Err(format!("row {row}: malformed topology row"));
        };
        validate_topology_row(root, tracked, row, key, value, composition, runtime)?;
        if !seen_keys.insert((*key).to_owned()) {
            return Err(format!("row {row}: duplicate key '{key}'"));
        }
        if !seen_anchors.insert((*key).to_owned()) {
            return Err(format!("row {row}: derived anchor '{key}' collides"));
        }
        rows.push((
            (*key).to_owned(),
            (*value).to_owned(),
            (*composition).to_owned(),
            (*runtime).to_owned(),
        ));
    }
    let header = format!(
        "# Topology Projection\n\n<!-- AUTO-GENERATED: Derived from skills/shared/topology.tsv. Do not edit. Regenerate via: {} -->\n\nThis document is a consumer-doc projection of runtime authorities. The runtime authority listed for each row remains the source of truth; the projection exists so consumer docs can link to stable row anchors instead of repeating drift-prone counts.\n\n`/implement` Step 5 public phrases are pinned by `scripts/test-quick-mode-docs-sync.sh`; the review-panel shape is also projected here from `skills/shared/topology.tsv` so the topology row and public-doc harness stay aligned.\n\n| Key | Value | Composition | Runtime Authority |\n|---|---:|---|---|\n",
        legacy_invocation("topology-docs")
    );
    let mut output = header;
    for (key, value, composition, runtime) in rows {
        let composition = if composition.is_empty() {
            " ".to_owned()
        } else {
            composition
        };
        let _ = writeln!(
            output,
            "| <a id=\"{key}\"></a>`{key}` | {value} | {composition} | `{runtime}` |"
        );
    }
    Ok(output)
}

fn physical_lines<'a>(text: &'a str, crlf_prefix: &str) -> Result<Vec<(usize, &'a str)>, String> {
    let mut rows = Vec::new();
    for (index, line) in text.split('\n').enumerate() {
        let row = index + 1;
        if line.contains('\r') {
            let suffix = if crlf_prefix.ends_with(':') {
                " (use LF)"
            } else {
                ""
            };
            return Err(format!(
                "{crlf_prefix}{row}: CRLF line endings not allowed{suffix}"
            ));
        }
        if !line.is_empty() && !line.starts_with('#') {
            rows.push((row, line));
        }
    }
    Ok(rows)
}

fn validate_topology_row(
    root: &Path,
    tracked: &BTreeSet<Vec<u8>>,
    row: usize,
    key: &str,
    value: &str,
    composition: &str,
    runtime: &str,
) -> Result<(), String> {
    if key.is_empty()
        || !key.bytes().all(|byte| {
            byte.is_ascii_lowercase() || byte.is_ascii_digit() || matches!(byte, b'_' | b'.')
        })
    {
        return Err(format!("row {row}: key must match [a-z0-9_.]+: {key}"));
    }
    if !valid_topology_value(value) {
        return Err(format!("row {row}: invalid value: {value}"));
    }
    if !composition.is_empty() && !valid_topology_value(composition) {
        return Err(format!("row {row}: invalid composition: {composition}"));
    }
    if invalid_relative_path(runtime) {
        return Err(format!("row {row}: invalid runtime_authority: {runtime}"));
    }
    if value.chars().count() < MIN_TOPOLOGY_VALUE_LEN
        || value.bytes().all(|byte| byte.is_ascii_digit())
    {
        return Err(format!(
            "row {row}: value '{value}' is too short or purely numeric"
        ));
    }
    let path = root.join(runtime);
    if !path.is_file() {
        return Err(format!("row {row}: runtime_authority not found: {runtime}"));
    }
    if !tracked.contains(runtime.as_bytes()) {
        return Err(format!(
            "row {row}: runtime_authority is not tracked by git: {runtime}"
        ));
    }
    if !read_text(&path)?.contains(value) {
        return Err(format!(
            "row {row}: value '{value}' not found in runtime_authority: {runtime}"
        ));
    }
    Ok(())
}

fn valid_topology_value(value: &str) -> bool {
    !value.is_empty()
        && value.bytes().all(|byte| {
            byte.is_ascii_alphanumeric() || matches!(byte, b' ' | b'.' | b'/' | b'+' | b'-')
        })
}

fn invalid_relative_path(path: &str) -> bool {
    path.is_empty()
        || path.starts_with(['/', '\\', '-', ':'])
        || path.as_bytes().get(1) == Some(&b':')
        || Path::new(path).is_absolute()
        || path.contains("//")
        || path.contains("\\\\")
        || path
            .split(['/', '\\'])
            .any(|segment| matches!(segment, "." | ".."))
}

fn generate_check(root: &Path) -> Result<(), String> {
    let registry = root.join("scripts/generators.tsv");
    if !registry.is_file() {
        return Err(format!(
            "check-generators: registry not found: {}",
            registry.display()
        ));
    }
    let tracked = tracked_paths(root)?;
    let rows = generator_registry_rows(root, &tracked)?;
    let before = output_snapshot(root, &rows)?;
    for row in &rows {
        if let Err(error) = generate_one(root, Some(&tracked), &row.verb, true) {
            return Err(format!(
                "{error}\ncheck-generators: drift detected by {} (output: {})",
                row.command, row.output
            ));
        }
    }
    let after = output_snapshot(root, &rows)?;
    if before != after {
        let outputs = rows
            .iter()
            .map(|row| row.output.as_str())
            .collect::<Vec<_>>()
            .join(" ");
        return Err(format!(
            "check-generators: post-run working-tree delta detected at: {outputs}"
        ));
    }
    Ok(())
}

fn generator_registry_rows(
    root: &Path,
    tracked: &BTreeSet<Vec<u8>>,
) -> Result<Vec<GeneratorRow>, String> {
    let registry = root.join("scripts/generators.tsv");
    let text = read_text(&registry)?;
    let mut rows = Vec::new();
    let mut commands = BTreeSet::new();
    let mut outputs = BTreeSet::new();
    for (row, line) in physical_lines(&text, "scripts/generators.tsv:")? {
        let columns: Vec<&str> = line.split('\t').collect();
        if columns.len() != GENERATOR_COLUMN_COUNT || columns[0].is_empty() || columns[1].is_empty()
        {
            return Err(format!(
                "scripts/generators.tsv:{row}: malformed row; expected exactly two non-empty tab-separated columns"
            ));
        }
        let command = columns[0];
        let output = columns[1];
        let mut words = command.split_whitespace();
        let domain = words.next();
        let verb = words.next();
        if words.next().is_some()
            || domain != Some("generate")
            || !verb.is_some_and(is_generator_verb)
        {
            return Err(format!(
                "scripts/generators.tsv:{row}: generator command must be 'generate <registered-verb>': {command}"
            ));
        }
        validate_registry_path(row, "output", output)?;
        if !commands.insert(command.to_owned()) {
            return Err(format!(
                "scripts/generators.tsv:{row}: duplicate generator command: {command}"
            ));
        }
        if !outputs.insert(output.to_owned()) {
            return Err(format!(
                "scripts/generators.tsv:{row}: duplicate output path: {output}"
            ));
        }
        if !root.join(output).exists() {
            return Err(format!(
                "scripts/generators.tsv:{row}: output path not found: {output}"
            ));
        }
        if !tracked.contains(output.as_bytes()) {
            return Err(format!(
                "scripts/generators.tsv:{row}: output path is not tracked by git: {output}"
            ));
        }
        rows.push(GeneratorRow {
            command: command.to_owned(),
            verb: verb.unwrap_or_default().to_owned(),
            output: output.to_owned(),
        });
    }
    if rows.is_empty() {
        return Err(format!("{}: no rows registered", registry.display()));
    }
    Ok(rows)
}

fn validate_registry_path(row: usize, label: &str, path: &str) -> Result<(), String> {
    if invalid_relative_path(path) || path.contains(['\t', '\n']) {
        return Err(format!(
            "scripts/generators.tsv:{row}: invalid {label} path: {path}"
        ));
    }
    Ok(())
}

fn output_snapshot(
    root: &Path,
    rows: &[GeneratorRow],
) -> Result<BTreeMap<String, Vec<u8>>, String> {
    rows.iter()
        .map(|row| {
            fs::read(root.join(&row.output))
                .map(|contents| (row.output.clone(), contents))
                .map_err(|error| format!("cannot read {}: {error}", row.output))
        })
        .collect()
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

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn generate_check_validates_every_registered_artifact_without_a_delta() {
        let root = repository_root().expect("repository root");
        let tracked = tracked_paths(&root).expect("tracked paths");
        let rows = generator_registry_rows(&root, &tracked).expect("registry rows");
        assert_eq!(rows.len(), 13);
        let before = output_snapshot(&root, &rows).expect("before snapshot");
        generate_check(&root).expect("generated artifacts are current");
        assert_eq!(
            output_snapshot(&root, &rows).expect("after snapshot"),
            before
        );
    }

    #[test]
    fn stale_artifact_fails_check_without_rewriting_it() {
        let temporary = TempDir::new().expect("temporary directory");
        let target = temporary.path().join("artifact.md");
        fs::write(&target, "stale\n").expect("write stale artifact");

        let error = diff_or_write(&target, "fresh\n", true, "code-reviewer-agent")
            .expect_err("stale artifact should fail");

        assert!(error.contains("code-reviewer-agent is out of sync"));
        assert_eq!(
            fs::read_to_string(&target).expect("read stale artifact"),
            "stale\n"
        );
    }

    #[test]
    fn registry_rejects_malformed_and_duplicate_rows() {
        let temporary = TempDir::new().expect("temporary directory");
        let root = temporary.path();
        fs::create_dir_all(root.join("scripts")).expect("create scripts directory");
        let registry = root.join("scripts/generators.tsv");
        fs::write(&registry, "generate code-reviewer-agent\n").expect("write malformed registry");
        let tracked = BTreeSet::new();
        assert!(
            generator_registry_rows(root, &tracked)
                .expect_err("malformed registry should fail")
                .contains("malformed row")
        );

        fs::write(root.join("artifact.md"), "artifact\n").expect("write artifact");
        let mut tracked = BTreeSet::new();
        let _ = tracked.insert(b"artifact.md".to_vec());
        fs::write(
            &registry,
            "generate code-reviewer-agent\tartifact.md\ngenerate code-reviewer-agent\tartifact.md\n",
        )
        .expect("write duplicate registry");
        assert!(
            generator_registry_rows(root, &tracked)
                .expect_err("duplicate registry should fail")
                .contains("duplicate generator command")
        );
    }

    #[test]
    fn registry_path_hygiene_rejects_windows_escape_forms() {
        for path in [
            r"..\artifact.md",
            r"C:\artifact.md",
            r"\\server\artifact.md",
        ] {
            assert!(
                validate_registry_path(1, "output", path).is_err(),
                "path should be rejected: {path}"
            );
        }
    }
}
