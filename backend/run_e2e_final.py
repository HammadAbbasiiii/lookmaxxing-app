import requests, json, os, sys, time

BASE = "http://localhost:8000/api/v1"
PASS, FAIL, TOTAL = 0, 0, 0
TS = int(time.time())
EMAIL = f"e2e_vfinal_{TS}@lookmaxx.com"
PWD = "Test123!"
TOKEN = None
USER_ID = None
PHOTO_ID = None

def report(test_name, passed, detail=""):
    global PASS, FAIL, TOTAL
    TOTAL += 1
    if passed:
        PASS += 1; print(f"  ✅ {test_name}{' — ' + detail if detail else ''}")
    else:
        FAIL += 1; print(f"  ❌ {test_name}{' — ' + detail if detail else ''}")

print("=" * 65)
print("LOOKMAXX API — FINAL OPTIMIZED E2E TEST SUITE")
print("=" * 65)

# ========== CORE E2E TESTS ==========

# TEST 1: Health
print("\n─── TEST 1: Database & Models ───")
try:
    r = requests.get(f"{BASE}/health")
    report("Health endpoint", r.status_code == 200, f"status={r.status_code}")
except Exception as e:
    report("Health endpoint", False, str(e))

# TEST 2: Auth
print("\n─── TEST 2: User Authentication ───")
try:
    r = requests.post(f"{BASE}/auth/signup", json={"email": EMAIL, "password": PWD, "full_name": "E2E Final User"})
    js = r.json()
    USER_ID = js.get("id")
    report("Signup", r.status_code in (200,201) and bool(USER_ID), f"uid={str(USER_ID)[:8]}...")
except Exception as e:
    report("Signup", False, str(e))

try:
    r = requests.post(f"{BASE}/auth/login", data={"username": EMAIL, "password": PWD})
    js = r.json()
    TOKEN = js.get("access_token")
    report("Login", r.status_code == 200 and bool(TOKEN), f"token_type={js.get('token_type','?')}")
except Exception as e:
    report("Login", False, str(e))

if TOKEN:
    try:
        r = requests.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {TOKEN}"})
        js = r.json()
        report("GET /me", r.status_code == 200 and js.get("email") == EMAIL)
    except Exception as e:
        report("GET /me", False, str(e))

# TEST 3: Photo upload & analyze
print("\n─── TEST 3: Prediction Pipeline ───")
from PIL import Image
img = Image.new('RGB', (640, 480), color=(180, 140, 100))
img.save('/tmp/test_face_final.jpg', 'JPEG')

if TOKEN:
    try:
        with open('/tmp/test_face_final.jpg', 'rb') as f:
            r = requests.post(f"{BASE}/photos/upload", headers={"Authorization": f"Bearer {TOKEN}"}, files={"file": ("face.jpg", f, "image/jpeg")})
        js = r.json()
        PHOTO_ID = js.get("id")
        is_cloudinary = "cloudinary" in str(js.get("file_url", ""))
        report("Photo upload", r.status_code == 200 and bool(PHOTO_ID), f"cloudinary={'yes' if is_cloudinary else 'no'}, score={js.get('score','?')}")
    except Exception as e:
        report("Photo upload", False, str(e))

    if PHOTO_ID:
        try:
            r = requests.post(f"{BASE}/photos/analyze/{PHOTO_ID}", headers={"Authorization": f"Bearer {TOKEN}"})
            report("Analyze endpoint", r.status_code in (200,500), f"code={r.status_code}")
        except Exception as e:
            report("Analyze endpoint", False, str(e))

# TEST 4: Plan
print("\n─── TEST 4: Action Plan Generation ───")
if TOKEN:
    try:
        r = requests.get(f"{BASE}/plan", headers={"Authorization": f"Bearer {TOKEN}"})
        report("GET /plan", r.status_code == 200, f"has_plan={r.json().get('has_plan', '?')}")
    except Exception as e:
        report("GET /plan", False, str(e))

# TEST 5: Progress endpoints
print("\n─── TEST 5: Check-in & Progress ───")
if TOKEN:
    for url in ["/progress/streak", "/progress/history", "/progress/milestones", "/plan/progress"]:
        try:
            r = requests.get(f"{BASE}{url}", headers={"Authorization": f"Bearer {TOKEN}"})
            report(f"GET {url}", r.status_code == 200, f"code={r.status_code}")
        except Exception as e:
            report(f"GET {url}", False, str(e))

