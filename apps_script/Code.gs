let _GRUPOS_CACHE = null;
function leerGrupos() {
  if (_GRUPOS_CACHE) return _GRUPOS_CACHE;
  const files = DriveApp.getFilesByName(SHEET_ESTUDIANTES);
  if (!files.hasNext()) throw new Error('No se encontró la hoja de configuración: ' + SHEET_ESTUDIANTES);
  const ss = SpreadsheetApp.open(files.next());
  const sheet = ss.getSheetByName('Grupos');
  if (!sheet || sheet.getLastRow() < 2) throw new Error('La pestaña "Grupos" está vacía o no existe en ' + SHEET_ESTUDIANTES);
  const headers = sheet.getRange(1,1,1,sheet.getLastColumn()).getValues()[0];
  const campos = ['GrupoKey','NombreGrupo','Materia','CedulaProfesor','CarpetaDrive','HojaGrabaciones','HojaControl'];
  const idx = {};
  campos.forEach(c => { idx[c] = headers.indexOf(c); });
  const faltantes = campos.filter(c => idx[c] < 0);
  if (faltantes.length) throw new Error('Faltan columnas en la hoja Grupos: ' + faltantes.join(', '));

  const rows = sheet.getRange(2,1,sheet.getLastRow()-1,sheet.getLastColumn()).getValues();
  const colLimite3 = headers.indexOf('DiasLimite3'); // opcional — si falta, cae al default (3 = lunes)
  _GRUPOS_CACHE = rows.map(r => ({
    key: String(r[idx.GrupoKey]).trim(),
    nombre: String(r[idx.NombreGrupo]).trim(),
    materia: String(r[idx.Materia]).trim(),
    profesor: String(r[idx.CedulaProfesor]).trim(),
    carpeta: String(r[idx.CarpetaDrive]).trim(),
    grabaciones: String(r[idx.HojaGrabaciones]).trim(),
    control: String(r[idx.HojaControl]).trim(),
    limite3: colLimite3>=0 && r[colLimite3] !== '' ? Number(r[colLimite3]) : 3,
  })).filter(g => g.key);
  return _GRUPOS_CACHE;
}
function grupoPorKey(key) {
  const g = leerGrupos().find(g => g.key === String(key).trim());
  if (!g) throw new Error('Grupo no encontrado en la hoja Grupos: ' + key);
  return g;
}

// ── Alertas del modelo (piloto local, "mientras tanto") ──
// El modelo (RandomForest de sistema_dos_niveles.py) corre en la máquina local del
// docente, NO aquí — este bloque solo lee el JSON de resultados que se sube
// a mano a esta carpeta de Drive tras correr predecir_semestre_actual.py +
// exportar_datos_dashboard.py. Si la carpeta o el archivo no existen todavía (p.ej.
// la primera vez, antes de subir nada), devuelve {} y el dashboard simplemente no
// muestra la sección de alertas del modelo, sin romper el resto.
const CARPETA_ALERTAS_MODELO = 'Foné — Alertas Modelo';
const ARCHIVO_ALERTAS_MODELO = 'dashboard_semestre_actual.json';
function leerAlertasModelo() {
  try {
    const carpetas = DriveApp.getFoldersByName(CARPETA_ALERTAS_MODELO);
    if (!carpetas.hasNext()) return {};
    const archivos = carpetas.next().getFilesByName(ARCHIVO_ALERTAS_MODELO);
    if (!archivos.hasNext()) return {};
    return JSON.parse(archivos.next().getBlob().getDataAsString('UTF-8'));
  } catch (e) {
    return {};
  }
}

// Mismo patrón que leerAlertasModelo() de arriba, pero para el análisis por tema (ABSA:
// dudas/dificultad + reglas v3 + árbitro LLM + tema(s) + vigencia) — el JSON lo genera el pipeline (paso del tema)
// localmente y el usuario lo sube a mano a esta carpeta de Drive. Si la carpeta o el
// archivo no existen todavía, devuelve {} y la pestaña "Estudiantes → Por tema" cae al
// selector de archivo local, sin romper el resto del dashboard.
const CARPETA_ABSA_MODELO = 'Foné — Análisis por Tema';
// Mismo nombre del archivo JSON que genera el pipeline — así al subir
// el archivo a Drive no hace falta renombrarlo.
const ARCHIVO_ABSA_MODELO = 'absa_dashboard_data27sept.json';
function leerAbsaModelo() {
  try {
    const carpetas = DriveApp.getFoldersByName(CARPETA_ABSA_MODELO);
    if (!carpetas.hasNext()) return {};
    const archivos = carpetas.next().getFilesByName(ARCHIVO_ABSA_MODELO);
    if (!archivos.hasNext()) return {};
    return JSON.parse(archivos.next().getBlob().getDataAsString('UTF-8'));
  } catch (e) {
    return {};
  }
}

// Panel de las 3 preguntas: mismo esquema que leerAbsaModelo — JSON
// generado localmente por scripts\construir_panel_preguntas.py y subido a mano a la MISMA carpeta
// de Drive. Devuelve solo .cursos ({ grupoKey: {resumen, por_sesion, estudiantes} }) o {}.
const ARCHIVO_PANEL_PREGUNTAS = 'panel_preguntas.json';
function leerPanelPreguntas() {
  try {
    const carpetas = DriveApp.getFoldersByName(CARPETA_ABSA_MODELO);
    if (!carpetas.hasNext()) return {};
    const archivos = carpetas.next().getFilesByName(ARCHIVO_PANEL_PREGUNTAS);
    if (!archivos.hasNext()) return {};
    return JSON.parse(archivos.next().getBlob().getDataAsString('UTF-8')).cursos || {};
  } catch (e) {
    return {};
  }
}

// Hoja maestra única con TODOS los estudiantes (de todos los grupos), para que
// cambiar el roster cada semestre sea editar un Excel/Sheet, no tocar código.
// Columnas esperadas: Cedula | Nombre | Correo | Clave | Grupos
// 'Grupos' es una lista separada por comas con las claves de grupo (ej. "santiago,omar")
// para el caso de una persona matriculada en más de un curso.
const SHEET_ESTUDIANTES = 'Foné — Estudiantes';

// URLs reales de GitHub Pages — ajusta si cambian.
const URL_INDEX = 'https://jkyyng.github.io/TESIS/index.html';
const URL_DASHBOARD = 'https://jkyyng.github.io/TESIS/dashboard.html';

// Profesores — se queda hardcodeado por ahora (fuera de alcance de este cambio).
// Los profesores ya NO están hardcodeados aquí — viven en la hoja maestra "Foné — Estudiantes"
// igual que los estudiantes, distinguidos por la columna Vinculo=PROFESOR. Su nombre se
// resuelve con nombreDeEstudiante() y su cédula por grupo con grupoPorKey(key).profesor.

// Lee la hoja maestra completa. Se relee en cada llamada (sin cachear) porque el
// roster cambia poco y así siempre refleja lo que haya en la hoja en ese momento.
function leerEstudiantesMaestro() {
  const files = DriveApp.getFilesByName(SHEET_ESTUDIANTES);
  if (!files.hasNext()) throw new Error('No se encontró la hoja maestra de estudiantes: ' + SHEET_ESTUDIANTES);
  const ss = SpreadsheetApp.open(files.next());
  const sheet = ss.getSheetByName('Estudiantes');
  if (!sheet || sheet.getLastRow() < 2) return [];
  const headers = sheet.getRange(1,1,1,sheet.getLastColumn()).getValues()[0];
  const colCed = headers.indexOf('Cedula');
  const colNom = headers.indexOf('Nombre');
  const colCor = headers.indexOf('Correo');
  const colCla = headers.indexOf('Clave');
  const colGru = headers.indexOf('Grupos');
  const colVin = headers.indexOf('Vinculo'); // opcional — si falta, se asume ESTUDIANTE
  if ([colCed,colNom,colCla,colGru].includes(-1)) {
    throw new Error('Faltan columnas esperadas en la hoja Estudiantes (Cedula, Nombre, Clave, Grupos).');
  }
  const rows = sheet.getRange(2,1,sheet.getLastRow()-1,sheet.getLastColumn()).getValues();
  return rows
    .map(r => ({
      cedula: String(r[colCed]||'').trim(),
      nombre: String(r[colNom]||'').trim(),
      correo: colCor>=0 ? String(r[colCor]||'').trim() : '',
      clave: String(r[colCla]||'').trim(),
      grupos: String(r[colGru]||'').split(',').map(g=>g.trim().toLowerCase()).filter(Boolean),
      vinculo: colVin>=0 ? String(r[colVin]||'ESTUDIANTE').trim().toUpperCase() : 'ESTUDIANTE',
    }))
    .filter(e => e.cedula);
}

// Todos los ESTUDIANTES (no profesores) matriculados en un grupo — para las hojas de Notas/Control,
// donde el profesor ya se agrega aparte como fila destacada (si se incluyera aquí también,
// saldría duplicado).
function estudiantesDeGrupo(grupoKey) {
  return leerEstudiantesMaestro().filter(e => e.grupos.includes(grupoKey) && e.vinculo !== 'PROFESOR');
}

// Nombre de un estudiante por cédula (para nombrar archivos, etc.) — busca en cualquier grupo.
function nombreDeEstudiante(cedula) {
  const match = leerEstudiantesMaestro().find(e => e.cedula === String(cedula).trim());
  return match ? match.nombre.replace(/\s+/g,'_').toUpperCase() : String(cedula);
}

// Valida cédula+clave contra la hoja maestra. Devuelve a qué grupo(s) pertenece esa persona,
// para que el frontend pueda saltar directo si es uno solo, o preguntar cuál si son varios.
function validarLoginEstudiante(cedula, clave) {
  const estudiantes = leerEstudiantesMaestro();
  const match = estudiantes.find(e =>
    e.cedula === String(cedula||'').trim() && e.clave === String(clave||'').trim()
  );
  if (!match) return { ok: false, error: 'Cédula o clave incorrecta.' };
  if (match.grupos.length === 0) return { ok: false, error: 'Esta cédula no está matriculada en ningún curso.' };
  return { ok: true, nombre: match.nombre, grupos: match.grupos };
}

