# Score de Potencial de Expansão — Expandir Franquias
## Data Analysis in Business · FAE 2026

---

## O que é este projeto

Modelo preditivo que avalia o potencial de sucesso de uma franquia
candidata com base em dados públicos de mercado (ABF, IBGE, SEBRAE).

**Pergunta central:** dado o perfil de uma franquia e da praça onde ela
quer se instalar, qual o potencial de sucesso?

---

## Como rodar — passo a passo

### 1. Instalar dependências
```bash
pip install playwright pandas openpyxl requests unidecode scikit-learn matplotlib seaborn joblib
playwright install chromium
```

### 2. Coletar dados do Portal ABF
```bash
python 1_coleta_portal_abf.py
```
- Abre o navegador e coleta ~300 franquias automaticamente
- Leva ~30 minutos (respeita delays entre requisições)
- Salva em `dados_brutos/franquias_portal_abf.csv`

### 3. Enriquecer com dados do IBGE e SEBRAE
```bash
python 2_enriquece_ibge.py
```
- Adiciona população, PIB per capita, IDH de cada cidade-sede
- Define a variável-alvo (sucesso binário)
- Salva em `dados_modelo/franquias_enriquecidas.csv`

### 4. Treinar o modelo
```bash
python 3_treina_modelo.py
```
- Compara Regressão Logística, Random Forest e Gradient Boosting
- Seleciona o melhor por ROC-AUC com validação cruzada
- Salva o modelo em `modelos/modelo_score_potencial.pkl`
- Gera gráficos em `graficos/`

---

## Estrutura de pastas gerada
```
dados_brutos/
  franquias_portal_abf.csv        ← dados brutos do scraper
dados_modelo/
  franquias_enriquecidas.csv      ← base com dados IBGE/SEBRAE
  franquias_com_score.csv         ← base final com scores
  franquias_com_score.xlsx        ← idem em Excel
modelos/
  modelo_score_potencial.pkl      ← modelo treinado
  encoder_segmento.pkl            ← encoders para novas predições
  encoder_regiao.pkl
  encoder_porte.pkl
  metricas_modelo.json            ← R², AUC, importância
  importancia_variaveis.csv
graficos/
  modelo_01_*.png                 ← distribuição do score
  modelo_02_*.png                 ← importância das variáveis
  modelo_03_*.png                 ← score por segmento
  modelo_04_*.png                 ← score por região
relatorio_modelo/
  resumo_modelo.md                ← texto pronto para o relatório
```

---

## Fontes de dados

| Fonte | Dados | Como é usada |
|-------|-------|--------------|
| ABF / Portal do Franchising | Nome, segmento, investimento, unidades, retorno | Variável-alvo + features |
| IBGE (API + embutido) | População, PIB per capita, IDH, região | Features demográficas |
| SEBRAE | Taxa de sobrevivência por segmento/porte | Feature de risco de mercado |

---

## Nota sobre viés de sobrevivência

Os dados da ABF incluem apenas franquias ativas e associadas — ou seja,
já há um filtro natural de sobrevivência. Para compensar isso:
1. A variável-alvo usa crescimento **relativo** ao segmento, não absoluto
2. A taxa de mortalidade do SEBRAE é incluída como feature
3. O relatório documenta explicitamente esta limitação metodológica
