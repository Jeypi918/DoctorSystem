document.addEventListener('DOMContentLoaded', function() {
    const firstNameInput = document.getElementById('id_first_name');
    const lastNameInput = document.getElementById('id_last_name');
    const usernameInput = document.getElementById('id_username');
    const roleSelect = document.getElementById('id_role');
    const specialtyGroup = document.getElementById('specialty-group');
    const specialtyInput = document.getElementById('id_specialty');

    if (!firstNameInput || !lastNameInput || !usernameInput) {
        console.error('Signup form fields not found');
        return;
    }

    function updateUsername() {
        const firstName = firstNameInput.value.trim();
        const lastName = lastNameInput.value.trim();

        if (firstName && lastName) {
            // Split words, lowercase all, join without spaces
            const firstWords = firstName.toLowerCase().replace(/\\s+/g, ' ').trim().split(' ').filter(Boolean).join('');
            const lastWords = lastName.toLowerCase().replace(/\\s+/g, ' ').trim().split(' ').filter(Boolean).join('');
            const newUsername = firstWords + lastWords;
            usernameInput.value = newUsername;
            
            // Set password fields to match username
            const password1 = document.getElementById('id_password1');
            const password2 = document.getElementById('id_password2');
            if (password1) password1.value = newUsername;
            if (password2) password2.value = newUsername;
        } else {
            usernameInput.value = '';
            const password1 = document.getElementById('id_password1');
            const password2 = document.getElementById('id_password2');
            if (password1) password1.value = '';
            if (password2) password2.value = '';
        }
    }

    function updateSpecialtyVisibility() {
        if (roleSelect && specialtyGroup) {
            const selectedRole = roleSelect.value;
            if (selectedRole === 'doctor') {
                specialtyGroup.style.display = 'block';
                specialtyInput.required = true;
            } else {
                specialtyGroup.style.display = 'none';
                specialtyInput.required = false;
                specialtyInput.value = ''; // Clear the value when hidden
            }
        }
    }

    // Update on input events
    firstNameInput.addEventListener('input', updateUsername);
    lastNameInput.addEventListener('input', updateUsername);
    
    // Show/hide specialty based on role selection
    if (roleSelect) {
        roleSelect.addEventListener('change', updateSpecialtyVisibility);
    }

    // Initial call in case fields pre-filled
    updateUsername();
    updateSpecialtyVisibility();
});
