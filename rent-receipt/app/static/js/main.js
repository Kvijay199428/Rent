// Main JS functionality (Theme, Sidebar, Setup)

document.addEventListener("DOMContentLoaded", () => {
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

    // Sidebar Mobile Drawer Toggle
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    const toggle = document.getElementById("menuToggle");
    const closeBtn = document.getElementById("sidebarCloseBtn");

    function closeSidebar(){
        if(sidebar) sidebar.classList.remove("open");
        if(overlay) overlay.classList.remove("show");
        document.body.classList.remove("sidebar-open");
    }

    if(toggle) {
        toggle.addEventListener("click", () => {
            sidebar.classList.toggle("open");
            overlay.classList.toggle("show");
            document.body.classList.toggle("sidebar-open");
        });
    }

    if(overlay) overlay.addEventListener("click", closeSidebar);
    if(closeBtn) closeBtn.addEventListener("click", closeSidebar);

    document.querySelectorAll(".sidebar a").forEach(link => {
        link.addEventListener("click", closeSidebar);
    });
});

// --- Smooth DOM Update Engine ---
async function smoothUpdate(selectors) {
    try {
        const res = await fetch(window.location.href);
        const htmlText = await res.text();
        const doc = new DOMParser().parseFromString(htmlText, 'text/html');
        
        selectors.forEach(selector => {
            const currentElements = document.querySelectorAll(selector);
            const newElements = doc.querySelectorAll(selector);
            
            // Replace the HTML of the target containers
            currentElements.forEach((el, index) => {
                if (newElements[index]) {
                    el.innerHTML = newElements[index].innerHTML;
                }
            });
        });
        
        // Re-trigger visual scripts if they exist on the page
        if (typeof calculateYearStats === 'function') calculateYearStats();
        if (typeof searchTenants === 'function') searchTenants();
    } catch(e) {
        console.error("Smooth update failed", e);
        window.location.reload(); // Safe fallback
    }
}

// Global UI Updater mapping
async function updateUI() {
    const path = window.location.pathname;
    if (path === '/') {
        await smoothUpdate(['.row-cols-1', '.table-responsive', '.d-md-none']); // Updates Dashboard Cards & Tables
    } else if (path.includes('/history')) {
        await smoothUpdate(['#historyAccordion']); // Updates History Accordion
    } else if (path.includes('/archive')) {
        await smoothUpdate(['#archiveAccordion', '.row.g-4.mb-4']); // Updates Archive Accordion & Stats
    } else if (path.includes('/tenants')) {
        await smoothUpdate(['#tenantsTable']); // Updates Tenants Table
    } else if (path.startsWith('/tenant/')) {
        await smoothUpdate(['.col-xl-4', '.col-xl-8']); // Updates Tenant Profile columns
    } else {
        window.location.reload();
    }
}

// --- Instant Theme Handler ---
async function setTheme(themeName) {
    try {
        const res = await fetch(window.APP.API + "/ui/theme", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ theme: themeName })
        });
        if (res.ok) {
            // Apply theme instantly without reloading
            const targetTheme = themeName === 'system' 
                ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') 
                : themeName;
            document.documentElement.setAttribute('data-bs-theme', targetTheme);
        }
    } catch (e) {
        showError("Theme Error", "Failed to switch theme.");
    }
}

