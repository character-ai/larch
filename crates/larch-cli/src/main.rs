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
    /// Non-production commands that exercise dispatcher wiring.
    #[command(subcommand)]
    Example(ExampleCommand),
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

fn run(cli: Cli) {
    match cli.domain {
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
    run(cli);
    ExitCode::SUCCESS
}
