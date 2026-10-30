#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${project_root}/.venv/bin/python"

if [[ ! -x "${python_bin}" ]]; then
    echo "Python environment not found at ${python_bin}." >&2
    echo "Create it and install acquisition/requirements.txt first; see docs/raspberry_pi_acquisition.md." >&2
    exit 1
fi

cd "${project_root}"
exec "${python_bin}" -m acquisition.main
