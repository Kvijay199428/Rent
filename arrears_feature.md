This is an excellent architectural upgrade. Using **Excel (`.xlsx`)** with multiple sheets (relational structure) drastically improves data integrity, eliminates redundancy, and provides a much cleaner experience for manual editing.

To support this relational Excel structure, you will need the standard python package for Excel files.
Before proceeding, please run this in your terminal to install it:

```bash
pip install openpyxl

```

*(If you are using Docker, add `openpyxl==3.1.2` to your `requirements.txt` and rebuild).*

Here is the complete implementation for the **Excel Relational Import/Export Engine**, featuring the 20/80 split UI, nested file-to-tenant lists, and receipt previews.

### 1. Backend: API Endpoints (`app/main.py`)

Replace the previous `UNIFIED IMPORT & EXPORT ENGINE` block (at the bottom of `app/main.py`) with this updated Excel-powered engine.

```python
# ==========================================
# EXCEL IMPORT & EXPORT ENGINE (RELATIONAL)
# ==========================================
import json
import openpyxl
from openpyxl.styles import Font, PatternFill

PROFILE_HEADERS = [
    "Tenant_ID", "Tenant_Name", "Phone", "Email", "Company", "Address", "Room", 
    "Meter_ID", "PIN", "Rent", "Water", "Electricity_Rate", "Additional_Person_Rate", 
    "Tank_Water", "Status"
]

RECEIPT_HEADERS = [
    "Bill_No", "Tenant_ID", "Month", "Date", "Previous", "Current", "Units", "Rent", 
    "Water", "Electricity", "Additional", "Tank_Water", "Maintenance", "Arrears", 
    "Amount_Received", "Total", "Payment_Status", "Receipt_Status"
]

@app.get("/api/sync/template")
async def download_excel_template():
    wb = openpyxl.Workbook()
    
    # 1. Tenant Profile Sheet
    ws_profile = wb.active
    ws_profile.title = "Tenant_Profile"
    ws_profile.append(PROFILE_HEADERS)
    
    # 2. Rent Receipts Sheet
    ws_receipts = wb.create_sheet("Rent_Receipts")
    ws_receipts.append(RECEIPT_HEADERS)
    
    # Style Headers
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    for ws in [ws_profile, ws_receipts]:
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            
    # Sample Data
    ws_profile.append(["T001", "John Doe", "9876543210", "john@gmail.com", "ABC Pvt Ltd", "Delhi", "A101", "MTR001", "1234", 15000, 500, 8.5, 1000, 300, "Active"])
    ws_profile.append(["T002", "Alice Smith", "9988776655", "alice@gmail.com", "XYZ Ltd", "Noida", "B202", "MTR002", "4321", 18000, 600, 9.0, 1200, 400, "Active"])
    
    ws_receipts.append(["T1-001", "T001", "January 2026", "01 Jan 2026", 120, 150, 30, 15000, 500, 255, 1000, 300, 0, 0, 17055, 17055, "PAID", "ACTIVE"])
    ws_receipts.append(["T2-001", "T002", "January 2026", "01 Jan 2026", 80, 110, 30, 18000, 600, 270, 0, 400, 0, 0, 19270, 19270, "PAID", "ACTIVE"])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    
    response = StreamingResponse(iter([stream.getvalue()]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response.headers["Content-Disposition"] = 'attachment; filename="Rent_Data_Template.xlsx"'
    return response

@app.get("/api/sync/export/{format}")
async def export_excel_data(format: str):
    tenants = load_tenants()
    receipts = get_all_receipts()
    
    wb = openpyxl.Workbook()
    ws_profile = wb.active
    ws_profile.title = "Tenant_Profile"
    ws_profile.append(PROFILE_HEADERS)
    
    ws_receipts = wb.create_sheet("Rent_Receipts")
    ws_receipts.append(RECEIPT_HEADERS)
    
    # Style Headers
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    for ws in [ws_profile, ws_receipts]:
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill

    tenant_id_map = {}
    
    for t in tenants:
        t_id_str = f"T{str(t.id).zfill(3)}"
        tenant_id_map[t.name] = t_id_str
        
        ws_profile.append([
            t_id_str, t.name, str(t.phone), getattr(t, 'email', ''), getattr(t, 'company', ''), 
            getattr(t, 'address', ''), getattr(t, 'room_number', ''), getattr(t, 'meter_id', ''), 
            getattr(t, 'tenant_pin', '1234'), float(t.rent), float(t.water), float(t.electricity_rate), 
            float(t.additional_person_charge), float(getattr(t, 'default_tank_water_charge', 0.0)), t.status
        ])

    for r in receipts:
        t_name = r.get("Tenant", "")
        t_id_str = tenant_id_map.get(t_name, "UNKNOWN")
        
        ws_receipts.append([
            r.get("Bill", ""), t_id_str, r.get("Month", ""), r.get("Date", ""), float(r.get("Previous", 0)), 
            float(r.get("Current", 0)), float(r.get("Units", 0)), float(r.get("Rent", 0)), float(r.get("Water", 0)), 
            float(r.get("Electricity", 0)), float(r.get("Additional", 0)), float(r.get("Tank_Water", 0)), 
            float(r.get("Maintenance_Charge", 0)), float(r.get("Previous_Arrears", 0)), float(r.get("Amount_Received", 0)), 
            float(r.get("Total", 0)), r.get("Payment_Status", "PENDING"), r.get("Status", "ACTIVE")
        ])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    
    date_str = datetime.now().strftime('%Y%m%d')
    
    if format == "xlsx":
        filename = f"Rent_Data_Export_{date_str}.xlsx"
        response = StreamingResponse(iter([stream.getvalue()]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
        
    elif format == "zip":
        zip_filename = f"Rent_Data_Archive_{date_str}.zip"
        zip_path = os.path.join(BACKUPS_DIR, zip_filename)
        os.makedirs(BACKUPS_DIR, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr(f"Rent_Data_Export_{date_str}.xlsx", stream.getvalue())
            
        response = FileResponse(zip_path, media_type="application/zip", filename=zip_filename)
        response.headers["Content-Disposition"] = f'attachment; filename="{zip_filename}"'
        return response

def parse_excel_bytes(file_bytes, filename):
    wb = openpyxl.load_workbook(filename=io.BytesIO(file_bytes), data_only=True)
    if "Tenant_Profile" not in wb.sheetnames or "Rent_Receipts" not in wb.sheetnames:
        raise ValueError(f"File {filename} is missing required sheets 'Tenant_Profile' and/or 'Rent_Receipts'.")
        
    ws_profile = wb["Tenant_Profile"]
    ws_receipts = wb["Rent_Receipts"]
    
    p_headers = [str(cell.value).strip() if cell.value else f"Col{i}" for i, cell in enumerate(ws_profile[1])]
    r_headers = [str(cell.value).strip() if cell.value else f"Col{i}" for i, cell in enumerate(ws_receipts[1])]
    
    tenants_dict = {}
    
    for row in ws_profile.iter_rows(min_row=2, values_only=True):
        if not row[0]: continue # Skip empty rows
        row_dict = {p_headers[i]: (str(val).strip() if val is not None else "") for i, val in enumerate(row)}
        t_id = row_dict.get("Tenant_ID", "")
        if t_id:
            tenants_dict[t_id] = {
                "profile": row_dict,
                "receipts": []
            }
            
    for row in ws_receipts.iter_rows(min_row=2, values_only=True):
        if not row[0]: continue
        row_dict = {r_headers[i]: (str(val).strip() if val is not None else "") for i, val in enumerate(row)}
        t_id = row_dict.get("Tenant_ID", "")
        if t_id in tenants_dict:
            tenants_dict[t_id]["receipts"].append(row_dict)
            
    return tenants_dict

@app.post("/api/sync/import/preview")
async def import_preview_data(file: UploadFile = File(...)):
    preview_data = {}
    content = await file.read()

    try:
        if file.filename.endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                for zip_info in z.infolist():
                    if zip_info.filename.endswith('.xlsx'):
                        with z.open(zip_info) as f:
                            preview_data[zip_info.filename] = parse_excel_bytes(f.read(), zip_info.filename)
        elif file.filename.endswith('.xlsx'):
            preview_data[file.filename] = parse_excel_bytes(content, file.filename)
        else:
            raise HTTPException(status_code=400, detail="Only .xlsx or .zip files are supported.")
            
        return {"status": "success", "files": preview_data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/sync/import/execute")
async def import_execute_data(
    file: UploadFile = File(...), 
    selected_targets: str = Form(...), # Format: ["filename::T001", "filename::T002"]
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    selected_list = json.loads(selected_targets)
    if not selected_list:
        raise HTTPException(status_code=400, detail="No tenants selected for import.")
        
    content = await file.read()
    sys_tenants = load_tenants()
    sys_receipts = get_all_receipts()
    
    background_tasks.add_task(create_full_backup, tag="pre_import_excel")

    def execute_import_for_file(file_bytes, filename):
        parsed_data = parse_excel_bytes(file_bytes, filename)
        
        for t_id, t_data in parsed_data.items():
            target_key = f"{filename}::{t_id}"
            if target_key not in selected_list:
                continue # User didn't check this tenant
                
            p = t_data["profile"]
            t_name = p.get("Tenant_Name", "").strip()
            
            # 1. Sync Profile
            t = next((x for x in sys_tenants if x.name.lower() == t_name.lower()), None)
            is_new = False
            if not t:
                t = Tenant(name=t_name, phone=p.get("Phone", ""), rent=0.0, water=0.0, electricity_rate=0.0)
                is_new = True
                
            t.phone = p.get("Phone", t.phone)
            t.email = p.get("Email", getattr(t, 'email', ''))
            t.company = p.get("Company", getattr(t, 'company', ''))
            t.address = p.get("Address", getattr(t, 'address', ''))
            t.room_number = p.get("Room", getattr(t, 'room_number', ''))
            t.meter_id = p.get("Meter_ID", getattr(t, 'meter_id', ''))
            t.tenant_pin = p.get("PIN", getattr(t, 'tenant_pin', '1234'))
            t.rent = float(p.get("Rent", t.rent) or 0.0)
            t.water = float(p.get("Water", t.water) or 0.0)
            t.electricity_rate = float(p.get("Electricity_Rate", t.electricity_rate) or 0.0)
            t.additional_person_charge = float(p.get("Additional_Person_Rate", getattr(t, 'additional_person_charge', 0.0)) or 0.0)
            t.default_tank_water_charge = float(p.get("Tank_Water", getattr(t, 'default_tank_water_charge', 0.0)) or 0.0)
            t.status = p.get("Status", getattr(t, 'status', 'Active'))
            
            if is_new:
                add_tenant(t)
                sys_tenants.append(t)
            else:
                update_tenant(t)
                
            # 2. Sync Receipts
            for r in t_data["receipts"]:
                bill_no = r.get("Bill_No", "").strip()
                if not bill_no: continue
                
                sys_r = next((x for x in sys_receipts if x.get("Bill") == bill_no), None)
                data = {
                    "Bill": bill_no, "Date": r.get("Date", ""), "Month": r.get("Month", ""),
                    "Tenant": t_name, "Previous": r.get("Previous", 0), "Current": r.get("Current", 0),
                    "Units": r.get("Units", 0), "Rent": r.get("Rent", 0), "Additional": r.get("Additional", 0), 
                    "Water": r.get("Water", 0), "Tank_Water": r.get("Tank_Water", 0), "Electricity": r.get("Electricity", 0),
                    "Maintenance_Charge": r.get("Maintenance", 0), "Maintenance_Desc": r.get("Maintenance_Desc", ""),
                    "Previous_Arrears": r.get("Arrears", 0), "Amount_Received": r.get("Amount_Received", 0), 
                    "Total": r.get("Total", 0), "Payment_Status": r.get("Payment_Status", "PENDING"),
                    "Status": r.get("Receipt_Status", "ACTIVE"), "Receipt_Version": 8, "Generated_By": "Import"
                }
                if sys_r:
                    sys_r.update(data)
                else:
                    sys_receipts.append(data)

    try:
        if file.filename.endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                for zip_info in z.infolist():
                    if zip_info.filename.endswith('.xlsx'):
                        with z.open(zip_info) as f:
                            execute_import_for_file(f.read(), zip_info.filename)
        elif file.filename.endswith('.xlsx'):
            execute_import_for_file(content, file.filename)
            
        from app.services.billing_service import save_all_receipts
        save_all_receipts(sys_receipts)
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

```

