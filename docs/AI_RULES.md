# AI Development Rules

**This file is extremely important. All AI assistants MUST adhere to these rules when interacting with this codebase.**

1. **Read documentation before coding**: Always consult `/opt/pisowifi/docs/` (especially `ARCHITECTURE.md` and `PROJECT_MEMORY.md`) before making architectural assumptions.
2. **Never modify unrelated code**: Only touch files and functions strictly necessary for the current task. Do NOT refactor functioning code just because it looks "suboptimal" unless explicitly requested.
3. **Understand architecture before fixing**: If a bug occurs, trace the flow (Hardware -> Network -> Backend -> Frontend) before injecting patches.
4. **Explain root cause first**: When diagnosing a bug, explicitly state the root cause before writing the fix.
5. **Preserve backward compatibility**: API changes must not break existing frontend components. 
6. **Never guess**: If a system behavior (like a `tc` command or a serial payload) is unknown, write a diagnostic script, execute it, and observe the output before committing to a fix.
7. **Read affected files completely**: Never rely on a snippet. Read the entire file to understand the surrounding context.
8. **Verify every API**: Test new API endpoints to ensure they return exactly what the frontend expects.
9. **Verify frontend and backend together**: A fix on the backend must be verified against frontend state behaviors (and vice versa).
10. **Verify race conditions**: Pay special attention to concurrent requests (e.g. two users clicking "Insert Coin" at the same time).
11. **Verify concurrency**: Ensure database locks and serial hardware locks are thread-safe or properly queued.
12. **Verify performance**: Avoid `O(N)` loops over all database rows if it can be filtered in SQL.
13. **Verify security**: Ensure MAC spoofing mitigations exist. Do not trust client-supplied data unconditionally.
14. **Verify database compatibility**: Always write SQLAlchemy migrations or verify SQLite constraints when altering schemas.
15. **Verify Linux services**: Remember that `systemd` services execute with a restricted `$PATH`. Always use absolute paths for system binaries (`/usr/sbin/tc`, `/usr/sbin/ip`).
16. **Verify network behavior**: When modifying `nftables` or `tc`, ensure the rules are both correctly applied AND correctly cleaned up.
17. **Keep code modular**: Respect the Service-Repository pattern. Do not put business logic in API routers.
18. **Keep code consistent**: Follow the existing indentation, naming conventions, and error handling styles.
19. **Avoid duplicated logic**: Reuse existing helper functions and utilities.
20. **Remove dead code only after verification**: Confirm code is truly unreachable before deleting it.
21. **Update documentation after every completed feature**: Keep `PROJECT_MEMORY.md`, `API.md`, and `CHANGELOG.md` perfectly synced with reality before ending a session.
