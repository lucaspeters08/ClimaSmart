"""
ClimaSmart - Servidor Flask
Proyecto escolar de: Lucas Bertinotti Peterseim y Dante Santos

Qué hace este archivo (backend):
  1. Recibe del navegador una ciudad o unas coordenadas (lat/lon).
  2. Le pregunta el clima a la API de OpenWeather.
  3. Le pide un consejo a la IA (Google Gemini).
  4. Si la IA falla (sin clave, sin cuota, sin internet...), genera el consejo
     con reglas propias en Python (sistema de RESPALDO o "fallback").
  5. Devuelve todo junto al navegador en formato JSON.

Las claves secretas viven SOLO acá, en el archivo .env. El navegador nunca las ve.
"""

import os

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

# ---------------------------------------------------------------------------
# 1. CONFIGURACIÓN
# ---------------------------------------------------------------------------

# Lee el archivo .env y carga sus variables en el sistema.
load_dotenv()

app = Flask(__name__)

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
# El modelo se puede cambiar desde el .env sin tocar el código.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
TIEMPO_MAXIMO_OPENWEATHER = 8      # segundos de espera máxima
TIEMPO_MAXIMO_GEMINI_MS = 30000    # milisegundos (10 segundos)


class ErrorClima(Exception):
    """Error propio: guarda un mensaje claro para el usuario y un código HTTP."""

    def __init__(self, mensaje, codigo_http):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo_http = codigo_http


def crear_cliente_gemini():
    """
    Crea el cliente de Gemini. Si no hay clave o la librería falla,
    devuelve None y la app seguirá funcionando con el respaldo por reglas.
    """
    if not GEMINI_API_KEY:
        print("AVISO: no hay GEMINI_API_KEY. Se usará solo el respaldo por reglas.")
        return None
    try:
        # Se importa acá adentro para que, si la librería no está instalada,
        # la aplicación igual arranque.
        from google import genai
        from google.genai import types

        return genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=TIEMPO_MAXIMO_GEMINI_MS),
        )
    except Exception as error:
        print(f"AVISO: no se pudo iniciar Gemini ({error}). Se usará el respaldo.")
        return None


cliente_gemini = crear_cliente_gemini()


# ---------------------------------------------------------------------------
# 2. CONSULTA AL CLIMA (OpenWeather)
# ---------------------------------------------------------------------------

def consultar_clima(parametros_ubicacion):
    """
    Pide el clima actual a OpenWeather.
    `parametros_ubicacion` es {"q": "Mar del Plata"} o {"lat": -38, "lon": -57}.
    Devuelve el JSON de OpenWeather o lanza ErrorClima con un mensaje claro.
    """
    if not OPENWEATHER_API_KEY:
        raise ErrorClima("El servidor no tiene configurada la clave de OpenWeather.", 500)

    # Usamos `params` para que requests codifique bien tildes y espacios.
    parametros = {
        **parametros_ubicacion,
        "units": "metric",   # temperaturas en °C
        "lang": "es",        # descripciones en español
        "appid": OPENWEATHER_API_KEY,
    }

    try:
        respuesta = requests.get(
            OPENWEATHER_URL, params=parametros, timeout=TIEMPO_MAXIMO_OPENWEATHER
        )
    except requests.exceptions.Timeout:
        raise ErrorClima("El servicio del clima tardó demasiado. Probá de nuevo.", 504)
    except requests.exceptions.RequestException:
        raise ErrorClima("No se pudo conectar con el servicio del clima.", 502)

    if respuesta.status_code == 404:
        raise ErrorClima("No encontramos esa ciudad. Revisá cómo está escrita.", 404)
    if respuesta.status_code == 401:
        raise ErrorClima(
            "La clave de OpenWeather es inválida o todavía no se activó "
            "(las claves nuevas pueden tardar un rato).", 502)
    if respuesta.status_code == 429:
        raise ErrorClima("Se superó el límite de consultas del clima. Esperá un minuto.", 429)
    if respuesta.status_code != 200:
        raise ErrorClima("El servicio del clima respondió con un error inesperado.", 502)

    return respuesta.json()


def extraer_datos_clima(datos_api):
    """Se queda solo con los datos que necesita la interfaz."""
    nombre = datos_api["name"]
    pais = datos_api.get("sys", {}).get("country")
    return {
        "city": f"{nombre}, {pais}" if pais else nombre,
        "temp": round(datos_api["main"]["temp"], 1),
        "feels_like": round(datos_api["main"]["feels_like"], 1),
        "humidity": datos_api["main"]["humidity"],
        "description": datos_api["weather"][0]["description"].capitalize(),
        # Grupo general del clima: "clear", "clouds", "rain", "snow", etc.
        "condition": datos_api["weather"][0]["main"].lower(),
    }


# ---------------------------------------------------------------------------
# 3. RESPALDO POR REGLAS (fallback) - funciona sin internet y sin IA
# ---------------------------------------------------------------------------

def consejo_de_ropa(temp):
    """Regla 1: qué ropa usar según la temperatura."""
    if temp < 5:
        return "Hace mucho frío: usá campera gruesa, bufanda y guantes."
    if temp < 15:
        return "Hace frío: llevá abrigo o campera."
    if temp < 20:
        return "El clima está fresco: un buzo o una campera liviana alcanzan."
    if temp < 27:
        return "La temperatura es agradable: usá ropa cómoda y liviana."
    return "Hace calor: usá ropa clara y fresca, gorra, y tomá mucha agua."


