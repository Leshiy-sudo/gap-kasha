# Gap Kassa Backlog (UI / UX / QA)

This backlog is structured by **Agency Agents** and includes clear acceptance criteria for each item.

## UI Designer (Visual System)
Source: `/Users/user/Documents/автоматизация/gap-kassa/tools/agency-agents/design/design-ui-designer.md`

1. **Unify action button system**
Status: Implemented — needs QA
Acceptance:
- All primary actions use consistent color tokens (green=save/paid, red=destructive, blue=navigation).
- Buttons have consistent corner radius and text contrast (AA).
- FAB is circular and light blue on Home screen.

2. **Card styling consistency in Room view**
Status: Implemented — needs QA
Acceptance:
- Default cards are neutral gray.
- Paid/Skipped cards are tinted (green/red) distinct from button colors.
- Spacing and typography remain consistent across all payment cards.

3. **Typography hierarchy on Home**
Status: Implemented — needs QA
Acceptance:
- Top bar title is “Главная страница / Bosh sahifa”.
- “Комнаты” appears below, smaller than the main title.
- No duplicate “Главная страница” label in list content.

## UX Architect (Flow + Structure)
Source: `/Users/user/Documents/автоматизация/gap-kassa/tools/agency-agents/design/design-ux-architect.md`

1. **Global Home/Back navigation pattern**
Status: Implemented — needs QA
Acceptance:
- All screens (except login) show Back/Home side‑by‑side blue buttons at the bottom.
- Login screen has no Home button or extra fields.

2. **Exit confirmation from Home**
Status: Implemented — needs QA
Acceptance:
- Back on Home triggers confirmation dialog.
- Confirm exits app, cancel dismisses dialog.

3. **Post‑Create flow**
Status: Implemented — needs QA
Acceptance:
- After creating a room, user returns to Home room list.

4. **Calendar UX**
Status: Implemented — needs QA
Acceptance:
- Month navigation works (prev/next).
- Month title is localized (RU/UZ).
- Day cells show initials only; tapping a date shows receiver names.

## Testing Reality Checker (QA)
Source: `/Users/user/Documents/автоматизация/gap-kassa/tools/agency-agents/testing/testing-reality-checker.md`

1. **Localization verification**
Status: Needs QA
Checks:
- Toggle RU/UZ and confirm full UI updates (including month names).
- Validate weekday labels change with locale.

2. **Auth validation evidence**
Status: Needs QA
Checks:
- Invalid login shows explicit error message.
- Registration validates required fields and optional surname/patronymic.

3. **Navigation regression**
Status: Needs QA
Checks:
- Back/Home buttons present on all screens except login.
- Home always returns to Rooms list.

4. **UI safety zone**
Status: Needs QA
Checks:
- Bottom controls never overlap system navigation bar.

---

If you want, I can mark items as DONE after running a full QA pass with screenshots.
