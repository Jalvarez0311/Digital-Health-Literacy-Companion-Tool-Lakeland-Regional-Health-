from django.urls import path 
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_page, name='login'),
    path('signup/', views.signup_page, name='signup'),
    path('logout/', views.logout_user, name='logout'),  # New logout URL
    path('dashboard/nurse/', views.dashboard_nurse, name='dashboard_nurse'),
    path('dashboard/patient/', views.dashboard_patient, name='dashboard_patient'),
    path('discharge/', views.create_discharge, name='discharge_summary'),
    path('discharge/generate/', views.generate_discharge, name='generate_discharge'),
    path('patient-documents/', views.patient_documents, name='patient_documents'),
    path(
        'patient-documents/<int:doc_id>/pdf/',
        views.patient_discharge_pdf,
        name='patient_discharge_pdf',
    ),
    path('survey/', views.survey, name='survey'),
    path('patient-info/', views.patient_info, name='patient_info'),
]
