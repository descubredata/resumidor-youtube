# Resumidor de YouTube

Pega el enlace de un video y obtén un informe que te ahorra verlo.

## Cómo se usa

Doble clic en **`run.bat`**. Abre el navegador en `http://localhost:8520`, pegas el enlace,
das clic en *Analizar* y en ~20 segundos tienes el informe. Botón para descargarlo en `.md`.

Para cerrarlo: `Ctrl+C` en la ventana negra, o simplemente ciérrala.

## Qué hace exactamente

1. Baja los **subtítulos** del video desde YouTube (`youtube-transcript-api`) e intercala
   marcas de tiempo cada 60 segundos.
2. Le pasa ese texto a **Claude** (`claude-sonnet-5`) con instrucciones de analista.
3. Devuelve seis secciones: *Veredicto* (¿vale la pena verlo?), *Lo esencial*,
   *Índice con minutos*, *Datos y cifras*, *Pasos accionables* y *Cabos sueltos*.

Prefiere subtítulos en español; si no hay, inglés o portugués; si el video está en un idioma
exótico, los traduce. Avisa en pantalla cuando los subtítulos son automáticos, porque traen
errores de audio en nombres propios y términos técnicos.

## Cuando YouTube dice que no

YouTube limita cuántas transcripciones se le piden desde una misma conexión. Aparece al
analizar varios videos seguidos y **no es un error de la app**. Hay tres defensas, en orden:

1. **Caché en disco** (`cache/`): un video ya analizado no vuelve a pedirle nada a YouTube.
   Reanalizarlo es instantáneo.
2. **Reintentos** de 3 y 8 segundos, en silencio.
3. **Camino alternativo con `yt-dlp`**, que pide los subtítulos por otra ruta. Verificado:
   entrega exactamente la misma transcripción que la ruta principal (4.400 palabras, 0 % de
   desvío, en el mismo video de prueba).

Si las tres fallan, el bloqueo cede solo en unos minutos.

⚠️ **Nunca se piden idiomas con comodín.** Si a YouTube se le pide un idioma que el video no
tiene, inventa una traducción automática *de la transcripción automática* — doblemente
degradada, con los términos técnicos destrozados. El respaldo consulta primero el catálogo
real de pistas y solo pide códigos que existan, prefiriendo la variante `-orig`.

## Límite conocido

**No procesa el audio.** Si un video no tiene subtítulos —ni automáticos— no hay texto que
leer y la app lo dice. Es poco frecuente, pero pasa (audio muy ruidoso, música, algunos
directos). Resolverlo requeriría descargar el audio y transcribirlo con un modelo de voz;
no está implementado.

## Consumo real medido

Un video de 3:31 gastó **1.949 tokens de entrada / 580 de salida**. Escalando linealmente,
una hora de video ronda los 33.000 tokens de entrada. La app imprime los tokens exactos de
cada análisis debajo del informe, para poder calcular el costo con la tarifa vigente.

## Publicarla en internet

Se publica en **Streamlit Community Cloud** (gratis, hecho por los mismos de Streamlit).
No hace falta servidor, ni Docker, ni tarjeta: se conecta a un repositorio de GitHub y
listo. Los pasos, tal cual:

1. Entra a **share.streamlit.io** y conéctate con tu cuenta de GitHub.
2. *Create app* → elige este repositorio, rama `main`, archivo principal `app.py`.
3. *Advanced settings* → **Secrets**: pega el contenido de
   `.streamlit/secrets.toml.ejemplo` con tus valores reales.
4. *Deploy*. En un par de minutos tienes una dirección `...streamlit.app` para compartir.

Para actualizarla después: subes los cambios a GitHub y la app se redespliega sola.

### 🔒 Antes de darle el enlace a nadie

**Pon `RESUMIDOR_CLAVE` en los secretos.** Cada análisis lo paga la llave de la API que
está en esa app: sin clave, cualquiera con el enlace gasta tu saldo. Si el secreto
existe, la app pide contraseña; si no existe, entra directo (que es lo que quieres en tu
computador, pero no en internet).

### ⚠️ El límite serio: YouTube bloquea a los servidores

Esta es la razón por la que la app publicada **no es igual de confiable que la local**.
Lo dice la propia librería de subtítulos en su código:

> *"You are doing requests from an IP belonging to a cloud provider (like AWS, Google
> Cloud Platform, Azure, etc.). Unfortunately, most IPs from cloud providers are blocked
> by YouTube."*

Traducido: desde tu casa YouTube casi siempre responde; desde un servidor gratuito, casi
siempre bloquea. El camino alternativo con `yt-dlp` sale por esa misma IP, así que
tampoco salva. Resolverlo de verdad exige **proxies de pago**, que es justo la
complicación que no queremos para enseñar.

**Cómo se convive con eso, y funciona:** un video ya analizado no le pide nada a YouTube.
Así que para una clase se **suben los videos ya cacheados junto con el código** —
`cache/*.json` y `historial/*.json`— y la demo corre perfecta delante de los alumnos.
Analizar un video nuevo en vivo es "a ver si pasa", y conviene tener un plan B.

