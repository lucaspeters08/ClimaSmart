# ClimaSmart 🌤️

Aplicación web que muestra el clima actual de cualquier ciudad y, usando
inteligencia artificial, da un consejo útil: qué ropa usar, si llevar abrigo
o paraguas y cuándo conviene salir.

**Integrantes:** Lucas Bertinotti Peterseim y Dante Santos

**Tecnologías:** Python + Flask (backend) · HTML5, CSS3 y JavaScript nativo (frontend) ·
API de OpenWeather · API de Google Gemini

---

## 1. Estructura del proyecto

```
ClimaSmart/
├── app.py               ← Servidor Flask: rutas, APIs y sistema de respaldo
├── requirements.txt     ← Librerías de Python necesarias
├── .env.example         ← Modelo del archivo de claves (sin secretos)
├── .env                 ← TUS claves reales (lo creás vos; no se sube a GitHub)
├── .gitignore           ← Le dice a Git que ignore el .env
├── README.md
├── templates/
│   └── index.html       ← Estructura de la página
└── static/
    ├── css/style.css    ← Estilos (diseño responsive)
    └── js/main.js       ← Interacciones, fetch y actualización de la página
```

> Flask exige estos nombres: el HTML va en `templates/` y los CSS/JS en `static/`.

## 2. Instalación y ejecución

**Requisitos:** Python 3.9 o superior.

```bash
# 1) Entrar a la carpeta del proyecto
cd ClimaSmart

# 2) Crear y activar un entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac / Linux

# 3) Instalar las dependencias
pip install -r requirements.txt

# 4) Crear el archivo de claves a partir del modelo
copy .env.example .env         # Windows
cp .env.example .env           # Mac / Linux

# 5) Abrir .env con un editor y pegar tus claves (ver sección 3)

# 6) Ejecutar
python app.py
```

Abrí el navegador en **http://127.0.0.1:5000**

## 3. Cómo conseguir las claves

| Clave | Dónde se obtiene | ¿Obligatoria? |
|---|---|---|
| `OPENWEATHER_API_KEY` | https://home.openweathermap.org/api_keys (cuenta gratuita; una clave nueva puede tardar un rato en activarse) | Sí |
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey | No: sin ella la app usa el respaldo por reglas |
| `GEMINI_MODEL` | Nombre del modelo de Gemini. Si Google lo renombra, se cambia acá sin tocar el código | No |

⚠️ **Seguridad:** el archivo `.env` nunca se comparte, ni por chat, ni por mail,
ni en GitHub. Si una clave se expuso, hay que **borrarla y generar una nueva**
en el panel de cada servicio.

## 4. Cómo funciona (para la defensa oral)

```
 Navegador (main.js)                 Servidor Flask (app.py)              APIs externas
 ───────────────────                 ───────────────────────              ─────────────
 1. El usuario busca  ──fetch──►  2. Valida lo recibido
                                  3. Consulta el clima ───────────────►  OpenWeather
                                  4. Pide un consejo ─────────────────►  Gemini (IA)
                                     ├─ si responde: usa el consejo de la IA
                                     └─ si falla:    usa las REGLAS propias (fallback)
 6. Muestra el resultado ◄─JSON─  5. Devuelve clima + consejo
```

### El sistema de respaldo (fallback)
La IA puede fallar (sin internet, cuota agotada, clave faltante o inválida).
Por eso `obtener_consejo()` hace esto:

1. Intenta `generar_consejo_con_ia()` dentro de un bloque `try`.
2. Si hay **cualquier** excepción, el bloque `except` la captura, la muestra en
   la terminal y llama a `generar_consejo_por_reglas()`.
3. La interfaz avisa al usuario de dónde salió el consejo (IA o respaldo).

Reglas del respaldo (funciones `consejo_de_ropa`, `consejo_de_proteccion` y `consejo_de_horario`):

| Condición | Consejo |
|---|---|
| Menos de 15 °C | Abrigo / campera (y guantes y bufanda si hace menos de 5 °C) |
| Lluvia, llovizna o tormenta | Llevar paraguas |
| 28 °C o más | Evitar salir entre las 12 y las 17 h |
| 27 °C o más con cielo despejado | Protector solar |
| Menos de 10 °C | Salir al mediodía, que hace menos frío |

### Decisiones técnicas que conviene saber explicar
- **¿Por qué las claves están en el backend?** Todo lo que está en el HTML/JS lo
  puede ver cualquiera con "Inspeccionar". El `.env` solo lo lee el servidor.
- **¿Por qué `fetch` y no recargar la página?** Es comunicación asíncrona: la
  página no se recarga y solo se actualiza la tarjeta (manipulación del DOM).
- **¿Por qué `textContent` y no `innerHTML`?** Evita que se ejecute código
  malicioso si algún dato llegara con etiquetas HTML.
- **¿Por qué `params=` en `requests.get`?** `requests` codifica solo los
  caracteres especiales (tildes, espacios) y evita armar URLs a mano.
- **¿Para qué sirve `timeout`?** Para que la app no quede "colgada" si un
  servicio externo no responde.
- **¿Por qué un `<form>`?** Permite buscar con la tecla Enter sin escribir código extra.
- **Geolocalización:** el navegador pide permiso; si el usuario lo rechaza,
  se muestra un mensaje y se lo invita a escribir la ciudad.

## 5. Probar el respaldo
1. Dejá `GEMINI_API_KEY=` vacío en el `.env` (o poné una clave inválida).
2. Reiniciá `python app.py` y buscá una ciudad.
3. La app responde igual, con el cartel *"Consejo generado por el sistema de respaldo"*.

## 6. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| "La clave de OpenWeather es inválida" | Revisá que esté bien copiada, sin espacios; las claves nuevas tardan un rato en activarse |
| Siempre aparece el cartel de respaldo | Mirá el aviso en la terminal: suele ser clave faltante, cuota agotada o nombre de modelo inexistente (ajustá `GEMINI_MODEL`) |
| "No encontramos esa ciudad" | Probá con otro formato, por ej. `Rosario,AR` |
| La ubicación no funciona | Usá `http://127.0.0.1:5000` o `localhost` (los navegadores bloquean la ubicación en sitios sin HTTPS) y aceptá el permiso |

## 7. Posibles mejoras futuras
Pronóstico por horas, cambio entre °C y °F, historial de ciudades buscadas,
modo oscuro y publicación online (por ejemplo en PythonAnywhere o Render).
