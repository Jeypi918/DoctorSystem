from django.urls import path
from . import views

urlpatterns = [
    # ===== AUTH =====
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    
    # ===== DOCTORS =====
    path('doctors/', views.DoctorListView.as_view(), name='doctors'),
    path('doctors/add/', views.doctor_create_view, name='doctor_add'),
    path('doctors/<int:pk>/', views.doctor_detail_view, name='doctor_detail'),
    path('doctors/<int:pk>/reset-password/', views.doctor_reset_password_view, name='doctor_reset_password'),
    path('doctors/<int:pk>/edit/', views.doctor_update_view, name='doctor_edit'),
    path('doctors/<int:pk>/delete/', views.doctor_delete_view, name='doctor_delete'),
    
    # ===== PATIENTS =====
    path('patients/', views.PatientListView.as_view(), name='patients'),
    path('patients/add/', views.patient_create_view, name='patient_add'),
    path('patients/<int:pk>/', views.patient_detail_view, name='patient_detail'),
    path('patients/<int:pk>/edit/', views.patient_update_view, name='patient_edit'),
    path('patients/<int:pk>/delete/', views.patient_delete_view, name='patient_delete'),
    
    # ===== TRANSACTIONS =====
    path('transactions/', views.TransactionListView.as_view(), name='transactions'),
    path('transactions/add/', views.transaction_create_view, name='transaction_add'),
    path('transactions/<int:pk>/edit/', views.transaction_update_view, name='transaction_edit'),
    path('transactions/<int:pk>/delete/', views.transaction_delete_view, name='transaction_delete'),
    
    # ===== STATEMENTS =====
    path('statements/', views.SoaListView.as_view(), name='statements'),
    path('statements/add/', views.statement_create_view, name='statement_add'),
    path('statements/<int:pk>/edit/', views.statement_update_view, name='statement_edit'),
    path('statements/<int:pk>/delete/', views.statement_delete_view, name='statement_delete'),

    # ===== RELEASED CHECKS =====
    path('released-checks/', views.ReleasedCheckListView.as_view(), name='released_checks'),

    # ===== DOCTOR SELF =====
    path('my-doctor/', views.my_doctor_view, name='my_doctor'),

    # ===== BILLING =====
    path('billing/', views.billing_view, name='billing'),

    # ===== ACCOUNTING =====
    path('accounting/', views.accounting_view, name='accounting'),
]

