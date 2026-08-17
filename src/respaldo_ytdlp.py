"""Camino alternativo para bajar subtítulos, con yt-dlp.

Cuando YouTube limita las peticiones de la ruta principal (`youtube-transcript-api`),
yt-dlp suele seguir funcionando porque pide los subtítulos por otro camino. Devuelve
exactamente la misma estructura que la ruta principal, así que el resto del programa no
nota la diferencia.

Regla importante: solo se piden pistas que EXISTEN en el video. Si se le pide un idioma
con comodín, YouTube inventa una traducción automática de la transcripción automática
—doblemente degradada— y arruina los términos técnicos. Antes de bajar nada se consulta
el catálogo real de pistas.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SEGUNDOS_LIMITE = 120


class RespaldoNoDisponible(Exception):
    """yt-dlp no está instalado o tampoco pudo traer los subtítulos."""


def _correr(argumentos: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            [sys.executable, "-m", "yt_dlp", *argumentos],
            capture_output=True,
            text=True,
            timeout=SEGUNDOS_LIMITE,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise RespaldoNoDisponible("yt-dlp tardó demasiado y se canceló.")
    except FileNotFoundError:
        raise RespaldoNoDisponible("yt-dlp no está instalado (pip install yt-dlp).")


def _catalogo(video_id: str) -> tuple[dict, dict, str]:
    """Devuelve (pistas manuales, pistas automáticas, idioma original del video)."""
    resultado = _correr(
        [
            "-J",
            "--skip-download",
            "--no-warnings",
            f"https://www.youtube.com/watch?v={video_id}",
        ]
    )
    if resultado.returncode != 0 or not resultado.stdout.strip():
        detalle = (resultado.stderr or "").strip().splitlines()
        raise RespaldoNoDisponible(
            f"yt-dlp no pudo leer el video ({detalle[-1] if detalle else 'sin detalle'})"
        )

    try:
        info = json.loads(resultado.stdout)
    except json.JSONDecodeError:
        raise RespaldoNoDisponible("yt-dlp devolvió una respuesta que no pude interpretar.")

    return (
        info.get("subtitles") or {},
        info.get("automatic_captions") or {},
        info.get("language") or "",
    )


def _elegir_pista(
    manuales: dict, automaticas: dict, idioma_original: str, preferidos: list[str]
) -> tuple[str, bool]:
    """Devuelve (código de la pista, es_automatica) sin aceptar traducciones inventadas."""

    def buscar(disponibles: dict) -> str | None:
        for preferido in preferidos:
            # La variante `-orig` es la transcripción original, nunca una traducción.
            for candidato in (f"{preferido}-orig", preferido):
                if candidato in disponibles:
                    return candidato
        return None

    elegida = buscar(manuales)
    if elegida:
        return elegida, False

    elegida = buscar(automaticas)
    if elegida:
        return elegida, True

    # Ningún idioma preferido: nos quedamos con el original del video, que es fiel.
    for candidato in (f"{idioma_original}-orig", idioma_original):
        if candidato in automaticas:
            return candidato, True
        if candidato in manuales:
            return candidato, False

    raise RespaldoNoDisponible("el video no tiene ninguna pista de subtítulos.")


def _parsear_json3(ruta: Path) -> list[dict]:
    """Convierte el formato json3 de YouTube en fragmentos limpios.

    Los subtítulos automáticos traen eventos de "append" que repiten el texto anterior
    para simular el efecto de máquina de escribir; se descartan para no duplicar todo.
    """
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    fragmentos: list[dict] = []

    for evento in contenido.get("events", []):
        if evento.get("aAppend") == 1 or "segs" not in evento:
            continue

        texto = "".join(seg.get("utf8", "") for seg in evento["segs"]).strip()
        if not texto:
            continue

        fragmentos.append(
            {
                "inicio": evento.get("tStartMs", 0) / 1000,
                "duracion": evento.get("dDurationMs", 0) / 1000,
                "texto": texto.replace("\n", " "),
            }
        )

    return fragmentos


def descargar(video_id: str, preferidos: list[str]) -> dict:
    """Baja los subtítulos y los devuelve en el formato de la ruta principal."""
    manuales, automaticas, idioma_original = _catalogo(video_id)
    pista, es_automatica = _elegir_pista(manuales, automaticas, idioma_original, preferidos)

    with tempfile.TemporaryDirectory(prefix="resumidor_") as temporal:
        carpeta = Path(temporal)
        bandera = "--write-auto-subs" if es_automatica else "--write-subs"

        resultado = _correr(
            [
                "--skip-download",
                "--no-warnings",
                "--quiet",
                bandera,
                "--sub-langs",
                pista,  # código exacto: nunca comodines, para no provocar traducciones
                "--sub-format",
                "json3",
                "-o",
                str(carpeta / "%(id)s"),
                f"https://www.youtube.com/watch?v={video_id}",
            ]
        )

        archivos = list(carpeta.glob("*.json3"))
        if not archivos:
            detalle = (resultado.stderr or "").strip().splitlines()
            raise RespaldoNoDisponible(
                f"yt-dlp no escribió la pista '{pista}' "
                f"({detalle[-1] if detalle else 'sin detalle'})"
            )

        fragmentos = _parsear_json3(archivos[0])

    if not fragmentos:
        raise RespaldoNoDisponible(f"la pista '{pista}' vino vacía.")

    codigo_base = pista.removesuffix("-orig")
    return {
        "video_id": video_id,
        "idioma": codigo_base,
        "es_automatica": es_automatica,
        # Solo sería traducción si la pista no fuera del idioma hablado en el video.
        "fue_traducida": bool(idioma_original) and codigo_base != idioma_original,
        "origen": "yt-dlp",
        "fragmentos": fragmentos,
    }
