from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('doctor', 'Doctor'),
        ('billing', 'Billing'),
        ('accounting', 'Accounting'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='doctor')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

class EmdDoctor(models.Model):
    # Primary model for emddoctors table - FULL SYSTEM SWITCH
    pk_emddoctors = models.IntegerField(primary_key=True)
    doctors_name = models.CharField(max_length=255)
    smsplusmobileno = models.CharField('Mobile', max_length=30, blank=True)
    tin = models.CharField(max_length=15, blank=True)
    active = models.BooleanField(default=True)
    prctype = models.CharField('PRC Type', max_length=10, blank=True)
    prcno = models.CharField(max_length=15, blank=True)
    prcexpdate = models.DateField(null=True, blank=True)
    phicno = models.CharField(max_length=40, blank=True)
    fk_psphicpfgroup = models.CharField(max_length=20, blank=True)
    phicexpdate = models.DateField(null=True, blank=True)
    pmccno = models.CharField(max_length=20, blank=True)
    doctorsid = models.IntegerField(blank=True, null=True)
    bankacctname = models.CharField(max_length=125, blank=True)
    bankacctno = models.CharField(max_length=20, blank=True)
    s2no = models.CharField(max_length=20, blank=True)
    s2expirydate = models.DateField(null=True, blank=True)
    dctrcategory = models.CharField(max_length=10, blank=True)
    classcode = models.CharField(max_length=2, blank=True)
    ewtrate = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    vatcondition = models.CharField(max_length=1, blank=True)
    phicissuancedate = models.DateField(null=True, blank=True)
    specialization = models.TextField(blank=True)
    specialize = models.CharField(max_length=30, blank=True)
    service_type = models.TextField('Service Type', blank=True)
    category = models.CharField('Category', max_length=50, db_column='category', blank=True)
    
    # User relation - db_column='user_id' if legacy column exists, else None
    # user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='emd_doctor_profile', null=True, blank=True)
    
    # Computed properties for compatibility
    @property
    def full_name(self):
        if ',' in self.doctors_name:
            parts = self.doctors_name.split(',', 1)
            last = parts[0].strip()
            first = parts[1].strip().split()[0] if len(parts[1].strip()) > 0 else ''
            return f"{last}, {first}"
        return self.doctors_name
    
    @property
    def first_name(self):
        if ',' in self.doctors_name:
            parts = self.doctors_name.split(',', 1)[1].strip().split()
            return parts[0] if parts else ''
        parts = self.doctors_name.split()
        return parts[0] if parts else ''
    
    @property
    def last_name(self):
        if ',' in self.doctors_name:
            return self.doctors_name.split(',', 1)[0].strip()
        parts = self.doctors_name.split()
        return parts[-1] if parts else ''
    
    @property
    def is_active_consultant(self):
        return 'Yes' if self.active else 'No'
    
    @property
    def ewtrate_pct(self):
        return f"{self.ewtrate}%"

    class Meta:
        managed = False
        db_table = 'emddoctors'

    def __str__(self):
        return self.doctors_name or 'Unknown Doctor'

class Patient(models.Model):
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    dob = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class PFTransaction(models.Model):
    doctor = models.ForeignKey(EmdDoctor, on_delete=models.CASCADE, related_name='transactions')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    reference = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.date} - {self.doctor.doctors_name} - {self.amount}"

class StatementOfAccount(models.Model):
    doctor = models.ForeignKey(EmdDoctor, on_delete=models.CASCADE, related_name='statements')
    start_date = models.DateField()
    end_date = models.DateField()
    filtered_total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Statement of Account'
        verbose_name_plural = 'Statements of Account'

    def __str__(self):
        return f"SOA: {self.doctor.doctors_name} ({self.start_date} - {self.end_date})"

class ReleasedCheck(models.Model):
    checkno = models.CharField(max_length=50, primary_key=True)
    checkdate = models.DateField()
    releasedate = models.DateField(db_column='releasedate', null=True, blank=True)

    payee = models.CharField(max_length=255)
    vendorname = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    bankname = models.CharField(max_length=100)

    # New columns added to the releasedchecks table
    remarks = models.CharField(max_length=255, blank=True, null=True, db_column='Remarks')
    admissiontype = models.CharField(max_length=50, blank=True, null=True, db_column='AdmissionType')
    admissionno = models.CharField(max_length=50, blank=True, null=True, db_column='AdmissionNo')
    status = models.CharField(max_length=50, blank=True, null=True, db_column='Status')
    patientname = models.CharField(max_length=255, blank=True, null=True, db_column='PatientName')
    patientnameinitials = models.CharField(max_length=50, blank=True, null=True, db_column='PatientName_Initials')
    remarkcategory = models.CharField(max_length=255, blank=True, null=True, db_column='RemarkCategory')
    remarkdetail = models.CharField(max_length=255, blank=True, null=True, db_column='RemarkDetail')

    class Meta:
        managed = False
        db_table = 'releasedchecks'

    def __str__(self):
        return f"{self.checkno} - {self.payee} - ₱{self.amount}"

