# -*- coding: utf-8 -*-
"""Pasos 1 y 2 de Foné: preparación de los audios y transcripción local.

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



@_biblioteca("retranscribir_muletillas_produccion")
def _cargar_retranscribir_muletillas_produccion():
    import os

    import re

    import json

    import time

    import subprocess

    import uuid

    SITE = os.environ.get("FONE_SITE_PACKAGES", "")  # carpeta site-packages (para localizar las DLL de NVIDIA, solo en Windows)

    for sub in ["cudnn\\bin", "cublas\\bin"]:
        p_ = os.path.join(SITE, "nvidia", sub)
        if os.path.isdir(p_):
            os.add_dll_directory(p_)

    from faster_whisper import WhisperModel

    TESIS = r"RUTA_PROYECTO"

    TMP_DIR = TESIS + r"\_tmp_retranscripcion_chunks"

    LOG_PATH = TESIS + r"\logs\retranscripcion_muletillas.log"

    os.makedirs(TMP_DIR, exist_ok=True)

    MULETILLAS = ["eh", "ehh", "eeh", "ah", "em", "emm", "ehm", "este", "mmm", "mmmm",
                  "pues", "osea", "o sea", "digamos", "aja", "tipo"]

    PROMPT_MULETILLAS = (
        "Eh, o sea, pues... este, no sé, tipo... mmm, eh, digamos que sí, o sea, "
        "aja, este... eh, pues no sé, tipo, mmm."
    )

    CHUNK_TARGET_S = 22.0

    def contar_muletillas(texto):
        t = texto.lower()
        total = 0
        for m in MULETILLAS:
            total += len(re.findall(r"\b" + re.escape(m) + r"\b", t))
        return total

    def duracion_audio(ruta):
        # encoding="utf-8"/errors="replace" explicito: sin esto subprocess.run decodifica
        # con cp1252 en Windows y falla si ffprobe repite en stderr un nombre con tildes o "Ñ".
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", ruta]
        proc = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=60)
        try:
            return float(proc.stdout.strip())
        except ValueError:
            return None

    def detectar_silencios(ruta):
        cmd = ["ffmpeg", "-i", ruta, "-af", "silencedetect=noise=-30dB:d=0.3", "-f", "null", "-"]
        proc = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=180)
        silencios = []
        inicio = None
        for line in proc.stderr.splitlines():
            m1 = re.search(r"silence_start:\s*([\d.]+)", line)
            m2 = re.search(r"silence_end:\s*([\d.]+)", line)
            if m1:
                inicio = float(m1.group(1))
            if m2 and inicio is not None:
                silencios.append((inicio, float(m2.group(1))))
                inicio = None
        return silencios

    def construir_cortes(duracion, silencios, objetivo=CHUNK_TARGET_S):
        # OJO: t avanza sobre una secuencia FIJA (n*objetivo), nunca en funcion de `punto`.
        # Caso real en produccion: cuando hay
        # un solo silencio gigante que cubre casi todo el audio, su punto medio es el mismo
        # sin importar `t` -- si t se recalculaba como `punto + objetivo`, `t` se quedaba
        # fijo para siempre y el while nunca terminaba (loop infinito, 100% CPU, sin ningun
        # error ni output -- exactamente el patron de las caidas silenciosas de esta sesion).
        cortes = [0.0]
        n = 1
        while n * objetivo < duracion - 3.0:
            t = n * objetivo
            candidatos = [(s + f) / 2 for (s, f) in silencios if s < t + objetivo * 0.6 and f > t - objetivo * 0.6]
            punto = min(candidatos, key=lambda c: abs(c - t)) if candidatos else t
            if punto - cortes[-1] > 5.0:
                cortes.append(punto)
            n += 1
        cortes.append(duracion)
        return cortes

    def extraer_chunk(ruta, inicio, fin, salida):
        cmd = ["ffmpeg", "-y", "-ss", str(inicio), "-to", str(fin), "-i", ruta,
               "-ar", "16000", "-ac", "1", salida]
        subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=120)

    DURACION_MAXIMA_PLAUSIBLE_S = 600.0

    MAX_CHUNKS_POR_AUDIO = 40

    def transcribir_con_chunking(model, ruta_audio, duracion_conocida=None):
        dur = duracion_conocida
        if not dur or dur < 0.5:
            dur = duracion_audio(ruta_audio)
        if not dur or dur < 0.5:
            return "", 0, 0, 0
        if dur > DURACION_MAXIMA_PLAUSIBLE_S:
            # Metadata de contenedor corrupta (ver nota arriba) -- no confiar en este valor
            # para trocear; usar el tope como duracion de trabajo.
            dur = DURACION_MAXIMA_PLAUSIBLE_S
        silencios = detectar_silencios(ruta_audio)
        cortes = construir_cortes(dur, silencios)

        if len(cortes) - 1 > MAX_CHUNKS_POR_AUDIO:
            raise RuntimeError(
                f"audio genero {len(cortes)-1} chunks (> {MAX_CHUNKS_POR_AUDIO}), "
                f"probablemente corrupto -- se salta"
            )

        textos = []
        for i in range(len(cortes) - 1):
            ini, fin = cortes[i], cortes[i + 1]
            chunk_path = os.path.join(TMP_DIR, f"chunk_{uuid.uuid4().hex}.wav")
            try:
                extraer_chunk(ruta_audio, ini, fin, chunk_path)
                segments_iter, _ = model.transcribe(
                    chunk_path, language="es", beam_size=5, word_timestamps=False,
                    condition_on_previous_text=False, initial_prompt=PROMPT_MULETILLAS,
                    temperature=[0.0, 0.2, 0.4],
                )
                texto_chunk = " ".join(s.text.strip() for s in segments_iter).strip()
                textos.append(texto_chunk)
            finally:
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)

        texto_final = " ".join(t for t in textos if t)
        return texto_final, contar_muletillas(texto_final), len(texto_final.split()), len(cortes) - 1

    return {k: v for k, v in locals().items() if not k.startswith('__')}


def paso_01_preparar():
    r"""Paso: script «preparar_transcripcion».

    Cruza los audios nuevos descargados en CARPETA_DATOS\extraido\<carpeta>\ contra
    el roster Foné — Estudiantes.xlsx (raiz del proyecto) para asignarles
    Cedula (los archivos solo traen el nombre del estudiante). Arma el registro
    completo {archivo, ruta, cedula, grupo, fecha_sesion} por curso, listo para
    alimentar la transcripcion local (Whisper).

    Imprime el % de match y guarda resultados
