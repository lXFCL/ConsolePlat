# ConsolePlat v2.0.1

This source release focuses on making the desktop shell calmer and safer during everyday use.

## User Experience

- The header now identifies the current page and explains its purpose without opening a tutorial.
- The application status now reports whether the workbench is ready or how many pages have active work.
- Navigation items expose concise tooltips, and running pages keep their visible badges up to date.
- Keyboard focus is clearer across buttons, inputs, lists, and tables in both light and dark themes.

## Task Safety

- Closing ConsolePlat while monitoring, child processes, downloads, or background image work is active now requires confirmation.
- Cancelling the close keeps the active work and monitor timer untouched.
- Confirming the close retains the existing page cleanup behavior, including monitor browser-page cleanup.

## Accuracy

- The stale `framework preview` label and README status were replaced with wording that reflects the workflows currently connected.

## Packaging

No new Windows package is included in this source change. The latest packaged download remains `v1.9.1` until a separate release build is produced and verified.
