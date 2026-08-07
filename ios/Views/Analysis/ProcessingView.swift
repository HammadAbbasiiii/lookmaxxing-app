import SwiftUI

/// Screen 4 — Loading / processing state.
///
/// Psychology: Show progress, not emptiness.
/// Animated facts reduce perceived wait time.
struct ProcessingView: View {
    @EnvironmentObject var appState: AppState
    @State private var factIndex = 0
    @State private var progress = 0.0
    @State private var navigateToScore = false
    private let timer = Timer.publish(every: 2.5, on: .main, in: .common).autoconnect()

    var body: some View {
        ZStack {
            LXColor.black.ignoresSafeArea()

            VStack(spacing: 40) {
                Spacer()

                // Animated spinner
                ZStack {
                    Circle()
                        .strokeBorder(LXColor.gold.opacity(0.2), lineWidth: 4)
                        .frame(width: 160, height: 160)

                    Circle()
                        .trim(from: 0, to: progress)
                        .stroke(LXColor.gold, style: StrokeStyle(lineWidth: 4, lineCap: .round))
                        .frame(width: 160, height: 160)
                        .rotationEffect(.degrees(-90))
                        .animation(.linear(duration: 1), value: progress)

                    Image(systemName: "sparkles")
                        .font(.system(size: 44))
                        .foregroundColor(LXColor.gold)
                }

                Text("Analyzing your photo...")
                    .lxH2()
                    .foregroundColor(LXColor.white)

                Text(ProcessingFact.random())
                    .lxCaption()
                    .foregroundColor(LXColor.white.opacity(0.6))
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, LXConstants.standardPadding)
                    .id(factIndex)  // forces transition
                    .transition(.asymmetric(insertion: .move(edge: .trailing), removal: .move(edge: .leading)))
                    .animation(.easeInOut(duration: 0.5), value: factIndex)

                // Upload error
                if let err = appState.uploadError {
                    Text(err)
                        .lxCaption()
                        .foregroundColor(LXColor.red)
                        .padding()
                        Button("Retry") { /* back to camera */ }
                        .lxBody()
                        .foregroundColor(LXColor.gold)
                }

                Spacer()
            }
            .onReceive(timer) { _ in
                factIndex += 1
                progress = min(0.95, progress + 0.12)
            }
            .onChange(of: appState.currentScore) { score in
                if score != nil { navigateToScore = true }
            }
        }
        .fullScreenCover(isPresented: $navigateToScore) {
            ScoreView()
        }
    }
}

// MARK: - Score (Results) View ---------------------------------------------

/// Screen 5 — The "aha!" moment.
///
/// Psychology: Satisfaction + aspiration.
/// Show score clearly, then immediately suggest a path forward.
struct ScoreView: View {
    @EnvironmentObject var appState: AppState
    @State private var animateScore = false
    @State private var navigateToPlan = false

    var body: some View {
        NavigationStack {
            ZStack {
                LXColor.black.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 32) {
                        // Title
                        Text("Your LookMaxx Score")
                            .lxH2()
                            .foregroundColor(LXColor.white)
                            .padding(.top, 60)

                        // Score circle
                        ZStack {
                            Circle()
                                .strokeBorder(LXColor.gold.opacity(0.3), lineWidth: 6)
                                .frame(width: 200, height: 200)

                            Circle()
                                .trim(from: 0, to: animateScore ? scorePercent : 0)
                                .stroke(LXColor.gold, style: StrokeStyle(lineWidth: 6, lineCap: .round))
                                .frame(width: 200, height: 200)
                                .rotationEffect(.degrees(-90))
                                .animation(.easeOut(duration: 1.5), value: animateScore)

                            VStack(spacing: 4) {
                                Text(String(format: "%.0f", appState.currentScore?.overallScore ?? 0))
                                    .font(.system(size: 56, weight: .bold, design: .rounded))
                                    .foregroundColor(LXColor.gold)
                                Text("/ 100")
                                    .lxCaption()
                                    .foregroundColor(LXColor.white.opacity(0.5))
                            }
                        }

                        // Tier
                        if let tier = appState.currentScore?.tierLabel {
                            Text(tier.uppercased())
                                .font(LXFont.h3())
                                .foregroundColor(LXColor.gold)
                                .padding(.horizontal, 16)
                                .padding(.vertical, 6)
                                .background(LXColor.gold.opacity(0.15))
                                .cornerRadius(20)
                        }

                        // Category scores
                        if let categories = appState.currentScore?.categoryScores {
                            VStack(spacing: 12) {
                                Text("Category Breakdown")
                                    .lxH3()
                                    .foregroundColor(LXColor.white)

                                ForEach(categories.sorted(by: { $0.value > $1.value }), id: \.key) { key, value in
                                    HStack {
                                        Text(key.capitalized)
                                            .lxBody()
                                            .foregroundColor(LXColor.white)
                                        Spacer()
                                        Text(String(format: "%.1f", value))
                                            .lxBody()
                                            .foregroundColor(LXColor.gold)
                                    }
                                    .padding(.horizontal, LXConstants.standardPadding)
                                }
                            }
                            .padding()
                            .background(LXColor.deepNavy)
                            .cornerRadius(LXConstants.cornerRadius)
                            .padding(.horizontal, LXConstants.standardPadding)
                        }

                        // Strengths & Improvements
                        HStack(spacing: 16) {
                            // Strengths
                            VStack(alignment: .leading, spacing: 8) {
                                Text("💪 Strengths")
                                    .lxH3()
                                    .foregroundColor(LXColor.green)
                                ForEach(appState.currentScore?.strengths ?? [], id: \.self) { s in
                                    HStack(spacing: 6) {
                                        Circle().fill(LXColor.green).frame(width: 6, height: 6)
                                        Text(s).lxCaption().foregroundColor(LXColor.white)
                                    }
                                }
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding()
                            .background(LXColor.deepNavy)
                            .cornerRadius(LXConstants.cornerRadius)

                            // Improvements
                            VStack(alignment: .leading, spacing: 8) {
                                Text("🎯 Improve")
                                    .lxH3()
                                    .foregroundColor(LXColor.gold)
                                ForEach(appState.currentScore?.improvementAreas ?? [], id: \.self) { s in
                                    HStack(spacing: 6) {
                                        Circle().fill(LXColor.gold).frame(width: 6, height: 6)
                                        Text(s).lxCaption().foregroundColor(LXColor.white)
                                    }
                                }
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding()
                            .background(LXColor.deepNavy)
                            .cornerRadius(LXConstants.cornerRadius)
                        }
                        .padding(.horizontal, LXConstants.standardPadding)

                        // CTA
                        Button(action: { navigateToPlan = true }) {
                            HStack(spacing: 8) {
                                Text("📋")
                                Text("VIEW YOUR 90-DAY PLAN")
                                    .font(LXFont.h3())
                            }
                            .frame(maxWidth: .infinity)
                            .frame(height: LXConstants.buttonHeight)
                            .background(LXColor.gold)
                            .foregroundColor(LXColor.black)
                            .cornerRadius(LXConstants.cornerRadius)
                        }
                        .padding(.horizontal, LXConstants.standardPadding)

                        Spacer().frame(height: 40)
                    }
                }
            }
            .navigationDestination(isPresented: $navigateToPlan) {
                PlanView()
            }
            .onAppear { animateScore = true }
        }
    }

    private var scorePercent: Double {
        Double(appState.currentScore?.overallScore ?? 0) / 100.0
    }
}

// MARK: - Preview ----------------------------------------------------------

#Preview("Processing") {
    ProcessingView()
        .environmentObject(AppState())
}