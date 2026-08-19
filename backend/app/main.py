import io
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Content-Disposition"]
)

@app.get("/api/analytics/export/pdf")
async def export_pdf():
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

        story.append(Paragraph("Consumer Attention Mapping — Multi-Role Executive Report", title_style))
        story.append(Paragraph("Aggregated analytical breakdown covering Store Operations, Product Merchandising, and Marketing Saliency.", subtitle_style))

        # Store Manager Data
        story.append(Paragraph("1. Store Manager: Floor Heatmaps & Operational Inventory Alerts", section_style))
        sm_data = [
            ['Shelf Zone', 'Attention Rate', 'Footfall Status', 'Operational Action Required'],
            ['Zone A (Eye Level)', '94%', 'High Density', 'Optimal Stock Level'],
            ['Zone B (Touch Level)', '62%', 'Moderate Density', 'Restock Alert: Wireless Headphones (< 5 units)'],
            ['Zone C (Knee Level)', '18%', 'Low Density', 'Misplaced Alert: Dark Chocolate in Electronics Tier']
        ]
        t1 = Table(sm_data, colWidths=[110, 85, 95, 250])
        t1.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t1)
        story.append(Spacer(1, 10))

        # Retail Analyst Data
        story.append(Paragraph("2. Retail Analyst: Product Attractiveness & Cross-Merchandising Lifts", section_style))
        ra_data = [
            ['Product Name', 'Shelf Zone', 'Gaze Count', 'Attractiveness', 'Cross-Merchandising Strategy'],
            ['Wireless Headphones', 'Eye Level', '412', '98 / 100', 'Expand Facing (+20 units)'],
            ['Chronograph Watch', 'Eye Level', '342', '94 / 100', 'Pair with Leather Belts (+88% Lift)'],
            ['Cold-Pressed Juice', 'Touch Level', '289', '78 / 100', 'Cross-sell near Energy Bars (+64% Lift)'],
            ['Dark Chocolate', 'Knee Level', '156', '52 / 100', 'Relocate to Checkout Display']
        ]
        t2 = Table(ra_data, colWidths=[110, 70, 65, 75, 220])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2563EB')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t2)
        story.append(Spacer(1, 10))

        # Marketing Manager Data
        story.append(Paragraph("3. Marketing Manager: Campaign A/B Visual Saliency & Demographics", section_style))
        mm_data = [
            ['Display Variant', 'Visual Saliency Score', 'Avg Dwell Duration', 'Demographic Impact'],
            ['Variant A (Neon Header)', '78.4% (+24% Lift)', '18.2 seconds', 'Age 18 - 28 (High Engagement)'],
            ['Variant B (Standard Banner)', '52.1% (-8% Shift)', '9.4 seconds', 'Age 29 - 45 (Moderate Engagement)']
        ]
        t3 = Table(mm_data, colWidths=[140, 110, 90, 200])
        t3.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t3)

        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()

        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=Attention_Analytics_Full_Report.pdf"}
        )
    except Exception as e:
        return Response(content=f"Error generating PDF: {str(e)}", status_code=500)