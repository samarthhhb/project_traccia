"""TRACCIA Server Launcher"""
import os
import sys
import argparse
import signal
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend import mongo_db
from backend.seed_data import seed_all
from backend.logger import CYAN, GREEN, RESET

def print_banner(host: str, port: int) -> None:
    base_url = f"http://{host}:{port}"
    art = (
        f"{CYAN}"
        "  _____ ____      _    ____ ____ ___    _   \n"
        " |_   _|  _ \\    / \\  / ___/ ___|_ _|  / \\  \n"
        "   | | | |_) |  / _ \\| |  | |    | |  / _ \\ \n"
        "   | | |  _ <  / ___ \\ |__| |___ | | / ___ \\\n"
        "   |_| |_| \\_\\/_/   \\_\\____\\____|___/_/   \\_\\\n"
        f"{RESET}"
    )
    print(f"\n{art}")
    print(f"  {GREEN}● Dashboard:{RESET} {base_url}/")
    print(f"  {CYAN}● API Docs:{RESET}  {base_url}/docs\n")

def main():
    parser = argparse.ArgumentParser(description="TRACCIA Server Launcher")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)), help="Port (default: 8000)")
    parser.add_argument("--host", type=str, default=os.environ.get("HOST", "127.0.0.1"), help="Host (default: 127.0.0.1)")
    parser.add_argument("--reload", action="store_true", help="Auto-reload on changes")
    parser.add_argument("--seed", action="store_true", help="Force re-seed database")
    parser.add_argument("--reset", action="store_true", help="Reset database and re-seed")
    args = parser.parse_args()

    db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "traccia.db")

    if args.reset:
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except Exception:
                pass
        mdb = mongo_db.get_mongo_db()
        mdb.consumers.drop()
        mdb.grievances.drop()
        seed_all()
    elif args.seed:
        seed_all()
    else:
        mdb = mongo_db.get_mongo_db()
        if not os.path.exists(db_file) or mdb.consumers.count_documents({"is_deleted": {"$ne": True}}) == 0:
            seed_all()

    print_banner(args.host, args.port)

    # Clean shutdown on Ctrl+C
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))

    try:
        uvicorn.run(
            "backend.server:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="warning"
        )
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
