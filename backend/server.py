"""
FastAPI Server connecting SQL (Inventory & Disaster Operations) and MongoDB (Beneficiary Profiles & Grievances).
Disaster Response and Relief Management with Nepal Melamchi and Indian Flood Case Studies.
"""
import os
import sys
import time
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend import sql_db, mongo_db
from backend.logger import log_api_call, current_request_ctx

app = FastAPI(
    title="TRACCIA Disaster Operations Portal",
    description="Database Management for Inventory and Disaster Response (India & Nepal Case Study)",
    version="2.0.0"
)

# Real-time API call logging middleware
@app.middleware("http")
async def log_api_calls(request: Request, call_next):
    path = request.url.path
    if path.startswith("/static/"):
        return await call_next(request)

    start_time = time.time()
    token = current_request_ctx.set(path)

    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        log_api_call(request.method, path, response.status_code, duration_ms)
        return response
    except Exception as exc:
        duration_ms = (time.time() - start_time) * 1000
        log_api_call(request.method, path, 500, duration_ms)
        raise exc
    finally:
        current_request_ctx.reset(token)

# Initialize databases on startup
@app.on_event("startup")
def startup_event():
    sql_db.init_sql_db()
    db = mongo_db.get_mongo_db()
    # Auto-seed if using in-memory mock or empty database
    try:
        if db.consumers.count_documents({"is_deleted": {"$ne": True}}) == 0:
            from backend import seed_data
            seed_data.seed_all()
    except Exception:
        pass

# Ensure static directory exists
os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"), exist_ok=True)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")), name="static")

# ----------------- PYDANTIC REQUEST MODELS -----------------

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    sku: str = Field(..., min_length=1)
    unit_price: float = Field(..., ge=0)

class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=1)
    contact_details: str = Field(..., min_length=1)

class LocationCreate(BaseModel):
    name: str = Field(..., min_length=1)
    address: str = Field(..., min_length=1)

class FloodEventCreate(BaseModel):
    event_id: str = Field(..., min_length=1)
    event_name: str = Field(..., min_length=1)
    country: str = Field(..., pattern="^(Nepal|India)$")
    state_province: str = Field(..., min_length=1)
    river_basin: str = Field(..., min_length=1)
    start_date: str = Field(..., min_length=1)
    end_date: Optional[str] = None
    severity: Optional[str] = "SEVERE"
    displaced_population: Optional[int] = 0
    casualties: Optional[int] = 0
    source_dataset: Optional[str] = "India Flood Inventory and Impacts (1967–2023)"
    geospatial_notes: Optional[str] = ""

class RainfallTelemetryCreate(BaseModel):
    station_id: str = Field(..., min_length=1)
    station_name: str = Field(..., min_length=1)
    state_or_region: str = Field(..., min_length=1)
    river_basin: str = Field(..., min_length=1)
    hourly_rainfall_mm: float = Field(..., ge=0)
    cumulative_24h_mm: float = Field(..., ge=0)
    danger_level_meters: float
    current_water_level_meters: float
    alert_level: Optional[str] = "NORMAL"
    source_dataset: Optional[str] = "CWC Telemetry Hourly Rainfall Data (NWIC)"

class PurchaseCreate(BaseModel):
    supplier_id: int
    product_id: int
    location_id: int
    quantity_received: int = Field(..., gt=0)

class SaleCreate(BaseModel):
    product_id: int
    location_id: int
    quantity_sold: int = Field(..., gt=0)
    consumer_id: Optional[str] = None

class DistributionItemInput(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)

class ReliefDistributionCreate(BaseModel):
    location_id: int
    beneficiary_id: str = Field(..., min_length=1)
    items: List[DistributionItemInput]
    flood_event_id: Optional[str] = None
    relief_officer: Optional[str] = "Field Relief Officer"
    notes: Optional[str] = ""

