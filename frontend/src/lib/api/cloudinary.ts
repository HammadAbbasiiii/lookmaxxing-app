// Direct Cloudinary upload (§4.4, §8.5). Image bytes never pass through the
// 512 MB backend worker — they go straight to Cloudinary with a signed request.

import { CLOUDINARY_UPLOAD_URL } from "@/lib/constants";
import type { UploadSignature } from "@/lib/zod";

export async function uploadDirectToCloudinary(
  signature: UploadSignature,
  file: File | Blob,
): Promise<string> {
  const url = `${CLOUDINARY_UPLOAD_URL}/${signature.cloud_name}/image/upload`;
  const form = new FormData();
  form.append("file", file);
  form.append("api_key", signature.api_key);
  form.append("timestamp", String(signature.timestamp));
  form.append("signature", signature.signature);
  form.append("folder", signature.folder);
  form.append("public_id", signature.public_id);
  if (signature.upload_preset) form.append("upload_preset", signature.upload_preset);

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20_000);
  let response: Response;
  try {
    response = await fetch(url, { method: "POST", body: form, signal: controller.signal });
  } catch (error) {
    clearTimeout(timer);
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Upload is taking too long. Try a smaller photo.");
    }
    throw new Error("No connection. Check your signal.");
  }
  clearTimeout(timer);

  if (!response.ok) {
    throw new Error("Image upload failed. Try again.");
  }

  const data: unknown = await response.json().catch(() => null);
  const secureUrl =
    data && typeof data === "object" ? (data as Record<string, unknown>).secure_url : null;
  if (typeof secureUrl !== "string" || secureUrl.length === 0) {
    throw new Error("Image upload failed. Try again.");
  }
  return secureUrl;
}
