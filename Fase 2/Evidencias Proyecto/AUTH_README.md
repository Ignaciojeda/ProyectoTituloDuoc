# Sistema de Login por Roles

## Lo que se agregó

```
auth.py                  Hashing + sesión + dependencias por rol
schemas.py               + LoginRequest, LoginResponse, UsuarioCreate/Update/Out
main.py                  + /login, /logout, /me, /dashboard, /admin, /coordinador, /docente
                         + CRUD de usuarios en /admin/usuarios (solo admin)
                         + SessionMiddleware
                         + / ahora redirige (a login o al dashboard según sesión)

templates/login.html     Formulario de login
templates/base.html      Layout compartido con navbar (rol + logout)
templates/admin.html     Dashboard del administrador
templates/coordinador.html Dashboard del coordinador
templates/docente.html   Dashboard del docente

static/css/login.css     Estilos del login

seed_users.py            Crea usuarios de prueba (uno por rol)

requirements.txt         + passlib[bcrypt], bcrypt, itsdangerous, psycopg[binary]
```

## Cómo funciona el control de acceso

| Dependencia           | Roles permitidos                          |
|-----------------------|-------------------------------------------|
| `require_admin`       | administrador                             |
| `require_coordinador` | coordinador, administrador               |
| `require_docente`     | docente, coordinador, administrador      |
| `require_login`       | cualquier usuario autenticado             |

Uso en una ruta:
```python
@app.post("/sinopticos", dependencies=[Depends(require_coordinador)])
def crear_sinoptico(...): ...

# o si necesitas el usuario en el cuerpo de la función:
@app.get("/mis-clases")
def mis_clases(user: models.Usuario = Depends(require_docente)): ...
```

Si la petición viene del navegador (`Accept: text/html`), un 401 redirige a `/login`.
Si viene de un cliente API (JSON), devuelve 401 con detalle en el body.

## Puesta en marcha

```bash
# 1. Instalar dependencias nuevas
pip install -r "Fase 2/Evidencias Proyecto/requirements.txt"

# 2. Crear usuarios de prueba
python "Fase 2/Evidencias Proyecto/seed_users.py"

# 3. Definir SECRET_KEY en .env (opcional, recomendado)
echo 'SECRET_KEY=una-clave-larga-aleatoria-de-32-bytes' >> .env

# 4. Levantar el servidor
uvicorn main:app --reload
```

## Credenciales de prueba

| Rol            | Email              | Contraseña     | URL tras login |
|----------------|--------------------|----------------|----------------|
| administrador  | admin@duoc.cl      | Admin123!      | `/admin`       |
| coordinador    | coord@duoc.cl      | Coord123!      | `/coordinador` |
| docente        | docente@duoc.cl    | Docente123!    | `/docente`     |

## Endpoints

### Auth
- `GET  /login` — formulario
- `POST /login` — login (form o JSON)
- `GET  /logout` — cerrar sesión
- `GET  /me` — devuelve el usuario actual (JSON, requiere login)

### Dashboards
- `GET  /dashboard` — redirige al dashboard según rol
- `GET  /admin` — solo administrador
- `GET  /coordinador` — coordinador + administrador
- `GET  /docente` — cualquier rol logueado

### Gestión de usuarios (solo administrador)
- `GET    /admin/usuarios` — listar
- `POST   /admin/usuarios` — crear (`{nombre, email, password, rol}`)
- `PATCH  /admin/usuarios/{id}` — actualizar parcial
- `DELETE /admin/usuarios/{id}` — eliminar (no permite auto-eliminarse)

## Login vía API (JSON)

```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@duoc.cl","password":"Admin123!"}' \
  -c cookies.txt
```
La cookie `sinopticos_session` queda guardada para llamadas siguientes.

## Notas de seguridad

- Las contraseñas **jamás** se almacenan en texto plano; se hashean con bcrypt.
- Las cookies de sesión están firmadas (itsdangerous) — no se pueden falsificar.
- `https_only=False` está bien para desarrollo local; cambiar a `True` en producción.
- El `SECRET_KEY` debería estar en `.env`, nunca en el repositorio.
- Para producción, conviene mover `https_only=True` y agregar `SECURE_PROXY_SSL_HEADER`.
