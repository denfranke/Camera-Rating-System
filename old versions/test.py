import pyodbc

print(pyodbc.drivers())



conn_str = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=PhotoQualityAnalyzer;"
    "Trusted_Connection=yes;"
)

try:
    conn = pyodbc.connect(conn_str)
    print("✅ Подключение успешно!")
    conn.close()
except Exception as e:
    print(f"❌ Ошибка: {e}")