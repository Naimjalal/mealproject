from django.contrib.auth.decorators import login_required 
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from datetime import date, timedelta, time, datetime
import datetime 
try:
    import openpyxl
except ImportError:
    openpyxl = None
from django.utils import timezone
from .models import Employee, MealOrder,DailyMenu
from django.contrib.auth import logout
from django.shortcuts import redirect
import openpyxl

ALLOWED_BY_DUTY = {
    "24h": {"breakfast", "lunch", "dinner"},

    "dbl_5_7": {"breakfast", "lunch", "dinner"},
    "dbl_8_13": {"lunch", "dinner"},
    "dbl_14_20": {"dinner"},

    "8h_morn": {"breakfast"},
    "8h_noon": {"lunch"},
    "8h_night": {"dinner"},

    "12h_day": {"breakfast", "lunch"},
    "12h_night": {"dinner"},
}


@login_required
def meal_report(request):
    # date param (defaults to tomorrow)
    date_str = request.GET.get("date")
    if date_str:
        report_date = date.fromisoformat(date_str)
    else:
        report_date = date.today() + timedelta(days=1)

    locations = [
        ("budaiya", "البديع"),
        ("khamis", "الخميس"),
        ("gharbiya", "الغربية"),
    ]
    meal_types = [
        ("breakfast", "الفطور"),
        ("lunch", "الغداء"),
        ("dinner", "العشاء"),
    ]

    # --- summary (existing) ---
    data = []
    grand_totals = {"breakfast": 0, "lunch": 0, "dinner": 0, "all": 0}

    for loc_code, loc_name in locations:
        row = {"location_name": loc_name, "breakfast": 0, "lunch": 0, "dinner": 0, "total": 0}
        for meal_code, _ in meal_types:
            c = MealOrder.objects.filter(order_date=report_date, location=loc_code, meal_type=meal_code).count()
            row[meal_code] = c
            row["total"] += c
            grand_totals[meal_code] += c
            grand_totals["all"] += c
        data.append(row)

    # --- detailed one-row-per-employee ---
    orders = (
        MealOrder.objects
        .select_related("employee")
        .filter(order_date=report_date)
        .order_by("employee__unique_number", "meal_type", "-submitted_at")
    )

    # build rows keyed by employee
    detail_map = {}
    for o in orders:
        key = o.employee_id
        if key not in detail_map:
            detail_map[key] = {
                "employee_no": o.employee.unique_number,
                "location": o.location,
                "breakfast": False,
                "lunch": False,
                "dinner": False,
                "last_time": o.submitted_at,
            }
        # set meal flags
        detail_map[key][o.meal_type] = True
        # latest submission time
        if o.submitted_at and detail_map[key]["last_time"]:
            if o.submitted_at > detail_map[key]["last_time"]:
                detail_map[key]["last_time"] = o.submitted_at

    # sort rows by location, then employee number
    loc_order = {"budaiya": 0, "khamis": 1, "gharbiya": 2}
    detail_rows = sorted(
        detail_map.values(),
        key=lambda r: (loc_order.get(r["location"], 99), r["employee_no"])
    )

    context = {
        "report_date": report_date,
        "data": data,
        "grand_totals": grand_totals,
        "detail_rows": detail_rows,
    }
    return render(request, "meals/report.html", context)


def store_logout(request):
    logout(request)
    return redirect('store_login')

