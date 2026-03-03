# Proof (Reproducible)

Run the full proof on Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\demo_all.ps1
```

You should observe:

## Demo 1 — Integrity
- `SHA256(README.md) == SHA256(README_restored.md)` via `certutil`

## Demo 2 — Exact copy dedup
- `big_copy.txt` stores **0 new tiles** (all tiles referenced)

## Demo 3 — Header shift (CDC)
- After adding a header, many tiles are still re-used (partial dedup)

Paste your console output in your issue / Reddit thread for verification.
