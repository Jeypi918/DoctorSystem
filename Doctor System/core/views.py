from datetime import datetime, date
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
from .models import EmdDoctor, Patient, PFTransaction, StatementOfAccount, UserProfile, ReleasedCheck, UnreleasedCheck, OutstandingPayable, APV, CheckReport, Patientlist

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
            profile, created = UserProfile.objects.get_or_create(user=user)
            role_value = form.cleaned_data['role']
            print(f"DEBUG: Setting role '{role_value}' (type {type(role_value)}) for user '{user.username}' (profile created: {created})")
            profile.role = role_value
            profile.save()
            print(f"DEBUG: Profile saved. Final role: '{profile.role}'")
            # Verify DB
            profile.refresh_from_db()
            print(f"DEBUG: After refresh role: '{profile.role}'")
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
def get_current_doctor(request):
    """Resolve the logged-in doctor profile from the doctor username.

    Recent reset scheme uses a linked doctorsid and username like:
      LASTNAME + FIRSTINITIAL (Title case last name, uppercase initial)
      Example: "AbbariaoA".

    Legacy parsing still supports older username formats such as:
      LASTNAME + MMYY or LASTNAME + pk_emddoctors.
    """
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'doctor':
        print(f"get_current_doctor: Role check failed for {request.user.username}")
        return None

    username = (request.user.username or '').strip()
    print(f"get_current_doctor DEBUG: username='{username}'")
    if not username:
        return None

    # Prefer a direct user-to-doctor link when available.
    linked_doctors = list(EmdDoctor.objects.filter(doctorsid=request.user.id, active=True))
    import re

    def username_matches_doctor(username, doctor):
        m2 = re.match(r'^(?P<lastname>[A-Za-z]+)(?P<initial>[A-Z])?$', username)
        if not m2:
            return False
        username_lastname = m2.group('lastname').lower()
        username_initial = m2.group('initial')
        doctor_lastname = (doctor.last_name or '').strip().lower()
        if doctor_lastname != username_lastname:
            return False
        if username_initial:
            doctor_first_initial = ((doctor.first_name or '').strip()[:1] or '').upper()
            return doctor_first_initial == username_initial
        return True

    if linked_doctors:
        for d in linked_doctors:
            if username_matches_doctor(username, d):
                return d

        if len(linked_doctors) == 1:
            print(f"get_current_doctor: linked doctor mismatch for {username}, falling back to username-based lookup")
        else:
            print(f"get_current_doctor: duplicate doctorsid found for {username}, but no linked doctor matched username; falling back to general lookup")

    m = re.match(r'^(?P<prefix>.+?)(?P<digits>\d{4,6})$', username)
    if m:
        prefix = m.group('prefix').strip().upper()
        digits = m.group('digits')

        # First try: interpret trailing digits as MMYY (use last 4 digits)
        mm_yy = digits[-4:]
        try:
            month = int(mm_yy[:2])
            year2 = int(mm_yy[2:])
        except ValueError:
            month = None
            year2 = None

        if month and 1 <= month <= 12:
            candidates = EmdDoctor.objects.filter(active=True, prcexpdate__isnull=False, prcexpdate__month=month)
            candidates = [d for d in candidates if d.prcexpdate and (d.prcexpdate.year % 100) == year2]

            for d in candidates:
                name = (d.doctors_name or '').strip()
                last_token = name.split(',', 1)[0].strip().upper() if ',' in name else name.split()[0].strip().upper()
                if last_token == prefix:
                    return d

        # Legacy fallback: LASTNAME + pk_emddoctors (original scheme)
        try:
            doctor_pk = int(digits)
            candidates = EmdDoctor.objects.filter(active=True, pk_emddoctors=doctor_pk)
            for cand in candidates:
                if prefix.lower() in cand.doctors_name.lower():
                    return cand
        except ValueError:
            pass

    # New username format without trailing digits: LASTNAME + FIRSTINITIAL
    username_match = re.match(r'^(?P<lastname>[A-Za-z]+)(?P<initial>[A-Z])$', username)
    if username_match:
        username_lastname = username_match.group('lastname').strip().lower()
        username_initial = username_match.group('initial')
        candidates = EmdDoctor.objects.filter(active=True)
        for d in candidates:
            doctor_lastname = (d.last_name or '').strip().lower()
            doctor_first_initial = ((d.first_name or '').strip()[:1] or '').upper()
            if doctor_lastname == username_lastname and doctor_first_initial == username_initial:
                return d

    # Fallback: match lastname only if possible
    username_lastname_only = re.match(r'^(?P<lastname>[A-Za-z]+)$', username)
    if username_lastname_only:
        username_lastname = username_lastname_only.group('lastname').strip().lower()
        candidate = EmdDoctor.objects.filter(active=True).filter(doctors_name__istartswith=username_lastname).first()
        if candidate:
            return candidate

    # Final fallback
    fallback = EmdDoctor.objects.filter(active=True).first()
    print(f"FALLBACK to {fallback.doctors_name if fallback else 'NONE'} for {username}")
    return fallback