// --- Smooth Payment Status Toggle with Arrears Logic ---
async function togglePaymentStatus(billNo, currentStatus, grandTotal = null) {
    const newStatus = currentStatus === 'PENDING' ? 'PAID' : 'PENDING';
    
    let amountReceived = null;
    
    if (newStatus === 'PAID') {
        const { value: amount } = await Swal.fire({
            title: 'Payment Received',
            text: 'Enter the exact amount paid by the tenant:',
            input: 'number',
            inputValue: grandTotal !== null ? grandTotal : '',
            inputPlaceholder: 'e.g. 15000',
            showCancelButton: true,
            confirmButtonColor: '#198754',
            confirmButtonText: 'Mark as Paid',
            inputValidator: (value) => {
                if (!value || isNaN(value) || Number(value) < 0) {
                    return 'Please enter a valid positive amount';
                }
            }
        });
        
        if (!amount) return; // User cancelled
        amountReceived = parseFloat(amount);
    }
    
    try {
        const response = await fetch(window.APP.API + `/bill/${billNo}/payment`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                payment_status: newStatus,
                amount_received: amountReceived
            })
        });
        
        if (response.ok) {
            showToast('success', `Bill #${billNo} marked as ${newStatus}!`);
            await updateUI();
        } else {
            showError('Error', 'Failed to update payment status');
        }
    } catch (error) {
        showError('Network Error', 'Could not reach server');
    }
}

// Secure Download wrapper to bypass browser HTTP download warnings
async function secureDownload(url, filename) {
    if (typeof showLoading === 'function') {
        showLoading('Preparing download...');
    }
    try {
        const response = await fetch(window.APP.BASE + "/" + url);
        if (!response.ok) throw new Error('Download failed');
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
    } catch (e) {
        console.error('Download error:', e);
        if (typeof showError === 'function') {
            showError('Download Error', 'Could not download the file securely.');
        } else {
            alert('Could not download the file.');
        }
    } finally {
        if (typeof hideLoading === 'function') {
            hideLoading();
        }
    }
}


// --- Global PDF Preview Handler ---

/**
 * Opens Chrome's native PDF viewer in a global modal overlay.
 * @param {string} billNo - The receipt bill number to preview.
 */
function openGlobalPDFPreview(billNo) {
    const iframe = document.getElementById('globalPdfIframe');
    const modalEl = document.getElementById('globalPdfModal');
    
    if (!iframe || !modalEl) {
        console.error("Global PDF Modal elements not found in the DOM.");
        if (typeof showError === 'function') showError("UI Error", "Cannot find PDF viewer components.");
        return;
    }

    // Point the iframe directly to your existing FastAPI PDF endpoint
    iframe.src = window.APP.API + `/pdf/${billNo}/view`;
    
    // Initialize and show the Bootstrap modal
    const pdfModal = new bootstrap.Modal(modalEl);
    pdfModal.show();
}

// Memory & UX Cleanup: Clear the iframe when the modal closes
document.addEventListener('DOMContentLoaded', () => {
    const modalEl = document.getElementById('globalPdfModal');
    if (modalEl) {
        modalEl.addEventListener('hidden.bs.modal', () => {
            const iframe = document.getElementById('globalPdfIframe');
            if (iframe) iframe.src = "";
        });
    }
});

