# Doctor Auth: PRCno + lastname{pk} Username/Password Fix

## Steps:

- [✅] 1. Update core/models.py: Add computed username property to EmdDoctor
- [✅] 2. Update core/views.py: Improve doctor_reset_password_view (lastname + pk_emddoctors for username/pwd)
- [✅] 3. Update core/views.py: Improve get_current_doctor (reverse lookup by username pattern)
- [✅] 4. Test reset/login → my_doctor shows correct profile
- [✅] 5. Update this TODO (complete)

✅ **Completed**: Doctor reset now generates Username/Pwd = Lastname{pk} (Guzman1124), PRCno check, improved login matching (regex parse pk from username + name match, fallback fuzzy). doctor_self.html already shows full info.

**Demo**: python manage.py runserver → /doctors/ → reset pwd → login w/ new creds → /my-doctor/
