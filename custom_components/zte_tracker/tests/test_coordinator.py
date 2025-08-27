"""Test the ZTE Tracker coordinator."""
import pytest
from unittest.mock import patch

from custom_components.zte_tracker.coordinator import ZteDataCoordinator


def test_coordinator_pause_resume(hass, mock_config_entry, mock_zte_client):
    """Test pause and resume functionality."""
    with patch("custom_components.zte_tracker.coordinator.zteClient", return_value=mock_zte_client):
        coordinator = ZteDataCoordinator(hass, mock_config_entry)
        
        assert not coordinator.paused
        
        coordinator.pause_scanning()
        assert coordinator.paused
        
        coordinator.resume_scanning()
        assert not coordinator.paused