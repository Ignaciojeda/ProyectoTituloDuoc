from fastapi import FastAPI, Request, Depends, HTTPException, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request as StarletteRequest
from collections import defaultdict
import os
import secrets

from database import engine, get_db, Base
import models
import schemas
from auth import (
    authenticate_user,
    hash_password,
    require_login,
    require_admin,
    require_coordinador,
    require_docente,
)

app = FastAPI()

# Sesión firmada por cookie (requerida para auth).
# En producción, definir SECRET_KEY en el .env (mínimo 32 bytes aleatorios).
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY") or secrets.token_urlsafe(32),
    session_cookie="sinopticos_session",
    max_age=60 * 60 * 8,  # 8 horas
    same_site="lax",
    https_only=False,  # cambiar a True en producción con HTTPS
)

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Crea las tablas en Postgres (si no existen) al levantar el servidor
Base.metadata.create_all(bind=engine)

# diccionario de palabras clave
PALABRA_CLAVE_AREA = {
    "informatica": ["programacion", "base de datos", "software", "sistemas"],
    "redes": ["redes"],
    "matematica": ["matematica", "algebra", "calculo"],
    # aca se pueden agregar mas basado en las asignaturas reales
}

def area_para_asignatura(nombre_asignatura: str):
    nombre = nombre_asignatura.lower()
    for area, palabras in PALABRA_CLAVE_AREA.items():
        if any(p in nombre for p in palabras):
            return area
    return None