### 2. Frontend: Modals and UI (`app/templates/settings.html`)

Replace your Data Import/Export section with this exact 20/80 split layout.

```html
<div class="card shadow-sm border-0 mb-4 rounded-4">
    <div class="card-header bg-success bg-gradient text-white py-3 px-4 d-flex align-items-center rounded-top-4">
        <i class="bi bi-file-earmark-spreadsheet fs-5 me-3"></i>
        <h5 class="mb-0 fw-bold">Excel Import & Export (Relational)</h5>
    </div>
    <div class="card-body p-4">
        <p class="text-muted mb-4 fs-7">
            Manage your tenants and receipts using a highly organized Excel format (.xlsx). The workbook separates Tenant Profiles and Receipts into distinct sheets to prevent duplication and make editing easier.
        </p>

        <div class="row g-3">
            <div class="col-md-4">
                <a href="api/sync/template" class="btn btn-outline-success w-100 py-2 fw-bold text-start rounded-3 shadow-sm d-flex align-items-center justify-content-between">
                    <span><i class="bi bi-grid-3x3 me-2 text-success"></i> Blank Excel Template</span>
                    <i class="bi bi-download"></i>
                </a>
            </div>
            <div class="col-md-4">
                <a href="api/sync/export/xlsx" class="btn btn-outline-primary w-100 py-2 fw-bold text-start rounded-3 shadow-sm d-flex align-items-center justify-content-between">
                    <span><i class="bi bi-file-excel-fill me-2 text-primary"></i> Export to Excel (.xlsx)</span>
                    <i class="bi bi-box-arrow-up-right"></i>
                </a>
            </div>
            <div class="col-md-4">
                <a href="api/sync/export/zip" class="btn btn-outline-primary w-100 py-2 fw-bold text-start rounded-3 shadow-sm d-flex align-items-center justify-content-between">
                    <span><i class="bi bi-file-zip-fill me-2 text-primary"></i> Export as ZIP Archive</span>
                    <i class="bi bi-box-arrow-up-right"></i>
                </a>
            </div>
        </div>
        
        <hr class="my-4 text-muted">
        
        <div class="d-flex align-items-center justify-content-between bg-primary-subtle p-3 rounded-3 border border-primary">
            <div>
                <h6 class="fw-bold text-primary mb-1">Import Excel Data</h6>
                <div class="fs-8 text-muted">Select an .xlsx file or a .zip containing multiple .xlsx files.</div>
            </div>
            <div>
                <input type="file" id="importExcelFile" accept=".xlsx, .zip" class="d-none" onchange="handleExcelImport(this)">
                <button onclick="document.getElementById('importExcelFile').click()" class="btn btn-primary fw-bold shadow-sm rounded-pill px-4">
                    <i class="bi bi-cloud-arrow-up-fill me-2"></i> Select File to Import
                </button>
            </div>
        </div>
    </div>
</div>

<div class="modal fade" id="importPreviewModal" tabindex="-1" data-bs-backdrop="static">
    <div class="modal-dialog modal-dialog-centered" style="max-width: 95vw; width: 95vw;">
        <div class="modal-content border-0 shadow-lg rounded-4 overflow-hidden" style="height: 85vh;">
            <div class="modal-header bg-dark text-white border-bottom-0 py-2">
                <h5 class="modal-title fw-bold fs-6">
                    <i class="bi bi-file-excel me-2 text-success"></i> Data Import Preview
                </h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            
            <div class="modal-body p-0 d-flex flex-row h-100" style="overflow: hidden;">
                
                <div class="border-end bg-body-tertiary d-flex flex-column h-100" style="width: 20%; min-width: 250px;">
                    <div class="p-2 border-bottom bg-light d-flex justify-content-between align-items-center shadow-sm z-1">
                        <h6 class="fw-bold mb-0 text-secondary fs-7 px-2">Select Tenants</h6>
                    </div>
                    
                    <div class="overflow-auto flex-grow-1 p-2" id="importTreeList">
                        </div>
                </div>

                <div class="bg-body d-flex flex-column h-100" style="width: 80%;">
                    
                    <div class="p-3 border-bottom bg-primary-subtle shadow-sm z-1 d-none" id="previewProfileCard">
                        <div class="row align-items-center">
                            <div class="col-md-4">
                                <h5 class="fw-bold text-primary mb-0" id="prev_t_name">Tenant Name</h5>
                                <div class="fs-7 text-muted" id="prev_t_id">T001</div>
                            </div>
                            <div class="col-md-8">
                                <div class="row fs-7 text-dark fw-semibold">
                                    <div class="col-4"><i class="bi bi-telephone me-1"></i> <span id="prev_t_phone"></span></div>
                                    <div class="col-4"><i class="bi bi-building me-1"></i> <span id="prev_t_company"></span></div>
                                    <div class="col-4">Rent: ₹<span id="prev_t_rent"></span></div>
                                    <div class="col-4"><i class="bi bi-lightning-charge me-1"></i> ₹<span id="prev_t_rate"></span>/unit</div>
                                    <div class="col-4">Water: ₹<span id="prev_t_water"></span></div>
                                    <div class="col-4"><span class="badge bg-success" id="prev_t_status"></span></div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="px-3 py-2 border-bottom bg-light d-flex justify-content-between align-items-center" id="previewHeaderBar">
                        <h6 class="fw-bold mb-0 text-secondary" id="previewTableName">Select a tenant on the left to preview receipts</h6>
                        <span class="badge bg-secondary" id="previewTableRowsCount">0 Receipts</span>
                    </div>
                    
                    <div class="table-responsive flex-grow-1 p-0 m-0 bg-white" style="overflow-y: auto;">
                        <table class="table table-hover table-sm fs-8 m-0 border-top-0" id="previewTable">
                            <thead class="table-dark sticky-top" id="previewTableHead"></thead>
                            <tbody id="previewTableBody">
                                <tr><td colspan="100%" class="text-center text-muted py-5 mt-5"><i class="bi bi-inboxes d-block fs-1 mb-3 opacity-50"></i>No preview available</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>

            </div>
            
            <div class="modal-footer bg-light border-top-0 py-2">
                <button type="button" class="btn btn-outline-secondary fw-bold rounded-pill px-4" data-bs-dismiss="modal">Cancel</button>
                <button type="button" class="btn btn-success fw-bold rounded-pill px-5 shadow-sm" id="btnExecuteImport" onclick="executeExcelImport()">
                    <i class="bi bi-cloud-check-fill me-2"></i> Import Selected Tenants
                </button>
            </div>
        </div>
    </div>
</div>

```

