from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path('', views.enter_meal_number, name='enter_meal_number'),
    path('choose-date/<int:employee_id>/', views.choose_date, name='choose_date'),
    path('meal/<int:employee_id>/<str:order_date>/', views.meal_form, name='meal_form'),

    # admin/report
    path('report/', views.meal_report, name='meal_report'),
    path('report/excel/', views.meal_report_excel, name='meal_report_excel'),
    path('report/excel-detailed/', views.meal_report_excel_detailed, name='meal_report_excel_detailed'),

    path('store-login/', auth_views.LoginView.as_view(template_name='meals/login.html'), name='store_login'),

    path('logout/', views.store_logout, name='logout'),


    ]

