//! `larch test-shard` command composition.

use clap::{Args, Subcommand};
use larch_core::{
    TestShardMap, TestShardTiming, pack_test_shards, read_makefile_shards, rewrite_makefile_shards,
};
use serde::Serialize;
use std::{
    fs,
    io::{Read as _, Write as _},
    path::{Path, PathBuf},
    process::ExitCode,
};

const DEFAULT_GUARD: &str = "";
const DEFAULT_MAKEFILE_PATH: &str = "Makefile";

#[derive(Subcommand)]
pub enum TestShardCommand {
    /// Pack timing rows from stdin into deterministic LPT shard assignments.
    Pack(PackArguments),
    /// Read literal `test-harnesses-N:` Makefile rules as JSON.
    ReadMakefile(MakefileArguments),
    /// Rewrite selected literal `test-harnesses-N:` Makefile rules from stdin JSON.
    WriteMakefile(WriteMakefileArguments),
}

#[derive(Args)]
pub struct PackArguments {
    /// Number of one-based output shards.
    #[arg(long, value_parser = parse_shard_count)]
    n_shards: u32,
    /// Target that must be first in its assigned shard. An empty value disables it.
    #[arg(long, default_value = DEFAULT_GUARD)]
    guard: String,
    /// Unmeasured target to place with zero weight. Repeat for multiple targets.
    #[arg(long = "extra")]
    extras: Vec<String>,
    /// JSON timing rows. Reads stdin when omitted.
    #[arg(long)]
    input: Option<PathBuf>,
}

#[derive(Args)]
pub struct MakefileArguments {
    /// Makefile to read or rewrite.
    #[arg(long, default_value = DEFAULT_MAKEFILE_PATH)]
    path: PathBuf,
}

#[derive(Args)]
pub struct WriteMakefileArguments {
    /// Makefile to rewrite.
    #[arg(long, default_value = DEFAULT_MAKEFILE_PATH)]
    path: PathBuf,
    /// JSON shard map. Reads stdin when omitted.
    #[arg(long)]
    input: Option<PathBuf>,
}

pub fn run(command: TestShardCommand) -> ExitCode {
    match run_inner(command) {
        Ok(Some(output)) => {
            if let Err(error) = std::io::stdout().lock().write_all(&output) {
                eprintln!("test-shard: cannot write output: {error}");
                return ExitCode::from(1);
            }
            ExitCode::SUCCESS
        }
        Ok(None) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("test-shard: {error}");
            ExitCode::from(1)
        }
    }
}

fn run_inner(command: TestShardCommand) -> Result<Option<Vec<u8>>, String> {
    match command {
        TestShardCommand::Pack(arguments) => {
            let timings = read_json_input::<Vec<TestShardTiming>>(arguments.input.as_deref())?;
            let shards = pack_test_shards(
                &timings,
                arguments.n_shards,
                &arguments.guard,
                &arguments.extras,
            )?;
            serialize_json(&shards).map(Some)
        }
        TestShardCommand::ReadMakefile(arguments) => {
            let source = read_makefile(&arguments.path)?;
            serialize_json(&read_makefile_shards(&source)).map(Some)
        }
        TestShardCommand::WriteMakefile(arguments) => {
            let shards = read_json_input::<TestShardMap>(arguments.input.as_deref())?;
            if shards.keys().any(|shard| *shard == 0) {
                return Err("shard identifiers must be at least 1".to_owned());
            }
            let source = read_makefile(&arguments.path)?;
            let rewritten = rewrite_makefile_shards(&source, &shards);
            write_makefile_atomically(&arguments.path, &rewritten)?;
            Ok(None)
        }
    }
}

fn parse_shard_count(value: &str) -> Result<u32, String> {
    value
        .parse::<u32>()
        .ok()
        .filter(|count| *count > 0)
        .ok_or_else(|| format!("expected a positive integer, got {value:?}"))
}

fn read_json_input<T: serde::de::DeserializeOwned>(path: Option<&Path>) -> Result<T, String> {
    let input = if let Some(path) = path {
        fs::read(path)
            .map_err(|error| format!("cannot read JSON input {}: {error}", path.display()))?
    } else {
        let mut input = Vec::new();
        std::io::stdin()
            .lock()
            .read_to_end(&mut input)
            .map_err(|error| format!("cannot read stdin: {error}"))?;
        input
    };
    let source = path.map_or_else(|| "stdin".to_owned(), |path| path.display().to_string());
    serde_json::from_slice(&input).map_err(|error| format!("invalid JSON from {source}: {error}"))
}

fn serialize_json(value: &impl Serialize) -> Result<Vec<u8>, String> {
    let mut output = serde_json::to_vec(value)
        .map_err(|error| format!("cannot serialize test-shard output: {error}"))?;
    output.push(b'\n');
    Ok(output)
}

fn read_makefile(path: &Path) -> Result<String, String> {
    fs::read_to_string(path).map_err(|error| format!("cannot read {}: {error}", path.display()))
}

fn write_makefile_atomically(path: &Path, contents: &str) -> Result<(), String> {
    let parent = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    let permissions = fs::metadata(path)
        .ok()
        .map(|metadata| metadata.permissions());
    let mut temporary = tempfile::NamedTempFile::new_in(parent).map_err(|error| {
        format!(
            "cannot create temporary Makefile beside {}: {error}",
            path.display()
        )
    })?;
    temporary
        .write_all(contents.as_bytes())
        .map_err(|error| format!("cannot write temporary Makefile: {error}"))?;
    temporary
        .flush()
        .map_err(|error| format!("cannot flush temporary Makefile: {error}"))?;
    if let Some(permissions) = permissions {
        temporary
            .as_file()
            .set_permissions(permissions)
            .map_err(|error| format!("cannot preserve Makefile permissions: {error}"))?;
    }
    temporary
        .persist(path)
        .map_err(|error| format!("cannot atomically replace {}: {error}", path.display()))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::parse_shard_count;

    #[test]
    fn shard_count_parser_rejects_zero_and_non_numbers() {
        assert_eq!(parse_shard_count("3"), Ok(3));
        assert!(parse_shard_count("0").is_err());
        assert!(parse_shard_count("nope").is_err());
    }
}
