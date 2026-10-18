"""
Exportación de un sinóptico a PDF con el formato del "Boletín de carga académica"
de Duoc UC: encabezado con logo, grilla Módulo x Lunes..Sábado y, para las
asignaturas que no se dictan todas las semanas, el detalle de clases con fechas.

No depende de la base de datos: recibe datos ya armados (ver construir_pdf_sinoptico).
"""
import io
import os
from datetime import timedelta
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether,
)

PAGE_W, PAGE_H = 609, 791
MARGEN_IZQ = 15
ANCHO_TABLA = 535
TOPE_TABLA = 188          # distancia desde arriba hasta donde parte la tabla
MARGEN_INFERIOR = 40

SEDE_NOMBRE = "PUERTO MONTT"
SEDE_NUMERO = "76"
SEDE_PREFIJO = "PM"

LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo_duocuc.png")

DIAS = [(1, "Lunes"), (2, "Martes"), (3, "Miércoles"), (4, "Jueves"), (5, "Viernes"), (6, "Sábado")]
DIAS_NOMBRE = {1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes", 6: "Sábado", 7: "Domingo"}
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def _fecha_larga(f):
    return f"{DIAS_NOMBRE[f.isoweekday()]} {f.day:02d} de {MESES[f.month - 1]} de {f.year}"


def _hhmm(t):
    return t.strftime("%H:%M")


def _codigo_seccion(it):
    cod = it["codigo"] or ""
    sec = it.get("seccion") or ""
    if sec and cod and sec.upper().startswith(cod.upper()):
        return sec
    return f"{cod}-{sec}" if sec else cod


def _texto_celda(it):
    sala = f"/{SEDE_PREFIJO}-{it['sala']}" if it.get("sala") else ""
    return f"{escape((it['nombre'] or '').upper())}<br/>{escape(_codigo_seccion(it))}{escape(sala)}"


def construir_pdf_sinoptico(*, sinoptico_id, carrera_nombre, carrera_codigo, jornada_nombre,
                            semestre_numero, anio, items, bloques_horas, lunes_inicio, fecha_emision):
    """
    items: lista de dicts con: asignatura_id, nombre, codigo, seccion, profesor, sala,
           dia_semana (1..6), hora_inicio, hora_fin (datetime.time), semanas (lista 1..17 o None=todas)
    bloques_horas: lista de (hora_inicio, hora_fin) que forman las filas de la grilla.
    lunes_inicio: date del lunes de la semana 1 del semestre.
    """
    buf = io.BytesIO()

    # ---------- estilos ----------
    est_celda = ParagraphStyle("celda", fontName="Courier", fontSize=6.2, leading=8.2, alignment=TA_CENTER)
    est_hora = ParagraphStyle("hora", fontName="Courier", fontSize=6.6, leading=11.5, alignment=TA_CENTER)
    est_cab = ParagraphStyle("cab", fontName="Courier-Bold", fontSize=9.5, leading=10.5, alignment=TA_LEFT)
    est_cab_c = ParagraphStyle("cabc", parent=est_cab, alignment=TA_CENTER)
    est_texto = ParagraphStyle("texto", fontName="Courier", fontSize=9, leading=11)
    est_det = ParagraphStyle("det", fontName="Courier", fontSize=9, leading=10.5)

    # ---------- encabezado de cada página ----------
    sem_txt = "1er" if semestre_numero == 1 else ("2do" if semestre_numero == 2 else f"{semestre_numero}°")

    def encabezado(c, doc):
        c.saveState()
        top = lambda y: PAGE_H - y
        # logo
        try:
            from reportlab.lib.utils import ImageReader
            img = ImageReader(LOGO_PATH)
            iw, ih = img.getSize()
            w = 133
            h = w * ih / iw
            c.drawImage(img, MARGEN_IZQ, top(10) - h, width=w, height=h, mask="auto")
        except Exception:
            pass
        c.setFont("Courier-Bold", 9.5)
        c.drawString(355, top(25), "Dirección de Docencia")
        c.drawString(355, top(38), f"Fecha emisión {fecha_emision.strftime('%d.%m.%Y')}")
        c.setFont("Courier-Bold", 9)
        c.drawString(12, top(64), f"SEDE: {SEDE_NOMBRE}")
        c.drawString(12, top(77), f"N°SEDE: {SEDE_NUMERO}")
        c.setFont("Helvetica-Bold", 11)
        c.drawString(59, top(101), f"BOLETIN DE CARGA ACADEMICA {sem_txt} Sem.")
        c.drawString(371, top(101), str(anio))
        c.setFont("Courier", 9)
        lineas = [
            ("Sinóptico:", f"N°{sinoptico_id}"),
            ("Carrera:", f"{carrera_nombre.upper()}   N°{carrera_codigo}"),
            ("Jornada:", jornada_nombre),
        ]
        y = 126
        for etiqueta, valor in lineas:
            c.drawString(59, top(y), etiqueta)
            c.drawString(145, top(y), valor)
            y += 12.5
        c.setFont("Courier-Bold", 9.5)
        c.drawString(170, top(175), "Horario de Clases")
        c.restoreState()

    frame = Frame(MARGEN_IZQ, MARGEN_INFERIOR, ANCHO_TABLA, PAGE_H - TOPE_TABLA - MARGEN_INFERIOR,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc = BaseDocTemplate(buf, pagesize=(PAGE_W, PAGE_H),
                          title=f"Horario sinóptico {sinoptico_id}", author="Sistema de Sinópticos",
                          pageTemplates=[PageTemplate(id="p", frames=[frame], onPage=encabezado)])

    # ---------- grilla ----------
    horas = sorted({(a, b) for a, b in bloques_horas} | {(i["hora_inicio"], i["hora_fin"]) for i in items})
    celdas = {}
    for it in items:
        celdas.setdefault((it["dia_semana"], it["hora_inicio"]), []).append(it)

    data = [[Paragraph("Módulo<br/>Horario", est_cab)] + [Paragraph(n, est_cab) for _, n in DIAS]]
    for ini, fin in horas:
        fila = [Paragraph(f"{_hhmm(ini)}<br/>A<br/>{_hhmm(fin)}", est_hora)]
        for dia, _ in DIAS:
            its = celdas.get((dia, ini), [])
            fila.append(Paragraph("<br/>".join(_texto_celda(i) for i in its), est_celda) if its else "")
        data.append(fila)

    col_w = [66, 78, 78, 78, 78, 78, 79]
    grilla = Table(data, colWidths=col_w, repeatRows=1)
    grilla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("VALIGN", (0, 0), (-1, 0), "TOP"),
        ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, 0), 1), ("BOTTOMPADDING", (0, 0), (-1, 0), 14),
    ]))
    story = [grilla]

    # ---------- detalle de clases por fecha (asignaturas que no son todas las semanas) ----------
    grupos = {}
    for it in items:
        if it.get("semanas"):
            grupos.setdefault((it["asignatura_id"], it.get("seccion") or ""), []).append(it)

    for (_, _), its in sorted(grupos.items(), key=lambda kv: kv[1][0]["nombre"]):
        base = its[0]
        clases = []
        for it in its:
            for w in it["semanas"]:
                fecha = lunes_inicio + timedelta(weeks=w - 1, days=it["dia_semana"] - 1)
                clases.append((fecha, it["hora_inicio"], it["hora_fin"], it.get("sala") or ""))
        clases.sort(key=lambda c: (c[0], c[1]))

        profes = []
        for it in its:
            if it.get("profesor") and it["profesor"] not in profes:
                profes.append(it["profesor"])

        titulo = f"{_codigo_seccion(base)}-{(base['nombre'] or '').upper()}"
        filas = [[Paragraph("Nro. Clase", est_cab_c), Paragraph("Fecha", est_cab_c),
                  Paragraph("Horario", est_cab_c), Paragraph("Sala", est_cab_c)]]
        for n, (f, a, b, sala) in enumerate(clases, 1):
            filas.append([
                Paragraph(f"Clase {n:02d}", est_det),
                Paragraph(_fecha_larga(f), est_det),
                Paragraph(f"{_hhmm(a)} a {_hhmm(b)}", est_det),
                Paragraph(escape(sala), est_det),
            ])
        t = Table(filas, colWidths=[80, 175, 140, 140], repeatRows=1)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        encabezado_bloque = [
            Spacer(1, 18),
            Paragraph(f'El Detalle de las clases de la asignatura "<b>{escape(titulo)}</b>" es:', est_texto),
            Spacer(1, 8),
            Paragraph(f"<b>Docente: {escape(', '.join(profes).upper()) if profes else 'SIN ASIGNAR'}</b>", est_texto),
            Spacer(1, 8),
        ]
        story.append(KeepTogether(encabezado_bloque + [t]) if len(clases) <= 16 else None)
        if len(clases) > 16:
            story.extend(encabezado_bloque + [t])
        story = [s for s in story if s is not None]

    doc.build(story)
    return buf.getvalue()