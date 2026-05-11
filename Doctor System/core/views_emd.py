from datetime import datetime
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.db import IntegrityError, connection
from .models import EmdDoctor, Patient, PFTransaction, StatementOfAccount, UserProfile
from .forms import SignUpForm, EmdDoctorForm, PatientForm, PFTransactionForm, StatementOfAccountForm
from .decorators import admin_required, doctor_required, billing_required, accounting_required

def staff_required(view_func):
    return user_passes_test(lambda user: user.is_staff, login_url='login')(view_func)

# ===== AUTHENTICATION VIEWS =====
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.update_or_create(user=user, defaults={'role': form.cleaned_data['role']})
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

# ===== DASHBOARD VIEW =====
@login_required(login_url='login')
def home_view(request):
    doctor_count = EmdDoctor.objects.count()
    patient_count = Patient.objects.count()
    transaction_count = PFTransaction.objects.count()
    statement_count = StatementOfAccount.objects.count()
    return render(request, 'home.html', {
        'doctor_count': doctor_count,
        'patient_count': patient_count,
        'transaction_count': transaction_count,
        'statement_count': statement_count,
    })

# ===== DOCTOR VIEWS =====
class DoctorListView(ListView):
    model = EmdDoctor
    template_name = 'doctors_list.html'
    context_object_name = 'doctors'
    paginate_by = 25

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = context['paginator']
        page_number = context['page_obj'].number
        context['page_range'] = [1] + list(range(max(2, page_number - 2), min(paginator.num_pages + 1, page_number + 3))) + [paginator.num_pages] if paginator.num_pages > 5 else list(range(1, paginator.num_pages + 1))
        return context

@login_required(login_url='login')
@staff_required
def doctor_detail_view(request, pk):
    doctor = get_object_or_404(EmdDoctor, pk_emddoctors=pk)
    transactions = PFTransaction.objects.filter(doctor=doctor)
    return render(request, 'doctor_detail.html', {'doctor': doctor, 'transactions': transactions})

@login_required(login_url='login')
@staff_required
def doctor_reset_password_view(request, pk):
    doctor = get_object_or_404(EmdDoctor, pk_emddoctors=pk)
    if doctor.doctorsid:
        try:
            user = User.objects.get(id=doctor.doctorsid)
        except User.DoesNotExist:
            user = None
        if request.method == 'POST':
            # New reset username/password scheme:
            # LASTNAME(uppercase, before comma) + MM + YY where prcexpdate is e.g. 2028-12-30 => 123028
            if not doctor.prcexpdate:
                # fallback to legacy behavior if missing
                lastname = doctor.last_name.strip().upper() if doctor.last_name else 'DOCTOR'
                username = f"{lastname}{doctor.pk_emddoctors}"
            else:
                lastname = doctor.doctors_name.split(',', 1)[0].strip().upper() if ',' in doctor.doctors_name else (doctor.last_name.strip().upper() if doctor.last_name else 'DOCTOR')
                suffix = f"{doctor.prcexpdate.month:02d}{doctor.prcexpdate.year % 100:02d}"
                username = f"{lastname}{suffix}"

            user.first_name = doctor.first_name or ''
            user.last_name = doctor.last_name or ''
            user.email = getattr(doctor, 'email_doctors', None) or getattr(doctor, 'email', None) or user.email
            user.set_password(username)
            user.save()
            messages.success(request, f'Password reset for {doctor}! New password: {username}')
            return redirect('doctor_detail', pk=pk)
        return render(request, 'confirm_reset.html', {
            'doctor': doctor,
            'new_password': f"{doctor.first_name.lower().strip()}{doctor.last_name.lower().strip()}"
        })
    else:
        messages.error(request, 'No user account linked to this doctor.')
        return redirect('doctors')

@login_required(login_url='login')
@staff_required
def doctor_create_view(request):
    if request.method == 'POST':
        form = EmdDoctorForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Doctor created successfully!')
                return redirect('doctors')
            except IntegrityError:
                form.add_error(None, 'Duplicate entry or constraint violation.')
            except Exception as e:
                form.add_error(None, f'Error: {str(e)}')
    else:
        form = EmdDoctorForm()
    return render(request, 'doctor_form.html', {'form': form, 'title': 'Add Doctor'})

