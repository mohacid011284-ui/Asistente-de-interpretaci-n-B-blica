import streamlit as st
from google import genai
from google.genai import types
import os

# CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Instructor Bíblico", page_icon="📖", layout="wide")

# ESTILOS
st.markdown("""<style>div.stButton > button {width: 100%; border-radius: 10px; height: 3em;}</style>""", unsafe_allow_html=True)

# --- 🧠 EL CEREBRO (INSTRUCCIONES + CONOCIMIENTO) ---
INSTRUCCIONES_BASE = """
ACTÚA COMO: Un Instructor de Seminario experto en Hermenéutica Expositiva.
TU FILOSOFÍA: "Permanecer en la línea".

🚨 PROTOCOLO DE COMPORTAMIENTO:
MODO 1: MAESTRO SOCRÁTICO (Botones Aula/Alumno) -> Sé breve, pregunta y espera.
MODO 2: AUDITOR ESTRICTO (Botón Revisión / Archivo subido) -> Sé crítico, llena la hoja de evaluación, señala errores y reglas rotas.

⚠️ CIERRE OBLIGATORIO EN REVISIÓN:
"¿Te gustaría que genere una re-modificación de tu sermón/trabajo aplicando estas correcciones?"
"""

def get_system_prompt():
    prompt_completo = INSTRUCCIONES_BASE
    carpeta_knowledge = "knowledge"
    
    if os.path.exists(carpeta_knowledge):
        archivos_encontrados = False
        prompt_completo += "\n\n=== BIBLIOTECA DE CONOCIMIENTOS ===\n"
        for archivo_nombre in os.listdir(carpeta_knowledge):
            if archivo_nombre.endswith((".md", ".txt")):
                ruta_completa = os.path.join(carpeta_knowledge, archivo_nombre)
                try:
                    with open(ruta_completa, "r", encoding="utf-8") as f:
                        contenido = f.read()
                        prompt_completo += f"\n--- TEMA: {archivo_nombre.upper()} ---\n{contenido}\n"
                        archivos_encontrados = True
                except:
                    pass
        if not archivos_encontrados:
            prompt_completo += "\n(No se encontraron archivos en knowledge)."
    return prompt_completo

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3389/3389081.png", width=100)
    st.title("Aula Virtual")
    
    st.markdown("### 📂 Buzón de Revisión")
    archivo_subido = st.file_uploader("Sube PDF, TXT o MD", type=["pdf", "txt", "md"])
    if archivo_subido:
        st.success("✅ Archivo cargado.")
    
    st.markdown("---")
    if st.button("🗑️ Borrar Chat", type="primary"):
        st.session_state.messages = []
        st.session_state.chat = None # Reseteamos el chat también
        st.rerun()

# --- NUEVO CLIENTE GOOGLE GENAI (SDK MODERNO) ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except KeyError:
    st.error("Falta la API Key en Secrets.")
    st.stop()

if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=api_key)

# --- INICIALIZAR CHAT ---
if "chat" not in st.session_state or st.session_state.chat is None:
    prompt_final = get_system_prompt()
    
    # AQUÍ ES DONDE ELIGES EL MODELO (2.0 o 2.5)
    st.session_state.chat = st.session_state.client.chats.create(
        model="gemini-2.0-flash", 
        config=types.GenerateContentConfig(
            system_instruction=prompt_final,
            temperature=0.3 # Un poco más preciso para teología
        ),
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- INTERFAZ ---
st.title("📖 Instructor de Interpretación Bíblica")
st.caption("Filosofía: Permanecer en la línea | Powered by Google GenAI SDK")

# Botones
c1, c2, c3, c4 = st.columns(4)
def click(txt): st.session_state.messages.append({"role": "user", "content": txt})

with c1: 
    if st.button("🎓 Aula"): click("Iniciar Modo Aula: Lección 1")
with c2: 
    if st.button("📝 Alumno"): click("Quiero analizar un pasaje (Modo Socrático)")
with c3: 
    if st.button("🧑‍🏫 Maestro"): click("Modela una interpretación")
with c4: 
    if st.button("🔍 Revisión"): click("He subido mi documento. ACTIVA EL MODO AUDITOR ESTRICTO.")

# Mostrar Chat
for m in st.session_state.messages:
    role_to_show = "assistant" if m["role"] == "model" else "user"
    with st.chat_message(role_to_show): 
        st.markdown(m["content"])

# --- LÓGICA DE PROCESAMIENTO (NUEVO SDK) ---
if prompt := st.chat_input("Escribe aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Analizando con nueva teconología..."):
            try:
                user_msg = st.session_state.messages[-1]["content"]
                
                # Manejo de Archivos con el nuevo SDK
                message_parts = [user_msg]
                
                if archivo_subido:
                    # Convertimos a bytes para el nuevo formato
                    file_bytes = archivo_subido.getvalue()
                    file_mime = archivo_subido.type
                    
                    # Creamos la 'Part' compatible con el nuevo SDK
                    file_part = types.Part.from_bytes(
                        data=file_bytes,
                        mime_type=file_mime
                    )
                    message_parts.append(file_part)
                
                # Enviar mensaje
                response = st.session_state.chat.send_message(message_parts)
                
                # Mostrar respuesta
                st.markdown(response.text)
                st.session_state.messages.append({"role": "model", "content": response.text})
                
            except Exception as e:
                st.error(f"Error del sistema: {e}")
                if "429" in str(e):
                    st.warning("⚠️ Cuota excedida. El modelo 2.0/2.5 tiene límites estrictos. Intenta en un minuto.")
