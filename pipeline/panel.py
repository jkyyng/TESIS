# -*- coding: utf-8 -*-
"""Pasos 5 y 13 de Foné: panel de las tres preguntas y panel final con estudiantes seudonimizados.

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
import tema as _tema

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
    try:
        return _tema._modulo(nombre)
    except ImportError:
        pass
    raise ImportError(nombre)



def paso_05_panel_preguntas():
    r"""Paso: script «construir_panel_preguntas_v10».

    Agrega resultados\panel_preguntas\oraciones_etiquetadas.jsonl (etiquetar_corpus_preguntas.py, 3.129)
    al nivel que ve el profe: por curso -> estudiante (cedula) -> sesion, las oraciones que responden
    cada una de las 3 preguntas, como citas.

    Por audio:
      P1: oraciones con A          P3: oraciones con R
      P2: oraciones P2, cada una con su tipo (D+, D0, solo_LLM); estado del audio en P2:
          "reporta_dificultad" si hay alguna D+; "dice_que_no" si solo hay D0; "posible" si solo hay solo_LLM;
          "sin_respuesta" si ninguna oracion responde P2.
      sigue_estructura: True si el audio responde P1, P2 y P3 (indicador descriptivo; 3.121 encontro ~50 %).
    Resumen por curso y sesion: % de audios con respuesta a cada pregunta y % con dificultad reportada.
    Las citas son la oracion completa (no la transcripcion completa: ver definicion_instrumento.md, cita acotada).
    Salida: resultados\panel_preguntas\panel_preguntas.json
    """
    _DOC = '\nAgrega resultados\\panel_preguntas\\oraciones_etiquetadas.jsonl (etiquetar_corpus_preguntas.py, 3.129)\nal nivel que ve el profe: por curso -> estudiante (cedula) -> sesion, las oraciones que responden\ncada una de las 3 preguntas, como citas.\n\nPor audio:\n  P1: oraciones con A          P3: oraciones con R\n  P2: oraciones P2, cada una con su tipo (D+, D0, solo_LLM); estado del audio en P2:\n      "reporta_dificultad" si hay alguna D+; "dice_que_no" si solo hay D0; "posible" si solo hay solo_LLM;\n      "sin_respuesta" si ninguna oracion responde P2.\n  sigue_estructura: True si el audio responde P1, P2 y P3 (indicador descriptivo; 3.121 encontro ~50 %).\nResumen por curso y sesion: % de audios con respuesta a cada pregunta y % con dificultad reportada.\nLas citas son la oracion completa (no la transcripcion completa: ver definicion_instrumento.md, cita acotada).\nSalida: resultados\\panel_preguntas\\panel_preguntas.json\n'
    # -*- coding: utf-8 -*-
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


    def norm_c(s):
        import unicodedata
        return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


    def estado_p2(tipos):
        if "D+" in tipos:
            return "reporta_dificultad"
        if "D0" in tipos:
            return "dice_que_no"
        if "revisar_reglas" in tipos or "solo_LLM" in tipos or "tras_pregunta" in tipos:
            return "posible"
        return "sin_respuesta"


    def main():
        cursos = defaultdict(lambda: defaultdict(list))
        with open(D + r"\oraciones_etiquetadas_v10.jsonl", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                a = json.loads(line)
                # La consigna repetida en voz alta se excluye como respuesta, pero marca el inicio de la
                # respuesta: las siguientes oraciones (hasta CAP o la siguiente consigna) pertenecen a esa
                # pregunta aunque el detector no las haya marcado (p. ej. "no, nada" tras "¿qué se me dificultó?").
                os_, seg, cnt, n_consigna, n_tras = [], None, 0, 0, 0
                for o in a["oraciones"]:
                    if es_consigna(o["oracion"]):
                        n_consigna += 1
                        t = norm_c(o["oracion"])
                        seg = 2 if "dificult" in t else 1 if "aprend" in t else 3 if "ritmo" in t else None
                        cnt = 0
                        continue
                    o = dict(o)
                    # Solo se usa la consigna de P2 (P1 y P3 ya los detecta bien el LLM: A y R). La respuesta
                    # termina al llegar a una oración de ritmo (R) o a CAP oraciones.
                    if seg == 2 and o["P3"]:
                        seg = None
                    if seg == 2 and cnt < CAP[2]:
                        cnt += 1
                        if not o["P2"]:
                            o["P2"] = True
                            o["P2_tipo"] = "tras_pregunta"
                            n_tras += 1
                    os_.append(o)
                p1 = [o["oracion"] for o in os_ if o["P1"]]
                # "senales": en D+ cuentan el lexico con negacion y el LLM v2 (D). Con las dos, precision 0.85 frente
                # a 0.76 del lexico solo en la muestra v3 de oraciones (3.135); sin el LLM, 0 de 3 acertaron (n minimo).
                # v7: cada cita de P2 lleva la oracion anterior y la siguiente (contexto) porque la detectada puede quedar cortada
                p2 = [{"cita": o["oracion"], "tipo": o["P2_tipo"],
                       "antes": os_[k - 1]["oracion"] if k > 0 else "", "despues": os_[k + 1]["oracion"] if k + 1 < len(os_) else "",
                       **({"senales": o["P2_senales"]} if o["P2_tipo"] == "D+" else {})}
                      for k, o in enumerate(os_) if o["P2"]]
                p3 = [o["oracion"] for o in os_ if o["P3"]]
                est = estado_p2({x["tipo"] for x in p2})
                cursos[a["curso"]][a["cedula"]].append({
                    "sesion": a["fecha_sesion"], "archivo": a["archivo"],
                    "P1": p1, "P2": p2, "P2_estado": est, "P3": p3,
                    "sigue_estructura": bool(p1) and est != "sin_respuesta" and bool(p3),
                    "n_oraciones": len(os_), "n_consigna_excluida": n_consigna, "n_atribuidas_tras_consigna": n_tras,"sin_etiqueta_llm": sum(o["llm_v2"] is None for o in os_),
                })
        salida = {"_descripcion": _DOC.strip().splitlines()[0], "cursos": {}}
        for curso, ests in cursos.items():
            audios = [x for v in ests.values() for x in v]
            por_sesion = defaultdict(list)
            for x in audios:
                por_sesion[x["sesion"]].append(x)
            resumen = lambda xs: {
                "audios": len(xs),
                "responde_P1": round(sum(bool(x["P1"]) for x in xs) / len(xs), 3),
                "responde_P2": round(sum(x["P2_estado"] != "sin_respuesta" for x in xs) / len(xs), 3),
                "responde_P3": round(sum(bool(x["P3"]) for x in xs) / len(xs), 3),
                "P2_estado": dict(Counter(x["P2_estado"] for x in xs)),
                "sigue_estructura": round(sum(x["sigue_estructura"] for x in xs) / len(xs), 3),
            }
            # misma clave de grupo que el dashboard y absa_dashboard_CARPETA_DATOS.json (p. ej. "edwin_algebra")
            salida["cursos"][curso.lower()] = {
                "resumen": resumen(audios),
                "por_sesion": {s: resumen(xs) for s, xs in sorted(por_sesion.items())},
                "estudiantes": {c: sorted(v, key=lambda x: x["sesion"]) for c, v in ests.items()},
            }
        json.dump(salida, open(D + r"\panel_preguntas_v10.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        for c, v in salida["cursos"].items():
            print(c, v["resumen"])


    if True:
        main()









def paso_13_panel_unificado():
    r"""Paso: script «construir_panel_unificado_v10».

    Regenera panel_unificado.html (filtros arriba + 3 secciones: Preguntas, Temas con dificultad, Tablero general) con las ULTIMAS reglas:
    datos = panel_preguntas_v10.json (reglas + verificador) y absa_dashboard_CARPETA_DATOS_v11r.json (tema final: contenido + factores + rescate extractivo).
    Plantilla: la version del 2026-10-06 del hilo "Trabajo grafico" (panel/panel_unificado.base.html): se conservan HTML, CSS y JS; solo cambian
    los datos (PD y TD) y unos parches pequenos (resaltado del tema, chips de tipo de tema, sin "por revisar" vacio).
    Privacidad: cedulas reemplazadas por un numero de estudiante comun a todos los cursos; se omiten nombres de archivo.
    Uso: python construir_panel_unificado_v10.py [salida.html]
    """
    # -*- coding: utf-8 -*-
    import json
    import re
    import sys

    D = r"RUTA_PROYECTO" + "\\"
    BASE = D + r"panel\panel_unificado.base.html"
    OUT = sys.argv[1] if len(sys.argv) > 1 else D + "panel_unificado.html"

    pan = json.load(open(D + r"resultados\panel_preguntas\panel_preguntas_v10.json", encoding="utf-8"))["cursos"]
    tema = json.load(open(D + r"resultados\absa_dashboard_CARPETA_DATOS_v11r.json", encoding="utf-8"))
    KS = [c["grupo"] for c in json.load(open(r"RUTA_PROYECTO\CARPETA_DATOS\cursos.json", encoding="utf-8"))]

    # numero de estudiante comun a todos los cursos
    # la primera clase (24/07) tiene audios de prueba: se excluye de todo el panel (pedido del autor, 2026-10-15)
    EXCL = {"2026-07-24"}
    ceds = set()
    for g in KS:
        ceds |= {str(c) for c, aud in pan[g]["estudiantes"].items() if any(a["sesion"] not in EXCL for a in aud)} | {str(m["c"]) for m in tema[g]["menciones"] if m["s"] not in EXCL}
    num = {c: i + 1 for i, c in enumerate(sorted(ceds))}

    # Alucinaciones de Whisper en silencios ("Subtitulado por Jnkoil", "Gracias por ver el video"; vienen de subtitulos de YouTube) se quitan de
    # citas y transcripciones (2026-10-15, auditoria de errores tecnicos). En las transcripciones se reemplazan por espacios del mismo largo para
    # no mover las posiciones de la marca y los resaltados.
    ALUC = re.compile(r"(?:Subtitulado por Jnkoil[.!]?\s*)+|¡?Gracias por ver el video[.!]?", re.I)


    def limpia(s):
        return re.sub(r"\s+", " ", ALUC.sub(" ", s)).strip()


    def audio_limpio(a):
        p1 = [c for c in map(limpia, a["P1"]) if c]
        p3 = [c for c in map(limpia, a["P3"]) if c]
        p2 = [{"cita": limpia(x["cita"]), "tipo": x["tipo"]} for x in a["P2"] if limpia(x["cita"])]
        est = a["P2_estado"] if p2 else "sin_respuesta"
        return {"sesion": a["sesion"], "P1": p1, "P2": p2, "P3": p3, "P2_estado": est, "sigue_estructura": bool(p1) and est != "sin_respuesta" and bool(p3)}


    PD, TD = {}, {}
    for g in KS:
        est = {}
        for ced, aud in pan[g]["estudiantes"].items():
            aud = [a for a in aud if a["sesion"] not in EXCL]
            if not aud:
                continue
            est[str(num[str(ced)])] = [audio_limpio(a) for a in aud]
        PD[g] = {"estudiantes": est}
        ms, tr = [], {}
        for m in tema[g]["menciones"]:
            if m["d"] != "DIFICULTAD" or not m.get("t") or m["s"] in EXCL:
                continue
            n = num[str(m["c"])]
            k = f'{n}|{m["s"]}'
            ms.append({"c": n, "s": m["s"], "d": m["d"], "e": m["e"], "t": m["t"], "tt": m.get("tt", ["tema"] * len(m["t"])), "hl": m.get("hl", []), "k": k, "r": m["r"]})
            tr[k] = ALUC.sub(lambda x: " " * len(x.group(0)), tema[g]["transcripciones"][m["k"]])
        TD[g] = {"menciones": ms, "transcripciones": tr}

    H = open(BASE, encoding="utf-8").read()
    L = H.split("\n")
    i_pd = next(i for i, l in enumerate(L) if l.startswith("const PD="))
    i_td = next(i for i, l in enumerate(L) if l.startswith("const TD="))
    assert i_td == i_pd + 1
    L[i_pd] = "const PD=" + json.dumps(PD, ensure_ascii=False).replace("</", "<\\/") + ";"
    L[i_td] = "const TD=" + json.dumps(TD, ensure_ascii=False).replace("</", "<\\/") + ";"
    H = "\n".join(L)


    def rep(old, new):
        nonlocal H
        assert H.count(old) == 1, ("no se encontro exactamente una vez:", old[:80], H.count(old))
        H = H.replace(old, new)


    # los contadores animados mostraban un numero negativo un instante (el primer cuadro de la animacion da p < 0)
    rep("const p=Math.min(1,(t-t0)/1200);el.textContent=Math.round(to*(1-Math.pow(1-p,3)))+(suf||'')", "const p=Math.max(0,Math.min(1,(t-t0)/1200));el.textContent=Math.round(to*(1-Math.pow(1-p,3)))+(suf||'')")
    # estudiantes: ya son numeros anonimos
    rep("const nomE=c=>'Estudiante '+String(c).slice(-ELEN);", "const nomE=c=>'Estudiante '+c;")
    rep("const ids=Object.keys(E).sort();", "const ids=Object.keys(E).sort((a,b)=>a-b);")
    rep("'cédulas distintas'", "'estudiantes distintos'")
    # tipos de P2 de v10 (D+, D0, tras_pregunta) y sin "por revisar" vacio
    rep("'solo_LLM':['por revisar','rgba(245,184,61,.2)','#F5B83D']};", "'solo_LLM':['por revisar','rgba(245,184,61,.2)','#F5B83D'],'tras_pregunta':['tras la pregunta','rgba(245,184,61,.2)','#F5B83D']};")
    rep("const ORD={'D+':0,'solo_LLM':1,'D0':2};", "const ORD={'D+':0,'solo_LLM':1,'tras_pregunta':1,'D0':2};")
    rep("+L('var(--amber)','por revisar',est.posible)+", "+(est.posible?L('var(--amber)','por revisar',est.posible):'')+")
    rep("lgD.innerHTML=S.map(([k,t,c])=>", "lgD.innerHTML=S.filter(([k])=>k!='posible'||e[k]).map(([k,t,c])=>")
    # tema: ventana de +-300 caracteres, resaltado del tema / causa general / frase y chips de tres colores (como la maqueta aprobada)
    i0 = H.index("function tSnip(")
    i1 = H.index("function tPint0(){")
    nuevo = r"""const HLC={t:'ht',f:'hf',p:'hp'};
