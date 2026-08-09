import SwiftUI

// MARK: - Auth ViewModel --------------------------------------------------

final class AuthViewModel: ObservableObject {
    @Published var username = ""
    @Published var email = ""
    @Published var password = ""
    @Published var isLoading = false
    @Published var errorMessage: String?

    func login(appState: AppState) {
        guard !username.isEmpty, !password.isEmpty else {
            errorMessage = "Please fill in all fields."
            return
        }
        isLoading = true
        errorMessage = nil

        Task {
            do {
                let token = try await APIService.shared.login(email: username, password: password)
                await MainActor.run {
                    APIService.shared.accessToken = token.accessToken
                    appState.isAuthenticated = true
                    isLoading = false
                }
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    isLoading = false
                }
            }
        }
    }

    func signUp(appState: AppState) {
        guard !email.isEmpty, !username.isEmpty, password.count >= AppConfig.minPasswordLength else {
            errorMessage = "Please provide a valid email, username, and password (min \(AppConfig.minPasswordLength) chars)."
            return
        }
        isLoading = true
        errorMessage = nil

        Task {
            do {
                _ = try await APIService.shared.signUp(email: email, password: password, fullName: username)
                let token = try await APIService.shared.login(email: email, password: password)
                await MainActor.run {
                    APIService.shared.accessToken = token.accessToken
                    appState.isAuthenticated = true
                    isLoading = false
                }
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    isLoading = false
                }
            }
        }
    }
}

// MARK: - Photo ViewModel -------------------------------------------------

final class PhotoViewModel: ObservableObject {
    @Published var selectedImage: UIImage?
    @Published var isCompressing = false
    @Published var compressedSizeKB: Int = 0

    /// Compress and upload the currently selected image.
    func upload(appState: AppState) {
        guard let img = selectedImage else { return }

        Task {
            await MainActor.run {
                appState.isUploading = true
                appState.uploadError = nil
            }

            // 1. Compress
            await MainActor.run { isCompressing = true }
            guard let compressed = await compress(img: img) else {
                await MainActor.run {
                    appState.uploadError = "Could not compress image. Please try another photo."
                    appState.isUploading = false
                    isCompressing = false
                }
                return
            }
            await MainActor.run {
                compressedSizeKB = compressed.count / 1024
                isCompressing = false
                appState.currentPhoto = img
            }

            // 2. Upload
            do {
                let response = try await APIService.shared.uploadPhoto(data: compressed, fileName: "photo_\(Date().timeIntervalSince1970).jpg")
                await MainActor.run { appState.isUploading = false }

                // 3. Poll for score
                await pollScore(photoId: response.id, appState: appState)
            } catch {
                await MainActor.run {
                    appState.uploadError = error.localizedDescription
                    appState.isUploading = false
                }
            }
        }
    }

    private func compress(img: UIImage) async -> Data? {
        await Task.detached(priority: .userInitiated) {
            ImageCompressor.compressImage(img)
        }.value
    }

    private func pollScore(photoId: String, appState: AppState) async {
        await MainActor.run { appState.isPolling = true }

        for _ in 0..<LXConstants.statusPollMaxAttempts {
            do {
                let status = try await APIService.shared.getPhotoStatus(photoId: photoId)
                if status.analysis_status == "completed" {
                    await MainActor.run {
                        let score = status.toScore(photoId: photoId)
                        appState.currentScore = score
                        appState.isPolling = false
                        CacheService.shared.setScore(score)
                    }
                    return
                }
            } catch {
                // continue polling on transient errors
            }
            try? await Task.sleep(nanoseconds: UInt64(LXConstants.statusPollInterval * 1_000_000_000))
        }

        await MainActor.run {
            appState.uploadError = "Analysis timed out. Please try again."
            appState.isPolling = false
        }
    }
}

// MARK: - Plan ViewModel --------------------------------------------------

final class PlanViewModel: ObservableObject {
    @Published var plan: Plan?
    @Published var isLoading = false
    @Published var errorMessage: String?

    func loadPlan(appState: AppState) {
        // Use cache if available
        if let cached = CacheService.shared.cachedPlan() {
            plan = cached
            Task { @MainActor in
                appState.currentPlan = cached
            }
        }

        isLoading = true
        Task {
            do {
                let p = try await APIService.shared.getPlan()
                await MainActor.run {
                    plan = p
                    appState.currentPlan = p
                    isLoading = false
                    CacheService.shared.setPlan(p)
                }
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    isLoading = false
                }
            }
        }
    }

    func toggleTask(_ task: PlanTask) {
        guard var p = plan else { return }
        guard p.phases.flatMap(\.tasks).contains(where: { $0.id == task.id }) else { return }

        // Find the phase that contains the task so we can mutate it
        for (phaseIdx, phase) in p.phases.enumerated() {
            if let taskIdx = phase.tasks.firstIndex(where: { $0.id == task.id }) {
                p.phases[phaseIdx].tasks[taskIdx].isCompleted.toggle()
                let capturedPlan = p  // immutable copy for safe concurrency capture

                Task {
                    do {
                        if capturedPlan.phases[phaseIdx].tasks[taskIdx].isCompleted {
                            _ = try await APIService.shared.markTaskComplete(taskId: task.id)
                        }
                        await MainActor.run {
                            plan = capturedPlan
                            CacheService.shared.setPlan(capturedPlan)
                        }
                    } catch {
                        // revert
                        await MainActor.run {
                            errorMessage = "Could not update. Try again."
                        }
                    }
                }
                return
            }
        }
    }
}

// MARK: - Dashboard ViewModel ---------------------------------------------

final class DashboardViewModel: ObservableObject {
    @Published var data: DashboardData?
    @Published var isLoading = false
    @Published var errorMessage: String?

    func load(appState: AppState) {
        if let cached = CacheService.shared.cachedDashboard() {
            data = cached
        }

        isLoading = true
        Task {
            do {
                let d = try await APIService.shared.getDashboard()
                await MainActor.run {
                    data = d
                    appState.dashboard = d
                    isLoading = false
                    CacheService.shared.setDashboard(d)
                }
            } catch {
                // offline: keep cached data
                await MainActor.run { isLoading = false }
            }
        }
    }

    var scoreDelta: Double? {
        guard let current = data?.currentScore, let baseline = data?.baselineScore else { return nil }
        return current - baseline
    }

    var scoreDeltaText: String {
        guard let delta = scoreDelta else { return "" }
        let prefix = delta >= 0 ? "+" : ""
        return "\(prefix)\(String(format: "%.1f", delta)) from baseline"
    }
}