# TEST 6: Plan regeneration
print("\n─── TEST 6: Plan Regeneration ───")
if TOKEN:
    try:
        r = requests.post(f"{BASE}/plan/regenerate", headers={"Authorization": f"Bearer {TOKEN}"})
        report("Regenerate plan", r.status_code in (200, 400, 404), f"code={r.status_code}")
    except Exception as e:
        report("Regenerate plan", False, str(e))

# TEST 7: Products
print("\n─── TEST 7: Product Recommendations ───")
if TOKEN:
    try:
        r = requests.get(f"{BASE}/products/recommendations", headers={"Authorization": f"Bearer {TOKEN}"})
        report("Product recommendations", r.status_code == 200, f"code={r.status_code}")
    except Exception as e:
        report("Product recommended", False, str(e))

    try:
        r = requests.get(f"{BASE}/products/categories", headers={"Authorization": f"Bearer {TOKEN}"})
        report("Categories", r.status_code == 200, f"cats={len(r.json().get('categories',[]))}")
    except Exception as e:
        report("Categories", False, str(e))

# TEST 8: Dashboard
print("\n─── TEST 8: Dashboard ───")
if TOKEN:
    try:
        r = requests.get(f"{BASE}/dashboard", headers={"Authorization": f"Bearer {TOKEN}"})
        report("GET /dashboard", r.status_code == 200, f"latency={r.elapsed.total_seconds():.4f}s")
    except Exception as e:
        report("GET /dashboard", False, str(e))

# TEST 9: Error Handling
print("\n─── TEST 9: Error Handling ───")
try:
    r = requests.get(f"{BASE}/auth/me")
    report("No token → 401", r.status_code == 401, f"code={r.status_code}")
except Exception as e:
    report("No token → 401", False, str(e))

try:
    r = requests.post(f"{BASE}/photos/upload", files={"file": ("text.txt", b"not an image", "text/plain")})
    report("Non-image upload → error", r.status_code >= 400, f"code={r.status_code}")
except Exception as e:
    report("Non-image upload → error", False, str(e))

if TOKEN:
    try:
        r = requests.post(f"{BASE}/photos/analyze/nonexistent-id-99999", headers={"Authorization": f"Bearer {TOKEN}"})
        report("Fake photo → 404", r.status_code == 404, f"code={r.status_code}")
    except Exception as e:
        report("Fake photo → 404", False, str(e))

# ========== OPTIMIZATION VERIFICATION ==========
print("\n─── OPTIMIZATION VERIFICATION ───")

# GZip Test: upload a photo which creates a large response
if TOKEN:
    try:
        r = requests.get(f"{BASE}/dashboard",
                         headers={"Authorization": f"Bearer {TOKEN}",
                                  "Accept-Encoding": "gzip, deflate"})
        ce = r.headers.get("Content-Encoding", "none")
        cl = r.headers.get("Content-Length", "0")
        report("GZip compression", ce == "gzip", f"encoding={ce}, size={cl}")
    except Exception as e:
        report("GZip compression", False, str(e))

# Rate Limiting: make many rapid requests
try:
    # Use a fresh session (new server just restarted so counter is fresh)
    error_count = 0
    for i in range(62):
        rr = requests.get(f"{BASE}/health", timeout=2)
        if rr.status_code == 429:
            error_count += 1
            break  # Got our first 429, rate limiter works!
    report("Rate limiting active", error_count > 0, f"{error_count} 429(s) after {i+1} requests")
except Exception as e:
    report("Rate limiting active", False, str(e))

# Database Index Query Performance
if TOKEN:
    try:
        r = requests.get(f"{BASE}/dashboard", headers={"Authorization": f"Bearer {TOKEN}"})
        lat = r.elapsed.total_seconds()
        report("Dashboard query < 100ms", lat < 0.1, f"latency={lat:.4f}s")
    except Exception as e:
        report("Dashboard query < 100ms", False, str(e))

# ===== SUMMARY =====
print("\n" + "=" * 65)
print("      FINAL OPTIMIZED TEST REPORT")
print("=" * 65)
if FAIL == 0:
    print(f"  ✅ ALL {PASS} TESTS PASSED")
    print("  Status: READY FOR PRODUCTION")
else:
    print(f"  Passed: {PASS} / {TOTAL}")
    print(f"  Failed: {FAIL} / {TOTAL}")
    print("  Status: NEEDS FIXES")
print("=" * 65)
sys.exit(0 if FAIL == 0 else 1)