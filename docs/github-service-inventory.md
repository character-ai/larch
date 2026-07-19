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

The implementation uses the authenticated Octocrab adapter from issue #7724.
It does not invoke `gh`, Python, an arbitrary REST path, or another HTTP client.
The existing Python callers and command registry remain authoritative until a
later cutover issue adds black-box parity evidence and changes their ownership.
