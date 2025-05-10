import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.traceback import install

# Create console for rich output
console = Console()

# Completely disable rich traceback
install(show_locals=False, suppress=[
    "botocore",
    "boto3",
    "urllib3",
    "rich",
    "__main__",
    "typer",
])

def setup_logging(level=logging.INFO):
    """Setup logging configuration with rich handler"""
    # Suppress boto3 credentials message
    logging.getLogger("botocore.credentials").setLevel(logging.ERROR)
    
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=False, show_path=False)]
    )
    return logging.getLogger("landing-zone")
