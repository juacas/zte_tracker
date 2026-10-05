"""Minimal ARP listener used to notice devices that join the network.

Every device, with a static or a DHCP address, announces itself with ARP (a
probe or a gratuitous ARP) when it connects. A Linux packet socket bound to the
ARP ethertype only receives ARP frames, so no capture filter or extra package
is needed. It needs CAP_NET_RAW, which Home Assistant OS has and a container
gets with host networking.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
import socket
import struct

_LOGGER = logging.getLogger(__name__)

ETH_P_ARP = 0x0806
ETH_P_IP = 0x0800
_ETH_HEADER = 14
_ARP_LENGTH = 28
# Bound the work done per wakeup so a flood cannot starve the event loop.
_MAX_FRAMES = 100


def parse_arp(frame: bytes) -> tuple[str, str] | None:
    """Return (sender mac, sender ip) for an IPv4 over Ethernet ARP frame."""
    if len(frame) < _ETH_HEADER + _ARP_LENGTH:
        return None
    if frame[12:14] != ETH_P_ARP.to_bytes(2, "big"):
        return None
    htype, ptype, hlen, plen, _op = struct.unpack(
        "!HHBBH", frame[_ETH_HEADER : _ETH_HEADER + 8]
    )
    if htype != 1 or ptype != ETH_P_IP or hlen != 6 or plen != 4:
        return None
    sender_mac = frame[_ETH_HEADER + 8 : _ETH_HEADER + 14]
    if sender_mac in (b"\x00" * 6, b"\xff" * 6):
        return None
    sender_ip = socket.inet_ntoa(frame[_ETH_HEADER + 14 : _ETH_HEADER + 18])
    return ":".join(f"{b:02x}" for b in sender_mac), sender_ip


def async_start_arp(
    loop: asyncio.AbstractEventLoop, callback: Callable[[str, str], None]
) -> Callable[[], None]:
    """Call callback(mac, ip) for every ARP frame; return a stop function.

    Raises when raw sockets are unavailable (no permission, or not Linux).
    """
    if not hasattr(socket, "AF_PACKET"):
        raise OSError("packet sockets are not available on this platform")
    sock = socket.socket(
        socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ARP)  # type: ignore[attr-defined]
    )
    sock.setblocking(False)

    def _on_readable() -> None:
        for _ in range(_MAX_FRAMES):
            try:
                frame = sock.recv(256)
            except (BlockingIOError, InterruptedError):
                return
            except OSError as ex:
                _LOGGER.error("ARP listener stopped: %s", ex)
                loop.remove_reader(sock.fileno())
                return
            if (parsed := parse_arp(frame)) is not None:
                try:
                    callback(*parsed)
                except Exception:  # noqa: BLE001 - one bad frame must not stop us
                    _LOGGER.exception("ARP callback failed")

    try:
        loop.add_reader(sock.fileno(), _on_readable)
    except Exception:
        sock.close()
        raise

    def _stop() -> None:
        loop.remove_reader(sock.fileno())
        sock.close()

    return _stop
