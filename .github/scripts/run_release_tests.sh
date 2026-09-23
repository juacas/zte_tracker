#!/usr/bin/env bash
# The one test suite: tests.yml runs this too, so the two can never drift apart.
set -euo pipefail
# cryptography: imported by zte_client, shipped by HA, declared nowhere.
pip install -r requirements.txt cryptography flake8==7.1.1 black==24.10.0
# These load their targets with importlib, so they need no Home Assistant.
(cd tests && python -m unittest test_support_bundle test_service_layer test_diagnostics)
(cd tests/zteclient && python -m unittest test_router_details_parsing test_wan_status)
# The property: no value from a router appears in its own description.
(cd tests && ZTE_FUZZ_ITERATIONS=50000 python -m unittest test_support_shape_fuzz)
modules=(
  custom_components/zte_tracker/support_shape.py
  custom_components/zte_tracker/support_bundle.py
  custom_components/zte_tracker/diagnostics.py
)
flake8 "${modules[@]}"
black --check "${modules[@]}"
