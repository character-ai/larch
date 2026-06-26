"""/research helper CLIs and importable contracts."""
# ruff: noqa: PLR2004,S607
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportUnusedFunction=false, reportAttributeAccessIssue=false

from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import datetime as _dt
import http.client
import json
import subprocess
import ipaddress
import os
import re
import socket
import ssl
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable
from urllib.parse import urlparse

import larch_io
import logging_util
import rendering
import voting

BANNER_TEMPLATE = "**⚠ Reduced lane diversity: <N_FALLBACK> of 4 external research lanes ran as Claude-fallback. The model-family heterogeneity claim does not hold for this run.**"

_URL_RE = re.compile(r"https?://[A-Za-z0-9._~:/?#@!$&'()*+,;=%-]+")
_DOI_RE = re.compile(r"\b10\.[0-9]{4,9}/[A-Za-z0-9._;()/:-]+")
_VALID_DOI_RE = re.compile(r"^10\.[0-9]{4,9}/[A-Za-z0-9._;()/:-]+$")


@dataclass(frozen=True)
class FetchResult:
    status: str
    reason: str = ""

    def token(self) -> str:
        if self.status == "PASS":
            return "PASS"
        return f"{self.status}({self.reason})"


@dataclass(frozen=True)
class CitationLedgerRow:
    claim: str
    claim_type: str
    status: str
    reason: str


def _usage(message: str) -> None:
    logging_util.diagnostic(message)


def _emit_summary( *,pass_count: int, fail_count: int, unknown_count: int, total: int) -> None:
    logging_util.emit(f"SUMMARY=PASS={pass_count} FAIL={fail_count} UNKNOWN={unknown_count} TOTAL={total}")


def _write_text_atomic( *,path: Path, text: str) -> None:
    larch_io.atomic_write(path=path, text=text, temp_name=f".{path.name}.{os.getpid()}.tmp")


def _positive_int( *,value: str, flag: str) -> int:
    if not re.fullmatch(r"[0-9]+", value or "") or int(value) <= 0:
        raise ValueError(f"{flag} must be a positive integer (got: {value})")
    return int(value)


def _sanitize_excerpt(text: str) -> str:
    value = re.sub(r"\s+", " ", text.replace("|", " ")).strip()
    if len(value) > 80:
        value = value[:77] + "..."
    return value


def extract_urls(report_text: str) -> list[str]:
    return sorted({m.group(0).rstrip(".,;:") for m in _URL_RE.finditer(report_text)})


def extract_dois(report_text: str) -> list[str]:
    return sorted({m.group(0).rstrip(".,;:") for m in _DOI_RE.finditer(report_text)})


def extract_filelines(report_text: str) -> list[str]:
    pattern = re.compile(f"{voting.FILE_LINE_REGEXES['any-re']}|{voting.FILE_LINE_REGEXES['extensionless-re']}")
    out: set[str] = set()
    keep = re.compile(r"\.[A-Za-z]+(:[0-9]+(-[0-9]+)?)?$|^(Makefile|Dockerfile|GNUmakefile)(:[0-9]+(-[0-9]+)?)?$")
    for match in pattern.finditer(report_text):
        value = match.group(0)
        value = re.sub(r"^[^A-Za-z0-9._/-]", "", value)
        value = re.sub(r"[^A-Za-z0-9._/:-]$", "", value)
        if keep.search(value):
            out.add(value)
    return sorted(out)


_CGNAT_NET = ipaddress.ip_network("100.64.0.0/10")


def _is_private_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value.strip("[]"))
    except ValueError:
        return False
    if ip in _CGNAT_NET:
        return True
    return bool(ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_unspecified or ip.is_reserved)


def _private_hostname(host: str) -> bool:
    lowered = host.strip("[]").lower()
    if lowered in {"localhost", "localhost.localdomain"} or lowered.endswith(".localhost"):
        return True
    return _is_private_ip(lowered)


