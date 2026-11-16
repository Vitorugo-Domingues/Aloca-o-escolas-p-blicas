import os
import re
import unicodedata
import numpy as np
import pandas as pd

from scipy.optimize import linprog
from scipy.sparse import lil_matrix

PASTA_BASE = r"C:\Users\suell\Desktop\Faculdade\6º Semestre\TCC II\Base"

CAMINHO_ESCOLAS = os.path.join(PASTA_BASE, "escolas_filtradas.csv")

COLUNAS_VAGAS = {
    "CRECHE": "QT_VAGAS_INF_CRE",
    "PRE": "QT_VAGAS_INF_PRE",
    "ANO_1": "QT_VAGAS_FUND_AI_1",
    "ANO_2": "QT_VAGAS_FUND_AI_2",
    "ANO_3": "QT_VAGAS_FUND_AI_3",
    "ANO_4": "QT_VAGAS_FUND_AI_4",
    "ANO_5": "QT_VAGAS_FUND_AI_5",
    "ANO_6": "QT_VAGAS_FUND_AF_6",
    "ANO_7": "QT_VAGAS_FUND_AF_7",
    "ANO_8": "QT_VAGAS_FUND_AF_8",
    "ANO_9": "QT_VAGAS_FUND_AF_9"
}

def normalizar_texto(texto):

    texto = str(texto).strip().upper()
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("ASCII")
    return texto

def identificar_grupo(escolaridade):

    valor = normalizar_texto(escolaridade)

    if "CRECHE" in valor:
        return "CRECHE"

    if "PRE" in valor:
        return "PRE"

    ano = re.search(r"(\d+)", valor)

    if ano:
        numero = int(ano.group(1))

        if 1 <= numero <= 9:
            return f"ANO_{numero}"

    raise ValueError(f"Não foi possível identificar a escolaridade: {escolaridade}")


def carregar_escolas(municipio):

    escolas = pd.read_csv(CAMINHO_ESCOLAS, sep=";", encoding="latin-1")

    escolas = escolas[
        (escolas["NO_MUNICIPIO"] == municipio) &
        (escolas["TP_SITUACAO_FUNCIONAMENTO"] == 1)
    ].copy()

    escolas["CO_ENTIDADE"] = escolas["CO_ENTIDADE"].astype(str)

    return escolas

def calcular_capacidades(escolas):

    capacidades = {}

    for grupo, coluna in COLUNAS_VAGAS.items():

        capacidades[grupo] = pd.to_numeric(escolas[coluna], errors="coerce").fillna(0).to_numpy()

    return capacidades

def distribuir_alunos(alunos, escolas, matriz_distancias, capacidades):

    # Quantidade de alunos e escolas
    n_alunos = len(alunos)
    n_escolas = len(escolas)

    # Converte as distâncias em matriz NumPy
    distancias = np.asarray(matriz_distancias, dtype=float)

    # Identifica a série de cada aluno
    grupos = [
        identificar_grupo(escolaridade)
        for escolaridade in alunos["escolaridade"]
    ]

    # Verifica se todos os alunos possuem rotas válidas
    if not np.isfinite(distancias).any(axis=1).all():
        raise ValueError("Existem alunos sem rotas válidas.")

    # Função objetivo: minimizar a distância total
    funcao_objetivo = np.where(
        np.isfinite(distancias), distancias, 0
    ).flatten()

    # Restrição 1: cada aluno deve ser alocado a exatamente uma escola
    A_eq = lil_matrix((n_alunos, n_alunos * n_escolas))

    for i in range(n_alunos):
        A_eq[i, i * n_escolas:(i + 1) * n_escolas] = 1

    b_eq = np.ones(n_alunos)

    # Restrição 2: a quantidade de alunos não pode ultrapassar as vagas de cada série em cada escola
    A_ub = lil_matrix((len(COLUNAS_VAGAS) * n_escolas, n_alunos * n_escolas))
    b_ub = []

    linha = 0

    for grupo in COLUNAS_VAGAS:

        for j in range(n_escolas):

            for i in range(n_alunos):

                if grupos[i] == grupo:
                    A_ub[linha, i * n_escolas + j] = 1

            b_ub.append(capacidades[grupo][j])
            linha += 1

    # Restrição 3: as variáveis de alocação devem ser binárias (0 ou 1)
    # Também impede alocações em escolas sem rota válida
    limites = [
        (0, 1) if np.isfinite(distancias[i, j]) else (0, 0)
        for i in range(n_alunos)
        for j in range(n_escolas)
    ]

    # Executa o modelo de otimização
    resultado = linprog(
        c=funcao_objetivo,
        A_ub=A_ub.tocsr(),
        b_ub=b_ub,
        A_eq=A_eq.tocsr(),
        b_eq=b_eq,
        bounds=limites,
        integrality=np.ones(n_alunos * n_escolas),
        method="highs"
    )

    # Verifica se foi encontrada uma solução
    if not resultado.success:
        raise ValueError(
            "Não foi possível realizar a otimização. "
            "Verifique os dados, as capacidades disponíveis e as restrições do modelo."
        )    

    # Organiza o resultado em uma matriz
    alocacao = resultado.x.reshape(n_alunos, n_escolas).round().astype(int)

    return alocacao, resultado.fun

def criar_resultados(alunos, escolas, alocacao, matriz_distancias):

    # Cria uma cópia da base de alunos
    resultados = alunos.copy().reset_index(drop=True)

    # Identifica a escola escolhida para cada aluno
    indices_escolas = np.argmax(alocacao, axis=1)

    # Adiciona o código e o nome da escola escolhida
    resultados["CO_ENTIDADE"] = escolas.iloc[indices_escolas]["CO_ENTIDADE"].values
    resultados["ESCOLA_DESTINO"] = escolas.iloc[indices_escolas]["NO_ENTIDADE"].values

    # Adiciona a distância entre o aluno e a escola escolhida
    resultados["DISTANCIA_KM"] = matriz_distancias[
        np.arange(len(alunos)), indices_escolas
    ]

    return resultados

def processar_alocacao(alunos, municipio, matriz_distancias):

    # Carrega as escolas em funcionamento
    escolas = carregar_escolas(municipio)

    # Calcula as capacidades por série
    capacidades = calcular_capacidades(escolas)

    # Executa a otimização
    alocacao, distancia_total = distribuir_alunos(alunos, escolas, matriz_distancias, capacidades)

    # Organiza os resultados
    resultados = criar_resultados(alunos, escolas, alocacao, matriz_distancias)

    return resultados, distancia_total