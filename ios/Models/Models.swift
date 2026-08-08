import Foundation

// MARK: - User ------------------------------------------------------------

struct User: Codable, Identifiable {
    let id: String
    let email: String
    var username: String?
    var age: Int?
    var gender: String?
    var avatarURL: String?
    var createdAt: Date
    var subscriptionTier: SubscriptionTier
    var daysActive: Int
    var longestStreak: Int
    var photosUploaded: Int

    enum CodingKeys: String, CodingKey {
        case id, email, username, age, gender
        case avatarURL = "avatar_url"
        case createdAt = "created_at"
        case subscriptionTier = "subscription_tier"
        case daysActive = "days_active"
        case longestStreak = "longest_streak"
        case photosUploaded = "photos_uploaded"
    }
}

enum SubscriptionTier: String, Codable {
    case free
    case pro
    case elite
}

// MARK: - Auth ------------------------------------------------------------

struct LoginRequest: Codable {
    let username: String
    let password: String
}

struct TokenResponse: Codable {
    let accessToken: String
    let tokenType: String

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
    }
}

// MARK: - Photo -----------------------------------------------------------

struct Photo: Codable, Identifiable {
    let id: String
    let fileURL: String
    let analysisStatus: AnalysisStatus
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case fileURL = "file_url"
        case analysisStatus = "analysis_status"
        case createdAt = "created_at"
    }
}

enum AnalysisStatus: String, Codable {
    case pending
    case processing
    case completed
    case failed
}

struct PhotoUploadResponse: Codable {
    let id: String
    let fileURL: String
    let analysisStatus: String
    let message: String?

    enum CodingKeys: String, CodingKey {
        case id
        case fileURL = "file_url"
        case analysisStatus = "analysis_status"
        case message
    }
}

// MARK: - Score -----------------------------------------------------------

struct Score: Codable {
    let photoID: String
    let overallScore: Double
    let categoryScores: [String: Double]
    let tierLabel: String
    let strengths: [String]
    let improvementAreas: [String]
    let analysisStatus: String
    var createdAt: Date?

    enum CodingKeys: String, CodingKey {
        case photoID = "photo_id"
        case overallScore = "score"
        case categoryScores = "category_scores"
        case tierLabel = "tier_label"
        case strengths
        case improvementAreas = "improvement_areas"
        case analysisStatus = "analysis_status"
        case createdAt = "created_at"
    }
}

// MARK: - Plan ------------------------------------------------------------

struct Plan: Codable {
    let id: String
    let userID: String
    let startDate: Date
    let currentDay: Int
    var phases: [Phase]
    let progressPhotos: [ProgressPhotoRecord]

    enum CodingKeys: String, CodingKey {
        case id
        case userID = "user_id"
        case startDate = "start_date"
        case currentDay = "current_day"
        case phases
        case progressPhotos = "progress_photos"
    }
}

struct Phase: Codable, Identifiable {
    let id: String
    let order: Int
    let title: String
    let description: String
    let weeks: String
    var tasks: [PlanTask]
}

struct PlanTask: Codable, Identifiable {
    let id: String
    let order: Int
    let label: String
    let timeOfDay: String
    var isCompleted: Bool

    enum CodingKeys: String, CodingKey {
        case id, order, label
        case timeOfDay = "time_of_day"
        case isCompleted = "is_completed"
    }
}

struct ProgressPhotoRecord: Codable, Identifiable {
    let id: String
    let day: Int
    let photoURL: String?
    let score: Double?
    let notes: String?

    enum CodingKeys: String, CodingKey {
        case id, day
        case photoURL = "photo_url"
        case score, notes
    }
}

// MARK: - Dashboard -------------------------------------------------------

struct DashboardData: Codable {
    let currentStreak: Int
    let currentScore: Double?
    let baselineScore: Double?
    let scoreHistory: [ScoreEntry]
    let tasksToday: [PlanTask]
    let milestones: [Milestone]

    enum CodingKeys: String, CodingKey {
        case currentStreak = "current_streak"
        case currentScore = "current_score"
        case baselineScore = "baseline_score"
        case scoreHistory = "score_history"
        case tasksToday = "tasks_today"
        case milestones
    }
}

struct ScoreEntry: Codable, Identifiable {
    let id: String
    let date: Date
    let score: Double
}

struct Milestone: Codable, Identifiable {
    let id: String
    let day: Int
    let label: String
    let isCompleted: Bool

    enum CodingKeys: String, CodingKey {
        case id, day, label
        case isCompleted = "is_completed"
    }
}

// MARK: - Product ---------------------------------------------------------

struct Product: Codable, Identifiable {
    let id: String
    let name: String
    let description: String
    let price: Double
    let rating: Double
    let reviewCount: Int
    let imageURL: String?
    let affiliateURL: String?

    enum CodingKeys: String, CodingKey {
        case id, name, description, price, rating
        case reviewCount = "review_count"
        case imageURL = "image_url"
        case affiliateURL = "affiliate_url"
    }
}

struct Transformation: Codable, Identifiable {
    let id: String
    let username: String
    let beforeScore: Double
    let afterScore: Double
    let beforeImageURL: String?
    let afterImageURL: String?

    enum CodingKeys: String, CodingKey {
        case id, username
        case beforeScore = "before_score"
        case afterScore = "after_score"
        case beforeImageURL = "before_image_url"
        case afterImageURL = "after_image_url"
    }
}

// MARK: - Explore ---------------------------------------------------------

struct ExploreData: Codable {
    let transformations: [Transformation]
    let products: [Product]
    let articles: [Article]
}

struct Article: Codable, Identifiable {
    let id: String
    let title: String
    let summary: String
    let url: String
    let imageURL: String?

    enum CodingKeys: String, CodingKey {
        case id, title, summary, url
        case imageURL = "image_url"
    }
}

// MARK: - Processing facts ------------------------------------------------

enum ProcessingFact {
    static let facts = [
        "Facial symmetry is a key indicator of attractiveness.",
        "Strong jawlines are associated with higher testosterone.",
        "Skin quality is the first thing people notice.",
        "Sleep and hydration are the fastest ways to improve your appearance.",
        "Facial harmony is more important than any single feature.",
        "People form first impressions in under 200 milliseconds.",
        "Good posture can instantly improve your perceived attractiveness.",
        "Confidence is the most attractive non-physical trait.",
        "Consistent skincare routines show results in 4–6 weeks.",
        "Hydration affects skin plumpness within 24 hours."
    ]

    static func random() -> String { facts.randomElement() ?? facts[0] }
}

// MARK: - API Error -------------------------------------------------------

struct LXError: Codable, LocalizedError {
    let detail: String
    var errorDescription: String? { detail }
}