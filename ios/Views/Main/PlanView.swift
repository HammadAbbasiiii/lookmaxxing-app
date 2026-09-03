import SwiftUI

/// Screen 6 — 90-day transformation plan.
///
/// Psychology: Commitment + structure.
/// Phase progress gives immediate next action, not just a score.
struct PlanView: View {
    @EnvironmentObject var appState: AppState
    @State private var expandedPhaseId: String?
    @State private var loadingStep = 0
    private let loadingSteps = [
        "Analyzing your facial features...",
        "Generating your personalized plan...",
        "Almost ready..."
    ]
    private let stepTimer = Timer.publish(every: 4, on: .main, in: .common).autoconnect()

    var body: some View {
        NavigationStack {
            ZStack {
                LXColor.black.ignoresSafeArea()

                if case .loading = appState.planState, appState.currentPlan == nil {
                    VStack(spacing: 24) {
                        LXSpinnerRing(size: 96)
                        Text(loadingSteps[min(loadingStep, loadingSteps.count - 1)])
                            .lxH3()
                            .foregroundColor(LXColor.white)
                            .multilineTextAlignment(.center)
                            .animation(LXAnimation.fadeIn, value: loadingStep)
                        MotivationalQuoteView(interval: 4)
                            .padding(.horizontal, LXConstants.standardPadding)
                        Text("This can take up to 30 seconds the first time.")
                            .lxCaption()
                            .foregroundColor(LXColor.white.opacity(0.5))
                    }
                    .padding(.horizontal, LXConstants.standardPadding)
                } else if let plan = appState.currentPlan {
                    ScrollView {
                        VStack(spacing: 24) {
                            Text("Your 90-Day\nTransformation")
                                .lxH2()
                                .foregroundColor(LXColor.white)
                                .padding(.top, 20)

                            // Overall progress
                            VStack(spacing: 8) {
                                Text("Day \(plan.currentDay) of 90")
                                    .lxH3()
                                    .foregroundColor(LXColor.gold)

                                GeometryReader { geo in
                                    ZStack(alignment: .leading) {
                                        RoundedRectangle(cornerRadius: 6)
                                            .fill(LXColor.gold.opacity(0.2))
                                            .frame(height: 8)
                                        RoundedRectangle(cornerRadius: 6)
                                            .fill(LXColor.gold)
                                            .frame(width: geo.size.width * dayProgress(plan), height: 8)
                                            .animation(.easeInOut(duration: 0.8), value: plan.currentDay)
                                    }
                                }
                                .frame(height: 8)
                                .padding(.horizontal, LXConstants.standardPadding)
                            }

                            // Phases
                            ForEach(plan.phases) { phase in
                                PhaseCard(phase: phase, isExpanded: expandedPhaseId == phase.id) {
                                    withAnimation(.spring()) {
                                        expandedPhaseId = expandedPhaseId == phase.id ? nil : phase.id
                                    }
                                } onToggleTask: { task in
                                    Task {
                                        await appState.markTaskComplete(taskID: task.id)
                                    }
                                }
                            }

                            // Error handling
                            if case .error(let err) = appState.planState {
                                Text(err)
                                    .lxCaption()
                                    .foregroundColor(LXColor.red)
                                    .padding()
                            }

                            Spacer().frame(height: 40)
                        }
                    }
                    .refreshable {
                        await appState.fetchPlan()
                    }
                } else {
                    // No plan yet, or an error occurred while fetching
                    VStack(spacing: 16) {
                        if case .error(let err) = appState.planState {
                            Text(err)
                                .lxBody()
                                .foregroundColor(LXColor.red)
                                .multilineTextAlignment(.center)
                        }
                        Text("No plan yet")
                            .lxH3()
                            .foregroundColor(LXColor.white.opacity(0.5))
                        Text("Take a photo to get your personalized plan")
                            .lxBody()
                            .foregroundColor(LXColor.white.opacity(0.4))
                            .multilineTextAlignment(.center)
                        Button("Retry") {
                            Task { await appState.fetchPlan() }
                        }
                        .lxBody()
                        .foregroundColor(LXColor.gold)
                    }
                    .padding(.horizontal, LXConstants.standardPadding)
                }
            }
            .onAppear {
                loadingStep = 0
                if appState.currentPlan == nil {
                    Task { await appState.fetchPlan() }
                }
            }
            .onReceive(stepTimer) { _ in
                if case .loading = appState.planState {
                    loadingStep = min(loadingStep + 1, loadingSteps.count - 1)
                }
            }
        }
    }

    private func dayProgress(_ plan: Plan) -> Double {
        min(1.0, Double(plan.currentDay) / 90.0)
    }
}

// MARK: - Phase Card -------------------------------------------------------

struct PhaseCard: View {
    let phase: Phase
    let isExpanded: Bool
    let onToggle: () -> Void
    let onToggleTask: (PlanTask) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Button(action: onToggle) {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Phase \(phase.order)")
                            .lxCaption()
                            .foregroundColor(LXColor.gold.opacity(0.7))
                        Text(phase.title)
                            .lxH3()
                            .foregroundColor(LXColor.white)
                    }
                    Spacer()
                    VStack(alignment: .trailing, spacing: 4) {
                        Text("\(phase.weeks)")
                            .lxCaption()
                            .foregroundColor(LXColor.white.opacity(0.5))
                        Text("\(completedTasks)/\(phase.tasks.count) tasks")
                            .lxCaption()
                            .foregroundColor(LXColor.gold)
                    }
                    Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                        .foregroundColor(LXColor.gold.opacity(0.6))
                        .padding(.leading, 8)
                }
                .padding()
                .background(LXColor.deepNavy)
                .cornerRadius(LXConstants.cornerRadius)
            }

            if isExpanded {
                VStack(alignment: .leading, spacing: 12) {
                    Text(phase.description)
                        .lxCaption()
                        .foregroundColor(LXColor.white.opacity(0.7))
                        .padding(.top, 4)

                    ForEach(phase.tasks) { task in
                        TaskRow(task: task, onToggle: { onToggleTask(task) })
                    }
                }
                .padding()
                .background(LXColor.deepNavy.opacity(0.5))
                .cornerRadius(LXConstants.cornerRadius)
            }
        }
        .padding(.horizontal, LXConstants.standardPadding)
    }

    private var completedTasks: Int {
        phase.tasks.filter(\.isCompleted).count
    }
}

// MARK: - Task Row ---------------------------------------------------------

struct TaskRow: View {
    let task: PlanTask
    let onToggle: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            Button(action: onToggle) {
                Image(systemName: task.isCompleted ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 22))
                    .foregroundColor(task.isCompleted ? LXColor.green : LXColor.white.opacity(0.3))
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(task.label)
                    .lxBody()
                    .foregroundColor(LXColor.white)
                    .strikethrough(task.isCompleted)
                Text(task.timeOfDay)
                    .lxCaption()
                    .foregroundColor(LXColor.white.opacity(0.5))
            }

            Spacer()
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Preview ----------------------------------------------------------

#Preview {
    PlanView()
        .environmentObject(AppState())
}