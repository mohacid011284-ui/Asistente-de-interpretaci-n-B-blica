import streamlit as st
from google import genai
from google.genai import types
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Instructor Bíblico", page_icon="📖", layout="wide")
st.markdown("""<style>div.stButton > button {width: 100%; border-radius: 10px; height: 3em;}</style>""", unsafe_allow_html=True)

# --- API KEY & CLIENTE (SDK NUEVO) ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("⚠️ Falta la API Key en los Secrets de Streamlit.")
    st.stop()

if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=api_key)

# --- CEREBRO (INSTRUCCIONES) ---
INSTRUCCIONES = """
ACTÚA COMO: Instructor de Seminario experto en Hermenéutica Expositiva.
TU FILOSOFÍA: "Permanecer en la línea".

MODO 1: MAESTRO SOCRÁTICO (Aula/Alumno) -> Sé breve, pregunta y espera.
MODO 2: AUDITOR ESTRICTO (Revisión) -> Sé crítico, usa la Hoja de Evaluación, señala errores y reglas rotas.
CIERRE OBLIGATORIO EN REVISIÓN: "¿Te gustaría que genere una re-modificación...?"
"""

def get_prompt():
    texto = INSTRUCCIONES
    if os.path.exists("knowledge"):
        for f in os.listdir("knowledge"):
            if f.endswith((".md", ".txt")):
                try: 
                    with open(f"knowledge/{f}", "r", encoding="utf-8") as file:
                        texto += f"\n--- {f.upper()} ---\n{file.read()}"
                except: pass
    return texto

# --- CONFIGURACIÓN DEL CHAT ---
if "chat" not in st.session_state or st.session_state.chat is None:
    # Usamos el modelo ESTABLE (1.5 Flash)
    st.session_state.chat = st.session_state.client.chats.create(
        model="gemini-1.5-flash", 
        config=types.GenerateContentConfig(
            system_instruction=get_prompt(),
            temperature=0.3
        )
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- INTERFAZ VISUAL ---
st.title("📖 Instructor de Interpretación Bíblica")

with st.sidebar:
    st.title("Panel de Control")
    archivo = st.file_uploader("📂 Subir Sermón/Hoja", type=["pdf", "txt", "md"])
    if archivo: st.success("✅ Archivo listo")
        
    st.markdown("---")
    if st.button("🗑️ Reiniciar Chat", type="primary"):
        st.session_state.chat = None
        st.session_state.messages = []
        st.rerun()

# --- BOTONES DE ACCIÓN (LOS 4 BOTONES) ---
c1, c2, c3, c4 = st.columns(4)

def enviar(txt): 
    st.session_state.messages.append({"role": "user", "content": txt})

with c1: 
    if st.button("🎓 Aula"): enviar("Iniciar Modo Aula: Lección 1")
with c2: 
    if st.button("📝 Alumno"): enviar("Quiero analizar un pasaje (Modo Socrático)")
with c3: 
    if st.button("🧑‍🏫 Maestro"): enviar("Modela una interpretación experta")
with c4: 
    if st.button("🔍 Revisión"): enviar("He subido mi documento. ACTIVA MODO AUDITOR ESTRICTO.")

# --- MOSTRAR CHAT ---
for m in st.session_state.messages:
    role = "assistant" if m["role"] == "model" else "user"
    with st.chat_message(role): st.markdown(m["content"])

# --- PROCESAMIENTO ---
if prompt := st.chat_input("Escribe aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Analizando..."):
            try:
                user_msg = st.session_state.messages[-1]["content"]
                contenido = [user_msg]
                
                if archivo:
                    part = types.Part.from_bytes(data=archivo.getvalue(), mime_type=archivo.type)
                    contenido.append(part)
                
                resp = st.session_state.chat.send_message(contenido)
                st.markdown(resp.text)
                st.session_state.messages.append({"role": "model", "content": resp.text})
            except Exception as e:
                st.error(f"Error: {e}")
