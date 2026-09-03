import SwiftUI

/// Login sheet presented from Onboarding when the user taps
/// "I'll do this later" (or "Already have an account?").
///
/// Psychology: Confidence + familiarity. Returning users should feel
/// welcomed back, never blocked by a broken skip button.
struct LoginView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) private var dismiss

    @State private var email = ""
    @State private var password = ""
    @State private var fullName = ""
    @State private var showSignUp = false

    var body: some View {
        NavigationStack {
            ZStack {
                GoldGradientBackground()

                ScrollView {
                    VStack(spacing: 24) {
                        // Header
                        VStack(spacing: 8) {
                            Text(showSignUp ? "Create Your Account" : "Welcome Back")
                                .lxH2()
                                .foregroundColor(LXColor.white)
                                .multilineTextAlignment(.center)

                            Text(showSignUp
                                 ? "Start your transformation journey"
                                 : "We've missed you")
                                .lxBody()
                                .foregroundColor(LXColor.white.opacity(0.7))
                                .multilineTextAlignment(.center)
                        }
                        .padding(.top, 32)

                        // Fields
                        VStack(spacing: 20) {
                            if showSignUp {
                                LXTextField(placeholder: "Full Name (optional)", text: $fullName)
                            }

                            LXTextField(placeholder: "Email", text: $email, keyboardType: .emailAddress)
                            LXTextField(placeholder: showSignUp ? "Min 8 characters" : "Password", text: $password, isSecure: true)

                            // Inline error (below fields)
                            if case .error(let err) = appState.authState {
                                Text(err)
                                    .lxCaption()
                                    .foregroundColor(LXColor.red)
                                    .multilineTextAlignment(.center)
                                    .transition(.opacity)
                            }

                            // Primary button
                            Button(action: submit) {
                                HStack(spacing: 8) {
                                    if isLoading {
                                        ProgressView()
                                            .tint(LXColor.black)
                                    }
                                    Text(isLoading ? "Please wait..." : (showSignUp ? "Create Account" : "Log In"))
                                        .lxH3()
                                        .foregroundColor(LXColor.black)
                                }
                                .frame(maxWidth: .infinity)
                                .frame(height: LXConstants.buttonHeight)
                                .background(LXColor.gold)
                                .cornerRadius(LXConstants.cornerRadius)
                            }
                            .buttonStyle(PressableButtonStyle())
                            .disabled(isLoading)

                            // Toggle between sign up / login
                            Button(showSignUp ? "Already have an account? Log in" : "Don't have an account? Sign Up") {
                                if showSignUp {
                                    switchToLogin()
                                } else {
                                    switchToSignUp()
                                }
                            }
                            .lxCaption()
                            .foregroundColor(LXColor.gold)
                            .padding(.top, 8)
                        }
                        .padding(.horizontal, LXConstants.standardPadding)
                    }
                    .padding(.bottom, 32)
                }
            }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .lxCaption()
                    .foregroundColor(LXColor.white.opacity(0.6))
                }
            }
        }
        .onChange(of: appState.isAuthenticated) { authenticated in
            if authenticated {
                dismiss()
            }
        }
    }

    private var isLoading: Bool {
        if case .loading = appState.authState { return true }
        return false
    }

    // MARK: - Mode Switching ------------------------------------------------

    /// Switches to Sign Up mode and clears any lingering state, so a previous
    /// login error never leaks onto the sign-up form.
    private func switchToSignUp() {
        withAnimation(.easeInOut(duration: 0.3)) {
            showSignUp = true
        }
        resetForm()
    }

    /// Switches to Login mode and clears any lingering state, so a previous
    /// sign-up error never leaks onto the login form.
    private func switchToLogin() {
        withAnimation(.easeInOut(duration: 0.3)) {
            showSignUp = false
        }
        resetForm()
    }

    /// Clears the shared error state and the form fields when changing modes
    /// or after a successful action, preventing cross-mode error leakage.
    private func resetForm() {
        appState.authState = .idle
        email = ""
        password = ""
        fullName = ""
    }

    private func submit() {
        Task {
            if showSignUp {
                await appState.signUp(
                    email: email,
                    password: password,
                    fullName: fullName.isEmpty ? nil : fullName
                )
            } else {
                await appState.login(email: email, password: password)
            }

            if case .error = appState.authState {
                Haptics.warning()
            } else if appState.isAuthenticated {
                Haptics.success()
            }
        }
    }
}

// MARK: - Preview ----------------------------------------------------------

#Preview {
    LoginView()
        .environmentObject(AppState())
}