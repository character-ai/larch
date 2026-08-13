"""Frozen Python behavior for the `/umbrella` cutovers in #8173 and #8174.

This reproduces all eight `/umbrella` verbs from
`python/larch/issue/umbrella.py` as they behaved at cutover, restricted to the
paths a hermetic sandbox can reach. The five record verbs moved to Rust in
#8173; `mutate`, `verify`, and `verify-completion` followed in #8174, and the
whole Python module was removed with them. The reviewed #8454 Rust-only usage
presentation is modeled below so the parity cases continue to pin the current
CLI contract.

Six of the eight verbs never leave the filesystem, so their cases cover the
whole command: the strict `--flag value` scanner, the durable record's exact
JSON bytes, the leaf identity hash, the bound and grammar refusals, the
prepared-partition round trip, the trusted-root confinement, the graph
verification, the completion sentinel's exact bytes, and each state transition.
`prepare` reads one GitHub issue and `mutate` writes one, and the sandbox has
no `gh`, no credential, and no network, so their cases cover the scanner and
every validation that runs before the first request.

The batch grammar is not restated here. `parse_issue_input` is imported from
`issue_input_reference.py`, the frozen owner of that grammar for the #8168
cutover, so the two references cannot drift apart on the parser they share.

Deliberate omissions, none of them part of a command contract:

* `logging_util.quiet_init` file routing, which duplicates the contract streams
  into a per-invocation log while leaving the originals in place.
* The `larch.io` root-owned symlink exemption. Python walked every path
  component and refused a symlink unless `root` owned it, exempting platform
  aliases such as the macOS `/tmp` and `/var`. Every case here names the
  canonicalized parity sandbox, so no exempted alias is on any path.

Seven differences are intentional and documented in the pull request:

* Trusted roots. Python re-derived containment lexically on every read and
  write; Rust resolves each declared root once through the shared
  `TemporaryRoot` owner, which canonicalizes it and refuses a symlinked
  component without the root-owned exemption above.
* Numeric validation. Python used `str.isdecimal()` for `--number` and the
  umbrella number, which also accepted non-ASCII digits such as `١٢`;
  Rust accepts only ASCII decimals, matching the check the prepared edge rows
  already applied.
* Candidate rows. Python compared `isinstance(number, int)`, which admits
  `true` and a negative number and then refused them one step later as an
  invalid leaf number; Rust reads an unsigned integer and reports the same
  ambiguous-recovery refusal for every other spelling. Python also rendered a
  non-string, non-integer `id` through `str()`; Rust keeps it empty.
* Contract-row safety. A resolved URL carrying a line break made Python's
  emitter raise an unhandled error after the record was already written; Rust
  refuses it as an invalid resolved leaf before the write.
* A missing parent directory. Python created one for a published artifact;
  Rust resolves the parent as a trusted root and refuses when it is absent.
* A pull request. `gh issue view` refused a pull-request number outright, so
  Python reported the transport refusal; Rust discriminates the typed read and
  reports the same token.
* Usage text. Python emitted only the machine-readable refusal rows. Rust
  prints a per-verb stderr usage string for `REASON=usage`; this reference
  models that reviewed post-cutover contract.
"""
# ruff: noqa: FBT001, FBT003, PLR0911, PLR0912, PLR0913, C901 - the frozen
# readers and reviewed presentation model preserve their original branch shape.

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from issue_input_reference import parse_issue_input  # noqa: E402

PROPOSAL_MARKER = "larch:umbrella-proposal"
UMBRELLA_PREFIX = "[UMBRELLA]"
LEAF_OPENING_TEMPLATE = "This is a leaf of umbrella #{umbrella}. Read the umbrella in full before acting."
MAX_LEAVES = 30
MIN_PREPARED_LEAVES = 2
MAX_PREPARED_INPUT_BYTES = 262_144
MAX_PREPARED_DEPS_BYTES = 16_384
PREPARED_DEP_FIELD_COUNT = 2
SHA256_HEX_LENGTH = 64
COMPLETION_SENTINEL_VERSION = "2"
MANAGED_PARTITION_PREFIXES = ("[DESIGNING] ", "[IMPLEMENTING] ")
LEAF_STATES = ("pending", "in-flight", "resolved")
REPO_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")