@login_required(login_url='login')
@staff_required
def doctor_update_view(request, pk):
    doctor = get_object_or_404(EmdDoctor, pk_emddoctors=pk)
    if request.method == 'POST':
        form = EmdDoctorForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            return redirect('doctors')
    else:
        form = EmdDoctorForm(instance=doctor)
    return render(request, 'doctor_form.html', {'form': form, 'title': 'Edit Doctor', 'object': doctor})

@login_required(login_url='login')
@staff_required
def doctor_delete_view(request, pk):
    doctor = get_object_or_404(EmdDoctor, pk_emddoctors=pk)
    if request.method == 'POST':
        doctor.delete()
        return redirect('doctors')
    return render(request, 'confirm_delete.html', {'object': doctor, 'object_name': 'Doctor'})

def get_current_doctor_emd(request):
    """Match doctor profile using username format derived from prcexpdate.

    Username is expected to be:
      LASTNAME (uppercase, before comma) + MM + YY
    Example:
      "ABAD" + (prcexpdate=2028-12-30) => "ABAD1228"

    This replaces broad icontains matching that can mis-link users.
    """
    # Role check
    try:
        if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'doctor':
            return None
    except Exception:
        return None

    username = (request.user.username or '').strip()
    if not username:
        return None

    # Prefer a direct user-to-doctor link when available.
    linked_doctor = EmdDoctor.objects.filter(doctorsid=request.user.id, active=True).first()
    if linked_doctor:
        return linked_doctor

    import re
    # split into prefix letters + trailing digits
    m = re.match(r'^(?P<prefix>.+?)(?P<digits>\d{4,6})$', username)
    if not m:
        return EmdDoctor.objects.filter(active=True).first()

    prefix = m.group('prefix').strip().upper()
    digits = m.group('digits')

    # Interpret suffix as MMYY.
    # If digits is 4 => MMYY, if 5/6 => try last 4 as MMYY.
    mm_yy = digits[-4:]
    try:
        month = int(mm_yy[:2])
        year2 = int(mm_yy[2:])
    except ValueError:
        month = None
        year2 = None

    candidates = EmdDoctor.objects.all()
    if month and 1 <= month <= 12:
        # year2 matches prcexpdate.year % 100
        candidates = candidates.filter(prcexpdate__isnull=False).filter(prcexpdate__month=month)
        # year%100 filter via annotation isn't available in this project; do it in python safely.
        candidates = [d for d in candidates if d.prcexpdate and (d.prcexpdate.year % 100) == year2]

        # Match prefix against the LASTNAME token only.
        # doctors_name is expected like: "LASTNAME, Firstname ...".
        for d in candidates:
            name = (d.doctors_name or '').strip()
            last_token = name.split(',', 1)[0].strip().upper() if ',' in name else name.split()[0].strip().upper()
            if last_token == prefix:
                return d

    # Strict fallback: LASTNAME token exact match
    for d in EmdDoctor.objects.filter(active=True):
        name = (d.doctors_name or '').strip()
        last_token = name.split(',', 1)[0].strip().upper() if ',' in name else name.split()[0].strip().upper()
        if last_token == prefix:
            return d


    return EmdDoctor.objects.filter(active=True).first()


@doctor_required
def my_doctor_view(request):
    my_doctor = get_current_doctor_emd(request)
    if not my_doctor:
        return render(
            request,
            'doctor_self.html',
            {'error': 'No doctor profile found. Contact admin.', 'debug_username': request.user.username},
        )

    print(f'Matched {my_doctor.doctors_name} (ID {my_doctor.pk_emddoctors}) for {request.user.username}')

    transactions = PFTransaction.objects.filter(doctor=my_doctor)
    patients = Patient.objects.filter(pftransaction__doctor=my_doctor).distinct()
    soa_list = StatementOfAccount.objects.filter(doctor=my_doctor).order_by('-start_date')

    return render(
        request,
        'doctor_self.html',
        {
            'doctor': my_doctor,
            'transactions': transactions,
            'patients': patients,
            'soa_list': soa_list,
        },
    )

# ===== PATIENT VIEWS =====
class PatientListView(ListView):
    model = Patient
    template_name = 'patients_list.html'
    context_object_name = 'patients'
    paginate_by = 10

