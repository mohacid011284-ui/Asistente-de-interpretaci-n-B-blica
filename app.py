import streamlit as st
import google.generativeai as genai

st.title("🛠️ Diagnóstico de Modelos")

# 1. Configurar API Key
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    st.success("✅ API Key encontrada.")
except Exception as e:
    st.error(f"❌ Error con la API Key: {e}")
    st.stop()

# 2. Listar modelos disponibles
st.write("Consultando a Google qué modelos están disponibles para esta API Key...")

try:
    available_models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            available_models.append(m.name)
            st.code(f"Encontrado: {m.name}")
    
    if not available_models:
        st.error("⚠️ No se encontraron modelos compatibles con 'generateContent'.")
    else:
        st.success(f"✅ Se encontraron {len(available_models)} modelos.")

except Exception as e:
    st.error(f"❌ Error crítico al listar modelos: {e}")
    st.info("Pista: Si el error menciona 'old version' o 'module not found', es que requirements.txt no se instaló bien.")
