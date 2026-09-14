"""Describe a router response by its structure, never by its content."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from typing import Any

# A name worth printing: a single identifier token, short, with no long digit run.
_SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,48}$")
_LONG_DIGITS = re.compile(r"\d{5,}")
_BARE_MAC = re.compile(r"^[0-9A-Fa-f]{12}$")
_SERIAL_LIKE = re.compile(r"^(?=.*\d)[A-Z0-9]{8,}$")

_SHAPES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("int", re.compile(r"^-?\d{1,18}$")),
    ("float", re.compile(r"^-?\d+\.\d+$")),
    ("mac", re.compile(r"^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")),
    ("ipv4", re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")),
    ("ipv6", re.compile(r"^[0-9A-Fa-f:]{6,45}$")),
    ("hex", re.compile(r"^[0-9A-Fa-f]{6,}$")),
    ("bool", re.compile(r"^(?:true|false|yes|no|on|off)$", re.IGNORECASE)),
    ("date", re.compile(r"^\d{4}-\d{2}-\d{2}")),
    ("uri", re.compile(r"^[a-z]{2,10}://")),
)

MAX_FIELDS_PER_NODE = 60
MAX_NODES = 40
MAX_KEYS = 80


def instance_count(structure: dict[str, Any]) -> int:
    """How many records a described response contained."""
    if structure.get("format") == "xml":
        return sum(
            node.get("instances", 0)
            for node in (structure.get("nodes") or {}).values()
            if isinstance(node, dict)
        )

    def walk(node: Any) -> int:
        if isinstance(node, dict):
            if "list" in node and isinstance(node["list"], int):
                return node["list"] + walk(node.get("of"))
            # A map of like shaped records is a record count too.
            if "map" in node and isinstance(node["map"], int):
                return node["map"] + walk(node.get("of"))
            return sum(walk(value) for value in node.values())
        return 0

    return walk(structure.get("keys"))


def node_names(structure: dict[str, Any]) -> list[str]:
    """The node or top level key names a response contained."""
    if structure.get("format") == "xml":
        return sorted(structure.get("nodes") or {})
    keys = structure.get("keys")
    if not isinstance(keys, dict):
        return []
    # map and of are this module's own wrapper for a collapsed record map, not
    # names the firmware sent, and reporting them as unparsed nodes is noise on
    return sorted(k for k in keys if k not in ("map", "of"))


def safe_name(name: str) -> str:
    """Return the name if it is safe to print, else a description of it."""
    if (
        _SAFE_NAME.match(name)
        and not _LONG_DIGITS.search(name)
        and not _BARE_MAC.match(name)
        and not _SERIAL_LIKE.match(name)
    ):
        return name
    return f"<name len={len(name)} digits={bool(_LONG_DIGITS.search(name))}>"


def shape_of(value: Any) -> str:
    """Classify a value without reproducing any part of it."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    text = str(value)
    if not text:
        return "empty"
    if not text.strip():
        return "blank"
    for name, pattern in _SHAPES:
        if pattern.match(text.strip()):
            return name
    return "text"


# Fields whose VALUE a maintainer cannot work without.
ENUM_FIELDS = frozenset(
    {
        "connstatus",
        "linkstatus",
        "wancname",
        "accesstype",
        "networktype",
        "ipmode",
        "linkmode",
        "workmode",
        "wanmode",
        "conntype",
        "if_errorstr",
        "if_errortype",
        "if_errorid",
        "active",
        "enable",
    }
)
# (node, field) pairs too generic to allowlist globally (e.g. "Status" can carry an SSID elsewhere), but safe on this specific node.
NODE_SCOPED_ENUM_FIELDS = frozenset(
    {
        ("obj_dslinterface_id", "status"),  # H2640 DSL line sync (#75)
    }
)
_ENUM_VALUE = re.compile(r"^[A-Za-z0-9_.:+-]{1,16}$")


def _field(name: str, value: Any, node: str = "") -> dict[str, Any]:
    """Describe one field. Exact length is itself a small disclosure for a
    secret, so those are bucketed rather than measured."""
    text = str(value or "")
    # The enum list wins over the name gate: WANCName contains "name", and its
    # value is the one thing that says which instance is the internet WAN.
    if (
        name.casefold() in ENUM_FIELDS
        or (
            node.casefold(),
            name.casefold(),
        )
        in NODE_SCOPED_ENUM_FIELDS
    ):
        described: dict[str, Any] = {"shape": shape_of(value), "len": len(text)}
        if _ENUM_VALUE.match(text):
            described["value"] = text
        return described
    if is_sensitive_name(name):
        return {"shape": shape_of(value), "len": f"<{8 if len(text) < 8 else 64}"}
    return {"shape": shape_of(value), "len": len(text)}


