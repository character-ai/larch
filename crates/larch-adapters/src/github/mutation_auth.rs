//! Live-mutation authorization gate for issue-dependency mutations.
//!
//! This ports the Python `check_live_mutation_auth` boundary: operator mode
//! bypasses context-file validation, a test denial overrides session-inherited
//! authorization but not operator mode, and a session-backed call requires a
//! regular, non-symlink context file that sits directly under a canonical larch
//! session root and carries `LARCH_LIVE_MUTATION_OK=true` with a matching run id.

use std::{
    env, fs,
    path::{Path, PathBuf},
};

use larch_core::{KvDocument, ParseOptions};

const AUTH_KEY: &str = "LARCH_LIVE_MUTATION_OK";
const RUN_ID_KEY: &str = "LARCH_RUN_ID";
const REFUSAL_REASON: &str = "unauthorized-mutation";
const TEST_DENIED_REASON: &str = "test-denied";
const OPERATOR_REASON: &str = "operator";
const SESSION_REASON: &str = "session";
const MAX_RUN_ID: usize = 128;

/// Authorized live-mutation route.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LiveMutationMode {
    Operator,
    Session,
}

/// Outcome of the live-mutation authorization gate.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LiveMutationDecision {
    /// Authorization succeeded through the named route.
    Authorized(LiveMutationMode),
    /// Authorization was refused with a stable reason.
    Refused(&'static str),
}

impl LiveMutationDecision {
    /// Whether the gate authorized the mutation.
    #[must_use]
    pub const fn is_authorized(self) -> bool {
        matches!(self, Self::Authorized(_))
    }

    /// Stable reason string preserved from the Python contract.
    #[must_use]
    pub const fn reason(self) -> &'static str {
        match self {
            Self::Authorized(LiveMutationMode::Operator) => OPERATOR_REASON,
            Self::Authorized(LiveMutationMode::Session) => SESSION_REASON,
            Self::Refused(reason) => reason,
        }
    }
}

/// Inputs to the live-mutation authorization gate.
pub struct LiveMutationRequest<'a> {
    /// Session context file that must carry the authorization key and run id.
    pub context_file: Option<&'a Path>,
    /// Direct operator invocation bypasses context-file validation.
    pub operator_mode: bool,
    /// Run identifier that must match the context file's run id.
    pub run_id: &'a str,
    /// Trusted canonical session root the context file must sit directly under.
    pub trusted_root: Option<&'a Path>,
    /// Test-only denial that overrides session-inherited authorization.
    pub test_deny: bool,
}

/// Authorize a live GitHub mutation.
#[must_use]
pub fn check_live_mutation_auth(request: &LiveMutationRequest<'_>) -> LiveMutationDecision {
    if request.operator_mode {
        return LiveMutationDecision::Authorized(LiveMutationMode::Operator);
    }
    if request.test_deny {
        return LiveMutationDecision::Refused(TEST_DENIED_REASON);
    }
    if authorize_session(request) {
        LiveMutationDecision::Authorized(LiveMutationMode::Session)
    } else {
        LiveMutationDecision::Refused(REFUSAL_REASON)
    }
}

fn authorize_session(request: &LiveMutationRequest<'_>) -> bool {
    let (Some(context), Some(root)) = (request.context_file, request.trusted_root) else {
        return false;
    };
    if !is_regular_file(context)
        || !is_canonical_mutation_session_root(root)
        || !context_parent_is_root(context, root)
    {
        return false;
    }
    let Some((auth_value, context_run_id)) = read_context(context) else {
        return false;
    };
    auth_value == "true" && is_safe_run_id(&context_run_id) && request.run_id == context_run_id
}

fn is_regular_file(path: &Path) -> bool {
    fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_file())
}

fn context_parent_is_root(context: &Path, root: &Path) -> bool {
    let Some(parent) = context.parent() else {
        return false;
    };
    match (parent.canonicalize(), root.canonicalize()) {
        (Ok(parent), Ok(root)) => parent == root,
        _ => false,
    }
}

