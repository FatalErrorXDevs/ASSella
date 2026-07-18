# Release Notes - ASSella v2.2.4-rc2

### Bug Fixes & Stability

* **SLSsteam AppTokens Deduplication & Regex Fix:**
  - Fixed a regex pattern compilation bug in `add_app_token` where `{2}` inside a Python f-string incorrectly evaluated to the character `'2'` instead of the regex quantifier `{2}`. This caused duplicate AppToken configuration entries to be generated on every update check.
  - Implemented a robust deduplication logic that automatically cleans up and removes any existing duplicate AppToken entries in `config.yaml` upon token updates.
