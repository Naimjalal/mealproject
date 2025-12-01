from django.db import models

WEEKDAY_CHOICES = [
    ("Saturday", "السبت"),
    ("Sunday", "الأحد"),
    ("Monday", "الاثنين"),
    ("Tuesday", "الثلاثاء"),
    ("Wednesday", "الأربعاء"),
    ("Thursday", "الخميس"),
    ("Friday", "الجمعة"),
]

# نوع الدوام لكل طلب وجبة
DUTY_TYPE_CHOICES = [
    ("24h", "واجب ٢٤ ساعة"),
    ("18h", "واجب ١٨ ساعة (التأخير عن الواجب الاساسي)"),
    ("12h_day", "واجب ١٢ ساعة (من 0500 الى 1700)"),
    ("12h_night", "واجب ١٢ ساعة (من 1700 الى 0500)"),
    ("8h_morning", "واجب ٨ ساعات (نهار)"),
    ("8h_noon", "واجب ٨ ساعات (اول ليل)"),
    ("8h_night", "واجب ٨ ساعات (آخر ليل)"),

]

class Employee(models.Model):
    
    unique_number = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.unique_number


class MealOrder(models.Model):
    MEAL_CHOICES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
    ]

    
    

    LOCATION_CHOICES = [
        ('budaiya', 'Budaiya'),
        ('khamis', 'Khamis'),
        ('gharbiya', 'Gharbiya'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    order_date = models.DateField()
    meal_type = models.CharField(max_length=20)
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES)
    duty_type = models.CharField(
        "نوع الدوام",
        max_length=20,
        choices=DUTY_TYPE_CHOICES,
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        # allow multiple meals per day,
        # but NOT the same meal twice in same day
        unique_together = ('employee', 'order_date', 'meal_type')

    def __str__(self):
        return f"{self.employee.unique_number} - {self.order_date} - {self.meal_type} - {self.location}"

class DailyMenu(models.Model):
    weekday = models.CharField(
        "اليوم",
        max_length=10,
        choices=WEEKDAY_CHOICES,
        unique=True,  # one menu per weekday
    )
    breakfast_text = models.CharField("فطور", max_length=200, blank=True)
    lunch_text = models.CharField("غداء", max_length=200, blank=True)
    dinner_text = models.CharField("عشاء", max_length=200, blank=True)

    def __str__(self):
        # shows: قائمة يوم الاثنين
        return f"قائمة يوم {self.get_weekday_display()}"
