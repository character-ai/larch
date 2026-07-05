#!/usr/bin/env bash
# Validate /implement SKILL.md Bash fences are thin script-call wrappers.

set -euo pipefail


python3 <<'PY'
from pathlib import Path
import re, shlex, sys

path = Path('skills/implement/SKILL.md')
lines = path.read_text().splitlines()
fences = []
in_fence = False
start = 0
body = []
for idx, line in enumerate(lines, 1):
    if line.lstrip().startswith('```bash'):
        in_fence = True
        start = idx
        body = []
    elif in_fence and line.lstrip().startswith('```'):
        fences.append((start, idx, body[:]))
        in_fence = False
    elif in_fence:
        body.append((idx, line))

errors = []
old_count = 0
new_count = 0
saw_py_launcher = False

CANONICAL_GUARD = '[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ] && . "$IMPLEMENT_TMPDIR/plugin-root.env"'
AWK_FALLBACK_PREFIX = '[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ] && CLAUDE_PLUGIN_ROOT=$(awk '
LAUNCHER_PREFIX = '"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" '
EXPECTED_OLD = 2
EXPECTED_NEW = 21

def old_logical_commands(body):
    commands = []
    parts = []
    for _, raw in body:
        stripped = raw.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if stripped == CANONICAL_GUARD:
            continue
        if stripped.startswith(AWK_FALLBACK_PREFIX):
            continue
        if stripped in {'export IMPLEMENT_TMPDIR', 'export CLAUDE_PLUGIN_ROOT'}:
            continue
        if stripped.endswith('\\'):
            stripped = stripped[:-1].rstrip()
            parts.append(stripped)
            continue
        parts.append(stripped)
        commands.append(' '.join(parts))
        parts = []
    if parts:
        commands.append(' '.join(parts))
    return commands

def old_target_kind(cmd):
    if 'python/cli.py' in cmd and 'pr closes-issue' in cmd:
        return 'structured-invocation'
    if 'python/cli.py' in cmd and 'implement preflight' in cmd:
        return 'preflight-helper'
    if 'python/cli.py' in cmd and 'plan-block read' in cmd:
        return 'preflight-plan-direct'
    if 'skills/implement/scripts/step-0-bootstrap.sh' in cmd and '--mode initial' in cmd:
        return 'step-0-initial'
    if 'skills/implement/scripts/step-0-bootstrap.sh' in cmd and '--mode resume' in cmd:
        return 'dirty-tree-resume'
    return ''

def has_guard(body):
    return any(raw.strip() == CANONICAL_GUARD for _, raw in body)

def has_awk(body):
    return any(raw.strip().startswith(AWK_FALLBACK_PREFIX) for _, raw in body)

def nonblank_lines(body):
    return [(ln, raw) for ln, raw in body if raw.strip()]

def validate_old(start, end, body, commands, cmd, kind):
    if kind == 'preflight-plan-direct':
        errors.append(f'fence {start}-{end}: direct Preflight plan-block read fence is forbidden')
        return
    if kind == 'preflight-helper':
        validate_preflight_helper(start, end, body, commands, cmd)
        return
    if len(commands) != 1:
        errors.append(f'fence {start}-{end}: old-shape {kind} must have exactly one logical command, found {len(commands)}')
    if not has_guard(body):
        errors.append(f'fence {start}-{end}: old-shape {kind} missing canonical plugin-root.env guard')
    awk = has_awk(body)
    requires_awk = kind in {'structured-invocation', 'step-0-initial', 'dirty-tree-resume'}
    if requires_awk and not awk:
        errors.append(f'fence {start}-{end}: old-shape {kind} missing session-env awk fallback')
    if not requires_awk and awk:
        errors.append(f'fence {start}-{end}: old-shape {kind} must remain guard-only without awk fallback')
    if kind == 'step-0-initial' and '--mode initial' not in cmd:
        errors.append(f'fence {start}-{end}: Step 0 initial old-shape target missing --mode initial')
    if kind == 'step-0-initial' and 'LARCH_CLAUDE_PID="$PPID" ' not in cmd:
        errors.append(f'fence {start}-{end}: Step 0 initial old-shape target missing LARCH_CLAUDE_PID prefix')
    if kind == 'dirty-tree-resume' and '--mode resume' not in cmd:
        errors.append(f'fence {start}-{end}: dirty-tree resume old-shape target missing --mode resume')
    if kind == 'dirty-tree-resume' and 'LARCH_CLAUDE_PID="$PPID" ' not in cmd:
        errors.append(f'fence {start}-{end}: dirty-tree resume old-shape target missing LARCH_CLAUDE_PID prefix')
    if re.search(r'(^|[\s;])(\|\||&&|;|\bif\s|\bwhile\s|\buntil\s|\bcase\s)', cmd):
        errors.append(f'fence {start}-{end}: inline shell control logic is not allowed: {cmd}')


