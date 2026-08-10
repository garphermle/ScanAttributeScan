#!/usr/bin/env bash
# Script to launch ScanAttribute Desktop App using pdfsplit's virtual environment or system python3

VENV_PYTHON="/home/garpherm/VNPT/Source/pdfsplit/.venv/bin/python"

if [ -f "$VENV_PYTHON" ]; then
    PYTHON_BIN="$VENV_PYTHON"
else
    PYTHON_BIN="python3"
fi

export PYTHONPATH="/home/garpherm/VNPT/Source/scan_attribute:$PYTHONPATH"

echo "🚀 Starting ScanAttribute Tool with $PYTHON_BIN..."
exec "$PYTHON_BIN" -m scan_attribute.main "$@"
