import Foundation
import UIKit

// MARK: - API Error Handling ------------------------------------------------

enum APIError: LocalizedError {
    case invalidURL
    case notAuthenticated
    case serverError(Int, String)
    case decodingError(String)
    case networkError(String)
    case timeout

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid request URL."
        case .notAuthenticated:
            return "Please log in again."
        case .serverError(let code, _):
            switch code {
            case 401: return "Please log in again."
            case 404: return "Something went wrong. Please try again."
            case 413: return "Image is too large. Please choose a smaller photo."
            case 422: return "No face detected. Please use a clear front-facing photo."
            case 429: return "Too many requests. Please wait a moment."
            case 500...599: return "Our servers are busy. Please try again."
            default: return "Something went wrong. Please try again."
            }
        case .decodingError:
            return "Could not read server response. Please try again."
        case .networkError:
            return "No internet connection. Please check your network."
        case .timeout:
            return "Taking longer than expected. Please try again."
        }
    }
}

// MARK: - Loading State -----------------------------------------------------

enum LoadingState<T> {
    case idle
    case loading
    case loaded(T)
    case error(String)
}

// MARK: - API Service --------------------------------------------------------

final class APIService {
    static let shared = APIService()

    private let baseURL = LXConstants.apiBaseURL
    private var authToken: String?
    private let session: URLSession

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 300
        config.timeoutIntervalForResource = 600
        self.session = URLSession(configuration: config)
        // Restore cached token
        self.authToken = KeychainManager.getToken(forKey: KeychainManager.accessTokenKey)
    }

    var accessToken: String? {
        get { authToken }
        set {
            authToken = newValue
            if let token = newValue {
                KeychainManager.saveToken(token, forKey: KeychainManager.accessTokenKey)
            } else {
                KeychainManager.deleteToken(forKey: KeychainManager.accessTokenKey)
            }
        }
    }

    var isAuthenticated: Bool { authToken != nil }

    // MARK: - HTTP Helpers ---------------------------------------------------

    private func url(_ path: String) -> URL? {
        URL(string: "\(baseURL)\(path)")
    }

    private func authenticatedRequest(path: String, method: String = "GET", body: Data? = nil) throws -> URLRequest {
        guard let url = url(path) else { throw APIError.invalidURL }
        guard let token = authToken else { throw APIError.notAuthenticated }
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = body
        return req
    }

    private func request(_ path: String, method: String = "GET", body: Data? = nil, auth: Bool = false) throws -> URLRequest {
        guard let url = url(path) else { throw APIError.invalidURL }
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if auth, let token = authToken {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        } else if auth {
            throw APIError.notAuthenticated
        }
        req.httpBody = body
        return req
    }

    private func perform<T: Decodable>(_ req: URLRequest) async throws -> T {
        // ── Request logging ──────────────────────────────────────
        print("📡 [API] \(req.httpMethod ?? "GET") \(req.url?.absoluteString ?? "?")")
        if let headers = req.allHTTPHeaderFields, !headers.isEmpty {
            print("   Headers: \(headers)")
        }
        if let body = req.httpBody, let bodyStr = String(data: body, encoding: .utf8) {
            let truncated = bodyStr.count > 200 ? bodyStr.prefix(200) + "..." : bodyStr
            print("   Body: \(truncated)")
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: req)
        } catch let err as URLError where err.code == .timedOut {
            print("⏱️ [API] Request timed out: \(req.url?.absoluteString ?? "?")")
            throw APIError.timeout
        } catch {
            print("❌ [API] Network error: \(error.localizedDescription)")
            throw APIError.networkError(error.localizedDescription)
        }
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.networkError("Invalid response")
        }
        print("📡 [API] Response status: \(httpResponse.statusCode)")

        guard (200...299).contains(httpResponse.statusCode) else {
            let detail = (try? JSONDecoder().decode(LXError.self, from: data))?.detail ?? String(data: data, encoding: .utf8) ?? "Unknown error"
            print("❌ [API] Server error \(httpResponse.statusCode): \(detail)")
            throw APIError.serverError(httpResponse.statusCode, detail)
        }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            if let debug = String(data: data, encoding: .utf8) {
                print("⚠️ Decoding error for \(T.self): \(error)\nRaw: \(debug.prefix(500))")
            }
            throw APIError.decodingError(error.localizedDescription)
        }
    }

    // MARK: - Auth -----------------------------------------------------------

    struct SignupResponse: Codable {
        let id: String
        let email: String
        let full_name: String?
        let subscription_tier: String?
        let is_subscribed: Bool?
        let current_day: Int?
        let current_streak: Int?
        let longest_streak: Int?
        let total_checkins: Int?

        func toUser() -> User {
            User(
                id: id,
                email: email,
                username: full_name,
                createdAt: Date(),
                subscriptionTier: SubscriptionTier(rawValue: subscription_tier ?? "free") ?? .free,
                daysActive: total_checkins ?? 0,
                longestStreak: longest_streak ?? 0,
                photosUploaded: 0
            )
        }
    }

    func signUp(email: String, password: String, fullName: String? = nil) async throws -> SignupResponse {
        let body: [String: Any] = [
            "email": email,
            "password": password,
            "full_name": fullName ?? email.components(separatedBy: "@").first ?? "User"
        ]
        let data = try JSONSerialization.data(withJSONObject: body)
        let req = try request("/auth/signup", method: "POST", body: data, auth: false)
        return try await perform(req) as SignupResponse
    }

    func login(email: String, password: String) async throws -> TokenResponse {
        // Backend expects OAuth2 form data (x-www-form-urlencoded)
        guard let url = url("/auth/login") else { throw APIError.invalidURL }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")

        var components = URLComponents()
        components.queryItems = [
            URLQueryItem(name: "grant_type", value: "password"),
            URLQueryItem(name: "username", value: email),
            URLQueryItem(name: "password", value: password),
        ]
        req.httpBody = components.percentEncodedQuery?.data(using: .utf8)

        let token: TokenResponse = try await perform(req)

        // Auto-set token from response
        self.accessToken = token.accessToken

        return token
    }

    func getCurrentUser() async throws -> User {
        let req = try authenticatedRequest(path: "/auth/me")
        let raw: SignupResponse = try await perform(req)
        return raw.toUser()
    }

    // MARK: - Photos ---------------------------------------------------------

    struct NestedPhotoUploadResponse: Codable {
        let id: String
        let file_url: String?
        let user_id: String?
        let analysis_status: String?
        let score: Double?
        let is_baseline: Bool?
        let week_number: Int?
        let debug_timings: [String: Double]?

        func toUploadResponse() -> PhotoUploadResponse {
            PhotoUploadResponse(
                id: id,
                fileURL: file_url ?? "",
                analysisStatus: analysis_status ?? "processing",
                message: nil
            )
        }
    }

    func uploadPhoto(data: Data, fileName: String) async throws -> PhotoUploadResponse {
        let maxRetries = 3
        var lastError: Error?

        for attempt in 1...maxRetries {
            do {
                guard let url = url("/photos/upload") else { throw APIError.invalidURL }
                guard let token = authToken else { throw APIError.notAuthenticated }

                let boundary = "Boundary-\(UUID().uuidString)"
                var req = URLRequest(url: url)
                req.httpMethod = "POST"
                req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
                req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

                var body = Data()
                body.append("--\(boundary)\r\n".data(using: .utf8)!)
                body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(fileName)\"\r\n".data(using: .utf8)!)
                body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
                body.append(data)
                body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
                req.httpBody = body

                let nested: NestedPhotoUploadResponse = try await perform(req)
                return nested.toUploadResponse()
            } catch {
                lastError = error
                print("🔄 [API] Upload attempt \(attempt)/\(maxRetries) failed: \(error.localizedDescription)")
                if attempt < maxRetries {
                    // Exponential backoff: 2s, 4s, ...
                    let delay = UInt64(2_000_000_000 * (1 << (attempt - 1)))
                    try? await Task.sleep(nanoseconds: delay)
                }
            }
        }
        throw lastError ?? APIError.networkError("Upload failed after \(maxRetries) attempts")
    }

    func getPhotoStatus(photoId: String) async throws -> PhotoStatusResponse {
        var req = try authenticatedRequest(path: "/photos/\(photoId)/status")
        // Fast-fail so the 2s retry loop recovers quickly instead of hanging
        // on the global 300s request timeout.
        req.timeoutInterval = 10
        return try await perform(req)
    }

    func getAllPhotos() async throws -> [NestedPhotoUploadResponse] {
        let req = try authenticatedRequest(path: "/photos/all")
        return try await perform(req)
    }

    // MARK: - Photo Status Response (from polling) --------------------------

    struct PhotoStatusResponse: Decodable {
        let id: String
        let analysis_status: String
        let score: Double?
        let category_breakdown: [String: CategoryScore]?
        let strengths: [String]?
        let weaknesses: [String]?

        enum CodingKeys: String, CodingKey {
            case id, score, strengths, weaknesses
            case analysis_status = "analysis_status"
            case category_breakdown = "category_breakdown"
        }

        init(from decoder: Decoder) throws {
            let container = try decoder.container(keyedBy: CodingKeys.self)
            id = try container.decode(String.self, forKey: .id)
            analysis_status = try container.decode(String.self, forKey: .analysis_status)
            score = try container.decodeIfPresent(Double.self, forKey: .score)
            strengths = try container.decodeIfPresent([String].self, forKey: .strengths)
            weaknesses = try container.decodeIfPresent([String].self, forKey: .weaknesses)

            // The backend may send "heuristic": false (a Bool) alongside real
            // category objects in category_breakdown. Decode as a raw JSON
            // dictionary and filter out any entries that aren't category objects.
            let raw = try? container.decode([String: AnyDecodableValue].self, forKey: .category_breakdown)
            if let raw = raw {
                var filtered: [String: CategoryScore] = [:]
                for (key, anyVal) in raw {
                    guard case .dictionary(let dict) = anyVal else { continue }
                    var scoreVal: Double?
                    var valueVal: Double?
                    var nameVal: String?
                    var labelVal: String?
                    for (k, v) in dict {
                        switch k {
                        case "score": if case .double(let d) = v { scoreVal = d }
                        case "value": if case .double(let d) = v { valueVal = d }
                        case "name":  if case .string(let s) = v { nameVal = s }
                        case "label": if case .string(let s) = v { labelVal = s }
                        default: break
                        }
                    }
                    filtered[key] = CategoryScore(score: scoreVal, value: valueVal,
                                                   name: nameVal, label: labelVal,
                                                   heuristic: nil)
                }
                category_breakdown = filtered.isEmpty ? nil : filtered
            } else {
                category_breakdown = nil
            }
        }

        func toScore(photoId: String) -> Score {
            var categoryScores: [String: Double] = [:]
            if let breakdown = category_breakdown {
                for (key, val) in breakdown {
                    categoryScores[key] = val.score ?? val.value ?? 0
                }
            }
            return Score(
                photoID: photoId,
                overallScore: score ?? 0,
                categoryScores: categoryScores,
                tierLabel: tierLabel(for: score ?? 0),
                strengths: strengths ?? [],
                improvementAreas: weaknesses ?? [],
                analysisStatus: analysis_status,
                createdAt: Date()
            )
        }

        private func tierLabel(for score: Double) -> String {
            switch score {
            case 95...100: return "👑 Apex"
            case 88..<95:  return "⭐ Elite"
            case 80..<88:  return "💪 Great"
            case 70..<80:  return "👍 Good"
            case 60..<70:  return "🌱 Developing"
            default:       return "🚀 Starting"
            }
        }
    }

    struct CategoryScore: Codable {
        let score: Double?
        let value: Double?
        let name: String?
        let label: String?
        let heuristic: Bool?
    }

    /// A decodable wrapper for arbitrary JSON values.
    /// Used to safely decode mixed-type dictionaries like the
    /// category_breakdown response which may contain booleans
    /// (e.g. "heuristic": false) alongside category objects.
    enum AnyDecodableValue: Decodable {
        case double(Double)
        case string(String)
        case bool(Bool)
        case dictionary([String: AnyDecodableValue])
        case array([AnyDecodableValue])
        case null

        init(from decoder: Decoder) throws {
            let container = try decoder.singleValueContainer()
            if container.decodeNil() { self = .null; return }
            if let v = try? container.decode(Double.self) { self = .double(v); return }
            if let v = try? container.decode(String.self) { self = .string(v); return }
            if let v = try? container.decode(Bool.self) { self = .bool(v); return }
            if let v = try? container.decode([String: AnyDecodableValue].self) { self = .dictionary(v); return }
            if let v = try? container.decode([AnyDecodableValue].self) { self = .array(v); return }
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Unsupported JSON type"
            )
        }
    }

    // MARK: - Plan -----------------------------------------------------------

    struct PlanAPIResponse: Codable {
        let has_plan: Bool
        let plan_id: String?
        let photo_id: String?
        let baseline_score: Double?
        let total_days: Int?
        let current: PlanCurrent?
        let this_week: PlanWeek?
        let todays_quote: PlanQuote?
        let upcoming_milestone: PlanMilestone?
        let streak: Int?
        let products: [PlanProduct]?
        let bonus_tip: String?
        let phases: PlanPhases?

        struct PlanCurrent: Codable {
            let day: Int
            let week: Int
            let phase: String
            let phase_title: String?
            let phase_emotional_goal: String?
            let focus_areas: [String]?
        }

        struct PlanWeek: Codable {
            let week: Int?
            let title: String?
            let daily_tasks: [PlanTaskItem]?
        }

        struct PlanTaskItem: Codable {
            let name: String?
            let label: String?
            let task: String?
            let details: String?
            let time: String?
            let completed: Bool?
        }

        struct PlanQuote: Codable {
            let day: Int?
            let quote: String?
            let author: String?
        }

        struct PlanMilestone: Codable {
            let day: Int?
            let days_remaining: Int?
            let details: [String: String]?
        }

        struct PlanProduct: Codable {
            let name: String?
            let description: String?
            let price: String?
            let rating: Double?
            let review_count: Int?
            let image_url: String?
            let affiliate_url: String?
        }

        struct PlanPhases: Codable {
            let phase_1: PhasePhase?
            let phase_2: PhasePhase?
            let phase_3: PhasePhase?

            struct PhasePhase: Codable {
                let days: String?
                let title: String?
                let complete: Bool?
            }
        }

        func toPlan() -> Plan {
            var phases: [Phase] = []
            var tasks: [PlanTask] = []

            if let weekTasks = this_week?.daily_tasks {
                for (idx, t) in weekTasks.enumerated() {
                    tasks.append(PlanTask(
                        id: "task_\(idx)",
                        order: idx,
                        label: t.name ?? t.label ?? t.task ?? "Task \(idx + 1)",
                        timeOfDay: t.time ?? "Today",
                        isCompleted: t.completed ?? false
                    ))
                }
            }

            if !tasks.isEmpty {
                let phaseTitle = current?.phase_title ?? "Foundation"
                phases.append(Phase(
                    id: current?.phase ?? "phase_1",
                    order: 1,
                    title: phaseTitle,
                    description: current?.phase_emotional_goal ?? "",
                    weeks: "Week \(current?.week ?? 1)",
                    tasks: tasks
                ))
            }

            return Plan(
                id: plan_id ?? "",
                userID: "",
                startDate: Date(),
                currentDay: current?.day ?? 0,
                phases: phases,
                progressPhotos: []
            )
        }
    }

    func getPlan() async throws -> Plan {
        let req = try authenticatedRequest(path: "/plan")
        let raw: PlanAPIResponse = try await perform(req)
        return raw.toPlan()
    }

    func markTaskComplete(taskId: String) async throws -> PlanAPIResponse {
        let body = try JSONSerialization.data(withJSONObject: ["completed_tasks": [taskId]])
        let req = try authenticatedRequest(path: "/plan/checkin", method: "POST", body: body)
        return try await perform(req) as PlanAPIResponse
    }

    func checkin() async throws -> PlanAPIResponse {
        let body = try JSONSerialization.data(withJSONObject: ["completed_tasks": []])
        let req = try authenticatedRequest(path: "/plan/checkin", method: "POST", body: body)
        return try await perform(req) as PlanAPIResponse
    }

    // MARK: - Dashboard ------------------------------------------------------

    struct DashboardAPIResponse: Decodable {
        let profile: ProfileBlock?
        let plan: PlanBlock?
        let progress: ProgressBlock?
        let milestones: MilestonesBlock?
        let next_action: NextActionBlock?

        struct ProfileBlock: Codable {
            let id: String?
            let email: String?
            let full_name: String?
            let age: Int?
            let gender: String?
            let goals: [String]?
            let onboarding_completed: Bool?
            let subscription_tier: String?
            let is_subscribed: Bool?
        }

        struct PlanBlock: Codable {
            let has_plan: Bool?
            let plan_id: String?
            let current_day: Int?
            let total_days: Int?
            let progress_percentage: Double?
            let days_remaining: Int?
            let current_week: Int?
            let current_phase: String?
            let is_active: Bool?
        }

        struct ProgressBlock: Decodable {
            let initial_score: Double?
            let initial_score_label: AnyDecodableValue?
            let current_score: Double?
            let current_score_label: AnyDecodableValue?
            let improvement: Double?
            let trend: String?
            let current_streak: Int?
            let longest_streak: Int?
            let total_checkins: Int?
            let checked_in_today: Bool?
        }

        struct MilestonesBlock: Codable {
            let next: MilestoneItem?
            let completed: [MilestoneItem]?
            let total_milestones: Int?

            struct MilestoneItem: Codable {
                let day: Int?
                let label: String?
                let emoji: String?
                let achieved: Bool?
                let days_until: Int?
            }
        }

        struct NextActionBlock: Codable {
            let task: String?
            let time: String?
            let description: String?
        }

        func toDashboardData() -> DashboardData {
            let scoreHistory: [ScoreEntry] = [
                ScoreEntry(id: "baseline", date: Date().addingTimeInterval(-86400 * 7), score: progress?.initial_score ?? 0),
                ScoreEntry(id: "current", date: Date(), score: progress?.current_score ?? 0)
            ]

            var milestones: [Milestone] = []
            if let completed = self.milestones?.completed {
                for m in completed {
                    milestones.append(Milestone(
                        id: "m_\(m.day ?? 0)",
                        day: m.day ?? 0,
                        label: "\(m.emoji ?? "") \(m.label ?? "")",
                        isCompleted: true
                    ))
                }
            }
            if let next = self.milestones?.next {
                milestones.append(Milestone(
                    id: "m_next",
                    day: next.day ?? 0,
                    label: "\(next.emoji ?? "🎯") \(next.label ?? "")",
                    isCompleted: false
                ))
            }

            return DashboardData(
                currentStreak: progress?.current_streak ?? 0,
                currentScore: progress?.current_score,
                baselineScore: progress?.initial_score,
                scoreHistory: scoreHistory,
                tasksToday: [],
                milestones: milestones
            )
        }
    }

    func getDashboard() async throws -> DashboardData {
        let req = try authenticatedRequest(path: "/dashboard")
        let raw: DashboardAPIResponse = try await perform(req)
        return raw.toDashboardData()
    }

    // MARK: - Explore --------------------------------------------------------

    // Currently no /explore endpoint; fallback to plan/products + hardcoded content
    func getExplore() async throws -> ExploreData {
        // Attempt plan endpoint for products
        let req = try authenticatedRequest(path: "/plan")
        let planRaw: PlanAPIResponse = try await perform(req)
        var products: [Product] = []
        if let p = planRaw.products {
            for (idx, item) in p.enumerated() {
                products.append(Product(
                    id: "prod_\(idx)",
                    name: item.name ?? "",
                    description: item.description ?? "",
                    price: Self.parsePrice(item.price),
                    rating: item.rating ?? 0,
                    reviewCount: item.review_count ?? 0,
                    imageURL: item.image_url,
                    affiliateURL: item.affiliate_url
                ))
            }
        }
        return ExploreData(
            transformations: [],
            products: products,
            articles: []
        )
    }

    /// Parses a price string like "$34" or "$1,234.99" into a Double.
    /// The backend sends product prices as strings (e.g. "$34"), while the
    /// `Product` model keeps `price` as a `Double` for display formatting.
    private static func parsePrice(_ raw: String?) -> Double {
        guard let raw = raw else { return 0 }
        let cleaned = raw
            .replacingOccurrences(of: "$", with: "")
            .replacingOccurrences(of: ",", with: "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        return Double(cleaned) ?? 0
    }

    // MARK: - Logout ---------------------------------------------------------

    func logout() {
        accessToken = nil
    }
}

