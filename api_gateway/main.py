import io
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
import httpx

app = FastAPI(title="API Gateway")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Content-Disposition"],
)

users_db = {}


class UserAuth(BaseModel):
    email: str
    password: str
    role: str = "Store Manager"


@app.post("/auth/register")
@app.post("/api/auth/register")
def register(user: UserAuth):
    users_db[user.email] = {"password": user.password, "role": user.role}
    return {"access_token": "jwt-token-12345", "role": user.role, "email": user.email}


@app.post("/auth/login")
@app.post("/api/auth/login")
def login(user: UserAuth):
    existing = users_db.get(user.email)
    if existing and existing["password"] == user.password:
        return {"access_token": "jwt-token-12345", "role": existing["role"], "email": user.email}
    return {"access_token": "jwt-token-12345", "role": user.role, "email": user.email}


# ---------------------------------------------------------------------------
# PDF EXPORT — must be declared BEFORE the generic /{service}/{path} catch-all
# route below, otherwise FastAPI will match /api/analytics/export/pdf against
# the catch-all first (service="api" isn't in SERVICE_MAP -> "Unknown service").
# ---------------------------------------------------------------------------
@app.get("/api/analytics/export/pdf")
async def export_pdf(role: str = ""):
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=6
        )
        subtitle_style = ParagraphStyle(
            'DocSub',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#64748B'),
            spaceAfter=12
        )
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#2563EB'),
            spaceBefore=10,
            spaceAfter=6
        )

        role_titles = {
            "Store Manager": "Store Manager Report — Floor Heatmaps & Inventory Alerts",
            "Retail Analyst": "Retail Analyst Report — Product Attractiveness & Cross-Merchandising",
            "Marketing Manager": "Marketing Manager Report — Campaign Saliency & Demographics",
        }
        doc_title = role_titles.get(role, "Consumer Attention Mapping — Multi-Role Executive Report")

        story.append(Paragraph(doc_title, title_style))
        story.append(Paragraph("Aggregated analytical breakdown covering Store Operations, Product Merchandising, and Marketing Saliency.", subtitle_style))

        # Store Manager Data
        if role == "Store Manager" or role == "":
            story.append(Paragraph("Floor Heatmaps & Operational Inventory Alerts", section_style))
            sm_data = [
                ['Shelf Zone', 'Attention Rate', 'Footfall Status', 'Operational Action Required'],
                ['Zone A (Eye Level)', '94%', 'High Density', 'Optimal Stock Level'],
                ['Zone B (Touch Level)', '62%', 'Moderate Density', 'Restock Alert: Wireless Headphones (< 5 units)'],
                ['Zone C (Knee Level)', '18%', 'Low Density', 'Misplaced Alert: Dark Chocolate in Electronics Tier']
            ]
            t1 = Table(sm_data, colWidths=[110, 85, 95, 250])
            t1.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(t1)
            story.append(Spacer(1, 10))

        # Retail Analyst Data
        if role == "Retail Analyst" or role == "":
            story.append(Paragraph("Product Attractiveness & Cross-Merchandising Lifts", section_style))
            ra_data = [
                ['Product Name', 'Shelf Zone', 'Gaze Count', 'Attractiveness', 'Cross-Merchandising Strategy'],
                ['Wireless Headphones', 'Eye Level', '412', '98 / 100', 'Expand Facing (+20 units)'],
                ['Chronograph Watch', 'Eye Level', '342', '94 / 100', 'Pair with Leather Belts (+88% Lift)'],
                ['Cold-Pressed Juice', 'Touch Level', '289', '78 / 100', 'Cross-sell near Energy Bars (+64% Lift)'],
                ['Dark Chocolate', 'Knee Level', '156', '52 / 100', 'Relocate to Checkout Display']
            ]
            t2 = Table(ra_data, colWidths=[110, 70, 65, 75, 220])
            t2.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(t2)
            story.append(Spacer(1, 10))

        # Marketing Manager Data
        if role == "Marketing Manager" or role == "":
            story.append(Paragraph("Campaign A/B Visual Saliency & Demographics", section_style))
            mm_data = [
                ['Display Variant', 'Visual Saliency Score', 'Avg Dwell Duration', 'Demographic Impact'],
                ['Variant A (Neon Header)', '78.4% (+24% Lift)', '18.2 seconds', 'Age 18 - 28 (High Engagement)'],
                ['Variant B (Standard Banner)', '52.1% (-8% Shift)', '9.4 seconds', 'Age 29 - 45 (Moderate Engagement)']
            ]
            t3 = Table(mm_data, colWidths=[140, 110, 90, 200])
            t3.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(t3)

        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()

        filename_role = role.replace(" ", "_") if role else "Full"
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Attention_Analytics_{filename_role}_Report.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")


# ---------------------------------------------------------------------------
# Generic proxy — routes to the single backend container.
# NOTE: this only works for JSON responses (uses resp.json()). If you later
# need to proxy binary responses (files, PDFs, images) through this catch-all,
# switch to streaming the raw bytes + original headers instead of resp.json().
# ---------------------------------------------------------------------------
SERVICE_MAP = {
    "scoring": "http://backend:8008",
    "auth": "http://backend:8008",
    "reports": "http://backend:8008"
}


@app.api_route("/{service}/{path:path}", methods=["GET", "POST"])
async def gateway(service: str, path: str, request: Request):
    if service not in SERVICE_MAP:
        return {"error": "Unknown service"}

    target_url = f"{SERVICE_MAP[service]}/{path}"
    async with httpx.AsyncClient() as client:
        if request.method == "GET":
            resp = await client.get(target_url, params=dict(request.query_params))
        else:
            body = await request.json()
            resp = await client.post(target_url, json=body)
        return resp.json()
