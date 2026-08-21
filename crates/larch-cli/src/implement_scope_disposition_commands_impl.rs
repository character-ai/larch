fn word_tokens(value: &str) -> Vec<String> {
    value
        .to_lowercase()
        .split(|character: char| {
            !(character.is_ascii_lowercase() || character.is_ascii_digit())
        })
        .filter(|token| !token.is_empty())
        .map(str::to_owned)
        .collect()
}

fn contains_token_sequence(tokens: &[String], sequence: &[&str]) -> bool {
    if sequence.is_empty() || tokens.len() < sequence.len() {
        return false;
    }
    tokens.windows(sequence.len()).any(|window| {
        window
            .iter()
            .zip(sequence.iter())
            .all(|(token, expected)| token == *expected)
    })
}

const BLOCKERS: &[&str] = &[
    "add", "added", "broken", "error", "errors", "fail", "failed", "failing", "fails", "failure",
    "fixed", "fixes", "finish", "fix", "missing", "unimplemented", "write", "writing",
];
const UNRUN: &[&str] = &["incomplete", "skipped", "uncompleted", "unexecuted", "unrun"];

fn is_nonblocking_full_suite_todo(value: &str) -> bool {
    let tokens = word_tokens(value);
    if tokens.iter().any(|token| BLOCKERS.contains(&token.as_str())) {
        return false;
    }
    let full_suite = tokens.iter().any(|token| token == "full")
        && tokens
            .iter()
            .any(|token| token == "suite" || token == "suites")
        && (contains_token_sequence(&tokens, &["make", "py", "lint"])
            || contains_token_sequence(&tokens, &["make", "py", "test"]));
    if !full_suite {
        return false;
    }
    let unrun = {
        if tokens.iter().any(|token| UNRUN.contains(&token.as_str())) {
            true
        } else {
            tokens.iter().enumerate().any(|(index, token)| {
                if !matches!(
                    token.as_str(),
                    "completed" | "executed" | "finished" | "ran" | "run"
                ) {
                    return false;
                }
                let start = index.saturating_sub(3);
                tokens[start..index]
                    .iter()
                    .any(|prior| prior == "not" || prior == "never")
            })
        }
    };
    if !unrun {
        return false;
    }
    contains_token_sequence(&tokens, &["focused", "tests", "passed"])
        || contains_token_sequence(&tokens, &["focused", "test", "passed"])
}

fn read_manifest_todos(manifest_path: Option<&Path>) -> Result<(Vec<String>, i64), String> {
    let Some(path) = manifest_path else {
        return Ok((Vec::new(), 0));
    };
    if !artifact_present(path) {
        return Ok((Vec::new(), 0));
    }
    let schema_invalid = || format!("resolved manifest schema-invalid: {}", path.display());
    let raw = read_trusted_text(path)
        .map_err(|_| format!("resolved manifest unreadable: {}", path.display()))?;
    let parsed: Value = serde_json::from_str(&raw)
        .map_err(|_| format!("resolved manifest malformed: {}", path.display()))?;
    let raw_todos = parsed
        .as_object()
        .and_then(|object| object.get("todos_left"))
        .and_then(Value::as_array)
        .ok_or_else(schema_invalid)?;
    let mut blocking = Vec::new();
    for item in raw_todos {
        let text = item.as_str().ok_or_else(schema_invalid)?;
        if !is_nonblocking_full_suite_todo(text) {
            blocking.push(text.to_owned());
        }
    }
    let mut lines: Vec<String> = Vec::new();
    let mut budget = MAX_TODO_CHARS;
    for item in blocking.iter().take(MAX_TODO_ITEMS) {
        let line = safe_line(item, 300);
        if line.is_empty() {
            continue;
        }
        if line.chars().count() + 1 > budget {
            break;
        }
        budget -= line.chars().count() + 1;
        lines.push(line);
    }
    if blocking.len() > lines.len() {
        lines.push(format!(
            "… {} more todo item(s) omitted",
            blocking.len() - lines.len()
        ));
    }
    Ok((lines, i64::try_from(blocking.len()).unwrap_or(i64::MAX)))
}

fn read_forked_target(path: &Path) -> bool {
    let Ok(text) = read_trusted_text(path) else {
        return false;
    };
    let Ok(document) = KvDocument::parse(
        &text,
        ParseOptions {
            comments: larch_core::CommentPolicy::Skip,
            ..ParseOptions::legacy()
        },
    ) else {
        return false;
    };
    document
        .select(DuplicatePolicy::Last)
        .get("FORKED_TARGET")
        .is_some_and(|value| value.as_str() == "true")
}

fn forked_target(tmpdir: &Path) -> bool {
    let ship = tmpdir.join(SHIP_PR_STATE);
    if artifact_present(&ship) {
        return read_forked_target(&ship);
    }
    let session = tmpdir.join(SESSION_ENV);
    artifact_present(&session) && read_forked_target(&session)
}

fn selected_remote(tmpdir: &Path) -> &'static str {
    if forked_target(tmpdir) {
        "upstream"
    } else {
        "origin"
    }
}

fn step2_baseline(tmpdir: &Path) -> Result<String, String> {
    let missing = || "step2 baseline missing or unreadable".to_owned();
    let raw = read_trusted_text(&tmpdir.join("step2-baseline.txt")).map_err(|_| missing())?;
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return Err(missing());
    }
    Ok(trimmed.to_owned())
}

fn resolve_baseline(tmpdir: &Path, repo_root: &Path) -> Result<BaselineResolution, String> {
    let remote = selected_remote(tmpdir);
    let repository = GixRepository::discover(repo_root)
        .map_err(|_| "repo root is not a git repository".to_owned())?;
    let remote_head = repository
        .resolve_revision(&Revision::new(
            format!("refs/remotes/{remote}/HEAD").into_bytes(),
        ))
        .ok();
    let Some(remote_head) = remote_head else {
        let sha = step2_baseline(tmpdir)?;
        eprintln!(
            "scope-disposition: unresolved {remote}/HEAD; using frozen step2 baseline {} (porcelain-only attribution)",
            safe_line(&sha, 64)
        );
        return Ok(BaselineResolution {
            sha,
            frozen_fallback_active: true,
        });
    };
    let head = repository
        .resolve_revision(&Revision::new("HEAD"))
        .map_err(|_| format!("merge-base failed for {remote}/HEAD: cannot resolve HEAD"))?;
    let merge = repository
        .merge_base(&remote_head, &head)
        .map_err(|_| format!("merge-base failed for {remote}/HEAD: no merge base"))?;
    let sha = merge.to_hex();
    if sha.is_empty() {
        return Err(format!("merge-base returned empty SHA for {remote}/HEAD"));
    }
    Ok(BaselineResolution {
        sha,
        frozen_fallback_active: false,
    })
}

fn status_paths(repo_root: &Path) -> Result<BTreeSet<String>, String> {
    let failed = || "working-tree status failed".to_owned();
    let repository = GixRepository::discover(repo_root).map_err(|_| failed())?;
    let status = repository
        .local_status(&StatusOptions {
            include_untracked: true,
            ..StatusOptions::default()
        })
        .map_err(|_| failed())?;
    let mut paths = BTreeSet::new();
    for change in status
        .tree_to_index
        .entries()
        .iter()
        .chain(status.index_to_worktree.entries().iter())
    {
        let _ = paths.insert(String::from_utf8_lossy(change.path.as_bytes()).into_owned());
        if let Some(source) = &change.source_path {
            let _ = paths.insert(String::from_utf8_lossy(source.as_bytes()).into_owned());
        }
    }
    for path in &status.untracked {
        let _ = paths.insert(String::from_utf8_lossy(path.as_bytes()).into_owned());
    }
    for entry in &status.unmerged {
        let _ = paths.insert(String::from_utf8_lossy(entry.path.as_bytes()).into_owned());
    }
    Ok(paths)
}

/// Ported `git diff --name-only <base>..<head>` over resolved commit trees.
fn diff_names(repo_root: &Path, base: &str, head: &str, label: &str) -> Result<Vec<String>, String> {
    let repository = GixRepository::discover(repo_root).map_err(|_| label.to_owned())?;
    let tree = |revision: &str| {
        repository
            .resolve_revision(&Revision::new(
                format!("{revision}^{{tree}}").into_bytes(),
            ))
            .map_err(|_| label.to_owned())
    };
    let changes = repository
        .tree_changes(&tree(base)?, &tree(head)?)
        .map_err(|_| label.to_owned())?;
    Ok(changes
        .paths()
        .map(|path| String::from_utf8_lossy(path.as_bytes()).into_owned())
        .collect())
}

