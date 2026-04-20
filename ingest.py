import logging

from llm.factory import configure_logging, get_settings
from rag.ingestion import build_indices

LOGGER = logging.getLogger(__name__)


if __name__ == "__main__":
    configure_logging()
    settings = get_settings()
    LOGGER.info("Starting document ingestion from %s", settings.docs_path)

    try:
        stats = build_indices()
        LOGGER.info(
            "Ingestion completed successfully: %s documents, %s chunks, index at %s",
            stats["documents"],
            stats["chunks"],
            stats["index_path"],
        )
    except Exception:
        LOGGER.exception("Ingestion failed.")
        raise SystemExit(1)
