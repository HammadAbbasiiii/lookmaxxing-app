import SwiftUI
import StoreKit
import UserNotifications
import UIKit

/// Dedicated Settings screen.
///
/// Consolidates account management, preferences, and sign-out into
/// a single place reachable from the Profile tab.
struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) private var dismiss
    @State private var restoreMessage = ""
    @State private var showRestoreAlert = false

    var body: some View {
        ZStack {
            LXColor.black.ignoresSafeArea()

            ScrollView {
                VStack(spacing: 24) {
                    // Account section
                    VStack(spacing: 0) {
                        NavigationLink {
                            AccountView()
                        } label: {
                            settingsRow(icon: "person.crop.circle", title: "Account", detail: appState.currentUser?.email)
                        }
                        Divider().background(LXColor.white.opacity(0.1))
                        NavigationLink {
                            SubscriptionView()
                        } label: {
                            settingsRow(icon: "creditcard", title: "Subscription", detail: tierLabel)
                        }
                        Divider().background(LXColor.white.opacity(0.1))
                        Button {
                            restorePurchases()
                        } label: {
                            settingsRow(icon: "star.fill", title: "Restore Purchases")
                        }
                    }
                    .background(LXColor.deepNavy)
                    .cornerRadius(LXConstants.cornerRadius)
                    .padding(.horizontal, LXConstants.standardPadding)
                    .padding(.top, 20)

                    // Preferences section
                    VStack(spacing: 0) {
                        NavigationLink {
                            NotificationsView()
                        } label: {
                            settingsRow(icon: "bell.fill", title: "Notifications")
                        }
                        Divider().background(LXColor.white.opacity(0.1))
                        NavigationLink {
                            PrivacyView()
                        } label: {
                            settingsRow(icon: "lock.fill", title: "Privacy")
                        }
                        Divider().background(LXColor.white.opacity(0.1))
                        NavigationLink {
                            HelpView()
                        } label: {
                            settingsRow(icon: "questionmark.circle", title: "Help & Support")
                        }
                        Divider().background(LXColor.white.opacity(0.1))
                        NavigationLink {
                            TermsView()
                        } label: {
                            settingsRow(icon: "doc.text.fill", title: "Terms & Conditions")
                        }
                    }
                    .background(LXColor.deepNavy)
                    .cornerRadius(LXConstants.cornerRadius)
                    .padding(.horizontal, LXConstants.standardPadding)

                    // Sign out
                    Button(action: { appState.signOut() }) {
                        HStack(spacing: 8) {
                            Image(systemName: "rectangle.portrait.and.arrow.right")
                            Text("Sign Out")
                        }
                        .lxBody()
                        .foregroundColor(LXColor.red)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(LXColor.deepNavy)
                        .cornerRadius(LXConstants.cornerRadius)
                    }
                    .padding(.horizontal, LXConstants.standardPadding)

                    Spacer().frame(height: 40)
                }
            }
        }
        .navigationTitle("Settings")
        .navigationBarTitleDisplayMode(.inline)
        .alert("Restore Purchases", isPresented: $showRestoreAlert) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(restoreMessage)
        }
    }

    private func restorePurchases() {
        Task {
            do {
                // Sync the user's App Store transactions. With no in-app products
                // configured yet this simply confirms nothing is owed.
                try await AppStore.sync()
                restoreMessage = "No previous purchases were found on this account."
            } catch {
                restoreMessage = "Could not restore purchases. Please try again."
            }
            showRestoreAlert = true
        }
    }

    private var tierLabel: String {
        appState.currentUser?.subscriptionTier.rawValue.uppercased() ?? "FREE"
    }

    private func settingsRow(icon: String, title: String, detail: String? = nil) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundColor(LXColor.gold)
                .frame(width: 24)
            Text(title)
                .lxBody()
                .foregroundColor(LXColor.white)
            Spacer()
            if let detail {
                Text(detail)
                    .lxCaption()
                    .foregroundColor(LXColor.white.opacity(0.5))
            }
            Image(systemName: "chevron.right")
                .foregroundColor(LXColor.white.opacity(0.3))
        }
        .padding()
        .contentShape(Rectangle())
    }
}

