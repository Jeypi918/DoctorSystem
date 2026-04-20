# TODO: Update Home Dashboard Transactions Card to PF Transactions Total (625,962)

## Steps:

- [ ] Step 1: Create this TODO.md file ✅ (automated)
- [✅] Step 2: Edit `Doctor System/core/views.py` - Update `home_view`:
  - Import models: ReleasedCheck, UnreleasedCheck, OutstandingPayable, APV, CheckReport (already present)
  - Compute `pf_total = released_count + unreleased_count + outstanding_count + apv_count + check_report_count`
  - Set `transaction_count = pf_total` instead of `PFTransaction.objects.count()` ✅ (edit successful)
- [ ] Step 3: Restart Django server if running (e.g., `python Doctor System/manage.py runserver`)
- [ ] Step 4: Verify on /home/ page: Transactions card shows 625,962
- [ ] Step 5: Mark complete and close task

**Status:** Steps 1-2 complete. Refresh/restart Django server and check http://localhost:8000/ home page Transactions card (should show 625,962). Mark Step 4 ✅ then done.
