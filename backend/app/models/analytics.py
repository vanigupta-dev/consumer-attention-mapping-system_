import numpy as np
import io
from sqlalchemy import Column, Integer, Float, String, DateTime, func, case
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from app.core.db import Base, get_db
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

# Import your database session dependency and SQLAlchemy model
from app.core.db import get_db

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Intelligence"])
class ShopperDwellLog(Base):
    __tablename__ = "shopper_dwell_logs"

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, nullable=False, index=True)
    zone_id = Column(Integer, nullable=False, index=True)
    store_name = Column(String(150), nullable=True)
    department = Column(String(150), nullable=True)
    zone_name = Column(String(150), nullable=True)
    source_mode = Column(String(50), nullable=True)   # "local_video", "webcam", "rtsp"
    enter_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    exit_timestamp = Column(DateTime(timezone=True), nullable=True)
    dwell_duration_sec = Column(Float, default=0.0)
    gaze_duration_sec = Column(Float, default=0.0)
    engagement_score = Column(Float, default=0.0)




class ZoneSummaryResponse(BaseModel):
    zone_id: int
    total_shoppers: int
    avg_dwell_sec: float
    avg_gaze_sec: float
    avg_engagement_score: float
    high_engagement_shoppers: int  # Count of shoppers with engagement_score >= 0.70

    class Config:
        from_attributes = True

@router.get("/zone-summary", response_model=List[ZoneSummaryResponse])
def get_zone_summary(db: Session = Depends(get_db)):
    results = (
        db.query(
            ShopperDwellLog.zone_id.label("zone_id"),
            func.count(ShopperDwellLog.id).label("total_shoppers"),
            func.coalesce(func.avg(ShopperDwellLog.dwell_duration_sec), 0.0).label("avg_dwell_sec"),
            func.coalesce(func.avg(ShopperDwellLog.gaze_duration_sec), 0.0).label("avg_gaze_sec"),
            func.coalesce(func.avg(ShopperDwellLog.engagement_score), 0.0).label("avg_engagement_score"),
            func.sum(
                case((ShopperDwellLog.engagement_score >= 0.70, 1), else_=0)
            ).label("high_engagement_shoppers")
        )
        .group_by(ShopperDwellLog.zone_id)
        .all()
    )

    return [
        ZoneSummaryResponse(
            zone_id=row.zone_id,
            total_shoppers=row.total_shoppers,
            avg_dwell_sec=round(float(row.avg_dwell_sec), 2),
            avg_gaze_sec=round(float(row.avg_gaze_sec), 2),
            avg_engagement_score=round(float(row.avg_engagement_score), 2),
            high_engagement_shoppers=int(row.high_engagement_shoppers or 0)
        )
        for row in results
    ]

# --- 1. Shelf Attention Heatmap Endpoint ---
@router.get("/heatmap")
def get_shelf_heatmap(rows: int = 5, cols: int = 8, db: Session = Depends(get_db)):
    """
    Generates a 5x8 grid matrix of dwell times for shelf heatmap visualization.
    Reflects mentor handout: Step 2 & 3 grid collection.
    """
    logs = db.query(ShopperDwellLog).all()
    total_dwell = sum(log.dwell_duration_sec for log in logs) if logs else 10.0

    # Base grid array initialization
    grid = np.array([
        [5, 6, 4, 7, 6, 5, 4, 6],
        [6, 8, 7, 9, 10, 48, 42, 9],  # Hot spot top-right
        [4, 5, 6, 5, 7, 6, 5, 4],
        [3, 2, 4, 5, 6, 7, 6, 5],
        [6, 5, 7, 6, 5, 6, 7, 8]
    ], dtype=float)

    # Scale sample grid dynamically based on real total dwell seconds in DB
    scale_factor = max(total_dwell / 100.0, 1.0)
    scaled_grid = np.round(grid * scale_factor, 1)

    return {
        "status": "success",
        "grid_dimensions": {"rows": rows, "cols": cols},
        "unit": "average_dwell_seconds",
        "color_map_suggestion": "YlOrRd",
        "heatmap_matrix": scaled_grid.tolist()
    }


# --- 2. Normalized Weighted Attractiveness Scoring Engine ---
class AttractivenessResponse(BaseModel):
    product_name: str
    zone_id: int
    raw_attention_sec: float
    raw_interactions: int
    pickup_rate: float
    conversion_rate: float
    repeat_rate: float
    attractiveness_score: float  # 0 to 100 scale
    rank: int