// Solo valida que la cédula exista en al menos un grupo (para el flujo de GRABAR, que no pide clave).
function buscarGruposDeCedula(cedula) {
  const match = leerEstudiantesMaestro().find(e => e.cedula === String(cedula||'').trim());
  if (!match) return { ok: false, error: 'Cédula no registrada.' };
  if (match.grupos.length === 0) return { ok: false, error: 'Esta cédula no está matriculada en ningún curso.' };
  return { ok: true, nombre: match.nombre, grupos: match.grupos };
}

// ── Crear toda la infraestructura de Drive para los grupos del semestre (correr UNA vez) ──
// Lee la pestaña "Grupos" y, para cada grupo, crea (si no existen ya) su carpeta de audios
// y sus hojas de Grabaciones/Control con los encabezados correctos ya armados. Es segura de
// correr varias veces — lo que ya existe se deja intacto, solo crea lo que falte.
// Carpeta contenedora de TODO el proyecto en Drive — para no dejar archivos sueltos.
// Debe existir ya en tu Drive con este nombre exacto antes de correr configurarNuevoSemestre().
const CARPETA_PROYECTO = 'Foné 2026-2';

function obtenerCarpetaProyecto() {
  const carpetas = DriveApp.getFoldersByName(CARPETA_PROYECTO);
  if (!carpetas.hasNext()) {
    throw new Error(`No encontré la carpeta "${CARPETA_PROYECTO}" en tu Drive. Créala primero (en la raíz de Mi unidad) y vuelve a correr esta función.`);
  }
  return carpetas.next();
}

// ── Corregir encabezados de sesión en hojas de Control/Notas ya creadas ──
// Necesaria cuando las hojas se crearon con configurarNuevoSemestre() ANTES de que
// SESIONES tuviera las fechas correctas — los encabezados quedan grabados al crear la
// hoja y no se actualizan solos después. Esto solo reescribe la fila 1 (columnas de
// sesión), no toca ninguna nota ni fila de estudiante ya guardada.
function corregirEncabezadosSesiones() {
  const grupos = leerGrupos();
  let corregidos = 0;
  grupos.forEach(g => {
    const filesControl = DriveApp.getFilesByName(g.control);
    if (!filesControl.hasNext()) {
      Logger.log(`${g.key}: no se encontró la hoja de Control (${g.control}), se salta.`);
      return;
    }
    const ss = SpreadsheetApp.open(filesControl.next());
    ['Control','Notas'].forEach(nombreHoja => {
      const sheet = ss.getSheetByName(nombreHoja);
      if (!sheet) return;
      SESIONES.forEach((s, i) => {
        sheet.getRange(1, 3+i).setValue('A'+(i+1)+'\n'+s);
      });
    });
    corregidos++;
    Logger.log(`${g.key}: encabezados de Control y Notas corregidos.`);
  });
  Logger.log(`corregirEncabezadosSesiones: ${corregidos} grupo(s) corregidos.`);
}

// ── Borrar columnas de sesión sobrantes (del semestre viejo, con más sesiones) ──
// corregirEncabezadosSesiones() solo RENOMBRA las primeras columnas — si la hoja vieja
// tenía más sesiones que la nueva (ej. 21 vs 15), las columnas de más quedan como basura
// entre las sesiones nuevas y "Promedio Final". Esto las borra de verdad.
function limpiarColumnasSesionesViejas() {
  const grupos = leerGrupos();
  const ultimaColSesion = 3 + SESIONES.length - 1; // última columna que SÍ debe quedar
  let limpiados = 0;
  grupos.forEach(g => {
    const filesControl = DriveApp.getFilesByName(g.control);
    if (!filesControl.hasNext()) {
      Logger.log(`${g.key}: no se encontró la hoja de Control (${g.control}), se salta.`);
      return;
    }
    const ss = SpreadsheetApp.open(filesControl.next());
    ['Control','Notas'].forEach(nombreHoja => {
      const sheet = ss.getSheetByName(nombreHoja);
      if (!sheet) return;
      const headers = sheet.getRange(1,1,1,sheet.getLastColumn()).getValues()[0];
      const colPromedio = headers.findIndex(h => String(h).includes('Promedio Final')) + 1; // 0 si no existe (Control no tiene)
      const colFinBorrar = colPromedio > 0 ? colPromedio - 1 : sheet.getLastColumn();
      if (colFinBorrar > ultimaColSesion) {
        sheet.deleteColumns(ultimaColSesion + 1, colFinBorrar - ultimaColSesion);
        Logger.log(`${g.key} / ${nombreHoja}: borradas ${colFinBorrar - ultimaColSesion} columnas sobrantes.`);
      } else {
        Logger.log(`${g.key} / ${nombreHoja}: no había columnas sobrantes, nada que borrar.`);
      }
    });
    limpiados++;
  });
  Logger.log(`limpiarColumnasSesionesViejas: ${limpiados} grupo(s) revisados.`);
}

function configurarNuevoSemestre() {
  const carpetaProyecto = obtenerCarpetaProyecto();
  const grupos = leerGrupos();
  const resumen = [];
  grupos.forEach(g => {
    let detalle = `${g.key} (${g.nombre}): `;

    const carpetas = DriveApp.getFoldersByName(g.carpeta);
    if (!carpetas.hasNext()) {
      carpetaProyecto.createFolder(g.carpeta);
      detalle += 'carpeta creada; ';
    } else {
      detalle += 'carpeta ya existía; ';
    }

    const filesGrab = DriveApp.getFilesByName(g.grabaciones);
    if (!filesGrab.hasNext()) {
      const ss = SpreadsheetApp.create(g.grabaciones);
      const sheet = ss.getSheets()[0];
      sheet.setName('Grabaciones');
      crearEncabezadosGrabaciones(sheet);
      moverArchivoACarpeta(ss.getId(), carpetaProyecto);
      detalle += 'hoja Grabaciones creada; ';
    } else {
      detalle += 'hoja Grabaciones ya existía; ';
    }

    const filesControl = DriveApp.getFilesByName(g.control);
    if (!filesControl.hasNext()) {
      const ss = SpreadsheetApp.create(g.control);
      const sheetControl = ss.getSheets()[0];
      sheetControl.setName('Control');
      crearEncabezadosControl(sheetControl, g.key);
      const sheetNotas = ss.insertSheet('Notas');
      crearEncabezadosNotas(sheetNotas, g.key);
      moverArchivoACarpeta(ss.getId(), carpetaProyecto);
      detalle += 'hoja Control+Notas creada.';
    } else {
      detalle += 'hoja Control ya existía.';
    }

    resumen.push(detalle);
    Logger.log(detalle);
  });
  Logger.log('\n=== RESUMEN ===\n' + resumen.join('\n'));
}

// Mueve un Sheet recién creado (que por defecto queda en la raíz de Mi unidad) a la
// carpeta del proyecto, para que no queden archivos sueltos.
function moverArchivoACarpeta(fileId, carpeta) {
  const archivo = DriveApp.getFileById(fileId);
  carpeta.addFile(archivo);
  DriveApp.getRootFolder().removeFile(archivo);
}

// ── Generar claves de 3 dígitos para estudiantes nuevos (los que llegaron sin clave) ──
// Correr manualmente desde el editor después de importar/pegar estudiantes nuevos en la hoja.
// ── Enviar correo de bienvenida con usuario/clave a todos los de la hoja maestra ──
// Usa tu propia cuenta de Google (GmailApp) — no necesita ningún servicio externo.
// Es seguro correrla varias veces: agrega una columna "CorreoEnviado" a la hoja y
// solo le manda a quien todavía no se le haya mandado, así si se corta a mitad de
// camino (por cuota diaria de Gmail, ~100/día en cuentas gratuitas) puedes volver a
// correrla después y sigue donde quedó, sin duplicar envíos.
function enviarCorreosEstudiantes() { enviarCorreosATodos('ESTUDIANTE'); }
function enviarCorreosProfesores() { enviarCorreosATodos('PROFESOR'); }
function enviarCorreosATodos(vinculoFiltro) {
  const files = DriveApp.getFilesByName(SHEET_ESTUDIANTES);
  if (!files.hasNext()) throw new Error('No se encontró la hoja maestra: ' + SHEET_ESTUDIANTES);
  const ss = SpreadsheetApp.open(files.next());
  const sheet = ss.getSheetByName('Estudiantes');
  if (!sheet || sheet.getLastRow() < 2) throw new Error('La hoja Estudiantes está vacía.');

  let headers = sheet.getRange(1,1,1,sheet.getLastColumn()).getValues()[0];
  let colEnviado = headers.indexOf('CorreoEnviado');
  if (colEnviado === -1) {
    // Se agrega sola la primera vez que corres esto — no hace falta que la crees a mano.
    colEnviado = headers.length;
    sheet.getRange(1, colEnviado+1).setValue('CorreoEnviado');
    headers = sheet.getRange(1,1,1,sheet.getLastColumn()).getValues()[0];
  }

  const colCed = headers.indexOf('Cedula');
  const colNom = headers.indexOf('Nombre');
  const colCor = headers.indexOf('Correo');
  const colCla = headers.indexOf('Clave');
  const colVin = headers.indexOf('Vinculo');
  if ([colCed,colNom,colCor,colCla].includes(-1)) {
    throw new Error('Faltan columnas esperadas en Estudiantes (Cedula, Nombre, Correo, Clave).');
  }

  const lastRow = sheet.getLastRow();
  const filas = sheet.getRange(2,1,lastRow-1,sheet.getLastColumn()).getValues();

  let enviados = 0, saltados = 0, fallidos = 0;
  filas.forEach((fila, i) => {
    const vinculo = colVin>=0 ? String(fila[colVin]||'ESTUDIANTE').trim().toUpperCase() : 'ESTUDIANTE';
    if (vinculoFiltro && vinculo !== vinculoFiltro) return;

    const yaEnviado = String(fila[colEnviado]||'').trim().toUpperCase() === 'SÍ';
    const correo = String(fila[colCor]||'').trim();
    if (yaEnviado || !correo) { saltados++; return; }

    const nombre = String(fila[colNom]||'').trim();
    const cedula = String(fila[colCed]||'').trim();
    const clave = String(fila[colCla]||'').trim();

    try {
      const asunto = 'Acceso a tu dashboard de seguimiento — Foné';
      const cuerpo = construirCuerpoCorreo(nombre, cedula, clave, vinculo);
      GmailApp.sendEmail(correo, asunto, '', { htmlBody: cuerpo, name: 'Foné' });
      sheet.getRange(i+2, colEnviado+1).setValue('Sí');
      enviados++;
    } catch (e) {
      Logger.log(`Error enviando a ${correo}: ${e.message}`);
      fallidos++;
    }
  });

  Logger.log(`enviarCorreosATodos(${vinculoFiltro}): ${enviados} enviados, ${saltados} saltados (ya tenían o sin correo), ${fallidos} fallidos.`);
}