### 3. Frontend: JS Logic (Add to bottom of `settings.html` or `main.js`)

This parses the nested Dictionary generated by the API, builds the visual tree mapping, handles selections, and renders the 80% view.

```javascript
let importExcelCache = {};
let currentExcelFileObj = null;

async function handleExcelImport(inputEl) {
    if (!inputEl.files || inputEl.files.length === 0) return;
    
    currentExcelFileObj = inputEl.files[0];
    const formData = new FormData();
    formData.append("file", currentExcelFileObj);
    
    if (typeof showLoadingOverlay === 'function') showLoadingOverlay("Parsing Excel structure...");
    
    try {
        const res = await fetch("api/sync/import/preview", { method: "POST", body: formData });
        if (typeof hideLoadingOverlay === 'function') hideLoadingOverlay();
        
        if (!res.ok) {
            const data = await res.json();
            showError("Parse Error", data.detail || "Unable to read file contents.");
            inputEl.value = '';
            return;
        }
        
        const data = await res.json();
        importExcelCache = data.files; // Format: { "Rent_Data.xlsx": { "T001": { profile: {}, receipts: [] } } }
        
        renderImportTreeList();
        
        // Hide right side preview initially
        document.getElementById('previewProfileCard').classList.add('d-none');
        document.getElementById('previewTableBody').innerHTML = '<tr><td colspan="100%" class="text-center text-muted py-5 mt-5"><i class="bi bi-inboxes d-block fs-1 mb-3 opacity-50"></i>Select a tenant on the left to preview data.</td></tr>';
        document.getElementById('previewTableHead').innerHTML = '';
        
        const modal = new bootstrap.Modal(document.getElementById('importPreviewModal'));
        modal.show();
        
    } catch(e) {
        if (typeof hideLoadingOverlay === 'function') hideLoadingOverlay();
        showError("Network Error", "Could not reach the server.");
    }
    inputEl.value = ''; // reset input
}

function renderImportTreeList() {
    const listContainer = document.getElementById('importTreeList');
    listContainer.innerHTML = '';
    
    let isFirst = true;

    // Loop over files (Will be 1 if just .xlsx, multiple if .zip)
    for (const [filename, tenantsObj] of Object.entries(importExcelCache)) {
        
        // File Header
        const fileGroup = document.createElement('div');
        fileGroup.className = "mb-3 border rounded-3 bg-white overflow-hidden shadow-sm";
        
        const fileHeader = document.createElement('div');
        fileHeader.className = "bg-body-tertiary p-2 border-bottom d-flex align-items-center justify-content-between";
        fileHeader.innerHTML = `
            <div class="fw-bold fs-7 text-dark text-truncate" title="${filename}">
                <i class="bi bi-file-earmark-excel-fill text-success me-1"></i> ${filename}
            </div>
            <input type="checkbox" class="form-check-input file-group-checkbox" checked onchange="toggleFileGroup(this, '${filename.replace(/[^a-zA-Z0-9]/g, '_')}')" title="Select All in File">
        `;
        fileGroup.appendChild(fileHeader);
        
        const tenantList = document.createElement('div');
        tenantList.className = "list-group list-group-flush";
        tenantList.id = `group_${filename.replace(/[^a-zA-Z0-9]/g, '_')}`;
        
        // Loop over Tenants inside this file
        for (const [tenantId, data] of Object.entries(tenantsObj)) {
            const tName = data.profile.Tenant_Name || "Unknown Tenant";
            const receiptCount = data.receipts.length;
            
            const tItem = document.createElement('div');
            tItem.className = `list-group-item list-group-item-action d-flex align-items-center gap-2 py-2 px-3 border-bottom-0 tenant-select-item ${isFirst ? 'bg-primary-subtle' : ''}`;
            tItem.style.cursor = "pointer";
            
            // Handle clicking the row to preview
            tItem.onclick = (e) => {
                if(e.target.type === 'checkbox') return;
                
                document.querySelectorAll('.tenant-select-item').forEach(el => el.classList.remove('bg-primary-subtle'));
                tItem.classList.add('bg-primary-subtle');
                
                renderRightSidePreview(filename, tenantId);
            };
            
            tItem.innerHTML = `
                <input class="form-check-input import-tenant-checkbox" type="checkbox" value="${filename}::${tenantId}" checked>
                <div class="d-flex flex-column w-100" style="overflow: hidden;">
                    <div class="fw-bold fs-7 text-truncate" title="${tName}">${tName}</div>
                    <div class="d-flex justify-content-between">
                        <span class="fs-8 text-muted">${tenantId}</span>
                        <span class="fs-8 badge bg-secondary rounded-pill">${receiptCount} Bills</span>
                    </div>
                </div>
            `;
            
            tenantList.appendChild(tItem);
            
            if (isFirst) {
                renderRightSidePreview(filename, tenantId);
                isFirst = false;
            }
        }
        
        fileGroup.appendChild(tenantList);
        listContainer.appendChild(fileGroup);
    }
}

function toggleFileGroup(checkbox, groupId) {
    const group = document.getElementById(`group_${groupId}`);
    if (group) {
        group.querySelectorAll('.import-tenant-checkbox').forEach(cb => cb.checked = checkbox.checked);
    }
}

function renderRightSidePreview(filename, tenantId) {
    const data = importExcelCache[filename][tenantId];
    
    // 1. Render Profile Summary Card
    document.getElementById('previewProfileCard').classList.remove('d-none');
    
    const p = data.profile;
    document.getElementById('prev_t_name').innerText = p.Tenant_Name || "-";
    document.getElementById('prev_t_id').innerText = tenantId;
    document.getElementById('prev_t_phone').innerText = p.Phone || "-";
    document.getElementById('prev_t_company').innerText = p.Company || "-";
    document.getElementById('prev_t_rent').innerText = p.Rent || "0";
    document.getElementById('prev_t_rate').innerText = p.Electricity_Rate || "0";
    document.getElementById('prev_t_water').innerText = p.Water || "0";
    document.getElementById('prev_t_status').innerText = p.Status || "Active";
    
    // 2. Render Receipts Table
    document.getElementById('previewTableName').innerText = `Receipt History`;
    document.getElementById('previewTableRowsCount').innerText = `${data.receipts.length} Receipts`;
    
    const thead = document.getElementById('previewTableHead');
    const tbody = document.getElementById('previewTableBody');
    
    if (data.receipts.length === 0) {
        thead.innerHTML = "";
        tbody.innerHTML = `<tr><td colspan="100%" class="text-center text-muted py-5"><i class="bi bi-inbox d-block fs-1 mb-2 opacity-50"></i>No receipts found for this tenant.</td></tr>`;
        return;
    }
    
    // Extract headers from first receipt object keys dynamically
    const headers = Object.keys(data.receipts[0]);
    
    let trHead = '<tr>';
    headers.forEach(h => { trHead += `<th class="text-nowrap">${h}</th>`; });
    trHead += '</tr>';
    thead.innerHTML = trHead;
    
    let trBody = '';
    data.receipts.forEach(row => {
        trBody += '<tr>';
        headers.forEach(h => {
            const val = row[h] || '-';
            
            // Color code statuses visually for preview
            let styledVal = val;
            if (h === 'Payment_Status') {
                styledVal = val === 'PAID' ? `<span class="text-success fw-bold">${val}</span>` : `<span class="text-danger fw-bold">${val}</span>`;
            }
            
            trBody += `<td class="text-nowrap">${styledVal}</td>`;
        });
        trBody += '</tr>';
    });
    tbody.innerHTML = trBody;
}

async function executeExcelImport() {
    const checkboxes = document.querySelectorAll('.import-tenant-checkbox:checked');
    const selectedTargets = Array.from(checkboxes).map(cb => cb.value); // ["RentData.xlsx::T001", ...]
    
    if (selectedTargets.length === 0) {
        showError("Selection Required", "Please check at least one tenant from the list on the left to import.");
        return;
    }
    
    const btn = document.getElementById('btnExecuteImport');
    const originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Importing...';
    
    const formData = new FormData();
    formData.append("file", currentExcelFileObj);
    formData.append("selected_targets", JSON.stringify(selectedTargets));
    
    try {
        const res = await fetch("api/sync/import/execute", { method: "POST", body: formData });
        
        btn.disabled = false;
        btn.innerHTML = originalHtml;
        
        if (res.ok) {
            bootstrap.Modal.getInstance(document.getElementById('importPreviewModal')).hide();
            Swal.fire({
                icon: 'success',
                title: 'Excel Data Synced',
                text: 'Your relational tenant profiles and receipts have been successfully merged into the system.',
                confirmButtonColor: '#198754'
            }).then(() => {
                window.location.reload();
            });
        } else {
            const errData = await res.json();
            showError("Import Failed", errData.detail || "An error occurred while merging Excel data.");
        }
        
    } catch(e) {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
        showError("Network Error", "Could not reach the server.");
    }
}

```
This is a perfect architectural decision. Maintaining a **Single Source of Truth** prevents data fragmentation and stops your server storage from filling up with obsolete, downloaded, or uploaded Excel files.

