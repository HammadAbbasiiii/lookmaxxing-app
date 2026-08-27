import SwiftUI

@main
struct LookMaxxApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            Group {
                if appState.isAuthenticated {
                    if appState.shouldShowCamera {
                        // Fresh signup/login — show camera first for baseline photo
                        CameraFirstFlow()
                            .environmentObject(appState)
                            .transition(.opacity)
                    } else {
                        // Returning user — show main tabs
                        MainTabView()
                            .environmentObject(appState)
                            .transition(.opacity)
                    }
                } else {
                    OnboardingView()
                        .environmentObject(appState)
                        .transition(.opacity)
                }
            }
            .animation(.easeInOut(duration: 0.3), value: appState.isAuthenticated)
            .preferredColorScheme(.dark)
            .onAppear { loadCachedSession() }
        }
    }

    private func loadCachedSession() {
        appState.restoreFromCache()
    }
}

// MARK: - Camera-First Flow (post-signup) ------------------------------------

/// Full-screen camera flow shown immediately after a fresh signup/login.
/// The user takes their baseline photo before entering the main app.
struct CameraFirstFlow: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        NavigationStack {
            ZStack {
                LXColor.black.ignoresSafeArea()

                VStack(spacing: 32) {
                    Spacer()

                    Text("Take Your\nFirst Photo")
                        .lxH2()
                        .foregroundColor(LXColor.white)
                        .multilineTextAlignment(.center)

                    Text("This is your baseline photo.\nWe'll analyze it to create your\npersonalized 90-day plan.")
                        .lxBody()
                        .foregroundColor(LXColor.white.opacity(0.7))
                        .multilineTextAlignment(.center)

                    // Camera & gallery picker
                    CameraView()

                    Button("Skip for now") {
                        appState.shouldShowCamera = false
                    }
                    .lxCaption()
                    .foregroundColor(LXColor.white.opacity(0.4))

                    Spacer()
                }
                .padding()
            }
        }
    }
}

// MARK: - Main Tab Navigation ------------------------------------------------

struct MainTabView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        TabView(selection: $appState.selectedTab) {
            DashboardView()
                .tabItem { Label("Home", systemImage: "house.fill") }
                .tag(MainTab.home)

            PlanView()
                .tabItem { Label("Progress", systemImage: "chart.line.uptrend.xyaxis") }
                .tag(MainTab.plan)

            ExploreView()
                .tabItem { Label("Explore", systemImage: "magnifyingglass") }
                .tag(MainTab.explore)

            ProfileView()
                .tabItem { Label("Profile", systemImage: "person.fill") }
                .tag(MainTab.profile)
        }
        .accentColor(LXColor.gold)
    }
}
