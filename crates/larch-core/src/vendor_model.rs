//! Model-argument resolution and Claude transcript model discovery.

use crate::env;
use std::collections::BTreeMap;

/// Default Cursor model when no env or plugin override is set.
pub const CURSOR_DEFAULT_MODEL: &str = "composer-2.5";
/// Default Codex model for the default role.
pub const CODEX_DEFAULT_MODEL: &str = "gpt-5.6-sol";
/// Default Codex model for the review role.
pub const CODEX_REVIEW_MODEL_DEFAULT: &str = "gpt-5.6-luna";
/// Default Codex model for the vote role.
pub const CODEX_VOTE_MODEL_DEFAULT: &str = "gpt-5.6-terra";
/// Default Codex model for the fix role.
pub const CODEX_FIX_MODEL_DEFAULT: &str = "gpt-5.6-terra";

/// Vendor tool accepted by `agent model-args --tool`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ModelTool {
    /// Cursor agent.
    Cursor,
    /// Codex CLI.
    Codex,
}

/// Codex model-role pin used when resolving Codex argv.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CodexModelRole {
    /// Default Codex model role.
    Default,
    /// Reviewer model role.
    Review,
    /// Voter model role.
    Vote,
    /// Fixer model role.
    Fix,
}

impl ModelTool {
    /// Parse the `--tool` flag value.
    ///
    /// # Errors
    ///
    /// Returns [`ModelArgError`] when the token is not `cursor` or `codex`.
    pub fn parse(raw: &str) -> Result<Self, ModelArgError> {
        match raw {
            "cursor" => Ok(Self::Cursor),
            "codex" => Ok(Self::Codex),
            other => Err(ModelArgError::new(format!(
                "--tool must be 'cursor' or 'codex' (got: {other})"
            ))),
        }
    }
}

impl CodexModelRole {
    /// Parse the `--codex-role` flag value.
    ///
    /// # Errors
    ///
    /// Returns [`ModelArgError`] when the token is not a supported role.
    pub fn parse(raw: &str) -> Result<Self, ModelArgError> {
        match raw {
            "default" => Ok(Self::Default),
            "review" => Ok(Self::Review),
            "vote" => Ok(Self::Vote),
            "fix" => Ok(Self::Fix),
            other => Err(ModelArgError::new(format!(
                "--codex-role must be default|review|vote|fix (got: {other})"
            ))),
        }
    }
}

/// Resolved model argv tokens plus an optional operator warning.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ModelArgResult {
    argv: Vec<String>,
    warning: String,
}

impl ModelArgResult {
    /// Return the argv tokens that should be appended to a vendor launch.
    #[must_use]
    pub fn argv(&self) -> &[String] {
        &self.argv
    }

    /// Return the optional warning written to stderr by the CLI.
    #[must_use]
    pub fn warning(&self) -> &str {
        &self.warning
    }
}

/// Fail-closed model-argument resolution error.
pub type ModelArgError = crate::message_error::MessageError;
/// Resolve Cursor or Codex model argv from an environment map.
///
/// # Errors
///
/// Returns [`ModelArgError`] when a selected model token is blank or contains
/// POSIX control characters, or when the tool/role combination is invalid.
pub fn resolve_model_args(
    tool: ModelTool,
    with_effort: bool,
    default_model: &str,
    codex_role: CodexModelRole,
    env_map: &BTreeMap<String, String>,
) -> Result<ModelArgResult, ModelArgError> {
    match tool {
        ModelTool::Cursor => {
            let model = resolve_named(
                env_map,
                env::LARCH_CURSOR_MODEL,
                env::CLAUDE_PLUGIN_OPTION_CURSOR_MODEL,
                if default_model.is_empty() {
                    CURSOR_DEFAULT_MODEL
                } else {
                    default_model
                },
            )?;
            Ok(ModelArgResult {
                argv: vec!["--model".to_owned(), model],
                warning: String::new(),
            })
        }
        ModelTool::Codex => {
            resolve_codex_model_args(with_effort, default_model, codex_role, env_map)
        }
    }
}

fn resolve_codex_model_args(
    with_effort: bool,
    default_model: &str,
    codex_role: CodexModelRole,
    env_map: &BTreeMap<String, String>,
) -> Result<ModelArgResult, ModelArgError> {
    let model = match codex_role {
        CodexModelRole::Default => resolve_named(
            env_map,
            env::LARCH_CODEX_MODEL,
            env::CLAUDE_PLUGIN_OPTION_CODEX_MODEL,
            if default_model.is_empty() {
                CODEX_DEFAULT_MODEL
            } else {
                default_model
            },
        )?,
        CodexModelRole::Review => resolve_role_model(
            env_map,
            env::LARCH_CODEX_REVIEW_MODEL,
            default_model,
            CODEX_REVIEW_MODEL_DEFAULT,
        )?,
        CodexModelRole::Vote => resolve_role_model(
            env_map,
            env::LARCH_CODEX_VOTE_MODEL,
            default_model,
            CODEX_VOTE_MODEL_DEFAULT,
        )?,
        CodexModelRole::Fix => resolve_role_model(
            env_map,
            env::LARCH_CODEX_FIX_MODEL,
            default_model,
            CODEX_FIX_MODEL_DEFAULT,
        )?,
    };
    let mut argv = vec!["-m".to_owned(), model];
    let mut warning = String::new();
    if with_effort {
        let (effort, effort_warning) = resolve_effort(env_map);
        warning = effort_warning;
        argv.extend([
            "-c".to_owned(),
            format!("model_reasoning_effort=\"{effort}\""),
        ]);
    }
    Ok(ModelArgResult { argv, warning })
}

