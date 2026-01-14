import streamlit as st
from google import genai
from google.genai import types
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Instructor Bíblico", page_icon="📖", layout="wide")
st.markdown("""<style>div.stButton > button {width: 100%; border-radius: 10px; height: 3em;}</style>""", unsafe_allow_html=True)

# --- MODELO VIGENTE (2026) ---
MODELO_ACTUAL = "gemini-2.5-flash"

# --- API KEY & CLIENTE ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("⚠️ Falta la API Key en los Secrets.")
    st.stop()

if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=api_key)

# --- CEREBRO (PROMPT) ---
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
                    with open(f"knowledge/{f}","r",encoding="utf-8") as x: texto+=f"\n--{f}--\n{x.read()}"
                except: pass
    return texto

# --- CONFIGURACIÓN DEL CHAT ---
# Inicializar chat si no existe
if "chat" not in st.session_state or st.session_state.chat is None:
    st.session_state.chat = st.session_state.client.chats.create(
        model=MODELO_ACTUAL,
        config=types.GenerateContentConfig(
            system_instruction=get_prompt(),
            temperature=0.3
        )
    )

if "messages" not in st.session_state: st.session_state.messages = []

# --- INTERFAZ ---
st.title("📖 Instructor de Interpretación Bíblica")

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3389/3389081.png", width=100)
    st.title("Panel de Control")
    archivo = st.file_uploader("📂 Subir Archivo", type=["pdf","txt","md"])
    if archivo: st.success("✅ Archivo cargado")
    
    st.markdown("---")
    # BOTÓN RESTAURADO (LIMPIEZA NORMAL)
    if st.button("🗑️ Reiniciar Chat", type="primary"):
        st.session_state.chat = None
        st.session_state.messages = []
        st.rerun()

# --- 4 BOTONES DE ACCIÓN ---
c1,c2,c3,c4 = st.columns(4)
def enviar(t): st.session_state.messages.append({"role":"user","content":t})

with c1: 
    if st.button("🎓 Aula"): enviar("Iniciar Modo Aula: Lección 1")
with c2: 
    if st.button("📝 Alumno"): enviar("Quiero analizar un pasaje (Socrático)")
with c3: 
    if st.button("🧑‍🏫 Maestro"): enviar("Modela una interpretación experta")
with c4: 
    if st.button("🔍 Revisión"): enviar("ACTIVA MODO AUDITOR. Revisa mi archivo.")

# --- CHAT LOOP ---
for m in st.session_state.messages:
    r = "assistant" if m["role"]=="model" else "user"
    with st.chat_message(r): st.markdown(m["content"])

# --- LÓGICA DE RESPUESTA ---
if prompt := st.chat_input("Escribe tu pregunta o respuesta..."):
    st.session_state.messages.append({"role":"user","content":prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Analizando..."):
            try:
                msg_content = [st.session_state.messages[-1]["content"]]
                
                if archivo:
                    msg_content.append(types.Part.from_bytes(data=archivo.getvalue(), mime_type=archivo.type))
                
                res = st.session_state.chat.send_message(msg_content)
                st.markdown(res.text)
                st.session_state.messages.append({"role":"model","content":res.text})
            except Exception as e:
                st.error(f"Error: {e}")
