# -*- coding: utf-8 -*-
r"""
Pipeline completo de Foné: de los audios descargados al panel del docente.

El código está en cuatro archivos por etapa; este programa fija la configuración y ejecuta los 15 pasos
en orden. Durante el proyecto los pasos se corrieron uno por uno; aquí se ejecutan en ese mismo orden
y el programa se detiene si alguno falla.

  transcripcion.py   pasos 1 y 2
      1. paso_01_preparar: cruza el nombre de cada archivo de audio con la cédula, usando la lista de
         estudiantes (archivo local, no incluido en el repositorio) y datos/cursos.json.
      2. paso_02_transcribir: corta cada audio en silencios (ffmpeg), convierte los trozos a WAV de
         16 kHz y un canal, y los transcribe con faster-whisper.
  clasificacion.py   pasos 3 y 4
      3. paso_03_reetiquetar: divide cada transcripción en oraciones (uniendo los cortes «...» que deja el
         transcriptor) y las etiqueta con reglas léxicas con negación y el verificador de lenguaje local (Ollama).
      4. paso_04_continuidad: regla de continuidad de «aprendido».
  panel.py           pasos 5 y 13
      5. paso_05_panel_preguntas: agrega las oraciones por curso, estudiante y sesión.
     13. paso_13_panel_unificado: genera el HTML del panel con las cédulas reemplazadas por «Estudiante n».
  tema.py            pasos 6 a 12
      6. paso_06_menciones: ubica cada dificultad y los términos del vocabulario cercanos (y guarda el vocabulario).
      7. paso_07_selector: el modelo de lenguaje local elige el término al que se refiere la dificultad.
      8. paso_08_combinar: combina el selector con el tema libre heredado y arma los temas por mención.
      9. paso_09_causas_generales: reglas para horario, carga de trabajo, evaluaciones, etc.
     10. paso_10_rescate: si no hay tema ni causa, copia la frase del estudiante.
     11. paso_11_unir_obvias: une las frases rescatadas que son obviamente lo mismo que un tema o una causa ya existentes.
     12. paso_12_dashboard_tema: escribe el archivo de temas finales que lee el panel.

USO (desde la carpeta pipeline/)
    python fone_pipeline.py --listar
    python fone_pipeline.py --proyecto D:\mi_trabajo --simular
    python fone_pipeline.py --proyecto D:\mi_trabajo --desde 3 --hasta 5
    python fone_pipeline.py --proyecto D:\mi_trabajo --cpu --ollama qwen2.5:7b-instruct

REQUISITOS
  - Carpeta de trabajo con la subcarpeta de datos (por defecto «datos\extraido\», con los audios
    descargados de Drive) y la lista de estudiantes. Esos datos no se publican.
  - ffmpeg en el PATH; Ollama en marcha con el modelo elegido; GPU NVIDIA para Whisper (o --cpu).

Los archivos de etapa traen marcas en sus rutas. Para no modificarlos, el programa genera una copia con la
configuración elegida en <proyecto>\_ejecucion\ y ejecuta los pasos desde ahí.
"""
import argparse
import importlib
import os
import re
import shutil
import sys
import time

# ---------------------------------------------------------------- CONFIGURACIÓN
# Cada valor puede cambiarse aquí o con el argumento indicado.
RUTA_PROYECTO = os.environ.get("RUTA_PROYECTO", "")  # --proyecto: carpeta de trabajo
CARPETA_DATOS = "datos"                              # --datos: audios y registros de entrada
CARPETA_RESULTADOS = "resultados"                    # --resultados: salidas de cada paso
MODELO_WHISPER = "large-v3"                          # --whisper: modelo de faster-whisper
USAR_GPU = True                                      # --cpu: usar la CPU en vez de la GPU
MODELO_OLLAMA = "qwen2.5:7b-instruct"                # --ollama: modelo del verificador y el selector
# ------------------------------------------------------------------------------

# Marcas que traen los archivos de etapa y se reemplazan en la copia de ejecución.
_MARCA_RUTA = "RUTA_PROYECTO"
_MARCA_DATOS = "CARPETA_DATOS"
_MARCA_RESULTADOS = "resultados"
_WHISPER_ORIGINAL = 'WhisperModel("large-v3", device="cuda", compute_type="int8_float16")'
_OLLAMA_ORIGINAL = '"qwen2.5:7b-instruct"'

ETAPAS = ["transcripcion", "clasificacion", "tema", "panel"]

# (archivo de etapa, función, nombre del paso)
PASOS = [
    ("transcripcion", "paso_01_preparar", "Cruce del nombre del archivo con la cédula"),
    ("transcripcion", "paso_02_transcribir", "Transcripción local con Whisper"),
    ("clasificacion", "paso_03_reetiquetar", "Oraciones y etiquetado con reglas y verificador"),
    ("clasificacion", "paso_04_continuidad", "Regla de continuidad de «aprendido»"),
    ("panel", "paso_05_panel_preguntas", "Panel de las tres preguntas"),
    ("tema", "paso_06_menciones", "Tema: menciones y candidatos"),
    ("tema", "paso_07_selector", "Tema: selector con el modelo de lenguaje local"),
    ("tema", "paso_08_combinar", "Tema: combinación del selector con el tema heredado"),
    ("tema", "paso_09_causas_generales", "Tema: causas generales y zona de respuesta"),
    ("tema", "paso_10_rescate", "Tema: rescate de la frase del estudiante"),
    ("tema", "paso_11_unir_obvias", "Tema: unión de frases obvias"),
    ("tema", "paso_12_dashboard_tema", "Tema: archivo de temas finales"),
    ("panel", "paso_13_panel_unificado", "Panel final con estudiantes seudonimizados"),
]

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ_REPO = os.path.dirname(AQUI)


