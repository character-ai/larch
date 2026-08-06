//! Effect-free rules for clone-scoped progress breadcrumbs and the statusline.
//!
//! The statusline runs on a Claude Code hot path, so every rule here is a pure
//! function over already-read bytes: no filesystem, clock, or process access.
//! The adapters layer supplies the state and applies these decisions.

use core::fmt::Write as _;
use serde_json::{Map, Value, json};
use sha2::{Digest as _, Sha256};
use std::path::Path;

use crate::shell::shell_quote;

/// Directory under the larch cache root that holds clone-scoped progress state.
pub const PROGRESS_DIRNAME: &str = "progress";
/// Basename of the clone-scoped active-run pointer.
pub const CURRENT_RUN_FILENAME: &str = "current";
/// Basename of the clone-scoped pointer lock.
pub const CURRENT_RUN_LOCK_FILENAME: &str = ".current.lock";
/// Basename of a run's breadcrumb log.
pub const RUN_BREADCRUMB_FILENAME: &str = "breadcrumbs.log";
/// Environment variable that opts a clone out of the larch statusline.
pub const STATUSLINE_DISABLE_ENV: &str = "LARCH_STATUSLINE_DISABLE";
/// Clone-local settings file the installer merges into.
pub const STATUSLINE_LOCAL_SETTINGS: &str = ".claude/settings.local.json";
/// Substring that identifies a larch-owned `statusLine` command.
pub const STATUSLINE_COMMAND_MARKER: &str = ".cache/larch/statusline.sh";
/// Second substring that identifies a larch-owned `statusLine` command.
pub const STATUSLINE_VERB_MARKER: &str = "progress statusline";
/// Seconds after which an active breadcrumb log is reported as stale.
pub const DEFAULT_STALE_AFTER_S: u64 = 300;
/// Seconds after which a stale breadcrumb log renders nothing.
pub const DEFAULT_HIDE_AFTER_S: u64 = 3600;
/// Upper bound on rendered breadcrumb lines.
pub const MAX_STATUSLINE_LINES: u64 = 3;
/// Session-start sources that reset a stale active-run pointer.
pub const RESET_SESSION_SOURCES: [&str; 2] = ["startup", "clear"];

const CLONE_HASH_CHARS: usize = 16;
const RUN_ID_MAX_CHARS: usize = 128;
const STATUSLINE_YELLOW: &str = "\u{1b}[33m";
const STATUSLINE_RESET: &str = "\u{1b}[0m";
const PRINTABLE_ASCII_MIN: u32 = 32;
const ASCII_DELETE: u32 = 127;
const C1_CONTROL_MIN: u32 = 0x80;
const C1_CONTROL_MAX: u32 = 0x9F;

/// Return the 16-character clone hash for a canonical repository root.
#[must_use]
pub fn progress_clone_digest(canonical_root: &str) -> String {
    let digest = Sha256::digest(canonical_root.as_bytes());
    let mut hex = String::with_capacity(CLONE_HASH_CHARS);
    for byte in digest.iter().take(CLONE_HASH_CHARS / 2) {
        let _ignored = write!(&mut hex, "{byte:02x}");
    }
    hex
}

/// Return `run_id` when it is a safe, non-reserved progress run identifier.
#[must_use]
pub fn validate_progress_run_id(run_id: &str) -> Option<&str> {
    if run_id.is_empty() || run_id.chars().count() > RUN_ID_MAX_CHARS {
        return None;
    }
    if matches!(run_id, "." | ".." | CURRENT_RUN_FILENAME) {
        return None;
    }
    run_id
        .chars()
        .all(|character| character.is_ascii_alphanumeric() || matches!(character, '.' | '_' | '-'))
        .then_some(run_id)
}

/// Return the exact operator diagnostic for a rejected progress run ID.
#[must_use]
pub fn progress_run_id_error(run_id: &str) -> Option<String> {
    if validate_progress_run_id(run_id).is_some() {
        return None;
    }
    if run_id.is_empty() {
        return Some("run ID must be non-empty".to_owned());
    }
    if matches!(run_id, "." | ".." | CURRENT_RUN_FILENAME) {
        return Some(format!("reserved run ID: {run_id}"));
    }
    Some("run ID must contain only letters, digits, dot, underscore, or dash".to_owned())
}

