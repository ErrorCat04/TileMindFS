
# TileMindFS (V2)

User-space MVP: content-defined chunking (CDC) + tile hashing + dedup + compression + reporting + optimizer loop.

## Quick start (Windows PowerShell)
```powershell
cd .\TileMindFS_V2
python .\main.py store .\README.md
python .\main.py reconstruct README.md .\README_restored.md
certutil -hashfile .\README.md SHA256
certutil -hashfile .\README_restored.md SHA256
python .\main.py report
python .\main.py optimize --interval 5
```

## Commands
- Store (CDC default):
`python main.py store <file>`

- Store (fixed tiles 8KB):
`python main.py store <file> --mode fixed --tile-size 8192`

- Reconstruct:
`python main.py reconstruct <original> <output>`

- Report:
`python main.py report --top 10`

- Optimizer loop:
`python main.py optimize --interval 10 --top 10`


## Proof
See `PROOF.md` and run `demo_all.ps1`.
