import SwiftUI
import Combine

@MainActor
final class AppState: ObservableObject {
    // MARK: - Auth -----------------------------------------------------------
    @Published var isAuthenticated = false
    @Published var currentUser: User?

    // MARK: - Photo & Analysis -----------------------------------------------
    @Published var currentPhoto: UIImage?
    @Published var currentPhotoID: String?
    @Published var currentScore: Score?
    @Published var isUploading = false
    @Published var isAnalyzing = false
    @Published var isPolling = false
    @Published var uploadProgress: Double = 0
    @Published var uploadError: String?

    // MARK: - Plan -----------------------------------------------------------
    @Published var currentPlan: Plan?

    // MARK: - Dashboard ------------------------------------------------------
    @Published var dashboardData: DashboardData?

    // MARK: - Explore --------------------------------------------------------
    @Published var exploreData: ExploreData?
    @Published var dashboard: DashboardData?

    // MARK: - Loading States -------------------------------------------------
    @Published var authState: AppLoadingState = .idle
    @Published var dashboardState: AppLoadingState = .idle
    @Published var planState: AppLoadingState = .idle
    @Published var exploreState: AppLoadingState = .idle

    // MARK: - Authentication ------------------------------------------------

    func signUp(email: String, password: String, fullName: String? = nil) async -> Bool {
        authState = .loading
        do {
            let response = try await APIService.shared.signUp(email: email, password: password, fullName: fullName)
            // After signup, auto-login to get token
            _ = try await APIService.shared.login(email: email, password: password)
            currentUser = response.toUser()
            isAuthenticated = true
            authState = .loaded
            return true
        } catch {
            authState = .error(error.localizedDescription)
            return false
        }
    }

    func login(email: String, password: String) async -> Bool {
        authState = .loading
        do {
            let token = try await APIService.shared.login(email: email, password: password)
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
            authState = .loaded
            return true
        } catch {
            authState = .error(error.localizedDescription)
            return false
        }
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
        currentUser = nil
        currentPhoto = nil
        currentPhotoID = nil
        currentScore = nil
        currentPlan = nil
        dashboardData = nil
        exploreData = nil
        authState = .idle
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

    func pollForResults(photoID: String) async -> Score? {
        isAnalyzing = true
        // Poll every 2 seconds for up to 60 seconds
        for _ in 0..<30 {
            do {
                let status = try await APIService.shared.getPhotoStatus(photoId: photoID)
                if status.analysis_status == "completed" {
                    let score = status.toScore(photoId: photoID)
                    currentScore = score
                    isAnalyzing = false
                    return score
                } else if status.analysis_status == "failed" {
                    isAnalyzing = false
                    // Return a fallback score instead of nil so the flow continues
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
                // Still processing — wait and retry
                try await Task.sleep(nanoseconds: 2_000_000_000)
            } catch {
                // If we get a 404, the photo might not exist yet; keep polling
                try? await Task.sleep(nanoseconds: 2_000_000_000)
                continue
            }
        }
        // Timeout after 60s — return nil
        isAnalyzing = false
        return nil
    }

    // MARK: - Plan Fetching --------------------------------------------------

    func fetchPlan() async {
        planState = .loading
        do {
            currentPlan = try await APIService.shared.getPlan()
            planState = .loaded
        } catch {
            planState = .error(error.localizedDescription)
        }
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
            dashboardState = .error(error.localizedDescription)
        }
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

// MARK: - App Loading State --------------------------------------------------

enum AppLoadingState {
    case idle
    case loading
    case loaded
    case error(String)
}