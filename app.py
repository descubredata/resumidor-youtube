"""Resumidor de videos de YouTube — interfaz local.

Tres vistas: **Analizar** (pegar un enlace y leer el informe), **Biblioteca** (los
informes ya guardados, con buscador) y **Consumo** (tokens, costo y tiempo ahorrado).
"""

from __future__ import annotations

import itertools
import re
import time
from datetime import datetime

import streamlit as st

from src import acceso, analisis, estilo, historial, metadatos, precios, transcripcion

st.set_page_config(
    page_title="Resumidor de YouTube",
    page_icon="▶",
    layout="centered",
    initial_sidebar_state="collapsed",
)

VISTAS = ["Analizar", "Biblioteca", "Consumo"]

for clave in ("informe", "datos", "meta", "uso", "segundos"):
    st.session_state.setdefault(clave, None)
st.session_state.setdefault("vista", "Analizar")

# Apertura de un informe archivado: la biblioteca solo deja anotado el video y provoca
# un rerun. Aquí se carga y se salta a la vista de lectura.
por_abrir = st.session_state.pop("abrir", None)
if por_abrir:
    guardado = historial.leer(por_abrir)
    if guardado:
        st.session_state.update(
            informe=guardado.informe,
            # La entrada del historial expone los mismos atributos que una
            # transcripción, así que la ficha y las tarjetas la dibujan sin cambios.
            datos=guardado,
            meta=metadatos.obtener(por_abrir),
            uso=guardado.uso,
            segundos=guardado.segundos,
            vista="Analizar",
        )


def aplicar_css(css: str) -> None:
    """Inyecta una hoja de estilos.

    ⚠️ Va por `st.markdown` y NO por `st.html`. Cuando a `st.html` se le pasa contenido
    que es *solo* `<style>`, Streamlit lo desvía a un contenedor de eventos aparte y
    ahí, medido en este proyecto, **los bloques de más de ~11.000 caracteres se pierden
    enteros y en silencio**: la página se queda con el tema básico y ni la consola ni la
    interfaz avisan de nada. `st.markdown` entrega la hoja completa.
    """
    st.markdown(css, unsafe_allow_html=True)


# La hoja de estilos se tiñe con el color dominante de la miniatura del video que se
# esté mostrando; sin video, el dorado por defecto.
acento = st.session_state.meta.acento if st.session_state.meta else metadatos.COLOR_POR_DEFECTO
aplicar_css(estilo.hoja_de_estilos(acento))

# Reja: solo aparece si hay una clave configurada (o sea, en la app publicada).
if not acceso.exigir_clave():
    st.stop()

st.html(estilo.barra_marca())
# Sin `default=`: el valor lo lleva `st.session_state["vista"]` (así abrir un informe
# desde la biblioteca puede saltar solo a la vista de lectura). Pasar ambos hace que
# Streamlit avise de conflicto por consola.
vista = st.segmented_control("Vista", VISTAS, key="vista", label_visibility="collapsed")


def cabecera(meta, datos) -> None:
    """Ficha del video, tarjetas de datos y advertencias de calidad de la fuente."""
    st.html(estilo.ficha_video(meta, datos))
    st.html(estilo.tarjetas(datos))
    aviso = estilo.chips(datos)
    if aviso:
        st.html(aviso)


# ══════════════════════════════════════════════════════════════════ ANALIZAR ══════