fn accepted_line_part(value: &str, is_text: bool) -> Option<&str> {
    let text = value.trim();
    if text.is_empty() || text.contains('\t') {
        return None;
    }
    if text.chars().any(|character| {
        let point = u32::from(character);
        point < PRINTABLE_ASCII_MIN
            || point == ASCII_DELETE
            || (C1_CONTROL_MIN..=C1_CONTROL_MAX).contains(&point)
    }) {
        return None;
    }
    // Breadcrumbs identify GitHub entities by number, never by URL.
    (!is_text || !text.contains("://")).then_some(text)
}

/// Compose one breadcrumb line, rejecting multi-line, control, or URL content.
#[must_use]
pub fn breadcrumb_line(skill: &str, step: &str, text: &str) -> Option<String> {
    let skill_text = accepted_line_part(skill, false)?;
    let step_text = accepted_line_part(step, false)?;
    let body = accepted_line_part(text, true)?;
    Some(format!("[{skill_text} {step_text}] {body}\n"))
}

/// Return whether a stored log line is a renderable breadcrumb row.
#[must_use]
pub fn is_breadcrumb_row(line: &str) -> bool {
    line.starts_with('[') && line.contains("] ") && !line.contains('\t')
}

/// Read one positive integer setting, clamped to an optional maximum.
#[must_use]
pub fn positive_int(raw: Option<&str>, default: u64, max_value: Option<u64>) -> u64 {
    let parsed = raw
        .filter(|text| !text.is_empty() && text.bytes().all(|byte| byte.is_ascii_digit()))
        .and_then(|text| text.parse::<u64>().ok())
        .filter(|value| *value > 0)
        .unwrap_or(default);
    max_value.map_or(parsed, |cap| parsed.min(cap))
}

fn payload_object(payload: &str) -> Map<String, Value> {
    let source = if payload.is_empty() { "{}" } else { payload };
    match serde_json::from_str::<Value>(source) {
        Ok(Value::Object(map)) => map,
        Ok(_) | Err(_) => Map::new(),
    }
}

fn payload_string<'a>(payload: &'a Map<String, Value>, key: &str) -> Option<&'a str> {
    payload.get(key).and_then(Value::as_str)
}

fn payload_current_dir(payload: &Map<String, Value>) -> Option<&str> {
    payload
        .get("workspace")
        .and_then(Value::as_object)
        .and_then(|workspace| payload_string(workspace, "current_dir"))
}

/// Return the absolute working directory a statusline payload reports, if any.
///
/// An empty `workspace.current_dir` falls back to `cwd`, matching the renderer,
/// and a relative directory is refused rather than resolved against the cwd.
#[must_use]
pub fn statusline_payload_directory(payload: &str) -> Option<String> {
    let object = payload_object(payload);
    let current_dir = payload_current_dir(&object).filter(|value| !value.is_empty());
    let raw = current_dir.or_else(|| payload_string(&object, "cwd"))?;
    Path::new(raw).is_absolute().then(|| raw.to_owned())
}

/// Return the working directory an install payload reports, if any.
///
/// A present but empty `workspace.current_dir` wins over `cwd`, matching the
/// installer's frozen Python boundary.
#[must_use]
pub fn install_payload_directory(payload: &str) -> Option<String> {
    let object = payload_object(payload);
    let raw = payload_current_dir(&object)
        .or_else(|| payload_string(&object, "cwd"))
        .unwrap_or_default();
    (!raw.is_empty()).then(|| raw.to_owned())
}

/// Return whether a session payload names a source that resets the pointer.
#[must_use]
pub fn resets_active_run(payload: &str) -> bool {
    payload_string(&payload_object(payload), "source")
        .is_some_and(|source| RESET_SESSION_SOURCES.contains(&source))
}

