package com.lookmaxxing.viewmodels

import android.content.Context
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.lookmaxxing.utils.ImageCompressor
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException

/**
 * ViewModel that compresses a photo client-side, uploads it to the
 * lookmaxxing API, and polls for analysis completion.
 *
 * Usage (Compose):
 * ```
 * val vm: PhotoUploadViewModel = viewModel()
 * vm.upload(context, imageUri)
 * val state by vm.uploadState.collectAsState()
 * ```
 */
class PhotoUploadViewModel : ViewModel() {

    // ── UI state ────────────────────────────────────────────────
    data class UploadUiState(
        val isUploading: Boolean = false,
        val photoId: String? = null,
        val fileUrl: String? = null,
        val analysisStatus: String? = null, // "processing" | "completed" | "failed"
        val score: Double? = null,
        val error: String? = null,
        val progressMessage: String = ""
    )

    private val _state = MutableStateFlow(UploadUiState())
    val uploadState: StateFlow<UploadUiState> = _state

    // ── Configuration ───────────────────────────────────────────
    var apiBaseUrl: String = "https://lookmaxx-api.onrender.com/api/v1"
    var authToken: String = ""

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
        .writeTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
        .readTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
        .build()

    // ── Public API ──────────────────────────────────────────────

    /**
     * Compress + upload the selected image, then poll for status.
     */
    fun upload(context: Context, imageUri: Uri) {
        viewModelScope.launch {
            _state.value = _state.value.copy(isUploading = true, error = null,
                progressMessage = "Compressing…")

            try {
                // 1. Compress
                val compressedData = withContext(Dispatchers.IO) {
                    ImageCompressor.compressImage(context, imageUri)
                } ?: throw IOException("Image compression returned null")

                val fileSizeKB = compressedData.size / 1024.0
                _state.value = _state.value.copy(
                    progressMessage = "Compressed to ${"%.1f".format(fileSizeKB)} KB"
                )

                // 2. Upload
                _state.value = _state.value.copy(progressMessage = "Uploading…")
                val photoResponse = withContext(Dispatchers.IO) {
                    uploadBytes(compressedData, "photo.jpg")
                }

                val photoId = photoResponse.getString("id")
                val status = photoResponse.optString("analysis_status", "processing")
                _state.value = _state.value.copy(
                    photoId = photoId,
                    fileUrl = photoResponse.optString("file_url"),
                    analysisStatus = status,
                    progressMessage = "Upload done — analysing…"
                )

                // 3. Poll for completion
                if (status == "processing" || status == "pending") {
                    pollStatus(photoId)
                }
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    error = e.message ?: "Unknown error",
                    isUploading = false
                )
            }
        }
    }

    /** Poll GET /photos/{id}/status every 1.5 s until completed or failed. */
    private suspend fun pollStatus(photoId: String) {
        for (attempt in 1..15) {
            delay(1_500)
            try {
                val json = withContext(Dispatchers.IO) { getStatus(photoId) }
                val status = json.optString("analysis_status", "processing")
                _state.value = _state.value.copy(analysisStatus = status)

                when (status) {
                    "completed" -> {
                        _state.value = _state.value.copy(
                            score = json.optDouble("score"),
                            isUploading = false,
                            progressMessage = "Complete!"
                        )
                        return
                    }
                    "failed" -> {
                        _state.value = _state.value.copy(
                            error = "Analysis failed on server",
                            isUploading = false
                        )
                        return
                    }
                }
            } catch (_: Exception) {
                // Retry on network hiccup
            }
        }
        _state.value = _state.value.copy(
            error = "Analysis timed out after 15 polls",
            isUploading = false
        )
    }

    // ── HTTP helpers ────────────────────────────────────────────

    @Throws(IOException::class)
    private fun uploadBytes(data: ByteArray, fileName: String): JSONObject {
        val mediaType = "image/jpeg".toMediaType()
        val body = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart(
                "file", fileName,
                data.toRequestBody(mediaType)
            )
            .build()

        val request = Request.Builder()
            .url("$apiBaseUrl/photos/upload")
            .header("Authorization", "Bearer $authToken")
            .post(body)
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                val errBody = response.body?.string() ?: ""
                throw IOException("Upload failed (HTTP ${response.code}): $errBody")
            }
            val responseBody = response.body?.string() ?: throw IOException("Empty response body")
            return JSONObject(responseBody)
        }
    }

    @Throws(IOException::class)
    private fun getStatus(photoId: String): JSONObject {
        val request = Request.Builder()
            .url("$apiBaseUrl/photos/$photoId/status")
            .header("Authorization", "Bearer $authToken")
            .get()
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                throw IOException("Status check failed (HTTP ${response.code})")
            }
            val body = response.body?.string() ?: throw IOException("Empty response body")
            return JSONObject(body)
        }
    }
}