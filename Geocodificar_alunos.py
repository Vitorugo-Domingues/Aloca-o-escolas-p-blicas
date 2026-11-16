import pandas as pd
from geopy.geocoders import ArcGIS
from time import sleep

Pasta_base = r"C:\Users\suell\Desktop\Faculdade\6º Semestre\TCC II\Base"

def geocodificar_alunos(df, municipio):

    # Cria uma cópia da planilha
    df = df.copy().reset_index(drop=True)

    # Trata os campos de endereço
    df["Endereço"] = df["Endereço"].fillna("").astype(str)
    df["Número"] = df["Número"].fillna("").astype(str)
    df["CEP"] = df["CEP"].fillna("").astype(str)

    # Cria as colunas de coordenadas
    df["LATITUDE"] = None
    df["LONGITUDE"] = None

    # Inicializa o geocodificador
    geolocalizador = ArcGIS(timeout=20)

    # Geocodificar alunos
    for i in df.index:

        endereco = df.loc[i, "Endereço"]
        numero = df.loc[i, "Número"]
        cep = df.loc[i, "CEP"]

        consulta = f"{endereco}, {numero}, {cep}, {municipio}, SP, Brasil"

        try:
            local = geolocalizador.geocode(consulta)

            if local:
                df.loc[i, "LATITUDE"] = round(local.latitude, 8)
                df.loc[i, "LONGITUDE"] = round(local.longitude, 8)

        except Exception as erro:
            print(f"Erro no aluno {i + 1}: {erro}")

        sleep(1)

    # Converter coordenadas para números
    df["LATITUDE"] = pd.to_numeric(df["LATITUDE"], errors="coerce")
    df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"], errors="coerce")

    # Contar endereços encontrados
    encontrados = df["LATITUDE"].notna().sum()
    nao_encontrados = len(df) - encontrados

    print(f"Endereços encontrados: {encontrados}")
    print(f"Endereços não encontrados: {nao_encontrados}")

    # Definir nome e caminho do arquivo
    nome_arquivo = "alunos_geolocalizados_" + municipio.lower().replace(" ", "_") + ".csv"
    caminho_saida = Pasta_base + "\\" + nome_arquivo

    # Salvar arquivo
    df.to_csv(caminho_saida, index=False, sep=";", encoding="latin-1")

    return df
