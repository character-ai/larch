//! Effect-free rules for the session environment and run-flag writers.
//!
//! These are the validations, key allowlists, and rendered launcher texts the
//! `session write-*`, `persist-run-flags`, and `restore-finalize-state` verbs
//! share. Filesystem effects live in the adapter layer; ambient state is read at
//! the composition root and passed in.

use regex::Regex;
use std::sync::LazyLock;

use crate::shell::shell_quote;

/// Longest accepted path-shaped flag value, in characters.
pub const MAX_PATH_VALUE_LEN: usize = 512;

/// Keys the implement session-env writer may emit.
pub const WRITE_ENV_KEYS: [&str; 17] = [
    "REPO",
    "REPO_ROOT",
    "REPO_UNAVAILABLE",
    "FORKED_TARGET",
    "LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT",
    "CLAUDE_BINARY_FOUND",
    "CODEX_BINARY_FOUND",
    "CURSOR_BINARY_FOUND",
    "LARCH_AUTO_MODE",
    "LARCH_TIMING_LEDGER",
    "LARCH_TOKEN_SESSION_ID",
    "LARCH_CLAUDE_SOURCE_FILE",
    "PREV_IMPLEMENT_TMPDIR",
    "LARCH_DYNAMIC_ARCHETYPES_MAX",
    "LARCH_RUN_ID",
    "LARCH_CLAUDE_PLUGIN_ROOT",
    "LARCH_LIVE_MUTATION_OK",
];

/// Keys the design session-env writer may emit.
pub const WRITE_DESIGN_ENV_KEYS: [&str; 13] = [
    "DESIGN_TMPDIR",
    "SESSION_TMPDIR",
    "SESSION_ID",
    "REPO",
    "REPO_ROOT",
    "ISSUE_NUMBER",
    "CODEX_BINARY_FOUND",
    "CURSOR_BINARY_FOUND",
    "LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT",
    "CLAUDE_PLUGIN_ROOT",
    "LARCH_CLAUDE_SOURCE_FILE",
    "LARCH_RUN_ID",
    "LARCH_LIVE_MUTATION_OK",
];

/// Keys the persisted implement run-flags file may carry.
pub const RUN_FLAG_KEYS: [&str; 6] = [
    "QUICK_MODE",
    "NO_ISSUES",
    "FORCE_REQUESTED",
    "SELF_REVIEW_REQUESTED",
    "SELF_IMPLEMENT_REQUESTED",
    "DIFFICULTY_OVERRIDE",
];

/// Ordered keys the finalize-state restore writes, first to last.
pub const RESTORE_FINALIZE_KEYS: [&str; 20] = [
    "BRANCH_NAME",
    "PR_NUMBER",
    "PR_TITLE",
    "PR_URL",
    "ISSUE_NUMBER",
    "REPO",
    "DRAFT",
    "MERGE",
    "DEFERRED",
    "REPO_UNAVAILABLE",
    "PR_CLOSED",
    "DESIGN_ONLY_DONE",
    "BAIL_NEEDS_USER_INPUT",
    "STALL_TRACKING",
    "STALL_STEP",
    "DONE_RENAME_APPLIED",
    "RUN_ID",
    "EXPECTED_SESSION_ID",
    "EXPECTED_TMPDIR_BASENAME_PREFIX",
    "NO_LOGS_COMMIT",
];

/// Difficulty tiers an override flag may name.
pub const DIFFICULTY_CHOICES: [&str; 3] = ["TRIVIAL", "MODERATE", "HARD"];

/// Default value for a finalize-state key absent from both sources.
#[must_use]
pub fn restore_finalize_default(key: &str) -> &'static str {
    match key {
        "DESIGN_ONLY_DONE"
        | "DRAFT"
        | "MERGE"
        | "DEFERRED"
        | "REPO_UNAVAILABLE"
        | "PR_CLOSED"
        | "BAIL_NEEDS_USER_INPUT"
        | "STALL_TRACKING"
        | "DONE_RENAME_APPLIED"
        | "NO_LOGS_COMMIT" => "false",
        _ => "",
    }
}

