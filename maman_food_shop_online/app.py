
import os
from functools import wraps
from flask import (
    Flask, request, redirect, url_for,
    session, render_template_string, abort
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash

app = Flask(__name__)

# تنظیمات سایت
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

database_url = os.environ.get("DATABASE_URL", "sqlite:///maman_food.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =====================================
# نام کاربری و رمز پنل مدیریت
# این دو مقدار را به دلخواه خودت تغییر بده
# =====================================
ADMIN_USERNAME = "1356Af1392"
ADMIN_PASSWORD = "1356Af1392"


# مدل غذاها
class Food(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    emoji = db.Column(db.String(20), default="🍽️")


# مدل سفارش‌ها
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    note = db.Column(db.Text, default="")
    status = db.Column(db.String(40), default="جدید")


# غذاهای داخل هر سفارش
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer,
        db.ForeignKey("order.id"),
        nullable=False
    )
    food_name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)


# بررسی ورود مدیر
def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


# ظاهر ساده و مشترک صفحات
STYLE = """
<style>
body {
    font-family: Tahoma, Arial, sans-serif;
    direction: rtl;
    background: #fff8f0;
    color: #333;
    margin: 0;
    padding: 20px;
}
main {
    max-width: 850px;
    margin: 20px auto;
}
h1, h2 { color: #a84c24; }
.card {
    background: white;
    padding: 18px;
    margin: 12px 0;
    border-radius: 12px;
    box-shadow: 0 2px 8px #0001;
}
input, textarea, button {
    font-family: inherit;
    font-size: 16px;
    padding: 10px;
    margin: 5px 0;
    max-width: 100%;
    box-sizing: border-box;
}
input, textarea { border: 1px solid #ddd; border-radius: 7px; }
button, .button {
    background: #a84c24;
    color: white;
    border: 0;
    border-radius: 7px;
    cursor: pointer;
    padding: 10px 16px;
    text-decoration: none;
}
.danger { background: #b3261e; }
small { color: #666; }
</style>
"""

# صفحه اصلی سفارش غذا
HOME_HTML = """
<!doctype html>
<html lang="fa">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>مامان‌پز</title>
""" + STYLE + """
</head>
<body>
<main>
    <h1>🍲 مامان‌پز</h1>
    <p>غذای مورد علاقه‌ات رو انتخاب کن و تعداد پرس رو بنویس.</p>

    {% if foods %}
    <form method="post" action="{{ url_for('place_order') }}">
        <div class="card">
            <label>نام شما</label><br>
            <input name="customer" required maxlength="120"
                   placeholder="نام و نام خانوادگی"><br>

            <label>شماره تماس</label><br>
            <input name="phone" required maxlength="40"
                   placeholder="شماره تماس">
        </div>

        <h2>منوی غذاها</h2>
        {% for food in foods %}
        <div class="card">
            <h3>{{ food.emoji }} {{ food.name }}</h3>
            <label>تعداد پرس:</label>
            <input type="number" name="food_{{ food.id }}"
                   min="0" max="50" value="0">
        </div>
        {% endfor %}

        <div class="card">
            <label>توضیحات (اختیاری)</label><br>
            <textarea name="note" rows="3"
                      placeholder="مثلاً توضیحات سفارش"></textarea><br>
            <button type="submit">ثبت سفارش</button>
        </div>
    </form>
    {% else %}
        <div class="card">هنوز غذایی به منو اضافه نشده است.</div>
    {% endif %}
</main>
</body>
</html>
"""

# صفحه نتیجه سفارش
SUCCESS_HTML = """
<!doctype html>
<html lang="fa">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>سفارش ثبت شد</title>
""" + STYLE + """
</head>
<body>
<main>
    <div class="card">
        <h1>✅ سفارش ثبت شد!</h1>
        <p>شماره سفارش شما: {{ order.id }}</p>
        <p>ممنون که مامان‌پز رو انتخاب کردی ❤️</p>
        <a class="button" href="{{ url_for('home') }}">بازگشت</a>
    </div>
</main>
</body>
</html>
"""

# صفحه ورود مدیر
LOGIN_HTML = """
<!doctype html>
<html lang="fa">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ورود مدیر مامان‌پز</title>
""" + STYLE + """
</head>
<body>
<main>
    <div class="card">
        <h1>🔐 ورود به پنل مامان‌پز</h1>
        {% if error %}
            <p style="color:#b3261e">{{ error }}</p>
        {% endif %}
        <form method="post">
            <label>نام کاربری</label><br>
            <input name="username" required autocomplete="username"><br>
            <label>رمز عبور</label><br>
            <input name="password" type="password" required
                   autocomplete="current-password"><br>
            <button type="submit">ورود به پنل</button>
        </form>
        <p><a href="{{ url_for('home') }}">بازگشت به سایت</a></p>
    </div>
</main>
</body>
</html>
"""

# پنل مدیریت
ADMIN_HTML = """
<!doctype html>
<html lang="fa">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>پنل مدیریت مامان‌پز</title>
""" + STYLE + """
</head>
<body>
<main>
    <h1>🍲 پنل مدیریت مامان‌پز</h1>
    <p><a class="button" href="{{ url_for('home') }}">صفحه سفارش</a>
       <a class="button" href="{{ url_for('admin_logout') }}">خروج از پنل</a>
    </p>

    <div class="card">
        <h2>افزودن غذا</h2>
        <form method="post" action="{{ url_for('add_food') }}">
            <input name="name" required maxlength="120"
                   placeholder="نام غذا">
            <input name="emoji" maxlength="20" value="🍽️"
                   placeholder="ایموجی">
            <button type="submit">افزودن غذا</button>
        </form>
    </div>

    <h2>غذاهای منو</h2>
    {% for food in foods %}
    <div class="card">
        {{ food.emoji }} {{ food.name }}
        <form method="post"
              action="{{ url_for('delete_food', food_id=food.id) }}"
              onsubmit="return confirm('این غذا از منو حذف شود؟')">
            <button class="danger" type="submit">حذف غذا</button>
        </form>
    </div>
    {% else %}
        <p>هنوز غذایی ثبت نشده.</p>
    {% endfor %}

    <h2>سفارش‌ها</h2>
    {% for order in orders %}
    <div class="card">
        <h3>سفارش شماره {{ order.id }}</h3>
        <p>نام: {{ order.customer }}</p>
        <p>تلفن: {{ order.phone }}</p>
        <p>وضعیت: {{ order.status }}</p>
        <p>توضیحات: {{ order.note or "ندارد" }}</p>
        <h4>اقلام سفارش</h4>
        <ul>
        {% for item in order_items[order.id] %}
            <li>{{ item.food_name }} — {{ item.quantity }} پرس</li>
        {% else %}
            <li>موردی ثبت نشده.</li>
        {% endfor %}
        </ul>
        <form method="post"
              action="{{ url_for('update_status', order_id=order.id) }}">
            <select name="status">
                {% for status in statuses %}
                <option value="{{ status }}"
                    {% if order.status == status %}selected{% endif %}>
                    {{ status }}
                </option>
                {% endfor %}
            </select>
            <button type="submit">ذخیره وضعیت</button>
        </form>
    </div>
    {% else %}
        <div class="card">هنوز سفارشی ثبت نشده است.</div>
    {% endfor %}
</main>
</body>
</html>
"""


# صفحه اصلی
@app.route("/")
def home():
    foods = Food.query.order_by(Food.id).all()
    return render_template_string(HOME_HTML, foods=foods)


# ثبت سفارش
@app.route("/order", methods=["POST"])
def place_order():
    customer = request.form.get("customer", "").strip()
    phone = request.form.get("phone", "").strip()
    note = request.form.get("note", "").strip()

    if not customer or not phone:
        return "لطفاً نام و شماره تماس را وارد کن.", 400

    foods = Food.query.all()
    selected = []

    for food in foods:
        raw_quantity = request.form.get(f"food_{food.id}", "0")
        try:
            quantity = int(raw_quantity)
        except (TypeError, ValueError):
            quantity = 0

        if quantity < 0 or quantity > 50:
            return "تعداد پرس واردشده معتبر نیست.", 400

        if quantity > 0:
            selected.append((food, quantity))

    if not selected:
        return "لطفاً دست‌کم یک غذا انتخاب کن.", 400

    order = Order(customer=customer, phone=phone, note=note)
    db.session.add(order)
    db.session.flush()

    for food, quantity in selected:
        db.session.add(Item(
            order_id=order.id,
            food_name=food.name,
            quantity=quantity
        ))

    db.session.commit()
    return redirect(url_for("order_success", order_id=order.id))


@app.route("/success/<int:order_id>")
def order_success(order_id):
    order = db.session.get(Order, order_id)
    if order is None:
        abort(404)
    return render_template_string(SUCCESS_HTML, order=order)


# صفحه ورود مدیر
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin"))

    error = None

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))

        error = "نام کاربری یا رمز عبور اشتباه است."

    return render_template_string(LOGIN_HTML, error=error)


