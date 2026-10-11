# Matapan repository guidance

- Treat `docs/mvp_architecture.md` (v0.6) as the architecture authority. Do not rewrite it as part of implementation work.
- Follow `docs/mvp_code_structure.md` for file organization and implementation sequencing.
- The frontend currently contains placeholders; the local API and initial Revolut import flow are implemented in `backend/`. Implement only the work requested by the user; add future modules when a working feature needs them.
- Keep HTTP handling, persistence, import orchestration, provider parsing, reporting, and frontend integration in the files assigned by the structure guide.
- Use exact money types. Preserve dated observations, source provenance, atomic imports, and user review of ambiguous duplicates.
- Keep private financial exports, credentials, and SQLite data out of Git. Use synthetic or anonymized test fixtures.
- Preserve migration history and user data; never reset a financial database as an implementation shortcut.
- Run checks appropriate to the requested change and report what was verified.