// Python anchors these with `re.match` and a trailing `$`, which also accepts one
// trailing newline. The `\n?` suffix reproduces that boundary exactly; the
// separate `_FULL` spellings reproduce `re.fullmatch`, which does not.
static SAFE_PATH_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[A-Za-z0-9_./~+-]+\n?$").expect("valid safe-path regex"));
static SAFE_ID_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[A-Za-z0-9_.-]{1,128}\n?$").expect("valid safe-id regex"));
static SAFE_RUN_ID_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[A-Za-z0-9._-]{1,128}\n?$").expect("valid run-id regex"));
static SAFE_RUN_ID_FULL_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[A-Za-z0-9._-]{1,128}$").expect("valid strict run-id regex"));
static REPO_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+\n?$").expect("valid repo regex")
});
static CLAUDE_PID_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[1-9][0-9]{0,6}\n?$").expect("valid claude-pid regex"));

/// Return whether `value` is one of the two accepted boolean spellings.
#[must_use]
pub fn is_bool(value: &str) -> bool {
    value == "true" || value == "false"
}

/// Reject a non-boolean flag value with the operator diagnostic.
///
/// # Errors
///
/// Returns the exact `Invalid <flag>` message when the value is not boolean.
pub fn parse_bool_arg(value: &str, flag: &str) -> Result<(), String> {
    if is_bool(value) {
        Ok(())
    } else {
        Err(format!("Invalid {flag}: must be true or false"))
    }
}

/// Return whether a `CLAUDE_PLUGIN_ROOT` value is an accepted absolute path.
#[must_use]
pub fn is_valid_plugin_root_value(value: &str) -> bool {
    !value.is_empty()
        && value.chars().count() <= MAX_PATH_VALUE_LEN
        && value.starts_with('/')
        && SAFE_PATH_RE.is_match(value)
}

/// Return whether a `--repo` value names `OWNER/REPO` or is absent.
#[must_use]
pub fn is_valid_repo_value(value: &str) -> bool {
    if value.is_empty() {
        return true;
    }
    if value.starts_with("--")
        || value.starts_with('/')
        || value.contains("../")
        || value.contains('\\')
        || value.contains(['\n', '\r'])
    {
        return false;
    }
    REPO_RE.is_match(value)
}

/// Return whether a `--claude-pid` value is a bounded positive integer.
#[must_use]
pub fn is_valid_claude_pid(value: &str) -> bool {
    CLAUDE_PID_RE.is_match(value)
}

/// Return whether a session identity matches the shared id grammar.
#[must_use]
pub fn is_valid_session_id(value: &str) -> bool {
    SAFE_ID_RE.is_match(value)
}

/// Return whether a run identity matches the shared run-id grammar.
#[must_use]
pub fn is_valid_run_id(value: &str) -> bool {
    SAFE_RUN_ID_RE.is_match(value)
}

/// Return whether a run identity matches the grammar with no trailing newline.
#[must_use]
pub fn is_strict_run_id(value: &str) -> bool {
    SAFE_RUN_ID_FULL_RE.is_match(value)
}

/// Reject a path-shaped flag value that is too long or carries unsafe bytes.
///
/// # Errors
///
/// Returns the exact `Invalid <flag>` message for a rejected non-empty value.
pub fn validate_path_arg_value(value: &str, flag: &str) -> Result<(), String> {
    if !value.is_empty()
        && (value.chars().count() > MAX_PATH_VALUE_LEN || !SAFE_PATH_RE.is_match(value))
    {
        return Err(format!(
            "Invalid {flag}: must match ^[A-Za-z0-9_./~+-]{{1,512}}$"
        ));
    }
    Ok(())
}

/// Reject a repository root that is not a bounded absolute single-line path.
///
/// # Errors
///
/// Returns the exact `Invalid <flag>` message for a rejected non-empty value.
pub fn validate_repo_root_value(value: &str, flag: &str) -> Result<(), String> {
    if value.is_empty() {
        return Ok(());
    }
    if value.chars().count() > MAX_PATH_VALUE_LEN || value.contains(['\n', '\r', '\0']) {
        return Err(format!(
            "Invalid {flag}: must be an absolute single-line path"
        ));
    }
    if !value.starts_with('/') {
        return Err(format!("Invalid {flag}: must be an absolute path"));
    }
    Ok(())
}

