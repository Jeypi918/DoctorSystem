# Fix Admin Signup Role Bug (After Truncate)

## Status: [IN PROGRESS]

### Steps:

- [x] 1. Update core/views.py signup_view to force override profile.role = form.cleaned_data['role']; profile.save()\n- [x] 2. Condition signals.py create_user_profile to avoid default 'doctor' (e.g., check if role field exists or context) - Skipped: View force sufficient, urls use core/views.py\n- [x] 3. Verify core/forms.py SignUpForm role handling - Confirmed good, sets is_superuser for admin
- [ ] 4. Test: Signup new admin → check DB auth_user + core_userprofile role='admin'
- [ ] 5. Test doctor signup → role='doctor'
- [ ] 6. Migrate if needed (no)
- [ ] 7. Run server and verify no regressions

**Root Cause**: Signal post_save creates UserProfile(role='doctor' default) on user.save() → view update_or_create skips defaults on existing → stuck doctor.

**Current Progress**: Plan approved, TODO created.
