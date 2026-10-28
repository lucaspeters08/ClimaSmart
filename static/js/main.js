/*
  ClimaSmart - JavaScript del navegador (frontend)

  Qué hace este archivo:
    1. Escucha el formulario de búsqueda y el botón de ubicación.
    2. Le pide los datos a NUESTRO servidor Flask con fetch() (sin recargar la página).
    3. Muestra el resultado, la pantalla de carga o un mensaje de error.

  Importante: acá NO hay claves secretas. Las claves están solo en el backend.
*/

document.addEventListener('DOMContentLoaded', () => {

    // ---------- 1. Referencias a los elementos de la página ----------
    const searchForm = document.getElementById('searchForm');
    const cityInput = document.getElementById('cityInput');
    const btnSearch = document.getElementById('btnSearch');
    const btnGeo = document.getElementById('btnGeo');

    const loadingText = document.getElementById('loading');
    const errorBox = document.getElementById('errorBox');
    const weatherCard = document.getElementById('weatherCard');
    const adviceBox = document.getElementById('adviceBox');

    // Tiempo máximo de espera al servidor (el backend puede tardar si la IA es lenta)
    const TIEMPO_MAXIMO_MS = 45000;

    // Emoji para cada tipo de clima (OpenWeather devuelve estos grupos)
    const ICONOS = {
        clear: '☀️',
        clouds: '☁️',
        rain: '🌧️',
        drizzle: '🌦️',
        thunderstorm: '⛈️',
        snow: '❄️',
        mist: '🌫️',
        fog: '🌫️',
        haze: '🌫️'
    };

    // ---------- 2. Funciones para mostrar u ocultar cosas ----------

    // Muestra u oculta la carga y bloquea los botones para evitar doble clic
    function mostrarCargando(estaCargando) {
        loadingText.classList.toggle('hidden', !estaCargando);
        btnSearch.disabled = estaCargando;
        btnGeo.disabled = estaCargando;
    }

    function mostrarError(mensaje) {
        errorBox.textContent = mensaje;
        errorBox.classList.remove('hidden');
    }

    function ocultarError() {
        errorBox.classList.add('hidden');
    }

    // Rellena la tarjeta con los datos que llegaron del servidor.
    // Usamos textContent (y no innerHTML) para que nunca se ejecute código ajeno.
    function mostrarClima(datos) {
        document.getElementById('cityName').textContent = datos.city;
        document.getElementById('description').textContent = datos.description;
        document.getElementById('temp').textContent = datos.temp;
        document.getElementById('feelsLike').textContent = datos.feels_like;
        document.getElementById('humidity').textContent = datos.humidity;
        document.getElementById('iaAdvice').textContent = datos.advice;
        document.getElementById('weatherIcon').textContent = ICONOS[datos.condition] || '🌡️';

        // Indica de dónde salió el consejo: IA o reglas de respaldo
        const vinoDeLaIA = datos.advice_source === 'ia';
        adviceBox.classList.toggle('respaldo', !vinoDeLaIA);
        document.getElementById('adviceSource').textContent = vinoDeLaIA
            ? 'Consejo generado por inteligencia artificial.'
            : 'Consejo generado por el sistema de respaldo (la IA no estuvo disponible).';

        // El CSS usa este atributo para cambiar el color de la tarjeta
        weatherCard.dataset.condition = datos.condition;
        weatherCard.classList.remove('hidden');
    }

    // ---------- 3. Comunicación con el servidor ----------

    // Pide el clima a Flask. `endpoint` es algo como "/api/weather?city=Rosario"
    async function pedirClima(endpoint) {
        ocultarError();
        weatherCard.classList.add('hidden');
        mostrarCargando(true);

        // AbortController permite cortar la espera si el servidor no responde
        const controlador = new AbortController();
        const temporizador = setTimeout(() => controlador.abort(), TIEMPO_MAXIMO_MS);

        try {
            const respuesta = await fetch(endpoint, { signal: controlador.signal });

            // Intentamos leer el JSON; si el servidor devolvió otra cosa, queda en null
            let datos = null;
            try {
                datos = await respuesta.json();
            } catch {
                datos = null;
            }

            if (!respuesta.ok) {
                throw new Error((datos && datos.error) || 'Ocurrió un error al consultar el clima.');
            }

            mostrarClima(datos);

        } catch (error) {
            if (error.name === 'AbortError') {
                mostrarError('El servidor tardó demasiado en responder. Probá de nuevo.');
            } else if (error instanceof TypeError) {
                // fetch lanza TypeError cuando no hay conexión con el servidor
                mostrarError('No hay conexión con el servidor. Revisá tu internet y que Flask esté encendido.');
            } else {
                mostrarError(error.message);
            }
        } finally {
            // "finally" se ejecuta siempre, haya salido bien o mal
            clearTimeout(temporizador);
            mostrarCargando(false);
        }
    }

    // ---------- 4. Búsqueda por ciudad ----------

    // Se ejecuta al apretar "Buscar" o la tecla Enter (por ser un <form>)
    searchForm.addEventListener('submit', (evento) => {
        evento.preventDefault(); // evita que la página se recargue
        const ciudad = cityInput.value.trim();

        if (!ciudad) {
            mostrarError('Escribí el nombre de una ciudad para buscar.');
            cityInput.focus();
            return;
        }
        pedirClima(`/api/weather?city=${encodeURIComponent(ciudad)}`);
    });

    // ---------- 5. Geolocalización del navegador ----------

    // Convierte el código de error del navegador en un mensaje claro
    function explicarErrorGeolocalizacion(error) {
        if (error.code === error.PERMISSION_DENIED) {
            return 'No diste permiso para usar tu ubicación. Podés escribir tu ciudad manualmente.';
        }
        if (error.code === error.POSITION_UNAVAILABLE) {
            return 'No se pudo determinar tu ubicación. Probá escribiendo tu ciudad.';
        }
        if (error.code === error.TIMEOUT) {
            return 'Tardó demasiado en encontrar tu ubicación. Probá de nuevo o escribí tu ciudad.';
        }
        return 'No se pudo acceder a tu ubicación. Escribí tu ciudad manualmente.';
    }

    btnGeo.addEventListener('click', () => {
        ocultarError();

        if (!navigator.geolocation) {
            mostrarError('Tu navegador no soporta ubicación. Escribí tu ciudad manualmente.');
            cityInput.focus();
            return;
        }

        mostrarCargando(true);
        navigator.geolocation.getCurrentPosition(
            // Si el usuario acepta el permiso:
            (posicion) => {
                const { latitude, longitude } = posicion.coords;
                pedirClima(`/api/weather?lat=${latitude}&lon=${longitude}`);
            },
            // Si lo rechaza o hay un problema: dejamos la búsqueda manual
            (error) => {
                mostrarCargando(false);
                mostrarError(explicarErrorGeolocalizacion(error));
                cityInput.focus();
            },
            { timeout: 10000 }
        );
    });
});