def validate_preflight_helper(start, end, body, commands, cmd):
    if not has_guard(body):
        errors.append(f'fence {start}-{end}: preflight-helper missing canonical plugin-root.env guard')
    if has_awk(body):
        errors.append(f'fence {start}-{end}: preflight-helper must not use session-env awk fallback')
    if cmd.count('python/cli.py') != 1 or 'implement preflight' not in cmd:
        errors.append(f'fence {start}-{end}: preflight-helper must invoke python/cli.py implement preflight exactly once')
    required = [
        'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement preflight',
        '--issue "$TARGET_ISSUE_NUMBER"',
        '--preflight-tmpdir "$PREFLIGHT_TMPDIR"',
        'preflight_args=(',
        '"${preflight_args[@]}"',
    ]
    for needle in required:
        if needle not in cmd:
            errors.append(f'fence {start}-{end}: preflight-helper missing {needle}')
    if '--repo "$UPSTREAM_REPO"' not in cmd or '[ -n "${UPSTREAM_REPO:-}" ]' not in cmd:
        errors.append(f'fence {start}-{end}: preflight-helper must add --repo only inside the UPSTREAM_REPO non-empty branch')
    if '--force' not in cmd or '[ "${force_requested:-false}" = true ]' not in cmd:
        errors.append(f'fence {start}-{end}: preflight-helper must add --force only inside the force_requested=true branch')
    if '${force_requested:+--force}' in cmd:
        errors.append(f'fence {start}-{end}: preflight-helper must not use parameter-expansion force argv')

def validate_new(start, end, body):
    global saw_py_launcher
    physical = nonblank_lines(body)
    if len(physical) != 1:
        errors.append(f'fence {start}-{end}: new-shape fence must have exactly one nonblank physical line, found {len(physical)}')
        return
    line_no, raw = physical[0]
    stripped = raw.strip()
    if raw.lstrip().startswith('#'):
        errors.append(f'fence {start}-{end}: new-shape fence must not contain comments')
        return
    if stripped.endswith('\\'):
        errors.append(f'fence {start}-{end}: new-shape fence must not use a line continuation')
    if stripped == 'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement step-16-17 --implement-tmpdir "$IMPLEMENT_TMPDIR"':
        return
    if not stripped.startswith(LAUNCHER_PREFIX):
        errors.append(f'fence {start}-{end}: new-shape command must start with {LAUNCHER_PREFIX!r} or be the direct Step 16-17 Python CLI call: {stripped}')
        return
    try:
        tokens = shlex.split(stripped)
    except ValueError as exc:
        errors.append(f'fence {start}-{end}: new-shape command is not shell-parseable: {exc}: {stripped}')
        return
    if len(tokens) < 2:
        errors.append(f'fence {start}-{end}: new-shape launcher call missing script target: {stripped}')
        return
    if tokens[0] != '$HOME/.cache/larch/sessions/implement-run-$PPID.sh':
        errors.append(f'fence {start}-{end}: launcher path must be exactly "$HOME/.cache/larch/sessions/implement-run-$PPID.sh": {stripped}')
    target = tokens[1]
    if target.startswith('/') or '..' in target:
        errors.append(f'fence {start}-{end}: launcher target must be repo-relative without ..: {target}')
    if not (target.endswith('.sh') or target.endswith('.py')):
        errors.append(f'fence {start}-{end}: launcher target must be a .sh or .py path: {target}')
    if target.endswith('.py'):
        saw_py_launcher = True
    best_effort_timing = stripped == '"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py timing telemetry-mark --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step 5 — code review" || true'
    if re.search(r'(^|[\s;])(\|\||&&|;|\bif\s|\bwhile\s|\buntil\s|\bcase\s)', stripped) and not best_effort_timing:
        errors.append(f'fence {start}-{end}: inline shell control logic is not allowed: {stripped}')
    if re.search(r'/(?:token-ledger|timing-ledger|token-report|timing-report)\.sh\b', stripped):
        errors.append(f'fence {start}-{end}: telemetry-only script invocation is not allowed: {stripped}')

