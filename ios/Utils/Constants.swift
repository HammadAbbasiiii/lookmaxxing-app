import Foundation

/// Centralised constants for the LookMaxx AI app.
/// Change once, apply everywhere — no magic strings in views.
enum LXConstants {
    // ── API ──────────────────────────────────────────────────
    static let apiBaseURL = "https://lookmaxx-api.onrender.com/api/v1"

    // ── Compression ─────────────────────────────────────────
    static let maxImageDimension: CGFloat = 1200
    static let jpegQuality: CGFloat = 0.75
    static let maxUploadSizeKB = 500
    static let minFaceDimension: CGFloat = 400

    // ── Polling ─────────────────────────────────────────────
    static let statusPollInterval: TimeInterval = 1.5
    static let statusPollMaxAttempts = 15

    // ── UI ──────────────────────────────────────────────────
    static let cornerRadius: CGFloat = 12
    static let buttonHeight: CGFloat = 52
    static let standardPadding: CGFloat = 20

    // ── Plan ────────────────────────────────────────────────
    static let planTotalDays = 90
    static let progressPhotoDays = [30, 60, 90]

    // ── Score thresholds ────────────────────────────────────
    static let scoreThresholds: [(min: Double, label: String)] = [
        (85, "Apex"),
        (80, "High"),
        (70, "Notable"),
        (0,  "Solid")
    ]

    /// Maps a numeric score to a tier label.
    static func tierLabel(for score: Double) -> String {
        for (min, label) in scoreThresholds {
            if score >= min { return label }
        }
        return "Solid"
    }
}