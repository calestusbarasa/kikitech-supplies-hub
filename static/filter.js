document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("searchInput");
    const tableRows = document.querySelectorAll("tbody tr");
    const totalDisplay = document.getElementById("grandTotalDisplay");
    const totalValue = document.getElementById("grandTotalValue");

    if (searchInput) {
        searchInput.addEventListener("keyup", function () {
            const filter = searchInput.value.toLowerCase();
            let visibleRows = 0;
            let runningTotal = 0;

            tableRows.forEach(row => {
                const text = row.innerText.toLowerCase();
                if (text.includes(filter)) {
                    row.style.display = "";
                    visibleRows++;
                    const amount = parseFloat(row.getAttribute("data-total")) || 0;
                    runningTotal += amount;
                } else {
                    row.style.display = "none";
                }
            });

            if (totalValue) totalValue.textContent = runningTotal.toFixed(2);
            if (totalDisplay) totalDisplay.style.display = visibleRows > 0 ? "block" : "none";
        });
    }

    const printBtn = document.getElementById("printBtn");
    if (printBtn) {
        printBtn.addEventListener("click", function () {
            window.print();
        });
    }

    const pdfBtn = document.getElementById("downloadPdfBtn");
    if (pdfBtn) {
        pdfBtn.addEventListener("click", function () {
            window.print(); // Optionally implement PDF export here
        });
    }
});