/// Reject any writer row whose value would forge a new wire line.
///
/// # Errors
///
/// Returns the exact diagnostic naming the first offending key.
pub fn validate_no_newlines(rows: &[(&str, String)]) -> Result<(), String> {
    for (key, value) in rows {
        if value.contains(['\n', '\r']) {
            return Err(format!(
                "value for {key} contains newline or carriage return"
            ));
        }
    }
    Ok(())
}

/// Reject any writer row whose key is outside the writer's allowlist.
///
/// # Errors
///
/// Returns the exact diagnostic naming the first disallowed key.
pub fn validate_writer_keys(rows: &[(&str, String)], allowed: &[&str]) -> Result<(), String> {
    for (key, _value) in rows {
        if !allowed.contains(key) {
            return Err(format!("disallowed writer key: {key}"));
        }
    }
    Ok(())
}

/// Resolve the external health-check timeout, defaulting a non-numeric override.
#[must_use]
pub fn external_timeout(raw: Option<&str>) -> String {
    raw.filter(|value| !value.is_empty() && value.chars().all(|digit| digit.is_ascii_digit()))
        .map_or_else(|| "60".to_owned(), ToOwned::to_owned)
}

/// Render one `export KEY=<quoted>` line for a design session-env file.
#[must_use]
pub fn export_line(key: &str, value: &str) -> String {
    format!("export {key}={}\n", shell_quote(value))
}