fn resolve_named(
    env_map: &BTreeMap<String, String>,
    primary: &str,
    plugin: &str,
    default_value: &str,
) -> Result<String, ModelArgError> {
    if let Some(value) = env_map.get(primary) {
        return reject_blank(value, primary);
    }
    if let Some(value) = env_map.get(plugin) {
        return reject_blank(value, plugin);
    }
    reject_blank(default_value, "default model")
}

fn resolve_role_model(
    env_map: &BTreeMap<String, String>,
    env_name: &str,
    default_model: &str,
    role_default: &str,
) -> Result<String, ModelArgError> {
    let effective = if default_model.is_empty() {
        role_default
    } else {
        default_model
    };
    if let Some(value) = env_map.get(env_name) {
        return reject_blank(value, env_name);
    }
    reject_blank(effective, "default model")
}

fn resolve_effort(env_map: &BTreeMap<String, String>) -> (String, String) {
    let raw = env_map
        .get(env::LARCH_CODEX_EFFORT)
        .cloned()
        .or_else(|| env_map.get(env::CLAUDE_PLUGIN_OPTION_CODEX_EFFORT).cloned())
        .unwrap_or_else(|| "high".to_owned());
    match raw.as_str() {
        "minimal" | "low" | "medium" | "high" => (raw, String::new()),
        other => (
            "high".to_owned(),
            format!(
                "WARN invalid codex effort '{other}' (must be minimal|low|medium|high); falling back to 'high'"
            ),
        ),
    }
}

fn reject_blank(value: &str, context: &str) -> Result<String, ModelArgError> {
    reject_control(value, context)?;
    if value.trim().is_empty() {
        return Err(ModelArgError::new(format!(
            "{context} must not be blank or whitespace-only"
        )));
    }
    Ok(value.to_owned())
}

fn reject_control(value: &str, context: &str) -> Result<(), ModelArgError> {
    if value.chars().any(is_posix_cntrl) {
        return Err(ModelArgError::new(format!(
            "{context} must not contain POSIX [[:cntrl:]] characters"
        )));
    }
    Ok(())
}

/// Return true for POSIX `[[:cntrl:]]` characters (`\\x00-\\x1f` and `\\x7f`).
#[must_use]
pub const fn is_posix_cntrl(ch: char) -> bool {
    matches!(ch, '\u{0000}'..='\u{001f}' | '\u{007f}')
}

/// Validate one emitted argv token before writing it to stdout.
///
/// # Errors
///
/// Returns [`ModelArgError`] when the token contains POSIX control characters.
pub fn validate_emitted_token(token: &str) -> Result<(), ModelArgError> {
    if token.is_empty() {
        return Ok(());
    }
    if token.chars().any(is_posix_cntrl) {
        return Err(ModelArgError::new(
            "emitted argv token must not contain POSIX [[:cntrl:]] characters",
        ));
    }
    Ok(())
}

/// Scan a Claude transcript JSONL body for the first assistant `message.model`.
#[must_use]
pub fn claude_model_from_transcript(text: &str) -> String {
    for raw in text.split_inclusive('\n') {
        let line = raw.trim_end_matches(['\n', '\r']);
        if let Some(model) = assistant_model_from_line(line) {
            return model;
        }
    }
    "unknown".to_owned()
}

fn assistant_model_from_line(raw: &str) -> Option<String> {
    if !raw.contains("\"assistant\"") {
        return None;
    }
    let value: serde_json::Value = serde_json::from_str(raw).ok()?;
    let object = value.as_object()?;
    if object.get("type")?.as_str()? != "assistant" {
        return None;
    }
    let model = object.get("message")?.get("model")?.as_str()?;
    if model.is_empty() {
        None
    } else {
        Some(model.to_owned())
    }
}