Por eso `.gitignore` excluye `historial/` y `cache/visual/` por defecto: son tuyos y
pesan. Si quieres llevártelos a la demo, súbelos a mano con `git add -f`.

### Lo que NO sirve aquí

- **Vercel y Netlify** no ejecutan Streamlit: sirven páginas, no un proceso de Python
  vivo. La app no arranca.
- **Hugging Face Spaces** sí funciona y también es gratis, por si quieres una alternativa
  donde los archivos se suben arrastrándolos en el navegador, sin git.

## Las tres vistas

**Analizar** · pegas el enlace y lees el informe.

**Biblioteca** · todos los informes guardados, uno por fila con su miniatura, lo que
costó y cuántos tokens gastó. Tiene **buscador** por título o canal y orden por fecha,
duración o costo, para que siga sirviendo cuando haya cien. **Abrir uno es instantáneo y
no gasta tokens.**

**Consumo** · cuánto llevas gastado. Costo total en dólares, tokens de entrada y salida,
costo promedio por informe, gráfico de en qué se fue el dinero y una tabla con el detalle.
Arriba de todo, las **horas de video que te ahorraste**: la suma de las duraciones menos
lo que cuesta leer los informes, a 200 palabras por minuto.

Cada informe se guarda en `historial/<video_id>.json`. Uno por video: reanalizar
sobrescribe. Para olvidar un informe borra su archivo; para vaciar todo, borra la carpeta.

⚠️ **Los precios de la API están escritos a mano** en `src/precios.py`, copiados de
`platform.claude.com/docs/en/about-claude/pricing` el 17 de agosto de 2026
(Sonnet 5: US$2 por millón de tokens de entrada, US$10 de salida). Si Anthropic los
cambia, hay que actualizar ese archivo. Un modelo que no esté en la tabla se muestra
como "sin tarifa" en vez de inventar una cifra.

## Cómo se ve

Base oscura, tipografía editorial (serif en los títulos) y **las imágenes del propio
video**: no hay fotos de archivo en ninguna parte.

- La **miniatura en alta** encabeza el informe, junto al título y el canal reales.
- Esa misma miniatura, ampliada y desenfocada, hace de **luz de fondo** en la ficha.
- El **color de acento se calcula de la miniatura** de cada video, así que la página se
  tiñe del color del contenido que está resumiendo. Si la miniatura no existe, dorado.

Todo eso sale de dos rutas públicas de YouTube que no piden API key (`oembed` para el
título y el canal, `img.youtube.com` para la miniatura) y se guarda en `cache/visual/`.
Si YouTube no responde, la ficha se dibuja igual con el ID del video: es decoración, y
nunca puede tumbar el análisis.

## Ajustes

- **Qué extrae**: `src/prompts.py`. Editar las secciones de `PLANTILLA` cambia el informe;
  es texto plano, no hace falta programar.
- **Aspecto**: `src/estilo.py`. Los colores base están en el bloque `:root` del principio.
- **Modelo**: variable de entorno `RESUMIDOR_MODELO` (por defecto `claude-sonnet-5`).
  Para análisis más profundos, `claude-opus-5`.
- **Densidad de marcas de tiempo**: parámetro `marca_cada_seg` en
  `src/transcripcion.py` (60 s por defecto).

## Credenciales

Toma `ANTHROPIC_API_KEY` de las variables de entorno y, si no está ahí, de
`C:\5. Credenciales\.env.credentials`. No hay llaves escritas en el código.

## Archivos

```
run.bat                  arranca la app
app.py                   interfaz (Streamlit)
src/transcripcion.py     baja y normaliza los subtítulos, caché y reintentos
src/respaldo_ytdlp.py    camino alternativo cuando YouTube bloquea
src/analisis.py          llamada a Claude (streaming)
src/prompts.py           instrucciones del analista  <- lo que se ajusta seguido
src/metadatos.py         miniatura, título, canal y color dominante del video
src/estilo.py            hoja de estilos y bloques de HTML de la interfaz
src/historial.py         guarda y recupera los informes ya generados
src/precios.py           tarifas de la API para calcular el costo en dólares
.streamlit/config.toml   tema oscuro de arranque y puerto 8520
cache/                   transcripciones guardadas (se puede borrar sin miedo)
cache/visual/            miniaturas y metadatos (también se puede borrar)
historial/               los informes; borrar un archivo lo saca de la biblioteca
```

⚠️ `src/estilo.py` usa selectores `[data-testid="..."]`, que son API **interna** de
Streamlit. Si algún día se actualiza la librería y un control se ve desalineado, es ahí
—y solo ahí— donde hay que mirar. El motor no depende de nada de eso.

⚠️ **La hoja de estilos se inyecta con `st.markdown(..., unsafe_allow_html=True)`, nunca
con `st.html`.** Cuando `st.html` recibe contenido que es *solo* `<style>`, Streamlit lo
desvía a un contenedor aparte que **descarta los bloques de más de ~11.000 caracteres,
enteros y en silencio**: la app se ve con el tema básico y no aparece ningún error ni en
pantalla ni en la consola. Está medido; el ayudante `aplicar_css()` de `app.py` existe
solo para eso.
