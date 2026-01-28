# Release Notes
## v2.0.13
### Added
- Option to enable/disable Wan and router details scans. Avoid extra load and warnings on unsupported models. [#52](https://github.com/juacas/zte_tracker/issues/52) reported by @Ices-Eyes (help needed for proper support for H2640 and H6645P V2).
### Fixed
- "Add new devices" switch not using known devices not in cache.
- Ensure logout from de router when pausing scanning.
- Fix device removal service to also remove orphaned devices without entities.

## v2.0.12
### Added
- Reboot button for easy router reboot from Home Assistant UI.
- Reboot action working for F6640 and similar models.

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