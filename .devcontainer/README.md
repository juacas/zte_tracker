# ZTE Tracker Development Container

This directory contains the configuration for developing the ZTE Tracker Home Assistant integration using Visual Studio Code and Docker with the official Home Assistant development container.

## Prerequisites

- [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
- [Docker](https://www.docker.com/) 
  - For Linux, macOS, or Windows 10 Pro/Enterprise/Education use the [current release version of Docker](https://docs.docker.com/install/)
  - Windows 10 Home requires [WSL 2](https://docs.microsoft.com/windows/wsl/wsl2-install) and the current Edge version of Docker Desktop
- [Visual Studio Code](https://code.visualstudio.com/)
- [Dev Containers Extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

## Getting Started

1. **Clone and Open**:
   - Fork the repository
   - Clone to your computer
   - Open the repository in VS Code

2. **Open in Dev Container**:
   - When prompted, click "Reopen in Container"
   - Or press `F1` and select "Dev Containers: Reopen in Container"
   - Wait for the container to build (first time takes longer)

3. **Start Development**:
   - Home Assistant will be available at `http://localhost:8123`
   - The debugger port is available on `5678`

## Development Features

### Enhanced Configuration
This devcontainer uses the official Home Assistant development image with:
- **Latest Home Assistant Core**: Always up-to-date development environment
- **Pre-configured Debugging**: Remote debugging ready with debugpy
- **Integrated Testing**: Pytest configuration for running tests
- **Code Quality Tools**: Black, isort, flake8 pre-configured

### VS Code Extensions
Automatically installed:
- **Python Tools**: Python, Pylance, Black formatter, isort, flake8
- **YAML Support**: YAML language support with Home Assistant schema validation
- **Development Tools**: GitHub integration, code coverage, test adapters
- **Formatting**: Prettier for JSON/YAML formatting

### Debug Configurations
Available in the Debug panel (F5):
- **Home Assistant**: Full HA instance with debugging enabled
- **Home Assistant (Skip Dependencies)**: Faster startup, skips pip install
- **Python: Test ZTE Tracker**: Run integration tests with debugging
- **Python: Run Tests**: Execute all tests with pytest
- **Python: Debug Current File**: Debug any Python file

### Development Tasks
Access via `Ctrl+Shift+P` → "Tasks: Run Task":
- **Run Home Assistant**: Start HA manually
- **Run Tests**: Execute the test suite
- **Lint with Black**: Format Python code
- **Sort Imports with isort**: Organize imports
- **Check with Flake8**: Code style validation
- **Format and Lint All**: Run all code quality tools

## Configuration Files

### devcontainer.json
- Uses official `ghcr.io/home-assistant/devcontainer:addons` image
- Configures ports: 8123 (Home Assistant), 5678 (Debugger)
- Sets up VS Code extensions and settings
- Enables privileged mode for full Docker access

### configuration.yaml
Home Assistant configuration for development:
```yaml
# Debug logging for ZTE Tracker
logger:
  logs:
    custom_components.zte_tracker: debug

# Remote debugging enabled
debugpy:
  start: true
  port: 5678

# Example ZTE Tracker configuration
zte_tracker:
  host: 192.168.1.1
  username: admin
  password: admin
  model: F6640
```

### VS Code Settings
- Python interpreter configured for container environment
- Auto-formatting with Black on save
- Import organization with isort
- YAML schema validation for Home Assistant
- Testing configured with pytest

## Testing Your Integration

### Unit Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_coordinator.py -v

# Run with coverage
python -m pytest tests/ --cov=custom_components.zte_tracker
```

### Integration Testing
1. Update `.devcontainer/configuration.yaml` with your router details
2. Start Home Assistant using the debug configuration
3. Check logs for integration loading and device discovery
4. Test config flow by adding the integration via UI

### Live Development
- Home Assistant automatically reloads when you modify the integration
- Use `ha core restart` in the terminal for full restart
- Check logs with `ha logs` command

## Advanced Features

### Remote Debugging
1. Set breakpoints in your Python code
2. Run "Home Assistant" debug configuration
3. Debugger automatically attaches when breakpoints hit
4. Full variable inspection and step-through debugging

### Code Quality Automation
All tools run automatically on save:
- **Black**: Code formatting
- **isort**: Import sorting  
- **Flake8**: Style checking
- **Pylance**: Type checking and intellisense

### Docker Integration
The container has access to Docker for:
- Testing containerized scenarios
- Building custom images
- Running additional services for testing

## Tips and Tricks

- **Terminal**: Use `Ctrl+Shift+`` ` to open integrated terminal
- **Reload Integration**: Use Developer Tools → YAML → Reload custom integrations
- **Check Config**: Use the "Check Configuration" task before testing
- **Port Forwarding**: Access Home Assistant at http://localhost:8123
- **File Sync**: All changes sync automatically between container and host

## Troubleshooting

### Container Issues
- **Build Fails**: Try "Dev Containers: Rebuild Container" from command palette
- **Slow Performance**: Ensure Docker has sufficient memory allocated (4GB+)
- **Port Conflicts**: Check if ports 8123 or 5678 are already in use

### Home Assistant Issues
- **Integration Not Loading**: Check `configuration.yaml` syntax and logs
- **Debugger Not Connecting**: Verify debugpy is enabled and port 5678 is open
- **Test Failures**: Ensure test environment variables are set correctly

### Development Issues
- **Import Errors**: Check PYTHONPATH includes custom_components directory
- **Linting Errors**: Run "Format and Lint All" task to fix style issues
- **Type Errors**: Enable type checking in Python settings

## Contributing

1. Make your changes in the development container
2. Run tests: `python -m pytest tests/ -v`
3. Format code: Use "Format and Lint All" task
4. Test integration manually in Home Assistant
5. Commit and push your changes
6. Create a pull request

For more information about Home Assistant development, see the [official developer documentation](https://developers.home-assistant.io/).