# پنل مدیریت
@app.route("/admin")
@admin_required
def admin():
    foods = Food.query.order_by(Food.id).all()
    orders = Order.query.order_by(Order.id.desc()).all()

    order_items = {
        order.id: Item.query.filter_by(order_id=order.id).all()
        for order in orders
    }

    statuses = ["جدید", "در حال آماده‌سازی", "آماده", "تحویل داده شد"]

    return render_template_string(
        ADMIN_HTML,
        foods=foods,
        orders=orders,
        order_items=order_items,
        statuses=statuses
    )


# خروج مدیر
@app.route("/admin/logout")
@admin_required
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


# افزودن غذا
@app.route("/admin/add", methods=["POST"])
@admin_required
def add_food():
    name = request.form.get("name", "").strip()
    emoji = request.form.get("emoji", "🍽️").strip() or "🍽️"

    if name:
        db.session.add(Food(name=name, emoji=emoji))
        db.session.commit()

    return redirect(url_for("admin"))


# حذف غذا
@app.route("/admin/delete/<int:food_id>", methods=["POST"])
@admin_required
def delete_food(food_id):
    food = db.session.get(Food, food_id)

    if food:
        db.session.delete(food)
        db.session.commit()

    return redirect(url_for("admin"))


# تغییر وضعیت سفارش
@app.route("/admin/status/<int:order_id>", methods=["POST"])
@admin_required
def update_status(order_id):
    order = db.session.get(Order, order_id)

    allowed_statuses = [
        "جدید", "در حال آماده‌سازی", "آماده", "تحویل داده شد"
    ]
    new_status = request.form.get("status", "")

    if order and new_status in allowed_statuses:
        order.status = new_status
        db.session.commit()

    return redirect(url_for("admin"))


# ساخت جدول‌ها و منوی اولیه در صورت خالی بودن
with app.app_context():
    db.create_all()

    if Food.query.count() == 0:
        db.session.add_all([
            Food(name="قرمه‌سبزی", emoji="🍲"),
            Food(name="قیمه", emoji="🍛"),
            Food(name="ماکارونی", emoji="🍝"),
            Food(name="کتلت", emoji="🥘"),
            Food(name="عدس‌پلو", emoji="🍚"),
        ])
        db.session.commit()
