//! Checked transaction for synchronized release-version surfaces.

use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    fmt::Write as _,
    fs,
    os::unix::fs::PermissionsExt,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::{ConfinedPath, PathIntent, RepositoryRoot, atomic_write_utf8, read_utf8};

use crate::release_common::semver;
use serde::{
    Deserialize, Deserializer,
    de::{MapAccess, SeqAccess, Visitor},
};
use serde_json::Value as JsonValue;
use toml::Value as TomlValue;

const PLUGIN_JSON: &str = ".claude-plugin/plugin.json";
const PROJECTED_PLUGIN_JSON: &str = "plugin/.claude-plugin/plugin.json";
const CARGO_MANIFEST: &str = "Cargo.toml";
const CARGO_LOCK: &str = "Cargo.lock";
const TEST_REPOSITORY_ROOT: &str = "LARCH_RELEASE_SET_VERSION_REPO_ROOT";
const TEST_PLUGIN_JSON: &str = "LARCH_RELEASE_SET_VERSION_PLUGIN_JSON";
const TEST_FAIL_AFTER_WRITE: &str = "LARCH_TEST_RELEASE_SET_VERSION_FAIL_AFTER_WRITE";

struct SourceFile {
    relative: PathBuf,
    write_path: ConfinedPath,
    original: String,
    mode: u32,
}

struct StagedFile {
    source: SourceFile,
    rendered: String,
}

struct ReleaseVersions {
    member_names: Vec<String>,
    internal_dependencies: Vec<String>,
}

enum OrderedJson {
    Null,
    Bool(bool),
    Number(serde_json::Number),
    String(String),
    Array(Vec<Self>),
    Object(Vec<(String, Self)>),
}

struct OrderedJsonVisitor;

impl<'de> Visitor<'de> for OrderedJsonVisitor {
    type Value = OrderedJson;

    fn expecting(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str("a JSON value")
    }

    fn visit_bool<E>(self, value: bool) -> Result<Self::Value, E> {
        Ok(OrderedJson::Bool(value))
    }

    fn visit_i64<E>(self, value: i64) -> Result<Self::Value, E> {
        Ok(OrderedJson::Number(value.into()))
    }

    fn visit_u64<E>(self, value: u64) -> Result<Self::Value, E> {
        Ok(OrderedJson::Number(value.into()))
    }

    fn visit_f64<E>(self, value: f64) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        serde_json::Number::from_f64(value)
            .map(OrderedJson::Number)
            .ok_or_else(|| E::custom("JSON number is not finite"))
    }

    fn visit_str<E>(self, value: &str) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        self.visit_string(value.to_owned())
    }

    fn visit_string<E>(self, value: String) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        Ok(OrderedJson::String(value))
    }

    fn visit_none<E>(self) -> Result<Self::Value, E> {
        Ok(OrderedJson::Null)
    }

    fn visit_unit<E>(self) -> Result<Self::Value, E> {
        Ok(OrderedJson::Null)
    }

    fn visit_seq<A>(self, mut sequence: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        let mut values = Vec::new();
        while let Some(value) = sequence.next_element()? {
            values.push(value);
        }
        Ok(OrderedJson::Array(values))
    }

    fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut values: Vec<(String, OrderedJson)> = Vec::new();
        while let Some((key, value)) = map.next_entry()? {
            if let Some((_, prior)) = values.iter_mut().find(|(prior, _)| prior == &key) {
                *prior = value;
            } else {
                values.push((key, value));
            }
        }
        Ok(OrderedJson::Object(values))
    }
}

impl<'de> Deserialize<'de> for OrderedJson {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(OrderedJsonVisitor)
    }
}

