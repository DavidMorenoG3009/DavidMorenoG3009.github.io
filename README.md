# Teclado de Voz Universal (Offline) - Documentación del Proyecto

¡Hola! Esta es la bitácora técnica de mi proyecto de "Teclado de Voz". Aquí documento toda la arquitectura de la aplicación, cómo la construí, y los problemas que me fui encontrando y solucionando por el camino para dejarla estable en Windows.

## 1. Visión General del Proyecto

La idea principal de este proyecto era crear una aplicación de escritorio que funcionara de manera global ("universal"). Quería un programa que:

1. Me escuchara continuamente en segundo plano.
2. Transcribiera lo que digo, **completamente offline** (sin consumir mi internet ni violar mi privacidad).
3. Escribiera el texto mágicamente como si fuera un teclado, en _cualquier_ aplicación donde yo tenga el cursor puesto (VS Code, Word, navegador, etc).

## 2. Tecnologías y Librerías Utilizadas

Para lograr esto, construí el código en Python y usé el siguiente stack:

- **Vosk (`vosk`)**: El superhéroe de este proyecto. Es el motor de reconocimiento de voz. Lo elegí en lugar de _SpeechRecognition/Google_ porque no tiene lag, funciona sin internet y es gratis. Me decidí por el modelo pesado de español de España/Latam (`vosk-model-es-0.42` de ~1.4GB) porque el modelo ligero (40MB) fallaba mucho con la dicción. Su precisión compensa con creces el requerimiento de memoria RAM.
- **SoundDevice (`sounddevice`)**: Me permite extraer el audio estéreo/mono bruto de mi tarjeta de sonido o micrófono con una latencia increíblemente baja.
- **Keyboard (`keyboard`)**: Fundamental para atrapar y simular las pulsaciones de teclado a un nivel de kernel en Windows. La usé tanto para simular atajos globales (ej. `Ctrl+C`, `Ctrl+Z`), como para interceptar llamadas cuando estoy fuera del programa. Originalmente traté de usar _PyAutoGUI_, pero se volvía completamente loco y se ahogaba intentando escribir caracteres especiales con tildes (ñ, á, é) en entornos Windows. `keyboard.write()` me solucionó la vida ahí.

## 3. Retos Técnicos y Refactorizaciones

Durante el desarrollo de `voice_keyboard.py`, tuve que iterar varias veces la solución. Estos son los parches críticos que implementé:

### A. El "Problema de Scunthorpe" en los comandos.

Al principio, configuré la app para que, si detectaba la palabra "coma" o "punto", me pusiera los signos `,` y `.`.
El problema pasó cuando quise crear el comando _"comandos de voz"_. El programa se volvía loco porque veía la cadena `"coma"` escondida dentro del string `"comandos... "`, la cortaba internamente y la reemplazaba.

- **Solución**: Tuve que reemplazar el motor básico de búsqueda (strings) por la librería Regex de Python (`re`). Ahora uso los marcadores de bordes de palabras `\b`. Así el bloque: `re.sub(r"\bcoma\b", ",", ...)` asegura que solo se reemplace si la palabra es aislada.

### B. El error Fatal en la "Barra Invertida" (Regex)

La migración a Regex me trajo otro dolor de cabeza. Al procesar el reemplazo del signo `"\"` (Backslash), la librería `re.sub()` fallaba arrojando un error en consola: `bad escape (end of pattern) at position 0`.

- **Solución**: Aprendí que con los motores Regex, la barra invertida es un símbolo escape, entonces pasarle `\\` causaba pánico al final del parsing. Lo arreglé inyectando cuatro barras literales `\\\\` dentro del diccionario de reemplazos.

### C. El Control de Frecuencias de Micrófono

Implementé una lectura dinámica de las variables del puerto de entrada (`query_devices`). Descubrí que si dejaba hardcodeado `44100Hz`, el sistema se partía en computadoras diferentes. Usando esta línea, obligo al programa a preguntarle a Windows qué velocidad de muestreo usa por defecto, y acoplo el modelo de Kaldi/Vosk a ella automáticamente:

```python
self.device_info = sd.query_devices(sd.default.device[0], 'input')
self.samplerate = int(self.device_info['default_samplerate'])
```

### D. Modo "Mute" vs "Pausa Dura"

Originalmente solo tenía el atajo de mi teclado físico para pausar todo. Quise implementar un comando activado por voz (_"pausar dictado"_, _"reanudar dictado"_).
Pero me topé con una paradoja: _Si por voz le ordeno apagar el micrófono... ¿Cómo diablos me va a escuchar cuando luego diga: "reanudar dictado"?_

- **Solución**: Creé un "Modo Mute" simulado usando la bandera boolena `self.dictation_muted`. Ahora, cuando digo _"descansa"_, el hilo de Python sigue procesando absolutamente todo el audio en RAM como un oyente activo, simplemente tiene un _if-statement_ que **bloquea la orden de escritura en la pantalla**.

## 4. Estructura de Automatización (.ps1 y .bat)

Para no tener que abrir VS Code jamás cuando simplemente quiero usar el dictador, automatizé la instalación.
Generé un archivo `setup.ps1` que detecta la instalación de Python de la máquina, me crea automáticamente un entorno virtual asilado (`.venv`) y se descarga él solo todas las librerías con `pip`. Por último, el setup me crea un archivo llamado `start_voice_keyboard.bat` en mi escritorio para poder lanzarlo con un doble clic super cómodo.

---

_Escrito por: [Tu Nombre] - En la lucha constante por hacer que Windows obedezca mi voz._