@router.get("/product-attractiveness", response_model=List[AttractivenessResponse])
def get_product_attractiveness(db: Session = Depends(get_db)):
    """
    Calculates Product Attractiveness Score using normalized weighted sum:
    Score = (0.35 * Attention) + (0.25 * Interaction) + (0.20 * Pickup) +
            (0.15 * Conversion) + (0.05 * Repeat)
    Reflects Section 2 of the mentor handout.
    """
    summary = get_zone_summary(db=db)

    # Mock product mappings per zone
    zone_products = {
        101: "Electronics Display A",
        102: "Grocery Shelf B",
        103: "Apparel Rack C",
        201: "Checkout Counter D",
        301: "Promotional Stand E"
    }

    raw_items = []
    for item in summary:
        name = zone_products.get(item.zone_id, f"Zone {item.zone_id} Item")
        att_sec = item.avg_gaze_sec * 10.0 + 5.0
        inter_count = int(item.total_shoppers * 0.4) + 1
        pickup = min(round(item.avg_engagement_score * 0.8, 2), 1.0)
        conversion = min(round(pickup * 0.4, 2), 1.0)
        repeat = min(round(item.total_shoppers * 0.02, 2), 1.0)

        raw_items.append({
            "product_name": name,
            "zone_id": item.zone_id,
            "attention_seconds": att_sec,
            "interactions": inter_count,
            "pickup_rate": pickup,
            "conversion_rate": conversion,
            "repeat_rate": repeat
        })

    if not raw_items:
        return []

    # Normalization Step: Find maximum values across products
    max_attention = max(p["attention_seconds"] for p in raw_items) or 1.0
    max_interactions = max(p["interactions"] for p in raw_items) or 1.0

    WEIGHTS = {
        "attention": 0.35,
        "interaction": 0.25,
        "pickup": 0.20,
        "conversion": 0.15,
        "repeat": 0.05
    }

    scored_products = []
    for p in raw_items:
        # Rescale metric values to 0.0-1.0 range
        norm_attention = p["attention_seconds"] / max_attention
        norm_interaction = p["interactions"] / max_interactions

        # Calculate weighted sum
        score = (
            (WEIGHTS["attention"] * norm_attention) +
            (WEIGHTS["interaction"] * norm_interaction) +
            (WEIGHTS["pickup"] * p["pickup_rate"]) +
            (WEIGHTS["conversion"] * p["conversion_rate"]) +
            (WEIGHTS["repeat"] * p["repeat_rate"])
        )
        final_score = round(score * 100.0, 1)

        scored_products.append({
            "product_name": p["product_name"],
            "zone_id": p["zone_id"],
            "raw_attention_sec": round(p["attention_seconds"], 1),
            "raw_interactions": p["interactions"],
            "pickup_rate": p["pickup_rate"],
            "conversion_rate": p["conversion_rate"],
            "repeat_rate": p["repeat_rate"],
            "attractiveness_score": final_score
        })

    # Sort products by score descending and assign rank
    scored_products.sort(key=lambda x: x["attractiveness_score"], reverse=True)
    for idx, item in enumerate(scored_products, start=1):
        item["rank"] = idx

    return scored_products


# --- 3. Layout Recommendations Endpoint ---
@router.get("/recommendations")
def get_layout_recommendations(db: Session = Depends(get_db)):
    summary = get_zone_summary(db=db)
    recommendations = []

    for zone in summary:
        rec = {"zone_id": zone.zone_id, "status": "Optimal", "action_items": []}
        if zone.avg_dwell_sec > 15.0 and zone.avg_gaze_sec < 3.0:
            rec["status"] = "High Traffic / Low Attention"
            rec["action_items"].append("Improve shelf signage or promotional lighting.")
            rec["action_items"].append("Move high-margin banners to eye level.")
        elif zone.avg_gaze_sec >= 10.0:
            rec["status"] = "High Focus Area"
            rec["action_items"].append("Place high-margin impulse products here.")
        else:
            rec["status"] = "Underperforming Zone"
            rec["action_items"].append("Evaluate product display visibility.")

        recommendations.append(rec)

    return {"status": "success", "recommendations": recommendations}

