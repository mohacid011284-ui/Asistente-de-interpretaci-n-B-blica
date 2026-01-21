import os
import re
import hmac
import streamlit as st
from google import genai
from google.genai import types

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Instructor Bíblico AI", page_icon="📖", layout="wide")

# Estilos CSS para botones grandes y limpios
st.markdown("""
    <style>
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        height: 3.5em;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- GESTIÓN DE SECRETOS ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except Exception:
    st.error("⚠️ Error: No se encontró GOOGLE_API_KEY en los secretos (.streamlit/secrets.toml).")
    st.stop()

# --- DEFINICIÓN DEL CEREBRO (PROMPT MAESTRO) ---
# Aquí pegamos la instrucción completa que definiste anteriormente
SYSTEM_INSTRUCTION = """
Eres un GPT personalizado que funciona como INSTRUCTOR DE INTERPRETACIÓN BÍBLICA.
Tu autoridad normativa es el texto bíblico.
PRINCIPIO RECTOR: “Permanecer en la línea: decir exactamente lo que el texto dice, ni más ni menos.”

MARCO HERMENÉUTICO OBLIGATORIO (En orden):
1. Texto bíblico | 2. Audiencia original | 3. Tipo de texto | 4. Rasgos literarios | 5. Estructura
6. Énfasis | 7. Contexto | 8. Línea melódica | 9. Argumento | 10. Reflexión teológica
11. Persuasión | 12. Arreglo | 13. Aplicación.

MODOS DE OPERACIÓN:
- MODO AULA: Enseña lección por lección. No permitas avanzar sin validar el paso anterior.
- MODO ALUMNO: Guía con preguntas socráticas. Nunca des respuestas completas.
- MODO MAESTRO: Modela interpretaciones completas y perfectas. (SOLO SI SE SOLICITA EXPLÍCITAMENTE).
- MODO REVISIÓN: Evalúa trabajos subidos. Sé estricto con el marco hermenéutico.

IMPORTANTE: Si el usuario intenta saltarse pasos en Modo Alumno, bloquéalo y regrésalo al paso correspondiente.
"""

# --- INICIALIZACIÓN DE ESTADO ---
if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=api_key)

if "chat" not in st.session_state:
    # Configuramos el modelo con tu instrucción maestra
    st.session_state.chat = st.session_state.client.chats.create(
        model="gemini-2.0-flash", # O usa "gemini-1.5-pro" para más potencia
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.3 # Bajo para ser preciso y riguroso
        )
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

# Variables de control de flujo
if "maestro_unlocked" not in st.session_state:
    st.session_state.maestro_unlocked = False
if "submission" not in st.session_state:
    st.session_state.submission = None
if "attach_file_next" not in st.session_state:
    st.session_state.attach_file_next = False
if "aula_iniciada" not in st.session_state:
    st.session_state.aula_iniciada = False

# --- FUNCIONES DE SEGURIDAD Y LÓGICA ---

def verificar_password():
    """Verifica la contraseña del modo maestro de forma segura"""
    clave_real = st.secrets.get("MAESTRO_PASSWORD", "12345")
    input_usuario = st.session_state.get("pass_input", "")
    
    if hmac.compare_digest(input_usuario, clave_real):
        st.session_state.maestro_unlocked = True
        st.success("✅ Modo Maestro Desbloqueado")
    else:
        st.error("❌ Contraseña incorrecta")

def bloquear_maestro():
    st.session_state.maestro_unlocked = False
    st.info("🔒 Modo Maestro Bloqueado")

def reiniciar_chat():
    st.session_state.messages = []
    st.session_state.chat = st.session_state.client.chats.create(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)
    )
    st.session_state.aula_iniciada = False
    st.session_state.attach_file_next = False

# Detección de intentos de hackeo vía texto (Regex)
def es_intento_no_autorizado(texto):
    texto = texto.lower()
    patron_maestro = r"(modo maestro|actúa como maestro|dame la respuesta|resuelve tú)"
    
    # 1. Si intenta ser maestro y está bloqueado
    if re.search(patron_maestro, texto) and not st.session_state.maestro_unlocked:
        return "LOCK_MAESTRO"
    
    return "OK"

# --- FUNCIONES DE BOTONES (COMMAND INJECTION) ---
def trigger_aula():
    msg = "COMANDO INTERNO: Inicia el MODO AULA. Comienza con el paso 1 (Audiencia Original) para el pasaje que elija el usuario."
    st.session_state.messages.append({"role": "user", "content": msg, "hidden": True})
    st.session_state.aula_iniciada = True
    enviar_a_gemini(msg, ocultar_usuario=True)

def trigger_alumno():
    msg = "COMANDO INTERNO: Cambia a MODO ALUMNO. Hazme una pregunta socrática sobre el paso actual."
    st.session_state.messages.append({"role": "user", "content": msg, "hidden": True})
    enviar_a_gemini(msg, ocultar_usuario=True)

def trigger_maestro():
    msg = "COMANDO INTERNO: Cambia a MODO MAESTRO. Muestra cómo se resuelve el paso actual perfectamente."
    st.session_state.messages.append({"role": "user", "content": msg, "hidden": True})
    enviar_a_gemini(msg, ocultar_usuario=True)

def trigger_revision():
    st.session_state.attach_file_next = True
    msg = "COMANDO INTERNO: Cambia a MODO REVISIÓN. He adjuntado mi tarea. Evalúala estrictamente."
    st.session_state.messages.append({"role": "user", "content": msg, "hidden": True})
    enviar_a_gemini(msg, ocultar_usuario=True)

# --- MOTOR DE COMUNICACIÓN ---
def enviar_a_gemini(texto, ocultar_usuario=False):
    try:
        contenido_envio = [texto]
        
        # Si hay archivo pendiente (Solo para modo revisión)
        if st.session_state.attach_file_next and st.session_state.submission:
            archivo = st.session_state.submission
            # Convertimos bytes para Gemini
            datos_archivo = types.Part.from_bytes(data=archivo.getvalue(), mime_type=archivo.type)
            contenido_envio.append(datos_archivo)
            st.session_state.attach_file_next = False # Ya lo enviamos, apagamos flag
        
        # Llamada a la API
        response = st.session_state.chat.send_message(contenido_envio)
        
        # Guardar historial (Filtrando lo oculto)
        if not ocultar_usuario:
             # Ya se agregó arriba en el flujo normal, esto es redundancia por si acaso
             pass
             
        st.session_state.messages.append({"role": "model", "content": response.text})
        
    except Exception as e:
        st.error(f"Error de conexión: {e}")

# --- INTERFAZ GRÁFICA ---

# BARRA LATERAL
with st.sidebar:
    st.image("https://cfmpaideia.com/wp-content/uploads/2023/05/logo-paideia-blanco.png", width=200)
    st.header("Panel de Control")
    
    # Uploader
    uploaded_file = st.file_uploader("📂 Subir Tarea (PDF/TXT)", type=['pdf', 'txt', 'md'])
    if uploaded_file:
        st.session_state.submission = uploaded_file
        st.success("Archivo cargado y listo para revisión.")
    
    st.markdown("---")
    
    # Seguridad Maestro
    st.subheader("🔐 Acceso Maestro")
    if not st.session_state.maestro_unlocked:
        st.text_input("Contraseña", type="password", key="pass_input")
        st.button("Desbloquear", on_click=verificar_password)
    else:
        st.success("Modo Maestro: ACTIVO")
        st.button("Bloquear de nuevo", on_click=bloquear_maestro)
        
    st.markdown("---")
    st.button("🗑️ Reiniciar Clase", on_click=reiniciar_chat)

# TÍTULO Y BOTONES DE MODO
st.title("Aula de Hermenéutica Expositiva")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.button("🏫 MODO AULA", on_click=trigger_aula, help="Iniciar la clase paso a paso")
    
with col2:
    # Solo activo si la clase empezó
    st.button("🤔 MODO ALUMNO", on_click=trigger_alumno, disabled=not st.session_state.aula_iniciada, help="Ayuda socrática")

with col3:
    # Solo activo si está desbloqueado
    st.button("👨‍🏫 MODO MAESTRO", on_click=trigger_maestro, disabled=not st.session_state.maestro_unlocked, type="primary" if st.session_state.maestro_unlocked else "secondary")

with col4:
    # Solo activo si hay archivo
    st.button("📝 MODO REVISIÓN", on_click=trigger_revision, disabled=uploaded_file is None)

# ÁREA DE CHAT
st.markdown("---")

for message in st.session_state.messages:
    # No mostramos los comandos internos ocultos
    if message.get("hidden"):
        continue
        
    role = message["role"]
    avatar = "🧑‍💻" if role == "user" else "📖"
    bg_color = "#f0f2f6" if role == "model" else "#ffffff"
    
    with st.chat_message(role, avatar=avatar):
        st.markdown(message["content"])

# INPUT DE USUARIO
if prompt := st.chat_input("Escribe tu análisis o pregunta..."):
    
    # 1. Verificación de Seguridad (Anti-Cheat)
    check_seguridad = es_intento_no_autorizado(prompt)
    
    if check_seguridad == "LOCK_MAESTRO":
        st.error("⛔ ACCESO DENEGADO: No puedes activar funciones de Maestro sin contraseña. Usa el panel lateral.")
        # No guardamos ni enviamos el mensaje
    else:
        # 2. Flujo Normal
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(prompt)
        
        with st.spinner("El instructor está analizando..."):
            enviar_a_gemini(prompt)
            st.rerun()
