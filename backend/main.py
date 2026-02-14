"""FastAPI application with SSE chat endpoint"""
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from .agent import root_agent
from .adk_sse_wrapper import run_agent_sse
from .config import settings
from .models import ChatRequest, InsuranceRequest
from google.adk.runners import InMemoryRunner

app = FastAPI(
    title="Blaxel Hello World Agent",
    description="Hello World SSE agent powered by Claude via Google ADK",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "blaxel-agent", "version": "1.0.0"}


@app.post("/api/sandbox/insurance")
async def generate_insurance(req: InsuranceRequest):
    """Generate an insurance PDF inside the Blaxel sandbox and email it."""
    import os
    import base64
    import shlex

    os.environ.setdefault("BL_WORKSPACE", settings.bl_workspace)
    os.environ.setdefault("BL_API_KEY", settings.bl_api_key)

    from blaxel.core import SandboxInstance

    sandbox = await SandboxInstance.get(settings.sandbox_name)

    # Pure-Python script (zero dependencies) to generate PDF + send email
    script = r'''
import sys, random, json, base64
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

insurance_number = sys.argv[1]
sendgrid_key = ""

# ── Pure-Python PDF writer (no dependencies) ────────────────────
def esc(t):
    return t.replace("\\","\\\\").replace("(","\\(").replace(")","\\)")

W, H = 612, 792
y = H - 50
cmds = []

def color(r,g,b):
    cmds.append(f"{r/255:.3f} {g/255:.3f} {b/255:.3f} rg")

def stroke(r,g,b):
    cmds.append(f"{r/255:.3f} {g/255:.3f} {b/255:.3f} RG")

def txt(x, font, size, text):
    global y
    cmds.append(f"BT /{font} {size} Tf {x} {y} Td ({esc(text)}) Tj ET")

def txt_at(x, yy, font, size, text):
    cmds.append(f"BT /{font} {size} Tf {x} {yy} Td ({esc(text)}) Tj ET")

def ln(x1, y1, x2, y2, w=0.5):
    cmds.append(f"{w} w {x1} {y1} m {x2} {y2} l S")

def down(pts):
    global y
    y -= pts

# ── Build the document ──────────────────────────────────────────
color(0,51,102)
txt(175, "F2", 22, "ACME Insurance Co.")
down(18)
color(80,80,80)
txt(140, "F1", 9, "123 Insurance Blvd, Suite 400, New York, NY 10001")
down(13)
txt(155, "F1", 9, "Tel: (800) 555-0199  |  claims@acmeinsurance.com")
down(10)
stroke(0,51,102); ln(50, y, 562, y); down(25)

color(0,51,102)
txt(190, "F2", 16, "CERTIFICATE OF INSURANCE")
down(30)

color(0,51,102); txt(50, "F2", 13, "Policy Information")
down(3); stroke(0,51,102); ln(50, y, 562, y); down(18)

eff = datetime.now(); exp = eff + timedelta(days=365)
prem = random.randint(800,3500); ded = random.choice([500,1000,1500,2000])
lim = random.randint(100,500)*1000

rows = [
    ("Policy Number", insurance_number),
    ("Policy Type", "Comprehensive Coverage Plan"),
    ("Policyholder", "John Q. Public"),
    ("Effective Date", eff.strftime("%B %d, %Y")),
    ("Expiration Date", exp.strftime("%B %d, %Y")),
    ("Annual Premium", f"${prem:,.2f}"),
    ("Deductible", f"${ded:,}"),
    ("Coverage Limit", f"${lim:,}"),
    ("Status", "ACTIVE"),
]
for label, val in rows:
    color(60,60,60); txt(50, "F2", 10, label + ":")
    color(30,30,30); txt(200, "F1", 10, val)
    down(16)

down(8)
color(0,51,102); txt(50, "F2", 13, "Coverage Details")
down(3); stroke(0,51,102); ln(50, y, 562, y); down(18)

covs = [
    "Property Damage Liability - Up to policy limit",
    "Bodily Injury Liability - Up to policy limit per person",
    "Personal Injury Protection - Included",
    "Uninsured/Underinsured Motorist Coverage - Included",
    "Comprehensive Coverage - Included (subject to deductible)",
    "Collision Coverage - Included (subject to deductible)",
    "Emergency Roadside Assistance - 24/7 Included",
    "Rental Car Reimbursement - Up to $50/day for 30 days",
]
color(30,30,30)
for c in covs:
    txt(50, "F1", 10, "- " + c); down(15)

down(8)
color(0,51,102); txt(50, "F2", 13, "Terms & Conditions")
down(3); stroke(0,51,102); ln(50, y, 562, y); down(18)

color(60,60,60)
for t in [
    "This policy is subject to the terms, conditions, and exclusions set forth herein.",
    "Coverage is provided on an occurrence basis unless otherwise stated. The insured",
    "agrees to pay all premiums when due and to comply with all policy conditions.",
    "Failure to pay premiums may result in cancellation. Claims must be reported within",
    "30 days of occurrence. ACME Insurance Co. reserves the right to modify terms with",
    "30 days written notice. Governed by the laws of the State of New York.",
]:
    txt(50, "F1", 9, t); down(12)

down(20)
color(30,30,30)
txt(50, "F2", 11, "Authorized Signature: ____________________________")
down(18)
color(100,100,100)
txt(50, "F3", 9, f"Document generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
down(13)
txt(50, "F3", 9, f"Reference: {insurance_number}-{random.randint(1000,9999)}")

color(100,100,100)
txt_at(170, 20, "F3", 8, "Page 1  |  ACME Insurance Co. - CONFIDENTIAL")

# ── Assemble PDF bytes ──────────────────────────────────────────
stream = "\n".join(cmds)
objs = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
    "/Contents 4 0 R /Resources << /Font << "
    "/F1 5 0 R /F2 6 0 R /F3 7 0 R >> >> >>",
    f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique >>",
]

parts = ["%PDF-1.4\n"]
offsets = []
for i, o in enumerate(objs):
    offsets.append(len("".join(parts)))
    parts.append(f"{i+1} 0 obj\n{o}\nendobj\n")

xref_off = len("".join(parts))
parts.append(f"xref\n0 {len(objs)+1}\n")
parts.append("0000000000 65535 f \n")
for off in offsets:
    parts.append(f"{off:010d} 00000 n \n")
parts.append(f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\n")
parts.append(f"startxref\n{xref_off}\n%%EOF\n")

output_path = f"/tmp/insurance_policy_{insurance_number}.pdf"
with open(output_path, "w") as f:
    f.write("".join(parts))
print(f"PDF_OK: {output_path}")

# ── Send Email via SendGrid ─────────────────────────────────────
with open(output_path, "rb") as f:
    pdf_b64 = base64.b64encode(f.read()).decode()

payload = {
    "personalizations": [{"to": [{"email": "shresthkapoor7@gmail.com"}]}],
    "from": {"email": "retsuexec@gmail.com", "name": "ACME Insurance Co."},
    "subject": f"Your Insurance Policy - #{insurance_number}",
    "content": [{"type": "text/plain", "value":
        f"Dear Policyholder,\n\n"
        f"Please find attached your insurance policy document for Policy #{insurance_number}.\n\n"
        f"This document contains your complete coverage details, terms, and conditions.\n"
        f"Please review it carefully and contact us at (800) 555-0199 with any questions.\n\n"
        f"Best regards,\nACME Insurance Co.\nClaims Department\n"
    }],
    "attachments": [{
        "content": pdf_b64,
        "filename": f"policy_{insurance_number}.pdf",
        "type": "application/pdf",
        "disposition": "attachment",
    }],
}

try:
    req = Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {sendgrid_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    resp = urlopen(req, timeout=15)
    print(f"EMAIL_OK: SendGrid responded {resp.status}")
except HTTPError as e:
    print(f"EMAIL_FAIL: SendGrid {e.code} - {e.read().decode()}")
except Exception as e:
    print(f"EMAIL_FAIL: {e}")
'''

    # Base64-encode the script to avoid shell quoting issues
    script_b64 = base64.b64encode(script.encode()).decode()
    safe_number = shlex.quote(req.insurance_number)
    result = await sandbox.process.exec({
        "command": f"echo '{script_b64}' | base64 -d | python3 - {safe_number}",
        "wait_for_completion": True,
        "timeout": 30000,
    })

    stdout = result.stdout or ""
    pdf_ok = "PDF_OK" in stdout
    email_ok = "EMAIL_OK" in stdout

    return {
        "insurance_number": req.insurance_number,
        "pdf_generated": pdf_ok,
        "email_sent": email_ok,
        "email_to": "something@mailinator.com",
        "stdout": stdout,
        "stderr": result.stderr or "",
        "exit_code": result.exit_code,
    }


@app.post("/api/chat")
async def chat(req: ChatRequest):
    runner = InMemoryRunner(agent=root_agent, app_name=settings.app_name)
    session = await runner.session_service.create_session(
        app_name=settings.app_name,
        user_id="web_user",
    )

    async def sse_generator():
        async for payload in run_agent_sse(
            runner=runner,
            session_id=session.id,
            user_id="web_user",
            message=req.message,
        ):
            yield {"data": payload}

    return EventSourceResponse(sse_generator())


# Static files must be mounted last so API routes take priority
if settings.frontend_dir.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(settings.frontend_dir), html=True),
        name="frontend",
    )
