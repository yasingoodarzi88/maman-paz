import os
import secrets
import string
from datetime import datetime
from functools import wraps

from flask import Flask, request, redirect, url_for, session, render_template_string, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-in-render")

database_url = os.environ.get("DATABASE_URL", "sqlite:///maman_food.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

db = SQLAlchemy(app)

# Change these values. Keep the GitHub repository private if you put a real password here.
ADMIN_USERNAME = "1356Af1392"
ADMIN_PASSWORD = "123456"

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


class Food(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    emoji = db.Column(db.String(20), default="🍽️")
    image_filename = db.Column(db.String(255), nullable=True)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    note = db.Column(db.Text, default="")
    status = db.Column(db.String(40), default="جدید")
    tracking_code = db.Column(db.String(32), unique=True, nullable=True)
    kitchen_message = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    food_name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)


def migrate_existing_database():
    """Add new columns without dropping existing orders or foods."""
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    if "food" in tables:
        cols = {c["name"] for c in inspector.get_columns("food")}
        if "image_filename" not in cols:
            db.session.execute(text("ALTER TABLE food ADD COLUMN image_filename VARCHAR(255)"))

    if "order" in tables:
        cols = {c["name"] for c in inspector.get_columns("order")}
        if "tracking_code" not in cols:
            db.session.execute(text('ALTER TABLE "order" ADD COLUMN tracking_code VARCHAR(32)'))
        if "kitchen_message" not in cols:
            db.session.execute(text('ALTER TABLE "order" ADD COLUMN kitchen_message TEXT'))
        if "created_at" not in cols:
            db.session.execute(text('ALTER TABLE "order" ADD COLUMN created_at TIMESTAMP'))
    db.session.commit()


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def new_tracking_code():
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "MP" + "".join(secrets.choice(alphabet) for _ in range(8))
        if not Order.query.filter_by(tracking_code=code).first():
            return code


with app.app_context():
    db.create_all()
    migrate_existing_database()
    for old_order in Order.query.filter(
        (Order.tracking_code.is_(None)) | (Order.tracking_code == "")
    ).all():
        old_order.tracking_code = "MP" + secrets.token_hex(4).upper()
    db.session.commit()
    if Food.query.count() == 0:
        db.session.add_all([
            Food(name="قرمه‌سبزی", emoji="🍲"),
            Food(name="قیمه", emoji="🍛"),
            Food(name="ماکارونی", emoji="🍝"),
            Food(name="کتلت", emoji="🥘"),
            Food(name="عدس‌پلو", emoji="🍚"),
        ])
        db.session.commit()


STYLE = """
<style>
*{box-sizing:border-box}body{font-family:Tahoma,Arial,sans-serif;direction:rtl;background:#fff8f0;color:#30251f;margin:0;padding:18px}
main{max-width:1050px;margin:0 auto}header{text-align:center;padding:12px 0 22px}
h1,h2{color:#a84c24}p{line-height:1.8}.card{background:white;padding:18px;margin:12px 0;border-radius:15px;box-shadow:0 3px 12px #51290012}
input,textarea,select,button{font-family:inherit;font-size:15px;padding:11px;margin:5px 0;max-width:100%;border-radius:8px}
input,textarea,select{border:1px solid #ded5ce;background:white}button,.button{display:inline-block;background:#a84c24;color:white;border:0;cursor:pointer;text-decoration:none;padding:11px 16px}
.danger{background:#b3261e}.menu-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.food-card{overflow:hidden;padding:0}.food-photo{width:100%;height:220px;object-fit:cover;display:block;background:#f1e5d9}
.food-placeholder{height:220px;display:flex;align-items:center;justify-content:center;background:#f1e5d9;font-size:64px}
.food-content{padding:16px}.quantity{width:105px}.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.form-grid label,.field{display:block}.form-grid input{width:100%}.status{display:inline-block;border-radius:20px;padding:6px 12px;background:#fff0d9;color:#7a431e;font-weight:bold}
.order-item{border-bottom:1px solid #eee;padding:8px 0}.muted{color:#74685f;font-size:13px}
@media(max-width:650px){.menu-grid{grid-template-columns:1fr}.food-photo,.food-placeholder{height:200px}.form-grid{grid-template-columns:1fr}}
</style>
"""

HOME_HTML = """
<!doctype html><html lang="fa"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>مامان‌پز</title>""" + STYLE + """</head><body><main>
<header><h1>🍲 مامان‌پز</h1><p>غذای مورد علاقه‌ات رو انتخاب کن، تعداد پرس رو بنویس و سفارشت رو ثبت کن.</p></header>
<form method="post" action="{{ url_for('place_order') }}"><h2>منوی غذاها</h2><div class="menu-grid">
{% for food in foods %}<section class="card food-card">
{% if food.image_filename %}<img class="food-photo" src="{{ url_for('static', filename='uploads/' ~ food.image_filename) }}" alt="{{ food.name }}">
{% else %}<div class="food-placeholder">{{ food.emoji or "🍽️" }}</div>{% endif %}
<div class="food-content"><h3>{{ food.name }}</h3><label for="food_{{ food.id }}">تعداد پرس:</label>
<input class="quantity" id="food_{{ food.id }}" type="number" name="food_{{ food.id }}" min="0" max="50" value="0"></div></section>
{% else %}<div class="card">هنوز غذایی به منو اضافه نشده است.</div>{% endfor %}</div>
<div class="card"><h2>مشخصات سفارش</h2><div class="form-grid">
<label>نام شما<input name="customer" required maxlength="120" placeholder="نام و نام خانوادگی"></label>
<label>شماره تماس<input name="phone" required maxlength="40" placeholder="شماره تماس"></label></div>
<label class="field">توضیحات (اختیاری)<textarea name="note" rows="3" style="width:100%" placeholder="مثلاً توضیحات سفارش"></textarea></label>
<button type="submit">ثبت سفارش</button></div></form>
<div class="card"><h2>پیگیری سفارش</h2><p>کدی رو که بعد از ثبت سفارش گرفتی وارد کن تا وضعیت و پیام آشپز رو ببینی.</p>
<form method="get" action="{{ url_for('track_order') }}"><input name="code" required placeholder="مثلاً MP12AB34CD"><button type="submit">پیگیری</button></form></div>
</main></body></html>
"""

SUCCESS_HTML = """
<!doctype html><html lang="fa"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>سفارش ثبت شد</title>""" + STYLE + """</head><body><main><div class="card">
<h1>✅ سفارشت ثبت شد!</h1><p>شماره سفارش: {{ order.id }}</p><p>کد پیگیری مخصوص شما:</p>
<h2 style="direction:ltr;text-align:center">{{ order.tracking_code }}</h2><p>این کد رو نگه دار تا وضعیت سفارش رو ببینی.</p>
<a class="button" href="{{ url_for('track_order', code=order.tracking_code) }}">پیگیری سفارش</a> <a class="button" href="{{ url_for('home') }}">بازگشت به منو</a>
</div></main></body></html>
"""

TRACK_HTML = """
<!doctype html><html lang="fa"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>پیگیری سفارش</title>""" + STYLE + """</head><body><main><div class="card">
<h1>🔎 پیگیری سفارش</h1><form method="get" action="{{ url_for('track_order') }}"><input name="code" required value="{{ code }}" placeholder="کد پیگیری"><button type="submit">جست‌وجو</button></form>
{% if searched and not order %}<p>این کد پیگیری پیدا نشد. کد رو دوباره بررسی کن.</p>{% endif %}
{% if order %}<h2>سفارش شماره {{ order.id }}</h2><p>وضعیت: <span class="status">{{ order.status }}</span></p>
<p>پیام آشپز: {{ order.kitchen_message or "هنوز پیامی ثبت نشده است." }}</p><h3>غذاهای سفارش</h3>
{% for item in items %}<div class="order-item">{{ item.food_name }} — {{ item.quantity }} پرس</div>{% endfor %}
<p class="muted">اطلاعات تماس شما در صفحه پیگیری نمایش داده نمی‌شود.</p>{% endif %}
<a class="button" href="{{ url_for('home') }}">بازگشت به منو</a></div></main></body></html>
"""

LOGIN_HTML = """
<!doctype html><html lang="fa"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>ورود مدیر</title>""" + STYLE + """</head><body><main><div class="card">
<h1>ورود به پنل مامان‌پز</h1>{% if error %}<p style="color:#b3261e">{{ error }}</p>{% endif %}
<form method="post"><label class="field">نام کاربری<input name="username" required autocomplete="username"></label>
<label class="field">رمز عبور<input name="password" type="password" required autocomplete="current-password"></label><button type="submit">ورود</button></form></div></main></body></html>
"""

ADMIN_HTML = """
<!doctype html><html lang="fa"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>پنل مامان‌پز</title>""" + STYLE + """</head><body><main>
<h1>پنل مدیریت مامان‌پز</h1><p><a class="button" href="{{ url_for('home') }}">صفحه سفارش</a> <a class="button" href="{{ url_for('admin_logout') }}">خروج</a></p>
<div class="card"><h2>افزودن غذا</h2><form method="post" action="{{ url_for('add_food') }}" enctype="multipart/form-data">
<label class="field">نام غذا<input name="name" required maxlength="120"></label>
<label class="field">ایموجی (اگر عکس نداشتی)<input name="emoji" maxlength="20" value="🍽️"></label>
<label class="field">عکس غذا (اختیاری؛ JPG، PNG، WEBP یا GIF تا ۵ مگابایت)<input type="file" name="photo" accept=".jpg,.jpeg,.png,.webp,.gif,image/*"></label>
<button type="submit">افزودن غذا</button></form></div>
<h2>غذاهای منو</h2><div class="menu-grid">{% for food in foods %}<div class="card">
{% if food.image_filename %}<img class="food-photo" src="{{ url_for('static', filename='uploads/' ~ food.image_filename) }}" alt="{{ food.name }}">{% else %}<div class="food-placeholder">{{ food.emoji or "🍽️" }}</div>{% endif %}
<h3>{{ food.name }}</h3><form method="post" action="{{ url_for('update_food_image', food_id=food.id) }}" enctype="multipart/form-data">
<label class="field">تغییر عکس<input type="file" name="photo" required accept=".jpg,.jpeg,.png,.webp,.gif"></label><button type="submit">ذخیره عکس جدید</button></form>
<form method="post" action="{{ url_for('delete_food', food_id=food.id) }}" onsubmit="return confirm('این غذا از منو حذف شود؟')"><button class="danger" type="submit">حذف غذا</button></form>
</div>{% else %}<p>هنوز غذایی ثبت نشده.</p>{% endfor %}</div>
<h2>سفارش‌ها</h2>{% for order in orders %}<div class="card"><h3>سفارش شماره {{ order.id }}</h3>
<p>کد پیگیری: <b style="direction:ltr;display:inline-block">{{ order.tracking_code }}</b></p><p>نام: {{ order.customer }} | تلفن: {{ order.phone }}</p>
<p>وضعیت فعلی: <span class="status">{{ order.status }}</span></p><p>توضیحات مشتری: {{ order.note or "ندارد" }}</p><h4>اقلام سفارش</h4>
{% for item in order_items[order.id] %}<div class="order-item">{{ item.food_name }} — {{ item.quantity }} پرس</div>{% endfor %}
<form method="post" action="{{ url_for('update_status', order_id=order.id) }}"><label class="field">وضعیت سفارش<select name="status">{% for status in statuses %}<option value="{{ status }}" {% if order.status == status %}selected{% endif %}>{{ status }}</option>{% endfor %}</select></label>
<label class="field">پیام آشپز برای مشتری<textarea name="kitchen_message" rows="2" style="width:100%" placeholder="مثلاً غذات تا نیم ساعت دیگه آماده می‌شه">{{ order.kitchen_message or "" }}</textarea></label><button type="submit">ذخیره وضعیت و پیام</button></form>
</div>{% else %}<div class="card">هنوز سفارشی ثبت نشده است.</div>{% endfor %}</main></body></html>
"""


@app.route("/")
def home():
    return render_template_string(HOME_HTML, foods=Food.query.order_by(Food.id).all())


@app.route("/order", methods=["POST"])
def place_order():
    customer = request.form.get("customer", "").strip()
    phone = request.form.get("phone", "").strip()
    note = request.form.get("note", "").strip()
    if not customer or not phone:
        abort(400, "لطفاً نام و شماره تماس را وارد کن.")

    selected = []
    for food in Food.query.all():
        try:
            quantity = int(request.form.get(f"food_{food.id}", "0"))
        except (TypeError, ValueError):
            quantity = 0
        if quantity < 0 or quantity > 50:
            abort(400, "تعداد پرس معتبر نیست.")
        if quantity:
            selected.append((food, quantity))
    if not selected:
        abort(400, "لطفاً حداقل یک غذا انتخاب کن.")

    order = Order(customer=customer, phone=phone, note=note,
                  status="جدید", tracking_code=new_tracking_code())
    db.session.add(order)
    db.session.flush()
    for food, quantity in selected:
        db.session.add(Item(order_id=order.id, food_name=food.name, quantity=quantity))
    db.session.commit()
    return redirect(url_for("order_success", order_id=order.id))


@app.route("/success/<int:order_id>")
def order_success(order_id):
    order = db.session.get(Order, order_id)
    if order is None:
        abort(404)
    return render_template_string(SUCCESS_HTML, order=order)


@app.route("/track")
def track_order():
    code = request.args.get("code", "").strip().upper()
    order = Order.query.filter_by(tracking_code=code).first() if code else None
    items = Item.query.filter_by(order_id=order.id).all() if order else []
    return render_template_string(TRACK_HTML, code=code, order=order, items=items, searched=bool(code))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin"))
    error = None
    if request.method == "POST":
        if request.form.get("username", "") == ADMIN_USERNAME and request.form.get("password", "") == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))
        error = "نام کاربری یا رمز عبور اشتباه است."
    return render_template_string(LOGIN_HTML, error=error)


