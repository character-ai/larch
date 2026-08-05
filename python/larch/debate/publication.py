"""Freshness-checked GitHub lifecycle ownership for the public debate skill."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Final, cast

from larch import io as larch_io
from larch.core import config, proc, redact
from larch.errors import ShipError
from larch.git import gh
from larch.issue import issue_mutation, issue_wire

_METADATA_FILENAME: Final = "debate-source.json"


@dataclass(frozen=True)
class SourceMetadata:
    repository: str
    issue: str
    original_title: str
    debating_title: str
    debated_title: str
    prepared_updated_at: str
    issue_url: str


def _root(value: str | Path, *, create: bool = False) -> Path:
    root = Path(value)
    try:
        if create:
            return larch_io.ensure_trusted_directory(root)
        return larch_io.validate_trusted_directory(root)
    except OSError as exc:
        raise ValueError("unsafe debate directory") from exc


def _bounded_subject(*, issue: str, title: str, body: str) -> str:
    clean = redact.redact_outbound(
        f"# Debate subject\n\nSource issue #{issue}: {title}\n\n{body}"
    ).replace("\r", "\n").replace("\x00", "")
    encoded = clean.encode("utf-8")
    if len(encoded) > config.DEBATE_SUBJECT_MAX_BYTES:
        suffix = b"\n\n[subject truncated]\n"
        encoded = encoded[: config.DEBATE_SUBJECT_MAX_BYTES - len(suffix)]
        while True:
            try:
                clean = encoded.decode("utf-8")
                break
            except UnicodeDecodeError:
                encoded = encoded[:-1]
        clean += suffix.decode()
    if not clean.strip():
        raise ValueError("empty debate subject")
    return clean


def _lifecycle_title(prefix: str, original: str) -> str:
    tail_len = config.TRACKING_TITLE_MAX_LEN - len(prefix)
    if tail_len <= 0 or not original:
        raise ValueError("invalid issue title")
    return prefix + original[:tail_len]


def _metadata_path(root: Path) -> Path:
    return root / _METADATA_FILENAME


def _canonical_input_path(*, root: Path, supplied: str | Path, filename: str) -> Path:
    path = Path(supplied)
    path = path if path.is_absolute() else Path.cwd() / path
    if path != root / filename:
        raise ValueError("unexpected debate artifact path")
    return path


def _write_metadata(root: Path, metadata: SourceMetadata) -> None:
    larch_io.trusted_atomic_write(
        _metadata_path(root),
        json.dumps(asdict(metadata), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        root=root,
    )


def _read_metadata(root: Path) -> SourceMetadata:
    try:
        raw: object = json.loads(larch_io.read_trusted_text(_metadata_path(root), root=root, reject_cr=True))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError("invalid debate source metadata") from exc
    expected_keys = {field.name for field in fields(SourceMetadata)}
    if not isinstance(raw, dict):  # pylint: disable=unidiomatic-typecheck  # exact JSON object required
        raise ValueError("invalid debate source metadata")  # noqa: TRY004 - wire validation uses one stable exception
    values = cast("dict[str, object]", raw)
    if set(values) != expected_keys:
        raise ValueError("invalid debate source metadata")
    if not all(isinstance(value, str) and value for value in values.values()):
        raise ValueError("invalid debate source metadata")
    return SourceMetadata(**cast("dict[str, str]", values))


def load_source_metadata(
    *, debate_tmpdir: str | Path, metadata_file: str | Path
) -> SourceMetadata:
    """Load only the canonical preparation artifact under the debate root."""
    root = _root(debate_tmpdir)
    _ = _canonical_input_path(
        root=root,
        supplied=metadata_file,
        filename=_METADATA_FILENAME,
    )
    return _read_metadata(root)


def prepare_issue(*, debate_tmpdir: str | Path, repository: str, issue: str) -> tuple[SourceMetadata, Path]:
    root = _root(debate_tmpdir, create=True)
    snapshot = issue_mutation.read_snapshot(proc, repository=repository, issue=issue)
    if snapshot.state.upper() != "OPEN":
        raise ValueError("source issue is not open")
    if issue_wire.title_lifecycle_reject_marker(snapshot.title):
        raise ValueError("source issue has a protected lifecycle title")
    debating = _lifecycle_title(config.DEBATE_TITLE_PREFIX_BY_STATE["DEBATING"], snapshot.title)
    debated = _lifecycle_title(config.DEBATE_TITLE_PREFIX_BY_STATE["DEBATED"], snapshot.title)
    metadata = SourceMetadata(
        repository=repository,
        issue=issue,
        original_title=snapshot.title,
        debating_title=debating,
        debated_title=debated,
        prepared_updated_at=snapshot.updated_at,
        issue_url=f"https://github.com/{repository}/issues/{issue}",
    )
    subject_path = root / config.DEBATE_SUBJECT_FILENAME
    larch_io.trusted_atomic_write(
        subject_path,
        _bounded_subject(issue=issue, title=snapshot.title, body=snapshot.body),
        root=root,
    )
    _write_metadata(root, metadata)
    return metadata, subject_path


def _transition_target(
    *, metadata: SourceMetadata, snapshot: issue_mutation.IssueSnapshot, mode: str
) -> tuple[str | None, bool]:
    target: str | None
    owned = True
    if mode == "start":
        if snapshot.title == metadata.debating_title:
            target = None
        elif snapshot.title != metadata.original_title or snapshot.updated_at != metadata.prepared_updated_at:
            raise ValueError("source issue changed after preparation")
        else:
            target = metadata.debating_title
    elif mode == "finish":
        if snapshot.title == metadata.debated_title:
            target = None
        elif snapshot.title != metadata.debating_title:
            raise ValueError("source issue title is not owned by this debate")
        else:
            target = metadata.debated_title
    elif mode == "restore":
        if snapshot.title == metadata.debating_title:
            target = metadata.original_title
        else:
            target = None
            owned = False
    else:
        raise ValueError("invalid title transition")
    return target, owned


def transition_title(*, debate_tmpdir: str | Path, mode: str) -> tuple[bool, bool, str]:
    root = _root(debate_tmpdir)
    metadata = _read_metadata(root)
    snapshot = issue_mutation.read_snapshot(
        proc, repository=metadata.repository, issue=metadata.issue
    )
    if mode != "restore" and snapshot.state.upper() != "OPEN":
        raise ValueError("source issue is not open")
    target, owned = _transition_target(metadata=metadata, snapshot=snapshot, mode=mode)
    if target is None:
        return False, owned, snapshot.updated_at
    result = issue_mutation.apply(
        proc,
        issue_mutation.request_for_snapshot(
            snapshot,
            fields=frozenset({issue_mutation.MutationField.TITLE}),
            title=target,
        ),
    )
    return result.after.title != result.before.title, True, result.after.updated_at


def link_proposal_body(
    *, debate_tmpdir: str | Path, body_file: str | Path
) -> Path:
    """Append the canonical source backlink to a synthesized proposal body."""
    root = _root(debate_tmpdir)
    metadata = _read_metadata(root)
    canonical_body = _canonical_input_path(
        root=root,
        supplied=body_file,
        filename=config.DEBATE_PROPOSAL_BODY_FILENAME,
    )
    try:
        body = larch_io.read_trusted_text(canonical_body, root=root, reject_cr=True)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError("invalid proposal body") from exc
    body = redact.redact_outbound(body).strip()
    if not body or "\x00" in body:
        raise ValueError("invalid proposal body")
    linked = (
        f"{body}\n\n## Debate source\n\n"
        f"Source: [#{metadata.issue}]({metadata.issue_url})\n"
    )
    destination = root / config.DEBATE_LINKED_PROPOSAL_BODY_FILENAME
    larch_io.trusted_atomic_write(destination, linked, root=root)
    return destination


def _expected_comment_body(*, marker: str, content: str) -> str:
    if (
        not marker.startswith("<!-- larch:debate-")
        or not marker.endswith(" -->")
        or "\n" in marker
        or "\r" in marker
    ):
        raise ValueError("invalid debate comment marker")
    body = redact.redact_tmpdir_paths(f"{marker}\n\n{content}")
    body = redact.redact_secrets_only(body)
    if "[content truncated" in body:
        raise ValueError("invalid debate comment content")
    return body.rstrip("\n")


def verify_comment(
    *, debate_tmpdir: str | Path, marker: str, content_file: str | Path
) -> str:
    """Re-read one source comment and verify its exact redacted postcondition."""
    root = _root(debate_tmpdir)
    metadata = _read_metadata(root)
    try:
        content = larch_io.read_trusted_text(content_file, root=root, reject_cr=True)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError("invalid debate comment content") from exc
    expected = _expected_comment_body(marker=marker, content=content)
    result = gh.issue_comments_list_read(
        proc,
        metadata.issue,
        repo=metadata.repository,
    )
    if result.returncode != 0:
        raise ValueError("debate comment read-back failed")
    try:
        rows = gh.loads_json_paginated_list(result.stdout or "[]")
    except ShipError as exc:
        raise ValueError("debate comment read-back failed") from exc
    matches: list[tuple[str, str]] = []
    for value in rows:
        if not isinstance(value, dict):
            continue
        row = cast("dict[str, object]", value)
        body = row.get("body")
        comment_id = row.get("id")
        if not isinstance(body, str):
            continue
        first_line = body.split("\n", 1)[0].removeprefix("\ufeff").removesuffix("\r")
        if first_line == marker:
            matches.append((str(comment_id or ""), body.rstrip("\n")))
    if len(matches) != 1 or matches[0][1] != expected or not matches[0][0].isdigit():
        raise ValueError("debate comment postcondition mismatch")
    return matches[0][0]


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def issue_prepare_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py debate issue-prepare")
    _ = parser.add_argument("--debate-tmpdir", required=True)
    _ = parser.add_argument("--repo", required=True)
    _ = parser.add_argument("--issue", required=True)
    try:
        args = parser.parse_args(argv)
        metadata, subject = prepare_issue(
            debate_tmpdir=args.debate_tmpdir,
            repository=args.repo,
            issue=args.issue,
        )
    except (OSError, SystemExit, ValueError, issue_mutation.ProtectedIssueMutation):
        _emit({"ok": False, "operation": "issue-prepare", "error_class": "validation"})
        return config.DEBATE_EXIT_VALIDATION
    _emit(
        {
            "ok": True,
            "operation": "issue-prepare",
            "error_class": None,
            "metadata_path": str(_metadata_path(_root(args.debate_tmpdir))),
            "subject_path": str(subject),
            "source_issue": metadata.issue,
            "source_url": metadata.issue_url,
        }
    )
    return 0


def title_transition_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py debate title-transition")
    _ = parser.add_argument("--debate-tmpdir", required=True)
    _ = parser.add_argument("--mode", choices=("start", "finish", "restore"), required=True)
    try:
        args = parser.parse_args(argv)
        changed, owned, updated_at = transition_title(
            debate_tmpdir=args.debate_tmpdir,
            mode=args.mode,
        )
    except (OSError, SystemExit, ValueError, issue_mutation.ProtectedIssueMutation):
        _emit({"ok": False, "operation": "title-transition", "error_class": "mutation"})
        return config.DEBATE_EXIT_PUBLICATION_FAILURE
    _emit(
        {
            "ok": True,
            "operation": "title-transition",
            "error_class": None,
            "changed": changed,
            "owned": owned,
            "updated_at": updated_at,
        }
    )
    return 0


def proposal_link_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py debate proposal-link")
    _ = parser.add_argument("--debate-tmpdir", required=True)
    _ = parser.add_argument("--body-file", required=True)
    try:
        args = parser.parse_args(argv)
        artifact = link_proposal_body(
            debate_tmpdir=args.debate_tmpdir,
            body_file=args.body_file,
        )
    except (OSError, SystemExit, ValueError):
        _emit({"ok": False, "operation": "proposal-link", "error_class": "validation"})
        return config.DEBATE_EXIT_PUBLICATION_FAILURE
    _emit(
        {
            "ok": True,
            "operation": "proposal-link",
            "error_class": None,
            "artifact_path": str(artifact),
        }
    )
    return 0


def comment_verify_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py debate comment-verify")
    _ = parser.add_argument("--debate-tmpdir", required=True)
    _ = parser.add_argument("--marker", required=True)
    _ = parser.add_argument("--content-file", required=True)
    try:
        args = parser.parse_args(argv)
        comment_id = verify_comment(
            debate_tmpdir=args.debate_tmpdir,
            marker=args.marker,
            content_file=args.content_file,
        )
    except (OSError, SystemExit, ValueError):
        _emit({"ok": False, "operation": "comment-verify", "error_class": "postcondition"})
        return config.DEBATE_EXIT_PUBLICATION_FAILURE
    _emit(
        {
            "ok": True,
            "operation": "comment-verify",
            "error_class": None,
            "comment_id": comment_id,
        }
    )
    return 0