/// Update all synchronized version files, preserving the Python command's wire output.
pub fn run(new_version: &str) -> ExitCode {
    match update_release_version(new_version) {
        Ok(previous) => {
            println!("PREVIOUS_VERSION={previous}");
            println!("NEW_VERSION={new_version}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("ERROR={}", one_line(&error));
            ExitCode::FAILURE
        }
    }
}

fn update_release_version(new_version: &str) -> Result<String, String> {
    let new_parts = semver(new_version).ok_or_else(|| format!("invalid semver: {new_version}"))?;
    let (root_path, plugin_path) = release_paths()?;
    let plugin_relative = relative_to_root(&root_path, &plugin_path)?;
    let root = RepositoryRoot::resolve(Some(&root_path)).map_err(|error| error.to_string())?;
    let plugin = source_file(&root, &plugin_relative)?;
    let current = plugin_version(&plugin.original, PLUGIN_JSON)?;
    let current_parts = semver(&current)
        .ok_or_else(|| format!("version {current:?} is not semver (expected X.Y.Z)"))?;
    if new_version == current {
        return Err(format!("no-op: version already {current}"));
    }
    if new_parts < current_parts {
        return Err(format!("downgrade refused: {new_version} < {current}"));
    }

    let staged = stage_transaction(&root, plugin, &current, new_version)?;
    commit_transaction(&root, &staged, new_version)?;
    Ok(current)
}

fn release_paths() -> Result<(PathBuf, PathBuf), String> {
    let root_override = nonempty_env(TEST_REPOSITORY_ROOT);
    let plugin_override = nonempty_env(TEST_PLUGIN_JSON);
    let plugin = plugin_override
        .as_ref()
        .map_or_else(|| PathBuf::from(PLUGIN_JSON), PathBuf::from);
    let root = if let Some(value) = root_override {
        PathBuf::from(value)
    } else if let Some(value) = plugin_override {
        let path = PathBuf::from(value);
        path.parent()
            .and_then(Path::parent)
            .ok_or_else(|| format!("{TEST_PLUGIN_JSON} has no repository parent"))?
            .to_path_buf()
    } else {
        env::current_dir().map_err(|error| error.to_string())?
    };
    let root = absolutize(root)?;
    let plugin = if plugin.is_absolute() {
        plugin
    } else {
        root.join(plugin)
    };
    Ok((root, plugin))
}

fn nonempty_env(name: &str) -> Option<String> {
    env::var(name).ok().filter(|value| !value.is_empty())
}

fn absolutize(path: PathBuf) -> Result<PathBuf, String> {
    if path.is_absolute() {
        Ok(path)
    } else {
        env::current_dir()
            .map(|current| current.join(path))
            .map_err(|error| error.to_string())
    }
}

fn relative_to_root(root: &Path, path: &Path) -> Result<PathBuf, String> {
    path.strip_prefix(root).map(Path::to_path_buf).map_err(|_| {
        format!(
            "release version path escapes repository root: {}",
            path.display()
        )
    })
}

fn stage_transaction(
    root: &RepositoryRoot,
    plugin: SourceFile,
    current: &str,
    new: &str,
) -> Result<Vec<StagedFile>, String> {
    let cargo = source_file(root, Path::new(CARGO_MANIFEST))?;
    let lock = source_file(root, Path::new(CARGO_LOCK))?;
    let projected = optional_source_file(root, Path::new(PROJECTED_PLUGIN_JSON))?;
    if projected
        .as_ref()
        .is_some_and(|file| file.original != plugin.original)
    {
        return Err("runtime projection plugin version source is out of sync".to_owned());
    }

    let cargo_data = toml_data(&cargo.original, CARGO_MANIFEST)?;
    let workspace_version = workspace_version(&cargo_data)?;
    if workspace_version != current {
        return Err("Cargo workspace version does not match plugin version".to_owned());
    }
    let versions = release_versions(root, &cargo_data, current)?;
    let lock_data = toml_data(&lock.original, CARGO_LOCK)?;
    validate_lock_versions(&lock_data, &versions.member_names, current)?;

    let mut plugin_data: OrderedJson = serde_json::from_str(&plugin.original)
        .map_err(|_| format!("{PLUGIN_JSON} is not valid JSON"))?;
    let OrderedJson::Object(plugin_object) = &mut plugin_data else {
        return Err(format!("{PLUGIN_JSON} does not contain an object"));
    };
    let version = plugin_object
        .iter_mut()
        .find(|(key, _)| key == "version")
        .ok_or_else(|| format!("{PLUGIN_JSON} missing .version field"))?;
    version.1 = OrderedJson::String(new.to_owned());
    let plugin_rendered = pretty_json(&plugin_data) + "\n";

    let cargo_rendered = replace_dependency_versions(
        &replace_workspace_version(&cargo.original, current, new)?,
        &versions.internal_dependencies,
        current,
        new,
    )?;
    let lock_rendered =
        replace_lock_versions(&lock.original, &versions.member_names, current, new)?;

    let mut staged = vec![
        StagedFile {
            source: plugin,
            rendered: plugin_rendered.clone(),
        },
        StagedFile {
            source: cargo,
            rendered: cargo_rendered,
        },
        StagedFile {
            source: lock,
            rendered: lock_rendered,
        },
    ];
    if let Some(source) = projected {
        staged.push(StagedFile {
            source,
            rendered: plugin_rendered,
        });
    }
    Ok(staged)
}

fn source_file(root: &RepositoryRoot, relative: &Path) -> Result<SourceFile, String> {
    let read_path = release_read_path(root, relative)?;
    let original = read_release_file(&read_path, relative)?;
    let mode = fs::metadata(read_path.path())
        .map_err(|error| error.to_string())?
        .permissions()
        .mode()
        & 0o777;
    let write_path = root
        .confine(relative, PathIntent::Write)
        .map_err(|error| error.to_string())?;
    Ok(SourceFile {
        relative: relative.to_path_buf(),
        write_path,
        original,
        mode,
    })
}

fn release_read_path(root: &RepositoryRoot, relative: &Path) -> Result<ConfinedPath, String> {
    root.confine(relative, PathIntent::Read).map_err(|_| {
        format!(
            "required release version file is missing or unsafe: {}",
            relative.display()
        )
    })
}

fn read_release_file(path: &ConfinedPath, relative: &Path) -> Result<String, String> {
    read_utf8(path).map_err(|_| format!("{} is not valid UTF-8", relative.display()))
}

fn optional_source_file(
    root: &RepositoryRoot,
    relative: &Path,
) -> Result<Option<SourceFile>, String> {
    match fs::symlink_metadata(root.path().join(relative)) {
        Ok(_) => source_file(root, relative).map(Some),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(error) => Err(error.to_string()),
    }
}

fn plugin_version(text: &str, source: &str) -> Result<String, String> {
    let value: JsonValue =
        serde_json::from_str(text).map_err(|_| format!("{source} is not valid JSON"))?;
    let version = value
        .get("version")
        .and_then(JsonValue::as_str)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| format!("{source} missing .version field"))?;
    if semver(version).is_none() {
        return Err(format!(
            "version {version:?} is not semver (expected X.Y.Z)"
        ));
    }
    Ok(version.to_owned())
}

