"""Probe every known endpoint profile and describe what came back."""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from typing import Any

from .support_shape import describe, instance_count, node_names, safe_name

_LOGGER = logging.getLogger(__name__)

# Where exports land. A subdirectory keeps them out of the configuration root
# and lets the directory itself be 0700. Named here rather than in __init__ so
# diagnostics can reference it without importing the integration package.
BUNDLE_DIRNAME = "zte_tracker_support"

# Per-probe timeout, held against the coordinator's client lock.
PROBE_TIMEOUT = 8

# Ceiling for the whole walk, enforced here rather than by the caller: an
# asyncio.wait_for around the executor job cannot cancel the thread, so it
WALK_DEADLINE = 120

FIXED_PROBES: dict[str, tuple[str, str]] = {
    "device_info": ("menuData", "devmgr_statusmgr_lua.lua"),
    "device_info_view": ("menuView", "statusMgr&Menu3Location=0"),
    "topology": ("menuData", "topo_lua.lua"),
    "lan_view": ("menuView", "localNetStatus"),
}

# Node names the parsers already understand.
KNOWN_NODES = frozenset(
    {
        "OBJ_WLAN_AD_ID",  # F6640 wlan_id_element
        "OBJ_ACCESSDEV_ID",  # F6640/H288A/H388X lan, H288A/H388X wlan
        "OBJ_CLIENTS_ID",  # E2631 wlan_id_element
        "OBJ_LAN_INFO_ID",  # E2631 lan_id_element
        "OBJ_DEVINFO_ID",  # get_router_details
        "OBJ_CPUMEMUSAGE_ID",  # get_router_details
        "OBJ_POWERONTIME_ID",  # get_router_details
        "OBJ_WLANAP_ID",  # parse_devices, ESSID mapping
        "ID_WAN_COMFIG",  # get_wan_status
        "OBJ_PON_OPTICALPARA_ID",  # get_pon_optical_info
        "OBJ_LOS_INFO_ID",  # get_pon_optical_info
        "OBJ_GPONREGSTATUS_ID",  # get_pon_optical_info
    }
)


def _configured_profile_name(client: Any) -> str | None:
    try:
        paths = dict(getattr(client, "paths", {}) or {})
        for name, profile in (client.get_profiles() or {}).items():
            if dict(profile) == paths:
                return name
    except Exception:  # noqa: BLE001 - a summary field is never worth raising
        _LOGGER.debug("Support bundle: could not resolve the configured profile")
    return None


def _analyse(bundle: dict[str, Any]) -> dict[str, Any]:
    per_probe: dict[str, dict[str, Any]] = {}
    all_nodes: set[str] = set()

    for name, entry in bundle.get("probes", {}).items():
        structure = entry.get("structure") or {}
        # The envelope is reported inside each probe, not as firmware nobody
        # parses, and it appears on every response from every model.
        nodes = [
            n
            for n in node_names(structure)
            if not n.startswith("IF_") and n != "<envelope>"
        ]
        all_nodes.update(nodes)
        per_probe[name] = {
            "status": entry.get("status", entry.get("error")),
            "instances": instance_count(structure),
            "nodes": nodes,
            "source": entry.get("source", "profile"),
            "format": structure.get("format"),
        }

    # A profile is judged by what its own lan and wlan probes returned. The
    # owners map exists because the matrix deduplicates: a shared endpoint is
    owners: dict[str, list[str]] = bundle.get("_probe_owners", {})
    scores: dict[str, int] = {name: 0 for names in owners.values() for name in names}
    for name, summary in per_probe.items():
        # Discovered and swept probes are named after a firmware tag, not a profile.
        if summary["source"] != "profile":
            continue
        if summary["status"] != 200:
            continue
        for owner in owners.get(name, ()):
            scores[owner] = scores.get(owner, 0) + summary["instances"]

    # An endpoint that answers 200 with zero instances is the failure mode in
    # upstream issue #40: the router connects, the URL exists, and no device
    answered = {name: score for name, score in scores.items() if score > 0}
    # Some profiles are indistinguishable by endpoint alone. F8748 is F6640
    # plus one parsing flag and shares every endpoint with it, so the two
    top = max(answered.values()) if answered else 0
    tied = sorted(name for name, score in answered.items() if score == top)
    best = tied[0] if tied else None
    configured = bundle.get("configured_model")
    # Falls back to the model name only when the profile could not be
    # resolved, which keeps the old behaviour rather than reporting nothing.
    resolved = bundle.get("_configured_profile_name") or str(configured)

    return {
        "best_matching_profile": best,
        "tied_profiles": tied if len(tied) > 1 else [],
        "profile_scores": scores,
        "configured_model": configured,
        "configured_profile_answered": bool(scores.get(resolved, 0)),
        "configured_profile_name": bundle.get("_configured_profile_name"),
        "nodes_seen": sorted(all_nodes),
        "nodes_not_understood": sorted(all_nodes - KNOWN_NODES),
        # HTML view pages are rendered menus, not data endpoints, so they can never carry a record.
        "endpoints_answered_empty": sorted(
            name
            for name, summary in per_probe.items()
            if summary["status"] == 200
            and summary["instances"] == 0
            and summary["format"] not in ("html", "empty", "unrecognised")
        ),
        "probes": per_probe,
    }


