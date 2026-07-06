# Fork CI dry-runs

`/implement --forked` is for open-source fork workflows where `origin` is the contributor fork and `upstream` is the canonical repository. It runs CI checks against `origin` and `upstream/main` as a dry run: no tracking issue, no merge. Configure remotes before running:

```bash
git remote -v
git remote add upstream git@github.com:OWNER/UPSTREAM.git
```
