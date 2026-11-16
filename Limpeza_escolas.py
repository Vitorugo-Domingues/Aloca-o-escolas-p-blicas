import pandas as pd
from geopy.geocoders import ArcGIS
from time import sleep

# Caminhos dos arquivos
caminho_escolas = r"C:\Users\suell\Desktop\Faculdade\6º Semestre\TCC II\Dados\Antigo\Tabela_Escola_2025.csv"
caminho_turmas = r"C:\Users\suell\Desktop\Faculdade\6º Semestre\TCC II\Dados\Antigo\Tabela_Turma_2025.csv"
caminho_saida = r"C:\Users\suell\Desktop\Faculdade\6º Semestre\TCC II\Base\escolas_filtradas.csv"

# Leitura das bases
df = pd.read_csv(caminho_escolas, sep=";", encoding="latin1")
df_turmas = pd.read_csv(caminho_turmas, sep=";", encoding="latin1")

# Filtrar municípios
df = df[
    (df["NO_REGIAO"] == "Sudeste") &
    (df["NO_UF"] == "São Paulo") &
    (df["NO_MUNICIPIO"].isin(["Santana de Parnaíba", "Cajamar"])) &
    (df["TP_DEPENDENCIA"] == 3)
    ]

# Colunas da base de escolas
colunas = [
    "NU_ANO_CENSO",
    "NO_REGIAO",
    "NO_UF",
    "NO_MUNICIPIO",
    "CO_MUNICIPIO",
    "NO_MESORREGIAO",
    "NO_MICRORREGIAO",
    "NO_ENTIDADE",
    "CO_ENTIDADE",
    "TP_DEPENDENCIA",
    "DS_ENDERECO",
    "NU_ENDERECO",
    "NO_BAIRRO",
    "CO_CEP",
    "NU_DDD",
    "NU_TELEFONE",
    "LATITUDE",
    "LONGITUDE",
    "TP_SITUACAO_FUNCIONAMENTO"
]

df = df[colunas]

# Colunas da base de turmas
colunas_turma = [
    "NU_ANO_CENSO",
    "CO_ENTIDADE",
    "QT_TUR_INF_CRE",
    "QT_TUR_INF_PRE",
    "QT_TUR_FUND_AI_1",
    "QT_TUR_FUND_AI_2",
    "QT_TUR_FUND_AI_3",
    "QT_TUR_FUND_AI_4",
    "QT_TUR_FUND_AI_5",
    "QT_TUR_FUND_AF_6",
    "QT_TUR_FUND_AF_7",
    "QT_TUR_FUND_AF_8",
    "QT_TUR_FUND_AF_9"
]

df_turmas = df_turmas[colunas_turma]

# Relacionamento das bases
df = df.merge(df_turmas, on=["NU_ANO_CENSO", "CO_ENTIDADE"], how="left")

# Ajustar coordenadas
df["LATITUDE"] = pd.to_numeric(df["LATITUDE"], errors="coerce")
df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"], errors="coerce")

# Escolas sem coordenadas
sem_coordenadas = df[df["LATITUDE"].isna() | df["LONGITUDE"].isna()]

# Geolocalizador
geolocalizador = ArcGIS(timeout=20)

# Buscar coordenadas faltantes
for i in sem_coordenadas.index:

    numero = ""
    bairro = ""
    cep = ""

    if pd.notna(df.loc[i, "NU_ENDERECO"]):
        numero = str(df.loc[i, "NU_ENDERECO"])

    if pd.notna(df.loc[i, "NO_BAIRRO"]):
        bairro = str(df.loc[i, "NO_BAIRRO"])

    if pd.notna(df.loc[i, "CO_CEP"]):
        cep = str(df.loc[i, "CO_CEP"])

    endereco = (f"{df.loc[i, 'DS_ENDERECO']}, {numero}, {bairro}, {cep}, {df.loc[i, 'NO_MUNICIPIO']}, SP, Brasil")

    #Consulta do endereço
    localizacao = geolocalizador.geocode(endereco)

    if localizacao:
        df.loc[i, "LATITUDE"] = round(localizacao.latitude, 8)
        df.loc[i, "LONGITUDE"] = round(localizacao.longitude, 8)
    else:
        print(f"Endereço não encontrado: {endereco}")

    sleep(1)

# Calcular vagas e renomear colunas
df = df.rename(columns={
    "QT_TUR_INF_CRE": "QT_VAGAS_INF_CRE",
    "QT_TUR_INF_PRE": "QT_VAGAS_INF_PRE",
    "QT_TUR_FUND_AI_1": "QT_VAGAS_FUND_AI_1",
    "QT_TUR_FUND_AI_2": "QT_VAGAS_FUND_AI_2",
    "QT_TUR_FUND_AI_3": "QT_VAGAS_FUND_AI_3",
    "QT_TUR_FUND_AI_4": "QT_VAGAS_FUND_AI_4",
    "QT_TUR_FUND_AI_5": "QT_VAGAS_FUND_AI_5",
    "QT_TUR_FUND_AF_6": "QT_VAGAS_FUND_AF_6",
    "QT_TUR_FUND_AF_7": "QT_VAGAS_FUND_AF_7",
    "QT_TUR_FUND_AF_8": "QT_VAGAS_FUND_AF_8",
    "QT_TUR_FUND_AF_9": "QT_VAGAS_FUND_AF_9"
})


# Calcular vagas por etapa de ensino
df["QT_VAGAS_INF_CRE"] = df["QT_VAGAS_INF_CRE"].fillna(0) * 10
df["QT_VAGAS_INF_PRE"] = df["QT_VAGAS_INF_PRE"].fillna(0) * 20

df["QT_VAGAS_FUND_AI_1"] = df["QT_VAGAS_FUND_AI_1"].fillna(0) * 30
df["QT_VAGAS_FUND_AI_2"] = df["QT_VAGAS_FUND_AI_2"].fillna(0) * 30
df["QT_VAGAS_FUND_AI_3"] = df["QT_VAGAS_FUND_AI_3"].fillna(0) * 30
df["QT_VAGAS_FUND_AI_4"] = df["QT_VAGAS_FUND_AI_4"].fillna(0) * 30
df["QT_VAGAS_FUND_AI_5"] = df["QT_VAGAS_FUND_AI_5"].fillna(0) * 30

df["QT_VAGAS_FUND_AF_6"] = df["QT_VAGAS_FUND_AF_6"].fillna(0) * 30
df["QT_VAGAS_FUND_AF_7"] = df["QT_VAGAS_FUND_AF_7"].fillna(0) * 30
df["QT_VAGAS_FUND_AF_8"] = df["QT_VAGAS_FUND_AF_8"].fillna(0) * 30
df["QT_VAGAS_FUND_AF_9"] = df["QT_VAGAS_FUND_AF_9"].fillna(0) * 30

# Calcular total de vagas por escola
df["QT_VAGAS_TOTAL"] = df[[
    "QT_VAGAS_INF_CRE",
    "QT_VAGAS_INF_PRE",
    "QT_VAGAS_FUND_AI_1",
    "QT_VAGAS_FUND_AI_2",
    "QT_VAGAS_FUND_AI_3",
    "QT_VAGAS_FUND_AI_4",
    "QT_VAGAS_FUND_AI_5",
    "QT_VAGAS_FUND_AF_6",
    "QT_VAGAS_FUND_AF_7",
    "QT_VAGAS_FUND_AF_8",
    "QT_VAGAS_FUND_AF_9"
]].sum(axis=1)

# Salvar base de escolas
df.to_csv(caminho_saida, sep=";", index=False, encoding="latin1")

print("Base de escolas salva com sucesso!")
