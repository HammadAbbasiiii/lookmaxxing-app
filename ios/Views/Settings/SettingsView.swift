import SwiftUI

/// Dedicated Settings screen.
///
/// Consolidates account management, preferences, and sign-out into
/// a single place reachable from the Profile tab.
struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ZStack {
            LXColor.black.ignoresSafeArea()

            ScrollView {
                VStack(spacing: 24) {
                    // Account section
                    VStack(spacing: 0) {
                        settingsRow(icon: "person.crop.circle", title: "Account", detail: appState.currentUser?.email, action: {})
                        Divider().background(LXColor.white.opacity(0.1))
                        settingsRow(icon: "creditcard", title: "Subscription", detail: tierLabel, action: {})
                        Divider().background(LXColor.white.opacity(0.1))
                        settingsRow(icon: "star.fill", title: "Restore Purchases", detail: nil, action: {})
                    }
                    .background(LXColor.deepNavy)
                    .cornerRadius(LXConstants.cornerRadius)
                    .padding(.horizontal, LXConstants.standardPadding)
                    .padding(.top, 20)

                    // Preferences section
                    VStack(spacing: 0) {
                        settingsRow(icon: "bell.fill", title: "Notifications", detail: nil, action: {})
                        Divider().background(LXColor.white.opacity(0.1))
                        settingsRow(icon: "lock.fill", title: "Privacy", detail: nil, action: {})
                        Divider().background(LXColor.white.opacity(0.1))
                        settingsRow(icon: "questionmark.circle", title: "Help & Support", detail: nil, action: {})
                        Divider().background(LXColor.white.opacity(0.1))
                        settingsRow(icon: "doc.text.fill", title: "Terms & Conditions", detail: nil, action: {})
                    }
                    .background(LXColor.deepNavy)
                    .cornerRadius(LXConstants.cornerRadius)
                    .padding(.horizontal, LXConstants.standardPadding)

                    // Sign out
                    Button(action: { appState.signOut() }) {
                        HStack(spacing: 8) {
                            Image(systemName: "rectangle.portrait.and.arrow.right")
                            Text("Sign Out")
                        }
                        .lxBody()
                        .foregroundColor(LXColor.red)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(LXColor.deepNavy)
                        .cornerRadius(LXConstants.cornerRadius)
                    }
                    .padding(.horizontal, LXConstants.standardPadding)

                    Spacer().frame(height: 40)
                }
            }
        }
        .navigationTitle("Settings")
        .navigationBarTitleDisplayMode(.inline)
    }

    private var tierLabel: String {
        appState.currentUser?.subscriptionTier.rawValue.uppercased() ?? "FREE"
    }

    private func settingsRow(icon: String, title: String, detail: String?, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .foregroundColor(LXColor.gold)
                    .frame(width: 24)
                Text(title)
                    .lxBody()
                    .foregroundColor(LXColor.white)
                Spacer()
                if let detail {
                    Text(detail)
                        .lxCaption()
                        .foregroundColor(LXColor.white.opacity(0.5))
                }
                Image(systemName: "chevron.right")
                    .foregroundColor(LXColor.white.opacity(0.3))
            }
            .padding()
        }
    }
}

// MARK: - Preview ----------------------------------------------------------

#Preview {
    NavigationStack {
        SettingsView()
            .environmentObject(AppState())
    }
}