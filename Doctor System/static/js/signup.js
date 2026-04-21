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
            // Generate username: First letter upper + rest lower for first, + First letter upper + rest lower for last
            // e.g., "JP" -> "Jp", "Cureg" -> "Cureg" → "JpCureg"
            const formattedFirst = firstName.charAt(0).toUpperCase()+firstName.slice(1).toLowerCase();
            const formattedLast = lastName.charAt(0).toLowerCase()+lastName.slice(1).toLowerCase();
            usernameInput.value = formattedFirst+formattedLast;
        } else {
            usernameInput.value = '';
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

