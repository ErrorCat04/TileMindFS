
# TileMindFS (V2)

Minimal reproducible user-space tile storage system.

## Features

- SHA256 tile hashing
- Deduplication
- Compression (zlib)
- Reconstruction bit-identical
- Report + Optimizer loop

## Quick Start (Windows PowerShell)

```powershell
python main.py store README.md
python main.py reconstruct README.md README_restored.md
certutil -hashfile .\README.md SHA256
certutil -hashfile .\README_restored.md SHA256
python main.py report
```

## Proof

Reconstruction verified via SHA256.
