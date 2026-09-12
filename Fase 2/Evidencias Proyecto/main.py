from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

app = FastAPI()

templates = Jinja2Templates(directory="templates")


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