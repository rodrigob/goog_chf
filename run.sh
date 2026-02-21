#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/../streamlit_venv"

source "$VENV/bin/activate"
pip install -q -r "$SCRIPT_DIR/requirements.txt"
exec streamlit run "$SCRIPT_DIR/goog_chf.py" "$@"
