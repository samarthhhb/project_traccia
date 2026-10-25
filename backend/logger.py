"""TRACCIA Activity Logger"""
import time
import contextvars
from typing import Optional, Any

# Reduced, purposeful colors
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[96m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
WHITE = "\033[97m"

current_request_ctx = contextvars.ContextVar("current_request_ctx", default=None)

def log_api_call(method: str, path: str, status_code: int, duration_ms: float) -> None:
    """Logs a completed HTTP API call with status and newline."""
    timestamp = time.strftime("%H:%M:%S")
    status_color = GREEN if status_code < 400 else RED
    print(f"{CYAN}[API {timestamp}]{RESET} {method} {path} -> {status_color}{status_code}{RESET} {DIM}({duration_ms:.1f}ms){RESET}\n")

def log_api_request(method: str, path: str, query: str = "", client_ip: str = "") -> None:
    pass

def log_api_response(method: str, path: str, status_code: int, duration_ms: float) -> None:
    log_api_call(method, path, status_code, duration_ms)

def format_sql_log(action: str, query: str = "", params: Any = None, rows_affected: Optional[int] = None) -> str:
    """Formats a simplified SQL log with blue tag."""
    timestamp = time.strftime("%H:%M:%S")
    param_str = f" {params}" if params else ""
    row_str = f" -> {rows_affected} rows" if rows_affected is not None else ""
    return f"  {BLUE}[SQL {timestamp}]{RESET} {action}{param_str}{row_str}"

def format_mongo_log(action: str, collection: str, query_or_doc: Any = None, result_summary: str = "") -> str:
    """Formats a simplified MongoDB log with magenta tag."""
    timestamp = time.strftime("%H:%M:%S")

    detail = ""
    if isinstance(query_or_doc, dict):
        clean = {k: v for k, v in query_or_doc.items() if k != "is_deleted"}
        if clean:
            detail = f" ({', '.join(f'{k}={v}' for k, v in clean.items())})"
    elif query_or_doc:
        detail = f" ({query_or_doc})"

    summary = ""
    if result_summary:
        s = result_summary.replace("consumer/beneficiary document(s)", "docs")
        s = s.replace("document(s)", "docs")
        s = s.replace("ticket(s)", "tickets")
        s = s.replace("Found ", "")
        s = s.replace("Returned ", "")
        summary = f" -> {s.strip()}"

    return f"  {MAGENTA}[MONGO {timestamp}]{RESET} {collection}.{action}{detail}{summary}"