PREPARE_USAGE = "Usage: umbrella prepare --repo OWNER/REPO --issue N --output PATH [--managed-partition true|false]"
PERSIST_PROPOSAL_USAGE = (
    "Usage: umbrella persist-proposal (--proposal PATH --output PATH | --snapshot PATH --prepared-root PATH --prepared-input PATH --prepared-deps PATH --completion-sentinel PATH --output-root PATH --output PATH --issue-input-output PATH --deps-output PATH)"
    "\n--proposal must name a ProposalRecord JSON object with umbrella, repository, expected_updated_at, common_context, and non-empty leaves; see larch_core::issue::umbrella::ProposalRecord."
)
MARK_IN_FLIGHT_USAGE = "Usage: umbrella mark-in-flight --proposal PATH --identity SHA256"
RECORD_RESOLVED_USAGE = "Usage: umbrella record-resolved --proposal PATH --identity SHA256 --number N --url URL [--issue-id ID]"
RECONCILE_IN_FLIGHT_USAGE = "Usage: umbrella reconcile-in-flight --proposal PATH --identity SHA256 --candidates PATH"
MUTATE_USAGE = "Usage: umbrella mutate --repo OWNER/REPO --issue N --title TITLE --body-file PATH [--managed-partition true|false] [--adopted-umbrella true|false]"
VERIFY_USAGE = "Usage: umbrella verify --proposal PATH --leaves PATH [--sentinel-file PATH --sentinel-root PATH --prepared-input PATH --prepared-deps PATH]"
VERIFY_COMPLETION_USAGE = "Usage: umbrella verify-completion --repo OWNER/REPO --issue N --sentinel-file PATH --sentinel-root PATH --prepared-input PATH --prepared-deps PATH"


class UmbrellaError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def emit_kv(key: str, value: object) -> None:
    rendered = "true" if value is True else "false" if value is False else str(value)
    sys.stdout.write(f"{key}={rendered}\n")
    sys.stdout.flush()


def emit_error(reason: str) -> int:
    emit_kv("UMBRELLA_FAILED", True)
    emit_kv("REASON", reason)
    return 2


def usage_error(usage: str) -> int:
    sys.stderr.write(f"{usage}\n")
    return emit_error("usage")


def validate_repo_slug(value: str) -> bool:
    if not value or "\n" in value or "\r" in value:
        return False
    if value.startswith(("--", "/")) or "../" in value or "\\" in value:
        return False
    return REPO_RE.fullmatch(value) is not None and not any(
        part in {".", ".."} for part in value.split("/")
    )


def parse_values(argv: list[str], permitted: set[str]) -> dict[str, str] | None:
    values: dict[str, str] = {}
    index = 0
    while index < len(argv):
        if argv[index] not in permitted or argv[index] in values or index + 1 >= len(argv):
            return None
        values[argv[index]] = argv[index + 1]
        index += 2
    return values


def leaf_opening(umbrella: str) -> str:
    return LEAF_OPENING_TEMPLATE.format(umbrella=umbrella)


def leaf_identity(title: str, body: str) -> str:
    return hashlib.sha256(f"{title.strip()}\n{body}".encode()).hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def valid_sha256(value: str) -> bool:
    return len(value) == SHA256_HEX_LENGTH and value.isascii() and all(char in "0123456789abcdef" for char in value)


def require_positive(value: str, name: str) -> None:
    if not value.isdecimal() or value == "0":
        raise UmbrellaError(f"invalid-{name}")


def managed_partition_title(title: str) -> bool:
    return title.startswith(MANAGED_PARTITION_PREFIXES)


# --- the trusted-path readers `larch.io` provided -------------------------


def absolute_lexical(path: Path) -> Path:
    return path if path.is_absolute() else Path.cwd() / path


def assert_contained(path: Path, root: Path) -> tuple[Path, Path]:
    absolute_path = absolute_lexical(path)
    absolute_root = absolute_lexical(root)
    try:
        _ = absolute_path.relative_to(absolute_root)
    except ValueError as exc:
        raise OSError(f"artifact path escapes trusted root: {path}") from exc
    return absolute_path, absolute_root


def assert_no_symlink_components(path: Path) -> None:
    current = path
    while True:
        try:
            mode_stat = current.lstat()
        except FileNotFoundError:
            pass
        else:
            if stat.S_ISLNK(mode_stat.st_mode) and mode_stat.st_uid != 0:
                raise OSError(f"refusing symlinked path or ancestor: {current}")
        if current == current.parent:
            return
        current = current.parent


def validate_trusted_directory(path: Path, root: Path | None = None) -> Path:
    directory = absolute_lexical(path)
    if root is not None:
        _ = assert_contained(directory, root)
    assert_no_symlink_components(directory)
    try:
        mode = directory.lstat().st_mode
    except FileNotFoundError as exc:
        raise OSError(f"trusted artifact directory is missing: {directory}") from exc
    if not stat.S_ISDIR(mode):
        raise OSError(f"trusted artifact root is not a directory: {directory}")
    return directory


def trusted_file_present(path: Path, root: Path) -> bool:
    absolute_path, absolute_root = assert_contained(path, root)
    _ = validate_trusted_directory(absolute_root)
    assert_no_symlink_components(absolute_path.parent)
    try:
        mode = absolute_path.lstat().st_mode
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise OSError(f"trusted artifact is not a regular file: {absolute_path}")
    return True


