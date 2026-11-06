# repo-context-packer-cli

Pack selected repo files into one AI-readable text file.

[![CI](https://github.com/haiderstudio/repo-context-packer-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/repo-context-packer-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`repo-context-packer` packs only the files and folders you name into one
plain text file, in the order you name them. The pack starts with a short
header (file count, line count), then a list of the packed files, then
each file's contents under a `==== path ====` heading.

- It packs only what you name. Run it with no paths and it packs
  nothing — there is no whole-repo default.
- It leaves secrets out, even when you name them: `.env`, private keys,
  and files whose names contain `secret` or `credentials` are refused.
- It leaves build output out: `.git`, `node_modules`, `dist`, `build`,
  `__pycache__`, and similar folders are never packed.
- It leaves binary files out (a file with a NUL byte, or text that is
  not valid UTF-8, is skipped).
- It never writes into the repo it packs. The pack goes to standard
  output, or to a file outside the repo with `-o`. It sends nothing
  anywhere — it runs fully offline.

## What it does NOT do

- It does not pack a whole repo. If you want everything, name the
  folders — or use a whole-repo packer (see below).
- It does not read `.gitignore`. It applies its own fixed exclusion
  list, so what is left out is the same on every machine.
- It does not count tokens, compress code, or fetch remote repos.
- It does not upload, send, or share your code. The pack is a file on
  your machine; what you paste from it is your choice.
- It does not fix, delete, or change any file in the repo.

## Who it is for

Anyone who wants to hand a few files — not a whole repo — to an AI
assistant: a bug in two files, a small feature spread over a folder,
a code review of one change. If the model only needs those files, the
pack stays small and the secrets stay out.

## How this differs from similar tools

Whole-repo packers already exist and are good at that job. Repomix
(~28k stars) packs an entire repo into XML, Markdown, or plain text,
with token counts, compression, and remote repos — it needs Node.js.
packdiff (Python, standard library only) packs a whole repo into one
Markdown file with a token estimate and a diff mode.

This tool does a narrower job: it packs only the files you name, in
plain text only, with no token counting, no compression, and no
install — Python 3 and one file. And it refuses secret files even
when you name them, instead of relying on `.gitignore` alone.

## Install

Python standard library only — no packages to download. Clone the repo
and run it in place:

```sh
git clone https://github.com/haiderstudio/repo-context-packer-cli.git
cd repo-context-packer-cli
```

Python 3.9 or newer.

## Usage

```sh
python3 src/repo_context_packer.py <root> <path>... [-o output.txt]
```

`<root>` is the repo folder. `<path>...` are files or folders inside it,
relative to the root, in the order you want them packed. A folder packs
all its files, sorted by name.

Check what would be packed first, without packing anything:

```sh
python3 src/repo_context_packer.py examples/sample-repo src README.md docs --list
```

Real output:

```text
src/app.py
src/util.py
README.md
docs/guide.md
```

Pack to standard output:

```sh
python3 src/repo_context_packer.py examples/sample-repo src README.md docs
```

Real output (first lines; the full pack follows with each file's contents):

```text
# Repo context pack
# Root: sample-repo
# Files: 4
# Lines: 22
# Note: secrets and build outputs were left out.
## Files
src/app.py
src/util.py
README.md
docs/guide.md

==== src/app.py ====
"""Demo shop: add prices and print a total."""
```

The summary line goes to standard error, so the pack on standard output
stays clean when you pipe it:

```text
packed 4 file(s), 22 lines
```

Pack to a file outside the repo:

```sh
python3 src/repo_context_packer.py examples/sample-repo src README.md -o /tmp/pack.txt
```

```text
packed 3 file(s), 19 lines into /tmp/pack.txt
```

`-o` inside the packed root is refused, so the tool never writes into
the repo:

```sh
python3 src/repo_context_packer.py examples/sample-repo README.md -o examples/sample-repo/pack.txt
```

```text
error: output must be outside the packed root: examples/sample-repo/pack.txt
```

## Examples

### 1. Pack two files for a bug report

```sh
python3 src/repo_context_packer.py examples/sample-repo src/app.py src/util.py -o /tmp/bug.txt
```

```text
packed 2 file(s), 16 lines into /tmp/bug.txt
```

`/tmp/bug.txt` now holds only those two files — paste it into the AI
chat with the bug report.

### 2. A secret file is refused even when named

```sh
python3 src/repo_context_packer.py examples/sample-repo .env README.md -o /tmp/pack2.txt
```

Real output:

```text
packed 1 file(s), 3 lines into /tmp/pack2.txt
skipped .env (secret file)
```

The pack holds only `README.md`. The `.env` contents are nowhere in
the output file.

### 3. Only Python files from a folder

```sh
python3 src/repo_context_packer.py examples/sample-repo src docs --include "*.py" --list
```

```text
src/app.py
src/util.py
```

## How it is tested

```sh
python3 tests/test_repo_context_packer.py
```

18 tests, standard library `unittest` only — no third-party packages.
They cover: named files in given order, folder packing in sorted
order, `.env` and private keys refused, build folders left out, binary
and hidden files left out, `--list`, `--include`, output inside the
root refused, output outside the root written, nothing packable (exit
1), and bad input (exit 2). The tests build a fake repo in a temporary
folder; they never touch a real repo.

The bundled example is a real run, not made-up output:

```sh
sh examples/run-example.sh
```

It packs `examples/sample-repo` and checks that the fake key in its
`.env` does not appear in the pack. The committed
`examples/sample-pack.txt` is the pack that run produces.

## Contributing

Small, focused improvements are welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

Built from scratch for this repo. The idea — packing code for an AI
assistant — follows the same pattern as Repomix and packdiff (named in
"How this differs from similar tools" above); no code was copied from
either.
