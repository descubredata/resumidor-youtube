"""Capa visual: la hoja de estilos y los bloques de HTML que dibuja la interfaz.

Streamlit trae sus propios componentes, correctos pero anónimos. Aquí se repinta todo
sobre una base oscura y se reemplazan por HTML propio las tres piezas donde más se nota
el acabado: la portada, la ficha del video y las tarjetas de datos.

**El acento no es fijo:** se calcula a partir de la miniatura de cada video
(`metadatos.py`), así que la página se tiñe del color del contenido que está resumiendo.

Los selectores `[data-testid="..."]` son API interna de Streamlit y pueden cambiar al
actualizar la librería. Si algún día un control se ve desalineado, es aquí. Nada de eso
afecta al motor.
"""

from __future__ import annotations

import html

# Grano de película: rompe las superficies planas y quita el aspecto de plantilla.
# Va como SVG incrustado para no depender de ningún archivo ni de la red.
GRANO = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='220' height='220'"
    "%3E%3Cfilter id='g'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8'"
    " numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='220' height='220'"
    " filter='url(%23g)'/%3E%3C/svg%3E"
)

TIPOGRAFIAS = (
    "https://fonts.googleapis.com/css2?"
    "family=Inter:wght@400;500;600;700&family=Instrument+Serif:ital@0;1&display=swap"
)


