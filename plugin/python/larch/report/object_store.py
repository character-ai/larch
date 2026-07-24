"""Provider-neutral object transport for larch run archives."""
from __future__ import annotations
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from contextlib import suppress
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, NamedTuple, cast
from urllib.parse import urlsplit
from larch.core import config, proc
from larch.core.repo_roots import larch_entrypoint
_GCS_ERRORS: Final = {2: "invalid-response", 3: "authentication", 4: "already-exists", 5: "not-found", 6: "local-io"}
ObjectStoreErrorKind: Any = StrEnum("ObjectStoreErrorKind", {"CONFIGURATION": "configuration", "AUTHENTICATION": "authentication", "ALREADY_EXISTS": "already-exists", "NOT_FOUND": "not-found", "LOCAL_IO": "local-io", "INVALID_RESPONSE": "invalid-response", "TRANSPORT": "transport"})
class ObjectStoreError(RuntimeError):
    """A normalized provider failure containing no provider diagnostics."""

    def __init__(self, kind: Any, provider: str, operation: str) -> None:
        self.kind, self.provider, self.operation = kind, provider, operation
        super().__init__(f"{provider} object {operation} failed ({kind.value})")
class RemoteObject(NamedTuple):
    key: str
    size: int
    etag: str | None
    version: str | None
class CommandObjectStore:
    """S3/R2 CLI and verified GCS Rust-command adapter."""

    def __init__(self, root: Any, runner: proc.Runner, endpoint: str | None = None) -> None:
        self.root, self.runner, self.endpoint = root, runner, endpoint
    def _key(self, relative: str, *, empty: bool = False) -> str:
        parts = relative.split("/") if relative else []
        invalid = relative.startswith("/") or (not relative and not empty)
        invalid = invalid or any(not part or part in {".", ".."} or any(ord(char) < 32 or ord(char) == 127 for char in part) for part in parts)  # noqa: PLR2004 - ASCII control bounds
        if invalid:
            raise ObjectStoreError(ObjectStoreErrorKind.CONFIGURATION, self.root.scheme, "key")
        return f"{self.root.prefix}/{relative}" if relative else f"{self.root.prefix}/"
    def _list_prefix(self, relative: str) -> str:
        trailing = relative.endswith("/")
        normalized = relative[:-1] if trailing else relative
        if trailing and not normalized:
            raise ObjectStoreError(ObjectStoreErrorKind.CONFIGURATION, self.root.scheme, "key")
        return self._key(normalized, empty=True) + ("/" if trailing else "")
    def _aws(self, *args: str) -> list[str]:
        return [config.AWS_CLI, *args, *(["--endpoint-url", self.endpoint] if self.endpoint else [])]
    def _gcs(self, operation: str, *args: str) -> list[str]:
        return [str(larch_entrypoint()), "object-store", "gcs", "--operation", operation, "--bucket", self.root.bucket, *args]
    def _run(self, command: Sequence[str], operation: str) -> proc.CommandResult:
        result = self.runner.run(command, timeout=300, check=False)
        if result.returncode:
            raise _command_error(self.root.scheme, operation, result)
        return result
    def _json(self, command: Sequence[str], operation: str) -> dict[str, object]:
        try:
            value: object = json.loads(self._run(command, operation).stdout)
        except json.JSONDecodeError as exc:
            raise ObjectStoreError(ObjectStoreErrorKind.INVALID_RESPONSE, self.root.scheme, operation) from exc
        if not isinstance(value, dict):
            raise ObjectStoreError(ObjectStoreErrorKind.INVALID_RESPONSE, self.root.scheme, operation)
        return cast("dict[str, object]", value)
    def preflight_prefix(self) -> None:
        remote_prefix = self._list_prefix("")
        command = (
            self._gcs("preflight", "--prefix", remote_prefix)
            if self.root.scheme == "gs"
            else self._aws(
                "s3api", "list-objects-v2",
                "--bucket", self.root.bucket,
                "--prefix", remote_prefix,
                "--max-keys", "1",
                "--no-paginate",
                "--output", "json",
            )
        )
        _ = self._run(command, "preflight")
    def list_objects(self, prefix: str = "") -> tuple[RemoteObject, ...]:
        remote_prefix, token = self._list_prefix(prefix), None
        objects: list[RemoteObject] = []
        seen: set[str] = set()
        while True:
            if self.root.scheme == "gs":
                args = ["--prefix", remote_prefix, *( ["--page-token", token] if token else [])]
                page = self._json(self._gcs("list", *args), "list")
                raw, token_value = page.get("objects", []), page.get("next_page_token")
            else:
                args = ["s3api", "list-objects-v2", "--bucket", self.root.bucket, "--prefix", remote_prefix, "--no-paginate", "--output", "json"]
                if token:
                    args.extend(["--continuation-token", token])
                page = self._json(self._aws(*args), "list")
                raw, token_value = page.get("Contents", []), page.get("NextContinuationToken")
            token = token_value if isinstance(token_value, str) and token_value else None
            if not isinstance(raw, list) or token in seen:
                raise ObjectStoreError(ObjectStoreErrorKind.INVALID_RESPONSE, self.root.scheme, "list")
            objects.extend(self._object(item, listed=True) for item in cast("list[object]", raw))
            if token is None:
                return tuple(objects)
            seen.add(token)
    def upload_create(self, key: str, source: Path) -> RemoteObject:
        try:
            if source.is_symlink() or not source.is_file():
                raise OSError
            size = source.stat().st_size
        except OSError as exc:
            raise ObjectStoreError(ObjectStoreErrorKind.LOCAL_IO, self.root.scheme, "upload") from exc
        remote = self._key(key)
        if self.root.scheme == "gs":
            data = self._json(self._gcs("upload-create", "--key", remote, "--source", str(source)), "upload")
            return self._object(data)
        command = self._aws("s3api", "put-object", "--bucket", self.root.bucket, "--key", remote, "--body", str(source), "--if-none-match", "*", "--output", "json")
        return self._object(self._json(command, "upload"), key=key, size=size)
    def download(self, key: str, destination: Path) -> None:
        parent, temporary = destination.parent, None
        if parent.is_symlink() or not parent.is_dir() or destination.is_symlink():
            raise ObjectStoreError(ObjectStoreErrorKind.LOCAL_IO, self.root.scheme, "download")
        try:
            with tempfile.NamedTemporaryFile(dir=parent, prefix=f".{destination.name}.", delete=False) as handle:
                temporary = Path(handle.name)
            remote = self._key(key)
            command = self._gcs("download", "--key", remote, "--destination", str(temporary)) if self.root.scheme == "gs" else self._aws("s3api", "get-object", "--bucket", self.root.bucket, "--key", remote, str(temporary), "--output", "json")
            _ = self._run(command, "download")
            if temporary.is_symlink() or not temporary.is_file():
                raise OSError
            _ = temporary.replace(destination)
            temporary = None
        except OSError as exc:
            raise ObjectStoreError(ObjectStoreErrorKind.LOCAL_IO, self.root.scheme, "download") from exc
        finally:
            if temporary is not None:
                with suppress(OSError):
                    temporary.unlink(missing_ok=True)
    def metadata(self, key: str) -> RemoteObject:
        remote = self._key(key)
        command = self._gcs("metadata", "--key", remote) if self.root.scheme == "gs" else self._aws("s3api", "head-object", "--bucket", self.root.bucket, "--key", remote, "--output", "json")
        return self._object(self._json(command, "metadata"), key=key)
    def _object(self, value: object, *, listed: bool = False, key: str | None = None, size: int | None = None) -> RemoteObject:
        if not isinstance(value, dict):
            raise ObjectStoreError(ObjectStoreErrorKind.INVALID_RESPONSE, self.root.scheme, "response")
        data = cast("dict[str, object]", value)
        lower = self.root.scheme == "gs"
        remote = data.get("key" if lower else "Key") if listed or lower else None
        if key is None:
            root_prefix = f"{self.root.prefix}/"
            if not isinstance(remote, str) or not remote.startswith(root_prefix) or remote == root_prefix:
                raise ObjectStoreError(ObjectStoreErrorKind.INVALID_RESPONSE, self.root.scheme, "response")
            key = remote.removeprefix(root_prefix)
            _ = self._key(key)
        size_field = "size" if lower else ("Size" if listed else "ContentLength")
        raw_size = data.get(size_field) if size is None else size
        if not isinstance(raw_size, int) or isinstance(raw_size, bool) or raw_size < 0:
            raise ObjectStoreError(ObjectStoreErrorKind.INVALID_RESPONSE, self.root.scheme, "response")
        etag, version = data.get("etag" if lower else "ETag"), data.get("version" if lower else "VersionId")
        return RemoteObject(key, raw_size, etag if isinstance(etag, str) and etag else None, version if isinstance(version, str) and version else None)
