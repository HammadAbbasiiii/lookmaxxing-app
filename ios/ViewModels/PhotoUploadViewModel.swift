import Foundation
import UIKit

/// ViewModel that handles photo selection, compression, and upload.
///
/// Usage:
/// ```
/// let vm = PhotoUploadViewModel()
/// vm.upload(selectedImage) { result in
///     switch result {
///     case .success(let response):  print("Photo ID: \(response.id)")
///     case .failure(let err):       print("Upload failed: \(err)")
///     }
/// }
/// ```
@MainActor
final class PhotoUploadViewModel: ObservableObject {
    @Published var isUploading = false
    @Published var uploadProgress: Float = 0.0  // 0 → 1

    private let apiBaseURL: String
    private var authToken: String

    init(apiBaseURL: String = "https://lookmaxx-api.onrender.com/api/v1",
         authToken: String = "") {
        self.apiBaseURL = apiBaseURL
        self.authToken = authToken
    }

    // ── Public API ──────────────────────────────────────────────

    /// Compress + upload a single photo.  Compression runs on a background
    /// queue; the upload call is async/await.
    func upload(_ image: UIImage) async throws -> PhotoUploadResponse {
        isUploading = true
        uploadProgress = 0.0
        defer { isUploading = false }

        // 1. Compress
        guard let compressedData = ImageCompressor.compressImage(image) else {
            throw UploadError.compressionFailed
        }
        let fileSizeKB = Double(compressedData.count) / 1024.0
        print("📦 Compressed to \(String(format: "%.1f", fileSizeKB)) KB")
        uploadProgress = 0.3

        // 2. Build multipart request
        let url = URL(string: "\(apiBaseURL)/photos/upload")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(authToken)", forHTTPHeaderField: "Authorization")

        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)",
                         forHTTPHeaderField: "Content-Type")

        let body = multipartBody(data: compressedData,
                                 fileName: "photo.jpg",
                                 fieldName: "file",
                                 boundary: boundary)
        request.httpBody = body
        uploadProgress = 0.5

        // 3. Upload
        let (responseData, urlResponse) = try await URLSession.shared.data(for: request)

        guard let httpResponse = urlResponse as? HTTPURLResponse,
              (200...299).contains(httpResponse.statusCode) else {
            throw UploadError.serverError(code: (urlResponse as? HTTPURLResponse)?.statusCode ?? 0)
        }

        uploadProgress = 1.0

        // 4. Decode
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(PhotoUploadResponse.self, from: responseData)
    }

    /// Poll for analysis status until completed or failed.
    func pollStatus(photoID: String, maxAttempts: Int = 15, interval: TimeInterval = 1.5) async throws -> PhotoStatusResponse {
        let url = URL(string: "\(apiBaseURL)/photos/\(photoID)/status")!
        var request = URLRequest(url: url)
        request.setValue("Bearer \(authToken)", forHTTPHeaderField: "Authorization")

        for _ in 0..<maxAttempts {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse,
                  (200...299).contains(httpResponse.statusCode) else {
                throw UploadError.serverError(code: (response as? HTTPURLResponse)?.statusCode ?? 0)
            }
            let decoder = JSONDecoder()
            let status = try decoder.decode(PhotoStatusResponse.self, from: data)
            switch status.analysis_status {
            case "completed", "failed":
                return status
            default:
                try await Task.sleep(nanoseconds: UInt64(interval * 1_000_000_000))
            }
        }
        throw UploadError.pollingTimeout
    }

    // MARK: - Private helpers

    private func multipartBody(data: Data,
                               fileName: String,
                               fieldName: String,
                               boundary: String) -> Data {
        var body = Data()
        let lineBreak = "\r\n".data(using: .utf8)!

        body.append("--\(boundary)\(lineBreak)".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"\(fieldName)\"; filename=\"\(fileName)\"\(lineBreak)".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\(lineBreak)\(lineBreak)".data(using: .utf8)!)
        body.append(data)
        body.append("\(lineBreak)--\(boundary)--\(lineBreak)".data(using: .utf8)!)

        return body
    }

    // MARK: - Error

    enum UploadError: LocalizedError {
        case compressionFailed
        case serverError(code: Int)
        case pollingTimeout

        var errorDescription: String? {
            switch self {
            case .compressionFailed:  return "Image compression failed"
            case .serverError(let c): return "Server error (HTTP \(c))"
            case .pollingTimeout:     return "Analysis timed out"
            }
        }
    }
}

struct PhotoStatusResponse: Codable {
    let id: String
    let analysis_status: String
    let score: Double?
    let categoryBreakdown: [String: AnyCodable]?
    let strengths: [String]?
    let weaknesses: [String]?

    enum CodingKeys: String, CodingKey {
        case id, score, strengths, weaknesses
        case analysis_status = "analysis_status"
        case categoryBreakdown = "category_breakdown"
    }
}

/// Simple wrapper so arbitrary JSON dicts can be Codable.
struct AnyCodable: Codable {
    let value: Any
    init(_ value: Any) { self.value = value }
    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let intVal = try? container.decode(Int.self) { value = intVal }
        else if let dblVal = try? container.decode(Double.self) { value = dblVal }
        else if let strVal = try? container.decode(String.self) { value = strVal }
        else if let boolVal = try? container.decode(Bool.self) { value = boolVal }
        else { value = "unknown" }
    }
    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        if let v = value as? Int { try container.encode(v) }
        else if let v = value as? Double { try container.encode(v) }
        else if let v = value as? String { try container.encode(v) }
        else if let v = value as? Bool { try container.encode(v) }
        else { try container.encode("unknown") }
    }
}