def _describe_xml(root: ET.Element) -> dict[str, Any]:
    """Report each node once, with the fields its instances contain."""
    nodes: dict[str, Any] = {}

    for node in list(root):
        tag = node.tag.rpartition("}")[2]
        node_tag = tag
        # The IF_ERROR* envelope is a fixed firmware enumeration, and it is the
        # difference between "this endpoint returned no devices" and "the
        if tag.startswith("IF_"):
            envelope = nodes.setdefault("<envelope>", {"instances": 0, "fields": {}})
            envelope["fields"].setdefault(safe_name(tag), _field(tag, node.text))
            continue
        key = safe_name(tag)
        entry = nodes.setdefault(key, {"instances": 0, "fields": {}})
        explicit = node.findall("Instance")
        # Only <Instance> is a record.
        entry["instances"] += len(explicit)
        instances = explicit or (
            [node] if len(node) or (node.text or "").strip() else []
        )

        for instance in instances:
            name = None
            for child in instance:
                tag = child.tag.rpartition("}")[2]
                if len(entry["fields"]) >= MAX_FIELDS_PER_NODE:
                    # Checked per field, not per instance: a single Instance
                    # with five thousand children used to add all of them.
                    entry["fields_truncated"] = True
                    break
                if tag == "ParaName":
                    name = (child.text or "").strip()
                elif tag == "ParaValue" and name is not None:
                    entry["fields"].setdefault(
                        safe_name(name), _field(name, child.text, node_tag)
                    )
                    name = None
                elif tag not in ("ParaName", "ParaValue"):
                    entry["fields"].setdefault(
                        safe_name(tag), _field(tag, child.text, node_tag)
                    )
            if instance is node and node.text and node.text.strip():
                entry["fields"].setdefault(
                    "#text", _field(node.tag.rpartition("}")[2], node.text, node_tag)
                )

        if len(nodes) >= MAX_NODES:
            nodes["<truncated>"] = {"instances": 0, "fields": {}}
            break

    return {"format": "xml", "root": safe_name(root.tag), "nodes": nodes}


def _describe_json(data: Any, depth: int = 0) -> Any:
    """Replace every value with its shape, and check every key."""
    if depth > 6:
        return "<deep>"
    if isinstance(data, dict):
        # A dictionary whose record shaped entries all describe identically is
        # a map of records, which means its keys are data rather than schema.
        records = {k: v for k, v in data.items() if isinstance(v, dict)}
        # Two or more, not one.
        if len(records) > 1:
            described = [_describe_json(v, depth + 1) for v in records.values()]
            fields = [set(d) if isinstance(d, dict) else set() for d in described]
            union = set().union(*fields) if fields else set()
            # Collapse on similar key sets, from one record upward.
            if union and all(len(f) * 2 >= len(union) for f in fields):
                merged: dict[str, Any] = {}
                for d in described:
                    if isinstance(d, dict):
                        merged.update(d)
                # A collapsed map describes many records with one shape, so an
                # enum value lifted from the first record would be presented as
                for field, described_field in list(merged.items()):
                    if isinstance(described_field, dict) and "value" in described_field:
                        merged[field] = {
                            k: v for k, v in described_field.items() if k != "value"
                        }
                collapsed: dict[str, Any] = {"map": len(records), "of": merged}
                for key, value in data.items():
                    if key not in records:
                        collapsed[safe_name(str(key))] = _describe_json(
                            value, depth + 1
                        )
                return collapsed
        out: dict[str, Any] = {}
        for index, (key, value) in enumerate(data.items()):
            if index >= MAX_KEYS:
                out["<truncated>"] = len(data) - MAX_KEYS
                break
            name = safe_name(str(key))
            if name.startswith("<") and name in out:
                name = f"{name[:-1]} #{len(out)}>"
            if (
                not isinstance(value, (dict, list))
                and str(key).casefold() in ENUM_FIELDS
            ):
                # The vue dialect carries the same dispatch literals in JSON.
                out[name] = _field(str(key), value)
            else:
                out[name] = _describe_json(value, depth + 1)
        return out
    if isinstance(data, list):
        if not data:
            return {"list": 0}
        return {"list": len(data), "of": _describe_json(data[0], depth + 1)}
    return shape_of(data)


