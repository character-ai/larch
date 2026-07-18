fn main() {
    let target = std::env::var("TARGET").expect("Cargo must provide TARGET to build scripts");
    println!("cargo:rustc-env=LARCH_BUILD_TARGET={target}");
}