// --- Live Global Search Engine ---
document.addEventListener('DOMContentLoaded', () => {
    const globalSearch = document.getElementById('globalSearchBar');
    const dropdown = document.getElementById('globalSearchDropdown');

    if (globalSearch && dropdown) {
        let searchTimeout;

        globalSearch.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim().toLowerCase();
            
            if (query.length < 2) {
                dropdown.style.display = 'none';
                return;
            }

            // Debounce the API call to prevent spamming the backend
            searchTimeout = setTimeout(async () => {
                try {
                    const [tRes, rRes] = await Promise.all([
                        fetch(window.APP.API + "/tenants"),
                        fetch(window.APP.API + "/bills/filter?status=all")
                    ]);
                    const tenants = await tRes.json();
                    const bills = await rRes.json();
                    
                    let html = '';
                    
                    // Filter Tenants
                    const matchT = tenants.filter(t => t.name.toLowerCase().includes(query) || `t${t.id}`.includes(query) || (t.company && t.company.toLowerCase().includes(query)));
                    if (matchT.length > 0) {
                        html += `<li><h6 class="dropdown-header text-primary fw-bold">Tenants</h6></li>`;
                        matchT.slice(0, 3).forEach(t => {
                            html += `<li><a class="dropdown-item" href="tenant/${t.id}">
                                <div class="d-flex align-items-center"><i class="bi bi-person bg-primary-subtle text-primary p-1 rounded me-2"></i> 
                                <div><div class="fw-semibold">${t.name} (T${t.id})</div>
                                <div class="text-muted" style="font-size: 0.7rem;">${t.company || 'Individual'}</div></div></div></a></li>`;
                        });
                    }
                    
                    // Filter Bills
                    const matchB = bills.filter(b => b.Tenant.toLowerCase().includes(query) || b.Bill.toLowerCase().includes(query) || String(b.Total).includes(query));
                    if (matchB.length > 0) {
                        if (html) html += `<li><hr class="dropdown-divider"></li>`;
                        html += `<li><h6 class="dropdown-header text-success fw-bold">Receipts</h6></li>`;
                        matchB.slice(0, 5).forEach(b => {
                            html += `<li><a class="dropdown-item" href="javascript:void(0)" onclick="dropdownPreview('${b.Bill}')">
                                <div class="d-flex justify-content-between align-items-center">
                                <div><i class="bi bi-receipt bg-success-subtle text-success p-1 rounded me-2"></i><span class="fw-semibold">#${b.Bill}</span></div>
                                <span class="text-muted fs-7">${b.Tenant}</span></div></a></li>`;
                        });
                    }
                    
                    if (!html) {
                        html = `<li><span class="dropdown-item text-muted py-3 text-center"><i class="bi bi-search d-block fs-4 mb-2"></i>No results found for "${query}"</span></li>`;
                    }
                    
                    dropdown.innerHTML = html;
                    dropdown.style.display = 'block';
                } catch (e) {
                    console.error("Live search failed", e);
                }
            }, 300); // 300ms debounce
        });

        // Hide dropdown on click outside
        document.addEventListener('click', (e) => {
            if (!globalSearch.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.style.display = 'none';
            }
        });

        // Keep the Enter key to redirect
        globalSearch.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                dropdown.style.display = 'none';
                const query = this.value.trim().toUpperCase();
                if (query.startsWith('T') && !isNaN(query.substring(1))) {
                    window.location.href = window.APP.BASE + `/tenant/${query.substring(1)}`;
                } else {
                    window.location.href = window.APP.BASE + `/history?q=${query}`;
                }
            }
        });
    }
});

// Helper for live dropdown PDF preview
window.dropdownPreview = function(billNo) {
    document.getElementById('globalSearchDropdown').style.display = 'none';
    openGlobalPDFPreview(billNo);
};

// --- Global Sync Overlay Controls ---
function showSyncOverlay(message = "Processing Data...") {
    const overlay = document.getElementById('globalSyncOverlay');
    const textEl = document.getElementById('syncOverlayText');
    if (overlay) {
        if(textEl) textEl.innerText = message;
        overlay.classList.add('active');
        document.activeElement.blur(); 
    }
}

function hideSyncOverlay() {
    const overlay = document.getElementById('globalSyncOverlay');
    if (overlay) overlay.classList.remove('active');
}

window.showLoadingOverlay = showSyncOverlay;
window.hideLoadingOverlay = hideSyncOverlay;

async function executeExport(format) {
    showSyncOverlay(`Generating ${format === 'template' ? 'Template' : format.toUpperCase() + ' Backup'}...`);
    
    try {
        const endpoint = format === 'template' ? window.APP.BASE + '/api/sync/template' : window.APP.API + `/sync/export/${format}`;
        const response = await fetch(endpoint);
        if (!response.ok) throw new Error("Failed to generate export file.");
        
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
            if (typeof showToast === 'function') showToast('success', `${format === 'template' ? 'Template' : format.toUpperCase() + ' Export'} completed successfully!`);
        }, 500);
    } catch (e) {
        hideSyncOverlay();
        if (typeof showError === 'function') {
            showError("Export Failed", e.message);
        } else {
            alert("Failed to export data.");
        }
    }
}
// Secure Download wrapper to bypass browser HTTP download warnings
async function secureDownload(url, filename) {
    if (typeof showLoading === 'function') {
        showLoading('Preparing download...');
    }
    try {
        const response = await fetch(window.APP.BASE + "/" + url);
        if (!response.ok) throw new Error('Download failed');
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
    } catch (e) {
        console.error('Download error:', e);
        if (typeof showError === 'function') {
            showError('Download Error', 'Could not download the file securely.');
        } else {
            alert('Could not download the file.');
        }
    } finally {
        if (typeof hideLoading === 'function') {
            hideLoading();
        }
    }
}


