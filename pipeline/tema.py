# -*- coding: utf-8 -*-
"""Pasos 6 a 12 de Foné: tema de la dificultad (menciones, selector, combinación, causas generales, rescate de la frase, unión de frases obvias y archivo de temas finales).

Archivo generado a partir de los scripts del flujo original sin cambiar su lógica: cada paso es una
función ``paso_NN_*`` y los módulos de apoyo se cargan bajo demanda con ``_modulo()`` y solo conservan
las definiciones que algún paso usa. Las marcas de ruta y de carpeta de datos que traen sus rutas las
reemplaza ``fone_pipeline.py`` al preparar la copia de ejecución.
"""
import sys
from types import SimpleNamespace

_BIBLIOTECAS = {}
_CACHE = {}
import clasificacion as _clasificacion

def _biblioteca(nombre):
    def registrar(f):
        _BIBLIOTECAS[nombre] = f
        return f
    return registrar


def _modulo(nombre):
    """Devuelve el módulo de apoyo ``nombre`` (se carga una sola vez)."""
    if nombre in _CACHE:
        return _CACHE[nombre]
    if nombre in _BIBLIOTECAS:
        argv, sys.argv = sys.argv, ["fone_pipeline"]
        try:
            _CACHE[nombre] = SimpleNamespace(**_BIBLIOTECAS[nombre]())
        finally:
            sys.argv = argv
        return _CACHE[nombre]
    try:
        return _clasificacion._modulo(nombre)
    except ImportError:
        pass
    raise ImportError(nombre)



@_biblioteca("combinar_temas")
def _cargar_combinar_temas():
    import json

    import re

    import sys

    import unicodedata

    from collections import Counter

    NO_TEMA = _modulo("tema_automatico").NO_TEMA
    norm = _modulo("tema_automatico").norm

    D = r"RUTA_PROYECTO\resultados\temas_curso"

    VOCAB_TOKENS = {}

    def toks(ts):
        return {w[:6] for t in ts for w in re.findall(r"[a-z0-9]+", norm(t)) if len(w) > 3}

    return {k: v for k, v in locals().items() if not k.startswith('__')}


@_biblioteca("combinar_temas_v4")
def _cargar_combinar_temas_v4():
    import json

    import re

    import sys

    toks = _modulo("combinar_temas").toks

    D = r"RUTA_PROYECTO\resultados\temas_curso"

    MAX_TEMAS = 3

    def sin_redundantes(temas):
        out = []
        for t in temas:
            tt = toks([t])
            if any(tt < toks([o]) or (tt == toks([o]) and len(o) > len(t)) for o in temas if o != t):
                continue
            out.append(t)
        return out

    return {k: v for k, v in locals().items() if not k.startswith('__')}


@_biblioteca("tema_automatico")
def _cargar_tema_automatico():
    import collections

    import json

    import re

    import statistics

    import sys

    import unicodedata

    import spacy

    T = r"RUTA_PROYECTO"

    OUT = T + r"\resultados\temas_curso"

    MIN_AUDIOS, MIN_EST, RATIO, RATIO_UNA, VENTANA_PALABRAS, PALABRAS_ANTES = 4, 3, 2.0, 5.0, 40, 30

    NO_TEMA = set("""horario ritmo curso clase tema semana gracias profesor profe parcial quiz taller ejercicio cosa vez momento forma manera
parte caso tipo orden tiempo dia hora nota estudiante companero material ejemplo pregunta duda dificultad problema punto audio grabacion semestre corte
tarea mes ano fin lado lugar poco mucho gente persona grupo sesion respuesta idea nombre numero cantidad
lunes martes miercoles jueves viernes sabado domingo preparcial finde fecha rato
verdad hola buenas noches noche tardes dias paso repaso resultado informacion monton""".split())

    def norm(s):
        return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")

    def candidatos(doc):
        """Frases nominales como tuplas de lemas normalizados + (inicio, fin) en caracteres."""
        out = []
        for ch in doc.noun_chunks:
            toks = [t for t in ch if t.pos_ in ("NOUN", "PROPN", "ADJ", "ADP", "NUM") and not t.is_punct]
            while toks and toks[0].pos_ in ("ADP", "NUM"):
                toks = toks[1:]
            while toks and toks[-1].pos_ in ("ADP", "NUM"):
                toks = toks[:-1]
            if not toks or toks[0].pos_ == "ADJ" or ch.root.pos_ not in ("NOUN", "PROPN"):
                continue
            if len(toks) > 3:
                toks = toks[:3]
            lem = tuple(norm(t.lemma_) for t in toks if t.pos_ != "ADP")
            if not lem or any(len(l) < 2 for l in lem) or lem[0] in NO_TEMA or all(l in NO_TEMA for l in lem):
                continue
            if len(lem) == 1 and len(lem[0]) < 4:
                continue
            out.append((lem, toks[0].idx, toks[-1].idx + len(toks[-1].text), " ".join(t.text.lower() for t in toks),
                        extender(doc, toks[0].i, toks[-1].i)))
        return out

    def extender(doc, s, e):
        """Nombre completo del tema (v3): spaCy parte "reduccion de dimensionalidad" en dos frases nominales; se
    une con el sustantivo vecino unido por "de/del" (a la izquierda y a la derecha), hasta 6 palabras, sin cabezas
    de la lista de no-temas ("parte de", "tipo de"). Devuelve (inicio_car, fin_car)."""
        n = len(doc)
        for _ in range(2):
            if s >= 2 and doc[s - 1].lower_ in ("de", "del") and doc[s - 2].pos_ in ("NOUN", "PROPN") \
                    and norm(doc[s - 2].lemma_) not in NO_TEMA and e - s + 3 <= 6:
                s -= 2
            else:
                break
        for _ in range(2):
            if e + 2 < n and doc[e + 1].lower_ in ("de", "del") and doc[e + 2].pos_ in ("NOUN", "PROPN") \
                    and norm(doc[e + 2].lemma_) not in NO_TEMA and e - s + 3 <= 6:
                e += 2
                while e + 1 < n and doc[e + 1].pos_ in ("PROPN", "ADJ") and e - s + 1 < 6:
                    e += 1
            else:
                break
        return doc[s].idx, doc[e].idx + len(doc[e].text)

    CORRECCIONES_ASR = {"edad": "EDA", "edad bivariado": "EDA bivariado", "edad univariado": "EDA univariado"}

    def nombre_completo(texto_doc, lem, rango, vocab_lemas):
        nombre = texto_doc[rango[0]:rango[1]].lower().strip()
        return CORRECCIONES_ASR.get(nombre, nombre)

    return {k: v for k, v in locals().items() if not k.startswith('__')}


