import sqlite3

DB_PATH = "db_web.db"


def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("PRAGMA foreign_keys = ON")

    cur.execute("DROP TABLE IF EXISTS audit_log")
    cur.execute("DROP TABLE IF EXISTS user_roles")
    cur.execute("DROP TABLE IF EXISTS roles")
    cur.execute("DROP TABLE IF EXISTS admins")
    cur.execute("DROP TABLE IF EXISTS users")

    cur.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE user_roles (
            user_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, role_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_username TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.executemany(
        "INSERT INTO roles (name) VALUES (?)",
        [("admin",), ("viewer",)],
    )

    cur.executemany(
        "INSERT INTO users (username, password, name, email) VALUES (?, ?, ?, ?)",
        [
            ("admin", "admin", "Главный администратор", "admin@example.com"),
            ("viewer", "viewer", "Наблюдатель", "viewer@example.com"),
            ("user1", "user1", "Иван Иванов", "ivan@example.com"),
            ("user2", "user2", "Петр Петров", "petr@example.com"),
        ],
    )

    cur.executemany(
        "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
        [
            (1, 1),  # admin -> role admin
            (1, 2),  # admin -> role viewer
            (2, 2),  # viewer -> role viewer
        ],
    )

    con.commit()
    con.close()
    print("База данных инициализирована (users, roles, user_roles, audit_log)")


if __name__ == "__main__":
    init_db()