@login_required(login_url='login')
def home_view(request):
    my_doctor = get_current_doctor(request)
    
    doctor_count = EmdDoctor.objects.count()
    if my_doctor:
        patient_count = Patientlist.objects.filter(doctors_code=str(my_doctor.pk_emddoctors)).count()
    else:
        patient_count = Patientlist.objects.count()
    
    if my_doctor:
        released_count = ReleasedCheck.objects.filter(
            Q(payee__icontains=my_doctor.doctors_name) | Q(vendorname__icontains=my_doctor.doctors_name)
        ).count()
        unreleased_count = UnreleasedCheck.objects.filter(payeename__icontains=my_doctor.doctors_name).count()
        outstanding_count = OutstandingPayable.objects.filter(Vendor__icontains=my_doctor.doctors_name).count()
        apv_count = APV.objects.filter(payee_name__icontains=my_doctor.doctors_name).count()
        check_report_count = CheckReport.objects.filter(payto__icontains=my_doctor.doctors_name).count()
    else:
        released_count = ReleasedCheck.objects.count()
        unreleased_count = UnreleasedCheck.objects.count()
        outstanding_count = OutstandingPayable.objects.count()
        apv_count = APV.objects.count()
        check_report_count = CheckReport.objects.count()
    
    if my_doctor:
        pf_total = released_count + unreleased_count + outstanding_count
    else:
        pf_total = released_count + unreleased_count + outstanding_count + apv_count + check_report_count
    transaction_count = pf_total
    statement_count = StatementOfAccount.objects.count()

    # Compute welcome display for doctors - Proper case: Dr. Initial Lastname
    try:
        if hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'doctor' and my_doctor:
            first_name = (getattr(my_doctor, 'first_name', '') or '').strip()
            last_name = (getattr(my_doctor, 'last_name', '') or '').strip()

            initial = first_name[0].upper() if first_name else ''
            lastname_proper = last_name.title() if last_name else ''

            
            if initial and lastname_proper:
                welcome_display = f"Dr. {initial}. {lastname_proper} "
            elif lastname_proper:
                welcome_display = f"Dr. {lastname_proper}"
            else:
                welcome_display = request.user.username
        else:
            welcome_display = request.user.username
    except AttributeError:
        welcome_display = request.user.username


    return render(request, 'home.html', {
        'doctor_count': doctor_count,
        'patient_count': patient_count,
        'transaction_count': transaction_count,
        'statement_count': statement_count,
        'welcome_display': welcome_display,
    })

