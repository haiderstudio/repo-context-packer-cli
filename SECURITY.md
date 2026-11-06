# Security Policy

This tool runs locally, collects no data, sends nothing anywhere, and needs no API key or secret. It only reads the files you name, and it refuses secret files (`.env`, private keys, files with `secret` or `credentials` in the name) even when you name them. It never writes into the repo it packs: the pack goes to standard output, or to a file outside the repo with `-o`.

If you find a case where a secret file ends up in a pack, please open an issue describing the exact commands and input. Do not include any real secret in the report.
