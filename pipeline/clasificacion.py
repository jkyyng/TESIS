# -*- coding: utf-8 -*-
"""Pasos 3 y 4 de Foné: oraciones, reglas léxicas con negación, verificador de lenguaje y continuidad.

Archivo generado a partir de los scripts del flujo original sin cambiar su lógica: cada paso es una
función ``paso_NN_*`` y los módulos de apoyo se cargan bajo demanda con ``_modulo()`` y solo conservan
las definiciones que algún paso usa. Las marcas de ruta y de carpeta de datos que traen sus rutas las
reemplaza ``fone_pipeline.py`` al preparar la copia de ejecución.
"""
import sys
from types import SimpleNamespace

_BIBLIOTECAS = {}
_CACHE = {}


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
    raise ImportError(nombre)



@_biblioteca("construir_panel_preguntas_v9")
def _cargar_construir_panel_preguntas_v9():
    """Módulo de apoyo «construir_panel_preguntas_v9»: solo las definiciones que usa algún paso."""
    import json

    import re

    from collections import Counter, defaultdict

    D = r"RUTA_PROYECTO\resultados\panel_preguntas"

    CONSIGNA = re.compile(r"(que|qué)\s+(se\s+me|se\s+te|aprend)|c[oó]mo\s+va\s+el\s+ritmo|\bhas\s+aprendido|\bse\s+te\s+dificult", re.I)

    def es_consigna(o):
        """Ajuste post hoc (3.129): el estudiante repite en voz alta la pregunta ("¿Qué se me dificultó esta
    semana?"). Es el inicio de la respuesta, no una respuesta: se excluye de P1, P2 y P3."""
        return "?" in o and bool(CONSIGNA.search(o)) and len(o.split()) <= 12

    CAP = {2: 3}  # máx. oraciones que se atribuyen a P2 tras su consigna (elegido a mano, sin validar)

    return {k: v for k, v in locals().items() if not k.startswith('__')}