class StockMovementCreate(BaseModel):
    product_id: int
    movement_type: str = Field(..., pattern="^(TRANSFER|RETURN|ADJUSTMENT)$")
    quantity: int = Field(..., gt=0)
    from_location_id: Optional[int] = None
    to_location_id: Optional[int] = None

class ConsumerCreate(BaseModel):
    consumer_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    contact: str = Field(..., min_length=1)
    preferences: Optional[str] = ""
    verification_status: Optional[str] = "PENDING"
    address: Optional[str] = ""
    district: Optional[str] = ""
    state_country: Optional[str] = ""
    flood_event_id: Optional[str] = ""
    vulnerability_category: Optional[str] = "GENERAL"
    family_members_count: Optional[int] = 1
    is_synthetic: Optional[bool] = True

class ConsumerUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    preferences: Optional[str] = None
    verification_status: Optional[str] = None
    address: Optional[str] = None
    district: Optional[str] = None
    state_country: Optional[str] = None
    flood_event_id: Optional[str] = None
    vulnerability_category: Optional[str] = None
    family_members_count: Optional[int] = None

class GrievanceCreate(BaseModel):
    grievance_id: str = Field(..., min_length=1)
    consumer_id: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    priority: Optional[str] = "MEDIUM"
    assigned_team: Optional[str] = "Disaster Relief Cell"
    affected_location: Optional[str] = ""
    flood_event_id: Optional[str] = ""
    is_synthetic: Optional[bool] = True

class GrievanceUpdate(BaseModel):
    status: Optional[str] = None
    assigned_team: Optional[str] = None
    resolution: Optional[str] = None
    update_note: Optional[str] = None
    staff_id: Optional[str] = "FIELD_STAFF"

# ----------------- SQL ENDPOINTS (CRUD & TRANSACTIONS) -----------------

@app.get("/api/products")
def list_products():
    return sql_db.get_products()

