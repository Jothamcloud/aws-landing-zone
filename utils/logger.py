import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.traceback import install

# Install rich traceback handler
install(show_locals=True)

# Create console for rich output
console = Console()

def setup_logging(level=logging.INFO):
    """Setup logging configuration with rich handler"""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    return logging.getLogger("landing-zone")
