import psycopg2
import traceback

try:
    conn = psycopg2.connect(
        dbname="sinoptico",
        user="postgres",
        password="postgres",
        host="127.0.0.1",
        port="5432",
        connect_timeout=5,
    )
    print("✅ Conexión exitosa")
    conn.close()
except Exception:
    print("---- TRACEBACK COMPLETO ----")
    traceback.print_exc()