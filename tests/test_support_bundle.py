"""End to end tests for the support bundle.

Happy paths plus the scenarios that map to open upstream issues. Everything
about "no value from the router comes back" lives in the fuzz property.
"""

import time
from unittest import TestCase

import _stub


def _load():
    return _stub.load("ztebundlestub", "support_shape", "support_bundle")


# The real profiles, copied so a change to _MODELS cannot silently rewrite what
# these tests mean. F8748 shares every endpoint with F6640 on purpose.
PROFILES = {
    "F6640": {
        "wlan_script": "wlan_client_stat_lua.lua",
        "lan_script": "accessdev_landevs_lua.lua",
        "tag_wan_status_view": "ethWanStatus",
        "tag_wan_status_data": "wan_internetstatus_lua.lua",
        "type_first_request": "menuView",
        "type_main_request": "menuData",
    },
    "F8748": {
        "wlan_script": "wlan_client_stat_lua.lua",
        "lan_script": "accessdev_landevs_lua.lua",
        "tag_wan_status_view": "ethWanStatus",
        "tag_wan_status_data": "wan_internetstatus_lua.lua",
        "type_first_request": "menuView",
        "type_main_request": "menuData",
        "parse_wan_traffic": True,
    },
    "H288A": {
        "wlan_script": "accessdev_ssiddev_lua.lua",
        "lan_script": "accessdev_landevs_lua.lua",
        "tag_wan_status_view": "ethWanStatus",
        "tag_wan_status_data": "wan_internetstatus_lua.lua",
        "type_first_request": "menuView",
        "type_main_request": "menuData",
    },
    "H388X": {
        "wlan_script": "accessdev_ssiddev_lua.lua",
        "lan_script": "accessdev_landevs_lua.lua",
        "tag_wan_status_view": "ethWanStatus",
        "tag_wan_status_data": "wan_internet_lua.lua",
        "type_first_request": "menuView",
        "type_main_request": "menuData",
    },
    "E2631": {
        "wlan_script": "vue_client_data",
        "lan_script": "localnet_lan_info_lua",
        "tag_wan_status_view": "vue_home_device_data_no_update_sess",
        "tag_wan_status_data": "vue_mainwan_data",
        "type_first_request": "vueData",
        "type_main_request": "vueData",
    },
}

# Every real response carries this envelope. Counting it as records made a
# reply with no devices look like a match.
ENVELOPE = (
    "<IF_ERRORID>0</IF_ERRORID><IF_ERRORSTR>SUCC</IF_ERRORSTR>"
    "<IF_ERRORTYPE>0</IF_ERRORTYPE>"
)


def devices_xml(node="OBJ_WLAN_AD_ID", count=3):
    instances = "".join(
        "<Instance>"
        "<ParaName>HostName</ParaName><ParaValue>SYNTH-DEVICE-%d</ParaValue>"
        "<ParaName>MACAddress</ParaName><ParaValue>a4:e9:75:2b:1c:%02x</ParaValue>"
        "</Instance>" % (i, i)
        for i in range(count)
    )
    return (
        f"<ajax_response_xml_root>{ENVELOPE}"
        f"<{node}>{instances}</{node}></ajax_response_xml_root>"
    )


EMPTY_XML = (
    f"<ajax_response_xml_root>{ENVELOPE}"
    "<OBJ_ACCESSDEV_ID></OBJ_ACCESSDEV_ID></ajax_response_xml_root>"
)
NOT_FOUND = "<html><body>404 Not Found</body></html>"


class _Response:
    def __init__(self, text, status=200, content_type="text/xml", encoding="utf-8"):
        self.text = text
        self.status_code = status
        self.headers = {"Content-Type": content_type}
        self.encoding = encoding
        self.closed = False

    def iter_content(self, chunk_size=8192):
        # Always real utf-8 on the wire. `encoding` is only what the router
        # claims in its header, which is the thing under test.
        data = self.text.encode("utf-8", errors="replace")
        step = max(chunk_size, 1)
        for start in range(0, len(data), step):
            yield data[start : start + step]

    def close(self):
        self.closed = True


class _Slow(_Response):
    def iter_content(self, chunk_size=8192):
        data = self.text.encode()
        for start in range(0, len(data), 40):
            time.sleep(0.02)
            yield data[start : start + 40]