def adaptar_texto(t, destino, proyecto, datos, resultados, whisper, gpu, ollama):
    """Aplica la configuración elegida al código fuente de un archivo de etapa."""
    t = t.replace(_MARCA_RUTA + "\\pipeline", destino)
    t = t.replace(_MARCA_RUTA + "\\panel", os.path.join(RAIZ_REPO, "panel"))
    t = t.replace(_MARCA_RUTA, proyecto)
    t = t.replace(_MARCA_DATOS, datos)
    if resultados != _MARCA_RESULTADOS:
        t = re.sub(r"(?<![A-Za-z_])resultados(?=\\)", resultados, t)
    dispositivo = 'device="cuda", compute_type="int8_float16"' if gpu else 'device="cpu", compute_type="int8"'
    t = t.replace(_WHISPER_ORIGINAL, f'WhisperModel("{whisper}", {dispositivo})')
    t = t.replace(_OLLAMA_ORIGINAL, f'"{ollama}"')
    return t


def preparar_copia(proyecto, datos, resultados, whisper, gpu, ollama):
    destino = os.path.join(proyecto, "_ejecucion")
    if os.path.isdir(destino):
        shutil.rmtree(destino)
    os.makedirs(destino)
    for etapa in ETAPAS:
        t = open(os.path.join(AQUI, etapa + ".py"), encoding="utf-8").read()
        t = adaptar_texto(t, destino, proyecto, datos, resultados, whisper, gpu, ollama)
        open(os.path.join(destino, etapa + ".py"), "w", encoding="utf-8").write(t)
    # carpetas de salida que los pasos esperan encontrar
    for sub in ("panel_preguntas", "temas_curso", "reglas_oracion"):
        os.makedirs(os.path.join(proyecto, resultados, sub), exist_ok=True)
    os.makedirs(os.path.join(proyecto, "logs"), exist_ok=True)
    # plantilla del panel (el paso 12 la busca en <proyecto>/panel/)
    shutil.copytree(os.path.join(RAIZ_REPO, "panel"), os.path.join(proyecto, "panel"), dirs_exist_ok=True)
    return destino


def ejecutar_paso(destino, etapa, funcion, proyecto):
    if destino not in sys.path:
        sys.path.insert(0, destino)
    modulo = importlib.import_module(etapa)
    argv, sys.argv = sys.argv, ["fone_pipeline"]
    cwd = os.getcwd()
    os.chdir(proyecto)
    try:
        getattr(modulo, funcion)()
    finally:
        sys.argv = argv
        os.chdir(cwd)


def main():
    ap = argparse.ArgumentParser(description="Ejecuta el pipeline completo de Foné.")
    ap.add_argument("--proyecto", default=RUTA_PROYECTO, help="carpeta de trabajo (o variable RUTA_PROYECTO)")
    ap.add_argument("--datos", default=CARPETA_DATOS, help="subcarpeta de datos de entrada (por defecto: %s)" % CARPETA_DATOS)
    ap.add_argument("--resultados", default=CARPETA_RESULTADOS, help="subcarpeta de resultados (por defecto: %s)" % CARPETA_RESULTADOS)
    ap.add_argument("--whisper", default=MODELO_WHISPER, help="modelo de faster-whisper (por defecto: %s)" % MODELO_WHISPER)
    ap.add_argument("--cpu", action="store_true", help="usar la CPU en vez de la GPU para Whisper")
    ap.add_argument("--ollama", default=MODELO_OLLAMA, help="modelo de Ollama (por defecto: %s)" % MODELO_OLLAMA)
    ap.add_argument("--listar", action="store_true", help="muestra los pasos y termina")
    ap.add_argument("--simular", action="store_true", help="solo imprime lo que haría; no ejecuta nada")
    ap.add_argument("--desde", type=int, default=1, help="primer paso (1 a %d)" % len(PASOS))
    ap.add_argument("--hasta", type=int, default=len(PASOS), help="último paso")
    a = ap.parse_args()

    if a.listar:
        print("Antes del paso 1: descargar a mano los audios de Drive a <proyecto>\\%s\\extraido\\" % a.datos)
        for n, (etapa, funcion, nombre) in enumerate(PASOS, 1):
            print(f"{n:2d}. {nombre}  [{etapa}.{funcion}]")
        return

    if not a.proyecto:
        sys.exit("Indique la carpeta de trabajo con --proyecto o con la variable de entorno RUTA_PROYECTO.")
    proyecto = os.path.abspath(a.proyecto)
    destino = os.path.join(proyecto, "_ejecucion")
    if not a.simular:
        destino = preparar_copia(proyecto, a.datos, a.resultados, a.whisper, not a.cpu, a.ollama)

    for n, (etapa, funcion, nombre) in enumerate(PASOS, 1):
        if n < a.desde or n > a.hasta:
            continue
        print(f"[{n}/{len(PASOS)}] {nombre}  ->  {etapa}.{funcion}()", flush=True)
        if a.simular:
            continue
        t0 = time.time()
        try:
            ejecutar_paso(destino, etapa, funcion, proyecto)
        except SystemExit as e:
            if e.code not in (None, 0):
                sys.exit(f"El paso {n} terminó con error ({e.code}). Corrija y vuelva a correr con --desde {n}.")
        except Exception as e:
            sys.exit(f"El paso {n} falló: {type(e).__name__}: {e}. Corrija y vuelva a correr con --desde {n}.")
        print(f"    listo en {time.time() - t0:.0f} s", flush=True)
    print("Simulación terminada: no se ejecutó nada." if a.simular else "Pipeline terminado.")


if __name__ == "__main__":
    main()
