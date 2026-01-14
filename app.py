import streamlit as st
from google import genai
from google.genai import types
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Instructor Bíblico", page_icon="📖", layout="wide")
st.markdown("""<style>div.stButton > button {width: 100%; border-radius: 10px; height: 3em;}</style>""", unsafe_allow_html=True)

# --- CONEXIÓN NUEVA (SDK GOOGLE-GENAI) ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("⚠️ Falta la API Key en los Secrets.")
    st.stop()

if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=api_key)

# --- PROMPT ---
INSTRUCCIONES = """ACTÚA COMO: Instructor de Seminario. MODO AULA: Socrático. MODO REVISIÓN: Crítico y usa hoja de evaluación."""
def get_prompt():
    t = INSTRUCCIONES
    if os.path.exists("knowledge"):
        for f in os.listdir("knowledge"):
            if f.endswith((".md", ".txt")):
                try: 
                    with open(f"knowledge/{f}","r",encoding="utf-8") as x: t+=f"\n--{f}--\n{x.read()}"
                except: pass
    return t

# --- CHAT ---
if "chat" not in st.session_state or st.session_state.chat is None:
    # Usamos el modelo ESTABLE (1.5 Flash) que ya pagaste
    st.session_state.chat = st.session_state.client.chats.create(
        model="gemini-1.5-flash",
        config=types.GenerateContentConfig(system_instruction=get_prompt(), temperature=0.3)
    )

if "messages" not in st.session_state: st.session_state.messages = []

# --- INTERFAZ ---
st.title("📖 Instructor Bíblico")

with st.sidebar:
    st.title("Panel")
    archivo = st.file_uploader("Subir Archivo", type=["pdf","txt","md"])
    if st.button("🗑️ Reiniciar"): 
        st.session_state.chat = None
        st.session_state.messages = []
        st.rerun()

# --- LOS 4 BOTONES ---
c1,c2,c3,c4 = st.columns(4)
def click(t): st.session_state.messages.append({"role":"user","content":t})
with c1: 
    if st.button("🎓 Aula"): click("Modo Aula")
with c2: 
    if st.button("📝 Alumno"): click("Modo Alumno")
with c3: 
    if st.button("🧑‍🏫 Maestro"): click("Modo Maestro")
with c4: 
    if st.button("🔍 Revisión"): click("Modo Revisión (Auditor)")

# --- MOSTRAR CHAT ---
for m in st.session_state.messages:
    r = "assistant" if m["role"]=="model" else "user"
    with st.chat_message(r): st.markdown(m["content"])

# --- LÓGICA DE ENVÍO ---
if p := st.chat_input("Escribe aquí..."):
    st.session_state.messages.append({"role":"user","content":p})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"]=="user":
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                c = [st.session_state.messages[-1]["content"]]
                if archivo:
                    # Código nuevo para archivos
                    c.append(types.Part.from_bytes(data=archivo.getvalue(), mime_type=archivo.type))
                
                res = st.session_state.chat.send_message(c)
                st.markdown(res.text)
                st.session_state.messages.append({"role":"model","content":res.text})
            except Exception as e: st.error(f"Error: {e}")
