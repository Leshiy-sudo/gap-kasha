# UI Redesign Log (Clean Fintech)

## Stage 1 — Design Tokens & Theme Structure
- Added `UiConfig.useCleanFintechRedesign` feature flag.
- Added centralized spacing & radius tokens.
- Added Clean Fintech color system (light/dark) with Material3 mapping.
- Added Fintech typography scale and shapes.
- Preserved legacy theme palettes for safe rollback.

## Stage 2 — Reusable Components (Foundations)
- Upgraded primary/secondary/tertiary/destructive buttons with consistent sizes and radii.
- Upgraded nav button styling to use new tokens.
- Enhanced input field component (colors, password toggle, supporting text, icons).
- Added base card component and status chip.
- Added centralized app bar component.

## Stage 3 — Auth & Registration
- Redesigned login container with subtitle and inline error banner.
- Registration form grouped into sections with scrollable layout.
- App bars updated with back/home icons; removed bulky bottom navigation.

## Stage 4 — Home & Room List
- Home app bar actions for theme/language/profile.
- Room cards now show amount, payment day, members, and cycle chips.
- FAB updated to Clean Fintech radius.

## Stage 5 — Room Details & Payments
- Room summary chips and Calendar/Stats quick actions added.
- Payment cards show status chip and conditional actions.
- Navigation moved to app bar actions.

## Stage 6 — Calendar & Statistics
- Calendar header with icon navigation and today highlight.
- Calendar legend chips and cleaner grid cells.
- Stats screen redesigned into metric cards with discipline progress.

## Stage 7 — Profile & Create Room
- Profile screen grouped sections and change-photo dialog.
- Create room form reorganized with Clean Fintech layout and validation.

## Stage 8 — Rollback Documentation
- Added rollback guide with feature-flag and file-level restore steps.