// MARK: - Account

struct AccountView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) private var dismiss

    @State private var fullName = ""
    @State private var age = ""
    @State private var gender = ""
    @State private var height = ""
    @State private var weight = ""
    @State private var location = ""
    @State private var bio = ""
    @State private var isLoading = true
    @State private var errorMessage = ""
    @State private var showError = false
    @State private var showDeleteConfirm = false

    var body: some View {
        ZStack {
            LXColor.black.ignoresSafeArea()
            ScrollView {
                VStack(spacing: 20) {
                    VStack(spacing: 8) {
                        Image(systemName: "person.crop.circle").font(.system(size: 48)).foregroundColor(LXColor.gold)
                        Text(appState.currentUser?.username ?? "Your Profile").lxH2().foregroundColor(LXColor.white)
                        Text("These details personalise your plan.").lxCaption().foregroundColor(LXColor.white.opacity(0.5))
                    }
                    .padding(.top, 20)

                    if isLoading {
                        LXSpinnerRing(size: 96).padding(.vertical, 40)
                    } else {
                        field("Full Name", text: $fullName)
                        field("Age", text: $age, keyboard: .numberPad)
                        field("Height (cm)", text: $height, keyboard: .numberPad)
                        field("Weight (kg)", text: $weight, keyboard: .numberPad)
                        field("Location", text: $location)
                        field("Gender", text: $gender)
                        field("Bio", text: $bio)

                        Button(action: save) {
                            Text("Save Changes").lxButtonText().foregroundColor(LXColor.black)
                                .frame(maxWidth: .infinity).frame(height: LXConstants.buttonHeight)
                                .background(LXColor.gold).cornerRadius(LXConstants.cornerRadius)
                        }
                        .buttonStyle(PressableButtonStyle())
                        .padding(.horizontal, LXConstants.standardPadding)

                        Button(action: { showDeleteConfirm = true }) {
                            Text("Delete Account").lxBody().foregroundColor(LXColor.red)
                                .frame(maxWidth: .infinity).frame(height: LXConstants.buttonHeight)
                                .background(LXColor.red.opacity(0.12)).cornerRadius(LXConstants.cornerRadius)
                        }
                        .buttonStyle(PressableButtonStyle())
                        .padding(.horizontal, LXConstants.standardPadding)
                    }

                    Spacer().frame(height: 40)
                }
            }
        }
        .navigationTitle("Account")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
        .alert("Error", isPresented: $showError) {
            Button("OK", role: .cancel) {}
        } message: { Text(errorMessage) }
        .confirmationDialog("Delete your account and all data? This cannot be undone.", isPresented: $showDeleteConfirm) {
            Button("Delete Account", role: .destructive) { Task { await delete() } }
            Button("Cancel", role: .cancel) {}
        }
    }

    @MainActor
    private func load() async {
        isLoading = true
        await appState.fetchProfile()
        if let p = appState.profile {
            fullName = p.fullName ?? ""
            age = p.age.map(String.init) ?? ""
            gender = p.gender ?? ""
            height = p.height.map(String.init) ?? ""
            weight = p.weight.map(String.init) ?? ""
            location = p.location ?? ""
            bio = p.bio ?? ""
        }
        isLoading = false
    }

    private func save() {
        let update = ProfileUpdateRequest(
            fullName: fullName.isEmpty ? nil : fullName,
            age: Int(age),
            gender: gender.isEmpty ? nil : gender,
            height: Int(height),
            weight: Int(weight),
            location: location.isEmpty ? nil : location,
            bio: bio.isEmpty ? nil : bio
        )
        Task { @MainActor in
            let ok = await appState.updateProfile(update)
            if ok { Haptics.success(); dismiss() }
            else { errorMessage = appState.profileError ?? "Could not save."; showError = true }
        }
    }

    @MainActor
    private func delete() async {
        do { try await appState.deleteAccount() }
        catch { errorMessage = error.localizedDescription; showError = true }
    }

    private func field(_ label: String, text: Binding<String>, keyboard: UIKeyboardType = .default) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(label).lxCaption().foregroundColor(LXColor.white.opacity(0.5))
            TextField(label, text: text).keyboardType(keyboard).foregroundColor(LXColor.white)
                .padding().background(LXColor.deepNavy).cornerRadius(LXConstants.cornerRadius)
        }
        .padding(.horizontal, LXConstants.standardPadding)
    }
}

