import csv
import io
import os
import shutil
import sqlite3
from datetime import datetime
from functools import wraps
from flask import (
    Flask,
    Response,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)

app = Flask(__name__)
app.secret_key = "very_secret_key_for_session"  # для продакшена — сменить

DB_PATH = "db_web.db"  # дефолтная, но теперь будет выбираться
ADMIN_DB_PATH = "admin.db"
USERS_PER_PAGE = 5


@app.context_processor
def inject_current_conn_name():
    return {'current_conn_name': get_current_connection_name()}


def get_admin_db_connection():
    con = sqlite3.connect(ADMIN_DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    return con


def get_current_db_path():
    connection_id = session.get("current_connection_id")
    if not connection_id:
        # По умолчанию используем первую доступную
        con = get_admin_db_connection()
        conn = con.execute("SELECT db_path FROM connections ORDER BY id LIMIT 1").fetchone()
        con.close()
        return conn["db_path"] if conn else DB_PATH
    con = get_admin_db_connection()
    conn = con.execute("SELECT db_path FROM connections WHERE id = ?", (connection_id,)).fetchone()
    con.close()
    return conn["db_path"] if conn else DB_PATH


def get_current_connection_name():
    connection_id = session.get("current_connection_id")
    if not connection_id:
        return "Не выбрана"
    con = get_admin_db_connection()
    conn = con.execute("SELECT name FROM connections WHERE id = ?", (connection_id,)).fetchone()
    con.close()
    return conn["name"] if conn else "Неизвестная"


def is_current_connection_read_only():
    connection_id = session.get("current_connection_id")
    if not connection_id:
        return False  # По умолчанию не read-only
    con = get_admin_db_connection()
    conn = con.execute("SELECT read_only FROM connections WHERE id = ?", (connection_id,)).fetchone()
    con.close()
    return bool(conn["read_only"]) if conn else False


def get_db_connection():
    current_path = get_current_db_path()
    con = sqlite3.connect(current_path)
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    return con


def get_user_roles(user_id):
    con = get_db_connection()
    roles = con.execute(
        """
        SELECT r.name
        FROM roles r
        JOIN user_roles ur ON ur.role_id = r.id
        WHERE ur.user_id = ?
        """,
        (user_id,),
    ).fetchall()
    con.close()
    return [r["name"] for r in roles]


def current_roles():
    return session.get("roles", [])


def has_role(role_name):
    return role_name in current_roles()


def is_admin():
    return has_role("admin")


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Необходимо войти как администратор", "error")
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return wrapper


def role_required(*required_roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not session.get("admin_logged_in"):
                flash("Необходимо войти как администратор", "error")
                return redirect(url_for("login"))

            roles = current_roles()
            if not any(r in roles for r in required_roles):
                flash("Недостаточно прав для выполнения действия", "error")
                return redirect(url_for("users_list"))
            return func(*args, **kwargs)

        return wrapper

    return decorator


def write_log(action, details=""):
    if not session.get("admin_logged_in"):
        return
    con = get_admin_db_connection()
    con.execute(
        """
        INSERT INTO admin_audit_log (admin_username, action, details, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            session.get("admin_username", "unknown"),
            action,
            details,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    con.commit()
    con.close()


@app.route("/")
def index():
    if session.get("admin_logged_in"):
        return redirect(url_for("users_list"))
    return redirect(url_for("login"))


# ---------- АВТОРИЗАЦИЯ ----------


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        con = get_db_connection()
        user = con.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password),
        ).fetchone()
        con.close()

        if user:
            roles = get_user_roles(user["id"])
            session["admin_logged_in"] = True
            session["admin_username"] = user["username"]
            session["admin_name"] = user["name"]
            session["admin_id"] = user["id"]
            session["roles"] = roles

            write_log("login", f"Вход пользователя {user['username']}")
            flash("Вы успешно вошли в систему", "success")
            return redirect(url_for("users_list"))
        else:
            flash("Неверное имя пользователя или пароль", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Вы вышли из системы", "info")
    return redirect(url_for("login"))


# ---------- УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ (CRUD) ----------


@app.route("/users")
@login_required
def users_list():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "id")
    role_filter = request.args.get("role", "all")

    sort_map = {
        "id": "users.id",
        "name": "users.name",
        "email": "users.email",
    }
    sort_column = sort_map.get(sort, "users.id")

    base_query = """
        SELECT users.id, users.username, users.name, users.email
        FROM users
    """

    filters = []
    params = []

    if role_filter != "all":
        base_query = """
            SELECT DISTINCT users.id, users.username, users.name, users.email
            FROM users
            JOIN user_roles ur ON ur.user_id = users.id
            JOIN roles r ON r.id = ur.role_id
        """
        filters.append("r.name = ?")
        params.append(role_filter)

    where_clause = " WHERE " + " AND ".join(filters) if filters else ""

    con = get_db_connection()
    total_query = "SELECT COUNT(DISTINCT users.id) FROM users"
    if role_filter != "all":
        total_query += " JOIN user_roles ur ON ur.user_id = users.id JOIN roles r ON r.id = ur.role_id"
        total_query += " WHERE " + " AND ".join(filters)
    total = con.execute(total_query, params).fetchone()[0]

    limit_offset = f" ORDER BY {sort_column} LIMIT ? OFFSET ?"
    users = con.execute(
        base_query + where_clause + limit_offset,
        params + [USERS_PER_PAGE, (page - 1) * USERS_PER_PAGE],
    ).fetchall()

    roles = con.execute("SELECT * FROM roles ORDER BY id").fetchall()
    con.close()

    total_pages = max(1, (total + USERS_PER_PAGE - 1) // USERS_PER_PAGE) if total else 1

    return render_template(
        "users_list.html",
        users=users,
        page=page,
        total_pages=total_pages,
        total=total,
        sort=sort,
        role_filter=role_filter,
        roles=roles,
    )


@app.route("/users/export")
@login_required
@role_required("admin")
def users_export_csv():
    con = get_db_connection()
    users = con.execute(
        "SELECT id, username, name, email FROM users ORDER BY id"
    ).fetchall()
    con.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["ID", "Логин", "Имя", "Email"])

    for u in users:
        writer.writerow([u["id"], u["username"], u["name"], u["email"]])

    csv_data = output.getvalue().encode("utf-8-sig")

    response = Response(csv_data, content_type="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = "attachment; filename=users.csv"
    return response


@app.route("/users/create", methods=["GET", "POST"])
@login_required
@role_required("admin")
def user_create():
    if is_current_connection_read_only():
        flash("Эта база данных открыта только для просмотра. Изменения запрещены.", "error")
        return redirect(url_for("users_list"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()

        if not username or not password or not name or not email:
            flash("Все поля обязательны для заполнения.", "error")
            return render_template("user_form.html", action="create")

        con = get_db_connection()
        try:
            con.execute(
                "INSERT INTO users (username, password, name, email) VALUES (?, ?, ?, ?)",
                (username, password, name, email),
            )
            con.commit()
            write_log("user_create", f"Создан пользователь {name} ({email})")
            flash("Пользователь успешно создан", "success")
            return redirect(url_for("users_list"))
        except sqlite3.IntegrityError as e:
            error_msg = str(e).lower()
            if "username" in error_msg:
                flash("Пользователь с таким логином уже существует.", "error")
            elif "email" in error_msg:
                flash("Пользователь с таким email уже существует.", "error")
            else:
                flash("Такие данные уже существуют в базе.", "error")
        finally:
            con.close()

    return render_template("user_form.html", action="create")


@app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def user_edit(user_id):
    if is_current_connection_read_only():
        flash("Эта база данных открыта только для просмотра. Изменения запрещены.", "error")
        return redirect(url_for("users_list"))

    con = get_db_connection()
    user = con.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    if user is None:
        con.close()
        flash("Пользователь не найден", "error")
        return redirect(url_for("users_list"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not username or not name or not email:
            flash("Все обязательные поля должны быть заполнены.", "error")
            con.close()
            return render_template("user_form.html", action="edit", user=user)

        try:
            if password:
                con.execute(
                    "UPDATE users SET username = ?, password = ?, name = ?, email = ? WHERE id = ?",
                    (username, password, name, email, user_id),
                )
            else:
                con.execute(
                    "UPDATE users SET username = ?, name = ?, email = ? WHERE id = ?",
                    (username, name, email, user_id),
                )
            con.commit()
            write_log("user_update", f"Изменён пользователь id={user_id}")
            flash("Данные пользователя обновлены", "success")
        except sqlite3.IntegrityError as e:
            error_msg = str(e).lower()
            if "username" in error_msg:
                flash("Пользователь с таким логином уже существует.", "error")
            elif "email" in error_msg:
                flash("Пользователь с таким email уже существует.", "error")
            else:
                flash("Такие данные уже существуют в базе.", "error")
        finally:
            con.close()
        return redirect(url_for("users_list"))

    con.close()
    return render_template("user_form.html", action="edit", user=user)


@app.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def user_delete(user_id):
    if is_current_connection_read_only():
        flash("Эта база данных открыта только для просмотра. Изменения запрещены.", "error")
        return redirect(url_for("users_list"))

    con = get_db_connection()
    con.execute("DELETE FROM users WHERE id = ?", (user_id,))
    con.commit()
    con.close()
    write_log("user_delete", f"Удалён пользователь id={user_id}")
    flash("Пользователь удалён", "warning")
    return redirect(url_for("users_list"))


# ---------- УПРАВЛЕНИЕ РОЛЯМИ ПОЛЬЗОВАТЕЛЕЙ ----------


@app.route("/user-roles", methods=["GET", "POST"])
@login_required
@role_required("admin")
def user_roles_manage():
    if request.method == "POST" and is_current_connection_read_only():
        flash("Для текущей базы данных разрешён только режим чтения", "error")
        return redirect(url_for("user_roles_manage"))

    con = get_db_connection()

    if request.method == "POST":
        user_id = request.form.get("user_id", type=int)
        if not user_id:
            flash("Некорректный идентификатор пользователя", "error")
            con.close()
            return redirect(url_for("user_roles_manage"))

        selected_role_ids = request.form.getlist("roles")
        selected_role_ids = [int(rid) for rid in selected_role_ids if rid and str(rid).strip().isdigit()]

        try:
            con.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))
            for role_id in selected_role_ids:
                con.execute(
                    "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                    (user_id, role_id),
                )
            con.commit()
            write_log(
                "user_roles_update",
                f"Обновлены роли пользователя id={user_id} -> {selected_role_ids}",
            )
            flash("Роли пользователя обновлены", "success")
        except Exception as e:
            con.rollback()
            flash(f"Ошибка при обновлении ролей: {e}", "error")

        con.close()
        return redirect(url_for("user_roles_manage"))

    roles = con.execute("SELECT * FROM roles ORDER BY id").fetchall()
    users = con.execute("SELECT * FROM users ORDER BY id").fetchall()

    user_roles_map = {}
    for row in con.execute("SELECT user_id, role_id FROM user_roles").fetchall():
        user_roles_map.setdefault(row["user_id"], set()).add(row["role_id"])
    for u in users:
        user_roles_map.setdefault(u["id"], set())

    con.close()

    return render_template(
        "user_roles.html",
        users=users,
        roles=roles,
        user_roles_map=user_roles_map,
    )


@app.route("/audit-log")
@login_required
@role_required("admin")
def audit_log_view():
    con = get_admin_db_connection()
    logs = con.execute(
        "SELECT * FROM admin_audit_log ORDER BY id DESC LIMIT 200"
    ).fetchall()
    con.close()
    return render_template("audit_log.html", logs=logs)


# ---------- УПРАВЛЕНИЕ ПОДКЛЮЧЕНИЯМИ К БД ----------


@app.route("/dashboard")
@login_required
def dashboard():
    # метрики из admin.db
    admin_con = get_admin_db_connection()
    total_connections = admin_con.execute(
        "SELECT COUNT(*) FROM connections"
    ).fetchone()[0]
    total_backups = admin_con.execute(
        "SELECT COUNT(*) FROM backups"
    ).fetchone()[0]

    # последние записи журнала тоже берем, прежде чем закрыть соединение
    recent_logs = admin_con.execute(
        "SELECT * FROM admin_audit_log ORDER BY id DESC LIMIT 10"
    ).fetchall()
    admin_con.close()

    # статистика из активной БД (если есть путь)
    db_path = get_current_db_path()
    total_users = 0
    roles_stats = []
    if db_path:
        current_con = sqlite3.connect(db_path)
        current_con.row_factory = sqlite3.Row
        total_users = current_con.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]
        roles_stats = current_con.execute("""
            SELECT r.name, COUNT(ur.user_id) as count
            FROM roles r
            LEFT JOIN user_roles ur ON r.id = ur.role_id
            GROUP BY r.id, r.name
            ORDER BY r.name
        """ ).fetchall()
        current_con.close()

    return render_template(
        "dashboard.html",
        total_connections=total_connections,
        total_backups=total_backups,
        total_users=total_users,
        roles_stats=roles_stats,
        recent_logs=recent_logs,
    )


@app.route("/databases")
@login_required
@role_required("admin")
def databases_list():
    con = get_admin_db_connection()
    connections = con.execute("SELECT * FROM connections ORDER BY id").fetchall()
    con.close()
    return render_template("databases.html", connections=connections)


@app.route("/databases/set-active/<int:conn_id>", methods=["POST"])
@login_required
@role_required("admin")
def set_active_database(conn_id):
    con = get_admin_db_connection()
    conn = con.execute("SELECT id, name FROM connections WHERE id = ?", (conn_id,)).fetchone()
    con.close()
    if conn:
        session["current_connection_id"] = conn_id
        write_log("set_active_db", f"Выбрана БД: {conn['name']}")
        flash(f"Активная БД изменена на: {conn['name']}", "success")
    else:
        flash("Подключение не найдено", "error")
    return redirect(url_for("databases_list"))


@app.route("/databases/create", methods=["GET", "POST"])
@login_required
@role_required("admin")
def database_create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        db_path = request.form.get("db_path", "").strip()
        description = request.form.get("description", "").strip()
        read_only = 1 if request.form.get("read_only") else 0

        if not name or not db_path:
            flash("Заполните обязательные поля", "error")
            return render_template("database_form.html", action="create")

        con = get_admin_db_connection()
        try:
            con.execute(
                "INSERT INTO connections (name, db_type, db_path, description, read_only) VALUES (?, 'sqlite', ?, ?, ?)",
                (name, db_path, description, read_only),
            )
            con.commit()
            write_log("db_create", f"Создано подключение: {name} ({db_path})")
            flash("Подключение успешно создано", "success")
            return redirect(url_for("databases_list"))
        except sqlite3.IntegrityError:
            flash("Ошибка: имя подключения уже занято", "error")
        finally:
            con.close()

    return render_template("database_form.html", action="create")


@app.route("/databases/<int:conn_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def database_edit(conn_id):
    con = get_admin_db_connection()
    conn = con.execute("SELECT * FROM connections WHERE id = ?", (conn_id,)).fetchone()
    if conn is None:
        con.close()
        flash("Подключение не найдено", "error")
        return redirect(url_for("databases_list"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        db_path = request.form.get("db_path", "").strip()
        description = request.form.get("description", "").strip()
        read_only = 1 if request.form.get("read_only") else 0

        if not name or not db_path:
            flash("Заполните обязательные поля", "error")
            con.close()
            return render_template("database_form.html", action="edit", connection=conn)

        try:
            con.execute(
                "UPDATE connections SET name = ?, db_path = ?, description = ?, read_only = ? WHERE id = ?",
                (name, db_path, description, read_only, conn_id),
            )
            con.commit()
            write_log("db_update", f"Изменено подключение id={conn_id}")
            flash("Подключение обновлено", "success")
        except sqlite3.IntegrityError:
            flash("Ошибка: имя подключения уже занято", "error")
        finally:
            con.close()
        return redirect(url_for("databases_list"))

    con.close()
    return render_template("database_form.html", action="edit", connection=conn)


@app.route("/databases/<int:conn_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def database_delete(conn_id):
    con = get_admin_db_connection()
    conn = con.execute("SELECT name FROM connections WHERE id = ?", (conn_id,)).fetchone()
    if conn:
        con.execute("DELETE FROM connections WHERE id = ?", (conn_id,))
        con.commit()
        write_log("db_delete", f"Удалено подключение: {conn['name']}")
        flash("Подключение удалено", "warning")
        # Если удалена активная БД, сбросим сессию
        if session.get("current_connection_id") == conn_id:
            session.pop("current_connection_id", None)
    con.close()
    return redirect(url_for("databases_list"))


@app.route("/databases/<int:conn_id>/backup", methods=["POST"])
@login_required
@role_required("admin")
def connection_backup(conn_id):
    con = get_admin_db_connection()
    conn = con.execute("SELECT id, name, db_path FROM connections WHERE id = ?", (conn_id,)).fetchone()
    if conn is None:
        con.close()
        flash("Подключение не найдено", "error")
        return redirect(url_for("databases_list"))

    # Создать папку backups, если не существует
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)

    # Сформировать имя файла с датой/временем
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{conn['name'].replace(' ', '_')}_{timestamp}.sqlite"
    backup_path = os.path.join(backup_dir, backup_filename)

    try:
        # Копировать файл БД
        shutil.copy2(conn['db_path'], backup_path)

        # Записать в таблицу backups
        con.execute(
            "INSERT INTO backups (connection_id, backup_path, created_at) VALUES (?, ?, ?)",
            (conn_id, backup_path, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        con.commit()

        write_log("backup_create", f"Создан бэкап для подключения {conn['name']}: {backup_path}")
        flash(f"Резервная копия создана: {backup_filename}", "success")
    except Exception as e:
        flash(f"Ошибка при создании бэкапа: {e}", "error")
    finally:
        con.close()

    return redirect(url_for("databases_list"))


if __name__ == "__main__":
    app.run(debug=True)
