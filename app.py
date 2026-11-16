import streamlit as st
import pandas as pd
import numpy as np

from geocodificar_alunos_final import geocodificar_alunos
from Roteirizador_final import processar_alocacao
from calcular_distancias_final import carregar_escolas, calcular_distancias

# Configuração da página
st.set_page_config(
    page_title="Alocação Escolar",
    page_icon="🏫",
    layout="centered"
)

# Cabeçalho
st.title("🏫 Sistema de Alocação Escolar")
st.write(
    "Modelo de programação linear para alocação de alunos "
    "na rede municipal de ensino."
)

st.divider()


# Seleção do município
st.subheader("1. Seleção do município")

municipio = st.selectbox("Selecione o município:", ["Cajamar", "Santana de Parnaíba"])

# Envio da planilha
st.subheader("2. Envio dos dados dos alunos")

st.info(
    """
    **Formato:** Excel (.xlsx).

    A planilha deve conter as seguintes colunas:
    - Nome
    - Endereço
    - Número
    - CEP
    - escolaridade
    
    (Respeite a ordem e título das colunas)
    """
)

arquivo = st.file_uploader("Selecione a planilha Excel",type=["xlsx"])

# Leitura da planilha
if arquivo is not None:
    alunos = pd.read_excel(arquivo)

    if all(coluna in alunos.columns for coluna in ["Nome", "Endereço", "Número", "CEP", "escolaridade"]):
        st.success(f"{len(alunos)} alunos identificados.")
        st.dataframe(alunos)
    else:
        st.error("A planilha não possui todas as colunas obrigatórias.")

# Iniciar processamento
if arquivo is not None and st.button("Iniciar alocação"):

    with st.spinner("Processando alocação dos alunos..."):

        # Geocodifica os endereços
        alunos_geo = geocodificar_alunos(alunos, municipio)

        # Carrega as escolas e calcula as distâncias
        escolas = carregar_escolas(municipio)
        matriz_distancias = calcular_distancias(alunos_geo, escolas)

        # Executa a otimização
        resultados, distancia_total = processar_alocacao(
            alunos_geo,
            municipio,
            matriz_distancias
        )

        # Calcula a porcentagem de alunos alocados na escola mais próxima
        menores_distancias = matriz_distancias.min(axis=1)

        alocados_mais_proxima = np.isclose(
            resultados["DISTANCIA_KM"].to_numpy(),
            menores_distancias
        )

        porcentagem_mais_proxima = alocados_mais_proxima.mean() * 100

        # Armazena os resultados
        st.session_state["resultados"] = resultados
        st.session_state["distancia_total"] = distancia_total
        st.session_state["porcentagem_mais_proxima"] = porcentagem_mais_proxima

    st.success("Alocação concluída!")

# Exibição dos resultados
if "resultados" in st.session_state:

    resultados = st.session_state["resultados"]
    distancias = resultados["DISTANCIA_KM"]

    st.divider()
    st.subheader("3. Resultado da alocação")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Distância média", f"{distancias.mean():.2f} km")
    col2.metric("Menor distância", f"{distancias.min():.2f} km")
    col3.metric("Maior distância", f"{distancias.max():.2f} km")

    col4.metric(
        "Alunos na escola mais próxima",
        f"{st.session_state['porcentagem_mais_proxima']:.1f}%"
    )

    st.dataframe(resultados, use_container_width=True)

    # Prepara o arquivo para download
    arquivo_resultados = resultados.to_csv(
        index=False,
        sep=";",
        encoding="latin-1"
    )

    # Botão para baixar os resultados
    st.download_button(
        "Baixar resultado da alocação",
        arquivo_resultados,
        file_name="resultado_alocacao.csv",
        mime="text/csv"
    )