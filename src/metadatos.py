"""Metadatos visuales del video: título, canal, miniatura y color dominante.

Nada de esto es imprescindible para el informe. Si YouTube no responde o el video no
tiene miniatura en alta, la interfaz sigue funcionando con los campos vacíos: por eso
todo este módulo falla en silencio y nunca levanta excepciones hacia la app.

Las imágenes que usa la interfaz son las del propio video, no fotos de archivo. Salen
de dos rutas públicas que no piden API key:

- `https://www.youtube.com/oembed?...`  -> título y canal
- `https://img.youtube.com/vi/<id>/...` -> miniatura
"""

from __future__ import annotations

import base64
import colorsys
import json
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

CARPETA_CACHE = Path(__file__).resolve().parent.parent / "cache" / "visual"

# De mayor a menor calidad: YouTube no genera `maxresdefault` para todos los videos.
CALIDADES_MINIATURA = ("maxresdefault", "sddefault", "hqdefault", "mqdefault")

# Dorado tibio: el acento por defecto cuando no hay miniatura de la que sacar color.
COLOR_POR_DEFECTO = "#E4B45C"

TIEMPO_LIMITE = 6

# La miniatura se muestra a ~420 px de ancho; 640 basta para pantallas retina sin
# inflar el HTML (el data URI viaja incrustado en la página en cada re-render).
ANCHO_MINIATURA = 640
# El fondo va desenfocado por CSS, así que una imagen diminuta se ve idéntica a una
# grande y pesa ~4 KB en vez de ~60 KB.
ANCHO_FONDO = 160


@dataclass
class Metadatos:
    video_id: str
    titulo: str = ""
    canal: str = ""
    canal_url: str = ""
    miniatura: str = ""  # data URI listo para <img>
    fondo: str = ""  # data URI reducido, para el resplandor de fondo
    acento: str = COLOR_POR_DEFECTO

    @property
    def hay_imagen(self) -> bool:
        return bool(self.miniatura)

    @property
    def url_video(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"


def _oembed(video_id: str) -> dict:
    """Título y canal del video. Endpoint público, sin llave ni cuota."""
    try:
        respuesta = requests.get(
            "https://www.youtube.com/oembed",
            params={
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "format": "json",
            },
            timeout=TIEMPO_LIMITE,
        )
        respuesta.raise_for_status()
        return respuesta.json()
    except Exception:
        return {}


def _descargar_miniatura(video_id: str) -> Image.Image | None:
    """Baja la miniatura de mayor calidad disponible.

    YouTube responde 404 —o una imagen gris de relleno de 120x90— cuando esa calidad
    no existe, así que descartamos las respuestas sospechosamente pequeñas.
    """
    for calidad in CALIDADES_MINIATURA:
        try:
            respuesta = requests.get(
                f"https://img.youtube.com/vi/{video_id}/{calidad}.jpg",
                timeout=TIEMPO_LIMITE,
            )
            if respuesta.status_code != 200 or len(respuesta.content) < 3000:
                continue
            return Image.open(BytesIO(respuesta.content)).convert("RGB")
        except Exception:
            continue
    return None


def _recortar_a_panoramica(imagen: Image.Image) -> Image.Image:
    """Quita las bandas negras de las miniaturas 4:3.

    `hqdefault` y `mqdefault` vienen en 4:3 con barras arriba y abajo. Si las dejamos,
    el color dominante sale negro y la tarjeta se ve con marco sucio.
    """
    proporcion = imagen.width / imagen.height
    if proporcion >= 1.55:
        return imagen

    alto_util = round(imagen.width * 9 / 16)
    margen = (imagen.height - alto_util) // 2
    return imagen.crop((0, margen, imagen.width, margen + alto_util))


def _color_dominante(imagen: Image.Image) -> str:
    """Color vivo y representativo de la miniatura, ajustado para fondo oscuro.

    No sirve el color *más frecuente* a secas: en la mayoría de las miniaturas gana un
    gris o un blanco de fondo que no tiñe nada. Se busca el que combine presencia y
    saturación, y luego se normaliza para que el acento se lea igual de sólido venga
    de una miniatura apagada o de una saturadísima.
    """
    muestra = imagen.resize((120, 68))
    paleta = muestra.quantize(colors=10, method=Image.Quantize.MEDIANCUT)
    colores = paleta.convert("RGB").getcolors(120 * 68) or []

    mejor = None
    mejor_puntaje = -1.0
    for frecuencia, (r, g, b) in colores:
        tono, luz, saturacion = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        # Grises, negros de letterbox y blancos de titular: no funcionan como acento.
        if saturacion < 0.18 or luz < 0.12 or luz > 0.92:
            continue
        # Raíz de la frecuencia: que un color enorme y apagado no aplaste a uno
        # mediano y vibrante.
        puntaje = (frecuencia**0.5) * (saturacion + 0.35)
        if puntaje > mejor_puntaje:
            mejor, mejor_puntaje = (tono, luz, saturacion), puntaje

    if mejor is None:
        return COLOR_POR_DEFECTO

    tono, luz, saturacion = mejor
    saturacion = min(max(saturacion, 0.45), 0.85)
    luz = min(max(luz, 0.55), 0.70)
    r, g, b = colorsys.hls_to_rgb(tono, luz, saturacion)
    return "#{:02X}{:02X}{:02X}".format(round(r * 255), round(g * 255), round(b * 255))


def _a_data_uri(imagen: Image.Image, ancho: int, calidad: int) -> str:
    alto = max(1, round(imagen.height * ancho / imagen.width))
    copia = imagen.resize((ancho, alto), Image.LANCZOS)
    memoria = BytesIO()
    copia.save(memoria, format="JPEG", quality=calidad, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(memoria.getvalue()).decode()


def _ruta_cache(video_id: str) -> Path:
    return CARPETA_CACHE / f"{video_id}.json"


def _leer_cache(video_id: str) -> Metadatos | None:
    ruta = _ruta_cache(video_id)
    if not ruta.exists():
        return None
    try:
        return Metadatos(**json.loads(ruta.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError, TypeError):
        return None  # caché vieja o corrupta: se vuelve a construir


def _guardar_cache(meta: Metadatos) -> None:
    try:
        CARPETA_CACHE.mkdir(parents=True, exist_ok=True)
        _ruta_cache(meta.video_id).write_text(
            json.dumps(asdict(meta), ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass  # no poder cachear no debe romper nada


def obtener(video_id: str, usar_cache: bool = True) -> Metadatos:
    """Devuelve los metadatos visuales del video. Nunca lanza excepciones."""
    if usar_cache:
        guardado = _leer_cache(video_id)
        if guardado is not None:
            return guardado

    meta = Metadatos(video_id=video_id)

    datos = _oembed(video_id)
    meta.titulo = (datos.get("title") or "").strip()
    meta.canal = (datos.get("author_name") or "").strip()
    meta.canal_url = (datos.get("author_url") or "").strip()

    imagen = _descargar_miniatura(video_id)
    if imagen is not None:
        imagen = _recortar_a_panoramica(imagen)
        meta.acento = _color_dominante(imagen)
        meta.miniatura = _a_data_uri(imagen, ANCHO_MINIATURA, calidad=82)
        meta.fondo = _a_data_uri(imagen, ANCHO_FONDO, calidad=60)

    _guardar_cache(meta)
    return meta
