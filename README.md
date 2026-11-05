# Foné: código del flujo de análisis y del panel

Código de la tesis *Foné: instrumento léxico para clasificar reflexiones orales semanales de estudiantes y panel de apoyo para el docente* (Universidad Externado de Colombia, Programa de Ciencia de Datos, 2026).

Contiene **solo código**: no incluye audios, transcripciones, listas de estudiantes, tablas con datos ni claves. Se agrega al repositorio existente, donde ya están `index.html` (página de captura del audio) y `dashboard.html` (panel del docente); esos dos archivos no se modifican.

## Cómo citar

Reyes Castellanos, J. D. (2026). *Foné: instrumento léxico para clasificar reflexiones orales semanales de estudiantes y panel de apoyo para el docente* [Trabajo de grado, Universidad Externado de Colombia].

## Contenido

| Archivo | Qué contiene |
|---|---|
| `index.html`, `dashboard.html` | Ya están en el repositorio: página de captura y panel del docente. |
| `apps_script/Code.gs` | Apps Script de Google: valida cédula y clave, guarda el audio en Drive (con los permisos privados de la carpeta) y registra el cumplimiento. No llama a ningún servicio externo. |
| `pipeline/fone_pipeline.py` | Configuración, argumentos y orden de los 13 pasos. |
| `pipeline/transcripcion.py` | Pasos 1 y 2: preparación de los audios y transcripción local. |
| `pipeline/clasificacion.py` | Pasos 3 y 4: oraciones, reglas léxicas con negación, verificador de lenguaje y regla de continuidad. |
| `pipeline/panel.py` | Pasos 5 y 13: panel de las tres preguntas y panel final con estudiantes seudonimizados. |
| `pipeline/tema.py` | Pasos 6 a 12: tema de la dificultad. |
| `panel/panel_unificado.base.html` | Plantilla del panel del docente, sin datos. |

Cada paso es una función `paso_NN_*` dentro de su archivo de etapa; el código de cada paso no cambia respecto del flujo que se corrió durante el proyecto.

## Requisitos

- Windows. El código usa rutas con barra invertida y solo se ha ejecutado en Windows.
- Python 3.12 con los paquetes de `requirements.txt` (`pip install -r requirements.txt`) y el modelo de spaCy `es_core_news_sm` (`python -m spacy download es_core_news_sm`).
- `ffmpeg` en el PATH.
- GPU NVIDIA para Whisper (`faster-whisper`, `int8_float16`); sin GPU se puede usar `--cpu`.
- Ollama en marcha con un modelo de lenguaje local (por defecto, `qwen2.5:7b-instruct`) para el verificador y el selector de tema.

## Estructura de carpetas esperada

El pipeline trabaja dentro de una carpeta de trabajo (`<proyecto>`), distinta del repositorio, que no se publica:

```
<proyecto>/
├── datos/
│   ├── cursos.json                    cursos del semestre (formato abajo)
│   └── extraido/
│       └── <carpeta_de_cada_curso>/   audios descargados de Drive (.webm, .m4a, ...)
├── Foné — Estudiantes.xlsx            lista local de estudiantes (nombre, cédula, vínculo y cursos)
├── resultados/                        salidas de cada paso
└── _ejecucion/                        copia temporal de los archivos de etapa con las rutas reales (la genera el programa)
```

`datos/cursos.json` lista los cursos, con la carpeta de Drive descargada, la clave del grupo en la hoja maestra, el prefijo de materia que lleva el nombre de los audios y el nombre interno del curso:

```json
[
  {"carpeta": "<carpeta descargada de Drive>", "grupo": "curso_a", "prefijo": "ALG", "curso": "Curso_A"}
]
```

Los nombres `datos` y `resultados` se pueden cambiar con `--datos` y `--resultados`.

Los pasos 6 a 12 (tema) usan además dos archivos que provienen del análisis anterior de dificultad y dudas, no de estos pasos: `resultados/absa_dashboard_datos.json` (tema libre del modelo de lenguaje, que el paso 8 usa como señal independiente para marcar un tema como «confirmado») y `resultados/absa_dashboard_datos_v4.json` (estructura base, con las menciones de dudas, que el paso 8 completa con los temas nuevos). Esos dos archivos no se incluyen.

## Cómo ejecutar

Durante el proyecto, los pasos se corrieron uno por uno. `pipeline/fone_pipeline.py` los ejecuta en ese mismo orden y se detiene si un paso falla.

```bash
python fone_pipeline.py --listar
python fone_pipeline.py --proyecto D:\mi_trabajo --simular
python fone_pipeline.py --proyecto D:\mi_trabajo --desde 3 --hasta 5
python fone_pipeline.py --proyecto D:\mi_trabajo --cpu --ollama qwen2.5:7b-instruct
```

| Opción | Qué hace |
|---|---|
| `--proyecto` | Carpeta de trabajo (también se lee de la variable de entorno `RUTA_PROYECTO`). |
| `--datos`, `--resultados` | Nombres de las subcarpetas de datos y de resultados. |
| `--whisper`, `--cpu` | Modelo de faster-whisper y uso de la CPU en vez de la GPU. |
| `--ollama` | Modelo de Ollama para el verificador y el selector de tema. |
| `--listar` | Muestra los pasos y termina. |
| `--simular` | Imprime lo que haría sin ejecutar nada. |
| `--desde N`, `--hasta N` | Ejecuta solo un tramo de los pasos. |

