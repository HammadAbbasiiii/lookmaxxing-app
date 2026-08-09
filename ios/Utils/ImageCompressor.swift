import UIKit

/// Compresses JPEG images to stay under 2MB while keeping dimensions large
/// enough for face detection (minimum 400 px on the shortest side).
///
/// Strategy: scale down to max 2048 px, then binary search on JPEG quality.
/// Never goes below 400 px so MediaPipe can detect faces reliably.
enum ImageCompressor {
    /// Maximum allowed upload size, in bytes.
    static let maxUploadSize = 2_000_000

    /// Compress `img` to under `maxUploadSize`.
    /// - Returns: JPEG `Data` or `nil`
    static func compressImage(_ img: UIImage) -> Data? {
        // 1. Scale down if too large, but never below 400 px on the shortest side
        var scaledImage = img
        let maxDimension: CGFloat = 2048
        let minDimension: CGFloat = LXConstants.minFaceDimension  // 400 px
        let scale = min(maxDimension / img.size.width, maxDimension / img.size.height, 1.0)
        if scale < 1.0 {
            let newWidth = max(img.size.width * scale, minDimension)
            let newHeight = max(img.size.height * scale, minDimension)
            let newSize = CGSize(width: newWidth, height: newHeight)
            let renderer = UIGraphicsImageRenderer(size: newSize)
            scaledImage = renderer.image { _ in
                img.draw(in: CGRect(origin: .zero, size: newSize))
            }
        } else if img.size.width < minDimension || img.size.height < minDimension {
            // Image is too small — skip scaling so we keep JPEG quality high
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

        // If the smallest image is still too large, return the smallest we can make
        return bestData ?? scaledImage.jpegData(compressionQuality: 0.1)
    }
}