// --- Global PDF Preview Handler ---

/**
 * Opens Chrome's native PDF viewer in a global modal overlay.
 * @param {string} billNo - The receipt bill number to preview.
 */
function openGlobalPDFPreview(billNo) {
    const iframe = document.getElementById('globalPdfIframe');
    const modalEl = document.getElementById('globalPdfModal');
    
    if (!iframe || !modalEl) {
        console.error("Global PDF Modal elements not found in the DOM.");
        if (typeof showError === 'function') showError("UI Error", "Cannot find PDF viewer components.");
        return;
    }

    // Point the iframe directly to your existing FastAPI PDF endpoint
    iframe.src = window.APP.API + `/pdf/${billNo}/view`;
    
    // Initialize and show the Bootstrap modal
    const pdfModal = new bootstrap.Modal(modalEl);
    pdfModal.show();
}

// Memory & UX Cleanup: Clear the iframe when the modal closes
document.addEventListener('DOMContentLoaded', () => {
    const modalEl = document.getElementById('globalPdfModal');
    if (modalEl) {
        modalEl.addEventListener('hidden.bs.modal', () => {
            const iframe = document.getElementById('globalPdfIframe');
            if (iframe) iframe.src = "";
        });
    }
});

// --- Live Global Search Engine ---
document.addEventListener('DOMContentLoaded', () => {
    const globalSearch = document.getElementById('globalSearchBar');
    const dropdown = document.getElementById('globalSearchDropdown');

    if (globalSearch && dropdown) {
        let searchTimeout;

        globalSearch.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim().toLowerCase();
            
            if (query.length < 2) {
                dropdown.style.display = 'none';
                return;
            }

            // Debounce the API call to prevent spamming the backend
            searchTimeout = setTimeout(async () => {
                try {
                    const [tRes, rRes] = await Promise.all([
                        fetch(window.APP.API + "/tenants"),
                        fetch(window.APP.API + "/bills/filter?status=all")
                    ]);
                    const tenants = await tRes.json();
                    const bills = await rRes.json();
                    
                    let html = '';
                    
                    // Filter Tenants
                    const matchT = tenants.filter(t => t.name.toLowerCase().includes(query) || `t${t.id}`.includes(query) || (t.company && t.company.toLowerCase().includes(query)));
                    if (matchT.length > 0) {
                        html += `<li><h6 class="dropdown-header text-primary fw-bold">Tenants</h6></li>`;
                        matchT.slice(0, 3).forEach(t => {
                            html += `<li><a class="dropdown-item" href="tenant/${t.id}">
                                <div class="d-flex align-items-center"><i class="bi bi-person bg-primary-subtle text-primary p-1 rounded me-2"></i> 
                                <div><div class="fw-semibold">${t.name} (T${t.id})</div>
                                <div class="text-muted" style="font-size: 0.7rem;">${t.company || 'Individual'}</div></div></div></a></li>`;
                        });
                    }
                    
                    // Filter Bills
                    const matchB = bills.filter(b => b.Tenant.toLowerCase().includes(query) || b.Bill.toLowerCase().includes(query) || String(b.Total).includes(query));
                    if (matchB.length > 0) {
                        if (html) html += `<li><hr class="dropdown-divider"></li>`;
                        html += `<li><h6 class="dropdown-header text-success fw-bold">Receipts</h6></li>`;
                        matchB.slice(0, 5).forEach(b => {
                            html += `<li><a class="dropdown-item" href="javascript:void(0)" onclick="dropdownPreview('${b.Bill}')">
                                <div class="d-flex justify-content-between align-items-center">
                                <div><i class="bi bi-receipt bg-success-subtle text-success p-1 rounded me-2"></i><span class="fw-semibold">#${b.Bill}</span></div>
                                <span class="text-muted fs-7">${b.Tenant}</span></div></a></li>`;
                        });
                    }
                    
                    if (!html) {
                        html = `<li><span class="dropdown-item text-muted py-3 text-center"><i class="bi bi-search d-block fs-4 mb-2"></i>No results found for "${query}"</span></li>`;
                    }
                    
                    dropdown.innerHTML = html;
                    dropdown.style.display = 'block';
                } catch (e) {
                    console.error("Live search failed", e);
                }
            }, 300); // 300ms debounce
        });

        // Hide dropdown on click outside
        document.addEventListener('click', (e) => {
            if (!globalSearch.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.style.display = 'none';
            }
        });

        // Keep the Enter key to redirect
        globalSearch.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                dropdown.style.display = 'none';
                const query = this.value.trim().toUpperCase();
                if (query.startsWith('T') && !isNaN(query.substring(1))) {
                    window.location.href = window.APP.BASE + `/tenant/${query.substring(1)}`;
                } else {
                    window.location.href = window.APP.BASE + `/history?q=${query}`;
                }
            }
        });
    }
});

