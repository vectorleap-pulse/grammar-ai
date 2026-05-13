import argparse
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

from loguru import logger

from app.config import DATA_DIR, ERROR_LOG_PATH, EXE_OLD_SUFFIX, LOG_PATH
from app.core.autorun import configure_autorun
from app.db.database import init_db, load_autorun
from app.ui.main_window import MainWindow


def _ensure_exe_name() -> None:
    """Rename the running exe to grammar-ai.exe if it has a different name."""
    if not getattr(sys, "frozen", False):
        logger.debug("Not running as frozen executable; skipping exe name check")
        return
    exe = Path(sys.executable)
    target = "grammar-ai.exe"
    if exe.name.lower() == target:
        return
    if EXE_OLD_SUFFIX in exe.stem:
        return
    new_path = exe.parent / target
    try:
        if new_path.exists():
            ts = datetime.now().strftime("%Y%m%dT%H%M%S")
            stale = new_path.with_name(f"{new_path.stem}-{ts}{EXE_OLD_SUFFIX}{new_path.suffix}")
            new_path.rename(stale)
            logger.debug(f"Moved existing {target} to {stale.name} for cleanup")
        exe.rename(new_path)
        logger.info(f"Renamed {exe.name} to {target}; restarting")
        subprocess.Popen([str(new_path)] + sys.argv[1:])
        sys.exit(0)
    except Exception as e:
        logger.warning(f"Could not rename {exe.name} to {target}: {e}")


def main() -> None:
    try:
        logger.remove()

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        logger.add(str(LOG_PATH), rotation="10 MB", level="DEBUG", encoding="utf-8")

        if not getattr(sys, "frozen", False) and sys.stderr:
            logger.add(sys.stderr, level="WARNING")

        _ensure_exe_name()

        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--tray-only", action="store_true")
        args, _ = parser.parse_known_args()

        init_db()
        configure_autorun(load_autorun())
        app = MainWindow(tray_only=args.tray_only)
        app.mainloop()
    except Exception as e:
        error_msg = f"Error starting Grammar AI: {e}\n{traceback.format_exc()}"
        print(error_msg)
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(ERROR_LOG_PATH, "w") as f:
                f.write(error_msg)
        except Exception as write_err:
            print(f"Could not write error.log: {write_err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