@app.route("/admin")
@admin_required
def admin():
    foods = Food.query.order_by(Food.id).all()
    orders = Order.query.order_by(Order.id.desc()).all()
    order_items = {order.id: Item.query.filter_by(order_id=order.id).all() for order in orders}
    statuses = ["جدید", "در حال آماده‌سازی", "آماده", "تحویل داده شد"]
    return render_template_string(ADMIN_HTML, foods=foods, orders=orders, order_items=order_items, statuses=statuses)


@app.route("/admin/logout")
@admin_required
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


@app.route("/admin/add", methods=["POST"])
@admin_required
def add_food():
    name = request.form.get("name", "").strip()
    emoji = request.form.get("emoji", "🍽️").strip() or "🍽️"
    photo = request.files.get("photo")
    filename = None
    if not name:
        abort(400, "نام غذا را وارد کن.")
    if photo and photo.filename:
        if not allowed_file(photo.filename):
            abort(400, "فرمت عکس پشتیبانی نمی‌شود.")
        ext = secure_filename(photo.filename).rsplit(".", 1)[1].lower()
        filename = secrets.token_hex(12) + "." + ext
        photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    db.session.add(Food(name=name, emoji=emoji, image_filename=filename))
    db.session.commit()
    return redirect(url_for("admin"))