To achieve this, we need to ensure that our operations are **100% in-memory (RAM-based)**:

1. **For Imports:** The file bytes are parsed instantly from the incoming request buffer (`io.BytesIO`) without ever being saved to the `UPLOADS_DIR`. *(Our previous import logic already does this natively!)*
2. **For Exports:** The Excel and ZIP files are generated in an active memory buffer (`io.BytesIO`) and streamed directly to the browser via FastAPI's `StreamingResponse` without ever touching the `BACKUPS_DIR` or disk.

Here is the updated backend logic.

### 1. Update Backend API (`app/main.py`)

Replace the `export_excel_data` endpoint in your `app/main.py` with this updated code. We are removing `os.makedirs`, `BACKUPS_DIR`, and `FileResponse`, and replacing them with purely RAM-buffered streams.

```python
# File: app/main.py (Replace the export_excel_data function)

@app.get("/api/sync/export/{format}")
async def export_excel_data(format: str):
    tenants = load_tenants()
    receipts = get_all_receipts()
    
    # 1. Generate Excel Workbook in Memory
    wb = openpyxl.Workbook()
    ws_profile = wb.active
    ws_profile.title = "Tenant_Profile"
    ws_profile.append(PROFILE_HEADERS)
    
    ws_receipts = wb.create_sheet("Rent_Receipts")
    ws_receipts.append(RECEIPT_HEADERS)
    
    # Style Headers
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    for ws in [ws_profile, ws_receipts]:
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill

    # Populate Data
    tenant_id_map = {}
    for t in tenants:
        t_id_str = f"T{str(t.id).zfill(3)}"
        tenant_id_map[t.name] = t_id_str
        
        ws_profile.append([
            t_id_str, t.name, str(t.phone), getattr(t, 'email', ''), getattr(t, 'company', ''), 
            getattr(t, 'address', ''), getattr(t, 'room_number', ''), getattr(t, 'meter_id', ''), 
            getattr(t, 'tenant_pin', '1234'), float(t.rent), float(t.water), float(t.electricity_rate), 
            float(t.additional_person_charge), float(getattr(t, 'default_tank_water_charge', 0.0)), t.status
        ])

    for r in receipts:
        t_name = r.get("Tenant", "")
        t_id_str = tenant_id_map.get(t_name, "UNKNOWN")
        
        ws_receipts.append([
            r.get("Bill", ""), t_id_str, r.get("Month", ""), r.get("Date", ""), float(r.get("Previous", 0)), 
            float(r.get("Current", 0)), float(r.get("Units", 0)), float(r.get("Rent", 0)), float(r.get("Water", 0)), 
            float(r.get("Electricity", 0)), float(r.get("Additional", 0)), float(r.get("Tank_Water", 0)), 
            float(r.get("Maintenance_Charge", 0)), float(r.get("Previous_Arrears", 0)), float(r.get("Amount_Received", 0)), 
            float(r.get("Total", 0)), r.get("Payment_Status", "PENDING"), r.get("Status", "ACTIVE")
        ])

    # 2. Save Workbook strictly to an In-Memory Bytes Buffer (NO DISK I/O)
    excel_stream = io.BytesIO()
    wb.save(excel_stream)
    excel_stream.seek(0)
    
    date_str = datetime.now().strftime('%Y%m%d')
    
    # 3. Stream back to the User directly
    if format == "xlsx":
        filename = f"Rent_Data_Export_{date_str}.xlsx"
        response = StreamingResponse(
            iter([excel_stream.getvalue()]), 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
        
    elif format == "zip":
        # Create a ZIP file entirely in RAM
        zip_stream = io.BytesIO()
        with zipfile.ZipFile(zip_stream, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Write the in-memory Excel file into the in-memory ZIP file
            zipf.writestr(f"Rent_Data_Export_{date_str}.xlsx", excel_stream.getvalue())
            
        zip_stream.seek(0)
        zip_filename = f"Rent_Data_Archive_{date_str}.zip"
        
        response = StreamingResponse(
            iter([zip_stream.getvalue()]), 
            media_type="application/zip"
        )
        response.headers["Content-Disposition"] = f'attachment; filename="{zip_filename}"'
        return response

```

