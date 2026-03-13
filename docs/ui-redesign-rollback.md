# UI Redesign Rollback Guide (Clean Fintech)

This redesign is guarded by a feature flag and centralized theme tokens. Use the steps below depending on how much you want to roll back.

## A) Full rollback (git, if available)
If the project is under git and you want a complete revert of all redesign changes:

```bash
git restore --source=HEAD~1 -- app/src/main/java/com/gapkassa/ui
git restore --source=HEAD~1 -- app/src/main/res/values/strings.xml
git restore --source=HEAD~1 -- app/src/main/res/values-uz/strings.xml
git restore --source=HEAD~1 -- docs/ui-redesign-log.md
git restore --source=HEAD~1 -- docs/ui-redesign-rollback.md
```

Adjust the commit reference (`HEAD~1`) to the last known good state in your history.

## B) Roll back only the Clean Fintech theme
Keep layout changes but switch the design system off:

1. Open `app/src/main/java/com/gapkassa/ui/theme/UiConfig.kt`
2. Set:
   ```kotlin
   useCleanFintechRedesign = false
   ```
3. Rebuild the app.

This will restore legacy colors/typography/shapes while keeping the current layouts.

## C) Roll back only navigation/layout changes
Restore only screen and UI component files from a backup or version control.
Key files touched by the redesign include:

- `app/src/main/java/com/gapkassa/ui/screens/AuthScreen.kt`
- `app/src/main/java/com/gapkassa/ui/screens/RegisterScreen.kt`
- `app/src/main/java/com/gapkassa/ui/screens/RoomsScreen.kt`
- `app/src/main/java/com/gapkassa/ui/screens/RoomScreen.kt`
- `app/src/main/java/com/gapkassa/ui/screens/CalendarScreen.kt`
- `app/src/main/java/com/gapkassa/ui/screens/StatsScreen.kt`
- `app/src/main/java/com/gapkassa/ui/screens/PaymentDetailScreen.kt`
- `app/src/main/java/com/gapkassa/ui/screens/ProfileScreen.kt`
- `app/src/main/java/com/gapkassa/ui/screens/CreateRoomScreen.kt`
- `app/src/main/java/com/gapkassa/ui/components/*`
- `app/src/main/java/com/gapkassa/ui/theme/*`

If you do not use git, restore these files from your own backup copy.

## D) Disable redesign via feature flag
This is the fastest safe toggle without touching layouts:

1. Set `useCleanFintechRedesign = false` in `UiConfig.kt`.
2. Rebuild.

This keeps the new screens but uses legacy colors/typography/shapes.
