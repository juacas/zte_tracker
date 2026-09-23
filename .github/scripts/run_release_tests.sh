#!/usr/bin/env bash
# Runs the test suite against the exact commit that is about to be tagged.
set -euo pipefail
set -euo pipefail
pip install -r requirements.txt cryptography flake8==7.1.1 black==24.10.0
(cd tests && python -m unittest test_support_bundle test_service_layer test_diagnostics)
(cd tests/zteclient && python -m unittest test_router_details_parsing test_wan_status)
(cd tests && ZTE_FUZZ_ITERATIONS=50000 python -m unittest test_support_shape_fuzz)
modules=(
  custom_components/zte_tracker/support_shape.py
  custom_components/zte_tracker/support_bundle.py
  custom_components/zte_tracker/diagnostics.py
)
flake8 "${modules[@]}"
black --check "${modules[@]}"
