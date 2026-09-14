from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import engine, get_db, Base
import models

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# Crea las tablas en Postgres (si no existen) al levantar el servidor
Base.metadata.create_all(bind=engine)


@app.get("/")
def inicio(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )

@app.get("/pag2")
def segunda(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="pag2.html",
        context={}
    )

# --- conexión---
@app.get("/asignaturas")
def listar_asignaturas(db: Session = Depends(get_db)):
    return db.query(models.Asignatura).all()