def consejo_de_proteccion(condition, temp):
    """Regla 2: paraguas, protección solar o precauciones según el estado del tiempo."""
    if condition == "thunderstorm":
        return "Hay tormenta: llevá paraguas y evitá estar bajo los árboles."
    if condition in ("rain", "drizzle"):
        return "Hay lluvia: no te olvides el paraguas o un piloto impermeable."
    if condition == "snow":
        return "Hay nieve: usá calzado impermeable y antideslizante."
    if condition in ("mist", "fog", "haze", "smoke", "dust"):
        return "Hay poca visibilidad: tené cuidado al cruzar calles."
    if condition == "clear" and temp >= 27:
        return "El sol está fuerte: usá protector solar."
    return ""


def consejo_de_horario(condition, temp):
    """Regla 3: cuál es un buen momento para salir."""
    if condition in ("thunderstorm", "rain", "drizzle"):
        return "Si podés, esperá a que pare la lluvia para salir."
    if temp >= 28:
        return "Evitá salir entre las 12 y las 17 h: mejor a la mañana temprano o al atardecer."
    if temp < 10:
        return "El mejor momento para salir es al mediodía, cuando hace menos frío."
    return "Es un buen momento para salir a cualquier hora del día."


def generar_consejo_por_reglas(clima):
    """Junta las tres reglas en un solo consejo (nunca falla)."""
    partes = [
        consejo_de_ropa(clima["temp"]),
        consejo_de_proteccion(clima["condition"], clima["temp"]),
        consejo_de_horario(clima["condition"], clima["temp"]),
    ]
    return " ".join(parte for parte in partes if parte)


# ---------------------------------------------------------------------------
# 4. CONSEJO CON IA (Gemini) + decisión entre IA y respaldo
# ---------------------------------------------------------------------------

def generar_consejo_con_ia(clima):
    """
    Le pide el consejo a Gemini. Lanza una excepción si algo sale mal;
    quien llama a esta función se encarga de usar el respaldo.
    """
    if cliente_gemini is None:
        raise RuntimeError("Gemini no está disponible (sin clave o sin librería).")

    prompt = (
        "Sos el asistente de la app ClimaSmart. Datos actuales del clima: "
        f"{clima['description']}, temperatura {clima['temp']} °C, "
        f"sensación térmica {clima['feels_like']} °C, humedad {clima['humidity']} %. "
        "Respondé en español rioplatense, en un solo párrafo de 2 o 3 oraciones, "
        "con un tono amigable. Indicá qué ropa usar, si conviene llevar abrigo o "
        "paraguas, y en qué momento del día conviene salir. "
        "No uses listas, asteriscos ni formato especial."
    )

    respuesta = cliente_gemini.models.generate_content(
        model=GEMINI_MODEL, contents=prompt
    )
    texto = (respuesta.text or "").replace("*", "").strip()
    if not texto:
        raise RuntimeError("Gemini devolvió una respuesta vacía.")
    return texto


def obtener_consejo(clima):
    """
    Intenta con la IA; si falla por CUALQUIER motivo, usa las reglas locales.
    Devuelve (texto, fuente) donde fuente es "ia" o "reglas".
    """
    try:
        return generar_consejo_con_ia(clima), "ia"
    except Exception as error:
        # Mostramos el motivo real en la terminal (para los desarrolladores),
        # pero el usuario recibe igual un consejo útil.
        print(f"AVISO: falló la IA ({error}). Se usa el respaldo por reglas.")
        return generar_consejo_por_reglas(clima), "reglas"


# ---------------------------------------------------------------------------
# 5. RUTAS DE FLASK
# ---------------------------------------------------------------------------

@app.route("/")
def inicio():
    """Entrega la página principal."""
    return render_template("index.html")


def leer_ubicacion_del_pedido():
    """
    Lee ?city=... o ?lat=...&lon=... de la URL y los valida.
    Devuelve los parámetros para OpenWeather o lanza ErrorClima (400).
    """
    ciudad = request.args.get("city", "").strip()
    lat = request.args.get("lat", "").strip()
    lon = request.args.get("lon", "").strip()

    if ciudad:
        if len(ciudad) > 100:
            raise ErrorClima("El nombre de la ciudad es demasiado largo.", 400)
        return {"q": ciudad}

    if lat and lon:
        try:
            lat_num, lon_num = float(lat), float(lon)
        except ValueError:
            raise ErrorClima("Las coordenadas no son válidas.", 400)
        if not (-90 <= lat_num <= 90 and -180 <= lon_num <= 180):
            raise ErrorClima("Las coordenadas están fuera de rango.", 400)
        return {"lat": lat_num, "lon": lon_num}

    raise ErrorClima("Escribí una ciudad o permití el acceso a tu ubicación.", 400)


@app.route("/api/weather")
def api_clima():
    """Endpoint que usa el JavaScript del navegador con fetch()."""
    try:
        ubicacion = leer_ubicacion_del_pedido()
        datos_api = consultar_clima(ubicacion)
        clima = extraer_datos_clima(datos_api)
    except ErrorClima as error:
        return jsonify({"error": error.mensaje}), error.codigo_http
    except (KeyError, IndexError, TypeError, ValueError):
        return jsonify({"error": "Recibimos datos del clima en un formato inesperado."}), 502

    consejo, fuente = obtener_consejo(clima)
    return jsonify({**clima, "advice": consejo, "advice_source": fuente})


# ---------------------------------------------------------------------------
# 6. ARRANQUE
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # debug=True recarga el servidor al guardar cambios. Solo para desarrollo.
    app.run(debug=os.getenv("FLASK_DEBUG", "1") == "1")