fn pretty_json(value: &OrderedJson) -> String {
    let mut output = String::new();
    render_json(value, 0, &mut output);
    output
}

fn render_json(value: &OrderedJson, indent: usize, output: &mut String) {
    match value {
        OrderedJson::Null => output.push_str("null"),
        OrderedJson::Bool(value) => output.push_str(if *value { "true" } else { "false" }),
        OrderedJson::Number(value) => output.push_str(&value.to_string()),
        OrderedJson::String(value) => output.push_str(&ascii_json_string(value)),
        OrderedJson::Array(values) => render_json_array(values, indent, output),
        OrderedJson::Object(values) => render_json_object(values, indent, output),
    }
}

fn render_json_array(values: &[OrderedJson], indent: usize, output: &mut String) {
    if values.is_empty() {
        output.push_str("[]");
        return;
    }
    output.push_str("[\n");
    for (index, value) in values.iter().enumerate() {
        output.push_str(&" ".repeat(indent + 2));
        render_json(value, indent + 2, output);
        output.push_str(if index + 1 == values.len() {
            "\n"
        } else {
            ",\n"
        });
    }
    output.push_str(&" ".repeat(indent));
    output.push(']');
}

fn render_json_object(values: &[(String, OrderedJson)], indent: usize, output: &mut String) {
    if values.is_empty() {
        output.push_str("{}");
        return;
    }
    output.push_str("{\n");
    for (index, (key, value)) in values.iter().enumerate() {
        output.push_str(&" ".repeat(indent + 2));
        output.push_str(&ascii_json_string(key));
        output.push_str(": ");
        render_json(value, indent + 2, output);
        output.push_str(if index + 1 == values.len() {
            "\n"
        } else {
            ",\n"
        });
    }
    output.push_str(&" ".repeat(indent));
    output.push('}');
}

