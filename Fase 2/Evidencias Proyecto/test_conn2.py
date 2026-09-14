import psycopg

try:
    conn = psycopg.connect(
        dbname="sinoptico",
        user="postgres",
        password="postgres",
        host="127.0.0.1",
        port="5432",
    )
    print("✅ Conexión exitosa")
    conn.close()
except Exception as e:
    print("❌ ERROR:", repr(e))