### 2. Why the Import Endpoints are Already "Disk-Free"

You don't need to change the `import_preview_data` or `import_execute_data` functions we implemented in the previous step because they were natively written to bypass the disk.

If you look closely at how the file is retrieved:

```python
content = await file.read()  # <-- Reads the upload directly into RAM as a raw byte string

```

And how it parses ZIPs or Excel files:

```python
with zipfile.ZipFile(io.BytesIO(content)) as z:
    # Extracts bytes directly from RAM

```

```python
wb = openpyxl.load_workbook(filename=io.BytesIO(file_bytes), data_only=True)
# Loads workbook strictly from RAM

```

Because of this `io.BytesIO()` implementation, the moment the user imports the file and the function finishes executing, **Python's garbage collector automatically deletes the file from memory**. It never creates an `.xlsx` file on your server's hard drive, fulfilling your goal of having one single source of truth (your primary CSV/JSON databases).
This is a fantastic UX improvement. When dealing with file parsing and data generation, preventing accidental double-clicks and giving the user visual feedback is essential for maintaining data integrity.

We will achieve this by creating a **Frosted-Glass Fullscreen Overlay** that intercepts all clicks, blurs the background, and shows a data-sync animation. We will also switch your Export links to use JavaScript `fetch()` so we can keep the overlay active exactly until the file is fully ready for download.

