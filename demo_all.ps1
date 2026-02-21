
cd .

Write-Host "=== DEMO: Integrity ==="
python main.py store README.md
python main.py reconstruct README.md README_restored.md
certutil -hashfile .\README.md SHA256
certutil -hashfile .\README_restored.md SHA256

Write-Host "=== Report ==="
python main.py report
