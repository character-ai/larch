Add a SessionStart reset path that clears only the clone-local `current` progress pointer on fresh `startup` and `clear` events. Preserve run logs, staleness math, and active bgjob protection.