# What a page is, judged by structure rather than by its words.
_PASSWORD_INPUT = re.compile(r"<input[^>]*type\s*=\s*['\"]password", re.IGNORECASE)
_FORM = re.compile(r"<form\b", re.IGNORECASE)
_INPUT = re.compile(r"<input\b", re.IGNORECASE)
_SCRIPT = re.compile(r"<script\b", re.IGNORECASE)
_TABLE_ROW = re.compile(r"<tr\b", re.IGNORECASE)
_FRAME = re.compile(r"<(?:i?frame)\b", re.IGNORECASE)
_REFRESH = re.compile(r"http-equiv\s*=\s*['\"]refresh", re.IGNORECASE)


def _classify_page(text: str) -> str:
    """One word for what this page is, for a reader who cannot see its text."""
    if _PASSWORD_INPUT.search(text):
        return "login_form"
    if _REFRESH.search(text):
        return "redirect_or_refresh"
    if _FRAME.search(text):
        return "frameset"
    if _FORM.search(text) and _INPUT.search(text):
        return "form"
    if _TABLE_ROW.search(text):
        return "data_table"
    if len(text) < 512:
        return "stub"
    return "page"


def _describe_html(text: str) -> dict[str, Any]:
    """Describe a rendered page without reproducing any of it."""
    return {
        "format": "html",
        "kind": _classify_page(text),
        "length": len(text),
        "forms": len(_FORM.findall(text)),
        "inputs": len(_INPUT.findall(text)),
        "password_inputs": len(_PASSWORD_INPUT.findall(text)),
        "scripts": len(_SCRIPT.findall(text)),
        "table_rows": len(_TABLE_ROW.findall(text)),
    }


def describe(text: str, content_type: str = "") -> dict[str, Any]:
    """Describe a response body. Never returns any value from it."""
    if not text:
        return {"format": "empty"}

    stripped = text.lstrip("\ufeff\u200b \t\r\n\x00")
    if stripped[:1] in "{[":
        try:
            return {"format": "json", "keys": _describe_json(json.loads(stripped))}
        except (ValueError, RecursionError):
            pass

    # A real page announces itself, and is never parsed as data.
    if stripped[:15].lower().startswith(("<!doctype", "<html")):
        return _describe_html(text)

    if stripped[:1] == "<":
        try:
            root = ET.fromstring(stripped)
        except ET.ParseError:
            root = None
        if root is not None:
            # Two failures to avoid at once.
            if root.tag.rpartition("}")[2].lower() in ("html", "body", "head"):
                return _describe_html(text)
            return _describe_xml(root)

    if "html" in content_type.lower():
        return _describe_html(text)

    return {"format": "unrecognised", "length": len(text)}


# Diagnostics uses this to decide whether a key it does not recognise should be reported at all.
_SENSITIVE = (
    "password",
    "passwd",
    "passphrase",
    "pwd",
    "psk",
    "secret",
    "token",
    "cookie",
    "session",
    "credential",
    "key",
    "auth",
    "serial",
    "ssid",
    "mac",
    "hostname",
    "host",
    "phone",
    "msisdn",
    "iccid",
    "imei",
    "imsi",
    "account",
    "subscriber",
    "user",
    "loid",
    "alias",
    "sip",
    "voip",
    # Free prose written by the firmware.
    "error_message",
    "errormsg",
    "errorstr",
    "statusmsg",
    "name",
)

# Names that end in Name but describe the hardware, not a person.
_NAME_EXEMPT = frozenset(
    {"modelname", "manufacturername", "productname", "classname", "vendorname"}
)

# Short markers are matched as whole words, not as substrings.
_SENSITIVE_WORDS = frozenset({"pin", "sn", "onu", "wps", "id"})
_WORDS = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+")


def is_sensitive_name(name: str) -> bool:
    """Whether a field name suggests it holds something personal."""
    lowered = name.casefold()
    if lowered in _NAME_EXEMPT:
        return False
    if any(marker in lowered for marker in _SENSITIVE):
        return True
    return bool(_SENSITIVE_WORDS & {word.casefold() for word in _WORDS.findall(name)})
