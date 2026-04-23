# Doctor PF Transactions Filtering - Implementation Steps

## Completed: [ ]

## Progress: 0/10

1. [ ] Create TODO_doctor_pf_filter.md (this file) - DONE
2. [ ] Extract doctor matching helper function from my_doctor_view to utils or views mixin
3. [ ] Add @doctor_required decorator to 5 ListViews: ReleasedCheckListView, UnreleasedCheckListView, OutstandingReportListView, APVListView, CheckReportListView
4. [ ] Implement get_queryset() filter by doctor.doctors_name in each ListView (payee/payeename/Vendor/payee_name/payto \_\_icontains)
5. [ ] Update home_view counts: filter by doctor if role=='doctor'
6. [ ] Update TransactionListView.get_context_data counts similarly
7. [ ] Add doctor_self.html navigation cards/links to the 5 PF pages
8. [ ] Add template badges: "Showing X of your records" in list templates
9. [ ] Test as doctor: login, check each page filters correctly
10. [ ] Test as admin: sees all data
11. [ ] Update this TODO with completions
12. [ ] attempt_completion

**Notes:**

- Use same matching logic as my_doctor_view
- Admin/other roles see all
- No DB changes
