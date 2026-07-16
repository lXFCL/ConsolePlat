# ConsolePlat Versioned Runtime and Incremental Update Design

> Date: 2026-07-16
> Status: Design agreed; implementation pending
> Decision record: `docs/adr/0001-versioned-application-runtime.md`

## 1. Goal

Replace the current whole-package GitHub download experience with a trusted incremental update system that:

- downloads only changed release content when a supported local manifest is available;
- never modifies a running application runtime in place;
- blocks installation while ConsolePlat-managed integration work is active;
- switches to a new application version and reloads automatically after explicit confirmation;
- rolls back when the new version cannot complete startup initialization;
- preserves one shared configuration and business-data location across versions;
- keeps a complete release package as a manual recovery option.

The first migration from the existing PyInstaller layout is necessarily a full architecture migration. Incremental delivery starts after that migration.

## 2. Product Boundaries

### 2.1 Installation is blocked by managed work

An active integration task is a monitor collection, local generation, AI edit, publish, putaway, application/compliance task, or managed child process registered by ConsolePlat and not yet complete. Unrelated Chrome, Excel, and other desktop applications do not block installation.

Checking and downloading may continue while tasks run. Assembly, pointer switching, and restart require an exclusive update lock. Acquiring that lock prevents new integration tasks from starting. Existing tasks are listed to the user and are not force-stopped.

### 2.2 Explicit installation

The user explicitly starts download/update and later confirms `立即重启更新`. Normal close, Windows shutdown, logout, or application crash never installs a prepared update. A prepared version remains available across sessions.

### 2.3 Packaged releases only

Automatic installation applies only to packaged Windows releases. Source checkouts can check releases and open the official Release page, but the updater never edits a Git worktree or runs `git pull`.

### 2.4 Stable channel only

The first implementation consumes stable GitHub Releases only and ignores draft and prerelease releases. Automatic checks run at most once per local calendar day; manual checks remain unrestricted. Automatic download is disabled by default.

## 3. Installation Layout

```text
ConsolePlat/
  ConsolePlat.exe
  launcher-runtime/
  updater/
    ConsolePlatUpdater.exe
    BootstrapUpdater.exe
  app/
    versions/
      2.0.0/
        ConsolePlatApp.exe
        _internal/
        modules/
        resources/
        app-manifest.json
    current.json
  data/
    config/
    credentials/
    browser-profiles/
    tasks/
    logs/
    downloads/
    outputs/
    putaway/
    galleries/
    models/
    updates/
      cache/
      staging/
```

`ConsolePlat.exe` is a stable Rust launcher. Each application version is a complete Python/PyQt runtime with its required dependencies. Installed version directories become read-only. Runtime code must not write business state beside its own source.

All persistent configuration and business data use the adjacent `data/` root. The updater never owns, replaces, or removes this directory. Credentials retain Windows DPAPI protection. An unwritable installation disables automatic update without requesting elevation.

## 4. Stable Components

The Rust Cargo workspace contains three narrowly scoped components:

- `ConsolePlat.exe`: per-installation single-instance coordination, current-version selection, application launch, health observation, and rollback.
- `ConsolePlatUpdater.exe`: release discovery, signed-manifest verification, resumable download, staging, validation, ready-state management, and transactional pointer switching.
- `BootstrapUpdater.exe`: low-frequency replacement of launcher/updater components after their processes exit.

The components communicate with the Python application through versioned JSON files, command-line arguments, exit status, and startup-health records. They do not share an FFI interface.

Expected Rust dependencies are limited to serialization, SHA-256, Ed25519, HTTPS via rustls, ZIP handling, locking, and focused Windows APIs. `Cargo.lock` and a fixed stable toolchain are committed.

## 5. Release Protocol

### 5.1 Assets

A production Release contains:

```text
app-manifest-v2.0.1.json
app-manifest-v2.0.1.sig
app-chunk-<content-hash>.zip
ConsolePlat-v2.0.1-full.zip
```

The signed manifest declares at least:

- manifest and protocol versions;
- source compatibility and target application version;
- Release tag, commit SHA, workflow run, and build time;
- minimum launcher/updater versions;
- every managed path, byte size, SHA-256, and content chunk;
- managed files removed by the target version;
- signing `key_id`.