for start, end, body in fences:
    body_text = '\n'.join(raw for _, raw in body)
    if '8-pre-ship' in body_text and 'step-8-ship.sh' not in body_text:
        errors.append(f'fence {start}-{end}: standalone orchestrator 8-pre-ship fence is forbidden')
    if 'step-8' in body_text and 'sys.version_info' in body_text:
        errors.append(f'fence {start}-{end}: Step 8 python version checks must delegate to step-8-python-guard.sh')
    if 'python/cli.py ship seed-initial-state' in body_text:
        errors.append(f'fence {start}-{end}: Step 8 seed fences must delegate to step-8-seed-initial.sh')
    for _, raw in body:
        if 'session read-key' in raw:
            errors.append(f'fence {start}-{end}: inline session read-key is not allowed')
            break
    if 'python/cli.py' in body_text and 'plan-block read' in body_text:
        errors.append(f'fence {start}-{end}: direct Preflight plan-block read call is forbidden')
    if 'gh issue view' in body_text:
        errors.append(f'fence {start}-{end}: direct Preflight gh issue view call is forbidden')
    commands = old_logical_commands(body)
    cmd = ' '.join(commands)
    kind = old_target_kind(cmd)
    if kind:
        old_count += 1
        validate_old(start, end, body, commands, cmd, kind)
    else:
        new_count += 1
        validate_new(start, end, body)

for (_, end_a, _), (start_b, _, _) in zip(fences, fences[1:]):
    between = lines[end_a:start_b-1]
    if all(not line.strip() for line in between):
        errors.append(f'fences {end_a} and {start_b} are separated only by blank lines')

if old_count != EXPECTED_OLD or new_count != EXPECTED_NEW:
    errors.append(f'expected old={EXPECTED_OLD} new={EXPECTED_NEW} bash fences, found old={old_count} new={new_count}')


skill_text = path.read_text()
try:
    reship_start = skill_text.index('- **`reship`**:')
    oos_start = skill_text.index('- **`oos-pipeline`**:', reship_start)
    reship_slice = skill_text[reship_start:oos_start]
    reship_pre_fix = reship_slice.index('ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"')
    reship_continue = reship_slice.index('`NEXT_ACTION=continue` proceeds to the stale-handoff clear')
    if reship_pre_fix > reship_continue:
        errors.append('reship branch must require ship pre-fix-rebase before stale-handoff clear')
except ValueError as exc:
    errors.append(f'reship branch must document ship pre-fix-rebase ordering: {exc}')
try:
    ci_fix_start = skill_text.index('- **`ci-fix`**:')
    conflict_start = skill_text.index('- **`conflict-fix`**', ci_fix_start)
    ci_fix_slice = skill_text[ci_fix_start:conflict_start]
    ci_fix_pre_fix = ci_fix_slice.index('ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"')
    ci_fix_load = ci_fix_slice.index('Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/ship-pr-ci-fix.md`')
    if ci_fix_pre_fix > ci_fix_load:
        errors.append('ci-fix branch must require ship pre-fix-rebase before loading ship-pr-ci-fix.md')