fn ascii_json_string(value: &str) -> String {
    let serialized = serde_json::to_string(value).expect("a string always serializes");
    let mut output = String::with_capacity(serialized.len());
    for character in serialized.chars() {
        let codepoint = u32::from(character);
        if character.is_ascii() {
            output.push(character);
        } else if codepoint <= 0xffff {
            let _ = write!(output, "\\u{codepoint:04x}");
        } else {
            let adjusted = codepoint - 0x1_0000;
            let high = 0xd800 + (adjusted >> 10);
            let low = 0xdc00 + (adjusted & 0x3ff);
            let _ = write!(output, "\\u{high:04x}\\u{low:04x}");
        }
    }
    output
}

fn toml_data(text: &str, path: &str) -> Result<TomlValue, String> {
    toml::from_str::<TomlValue>(text).map_err(|_| format!("{path} is not valid UTF-8 TOML"))
}

fn workspace_table(data: &TomlValue) -> Result<&toml::map::Map<String, TomlValue>, String> {
    data.get("workspace")
        .and_then(TomlValue::as_table)
        .ok_or_else(|| "Cargo.toml is missing [workspace]".to_owned())
}

fn workspace_version(data: &TomlValue) -> Result<&str, String> {
    let version = workspace_table(data)?
        .get("package")
        .and_then(TomlValue::as_table)
        .and_then(|package| package.get("version"))
        .and_then(TomlValue::as_str)
        .ok_or_else(|| "Cargo.toml has no valid workspace package version".to_owned())?;
    semver(version)
        .map(|_| version)
        .ok_or_else(|| "Cargo.toml has no valid workspace package version".to_owned())
}

fn release_versions(
    root: &RepositoryRoot,
    cargo: &TomlValue,
    current: &str,
) -> Result<ReleaseVersions, String> {
    let workspace = workspace_table(cargo)?;
    let members = workspace
        .get("members")
        .and_then(TomlValue::as_array)
        .filter(|members| !members.is_empty())
        .ok_or_else(|| "Cargo.toml workspace members are invalid".to_owned())?;
    let mut paths = BTreeMap::new();
    let mut member_names = Vec::new();
    for member in members {
        let member = member
            .as_str()
            .ok_or_else(|| "Cargo.toml workspace members are invalid".to_owned())?;
        let manifest_relative = Path::new(member).join(CARGO_MANIFEST);
        let manifest_path = release_read_path(root, &manifest_relative)?;
        let manifest = read_release_file(&manifest_path, &manifest_relative)?;
        let data = toml_data(&manifest, &manifest_relative.display().to_string())?;
        let package = data
            .get("package")
            .and_then(TomlValue::as_table)
            .ok_or_else(|| format!("workspace member version ownership is invalid: {member}"))?;
        let name = package
            .get("name")
            .and_then(TomlValue::as_str)
            .ok_or_else(|| format!("workspace member version ownership is invalid: {member}"))?;
        let workspace_owned = package
            .get("version")
            .and_then(TomlValue::as_table)
            .and_then(|version| version.get("workspace"))
            .and_then(TomlValue::as_bool)
            == Some(true);
        if !workspace_owned {
            return Err(format!(
                "workspace member version ownership is invalid: {member}"
            ));
        }
        paths.insert(member.to_owned(), name.to_owned());
        member_names.push(name.to_owned());
    }
    if member_names.iter().collect::<BTreeSet<_>>().len() != member_names.len() {
        return Err("Cargo workspace member names are not unique".to_owned());
    }

    let dependencies = workspace
        .get("dependencies")
        .and_then(TomlValue::as_table)
        .ok_or_else(|| "Cargo.toml is missing [workspace.dependencies]".to_owned())?;
    let mut internal_dependencies = Vec::new();
    for (dependency_name, specification) in dependencies {
        let Some(specification) = specification.as_table() else {
            continue;
        };
        let Some(path) = specification.get("path").and_then(TomlValue::as_str) else {
            continue;
        };
        let Some(member_name) = paths.get(path) else {
            continue;
        };
        if dependency_name != member_name {
            return Err(format!(
                "workspace path dependency name mismatch: {dependency_name}"
            ));
        }
        let expected = format!("={current}");
        if specification.get("version").and_then(TomlValue::as_str) != Some(&expected) {
            return Err(format!(
                "workspace path dependency version mismatch: {dependency_name}"
            ));
        }
        internal_dependencies.push(dependency_name.clone());
    }
    internal_dependencies.sort();
    Ok(ReleaseVersions {
        member_names,
        internal_dependencies,
    })
}

