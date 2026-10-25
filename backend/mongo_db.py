"""
TRACCIA MongoDB Database Manager with live terminal operation logging.
Disaster Beneficiary Onboarding, Grievance Lifecycle & Flood Event Referencing.
"""
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from bson import ObjectId

_mongo_client = None
_db = None

# ANSI colors
from backend.logger import format_mongo_log, GREEN, YELLOW, MAGENTA, BOLD, RESET

def log_mongo(action: str, collection: str, query_or_doc: Any = None, result_summary: str = ""):
    print(format_mongo_log(action, collection, query_or_doc, result_summary))

def get_mongo_db():
    global _mongo_client, _db
    if _db is not None:
        return _db
    
    mongo_uri = os.environ.get("TRACCIA_MONGO_URI", "mongodb://localhost:27017")
    use_mock = os.environ.get("TRACCIA_USE_MOCK_MONGO", "").lower() in ("1", "true", "yes")

    if not use_mock:
        try:
            import pymongo
            client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=1000)
            client.admin.command('ping')
            _mongo_client = client
            _db = _mongo_client["traccia_db"]
            init_mongo_indexes(_db)
            return _db
        except Exception:
            pass

    import mongomock
    _mongo_client = mongomock.MongoClient()
    _db = _mongo_client["traccia_db"]
    init_mongo_indexes(_db)
    return _db

def init_mongo_indexes(db):
    try:
        db.consumers.create_index("consumer_id", unique=True)
        db.consumers.create_index("flood_event_id")
        db.consumers.create_index("district")
        db.consumers.create_index("is_deleted")
        db.grievances.create_index("grievance_id", unique=True)
        db.grievances.create_index("consumer_id")
        db.grievances.create_index("flood_event_id")
        db.grievances.create_index([("status", 1), ("priority", 1)])
        db.grievances.create_index("is_deleted")
    except Exception:
        pass

def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    clean = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            clean[k] = str(v)
        elif isinstance(v, datetime):
            clean[k] = v.isoformat()
        elif isinstance(v, list):
            clean[k] = [serialize_doc(item) if isinstance(item, dict) else item for item in v]
        elif isinstance(v, dict):
            clean[k] = serialize_doc(v)
        else:
            clean[k] = v
    return clean

# ----------------- CRUD: Consumers / Beneficiaries -----------------

def create_consumer(
    consumer_id: str,
    name: str,
    contact: str,
    preferences: str = "",
    verification_status: str = "PENDING",
    address: str = "",
    district: str = "",
    state_country: str = "",
    flood_event_id: str = "",
    vulnerability_category: str = "GENERAL",
    family_members_count: int = 1,
    is_synthetic: bool = True
) -> Dict[str, Any]:
    db = get_mongo_db()
    if not consumer_id or not name:
        raise ValueError("Consumer/Beneficiary ID and Name are required fields.")
    
    existing = db.consumers.find_one({"consumer_id": consumer_id, "is_deleted": {"$ne": True}})
    if existing:
        raise ValueError(f"Consumer/Beneficiary with ID '{consumer_id}' already exists.")

    doc = {
        "consumer_id": consumer_id.strip(),
        "name": name.strip(),
        "contact": contact.strip(),
        "preferences": preferences.strip(),
        "verification_status": verification_status.strip().upper(),
        "address": address.strip(),
        "district": district.strip(),
        "state_country": state_country.strip(),
        "flood_event_id": flood_event_id.strip(),
        "vulnerability_category": vulnerability_category.strip().upper(),
        "family_members_count": int(family_members_count) if family_members_count else 1,
        "is_synthetic": bool(is_synthetic),
        "dataset_context": "Synthetic beneficiary mapped to historical disaster response case study",
        "onboarding_date": datetime.now(timezone.utc),
        "is_deleted": False
    }
    result = db.consumers.insert_one(doc)
    doc["_id"] = result.inserted_id
    log_mongo("insertOne", "consumers", {"consumer_id": doc["consumer_id"], "name": doc["name"], "event": doc["flood_event_id"]}, f"Inserted _id={doc['_id']}")
    return serialize_doc(doc)

