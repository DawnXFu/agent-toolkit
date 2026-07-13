#!/usr/bin/env python3
"""Public facade for the unified handoff implementation.

The implementation is split at Python top-level syntax boundaries so repository
connectors with conservative per-file limits can transport it safely. All parts
execute in this module namespace; public imports remain unchanged.
"""
from pathlib import Path as _LoaderPath

_PARTS_DIR = _LoaderPath(__file__).with_name("handoff_lib_parts")
for _part in sorted(_PARTS_DIR.glob("part_*.py")):
    exec(compile(_part.read_text(encoding="utf-8"), str(_part), "exec"), globals(), globals())
del _part, _PARTS_DIR, _LoaderPath