# Endpoint names the router itself advertises in its pages. Guessing only ever
# finds what we already know; a firmware family nobody here has seen answers
# on its own terms. Menu pages (menuView) are named as plain words, e.g.
# "statusMgr" or "ethWanStatus", with no _lua suffix at all: matching only the
# _lua-suffixed form (the old pattern) meant the whole left-nav menu tree was
# invisible to discovery, only its data endpoints were ever found.
_ADVERTISED_TAG = re.compile(r"_tag=([A-Za-z0-9_.]+)")

# One page mentioning five thousand tags would otherwise be repeated, in full,
# inside every probe entry. Measured at 3.7 MB for a single 200 KB response.
MAX_ADVERTISED_PER_PROBE = 40
MAX_ADVERTISED_TOTAL = 100
MAX_ADVERTISED_LISTED_UNPROBED = 40

# Requested before authentication, so a firmware whose LOGIN is the thing that
# breaks still produces evidence.
PREAUTH_PROBES: dict[str, str] = {
    "login_page": "",
    "login_session_token": "?_type=loginData&_tag=login_token",
    "login_entry_form": "?_type=loginData&_tag=login_entry",
}


# Reading is bounded by bytes as well as by time, but the byte bound is the
# looser of the two: reading one byte at a time measures around 60 KB/s, so the
MAX_BODY_BYTES = 2_000_000

# How long one response may spend arriving, in total.
BODY_READ_BUDGET = 15


def _read_body(response: Any, budget: float) -> tuple[str, bool]:
    iter_content = getattr(response, "iter_content", None)
    if iter_content is None:
        # A response object that cannot stream, which in practice means a test
        # double. The size bound still applies.
        return (response.text or "")[:MAX_BODY_BYTES], False

    stop = time.monotonic() + budget
    chunks: list[bytes] = []
    size = 0
    truncated = False
    # One byte at a time, deliberately. requests fills a chunk before yielding,
    # and every socket read resets its own timeout, so with a larger chunk the
    # budget below is only checked once per chunk and a trickling router runs
    # unbounded.
    for chunk in iter_content(chunk_size=1):
        if not chunk:
            continue
        chunks.append(chunk)
        size += len(chunk)
        if size >= MAX_BODY_BYTES or time.monotonic() > stop:
            truncated = True
            break

    raw = b"".join(chunks)
    encoding = getattr(response, "encoding", None)
    if not encoding:
        # requests falls back to charset detection here rather than assuming
        # UTF-8. Assuming UTF-8 turned a UTF-16 body into NUL-interleaved text.
        encoding = getattr(response, "apparent_encoding", None) or "utf-8"
    try:
        return raw.decode(encoding, errors="replace"), truncated
    except LookupError:
        # The charset label comes from the router and is not validated by
        # requests. An unknown one must not cost the whole body: losing it
        return raw.decode("utf-8", errors="replace"), truncated