def _rgba(color_hex: str, alfa: float) -> str:
    crudo = color_hex.lstrip("#")
    r, g, b = (int(crudo[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alfa})"


def _miles(numero: int) -> str:
    return f"{numero:,}".replace(",", ".")


def hoja_de_estilos(acento: str) -> str:
    """CSS completo de la aplicación, teñido con el acento del video actual."""
    return f"""
<style>
@import url('{TIPOGRAFIAS}');

:root {{
  --acento: {acento};
  --acento-12: {_rgba(acento, 0.12)};
  --acento-22: {_rgba(acento, 0.22)};
  --acento-40: {_rgba(acento, 0.40)};
  --tinta:   #EDEDEF;
  --tinta-2: #A9A9B4;
  --tinta-3: #71717A;
  --fondo:   #08080A;
  --superficie: rgba(255,255,255,0.035);
  --borde:      rgba(255,255,255,0.09);
  --borde-vivo: rgba(255,255,255,0.16);
  --radio: 14px;
}}

/* ---------- lienzo ---------- */

[data-testid="stAppViewContainer"] {{
  background:
    radial-gradient(1100px 520px at 50% -8%, var(--acento-12), transparent 68%),
    var(--fondo);
}}
[data-testid="stHeader"] {{ background: transparent; }}
/* Fuera el botón "Deploy", el menú de hamburguesa y el pie: son de la plantilla de
   Streamlit y en una herramienta propia solo delatan de dónde salió. */
[data-testid="stToolbar"], [data-testid="stMainMenu"], [data-testid="stDecoration"],
.stAppDeployButton, footer {{ display: none !important; }}

/* El grano va fijo sobre todo el lienzo, por debajo del contenido. */
[data-testid="stAppViewContainer"]::before {{
  content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background-image: url("{GRANO}");
  opacity: 0.30; mix-blend-mode: overlay;
}}

/* Esta hoja viaja dentro de un st.markdown (ver `aplicar_css` en app.py); su
   contenedor no debe ocupar sitio ni sumar separación en la página. */
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdownContainer"] > style) {{
  display: none;
}}

[data-testid="stMainBlockContainer"], .block-container {{
  max-width: 880px; padding-top: 2.4rem; padding-bottom: 6rem;
  position: relative; z-index: 1;
}}

html, body, [class*="st-"] {{ font-family: 'Inter', system-ui, -apple-system, sans-serif; }}
body {{ color: var(--tinta); }}

/* Los íconos de Streamlit no son dibujos sino glifos de una fuente propia. La regla
   de arriba también los alcanza, y sin su familia el glifo cae como texto crudo
   ("keyboard_arrow_right") encima del título del desplegable. */
[data-testid="stIconMaterial"] {{
  font-family: 'Material Symbols Rounded' !important;
}}

/* ---------- portada (antes de analizar) ---------- */

.rd-portada {{ padding: 1.2rem 0 2.2rem; }}
.rd-portada--sello {{ padding: .2rem 0 1.2rem; }}
.rd-marca {{
  display: inline-flex; align-items: center; gap: .55rem;
  font-size: .72rem; font-weight: 600; letter-spacing: .16em; text-transform: uppercase;
  color: var(--acento); border: 1px solid var(--acento-22); border-radius: 999px;
  padding: .38rem .85rem; background: var(--acento-12);
}}
.rd-portada h1 {{
  font-family: 'Instrument Serif', Georgia, serif;
  font-size: clamp(2.6rem, 6vw, 4rem); font-weight: 400; line-height: 1.04;
  margin: 1.4rem 0 .9rem; letter-spacing: -.015em; color: var(--tinta);
}}
.rd-portada h1 em {{ font-style: italic; color: var(--acento); }}
.rd-portada p {{
  font-size: 1.06rem; line-height: 1.6; color: var(--tinta-2);
  max-width: 46ch; margin: 0;
}}

/* ---------- ficha del video ---------- */

.rd-ficha {{
  position: relative; overflow: hidden;
  border: 1px solid var(--borde); border-radius: 20px;
  padding: 1.6rem; margin-bottom: 1.1rem;
  background: var(--superficie);
}}
/* La miniatura del propio video, ampliada y desenfocada, hace de luz ambiental.
   Es el único "fondo con imagen" de la app y siempre pertenece al contenido. */
.rd-ficha__resplandor {{
  position: absolute; inset: -50%; z-index: 0;
  background-size: cover; background-position: center;
  filter: blur(52px) saturate(1.85) brightness(1.15);
  opacity: .72; transform: scale(1.15);
}}
/* Velo por encima del resplandor: deja pasar la luz pero garantiza que el título
   siempre se lea, venga la miniatura clara u oscura. */
.rd-ficha::after {{
  content: ""; position: absolute; inset: 0; z-index: 1;
  background:
    linear-gradient(100deg, rgba(8,8,10,.93) 26%, rgba(8,8,10,.62) 62%, rgba(8,8,10,.30) 100%);
}}
.rd-ficha__cuerpo {{
  position: relative; z-index: 2;
  display: flex; gap: 1.5rem; align-items: center;
}}
.rd-ficha__texto {{ flex: 1; min-width: 0; }}
.rd-ficha__canal {{
  font-size: .72rem; font-weight: 600; letter-spacing: .13em; text-transform: uppercase;
  color: var(--acento); margin-bottom: .55rem;
}}
.rd-ficha__titulo {{
  font-family: 'Instrument Serif', Georgia, serif;
  font-size: clamp(1.5rem, 3.2vw, 2.1rem); font-weight: 400; line-height: 1.15;
  color: var(--tinta); margin: 0 0 .7rem; letter-spacing: -.01em;
}}
.rd-ficha__meta {{
  display: flex; flex-wrap: wrap; gap: .5rem; align-items: center;
  font-size: .84rem; color: var(--tinta-3);
}}
.rd-ficha__meta span.punto {{ opacity: .45; }}

.rd-ficha__mini {{
  position: relative; flex: 0 0 232px; display: block;
  border-radius: 12px; overflow: hidden; line-height: 0;
  border: 1px solid var(--borde-vivo);
  box-shadow: 0 18px 40px rgba(0,0,0,.55);
  transition: transform .25s ease, box-shadow .25s ease;
}}
.rd-ficha__mini:hover {{ transform: translateY(-3px); box-shadow: 0 22px 50px rgba(0,0,0,.65); }}
.rd-ficha__mini img {{ width: 100%; height: auto; display: block; }}
.rd-ficha__play {{
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  background: rgba(0,0,0,.28); opacity: 0; transition: opacity .25s ease;
}}
.rd-ficha__mini:hover .rd-ficha__play {{ opacity: 1; }}
.rd-ficha__play i {{
  width: 46px; height: 46px; border-radius: 999px; background: var(--acento);
  display: flex; align-items: center; justify-content: center;
  color: #0B0B0D; font-style: normal; font-size: 1rem; padding-left: 3px;
}}

@media (max-width: 700px) {{
  .rd-ficha__cuerpo {{ flex-direction: column-reverse; align-items: stretch; }}
  .rd-ficha__mini {{ flex: 1 1 auto; }}
}}

/* ---------- tarjetas de datos ---------- */

.rd-tarjetas {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: .7rem; }}
.rd-tarjeta {{
  border: 1px solid var(--borde); border-radius: var(--radio);
  background: var(--superficie); padding: .95rem 1.05rem;
}}
.rd-tarjeta__valor {{
  display: block; font-size: 1.5rem; font-weight: 600; color: var(--tinta);
  letter-spacing: -.02em; font-variant-numeric: tabular-nums;
}}
.rd-tarjeta__etiqueta {{
  display: block; margin-top: .2rem;
  font-size: .7rem; letter-spacing: .11em; text-transform: uppercase; color: var(--tinta-3);
}}
@media (max-width: 640px) {{ .rd-tarjetas {{ grid-template-columns: 1fr; }} }}

/* ---------- chips de advertencia ---------- */

.rd-chips {{ display: flex; flex-wrap: wrap; gap: .5rem; margin-top: .8rem; }}
.rd-chip {{
  display: inline-flex; align-items: center; gap: .4rem;
  font-size: .8rem; color: var(--tinta-2);
  border: 1px solid var(--borde); border-radius: 999px;
  padding: .34rem .8rem; background: rgba(255,255,255,.03);
}}
.rd-chip--ojo {{
  color: #F0C674; border-color: rgba(240,198,116,.28); background: rgba(240,198,116,.09);
}}
.rd-chip--guardado {{
  color: var(--acento); border-color: var(--acento-22); background: var(--acento-12);
}}

/* ---------- encabezado de sección ---------- */

.rd-seccion {{ display: flex; align-items: baseline; gap: .6rem; margin: 1.6rem 0 1rem; }}
.rd-seccion h2 {{
  font-family: 'Instrument Serif', Georgia, serif;
  font-size: 1.5rem; font-weight: 400; color: var(--tinta); margin: 0;
}}
.rd-seccion span {{ font-size: .82rem; color: var(--tinta-3); }}

/* ---------- biblioteca: una fila por informe ----------
   En rejilla, dos tarjetas vecinas con títulos de distinto largo quedaban a distinta
   altura y las filas no cuadraban. En lista eso no puede pasar, y además escala: con
   cien informes se recorre con la vista y se filtra con el buscador. */

.rd-fila {{
  display: flex; gap: 1rem; align-items: center;
  border: 1px solid var(--borde); border-radius: var(--radio);
  background: var(--superficie); padding: .75rem .9rem;
  transition: border-color .18s ease;
}}
.rd-fila:hover {{ border-color: var(--borde-vivo); }}
.rd-fila__mini {{
  flex: 0 0 124px; border-radius: 8px; overflow: hidden; line-height: 0;
  border: 1px solid var(--borde);
}}
.rd-fila__mini img {{ width: 100%; height: auto; display: block; }}
.rd-fila__texto {{ flex: 1; min-width: 0; }}
.rd-fila__titulo {{
  font-size: .95rem; font-weight: 600; color: var(--tinta); line-height: 1.35;
  /* Una sola línea con puntos suspensivos: los títulos de YouTube son larguísimos. */
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  margin-bottom: .3rem;
}}
.rd-fila__pie {{
  font-size: .76rem; color: var(--tinta-3);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.rd-fila__costo {{
  flex: 0 0 auto; text-align: right; font-size: .74rem; color: var(--tinta-3);
  font-family: ui-monospace, 'Cascadia Code', Menlo, monospace;
}}
.rd-fila__costo b {{ display: block; color: var(--acento); font-size: .86rem; font-weight: 600; }}

@media (max-width: 640px) {{
  .rd-fila {{ flex-wrap: wrap; }}
  .rd-fila__mini {{ flex: 0 0 96px; }}
  .rd-fila__costo {{ text-align: left; }}
}}

/* El botón va al costado de la fila, no debajo: apilado quedaba separado por el hueco
   propio de Streamlit y se leía como dos elementos sin relación. */
.st-key-biblioteca [data-testid="stHorizontalBlock"] {{ gap: .5rem; margin-bottom: .5rem; }}
.st-key-biblioteca .stButton button {{
  height: 62px; font-size: .78rem; font-weight: 500; color: var(--tinta-2);
}}
.st-key-biblioteca .stButton button:hover {{ color: var(--acento); }}

/* ---------- panel de consumo ---------- */

.rd-kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: .7rem; }}
.rd-kpi {{
  border: 1px solid var(--borde); border-radius: var(--radio);
  background: var(--superficie); padding: 1rem;
}}
.rd-kpi__valor {{
  display: block; font-size: 1.55rem; font-weight: 600; color: var(--tinta);
  letter-spacing: -.02em; font-variant-numeric: tabular-nums;
}}
.rd-kpi__valor.acento {{ color: var(--acento); }}
.rd-kpi__etiqueta {{
  display: block; margin-top: .25rem;
  font-size: .68rem; letter-spacing: .1em; text-transform: uppercase; color: var(--tinta-3);
}}
.rd-kpi__nota {{ display: block; margin-top: .35rem; font-size: .72rem; color: var(--tinta-3); }}
@media (max-width: 780px) {{ .rd-kpis {{ grid-template-columns: repeat(2, 1fr); }} }}

/* Destacado del tiempo ahorrado: es la única cifra que responde "¿esto para qué sirve?" */
.rd-ahorro {{
  position: relative; overflow: hidden;
  border: 1px solid var(--acento-22); border-radius: 18px;
  background: var(--acento-12); padding: 1.5rem 1.6rem; margin: 1rem 0;
}}
.rd-ahorro__cifra {{
  font-family: 'Instrument Serif', Georgia, serif;
  font-size: clamp(2.2rem, 5vw, 3.2rem); line-height: 1; color: var(--acento);
  letter-spacing: -.02em;
}}
.rd-ahorro__texto {{ margin-top: .6rem; font-size: .95rem; color: var(--tinta-2); max-width: 52ch; }}

/* Barras horizontales: gráfico propio para no romper la paleta con el de la librería. */
.rd-barras {{ margin-top: .4rem; }}
.rd-barra {{ display: flex; align-items: center; gap: .8rem; padding: .38rem 0; }}
.rd-barra__nombre {{
  flex: 0 0 44%; font-size: .8rem; color: var(--tinta-2);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.rd-barra__pista {{ flex: 1; height: 8px; border-radius: 999px; background: rgba(255,255,255,.05); }}
.rd-barra__valor {{ display: block; height: 100%; border-radius: 999px; background: var(--acento); }}
.rd-barra__cifra {{
  flex: 0 0 auto; font-size: .74rem; color: var(--tinta-3);
  font-family: ui-monospace, Menlo, monospace; font-variant-numeric: tabular-nums;
}}

/* ---------- selector de vista (Analizar / Biblioteca / Consumo) ---------- */

/* Streamlit llama a este widget `stButtonGroup`, no `stSegmentedControl`: con el
   nombre equivocado el selector no engancha nada y las vistas salen como botones
   sueltos. Verificado en el DOM. */
[data-testid="stButtonGroup"] {{
  margin-bottom: 1.4rem; gap: .3rem;
  border-bottom: 1px solid var(--borde);
}}
[data-testid="stBaseButton-segmented_control"],
[data-testid="stBaseButton-segmented_controlActive"] {{
  background: transparent; border: none; border-bottom: 2px solid transparent;
  border-radius: 0; height: 42px; padding: 0 1.1rem;
  font-size: .88rem; font-weight: 500; color: var(--tinta-3);
  transition: color .18s ease, border-color .18s ease;
}}
[data-testid="stBaseButton-segmented_control"]:hover {{
  color: var(--tinta); background: transparent; transform: none;
}}
[data-testid="stBaseButton-segmented_controlActive"] {{
  color: var(--acento); border-bottom-color: var(--acento); background: transparent;
}}
[data-testid="stBaseButton-segmented_controlActive"]:hover {{
  color: var(--acento); background: transparent; transform: none;
}}

/* ---------- espera ---------- */

.rd-espera {{
  display: flex; align-items: center; gap: .8rem;
  border: 1px solid var(--acento-22); border-radius: var(--radio);
  background: var(--acento-12); padding: 1rem 1.15rem;
  font-size: .94rem; color: var(--tinta-2);
}}
.rd-espera b {{ color: var(--tinta); font-weight: 600; }}
.rd-pulso {{
  width: 9px; height: 9px; border-radius: 999px; background: var(--acento);
  flex: 0 0 auto; animation: rd-latido 1.4s ease-in-out infinite;
}}
@keyframes rd-latido {{
  0%, 100% {{ opacity: 1; box-shadow: 0 0 0 0 var(--acento-40); }}
  50%      {{ opacity: .55; box-shadow: 0 0 0 7px transparent; }}
}}

/* ---------- el informe ---------- */

.st-key-informe {{ animation: rd-entrada .5s ease both; }}
@keyframes rd-entrada {{ from {{ opacity: 0; transform: translateY(8px); }} }}

.st-key-informe h2 {{
  font-family: 'Instrument Serif', Georgia, serif;
  font-size: 1.85rem; font-weight: 400; letter-spacing: -.01em; color: var(--tinta);
  margin: 2.6rem 0 1rem; padding-top: 1.7rem;
  border-top: 1px solid var(--borde);
}}
.st-key-informe h3 {{
  font-size: 1.02rem; font-weight: 600; color: var(--tinta); margin: 1.6rem 0 .6rem;
}}
.st-key-informe p, .st-key-informe li {{
  font-size: 1.01rem; line-height: 1.75; color: #D2D2D8;
}}
.st-key-informe li {{ margin-bottom: .45rem; }}
.st-key-informe strong {{ color: var(--tinta); font-weight: 600; }}
.st-key-informe a {{ color: var(--acento); text-decoration: none; border-bottom: 1px solid var(--acento-40); }}
.st-key-informe code {{
  background: var(--acento-12); color: var(--acento);
  padding: .12em .42em; border-radius: 6px; font-size: .88em;
}}
.st-key-informe blockquote {{
  border-left: 2px solid var(--acento); padding-left: 1rem; color: var(--tinta-2);
}}
/* El índice con minutos es una tabla: se le da aire y se destaca la columna del tiempo. */
.st-key-informe table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
.st-key-informe th {{
  text-align: left; font-size: .7rem; letter-spacing: .11em; text-transform: uppercase;
  color: var(--tinta-3); font-weight: 600; padding: .55rem .7rem;
  border-bottom: 1px solid var(--borde);
}}
.st-key-informe td {{
  padding: .6rem .7rem; font-size: .95rem; color: #D2D2D8;
  border-bottom: 1px solid rgba(255,255,255,.05);
}}
.st-key-informe td:first-child {{
  color: var(--acento); font-variant-numeric: tabular-nums; white-space: nowrap;
  font-weight: 500; width: 1%;
}}
.st-key-informe tr:hover td {{ background: rgba(255,255,255,.02); }}

/* ---------- controles de Streamlit ---------- */

[data-testid="stForm"] {{
  border: 1px solid var(--borde); border-radius: 18px;
  background: var(--superficie); padding: 1.3rem;
}}
[data-testid="stForm"] [data-testid="stVerticalBlock"] {{ gap: 1.1rem; }}
/* El alto va en la caja que Streamlit MIDE (`stTextInputRootElement`), no en el
   <input>. Forzarlo en el input lo hace desbordar su propio contenedor —que se sigue
   reservando 40 px— y comerse el hueco hasta chocar con el botón de abajo. */
[data-testid="stTextInputRootElement"] {{
  height: 54px; border-radius: 11px;
  background: rgba(0,0,0,.35); border: 1px solid var(--borde-vivo);
  transition: border-color .2s ease, box-shadow .2s ease;
}}
[data-testid="stTextInputRootElement"]:focus-within {{
  border-color: var(--acento); box-shadow: 0 0 0 3px var(--acento-22);
}}
[data-testid="stTextInput"] [data-baseweb="base-input"] {{
  height: 100%; background: transparent;
}}
[data-testid="stTextInput"] input {{
  height: 100%; background: transparent; border: none;
  color: var(--tinta); font-size: .98rem; padding-left: .9rem;
}}
[data-testid="stTextInput"] input::placeholder {{ color: var(--tinta-3); }}
[data-testid="stWidgetLabel"] p {{
  font-size: .74rem; letter-spacing: .11em; text-transform: uppercase;
  color: var(--tinta-3); font-weight: 600;
}}

.stButton button, .stFormSubmitButton button, .stDownloadButton button,
[data-testid="stFormSubmitButton"] button, [data-testid="stDownloadButton"] button {{
  border-radius: 11px; height: 48px; font-weight: 600; font-size: .95rem;
  border: 1px solid var(--borde-vivo); background: rgba(255,255,255,.05);
  color: var(--tinta); transition: transform .15s ease, background .2s ease, border-color .2s ease;
}}
.stButton button:hover, .stFormSubmitButton button:hover, .stDownloadButton button:hover,
[data-testid="stDownloadButton"] button:hover {{
  border-color: var(--acento-40); background: rgba(255,255,255,.08); transform: translateY(-1px);
}}
/* El botón primario (Analizar) es el único elemento sólido de la pantalla. */
.stFormSubmitButton button[kind="primaryFormSubmit"],
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"],
.stButton button[kind="primary"] {{
  background: var(--acento); color: #0B0B0D; border-color: transparent;
  box-shadow: 0 8px 24px var(--acento-22);
}}
.stFormSubmitButton button[kind="primaryFormSubmit"]:hover,
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]:hover,
.stButton button[kind="primary"]:hover {{
  background: var(--acento); filter: brightness(1.08); color: #0B0B0D;
}}

[data-testid="stExpander"] {{
  border: 1px solid var(--borde); border-radius: var(--radio);
  background: var(--superficie); overflow: hidden;
}}
[data-testid="stExpander"] summary {{ font-size: .9rem; color: var(--tinta-2); }}
[data-testid="stExpander"] summary:hover {{ color: var(--acento); }}

[data-testid="stAlert"] {{ border-radius: var(--radio); border: 1px solid var(--borde); }}

[data-testid="stCaptionContainer"] p, [data-testid="stCaptionContainer"] {{
  color: var(--tinta-3); font-size: .82rem;
}}
hr, [data-testid="stDivider"] hr {{ border-color: var(--borde); }}

/* Pie de tokens: monoespaciado para que las cifras se lean como telemetría. */
.rd-telemetria {{
  font-family: ui-monospace, 'Cascadia Code', Menlo, monospace;
  font-size: .76rem; color: var(--tinta-3); letter-spacing: .02em;
  display: flex; flex-wrap: wrap; gap: .55rem; margin: 1.6rem 0 .4rem;
}}
.rd-telemetria span {{
  border: 1px solid var(--borde); border-radius: 7px; padding: .22rem .55rem;
  background: rgba(255,255,255,.02);
}}
</style>
"""


def tinte(acento: str) -> str:
    """Solo las variables de color, para repintar sin reenviar la hoja entera.

    El color del video se conoce después de haber dibujado la página, así que en vez de
    inyectar otra hoja de estilos completa se manda este bloque diminuto: como llega
    más tarde en el documento, gana en la cascada y toda la pantalla se re-tiñe.
    """
    return f"""
<style>
:root {{
  --acento: {acento};
  --acento-12: {_rgba(acento, 0.12)};
  --acento-22: {_rgba(acento, 0.22)};
  --acento-40: {_rgba(acento, 0.40)};
}}
</style>
"""


def portada() -> str:
    """Pantalla de entrada, cuando todavía no se ha analizado nada."""
    # El sello de marca ya va arriba, en la barra de vistas: repetirlo aquí lo duplica.
    return """
<div class="rd-portada">
  <h1>Lee el informe,<br><em>no veas el video.</em></h1>
  <p>Pega un enlace y en segundos tienes el veredicto, el índice con minutos y los
     pasos accionables. Se leen los subtítulos del video, no el audio.</p>
</div>
"""


def portada_acceso() -> str:
    """Pantalla de la reja, cuando la app está publicada y pide clave."""
    return """
<div class="rd-portada">
  <div class="rd-marca"><span>&#9654;</span> Resumidor de YouTube</div>
  <h1>Esta app es <em>privada.</em></h1>
  <p>Analizar un video consume saldo de la API de quien la publicó, así que hace falta
     la clave para entrar.</p>
</div>
"""


def barra_marca() -> str:
    """Identidad reducida a un sello, para cuando la portada ya cedió su sitio al informe."""
    return '<div class="rd-portada rd-portada--sello"><div class="rd-marca">' '<span>&#9654;</span> Resumidor de YouTube</div></div>'


def ficha_video(meta, datos) -> str:
    """Cabecera del informe: miniatura real del video, título, canal y duración."""
    titulo = html.escape(meta.titulo) if meta.titulo else f"Video {meta.video_id}"
    canal = html.escape(meta.canal) if meta.canal else "YouTube"

    resplandor = (
        f'<div class="rd-ficha__resplandor" style="background-image:url({meta.fondo})"></div>'
        if meta.fondo
        else ""
    )
    miniatura = (
        f'<a class="rd-ficha__mini" href="{meta.url_video}" target="_blank" rel="noopener">'
        f'<img src="{meta.miniatura}" alt="Miniatura del video">'
        f'<span class="rd-ficha__play"><i>&#9654;</i></span></a>'
        if meta.miniatura
        else ""
    )

    return f"""
<div class="rd-ficha">
  {resplandor}
  <div class="rd-ficha__cuerpo">
    <div class="rd-ficha__texto">
      <div class="rd-ficha__canal">{canal}</div>
      <h2 class="rd-ficha__titulo">{titulo}</h2>
      <div class="rd-ficha__meta">
        <span>{datos.duracion_legible} de video</span>
        <span class="punto">&bull;</span>
        <span>{_miles(datos.palabras)} palabras</span>
        <span class="punto">&bull;</span>
        <span>lectura del informe ~2 min</span>
      </div>
    </div>
    {miniatura}
  </div>
</div>
"""


def tarjetas(datos) -> str:
    origen = "Automáticos" if datos.es_automatica else "Escritos a mano"
    return f"""
<div class="rd-tarjetas">
  <div class="rd-tarjeta">
    <span class="rd-tarjeta__valor">{datos.duracion_legible}</span>
    <span class="rd-tarjeta__etiqueta">Duración</span>
  </div>
  <div class="rd-tarjeta">
    <span class="rd-tarjeta__valor">{_miles(datos.palabras)}</span>
    <span class="rd-tarjeta__etiqueta">Palabras transcritas</span>
  </div>
  <div class="rd-tarjeta">
    <span class="rd-tarjeta__valor">{html.escape(datos.idioma).upper()}</span>
    <span class="rd-tarjeta__etiqueta">{origen}</span>
  </div>
</div>
"""


def chips(datos) -> str:
    """Advertencias sobre la calidad de la fuente, como etiquetas y no como alertas."""
    piezas = []

    if datos.es_automatica:
        piezas.append(
            '<span class="rd-chip rd-chip--ojo">&#9888; Subtítulos automáticos: '
            "revisa nombres propios y términos técnicos</span>"
        )
    if datos.fue_traducida:
        piezas.append(
            '<span class="rd-chip rd-chip--ojo">&#9888; Traducción automática de una '
            "transcripción automática</span>"
        )
    if datos.origen == "historial":
        piezas.append(
            f'<span class="rd-chip rd-chip--guardado">&#128190; Informe guardado el '
            f"{html.escape(datos.fecha_legible)}: no se gastaron tokens</span>"
        )
    elif datos.desde_cache:
        piezas.append(
            '<span class="rd-chip">&#8635; Desde la caché local: no se le pidió nada '
            "a YouTube</span>"
        )
    elif datos.origen == "yt-dlp":
        piezas.append(
            '<span class="rd-chip">&#8644; YouTube limitó la ruta principal: '
            "se usó el camino alternativo</span>"
        )

    if not piezas:
        return ""
    return f'<div class="rd-chips">{"".join(piezas)}</div>'


def espera(datos) -> str:
    """Aviso mientras Claude piensa: sin señal visible, una pausa se lee como app rota."""
    return f"""
<div class="rd-espera">
  <span class="rd-pulso"></span>
  <span>Claude está leyendo <b>{_miles(datos.palabras)} palabras</b>
        ({datos.duracion_legible} de video). El informe empieza a escribirse solo
        en unos segundos.</span>
</div>
"""


def seccion(titulo: str, nota: str = "") -> str:
    apunte = f"<span>{html.escape(nota)}</span>" if nota else ""
    return f'<div class="rd-seccion"><h2>{html.escape(titulo)}</h2>{apunte}</div>'


def fila_guardado(entrada, meta, costo_texto: str) -> str:
    """Una fila de la biblioteca: miniatura, título, canal, fecha y lo que costó."""
    titulo = html.escape(entrada.titulo) if entrada.titulo else f"Video {entrada.video_id}"
    canal = html.escape(entrada.canal) if entrada.canal else "YouTube"
    mini = (
        f'<div class="rd-fila__mini"><img src="{meta.miniatura}" alt=""></div>'
        if meta and meta.miniatura
        else ""
    )
    return f"""
<div class="rd-fila">
  {mini}
  <div class="rd-fila__texto">
    <div class="rd-fila__titulo">{titulo}</div>
    <div class="rd-fila__pie">{canal} &middot; {entrada.duracion_legible} de video
        &middot; {entrada.fecha_legible}</div>
  </div>
  <div class="rd-fila__costo"><b>{html.escape(costo_texto)}</b>
      {_miles(entrada.uso.get('entrada', 0) + entrada.uso.get('salida', 0))} tok</div>
</div>
"""


def kpis(tarjetas_kpi: list[tuple[str, str, str]]) -> str:
    """Fila de indicadores. Cada tarjeta es (valor, etiqueta, nota al pie)."""
    piezas = []
    for indice, (valor, etiqueta, nota) in enumerate(tarjetas_kpi):
        # El primero es el que importa (el costo): va en el color del video.
        clase = "rd-kpi__valor acento" if indice == 0 else "rd-kpi__valor"
        pie = f'<span class="rd-kpi__nota">{html.escape(nota)}</span>' if nota else ""
        piezas.append(
            f'<div class="rd-kpi"><span class="{clase}">{html.escape(valor)}</span>'
            f'<span class="rd-kpi__etiqueta">{html.escape(etiqueta)}</span>{pie}</div>'
        )
    return f'<div class="rd-kpis">{"".join(piezas)}</div>'


def ahorro(horas_video: float, horas_lectura: float) -> str:
    """El dato que responde para qué sirve la app: cuánto video no hubo que ver."""
    ahorradas = max(0.0, horas_video - horas_lectura)
    return f"""
<div class="rd-ahorro">
  <div class="rd-ahorro__cifra">{ahorradas:.1f} horas</div>
  <div class="rd-ahorro__texto">
    Es lo que te habrías tardado viendo estos videos completos
    ({horas_video:.1f} h) menos lo que cuesta leer sus informes
    ({horas_lectura:.1f} h, calculado a 200 palabras por minuto).
  </div>
</div>
"""


def barras(datos: list[tuple[str, float, str]]) -> str:
    """Gráfico de barras horizontales: (nombre, valor, cifra ya formateada)."""
    if not datos:
        return ""
    tope = max(valor for _, valor, _ in datos) or 1
    filas = "".join(
        f'<div class="rd-barra"><span class="rd-barra__nombre">{html.escape(nombre)}</span>'
        f'<span class="rd-barra__pista"><span class="rd-barra__valor" '
        f'style="width:{max(2, round(valor / tope * 100))}%"></span></span>'
        f'<span class="rd-barra__cifra">{html.escape(cifra)}</span></div>'
        for nombre, valor, cifra in datos
    )
    return f'<div class="rd-barras">{filas}</div>'


def telemetria(partes: list[str]) -> str:
    etiquetas = "".join(f"<span>{html.escape(parte)}</span>" for parte in partes)
    return f'<div class="rd-telemetria">{etiquetas}</div>'
