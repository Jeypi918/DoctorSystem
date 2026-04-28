# TODO: Add new database fields to UnreleasedCheck

## Steps

1. [x] Update `core/models.py` — Add 8 new fields to `UnreleasedCheck`
2. [x] Update `core/views.py` — Expand `UnreleasedCheckListView` search filter
3. [x] Update `templates/unreleased_checks_list.html` — Add new columns to table
4. [x] Update `core/admin.py` — Register `UnreleasedCheck` with new fields
5. [x] Fix pagination ordering — Added `.order_by()` to all ListView querysets
