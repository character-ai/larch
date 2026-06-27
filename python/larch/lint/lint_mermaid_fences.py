"""Lint Mermaid fenced code blocks in Markdown files."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

GIT = shutil.which("git") or "git"

FENCE_RE = re.compile(r"^[ \t]{0,3}(`{3,})([^`]*)$")


def _repo_root() -> Path:
    try:
        proc = subprocess.run(
            [GIT, "rev-parse", "--show-toplevel"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except FileNotFoundError:
        proc = subprocess.CompletedProcess([GIT], 1, stdout="")
    if proc.returncode == 0 and proc.stdout.strip():
        return Path(proc.stdout.strip())
    return Path(__file__).resolve().parents[3]


def _usage_error(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def _parse_args(argv: list[str]) -> tuple[int, bool, list[str]]:
    changed_only = False
    files: list[str] = []
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg in {"-h", "--help"}:
            print("Usage: cli.py lint mermaid-fences [--changed-only] [FILE ...]")
            raise SystemExit(0)
        if arg == "--changed-only":
            changed_only = True
        elif arg.startswith("--"):
            return 1, changed_only, [f"unknown flag: {arg}"]
        else:
            files.append(arg)
        idx += 1
    if changed_only and files:
        return 1, changed_only, ["--changed-only does not accept file arguments"]
    return 0, changed_only, files


def _in_ci(env: dict[str, str]) -> bool:
    return bool(env.get("GITHUB_EVENT_NAME") or env.get("GITHUB_ACTIONS"))


def _git_ok( *,args: list[str], root: Path) -> bool:
    return subprocess.run(
        [GIT, *args],
        cwd=root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def _changed_files( *,root: Path, env: dict[str, str]) -> tuple[int, list[str]]:
    range_spec = ""
    in_ci = _in_ci(env)
    event = env.get("GITHUB_EVENT_NAME", "")
    if event == "pull_request" and env.get("GITHUB_BASE_REF"):
        base = env["GITHUB_BASE_REF"]
        if not _git_ok(args=["rev-parse", "--verify", f"origin/{base}"], root=root):
            _ = subprocess.run(
                [GIT, "fetch", "--no-tags", "--prune", "origin", base],
                cwd=root,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        if not _git_ok(args=["rev-parse", "--verify", f"origin/{base}"], root=root):
            print(
                f"ERROR: cannot resolve origin/{base} for --changed-only diff range",
                file=sys.stderr,
            )
            return 2, []
        range_spec = f"origin/{base}...HEAD"
    elif event == "push":
        before = env.get("GITHUB_EVENT_BEFORE", "")
        sha = env.get("GITHUB_SHA", "")
        range_spec = f"{before}..{sha}" if before and sha else "HEAD~1..HEAD"
    elif _git_ok(args=["rev-parse", "--verify", "origin/main"], root=root):
        range_spec = "origin/main...HEAD"
    elif in_ci:
        print(
            "ERROR: origin/main unavailable in CI; refusing to silently skip Mermaid lint",
            file=sys.stderr,
        )
        return 2, []
    else:
        print("INFO: origin/main unavailable; no changed Mermaid files linted", file=sys.stderr)
        return 0, []

    proc = subprocess.run(
        [GIT, "diff", "--name-only", "--diff-filter=ACMR", range_spec, "--", "*.md"],
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if proc.returncode != 0:
        if in_ci:
            print(f"ERROR: git diff {range_spec} failed in CI", file=sys.stderr)
            return 2, []
        print(f"INFO: git diff {range_spec} failed; no changed Mermaid files linted", file=sys.stderr)
        return 0, []
    return 0, [line for line in proc.stdout.splitlines() if line]


def _filter_files(files: list[str]) -> list[str]:
    return [path for path in files if path and not path.startswith("larch-logs/")]


def extract_fences( *,src: Path, outdir: Path) -> int:
    in_outer = False
    outer_len = 0
    outer_mermaid = False
    fence_count = 0
    current: Path | None = None
    for line in src.read_text(encoding="utf-8", errors="replace").splitlines():
        match = FENCE_RE.match(line)
        if match:
            opener = match.group(1)
            rest = match.group(2)
            length = len(opener)
            if not in_outer:
                if re.fullmatch(r"[ \t]*mermaid[ \t]*", rest):
                    fence_count += 1
                    in_outer = True
                    outer_len = length
                    outer_mermaid = True
                    current = outdir / f"fence-{fence_count}.mmd"
                    _ = current.write_text("", encoding="utf-8")
                    continue
                in_outer = True
                outer_len = length
                outer_mermaid = False
            elif length >= outer_len and re.fullmatch(r"[ \t]*", rest):
                in_outer = False
                outer_len = 0
                outer_mermaid = False
                current = None
                continue
        if in_outer and outer_mermaid and current is not None:
            with current.open("a", encoding="utf-8") as handle:
                _ = handle.write(f"{line}\n")
    return fence_count


class MermaidRunner:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.mmdc = ""
        self.supports_parse_only = False
        self.render_args: list[str] = []

    def _resolve_mmdc(self) -> str | None:
        local = self.root / "mermaid-lint" / "node_modules" / ".bin" / "mmdc"
        if local.is_file() and local.stat().st_mode & 0o111:
            return str(local)
        return shutil.which("mmdc")

    def _install_local_toolchain(self) -> bool:
        toolchain = self.root / "mermaid-lint"
        if not (toolchain / "package-lock.json").is_file():
            return False
        npm = shutil.which("npm")
        if not npm:
            return False
        return (
            subprocess.run(
                [npm, "ci"],
                cwd=toolchain,
                check=False,
                stdout=subprocess.DEVNULL,
            ).returncode
            == 0
        )

    def ensure(self) -> int:
        if self.mmdc:
            return 0
        resolved = self._resolve_mmdc()
        if not resolved and self._install_local_toolchain():
            resolved = self._resolve_mmdc()
        if not resolved:
            print(
                "ERROR: missing Mermaid CLI (install @mermaid-js/mermaid-cli or run: cd mermaid-lint && npm ci)",
                file=sys.stderr,
            )
            return 2
        self.mmdc = resolved
        config = self.root / "scripts" / "lint-mermaid-puppeteer.json"
        if config.is_file():
            self.render_args = ["--puppeteerConfigFile", str(config)]
        help_proc = subprocess.run(
            [self.mmdc, "--help"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.supports_parse_only = "--parseOnly" in help_proc.stdout
        return 0

    def lint_one(self, *, input_path: Path, output_path: Path) -> bool:
        if self.supports_parse_only:
            cmd = [self.mmdc, "--parseOnly", "-i", str(input_path)]
        else:
            cmd = [self.mmdc, *self.render_args, "-i", str(input_path), "-o", str(output_path)]
        proc = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode == 0:
            return True
        if (
            not self.supports_parse_only
            and "Failed to launch the browser process" in proc.stderr
            and not _in_ci(dict(os.environ))
        ):
            print(
                "WARN: Mermaid render skipped because Puppeteer could not launch a browser",
                file=sys.stderr,
            )
            return True
        if proc.stderr:
            print(proc.stderr, file=sys.stderr, end="" if proc.stderr.endswith("\n") else "\n")
        return False


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    try:
        parse_rc, changed_only, files = _parse_args(argv=args)
    except SystemExit as exc:
        return int(exc.code or 0)
    if parse_rc != 0:
        return _usage_error(files[0])

    root = _repo_root()
    if changed_only:
        changed_rc, files = _changed_files(root=root, env=dict(os.environ))
        if changed_rc != 0:
            return changed_rc
    files = _filter_files(files)
    if not files:
        print("INFO: no Markdown files to lint")
        return 0

    failures = 0
    runner = MermaidRunner(root)
    with tempfile.TemporaryDirectory(prefix="mermaid-lint-") as tmp:
        tmpdir = Path(tmp)
        for path_text in files:
            if not path_text.endswith(".md"):
                continue
            path = Path(path_text)
            if not path.is_file():
                continue
            file_tmp = Path(tempfile.mkdtemp(prefix="file-", dir=tmpdir))
            count = extract_fences(src=path, outdir=file_tmp)
            for index in range(1, count + 1):
                ensure_rc = runner.ensure()
                if ensure_rc != 0:
                    return ensure_rc
                input_path = file_tmp / f"fence-{index}.mmd"
                output_path = file_tmp / f"fence-{index}.svg"
                if not runner.lint_one(input_path=input_path, output_path=output_path):
                    mode = "parse" if runner.supports_parse_only else "render"
                    print(f"ERROR: Mermaid {mode} failed: {path_text} fence {index}", file=sys.stderr)
                    failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
