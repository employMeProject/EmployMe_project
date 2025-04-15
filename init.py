import sqlite3
from pathlib import Path

# Путь к вашей базе данных (обычно в папке instance)
db_path =  "mydatabase.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
# Список нужных колонок
columns_to_add = {
    "avatar": "TEXT",
    "about": "TEXT",
    "skills": "TEXT"
}

for column, column_type in columns_to_add.items():
    try:
        cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {column_type}")
        print(f"Колонка '{column}' добавлена.")
    except sqlite3.OperationalError as e:
        print(f"Колонка '{column}' уже существует или другая ошибка: {e}")

conn.commit()
conn.close()