@_biblioteca("tema_extractivo")
def _cargar_tema_extractivo():
    import json

    import re

    import unicodedata

    import urllib.request

    URL = "http://localhost:11434/api/generate"

    MODELO = "qwen2.5:7b-instruct"

    SISTEMA = """Un estudiante universitario responde por audio la pregunta "¿Qué se te dificultó esta semana?". Te doy un fragmento de su transcripción con la palabra que
sugiere dificultad marcada entre **asteriscos**.

Tu tarea:
1. Decide si el estudiante expresa una dificultad REAL suya (le costó, no entendió, le preocupa, le fue mal). No lo es si dice que NO se le dificultó, si "difícil" describe
   un concepto técnico o si no habla de sí mismo.
2. Si lo es, COPIA del fragmento, con las mismas palabras, la frase corta (2 a 8 palabras) con la que el estudiante nombra LO QUE se le dificultó: puede ser un tema de la
   materia, pero también otra cosa (el horario, un parcial o quiz, la carga de talleres, la explicación del profesor, practicar, el ritmo...). Debe ser lo que le costó, no lo que
   solo vio, repasó o aprendió. Si el estudiante no nombra nada concreto ("se me dificultó un poco", "fue difícil, todo"), deja la frase vacía.

Responde SOLO un JSON de una línea: {"es_dificultad": true|false, "causa": "frase copiada del texto o vacío"}

Ejemplos (inventados):
Fragmento: "esta semana vimos pilas y colas. Lo que más se **dificultó** fue entender cómo se hereda una clase en Java, y lo demás bien"
JSON: {"es_dificultad": true, "causa": "cómo se hereda una clase en Java"}

Fragmento: "el ritmo va bien. Se me **dificultó** el horario, porque la clase es a las siete de la mañana y me cuesta madrugar"
JSON: {"es_dificultad": true, "causa": "el horario"}

Fragmento: "vimos integrales y límites, la verdad no se me **dificultó** nada, todo claro"
JSON: {"es_dificultad": false, "causa": ""}

Fragmento: "esta semana se me **dificultó** un poco, no sé, de pronto fue la semana larga, pero bien"
JSON: {"es_dificultad": true, "causa": ""}

Fragmento: "repasamos derivadas. Lo que más me **costó** fue el quiz, porque no esperaba ese tipo de preguntas, y las derivadas sí las entendí"
JSON: {"es_dificultad": true, "causa": "el quiz"}

Fragmento: "esta semana vimos series y límites, y creo que se me **dificultó** un poquito el tema, más que todo con las series geométricas, pero bien"
JSON: {"es_dificultad": true, "causa": "las series geométricas"}

"""

    GENERICAS = {"el tema", "tema", "la semana", "esta semana", "eso", "esto", "todo", "casi todo", "un poco", "cosas", "las cosas", "la clase", "el curso", "lo que vimos"}

    def norm(s):
        s = unicodedata.normalize("NFD", s.lower())
        return re.sub(r"\s+", " ", "".join(c for c in s if unicodedata.category(c) != "Mn")).strip()

    def recortar(texto_con_marca, antes=300, despues=260):
        t = texto_con_marca.replace("\n", " ")
        a = t.find("**")
        b = t.find("**", a + 2) if a >= 0 else -1
        if a < 0 or b < 0:
            return t[:antes + despues]
        return t[max(0, a - antes): b + 2 + despues]

    def extraer(texto_con_marca):
        v = recortar(texto_con_marca)
        prompt = f'{SISTEMA}\nAhora tú:\nFragmento: "{v}"\nJSON:'
        data = json.dumps({"model": MODELO, "prompt": prompt, "stream": False, "options": {"temperature": 0, "num_predict": 80}}).encode("utf-8")
        req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as r:
            out = json.loads(r.read())["response"].strip()
        try:
            j = json.loads(out[out.index("{"): out.rindex("}") + 1])
            es = bool(j.get("es_dificultad", False))
            causa = str(j.get("causa", "") or "").strip().strip('."«»')
        except Exception:
            return {"es_dificultad": None, "causa": "", "crudo": out, "ventana": v}
        causa = verificar(causa, v)
        return {"es_dificultad": es, "causa": causa if es else "", "crudo": out, "ventana": v}

    VACIAS = set("""el la los las un una unos unas este esta esto estos estas ese esa eso esos esas aquel aquello todo toda todos todas ultimo ultima ultimos ultimas primer primero
primera segundo segunda de del que lo y en a al mas muy poco tema temas parte partes proceso procesos punto puntos cosa cosas demostracion conlleva mismo misma otro otra""".split())

    def es_generica(nc):
        """Frase sin contenido propio ('este ultimo tema', 'este proceso', 'el primer punto'): todas sus palabras son determinantes o palabras comodin."""
        ws = re.findall(r"\w+", nc)
        return bool(ws) and all(w in VACIAS for w in ws)

    def verificar(causa, ventana):
        """La causa debe salir del texto: si no aparece literal, cada una de sus palabras (con raiz de 5 letras) debe aparecer en la ventana (tolera el 'invertas' del
    transcriptor o 'los ejercicios de la casa' dicho como 'los ejercicios ... los de la casa'). Se recorta a 12 palabras. Las frases genericas ('el tema') se descartan."""
        if not causa:
            return ""
        nc, nv = norm(causa), norm(ventana)
        if nc in GENERICAS or es_generica(nc):
            return ""
        if nc not in nv:
            palabras = [w for w in re.findall(r"\w+", nc) if len(w) > 3]
            if not palabras or not all(any(tv.startswith(w[:5]) for tv in re.findall(r"\w+", nv)) for w in palabras):
                return ""  # algo que el estudiante no dijo
        w = causa.split()
        return " ".join(w[:12]) if len(w) > 12 else causa

    return {k: v for k, v in locals().items() if not k.startswith('__')}


@_biblioteca("tema_factores_v11")
def _cargar_tema_factores_v11():
    import json

    import re

    import unicodedata

    T = r"RUTA_PROYECTO\resultados"

    def norm(s):
        s = unicodedata.normalize("NFD", s.lower())
        return "".join(c for c in s if unicodedata.category(c) != "Mn")

    FACTORES = [
        ("Evaluaciones (parcial, quiz)", r"\b(parcial|parciales|preparcial|quiz|quices|examen|examenes|evaluacion|evaluaciones)\b"),
        ("Carga de trabajo (talleres, tareas, cantidad de temas)",
         r"\b(taller|talleres|tarea|tareas|proyecto|proyectos|entrega|entregas|trabajos? (tan )?largos?|mucho trabajo|muchos temas|cantidad de (temas|trabajo|contenido)|bastantes temas|mucha materia|mucho contenido|muchos conceptos|extens[oa]s?)\b"),
        ("Ritmo y densidad del curso",
         r"(muy rapido|demasiado rapido|va rapido|un poco rapido|ritmo (muy )?(rapido|acelerado)|acelerad|\b(denso|densos|densa|densas)\b|\bpesad[oa]s?\b|agobi|abrum|(no|nunca) (me )?(da|daba|dio|dan) tiempo (de|para) procesar|se hace (mas|cada) )"),
        ("Explicación del profesor",
         r"(no (le )?(entend\w*|comprend\w*) (nada )?(al|lo que (dijo|explic\w*|dice))( profe\w*)?|(profe\w*|docente)\s+(va|explica|habla|avanza)\s+(muy|demasiado|rapid)|(como|forma en que|manera en que)\s+(explica|ensena)|explicacion\w*\s+(no|poco|confus)|metodologia)"),
        ("Conceptos previos (de semestres pasados)",
         r"(no (me )?(recordaba|acordaba|recuerdo|recordar)|semestres? (pasados?|anteriores?)|se supone que ya|prerrequisito|volver a (coger|repasar)|bases? de)"),
        ("Tiempo y organización",
         r"(no (tuve|tenia|me dio|alcance a tener)\s+(el )?tiempo|falta de tiempo|me falto tiempo|organizarme|mi organizacion|estudiar con anticipacion|no me dio tiempo)"),
        ("Atención y estado personal", r"(atencion|concentr|cansad|\bsueno\b|distrai|distraid|estres|motivacion|\banimo\b|enferm|problemas personales)"),
        ("Horario y logística", r"(horario|madrugar|temprano|\b7 ?am\b|plataforma|internet|\bvirtual\b|asistir|inasistencia|salon|\bsede\b|hora de la clase)"),
    ]

    FACT_RX = [(n, re.compile(r, re.I)) for n, r in FACTORES]

    CONT = 140

    ANTES, DESPUES = 90, 110

    ZONA_ANTES, ZONA_DESPUES, ZONA_ANTES_ANAFORA = 60, 300, 300  # arreglo 1 (11 oct): la zona hacia adelante sube de 140 a 300 caracteres (la respuesta puede seguir en otra frase)

    ANAFORA = re.compile(r"\b(ese|esa|esos|esas|eso|esto|este|esta|estos|estas|aquel|aquello|lo anterior|lo mismo)\b")

    def segmento(x):
        """Ventana alrededor de la palabra de dificultad (la que va entre ** en texto_amplio): el factor debe estar pegado a la dificultad."""
        t = x["texto_amplio"].replace("\n", " ")
        a = t.find("**")
        b = t.find("**", a + 2) if a >= 0 else -1
        if a < 0 or b < 0:
            return x["oracion"].replace("\n", " ")
        seg = t[max(0, a - ANTES):b + 2 + DESPUES].replace("**", "")
        return seg

    def factores(x):
        s = norm(segmento(x))
        return [n for n, rx in FACT_RX if rx.search(s)]

    def asignar_v11(x):
        """Misma logica que main() para una mencion suelta (campos: oracion, texto_amplio, r, candidatos, tema, confianza). Devuelve tema_v11, factores y tipo_v11."""
        if x["confianza"] == "no_dificultad":
            return dict(tema_v11=[], factores=[], tipo_v11="no_dificultad")
        f = factores(x)
        seg = norm(segmento(x))
        pos = {c["nombre"]: (c["pos"] - x["r"][0], c["rel"]) for c in x["candidatos"]}
        t_amp = x["texto_amplio"].replace("\n", " ")
        a_, b_ = t_amp.find("**"), t_amp.find("**", t_amp.find("**") + 2)
        anafora = a_ >= 0 and b_ >= 0 and bool(ANAFORA.search(norm(t_amp[b_ + 2:b_ + 2 + 45])))
        zona_antes = ZONA_ANTES_ANAFORA if anafora else ZONA_ANTES
        en_zona = [t for t in x["tema"] if t in pos and ((pos[t][1] == "despues" and 0 <= pos[t][0] <= ZONA_DESPUES) or (pos[t][1] == "antes" and 0 < -pos[t][0] <= zona_antes))]
        contenido = [t for t in x["tema"] if norm(t) in seg]
        if f:
            return dict(tema_v11=f + [t for t in dict.fromkeys(contenido + en_zona) if t not in f], factores=f, tipo_v11="factor")
        if en_zona:
            return dict(tema_v11=en_zona, factores=[], tipo_v11=x["confianza"])
        return dict(tema_v11=[], factores=[], tipo_v11="sin_tema")

    return {k: v for k, v in locals().items() if not k.startswith('__')}


