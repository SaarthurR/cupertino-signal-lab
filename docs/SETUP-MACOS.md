# Setup on a fresh Apple Silicon Mac (verified)

Tested on macOS with an M-series chip, starting with no Homebrew, no `gh` and only the system Python 3.9.
Everything below worked end to end: environment, world build, smoke test, unit tests and the demo launcher.

## 1. Prerequisites

| Need | How |
|---|---|
| Git | Run `git --version`. macOS offers to install the Xcode command line tools; accept. |
| uv (also fetches Python 3.12) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` then `export PATH="$HOME/.local/bin:$PATH"` |
| GitHub CLI (optional) | Download the `macOS_arm64.zip` from <https://github.com/cli/cli/releases>, copy `bin/gh` to `~/bin`, then `gh auth login` |

The system Python on macOS is 3.9, which is too old (`requires-python >= 3.12`). Do not use it. `uv venv --python 3.12` downloads the right one.

## 2. Install

```sh
git clone https://github.com/SaarthurR/cupertino-signal-lab.git && cd cupertino-signal-lab
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -r requirements.txt && uv pip install -e .
export PYTHONPATH=src
python -m tools.learner build-world --road wolfe
```

`build-world` prints nothing on success. Check that `worlds/wolfe/` exists afterwards.

## 3. Check it works

| Command | Expect |
|---|---|
| `python smoke_test.py` | Ends with `Fixed timer: average wait 6.9 s` and `AI (PPO): average wait 0.5 s`. Lines saying `Retrying in 1 seconds` are harmless. |
| `python -m unittest discover -s tests` | `OK` after about a minute. |
| `python3 -m tools.demo` | Prints local links for the slides, the engineer console, the video and the PDF. Ctrl-C stops it. |

## 4. Every new terminal

`PYTHONPATH` and the virtual environment do not persist between terminals:

```sh
cd cupertino-signal-lab && source .venv/bin/activate && export PYTHONPATH=src
```

## Common problems

- **`command not found: uv`**: run `export PATH="$HOME/.local/bin:$PATH"` or open a new terminal.
- **`ModuleNotFoundError`**: you forgot `export PYTHONPATH=src` or `source .venv/bin/activate`.
- **Step 3 (The proof) plays a recording instead of running live**: you skipped `build-world --road wolfe`.