/// Render the PID-keyed `/design` wrapper launcher script.
#[must_use]
pub fn design_run_launcher_text(pid: &str, plugin_root: &str) -> String {
    let quoted_plugin_root = shell_quote(plugin_root);
    format!(
        concat!(
            "#!/usr/bin/env bash\n",
            "set -uo pipefail\n",
            "PLUGIN_ROOT={quoted_plugin_root}\n",
            "SESSION_ENV_PATH=\"$HOME/.cache/larch/sessions/current-design-env-{pid}.sh\"\n",
            "CLAUDE_PID={pid}\n",
            "if [ \"$#\" -lt 1 ]; then\n",
            "  printf '%s\\n' 'ERROR=missing design wrapper script name' >&2\n",
            "  exit 2\n",
            "fi\n",
            "script=$1\n",
            "shift\n",
            "case \"$script\" in\n",
            r#"  ""|*/*|*..*|*\\*|*\;*|*\&*|*\|*|*\$*|*\`*|*\(*|*\)*|*\<*|*\>*|*[[:space:]]*)"#,
            "\n",
            "    printf '%s\\n' 'ERROR=invalid design wrapper script name' >&2\n",
            "    exit 2\n",
            "    ;;\n",
            "esac\n",
            "export CLAUDE_PLUGIN_ROOT=\"$PLUGIN_ROOT\"\n",
            "case \"$script\" in\n",
            "  step0-*.sh|step0c.sh|step1d5.sh|step1d7.sh|step1e-reentry.sh|design-step0-parse.sh|design-step0-session.sh|design-step0-route.sh|design-step0-clarify-hard-halt.sh|design-step0-init.sh|design-step0-abort-cleanup.sh|design-step0-ap-continue.sh|design-step0c.sh|design-step1d5.sh|design-step1d7.sh|design-step1e-reentry.sh|design-step2b-drafter.sh|design-step2b-postplan.sh)\n",
            "    printf '%s\\n' 'ERROR=ported design wrapper must use bare verb name, not .sh' >&2\n",
            "    exit 2\n",
            "    ;;\n",
            "  design-step35-settle.sh)\n",
            "    exec python3 \"$PLUGIN_ROOT/python/cli.py\" design step35-settle --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"\n",
            "    ;;\n",
            "  design-step2b5.sh)\n",
            "    exec python3 \"$PLUGIN_ROOT/python/cli.py\" design step2b5 --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"\n",
            "    ;;\n",
            "  design-step6.sh)\n",
            "    exec python3 \"$PLUGIN_ROOT/python/cli.py\" design step6 --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"\n",
            "    ;;\n",
            "  design-step6-prelude.sh)\n",
            "    exec python3 \"$PLUGIN_ROOT/python/cli.py\" design step6-prelude --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"\n",
            "    ;;\n",
            "  design-step6-cleanup.sh)\n",
            "    exec python3 \"$PLUGIN_ROOT/python/cli.py\" design step6-cleanup --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"\n",
            "    ;;\n",
            "  design-step-validator-autofix.sh)\n",
            "    exec \"$PLUGIN_ROOT/scripts/larch.sh\" plan validator-autofix --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"\n",
            "    ;;\n",
            "  design-stage-terminal-state.sh)\n",
            "    exec \"$PLUGIN_ROOT/scripts/larch.sh\" design stage-terminal-state \"$@\"\n",
            "    ;;\n",
            "  design-failure-report.sh)\n",
            "    exec \"$PLUGIN_ROOT/scripts/larch.sh\" design failure-report \"$@\"\n",
            "    ;;\n",
            "  design-step-final-summary.sh)\n",
            "    exec \"$PLUGIN_ROOT/scripts/larch.sh\" design step-final-summary --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"\n",
            "    ;;\n",
            "  *.sh)\n",
            "    exec \"$PLUGIN_ROOT/skills/design/scripts/$script\" --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"\n",
            "    ;;\n",
            "  step0-parse|step0-session|step0-route|step0-clarify-hard-halt|step0-init|step0-abort-cleanup|step0-ap-continue|step0c)\n",
            "    exec \"$PLUGIN_ROOT/scripts/larch.sh\" design \"$script\" --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"\n",
            "    ;;\n",
            "  step1d5|step1d7|step1e-reentry)\n",
            "    exec \"$PLUGIN_ROOT/scripts/larch.sh\" design \"$script\" --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"\n",
            "    ;;\n",
            "  step2b-drafter|step2b-postplan|step3b-entry)\n",
            "    exec \"$PLUGIN_ROOT/scripts/larch.sh\" design \"$script\" --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"\n",
            "    ;;\n",
            "  step6|step6-prelude|step6-cleanup)\n",
            "    exec python3 \"$PLUGIN_ROOT/python/cli.py\" design \"$script\" --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"\n",
            "    ;;\n",
            "  *.*)\n",
            "    printf '%s\\n' 'ERROR=design verb must be bare and must not end in .sh' >&2\n",
            "    exit 2\n",
            "    ;;\n",
            "  *)\n",
            "    printf '%s\\n' 'ERROR=unknown design wrapper verb' >&2\n",
            "    exit 2\n",
            "    ;;\n",
            "esac\n",
        ),
        quoted_plugin_root = quoted_plugin_root,
        pid = pid,
    )
}

