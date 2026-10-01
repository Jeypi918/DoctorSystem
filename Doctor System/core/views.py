from collections import defaultdict
from datetime import datetime, date
import secrets
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils import timezone
from django.db import IntegrityError, connection, transaction
from .models import EmdDoctor, Patient, PFTransaction, StatementOfAccount, UserProfile, ReleasedCheck, UnreleasedCheck, OutstandingPayable, APV, CheckReport, Patientlist

from .forms import ManagedUserCreateForm, ManagedUserUpdateForm, ManagedUserPasswordForm, EmdDoctorForm, PatientForm, PFTransactionForm, StatementOfAccountForm
from .decorators import admin_required, doctor_required, billing_required, accounting_required

def staff_required(view_func):
    return user_passes_test(lambda user: user.is_staff, login_url='login')(view_func)

# ===== AUTHENTICATION VIEWS =====
def signup_view(request):
    messages.info(request, 'Accounts are created by an administrator. Please contact your administrator.')
    return redirect('login')

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


def _doctor_temporary_password(doctor):
    if not doctor or not doctor.last_name or not doctor.birthdate:
        return None

    birthdate = doctor.birthdate
    if isinstance(birthdate, str):
        for date_format in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y', '%d/%m/%Y'):
            try:
                birthdate = datetime.strptime(birthdate.strip(), date_format).date()
                break
            except ValueError:
                continue
    elif isinstance(birthdate, datetime):
        birthdate = birthdate.date()

    if not isinstance(birthdate, date):
        return None

    return f"{doctor.last_name.strip().title()}{birthdate.month:02d}{birthdate.year:04d}"


def _issue_temporary_password(request, user, doctor=None):
    temporary_password = _doctor_temporary_password(doctor)
    uses_doctor_format = temporary_password is not None
    if temporary_password is None:
        temporary_password = secrets.token_urlsafe(18)
    user.set_password(temporary_password)
    user.save(update_fields=['password'])
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.must_change_password = True
    profile.save(update_fields=['must_change_password'])
    request.session[f'temporary_password_{user.pk}'] = temporary_password
    request.session[f'temporary_password_uses_doctor_format_{user.pk}'] = uses_doctor_format
    return redirect('user_management_temporary_password', user_id=user.pk)


@login_required(login_url='login')
def password_change_required_view(request):
    form = ManagedUserPasswordForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        profile = request.user.userprofile
        profile.must_change_password = False
        profile.save(update_fields=['must_change_password'])
        update_session_auth_hash(request, request.user)
        messages.success(request, 'Your password has been changed.')
        return redirect('home')
    return render(request, 'password_change_required.html', {'form': form})


@admin_required
def user_management_list_view(request):
    roles = dict(UserProfile.ROLE_CHOICES)
    profile_roles = dict(UserProfile.objects.values_list('user_id', 'role'))
    doctor_links = {}
    for doctor in EmdDoctor.objects.filter(doctorsid__isnull=False).order_by('pk_emddoctors'):
        doctor_links.setdefault(doctor.doctorsid, []).append(doctor.doctors_name)

    rows = []
    for user in User.objects.order_by('username'):
        linked_doctors = doctor_links.get(user.pk, [])
        rows.append({
            'user': user,
            'role': roles.get(profile_roles.get(user.pk), 'Unassigned'),
            'doctor': linked_doctors[0] if len(linked_doctors) == 1 else None,
            'multiple_doctors': len(linked_doctors) > 1,
        })
    return render(request, 'user_management.html', {'rows': rows})