fn firm_path_covered_by(firm_path: &str, touched_path: &str) -> bool {
    touched_path == firm_path || (firm_path.ends_with('/') && touched_path.starts_with(firm_path))
}

fn map_touched_to_firm(plan_paths: &[String], raw_touched: &[String]) -> Vec<String> {
    plan_paths
        .iter()
        .filter(|firm| {
            raw_touched
                .iter()
                .any(|touched| firm_path_covered_by(firm, touched))
        })
        .cloned()
        .collect()
}

fn sha256_hex(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn is_object_sha(value: &str) -> bool {
    (40..=64).contains(&value.len())
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

fn is_path_signature(value: &str) -> bool {
    value == "missing"
        || value == "unreadable"
        || (value.len() == 64
            && value
                .bytes()
                .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte)))
}

fn fallback_session_id(tmpdir: &Path) -> String {
    let Ok(text) = read_trusted_text(&tmpdir.join("session-id")) else {
        return String::new();
    };
    let trimmed = text.trim();
    if trimmed.is_empty() || trimmed.contains('\0') {
        String::new()
    } else {
        trimmed.to_owned()
    }
}

fn fallback_path_signature(repo_root: &Path, path: &str) -> String {
    let target = repo_root.join(path);
    let Ok(meta) = fs::symlink_metadata(&target) else {
        return "missing".to_owned();
    };
    if meta.file_type().is_symlink() || !meta.is_file() {
        return "missing".to_owned();
    }
    fs::read(&target).map_or_else(|_| "unreadable".to_owned(), |bytes| sha256_hex(&bytes))
}

fn fallback_provenance_path(tmpdir: &Path) -> PathBuf {
    tmpdir.join(FALLBACK_PROVENANCE)
}

fn parse_fallback_provenance(parsed: &Value) -> Option<FallbackProvenance> {
    let object = parsed.as_object()?;
    let session_id = object.get("session_id")?.as_str()?;
    let anchor_head = object.get("anchor_head")?.as_str()?;
    if session_id.is_empty() || !is_object_sha(anchor_head) {
        return None;
    }
    let mut path_signatures = BTreeMap::new();
    for (path, signature) in object.get("path_signatures")?.as_object()? {
        let signature = signature.as_str()?;
        if path.is_empty() || path.contains('\0') || !is_path_signature(signature) {
            return None;
        }
        let _ = path_signatures.insert(path.clone(), signature.to_owned());
    }
    Some(FallbackProvenance {
        session_id: session_id.to_owned(),
        anchor_head: anchor_head.to_owned(),
        path_signatures,
    })
}

fn read_fallback_provenance(tmpdir: &Path) -> Option<FallbackProvenance> {
    let path = fallback_provenance_path(tmpdir);
    if !artifact_present(&path) {
        return None;
    }
    let text = read_trusted_text(&path).ok()?;
    parse_fallback_provenance(&serde_json::from_str::<Value>(&text).ok()?)
}

fn write_fallback_provenance(
    tmpdir: &Path,
    provenance: &FallbackProvenance,
) -> Result<(), String> {
    let mut payload = Map::new();
    let _ = payload.insert("schema_version".to_owned(), Value::from("3"));
    let _ = payload.insert(
        "session_id".to_owned(),
        Value::from(provenance.session_id.clone()),
    );
    let _ = payload.insert(
        "anchor_head".to_owned(),
        Value::from(provenance.anchor_head.clone()),
    );
    let _ = payload.insert(
        "path_signatures".to_owned(),
        Value::Object(
            provenance
                .path_signatures
                .iter()
                .map(|(path, signature)| (path.clone(), Value::from(signature.clone())))
                .collect(),
        ),
    );
    write_trusted(
        &fallback_provenance_path(tmpdir),
        &json_text(&Value::Object(payload)),
        tmpdir,
    )
}

/// Attribute coverage from current porcelain and this run's own commits only.
fn frozen_fallback_touched_paths(
    tmpdir: &Path,
    repo_root: &Path,
    plan_paths: &[String],
) -> Result<Vec<String>, String> {
    let porcelain_plan: BTreeSet<String> = status_paths(repo_root)?
        .into_iter()
        .filter(|path| {
            plan_paths
                .iter()
                .any(|firm| firm_path_covered_by(firm, path))
        })
        .collect();
    let session_id = fallback_session_id(tmpdir);
    let repository = GixRepository::discover(repo_root)
        .map_err(|_| "repo root is not a git repository".to_owned())?;
    let Some(current_head) = repository
        .resolve_revision(&Revision::new("HEAD"))
        .ok()
        .map(|head| head.to_hex())
        .filter(|head| is_object_sha(head))
    else {
        return Ok(porcelain_plan.into_iter().collect());
    };
    let active = read_fallback_provenance(tmpdir)
        .filter(|provenance| provenance.session_id == session_id);
    let mut committed_plan: BTreeSet<String> = BTreeSet::new();
    if let Some(provenance) = &active {
        for path in diff_names(
            repo_root,
            &provenance.anchor_head,
            &current_head,
            "frozen fallback anchor-to-HEAD diff failed",
        )? {
            if provenance.path_signatures.get(&path)
                == Some(&fallback_path_signature(repo_root, &path))
            {
                let _ = committed_plan.insert(path);
            }
        }
    }
    if session_id.is_empty() {
        return Ok(committed_plan.into_iter().collect());
    }
    let mut path_signatures = active
        .as_ref()
        .map(|provenance| provenance.path_signatures.clone())
        .unwrap_or_default();
    for path in &porcelain_plan {
        let _ = path_signatures.insert(path.clone(), fallback_path_signature(repo_root, path));
    }
    write_fallback_provenance(
        tmpdir,
        &FallbackProvenance {
            session_id,
            anchor_head: active
                .as_ref()
                .map_or_else(|| current_head.clone(), |value| value.anchor_head.clone()),
            path_signatures,
        },
    )?;
    Ok(porcelain_plan
        .into_iter()
        .chain(committed_plan)
        .collect::<BTreeSet<String>>()
        .into_iter()
        .collect())
}

fn live_touched_paths(repo_root: &Path, baseline_sha: &str) -> Result<Vec<String>, String> {
    let mut touched = status_paths(repo_root)?;
    touched.extend(diff_names(
        repo_root,
        baseline_sha,
        "HEAD",
        "baseline-to-HEAD diff failed",
    )?);
    Ok(touched.into_iter().filter(|path| !path.is_empty()).collect())
}

fn touched_paths_since_baseline(
    tmpdir: &Path,
    repo_root: &Path,
    plan_paths: &[String],
) -> Result<Vec<String>, String> {
    let resolution = resolve_baseline(tmpdir, repo_root)?;
    if resolution.frozen_fallback_active {
        frozen_fallback_touched_paths(tmpdir, repo_root, plan_paths)
    } else {
        live_touched_paths(repo_root, &resolution.sha)
    }
}

fn firm_plan_paths(plan_file: &Path) -> Result<Vec<String>, String> {
    let text = read_trusted_text(plan_file)
        .map_err(|_| format!("plan file unreadable: {}", plan_file.display()))?;
    Ok(extract_firm_scope_paths(&text))
}

fn coverage_band(total: i64, untouched: i64) -> String {
    let percent = if total > 0 { untouched * 100 / total } else { 0 };
    if total > 0 && (untouched >= HIGH_COUNT || percent >= HIGH_PERCENT) {
        return "high".to_owned();
    }
    if total > 0 && (untouched >= MIDDLE_COUNT || percent >= MIDDLE_PERCENT) {
        return "middle".to_owned();
    }
    "advisory".to_owned()
}

/// Escape non-ASCII scalars the way Python's `json.dumps` default does.
fn ensure_ascii(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for character in text.chars() {
        if character.is_ascii() {
            out.push(character);
            continue;
        }
        let mut units = [0u16; 2];
        for unit in character.encode_utf16(&mut units) {
            let _ = write!(out, "\\u{unit:04x}");
        }
    }
    out
}

/// Render `prefix`-tagged inventory lines the way the companion artifacts store them.
fn prefixed_lines(items: &[String], prefix: &str) -> String {
    items.iter().fold(String::new(), |mut text, item| {
        let _ = writeln!(text, "{prefix}{item}");
        text
    })
}

