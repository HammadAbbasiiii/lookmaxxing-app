import SwiftUI
import UIKit

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

// MARK: - Haptic feedback ----------------------------------------------------

/// Lightweight haptic helpers so every meaningful interaction gives physical
/// feedback. This "touch + reward" loop is core to retention.
enum Haptics {
    static func tap() {
        UIImpactFeedbackGenerator(style: .light).impactOccurred()
    }

    static func success() {
        UINotificationFeedbackGenerator().notificationOccurred(.success)
    }

    static func celebration() {
        UIImpactFeedbackGenerator(style: .heavy).impactOccurred()
        UINotificationFeedbackGenerator().notificationOccurred(.success)
    }

    static func warning() {
        UINotificationFeedbackGenerator().notificationOccurred(.warning)
    }
}

// MARK: - Spinner ring -------------------------------------------------------

/// A gold indeterminate spinner: a partial arc rotates around a faint full
/// circle, with an optional center icon. Used for all loading/waiting states.
struct LXSpinnerRing: View {
    var size: CGFloat = 100
    var lineWidth: CGFloat = 4
    var icon: String = "sparkles"

    @State private var spin = false

    var body: some View {
        ZStack {
            Circle()
                .stroke(LXColor.gold.opacity(0.18), lineWidth: lineWidth)

            Circle()
                .trim(from: 0, to: 0.8)
                .stroke(LXColor.gold, style: StrokeStyle(lineWidth: lineWidth, lineCap: .round))
                .rotationEffect(.degrees(spin ? 360 : 0))
                .animation(.linear(duration: 1).repeatForever(autoreverses: false), value: spin)

            Image(systemName: icon)
                .font(.system(size: size * 0.3))
                .foregroundColor(LXColor.gold)
        }
        .frame(width: size, height: size)
        .onAppear { spin = true }
    }
}

// MARK: - Glow orb -----------------------------------------------------------

/// A soft pulsing glow placed behind hero content (scores, onboarding).
struct GlowOrb: View {
    var color: Color = LXColor.gold
    var size: CGFloat = 140

    @State private var pulse = false

    var body: some View {
        Circle()
            .fill(color.opacity(0.35))
            .frame(width: size, height: size)
            .blur(radius: 28)
            .scaleEffect(pulse ? 1.35 : 0.9)
            .animation(LXAnimation.pulse, value: pulse)
            .onAppear { pulse = true }
    }
}

// MARK: - Streak flame -------------------------------------------------------

/// A flickering flame for the streak card — habit reinforcement visual.
struct StreakFlameView: View {
    var size: CGFloat = 40

    @State private var flicker = false

    var body: some View {
        Image(systemName: "flame.fill")
            .font(.system(size: size))
            .foregroundStyle(
                LinearGradient(
                    colors: [LXColor.gold, LXColor.amber, LXColor.red],
                    startPoint: .bottom,
                    endPoint: .top
                )
            )
            .scaleEffect(flicker ? 1.12 : 0.96)
            .animation(LXAnimation.pulse, value: flicker)
            .onAppear { flicker = true }
    }
}

// MARK: - Animated gradient background ---------------------------------------

/// A slow-moving dark gradient used behind hero / celebration screens so they
/// never feel like a flat black wall.
struct GoldGradientBackground: View {
    @State private var animate = false

    var body: some View {
        LinearGradient(
            colors: [LXColor.deepNavy, LXColor.darkPurple, LXColor.black],
            startPoint: animate ? .topLeading : .bottomTrailing,
            endPoint: animate ? .bottomTrailing : .topLeading
        )
        .ignoresSafeArea()
        .onAppear {
            withAnimation(.easeInOut(duration: 8).repeatForever(autoreverses: true)) {
                animate = true
            }
        }
    }
}

// MARK: - Confetti -----------------------------------------------------------

/// A continuous confetti rain used for milestone celebrations (score ≥ 85,
/// positive before/after trend). Deterministic per-particle motion keeps it
/// smooth and cheap to render.
struct ConfettiView: View {
    var particleCount: Int = 140
    var colors: [Color] = [LXColor.gold, LXColor.amber, LXColor.teal,
                           LXColor.green, LXColor.goldGlow, LXColor.red]

    @State private var start = Date()

    var body: some View {
        TimelineView(.animation) { timeline in
            Canvas { context, size in
                let elapsed = timeline.date.timeIntervalSince(start)

                for i in 0..<particleCount {
                    let f = CGFloat(i) / CGFloat(particleCount)

                    func rand(_ k: CGFloat) -> CGFloat {
                        abs(sin(f * 97.0 + k * 31.7) * 0.5 + 0.5)
                    }

                    let x0 = rand(1) * size.width
                    let speed = 60 + rand(2) * 140
                    let cycle = 2.0 + rand(3) * 2.5
                    let phase = rand(4) * cycle
                    let t = (CGFloat(elapsed) + phase).truncatingRemainder(dividingBy: cycle) / cycle

                    let x = (x0 + t * speed).truncatingRemainder(dividingBy: size.width + 40) - 20
                    let y = -30 + t * (size.height + 60)

                    let w: CGFloat = 7
                    let h: CGFloat = 13
                    let color = colors[i % colors.count]
                    let rotation = Angle.degrees(Double(t * 360 + f * 180))

                    var ctx = context
                    ctx.translateBy(x: x, y: y)
                    ctx.rotate(by: rotation)
                    let rect = CGRect(x: -w / 2, y: -h / 2, width: w, height: h)
                    ctx.fill(Path(roundedRect: rect, cornerRadius: 1.5),
                             with: .color(color.opacity(0.9)))
                }
            }
        }
        .ignoresSafeArea()
        .allowsHitTesting(false)
    }
}

// MARK: - Pressable button style ----------------------------------------------

/// A tactile button style: scales down slightly on press and fires a light
/// haptic, so every tap feels responsive (game-like "juice").
struct PressableButtonStyle: ButtonStyle {
    var scale: CGFloat = 0.97

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? scale : 1)
            .opacity(configuration.isPressed ? 0.9 : 1)
            .animation(.spring(response: 0.3, dampingFraction: 0.6), value: configuration.isPressed)
            .onChange(of: configuration.isPressed) { pressed in
                if pressed { Haptics.tap() }
            }
    }
}