@login_required
def meal_report_excel(request):
    # same date logic
    date_str = request.GET.get("date")
    if date_str:
        try:
            report_date = date.fromisoformat(date_str)
        except ValueError:
        # maybe it's like "Nov. 12, 2025"
         report_date = datetime.datetime.strptime(date_str, "%b. %d, %Y").date()
    else:
        report_date = date.today() + timedelta(days=1)

    locations = [
        ("budaiya", "البديع"),
        ("khamis", "الخميس"),
        ("gharbiya", "الغربية"),
    ]
    meal_types = [
        ("breakfast", "الفطور"),
        ("lunch", "الغداء"),
        ("dinner", "العشاء"),
    ]

    # we need openpyxl
    if openpyxl is None:
        return HttpResponse("openpyxl غير مثبت. شغّل: pip install openpyxl", content_type="text/plain")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Meals"

    # header
    ws.append([
        f"تقرير الوجبات ليوم {report_date}",
    ])
    ws.append([])

    ws.append(["الموقع", "الفطور", "الغداء", "العشاء", "الإجمالي"])

    grand_breakfast = grand_lunch = grand_dinner = grand_all = 0

    for loc_code, loc_name in locations:
        # count per meal
        b = MealOrder.objects.filter(order_date=report_date, location=loc_code, meal_type="breakfast").count()
        l = MealOrder.objects.filter(order_date=report_date, location=loc_code, meal_type="lunch").count()
        d = MealOrder.objects.filter(order_date=report_date, location=loc_code, meal_type="dinner").count()
        total = b + l + d

        grand_breakfast += b
        grand_lunch += l
        grand_dinner += d
        grand_all += total

        ws.append([loc_name, b, l, d, total])

    # total row
    ws.append([])
    ws.append(["الإجمالي", grand_breakfast, grand_lunch, grand_dinner, grand_all])

    # prepare response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = f"meal-report-{report_date}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response

@login_required
def meal_report_excel_detailed(request):
    date_str = request.GET.get("date")
    if date_str:
        report_date = date.fromisoformat(date_str)
    else:
        report_date = date.today() + timedelta(days=1)

    if openpyxl is None:
        return HttpResponse("openpyxl غير مثبت. شغّل: pip install openpyxl", content_type="text/plain")

    # fetch orders & build one row per employee
    orders = (
        MealOrder.objects
        .select_related("employee")
        .filter(order_date=report_date)
        .order_by("employee__unique_number", "meal_type", "-submitted_at")
    )
    loc_order = {"budaiya": "البديع", "khamis": "الخميس", "gharbiya": "الغربية"}

    rows = {}
    for o in orders:
        key = o.employee_id
        if key not in rows:
            rows[key] = {
                "employee_no": o.employee.unique_number,
                "location": loc_order.get(o.location, o.location),
                "breakfast": False,
                "lunch": False,
                "dinner": False,
                "last_time": o.submitted_at,
            }
        rows[key][o.meal_type] = True
        if o.submitted_at and rows[key]["last_time"]:
            if o.submitted_at > rows[key]["last_time"]:
                rows[key]["last_time"] = o.submitted_at

    # create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Details"

    ws.append([f"التقرير التفصيلي ليوم {report_date}"])
    ws.append([])
    ws.append(["#","رقم الموظف","الموقع","الفطور","الغداء","العشاء","آخر وقت"])

    # write rows
    idx = 1
    for r in sorted(rows.values(), key=lambda r: (r["location"], r["employee_no"])):
        check = "✓"
        ws.append([
            idx,
            r["employee_no"],
            r["location"],
            check if r["breakfast"] else "",
            check if r["lunch"] else "",
            check if r["dinner"] else "",
            (r["last_time"].astimezone().strftime("%H:%M") if r["last_time"] else ""),
        ])
        idx += 1

    # return file
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = f"meal-details-{report_date}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response

def enter_meal_number(request):
    error = None

    if request.method == "POST":
        number = request.POST.get("unique_number", "").strip()

        try:
            employee = Employee.objects.get(unique_number=number, is_active=True)
        except Employee.DoesNotExist:
            error = "الرقم غير صحيح أو غير مفعل"
        else:
            return redirect("choose_date", employee_id=employee.id)

    return render(request, "meals/enter_number.html", {"error": error})


