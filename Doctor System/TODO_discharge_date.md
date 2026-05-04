# TODO: Integrate DischargeDate column into Outstanding Report

## Steps:

- [x] 1. Add `discharge_date` field to `OutstandingPayable` model in `Doctor System/core/models.py`
- [x] 2. Update `OutstandingReportListView.get_queryset()` in `Doctor System/core/views.py` to support search/filtering by `discharge_date` (add to Q, discharge_from/to params)
- [x] 3. Add "Discharge Date" column to table in `Doctor System/templates/outstanding_report.html` (after Status column)
- [x] 4. Test: runserver, visit /outstanding-report/, verify display/filter/search works
- [x] 5. Mark complete and attempt_completion