function construirCuerpoCorreo(nombre, cedula, clave, vinculo) {
  const esProfesor = vinculo === 'PROFESOR';
  const saludo = esProfesor ? `Profe ${nombre.split(' ')[0]}` : nombre.split(' ')[0];
  const descripcion = esProfesor
    ? 'Foné analiza los audios que grabas cada viernes junto con los de tus estudiantes, y te deja ver el seguimiento del curso completo: quién ha cumplido, cómo va el vocabulario y la fluidez de cada uno, y alertas de estudiantes con posible riesgo académico.'
    : 'Cada viernes grabas un audio corto contando qué aprendiste esa semana. Foné lo analiza y te deja ver tus propias estadísticas — tu vocabulario, cumplimiento, y cómo vas comparado con el promedio del grupo.';

  return `
    <div style="font-family:Arial,sans-serif;font-size:14px;color:#222;line-height:1.6;max-width:560px;">
      <p>Hola ${saludo},</p>
      <p>${descripcion}</p>
      <p>Tus datos de acceso:</p>
      <table style="border-collapse:collapse;margin:12px 0;">
        <tr><td style="padding:4px 12px 4px 0;color:#555;">Cédula</td><td style="font-weight:bold;">${cedula}</td></tr>
        <tr><td style="padding:4px 12px 4px 0;color:#555;">Clave</td><td style="font-weight:bold;letter-spacing:2px;">${clave}</td></tr>
      </table>
      <p>
        🎙️ <a href="${URL_INDEX}">Grabar tu audio</a><br/>
        📊 <a href="${URL_DASHBOARD}">Ver tu dashboard</a>
      </p>
      <p style="color:#666;font-size:13px;">
        El proyecto sigue en desarrollo y se sigue actualizando — si algo no te queda claro,
        ves un dato raro, o se te ocurre algo que le haría falta, cuéntame.<br/>
        Esta información es personal — por favor no compartas tu clave.
      </p>
      <p>Cualquier duda me escribes.</p>
    </div>`;
}

function generarClavesFaltantes() {
  const files = DriveApp.getFilesByName(SHEET_ESTUDIANTES);
  if (!files.hasNext()) throw new Error('No se encontró la hoja maestra de estudiantes: ' + SHEET_ESTUDIANTES);
  const ss = SpreadsheetApp.open(files.next());
  const sheet = ss.getSheetByName('Estudiantes');
  if (!sheet || sheet.getLastRow() < 2) return;
  const headers = sheet.getRange(1,1,1,sheet.getLastColumn()).getValues()[0];
  const colCla = headers.indexOf('Clave') + 1;
  if (colCla === 0) throw new Error('No se encontró la columna Clave.');

  const lastRow = sheet.getLastRow();
  const claves = sheet.getRange(2, colCla, lastRow-1, 1).getValues().map(r => String(r[0]).trim());
  const usadas = new Set(claves.filter(Boolean));
  // Alfanumérico, 3 caracteres, sin 0/O/1/I para evitar confusión visual al leerlas.
  const ALFABETO = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  const generarCodigo = () => Array.from({length:3}, () => ALFABETO[Math.floor(Math.random()*ALFABETO.length)]).join('');
  let generadas = 0;
  for (let i = 0; i < claves.length; i++) {
    if (claves[i]) continue; // ya tiene clave, no se toca
    let nueva;
    do { nueva = generarCodigo(); } while (usadas.has(nueva));
    usadas.add(nueva);
    sheet.getRange(i+2, colCla).setValue(nueva);
    generadas++;
  }
  Logger.log(`generarClavesFaltantes: ${generadas} claves nuevas generadas (de ${claves.length} estudiantes)`);
}

// Sesiones
const SESIONES = [
  '24/07/2026','31/07/2026','07/08/2026','14/08/2026','21/08/2026','28/08/2026',
  '04/09/2026','11/09/2026','18/09/2026','25/09/2026','02/10/2026','16/10/2026',
  '23/10/2026','30/10/2026','06/11/2026'
];
// Sesiones que SÍ quedan en la hoja (para seguir registrando envíos) pero que NO cuentan
// en el promedio final. Vacío por ahora — la exclusión del semestre anterior (S1 sin nota)
// ya no aplica, esa fecha ni siquiera existe en el semestre nuevo. Si alguna sesión de este
// semestre no debe contar, agrega su fecha aquí (formato 'dd/MM/yyyy').
const SESIONES_EXCLUIDAS_PROMEDIO = [];

function doGet(e) {
  try {
    const action = e.parameter.action;

    // Login de estudiante para VER el dashboard — pide cédula + clave, sin grupo previo.
    if (action === 'loginEstudiante') {
      return json(validarLoginEstudiante(e.parameter.cedula, e.parameter.clave));
    }
    // Verificación de estudiante para GRABAR — solo cédula, sin clave (bajo riesgo, no expone datos).
    if (action === 'buscarCedula') {
      return json(buscarGruposDeCedula(e.parameter.cedula));
    }

    // Panel nuevo del profesor: valida cédula + clave y devuelve los datos.
    if (action === 'getPanel' || action === 'getPanelTr' || action === 'getPanelTx' || action === 'getNotas') {
      const prof = profesorValido_(e.parameter.cedula, e.parameter.clave);
      if (!prof) return json({ ok: false, error: 'Cédula o clave incorrecta, o esta cuenta no es de profesor.' });
      const texto = action === 'getNotas' ? notasProfesorTexto_(prof.cedula)
                  : (action === 'getPanel' ? panelProfesorTextos_(prof.cedula).main
                      : action === 'getPanelTx' ? panelProfesorTextos_(prof.cedula).tx : panelProfesorTextos_(prof.cedula).tr);
      return ContentService.createTextOutput(texto).setMimeType(ContentService.MimeType.JSON);
    }

    // Sesiones enviadas por cédula
    const cedula = e.parameter.cedula;
    const grupoKey = e.parameter.grupo;
    if (!cedula || !grupoKey) return json({ ok: false, error: 'Faltan parámetros' });

    const nombreSheet = grupoPorKey(grupoKey).control;
    const files = DriveApp.getFilesByName(nombreSheet);
    if (!files.hasNext()) return json({ ok: true, enviadas: [] });

    const ss = SpreadsheetApp.open(files.next());
    const sheet = ss.getSheetByName('Control');
    if (!sheet) return json({ ok: true, enviadas: [] });

    const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    const cedulasSheet = sheet.getRange(2, 1, sheet.getLastRow()-1, 1).getValues().flat().map(String);
    const fila = cedulasSheet.indexOf(cedula) + 2;
    if (fila === 1) return json({ ok: true, enviadas: [] });

    const enviadas = [];
    SESIONES.forEach(s => {
      const col = headers.findIndex(h => String(h).includes(s)) + 1;
      if (col > 0) {
        const val = sheet.getRange(fila, col).getValue();
        if (val && String(val).trim() !== '') enviadas.push(s);
      }
    });

    return json({ ok: true, enviadas });
  } catch(err) {
    return json({ ok: false, error: err.message });
  }
}

