from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import EmdDoctor, Patient, PFTransaction, StatementOfAccount, UserProfile

class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, label='First Name')
    last_name = forms.CharField(max_length=150, label='Last Name')
    email = forms.EmailField(max_length=254, help_text='Required. Enter a valid email address.')
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, label='Role')
    specialty = forms.CharField(max_length=255, label='Specialty', required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'role', 'specialty')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_staff = True
        if self.cleaned_data['role'] == 'admin':
            user.is_superuser = True
        if commit:
            user.save()
            UserProfile.objects.get_or_create(user=user, defaults={'role': self.cleaned_data['role']})
            if self.cleaned_data['role'] == 'doctor':
                specialty = self.cleaned_data.get('specialty', 'General')
                # Will be handled by signals or views
        return user

# ===== EMD DOCTOR FORMS (Replaced DoctorForm) =====
class EmdDoctorForm(forms.ModelForm):
    # Core fields matching emddoctors table
    doctors_name = forms.CharField(max_length=255, label='Doctor Name', widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name, First Name'}))
    smsplusmobileno = forms.CharField(max_length=30, label='Mobile No', widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '09xxxxxxxxx'}))
    tin = forms.CharField(max_length=15, label='TIN', widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'TIN Number'}))
    prctype = forms.CharField(max_length=10, label='PRC Type', required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    prcno = forms.CharField(max_length=15, label='PRC No', required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    prcexpdate = forms.DateField(label='PRC Expiry', required=False, widget=forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}))
    phicno = forms.CharField(max_length=40, label='PHIC No', required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    phicexpdate = forms.DateField(label='PHIC Expiry', required=False, widget=forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}))
    pmccno = forms.CharField(max_length=20, label='PMCC No', required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    bankacctname = forms.CharField(max_length=125, label='Bank Account Name', required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    bankacctno = forms.CharField(max_length=20, label='Bank Account No', required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    dctrcategory = forms.CharField(max_length=10, label='Category', required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    specialization = forms.CharField(max_length=500, label='Specialization', widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Specialty'}))

    class Meta:
        model = EmdDoctor
        fields = ['doctors_name', 'smsplusmobileno', 'tin', 'prctype', 'prcno', 'prcexpdate', 'phicno', 'phicexpdate', 'pmccno', 'doctorsid', 'bankacctname', 'bankacctno', 's2no', 's2expirydate', 'dctrcategory', 'specialization', 'classcode', 'ewtrate']
        exclude = ['user', 'active', 'fk_psphicpfgroup', 'phicissuancedate', 'vatcondition', 'service_type', 'specialize', 'pk_emddoctors']
        widgets = {
            'doctors_name': forms.TextInput(attrs={'class': 'form-input'}),
            'smsplusmobileno': forms.TextInput(attrs={'class': 'form-input'}),
            'tin': forms.TextInput(attrs={'class': 'form-input'}),
            'prctype': forms.TextInput(attrs={'class': 'form-input'}),
            'prcno': forms.TextInput(attrs={'class': 'form-input'}),
            'prcexpdate': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'phicno': forms.TextInput(attrs={'class': 'form-input'}),
            'phicexpdate': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'pmccno': forms.TextInput(attrs={'class': 'form-input'}),
            'bankacctname': forms.TextInput(attrs={'class': 'form-input'}),
            'bankacctno': forms.TextInput(attrs={'class': 'form-input'}),
            'dctrcategory': forms.TextInput(attrs={'class': 'form-input'}),
            'specialization': forms.TextInput(attrs={'class': 'form-input'}),
            'classcode': forms.TextInput(attrs={'class': 'form-input'}),
            'ewtrate': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['smsplusmobileno'].required = True
        self.fields['tin'].required = True

# Compatible self-doctor form
class EmdDoctorSelfForm(forms.ModelForm):
    class Meta(EmdDoctorForm.Meta):
        exclude = EmdDoctorForm.Meta.exclude + ['doctorsid', 's2no', 's2expirydate']

# ===== OTHER FORMS (unchanged model refs updated) =====
class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['first_name', 'last_name', 'dob', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}),
            'dob': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Phone Number'}),
        }

class PFTransactionForm(forms.ModelForm):
    class Meta:
        model = PFTransaction
        fields = ['doctor', 'patient', 'amount', 'date', 'reference']
        widgets = {
            'doctor': forms.Select(attrs={'class': 'form-input'}),
            'patient': forms.Select(attrs={'class': 'form-input'}),
            'amount': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Amount', 'step': '0.01'}),
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'reference': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Reference (optional)'}),
        }

class StatementOfAccountForm(forms.ModelForm):
    class Meta:
        model = StatementOfAccount
        fields = ['doctor', 'start_date', 'end_date', 'filtered_total']
        widgets = {
            'doctor': forms.Select(attrs={'class': 'form-input'}),
            'start_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'filtered_total': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Total', 'step': '0.01'}),
        }

