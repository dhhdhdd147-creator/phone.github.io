from __future__ import annotations

from functools import wraps

from flask import Flask, redirect, render_template, request, session, url_for

from config import debug, port, secret_key
from db import fetchall, fetchone, init_db_schema_if_needed, execute


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = secret_key()

ROLE_ADMIN = "admin"
ROLE_CLIENT = "client"
PUBLIC_ENDPOINTS = {"static", "login", "logout"}


def _q_param(name: str) -> str:
    return (request.args.get(name) or "").strip()


def status_label(status_value: int) -> str:
    return "Подключен" if int(status_value) == 1 else "Отключен"


def current_role() -> str | None:
    role = session.get("role")
    return role if role in (ROLE_ADMIN, ROLE_CLIENT) else None


def is_admin() -> bool:
    return current_role() == ROLE_ADMIN


def admin_only(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_admin():
            return redirect(url_for("home"))
        return view(*args, **kwargs)

    return wrapped


@app.context_processor
def inject_role_flags():
    role = current_role()
    return {"current_role": role, "is_admin": role == ROLE_ADMIN, "is_client": role == ROLE_CLIENT}


@app.before_request
def require_auth():
    if request.endpoint in (None, *PUBLIC_ENDPOINTS):
        return
    if current_role() is None:
        return redirect(url_for("login"))


@app.get("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = (request.form.get("role") or "").strip().lower()
        if role in (ROLE_ADMIN, ROLE_CLIENT):
            session["role"] = role
            return redirect(url_for("home"))
    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.before_request
def ensure_schema():
    # Создаем схему только при первом запуске/отсутствии таблиц.
    # Для Access это может быть тяжело, но для учебного проекта допустимо.
    if request.endpoint in (None, *PUBLIC_ENDPOINTS):
        return
    init_db_schema_if_needed()


@app.get("/subscribers")
def subscribers_list():
    q = _q_param("q")
    # Поиск по ФИО/паспорту/адресу.
    if q:
        rows = fetchall(
            """
            SELECT
                s.[Id],
                s.[FullName],
                s.[PassportId],
                s.[Address],
                (SELECT p.[Number]
                 FROM [Phones] p
                 WHERE p.[SubscriberId] = s.[Id]
                 ORDER BY p.[Id] DESC
                 LIMIT 1
                ) AS [PhoneNumber]
            FROM [Subscribers] s
            WHERE s.[FullName] LIKE ? OR s.[PassportId] LIKE ? OR s.[Address] LIKE ?
            ORDER BY s.[Id] DESC
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%"),
        )
    else:
        rows = fetchall(
            """
            SELECT
                s.[Id],
                s.[FullName],
                s.[PassportId],
                s.[Address],
                (SELECT p.[Number]
                 FROM [Phones] p
                 WHERE p.[SubscriberId] = s.[Id]
                 ORDER BY p.[Id] DESC
                 LIMIT 1
                ) AS [PhoneNumber]
            FROM [Subscribers] s
            ORDER BY s.[Id] DESC
            """
        )

    subscribers = [
        {"Id": r[0], "FullName": r[1], "PassportId": r[2], "Address": r[3], "PhoneNumber": r[4]}
        for r in rows
    ]
    return render_template("subscribers_list.html", subscribers=subscribers, q=q)


@app.get("/subscribers/new")
@admin_only
def subscribers_new():
    return render_template("subscribers_form.html", mode="create", item=None)


@app.post("/subscribers/new")
@admin_only
def subscribers_create():
    full_name = (request.form.get("full_name") or "").strip()
    passport_id = (request.form.get("passport_id") or "").strip() or None
    address = (request.form.get("address") or "").strip() or None
    if not full_name:
        return redirect(url_for("subscribers_new"))

    execute(
        "INSERT INTO [Subscribers] ([FullName], [PassportId], [Address]) VALUES (?,?,?)",
        (full_name, passport_id, address),
    )
    return redirect(url_for("subscribers_list"))


@app.get("/subscribers/<int:subscriber_id>")
def subscribers_details(subscriber_id: int):
    row = fetchone(
        "SELECT [Id], [FullName], [PassportId], [Address] FROM [Subscribers] WHERE [Id]=?",
        (subscriber_id,),
    )
    if not row:
        return redirect(url_for("subscribers_list"))
    item = {"Id": row[0], "FullName": row[1], "PassportId": row[2], "Address": row[3]}

    phones_rows = fetchall(
        """
        SELECT [Id], [Number], [Operator], [Status]
        FROM [Phones]
        WHERE [SubscriberId]=?
        ORDER BY [Id] DESC
        """,
        (subscriber_id,),
    )
    phones = [
        {"Id": r[0], "Number": r[1], "Operator": r[2], "Status": r[3], "StatusText": status_label(r[3])}
        for r in phones_rows
    ]

    return render_template("subscribers_form.html", mode="edit", item=item, phones=phones)


@app.post("/subscribers/<int:subscriber_id>/edit")
@admin_only
def subscribers_update(subscriber_id: int):
    full_name = (request.form.get("full_name") or "").strip()
    passport_id = (request.form.get("passport_id") or "").strip() or None
    address = (request.form.get("address") or "").strip() or None
    if not full_name:
        return redirect(url_for("subscribers_details", subscriber_id=subscriber_id))

    execute(
        """
        UPDATE [Subscribers]
        SET [FullName]=?, [PassportId]=?, [Address]=?
        WHERE [Id]=?
        """,
        (full_name, passport_id, address, subscriber_id),
    )
    return redirect(url_for("subscribers_details", subscriber_id=subscriber_id))


@app.post("/subscribers/<int:subscriber_id>/delete")
@admin_only
def subscribers_delete(subscriber_id: int):
    # Чтобы не ломать целостность, обнуляем связь у телефонов.
    execute(
        "UPDATE [Phones] SET [SubscriberId]=NULL WHERE [SubscriberId]=?",
        (subscriber_id,),
    )
    execute("DELETE FROM [Subscribers] WHERE [Id]=?", (subscriber_id,))
    return redirect(url_for("subscribers_list"))


@app.get("/phones")
def phones_list():
    q = _q_param("q")
    if q:
        rows = fetchall(
            """
            SELECT
                [Phones].[Id],
                [Phones].[Number],
                [Phones].[Operator],
                [Phones].[Status],
                [Phones].[SubscriberId],
                [Subscribers].[FullName]
            FROM [Phones]
            LEFT JOIN [Subscribers] ON [Phones].[SubscriberId] = [Subscribers].[Id]
            WHERE
                [Phones].[Number] LIKE ?
                OR [Phones].[Operator] LIKE ?
                OR [Subscribers].[FullName] LIKE ?
            ORDER BY [Phones].[Id] DESC
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%"),
        )
    else:
        rows = fetchall(
            """
            SELECT
                [Phones].[Id],
                [Phones].[Number],
                [Phones].[Operator],
                [Phones].[Status],
                [Phones].[SubscriberId],
                [Subscribers].[FullName]
            FROM [Phones]
            LEFT JOIN [Subscribers] ON [Phones].[SubscriberId] = [Subscribers].[Id]
            ORDER BY [Phones].[Id] DESC
            """
        )

    phones = [
        {
            "Id": r[0],
            "Number": r[1],
            "Operator": r[2],
            "Status": r[3],
            "SubscriberId": r[4],
            "SubscriberName": r[5],
            "StatusText": status_label(r[3]),
        }
        for r in rows
    ]
    return render_template("phones_list.html", phones=phones, q=q)


@app.get("/phones/new")
@admin_only
def phones_new():
    # Если переходят с конкретного абонента, предвыбираем его.
    default_subscriber_id_raw = (request.args.get("subscriber_id") or "").strip()
    default_subscriber_id = int(default_subscriber_id_raw) if default_subscriber_id_raw.isdigit() else None

    subscribers = fetchall("SELECT [Id], [FullName] FROM [Subscribers] ORDER BY [FullName]")
    subscribers_items = [{"Id": r[0], "FullName": r[1]} for r in subscribers]
    return render_template(
        "phones_form.html",
        mode="create",
        item=None,
        subscribers=subscribers_items,
        default_subscriber_id=default_subscriber_id,
    )


@app.post("/phones/new")
@admin_only
def phones_create():
    number = (request.form.get("number") or "").strip()
    operator = (request.form.get("operator") or "").strip() or None
    status_raw = request.form.get("status") or "1"
    status = 1 if str(status_raw) == "1" else 0

    subscriber_id_raw = (request.form.get("subscriber_id") or "").strip()
    if not subscriber_id_raw:
        return redirect(url_for("phones_new"))
    subscriber_id = int(subscriber_id_raw)

    # Валидация: абонент должен существовать.
    existing = fetchone("SELECT [Id] FROM [Subscribers] WHERE [Id]=?", (subscriber_id,))
    if not existing:
        return redirect(url_for("phones_new"))

    if not number:
        return redirect(url_for("phones_new"))

    # Валидация номера: только цифры и до 11 знаков.
    if (not number.isdigit()) or len(number) > 11:
        return redirect(url_for("phones_new"))

    execute(
        """
        INSERT INTO [Phones] ([Number], [Operator], [Status], [SubscriberId])
        VALUES (?,?,?,?)
        """,
        (number, operator, status, subscriber_id),
    )
    return redirect(url_for("phones_list"))


@app.get("/phones/<int:phone_id>")
def phones_details(phone_id: int):
    row = fetchone(
        """
        SELECT [Id], [Number], [Operator], [Status], [SubscriberId]
        FROM [Phones]
        WHERE [Id]=?
        """,
        (phone_id,),
    )
    if not row:
        return redirect(url_for("phones_list"))

    subscribers = fetchall("SELECT [Id], [FullName] FROM [Subscribers] ORDER BY [FullName]")
    subscribers_items = [{"Id": r[0], "FullName": r[1]} for r in subscribers]

    item = {"Id": row[0], "Number": row[1], "Operator": row[2], "Status": row[3], "SubscriberId": row[4]}

    subscriber_detail = fetchone(
        """
        SELECT [Id], [FullName], [PassportId], [Address]
        FROM [Subscribers]
        WHERE [Id]=?
        """,
        (row[4],),
    )
    subscriber_detail_obj = (
        {
            "Id": subscriber_detail[0],
            "FullName": subscriber_detail[1],
            "PassportId": subscriber_detail[2],
            "Address": subscriber_detail[3],
        }
        if subscriber_detail
        else None
    )
    return render_template(
        "phones_form.html",
        mode="edit",
        item=item,
        subscribers=subscribers_items,
        subscriber_detail=subscriber_detail_obj,
    )


@app.post("/phones/<int:phone_id>/edit")
@admin_only
def phones_update(phone_id: int):
    number = (request.form.get("number") or "").strip()
    operator = (request.form.get("operator") or "").strip() or None
    status_raw = request.form.get("status") or "1"
    status = 1 if str(status_raw) == "1" else 0

    subscriber_id_raw = (request.form.get("subscriber_id") or "").strip()
    if not subscriber_id_raw:
        return redirect(url_for("phones_details", phone_id=phone_id))
    subscriber_id = int(subscriber_id_raw)

    existing = fetchone("SELECT [Id] FROM [Subscribers] WHERE [Id]=?", (subscriber_id,))
    if not existing:
        return redirect(url_for("phones_details", phone_id=phone_id))

    if not number:
        return redirect(url_for("phones_details", phone_id=phone_id))

    # Валидация номера: только цифры и до 11 знаков.
    if (not number.isdigit()) or len(number) > 11:
        return redirect(url_for("phones_details", phone_id=phone_id))

    execute(
        """
        UPDATE [Phones]
        SET [Number]=?, [Operator]=?, [Status]=?, [SubscriberId]=?
        WHERE [Id]=?
        """,
        (number, operator, status, subscriber_id, phone_id),
    )
    return redirect(url_for("phones_details", phone_id=phone_id))


@app.post("/phones/<int:phone_id>/delete")
@admin_only
def phones_delete(phone_id: int):
    execute("DELETE FROM [Phones] WHERE [Id]=?", (phone_id,))
    return redirect(url_for("phones_list"))


if __name__ == "__main__":
    # Запуск:
    # 1) (Опционально) укажите SQLITE_DB_PATH
    # 2) python app.py
    app.run(host="0.0.0.0", port=port(), debug=debug())