function json(data) {
  return ContentService.createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

// ── Entry point POST ──
function doPost(e) {
  let p = null; // declarado afuera del try para que el catch pueda usarlo en registrarErrorAudio
  try {
    p = JSON.parse(e.postData.contents);
    // El servidor valida la cédula y la clave de quien envía el audio; la página no es suficiente
    // porque la URL del Apps Script es pública.
    const login = validarLoginEstudiante(p.cedula, p.clave);
    if (!login.ok) return json({ ok: false, error: 'Cédula o clave incorrecta.' });
    delete p.clave; // la clave no se guarda ni se registra
    const grupoKey = getGrupoKey(p.grupo);
    if (login.grupos.indexOf(grupoKey) < 0) return json({ ok: false, error: 'Esta cédula no pertenece a ese curso.' });

    // Respaldo del filtro que ya existe en el frontend (index.html no debería ni siquiera
    // ofrecer sesiones futuras como opción) — si por lo que sea llega una petición para una
    // sesión cuya fecha todavía no pasa, se rechaza aquí. Sin este chequeo, un envío así
    // terminaba con nota automática 5.0 (diasDespues<=0) para una clase que no había ocurrido.
    if (p.sesion) {
      const [d,m,y] = p.sesion.split('/');
      const sesionUTC = Date.UTC(Number(y), Number(m)-1, Number(d));
      const hoyBogStr = Utilities.formatDate(new Date(), 'America/Bogota', 'yyyy-MM-dd');
      const [hy,hm,hd] = hoyBogStr.split('-').map(Number);
      const hoyUTC = Date.UTC(hy, hm-1, hd);
      if (sesionUTC > hoyUTC) {
        return json({ ok:false, error:'Todavía no puedes enviar el audio de la sesión '+p.sesion+' — esa clase no ha pasado.' });
      }
    }

    // Validación en servidor de la regla "primero el audio pendiente más antiguo" (antes solo
    // la aplicaba el index.html). Si la consulta falla por un error técnico NO bloquea el envío.
    if (p.sesion && p.cedula) {
      let pend = null;
      try { pend = pendientesDe_(String(p.cedula), grupoKey); } catch (errPend) { pend = null; }
      if (pend && pend.length > 0 && pend[0] !== p.sesion) {
        return json({ ok:false, error:'Debes ' + pend.length + ' audio' + (pend.length>1?'s':'') + ' pendiente' + (pend.length>1?'s':'') + '. Primero envía el de la sesión ' + pend[0] + '.' });
      }
    }

    // 1. Nombre del archivo de audio
    const nombreArchivo = generarNombreArchivo(p, grupoKey);

    // 2. Subir audio a carpeta del grupo -- PRIMERO, antes de intentar transcribir.
    //    Esto casi nunca falla (es solo escribir un archivo a Drive). Si algo falla
    //    despues, el audio del estudiante ya queda a salvo -- no se pierde ni hay que
    //    pedirle que vuelva a grabar (antes, un fallo del
    //    transcriptor abortaba todo el envio, incluida la subida del audio).
    const driveUrl = subirADrive(p.fileBase64, p.fileType, nombreArchivo, grupoKey);

    // 3. El audio solo se guarda en Drive: la transcripcion se hace despues, en el analisis local.
    let transcripcion = '', segments = [];
    const transcripcionPendiente = true;
    // calcularVariables('', ...) con transcripcion vacia deja las variables derivadas en 0 (placeholder valido).
    vars = calcularVariables(transcripcion, p.fileName, p.duracion_segundos || 0, segments);

    // 4. Guardar en Sheets de grabaciones (con o sin transcripcion)
    const sheetUrl = guardarGrabacion(p, vars, driveUrl, grupoKey, transcripcion);

    // 5. Actualizar control de asistencia (estudiantes y profesores) -- el estudiante SI
    //    cumplio con enviar el audio de esta sesion, independientemente de la transcripcion.
    actualizarControl(p, grupoKey);

    return json({ ok: true, driveUrl, sheetUrl, ...vars, transcripcionPendiente });

  } catch(err) {
    registrarErrorAudio(p, err.message);
    return json({ ok: false, error: err.message });
  }
}

// Las Ejecuciones de Apps Script son difíciles de leer/encontrar a mano (todo aparece como
// "Completada" aunque haya un error interno, porque el try/catch de arriba lo atrapa). Esta
// función deja un registro de cada envío de audio que falló directamente en una pestaña de
// la hoja maestra, para poder abrirla como cualquier Excel en vez de bucear en logs.
function registrarErrorAudio(p, mensaje) {
  try {
    const files = DriveApp.getFilesByName(SHEET_ESTUDIANTES);
    if (!files.hasNext()) return;
    const ss = SpreadsheetApp.open(files.next());
    let sheet = ss.getSheetByName('ErroresAudio');
    if (!sheet) {
      sheet = ss.insertSheet('ErroresAudio');
      sheet.appendRow(['Fecha', 'Cedula', 'Grupo', 'Sesion', 'FileType', 'Bytes (aprox.)', 'Error']);
    }
    // Tamaño aproximado del archivo original a partir del largo del base64 (base64 codifica
    // 3 bytes en 4 caracteres) — suficiente para ver si el audio llegó vacío o truncado,
    // sin tener que decodificarlo de nuevo solo para loguear el error.
    const bytesAprox = (p && p.fileBase64) ? Math.round(p.fileBase64.length * 3 / 4) : '';
    sheet.appendRow([
      Utilities.formatDate(new Date(), 'America/Bogota', 'dd/MM/yyyy HH:mm:ss'),
      p ? (p.cedula || '') : '',
      p ? (p.grupo || '') : '',
      p ? (p.sesion || '') : '',
      p ? (p.fileType || '') : '',
      bytesAprox,
      mensaje || '',
    ]);
  } catch (e2) {
    // Si falla el registro (ej. la hoja no existe todavía), no debe tapar el error real
    // que ya se le está devolviendo al estudiante — se ignora en silencio.
  }
}

// ── Nombre del archivo ──
function generarNombreArchivo(p, grupoKey) {
  const fecha = p.sesion.replace(/\//g, '');           // 09062026
  const sesionNum = 'S' + getSesionNum(p.sesion);      // S1
  const materia = grupoPorKey(grupoKey).materia;
  const identificador = nombreDeEstudiante(p.cedula); // profesor y estudiante viven en el mismo roster
  const ext = getExt(p.fileType); // .webm en Chrome/Android, .m4a en Safari/iOS, etc.
  return `${fecha}_${sesionNum}_${materia}_${identificador}${ext}`;
}

function getSesionNum(sesionFecha) {
  const idx = SESIONES.indexOf(sesionFecha);
  return idx >= 0 ? idx + 1 : '?';
}

// Resuelve el grupoKey a partir del nombre completo del grupo (ej. el valor que llega
// del frontend en p.grupo), buscando en la hoja Grupos en vez de comparar contra nombres fijos.
function getGrupoKey(grupoNombre) {
  const grupos = leerGrupos();
  const exacto = grupos.find(g => g.nombre === grupoNombre);
  if (exacto) return exacto.key;
  const parcial = grupos.find(g => grupoNombre.includes(g.nombre) || g.nombre.includes(grupoNombre));
  if (parcial) return parcial.key;
  throw new Error('No se pudo identificar el grupo: ' + grupoNombre);
}

// ── Diccionarios de conteo léxico — constantes compartidas entre calcularVariables()
// y el backfill (recalcularVariablesTexto), para que nunca queden desincronizados. ──

// Muletillas: palabras de relleno sin contenido proposicional. Se dejan fuera "bueno",
// "vale", "entonces", "mira", "oye" a propósito — son también palabras con uso gramatical
// legítimo y muy frecuente (bueno=adjetivo, vale=verbo valer, entonces=conector causal real),
// así que incluirlas dispararía muchos falsos positivos.
const MULETILLAS = ['eh','ehh','eeh','ah','em','emm','ehm','este','mmm','mmmm',
  'pues','osea','o sea','o sea que','digamos','aja','tipo'];

// Dudas: SOLO hedges epistémicos (expresan la incertidumbre del hablante sobre lo que dice).
// Se removieron 'dificil','difisil','complicado','confuso' — describen el tema, no la
// certeza del hablante; una respuesta puede ser correcta y aun así mencionar que el tema es difícil.
// Se usan raíces (*) para cubrir conjugaciones: 'no sab*' agarra sabía/sabemos/sabe,
// no solo 'no sé'. Las raíces se eligieron con cuidado para no ser tan cortas que
// enganchen palabras sin relación (evitar 'pens*' solo, por ejemplo).
const DUDAS = ['no se','nose','no sab*','no recuerd*','no record*','no me acuerdo',
  'no me acord*',
  'no comprendi','no comprend*','no capte','no capt*','no entendi','no entend*',
  'no logre entender','no logro entender','no logr* entender',
  'creo','creo que','creia','creiamos','pienso que','pensaba que','supongo','supon*',
  'imagino','imagin*','me parece','me parece que','nos parece','tal vez','talvez',
  'quizas','quiza','posiblemente','puede ser','puede que','no estoy seguro','no estoy segura',
  'no estaba seguro','no estaba segura','no estamos seguros','mas o menos','algo asi',
  'la verdad no se','honestamente no se','en realidad no se'];

// Percepción de dificultad del tema — se separa de 'dudas' porque mide algo distinto
// (qué tan difícil percibe el tema, no qué tan seguro está de su propia respuesta).
// Raíces: 'dificult*' agarra dificultó/dificulta/dificultad/dificultan (el caso que
// originalmente no se detectaba: "se me dificultó").
const PERCEPCION_DIFICULTAD = ['dificil*','dificult*','difisil','complic*','complej*',
  'confund*','confus*','se me complica','no le entiendo bien al tema',
  'cuesta entender','me cuesta','se me cuesta',
  // Agregado tras auditar 72 transcripciones reales del corpus:
  // sinonimos reales de dificultad que la lista original
  // no capturaba, encontrados repetidos en mas de un curso. 'duro*' se probo y se
  // descarto a proposito -- es ambiguo ("meterle duro" = esfuerzo, no dificultad).
  'pesad*','abrumador*','me cost*','nos cost*','le cost*',
  'me siento perdid*','estoy perdid*'];

const NEGACIONES = ['no','nunca','jamas','nada','tampoco','ni','ningun*'];

// ── Variables lingüísticas ──
function calcularVariables(texto, archivo, duracion, segments) {
  const limpio = limpiarTexto(texto);
  const tokens = limpio.split(' ').filter(Boolean);
  const n = tokens.length;
  const unicas = new Set(tokens).size;
  const riqueza = n > 0 ? unicas / n : 0;
  const promLon = n > 0 ? tokens.reduce((s,t) => s+t.length, 0) / n : 0;
  const freq = {};
  tokens.forEach(t => { freq[t] = (freq[t]||0)+1; });
  const sorted = Object.entries(freq).sort((a,b) => b[1]-a[1]);
  const top5 = sorted.slice(0,5).map(([p,c]) => p+':'+c).join(', ');
  const raras = Object.values(freq).filter(c=>c===1).length;
  const pctRaras = Object.keys(freq).length > 0 ? raras/Object.keys(freq).length : 0;

  const cMul = contarLista(limpio, MULETILLAS);
  const cDud = contarLista(limpio, DUDAS);
  const cNeg = contarLista(limpio, NEGACIONES);
  const cDif = contarListaSinNegacion(limpio, PERCEPCION_DIFICULTAD);

  // Velocidad de habla (De Jong et al.: tasa de articulación es predictor fuerte de
  // "adecuación funcional" del habla, junto con pausas y repeticiones).
  const palabrasPorMinuto = duracion > 0 ? round4(n / (duracion/60)) : 0;

  // Repeticiones/autocorrecciones: mismo token dicho dos veces seguidas ("la, la derivada").
  // Distinto de muletillas — aquí es contenido real repetido, no palabras de relleno.
  let cRep = 0;
  for (let i = 1; i < tokens.length; i++) { if (tokens[i] === tokens[i-1]) cRep++; }
  const frecRep = n > 0 ? round4(cRep/n) : 0;

  // Pausas: gaps entre segmentos consecutivos que el transcriptor devuelve con response_format=verbose_json.
  // Es una aproximación a nivel de segmento (no de palabra), pero es lo que entrega el transcriptor.
  const UMBRAL_PAUSA = 0.3; // segundos; gaps menores se consideran parte del habla normal
  let numPausas = 0, duracionPausas = 0;
  if (segments && segments.length > 1) {
    for (let i = 1; i < segments.length; i++) {
      const gap = segments[i].start - segments[i-1].end;
      if (gap > UMBRAL_PAUSA) { numPausas++; duracionPausas += gap; }
    }
  }
  const pausaPromedio = numPausas > 0 ? round4(duracionPausas/numPausas) : 0;

  return {
    texto, archivo,
    num_palabras: n, num_caracteres: limpio.length,
    palabras_unicas: unicas, riqueza_lexica: round4(riqueza),
    promedio_longitud_palabra: round4(promLon),
    palabra_mas_repetida: sorted.length>0 ? sorted[0][0] : '',
    frecuencia_palabra_top: sorted.length>0 ? sorted[0][1] : 0,
    top_5_palabras: top5,
    conteo_muletillas: cMul, frecuencia_muletillas: round4(n>0?cMul/n:0),
    conteo_dudas: cDud, frecuencia_dudas: round4(n>0?cDud/n:0),
    conteo_negaciones: cNeg, frecuencia_negaciones: round4(n>0?cNeg/n:0),
    conteo_percepcion_dificultad: cDif, frecuencia_percepcion_dificultad: round4(n>0?cDif/n:0),
    porcentaje_palabras_raras: round4(pctRaras), duracion_segundos: duracion,
    palabras_por_minuto: palabrasPorMinuto,
    conteo_repeticiones: cRep, frecuencia_repeticiones: frecRep,
    num_pausas: numPausas, duracion_pausas_total: round4(duracionPausas), pausa_promedio: pausaPromedio,
  };
}

function limpiarTexto(texto) {
  return texto.toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g,'')
    .replace(/[^a-z\s]/g,' ').replace(/\s+/g,' ').trim();
}

// Cuenta ocurrencias de cada entrada de `lista` en `texto`. Las palabras que terminan en '*'
// se tratan como raíz (ej. 'dificult*' coincide con dificultó, dificulta, dificultad,
// dificultan...) — necesario porque el español conjuga y flexiona muchísimo, y una lista
// de coincidencia exacta se queda corta rapidísimo.
function contarLista(texto, lista) {
  return lista.reduce((acc,frase) => {
    const partes = frase.split(' ').map(palabra =>
      palabra.endsWith('*') ? palabra.slice(0,-1)+'\\w*' : palabra
    );
    const cierre = frase.endsWith('*') ? '' : '\\b';
    const re = new RegExp('\\b'+partes.join('\\s+')+cierre, 'g');
    return acc+(texto.match(re)||[]).length;
  }, 0);
}

// Igual que contarLista, pero descarta las coincidencias que vienen negadas justo antes
// (dentro de una ventana de palabras) — ej. "no tengo dificultad" NO debe contar como
// que sí tuvo dificultad, aunque la palabra "dificultad" esté literalmente ahí. Sin esto,
// una negación simple invierte el sentido pero el conteo por substring no se entera.
const NEGADORES_PREVIOS = ['no','nunca','jamas','tampoco','ni','sin'];
function contarListaSinNegacion(texto, lista, ventana) {
  ventana = ventana || 3;
  let count = 0;
  lista.forEach(frase => {
    const partes = frase.split(' ').map(palabra =>
      palabra.endsWith('*') ? palabra.slice(0,-1)+'\\w*' : palabra
    );
    const cierre = frase.endsWith('*') ? '' : '\\b';
    const re = new RegExp('\\b'+partes.join('\\s+')+cierre, 'g');
    let m;
    while ((m = re.exec(texto)) !== null) {
      const antes = texto.slice(0, m.index).trim().split(/\s+/).slice(-ventana);
      const negado = antes.some(p => NEGADORES_PREVIOS.includes(p));
      if (!negado) count++;
    }
  });
  return count;
}

function round4(n) { return Math.round(n*10000)/10000; }

// Firma mínima de contenedor de audio esperado: se encontraron
// 78/801 audios del semestre guardados en Drive con bytes irreconocibles desde el byte 0 (ni
// EBML ni ftyp), causa exacta sin confirmar. Apps Script no tiene ffmpeg para decodificar de
// verdad, así que esto NO prueba que el audio suene bien -- solo descarta el caso ya
// confirmado: que lo guardado no sea ni remotamente un contenedor de audio válido. Es
// deliberadamente permisivo (varios formatos, tolera MIME mal declarado) para no rechazar
// audios sanos por error.
function esContenedorAudioValido(bytes) {
  if (!bytes || bytes.length < 500) return false; // vacío/truncado a las claras
  // Apps Script entrega bytes CON SIGNO (-128..127): se normalizan a 0..255.
  // Se busca la firma en los primeros 4096 bytes (no solo en el byte 0), porque hay audios
  // completos con basura antepuesta que luego se recuperan con demux.
  const n = Math.min(bytes.length, 4096);
  const b = [];
  for (let i = 0; i < n; i++) b.push(bytes[i] & 0xFF);
  for (let i = 0; i + 8 <= n; i++) {
    // WebM/Matroska (Chrome/Android): EBML
    if (b[i]===0x1A && b[i+1]===0x45 && b[i+2]===0xDF && b[i+3]===0xA3) return true;
    // MP4/M4A (Safari/iOS): 'ftyp'
    if (b[i+4]===0x66 && b[i+5]===0x74 && b[i+6]===0x79 && b[i+7]===0x70) return true;
    // AAC crudo (ADTS)
    if (b[i]===0xFF && (b[i+1] & 0xF0)===0xF0 && i < 8) return true;
  }
  // Ogg (OggS) / WAV (RIFF) / MP3 (ID3)
  const t = String.fromCharCode(b[0], b[1], b[2], b[3]);
  if (t === 'OggS' || t === 'RIFF' || t.slice(0,3) === 'ID3') return true;
  return false;
}

// Sesiones ya pasadas (o de hoy, hora Bogotá) que la cédula todavía no ha enviado, de la más antigua a la más reciente.
function pendientesDe_(cedula, grupoKey) {
  const files = DriveApp.getFilesByName(grupoPorKey(grupoKey).control);
  if (!files.hasNext()) return null;
  const sheet = SpreadsheetApp.open(files.next()).getSheetByName('Control');
  if (!sheet || sheet.getLastRow() < 2) return null;
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const ceds = sheet.getRange(2, 1, sheet.getLastRow()-1, 1).getValues().flat().map(String);
  const idx = ceds.indexOf(cedula);
  if (idx < 0) return null; // cédula no está en Control: no se puede juzgar, no bloquea
  const fila = idx + 2;
  const hoyBog = Utilities.formatDate(new Date(), 'America/Bogota', 'yyyy-MM-dd');
  const pend = [];
  SESIONES.forEach(s => {
    const [d,m,y] = s.split('/');
    if (y + '-' + m + '-' + d > hoyBog) return;
    const col = headers.findIndex(h => String(h).includes(s)) + 1;
    const val = col > 0 ? sheet.getRange(fila, col).getValue() : '';
    if (!(val && String(val).trim() !== '')) pend.push(s);
  });
  return pend;
}

// ── Subir audio a Drive ──
function subirADrive(fileBase64, fileType, nombreArchivo, grupoKey) {
  const decoded = Utilities.base64Decode(fileBase64);
  if (decoded.length < 500) {
    throw new Error('El audio llegó vacío o incompleto al servidor. Por favor, graba y envía de nuevo.');
  }
  if (!esContenedorAudioValido(decoded)) {
    // Ya NO se rechaza al estudiante: el audio se guarda igual (con sufijo _SINFIRMA y los primeros
    // bytes en el log) para poder diagnosticarlo/recuperarlo. Rechazar bloqueaba envíos legítimos.
    var hex = []; for (var q = 0; q < 16 && q < decoded.length; q++) hex.push(('0' + (decoded[q] & 0xFF).toString(16)).slice(-2));
    Logger.log('AUDIO SIN FIRMA CONOCIDA tipo=' + fileType + ' len=' + decoded.length + ' bytes0-15=' + hex.join(' ') + ' archivo=' + nombreArchivo);
    nombreArchivo = String(nombreArchivo).replace(/(\.[A-Za-z0-9]+)?$/, '_SINFIRMA$1');
  }
  const blob = Utilities.newBlob(decoded, fileType||'audio/webm', nombreArchivo);
  const carpetaNombre = grupoPorKey(grupoKey).carpeta;
  const carpetas = DriveApp.getFoldersByName(carpetaNombre);
  const carpeta = carpetas.hasNext() ? carpetas.next() : DriveApp.createFolder(carpetaNombre);
  const file = carpeta.createFile(blob);
  // El archivo hereda los permisos privados de la carpeta del curso (no se comparte por enlace).
  return file.getUrl();
}

// ── Guardar grabación en Sheets ──
function guardarGrabacion(p, vars, driveUrl, grupoKey, transcripcion) {
  const nombreSheet = grupoPorKey(grupoKey).grabaciones;
  const files = DriveApp.getFilesByName(nombreSheet);
  const ss = files.hasNext() ? SpreadsheetApp.open(files.next()) : SpreadsheetApp.create(nombreSheet);
  let sheet = ss.getSheetByName('Grabaciones');
  if (!sheet) { sheet = ss.getActiveSheet(); sheet.setName('Grabaciones'); }
  if (sheet.getLastRow() === 0) crearEncabezadosGrabaciones(sheet);

  // Dos columnas reservadas (sin uso): se conservan para no mover las demás columnas de la hoja.
  const reservada1 = 0;
  const reservada2 = '';

  const fecha = new Date().toLocaleString('es-CO', { timeZone: 'America/Bogota' });
  sheet.appendRow([
    fecha, p.grupo, p.sesion, p.cedula, p.es_profesor ? 'SÍ' : 'NO',
    vars.num_palabras, vars.num_caracteres, vars.palabras_unicas,
    vars.riqueza_lexica, vars.promedio_longitud_palabra,
    vars.palabra_mas_repetida, vars.frecuencia_palabra_top, vars.top_5_palabras,
    vars.conteo_muletillas, vars.frecuencia_muletillas,
    vars.conteo_dudas, vars.frecuencia_dudas,
    vars.conteo_negaciones, vars.frecuencia_negaciones,
    vars.porcentaje_palabras_raras, vars.duracion_segundos,
    transcripcion, driveUrl,
    reservada1, reservada2,
    vars.palabras_por_minuto, vars.conteo_repeticiones, vars.frecuencia_repeticiones,
    vars.num_pausas, vars.duracion_pausas_total, vars.pausa_promedio,
    vars.conteo_percepcion_dificultad, vars.frecuencia_percepcion_dificultad
  ]);
  return ss.getUrl();
}

function crearEncabezadosGrabaciones(sheet) {
  const headers = [
    'Fecha','Grupo','Sesion','Cedula','Es_Profesor',
    'num_palabras','num_caracteres','palabras_unicas',
    'riqueza_lexica','promedio_longitud_palabra',
    'palabra_mas_repetida','frecuencia_palabra_top','top_5_palabras',
    'conteo_muletillas','frecuencia_muletillas',
    'conteo_dudas','frecuencia_dudas',
    'conteo_negaciones','frecuencia_negaciones',
    'porcentaje_palabras_raras','duracion_segundos',
    'Transcripcion','Audio (Drive)',
    'columna_reservada_1','columna_reservada_2',
    'palabras_por_minuto','conteo_repeticiones','frecuencia_repeticiones',
    'num_pausas','duracion_pausas_total','pausa_promedio',
    'conteo_percepcion_dificultad','frecuencia_percepcion_dificultad'
  ];
  const r = sheet.getRange(1,1,1,headers.length);
  r.setValues([headers]);
  r.setBackground('#0d1524'); r.setFontColor('#ffffff'); r.setFontWeight('bold');
  sheet.setFrozenRows(1);
  sheet.setColumnWidth(22, 500);
}

// ── Control de asistencia ──
function actualizarControl(p, grupoKey) {
  const nombreSheet = grupoPorKey(grupoKey).control;
  const files = DriveApp.getFilesByName(nombreSheet);
  const ss = files.hasNext() ? SpreadsheetApp.open(files.next()) : SpreadsheetApp.create(nombreSheet);

  // ── Hoja 1: Control (fechas de envío) ──
  let sheet = ss.getSheetByName('Control');
  if (!sheet) { sheet = ss.getActiveSheet(); sheet.setName('Control'); }
  if (sheet.getLastRow() === 0) crearEncabezadosControl(sheet, grupoKey);

  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  let colSesion = headers.findIndex(h => String(h).includes(p.sesion)) + 1;
  if (colSesion === 0) return;

  const ahora = new Date();
  const cedulasSheet = sheet.getRange(2, 1, sheet.getLastRow()-1, 1).getValues().flat().map(String);
  let fila = cedulasSheet.indexOf(p.cedula) + 2;
  if (fila > 1) {
    const ahoraStr = Utilities.formatDate(ahora, 'America/Bogota', 'dd/MM/yyyy HH:mm');
    sheet.getRange(fila, colSesion).setValue(ahoraStr);
    sheet.getRange(fila, colSesion).setBackground('#d4edda');
  }

  // ── Hoja 2: Notas ──
  let sheetNotas = ss.getSheetByName('Notas');
  if (!sheetNotas) {
    sheetNotas = ss.insertSheet('Notas');
    crearEncabezadosNotas(sheetNotas, grupoKey);
  }

  const headersN = sheetNotas.getRange(1, 1, 1, sheetNotas.getLastColumn()).getValues()[0];
  let colN = headersN.findIndex(h => String(h).includes(p.sesion)) + 1;
  if (colN === 0) return;

  // Fila: estudiante o profesor
  const cedulasN = sheetNotas.getRange(2, 1, sheetNotas.getLastRow()-1, 1).getValues().flat().map(String);
  let filaN = cedulasN.indexOf(p.cedula) + 2;
  if (filaN === 1) return;

  // Nota según cuántos días después de la sesión (siempre viernes) se envía:
  // mismo día (viernes) = 5.0; sábado hasta el límite del grupo (lunes por defecto,
  // martes para Métodos Numéricos) = 3.0; después = 1.0.
  // (Si nunca se envía, la celda se queda en el 0.0 con el que arranca la hoja — eso ya
  // no requiere lógica aquí, solo pasa cuando esta función nunca se ejecuta para esa sesión.)
  const ahoraBogStr = Utilities.formatDate(ahora, 'America/Bogota', 'yyyy-MM-dd');
  const [d,m,y] = p.sesion.split('/');
  const sesionUTC = Date.UTC(Number(y), Number(m)-1, Number(d));
  const [ay,am,ad] = ahoraBogStr.split('-').map(Number);
  const ahoraUTC = Date.UTC(ay, am-1, ad);
  const diasDespues = Math.round((ahoraUTC - sesionUTC) / (1000*60*60*24));
  const limite3 = grupoPorKey(grupoKey).limite3; // 3 = hasta el lunes, 4 = hasta el martes, etc.

  let nota, color;
  if (diasDespues <= 0)          { nota = 5.0; color = '#d4edda'; } // el mismo viernes (o antes, por si acaso)
  else if (diasDespues <= limite3) { nota = 3.0; color = '#fff3cd'; } // sábado...hasta el límite del grupo
  else                             { nota = 1.0; color = '#fde8e8'; } // después del límite

  sheetNotas.getRange(filaN, colN).setValue(nota);
  sheetNotas.getRange(filaN, colN).setBackground(color);
  sheetNotas.getRange(filaN, colN).setFontColor('#000000');

  // Recalcular promedio final — la columna se busca por nombre, no por aritmética,
  // para que funcione igual en hojas ya creadas con un número distinto de sesiones.
  // Las sesiones en SESIONES_EXCLUIDAS_PROMEDIO no suman ni entran al divisor (ej. S1 sin nota).
  const colPromedio = headersN.findIndex(h => String(h).includes('Promedio Final')) + 1;
  if (colPromedio === 0) return;
  const numSesiones = SESIONES.length;
  const notasRow = sheetNotas.getRange(filaN, 3, 1, numSesiones).getValues()[0];
  let suma = 0, contadas = 0;
  SESIONES.forEach((fechaSesion, idx) => {
    if (SESIONES_EXCLUIDAS_PROMEDIO.includes(fechaSesion)) return;
    suma += Number(notasRow[idx]) || 0;
    contadas++;
  });
  const promedio = contadas > 0 ? suma / contadas : 0;
  sheetNotas.getRange(filaN, colPromedio).setValue(Math.round(promedio*100)/100);
  sheetNotas.getRange(filaN, colPromedio).setBackground('#e8f0fe');
  sheetNotas.getRange(filaN, colPromedio).setFontWeight('bold');
}

function crearEncabezadosNotas(sheet, grupoKey) {
  const estudiantes = estudiantesDeGrupo(grupoKey);
  const profCedula = grupoPorKey(grupoKey).profesor;
  const profNombre = nombreDeEstudiante(profCedula);

  const headers = ['Cédula', 'Nombre'];
  SESIONES.forEach((s, i) => { headers.push('A'+(i+1)+'\n'+s); });
  headers.push('Promedio Final');

  const r = sheet.getRange(1, 1, 1, headers.length);
  r.setValues([headers]);
  r.setBackground('#0d1524'); r.setFontColor('#ffffff'); r.setFontWeight('bold');
  sheet.setFrozenRows(1);
  sheet.setFrozenColumns(2);
  sheet.setRowHeight(1, 40);

  // Fila del profesor (primero, destacada)
  sheet.getRange(2, 1).setValue(profCedula);
  sheet.getRange(2, 2).setValue('👨‍🏫 ' + profNombre.replace('_', ', '));
  sheet.getRange(2, 1, 1, 2).setBackground('#0d1a3a').setFontColor('#60a5fa').setFontWeight('bold');
  for (let c = 0; c < SESIONES.length; c++) {
    sheet.getRange(2, 3+c).setValue(0.0);
    sheet.getRange(2, 3+c).setBackground('#1a2a4a');
    sheet.getRange(2, 3+c).setFontColor('#5a7a9e');
  }
  sheet.getRange(2, 3+SESIONES.length).setValue(0.0);
  sheet.getRange(2, 3+SESIONES.length).setBackground('#0d1a3a').setFontWeight('bold').setFontColor('#60a5fa');

  // Filas de estudiantes
  estudiantes.forEach((est, i) => {
    const fila = i + 3; // +3 porque fila 1 = encabezado, fila 2 = profesor
    sheet.getRange(fila, 1).setValue(est.cedula);
    sheet.getRange(fila, 2).setValue(est.nombre);
    for (let c = 0; c < SESIONES.length; c++) {
      sheet.getRange(fila, 3+c).setValue(0.0);
      sheet.getRange(fila, 3+c).setBackground('#f5f5f5');
      sheet.getRange(fila, 3+c).setFontColor('#aaaaaa');
    }
    sheet.getRange(fila, 3+SESIONES.length).setValue(0.0);
    sheet.getRange(fila, 3+SESIONES.length).setBackground('#e8f0fe').setFontWeight('bold');
  });

  // Anchos
  sheet.setColumnWidth(1, 130);
  sheet.setColumnWidth(2, 180);
  for (let c = 3; c <= headers.length; c++) sheet.setColumnWidth(c, 100);
  sheet.setColumnWidth(headers.length, 130);

  // Leyenda
  const filaLey = estudiantes.length + 4;
  sheet.getRange(filaLey, 1).setValue('Leyenda:').setFontWeight('bold');
  sheet.getRange(filaLey+1, 1, 4, 2).setValues([
    ['5.0','Enviado el mismo día'],
    ['3.0','Enviado al día siguiente'],
    ['1.0','Enviado después'],
    ['0.0','No enviado'],
  ]);
  sheet.getRange(filaLey+1,1).setBackground('#d4edda');
  sheet.getRange(filaLey+2,1).setBackground('#fff3cd');
  sheet.getRange(filaLey+3,1).setBackground('#fde8e8');
  sheet.getRange(filaLey+4,1).setBackground('#f5f5f5');
}

function crearEncabezadosControl(sheet, grupoKey) {
  const estudiantes = estudiantesDeGrupo(grupoKey);
  const profCedula = grupoPorKey(grupoKey).profesor;
  const profNombre = nombreDeEstudiante(profCedula);

  const headers = ['Cédula', 'Nombre'];
  SESIONES.forEach((s, i) => { headers.push('A'+(i+1)+'\n'+s); });

  const r = sheet.getRange(1, 1, 1, headers.length);
  r.setValues([headers]);
  r.setBackground('#0d1524'); r.setFontColor('#ffffff'); r.setFontWeight('bold');
  sheet.setFrozenRows(1);
  sheet.setFrozenColumns(2);
  sheet.setRowHeight(1, 40);

  // Fila del profesor (primera, destacada)
  sheet.getRange(2, 1).setValue(profCedula);
  sheet.getRange(2, 2).setValue('👨‍🏫 ' + profNombre.replace('_', ', '));
  sheet.getRange(2, 1, 1, 2).setBackground('#0d1a3a').setFontColor('#60a5fa').setFontWeight('bold');
  sheet.getRange(2, 3, 1, SESIONES.length).setBackground('#1a2a4a');

  // Filas de estudiantes
  estudiantes.forEach((est, i) => {
    const fila = i + 3;
    sheet.getRange(fila, 1).setValue(est.cedula);
    sheet.getRange(fila, 2).setValue(est.nombre);
    sheet.getRange(fila, 3, 1, SESIONES.length).setBackground('#fde8e8');
  });

  sheet.setColumnWidth(1, 130);
  sheet.setColumnWidth(2, 180);
  for (let c = 3; c <= headers.length; c++) sheet.setColumnWidth(c, 120);
}

// Diagnóstico: lista los triggers realmente instalados en el proyecto (no borra ni crea nada).
function verTriggersInstalados() {
  const triggers = ScriptApp.getProjectTriggers();
  if (triggers.length === 0) {
    Logger.log('No hay ningún trigger instalado.');
    return;
  }
  triggers.forEach(t => {
    Logger.log(`Función: ${t.getHandlerFunction()} | Tipo: ${t.getEventType()} | ID: ${t.getUniqueId()}`);
  });
}

// ── Backfill de palabras_por_minuto y repeticiones para grabaciones antiguas ──
// (Las pausas NO se pueden recalcular en histórico: esa información depende de los
// segmentos con timestamps que el transcriptor devuelve, y esos nunca se guardaron para audios
// procesados antes de este cambio. Solo quedan disponibles para grabaciones nuevas.)
function recalcularVariablesTextoTodos() { leerGrupos().forEach(g => recalcularVariablesTexto(g.key)); }

// ── Recalcular "Promedio Final" de todos los estudiantes en la hoja Notas (Control) ──
// Necesario después de cancelar una sesión: los promedios ya guardados se calcularon
// dividiendo entre el número de sesiones ANTERIOR (ej. 22), que ahora está mal —
// habría que dividir entre las sesiones reales (ej. 21). Esto no toca las notas de
// sesiones individuales ya asignadas, solo recalcula el promedio final con el divisor correcto.
// ── Recalcular "Promedio Final" de todos los estudiantes en la hoja Notas (Control) ──
// Útil después de cancelar una sesión: los promedios ya guardados se calcularon
// dividiendo entre el número de sesiones ANTERIOR (ej. 22), que ahora está mal —
// hay que dividir entre las sesiones reales (ej. 21).
function recalcularPromediosFinalesTodos() { leerGrupos().forEach(g => recalcularPromediosFinales(g.key)); }
function recalcularPromediosFinales(grupoKey) {
  const nombreSheet = grupoPorKey(grupoKey).control;
  const files = DriveApp.getFilesByName(nombreSheet);
  if (!files.hasNext()) return;
  const ss = SpreadsheetApp.open(files.next());
  const sheet = ss.getSheetByName('Notas');
  if (!sheet || sheet.getLastRow() < 2) return;

  const headers = sheet.getRange(1,1,1,sheet.getLastColumn()).getValues()[0];
  const colPromedio = headers.findIndex(h => String(h).includes('Promedio Final')) + 1;
  if (colPromedio === 0) throw new Error('No se encontró la columna "Promedio Final" en Notas.');

  const numSesiones = SESIONES.length;
  const lastRow = sheet.getLastRow();
  const filas = sheet.getRange(2,1,lastRow-1,sheet.getLastColumn()).getValues();
  let actualizados = 0;
  filas.forEach((fila,i) => {
    const notasRow = fila.slice(2, 2+numSesiones); // columnas 3..(3+numSesiones-1), 0-indexado
    let suma = 0, contadas = 0;
    SESIONES.forEach((fechaSesion, idx) => {
      if (SESIONES_EXCLUIDAS_PROMEDIO.includes(fechaSesion)) return;
      suma += Number(notasRow[idx]) || 0;
      contadas++;
    });
    const promedio = contadas > 0 ? Math.round((suma/contadas)*100)/100 : 0;
    sheet.getRange(i+2, colPromedio).setValue(promedio);
    actualizados++;
  });
  Logger.log(`recalcularPromediosFinales(${grupoKey}): ${actualizados} filas actualizadas (÷${numSesiones - SESIONES_EXCLUIDAS_PROMEDIO.length} sesiones contadas)`);
}
function recalcularVariablesTexto(grupoKey) {
  const nombreSheet = grupoPorKey(grupoKey).grabaciones;
  const files = DriveApp.getFilesByName(nombreSheet);
  if (!files.hasNext()) return;
  const ss = SpreadsheetApp.open(files.next());
  const sheet = ss.getSheetByName('Grabaciones');
  if (!sheet || sheet.getLastRow() < 2) return;

  const headers = sheet.getRange(1,1,1,sheet.getLastColumn()).getValues()[0];
  const colTxt = headers.indexOf('Transcripcion');
  const colDur = headers.indexOf('duracion_segundos');
  const colPPM = headers.indexOf('palabras_por_minuto');
  const colRep = headers.indexOf('conteo_repeticiones');
  const colFrecRep = headers.indexOf('frecuencia_repeticiones');
  const colMul = headers.indexOf('conteo_muletillas');
  const colFrecMul = headers.indexOf('frecuencia_muletillas');
  const colDud = headers.indexOf('conteo_dudas');
  const colFrecDud = headers.indexOf('frecuencia_dudas');
  const colNeg = headers.indexOf('conteo_negaciones');
  const colFrecNeg = headers.indexOf('frecuencia_negaciones');
  const colDif = headers.indexOf('conteo_percepcion_dificultad');
  const colFrecDif = headers.indexOf('frecuencia_percepcion_dificultad');
  const requeridas = [colTxt,colDur,colPPM,colRep,colFrecRep,colMul,colFrecMul,colDud,colFrecDud,colNeg,colFrecNeg];
  if (requeridas.includes(-1)) {
    throw new Error('Faltan columnas esperadas en Grabaciones (agrega los encabezados nuevos manualmente en la fila 1 si la hoja es antigua). conteo_percepcion_dificultad/frecuencia_percepcion_dificultad son opcionales para hojas que aún no las tengan.');
  }
  const tienePercepcion = colDif >= 0 && colFrecDif >= 0;

  const lastRow = sheet.getLastRow();
  const rows = sheet.getRange(2,1,lastRow-1,sheet.getLastColumn()).getValues();
  let actualizados = 0;
  rows.forEach((row, i) => {
    const texto = row[colTxt];
    if (!texto) return;
    const limpio = limpiarTexto(texto);
    const tokens = limpio.split(' ').filter(Boolean);
    const n = tokens.length;

    let cRep = 0;
    for (let j = 1; j < tokens.length; j++) { if (tokens[j] === tokens[j-1]) cRep++; }
    const frecRep = n > 0 ? round4(cRep/n) : 0;
    const duracion = Number(row[colDur]) || 0;
    const ppm = duracion > 0 ? round4(n/(duracion/60)) : 0;

    const cMul = contarLista(limpio, MULETILLAS);
    const cDud = contarLista(limpio, DUDAS);
    const cNeg = contarLista(limpio, NEGACIONES);
    const cDif = contarListaSinNegacion(limpio, PERCEPCION_DIFICULTAD);

    sheet.getRange(i+2, colPPM+1, 1, 3).setValues([[ppm, cRep, frecRep]]);
    sheet.getRange(i+2, colMul+1).setValue(cMul);
    sheet.getRange(i+2, colFrecMul+1).setValue(n>0?round4(cMul/n):0);
    sheet.getRange(i+2, colDud+1).setValue(cDud);
    sheet.getRange(i+2, colFrecDud+1).setValue(n>0?round4(cDud/n):0);
    sheet.getRange(i+2, colNeg+1).setValue(cNeg);
    sheet.getRange(i+2, colFrecNeg+1).setValue(n>0?round4(cNeg/n):0);
    if (tienePercepcion) {
      sheet.getRange(i+2, colDif+1).setValue(cDif);
      sheet.getRange(i+2, colFrecDif+1).setValue(n>0?round4(cDif/n):0);
    }
    actualizados++;
  });
  Logger.log(`recalcularVariablesTexto(${grupoKey}): ${actualizados} filas actualizadas`);
}

function getExt(mime) {
  return {'audio/webm':'.webm','audio/webm;codecs=opus':'.webm',
    'audio/mp4':'.m4a','audio/mp4;codecs=mp4a.40.2':'.m4a','audio/x-m4a':'.m4a',
    'audio/aac':'.aac','audio/mpeg':'.mp3','audio/wav':'.wav',
    'audio/ogg':'.ogg'}[mime]||'.webm';
}

function json(data) {
  return ContentService.createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

// ===== PANEL DEL PROFESOR (dashboard.html nuevo) =====
const ARCHIVO_PANEL_UNIFICADO = 'panel_unificado_datos.json';   // se sube a la carpeta CARPETA_ABSA_MODELO
const PANEL_CACHE_TTL = 1800;                                    // 30 min (datos del panel)
const NOTAS_CACHE_TTL = 120;                                     // 2 min (notas: se ven casi en vivo)

function cacheGuardarTexto_(prefijo, s, ttl) {
  try {
    const c = CacheService.getScriptCache(), t = ttl || PANEL_CACHE_TTL;
    const T = 45000, ver = String(Date.now()), obj = {}; let n = 0;
    for (let i = 0; i < s.length; i += T) { obj[prefijo + '_' + ver + '_' + n] = s.substring(i, i + T); n++; }
    if (n > 90) return;
    c.putAll(obj, t);
    c.put(prefijo + '_meta', ver + ':' + n, t);
  } catch (e) {}
}
function cacheLeerTexto_(prefijo) {
  try {
    const c = CacheService.getScriptCache();
    const meta = c.get(prefijo + '_meta'); if (!meta) return null;
    const [ver, nStr] = meta.split(':'), n = parseInt(nStr, 10), keys = [];
    for (let i = 0; i < n; i++) keys.push(prefijo + '_' + ver + '_' + i);
    const parts = c.getAll(keys); let s = '';
    for (let i = 0; i < n; i++) { const p = parts[prefijo + '_' + ver + '_' + i]; if (p === undefined || p === null) return null; s += p; }
    return s;
  } catch (e) { return null; }
}
// Ejecutar a mano desde el editor después de subir un panel_unificado_datos.json nuevo a Drive (si no, tarda hasta 30 min en verse).
function invalidarPanelUnificado_() {
  try {
    const c = CacheService.getScriptCache(), profs = {};
    leerGrupos().forEach(g => { profs[g.profesor] = 1; });
    Object.keys(profs).forEach(p => { c.remove('pu_main_' + p + '_meta'); c.remove('pu_tr_' + p + '_meta'); c.remove('pu_tx_' + p + '_meta'); });
  } catch (e) {}
}

// Cada profesor recibe SOLO los cursos donde su cédula es CedulaProfesor en la hoja Grupos (las claves de grupo deben coincidir
// con las del panel: edwin_algebra, edwin_metodos, omar_24, omar_46) y solo los nombres de sus propios estudiantes.
// === DEMOSTRACIÓN: profesor de demostración que ve todos los cursos con estudiantes anonimizados. ===
// La cédula de la fila «PROFESOR DEMO» (Vínculo = PROFESOR, con su clave en la hoja maestra) se define en la propiedad de
// script CEDULAS_DEMO (separadas por comas); sin la propiedad no hay cuenta de demostración. Su clave vive solo en la hoja.
const CEDULAS_DEMO_ANONIMO = (PropertiesService.getScriptProperties().getProperty('CEDULAS_DEMO') || '').split(',').map(x => x.trim()).filter(Boolean);
function panelProfesorTextos_(cedulaProf) {
  const a = cacheLeerTexto_('pu_main_' + cedulaProf), b = cacheLeerTexto_('pu_tr_' + cedulaProf), x = cacheLeerTexto_('pu_tx_' + cedulaProf);
  if (a && b && x) return { main: a, tr: b, tx: x };
  const carpetas = DriveApp.getFoldersByName(CARPETA_ABSA_MODELO);
  if (!carpetas.hasNext()) throw new Error('No encuentro la carpeta de análisis en Drive.');
  const archivos = carpetas.next().getFilesByName(ARCHIVO_PANEL_UNIFICADO);
  if (!archivos.hasNext()) throw new Error('Falta el archivo ' + ARCHIVO_PANEL_UNIFICADO + ' en Drive.');
  const d = JSON.parse(archivos.next().getBlob().getDataAsString('UTF-8'));
  const demo = CEDULAS_DEMO_ANONIMO.indexOf(String(cedulaProf)) >= 0;
  const mios = {};
  if (demo) { Object.keys(d.PD || {}).forEach(k => { mios[k] = 1; }); }
  else { leerGrupos().filter(g => g.profesor === cedulaProf).forEach(g => { mios[g.key] = 1; }); }
  const pick = o => { const r = {}; Object.keys(o || {}).forEach(k => { if (mios[k]) r[k] = o[k]; }); return r; };
  const PD = pick(d.PD), TD = pick(d.TD), TR = pick(d.TR), TX = pick(d.TX), ids = {}, NOM = {};
  Object.keys(PD).forEach(k => Object.keys(PD[k].estudiantes || {}).forEach(n => { ids[n] = 1; }));
  Object.keys(TD).forEach(k => (TD[k].menciones || []).forEach(m => { ids[String(m.c)] = 1; }));
  if (!demo) Object.keys(ids).forEach(n => { if (d.NOM && d.NOM[n]) NOM[n] = d.NOM[n]; });
  const main = JSON.stringify({ ok: true, PD: PD, TD: TD, NOM: NOM });
  const tr = JSON.stringify({ ok: true, TR: TR });
  const tx = JSON.stringify({ ok: true, TX: TX });
  cacheGuardarTexto_('pu_main_' + cedulaProf, main); cacheGuardarTexto_('pu_tr_' + cedulaProf, tr); cacheGuardarTexto_('pu_tx_' + cedulaProf, tx);
  return { main: main, tr: tr, tx: tx };
}

// Solo entran personas con Vinculo = PROFESOR en la hoja de estudiantes.
function profesorValido_(cedula, clave) {
  const ced = String(cedula || '').trim(), cla = String(clave || '').trim();
  if (!ced || !cla) return null;
  const m = leerEstudiantesMaestro().find(e => e.cedula === ced && String(e.clave).toUpperCase() === cla.toUpperCase());   // la clave no distingue mayúsculas/minúsculas
  return (m && m.vinculo === 'PROFESOR') ? m : null;
}

// Notas por sesión y fechas de envío, SOLO de los grupos donde esta persona es CedulaProfesor (hoja Grupos).
function notasProfesorTexto_(cedulaProf) {
  const cache = cacheLeerTexto_('nt_' + cedulaProf);
  if (cache) return cache;
  const fmt = v => (v instanceof Date) ? Utilities.formatDate(v, 'America/Bogota', 'dd/MM/yyyy HH:mm') : String(v == null ? '' : v).trim();
  const grupos = [];
  leerGrupos().filter(g => g.profesor === cedulaProf).forEach(g => {
    const files = DriveApp.getFilesByName(g.control);
    if (!files.hasNext()) return;
    const ss = SpreadsheetApp.open(files.next());
    const shN = ss.getSheetByName('Notas'), shC = ss.getSheetByName('Control');
    if (!shN || shN.getLastRow() < 2) return;
    const N = shN.getDataRange().getValues();                 // una sola lectura por hoja
    const C = (shC && shC.getLastRow() >= 2) ? shC.getDataRange().getValues() : [];
    const hN = N[0].map(String), hC = (C[0] || []).map(String);
    const reFecha = /(\d{2}\/\d{2}\/\d{4})/;
    const sesiones = [], colN = [], colC = [];
    hN.forEach((h, i) => { const m = h.match(reFecha); if (m) { sesiones.push(m[1]); colN.push(i); colC.push(hC.findIndex(x => x.indexOf(m[1]) >= 0)); } });
    const colProm = hN.findIndex(h => h.indexOf('Promedio Final') >= 0);
    const extras = [], colExtra = [];
    hN.forEach((h, i) => { if (i >= 2 && !reFecha.test(h) && i !== colProm && h.trim()) { extras.push(h.trim()); colExtra.push(i); } });
    const ctrl = {};
    C.slice(1).forEach(r => { ctrl[String(r[0]).trim()] = r; });
    const estudiantes = [];
    N.slice(1).forEach(r => {
      const ced = String(r[0]).trim(), nom = String(r[1]).trim();
      if (!ced || ced === g.profesor || nom.indexOf('👨') === 0) return;
      const rc = ctrl[ced] || [];
      estudiantes.push({
        c: ced, n: nom,
        nt: colN.map(i => Number(r[i]) || 0),
        fe: colC.map(i => i >= 0 ? fmt(rc[i]) : ''),
        p: colProm >= 0 ? (Number(r[colProm]) || 0) : 0,
        x: colExtra.reduce((o, i, k) => { o[extras[k]] = fmt(r[i]); return o; }, {})
      });
    });
    grupos.push({ key: g.key, nombre: g.nombre, materia: g.materia, limite3: g.limite3, sesiones: sesiones,
                  excluidas: SESIONES_EXCLUIDAS_PROMEDIO, extras: extras, estudiantes: estudiantes });
  });
  const salida = JSON.stringify({ ok: true, hoy: Utilities.formatDate(new Date(), 'America/Bogota', 'dd/MM/yyyy'), grupos: grupos });
  cacheGuardarTexto_('nt_' + cedulaProf, salida, NOTAS_CACHE_TTL);
  return salida;
}
