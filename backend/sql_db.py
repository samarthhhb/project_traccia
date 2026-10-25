"""
TRACCIA SQL Database Manager with live terminal query/execution logging.
Disaster Response and Inventory Management for Indian Operational Requirements & Nepal Flood Case Study.
"""
import sqlite3
import os
import time
from typing import Dict, Any, List, Optional

DB_PATH = os.environ.get("TRACCIA_SQL_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "traccia.db"))

# ANSI Terminal Colors for live database activity display
CYAN = "\033[96m"
GREEN = "\033[92m"
from backend.logger import format_sql_log, CYAN, YELLOW, BLUE, MAGENTA, BOLD, RESET

def log_sql(action: str, query: str, params: Any = None, rows_affected: Optional[int] = None):
    print(format_sql_log(action, query, params, rows_affected))

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_sql_db():
    conn = get_connection()
    cur = conn.cursor()
    
    # 1. flood_events (Nepal Melamchi & Indian Flood Inventory 1967-2023)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS flood_events (
        event_id TEXT PRIMARY KEY,
        event_name TEXT NOT NULL,
        country TEXT NOT NULL CHECK(country IN ('Nepal', 'India')),
        state_province TEXT NOT NULL,
        river_basin TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT,
        severity TEXT NOT NULL CHECK(severity IN ('MODERATE', 'SEVERE', 'CATASTROPHIC')),
        displaced_population INTEGER DEFAULT 0 CHECK(displaced_population >= 0),
        casualties INTEGER DEFAULT 0 CHECK(casualties >= 0),
        source_dataset TEXT NOT NULL,
        geospatial_notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. cwc_rainfall_telemetry (CWC Hourly Rainfall & River Levels)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cwc_rainfall_telemetry (
        telemetry_id INTEGER PRIMARY KEY AUTOINCREMENT,
        station_id TEXT NOT NULL UNIQUE,
        station_name TEXT NOT NULL,
        state_or_region TEXT NOT NULL,
        river_basin TEXT NOT NULL,
        hourly_rainfall_mm REAL NOT NULL CHECK(hourly_rainfall_mm >= 0),
        cumulative_24h_mm REAL NOT NULL CHECK(cumulative_24h_mm >= 0),
        danger_level_meters REAL NOT NULL,
        current_water_level_meters REAL NOT NULL,
        alert_level TEXT NOT NULL CHECK(alert_level IN ('NORMAL', 'ADVISORY', 'WARNING', 'DANGER', 'EXTREME')),
        source_dataset TEXT DEFAULT 'CWC Telemetry Hourly Rainfall Data (NWIC)',
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. products (Relief Supplies & Equipment)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        sku TEXT NOT NULL UNIQUE,
        unit_price REAL NOT NULL CHECK(unit_price >= 0)
    );
    """)

    # 4. suppliers (NDRF, Red Cross, Aid Agencies & Manufacturers)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS suppliers (
        supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact_details TEXT NOT NULL
    );
    """)

    # 5. locations (Disaster Response Hubs, District Warehouses & Camps)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS locations (
        location_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT NOT NULL
    );
    """)

    # 6. inventory (Stock on hand per warehouse / relief center)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
        location_id INTEGER NOT NULL REFERENCES locations(location_id) ON DELETE CASCADE,
        quantity_on_hand INTEGER NOT NULL DEFAULT 0 CHECK(quantity_on_hand >= 0),
        reorder_level INTEGER NOT NULL DEFAULT 0 CHECK(reorder_level >= 0),
        UNIQUE(product_id, location_id)
    );
    """)

    # 7. purchases (Incoming relief procurement receipts)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS purchases (
        purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id INTEGER NOT NULL REFERENCES suppliers(supplier_id) ON DELETE RESTRICT,
        product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
        location_id INTEGER NOT NULL REFERENCES locations(location_id) ON DELETE RESTRICT,
        quantity_received INTEGER NOT NULL CHECK(quantity_received > 0),
        purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 8. relief_distributions (Dispatches to disaster-affected beneficiaries)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS relief_distributions (
        distribution_id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_id INTEGER NOT NULL REFERENCES locations(location_id) ON DELETE RESTRICT,
        beneficiary_id TEXT NOT NULL,
        flood_event_id TEXT REFERENCES flood_events(event_id) ON DELETE SET NULL,
        distribution_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        relief_officer TEXT NOT NULL DEFAULT 'Field Relief Officer',
        status TEXT NOT NULL DEFAULT 'DELIVERED' CHECK(status IN ('PREPARING', 'DISPATCHED', 'DELIVERED')),
        notes TEXT
    );
    """)

    # 9. distribution_items (Individual relief supply line items in a distribution dispatch)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS distribution_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        distribution_id INTEGER NOT NULL REFERENCES relief_distributions(distribution_id) ON DELETE CASCADE,
        product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
        quantity INTEGER NOT NULL CHECK(quantity > 0)
    );
    """)

    # 10. sales (Maintained and synchronized for backward compatibility with existing endpoints)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
        location_id INTEGER NOT NULL REFERENCES locations(location_id) ON DELETE RESTRICT,
        consumer_id TEXT,
        quantity_sold INTEGER NOT NULL CHECK(quantity_sold > 0),
        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 11. stock_movements (Inter-warehouse transfers, damaged inventory adjustments, returns)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stock_movements (
        movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
        from_location_id INTEGER REFERENCES locations(location_id) ON DELETE RESTRICT,
        to_location_id INTEGER REFERENCES locations(location_id) ON DELETE RESTRICT,
        movement_type TEXT NOT NULL CHECK(movement_type IN ('TRANSFER', 'RETURN', 'ADJUSTMENT')),
        quantity INTEGER NOT NULL CHECK(quantity > 0),
        movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()

# ----------------- CRUD: Products -----------------
def create_product(name: str, category: str, sku: str, unit_price: float) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = "INSERT INTO products (name, category, sku, unit_price) VALUES (?, ?, ?, ?)"
        params = (name.strip(), category.strip(), sku.strip(), float(unit_price))
        cur.execute(q, params)
        conn.commit()
        log_sql("INSERT", q, params, rows_affected=cur.rowcount)
        return cur.lastrowid
    finally:
        conn.close()

def get_products() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = "SELECT * FROM products ORDER BY product_id DESC"
        cur.execute(q)
        rows = [dict(row) for row in cur.fetchall()]
        log_sql("SELECT", q, rows_affected=len(rows))
        return rows
    finally:
        conn.close()

def update_product(product_id: int, name: str, category: str, sku: str, unit_price: float) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = "UPDATE products SET name = ?, category = ?, sku = ?, unit_price = ? WHERE product_id = ?"
        params = (name.strip(), category.strip(), sku.strip(), float(unit_price), product_id)
        cur.execute(q, params)
        conn.commit()
        log_sql("UPDATE", q, params, rows_affected=cur.rowcount)
        return cur.rowcount > 0
    finally:
        conn.close()

def delete_product(product_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = "DELETE FROM products WHERE product_id = ?"
        cur.execute(q, (product_id,))
        conn.commit()
        log_sql("DELETE", q, (product_id,), rows_affected=cur.rowcount)
        return cur.rowcount > 0
    finally:
        conn.close()

# ----------------- CRUD: Suppliers -----------------
def create_supplier(name: str, contact_details: str) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = "INSERT INTO suppliers (name, contact_details) VALUES (?, ?)"
        params = (name.strip(), contact_details.strip())
        cur.execute(q, params)
        conn.commit()
        log_sql("INSERT", q, params, rows_affected=cur.rowcount)
        return cur.lastrowid
    finally:
        conn.close()

def get_suppliers() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = "SELECT * FROM suppliers ORDER BY supplier_id DESC"
        cur.execute(q)
        rows = [dict(row) for row in cur.fetchall()]
        log_sql("SELECT", q, rows_affected=len(rows))
        return rows
    finally:
        conn.close()

def delete_supplier(supplier_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = "DELETE FROM suppliers WHERE supplier_id = ?"
        cur.execute(q, (supplier_id,))
        conn.commit()
        log_sql("DELETE", q, (supplier_id,), rows_affected=cur.rowcount)
        return cur.rowcount > 0
    finally:
        conn.close()

# ----------------- CRUD: Locations / Warehouses -----------------
def create_location(name: str, address: str) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = "INSERT INTO locations (name, address) VALUES (?, ?)"
        params = (name.strip(), address.strip())
        cur.execute(q, params)
        conn.commit()
        log_sql("INSERT", q, params, rows_affected=cur.rowcount)
        return cur.lastrowid
    finally:
        conn.close()

def get_locations() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = "SELECT * FROM locations ORDER BY location_id DESC"
        cur.execute(q)
        rows = [dict(row) for row in cur.fetchall()]
        log_sql("SELECT", q, rows_affected=len(rows))
        return rows
    finally:
        conn.close()

def delete_location(location_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = "DELETE FROM locations WHERE location_id = ?"
        cur.execute(q, (location_id,))
        conn.commit()
        log_sql("DELETE", q, (location_id,), rows_affected=cur.rowcount)
        return cur.rowcount > 0
    finally:
        conn.close()

# ----------------- CRUD: Flood Events -----------------
def create_flood_event(
    event_id: str,
    event_name: str,
    country: str,
    state_province: str,
    river_basin: str,
    start_date: str,
    end_date: Optional[str] = None,
    severity: str = "SEVERE",
    displaced_population: int = 0,
    casualties: int = 0,
    source_dataset: str = "India Flood Inventory and Impacts (1967–2023)",
    geospatial_notes: str = ""
) -> str:
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = """
            INSERT INTO flood_events (
                event_id, event_name, country, state_province, river_basin,
                start_date, end_date, severity, displaced_population, casualties,
                source_dataset, geospatial_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO UPDATE SET
                event_name = excluded.event_name,
                country = excluded.country,
                state_province = excluded.state_province,
                river_basin = excluded.river_basin,
                start_date = excluded.start_date,
                end_date = excluded.end_date,
                severity = excluded.severity,
                displaced_population = excluded.displaced_population,
                casualties = excluded.casualties,
                source_dataset = excluded.source_dataset,
                geospatial_notes = excluded.geospatial_notes
        """
        params = (
            event_id.strip(), event_name.strip(), country.strip(), state_province.strip(),
            river_basin.strip(), start_date.strip(), end_date.strip() if end_date else None,
            severity.strip().upper(), int(displaced_population), int(casualties),
            source_dataset.strip(), geospatial_notes.strip()
        )
        cur.execute(q, params)
        conn.commit()
        log_sql("INSERT flood_events", q, params, rows_affected=cur.rowcount)
        return event_id
    finally:
        conn.close()

def get_flood_events() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = "SELECT * FROM flood_events ORDER BY start_date DESC"
        cur.execute(q)
        rows = [dict(row) for row in cur.fetchall()]
        log_sql("SELECT flood_events", q, rows_affected=len(rows))
        return rows
    finally:
        conn.close()

def get_flood_event_by_id(event_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = "SELECT * FROM flood_events WHERE event_id = ?"
        cur.execute(q, (event_id,))
        row = cur.fetchone()
        log_sql("SELECT flood_event by ID", q, (event_id,), rows_affected=1 if row else 0)
        return dict(row) if row else None
    finally:
        conn.close()

def delete_flood_event(event_id: str) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = "DELETE FROM flood_events WHERE event_id = ?"
        cur.execute(q, (event_id,))
        conn.commit()
        log_sql("DELETE flood_event", q, (event_id,), rows_affected=cur.rowcount)
        return cur.rowcount > 0
    finally:
        conn.close()

# ----------------- CRUD: CWC Rainfall Telemetry -----------------
def create_or_update_telemetry(
    station_id: str,
    station_name: str,
    state_or_region: str,
    river_basin: str,
    hourly_rainfall_mm: float,
    cumulative_24h_mm: float,
    danger_level_meters: float,
    current_water_level_meters: float,
    alert_level: str = "NORMAL",
    source_dataset: str = "CWC Telemetry Hourly Rainfall Data (NWIC)"
) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = """
            INSERT INTO cwc_rainfall_telemetry (
                station_id, station_name, state_or_region, river_basin,
                hourly_rainfall_mm, cumulative_24h_mm, danger_level_meters,
                current_water_level_meters, alert_level, source_dataset, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(station_id) DO UPDATE SET
                hourly_rainfall_mm = excluded.hourly_rainfall_mm,
                cumulative_24h_mm = excluded.cumulative_24h_mm,
                current_water_level_meters = excluded.current_water_level_meters,
                alert_level = excluded.alert_level,
                last_updated = CURRENT_TIMESTAMP
        """
        params = (
            station_id.strip(), station_name.strip(), state_or_region.strip(),
            river_basin.strip(), float(hourly_rainfall_mm), float(cumulative_24h_mm),
            float(danger_level_meters), float(current_water_level_meters),
            alert_level.strip().upper(), source_dataset.strip()
        )
        cur.execute(q, params)
        conn.commit()
        log_sql("UPSERT cwc_rainfall_telemetry", q, params, rows_affected=cur.rowcount)
        return cur.lastrowid
    finally:
        conn.close()

def get_rainfall_telemetry() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = """
            SELECT 
                telemetry_id, station_id, station_name, state_or_region, river_basin,
                hourly_rainfall_mm, cumulative_24h_mm, danger_level_meters,
                current_water_level_meters, alert_level, source_dataset, last_updated,
                ROUND(current_water_level_meters - danger_level_meters, 2) AS freeboard_deficit
            FROM cwc_rainfall_telemetry
            ORDER BY 
                CASE alert_level
                    WHEN 'EXTREME' THEN 1
                    WHEN 'DANGER' THEN 2
                    WHEN 'WARNING' THEN 3
                    WHEN 'ADVISORY' THEN 4
                    ELSE 5
                END, hourly_rainfall_mm DESC
        """
        cur.execute(q)
        rows = [dict(row) for row in cur.fetchall()]
        log_sql("SELECT cwc_rainfall_telemetry", q, rows_affected=len(rows))
        return rows
    finally:
        conn.close()

# ----------------- Inventory JOIN -----------------
def get_inventory_records() -> List[Dict[str, Any]]:
    """3-Way JOIN: inventory + products + locations with stock deficit alert flag"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = """
            SELECT 
                i.inventory_id,
                i.product_id,
                p.name AS product_name,
                p.category,
                p.sku,
                p.unit_price,
                i.location_id,
                l.name AS location_name,
                i.quantity_on_hand,
                i.reorder_level,
                CASE WHEN i.quantity_on_hand <= i.reorder_level THEN 1 ELSE 0 END AS is_low_stock
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            JOIN locations l ON i.location_id = l.location_id
            ORDER BY is_low_stock DESC, p.name ASC
        """
        cur.execute(q)
        rows = [dict(row) for row in cur.fetchall()]
        log_sql("JOIN (Inventory + Products + Locations)", q, rows_affected=len(rows))
        return rows
    finally:
        conn.close()

# ----------------- MULTI-STEP TRANSACTION: Purchase -----------------
def record_purchase(supplier_id: int, product_id: int, location_id: int, quantity: int) -> int:
    """Atomic multi-step transaction: logs purchase order and increments inventory"""
    if quantity <= 0:
        raise ValueError("Quantity received must be strictly positive.")

    conn = get_connection()
    try:
        cur = conn.cursor()
        log_sql("TX BEGIN", "BEGIN TRANSACTION;")
        cur.execute("BEGIN TRANSACTION;")

        q_insert = """
            INSERT INTO purchases (supplier_id, product_id, location_id, quantity_received)
            VALUES (?, ?, ?, ?)
        """
        cur.execute(q_insert, (supplier_id, product_id, location_id, quantity))
        purchase_id = cur.lastrowid
        log_sql("TX STEP 1 (INSERT purchases)", q_insert, (supplier_id, product_id, location_id, quantity))

        q_upsert = """
            INSERT INTO inventory (product_id, location_id, quantity_on_hand, reorder_level)
            VALUES (?, ?, ?, 10)
            ON CONFLICT(product_id, location_id) 
            DO UPDATE SET quantity_on_hand = quantity_on_hand + excluded.quantity_on_hand
        """
        cur.execute(q_upsert, (product_id, location_id, quantity))
        log_sql("TX STEP 2 (UPSERT inventory)", q_upsert, (product_id, location_id, quantity))

        conn.commit()
        log_sql("TX COMMIT", f"COMMIT; Purchase Order #{purchase_id} added {quantity} units to inventory.")
        return purchase_id
    except Exception as e:
        conn.rollback()
        log_sql("TX ROLLBACK", f"ROLLBACK due to error: {e}")
        raise
    finally:
        conn.close()

# ----------------- MULTI-STEP TRANSACTION: Relief Distribution -----------------
def record_relief_distribution(
    location_id: int,
    beneficiary_id: str,
    items: List[Dict[str, int]],
    flood_event_id: Optional[str] = None,
    relief_officer: str = "Field Relief Officer",
    notes: str = ""
) -> int:
    """
    Atomic multi-step transaction for Disaster Response:
    1. Validates available inventory for all requested relief supplies at source location.
    2. Decrements inventory for each item.
    3. Records master entry in relief_distributions.
    4. Records individual items in distribution_items.
    5. Synchronizes into sales table for backwards compatibility.
    """
    if not items:
        raise ValueError("Relief distribution must contain at least one item.")
    if not beneficiary_id:
        raise ValueError("Beneficiary ID is required.")

    conn = get_connection()
    try:
        cur = conn.cursor()
        log_sql("TX BEGIN", "BEGIN TRANSACTION;")
        cur.execute("BEGIN TRANSACTION;")

        # 1 & 2: Check and decrement stock for each item
        for item in items:
            p_id = item["product_id"]
            qty = item["quantity"]
            if qty <= 0:
                raise ValueError(f"Quantity for product #{p_id} must be strictly positive.")

            q_check = "SELECT quantity_on_hand FROM inventory WHERE product_id = ? AND location_id = ?"
            cur.execute(q_check, (p_id, location_id))
            row = cur.fetchone()
            current_stock = row["quantity_on_hand"] if row else 0

            if current_stock < qty:
                raise ValueError(f"Insufficient stock for product #{p_id} (Available: {current_stock}, Requested: {qty}).")

            q_dec = "UPDATE inventory SET quantity_on_hand = quantity_on_hand - ? WHERE product_id = ? AND location_id = ?"
            cur.execute(q_dec, (qty, p_id, location_id))

        # 3. Master distribution entry
        q_dist = """
            INSERT INTO relief_distributions (location_id, beneficiary_id, flood_event_id, relief_officer, status, notes)
            VALUES (?, ?, ?, ?, 'DELIVERED', ?)
        """
        cur.execute(q_dist, (location_id, beneficiary_id, flood_event_id, relief_officer, notes))
        dist_id = cur.lastrowid
        log_sql("TX STEP (INSERT relief_distributions)", q_dist, (location_id, beneficiary_id, flood_event_id, relief_officer, notes))

        # 4. Detail line items & sync with sales
        for item in items:
            p_id = item["product_id"]
            qty = item["quantity"]
            q_item = "INSERT INTO distribution_items (distribution_id, product_id, quantity) VALUES (?, ?, ?)"
            cur.execute(q_item, (dist_id, p_id, qty))

            q_sale = "INSERT INTO sales (product_id, location_id, consumer_id, quantity_sold) VALUES (?, ?, ?, ?)"
            cur.execute(q_sale, (p_id, location_id, beneficiary_id, qty))

        conn.commit()
        log_sql("TX COMMIT", f"COMMIT; Relief Distribution #{dist_id} finalized for beneficiary {beneficiary_id} with {len(items)} item(s).")
        return dist_id
    except Exception as e:
        conn.rollback()
        log_sql("TX ROLLBACK", f"ROLLBACK relief distribution due to error: {e}")
        raise
    finally:
        conn.close()

# ----------------- MULTI-STEP TRANSACTION: Sale (with Distribution sync) -----------------
def record_sale(product_id: int, location_id: int, quantity: int, consumer_id: Optional[str] = None) -> int:
    """Atomic multi-step transaction: checks stock, decrements inventory, logs sale & relief distribution"""
    if quantity <= 0:
        raise ValueError("Quantity sold must be strictly positive.")

    conn = get_connection()
    try:
        cur = conn.cursor()
        log_sql("TX BEGIN", "BEGIN TRANSACTION;")
        cur.execute("BEGIN TRANSACTION;")

        q_check = "SELECT quantity_on_hand FROM inventory WHERE product_id = ? AND location_id = ?"
        cur.execute(q_check, (product_id, location_id))
        row = cur.fetchone()
        current_stock = row["quantity_on_hand"] if row else 0
        log_sql("TX STEP 1 (SELECT inventory check)", q_check, (product_id, location_id), rows_affected=1 if row else 0)

        if current_stock < quantity:
            raise ValueError(f"Insufficient stock at location (Available: {current_stock}, Requested: {quantity}).")

        q_dec = "UPDATE inventory SET quantity_on_hand = quantity_on_hand - ? WHERE product_id = ? AND location_id = ?"
        cur.execute(q_dec, (quantity, product_id, location_id))
        log_sql("TX STEP 2 (UPDATE inventory decrement)", q_dec, (quantity, product_id, location_id))

        q_sale = """
            INSERT INTO sales (product_id, location_id, consumer_id, quantity_sold)
            VALUES (?, ?, ?, ?)
        """
        cur.execute(q_sale, (product_id, location_id, consumer_id, quantity))
        sale_id = cur.lastrowid
        log_sql("TX STEP 3 (INSERT sales)", q_sale, (product_id, location_id, consumer_id, quantity))

        # Also log to relief_distributions for unified schema consistency
        beneficiary = consumer_id or "BEN-DIRECT-RELIEF"
        q_dist = "INSERT INTO relief_distributions (location_id, beneficiary_id, relief_officer, status, notes) VALUES (?, ?, 'Disaster Response Desk', 'DELIVERED', 'Direct Aid Dispatch')"
        cur.execute(q_dist, (location_id, beneficiary))
        dist_id = cur.lastrowid
        q_dist_item = "INSERT INTO distribution_items (distribution_id, product_id, quantity) VALUES (?, ?, ?)"
        cur.execute(q_dist_item, (dist_id, product_id, quantity))

        conn.commit()
        log_sql("TX COMMIT", f"COMMIT; Sale/Dispatch #{sale_id} finalized for {quantity} units. Beneficiary Link: {consumer_id or 'General'}")
        return sale_id
    except Exception as e:
        conn.rollback()
        log_sql("TX ROLLBACK", f"ROLLBACK due to error: {e}")
        raise
    finally:
        conn.close()

# ----------------- MULTI-STEP TRANSACTION: Stock Movement -----------------
def record_stock_movement(product_id: int, movement_type: str, quantity: int,
                          from_location_id: Optional[int] = None,
                          to_location_id: Optional[int] = None) -> int:
    """Atomic multi-step transaction: inter-location transfer, return, or stock correction"""
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")
    if movement_type not in ('TRANSFER', 'RETURN', 'ADJUSTMENT'):
        raise ValueError("Invalid movement type.")

    conn = get_connection()
    try:
        cur = conn.cursor()
        log_sql("TX BEGIN", "BEGIN TRANSACTION;")
        cur.execute("BEGIN TRANSACTION;")

        if movement_type == 'TRANSFER':
            if not from_location_id or not to_location_id:
                raise ValueError("Both source and destination locations required for TRANSFER.")
            if from_location_id == to_location_id:
                raise ValueError("Source and destination locations cannot be identical.")

            # Validate source stock
            cur.execute("SELECT quantity_on_hand FROM inventory WHERE product_id = ? AND location_id = ?",
                        (product_id, from_location_id))
            row = cur.fetchone()
            current_src = row["quantity_on_hand"] if row else 0
            if current_src < quantity:
                raise ValueError(f"Insufficient stock at source warehouse (Available: {current_src}, Needed: {quantity}).")

            # Decrement source
            cur.execute("UPDATE inventory SET quantity_on_hand = quantity_on_hand - ? WHERE product_id = ? AND location_id = ?",
                        (quantity, product_id, from_location_id))

            # Increment target
            cur.execute("""
                INSERT INTO inventory (product_id, location_id, quantity_on_hand, reorder_level)
                VALUES (?, ?, ?, 10)
                ON CONFLICT(product_id, location_id)
                DO UPDATE SET quantity_on_hand = quantity_on_hand + excluded.quantity_on_hand
            """, (product_id, to_location_id, quantity))

        elif movement_type == 'RETURN':
            if not to_location_id:
                raise ValueError("Destination location required for RETURN.")
            cur.execute("""
                INSERT INTO inventory (product_id, location_id, quantity_on_hand, reorder_level)
                VALUES (?, ?, ?, 10)
                ON CONFLICT(product_id, location_id)
                DO UPDATE SET quantity_on_hand = quantity_on_hand + excluded.quantity_on_hand
            """, (product_id, to_location_id, quantity))

        elif movement_type == 'ADJUSTMENT':
            target_loc = from_location_id or to_location_id
            if not target_loc:
                raise ValueError("Location required for ADJUSTMENT.")
            cur.execute("""
                INSERT INTO inventory (product_id, location_id, quantity_on_hand, reorder_level)
                VALUES (?, ?, ?, 10)
                ON CONFLICT(product_id, location_id)
                DO UPDATE SET quantity_on_hand = excluded.quantity_on_hand
            """, (product_id, target_loc, quantity))

        # Insert movement log entry
        q_m = """
            INSERT INTO stock_movements (product_id, from_location_id, to_location_id, movement_type, quantity)
            VALUES (?, ?, ?, ?, ?)
        """
        cur.execute(q_m, (product_id, from_location_id, to_location_id, movement_type, quantity))
        m_id = cur.lastrowid

        conn.commit()
        log_sql("TX COMMIT", f"COMMIT; Stock Movement #{m_id} [{movement_type}] completed.")
        return m_id
    except Exception as e:
        conn.rollback()
        log_sql("TX ROLLBACK", f"ROLLBACK due to error: {e}")
        raise
    finally:
        conn.close()

# ----------------- SQL JOINTS & AGGREGATE REPORTS -----------------

def get_purchases_report() -> List[Dict[str, Any]]:
    """4-Way JOIN: purchases + suppliers + products + locations"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = """
            SELECT 
                pu.purchase_id,
                pu.purchase_date,
                pu.quantity_received,
                s.name AS supplier_name,
                p.name AS product_name,
                p.sku,
                p.unit_price,
                (pu.quantity_received * p.unit_price) AS estimated_value,
                l.name AS location_name
            FROM purchases pu
            JOIN suppliers s ON pu.supplier_id = s.supplier_id
            JOIN products p ON pu.product_id = p.product_id
            JOIN locations l ON pu.location_id = l.location_id
            ORDER BY pu.purchase_date DESC
        """
        cur.execute(q)
        rows = [dict(row) for row in cur.fetchall()]
        log_sql("JOIN (purchases + suppliers + products + locations)", q, rows_affected=len(rows))
        return rows
    finally:
        conn.close()

def get_sales_report() -> List[Dict[str, Any]]:
    """3-Way JOIN: sales + products + locations"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = """
            SELECT 
                sa.sale_id,
                sa.sale_date,
                sa.quantity_sold,
                sa.consumer_id,
                p.name AS product_name,
                p.sku,
                p.unit_price,
                (sa.quantity_sold * p.unit_price) AS total_revenue,
                l.name AS location_name
            FROM sales sa
            JOIN products p ON sa.product_id = p.product_id
            JOIN locations l ON sa.location_id = l.location_id
            ORDER BY sa.sale_date DESC
        """
        cur.execute(q)
        rows = [dict(row) for row in cur.fetchall()]
        log_sql("JOIN (sales + products + locations)", q, rows_affected=len(rows))
        return rows
    finally:
        conn.close()

def get_relief_distributions_report() -> List[Dict[str, Any]]:
    """Multi-table JOIN: relief_distributions + distribution_items + products + locations + flood_events"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = """
            SELECT 
                rd.distribution_id,
                rd.distribution_date,
                rd.beneficiary_id,
                rd.relief_officer,
                rd.status,
                rd.notes,
                l.name AS location_name,
                di.quantity AS item_quantity,
                p.product_id,
                p.name AS product_name,
                p.sku,
                p.category,
                p.unit_price,
                (di.quantity * p.unit_price) AS total_relief_value,
                COALESCE(fe.event_id, 'GENERAL-DISASTER') AS flood_event_id,
                COALESCE(fe.event_name, 'Regional Flood Assistance') AS flood_event_name,
                COALESCE(fe.country, 'Regional') AS country
            FROM relief_distributions rd
            JOIN distribution_items di ON rd.distribution_id = di.distribution_id
            JOIN products p ON di.product_id = p.product_id
            JOIN locations l ON rd.location_id = l.location_id
            LEFT JOIN flood_events fe ON rd.flood_event_id = fe.event_id
            ORDER BY rd.distribution_date DESC
        """
        cur.execute(q)
        rows = [dict(row) for row in cur.fetchall()]
        log_sql("JOIN (relief_distributions + items + products + locations + flood_events)", q, rows_affected=len(rows))
        return rows
    finally:
        conn.close()

def report_stock_by_location() -> List[Dict[str, Any]]:
    """Aggregate: GROUP BY location"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = """
            SELECT 
                l.location_id,
                l.name AS location_name,
                COUNT(i.product_id) AS distinct_products_count,
                COALESCE(SUM(i.quantity_on_hand), 0) AS total_units_in_stock
            FROM locations l
            LEFT JOIN inventory i ON l.location_id = i.location_id
            GROUP BY l.location_id, l.name
            ORDER BY total_units_in_stock DESC
        """
        cur.execute(q)
        rows = [dict(row) for row in cur.fetchall()]
        log_sql("AGGREGATE GROUP BY location", q, rows_affected=len(rows))
        return rows
    finally:
        conn.close()

def report_supplier_purchases() -> List[Dict[str, Any]]:
    """Aggregate: GROUP BY suppliers + HAVING sum > 0"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = """
            SELECT 
                s.supplier_id,
                s.name AS supplier_name,
                COUNT(pu.purchase_id) AS total_orders,
                SUM(pu.quantity_received) AS total_units_supplied
            FROM suppliers s
            JOIN purchases pu ON s.supplier_id = pu.supplier_id
            GROUP BY s.supplier_id, s.name
            HAVING SUM(pu.quantity_received) > 0
            ORDER BY total_units_supplied DESC
        """
        cur.execute(q)
        rows = [dict(row) for row in cur.fetchall()]
        log_sql("AGGREGATE GROUP BY + HAVING supplier purchases", q, rows_affected=len(rows))
        return rows
    finally:
        conn.close()

def report_low_stock_products() -> List[Dict[str, Any]]:
    """JOIN & Filter: items at or below reorder level"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = """
            SELECT 
                p.product_id,
                p.name AS product_name,
                p.sku,
                l.name AS location_name,
                i.quantity_on_hand,
                i.reorder_level,
                (i.reorder_level - i.quantity_on_hand) AS deficit
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            JOIN locations l ON i.location_id = l.location_id
            WHERE i.quantity_on_hand <= i.reorder_level
            ORDER BY deficit DESC
        """
        cur.execute(q)
        rows = [dict(row) for row in cur.fetchall()]
        log_sql("JOIN + FILTER low stock alerts", q, rows_affected=len(rows))
        return rows
    finally:
        conn.close()

def report_sales_by_product() -> List[Dict[str, Any]]:
    """Aggregate: GROUP BY product + HAVING sum > 0"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = """
            SELECT 
                p.product_id,
                p.name AS product_name,
                p.sku,
                p.category,
                SUM(sa.quantity_sold) AS total_quantity_sold,
                SUM(sa.quantity_sold * p.unit_price) AS total_sales_revenue
            FROM products p
            JOIN sales sa ON p.product_id = sa.product_id
            GROUP BY p.product_id, p.name, p.sku, p.category
            HAVING SUM(sa.quantity_sold) > 0
            ORDER BY total_sales_revenue DESC
        """
        cur.execute(q)
        rows = [dict(row) for row in cur.fetchall()]
        log_sql("AGGREGATE GROUP BY + HAVING sales by product", q, rows_affected=len(rows))
        return rows
    finally:
        conn.close()

def report_distributions_by_event() -> List[Dict[str, Any]]:
    """Aggregate: GROUP BY flood_events with relief distribution stats"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = """
            SELECT 
                fe.event_id,
                fe.event_name,
                fe.country,
                fe.state_province,
                fe.river_basin,
                fe.severity,
                fe.source_dataset,
                COUNT(DISTINCT rd.distribution_id) AS total_distributions,
                COALESCE(SUM(di.quantity), 0) AS total_relief_units_dispatched,
                COALESCE(SUM(di.quantity * p.unit_price), 0) AS total_relief_value
            FROM flood_events fe
            LEFT JOIN relief_distributions rd ON fe.event_id = rd.flood_event_id
            LEFT JOIN distribution_items di ON rd.distribution_id = di.distribution_id
            LEFT JOIN products p ON di.product_id = p.product_id
            GROUP BY 
                fe.event_id, fe.event_name, fe.country, fe.state_province,
                fe.river_basin, fe.severity, fe.source_dataset
            ORDER BY total_relief_units_dispatched DESC
        """
        cur.execute(q)
        rows = [dict(row) for row in cur.fetchall()]
        log_sql("AGGREGATE GROUP BY flood_events", q, rows_affected=len(rows))
        return rows
    finally:
        conn.close()

def get_stock_movements_report() -> List[Dict[str, Any]]:
    """JOIN: stock_movements + products + from_location + to_location"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        q = """
            SELECT 
                sm.movement_id,
                sm.movement_date,
                sm.movement_type,
                sm.quantity,
                p.name AS product_name,
                p.sku,
                COALESCE(fl.name, 'N/A') AS from_location_name,
                COALESCE(tl.name, 'N/A') AS to_location_name
            FROM stock_movements sm
            JOIN products p ON sm.product_id = p.product_id
            LEFT JOIN locations fl ON sm.from_location_id = fl.location_id
            LEFT JOIN locations tl ON sm.to_location_id = tl.location_id
            ORDER BY sm.movement_date DESC
        """
        cur.execute(q)
        rows = [dict(row) for row in cur.fetchall()]
        log_sql("JOIN (movements + products + locations)", q, rows_affected=len(rows))
        return rows
    finally:
        conn.close()
