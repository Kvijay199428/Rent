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

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove("open");
        if (overlay) overlay.classList.remove("show");
        document.body.classList.remove("sidebar-open");
    }

    if (toggle) {
        toggle.addEventListener("click", () => {
            sidebar.classList.toggle("open");
            overlay.classList.toggle("show");
            document.body.classList.toggle("sidebar-open");
        });
    }

    if (overlay) overlay.addEventListener("click", closeSidebar);
    if (closeBtn) closeBtn.addEventListener("click", closeSidebar);

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
    } catch (e) {
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
const ThemeManager = {
    STORAGE_KEY: "rrg-theme",

    getStoredTheme() {
        return localStorage.getItem(this.STORAGE_KEY) || document.documentElement.getAttribute("data-user-theme") || "system";
    },

    getEffectiveTheme(theme) {
        if (theme === "system") {
            return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
        }
        return theme;
    },

    applyTheme(theme) {
        const effective = this.getEffectiveTheme(theme);
        document.documentElement.setAttribute("data-bs-theme", effective);
        document.documentElement.setAttribute("data-user-theme", theme);
        return effective;
    },

    syncThemeControls(theme, effectiveTheme) {
        // Sync Settings Page UI if it exists
        document.querySelectorAll(".theme-option-btn").forEach(btn => {
            const opt = btn.getAttribute("data-theme-option");
            const isActive = opt === theme;
            btn.setAttribute("aria-pressed", isActive ? "true" : "false");

            const badge = btn.querySelector(".theme-active-badge");
            if (badge) {
                if (isActive) badge.classList.remove("d-none");
                else badge.classList.add("d-none");
            }
        });

        const selectedLabel = document.getElementById("themeSelectedLabel");
        if (selectedLabel) {
            selectedLabel.textContent = theme.charAt(0).toUpperCase() + theme.slice(1);
        }

        const appliedLabel = document.getElementById("themeAppliedLabel");
        if (appliedLabel) {
            appliedLabel.textContent = effectiveTheme.charAt(0).toUpperCase() + effectiveTheme.slice(1);
        }

        // Sync Header Dropdown
        document.querySelectorAll(".theme-menu .dropdown-item").forEach(btn => {
            const opt = btn.getAttribute("data-theme-option");
            const check = btn.querySelector(".theme-menu-check");
            if (check) {
                if (opt === theme) check.classList.remove("d-none");
                else check.classList.add("d-none");
            }
        });
    },

    async saveTheme(theme) {
        const statusEl = document.getElementById("themeSaveStatus");
        if (statusEl) {
            statusEl.className = "theme-save-status saving";
            statusEl.innerHTML = '<span class="spinner-border spinner-border-sm me-1" style="width:1rem;height:1rem;" role="status"></span> Saving...';
        }

        localStorage.setItem(this.STORAGE_KEY, theme);

        try {
            const url = (window.RouteManifest && window.RouteManifest.api && window.RouteManifest.api.themeUpdate)
                ? window.RouteManifest.api.themeUpdate
                : (window.APP.API + "/ui/theme");

            const res = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ theme: theme })
            });

            if (res.ok) {
                if (statusEl) {
                    statusEl.className = "theme-save-status saved";
                    statusEl.innerHTML = '<i class="bi bi-check-circle-fill me-1 text-success"></i> Saved';
                    setTimeout(() => {
                        if (statusEl.className.includes("saved")) {
                            statusEl.className = "theme-save-status idle";
                            statusEl.innerHTML = '<i class="bi bi-circle-fill me-1 small text-muted"></i> Ready';
                        }
                    }, 2000);
                }
            } else {
                throw new Error("Failed to save");
            }
        } catch (e) {
            if (statusEl) {
                statusEl.className = "theme-save-status error text-danger fw-bold";
                statusEl.innerHTML = '<i class="bi bi-exclamation-triangle-fill me-1"></i> Could not save preference';
            } else {
                showError("Theme Error", "Failed to switch theme persistently.");
            }
        }
    },

    init() {
        const current = this.getStoredTheme();
        const effective = this.applyTheme(current);
        // Only run sync on DOMContentLoaded to ensure elements exist
        document.addEventListener("DOMContentLoaded", () => {
            this.syncThemeControls(current, effective);
        });

        document.addEventListener("click", (e) => {
            const btn = e.target.closest("[data-theme-option]");
            if (btn) {
                const theme = btn.getAttribute("data-theme-option");
                const effective = this.applyTheme(theme);
                this.syncThemeControls(theme, effective);
                this.saveTheme(theme);
            }
        });

        window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
            const current = this.getStoredTheme();
            if (current === "system") {
                const effective = this.applyTheme("system");
                this.syncThemeControls("system", effective);
            }
        });
    }
};

ThemeManager.init();

