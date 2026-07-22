# Changelog

## 2026-07-22

- Removed all mock files and production mock logic identified in the repository audit.
- Deleted the unused `app/src/services/aiFinanceService.js` mock service.
- Removed the banking OAuth demo consent fallback; unconfigured providers now fail explicitly instead of generating demo callbacks.
- Updated frontend runtime documentation to require persisted API-backed data in production paths.

Legitimate automated tests and dependency-owned mock utilities remain because they are required for verification and are not shipped as production behavior.
