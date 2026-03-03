Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

cd "$PSScriptRoot"

Write-Host "`n=== RESET ==="
Remove-Item -Recurse -Force .\data -ErrorAction SilentlyContinue
Remove-Item .\big.txt, .\big2.txt, .\big_copy.txt, .\README_restored.md -ErrorAction SilentlyContinue

Write-Host "`n=== DEMO 1: Integrity ==="
python .\main.py store README.md
python .\main.py reconstruct README.md README_restored.md
certutil -hashfile .\README.md SHA256
certutil -hashfile .\README_restored.md SHA256
python .\main.py report

Write-Host "`n=== DEMO 2: Exact copy dedup ==="
Remove-Item -Recurse -Force .\data -ErrorAction SilentlyContinue
Remove-Item .\big.txt, .\big_copy.txt -ErrorAction SilentlyContinue
for ($i=0; $i -lt 2000; $i++) { Add-Content .\big.txt "LayerOS fractal tile mind system architecture dynamic entropy" }
python .\main.py store big.txt
Copy-Item .\big.txt .\big_copy.txt -Force
python .\main.py store big_copy.txt
python .\main.py report

Write-Host "`n=== DEMO 3: Header shift + CDC dedup ==="
Remove-Item -Recurse -Force .\data -ErrorAction SilentlyContinue
Remove-Item .\big.txt, .\big2.txt -ErrorAction SilentlyContinue
for ($i=0; $i -lt 2000; $i++) { Add-Content .\big.txt "LayerOS fractal tile mind system architecture dynamic entropy" }
"HEADER SHIFT" | Set-Content .\big2.txt
Get-Content .\big.txt | Add-Content .\big2.txt
python .\main.py store big.txt  --avg 4096 --min 1024 --max 8192
python .\main.py store big2.txt --avg 4096 --min 1024 --max 8192
python .\main.py report

Write-Host "`nDONE."
