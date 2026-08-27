import SwiftUI

/// LookMaxx AI colour palette — every colour has a psychological purpose.
///
/// Usage: `Color.lxBlack` or `Color.lxGold`
///
/// Reference:
///   https://lookmaxx-ai-colours.notion.site
enum LXColor {
    // ── Primaries ────────────────────────────────────────────
    static let black      = Color(hex: "#000000")   // Power, sophistication, mystery
    static let gold       = Color(hex: "#FFD700")   // Success, premium, elite
    static let deepNavy   = Color(hex: "#1A1A2E")   // Trust, calm, depth
    static let white      = Color(hex: "#FFFFFF")   // Clean, fresh, pure

    // ── Accents ──────────────────────────────────────────────
    static let amber      = Color(hex: "#FFB300")   // Warmth, energy, action
    static let teal       = Color(hex: "#00D4FF")   // Trust, professional
    static let red        = Color(hex: "#FF4444")   // Caution, urgency
    static let green      = Color(hex: "#00C853")   // Growth, success
    static let darkPurple = Color(hex: "#2D1B69")   // Luxury, mystery

    // ── Neutrals ────────────────────────────────────────────
    static let warmWhite  = Color(hex: "#F5F5F5")   // Secondary text, subtle elements
    static let softGray   = Color(hex: "#8E8E93")   // Placeholders, hints, disabled text
    static let goldGlow   = Color(hex: "#FFE44D")   // Hover/active states, warm energy

    // ── Tier mapping ────────────────────────────────────────
    static func tierColour(for label: String) -> Color {
        switch label {
        case "Apex":    return gold
        case "High":    return green
        case "Notable": return teal
        case "Solid":   return amber
        default:        return white
        }
    }

    static func tierEmoji(for label: String) -> String {
        switch label {
        case "Apex":    return "👑"
        case "High":    return "💎"
        case "Notable": return "💫"
        case "Solid":   return "🌟"
        default:        return ""
        }
    }
}

// MARK: - Hex initializer -------------------------------------------------

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let r, g, b, a: UInt64
        switch hex.count {
        case 6:
            (a, r, g, b) = (255, (int >> 16) & 0xFF, (int >> 8) & 0xFF, int & 0xFF)
        case 8:
            (a, r, g, b) = ((int >> 24) & 0xFF, (int >> 16) & 0xFF, (int >> 8) & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}