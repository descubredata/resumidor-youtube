"""Obtención de transcripciones de YouTube.

El agente no "ve" el video: lee los subtítulos que YouTube ya tiene generados
(manuales o automáticos) y trabaja sobre ese texto.

YouTube limita cuántas veces se le puede pedir lo mismo desde una misma conexión, así que
cada transcripción se guarda en `cache/` la primera vez: volver a analizar un video ya visto
no cuesta ni una sola petición.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api import (
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    VideoUnplayable,
)

from . import respaldo_ytdlp

# Orden de preferencia: español primero, luego inglés, luego portugués.
IDIOMAS_PREFERIDOS = ["es", "es-419", "es-ES", "en", "en-US", "en-GB", "pt", "pt-BR"]

CARPETA_CACHE = Path(__file__).resolve().parent.parent / "cache"

# YouTube responde con bloqueo cuando se le pide lo mismo varias veces seguidas. Suele
# durar segundos, así que reintentamos en silencio antes de molestar al usuario.
ESPERAS_REINTENTO = (3, 8)

_PATRONES_ID = [
    r"(?:youtube\.com/watch\?(?:.*&)?v=)([A-Za-z0-9_-]{11})",
    r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
    r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
    r"(?:youtube\.com/live/)([A-Za-z0-9_-]{11})",
    r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})",
]


class ErrorTranscripcion(Exception):
    """Error legible para mostrar en la interfaz."""


@dataclass
class Transcripcion:
    video_id: str
    idioma: str
    es_automatica: bool
    fue_traducida: bool
    duracion_seg: float
    texto_con_marcas: str
    palabras: int
    desde_cache: bool = False
    origen: str = "youtube-transcript-api"

    @property
    def duracion_legible(self) -> str:
        return formatear_tiempo(self.duracion_seg)


def extraer_video_id(url_o_id: str) -> str:
    """Acepta una URL de YouTube en cualquiera de sus formas, o el ID pelado."""
    texto = (url_o_id or "").strip()
    if not texto:
        raise ErrorTranscripcion("Pega el enlace del video.")

    if re.fullmatch(r"[A-Za-z0-9_-]{11}", texto):
        return texto

    for patron in _PATRONES_ID:
        encontrado = re.search(patron, texto)
        if encontrado:
            return encontrado.group(1)

    raise ErrorTranscripcion(
        "No reconozco ese enlace como un video de YouTube. "
        "Debe verse como https://www.youtube.com/watch?v=XXXXXXXXXXX o https://youtu.be/XXXXXXXXXXX"
    )


def formatear_tiempo(segundos: float) -> str:
    """1h 03m 12s -> '1:03:12'; 12m 34s -> '12:34'."""
    total = int(segundos)
    horas, resto = divmod(total, 3600)
    minutos, segs = divmod(resto, 60)
    if horas:
        return f"{horas}:{minutos:02d}:{segs:02d}"
    return f"{minutos}:{segs:02d}"


def _elegir_transcripcion(lista):
    """Devuelve (transcripcion, fue_traducida) según la preferencia de idioma.

    Prioridad: manual en idioma preferido > automática en idioma preferido >
    cualquiera traducida al español > la primera que haya.
    """
    try:
        return lista.find_manually_created_transcript(IDIOMAS_PREFERIDOS), False
    except NoTranscriptFound:
        pass

    try:
        return lista.find_generated_transcript(IDIOMAS_PREFERIDOS), False
    except NoTranscriptFound:
        pass

    # Idioma exótico: si se puede traducir, la traducimos al español.
    for transcripcion in lista:
        if getattr(transcripcion, "is_translatable", False):
            try:
                return transcripcion.translate("es"), True
            except Exception:
                pass  # no soporta español: nos quedamos con el idioma original
        return transcripcion, False

    raise ErrorTranscripcion("El video no tiene subtítulos disponibles.")


def _descargar(video_id: str) -> dict:
    """Pide los subtítulos a YouTube. Reintenta si nos limita la conexión."""
    api = YouTubeTranscriptApi()
    ultimo_bloqueo: Exception | None = None

    for espera in (0,) + ESPERAS_REINTENTO:
        if espera:
            time.sleep(espera)

        try:
            lista = api.list(video_id)
            elegida, fue_traducida = _elegir_transcripcion(lista)
            fragmentos = list(elegida.fetch())
            break
        except (RequestBlocked, IpBlocked) as error:
            ultimo_bloqueo = error
            continue
        except (TranscriptsDisabled, NoTranscriptFound):
            raise ErrorTranscripcion(
                "Este video no tiene subtítulos (ni automáticos), así que no hay texto que "
                "leer. Es el único caso que este agente no puede resolver: haría falta "
                "descargar el audio y transcribirlo aparte."
            )
        except (VideoUnavailable, VideoUnplayable):
            raise ErrorTranscripcion(
                "El video no está disponible (privado, borrado o con restricción)."
            )
        except ErrorTranscripcion:
            raise
        except Exception as error:  # red caída, cambio de formato de YouTube, etc.
            raise ErrorTranscripcion(f"No pude obtener la transcripción: {error}")
    else:
        # Ruta principal bloqueada: probamos con yt-dlp, que pide los subtítulos por otro
        # camino y normalmente sigue funcionando.
        try:
            return respaldo_ytdlp.descargar(video_id, IDIOMAS_PREFERIDOS)
        except respaldo_ytdlp.RespaldoNoDisponible as fallo_respaldo:
            raise ErrorTranscripcion(
                "YouTube está limitando las peticiones desde esta conexión y el camino "
                f"alternativo tampoco pasó. Suele ceder en unos minutos; pasa al analizar "
                "varios videos seguidos. Los videos ya analizados siguen funcionando porque "
                "quedan guardados en la carpeta cache/. "
                f"(Detalle: {type(ultimo_bloqueo).__name__} · respaldo: {fallo_respaldo})"
            )

    if not fragmentos:
        raise ErrorTranscripcion("La transcripción vino vacía.")

    return {
        "video_id": video_id,
        "idioma": getattr(elegida, "language_code", "?"),
        "es_automatica": bool(getattr(elegida, "is_generated", False)),
        "fue_traducida": fue_traducida,
        "origen": "youtube-transcript-api",
        "fragmentos": [
            {"inicio": f.start, "duracion": f.duration or 0, "texto": f.text}
            for f in fragmentos
        ],
    }


def _ruta_cache(video_id: str) -> Path:
    return CARPETA_CACHE / f"{video_id}.json"


def _leer_cache(video_id: str) -> dict | None:
    ruta = _ruta_cache(video_id)
    if not ruta.exists():
        return None
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        return datos if datos.get("fragmentos") else None
    except (json.JSONDecodeError, OSError):
        return None  # caché corrupta: se vuelve a bajar


def _guardar_cache(datos: dict) -> None:
    try:
        CARPETA_CACHE.mkdir(parents=True, exist_ok=True)
        _ruta_cache(datos["video_id"]).write_text(
            json.dumps(datos, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass  # no poder cachear no debe romper el análisis


def hay_en_cache(video_id: str) -> bool:
    """¿Está la transcripción en disco? Sirve para saber si abrir un informe guardado
    puede mostrar también el texto original sin salir a la red."""
    return _leer_cache(video_id) is not None


def obtener_transcripcion(
    url_o_id: str, marca_cada_seg: int = 60, usar_cache: bool = True
) -> Transcripcion:
    """Devuelve la transcripción con marcas de tiempo intercaladas.

    Las marcas (ej. `[12:34]`) son lo que después le permite al modelo citar el minuto
    exacto de cada tema, para poder saltar directo a lo que interesa.
    """
    video_id = extraer_video_id(url_o_id)

    datos = _leer_cache(video_id) if usar_cache else None
    desde_cache = datos is not None
    if datos is None:
        datos = _descargar(video_id)
        _guardar_cache(datos)

    lineas: list[str] = []
    proxima_marca = 0.0
    for fragmento in datos["fragmentos"]:
        if fragmento["inicio"] >= proxima_marca:
            lineas.append(f"\n[{formatear_tiempo(fragmento['inicio'])}]")
            proxima_marca = fragmento["inicio"] + marca_cada_seg
        lineas.append(fragmento["texto"].replace("\n", " ").strip())

    texto = " ".join(lineas).strip()
    ultimo = datos["fragmentos"][-1]

    return Transcripcion(
        video_id=video_id,
        idioma=datos["idioma"],
        es_automatica=datos["es_automatica"],
        fue_traducida=datos["fue_traducida"],
        duracion_seg=ultimo["inicio"] + ultimo["duracion"],
        texto_con_marcas=texto,
        palabras=len(texto.split()),
        desde_cache=desde_cache,
        origen=datos.get("origen", "youtube-transcript-api"),
    )
