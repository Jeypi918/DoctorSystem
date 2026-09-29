from django import forms
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from django.db.models import OuterRef, Subquery
from .models import EmdDoctor, Patient, PFTransaction, StatementOfAccount, UserProfile


def doctor_records_with_accounts():
    account_username = User.objects.filter(pk=OuterRef('doctorsid')).values('username')[:1]
    return EmdDoctor.objects.annotate(
        linked_account_username=Subquery(account_username),
    ).order_by('doctors_name')


class DoctorRecordChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, doctor):
        details = [f"ID {doctor.pk_emddoctors}"]
        if doctor.prcno:
            details.append(f"PRC {doctor.prcno}")
        if doctor.email:
            details.append(doctor.email)
        if not doctor.active:
            details.append('Inactive')
        return f"{doctor.doctors_name} ({' | '.join(details)})"


class ManagedUserCreateForm(forms.ModelForm):
    role = forms.ChoiceField(choices=[('', 'Select role')] + UserProfile.ROLE_CHOICES)
    doctor = DoctorRecordChoiceField(queryset=EmdDoctor.objects.none(), required=False)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['doctor'].queryset = doctor_records_with_accounts()
        self.fields['doctor'].label = 'Doctor record'
        self.fields['doctor'].help_text = 'All doctor records are listed. Records linked to another account cannot be selected.'
        self.fields['doctor'].widget.attrs['class'] = 'form-input'
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-input'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_unusable_password()
        if commit:
            user.save()
        return user

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('role') == 'doctor' and not cleaned_data.get('doctor'):
            self.add_error('doctor', 'Select the existing doctor record for this account.')
        elif cleaned_data.get('role') != 'doctor' and cleaned_data.get('doctor'):
            self.add_error('doctor', 'Only doctor accounts can be linked to a doctor record.')
        return cleaned_data


class ManagedUserUpdateForm(forms.ModelForm):
    role = forms.ChoiceField(choices=[('', 'Select role')])
    doctor = DoctorRecordChoiceField(queryset=EmdDoctor.objects.none(), required=False)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = [('', 'Select role')] + UserProfile.ROLE_CHOICES
        self.fields['doctor'].label = 'Doctor record'
        self.fields['doctor'].queryset = doctor_records_with_accounts()
        self.fields['doctor'].help_text = 'All doctor records are listed. Records linked to another account cannot be selected.'
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-input'
        try:
            self.fields['role'].initial = self.instance.userprofile.role
        except UserProfile.DoesNotExist:
            pass
        linked_doctor = EmdDoctor.objects.filter(doctorsid=self.instance.pk).order_by('pk_emddoctors').first()
        if linked_doctor:
            self.fields['doctor'].initial = linked_doctor

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('role') == 'doctor' and not cleaned_data.get('doctor'):
            self.add_error('doctor', 'Select the existing doctor record for this account.')
        elif cleaned_data.get('role') != 'doctor' and cleaned_data.get('doctor'):
            self.add_error('doctor', 'Only doctor accounts can be linked to a doctor record.')
        return cleaned_data


class ManagedUserPasswordForm(SetPasswordForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-input'

# ===== EMD DOCTOR FORMS =====
class EmdDoctorForm(forms.ModelForm):
    doctors_name = forms.CharField(max_length=255, label='Doctor Name', widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last, First Name'}))
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
    specialization = forms.CharField(max_length=500, label='Specialization', widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g., Obstetrics & Gynecology'}))

    class Meta:
        model = EmdDoctor
        fields = ['doctors_name', 'smsplusmobileno', 'tin', 'prctype', 'prcno', 'prcexpdate', 'phicno', 'phicexpdate', 'pmccno', 'doctorsid', 'bankacctname', 'bankacctno', 's2no', 's2expirydate', 'dctrcategory', 'specialization', 'birthdate', 'classcode', 'ewtrate']
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
            'birthdate': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['smsplusmobileno'].required = True
        self.fields['tin'].required = True

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