def _fetch(client: Any, url: str) -> dict[str, Any]:
    """One captured request. Never raises: a failure is data too."""
    entry: dict[str, Any] = {}
    response = None
    try:
        response = client.session.get(
            url, verify=client.verify_ssl, timeout=PROBE_TIMEOUT, stream=True
        )
        entry["status"] = response.status_code
        # Defensive on purpose: a response object without headers is our bug,
        # not the router's, and letting it fall into the except below would
        entry["content_type"] = (getattr(response, "headers", None) or {}).get(
            "Content-Type", ""
        )
        text, read_truncated = _read_body(response, BODY_READ_BUDGET)
        if read_truncated:
            entry["read_truncated"] = True
        entry["length"] = len(text)
        # Endpoint names the router advertises.
        entry["advertised"] = sorted(
            {
                tag
                for tag in _ADVERTISED_TAG.findall(text)
                if safe_name(tag.replace(".", "_"))[0] != "<"
            }
        )[:MAX_ADVERTISED_PER_PROBE]
        # The whole point of this module. A value never leaves the router: what
        # is recorded is which nodes exist, which fields they hold, how many
        entry["structure"] = describe(text, entry["content_type"])
    except (OSError, ValueError, LookupError) as err:
        # A probe failing is data too: it is how an unsupported endpoint
        # announces itself. Only the exception class is recorded: a requests
        # exception stringifies to the full URL, which carries the host, and
        # this file is destined for a public issue.
        entry["error"] = type(err).__name__
        _LOGGER.debug("Support bundle: probe failed (%s)", type(err).__name__)
    except Exception as err:  # noqa: BLE001 - unexpected, and worth shouting about
        # Still recorded rather than raised, because one broken probe must not
        # lose the whole export, but logged at exception level and flagged in
        entry["error"] = type(err).__name__
        entry["unexpected"] = True
        _LOGGER.exception("Support bundle: unexpected error probing an endpoint")
    finally:
        # Streaming holds the connection open until the body is consumed or the response is closed.
        if response is not None:
            try:
                response.close()
            except Exception:  # noqa: BLE001 - best effort cleanup
                _LOGGER.debug("Support bundle: closing a probe response failed")
    return entry


# A firmware nobody here has seen answers none of the known profiles, and no
# amount of guessing fixes that. The cap exists because a router that mentions
# every menu page on every response could otherwise queue an unbounded crawl.
MAX_DISCOVERED_PROBES = 40


def _base_tag(tag: str) -> str:
    return tag.split("&", 1)[0]


_LUA_TAG = re.compile(r"(?:_lua\.lua|_lua|\.lua)$")


def _discovered_request_type(tag: str) -> str:
    """menuData for data endpoints, menuView for the plain-word menu pages.

    Every _lua-suffixed tag seen so far is a menuData endpoint; every plain
    word (statusMgr, localNetStatus, ethWanStatus...) is a menuView page. A
    tag guessed the wrong way still returns something (an error page, most
    likely), which is why this is a heuristic and not asserted anywhere.
    """
    return "menuData" if _LUA_TAG.search(tag) else "menuView"


def _known_tags(profiles: dict[str, dict[str, Any]]) -> set[str]:
    """Every endpoint the matrix already requests, compared without suffixes."""
    return {_base_tag(tag) for _, tag in _probe_matrix(profiles).values()}


# Discovery must never GET one of these: unlike a data page, requesting them
# is itself the action. login_entry/login_token mint or consume a session,
# logout_entry ends the diagnostic's own session mid-walk, modeswitch_entry
# and switchlang_entry change router-wide settings. All four were only found
# because the wider tag regex above now also catches plain-word menu tags.
_UNSAFE_TAG = re.compile(r"(?:^|_)(login|logout|modeswitch|switchlang)(?:_|$)", re.I)


def _is_probeable(tag: str) -> bool:
    return not _UNSAFE_TAG.search(_base_tag(tag))


