"""larch.issue: issue management, OOS, and execution-tracking subsystem.

Home for the issue pipeline:
``issue_wire``, ``tracking_issue``, ``file_oos``, and ``oos``.
``file_oos`` is a retained #7680 helper library;
the six OOS commands migrated by #8178 and #8179, plus execution-issue
workflows, are Rust-owned.
"""
