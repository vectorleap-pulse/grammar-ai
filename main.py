import sys

from loguru import logger


def main() -> None:
    logger.remove()
    logger.add(sys.stderr, level="WARNING")
    logger.add("grammar_ai.log", rotation="10 MB", level="DEBUG")
    logger.info("Starting Grammar AI")

    from app.db.database import init_db
    from app.ui.main_window import MainWindow

    init_db()
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
