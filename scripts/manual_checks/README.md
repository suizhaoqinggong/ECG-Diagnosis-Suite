# Manual Checks

This directory contains ad hoc smoke checks that were previously stored as
`test_*.py` files in repository roots.

They are intentionally kept out of automated test discovery because:

- several scripts require local model checkpoints or a running backend;
- some scripts are interactive or expect real ECG sample files;
- they are useful for manual debugging, but not stable CI coverage.

Use automated suites for regular verification:

- Backend: `cd backend && pytest -q tests`
- Frontend: `cd frontend && npm test -- --run`

Run a manual check directly when needed, for example:

```bash
python scripts/manual_checks/check_cardioformer_integration.py
python scripts/manual_checks/check_upload_fix.py /path/to/record.dat /path/to/record.hea
```
