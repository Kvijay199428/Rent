function initializeSharedSearch(searchInputId, containerSelector, rowSelector) {
    const searchInput = document.getElementById(searchInputId);
    if (!searchInput) return;

    searchInput.addEventListener('keyup', function() {
        const query = this.value.toLowerCase();
        const containers = document.querySelectorAll(containerSelector);

        containers.forEach(container => {
            const rows = container.querySelectorAll(rowSelector);
            let visibleInContainer = 0;

            rows.forEach(row => {
                // Fetch attributes
                const tenant = (row.getAttribute('data-tenant') || "").toLowerCase();
                const month = (row.getAttribute('data-month') || "").toLowerCase();
                const year = (row.getAttribute('data-year') || "").toLowerCase();
                const bill = (row.getAttribute('data-bill') || "").toLowerCase();
                const company = (row.getAttribute('data-company') || "").toLowerCase();
                const amount = parseFloat(row.getAttribute('data-total') || "0");
                
                // Allow amount range searching like "> 5000" or simple match
                let amountMatches = false;
                if (query.startsWith(">") || query.startsWith("<")) {
                    const num = parseFloat(query.substring(1).trim());
                    if (!isNaN(num)) {
                        if (query.startsWith(">") && amount > num) amountMatches = true;
                        if (query.startsWith("<") && amount < num) amountMatches = true;
                    }
                } else if (amount.toString().includes(query)) {
                    amountMatches = true;
                }

                if (
                    tenant.includes(query) || 
                    month.includes(query) || 
                    year.includes(query) || 
                    bill.includes(query) ||
                    company.includes(query) ||
                    amountMatches
                ) {
                    row.style.display = "";
                    visibleInContainer++;
                } else {
                    row.style.display = "none";
                }
            });

            // Container visibility logic (specifically for accordion year groups)
            if (container.classList.contains('year-group')) {
                if (visibleInContainer === 0) {
                    container.style.display = "none";
                } else {
                    container.style.display = "";
                    const collapseTarget = container.querySelector('.accordion-collapse');
                    if (collapseTarget && query.length > 0) {
                        collapseTarget.classList.add('show');
                    }
                }
            }
        });
    });
}