Los archivos de etapa traen marcas en sus rutas. Para no modificarlos, el programa genera una copia con la configuración elegida en `<proyecto>/_ejecucion/` y ejecuta los pasos desde ahí.

Antes del paso 1, los audios se descargan a mano de Drive a `<proyecto>/datos/extraido/`.

| Paso | Qué hace | Función |
|---|---|---|
| 1 | Cruce del nombre del archivo con la cédula | `transcripcion.paso_01_preparar` |
| 2 | Transcripción local con Whisper | `transcripcion.paso_02_transcribir` |
| 3 | Oraciones y etiquetado con reglas y verificador | `clasificacion.paso_03_reetiquetar` |
| 4 | Regla de continuidad de «aprendido» | `clasificacion.paso_04_continuidad` |
| 5 | Panel de las tres preguntas | `panel.paso_05_panel_preguntas` |
| 6 | Tema: menciones y candidatos | `tema.paso_06_menciones` |
| 7 | Tema: selector con el modelo de lenguaje local | `tema.paso_07_selector` |
| 8 | Tema: combinación del selector con el tema heredado | `tema.paso_08_combinar` |
| 9 | Tema: causas generales y zona de respuesta | `tema.paso_09_causas_generales` |
| 10 | Tema: rescate de la frase del estudiante | `tema.paso_10_rescate` |
| 11 | Tema: unión de frases obvias | `tema.paso_11_unir_obvias` |
| 12 | Tema: archivo de temas finales | `tema.paso_12_dashboard_tema` |
| 13 | Panel final con estudiantes seudonimizados | `panel.paso_13_panel_unificado` |

Las reglas de clasificación, los léxicos, la negación y el verificador de lenguaje están en `clasificacion.py`. El procesamiento de audio y texto se hace en un equipo local; Drive y el Apps Script de Google solo guardan los audios y los archivos de resultados.

## Cómo se nombra cada audio

El Apps Script nombra cada archivo al subirlo a Drive con `generarNombreArchivo()`:

`DDMMYYYY_S<n>_<MATERIA>_<NOMBRE_DEL_ESTUDIANTE>.<ext>`

- `DDMMYYYY`: fecha de la sesión; `S<n>`: número de sesión; `<MATERIA>`: materia del grupo; el nombre del estudiante se toma de la hoja maestra a partir de la cédula, en mayúsculas y con guiones bajos.
- El archivo no se renombra después. Por eso los audios en Drive y las carpetas descargadas **contienen el nombre real del estudiante** y no deben publicarse.
- Para el análisis, el paso 1 cruza el nombre del archivo con la lista de estudiantes (archivo local, no incluido) y obtiene la cédula; desde ahí el análisis usa la cédula.

## Cómo se seudonimiza

El paso 13 (`panel.paso_13_panel_unificado`, línea `num = {c: i + 1 for ...}`) reemplaza cada cédula por «Estudiante n», donde n es la posición de la cédula en la lista ordenada de cédulas, igual para todos los cursos. Los nombres de archivo no se incluyen en el panel. La correspondencia cédula-número no se guarda en ningún archivo: se recalcula en cada construcción. En el panel de producción, el docente ve por su nombre a los estudiantes de sus propios cursos.

## Qué se le hace al audio antes de transcribir

No se normaliza el volumen ni se reduce el ruido. El paso 2 detecta silencios con ffmpeg (`silencedetect`, −30 dB, 0,3 s), corta el audio en trozos de unos 22 s en los silencios más cercanos y convierte cada trozo a WAV de 16 kHz y un canal. Parámetros de `faster-whisper`: `language="es"`, `beam_size=5`, `temperature=[0.0, 0.2, 0.4]`, `condition_on_previous_text=False`, `initial_prompt` con muletillas, sin filtro VAD.

## Configuración del Apps Script

`Code.gs` espera una hoja maestra de estudiantes y hojas de grabaciones y de control por curso, cuyos nombres se definen en las constantes del inicio del archivo. Se despliega como aplicación web y su URL se usa en la página de captura.

- El servidor valida la cédula y la clave de quien envía cada audio (`doPost`), y que la cédula pertenezca al curso; la página de captura debe enviar la clave junto con el audio.
- Los audios se guardan en la carpeta del curso en Drive y heredan sus permisos privados; no se comparten por enlace.
- La cuenta de demostración del panel (opcional) se define en la propiedad de script `CEDULAS_DEMO`; su clave está solo en la hoja maestra.

## Cambios de diseño durante el proyecto

Al inicio del semestre 2026-II, el Apps Script enviaba cada audio al servicio de transcripción de Groq al subirlo. Se desactivó el 6 de octubre de 2026 por su baja calidad y por privacidad; esas transcripciones no se usaron en el análisis, que siempre se hizo localmente con Whisper large-v3. Desde entonces el audio solo se guarda en Drive.
