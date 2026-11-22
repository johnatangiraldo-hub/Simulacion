"""Construye el informe Word (APA 7.ª edición) de la Actividad didáctica 2-M3.

Lee los CSV de simulacion_bancaria.py, calcula los estadísticos y las figuras con
analisis_figuras.py y arma Grupo_15_EA3.docx.

Uso:
    python generar_informe_apa.py --resultados resultados --destino entrega
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from analisis_figuras import ETIQ, TIPOS, calcular

REPO = "https://github.com/johnatangiraldo-hub/Simulacion/tree/feature/ActividadM3/Actividad%203"
FUENTE = "Arial"


def f(v: float, d: int = 2) -> str:
    """Número con coma decimal."""
    return f"{v:.{d}f}".replace(".", ",")


def pct(v: float, d: int = 1) -> str:
    return f(v * 100, d) + " %"


def ic_txt(t, d: int = 2) -> str:
    return f"[{f(t[2], d)}; {f(t[3], d)}]"


# ------------------------------------------------------------------ utilidades docx
def _fuente(run, nombre=FUENTE, tam=None, negrita=None, cursiva=None):
    run.font.name = nombre
    rpr = run._r.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), nombre)
    if tam:
        run.font.size = Pt(tam)
    if negrita is not None:
        run.font.bold = negrita
    if cursiva is not None:
        run.font.italic = cursiva


def runs_con_formato(p, texto: str, tam=None, base_negrita=False, base_cursiva=False):
    """Interpreta **negrita** y *cursiva* dentro de un texto."""
    for trozo in re.split(r"(\*\*.+?\*\*|\*.+?\*)", texto):
        if not trozo:
            continue
        if trozo.startswith("**"):
            r = p.add_run(trozo[2:-2]); _fuente(r, tam=tam, negrita=True, cursiva=base_cursiva)
        elif trozo.startswith("*"):
            r = p.add_run(trozo[1:-1]); _fuente(r, tam=tam, negrita=base_negrita, cursiva=True)
        else:
            r = p.add_run(trozo); _fuente(r, tam=tam, negrita=base_negrita, cursiva=base_cursiva)


def hipervinculo(p, url: str, texto: str | None = None, tam=None):
    rid = p.part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                           is_external=True)
    h = OxmlElement("w:hyperlink"); h.set(qn("r:id"), rid)
    r = OxmlElement("w:r"); rpr = OxmlElement("w:rPr")
    rf = OxmlElement("w:rFonts")
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), FUENTE)
    rpr.append(rf)
    c = OxmlElement("w:color"); c.set(qn("w:val"), "0563C1"); rpr.append(c)
    u = OxmlElement("w:u"); u.set(qn("w:val"), "single"); rpr.append(u)
    if tam:
        sz = OxmlElement("w:sz"); sz.set(qn("w:val"), str(int(tam * 2))); rpr.append(sz)
    r.append(rpr)
    t = OxmlElement("w:t"); t.text = texto or url; t.set(qn("xml:space"), "preserve"); r.append(t)
    h.append(r); p._p.append(h)


class Informe:
    def __init__(self):
        self.d = Document()
        self.n_tabla = 0
        self.n_fig = 0
        s = self.d.sections[0]
        s.page_width, s.page_height = Cm(21.0), Cm(29.7)
        s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Cm(2.54)
        st = self.d.styles
        n = st["Normal"]
        n.font.name = FUENTE; n.font.size = Pt(11)
        n.element.rPr.rFonts.set(qn("w:eastAsia"), FUENTE)
        n.paragraph_format.space_after = Pt(0)
        n.paragraph_format.line_spacing = 2.0
        for nombre, neg, cur, ali in (("Heading 1", True, False, WD_ALIGN_PARAGRAPH.CENTER),
                                      ("Heading 2", True, False, WD_ALIGN_PARAGRAPH.LEFT),
                                      ("Heading 3", True, True, WD_ALIGN_PARAGRAPH.LEFT)):
            h = st[nombre]
            h.font.name = FUENTE; h.font.size = Pt(11); h.font.bold = neg; h.font.italic = cur
            h.font.color.rgb = RGBColor(0, 0, 0)
            rf = h.element.rPr.rFonts
            for a in list(rf.attrib):
                del rf.attrib[a]
            for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
                rf.set(qn(a), FUENTE)
            h.paragraph_format.alignment = ali
            h.paragraph_format.space_before = Pt(0); h.paragraph_format.space_after = Pt(0)
            h.paragraph_format.line_spacing = 2.0; h.paragraph_format.keep_with_next = True
        self._numerar_paginas(s)

    # ---- pie / encabezado
    def _numerar_paginas(self, sec):
        p = sec.header.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = p.add_run(); _fuente(r, tam=11)
        for tipo, txt in (("begin", None), (None, "PAGE"), ("end", None)):
            if tipo:
                e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), tipo)
            else:
                e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = txt
            r._r.append(e)

    # ---- bloques de texto
    def titulo(self, texto, nivel=1):
        p = self.d.add_heading(level=nivel)
        r = p.add_run(texto); _fuente(r, negrita=True, cursiva=(nivel == 3), tam=11)
        return p

    def p(self, texto, sangria=True, centrado=False, espaciado=2.0, tam=None):
        par = self.d.add_paragraph()
        pf = par.paragraph_format
        pf.line_spacing = espaciado
        if sangria:
            pf.first_line_indent = Cm(1.27)
        if centrado:
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        runs_con_formato(par, texto, tam=tam)
        return par

    def pagina_nueva(self):
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def ecuacion(self, texto):
        par = self.d.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.line_spacing = 1.5
        r = par.add_run(texto); _fuente(r, cursiva=True)

    def lista(self, items):
        for it in items:
            par = self.d.add_paragraph()
            par.paragraph_format.left_indent = Cm(1.27)
            par.paragraph_format.first_line_indent = Cm(-.63)
            runs_con_formato(par, "•  " + it)

    # ---- tablas APA
    def tabla(self, titulo, encabezados, filas, anchos=None, nota=None, alinear=None, tam=9,
              repetir_encabezado=False, mantener=True):
        self.n_tabla += 1
        for txt, cur, neg in ((f"Tabla {self.n_tabla}", False, True), (titulo, True, False)):
            par = self.d.add_paragraph()
            par.paragraph_format.line_spacing = 1.0
            par.paragraph_format.space_after = Pt(0 if neg else 4)
            par.paragraph_format.keep_with_next = True
            r = par.add_run(txt); _fuente(r, negrita=neg, cursiva=cur)
        t = self.d.add_table(rows=1, cols=len(encabezados))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        tblpr = t._tbl.tblPr
        mar = OxmlElement("w:tblCellMar")
        for lado, v in (("top", 30), ("left", 70), ("bottom", 30), ("right", 70)):
            e = OxmlElement(f"w:{lado}"); e.set(qn("w:w"), str(v)); e.set(qn("w:type"), "dxa"); mar.append(e)
        tblpr.append(mar)
        total = sum(anchos) if anchos else 16.0
        anchos = anchos or [total / len(encabezados)] * len(encabezados)
        alinear = alinear or ["l"] + ["c"] * (len(encabezados) - 1)

        def llenar(celda, txt, i, neg=False):
            celda.width = Cm(anchos[i])
            par = celda.paragraphs[0]
            par.paragraph_format.line_spacing = 1.0
            par.alignment = {"l": WD_ALIGN_PARAGRAPH.LEFT, "c": WD_ALIGN_PARAGRAPH.CENTER,
                             "r": WD_ALIGN_PARAGRAPH.RIGHT}[alinear[i]]
            runs_con_formato(par, str(txt), tam=tam, base_negrita=neg)

        for i, e in enumerate(encabezados):
            llenar(t.rows[0].cells[i], e, i)
        for fila in filas:
            cs = t.add_row().cells
            for i, v in enumerate(fila):
                llenar(cs[i], v, i)

        def borde(celda, lado):
            tcpr = celda._tc.get_or_add_tcPr()
            b = tcpr.find(qn("w:tcBorders"))
            if b is None:
                b = OxmlElement("w:tcBorders"); tcpr.append(b)
            e = OxmlElement(f"w:{lado}")
            e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "6"); e.set(qn("w:color"), "000000")
            b.append(e)
        for c in t.rows[0].cells:
            borde(c, "top"); borde(c, "bottom")
        for c in t.rows[-1].cells:
            borde(c, "bottom")
        if repetir_encabezado:
            trpr = t.rows[0]._tr.get_or_add_trPr()
            e = OxmlElement("w:tblHeader"); e.set(qn("w:val"), "true"); trpr.append(e)
        for fila in t.rows:
            trpr = fila._tr.get_or_add_trPr()
            e = OxmlElement("w:cantSplit"); e.set(qn("w:val"), "true"); trpr.append(e)
        if mantener:
            for fila in t.rows[:-1]:
                for c in fila.cells:
                    for par in c.paragraphs:
                        par.paragraph_format.keep_with_next = True
        if nota:
            par = self.d.add_paragraph()
            par.paragraph_format.line_spacing = 1.0
            par.paragraph_format.space_before = Pt(3)
            runs_con_formato(par, "*Nota.* " + nota, tam=9)
        sp = self.d.add_paragraph(); sp.paragraph_format.line_spacing = 1.0
        sp.paragraph_format.space_after = Pt(4)
        return t

    # ---- figuras APA
    def figura(self, titulo, ruta: Path, ancho_cm=14.0, nota=None):
        self.n_fig += 1
        for txt, cur, neg in ((f"Figura {self.n_fig}", False, True), (titulo, True, False)):
            par = self.d.add_paragraph()
            par.paragraph_format.line_spacing = 1.0
            par.paragraph_format.space_after = Pt(0 if neg else 4)
            par.paragraph_format.keep_with_next = True
            r = par.add_run(txt); _fuente(r, negrita=neg, cursiva=cur)
        par = self.d.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.line_spacing = 1.0
        par.paragraph_format.keep_with_next = bool(nota)
        par.add_run().add_picture(str(ruta), width=Cm(ancho_cm))
        if nota:
            n = self.d.add_paragraph()
            n.paragraph_format.line_spacing = 1.0
            runs_con_formato(n, "*Nota.* " + nota, tam=9)
        sp = self.d.add_paragraph(); sp.paragraph_format.line_spacing = 1.0
        sp.paragraph_format.space_after = Pt(4)

    def codigo(self, texto: str):
        for linea in texto.splitlines():
            par = self.d.add_paragraph()
            pf = par.paragraph_format
            pf.line_spacing = 1.0; pf.space_after = Pt(0)
            r = par.add_run(linea if linea else " ")
            _fuente(r, nombre="Courier New", tam=7)


# ------------------------------------------------------------------ contenido
def construir(resultados: Path, destino: Path, nombre="Grupo_15_EA3"):
    figuras = destino / "figuras"
    R = calcular(resultados, figuras)
    E = {e["escenario"]: e for e in R["escenarios"]}
    A, B, C, D, Ee, F, G = (E[k] for k in ETIQ)
    dem = R["demanda_total"]
    dt = {t["tipo"]: t for t in R["demanda_tipo"]}
    cajasA = [c for c in R["cajas"] if c["escenario"] == "A_3_mixtas"]
    menor = min(cajasA, key=lambda c: c["servicio"])
    mayor = max(cajasA, key=lambda c: c["servicio"])
    dif = R["diferencias"]
    val = R["validacion"]
    carga = R["carga"]
    rho = {(r["escenario"], r["grupo"]): r for r in R["rho"]}
    pares = R["replicas_pares"]
    rep = {r["escenario"]: r for r in R["replicas"]}
    pend = R["pendientes_tipo"]

    I = Informe()
    # ---------- Portada
    for txt, neg in (("Actividad didáctica 2-M3. Solución de un problema bancario mediante simulación de colas", True),
                     ("Luis Miguel Vargas Guevara, Johnatan Giraldo Cardona, Nicolas Mateo Chavez Garcia", False),
                     ("Facultad de Ingeniería y Ciencias Agropecuarias, Institución Universitaria Digital de Antioquia", False),
                     ("Simulación - PREICA2602B020045", False), ("Julian Andres Loaiza", False),
                     ("Grupo de trabajo 15", False), ("Noviembre 22, de 2026", False)):
        par = I.d.add_paragraph(); par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.line_spacing = 2.0
        r = par.add_run(txt); _fuente(r, negrita=neg)
    I.pagina_nueva()

    # ---------- Introducción
    I.titulo("Introducción")
    I.p("La teoría de colas estudia sistemas en los que usuarios llegan de forma aleatoria, esperan y reciben un servicio de duración "
        "también aleatoria. Cuando las fórmulas analíticas no se pueden aplicar con exactitud, la simulación de eventos discretos permite "
        "reproducir el comportamiento del sistema y estimar sus indicadores mediante réplicas independientes (Law, 2015).")
    I.p("El Banco de Colombia no cuenta con cajeros electrónicos y atiende retiros y pagos en tres cajas. El banco quiere saber si debe "
        "destinar una caja exclusiva a retiros y dos a pagos, o lo contrario, y si necesita habilitar una caja adicional para que los usuarios "
        "realicen sus operaciones sin demora. Según el enunciado, el 70 % de los usuarios retira dinero y el 30 % restante hace consignaciones "
        "o pagos; cada operación admite cuatro tipos de usuario (rápido, normal, lento y muy lento) con tiempos de llegada y de servicio "
        "exponenciales, y el banco opera ocho horas al día.")
    I.p("El objetivo de esta actividad es construir un modelo de simulación en Python, ejecutarlo en al menos diez réplicas y responder cinco "
        "preguntas: (1) cuál cajero tiene el menor y el mayor tiempo promedio de atención; (2) cuál es el promedio de usuarios de cada tipo; "
        "(3) cuántos usuarios de cada tipo llegan en cada réplica y cuál es la réplica con menos; (4) si es necesario crear una nueva caja; y "
        "(5) cuántas cajas deben ser exclusivas para pagos y cuántas para retiros.")
    I.p("El informe se organiza así: la metodología describe el modelo, los supuestos, las configuraciones comparadas y la validación; los "
        "resultados responden los cinco puntos con tablas y gráficas; y las conclusiones resumen la recomendación para el banco y las "
        "limitaciones del estudio. El código, los datos y las figuras están disponibles en el repositorio del grupo ("
        f"{REPO}).")

    # ---------- Metodología
    I.titulo("Metodología")
    I.titulo("Datos y supuestos del sistema", 2)
    I.p("La Tabla 1 resume los datos del enunciado. Las probabilidades de la Tabla 2 del enunciado se interpretan como condicionales "
        "dentro de cada operación (suman 1 en retiros y en pagos), de modo que la probabilidad global de un tipo es el producto de la "
        "probabilidad de la operación (0,70 o 0,30) y la condicional.")
    filas = []
    prob = {"Retiro": (0.23, 0.40, 0.17, 0.20), "Pago": (0.10, 0.20, 0.30, 0.40)}
    serv = {"Retiro": (1, 2, 3, 4), "Pago": (3, 3, 5, 7)}
    lleg = {"Retiro": (1, 2, 3, 3), "Pago": (1, 2, 3, 4)}
    for ac, pa in (("Retiro", .7), ("Pago", .3)):
        for i, t in enumerate(TIPOS):
            filas.append([ac if i == 0 else "", t, f(prob[ac][i]), f(prob[ac][i] * pa, 3), serv[ac][i], lleg[ac][i]])
    I.tabla("Parámetros de entrada de la simulación", ["Operación", "Tipo de usuario", "Prob. condicional",
            "Prob. global", "Servicio (media, min)", "Entrellegada (media, min)"], filas,
            anchos=[2.4, 3.0, 2.6, 2.4, 2.8, 3.2], alinear=["l", "l", "c", "c", "c", "c"],
            nota="Servicio y entrellegada se modelan como exponenciales parametrizadas por su media en minutos.")
    I.p("Se asumen los siguientes supuestos: (a) las cajas son servidores independientes, cada una con su propia cola de orden de "
        "llegada (FIFO); (b) la velocidad de atención es la misma en todas las cajas para una clase de usuario y el desplazamiento es "
        "despreciable, como indica el enunciado; (c) el día comienza con el banco vacío y se reciben usuarios entre el minuto 0 y el 480, "
        "y quienes ya llegaron al cierre terminan su atención después de las 8 horas; (d) todos los días son iguales en distribución, por "
        "lo que se simula un día y se repite en réplicas independientes; y (e) un usuario no cambia de caja una vez ingresa a una cola.")
    I.titulo("Modelo de simulación", 2)
    I.p("El modelo es de eventos discretos y se implementó en Python con NumPy. Para cada usuario se sortea primero su operación "
        "(retiro con probabilidad 0,70) y su tipo según la probabilidad condicional; luego se genera el intervalo hasta su llegada con una "
        "exponencial cuya media es la de su fila de la Tabla 1 (misma lógica del código de ejemplo del laboratorio) y su tiempo de servicio "
        "con la exponencial de esa fila. Con estos valores la media ponderada entre llegadas es "
        f"{f(val['interllegada_teo'], 3)} minutos y la del servicio es {f(val['servicio_teo'], 3)} minutos.")
    I.p("Al llegar, el usuario se asigna a la caja compatible con menos trabajos pendientes; si hay empate se prefiere la caja cuya "
        "agenda termina antes y luego un desempate rotativo. El servicio comienza cuando la caja queda libre. Se registran, por usuario, "
        "la llegada, el inicio, el fin, la caja, la espera (inicio − llegada), el servicio (fin − inicio) y el tiempo en el sistema.")
    I.p("Dentro de una réplica todas las configuraciones reciben exactamente los mismos usuarios y servicios (números aleatorios "
        "comunes), de modo que las diferencias entre configuraciones se deben a la organización de las cajas y no a la suerte de cada día. "
        "Las réplicas usan semillas distintas derivadas de una semilla base (20261122), lo que permite reproducir los resultados.")
    I.p("Respecto de la precisión del modelo M/M/1: cada caja es un servidor con cola propia, pero las tablas del enunciado mezclan ocho "
        "medias de servicio y ocho de llegada, de modo que la caja agregada no es exactamente M/M/1 y las fórmulas estacionarias no son "
        "exactas (Gross et al., 2008). Por eso el desempeño se estima mediante la simulación de cada usuario y las fórmulas se usan solo "
        "como verificación de órdenes de magnitud.")
    I.titulo("Configuraciones evaluadas", 2)
    I.p("Además de las tres cajas mixtas (situación actual) y las dos alternativas del enunciado, se evaluaron cuatro configuraciones "
        "con una caja adicional para responder la pregunta sobre la necesidad de una nueva caja (Tabla 2).")
    I.tabla("Configuraciones de cajas comparadas", ["Código", "Cajas", "Distribución", "Propósito"], [
        ["3 mixtas", "3", "3 mixtas", "Situación actual"],
        ["1R + 2P", "3", "1 retiros, 2 pagos", "Alternativa exclusiva 1"],
        ["2R + 1P", "3", "2 retiros, 1 pagos", "Alternativa exclusiva 2"],
        ["4 mixtas", "4", "4 mixtas", "Caja adicional flexible"],
        ["2R + 2P", "4", "2 retiros, 2 pagos", "Caja adicional exclusiva equilibrada"],
        ["1R + 3P", "4", "1 retiros, 3 pagos", "Sensibilidad con cuatro cajas"],
        ["3R + 1P", "4", "3 retiros, 1 pagos", "Sensibilidad con cuatro cajas"]],
        anchos=[2.6, 1.5, 4.8, 6.0], alinear=["l", "c", "l", "l"])
    I.titulo("Métricas y análisis estadístico", 2)
    I.p("Los indicadores por réplica son la espera media, el percentil 95 de la espera, los usuarios que no terminan al minuto 480, "
        "el servicio medio, el tiempo en el sistema y la utilización de cada caja (tiempo de servicio dentro del horario dividido por 480). "
        "Para cada indicador se calculó el promedio de las réplicas, la desviación estándar y el intervalo de confianza (IC) del 95 % con la "
        "distribución *t* de Student:")
    I.ecuacion("x̄ ± t(0,975; n−1) · s / √n")
    I.p("Las comparaciones entre configuraciones usan diferencias emparejadas por réplica, porque ambas configuraciones se simulan con la "
        "misma demanda. Para verificar la estabilidad se calcula el factor de utilización ρ = λ·E[S]/c, que debe ser menor que 1, y para "
        "validar la simulación se contrasta la ley de Little, Lq = λ·Wq (Little, 1961).")
    I.titulo("Validación del modelo", 2)
    I.p("Antes de interpretar resultados se comprobó que el generador reproduce los parámetros teóricos y que el modelo cumple la ley de "
        "Little (Tabla 3).")
    I.tabla("Comparación entre valores teóricos y simulados (30 réplicas)", ["Indicador", "Teórico", "Simulado"], [
        ["Entrellegada media (min)", f(val["interllegada_teo"], 3), f(val["interllegada_obs"], 3)],
        ["Servicio medio (min)", f(val["servicio_teo"], 3), f(val["servicio_obs"], 3)],
        ["Proporción de retiros", pct(val["retiros_teo"]), pct(val["retiros_obs"])],
        ["Usuarios por día", f(val["llegadas_dia_teo"]), f(val["llegadas_dia_obs"])],
        ["Utilización de las 3 cajas mixtas (ρ)", pct(rho[("A_3_mixtas", "Mixto")]["teo"]), pct(rho[("A_3_mixtas", "Mixto")]["obs"])]],
        anchos=[7.0, 3.5, 3.5],
        nota="El valor teórico de ρ es λ·E[S]/c con λ = 1/2,398 usuarios por minuto y E[S] = 3,198 minutos. La utilización simulada cuenta solo el servicio dentro del horario.")
    I.p("Las diferencias son menores al 2 % en las medias y la diferencia en los usuarios por día (202,73 frente a 200,17) está dentro de "
        f"un error estándar ({f(dem['de'] / 30 ** .5)} usuarios). Las utilizaciones teóricas y simuladas de las diez combinaciones de cajas "
        "coinciden dentro de unos pocos puntos porcentuales (Figura 6). Además, la ley de Little se cumple con diferencias menores de 3,5 % "
        "en las siete configuraciones (Tabla 10), lo que respalda el cálculo de las esperas.")
    I.titulo("Implementación y reproducibilidad", 2)
    I.p("El código se organizó en tres módulos: simulacion_bancaria.py (modelo y réplicas), analisis_figuras.py (estadísticos y gráficas) "
        "y generar_informe_apa.py (este documento). Se incluyen cuatro pruebas unitarias que verifican la reproducibilidad con la misma "
        "semilla, que todas las configuraciones atienden la misma demanda, que no hay solapamiento de servicios en una caja y el manejo "
        "del cierre. El Anexo C contiene el código del modelo y el repositorio contiene el resto, con instrucciones de ejecución en el README.")

    # ---------- Resultados
    I.titulo("Resultados")
    I.titulo("Número de réplicas", 2)
    I.p("El enunciado exige al menos 10 corridas. Se ejecutaron 30 réplicas por configuración. Para justificar esa cantidad se examinó "
        "cuánto se estabiliza la media y cuánto se estrecha el IC al aumentar las réplicas (Figura 1). Con las primeras 10 réplicas como "
        "piloto se estimó además el número de réplicas necesario para que el semiancho del IC 95 % de la espera media no supere 0,5 minutos "
        "(Tabla 4), siguiendo el criterio de estimar *n* a partir de una muestra piloto (Law, 2015; Taco-Mena et al., 2019).")
    I.figura("Convergencia de la espera media y del semiancho del IC 95 % según el número de réplicas",
             figuras / "fig1_convergencia_replicas.png", 15.5,
             "Izquierda: promedio acumulado de la espera media diaria con tres cajas mixtas y su IC 95 %. Derecha: semiancho del IC para tres configuraciones. La línea punteada marca el mínimo de 10 réplicas.")
    I.tabla("Réplicas necesarias para un IC 95 % de ±0,5 minutos en la espera media", ["Configuración",
            "Desv. est. (piloto de 10)", "Semiancho con 10", "Semiancho con 30", "Réplicas necesarias"],
            [[ETIQ[e], f(rep[e]["s10"]), f(rep[e]["h10"]), f(rep[e]["h30"]), rep[e]["n_050"]] for e in ETIQ],
            anchos=[3.0, 3.4, 3.2, 3.2, 3.4],
            nota="La desviación estándar corresponde a la espera media diaria (minutos). Las réplicas necesarias se calculan con la desviación estándar del piloto de 10 réplicas.")
    I.p("Las configuraciones con cajas mixtas o equilibradas son muy estables: con 5 réplicas o menos se alcanza una precisión de ±0,5 "
        "minutos, y con 30 réplicas el semiancho de la configuración actual es de "
        f"{f(rep['A_3_mixtas']['h30'])} minutos. Las configuraciones con una sola caja exclusiva son más variables (hasta {rep['B_1R_2P']['n_050']} "
        f"réplicas para la misma precisión), pero esa variabilidad no afecta la decisión: con solo 10 réplicas el IC de las diferencias "
        f"emparejadas ya excluía el cero en las tres comparaciones clave (1R + 2P − 2R + 1P: {ic_txt(pares['B-C']['ic10'])}; "
        f"2R + 1P − 3 mixtas: {ic_txt(pares['C-A']['ic10'])}; 3 mixtas − 4 mixtas: {ic_txt(pares['A-D']['ic10'])}), y con 30 réplicas se "
        f"estrechan a {ic_txt(pares['B-C']['ic30'])}, {ic_txt(pares['C-A']['ic30'])} y {ic_txt(pares['A-D']['ic30'])}. En consecuencia, "
        "10 réplicas bastan para ordenar las configuraciones y 30 dan una precisión adecuada; no se requieren más para las conclusiones.")

    # --- Punto 1
    I.titulo("Punto 1. Cajero con menor y mayor tiempo promedio de atención", 2)
    I.p("Se tomó como tiempo de atención el tiempo de servicio medio por usuario de cada caja, sin separar tipos de usuario, como "
        "indica el enunciado. La Tabla 5 y la Figura 2 muestran los resultados de la configuración actual de tres cajas mixtas.")
    I.tabla("Desempeño de cada caja en la configuración de tres cajas mixtas", ["Caja", "Usuarios por día",
            "Servicio medio (min)", "IC 95 % del servicio", "Espera en cola (min)", "Tiempo en el sistema (min)", "Utilización"],
            [[c["caja"], f(c["clientes"]), f(c["servicio"]), f"[{f(c['servicio_lo'])}; {f(c['servicio_hi'])}]", f(c["espera"]),
              f(c["sistema"]), pct(c["util"])] for c in cajasA],
            anchos=[1.5, 2.2, 2.4, 3.0, 2.4, 2.6, 2.1], tam=8.5,
            nota="Promedios de 30 réplicas.")
    I.figura("Servicio medio y espera media por caja con tres cajas mixtas", figuras / "fig2_cajeros.png", 13.0,
             "Las barras de error del panel izquierdo son el IC 95 % de 30 réplicas.")
    I.p(f"La caja con menor tiempo promedio de atención es **{menor['caja']}** ({f(menor['servicio'])} min) y la de mayor tiempo es "
        f"**{mayor['caja']}** ({f(mayor['servicio'])} min). Sin embargo, la diferencia no es estadísticamente significativa: la diferencia "
        f"emparejada {mayor['caja']} − {menor['caja']} es {f(R['dif_cajas']['C1-C3'][0])} minutos con IC 95 % {ic_txt(R['dif_cajas']['C1-C3'])}, que incluye el "
        f"cero, y un ANOVA de un factor sobre el servicio medio diario de las tres cajas no rechaza la igualdad (*p* = {f(R['anova_cajas'], 3)}). "
        "Esto es coherente con el modelo, porque las tres cajas tienen los mismos parámetros de servicio y su diferencia depende solo de la "
        "mezcla de usuarios que recibió cada una en el azar. El mismo orden aparece en el tiempo total en el sistema (C3 con "
        f"{f(cajasA[2]['sistema'])} min y C1 con {f(cajasA[0]['sistema'])} min). En las configuraciones con cajas exclusivas sí hay diferencias "
        "reales, porque cambia la clase de usuario atendida: las cajas de retiro tienen un servicio medio cercano a 2,4 minutos y las de pago "
        "cercano a 5,2 minutos (Anexo B).")

    # --- Punto 2
    I.titulo("Punto 2. Promedio de usuarios de cada tipo en la totalidad de cajeros", 2)
    I.p(f"En promedio llegan {f(dem['media'])} usuarios por día (DE = {f(dem['de'])}), de los cuales {f(dem['retiros'])} hacen retiros y "
        f"{f(dem['pagos'])} hacen pagos. La Tabla 6 y la Figura 3 muestran el promedio diario de cada tipo en el conjunto de las cajas; "
        "como todas las configuraciones atienden la misma demanda, estos promedios no dependen de cómo se distribuyan las cajas.")
    I.tabla("Promedio diario de usuarios por tipo (30 réplicas)", ["Tipo de usuario", "Retiros", "Pagos", "Total (promedio)",
            "Desviación estándar", "Mínimo (réplica)", "Máximo"],
            [[t, f(dt[t]["retiro"]), f(dt[t]["pago"]), f(dt[t]["media"]), f(dt[t]["de"]),
              f"{dt[t]['minimo']} (R{dt[t]['replica_min']})", dt[t]["maximo"]] for t in TIPOS] +
            [["Total", f(dem["retiros"]), f(dem["pagos"]), f(dem["media"]), f(dem["de"]),
              f"{dem['minimo']} (R{dem['replica_min']})", ""]],
            anchos=[2.9, 1.9, 1.9, 2.5, 2.7, 2.7, 1.6], tam=8.5)
    I.figura("Promedio diario de usuarios por tipo y operación", figuras / "fig3_usuarios_por_tipo.png", 12.5,
             "Las barras de error son la desviación estándar diaria del total de cada tipo.")
    I.p(f"El tipo más frecuente es el normal ({f(dt['Normal']['media'])} usuarios por día), seguido por el muy lento "
        f"({f(dt['Muy lento']['media'])}), el lento ({f(dt['Lento']['media'])}) y el rápido ({f(dt['Rápido']['media'])}). Los retiros se "
        "concentran en usuarios rápidos y normales, mientras que los pagos se concentran en usuarios lentos y muy lentos.")

    # --- Punto 3
    I.titulo("Punto 3. Total de usuarios de cada tipo por réplica y réplica con menos usuarios", 2)
    I.titulo("Lectura principal: réplicas de demanda", 3)
    I.p("El Anexo A detalla el total de usuarios de cada tipo, de retiros y de pagos en las 30 réplicas. La Figura 4 resume esa "
        "información y resalta, en cada tipo, la réplica con menos usuarios.")
    I.figura("Usuarios de cada tipo en cada una de las 30 réplicas", figuras / "fig4_usuarios_por_replica.png", 11.0,
             "Los recuadros naranja marcan el mínimo de cada tipo.")
    I.p(f"La réplica con menos usuarios es la **{dem['replica_min']}**, con {dem['minimo']} usuarios en total ({dem['ret_min']} retiros y "
        f"{dem['pag_min']} pagos). Por tipo, el mínimo ocurre en la réplica {dt['Rápido']['replica_min']} para los rápidos "
        f"({dt['Rápido']['minimo']}), en la {dt['Normal']['replica_min']} para los normales ({dt['Normal']['minimo']}), en la "
        f"{dt['Lento']['replica_min']} para los lentos ({dt['Lento']['minimo']}) y en la {dt['Muy lento']['replica_min']} para los muy "
        f"lentos ({dt['Muy lento']['minimo']}). La Tabla 7 detalla el mínimo de cada combinación de operación y tipo.")
    I.tabla("Mínimo de usuarios por operación y tipo", ["Operación", "Tipo de usuario", "Promedio diario", "Mínimo", "Réplica"],
            [[s["accion"] if i % 4 == 0 else "", s["tipo"], f(s["media"]), s["minimo"], s["replica_min"]]
             for i, s in enumerate(R["demanda_subtipo"])], anchos=[2.8, 3.2, 3.2, 2.4, 2.4], alinear=["l", "l", "c", "c", "c"])
    I.titulo("Lectura alternativa: modelo con menos usuarios por tipo sin atender al cierre", 3)
    I.p("La lectura anterior compara réplicas, no modelos, porque en cada réplica todas las configuraciones reciben los mismos "
        "usuarios; por eso ninguna configuración puede tener menos llegadas. Si el punto se interpreta como \"el modelo (configuración) "
        "con menor cantidad de usuarios de cada tipo\" en el sistema, la comparación razonable es la cantidad de usuarios de cada tipo que "
        "siguen en cola o en atención al minuto 480 (Tabla 8).")
    I.tabla("Usuarios por día que no han terminado al cierre (minuto 480), por tipo y configuración",
            ["Configuración", "Rápido", "Normal", "Lento", "Muy lento", "Total"],
            [[ETIQ[e]] + [f(pend[e][t]) for t in TIPOS] + [f(sum(pend[e].values()))] for e in ETIQ],
            anchos=[3.2, 2.4, 2.4, 2.4, 2.6, 2.4],
            nota="Promedio de 30 réplicas. Un usuario sin atender es quien llegó antes del cierre y todavía no ha terminado su servicio.")
    I.p("El modelo con menor cantidad de usuarios sin atender al cierre es el de **cuatro cajas mixtas** en los cuatro tipos "
        f"(rápidos {f(pend['D_4_mixtas']['Rápido'])}; normales {f(pend['D_4_mixtas']['Normal'])}; lentos {f(pend['D_4_mixtas']['Lento'])}, "
        "empatado con 2R + 2P; y muy lentos "
        f"{f(pend['D_4_mixtas']['Muy lento'])}), seguido muy de cerca por las cajas equilibradas. Las configuraciones con una sola caja de "
        f"retiros (1R + 2P y 1R + 3P) dejan cerca de {f(B['pend'], 1)} usuarios sin atender, el peor resultado. Aun así, las diferencias entre "
        "3 mixtas, 4 mixtas y 2R + 2P son de décimas de usuario, de modo que a la hora del cierre las configuraciones balanceadas son "
        "equivalentes en la práctica.")

    # --- Punto 4
    I.titulo("Punto 4. ¿Es necesario crear una nueva caja?", 2)
    I.p("La decisión se tomó con los tiempos de espera en todos los criterios del modelo: espera media global y por operación, "
        "percentil 95, proporción de usuarios que esperan más de cinco minutos, usuarios sin atender al cierre y utilización "
        "(Tabla 9, Figuras 5 a 7). Como el enunciado no fija una meta numérica, el grupo adopta como criterio de trabajo que la espera "
        "media de cada operación sea menor que 5 minutos y que el percentil 95 de la espera sea menor que 10 minutos; es un supuesto del "
        "equipo, no una exigencia del enunciado, y se analiza su sensibilidad más adelante.")
    I.tabla("Desempeño de las configuraciones (promedio de 30 réplicas)", ["Configuración", "Espera media (min)", "IC 95 %",
            "Retiros", "Pagos", "P95", "% con espera > 5 min", "Sin atender al cierre", "Utilización"],
            [[ETIQ[e["escenario"]], f(e["espera"]), ic_txt((0, 0, e["lo"], e["hi"])), f(e["retiro"]), f(e["pago"]), f(e["p95"]),
              pct(e["mayor5"]), f(e["pend"]), pct(e["util"], 0)] for e in R["escenarios"]],
            anchos=[2.1, 1.7, 2.3, 1.5, 1.5, 1.4, 2.0, 1.9, 1.7], tam=8,
            nota="Las esperas, P95 y diferencias están en minutos. La espera media es el promedio de los usuarios que llegan antes del cierre, incluidos quienes terminan después.")
    I.figura("Distribución de la espera media diaria por configuración (30 réplicas)", figuras / "fig5_distribucion_espera.png", 13.5,
             "Cada caja resume las 30 réplicas: mediana, cuartiles y valores extremos.")
    I.p(f"**Evidencia de que no se requiere una caja adicional.** Con tres cajas mixtas la espera media es {f(A['espera'])} minutos "
        f"(IC 95 % {ic_txt((0, 0, A['lo'], A['hi']))}): {f(A['retiro'])} para retiros y {f(A['pago'])} para pagos. El {pct(A['sin_espera'])} de los usuarios "
        f"no espera nada, solo el {pct(A['mayor5'])} espera más de 5 minutos y el percentil 95 es {f(A['p95'])} minutos, menor que el límite de 10. "
        f"La utilización de las cajas es {pct(A['util'])}, muy por debajo de 100 %; es decir, el sistema es estable y tiene capacidad ociosa.")
    I.figura("Utilización teórica y observada por tipo de caja y configuración", figuras / "fig6_utilizacion.png", 14.5,
             "La utilización teórica es λ·E[S]/c con la carga ofrecida por operación (0,68 erlangs en retiros y 0,65 en pagos); la observada es el promedio de 30 réplicas.")
    I.p(f"El tráfico ofrecido total es λ·E[S] = {f(carga['total'], 3)} erlangs ({f(carga['erlangs']['Retiro'], 3)} de retiros y "
        f"{f(carga['erlangs']['Pago'], 3)} de pagos), repartido entre tres cajas. Como ρ = {f(rho[('A_3_mixtas', 'Mixto')]['teo'], 3)} < 1, la cola no crece sin límite, y "
        "la Figura 6 confirma que la simulación reproduce ese valor. Las dos configuraciones con una sola caja para una operación tienen ρ "
        f"cercanos a 0,65 y 0,68, que explican sus esperas de cerca de 7 y 8 minutos.")
    I.figura("Porcentaje de usuarios que esperan más de t minutos", figuras / "fig7_cola_espera.png", 12.5,
             "Distribución empírica complementaria calculada con todos los usuarios de las 30 réplicas.")
    I.p(f"Agregar una cuarta caja mixta reduce la espera media de {f(A['espera'])} a {f(D['espera'])} minutos, una mejora de "
        f"{f(dif['A-D'][0])} minutos (IC 95 % {ic_txt(dif['A-D'])}), y baja la utilización a {pct(D['util'])}. Es una mejora real, pero de "
        f"unos {f(dif['A-D'][0] * 60, 0)} segundos por usuario sobre un nivel que ya cumple ambos criterios; sin información de costos no "
        "hay evidencia para afirmar que la inversión sea necesaria. **Conclusión del punto 4: no es necesario crear una nueva caja si las "
        "tres actuales atienden retiros y pagos de forma indistinta.**")
    I.p(f"*Sensibilidad del criterio.* La conclusión no depende de los umbrales elegidos: la espera media de 3 mixtas ({f(A['espera'])} min) "
        "incluso cumpliría una meta de 1 minuto. El resultado solo cambia si se exige que las cajas sean exclusivas: con tres cajas exclusivas "
        f"alguna operación supera los 5 minutos (retiros {f(B['retiro'])} en 1R + 2P; pagos {f(C['pago'])} en 2R + 1P). En ese caso la "
        f"cuarta caja sí se justifica, y la configuración equilibrada 2R + 2P deja esperas de {f(Ee['retiro'])} (retiros) y {f(Ee['pago'])} (pagos) "
        f"minutos, con {pct(Ee['mayor5'])} de usuarios esperando más de 5 minutos. Además, 2R + 2P no es distinguible de 3 mixtas en espera global "
        f"(diferencia {f(dif['A-E'][0])} min, IC 95 % {ic_txt(dif['A-E'])}), por lo que la cuarta caja exclusiva solo compensa la pérdida de "
        "eficiencia de separar las operaciones. Finalmente, el enunciado menciona la falta de cajeros electrónicos; como no se conocen su "
        "velocidad, las operaciones que admiten ni su costo, no es posible evaluarlos con estos datos.")
    I.tabla("Validación con la ley de Little (Lq = λ·Wq)", ["Configuración", "Lq observada", "λ·Wq", "Diferencia"],
            [[ETIQ[l["escenario"]], f(l["Lq"], 3), f(l["little"], 3), pct((l["little"] - l["Lq"]) / l["Lq"])] for l in R["little"]],
            anchos=[3.5, 3.2, 3.2, 3.2],
            nota="Lq es el número medio de usuarios en cola durante la jornada; λ es el número de llegadas por minuto y Wq la espera media. La diferencia se debe a que Wq incluye esperas posteriores al cierre.")

    # --- Punto 5
    I.titulo("Punto 5. Cajas exclusivas para pagos y para retiros", 2)
    I.p("Si el banco decide dedicar sus tres cajas a operaciones específicas, hay dos opciones: una caja para retiros y dos para pagos, "
        f"o dos para retiros y una para pagos. La opción **2R + 1P** tiene una espera media global de {f(C['espera'])} minutos frente a "
        f"{f(B['espera'])} de 1R + 2P. La diferencia emparejada es de {f(dif['B-C'][0])} minutos (IC 95 % {ic_txt(dif['B-C'])}), que "
        f"excluye el cero. Además, solo el {pct(C['mayor5'])} de los usuarios espera más de 5 minutos con 2R + 1P, frente al "
        f"{pct(B['mayor5'])} con 1R + 2P, y quedan menos usuarios sin atender al cierre ({f(C['pend'])} frente a {f(B['pend'])}).")
    I.figura("Espera media de retiros y de pagos en cada configuración", figuras / "fig8_compromiso_operaciones.png", 12.0,
             "Azul: tres cajas mixtas; naranja: tres cajas exclusivas; gris: configuraciones de cuatro cajas. El área verde indica espera media menor que 5 minutos en ambas operaciones.")
    I.p(f"La razón es que la caja única de cada operación tiene una utilización similar (ρ ≈ {f(rho[('B_1R_2P', 'Retiro')]['teo'], 2)} para retiros y "
        f"{f(rho[('C_2R_1P', 'Pago')]['teo'], 2)} para pagos) y produce una espera de entre {f(B['retiro'], 1)} y {f(C['pago'], 1)} minutos, pero los retiros "
        f"son el 70 % de la demanda: sacrificar a los {f(dem['pagos'], 0)} usuarios de pago es menos costoso que sacrificar a los "
        f"{f(dem['retiros'], 0)} de retiro. El costo de la opción 2R + 1P es que los pagos esperan {f(C['pago'])} minutos en promedio, valor por "
        "encima del criterio de 5 minutos (Figura 8).")
    I.p("**Recomendación del punto 5:** (a) lo mejor para el banco es no dedicar cajas y mantener las tres mixtas; (b) si la exclusividad es "
        "obligatoria con tres cajas, asignar **2 cajas a retiros y 1 a pagos**; y (c) si además se quiere que ambas operaciones tengan esperas "
        "medias menores que 5 minutos, habilitar una cuarta caja con **2 cajas exclusivas para retiros y 2 para pagos**.")
    I.tabla("Diferencias emparejadas de la espera media entre configuraciones", ["Comparación", "Diferencia media (min)", "IC 95 %"],
            [["1R + 2P − 2R + 1P", f(dif["B-C"][0]), ic_txt(dif["B-C"])],
             ["2R + 1P − 3 mixtas", f(dif["C-A"][0]), ic_txt(dif["C-A"])],
             ["1R + 2P − 3 mixtas", f(dif["B-A"][0]), ic_txt(dif["B-A"])],
             ["3 mixtas − 2R + 2P", f(dif["A-E"][0]), ic_txt(dif["A-E"])],
             ["3 mixtas − 4 mixtas", f(dif["A-D"][0]), ic_txt(dif["A-D"])],
             ["2R + 2P − 4 mixtas", f(dif["E-D"][0]), ic_txt(dif["E-D"])]],
            anchos=[5.5, 4.0, 4.0],
            nota="Diferencias entre las 30 réplicas emparejadas. Un IC que no contiene el cero indica una diferencia significativa.")

    # ---------- Conclusiones
    I.titulo("Conclusiones")
    I.p(f"La simulación de 30 jornadas de ocho horas muestra que la configuración actual, con tres cajas que atienden retiros y pagos, ofrece "
        f"el mejor desempeño entre las configuraciones de tres cajas: espera media de {f(A['espera'])} minutos, percentil 95 de {f(A['p95'])} "
        f"minutos y utilización de {pct(A['util'], 0)}. Con ρ < 1 el sistema es estable y no se justifica, con los datos disponibles, crear una "
        "caja adicional; una cuarta caja mixta recortaría la espera en unos 30 segundos por usuario, pero requeriría un análisis de costos.")
    I.p(f"En la configuración actual, C3 tiene el menor tiempo promedio de atención ({f(menor['servicio'])} min) y C1 el mayor "
        f"({f(mayor['servicio'])} min), aunque la diferencia no es estadísticamente significativa y se explica por la mezcla aleatoria de "
        f"usuarios. Llegan en promedio {f(dem['media'])} usuarios por día: {f(dt['Rápido']['media'])} rápidos, {f(dt['Normal']['media'])} normales, "
        f"{f(dt['Lento']['media'])} lentos y {f(dt['Muy lento']['media'])} muy lentos. La réplica con menos usuarios fue la {dem['replica_min']} "
        f"({dem['minimo']}), y entre las configuraciones la de cuatro cajas mixtas deja menos usuarios sin atender al cierre.")
    I.p("Si el banco necesita reservar cajas por operación, debe asignar dos a retiros y una a pagos, porque reduce la espera global frente a "
        "la alternativa inversa y protege a la mayoría de los usuarios; pero los pagos quedarían con esperas de unos 8 minutos. Con cuatro "
        "cajas, dos para cada operación equilibran la espera en menos de un minuto. La principal enseñanza es que la separación de "
        "operaciones reduce la eficiencia del conjunto de cajas, porque una caja libre no puede ayudar a la otra fila.")
    I.p("*Limitaciones.* Los resultados dependen de las medias de las tablas, de que el día empiece con el banco vacío, de que no haya "
        "variación de la demanda por hora, de que los usuarios no cambien de fila ni abandonen la cola y de la regla de asignación a la caja con "
        "menos trabajos pendientes. No se incluyeron costos, pausas del personal ni las características de un posible cajero electrónico. "
        "Los umbrales de 5 y 10 minutos son un criterio de trabajo del grupo. Finalmente, como las tablas combinan varias medias, el "
        "sistema no es una M/M/1 homogénea exacta, y por eso los resultados provienen de la simulación y no de fórmulas cerradas.")

    # ---------- Referencias
    I.titulo("Referencias Bibliográficas")
    refs = [
        "Banks, J., Carson, J. S., II, Nelson, B. L., & Nicol, D. M. (2010). *Discrete-event system simulation* (5.ª ed.). Pearson.",
        "Gross, D., Shortle, J. F., Thompson, J. M., & Harris, C. M. (2008). *Fundamentals of queueing theory* (4.ª ed.). Wiley.",
        "Institución Universitaria Digital de Antioquia. (s. f.). *Laboratorio: Problema bancario. Simulación de sistemas de colas* [Material de curso]. Programa de Ingeniería de Software y Datos.",
        "Law, A. M. (2015). *Simulation modeling and analysis* (5.ª ed.). McGraw-Hill Education.",
        "Little, J. D. C. (1961). A proof for the queuing formula: L = λW. *Operations Research, 9*(3), 383-387. https://doi.org/10.1287/opre.9.3.383",
        "Taco-Mena, D., Gutiérrez-Ojeda, M., Castillo-Reyes, A., & Iñiguez-Izquierdo, J. (2019). Determinación del número óptimo de iteraciones para las simulaciones por el método de Montecarlo. *DYNA*, *94*(2), 129-130. https://doi.org/10.6036/9046",
    ]
    for r_ in refs:
        par = I.d.add_paragraph()
        par.paragraph_format.left_indent = Cm(1.27); par.paragraph_format.first_line_indent = Cm(-1.27)
        par.paragraph_format.line_spacing = 2.0
        runs_con_formato(par, r_)

    # ---------- Anexos
    I.pagina_nueva()
    I.titulo("Anexo A. Usuarios por réplica")
    import pandas as pd
    dem_df = pd.read_csv(resultados / "demanda_por_replica.csv", encoding="utf-8-sig")
    I.tabla("Total de usuarios por réplica, tipo y operación", ["Réplica", "Rápido", "Normal", "Lento", "Muy lento", "Retiros",
            "Pagos", "Total"],
            [[int(r.replica), int(r.Todos_Rápido), int(r.Todos_Normal), int(r.Todos_Lento), int(r["Todos_Muy lento"]),
              int(r.Retiro), int(r.Pago), int(r.total)] for _, r in dem_df.iterrows()] +
            [["Promedio", f(dem_df["Todos_Rápido"].mean()), f(dem_df["Todos_Normal"].mean()), f(dem_df["Todos_Lento"].mean()),
              f(dem_df["Todos_Muy lento"].mean()), f(dem_df.Retiro.mean()), f(dem_df.Pago.mean()), f(dem_df.total.mean())]],
            anchos=[2.2, 2.0, 2.0, 2.0, 2.2, 2.0, 2.0, 2.0], tam=8.5, repetir_encabezado=True, mantener=False,
            nota="Los desgloses por operación y tipo de las 30 réplicas están en demanda_por_replica.csv.")
    I.pagina_nueva()
    I.titulo("Anexo B. Desempeño de cada caja en todas las configuraciones")
    I.tabla("Servicio, espera y utilización por caja", ["Configuración", "Caja", "Tipo", "Usuarios por día", "Servicio (min)",
            "Espera (min)", "Sistema (min)", "Utilización"],
            [[ETIQ[c["escenario"]], c["caja"], c["capacidad"], f(c["clientes"]), f(c["servicio"]), f(c["espera"]),
              f(c["sistema"]), pct(c["util"], 0)] for c in R["cajas"]],
            anchos=[2.4, 1.4, 2.0, 2.2, 2.2, 2.0, 2.2, 2.2], tam=8, repetir_encabezado=True, mantener=False,
            nota="Promedios de 30 réplicas. El servicio es el tiempo medio de atención por usuario.")
    I.pagina_nueva()
    I.titulo("Anexo C. Código fuente del modelo (simulacion_bancaria.py)")
    I.p("El código completo, las pruebas, los datos por usuario y las gráficas están en el repositorio: ", sangria=False, espaciado=1.5)
    par = I.d.paragraphs[-1]
    hipervinculo(par, REPO)
    I.codigo((Path(__file__).parent / "simulacion_bancaria.py").read_text(encoding="utf-8"))

    destino.mkdir(parents=True, exist_ok=True)
    salida = destino / f"{nombre}.docx"
    I.d.core_properties.title = "Actividad didáctica 2-M3. Solución de un problema bancario"
    I.d.core_properties.author = "Grupo de trabajo 15"
    I.d.save(salida)
    return salida


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--resultados", type=Path, default=Path("resultados"))
    ap.add_argument("--destino", type=Path, default=Path("entrega"))
    ap.add_argument("--nombre", default="Grupo_15_EA3")
    a = ap.parse_args()
    print("Generado:", construir(a.resultados, a.destino, a.nombre))