def get_consumers(
    include_deleted: bool = False,
    flood_event_id: Optional[str] = None,
    district: Optional[str] = None,
    verification_status: Optional[str] = None
) -> List[Dict[str, Any]]:
    db = get_mongo_db()
    query: Dict[str, Any] = {}
    if not include_deleted:
        query["is_deleted"] = {"$ne": True}
    if flood_event_id:
        query["flood_event_id"] = flood_event_id
    if district:
        query["district"] = district
    if verification_status:
        query["verification_status"] = verification_status.upper()

    cursor = db.consumers.find(query).sort("onboarding_date", -1)
    docs = [serialize_doc(d) for d in cursor]
    log_mongo("find", "consumers", query, f"Found {len(docs)} consumer/beneficiary document(s)")
    return docs

def get_consumer_by_id(consumer_id: str) -> Optional[Dict[str, Any]]:
    db = get_mongo_db()
    query = {"consumer_id": consumer_id, "is_deleted": {"$ne": True}}
    doc = db.consumers.find_one(query)
    log_mongo("findOne", "consumers", query, "Match found" if doc else "None")
    return serialize_doc(doc) if doc else None

def update_consumer(consumer_id: str, updates: Dict[str, Any]) -> bool:
    db = get_mongo_db()
    updates.pop("_id", None)
    updates.pop("consumer_id", None)
    
    query = {"consumer_id": consumer_id, "is_deleted": {"$ne": True}}
    res = db.consumers.update_one(query, {"$set": updates})
    log_mongo("updateOne", "consumers", {"query": query, "$set": updates}, f"Modified: {res.modified_count}")
    return res.modified_count > 0

def delete_consumer(consumer_id: str, soft_delete: bool = True) -> bool:
    db = get_mongo_db()
    if soft_delete:
        res = db.consumers.update_one(
            {"consumer_id": consumer_id},
            {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc)}}
        )
        log_mongo("updateOne (Soft Delete)", "consumers", {"consumer_id": consumer_id}, f"Soft-deleted: {res.modified_count}")
        return res.modified_count > 0
    else:
        res = db.consumers.delete_one({"consumer_id": consumer_id})
        log_mongo("deleteOne", "consumers", {"consumer_id": consumer_id}, f"Deleted: {res.deleted_count}")
        return res.deleted_count > 0

# ----------------- CRUD: Grievances & Relief Requests -----------------

def create_grievance(
    grievance_id: str,
    consumer_id: str,
    category: str,
    description: str,
    priority: str = "MEDIUM",
    assigned_team: str = "Disaster Relief Cell",
    affected_location: str = "",
    flood_event_id: str = "",
    is_synthetic: bool = True
) -> Dict[str, Any]:
    db = get_mongo_db()
    if not grievance_id or not consumer_id or not description:
        raise ValueError("Grievance ID, Consumer ID, and Description are required.")

    consumer = db.consumers.find_one({"consumer_id": consumer_id, "is_deleted": {"$ne": True}})
    if not consumer:
        raise ValueError(f"No active consumer/beneficiary found with ID '{consumer_id}'.")

    if db.grievances.find_one({"grievance_id": grievance_id}):
        raise ValueError(f"Grievance with ID '{grievance_id}' already exists.")

    # Inherit flood event from beneficiary if not specified
    eff_event_id = flood_event_id.strip() if flood_event_id else consumer.get("flood_event_id", "")
    eff_location = affected_location.strip() if affected_location else consumer.get("address", "")

    now = datetime.now(timezone.utc)
    doc = {
        "grievance_id": grievance_id.strip(),
        "consumer_id": consumer_id.strip(),
        "category": category.strip(),
        "description": description.strip(),
        "priority": priority.strip().upper(),
        "status": "OPEN",
        "assigned_team": assigned_team.strip(),
        "affected_location": eff_location,
        "flood_event_id": eff_event_id,
        "is_synthetic": bool(is_synthetic),
        "resolution": None,
        "created_date": now,
        "updates": [
            {
                "timestamp": now,
                "note": "Assistance request logged in disaster grievance queue.",
                "status": "OPEN",
                "staff_id": "DISASTER_OPS"
            }
        ],
        "is_deleted": False
    }
    result = db.grievances.insert_one(doc)
    doc["_id"] = result.inserted_id
    log_mongo("insertOne", "grievances", {"grievance_id": doc["grievance_id"], "consumer_id": doc["consumer_id"], "priority": doc["priority"]}, f"Inserted _id={doc['_id']}")
    return serialize_doc(doc)

