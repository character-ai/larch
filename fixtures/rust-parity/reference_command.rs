use std::{env, fs, path::Path, process::ExitCode};

fn main() -> ExitCode {
    let arguments: Vec<String> = env::args().collect();
    if arguments.len() != 3 {
        eprintln!("usage: reference-command <mode> <root>");
        return ExitCode::from(2);
    }

    let mode = &arguments[1];
    let root = Path::new(&arguments[2]);
    match mode.as_str() {
        "malformed" => {
            eprintln!("malformed input");
            return ExitCode::from(65);
        }
        "environment" => {
            if env::var_os("FIXTURE_REQUIRED").is_none() {
                eprintln!("required environment value is unavailable");
                return ExitCode::from(69);
            }
            return ExitCode::SUCCESS;
        }
        "isolation" => {
            let token_state = if env::var_os("GH_TOKEN").is_some() {
                "present"
            } else {
                "absent"
            };
            println!("GH_TOKEN={token_state}");
            for key in [
                "GITHUB_API_URL",
                "CLOUDSDK_CONFIG",
                "PATH",
                "LARCH_PARITY_LIVE_SERVICES",
            ] {
                println!(
                    "{key}={}",
                    env::var(key).expect("isolation environment should be set")
                );
            }
            return ExitCode::SUCCESS;
        }
        "clean" => {}
        _ => {
            eprintln!("unknown mode: {mode}");
            return ExitCode::from(64);
        }
    }

    let timestamp = env::var("FIXTURE_TIMESTAMP").expect("fixture timestamp should be set");
    let seed = fs::read_to_string(root.join("input/seed.txt"))
        .expect("seed should be readable")
        .trim()
        .to_owned();
    let output = root.join("output");
    fs::create_dir(&output).expect("output directory should be created");
    let rendered = format!(
        "root={}\ntimestamp={timestamp}\nseed={seed}\n",
        root.display()
    );
    fs::write(output.join("result.txt"), rendered).expect("result should be written");
    fs::write(output.join("data.bin"), [0, 255]).expect("binary result should be written");
    fs::write(
        root.join("effects.ndjson"),
        format!(
            "{{\"action\":\"write\",\"root\":\"{}\",\"at\":\"{timestamp}\"}}\n",
            root.display()
        ),
    )
    .expect("side effect should be recorded");
    println!(
        "wrote {} at {timestamp}",
        output.join("result.txt").display()
    );
    ExitCode::SUCCESS
}