fn validate_lock_versions(
    lock: &TomlValue,
    member_names: &[String],
    current: &str,
) -> Result<(), String> {
    let packages = lock
        .get("package")
        .and_then(TomlValue::as_array)
        .ok_or_else(|| "Cargo.lock has no package records".to_owned())?;
    let mut found = member_names
        .iter()
        .map(|name| (name.as_str(), Vec::new()))
        .collect::<BTreeMap<_, _>>();
    for package in packages {
        let package = package
            .as_table()
            .ok_or_else(|| "Cargo.lock contains an invalid package record".to_owned())?;
        let Some(name) = package.get("name").and_then(TomlValue::as_str) else {
            continue;
        };
        if let (Some(versions), Some(version)) = (
            found.get_mut(name),
            package.get("version").and_then(TomlValue::as_str),
        ) {
            versions.push(version);
        }
    }
    for (name, versions) in found {
        if versions != [current] {
            return Err(format!(
                "Cargo.lock workspace package version mismatch: {name}"
            ));
        }
    }
    Ok(())
}

fn replace_workspace_version(text: &str, current: &str, new: &str) -> Result<String, String> {
    let header = "[workspace.package]";
    let start = text
        .find(header)
        .ok_or_else(|| "Cargo.toml is missing [workspace.package]".to_owned())?;
    let end = text[start + header.len()..]
        .find("\n[")
        .map_or(text.len(), |offset| start + header.len() + offset);
    let section = &text[start..end];
    let old = format!("version = \"{current}\"");
    if section.matches(&old).count() != 1 {
        return Err("Cargo.toml workspace version line is not canonical".to_owned());
    }
    Ok(format!(
        "{}{}{}",
        &text[..start],
        section.replace(&old, &format!("version = \"{new}\"")),
        &text[end..]
    ))
}

fn replace_dependency_versions(
    text: &str,
    dependency_names: &[String],
    current: &str,
    new: &str,
) -> Result<String, String> {
    let mut lines = text
        .split_inclusive('\n')
        .map(str::to_owned)
        .collect::<Vec<_>>();
    for name in dependency_names {
        let matching = lines
            .iter()
            .enumerate()
            .filter_map(|(index, line)| line.starts_with(&format!("{name} = ")).then_some(index))
            .collect::<Vec<_>>();
        if matching.len() != 1 {
            return Err(format!(
                "Cargo.toml dependency line is not canonical: {name}"
            ));
        }
        let old = format!("version = \"={current}\"");
        let index = matching[0];
        if lines[index].matches(&old).count() != 1 {
            return Err(format!(
                "Cargo.toml dependency version is not canonical: {name}"
            ));
        }
        lines[index] = lines[index].replace(&old, &format!("version = \"={new}\""));
    }
    Ok(lines.concat())
}

