# ZTE Router Integration for Home Assistant

ZTE Router Integration is a Home Assistant custom component that provides device tracking for ZTE routers. It tracks devices connected to WiFi and LAN ports and exposes them as device trackers in Home Assistant.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

- **CRITICAL**: All tests require actual ZTE router hardware with TEST_HOST and TEST_PASSWORD environment variables set. Most validation can be done without hardware.
- **CRITICAL**: This is a Home Assistant custom integration - there is no traditional "build" process, only validation and testing.

### Essential Setup Commands:
```bash
# Install basic dependencies
python3 -m pip install requests homeassistant black flake8

# Validate Python syntax (ALWAYS run this first)
python3 -m py_compile custom_components/zte_tracker/__init__.py
python3 -m py_compile custom_components/zte_tracker/device_tracker.py
python3 -m py_compile custom_components/zte_tracker/zteclient/zte_client.py

# NEVER CANCEL: Run linting and formatting (takes < 5 seconds)
python3 -m flake8 custom_components/zte_tracker/*.py --max-line-length=88 --extend-ignore=E203
python3 -m black custom_components/zte_tracker/ --check
```

### Development Container Setup:
```bash
# NEVER CANCEL: Pull development container (takes 60-90 seconds)
docker pull ludeeus/container:integration-debian

# NEVER CANCEL: Start development environment (takes 3-5 minutes)
# Note: Requires VS Code with Remote-Containers extension for full functionality
docker run --rm -v $(pwd):/workspaces/zte_tracker -p 9123:8123 ludeeus/container:integration-debian
```

### Manual Testing (Requires Hardware):
```bash
# IMPORTANT: Only works with actual ZTE router access
export TEST_HOST=192.168.1.1  # Your router IP
export TEST_PASSWORD=your_router_password

# Run basic client test
cd custom_components/zte_tracker/zteclient
PYTHONPATH=/home/runner/work/zte_tracker/zte_tracker/custom_components/zte_tracker python3 -c "from zteclient.zte_client import zteClient; client = zteClient('192.168.1.1', 'admin', 'password', 'F6640'); print('Client created successfully')"
```

## Validation

- **ALWAYS** run Python syntax validation before making any changes.
- **ALWAYS** run linting after making changes to ensure code quality.
- **NEVER CANCEL** Docker operations - they may take several minutes but are essential for proper testing.
- You can validate the integration structure without actual router hardware.
- **MANUAL VALIDATION**: If you change core functionality, you must test with actual ZTE router hardware if available.

### GitHub Actions Validation:
- The repository uses GitHub Actions for hassfest and HACS validation
- These run automatically on push/PR and validate the Home Assistant integration structure
- Local hassfest validation requires full Home Assistant development environment

## Common Tasks

### Repository Structure:
```
custom_components/zte_tracker/
├── __init__.py              # Main integration setup
├── device_tracker.py        # Device tracker implementation  
├── sensor.py               # Status sensor
├── const.py                # Constants and configuration
├── manifest.json           # Home Assistant integration manifest
├── zteclient/              # ZTE router client library
│   ├── zte_client.py       # Main router communication client
│   ├── tests/              # Client-specific tests
│   └── routers/            # Router-specific configurations
└── tests/                  # Integration tests
```

### Supported Router Models:
Available models: F6640, H288A, H169A, H388X, H2640, F6645P, H3600P, H6645P, H3640

### Key Files to Monitor:
- `zte_client.py` - Core router communication logic
- `device_tracker.py` - Home Assistant device tracker implementation
- `manifest.json` - Integration metadata and dependencies
- `const.py` - Configuration constants

### Quick Validation Commands:
```bash
# Validate manifest.json structure (< 1 second)
python3 -c "import json; print('Manifest valid:', bool(json.load(open('custom_components/zte_tracker/manifest.json'))))"

# Check available router models (< 1 second)
cd custom_components/zte_tracker/zteclient && PYTHONPATH=.. python3 -c "from zteclient.zte_client import zteClient; print('Models:', zteClient.get_models(None))"

# Validate all Python files have correct syntax (< 2 seconds)
python3 -c "import ast; [ast.parse(open(f).read()) for f in ['custom_components/zte_tracker/__init__.py', 'custom_components/zte_tracker/device_tracker.py', 'custom_components/zte_tracker/zteclient/zte_client.py']]; print('All files have valid syntax')"
```

### Common Development Workflow:
1. **ALWAYS** validate Python syntax first with py_compile
2. Make your changes to the relevant files
3. **ALWAYS** run linting with flake8 to catch issues
4. **ALWAYS** format code with black if making significant changes
5. Test with actual hardware if available (set TEST_HOST and TEST_PASSWORD)
6. Validate that GitHub Actions will pass by ensuring manifest.json is valid

### Debugging Tips:
- The integration uses Python logging - check logs for router communication issues
- Router tests require network access to actual ZTE router hardware
- The devcontainer provides a full Home Assistant development environment
- Most validation can be done without router hardware using syntax and lint checks

### Time Expectations:
- Python syntax validation: < 1 second
- Linting entire codebase: < 5 seconds  
- Docker image pull: 60-90 seconds (NEVER CANCEL)
- Container startup: 3-5 minutes (NEVER CANCEL)
- Running tests with hardware: 10-30 seconds per test

### Configuration Examples:
The integration requires configuration in Home Assistant's configuration.yaml:
```yaml
zte_tracker:
  host: 192.168.1.1
  model: F6640
  username: admin
  password: !secret zte_password
  interval_seconds: 60
  consider_home: 180
```

### Development Scenarios:

**Scenario 1: Adding support for a new router model**
1. Validate syntax: `python3 -m py_compile custom_components/zte_tracker/zteclient/zte_client.py`
2. Add model to _MODELS dictionary in zte_client.py
3. Test model availability: `cd custom_components/zte_tracker/zteclient && PYTHONPATH=.. python3 -c "from zteclient.zte_client import zteClient; print('Models:', zteClient.get_models(None))"`
4. Run linting: `python3 -m flake8 custom_components/zte_tracker/zteclient/zte_client.py --max-line-length=88`
5. If possible, test with actual hardware using new model parameter

**Scenario 2: Fixing device detection issues**
1. Validate syntax of device_tracker.py first
2. Check router client communication in zteclient/zte_client.py
3. Use router web interface to understand data format changes
4. Update parsing logic in get_devices_response() method
5. Test with actual router: `export TEST_HOST=your_router_ip && export TEST_PASSWORD=your_password`

**Scenario 3: Updating Home Assistant integration structure**
1. Validate manifest.json: `python3 -c "import json; json.load(open('custom_components/zte_tracker/manifest.json'))"`
2. Check const.py for any new constants needed
3. Update __init__.py for new setup logic
4. Validate all syntax: `python3 -c "import ast; [ast.parse(open(f).read()) for f in ['custom_components/zte_tracker/__init__.py', 'custom_components/zte_tracker/device_tracker.py']]; print('All files valid')"`
5. Ensure GitHub Actions will pass (hassfest validation)

### Working Without Router Hardware:
- All syntax validation and linting works without hardware
- Structure validation works without hardware  
- Client instantiation works without hardware
- Actual login/device detection requires router access
- Use mock testing approaches for unit tests when no hardware available

### Critical Notes:
- This integration polls ZTE routers for device information
- Active polling can interfere with router web admin console sessions  
- The integration provides a pause/resume service to temporarily stop polling
- Router communication uses HTTP requests with session management and authentication
- **ALWAYS** validate Python syntax before pushing changes
- **NEVER CANCEL** Docker operations - they take time but provide full validation environment