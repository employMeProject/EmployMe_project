import sqlite3
from datetime import datetime

# Подключение к базе данных
conn = sqlite3.connect('mydatabase.db')
cursor = conn.cursor()

# Получаем информацию о колонках таблицы, например "users"
# Показывает структуру таблицы 'companies'
cursor.execute("PRAGMA table_info(applications)")
columns = cursor.fetchall()

print("Схема таблицы 'applications':")
for col in columns:
    print(col)

conn.close()