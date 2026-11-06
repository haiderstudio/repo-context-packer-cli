#!/bin/sh
# Pack the sample repo's code and docs into one plain text file.
# The pack is written outside the sample repo, so the repo is untouched.
# Run from the repo root: sh examples/run-example.sh
set -e
cd "$(dirname "$0")/.."
python3 src/repo_context_packer.py examples/sample-repo src README.md docs -o /tmp/sample-pack.txt
echo "--- first 12 lines of the pack ---"
head -12 /tmp/sample-pack.txt
echo "--- .env is refused even when named ---"
python3 src/repo_context_packer.py examples/sample-repo .env README.md -o /tmp/sample-pack2.txt
grep -c "example-only" /tmp/sample-pack2.txt || true
