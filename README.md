# Sistema de Alocação Escolar

Aplicação web que aloca alunos às escolas da rede municipal de ensino usando **programação linear inteira**, minimizando a distância total percorrida (por vias reais) e respeitando as vagas disponíveis por etapa de ensino em cada escola.

Municípios atendidos atualmente: **Cajamar** e **Santana de Parnaíba** (SP).

---

## Como funciona

```
Planilha de alunos (.xlsx)
        │
        ▼
1. Geocodificação dos endereços (ArcGIS)        → LATITUDE / LONGITUDE
        │
        ▼
2. Cálculo das distâncias aluno × escola (OSRM) → matriz de distâncias (km)
        │
        ▼
3. Otimização (programação linear inteira)      → escola de cada aluno
        │
        ▼
Resultados na tela + download em CSV
```

**Modelo de otimização**

- **Variáveis:** `x[i][j] ∈ {0, 1}`, igual a 1 se o aluno *i* for alocado à escola *j*.
- **Objetivo:** minimizar a soma das distâncias entre cada aluno e a escola de destino.
- **Restrições:**
  1. Cada aluno é alocado a exatamente uma escola.
  2. Em cada escola, o número de alunos de uma etapa (creche, pré-escola, 1º ao 9º ano) não pode ultrapassar as vagas daquela etapa.
  3. Alocações só são permitidas em escolas com rota válida.
- **Solver:** `scipy.optimize.linprog` (método HiGHS) com `integrality` ativado.

---

## Estrutura do projeto

| Arquivo | Função |
|---|---|
| `app.py` | Interface web em Streamlit: upload da planilha, execução do pipeline e exibição/download dos resultados. |
| `limpeza_escolas_final.py` | Prepara a base de escolas (executado uma única vez, fora do app). |
| `geocodificar_alunos_final.py` | Converte os endereços dos alunos em coordenadas geográficas. |
| `calcular_distancias_final.py` | Calcula a matriz de distâncias aluno × escola via OSRM. |
| `Roteirizador_final.py` | Monta e resolve o modelo de otimização e gera a tabela de resultados. |

### `limpeza_escolas_final.py`
Lê as tabelas de **Escola** e **Turma** do Censo Escolar 2025 (INEP) e:

- filtra escolas da região Sudeste, SP, nos municípios de Cajamar e Santana de Parnaíba, com `TP_DEPENDENCIA == 3` (rede municipal);
- une escolas e turmas por `NU_ANO_CENSO` e `CO_ENTIDADE`;
- geocodifica (ArcGIS) as escolas que estão sem latitude/longitude;
- converte a quantidade de turmas em **vagas** por etapa, usando estas capacidades por turma:
  - Creche: **10** alunos
  - Pré-escola: **20** alunos
  - Ensino Fundamental (1º ao 9º ano): **30** alunos
- calcula `QT_VAGAS_TOTAL` e salva `escolas_filtradas.csv`.

### `geocodificar_alunos_final.py`
Monta a consulta `Endereço, Número, CEP, Município, SP, Brasil`, geocodifica com ArcGIS (pausa de 1 s por aluno) e salva `alunos_geolocalizados_<municipio>.csv`. Endereços não encontrados ficam sem coordenadas.

### `calcular_distancias_final.py`
Carrega as escolas em funcionamento (`TP_SITUACAO_FUNCIONAMENTO == 1`) do município e consulta o serviço `table` do **OSRM** em blocos de 20 alunos, obtendo a distância de condução em km. Interrompe com erro caso exista aluno sem coordenadas. A função `salvar_matriz` grava a matriz em CSV (uso opcional).

### `Roteirizador_final.py`
Identifica a etapa de cada aluno a partir da coluna `escolaridade`, calcula as capacidades por escola, resolve o modelo e devolve a tabela com `CO_ENTIDADE`, `ESCOLA_DESTINO` e `DISTANCIA_KM`.

---

## Pré-requisitos

- Python 3.9+
- Servidor **OSRM** rodando localmente em `http://127.0.0.1:5000`, com dados do OpenStreetMap que cubram a região (perfil de carro)
- Acesso à internet (geocodificação via ArcGIS)
- Base `escolas_filtradas.csv` gerada por `limpeza_escolas_final.py`

### Dependências Python

```bash
pip install streamlit pandas numpy scipy requests geopy openpyxl
```

---

## Configuração do OSRM (mapa da região metropolitana de SP)