fn is_canonical_mutation_session_root(root: &Path) -> bool {
    let Ok(resolved) = root.canonicalize() else {
        return false;
    };
    if !resolved.is_dir() {
        return false;
    }
    let Some(name) = resolved.file_name().and_then(|name| name.to_str()) else {
        return false;
    };
    is_session_dir_name(name)
        && allowlisted_roots()
            .iter()
            .any(|allowed| is_strictly_under(&resolved, allowed))
}

fn allowlisted_roots() -> Vec<PathBuf> {
    let mut roots = Vec::new();
    if let Some(home) = env::var_os("HOME") {
        roots.push(PathBuf::from(home).join(".cache/larch/sessions"));
    }
    roots.push(env::temp_dir());
    roots.push(PathBuf::from("/private/tmp"));
    roots.push(PathBuf::from("/var/folders"));
    roots.push(PathBuf::from("/private/var/folders"));
    roots
        .into_iter()
        .filter_map(|root| root.canonicalize().ok())
        .collect()
}

fn is_strictly_under(path: &Path, root: &Path) -> bool {
    path != root && path.starts_with(root)
}

fn is_session_dir_name(name: &str) -> bool {
    let suffix = name
        .strip_prefix("claude-design-")
        .or_else(|| name.strip_prefix("claude-implement-"));
    suffix.is_some_and(|rest| !rest.is_empty() && rest.bytes().all(is_identifier_byte))
}

fn is_safe_run_id(run_id: &str) -> bool {
    (1..=MAX_RUN_ID).contains(&run_id.len()) && run_id.bytes().all(is_identifier_byte)
}

const fn is_identifier_byte(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'.' | b'_')
}

fn read_context(path: &Path) -> Option<(String, String)> {
    let contents = fs::read_to_string(path).ok()?;
    let document = KvDocument::parse(&contents, ParseOptions::legacy()).ok()?;
    let mut auth_value = String::new();
    let mut run_id = String::new();
    for row in document.rows() {
        let key = row.key().trim();
        let key = key.strip_prefix("export ").map_or(key, str::trim_start);
        let value = row.value().trim().trim_matches(|c| c == '\'' || c == '"');
        match key {
            AUTH_KEY => value.clone_into(&mut auth_value),
            RUN_ID_KEY => value.clone_into(&mut run_id),
            _ => {}
        }
    }
    Some((auth_value, run_id))
}

#[cfg(test)]
mod tests {
    use super::{
        LiveMutationDecision, LiveMutationMode, LiveMutationRequest, check_live_mutation_auth,
    };
    use larch_test_support::TestWorkspace;
    use std::path::{Path, PathBuf};

    fn session(workspace: &TestWorkspace, contents: &str) -> (PathBuf, PathBuf) {
        let root = workspace
            .create_dir("claude-implement-run1")
            .expect("session root");
        let context = workspace
            .write("claude-implement-run1/source-env.sh", contents)
            .expect("context file");
        (root, context)
    }