// MARK: - Notifications

struct NotificationsView: View {
    @AppStorage("notifications.dailyReminder") private var dailyReminder = false
    @AppStorage("notifications.weeklyReminder") private var weeklyReminder = false
    @State private var showDenied = false

    var body: some View {
        ZStack {
            LXColor.black.ignoresSafeArea()
            ScrollView {
                VStack(spacing: 20) {
                    VStack(spacing: 8) {
                        Image(systemName: "bell.badge.fill").font(.system(size: 40)).foregroundColor(LXColor.gold)
                        Text("Notifications").lxH2().foregroundColor(LXColor.white)
                        Text("Gentle nudges to keep your streak alive.").lxCaption().foregroundColor(LXColor.white.opacity(0.5))
                    }
                    .padding(.top, 20)

                    toggleRow(title: "Daily Reminder", subtitle: "A nudge at 9:00 AM to complete today's tasks.", isOn: $dailyReminder) { toggleDaily($0) }
                    toggleRow(title: "Weekly Progress Reminder", subtitle: "A Sunday reminder to snap a progress photo.", isOn: $weeklyReminder) { toggleWeekly($0) }

                    Text("Reminders are delivered locally on your device.")
                        .lxCaption().foregroundColor(LXColor.white.opacity(0.5))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, LXConstants.standardPadding)

                    Spacer().frame(height: 40)
                }
            }
        }
        .navigationTitle("Notifications")
        .navigationBarTitleDisplayMode(.inline)
        .alert("Notifications Disabled", isPresented: $showDenied) {
            Button("Open Settings") { openSettings() }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Enable notifications for LookMaxx in iOS Settings to receive reminders.")
        }
    }

    private func requestAuthorization() async -> Bool {
        let center = UNUserNotificationCenter.current()
        let settings = await center.notificationSettings()
        switch settings.authorizationStatus {
        case .notDetermined:
            return (try? await center.requestAuthorization(options: [.alert, .sound, .badge])) ?? false
        case .denied: return false
        default: return true
        }
    }

    private func toggleDaily(_ on: Bool) {
        let center = UNUserNotificationCenter.current()
        if on {
            Task {
                let granted = await requestAuthorization()
                if granted { await scheduleDaily() }
                else {
                    await MainActor.run {
                        dailyReminder = false
                        showDenied = true
                    }
                }
            }
        } else {
            center.removePendingNotificationRequests(withIdentifiers: ["dailyReminder"])
        }
    }

    private func toggleWeekly(_ on: Bool) {
        let center = UNUserNotificationCenter.current()
        if on {
            Task {
                let granted = await requestAuthorization()
                if granted { await scheduleWeekly() }
                else {
                    await MainActor.run {
                        weeklyReminder = false
                        showDenied = true
                    }
                }
            }
        } else {
            center.removePendingNotificationRequests(withIdentifiers: ["weeklyReminder"])
        }
    }

    private func scheduleDaily() async {
        let content = UNMutableNotificationContent()
        content.title = "Daily Check-In"
        content.body = "Complete today's tasks to keep your streak alive."
        content.sound = .default
        var c = DateComponents()
        c.hour = 9
        let trigger = UNCalendarNotificationTrigger(dateMatching: c, repeats: true)
        try? await UNUserNotificationCenter.current().add(UNNotificationRequest(identifier: "dailyReminder", content: content, trigger: trigger))
    }

    private func scheduleWeekly() async {
        let content = UNMutableNotificationContent()
        content.title = "Weekly Progress Photo"
        content.body = "Snap this week's progress photo and watch your score climb."
        content.sound = .default
        var c = DateComponents()
        c.hour = 10
        c.weekday = 1 // Sunday
        let trigger = UNCalendarNotificationTrigger(dateMatching: c, repeats: true)
        try? await UNUserNotificationCenter.current().add(UNNotificationRequest(identifier: "weeklyReminder", content: content, trigger: trigger))
    }

    private func openSettings() {
        if let url = URL(string: UIApplication.openSettingsURLString) {
            UIApplication.shared.open(url)
        }
    }

    private func toggleRow(title: String, subtitle: String, isOn: Binding<Bool>, onChange: @escaping (Bool) -> Void) -> some View {
        Toggle(isOn: Binding(
            get: { isOn.wrappedValue },
            set: { v in isOn.wrappedValue = v; onChange(v) }
        )) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title).lxBody().foregroundColor(LXColor.white)
                Text(subtitle).lxCaption().foregroundColor(LXColor.white.opacity(0.5))
            }
        }
        .tint(LXColor.gold)
        .padding()
        .background(LXColor.deepNavy)
        .cornerRadius(LXConstants.cornerRadius)
        .padding(.horizontal, LXConstants.standardPadding)
    }
}

