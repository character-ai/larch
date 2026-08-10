//! Typed Git CLI operation requests and fixed argv builders.

#![allow(clippy::unnecessary_wraps)] // GitOperation::arguments is Result for fallible builders
#![allow(clippy::struct_excessive_bools)] // ExactDiffRequest mirrors the Git flag surface

use std::ffi::OsString;

use larch_core::GitCliOperation;

use super::{
    GitCliInputError, GitCliInputErrorKind, GitConfigKey, GitFilePath, GitPath, GitRef, GitRefspec,
    GitRemote, GitToken, GitUrl,
};

pub(super) trait GitOperation {
    fn operation(&self) -> GitCliOperation;
    fn arguments(&self) -> Result<Vec<OsString>, GitCliInputError>;
    fn stdin(&self) -> Vec<u8> {
        Vec::new()
    }
}

fn err(kind: GitCliInputErrorKind, message: &str) -> GitCliInputError {
    GitCliInputError::new(kind, message)
}

fn reject_value(value: &OsString) -> Result<(), GitCliInputError> {
    if value.is_empty() {
        return Err(err(GitCliInputErrorKind::Empty, "value must not be empty"));
    }
    if value.as_encoded_bytes().contains(&0) {
        return Err(err(
            GitCliInputErrorKind::NulByte,
            "value must not contain NUL",
        ));
    }
    Ok(())
}

fn push_paths(a: &mut Vec<OsString>, paths: &[GitPath]) -> Result<(), GitCliInputError> {
    if paths.is_empty() {
        return Err(err(
            GitCliInputErrorKind::Empty,
            "at least one path is required",
        ));
    }
    a.push("--".into());
    a.extend(paths.iter().map(|p| p.as_os_str().into()));
    Ok(())
}