class _Router:
    """A fake router. `routes` maps a substring of the URL to a response."""

    verify_ssl = False
    base_url = "https://192.168.1.1"
    model = "unknown"
    paths = PROFILES["F6640"]

    def __init__(self, routes, login_ok=True, default=None):
        self.routes = routes
        self.default = default if default is not None else _Response(NOT_FOUND, 404)
        self._login_ok = login_ok
        self.login_data = None
        self.session = self
        self.logged_out = False

    def get(self, url, verify=True, timeout=None, **kwargs):
        for fragment, response in self.routes.items():
            if fragment in url:
                return response
        return self.default

    def _setup_session(self):
        self.session = self

    def login(self):
        if self._login_ok:
            self.login_data = {"ok": 1}
        return self._login_ok

    def logout(self):
        self.logged_out = True

    def get_guid(self):
        return 1

    def get_router_details(self):
        return {"ModelName": self.model, "SoftwareVer": "V1.0.0"}

    @staticmethod
    def get_profiles():
        return PROFILES


class BundleTest(TestCase):
    def setUp(self) -> None:
        self.module = _load()

    def bundle(self, router):
        return self.module.build_bundle(router)


class TestHappyPath(BundleTest):
    def test_a_supported_router_is_identified(self):
        router = _Router(
            {
                "wlan_client_stat_lua.lua": _Response(devices_xml(count=4)),
                "accessdev_landevs_lua.lua": _Response(
                    devices_xml("OBJ_ACCESSDEV_ID", 2)
                ),
            }
        )
        router.model = "F6600P"
        analysis = self.bundle(router)["analysis"]

        self.assertEqual(analysis["best_matching_profile"], "F6640")
        self.assertEqual(analysis["configured_profile_name"], "F6640")
        self.assertTrue(analysis["configured_profile_answered"])
        # F8748 shares every endpoint, so probing cannot separate the two.
        self.assertEqual(analysis["tied_profiles"], ["F6640", "F8748"])

    def test_the_file_carries_no_internal_plumbing(self):
        """Scoring needs the owners map and the resolved profile name; a
        reader does not, and the profile name is already in the summary."""
        bundle = self.bundle(_Router({"": _Response(devices_xml(count=2))}))
        for key in ("_probe_owners", "probe_owners", "_configured_profile_name"):
            self.assertNotIn(key, bundle)
        self.assertIn("configured_profile_name", bundle["analysis"])

    def test_a_shared_endpoint_credits_every_profile_that_owns_it(self):
        """Three profiles share the LAN endpoint. Crediting only the winner of
        deduplication recommended F6640 for an H288A router."""
        router = _Router(
            {
                "accessdev_landevs_lua.lua": _Response(
                    devices_xml("OBJ_ACCESSDEV_ID", 10)
                ),
                "accessdev_ssiddev_lua.lua": _Response(devices_xml(count=4)),
                "wlan_client_stat_lua.lua": _Response(NOT_FOUND, 404),
            }
        )
        scores = self.bundle(router)["analysis"]["profile_scores"]
        self.assertEqual(scores["F6640"], 10)
        self.assertEqual(scores["H288A"], 14)
        self.assertEqual(scores["H388X"], 14)

    def test_the_login_is_released_only_when_we_took_it(self):
        taken = _Router({})
        self.bundle(taken)
        self.assertTrue(taken.logged_out)

        held = _Router({})
        held.login_data = {"ok": 1}
        self.bundle(held)
        self.assertFalse(held.logged_out)