def _credibility_tier(host: str) -> str:
    lowered = host.lower()
    if lowered in {"arxiv.org", "doi.org", "github.com", "anthropic.com"}:
        return "allow"
    allow_suffixes = (
        ".wikipedia.org",
        ".arxiv.org",
        ".acm.org",
        ".ietf.org",
        ".python.org",
        ".rust-lang.org",
        ".doi.org",
        ".github.com",
        ".githubusercontent.com",
        ".anthropic.com",
    )
    if any(lowered.endswith(suffix) for suffix in allow_suffixes):
        return "allow"
    return "unknown"


def _url_host(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return None
    return parsed.hostname


def _render_credibility_block(hosts: list[str]) -> str:
    unique_hosts = sorted({host.lower() for host in hosts if host})
    if not unique_hosts:
        return ""
    rows: list[str] = []
    for host in unique_hosts:
        tier = _credibility_tier(host)
        note = (
            "well-known reputable origin"
            if tier == "allow"
            else "no allow-list entry; classification heuristic only — NOT a FAIL signal"
        )
        rows.append(f"| {host} | {tier} | {note} |\n")
    return (
        "\n\n<details><summary>Domain credibility (advisory only)</summary>\n\n"
        "| Domain | Tier | Notes |\n"
        "|---|---|---|\n"
        f"{''.join(rows)}"
        "</details>"
    )


def _resolve_public_ips(
    host: str,
    *,
    port: int = 443,
    timeout: float,
    resolver: Callable[[str], list[str]] | None = None,
) -> tuple[list[str], str | None]:
    if resolver is not None:
        ips = resolver(host)
    else:
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(socket.getaddrinfo, host, port, type=socket.SOCK_STREAM)
        try:
            infos = future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            executor.shutdown(wait=False, cancel_futures=True)
            return [], "timeout"
        except socket.gaierror:
            executor.shutdown(wait=False, cancel_futures=True)
            return [], "network-error"
        except OSError:
            executor.shutdown(wait=False, cancel_futures=True)
            return [], "network-error"
        executor.shutdown(wait=False, cancel_futures=True)
        ips = []
        for info in infos:
            addr = info[4][0]
            if addr not in ips:
                ips.append(addr)
    for ip in ips:
        if _is_private_ip(ip):
            return [], "ssrf-private-resolved"
    return ips, None


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, *, host: str, port: int, pinned_ip: str | None, timeout: float):
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self._pinned_ip = pinned_ip

    def connect(self) -> None:  # pragma: no cover - exercised via integration seam
        target = self._pinned_ip or self.host
        sock = socket.create_connection((target, self.port), self.timeout, self.source_address)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def fetch_url(
    url: str,
    *,
    timeout: int = 10,
    resolver: Callable[[str], list[str]] | None = None,
    connector: Callable[[str, str | None, int], int] | None = None,
) -> FetchResult:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return FetchResult("FAIL", "non-https")
    host = parsed.hostname or ""
    if not host:
        return FetchResult("FAIL", "non-https")
    if _private_hostname(host):
        return FetchResult("FAIL", "ssrf-private-host")
    try:
        port = parsed.port or 443
    except ValueError:
        return FetchResult("FAIL", "invalid-url")
    ips, resolve_reason = _resolve_public_ips(host, port=port, timeout=timeout, resolver=resolver)
    if resolve_reason == "ssrf-private-resolved":
        return FetchResult("FAIL", resolve_reason)
    if resolve_reason in {"timeout", "network-error"}:
        return FetchResult("UNKNOWN", resolve_reason)
    if not ips:
        return FetchResult("UNKNOWN", "network-error")
    pinned_ip = ips[0]
    try:
        if connector is not None:
            code = connector(url, pinned_ip, timeout)
        else:
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            host_header = host if port == 443 else f"{host}:{port}"
            conn = _PinnedHTTPSConnection(host=host, port=port, pinned_ip=pinned_ip, timeout=timeout)
            try:
                conn.request("HEAD", path, headers={"Host": host_header})
                response = conn.getresponse()
                code = response.status
            finally:
                conn.close()
    except TimeoutError:
        return FetchResult("UNKNOWN", "timeout")
    except OSError:
        return FetchResult("UNKNOWN", resolve_reason or "network-error")
    if 200 <= code <= 299:
        return FetchResult("PASS")
    if 300 <= code <= 399:
        return FetchResult("UNKNOWN", "redirect-not-followed")
    if code in {403, 405, 501}:
        return FetchResult("UNKNOWN", "head-not-supported")
    if code in {404, 410}:
        return FetchResult("FAIL", "head-not-found")
    if 400 <= code <= 499:
        return FetchResult("FAIL", f"head-client-error-{code}")
    if 500 <= code <= 599:
        return FetchResult("FAIL", f"head-server-error-{code}")
    return FetchResult("UNKNOWN", f"unrecognized-status-{code}")