@_biblioteca("lexico_matching")
def _cargar_lexico_matching():
    """Módulo de apoyo «lexico_matching»: solo las definiciones que usa algún paso."""
    import re

    import unicodedata

    DUDAS = [
        "no se", "nose", "no sab*", "no recuerd*", "no record*", "no me acuerdo",
        "no me acord*", "no comprendi", "no comprend*", "no capte", "no capt*",
        "no entendi", "no entend*", "no entiend*", "no logre entender", "no logro entender",
        "no logr* entender",
        # Pronombre de objeto insertado entre "no" y el verbo (ver chat/
        # documentacion.md): "no lo entendi"/"no la comprendi" etc. son
        # construccion natural comunisima que el bigrama "no entend*" no cubre
        # porque exige tokens consecutivos -- 20 ocurrencias reales confirmadas
        # en el corpus completo al agregar esto.
        "no lo entend*", "no la entend*", "no los entend*", "no las entend*",
        "no lo comprend*", "no la comprend*", "no los comprend*", "no las comprend*",
        "creo", "creo que", "creia", "creiamos",
        "pienso que", "pensaba que", "supongo", "supon*", "imagino", "imagina",
        "imaginan", "imaginas", "imaginamos", "imaginaba", "imaginabamos", "imaginate",
        "imaginese", "imaginar", "imaginado", "imaginandome", "imaginarmela",
        "imaginarmelo", "imaginarselo",
        "considero", "considero que", "olvid*", "me parece", "me parece que", "nos parece", "tal vez", "talvez",
        "quizas", "quiza", "posiblemente", "puede ser", "puede que",
        "no estoy seguro", "no estoy segura", "no estaba seguro",
        "no estaba segura", "no estamos seguros", "mas o menos", "algo asi",
        "la verdad no se", "honestamente no se", "en realidad no se",
    ]

    DIFICULTAD = [
        "dificil*", "dificult*", "difisil", "complic*", "complej*", "confund*",
        "confus*", "se me complica", "no le entiendo bien al tema",
        "cuesta entender", "me cuesta", "se me cuesta",
        "pesad*", "abrumador*", "me cost*", "nos cost*", "le cost*",
        "me siento perdid*", "estoy perdid*",
        "me ha cost*", "me esta cost*", "nos ha cost*", "le ha cost*",
        "tan perdid*", "poco perdid*",
    ]

    COMPRENSION = [
        "entend* perfectamente", "comprend* perfectamente",
        "entend* muy bien", "entiend* muy bien",
        "entend* todo",
        "qued* muy claro", "me qued* claro", "me qued* muy claro",
        "tengo claro", "tengo muy claro", "lo tengo claro",
        "facilit*",
        "claramente", "definitivamente", "obviamente", "obvio",
        "por supuesto", "claro que si", "sin duda",
    ]

    ENTRADAS_CLARAS_DUDAS = {"no entendi", "tal vez"}

    ENTRADAS_CLARAS_DIFICULTAD = {"dificil*", "complic*", "dificult*", "pesad*", "me cuesta"}

    ENTRADAS_CLARAS_COMPRENSION = {"entend* perfectamente", "entend* todo", "facilit*"}

    ENTRADAS_CLARAS_POR_DICCIONARIO = {
        "DUDAS": ENTRADAS_CLARAS_DUDAS,
        "DIFICULTAD": ENTRADAS_CLARAS_DIFICULTAD,
        "COMPRENSION": ENTRADAS_CLARAS_COMPRENSION,
    }

    NEGADORES = {"no", "nunca", "jamas", "tampoco", "ni", "sin", "nada", "menos"}

    CONECTORES_CORTE = {"pero", "sino", "aunque"}

    VENTANA_MAX = 8

    PUNTUACION_CORTE = ",.;:"

    VENTANA_MAX_ADELANTE = 5

    PUNTUACION_CORTE_ADELANTE = ".;:"

    def normalizar(palabra):
        t = palabra.lower()
        t = unicodedata.normalize("NFD", t)
        return "".join(c for c in t if unicodedata.category(c) != "Mn")

    def es_negador(tok_norm):
        return tok_norm in NEGADORES or tok_norm.startswith("ningun")

    def tokenizar_con_posicion(texto):
        tokens = []
        for m in re.finditer(r"[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ]+", texto):
            tokens.append({"raw": m.group(0), "norm": normalizar(m.group(0)),
                            "start": m.start(), "end": m.end()})
        return tokens

    def _negado(tokens, texto, i):
        """Camina hacia atras desde i-1 buscando un negador, deteniendose en el
    primer corte de clausula (puntuacion fuerte o conector adversativo).
    El corte se revisa ANTES de considerar cada token candidato, mirando el
    hueco entre ese token y el siguiente (mas cercano al match) -- incluyendo
    el hueco justo antes del match mismo (entre tokens[i-1] y tokens[i]),
    que es el caso mas comun de clausula vecina separada por coma."""
        k = i - 1
        pasos = 0
        while k >= 0 and pasos < VENTANA_MAX:
            entre = texto[tokens[k]["end"]:tokens[k + 1]["start"]]
            if any(p in entre for p in PUNTUACION_CORTE):
                return False
            if tokens[k]["norm"] in CONECTORES_CORTE:
                return False
            if es_negador(tokens[k]["norm"]):
                return True
            k -= 1
            pasos += 1
        return False

    def _negado_adelante(tokens, texto, i, m, entrada):
        """Camina hacia adelante desde el final del match buscando una
    autocorreccion inmediata ("dificulto... nada"). Excluye el modismo "nada
    menos que" (intensificador, no negacion). Tambien se excluye cuando la
    propia ENTRADA del diccionario ya empieza en "no" (ej. "no me acuerd*",
    "no entend*") -- ahi un "nada" que sigue REFUERZA la negacion ya presente
    en la entrada ("no me acuerdo de nada" = no recuerdo nada en absoluto),
    no la revierte (bug real encontrado validando Testeo20262: 2/8 purgas
    iniciales eran de este tipo, casos falsos)."""
        if entrada.lstrip().startswith("no ") or entrada in ("no se", "nose"):
            return False
        k = i + m
        pasos = 0
        while k < len(tokens) and pasos < VENTANA_MAX_ADELANTE:
            entre = texto[tokens[k - 1]["end"]:tokens[k]["start"]]
            if any(p in entre for p in PUNTUACION_CORTE_ADELANTE):
                return False
            if tokens[k]["norm"] == "nada":
                siguiente = tokens[k + 1]["norm"] if k + 1 < len(tokens) else ""
                return siguiente != "menos"
            k += 1
            pasos += 1
        return False

    def encontrar_spans(texto, tokens, diccionario, excluir_si_negado):
        """Devuelve lista de dicts {start,end,entrada,cuenta} -- cuenta=False son
    matches que el diccionario encontro pero se excluyeron por negacion (se
    reportan igual, para poder auditar/revalidar)."""
        spans = []
        usados = [False] * len(tokens)
        for entrada in diccionario:
            palabras = entrada.split(" ")
            es_raiz = [p.endswith("*") for p in palabras]
            raices = [p[:-1] if r else p for p, r in zip(palabras, es_raiz)]
            m = len(palabras)
            i = 0
            while i <= len(tokens) - m:
                if usados[i]:
                    i += 1
                    continue
                ok = True
                for j in range(m):
                    t = tokens[i + j]
                    if usados[i + j]:
                        ok = False
                        break
                    cond = t["norm"].startswith(raices[j]) if es_raiz[j] else t["norm"] == raices[j]
                    if not cond:
                        ok = False
                        break
                if not ok:
                    i += 1
                    continue
                # Fix homografo (ver docstring): "no se" (reflexivo, SIN tilde en
                # el texto crudo) no cuenta como duda -- solo cuenta "no se"
                # (epistemico, CON tilde: "se" en el texto original).
                if entrada == "no se" and tokens[i + 1]["raw"].lower() == "se":
                    i += 1
                    continue
                # Fix "olvid*" + audio (ver documentacion.md 3.93): "se me olvido
                # enviar/hacer el audio" es logistica (por que llego tarde la
                # grabacion), no duda de contenido -- patron clarisimo y repetido
                # en el corpus (6/25 en muestra manual). Se excluye si "audio"
                # aparece en los siguientes 5 tokens.
                if entrada == "olvid*":
                    siguientes = [t["norm"] for t in tokens[i + m:i + m + 5]]
                    if "audio" in siguientes:
                        i += 1
                        continue
                cuenta = True
                if excluir_si_negado and (_negado(tokens, texto, i) or _negado_adelante(tokens, texto, i, m, entrada)):
                    cuenta = False
                spans.append({"start": tokens[i]["start"], "end": tokens[i + m - 1]["end"],
                               "entrada": entrada, "cuenta": cuenta})
                for j in range(m):
                    usados[i + j] = True
                i += m
        return spans

    def contar(texto, diccionario, excluir_si_negado):
        tokens = tokenizar_con_posicion(texto)
        spans = encontrar_spans(texto, tokens, diccionario, excluir_si_negado)
        return sum(1 for s in spans if s["cuenta"])

    return {k: v for k, v in locals().items() if not k.startswith('__')}


@_biblioteca("mejora_reglas_base")
def _cargar_mejora_reglas_base():
    """Módulo de apoyo «mejora_reglas_base»: solo las definiciones que usa algún paso."""
    import json

    import sys

    import unicodedata

    import numpy as np

    import pandas as pd

    RUTA = r"RUTA_PROYECTO\resultados\modelo_funciones_oracion\dataset.xlsx"

    DESARROLLO = ("v1", "v2")

    PRUEBA = ("v3", "v4")

    def norm(s):
        return "".join(c for c in unicodedata.normalize("NFD", str(s).lower()) if unicodedata.category(c) != "Mn")

    return {k: v for k, v in locals().items() if not k.startswith('__')}


