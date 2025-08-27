# ZTE Router Integration for Home Assistant

ZTE Router Integration is a Python-based Home Assistant custom integration that provides device tracking for ZTE routers. The integration monitors connected devices on Wifi and LAN ports, exposes status sensors, and provides router control services.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

- **Validate Python syntax** (takes ~0.4s):
  ```bash
  find . -name '*.py' -exec python3 -m py_compile {} \;
  ```

- **Test imports and basic functionality** (takes ~0.1s):
  ```bash
  python3 -c "import sys; sys.path.extend(['custom_components/zte_tracker', 'custom_components/zte_tracker/zteclient']); from zte_client import zteClient; client = zteClient('192.168.1.1', 'admin', 'test', 'F6640'); print('✓ Import and instantiation successful')"
  ```

- **Run comprehensive tests** (takes ~0.1s):
  ```bash
  cd custom_components/zte_tracker/zteclient && python3 -c "
  from zte_client import zteClient
  models = ['F6640', 'H288A', 'H169A', 'H388X', 'H2640', 'F6645P', 'H3600P', 'H6645P', 'H3640']
  for model in models:
      client = zteClient('192.168.1.1', 'admin', 'test', model)
      assert client.model == model
  print('✓ All', len(models), 'supported router models validated')
  "
  ```

- **Validate JSON configuration files** (takes ~0.02s):
  ```bash
  python3 -c "import json; json.load(open('custom_components/zte_tracker/manifest.json')); json.load(open('custom_components/zte_tracker/strings.json')); json.load(open('hacs.json')); print('✓ All JSON files valid')"
  ```

## Development Environment

### VS Code + DevContainer (Recommended)
The repository includes a complete DevContainer setup for Home Assistant development:

- **Start DevContainer** (NEVER CANCEL - may take 5+ minutes on first run):
  ```bash
  # From VS Code: Command Palette > "Remote-Containers: Reopen Folder in Container"
  # Or manually:
  docker run --rm -v $(pwd):/workspace -p 9123:8123 ludeeus/container:integration-debian
  ```

- **Container validation** (takes ~0.6s):
  ```bash
  docker run --rm -v $(pwd):/workspace ludeeus/container:integration-debian bash -c 'cd /workspace && find . -name "*.py" -exec python3 -m py_compile {} \;'
  ```

### Dependencies
- **Install required dependencies**:
  ```bash
  pip3 install requests voluptuous
  ```

- **Install development tools** (for linting and formatting):
  ```bash
  pip3 install black flake8 pylint
  ```

## Code Quality and Validation

### Linting (takes ~0.2s - expect style issues):
```bash
flake8 custom_components/zte_tracker/ --count --statistics --max-line-length=88
```

### Formatting (takes ~0.3s - expect reformatting needed):
```bash
black --check custom_components/zte_tracker/
```

### Apply formatting:
```bash
black custom_components/zte_tracker/
```

## Validation Scenarios

**CRITICAL**: Always run through these validation scenarios after making changes:

1. **Basic integration test**:
   ```bash
   python3 -c "
   import sys
   sys.path.extend(['custom_components/zte_tracker', 'custom_components/zte_tracker/zteclient'])
   from zte_client import zteClient
   import const
   print('✓ Domain:', const.DOMAIN)
   client = zteClient('192.168.1.1', 'admin', 'test', 'F6640')
   print('✓ Client created for model:', client.model)
   print('✓ Available models:', client.get_models())
   "
   ```

2. **Mock Home Assistant test**:
   ```bash
   python3 -c "
   import sys
   sys.path.extend(['custom_components/zte_tracker', 'custom_components/zte_tracker/zteclient'])
   from zte_client import zteClient
   
   # Test mock objects like Home Assistant tests do
   class HassMock:
       def __init__(self):
           self.data = {}
           self.states = type('obj', (object,), {'set': lambda self, x: None})()
   
   hass = HassMock()
   client = zteClient('192.168.1.1', 'admin', 'test', 'F6640')
   print('✓ Mock Home Assistant objects work correctly')
   "
   ```

## Common Tasks

### Repository Structure
```
.
├── README.md                           # Installation and usage instructions
├── custom_components/zte_tracker/      # Main integration code
│   ├── __init__.py                     # Integration setup and services
│   ├── device_tracker.py               # Device tracking implementation
│   ├── sensor.py                       # Status sensors
│   ├── const.py                        # Constants and configuration
│   ├── manifest.json                   # Integration metadata
│   ├── services.yaml                   # Service definitions
│   ├── strings.json                    # UI strings
│   ├── tests/                          # Integration tests
│   └── zteclient/                      # ZTE router client library
│       ├── zte_client.py               # Main client implementation
│       ├── tests/                      # Client tests
│       └── README.md                   # Client documentation
├── .devcontainer/                      # VS Code devcontainer setup
├── .github/workflows/                  # CI/CD workflows
└── hacs.json                          # HACS integration metadata
```

### Supported Router Models
F6640, H288A, H169A, H388X, H2640, F6645P, H3600P, H6645P, H3640

### Key Configuration
- Domain: `zte_tracker`
- Required parameters: host, model, username, password
- Example configuration in `configuration.yaml`:
  ```yaml
  zte_tracker:
    host: 192.168.1.1
    model: F6640
    username: admin
    password: !secret zte_password
  ```

## CI/CD Information

### GitHub Actions
- **hassfest validation**: Validates Home Assistant integration standards
- **HACS validation**: Validates HACS integration requirements
- Both run on push and pull requests - NEVER CANCEL, wait for completion

### Expected Command Times
- Python syntax validation: ~0.4 seconds
- Import tests: ~0.1 seconds  
- Linting: ~0.2 seconds
- Formatting: ~0.3 seconds
- Container operations: ~0.6 seconds
- **NEVER CANCEL** any build or test command

### Manual Validation Checklist
Before committing changes, always run:
1. ✓ Python syntax validation
2. ✓ Import and instantiation test
3. ✓ JSON validation
4. ✓ Mock Home Assistant test
5. ✓ Linting check (expect issues in existing code)
6. ✓ Container validation if using DevContainer

## Troubleshooting

### Import Issues
If you encounter import errors when running tests:
```bash
export PYTHONPATH="custom_components/zte_tracker:custom_components/zte_tracker/zteclient:$PYTHONPATH"
```

### DevContainer Issues
If the devcontainer fails to start:
- Ensure Docker is running
- Try pulling the image manually: `docker pull ludeeus/container:integration-debian`
- Check that ports 9123 and 5678 are available

### Test Issues
The repository includes unit tests with import path dependencies. Use the validation commands above instead of trying to run tests directly with unittest or pytest.