// Helper for live dropdown PDF preview
window.dropdownPreview = function(billNo) {
    document.getElementById('globalSearchDropdown').style.display = 'none';
    openGlobalPDFPreview(billNo);
};

// --- Global Sync Overlay Controls ---
function showSyncOverlay(message = "Processing Data...") {
    const overlay = document.getElementById('globalSyncOverlay');
    const textEl = document.getElementById('syncOverlayText');
    if (overlay) {
        if(textEl) textEl.innerText = message;
        overlay.classList.add('active');
        document.activeElement.blur(); 
    }
}

function hideSyncOverlay() {
    const overlay = document.getElementById('globalSyncOverlay');
    if (overlay) overlay.classList.remove('active');
}

window.showLoadingOverlay = showSyncOverlay;
window.hideLoadingOverlay = hideSyncOverlay;

async function executeExport(format) {
    showSyncOverlay(`Generating ${format === 'template' ? 'Template' : format.toUpperCase() + ' Backup'}...`);
    
    try {
        const endpoint = format === 'template' ? window.APP.BASE + '/api/sync/template' : window.APP.API + `/sync/export/${format}`;
        const response = await fetch(endpoint);
        if (!response.ok) throw new Error("Failed to generate export file.");
        
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
            if (typeof showToast === 'function') showToast('success', `${format === 'template' ? 'Template' : format.toUpperCase() + ' Export'} completed successfully!`);
        }, 500);
    } catch (e) {
        hideSyncOverlay();
        if (typeof showError === 'function') {
            showError("Export Failed", e.message);
        } else {
            alert("Failed to export data.");
        }
    }
}

async function updatePaymentStatus(billNo, newStatus, amountReceived) {
    if (newStatus === 'PARTIAL' && amountReceived === undefined) {
        const amount = prompt("Enter the partial amount received:");
        if (!amount) return; // User cancelled
        amountReceived = parseFloat(amount);
    }
    
    try {
        const response = await fetch(window.APP.API + `/bills/${billNo}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                payment_status: newStatus,
                amount_received: amountReceived
            })
        });
        
        if (response.ok) {
            showToast('success', `Bill #${billNo} marked as ${newStatus}!`);
            await updateUI();
        } else {
            showError('Error', 'Failed to update payment status');
        }
    } catch (error) {
        showError('Network Error', 'Could not reach server');
    }
}

// Global fix for Chrome aria-hidden focus warning on Bootstrap modals
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('hide.bs.modal', function () {
            if (document.activeElement) {
                document.activeElement.blur();
            }
        });
    });
});