except ValueError as exc:
    errors.append(f'ci-fix branch must document ship pre-fix-rebase before ci-fix load: {exc}')
try:
    guidelines_start = skill_text.index('- **`guidelines-assessment`**:')
    reship_start = skill_text.index('- **`reship`**:', guidelines_start)
    guidelines_slice = skill_text[guidelines_start:reship_start]
    write_compose = guidelines_slice.index('step-architectural-guidelines-write-compose.sh')
    stale_clear = guidelines_slice.index('foreground stale-handoff clear')
    relaunch = guidelines_slice.index('relaunch `step-8-ship.sh`')
    if not (write_compose < stale_clear < relaunch):
        errors.append('guidelines-assessment branch must run step-architectural-guidelines-write-compose.sh before stale-handoff clear and step-8-ship.sh relaunch')
except ValueError as exc:
    errors.append(f'guidelines-assessment branch must document compose-write ordering: {exc}')


resume_text = Path('skills/implement/references/bootstrap-recovery.md').read_text()
if 'LARCH_CLAUDE_PID="$PPID" "${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-0-bootstrap.sh" --mode resume' not in resume_text:
    errors.append('bootstrap-recovery resume fence must prefix step-0-bootstrap.sh with LARCH_CLAUDE_PID="$PPID"')

if saw_py_launcher:
    bootstrap = Path('python/larch/state/bootstrap.py').read_text()
    required = 'trap _larch_cleanup_active_leg EXIT INT TERM'
    forbidden_exec = '*.py) exec python3 "$CLAUDE_PLUGIN_ROOT/$script" "$@" ;;'
    forbidden = '*.py) exec "$CLAUDE_PLUGIN_ROOT/$script" "$@" ;;'
    if required not in bootstrap:
        errors.append('larch-run.sh template must trap active-leg cleanup for .py targets')
    if 'export __OWNER_TOKEN_ENV__="$_larch_active_leg_owner_token"' not in bootstrap or 'script = script.replace("__OWNER_TOKEN_ENV__", config.ENV_ACTIVE_LEG_OWNER_TOKEN)' not in bootstrap:
        errors.append('larch-run.sh template must export active-leg owner token before .py target')
    if 'implement kill-active-leg --owner-token "$_larch_active_leg_owner_token" --implement-tmpdir' not in bootstrap:
        errors.append('larch-run.sh template must forward owner token to implement kill-active-leg')
    if 'kill-active-leg --implement-tmpdir "$IMPLEMENT_TMPDIR" 2>/dev/null' in bootstrap:
        errors.append('larch-run.sh template must not silence kill-active-leg stderr')
    if forbidden_exec in bootstrap:
        errors.append('larch-run.sh template must not exec .py targets (outer fence needs trap cleanup)')
    if forbidden in bootstrap:
        errors.append('larch-run.sh template must not bare-exec .py targets')

if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
print(f'PASS: test-implement-fence-shape.sh (old={old_count} new={new_count})')
PY

python3 <<'PY'
from pathlib import Path
import contextlib
import io
import os
import re
import stat
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path("python").resolve()))
from larch.state import bootstrap, session_env  # noqa: E402


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


