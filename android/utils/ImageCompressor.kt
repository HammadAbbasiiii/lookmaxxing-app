package com.lookmaxxing.utils

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import java.io.ByteArrayOutputStream
import java.io.InputStream

/**
 * Client-side image compression for the LookMaxxing Android app.
 *
 * Why compress?
 * - Model input is 224×224 — extra pixels are wasted bandwidth
 * - Face detection (MediaPipe) works at 800×800 — no need for 4000×3000 raw files
 * - JPEG quality 70–80 % is visually lossless on phone screens
 * - Target: 200–500 KB instead of 10–12 MB → upload drops from ~10 s to ~2 s
 *
 * Usage:
 * ```
 * val data = ImageCompressor.compressImage(context, imageUri)
 * // upload data to the API
 * ```
 */
object ImageCompressor {

    // ── Parameters ──────────────────────────────────────────────
    private const val MAX_DIMENSION = 1200           // 5.3× more than model needs
    private const val DEFAULT_QUALITY = 75           // 0–100 scale (75 → 0.75 JPEG)
    private const val MAX_SIZE_BYTES = 500 * 1024L   // cap at 500 KB
    private const val MIN_EDGE = 400                 // below this → skip resize
    private const val BITMAP_CONFIG = Bitmap.Config.RGB_565  // memory-efficient

    /**
     * Load, resize, and compress an image from a content:// URI.
     *
     * @param context  Android context (for ContentResolver)
     * @param uri      Content URI of the selected image
     * @param maxDim   Max width or height in pixels
     * @param quality  JPEG quality 0–100
     * @param maxBytes Hard cap on output byte-array size
     * @return Compressed JPEG bytes, or null if decoding fails
     */
    fun compressImage(
        context: Context,
        uri: Uri,
        maxDim: Int = MAX_DIMENSION,
        quality: Int = DEFAULT_QUALITY,
        maxBytes: Long = MAX_SIZE_BYTES
    ): ByteArray? {
        // 1. Decode only the dimensions first (no pixel allocation)
        val options = BitmapFactory.Options().apply {
            inJustDecodeBounds = true
        }
        context.contentResolver.openInputStream(uri)?.use { stream ->
            BitmapFactory.decodeStream(stream, null, options)
        } ?: return null

        val (origW, origH) = options.outWidth to options.outHeight

        // 2. Calculate inSampleSize to avoid loading massive bitmaps into memory
        val sampleSize = calculateInSampleSize(origW, origH, maxDim)
        val decodeOpts = BitmapFactory.Options().apply {
            inSampleSize = sampleSize
            inPreferredConfig = BITMAP_CONFIG
        }

        var bitmap: Bitmap? = null
        context.contentResolver.openInputStream(uri)?.use { stream ->
            bitmap = BitmapFactory.decodeStream(stream, null, decodeOpts)
        }
        bitmap ?: return null

        try {
            // 3. If still too large after sub-sampling, do precise resize
            val (targetW, targetH) = calcDimensions(bitmap!!.width, bitmap.height, maxDim)
            val resized = if (targetW < MIN_EDGE || targetH < MIN_EDGE) {
                bitmap // already small enough
            } else if (targetW != bitmap.width || targetH != bitmap.height) {
                val scaled = Bitmap.createScaledBitmap(bitmap!!, targetW, targetH, true)
                bitmap.recycle()
                scaled
            } else {
                bitmap
            }

            // 4. Encode to JPEG, incrementally reducing quality until ≤ maxBytes
            var q = quality
            var data: ByteArray
            do {
                data = resized.toJpegBytes(q)
                q -= 5
            } while (data.size > maxBytes && q >= 30)

            val origKB: Double = try {
                context.contentResolver.openInputStream(uri)?.use { it.available().toDouble() / 1024.0 } ?: 0.0
            } catch (_: Exception) { 0.0 }

            android.util.Log.d(
                "ImageCompressor",
                "📦 Compressed %.1f KB → %.1f KB (%d×%d, q=%d)".format(
                    origKB, data.size / 1024.0, resized.width, resized.height, q
                )
            )

            return data
        } finally {
            bitmap?.recycle()
        }
    }

    /** Convenience overload for Bitmap input (e.g., from camera capture). */
    fun compressImage(
        bitmap: Bitmap,
        maxDim: Int = MAX_DIMENSION,
        quality: Int = DEFAULT_QUALITY,
        maxBytes: Long = MAX_SIZE_BYTES
    ): ByteArray {
        val (targetW, targetH) = calcDimensions(bitmap.width, bitmap.height, maxDim)
        val resized = if (targetW < MIN_EDGE || targetH < MIN_EDGE) {
            bitmap
        } else if (targetW != bitmap.width || targetH != bitmap.height) {
            Bitmap.createScaledBitmap(bitmap, targetW, targetH, true)
        } else {
            bitmap
        }

        var q = quality
        var data: ByteArray
        do {
            data = resized.toJpegBytes(q)
            q -= 5
        } while (data.size > maxBytes && q >= 30)

        if (resized !== bitmap) resized.recycle()

        return data
    }

    // ── helpers ─────────────────────────────────────────────────

    private fun calculateInSampleSize(origW: Int, origH: Int, maxDim: Int): Int {
        var sampleSize = 1
        val maxEdge = maxOf(origW, origH)
        if (maxEdge > maxDim) {
            val halfW = origW / 2
            val halfH = origH / 2
            // Scale down until both dimensions are <= maxDim
            while ((halfW / sampleSize) > maxDim || (halfH / sampleSize) > maxDim) {
                sampleSize *= 2
            }
        }
        return sampleSize
    }

    private fun calcDimensions(origW: Int, origH: Int, maxDim: Int): Pair<Int, Int> {
        if (origW > origH) {
            if (origW <= maxDim) return origW to origH
            return maxDim to ((origH.toFloat() / origW) * maxDim).toInt()
        }
        if (origH <= maxDim) return origW to origH
        return (((origW.toFloat() / origH) * maxDim).toInt()) to maxDim
    }

    private fun Bitmap.toJpegBytes(quality: Int): ByteArray {
        val stream = ByteArrayOutputStream()
        this.compress(Bitmap.CompressFormat.JPEG, quality, stream)
        return stream.toByteArray()
    }
}