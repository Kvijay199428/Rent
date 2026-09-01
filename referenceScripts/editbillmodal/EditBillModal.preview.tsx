/**
 * EditBillModal.preview.tsx
 * ------------------------------------------------------------------
 * A throwaway preview harness for <EditBillModal />.
 *
 * Unlike a pure-UI component, EditBillModal fetches its own data
 * (api.getReceipt / api.getProperties / api.getBillingMonths /
 * api.getTenant) as soon as it's given a billNo + tenantId, and it
 * needs a real landlordUuid from AuthContext to do it. So this
 * harness does NOT mock those out — it runs inside your real app,
 * against a real bill, so you can see the actual data in the layout
 * (long property names/addresses, long tenant names, etc.) rather
 * than guessing with fake values.
 *
 * HOW TO USE
 * 1. Drop this file anywhere in your app, e.g. src/pages/_preview/EditBillModalPreview.tsx
 * 2. Temporarily mount it, e.g. add a throwaway route:
 *      { path: '/_preview/edit-bill', element: <EditBillModalPreview /> }
 *    then visit /_preview/edit-bill and enter a real Bill No + Tenant ID
 *    from your dev database (e.g. from the Bills modal you already
 *    previewed, or straight from your DB/admin panel).
 * 3. For the best overlap stress-test, pick a tenant/property combo
 *    with the longest name + address you have — that's the case the
 *    header and the Property/Tenant grid need to survive.
 * 4. Delete this file (and the throwaway route) once you're done.
 *
 * WHAT TO LOOK FOR
 * - The dialog title ("Edit Receipt #...") should truncate rather
 *   than running under the close (X) button for a long bill number.
 * - The Property select value and the disabled Tenant input should
 *   each stay inside their own column and ellipsize instead of
 *   overlapping each other or spilling out of the grid, even with a
 *   long property name + address.
 */
import { useState } from 'react';
import EditBillModal from './EditBillModal'; // adjust path to match where you saved the fixed file

export default function EditBillModalPreview() {
    const [billNo, setBillNo] = useState('');
    const [tenantId, setTenantId] = useState('');
    const [openBillNo, setOpenBillNo] = useState<string | null>(null);
    const [openTenantId, setOpenTenantId] = useState<number | null>(null);

    return (
        <div className="p-6 space-y-3 max-w-sm">
            <div className="space-y-1">
                <label className="text-sm font-medium">Bill No</label>
                <input
                    className="w-full border rounded-md px-2 py-1.5 text-sm"
                    value={billNo}
                    onChange={(e) => setBillNo(e.target.value)}
                    placeholder="e.g. B-2026-08"
                />
            </div>
            <div className="space-y-1">
                <label className="text-sm font-medium">Tenant ID</label>
                <input
                    className="w-full border rounded-md px-2 py-1.5 text-sm"
                    value={tenantId}
                    onChange={(e) => setTenantId(e.target.value)}
                    placeholder="e.g. 12345"
                />
            </div>
            <button
                type="button"
                className="rounded-md border px-3 py-1.5 text-sm"
                onClick={() => {
                    setOpenBillNo(billNo || null);
                    setOpenTenantId(tenantId ? Number(tenantId) : null);
                }}
            >
                Open Edit Bill Modal (preview)
            </button>

            <EditBillModal
                billNo={openBillNo}
                tenantId={openTenantId}
                onClose={() => setOpenBillNo(null)}
                onSaved={() => setOpenBillNo(null)}
            />
        </div>
    );
}