macro_rules! git_op {
    ($ty:ty, $variant:ident) => {
        impl GitOperation for $ty {
            fn operation(&self) -> GitCliOperation {
                GitCliOperation::$variant
            }
            fn arguments(&self) -> Result<Vec<OsString>, GitCliInputError> {
                self.argv()
            }
        }
    };
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct VersionRequest;
impl VersionRequest {
    #[allow(
        clippy::unused_self,
        clippy::missing_const_for_fn,
        clippy::trivially_copy_pass_by_ref
    )] // GitOperation keeps &self for every operation
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        Ok(Vec::new())
    }
}
git_op!(VersionRequest, Version);

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExactDiffRequest {
    pub cached: bool,
    /// Fixed unified-context width for callers that need patch text.
    pub unified_context: Option<u16>,
    pub name_only: bool,
    pub name_status: bool,
    pub quiet: bool,
    pub exit_code: bool,
    pub base: Option<GitRef>,
    pub head: Option<GitRef>,
    pub paths: Vec<GitPath>,
}
impl ExactDiffRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        if self.name_only && self.name_status {
            return Err(err(
                GitCliInputErrorKind::UnsupportedCombination,
                "diff cannot request both --name-only and --name-status",
            ));
        }
        let mut a = Vec::new();
        if self.cached {
            a.push("--cached".into());
        }
        if let Some(context) = self.unified_context {
            a.push(format!("-U{context}").into());
        }
        if self.name_only {
            a.push("--name-only".into());
        }
        if self.name_status {
            a.push("--name-status".into());
        }
        if self.quiet {
            a.push("--quiet".into());
        }
        if self.exit_code {
            a.push("--exit-code".into());
        }
        if let Some(v) = &self.base {
            a.push(v.as_os_str().into());
        }
        if let Some(v) = &self.head {
            a.push(v.as_os_str().into());
        }
        if !self.paths.is_empty() {
            a.push("--".into());
            a.extend(self.paths.iter().map(|p| p.as_os_str().into()));
        }
        Ok(a)
    }
}
git_op!(ExactDiffRequest, ExactDiff);

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ConfigMutationRequest {
    Set { key: GitConfigKey, value: OsString },
    Unset { key: GitConfigKey },
    Add { key: GitConfigKey, value: OsString },
}
impl ConfigMutationRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        let mut a = vec!["--local".into()];
        match self {
            Self::Set { key, value } => {
                reject_value(value)?;
                a.push(key.as_os_str().into());
                a.push(value.clone());
            }
            Self::Unset { key } => {
                a.push("--unset".into());
                a.push(key.as_os_str().into());
            }
            Self::Add { key, value } => {
                reject_value(value)?;
                a.push("--add".into());
                a.push(key.as_os_str().into());
                a.push(value.clone());
            }
        }
        Ok(a)
    }
}
git_op!(ConfigMutationRequest, ConfigMutation);

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RemoteMutationRequest {
    Add { name: GitRemote, url: GitUrl },
    Remove { name: GitRemote },
    SetUrl { name: GitRemote, url: GitUrl },
    Rename { from: GitRemote, to: GitRemote },
}
impl RemoteMutationRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        Ok(match self {
            Self::Add { name, url } => vec![
                "add".into(),
                name.as_os_str().into(),
                url.as_os_str().into(),
            ],
            Self::Remove { name } => vec!["remove".into(), name.as_os_str().into()],
            Self::SetUrl { name, url } => vec![
                "set-url".into(),
                name.as_os_str().into(),
                url.as_os_str().into(),
            ],
            Self::Rename { from, to } => vec![
                "rename".into(),
                from.as_os_str().into(),
                to.as_os_str().into(),
            ],
        })
    }
}
git_op!(RemoteMutationRequest, RemoteMutation);

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AddRequest {
    pub all: bool,
    pub force: bool,
    pub pathspec_from_file: Option<GitFilePath>,
    pub pathspec_file_nul: bool,
    pub paths: Vec<GitPath>,
}
impl AddRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        let mut a = Vec::new();
        if self.all {
            a.push("--all".into());
        }
        if self.force {
            a.push("--force".into());
        }
        if let Some(path) = &self.pathspec_from_file {
            if !self.paths.is_empty() {
                return Err(err(
                    GitCliInputErrorKind::UnsupportedCombination,
                    "pathspec-from-file cannot combine with path arguments",
                ));
            }
            let mut flag = OsString::from("--pathspec-from-file=");
            flag.push(path.as_os_str());
            a.push(flag);
            if self.pathspec_file_nul {
                a.push("--pathspec-file-nul".into());
            }
            return Ok(a);
        }
        if self.pathspec_file_nul {
            return Err(err(
                GitCliInputErrorKind::UnsupportedCombination,
                "--pathspec-file-nul requires --pathspec-from-file",
            ));
        }
        if self.all {
            if !self.paths.is_empty() {
                return Err(err(
                    GitCliInputErrorKind::UnsupportedCombination,
                    "--all cannot combine with path arguments",
                ));
            }
            return Ok(a);
        }
        push_paths(&mut a, &self.paths)?;
        Ok(a)
    }
}
git_op!(AddRequest, Add);

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RmRequest {
    pub force: bool,
    pub paths: Vec<GitPath>,
}
impl RmRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        let mut a = Vec::new();
        if self.force {
            a.push("--force".into());
        }
        push_paths(&mut a, &self.paths)?;
        Ok(a)
    }
}
git_op!(RmRequest, Rm);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ResetMode {
    Soft,
    Mixed,
    Hard,
}
impl ResetMode {
    const fn flag(self) -> &'static str {
        match self {
            Self::Soft => "--soft",
            Self::Mixed => "--mixed",
            Self::Hard => "--hard",
        }
    }
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ResetRequest {
    pub mode: ResetMode,
    pub target: GitRef,
    pub paths: Vec<GitPath>,
}
impl ResetRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        let mut a = vec![self.mode.flag().into(), self.target.as_os_str().into()];
        if !self.paths.is_empty() {
            if self.mode != ResetMode::Mixed {
                return Err(err(
                    GitCliInputErrorKind::UnsupportedCombination,
                    "path-limited reset requires --mixed",
                ));
            }
            a.push("--".into());
            a.extend(self.paths.iter().map(|p| p.as_os_str().into()));
        }
        Ok(a)
    }
}
git_op!(ResetRequest, Reset);

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RestoreRequest {
    pub staged: bool,
    pub paths: Vec<GitPath>,
}
impl RestoreRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        let mut a = Vec::new();
        if self.staged {
            a.push("--staged".into());
        }
        push_paths(&mut a, &self.paths)?;
        Ok(a)
    }
}
git_op!(RestoreRequest, Restore);

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum CheckoutRequest {
    Paths {
        ours: bool,
        theirs: bool,
        paths: Vec<GitPath>,
    },
    Branch {
        create: bool,
        force: bool,
        no_track: bool,
        name: GitRef,
        start_point: Option<GitRef>,
    },
    Detach {
        target: GitRef,
    },
}
impl CheckoutRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        match self {
            Self::Paths {
                ours,
                theirs,
                paths,
            } => {
                if *ours && *theirs {
                    return Err(err(
                        GitCliInputErrorKind::UnsupportedCombination,
                        "checkout cannot request both --ours and --theirs",
                    ));
                }
                let mut a = Vec::new();
                if *ours {
                    a.push("--ours".into());
                }
                if *theirs {
                    a.push("--theirs".into());
                }
                push_paths(&mut a, paths)?;
                Ok(a)
            }
            Self::Branch {
                create,
                force,
                no_track,
                name,
                start_point,
            } => {
                let mut a = Vec::new();
                if *create {
                    a.push(OsString::from(if *force { "-B" } else { "-b" }));
                    if *no_track {
                        a.push("--no-track".into());
                    }
                } else if *no_track {
                    return Err(err(
                        GitCliInputErrorKind::UnsupportedCombination,
                        "checkout --no-track requires create (-b/-B)",
                    ));
                } else if *force {
                    return Err(err(
                        GitCliInputErrorKind::UnsupportedCombination,
                        "force branch checkout requires create",
                    ));
                } else if start_point.is_some() {
                    return Err(err(
                        GitCliInputErrorKind::UnsupportedCombination,
                        "checkout start_point requires create (-b/-B)",
                    ));
                }
                a.push(name.as_os_str().into());
                if let Some(start) = start_point {
                    a.push(start.as_os_str().into());
                }
                Ok(a)
            }
            Self::Detach { target } => Ok(vec!["--detach".into(), target.as_os_str().into()]),
        }
    }
}
git_op!(CheckoutRequest, Checkout);

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CleanRequest {
    pub directories: bool,
    pub force: bool,
}
impl CleanRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        if !self.force {
            return Err(err(
                GitCliInputErrorKind::UnsupportedCombination,
                "clean requires --force",
            ));
        }
        let mut a = vec!["--force".into()];
        if self.directories {
            a.push("-d".into());
        }
        Ok(a)
    }
}
git_op!(CleanRequest, Clean);

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ApplyRequest {
    pub patch: GitPath,
    pub index: bool,
    pub check: bool,
}
impl ApplyRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        let mut a = Vec::new();
        if self.index {
            a.push("--index".into());
        }
        if self.check {
            a.push("--check".into());
        }
        a.push(self.patch.as_os_str().into());
        Ok(a)
    }
}
git_op!(ApplyRequest, Apply);

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum CommitMessage {
    Literal(OsString),
    File(GitFilePath),
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CommitRequest {
    pub message: Option<CommitMessage>,
    pub amend: bool,
    pub no_edit: bool,
    pub allow_empty: bool,
    pub only: bool,
    pub pathspec_from_file: Option<GitFilePath>,
    pub pathspec_file_nul: bool,
    pub paths: Vec<GitPath>,
}
impl CommitRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        let mut a = Vec::new();
        if self.amend {
            a.push("--amend".into());
        }
        if self.allow_empty {
            a.push("--allow-empty".into());
        }
        if self.no_edit {
            a.push("--no-edit".into());
        }
        if self.only {
            a.push("--only".into());
        }
        match &self.message {
            Some(CommitMessage::Literal(message)) => {
                reject_value(message)?;
                a.push("-m".into());
                a.push(message.clone());
            }
            Some(CommitMessage::File(path)) => {
                a.push("--file".into());
                a.push(path.as_os_str().into());
            }
            None if self.no_edit && self.amend => {}
            None => {
                return Err(err(
                    GitCliInputErrorKind::UnsupportedCombination,
                    "commit requires a message unless amending with --no-edit",
                ));
            }
        }
        if let Some(path) = &self.pathspec_from_file {
            if !self.paths.is_empty() {
                return Err(err(
                    GitCliInputErrorKind::UnsupportedCombination,
                    "pathspec-from-file cannot combine with path arguments",
                ));
            }
            let mut flag = OsString::from("--pathspec-from-file=");
            flag.push(path.as_os_str());
            a.push(flag);
            if self.pathspec_file_nul {
                a.push("--pathspec-file-nul".into());
            }
        } else if self.pathspec_file_nul {
            return Err(err(
                GitCliInputErrorKind::UnsupportedCombination,
                "--pathspec-file-nul requires --pathspec-from-file",
            ));
        } else if !self.paths.is_empty() {
            a.push("--".into());
            a.extend(self.paths.iter().map(|p| p.as_os_str().into()));
        }
        Ok(a)
    }
}
git_op!(CommitRequest, Commit);

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct InterpretTrailersRequest {
    pub trailers: Vec<OsString>,
    pub in_place: Option<GitFilePath>,
    pub add_if_different: bool,
    pub add_if_missing: bool,
    /// Commit-message body fed on stdin when `in_place` is unset.
    pub stdin: Vec<u8>,
}
impl InterpretTrailersRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        if self.trailers.is_empty() {
            return Err(err(
                GitCliInputErrorKind::Empty,
                "at least one trailer is required",
            ));
        }
        if self.in_place.is_some() && !self.stdin.is_empty() {
            return Err(err(
                GitCliInputErrorKind::UnsupportedCombination,
                "interpret-trailers cannot combine --in-place with stdin",
            ));
        }
        let mut a = Vec::new();
        if self.add_if_different {
            a.extend(["--if-exists".into(), "addIfDifferent".into()]);
        }
        if self.add_if_missing {
            a.extend(["--if-missing".into(), "add".into()]);
        }
        for trailer in &self.trailers {
            reject_value(trailer)?;
            a.push("--trailer".into());
            a.push(trailer.clone());
        }
        if let Some(path) = &self.in_place {
            a.push("--in-place".into());
            a.push(path.as_os_str().into());
        }
        Ok(a)
    }
}
impl GitOperation for InterpretTrailersRequest {
    fn operation(&self) -> GitCliOperation {
        GitCliOperation::InterpretTrailers
    }
    fn arguments(&self) -> Result<Vec<OsString>, GitCliInputError> {
        self.argv()
    }
    fn stdin(&self) -> Vec<u8> {
        self.stdin.clone()
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum BranchMutationRequest {
    Create {
        force: bool,
        name: GitRef,
        start_point: Option<GitRef>,
    },
    Delete {
        force: bool,
        name: GitRef,
    },
    SetUpstream {
        name: GitRef,
        upstream: GitRef,
    },
}
impl BranchMutationRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        Ok(match self {
            Self::Create {
                force,
                name,
                start_point,
            } => {
                let mut a = Vec::new();
                if *force {
                    a.push("--force".into());
                }
                a.push(name.as_os_str().into());
                if let Some(start) = start_point {
                    a.push(start.as_os_str().into());
                }
                a
            }
            Self::Delete { force, name } => vec![
                OsString::from(if *force { "-D" } else { "-d" }),
                name.as_os_str().into(),
            ],
            Self::SetUpstream { name, upstream } => vec![
                "--set-upstream-to".into(),
                upstream.as_os_str().into(),
                name.as_os_str().into(),
            ],
        })
    }
}
git_op!(BranchMutationRequest, BranchMutation);

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum WorktreeRequest {
    Add {
        branch: Option<GitRef>,
        path: GitPath,
        start_point: Option<GitRef>,
    },
    Remove {
        force: bool,
        path: GitPath,
    },
}
impl WorktreeRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        Ok(match self {
            Self::Add {
                branch,
                path,
                start_point,
            } => {
                let mut a = vec!["add".into()];
                if let Some(branch) = branch {
                    a.push("-b".into());
                    a.push(branch.as_os_str().into());
                }
                a.push(path.as_os_str().into());
                if let Some(start) = start_point {
                    a.push(start.as_os_str().into());
                }
                a
            }
            Self::Remove { force, path } => {
                let mut a = vec!["remove".into()];
                if *force {
                    a.push("--force".into());
                }
                a.push(path.as_os_str().into());
                a
            }
        })
    }
}
git_op!(WorktreeRequest, Worktree);

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct InitRequest {
    pub directory: Option<GitPath>,
    pub initial_branch: Option<GitRef>,
}
impl InitRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        let mut a = Vec::new();
        if let Some(branch) = &self.initial_branch {
            a.push("--initial-branch".into());
            a.push(branch.as_os_str().into());
        }
        if let Some(directory) = &self.directory {
            a.push(directory.as_os_str().into());
        }
        Ok(a)
    }
}
git_op!(InitRequest, Init);

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CloneRequest {
    pub url: GitUrl,
    pub directory: Option<GitPath>,
}
impl CloneRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        let mut a = vec![self.url.as_os_str().into()];
        if let Some(directory) = &self.directory {
            a.push(directory.as_os_str().into());
        }
        Ok(a)
    }
}
git_op!(CloneRequest, Clone);

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum SparseCheckoutRequest {
    Init { cone: bool },
    Set { paths: Vec<GitPath> },
    Disable,
}
impl SparseCheckoutRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        Ok(match self {
            Self::Init { cone } => {
                let mut a = vec!["init".into()];
                if *cone {
                    a.push("--cone".into());
                }
                a
            }
            Self::Set { paths } => {
                if paths.is_empty() {
                    return Err(err(
                        GitCliInputErrorKind::Empty,
                        "sparse-checkout set requires paths",
                    ));
                }
                let mut a = vec!["set".into()];
                a.extend(paths.iter().map(|p| p.as_os_str().into()));
                a
            }
            Self::Disable => vec!["disable".into()],
        })
    }
}
git_op!(SparseCheckoutRequest, SparseCheckout);

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RebaseRequest {
    Start {
        onto: Option<GitRef>,
        upstream: GitRef,
        branch: Option<GitRef>,
    },
    Continue,
    Skip,
    Abort,
}
impl RebaseRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        Ok(match self {
            Self::Start {
                onto,
                upstream,
                branch,
            } => {
                let mut a = Vec::new();
                if let Some(onto) = onto {
                    a.push("--onto".into());
                    a.push(onto.as_os_str().into());
                }
                a.push(upstream.as_os_str().into());
                if let Some(branch) = branch {
                    a.push(branch.as_os_str().into());
                }
                a
            }
            Self::Continue => vec!["--continue".into()],
            Self::Skip => vec!["--skip".into()],
            Self::Abort => vec!["--abort".into()],
        })
    }
}
git_op!(RebaseRequest, Rebase);

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum MergeRequest {
    Commit { theirs: GitRef, no_edit: bool },
    Abort,
}
impl MergeRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        Ok(match self {
            Self::Commit { theirs, no_edit } => {
                let mut a = Vec::new();
                if *no_edit {
                    a.push("--no-edit".into());
                }
                a.push(theirs.as_os_str().into());
                a
            }
            Self::Abort => vec!["--abort".into()],
        })
    }
}
git_op!(MergeRequest, Merge);

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PullRequest {
    pub remote: GitRemote,
    pub refspec: Option<GitRefspec>,
    /// Refuse a merge commit while synchronizing a checked-out branch.
    pub fast_forward_only: bool,
}
impl PullRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        let mut a = Vec::new();
        if self.fast_forward_only {
            a.push("--ff-only".into());
        }
        a.push(self.remote.as_os_str().into());
        if let Some(refspec) = &self.refspec {
            a.push(refspec.as_os_str().into());
        }
        Ok(a)
    }
}
git_op!(PullRequest, Pull);

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum StashRequest {
    Push { message: Option<OsString> },
    Pop,
    Drop,
}
impl StashRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        Ok(match self {
            Self::Push { message } => {
                let mut a = vec!["push".into()];
                if let Some(message) = message {
                    reject_value(message)?;
                    a.push("-m".into());
                    a.push(message.clone());
                }
                a
            }
            Self::Pop => vec!["pop".into()],
            Self::Drop => vec!["drop".into()],
        })
    }
}
git_op!(StashRequest, Stash);

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FetchRequest {
    pub remote: GitRemote,
    pub refspec: Option<GitRefspec>,
    pub quiet: bool,
    /// Skip the tag auto-follow a bounded single-object fetch does not want.
    pub no_tags: bool,
}
impl FetchRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        let mut a = Vec::new();
        if self.no_tags {
            a.push("--no-tags".into());
        }
        if self.quiet {
            a.push("--quiet".into());
        }
        a.push(self.remote.as_os_str().into());
        if let Some(refspec) = &self.refspec {
            a.push(refspec.as_os_str().into());
        }
        Ok(a)
    }
}
git_op!(FetchRequest, Fetch);

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ForceWithLease {
    Enabled,
    /// Require the remote reference to retain this exact object ID.
    Expecting {
        reference: GitRef,
        oid: GitRef,
    },
    /// Require the remote reference to be absent (empty `<expect>` after the colon).
    ExpectingAbsent {
        reference: GitRef,
    },
}
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PushRequest {
    pub remote: GitRemote,
    pub refspec: GitRefspec,
    pub force_with_lease: Option<ForceWithLease>,
    /// Set the upstream to the explicit destination after a successful push.
    pub set_upstream: bool,
}
impl PushRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        let mut a = Vec::new();
        if self.set_upstream {
            a.push("--set-upstream".into());
        }
        match &self.force_with_lease {
            Some(ForceWithLease::Enabled) => a.push("--force-with-lease".into()),
            Some(ForceWithLease::Expecting { reference, oid }) => {
                let mut flag = OsString::from("--force-with-lease=");
                flag.push(reference.as_os_str());
                flag.push(":");
                flag.push(oid.as_os_str());
                a.push(flag);
            }
            Some(ForceWithLease::ExpectingAbsent { reference }) => {
                let mut flag = OsString::from("--force-with-lease=");
                flag.push(reference.as_os_str());
                flag.push(":");
                a.push(flag);
            }
            None => {}
        }
        a.push(self.remote.as_os_str().into());
        a.push(self.refspec.as_os_str().into());
        Ok(a)
    }
}
git_op!(PushRequest, Push);

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LsRemoteRequest {
    pub remote: GitRemote,
    pub patterns: Vec<GitRef>,
    /// Restrict results to `refs/heads/*` (`--heads`).
    pub heads: bool,
    /// Exit 2 when no matching refs are found (`--exit-code`).
    pub exit_code: bool,
}
impl LsRemoteRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        let mut a = Vec::new();
        if self.exit_code {
            a.push("--exit-code".into());
        }
        if self.heads {
            a.push("--heads".into());
        }
        a.push(self.remote.as_os_str().into());
        a.extend(self.patterns.iter().map(|p| p.as_os_str().into()));
        Ok(a)
    }
}
git_op!(LsRemoteRequest, LsRemote);

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum TagMutationRequest {
    Create {
        force: bool,
        name: GitRef,
        target: Option<GitRef>,
        message: Option<OsString>,
    },
    Delete {
        name: GitRef,
    },
}
impl TagMutationRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        Ok(match self {
            Self::Create {
                force,
                name,
                target,
                message,
            } => {
                let mut a = Vec::new();
                if *force {
                    a.push("--force".into());
                }
                if let Some(message) = message {
                    reject_value(message)?;
                    a.push("-m".into());
                    a.push(message.clone());
                }
                a.push(name.as_os_str().into());
                if let Some(target) = target {
                    a.push(target.as_os_str().into());
                }
                a
            }
            Self::Delete { name } => vec!["--delete".into(), name.as_os_str().into()],
        })
    }
}
git_op!(TagMutationRequest, TagMutation);

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum SubmoduleRequest {
    Update {
        init: bool,
        recursive: bool,
    },
    Foreach {
        recursive: bool,
        command: Vec<GitToken>,
    },
}
impl SubmoduleRequest {
    fn argv(&self) -> Result<Vec<OsString>, GitCliInputError> {
        Ok(match self {
            Self::Update { init, recursive } => {
                let mut a = vec!["update".into()];
                if *init {
                    a.push("--init".into());
                }
                if *recursive {
                    a.push("--recursive".into());
                }
                a
            }
            Self::Foreach { recursive, command } => {
                if command.is_empty() {
                    return Err(err(
                        GitCliInputErrorKind::Empty,
                        "submodule foreach requires a command",
                    ));
                }
                let mut a = vec!["foreach".into()];
                if *recursive {
                    a.push("--recursive".into());
                }
                a.extend(command.iter().map(|t| t.as_os_str().into()));
                a
            }
        })
    }
}
git_op!(SubmoduleRequest, SubmoduleUpdate);
