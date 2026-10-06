from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
database_url = os.environ.get("DATABASE_URL")
if database_url:
    database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///maman_food.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Food(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(120),nullable=False)
    emoji=db.Column(db.String(20),default="🍽️")

class Order(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    customer=db.Column(db.String(120),nullable=False)
    phone=db.Column(db.String(50),nullable=False)
    note=db.Column(db.Text,default="")
    status=db.Column(db.String(50),default="جدید")

class Item(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    order_id=db.Column(db.Integer,nullable=False)
    food_name=db.Column(db.String(120),nullable=False)
    quantity=db.Column(db.Integer,nullable=False)

def init_db():
    db.create_all()
    if Food.query.count()==0:
        db.session.add_all([
            Food(name="قرمه‌سبزی",emoji="🍲"),Food(name="قیمه",emoji="🥘"),
            Food(name="ماکارونی",emoji="🍝"),Food(name="کتلت",emoji="🥩"),
            Food(name="عدس‌پلو",emoji="🍚")
        ])
        db.session.commit()

@app.route("/")
def home():
    return render_template("index.html",foods=Food.query.order_by(Food.id.desc()).all())

@app.post("/order")
def order():
    customer=request.form.get("customer","").strip()
    phone=request.form.get("phone","").strip()
    note=request.form.get("note","").strip()
    selected=[]
    for f in Food.query.all():
        try:q=int(request.form.get("food_"+str(f.id),0))
        except:q=0
        if q>0:selected.append((f.name,q))
    if not customer or not phone or not selected:
        return "نام، شماره و حداقل یک غذا را وارد/انتخاب کنید.",400
    o=Order(customer=customer,phone=phone,note=note)
    db.session.add(o); db.session.flush()
    db.session.add_all([Item(order_id=o.id,food_name=n,quantity=q) for n,q in selected])
    db.session.commit()
    return redirect(url_for("success",oid=o.id))

@app.route("/success/<int:oid>")
def success(oid): return render_template("success.html",oid=oid)

@app.route("/admin")
def admin():
    orders=Order.query.order_by(Order.id.desc()).all()
    data=[(o,Item.query.filter_by(order_id=o.id).all()) for o in orders]
    return render_template("admin.html",orders=data,foods=Food.query.order_by(Food.id.desc()).all())

@app.post("/admin/status/<int:oid>")
def change(oid):
    o=Order.query.get_or_404(oid); o.status=request.form.get("status","جدید")
    db.session.commit(); return redirect(url_for("admin"))

@app.post("/admin/add")
def add():
    name=request.form.get("name","").strip()
    emoji=request.form.get("emoji","🍽️").strip() or "🍽️"
    if name:
        db.session.add(Food(name=name,emoji=emoji)); db.session.commit()
    return redirect(url_for("admin"))

@app.post("/admin/delete/<int:fid>")
def delete(fid):
    f=Food.query.get_or_404(fid); db.session.delete(f); db.session.commit()
    return redirect(url_for("admin"))

with app.app_context():
    init_db()

if __name__=="__main__":
    port=int(os.environ.get("PORT",5001))
    app.run(host="0.0.0.0",port=port,debug=True)