def object_store_for(root: Any, *, environ: Mapping[str, str] | None = None, runner: proc.Runner | None = None) -> CommandObjectStore:
    active = proc.ProcRunner() if runner is None else runner
    if root.scheme in {"s3", "gs"}:
        return CommandObjectStore(root, active)
    if root.scheme == "r2":
        environment = os.environ if environ is None else environ
        account = environment.get(config.ENV_LARCH_R2_ACCOUNT_ID, "")
        endpoint = environment.get(config.ENV_LARCH_R2_ENDPOINT, "")
        if _valid_r2_endpoint(account, endpoint):
            return CommandObjectStore(root, active, endpoint)
    raise ObjectStoreError(ObjectStoreErrorKind.CONFIGURATION, root.scheme, "configure")
def _valid_r2_endpoint(account: str, endpoint: str) -> bool:
    parsed = urlsplit(endpoint)
    return len(account) == 32 and all(char in "0123456789abcdef" for char in account) and parsed.scheme == "https" and parsed.netloc == f"{account}.r2.cloudflarestorage.com" and parsed.path in {"", "/"} and not parsed.query and not parsed.fragment and parsed.username is None and parsed.password is None  # noqa: PLR2004 - fixed R2 account length
def _command_error(provider: str, operation: str, result: proc.CommandResult) -> ObjectStoreError:
    if provider == "gs":
        kind = ObjectStoreErrorKind(_GCS_ERRORS.get(result.returncode, "transport"))
    else:
        diagnostic = result.stderr.casefold()
        checks = ((ObjectStoreErrorKind.ALREADY_EXISTS, ("preconditionfailed", "status code: 412", "(412)") if operation == "upload" else ()), (ObjectStoreErrorKind.NOT_FOUND, ("nosuchkey", "not found", "status code: 404", "(404)")), (ObjectStoreErrorKind.AUTHENTICATION, ("accessdenied", "access denied", "expiredtoken", "invalidaccesskeyid", "no credentials", "unable to locate credentials")))
        kind = ObjectStoreErrorKind.CONFIGURATION if result.returncode == config.AWS_CLI_NOT_FOUND_EXIT_CODE else next((error for error, markers in checks if any(marker in diagnostic for marker in markers)), ObjectStoreErrorKind.TRANSPORT)
    return ObjectStoreError(kind, provider, operation)
