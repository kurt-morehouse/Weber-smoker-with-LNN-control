#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'HELP'
Usage: bash bash/github-security.bash

Guided local setup for this project’s GitHub workflow. It can initialize the
local repository, set repository-local author identity, prepare an SSH key,
and add a GitHub remote. It never stages, commits, or pushes files.

Create an empty repository on GitHub first, then run this script and enter its
SSH or HTTPS URL when prompted. Review and stage files yourself before commit.
HELP
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    usage
    exit 0
fi
if [[ $# -ne 0 ]]; then
    usage >&2
    exit 2
fi

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

if ! command -v git >/dev/null 2>&1; then
    echo "Git is required. Install Git, then run this script again." >&2
    exit 1
fi

echo "Project: $project_root"
git --version

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Initializing a local repository on branch main."
    git init -b main
else
    echo "Local Git repository already exists."
    if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
        git branch -M main
    fi
fi

current_name="$(git config --local --get user.name || true)"
current_email="$(git config --local --get user.email || true)"
if [[ -z "$current_name" ]]; then
    read -r -p "Name to record on commits: " current_name
    if [[ -z "$current_name" ]]; then
        echo "A commit author name is required." >&2
        exit 1
    fi
    git config --local user.name "$current_name"
else
    echo "Repository-local commit name is already set to: $current_name"
fi

if [[ -z "$current_email" ]]; then
    read -r -p "Email to record on commits (GitHub noreply address is fine): " current_email
    if [[ -z "$current_email" ]]; then
        echo "A commit author email is required." >&2
        exit 1
    fi
    git config --local user.email "$current_email"
else
    echo "Repository-local commit email is already set."
fi

if git remote get-url origin >/dev/null 2>&1; then
    echo "origin is already set to: $(git remote get-url origin)"
else
    read -r -p "GitHub repository URL (SSH/HTTPS; blank to skip): " remote_url
    if [[ -n "$remote_url" ]]; then
        case "$remote_url" in
            git@github.com:*|https://github.com/*)
                git remote add origin "$remote_url"
                echo "Added origin: $remote_url"
                ;;
            *)
                echo "Expected a GitHub.com SSH URL or HTTPS URL; remote was not added." >&2
                exit 1
                ;;
        esac
    else
        echo "Skipped remote setup. Add origin after creating the GitHub repository."
    fi
fi

read -r -p "Prepare an SSH key for GitHub now? [y/N] " prepare_ssh
case "$prepare_ssh" in
    y|Y|yes|YES)
        ssh_key_path="${HOME}/.ssh/id_ed25519"
        read -r -p "SSH key path [$ssh_key_path]: " requested_key_path
        if [[ -n "$requested_key_path" ]]; then
            ssh_key_path="$requested_key_path"
        fi
        mkdir -p "$(dirname -- "$ssh_key_path")"
        if [[ ! -f "$ssh_key_path" ]]; then
            ssh-keygen -t ed25519 -C "$current_email" -f "$ssh_key_path"
        fi
        if [[ ! -f "$ssh_key_path.pub" ]]; then
            echo "Public key not found at $ssh_key_path.pub. No key was displayed." >&2
            exit 1
        fi
        echo
        echo "Add this public key to GitHub → Settings → SSH and GPG keys:"
        cat "$ssh_key_path.pub"
        echo
        read -r -p "Load the key into your SSH agent now? [y/N] " load_key
        case "$load_key" in
            y|Y|yes|YES)
                eval "$(ssh-agent -s)"
                ssh-add "$ssh_key_path"
                ;;
            *)
                echo "Skipped ssh-agent setup."
                ;;
        esac
        ;;
    *)
        echo "Skipped SSH-key setup. HTTPS remotes do not require an SSH key."
        ;;
esac

echo
echo "Setup complete. No files were staged, committed, or pushed."
echo "Review the project before staging:"
echo "  git status --short"
echo "  git status --ignored --short"
echo "Then stage only the files you intend to publish and inspect them before committing."
