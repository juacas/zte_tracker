#!/usr/bin/env python3
"""Redact a ZTE Tracker debug log before attaching it to an issue.

Usage:
    python3 scripts/redact_log.py home-assistant.log > redacted.log
    python3 scripts/redact_log.py < home-assistant.log > redacted.log

Standard library only. Masks, in this order:
  * values of secret-looking keys: passwords, user names, session/login tokens,
    cookies, the ``Check`` header, authorization, host names, SSIDs
    (``key=value``, ``"key": "value"``, ``Key: value`` header lines and the
    ``addParameter("_sessionTOKEN", "123")`` form of the E2633 login page);
  * long hexadecimal strings (SHA-256 password hashes, ``Check`` values);
  * MAC addresses (``aa:bb:..`` or ``aa-bb-..``) -> ``<MAC-1>``, ``<MAC-2>`` ...;
  * IPv4 addresses (four numbers) -> ``<IP-1>``, ``<IP-2>`` ....
The same MAC or IP always gets the same placeholder, so the log stays readable.
Firmware versions such as ``V1.0.4`` are kept.

This is a best-effort filter, not a guarantee. READ the result before posting it:
device names, SSIDs, IPv6 addresses or anything unusual may still be in there.
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Callable, TextIO

_SECRET_KEYS = (
    r"password|passwd|pwd|username|user_name|_?sessiontoken|frm_logintoken|logintoken"
    r"|token|check|sid|session_?id|set-cookie|cookie|authorization|hostname|host_name|ssid"
)
_KEY_BOUNDARY = r"(?<![A-Za-z0-9])"

# key=value in a form body or query string: stops at & ; , whitespace or a quote.
_FORM = re.compile(rf"{_KEY_BOUNDARY}((?:{_SECRET_KEYS})=)[^&;,\s\"']*", re.IGNORECASE)
# "key": "value" / 'key': 'value' (JSON or Python dict repr), quoted value.
_QUOTED = re.compile(
    rf"({_KEY_BOUNDARY}([\"'])(?:{_SECRET_KEYS})\2\s*:\s*)([\"']).*?\3", re.IGNORECASE
)
# "key": 123 (unquoted value).
_UNQUOTED = re.compile(
    rf"({_KEY_BOUNDARY}([\"'])(?:{_SECRET_KEYS})\2\s*:\s*)(?![\"'])[^,}}\s]+", re.IGNORECASE
)
# Header lines: "Cookie: ...", "Set-Cookie: ...", "Authorization: ...", "Check: ..." to the end of the line.
_HEADER = re.compile(
    rf"({_KEY_BOUNDARY}(?:cookie|set-cookie|authorization|check)\s*:\s*)[^\r\n]*", re.IGNORECASE
)
# addParameter("_sessionTOKEN", "98765")
_ADD_PARAMETER = re.compile(
    r"(addParameter\(\s*\"(?:_sessiontoken|frm_logintoken)\"\s*,\s*\")[^\"]*(\")", re.IGNORECASE
)
_LONG_HEX = re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{32,}(?![0-9A-Fa-f])")
_MAC = re.compile(r"(?<![0-9A-Fa-f])(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}(?![0-9A-Fa-f])")
# Four numbers, not part of a longer dotted number (so V1.0.4 and 2026.1.0 are left alone).
_IPV4 = re.compile(r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d]|\.\d)")

_REDACTED = "<redacted>"


class Redactor:
    """Stateful so that the same MAC / IP keeps the same placeholder across lines."""

    def __init__(self) -> None:
        self._macs: dict[str, str] = {}
        self._ips: dict[str, str] = {}
        self.counts = {"secrets": 0, "hashes": 0, "macs": 0, "ips": 0}

    def _placeholder(self, table: dict[str, str], key: str, label: str, counter: str) -> str:
        if key not in table:
            table[key] = f"<{label}-{len(table) + 1}>"
            self.counts[counter] += 1
        return table[key]

    def _secret(self, text: str) -> str:
        def count(replacement: str) -> Callable:
            def handler(match: re.Match) -> str:
                self.counts["secrets"] += 1
                return match.expand(replacement)

            return handler

        text = _FORM.sub(count(rf"\1{_REDACTED}"), text)
        text = _QUOTED.sub(count(rf"\1\3{_REDACTED}\3"), text)
        text = _UNQUOTED.sub(count(rf"\1\"{_REDACTED}\""), text)
        text = _HEADER.sub(count(rf"\1{_REDACTED}"), text)
        text = _ADD_PARAMETER.sub(count(rf"\1{_REDACTED}\2"), text)
        return text

    def line(self, text: str) -> str:
        text = self._secret(text)

        def hash_(match: re.Match) -> str:
            self.counts["hashes"] += 1
            return "<hash>"

        text = _LONG_HEX.sub(hash_, text)
        text = _MAC.sub(
            lambda m: self._placeholder(self._macs, m.group(0).lower().replace("-", ":"), "MAC", "macs"), text
        )
        text = _IPV4.sub(lambda m: self._placeholder(self._ips, m.group(0), "IP", "ips"), text)
        return text


def redact(stream: TextIO, out: TextIO) -> Redactor:
    redactor = Redactor()
    for text in stream:
        out.write(redactor.line(text))
    return redactor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Redact a ZTE Tracker debug log (MAC, IP, passwords, tokens, cookies).")
    parser.add_argument("log", nargs="?", help="log file (default: standard input)")
    parser.add_argument("-o", "--output", help="write here instead of standard output")
    args = parser.parse_args(argv)

    source = open(args.log, encoding="utf-8", errors="replace") if args.log else sys.stdin
    target = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    try:
        redactor = redact(source, target)
    finally:
        if args.log:
            source.close()
        if args.output:
            target.close()
    counts = redactor.counts
    print(
        f"redacted: {counts['secrets']} secret values, {counts['hashes']} hashes, "
        f"{counts['macs']} distinct MACs, {counts['ips']} distinct IPs. "
        "Read the result before posting it.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