// MARK: - Subscription

struct SubscriptionView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        ZStack {
            LXColor.black.ignoresSafeArea()
            ScrollView {
                VStack(spacing: 20) {
                    VStack(spacing: 8) {
                        Image(systemName: "crown.fill").font(.system(size: 40)).foregroundColor(LXColor.gold)
                        Text("\(tier) Plan").lxH2().foregroundColor(LXColor.white)
                        Text("Your current subscription tier.").lxCaption().foregroundColor(LXColor.white.opacity(0.5))
                    }
                    .padding(.top, 20)

                    tierCard(title: "Free", price: "$0", features: ["1 analysis per day", "7-day plan preview", "Score history"])
                    tierCard(title: "Pro", price: "$9.99/mo", features: ["Unlimited analyses", "Full 90-day plan", "Progress photo tracking", "Personalised product picks"])
                    tierCard(title: "Elite", price: "$19.99/mo", features: ["Everything in Pro", "1-on-1 coaching", "Priority support"])

                    Text("Billing is handled by the App Store. Manage or cancel anytime in iOS Settings.")
                        .lxCaption().foregroundColor(LXColor.white.opacity(0.5))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, LXConstants.standardPadding)

                    Spacer().frame(height: 40)
                }
            }
        }
        .navigationTitle("Subscription")
        .navigationBarTitleDisplayMode(.inline)
    }

    private var tier: String {
        appState.currentUser?.subscriptionTier.rawValue.capitalized ?? "Free"
    }

    private func tierCard(title: String, price: String, features: [String]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text(title).lxH3().foregroundColor(LXColor.gold)
                Spacer()
                Text(price).lxBodyBold().foregroundColor(LXColor.white)
            }
            ForEach(features, id: \.self) { f in
                HStack(spacing: 8) {
                    Image(systemName: "checkmark.circle.fill").foregroundColor(LXColor.green)
                    Text(f).lxBody().foregroundColor(LXColor.white.opacity(0.8))
                }
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(LXColor.deepNavy)
        .cornerRadius(LXConstants.cornerRadius)
        .padding(.horizontal, LXConstants.standardPadding)
    }
}

// MARK: - Info text (Privacy / Terms) ----------------------------------------

struct InfoSection: Identifiable {
    let id = UUID()
    let title: String
    let body: String
}

struct InfoTextView: View {
    let title: String
    let icon: String
    let sections: [InfoSection]