def get_grievances(
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    consumer_id: Optional[str] = None,
    flood_event_id: Optional[str] = None,
    include_deleted: bool = False
) -> List[Dict[str, Any]]:
    db = get_mongo_db()
    query: Dict[str, Any] = {}
    if not include_deleted:
        query["is_deleted"] = {"$ne": True}
    if status:
        query["status"] = status.upper()
    if category:
        query["category"] = category
    if priority:
        query["priority"] = priority.upper()
    if consumer_id:
        query["consumer_id"] = consumer_id
    if flood_event_id:
        query["flood_event_id"] = flood_event_id

    cursor = db.grievances.find(query).sort("created_date", -1)
    docs = [serialize_doc(d) for d in cursor]
    log_mongo("find", "grievances", query, f"Returned {len(docs)} ticket(s)")
    return docs

def get_grievance_by_id(grievance_id: str) -> Optional[Dict[str, Any]]:
    db = get_mongo_db()
    query = {"grievance_id": grievance_id, "is_deleted": {"$ne": True}}
    doc = db.grievances.find_one(query)
    log_mongo("findOne", "grievances", query, "Match found" if doc else "None")
    return serialize_doc(doc) if doc else None

def update_grievance(
    grievance_id: str,
    status: Optional[str] = None,
    assigned_team: Optional[str] = None,
    resolution: Optional[str] = None,
    update_note: Optional[str] = None,
    staff_id: str = "FIELD_STAFF"
) -> bool:
    db = get_mongo_db()
    current = db.grievances.find_one({"grievance_id": grievance_id, "is_deleted": {"$ne": True}})
    if not current:
        raise ValueError(f"Grievance '{grievance_id}' not found.")

    set_fields: Dict[str, Any] = {}
    new_status = status.upper() if status else current["status"]

    if status:
        set_fields["status"] = new_status
    if assigned_team:
        set_fields["assigned_team"] = assigned_team.strip()
    if resolution is not None:
        set_fields["resolution"] = resolution.strip()

    note_text = update_note or f"Updated status to {new_status}"
    timeline_entry = {
        "timestamp": datetime.now(timezone.utc),
        "note": note_text,
        "status": new_status,
        "staff_id": staff_id
    }

    res = db.grievances.update_one(
        {"grievance_id": grievance_id},
        {
            "$set": set_fields,
            "$push": {"updates": timeline_entry}
        }
    )
    log_mongo("updateOne ($push timeline update)", "grievances", {"grievance_id": grievance_id, "status": new_status}, f"Timeline appended. Modified: {res.modified_count}")
    return res.modified_count > 0

def delete_grievance(grievance_id: str, soft_delete: bool = True) -> bool:
    db = get_mongo_db()
    if soft_delete:
        res = db.grievances.update_one(
            {"grievance_id": grievance_id},
            {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc)}}
        )
        log_mongo("updateOne (Soft Delete)", "grievances", {"grievance_id": grievance_id}, f"Soft-deleted: {res.modified_count}")
        return res.modified_count > 0
    else:
        res = db.grievances.delete_one({"grievance_id": grievance_id})
        log_mongo("deleteOne", "grievances", {"grievance_id": grievance_id}, f"Deleted: {res.deleted_count}")
        return res.deleted_count > 0

def get_disaster_grievance_stats() -> Dict[str, Any]:
    """Status & Priority breakdown for disaster intelligence dashboards"""
    db = get_mongo_db()
    all_grievances = list(db.grievances.find({"is_deleted": {"$ne": True}}))
    
    status_counts = {"OPEN": 0, "IN_PROGRESS": 0, "RESOLVED": 0}
    priority_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    by_event: Dict[str, int] = {}

    for g in all_grievances:
        st = g.get("status", "OPEN").upper()
        pr = g.get("priority", "MEDIUM").upper()
        ev = g.get("flood_event_id") or "UNASSIGNED"

        status_counts[st] = status_counts.get(st, 0) + 1
        priority_counts[pr] = priority_counts.get(pr, 0) + 1
        by_event[ev] = by_event.get(ev, 0) + 1

    return {
        "status_counts": status_counts,
        "priority_counts": priority_counts,
        "by_event": by_event,
        "total": len(all_grievances)
    }
