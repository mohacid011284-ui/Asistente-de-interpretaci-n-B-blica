import streamlit as st
from google import genai
from google.genai import types
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Instructor Bíblico", page_icon="📖", layout="wide")
st.markdown("""<style>div.stButton > button {width: 100%; border-radius: 10px; height: 3em;}</style>""", unsafe_allow_html=True)

# --- MODELO VIGENTE ---
MODELO_ACTUAL = "gemini-2.5-flash"

# --- API KEY & CLIENTE ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("⚠️ Falta la API Key en los Secrets.")
    st.stop()

if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=api_key)

# --- CEREBRO (PROMPT ESTRICTO) ---
INSTRUCCIONES_BASE = """
ROL: Eres un Instructor de Seminario de Hermenéutica Expositiva.
FUENTE: Usa EXCLUSIVAMENTE los archivos de la BIBLIOTECA.

MODO 1: MAESTRO (Botón 'Aula')
🛑 REGLA DE ORO: ¡NO preguntes sin antes enseñar!
TU SECUENCIA OBLIGATORIA DE RESPUESTA ES:
1. 📖 EXPOSICIÓN: Lee el tema correspondiente en el PLAN DE ESTUDIO/MANUAL. Explica el concepto clave en 1 o 2 párrafos claros (cita el manual).
2. ❓ INTERACCIÓN: SOLO DESPUÉS de explicar, haz UNA pregunta para asegurar que el alumno entendió lo que acabas de explicar.
3. ESPERA: No des la siguiente lección hasta que el alumno responda.

MODO 2: AUDITOR (Botón 'Revisión')
- Compara el sermón/texto del alumno contra las REGLAS del Manual.
- Sé estricto. Cita la regla que se rompió.
"""

def get_prompt():
    texto = INSTRUCCIONES_BASE
    texto += "\n\n=== BIBLIOTECA (TUS ARCHIVOS) ===\n"
    if os.path.exists("knowledge"):
        for f in os.listdir("knowledge"):
            if f.endswith((".md", ".txt")):
                try: 
                    with open(f"knowledge/{f}","r",encoding="utf-8") as x: 
                        texto += f"\n--- CONTENIDO DE {f.upper()} ---\n{x.read()}\n"
                except: pass
    return texto

# --- CHAT ---
if "chat" not in st.session_state or st.session_state.chat is None:
    st.session_state.chat = st.session_state.client.chats.create(
        model=MODELO_ACTUAL,
        config=types.GenerateContentConfig(system_instruction=get_prompt(), temperature=0.3)
    )

if "messages" not in st.session_state: st.session_state.messages = []

# --- FUNCIONES SEGURAS (CALLBACKS) ---
# Estas funciones evitan el error "removeChild"
def enviar_mensaje(texto):
    st.session_state.messages.append({"role": "user", "content": texto})

def reiniciar():
    st.session_state.chat = None
    st.session_state.messages = []

# --- INTERFAZ ---
st.title("📖 Instructor de Interpretación Bíblica")

with st.sidebar:
    st.title("Panel de Control")
    archivo = st.file_uploader("📂 Subir Archivo", type=["pdf","txt","md"])
    if archivo: st.success("✅ Archivo cargado")

# --- VERIFICADOR DE BIBLIOTECA ---
    st.divider() # Línea divisoria
    st.write("📚 **Estado de la Biblioteca:**")
    
    if os.path.exists("knowledge"):
        archivos_leidos = [f for f in os.listdir("knowledge") if f.endswith((".md", ".txt"))]
        
        if archivos_leidos:
            st.success(f"✅ {len(archivos_leidos)} archivos cargados")
            for arch in archivos_leidos:
                st.code(arch, language="markdown")
        else:
            st.error("⚠️ La carpeta existe pero no tiene archivos .md o .txt")
    else:
        st.error("❌ No encuentro la carpeta 'knowledge' en el sistema")
    
    st.markdown("---")
    # Usamos on_click para mayor estabilidad
    st.button("🗑️ Reiniciar Chat", type="primary", on_click=reiniciar)

# --- 4 BOTONES DE ACCIÓN (CON PROTECCIÓN) ---
c1,c2,c3,c4 = st.columns(4)

with c1: 
    st.button("🎓 Aula", on_click=enviar_mensaje, args=("Iniciar Modo Aula: Lección 1",))
with c2: 
    st.button("📝 Alumno", on_click=enviar_mensaje, args=("Quiero analizar un pasaje (Socrático)",))
with c3: 
    st.button("🧑‍🏫 Maestro", on_click=enviar_mensaje, args=("Modela una interpretación experta",))
with c4: 
    st.button("🔍 Revisión", on_click=enviar_mensaje, args=("ACTIVA MODO AUDITOR. Revisa mi archivo.",))

# --- MOSTRAR CHAT ---
for m in st.session_state.messages:
    r = "assistant" if m["role"]=="model" else "user"
    with st.chat_message(r): st.markdown(m["content"])

# --- INPUT DE USUARIO ---
if prompt := st.chat_input("Escribe tu respuesta..."):
    st.session_state.messages.append({"role":"user","content":prompt})
    st.rerun()

# --- RESPUESTA DEL MODELO ---
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
