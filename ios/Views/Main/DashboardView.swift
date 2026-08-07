import SwiftUI

/// Screen 7 — Home / Dashboard (first tab).
///
/// Psychology: Daily motivation + habit reinforcement.
/// Shows streak, today's tasks, and quick actions.
struct DashboardView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var viewModel = DashboardViewModel()
    @State private var showCamera = false

    var body: some View {
        NavigationStack {
            ZStack {
                LXColor.black.ignoresSafeArea()

                if viewModel.isLoading && viewModel.data == nil {
                    VStack(spacing: 16) {
                        ProgressView().tint(LXColor.gold)
                        Text("Loading...")
                            .lxBody()
                            .foregroundColor(LXColor.white)
                    }
                } else {
                    ScrollView {
                        VStack(spacing: 24) {
                            // Header
                            HStack {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("Welcome back")
                                        .lxCaption()
                                        .foregroundColor(LXColor.white.opacity(0.5))
                                    Text(userFirstName)
                                        .lxH1()
                                        .foregroundColor(LXColor.white)
                                }
                                Spacer()
                                Button(action: { showCamera = true }) {
                                    Image(systemName: "camera.fill")
                                        .font(.system(size: 20))
                                        .foregroundColor(LXColor.gold)
                                        .padding(12)
                                        .background(LXColor.deepNavy)
                                        .clipShape(Circle())
                                }
                            }
                            .padding(.horizontal, LXConstants.standardPadding)
                            .padding(.top, 16)

                            // Streak card
                            if let data = viewModel.data {
                                HStack(spacing: 16) {
                                    // Streak
                                    VStack(spacing: 4) {
                                        Text("\(data.currentStreak)")
                                            .font(.system(size: 40, weight: .bold, design: .rounded))
                                            .foregroundColor(LXColor.gold)
                                        Text("day streak")
                                            .lxCaption()
                                            .foregroundColor(LXColor.white.opacity(0.5))
                                    }
                                    .frame(maxWidth: .infinity)
                                    .padding()
                                    .background(LXColor.deepNavy)
                                    .cornerRadius(LXConstants.cornerRadius)

                                    // Score
                                    VStack(spacing: 4) {
                                        if let currentScore = data.currentScore {
                                            Text(String(format: "%.0f", currentScore))
                                                .font(.system(size: 40, weight: .bold, design: .rounded))
                                                .foregroundColor(LXColor.gold)
                                        } else {
                                            Text("--")
                                                .font(.system(size: 40, weight: .bold))
                                                .foregroundColor(LXColor.white.opacity(0.3))
                                        }
                                        Text("score")
                                            .lxCaption()
                                            .foregroundColor(LXColor.white.opacity(0.5))
                                    }
                                    .frame(maxWidth: .infinity)
                                    .padding()
                                    .background(LXColor.deepNavy)
                                    .cornerRadius(LXConstants.cornerRadius)
                                }
                                .padding(.horizontal, LXConstants.standardPadding)

                                // Score delta
                                if let delta = viewModel.scoreDelta {
                                    HStack {
                                        Image(systemName: delta >= 0 ? "arrow.up.right" : "arrow.down.right")
                                        Text(viewModel.scoreDeltaText)
                                    }
                                    .lxCaption()
                                    .foregroundColor(delta >= 0 ? LXColor.green : LXColor.red)
                                    .padding(.horizontal, LXConstants.standardPadding)
                                }

                                // Today's tasks
                                if !data.tasksToday.isEmpty {
                                    VStack(alignment: .leading, spacing: 12) {
                                        Text("TODAY'S TASKS")
                                            .lxCaption()
                                            .foregroundColor(LXColor.gold.opacity(0.7))

                                        ForEach(data.tasksToday) { task in
                                            HStack(spacing: 12) {
                                                Image(systemName: task.isCompleted ? "checkmark.circle.fill" : "circle")
                                                    .foregroundColor(task.isCompleted ? LXColor.green : LXColor.white.opacity(0.3))
                                                VStack(alignment: .leading, spacing: 2) {
                                                    Text(task.label)
                                                        .lxBody()
                                                        .foregroundColor(LXColor.white)
                                                    Text(task.timeOfDay)
                                                        .lxCaption()
                                                        .foregroundColor(LXColor.white.opacity(0.5))
                                                }
                                                Spacer()
                                            }
                                            .padding()
                                            .background(LXColor.deepNavy)
                                            .cornerRadius(LXConstants.cornerRadius)
                                        }
                                    }
                                    .padding(.horizontal, LXConstants.standardPadding)
                                }

                                // Milestones
                                if !data.milestones.isEmpty {
                                    VStack(alignment: .leading, spacing: 12) {
                                        Text("MILESTONES")
                                            .lxCaption()
                                            .foregroundColor(LXColor.gold.opacity(0.7))

                                        ForEach(data.milestones) { milestone in
                                            HStack(spacing: 12) {
                                                Image(systemName: milestone.isCompleted ? "trophy.fill" : "trophy")
                                                    .foregroundColor(milestone.isCompleted ? LXColor.gold : LXColor.white.opacity(0.3))
                                                VStack(alignment: .leading, spacing: 2) {
                                                    Text(milestone.label)
                                                        .lxBody()
                                                        .foregroundColor(LXColor.white)
                                                    Text("Day \(milestone.day)")
                                                        .lxCaption()
                                                        .foregroundColor(LXColor.white.opacity(0.5))
                                                }
                                                Spacer()
                                            }
                                            .padding()
                                            .background(LXColor.deepNavy)
                                            .cornerRadius(LXConstants.cornerRadius)
                                        }
                                    }
                                    .padding(.horizontal, LXConstants.standardPadding)
                                }

                                // Score history
                                if !data.scoreHistory.isEmpty {
                                    VStack(alignment: .leading, spacing: 12) {
                                        Text("SCORE HISTORY")
                                            .lxCaption()
                                            .foregroundColor(LXColor.gold.opacity(0.7))

                                        HStack(alignment: .bottom, spacing: 4) {
                                            ForEach(data.scoreHistory.suffix(14)) { entry in
                                                VStack {
                                                    Spacer()
                                                    RoundedRectangle(cornerRadius: 3)
                                                        .fill(LXColor.gold)
                                                        .frame(width: 20, height: max(4, CGFloat(entry.score / 100) * 100))
                                                    Text("\(Calendar.current.component(.day, from: entry.date))")
                                                        .lxCaption()
                                                        .foregroundColor(LXColor.white.opacity(0.4))
                                                        .font(.system(size: 8))
                                                }
                                            }
                                        }
                                        .frame(height: 120)
                                        .padding()
                                        .background(LXColor.deepNavy)
                                        .cornerRadius(LXConstants.cornerRadius)
                                    }
                                    .padding(.horizontal, LXConstants.standardPadding)
                                }
                            }

                            Spacer().frame(height: 40)
                        }
                    }
                }
            }
            .onAppear { viewModel.load(appState: appState) }
            .sheet(isPresented: $showCamera) {
                CameraView()
            }
        }
    }

    private var userFirstName: String {
        appState.user?.username ?? "Maxxer"
    }
}

// MARK: - Preview ----------------------------------------------------------

#Preview {
    DashboardView()
        .environmentObject(AppState())
}