/// Render the PID-keyed `/implement` stable launcher script.
#[must_use]
pub fn implement_run_launcher_text(pid: &str) -> String {
    format!(
        concat!(
            "#!/usr/bin/env bash\n",
            "set -uo pipefail\n",
            "POINTER=\"$HOME/.cache/larch/sessions/current-implement-env-{pid}.sh\"\n",
            "[ -f \"$POINTER\" ] && [ ! -L \"$POINTER\" ] || {{ printf '%s\\n' \"implement-run: missing current-env pointer: $POINTER\" >&2; exit 2; }}\n",
            "IMPLEMENT_TMPDIR=$(awk 'BEGIN{{p=\"IMPLEMENT_TMPDIR=\"}} index($0,p)==1{{print substr($0,length(p)+1); found=1; exit}} END{{exit found ? 0 : 1}}' \"$POINTER\" 2>/dev/null) || {{ printf '%s\\n' \"implement-run: IMPLEMENT_TMPDIR missing from pointer: $POINTER\" >&2; exit 2; }}\n",
            "[ -n \"$IMPLEMENT_TMPDIR\" ] || {{ printf '%s\\n' \"implement-run: IMPLEMENT_TMPDIR empty in pointer: $POINTER\" >&2; exit 2; }}\n",
            "case \"$IMPLEMENT_TMPDIR\" in /*) ;; *) printf '%s\\n' \"implement-run: IMPLEMENT_TMPDIR must be absolute: $IMPLEMENT_TMPDIR\" >&2; exit 2 ;; esac\n",
            "LARCH_RUN_SH=\"$IMPLEMENT_TMPDIR/larch-run.sh\"\n",
            "[ -f \"$LARCH_RUN_SH\" ] || {{ printf '%s\\n' \"implement-run: missing larch-run.sh: $LARCH_RUN_SH\" >&2; exit 2; }}\n",
            "[ -x \"$LARCH_RUN_SH\" ] || {{ printf '%s\\n' \"implement-run: larch-run.sh is not executable: $LARCH_RUN_SH\" >&2; exit 2; }}\n",
            "export IMPLEMENT_TMPDIR\n",
            "export LARCH_CLAUDE_PID=\"${{LARCH_CLAUDE_PID:-{pid}}}\"\n",
            "exec \"$LARCH_RUN_SH\" \"$@\"\n",
        ),
        pid = pid,
    )
}

/// Render a path the way Python's `str(PurePosixPath(value))` renders it.
///
/// Verbs that echo a caller-supplied path back on stdout report the normalized
/// spelling: repeated separators collapse, `.` components and trailing
/// separators drop, `..` is preserved, and exactly two leading separators
/// survive because POSIX reserves that spelling.
#[must_use]
pub fn posix_path_display(value: &str) -> String {
    let components: Vec<&str> = value
        .split('/')
        .filter(|component| !component.is_empty() && *component != ".")
        .collect();
    let root = if value.starts_with("//") && !value.starts_with("///") {
        "//"
    } else if value.starts_with('/') {
        "/"
    } else {
        ""
    };
    if components.is_empty() {
        return if root.is_empty() {
            ".".to_owned()
        } else {
            root.to_owned()
        };
    }
    format!("{root}{}", components.join("/"))
}

/// Render the two-line `plugin-root.env` sidecar.
#[must_use]
pub fn plugin_root_env_text(value: &str) -> String {
    format!("CLAUDE_PLUGIN_ROOT={value}\nexport CLAUDE_PLUGIN_ROOT\n")
}

/// The `/design` run parameters one `run-params.json` document records.
#[allow(clippy::struct_excessive_bools)] // one field per schema v3 wire boolean
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct RunParams<'a> {
    /// Whether the operator asked for issue partitioning.
    pub partition_requested: bool,
    /// Whether the operator asked for a brainstorm pass.
    pub brainstorm_requested: bool,
    /// Whether the operator asked for explicit per-round approval.
    pub approve_requested: bool,
    /// Whether the operator asked to skip the approval gates.
    pub skip_approve_requested: bool,
    /// Operator-forced difficulty tier, or empty for the panel's own rating.
    pub difficulty_override: &'a str,
}

/// Render the schema v3 `run-params.json` payload for one `/design` run.
#[must_use]
pub fn run_params_json(params: RunParams<'_>) -> String {
    format!(
        concat!(
            "{{\n",
            "  \"schema_version\": 3,\n",
            "  \"partition_requested\": {},\n",
            "  \"brainstorm_requested\": {},\n",
            "  \"approve_requested\": {},\n",
            "  \"skip_approve_requested\": {},\n",
            "  \"difficulty_override\": {}\n",
            "}}\n",
        ),
        params.partition_requested,
        params.brainstorm_requested,
        params.approve_requested,
        params.skip_approve_requested,
        json_string(params.difficulty_override),
    )
}

