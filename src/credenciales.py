"""De dónde sale la llave de la API, según dónde esté corriendo la app.

Se busca en tres sitios, en este orden:

1. **Variable de entorno** `ANTHROPIC_API_KEY` — lo habitual al correr desde consola.
2. **Secretos de Streamlit** (`.streamlit/secrets.toml` en local, el panel *Secrets* en
   Streamlit Community Cloud) — es la vía cuando la app está publicada, porque en un
   servidor no existe la carpeta de credenciales del computador.
3. **Archivo central de credenciales** del equipo — solo tiene sentido en la máquina
   propia.

Nunca hay llaves escritas en el código, y por eso el repositorio se puede publicar.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

ARCHIVO_CREDENCIALES = Path(r"C:\5. Credenciales\.env.credentials")


class FaltaLlave(Exception):
    """No se encontró la llave por ninguna de las tres vías."""


def _de_los_secretos(nombre: str) -> str:
    """Lee un secreto de Streamlit sin reventar si no hay archivo ni panel.

    `st.secrets` levanta excepción cuando no existe `secrets.toml`, que es justo el
    caso normal en la máquina local. Por eso va envuelto.
    """
    try:
        import streamlit as st

        return str(st.secrets.get(nombre, "")).strip()
    except Exception:
        return ""


def _del_archivo(nombre: str) -> str:
    if not ARCHIVO_CREDENCIALES.exists():
        return ""
    try:
        valores = dotenv_values(ARCHIVO_CREDENCIALES, encoding="utf-8")
        return (valores.get(nombre) or "").strip().strip('"').strip("'")
    except OSError:
        return ""


def obtener(nombre: str, obligatoria: bool = True) -> str:
    """Devuelve el valor del secreto pedido, o cadena vacía si no es obligatorio."""
    for valor in (
        os.environ.get(nombre, "").strip(),
        _de_los_secretos(nombre),
        _del_archivo(nombre),
    ):
        if valor:
            return valor

    if not obligatoria:
        return ""

    raise FaltaLlave(
        f"No encontré {nombre}. En tu computador va como variable de entorno o en "
        f"{ARCHIVO_CREDENCIALES}; en la app publicada, en el panel «Secrets» de "
        "Streamlit Cloud."
    )
