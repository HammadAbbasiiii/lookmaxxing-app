import SwiftUI

/// Score History & Progress Photos — sub-screens reachable from Profile.
///
/// Both are backed by existing `/progress/*` endpoints:
/// - `GET /progress/history` → score trend over time (chart data).
/// - `GET /progress/photos`  → baseline + weekly check-in photos.
/// These screens replace the "coming soon" placeholders in `ProfileView`.

// MARK: - Score History ------------------------------------------------------

struct ScoreHistoryView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        ZStack {
            LXColor.black.ignoresSafeArea()

            if let data = appState.scoreHistory {
                if data.hasData, !data.history.isEmpty {
                    ScrollView {
                        VStack(spacing: 24) {
                            header(data)
                            chartCard(data)
                            historyList(data)
                            Spacer().frame(height: 40)
                        }
                        .padding(.top, 20)
                    }
                    .refreshable { await appState.fetchScoreHistory() }
                } else {
                    emptyView
                }
            } else if case .error(let err) = appState.scoreHistoryState {
                errorView(err)
            } else {
                ProgressView().tint(LXColor.gold)
            }
        }
        .navigationTitle("Score History")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            if appState.scoreHistory == nil {
                Task { await appState.fetchScoreHistory() }
            }
        }
    }

    private var emptyView: some View {
        VStack(spacing: 16) {
            Image(systemName: "chart.xyaxis.line")
                .font(.system(size: 40))
                .foregroundColor(LXColor.gold.opacity(0.5))
            Text("No score history yet")
                .lxH3()
                .foregroundColor(LXColor.white.opacity(0.6))
            Text("Complete a photo analysis to start tracking your score over time.")
                .lxCaption()
                .foregroundColor(LXColor.white.opacity(0.4))
                .multilineTextAlignment(.center)
        }
        .padding()
    }

    private func errorView(_ message: String) -> some View {
        VStack(spacing: 16) {
            Text("Couldn't load your history")
                .lxH3()
                .foregroundColor(LXColor.white)
            Text(message)
                .lxCaption()
                .foregroundColor(LXColor.white.opacity(0.5))
            Button("Retry") {
                Task { await appState.fetchScoreHistory() }
            }
            .lxBody()
            .foregroundColor(LXColor.gold)
        }
        .padding()
    }

    private func header(_ data: ScoreHistoryResponse) -> some View {
        VStack(spacing: 8) {
            Text(data.currentScore.map { String(format: "%.0f", $0) } ?? "—")
                .font(.system(size: 56, weight: .bold, design: .rounded))
                .foregroundColor(LXColor.gold)
            Text("Current Score")
                .lxCaption()
                .foregroundColor(LXColor.white.opacity(0.5))

            if let improvement = data.improvement {
                HStack(spacing: 6) {
                    Image(systemName: improvement >= 0 ? "arrow.up.right" : "arrow.down.right")
                    Text("\(improvement >= 0 ? "+" : "")\(String(format: "%.1f", improvement)) since baseline")
                }
                .lxCaption()
                .foregroundColor(improvement >= 0 ? LXColor.green : LXColor.red)
            }
        }
    }

    private func chartCard(_ data: ScoreHistoryResponse) -> some View {
        let scores = data.history.compactMap { $0.score }
        return VStack(alignment: .leading, spacing: 12) {
            Text("TREND")
                .lxCaption()
                .foregroundColor(LXColor.gold.opacity(0.7))

            ScoreLineChart(points: scores)
                .frame(height: 180)

            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("BASELINE")
                        .lxCaption()
                        .foregroundColor(LXColor.white.opacity(0.4))
                    Text(data.initialScore.map { String(format: "%.0f", $0) } ?? "—")
                        .lxH3()
                        .foregroundColor(LXColor.white)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 2) {
                    Text("CURRENT")
                        .lxCaption()
                        .foregroundColor(LXColor.white.opacity(0.4))
                    Text(data.currentScore.map { String(format: "%.0f", $0) } ?? "—")
                        .lxH3()
                        .foregroundColor(LXColor.gold)
                }
            }
        }
        .padding()
        .background(LXColor.deepNavy)
        .cornerRadius(LXConstants.cornerRadius)
        .padding(.horizontal, LXConstants.standardPadding)
    }

    private func historyList(_ data: ScoreHistoryResponse) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("CHECK-INS")
                .lxCaption()
                .foregroundColor(LXColor.gold.opacity(0.7))
                .padding(.horizontal, LXConstants.standardPadding)

            VStack(spacing: 0) {
                ForEach(data.history.indices, id: \.self) { index in
                    let point = data.history[index]

                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(point.isBaseline == true ? "Baseline" : "Week \(point.weekNumber ?? index + 1)")
                                .lxBody()
                                .foregroundColor(LXColor.white)
                            if let date = point.date {
                                Text(lxFriendlyDate(date))
                                    .lxCaption()
                                    .foregroundColor(LXColor.white.opacity(0.4))
                            }
                        }
                        Spacer()
                        Text(point.score.map { String(format: "%.1f", $0) } ?? "—")
                            .font(.system(size: 18, weight: .bold, design: .rounded))
                            .foregroundColor(LXColor.gold)
                    }
                    .padding()

                    if index < data.history.count - 1 {
                        Divider().background(LXColor.white.opacity(0.1))
                    }
                }
            }
            .background(LXColor.deepNavy)
            .cornerRadius(LXConstants.cornerRadius)
            .padding(.horizontal, LXConstants.standardPadding)
        }
    }
}