/// Read `TRANSCRIPT_PATH` from a cached Claude source snapshot body.
#[must_use]
pub fn transcript_path_from_claude_source(text: &str) -> Option<String> {
    for line in text.split('\n') {
        let trimmed = line.trim_end_matches('\r');
        if let Some(value) = trimmed.strip_prefix("TRANSCRIPT_PATH=")
            && !value.is_empty()
        {
            return Some(value.to_owned());
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::{
        CODEX_DEFAULT_MODEL, CODEX_FIX_MODEL_DEFAULT, CODEX_REVIEW_MODEL_DEFAULT,
        CODEX_VOTE_MODEL_DEFAULT, CURSOR_DEFAULT_MODEL, CodexModelRole, ModelTool,
        claude_model_from_transcript, resolve_model_args, transcript_path_from_claude_source,
    };
    use crate::env;
    use std::collections::BTreeMap;

    fn env(pairs: &[(&str, &str)]) -> BTreeMap<String, String> {
        pairs
            .iter()
            .map(|(key, value)| ((*key).to_owned(), (*value).to_owned()))
            .collect()
    }

    #[test]
    fn cursor_uses_default_model_pin() {
        let result = resolve_model_args(
            ModelTool::Cursor,
            false,
            "",
            CodexModelRole::Default,
            &env(&[]),
        )
        .expect("resolve");
        assert_eq!(
            result.argv(),
            ["--model".to_owned(), CURSOR_DEFAULT_MODEL.to_owned()]
        );
    }

    #[test]
    fn cursor_prefers_env_then_plugin_then_default_argument() {
        let env_wins = resolve_model_args(
            ModelTool::Cursor,
            false,
            "arg-default",
            CodexModelRole::Default,
            &env(&[
                (env::LARCH_CURSOR_MODEL, "env-model"),
                (env::CLAUDE_PLUGIN_OPTION_CURSOR_MODEL, "plugin-model"),
            ]),
        )
        .expect("resolve");
        assert_eq!(env_wins.argv()[1], "env-model");

        let plugin = resolve_model_args(
            ModelTool::Cursor,
            false,
            "arg-default",
            CodexModelRole::Default,
            &env(&[(env::CLAUDE_PLUGIN_OPTION_CURSOR_MODEL, "plugin-model")]),
        )
        .expect("resolve");
        assert_eq!(plugin.argv()[1], "plugin-model");

        let arg = resolve_model_args(
            ModelTool::Cursor,
            false,
            "arg-default",
            CodexModelRole::Default,
            &env(&[]),
        )
        .expect("resolve");
        assert_eq!(arg.argv()[1], "arg-default");
    }

    #[test]
    fn codex_default_emits_effort_and_warns_on_invalid() {
        let ok = resolve_model_args(
            ModelTool::Codex,
            true,
            "",
            CodexModelRole::Default,
            &env(&[]),
        )
        .expect("resolve");
        assert_eq!(ok.argv()[0], "-m");
        assert_eq!(ok.argv()[1], CODEX_DEFAULT_MODEL);
        assert_eq!(ok.argv()[2], "-c");
        assert_eq!(ok.argv()[3], "model_reasoning_effort=\"high\"");
        assert!(ok.warning().is_empty());

        let warned = resolve_model_args(
            ModelTool::Codex,
            true,
            "",
            CodexModelRole::Default,
            &env(&[(env::LARCH_CODEX_EFFORT, "nope")]),
        )
        .expect("resolve");
        assert!(warned.warning().contains("WARN invalid codex effort"));
        assert_eq!(warned.argv()[3], "model_reasoning_effort=\"high\"");
    }

    #[test]
    fn codex_roles_use_role_defaults_and_env() {
        for (role, default, env_name) in [
            (
                CodexModelRole::Review,
                CODEX_REVIEW_MODEL_DEFAULT,
                env::LARCH_CODEX_REVIEW_MODEL,
            ),
            (
                CodexModelRole::Vote,
                CODEX_VOTE_MODEL_DEFAULT,
                env::LARCH_CODEX_VOTE_MODEL,
            ),
            (
                CodexModelRole::Fix,
                CODEX_FIX_MODEL_DEFAULT,
                env::LARCH_CODEX_FIX_MODEL,
            ),
        ] {
            let pinned =
                resolve_model_args(ModelTool::Codex, false, "", role, &env(&[])).expect("resolve");
            assert_eq!(pinned.argv()[1], default);

            let overridden = resolve_model_args(
                ModelTool::Codex,
                false,
                "",
                role,
                &env(&[(env_name, "role-env")]),
            )
            .expect("resolve");
            assert_eq!(overridden.argv()[1], "role-env");
        }
    }

    #[test]
    fn rejects_blank_and_control_characters() {
        let blank = resolve_model_args(
            ModelTool::Cursor,
            false,
            "   ",
            CodexModelRole::Default,
            &env(&[]),
        );
        assert!(blank.expect_err("blank").as_str().contains("blank"));

        let control = resolve_model_args(
            ModelTool::Cursor,
            false,
            "",
            CodexModelRole::Default,
            &env(&[(env::LARCH_CURSOR_MODEL, "bad\nmodel")]),
        );
        assert!(
            control
                .expect_err("control")
                .as_str()
                .contains("[[:cntrl:]]")
        );
    }

    #[test]
    fn transcript_helpers_match_python_contracts() {
        assert_eq!(
            transcript_path_from_claude_source("TRANSCRIPT_PATH=/tmp/a.jsonl\nSESSION_UUID=x\n")
                .as_deref(),
            Some("/tmp/a.jsonl")
        );
        let body = concat!(
            "{\"type\":\"user\"}\n",
            "{\"type\":\"assistant\",\"message\":{\"model\":\"claude-opus-4\"}}\n",
        );
        assert_eq!(claude_model_from_transcript(body), "claude-opus-4");
        assert_eq!(claude_model_from_transcript(""), "unknown");
    }
}
