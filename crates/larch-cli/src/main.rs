use clap::{CommandFactory, Parser};

#[derive(Parser)]
#[command(name = "larch", about = "Larch workflow automation")]
struct Cli;

fn main() {
    let metadata = larch_adapters::build_metadata();
    Cli::command().version(metadata.version()).get_matches();
}
