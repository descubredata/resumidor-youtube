"""Tarifas de la API de Claude, para poder poner un costo en dólares a cada informe.

⚠️ **Estas cifras se copian a mano de la documentación oficial y pueden quedar viejas.**
Fuente: https://platform.claude.com/docs/en/about-claude/pricing
Consultada el **17 de agosto de 2026**.

Si un modelo no está en la tabla, el costo se devuelve como `None` y la interfaz lo
muestra como "sin tarifa" en vez de inventarse un número.
"""

from __future__ import annotations

FECHA_TARIFAS = "17 ago 2026"
FUENTE = "platform.claude.com/docs/en/about-claude/pricing"

# (dólares por millón de tokens de entrada, dólares por millón de tokens de salida)
TARIFAS: dict[str, tuple[float, float]] = {
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


def _tarifa(modelo: str) -> tuple[float, float] | None:
    """Busca la tarifa tolerando los sufijos de fecha (`claude-haiku-4-5-20251001`)."""
    if not modelo:
        return None
    if modelo in TARIFAS:
        return TARIFAS[modelo]

    # El id que devuelve la API puede traer la fecha de la versión pegada al final.
    candidatos = [nombre for nombre in TARIFAS if modelo.startswith(nombre)]
    if not candidatos:
        return None
    return TARIFAS[max(candidatos, key=len)]


def costo(uso: dict) -> float | None:
    """Dólares que costó un informe. `None` si no conocemos la tarifa del modelo."""
    tarifa = _tarifa((uso or {}).get("modelo", ""))
    if tarifa is None:
        return None

    por_entrada, por_salida = tarifa
    entrada = (uso.get("entrada") or 0) / 1_000_000 * por_entrada
    salida = (uso.get("salida") or 0) / 1_000_000 * por_salida
    return entrada + salida


def formatear(dolares: float | None) -> str:
    """Los informes cuestan centavos: 4 decimales o no se ve nada."""
    if dolares is None:
        return "sin tarifa"
    if dolares < 0.01:
        return f"US$ {dolares:.4f}"
    return f"US$ {dolares:,.2f}".replace(",", ".")
