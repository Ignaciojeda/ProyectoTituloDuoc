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

# Logo incrustado en el código: así el PDF lleva logo aunque falte la carpeta assets/ o Pillow.
LOGO_JPG_B64 = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8Q"
    "EBEQCgwSExIQEw8QEBD/2wBDAQMDAwQDBAgEBAgQCwkLEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQ"
    "EBAQEBAQEBD/wAARCABKAUADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUF"
    "BAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVW"
    "V1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi"
    "4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAEC"
    "AxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVm"
    "Z2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq"
    "8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD7+/ZO/wCTWPg3/wBk/wDD3/pugr1WvKv2Tv8Ak1j4N/8AZP8Aw9/6boK9VoAKKKKACiii"
    "gAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACmSyxQRPPPIkccal3dyAqqBk"
    "kk9AKfVGK9Oq2kc+lsyxTPJFJK6tFLDt3qWVHQ5YOoGGAGMnnABAMu21fVk115L2401dAvCF0+4Mqh5ZGSDy1Q7sMHLT44z8o7EZ"
    "6KsD/hDrRtP0bTJdTvpIdDmjnhDeVmUx/wCrD/JyFHA27TwCSTzSpruu2+rW+mal4UnKXQ+S7sbhZ4IyC24SlxGyYUKRhTnJA5GC"
    "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"
)

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
        # logo (incrustado en el código, no depende de archivos externos)
        try:
            import base64
            from reportlab.lib.utils import ImageReader
            img = ImageReader(io.BytesIO(base64.b64decode("".join(LOGO_JPG_B64))))
            iw, ih = img.getSize()
            w = 133
            h = w * ih / iw
            c.drawImage(img, MARGEN_IZQ, top(10) - h, width=w, height=h)
        except Exception as e:
            print(f"[pdf_sinoptico] No se pudo dibujar el logo: {e!r}")
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