/// Render one JSON string literal the way `json.dumps` renders it.
fn json_string(value: &str) -> String {
    use std::fmt::Write as _;

    let mut rendered = String::with_capacity(value.len() + 2);
    rendered.push('"');
    for character in value.chars() {
        match character {
            '"' => rendered.push_str("\\\""),
            '\\' => rendered.push_str("\\\\"),
            '\n' => rendered.push_str("\\n"),
            '\r' => rendered.push_str("\\r"),
            '\t' => rendered.push_str("\\t"),
            control if control < ' ' || control == '\u{7f}' => {
                let _ignored = write!(rendered, "\\u{:04x}", control as u32);
            }
            other if (other as u32) > 0x7f => {
                for unit in other.encode_utf16(&mut [0_u16; 2]) {
                    let _ignored = write!(rendered, "\\u{unit:04x}");
                }
            }
            other => rendered.push(other),
        }
    }
    rendered.push('"');
    rendered
}

#[cfg(test)]
mod tests {
    use super::{
        RunParams, WRITE_ENV_KEYS, design_run_launcher_text, export_line, external_timeout,
        implement_run_launcher_text, is_strict_run_id, is_valid_claude_pid,
        is_valid_plugin_root_value, is_valid_repo_value, is_valid_run_id, posix_path_display,
        restore_finalize_default, run_params_json, shell_quote, validate_no_newlines,
        validate_path_arg_value, validate_repo_root_value, validate_writer_keys,
    };

    #[test]
    fn trailing_newline_boundary_matches_python_match_and_fullmatch() {
        assert!(is_valid_run_id("run-1"));
        // Python's `$` accepts one trailing newline under `re.match` ...
        assert!(is_valid_run_id("run-1\n"));
        // ... but not under `re.fullmatch`, which the design writer uses.
        assert!(is_strict_run_id("run-1"));
        assert!(!is_strict_run_id("run-1\n"));
        assert!(!is_valid_run_id(""));
        assert!(!is_valid_run_id("run/1"));
    }

    #[test]
    fn plugin_root_and_repo_values_reject_traversal_and_relatives() {
        assert!(is_valid_plugin_root_value("/opt/larch"));
        assert!(!is_valid_plugin_root_value("opt/larch"));
        assert!(!is_valid_plugin_root_value(&format!(
            "/{}",
            "a".repeat(512)
        )));
        assert!(is_valid_repo_value(""));
        assert!(is_valid_repo_value("character-ai/larch"));
        assert!(!is_valid_repo_value("/character-ai/larch"));
        assert!(!is_valid_repo_value("../character-ai/larch"));
        assert!(!is_valid_repo_value("--flag/value"));
        assert!(is_valid_claude_pid("1234567"));
        assert!(!is_valid_claude_pid("0"));
        assert!(!is_valid_claude_pid("12345678"));
    }

    #[test]
    fn path_and_repo_root_validation_reports_the_legacy_message() {
        assert_eq!(validate_path_arg_value("", "--timing-ledger"), Ok(()));
        assert_eq!(
            validate_path_arg_value("a b", "--timing-ledger"),
            Err("Invalid --timing-ledger: must match ^[A-Za-z0-9_./~+-]{1,512}$".to_owned())
        );
        assert_eq!(validate_repo_root_value("", "--repo-root"), Ok(()));
        assert_eq!(
            validate_repo_root_value("relative", "--repo-root"),
            Err("Invalid --repo-root: must be an absolute path".to_owned())
        );
        assert_eq!(
            validate_repo_root_value("/a\nb", "--repo-root"),
            Err("Invalid --repo-root: must be an absolute single-line path".to_owned())
        );
    }

    #[test]
    fn writer_row_guards_name_the_first_offender() {
        let rows = [("REPO", "a/b".to_owned()), ("BOGUS", String::new())];
        assert_eq!(
            validate_writer_keys(&rows, &WRITE_ENV_KEYS),
            Err("disallowed writer key: BOGUS".to_owned())
        );
        assert_eq!(
            validate_no_newlines(&[("REPO", "a\nb".to_owned())]),
            Err("value for REPO contains newline or carriage return".to_owned())
        );
    }

