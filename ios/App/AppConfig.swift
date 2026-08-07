import Foundation

/// Compile-time configuration for the LookMaxx AI app.
///
/// Keep secrets out of source control — these are client-safe values only.
enum AppConfig {
    // ── API ──────────────────────────────────────────────────
    static let apiBaseURL = LXConstants.apiBaseURL

    // ── Auth ─────────────────────────────────────────────────
    static let minPasswordLength = 8
    static let maxUploadFileSizeKB = 10_000  // server-side cap; client targets 500 KB

    // ── Feature flags ───────────────────────────────────────
    static let enableDebugLogging = false
    static let enableMockData = false     // flip true for SwiftUI previews
}