fn replace_lock_versions(
    text: &str,
    member_names: &[String],
    current: &str,
    new: &str,
) -> Result<String, String> {
    let mut blocks = text
        .split("[[package]]")
        .map(str::to_owned)
        .collect::<Vec<_>>();
    for name in member_names {
        let name_line = format!("\nname = \"{name}\"\n");
        let matching = blocks
            .iter()
            .enumerate()
            .filter_map(|(index, block)| block.contains(&name_line).then_some(index))
            .collect::<Vec<_>>();
        if matching.len() != 1 {
            return Err(format!(
                "Cargo.lock package record is not canonical: {name}"
            ));
        }
        let old = format!("\nversion = \"{current}\"\n");
        let index = matching[0];
        if blocks[index].matches(&old).count() != 1 {
            return Err(format!(
                "Cargo.lock package version is not canonical: {name}"
            ));
        }
        blocks[index] = blocks[index].replace(&old, &format!("\nversion = \"{new}\"\n"));
    }
    Ok(blocks.join("[[package]]"))
}

fn commit_transaction(
    root: &RepositoryRoot,
    staged: &[StagedFile],
    expected: &str,
) -> Result<(), String> {
    let result = write_all(staged).and_then(|()| verify_release_version(root, expected));
    if let Err(error) = result {
        let rollback_errors = rollback(staged);
        let detail = if rollback_errors.is_empty() {
            String::new()
        } else {
            format!("; rollback failed for {}", rollback_errors.join(","))
        };
        return Err(format!("release version update failed: {error}{detail}"));
    }
    Ok(())
}

fn write_all(staged: &[StagedFile]) -> Result<(), String> {
    for (index, file) in staged.iter().enumerate() {
        atomic_write_utf8(&file.source.write_path, &file.rendered, file.source.mode)
            .map_err(|error| error.to_string())?;
        if injected_failure_after(index + 1) {
            return Err(format!(
                "injected write interruption after {}",
                file.source.relative.display()
            ));
        }
    }
    Ok(())
}

fn rollback(staged: &[StagedFile]) -> Vec<String> {
    let mut errors = Vec::new();
    for file in staged.iter().rev() {
        if atomic_write_utf8(
            &file.source.write_path,
            &file.source.original,
            file.source.mode,
        )
        .is_err()
        {
            errors.push(file.source.relative.display().to_string());
        }
    }
    errors
}

fn verify_release_version(root: &RepositoryRoot, expected: &str) -> Result<(), String> {
    let plugin = source_file(root, Path::new(PLUGIN_JSON))?;
    if plugin_version(&plugin.original, PLUGIN_JSON)? != expected {
        return Err("plugin version postcondition failed".to_owned());
    }
    let cargo = source_file(root, Path::new(CARGO_MANIFEST))?;
    let cargo_data = toml_data(&cargo.original, CARGO_MANIFEST)?;
    if workspace_version(&cargo_data)? != expected {
        return Err("Cargo workspace version postcondition failed".to_owned());
    }
    let versions = release_versions(root, &cargo_data, expected)?;
    let lock = source_file(root, Path::new(CARGO_LOCK))?;
    validate_lock_versions(
        &toml_data(&lock.original, CARGO_LOCK)?,
        &versions.member_names,
        expected,
    )?;
    if let Some(projected) = optional_source_file(root, Path::new(PROJECTED_PLUGIN_JSON))?
        && plugin_version(&projected.original, PROJECTED_PLUGIN_JSON)? != expected
    {
        return Err("runtime projection plugin version does not match release version".to_owned());
    }
    Ok(())
}

fn injected_failure_after(write_count: usize) -> bool {
    cfg!(debug_assertions)
        && env::var(TEST_FAIL_AFTER_WRITE)
            .ok()
            .and_then(|value| value.parse::<usize>().ok())
            == Some(write_count)
}

fn one_line(value: &str) -> String {
    value.replace(['\n', '\r'], " ")
}