def choose_date(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    now = datetime.datetime.now()
 # current time

    DAY_NAMES_AR = {
        "Saturday": "السبت",
        "Sunday": "الأحد",
        "Monday": "الاثنين",
        "Tuesday": "الثلاثاء",
        "Wednesday": "الأربعاء",
        "Thursday": "الخميس",
        "Friday": "الجمعة",
    }

    days = []
    offset = 1   # start from tomorrow

    while len(days) < 3:
        meal_day = date.today() + timedelta(days=offset)

        # RULE: after 8pm, don't allow tomorrow
        if offset == 1 and now.hour >= 20:
            offset += 1
            continue

        weekday_en = meal_day.strftime("%A")  # e.g. "Monday"
        weekday_ar = DAY_NAMES_AR.get(weekday_en, weekday_en)

        # Get menu for this weekday
        try:
            menu = DailyMenu.objects.get(weekday=weekday_en)
        except DailyMenu.DoesNotExist:
            menu = None

        if offset == 1:
            deadline_text = "متاح حتى 8:00 م اليوم"
        elif offset == 2:
            deadline_text = "متاح حتى 8:00 م غداً"
        else:
            deadline_text = "متاح حتى 8:00 م قبلها بيوم"

        days.append({
            "date": meal_day,
            "day_name": weekday_ar,
            "deadline_text": deadline_text,
            "menu": menu,  # attach menu object here!
        })

        offset += 1

    return render(request, "meals/choose_date.html", {
        "employee": employee,
        "days": days,
    })


def meal_form(request, employee_id, order_date):
    employee = get_object_or_404(Employee, id=employee_id)
    order_for = date.fromisoformat(order_date)

    # safety: after 8pm, can't order for tomorrow
    now = datetime.datetime.now()

    tomorrow = date.today() + timedelta(days=1)
    if order_for == tomorrow and now.hour >= 20:
        return render(request, "meals/too_late.html", {"order_for": order_for})

    existing_orders = MealOrder.objects.filter(employee=employee, order_date=order_for)
    existing_types = {m.meal_type for m in existing_orders}

    existing_location = None
    existing_duty = None
    if existing_orders.exists():
        first = existing_orders.first()
        existing_location = first.location
        existing_duty = first.duty_type

    error = None

    if request.method == "POST":
        # meals from form (raw)
        raw_selected_meals = request.POST.getlist("meal_type")

        # location
        if existing_location:
            location = existing_location
        else:
            location = request.POST.get("location")
        if not location:
            error = "يرجى اختيار موقع العمل"
            return render(
                request,
                "meals/meal_form.html",
                {
                    "employee": employee,
                    "order_for": order_for,
                    "existing_types": existing_types,
                    "existing_location": existing_location,
                    "existing_duty": existing_duty,
                    "error": error,
                },
            )

        # duty
        duty_type = request.POST.get("duty_type")
        if not duty_type:
            error = "يرجى اختيار نوع الدوام"
            return render(
                request,
                "meals/meal_form.html",
                {
                    "employee": employee,
                    "order_for": order_for,
                    "existing_types": existing_types,
                    "existing_location": existing_location,
                    "existing_duty": existing_duty,
                    "error": error,
                },
            )

        # --- NEW: enforce allowed meals ---
        allowed = ALLOWED_BY_DUTY.get(duty_type, set())
        # keep only meals that are allowed for this duty
        selected_meals = [m for m in raw_selected_meals if m in allowed]

        if not selected_meals:
            error = "الوجبات المختارة لا تتوافق مع نوع الدوام. يرجى تعديل الاختيار."
            return render(
                request,
                "meals/meal_form.html",
                {
                    "employee": employee,
                    "order_for": order_for,
                    "existing_types": existing_types,
                    "existing_location": existing_location,
                    "existing_duty": duty_type,  # keep what they chose
                    "error": error,
                },
            )

        # sync existing orders with new selection
        # 1) delete any old meals that are no longer selected
        for o in list(existing_orders):
            if o.meal_type not in selected_meals:
                o.delete()
            else:
                o.location = location
                o.duty_type = duty_type
                o.save()

        # 2) create any new meals that weren't there before
        existing_types = {m.meal_type for m in MealOrder.objects.filter(employee=employee, order_date=order_for)}
        for meal in selected_meals:
            if meal not in existing_types:
                MealOrder.objects.create(
                    employee=employee,
                    order_date=order_for,
                    meal_type=meal,
                    location=location,
                    duty_type=duty_type,
                    ip_address=request.META.get("REMOTE_ADDR", ""),
                )

        return render(
            request,
            "meals/thanks.html",
            {"employee": employee, "order_for": order_for},
        )

    # GET
    return render(
        request,
        "meals/meal_form.html",
        {
            "employee": employee,
            "order_for": order_for,
            "existing_types": existing_types,
            "existing_location": existing_location,
            "existing_duty": existing_duty,
            "error": error,
        },
    )