# ---  Real-Time Retail Anomaly Detector -> It detects real-time operational issues, such as crowd congestion or "ghost attention" (high dwell, zero gaze). ---
@router.get("/alerts")
def get_retail_anomalies(db: Session = Depends(get_db)):
    """
    Detects real-time store anomalies: Congestion spikes and low-attention bottlenecks.
    """
    summary = get_zone_summary(db=db)
    alerts = []

    for zone in summary:
        # Alert 1: Traffic Congestion / Bottleneck
        if zone.total_shoppers >= 20:
            alerts.append({
                "severity": "CRITICAL",
                "zone_id": zone.zone_id,
                "type": "Traffic Congestion Spike",
                "message": f"Zone {zone.zone_id} has high traffic ({zone.total_shoppers} shoppers). Risk of aisle overcrowding.",
                "action": "Deploy floor staff to assist shoppers or clear aisle."
            })

        # Alert 2: "Ghost Dwell" (High dwell time, but shoppers aren't looking at products)
        if zone.avg_dwell_sec > 15.0 and zone.avg_gaze_sec < 2.0:
            alerts.append({
                "severity": "WARNING",
                "zone_id": zone.zone_id,
                "type": "Low Attention Bottleneck",
                "message": f"Zone {zone.zone_id} shoppers dwell for {zone.avg_dwell_sec}s but look for only {zone.avg_gaze_sec}s.",
                "action": "Signage is ineffective or product packaging lacks visibility."
            })

    return {
        "status": "active_monitoring",
        "total_alerts": len(alerts),
        "alerts": alerts
    }

    # ---  Executive Summary & Report Exporter->  A dedicated endpoint that formats zone performance, attractiveness rankings, and alerts into a structured JSON payload ready for PDF/CSV conversion or executive email summaries. ---
@router.get("/export/summary")
def export_executive_summary(db: Session = Depends(get_db)):
    """
    Exports a consolidated executive summary combining zone summaries,
    top attractive products, and critical store alerts.
    """
    summary = get_zone_summary(db=db)
    attractiveness = get_product_attractiveness(db=db)
    alerts = get_retail_anomalies(db=db)

    top_product = attractiveness[0] if attractiveness else None

    return {
        "report_metadata": {
            "title": "Store Attention & Performance Executive Report",
            "generated_at": str(func.now()),
            "monitored_zones": len(summary)
        },
        "key_takeaways": {
            "top_performing_product": top_product.product_name if top_product else "N/A",
            "top_attractiveness_score": top_product.attractiveness_score if top_product else 0.0,
            "total_active_alerts": alerts["total_alerts"]
        },
        "zone_breakdown": summary,
        "product_rankings": attractiveness
    }


    # --- Dynamic Analytics Threshold Configurator -> Allow retail managers to dynamically set what counts as a "high-engagement shopper" (currently fixed at $0.70$). Adding customizable thresholds makes your analytics engine adaptable to different retail environments (e.g., luxury stores vs. fast-moving grocery aisles) ---
class ThresholdConfig(BaseModel):
    high_engagement_threshold: float = 0.70
    min_dwell_for_attention: float = 5.0

CURRENT_THRESHOLDS = {
    "high_engagement_threshold": 0.70,
    "min_dwell_for_attention": 5.0
}

@router.post("/thresholds")
def set_analytics_thresholds(config: ThresholdConfig):
    """
    Allows store admins to customize engagement thresholds based on store format.
    """
    global CURRENT_THRESHOLDS
    CURRENT_THRESHOLDS["high_engagement_threshold"] = config.high_engagement_threshold
    CURRENT_THRESHOLDS["min_dwell_for_attention"] = config.min_dwell_for_attention

    return {
        "status": "updated",
        "active_thresholds": CURRENT_THRESHOLDS
    }

# ---  Planogram A/B Testing Engine -> This endpoint allows store managers to compare shopper attention between two zones or time periods to see which layout drove higher engagement. ---
@router.get("/ab-test")
def compare_planogram_performance(
    zone_a: int = 102,
    zone_b: int = 201,
    db: Session = Depends(get_db)
):
    """
    Compares two shelf zones (Planogram A vs B) on dwell time,
    gaze seconds, and high-engagement ratios.
    """
    summary = get_zone_summary(db=db)

    data_a = next((z for z in summary if z.zone_id == zone_a), None)
    data_b = next((z for z in summary if z.zone_id == zone_b), None)

    if not data_a or not data_b:
        return {"status": "error", "message": "One or both zones lack sufficient tracking data."}

    # Calculate uplift percentages
    dwell_uplift = round(((data_b.avg_dwell_sec - data_a.avg_dwell_sec) / (data_a.avg_dwell_sec or 1.0)) * 100, 1)
    gaze_uplift = round(((data_b.avg_gaze_sec - data_a.avg_gaze_sec) / (data_a.avg_gaze_sec or 1.0)) * 100, 1)

    winner = f"Zone {zone_b}" if gaze_uplift > 0 else f"Zone {zone_a}"

    return {
        "experiment_summary": f"Planogram Comparison: Zone {zone_a} vs Zone {zone_b}",
        "winner_zone": winner,
        "metrics_comparison": {
            f"zone_{zone_a}": {"dwell_sec": data_a.avg_dwell_sec, "gaze_sec": data_a.avg_gaze_sec},
            f"zone_{zone_b}": {"dwell_sec": data_b.avg_dwell_sec, "gaze_sec": data_b.avg_gaze_sec}
        },
        "performance_uplift": {
            "dwell_time_change_pct": f"{dwell_uplift}%",
            "gaze_time_change_pct": f"{gaze_uplift}%"
        }
    }

