"""Load integration modules without Home Assistant installed.

Every suite here targets code that does not need Home Assistant at runtime, so
each one loaded its target by path with its own copy of this. One copy.
"""

import importlib.util
import sys
import types
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DIR = _REPO_ROOT / "custom_components" / "zte_tracker"


def install_homeassistant():
    """Enough of Home Assistant for a module that imports it to load."""
    if "homeassistant" in sys.modules:
        return

    def async_redact_data(data, to_redact):
        return {
            key: ("**REDACTED**" if key in to_redact else value)
            for key, value in data.items()
        }

    made = {}
    for name, attrs in (
        ("homeassistant", {}),
        ("homeassistant.components", {}),
        (
            "homeassistant.components.diagnostics",
            {"async_redact_data": async_redact_data},
        ),
        ("homeassistant.config_entries", {"ConfigEntry": object}),
        (
            "homeassistant.const",
            {
                "CONF_HOST": "host",
                "CONF_PASSWORD": "password",
                "CONF_USERNAME": "username",
            },
        ),
        ("homeassistant.core", {"HomeAssistant": object}),
    ):
        module = types.ModuleType(name)
        module.__path__ = []
        for key, value in attrs.items():
            setattr(module, key, value)
        made[name] = module
    sys.modules.update(made)


def load(package: str, *names: str, const: dict | None = None):
    """Load the named modules as a throwaway package, and return the last."""
    if package not in sys.modules:
        stub = types.ModuleType(package)
        stub.__path__ = []
        sys.modules[package] = stub
        if const is not None:
            module = types.ModuleType(f"{package}.const")
            for key, value in const.items():
                setattr(module, key, value)
            sys.modules[f"{package}.const"] = module

    for name in names:
        key = f"{package}.{name}"
        if key in sys.modules:
            continue
        path = _DIR / f"{name}.py"
        spec = importlib.util.spec_from_file_location(key, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[key] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            # A module that failed to execute must not stay registered: the
            # next caller would get a half-built one and a misleading
            # AttributeError instead of the real cause.
            sys.modules.pop(key, None)
            raise

    return sys.modules[f"{package}.{names[-1]}"]
