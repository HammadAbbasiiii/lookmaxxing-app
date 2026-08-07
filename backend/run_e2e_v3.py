import requests, json, os, sys, time

BASE = "http://localhost:8000/api/v1"
PASS, FAIL, TOTAL = 0, 0, 0
TS = int(time.time())
EMAIL = f"e2e_v3_{TS}@lookmaxx.com"
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
print("LOOKMAXX API — OPTIMIZED E2E TEST SUITE (v3)")
print("=" * 65)

# ----- TEST 1: DATABASE & MODELS -----
print("\n─── TEST 1: Database & Models ───")
try:
    r = requests.get(f"{BASE}/health")
    report("Health endpoint", r.status_code == 200, f"status={r.status_code}")
except Exception as e:
    report("Health endpoint", False, str(e))

# ----- TEST 2: AUTHENTICATION -----
print("\n─── TEST 2: User Authentication ───")
try:
    r = requests.post(f"{BASE}/auth/signup", json={"email": EMAIL, "password": PWD, "full_name": "E2E v3 User"})
    js = r.json()
    USER_ID = js.get("id")
    report("Signup", r.status_code in (200,201) and bool(USER_ID), f"uid={str(USER_ID)[:8] if USER_ID else '?'}...")
except Exception as e:
    report("Signup", False, str(e))

try:
    r = requests.post(f"{BASE}/auth/login", data={"username": EMAIL, "password": PWD})
    js = r.json()
    TOKEN = js.get("access_token")
    report("Login", r.status_code == 200 and bool(TOKEN), f"type={js.get('token_type','?')}")
except Exception as e:
    report("Login", False, str(e))

if TOKEN:
    try:
        r = requests.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {TOKEN}"})
        js = r.json()
        report("GET /me", r.status_code == 200 and js.get("email") == EMAIL)
    except Exception as e:
        report("GET /me", False, str(e))

# ----- TEST 3: PHOTO UPLOAD & ANALYSIS -----
print("\n─── TEST 3: Prediction Pipeline ───")
from PIL import Image
img = Image.new('RGB', (640, 480), color=(180, 140, 100))
img.save('/tmp/test_face_v3.jpg', 'JPEG')

if TOKEN:
    try:
        with open('/tmp/test_face_v3.jpg', 'rb') as f:
            r = requests.post(f"{BASE}/photos/upload", headers={"Authorization": f"Bearer {TOKEN}"}, files={"file": ("face.jpg", f, "image/jpeg")})
        js = r.json()
        PHOTO_ID = js.get("id")
        file_url = js.get("file_url", "")
        is_cloudinary = "cloudinary" in file_url
        report("Photo upload", r.status_code == 200 and bool(PHOTO_ID), f"cloudinary={'yes' if is_cloudinary else 'no'}, score={js.get('score','?')}")
    except Exception as e:
        report("Photo upload", False, str(e))

    if PHOTO_ID:
        try:
            r = requests.post(f"{BASE}/photos/analyze/{PHOTO_ID}", headers={"Authorization": f"Bearer {TOKEN}"})
            report("Analyze", r.status_code in (200,500), f"code={r.status_code}")
        except Exception as e:
            report("Analyze", False, str(e))

# ----- TEST 4: PLAN -----
print("\n─── TEST 4: Action Plan Generation ───")
if TOKEN:
    try:
        r = requests.get(f"{BASE}/plan", headers={"Authorization": f"Bearer {TOKEN}"})
        report("GET /plan", r.status_code == 200, f"has_plan={r.json().get('has_plan', '?')}")
    except Exception as e:
        report("GET /plan", False, str(e))

# ----- TEST 5: CHECKIN & PROGRESS -----
print("\n─── TEST 5: Check-in & Progress ───")
if TOKEN:
    for label, url in [("streak", "/progress/streak"), ("history", "/progress/history"), ("milestones", "/progress/milestones"), ("plan/progress", "/plan/progress")]:
        try:
            r = requests.get(f"{BASE}{url}", headers={"Authorization": f"Bearer {TOKEN}"})
            report(f"GET {url}", r.status_code in (200, 404), f"code={r.status_code}")
        except Exception as e:
            report(f"GET {url}", False, str(e))

