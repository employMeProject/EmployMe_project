import sqlite3
from datetime import datetime

# Подключение к базе данных
conn = sqlite3.connect('mydatabase.db')
cursor = conn.cursor()

# Получаем информацию о колонках таблицы, например "users"
cursor.execute("PRAGMA table_info(companies);")  # замени 'users' на свою таблицу
columns = cursor.fetchall()

# Выводим названия колонок
for col in columns:
    print(col[1])  # col[1] — это имя колонки