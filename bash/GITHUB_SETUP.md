# GitHub setup

This project’s setup script only configures the local Git identity, optionally prepares an SSH key, and optionally adds `origin`. It does **not** stage, commit, create a GitHub repository, or push files.

## 1. Review local files

From the project root:

```bash
git status --short
git status --ignored --short
```

The root `.gitignore` excludes the virtual environment, generated session data, PyCharm settings, and the local `probe_labels.json` file. That file contains probe device IDs and friendly labels. The copied `resources/styles/css/` bundle is also ignored because the app’s PyInstaller spec does not package or reference it.

Review documentation photos, videos, experiment CSVs, and all other files before publishing. They may contain project or personal information you do not want in a public repository.

## 2. Create an empty GitHub repository

Create the repository on GitHub without initializing it with a README, license, or `.gitignore`. Choose private or public intentionally. This avoids unrelated first-commit histories.

## 3. Configure local Git and remote

Run:

```bash
bash bash/github-security.bash
```

Enter a commit name and email if this repository does not already have local settings. The script uses `git config --local`; it does not alter identity settings for your other repositories. If you choose SSH setup, it generates an Ed25519 key only when the selected key path does not already exist and displays only the `.pub` key. Add that public key to GitHub.

When prompted for the repository URL, use one of these forms:

```text
git@github.com:YOUR-ACCOUNT/YOUR-REPOSITORY.git
https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY.git
```

## 4. Stage and inspect before committing

The script deliberately leaves staging and commits to you. For a first commit, stage the files you intend to publish, then inspect the staged names and diff:

```bash
git add .gitignore README.md acquisition bash core docs gui main_gui.spec simulator tools
git status --short
git diff --cached --stat
git diff --cached
```

Add other files only if you reviewed them and want them in the repository. In particular, do not stage `probe_labels.json`, `.venv/`, `data/`, or the ignored copied web bundle.

When the staged changes look right:

```bash
git commit -m "Initial Weber smoker acquisition and simulator"
git push -u origin main
```

If GitHub authentication has not been checked yet, test SSH with `ssh -T git@github.com` after adding the public key, or use the normal GitHub HTTPS authentication flow.
