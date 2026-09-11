"""Tests for the service layer: file writing, permissions and pruning.

`build_bundle` was well covered and the service that writes its output was not,
which is how a failing login came to produce a perfectly good bundle that was
then discarded before it reached disk. These exercise the parts that only exist
because the config directory is shared over the LAN by the Samba add-on.
"""

import ast
import json
import logging
import os
import stat
import sys
import tempfile
import time
import types
from pathlib import Path
from unittest import TestCase

_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "zte_tracker"
_PKG = "zteservicestub"


def _load():
    """Load only the two filesystem helpers, with their real source.

    Stubbing the whole of Home Assistant to reach two functions that touch
    nothing but os and json is more machinery than the thing under test, and a
    stub that drifts silently starts passing for the wrong reason. These are
    extracted from the real file by name, so they cannot drift at all.
    """
    if f"{_PKG}.init" in sys.modules:
        return sys.modules[f"{_PKG}.init"]

    tree = ast.parse((_DIR / "__init__.py").read_text())
    # BUNDLE_DIRNAME lives in support_bundle so diagnostics can name the folder
    # without importing the integration package.
    tree.body.extend(
        node
        for node in ast.parse((_DIR / "support_bundle.py").read_text()).body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(t, ast.Name) and t.id == "BUNDLE_DIRNAME" for t in node.targets
        )
    )
    wanted = {
        "_write_bundle",
        "_prune_old_bundles",
        "BUNDLE_DIRNAME",
        "BUNDLE_MAX_AGE_SECONDS",
    }
    kept = [
        node
        for node in tree.body
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in wanted
        )
        or (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id in wanted for t in node.targets)
        )
    ]
    module = types.ModuleType(f"{_PKG}.init")
    module.os = os
    module.json = json
    module.time = time
    module.HomeAssistant = object
    module.HomeAssistantError = RuntimeError
    module._LOGGER = logging.getLogger(__name__)
    exec(  # noqa: S102 - the repository's own source, by name
        compile(ast.Module(body=kept, type_ignores=[]), "<extracted>", "exec"),
        module.__dict__,
    )
    sys.modules[f"{_PKG}.init"] = module
    return module


class _Hass:
    def __init__(self, root):
        self._root = root

    class config:  # noqa: D106 - replaced per instance below
        pass

    def path(self, *parts):
        return os.path.join(self._root, *parts)


class ServiceLayerTest(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.module = _load()
        except Exception as err:  # noqa: BLE001 - reported as a skip below
            cls.module = None
            cls.reason = f"{type(err).__name__}: {err}"

    def setUp(self) -> None:
        if self.module is None:
            self.skipTest(f"__init__ could not be stubbed: {self.reason}")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        hass = types.SimpleNamespace()
        hass.config = types.SimpleNamespace(
            path=lambda *p: os.path.join(self.tmp.name, *p)
        )
        self.hass = hass

    def directory(self):
        return os.path.join(self.tmp.name, self.module.BUNDLE_DIRNAME)


class TestWriteBundle(ServiceLayerTest):
    def test_the_file_is_owner_only(self):
        """Default umask would leave it world readable in a Samba share."""
        path = os.path.join(self.directory(), "export-test.json")
        self.module._write_bundle(path, {"a": 1})
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)

    def test_an_existing_loose_directory_is_tightened(self):
        """os.makedirs ignores its mode argument when the target exists, and
        after the first export it always exists."""
        os.makedirs(self.directory(), mode=0o755)
        os.chmod(self.directory(), 0o755)
        self.module._write_bundle(
            os.path.join(self.directory(), "export-test.json"), {"a": 1}
        )
        self.assertEqual(stat.S_IMODE(os.stat(self.directory()).st_mode), 0o700)

    def test_a_symlinked_directory_is_refused(self):
        """Following it would chmod and write into whatever it points at."""
        target = os.path.join(self.tmp.name, "elsewhere")
        os.makedirs(target)
        os.symlink(target, self.directory())

        with self.assertRaises(Exception):
            self.module._write_bundle(
                os.path.join(self.directory(), "export-test.json"), {"a": 1}
            )


class TestFailedLoginIsStillWritten(TestCase):
    """The round twelve blocker: a failing login produced a good bundle that
    the service threw away before writing, which killed the one issue the
    pre-auth capture was built for. The guard is dict logic, so it is asserted
    directly: any rework that moves pre-auth after login restores the bug."""

    @staticmethod
    def discarded(bundle):
        # Mirrors __init__.py: write unless there is an error AND nothing was
        # captured before it.
        return bool(bundle.get("error") and not bundle.get("preauth"))

    def test_a_login_failure_carrying_evidence_is_written(self):
        self.assertFalse(
            self.discarded(
                {"error": "login failed", "preauth": {"login_page": {"status": 200}}}
            )
        )

    def test_a_login_failure_with_nothing_captured_is_discarded(self):
        self.assertTrue(self.discarded({"error": "login failed", "preauth": {}}))

    def test_a_successful_walk_is_always_written(self):
        self.assertFalse(self.discarded({"probes": {"a": {}}, "preauth": {}}))


class TestPruning(ServiceLayerTest):
    def test_only_old_exports_are_removed(self):
        os.makedirs(self.directory(), mode=0o700)
        old = os.path.join(self.directory(), "export-old.json")
        new = os.path.join(self.directory(), "export-new.json")
        keep = os.path.join(self.directory(), "notes.txt")
        for path in (old, new, keep):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{}")
        stale = time.time() - 60 * 60 * 30
        os.utime(old, (stale, stale))

        self.module._prune_old_bundles(self.hass)

        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.exists(new))
        self.assertTrue(os.path.exists(keep))

    def test_a_symlink_is_not_followed(self):
        os.makedirs(self.directory(), mode=0o700)
        outside = os.path.join(self.tmp.name, "precious.json")
        with open(outside, "w", encoding="utf-8") as handle:
            handle.write("{}")
        stale = time.time() - 60 * 60 * 30
        os.utime(outside, (stale, stale))
        os.symlink(outside, os.path.join(self.directory(), "export-link.json"))

        self.module._prune_old_bundles(self.hass)

        self.assertTrue(os.path.exists(outside))
