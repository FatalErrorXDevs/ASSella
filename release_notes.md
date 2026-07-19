# Release Notes - ASSella v2.2.4-alpha4

### Updater Bug Fixes

* **Fixed updater path resolution:** Added a robust fallback to check and locate the default packaged AppImage path when the APPIMAGE environment variable contains an invalid or wrapper-defined value (like "1"), preventing the updater tool from failing with exit code 1.
