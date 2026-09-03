import SwiftUI

/// Motivation engine for LookMaxx AI.
///
/// Keeps users engaged during waits ("anticipatory design") and celebrates
/// milestones. Each bank is copy for a specific emotional beat, so the app
/// never shows a boring "Loading..." — it speaks to the user's ambition.
enum Motivation {

    // ── Waiting (analysis / loading) ─────────────────────────
    static let waitingQuotes: [String] = [
        "Greatness is built one day at a time.",
        "Your future self is watching — make them proud.",
        "Every rep, every night of sleep, every good choice compounds.",
        "Discipline is choosing what you want most over what you want now.",
        "You don't have to be perfect — just better than yesterday.",
        "Small daily improvements are the key to staggering results.",
        "The grind you avoid today is the progress you'll miss tomorrow.",
        "Consistency beats intensity.",
        "Your only competition is who you were yesterday.",
        "Level up quietly — let the results make the noise."
    ]

    // ── High-score / milestone celebration ──────────────────
    static let levelUpQuotes: [String] = [
        "Elite energy detected. Keep ascending.",
        "Apex behavior. This is only the beginning.",
        "You just leveled up. Stay locked in.",
        "The mirror is noticing. Keep going.",
        "Momentum secured — don't let it cool down."
    ]

    // ── Daily tips ──────────────────────────────────────────
    static let dailyTips: [String] = [
        "Drink a glass of water right now — hydration shows on your skin.",
        "Sleep 7–9 hours tonight. It's the cheapest looksmaxxing tool.",
        "Good tongue posture can sharpen your jawline over time.",
        "Sunscreen daily — most visible aging comes from UV.",
        "Fix your posture: shoulders back, chin tucked. Instant +1.",
        "Train your neck — a thicker neck frames your face.",
        "Cardio 3x a week improves skin blood flow and glow."
    ]

    // ── Streaks ─────────────────────────────────────────────
    static let streakMessages: [String] = [
        "Day by day, compounding wins.",
        "Don't break the chain.",
        "Momentum is your superpower."
    ]

    /// Returns a random item from a bank (falls back to the first item).
    static func random(_ bank: [String]) -> String {
        bank.randomElement() ?? bank[0]
    }

    /// Returns a motivational line appropriate for a given score.
    static func line(for score: Double) -> String {
        switch score {
        case 85...: return levelUpQuotes.randomElement() ?? levelUpQuotes[0]
        case 80..<85: return "High-tier performance. Push for Apex."
        case 70..<80: return "Solid foundation — consistency will take you higher."
        default: return "Every expert was once a beginner. Start climbing."
        }
    }
}

// MARK: - Rotating motivational quote ----------------------------------------

/// A quote that cross-fades / slides to the next one on a timer.
/// Uses the serif italic `LXFont.motivational()` so motivational copy feels
/// distinct from UI text — a deliberate emotional cue.
struct MotivationalQuoteView: View {
    var quotes: [String] = Motivation.waitingQuotes
    var interval: TimeInterval = 3.5
    var color: Color = LXColor.gold.opacity(0.9)

    @State private var index = 0
    @State private var timer: Timer?

    var body: some View {
        Text(quotes.isEmpty ? "" : quotes[index])
            .font(LXFont.motivational())
            .foregroundColor(color)
            .multilineTextAlignment(.center)
            .id(index)
            .transition(.asymmetric(
                insertion: .move(edge: .trailing).combined(with: .opacity),
                removal: .move(edge: .leading).combined(with: .opacity)
            ))
            .onAppear {
                timer?.invalidate()
                let count = max(quotes.count, 1)
                timer = Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { _ in
                    withAnimation(LXAnimation.fadeIn) {
                        index = (index + 1) % count
                    }
                }
            }
            .onDisappear { timer?.invalidate() }
    }
}

// MARK: - Reusable loading state ---------------------------------------------

/// A polished, motivational loading state. Replaces every bare
/// `ProgressView() + "Loading..."` in the app with a spinning gold ring,
/// a title, and a rotating motivational quote.
struct LXLoadingView: View {
    var title: String = "Loading"
    var quotes: [String] = Motivation.waitingQuotes

    var body: some View {
        VStack(spacing: 24) {
            LXSpinnerRing(size: 96)

            Text(title)
                .lxH3()
                .foregroundColor(LXColor.white)

            MotivationalQuoteView(quotes: quotes)
                .padding(.horizontal, LXConstants.standardPadding)
        }
        .padding(.horizontal, LXConstants.standardPadding)
    }
}

// MARK: - Shimmer skeleton ----------------------------------------------------

/// A shimmering placeholder card used while content is loading. The sweeping
/// highlight signals activity and makes waits feel faster than a static block.
struct LXSkeletonCard: View {
    var height: CGFloat = 84
    var cornerRadius: CGFloat = LXConstants.cornerRadius

    @State private var shimmer = false

    var body: some View {
        RoundedRectangle(cornerRadius: cornerRadius)
            .fill(LXColor.deepNavy)
            .frame(height: height)
            .overlay(
                LinearGradient(
                    colors: [.clear, LXColor.white.opacity(0.10), .clear],
                    startPoint: .leading,
                    endPoint: .trailing
                )
                .frame(width: 180)
                .offset(x: shimmer ? 340 : -180)
                .blendMode(.plusLighter)
            )
            .clipShape(RoundedRectangle(cornerRadius: cornerRadius))
            .onAppear {
                withAnimation(.linear(duration: 1.4).repeatForever(autoreverses: false)) {
                    shimmer = true
                }
            }
    }
}