class TestOpenIssues(BundleTest):
    def test_issue_40_an_empty_answer_is_not_a_match(self):
        """Connects, lists no devices. The envelope must not count as records."""
        router = _Router(
            {
                "accessdev_ssiddev_lua.lua": _Response(EMPTY_XML),
                "accessdev_landevs_lua.lua": _Response(EMPTY_XML),
            }
        )
        analysis = self.bundle(router)["analysis"]

        self.assertIsNone(analysis["best_matching_profile"])
        self.assertTrue(analysis["endpoints_answered_empty"])
        self.assertNotIn("IF_ERRORSTR", analysis["nodes_seen"])
        self.assertNotIn("<envelope>", analysis["nodes_seen"])

    def test_issue_40_a_refusal_is_distinguishable_from_no_devices(self):
        """instances: 0 alone cannot tell a wrong endpoint from a router that
        refused. The envelope value is the byte that does."""
        refused = (
            "<ajax_response_xml_root><IF_ERRORSTR>NO_AUTH</IF_ERRORSTR>"
            "<OBJ_ACCESSDEV_ID></OBJ_ACCESSDEV_ID></ajax_response_xml_root>"
        )
        router = _Router({"accessdev_landevs_lua.lua": _Response(refused)})
        nodes = self.bundle(router)["probes"]["F6640_lan"]["structure"]["nodes"]

        self.assertEqual(
            nodes["<envelope>"]["fields"]["IF_ERRORSTR"]["value"], "NO_AUTH"
        )

    def test_issue_13_json_enums_are_published_too(self):
        """The vue dialect carries the same dispatch literals in JSON."""
        body = '{"ConnStatus":"Connected","AccessType":"1","HostName":"nikos-pc"}'
        router = _Router({"vue_client_data": _Response(body, 200, "application/json")})
        keys = self.bundle(router)["probes"]["E2631_wlan"]["structure"]["keys"]

        self.assertEqual(keys["ConnStatus"]["value"], "Connected")
        self.assertEqual(keys["AccessType"]["value"], "1")
        self.assertNotIn("nikos-pc", str(keys))

    def test_issue_24_a_failed_login_still_produces_evidence(self):
        """The login page is classified, which is the only readable evidence
        when the login itself is what fails. Its text never travels."""
        page = (
            "<html><form action='/login'><input name='Username'>"
            "<input type='password' name='Password'></form>"
            "<span>Welcome to MyHouseWiFi</span></html>"
        )
        router = _Router({"login": _Response(page, 200, "text/html")}, login_ok=False)
        bundle = self.bundle(router)

        self.assertEqual(bundle["error"], "login failed")
        captured = bundle["preauth"]["login_session_token"]["structure"]
        self.assertEqual(captured["format"], "html")
        self.assertEqual(captured["kind"], "login_form")
        self.assertEqual(captured["password_inputs"], 1)
        self.assertNotIn("MyHouseWiFi", str(bundle))

    def test_a_session_bounce_is_distinguishable_from_a_login_form(self):
        """Both are HTML with no data. Only the classification separates
        "the router asked me to log in" from "it bounced me"."""
        bounce = "<html><meta http-equiv='refresh' content='0;url=/login'></html>"
        router = _Router({"login": _Response(bounce, 200, "text/html")}, login_ok=False)
        kind = self.bundle(router)["preauth"]["login_session_token"]["structure"][
            "kind"
        ]
        self.assertEqual(kind, "redirect_or_refresh")

    def test_discovery_follows_a_chain_of_advertised_pages(self):
        """An endpoint discovered this round can itself advertise a further unknown one; the walk must not stop after a single hop."""
        router = _Router(
            {
                "accessdev_ssiddev_lua.lua": _Response(devices_xml(count=3)),
                "localNetStatus": _Response(
                    "<html>?_type=menuData&_tag=first_hop_lua.lua</html>",
                    200,
                    "text/html",
                ),
                "first_hop_lua.lua": _Response(
                    "<html>?_type=menuData&_tag=second_hop_lua.lua</html>",
                    200,
                    "text/html",
                ),
                "second_hop_lua.lua": _Response(devices_xml("OBJ_WANLAN_ID", 1)),
            }
        )
        bundle = self.bundle(router)

        self.assertIn("second_hop_lua.lua", bundle["advertised_endpoints"])
        probe = bundle["probes"]["discovered_second_hop_lua.lua"]
        self.assertEqual(probe["status"], 200)
        self.assertEqual(probe["source"], "advertised")

    def test_discovery_stops_at_the_probe_cap_even_across_many_hops(self):
        """A chain longer than the cap must be truncated, not followed forever: the cap is a safety bound, not a single-hop limit."""
        cap = self.module.MAX_DISCOVERED_PROBES
        routes = {
            "accessdev_ssiddev_lua.lua": _Response(devices_xml(count=3)),
            "localNetStatus": _Response(
                "<html>?_type=menuData&_tag=hop_0_lua.lua</html>", 200, "text/html"
            ),
        }
        for i in range(cap + 3):
            routes[f"hop_{i}_lua.lua"] = _Response(
                f"<html>?_type=menuData&_tag=hop_{i + 1}_lua.lua</html>",
                200,
                "text/html",
            )
        bundle = self.bundle(_Router(routes))

        self.assertTrue(bundle.get("discovery_truncated"))
        discovered = [
            key for key in bundle["probes"] if key.startswith("discovered_hop_")
        ]
        self.assertEqual(len(discovered), cap)
        self.assertIn("advertised_endpoints_not_probed", bundle)

    def test_wan_status_view_page_also_advertises_unknown_endpoints(self):
        """The bundle probes each profile's WAN view page, not just the LAN one, so an unadvertised WAN endpoint can be discovered without any user-supplied XML."""
        router = _Router(
            {
                "accessdev_ssiddev_lua.lua": _Response(devices_xml(count=3)),
                "ethWanStatus": _Response(
                    "<html>?_type=menuData&_tag=wan_ip_status_lua.lua</html>",
                    200,
                    "text/html",
                ),
                "wan_ip_status_lua.lua": _Response(
                    devices_xml("OBJ_WANLAN_ID", 1)
                ),
            }
        )
        bundle = self.bundle(router)

        self.assertIn("wan_ip_status_lua.lua", bundle["advertised_endpoints"])
        probe = bundle["probes"]["discovered_wan_ip_status_lua.lua"]
        self.assertEqual(probe["status"], 200)
        self.assertEqual(probe["source"], "advertised")

    def test_issue_75_an_advertised_endpoint_is_discovered(self):
        """WAN status lives where no profile looks, but the router names it."""
        router = _Router(
            {
                "accessdev_ssiddev_lua.lua": _Response(devices_xml(count=3)),
                "localNetStatus": _Response(
                    "<html>?_type=menuData&_tag=dsl_interface_status_lua.lua</html>",
                    200,
                    "text/html",
                ),
                "dsl_interface_status_lua.lua": _Response(
                    devices_xml("OBJ_DSLINTERFACE_ID", 1)
                ),
            }
        )
        bundle = self.bundle(router)

        self.assertIn("dsl_interface_status_lua.lua", bundle["advertised_endpoints"])
        probe = bundle["probes"]["discovered_dsl_interface_status_lua.lua"]
        self.assertEqual(probe["status"], 200)
        self.assertEqual(probe["source"], "advertised")
        # A discovered tag must never be mistaken for a profile.
        self.assertEqual(bundle["analysis"]["best_matching_profile"], "H288A")

    def test_issue_13_nothing_matches_and_the_report_says_so(self):
        router = _Router({}, default=_Response(NOT_FOUND, 404))
        analysis = self.bundle(router)["analysis"]

        self.assertIsNone(analysis["best_matching_profile"])
        self.assertEqual(analysis["nodes_seen"], [])
        self.assertEqual({p["status"] for p in analysis["probes"].values()}, {404})