@app.post("/api/products")
def add_product(payload: ProductCreate):
    try:
        pid = sql_db.create_product(payload.name, payload.category, payload.sku, payload.unit_price)
        return {"status": "success", "product_id": pid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/products/{product_id}")
def edit_product(product_id: int, payload: ProductCreate):
    try:
        ok = sql_db.update_product(product_id, payload.name, payload.category, payload.sku, payload.unit_price)
        if not ok:
            raise HTTPException(status_code=404, detail="Product not found")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/products/{product_id}")
def remove_product(product_id: int):
    try:
        ok = sql_db.delete_product(product_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Product not found or has foreign key dependencies.")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/suppliers")
def list_suppliers():
    return sql_db.get_suppliers()

@app.post("/api/suppliers")
def add_supplier(payload: SupplierCreate):
    try:
        sid = sql_db.create_supplier(payload.name, payload.contact_details)
        return {"status": "success", "supplier_id": sid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/suppliers/{supplier_id}")
def remove_supplier(supplier_id: int):
    try:
        ok = sql_db.delete_supplier(supplier_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Supplier not found or has associated purchases.")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/locations")
def list_locations():
    return sql_db.get_locations()

@app.post("/api/locations")
def add_location(payload: LocationCreate):
    try:
        lid = sql_db.create_location(payload.name, payload.address)
        return {"status": "success", "location_id": lid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/locations/{location_id}")
def remove_location(location_id: int):
    try:
        ok = sql_db.delete_location(location_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Location not found or has inventory/transactions.")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/flood-events")
def list_flood_events():
    return sql_db.get_flood_events()

@app.get("/api/flood-events/{event_id}")
def get_flood_event(event_id: str):
    fe = sql_db.get_flood_event_by_id(event_id)
    if not fe:
        raise HTTPException(status_code=404, detail="Flood event not found")
    return fe

@app.post("/api/flood-events")
def add_flood_event(payload: FloodEventCreate):
    try:
        eid = sql_db.create_flood_event(
            payload.event_id, payload.event_name, payload.country, payload.state_province,
            payload.river_basin, payload.start_date, payload.end_date, payload.severity or "SEVERE",
            payload.displaced_population or 0, payload.casualties or 0,
            payload.source_dataset or "India Flood Inventory and Impacts (1967–2023)",
            payload.geospatial_notes or ""
        )
        return {"status": "success", "event_id": eid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/flood-events/{event_id}")
def remove_flood_event(event_id: str):
    try:
        ok = sql_db.delete_flood_event(event_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Flood event not found")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/rainfall-telemetry")
def list_rainfall_telemetry():
    return sql_db.get_rainfall_telemetry()

@app.post("/api/rainfall-telemetry")
def update_telemetry(payload: RainfallTelemetryCreate):
    try:
        tid = sql_db.create_or_update_telemetry(
            payload.station_id, payload.station_name, payload.state_or_region,
            payload.river_basin, payload.hourly_rainfall_mm, payload.cumulative_24h_mm,
            payload.danger_level_meters, payload.current_water_level_meters,
            payload.alert_level or "NORMAL", payload.source_dataset or "CWC Telemetry Hourly Rainfall Data (NWIC)"
        )
        return {"status": "success", "telemetry_id": tid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/inventory")
def list_inventory():
    """JOIN: Inventory records joined with Products and Locations"""
    return sql_db.get_inventory_records()

@app.post("/api/purchases")
def execute_purchase(payload: PurchaseCreate):
    """Multi-step transaction: purchases and auto-increments inventory"""
    try:
        purchase_id = sql_db.record_purchase(
            payload.supplier_id, payload.product_id, payload.location_id, payload.quantity_received
        )
        return {"status": "success", "purchase_id": purchase_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/sales")
def execute_sale(payload: SaleCreate):
    """Multi-step transaction: validates stock, decrements inventory, and logs sale & relief dispatch"""
    try:
        sale_id = sql_db.record_sale(
            payload.product_id, payload.location_id, payload.quantity_sold, payload.consumer_id
        )
        return {"status": "success", "sale_id": sale_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/distributions")
def execute_relief_distribution(payload: ReliefDistributionCreate):
    """Multi-step transaction: atomically records multi-item disaster relief dispatches"""
    try:
        items_dict = [{"product_id": i.product_id, "quantity": i.quantity} for i in payload.items]
        dist_id = sql_db.record_relief_distribution(
            payload.location_id, payload.beneficiary_id, items_dict,
            payload.flood_event_id, payload.relief_officer or "Field Relief Officer", payload.notes or ""
        )
        return {"status": "success", "distribution_id": dist_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/stock-movements")
def execute_movement(payload: StockMovementCreate):
    """Multi-step transaction: transfers, returns, or adjustments"""
    try:
        m_id = sql_db.record_stock_movement(
            payload.product_id, payload.movement_type, payload.quantity,
            payload.from_location_id, payload.to_location_id
        )
        return {"status": "success", "movement_id": m_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ----------------- SQL JOINTS & AGGREGATE REPORTS -----------------

@app.get("/api/reports/purchases")
def report_purchases():
    """JOIN: Purchases + Suppliers + Products + Locations"""
    return sql_db.get_purchases_report()

@app.get("/api/reports/sales")
def report_sales():
    """JOIN: Sales + Products + Locations"""
    return sql_db.get_sales_report()

@app.get("/api/reports/distributions")
def report_distributions():
    """JOIN: Relief Distributions + Distribution Items + Products + Locations + Flood Events"""
    return sql_db.get_relief_distributions_report()

@app.get("/api/reports/distributions-by-event")
def report_distributions_by_event():
    """AGGREGATE: GROUP BY Flood Event"""
    return sql_db.report_distributions_by_event()

@app.get("/api/reports/stock-movements")
def report_movements():
    """JOIN: Movements + Products + Locations"""
    return sql_db.get_stock_movements_report()

@app.get("/api/reports/stock-by-location")
def report_stock_by_loc():
    """AGGREGATE: GROUP BY location"""
    return sql_db.report_stock_by_location()

@app.get("/api/reports/supplier-purchases")
def report_supp_purchases():
    """AGGREGATE: GROUP BY & HAVING on purchases"""
    return sql_db.report_supplier_purchases()

@app.get("/api/reports/low-stock")
def report_low_stock():
    """AGGREGATE/FILTER: low stock items"""
    return sql_db.report_low_stock_products()

@app.get("/api/reports/sales-by-product")
def report_sales_by_prod():
    """AGGREGATE: GROUP BY product with HAVING"""
    return sql_db.report_sales_by_product()

# ----------------- MONGODB ENDPOINTS (CRUD & FILTERING) -----------------

@app.get("/api/consumers")
def list_consumers(
    flood_event_id: Optional[str] = None,
    district: Optional[str] = None,
    verification_status: Optional[str] = None
):
    return mongo_db.get_consumers(flood_event_id=flood_event_id, district=district, verification_status=verification_status)

@app.get("/api/consumers/{consumer_id}")
def get_consumer(consumer_id: str):
    c = mongo_db.get_consumer_by_id(consumer_id)
    if not c:
        raise HTTPException(status_code=404, detail="Consumer/Beneficiary not found")
    return c

@app.post("/api/consumers")
def add_consumer(payload: ConsumerCreate):
    try:
        res = mongo_db.create_consumer(
            payload.consumer_id, payload.name, payload.contact,
            payload.preferences or "", payload.verification_status or "PENDING",
            payload.address or "", payload.district or "", payload.state_country or "",
            payload.flood_event_id or "", payload.vulnerability_category or "GENERAL",
            payload.family_members_count or 1, payload.is_synthetic if payload.is_synthetic is not None else True
        )
        return {"status": "success", "consumer": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/consumers/{consumer_id}")
def edit_consumer(consumer_id: str, payload: ConsumerUpdate):
    try:
        data = {k: v for k, v in payload.dict().items() if v is not None}
        ok = mongo_db.update_consumer(consumer_id, data)
        if not ok:
            raise HTTPException(status_code=404, detail="Consumer not found or no changes made")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/consumers/{consumer_id}")
def remove_consumer(consumer_id: str):
    try:
        ok = mongo_db.delete_consumer(consumer_id, soft_delete=True)
        if not ok:
            raise HTTPException(status_code=404, detail="Consumer not found")
        return {"status": "success", "message": "Consumer soft deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/grievances")
def list_grievances(
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    consumer_id: Optional[str] = None,
    flood_event_id: Optional[str] = None
):
    return mongo_db.get_grievances(
        status=status, category=category, priority=priority,
        consumer_id=consumer_id, flood_event_id=flood_event_id
    )

@app.get("/api/grievances/{grievance_id}")
def get_grievance(grievance_id: str):
    g = mongo_db.get_grievance_by_id(grievance_id)
    if not g:
        raise HTTPException(status_code=404, detail="Grievance not found")
    return g

@app.post("/api/grievances")
def add_grievance(payload: GrievanceCreate):
    try:
        res = mongo_db.create_grievance(
            payload.grievance_id, payload.consumer_id, payload.category,
            payload.description, payload.priority or "MEDIUM",
            payload.assigned_team or "Disaster Relief Cell",
            payload.affected_location or "", payload.flood_event_id or "",
            payload.is_synthetic if payload.is_synthetic is not None else True
        )
        return {"status": "success", "grievance": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/grievances/{grievance_id}")
def edit_grievance(grievance_id: str, payload: GrievanceUpdate):
    try:
        ok = mongo_db.update_grievance(
            grievance_id,
            status=payload.status,
            assigned_team=payload.assigned_team,
            resolution=payload.resolution,
            update_note=payload.update_note,
            staff_id=payload.staff_id or "FIELD_STAFF"
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Grievance not found")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/grievances/{grievance_id}")
def remove_grievance(grievance_id: str):
    try:
        ok = mongo_db.delete_grievance(grievance_id, soft_delete=True)
        if not ok:
            raise HTTPException(status_code=404, detail="Grievance not found")
        return {"status": "success", "message": "Grievance soft deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ----------------- CROSS-DATABASE HYBRID INTEGRATION & SUMMARY -----------------

@app.get("/api/reports/cross-database-disaster")
def report_cross_database_disaster():
    """
    Demonstrates true hybrid database integration:
    Joins SQL flood events with SQL relief distribution aggregates AND
    enriches them with MongoDB beneficiary counts and active grievances.
    """
    sql_events = sql_db.get_flood_events()
    sql_dist_by_event = {r["event_id"]: r for r in sql_db.report_distributions_by_event()}
    mongo_stats = mongo_db.get_disaster_grievance_stats()
    mongo_grievances_by_event = mongo_stats.get("by_event", {})

    enriched_events = []
    for ev in sql_events:
        eid = ev["event_id"]
        dist_info = sql_dist_by_event.get(eid, {})
        beneficiaries_in_event = mongo_db.get_consumers(flood_event_id=eid)

        enriched_events.append({
            "event_id": eid,
            "event_name": ev["event_name"],
            "country": ev["country"],
            "state_province": ev["state_province"],
            "river_basin": ev["river_basin"],
            "severity": ev["severity"],
            "displaced_population": ev["displaced_population"],
            "source_dataset": ev["source_dataset"],
            "geospatial_notes": ev["geospatial_notes"],
            "sql_relief_units_dispatched": dist_info.get("total_relief_units_dispatched", 0),
            "sql_relief_total_value": dist_info.get("total_relief_value", 0),
            "sql_total_distributions": dist_info.get("total_distributions", 0),
            "mongo_beneficiaries_onboarded": len(beneficiaries_in_event),
            "mongo_active_grievances": mongo_grievances_by_event.get(eid, 0)
        })

    return {
        "status": "success",
        "cross_database_disaster_reports": enriched_events
    }

@app.get("/api/summary")
def get_system_summary():
    """Unified cross-database system metrics for Disaster Response & Inventory"""
    inventory_items = sql_db.get_inventory_records()
    low_stock = sql_db.report_low_stock_products()
    flood_events = sql_db.get_flood_events()
    rainfall_telemetry = sql_db.get_rainfall_telemetry()
    consumers = mongo_db.get_consumers()
    open_grievances = mongo_db.get_grievances(status="OPEN")
    in_progress = mongo_db.get_grievances(status="IN_PROGRESS")

    high_alert_stations = [s for s in rainfall_telemetry if s.get("alert_level") in ("DANGER", "EXTREME", "WARNING")]

    return {
        "sql_metrics": {
            "total_inventory_positions": len(inventory_items),
            "low_stock_alerts_count": len(low_stock),
            "total_flood_events": len(flood_events),
            "active_cwc_stations": len(rainfall_telemetry),
            "cwc_high_alert_count": len(high_alert_stations),
            "database_engine": "SQL Relational Store (Foreign Keys, Constraints & Atomic ACID Dispatches)"
        },
        "mongo_metrics": {
            "active_consumers_count": len(consumers),
            "open_grievances_count": len(open_grievances),
            "in_progress_grievances_count": len(in_progress),
            "database_engine": "MongoDB Document Store (Beneficiaries, Disaster Requests & Embedded Audit Timelines)"
        },
        "disaster_context": {
            "focus_region": "India & Nepal Flood Disaster Operations",
            "datasets": [
                "Nepal-FRES: 2021 Melamchi Flood Data (HydroShare)",
                "India Flood Inventory and Impacts (1967–2023) (Zenodo)",
                "CWC Hourly Rainfall Telemetry (NWIC)"
            ]
        }
    }

# ----------------- FRONTEND UI ROUTE -----------------

@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r") as f:
            return f.read()
    return "<h1>TRACCIA Backend is running. Frontend static index.html not found.</h1>"