/// Staleness classification for one active-run breadcrumb log.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum StalenessDecision {
    /// The log is recent enough to render without a suffix.
    Fresh,
    /// The log is stale by the given whole minutes.
    Stale(u64),
    /// The log is old enough to render nothing.
    Hidden,
}

/// Classify a breadcrumb log age before any background-job liveness probe.
///
/// A live background job overrides `Stale` and `Hidden` alike, so the caller
/// probes liveness only for a non-`Fresh` result.
#[must_use]
pub const fn classify_staleness(
    age_s: u64,
    stale_after_s: u64,
    hide_after_s: u64,
) -> StalenessDecision {
    if age_s < stale_after_s {
        return StalenessDecision::Fresh;
    }
    if age_s >= hide_after_s {
        return StalenessDecision::Hidden;
    }
    let minutes = age_s / 60;
    StalenessDecision::Stale(if minutes == 0 { 1 } else { minutes })
}

/// Render the suffix a stale breadcrumb row carries.
#[must_use]
pub fn stale_suffix(minutes: u64) -> String {
    format!(" (stale {minutes}m)")
}

/// Truncate one rendered row to a column budget with an ellipsis.
#[must_use]
pub fn truncate_columns(text: &str, columns: usize) -> String {
    if columns == 0 || text.chars().count() <= columns {
        return text.to_owned();
    }
    if columns <= 1 {
        return text.chars().take(columns).collect();
    }
    let mut truncated: String = text.chars().take(columns - 1).collect();
    truncated.push('…');
    truncated
}

/// Render the coloured statusline body for the tailed breadcrumb rows.
#[must_use]
pub fn render_statusline_body(rows: &[&str], stamp: &str, suffix: &str, columns: usize) -> String {
    let rendered = rows
        .iter()
        .map(|row| truncate_columns(&format!("larch {stamp}: {row}{suffix}"), columns))
        .collect::<Vec<_>>()
        .join("\n");
    format!("{STATUSLINE_YELLOW}{rendered}{STATUSLINE_RESET}\n")
}

/// Return the `statusLine.command` a settings document declares.
#[must_use]
pub fn settings_statusline_command(settings: &Value) -> &str {
    settings
        .get("statusLine")
        .and_then(Value::as_object)
        .and_then(|status| status.get("command"))
        .and_then(Value::as_str)
        .unwrap_or_default()
}

/// Return whether a `statusLine.command` is larch-owned.
#[must_use]
pub fn is_larch_statusline_command(command: &str) -> bool {
    command.contains(STATUSLINE_COMMAND_MARKER) || command.contains(STATUSLINE_VERB_MARKER)
}

/// Return the user-scope statusline larch should chain ahead of its own line.
#[must_use]
pub fn chained_user_command(settings: &Value) -> String {
    let command = settings_statusline_command(settings);
    if command.contains('\n') || command.contains('\r') || is_larch_statusline_command(command) {
        return String::new();
    }
    command.to_owned()
}

/// Replace a settings document's `statusLine` with the larch launcher entry.
pub fn apply_statusline(settings: &mut Value, launcher: &str) {
    if let Some(object) = settings.as_object_mut() {
        let _replaced = object.insert(
            "statusLine".to_owned(),
            json!({"type": "command", "command": launcher, "refreshInterval": 2}),
        );
    }
}

