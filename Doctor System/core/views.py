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
from django.db.models import Q
from django.db import IntegrityError, connection
from .models import EmdDoctor, Patient, PFTransaction, StatementOfAccount, UserProfile, ReleasedCheck, UnreleasedCheck, OutstandingPayable, APV, CheckReport
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
    released_count = ReleasedCheck.objects.count()
    unreleased_count = UnreleasedCheck.objects.count()
    outstanding_count = OutstandingPayable.objects.count()
    apv_count = APV.objects.count()
    check_report_count = CheckReport.objects.count()
    pf_total = released_count + unreleased_count + outstanding_count + apv_count + check_report_count
    transaction_count = pf_total
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
    if doctor.user:
        user = doctor.user
        if request.method == 'POST':
            username = f"{doctor.first_name.lower().strip()}{doctor.last_name.lower().strip()}"
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

@doctor_required
def my_doctor_view(request):
    try:
        my_doctor = request.user.emd_doctor_profile
    except EmdDoctor.DoesNotExist:
        return render(request, 'doctor_self.html', {'error': 'No doctor profile found. Contact admin.'})

    transactions = PFTransaction.objects.filter(doctor=my_doctor)
    patients = Patient.objects.filter(pftransaction__doctor=my_doctor).distinct()
    soa_list = StatementOfAccount.objects.filter(doctor=my_doctor).order_by('-start_date')

    return render(request, 'doctor_self.html', {
        'doctor': my_doctor,
        'transactions': transactions,
        'patients': patients,
        'soa_list': soa_list,
    })

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['released_count'] = ReleasedCheck.objects.count()
        context['unreleased_count'] = UnreleasedCheck.objects.count()
        context['outstanding_count'] = OutstandingPayable.objects.count()
        context['apv_count'] = APV.objects.count()
        context['check_report_count'] = CheckReport.objects.count()
        return context

class ReleasedCheckListView(ListView):
    model = ReleasedCheck
    template_name = 'released_checks_list.html'
    context_object_name = 'released_checks'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        if q:
            queryset = queryset.filter(
                Q(checkno__icontains=q) |
                Q(payee__icontains=q) |
                Q(vendorname__icontains=q) |
                Q(bankname__icontains=q)
            )
        if date_from:
            queryset = queryset.filter(releasedate__gte=date_from)
        if date_to:
            queryset = queryset.filter(releasedate__lte=date_to)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query_params'] = self.request.GET.urlencode()
        return context

class UnreleasedCheckListView(ListView):
    model = UnreleasedCheck
    template_name = 'unreleased_checks_list.html'
    context_object_name = 'unreleased_checks'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        if q:
            queryset = queryset.filter(
                Q(payeename__icontains=q) |
                Q(checkno__icontains=q) |
                Q(monthvalue__icontains=q)
            )
        if date_from:
            queryset = queryset.filter(checkdate__gte=date_from)
        if date_to:
            queryset = queryset.filter(checkdate__lte=date_to)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query_params'] = self.request.GET.urlencode()
        return context


class OutstandingReportListView(ListView):
    model = OutstandingPayable
    template_name = 'outstanding_report.html'
    context_object_name = 'outstanding_payables'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        if q:
            queryset = queryset.filter(
                Q(docno__icontains=q) |
                Q(Vendor__icontains=q) |
                Q(doctype__icontains=q) |
                Q(documentstatus__icontains=q) |
                Q(remarks__icontains=q) |
                Q(PFRFtype__icontains=q)
            )
        if date_from:
            queryset = queryset.filter(duedate__gte=date_from)
        if date_to:
            queryset = queryset.filter(duedate__lte=date_to)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query_params'] = self.request.GET.urlencode()
        return context

class APVListView(ListView):
    model = APV
    template_name = 'apv_list.html'
    context_object_name = 'apvouchers'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        if q:
            queryset = queryset.filter(
                Q(ap_voucher_no__icontains=q) |
                Q(ap_category__icontains=q) |
                Q(supplier_type__icontains=q) |
                Q(payee_name__icontains=q) |
                Q(remarks_notes__icontains=q) |
                Q(posted_by__icontains=q)
            )
        if date_from:
            queryset = queryset.filter(ap_voucher_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(ap_voucher_date__lte=date_to)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query_params'] = self.request.GET.urlencode()
        return context

class CheckReportListView(ListView):
    model = CheckReport
    template_name = 'check_report_list.html'
    context_object_name = 'check_reports'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        if q:
            queryset = queryset.filter(
                Q(voucherno__icontains=q) |
                Q(payto__icontains=q) |
                Q(checkno__icontains=q) |
                Q(banks__icontains=q) |
                Q(remarks__icontains=q)
            )
        if date_from:
            queryset = queryset.filter(voucherdate__gte=date_from)
        if date_to:
            queryset = queryset.filter(voucherdate__lte=date_to)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query_params'] = self.request.GET.urlencode()
        return context

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
    check_report_count = CheckReport.objects.count()
    return render(request, 'accounting.html', {
        'total_transactions': total_transactions,
        'total_soa': total_soa,
        'doctor_count': doctor_count,
        'patient_count': patient_count,
        'check_report_count': check_report_count,
    })
