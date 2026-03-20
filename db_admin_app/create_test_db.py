import sqlite3

DB_PATH = "test.db"


def init_test_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("PRAGMA foreign_keys = ON")

    cur.execute("DROP TABLE IF EXISTS audit_log")
    cur.execute("DROP TABLE IF EXISTS user_roles")
    cur.execute("DROP TABLE IF EXISTS roles")
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
            admin_username TEXT,
            action TEXT,
            details TEXT,
            created_at TEXT
        )
        """
    )

    # Вставка тестовых данных
    cur.execute("INSERT INTO users (username, password, name, email) VALUES (?, ?, ?, ?)",
                ("admin", "admin", "Администратор", "admin@test.com"))
    cur.execute("INSERT INTO users (username, password, name, email) VALUES (?, ?, ?, ?)",
                ("user1", "pass1", "Пользователь 1", "user1@test.com"))

    cur.execute("INSERT INTO roles (name) VALUES (?)", ("admin",))
    cur.execute("INSERT INTO roles (name) VALUES (?)", ("user",))

    cur.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (1, 1))  # admin -> admin
    cur.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (2, 2))  # user1 -> user

    con.commit()
    con.close()
    print("Тестовая БД создана и инициализирована.")


if __name__ == "__main__":
    init_test_db()