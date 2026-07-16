# ADR 0001: Versioned Application Runtime

## Status

Accepted

## Context

ConsolePlat currently ships as a PyInstaller onedir application whose Python application code is bundled into the executable. Updating from a GitHub Release therefore requires downloading a complete package and cannot safely replace files while the application is running.

The application also coordinates long-running integration tasks and stores configuration, credentials, browser profiles, task records, generated outputs, and other business data that must survive application upgrades and rollbacks.

## Decision

ConsolePlat will separate a stable launcher from versioned application content.

- The launcher reads an atomic current-version pointer and starts the selected application version.
- Each application version has an isolated, complete runtime containing its application code and required dependencies.
- Updates build and verify a new version directory before changing the current-version pointer.
- The current version and previous version are retained so a failed startup can roll back by switching the pointer.
- Application version directories are treated as read-only after installation.
- Persistent configuration and business data live in a shared `data/` directory beside the launcher and are never owned or removed by an application version.
- Configuration files carry a schema version. A new application version backs up and migrates configuration before use, preserving user values and only transforming structure or adding defaults.
- A configuration migration failure prevents the new version from starting and causes rollback to the previous version.
- Installation is blocked while ConsolePlat has active integration tasks or managed child processes. Unrelated desktop applications do not block installation.
- Automatic installation is supported only for packaged Windows releases. Source checkouts may check for releases but are not modified automatically.
- Automatic installation requires a digitally signed application manifest. The packaged launcher and updater contain only the public verification key; the private signing key remains outside the repository and GitHub Release assets.
- A manifest declares the source version, target version, managed file paths, sizes, SHA-256 hashes, removed files, and minimum launcher version. Missing, invalid, or unsupported signatures disable automatic installation and fall back to opening the official Release page.
- Update paths are constrained to the target version directory and validated against absolute paths and directory traversal before any file is written.
- The stable launcher and updater use a separate low-frequency bootstrap update path when their protocol or verification implementation must change.
- Blocking task state is provided by a shared activity registry rather than inferred from page-specific UI fields. Installing an update requires an exclusive update lock; while held, no new integration task may start.
- Existing blocking activities are shown to the user and are never force-stopped by the updater. Stale registry entries are reconciled against managed process state after an abnormal exit.
- Update chunks are cached outside application versions and may resume across application restarts. New versions are assembled in an isolated staging directory and become installable only after signature, archive-path, and complete manifest-hash validation.
- Disk-space checks include download cache, staging, the new version, and a safety margin. The previous healthy version is never deleted to make an otherwise unsafe update fit.
- The system retains the current healthy version and previous healthy version as protected rollback targets. Shared data is never part of version cleanup.
- Shared configuration carries an independent schema version and is snapshotted before migration. Migrations preserve existing user values and deprecated fields for a compatibility window.
- Rollback uses the current shared configuration when the previous application supports its schema. An incompatible rollback requires a tested downgrade migration or explicit user confirmation before restoring an older configuration snapshot; business data is not rolled back with configuration.
- The existing monolithic release migrates through a one-time architecture migration package. It preserves the legacy installation as a recovery path until the first versioned runtime passes its health check; subsequent releases use the normal incremental protocol.
- Update manifests use Ed25519 signatures and include a key identifier to support rotation. Production private keys are held in protected GitHub Actions secrets and never enter the repository or Release assets.
- Automatically installable production assets are built and signed only by GitHub Actions from an immutable version tag. Published assets for an existing version are never replaced in place; corrections require a new version.
- Local builds may use a test key for development, but production launchers do not trust test keys.
- This decision does not introduce a general business-plugin system. Each application runtime remains a complete application using the existing adapter boundaries; optional business-plugin APIs are deferred.
- Updates operate without administrator elevation and require the launcher, version, update-cache, and shared-data locations to be writable. An unwritable installation disables automatic installation and directs the user to move the complete directory.
- Each installation directory permits one launcher/application instance and one updater operation at a time. Separate installation directories remain independent and use separate shared data roots.
- The first release channel is stable only. Automatic checks ignore draft and prerelease assets and run at most once per local calendar day; explicit user checks remain available.
- Update checks and downloads may run while integration tasks are active, but assembly, version switching, and restart require the exclusive update lock and explicit user confirmation.
- Launcher and updater diagnostics are stored locally as structured logs with relative managed paths and release metadata. They omit credentials, configuration values, cookies, tokens, business inputs, and other sensitive data, are retained for 30 days by default, and are never uploaded without explicit user action.
- Online manifests, signatures, and chunks are accepted only from an allowlist of official GitHub domains. A configured HTTP proxy may transport those requests, but redirects to other origins are rejected and no third-party mirror is selected automatically.
- Offline update imports are supported only when they pass the same signature, version, path, hash, activity-lock, health-check, and rollback requirements as online assets.
- A fully assembled and verified version is marked ready but is not installed by normal application close, crash, logout, or shutdown. Switching requires the explicit restart-update command.
- Update work remains cancellable through download, staging, and validation. After the exclusive update lock is acquired and pointer commit begins, the short transactional switch is non-cancellable.
- Current-version pointer changes use a flushed temporary file and same-directory atomic replacement. Transaction records allow the launcher to select the last healthy pointer after interruption or power loss.
- Delivery is phased: first define and test the signed manifest and transaction protocol; then introduce the stable launcher, health reporting, shared data, and rollback; then add incremental chunk delivery, staging, activity locking, and GitHub Actions publishing; finally ship a one-time migration release from the legacy package layout.
- The existing complete-package download remains available as a manual recovery path after incremental updates are enabled.
- The stable launcher, updater, and bootstrap updater are implemented as a Rust Cargo workspace. The Python/PyQt application remains a separately packaged versioned runtime, and the two sides communicate through versioned JSON files, command-line arguments, process exit status, and startup health records rather than an in-process FFI boundary.
- Rust dependencies are intentionally narrow and locked with `Cargo.lock`; expected building blocks include `serde`, `serde_json`, `sha2`, `ed25519-dalek`, `reqwest` with rustls, `zip`, and focused Windows API bindings.
- The launcher has no embedded WebView or application UI framework. It provides only minimal native failure and recovery prompts; normal update interaction remains in the PyQt application.
- Manifests, transactions, activity records, and health records have independent schema versions. Cross-component messages also declare a protocol version. A component rejects unsupported newer security-sensitive protocols instead of ignoring them.
- Ed25519 remains the mandatory application-level trust mechanism. Authenticode signing of the stable Windows executables is a recommended public-release gate but does not block development phases; signing keys should use CI-compatible protected or hardware-backed storage and trusted timestamping.

## Consequences

- Routine application changes can be distributed as changed files instead of a complete release archive.
- Runtime dependency changes may still produce large update payloads because each version must remain internally consistent.
- Rollback remains reliable because a previous application version is not modified in place.
- Legacy modules that write beside their source files must be migrated or adapted to use the shared data root.
- The launcher and updater become separately maintained trusted components and may occasionally require their own update path.
- Release production requires protected signing-key management and deterministic manifest generation.
- Moving the installation to another computer may require credentials to be entered again because Windows DPAPI data is tied to the original Windows user context.
