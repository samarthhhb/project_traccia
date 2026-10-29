# TRACCIA: Database Integration Guide

TRACCIA utilizes a **polyglot persistence architecture** integrating a relational database (**SQL / SQLite / PostgreSQL**) and a document database (**MongoDB / PyMongo**) through Python. This document outlines how both database systems are configured, connected, and linked across transactional workflows.

---

## 1. Architectural Overview

```
                      ┌──────────────────────────────────────────────┐
                      │             FastAPI Application              │
                      │             (backend/server.py)              │
                      └───────────────┬──────────────┬───────────────┘
                                      │              │
                   Direct Python API  │              │  PyMongo / mongomock
                                      ▼              ▼
                     ┌──────────────────┐          ┌──────────────────┐
                     │   SQL Database   │          │ MongoDB Document │
                     │ (backend/sql_db) │          │(backend/mongo_db)│
                     └────────┬─────────┘          └────────┬─────────┘
                              │                             │
                              │       Cross-DB Linking      │
                              └─────── (Event / ID) ────────┘
```

- **Relational SQL Database (`backend/sql_db.py`)**: Handles strictly-structured, ACID-critical data—such as relief supply catalog, multi-warehouse inventory levels, supplier purchases, and river telemetry.
- **Document MongoDB Database (`backend/mongo_db.py`)**: Handles flexible, polymorphic disaster beneficiary profiles and grievance tickets with chronologically embedded timeline update histories.
- **Cross-Database Linking**: MongoDB documents link to SQL records using `flood_event_id`, while SQL distributions link to MongoDB beneficiary records via `consumer_id`.

---

## 2. SQL Integration (`backend/sql_db.py`)

### Connection Management
Python connects to SQLite (with support for PostgreSQL connection parity) and enforces relational integrity via foreign key pragma:

```python
import sqlite3
import os

DB_PATH = os.environ.get("TRACCIA_SQL_PATH", "data/traccia.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enables dict-like column access
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
```

### Schema Definition & Data Integrity Checks
Tables are initialized with primary keys, foreign keys, and domain check constraints:

```sql
CREATE TABLE IF NOT EXISTS inventory (
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
    reorder_level INTEGER NOT NULL DEFAULT 10 CHECK(reorder_level >= 0),
    PRIMARY KEY (product_id, location_id)
);
```

### ACID Transaction Atomicity
Complex operations such as **multi-item relief dispatches** or **stock transfers** run inside explicit Python database transactions with automated rollback on shortfall:

```python
def create_relief_distribution(location_id, consumer_id, flood_event_id, officer_name, items):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN TRANSACTION;")
        
        # 1. Verify stock availability for all items before decrementing
        for it in items:
            cur.execute(
                "SELECT quantity FROM inventory WHERE product_id = ? AND location_id = ?",
                (it["product_id"], location_id)
            )
            row = cur.fetchone()
            if not row or row["quantity"] < it["quantity"]:
                raise ValueError(f"Insufficient stock for product ID {it['product_id']}")

        # 2. Insert distribution record
        cur.execute("""
            INSERT INTO relief_distributions (location_id, consumer_id, flood_event_id, officer_name)
            VALUES (?, ?, ?, ?)
        """, (location_id, consumer_id, flood_event_id, officer_name))
        dist_id = cur.lastrowid

        # 3. Deduct stock and record distribution line items
        for it in items:
            cur.execute("""
                UPDATE inventory SET quantity = quantity - ? 
                WHERE product_id = ? AND location_id = ?
            """, (it["quantity"], it["product_id"], location_id))
            
            cur.execute("""
                INSERT INTO distribution_items (distribution_id, product_id, quantity)
                VALUES (?, ?, ?)
            """, (dist_id, it["product_id"], it["quantity"]))

        conn.commit()
        return dist_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
```

---

## 3. MongoDB Integration (`backend/mongo_db.py`)

### Resilient Client Connection (PyMongo with Mock Fallback)
The system automatically connects to a live MongoDB instance via `TRACCIA_MONGO_URI`, and transparently falls back to `mongomock` in isolated or offline environments without altering queries:

```python
import os

_mongo_client = None
_db = None

def get_mongo_db():
    global _mongo_client, _db
    if _db is not None:
        return _db
    
    mongo_uri = os.environ.get("TRACCIA_MONGO_URI", "mongodb://localhost:27017")
    try:
        import pymongo
        client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=1000)
        client.admin.command('ping')
        _mongo_client = client
        _db = _mongo_client["traccia_db"]
        init_mongo_indexes(_db)
        return _db
    except Exception:
        import mongomock
        _mongo_client = mongomock.MongoClient()
        _db = _mongo_client["traccia_db"]
        init_mongo_indexes(_db)
        return _db
```

### Document Indexing
Indexes optimize query execution across beneficiary IDs, flood incident linkages, and grievance priority status:

```python
def init_mongo_indexes(db):
    db.consumers.create_index("consumer_id", unique=True)
    db.consumers.create_index("flood_event_id")
    db.grievances.create_index("grievance_id", unique=True)
    db.grievances.create_index([("status", 1), ("priority", 1)])
```

### Embedded Timeline Updates via `$push`
Rather than splitting history across multiple joins, grievances preserve an immutable chronological activity history inside the root document using MongoDB's `$push`:

```python
def update_grievance_status(grievance_id, new_status, note, updated_by="System"):
    db = get_mongo_db()
    timeline_entry = {
        "status": new_status,
        "note": note,
        "updated_by": updated_by,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    result = db.grievances.update_one(
        {"grievance_id": grievance_id},
        {
            "$set": {
                "status": new_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            "$push": {"timeline": timeline_entry}
        }
    )
    return result.modified_count > 0
```

---

## 4. Cross-Database Workflow Integration

The backend orchestrator (`backend/server.py`) harmonizes SQL and NoSQL data into unified API responses:

```
[SQL Database]                       [MongoDB Document Store]
flood_events                          consumers
  ├── event_id: "IND-2018-KERALA" ◄─────── flood_event_id: "IND-2018-KERALA"
  │                                   grievances
relief_distributions                  ├── flood_event_id: "IND-2018-KERALA"
  └── consumer_id: "BEN-KER-001" ◄─────── consumer_id: "BEN-KER-001"
```

1. **Beneficiary Onboarding**: A citizen registers during a flood; a profile is stored in MongoDB referencing the SQL `event_id`.
2. **Relief Package Allocation**: Field operators log relief packages in SQL against warehouse inventory, tagging the recipient's MongoDB `consumer_id`.
3. **Unified Incident View**: When querying `/api/events/{event_id}`, the API pulls geospatial severity from SQL and executes parallel queries in MongoDB to return registered citizens and unresolved grievances for that event.