// MARK: - Progress Photos ----------------------------------------------------

struct ProgressPhotosView: View {
    @EnvironmentObject var appState: AppState
    @State private var showPhotoPicker = false
    @State private var showComparison = false
    @State private var showUploadError = false
    @State private var pickedImage: UIImage?

    private let columns = [
        GridItem(.flexible(), spacing: 12),
        GridItem(.flexible(), spacing: 12)
    ]

    var body: some View {
        ZStack {
            LXColor.black.ignoresSafeArea()

            if let data = appState.progressPhotos {
                if data.photos.isEmpty {
                    emptyView
                } else {
                    ScrollView {
                        VStack(spacing: 20) {
                            Text("\(data.total) photos")
                                .lxCaption()
                                .foregroundColor(LXColor.white.opacity(0.5))

                            if data.photos.count >= 2 {
                                Button {
                                    showComparison = true
                                } label: {
                                    HStack(spacing: 8) {
                                        Image(systemName: "rectangle.2.swap")
                                        Text("Compare Before & After")
                                    }
                                    .lxBody()
                                    .frame(maxWidth: .infinity)
                                    .frame(height: LXConstants.buttonHeight)
                                    .background(LXColor.deepNavy)
                                    .foregroundColor(LXColor.gold)
                                    .cornerRadius(LXConstants.cornerRadius)
                                }
                                .padding(.horizontal, LXConstants.standardPadding)
                            }

                            LazyVGrid(columns: columns, spacing: 12) {
                                ForEach(data.photos) { photo in
                                    photoCard(photo)
                                }
                            }
                            .padding(.horizontal, LXConstants.standardPadding)

                            Spacer().frame(height: 40)
                        }
                        .padding(.top, 16)
                    }
                    .refreshable { await appState.fetchProgressPhotos() }
                }
            } else if case .error(let err) = appState.progressPhotosState {
                VStack(spacing: 16) {
                    Text("Couldn't load your photos")
                        .lxH3()
                        .foregroundColor(LXColor.white)
                    Text(err)
                        .lxCaption()
                        .foregroundColor(LXColor.white.opacity(0.5))
                    Button("Retry") {
                        Task { await appState.fetchProgressPhotos() }
                    }
                    .lxBody()
                    .foregroundColor(LXColor.gold)
                }
                .padding()
            } else {
                ProgressView().tint(LXColor.gold)
            }
        }
        .navigationTitle("Progress Photos")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button {
                    showPhotoPicker = true
                } label: {
                    Image(systemName: "plus")
                        .foregroundColor(LXColor.gold)
                }
            }
        }
        .sheet(isPresented: $showPhotoPicker) {
            PHPickerSwiftUI(selectedImage: $pickedImage) { image in
                guard let image = image else { return }
                Task {
                    await appState.uploadProgressPhoto(image: image)
                    if appState.progressUploadError != nil {
                        showUploadError = true
                    }
                }
            }
        }
        .navigationDestination(isPresented: $showComparison) {
            ProgressComparisonView()
        }
        .alert("Couldn't upload photo", isPresented: $showUploadError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(appState.progressUploadError ?? "Please try again.")
        }
        .onAppear {
            if appState.progressPhotos == nil {
                Task { await appState.fetchProgressPhotos() }
            }
        }
    }

    private var emptyView: some View {
        VStack(spacing: 16) {
            Image(systemName: "photo.on.rectangle.angled")
                .font(.system(size: 40))
                .foregroundColor(LXColor.gold.opacity(0.5))
            Text("No progress photos yet")
                .lxH3()
                .foregroundColor(LXColor.white.opacity(0.6))
            Text("Upload your first photo to begin tracking your transformation.")
                .lxCaption()
                .foregroundColor(LXColor.white.opacity(0.4))
                .multilineTextAlignment(.center)

            Button {
                showPhotoPicker = true
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "plus")
                    Text("Add Your First Photo")
                }
                .lxBody()
                .frame(maxWidth: .infinity)
                .frame(height: LXConstants.buttonHeight)
                .background(LXColor.gold)
                .foregroundColor(LXColor.black)
                .cornerRadius(LXConstants.cornerRadius)
            }
            .padding(.horizontal, LXConstants.standardPadding)
            .padding(.top, 8)
        }
    }

    private func photoCard(_ photo: ProgressPhoto) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            ZStack(alignment: .topLeading) {
                if let url = photo.fileURL, let u = URL(string: url) {
                    AsyncImage(url: u) { image in
                        image
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                    } placeholder: {
                        Rectangle().fill(LXColor.deepNavy)
                    }
                    .frame(height: 180)
                    .clipped()
                    .cornerRadius(LXConstants.cornerRadius)
                } else {
                    Rectangle()
                        .fill(LXColor.deepNavy)
                        .frame(height: 180)
                        .overlay(
                            Image(systemName: "photo")
                                .font(.system(size: 28))
                                .foregroundColor(LXColor.white.opacity(0.3))
                        )
                        .cornerRadius(LXConstants.cornerRadius)
                }

                if photo.isBaseline {
                    Text("BASELINE")
                        .lxCaption()
                        .foregroundColor(LXColor.black)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(LXColor.gold)
                        .cornerRadius(6)
                        .padding(8)
                }
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(photo.isBaseline ? "Baseline" : "Week \(photo.weekNumber ?? 0)")
                    .lxBody()
                    .foregroundColor(LXColor.white)

                HStack {
                    if let score = photo.score {
                        Text(String(format: "Score %.0f", score))
                            .lxCaption()
                            .foregroundColor(LXColor.gold)
                    }
                    Spacer()
                    if let capturedAt = photo.capturedAt {
                        Text(lxFriendlyDate(capturedAt))
                            .lxCaption()
                            .foregroundColor(LXColor.white.opacity(0.4))
                    }
                }
            }
            .padding(8)
        }
        .padding(8)
        .background(LXColor.deepNavy)
        .cornerRadius(LXConstants.cornerRadius)
    }
}


