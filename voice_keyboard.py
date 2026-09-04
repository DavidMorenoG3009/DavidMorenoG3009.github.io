import os
import sys
import queue
import json
import threading
import urllib.request
import zipfile
import keyboard
import pyautogui
import re

# Le apago los logs por defecto a Vosk para que la terminal no se me llene de advertencias raras de ALSA/PyAudio que asustan
os.environ['VOSK_LOG_LEVEL'] = '-1' 
from vosk import Model, KaldiRecognizer
import sounddevice as sd

# Elegí el modelo completo (1.4GB) en lugar del chico (40MB) porque fallaba bastante. Mejor precisión ante todo, aunque pese más.
MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip"
MODEL_DIR = "model_es"

class VoiceKeyboardOffline:
    def __init__(self):
        # Uso una cola (Queue) para ir guardando los pedacitos de audio que llegan del mic sin trabar el resto del main
        self.q = queue.Queue()
        self.is_listening = False
        self.dictation_muted = False # <--- Controla si el mic escucha pero no escribe
        self.model = None
        self.device_info = None
        self.samplerate = None

    def setup_model(self):
        """Descarga y descomprime mi modelo de IA si es la primera vez que corro esto en la PC."""
        if not os.path.exists(MODEL_DIR):
            print(f"[*] Veo que no tienes el modelo en '{MODEL_DIR}'. Descargando desde internet (tranqui, es solo una vez, ve por un café)...")
            zip_path = "model.zip"
            
            try:
                urllib.request.urlretrieve(MODEL_URL, zip_path)
                print("[*] ¡Descarga lista! Voy a extraer los archivos...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(".")
                os.rename("vosk-model-es-0.42", MODEL_DIR)
                os.remove(zip_path)
                print("[*] ¡Todo el modelo configurado al 100%!")
            except Exception as e:
                print(f"[!] Uy, algo falló bajando el modelo: {e}")
                sys.exit(1)
        else:
            print("[*] Encontré el modelo offline en la carpeta. Cargándolo a la memoria...")

        self.model = Model(MODEL_DIR)

    def audio_callback(self, indata, frames, time, status):
        """Función super interna que me pide 'sounddevice' para inyectarle el audio captado cada milisegundo."""
        if status:
            print(status, file=sys.stderr)
        if self.is_listening:
            # Si el micrófono no está pausado, meto el crudo de audio a mi cola para procesarlo al rato.
            self.q.put(bytes(indata))

    def process_special_commands(self, text):
        """Aquí atajo las palabras sueltas que digo, para convertirlas en atajos del sistema en lugar de transcribirlas."""
        if not text:
            return False
            
        text_lower = text.lower().strip()
        
        # Mis mapeos personales de atajos de teclado
        if text_lower in ["enter", "intro"]:
            keyboard.send('enter')
            return True
        elif text_lower in ["tabulador", "tab"]:
            keyboard.send('tab')
            return True
        elif text_lower in ["nueva línea", "línea nueva"]:
            keyboard.send('shift+enter')
            return True
        elif text_lower in ["borrar", "borra eso"]:
            keyboard.send('backspace')
            return True
        elif text_lower in ["borrar palabra"]:
            keyboard.send('ctrl+backspace')
            return True
        elif text_lower in ["espacio"]:
            keyboard.send('space')
            return True
        elif text_lower in ["guardar archivo", "guardar documento"]:
            keyboard.send('ctrl+s')
            return True
        elif text_lower in ["copiar texto", "copiar"]:
            keyboard.send('ctrl+c')
            return True
        elif text_lower in ["pegar texto", "pegar"]:
            keyboard.send('ctrl+v')
            return True
        elif text_lower in ["deshacer", "deshacer eso"]:
            keyboard.send('ctrl+z')
            return True
        elif text_lower in ["seleccionar todo"]:
            keyboard.send('ctrl+a')
            return True
        
        # --- COMANDOS PARA CONTROLAR EL PROGRAMA CON LA VOZ ---
        elif text_lower in ["pausar dictado", "pausar programa", "descansa"]:
            self.dictation_muted = True
            print("\n[🎙️] Dictado MUTEADO por voz. Di 'reanudar dictado' para volver a escribir.")
            return True
        elif text_lower in ["reanudar dictado", "reanudar programa", "despierta"]:
            self.dictation_muted = False
            print("\n[🎙️] Dictado REANUDADO por voz. Escuchando...")
            return True
        elif text_lower in ["apagar teclado", "terminar programa", "apagar dictado"]:
            print("\n[🎙️] Apagando el sistema por comando de voz...")
            keyboard.send('esc')  # Esto simula un Escape, lo que rompe el bucle principal y cierra la app.
            return True
        # ------------------------------------------------------
            
        return False

    def format_text(self, text):
        """Magia pura: paso reemplazando las palabras habladas por los símbolos reales en medio de mis oraciones."""
        # Se usa 'regex' para que busque palabras completas (\b) y no reemplace pedacitos dentro de otras palabras (como 'coma' en 'comandos').
        replacements = {
            r"\bpunto final\b": ".",
            r"\bpunto y coma\b": ";",
            r"\bdos puntos\b": ":",
            r"\bcoma\b": ",",
            r"\bpunto\b": ".",
            r"\babrir interrogación\b": "¿",
            r"\babre interrogación\b": "¿",
            r"\bsigno de pregunta\b": "?",
            r"\bsigno de interrogación\b": "?",
            r"\bcerrar interrogación\b": "?",
            r"\bcierra interrogación\b": "?",
            r"\babrir exclamación\b": "¡",
            r"\babre exclamación\b": "¡",
            r"\bsigno de exclamación\b": "!",
            r"\bcerrar exclamación\b": "!",
            r"\bcierra exclamación\b": "!",
            r"\bguion bajo\b": "_",
            r"\bguión bajo\b": "_",
            r"\bguion medio\b": "-",
            r"\bguión medio\b": "-",
            r"\barroba\b": "@",
            r"\bcomillas\b": '"',
            r"\bbarra inclinada\b": "/",
            r"\bbarra invertida\b": "\\\\" # <-- Se necesitan doble escape al dárselo a Regex como string de reemplazo
        }
        
        texto_formateado = text.lower()
        for patron, signo in replacements.items():
            # re.sub busca el patrón exacto. re.IGNORECASE por si acaso, aunque ya le hicimos lower() a todo.
            texto_formateado = re.sub(patron, signo, texto_formateado)
            
        # Puliendo detallitos: elimino los espacios huecos que puedan quedar "hola ," -> "hola,"
        texto_formateado = texto_formateado.replace(" ,", ",").replace(" .", ".").replace(" ?", "?").replace(" !", "!")
        
        # Le doy un toque profesional capitalizando siempre la primera letra
        if len(texto_formateado) > 0:
            texto_formateado = texto_formateado[0].upper() + texto_formateado[1:]
            
        return texto_formateado

    def listen_worker(self):
        """Este es mi hilo principal de abajo (background). Se queda girando infinito analizando mi voz."""
        try:
            # Le pregunto a Windows cuál es la tasa de muestreo (frecuencia) que usa mi micro actualmente, 
            # para no 'hardcodear' un 44100Hz o 48000Hz y que truene en otra PC.
            self.device_info = sd.query_devices(sd.default.device[0], 'input')
            self.samplerate = int(self.device_info['default_samplerate'])
            
            # Le aviso a Vosk que esté preparado para recibir audio en esta frecuencia exacta.
            recognizer = KaldiRecognizer(self.model, self.samplerate)
            
            print(f"[*] ¡Micrófono enchufado! Trabajando a la frecuencia perfecta: {self.samplerate}Hz.")
            
            # Configuro un bloque grande o 'blocksize' de 8000 para que recoja el audio en ráfagas de ~0.1 seg.
            # Es el balance ("sweet spot") para que se sienta muy fluido sin hacer explotar mi CPU.
            with sd.RawInputStream(samplerate=self.samplerate, blocksize=8000, device=None,
                                   dtype='int16', channels=1, callback=self.audio_callback):
                while True: # Bucle infinito (solo se rompe cuando cierre el programa)
                    
                    if not self.is_listening:
                        # Si me pausé, le digo al hilo que se eche a dormir un rato (100ms) para no gastar energía
                        sd.sleep(100)
                        self.q.queue.clear() # Limpio la cola para soltar cualquier audio/eco viejo guardado
                        continue
                        
                    data = self.q.get()
                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        texto_reconocido = result.get("text", "")
                        
                        if texto_reconocido:
                            print(f"-> Escuché: {texto_reconocido}")
                            
                            # Si sí detecté algo, primero veo si lo que dije fue solo un atajo estricto de mi lista...
                            if not self.process_special_commands(texto_reconocido):
                                # ...Si no lo fue y no le pedí antes al sistema que descasara (mute), asumo que quiero dictarlo libremente.
                                if not self.dictation_muted:
                                    texto_final = self.format_text(texto_reconocido)
                                    
                                    # Terminé usando 'keyboard.write' en este proyecto en lugar de 'pyautogui' porque este último
                                    # se vuelve súper agresivo e inestable con las tildes (ñ, á, etc) en el OS de Windows.
                                    keyboard.write(texto_final + " ")
                                
        except Exception as e:
            print(f"[!] Explotó algo feo en el módulo de sonido: {e}")

    def toggle_listening(self):
        """Prende o apaga el dictado rapidito cuando presiono la combi de teclas."""
        self.is_listening = not self.is_listening
        estado = "ACTIVADO 🔴" if self.is_listening else "PAUSADO ⏸️"
        print(f"\n=== Micrófono {estado} ===")

    def run(self):
        """Este es mi punto de arranque, ata todas las piezas de arriba."""
        print("=== Iniciando Mi Teclado de Voz Universal (Offline con Vosk) ===")
        self.setup_model()
        
        # Meto la escucha del mic en un hilo completamente aparte (multithreading)
        # esto garantiza que la ventana principal no se trabe/congele esperando que yo hable.
        t = threading.Thread(target=self.listen_worker, daemon=True)
        t.start()
        
        print("\nMis atajos de teclado clave:")
        print(" - 'Ctrl + Alt + V': Pausar / Reanudar el micro")
        print(" - 'Esc': Salir y matar la app por completo\n")
        
        # Le clavo un listener global para mi hotkey
        keyboard.add_hotkey('ctrl+alt+v', self.toggle_listening)
        
        self.toggle_listening() # Lo enciendo de una para empezar
        
        # Mantengo vivo este archivo hasta que mi dedo oprima la tecla escape
        keyboard.wait('esc')
        
        print("\n=== Teclado de voz apagado. ¡Nos vemos! ===")
        sys.exit(0)

if __name__ == "__main__":
    app = VoiceKeyboardOffline()
    app.run()