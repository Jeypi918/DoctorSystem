# Doctor Model DB Column Mismatch Fix

**Problem**: Doctor model (`db_table = 'core_doctor', managed = False`) defines fields not in legacy table.

**Error on doctor_detail_view(pk=1037)**: SELECT * fails on missing columns (middle_name, residentialaddress, etc.).

**Fix Plan**:
1. Add `fields = [...]` to Doctor.Meta - only actual DB columns
2. Use @property for computed/derived fields
3. Detail view: Use EmdDoctor(pk_emddoctors=pk) for legacy, Doctor for managed
4. Update views/forms to handle both

**Actual DB Columns (from EmdDoctor + error)**:
- pk (autoid?)
- doctors_name
- smsplusmobileno
- tin
- active
- prctype
- prcno
- prcexpdate
- phicno
- phicexpdate
- pmccno
- doctorsid
- bankacctname
- bankacctno
- s2no
- s2expirydate
- dctrcategory
- classcode
- ewtrate
- vatcondition
- specialization
- specialize
- servicetype

**Update Doctor model**:
```
class Meta:
    db_table = 'core_doctor'
    managed = False
    fields = ['id', 'doctors_name', 'smsplusmobileno', 'tin', 'active', 'prctype', 'prcno', 'prcexpdate', 'phicno', 'phicexpdate', 'pmccno', 'doctorsid', 'bankacctname', 'bankacctno', 's2no', 's2expirydate', 'dctrcategory', 'specialization']
```

**Views**:
- doctor_detail: EmdDoctor.objects.get(pk_emddoctors=pk)