// MARK: - Progress Comparison ------------------------------------------------

struct ProgressComparisonView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        ZStack {
            LXColor.black.ignoresSafeArea()

            if let comparison = appState.progressComparison {
                if let baseline = comparison.baseline, let latest = comparison.latest {
                    comparisonContent(baseline: baseline, latest: latest, comparison: comparison)
                } else {
                    incompleteView
                }
            } else if case .error = appState.progressComparisonState {
                noComparisonView
            } else {
                ProgressView().tint(LXColor.gold)
            }
        }
        .navigationTitle("Before & After")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            if appState.progressComparison == nil {
                Task { await appState.fetchProgressComparison() }
            }
        }
    }

    // MARK: Content

    private func comparisonContent(
        baseline: ComparisonPhoto,
        latest: ComparisonPhoto,
        comparison: ProgressComparison
    ) -> some View {
        ScrollView {
            VStack(spacing: 24) {
                scoreChangeHeader(comparison)

                HStack(alignment: .top, spacing: 12) {
                    sideCard(title: "Before", subtitle: "Baseline", photo: baseline)
                    sideCard(
                        title: "After",
                        subtitle: latest.weekNumber.map { "Week \($0)" } ?? "Latest",
                        photo: latest
                    )
                }
                .padding(.horizontal, LXConstants.standardPadding)

                if let trend = comparison.trend {
                    trendBadge(trend, weeks: comparison.weeksProgressed)
                }

                Spacer().frame(height: 40)
            }
            .padding(.top, 20)
        }
        .refreshable { await appState.fetchProgressComparison() }
    }

    private func scoreChangeHeader(_ comparison: ProgressComparison) -> some View {
        VStack(spacing: 8) {
            if let change = comparison.scoreChange {
                let arrow = change > 0 ? "arrow.up.right" : (change < 0 ? "arrow.down.right" : "arrow.right")
                HStack(spacing: 6) {
                    Image(systemName: arrow)
                    Text(String(format: "%+.1f", change))
                }
                .font(.system(size: 44, weight: .bold, design: .rounded))
                .foregroundColor(change >= 0 ? LXColor.gold : LXColor.red)
            } else {
                Text("—")
                    .font(.system(size: 44, weight: .bold, design: .rounded))
                    .foregroundColor(LXColor.gold)
            }
            Text("Score Change")
                .lxCaption()
                .foregroundColor(LXColor.white.opacity(0.5))
        }
    }

    private func sideCard(title: String, subtitle: String, photo: ComparisonPhoto) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            comparisonImage(url: photo.fileURL)

            Text(title)
                .lxBody()
                .foregroundColor(LXColor.white)

            HStack {
                Text(subtitle)
                    .lxCaption()
                    .foregroundColor(LXColor.white.opacity(0.4))
                Spacer()
                if let score = photo.score {
                    Text(String(format: "%.0f", score))
                        .font(.system(size: 16, weight: .bold, design: .rounded))
                        .foregroundColor(LXColor.gold)
                }
            }
        }
        .padding(8)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(LXColor.deepNavy)
        .cornerRadius(LXConstants.cornerRadius)
    }

    @ViewBuilder
    private func comparisonImage(url: String?) -> some View {
        if let url = url, let u = URL(string: url) {
            AsyncImage(url: u) { image in
                image.resizable().aspectRatio(contentMode: .fill)
            } placeholder: {
                Rectangle().fill(LXColor.deepNavy)
            }
            .frame(height: 220)
            .frame(maxWidth: .infinity)
            .clipped()
            .cornerRadius(LXConstants.cornerRadius)
        } else {
            Rectangle()
                .fill(LXColor.deepNavy)
                .frame(height: 220)
                .frame(maxWidth: .infinity)
                .overlay(
                    Image(systemName: "photo")
                        .font(.system(size: 28))
                        .foregroundColor(LXColor.white.opacity(0.3))
                )
                .cornerRadius(LXConstants.cornerRadius)
        }
    }

    private func trendBadge(_ trend: String, weeks: Int?) -> some View {
        let icon: String
        let label: String
        switch trend {
        case "improving":
            icon = "chart.line.uptrend.xyaxis"
            label = "You're improving"
        case "declining":
            icon = "chart.line.downtrend.xyaxis"
            label = "Keep pushing"
        default:
            icon = "chart.line.flattrend.xyaxis"
            label = "Steady progress"
        }
        return HStack(spacing: 8) {
            Image(systemName: icon)
            Text("\(label)\(weeks.map { " · \($0) week\($0 == 1 ? "" : "s") in" } ?? "")")
        }
        .lxCaption()
        .foregroundColor(LXColor.gold)
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(LXColor.deepNavy)
        .cornerRadius(LXConstants.cornerRadius)
    }

    // MARK: Empty states

    private var incompleteView: some View {
        VStack(spacing: 16) {
            Image(systemName: "camera.badge.ellipsis")
                .font(.system(size: 40))
                .foregroundColor(LXColor.gold.opacity(0.5))
            Text("Baseline ready")
                .lxH3()
                .foregroundColor(LXColor.white.opacity(0.6))
            Text("Upload your next check-in photo to unlock your before & after comparison.")
                .lxCaption()
                .foregroundColor(LXColor.white.opacity(0.4))
                .multilineTextAlignment(.center)
        }
        .padding()
    }

    private var noComparisonView: some View {
        VStack(spacing: 16) {
            Image(systemName: "rectangle.2.swap")
                .font(.system(size: 40))
                .foregroundColor(LXColor.gold.opacity(0.5))
            Text("No comparison yet")
                .lxH3()
                .foregroundColor(LXColor.white.opacity(0.6))
            Text("Upload a baseline photo and at least one check-in photo to see your transformation.")
                .lxCaption()
                .foregroundColor(LXColor.white.opacity(0.4))
                .multilineTextAlignment(.center)
            Button("Retry") {
                Task { await appState.fetchProgressComparison() }
            }
            .lxBody()
            .foregroundColor(LXColor.gold)
        }
        .padding()
    }
}


