#!/bin/bash
set -e

# Instalar Home Assistant Core y dependencias
python3 -m venv venv
source venv/bin/activate

# Actualizar pip y wheel
pip install --upgrade pip wheel

# Instalar Home Assistant Core en modo desarrollo
pip install -r tests/requirements_test.txt
cp tests/configuration_test.yaml /workspaces/homeassistant-core/configuration.yaml

# Mensaje de bienvenida
echo "Home Assistant Core está configurado. Usa el comando:"
echo "source venv/bin/activate && python3 -m homeassistant --config /workspaces/homeassistant-core/"