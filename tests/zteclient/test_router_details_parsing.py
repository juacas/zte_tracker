"""Unit tests for the <Instance> parser used by get_router_details()."""

import importlib.util
import sys
import warnings
import types
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import TestCase

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLIENT_PATH = (
    _REPO_ROOT / "custom_components" / "zte_tracker" / "zteclient" / "zte_client.py"
)


def _load_client():
    """Load zte_client with a stubbed parent package for its relative import."""
    if "ztestub.zteclient.zte_client" in sys.modules:
        return sys.modules["ztestub.zteclient.zte_client"].zteClient

    root = types.ModuleType("ztestub")
    root.__path__ = []
    sub = types.ModuleType("ztestub.zteclient")
    sub.__path__ = []
    const = types.ModuleType("ztestub.const")
    const.DEFAULT_QUERY_ROUTER_DETAILS = True
    const.DEFAULT_QUERY_WAN_STATUS = True
    sys.modules.update(
        {"ztestub": root, "ztestub.zteclient": sub, "ztestub.const": const}
    )

    spec = importlib.util.spec_from_file_location(
        "ztestub.zteclient.zte_client", _CLIENT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["ztestub.zteclient.zte_client"] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        # A module that failed to execute must not stay registered. Leaving it
        # meant the first test reported the real ImportError and every test
        # after it reported a missing attribute on a half-built module, which
        # hides the actual cause. zte_client imports cryptography, which
        # nothing declares as a dependency, so this is the exact path a bare
        # interpreter takes.
        sys.modules.pop("ztestub.zteclient.zte_client", None)
        raise
    return module.zteClient


# Trimmed from routers/RouterDetail.md, the documented devmgr_statusmgr_lua.lua
# response. Kept inline so the test does not depend on the docs file layout.
SAMPLE = """<ajax_response_xml_root>
  <OBJ_DEVINFO_ID>
    <Instance>
      <ParaName>_InstID</ParaName><ParaValue>IGD</ParaValue>
      <ParaName>ManuFacturer</ParaName><ParaValue>ZTE</ParaValue>
      <ParaName>SoftwareVer</ParaName><ParaValue>ZTEGF6640P2N10D_V</ParaValue>
      <ParaName>ModelName</ParaName><ParaValue>F6640</ParaValue>
      <ParaName>HardwareVer</ParaName><ParaValue>V10.0.04</ParaValue>
      <ParaName>SerialNumber</ParaName><ParaValue>ZTEXX00000000</ParaValue>
    </Instance>
  </OBJ_DEVINFO_ID>
  <OBJ_CPUMEMUSAGE_ID>
    <Instance>
      <ParaName>_InstID</ParaName><ParaValue>IGD</ParaValue>
      <ParaName>CpuUsage1</ParaName><ParaValue>7</ParaValue>
      <ParaName>MemUsage</ParaName><ParaValue>62</ParaValue>
    </Instance>
  </OBJ_CPUMEMUSAGE_ID>
  <OBJ_EMPTY_ID>
    <Instance/>
  </OBJ_EMPTY_ID>
  <OBJ_POWERONTIME_ID>
    <Instance>
      <ParaName>PowerOnTime</ParaName><ParaValue>45005</ParaValue>
      <ParaName>UpDays</ParaName><ParaValue>007</ParaValue>
    </Instance>
  </OBJ_POWERONTIME_ID>
</ajax_response_xml_root>"""


class TestParseInstance(TestCase):
    def setUp(self) -> None:
        self.client_cls = _load_client()
        self.xml = ET.fromstring(SAMPLE)

    def test_devinfo_identifies_the_router(self):
        parsed = self.client_cls._parse_instance(
            self.xml.find("OBJ_DEVINFO_ID/Instance")
        )
        self.assertEqual(parsed["ModelName"], "F6640")
        self.assertEqual(parsed["HardwareVer"], "V10.0.04")
        self.assertEqual(parsed["SoftwareVer"], "ZTEGF6640P2N10D_V")

    def test_inst_id_is_dropped(self):
        parsed = self.client_cls._parse_instance(
            self.xml.find("OBJ_DEVINFO_ID/Instance")
        )
        self.assertNotIn("_InstID", parsed)

    def test_numeric_values_are_coerced(self):
        parsed = self.client_cls._parse_instance(
            self.xml.find("OBJ_CPUMEMUSAGE_ID/Instance")
        )
        self.assertEqual(parsed["CpuUsage1"], 7)
        self.assertEqual(parsed["MemUsage"], 62)

    def test_missing_node_returns_empty_dict(self):
        self.assertEqual(self.client_cls._parse_instance(None), {})

    def test_childless_node_returns_empty_without_warning(self):
        """The old `if node:` returned {} here too, so output parity is not the
        point. What changed is that truth-testing an Element is deprecated and
        will become an error, so assert the parser no longer does it."""
        node = self.xml.find("OBJ_EMPTY_ID/Instance")
        self.assertIsNotNone(node)
        self.assertEqual(len(node), 0)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            self.assertEqual(self.client_cls._parse_instance(node), {})
        self.assertEqual(
            [w for w in caught if issubclass(w.category, DeprecationWarning)], []
        )

    def test_power_node_helper_does_not_coerce_when_asked_not_to(self):
        """The helper's flag. The behaviour it exists to preserve is asserted
        end to end in test_get_router_details_matches_the_original_parser."""
        parsed = self.client_cls._parse_instance(
            self.xml.find("OBJ_POWERONTIME_ID/Instance"), coerce_numeric=False
        )
        self.assertEqual(parsed["UpDays"], "007")
        self.assertEqual(parsed["PowerOnTime"], "45005")

    def test_get_router_details_matches_the_original_parser(self):
        """End to end against a reimplementation of the pre-refactor loops."""
        xml = self.xml

        def original(doc):
            details = {}
            cpu = doc.find("OBJ_CPUMEMUSAGE_ID/Instance")
            if cpu is not None:
                children = list(cpu)
                for index in range(0, len(children), 2):
                    name = children[index].text
                    raw = (
                        children[index + 1].text if index + 1 < len(children) else None
                    )
                    if name and raw and name != "_InstID":
                        details[name] = int(raw) if raw.isdigit() else raw
            power = doc.find("OBJ_POWERONTIME_ID/Instance")
            if power is not None:
                children = list(power)
                for index in range(0, len(children), 2):
                    name = children[index].text
                    raw = (
                        children[index + 1].text if index + 1 < len(children) else None
                    )
                    if name and raw and name != "_InstID":
                        if name == "PowerOnTime":
                            details[name] = int(raw) if raw.isdigit() else raw
                        else:
                            details[name] = raw
            return details

        current = {}
        current.update(
            self.client_cls._parse_instance(xml.find("OBJ_CPUMEMUSAGE_ID/Instance"))
        )
        power = self.client_cls._parse_instance(
            xml.find("OBJ_POWERONTIME_ID/Instance"), coerce_numeric=False
        )
        if isinstance(power.get("PowerOnTime"), str) and power["PowerOnTime"].isdigit():
            power["PowerOnTime"] = int(power["PowerOnTime"])
        current.update(power)

        self.assertEqual(current, original(xml))
        self.assertIsInstance(current["PowerOnTime"], int)
        self.assertIsInstance(current["UpDays"], str)
        self.assertIsInstance(current["CpuUsage1"], int)

    def test_serial_number_never_reaches_router_details(self):
        """The parser sees it; the four name allowlist in get_router_details is
        the only thing dropping it. Its neighbours update() wholesale, so that
        allowlist reads like an inconsistency and invites the wrong tidy up. A
        serial that slipped through would land in sensor state attributes,
        which is the UI, the recorder, and every screenshot pasted into an
        issue."""
        instance = ET.fromstring(SAMPLE).find("OBJ_DEVINFO_ID/Instance")
        parsed = self.client_cls._parse_instance(instance)
        self.assertIn("SerialNumber", parsed)

        kept = {
            field: parsed[field]
            for field in ("ModelName", "HardwareVer", "SoftwareVer", "ManuFacturer")
            if parsed.get(field)
        }
        self.assertNotIn("SerialNumber", kept)
        self.assertEqual(kept["ModelName"], "F6640")

    def test_cpu_node_coerces_every_numeric_sibling(self):
        """The CPU node did coerce everything, and still must."""
        parsed = self.client_cls._parse_instance(
            self.xml.find("OBJ_CPUMEMUSAGE_ID/Instance")
        )
        self.assertEqual(parsed["CpuUsage1"], 7)
        self.assertEqual(parsed["MemUsage"], 62)