// Provide backward compatibility just in case
function setTheme(theme) {
    const effective = ThemeManager.applyTheme(theme);
    ThemeManager.syncThemeControls(theme, effective);
    ThemeManager.saveTheme(theme);
}

// --- Smooth Payment Status Toggle with Arrears Logic ---
async function togglePaymentStatus(billNo, currentStatus, grandTotal, currentReceived = 0) {
    if (currentStatus === "PAID" || currentStatus === "PARTIAL" || currentStatus === "ADVANCE") {
        const reset = await confirmAction("Reset Status?", "Reset this bill to PENDING?", "Yes, Reset");
        if (!reset.isConfirmed) return;

        try {
            const res = await fetch(`${window.APP.BASE}/api/bill/${billNo}/payment`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ paymentstatus: "PENDING", amountreceived: 0 })
            });
            const result = await res.json().catch(() => ({}));
            if (!res.ok) {
                showError("Payment Update Failed", result.detail || "Could not update payment.");
                return;
            }
            await updateUI();
        } catch (e) {
            showError("Network Error", "Could not reach server.");
        }
        return;
    }

    const defaultAmount = parseFloat(currentReceived) > 0 ? parseFloat(currentReceived) : parseFloat(grandTotal);
    const { value: input } = await Swal.fire({
        title: "Amount Received",
        text: `Total Bill: ₹${parseFloat(grandTotal).toFixed(2)}`,
        input: "number",
        inputValue: defaultAmount.toFixed(2),
        showCancelButton: true,
        confirmButtonText: "Update",
        confirmButtonColor: "#198754"
    });

    if (input === undefined || input === null || input === "") return;

    const amount = parseFloat(input);
    if (Number.isNaN(amount) || amount < 0) {
        showError("Invalid Amount", "Please enter a valid non-negative amount.");
        return;
    }

    try {
        const res = await fetch(`${window.APP.BASE}/api/bill/${billNo}/payment`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ paymentstatus: "PAID", amountreceived: amount })
        });
        const result = await res.json().catch(() => ({}));
        if (!res.ok) {
            showError("Payment Update Failed", result.detail || "Could not update payment.");
            return;
        }
        showToast("success", `Bill ${billNo} payment updated!`);
        await updateUI();
    } catch (e) {
        showError("Network Error", "Could not reach server.");
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
function appUrl(path) {
    const base = (window.APP?.BASE || "").replace(/\/+$/, "");
    const cleanPath = String(path || "").replace(/^\/+/, "");
    return `${base}/${cleanPath}`;
}

document.addEventListener('DOMContentLoaded', () => {
    const globalSearch = document.getElementById('globalSearchBar');
    const dropdown = document.getElementById('globalSearchDropdown');

    if (globalSearch && dropdown) {
        let searchTimeout;

        globalSearch.addEventListener('input', function () {
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
                            const tenantUrl = appUrl(`tenant/${t.id}`);
                            html += `
                                <li>
                                    <a class="dropdown-item" href="${tenantUrl}">
                                        <div class="d-flex align-items-center">
                                            <i class="bi bi-person bg-primary-subtle text-primary p-1 rounded me-2"></i>
                                            <div>
                                                <div class="fw-semibold">${t.name} (T-${t.id})</div>
                                                <div class="text-muted" style="font-size: 0.7rem;">${t.company || "Individual"}</div>
                                            </div>
                                        </div>
                                    </a>
                                </li>
                            `;
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

                if (/^T\d+$/.test(query)) {
                    window.location.href = appUrl(`tenant/${query.substring(1)}`);
                } else {
                    window.location.href = appUrl(`history?q=${encodeURIComponent(query)}`);
                }
            }
        });
    }
});

// Helper for live dropdown PDF preview
window.dropdownPreview = function (billNo) {
    document.getElementById('globalSearchDropdown').style.display = 'none';
    openGlobalPDFPreview(billNo);
};

// --- Global Sync Overlay Controls ---

// --- Global Sync Overlay Controls ---
function showSyncOverlay(message = "Processing Data...") {
    const overlay = document.getElementById('globalSyncOverlay');
    const textEl = document.getElementById('syncOverlayText');
    if (overlay) {
        if (textEl) textEl.innerText = message;
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
        const endpoint = format === 'template' ? window.APP.API + '/sync/template' : window.APP.API + `/sync/export/${format}`;
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

// Fix for Chrome aria-hidden focus warning on Edit Modal
document.addEventListener('DOMContentLoaded', () => {
    const modalsToUnfocus = ["globalEditBillModal", "globalPdfModal"];

    modalsToUnfocus.forEach(modalId => {
        const modalEl = document.getElementById(modalId);
        modalEl?.addEventListener("hide.bs.modal", function () {
            if (document.activeElement && modalEl.contains(document.activeElement)) {
                document.activeElement.blur();
            }
        });
    });
});
