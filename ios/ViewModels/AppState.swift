import SwiftUI
import Combine

@MainActor
final class AppState: ObservableObject {
    // MARK: - Auth -----------------------------------------------------------
    @Published var isAuthenticated = false
    @Published var currentUser: User?
    @Published var shouldShowCamera = false   // True after signup/login — navigate to Camera
    @Published var showSessionExpired = false // Triggers the session-expired alert

    // MARK: - Photo & Analysis -----------------------------------------------
    @Published var currentPhoto: UIImage?
    @Published var currentPhotoID: String?
    @Published var currentScore: Score?
    @Published var isUploading = false
    @Published var isAnalyzing = false
    @Published var isPolling = false
    @Published var analysisIsTakingLonger = false
    @Published var uploadProgress: Double = 0
    @Published var uploadError: String?

    /// Set to true when the user cancels a long-running analysis poll.
    private var analysisCancelled = false

    // MARK: - Plan -----------------------------------------------------------
    @Published var currentPlan: Plan?

    // MARK: - Dashboard ------------------------------------------------------
    @Published var dashboardData: DashboardData?

    // MARK: - Explore --------------------------------------------------------
    @Published var exploreData: ExploreData?

    // MARK: - Navigation ------------------------------------------------------
    /// Currently selected tab in the main `TabView`. Used to route the user
    /// to the "Progress" (Plan) tab when they tap "View Your 90-Day Plan".
    @Published var selectedTab: MainTab = .home

    // MARK: - Loading States -------------------------------------------------
    @Published var authState: AppLoadingState = .idle
    @Published var dashboardState: AppLoadingState = .idle
    @Published var planState: AppLoadingState = .idle
    @Published var exploreState: AppLoadingState = .idle

    // MARK: - Initialization ------------------------------------------------

    init() {
        // Restore session synchronously from Keychain-backed token storage.
        // A guest session (no token) does not persist across launches.
        if let token = KeychainManager.getToken(forKey: KeychainManager.accessTokenKey),
           !KeychainManager.isTokenExpired(token) {
            isAuthenticated = true
        }
    }

    /// True when a valid, non-expired access token exists in the Keychain.
    /// Used by Onboarding to decide whether to enter the app or show auth.
    var hasValidToken: Bool {
        guard let token = KeychainManager.getToken(forKey: KeychainManager.accessTokenKey) else {
            return false
        }
        return !KeychainManager.isTokenExpired(token)
    }

    // MARK: - Authentication ------------------------------------------------

    func signUp(email: String, password: String, fullName: String? = nil) async -> Bool {
        authState = .loading
        do {
            let response = try await APIService.shared.signUp(email: email, password: password, fullName: fullName)
            // After signup, auto-login to get token
            _ = try await APIService.shared.login(email: email, password: password)
            currentUser = response.toUser()
            isAuthenticated = true
            shouldShowCamera = true
            authState = .loaded
            return true
        } catch {
            // Translate server errors into user-friendly messages
            authState = .error(friendlyMessage(for: error))
            return false
        }
    }

    func login(email: String, password: String) async -> Bool {
        authState = .loading
        do {
            _ = try await APIService.shared.login(email: email, password: password)
            // Fetch user profile after login
            do {
                let user = try await APIService.shared.getCurrentUser()
                currentUser = user
            } catch {
                // If /me fails, construct minimal user from token response
                currentUser = User(
                    id: "",
                    email: email,
                    username: nil,
                    createdAt: Date(),
                    subscriptionTier: .free,
                    daysActive: 0,
                    longestStreak: 0,
                    photosUploaded: 0
                )
            }
            isAuthenticated = true
            shouldShowCamera = true
            authState = .loaded
            return true
        } catch {
            // Translate server errors into user-friendly messages
            authState = .error(friendlyMessage(for: error))
            return false
        }
    }

    /// Converts raw API errors into user-friendly messages.
    /// "No face detected" / 422 errors are only relevant during photo analysis,
    /// never during authentication.
    private func friendlyMessage(for error: Error) -> String {
        if let apiError = error as? APIError {
            switch apiError {
            case .serverError(422, _):
                // This should never happen during auth — if it does, the backend
                // has a bug. Show a generic message instead of "No face detected".
                return "Something went wrong. Please try again."
            case .notAuthenticated:
                return "Session expired. Please log in again."
            case .networkError:
                return "No internet connection. Please check your network."
            case .timeout:
                return "Request timed out. Please try again."
            default:
                return apiError.localizedDescription
            }
        }
        return error.localizedDescription
    }

    func restoreFromCache() {
        if APIService.shared.isAuthenticated {
            isAuthenticated = true
            // Fetch latest user info in background
            Task {
                do {
                    currentUser = try await APIService.shared.getCurrentUser()
                } catch {
                    // Keep cached state; token may be expired
                    if case APIError.notAuthenticated = error {
                        signOut()
                    }
                }
            }
        }
    }

    func signOut() {
        APIService.shared.logout()
        isAuthenticated = false
        shouldShowCamera = false
        showSessionExpired = false
        currentUser = nil
        currentPhoto = nil
        currentPhotoID = nil
        currentScore = nil
        currentPlan = nil
        dashboardData = nil
        exploreData = nil
        authState = .idle
        dashboardState = .idle
        planState = .idle
        exploreState = .idle
    }

    /// Dismisses the session-expired alert and returns the user to onboarding.
    /// Triggered by the "Log In" button on the alert.
    func handleSessionExpired() {
        signOut()
    }