Here are the updates to make this happen:

### 1. The Blocker & Animation CSS (Add to `app/static/css/style.css` or `<style>` in `base.html`)

This CSS creates a high-z-index overlay with a blur effect (`backdrop-filter`) and a neat animated bouncing loader.

```css
/* ==========================================
   GLOBAL LOADING & SYNC OVERLAY
   ========================================== */
#globalSyncOverlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    z-index: 99999; /* Stays above modals */
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    opacity: 0;
    visibility: hidden;
    transition: opacity 0.3s ease, visibility 0.3s ease;
    cursor: wait;
}

#globalSyncOverlay.active {
    opacity: 1;
    visibility: visible;
}

/* Data Sync Animation */
.sync-spinner {
    width: 60px;
    height: 60px;
    position: relative;
    animation: sync-spin 2s infinite linear;
    margin-bottom: 20px;
}
.sync-spinner .dot {
    width: 100%;
    height: 100%;
    position: absolute;
    left: 0;
    top: 0;
}
.sync-spinner .dot::before {
    content: '';
    display: block;
    width: 25%;
    height: 25%;
    background-color: #ffffff;
    border-radius: 100%;
    animation: sync-bounce 2s infinite ease-in-out both;
}
.sync-spinner .dot:nth-child(1) { transform: rotate(0deg); }
.sync-spinner .dot:nth-child(2) { transform: rotate(90deg); }
.sync-spinner .dot:nth-child(3) { transform: rotate(180deg); }
.sync-spinner .dot:nth-child(4) { transform: rotate(270deg); }

.sync-spinner .dot:nth-child(1)::before { animation-delay: -1.1s; background-color: #0d6efd;} /* Primary */
.sync-spinner .dot:nth-child(2)::before { animation-delay: -1.0s; background-color: #198754;} /* Success */
.sync-spinner .dot:nth-child(3)::before { animation-delay: -0.9s; background-color: #ffc107;} /* Warning */
.sync-spinner .dot:nth-child(4)::before { animation-delay: -0.8s; background-color: #dc3545;} /* Danger */

@keyframes sync-spin { 100% { transform: rotate(360deg); } }
@keyframes sync-bounce {
    0%, 100% { transform: scale(0.0); } 
    50% { transform: scale(1.0); }
}

.sync-text {
    color: white;
    font-weight: 600;
    font-size: 1.2rem;
    letter-spacing: 1px;
    text-shadow: 0 2px 4px rgba(0,0,0,0.5);
}

```

