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
    releasedate = models.CharField(max_length=20, null=True, blank=True)

    def get_releasedate_formatted(self):
        if self.releasedate:
            try:
                # Parse m/d/yyyy -> YYYY-MM-DD
                from datetime import datetime
                dt = datetime.strptime(self.releasedate, '%m/%d/%Y')
                return dt.strftime('%Y-%m-%d')
            except:
                pass
        return self.releasedate or '—'
    payee = models.CharField(max_length=255)
    vendorname = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    bankname = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'releasedchecks'

    def __str__(self):
        return f"{self.checkno} - {self.payee} - ₱{self.amount}"


