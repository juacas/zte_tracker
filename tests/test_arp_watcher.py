"""Tests for the ARP frame parser."""

from __future__ import annotations

import asyncio
import socket
import struct
from unittest.mock import Mock, patch

import pytest

from custom_components.zte_tracker.arp_watcher import async_start_arp, parse_arp


def _frame(
    sender_mac: bytes = bytes.fromhex("aabbccddee01"),
    sender_ip: bytes = bytes([192, 168, 1, 50]),
    ethertype: bytes = b"\x08\x06",
    hlen: int = 6,
) -> bytes:
    eth = b"\xff" * 6 + sender_mac + ethertype
    arp = struct.pack("!HHBBH", 1, 0x0800, hlen, 4, 1)
    return eth + arp + sender_mac + sender_ip + b"\x00" * 6 + bytes([192, 168, 1, 1])


def test_parses_sender_mac_and_ip() -> None:
    """The sender of the frame is the device that just joined."""
    assert parse_arp(_frame()) == ("aa:bb:cc:dd:ee:01", "192.168.1.50")


def test_probe_with_zero_sender_ip_still_yields_the_mac() -> None:
    """Static-IP devices announce themselves with an ARP probe from 0.0.0.0."""
    assert parse_arp(_frame(sender_ip=b"\x00" * 4)) == (
        "aa:bb:cc:dd:ee:01",
        "0.0.0.0",
    )


def test_rejects_malformed_or_foreign_frames() -> None:
    """Short frames, other ethertypes and null/broadcast senders are dropped."""
    assert parse_arp(b"\x00" * 10) is None
    assert parse_arp(_frame(ethertype=b"\x08\x00")) is None
    assert parse_arp(_frame(hlen=8)) is None
    assert parse_arp(_frame(sender_mac=b"\x00" * 6)) is None
    assert parse_arp(_frame(sender_mac=b"\xff" * 6)) is None


def test_a_raising_callback_does_not_stop_the_listener() -> None:
    """Every frame is handled even if one callback raises."""
    sock = Mock()
    sock.recv.side_effect = [_frame(), _frame(), BlockingIOError()]
    callback = Mock(side_effect=[RuntimeError("boom"), None])
    loop = Mock(spec=asyncio.AbstractEventLoop)
    with patch.object(socket, "socket", return_value=sock):
        async_start_arp(loop, callback)
    loop.add_reader.call_args.args[1]()
    assert callback.call_count == 2


def test_socket_is_closed_if_the_reader_cannot_be_registered() -> None:
    """A failing add_reader must not leak the raw socket."""
    sock = Mock()
    loop = Mock(spec=asyncio.AbstractEventLoop)
    loop.add_reader.side_effect = RuntimeError("no loop")
    with patch.object(socket, "socket", return_value=sock), pytest.raises(RuntimeError):
        async_start_arp(loop, Mock())
    sock.close.assert_called_once()


def test_one_wakeup_handles_a_bounded_number_of_frames() -> None:
    """A flood of frames cannot keep the event loop busy forever."""
    sock = Mock()
    sock.recv.return_value = _frame()
    callback = Mock()
    loop = Mock(spec=asyncio.AbstractEventLoop)
    with patch.object(socket, "socket", return_value=sock):
        async_start_arp(loop, callback)
    loop.add_reader.call_args.args[1]()
    assert callback.call_count == 100
