# Analyzer state

Run archives are immutable analysis inputs. Stateful analyzers synchronize the
remote run corpus once, then read ordinary files from
`${XDG_CACHE_HOME:-$HOME/.cache}/larch/run-logs/<repo>/` for the rest of the
invocation.

Mutable cursors, ledgers, retry bundles, generated analyses, and generated
measurements do not belong under `run-logs/`. They live at:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/larch/analysis-state/<repo>/<owner>/
```

Repository and owner names remain literal validated path components. Files use
private directories and `0600` modes. Writers use a per-file advisory lock,
atomic replacement, and an expected SHA-256 identity when a workflow carries
state across multiple steps. A stale concurrent writer fails without replacing
the newer file. Corrupt, symlinked, non-regular, or unreadable state fails
closed.

On first access, migrated owners import their former Git or cache file when the
new state file is absent. A warm access never rereads or overwrites from the
legacy path. Run-log cloud sync never lists, downloads, uploads, or interprets
this mutable state tree.
