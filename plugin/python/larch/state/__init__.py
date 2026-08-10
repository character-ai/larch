"""larch.state: session, admission, and run-lifecycle state subsystem.

Home for the state modules that form a coherent lifecycle subsystem:
``session_env``, ``finalize``, ``closeout``, and ``stall_recovery``.
Step 0 bootstrap moved to the Rust owner in #8358; admission moved in #8059.
"""
