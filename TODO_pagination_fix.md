# TODO - Pagination Fix

## Task: Fix pagination on multiple templates

### Issues to Fix:

1. Expand visible range from 5 pages to 10 pages
2. Remove duplicate "1" showing twice (at beginning and in page range)
3. Remove duplicate last page showing twice

### Templates to Edit:

1. released_checks_list.html
2. check_report_list.html
3. outstanding_report.html
4. doctors_list.html
5. apv_list.html
6. unreleased_checks_list.html

### Changes Required:

- Replace `current|add:"-2"` with `current|add:"-4"` (shows 5 pages before current)
- Replace `current|add:"2"` with `current|add:"5"` (shows 5 pages after current)
- Remove standalone first "1" link when showing page 1 in range
- Remove standalone last page link when already shown in range

### Progress:

- ✅ released_checks_list.html
- ✅ check_report_list.html
- ✅ outstanding_report.html
- ✅ doctors_list.html
- ✅ apv_list.html
- ✅ unreleased_checks_list.html

**✅ ALL FILES FIXED!**
