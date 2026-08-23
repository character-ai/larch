//! Rust composition owner for the design Step 3 and implement Step 5
//! loop-identity commands.
//!
//! Process capture, polling, validated group termination, and kill-log bytes
//! remain in `larch-core`; this module preserves the retired `argparse` command
//! line and rejects unsafe temp-directory leaves before invoking that owner.

use std::{ffi::OsString, fs, path::Path, process::ExitCode};

use larch_adapters::SystemProcessIdentityHost;
use larch_core::{
    await_loop_identity, await_step5_loop_identity, teardown_loop_identity,
    teardown_step5_loop_identity, write_loop_identity, write_step5_loop_identity,
};

use crate::argparse_compat::parse_required_with_help;

const PLAN_WRITE_PROGRAM: &str = "cli.py plan-review write-loop-identity";
const PLAN_WRITE_USAGE: &str = concat!(
    "usage: cli.py plan-review write-loop-identity [-h] --design-tmpdir\n",
    "                                              DESIGN_TMPDIR --pid PID\n",
    "                                              [--expected-signature EXPECTED_SIGNATURE]",
);
const PLAN_WRITE_HELP: &str = concat!(
    "usage: cli.py plan-review write-loop-identity [-h] --design-tmpdir\n",
    "                                              DESIGN_TMPDIR --pid PID\n",
    "                                              [--expected-signature EXPECTED_SIGNATURE]\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --design-tmpdir DESIGN_TMPDIR\n",
    "  --pid PID\n",
    "  --expected-signature EXPECTED_SIGNATURE",
);
const PLAN_AWAIT_PROGRAM: &str = "cli.py plan-review await-loop-identity";
const PLAN_AWAIT_USAGE: &str = concat!(
    "usage: cli.py plan-review await-loop-identity [-h] --design-tmpdir\n",
    "                                              DESIGN_TMPDIR --pid PID\n",
    "                                              [--timeout-s TIMEOUT_S]\n",
    "                                              [--reattach]",
);
const PLAN_AWAIT_HELP: &str = concat!(
    "usage: cli.py plan-review await-loop-identity [-h] --design-tmpdir\n",
    "                                              DESIGN_TMPDIR --pid PID\n",
    "                                              [--timeout-s TIMEOUT_S]\n",
    "                                              [--reattach]\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --design-tmpdir DESIGN_TMPDIR\n",
    "  --pid PID\n",
    "  --timeout-s TIMEOUT_S\n",
    "  --reattach",
);
const PLAN_TEARDOWN_PROGRAM: &str = "cli.py plan-review teardown-loop-identity";
const PLAN_TEARDOWN_USAGE: &str = concat!(
    "usage: cli.py plan-review teardown-loop-identity [-h] --design-tmpdir\n",
    "                                                 DESIGN_TMPDIR --pid PID",
);
const PLAN_TEARDOWN_HELP: &str = concat!(
    "usage: cli.py plan-review teardown-loop-identity [-h] --design-tmpdir\n",
    "                                                 DESIGN_TMPDIR --pid PID\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --design-tmpdir DESIGN_TMPDIR\n",
    "  --pid PID",
);

