import sqlite3

# Создание служебной БД для админки
ADMIN_DB_PATH = "admin.db"

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
    con.execute("""
        INSERT OR IGNORE INTO connections (name, db_type, db_path, description, read_only)
        VALUES ('Основная БД', 'sqlite', 'db_web.db', 'Основная база данных приложения', 0)
    """)

    con.execute("""
        INSERT OR IGNORE INTO connections (name, db_type, db_path, description, read_only)
        VALUES ('Тестовая БД', 'sqlite', 'test.db', 'Тестовая база для экспериментов', 0)
    """)

    con.execute("""
        INSERT OR IGNORE INTO connections (name, db_type, db_path, description, read_only)
        VALUES ('БД только чтение', 'sqlite', 'db_web.db', 'Демонстрация режима только чтение', 1)
    """)

    con.commit()
    con.close()
    print("Служебная БД создана и инициализирована.")

if __name__ == "__main__":
    create_admin_db()