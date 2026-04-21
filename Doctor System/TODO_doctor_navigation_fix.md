# Doctor Navigation Fix TODO

## Status: In Progress

### Steps:

- [x] 1. Create this TODO file
- [x] 2. Read home.html to check navigation links to doctors (confirmed: has `{% url 'doctors' %}` card link)
- [x] 3. Confirmed URL names in core/urls.py (good, path('doctors/', DoctorListView.as_view(), name='doctors'))
- [x] 4. Analyzed views.py decorators - detail view @staff_required blocks non-admin users
- [x] 5. Added @login_required to DoctorListView via dispatch method
- [x] 6. Removed @staff_required from doctor_detail_view (now @login_required only)
- [x] 7. Added debug PK display to doctors_list.html (title attribute on name link)

**Next Step:** Test navigation in browser. Run `cd "Doctor System" ; python manage.py runserver`, login as non-admin user, go to home -> Doctors card -> click doctor name.

- [ ] 7. Add debug pk display to doctors_list.html temporarily
- [ ] 8. Test navigation: home -> doctors -> click name
- [ ] 9. Clean up debug and complete

**Next Step:** Analyzed doctor_self.html (no direct doctor list links), models_emd.py (same as models.py, pk_emddoctors correct). URLs good, home.html link good.

**Root Cause Found:** DoctorListView in views.py has NO decorator, accessible to all. But doctor_detail_view has @staff_required + @login_required. Non-staff users (doctors, billing) can see list but can't click to detail.

**Fix:** Make doctor list @login_required only, detail @login_required only (remove staff_required for broader access), or adjust per role.

**Next Step:** Update TODO with fix plan, then edit views.py

- [ ] 3. Confirm URL names in core/urls.py and add name='doctors' if missing
- [ ] 4. Update core/views.py: Add explicit doctor_list_view or adjust DoctorListView decorator
- [ ] 5. Add debug info to doctors_list.html to verify pk_emddoctors values
- [ ] 6. Update home.html with proper `{% url 'doctors' %}` link for "View Doctors"
- [ ] 7. Test navigation flow after changes
- [ ] 8. Remove debug info and mark complete
- [ ] 9. attempt_completion with test instructions

**Next Step:** Read home.html