const REVIEW_WRITE_PROGRAM: &str = "cli.py review-and-fix write-loop-identity";
const REVIEW_WRITE_USAGE: &str = concat!(
    "usage: cli.py review-and-fix write-loop-identity [-h] --implement-tmpdir\n",
    "                                                 IMPLEMENT_TMPDIR --pid PID\n",
    "                                                 [--expected-signature EXPECTED_SIGNATURE]",
);
const REVIEW_WRITE_HELP: &str = concat!(
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
const REVIEW_AWAIT_PROGRAM: &str = "cli.py review-and-fix await-loop-identity";
const REVIEW_AWAIT_USAGE: &str = concat!(
    "usage: cli.py review-and-fix await-loop-identity [-h] --implement-tmpdir\n",
    "                                                 IMPLEMENT_TMPDIR --pid PID\n",
    "                                                 [--timeout-s TIMEOUT_S]\n",
    "                                                 [--reattach]",
);
const REVIEW_AWAIT_HELP: &str = concat!(
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
const REVIEW_TEARDOWN_PROGRAM: &str = "cli.py review-and-fix teardown-loop-identity";
const REVIEW_TEARDOWN_USAGE: &str = concat!(
    "usage: cli.py review-and-fix teardown-loop-identity [-h] --implement-tmpdir\n",
    "                                                    IMPLEMENT_TMPDIR --pid PID",
);
const REVIEW_TEARDOWN_HELP: &str = concat!(
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

#[derive(Clone, Copy)]
enum LoopSurface {
    PlanReview,
    ReviewAndFix,
}

impl LoopSurface {
    const fn tmpdir_option(self) -> &'static str {
        match self {
            Self::PlanReview => "--design-tmpdir",
            Self::ReviewAndFix => "--implement-tmpdir",
        }
    }

    const fn write_contract(self) -> (&'static str, &'static str, &'static str, &'static str) {
        match self {
            Self::PlanReview => (
                PLAN_WRITE_PROGRAM,
                PLAN_WRITE_USAGE,
                PLAN_WRITE_HELP,
                "plan-review run",
            ),
            Self::ReviewAndFix => (
                REVIEW_WRITE_PROGRAM,
                REVIEW_WRITE_USAGE,
                REVIEW_WRITE_HELP,
                "review-and-fix step5",
            ),
        }
    }

    const fn await_contract(self) -> (&'static str, &'static str, &'static str) {
        match self {
            Self::PlanReview => (PLAN_AWAIT_PROGRAM, PLAN_AWAIT_USAGE, PLAN_AWAIT_HELP),
            Self::ReviewAndFix => (REVIEW_AWAIT_PROGRAM, REVIEW_AWAIT_USAGE, REVIEW_AWAIT_HELP),
        }
    }

    const fn teardown_contract(self) -> (&'static str, &'static str, &'static str) {
        match self {
            Self::PlanReview => (
                PLAN_TEARDOWN_PROGRAM,
                PLAN_TEARDOWN_USAGE,
                PLAN_TEARDOWN_HELP,
            ),
            Self::ReviewAndFix => (
                REVIEW_TEARDOWN_PROGRAM,
                REVIEW_TEARDOWN_USAGE,
                REVIEW_TEARDOWN_HELP,
            ),
        }
    }
}

fn validated_tmpdir(raw: &str) -> Option<&str> {
    let path = Path::new(raw);
    if !path.is_absolute() {
        return None;
    }
    let metadata = fs::symlink_metadata(path).ok()?;
    (metadata.file_type().is_dir() && !metadata.file_type().is_symlink()).then_some(raw)
}

fn write_for(arguments: &[OsString], surface: LoopSurface) -> ExitCode {
    let (program, usage, help, default_signature) = surface.write_contract();
    let tmpdir_option = surface.tmpdir_option();
    let parsed = match parse_required_with_help(
        arguments,
        program,
        usage,
        help,
        &[tmpdir_option, "--pid", "--expected-signature"],
        &[],
        &[tmpdir_option, "--pid"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tmpdir = parsed
        .value(tmpdir_option)
        .unwrap_or_default()
        .to_string_lossy();
    let Some(tmpdir) = validated_tmpdir(&tmpdir) else {
        return ExitCode::SUCCESS;
    };
    let pid = parsed.value("--pid").unwrap_or_default().to_string_lossy();
    let signature = parsed
        .value("--expected-signature")
        .map_or_else(|| default_signature.into(), |value| value.to_string_lossy());
    let host = SystemProcessIdentityHost::new();
    exit_code(match surface {
        LoopSurface::PlanReview => write_loop_identity(&host, tmpdir, &pid, &signature),
        LoopSurface::ReviewAndFix => write_step5_loop_identity(&host, tmpdir, &pid, &signature),
    })
}

fn await_for(arguments: &[OsString], surface: LoopSurface) -> ExitCode {
    let (program, usage, help) = surface.await_contract();
    let tmpdir_option = surface.tmpdir_option();
    let parsed = match parse_required_with_help(
        arguments,
        program,
        usage,
        help,
        &[tmpdir_option, "--pid", "--timeout-s"],
        &["--reattach"],
        &[tmpdir_option, "--pid"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tmpdir = parsed
        .value(tmpdir_option)
        .unwrap_or_default()
        .to_string_lossy();
    let Some(tmpdir) = validated_tmpdir(&tmpdir) else {
        return ExitCode::FAILURE;
    };
    let pid = parsed.value("--pid").unwrap_or_default().to_string_lossy();
    let timeout = parsed
        .value("--timeout-s")
        .map_or_else(|| "21600".into(), |value| value.to_string_lossy());
    let host = SystemProcessIdentityHost::new();
    exit_code(match surface {
        LoopSurface::PlanReview => {
            await_loop_identity(&host, tmpdir, &pid, &timeout, parsed.flag("--reattach"))
        }
        LoopSurface::ReviewAndFix => {
            await_step5_loop_identity(&host, tmpdir, &pid, &timeout, parsed.flag("--reattach"))
        }
    })
}

fn teardown_for(arguments: &[OsString], surface: LoopSurface) -> ExitCode {
    let (program, usage, help) = surface.teardown_contract();
    let tmpdir_option = surface.tmpdir_option();
    let parsed = match parse_required_with_help(
        arguments,
        program,
        usage,
        help,
        &[tmpdir_option, "--pid"],
        &[],
        &[tmpdir_option, "--pid"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tmpdir = parsed
        .value(tmpdir_option)
        .unwrap_or_default()
        .to_string_lossy();
    let Some(tmpdir) = validated_tmpdir(&tmpdir) else {
        return ExitCode::SUCCESS;
    };
    let pid = parsed.value("--pid").unwrap_or_default().to_string_lossy();
    let host = SystemProcessIdentityHost::new();
    exit_code(match surface {
        LoopSurface::PlanReview => teardown_loop_identity(&host, tmpdir, &pid),
        LoopSurface::ReviewAndFix => teardown_step5_loop_identity(&host, tmpdir, &pid),
    })
}

/// Capture and persist one implement Step 5 process identity.
pub fn write(arguments: &[OsString]) -> ExitCode {
    write_for(arguments, LoopSurface::ReviewAndFix)
}

/// Wait until the persisted implement Step 5 process exits or its timeout elapses.
pub fn await_identity(arguments: &[OsString]) -> ExitCode {
    await_for(arguments, LoopSurface::ReviewAndFix)
}

/// Terminate a matching implement Step 5 process group and persist the kill log.
pub fn teardown(arguments: &[OsString]) -> ExitCode {
    teardown_for(arguments, LoopSurface::ReviewAndFix)
}

/// Capture and persist one design Step 3 process identity.
pub fn write_plan_review(arguments: &[OsString]) -> ExitCode {
    write_for(arguments, LoopSurface::PlanReview)
}

/// Wait until the persisted design Step 3 process exits or its timeout elapses.
pub fn await_plan_review(arguments: &[OsString]) -> ExitCode {
    await_for(arguments, LoopSurface::PlanReview)
}

/// Terminate a matching design Step 3 process group and persist the kill log.
pub fn teardown_plan_review(arguments: &[OsString]) -> ExitCode {
    teardown_for(arguments, LoopSurface::PlanReview)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn tmpdir_validation_matches_the_retired_python_rules() {
        let temporary = tempdir().expect("temporary directory");
        let path = temporary.path().to_string_lossy();
        assert_eq!(validated_tmpdir(&path), Some(path.as_ref()));
        assert!(validated_tmpdir("relative").is_none());

        #[cfg(unix)]
        {
            let link = temporary.path().with_extension("link");
            std::os::unix::fs::symlink(temporary.path(), &link).expect("directory symlink");
            assert!(validated_tmpdir(&link.to_string_lossy()).is_none());
            fs::remove_file(link).expect("remove test symlink");
        }
    }
}
