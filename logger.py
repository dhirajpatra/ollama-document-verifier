import logging # <--- ADD THIS LINE

# --- Configure Logging ---
# Create a logger object
logger = logging.getLogger(__name__)
# Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
logger.setLevel(logging.INFO) # Or logging.DEBUG for more verbose output

# Create a console handler
handler = logging.StreamHandler()
# Create a formatter and add it to the handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
# Add the handler to the logger
if not logger.handlers: # Prevent adding multiple handlers if script reloads
    logger.addHandler(handler)
# --- End Logging Configuration ---