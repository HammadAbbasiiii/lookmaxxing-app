import UIKit

/// Compresses JPEG images to stay under 2MB.
///
/// Strategy: iterative binary search to hit target size under 2MB,
/// then JPEG compress. Falls back to the original data on failure.
enum ImageCompressor {
    /// Maximum allowed upload size, in bytes.
    static let maxUploadSize = 2_000_000

    /// Compress `img` to under `maxUploadSize`.
    /// - Returns: JPEG `Data` or `nil`
    static func compressImage(_ img: UIImage) -> Data? {
        // 1. Scale down if too large (max 2048 px on the longest side)
        var scaledImage = img
        let maxDimension: CGFloat = 2048
        let scale = min(maxDimension / img.size.width, maxDimension / img.size.height, 1.0)
        if scale < 1.0 {
            let newSize = CGSize(width: img.size.width * scale, height: img.size.height * scale)
            let renderer = UIGraphicsImageRenderer(size: newSize)
            scaledImage = renderer.image { _ in
                img.draw(in: CGRect(origin: .zero, size: newSize))
            }
        }

        // 2. Binary search for compression quality
        var low: CGFloat = 0.0
        var high: CGFloat = 1.0
        var bestData: Data?

        for _ in 0..<8 {  // 8 iterations → within ~0.4% precision
            let mid = (low + high) / 2.0
            guard let data = scaledImage.jpegData(compressionQuality: mid) else {
                return scaledImage.jpegData(compressionQuality: 0.7) ?? nil
            }

            if data.count <= maxUploadSize {
                bestData = data
                low = mid  // try higher quality
            } else {
                high = mid  // must compress more
            }
        }

        return bestData ?? scaledImage.jpegData(compressionQuality: 0.0)
    }
}