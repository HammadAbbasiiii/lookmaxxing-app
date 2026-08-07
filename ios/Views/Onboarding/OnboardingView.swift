import SwiftUI

/// Screen 1 — First impression. Hook user in 30 seconds.
///
/// Psychology: Curiosity.
/// "What will my score be?"
struct OnboardingView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var authVM = AuthViewModel()
    @State private var showSignUp = false

    var body: some View {
        ZStack {
            LXColor.black.ignoresSafeArea()

            VStack(spacing: 40) {
                Spacer()

                // Hero image placeholder
                ZStack {
                    Circle()
                        .fill(LXColor.deepNavy)
                        .frame(width: 200, height: 200)
                    Text("🚀")
                        .font(.system(size: 80))
                }

                VStack(spacing: 12) {
                    Text("Discover Your\nHidden Potential")
                        .lxH2()
                        .foregroundColor(LXColor.white)
                        .multilineTextAlignment(.center)

                    Text("AI-powered facial analysis that helps you\nunlock your best self.")
                        .lxBody()
                        .foregroundColor(LXColor.white.opacity(0.7))
                        .multilineTextAlignment(.center)
                }

                // CTA — Get My Score
                Button(action: { showSignUp = true }) {
                    HStack(spacing: 8) {
                        Text("🚀")
                        Text("GET MY SCORE")
                            .font(LXFont.h3())
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: LXConstants.buttonHeight)
                    .background(LXColor.gold)
                    .foregroundColor(LXColor.black)
                    .cornerRadius(LXConstants.cornerRadius)
                }
                .padding(.horizontal, LXConstants.standardPadding)

                // Lazy sign-up flow
                if showSignUp {
                    VStack(spacing: 16) {
                        LXTextField(placeholder: "Email", text: $authVM.email, keyboardType: .emailAddress)
                        LXTextField(placeholder: "Username", text: $authVM.username)
                        LXTextField(placeholder: "Password", text: $authVM.password, isSecure: true)

                        if let err = authVM.errorMessage {
                            Text(err)
                                .lxCaption()
                                .foregroundColor(LXColor.red)
                                .multilineTextAlignment(.center)
                        }

                        Button(action: { authVM.signUp(appState: appState) }) {
                            Text(authVM.isLoading ? "Creating Account..." : "Create Account")
                                .lxH3()
                                .frame(maxWidth: .infinity)
                                .frame(height: LXConstants.buttonHeight)
                                .background(LXColor.gold)
                                .foregroundColor(LXColor.black)
                                .cornerRadius(LXConstants.cornerRadius)
                        }
                        .disabled(authVM.isLoading)

                        Button("Already have an account? Log in") {
                            authVM.login(appState: appState)
                        }
                        .lxCaption()
                        .foregroundColor(LXColor.white.opacity(0.6))
                    }
                    .padding(.horizontal, LXConstants.standardPadding)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
                } else {
                    Button("I'll do this later") {
                        // Guest entry: proceed without auth
                        appState.isAuthenticated = true
                    }
                    .lxCaption()
                    .foregroundColor(LXColor.white.opacity(0.5))
                }

                Spacer()
            }
        }
    }
}

// MARK: - Reusable TextField -----------------------------------------------

struct LXTextField: View {
    let placeholder: String
    @Binding var text: String
    var keyboardType: UIKeyboardType = .default
    var isSecure = false

    var body: some View {
        Group {
            if isSecure {
                SecureField(placeholder, text: $text)
            } else {
                TextField(placeholder, text: $text)
                    .keyboardType(keyboardType)
                    .autocapitalization(.none)
            }
        }
        .font(LXFont.body())
        .foregroundColor(LXColor.white)
        .padding()
        .background(LXColor.deepNavy)
        .cornerRadius(LXConstants.cornerRadius)
    }
}

// MARK: - Preview ----------------------------------------------------------

#Preview {
    OnboardingView()
        .environmentObject(AppState())
}