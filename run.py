import socket
import subprocess
import time
from pathlib import Path


def ensure_postgres_running():
    """Checks if PostgreSQL is reachable on port 5432; if not, automatically launches it."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('127.0.0.1', 5432))
    sock.close()
    if result != 0:
        print("[SmartCivic] PostgreSQL not running on port 5432. Starting database...")
        data_dir = Path(r"C:\Program Files\PostgreSQL\18\data")
        pid_file = data_dir / "postmaster.pid"
        if pid_file.exists():
            try:
                pid_file.unlink()
            except Exception:
                pass
        pg_ctl = Path(r"C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe")
        log_file = data_dir / "log" / "pg_startup.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        if pg_ctl.exists():
            subprocess.run(
                [str(pg_ctl), "-D", str(data_dir), "-l", str(log_file), "start"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False
            )
        for _ in range(25):
            time.sleep(0.5)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            r = s.connect_ex(('127.0.0.1', 5432))
            s.close()
            if r == 0:
                print("[SmartCivic] PostgreSQL database is ready and connected!")
                return


if __name__ == "__main__":
    ensure_postgres_running()
    from app import create_app
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
else:
    from app import create_app
    app = create_app()

