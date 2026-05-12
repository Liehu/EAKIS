"""Centralized configuration file paths.

All user-customizable configuration files should be referenced through this module
to ensure consistency across the codebase.
"""
from __future__ import annotations

from pathlib import Path

# Project root directory (assumes this file is at src/core/config_paths.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Base config directory
CONFIG_DIR = PROJECT_ROOT / "config"

# User-customizable configuration paths
DOMAIN_DICTS_DIR = CONFIG_DIR / "domain_dicts"
ENGINES_DIR = CONFIG_DIR / "engines"
PROMPTS_DIR = CONFIG_DIR / "prompts"

# Specific files
ENGINES_YAML = ENGINES_DIR / "engines.yaml"
DATASOURCES_YAML = CONFIG_DIR / "datasources.yaml"


def get_domain_dict_path(filename: str) -> Path:
    """Get path to a domain dictionary file."""
    return DOMAIN_DICTS_DIR / filename


def get_prompt_path(filename: str) -> Path:
    """Get path to a prompt file."""
    return PROMPTS_DIR / filename


def list_domain_dicts() -> list[str]:
    """List all available domain dictionary files."""
    if not DOMAIN_DICTS_DIR.exists():
        return []
    return [f.name for f in DOMAIN_DICTS_DIR.iterdir() if f.is_file() and f.suffix == ".txt"]


def list_prompts() -> list[str]:
    """List all available prompt files."""
    if not PROMPTS_DIR.exists():
        return []
    return [f.name for f in PROMPTS_DIR.iterdir() if f.is_file() and f.suffix == ".yaml"]

def get_engine_specs() -> dict:
    """Get engine specifications from engines.yaml."""
    import yaml

    if not ENGINES_YAML.exists():
        return {}

    with open(ENGINES_YAML, "r", encoding="utf-8") as f:
        return yaml.safe_load(f).get("engines", {})
