"""Llamada a Claude para convertir la transcripción en un informe."""

from __future__ import annotations

import os

from anthropic import Anthropic

from . import credenciales, prompts

# Sonnet 5 es el punto de equilibrio para esta tarea: resumir texto largo con fidelidad.
# Cambiar a "claude-opus-5" si algún día se necesita más profundidad de análisis.
MODELO = credenciales.obtener("RESUMIDOR_MODELO", obligatoria=False) or "claude-sonnet-5"
# Un video de 24 min consumió 4.050 tokens de salida; este techo deja margen para
# conferencias y podcasts largos sin que el informe salga cortado.
MAX_TOKENS_SALIDA = 16000

class ErrorAnalisis(Exception):
    """Error legible para mostrar en la interfaz."""


def _api_key() -> str:
    """Entorno, secretos de Streamlit o archivo local. Ver `credenciales.py`."""
    try:
        return credenciales.obtener("ANTHROPIC_API_KEY")
    except credenciales.FaltaLlave as error:
        raise ErrorAnalisis(str(error))


def analizar(transcripcion, uso: dict | None = None):
    """Genera el informe en trozos, para que se vea escribiéndose en pantalla.

    Si se pasa `uso`, al terminar queda con los tokens realmente consumidos.
    """
    cliente = Anthropic(api_key=_api_key())
    mensaje = prompts.construir_mensaje(transcripcion)

    try:
        with cliente.messages.stream(
            model=MODELO,
            max_tokens=MAX_TOKENS_SALIDA,
            system=prompts.SISTEMA,
            messages=[{"role": "user", "content": mensaje}],
        ) as flujo:
            for fragmento in flujo.text_stream:
                yield fragmento

            if uso is not None:
                final = flujo.get_final_message()
                uso["entrada"] = final.usage.input_tokens
                uso["salida"] = final.usage.output_tokens
                uso["modelo"] = final.model
                # Un video muy largo puede agotar el presupuesto de salida y cortar el
                # informe a media frase; hay que avisarlo en pantalla.
                uso["truncado"] = final.stop_reason == "max_tokens"
    except ErrorAnalisis:
        raise
    except Exception as error:
        raise ErrorAnalisis(f"Falló la llamada a Claude: {error}")
