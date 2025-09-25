from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

# Optional dependencies (detected at runtime)
try:  # RapidFuzz for fast fuzzy scores
    from rapidfuzz import fuzz as _rf_fuzz
    HAVE_RAPIDFUZZ = True
except Exception:
    HAVE_RAPIDFUZZ = False

try:  # PyYAML for robust frontmatter parsing
    import yaml as _yaml
    HAVE_PYYAML = True
except Exception:
    HAVE_PYYAML = False


def now_timestamp_str() -> str:
    # naive local time "YYYY-MM-DD HH:mm"
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def ensure_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def atomic_write_text(path: Path, text: str, make_backup: bool = True) -> None:
    ensure_dir(path)
    if make_backup and path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup)
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
        tmp.write(text)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def run_in_thread(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return loop.run_in_executor(None, lambda: func(*args, **kwargs))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    atomic_write_text(path, text, make_backup=True)


def which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


def has_ripgrep() -> bool:
    exe = which("rg")
    if not exe:
        return False
    try:
        subprocess.run([exe, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False


def run_ripgrep(root: Path, pattern: str, flags: Iterable[str]) -> Tuple[int, str, str]:
    """Returncode, stdout, stderr."""
    cmd = ["rg", *flags, "--line-number", "--with-filename", pattern, str(root)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def fuzzy_score(a: str, b: str) -> float:
    a = a or ""
    b = b or ""
    if HAVE_RAPIDFUZZ:
        return float(_rf_fuzz.QRatio(a, b))
    # stdlib fallback
    import difflib
    return 100.0 * difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


# Very small YAML fallback: only handles "key: value", "list:" followed by "- item"
def mini_yaml_load(text: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    lines = [ln.rstrip("\n") for ln in text.splitlines()]
    key = None
    for ln in lines:
        if not ln.strip():
            continue
        if ln.lstrip().startswith("-") and key:
            data.setdefault(key, [])
            data[key].append(ln.lstrip()[1:].strip())
        elif ":" in ln:
            k, v = ln.split(":", 1)
            key = k.strip()
            v = v.strip()
            if v == "":
                data[key] = []
            else:
                # coerce simple ints
                if re.fullmatch(r"-?\d+", v):
                    data[key] = int(v)
                else:
                    data[key] = v
        else:
            # ignore malformed
            pass
    return data


def yaml_load(text: str) -> Dict[str, Any]:
    if HAVE_PYYAML:
        try:
            val = _yaml.safe_load(text) or {}
            if not isinstance(val, dict):
                return {}
            return val
        except Exception:
            return {}
    return mini_yaml_load(text)