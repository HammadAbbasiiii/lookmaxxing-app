import SwiftUI

@main
struct LookMaxxApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            Group {
                if appState.isAuthenticated {
                    MainTabView()
                        .environmentObject(appState)
                        .transition(.opacity)
                        .animation(LXAnimation.fadeIn, value: appState.isAuthenticated)
                } else {
                    OnboardingView()
                        .environmentObject(appState)
                        .transition(.opacity)
                        .animation(LXAnimation.fadeIn, value: appState.isAuthenticated)
                }
            }
            .preferredColorScheme(.dark)
            .onAppear { loadCachedSession() }
        }
    }

    private func loadCachedSession() {
        appState.restoreFromCache()
    }
}

// MARK: - Main Tab Navigation ----------------------------------------------

struct MainTabView: View {
    var body: some View {
        TabView {
            DashboardView()
                .tabItem { Label("Home", systemImage: "house.fill") }

            PlanView()
                .tabItem { Label("Progress", systemImage: "chart.line.uptrend.xyaxis") }

            ExploreView()
                .tabItem { Label("Explore", systemImage: "magnifyingglass") }

            ProfileView()
                .tabItem { Label("Profile", systemImage: "person.fill") }
        }
        .accentColor(LXColor.gold)
    }
}