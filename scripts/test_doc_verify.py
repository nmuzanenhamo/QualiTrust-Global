"""Quick test script for the verify-with-document endpoint."""

import requests
import io

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def make_pdf(lines: list[str]) -> bytes:
    """Create a real PDF with the given text lines."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    y = 750
    for line in lines:
        c.drawString(72, y, line)
        y -= 20
    c.save()
    buf.seek(0)
    return buf.read()


BASE = "http://127.0.0.1:8000/api/v1"

# Login
r = requests.post(f"{BASE}/auth/login", data={"username": "admin@qvs.com", "password": "Admin1234!"})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Get first qualification
r2 = requests.get(f"{BASE}/qualifications/?page=1&page_size=1", headers=headers)
qual = r2.json()["items"][0]
qual_id = qual["id"]
print(f"Qual ID: {qual_id}")
print(f"  Title: {qual['title']}")
print(f"  Holder: {qual['holder_name']}")
print(f"  Institution: {qual['issuing_institution']}")
print(f"  Serial: {qual.get('serial_number')}")
print(f"  Reg: {qual.get('registration_number')}")

# Create a matching PDF
matching_pdf = make_pdf([
    qual["title"],
    qual["issuing_institution"],
    qual["holder_name"],
    qual.get("serial_number", ""),
    qual.get("registration_number", ""),
])
files = {"file": ("matching_transcript.pdf", io.BytesIO(matching_pdf), "application/pdf")}
data = {"method": "ai_assisted", "notes": "Testing document comparison"}

print("\n--- Verifying with MATCHING document ---")
r3 = requests.post(
    f"{BASE}/qualifications/{qual_id}/verify-with-document",
    headers=headers,
    files=files,
    data=data,
)
print(f"Status: {r3.status_code}")
result = r3.json()
print(f"Result: {result.get('result')}")
print(f"Message: {result.get('message')}")

if result.get("document_analysis"):
    da = result["document_analysis"]
    dm = da["data_match"]
    print(f"\nData Match Score: {dm['match_score']}%")
    print(f"Recommendation: {dm['recommendation']}")
    print(f"Summary: {dm['summary']}")
    for c in dm["checks"]:
        status = "MATCH" if c["found_in_document"] else "MISMATCH"
        print(f"  {c['field']}: {status} (registered: {c['registered']})")
else:
    print("No document_analysis in response")

# Now test with a mismatching document
print("\n--- Verifying with MISMATCHING document ---")
mismatch_pdf = make_pdf([
    "BSc Software Engineering",
    "Fake University",
    "Jane Smith",
    "SN-9999-XXX",
    "REG-9999-XXX",
])
files2 = {"file": ("fake_transcript.pdf", io.BytesIO(mismatch_pdf), "application/pdf")}
data2 = {"method": "ai_assisted", "notes": "Testing mismatch detection"}

r4 = requests.post(
    f"{BASE}/qualifications/{qual_id}/verify-with-document",
    headers=headers,
    files=files2,
    data=data2,
)
print(f"Status: {r4.status_code}")
result2 = r4.json()
print(f"Result: {result2.get('result')}")
print(f"Message: {result2.get('message')}")

if result2.get("document_analysis"):
    da2 = result2["document_analysis"]
    dm2 = da2["data_match"]
    print(f"\nData Match Score: {dm2['match_score']}%")
    print(f"Recommendation: {dm2['recommendation']}")
    print(f"Summary: {dm2['summary']}")
    for c in dm2["checks"]:
        status = "MATCH" if c["found_in_document"] else "MISMATCH"
        print(f"  {c['field']}: {status} (registered: {c['registered']})")
