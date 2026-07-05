// SweetAlert2 Global Wrappers

const Toast = Swal.mixin({
    toast: true,
    position: 'top-end',
    showConfirmButton: false,
    timer: 3000,
    timerProgressBar: true,
    didOpen: (toast) => {
        toast.addEventListener('mouseenter', Swal.stopTimer)
        toast.addEventListener('mouseleave', Swal.resumeTimer)
    }
});

function showToast(icon, title) {
    Toast.fire({
        icon: icon,
        title: title
    });
}

function showSuccess(title, text, html = null) {
    return Swal.fire({
        icon: 'success',
        title: title,
        text: text,
        html: html,
        confirmButtonColor: '#198754',
        showClass: { popup: 'animate__animated animate__fadeInDown animate__faster' },
        hideClass: { popup: 'animate__animated animate__fadeOutUp animate__faster' }
    });
}

function showError(title, text) {
    return Swal.fire({
        icon: 'error',
        title: title,
        text: text,
        confirmButtonColor: '#dc3545',
        showClass: { popup: 'animate__animated animate__shakeX animate__faster' }
    });
}

function confirmAction(title, text, confirmBtnText = 'Confirm', confirmColor = '#dc3545') {
    return Swal.fire({
        title: title,
        text: text,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: confirmColor,
        cancelButtonColor: '#6c757d',
        confirmButtonText: confirmBtnText,
        showClass: { popup: 'animate__animated animate__fadeIn animate__faster' }
    });
}
