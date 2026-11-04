"""Shared loader for the optional project config `dev-pipeline.json`.

Every key is optional; a missing file means defaults. Unknown keys are reported
as warnings (usually a typo) and otherwise ignored. Standard library only.
"""
import copy
import json
import os

CONFIG_NAME = "dev-pipeline.json"

DEFAULTS = {
    "models": {"scout": "haiku", "implementor": "sonnet", "auditor": "haiku"},
    "commands": {"build": None, "test": None},
    "context_files": [],
    "protected_paths": [],
    "scope": {"ignore": [], "declaration_regex": None},
    "checks": {"timeout_seconds": 900, "failure_regex": None},
    "comments": {"max_lines": 1},
    "context": {
        "update_memory": True,
        "memory_file": ".dev-pipeline/project-memory.md",
        "max_memory_lines": 150,
        "refresh_command": None,
        "refresh_tool": None,
        "hint": None,
    },
    "questions": "ask",
    "require_brief_approval": True,
    "max_fix_rounds": 2,
}


def load(root):
    """Return (config, warnings). Never raises on a bad file."""
    cfg = copy.deepcopy(DEFAULTS)
    warnings = []
    path = os.path.join(root, CONFIG_NAME)
    if not os.path.isfile(path):
        return cfg, warnings
    try:
        with open(path, encoding="utf-8") as fh:
            user = json.load(fh)
        if not isinstance(user, dict):
            raise ValueError("top level must be an object")
    except (OSError, ValueError) as exc:
        return cfg, [f"{CONFIG_NAME} ignored ({exc}); using defaults"]
    for key, value in user.items():
        if key == "$schema":
            continue
        if key not in cfg:
            warnings.append(f"{CONFIG_NAME}: unknown key '{key}' ignored")
        elif isinstance(cfg[key], dict) and isinstance(value, dict):
            for sub, subval in value.items():
                if sub not in cfg[key]:
                    warnings.append(f"{CONFIG_NAME}: unknown key '{key}.{sub}' ignored")
                else:
                    cfg[key][sub] = subval
        else:
            cfg[key] = value
    if cfg["questions"] not in ("ask", "assume"):
        warnings.append("questions must be 'ask' or 'assume'; using 'ask'")
        cfg["questions"] = "ask"
    return cfg, warnings
