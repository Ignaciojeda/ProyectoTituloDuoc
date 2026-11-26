# bloqueo de cuenta por intentos de login fallidos

import requests
BASE = "https://web.icymoss-aa983815.westus2.azurecontainerapps.io/api"
EMAIL_PRUEBA = "l.yagi@profesor.duoc.cl"  # una que exista, da lo mismo el rol

for i in range(7):
    r = requests.post(f"{BASE}/auth/login", json={"email": EMAIL_PRUEBA, "password": f"clave-mala-{i}"})
    print(i, r.status_code, r.json().get("detail"))

