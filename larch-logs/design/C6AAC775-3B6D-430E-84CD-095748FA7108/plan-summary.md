Add an explicit Claude subprocess hook exemption. Set it only on spawned Claude children, let `hook-bg-poll-guard.sh` fail open for those children, and pin the behavior with hook and launcher tests.
