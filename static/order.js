// Export current visible order page to PDF via print dialog
function exportTableToPDF() {
    window.print();
}

// Handle pagination navigation
function goToPage(page) {
    const url = new URL(window.location.href);
    url.searchParams.set('page', page);
    window.location.href = url.toString();
}