### 2. The Overlay Markup (Add to `app/templates/base.html`)

Add this HTML block right before the closing `</body>` tag in your `base.html` so it's available on every page.

```html
<div id="globalSyncOverlay">
    <div class="sync-spinner">
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
    </div>
    <div class="sync-text" id="syncOverlayText">Processing Data...</div>
</div>

```

### 3. JavaScript Logic for Overlay & Export (`app/static/js/main.js` or `settings.html`)

Update your JavaScript to control the overlay and handle the export buttons dynamically.

```javascript
// --- Global Sync Overlay Controls ---
function showSyncOverlay(message = "Processing Data...") {
    const overlay = document.getElementById('globalSyncOverlay');
    const textEl = document.getElementById('syncOverlayText');
    if (overlay) {
        if(textEl) textEl.innerText = message;
        overlay.classList.add('active');
        // Prevent keyboard interactions while loading
        document.activeElement.blur(); 
    }
}

function hideSyncOverlay() {
    const overlay = document.getElementById('globalSyncOverlay');
    if (overlay) overlay.classList.remove('active');
}

// Map the old loading functions to the new Sync overlay for backwards compatibility 
window.showLoadingOverlay = showSyncOverlay;
window.hideLoadingOverlay = hideSyncOverlay;


// --- Secure Export Wrapper ---
async function executeExport(format) {
    showSyncOverlay(`Generating ${format.toUpperCase()} Backup...`);
    
    try {
        const response = await fetch(`api/sync/export/${format}`);
        if (!response.ok) throw new Error("Failed to generate export file.");
        
        // Extract filename from headers if possible
        const disposition = response.headers.get('Content-Disposition');
        let filename = `Rent_Data_Export.${format}`;
        if (disposition && disposition.includes('filename="')) {
            filename = disposition.split('filename="')[1].split('"')[0];
        }

        const blob = await response.blob();
        const blobUrl = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = blobUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        
        window.URL.revokeObjectURL(blobUrl);
        a.remove();
        
        setTimeout(() => {
            hideSyncOverlay();
            if (typeof showToast === 'function') showToast('success', `${format.toUpperCase()} Export completed successfully!`);
        }, 500); // 500ms delay to make the transition feel smooth

    } catch (e) {
        hideSyncOverlay();
        if (typeof showError === 'function') {
            showError("Export Failed", e.message);
        } else {
            alert("Failed to export data.");
        }
    }
}

```

