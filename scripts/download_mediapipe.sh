#!/bin/bash
# download_mediapipe.sh — Ensure MediaPipe face landmarker model is available
# Usage: bash scripts/download_mediapipe.sh

set -euo pipefail

MODEL_DIR="/opt/render/project/src/backend/app/ml"
MODEL_PATH="${MODEL_DIR}/face_landmarker.task"
MODEL_URL="https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"

echo "📥 Checking MediaPipe face landmarker model..."

mkdir -p "$MODEL_DIR"

if [ -f "$MODEL_PATH" ]; then
    echo "✅ MediaPipe model already exists: $MODEL_PATH"
    ls -la "$MODEL_PATH"
    exit 0
fi

echo "📥 Downloading from $MODEL_URL ..."
curl -fsSL -o "$MODEL_PATH" "$MODEL_URL"

if [ -f "$MODEL_PATH" ]; then
    echo "✅ MediaPipe model downloaded successfully: $MODEL_PATH"
    ls -la "$MODEL_PATH"
else
    echo "❌ MediaPipe model download FAILED!"
    exit 1
fi