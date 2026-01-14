import streamlit as st
from google import genai
from google.genai import types
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Instructor Bíblico", page_icon="📖", layout="wide")

# --- API KEY & CLIENTE (SDK NUEVO) ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("⚠️ Falta la API Key en los Secrets de Streamlit.")
    st.stop()

if "client" not in st.session_state:
    # Esta es la conexión moderna
    st.session_state.client = genai.Client(api_key=api_key)

# --- CEREBRO ---
INSTRUCCIONES = """
ACTÚA COMO: Instructor de Seminario (Hermenéutica).
MODO AULA: Sé socrático, breve.
MODO REVISIÓN: Sé crítico, usa la Hoja de Evaluación, señala errores.
"""

def get_prompt():
    texto = INSTRUCCIONES
    if os.path.exists("knowledge"):
        for f in os.listdir("knowledge"):
            if f.endswith(".md"):
                try: 
                    with open(f"knowledge/{f}", "r", encoding="utf-8") as file:
                        texto += f"\n--- {f} ---\n{file.read()}"
                except: pass
    return texto

# --- CHAT ---
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

# --- INTERFAZ ---
st.title("📖 Instructor Bíblico (Versión Pro)")

with st.sidebar:
    st.header("Herramientas")
    archivo = st.file_uploader("Subir Sermón/Hoja", type=["pdf", "txt", "md"])
    if st.button("🗑️ Reiniciar", type="primary"):
        st.session_state.chat = None
        st.session_state.messages = []
        st.rerun()

# Botones
cols = st.columns(4)
def enviar(txt): st.session_state.messages.append({"role": "user", "content": txt})
with cols[0]: 
    if st.button("🎓 Aula"): enviar("Modo Aula: Lección 1")
with cols[3]: 
    if st.button("🔍 Revisión"): enviar("ACTIVA MODO AUDITOR. Revisa mi archivo.")

# Chat Loop
for m in st.session_state.messages:
    role = "assistant" if m["role"] == "model" else "user"
    with st.chat_message(role): st.markdown(m["content"])

if prompt := st.chat_input("Escribe aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                contenido = [st.session_state.messages[-1]["content"]]
                if archivo:
                    # Manejo de archivo NUEVO SDK
                    part = types.Part.from_bytes(data=archivo.getvalue(), mime_type=archivo.type)
                    contenido.append(part)
                
                resp = st.session_state.chat.send_message(contenido)
                st.markdown(resp.text)
                st.session_state.messages.append({"role": "model", "content": resp.text})
            except Exception as e:
                st.error(f"Error: {e}")