@admin_required
def user_management_create_view(request):
    form = ManagedUserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        doctor = form.cleaned_data.get('doctor')
        role = form.cleaned_data['role']
        with transaction.atomic():
            locked_doctor = None
            if doctor:
                locked_doctor = EmdDoctor.objects.select_for_update().get(pk=doctor.pk_emddoctors)
                if (
                    locked_doctor.doctorsid is not None
                    and User.objects.filter(pk=locked_doctor.doctorsid).exists()
                ):
                    form.add_error('doctor', 'That doctor record is already linked to an account.')
                    return render(request, 'user_management_form.html', {
                        'form': form, 'title': 'Create account',
                    })

            user = form.save()
            user.is_staff = role == 'admin'
            user.is_superuser = False
            user.save(update_fields=['is_staff', 'is_superuser'])
            UserProfile.objects.update_or_create(
                user=user,
                defaults={'role': role, 'must_change_password': True},
            )
            if locked_doctor:
                locked_doctor.doctorsid = user.pk
                locked_doctor.save(update_fields=['doctorsid'])

        return _issue_temporary_password(
            request, user, doctor if role == 'doctor' else None,
        )
    return render(request, 'user_management_form.html', {
        'form': form, 'title': 'Create account',
    })


@admin_required
def user_management_update_view(request, user_id):
    managed_user = get_object_or_404(User, pk=user_id)
    form = ManagedUserUpdateForm(request.POST or None, instance=managed_user)
    if request.method == 'POST' and form.is_valid():
        role = form.cleaned_data['role']
        doctor = form.cleaned_data.get('doctor')
        active = form.cleaned_data['is_active']
        try:
            current_role = managed_user.userprofile.role
        except UserProfile.DoesNotExist:
            current_role = None

        if managed_user.pk == request.user.pk and (not active or role != current_role):
            form.add_error(None, 'You cannot deactivate your own account or change your own role.')
        elif (
            current_role == 'admin'
            and managed_user.is_active
            and (role != 'admin' or not active)
            and UserProfile.objects.filter(role='admin', user__is_active=True).count() <= 1
        ):
            form.add_error(None, 'The last active administrator cannot be demoted or deactivated.')

        if form.errors:
            return render(request, 'user_management_form.html', {
                'form': form, 'title': f'Edit {managed_user.username}',
                'managed_user': managed_user,
            })

        with transaction.atomic():
            doctor_ids = Q(doctorsid=managed_user.pk)
            if doctor:
                doctor_ids |= Q(pk_emddoctors=doctor.pk_emddoctors)
            locked_doctors = list(
                EmdDoctor.objects.select_for_update().filter(doctor_ids).order_by('pk_emddoctors')
            )
            locked_doctor = next(
                (item for item in locked_doctors if doctor and item.pk_emddoctors == doctor.pk_emddoctors),
                None,
            )
            if (
                doctor
                and locked_doctor
                and locked_doctor.doctorsid not in (None, managed_user.pk)
                and User.objects.filter(pk=locked_doctor.doctorsid).exists()
            ):
                form.add_error('doctor', 'That doctor record is already linked to another account.')
                return render(request, 'user_management_form.html', {
                    'form': form, 'title': f'Edit {managed_user.username}',
                    'managed_user': managed_user,
                })

            managed_user = form.save()
            managed_user.is_staff = role == 'admin'
            if role != 'admin':
                managed_user.is_superuser = False
            managed_user.save(update_fields=['is_staff', 'is_superuser'])
            UserProfile.objects.update_or_create(user=managed_user, defaults={'role': role})
            EmdDoctor.objects.filter(doctorsid=managed_user.pk).update(doctorsid=None)
            if locked_doctor:
                locked_doctor.doctorsid = managed_user.pk
                locked_doctor.save(update_fields=['doctorsid'])

        messages.success(request, f'Account for {managed_user.username} updated.')
        return redirect('user_management')
    return render(request, 'user_management_form.html', {
        'form': form, 'title': f'Edit {managed_user.username}',
        'managed_user': managed_user,
    })


@admin_required
def user_management_password_view(request, user_id):
    managed_user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        try:
            role = managed_user.userprofile.role
        except UserProfile.DoesNotExist:
            role = None
        doctor = EmdDoctor.objects.filter(doctorsid=managed_user.pk).first() if role == 'doctor' else None
        return _issue_temporary_password(request, managed_user, doctor)
    return render(request, 'user_password_reset.html', {
        'managed_user': managed_user,
    })