class UnreleasedCheck(models.Model):
    payeename = models.CharField('Payee Name', max_length=255, primary_key=True)
    checkno = models.CharField('Check No', max_length=50)
    checkdate = models.DateField('Check Date')
    monthvalue = models.CharField('Month Value', max_length=50)
    amount = models.DecimalField('Amount', max_digits=12, decimal_places=2)
    monthnumeric = models.CharField('Month Numeric', max_length=20)

    # New columns added to the unissuedchecks table
    remarks = models.CharField(max_length=255, blank=True, null=True, db_column='Remarks')
    admissiontype = models.CharField(max_length=50, blank=True, null=True, db_column='AdmissionType')
    admissionno = models.CharField(max_length=50, blank=True, null=True, db_column='AdmissionNo')
    status = models.CharField(max_length=50, blank=True, null=True, db_column='Status')
    patientname = models.CharField(max_length=255, blank=True, null=True, db_column='PatientName')
    patientnameinitials = models.CharField(max_length=50, blank=True, null=True, db_column='PatientName_Initials')
    remarkcategory = models.CharField(max_length=255, blank=True, null=True, db_column='RemarkCategory')
    remarkdetail = models.CharField(max_length=255, blank=True, null=True, db_column='RemarkDetail')

    class Meta:
        managed = False
        db_table = 'unissuedchecks'

    def __str__(self):
        return f"{self.checkno} - {self.payeename} - ₱{self.amount}"


class OutstandingPayable(models.Model):
    docno = models.CharField('Doc No', max_length=100, primary_key=True)
    docdate = models.DateField('Doc Date')
    duedate = models.DateField('Due Date')
    settlementdate = models.DateField('Settlement Date', null=True, blank=True)
    doctype = models.CharField('Doc Type', max_length=50)
    Vendor = models.CharField('Vendor', max_length=255)
    amount = models.DecimalField('Amount', max_digits=12, decimal_places=2)
    paymentsadjustments = models.DecimalField('Payments Adjustment', max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField('Balance', max_digits=12, decimal_places=2)
    remarks = models.TextField(blank=True)
    PFRFtype = models.CharField('PFRF Type', max_length=50)
    documentstatus = models.CharField('Document Status', max_length=50)

    # New columns added to outstandingpayables table
    admissiontype = models.CharField(max_length=50, blank=True, null=True, db_column='AdmissionType')
    admissionno = models.CharField(max_length=50, blank=True, null=True, db_column='AdmissionNo')
    status = models.CharField(max_length=50, blank=True, null=True, db_column='Status')
    patientname = models.CharField(max_length=255, blank=True, null=True, db_column='PatientName')
    patientnameinitials = models.CharField(max_length=50, blank=True, null=True, db_column='PatientName_Initials')
    remarkdetail = models.CharField(max_length=255, blank=True, null=True, db_column='RemarkDetail')

    class Meta:
        managed = False
        db_table = 'outstandingpayables'

    def __str__(self):
        return f"{self.docno} - {self.Vendor} - ₱{self.balance}"

class APV(models.Model):
    ap_voucher_no = models.CharField('AP Voucher No', max_length=50, primary_key=True)
    ap_voucher_date = models.DateField('AP Voucher Date')
    ap_category = models.CharField('AP Category', max_length=100, blank=True)
    supplier_type = models.CharField('Supplier Type', max_length=100, blank=True)
    payee_name = models.CharField('Payee Name', max_length=255, blank=True)
    amount = models.DecimalField('Amount', max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField('Discount Amount', max_digits=12, decimal_places=2, default=0)
    ewt_rate = models.DecimalField('EWT Rate', max_digits=8, decimal_places=2, default=0)
    ewt_amount = models.DecimalField('EWT Amount', max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField('Net Amount', max_digits=12, decimal_places=2)
    balance = models.DecimalField('Balance', max_digits=12, decimal_places=2)
    remarks_notes = models.TextField('Remarks/Notes', blank=True)
    posted_by = models.CharField('Posted By', max_length=255, blank=True)

    class Meta:
        managed = False
        db_table = 'apv'

    def __str__(self):
        return f"{self.ap_voucher_no} - {self.payee_name} - ₱{self.net_amount}"

class CheckReport(models.Model):
    voucherno = models.CharField(max_length=50, primary_key=True)
    voucherdate = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    cvtype = models.CharField(max_length=50, blank=True)
    cashamount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    checkamount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ewtamount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payto = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    apvno = models.CharField(max_length=50, blank=True)
    apvdate = models.DateField(null=True, blank=True)
    duedate = models.DateField(null=True, blank=True)
    netamount = models.DecimalField(max_digits=12, decimal_places=2)
    accountno = models.CharField(max_length=50, blank=True)
    acctdesc = models.CharField(max_length=255, blank=True)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    banks = models.CharField(max_length=100, blank=True)
    checkno = models.CharField(max_length=50, blank=True)
    checkdate = models.DateField(null=True, blank=True)
    checkamt = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    convertion = models.CharField(max_length=50, blank=True)
    cvcategory = models.CharField(max_length=50, blank=True)
    remarks = models.TextField(blank=True)
    invcno = models.CharField(max_length=50, blank=True)
    remarksapv = models.TextField(blank=True)
    releasedate = models.DateField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'check_report'

    def __str__(self):
        return f"{self.voucherno} - {self.payto} - ₱{self.netamount}"