def paso_06_menciones():
    r"""Paso: script «absa_v10_paso1_menciones_y_candidatos».

    ABSA sobre la MISMA lista de dificultades del panel v8. Paso 1: menciones y candidatos de tema.
    - Menciones = oraciones con P2_tipo == 'D+' del panel v8 (oraciones_etiquetadas_v9.jsonl), sin las consignas repetidas en voz alta.
      Cada una se ubica en la transcripcion completa del audio. r = rango de caracteres de la senal (primer match del lexico DIFICULTAD o de la
      extension; si no hay, los primeros 60 caracteres de la oracion).
    - Candidatos de tema: misma logica que tema_automatico.py (v3.1/v4): vocabulario automatico por curso (recalculado igual, sobre los mismos
      audios) y ventana amplia de 60 palabras antes y despues, cortada donde empieza el ritmo.
    - tema_llm (senal independiente para 'confirmado'): se hereda del ABSA anterior solo si una mencion anterior cae dentro de la oracion.
    Salida: resultados\temas_curso\temas_auto_menciones_v10.json
    """
    # -*- coding: utf-8 -*-
    import collections
    import json
    import re
    import sys

    import spacy

    TA = _modulo("tema_automatico")

    # vocabulario con umbral 3 audios / 2 estudiantes + limpieza
    TA.MIN_AUDIOS, TA.MIN_EST = 3, 2
    MATEMATICOS = {"pearson", "spearman", "kendall", "gauss", "jordan", "newton", "raphson", "lagrange", "chebyshev", "shapiro", "wilk", "mann", "whitney",
                   "kolmogorov", "smirnov", "mahalanobis", "student", "fisher", "fischer", "euler", "taylor", "riemann", "cramer", "bayes", "welch",
                   "maclaurin", "jacobi", "simpson", "schmidt", "gram", "lu", "qr", "pca", "psa", "eda", "crisp", "mice", "knn"}
    BASURA = {"gracias", "notebook", "layers", "eh", "bueno", "ritmo", "profesor", "profe", "parcial", "cosa", "cosas", "hola", "samuel", "lopez", "lópez"}


    def termino_ruido(nombre):
        """True si el termino del vocabulario es un nombre de persona, un saludo/metacomentario o un error evidente del transcriptor."""
        toks = nombre.replace("-", " ").split()
        low = [t.lower() for t in toks]
        if any(t in BASURA for t in low):
            return True
        if any(re.fullmatch(r"[a-z]\d+", t) for t in low):  # "r3", "x50": restos de formulas
            return True
        # nombre de persona: 2 o 3 palabras que son todas partes de nombres del roster y ninguna es un matematico conocido
        # (los terminos del vocabulario salen en minuscula, asi que no se puede usar la mayuscula inicial)
        if len(toks) in (2, 3) and all(sin_tilde(t) in NOMBRES_ROSTER for t in toks) and not any(sin_tilde(t) in MATEMATICOS for t in toks):
            return True
        return False


    def sin_tilde(s):
        import unicodedata
        return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


    def _cargar_roster():
        import pandas as pd
        df = pd.read_excel(T_RAIZ + r"\Foné — Estudiantes.xlsx")
        col = next(c for c in df.columns if "nombre" in c.lower())
        partes = set()
        for v in df[col].dropna():
            for p in re.split(r"\s+", str(v)):
                p = sin_tilde(p)
                if len(p) >= 3 and p.isalpha():
                    partes.add(p)
        return partes


    T_RAIZ = r"RUTA_PROYECTO"
    NOMBRES_ROSTER = _cargar_roster()
    cargar_audios_curso = _modulo("procesar_absa").cargar_audios_curso
    CURSOS = _modulo("procesar_absa").CURSOS
    DIFICULTAD = _modulo("lexico_matching").DIFICULTAD
    encontrar_spans = _modulo("lexico_matching").encontrar_spans
    tokenizar_con_posicion = _modulo("lexico_matching").tokenizar_con_posicion
    DIFICULTAD_EXT = _modulo("reglas_oracion_v2").DIFICULTAD_EXT
    es_consigna = _modulo("construir_panel_preguntas_v9").es_consigna

    T = r"RUTA_PROYECTO"
    OUT = T + r"\resultados\temas_curso"


    def span_senal(oracion, base):
        toks = tokenizar_con_posicion(oracion)
        for dic in (DIFICULTAD, DIFICULTAD_EXT):
            sp = [s for s in encontrar_spans(oracion, toks, dic, True) if s["cuenta"]]
            if sp:
                s = min(sp, key=lambda x: x["start"])
                return [base + s["start"], base + s["end"]], s["entrada"]
        return [base, base + min(60, len(oracion))], "regla v8"


    def main():
        nlp = spacy.load("es_core_news_sm", disable=["ner"])
        audios = {c: cargar_audios_curso(c) for c in CURSOS}
        docs, cand = {}, {}
        for c, auds in audios.items():
            for a, d in zip(auds, nlp.pipe([x["texto"] for x in auds], batch_size=16)):
                k = (c, str(a["cedula"]), a["fecha_sesion"])
                docs[k] = d
                cand[k] = TA.candidatos(d)
        print("audios parseados:", len(docs), flush=True)
        df, est, formas = {c: collections.Counter() for c in CURSOS}, {c: collections.defaultdict(set) for c in CURSOS}, collections.defaultdict(collections.Counter)
        for (c, ced, ses), cs in cand.items():
            vistos = set()
            for lem, i, j, surf, _ in cs:
                formas[(c, lem)][surf] += 1
                vistos.add(lem)
            for lem in vistos:
                df[c][lem] += 1
                est[c][lem].add(ced)
        n = {c: len(audios[c]) for c in CURSOS}
        vocab = {}
        for c in CURSOS:
            v = {}
            for lem, k in df[c].items():
                if k < TA.MIN_AUDIOS or len(est[c][lem]) < TA.MIN_EST:
                    continue
                piso = min(df[o].get(lem, 0) / n[o] for o in CURSOS if o != c)
                ratio = (k / n[c]) / (piso + 0.005)
                if ratio >= (TA.RATIO if len(lem) > 1 else TA.RATIO_UNA):
                    v[lem] = {"nombre": formas[(c, lem)].most_common(1)[0][0], "audios": k, "estudiantes": len(est[c][lem])}
            quitados = [x["nombre"] for x in v.values() if termino_ruido(x["nombre"])]
            v = {k: x for k, x in v.items() if not termino_ruido(x["nombre"])}
            print(c, "vocabulario 3/2:", len(v), "| quitados por ruido:", quitados, flush=True)
            vocab[c] = v
            json.dump(list(v.values()), open(T + rf"\resultados\temas_curso\vocabulario_auto_{c}.json", "w", encoding="utf-8"), ensure_ascii=False)
        anterior = json.load(open(T + r"\resultados\absa_dashboard_CARPETA_DATOS.json", encoding="utf-8"))
        texto_de = {(c, str(a["cedula"]), a["fecha_sesion"]): a["texto"] for c in CURSOS for a in audios[c]}
        res, sin_ubicar = [], 0
        for l in open(T + r"\resultados\panel_preguntas\oraciones_etiquetadas_v9.jsonl", encoding="utf-8"):
            a = json.loads(l)
            c, ced, ses = a["curso"], str(a["cedula"]), a["fecha_sesion"]
            clave = (c, ced, ses)
            if clave not in docs:
                continue
            d, texto = docs[clave], texto_de[clave]
            viejos = [m for m in anterior[c.lower()]["menciones"] if str(m["c"]) == ced and m["s"] == ses and m["d"] == "DIFICULTAD"]
            cursor = 0
            for o in a["oraciones"]:
                pos = texto.find(o["oracion"], cursor)
                if pos >= 0:
                    cursor = pos + len(o["oracion"])
                if o["P2_tipo"] != "D+" or es_consigna(o["oracion"]):
                    continue
                if pos < 0:
                    sin_ubicar += 1
                    continue
                (ini, fin), entrada = span_senal(o["oracion"], pos)
                t_llm = []
                for m in viejos:
                    if pos <= m["r"][0] < pos + len(o["oracion"]):
                        t_llm += [t for t in m["t"] if t not in t_llm]
                palabras = [t for t in d if t.idx >= ini and not t.is_space and not t.is_punct]
                pal_antes = [t for t in d if t.idx < ini and not t.is_space and not t.is_punct]
                ini_amp = pal_antes[-60].idx if len(pal_antes) >= 60 else 0
                lim_amp = palabras[59].idx + len(palabras[59].text) if len(palabras) >= 60 else len(d.text)
                cr = re.search(r"\britmo\b", d.text[fin:lim_amp], re.I)
                if cr:
                    lim_amp = fin + cr.start()
                vocab_lemas = {x for k2 in vocab[c] for x in k2}
                vistos_c, cands = set(), []
                for lem, i, j, surf, rango in cand[clave]:
                    if lem in vocab[c] and ini_amp <= i < lim_amp:
                        nom = TA.nombre_completo(d.text, lem, rango, vocab_lemas) or vocab[c][lem]["nombre"]
                        if nom not in vistos_c:
                            vistos_c.add(nom)
                            cands.append({"nombre": nom, "pos": i, "rel": "despues" if i >= ini else "antes"})
                res.append({"curso": c, "c": ced, "s": ses, "d": "DIFICULTAD", "e": entrada, "r": [ini, fin], "oracion": o["oracion"],
                            "senales": o["P2_senales"], "candidatos": cands,
                            "texto_amplio": d.text[ini_amp:ini] + "**" + d.text[ini:fin] + "**" + d.text[fin:lim_amp], "tema_llm": t_llm})
        json.dump(res, open(OUT + r"\temas_auto_menciones_v10.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"menciones v8: {len(res)} (sin ubicar: {sin_ubicar}) | con candidatos: {sum(bool(x['candidatos']) for x in res)} | con tema_llm heredado: {sum(bool(x['tema_llm']) for x in res)}")


    if True:
        main()





def paso_07_selector():
    r"""Paso: script «tema_selector_llm_v9».

    LLM como SELECTOR de tema: en vez de que el LLM invente el tema, elige entre los candidatos del
    vocabulario automatico del curso que aparecen en una ventana amplia (60 palabras antes y despues, cortada donde empieza
    el ritmo) y dice si la mencion expresa una dificultad real del estudiante. Pensado para (a) quitar menciones que no son
    dificultad ("cola pesada", "no se me dificulto nada"), (b) resolver si el tema va antes o despues, (c) permitir varios temas.
    Local (Ollama qwen2.5:7b-instruct, temperatura 0). Resumible: una linea por mencion en temas_selector_llm_v10.jsonl.
    Los ejemplos del prompt son inventados (no salen del corpus ni de las muestras juzgadas).
    """
    # -*- coding: utf-8 -*-
    import json
    import os
    import sys
    import time
    import urllib.request

    D = r"RUTA_PROYECTO\resultados\temas_curso"
    SALIDA = D + r"\temas_selector_llm_v10.jsonl"
    MODELO = "qwen2.5:7b-instruct"
    URL = "http://localhost:11434/api/generate"

    SISTEMA = """Un estudiante universitario responde por audio la pregunta "¿Qué se te dificultó esta semana?". Te doy un fragmento de su transcripción
con la palabra que sugiere dificultad marcada entre **asteriscos**, y una lista numerada de TEMAS candidatos que aparecen en el fragmento.

Tu tarea:
1. Decide si en la mención el estudiante expresa una dificultad REAL suya (le costó, no entendió, le preocupa, le fue mal). No lo es si dice que NO se le dificultó,
   si "difícil/pesado/complejo" describe el contenido en general o un concepto técnico (p. ej. "cola pesada"), o si no habla de sí mismo.
2. Si lo es, elige los temas candidatos QUE SE LE DIFICULTARON (uno o varios). El tema puede estar antes o después de la marca. No elijas temas que solo
   menciona haber visto, repasado o aprendido, ni los que dice que le quedaron claros. Si el tema que le costó NO está entre los candidatos (por ejemplo
   no aparece o está mal transcrito), devuelve una lista vacía: es mejor no elegir ninguno que elegir uno equivocado.

Responde SOLO un JSON de una línea: {"es_dificultad": true|false, "temas": [números]}

Ejemplos:
Fragmento: "esta semana vimos la regla del trapecio y los errores de truncamiento. Lo que más se me **dificultó** fue entender el error absoluto, y el"
Candidatos: 1) regla del trapecio 2) errores de truncamiento 3) error absoluto
JSON: {"es_dificultad": true, "temas": [3]}

Fragmento: "vimos matrices y vectores, la verdad no se me **dificultó** nada, todo claro"
Candidatos: 1) matrices 2) vectores
JSON: {"es_dificultad": false, "temas": []}

Fragmento: "miramos la curtosis, que significa que la cola está más **pesada** o más liviana que la normal"
Candidatos: 1) curtosis 2) distribución normal
JSON: {"es_dificultad": false, "temas": []}

Fragmento: "lo que más se me **dificultó** fue la factorización LU y también el pivoteo, aunque con las matrices todo bien"
Candidatos: 1) factorización lu 2) pivoteo 3) matrices
JSON: {"es_dificultad": true, "temas": [1, 2]}

Fragmento: "vimos el método de bisección, se me **complicó** un poco entender el criterio de parada, y hoy repasamos el método de Newton, que quedó claro"
Candidatos: 1) método de bisección 2) método de newton
JSON: {"es_dificultad": true, "temas": [1]}

Fragmento: "se me **complicó** entender cómo contar las operaciones primitivas; luego repasamos las medidas de dispersión, y eso sí quedó claro"
Candidatos: 1) medidas de dispersión 2) estructuras de datos
JSON: {"es_dificultad": true, "temas": []}
"""


    def preguntar(texto, candidatos):
        lista = "\n".join(f"{i}) {c}" for i, c in enumerate(candidatos, 1))
        prompt = f'{SISTEMA}\nAhora tú:\nFragmento: "{texto}"\nCandidatos:\n{lista}\nJSON:'
        data = json.dumps({"model": MODELO, "prompt": prompt, "stream": False, "options": {"temperature": 0}}).encode("utf-8")
        req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as r:
            out = json.loads(r.read())["response"].strip()
        try:
            j = json.loads(out[out.index("{"):out.rindex("}") + 1])
            temas = [int(t) for t in j.get("temas", []) if str(t).isdigit() and 1 <= int(t) <= len(candidatos)]
            return bool(j.get("es_dificultad", False)), temas, out
        except Exception:
            return None, [], out


    def main():
        r = json.load(open(D + r"\temas_auto_menciones_v10.json", encoding="utf-8"))
        hechos = set()
        if os.path.exists(SALIDA):
            hechos = {tuple(json.loads(l)["id"]) for l in open(SALIDA, encoding="utf-8") if l.strip()}
        pend = [x for x in r if x["d"] == "DIFICULTAD" and x["candidatos"]]
        pend = [x for x in pend if (x["curso"], x["c"], x["s"], x["r"][0]) not in hechos]
        print(f"pendientes: {len(pend)}", flush=True)
        with open(SALIDA, "a", encoding="utf-8") as f:
            for n, x in enumerate(pend, 1):
                cands = [c["nombre"] for c in sorted(x["candidatos"], key=lambda c: abs(c["pos"] - x["r"][0]))][:10]
                es, idx, crudo = preguntar(x["texto_amplio"], cands)
                f.write(json.dumps({"id": [x["curso"], x["c"], x["s"], x["r"][0]], "candidatos": cands, "es_dificultad": es,
                                    "temas": [cands[i - 1] for i in idx], "crudo": crudo}, ensure_ascii=False) + "\n")
                f.flush()
                if n % 20 == 0:
                    print(f"{n}/{len(pend)}", flush=True)
        print("listo", flush=True)


    if True:
        main()





def paso_08_combinar():
    r"""Paso: script «absa_v10_paso3_combinar_y_dashboard».

    ABSA sobre la lista de dificultades del panel v10. Paso 3: combina el selector LLM con la senal independiente (tema_llm heredado) y
    genera resultados\absa_dashboard_CARPETA_DATOS_v10.json con el mismo esquema que el v4 (las menciones de DUDAS se copian sin cambios).
    Reglas iguales a combinar_temas_v4.py: es_dificultad False -> 'no_dificultad'; sin tema elegido -> 'sin_tema'; hasta 3 temas ordenados por
    cercania; 'confirmado' si algun tema coincide con el tema libre del LLM del ABSA anterior (heredado), si no 'probable'. Menciones sin
    candidatos -> 'sin_tema'.
    """
    # -*- coding: utf-8 -*-
    import json
    import sys

    toks = _modulo("combinar_temas").toks
    sin_redundantes = _modulo("combinar_temas_v4").sin_redundantes
    MAX_TEMAS = _modulo("combinar_temas_v4").MAX_TEMAS

    T = r"RUTA_PROYECTO\resultados"
    aut = json.load(open(T + r"\temas_curso\temas_auto_menciones_v10.json", encoding="utf-8"))
    sel = {tuple(json.loads(l)["id"]): json.loads(l) for l in open(T + r"\temas_curso\temas_selector_llm_v10.jsonl", encoding="utf-8") if l.strip()}
    base = json.load(open(T + r"\absa_dashboard_CARPETA_DATOS_v4.json", encoding="utf-8"))
    cargar_audios_curso = _modulo("procesar_absa").cargar_audios_curso
    CURSOS = _modulo("procesar_absa").CURSOS
    texto_de = {(c, str(a["cedula"]), a["fecha_sesion"]): a["texto"] for c in CURSOS for a in cargar_audios_curso(c)}
    final, cnt = [], {}
    for x in aut:
        s = sel.get((x["curso"], x["c"], x["s"], x["r"][0]))
        if not x["candidatos"] or s is None or s["es_dificultad"] is None:
            tema, q = [], "sin_tema"
        elif not s["es_dificultad"]:
            tema, q = [], "no_dificultad"
        else:
            pos = {c["nombre"]: abs(c["pos"] - x["r"][0]) for c in x["candidatos"]}
            tema = sorted(sin_redundantes(s["temas"]), key=lambda t: pos.get(t, 1e9))[:MAX_TEMAS]
            otras = toks(list(x["tema_llm"]))
            q = "sin_tema" if not tema else ("confirmado" if any(toks([t]) & otras for t in tema) else "probable")
        cnt[q] = cnt.get(q, 0) + 1
        final.append(dict(x, tema=tema, confianza=q))
    json.dump(final, open(T + r"\temas_curso\temas_final_menciones_v10.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


    def clave_tema(t):
        return " ".join(w[:-2] if w.endswith("es") and len(w) > 5 else w[:-1] if w.endswith("s") and len(w) > 3 else w for w in t.lower().split())


    for g, v in base.items():
        curso = next(c for c in CURSOS if c.lower() == g)
        dudas = [m for m in v["menciones"] if m["d"] != "DIFICULTAD"]
        nuevas = []
        for f in final:
            if f["curso"] != curso:
                continue
            nuevas.append({"c": f["c"], "s": f["s"], "d": "DIFICULTAD", "e": f["e"], "t": f["tema"], "k": f"{f['c']}|{f['s']}", "r": f["r"],
                           "t_llm": f["tema_llm"], "q": f["confianza"], "t_extra": []})
        v["menciones"] = dudas + nuevas
        for m in nuevas:
            v["transcripciones"].setdefault(m["k"], texto_de[(curso, m["c"], m["s"])])
        v["tema_metodo"] = "lista de dificultades del panel v10 + vocabulario automatico por curso + selector LLM, con nivel de confianza"

        def ranking(solo_confirmado):
            acc = {}
            for m in v["menciones"]:
                if m["d"] != "DIFICULTAD" or m["q"] in ("no_dificultad", "sin_tema") or (solo_confirmado and m["q"] != "confirmado"):
                    continue
                for t in m["t"]:
                    a = acc.setdefault(clave_tema(t), {"nombres": {}, "ests": set(), "auds": set()})
                    a["nombres"][t] = a["nombres"].get(t, 0) + 1
                    a["ests"].add(str(m["c"]))
                    a["auds"].add(m["k"])  # una mencion cuenta una vez por audio y tema (evita contar dos frases seguidas del mismo audio como dos)
            return sorted(({"tema": max(a["nombres"], key=a["nombres"].get), "estudiantes": len(a["ests"]), "menciones": len(a["auds"])} for a in acc.values()),
                          key=lambda r: (-r["estudiantes"], -r["menciones"], r["tema"]))
        v["ranking_temas"] = ranking(True)
        v["ranking_temas_todos"] = ranking(False)
    json.dump(base, open(T + r"\absa_dashboard_CARPETA_DATOS_v10.json", "w", encoding="utf-8"), ensure_ascii=False)
    print("menciones DIFICULTAD v8:", len(final), cnt)
    ant = json.load(open(T + r"\absa_dashboard_CARPETA_DATOS_v4.json", encoding="utf-8"))
    for g in base:
        a = [m for m in ant[g]["menciones"] if m["d"] == "DIFICULTAD" and m["q"] not in ("no_dificultad",)]
        print(g, "| v4:", len(a), "menciones, ranking confirmados", len(ant[g]["ranking_temas"]), "temas | v8:", sum(1 for m in base[g]["menciones"] if m["d"] == "DIFICULTAD"),
              "menciones, ranking confirmados", len(base[g]["ranking_temas"]), "temas")
        print("   top v4:", [(r["tema"], r["estudiantes"]) for r in ant[g]["ranking_temas_todos"][:5]])
        print("   top v8:", [(r["tema"], r["estudiantes"]) for r in base[g]["ranking_temas_todos"][:5]])





def paso_09_causas_generales():
    r"""Paso: script «tema_factores_v11».

    Tema v11 = tema de contenido (vocabulario del curso + selector, como en v10) + FACTORES generales de dificultad.
    Motivo: lo que se le dificulta al estudiante puede no ser un tema del vocabulario sino un factor general:
    el horario, la explicacion del profesor, la carga de trabajo, las evaluaciones... En la muestra T (prueba limpia del tema v10) 9 de las 11 menciones
    incorrectas eran de ese tipo, y el selector, obligado a elegir un candidato, escogia un tema anterior sin relacion.
    Reglas (transparentes, sin LLM): se busca el factor en la oracion de la mencion mas los 140 caracteres siguientes (cubre oraciones cortadas por el
    transcriptor). Factores: evaluaciones, carga de trabajo, ritmo y densidad, explicacion del profesor, conceptos previos, tiempo y organizacion,
    atencion y estado personal, horario y logistica.
    Asignacion por mencion valida (no 'no_dificultad'):
      - si hay factor(es): tema = factores (+ los temas de contenido que aparecen en ese mismo segmento); confianza 'factor';
      - si no hay factor: se conserva el tema de contenido de v10 (confirmado/probable) o 'sin_tema'.
    Salidas: resultados\temas_curso\temas_final_menciones_v11.json y resultados\absa_dashboard_CARPETA_DATOS_v11.json (mismo esquema que v10; el
    dashboard ya cuenta m.t, asi que los factores aparecen como temas en el ranking).
    """
    # -*- coding: utf-8 -*-
    import json
    import re
    import unicodedata

    T = r"RUTA_PROYECTO\resultados"


    def norm(s):
        s = unicodedata.normalize("NFD", s.lower())
        return "".join(c for c in s if unicodedata.category(c) != "Mn")


    FACTORES = [
        ("Evaluaciones (parcial, quiz)", r"\b(parcial|parciales|preparcial|quiz|quices|examen|examenes|evaluacion|evaluaciones)\b"),
        ("Carga de trabajo (talleres, tareas, cantidad de temas)",
         r"\b(taller|talleres|tarea|tareas|proyecto|proyectos|entrega|entregas|trabajos? (tan )?largos?|mucho trabajo|muchos temas|cantidad de (temas|trabajo|contenido)|bastantes temas|mucha materia|mucho contenido|muchos conceptos|extens[oa]s?)\b"),
        ("Ritmo y densidad del curso",
         r"(muy rapido|demasiado rapido|va rapido|un poco rapido|ritmo (muy )?(rapido|acelerado)|acelerad|\b(denso|densos|densa|densas)\b|\bpesad[oa]s?\b|agobi|abrum|(no|nunca) (me )?(da|daba|dio|dan) tiempo (de|para) procesar|se hace (mas|cada) )"),
        ("Explicación del profesor",
         r"(no (le )?(entend\w*|comprend\w*) (nada )?(al|lo que (dijo|explic\w*|dice))( profe\w*)?|(profe\w*|docente)\s+(va|explica|habla|avanza)\s+(muy|demasiado|rapid)|(como|forma en que|manera en que)\s+(explica|ensena)|explicacion\w*\s+(no|poco|confus)|metodologia)"),
        ("Conceptos previos (de semestres pasados)",
         r"(no (me )?(recordaba|acordaba|recuerdo|recordar)|semestres? (pasados?|anteriores?)|se supone que ya|prerrequisito|volver a (coger|repasar)|bases? de)"),
        ("Tiempo y organización",
         r"(no (tuve|tenia|me dio|alcance a tener)\s+(el )?tiempo|falta de tiempo|me falto tiempo|organizarme|mi organizacion|estudiar con anticipacion|no me dio tiempo)"),
        ("Atención y estado personal", r"(atencion|concentr|cansad|\bsueno\b|distrai|distraid|estres|motivacion|\banimo\b|enferm|problemas personales)"),
        ("Horario y logística", r"(horario|madrugar|temprano|\b7 ?am\b|plataforma|internet|\bvirtual\b|asistir|inasistencia|salon|\bsede\b|hora de la clase)"),
    ]
    FACT_RX = [(n, re.compile(r, re.I)) for n, r in FACTORES]
    CONT = 140


    ANTES, DESPUES = 90, 110
    ZONA_ANTES, ZONA_DESPUES, ZONA_ANTES_ANAFORA = 60, 300, 300  # arreglo 1 (11 oct): la zona hacia adelante sube de 140 a 300 caracteres (la respuesta puede seguir en otra frase)
    ANAFORA = re.compile(r"\b(ese|esa|esos|esas|eso|esto|este|esta|estos|estas|aquel|aquello|lo anterior|lo mismo)\b")


    def segmento(x):
        """Ventana alrededor de la palabra de dificultad (la que va entre ** en texto_amplio): el factor debe estar pegado a la dificultad."""
        t = x["texto_amplio"].replace("\n", " ")
        a = t.find("**")
        b = t.find("**", a + 2) if a >= 0 else -1
        if a < 0 or b < 0:
            return x["oracion"].replace("\n", " ")
        seg = t[max(0, a - ANTES):b + 2 + DESPUES].replace("**", "")
        return seg


    def factores(x):
        s = norm(segmento(x))
        return [n for n, rx in FACT_RX if rx.search(s)]


    def asignar_v11(x):
        """Misma logica que main() para una mencion suelta (campos: oracion, texto_amplio, r, candidatos, tema, confianza). Devuelve tema_v11, factores y tipo_v11."""
        if x["confianza"] == "no_dificultad":
            return dict(tema_v11=[], factores=[], tipo_v11="no_dificultad")
        f = factores(x)
        seg = norm(segmento(x))
        pos = {c["nombre"]: (c["pos"] - x["r"][0], c["rel"]) for c in x["candidatos"]}
        t_amp = x["texto_amplio"].replace("\n", " ")
        a_, b_ = t_amp.find("**"), t_amp.find("**", t_amp.find("**") + 2)
        anafora = a_ >= 0 and b_ >= 0 and bool(ANAFORA.search(norm(t_amp[b_ + 2:b_ + 2 + 45])))
        zona_antes = ZONA_ANTES_ANAFORA if anafora else ZONA_ANTES
        en_zona = [t for t in x["tema"] if t in pos and ((pos[t][1] == "despues" and 0 <= pos[t][0] <= ZONA_DESPUES) or (pos[t][1] == "antes" and 0 < -pos[t][0] <= zona_antes))]
        contenido = [t for t in x["tema"] if norm(t) in seg]
        if f:
            return dict(tema_v11=f + [t for t in dict.fromkeys(contenido + en_zona) if t not in f], factores=f, tipo_v11="factor")
        if en_zona:
            return dict(tema_v11=en_zona, factores=[], tipo_v11=x["confianza"])
        return dict(tema_v11=[], factores=[], tipo_v11="sin_tema")


    def main():
        fin = json.load(open(T + r"\temas_curso\temas_final_menciones_v10.json", encoding="utf-8"))
        out, cnt = [], {}
        for x in fin:
            y = dict(x)
            if x["confianza"] == "no_dificultad":
                y.update(tema_v11=[], factores=[], tipo_v11="no_dificultad")
            else:
                f = factores(x)
                seg = norm(segmento(x))
                # zona de respuesta: el tema de contenido solo vale si el estudiante lo nombra pegado a la dificultad
                # (hasta ZONA_DESPUES caracteres despues, o ZONA_ANTES antes). Si dice solo "se me dificulto" sin nada cerca, no hay tema.
                pos = {c["nombre"]: (c["pos"] - x["r"][0], c["rel"]) for c in x["candidatos"]}
                # arreglo 2: si la dificultad se dice con un demostrativo ("se me dificulto aprender ese metodo"), el tema es lo que se acaba
                # de nombrar antes: la zona hacia atras sube a ZONA_ANTES_ANAFORA
                t_amp = x["texto_amplio"].replace("\n", " ")
                a_, b_ = t_amp.find("**"), t_amp.find("**", t_amp.find("**") + 2)
                anafora = a_ >= 0 and b_ >= 0 and bool(ANAFORA.search(norm(t_amp[b_ + 2:b_ + 2 + 45])))
                zona_antes = ZONA_ANTES_ANAFORA if anafora else ZONA_ANTES
                en_zona = [t for t in x["tema"] if t in pos and ((pos[t][1] == "despues" and 0 <= pos[t][0] <= ZONA_DESPUES) or (pos[t][1] == "antes" and 0 < -pos[t][0] <= zona_antes))]
                contenido = [t for t in x["tema"] if norm(t) in seg]
                if f:
                    y.update(tema_v11=f + [t for t in dict.fromkeys(contenido + en_zona) if t not in f], factores=f, tipo_v11="factor")
                elif en_zona:
                    y.update(tema_v11=en_zona, factores=[], tipo_v11=x["confianza"])
                else:
                    y.update(tema_v11=[], factores=[], tipo_v11="sin_tema")
            cnt[y["tipo_v11"]] = cnt.get(y["tipo_v11"], 0) + 1
            out.append(y)
        json.dump(out, open(T + r"\temas_curso\temas_final_menciones_v11.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("tipos v11:", cnt, "| total", len(out))
        por = {}
        for y in out:
            for f in y["factores"]:
                por[f] = por.get(f, 0) + 1
        print("factores:", por)

        base = json.load(open(T + r"\absa_dashboard_CARPETA_DATOS_v10.json", encoding="utf-8"))
        idx = {(y["curso"], y["c"], y["s"], y["r"][0]): y for y in out}
        CURSOS = _modulo("procesar_absa").CURSOS
        for g, v in base.items():
            curso = next(c for c in CURSOS if c.lower() == g)
            for m in v["menciones"]:
                if m["d"] != "DIFICULTAD":
                    continue
                y = idx.get((curso, m["c"], m["s"], m["r"][0]))
                if y is None:
                    continue
                m["t"] = y["tema_v11"]
                m["q"] = y["tipo_v11"]
            v["tema_metodo"] = "tema v11: vocabulario del curso + selector LLM (contenido) y factores generales por reglas (evaluaciones, carga, ritmo, profesor, conceptos previos, tiempo, atencion, horario)"

            def clave(t):
                return " ".join(w[:-2] if w.endswith("es") and len(w) > 5 else w[:-1] if w.endswith("s") and len(w) > 3 else w for w in t.lower().split())

            acc = {}
            for m in v["menciones"]:
                if m["d"] != "DIFICULTAD" or m["q"] in ("no_dificultad", "sin_tema"):
                    continue
                for t in m["t"]:
                    a = acc.setdefault(clave(t), {"nombres": {}, "ests": set(), "auds": set()})
                    a["nombres"][t] = a["nombres"].get(t, 0) + 1
                    a["ests"].add(str(m["c"]))
                    a["auds"].add(m["k"])
            v["ranking_temas_todos"] = sorted(({"tema": max(a["nombres"], key=a["nombres"].get), "estudiantes": len(a["ests"]), "menciones": len(a["auds"])} for a in acc.values()),
                                              key=lambda r: (-r["estudiantes"], -r["menciones"], r["tema"]))
            v["ranking_temas"] = v["ranking_temas_todos"]
            print(g, "top:", [(r["tema"][:28], r["estudiantes"]) for r in v["ranking_temas_todos"][:6]])
        json.dump(base, open(T + r"\absa_dashboard_CARPETA_DATOS_v11.json", "w", encoding="utf-8"), ensure_ascii=False)


    if True:
        import sys

        sys.path.insert(0, r"RUTA_PROYECTO\pipeline")
        main()



def paso_10_rescate():
    r"""Paso: script «tema_rescate_extractivo».

    Tema v11 + RESCATE EXTRACTIVO. Politica de combinacion (no puede romper lo que ya funcionaba):
      1. v11 da tema o factor      -> se conserva (y si el extractivo da una frase especifica, se guarda como detalle);
      2. v11 se abstiene (sin_tema) -> entra el extractivo si da una frase especifica (verificada contra el texto, no generica);
      3. v11 dice no_dificultad     -> se conserva.
    Corre el extractivo solo sobre las menciones de 2026-II que v11 deja sin tema (y, para el detalle, no sobre las demas). Resumible.
    Salidas: resultados\temas_curso\rescate_extractivo_2026II.jsonl, temas_final_menciones_v11r.json y absa_dashboard_CARPETA_DATOS_v11r.json (mismo esquema que v11).
    """
    # -*- coding: utf-8 -*-
    import json
    import os
    import sys

    TE = _modulo("tema_extractivo")

    T = r"RUTA_PROYECTO\resultados" + "\\"
    SAL = T + r"temas_curso\rescate_extractivo_2026II.jsonl"
    fin = json.load(open(T + r"temas_curso\temas_final_menciones_v11.json", encoding="utf-8"))
    key = lambda x: "|".join([x["curso"], str(x["c"]), x["s"], str(x["r"][0])])
    hechos = {}
    if os.path.exists(SAL):
        for l in open(SAL, encoding="utf-8"):
            if l.strip():
                d = json.loads(l)
                hechos[d["k"]] = d
    pend = [x for x in fin if x["tipo_v11"] == "sin_tema" and key(x) not in hechos]
    print("abstenciones:", sum(1 for x in fin if x["tipo_v11"] == "sin_tema"), "| pendientes:", len(pend), flush=True)
    with open(SAL, "a", encoding="utf-8") as f:
        for n, x in enumerate(pend, 1):
            e = TE.extraer(x["texto_amplio"])
            d = {"k": key(x), "causa": e["causa"], "es_dificultad": e["es_dificultad"]}
            hechos[d["k"]] = d
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
            f.flush()
            if n % 10 == 0:
                print(n, "/", len(pend), flush=True)

    out, cnt = [], {}
    for x in fin:
        y = dict(x)
        h = hechos.get(key(x))
        if x["tipo_v11"] == "sin_tema" and h is not None and h["causa"] and h["es_dificultad"]:
            y.update(tema_v11=[h["causa"]], tipo_v11="rescate_extractivo")
        elif x["tipo_v11"] == "sin_tema" and h is not None and h["es_dificultad"] is False:
            y.update(tema_v11=[], tipo_v11="no_dificultad_extractivo")  # el extractivo dice que no es dificultad: se deja sin tema, marcado
        cnt[y["tipo_v11"]] = cnt.get(y["tipo_v11"], 0) + 1
        out.append(y)
    json.dump(out, open(T + r"temas_curso\temas_final_menciones_v11r.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("tipos v11r:", cnt, flush=True)



def paso_11_unir_obvias():
    r"""Paso: script «unir_obvias_v11r».

    Une SOLO las frases rescatadas que son obviamente lo mismo que algo que ya existe, y deja libres las demas:
      1. la frase dispara las reglas de uno de los 8 factores ("el quiz" -> Evaluaciones; "el horario" -> Horario y logistica);
      2. la frase contiene TODAS las palabras (raiz de 5 letras) de un termino del vocabulario del curso ("el metodo de Newton" -> newton);
      3. dos frases iguales tras quitar articulos se cuentan como una (se conserva la forma mas repetida).
    Sin embeddings: regla determinista de alta precision. Actualiza temas_final_menciones_v11r.json (campo tema_v11 de las rescatadas; guarda la frase original en
    'frase_original') y muestra las uniones por pantalla.
    """
    # -*- coding: utf-8 -*-
    import collections
    import json
    import re
    import sys

    V11 = _modulo("tema_factores_v11")

    T = r"RUTA_PROYECTO\resultados\temas_curso" + "\\"
    fin = json.load(open(T + "temas_final_menciones_v11r.json", encoding="utf-8"))
    ART = re.compile(r"^(el|la|los|las|un|una|unos|unas|lo|de|del)\s+", re.I)


    def limpiar(f):
        f = f.strip().lower()
        for _ in range(2):
            f = ART.sub("", f)
        return V11.norm(f)


    def _tallo(w):
        if w.endswith("es") and len(w) > 6:
            return w[:-2]
        if w.endswith("s") and len(w) > 3:
            return w[:-1]
        return w


    def raices(s):
        """Palabras completas sin plural (no raiz de 5 letras: 'directores' no debe unirse con 'direccion' ni 'varianza' con 'variables')."""
        return {_tallo(w) for w in re.findall(r"\w+", V11.norm(s)) if len(w) > 3}


    voc = {}
    uniones = collections.defaultdict(list)
    for x in fin:
        c = x["curso"]
        if c not in voc:
            voc[c] = [v["nombre"] for v in json.load(open(T + f"vocabulario_auto_{c}.json", encoding="utf-8"))]
        if x["tipo_v11"] != "rescate_extractivo":
            continue
        fr = x.get("frase_original") or x["tema_v11"][0]
        x["frase_original"] = fr
        nuevo, motivo = fr, None
        f = [n for n, rx in V11.FACT_RX if rx.search(V11.norm(fr))]
        if f:
            nuevo, motivo = f[0], "factor"
        else:
            rf = raices(fr)
            cand = [t for t in voc[c] if raices(t) and raices(t) <= rf]
            if cand:
                nuevo, motivo = max(cand, key=lambda t: len(raices(t))), "vocabulario"
        x["tema_v11"] = [nuevo]
        if motivo:
            uniones[motivo].append((c, fr, nuevo))
    # frases iguales -> la forma mas repetida
    por_clave = collections.defaultdict(collections.Counter)
    for x in fin:
        if x["tipo_v11"] == "rescate_extractivo" and x["tema_v11"][0] == x["frase_original"]:
            por_clave[(x["curso"], limpiar(x["frase_original"]))][x["frase_original"]] += 1
    for x in fin:
        if x["tipo_v11"] == "rescate_extractivo" and x["tema_v11"][0] == x["frase_original"]:
            k = (x["curso"], limpiar(x["frase_original"]))
            mejor = por_clave[k].most_common(1)[0][0]
            if mejor != x["frase_original"]:
                uniones["iguales"].append((x["curso"], x["frase_original"], mejor))
            x["tema_v11"] = [mejor]
    json.dump(fin, open(T + "temas_final_menciones_v11r.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    resc = [x for x in fin if x["tipo_v11"] == "rescate_extractivo"]
    print("rescatadas:", len(resc), "| unidas por factor:", len(uniones["factor"]), "| por vocabulario:", len(uniones["vocabulario"]), "| frases iguales:", len(uniones["iguales"]),
          "| quedan libres (frase propia):", sum(1 for x in resc if x["tema_v11"][0] == x["frase_original"] and not any(x["frase_original"] == u[1] for u in uniones["iguales"])))
    for m in ("factor", "vocabulario", "iguales"):
        print("\n==", m)
        for c, a, b in uniones[m]:
            print(f"  [{c}] «{a}» -> {b}")



def paso_12_dashboard_tema():
    r"""Paso: script «generar_dashboard_v11r».

    Genera resultados\absa_dashboard_CARPETA_DATOS_v11r.json (tema final = v11 + rescate extractivo) con el mismo esquema que v10/v11 (el dashboard cuenta m.t).
    No sube nada a Drive ni toca el dashboard. Las frases rescatadas aparecen como temas (una por mencion); el ranking las cuenta por estudiante igual que a los demas.
    """
    # -*- coding: utf-8 -*-
    import json
    import re
    import sys
    import unicodedata

    CURSOS = _modulo("procesar_absa").CURSOS
    V11 = _modulo("tema_factores_v11")
    RF = _modulo("reglas_funciones")
    R6 = _modulo("reglas_v6")
    EX = _modulo("tema_extractivo")

    FACTORES = {n for n, _ in V11.FACT_RX}

    T = r"RUTA_PROYECTO\resultados" + "\\"
    out = json.load(open(T + r"temas_curso\temas_final_menciones_v11r.json", encoding="utf-8"))
    base = json.load(open(T + r"absa_dashboard_CARPETA_DATOS_v10.json", encoding="utf-8"))
    idx = {(y["curso"], y["c"], y["s"], y["r"][0]): y for y in out}


    def clave(t):
        return " ".join(w[:-2] if w.endswith("es") and len(w) > 5 else w[:-1] if w.endswith("s") and len(w) > 3 else w for w in t.lower().split())


    STOP = {"de", "la", "el", "en", "con", "para", "los", "las", "una", "del", "que", "como", "por", "mas", "tal", "vez", "sobre", "esta", "este", "esa", "ese", "sus", "muy", "bien"}
    FRX = dict(V11.FACT_RX)
    # patrones que activan D+ en el panel: reglas v5 (fuerte y debil) mas los parches de reglas_v6 ("no me quedo claro", "no se entiende", "cuesta mucho"...)
    PATRONES_DIF = RF.D_PERSONAL + RF.D_REVISAR + [R6.NO_CLARO.pattern, R6.D_EXTRA.pattern]
    RETRANS, ORAC = {}, {}
    for _c in CURSOS:
        _p = T + rf"transcripciones_CARPETA_DATOS\{_c}.jsonl"
        for _l in open(_p, encoding="utf-8"):
            if _l.strip() and '"retranscrito"' in _l:
                RETRANS.setdefault(_c, []).append(json.loads(_l))
    for _l in open(T + r"panel_preguntas\oraciones_etiquetadas_v9.jsonl", encoding="utf-8"):
        _a = json.loads(_l)
        if any(_a["archivo"] == r_["archivo"] for rs in RETRANS.values() for r_ in rs):
            ORAC[_a["archivo"]] = _a["oraciones"]
    EXPR_DIF = re.compile(r"complic|dificil|dificult|\bclar[oa]\b|preocup|la verdad|\bcuest|\bcost|pesad|complej|confund|perdid")


    def nmap(s):
        """Normaliza sin cambiar la longitud (minusculas, sin tildes) para que las posiciones valgan sobre el texto original."""
        out = []
        for ch in s:
            d = unicodedata.normalize("NFD", ch.lower())
            out.append(d[0] if d else ch.lower())
        return "".join(out)


    def spans_hl(texto, m, ventana=300):
        """Posiciones [a, b, tipo] (t=tema del curso, f=causa general, p=frase) cerca de la palabra de dificultad, para resaltar en la cita."""
        n = nmap(texto)
        lo, hi = max(0, m["r"][0] - ventana), min(len(texto), m["r"][1] + ventana)
        res = []
        for t, k in zip(m["t"], m["tt"]):
            if k == "factor" and t in FRX:
                for x in FRX[t].finditer(n, lo, hi):
                    res.append([x.start(), x.end(), "f"])
                continue
            nt = nmap(t).strip()
            i = n.find(nt, lo, hi) if k == "frase" else -1
            if i >= 0:
                res.append([i, i + len(nt), "p"])
                continue
            tipo = "p" if k == "frase" else "t"
            for w in nt.split():
                if len(w) < 4 or w in STOP:
                    continue
                for x in re.finditer(r"\b" + re.escape(w) + r"\w*", n[lo:hi]):
                    res.append([lo + x.start(), lo + x.end(), tipo])
        res.sort(key=lambda s: (s[0], -(s[1] - s[0])))
        return res


    for g, v in base.items():
        curso = next(c for c in CURSOS if c.lower() == g)
        for m in v["menciones"]:
            if m["d"] != "DIFICULTAD":
                continue
            y = idx.get((curso, m["c"], m["s"], m["r"][0]))
            if y is None:
                continue
            m["t"] = y["tema_v11"]
            m["q"] = y["tipo_v11"]
            # tipo de cada elemento de m.t para colorear las etiquetas: causa general / frase libre del estudiante / tema del curso
            m["tt"] = ["factor" if t in FACTORES else ("frase" if y["tipo_v11"] == "rescate_extractivo" and t == y.get("frase_original") else "tema") for t in m["t"]]
        # Audios re-transcritos (retranscribir_fallidos_CARPETA_DATOS.py: webm con marcas de tiempo danadas que salian como
        # "Subtitulado por Jnkoil"). Se reemplaza su transcripcion y sus menciones salen de las oraciones D+ del panel v9 re-etiquetado. El tema
        # sigue la politica final sin el selector de vocabulario (no se recalcula el vocabulario del curso por 3 audios): factores por reglas y,
        # si no hay, el rescate extractivo del LLM local. Son pocas menciones; quedan marcadas con "retranscrito".
        for r_ in RETRANS.get(curso, []):
            k = f'{r_["cedula"]}|{r_["fecha_sesion"]}'
            tx = r_["texto"]
            v["transcripciones"][k] = tx
            v["menciones"] = [m for m in v["menciones"] if m["k"] != k]
            n = nmap(tx)
            for o in ORAC.get(r_["archivo"], []):
                if o["P2_tipo"] != "D+":
                    continue
                i0 = n.find(nmap(o["oracion"])[:40])
                if i0 < 0:
                    continue
                seg = n[i0:i0 + len(o["oracion"])]
                hall = [(x.start(), x.end()) for p in PATRONES_DIF for x in [re.search(p, seg)] if x]
                a, b = (min(hall) if hall else (0, 0))
                a, b = i0 + a, i0 + b
                while b < len(tx) and tx[b].isalpha():
                    b += 1
                x = {"oracion": o["oracion"], "texto_amplio": tx[:a] + "**" + tx[a:b] + "**" + tx[b:], "r": [a, b], "candidatos": [], "tema": [], "confianza": "probable"}
                y = V11.asignar_v11(x)
                t_, q_ = y["tema_v11"], y["tipo_v11"]
                if q_ == "sin_tema":
                    e = EX.extraer(x["texto_amplio"])
                    if e["causa"] and e["es_dificultad"]:
                        t_, q_ = [e["causa"]], "rescate_extractivo"
                    elif e["es_dificultad"] is False:
                        q_ = "no_dificultad_extractivo"
                v["menciones"].append({"c": str(r_["cedula"]), "s": r_["fecha_sesion"], "d": "DIFICULTAD", "e": "regla D+ (expresión exacta)", "t": t_, "k": k, "r": [a, b],
                                       "t_llm": [], "q": q_, "t_extra": [], "retranscrito": True,
                                       "tt": ["factor" if t in FACTORES else ("frase" if q_ == "rescate_extractivo" else "tema") for t in t_]})
                print("  retranscrito", curso, r_["fecha_sesion"], "->", q_, t_, "|", tx[a:b])
        # Regla fija "dificultó fue X": si el estudiante nombra lo que le costó justo después de la palabra de
        # dificultad ("lo que más me dificultó fue las demostraciones") y eso no es un factor general, X reemplaza a los factores de esa mención.
        for m in v["menciones"]:
            if m["d"] != "DIFICULTAD" or "factor" not in (m.get("tt") or []):
                continue
            tx = v["transcripciones"].get(m["k"], "")
            n = nmap(tx)
            r0 = m["r"][0]
            mo = re.match(r"dificult\w*\s+(?:mucho\s+|mas\s+)?(?:fue|fueron|es|son|ha sido|han sido)\s+([^,.;?!]{3,90})", n[r0:r0 + 200])
            if not mo:
                continue
            x = tx[r0 + mo.start(1): r0 + mo.end(1)].strip()
            x = " ".join(x.split()[:10])
            nx = nmap(x)
            if EX.es_generica(EX.norm(x)) or any(rx.search(nx) for rx in FRX.values()):
                continue
            m["t"] = [x] + [t for t, k in zip(m["t"], m["tt"]) if k != "factor"]
            m["tt"] = ["frase"] + [k for k in m["tt"] if k != "factor"]
            m["q"] = "frase_directa"
            m["regla_fue"] = True
        # Filtro de frases rescatadas que repiten la expresión de dificultad y no nombran lo que le costó (auditoría de errores):
        # "no me quedó tan claro", "me preocupa un poco mucho", "salía un poco complicado". La frase se quita; sin nada más, queda sin tema.
        for m in v["menciones"]:
            if m["d"] != "DIFICULTAD" or m.get("q") != "rescate_extractivo" or "frase" not in (m.get("tt") or []):
                continue
            # si la frase trae "dificultó fue X" dentro, se conserva solo X ("el punto que más se les dificultó fue el de demostrar" -> "el de demostrar")
            m["t"] = [(t[re.search(r"dificult\w*\s+(?:fue|fueron|es|son)\s+", nmap(t)).end():] if k == "frase" and re.search(r"dificult\w*\s+(?:fue|fueron|es|son)\s+\S", nmap(t)) else t)
                      for t, k in zip(m["t"], m["tt"])]
            quedan = [(t, k) for t, k in zip(m["t"], m["tt"]) if not (k == "frase" and EXPR_DIF.search(nmap(t)))]
            if len(quedan) == len(m["t"]):
                continue
            m["frase_descartada"] = [t for t, k in zip(m["t"], m["tt"]) if k == "frase"]
            m["t"], m["tt"] = [t for t, _ in quedan], [k for _, k in quedan]
            if not m["t"]:
                m["q"] = "sin_tema"
        # Marca exacta de la dificultad: cuando la señal no es una palabra del léxico (m["e"] == "regla v8"), la marca original eran
        # los primeros 60 caracteres de la oración. Se busca la expresión de las reglas D+ (D_PERSONAL / D_REVISAR) que la activó.
        for m in v["menciones"]:
            if m["d"] != "DIFICULTAD" or m.get("e") != "regla v8":
                continue
            tx = v["transcripciones"].get(m["k"], "")
            n = nmap(tx)
            base_i = m["r"][0]
            fin = re.search(r"[.?!](\s|$)", n[base_i:])
            fin_i = base_i + fin.end() if fin else len(n)
            hall = [(x.start(), x.end()) for p in PATRONES_DIF for x in [re.search(p, n[base_i:fin_i])] if x]
            if hall:
                a, b = min(hall)
                while base_i + b < len(tx) and tx[base_i + b].isalpha():  # completar la palabra (el patrón puede cortar la raíz)
                    b += 1
                m["r"] = [base_i + a, base_i + b]
                m["e"] = "regla D+ (expresión exacta)"
            else:
                m["r"] = [base_i, base_i]
        for m in v["menciones"]:
            if m.get("tt"):
                m["hl"] = spans_hl(v["transcripciones"].get(m["k"], ""), m)
        v["tema_metodo"] = ("tema final: vocabulario del curso + selector LLM (contenido), factores generales por reglas, y rescate extractivo (el LLM local copia del texto la frase "
                            "con que el estudiante nombra lo que le costo, verificada contra el texto) cuando no hay tema ni factor")
        acc = {}
        for m in v["menciones"]:
            if m["d"] != "DIFICULTAD" or m["q"] in ("no_dificultad", "sin_tema", "no_dificultad_extractivo"):
                continue
            for t in m["t"]:
                a = acc.setdefault(clave(t), {"nombres": {}, "ests": set(), "auds": set()})
                a["nombres"][t] = a["nombres"].get(t, 0) + 1
                a["ests"].add(str(m["c"]))
                a["auds"].add(m["k"])
        v["ranking_temas_todos"] = sorted(({"tema": max(a["nombres"], key=a["nombres"].get), "estudiantes": len(a["ests"]), "menciones": len(a["auds"])} for a in acc.values()),
                                          key=lambda r: (-r["estudiantes"], -r["menciones"], r["tema"]))
        v["ranking_temas"] = v["ranking_temas_todos"]
        print(g, "| con tema/factor/rescate:", sum(1 for m in v["menciones"] if m["d"] == "DIFICULTAD" and m["t"]), "| top:", [(r["tema"][:26], r["estudiantes"]) for r in v["ranking_temas_todos"][:5]])
    json.dump(base, open(T + r"absa_dashboard_CARPETA_DATOS_v11r.json", "w", encoding="utf-8"), ensure_ascii=False)
    print("listo")



