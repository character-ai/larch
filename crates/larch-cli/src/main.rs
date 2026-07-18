use std::process::ExitCode;

use clap::{Args, CommandFactory, FromArgMatches, Parser, Subcommand};

#[derive(Parser)]
#[command(
    name = "larch",
    about = "Larch workflow automation",
    arg_required_else_help = true,
    subcommand_required = true
)]
struct Cli {
    #[command(subcommand)]
    domain: Domain,
}

#[derive(Subcommand)]
enum Domain {
    /// Internal bootstrap commands used before installation completes.
    #[command(subcommand, hide = true)]
    Bootstrap(BootstrapCommand),
    /// Non-production commands that exercise dispatcher wiring.
    #[command(subcommand)]
    Example(ExampleCommand),
}

#[derive(Subcommand)]
enum BootstrapCommand {
    /// Print the compiled version and target as machine-readable JSON.
    SelfCheck,
}

#[derive(Subcommand)]
enum ExampleCommand {
    /// Print a message through the core library.
    Echo(EchoArguments),
}

#[derive(Args)]
struct EchoArguments {
    /// Message to print.
    message: String,
}

fn run(cli: Cli, metadata: larch_core::BuildMetadata) {
    match cli.domain {
        Domain::Bootstrap(BootstrapCommand::SelfCheck) => {
            println!("{}", larch_core::bootstrap_self_check(metadata));
        }
        Domain::Example(ExampleCommand::Echo(arguments)) => {
            println!("{}", larch_core::example::echo(&arguments.message));
        }
    }
}

fn main() -> ExitCode {
    let metadata = larch_adapters::build_metadata();
    let matches = Cli::command().version(metadata.version()).get_matches();
    let cli = Cli::from_arg_matches(&matches)
        .expect("arguments already validated by the generated Clap command");
    run(cli, metadata);
    ExitCode::SUCCESS
}
