//! Standalone dependency-free residual Bash manifest reader for CI.

use std::{env, ffi::OsString, io::Write as _, path::PathBuf, process::ExitCode};

#[cfg(not(test))]
mod residual_bash;
#[cfg(test)]
use larch_harness_mark as residual_bash;

const USAGE: &str = "Usage: larch-residual-bash-paths --root PATH";

fn main() -> ExitCode {
    let arguments = env::args_os().skip(1).collect::<Vec<_>>();
    let Some(root) = parse_root(&arguments) else {
        eprintln!("{USAGE}");
        return ExitCode::from(2);
    };
    let paths = match residual_bash::read_residual_bash_paths(&root, true) {
        Ok(paths) => paths,
        Err(error) => {
            eprintln!("ERROR: {error}");
            return ExitCode::from(2);
        }
    };
    let mut stdout = std::io::stdout().lock();
    for path in paths {
        if stdout
            .write_all(path.as_bytes())
            .and_then(|()| stdout.write_all(b"\0"))
            .is_err()
        {
            return ExitCode::from(1);
        }
    }
    ExitCode::SUCCESS
}

fn parse_root(arguments: &[OsString]) -> Option<PathBuf> {
    (arguments.len() == 2 && arguments[0] == "--root").then(|| PathBuf::from(arguments[1].clone()))
}

#[cfg(test)]
mod tests {
    use super::parse_root;
    use std::{ffi::OsString, path::PathBuf};

    #[test]
    fn root_argument_is_exact() {
        assert_eq!(
            parse_root(&[OsString::from("--root"), OsString::from("repo")]),
            Some(PathBuf::from("repo"))
        );
        assert_eq!(parse_root(&[OsString::from("repo")]), None);
        assert_eq!(
            parse_root(&[
                OsString::from("--root"),
                OsString::from("repo"),
                OsString::from("extra")
            ]),
            None
        );
    }
}
