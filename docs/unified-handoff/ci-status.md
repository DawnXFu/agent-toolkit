# CI Validation Target

The pull request is expected to pass:

- Python compilation on all supported jobs.
- Unit and CLI tests on Ubuntu with Python 3.9, 3.10, 3.11, 3.12, and 3.13.
- Unit and CLI tests on Windows with Python 3.9 and 3.13.
- Unit and CLI tests on macOS with Python 3.9 and 3.13.
- Agent Skill document contract checks.
- Bootstrap-asset rejection checks.

This file records the intended validation matrix; GitHub Actions remains the authoritative result.
