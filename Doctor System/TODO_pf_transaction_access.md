# Fix Admin Access to PF Transactions and Sub-views (Doctor Required Views)

Status: In Progress

## Diagnosis:

- Sidebar/home 'PF Transactions' -> /transactions/ (dashboard with cards for Released Checks etc.)
- Cards 'View All' -> doctor_required views -> admin redirects to dashboard
- PFTransaction table empty (no data)

## Steps:

- [x] 1. Update decorators.py: doctor_required allows 'admin' OR 'doctor'
- [ ] 2. Protect unprotected ListViews with @login_required (views.py)
- [ ] 3. Test admin access to /transactions/ and sub-views
- [ ] 4. Add sample PFTransaction data if table empty
- [ ] 5. Complete: attempt_completion

## Plan Details:

Modified doctor_required to pass admins.
Added login_required to TransactionListView, PatientListView, SoaListView.
