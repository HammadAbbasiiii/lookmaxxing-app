import Foundation

/// Centralised HTTP client for the LookMaxx AI backend.
///
/// Handles auth headers, JSON decoding, and error mapping.
/// All calls are async/await.
final class APIService {
    static let shared = APIService()

    private let baseURL = LXConstants.apiBaseURL
    private let session: URLSession
    private let decoder: JSONDecoder

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        session = URLSession(configuration: config)

        decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        decoder.keyDecodingStrategy = .convertFromSnakeCase
    }

    // ── Auth token ───────────────────────────────────────────
    var accessToken: String?

    // MARK: - Auth ─────────────────────────────────────────────────────────

    func login(username: String, password: String) async throws -> TokenResponse {
        let body = "username=\(encode(username))&password=\(encode(password))"
        return try await request(.post, "/auth/login", body: body, contentType: "application/x-www-form-urlencoded")
    }

    func signUp(email: String, username: String, password: String) async throws -> TokenResponse {
        let body = "email=\(encode(email))&username=\(encode(username))&password=\(encode(password))"
        return try await request(.post, "/auth/signup", body: body, contentType: "application/x-www-form-urlencoded")
    }

    // MARK: - Photos ───────────────────────────────────────────────────────

    func uploadPhoto(data: Data, fileName: String) async throws -> PhotoUploadResponse {
        let boundary = UUID().uuidString
        return try await multipartUpload("/photos/upload", data: data, fileName: fileName, boundary: boundary)
    }

    func getPhotoStatus(photoId: String) async throws -> Score {
        return try await request(.get, "/photos/\(photoId)/status")
    }

    // MARK: - Plan ─────────────────────────────────────────────────────────

    func getPlan() async throws -> Plan {
        return try await request(.get, "/plan")
    }

    func markTaskComplete(taskId: String) async throws {
        let _: EmptyResponse = try await request(.post, "/plan/checkin", body: "{\"task_id\":\"\(taskId)\"}")
    }

    // MARK: - Dashboard ────────────────────────────────────────────────────

    func getDashboard() async throws -> DashboardData {
        return try await request(.get, "/dashboard")
    }

    // MARK: - Explore ──────────────────────────────────────────────────────

    func getExplore() async throws -> ExploreData {
        return try await request(.get, "/products/recommendations")
    }

    // MARK: - Generic request builders ─────────────────────────────────────

    private func request<T: Decodable>(_ method: HTTPMethod, _ path: String, body: String? = nil, contentType: String = "application/json") async throws -> T {
        let url = URL(string: "\(baseURL)\(path)")!
        var req = URLRequest(url: url)
        req.httpMethod = method.rawValue
        req.setValue(contentType, forHTTPHeaderField: "Content-Type")

        if let token = accessToken {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body = body {
            req.httpBody = body.data(using: .utf8)
        }

        let (data, response) = try await session.data(for: req)

        guard let http = response as? HTTPURLResponse else {
            throw NSError(domain: "APIService", code: -1, userInfo: [NSLocalizedDescriptionKey: "Invalid response"])
        }

        if http.statusCode >= 400 {
            if let err = try? decoder.decode(LXError.self, from: data) {
                throw err
            }
            throw NSError(domain: "APIService", code: http.statusCode,
                          userInfo: [NSLocalizedDescriptionKey: "HTTP \(http.statusCode)"])
        }

        return try decoder.decode(T.self, from: data)
    }

    private func multipartUpload<T: Decodable>(_ path: String, data: Data, fileName: String, boundary: String) async throws -> T {
        let url = URL(string: "\(baseURL)\(path)")!
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        if let token = accessToken {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(fileName)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(data)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        req.httpBody = body

        let (responseData, response) = try await session.data(for: req)

        guard let http = response as? HTTPURLResponse, http.statusCode < 400 else {
            if let err = try? decoder.decode(LXError.self, from: responseData) { throw err }
            throw NSError(domain: "APIService", code: (response as? HTTPURLResponse)?.statusCode ?? -1)
        }

        return try decoder.decode(T.self, from: responseData)
    }

    private func encode(_ s: String) -> String {
        s.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? s
    }
}

// MARK: - Helpers ----------------------------------------------------------

enum HTTPMethod: String {
    case get = "GET"
    case post = "POST"
    case put = "PUT"
    case delete = "DELETE"
}

struct EmptyResponse: Decodable {}