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
                                Text(String((appState.currentUser?.username ?? "U").prefix(1).uppercased()))
                                    .font(.system(size: 32, weight: .bold))
                                    .foregroundColor(LXColor.gold)
                            }

                            Text(appState.currentUser?.username ?? "Maxxer")
                                .lxH2()
                                .foregroundColor(LXColor.white)

                            if let tier = appState.currentUser?.subscriptionTier {
                                Text(tier.rawValue.uppercased())
                                    .font(LXFont.caption())
                                    .foregroundColor(LXColor.gold)
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 4)
                                    .background(LXColor.gold.opacity(0.15))
                                    .cornerRadius(LXConstants.cornerRadius)
                            }
                        }
                        .padding(.top, 30)

                        // Stats
                        HStack(spacing: 16) {
                            StatCard(value: "\(appState.currentUser?.daysActive ?? 0)", label: "Days Active")
                            StatCard(value: "\(appState.currentUser?.longestStreak ?? 0)", label: "Best Streak")
                            StatCard(value: "\(appState.currentUser?.photosUploaded ?? 0)", label: "Uploads")
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
                            Button(action: {
                                appState.selectedTab = .plan
                            }) {
                                settingsRow(icon: "slider.horizontal.3", title: "My Plan")
                            }
                            Divider().background(LXColor.white.opacity(0.1))
                            NavigationLink {
                                ScoreHistoryView()
                            } label: {
                                settingsRow(icon: "chart.bar.fill", title: "Score History")
                            }
                            Divider().background(LXColor.white.opacity(0.1))
                            NavigationLink {
                                ProgressPhotosView()
                            } label: {
                                settingsRow(icon: "photo.on.rectangle", title: "Progress Photos")
                            }
                            Divider().background(LXColor.white.opacity(0.1))
                            NavigationLink {
                                SettingsView()
                            } label: {
                                settingsRow(icon: "gearshape.fill", title: "Settings")
                            }
                            Divider().background(LXColor.white.opacity(0.1))
                            NavigationLink {
                                HelpView()
                            } label: {
                                settingsRow(icon: "questionmark.circle", title: "Help & Support")
                            }
                        }
                        .background(LXColor.deepNavy)
                        .cornerRadius(LXConstants.cornerRadius)
                        .padding(.horizontal, LXConstants.standardPadding)

                        // Sign out
                        Button(action: { appState.signOut() }) {
                            Text("Sign Out")
                                .lxBody()
                                .foregroundColor(LXColor.red)
                                .frame(maxWidth: .infinity)
                                .frame(height: LXConstants.buttonHeight)
                                .background(LXColor.red.opacity(0.12))
                                .cornerRadius(LXConstants.cornerRadius)
                        }
                        .padding(.horizontal, LXConstants.standardPadding)

                        Spacer().frame(height: 40)
                    }
                }
            }
            .navigationTitle("Profile")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private func settingsRow(icon: String, title: String) -> some View {
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
        .contentShape(Rectangle())
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