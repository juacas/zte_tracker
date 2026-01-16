# Release Notes
## v2.0.11
- Support for F6600P router model. [#53](https://github.com/juacas/zte_tracker/issues/53) thanks @lebdim
- Added 4096 bit private key for F6600P.
- Fix reboot action. Tested on F6600P. Not working for F6640. Testing help needed. [#53](https://github.com/juacas/zte_tracker/issues/52)

## v2.0.9
### Fixed
- Parse integer values for router details and WAN attributes where applicable to ensure correct data types.
- Tracked Devices correctly linked to tracker device. Devices shown in "Connected Devices" section.

## v2.0.8
### Fixed
- Corrected WAN status data tag for ZTE H388X model. The previous tag caused issues in retrieving WAN status information. Thanks to @gradypark86 for reporting! [#44](https://github.com/juacas/zte_tracker/issues/44)

## v2.0.7

### Added

- Support for ZTE SR7410 (ZTE BE7200 Pro+) router model. Thanks to @gradypark86 for the contribution! [#42](https://github.com/juacas/zte_tracker/issues/42)