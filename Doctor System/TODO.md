# TODO: ReleasedChecks Release Date to YYYY-MM-DD DateField

## Completed

- [x] Create TODO.md

## Pending Steps (from approved plan)

1. [x] Edit `Doctor System/core/models.py`: Change `releasedate` from CharField to DateField(null=True, blank=True), add db_column='releasedate', remove `get_releasedate_formatted()` method. ✅
2. [x] Edit `Doctor System/core/views.py`: In ReleasedCheckListView.get_queryset(), replace raw SQL CONVERT with Django ORM date filtering: queryset = queryset.filter(releasedate\_\_gte=date_from) if date_from, etc. ✅\n3. [x] Edit `Doctor System/core/admin.py`: Add releasedate to list_filter. ✅\n4. [x] Edit `Doctor System/templates/released_checks_list.html`: Change `{{ rc.get_releasedate_formatted }}` to `{{ rc.releasedate|date:"Y-m-d"|default:"—" }}`. ✅
3. **Manual DB Update** (critical):
   ```
   -- Backup DB first!
   UPDATE releasedchecks SET releasedate = NULL WHERE releasedate = '' OR releasedate IS NULL;
   UPDATE releasedchecks SET releasedate = TRY_CONVERT(date, releasedate, 101) WHERE releasedate IS NOT NULL AND TRY_CONVERT(date, releasedate, 101) IS NOT NULL;
   ```
   Run in SQL Server Management Studio or phpMyAdmin (if MySQL, adjust syntax).
4. Test: Restart server (`python Doctor System/manage.py runserver`), check /released-checks/ list, filters, admin.
5. Mark complete.

**Next**: After step 1-4 edits confirmed, run DB update, test, then delete this TODO.md.
