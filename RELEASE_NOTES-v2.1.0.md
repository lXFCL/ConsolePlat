# ConsolePlat v2.1.0

This source release refines the desktop workbench for calmer, more consistent daily use.

## Workbench Layout

- The sidebar uses smaller navigation symbols, steadier spacing, and a restrained brand mark.
- The page identity and application status now sit inside a stable header surface.
- The monitor banner is shorter and no longer repeats marketing copy above the actual work.
- Monitor refresh controls use separate status and action rows to remain readable at the minimum window size.

## Visual System

- Light and dark themes now style common inputs, combo boxes, checkboxes, progress bars, lists, logs, menus, tooltips, splitters, and horizontal scrollbars consistently.
- Generic buttons now have explicit normal, hover, pressed, and disabled states instead of falling back to Windows defaults.
- Focus feedback no longer changes one-pixel control borders into two-pixel borders, avoiding small layout shifts.
- Dark-theme scroll content and navigation labels now keep the intended background and contrast.

## Monitor Readability

- Metric markers are slimmer and use distinct blue, teal, amber, and red status colors.
- The monitor page exposes more operational content in the first viewport while keeping the existing image asset.

## Safety And Packaging

- No store publishing, inventory, address, JIT, upload, or other external-state workflow was changed or executed.
- No new Windows package is included. The latest packaged download remains `v1.9.1` until a separate release build is produced and verified.
