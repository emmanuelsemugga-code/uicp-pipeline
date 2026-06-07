# ============================================================
# Validate app/auth.py — GAP‑18 Enhanced Decorator
# ============================================================
!pip install flask -q

import os, json, sqlite3, tempfile
from flask import Flask, request, jsonify, g

# ── In‑memory SQLite database (simulates PostgreSQL for Colab) ──
db_path = tempfile.NamedTemporaryFile(delete=False).name
conn = sqlite3.connect(db_path)
conn.execute("CREATE TABLE IF NOT EXISTS tenants (id TEXT PRIMARY KEY, name TEXT, status TEXT DEFAULT 'ACTIVE')")
conn.execute("CREATE TABLE IF NOT EXISTS api_keys (key TEXT PRIMARY KEY, tenant_id TEXT, active INTEGER DEFAULT 1)")
conn.execute("INSERT OR IGNORE INTO tenants(id,name) VALUES ('hosp-a','Hospital A')")
conn.execute("INSERT OR IGNORE INTO api_keys(key,tenant_id) VALUES ('sk-hosp-a-abc123','hosp-a')")
conn.commit()

# ── EXACT content of app/auth.py (paste from your commit) ──
import hmac
from functools import wraps

class AuthenticationError(Exception):
    pass

def get_api_key_from_env() -> str:
    key = os.environ.get("API_KEY")
    if not key:
        raise ValueError("FATAL: API_KEY environment variable not set.")
    if len(key) < 8:
        raise ValueError("FATAL: API_KEY must be at least 8 characters.")
    return key

def verify_api_key(provided_key: str, expected_key: str) -> bool:
    return hmac.compare_digest(provided_key, expected_key)

def extract_tenant_from_key(key: str) -> str | None:
    static_key = os.environ.get("API_KEY")
    if static_key and hmac.compare_digest(key, static_key):
        return "default"
    if not key.startswith("sk-"):
        return None
    parts = key.split("-", 2)
    if len(parts) < 3:
        return None
    tenant_id = parts[1]
    try:
        cur = conn.cursor()
        cur.execute("SELECT tenant_id FROM api_keys WHERE key=? AND active=1", (key,))
        row = cur.fetchone()
        if row:
            return row[0]
    except Exception:
        pass
    return None

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get("X-API-Key", "")
        tenant_id = extract_tenant_from_key(provided_key)
        if not tenant_id:
            return jsonify({"error":True,"error_type":"INVALID_API_KEY","message":"X-API-Key is missing or invalid","retryable":False,"request_id":g.get("request_id","unknown")}), 401
        g.tenant_id = tenant_id
        return f(*args, **kwargs)
    return decorated_function

def mask_api_key(key: str, visible_chars: int = 8) -> str:
    if len(key) <= visible_chars:
        return "***"
    return key[:visible_chars] + "..."

# ── Flask test app ──
os.environ["API_KEY"] = "sk-static-fallback"
app = Flask(__name__)

@app.route('/test', methods=['GET'])
@require_api_key
def test():
    return jsonify({"tenant_id": g.tenant_id}), 200

client = app.test_client()
passed = failed = 0
def check(label, condition):
    global passed, failed
    if condition: passed += 1; print(f"  PASS  {label}")
    else: failed += 1; print(f"  FAIL  {label}")

print("=== app/auth.py GAP‑18 Validation ===\n")

# 1. Structured key extracts tenant
resp = client.get('/test', headers={"X-API-Key":"sk-hosp-a-abc123"})
check("Structured key → tenant 'hosp-a'", resp.status_code==200 and resp.json["tenant_id"]=="hosp-a")

# 2. Static fallback key
resp = client.get('/test', headers={"X-API-Key":"sk-static-fallback"})
check("Static fallback key → tenant 'default'", resp.status_code==200 and resp.json["tenant_id"]=="default")

# 3. Invalid structured key
resp = client.get('/test', headers={"X-API-Key":"sk-fake-xyz"})
check("Invalid structured key → 401", resp.status_code==401)

# 4. Missing key
resp = client.get('/test')
check("Missing key → 401", resp.status_code==401)

# 5. Malformed key
resp = client.get('/test', headers={"X-API-Key":"bad-key"})
check("Malformed key → 401", resp.status_code==401)

# 6. get_api_key_from_env works
os.environ["API_KEY"] = "sk-test-long-enough"
check("get_api_key_from_env returns key", get_api_key_from_env()=="sk-test-long-enough")

# 7. Short key rejected
os.environ["API_KEY"] = "short"
try:
    get_api_key_from_env()
    check("Short API_KEY raises ValueError", False)
except ValueError:
    check("Short API_KEY raises ValueError", True)

# 8. Missing key rejected
del os.environ["API_KEY"]
try:
    get_api_key_from_env()
    check("Missing API_KEY raises ValueError", False)
except ValueError:
    check("Missing API_KEY raises ValueError", True)

# 9. verify_api_key constant‑time comparison
check("verify_api_key matches", verify_api_key("abc","abc")==True)
check("verify_api_key rejects mismatch", verify_api_key("abc","xyz")==False)

# 10. mask_api_key
check("mask_api_key masks", mask_api_key("sk-test-abc123")=="sk-test-...")
check("mask_api_key short", mask_api_key("short")=="***")

print(f"\n=== Results: {passed}/{passed+failed} passed ===")
if failed == 0:
    print("✓ app/auth.py GAP‑18 VALIDATED — ready for commit\n")
else:
    print("✗ FIX FAILURES BEFORE COMMIT\n")