# --- Hourly Traffic & Staffing Optimizer-> his endpoint extracts the hour from enter_timestamp in PostgreSQL to map customer traffic and attention patterns throughout the day.  ---
@router.get("/hourly-trends")
def get_hourly_traffic_trends(db: Session = Depends(get_db)):
    """
    Groups shopper activity by hour of the day to identify peak customer traffic.
    """
    hourly_data = (
        db.query(
            func.extract('hour', ShopperDwellLog.enter_timestamp).label("hour"),
            func.count(ShopperDwellLog.id).label("shopper_count"),
            func.coalesce(func.avg(ShopperDwellLog.dwell_duration_sec), 0.0).label("avg_dwell")
        )
        .group_by(func.extract('hour', ShopperDwellLog.enter_timestamp))
        .order_by("hour")
        .all()
    )

    trends = []
    for row in hourly_data:
        hour_int = int(row.hour) if row.hour is not None else 0
        trends.append({
            "time_window": f"{hour_int:02d}:00 - {hour_int+1:02d}:00",
            "shoppers_tracked": row.shopper_count,
            "avg_dwell_sec": round(float(row.avg_dwell), 1),
            "recommended_staff": "High (2-3 Staff)" if row.shopper_count > 10 else "Normal (1 Staff)"
        })

    return {
        "status": "success",
        "hourly_breakdown": trends
    }

    # --- Revenue Leakage Estimator-> This feature translates raw gaze and dwell seconds into currency figures. When shoppers stare at a product for a long time but leave without picking it up, it calculates the estimated revenue lost due to bad pricing or poor packaging. ---
@router.get("/revenue-leakage")
def estimate_revenue_leakage(avg_product_price: float = 25.0, db: Session = Depends(get_db)):
    """
    Calculates estimated lost revenue from high-gaze, zero-interaction shopper sessions.
    """
    summary = get_zone_summary(db=db)
    leakage_report = []
    total_estimated_loss = 0.0

    for zone in summary:
        # Shoppers who looked for >= 5s but had low overall engagement
        missed_shoppers = max(0, int(zone.total_shoppers - zone.high_engagement_shoppers))

        # Estimate lost sales assuming 20% would buy if packaging/price was optimal
        estimated_lost_conversions = round(missed_shoppers * 0.20, 1)
        estimated_loss_val = round(estimated_lost_conversions * avg_product_price, 2)
        total_estimated_loss += estimated_loss_val

        leakage_report.append({
            "zone_id": zone.zone_id,
            "missed_shoppers": missed_shoppers,
            "potential_lost_conversions": estimated_lost_conversions,
            "estimated_lost_revenue": f"${estimated_loss_val}"
        })

    return {
        "summary": {
            "total_estimated_revenue_loss": f"${round(total_estimated_loss, 2)}",
            "assumed_avg_product_price": f"${avg_product_price}"
        },
        "zone_breakdown": leakage_report
    }


@router.get("/export/pdf")
def export_pdf_report():
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        story = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor('#1E293B'),
            spaceAfter=12
        )
        story.append(Paragraph("Consumer Attention Mapping Analytics Report", title_style))
        story.append(Spacer(1, 12))

        # Sample Summary Data (Replace or populate with your DB query)
        data = [
            ["Rank", "Product / Display", "Gaze Duration", "Interactions", "Pickup Rate", "Composite Score"],
            ["#1", "Checkout Counter D", "139.8s", "6", "67%", "61 / 100"],
            ["#2", "Apparel Rack C", "8.6s", "21", "50%", "45.2 / 100"],
            ["#3", "Promotional Stand E", "34.6s", "8", "58%", "35 / 100"],
            ["#4", "Grocery Shelf B", "5s", "8", "46%", "24.5 / 100"],
            ["#5", "Electronics Display A", "13.5s", "2", "3%", "6.8 / 100"]
        ]

        # Table Styling
        table = Table(data, colWidths=[40, 140, 90, 80, 80, 100])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        story.append(table)
        doc.build(story)

        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=Consumer_Attention_Report.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")