    #[test]
    fn timeout_and_defaults_fall_back_to_the_legacy_constants() {
        assert_eq!(external_timeout(None), "60");
        assert_eq!(external_timeout(Some("")), "60");
        assert_eq!(external_timeout(Some("12x")), "60");
        assert_eq!(external_timeout(Some("900")), "900");
        assert_eq!(restore_finalize_default("DRAFT"), "false");
        assert_eq!(restore_finalize_default("BRANCH_NAME"), "");
    }

    #[test]
    fn shell_quoting_matches_python_shlex_quote() {
        assert_eq!(shell_quote(""), "''");
        assert_eq!(shell_quote("/tmp/session"), "/tmp/session");
        assert_eq!(shell_quote("a b"), "'a b'");
        assert_eq!(shell_quote("it's"), r#"'it'"'"'s'"#);
        assert_eq!(export_line("REPO", "a/b"), "export REPO=a/b\n");
    }

    #[test]
    fn launcher_texts_pin_the_pid_and_plugin_root() {
        let design = design_run_launcher_text("4321", "/opt/larch");
        assert!(
            design.starts_with("#!/usr/bin/env bash\nset -uo pipefail\nPLUGIN_ROOT=/opt/larch\n")
        );
        assert!(design.contains("current-design-env-4321.sh"));
        // Leaf #8578: the Step 0 owner verbs run through the Rust entrypoint.
        // Leaf #8579: the step1d5/step1d7/step1e-reentry verbs now route through
        // the Rust entrypoint as well.
        assert!(design.contains(
            "  step0-parse|step0-session|step0-route|step0-clarify-hard-halt|step0-init|step0-abort-cleanup|step0-ap-continue|step0c)\n    exec \"$PLUGIN_ROOT/scripts/larch.sh\" design \"$script\" --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"\n"
        ));
        assert!(design.contains(
            "  step1d5|step1d7|step1e-reentry)\n    exec \"$PLUGIN_ROOT/scripts/larch.sh\" design \"$script\" --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"\n"
        ));
        // Leaf #8583: the drafting and post-plan verbs route through the Rust
        // entrypoint, and their pre-cutover `.sh` names are rejected.
        assert!(design.contains(
            "  step2b-drafter|step2b-postplan|step3b-entry)\n    exec \"$PLUGIN_ROOT/scripts/larch.sh\" design \"$script\" --session-env-path \"$SESSION_ENV_PATH\" --claude-pid \"$CLAUDE_PID\" \"$@\"\n"
        ));
        assert!(design.contains("design-step2b-drafter.sh|design-step2b-postplan.sh)"));
        assert!(design.ends_with("esac\n"));
        let implement = implement_run_launcher_text("4321");
        assert!(implement.contains("current-implement-env-4321.sh"));
        assert!(implement.contains("${LARCH_CLAUDE_PID:-4321}"));
        assert!(implement.ends_with("exec \"$LARCH_RUN_SH\" \"$@\"\n"));
    }

    #[test]
    fn posix_path_display_matches_python_path_str() {
        for (raw, expected) in [
            ("/a//b", "/a/b"),
            ("//a/b", "//a/b"),
            ("///a/b", "/a/b"),
            ("/a/./b", "/a/b"),
            ("/a/../b", "/a/../b"),
            ("/a/b/", "/a/b"),
            ("", "."),
            ("/", "/"),
            ("//", "//"),
            ("/a//", "/a"),
            ("a/b", "a/b"),
            ("/a/.//b/", "/a/b"),
        ] {
            assert_eq!(posix_path_display(raw), expected, "input {raw:?}");
        }
    }

    #[test]
    fn run_params_render_matches_the_python_json_dump() {
        assert_eq!(
            run_params_json(RunParams {
                partition_requested: true,
                skip_approve_requested: true,
                difficulty_override: "HARD",
                ..RunParams::default()
            }),
            concat!(
                "{\n",
                "  \"schema_version\": 3,\n",
                "  \"partition_requested\": true,\n",
                "  \"brainstorm_requested\": false,\n",
                "  \"approve_requested\": false,\n",
                "  \"skip_approve_requested\": true,\n",
                "  \"difficulty_override\": \"HARD\"\n",
                "}\n",
            )
        );
    }
}