# ===== DOCTOR VIEWS =====
class DoctorListView(ListView):
    model = EmdDoctor
    template_name = 'doctors_list.html'
    context_object_name = 'doctors'
    paginate_by = 25
    
    @method_decorator(login_required(login_url='login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset().order_by('doctors_name')
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(pk_emddoctors__icontains=q) |
                Q(doctors_name__icontains=q) |
                Q(category__icontains=q) |
                Q(specialization__icontains=q) |
                Q(phicno__icontains=q)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_params = self.request.GET.copy()
        query_params.pop('page', None)
        context['query_params'] = query_params.urlencode()
        paginator = context['paginator']
        page_number = context['page_obj'].number
        context['page_range'] = [1] + list(range(max(2, page_number - 2), min(paginator.num_pages + 1, page_number + 3))) + [paginator.num_pages] if paginator.num_pages > 5 else list(range(1, paginator.num_pages + 1))
        return context

@login_required(login_url='login')
def doctor_detail_view(request, pk):
    doctor = get_object_or_404(EmdDoctor, pk_emddoctors=pk)
    transactions = PFTransaction.objects.filter(doctor=doctor)
    return render(request, 'doctor_detail.html', {'doctor': doctor, 'transactions': transactions})

@login_required(login_url='login')
@staff_required
def doctor_reset_password_view(request, pk):
    doctor = get_object_or_404(EmdDoctor, pk_emddoctors=pk)

    # New reset scheme:
    #   username seed: LASTNAME + FIRSTINITIAL (Title case last name, uppercase initial)
    #   password seed: LASTNAME + birthdate MMYY
    #   Example: "Abbariao, Anne" + birthdate=1999-05-14 => username=AbbariaoA password=Abbariao0599

    if not doctor.prcno:
        return render(request, 'confirm_reset.html', {
            'doctor': doctor, 'error': 'PRC No required for reset.'
        })

    lastname_token = (doctor.last_name or '').strip()
    firstname_token = (doctor.first_name or '').strip()
    lastname_title = lastname_token.title() if lastname_token else 'Doctor'
    first_initial = firstname_token[:1].upper() if firstname_token else ''

    birthdate = None
    if doctor.birthdate:
        if isinstance(doctor.birthdate, str):
            for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y', '%d/%m/%Y'):
                try:
                    birthdate = datetime.strptime(doctor.birthdate.strip(), fmt).date()
                    break
                except ValueError:
                    continue
        elif isinstance(doctor.birthdate, datetime):
            birthdate = doctor.birthdate.date()
        else:
            birthdate = doctor.birthdate

    if birthdate:
        suffix = f"{birthdate.month:02d}{birthdate.year % 100:02d}"
        password = f"{lastname_title}{suffix}"
    else:
        # If birthdate is missing or invalid, keep legacy fallback to avoid breaking resets.
        password = f"{lastname_title}{doctor.pk_emddoctors}"

    username = f"{lastname_title}{first_initial}"

    # Get or create User
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'is_staff': True, 'is_active': True}
    )
    if created:
        user.set_unusable_password()

    # Ensure profile
    UserProfile.objects.get_or_create(
        user=user, defaults={'role': 'doctor'}
    )

    # Link doctorsid
    doctor.doctorsid = user.id
    doctor.save(update_fields=['doctorsid'])

    # IMPORTANT: do not reset until the confirmation POST.
    if request.method == 'POST':
        # Only perform the reset if user clicked the confirm button.
        if request.POST.get('confirm_reset') != '1':
            return render(request, 'confirm_reset.html', {
                'doctor': doctor,
                'username': username,
                'new_password': password,
            })

        # Update username/email/name to match doctor account expectations.
        if username:
            user.username = username

        user.first_name = getattr(doctor, 'first_name', '') or ''
        user.last_name = getattr(doctor, 'last_name', '') or ''

        # If you store doctor email in emddoctors column, this will set it.
        # (If the column doesn't exist, it will silently ignore due to getattr.)
        email_value = getattr(doctor, 'email_doctors', None) or getattr(doctor, 'email', None)
        if email_value:
            user.email = email_value

        user.set_password(password)
        user.save()
        messages.success(request, f'Reset for {doctor.doctors_name}. Username: {username} Password: {password}')
        return redirect('doctor_detail', pk=pk)


    return render(request, 'confirm_reset.html', {
        'doctor': doctor,
        'username': username,
        'new_password': password,
    })

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
    my_doctor = get_current_doctor(request)
    if not my_doctor:
        return render(request, 'doctor_self.html', {'error': 'No doctor profile found. Contact admin.', 'debug_username': request.user.username})
    
    print(f"my_doctor_view CONFIRMED: {my_doctor.doctors_name} (pk {my_doctor.pk_emddoctors}) for {request.user.username}")

    transactions = PFTransaction.objects.filter(doctor=my_doctor)
    patients = Patient.objects.filter(pftransaction__doctor=my_doctor).distinct()
    soa_list = StatementOfAccount.objects.filter(doctor=my_doctor).order_by('-start_date')

    print(f"DEBUG: transactions.count() = {transactions.count()}")
    print(f"DEBUG: First 3 transactions doctors: {list(transactions.values('doctor')[:3])}")
    print(f"DEBUG: my_doctor = {my_doctor.doctors_name}")

    # Connected patients should also include names from report entries
    released_report_patients = list(ReleasedCheck.objects.filter(
        Q(payee__icontains=my_doctor.doctors_name) | Q(vendorname__icontains=my_doctor.doctors_name)
    ).exclude(patientname__isnull=True).exclude(patientname__exact='').values('patientname', 'discharge_date'))
    unreleased_report_patients = list(UnreleasedCheck.objects.filter(
        payeename__icontains=my_doctor.doctors_name
    ).exclude(patientname__isnull=True).exclude(patientname__exact='').values('patientname', 'discharge_date'))

    report_patients_raw = released_report_patients + unreleased_report_patients
    pf_patient_names = {f"{p.first_name} {p.last_name}".strip() for p in patients}
    seen_report_patients = set()
    report_patients = []

    def initials_last_name(name):
        if not name:
            return ''

        normalized_name = name.strip()
        if ',' in normalized_name:
            last_name, first_parts = normalized_name.split(',', 1)
            last_name = last_name.strip()
            initials = []
            for part in first_parts.replace('.', ' ').split():
                if part:
                    initials.append(f"{part[0].upper()}.")
            return f"{last_name}, {' '.join(initials)}" if initials else last_name

        parts = normalized_name.split()
        if len(parts) == 1:
            return parts[0]

        last_name = parts[-1]
        initials = [f"{part[0].upper()}." for part in parts[:-1] if part]
        return f"{last_name}, {' '.join(initials)}" if initials else last_name

    for report in report_patients_raw:
        patient_name = report['patientname'].strip()
        if not patient_name or patient_name in pf_patient_names:
            continue

        discharge_date = report.get('discharge_date')
        key = (patient_name, discharge_date)
        if key in seen_report_patients:
            continue
        seen_report_patients.add(key)
        report_patients.append({
            'patient_name': patient_name,
            'display_name': initials_last_name(patient_name),
            'discharge_date': discharge_date,
        })

    def normalize_discharge_date(dt):
        if not dt:
            return date.min
        if isinstance(dt, datetime):
            return dt.date()
        return dt

    report_patients = sorted(
        report_patients,
        key=lambda r: normalize_discharge_date(r['discharge_date']),
        reverse=True,
    )

    patient_count = Patientlist.objects.filter(doctors_code=str(my_doctor.pk_emddoctors)).count()
    transaction_count = transactions.count()

    # Match home_view PF total logic for consistency
    released_count = ReleasedCheck.objects.filter(
        Q(payee__icontains=my_doctor.doctors_name) | Q(vendorname__icontains=my_doctor.doctors_name)
    ).count()
    unreleased_count = UnreleasedCheck.objects.filter(payeename__icontains=my_doctor.doctors_name).count()
    outstanding_count = OutstandingPayable.objects.filter(Vendor__icontains=my_doctor.doctors_name).count()
    apv_count = APV.objects.filter(payee_name__icontains=my_doctor.doctors_name).count()
    check_report_count = CheckReport.objects.filter(payto__icontains=my_doctor.doctors_name).count()
    pf_total = released_count + unreleased_count + outstanding_count
    transaction_count = pf_total
    statement_count = soa_list.count()


    print(f"DEBUG: patient_count={patient_count}, transaction_count(PF total)={transaction_count}, statement_count={statement_count}")

    # Recent PF reports from Released Check and Unreleased Checks for this doctor
    released_pf_reports = ReleasedCheck.objects.filter(
        Q(payee__icontains=my_doctor.doctors_name) | Q(vendorname__icontains=my_doctor.doctors_name)
    ).order_by('-checkdate').values('checkno', 'checkdate')[:5]
    unreleased_pf_reports = UnreleasedCheck.objects.filter(
        payeename__icontains=my_doctor.doctors_name
    ).order_by('-checkdate').values('checkno', 'checkdate')[:5]

    recent_pf_reports = []
    for report in released_pf_reports:
        recent_pf_reports.append({
            'checkno': report['checkno'],
            'checkdate': report['checkdate'],
            'report_type': 'Released Check',
        })
    for report in unreleased_pf_reports:
        recent_pf_reports.append({
            'checkno': report['checkno'],
            'checkdate': report['checkdate'],
            'report_type': 'Unreleased Check',
        })

    recent_pf_reports = sorted(
        recent_pf_reports,
        key=lambda r: r['checkdate'] or '',
        reverse=True,
    )

    return render(request, 'doctor_self.html', {
        'doctor': my_doctor,
        'transactions': transactions,
        'patients': patients,
        'report_patients': report_patients,
        'soa_list': soa_list,
        'patient_count': patient_count,
        'transaction_count': transaction_count,
        'statement_count': statement_count,
        'recent_pf_reports': recent_pf_reports,
    })

