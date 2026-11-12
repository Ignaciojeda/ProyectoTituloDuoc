"""
Pruebas de carga del Sistema de Sinópticos (Locust).

Uso (PowerShell, dentro de la carpeta pruebas):
  $env:LOCUST_EMAIL="usuario.prueba@duocuc.cl"
  $env:LOCUST_PASSWORD="su-clave"
  python -m locust -f locustfile.py --host http://localhost:8000

Por defecto SOLO lee datos y exporta (no modifica la base).

Para incluir las tareas de ESCRITURA (generar un sinóptico aleatorio y crear bloques aleatorios):
  $env:LOCUST_ESCRITURA="1"
Las tareas de escritura crean un sinóptico, lo usan y lo ELIMINAN al terminar, así la base queda como estaba.
Úsalas solo con un usuario de prueba y, de preferencia, en una base de prueba.
"""
import os
import random
import threading

from locust import HttpUser, task, between, events

EMAIL = os.environ.get("LOCUST_EMAIL", "")
PASSWORD = os.environ.get("LOCUST_PASSWORD", "")
ESCRITURA = os.environ.get("LOCUST_ESCRITURA") == "1"

# Respuestas que son reglas del negocio (ya existe, sin asignaturas, choque de horario...) y no fallas del servidor.
ESPERADOS = (400, 404, 409, 422)

_catalogo = {}
_candado = threading.Lock()


@events.test_start.add_listener
def _verifica_credenciales(environment, **kwargs):
    if not EMAIL or not PASSWORD:
        raise SystemExit("Define LOCUST_EMAIL y LOCUST_PASSWORD (usuario coordinador o administrador de PRUEBA).")


