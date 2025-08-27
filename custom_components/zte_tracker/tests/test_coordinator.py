"""Test the ZTE Tracker coordinator."""
import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta

from custom_components.zte_tracker.coordinator import ZteDataCoordinator, SLOW_UPDATE_INTERVAL, FAST_UPDATE_INTERVAL


def test_coordinator_pause_resume(hass, mock_config_entry, mock_zte_client):
    """Test pause and resume functionality."""
    with patch("custom_components.zte_tracker.coordinator.zteClient", return_value=mock_zte_client):
        coordinator = ZteDataCoordinator(hass, mock_config_entry)
        
        assert not coordinator.paused
        
        coordinator.pause_scanning()
        assert coordinator.paused
        
        coordinator.resume_scanning()
        assert not coordinator.paused


def test_coordinator_caching(hass, mock_config_entry, mock_zte_client):
    """Test device caching functionality."""
    with patch("custom_components.zte_tracker.coordinator.zteClient", return_value=mock_zte_client):
        coordinator = ZteDataCoordinator(hass, mock_config_entry)
        
        # Test device merging with cache
        devices = [
            {
                "HostName": "Phone",
                "IPAddress": "192.168.1.100",
                "MACAddress": "00:11:22:33:44:55",
                "Active": True,
                "IconType": "smartphone",
                "NetworkType": "WLAN",
            }
        ]
        
        processed = coordinator._merge_device_data(devices)
        
        # Should have the device in processed data
        assert "00:11:22:33:44:55" in processed
        assert processed["00:11:22:33:44:55"]["name"] == "Phone"
        assert processed["00:11:22:33:44:55"]["active"] is True
        
        # Now simulate device going offline
        devices_offline = []
        processed_offline = coordinator._merge_device_data(devices_offline)
        
        # Device should still be in cache but marked inactive
        assert "00:11:22:33:44:55" in processed_offline
        assert processed_offline["00:11:22:33:44:55"]["active"] is False
        assert processed_offline["00:11:22:33:44:55"]["name"] == "Phone"  # Name preserved


def test_coordinator_interval_adjustment(hass, mock_config_entry, mock_zte_client):
    """Test automatic interval adjustment based on device stability."""
    with patch("custom_components.zte_tracker.coordinator.zteClient", return_value=mock_zte_client):
        coordinator = ZteDataCoordinator(hass, mock_config_entry)
        
        # Start with default interval
        assert coordinator.update_interval.total_seconds() == 60
        
        # Test stable device count increases interval (need > 5, so 7 times)
        for i in range(7):  
            coordinator._adjust_update_interval(5)
        
        # Should have switched to slow interval after > 5 stable iterations
        assert coordinator.update_interval == SLOW_UPDATE_INTERVAL
        
        # Test changing device count resets to fast interval
        coordinator._adjust_update_interval(3)  # Different count
        assert coordinator.update_interval == FAST_UPDATE_INTERVAL