#!/usr/bin/env python3
"""
Тестовый скрипт для проверки основных функций приложения
"""

import sqlite3
import os
import sys

def test_databases():
    """Проверка структуры БД"""
    print("=== Проверка структуры БД ===")

    # Проверка admin.db
    if not os.path.exists('admin.db'):
        print("❌ admin.db не найден")
        return False

    con = sqlite3.connect('admin.db')
    tables = [row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    con.close()

    required_tables = ['connections', 'backups', 'admin_audit_log']
    for table in required_tables:
        if table not in tables:
            print(f"❌ Таблица {table} не найдена в admin.db")
            return False

    print("✅ Структура admin.db корректна")

    # Проверка данных в connections
    con = sqlite3.connect('admin.db')
    connections = con.execute("SELECT * FROM connections").fetchall()
    con.close()

    if len(connections) < 2:
        print("❌ Недостаточно подключений в БД")
        return False

    print(f"✅ Найдено {len(connections)} подключений")

    return True

def test_app_import():
    """Проверка импорта приложения"""
    print("\n=== Проверка импорта приложения ===")
    try:
        import app
        print("✅ Приложение импортируется без ошибок")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        return False

def test_templates():
    """Проверка наличия шаблонов"""
    print("\n=== Проверка шаблонов ===")
    required_templates = [
        'base.html', 'login.html', 'dashboard.html', 'databases.html',
        'database_form.html', 'users_list.html', 'user_form.html', 'user_roles.html'
    ]

    for template in required_templates:
        path = f'templates/{template}'
        if not os.path.exists(path):
            print(f"❌ Шаблон {template} не найден")
            return False

    print("✅ Все шаблоны на месте")
    return True

def test_static():
    """Проверка статических файлов"""
    print("\n=== Проверка статических файлов ===")
    required_static = ['static/style.css', 'static/main.js']

    for static_file in required_static:
        if not os.path.exists(static_file):
            print(f"❌ Файл {static_file} не найден")
            return False

    print("✅ Статические файлы на месте")
    return True

def main():
    print("🚀 Запуск тестирования курсовой работы\n")

    tests = [
        test_databases,
        test_app_import,
        test_templates,
        test_static,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"\n📊 Результаты: {passed}/{total} тестов пройдено")

    if passed == total:
        print("🎉 Все тесты пройдены! Приложение готово к использованию.")
        return 0
    else:
        print("⚠️  Найдены проблемы. Проверьте логи выше.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
