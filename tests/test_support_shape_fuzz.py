"""Property test: no value from a response ever appears in its description."""

import json
import os
import random
from unittest import TestCase

import _stub

ITERATIONS = int(os.environ.get("ZTE_FUZZ_ITERATIONS", "2000"))


def _load():
    return _stub.load("ztefuzzstub", "support_shape")


# Things a real household router actually returns, and the encodings that
# defeated the previous design.
VALUES = [
    "Dimitris-MacBook",
    "MyHouse-5G",
    "ZTEGD8A1B2C3",
    "a4:e9:75:2b:1c:3d",
    "A4-E9-75-2B-1C-3D",
    "88.197.44.12",
    "fe80::a6e9:75ff:fe2b:1c3d",
    "2101234567",
    "subscriber@isp.gr",
    "nikos.dsl.example.gr",
    "hunter2hunter2",
    "\uff19\uff13\uff0e\uff11\uff18\uff14\uff0e\uff12\uff11\uff16\uff0e\uff13\uff14",
    "93.\u200b184.216.34",
    "Kostas",
    "MyHouse",
]

# Field names only. A firmware that puts a client name where a field name
# belongs is the one documented residual of this design, covered by its own
# test below rather than by this property.
NAMES = [
    "HostName",
    "MACAddress",
    "SSIDName",
    "GponSerialNumber",
    "ExternalIPAddress",
    "WPAPassphrase",
    "PPPoEUser",
    "SomethingNobodyHasSeen",
]

NODES = ["OBJ_WLAN_AD_ID", "OBJ_ACCESSDEV_ID", "OBJ_SOMETHING_NEW"]


def _xml_pairs(rng, name, value):
    return (
        f"<ajax_response_xml_root><{rng.choice(NODES)}><Instance>"
        f"<ParaName>{name}</ParaName><ParaValue>{value}</ParaValue>"
        f"</Instance></{rng.choice(NODES)}></ajax_response_xml_root>"
    )


def _xml_children(rng, name, value):
    node = rng.choice(NODES)
    return f"<root><{node}><{name}>{value}</{name}></{node}></root>"


def _xml_attribute(rng, name, value):
    node = rng.choice(NODES)
    return f'<root><{node} {name}="{value}"><Instance/></{node}></root>'


def _xml_cdata(rng, name, value):
    node = rng.choice(NODES)
    return f"<root><{node}><{name}><![CDATA[{value}]]></{name}></{node}></root>"


def _json_value(rng, name, value):
    return json.dumps({name: value})


def _json_key(rng, name, value):
    return json.dumps({value: {"status": "online"}, "other": {"status": "online"}})


def _json_nested(rng, name, value):
    return json.dumps({"ad": {"1": {name: value}, "2": {name: value}}})


def _html(rng, name, value):
    return (
        f"<html><form action='/x/{value}/login?sn={value}'>"
        f"<input name='{value}'><input name='{name}'>"
        f"</form><script src='/js/{value}.js'></script></html>"
    )


def _plain(rng, name, value):
    return f"{name}: {value}\n{name}={value}\n"


BUILDERS = [
    _xml_pairs,
    _xml_children,
    _xml_attribute,
    _xml_cdata,
    _json_value,
    _json_key,
    _json_nested,
    _html,
    _plain,
]


class TestNothingFromTheRouterComesBack(TestCase):
    def setUp(self) -> None:
        self.module = _load()

    def test_no_generated_value_survives_description(self):
        rng = random.Random(20260910)
        failures = []

        for _ in range(ITERATIONS):
            builder = rng.choice(BUILDERS)
            name = rng.choice(NAMES)
            value = rng.choice(VALUES)
            body = builder(rng, name, value)
            described = json.dumps(
                self.module.describe(body, rng.choice(["text/xml", "text/html", ""])),
                ensure_ascii=False,
            )
            if value in described:
                failures.append((builder.__name__, name, value))
                if len(failures) > 4:
                    break

        self.assertEqual(
            failures,
            [],
            "a value came back in its own description",
        )

    def test_a_map_keyed_by_client_name_hides_the_keys(self):
        """The detectable half of the name position problem: when a response
        keys like shaped records by client name, the structure gives it away
        and the keys are replaced by a count."""
        rng = random.Random(7)
        for _ in range(min(ITERATIONS, 500)):
            value = rng.choice(["Dimitris-MacBook", "MyHouse", "Kostas"])
            body = json.dumps({value: {"n": 1}, "another": {"n": 2}})
            self.assertNotIn(value, json.dumps(self.module.describe(body, "")))

    def test_a_name_shaped_like_an_identifier_is_hidden(self):
        """The other detectable half: a name that is an address, a MAC or a
        long number is data whatever position it is in."""
        for value in (
            "a4:e9:75:2b:1c:3d",
            "A4-E9-75-2B-1C-3D",
            "2101234567",
            "88.197.44.12",
            "nikos.dsl.example.gr",
        ):
            for body in (
                f"<root><{('X' + value) if not value[0].isalpha() else value}>"
                f"<Instance/></{('X' + value) if not value[0].isalpha() else value}>"
                "</root>",
                json.dumps({value: 1, "other": 2}),
            ):
                described = json.dumps(self.module.describe(body, ""))
                self.assertNotIn(value, described, body)

    def test_a_plain_word_in_a_name_position_is_the_known_residual(self):
        """Stated as a test so it cannot quietly become untrue in either
        direction. A client called Kostas and a field called Status are both
        ordinary identifiers, and nothing in a single record distinguishes
        them, which is why the file still says to read it before attaching."""
        described = json.dumps(
            self.module.describe("<root><Kostas><Instance/></Kostas></root>", "")
        )
        self.assertIn("Kostas", described)

    def test_describe_never_raises(self):
        """A description that throws is a probe reported as a router failure,
        which is how a working router gets called unsupported."""
        rng = random.Random(99)
        for _ in range(min(ITERATIONS, 1000)):
            junk = "".join(
                rng.choice("<>{}[]&;\"'/\\ \n\t\x00\ufeff\uff1cabcXYZ019")
                for _ in range(rng.randint(0, 120))
            )
            self.module.describe(junk, rng.choice(["", "text/html", "text/xml"]))