# ===== PATIENT VIEWS =====
class PatientListView(ListView):
    model = Patientlist
    template_name = 'patients_list.html'
    context_object_name = 'patients'
    paginate_by = 10

    @method_decorator(doctor_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        doctor = get_current_doctor(self.request)
        if doctor:
            # Filter patients by doctor's code (assuming doctors_code is string of pk_emddoctors)
            queryset = queryset.filter(doctors_code=str(doctor.pk_emddoctors))

        q = self.request.GET.get('q', '').strip()
        date_from = self.request.GET.get('date_from', '').strip()
        date_to = self.request.GET.get('date_to', '').strip()
        patient_type = self.request.GET.get('patient_type', 'All').strip()

        if q:
            queryset = queryset.filter(
                Q(patient_name__icontains=q) |
                Q(patient_id__icontains=q) |
                Q(gender__icontains=q) |
                Q(doctor_name__icontains=q) |
                Q(doctors_code__icontains=q) |
                Q(citizenship__icontains=q) |
                Q(roomno__icontains=q) |
                Q(guarantors__icontains=q)
            )

        # Date filters apply to ADMISSION DateTime (registry_datetime)
        if date_from:
            queryset = queryset.filter(registry_datetime__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(registry_datetime__date__lte=date_to)

        if patient_type and patient_type.lower() != 'all':
            queryset = queryset.filter(patient_type__iexact=patient_type)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_params = self.request.GET.copy()
        query_params.pop('page', None)
        context['query_params'] = query_params.urlencode()
        context['patient_type_choices'] = ['All', 'Inpatient', 'Outpatient', 'Emergency']
        return context




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

    @method_decorator(login_required(login_url='login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        my_doctor = get_current_doctor(self.request)
        if my_doctor:
            context['released_count'] = ReleasedCheck.objects.filter(
                Q(payee__icontains=my_doctor.doctors_name) | Q(vendorname__icontains=my_doctor.doctors_name)
            ).count()
            context['unreleased_count'] = UnreleasedCheck.objects.filter(payeename__icontains=my_doctor.doctors_name).count()
            context['outstanding_count'] = OutstandingPayable.objects.filter(Vendor__icontains=my_doctor.doctors_name).count()
            context['apv_count'] = APV.objects.filter(payee_name__icontains=my_doctor.doctors_name).count()
            context['check_report_count'] = CheckReport.objects.filter(payto__icontains=my_doctor.doctors_name).count()
        else:
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
    paginate_by = 15

    @method_decorator(doctor_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-checkdate', 'checkno')
        
        my_doctor = get_current_doctor(self.request)
        if my_doctor:
            queryset = queryset.filter(
                Q(payee__icontains=my_doctor.doctors_name) | 
                Q(vendorname__icontains=my_doctor.doctors_name)
            )
        
        q = self.request.GET.get('q', '').strip()
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        if q:
            queryset = queryset.filter(
                Q(checkno__icontains=q) |
                Q(payee__icontains=q) |
                Q(vendorname__icontains=q) |
                Q(bankname__icontains=q) |
                Q(remarks__icontains=q) |
                Q(admissiontype__icontains=q) |
                Q(admissionno__icontains=q) |
                Q(status__icontains=q) |
                Q(patientname__icontains=q) |
                Q(patientnameinitials__icontains=q) |
                Q(remarkcategory__icontains=q) |
                Q(remarkdetail__icontains=q)
            )
        if date_from:
            queryset = queryset.filter(releasedate__gte=date_from)
        if date_to:
            queryset = queryset.filter(releasedate__lte=date_to)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_params = self.request.GET.copy()
        query_params.pop('page', None)
        context['query_params'] = query_params.urlencode()
        return context


class UnreleasedCheckListView(ListView):
    model = UnreleasedCheck
    template_name = 'unreleased_checks_list.html'
    context_object_name = 'unreleased_checks'
    paginate_by = 15

    @method_decorator(doctor_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-checkdate', 'checkno')
        
        my_doctor = get_current_doctor(self.request)
        if my_doctor:
            queryset = queryset.filter(payeename__icontains=my_doctor.doctors_name)
        
        q = self.request.GET.get('q', '').strip()
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        if q:
            queryset = queryset.filter(
                Q(payeename__icontains=q) |
                Q(checkno__icontains=q) |
                Q(monthvalue__icontains=q) |
                Q(remarks__icontains=q) |
                Q(admissiontype__icontains=q) |
                Q(admissionno__icontains=q) |
                Q(status__icontains=q) |
                Q(patientname__icontains=q) |
                Q(patientnameinitials__icontains=q) |
                Q(remarkcategory__icontains=q) |
                Q(remarkdetail__icontains=q) |
                Q(discharge_date__icontains=q)
            )
        if date_from:
            queryset = queryset.filter(checkdate__gte=date_from)
        if date_to:
            queryset = queryset.filter(checkdate__lte=date_to)
        discharge_from = self.request.GET.get('discharge_from')
        discharge_to = self.request.GET.get('discharge_to')
        if discharge_from:
            queryset = queryset.filter(discharge_date__date__gte=discharge_from)
        if discharge_to:
            queryset = queryset.filter(discharge_date__date__lte=discharge_to)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_params = self.request.GET.copy()
        query_params.pop('page', None)
        context['query_params'] = query_params.urlencode()
        return context


class OutstandingReportListView(ListView):
    model = OutstandingPayable
    template_name = 'outstanding_report.html'
    context_object_name = 'outstanding_payables'
    paginate_by = 15

    @method_decorator(doctor_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-duedate', 'docno')
        
        my_doctor = get_current_doctor(self.request)
        if my_doctor:
            queryset = queryset.filter(Vendor__icontains=my_doctor.doctors_name)
        
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
                Q(PFRFtype__icontains=q) |
                Q(admissiontype__icontains=q) |
                Q(admissionno__icontains=q) |
                Q(status__icontains=q) |
                Q(patientname__icontains=q) |
                Q(patientnameinitials__icontains=q) |
                Q(remarkdetail__icontains=q) |
                Q(discharge_date__icontains=q)
            )
        if date_from:
            queryset = queryset.filter(duedate__gte=date_from)
        if date_to:
            queryset = queryset.filter(duedate__lte=date_to)
        discharge_from = self.request.GET.get('discharge_from')
        discharge_to = self.request.GET.get('discharge_to')
        if discharge_from:
            queryset = queryset.filter(discharge_date__date__gte=discharge_from)
        if discharge_to:
            queryset = queryset.filter(discharge_date__date__lte=discharge_to)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_params = self.request.GET.copy()
        query_params.pop('page', None)
        context['query_params'] = query_params.urlencode()
        return context

class APVListView(ListView):
    model = APV
    template_name = 'apv_list.html'
    context_object_name = 'apvouchers'
    paginate_by = 15

    @method_decorator(doctor_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-ap_voucher_date', 'ap_voucher_no')
        
        my_doctor = get_current_doctor(self.request)
        if my_doctor:
            queryset = queryset.filter(payee_name__icontains=my_doctor.doctors_name)
        
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
        query_params = self.request.GET.copy()
        query_params.pop('page', None)
        context['query_params'] = query_params.urlencode()
        return context

class CheckReportListView(ListView):
    model = CheckReport
    template_name = 'check_report_list.html'
    context_object_name = 'check_reports'
    paginate_by = 15

    @method_decorator(doctor_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-voucherdate', 'voucherno')
        
        my_doctor = get_current_doctor(self.request)
        if my_doctor:
            queryset = queryset.filter(payto__icontains=my_doctor.doctors_name)
        
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
        query_params = self.request.GET.copy()
        query_params.pop('page', None)
        context['query_params'] = query_params.urlencode()
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

    @method_decorator(login_required(login_url='login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

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