Paths must be relative, canonical, and constrained to the target version directory. Absolute paths, parent traversal, alternate data streams, links/reparse points, and duplicate normalized paths are rejected.

### 5.2 Trust

Ed25519 verification is mandatory for automatic installation. Production launchers contain public keys only. Production private keys live in protected GitHub Actions secrets or equivalent protected signing infrastructure and never enter Git or Release assets.

Official online assets are accepted only through an allowlist of GitHub API and asset domains. A configured HTTP proxy may transport requests, but redirects outside the allowlist are rejected. Offline imports pass the same signature, version, path, hash, lock, health, and rollback checks.

Authenticode signing and trusted timestamping of the three stable executables is recommended before broad public release. It complements but does not replace Ed25519 manifest verification.

### 5.3 CI ownership

Automatically installable production assets are built and signed only by GitHub Actions from an immutable version tag matching the application version. Tests and package validation run before signing. A published version is never mutated in place; fixes use a new tag/version. Local builds use a test key that production launchers do not trust.

## 6. Incremental Assembly

When the installed current manifest is supported, the updater compares target hashes with current managed files:

1. Copy unchanged managed files into `data/updates/staging/<version>`.
2. Download only content chunks containing changed or new files.
3. Extract through validated relative paths into staging.
4. Apply target-manifest ownership, including omitted/deleted managed files by simply not copying them.
5. Verify every target file against size and SHA-256.
6. Move the complete staging directory into `app/versions/<version>`.
7. Mark the version `ready`; do not switch yet.

The old version directory is never modified. If the local manifest is missing, unsupported, or too old, the UI offers the complete signed package instead of chaining historical deltas.

Downloads use resumable `.part` files under `data/updates/cache`. Complete verified chunks survive cancellation and restart. Before downloading, required space includes cache, staging, target runtime, and a safety margin. The previous healthy version is never deleted to make an update fit.

Signature, hash, or archive-path failures invalidate the affected content and staging state. They do not proceed to installation.

## 7. Switch, Health, and Rollback

On `立即重启更新`:

1. Acquire the update lock after confirming no blocking activity.
2. Refuse all new integration-task registrations.
3. Persist a switch transaction.
4. Exit the Python application.
5. Atomically replace `app/current.json` using a flushed temporary file in the same directory.
6. Launch the target runtime with a one-time startup token.
7. Wait up to 60 seconds for a matching health confirmation.

The application writes `data/runtime/startup-health.json` only after configuration migration, main-window creation, and core page registration succeed. A premature exit, timeout, wrong token, or wrong version causes the launcher to restore the previous healthy pointer and relaunch it.

Only the update's first startup is rollback-sensitive. A later business-time crash does not automatically change versions.

Pointer switching becomes non-cancellable after transaction commit starts. Before that boundary, checking, downloading, assembly, and verification can be cancelled. Transaction records allow recovery after power loss: an uncommitted switch keeps the old healthy pointer; a committed complete switch resumes health observation; inconsistent state returns to the last healthy pointer.

## 8. Data and Configuration

`data/config/settings.json` has an independent `schema_version`. Migration rules:

- save an application- and schema-labelled snapshot before migration;
- preserve existing user values and add defaults only for absent fields;
- retain deprecated fields for at least two application versions where practical;
- write through a temporary file and atomic replacement;
- fail startup and roll back the application pointer when migration fails.

The previous healthy application declares its highest supported configuration schema. A rollback uses current shared configuration when compatible. Incompatible rollback requires a tested downgrade migration; otherwise the UI explains that restoring an older snapshot may lose newer setting changes and requires explicit confirmation. Business data is never rolled back with configuration.

Task records, databases, and other persisted models each require their own schema and migration policy; they do not reuse the settings schema number.

## 9. Activity Registry

All blocking work registers with a shared `ActivityRegistry` on start and unregisters on completion. Records contain an activity id, task kind, page, user-facing title, start time, optional managed PID, and `blocks_update` flag.

The registry is the update system's only authority for managed activity. Legacy reflection over page fields such as `current_task`, `process`, or `QThread.isRunning()` is migrated to explicit registration. On abnormal restart, stale records are reconciled against process identity and lifecycle evidence so they cannot permanently block updates.