@_biblioteca("procesar_absa")
def _cargar_procesar_absa():
    """Módulo de apoyo «procesar_absa»: solo las definiciones que usa algún paso."""
    import json

    import os

    import sys

    import time

    import urllib.request

    from collections import defaultdict

    import pandas as pd

    TESIS = r"RUTA_PROYECTO"

    IN_DIR = TESIS + r"\resultados\transcripciones_CARPETA_DATOS"

    OUT_DIR = TESIS + r"\resultados\absa_CARPETA_DATOS"

    LOG_PATH = TESIS + r"\logs\absa_CARPETA_DATOS.log"

    MODELO = "qwen2.5:7b-instruct"

    OLLAMA_URL = "http://localhost:11434/api/generate"

    CURSOS = [c["curso"] for c in json.load(open(r"RUTA_PROYECTO\CARPETA_DATOS\cursos.json", encoding="utf-8"))]

    CEDULA_DEMO_PROFESOR = 654321

    os.makedirs(OUT_DIR, exist_ok=True)

    PROMPT_SISTEMA = """Sos un asistente que analiza una frase donde un estudiante universitario \
expreso dificultad o duda (la palabra marcada va entre **asteriscos**). Hace DOS cosas:

1) TEMA(S): de que tema o temas especificos de la materia habla.
Temas ya vistos en este curso (usalos si alguno calza, para no fragmentar el mismo tema con \
nombres distintos): {lista}

Normalmente la frase nombra UN solo tema. Pero a veces nombra EXPLICITAMENTE dos o mas temas \
distintos en la misma dificultad -- ej. "se me dificulto la estructura de las matrices Y la \
solucion por Jordan y Gauss-Jordan" son DOS temas ("matrices" y "eliminacion gaussiana"), no \
uno. Identifica TODOS los que esten nombrados explicitamente, cada uno como su propio tema \
corto (2-4 palabras), NUNCA la palabra de dificultad misma ni sinonimos de ella (nunca \
"confusion", "dificultad", "complejidad" en vez de EL TEMA). Si no hay ningun tema \
identificable (habla del ritmo del curso en general, de logistica, o es demasiado vago), \
devolve una lista vacia.

IMPORTANTE -- no inventes un tema que no este realmente en el texto: para CADA tema, cita \
literalmente 2-5 palabras SEGUIDAS de la frase (tal como aparecen) que lo respalden \
especificamente A ESE tema. Si no podes citar texto real que respalde un tema, no lo incluyas.

2) VIGENCIA: si la dificultad o duda SIGUE VIGENTE al momento de hablar ("S"), o si el propio \
estudiante indica EXPLICITAMENTE, en la misma frase, que ya se resolvio / ya no es dificil / ya \
lo entendio / concluye que fue mas facil de lo esperado ("N"). No inventes una resolucion que \
no este en el texto -- si no hay indicio explicito, "S" (el default es que sigue vigente). Ver \
el ejemplo varias veces o pedir ayuda NO es una resolucion explicita.
  - "calcular muchas derivadas y era muy largo el segundo punto **creo** que no estuvo tan \
dificil" -> "N" (el estudiante concluye que no fue dificil)
  - "al principio me costo bastante entenderlo, **no entendia** bien las formulas, pero ya \
hice mas ejercicios y ya lo logro" -> "N" ("ya lo logro" es resolucion explicita)
  - "Se me **dificulto** bastante entender las integrales por partes, tuve que ver el ejemplo \
como tres veces." -> "S" (no hay resolucion explicita)
  - "el profesor resolvio una parte del preparcial con cosas que **no entendiamos**. \
Principalmente el teorema del trapecio" -> "S"

Respondé SOLO con un JSON de una linea:
{{"temas": [{{"tema": "nombre del tema", "evidencia": "cita textual corta"}}, ...], "vigente": "S"}}
(temas = lista vacia si no hay tema identificable)

Frase: {contexto}

JSON:"""

    def log(msg):
        linea = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        print(linea, flush=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(linea + "\n")

    def cargar_audios_curso(curso):
        """Audios unicos (dedup por cedula+sesion, el de texto mas largo), sin profesor/demo."""
        roster = pd.read_excel(TESIS + r"\Foné — Estudiantes.xlsx")
        profes = {int(c) for c in roster.loc[roster["Vinculo"].astype(str).str.upper() == "PROFESOR", "Cedula"]}
        profes.add(CEDULA_DEMO_PROFESOR)

        mejores = {}
        n_total = n_prof = n_sin_texto = 0
        with open(os.path.join(IN_DIR, f"{curso}.jsonl"), encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                n_total += 1
                ced = int(d["cedula"])
                if ced in profes:
                    n_prof += 1
                    continue
                if not (d.get("texto") or "").strip():
                    n_sin_texto += 1
                    continue
                clave = (ced, d["fecha_sesion"])
                if clave not in mejores or len(d["texto"]) > len(mejores[clave]["texto"]):
                    mejores[clave] = d
        log(f"[{curso}] {n_total} audios: -{n_prof} profesor/demo, -{n_sin_texto} sin texto, "
            f"-{n_total - n_prof - n_sin_texto - len(mejores)} duplicados -> {len(mejores)} unicos")
        return list(mejores.values())

    return {k: v for k, v in locals().items() if not k.startswith('__')}


@_biblioteca("reetiquetar_panel_v8")
def _cargar_reetiquetar_panel_v8():
    """Módulo de apoyo «reetiquetar_panel_v8»: solo las definiciones que usa algún paso."""
    import json

    import os

    import re

    import sys

    R5 = _modulo("reglas_v6")

    R2 = _modulo("reglas_oracion_v2")

    DIFICULTAD = _modulo("lexico_matching").DIFICULTAD
    contar = _modulo("lexico_matching").contar

    verifica = _modulo("verificador_llm_dplus").verifica

    D = r"RUTA_PROYECTO\resultados\panel_preguntas"

    ENT, SAL = D + r"\oraciones_etiquetadas.jsonl", D + r"\oraciones_etiquetadas_v8.jsonl"

    PRIMERA_DUDAS = re.compile(r"(?<!no )(?<!sin )\b(tengo|tuve|tenia|tenemos|aun tengo|todavia tengo|me quedan|me quedaron|me quedo|me surgen|me surgieron)\b[^.;]{0,25}\bdudas?\b")

    NO_DUDAS = re.compile(r"\bno (tengo|tuve|tenia|hay|hubo|me quedan|me quedaron)\b[^.,;]{0,20}\bdudas?\b|\bsin (ninguna )?dudas?\b|\bninguna duda\b")

    def _n(o):
        return R5.norm(o)

    def asignar(o):
        fuerte = R5.Dplus_fuerte(o)
        amplia = R5.Dplus_amplia(o)
        if (fuerte or amplia) and R5.R(o) and not R5.Dplus_amplia(re.sub(r"\bpreocup\w*", " ", o, flags=re.I)):
            fuerte = amplia = False
        tipo, sen = None, None
        if fuerte:
            tipo, sen = "D+", 2
        elif amplia:
            solo_dudas = not R5.Dplus_amplia(re.sub(r"\bdudas?\b", " ", o, flags=re.I))
            if solo_dudas:
                if PRIMERA_DUDAS.search(_n(o)):
                    tipo, sen = "D+", 1
            elif verifica(o):
                tipo, sen = "D+", 1
        if tipo is None:
            solo_negadas = contar(o, DIFICULTAD, True) == 0 and contar(o, DIFICULTAD, False) > 0
            if R5.N_amplia(o) or solo_negadas or R2.p2_tipo(o) == "D0" or NO_DUDAS.search(_n(o)):
                tipo = "D0"
        return {"P1": bool(R5.A(o)), "P2": tipo is not None, "P2_tipo": tipo, "P2_senales": sen, "P3": bool(R5.R(o))}

    return {k: v for k, v in locals().items() if not k.startswith('__')}


@_biblioteca("reglas_funciones")
def _cargar_reglas_funciones():
    """Módulo de apoyo «reglas_funciones»: solo las definiciones que usa algún paso."""
    import re

    import sys

    import unicodedata

    DIFICULTAD = _modulo("lexico_matching").DIFICULTAD
    contar = _modulo("lexico_matching").contar

    def norm(s):
        s = unicodedata.normalize("NFD", (s or "").lower())
        return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")

    R_CURSO = r"(profe\w*|docente|clase\w*|curso|materia|semestre|temas?|explic\w+|vamos|vamo|vemos)"

    R_VEL = r"(rapid\w*|lent\w*|despacio|apresur\w*|acelerad\w*|aceler\w*|pausad\w*|veloz|velocidad)"

    R_PATRONES = [
        r"\britmo\b",
        r"\bvelocidad\b",
        r"\bapresurad\w*|\bacelerad\w*",
        r"\bva\b.{0,25}\b" + R_VEL,
        r"\b" + R_CURSO + r"\b.{0,40}\b" + R_VEL,
        r"\b" + R_VEL + r"\b.{0,30}\b(clase\w*|curso|profe\w*|docente)\b",
        # 2026-10-08: "al dia" solo cuenta con verbo de estar/ir/poner (antes disparaba con fechas: "al dia viernes 28")
        r"\ba la par\b|\b(?:estar|estamos|estoy|estan|vamos|voy|ir|va|llevo|llevamos|llevar|poner\w*|pongo|puesto|mantener\w*)\b.{0,20}\bal dia\b|\batrasad\w*|\badelantad\w*",
        r"\bvamos (bien|mal|muy bien|bastante bien|tranquil\w*|al dia|a buen)",
    ]

    R_EXCLUIR = r"\bmas rapid[oa]\b(?!.{0,30}\b(clase|curso|profe\w*|docente)\b)"

    def regla_R(t):
        n = norm(t)
        if not any(re.search(p, n) for p in R_PATRONES):
            return False
        # "mas rapido" comparativo de una tecnica, sin referencia al curso: solo cuenta si hay otro indicio
        resto = re.sub(R_EXCLUIR, " ", n)
        return any(re.search(p, resto) for p in R_PATRONES)

    D_PERSONAL = [
        r"\bse me (ha |han |hizo |hace |hacen |esta |estan |puso )?(dificult|complic|cost|hizo (muy |bastante |un poco |algo )?(dificil|complic|pesad))",
        r"\bme (ha |han |esta |estan |fue |resulto |parecio )?(cost|cuesta|dificult|complic|confund)",
        r"\bnos (ha |han |se )?(cost|dificult|complic)",
        r"\bse nos (ha |han )?(dificult|complic|cost)",
        r"\b(estoy|estaba|andaba|ando|quede|queda|queda) (algo |un poco |bastante |muy )?(perdid|confundid|confus)",
        r"\bme (siento|senti|sentia) (algo |un poco |bastante |muy )?(perdid|confundid|abrumad|agobiad)",
        r"\bno (logre|logro|pude|puedo|he podido|consegui) (entender|resolver|hacer|comprender|aprender)",
        r"\bno (lo|la|los|las) (entend|comprend|logr|pude)",
        r"\bno (entendi|comprendi|entiendo|comprendo|entendia)\b",
        r"\bme (equivoque|perdi|trabe|bloquee|enrede)",
        r"\bme (quedo|salio|quedaron) mal",
    ]

    D_REVISAR = [
        r"\bdificil\w*|\bdificult\w*|\bcomplic\w*|\bcomplej\w*|\bpesad\w*|\bduro\b|\bdura\b",
        r"\bestres\w*|\bfrustr\w*|\bagobi\w*|\babrum\w*|\bsobrecarg\w*|\basust\w*|\bansied\w*|\bnervios\w*|\bpreocup\w*",
        r"\bno (alcance|alcanzo|alcanzamos|alcanzaba)\b",
        r"\bme (falta|faltan|faltaron)\b",
        r"\bvacios?\b|\bduda[s]?\b",
        r"\bno (me )?(quedo|queda|quedaron) (claro|clara)",
        r"\bapenas (entend|comprend|salv|pase)",
    ]

    D_NO_DIF = r"\b(dificult|complic|cost)\w*\W+(?:\w+\W+){0,2}nada\b|\bno (se me|me|le|nos) (ha |han |hizo |hace )?(dificult|complic|cost)|ninguna dificultad|no (he )?tenido (ninguna )?dificultad|nada (de )?(dificil|complic)|\bnada\b.{0,15}\bdificult"

    def _con_negacion(t):
        return contar(t, DIFICULTAD, True) > 0  # lexico vigente (incluye negacion hacia atras y adelante)

    def regla_Dplus_fuerte(t):
        n = norm(t)
        if re.search(D_NO_DIF, n):
            return False
        return any(re.search(p, n) for p in D_PERSONAL)

    def regla_Dplus_revisar(t):
        """Marca para revision humana: lexico vigente o indicio debil, no cubierto por la regla fuerte."""
        n = norm(t)
        if regla_Dplus_fuerte(t):
            return False
        if re.search(D_NO_DIF, n):
            return False
        if _con_negacion(t):
            return True
        return any(re.search(p, n) for p in D_REVISAR[1:])

    def regla_Dplus_amplia(t):
        return regla_Dplus_fuerte(t) or regla_Dplus_revisar(t)

    A_VISTO = r"\b(vimos|vemos|veremos|ver |vio|aprend\w+|hicimos|hacemos|trabajamos|estudiamos|repasamos|explico|explicaron|resolvimos|demostramos|calculamos|aplicamos|usamos|utilizamos|dimos|empezamos|comenzamos|tocamos|entendimos|vi que|conocimos|analizamos)\b"

    A_DEFINICION = r"\b(es un|es una|es el|es la|son los|son las|se define|se calcula|se usa|se utiliza|se aplica|se obtiene|se puede|se pueden|se tiene que|sirve|sirven|consiste|significa|quiere decir|se denomina|se llama|permite|permiten|depende|cuando [a-z]+ es|si [a-z]+ es|igual a|entonces)\b"

    A_TERMINOS = (r"matri\w*|vector\w*|determinant\w*|variabl\w*|dato\w*|distribu\w*|\bmedia\b|mediana|\bmoda\b|varianza|desviacion|hipotesis|"
                  r"integral\w*|derivad\w*|limite\w*|\bserie\w*|metodo\w*|algoritm\w*|modelo\w*|regres\w*|correlacion|outlier\w*|ecuacion\w*|"
                  r"sistema\w*|funcion\w*|probabilidad\w*|aproximacion\w*|numeric\w*|binari\w*|\bbits?\b|python|codigo|\bpca\b|cluster\w*|"
                  r"componente\w*|escalar\w*|espacio\w*|dimension\w*|gauss\w*|\blu\b|\bqr\b|cramer|inversa|estadistic\w*|grafic\w*|muestra\w*|"
                  r"poblacion\w*|normal(idad)?\b|imput\w*|nulo\w*|categoric\w*|tabla\w*|plano\w*|recta\w*|curva\w*|area\w*|volumen|punto\w*|"
                  r"propiedad\w*|teorema\w*|formula\w*|operacion\w*|sucesi\w*|convergen\w*|diverg\w*|error\w*|iteracion\w*|raiz|raices|"
                  r"polinom\w*|coeficiente\w*|pivote|fila\w*|columna\w*|rango|eigen\w*|autovalor\w*|ortogonal\w*|proyeccion\w*|kendall|pearson|spearman|"
                  r"chi cuadrado|tendencia central|dispersion|percentil\w*|cuartil\w*|negocio|despliegue|preparacion de datos|evaluacion|fase\w*")

    A_ENTENDIO = r"\b(entendi|comprendi|aprendi|entendimos|logre entender|me quedo claro|quedo claro)\b"

    A_FORMULA = r"\d+\s*(x|por|\*|\+|=)\s*\d+|\b[a-z]\s*(=|igual)\s*[a-z0-9]"

    A_SOLO_META = r"^(bueno |pues |eh |ah |ya |si |no |y |o sea |entonces )*(gracias|hola|adios|listo|ya|nada mas|eso seria todo|seria todo|eso es todo|chao)\b"

    def regla_A(t):
        n = norm(t)
        palabras = len(n.split())
        if palabras < 4 or re.search(A_SOLO_META, n):
            return False
        visto = re.search(A_VISTO, n) is not None
        defin = re.search(A_DEFINICION, n) is not None
        terminos = len(re.findall(A_TERMINOS, n))
        formula = re.search(A_FORMULA, n) is not None
        # oraciones sobre el curso/ritmo/dificultad sin contenido -> no A
        if regla_R(t) or regla_Dplus_amplia(t):
            # oracion sobre ritmo/dificultad: solo cuenta como A si dice explicitamente que se vio/aprendio algo
            return visto or formula or terminos >= 2 or re.search(A_ENTENDIO, n) is not None or (
                re.search(r"\btemas?\b", n) is not None and terminos >= 1)
        return visto or formula or terminos >= 1 or (defin and palabras >= 8) or re.search(A_ENTENDIO, n) is not None

    FUNCIONES = {"A": regla_A, "D+": regla_Dplus_amplia, "D+fuerte": regla_Dplus_fuerte, "R": regla_R}

    return {k: v for k, v in locals().items() if not k.startswith('__')}


@_biblioteca("reglas_oracion_v2")
def _cargar_reglas_oracion_v2():
    """Módulo de apoyo «reglas_oracion_v2»: solo las definiciones que usa algún paso."""
    import re

    import sys

    DIFICULTAD = _modulo("lexico_matching").DIFICULTAD
    contar = _modulo("lexico_matching").contar

    norm = _modulo("mejora_reglas_base").norm

    DIFICULTAD_EXT = [
        # no comprension (antes vivian en el diccionario DUDAS)
        "no entend*", "no entiend*", "no comprend*", "no comprendi", "no le entend*", "no lo entend*", "no la entend*",
        "no capt*", "no me qued* claro", "no me qued* clara", "no me qued* claros",
        # preocupacion / angustia / carga personal
        "me preocup*", "nos preocup*", "estoy preocupad*", "estaba preocupad*", "me asust*", "me frustr*", "frustrad*",
        "agobi*", "estres*", "engorros*", "enredad*", "me enred*", "me trab*",
        # errores de ASR frecuentes de "se me dificulto / resulto dificil"
        "se me ocult*", "se me resulto", "se me dificul*",
        # no logro / falta de dominio
        "no logr*", "no pude", "no he podido", "no me sale", "no me salen", "no me salio", "no me salieron",
        "me fue mal", "no me fue bien", "me fue regular", "me hizo falta", "me falta practic*", "falta de practic*",
        "me qued* dudas", "me qued* la duda", "tengo dudas", "tengo muchas dudas", "aun tengo dudas", "me qued* vacios",
        "me perd*", "me quede perdid*", "dificultad*",
    ]

    D0_RX = re.compile(
        r"no se me (ha )?(dificult|complic|hizo (tan |muy )?(dificil|complicad|pesad)|ocult)|ningun[ao]? (tipo de )?dificultad"
        r"|no (he )?tenido (ninguna |mucha |alguna )?(dificultad|problema)|no tuve (ninguna |mucha |alguna )?(dificultad|problema)"
        r"|no me (ha )?cost|no (fue|era|es|estuvo|esta) (tan |muy |nada )?(dificil|complicad|pesad)"
        r"|nada (se me )?(dificil|complicad)|no se me (ha )?(hecho|presentado) (nada|ninguna|alguna)"
        r"|se me (hizo|ha hecho) (muy |bastante )?facil|se me facilit"
        r"|\b(entendi|entiendo|entendimos|comprendi|comprendo) (todo|bien|perfecto|perfectamente|muy bien)|todo (muy |super )?claro"
        r"|(tengo|queda|quedo) (muy |super |todo )?claro|sin (ninguna |mayor |mucha )?(dificultad|problema)")

    RUIDO_RX = re.compile(r"complejidad|cola pesada|colas pesadas|complejo[s]? (de|que|para) (entender|ver)")

    def lex_neg(o):
        """D+ del nucleo (lexico vigente con filtro de negacion)."""
        return contar(o, DIFICULTAD, True) > 0

    def lex_all(o):
        return contar(o, DIFICULTAD, False) > 0

    def ext_neg(o):
        return contar(o, DIFICULTAD_EXT, True) > 0

    def ext_all(o):
        return contar(o, DIFICULTAD_EXT, False) > 0

    def p2_tipo(o):
        """'D+' (le costo), 'D0' (dice que no le costo) o None. Prioriza recall: cualquier senal activa P2."""
        n = norm(o)
        base_pos = lex_neg(o) or ext_neg(o)
        base_any = lex_all(o) or ext_all(o)
        d0 = bool(D0_RX.search(n))
        if base_pos and not (d0 and not lex_neg(o)):
            return "D+"
        if base_any or d0:
            return "D0"
        return None

    R_FUERTE = re.compile(
        r"\britmo\b|velocidad|a la par|despacio|apresurad|a las carreras|\bde afan\b"
        r"|vamos (bien|bastante bien|muy bien|adelantad|atrasad|al dia|tranquil|a tiempo)|vamos (con )?(mucha )?(prisa|afan)"
        r"|(el curso|la clase|el semestre|el profe|el profesor) (va|esta yendo|esta siendo|avanza|anda) (muy |bastante |un poco |algo )?"
        r"(bien|tranquil|normal|rapid|lent|suave|fluid|acelerad|pesad)"
        r"|muchos temas (en|al|para|por) |mucho(s)? (tema|contenido)s? en (poco|tan poco)|poco tiempo|casi no hay tiempo"
        r"|carga (academica|de trabajo|de informacion)|(mucha|demasiada) (carga|informacion|prisa)|llevadero|nivel del curso"
        r"|dinamica (de la clase|del curso)|flujo de la clase")

    R_DEBIL = re.compile(r"\brapid|\blent[oa]s?\b|\blentitud\b|acelerad")

    R_CONTEXTO = re.compile(r"\b(profe|profesor|clase|clases|curso|explica|explicaba|vamos|vemos|temas|semestre|materia)\b")

    R_METODO = re.compile(r"mas (rapid|lent)[oa]s? (de|que|para|en|y)|(manera|forma|metodo|codigo|analisis|calculo|operaciones?) .{0,25}rapid|rapidamente")

    A_RX = re.compile(
        r"\bvimos\b|\bvi\b|\bvio\b|\bveremos\b|aprend|\bhicimos\b|\bhice\b|\btuvimos\b|\bempezamos\b|\bterminamos\b|\bexplic|\bquiz\b|\bcuis\b"
        r"|\bparcial\b|\bpreparcial\b|\btaller\b|\bejercicio|\btema\b|\btemas\b|\bclase\b|\bclases\b|\bcalcul|\bresolv|\btrabajamos\b|\bestudiamos\b"
        r"|\bmetodo|\bmatriz|\bmatrices\b|\bvector|\bdeterminante|\bdistribucion|\bvariable|\bmodelo\b|\bdatos\b|\bdataset|\bformula|\becuacion"
        r"|\bconcepto|\bdefinicion|\bteorema|\bdemostr|\bpropiedad|\balgoritmo|\bgrafic|\bprobabilidad|\bmedia\b|\bvarianza|\bregresion|\bintegral|\bderivad"
        r"|\bse (puede|pueden|debe|deben|usa|utiliza|calcula|hace|obtiene)\b|\bsirve\b|\bsignifica\b|\bsea\b|\bentonces\b.*\bsi\b|\bpara (poder |que )?(ver|hallar|encontrar|calcular|obtener)")

    O_RX = re.compile(r"\bgracias\b|\bchao\b|\bhasta luego\b|\bsaludo|\bespero que se encuentren|\bgrabando\b|\blisto\b\?|\bno me dejan\b")

    A_FUERTE = re.compile(
        r"\bvimos\b|\bvi\b|\bvio\b|aprend|\bhicimos\b|\bhice\b|\btuvimos\b|\bempezamos\b|\bterminamos\b|\bexplic|\bquiz\b|\bcuis\b"
        r"|\btaller\b|\bejercicios?\b|\btrabajamos\b|\bestudiamos\b|\bresolvimos\b|\bresolv|\bcomparamos\b|\bcalculamos\b|\bpracticamos\b"
        r"|\bse (trata|trato) de\b|\bconsiste\b|\bsirve para\b|\bse utiliza\b|\bse usa\b|\bse calcula\b")

    A_DEBIL = re.compile(
        r"\btema\b|\btemas\b|\bparcial\b|\bpreparcial\b|\bmetodo|\bmatriz|\bmatrices\b|\bvector|\bdeterminante|\bdistribucion|\bvariable|\bmodelo\b"
        r"|\bdatos\b|\bdataset|\bformula|\becuacion|\bconcepto|\bdefinicion|\bteorema|\bdemostr|\bpropiedad|\balgoritmo|\bgrafic|\bprobabilidad"
        r"|\bmedia\b|\bvarianza|\bregresion|\bintegral|\bderivad|\boutliers?\b|\bestadistic|\bhipotesis|\bsistema de ecuaciones")

    return {k: v for k, v in locals().items() if not k.startswith('__')}


@_biblioteca("reglas_v6")
def _cargar_reglas_v6():
    """Módulo de apoyo «reglas_v6»: solo las definiciones que usa algún paso."""
    import re

    import sys

    R5 = _modulo("reglas_funciones")

    norm = _modulo("reglas_funciones").norm

    NO_CLARO = re.compile(r"\bno (me )?(ha |han |haya )?(quedad\w+|queda\w*|qued\w+) (muy |tan |del todo )?clar\w+|\bno se (entiende|entendio|comprende)\b")

    PREOC_NEG = re.compile(r"\bno\b[^,.;]{0,25}\bpreocup\w*")

    FACIL = re.compile(r"(?<!mas )(?<!menos )\b(muy |bastante |super |tan |algo |un poco )?(facil(es|mente)?|sencill[oa]s?)\b")

    NEG_ANTES = re.compile(r"\bno\b(\s+\w+){0,3}\s*$")

    NEG_DIF = re.compile(r"\bno (me parece|me parecio|es|fue|era|estuvo|esta|se me hizo|me resulto|me resulta)\b[^.;]{0,30}\b(complicad\w*|dificil\w*|pesad\w*)\b")

    D_EXTRA = re.compile(r"\b(a veces |ya |nos |me )?cuesta (mucho|bastante|trabajo|un poco|hacer|entender|recordar)\b|\bme (bloque\w+|perjudic\w+|ha perjudicad\w+)\b")

    N_EXTRA = re.compile(r"\b(entendible|muy entendible)\b|\b(he |lo )?(entendido|entendi|entiendo|comprendi|comprendo|logre entender) (todo|completamente|perfectamente|bien)\b|\b(nada|ninguna cosa) (que no (he |haya )?entendido|me quedo sin entender)\b")

    def _sin_preocup_negada(o):
        return PREOC_NEG.sub(" ", norm(o))

    def Dplus_fuerte(o):
        return R5.regla_Dplus_fuerte(_sin_preocup_negada(o)) or bool(NO_CLARO.search(norm(o))) or bool(D_EXTRA.search(norm(o)))

    def Dplus_amplia(o):
        return Dplus_fuerte(o) or R5.regla_Dplus_amplia(_sin_preocup_negada(o))

    def N_amplia(o):
        """El estudiante dice que algo fue facil/sencillo/claro (lectura amplia de N fijada por el autor, 2026-10-08)."""
        n = norm(o)
        if NEG_DIF.search(n) or N_EXTRA.search(n):  # v7: "no me parece (...) complicado"; v8: "entendible", "he entendido todo"
            return True
        for m in FACIL.finditer(n):
            if NEG_ANTES.search(n[: m.start()]):
                continue  # "no fue facil" es dificultad, no N
            return True
        return bool(R5.D_NO_DIF and re.search(R5.D_NO_DIF, n))

    def R(o):
        n = norm(o)
        if not R5.regla_R(o):
            return False
        # v8 (2026-10-09): la exclusion "velocidad como causa de la dificultad" solo vale en oraciones cortas; en las largas (todo el audio en
        # una oracion) tapaba el ritmo real (8 de 11 ritmos no detectados en la prueba de audios viejos tenian dificultad y ritmo juntos).
        if len(n.split()) <= 35 and Dplus_fuerte(o) and not re.search(r"\britmo\b|\bcarga\b|\bmuchos temas\b", n):
            return False
        return True

    A = R5.regla_A

    return {k: v for k, v in locals().items() if not k.startswith('__')}


@_biblioteca("segmentador_llm")
def _cargar_segmentador_llm():
    """Módulo de apoyo «segmentador_llm»: solo las definiciones que usa algún paso."""
    import json

    import re

    import time

    import urllib.request

    MODELO = "qwen2.5:7b-instruct"

    OLLAMA_URL = "http://localhost:11434/api/generate"

    PROMPT = """Un estudiante universitario grabo un audio de un minuto respondiendo, en este orden, tres preguntas:
 P1. ¿Que aprendiste esta semana?
 P2. ¿Que se te dificulto esta semana?
 P3. ¿Como va el ritmo del curso?
A continuacion esta la transcripcion dividida en oraciones numeradas. Indica en que numero de oracion EMPIEZA la respuesta a P2 (empieza a hablar de lo que se le dificulto, lo que le costo o no entendio) y en que numero EMPIEZA la respuesta a P3 (empieza a hablar del ritmo/velocidad/dinamica del curso). Si no responde una de ellas, usa null. Todo lo anterior a P2 es la respuesta a P1. Si el estudiante no sigue ese orden, pon "orden_estandar": false.
Respondé SOLO con un JSON de una linea: {{"inicio_R2": N o null, "inicio_R3": N o null, "orden_estandar": true o false}}

Transcripcion:
{texto}

JSON:"""

    def dividir_oraciones(texto):
        partes = [p.strip() for p in re.split(r"(?<=[.?!])\s+", texto.strip()) if p.strip()]
        return partes

    return {k: v for k, v in locals().items() if not k.startswith('__')}


@_biblioteca("verificador_llm_dplus")
def _cargar_verificador_llm_dplus():
    """Módulo de apoyo «verificador_llm_dplus»: solo las definiciones que usa algún paso."""
    import json

    import os

    import sys

    import urllib.request

    URL = "http://localhost:11434/api/generate"

    CACHE = r"RUTA_PROYECTO\resultados\reglas_oracion\cache_verificador.json"

    PROMPT = """Un estudiante universitario grabo un audio contando su semana de clase. Lee esta oracion de su audio:

\"{o}\"

Pregunta: en esta oracion, el propio estudiante dice que ALGO LE COSTO, NO LO ENTENDIO, SE LE COMPLICA, LE PREOCUPA, LE FUE MAL o LE QUEDARON DUDAS?
Responde NO si: la palabra de dificultad describe contenido tecnico (p. ej. "complejidad", "mal condicionado", "es complejo" como definicion), habla de otras personas o en general ("es dificil" sin decir que a el le costo), dice que NO se le dificulto nada, o la dificultad es de la oracion vecina. Responde NO tambien si solo menciona "dudas" como parte normal de la clase ("el profesor resolvio las dudas", "hacemos preguntas y dudas", "tenemos dudas y las preguntamos") sin decir que el estudiante no entendio algo, o si habla del ritmo del curso sin decir que a el le costo.
Responde SOLO con SI o NO."""

    _cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}

    def verifica(oracion, modelo="qwen2.5:7b-instruct"):
        k = "p2|" + modelo + "|" + oracion  # p2 = prompt revisado 2026-10-08 (dudas generales); las claves viejas ya no aplican
        if k in _cache:
            return _cache[k]
        data = json.dumps({"model": modelo, "prompt": PROMPT.format(o=oracion), "stream": False,
                           "options": {"temperature": 0, "num_predict": 4}}).encode("utf-8")
        req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as r:
            txt = json.loads(r.read())["response"].strip().upper()
        v = txt.startswith("SI") or txt.startswith("SÍ")
        _cache[k] = v
        json.dump(_cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
        return v

    return {k: v for k, v in locals().items() if not k.startswith('__')}


def paso_03_reetiquetar():
    r"""Paso: script «reetiquetar_panel_v9».

    Panel v9 (2026-10-09): MISMAS reglas que v8, pero con una segmentacion corregida. El transcriptor corta el audio en trozos de ~22 s y deja
    "..." en los bordes; la regex de oraciones (. ? !) trata ese "..." como fin de oracion y parte el pensamiento a la mitad ("...lo que mas se
    me dificulto fue como entender ese..." / "esa diferencia de hallar las matrices inversas"). Regla nueva: si una oracion termina en "..." o
    "…" y la siguiente empieza en minuscula (o con "..."), se unen. Lee el texto completo desde las transcripciones y escribe
    oraciones_etiquetadas_v9.jsonl con el mismo esquema que v8.
    """
    # -*- coding: utf-8 -*-
    import json
    import os
    import re
    import sys

    dividir_oraciones = _modulo("segmentador_llm").dividir_oraciones
    cargar_audios_curso = _modulo("procesar_absa").cargar_audios_curso
    CURSOS = _modulo("procesar_absa").CURSOS
    asignar = _modulo("reetiquetar_panel_v8").asignar

    SAL = r"RUTA_PROYECTO\resultados\panel_preguntas\oraciones_etiquetadas_v9.jsonl"
    os.makedirs(os.path.dirname(SAL), exist_ok=True)


    def dividir_v9(texto):
        out = []
        for s in dividir_oraciones(texto):
            if out and re.search(r"(\.\.\.|…)\s*$", out[-1]) and (s[:1].islower() or s.startswith("...") or s.startswith("…")):
                out[-1] = out[-1].rstrip() + " " + s.lstrip(". …")
            else:
                out.append(s)
        return out


    def main():
        hechos = set()
        if os.path.exists(SAL):
            hechos = {json.loads(l)["archivo"] for l in open(SAL, encoding="utf-8") if l.strip()}
        with open(SAL, "a", encoding="utf-8") as f:
            n = 0
            for c in CURSOS:
                for a in cargar_audios_curso(c):
                    if a["archivo"] in hechos:
                        continue
                    oraciones = [dict(idx=i, oracion=s, llm_v2=None, **asignar(s)) for i, s in enumerate(dividir_v9(a["texto"]))]
                    f.write(json.dumps({"curso": c, "archivo": a["archivo"], "cedula": a["cedula"], "fecha_sesion": a["fecha_sesion"], "oraciones": oraciones}, ensure_ascii=False) + "\n")
                    f.flush()
                    n += 1
                    if n % 50 == 0:
                        print(n, "audios", flush=True)
        print("listo", flush=True)


    if True:
        main()



def paso_04_continuidad():
    r"""Paso: script «panel_v10_regla1».

    Panel v10 (2026-10-09, con el visto bueno del autor): panel v9 + regla 1 de continuidad de aprendido (relleno de huecos): una oracion sin A, de >=4
    palabras, sin D/N/R, entre dos oraciones con A, pasa a A (probada de antemano en probar_continuidad_A.py: +2.5 puntos de recall, sin perder precision, n=458).
    Lee oraciones_etiquetadas_v9.jsonl y escribe oraciones_etiquetadas_v10.jsonl (mismo esquema); el panel se arma con construir_panel_preguntas_v10.py.
    """
    # -*- coding: utf-8 -*-
    import json
    import subprocess
    import sys

    D = r"RUTA_PROYECTO\resultados\panel_preguntas" + "\\"
    agregadas = total = 0
    with open(D + "oraciones_etiquetadas_v10.jsonl", "w", encoding="utf-8") as g:
        for l in open(D + "oraciones_etiquetadas_v9.jsonl", encoding="utf-8"):
            a = json.loads(l)
            os_ = a["oraciones"]
            for i in range(1, len(os_) - 1):
                o = os_[i]
                if not o["P1"] and os_[i - 1]["P1"] and os_[i + 1]["P1"] and len(o["oracion"].split()) >= 4 and o["P2_tipo"] is None and not o["P3"]:
                    o["P1"] = True
                    o["relleno_regla1"] = True
                    agregadas += 1
            total += len(os_)
            g.write(json.dumps(a, ensure_ascii=False) + "\n")
    print(f"oraciones {total} | A agregadas por la regla 1: {agregadas}")

