"""Reja de entrada para cuando la app está publicada en internet.

Una app pública que llama a la API de Claude **gasta el saldo de quien puso la llave**.
Sin una clave delante, cualquiera con el enlace analiza videos a tu costa.

La reja se enciende sola: si existe el secreto `RESUMIDOR_CLAVE`, pide contraseña; si no
existe —el caso normal en tu computador— la app abre directo y no estorba.
"""

from __future__ import annotations

import hmac

import streamlit as st

from . import credenciales, estilo


def _clave_configurada() -> str:
    return credenciales.obtener("RESUMIDOR_CLAVE", obligatoria=False)


def exigir_clave() -> bool:
    """Devuelve True si se puede seguir. Si no, dibuja la pantalla de entrada.

    El llamador debe cortar la ejecución (`st.stop()`) cuando esto devuelva False.
    """
    esperada = _clave_configurada()
    if not esperada:
        return True  # sin clave configurada: uso local, sin estorbos

    if st.session_state.get("acceso_ok"):
        return True

    st.html(estilo.portada_acceso())

    with st.form("acceso"):
        intento = st.text_input("Clave", type="password", label_visibility="collapsed")
        entrar = st.form_submit_button("Entrar", type="primary", use_container_width=True)

    if entrar:
        # `compare_digest` compara en tiempo constante: no delata cuántos caracteres
        # acertó quien esté probando claves.
        if hmac.compare_digest(intento, esperada):
            st.session_state.acceso_ok = True
            st.rerun()
        else:
            st.error("Clave incorrecta.")

    return False