class CoordinadorUser(HttpUser):
    """Simula a un coordinador: entra, mira la galería, abre sinópticos, exporta y (opcional) genera."""
    wait_time = between(1, 3)        # pausa entre acciones, como una persona real

    def on_start(self):
        # Un solo login por usuario simulado (cada login hace hash bcrypt y escribe en login_log)
        with self.client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD},
                              name="POST /api/auth/login", catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"Login falló: {r.status_code} {r.text[:120]}")
                self.stop()
                return
            token = r.json()["access_token"]
        self.client.headers.update({"Authorization": f"Bearer {token}"})
        self.sinoptico_ids = []
        self._cargar_ids()
        if ESCRITURA:
            self._cargar_catalogo()

    def _cargar_ids(self):
        r = self.client.get("/api/sinopticos", name="GET /api/sinopticos")
        if r.status_code == 200:
            self.sinoptico_ids = [s["id"] for s in r.json() if isinstance(s, dict) and "id" in s]

    def _cargar_catalogo(self):
        """Catálogos usados para elegir datos al azar; se piden una sola vez para todos los usuarios."""
        with _candado:
            if _catalogo:
                return
            for clave, ruta in (("carreras", "/api/carreras"), ("planes", "/api/planes-estudio"),
                                ("semestres", "/api/semestres"), ("asignaturas", "/api/asignaturas"),
                                ("profesores", "/api/profesores"), ("salas", "/api/salas"),
                                ("bloques", "/api/bloques-horario")):
                r = self.client.get(ruta, name=f"SETUP {ruta}")
                _catalogo[clave] = r.json() if r.status_code == 200 else []

    def _un_sinoptico(self):
        return random.choice(self.sinoptico_ids) if self.sinoptico_ids else None

    def _get_sinoptico(self, plantilla, nombre, sid):
        """GET sobre un sinóptico. Si otro usuario simulado ya lo eliminó (los de escritura son temporales),
        el 404 no es una falla del sistema: se descarta ese id y no se cuenta como error."""
        with self.client.get(plantilla.format(id=sid), name=nombre, catch_response=True) as r:
            if r.status_code == 404:
                r.success()
                if sid in self.sinoptico_ids:
                    self.sinoptico_ids.remove(sid)

    # ---------- Lecturas (la mayor parte del uso real) ----------
    @task(5)
    def galeria(self):
        self.client.get("/api/sinopticos", name="GET /api/sinopticos")
        self.client.get("/api/sinopticos/eventos", name="GET /api/sinopticos/eventos")

    @task(6)
    def abrir_sinoptico(self):
        sid = self._un_sinoptico()
        if sid is None:
            return
        self._get_sinoptico("/api/sinopticos/{id}/eventos", "GET /api/sinopticos/{id}/eventos", sid)
        self._get_sinoptico("/api/sinopticos/{id}/filtros", "GET /api/sinopticos/{id}/filtros", sid)

    @task(3)
    def catalogos(self):
        for ruta in ("/api/carreras", "/api/salas", "/api/bloques-horario", "/api/profesores"):
            self.client.get(ruta, name=f"GET {ruta}")

    @task(2)
    def salas_ocupacion(self):
        self.client.get("/api/salas/eventos", name="GET /api/salas/eventos")

    @task(2)
    def disponibilidad_profesores(self):
        self.client.get("/api/profesores/disponibilidad", name="GET /api/profesores/disponibilidad")
        self.client.get("/api/profesores/jornadas", name="GET /api/profesores/jornadas")

    # ---------- Operaciones pesadas ----------
    @task(1)
    def exportar_excel(self):
        sid = self._un_sinoptico()
        if sid is not None:
            self._get_sinoptico("/api/sinopticos/{id}/excel", "GET /api/sinopticos/{id}/excel", sid)

    @task(1)
    def exportar_pdf(self):
        sid = self._un_sinoptico()
        if sid is not None:
            self._get_sinoptico("/api/sinopticos/{id}/pdf", "GET /api/sinopticos/{id}/pdf", sid)

    @task(1)
    def sabana(self):
        self.client.get("/api/reportes/sabana", name="GET /api/reportes/sabana")

    # ---------- Escritura (solo con LOCUST_ESCRITURA=1) ----------
    def _post(self, ruta, cuerpo, nombre):
        """POST que trata las reglas del negocio (404/409...) como respuesta válida y solo marca falla los errores reales."""
        with self.client.post(ruta, json=cuerpo, name=nombre, catch_response=True) as r:
            if r.status_code in ESPERADOS:
                r.success()
            elif r.status_code >= 400:
                r.failure(f"{r.status_code}: {r.text[:150]}")
            return r

    def _borrar(self, sid):
        self.client.delete(f"/api/sinopticos/{sid}", name="DELETE /api/sinopticos/{id} (limpieza)")

    def _datos_aleatorios(self):
        carreras, semestres = _catalogo.get("carreras"), _catalogo.get("semestres")
        if not carreras or not semestres:
            return None
        carrera = random.choice(carreras)
        planes = [p for p in _catalogo.get("planes", []) if p.get("carrera_id") == carrera["id"]]
        return {
            "carrera_id": carrera["id"],
            "plan_estudio_id": random.choice(planes)["id"] if planes else None,
            "semestre_id": random.choice(semestres)["id"],
            "jornada": random.choice(["diurno", "vespertino"]),
            "nivel_semestral": random.randint(1, 8),
        }

    if ESCRITURA:
        @task(1)
        def generar_sinoptico_aleatorio(self):
            """Genera automáticamente un sinóptico con carrera, semestre, jornada y nivel al azar, y luego lo elimina."""
            cuerpo = self._datos_aleatorios()
            if not cuerpo:
                return
            r = self._post("/api/sinopticos/generar", cuerpo, "POST /api/sinopticos/generar (aleatorio)")
            if r.status_code == 200:
                try:
                    nuevo = r.json().get("sinoptico_id")
                except ValueError:
                    nuevo = None
                if nuevo and nuevo not in self.sinoptico_ids:     # solo borra lo que creó esta prueba
                    self._borrar(nuevo)

        @task(1)
        def crear_bloques_aleatorios(self):
            """Crea un sinóptico vacío, le agrega 1 a 3 bloques al azar (asignatura, profesor, sala y horario) y lo elimina."""
            cuerpo = self._datos_aleatorios()
            if not cuerpo or not _catalogo.get("asignaturas") or not _catalogo.get("bloques"):
                return
            r = self._post("/api/sinopticos", cuerpo, "POST /api/sinopticos (vacío, aleatorio)")
            if r.status_code != 201:
                return
            try:
                sid = r.json().get("sinoptico_id")
            except ValueError:
                return
            if not sid or sid in self.sinoptico_ids:
                return
            try:
                for _ in range(random.randint(1, 3)):
                    profesor = random.choice(_catalogo["profesores"]) if _catalogo.get("profesores") else None
                    sala = random.choice(_catalogo["salas"]) if _catalogo.get("salas") else None
                    self._post("/api/sinopticos/items", {
                        "sinoptico_id": sid,
                        "asignatura_id": random.choice(_catalogo["asignaturas"])["id"],
                        "profesor_id": profesor["id"] if profesor else None,
                        "sala_id": sala["id"] if sala else None,
                        "bloque_horario_id": random.choice(_catalogo["bloques"])["id"],
                        "capacidad_inicial": random.choice([20, 30, 40]),
                        "tipo": random.choice(["teorica", "practica"]),
                        "color": "#3B82F6",
                    }, "POST /api/sinopticos/items (bloque aleatorio)")
            finally:
                self._borrar(sid)