    fn request<'a>(
        context: Option<&'a Path>,
        root: Option<&'a Path>,
        run_id: &'a str,
    ) -> LiveMutationRequest<'a> {
        LiveMutationRequest {
            context_file: context,
            operator_mode: false,
            run_id,
            trusted_root: root,
            test_deny: false,
        }
    }

    #[test]
    fn operator_mode_authorizes_and_ignores_test_deny() {
        let decision = check_live_mutation_auth(&LiveMutationRequest {
            context_file: None,
            operator_mode: true,
            run_id: "",
            trusted_root: None,
            test_deny: true,
        });
        assert_eq!(
            decision,
            LiveMutationDecision::Authorized(LiveMutationMode::Operator)
        );
        assert_eq!(decision.reason(), "operator");
        assert!(decision.is_authorized());
    }

    #[test]
    fn test_deny_overrides_session_inherited_authorization() {
        let workspace = TestWorkspace::new().expect("workspace");
        let (root, context) = session(
            &workspace,
            "LARCH_LIVE_MUTATION_OK=true\nLARCH_RUN_ID=run1\n",
        );
        let mut input = request(Some(&context), Some(&root), "run1");
        input.test_deny = true;
        let decision = check_live_mutation_auth(&input);
        assert_eq!(decision, LiveMutationDecision::Refused("test-denied"));
    }

    #[test]
    fn session_backed_call_authorizes_with_matching_identity() {
        let workspace = TestWorkspace::new().expect("workspace");
        let (root, context) = session(
            &workspace,
            "export LARCH_LIVE_MUTATION_OK='true'\nLARCH_RUN_ID=\"run1\"\n",
        );
        let decision = check_live_mutation_auth(&request(Some(&context), Some(&root), "run1"));
        assert_eq!(
            decision,
            LiveMutationDecision::Authorized(LiveMutationMode::Session)
        );
        assert_eq!(decision.reason(), "session");
    }

    #[test]
    fn refuses_missing_context_and_wrong_authorization_value() {
        let workspace = TestWorkspace::new().expect("workspace");
        assert_eq!(
            check_live_mutation_auth(&request(None, None, "run1")),
            LiveMutationDecision::Refused("unauthorized-mutation")
        );
        let (root, context) = session(
            &workspace,
            "LARCH_LIVE_MUTATION_OK=false\nLARCH_RUN_ID=run1\n",
        );
        assert!(
            !check_live_mutation_auth(&request(Some(&context), Some(&root), "run1"))
                .is_authorized()
        );
    }

    #[test]
    fn refuses_run_id_mismatch_and_unsafe_run_id() {
        let workspace = TestWorkspace::new().expect("workspace");
        let (root, context) = session(
            &workspace,
            "LARCH_LIVE_MUTATION_OK=true\nLARCH_RUN_ID=run1\n",
        );
        assert!(
            !check_live_mutation_auth(&request(Some(&context), Some(&root), "run2"))
                .is_authorized()
        );

        let unsafe_workspace = TestWorkspace::new().expect("workspace");
        let unsafe_root = unsafe_workspace
            .create_dir("claude-implement-run1")
            .expect("root");
        let unsafe_context = unsafe_workspace
            .write(
                "claude-implement-run1/source-env.sh",
                "LARCH_LIVE_MUTATION_OK=true\nLARCH_RUN_ID=bad id\n",
            )
            .expect("context");
        assert!(
            !check_live_mutation_auth(&request(
                Some(&unsafe_context),
                Some(&unsafe_root),
                "bad id"
            ))
            .is_authorized()
        );
    }

    #[test]
    fn refuses_non_canonical_root_and_indirect_context() {
        let workspace = TestWorkspace::new().expect("workspace");
        let wrong = workspace.create_dir("not-a-session").expect("wrong root");
        let context = workspace
            .write(
                "not-a-session/source-env.sh",
                "LARCH_LIVE_MUTATION_OK=true\nLARCH_RUN_ID=run1\n",
            )
            .expect("context");
        assert!(
            !check_live_mutation_auth(&request(Some(&context), Some(&wrong), "run1"))
                .is_authorized()
        );

        let (root, _) = session(
            &workspace,
            "LARCH_LIVE_MUTATION_OK=true\nLARCH_RUN_ID=run1\n",
        );
        let nested = workspace
            .write(
                "claude-implement-run1/nested/source-env.sh",
                "LARCH_LIVE_MUTATION_OK=true\nLARCH_RUN_ID=run1\n",
            )
            .expect("nested context");
        assert!(
            !check_live_mutation_auth(&request(Some(&nested), Some(&root), "run1")).is_authorized()
        );
    }

    #[cfg(unix)]
    #[test]
    fn refuses_symlinked_context_file() {
        use std::os::unix::fs::symlink;

        let workspace = TestWorkspace::new().expect("workspace");
        let root = workspace.create_dir("claude-implement-run1").expect("root");
        let target = workspace
            .write(
                "target-env.sh",
                "LARCH_LIVE_MUTATION_OK=true\nLARCH_RUN_ID=run1\n",
            )
            .expect("target");
        let link = root.join("source-env.sh");
        symlink(&target, &link).expect("symlink");
        assert!(
            !check_live_mutation_auth(&request(Some(&link), Some(&root), "run1")).is_authorized()
        );
    }
}