@login_required(login_url='login')
@staff_required
def patient_detail_view(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    transactions = PFTransaction.objects.filter(patient=patient)
    return render(request, 'patient_detail.html', {'patient': patient, 'transactions': transactions})

@login_required(login_url='login')
@staff_required
def patient_create_view(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('patients')
    else:
        form = PatientForm()
    return render(request, 'patient_form.html', {'form': form, 'title': 'Add Patient'})

@login_required(login_url='login')
@staff_required
def patient_update_view(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            return redirect('patients')
    else:
        form = PatientForm(instance=patient)
    return render(request, 'patient_form.html', {'form': form, 'title': 'Edit Patient', 'object': patient})

@login_required(login_url='login')
@staff_required
def patient_delete_view(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        patient.delete()
        return redirect('patients')
    return render(request, 'confirm_delete.html', {'object': patient, 'object_name': 'Patient'})

# ===== TRANSACTION VIEWS =====
class TransactionListView(ListView):
    model = PFTransaction
    template_name = 'transactions_list.html'
    context_object_name = 'transactions'
    paginate_by = 10

@login_required(login_url='login')
@staff_required
def transaction_create_view(request):
    if request.method == 'POST':
        form = PFTransactionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('transactions')
    else:
        form = PFTransactionForm()
    return render(request, 'transaction_form.html', {'form': form, 'title': 'Add Transaction'})

@login_required(login_url='login')
@staff_required
def transaction_update_view(request, pk):
    transaction = get_object_or_404(PFTransaction, pk=pk)
    if request.method == 'POST':
        form = PFTransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            return redirect('transactions')
    else:
        form = PFTransactionForm(instance=transaction)
    return render(request, 'transaction_form.html', {'form': form, 'title': 'Edit Transaction', 'object': transaction})

@login_required(login_url='login')
@staff_required
def transaction_delete_view(request, pk):
    transaction = get_object_or_404(PFTransaction, pk=pk)
    if request.method == 'POST':
        transaction.delete()
        return redirect('transactions')
    return render(request, 'confirm_delete.html', {'object': transaction, 'object_name': 'Transaction'})

# ===== STATEMENT OF ACCOUNT VIEWS =====
class SoaListView(ListView):
    model = StatementOfAccount
    template_name = 'statement_list.html'
    context_object_name = 'statements'
    paginate_by = 10

@login_required(login_url='login')
@staff_required
def statement_create_view(request):
    if request.method == 'POST':
        form = StatementOfAccountForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('statements')
    else:
        form = StatementOfAccountForm()
    return render(request, 'statement_form.html', {'form': form, 'title': 'Add Statement'})

@login_required(login_url='login')
@staff_required
def statement_update_view(request, pk):
    statement = get_object_or_404(StatementOfAccount, pk=pk)
    if request.method == 'POST':
        form = StatementOfAccountForm(request.POST, instance=statement)
        if form.is_valid():
            form.save()
            return redirect('statements')
    else:
        form = StatementOfAccountForm(instance=statement)
    return render(request, 'statement_form.html', {'form': form, 'title': 'Edit Statement', 'object': statement})

@login_required(login_url='login')
@staff_required
def statement_delete_view(request, pk):
    statement = get_object_or_404(StatementOfAccount, pk=pk)
    if request.method == 'POST':
        statement.delete()
        return redirect('statements')
    return render(request, 'confirm_delete.html', {'object': statement, 'object_name': 'Statement'})

@billing_required
def billing_view(request):
    soa_items = StatementOfAccount.objects.select_related('doctor').order_by('-created_at')
    transactions = PFTransaction.objects.select_related('doctor', 'patient').order_by('-date')
    patients = Patient.objects.all().order_by('last_name', 'first_name')
    return render(request, 'billing.html', {
        'soa_items': soa_items,
        'transactions': transactions,
        'patients': patients,
    })

@accounting_required
def accounting_view(request):
    from django.db.models import Sum
    total_transactions = PFTransaction.objects.aggregate(total=Sum('amount'))['total'] or 0
    total_soa = StatementOfAccount.objects.aggregate(total=Sum('filtered_total'))['total'] or 0
    doctor_count = EmdDoctor.objects.count()
    patient_count = Patient.objects.count()
    return render(request, 'accounting.html', {
        'total_transactions': total_transactions,
        'total_soa': total_soa,
        'doctor_count': doctor_count,
        'patient_count': patient_count,
    })