def _discover(
    client: Any,
    bundle: dict[str, Any],
    deadline: float,
) -> None:
    """Walk the advertised-tag graph breadth-first: a discovered page can itself advertise a further unknown one, so one page is never the end of the trail. Bounded by the same probe cap and deadline as everything else."""
    already = _known_tags(client.get_profiles())
    advertised: set[str] = set()
    for section in ("preauth", "probes"):
        for entry in bundle.get(section, {}).values():
            advertised.update(entry.get("advertised", []))

    queued = {_base_tag(tag) for tag in advertised if _base_tag(tag) not in already}
    frontier = sorted(
        tag
        for tag in advertised
        if _base_tag(tag) not in already and _is_probeable(tag)
    )

    discovered: dict[str, Any] = {}
    truncated = False
    while frontier:
        if len(discovered) >= MAX_DISCOVERED_PROBES:
            truncated = True
            break
        if time.monotonic() > deadline:
            truncated = True
            break
        tag = frontier.pop(0)
        request_type = _discovered_request_type(tag)
        url = f"{client.base_url}/?_type={request_type}&_tag={tag}" f"&_={client.get_guid()}"
        entry: dict[str, Any] = {"type": request_type, "tag": tag, "source": "advertised"}
        entry.update(_fetch(client, url))
        discovered[f"discovered_{tag}"] = entry

        for new_tag in entry.get("advertised", []):
            advertised.add(new_tag)
            base = _base_tag(new_tag)
            if base in already or base in queued or not _is_probeable(new_tag):
                continue
            queued.add(base)
            frontier.append(new_tag)

    bundle["advertised_endpoints"] = sorted(advertised)[:MAX_ADVERTISED_TOTAL]
    if len(advertised) > MAX_ADVERTISED_TOTAL:
        bundle["advertised_endpoints_count"] = len(advertised)

    if truncated:
        bundle["discovery_truncated"] = True
    if frontier:
        not_probed = sorted({_base_tag(tag) for tag in frontier})
        bundle["advertised_endpoints_not_probed"] = not_probed[
            :MAX_ADVERTISED_LISTED_UNPROBED
        ]
        bundle["advertised_endpoints_not_probed_count"] = len(not_probed)

    bundle["probes"].update(discovered)


