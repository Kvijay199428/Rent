// Fullscreen Loading Overlay

function showLoadingOverlay(text = "Please wait...") {
    if (document.getElementById('global-loading-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'global-loading-overlay';
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100vw';
    overlay.style.height = '100vh';
    overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
    overlay.style.zIndex = '9999';
    overlay.style.display = 'flex';
    overlay.style.flexDirection = 'column';
    overlay.style.justifyContent = 'center';
    overlay.style.alignItems = 'center';
    overlay.style.color = '#fff';
    overlay.style.backdropFilter = 'blur(4px)';

    overlay.innerHTML = `
        <div class="spinner-border text-light mb-3" role="status" style="width: 3rem; height: 3rem;">
            <span class="visually-hidden">Loading...</span>
        </div>
        <h4 class="fw-bold tracking-wider">${text}</h4>
    `;

    document.body.appendChild(overlay);
    document.body.style.overflow = 'hidden';
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('global-loading-overlay');
    if (overlay) {
        overlay.remove();
        document.body.style.overflow = '';
    }
}
