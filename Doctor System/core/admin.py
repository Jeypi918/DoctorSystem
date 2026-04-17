from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import EmdDoctor, Patient, PFTransaction, StatementOfAccount, UserProfile, ReleasedCheck

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

# EmdDoctorInline removed - no FK to User in legacy table
# class EmdDoctorInline(admin.StackedInline):
#     model = EmdDoctor
#     can_delete = False
#     verbose_name_plural = 'Doctor Profile'
#     fields = ('doctors_name', 'smsplusmobileno', 'tin', 'specialization', 'active')

class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    list_display = UserAdmin.list_display + ('role',)
    
    def role(self, obj):
        try:
            return obj.userprofile.role
        except:
            return None

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'phone')

@admin.register(PFTransaction)
class PFTransactionAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'patient', 'amount', 'date')
    list_filter = ('date',)

@admin.register(StatementOfAccount)
class StatementOfAccountAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'start_date', 'end_date', 'filtered_total')
    list_filter = ('start_date',)

@admin.register(ReleasedCheck)
class ReleasedCheckAdmin(admin.ModelAdmin):
    list_display = ('checkno', 'payee', 'amount', 'checkdate', 'releasedate', 'bankname')
    list_filter = ('bankname', 'checkdate', 'releasedate')
    search_fields = ('checkno', 'payee', 'vendorname')
    list_filter = ('bankname', 'checkdate')
    search_fields = ('checkno', 'payee', 'vendorname')

