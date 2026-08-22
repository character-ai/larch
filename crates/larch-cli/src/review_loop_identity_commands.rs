//! Rust composition owner for the implement Step 5 loop-identity commands.
//!
//! Process capture, polling, validated group termination, and kill-log bytes
//! remain in `larch-core`; this module preserves the retired `argparse` command
//! line and rejects unsafe temp-directory leaves before invoking that owner.

use std::{ffi::OsString, fs, path::Path, process::ExitCode};

use larch_adapters::SystemProcessIdentityHost;
use larch_core::{
    await_step5_loop_identity, teardown_step5_loop_identity, write_step5_loop_identity,
};

use crate::argparse_compat::parse_required_with_help;

const WRITE_PROGRAM: &str = "cli.py review-and-fix write-loop-identity";
const WRITE_USAGE: &str = concat!(
    "usage: cli.py review-and-fix write-loop-identity [-h] --implement-tmpdir\n",
    "                                                 IMPLEMENT_TMPDIR --pid PID\n",
    "                                                 [--expected-signature EXPECTED_SIGNATURE]",
);
const WRITE_HELP: &str = concat!(
    "usage: cli.py review-and-fix write-loop-identity [-h] --implement-tmpdir\n",
    "                                                 IMPLEMENT_TMPDIR --pid PID\n",
    "                                                 [--expected-signature EXPECTED_SIGNATURE]\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --implement-tmpdir IMPLEMENT_TMPDIR\n",
    "  --pid PID\n",
    "  --expected-signature EXPECTED_SIGNATURE",
);
const AWAIT_PROGRAM: &str = "cli.py review-and-fix await-loop-identity";
const AWAIT_USAGE: &str = concat!(
    "usage: cli.py review-and-fix await-loop-identity [-h] --implement-tmpdir\n",
    "                                                 IMPLEMENT_TMPDIR --pid PID\n",
    "                                                 [--timeout-s TIMEOUT_S]\n",
    "                                                 [--reattach]",
);
const AWAIT_HELP: &str = concat!(
    "usage: cli.py review-and-fix await-loop-identity [-h] --implement-tmpdir\n",
    "                                                 IMPLEMENT_TMPDIR --pid PID\n",
    "                                                 [--timeout-s TIMEOUT_S]\n",
    "                                                 [--reattach]\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --implement-tmpdir IMPLEMENT_TMPDIR\n",
    "  --pid PID\n",
    "  --timeout-s TIMEOUT_S\n",
    "  --reattach",
);
const TEARDOWN_PROGRAM: &str = "cli.py review-and-fix teardown-loop-identity";
const TEARDOWN_USAGE: &str = concat!(
    "usage: cli.py review-and-fix teardown-loop-identity [-h] --implement-tmpdir\n",
    "                                                    IMPLEMENT_TMPDIR --pid PID",
);
const TEARDOWN_HELP: &str = concat!(
    "usage: cli.py review-and-fix teardown-loop-identity [-h] --implement-tmpdir\n",
    "                                                    IMPLEMENT_TMPDIR --pid PID\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --implement-tmpdir IMPLEMENT_TMPDIR\n",
    "  --pid PID",
);

fn exit_code(code: i32) -> ExitCode {
    ExitCode::from(u8::try_from(code).unwrap_or(1))
}

fn validated_implement_tmpdir(raw: &str) -> Option<&str> {
    let path = Path::new(raw);
    if !path.is_absolute() {
        return None;
    }
    let metadata = fs::symlink_metadata(path).ok()?;
    (metadata.file_type().is_dir() && !metadata.file_type().is_symlink()).then_some(raw)
}

/// Capture and persist one Step 5 process identity.
pub fn write(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        WRITE_PROGRAM,
        WRITE_USAGE,
        WRITE_HELP,
        &["--implement-tmpdir", "--pid", "--expected-signature"],
        &[],
        &["--implement-tmpdir", "--pid"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tmpdir = parsed
        .value("--implement-tmpdir")
        .unwrap_or_default()
        .to_string_lossy();
    let Some(tmpdir) = validated_implement_tmpdir(&tmpdir) else {
        return ExitCode::SUCCESS;
    };
    let pid = parsed.value("--pid").unwrap_or_default().to_string_lossy();
    let signature = parsed.value("--expected-signature").map_or_else(
        || "review-and-fix step5".into(),
        |value| value.to_string_lossy(),
    );
    exit_code(write_step5_loop_identity(
        &SystemProcessIdentityHost::new(),
        tmpdir,
        &pid,
        &signature,
    ))
}

/// Wait until the persisted Step 5 process exits or its timeout elapses.
pub fn await_identity(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        AWAIT_PROGRAM,
        AWAIT_USAGE,
        AWAIT_HELP,
        &["--implement-tmpdir", "--pid", "--timeout-s"],
        &["--reattach"],
        &["--implement-tmpdir", "--pid"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tmpdir = parsed
        .value("--implement-tmpdir")
        .unwrap_or_default()
        .to_string_lossy();
    let Some(tmpdir) = validated_implement_tmpdir(&tmpdir) else {
        return ExitCode::FAILURE;
    };
    let pid = parsed.value("--pid").unwrap_or_default().to_string_lossy();
    let timeout = parsed
        .value("--timeout-s")
        .map_or_else(|| "21600".into(), |value| value.to_string_lossy());
    exit_code(await_step5_loop_identity(
        &SystemProcessIdentityHost::new(),
        tmpdir,
        &pid,
        &timeout,
        parsed.flag("--reattach"),
    ))
}

/// Terminate a still-matching Step 5 process group and persist the kill log.
pub fn teardown(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        TEARDOWN_PROGRAM,
        TEARDOWN_USAGE,
        TEARDOWN_HELP,
        &["--implement-tmpdir", "--pid"],
        &[],
        &["--implement-tmpdir", "--pid"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tmpdir = parsed
        .value("--implement-tmpdir")
        .unwrap_or_default()
        .to_string_lossy();
    let Some(tmpdir) = validated_implement_tmpdir(&tmpdir) else {
        return ExitCode::SUCCESS;
    };
    let pid = parsed.value("--pid").unwrap_or_default().to_string_lossy();
    exit_code(teardown_step5_loop_identity(
        &SystemProcessIdentityHost::new(),
        tmpdir,
        &pid,
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn tmpdir_validation_matches_the_retired_python_leaf_rules() {
        let temporary = tempdir().expect("temporary directory");
        let path = temporary.path().to_string_lossy();
        assert_eq!(validated_implement_tmpdir(&path), Some(path.as_ref()));
        assert!(validated_implement_tmpdir("relative").is_none());

        #[cfg(unix)]
        {
            let link = temporary.path().with_extension("link");
            std::os::unix::fs::symlink(temporary.path(), &link).expect("directory symlink");
            assert!(validated_implement_tmpdir(&link.to_string_lossy()).is_none());
            fs::remove_file(link).expect("remove test symlink");
        }
    }
}
