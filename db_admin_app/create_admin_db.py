import sqlite3
import os

# Создание служебной БД для админки
ADMIN_DB_PATH = os.path.join(os.path.dirname(__file__), "admin.db")

def create_admin_db():
    con = sqlite3.connect(ADMIN_DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")

    # Таблица подключений к БД
    con.execute("""
        CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            db_type TEXT NOT NULL DEFAULT 'sqlite',
            db_path TEXT NOT NULL,
            description TEXT,
            read_only INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Таблица резервных копий
    con.execute("""
        CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            connection_id INTEGER NOT NULL,
            backup_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (connection_id) REFERENCES connections(id) ON DELETE CASCADE
        )
    """)

    # Журнал действий админки
    con.execute("""
        CREATE TABLE IF NOT EXISTS admin_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_username TEXT,
            action TEXT,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Вставим тестовые данные
    main_db_path = os.path.join(os.path.dirname(__file__), "db_web.db")
    test_db_path = os.path.join(os.path.dirname(__file__), "test.db")
    con.execute("""
        INSERT OR IGNORE INTO connections (name, db_type, db_path, description, read_only)
        VALUES ('Основная БД', 'sqlite', ?, 'Основная база данных приложения', 0)
    """, (main_db_path,))

    con.execute("""
        INSERT OR IGNORE INTO connections (name, db_type, db_path, description, read_only)
        VALUES ('Тестовая БД', 'sqlite', ?, 'Тестовая база для экспериментов', 0)
    """, (test_db_path,))

    con.execute("""
        INSERT OR IGNORE INTO connections (name, db_type, db_path, description, read_only)
        VALUES ('БД только чтение', 'sqlite', ?, 'Демонстрация режима только чтение', 1)
    """, (main_db_path,))

    con.commit()
    con.close()
    print("Служебная БД создана и инициализирована.")

if __name__ == "__main__":
    create_admin_db()
