import SwiftUI

/// Typography hierarchy for LookMaxx AI.
///
/// Always use San Francisco — Apple's native, clean, commanding typeface.
///
/// ## Hierarchy
/// ```
/// H1:  48–72 pt  Bold      Scores ("84.6")
/// H2:  28–34 pt  Bold      Screen titles ("Your Appeal Score")
/// H3:  20–24 pt  Semibold  Section headers ("Your Strengths")
/// Body: 16–17 pt Regular   Descriptions, task lists
/// Cap: 13–14 pt  Regular   Helper text, timestamps
/// ```
enum LXFont {

    // ── Weights ──────────────────────────────────────────────
    static func h1() -> Font { .system(size: 64, weight: .bold, design: .default) }
    static func h2() -> Font { .system(size: 28, weight: .bold, design: .default) }
    static func h3() -> Font { .system(size: 20, weight: .semibold, design: .default) }
    static func body() -> Font { .system(size: 16, weight: .regular, design: .default) }
    static func caption() -> Font { .system(size: 13, weight: .regular, design: .default) }
    static func motivational() -> Font { .system(size: 16, weight: .regular, design: .serif).italic() }

    // ── Dynamic sizing ──────────────────────────────────────
    /// Returns H1 scaled by `min(scale, 1.2)` relative to the baseline 64 pt.
    static func h1(dynamic: CGFloat) -> Font {
        .system(size: 64 * min(dynamic, 1.2), weight: .bold, design: .default)
    }

    static func boldCaption() -> Font { .system(size: 13, weight: .semibold, design: .default) }

    // ── Extended typography scale ───────────────────────────
    static func hero() -> Font { .system(size: 64, weight: .bold, design: .default) }
    static func bodyBold() -> Font { .system(size: 17, weight: .semibold, design: .default) }
    static func captionBold() -> Font { .system(size: 13, weight: .semibold, design: .default) }
    static func button() -> Font { .system(size: 17, weight: .bold, design: .default) }
}

// MARK: - Convenience ViewModifiers ---------------------------------------

struct LXH1Modifier: ViewModifier {
    func body(content: Content) -> some View { content.font(LXFont.h1()) }
}

struct LXH2Modifier: ViewModifier {
    func body(content: Content) -> some View { content.font(LXFont.h2()) }
}

struct LXH3Modifier: ViewModifier {
    func body(content: Content) -> some View { content.font(LXFont.h3()) }
}

struct LXBodyModifier: ViewModifier {
    func body(content: Content) -> some View { content.font(LXFont.body()) }
}

struct LXCaptionModifier: ViewModifier {
    func body(content: Content) -> some View { content.font(LXFont.caption()) }
}

struct LXHeroModifier: ViewModifier {
    func body(content: Content) -> some View { content.font(LXFont.hero()) }
}

struct LXBodyBoldModifier: ViewModifier {
    func body(content: Content) -> some View { content.font(LXFont.bodyBold()) }
}

struct LXCaptionBoldModifier: ViewModifier {
    func body(content: Content) -> some View { content.font(LXFont.captionBold()) }
}

struct LXButtonTextModifier: ViewModifier {
    func body(content: Content) -> some View { content.font(LXFont.button()).kerning(0.5) }
}

// MARK: - View extensions -------------------------------------------------

extension View {
    func lxH1() -> some View { modifier(LXH1Modifier()) }
    func lxH2() -> some View { modifier(LXH2Modifier()) }
    func lxH3() -> some View { modifier(LXH3Modifier()) }
    func lxBody() -> some View { modifier(LXBodyModifier()) }
    func lxCaption() -> some View { modifier(LXCaptionModifier()) }
    func lxHero() -> some View { modifier(LXHeroModifier()) }
    func lxBodyBold() -> some View { modifier(LXBodyBoldModifier()) }
    func lxCaptionBold() -> some View { modifier(LXCaptionBoldModifier()) }
    func lxButtonText() -> some View { modifier(LXButtonTextModifier()) }
}
