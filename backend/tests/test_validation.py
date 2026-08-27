"""
Regression tests for image pre-validation (Phase 2).

These lock in the deterministic quality gates — size, brightness, contrast
and blur — which run before any AI scoring. Face-presence checks are not
asserted here because they depend on MediaPipe / a Haar cascade being
available at runtime (in local CI the MediaPipe model file is absent and the
Haar cascade XML may not be bundled), and the service intentionally fails
open rather than blocking every upload when no detector is present.
"""
import io

import numpy as np
import pytest
from PIL import Image

from app.services.validation_service import validate_image


def _png_bytes(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr.astype(np.uint8)).save(buf, "PNG")
    return buf.getvalue()


def test_rejects_too_small():
    result = validate_image(_png_bytes(np.zeros((50, 50, 3))))
    assert result["valid"] is False
    assert "small" in result["error"]


def test_rejects_too_dark():
    result = validate_image(_png_bytes(np.zeros((400, 400, 3))))
    assert result["valid"] is False
    assert "dark" in result["error"]


def test_rejects_too_bright():
    result = validate_image(_png_bytes(np.full((400, 400, 3), 255)))
    assert result["valid"] is False
    assert "bright" in result["error"]


def test_rejects_low_contrast():
    # Uniform grey: mid brightness but essentially zero contrast.
    result = validate_image(_png_bytes(np.full((400, 400, 3), 128)))
    assert result["valid"] is False
    assert "contrast" in result["error"]


def test_rejects_blurry():
    # A smooth horizontal gradient has high contrast but near-zero Laplacian
    # variance, which the blur check flags as out-of-focus.
    grad = np.tile(np.linspace(0, 255, 400).astype(np.uint8).reshape(400, 1), (1, 400))
    img = np.stack([grad, grad, grad], axis=2)
    result = validate_image(_png_bytes(img))
    assert result["valid"] is False
    assert "blurry" in result["error"]
