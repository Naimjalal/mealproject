from django.contrib import admin
from .models import Employee, MealOrder, DailyMenu

admin.site.register(Employee)
admin.site.register(MealOrder)
admin.site.register(DailyMenu)
