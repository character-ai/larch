use clap::Parser;

/// Check larch repository policy.
#[derive(Debug, Parser)]
#[command(name = "larch-lint", version)]
struct Cli {}

fn main() {
    let _cli = Cli::parse();
}

#[cfg(test)]
mod tests {
    use clap::CommandFactory;

    use super::Cli;

    #[test]
    fn command_definition_is_valid() {
        Cli::command().debug_assert();
    }
}
