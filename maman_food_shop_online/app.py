from flask import (
    Flask, render_template, request,
    redirect, url_for, session, abort
)
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from hmac import compare_digest
from markupsafe import escape
from urllib.parse import urlparse
import os

app = Flask(__name__)

# تنظیمات امنیتی
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

# تنظیم دیتابیس
database_url = os.environ.get("DATABASE_URL")

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://", "postgresql://", 1
        )
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///maman_food.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("RENDER") == "true"
)

db = SQLAlchemy(app)


class Food(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    emoji = db.Column(db.String(20), default="🍽️")


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    note = db.Column(db.Text, default="")
    status = db.Column(db.String(50), default="جدید")


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, nullable=False)
    food_name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)


def init_db():
    db.create_all()

    if Food.query.count() == 0:
        db.session.add_all([
            Food(name="قرمه‌سبزی", emoji="🍲"),
            Food(name="قیمه", emoji="🥘"),
            Food(name="ماکارونی", emoji="🍝"),
            Food(name="کتلت", emoji="🥩"),
            Food(name="عدس‌پلو", emoji="🍚"),
        ])
        db.session.commit()


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped


LOGIN_PAGE = """
<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ورود مدیریت مامان‌پز</title>
<style>
body {
  font-family: Tahoma, sans-serif;
  background: #fff7ed;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 90vh;
  margin: 0;
}
main {
  background: white;
  padding: 28px;
  border-radius: 18px;
  width: min(340px, 85%);
  box-shadow: 0 5px 24px #0001;
}
input, button {
  box-sizing: border-box;
  width: 100%;
  padding: 12px;
  margin-top: 12px;
  border-radius: 9px;
  font: inherit;
}
input { border: 1px solid #ddd; }
button {
  border: 0;
  background: #c65d32;
  color: white;
  cursor: pointer;
}
.error { color: #b42318; }
</style>
</head>
<body>
<main>
<h2>🍲 ورود به پنل مامان‌پز</h2>
<p>نام کاربری و رمز مدیریت را وارد کن.</p>
{% if error %}<p class="error">{{ error }}</p>{% endif %}
<form method="post" action="{{ url_for('admin_login') }}">
<input type="text" name="username" placeholder="نام کاربری"
       autocomplete="username" required>
<input type="password" name="password" placeholder="رمز عبور"
       autocomplete="current-password" required>
<button type="submit">ورود به پنل</button>
</form>
</main>
</body>
</html>
"""


@app.route("/")
def home():
    foods = Food.query.order_by(Food.id.desc()).all()
    return render_template("index.html", foods=foods)


@app.post("/order")
def order():
    customer = request.form.get("customer", "").strip()
    phone = request.form.get("phone", "").strip()
    note = request.form.get("note", "").strip()

    if not customer or not phone:
        return "نام و شماره تماس را وارد کنید.", 400

    selected = []

    for food in Food.query.all():
        try:
            quantity = int(
                request.form.get("food_" + str(food.id), 0)
            )
        except (ValueError, TypeError):
            quantity = 0

        if quantity < 0:
            return "تعداد غذا معتبر نیست.", 400

        if quantity > 0:
            selected.append((food.name, quantity))

    if not selected:
        return "حداقل یک غذا انتخاب کنید.", 400

    new_order = Order(
        customer=customer,
        phone=phone,
        note=note
    )
    db.session.add(new_order)
    db.session.flush()

    for name, quantity in selected:
        db.session.add(Item(
            order_id=new_order.id,
            food_name=name,
            quantity=quantity
        ))

    db.session.commit()

    return redirect(url_for("success", oid=new_order.id))


@app.route("/success/<int:oid>")
def success(oid):
    return render_template("success.html", oid=oid)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if not ADMIN_USERNAME or not ADMIN_PASSWORD:
            error = "تنظیمات ورود در سرور کامل نیست."
        elif (
            compare_digest(username, ADMIN_USERNAME)
            and compare_digest(password, ADMIN_PASSWORD)
        ):
            session.clear()
            session["admin_logged_in"] = True

            next_url = request.args.get("next", "")
            parsed = urlparse(next_url)

            if not parsed.netloc and next_url.startswith("/"):
                return redirect(next_url)

            return redirect(url_for("admin"))
        else:
            error = "نام کاربری یا رمز عبور اشتباه است."

    return render_template_string_login(error)


def render_template_string_login(error):
    from flask import render_template_string
    return render_template_string(LOGIN_PAGE, error=error)


@app.post("/admin/logout")
@admin_required
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin():
    orders = Order.query.order_by(Order.id.desc()).all()
    data = [
        (order, Item.query.filter_by(order_id=order.id).all())
        for order in orders
    ]
    foods = Food.query.order_by(Food.id.desc()).all()

    return render_template(
        "admin.html",
        orders=data,
        foods=foods
    )


@app.post("/admin/status/<int:oid>")
@admin_required
def change(oid):
    order = Order.query.get_or_404(oid)
    allowed = [
        "جدید",
        "در حال آماده‌سازی",
        "آماده شد",
        "تحویل داده شد"
    ]

    status = request.form.get("status", "جدید")

    if status in allowed:
        order.status = status
        db.session.commit()

    return redirect(url_for("admin"))


@app.post("/admin/add")
@admin_required
def add():
    name = request.form.get("name", "").strip()
    emoji = request.form.get("emoji", "🍽️").strip() or "🍽️"

    if name and len(name) <= 120:
        db.session.add(Food(name=name, emoji=emoji[:20]))
        db.session.commit()

    return redirect(url_for("admin"))


@app.post("/admin/delete/<int:fid>")
@admin_required
def delete(fid):
    food = Food.query.get_or_404(fid)
    db.session.delete(food)
    db.session.commit()

    return redirect(url_for("admin"))


with app.app_context():
    init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
