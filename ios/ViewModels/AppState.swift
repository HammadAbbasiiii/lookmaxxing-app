import SwiftUI
import Combine

/// Shared, observable state for the entire app.
///
/// Injected as an `@EnvironmentObject` from `LookMaxxApp`.
/// All screens read/write from this single source of truth.
final class AppState: ObservableObject {
    // ── Auth ──────────────────────────────────────────────────
    @Published var user: User?
    @Published var isAuthenticated = false
    @Published var authError: String?

    // ── Photo flow ───────────────────────────────────────────
    @Published var currentPhoto: UIImage?
    @Published var isUploading = false
    @Published var uploadError: String?

    // ── Score ────────────────────────────────────────────────
    @Published var currentScore: Score?
    @Published var isPolling = false

    // ── Plan ─────────────────────────────────────────────────
    @Published var currentPlan: Plan?
    @Published var planLoading = false

    // ── Dashboard ────────────────────────────────────────────
    @Published var dashboard: DashboardData?
    @Published var dashboardLoading = false

    // ── Explore ──────────────────────────────────────────────
    @Published var exploreData: ExploreData?
    @Published var exploreLoading = false

    // ── Navigation ───────────────────────────────────────────
    @Published var currentTab: Tab = .home

    enum Tab { case home, progress, explore, profile }

    // MARK: - Cache restore -------------------------------------------------

    func restoreFromCache() {
        if let cachedUser = CacheService.shared.cachedUser() {
            user = cachedUser
            isAuthenticated = true
        }
        dashboard = CacheService.shared.cachedDashboard()
        currentScore = CacheService.shared.cachedScore()
        currentPlan = CacheService.shared.cachedPlan()
        exploreData = CacheService.shared.cachedExplore()
    }

    func signOut() {
        user = nil
        isAuthenticated = false
        currentPhoto = nil
        currentScore = nil
        currentPlan = nil
        dashboard = nil
        exploreData = nil
        CacheService.shared.clearAll()
        APIService.shared.accessToken = nil
    }
}