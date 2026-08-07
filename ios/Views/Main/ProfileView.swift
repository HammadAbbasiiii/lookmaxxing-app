import SwiftUI

/// Screen 9 — Profile / Settings (fourth tab).
///
/// Psychology: Ownership.
/// Let users see their stats and feel informed about their progress.
struct ProfileView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        NavigationStack {
            ZStack {
                LXColor.black.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 24) {
                        // Avatar + name
                        VStack(spacing: 12) {
                            ZStack {
                                Circle()
                                    .fill(LXColor.deepNavy)
                                    .frame(width: 80, height: 80)
                                Text(String((appState.user?.username ?? "U").prefix(1).uppercased()))
                                    .font(.system(size: 32, weight: .bold))
                                    .foregroundColor(LXColor.gold)
                            }

                            Text(appState.user?.username ?? "Maxxer")
                                .lxH2()
                                .foregroundColor(LXColor.white)

                            if let tier = appState.user?.subscriptionTier {
                                Text(tier.rawValue.uppercased())
                                    .font(LXFont.caption())
                                    .foregroundColor(LXColor.gold)
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 4)
                                    .background(LXColor.gold.opacity(0.15))
                                    .cornerRadius(12)
                            }
                        }
                        .padding(.top, 30)

                        // Stats
                        HStack(spacing: 16) {
                            StatCard(value: "\(appState.user?.daysActive ?? 0)", label: "Days Active")
                            StatCard(value: "\(appState.user?.longestStreak ?? 0)", label: "Best Streak")
                            StatCard(value: "\(appState.user?.photosUploaded ?? 0)", label: "Uploads")
                        }
                        .padding(.horizontal, LXConstants.standardPadding)

                        // Current score
                        if let score = appState.currentScore {
                            VStack(spacing: 8) {
                                Text(String(format: "%.0f", score.overallScore))
                                    .font(.system(size: 48, weight: .bold, design: .rounded))
                                    .foregroundColor(LXColor.gold)
                                Text("Current Score")
                                    .lxCaption()
                                    .foregroundColor(LXColor.white.opacity(0.5))
                            }
                            .padding()
                            .frame(maxWidth: .infinity)
                            .background(LXColor.deepNavy)
                            .cornerRadius(LXConstants.cornerRadius)
                            .padding(.horizontal, LXConstants.standardPadding)
                        }

                        // Settings list
                        VStack(spacing: 0) {
                            settingsRow(icon: "slider.horizontal.3", title: "My Plan", action: {
                                // Switch to progress tab
                            })
                            Divider().background(LXColor.white.opacity(0.1))
                            settingsRow(icon: "chart.bar.fill", title: "Score History", action: {})
                            Divider().background(LXColor.white.opacity(0.1))
                            settingsRow(icon: "photo.on.rectangle", title: "Progress Photos", action: {})
                            Divider().background(LXColor.white.opacity(0.1))
                            settingsRow(icon: "gearshape.fill", title: "Settings", action: {})
                            Divider().background(LXColor.white.opacity(0.1))
                            settingsRow(icon: "questionmark.circle", title: "Help & Support", action: {})
                        }
                        .background(LXColor.deepNavy)
                        .cornerRadius(LXConstants.cornerRadius)
                        .padding(.horizontal, LXConstants.standardPadding)

                        // Sign out
                        Button(action: { appState.signOut() }) {
                            Text("Sign Out")
                                .lxBody()
                                .foregroundColor(LXColor.red)
                        }
                        .padding()

                        Spacer().frame(height: 40)
                    }
                }
            }
            .navigationTitle("Profile")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private func settingsRow(icon: String, title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .foregroundColor(LXColor.gold)
                    .frame(width: 24)
                Text(title)
                    .lxBody()
                    .foregroundColor(LXColor.white)
                Spacer()
                Image(systemName: "chevron.right")
                    .foregroundColor(LXColor.white.opacity(0.3))
            }
            .padding()
        }
    }
}

// MARK: - Stat card --------------------------------------------------------

struct StatCard: View {
    let value: String
    let label: String

    var body: some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.system(size: 24, weight: .bold, design: .rounded))
                .foregroundColor(LXColor.gold)
            Text(label)
                .lxCaption()
                .foregroundColor(LXColor.white.opacity(0.5))
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
        .background(LXColor.deepNavy)
        .cornerRadius(LXConstants.cornerRadius)
    }
}

// MARK: - Preview ----------------------------------------------------------

#Preview {
    ProfileView()
        .environmentObject(AppState())
}