import SwiftUI

/// Animation presets for LookMaxx AI.
///
/// Every transition must be smooth (60 fps target).
/// Never use the default `.default` animation — always choose a preset.
enum LXAnimation {
    static let fadeIn       = Animation.easeOut(duration: 0.35)
    static let countUp      = Animation.spring(response: 0.8, dampingFraction: 0.7, blendDuration: 0)
    static let pulse        = Animation.easeInOut(duration: 1.5).repeatForever(autoreverses: true)
    static let bounce       = Animation.interpolatingSpring(stiffness: 170, damping: 15)
    static let smoothScroll = Animation.easeInOut(duration: 0.25)
    static let celebration  = Animation.spring(response: 0.6, dampingFraction: 0.5, blendDuration: 0.2)
    static let navTransition = Animation.easeInOut(duration: 0.3)
}

// MARK: - Sparkle effect (high scores ≥ 85) --------------------------------

struct SparkleView: View {
    @State private var scale: CGFloat = 0
    let score: Double

    var body: some View {
        if score >= 85 {
            Circle()
                .fill(LXColor.gold.opacity(0.3))
                .frame(width: 120, height: 120)
                .scaleEffect(scale)
                .blur(radius: 20)
                .onAppear {
                    withAnimation(Animation.easeOut(duration: 1.2).repeatForever(autoreverses: true)) {
                        scale = 1.5
                    }
                }
        }
    }
}

// MARK: - Progress bar animator --------------------------------------------

struct LXProgressBar: View {
    let progress: Double  // 0…1
    let color: Color
    var height: CGFloat = 8

    @State private var animated: CGFloat = 0

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Capsule()
                    .fill(Color.white.opacity(0.1))
                    .frame(height: height)
                Capsule()
                    .fill(color)
                    .frame(width: geo.size.width * animated, height: height)
                    .animation(.easeInOut(duration: 1.0), value: animated)
            }
        }
        .frame(height: height)
        .onAppear { animated = CGFloat(progress) }
        .onChange(of: progress) { new in
            withAnimation(.easeInOut(duration: 1.0)) { animated = CGFloat(new) }
        }
    }
}

// MARK: - Count-up text ----------------------------------------------------

struct CountUpText: View {
    let target: Double
    let suffix: String
    var decimalPlaces: Int = 1

    @State private var current: Double = 0

    var body: some View {
        Text(String(format: "%.\(decimalPlaces)f%@", current, suffix))
            .onAppear { animateCountUp() }
    }

    private func animateCountUp() {
        let steps = 30
        let increment = target / Double(steps)
        var i = 0
        Timer.scheduledTimer(withTimeInterval: 0.03, repeats: true) { timer in
            i += 1
            if i >= steps {
                current = target
                timer.invalidate()
            } else {
                current += increment
            }
        }
    }
}