### 4. Update the Export Buttons (`app/templates/settings.html`)

Since standard `<a href="...">` links bypass JavaScript loading controls, you must change the Export links in `settings.html` to buttons that trigger our new `executeExport()` function.

Replace the `` top section buttons with this:

```html
<div class="row g-3">
    <div class="col-md-4">
        <button onclick="executeExport('template')" class="btn btn-outline-success w-100 py-2 fw-bold text-start rounded-3 shadow-sm d-flex align-items-center justify-content-between">
            <span><i class="bi bi-grid-3x3 me-2 text-success"></i> Blank Excel Template</span>
            <i class="bi bi-download"></i>
        </button>
    </div>
    <div class="col-md-4">
        <button onclick="executeExport('xlsx')" class="btn btn-outline-primary w-100 py-2 fw-bold text-start rounded-3 shadow-sm d-flex align-items-center justify-content-between">
            <span><i class="bi bi-file-excel-fill me-2 text-primary"></i> Export to Excel (.xlsx)</span>
            <i class="bi bi-box-arrow-up-right"></i>
        </button>
    </div>
    <div class="col-md-4">
        <button onclick="executeExport('zip')" class="btn btn-outline-primary w-100 py-2 fw-bold text-start rounded-3 shadow-sm d-flex align-items-center justify-content-between">
            <span><i class="bi bi-file-zip-fill me-2 text-primary"></i> Export as ZIP Archive</span>
            <i class="bi bi-box-arrow-up-right"></i>
        </button>
    </div>
</div>

```

### 5. Attach the animation to the Import logic

In your previously added `handleExcelImport` and `executeExcelImport` JS functions, ensure you use the new wording so the spinner shows the correct status:

Modify your `handleExcelImport()`:

```javascript
async function handleExcelImport(inputEl) {
    if (!inputEl.files || inputEl.files.length === 0) return;
    
    currentExcelFileObj = inputEl.files[0];
    const formData = new FormData();
    formData.append("file", currentExcelFileObj);
    
    // Call the new overlay
    showSyncOverlay("Parsing Excel structure...");
    
    try {
        const res = await fetch("api/sync/import/preview", { method: "POST", body: formData });
        hideSyncOverlay();
        // ... rest of code

```

Modify your `executeExcelImport()`:

```javascript
async function executeExcelImport() {
    // ... file checking code
    
    // Use the overlay to block the screen
    bootstrap.Modal.getInstance(document.getElementById('importPreviewModal')).hide(); // Hide the modal first
    showSyncOverlay("Importing & Syncing Data..."); 
    
    const formData = new FormData();
    formData.append("file", currentExcelFileObj);
    formData.append("selected_targets", JSON.stringify(selectedTargets));
    
    try {
        const res = await fetch("api/sync/import/execute", { method: "POST", body: formData });
        hideSyncOverlay();
        
        if (res.ok) {
            Swal.fire({ ...

```

### How this improves efficacy:

1. **Z-Index 99999:** The overlay sits physically above *everything* (modals, dropdowns, headers).
2. **Backdrop Filter:** Blurs out the tables and UI behind it, instantly indicating to the user that the system state is locked.
3. **Pointer-Events interception:** Because the `div` takes up `100vw` and `100vh`, the user's mouse physically cannot click any button beneath it until `hideSyncOverlay()` is called.
4. **RAM Tracking:** By wrapping the Export download in a `fetch()` blob promise, the browser knows exactly when the server is done processing the Excel file in RAM, allowing us to drop the loading screen at the exact moment the file hits the user's downloads folder.