@app.get("/")
def inicio(request: Request):
    # Si hay sesión activa, redirige al dashboard correspondiente;
    # si no, al formulario de login.
    user_id = request.session.get("user_id")
    if user_id:
        rol = request.session.get("rol", "docente")
        return RedirectResponse(url=_home_for_role(rol), status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/pag2")
def segunda(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="pag2.html",
        context={}
    )

@app.get("/sinoptico")
def segunda(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="sinopticos.html",
        context={}
    )

# --- conexión---
@app.get("/asignaturas")
def listar_asignaturas(carrera_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Asignatura).filter(models.Asignatura.activo == True)
    if carrera_id is not None:
        query = query.join(
            models.PlanEstudio, models.Asignatura.plan_estudio_id == models.PlanEstudio.id
        ).filter(models.PlanEstudio.carrera_id == carrera_id)
    return query.all()

# NUEVCO: ruta para crear asignaturas usando el esquema AsignaturaCreate y devolviendo AsignaturaOut
@app.post("/asignaturas", response_model=schemas.AsignaturaOut)
def crear_asignatura(datos: schemas.AsignaturaCreate, db: Session = Depends(get_db)):
    nueva = models.Asignatura(**datos.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@app.get("/carreras", response_model=list[schemas.CarreraOut])
def listar_carreras(db: Session = Depends(get_db)):
    return db.query(models.Carrera).filter(models.Carrera.activo == True).order_by(models.Carrera.nombre).all()

@app.post("/carreras", response_model=schemas.CarreraOut)
def crear_carrera(datos: schemas.CarreraCreate, db: Session = Depends(get_db)):
    nueva = models.Carrera(**datos.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@app.get("/planes-estudio", response_model=list[schemas.PlanEstudioOut])
def listar_planes_estudio(db: Session = Depends(get_db)):
    return db.query(models.PlanEstudio).filter(models.PlanEstudio.activo == True).all()

@app.post("/planes-estudio", response_model=schemas.PlanEstudioOut)
def crear_plan_estudio(datos: schemas.PlanEstudioCreate, db: Session = Depends(get_db)):
    nuevo = models.PlanEstudio(**datos.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@app.get("/semestres", response_model=list[schemas.SemestreOut])
def listar_semestres(db: Session = Depends(get_db)):
    return db.query(models.Semestre).filter(models.Semestre.activo == True).order_by(
        models.Semestre.anio.desc(), models.Semestre.numero.desc()
    ).all()

@app.post("/semestres", response_model=schemas.SemestreOut)
def crear_semestre(datos: schemas.SemestreCreate, db: Session = Depends(get_db)):
    nuevo = models.Semestre(**datos.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@app.get("/profesores", response_model=list[schemas.ProfesorOut])
def listar_profesores(db: Session = Depends(get_db)):
    return db.query(models.Profesor).filter(models.Profesor.activo == True).all()

@app.post("/profesores", response_model=schemas.ProfesorOut)
def crear_profesor(datos: schemas.ProfesorCreate, db: Session = Depends(get_db)):
    nuevo = models.Profesor(**datos.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@app.get("/salas", response_model=list[schemas.SalaOut])
def listar_salas(db: Session = Depends(get_db)):
    return db.query(models.Sala).filter(models.Sala.activo == True).all()

@app.post("/salas", response_model=schemas.SalaOut)
def crear_sala(datos: schemas.SalaCreate, db: Session = Depends(get_db)):
    nueva = models.Sala(**datos.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@app.get("/bloques-horario", response_model=list[schemas.BloqueHorarioOut])
def listar_bloques_horario(db: Session = Depends(get_db)):
    return db.query(models.BloqueHorario).order_by(
        models.BloqueHorario.dia_semana, models.BloqueHorario.hora_inicio
    ).all()

@app.post("/bloques-horario", response_model=schemas.BloqueHorarioOut)
def crear_bloque_horario(datos: schemas.BloqueHorarioCreate, db: Session = Depends(get_db)):
    nuevo = models.BloqueHorario(**datos.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

# NUEVO: ruta para generar sinoptico(s)
@app.post("/sinopticos/generar")
def generar_sinoptico(datos: schemas.GenerarSinopticoRequest, db: Session = Depends(get_db)):
    asignaturas = db.query(models.Asignatura).join(
        models.PlanEstudio, models.Asignatura.plan_estudio_id == models.PlanEstudio.id
    ).filter(
        models.PlanEstudio.carrera_id == datos.carrera_id,
        models.Asignatura.activo == True
    ).all()

    if not asignaturas:
        raise HTTPException(status_code=404, detail="No se encontraron asignaturas para la carrera especificada.")

    jornada = asignaturas[0].jornada
    bloques = db.query(models.BloqueHorario).filter(
        models.BloqueHorario.jornada == jornada
    ).order_by(models.BloqueHorario.dia_semana, models.BloqueHorario.hora_inicio).all()

    profesores = db.query(models.Profesor).filter(models.Profesor.activo == True).all()
    salas = db.query(models.Sala).filter(models.Sala.activo == True).all()

    profesor_ocupado = defaultdict(set)
    sala_ocupada = defaultdict(set)

    nuevo_sinoptico = models.Sinoptico(carrera_id=datos.carrera_id, semestre_id=datos.semestre_id)
    db.add(nuevo_sinoptico)
    db.flush()  # Asegura que el ID del sinoptico esté disponible

    sin_asignar = []

    profesor_carga = defaultdict(int)
    sala_carga = defaultdict(int)

    for asignatura in asignaturas:
            area_requerida = area_para_asignatura(asignatura.nombre)
            candidatos_prof = sorted(profesores, key=lambda p: (
                0 if (area_requerida and p.area_docente.value == area_requerida) else 1,
                profesor_carga[p.id]
            ))
            candidatos_sala = sorted(salas, key=lambda s: sala_carga[s.id])
    
            asignado = False
            for b in bloques:
                for p in candidatos_prof:
                    if b.id in profesor_ocupado[p.id]:
                        continue
                    for s in candidatos_sala:
                        if b.id in sala_ocupada[s.id]:
                            continue
                        profesor_ocupado[p.id].add(b.id)
                        sala_ocupada[s.id].add(b.id)
                        profesor_carga[p.id] += 1
                        sala_carga[s.id] += 1
    
                        item = models.SinopticoItem(
                            sinoptico_id=nuevo_sinoptico.id,
                            asignatura_id=asignatura.id,
                            profesor_id=p.id,
                            sala_id=s.id,
                            bloque_horario_id=b.id
                        )
                        db.add(item)
                        asignado = True
                        break
                    if asignado:
                        break
                if asignado:
                    break
    
            if not asignado:
                sin_asignar.append(asignatura.codigo)
    
    db.commit()
    db.refresh(nuevo_sinoptico)
    
    return {
        "sinoptico_id": nuevo_sinoptico.id,
        "asignaturas_sin_asignar": sin_asignar
    }


@app.get("/sinopticos")
def listar_sinopticos(db: Session = Depends(get_db)):
    filas = (
        db.query(models.Sinoptico, models.Carrera, models.Semestre)
        .join(models.Carrera, models.Sinoptico.carrera_id == models.Carrera.id)
        .join(models.Semestre, models.Sinoptico.semestre_id == models.Semestre.id)
        .order_by(models.Sinoptico.creado_en.desc())
        .all()
    )
    return [
        {
            "id": sinoptico.id,
            "carrera": carrera.nombre,
            "semestre": f"{semestre.anio}-{semestre.numero}",
            "creado_en": sinoptico.creado_en,
        }
        for sinoptico, carrera, semestre in filas
    ]


@app.get("/sinopticos/{sinoptico_id}/eventos")
def eventos_sinoptico(sinoptico_id: int, db: Session = Depends(get_db)):
    filas = (
        db.query(models.SinopticoItem, models.Asignatura, models.Profesor, models.Sala, models.BloqueHorario)
        .join(models.Asignatura, models.SinopticoItem.asignatura_id == models.Asignatura.id)
        .outerjoin(models.Profesor, models.SinopticoItem.profesor_id == models.Profesor.id)
        .outerjoin(models.Sala, models.SinopticoItem.sala_id == models.Sala.id)
        .join(models.BloqueHorario, models.SinopticoItem.bloque_horario_id == models.BloqueHorario.id)
        .filter(models.SinopticoItem.sinoptico_id == sinoptico_id)
        .all()
    )

    if not filas:
        raise HTTPException(status_code=404, detail="Sinóptico no encontrado o sin asignaturas asignadas.")

    eventos = []
    for item, asignatura, profesor, sala, bloque in filas:
        eventos.append({
            "title": asignatura.nombre,
            "daysOfWeek": [bloque.dia_semana],
            "startTime": bloque.hora_inicio.strftime("%H:%M:%S"),
            "endTime": bloque.hora_fin.strftime("%H:%M:%S"),
            "extendedProps": {
                "codigo": asignatura.codigo,
                "profesor": f"{profesor.nombre} {profesor.apellido}" if profesor else "Sin asignar",
                "sala": sala.nombre if sala else "Sin asignar",
                "jornada": bloque.jornada.value,
            }
        })
    return eventos

@app.post("/sinopticos", response_model=schemas.SinopticoOut)
def crear_sinoptico_vacio(datos: schemas.SinopticoCreate, db: Session = Depends(get_db)):
    nuevo = models.Sinoptico(**datos.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@app.post("/sinopticos/items", response_model=schemas.SinopticoItemOut)
def agregar_item_sinoptico(datos: schemas.SinopticoItemCreate, db: Session = Depends(get_db)):
    sinoptico = db.query(models.Sinoptico).filter(models.Sinoptico.id == datos.sinoptico_id).first()
    if not sinoptico:
        raise HTTPException(status_code=404, detail="El sinóptico indicado no existe.")

    if datos.profesor_id is not None:
        choque_profesor = db.query(models.SinopticoItem).filter(
            models.SinopticoItem.profesor_id == datos.profesor_id,
            models.SinopticoItem.bloque_horario_id == datos.bloque_horario_id,
        ).first()
        if choque_profesor:
            raise HTTPException(status_code=400, detail="Ese profesor ya tiene una clase asignada en ese bloque horario.")

    if datos.sala_id is not None:
        choque_sala = db.query(models.SinopticoItem).filter(
            models.SinopticoItem.sala_id == datos.sala_id,
            models.SinopticoItem.bloque_horario_id == datos.bloque_horario_id,
        ).first()
        if choque_sala:
            raise HTTPException(status_code=400, detail="Esa sala ya está ocupada en ese bloque horario.")

    nuevo_item = models.SinopticoItem(**datos.model_dump())
    db.add(nuevo_item)
    db.commit()
    db.refresh(nuevo_item)
    return nuevo_item


@app.delete("/sinopticos/items/{item_id}")
def eliminar_item_sinoptico(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.SinopticoItem).filter(models.SinopticoItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="El ítem indicado no existe.")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ===========================================================================
# AUTENTICACIÓN Y AUTORIZACIÓN
# ===========================================================================

def _home_for_role(rol: str) -> str:
    """Devuelve la URL del dashboard según el rol."""
    return {
        "administrador": "/admin",
        "coordinador": "/coordinador",
        "docente": "/docente",
    }.get(rol.lower(), "/dashboard")


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, error: str | None = None, next: str | None = None):
    """Muestra el formulario de login."""
    # Si ya hay sesión activa, redirige al dashboard
    if request.session.get("user_id"):
        rol = request.session.get("rol", "docente")
        return RedirectResponse(url=_home_for_role(rol), status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
    request=request,
    name="login.html",
    context={"error": error, "next": next}
)


@app.post("/login")
async def login_submit(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Acepta tanto form (HTML) como JSON (API).
    - Form: redirige al dashboard correspondiente al rol.
    - JSON: devuelve {id, nombre, email, rol}.
    """
    content_type = request.headers.get("content-type", "")
    is_json = "application/json" in content_type

    if is_json:
        try:
            payload = await request.json()
            data = schemas.LoginRequest(**payload)
            email = data.email
            password = data.password
        except Exception:
            raise HTTPException(status_code=400, detail="Payload inválido")
    else:
        form = await request.form()
        email = (form.get("email") or "").strip().lower()
        password = form.get("password") or ""
        next_url = form.get("next") or None

    user = authenticate_user(db, email, password)

    if not user:
        if is_json:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
            )
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Credenciales inválidas", "next": next_url},
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    # Guardamos datos mínimos en la sesión
    request.session["user_id"] = user.id
    request.session["rol"] = user.rol.value
    request.session["nombre"] = user.nombre

    if is_json:
        return schemas.LoginResponse(
            id=user.id,
            nombre=user.nombre,
            email=user.email,
            rol=user.rol,
        )

    # Redirección: si viene ?next= y es relativa al sitio, la respetamos
    if not is_json and next_url and next_url.startswith("/"):
        return RedirectResponse(url=next_url, status_code=status.HTTP_303_SEE_OTHER)

    return RedirectResponse(
        url=_home_for_role(user.rol.value),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.get("/logout")
def logout(request: Request):
    """Cierra la sesión y redirige al login."""
    request.session.clear()
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return response


# --- Endpoint común para obtener el usuario actual (API) --------------------
@app.get("/me", response_model=schemas.UsuarioOut)
def me(user: models.Usuario = Depends(require_login)):
    return user


# --- Dashboard router (elige vista según rol) -------------------------------
@app.get("/dashboard")
def dashboard(request: Request, user: models.Usuario = Depends(require_login)):
    return RedirectResponse(
        url=_home_for_role(user.rol.value), status_code=status.HTTP_303_SEE_OTHER
    )


# --- Dashboards por rol ------------------------------------------------------
@app.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request, user: models.Usuario = Depends(require_admin)):
        return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"user": user}
    )


@app.get("/coordinador", response_class=HTMLResponse)
def coordinador_home(request: Request, user: models.Usuario = Depends(require_coordinador)):
    return templates.TemplateResponse(
        "coordinador.html", {"request": request, "user": user}
    )


@app.get("/docente", response_class=HTMLResponse)
def docente_home(request: Request, user: models.Usuario = Depends(require_docente)):
    return templates.TemplateResponse(
        "docente.html", {"request": request, "user": user}
    )


# ===========================================================================
# GESTIÓN DE USUARIOS (solo administrador)
# ===========================================================================

@app.get("/admin/usuarios", response_model=list[schemas.UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db), _: models.Usuario = Depends(require_admin)):
    return db.query(models.Usuario).order_by(models.Usuario.nombre).all()


@app.post("/admin/usuarios", response_model=schemas.UsuarioOut, status_code=201)
def crear_usuario(
    datos: schemas.UsuarioCreate,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_admin),
):
    nuevo = models.Usuario(
        nombre=datos.nombre,
        email=str(datos.email).lower(),
        password_hash=hash_password(datos.password),
        rol=datos.rol,
        activo=True,
    )
    db.add(nuevo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email")
    db.refresh(nuevo)
    return nuevo


@app.patch("/admin/usuarios/{usuario_id}", response_model=schemas.UsuarioOut)
def actualizar_usuario(
    usuario_id: int,
    datos: schemas.UsuarioUpdate,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_admin),
):
    user = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    cambios = datos.model_dump(exclude_unset=True)
    if "password" in cambios and cambios["password"]:
        user.password_hash = hash_password(cambios.pop("password"))
    if "email" in cambios and cambios["email"]:
        cambios["email"] = str(cambios["email"]).lower()
    for campo, valor in cambios.items():
        setattr(user, campo, valor)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email ya registrado")
    db.refresh(user)
    return user


@app.delete("/admin/usuarios/{usuario_id}", status_code=204)
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current: models.Usuario = Depends(require_admin),
):
    # Evitar que el admin se elimine a sí mismo
    if current.id == usuario_id:
        raise HTTPException(status_code=400, detail="No puede eliminarse a sí mismo")
    user = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(user)
    db.commit()
    return None