def read_trusted_text(path: Path, root: Path, reject_cr: bool = False) -> str:
    absolute_path, absolute_root = assert_contained(path, root)
    _ = validate_trusted_directory(absolute_root)
    assert_no_symlink_components(absolute_path)
    with absolute_path.open("r", encoding="utf-8", newline="") as handle:
        text = handle.read()
    if reject_cr and "\r" in text:
        msg = f"carriage return not allowed in {path}"
        raise ValueError(msg)
    return text


def atomic_write(path: Path, text: str) -> None:
    destination = absolute_lexical(path)
    assert_no_symlink_components(destination)
    if destination.is_symlink():
        raise OSError(f"refusing to write through symlink: {destination}")
    temporary = destination.parent / f".{destination.name}.tmp"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
        _ = handle.write(text)
    os.replace(temporary, destination)


def trusted_atomic_write(path: Path, text: str, root: Path) -> None:
    destination, absolute_root = assert_contained(path, root)
    _ = validate_trusted_directory(absolute_root)
    _ = validate_trusted_directory(destination.parent, absolute_root)
    atomic_write(destination, text)


# --- the durable record ---------------------------------------------------


def proposal_text(proposal: dict[str, object]) -> str:
    return json.dumps(proposal, sort_keys=True, separators=(",", ":")) + "\n"


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UmbrellaError("invalid-proposal-record") from exc


def string_value(value: object, reason: str) -> str:
    if not isinstance(value, str):
        raise UmbrellaError(reason)
    return value


