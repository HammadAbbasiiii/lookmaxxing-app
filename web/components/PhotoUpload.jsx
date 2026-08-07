import React, { useState } from "react";
import { compressImage } from "../utils/compressImage";

/**
 * Minimal photo-upload component that compresses the file client-side
 * before uploading to the lookmaxxing API.
 *
 * Props:
 *   - authToken  (string)  Bearer token from login
 *   - onUploaded (function) Called with { photoId, fileUrl, status }
 *   - apiBaseUrl (string)  Defaults to Render endpoint
 */
export default function PhotoUpload({
  authToken,
  onUploaded,
  apiBaseUrl = "https://lookmaxx-api.onrender.com/api/v1",
}) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState(null);

  async function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setError(null);
    setUploading(true);
    setProgress("Compressing…");

    try {
      // 1. Client-side compression
      const compressed = await compressImage(file);
      setProgress(
        `Compressed ${(file.size / 1024 / 1024).toFixed(1)} MB → ` +
          `${(compressed.size / 1024).toFixed(1)} KB`
      );

      // 2. Build form data
      const fd = new FormData();
      fd.append("file", compressed, file.name);

      // 3. Upload
      setProgress("Uploading…");
      const res = await fetch(`${apiBaseUrl}/photos/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${authToken}` },
        body: fd,
      });

      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Upload failed (HTTP ${res.status}): ${body}`);
      }

      const json = await res.json();
      setProgress("Done!");
      onUploaded?.({
        photoId: json.id,
        fileUrl: json.file_url,
        status: json.analysis_status,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", maxWidth: 360, margin: "0 auto" }}>
      <label
        style={{
          display: "block",
          padding: "16px 24px",
          background: uploading ? "#999" : "#4f46e5",
          color: "#fff",
          borderRadius: 8,
          textAlign: "center",
          cursor: uploading ? "not-allowed" : "pointer",
          fontWeight: 600,
          fontSize: 15,
        }}
      >
        {uploading ? progress : "📸 Select / Take Photo"}
        <input
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileChange}
          disabled={uploading}
          style={{ display: "none" }}
        />
      </label>

      {error && (
        <p style={{ color: "#dc2626", marginTop: 8, fontSize: 13 }}>⚠ {error}</p>
      )}
    </div>
  );
}