@admin_required
def user_management_temporary_password_view(request, user_id):
    managed_user = get_object_or_404(User, pk=user_id)
    password = request.session.pop(f'temporary_password_{managed_user.pk}', None)
    uses_doctor_format = request.session.pop(
        f'temporary_password_uses_doctor_format_{managed_user.pk}', False,
    )
    if not password:
        messages.error(request, 'That temporary password has already been viewed or expired.')
        return redirect('user_management')
    return render(request, 'user_temporary_password.html', {
        'managed_user': managed_user,
        'temporary_password': password,
        'uses_doctor_format': uses_doctor_format,
    })

# ===== DASHBOARD VIEW =====
@login_required(login_url='login')
def get_current_doctor(request):
    """Resolve a doctor from an explicit account link or a unique legacy username."""
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'doctor':
        return None

    username = (request.user.username or '').strip()
    if not username:
        return None

    import re

    linked_doctors = list(EmdDoctor.objects.filter(doctorsid=request.user.pk))
    if linked_doctors:
        return linked_doctors[0] if len(linked_doctors) == 1 and linked_doctors[0].active else None

    active_doctors = EmdDoctor.objects.filter(active=True)

    def unique_match(candidates):
        matches = list(candidates)
        return matches[0] if len(matches) == 1 else None

    match = re.match(r'^(?P<prefix>.+?)(?P<digits>\d{4,6})$', username)
    if match:
        prefix = match.group('prefix').strip()
        digits = match.group('digits')

        mm_yy = digits[-4:]
        try:
            month = int(mm_yy[:2])
            year2 = int(mm_yy[2:])
        except ValueError:
            month = None
            year2 = None

        if month and 1 <= month <= 12:
            candidates = [
                doctor for doctor in active_doctors.filter(
                    prcexpdate__isnull=False, prcexpdate__month=month,
                )
                if doctor.prcexpdate and doctor.prcexpdate.year % 100 == year2
                and doctor.last_name.strip().upper() == prefix.upper()
            ]
            match_doctor = unique_match(candidates)
            if match_doctor:
                return match_doctor

        try:
            doctor_pk = int(digits)
            candidate = active_doctors.filter(pk_emddoctors=doctor_pk).first()
            if candidate and candidate.last_name.strip().upper() == prefix.upper():
                return candidate
        except ValueError:
            pass

    username_match = re.match(r'^(?P<lastname>[A-Za-z]+)(?P<initial>[A-Z])$', username)
    if username_match:
        username_lastname = username_match.group('lastname').strip().lower()
        username_initial = username_match.group('initial')
        candidates = [
            doctor for doctor in active_doctors
            if doctor.last_name.strip().lower() == username_lastname
            and (doctor.first_name.strip()[:1] or '').upper() == username_initial
        ]
        match_doctor = unique_match(candidates)
        if match_doctor:
            return match_doctor

    username_lastname_only = re.match(r'^(?P<lastname>[A-Za-z]+)$', username)
    if username_lastname_only:
        username_lastname = username_lastname_only.group('lastname').strip().lower()
        candidates = [
            doctor for doctor in active_doctors
            if doctor.last_name.strip().lower() == username_lastname
        ]
        return unique_match(candidates)

    return None



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
        total_soa_amount = (
            (ReleasedCheck.objects.filter(
                Q(payee__icontains=my_doctor.doctors_name) | Q(vendorname__icontains=my_doctor.doctors_name)
            ).aggregate(total=Sum('amount'))['total'] or 0)
            + (UnreleasedCheck.objects.filter(
                payeename__icontains=my_doctor.doctors_name
            ).aggregate(total=Sum('amount'))['total'] or 0)
            + (OutstandingPayable.objects.filter(
                Vendor__icontains=my_doctor.doctors_name
            ).aggregate(total=Sum('amount'))['total'] or 0)
        )
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

    doctor_analytics = None
    if my_doctor and request.user.userprofile.role == 'doctor':
        today = timezone.localdate()

        def normalize_date(value):
            if isinstance(value, datetime):
                if timezone.is_aware(value):
                    value = timezone.localtime(value)
                return value.date()
            return value

        coverage_start = date(2025, 1, 1)
        months = []
        month_cursor = coverage_start
        while month_cursor <= today.replace(day=1):
            months.append(month_cursor)
            if month_cursor.month == 12:
                month_cursor = date(month_cursor.year + 1, 1, 1)
            else:
                month_cursor = date(month_cursor.year, month_cursor.month + 1, 1)
        years = list(range(coverage_start.year, today.year + 1))
        month_start = today.replace(day=1)
        current_year_start = date(today.year, 1, 1)
        try:
            prior_year_end = today.replace(year=today.year - 1)
        except ValueError:
            prior_year_end = date(today.year - 1, 2, 28)
        prior_year_start = date(today.year - 1, 1, 1)

        doctor_released_checks = ReleasedCheck.objects.filter(
            Q(payee__icontains=my_doctor.doctors_name)
            | Q(vendorname__icontains=my_doctor.doctors_name)
        )
        collected_checks = doctor_released_checks.filter(
            Q(releasedate__range=(coverage_start, today))
            | Q(releasedate__isnull=True, checkdate__range=(coverage_start, today))
        ).values('checkdate', 'releasedate', 'amount', 'hospplan')

        released_by_month = defaultdict(lambda: defaultdict(float))
        released_by_year = defaultdict(lambda: defaultdict(float))
        released_by_mode = defaultdict(float)
        payment_modes = set()
        released_total = 0
        released_ytd = 0
        released_prior_ytd = 0
        released_this_month = 0
        for check in collected_checks:
            collected_date = normalize_date(check['releasedate'] or check['checkdate'])
            if not collected_date:
                continue
            payment_mode = (check['hospplan'] or '').strip() or 'Unspecified'
            amount = float(check['amount'] or 0)
            payment_modes.add(payment_mode)
            released_by_month[(collected_date.year, collected_date.month)][payment_mode] += amount
            released_by_year[collected_date.year][payment_mode] += amount
            released_by_mode[payment_mode] += amount
            released_total += amount
            if current_year_start <= collected_date <= today:
                released_ytd += amount
            if prior_year_start <= collected_date <= prior_year_end:
                released_prior_ytd += amount
            if month_start <= collected_date <= today:
                released_this_month += amount

        patient_queryset = Patientlist.objects.filter(
            doctors_code=str(my_doctor.pk_emddoctors),
            registry_datetime__date__range=(coverage_start, today),
        )
        coverage_patient_count = patient_queryset.count()
        patients_ytd = patient_queryset.filter(
            registry_datetime__date__range=(current_year_start, today)
        ).count()
        patients_prior_ytd = patient_queryset.filter(
            registry_datetime__date__range=(prior_year_start, prior_year_end)
        ).count()
        patients_this_month = patient_queryset.filter(
            registry_datetime__date__range=(month_start, today)
        ).count()

        doctor_unreleased_checks = UnreleasedCheck.objects.filter(
            payeename__icontains=my_doctor.doctors_name
        )
        pending_checks = doctor_unreleased_checks.filter(
            checkdate__range=(coverage_start, today)
        ).values('checkdate', 'amount')
        pending_total = 0
        pending_this_month = 0
        pending_check_count = 0
        for check in pending_checks:
            pending_date = normalize_date(check['checkdate'])
            if pending_date:
                amount = float(check['amount'] or 0)
                pending_total += amount
                pending_check_count += 1
                if month_start <= pending_date <= today:
                    pending_this_month += amount

        next_check_release = doctor_unreleased_checks.filter(
            checkdate__gte=today
        ).order_by('checkdate').values_list('checkdate', flat=True).first()

        statements_this_month = StatementOfAccount.objects.filter(
            doctor=my_doctor,
            created_at__date__range=(month_start, today),
        ).count()

        recent_transactions = []
        recent_released = doctor_released_checks.filter(
            Q(releasedate__range=(coverage_start, today))
            | Q(releasedate__isnull=True, checkdate__range=(coverage_start, today))
        )
        for check in recent_released.values(
            'checkno', 'checkdate', 'releasedate', 'amount', 'patientnameinitials'
        ).order_by('-releasedate', '-checkdate')[:8]:
            recent_transactions.append({
                'date': normalize_date(check['releasedate'] or check['checkdate']),
                'reference': check['checkno'],
                'patient': check['patientnameinitials'] or '—',
                'status': 'Released',
                'amount': check['amount'],
            })

        for check in doctor_unreleased_checks.filter(
            checkdate__range=(coverage_start, today)
        ).values(
            'checkno', 'checkdate', 'amount', 'patientnameinitials'
        ).order_by('-checkdate')[:8]:
            recent_transactions.append({
                'date': normalize_date(check['checkdate']),
                'reference': check['checkno'],
                'patient': check['patientnameinitials'] or '—',
                'status': 'Pending',
                'amount': check['amount'],
            })
        recent_transactions.sort(key=lambda item: item['date'] or date.min, reverse=True)

        doctor_analytics = {
            'coverage_start': coverage_start,
            'coverage_end': today,
            'released_total': released_total,
            'released_change_pct': round((released_ytd - released_prior_ytd) / released_prior_ytd * 100, 1) if released_prior_ytd else None,
            'released_change_abs_pct': abs(round((released_ytd - released_prior_ytd) / released_prior_ytd * 100, 1)) if released_prior_ytd else 0,
            'patient_total': coverage_patient_count,
            'patient_change_pct': round((patients_ytd - patients_prior_ytd) / patients_prior_ytd * 100, 1) if patients_prior_ytd else None,
            'patient_change_abs_pct': abs(round((patients_ytd - patients_prior_ytd) / patients_prior_ytd * 100, 1)) if patients_prior_ytd else 0,
            'pending_total': pending_total,
            'pending_check_count': pending_check_count,
            'next_check_release': normalize_date(next_check_release),
            'average_pf_per_patient': released_total / coverage_patient_count if coverage_patient_count else 0,
            'this_month': {
                'label': today.strftime('%B %Y'),
                'patients': patients_this_month,
                'released_pf': released_this_month,
                'pending_pf': pending_this_month,
                'soa_created': statements_this_month,
            },
            'monthly_labels': [month.strftime('%b %Y') for month in months],
            'yearly_labels': [str(year) for year in years],
            'payment_modes': sorted(payment_modes),
            'released_monthly_datasets': [
                {
                    'label': mode,
                    'data': [round(released_by_month[(month.year, month.month)][mode], 2) for month in months],
                    'total': round(released_by_mode[mode], 2),
                }
                for mode in sorted(payment_modes)
            ],
            'released_yearly_datasets': [
                {
                    'label': mode,
                    'data': [round(released_by_year[year][mode], 2) for year in years],
                }
                for mode in sorted(payment_modes)
            ],
            'payment_mode_labels': sorted(payment_modes),
            'payment_mode_values': [round(released_by_mode[mode], 2) for mode in sorted(payment_modes)],
            'payment_mode_summaries': [
                {
                    'label': mode,
                    'amount': round(released_by_mode[mode], 2),
                    'percentage': round(released_by_mode[mode] / released_total * 100, 1) if released_total else 0,
                }
                for mode in sorted(payment_modes)
            ],
            'recent_transactions': recent_transactions[:8],
        }

    return render(request, 'home.html', {
        'doctor_count': doctor_count,
        'patient_count': patient_count,
        'transaction_count': transaction_count,
        'total_soa_amount': total_soa_amount if my_doctor else 0,
        'statement_count': statement_count,
        'welcome_display': welcome_display,
        'doctor_analytics': doctor_analytics,
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

@admin_required
def doctor_reset_password_view(request, pk):
    doctor = get_object_or_404(EmdDoctor, pk_emddoctors=pk)
    user = User.objects.filter(pk=doctor.doctorsid).first()
    if not user:
        messages.error(request, 'This doctor record is not linked to a user account. Link or create the account in User Management first.')
        return redirect('user_management')
    return redirect('user_management_password', user_id=user.pk)

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

    # Recent released and unreleased checks for this doctor
    released_checks_queryset = ReleasedCheck.objects.filter(
        Q(payee__icontains=my_doctor.doctors_name) | Q(vendorname__icontains=my_doctor.doctors_name)
    )
    unreleased_checks_queryset = UnreleasedCheck.objects.filter(
        payeename__icontains=my_doctor.doctors_name
    )

    recent_released_checks = list(
        released_checks_queryset.order_by('-checkdate').values('checkno', 'checkdate', 'amount')[:10]
    )
    recent_unreleased_checks = list(
        unreleased_checks_queryset.order_by('-checkdate').values('checkno', 'checkdate', 'amount')[:10]
    )

    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    released_table_queryset = released_checks_queryset
    if date_from:
        released_table_queryset = released_table_queryset.filter(checkdate__gte=date_from)
    if date_to:
        released_table_queryset = released_table_queryset.filter(checkdate__lte=date_to)

    if date_from or date_to:
        released_checks = list(
            released_table_queryset.order_by('-checkdate').values('checkno', 'checkdate', 'amount')
        )
        released_table_total = released_table_queryset.aggregate(total=Sum('amount'))['total'] or 0
    else:
        released_checks = recent_released_checks
        released_table_total = sum(check['amount'] for check in recent_released_checks)

    total_soa_amount = (
        (released_checks_queryset.aggregate(total=Sum('amount'))['total'] or 0)
        + (unreleased_checks_queryset.aggregate(total=Sum('amount'))['total'] or 0)
        + (OutstandingPayable.objects.filter(
            Vendor__icontains=my_doctor.doctors_name
        ).aggregate(total=Sum('amount'))['total'] or 0)
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
        'released_checks': released_checks,
        'recent_released_total': sum(check['amount'] for check in recent_released_checks),
        'released_table_total': released_table_total,
        'unreleased_checks': recent_unreleased_checks,
        'recent_unreleased_total': sum(check['amount'] for check in recent_unreleased_checks),
        'total_soa_amount': total_soa_amount,
        'date_from': date_from,
        'date_to': date_to,
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
        queryset = super().get_queryset().order_by('registry_datetime')

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
            released_checks = ReleasedCheck.objects.filter(
                Q(payee__icontains=my_doctor.doctors_name) | Q(vendorname__icontains=my_doctor.doctors_name)
            )
            unreleased_checks = UnreleasedCheck.objects.filter(payeename__icontains=my_doctor.doctors_name)
            outstanding_reports = OutstandingPayable.objects.filter(Vendor__icontains=my_doctor.doctors_name)
            context['apv_count'] = APV.objects.filter(payee_name__icontains=my_doctor.doctors_name).count()
            context['check_report_count'] = CheckReport.objects.filter(payto__icontains=my_doctor.doctors_name).count()
        else:
            released_checks = ReleasedCheck.objects.all()
            unreleased_checks = UnreleasedCheck.objects.all()
            outstanding_reports = OutstandingPayable.objects.all()
            context['apv_count'] = APV.objects.count()
            context['check_report_count'] = CheckReport.objects.count()

        context['released_count'] = released_checks.count()
        context['released_amount'] = released_checks.aggregate(total=Sum('amount'))['total'] or 0
        context['unreleased_count'] = unreleased_checks.count()
        context['unreleased_amount'] = unreleased_checks.aggregate(total=Sum('amount'))['total'] or 0
        context['outstanding_count'] = outstanding_reports.count()
        outstanding_totals = outstanding_reports.aggregate(
            amount=Sum('amount'),
            balance=Sum('balance'),
        )
        context['outstanding_amount'] = outstanding_totals['amount'] or 0
        context['outstanding_balance'] = outstanding_totals['balance'] or 0
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
        queryset = super().get_queryset().order_by('releasedate', 'checkno')

        
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
        queryset = super().get_queryset().order_by('checkdate', 'checkno')

        
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
        queryset = super().get_queryset().order_by('docdate', 'docno')

        
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

