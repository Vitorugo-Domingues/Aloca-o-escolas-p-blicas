import os
import numpy as np
import pandas as pd
import requests

# Configurações
OSRM_URL = "http://127.0.0.1:5000"

PASTA_BASE = r"C:\Users\suell\Desktop\Faculdade\6º Semestre\TCC II\Base"

CAMINHO_ESCOLAS = os.path.join(PASTA_BASE, "escolas_filtradas.csv")

TAMANHO_BLOCO = 20


def carregar_escolas(municipio):

    # Carregar a base de escolas
    escolas = pd.read_csv(CAMINHO_ESCOLAS, sep=";", encoding="latin-1")

    # Filtrar escolas do município em funcionamento
    escolas = escolas[(escolas["NO_MUNICIPIO"] == municipio) & (escolas["TP_SITUACAO_FUNCIONAMENTO"] == 1)].copy()

    # Converter o código INEP para texto
    escolas["CO_ENTIDADE"] = escolas["CO_ENTIDADE"].astype(str)

    # Converter coordenadas para números
    escolas["LATITUDE"] = pd.to_numeric(escolas["LATITUDE"], errors="coerce")
    escolas["LONGITUDE"] = pd.to_numeric(escolas["LONGITUDE"], errors="coerce")

    return escolas

def calcular_distancias(alunos, escolas):

    # Verificar coordenadas dos alunos
    if alunos[["LATITUDE", "LONGITUDE"]].isna().any().any():
        raise ValueError(
            "Existem alunos sem coordenadas válidas. "
            "Verifique o arquivo de geocodificação."
        )
    
    # Coordenadas das escolas
    coordenadas_escolas = [f"{lon},{lat}" for lon, lat in zip(escolas["LONGITUDE"], escolas["LATITUDE"])]

    # Criar matriz preenchida com infinito para evitar divergências com coordernadas iguais a 0
    matriz = np.full((len(alunos), len(escolas)), np.inf)

    #Quantidade de blocos para o processamento em lote
    total_blocos = int(np.ceil(len(alunos) / TAMANHO_BLOCO))

    print("\nIniciando cálculo das distâncias...")

    for inicio in range(0, len(alunos), TAMANHO_BLOCO):

        fim = min(inicio + TAMANHO_BLOCO, len(alunos))
        bloco = alunos.iloc[inicio:fim]

        coordenadas_alunos = [f"{lon},{lat}" for lon, lat in zip(bloco["LONGITUDE"], bloco["LATITUDE"])]

        # Juntar coordenadas dos alunos e das escolas
        coordenadas = (coordenadas_alunos + coordenadas_escolas)
        coordenadas_url = ";".join(coordenadas)

        # Índices das origens
        fontes = ";".join(str(i) for i in range(len(coordenadas_alunos)))

        # Índices dos destinos
        destinos = ";".join(str(i) for i in range(len(coordenadas_alunos), len(coordenadas)))
        
        url = (
            f"{OSRM_URL}/table/v1/driving/"
            f"{coordenadas_url}"
            f"?sources={fontes}"
            f"&destinations={destinos}"
            f"&annotations=distance"
        )

        try:

            resposta = requests.get(url,timeout=120)

            if resposta.status_code != 200:
                raise RuntimeError(f"Erro HTTP {resposta.status_code}: " f"{resposta.text}")

            resultado = resposta.json()

            if resultado.get("code") != "Ok":
                raise RuntimeError(f"Erro OSRM: {resultado}")

            distancias = resultado["distances"]

            # Converter metros para quilômetros
            matriz[inicio:fim, :] = (np.array(distancias) / 1000)

            bloco_atual = (inicio // TAMANHO_BLOCO) + 1

            print(
                f"Bloco {bloco_atual}/{total_blocos} "
                f"processado: alunos {inicio + 1} a {fim}"
            )

        except requests.exceptions.RequestException as erro:

            raise RuntimeError(
                f"Falha na comunicação com o OSRM "
                f"no bloco {inicio + 1} a {fim}: {erro}"
            )

    print("\nCálculo das distâncias concluído!")

    return matriz

def salvar_matriz(alunos, escolas, matriz, municipio):

    # Identificar escolas pelo código INEP
    colunas_escolas = [f"ESCOLA_{codigo}" for codigo in escolas["CO_ENTIDADE"]]

    matriz_df = pd.DataFrame(
        matriz,
        columns=colunas_escolas
    )

    # Informações dos alunos
    matriz_df.insert(0, "escolaridade", alunos["escolaridade"].values)

    matriz_df.insert(0, "Nome", alunos["Nome"].values)

    # Nome do arquivo
    nome_municipio = (municipio.lower().replace(" ", "_"))

    nome_arquivo = (f"matriz_distancias_{nome_municipio}.csv")

    caminho_saida = os.path.join(PASTA_BASE, nome_arquivo)

    matriz_df.to_csv(caminho_saida, index=False, sep=";", encoding="latin-1")

    print(f"\nMatriz salva em:\n{caminho_saida}")

    return caminho_saida
