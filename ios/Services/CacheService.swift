import Foundation

/// Simple on-disk cache so the app works offline.
///
/// Cached data (Dashboard, Plan, Explore) lets the user browse even
/// without connectivity — critical for subway / low-signal moments.
final class CacheService {
    static let shared = CacheService()

    private let defaults = UserDefaults(suiteName: "group.com.lookmaxx.cache")!
    private let encoder = JSONEncoder()
    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .iso8601
        return d
    }()

    private init() {}

    // MARK: - Keys ---------------------------------------------------------

    private enum Key: String {
        case dashboard, plan, explore, score, user
    }

    // MARK: - Getters / Setters --------------------------------------------

    func cachedDashboard() -> DashboardData? {
        load(.dashboard)
    }

    func setDashboard(_ data: DashboardData) {
        save(data, for: .dashboard)
    }

    func cachedPlan() -> Plan? {
        load(.plan)
    }

    func setPlan(_ plan: Plan) {
        save(plan, for: .plan)
    }

    func cachedExplore() -> ExploreData? {
        load(.explore)
    }

    func setExplore(_ data: ExploreData) {
        save(data, for: .explore)
    }

    func cachedScore() -> Score? {
        load(.score)
    }

    func setScore(_ score: Score) {
        save(score, for: .score)
    }

    func cachedUser() -> User? {
        load(.user)
    }

    func setUser(_ user: User) {
        save(user, for: .user)
    }

    func clearAll() {
        defaults.removePersistentDomain(forName: "group.com.lookmaxx.cache")
    }

    // MARK: - Helpers ------------------------------------------------------

    private func load<T: Decodable>(_ key: Key) -> T? {
        guard let data = defaults.data(forKey: key.rawValue) else { return nil }
        return try? decoder.decode(T.self, from: data)
    }

    private func save<T: Encodable>(_ value: T, for key: Key) {
        guard let data = try? encoder.encode(value) else { return }
        defaults.set(data, forKey: key.rawValue)
    }
}