/**
 * Client-side image compression — resize + quality reduction so uploads
 * fit within 200–500 KB instead of sending raw 10+ MB phone-camera files.
 *
 * Why?
 * - Model input is 224×224 — extra pixels are wasted bandwidth
 * - Face detection runs at 800×800 — no need for 4000×3000 originals
 * - JPEG quality 70–80 % is visually lossless on phone screens
 *
 * Usage:
 *   const blob = await compressImage(file);
 *   formData.append("file", blob, file.name);
 */

const MAX_DIMENSION = 1200;        // 5.3× more than model's 224×224
const DEFAULT_QUALITY = 0.75;      // 70–80 % visually lossless
const MAX_SIZE_BYTES = 500 * 1024; // cap at 500 KB
const MIN_EDGE = 400;              // below this → skip resize (already small)

/**
 * Compress a File / Blob → JPEG Blob ready for upload.
 * @param {File|Blob} file - The raw image file from <input> or camera.
 * @param {Object} [opts]
 * @param {number} [opts.maxDimension=1200] - Max width or height in px.
 * @param {number} [opts.quality=0.75]      - JPEG quality 0–1.
 * @param {number} [opts.maxSizeBytes=500*1024] - Hard cap on output size.
 * @returns {Promise<Blob>} Compressed JPEG Blob.
 */
export async function compressImage(file, opts = {}) {
  const maxDimension = opts.maxDimension ?? MAX_DIMENSION;
  const quality = opts.quality ?? DEFAULT_QUALITY;
  const maxSize = opts.maxSizeBytes ?? MAX_SIZE_BYTES;

  // 1. Load image from File into an img element
  const img = await loadImage(file);
  const { naturalWidth: w, naturalHeight: h } = img;

  // 2. Calculate target dimensions (preserve aspect ratio)
  let { width, height } = calcDimensions(w, h, maxDimension);

  // If already smaller than MIN_EDGE, skip resize entirely
  if (width < MIN_EDGE || height < MIN_EDGE) {
    ({ width, height } = { width: w, height: h });
  }

  // 3. Draw resized image onto canvas
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(width);
  canvas.height = Math.round(height);
  const ctx = canvas.getContext("2d");
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

  // 4. Encode to JPEG, lowering quality until ≤ maxSize
  let q = quality;
  let blob = await canvasToBlob(canvas, q);

  while (blob.size > maxSize && q > 0.3) {
    q = Math.round((q - 0.05) * 100) / 100; // step down by 0.05
    blob = await canvasToBlob(canvas, q);
  }

  console.log(
    `📦 Compressed ${formatBytes(file.size)} → ${formatBytes(blob.size)} ` +
    `(${canvas.width}×${canvas.height}, q=${q.toFixed(2)})`
  );
  return blob;
}

// ── helpers ─────────────────────────────────────────────────────

function loadImage(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = e.target.result;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function calcDimensions(origW, origH, maxDim) {
  if (origW > origH) {
    if (origW <= maxDim) return { width: origW, height: origH };
    return { width: maxDim, height: (origH / origW) * maxDim };
  }
  if (origH <= maxDim) return { width: origW, height: origH };
  return { width: (origW / origH) * maxDim, height: maxDim };
}

function canvasToBlob(canvas, quality) {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) resolve(blob);
        else reject(new Error("Canvas toBlob returned null"));
      },
      "image/jpeg",
      quality
    );
  });
}

/** Human-readable byte formatter (e.g., "2.6 MB"). */
function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}