def _probe_owners(profiles: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    owners: dict[str, set[str]] = {}
    matrix = _probe_matrix(profiles)
    by_request: dict[tuple[str, str], str] = {
        value: name for name, value in matrix.items()
    }

    for profile_name, paths in profiles.items():
        for label, key in (("lan", "lan_script"), ("wlan", "wlan_script")):
            tag = paths.get(key)
            if not tag:
                continue
            request = (paths.get("type_main_request", "menuData"), tag)
            probe_name = by_request.get(request)
            if probe_name:
                owners.setdefault(probe_name, set()).add(profile_name)

    return owners


def _probe_matrix(profiles: dict[str, dict[str, Any]]) -> dict[str, tuple[str, str]]:
    """Return probe name -> (request type, tag), deduplicated."""
    probes: dict[str, tuple[str, str]] = dict(FIXED_PROBES)
    seen: set[tuple[str, str]] = set(probes.values())

    for profile_name, paths in profiles.items():
        for label, key, type_key in (
            ("lan", "lan_script", "type_main_request"),
            ("wlan", "wlan_script", "type_main_request"),
            # wan_view (MenuView) must run before wan (MenuData): the router
            # only returns real WAN data if the view was requested first,
            # otherwise it answers SessionTimeout. get_wan_status() does the
            # same view-then-data sequence for this reason.
            ("wan_view", "tag_wan_status_view", "type_first_request"),
            ("wan", "tag_wan_status_data", "type_main_request"),
            # Same view-before-data requirement as wan_view/wan. Only models
            # confirmed to be GPON ONTs define these tags (see F6600P in
            # zte_client.py); paths.get() returns None for everyone else, so
            # this loop simply skips them.
            ("pon_optical_view", "tag_pon_optical_view", "type_first_request"),
            ("pon_optical", "tag_pon_optical_data", "type_main_request"),
        ):
            tag = paths.get(key)
            if not tag:
                continue
            request_type = paths.get(type_key, "menuData")
            if (request_type, tag) in seen:
                continue
            seen.add((request_type, tag))
            probes[f"{profile_name}_{label}"] = (request_type, tag)

    return probes


def build_bundle(client: Any) -> dict[str, Any]:
    """Probe the router and describe what came back. Blocking; use executor."""
    logged_in_here = False

    bundle: dict[str, Any] = {
        # First key in the file on purpose: whoever opens it reads this before
        # anything else, and whoever skims it still sees it.
        "ABOUT_THIS_FILE": "This file describes the STRUCTURE of your router's responses. No hostname, SSID, serial number, MAC address or IP address is collected. Each response is reported as the nodes it contained, the field names inside them, how many records came back, and the shape of each value. What is included from your router: the model, hardware and firmware versions it reports, and the endpoint names it advertises. Field and node names are printed as your firmware supplies them, so have a look before you attach it.",
        "generated": datetime.now().astimezone().isoformat(),
        "configured_model": getattr(client, "model", None),
        "configured_profile": dict(getattr(client, "paths", {}) or {}),
        "preauth": {},
        "probes": {},
    }

    try:
        # The deadline covers everything, not just the probe walk: it used to
        # start after login, which left the pre-auth probes unbounded.
        deadline = time.monotonic() + WALK_DEADLINE

        # Pre-auth probes request login endpoints, including the one that mints
        # a session token. They must never run on the coordinator's
        coordinator_session = getattr(client, "session", None)
        if not hasattr(client, "_setup_session"):
            bundle["preauth_skipped"] = "client cannot create an isolated session"
        else:
            client._setup_session()
            try:
                for name, suffix in PREAUTH_PROBES.items():
                    if time.monotonic() > deadline:
                        bundle["preauth_truncated"] = True
                        break
                    bundle["preauth"][name] = _fetch(
                        client, f"{client.base_url}/{suffix}"
                    )
            finally:
                throwaway = getattr(client, "session", None)
                client.session = coordinator_session
                if throwaway is not None and throwaway is not coordinator_session:
                    try:
                        throwaway.close()
                    except Exception:  # noqa: BLE001 - best effort cleanup
                        _LOGGER.debug(
                            "Support bundle: closing the preauth session failed"
                        )
                if client.session is None:
                    client._setup_session()

        prior_session = getattr(client, "session", None)
        if client.login_data is None:
            if not client.login():
                # statusmsg is never copied in: it is built as "Cannot connect
                # to router at {host}", so copying it puts a DDNS name or an
                # address straight into a file meant for a public issue.
                bundle["error"] = "login failed"
                bundle["analysis"] = _analyse(bundle)
                # login() replaces client.session with a fresh one even when it fails.
                new_session = getattr(client, "session", None)
                if new_session is not None and new_session is not prior_session:
                    try:
                        new_session.close()
                    except Exception:  # noqa: BLE001 - best effort cleanup
                        _LOGGER.debug("Support bundle: closing failed session failed")
                    client.session = prior_session
                # login() can set login_data from a lockout response before it
                # decides the attempt failed.
                client.login_data = None
                return bundle
            logged_in_here = True

        details = client.get_router_details() or {}
        # Reported identity is the whole reason an unknown model becomes
        # addressable, so it is lifted out of the raw probes as well.
        bundle["reported"] = {
            key: details.get(key)
            for key in ("ModelName", "HardwareVer", "SoftwareVer", "ManuFacturer")
            if details.get(key)
        }

        profiles = client.get_profiles()
        # Read by _analyse, which reports it. Removed before the file is
        # written, like the owners map: same value twice is noise.
        bundle["_configured_profile_name"] = _configured_profile_name(client)
        # Recorded so scoring can credit every profile a shared endpoint
        # belongs to, not just the one that won the deduplication.
        bundle["_probe_owners"] = {
            name: sorted(names) for name, names in _probe_owners(profiles).items()
        }
        for name, (request_type, tag) in _probe_matrix(profiles).items():
            if time.monotonic() > deadline:
                bundle["walk_truncated"] = True
                _LOGGER.warning(
                    "Support bundle: deadline reached, %d probes not attempted",
                    len(_probe_matrix(profiles)) - len(bundle["probes"]),
                )
                break
            url = (
                f"{client.base_url}/?_type={request_type}&_tag={tag}"
                f"&_={client.get_guid()}"
            )
            entry: dict[str, Any] = {"type": request_type, "tag": tag}
            entry.update(_fetch(client, url))
            bundle["probes"][name] = entry

        _discover(client, bundle, deadline)

        bundle["analysis"] = _analyse(bundle)
        # Internal plumbing for scoring, not something a reader needs.
        bundle.pop("_probe_owners", None)
        bundle.pop("_configured_profile_name", None)
        return bundle
    finally:
        if logged_in_here:
            try:
                client.logout()
            except Exception:  # noqa: BLE001 - best effort cleanup
                _LOGGER.debug("Support bundle: logout after probing failed")
