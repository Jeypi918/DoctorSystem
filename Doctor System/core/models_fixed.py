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


class Doctor(models.Model):
    # Only fields that exist in core_doctor table
    doctors_name = models.CharField(max_length=255, db_column='doctors_name')
    smsplusmobileno = models.CharField(max_length=20, blank=True)
    tin = models.CharField(max_length=20, blank=True)
    active = models.BooleanField(default=True)
    prctype = models.CharField(max_length=64, blank=True, db_column='PRCtype')
    prcno = models.CharField(max_length=64, blank=True)
    prcexpdate = models.DateField(null=True, blank=True)
    phicno = models.CharField(max_length=64, blank=True)
    phicexpdate = models.DateField(null=True, blank=True)
    pmccno = models.CharField(max_length=64, blank=True)
    doctorsid = models.CharField(max_length=64, blank=True)
    bankacctname = models.CharField(max_length=128, blank=True)
    bankacctno = models.CharField(max_length=64, blank=True)
    dctrcategory = models.CharField(max_length=64, blank=True)
    specialization = models.TextField(db_column='specialization', blank=True)

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile', null=True, blank=True)

    class Meta:
        db_table = 'core_doctor'
        managed = False

    def __str__(self):
        return self.doctors_name or 'Unknown Doctor'

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
        return ''

    @property
    def last_name(self):
        if ',' in self.doctors_name:
            return self.doctors_name.split(',', 1)[0].strip()
        return self.doctors_name

    @property
    def is_active_consultant(self):
        return 'Yes' if self.active else 'No'


class EmdDoctor(models.Model):
    """
    Read-only model for emddoctors table
    """
    pk_emddoctors = models.IntegerField(primary_key=True)
    doctors_name = models.CharField(max_length=255)
    smsplusmobileno = models.CharField(max_length=30, blank=True)
    tin = models.CharField(max_length=15, blank=True)
    active = models.BooleanField()
    prctype = models.CharField(max_length=10, blank=True)
    prcno = models.CharField(max_length=15, blank=True)
    prcexpdate = models.DateField(null=True, blank=True)
    phicno = models.CharField(max_length=40, blank=True)
    fk_psphicpfgroup = models.CharField(max_length=20, blank=True)
    phicexpdate = models.DateField(null=True, blank=True)
    pmccno = models.CharField(max_length=20, blank=True)
    doctorsid = models.IntegerField(blank=True)
    bankacctname = models.CharField(max_length=125, blank=True)
    bankacctno = models.CharField(max_length=20, blank=True)
    s2no = models.CharField(max_length=20, blank=True)
    s2expirydate = models.DateField(null=True, blank=True)
    dctrcategory = models.CharField(max_length=10, blank=True)
    classcode = models.CharField(max_length=2, blank=True)
    ewtrate = models.DecimalField(max_digits=8, decimal_places=2)
    vatcondition = models.CharField(max_length=1, blank=True)
    phicissuancedate = models.DateField(null=True, blank=True)
    specialization = models.TextField(blank=True)
    specialize = models.CharField(max_length=30, blank=True, db_column='specialize')
    service_type = models.TextField(blank=True)

    class Meta:
        managed = False
        db_table = 'emddoctors'

    def __str__(self):
        return self.doctors_name

    @property
    def full_name(self):
        return self.doctors_name

    @property
    def first_name(self):
        if ',' in self.doctors_name:
            parts = self.doctors_name.split(',', 1)[1].strip().split(maxsplit=1)
            return parts[0] if parts else ''
        return ''

    @property
    def last_name(self):
        if ',' in self.doctors_name:
            return self.doctors_name.split(',', 1)[0].strip()
        return self.doctors_name

    @property
    def is_active_consultant(self):
        return 'Yes' if self.active else 'No'

    @property
    def ewtrate_pct(self):
        return f"{self.ewtrate}%"


class Patient(models.Model):
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    dob = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class PFTransaction(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    reference = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.date} - {self.doctor} - {self.amount}"


class StatementOfAccount(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    filtered_total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Statement of Account'
        verbose_name_plural = 'Statements of Account'

    def __str__(self):
        return f"SOA: {self.doctors} ({self.start_date} - {self.end_date})"