    func deleteAccount() async -> Bool {
        // No delete endpoint yet — just sign out locally
        signOut()
        return true
    }

    // MARK: - Photo Upload ---------------------------------------------------

    func uploadPhoto(image: UIImage) async -> Bool {
        guard let data = ImageCompressor.compressImage(image) else {
            return false
        }
        isUploading = true
        uploadProgress = 0.3
        do {
            let response = try await APIService.shared.uploadPhoto(
                data: data,
                fileName: "photo_\(Int(Date().timeIntervalSince1970)).jpg"
            )
            uploadProgress = 1.0
            currentPhotoID = response.id
            isUploading = false
            return true
        } catch {
            isUploading = false
            uploadProgress = 0
            return false
        }
    }

    /// Cancels a long-running analysis poll (called from the Cancel button).
    func cancelAnalysis() {
        analysisCancelled = true
        isAnalyzing = false
        isPolling = false
    }

    func pollForResults(photoID: String) async -> Score? {
        isAnalyzing = true
        isPolling = true
        analysisIsTakingLonger = false
        analysisCancelled = false

        defer {
            isAnalyzing = false
            isPolling = false
        }

        // Poll every 2 seconds for up to 60 seconds.
        for attempt in 0..<30 {
            if analysisCancelled || Task.isCancelled {
                return nil
            }

            do {
                let status = try await APIService.shared.getPhotoStatus(photoId: photoID)
                if status.analysis_status == "completed" {
                    let score = status.toScore(photoId: photoID)
                    currentScore = score
                    return score
                } else if status.analysis_status == "failed" {
                    // Pre-analysis validation failed (e.g. no face, blurry, too dark).
                    // Surface the backend's user-facing message instead of showing a 0 score.
                    if let reason = status.error ?? status.message {
                        uploadError = reason
                        return nil
                    }
                    // Generic failure with no message — return a fallback score so the flow continues.
                    let fallback = Score(
                        photoID: photoID,
                        overallScore: 0,
                        categoryScores: [:],
                        tierLabel: "🚀 Starting",
                        strengths: [],
                        improvementAreas: [],
                        analysisStatus: "failed",
                        createdAt: Date()
                    )
                    currentScore = fallback
                    return fallback
                }
            } catch {
                // Timeout or transient network error (e.g. 404 while the photo
                // is still being processed) — retry after the 2s sleep below.
                analysisIsTakingLonger = true
            }

            // After ~10s of still processing (or any retry), surface a
            // "still working" message so the user isn't left wondering.
            if attempt >= 5 {
                analysisIsTakingLonger = true
            }

            if analysisCancelled || Task.isCancelled {
                return nil
            }
            try? await Task.sleep(nanoseconds: 2_000_000_000)
        }

        // Timeout after 60s — return nil.
        return nil
    }

    // MARK: - Plan Fetching --------------------------------------------------

    func fetchPlan() async {
        planState = .loading
        do {
            currentPlan = try await fetchPlanWithRetry()
            planState = .loaded
        } catch {
            planState = .error(friendlyPlanMessage(for: error))
        }
    }

    /// Fetches the 90-day plan with a single retry on transient failures
    /// (timeouts / network blips). The `/plan` endpoint is normally fast,
    /// but plan regeneration can occasionally take longer on first request.
    private func fetchPlanWithRetry(maxAttempts: Int = 2) async throws -> Plan {
        do {
            return try await APIService.shared.getPlan()
        } catch {
            guard maxAttempts > 1 else { throw error }
            try? await Task.sleep(nanoseconds: 1_500_000_000)
            return try await fetchPlanWithRetry(maxAttempts: maxAttempts - 1)
        }
    }

    /// User-friendly message for plan fetch failures (esp. timeouts).
    private func friendlyPlanMessage(for error: Error) -> String {
        if let apiError = error as? APIError, case .timeout = apiError {
            return "Your plan is taking a little longer than expected. Tap Retry to try again."
        }
        return error.localizedDescription
    }

    func markTaskComplete(taskID: String) async {
        do {
            _ = try await APIService.shared.markTaskComplete(taskId: taskID)
            // Refresh plan
            await fetchPlan()
        } catch {
            // Silently fail for individual task toggles
        }
    }

    // MARK: - Dashboard Fetching --------------------------------------------

    func fetchDashboard() async {
        dashboardState = .loading
        do {
            dashboardData = try await APIService.shared.getDashboard()
            dashboardState = .loaded
        } catch {
            if isAuthError(error) {
                // Token invalid/expired — surface a friendly alert instead of a
                // permanent red error text on the dashboard.
                showSessionExpired = true
                dashboardState = .idle
            } else {
                dashboardState = .error(error.localizedDescription)
            }
        }
    }

    /// Returns true for errors that indicate the session is no longer valid.
    private func isAuthError(_ error: Error) -> Bool {
        if let apiError = error as? APIError {
            switch apiError {
            case .notAuthenticated:
                return true
            case .serverError(401, _):
                return true
            default:
                return false
            }
        }
        return false
    }

    // MARK: - Explore Fetching -----------------------------------------------

    func fetchExplore() async {
        exploreState = .loading
        do {
            exploreData = try await APIService.shared.getExplore()
            exploreState = .loaded
        } catch {
            exploreState = .error(error.localizedDescription)
        }
    }
}

// MARK: - Main Tab -----------------------------------------------------------

enum MainTab: Hashable {
    case home
    case plan
    case explore
    case profile
}

// MARK: - App Loading State --------------------------------------------------

enum AppLoadingState {
    case idle
    case loading
    case loaded
    case error(String)
}