function tSnip(tx,r,d,hl){const a0=Math.max(0,r[0]-300),b0=Math.min(tx.length,r[1]+300);
  let a=a0>0?tx.indexOf(' ',a0):0;if(a<0||a>r[0])a=a0;let b=b0<tx.length?tx.lastIndexOf(' ',b0):tx.length;if(b<r[1])b=b0;
  const R=[{a:r[0],b:r[1],c:d=='DUDAS'?'du':'dif'}].concat((hl||[]).map(h=>({a:h[0],b:h[1],c:HLC[h[2]]||'ht'})));
  R.sort((p,q)=>p.a-q.a||((p.c=='dif'||p.c=='du')?-1:1));
  let out=a>0?'…':'',pos=a;
  R.forEach(x=>{if(x.b<=a||x.a>=b||x.a<pos)return;out+=esc(tx.slice(pos,x.a))+`<mark class="${x.c}">${esc(tx.slice(x.a,Math.min(x.b,b)))}</mark>`;pos=Math.min(x.b,b)});
  return out+esc(tx.slice(pos,b))+(b<tx.length?'…':'')}
const TC={tema:['rgba(94,224,163,.18)','#5EE0A3','Tema del curso'],factor:['rgba(245,184,61,.2)','#F5B83D','Causa general'],frase:['rgba(167,139,250,.22)','#C4B5FD','Frase del estudiante']};
const tchips=m=>m.t.map((t,i)=>{const c=TC[(m.tt&&m.tt[i])||'tema'];return `<span class="chip" title="${c[2]}" style="background:${c[0]};color:${c[1]}">${esc(t)}</span>`}).join('');
"""
    H = H[:i0] + nuevo + H[i1:]
    rep("${m.t.map(t=>`<span class=\"chip\" style=\"background:rgba(212,232,220,.12);color:#D4E8DC\">${esc(t)}</span>`).join('')}</div><p>${tSnip(tx,m.r,m.d)}</p></div>`}",
        "${tchips(m)}</div><p>${tSnip(tx,m.r,m.d,m.hl)}</p></div>`}")
    rep("<p>${tSnip(TD[m.kc].transcripciones[m.k]||'',m.r,m.d)}</p></div>`).join(''))}",
        "<div style=\"margin:4px 0\">${tchips(m)}</div><p>${tSnip(TD[m.kc].transcripciones[m.k]||'',m.r,m.d,m.hl)}</p></div>`).join(''))}")
    rep('<div class="cards" style="max-width:980px;margin-top:10px">',
        '<div class="legm rv d2"><span><mark class="dif">dificultad</mark></span><span><mark class="ht">tema del curso</mark></span><span><mark class="hf">causa general</mark></span><span><mark class="hp">frase del estudiante</mark></span></div><div class="cards" style="max-width:980px;margin-top:10px">')
    css = ("mark,#vt mark{border-radius:4px;padding:0 3px;color:#fff}mark.dif,#vt mark.dif{background:rgba(255,122,102,.45);font-weight:700}mark.du,#vt mark.du{background:rgba(167,139,250,.4);font-weight:700}"
           "mark.ht,#vt mark.ht{background:rgba(94,224,163,.3)}mark.hf,#vt mark.hf{background:rgba(245,184,61,.35)}mark.hp,#vt mark.hp{background:rgba(167,139,250,.35)}"
           ".legm{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--sage);margin:8px 0 2px}.legm mark{padding:1px 8px}"
           ".drawer .chip,#vt .chip{padding:2px 10px;border-radius:99px;font-weight:700;font-size:11px;display:inline-block;margin-right:6px}")
    rep("</style>", css + "</style>")
    # --- cambios pedidos el 2026-10-15 ---
    # 1) primera pantalla: sin el porcentaje grande de "responden las 3" (ni su linea temporal por sesion)
    rep('<div class="hero" style="margin-top:24px"><div><div class="big rv d2"><span id="qn3">0</span><small>%</small></div><div class="biglbl rv d3" id="qlbl3"></div></div>\n<div>',
        '<div class="hero" style="margin-top:24px;grid-template-columns:1fr;max-width:900px">\n<div>')
    rep("<h1 class=\"rv d1\">¿Cuántos estudiantes<br>responden las 3 preguntas?</h1>", "<h1 class=\"rv d1\">Las 3 preguntas<br>de un vistazo</h1>")
    rep('<div class="row rv d6" id="qtrend"></div>\n', '')
    rep("  g('qn3').dataset.count=PP(all);g('qn3').textContent=0;\n  g('qlbl3').textContent=all+' de '+n+' audios responden las tres preguntas en la misma grabación.';\n", '')
    i0 = H.index("  const m={};qAud.forEach(a=>{(m[a.sesion]")
    i1 = H.index("function qOpen(")
    H = H[:i0] + "}\n" + H[i1:]
    # 2) filtros y textos: "Audio 1, Audio 2..." en vez de fechas (las 4 clases comparten las mismas sesiones)
    rep("const iso=s=>{const p=s.split('-');return p[2]+'/'+p[1]};\nconst fecha=s=>{const p=s.split('-');return p[2]+'/'+p[1]+'/'+p[0]};",
        "const fecha=s=>'Audio '+(ALLS.indexOf(s)+1);\nconst iso=fecha;")
    # 3) tema: el ranking muestra todos los temas en una lista con barra de desplazamiento
    rep("const top=tL.slice(0,8),mx=Math.max(1,top[0]?top[0].n:1);", "const top=tL,mx=Math.max(1,top[0]?top[0].n:1);")
    rep("Clic en un tema para ver lo que dijeron los estudiantes.</div>", "Son ${tL.length} temas: desplázate dentro de la lista para verlos todos. Clic en uno para ver lo que dijeron los estudiantes.</div>")
    rep(">Los temas más mencionados</h1>", ">Los temas más mencionados</h1>")
    rep("#vt .rk .n{", "#vt .rank{max-height:max(260px,calc(100vh - 112px - 210px));overflow-y:auto;padding-right:14px;scrollbar-width:thin;scrollbar-color:var(--mint) rgba(2,43,26,.6)}#vt .rank::-webkit-scrollbar{width:8px}#vt .rank::-webkit-scrollbar-thumb{background:var(--mint);border-radius:8px}#vt .rank::-webkit-scrollbar-track{background:rgba(2,43,26,.6);border-radius:8px}\n#vt .rk .n{")
    # 4) tablero: sin comparativo entre cursos ni mapa de calor (se conserva "Para mirar primero")
    rep('<div class="card c6"><h3>Comparativo entre cursos</h3><div class="s">% que responde cada pregunta (siempre los 4 cursos)</div><div id="cmp"></div></div>\n', '')
    rep('<div class="card c6"><h3>Mapa de calor · las tres preguntas</h3><div class="s">% de audios que responden las tres, por curso y sesión (siempre los 4 cursos)</div><div id="hm"></div></div>\n', '')
    rep("pConst();pCmp();pHeat();pTemas()", "pConst();pAlertas();pTemas()")
    rep("function pHeat(){const ses=ALLS.filter(okS);\n  let o=", "function pAlertas(){const ses=ALLS.filter(okS);\n  let o=")
    rep("  hm.innerHTML=o+`</div>", "  o+=`</div>")
    # 5) sin "duda": el panel solo recibe menciones de DIFICULTAD (DUDAS es indicador secundario), asi que la barra dificultad/duda, el "0 duda"
    #    de cada fila del ranking y la tarjeta "Dificultad o duda" del tablero siempre mostraban 100 % / 0 (auditoria de errores tecnicos, 2026-10-15)
    rep('<div class="kp rv d6" style="grid-column:span 3"><div class="track"><div class="fill" id="tfd" style="background:var(--coral)"></div><div class="fill" id="tfu" style="background:var(--mint)"></div></div><div class="leg" id="tld"></div></div>', '')
    i0 = H.index("  const dif=tMs.filter(m=>m.d!='DUDAS').length")
    i1 = H.index("function tPint1(){")
    H = H[:i0] + "}\n" + H[i1:]
    rep("<span>${x.e.size} estudiante${x.e.size==1?'':'s'} · ${x.DIF} dificultad · ${x.DUD} duda</span>", "<span>${x.e.size} estudiante${x.e.size==1?'':'s'}</span>")
    rep('<div class="card c6"><h3>Dificultad o duda</h3><div class="s">Tipo de mención por curso</div><div id="tp"></div></div>\n', '')
    i0 = H.index("  const R=cs().map(k=>{const q=m.filter(x=>x.k==k)")
    i1 = H.index("  const a=rows(),n=a.length||1,pf=")
    H = H[:i0] + H[i1:]
    rep("Menciones de dificultad o duda, con cuántos", "Menciones de dificultad, con cuántos")
    # "por revisar" -> el estudiante SI respondio la pregunta 2 (cuenta como respuesta); solo no se pudo decir si le costo o no (decision del autor, 2026-10-14)
    assert H.count("'por revisar'") >= 3, H.count("'por revisar'")
    H = H.replace("'por revisar'", "'respondió, sin clasificar'")
    open(OUT, "w", encoding="utf-8").write(H)
    print("ok", round(len(H) / 1e6, 2), "MB;", len(num), "estudiantes;", {g: len(TD[g]["menciones"]) for g in KS}, "menciones con tema")

