import streamlit as st
import pandas as pd
import yaml
import os
from io import BytesIO

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


# ================================================================
# 🔄 FUNCIÓN PRINCIPAL DE PROCESAMIENTO (LO QUE VENÍA DE COLAB)
# ================================================================
def procesar_datos(app_file, cobros_file, sisco_file, hojas_autorizadas):

    # -----------------------------
    # 1️⃣ Leer APP y apilar hojas
    # -----------------------------
    Datos_app = pd.DataFrame()
    xls = pd.ExcelFile(app_file)

    for hoja in xls.sheet_names:
        if hoja.upper() in hojas_autorizadas:
            df = pd.read_excel(app_file, sheet_name=hoja)
            df["Nombre_Hoja"] = hoja
            Datos_app = pd.concat([Datos_app, df], ignore_index=True)

    # Separar Parqueadero
    if "Parqueadero" in Datos_app.columns:
        split = Datos_app["Parqueadero"].str.split("-", expand=True).fillna("")
        if split.shape[1] >= 2:
            Datos_app["Parqueadero_Parte2"] = split[1]

    # Contar parqueaderos
    if all(col in Datos_app.columns for col in ["Codigo", "Nombre_Hoja", "Parqueadero_Parte2"]):
        parqueadero_counts = (
            Datos_app.groupby(["Codigo", "Nombre_Hoja"])["Parqueadero_Parte2"]
            .value_counts()
            .unstack(fill_value=0)
        )
    else:
        st.error("❌ La APP no tiene las columnas requeridas.")
        return None

    # -----------------------------
    # 2️⃣ Leer Base de Cobros
    # -----------------------------
    Datos_cobros = pd.read_excel(cobros_file)

    parqueadero_counts = parqueadero_counts.reset_index()

    df_app = pd.merge(
        parqueadero_counts,
        Datos_cobros[["CONJUNTO", "CARRO", "MOTO"]],
        left_on="Nombre_Hoja",
        right_on="CONJUNTO",
        how="left"
    ).drop(columns=["CONJUNTO"])

    df_app["Fuente"] = "APP"
    df_app["moto"] = df_app["MOTO_x"] * df_app["MOTO_y"]
    df_app["cuotaparqu"] = df_app["CARRO_x"] * df_app["CARRO_y"]

    df_app = df_app[["Codigo", "Nombre_Hoja", "Fuente", "moto", "cuotaparqu"]]

    # -----------------------------
    # 3️⃣ Leer SISCO
    # -----------------------------
    xls2 = pd.ExcelFile(sisco_file)
    Data_sisco = pd.DataFrame()

    for hoja in xls2.sheet_names:
        df = pd.read_excel(sisco_file, sheet_name=hoja)
        df["Nombre_Hoja"] = hoja
        Data_sisco = pd.concat([Data_sisco, df], ignore_index=True)

    if not all(col in Data_sisco.columns for col in ["codigo", "Nombre_Hoja", "cuotaparqu", "moto"]):
        st.error("❌ La Base SISCO no tiene las columnas requeridas.")
        return None

    df_sisco = Data_sisco[["codigo", "Nombre_Hoja", "cuotaparqu", "moto"]].copy()
    df_sisco["Fuente"] = "SISCO"
    df_sisco = df_sisco.rename(columns={"codigo": "Codigo"})
    df_sisco = df_sisco[["Codigo", "Nombre_Hoja", "Fuente", "moto", "cuotaparqu"]]

    # -----------------------------
    # 4️⃣ Unir APP + SISCO
    # -----------------------------
    df_apilado = pd.concat([df_app, df_sisco], ignore_index=True)

    # -----------------------------
    # 5️⃣ Transformar formato
    # -----------------------------
    df_transformado = pd.melt(
        df_apilado,
        id_vars=["Codigo", "Nombre_Hoja", "Fuente"],
        value_vars=["moto", "cuotaparqu"],
        var_name="Tipo",
        value_name="Valor"
    )

    tabla = pd.pivot_table(
        df_transformado,
        index=["Codigo", "Nombre_Hoja", "Tipo"],
        columns="Fuente",
        values="Valor",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    tabla["Tipo"] = tabla["Tipo"].replace("cuotaparqu", "Carro")
    tabla["Validacion"] = tabla["APP"] - tabla["SISCO"]

    return tabla


# ==============================
# 🚀 Interfaz principal
# ==============================
def main():

    st.title("🧾 Sistema de Cruce de Parqueaderos")

    config = load_config()
    conjuntos_autorizados = load_conjuntos_autorizados()

    # LOGIN
    if "logged" not in st.session_state:
        st.session_state.logged = False

    if not st.session_state.logged:
        st.subheader("🔐 Inicio de sesión")
        username = st.text_input("👤 Usuario")
        password = st.text_input("🔑 Contraseña", type="password")

        if st.button("Iniciar sesión"):
            if username == config.get("username") and password == config.get("password"):
                st.session_state.logged = True
                st.success("Acceso concedido ✔")
            else:
                st.error("Usuario o contraseña incorrectos")
        return

    # ==============================
    # UI MEJORADA – PASO A PASO
    # ==============================

    st.success("🔓 Acceso verificado")
    st.markdown("---")

    st.header("📌 Paso 1: Cargar archivos requeridos")

    st.markdown("""
    Para ejecutar correctamente el cruce debes cargar **tres archivos Excel**:

    ### 📥 Archivos requeridos
    1. **Base APP**  
       Contiene los parqueaderos por unidad. Se descarga del sistema APP.

    2. **Base de Cobros**  
       Contiene tarifas de carro y moto por conjunto.

    3. **Base SISCO**  
       Contiene los valores cobrados realmente (carro y moto).

    ---
    """)

    # CARGA DE ARCHIVOS CON INSTRUCCIONES
    app_file = st.file_uploader(
        "📄 1. Cargar Archivo APP (Uno por conjunto – formato .xlsx)",
        type=["xlsx"],
        help="Debe contener varias hojas: cada hoja debe tener el nombre del conjunto."
    )

    cobros_file = st.file_uploader(
        "🏷️ 2. Cargar Archivo de Cobros (tarifas CARRO y MOTO)",
        type=["xlsx"],
        help="Archivo con columnas CONJUNTO, CARRO, MOTO."
    )

    sisco_file = st.file_uploader(
        "💰 3. Cargar Archivo SISCO (valores cobrados)",
        type=["xlsx"],
        help="Archivo que contiene las columnas codigo, cuotaparqu, moto y Nombre_Hoja."
    )

    st.markdown("---")

    # VALIDACIÓN AUTOMÁTICA DE HOJAS AUTORIZADAS
    if app_file:
        st.subheader("🔎 Validando conjuntos autorizados…")

        hojas_autorizadas, hojas_no_autorizadas = validar_hojas(app_file, conjuntos_autorizados)

        if hojas_autorizadas:
            st.success("🟢 Hojas autorizadas detectadas:")
            st.write(hojas_autorizadas)

        if hojas_no_autorizadas:
            st.warning("🟠 Hojas no autorizadas:")
            st.write(hojas_no_autorizadas)

        st.markdown("---")

    # ==============================
    # BOTÓN DE EJECUCIÓN
    # ==============================
    st.header("🚀 Paso 2: Ejecutar el Cruce")

    boton_disabled = not (app_file and cobros_file and sisco_file)

    if boton_disabled:
        st.info("⚠️ Debes cargar los **tres archivos** antes de ejecutar el cruce.")

    if st.button("🚀 Ejecutar Cruce", disabled=boton_disabled):
        tabla_final = procesar_datos(app_file, cobros_file, sisco_file, hojas_autorizadas)

        if tabla_final is not None:
            st.success("✔ Cruce realizado correctamente")
            st.dataframe(tabla_final)

            # Descargar
            buffer = BytesIO()
            tabla_final.to_excel(buffer, index=False)
            buffer.seek(0)

            st.download_button(
                label="📤 Descargar Informe Excel",
                data=buffer,
                file_name="Cruce_Parqueaderos.xlsx",
                mime="application/vnd.ms-excel"
            )


if __name__ == "__main__":
    main()



