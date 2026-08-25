# Generation environment for hypothesis-batch P1. Source it, do not run it.
#
#   export OUTPUT_DIR=<run directory>
#   source <this file>
#
# Defaults live in ideation_config.json beside this file. A variable already
# exported in the shell always wins, so configure by `export`, never by editing.
#
# The interpreter is resolved, not configured. This file finds the conda env from
# the skill's Setup step by name — `mechanist-ideation`, built from
# requirements.txt beside this file — whether or not the calling shell has it
# active, so no absolute path belongs in the config. To point elsewhere:
# `export IDEATION_CONDA_ENV=<name>` for another env, or
# `export IDEATION_PYTHON=<path>` to bypass the search with one interpreter.
# The model name the gateway wants is `claude-opus-4-8` — `claude-opus-4.8` 404s.

_P1_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_P1_CFG="${IDEATION_CONFIG:-$_P1_DIR/ideation_config.json}"
_P1_BOOT="$(command -v python3 || command -v python)"

# Export every config key that the environment has not already set.
eval "$("$_P1_BOOT" - "$_P1_CFG" <<'PY'
import json, os, shlex, sys
for k, v in json.load(open(sys.argv[1])).items():
    if k.startswith("_") or os.environ.get(k):
        continue
    print(f"export {k}={shlex.quote(str(v))}")
PY
)"

# Where the packaged scripts and their vendored ai_scientist/ closure live.
SCRIPTS_DIR="${MECHANIST_SCRIPTS_DIR:-$_P1_DIR}"

export IDEATION_CONDA_ENV="${IDEATION_CONDA_ENV:-mechanist-ideation}"

# Root of the conda install this shell knows about, so an env can be located by
# name alone.
_p1_conda_base() {
    if [ -n "$CONDA_EXE" ] && [ -x "$CONDA_EXE" ]; then
        dirname "$(dirname "$CONDA_EXE")"
        return 0
    fi
    _p1_c="$(command -v conda 2>/dev/null)"
    case "$_p1_c" in
        /*) dirname "$(dirname "$_p1_c")"; return 0 ;;
    esac
    # An active env lives at <base>/envs/<name>; the base has no such parent.
    case "$CONDA_PREFIX" in
        */envs/*) echo "${CONDA_PREFIX%/envs/*}"; return 0 ;;
        ?*)       echo "$CONDA_PREFIX"; return 0 ;;
    esac
    return 1
}

# First hit wins: explicit override, the env already active, the env found by
# name under any conda install this shell can see, then plain `python`.
_p1_python() {
    if [ -n "$IDEATION_PYTHON" ]; then
        echo "$IDEATION_PYTHON"
        return 0
    fi
    if [ "$CONDA_DEFAULT_ENV" = "$IDEATION_CONDA_ENV" ] && [ -x "$CONDA_PREFIX/bin/python" ]; then
        echo "$CONDA_PREFIX/bin/python"
        return 0
    fi
    _p1_base="$(_p1_conda_base)" || _p1_base=""
    for _p1_cand in \
        ${_p1_base:+"$_p1_base/envs/$IDEATION_CONDA_ENV/bin/python"} \
        "$HOME/miniconda3/envs/$IDEATION_CONDA_ENV/bin/python" \
        "$HOME/anaconda3/envs/$IDEATION_CONDA_ENV/bin/python" \
        "$HOME/miniforge3/envs/$IDEATION_CONDA_ENV/bin/python" \
        "$HOME/mambaforge/envs/$IDEATION_CONDA_ENV/bin/python"
    do
        if [ -x "$_p1_cand" ]; then
            echo "$_p1_cand"
            return 0
        fi
    done
    command -v python 2>/dev/null || command -v python3 2>/dev/null
}

PY="$(_p1_python)"

# A missing dependency otherwise surfaces as a ModuleNotFoundError deep inside a
# pass, so name the interpreter that was picked and the way out.
if [ -z "$PY" ] || ! "$PY" - <<'PY' 2>/dev/null
import importlib.util as u, sys
need = ("openai", "anthropic", "backoff", "httpx", "requests", "tiktoken")
sys.exit(1 if [n for n in need if u.find_spec(n) is None] else 0)
PY
then
    echo "p1_env.sh: '${PY:-python}' cannot import the P1 dependencies." >&2
    echo "           Build the env once, then re-source this file:" >&2
    echo "             conda create -n $IDEATION_CONDA_ENV python=3.11 -y" >&2
    echo "             conda run -n $IDEATION_CONDA_ENV pip install -r '$SCRIPTS_DIR/requirements.txt'" >&2
    echo "           Or name an env / interpreter that already has them:" >&2
    echo "             export IDEATION_CONDA_ENV=<env name>" >&2
    echo "             export IDEATION_PYTHON=<path to python>" >&2
fi

# Derived from the above; not user-facing knobs.
export OPENAI_API_BASE="$OPENAI_BASE_URL"
export https_proxy="${https_proxy:-$http_proxy}"
export HTTP_PROXY="$http_proxy"
export HTTPS_PROXY="$https_proxy"
export NO_PROXY="$no_proxy"
export MECHANIC_DB_CACHE_DIR="${MECHANIC_DB_CACHE_DIR:-$OUTPUT_DIR/search_cache}"
export PYTHONUNBUFFERED=1

unset -f _p1_conda_base _p1_python
unset _P1_DIR _P1_CFG _P1_BOOT _p1_c _p1_base _p1_cand