class TestSufficiency(BundleTest):
    """The export is worth nothing if a maintainer cannot act on it."""

    def test_the_values_a_parser_branches_on_are_present(self):
        """Every parser branch in the client dispatches on a literal: the
        internet WAN is WANCName == WAN_internet, up is ConnStatus ==
        Connected. Knowing the field exists is not enough."""
        wan = (
            f"<ajax_response_xml_root>{ENVELOPE}<OBJ_WANPPP_ID><Instance>"
            "<ParaName>WANCName</ParaName><ParaValue>WAN_internet</ParaValue>"
            "<ParaName>ConnStatus</ParaName><ParaValue>Connected</ParaValue>"
            "</Instance></OBJ_WANPPP_ID></ajax_response_xml_root>"
        )
        router = _Router({"wan_internetstatus_lua.lua": _Response(wan)})
        fields = self.bundle(router)["probes"]["F6640_wan"]["structure"]["nodes"][
            "OBJ_WANPPP_ID"
        ]["fields"]

        self.assertEqual(fields["WANCName"]["value"], "WAN_internet")
        self.assertEqual(fields["ConnStatus"]["value"], "Connected")

    def test_an_enum_field_still_cannot_carry_a_name(self):
        """A firmware that puts the SSID in a field called Status is why the
        list is exact names rather than anything status shaped."""
        body = (
            f"<ajax_response_xml_root>{ENVELOPE}<OBJ_WLAN_ID><Instance>"
            "<ParaName>Status</ParaName><ParaValue>MyHouseWiFi</ParaValue>"
            "<ParaName>SSID</ParaName><ParaValue>MyHouseWiFi</ParaValue>"
            "</Instance></OBJ_WLAN_ID></ajax_response_xml_root>"
        )
        router = _Router({"": _Response(body)})
        self.assertNotIn("MyHouseWiFi", str(self.bundle(router)))

    def test_the_file_carries_no_internal_plumbing(self):
        bundle = self.bundle(_Router({"": _Response(devices_xml(count=2))}))
        self.assertNotIn("_probe_owners", bundle)
        self.assertNotIn("probe_owners", bundle)
        # One explanation, not two.
        self.assertEqual(list(bundle)[0], "ABOUT_THIS_FILE")
        self.assertNotIn("what_this_contains", bundle)


