import streamlit as st
import pandas as pd
import yaml
import os


try:
    import yaml
except ModuleNotFoundError:
    import ruamel.yaml as yaml

# ==============================
# 🔐 Cargar credenciales
# ==============================
def load_config():
    try:
        with open("config.yaml", "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
            return data["login"]
    except Exception as e:
        st.error(f"Error cargando config.yaml: {e}")
        return {}

# ==============================
# 📋 Cargar conjuntos autorizados
# ==============================
def load_conjuntos_autorizados():
    try:
        if not os.path.exists("conjuntos_autorizados.txt"):
            return []
        with open("conjuntos_autorizados.txt", "r", encoding="utf-8") as file:
            return [line.strip().upper() for line in file if line.strip()]
    except:
        return []

# ==============================
# 🔎 Validar hojas autorizadas
# ==============================
def validar_hojas(excel_file, conjuntos_autorizados):
    try:
        xls = pd.ExcelFile(excel_file)
        hojas_en_archivo = [h.upper() for h in xls.sheet_names]

        hojas_autorizadas = [h for h in hojas_en_archivo if h in conjuntos_autorizados]
        hojas_no_autorizadas = [h for h in hojas_en_archivo if h not in conjuntos_autorizados]

        return hojas_autorizadas, hojas_no_autorizadas
    except Exception as e:
        st.error(f"Error al leer el archivo Excel: {e}")
        return [], []

# ==============================
# 🧮 Procesar hojas autorizadas
# ==============================
def procesar_hojas(excel_path, hojas_autorizadas):
    for hoja in hojas_autorizadas:
        st.info(f"📄 Procesando hoja: {hoja}")
        df = pd.read_excel(excel_path, sheet_name=hoja)
        st.write(df.head())

# ==============================
# 🚀 Interfaz principal
# ==============================
def main():

    st.title("🧾 Control y ejecución de hojas autorizadas")

    config = load_config()
    conjuntos_autorizados = load_conjuntos_autorizados()

    # ==============================
    # LOGIN
    # ==============================
    st.subheader("Inicio de sesión")

    if "logged" not in st.session_state:
        st.session_state.logged = False

    if not st.session_state.logged:
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")

        if st.button("Iniciar sesión"):
            if username == config.get("username") and password == config.get("password"):
                st.session_state.logged = True
                st.success("✅ Acceso concedido")
            else:
                st.error("❌ Usuario o contraseña incorrectos")
        return  # <- detiene la app hasta que inicien sesión

    # ==============================
    # UNA VEZ LOGUEADO...
    # ==============================
    st.success("🔓 Acceso verificado")

    st.subheader("Selecciona el archivo Excel para procesar")
    archivo_excel = st.file_uploader("Cargar archivo (.xlsx)", type=["xlsx"])

    if archivo_excel is not None:
        hojas_autorizadas, hojas_no_autorizadas = validar_hojas(archivo_excel, conjuntos_autorizados)

        if hojas_no_autorizadas:
            st.warning("⚠️ Hojas no autorizadas detectadas:")
            for h in hojas_no_autorizadas:
                st.write(f"- {h}")

        if hojas_autorizadas:
            st.success("✅ Hojas autorizadas para ejecución:")
            for h in hojas_autorizadas:
                st.write(f"- {h}")

            procesar_hojas(archivo_excel, hojas_autorizadas)
        else:
            st.error("❌ No se encontró ninguna hoja autorizada para procesar.")


if __name__ == "__main__":
    main()