fn env_text(rows: &[(&'static str, String)]) -> String {
    rows.iter().fold(String::new(), |mut text, (key, value)| {
        let _ = writeln!(text, "{key}={value}");
        text
    })
}

fn string_array(values: &[String]) -> Value {
    Value::Array(values.iter().map(|value| Value::from(value.clone())).collect())
}

fn fingerprint(plan_paths: &[String], touched_paths: &[String], todos_left: &[String]) -> String {
    let mut payload = Map::new();
    let _ = payload.insert("plan_paths".to_owned(), string_array(plan_paths));
    let _ = payload.insert("todos_left".to_owned(), string_array(todos_left));
    let _ = payload.insert("touched_paths".to_owned(), string_array(touched_paths));
    let compact = serde_json::to_string(&Value::Object(payload)).unwrap_or_default();
    sha256_hex(ensure_ascii(&compact).as_bytes())
}

fn compute_coverage(
    tmpdir: &Path,
    repo_root: &Path,
    plan_file: Option<&Path>,
    manifest: Option<&Path>,
) -> Result<PlanCoverage, String> {
    let effective_plan = plan_file.map_or_else(|| tmpdir.join("plan.txt"), Path::to_path_buf);
    let plan_paths = firm_plan_paths(&effective_plan)?;
    let raw_touched = touched_paths_since_baseline(tmpdir, repo_root, &plan_paths)?;
    // Coverage and its fingerprint must stay stable across relaunches, so only
    // firm plan paths count: raw touched files carry the selected remote's own
    // evolution plus this driver's log-flush commits, which drift every launch.
    let touched_paths = map_touched_to_firm(&plan_paths, &raw_touched);
    let untouched_paths: Vec<String> = plan_paths
        .iter()
        .filter(|path| !touched_paths.contains(path))
        .cloned()
        .collect();
    let total = i64::try_from(plan_paths.len()).unwrap_or(i64::MAX);
    let untouched = i64::try_from(untouched_paths.len()).unwrap_or(i64::MAX);
    let untouched_percent = if total > 0 { untouched * 100 / total } else { 0 };
    let band = coverage_band(total, untouched);
    let (todos_left, todos_left_count) = read_manifest_todos(manifest)?;
    Ok(PlanCoverage {
        total,
        touched: total - untouched,
        untouched,
        untouched_percent,
        plan_fidelity_forced: band == "middle" || band == "high",
        disposition_required: band == "high" || todos_left_count > 0,
        band,
        fingerprint: fingerprint(&plan_paths, &touched_paths, &todos_left),
        plan_paths,
        touched_paths,
        untouched_paths,
        todos_left_count,
        todos_left,
        coverage_file: tmpdir.join(COVERAGE_JSON).display().to_string(),
        untouched_file: tmpdir.join(UNTOUCHED_PATHS).display().to_string(),
        todos_file: tmpdir.join(TODOS_LEFT).display().to_string(),
    })
}

fn coverage_value(coverage: &PlanCoverage) -> Value {
    let mut object = Map::new();
    let mut put = |key: &str, value: Value| {
        let _ = object.insert(key.to_owned(), value);
    };
    put("band", Value::from(coverage.band.clone()));
    put("coverage_file", Value::from(coverage.coverage_file.clone()));
    put(
        "disposition_required",
        Value::Bool(coverage.disposition_required),
    );
    put("fingerprint", Value::from(coverage.fingerprint.clone()));
    put(
        "plan_fidelity_forced",
        Value::Bool(coverage.plan_fidelity_forced),
    );
    put("plan_paths", string_array(&coverage.plan_paths));
    put("todos_file", Value::from(coverage.todos_file.clone()));
    put("todos_left", string_array(&coverage.todos_left));
    put("todos_left_count", Value::from(coverage.todos_left_count));
    put("total", Value::from(coverage.total));
    put("touched", Value::from(coverage.touched));
    put("touched_paths", string_array(&coverage.touched_paths));
    put("untouched", Value::from(coverage.untouched));
    put("untouched_file", Value::from(coverage.untouched_file.clone()));
    put("untouched_paths", string_array(&coverage.untouched_paths));
    put("untouched_percent", Value::from(coverage.untouched_percent));
    Value::Object(object)
}

fn coverage_env_rows(coverage: &PlanCoverage) -> Vec<(&'static str, String)> {
    vec![
        ("PLAN_COVERAGE_TOTAL", coverage.total.to_string()),
        ("PLAN_COVERAGE_TOUCHED", coverage.touched.to_string()),
        ("PLAN_COVERAGE_UNTOUCHED", coverage.untouched.to_string()),
        (
            "PLAN_COVERAGE_UNTOUCHED_PERCENT",
            coverage.untouched_percent.to_string(),
        ),
        ("PLAN_COVERAGE_BAND", coverage.band.clone()),
        ("PLAN_COVERAGE_FILE", coverage.coverage_file.clone()),
        (
            "PLAN_COVERAGE_UNTOUCHED_FILE",
            coverage.untouched_file.clone(),
        ),
        ("TODOS_LEFT_COUNT", coverage.todos_left_count.to_string()),
        ("TODOS_LEFT_FILE", coverage.todos_file.clone()),
        ("PLAN_COVERAGE_FINGERPRINT", coverage.fingerprint.clone()),
        (
            "PLAN_COVERAGE_DISPOSITION_REQUIRED",
            coverage.disposition_required.to_string(),
        ),
        (
            "PLAN_FIDELITY_FORCED",
            coverage.plan_fidelity_forced.to_string(),
        ),
    ]
}

fn write_coverage(coverage: &PlanCoverage, tmpdir: &Path) -> Result<(), String> {
    write_trusted(
        Path::new(&coverage.untouched_file),
        &prefixed_lines(&coverage.untouched_paths, ""),
        tmpdir,
    )?;
    write_trusted(
        Path::new(&coverage.todos_file),
        &prefixed_lines(&coverage.todos_left, "- "),
        tmpdir,
    )?;
    write_trusted(
        &tmpdir.join(COVERAGE_JSON),
        &json_text(&coverage_value(coverage)),
        tmpdir,
    )?;
    // The env file is the completion artifact; publish it after its companions.
    write_trusted(
        &tmpdir.join(COVERAGE_ENV),
        &env_text(&coverage_env_rows(coverage)),
        tmpdir,
    )
}

fn compute_and_write(
    tmpdir: &Path,
    repo_root: &Path,
    plan_file: Option<&Path>,
    manifest: Option<&Path>,
) -> Result<PlanCoverage, String> {
    let coverage = compute_coverage(tmpdir, repo_root, plan_file, manifest)?;
    write_coverage(&coverage, tmpdir)?;
    Ok(coverage)
}

fn as_int(value: Option<&Value>) -> i64 {
    match value {
        Some(Value::String(text)) => text.parse().unwrap_or(0),
        Some(other) => other.as_i64().unwrap_or(0),
        None => 0,
    }
}

fn as_bool(value: Option<&Value>) -> bool {
    match value {
        Some(Value::Bool(flag)) => *flag,
        Some(Value::String(text)) => text.to_lowercase() == "true",
        _ => false,
    }
}

fn as_strings(value: Option<&Value>) -> Vec<String> {
    value
        .and_then(Value::as_array)
        .map(|items| {
            items
                .iter()
                .map(|item| {
                    item.as_str()
                        .map_or_else(|| item.to_string(), str::to_owned)
                })
                .collect()
        })
        .unwrap_or_default()
}

fn as_text(value: Option<&Value>) -> String {
    value
        .and_then(Value::as_str)
        .map(str::to_owned)
        .unwrap_or_default()
}

fn coverage_from_value(parsed: &Value, tmpdir: &Path) -> Result<PlanCoverage, String> {
    let object = parsed
        .as_object()
        .ok_or_else(|| "coverage artifact schema-invalid".to_owned())?;
    let coverage = PlanCoverage {
        total: as_int(object.get("total")),
        touched: as_int(object.get("touched")),
        untouched: as_int(object.get("untouched")),
        untouched_percent: as_int(object.get("untouched_percent")),
        band: as_text(object.get("band")),
        plan_paths: as_strings(object.get("plan_paths")),
        touched_paths: as_strings(object.get("touched_paths")),
        untouched_paths: as_strings(object.get("untouched_paths")),
        todos_left_count: as_int(object.get("todos_left_count")),
        todos_left: as_strings(object.get("todos_left")),
        fingerprint: as_text(object.get("fingerprint")),
        disposition_required: as_bool(object.get("disposition_required")),
        plan_fidelity_forced: as_bool(object.get("plan_fidelity_forced")),
        coverage_file: as_text(object.get("coverage_file")),
        untouched_file: as_text(object.get("untouched_file")),
        todos_file: as_text(object.get("todos_file")),
    };
    if !matches!(coverage.band.as_str(), "advisory" | "middle" | "high") {
        return Err("coverage artifact has an invalid band".to_owned());
    }
    if Path::new(&coverage.coverage_file) != tmpdir.join(COVERAGE_JSON)
        || Path::new(&coverage.untouched_file) != tmpdir.join(UNTOUCHED_PATHS)
        || Path::new(&coverage.todos_file) != tmpdir.join(TODOS_LEFT)
    {
        return Err("coverage artifact contains mismatched companion paths".to_owned());
    }
    let expected_untouched: Vec<String> = coverage
        .plan_paths
        .iter()
        .filter(|path| {
            !coverage
                .touched_paths
                .iter()
                .any(|touched| firm_path_covered_by(path, touched))
        })
        .cloned()
        .collect();
    let expected_percent = if coverage.total > 0 {
        coverage.untouched * 100 / coverage.total
    } else {
        0
    };
    let inconsistent = coverage.total != i64::try_from(coverage.plan_paths.len()).unwrap_or(i64::MAX)
        || coverage.untouched_paths != expected_untouched
        || coverage.untouched != i64::try_from(expected_untouched.len()).unwrap_or(i64::MAX)
        || coverage.touched != coverage.total - coverage.untouched
        || coverage.untouched_percent != expected_percent
        || coverage.band != coverage_band(coverage.total, coverage.untouched)
        || coverage.todos_left_count < i64::try_from(coverage.todos_left.len()).unwrap_or(i64::MAX)
        || coverage.fingerprint
            != fingerprint(
                &coverage.plan_paths,
                &coverage.touched_paths,
                &coverage.todos_left,
            )
        || coverage.disposition_required != (coverage.band == "high" || coverage.todos_left_count > 0)
        || coverage.plan_fidelity_forced
            != (coverage.band == "middle" || coverage.band == "high");
    if inconsistent {
        return Err("coverage artifact is internally inconsistent".to_owned());
    }
    Ok(coverage)
}

/// Report whether `path` is a trusted regular file, refusing a symlink.
fn trusted_present(path: &Path) -> Result<bool, String> {
    match fs::symlink_metadata(path) {
        Err(_) => Ok(false),
        Ok(meta) if meta.file_type().is_symlink() => Err(format!(
            "unsafe coverage artifact: {} is a symlink",
            path.display()
        )),
        Ok(meta) => Ok(meta.is_file()),
    }
}

fn load_coverage(tmpdir: &Path) -> Result<Option<PlanCoverage>, String> {
    let paths = [
        tmpdir.join(COVERAGE_JSON),
        tmpdir.join(COVERAGE_ENV),
        tmpdir.join(UNTOUCHED_PATHS),
        tmpdir.join(TODOS_LEFT),
    ];
    if !paths.iter().any(|path| artifact_present(path)) {
        return Ok(None);
    }
    let mut present = Vec::new();
    for path in &paths {
        present.push(trusted_present(path)?);
    }
    if !present.iter().all(|flag| *flag) {
        return Err("coverage artifact set is partial".to_owned());
    }
    let malformed =
        |detail: &str| format!("coverage artifact unreadable or malformed: {detail}");
    let parsed: Value = serde_json::from_str(&read_trusted_text(&paths[0])?)
        .map_err(|error| malformed(&safe_line(&error.to_string(), 300)))?;
    let coverage = coverage_from_value(&parsed, tmpdir)?;
    let untouched_text = read_trusted_text(&paths[2])?;
    let todos_text = read_trusted_text(&paths[3])?;
    let env = KvDocument::parse(&read_trusted_text(&paths[1])?, ParseOptions::legacy())
        .map_err(|error| malformed(&safe_line(&error.to_string(), 300)))?
        .select(DuplicatePolicy::Last);
    if untouched_text != prefixed_lines(&coverage.untouched_paths, "") {
        return Err("coverage untouched inventory mismatch".to_owned());
    }
    if todos_text != prefixed_lines(&coverage.todos_left, "- ") {
        return Err("coverage todo inventory mismatch".to_owned());
    }
    if coverage_env_rows(&coverage)
        .into_iter()
        .any(|(key, value)| env.get(key) != Some(&value))
    {
        return Err("coverage env companion mismatch".to_owned());
    }
    Ok(Some(coverage))
}

fn load_live_coverage(
    tmpdir: &Path,
    repo_root: &Path,
    manifest: Option<&Path>,
) -> Result<Option<PlanCoverage>, String> {
    let Some(persisted) = load_coverage(tmpdir)? else {
        return Ok(None);
    };
    let resolved = resolve_implement_manifest(tmpdir, manifest)?;
    let live = compute_coverage(tmpdir, repo_root, None, resolved.as_deref())?;
    if persisted == live {
        Ok(Some(persisted))
    } else {
        Err(STALE_LIVE.to_owned())
    }
}

fn disposition_path(tmpdir: &Path) -> PathBuf {
    tmpdir.join(DISPOSITION_JSON)
}

fn load_disposition(
    tmpdir: &Path,
    coverage: Option<&PlanCoverage>,
) -> Result<Option<DispositionRecord>, String> {
    let path = disposition_path(tmpdir);
    if !artifact_present(&path) {
        return Ok(None);
    }
    if !trusted_present(&path)? {
        return Err("scope disposition is not a trusted regular file".to_owned());
    }
    let parsed: Value = serde_json::from_str(&read_trusted_text(&path)?).map_err(|error| {
        format!(
            "scope disposition unreadable or unsafe: {}",
            safe_line(&error.to_string(), 300)
        )
    })?;
    let object = parsed
        .as_object()
        .ok_or_else(|| "scope disposition schema-invalid".to_owned())?;
    let disposition = as_text(object.get("disposition"));
    if !DISPOSITIONS.contains(&disposition.as_str()) {
        return Err("scope disposition has invalid disposition".to_owned());
    }
    let record = DispositionRecord {
        disposition,
        fingerprint: as_text(object.get("fingerprint")),
        followup_issue_number: as_text(object.get("followup_issue_number")),
        followup_issue_url: as_text(object.get("followup_issue_url")),
        coverage_file: as_text(object.get("coverage_file")),
    };
    if let Some(coverage) = coverage
        && (record.fingerprint != coverage.fingerprint
            || record.coverage_file != coverage.coverage_file)
    {
        return Err("scope disposition does not match trusted coverage".to_owned());
    }
    Ok(Some(record))
}

fn resolve_implement_manifest(
    tmpdir: &Path,
    manifest: Option<&Path>,
) -> Result<Option<PathBuf>, String> {
    if let Some(manifest) = manifest {
        if artifact_present(manifest) {
            return Ok(Some(manifest.to_path_buf()));
        }
        return Err("declared implement manifest is missing".to_owned());
    }
    Ok([
        tmpdir.join("manifest.json"),
        tmpdir.join("codex-step2-out").join("manifest.json"),
    ]
    .into_iter()
    .find(|candidate| artifact_present(candidate)))
}

fn is_pr_mutation_gate_relevant(tmpdir: &Path, manifest: Option<&Path>) -> bool {
    [
        tmpdir.join("plan.txt"),
        tmpdir.join(COVERAGE_JSON),
        disposition_path(tmpdir),
    ]
    .iter()
    .any(|candidate| artifact_present(candidate))
        || manifest.is_some_and(artifact_present)
}

fn render_deferred_inventory(
    coverage: &PlanCoverage,
    disposition: Option<&DispositionRecord>,
) -> String {
    if coverage.untouched_paths.is_empty() && coverage.todos_left.is_empty() {
        return String::new();
    }
    let mut lines = vec!["## Deferred plan inventory".to_owned(), String::new()];
    if let Some(record) = disposition
        && !record.followup_issue_number.is_empty()
    {
        lines.push(format!("Follow-up issue: #{}", record.followup_issue_number));
        lines.push(String::new());
    }
    if !coverage.untouched_paths.is_empty() {
        lines.push("Untouched firm plan paths:".to_owned());
        lines.extend(
            coverage
                .untouched_paths
                .iter()
                .take(MAX_UNTOUCHED_INVENTORY)
                .map(|path| format!("- `{path}`")),
        );
        if coverage.untouched_paths.len() > MAX_UNTOUCHED_INVENTORY {
            lines.push(format!(
                "- … {} more path(s)",
                coverage.untouched_paths.len() - MAX_UNTOUCHED_INVENTORY
            ));
        }
        lines.push(String::new());
    }
    if !coverage.todos_left.is_empty() {
        lines.push("Manifest todos left:".to_owned());
        lines.extend(coverage.todos_left.iter().map(|line| format!("- {line}")));
        lines.push(String::new());
    }
    format!("{}\n", lines.join("\n").trim_end())
}

fn deferred_inventory(
    tmpdir: &Path,
    repo_root: &Path,
    manifest: Option<&Path>,
) -> Result<String, String> {
    let resolved = resolve_implement_manifest(tmpdir, manifest)?;
    let Some(coverage) = load_live_coverage(tmpdir, repo_root, resolved.as_deref())? else {
        return refuse_disposition_without_coverage(tmpdir);
    };
    let record = load_disposition(tmpdir, Some(&coverage))?;
    Ok(render_deferred_inventory(&coverage, record.as_ref()))
}

/// A durable disposition with no trusted coverage is an integrity failure.
fn refuse_disposition_without_coverage(tmpdir: &Path) -> Result<String, String> {
    if artifact_present(&disposition_path(tmpdir)) {
        let _ = load_disposition(tmpdir, None)?;
        return Err(NO_TRUSTED_COVERAGE.to_owned());
    }
    Ok(String::new())
}

fn emit_coverage(coverage: &PlanCoverage) {
    for (key, value) in coverage_contract_rows(coverage) {
        emit_kv(key, &value);
    }
    emit_kv("PLAN_COVERAGE_FINGERPRINT", &coverage.fingerprint);
}

/// The coverage rows shared by every consumer of this measurement.
fn coverage_contract_rows(coverage: &PlanCoverage) -> Vec<(&'static str, String)> {
    vec![
        ("PLAN_COVERAGE_TOTAL", coverage.total.to_string()),
        ("PLAN_COVERAGE_TOUCHED", coverage.touched.to_string()),
        ("PLAN_COVERAGE_UNTOUCHED", coverage.untouched.to_string()),
        (
            "PLAN_COVERAGE_UNTOUCHED_PERCENT",
            coverage.untouched_percent.to_string(),
        ),
        ("PLAN_COVERAGE_BAND", coverage.band.clone()),
        ("PLAN_COVERAGE_FILE", coverage.coverage_file.clone()),
        (
            "PLAN_COVERAGE_UNTOUCHED_FILE",
            coverage.untouched_file.clone(),
        ),
        ("TODOS_LEFT_COUNT", coverage.todos_left_count.to_string()),
        ("TODOS_LEFT_FILE", coverage.todos_file.clone()),
        (
            "PLAN_COVERAGE_DISPOSITION_REQUIRED",
            coverage.disposition_required.to_string(),
        ),
        (
            "PLAN_FIDELITY_FORCED",
            coverage.plan_fidelity_forced.to_string(),
        ),
    ]
}

fn validate_for_ship(
    tmpdir: &Path,
    repo_root: &Path,
    manifest: Option<&Path>,
) -> Result<ValidationResult, String> {
    let resolved = resolve_implement_manifest(tmpdir, manifest)?;
    let gate_relevant = is_pr_mutation_gate_relevant(tmpdir, resolved.as_deref());
    let coverage = match load_live_coverage(tmpdir, repo_root, resolved.as_deref()).and_then(
        |persisted| {
            persisted.map_or_else(
                || compute_and_write(tmpdir, repo_root, None, resolved.as_deref()),
                Ok,
            )
        },
    ) {
        Ok(coverage) => coverage,
        Err(error) => {
            let stale = error.contains("does not match live repository inputs")
                && artifact_present(&disposition_path(tmpdir));
            let reason = if stale {
                "scope-disposition-stale".to_owned()
            } else {
                format!("coverage-recompute-failed: {}", safe_line(&error, 300))
            };
            return Ok(ValidationResult {
                ok: false,
                required: gate_relevant || stale,
                reason,
                coverage: None,
            });
        }
    };
    let record = match load_disposition(tmpdir, Some(&coverage)) {
        Ok(record) => record,
        Err(error) => {
            let reason = if error.contains("does not match trusted coverage") {
                "scope-disposition-stale".to_owned()
            } else {
                format!("scope-disposition-invalid: {}", safe_line(&error, 300))
            };
            return Ok(ValidationResult {
                ok: false,
                required: true,
                reason,
                coverage: Some(coverage),
            });
        }
    };
    if !coverage.disposition_required {
        return Ok(ValidationResult {
            ok: true,
            required: false,
            reason: String::new(),
            coverage: Some(coverage),
        });
    }
    let reason = match record.as_ref().map(|value| value.disposition.as_str()) {
        None => "scope-disposition-missing",
        Some("bail-rescope") => "scope-disposition-bail-rescope",
        Some(_) => "",
    };
    Ok(ValidationResult {
        ok: reason.is_empty(),
        required: true,
        reason: reason.to_owned(),
        coverage: Some(coverage),
    })
}

fn verified_larch(repo_root: &Path, args: &[OsString]) -> Result<ProcessOutput, String> {
    let root = resolve_plugin_root()?;
    delegate_verified_larch(repo_root, &root, args)
}

fn require_cli_success(
    output: &ProcessOutput,
    label: &str,
) -> Result<BTreeMap<String, String>, String> {
    let stdout = String::from_utf8_lossy(output.stdout()).into_owned();
    let stderr = String::from_utf8_lossy(output.stderr()).into_owned();
    let fields = KvDocument::parse(&stdout, ParseOptions::legacy())
        .map(|document| document.select(DuplicatePolicy::Last))
        .unwrap_or_default();
    let failed = fields
        .iter()
        .any(|(key, value)| key.ends_with("FAILED") && value == "true");
    if output.status().code().unwrap_or(1) != 0 || failed {
        let detail = fields
            .get("ERROR")
            .filter(|value| !value.is_empty())
            .cloned()
            .or_else(|| Some(stderr).filter(|value| !value.trim().is_empty()))
            .or_else(|| Some(stdout).filter(|value| !value.trim().is_empty()))
            .unwrap_or_else(|| format!("{label} failed"));
        return Err(safe_line(&detail, 500));
    }
    Ok(fields)
}

/// Build the session authorization argv tail for a nested issue mutation.
fn session_mutation_auth_args(tmpdir: &Path) -> Vec<OsString> {
    let session_env = tmpdir.join(SESSION_ENV);
    if !session_env.is_file() {
        return Vec::new();
    }
    let text = fs::read_to_string(&session_env).unwrap_or_default();
    let run_id = text
        .split_once("LARCH_RUN_ID=")
        .map_or(text.as_str(), |(_, rest)| rest)
        .lines()
        .next()
        .unwrap_or_default()
        .trim()
        .to_owned();
    vec![
        "--context-file".into(),
        session_env.into_os_string(),
        "--run-id".into(),
        run_id.into(),
        "--trusted-root".into(),
        tmpdir.as_os_str().to_owned(),
    ]
}

fn create_followup_issue(
    tmpdir: &Path,
    repo_root: &Path,
    repo: &str,
    tracking_issue: &str,
    coverage: &PlanCoverage,
) -> Result<(String, String), String> {
    let body = tmpdir.join("scope-disposition-followup-body.md");
    write_trusted(
        &body,
        &format!(
            "# Deferred /implement plan inventory\n\nParent tracking issue: #{tracking_issue}\n\n{}",
            render_deferred_inventory(coverage, None)
        ),
        tmpdir,
    )?;
    let mut args: Vec<OsString> = vec![
        "issue".into(),
        "create-one".into(),
        "--title".into(),
        "Complete deferred /implement plan work".into(),
        "--title-prefix".into(),
        "[FOLLOW-UP]".into(),
        "--body-file".into(),
        body.into_os_string(),
        "--repo".into(),
        repo.into(),
    ];
    args.extend(session_mutation_auth_args(tmpdir));
    let fields = require_cli_success(&verified_larch(repo_root, &args)?, "issue create-one")?;
    let number = fields.get("ISSUE_NUMBER").cloned().unwrap_or_default();
    let url = fields.get("ISSUE_URL").cloned().unwrap_or_default();
    if number.is_empty() || !number.bytes().all(|byte| byte.is_ascii_digit()) || url.is_empty() {
        return Err("issue create-one did not return ISSUE_NUMBER and ISSUE_URL".to_owned());
    }
    Ok((number, url))
}

fn append_cross_links(
    tmpdir: &Path,
    repo_root: &Path,
    repo: &str,
    tracking_issue: &str,
    followup: &(String, String),
) -> Result<(), String> {
    let parent_body = tmpdir.join("scope-disposition-parent-link.md");
    let child_body = tmpdir.join("scope-disposition-followup-link.md");
    write_trusted(
        &parent_body,
        &format!(
            "Partial-scope disposition recorded. Deferred plan work is tracked in #{}: {}\n",
            followup.0, followup.1
        ),
        tmpdir,
    )?;
    write_trusted(
        &child_body,
        &format!(
            "Filed from partial-scope disposition on parent tracking issue #{tracking_issue}.\n"
        ),
        tmpdir,
    )?;
    for (issue, body) in [
        (tracking_issue.to_owned(), parent_body),
        (followup.0.clone(), child_body),
    ] {
        let args: Vec<OsString> = vec![
            "tracking-issue".into(),
            "append-comment".into(),
            "--issue".into(),
            issue.into(),
            "--body-file".into(),
            body.into_os_string(),
            "--repo".into(),
            repo.into(),
        ];
        let _ = require_cli_success(
            &verified_larch(repo_root, &args)?,
            "tracking-issue append-comment",
        )?;
    }
    Ok(())
}

fn add_block_relation(
    tmpdir: &Path,
    repo_root: &Path,
    repo: &str,
    tracking_issue: &str,
    followup: &(String, String),
) -> Result<(), String> {
    let mut args: Vec<OsString> = vec![
        "issue".into(),
        "add-blocked-by".into(),
        "--client-issue".into(),
        tracking_issue.into(),
        "--blocker-issue".into(),
        followup.0.clone().into(),
        "--repo".into(),
        repo.into(),
    ];
    args.extend(session_mutation_auth_args(tmpdir));
    let _ = require_cli_success(&verified_larch(repo_root, &args)?, "issue add-blocked-by")?;
    Ok(())
}

fn write_scope_run_log(
    tmpdir: &Path,
    repo_root: &Path,
    run_id: &str,
    record: &DispositionRecord,
    coverage: &PlanCoverage,
) -> Result<(), String> {
    if run_id.is_empty() {
        return Ok(());
    }
    let payload = tmpdir.join("scope-disposition-run-log.json");
    let mut object = Map::new();
    let mut put = |key: &str, value: Value| {
        let _ = object.insert(key.to_owned(), value);
    };
    put(
        "coverage_fingerprint",
        Value::from(coverage.fingerprint.clone()),
    );
    put("disposition", Value::from(record.disposition.clone()));
    put(
        "followup_issue_number",
        Value::from(record.followup_issue_number.clone()),
    );
    put(
        "followup_issue_url",
        Value::from(record.followup_issue_url.clone()),
    );
    put("todos_left_count", Value::from(coverage.todos_left_count));
    put("untouched_count", Value::from(coverage.untouched));
    put("total", Value::from(coverage.total));
    write_trusted(&payload, &json_text(&Value::Object(object)), tmpdir)?;
    let args: Vec<OsString> = vec![
        "run-log".into(),
        "write".into(),
        "--log-root".into(),
        tmpdir.join("larch-logs").into_os_string(),
        "--skill".into(),
        "implement".into(),
        "--run-id".into(),
        run_id.into(),
        "--batch".into(),
        "scope-disposition".into(),
        "--input-file".into(),
        payload.into_os_string(),
    ];
    let _ = require_cli_success(
        &verified_larch(repo_root, &args)?,
        "run-log write scope-disposition",
    )?;
    Ok(())
}

/// Reuse the follow-up already filed for this exact coverage fingerprint.
fn existing_matching_followup(tmpdir: &Path, fingerprint: &str) -> Option<(String, String)> {
    let record = load_disposition(tmpdir, None).ok()??;
    (record.disposition == "proceed-partial"
        && record.fingerprint == fingerprint
        && !record.followup_issue_number.is_empty())
    .then_some((record.followup_issue_number, record.followup_issue_url))
}

fn record_disposition(
    tmpdir: &Path,
    disposition: &str,
    repo_root: &Path,
    manifest: Option<&Path>,
    repo: &str,
    tracking_issue: &str,
    run_id: &str,
) -> Result<DispositionRecord, String> {
    let coverage = load_live_coverage(tmpdir, repo_root, manifest)?
        .ok_or_else(|| "scope disposition requires a readable coverage artifact".to_owned())?;
    let mut followup = (String::new(), String::new());
    if disposition == "proceed-partial" {
        if repo.is_empty()
            || tracking_issue.is_empty()
            || !tracking_issue.bytes().all(|byte| byte.is_ascii_digit())
        {
            return Err("proceed-partial requires --repo and --tracking-issue".to_owned());
        }
        if let Some(existing) = existing_matching_followup(tmpdir, &coverage.fingerprint) {
            followup = existing;
        } else {
            followup =
                create_followup_issue(tmpdir, repo_root, repo, tracking_issue, &coverage)?;
            append_cross_links(tmpdir, repo_root, repo, tracking_issue, &followup)?;
            add_block_relation(tmpdir, repo_root, repo, tracking_issue, &followup)?;
        }
    }
    let record = DispositionRecord {
        disposition: disposition.to_owned(),
        fingerprint: coverage.fingerprint.clone(),
        followup_issue_number: followup.0,
        followup_issue_url: followup.1,
        coverage_file: coverage.coverage_file.clone(),
    };
    write_scope_run_log(tmpdir, repo_root, run_id, &record, &coverage)?;
    let mut object = Map::new();
    let _ = object.insert(
        "coverage_file".to_owned(),
        Value::from(record.coverage_file.clone()),
    );
    let _ = object.insert(
        "disposition".to_owned(),
        Value::from(record.disposition.clone()),
    );
    let _ = object.insert(
        "fingerprint".to_owned(),
        Value::from(record.fingerprint.clone()),
    );
    let _ = object.insert(
        "followup_issue_number".to_owned(),
        Value::from(record.followup_issue_number.clone()),
    );
    let _ = object.insert(
        "followup_issue_url".to_owned(),
        Value::from(record.followup_issue_url.clone()),
    );
    write_trusted(
        &disposition_path(tmpdir),
        &json_text(&Value::Object(object)),
        tmpdir,
    )?;
    Ok(record)
}

/// Resolve the consumer root a session persisted, without ambient state.
fn resolve_persisted_repo_root(tmpdir: &Path) -> Option<PathBuf> {
    for name in ["source-env.sh", SESSION_ENV] {
        let Ok(text) = fs::read_to_string(tmpdir.join(name)) else {
            continue;
        };
        for line in text.lines() {
            for prefix in ["REPO_ROOT=", "export REPO_ROOT="] {
                let Some(raw) = line.strip_prefix(prefix) else {
                    continue;
                };
                let candidate = PathBuf::from(raw.trim().trim_matches(['\'', '"']));
                if candidate.is_absolute()
                    && candidate.is_dir()
                    && let Ok(resolved) = fs::canonicalize(&candidate)
                {
                    return Some(resolved);
                }
            }
        }
    }
    None
}

fn plan_coverage_summary_line(
    tmpdir: &Path,
    manifest: Option<&Path>,
) -> Result<String, String> {
    let Some(repo_root) = resolve_persisted_repo_root(tmpdir) else {
        if load_coverage(tmpdir)?.is_none() {
            return refuse_disposition_without_coverage(tmpdir);
        }
        return Err("persisted repository root is required for coverage validation".to_owned());
    };
    let coverage = match load_live_coverage(tmpdir, &repo_root, manifest) {
        Ok(coverage) => coverage,
        Err(error) if error == STALE_LIVE => {
            // The final report runs after merge, where the live fingerprint no
            // longer matches by design. Only a sentinelled post-merge run may
            // degrade to an empty line.
            if !tmpdir.join("post-merge-sentinel").is_file() {
                return Err(error);
            }
            let persisted = load_coverage(tmpdir)?.ok_or_else(|| STALE_LIVE.to_owned())?;
            let _ = load_disposition(tmpdir, Some(&persisted))?;
            return Ok(String::new());
        }
        Err(error) => return Err(error),
    };
    let Some(coverage) = coverage else {
        return refuse_disposition_without_coverage(tmpdir);
    };
    let record = load_disposition(tmpdir, Some(&coverage))?;
    let disposition = record
        .as_ref()
        .map_or("none", |value| value.disposition.as_str());
    let followup = record
        .as_ref()
        .filter(|value| !value.followup_issue_number.is_empty())
        .map(|value| format!("; follow-up #{}", value.followup_issue_number))
        .unwrap_or_default();
    Ok(format!(
        "{}/{} firm headings; band: {}; disposition: {}; todos_left: {}{followup}",
        coverage.touched,
        coverage.total,
        coverage.band,
        disposition,
        coverage.todos_left_count
    ))
}

fn emit_summary_line(tmpdir: &Path, manifest: Option<&Path>) -> ExitCode {
    match plan_coverage_summary_line(tmpdir, manifest) {
        Ok(line) => {
            emit_kv("PLAN_COVERAGE_LINE", &line);
            ExitCode::SUCCESS
        }
        Err(error) if error == STALE_LIVE => {
            eprintln!(
                "final report: live coverage no longer matches repository inputs; omitting optional plan-coverage line"
            );
            emit_kv("PLAN_COVERAGE_LINE", "");
            ExitCode::SUCCESS
        }
        Err(error) => {
            // The explicit envelope key separates a coverage-integrity failure,
            // which must fail the terminal report, from an unreachable helper.
            emit_kv("PLAN_COVERAGE_ERROR", &safe_line(&error, 300));
            ExitCode::from(4)
        }
    }
}

#[cfg(test)]
mod scope_disposition_unit_tests {
    use std::{
        ffi::OsString,
        fmt::Write as _,
        fs,
        path::PathBuf,
        process::ExitCode,
        sync::{Arc, Mutex},
    };

    use larch_core::{ProcessOutput, ProcessStatus};
    use larch_test_support::{GitFixture, GitRepository};
    use tempfile::TempDir;

    use super::{
        compute_and_write, contains_token_sequence, coverage_band, ensure_ascii,
        is_nonblocking_full_suite_todo, load_disposition, record_disposition, scope_disposition,
        word_tokens,
    };
    use crate::implement_child_seam::declare_plugin_root;
    use crate::implement_dispatch_commands::{clear_test_hooks, install_test_larch};

    #[test]
    fn word_tokens_split_on_punctuation_and_lower_case() {
        assert_eq!(
            word_tokens("Make py-test!"),
            vec!["make".to_owned(), "py".to_owned(), "test".to_owned()]
        );
    }

    #[test]
    fn token_sequence_matches_contiguous_windows_only() {
        let tokens = word_tokens("make the py test suite");
        assert!(!contains_token_sequence(&tokens, &["make", "py", "test"]));
        assert!(contains_token_sequence(
            &word_tokens("please make py test now"),
            &["make", "py", "test"]
        ));
        assert!(!contains_token_sequence(&tokens, &[]));
    }

    #[test]
    fn nonblocking_full_suite_todo_requires_unrun_and_focused_pass() {
        assert!(is_nonblocking_full_suite_todo(
            "make py-lint and make py-test (full suites) were not completed; focused tests passed"
        ));
        assert!(!is_nonblocking_full_suite_todo(
            "finish the remaining docs edits"
        ));
        assert!(!is_nonblocking_full_suite_todo(
            "make py-test full suite was not run"
        ));
        assert!(!is_nonblocking_full_suite_todo(
            "full suite make py test failed; focused tests passed"
        ));
    }

    #[test]
    fn coverage_band_thresholds_match_the_python_cutover_contract() {
        assert_eq!(coverage_band(0, 0), "advisory");
        assert_eq!(coverage_band(10, 1), "advisory");
        assert_eq!(coverage_band(5, 1), "middle");
        assert_eq!(coverage_band(2, 1), "high");
        assert_eq!(coverage_band(40, 10), "middle");
        assert_eq!(coverage_band(40, 30), "high");
    }

    #[test]
    fn ensure_ascii_escapes_non_ascii_scalars_like_json_dumps() {
        assert_eq!(ensure_ascii("plain"), "plain");
        assert_eq!(ensure_ascii("café"), "caf\\u00e9");
    }

    fn out(code: i32, stdout: &str) -> ProcessOutput {
        ProcessOutput::new(
            ProcessStatus::new(code == 0, Some(code)),
            stdout.as_bytes().to_vec(),
            Vec::new(),
            false,
            false,
        )
    }

    fn os(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    fn code(exit: ExitCode) -> String {
        format!("{exit:?}")
    }

    fn expected(value: u8) -> String {
        format!("{:?}", ExitCode::from(value))
    }

    fn fixture(plan_paths: &[&str], existing: &[&str]) -> (GitRepository, TempDir, PathBuf) {
        let repository = GitRepository::builder(GitFixture::Refs)
            .build()
            .expect("git fixture");
        let session = TempDir::new().expect("session root");
        let tmp_path = session.path().join("tmp");
        fs::create_dir_all(&tmp_path).expect("tmp");
        let tmpdir = fs::canonicalize(&tmp_path).expect("canonical tmp");
        let head = repository
            .git(["rev-parse", "HEAD"])
            .expect("rev-parse");
        assert!(head.success(), "rev-parse failed");
        let head = String::from_utf8(head.stdout).expect("utf8");
        fs::write(tmpdir.join("step2-baseline.txt"), head.trim()).expect("baseline");
        fs::write(tmpdir.join("session-id"), "unit-scope\n").expect("session");
        let mut plan = String::from("## Files\n");
        for path in plan_paths {
            writeln!(plan, "### NEW: `{path}`").expect("plan line");
        }
        fs::write(tmpdir.join("plan.txt"), plan).expect("plan");
        for path in existing {
            repository
                .write(path, b"touched\n")
                .expect("touch plan path");
        }
        (repository, session, tmpdir)
    }

    fn coverage_fixture() -> (GitRepository, TempDir, PathBuf) {
        let (repository, session, tmpdir) = fixture(&["a.txt", "b.txt"], &["a.txt"]);
        let coverage =
            compute_and_write(&tmpdir, repository.root(), None, None).expect("compute coverage");
        assert_eq!(coverage.band, "high");
        (repository, session, tmpdir)
    }

    #[test]
    fn scope_disposition_cli_covers_compute_validate_summary_and_deferred() {
        let (repository, _session, tmpdir) = fixture(&["a.txt", "b.txt"], &["a.txt"]);
        let tmp = tmpdir.display().to_string();
        let repo_s = repository.root().display().to_string();
        assert_eq!(
            code(scope_disposition(&os(&[
                "compute",
                "--tmpdir",
                &tmp,
                "--repo-root",
                &repo_s,
            ]))),
            expected(0)
        );
        assert_eq!(
            code(scope_disposition(&os(&[
                "validate-ship",
                "--tmpdir",
                &tmp,
                "--repo-root",
                &repo_s,
            ]))),
            expected(3)
        );
        assert_eq!(
            code(scope_disposition(&os(&[
                "render-deferred-inventory",
                "--tmpdir",
                &tmp,
                "--repo-root",
                &repo_s,
            ]))),
            expected(0)
        );
        fs::write(
            tmpdir.join("session-env.sh"),
            format!("REPO_ROOT={}\n", repository.root().display()),
        )
        .expect("session env");
        assert_eq!(
            code(scope_disposition(&os(&["summary-line", "--tmpdir", &tmp]))),
            expected(0)
        );
        assert_eq!(
            code(scope_disposition(&os(&[
                "record",
                "--tmpdir",
                &tmp,
                "--repo-root",
                &repo_s,
                "--disposition",
                "bail-rescope",
            ]))),
            expected(0)
        );
        assert_eq!(
            code(scope_disposition(&os(&[
                "validate-ship",
                "--tmpdir",
                &tmp,
                "--repo-root",
                &repo_s,
            ]))),
            expected(3)
        );
    }

    #[test]
    fn scope_disposition_cli_invalidates_stale_fingerprint_and_accepts_advisory() {
        let (repository, _session, tmpdir) = fixture(&["a.txt"], &["a.txt"]);
        let tmp = tmpdir.display().to_string();
        let repo_s = repository.root().display().to_string();
        assert_eq!(
            code(scope_disposition(&os(&[
                "compute",
                "--tmpdir",
                &tmp,
                "--repo-root",
                &repo_s,
            ]))),
            expected(0)
        );
        assert_eq!(
            code(scope_disposition(&os(&[
                "validate-ship",
                "--tmpdir",
                &tmp,
                "--repo-root",
                &repo_s,
            ]))),
            expected(0)
        );
        let (repository2, _session2, tmpdir2) = coverage_fixture();
        let disposition = tmpdir2.join("scope-disposition.json");
        fs::write(
            &disposition,
            format!(
                "{{\n  \"coverage_file\": {:?},\n  \"disposition\": \"proceed-partial\",\n  \"fingerprint\": \"stale\",\n  \"followup_issue_number\": \"\",\n  \"followup_issue_url\": \"\"\n}}\n",
                tmpdir2.join("plan-coverage.json")
            ),
        )
        .expect("stale disposition");
        assert_eq!(
            code(scope_disposition(&os(&[
                "invalidate-if-stale",
                "--tmpdir",
                &tmpdir2.display().to_string(),
                "--repo-root",
                &repository2.root().display().to_string(),
            ]))),
            expected(3)
        );
        assert!(!disposition.exists());
    }

    #[test]
    fn scope_disposition_cli_filters_manifest_todos_and_may_update() {
        let (repository, _session, tmpdir) = fixture(&["a.txt"], &["a.txt"]);
        let manifest = tmpdir.join("manifest.json");
        fs::write(
            &manifest,
            r#"{"todos_left":["make py-lint and make py-test (full suites) were not completed; focused tests passed","finish remaining docs"]}"#,
        )
        .expect("manifest");
        let tmp = tmpdir.display().to_string();
        let repo_s = repository.root().display().to_string();
        assert_eq!(
            code(scope_disposition(&os(&[
                "compute",
                "--tmpdir",
                &tmp,
                "--repo-root",
                &repo_s,
                "--manifest-path",
                &manifest.display().to_string(),
            ]))),
            expected(0)
        );
        fs::write(
            tmpdir.join("plan.txt"),
            "## Files\n### UPDATED: `a.txt`\n### MAY_UPDATE: `optional.md`\n",
        )
        .expect("plan");
        assert_eq!(
            code(scope_disposition(&os(&[
                "compute",
                "--tmpdir",
                &tmp,
                "--repo-root",
                &repo_s,
            ]))),
            expected(0)
        );
    }

    #[test]
    fn scope_disposition_cli_uses_live_origin_and_forked_remote_selection() {
        // GitFixture::Refs already has a resolvable origin/HEAD.
        let (repository, _session, tmpdir) = fixture(&["a.txt"], &["a.txt"]);
        assert_eq!(
            code(scope_disposition(&os(&[
                "compute",
                "--tmpdir",
                &tmpdir.display().to_string(),
                "--repo-root",
                &repository.root().display().to_string(),
            ]))),
            expected(0)
        );
        let (repository2, _session2, tmpdir2) = fixture(&["a.txt", "b.txt"], &["a.txt"]);
        fs::write(
            tmpdir2.join("session-env.sh"),
            "FORKED_TARGET=true\nREPO_ROOT=ignored\n",
        )
        .expect("forked session");
        assert_eq!(
            code(scope_disposition(&os(&[
                "compute",
                "--tmpdir",
                &tmpdir2.display().to_string(),
                "--repo-root",
                &repository2.root().display().to_string(),
            ]))),
            expected(0)
        );
    }

    #[test]
    fn scope_disposition_cli_usage_and_missing_tmpdir_fail_closed() {
        assert_eq!(code(scope_disposition(&os(&["-h"]))), expected(0));
        assert_eq!(code(scope_disposition(&os(&[]))), expected(2));
        assert_eq!(
            code(scope_disposition(&os(&["not-an-action"]))),
            expected(2)
        );
        assert_eq!(
            code(scope_disposition(&os(&[
                "compute",
                "--tmpdir",
                "/tmp/larch-scope-disposition-missing-dir-xyz",
            ]))),
            expected(2)
        );
        let empty = TempDir::new().expect("tmp");
        assert_eq!(
            code(scope_disposition(&os(&[
                "record",
                "--tmpdir",
                &empty.path().display().to_string(),
                "--disposition",
                "nope",
            ]))),
            expected(2)
        );
    }

    #[test]
    fn proceed_partial_cli_refuses_without_tracking_issue() {
        let (repository, _session, tmpdir) = coverage_fixture();
        assert_eq!(
            code(scope_disposition(&os(&[
                "record",
                "--tmpdir",
                &tmpdir.display().to_string(),
                "--repo-root",
                &repository.root().display().to_string(),
                "--disposition",
                "proceed-partial",
            ]))),
            expected(4)
        );
    }

    #[test]
    fn empty_summary_line_when_no_coverage_artifacts_exist() {
        let root = TempDir::new().expect("root");
        let tmpdir = fs::canonicalize(root.path()).expect("tmp");
        assert_eq!(
            code(scope_disposition(&os(&[
                "summary-line",
                "--tmpdir",
                &tmpdir.display().to_string(),
            ]))),
            expected(0)
        );
    }

    #[test]
    fn proceed_partial_records_followup_through_the_verified_larch_hook() {
        let (repository, session, tmpdir) = coverage_fixture();
        declare_plugin_root(session.path());
        let calls = Arc::new(Mutex::new(Vec::<String>::new()));
        let observed = calls.clone();
        install_test_larch(move |_cwd, _root, args| {
            let joined = args
                .iter()
                .map(|value| value.to_string_lossy().into_owned())
                .collect::<Vec<_>>()
                .join(" ");
            observed.lock().expect("lock").push(joined.clone());
            if joined.starts_with("issue create-one") {
                return Ok(out(
                    0,
                    "ISSUE_NUMBER=99\nISSUE_URL=https://example.test/99\n",
                ));
            }
            if joined.starts_with("tracking-issue append-comment")
                || joined.starts_with("issue add-blocked-by")
                || joined.starts_with("run-log write")
            {
                return Ok(out(0, "OK=true\n"));
            }
            Ok(out(2, &format!("unexpected:{joined}")))
        });

        let record = record_disposition(
            &tmpdir,
            "proceed-partial",
            repository.root(),
            None,
            "o/r",
            "42",
            "run-unit",
        );
        clear_test_hooks();
        let record = record.expect("record");
        assert_eq!(record.disposition, "proceed-partial");
        assert_eq!(record.followup_issue_number, "99");
        assert_eq!(record.followup_issue_url, "https://example.test/99");
        let loaded = load_disposition(&tmpdir, None)
            .expect("load")
            .expect("present");
        assert_eq!(loaded.followup_issue_number, "99");
        let seen = calls.lock().expect("lock").clone();
        assert!(
            seen.iter().any(|row| row.starts_with("issue create-one")),
            "seen={seen:?}"
        );
        assert!(
            seen.iter()
                .any(|row| row.starts_with("tracking-issue append-comment")),
            "seen={seen:?}"
        );
        assert!(
            seen.iter().any(|row| row.starts_with("issue add-blocked-by")),
            "seen={seen:?}"
        );
        assert!(
            seen.iter().any(|row| row.starts_with("run-log write")),
            "seen={seen:?}"
        );
    }

    #[test]
    fn proceed_partial_reuses_an_existing_matching_followup() {
        let (repository, session, tmpdir) = coverage_fixture();
        declare_plugin_root(session.path());
        let coverage =
            compute_and_write(&tmpdir, repository.root(), None, None).expect("coverage");
        fs::write(
            tmpdir.join("scope-disposition.json"),
            format!(
                "{{\n  \"coverage_file\": {:?},\n  \"disposition\": \"proceed-partial\",\n  \"fingerprint\": {:?},\n  \"followup_issue_number\": \"77\",\n  \"followup_issue_url\": \"https://example.test/77\"\n}}\n",
                coverage.coverage_file, coverage.fingerprint
            ),
        )
        .expect("seed disposition");
        install_test_larch(|_c, _r, _a| Ok(out(2, "should-not-create")));

        let record = record_disposition(
            &tmpdir,
            "proceed-partial",
            repository.root(),
            None,
            "o/r",
            "42",
            "",
        );
        clear_test_hooks();
        let record = record.expect("reuse");
        assert_eq!(record.followup_issue_number, "77");
        assert_eq!(record.followup_issue_url, "https://example.test/77");
    }
}