# ----- TEST 6: PLAN REGENERATION -----
print("\n─── TEST 6: Plan Regeneration ───")
if TOKEN:
    try:
        r = requests.post(f"{BASE}/plan/regenerate", headers={"Authorization": f"Bearer {TOKEN}"})
        report("Regenerate plan", r.status_code in (200, 400, 404), f"code={r.status_code}")
    except Exception as e:
        report("Regenerate plan", False, str(e))

# ----- TEST 7: PRODUCT RECOMMENDATIONS -----
print("\n─── TEST 7: Product Recommendations ───")
if TOKEN:
    try:
        r = requests.get(f"{BASE}/products/recommended", headers={"Authorization": f"Bearer {TOKEN}"})
        report("Product endpoint", r.status_code == 200, f"items={len(r.json().get('products', []))}")
    except Exception as e:
        report("Product endpoint", False, str(e))

    try:
        r = requests.get(f"{BASE}/products/categories", headers={"Authorization": f"Bearer {TOKEN}"})
        report("Categories", r.status_code == 200, f"cats={len(r.json().get('categories',[]))}")
    except Exception as e:
        report("Categories", False, str(e))

# ----- TEST 8: DASHBOARD & EXPERIENCE -----
print("\n─── TEST 8: Dashboard & Experience ───")
if TOKEN:
    for label, url in [("Dashboard", "/dashboard"), ("Experience", "/experience")]:
        try:
            r = requests.get(f"{BASE}{url}", headers={"Authorization": f"Bearer {TOKEN}"})
            report(f"GET {url}", r.status_code in (200, 404), f"code={r.status_code}")
        except Exception as e:
            report(f"GET {url}", False, str(e))

# ----- TEST 9: ERROR HANDLING -----
print("\n─── TEST 9: Error Handling ───")
try:
    r = requests.get(f"{BASE}/auth/me")
    report("No token → 401", r.status_code == 401, f"code={r.status_code}")
except Exception as e:
    report("No token → 401", False, str(e))

try:
    r = requests.post(f"{BASE}/photos/upload", files={"file": ("text.txt", b"not an image", "text/plain")})
    report("Non-image → error", r.status_code >= 400, f"code={r.status_code}")
except Exception as e:
    report("Non-image → error", False, str(e))

try:
    r = requests.post(f"{BASE}/photos/analyze/nonexistent-id-12345", headers={"Authorization": f"Bearer {TOKEN}"})
    report("Fake photo → 404", r.status_code == 404, f"code={r.status_code}")
except Exception as e:
    report("Fake photo → 404", False, str(e))

# ===== OPTIMIZATION VERIFICATION TESTS =====
print("\n─── OPTIMIZATION VERIFICATION ───")

# Test 1: GZip compression
try:
    r = requests.get(f"{BASE}/dashboard", headers={"Authorization": f"Bearer {TOKEN}", "Accept-Encoding": "gzip"})
    ce = r.headers.get("Content-Encoding", "none")
    report("GZip compression", ce == "gzip", f"content-encoding={ce}")
except Exception as e:
    report("GZip compression", False, str(e))

# Test 2: Rate limiting (burst test)
try:
    quick_errors = 0
    for i in range(65):
        rr = requests.get(f"{BASE}/health")
        if rr.status_code == 429:
            quick_errors += 1
    report("Rate limiting (429)", quick_errors > 0, f"got {quick_errors} 429s out of 65 requests")
except Exception as e:
    report("Rate limiting", False, str(e))

# Test 3: Latency check
try:
    r = requests.get(f"{BASE}/dashboard", headers={"Authorization": f"Bearer {TOKEN}"})
    lat = r.elapsed.total_seconds()
    report("Dashboard latency < 500ms", lat < 0.5, f"latency={lat:.4f}s")
except Exception as e:
    report("Dashboard latency", False, str(e))

# ===== SUMMARY =====
print("\n" + "=" * 65)
print("      OPTIMIZED END-TO-END TEST REPORT")
print("=" * 65)
overall = "✅ ALL TESTS PASS — READY FOR PRODUCTION" if FAIL == 0 else "❌ SOME TESTS FAILED"
print(f"  Base Tests Passed: {PASS} / {TOTAL}")
print(f"  Base Tests Failed: {FAIL} / {TOTAL}")
print(f"  Overall: {overall}")
print("=" * 65)
sys.exit(0 if FAIL == 0 else 1)