// MARK: - Line chart ---------------------------------------------------------

private struct ScoreLineChart: View {
    let points: [Double]

    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width
            let h = geo.size.height
            let mn = points.min() ?? 0
            let mx = points.max() ?? 100
            let rawSpan = max(mx - mn, 1)
            let pad = max(rawSpan * 0.15, 2)
            let lo = max(0, mn - pad)
            let hi = min(100, mx + pad)
            let range = max(hi - lo, 1)
            let xStep = points.count > 1 ? w / CGFloat(points.count - 1) : 0

            ZStack {
                ForEach(0..<4, id: \.self) { i in
                    let y = h - (CGFloat(i) / 3) * h
                    Path { p in
                        p.move(to: CGPoint(x: 0, y: y))
                        p.addLine(to: CGPoint(x: w, y: y))
                    }
                    .stroke(LXColor.white.opacity(0.08), lineWidth: 1)
                }

                Path { path in
                    for (i, value) in points.enumerated() {
                        let x = points.count == 1 ? w / 2 : CGFloat(i) * xStep
                        let y = h - CGFloat((value - lo) / range) * h
                        let pt = CGPoint(x: x, y: y)
                        if i == 0 { path.move(to: pt) } else { path.addLine(to: pt) }
                    }
                }
                .stroke(LXColor.gold, style: StrokeStyle(lineWidth: 3, lineCap: .round, lineJoin: .round))

                ForEach(points.indices, id: \.self) { i in
                    let x = points.count == 1 ? w / 2 : CGFloat(i) * xStep
                    let y = h - CGFloat((points[i] - lo) / range) * h
                    Circle()
                        .fill(LXColor.gold)
                        .frame(width: 8, height: 8)
                        .position(x: x, y: y)
                }
            }
        }
    }
}

// MARK: - Shared helpers -----------------------------------------------------

/// Renders a backend ISO-8601 string (e.g. "2026-08-27T12:34:56.789012") as a
/// short, human-readable date ("Aug 27, 2026"). The backend emits naive UTC
/// timestamps, so we reformat the date portion rather than using an ISO formatter.
private func lxFriendlyDate(_ iso: String) -> String {
    let datePart = String(iso.prefix(10)) // "2026-08-27"
    let parts = datePart.split(separator: "-")
    guard parts.count == 3,
          let year = Int(parts[0]),
          let month = Int(parts[1]),
          let day = Int(parts[2]),
          month >= 1, month <= 12 else { return datePart }

    let months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return "\(months[month - 1]) \(day), \(year)"
}

// MARK: - Previews -----------------------------------------------------------

#Preview {
    NavigationStack {
        ScoreHistoryView()
            .environmentObject(AppState())
    }
}

#Preview {
    NavigationStack {
        ProgressPhotosView()
            .environmentObject(AppState())
    }
}