O cálculo de distâncias usa o [OSRM](https://project-osrm.org/) com dados do OpenStreetMap. O passo a passo abaixo usa Docker.

### 1. Baixar o mapa

O Geofabrik não tem um recorte só da região metropolitana de SP; o menor arquivo que a cobre é o da **região Sudeste do Brasil**:

```bash
mkdir osrm && cd osrm
curl -O https://download.geofabrik.de/south-america/brazil/sudeste-latest.osm.pbf
```

### 2. (Opcional) Recortar apenas a região de interesse

O arquivo do Sudeste é grande (SP, RJ, MG e ES) e o processamento consome bastante memória e tempo. Para trabalhar só com a região de Cajamar e Santana de Parnaíba, recorte com o [Osmium](https://osmcode.org/osmium-tool/):

```bash
# Instalação (Ubuntu/Debian): sudo apt install osmium-tool
osmium extract -b -47.3,-24.1,-46.2,-23.2 sudeste-latest.osm.pbf -o rmsp.osm.pbf
```

O parâmetro `-b` usa `lon_min,lat_min,lon_max,lat_max`. Essa caixa cobre a Grande São Paulo e os dois municípios; ajuste se necessário. Se pular esta etapa, use `sudeste-latest.osm.pbf` nos comandos abaixo.

### 3. Pré-processar o mapa

Execute na pasta onde está o `.osm.pbf` (os três comandos são necessários, nesta ordem):

```bash
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend osrm-extract -p /opt/car.lua /data/rmsp.osm.pbf
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend osrm-partition /data/rmsp.osrm
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend osrm-customize /data/rmsp.osrm
```

> No Windows (PowerShell), `${PWD}` funciona como acima; no CMD, use `%cd%`.

### 4. Subir o servidor na porta 5000

```bash
docker run -t -i -p 5000:5000 -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend osrm-routed --algorithm mld --max-table-size 1000 /data/rmsp.osrm
```

Importante: o parâmetro `--max-table-size 1000` é necessário. Por padrão o OSRM aceita no máximo **100 coordenadas** por requisição `table`, e o sistema envia, a cada chamada, 20 alunos mais todas as escolas do município. Sem esse ajuste, a requisição pode falhar com o erro `TooBig`.

### 5. Testar

```bash
curl "http://127.0.0.1:5000/route/v1/driving/-46.8754,-23.3549;-46.9170,-23.4500"
```

A resposta deve conter `"code":"Ok"`. Mantenha o servidor rodando enquanto usa o app.

---

## Configuração

Os caminhos das pastas estão fixos no código. Antes de executar, ajuste-os para o seu computador:

| Arquivo | Variável | O que é |
|---|---|---|
| `limpeza_escolas_final.py` | `caminho_escolas`, `caminho_turmas`, `caminho_saida` | Tabelas do Censo Escolar (entrada) e `escolas_filtradas.csv` (saída) |
| `geocodificar_alunos_final.py` | `Pasta_base` | Pasta onde o CSV dos alunos geocodificados é salvo |
| `calcular_distancias_final.py` | `PASTA_BASE`, `OSRM_URL` | Pasta da base de escolas e endereço do servidor OSRM |
| `Roteirizador_final.py` | `PASTA_BASE` | Pasta da base de escolas |

---

## Como usar

1. **Gerar a base de escolas** (apenas na primeira vez ou ao atualizar o censo):
   ```bash
   python limpeza_escolas_final.py
   ```
2. **Iniciar o servidor OSRM** na porta 5000.
3. **Abrir o app:**
   ```bash
   streamlit run app.py
   ```
4. No navegador:
   1. Selecione o município.
   2. Envie a planilha de alunos (`.xlsx`).
   3. Clique em **Iniciar alocação**.
   4. Consulte as métricas e baixe `resultado_alocacao.csv`.

### Formato da planilha de alunos

Arquivo Excel (`.xlsx`) com as colunas abaixo, exatamente com estes títulos:

| Nome | Endereço | Número | CEP | escolaridade |
|---|---|---|---|---|
| Maria Silva | Rua das Flores | 120 | 07750-000 | 3º ano |

Valores aceitos em `escolaridade`: um texto contendo **"Creche"**, **"Pré"** ou um número de **1 a 9** (ex.: `3º ano`, `ANO 5`).

---

## Resultados

O app exibe:

- distância média, mínima e máxima entre aluno e escola;
- percentual de alunos alocados na escola mais próxima;
- tabela completa da alocação.

O arquivo `resultado_alocacao.csv` é gerado com separador `;` e codificação `latin-1` (compatível com o Excel em português).

---

## Limitações

- A geocodificação faz uma consulta por aluno com pausa de 1 s, então planilhas grandes levam tempo.
- Alunos sem coordenadas válidas interrompem o processamento.
- A alocação falha se não houver vagas suficientes para alguma etapa; nesse caso, o app retorna erro de otimização.
- As vagas são estimadas a partir do número de turmas do Censo Escolar, com capacidade fixa por turma.
- A base de escolas contém apenas os municípios de Cajamar e Santana de Parnaíba.# Aloca-o-escolas-p-blicas
Distribuição de alunos em escolas utilizando SciPy e OSRM