class TestSafety(BundleTest):
    def test_no_probe_carries_a_body(self):
        """The guarantee everything else rests on."""
        bundle = self.bundle(_Router({"": _Response(devices_xml(count=3))}))

        for name, probe in bundle["probes"].items():
            self.assertNotIn("body", probe, name)
            self.assertIn("structure", probe, name)
        self.assertNotIn("SYNTH-DEVICE", str(bundle))
        self.assertNotIn("a4:e9:75", str(bundle))

    def test_preauth_never_touches_the_coordinator_session(self):
        """Pre-auth probes hit the token endpoint. On the live session a
        firmware that resets it would cost the integration its login."""

        class _Tracking(_Router):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # A session that works, so the probe succeeds and the test
                # measures which one was used rather than a failure.
                self.live = _Response(devices_xml(count=1))
                self.live.get = lambda url, **kw: _Response(devices_xml(count=1))
                self.session = self.live
                self.used = []

            def _setup_session(self):
                self.session = self

            def get(self, url, verify=True, timeout=None, **kwargs):
                self.used.append(self.session)
                return super().get(url, verify=verify, timeout=timeout, **kwargs)

        router = _Tracking({"": _Response(devices_xml(count=2))})
        router.login_data = {"ok": 1}
        self.bundle(router)

        self.assertNotIn(router.live, router.used)

    def test_a_slow_body_is_bounded_and_dropped(self):
        original = self.module.BODY_READ_BUDGET
        self.module.BODY_READ_BUDGET = 0.05
        try:
            entry = self.module._fetch(
                _Router({"": _Slow(devices_xml(count=3))}), "https://192.168.1.1/x"
            )
        finally:
            self.module.BODY_READ_BUDGET = original

        self.assertTrue(entry["read_truncated"])
        self.assertNotIn("SYNTH-DEVICE", str(entry))

    def test_a_failed_login_restores_the_coordinator_session(self):
        """login() builds a fresh session even when it fails. Leaving that in
        place hands the coordinator a half built session, and login_data set
        from a lockout reply makes it skip re auth entirely."""

        class _Swapping(_Router):
            def login(self):
                self.login_data = {"locked": 1}
                self.session = _Response("")
                return False

        router = _Swapping({}, login_ok=False)
        original = router.session
        bundle = self.bundle(router)

        self.assertEqual(bundle["error"], "login failed")
        self.assertIs(router.session, original)
        self.assertIsNone(router.login_data)

    def test_a_failed_probe_records_only_the_exception_class(self):
        """A requests exception stringifies to the full URL, which carries the
        host. This file is destined for a public issue."""

        class _Refusing(_Router):
            def get(self, url, verify=True, timeout=None, **kwargs):
                raise OSError(f"connection refused to {url}")

        entry = self.module._fetch(
            _Refusing({}), "https://nikos-home.duckdns.org/x?_tag=y"
        )

        self.assertEqual(entry["error"], "OSError")
        blob = str(entry)
        self.assertNotIn("duckdns", blob)
        self.assertNotIn("refused", blob)

    def test_an_unknown_charset_does_not_cost_the_body(self):
        """A charset the router invented must not empty every probe."""
        entry = self.module._fetch(
            _Router({"": _Response(devices_xml(count=2), encoding="x-zte-invented")}),
            "https://192.168.1.1/x",
        )

        self.assertNotIn("error", entry)
        self.assertEqual(entry["structure"]["format"], "xml")