def run_launcher(launcher: Path, target: str, *argv: str) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
    }
    return subprocess.run(
        [str(launcher), target, *argv],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def extract_root_awk_program(text: str) -> str:
    for match in re.finditer(r"awk '([^']+)'", text):
        program = match.group(1)
        if "LARCH_CLAUDE_PLUGIN_ROOT=" in program:
            return program
    fail("missing LARCH_CLAUDE_PLUGIN_ROOT awk program")
    return ""


with tempfile.TemporaryDirectory(prefix="larch-run-launcher-test.") as tmp:
    root = Path(tmp).resolve()
    impl = root / "impl"
    fake_plugin = root / "plugin"
    (fake_plugin / "scripts").mkdir(parents=True)
    (fake_plugin / "python").mkdir(parents=True)
    impl.mkdir()
    (impl / "plugin-root.env").write_text(f"CLAUDE_PLUGIN_ROOT={fake_plugin}\n", encoding="utf-8")

    sh_target = fake_plugin / "scripts" / "echo-argv.sh"
    sh_target.write_text(
        "#!/usr/bin/env bash\nprintf 'SH_ARGV=%s|%s\\n' \"$1\" \"$2\"\n",
        encoding="utf-8",
    )
    sh_target.chmod(sh_target.stat().st_mode | stat.S_IXUSR)
    py_target = fake_plugin / "python" / "echo_argv.py"
    py_target.write_text(
        "import sys\nprint('PY_EXECUTABLE=' + sys.executable)\nprint('PY_ARGV=' + '|'.join(sys.argv[1:]))\n",
        encoding="utf-8",
    )

    if not bootstrap._write_larch_run_sh(str(impl)):
        fail("failed to write larch-run.sh")
    launcher = impl / "larch-run.sh"
    if not launcher.exists() or not os.access(launcher, os.X_OK):
        fail("larch-run.sh was not executable")

    sh = run_launcher(launcher, "scripts/echo-argv.sh", "one", "two words")
    if sh.returncode != 0 or "SH_ARGV=one|two words" not in sh.stdout:
        fail(f".sh launcher argv passthrough failed: rc={sh.returncode} stdout={sh.stdout!r} stderr={sh.stderr!r}")

    py = run_launcher(launcher, "python/echo_argv.py", "alpha", "beta gamma")
    if py.returncode != 0 or "PY_ARGV=alpha|beta gamma" not in py.stdout:
        fail(f".py launcher argv passthrough failed: rc={py.returncode} stdout={py.stdout!r} stderr={py.stderr!r}")
    if "PY_EXECUTABLE=" not in py.stdout:
        fail(".py launcher did not prove Python execution")

    home = root / "home"
    home.mkdir()
    prior_home = os.environ.get("HOME", "")
    os.environ["HOME"] = str(home)
    try:
        rc = session_env.write_implement_env_main(
            ["--claude-pid", "12345", "--implement-tmpdir", str(impl), "--cwd", str(root)]
        )
    finally:
        if prior_home:
            os.environ["HOME"] = prior_home
        else:
            os.environ.pop("HOME", None)
    if rc != 0:
        fail("failed to write implement-run launcher")
    stable_runner = home / ".cache" / "larch" / "sessions" / "implement-run-12345.sh"
    stable_env = {"PATH": os.environ.get("PATH", ""), "TMPDIR": os.environ.get("TMPDIR", "/tmp"), "HOME": str(home)}
    stable = subprocess.run(
        [str(stable_runner), "scripts/echo-argv.sh", "stable", "runner arg"],
        text=True,
        capture_output=True,
        check=False,
        env=stable_env,
    )
    if stable.returncode != 0 or "SH_ARGV=stable|runner arg" not in stable.stdout:
        fail(f"implement-run launcher failed without IMPLEMENT_TMPDIR: rc={stable.returncode} stdout={stable.stdout!r} stderr={stable.stderr!r}")

    for label, target in (("absolute", "/tmp/not-allowed.sh"), ("traversal", "../not-allowed.sh"), ("unsupported", "scripts/not-supported.txt")):
        result = run_launcher(launcher, target)
        if result.returncode != 2:
            fail(f"{label} target expected exit 2, got {result.returncode}")

    step0_program = extract_root_awk_program(Path("skills/implement/scripts/step-0-bootstrap.sh").read_text(encoding="utf-8"))
    generated_program = extract_root_awk_program(launcher.read_text(encoding="utf-8"))
    if step0_program != generated_program:
        fail("generated larch-run.sh awk fallback drifted from step-0-bootstrap.sh")


with tempfile.TemporaryDirectory(prefix="larch-run-partial-upgrade-test.") as tmp:
    root = Path(tmp).resolve()
    impl = root / "impl"
    impl.mkdir()
    session_env = impl / "session-env.sh"
    session_env.write_text(
        "\n".join(
            [
                f"LARCH_CLAUDE_PLUGIN_ROOT={Path.cwd()}",
                "LARCH_TOKEN_SESSION_ID=resume-session",
                "LARCH_CLAUDE_SOURCE_FILE=",
                f"LARCH_TIMING_LEDGER={impl / 'timing-ledger.tsv'}",
                "REPO=owner/repo",
                "REPO_UNAVAILABLE=false",
                "CODEX_PRESENT=false",
                "CURSOR_PRESENT=false",
                "CODEX_BINARY_FOUND=false",
                "CURSOR_BINARY_FOUND=false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (impl / "session-id").write_text("resume-session\n", encoding="utf-8")
    (impl / "plugin-root.env").write_text(f"CLAUDE_PLUGIN_ROOT={Path.cwd()}\n", encoding="utf-8")
    (impl / "plan.txt").write_text("## Plan\n", encoding="utf-8")
    (impl / "feature-description.txt").write_text("Resume launcher fixture\n", encoding="utf-8")
    launcher = impl / "larch-run.sh"
    if launcher.exists():
        fail("partial-upgrade fixture unexpectedly started with larch-run.sh")

    original_env = os.environ.copy()
    original_run = bootstrap._run
    original_cli = bootstrap._cli
    original_checkpoint = bootstrap.dirty_tree.checkpoint

    def completed(args: object, stdout: str = "") -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, stdout, "")

    def fake_run(argv: list[str], *, env: dict[str, str] | None = None, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
        joined = " ".join(argv)
        if "pr create-branch --check" in joined:
            return completed(argv, "CURRENT_BRANCH=feature/resume\nIS_MAIN=false\nIS_USER_BRANCH=true\nUSER_PREFIX=user\n")
        if "python/cli.py git current-branch" in joined:
            return completed(argv, "BRANCH=feature/resume\n")
        if "python/cli.py plan step1-log" in joined:
            return completed(argv, "PLAN_LOG=ok\n")
        return completed(argv, "")

    def fake_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        if args[:3] == ("pr", "create-branch", "--check"):
            return completed(args, "CURRENT_BRANCH=feature/resume\nIS_MAIN=false\nIS_USER_BRANCH=true\nUSER_PREFIX=user\n")
        if args[:3] == ("session", "read-key", "--file"):
            path = Path(args[3])
            key = args[args.index("--key") + 1]
            default = args[args.index("--default") + 1] if "--default" in args else ""
            value = default
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith(key + "="):
                    value = line.split("=", 1)[1]
                    break
            return completed(args, value + "\n")
        if args[:3] == ("session", "entry-gate", "--mode"):
            return completed(args, "ENTRY_GATE=ok\nSKIP_BRANCH_CHECK=false\n")
        return completed(args, "")

    try:
        os.environ.clear()
        os.environ.update(original_env)
        os.environ["IMPLEMENT_TMPDIR"] = str(impl)
        os.environ["LARCH_CLAUDE_PID"] = "12345"
        bootstrap._run = fake_run
        bootstrap._cli = fake_cli
        bootstrap.dirty_tree.checkpoint = lambda: ["STATUS=clean"]
        opts = bootstrap.BootstrapOptions(
            up_to_phase="plan",
            issue_number="4104",
            run_id="resume-session",
            resume_plan_tail=True,
        )
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = bootstrap.run_bootstrap(opts)
    finally:
        bootstrap._run = original_run
        bootstrap._cli = original_cli
        bootstrap.dirty_tree.checkpoint = original_checkpoint
        os.environ.clear()
        os.environ.update(original_env)

    if rc != 0:
        fail(f"resume bootstrap partial-upgrade path failed with rc={rc}")
    if not launcher.exists() or not os.access(launcher, os.X_OK):
        fail("resume bootstrap partial-upgrade path did not emit executable larch-run.sh")

print("PASS: test-implement-fence-shape.sh launcher sandbox")
PY
