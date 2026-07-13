# سیستم مدیریت کارهای روزانه با GraphQL

این پروژه یک Mini Task Manager است که با Python، کتابخانه Strawberry، فریم‌ورک FastAPI و پایگاه داده SQLite پیاده‌سازی شده است. داده‌ها برخلاف یک ساختار درون‌حافظه‌ای پس از توقف برنامه نیز باقی می‌مانند.

## قابلیت‌ها

- دریافت همه کارها و فیلتر اختیاری بر اساس وضعیت یا برچسب
- دریافت یک کار مشخص با شناسه
- ایجاد، ویرایش و حذف کار
- تغییر مستقل وضعیت کار میان `TODO`، `DOING` و `DONE`
- تعریف چند برچسب برای هر کار و استفاده مجدد از برچسب‌های هم‌نام
- دریافت فهرست برچسب‌ها یا یک برچسب با شناسه و پیمایش کارهای هر برچسب
- اعتبارسنجی عنوان، شناسه و نام برچسب
- ذخیره پایدار داده‌ها در SQLite و حذف خودکار روابط یک کار هنگام حذف آن

## مدل داده

رابطه Task و Tag از نوع چندبه‌چند است و با جدول واسط `task_tags` نگهداری می‌شود:

```text
tasks 1 --- * task_tags * --- 1 tags
```

هر Task شامل `id`، `title`، `description`، `dueDate`، `status` و `tags` است. هر Tag نیز شامل `id`، `name` و فیلد قابل‌پیمایش `tasks` است. تاریخ سررسید از Scalar استاندارد `Date` در Strawberry استفاده می‌کند و در قالب `YYYY-MM-DD` ارسال می‌شود.

## اجرا

پروژه به Python 3.10 یا جدیدتر نیاز دارد. در PowerShell و از داخل پوشه `HW4-Practical` دستورات زیر را اجرا کنید:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app
```

پس از اجرا، محیط تعاملی GraphiQL در آدرس زیر در دسترس است:

```text
http://127.0.0.1:8000/graphql
```

مسیر `http://127.0.0.1:8000/health` نیز سلامت سرویس را بررسی می‌کند. فایل دیتابیس به‌صورت پیش‌فرض با نام `task_manager.db` ساخته می‌شود. مسیر آن را می‌توان با متغیر محیطی `TASK_MANAGER_DB_PATH` تغییر داد.

## نمونه عملیات GraphQL

ایجاد کار:

```graphql
mutation {
  createTask(
    input: {
      title: "تکمیل تمرین میکروسرویس"
      description: "پیاده‌سازی API با GraphQL"
      dueDate: "2026-07-20"
      tags: ["دانشگاه", "GraphQL"]
    }
  ) {
    id
    title
    status
    dueDate
    tags { id name }
  }
}
```

دریافت کارهای در حال انجام:

```graphql
query {
  tasks(status: DOING) {
    id
    title
    description
    dueDate
    status
    tags { id name }
  }
}
```

دریافت یک کار:

```graphql
query {
  task(id: "1") {
    id
    title
    status
    tags { name }
  }
}
```

ویرایش بخشی از اطلاعات کار؛ فیلدهای ارسال‌نشده بدون تغییر می‌مانند و مقدار `null` توضیح یا تاریخ را پاک می‌کند:

```graphql
mutation {
  updateTask(
    id: "1"
    input: { description: "نسخه نهایی", dueDate: null, tags: ["backend"] }
  ) {
    id
    title
    description
    dueDate
    tags { name }
  }
}
```

تغییر وضعیت:

```graphql
mutation {
  changeTaskStatus(id: "1", status: DONE) {
    id
    title
    status
  }
}
```

حذف کار:

```graphql
mutation {
  deleteTask(id: "1")
}
```

## اجرای تست‌ها

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

تست‌ها چرخه کامل ایجاد، دریافت، فیلتر، ویرایش، تغییر وضعیت و حذف را به همراه مدیریت رابطه برچسب‌ها و خطاهای اعتبارسنجی بررسی می‌کنند.