    var body: some View {
        ZStack {
            LXColor.black.ignoresSafeArea()
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    VStack(spacing: 8) {
                        Image(systemName: icon).font(.system(size: 40)).foregroundColor(LXColor.gold)
                        Text(title).lxH2().foregroundColor(LXColor.white)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.top, 20)

                    ForEach(sections) { section in
                        VStack(alignment: .leading, spacing: 6) {
                            Text(section.title).lxH3().foregroundColor(LXColor.gold)
                            Text(section.body).lxBody().foregroundColor(LXColor.white.opacity(0.85))
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding()
                        .background(LXColor.deepNavy)
                        .cornerRadius(LXConstants.cornerRadius)
                    }
                    .padding(.horizontal, LXConstants.standardPadding)

                    Spacer().frame(height: 40)
                }
            }
        }
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct PrivacyView: View {
    var body: some View {
        InfoTextView(
            title: "Privacy",
            icon: "lock.fill",
            sections: [
                InfoSection(title: "Your Data", body: "We collect the photos you upload and the profile details you provide, solely to generate your score, plan, and progress tracking."),
                InfoSection(title: "Storage", body: "Photos are processed and stored securely with our cloud provider. You can delete your account at any time to remove all associated data."),
                InfoSection(title: "Sharing", body: "We never sell your data. Analysis is performed automatically and is not shared with third parties."),
                InfoSection(title: "Your Rights", body: "You may request a copy or deletion of your data at any time via the Account screen or by contacting support.")
            ]
        )
    }
}

struct TermsView: View {
    var body: some View {
        InfoTextView(
            title: "Terms & Conditions",
            icon: "doc.text.fill",
            sections: [
                InfoSection(title: "Acceptance", body: "By using LookMaxx AI you agree to these terms. If you do not agree, please discontinue use."),
                InfoSection(title: "Service", body: "LookMaxx AI provides facial analysis and self-improvement guidance for informational purposes only."),
                InfoSection(title: "Medical Disclaimer", body: "This app is not a medical device and does not provide medical advice. Consult a professional for health concerns."),
                InfoSection(title: "Accounts", body: "You are responsible for maintaining the confidentiality of your account credentials.")
            ]
        )
    }
}

struct HelpView: View {
    var body: some View {
        ZStack {
            LXColor.black.ignoresSafeArea()
            ScrollView {
                VStack(spacing: 20) {
                    VStack(spacing: 8) {
                        Image(systemName: "questionmark.circle.fill").font(.system(size: 40)).foregroundColor(LXColor.gold)
                        Text("Help & Support").lxH2().foregroundColor(LXColor.white)
                    }
                    .padding(.top, 20)

                    faq("How do I improve my score?", "Follow your 90-day plan and complete daily tasks. Consistency drives the biggest gains.")
                    faq("How often should I take progress photos?", "We recommend a photo at baseline, then at day 30, 60, and 90 to track your transformation.")
                    faq("Can I delete my data?", "Yes. Open Settings > Account and tap Delete Account to permanently remove your data.")

                    if let url = URL(string: "mailto:support@lookmaxx.app") {
                        Link(destination: url) {
                            HStack(spacing: 8) {
                                Image(systemName: "envelope.fill")
                                Text("Contact Support")
                            }
                            .lxBody().foregroundColor(LXColor.black)
                            .frame(maxWidth: .infinity).frame(height: LXConstants.buttonHeight)
                            .background(LXColor.gold).cornerRadius(LXConstants.cornerRadius)
                        }
                        .padding(.horizontal, LXConstants.standardPadding)
                    }

                    Spacer().frame(height: 40)
                }
            }
        }
        .navigationTitle("Help")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func faq(_ q: String, _ a: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(q).lxH3().foregroundColor(LXColor.gold)
            Text(a).lxBody().foregroundColor(LXColor.white.opacity(0.85))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(LXColor.deepNavy)
        .cornerRadius(LXConstants.cornerRadius)
        .padding(.horizontal, LXConstants.standardPadding)
    }
}

// MARK: - Preview ----------------------------------------------------------

#Preview {
    NavigationStack {
        SettingsView()
            .environmentObject(AppState())
    }
}