# Onboarding & Dashboard UI Fixes

## Summary

Fixed the broken onboarding "skip" flow and added a proper empty state to the
Dashboard. The app now builds successfully (`BUILD SUCCEEDED`) for iOS 16.0+.

## Changes

### 1. Onboarding — "I'll do this later"
- **Before:** The skip button had no action, so a logged-out user could not
  proceed past onboarding.
- **After:** Tapping "I'll do this later" either enters the app (if already
  authenticated) or presents a Login sheet.

**File:** `Views/Onboarding/OnboardingView.swift`

### 2. Login / Sign-up sheet
- Added a new `LoginView` presented as a sheet from onboarding.
- Supports both login and sign-up with inline error display.
- Auto-dismisses when authentication succeeds.

**File:** `Views/Onboarding/LoginView.swift` (new)

### 3. Dashboard empty state
- Removed the red error text (which surfaced as "Please log in again").
- Added `EmptyDashboardView` shown when the user has no analysis data yet,
  inviting them to upload their first photo.
- Added a "Session Expired" alert for genuine auth errors.

**Files:**
- `Views/Main/DashboardView.swift`
- `Views/Main/EmptyDashboardView.swift` (new)

### 4. Design tokens (additive)
- `Utils/Colors.swift`: added `warmWhite`, `softGray`, `goldGlow`.
- `Utils/Fonts.swift`: added `lxHero`, `lxBodyBold`, `lxCaptionBold`,
  `lxButtonText` modifiers.

## Build

```
** BUILD SUCCEEDED **
```

The Xcode project was regenerated with `xcodegen generate` to register the two
new Swift files (`LoginView.swift` and `EmptyDashboardView.swift`), and the
project was switched to the full Xcode toolchain:

```
sudo xcode-select -s /Applications/Xcode.app