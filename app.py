import streamlit as st
from google import genai
from google.genai import types
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Instructor Bíblico 2026", page_icon="📖", layout="wide")
st.markdown("""<style>div.stButton > button {width: 100%; border-radius: 10px; height: 3em;}</style>""", unsafe_allow_html=True)

# --- MODELO VIGENTE (2026) ---
# Usamos el 2.5 Flash que es el estable actual
MODELO_ACTUAL = "gemini-2.5-flash"

# --- API KEY & CLIENTE ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("⚠️ Falta la API Key en los Secrets.")
    st.stop()

# Inicializar Cliente
if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=api_key)

# --- CEREBRO (PROMPT) ---
INSTRUCCIONES = """
ACTÚA COMO: Instructor de Seminario experto en Hermenéutica Expositiva.
TU FILOSOFÍA: "Permanecer en la línea".
MODO 1: MAESTRO SOCRÁTICO (Aula/Alumno) -> Sé breve, pregunta y espera.
MODO 2: AUDITOR ESTRICTO (Revisión) -> Sé crítico, usa la Hoja de Evaluación.
"""

def get_prompt():
    texto = INSTRUCCIONES
    if os.path.exists("knowledge"):
        for f in os.listdir("knowledge"):
            if f.endswith((".md", ".txt")):
                try: 
                    with open(f"knowledge/{f}","r",encoding="utf-8") as x: texto+=f"\n--{f}--\n{x.read()}"
                except: pass
    return texto

# --- GESTIÓN DE SESIÓN Y MODELO (EVITA EL ERROR DE CACHÉ) ---
# Si el modelo guardado no es el 2.5, reseteamos el chat para forzar el cambio
if st.session_state.get("model_name") != MODELO_ACTUAL:
    st.session_state.model_name = MODELO_ACTUAL
    st.session_state.chat = None
    st.session_state.messages = []

# Crear el chat si no existe
if st.session_state.chat is None:
    st.session_state.chat = st.session_state.client.chats.create(
        model=MODELO_ACTUAL,
        config=types.GenerateContentConfig(
            system_instruction=get_prompt(),
            temperature=0.3
        )
    )

if "messages" not in st.session_state: st.session_state.messages = []

# --- INTERFAZ ---
st.title(f"📖 Instructor Bíblico (v{MODELO_ACTUAL})")

with st.sidebar:
    st.title("Panel de Control")
    archivo = st.file_uploader("📂 Subir Archivo", type=["pdf","txt","md"])
    
    st.markdown("---")
    # BOTÓN DE RESET MANUAL (CLAVE PARA TU PROBLEMA)
    if st.button("🔄 Reset Total (Borrar Memoria)", type="primary"):
        st.session_state.chat = None
        st.session_state.messages = []
        st.session_state.model_name = None # Forzar recarga
        st.rerun()

# --- 4 BOTONES DE ACCIÓN ---
c1,c2,c3,c4 = st.columns(4)
def enviar(t): st.session_state.messages.append({"role":"user","content":t})

with c1: 
    if st.button("🎓 Aula"): enviar("Modo Aula: Lección 1")
with c2: 
    if st.button("📝 Alumno"): enviar("Quiero analizar un pasaje (Socrático)")
with c3: 
    if st.button("🧑‍🏫 Maestro"): enviar("Modela una interpretación")
with c4: 
    if st.button("🔍 Revisión"): enviar("ACTIVA MODO AUDITOR. Revisa mi archivo.")

# --- CHAT LOOP ---
for m in st.session_state.messages:
    r = "assistant" if m["role"]=="model" else "user"
    with st.chat_message(r): st.markdown(m["content"])

# --- LÓGICA DE RESPUESTA ---
if prompt := st.chat_input("Escribe aquí..."):
    st.session_state.messages.append({"role":"user","content":prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner(f"Analizando con {MODELO_ACTUAL}..."):
            try:
                msg_content = [st.session_state.messages[-1]["content"]]
                
                # Manejo de archivos (SDK Nuevo)
                if archivo:
                    msg_content.append(types.Part.from_bytes(data=archivo.getvalue(), mime_type=archivo.type))
                
                res = st.session_state.chat.send_message(msg_content)
                st.markdown(res.text)
                st.session_state.messages.append({"role":"model","content":res.text})
            except Exception as e:
                st.error(f"Error: {e}")
                if "404" in str(e):
                    st.warning("⚠️ Error 404: El modelo no existe. Intenta cambiar MODELO_ACTUAL en el código.")
