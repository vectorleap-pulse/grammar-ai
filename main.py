import argparse
import sys
import traceback

from loguru import logger

from app import i18n
from app.config import DATA_DIR, ERROR_LOG_PATH, LOG_PATH
from app.core.autorun import configure_autorun
from app.db.database import init_db, load_autorun, load_ui_language
from app.ui.main_window import MainWindow


def main() -> None:
    try:
        logger.remove()

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        logger.add(str(LOG_PATH), rotation="10 MB", level="DEBUG", encoding="utf-8")

        if sys.stderr:
            logger.add(sys.stderr, level="WARNING")

        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--tray-only", action="store_true")
        args, _ = parser.parse_known_args()

        init_db()
        i18n.set_language(load_ui_language())
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