/// Render the clone-independent statusline launcher script.
///
/// `larch_entrypoint` is the verified bootstrap script; the launcher never
/// executes the installed binary directly.
#[must_use]
pub fn statusline_launcher_text(
    plugin_root: &str,
    larch_entrypoint: &str,
    user_command: &str,
) -> String {
    let quoted_user = shell_quote(user_command);
    let quoted_root = shell_quote(plugin_root);
    let quoted_entrypoint = shell_quote(larch_entrypoint);
    let render = format!(
        "printf '%s' \"$INPUT\" | CLAUDE_PLUGIN_ROOT={quoted_root} {quoted_entrypoint} progress statusline"
    );
    format!(
        r#"#!/usr/bin/env bash
set -uo pipefail
INPUT=$(cat 2>/dev/null || true)
USER_STATUSLINE_CMD={quoted_user}
LARCH_ENTRYPOINT={quoted_entrypoint}
_larch_timeout_prefix=()
if command -v timeout >/dev/null 2>&1; then
  _larch_timeout_prefix=(timeout 2s)
fi
_larch_run_user_statusline() {{
  if [ -z "$USER_STATUSLINE_CMD" ]; then
    return 0
  fi
  case "$USER_STATUSLINE_CMD" in
    (*[!A-Za-z0-9_./:-]*)
      printf '%s' "$INPUT" | "${{_larch_timeout_prefix[@]}}" sh -c "$USER_STATUSLINE_CMD" 2>/dev/null || true
      ;;
    (*)
      printf '%s' "$INPUT" | "${{_larch_timeout_prefix[@]}}" "$USER_STATUSLINE_CMD" 2>/dev/null || true
      ;;
  esac
}}
if [ -n "$USER_STATUSLINE_CMD" ]; then
  _larch_run_user_statusline
fi
_larch_refresh_seconds=${{LARCH_STATUSLINE_REFRESH_SECONDS:-5}}
case "$_larch_refresh_seconds" in
  (''|*[!0-9]*) _larch_refresh_seconds=5 ;;
esac
if [ "$_larch_refresh_seconds" -le 0 ] 2>/dev/null; then
  _larch_refresh_seconds=5
fi
_larch_cache_source="$INPUT"
if [[ "$INPUT" =~ \"current_dir\"[[:space:]]*:[[:space:]]*\"([^\"]*)\" ]]; then
  _larch_cache_source="${{BASH_REMATCH[1]}}"
elif [[ "$INPUT" =~ \"cwd\"[[:space:]]*:[[:space:]]*\"([^\"]*)\" ]]; then
  _larch_cache_source="${{BASH_REMATCH[1]}}"
fi
_larch_cache_hash=""
if command -v shasum >/dev/null 2>&1; then
  _larch_cache_hash=$(printf '%s' "$_larch_cache_source" | shasum -a 256 2>/dev/null || true)
elif command -v sha256sum >/dev/null 2>&1; then
  _larch_cache_hash=$(printf '%s' "$_larch_cache_source" | sha256sum 2>/dev/null || true)
fi
_larch_cache_hash=${{_larch_cache_hash%% *}}
case "$_larch_cache_hash" in
  (????????????????????????????????????????????????????????????????) ;;
  (*) _larch_cache_hash="" ;;
esac
if [ -n "$_larch_cache_hash" ]; then
  _larch_cache_home=${{XDG_CACHE_HOME:-"$HOME/.cache"}}
  _larch_cache_dir="$_larch_cache_home/larch/progress/${{_larch_cache_hash:0:16}}"
  _larch_cache_file="$_larch_cache_dir/statusline-last"
  _larch_cache_lock="$_larch_cache_file.lock"
  _larch_now=$(date +%s 2>/dev/null || true)
  _larch_mtime=$(stat -f %m "$_larch_cache_file" 2>/dev/null || true)
  case "$_larch_mtime" in (''|*[!0-9]*) _larch_mtime=$(stat -c %Y "$_larch_cache_file" 2>/dev/null || true) ;; esac
  case "$_larch_mtime" in (''|*[!0-9]*) _larch_mtime="" ;; esac
  _larch_lock_mtime=$(stat -f %m "$_larch_cache_lock" 2>/dev/null || true)
  case "$_larch_lock_mtime" in (''|*[!0-9]*) _larch_lock_mtime=$(stat -c %Y "$_larch_cache_lock" 2>/dev/null || true) ;; esac
  case "$_larch_lock_mtime" in (''|*[!0-9]*) _larch_lock_mtime="" ;; esac
  if [ -d "$_larch_cache_lock" ] && [ -n "$_larch_now" ] && [ -n "$_larch_lock_mtime" ]; then
    _larch_lock_age=$((_larch_now - _larch_lock_mtime))
    if [ "$_larch_lock_age" -ge "$_larch_refresh_seconds" ]; then
      rmdir "$_larch_cache_lock" 2>/dev/null || true
    fi
  fi
  if [ -f "$_larch_cache_file" ] && [ -n "$_larch_now" ] && [ -n "$_larch_mtime" ]; then
    _larch_cache_age=$((_larch_now - _larch_mtime))
    if [ "$_larch_cache_age" -ge 0 ] && [ "$_larch_cache_age" -lt "$_larch_refresh_seconds" ]; then
      cat "$_larch_cache_file" 2>/dev/null || true
      exit 0
    fi
  fi
  if mkdir -p "$_larch_cache_dir" 2>/dev/null && mkdir "$_larch_cache_lock" 2>/dev/null; then
    if [ -x "$LARCH_ENTRYPOINT" ]; then
      _larch_cache_tmp="$_larch_cache_file.$$.tmp"
      {render} >"$_larch_cache_tmp" 2>/dev/null || true
      mv -f "$_larch_cache_tmp" "$_larch_cache_file" 2>/dev/null || rm -f "$_larch_cache_tmp"
      cat "$_larch_cache_file" 2>/dev/null || true
    fi
    rmdir "$_larch_cache_lock" 2>/dev/null || true
  elif [ -f "$_larch_cache_file" ]; then
    cat "$_larch_cache_file" 2>/dev/null || true
  fi
elif [ -x "$LARCH_ENTRYPOINT" ]; then
  {render} 2>/dev/null || true
fi
"#
    )
}

#[cfg(test)]
mod tests {
    use super::{
        StalenessDecision, apply_statusline, breadcrumb_line, chained_user_command,
        classify_staleness, install_payload_directory, is_breadcrumb_row, positive_int,
        progress_clone_digest, render_statusline_body, resets_active_run,
        settings_statusline_command, statusline_launcher_text, statusline_payload_directory,
        truncate_columns, validate_progress_run_id,
    };
    use serde_json::json;

    #[test]
    fn clone_digest_matches_the_python_prefix_rule() {
        assert_eq!(progress_clone_digest("/tmp/clone"), "93df82b5525785b8");
        assert_eq!(progress_clone_digest("/tmp/clone").len(), 16);
    }

    #[test]
    fn run_ids_reject_reserved_and_unsafe_spellings() {
        assert_eq!(validate_progress_run_id("run-1"), Some("run-1"));
        assert_eq!(validate_progress_run_id("current"), None);
        assert_eq!(validate_progress_run_id(".."), None);
        assert_eq!(validate_progress_run_id("a/b"), None);
        assert_eq!(validate_progress_run_id(""), None);
        assert_eq!(validate_progress_run_id(&"a".repeat(129)), None);
    }

    #[test]
    fn breadcrumbs_reject_tabs_controls_and_urls() {
        assert_eq!(
            breadcrumb_line("implement", "5", " code review started "),
            Some("[implement 5] code review started\n".to_owned())
        );
        assert_eq!(breadcrumb_line("implement", "5", "see https://x/y"), None);
        assert_eq!(breadcrumb_line("implement", "5", "a\tb"), None);
        assert_eq!(breadcrumb_line("implement", "", "text"), None);
        assert_eq!(breadcrumb_line("implement", "5", "bell\u{7}"), None);
    }

    #[test]
    fn payload_readers_split_on_the_empty_current_dir_case() {
        let payload = r#"{"workspace": {"current_dir": ""}, "cwd": "/clone"}"#;

        assert_eq!(
            statusline_payload_directory(payload),
            Some("/clone".to_owned())
        );
        assert_eq!(install_payload_directory(payload), None);
        assert_eq!(statusline_payload_directory("not json"), None);
        assert_eq!(
            statusline_payload_directory(r#"{"cwd": "relative/dir"}"#),
            None
        );
        assert!(resets_active_run(r#"{"source": "startup"}"#));
        assert!(!resets_active_run(r#"{"source": "resume"}"#));
    }

    #[test]
    fn staleness_and_rendering_match_the_python_thresholds() {
        assert_eq!(classify_staleness(10, 300, 3600), StalenessDecision::Fresh);
        assert_eq!(
            classify_staleness(320, 300, 3600),
            StalenessDecision::Stale(5)
        );
        assert_eq!(
            classify_staleness(301, 300, 3600),
            StalenessDecision::Stale(5)
        );
        assert_eq!(
            classify_staleness(3600, 300, 3600),
            StalenessDecision::Hidden
        );
        assert_eq!(classify_staleness(2, 1, 3600), StalenessDecision::Stale(1));
        assert!(is_breadcrumb_row("[design 3] note"));
        assert!(!is_breadcrumb_row("design 3] note"));
        assert_eq!(truncate_columns("abcdef", 3), "ab…");
        assert_eq!(truncate_columns("abcdef", 0), "abcdef");
        assert_eq!(truncate_columns("abcdef", 1), "a");
        assert_eq!(positive_int(Some("7"), 1, Some(3)), 3);
        assert_eq!(positive_int(Some("0"), 1, None), 1);
        assert_eq!(positive_int(Some("x"), 4, None), 4);
        assert_eq!(
            render_statusline_body(&["[a 1] b"], "14:03", " (stale 5m)", 0),
            "\u{1b}[33mlarch 14:03: [a 1] b (stale 5m)\u{1b}[0m\n"
        );
    }

    #[test]
    fn settings_helpers_preserve_the_installer_decisions() {
        let larch = json!({"statusLine": {"command": "/home/u/.cache/larch/statusline.sh"}});
        let custom = json!({"statusLine": {"command": "/usr/bin/mine"}});

        assert_eq!(chained_user_command(&larch), "");
        assert_eq!(chained_user_command(&custom), "/usr/bin/mine");
        assert_eq!(
            chained_user_command(&json!({"statusLine": {"command": "a\nb"}})),
            ""
        );

        let mut settings = json!({"other": 1});
        apply_statusline(&mut settings, "/launcher.sh");

        assert_eq!(settings_statusline_command(&settings), "/launcher.sh");
        assert_eq!(settings["statusLine"]["refreshInterval"], json!(2));
    }

    #[test]
    fn launcher_text_quotes_its_entrypoint_and_never_runs_the_binary() {
        let launcher = statusline_launcher_text("/plugin", "/plugin/scripts/larch.sh", "");

        assert!(
            launcher.contains(
                "CLAUDE_PLUGIN_ROOT=/plugin /plugin/scripts/larch.sh progress statusline"
            )
        );
        assert!(!launcher.contains("bin/larch"));
        assert!(!launcher.contains("python3"));
    }

    /// Pin the launcher bytes for an underscore-bearing plugin root.
    ///
    /// `install-statusline` has no parity matrix case: the frozen Python
    /// reference in `fixtures/rust-parity/progress_reference.py` deliberately
    /// omits the verb because the launcher body changed by design at the #8084
    /// cutover, so a byte comparison would only prove the fixture and this
    /// renderer agree. This golden is the coverage that would have caught the
    /// #8155 divergence, where `_` was missing from the shell-safe set and
    /// every operator with an underscore in their plugin root or home
    /// directory got a needlessly single-quoted launcher.
    #[test]
    fn launcher_text_leaves_an_underscored_plugin_root_unquoted() {
        let launcher = statusline_launcher_text(
            "/Users/jane_doe/plugin",
            "/Users/jane_doe/plugin/scripts/larch.sh",
            "",
        );

        assert!(launcher.contains(
            "CLAUDE_PLUGIN_ROOT=/Users/jane_doe/plugin \
             /Users/jane_doe/plugin/scripts/larch.sh progress statusline"
        ));
        assert!(launcher.contains("LARCH_ENTRYPOINT=/Users/jane_doe/plugin/scripts/larch.sh\n"));
        assert!(!launcher.contains("'/Users/jane_doe/plugin"));
    }
}
