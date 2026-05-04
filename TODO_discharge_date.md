# TODO: Add DischargeDate to Released Checks

## Task: Update ReleasedCheck model, view, and template to include DischargeDate column

### Step 1: Add DischargeDate field to ReleasedCheck model

- File: `Doctor System/core/models.py`
- Add `discharge_date = models.DateTimeField()` field with db_column='DischargeDate'

### Step 2: Update ReleasedCheckListView

- File: `Doctor System/core/views.py`
- Add DischargeDate to search filters in get_queryset method
- Add date filtering for DischargeDate

### Step 3: Update released_checks_list.html template

- File: `Doctor System/templates/released_checks_list.html`
- Add DischargeDate column header
- Add DischargeDate data cell in the table body
- Display with format mm/dd/yyyy

## Status: PENDING