The update download itself does not block installation. Assembly/switch takes the exclusive update lock. Browser processes may remain non-blocking when no registered automation task is using them.

## 10. Retention and Diagnostics

The current healthy and previous healthy versions are protected. Older healthy versions are removed only after a later version passes health confirmation. The previous version is retained for at least seven days and until a subsequent successful update needs the protected slot. Failed versions keep diagnostic metadata; large runtime content may be removed after confirmation.

Structured JSONL launcher/update logs are retained locally for 30 days by default. They record versions, release identity, signature/hash outcomes, chunk byte counts, retries, migration schema transitions, switch stages, health, rollback, and blocking activity labels. They omit credentials, cookies, tokens, configuration values, task inputs, product data, and sensitive profile details. Diagnostic upload never occurs automatically.

## 11. Legacy Migration

The existing release cannot become the stable-launcher architecture through an ordinary application delta. A one-time architecture migration package will:

1. Confirm no active integration task and exit the legacy program.
2. Inventory and back up the existing installation and known persistent data.
3. Install the stable Rust components and first complete versioned runtime.
4. Move or map configuration, task history, logs, downloads, outputs, Putaway data, profiles, galleries, and models into the shared data layout without duplicating large directories where possible.
5. Retain the legacy installation as a recovery path.
6. Start the new runtime and require the normal health confirmation.
7. Offer legacy cleanup only after successful validation and an additional retention period.

Migration failure restores the legacy entry point. The first migration package is expected to be close to a complete download; later releases receive incremental benefits.

## 12. Delivery Phases

### Phase 1: Protocol foundation

- Define schemas and fixtures for manifests, signatures, transactions, pointers, activity records, and health records.
- Add deterministic manifest/chunk build tooling and Ed25519 test signing.
- Add malicious-path, corrupted-content, unsupported-protocol, and deterministic-output tests.
- Keep the current download-only update UI unchanged.

### Phase 2: Stable launcher and shared data

- Add the Rust workspace, per-installation single instance, pointer selection, health observation, and rollback.
- Package current Python/PyQt code as a complete external application runtime.
- Introduce shared data-root resolution and configuration migration.
- Validate all four integrated modules and preserve their standalone fallback path.

### Phase 3: Incremental updater

- Add official-source release discovery, resumable chunks, cache, staging, disk checks, ready state, update lock, and activity registry integration.
- Add stable-component bootstrap update protocol.
- Build GitHub Actions test-key publishing before enabling production keys.
- Test interruption, cancellation, power-loss transactions, disk exhaustion, running tasks, invalid signatures, invalid paths, and rollback.

### Phase 4: Migration release

- Produce and test the one-time migration package on a small set of installations.
- Publish the stable signed Release only after migration and recovery tests pass.
- Retain complete-package download as manual recovery.

## 13. Acceptance Criteria

- A business-code-only release downloads only changed content chunks and assembles a complete isolated target runtime.
- A dependency change can download larger chunks without corrupting or modifying the current runtime.
- Active registered tasks prevent switch/restart and are listed; unrelated processes do not block it.
- Acquiring the update lock prevents a new task from starting.
- Signature, path, hash, space, or protocol failures cannot change `current.json`.
- A healthy target confirms within 60 seconds and becomes current.
- A target that exits, times out, or reports the wrong token automatically returns to the previous healthy version.
- Shared settings and business data survive update and rollback according to schema compatibility rules.
- Normal close and OS shutdown do not install a prepared update.
- Interrupted pointer switching recovers to a complete healthy state.
- Source-mode execution never modifies the Git worktree.
- Production stable components reject locally test-signed assets.

## 14. Known Risks

- Migrating legacy relative-path writes to a shared data root requires code-level inventory across all integrated modules.
- Complete version runtimes may consume significant disk space even when network delivery is incremental.
- GitHub Release chunk count and size need measurement; the initial 20-50 MB target is a tuning range, not a fixed protocol constant.
- Windows antivirus may hold newly created files and delay atomic moves or health startup; retry and diagnostic behavior must be tested on real packaged builds.
- Authenticode certificate acquisition and protected CI signing remain operational prerequisites for a polished public distribution.
