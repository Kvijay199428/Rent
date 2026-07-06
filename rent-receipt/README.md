# Rent Receipt Application

A modern, web-based rent receipt management system designed for landlords to easily manage tenants, generate receipts, and send automated notifications.

## Features

- **Tenant Management**: Keep track of tenant details, portal PINs, and active status.
- **Billing & Rent Generation**: Automatic calculation of rent, water, and electricity bills.
- **PDF Generation**: Create professional, printable PDF receipts automatically.
- **WhatsApp Integration**: Send rent receipts and notifications directly to tenants via WhatsApp using customizable, dynamic templates.
- **Tenant Portal**: A secure public-facing portal where tenants can scan a QR code and enter a secure PIN to view and download their receipts.
- **Excel Sync**: Import and export tenant data and receipt history directly via Excel spreadsheets for easy backups and bulk editing.
- **Customizable Appearance**: Supports Light, Dark, and System themes for the admin dashboard.
- **Secure Storage**: Persistent storage using SQLite for billing data, tenants, configurations, and encrypted administrative PIN vaults.

## Technology Stack

- **Backend**: Python, FastAPI
- **Frontend**: HTML5, Bootstrap 5, Jinja2 Templates, Vanilla JavaScript
- **Database**: SQLite
- **Deployment**: Docker, Docker Compose

## Deployment

Use the included `deploy.py` script to package the application into a ZIP file and push it to the server.

```bash
python deploy.py
```

To deploy and completely wipe all existing data (fresh install):
```bash
python deploy.py --clean
```

## Structure

- `app/` - Core application logic, API routers, database schemas, authentication, and HTML templates.
- `deploy.py` - Deployment automation script.
- `requirements.txt` - Python dependencies.
- `storage/` - (Generated on run) Persistent storage directory for the SQLite database (`rent.db`), config JSON files, Excel backups, and user uploads (e.g., landlord signatures).