_FETCH_WORKER_CODE = """\
import json
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import research
result = research.fetch_url(sys.argv[2], timeout=int(sys.argv[3]))
print(json.dumps({"status": result.status, "reason": result.reason}))
"""


def _decode_fetch_process(proc: subprocess.Popen[bytes]) -> FetchResult:
    stdout = proc.stdout.read() if proc.stdout is not None else b""
    if proc.returncode != 0 or not stdout.strip():
        return FetchResult("UNKNOWN", "network-error")
    try:
        payload = json.loads(stdout.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return FetchResult("UNKNOWN", "network-error")
    status = payload.get("status")
    reason = payload.get("reason", "")
    if status in {"PASS", "FAIL", "UNKNOWN"} and isinstance(reason, str):
        return FetchResult(status, reason)
    return FetchResult("UNKNOWN", "network-error")


def _terminate_fetch_process(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=1)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def _start_fetch_process(url: str, *, timeout: int) -> subprocess.Popen[bytes]:
    root = str(Path(__file__).resolve().parent)
    return subprocess.Popen(
        [sys.executable, "-c", _FETCH_WORKER_CODE, root, url, str(timeout)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )


def _parallel_fetch_results(
    fetch_targets: dict[str, str],
    *,
    budget_seconds: int,
    per_fetch_timeout: int,
    fetcher: Callable[[str], FetchResult] | None,
    sleeper: Callable[[float], None] | None = None,
) -> dict[str, FetchResult]:
    sleep = sleeper or time.sleep
    if fetcher is not None:
        results: dict[str, FetchResult] = {}
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=min(16, len(fetch_targets)))
        futures = {executor.submit(fetcher, target): key for key, target in fetch_targets.items()}
        try:
            done, pending = concurrent.futures.wait(futures, timeout=budget_seconds)
            for future in done:
                key = futures[future]
                with contextlib.suppress(Exception):
                    results[key] = future.result()
            for future in pending:
                future.cancel()
                results[futures[future]] = FetchResult("UNKNOWN", "timeout")
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
        return results

    active: list[tuple[str, subprocess.Popen[bytes], float]] = []
    for key, target in fetch_targets.items():
        active.append((key, _start_fetch_process(target, timeout=per_fetch_timeout), time.monotonic()))
    deadline = time.monotonic() + budget_seconds
    results: dict[str, FetchResult] = {}
    while active:
        now = time.monotonic()
        if now >= deadline:
            next_active: list[tuple[str, subprocess.Popen[bytes], float]] = []
            for key, proc, started in active:
                if proc.poll() is not None:
                    results[key] = _decode_fetch_process(proc)
                else:
                    next_active.append((key, proc, started))
            active = next_active
            break
        next_active = []
        for key, proc, started in active:
            if proc.poll() is not None:
                results[key] = _decode_fetch_process(proc)
            elif now - started >= per_fetch_timeout:
                _terminate_fetch_process(proc)
                with contextlib.suppress(Exception):
                    if proc.stdout is not None:
                        proc.stdout.read()
                results[key] = FetchResult("UNKNOWN", "timeout")
            else:
                next_active.append((key, proc, started))
        active = next_active
        if active:
            sleep(0.05)
    for key, proc, _started in active:
        if key in results:
            continue
        if proc.poll() is not None:
            results[key] = _decode_fetch_process(proc)
            continue
        _terminate_fetch_process(proc)
        with contextlib.suppress(Exception):
            if proc.stdout is not None:
                proc.stdout.read()
        results[key] = FetchResult("UNKNOWN", "timeout")
    return results


def check_fileline(cite: str, *, git_root: Path | None = None) -> FetchResult:
    match = re.match(r"^([^:]+):([0-9]+)(-([0-9]+))?$", cite)
    if match:
        rel = match.group(1)
        start = int(match.group(2))
        end = int(match.group(4) or start)
    else:
        rel = cite
        start = end = 0
    if git_root is None:
        try:
            got = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
            )
            if got.returncode != 0 or not got.stdout.strip():
                return FetchResult("UNKNOWN", "git-root-unavailable")
            git_root = Path(got.stdout.strip())
        except OSError:
            return FetchResult("UNKNOWN", "git-root-unavailable")
    target = git_root / rel
    if not target.exists() and Path(rel).exists():
        target = Path(rel)
    if not target.exists():
        return FetchResult("FAIL", "file-not-found")
    try:
        root_real = git_root.resolve(strict=True)
        target_real = target.resolve(strict=True)
    except FileNotFoundError:
        return FetchResult("UNKNOWN", "broken-symlink")
    try:
        target_real.relative_to(root_real)
    except ValueError:
        return FetchResult("UNKNOWN", "out-of-tree-path-after-realpath")
    if target_real.is_dir():
        return FetchResult("FAIL", "path-is-directory")
    if not target_real.is_file():
        return FetchResult("UNKNOWN", "broken-symlink")
    if not match:
        return FetchResult("PASS")
    if start > end:
        return FetchResult("FAIL", "line-range-empty")
    try:
        line_count = len(target_real.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return FetchResult("UNKNOWN", "file-unreadable")
    if end > line_count:
        return FetchResult("FAIL", "line-out-of-range")
    return FetchResult("PASS")


def _parse_result(token: str) -> FetchResult:
    if token == "PASS":
        return FetchResult("PASS")
    match = re.match(r"^(FAIL|UNKNOWN)\((.*)\)$", token)
    if match:
        return FetchResult(match.group(1), match.group(2))
    return FetchResult("UNKNOWN", "parse-error")


def _sidecar(
    *,
    synth_bytes: int | None = None,
    synth_lines: int | None = None,
    total: int,
    pass_count: int,
    fail_count: int,
    unknown_count: int,
    rows: list[CitationLedgerRow] | None = None,
    status: str | None = None,
    truncation: str = "",
    credibility_hosts: list[str] | None = None,
) -> str:
    if status is not None:
        return (
            "## Citation Validation\n\n"
            "**Validator**: validate-citations.sh v1\n"
            f"**Status**: {status}\n\n"
            "No claims were extracted; Step 3 splice will display this notice.\n"
        )
    if not rows:
        return (
            "## Citation Validation\n\n"
            "**Validator**: validate-citations.sh v1\n"
            f"**Synthesis**: {synth_bytes} bytes, {synth_lines} lines\n"
            "**Claims extracted**: 0\n"
            "**Status counts**: 0 PASS · 0 FAIL · 0 UNKNOWN\n\n"
            "_No citable provenance (URLs, DOIs, file:line) found in the synthesis. Citation validation is a no-op for this report._\n"
        )
    ledger = "".join(
        f"| `{_sanitize_excerpt(row.claim)}` | {row.claim_type} | {row.status} | {row.reason} |  |\n"
        for row in sorted(rows, key=lambda r: (r.claim_type, _sanitize_excerpt(r.claim), r.status, r.reason))
    )
    notice = f"\n_Note: {truncation}_\n" if truncation else ""
    return (
        "## Citation Validation\n\n"
        "**Validator**: validate-citations.sh v1\n"
        f"**Synthesis**: {synth_bytes} bytes, {synth_lines} lines\n"
        f"**Claims extracted**: {total}\n"
        f"**Status counts**: {pass_count} PASS · {fail_count} FAIL · {unknown_count} UNKNOWN\n\n"
        "| Claim | Type | Status | Reason | Cited by |\n"
        "|---|---|---|---|---|\n"
        f"{ledger}{notice}{_render_credibility_block(credibility_hosts or [])}"
    )


def validate_citations( *,
    report: Path,
    output: Path,
    tmpdir: Path,
    budget_seconds: int = 300,
    per_fetch_timeout: int = 10,
    max_claims: int = 200,
    fetcher: Callable[[str], FetchResult] | None = None,
    git_root: Path | None = None,
    sleeper: Callable[[float], None] | None = None,
) -> tuple[int, int, int, int]:
    if not report.is_file():
        _write_text_atomic(path=output, text=_sidecar(total=0, pass_count=0, fail_count=0, unknown_count=0, status=f"input report not readable: `{report}`"))
        _emit_summary(pass_count=0, fail_count=0, unknown_count=0, total=0)
        return 0, 0, 0, 0
    tmpdir.mkdir(parents=True, exist_ok=True)
    try:
        text = report.read_text(encoding="utf-8", errors="replace")
    except OSError:
        _write_text_atomic(path=output, text=_sidecar(total=0, pass_count=0, fail_count=0, unknown_count=0, status=f"input report not readable: `{report}`"))
        _emit_summary(pass_count=0, fail_count=0, unknown_count=0, total=0)
        return 0, 0, 0, 0
    urls = extract_urls(text)
    dois = extract_dois(text)
    filelines = extract_filelines(text)
    raw_total = len(urls) + len(dois) + len(filelines)
    truncated = raw_total > max_claims
    remaining = max_claims
    urls = urls[:remaining]
    remaining -= len(urls)
    dois = dois[: max(remaining, 0)]
    remaining -= len(dois)
    filelines = filelines[: max(remaining, 0)]
    if not urls and not dois and not filelines:
        _write_text_atomic(path=output, text=_sidecar(synth_bytes=len(text.encode()), synth_lines=len(text.splitlines()), total=0, pass_count=0, fail_count=0, unknown_count=0, rows=[]))
        _emit_summary(pass_count=0, fail_count=0, unknown_count=0, total=0)
        return 0, 0, 0, 0
    try:
        fetch_targets: dict[str, str] = {url: url for url in urls}
        for doi in dois:
            if _VALID_DOI_RE.match(doi):
                fetch_targets[f"doi:{doi}"] = f"https://doi.org/{doi}"
        fetch_results = _parallel_fetch_results(
            fetch_targets,
            budget_seconds=budget_seconds,
            per_fetch_timeout=per_fetch_timeout,
            fetcher=fetcher,
            sleeper=sleeper,
        ) if fetch_targets else {}
        rows: list[CitationLedgerRow] = []
        credibility_hosts: list[str] = []
        counts = {"PASS": 0, "FAIL": 0, "UNKNOWN": 0}

        def add_row( *,claim: str, claim_type: str, result: FetchResult) -> None:
            counts[result.status] = counts.get(result.status, 0) + 1
            rows.append(CitationLedgerRow(claim, claim_type, result.status, result.reason))

        for url in urls:
            host = _url_host(url)
            if host:
                credibility_hosts.append(host)
            add_row(claim=url, claim_type="url", result=fetch_results.get(url, FetchResult("UNKNOWN", "timeout")))
        for doi in dois:
            if not _VALID_DOI_RE.match(doi):
                add_row(claim=doi, claim_type="doi", result=FetchResult("FAIL", "doi-syntax"))
                continue
            credibility_hosts.append("doi.org")
            raw = fetch_results.get(f"doi:{doi}", FetchResult("UNKNOWN", "timeout"))
            if raw.status == "PASS" or raw.token() == "UNKNOWN(redirect-not-followed)":
                add_row(claim=doi, claim_type="doi", result=FetchResult("PASS"))
            else:
                add_row(claim=doi, claim_type="doi", result=FetchResult("UNKNOWN", "doi-unresolved"))
        for cite in filelines:
            add_row(claim=cite, claim_type="file-line", result=check_fileline(cite, git_root=git_root))
        total = len(rows)
        truncation = ""
        if truncated:
            truncation = f"claim count exceeded `--max-claims={max_claims}`. Excess claims were dropped from the ledger; consider re-running with `--max-claims` raised."
        _write_text_atomic(
            path=output,
            text=_sidecar(
                synth_bytes=len(text.encode()),
                synth_lines=len(text.splitlines()),
                total=total,
                pass_count=counts.get("PASS", 0),
                fail_count=counts.get("FAIL", 0),
                unknown_count=counts.get("UNKNOWN", 0),
                rows=rows,
                truncation=truncation,
                credibility_hosts=credibility_hosts,
            ),
        )
        _emit_summary(pass_count=counts.get("PASS", 0), fail_count=counts.get("FAIL", 0), unknown_count=counts.get("UNKNOWN", 0), total=total)
        return counts.get("PASS", 0), counts.get("FAIL", 0), counts.get("UNKNOWN", 0), total
    except OSError:
        _write_text_atomic(
            path=output,
            text=_sidecar(total=0, pass_count=0, fail_count=0, unknown_count=0, status="validation interrupted: filesystem error"),
        )
        _emit_summary(pass_count=0, fail_count=0, unknown_count=0, total=0)
        return 0, 0, 0, 0
    except Exception:
        _write_text_atomic(
            path=output,
            text=_sidecar(total=0, pass_count=0, fail_count=0, unknown_count=0, status="validation interrupted: unexpected error"),
        )
        _emit_summary(pass_count=0, fail_count=0, unknown_count=0, total=0)
        return 0, 0, 0, 0


def _pre_help( *,argv: list[str], usage: str) -> bool:
    if any(arg in {"-h", "--help"} for arg in argv):
        print(usage)
        return True
    return False


def validate_citations_main(argv: list[str]) -> int:
    usage = "Usage: validate-citations --report <path> --output <path> --tmpdir <path> [--budget-seconds N] [--per-fetch-timeout N] [--max-claims N]"
    if _pre_help(argv=argv, usage=usage):
        return 0
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--report")
    parser.add_argument("--output")
    parser.add_argument("--tmpdir")
    parser.add_argument("--budget-seconds", default="300")
    parser.add_argument("--per-fetch-timeout", default="10")
    parser.add_argument("--max-claims", default="200")
    try:
        ns, extra = parser.parse_known_args(argv)
        if extra or not ns.report or not ns.output or not ns.tmpdir:
            _usage(usage)
            return 2
        logging_util.quiet_init(argv0="validate-citations")
        try:
            budget = _positive_int(value=ns.budget_seconds, flag="--budget-seconds")
            per_fetch = _positive_int(value=ns.per_fetch_timeout, flag="--per-fetch-timeout")
            max_claims = _positive_int(value=ns.max_claims, flag="--max-claims")
        except ValueError as exc:
            out = Path(ns.output)
            _write_text_atomic(path=out, text=_sidecar(total=0, pass_count=0, fail_count=0, unknown_count=0, status=f"invalid argument ({exc}); sidecar is degraded"))
            _emit_summary(pass_count=0, fail_count=0, unknown_count=0, total=0)
            _usage(f"validate-citations: {exc}")
            return 2
    except SystemExit:
        return 2
    validate_citations(report=Path(ns.report), output=Path(ns.output), tmpdir=Path(ns.tmpdir), budget_seconds=budget, per_fetch_timeout=per_fetch, max_claims=max_claims)
    return 0


def render_findings_batch( *,
    report: Path,
    output: Path,
    research_question_file: Path,
    branch: str,
    commit: str,
    timestamp: str | None = None,
) -> tuple[int, bool]:
    if not report.is_file():
        raise FileNotFoundError(str(report))
    try:
        report_text = report.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise FileNotFoundError(str(report)) from exc
    question = ""
    if research_question_file.is_file():
        try:
            question_lines = research_question_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            question_lines: list[str] = []
        for line in question_lines:
            if line.strip():
                question = line
                break
    if not question:
        question = "(research question unavailable)"
    timestamp = timestamp or _dt.datetime.now(tz=_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    count, payload, section_absent = rendering.render_findings_issue_batch(
        report_text,
        research_question=question,
        branch=branch,
        commit=commit,
        timestamp=timestamp,
    )
    _write_text_atomic(path=output, text=payload)
    return count, section_absent


def render_findings_batch_main(argv: list[str]) -> int:
    usage = "Usage: render-findings-batch --report <path> --output <path> --research-question-file <path> --branch <value> --commit <value>"
    if _pre_help(argv=argv, usage=usage):
        return 0
    parser = argparse.ArgumentParser(add_help=False)
    for flag in ("--report", "--output", "--research-question-file", "--branch", "--commit"):
        parser.add_argument(flag)
    try:
        ns, extra = parser.parse_known_args(argv)
    except SystemExit:
        return 1
    if extra or not all(getattr(ns, name) for name in ["report", "output", "research_question_file", "branch", "commit"]):
        _usage(usage)
        return 1
    logging_util.quiet_init(argv0="render-findings-batch")
    try:
        count, absent = render_findings_batch(report=Path(ns.report), output=Path(ns.output), research_question_file=Path(ns.research_question_file), branch=ns.branch, commit=ns.commit)
    except FileNotFoundError:
        logging_util.diagnostic(f"ERROR: report file not found: {ns.report}")
        return 2
    logging_util.emit_kv(key="COUNT", value=str(count))
    if count == 0:
        if absent:
            logging_util.diagnostic("WARNING: Findings Summary section not found in input (input may be malformed). The sidecar is empty; '/issue --input-file <path>' on it would create no issues.")
        else:
            logging_util.diagnostic("WARNING: Findings Summary section is empty (zero findings). The sidecar is empty; '/issue --input-file <path>' on it would create no issues.")
        return 3
    return 0


def _sanitize_planner_line(line: str) -> str:
    line = "".join(ch for ch in line if ch == "\t" or (ch >= " " and ch != "\x7f"))
    line = line.replace("\t", " ")
    line = re.sub(r"^[ \t]*[-*][ \t]+", "", line)
    return line.strip()


def run_research_planner( *,raw: Path, output: Path) -> tuple[str, int]:
    if not raw.is_file() or raw.stat().st_size == 0:
        return "empty_input", 1
    if not output.parent.is_dir():
        return "bad_path", 2
    try:
        raw_lines = raw.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return "empty_input", 1
    questions = [line for line in (_sanitize_planner_line(line) for line in raw_lines) if line and line.endswith("?")]
    if any("||" in question for question in questions):
        return "delimiter_collision", 1
    if len(questions) < 2:
        return "count_below_minimum", 1
    if len(questions) > 4:
        return "count_above_maximum", 1
    _write_text_atomic(path=output, text="\n".join(questions) + "\n")
    return "success", 0


def run_research_planner_main(argv: list[str]) -> int:
    usage = "Usage: run-planner --raw <path> --output <path>"
    if _pre_help(argv=argv, usage=usage):
        return 0
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--raw")
    parser.add_argument("--output")
    try:
        ns, extra = parser.parse_known_args(argv)
    except SystemExit:
        logging_util.emit_kv(key="REASON", value="missing_arg")
        return 2
    logging_util.quiet_init(argv0="run-planner")
    if extra or not ns.raw or not ns.output:
        logging_util.emit_kv(key="REASON", value="missing_arg")
        return 2
    reason, code = run_research_planner(raw=Path(ns.raw), output=Path(ns.output))
    if reason == "success":
        count = len(Path(ns.output).read_text(encoding="utf-8").splitlines())
        logging_util.emit_kv(key="COUNT", value=str(count))
        logging_util.emit_kv(key="OUTPUT", value=ns.output)
    else:
        logging_util.emit_kv(key="REASON", value=reason)
    return code


def compute_research_banner(path: Path) -> str:
    if not path.is_file():
        return ""
    count = 0
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if re.match(r"^RESEARCH_[A-Z_]+_STATUS=fallback_", line):
                count += 1
    except OSError:
        return ""
    if count < 1:
        return ""
    return BANNER_TEMPLATE.replace("<N_FALLBACK>", str(count))


def compute_research_banner_main(argv: list[str]) -> int:
    usage = "Usage: banner <lane-status.txt>"
    if _pre_help(argv=argv, usage=usage):
        return 0
    logging_util.quiet_init(argv0="research-banner")
    if len(argv) < 1:
        logging_util.diagnostic("WARNING: research banner requires <lane-status.txt-path>; emitting empty banner")
        return 0
    banner = compute_research_banner(Path(argv[0]))
    if banner:
        logging_util.emit(banner)
    return 0
