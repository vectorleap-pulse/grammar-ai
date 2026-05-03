import sys
import traceback

from loguru import logger


def main() -> None:
    try:
        logger.remove()

        # Always log to file
        logger.add("grammar_ai.log", rotation="10 MB", level="DEBUG", encoding="utf-8")

        # Only add console logging in dev mode
        if not getattr(sys, "frozen", False) and sys.stderr:
            logger.add(sys.stderr, level="WARNING")

        from app.db.database import init_db
        from app.ui.main_window import MainWindow

        init_db()
        app = MainWindow()
        app.mainloop()
    except Exception as e:
        # Fallback error handling for compiled executable
        error_msg = f"Error starting Grammar AI: {e}\n{traceback.format_exc()}"
        print(error_msg)  # Print to console in case GUI fails
        try:
            with open("error.log", "w") as f:
                f.write(error_msg)
        except:  # noqa: E722
            pass  # If we can't write to file, at least we printed to console
        sys.exit(1)


if __name__ == "__main__":
    main()