if vista == "Analizar":
    if not st.session_state.informe:
        st.html(estilo.portada())

    with st.form("entrada"):
        url = st.text_input(
            "Enlace del video",
            placeholder="https://www.youtube.com/watch?v=...",
        )
        enviar = st.form_submit_button("Analizar", type="primary", use_container_width=True)

    if enviar:
        st.session_state.update(informe=None, datos=None, meta=None, uso=None, segundos=None)

        try:
            with st.spinner("Buscando la transcripción (si YouTube limita, reintenta solo)..."):
                datos = transcripcion.obtener_transcripcion(url)
        except transcripcion.ErrorTranscripcion as error:
            st.error(str(error))
            st.stop()

        # Título, canal, miniatura y color de acento. Es decorativo: si falla, vuelve
        # vacío y la ficha se dibuja igual con el ID del video.
        meta = metadatos.obtener(datos.video_id)

        # El acento se conoce recién ahora: se manda solo el bloque de variables, que al
        # llegar más tarde en el documento gana en la cascada y re-tiñe la pantalla.
        aplicar_css(estilo.tinte(meta.acento))
        cabecera(meta, datos)

        uso: dict = {}
        inicio = time.monotonic()
        espera = st.empty()
        espera.html(estilo.espera(datos))

        with st.container(key="informe"):
            try:
                # Consumimos el primer trozo aparte: así el aviso de espera se mantiene
                # visible hasta que Claude realmente empieza a responder, en vez de
                # dejar la pantalla en blanco. Luego lo devolvemos al flujo.
                flujo = analisis.analizar(datos, uso)
                primero = next(flujo, None)
                espera.empty()

                if primero is None:
                    st.error(
                        "Claude no devolvió nada. Vuelve a intentarlo; si se repite, el "
                        "problema está en la llamada a la API, no en el video."
                    )
                    st.stop()

                informe = st.write_stream(itertools.chain([primero], flujo))
            except analisis.ErrorAnalisis as error:
                espera.empty()
                st.error(str(error))
                st.stop()

        segundos = time.monotonic() - inicio
        # Al archivo: es lo que permite volver a abrirlo mañana sin pagar tokens.
        historial.guardar(datos, meta, informe, uso, segundos)

        st.session_state.update(
            informe=informe, datos=datos, meta=meta, uso=uso, segundos=segundos
        )

    # El informe se repinta desde la memoria de la sesión para que no desaparezca al
    # usar el botón de descarga (cada clic reejecuta el script).
    elif st.session_state.informe:
        cabecera(st.session_state.meta, st.session_state.datos)
        with st.container(key="informe"):
            st.markdown(st.session_state.informe)

    if st.session_state.informe:
        datos = st.session_state.datos
        meta = st.session_state.meta
        uso = st.session_state.uso or {}

        if uso.get("truncado"):
            st.warning(
                "El informe se cortó por longitud: el video es demasiado largo para el "
                f"tope de {analisis.MAX_TOKENS_SALIDA:,} tokens de salida. Súbelo en "
                "`src/analisis.py`.".replace(",", "."),
                icon="⚠️",
            )

        detalles = [f"{st.session_state.segundos:.0f} s"] if st.session_state.segundos else []
        if uso:
            detalles += [
                uso.get("modelo", analisis.MODELO),
                f"{uso.get('entrada', 0):,} tokens entrada".replace(",", "."),
                f"{uso.get('salida', 0):,} salida".replace(",", "."),
                precios.formatear(precios.costo(uso)),
            ]
        if detalles:
            st.html(estilo.telemetria(detalles))

        # Un informe recién hecho lleva la fecha de hoy; uno del archivo, la suya.
        fecha = getattr(datos, "fecha_legible", None) or f"{datetime.now():%d/%m/%Y %H:%M}"
        encabezado = (
            f"# {meta.titulo or 'Informe del video'}\n\n"
            f"- Canal: {meta.canal or '—'}\n"
            f"- Enlace: {meta.url_video}\n"
            f"- Duración: {datos.duracion_legible}\n"
            f"- Analizado: {fecha}\n\n---\n\n"
        )

        st.download_button(
            "Descargar el informe (.md)",
            data=encabezado + st.session_state.informe,
            file_name=f"informe_{datos.video_id}.md",
            mime="text/markdown",
            use_container_width=True,
        )

        # Una entrada del historial no carga el texto original; se recupera de la caché
        # solo si sigue ahí, para no salir a YouTube por abrir un informe viejo.
        texto = getattr(datos, "texto_con_marcas", "")
        if not texto and transcripcion.hay_en_cache(datos.video_id):
            texto = transcripcion.obtener_transcripcion(datos.video_id).texto_con_marcas

        if texto:
            with st.expander("Ver la transcripción completa"):
                # Una línea por marca de tiempo, para poder leerla y buscar en ella.
                st.text(re.sub(r"\s*(\[\d+:\d{2}(?::\d{2})?\])\s*", r"\n\1 ", texto).strip())


# ════════════════════════════════════════════════════════════════ BIBLIOTECA ══════

