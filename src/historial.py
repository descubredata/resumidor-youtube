"""Biblioteca de informes ya generados.

Hasta ahora la app guardaba las **transcripciones** (para no volver a molestar a YouTube)
pero no los **informes**: al cerrar la pestaña, lo que Claude había escrito se perdía y
volver a abrir el mismo video costaba tokens otra vez.

Aquí cada informe queda en `historial/<video_id>.json`. Reabrirlo es gratis e instantáneo.
Un solo archivo por video: si se reanaliza, se sobrescribe con la versión nueva.

La entrada guarda además los pocos datos que la ficha necesita para dibujarse
(duración, palabras, idioma), de modo que un informe se puede abrir aunque se haya
borrado la carpeta `cache/`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

CARPETA = Path(__file__).resolve().parent.parent / "historial"


@dataclass
class Entrada:
    """Un informe guardado.

    Expone a propósito los mismos atributos que `transcripcion.Transcripcion` usa la
    interfaz (`duracion_legible`, `palabras`, `idioma`...), para que la ficha y las
    tarjetas puedan dibujarse con una entrada del historial sin ningún caso especial.
    """

    video_id: str
    titulo: str = ""
    canal: str = ""
    fecha: str = ""  # ISO, en hora local
    duracion_legible: str = ""
    palabras: int = 0
    idioma: str = "?"
    es_automatica: bool = False
    fue_traducida: bool = False
    informe: str = ""
    uso: dict = field(default_factory=dict)
    segundos: float = 0.0

    # La ficha comparte plantilla con el análisis en vivo; estos dos campos le dicen
    # de dónde salió lo que se está viendo.
    desde_cache: bool = True
    origen: str = "historial"

    @property
    def fecha_legible(self) -> str:
        try:
            return f"{datetime.fromisoformat(self.fecha):%d/%m/%Y %H:%M}"
        except ValueError:
            return self.fecha

    @property
    def duracion_seg(self) -> int:
        """Segundos de video, reconstruidos desde '23:45' o '1:03:12'.

        Se calcula en vez de guardarse para que los informes archivados antes de que
        existiera el panel de consumo también cuenten en los totales.
        """
        try:
            partes = [int(p) for p in self.duracion_legible.split(":")]
        except ValueError:
            return 0
        segundos = 0
        for parte in partes:
            segundos = segundos * 60 + parte
        return segundos

    @property
    def minutos_lectura(self) -> float:
        """Cuánto se tarda en leer el informe, a 200 palabras por minuto."""
        return len(self.informe.split()) / 200


def _ruta(video_id: str) -> Path:
    return CARPETA / f"{video_id}.json"


def guardar(datos, meta, informe: str, uso: dict, segundos: float) -> None:
    """Archiva el informe recién generado. Nunca interrumpe el flujo si falla."""
    entrada = Entrada(
        video_id=datos.video_id,
        titulo=meta.titulo,
        canal=meta.canal,
        fecha=datetime.now().isoformat(timespec="seconds"),
        duracion_legible=datos.duracion_legible,
        palabras=datos.palabras,
        idioma=datos.idioma,
        es_automatica=datos.es_automatica,
        fue_traducida=datos.fue_traducida,
        informe=informe,
        uso=uso or {},
        segundos=segundos,
    )
    try:
        CARPETA.mkdir(parents=True, exist_ok=True)
        _ruta(datos.video_id).write_text(
            json.dumps(asdict(entrada), ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


def leer(video_id: str) -> Entrada | None:
    ruta = _ruta(video_id)
    if not ruta.exists():
        return None
    try:
        return Entrada(**json.loads(ruta.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError, TypeError):
        return None


def listar(limite: int | None = None) -> list[Entrada]:
    """Informes guardados, del más reciente al más antiguo."""
    if not CARPETA.exists():
        return []

    entradas = [e for archivo in CARPETA.glob("*.json") if (e := leer(archivo.stem))]
    entradas.sort(key=lambda e: e.fecha, reverse=True)
    return entradas[:limite] if limite else entradas


def borrar(video_id: str) -> None:
    try:
        _ruta(video_id).unlink(missing_ok=True)
    except OSError:
        pass
