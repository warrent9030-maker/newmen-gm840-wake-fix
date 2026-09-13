# Changelog

## 0.1.0 - experimental first release

- Early matrix capture during wireless wake, with pending snapshot retention.
- Optional Fn+B relative battery gauge on number keys 1..0.
- Fingerprint-checked offline patcher; owner configuration retained.
- Windows helper with two matching backups, application-only write and exact
  readback verification. Preparation is the default; flashing requires `-Flash`.
- Recovery instructions, annotated overlay assembler and synthetic unit tests.

Validated on one GM840. Wake-only passed short and six-minute physical typing
trials; the battery addition's display and release restoration were confirmed.
See [testing details](docs/testing.md) for the separate revision results.