def expected_leaf(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise UmbrellaError("invalid-proposal-record")
    identity = string_value(value.get("identity"), "invalid-proposal-record")
    title = string_value(value.get("title"), "invalid-proposal-record")
    body = string_value(value.get("body"), "invalid-proposal-record")
    state = string_value(value.get("state", "pending"), "invalid-proposal-record")
    number = string_value(value.get("number", ""), "invalid-proposal-record")
    url = string_value(value.get("url", ""), "invalid-proposal-record")
    issue_id = string_value(value.get("issue_id", ""), "invalid-proposal-record")
    if state not in LEAF_STATES or leaf_identity(title, body) != identity:
        raise UmbrellaError("invalid-proposal-record")
    if state == "resolved" and (not number.isdecimal() or not url):
        raise UmbrellaError("invalid-proposal-record")
    return {
        "identity": identity,
        "title": title,
        "body": body,
        "state": state,
        "number": number,
        "url": url,
        "issue_id": issue_id,
    }


def validate_dependency_graph(leaves: list[dict[str, object]], edges: list[dict[str, str]], reason: str) -> None:
    identities = {str(leaf["identity"]) for leaf in leaves}
    pairs = [(edge["blocker"], edge["blocked"]) for edge in edges]
    if len(set(pairs)) != len(pairs) or any(
        blocker not in identities or blocked not in identities or blocker == blocked
        for blocker, blocked in pairs
    ):
        raise UmbrellaError(reason)
    predecessors: dict[str, set[str]] = {identity: set() for identity in identities}
    for blocker, blocked in pairs:
        predecessors[blocked].add(blocker)
    remaining = dict(predecessors)
    while remaining:
        ready = [identity for identity, blockers in remaining.items() if not blockers & set(remaining)]
        if not ready:
            raise UmbrellaError(reason)
        for identity in ready:
            del remaining[identity]


def load_proposal(path: Path) -> dict[str, object]:
    value = load_json(path)
    if not isinstance(value, dict):
        raise UmbrellaError("invalid-proposal-record")
    umbrella = string_value(value.get("umbrella"), "invalid-proposal-record")
    repository = string_value(value.get("repository"), "invalid-proposal-record")
    updated = string_value(value.get("expected_updated_at"), "invalid-proposal-record")
    context = string_value(value.get("common_context"), "invalid-proposal-record")
    leaves_value = value.get("leaves")
    if not isinstance(leaves_value, list) or not 0 < len(leaves_value) <= MAX_LEAVES:
        raise UmbrellaError("invalid-proposal-record")
    leaves = [expected_leaf(item) for item in leaves_value]
    if len({leaf["identity"] for leaf in leaves}) != len(leaves):
        raise UmbrellaError("invalid-proposal-record")
    identities = {str(leaf["identity"]) for leaf in leaves}
    edges_value = value.get("dependency_edges", [])
    if not isinstance(edges_value, list):
        raise UmbrellaError("invalid-proposal-record")
    edges: list[dict[str, str]] = []
    for item in edges_value:
        if not isinstance(item, dict):
            raise UmbrellaError("invalid-proposal-record")
        blocker = string_value(item.get("blocker"), "invalid-proposal-record")
        blocked = string_value(item.get("blocked"), "invalid-proposal-record")
        if blocker == blocked or blocker not in identities or blocked not in identities:
            raise UmbrellaError("invalid-proposal-record")
        edges.append({"blocker": blocker, "blocked": blocked})
    validate_dependency_graph(leaves, edges, "invalid-proposal-record")
    prepared_input_sha256 = string_value(value.get("prepared_input_sha256", ""), "invalid-proposal-record")
    prepared_deps_sha256 = string_value(value.get("prepared_deps_sha256", ""), "invalid-proposal-record")
    if bool(prepared_input_sha256) != bool(prepared_deps_sha256) or (
        prepared_input_sha256 and (not valid_sha256(prepared_input_sha256) or not valid_sha256(prepared_deps_sha256))
    ):
        raise UmbrellaError("invalid-proposal-record")
    require_positive(umbrella, "umbrella")
    if not validate_repo_slug(repository):
        raise UmbrellaError("invalid-proposal-record")
    return {
        "umbrella": umbrella,
        "repository": repository,
        "expected_updated_at": updated,
        "common_context": context,
        "leaves": leaves,
        "dependency_edges": edges,
        "prepared_input_sha256": prepared_input_sha256,
        "prepared_deps_sha256": prepared_deps_sha256,
        "version": 1,
    }


def persist_proposal(path: Path, proposal: dict[str, object]) -> None:
    if len(list(proposal["leaves"])) > MAX_LEAVES:
        raise UmbrellaError("leaf-cap-exceeded")
    atomic_write(path, proposal_text(proposal))


def prepared_edges(deps_text: str, leaves: list[dict[str, object]]) -> list[dict[str, str]]:
    if "\r" in deps_text:
        raise UmbrellaError("invalid-prepared-dependencies")
    edges: list[dict[str, str]] = []
    seen: set[tuple[int, int]] = set()
    for raw_line in deps_text.splitlines():
        if not raw_line:
            raise UmbrellaError("invalid-prepared-dependencies")
        parts = raw_line.split("\t")
        if len(parts) != PREPARED_DEP_FIELD_COUNT or not all(part.isascii() and part.isdecimal() for part in parts):
            raise UmbrellaError("invalid-prepared-dependencies")
        blocker_index, blocked_index = (int(part) for part in parts)
        if (
            blocker_index < 1
            or blocked_index < 1
            or blocker_index > len(leaves)
            or blocked_index > len(leaves)
            or blocker_index == blocked_index
        ):
            raise UmbrellaError("invalid-prepared-dependencies")
        index_edge = (blocker_index, blocked_index)
        if index_edge in seen:
            raise UmbrellaError("invalid-prepared-dependencies")
        seen.add(index_edge)
        edges.append(
            {
                "blocker": str(leaves[blocker_index - 1]["identity"]),
                "blocked": str(leaves[blocked_index - 1]["identity"]),
            }
        )
    validate_dependency_graph(leaves, edges, "prepared-dependency-cycle")
    return edges


def prepare_proposal_from_batch(snapshot: dict[str, str], input_text: str, deps_text: str) -> tuple[dict[str, object], str]:
    if len(input_text.encode()) > MAX_PREPARED_INPUT_BYTES or len(deps_text.encode()) > MAX_PREPARED_DEPS_BYTES:
        raise UmbrellaError("prepared-partition-too-large")
    items, mode = parse_issue_input(input_text)
    if mode != "generic" or not MIN_PREPARED_LEAVES <= len(items) <= MAX_LEAVES or any(
        item.malformed
        or not item.title.strip()
        or not item.body.strip()
        or item.title.lstrip().casefold().startswith("[leaf of ")
        for item in items
    ):
        raise UmbrellaError("invalid-prepared-partition")
    leaves: list[dict[str, object]] = []
    batch_parts: list[str] = []
    opening = leaf_opening(snapshot["number"])
    for item in items:
        base_title = item.title.strip()
        leaf_title = f"[LEAF OF {snapshot['number']}] {base_title}"
        leaf_body = f"{opening}\n\n{item.body.strip()}"
        leaves.append(
            {
                "identity": leaf_identity(leaf_title, leaf_body),
                "title": leaf_title,
                "body": leaf_body,
                "state": "pending",
                "number": "",
                "url": "",
                "issue_id": "",
            }
        )
        batch_parts.append(f"### {base_title}\n\n{leaf_body}")
    if len({leaf["identity"] for leaf in leaves}) != len(leaves):
        raise UmbrellaError("invalid-prepared-partition")
    proposal: dict[str, object] = {
        "umbrella": snapshot["number"],
        "repository": snapshot["repository"],
        "expected_updated_at": snapshot["updated_at"],
        "common_context": snapshot["body"],
        "leaves": leaves,
        "dependency_edges": prepared_edges(deps_text, leaves),
        "prepared_input_sha256": text_sha256(input_text),
        "prepared_deps_sha256": text_sha256(deps_text),
        "version": 1,
    }
    issue_input = "\n".join(batch_parts) + "\n"
    round_trip_items, round_trip_mode = parse_issue_input(issue_input)
    prefix = f"[LEAF OF {snapshot['number']}] "
    if round_trip_mode != "generic" or len(round_trip_items) != len(leaves) or any(
        item.title.strip() != str(leaf["title"]).removeprefix(prefix) or item.body != leaf["body"]
        for item, leaf in zip(round_trip_items, leaves, strict=True)
    ):
        raise UmbrellaError("invalid-prepared-partition")
    return proposal, issue_input


def persist_prepared_proposal(values: dict[str, str]) -> dict[str, object]:
    snapshot_path = Path(values["--snapshot"])
    prepared_root = Path(values["--prepared-root"])
    input_path = Path(values["--prepared-input"])
    deps_path = Path(values["--prepared-deps"])
    completion_sentinel_path = Path(values["--completion-sentinel"])
    output_root = Path(values["--output-root"])
    proposal_path = Path(values["--output"])
    issue_input_path = Path(values["--issue-input-output"])
    deps_output_path = Path(values["--deps-output"])
    try:
        all_paths = (
            snapshot_path,
            prepared_root,
            input_path,
            deps_path,
            completion_sentinel_path,
            output_root,
            proposal_path,
            issue_input_path,
            deps_output_path,
        )
        if not all(path.is_absolute() for path in all_paths):
            raise UmbrellaError("invalid-prepared-path")
        _ = validate_trusted_directory(completion_sentinel_path.parent, prepared_root)
        if trusted_file_present(completion_sentinel_path, prepared_root):
            raise UmbrellaError("stale-completion-sentinel")
        snapshot_value = json.loads(read_trusted_text(snapshot_path, output_root))
        if not isinstance(snapshot_value, dict):
            raise TypeError("snapshot is not an object")
        snapshot = {
            field: string_value(snapshot_value.get(field), "invalid-snapshot")
            for field in ("repository", "number", "title", "body", "state", "updated_at")
        }
        require_positive(snapshot["number"], "umbrella")
        if (
            not validate_repo_slug(snapshot["repository"])
            or snapshot["state"].upper() != "OPEN"
            or not snapshot["updated_at"]
            or not managed_partition_title(snapshot["title"])
        ):
            raise UmbrellaError("invalid-snapshot")
        input_text = read_trusted_text(input_path, prepared_root)
        deps_text = read_trusted_text(deps_path, prepared_root)
        proposal, issue_input = prepare_proposal_from_batch(snapshot, input_text, deps_text)
        trusted_atomic_write(proposal_path, proposal_text(proposal), output_root)
        trusted_atomic_write(issue_input_path, issue_input, output_root)
        trusted_atomic_write(deps_output_path, deps_text, output_root)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise UmbrellaError("invalid-prepared-partition") from exc
    return proposal


def mark_in_flight(proposal_path: Path, identity: str) -> dict[str, object]:
    proposal = load_proposal(proposal_path)
    found = False
    leaves: list[dict[str, object]] = []
    for leaf in list(proposal["leaves"]):
        if leaf["identity"] == identity:
            if leaf["state"] == "resolved":
                raise UmbrellaError("leaf-already-resolved")
            leaves.append({**leaf, "state": "in-flight"})
            found = True
        else:
            leaves.append(leaf)
    if not found:
        raise UmbrellaError("unknown-leaf-identity")
    updated = {**proposal, "leaves": leaves}
    persist_proposal(proposal_path, updated)
    return updated


def record_resolved(proposal_path: Path, identity: str, number: str, url: str, issue_id: str = "") -> dict[str, object]:
    require_positive(number, "leaf")
    if not url:
        raise UmbrellaError("invalid-resolved-leaf")
    proposal = load_proposal(proposal_path)
    leaves: list[dict[str, object]] = []
    found = False
    for leaf in list(proposal["leaves"]):
        if leaf["identity"] == identity:
            leaves.append({**leaf, "state": "resolved", "number": number, "url": url, "issue_id": issue_id})
            found = True
        else:
            leaves.append(leaf)
    if not found:
        raise UmbrellaError("unknown-leaf-identity")
    updated = {**proposal, "leaves": leaves}
    persist_proposal(proposal_path, updated)
    return updated


def reconcile_in_flight(proposal: dict[str, object], identity: str, candidates: list[dict[str, object]]) -> dict[str, str]:
    leaf = next((item for item in list(proposal["leaves"]) if item["identity"] == identity), None)
    umbrella = str(proposal["umbrella"])
    keeps_contract = leaf is not None and str(leaf["title"]).startswith(f"[LEAF OF {umbrella}]") and str(leaf["body"]).startswith(leaf_opening(umbrella))
    if leaf is None or leaf["state"] != "in-flight" or not keeps_contract:
        raise UmbrellaError("ambiguous-in-flight-recovery")
    matches: list[dict[str, str]] = []
    for row in candidates:
        title = row.get("title")
        body = row.get("body")
        number = row.get("number")
        url = row.get("url")
        issue_id = row.get("id", "")
        if title == leaf["title"] and body == leaf["body"] and isinstance(number, int) and isinstance(url, str) and url:
            matches.append({"identity": identity, "number": str(number), "url": url, "issue_id": str(issue_id)})
    if len(matches) != 1:
        raise UmbrellaError("ambiguous-in-flight-recovery")
    return matches[0]


# --- the completion half ---------------------------------------------------


def leaf_contract(leaf: dict[str, object], umbrella: str) -> bool:
    return str(leaf["title"]).startswith(f"[LEAF OF {umbrella}]") and str(leaf["body"]).startswith(
        leaf_opening(umbrella)
    )


def prepared_graph_sha256(proposal: dict[str, object]) -> str:
    shape = {
        "leaves": [
            {"identity": leaf["identity"], "title": leaf["title"], "body": leaf["body"]}
            for leaf in list(proposal["leaves"])
        ],
        "dependency_edges": [
            {"blocker": edge["blocker"], "blocked": edge["blocked"]}
            for edge in list(proposal["dependency_edges"])
        ],
    }
    return text_sha256(json.dumps(shape, sort_keys=True, separators=(",", ":")))


def immutable_proposal_shape(proposal: dict[str, object]) -> tuple[object, object]:
    leaves = tuple(
        (leaf["identity"], leaf["title"], leaf["body"]) for leaf in list(proposal["leaves"])
    )
    edges = tuple((edge["blocker"], edge["blocked"]) for edge in list(proposal["dependency_edges"]))
    return leaves, edges


def write_completion_sentinel(
    proposal: dict[str, object],
    sentinel_file: str,
    sentinel_root: str,
    prepared_input: str,
    prepared_deps: str,
) -> None:
    live_input = read_trusted_text(Path(prepared_input), Path(sentinel_root))
    live_deps = read_trusted_text(Path(prepared_deps), Path(sentinel_root))
    expected_proposal, _issue_input = prepare_proposal_from_batch(
        {
            "repository": str(proposal["repository"]),
            "number": str(proposal["umbrella"]),
            "title": "",
            "body": str(proposal["common_context"]),
            "state": "OPEN",
            "updated_at": str(proposal["expected_updated_at"]),
        },
        live_input,
        live_deps,
    )
    if (
        not proposal["prepared_input_sha256"]
        or text_sha256(live_input) != proposal["prepared_input_sha256"]
        or text_sha256(live_deps) != proposal["prepared_deps_sha256"]
        or immutable_proposal_shape(proposal) != immutable_proposal_shape(expected_proposal)
    ):
        raise UmbrellaError("stale-prepared-partition")
    trusted_atomic_write(
        Path(sentinel_file),
        f"UMBRELLA_SENTINEL_VERSION={COMPLETION_SENTINEL_VERSION}\n"
        f"REPOSITORY={proposal['repository']}\n"
        f"UMBRELLA_NUMBER={proposal['umbrella']}\n"
        f"PREPARED_INPUT_SHA256={proposal['prepared_input_sha256']}\n"
        f"PREPARED_DEPS_SHA256={proposal['prepared_deps_sha256']}\n"
        f"PREPARED_GRAPH_SHA256={prepared_graph_sha256(expected_proposal)}\n"
        "GRAPH_VERIFIED=true\n",
        Path(sentinel_root),
    )


def completion_paths(values: dict[str, str]) -> tuple[str, str, str, str] | None:
    flags = ("--sentinel-file", "--sentinel-root", "--prepared-input", "--prepared-deps")
    if not any(flag in values for flag in flags):
        return "", "", "", ""
    if not all(flag in values and values[flag] for flag in flags):
        return None
    return values[flags[0]], values[flags[1]], values[flags[2]], values[flags[3]]


# --- the eight entrypoints -------------------------------------------------


def prepare_main(argv: list[str]) -> int:
    values = parse_values(argv, {"--repo", "--issue", "--output", "--managed-partition"})
    if values is None or not {"--repo", "--issue", "--output"} <= values.keys():
        return usage_error(PREPARE_USAGE)
    managed = values.get("--managed-partition", "false")
    if managed not in {"true", "false"}:
        return usage_error(PREPARE_USAGE)
    if not validate_repo_slug(values["--repo"]) or not values["--issue"].isdecimal() or values["--issue"] == "0":
        return emit_error("invalid-identity")
    msg = "the sandbox cannot reach the GitHub read this case would perform"
    raise NotImplementedError(msg)


def persist_proposal_main(argv: list[str]) -> int:
    permitted = {
        "--proposal",
        "--snapshot",
        "--prepared-root",
        "--prepared-input",
        "--prepared-deps",
        "--completion-sentinel",
        "--output-root",
        "--output",
        "--issue-input-output",
        "--deps-output",
    }
    values = parse_values(argv, permitted)
    if values is None:
        return usage_error(PERSIST_PROPOSAL_USAGE)
    prepared_mode = "--proposal" not in values
    try:
        if "--proposal" in values:
            if set(values) != {"--proposal", "--output"}:
                return usage_error(PERSIST_PROPOSAL_USAGE)
            proposal = load_proposal(Path(values["--proposal"]))
            persist_proposal(Path(values["--output"]), proposal)
        else:
            required = permitted - {"--proposal"}
            if set(values) != required:
                return usage_error(PERSIST_PROPOSAL_USAGE)
            proposal = persist_prepared_proposal(values)
    except UmbrellaError as exc:
        return emit_error(exc.reason)
    except OSError:
        return emit_error("proposal-write-failed")
    emit_kv("PROPOSAL_PERSISTED", True)
    if prepared_mode:
        emit_kv("LEAF_COUNT", len(list(proposal["leaves"])))
    return 0


def mark_in_flight_main(argv: list[str]) -> int:
    values = parse_values(argv, {"--proposal", "--identity"})
    if values is None or not {"--proposal", "--identity"} <= values.keys():
        return usage_error(MARK_IN_FLIGHT_USAGE)
    try:
        _ = mark_in_flight(Path(values["--proposal"]), values["--identity"])
    except UmbrellaError as exc:
        return emit_error(exc.reason)
    emit_kv("IN_FLIGHT_PERSISTED", True)
    return 0


def record_resolved_main(argv: list[str]) -> int:
    values = parse_values(argv, {"--proposal", "--identity", "--number", "--url", "--issue-id"})
    if values is None or not {"--proposal", "--identity", "--number", "--url"} <= values.keys():
        return usage_error(RECORD_RESOLVED_USAGE)
    try:
        _ = record_resolved(
            Path(values["--proposal"]),
            values["--identity"],
            values["--number"],
            values["--url"],
            values.get("--issue-id", ""),
        )
    except UmbrellaError as exc:
        return emit_error(exc.reason)
    emit_kv("RESOLVED_PERSISTED", True)
    return 0


def reconcile_in_flight_main(argv: list[str]) -> int:
    values = parse_values(argv, {"--proposal", "--identity", "--candidates"})
    if values is None or not {"--proposal", "--identity", "--candidates"} <= values.keys():
        return usage_error(RECONCILE_IN_FLIGHT_USAGE)
    try:
        candidate_value = load_json(Path(values["--candidates"]))
        if not isinstance(candidate_value, list) or not all(isinstance(item, dict) for item in candidate_value):
            raise UmbrellaError("ambiguous-in-flight-recovery")
        result = reconcile_in_flight(
            load_proposal(Path(values["--proposal"])),
            values["--identity"],
            candidate_value,
        )
        _ = record_resolved(
            Path(values["--proposal"]),
            result["identity"],
            result["number"],
            result["url"],
            result["issue_id"],
        )
    except UmbrellaError as exc:
        return emit_error(exc.reason)
    emit_kv("RECONCILED", True)
    emit_kv("ISSUE_NUMBER", result["number"])
    emit_kv("ISSUE_URL", result["url"])
    return 0


def mutate_main(argv: list[str]) -> int:
    values = parse_values(argv, {"--repo", "--issue", "--title", "--body-file", "--managed-partition"})
    if values is None or not {"--repo", "--issue", "--title", "--body-file"} <= values.keys():
        return usage_error(MUTATE_USAGE)
    managed = values.get("--managed-partition", "false")
    if managed not in {"true", "false"}:
        return usage_error(MUTATE_USAGE)
    try:
        body = Path(values["--body-file"]).read_text(encoding="utf-8")
    except OSError:
        return emit_error("mutation-failed")
    if not values["--title"].startswith(UMBRELLA_PREFIX) or PROPOSAL_MARKER not in body:
        return emit_error("invalid-final-umbrella")
    msg = "the sandbox cannot reach the GitHub mutation this case would perform"
    raise NotImplementedError(msg)


def verify_main(argv: list[str]) -> int:
    values = parse_values(
        argv,
        {"--proposal", "--leaves", "--sentinel-file", "--sentinel-root", "--prepared-input", "--prepared-deps"},
    )
    if values is None or not {"--proposal", "--leaves"} <= values.keys():
        return usage_error(VERIFY_USAGE)
    paths = completion_paths(values)
    if paths is None:
        return usage_error(VERIFY_USAGE)
    sentinel_file, sentinel_root, prepared_input, prepared_deps = paths
    try:
        proposal = load_proposal(Path(values["--proposal"]))
        rows_value = load_json(Path(values["--leaves"]))
        if not isinstance(rows_value, list) or not all(isinstance(item, dict) for item in rows_value):
            raise UmbrellaError("incomplete-graph-state")
        for leaf in list(proposal["leaves"]):
            if leaf["state"] != "resolved" or not leaf_contract(leaf, str(proposal["umbrella"])):
                raise UmbrellaError("incomplete-graph-state")
            matching = [row for row in rows_value if str(row.get("number") or "") == leaf["number"]]
            if len(matching) != 1 or matching[0].get("title") != leaf["title"] or matching[0].get("body") != leaf["body"]:
                raise UmbrellaError("incomplete-graph-state")
        if sentinel_file:
            write_completion_sentinel(proposal, sentinel_file, sentinel_root, prepared_input, prepared_deps)
    except OSError:
        return emit_error("sentinel-write-failed")
    except UmbrellaError as exc:
        return emit_error(exc.reason)
    emit_kv("GRAPH_VERIFIED", True)
    return 0


def verify_completion_main(argv: list[str]) -> int:
    required = {"--sentinel-file", "--sentinel-root", "--prepared-input", "--prepared-deps", "--repo", "--issue"}
    values = parse_values(argv, required)
    if values is None or set(values) != required:
        return usage_error(VERIFY_COMPLETION_USAGE)
    try:
        require_positive(values["--issue"], "umbrella")
        if not validate_repo_slug(values["--repo"]):
            raise UmbrellaError("invalid-repository")
        sentinel_text = read_trusted_text(
            Path(values["--sentinel-file"]), Path(values["--sentinel-root"]), reject_cr=True
        )
        rows: dict[str, str] = {}
        for line in sentinel_text.splitlines():
            key, separator, value = line.partition("=")
            if not separator or not key or key in rows:
                raise UmbrellaError("invalid-completion-sentinel")
            rows[key] = value
        if set(rows) != {
            "UMBRELLA_SENTINEL_VERSION",
            "REPOSITORY",
            "UMBRELLA_NUMBER",
            "PREPARED_INPUT_SHA256",
            "PREPARED_DEPS_SHA256",
            "PREPARED_GRAPH_SHA256",
            "GRAPH_VERIFIED",
        }:
            raise UmbrellaError("invalid-completion-sentinel")
        live_input = read_trusted_text(Path(values["--prepared-input"]), Path(values["--sentinel-root"]))
        live_deps = read_trusted_text(Path(values["--prepared-deps"]), Path(values["--sentinel-root"]))
        expected_proposal, _issue_input = prepare_proposal_from_batch(
            {
                "repository": values["--repo"],
                "number": values["--issue"],
                "title": "",
                "body": "",
                "state": "OPEN",
                "updated_at": "",
            },
            live_input,
            live_deps,
        )
        expected_rows = {
            "UMBRELLA_SENTINEL_VERSION": COMPLETION_SENTINEL_VERSION,
            "REPOSITORY": values["--repo"],
            "UMBRELLA_NUMBER": values["--issue"],
            "PREPARED_INPUT_SHA256": text_sha256(live_input),
            "PREPARED_DEPS_SHA256": text_sha256(live_deps),
            "PREPARED_GRAPH_SHA256": prepared_graph_sha256(expected_proposal),
            "GRAPH_VERIFIED": "true",
        }
        if rows != expected_rows:
            raise UmbrellaError("stale-completion-sentinel")
    except (OSError, ValueError, UmbrellaError) as exc:
        return emit_error(getattr(exc, "reason", "invalid-completion-sentinel"))
    emit_kv("UMBRELLA_COMPLETION_VERIFIED", True)
    emit_kv("UMBRELLA_NUMBER", values["--issue"])
    return 0


ENTRYPOINTS = {
    "umbrella-prepare": prepare_main,
    "umbrella-persist-proposal": persist_proposal_main,
    "umbrella-mark-in-flight": mark_in_flight_main,
    "umbrella-record-resolved": record_resolved_main,
    "umbrella-reconcile-in-flight": reconcile_in_flight_main,
    "umbrella-mutate": mutate_main,
    "umbrella-verify": verify_main,
    "umbrella-verify-completion": verify_completion_main,
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ENTRYPOINTS:
        sys.stderr.write(f"unknown umbrella reference entrypoint: {argv[:1]}\n")
        return 64
    return ENTRYPOINTS[argv[0]](argv[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