elif vista == "Biblioteca":
    entradas = historial.listar()

    if not entradas:
        st.html(estilo.seccion("Tu biblioteca", "todavía no hay informes guardados"))
        st.info("Analiza un video y su informe aparecerá aquí, listo para releer gratis.")
    else:
        st.html(estilo.seccion("Tu biblioteca", "abrir un informe no gasta tokens"))

        columnas = st.columns([3, 2])
        with columnas[0]:
            busqueda = st.text_input(
                "Buscar", placeholder="Buscar por título o canal...",
                label_visibility="collapsed",
            )
        with columnas[1]:
            orden = st.selectbox(
                "Orden",
                ["Más recientes", "Más antiguos", "Video más largo", "Más caro"],
                label_visibility="collapsed",
            )

        texto = (busqueda or "").strip().lower()
        if texto:
            entradas = [
                e for e in entradas
                if texto in e.titulo.lower() or texto in e.canal.lower()
            ]

        if orden == "Más antiguos":
            entradas.reverse()
        elif orden == "Video más largo":
            entradas.sort(key=lambda e: e.duracion_seg, reverse=True)
        elif orden == "Más caro":
            entradas.sort(key=lambda e: precios.costo(e.uso) or 0, reverse=True)

        st.caption(
            f"{len(entradas)} de {len(historial.listar())} informes"
            if texto else f"{len(entradas)} informes"
        )

        with st.container(key="biblioteca"):
            for entrada in entradas:
                fila, accion = st.columns([6, 1], vertical_alignment="center")
                with fila:
                    st.html(
                        estilo.fila_guardado(
                            entrada,
                            metadatos.obtener(entrada.video_id),
                            precios.formatear(precios.costo(entrada.uso)),
                        )
                    )
                with accion:
                    if st.button(
                        "Abrir",
                        key=f"abrir_{entrada.video_id}",
                        use_container_width=True,
                    ):
                        st.session_state.abrir = entrada.video_id
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════ CONSUMO ══════

elif vista == "Consumo":
    entradas = historial.listar()

    if not entradas:
        st.html(estilo.seccion("Consumo", "sin datos todavía"))
        st.info("Cuando analices tu primer video aparecerán aquí los tokens y el costo.")
    else:
        st.html(estilo.seccion("Consumo", f"tarifas de {precios.FECHA_TARIFAS}"))

        tokens_entrada = sum(e.uso.get("entrada", 0) for e in entradas)
        tokens_salida = sum(e.uso.get("salida", 0) for e in entradas)
        costos = [precios.costo(e.uso) for e in entradas]
        conocidos = [c for c in costos if c is not None]
        total = sum(conocidos)
        sin_tarifa = len(costos) - len(conocidos)

        st.html(
            estilo.kpis([
                (precios.formatear(total), "Costo total", f"{len(conocidos)} informes tarifados"),
                (str(len(entradas)), "Informes", "guardados en la biblioteca"),
                (
                    f"{(tokens_entrada + tokens_salida) / 1000:,.1f}k".replace(",", "."),
                    "Tokens",
                    f"{tokens_entrada / 1000:.0f}k entrada · {tokens_salida / 1000:.0f}k salida",
                ),
                (
                    precios.formatear(total / len(conocidos)) if conocidos else "—",
                    "Costo por informe",
                    "promedio",
                ),
            ])
        )

        if sin_tarifa:
            st.caption(
                f"{sin_tarifa} informe(s) usaron un modelo sin tarifa en `src/precios.py` "
                "y no suman al costo."
            )

        st.html(
            estilo.ahorro(
                horas_video=sum(e.duracion_seg for e in entradas) / 3600,
                horas_lectura=sum(e.minutos_lectura for e in entradas) / 60,
            )
        )

        st.html(estilo.seccion("En qué se fue el dinero"))
        st.html(
            estilo.barras([
                (
                    e.titulo or e.video_id,
                    precios.costo(e.uso) or 0,
                    precios.formatear(precios.costo(e.uso)),
                )
                for e in sorted(entradas, key=lambda x: precios.costo(x.uso) or 0, reverse=True)[:10]
            ])
        )

        st.html(estilo.seccion("Detalle", "una fila por informe"))
        st.dataframe(
            [
                {
                    "Video": e.titulo or e.video_id,
                    "Fecha": e.fecha_legible,
                    "Duración": e.duracion_legible,
                    "Modelo": e.uso.get("modelo", "?"),
                    "Entrada": e.uso.get("entrada", 0),
                    "Salida": e.uso.get("salida", 0),
                    "Costo USD": round(precios.costo(e.uso), 4) if precios.costo(e.uso) else None,
                    "Segundos": round(e.segundos),
                }
                for e in entradas
            ],
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            f"Tarifas copiadas a mano de {precios.FUENTE} el {precios.FECHA_TARIFAS}. "
            "Si Anthropic las cambia, hay que actualizarlas en `src/precios.py`."
        )
