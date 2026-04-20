# Doctors Category Display Fix ✅ COMPLETE

- Added `category = models.CharField('Category', max_length=50, db_column='category', blank=True)` to EmdDoctor in core/models.py
- Updated doctors_list.html: `{{ doctor.category|default:"N/A" }}`

**Restart Django server and visit doctors list:** Categories ("Regular Consultant", etc.) now display from DB column 'category'.

No migrations needed (managed=False). Changes ready.