@app.route("/admin/food/<int:food_id>/image", methods=["POST"])
@admin_required
def update_food_image(food_id):
    food = db.session.get(Food, food_id)
    if food is None:
        abort(404)
    photo = request.files.get("photo")
    if not photo or not photo.filename or not allowed_file(photo.filename):
        abort(400, "یک عکس معتبر انتخاب کن.")
    ext = secure_filename(photo.filename).rsplit(".", 1)[1].lower()
    filename = secrets.token_hex(12) + "." + ext
    photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    food.image_filename = filename
    db.session.commit()
    return redirect(url_for("admin"))


@app.route("/admin/delete/<int:food_id>", methods=["POST"])
@admin_required
def delete_food(food_id):
    food = db.session.get(Food, food_id)
    if food:
        if food.image_filename:
            path = os.path.join(app.config["UPLOAD_FOLDER"], food.image_filename)
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except OSError:
                pass
        db.session.delete(food)
        db.session.commit()
    return redirect(url_for("admin"))


@app.route("/admin/status/<int:order_id>", methods=["POST"])
@admin_required
def update_status(order_id):
    order = db.session.get(Order, order_id)
    allowed = ["جدید", "در حال آماده‌سازی", "آماده", "تحویل داده شد"]
    status = request.form.get("status", "")
    message = request.form.get("kitchen_message", "").strip()
    if order and status in allowed:
        order.status = status
        order.kitchen_message = message
        db.session.commit()
    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(debug=True)