egistro_transcripcion_CARPETA_DATOS.json
    con los matches, y resultados\sin_match_CARPETA_DATOS.json con los que no se
    pudieron resolver (para revisar a mano).
    """
    # -*- coding: utf-8 -*-

    import json
    import os
    import re
    import unicodedata

    import openpyxl

    TESIS = r"RUTA_PROYECTO"
    ROSTER = TESIS + r"\Foné — Estudiantes.xlsx"
    BASE_AUDIOS = TESIS + r"\CARPETA_DATOS\extraido"

    CEDULA_DEMO_PROFESOR = "654321"

    # carpeta descargada -> (grupo_key del roster, prefijo de materia en el nombre de archivo, nombre_curso interno)
    CARPETAS = {c["carpeta"]: (c["grupo"], c["prefijo"], c["curso"]) for c in json.load(open(r"RUTA_PROYECTO\CARPETA_DATOS\cursos.json", encoding="utf-8"))}


    def normalizar_nombre(t):
        t = unicodedata.normalize("NFD", t.upper())
        t = "".join(c for c in t if unicodedata.category(c) != "Mn")
        t = re.sub(r"[^A-Z ]", " ", t)
        return " ".join(t.split())


    def cargar_roster():
        wb = openpyxl.load_workbook(ROSTER, read_only=True)
        ws = wb["Estudiantes"]
        rows = list(ws.iter_rows(values_only=True))
        header = rows[0]
        idx = {h: i for i, h in enumerate(header)}
        def val(r, col):
            i = idx[col]
            return r[i] if i < len(r) else None

        por_grupo = {}
        for r in rows[1:]:
            cedula_raw = val(r, "Cedula")
            if not cedula_raw:
                continue
            cedula = str(int(cedula_raw)) if isinstance(cedula_raw, float) else str(cedula_raw)
            nombre_norm = normalizar_nombre(val(r, "Nombre") or "")
            grupos = str(val(r, "Grupos") or "").split(",")
            for g in grupos:
                g = g.strip()
                por_grupo.setdefault(g, {})[nombre_norm] = cedula
        return por_grupo


    def extraer_nombre_de_archivo(nombre_archivo, prefijo_materia):
        base = os.path.splitext(nombre_archivo)[0]
        base = re.sub(r"\(\d+\)$", "", base)  # sufijo de reintento "(1)", "(2)"
        partes = base.split("_")
        # formato: DDMMYYYY_S<n>_<PREFIJO>_<NOMBRE...>
        try:
            i_prefijo = partes.index(prefijo_materia)
        except ValueError:
            i_prefijo = 2  # fallback: los primeros 2 son fecha y semana
        nombre_partes = partes[i_prefijo + 1:]
        return normalizar_nombre(" ".join(nombre_partes))


    def main():
        roster = cargar_roster()
        registro = []
        sin_match = []

        for carpeta, (grupo_key, prefijo, nombre_curso) in CARPETAS.items():
            ruta_carpeta = os.path.join(BASE_AUDIOS, carpeta)
            nombres_roster = roster.get(grupo_key, {})
            archivos = []
            for root, _, files in os.walk(ruta_carpeta):
                for f in files:
                    archivos.append(os.path.join(root, f))

            n_match = 0
            for ruta in archivos:
                nombre_archivo = os.path.basename(ruta)
                nombre_norm = extraer_nombre_de_archivo(nombre_archivo, prefijo)

                if CEDULA_DEMO_PROFESOR in nombre_archivo:
                    continue  # audio de prueba del profesor, no un estudiante real

                cedula = nombres_roster.get(nombre_norm)
                if cedula is None:
                    sin_match.append({"curso": nombre_curso, "archivo": nombre_archivo, "nombre_buscado": nombre_norm})
                    continue

                m = re.match(r"(\d{2})(\d{2})(\d{4})", nombre_archivo)
                fecha_sesion = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None

                registro.append({
                    "curso": nombre_curso, "ruta": ruta, "archivo": nombre_archivo,
                    "cedula": int(cedula), "fecha_sesion": fecha_sesion,
                })
                n_match += 1

            total_reales = len([a for a in archivos if CEDULA_DEMO_PROFESOR not in a])
            print(f"[{nombre_curso}] {n_match}/{total_reales} audios con match "
                  f"({100*n_match/total_reales:.1f}%)")

        with open(TESIS + r"\resultados\registro_transcripcion_CARPETA_DATOS.json", "w", encoding="utf-8") as f:
            json.dump(registro, f, ensure_ascii=False, indent=1)
        with open(TESIS + r"\resultados\sin_match_CARPETA_DATOS.json", "w", encoding="utf-8") as f:
            json.dump(sin_match, f, ensure_ascii=False, indent=1)

        print(f"\nTotal con match: {len(registro)}")
        print(f"Total SIN match: {len(sin_match)}")
        if sin_match:
            print("\nEjemplos sin match:")
            for s in sin_match[:15]:
                print("  ", s["curso"], "|", s["nombre_buscado"], "|", s["archivo"])


    if True:
        main()



def paso_02_transcribir():
    r"""Paso: script «transcribir».

    Transcribe localmente (Whisper large-v3 GPU + chunking por silencios +
    PROMPT_MULETILLAS, misma logica ya validada en
    retranscribir_muletillas_produccion.py) los 801 audios nuevos de
    CARPETA_DATOS\extraido\ ya cruzados contra el roster
    (resultados
egistro_transcripcion_CARPETA_DATOS.json).

    Resumible: si se interrumpe, al volver a correr salta los audios que ya
    tienen resultado en el jsonl de salida de su curso.

    Salida: resultados	ranscripciones_CARPETA_DATOS\<curso>.jsonl -- un registro
    por audio con cedula, sesion, texto, conteo_muletillas, etc.
    """
    # -*- coding: utf-8 -*-

    import json
    import os
    import re
    import subprocess
    import sys
    import time
    from collections import defaultdict

    transcribir_con_chunking = _modulo("retranscribir_muletillas_produccion").transcribir_con_chunking
    duracion_audio = _modulo("retranscribir_muletillas_produccion").duracion_audio
    from faster_whisper import WhisperModel


    def duracion_por_decodificacion(ruta):
        """Fallback para los .webm nuevos (grabados con MediaRecorder de Chrome):
    no traen duracion en los metadatos del contenedor -- ni ffprobe ni la
    cabecera de ffmpeg la reportan ("Duration: N/A"). Decodificando el audio
    completo, ffmpeg si informa el tiempo real procesado en la ultima linea
    de progreso ("time=HH:MM:SS.xx")."""
        cmd = ["ffmpeg", "-i", ruta, "-f", "null", "-"]
        proc = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=180)
        tiempos = re.findall(r"time=(\d+):(\d+):(\d+\.\d+)", proc.stderr)
        if not tiempos:
            return None
        h, m, s = tiempos[-1]
        return int(h) * 3600 + int(m) * 60 + float(s)


    def duracion_robusta(ruta):
        d = duracion_audio(ruta)
        if d and d >= 0.5:
            return d
        return duracion_por_decodificacion(ruta)

    TESIS = r"RUTA_PROYECTO"
    OUT_DIR = TESIS + r"\resultados\transcripciones_CARPETA_DATOS"
    LOG_PATH = TESIS + r"\logs\transcripcion_CARPETA_DATOS.log"
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)


    def log(msg):
        linea = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        print(linea, flush=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(linea + "\n")


    def cargar_hechos(out_path):
        hechos = set()
        if os.path.exists(out_path):
            with open(out_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        hechos.add(d["archivo"])
                    except Exception:
                        continue
        return hechos


    def main():
        with open(TESIS + r"\resultados\registro_transcripcion_CARPETA_DATOS.json", encoding="utf-8") as f:
            registro = json.load(f)

        por_curso = defaultdict(list)
        for r in registro:
            por_curso[r["curso"]].append(r)

        log("Cargando modelo large-v3 en GPU...")
        model = WhisperModel("large-v3", device="cuda", compute_type="int8_float16")
        log("Modelo cargado.")

        for curso, filas in por_curso.items():
            out_path = os.path.join(OUT_DIR, f"{curso}.jsonl")
            ya_hechos = cargar_hechos(out_path)
            pendientes = [r for r in filas if r["archivo"] not in ya_hechos]
            log(f"[{curso}] {len(filas)} audios totales, {len(ya_hechos)} ya procesados, {len(pendientes)} pendientes")

            t_curso_inicio = time.time()
            for idx, r in enumerate(pendientes, 1):
                t0 = time.time()
                if not os.path.exists(r["ruta"]):
                    resultado = {**r, "texto": None, "error": "audio_no_encontrado"}
                else:
                    try:
                        dur = duracion_robusta(r["ruta"])
                        texto, n_muletillas, n_palabras, n_chunks = transcribir_con_chunking(
                            model, r["ruta"], duracion_conocida=dur
                        )
                        resultado = {
                            **r, "texto": texto, "conteo_muletillas": n_muletillas,
                            "num_palabras": n_palabras, "n_chunks": n_chunks, "error": None,
                        }
                    except Exception as e:
                        resultado = {**r, "texto": None, "error": f"excepcion: {e}"}

                with open(out_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(resultado, ensure_ascii=False) + "\n")

                dt = time.time() - t0
                if idx % 10 == 0 or idx == len(pendientes):
                    transcurrido = time.time() - t_curso_inicio
                    promedio = transcurrido / idx
                    restante = promedio * (len(pendientes) - idx)
                    log(f"[{curso}] {idx}/{len(pendientes)} -- ultimo audio {dt:.1f}s -- "
                        f"promedio {promedio:.1f}s/audio -- ETA curso {restante/60:.1f} min")

            log(f"[{curso}] completado.")

        log("TODO COMPLETADO.")


    if True:
        main()

