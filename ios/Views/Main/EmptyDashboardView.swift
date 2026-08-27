import SwiftUI

/// Empty state shown on the Dashboard when the user has no analysis data yet.
///
/// Psychology: Warm welcome + a clear next action. We invite the user to
/// take their first photo instead of showing a broken "Please log in again"
/// message or a wall of empty widgets.
struct EmptyDashboardView: View {
    /// Called when the user taps the "Upload Photo" button.
    var onUpload: () -> Void

    @EnvironmentObject var appState: AppState

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            // Icon
            Image(systemName: "camera.fill")
                .font(.system(size: 56))
                .foregroundColor(LXColor.softGray)

            // Title
            Text("Welcome back, \(appState.currentUser?.username ?? "User")!")
                .lxH2()
                .foregroundColor(LXColor.white)
                .multilineTextAlignment(.center)
                .padding(.horizontal, LXConstants.standardPadding)

            // Subtitle
            Text("Upload your first photo to unlock your facial analysis.")
                .lxBody()
                .foregroundColor(LXColor.softGray)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)

            // CTA
            Button(action: onUpload) {
                HStack(spacing: 8) {
                    Text("📸")
                    Text("Upload Photo")
                        .lxButtonText()
                }
                .foregroundColor(LXColor.black)
                .frame(maxWidth: .infinity)
                .frame(height: LXConstants.buttonHeight)
                .background(LXColor.gold)
                .cornerRadius(16)
            }
            .padding(.horizontal, 40)

            Spacer()
            Spacer()
        }
        .padding(.top, 60)
    }
}

// MARK: - Preview ----------------------------------------------------------

#Preview {
    EmptyDashboardView(onUpload: {})
        .environmentObject(AppState())
        .background(LXColor.black)
}