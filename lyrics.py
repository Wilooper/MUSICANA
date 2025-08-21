import subprocess
import time
import logging

logger = logging.getLogger(__name__)

def start_lyrica(folder_name="Lyrica", port=9999):
    """
    Start the Lyrica Flask server automatically.

    Args:
        folder_name (str): The folder where lyrica.py is located.
        port (int): Port where Lyrica runs (default 9999).

    Returns:
        subprocess.Popen: The process handle for Lyrica, or None on failure.
    """
    try:
        lyrica_process = subprocess.Popen(
            ["python3", "lyrica.py"],
            cwd=folder_name,   # "Lyrica" or "lyrica"
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.info(f"Lyrica server started on port {port}")
        time.sleep(3)  # give server time to boot
        return lyrica_process
    except Exception as e:
        logger.error(f"Failed to start Lyrica server: {e}")
        return None
