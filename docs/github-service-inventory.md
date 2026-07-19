# GitHub Service Migration Inventory

This inventory separates Rust implementation parity, production consumer
cutover, and Python removal. A Rust adapter does not transfer command ownership
or authorize deletion of the Python path.

| Operation group | Rust implementation | Consumer cutover | Python removal |
|---|---|---|---|
| Repository metadata | Implemented behind `GitHubService` | Not started | Not started |
| Issue get, list, search, create, edit, close | Implemented behind `GitHubService` | Not started | Not started |
| Comment list, create, edit, delete | Implemented behind `GitHubService` | Not started | Not started |
| Label list, create, add, remove | Implemented behind `GitHubService` | Not started | Not started |
| `gh run-logs`, `gh workflow-path` | Complete | Complete | Complete |
| `gh remote-repo`, `gh resolve-repo` | Complete | Complete | Complete |

The implementation uses the authenticated Octocrab adapter from issue #7724.
It does not invoke `gh`, Python, an arbitrary REST path, or another HTTP client.
Repository-resolution commands compose that metadata port with local remotes from
the gix read port (#7734) and own ambient discovery for `OWNER/REPO` slugs.
