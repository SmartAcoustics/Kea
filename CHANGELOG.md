# Changelog
All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.14.0 - 2026-09-04

### Removed

- Removed the clock from the `axis_connector` becuase it isn't used.

## 0.13.2 - 2026-08-18

### Added

- Added an `axis_ramp_driver` test util.

## 0.13.1 - 2026-08-12

### Changed

- Refactored the `ethernet_framer` tests to provide a tool for higher level tests.

## 0.13.0 - 2026-07-22

### Changed

- Modified the `kea/hdl/signal_handling/asynchronous/_signal_slicer` and `kea/hdl/signal_handling/synchronous/_synchronous_signal_slicer` so it uses the bitwidth of `signal_out` as the slice bitwidth rather than taking `slice_bitwidth` as an argument. The behaviour of the block hasn't changed (it used to require `slice_bitwidth` equalled the bitwidth of `signal_out`.
    - Updated all instances of the `signal_slicer` and `synchronous_signal_slicer` in kea.

### Added

- Added an `axi_stream_chunker`.
- Added an `ethernet_framer`.
- Added an `ethernet_monitor`.
- Added an asynchronous `left_shift_block`.

## 0.12.1 - 2026-04-29

### Changed

- Signal assigner updates
    - Added an deprecation warning to the `signal_assiger` in `kea/hdl/signal_handling/asynchronous`.
    - Added an deprecation warning to the `synchronous_signal_assiger` in `kea/hdl/signal_handling/synchronous`.
    - Replaced the deprecated blocks.
    - These changes do not affect behaviour.

## 0.12.0 - 2026-04-17

### Changed

- Updated the register pipeline (`kea/hdlregisters/register_pipeline`) to take boolean signals as well as `intbv` signals.

## 0.11.0 - 2026-03-17

### Changed

- Renamed `kea/hdl/axi/axi_stream_utils/axis_utils.py` to `kea/hdl/axi/axi_stream_utils/axis_interface_checks.py`.
- Removed some unused imports.
- Moved the AXI imports in `/kea/testing/myhdl/cosimulation.py` to solve a circular dependency.

### Added

- Added a asynchronous `sig_assigner` and `signed_sig_assigner`.
- Added a synchronous `sync_sig_assigner`, `sync_left_shift` and `sync_sig_assigner_with_reset`.
- Added a `check_bool_or_intbv_signal` to the interface checks.

## 0.10.0 - 2026-02-27

### Changed

- Added a `signal_out_valid` signal to `kea.hdl.signal_handling.synchronous.synchronous_saturating_rounding_slicer`.

### Added

- Added interface checks so blocks can check ports are correct.

## 0.9.3 - 2026-01-21

### Changed

- Added `xvlog.pb` to `.gitignore`. Newer versions of Vivado output an `xvlog.pb` but we don't want it in version control.

## 0.9.2 - 2026-01-13

### Fixed

- Fixed `kea/xilinx/vivado_utils/cosimulation.py` so it is compatible with Vivado 2025.2.

## 0.9.1 - 2026-01-07

### Fixed

- Fixed a syntax warning in `kea.testing.myhdl.cosimulation`.

## 0.9.0 - 2025-12-19

The changes here document all the changes since version 0.8.0.

### Changed

- Updated the python requirement to compatible with 3.12.3.
    - Fixed all deprecation warnings.
- Updated MyHDL to the latest.
- Updated all packages.

### Added

- Added setuptools as a dependency because they are no longer included by default in venvs.
