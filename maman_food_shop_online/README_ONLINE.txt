نسخه آنلاین آشپزخانه مامان

این نسخه برای انتشار روی Render آماده است.
ساختار پروژه:
- app.py
- requirements.txt
- Procfile
- render.yaml
- templates/
- static/

برای اجرای محلی:
pip install -r requirements.txt
python app.py

برای آنلاین شدن، کد را در یک Git repository قرار دهید و در Render به عنوان Web Service وصل کنید.
برای سفارش‌ها و غذاهای آنلاین، DATABASE_URL باید به یک PostgreSQL متصل باشد.
