# Publishing to GitHub (two accounts)

You can push the **same repo** to two remotes (ErrorCat04 and Nora33400) if both repos exist and you have access.

## 1) Create the repositories (web)
Create:
- https://github.com/ErrorCat04/TileMindFS
- https://github.com/Nora33400/TileMindFS

(Empty repos, no README/License generated on GitHub to avoid merge conflicts.)

## 2) Add two remotes
```powershell
git remote add errorcat https://github.com/ErrorCat04/TileMindFS.git
git remote add nora    https://github.com/Nora33400/TileMindFS.git
git remote -v
```

## 3) Push to both
```powershell
git push -u errorcat main
git push -u nora main
```

### If you get 403 on Nora33400
It means Git is authenticating as the other account (credential manager).
Fix options:

A) Use GitHub CLI to login as Nora33400 then push:
```powershell
& "$env:ProgramFiles\GitHub CLI\gh.exe" auth login
git push -u nora main
```

B) Clear Windows Git credentials for github.com and retry:
- Windows “Credential Manager” -> “Windows Credentials” -> remove `git:https://github.com`
then push again (you will re-enter credentials).

C) Use different remote URLs with a PAT (not recommended to paste in terminal history).
