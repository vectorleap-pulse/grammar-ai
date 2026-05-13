import sys
import traceback
from pathlib import Path

from loguru import logger

_DATA_DIR = Path.home() / ".grammar-ai"


def _ensure_exe_name() -> None:
    """Rename the running exe to grammar-ai.exe if it has a different name."""
    if not getattr(sys, "frozen", False):
        logger.debug("Not running as frozen executable; skipping exe name check")
        return
    exe = Path(sys.executable)
    target = "grammar-ai.exe"
    if exe.name.lower() == target:
        return
    # Leave update backup files alone
    if "-old" in exe.stem:
        return
    new_path = exe.parent / target
    try:
        exe.rename(new_path)
        logger.info(f"Renamed {exe.name} to {target}")
    except Exception as e:
        logger.warning(f"Could not rename {exe.name} to {target}: {e}")


def main() -> None:
    try:
        logger.remove()

        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(_DATA_DIR / "grammar_ai.log"),
            rotation="10 MB",
            level="DEBUG",
            encoding="utf-8",
        )

        if not getattr(sys, "frozen", False) and sys.stderr:
            logger.add(sys.stderr, level="WARNING")

        _ensure_exe_name()

        from app.core.autorun import configure_autorun
        from app.db.database import init_db, load_autorun
        from app.ui.main_window import MainWindow

        init_db()
        configure_autorun(load_autorun())
        app = MainWindow()
        app.mainloop()
    except Exception as e:
        error_msg = f"Error starting Grammar AI: {e}\n{traceback.format_exc()}"
        print(error_msg)
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(_DATA_DIR / "error.log", "w") as f:
                f.write(error_msg)
        except Exception as write_err:
            print(f"Could not write error.log: {write_err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
