import os

# Set the base storage directory. 
# Defaults to a local "storage" folder, but can be overridden by an environment variable.
STORAGE_DIR = os.environ.get("RENT_STORAGE_DIR", r"d:\VEGA\RENT\storage")

# Define organized subdirectories
CONFIG_DIR = os.path.join(STORAGE_DIR, "config")
DB_DIR = os.path.join(STORAGE_DIR, "database")
RECEIPTS_DIR = os.path.join(STORAGE_DIR, "receipts")
BACKUPS_DIR = os.path.join(STORAGE_DIR, "backups")
UPLOADS_DIR = os.path.join(STORAGE_DIR, "uploads")
KYC_DIR = os.path.join(UPLOADS_DIR, "kyc")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

def ensure_storage_dirs():
    """Creates all necessary directories if they don't exist."""
    directories = [CONFIG_DIR, DB_DIR, RECEIPTS_DIR, BACKUPS_DIR, UPLOADS_DIR, KYC_DIR]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
