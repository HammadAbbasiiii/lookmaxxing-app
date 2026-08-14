import Foundation
import Security

/// Secure token storage backed by the iOS Keychain (`kSecClassGenericPassword`).
///
/// Tokens must NEVER be stored in `UserDefaults` because it is unencrypted.
/// Keychain entries persist across app launches (and even reinstallations).
final class KeychainManager {

    /// The key under which the JWT access token is stored.
    static let accessTokenKey = "userAccessToken"

    private static let service = "com.lookmaxx.keychain"

    // MARK: - Save ---------------------------------------------------------

    @discardableResult
    static func saveToken(_ token: String, forKey key: String) -> Bool {
        guard let data = token.data(using: .utf8) else { return false }

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecValueData as String: data
        ]

        // Remove any existing item for this key before adding a fresh one.
        SecItemDelete(query as CFDictionary)
        let status = SecItemAdd(query as CFDictionary, nil)

        guard status == errSecSuccess else {
            print("[Keychain] Failed to save token (status \(status)).")
            return false
        }
        print("[Keychain] Token saved successfully.")
        return true
    }

    // MARK: - Read ---------------------------------------------------------

    static func getToken(forKey key: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecReturnData as String: kCFBooleanTrue!,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess, let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    // MARK: - Delete -------------------------------------------------------

    @discardableResult
    static func deleteToken(forKey key: String) -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key
        ]

        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess else { return false }
        print("[Keychain] Token deleted.")
        return true
    }

    // MARK: - JWT Expiration ----------------------------------------------

    /// Decodes the JWT payload and checks the `exp` (expiration) claim.
    /// Returns `true` if the token is malformed or already expired.
    static func isTokenExpired(_ token: String) -> Bool {
        let parts = token.split(separator: ".")
        guard parts.count >= 2 else { return true }

        let payload = String(parts[1])
        var base64 = payload
            .replacingOccurrences(of: "-", with: "+")
            .replacingOccurrences(of: "_", with: "/")
        while base64.count % 4 != 0 { base64 += "=" }

        guard let data = Data(base64Encoded: base64),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let exp = json["exp"] as? TimeInterval else {
            return true
        }

        return Date().timeIntervalSince1970 >= exp
    }
}