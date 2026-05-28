"""
=============================================================================
MODELO DE SCORE DE POTENCIAL DE EXPANSÃO — TREINAMENTO
Expandir Franquias · Data Analysis in Business · FAE 2026
=============================================================================

Treina o modelo preditivo de score de potencial de expansão de franquias
usando a base enriquecida com dados reais da ABF + IBGE + SEBRAE.

COMO RODAR:
  python 3_treina_modelo.py

ENTRADA:  dados_modelo/franquias_enriquecidas.csv
SAÍDA:
  modelos/modelo_score_potencial.pkl      → modelo treinado
  modelos/metricas_modelo.json            → métricas de avaliação
  modelos/importancia_variaveis.csv       → pesos do modelo
  graficos/modelo_01_real_vs_predito.png
  graficos/modelo_02_importancia.png
  graficos/modelo_03_score_por_segmento.png
  graficos/modelo_04_score_por_regiao.png
  relatorio_modelo/resumo_modelo.md       → texto pronto para o relatório
=============================================================================
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import json, os, warnings
warnings.filterwarnings("ignore")

from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    classification_report, roc_auc_score, confusion_matrix,
    mean_squared_error, r2_score
)
from sklearn.pipeline import Pipeline
import joblib

# ── Configuração ──────────────────────────────────────────────────────────────
INPUT_FILE      = "dados_modelo/franquias_enriquecidas.csv"
OUTPUT_MODELOS  = "modelos"
OUTPUT_GRAFICOS = "graficos"
OUTPUT_RELATORIO= "relatorio_modelo"

for d in [OUTPUT_MODELOS, OUTPUT_GRAFICOS, OUTPUT_RELATORIO]:
    os.makedirs(d, exist_ok=True)

PALETTE = {
    "teal":   "#0E8A7A", "navy":   "#0D1B2A",
    "ok":     "#3B6D11", "warn":   "#BA7517",
    "danger": "#A32D2D", "gray":   "#64748B",
    "bg":     "#F4F7F9", "mid":    "#1B3A5C",
}
plt.rcParams.update({"font.family": "DejaVu Sans", "figure.facecolor": PALETTE["bg"]})


# ── Carrega e prepara os dados ────────────────────────────────────────────────
print("=" * 60)
print("MODELO DE SCORE DE POTENCIAL DE EXPANSÃO")
print("=" * 60)

if not os.path.exists(INPUT_FILE):
    print(f"\n⚠ Arquivo não encontrado: {INPUT_FILE}")
    print("  Execute primeiro: python 2_enriquece_ibge.py")
    exit(1)

df = pd.read_csv(INPUT_FILE)
print(f"\nBase carregada: {len(df)} franquias, {len(df.columns)} variáveis\n")

# Remove linhas sem variável-alvo
df = df.dropna(subset=["sucesso_binario", "investimento_min"])
print(f"Após limpeza: {len(df)} franquias com dados suficientes")


# ── Feature Engineering ───────────────────────────────────────────────────────
# Encode categóricas
le_seg = LabelEncoder()
le_reg = LabelEncoder()
le_por = LabelEncoder()

df["segmento_cod"]  = le_seg.fit_transform(df["segmento"].fillna("Outros"))
df["regiao_cod"]    = le_reg.fit_transform(df["regiao"].fillna("Não identificada"))
df["porte_cod"]     = le_por.fit_transform(df["porte_investimento"].fillna("Não informado"))

# Normaliza população (log)
df["pop_log"] = np.log1p(df["populacao_estimada"].fillna(150000))
df["pib_norm"] = df["pib_per_capita"].fillna(28000) / 100000

# Normaliza investimento
df["inv_log"] = np.log1p(df["investimento_min"].fillna(100000))

# Prazo de retorno normalizado (menor = melhor)
df["retorno_norm"] = 1 / (df["prazo_retorno_meses"].fillna(24).clip(lower=1))

# Features finais para o modelo
FEATURES = [
    # Dados demográficos (IBGE)
    "pop_log",
    "pib_norm",
    "idh",
    "regiao_cod",
    # Dados da franquia (ABF)
    "inv_log",
    "porte_cod",
    "segmento_cod",
    "anos_mercado",
    "num_unidades",
    "retorno_norm",
    # Dados de mercado (SEBRAE)
    "taxa_sobrevivencia_segmento",
]

# Remove features com muitos nulos
FEATURES = [f for f in FEATURES if df[f].notna().mean() > 0.5]
print(f"Features selecionadas: {len(FEATURES)}")
for f in FEATURES:
    cobertura = df[f].notna().mean()
    print(f"  {f:<35} cobertura: {cobertura:.1%}")

X = df[FEATURES].fillna(df[FEATURES].median())
y = df["sucesso_binario"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y
)
print(f"\nTreino: {len(X_train)} | Teste: {len(X_test)}")
print(f"Taxa de sucesso na base: {y.mean():.1%}\n")


# ── Treina e compara modelos ──────────────────────────────────────────────────
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

modelos = {
    "Regressão Logística": Pipeline([
        ("scaler", StandardScaler()),
        ("model",  LogisticRegression(max_iter=1000, random_state=42))
    ]),
    "Random Forest": Pipeline([
        ("scaler", StandardScaler()),
        ("model",  RandomForestClassifier(n_estimators=100, random_state=42))
    ]),
    "Gradient Boosting": Pipeline([
        ("scaler", StandardScaler()),
        ("model",  GradientBoostingClassifier(
            n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42
        ))
    ]),
}

resultados = {}
print("─" * 60)
print(f"{'Modelo':<30} {'ROC-AUC':>8} {'Acc':>7} {'AUC-CV':>9}")
print("─" * 60)

for nome, pipeline in modelos.items():
    pipeline.fit(X_train, y_train)
    y_pred  = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    auc   = roc_auc_score(y_test, y_proba)
    acc   = (y_pred == y_test).mean()
    auc_cv = cross_val_score(pipeline, X, y, cv=cv, scoring="roc_auc").mean()

    resultados[nome] = {
        "roc_auc": round(auc, 4), "accuracy": round(acc, 4),
        "roc_auc_cv": round(auc_cv, 4),
        "classification_report": classification_report(y_test, y_pred, output_dict=True),
    }
    print(f"{nome:<30} {auc:>8.4f} {acc:>7.4f} {auc_cv:>9.4f}")

print("─" * 60)

# Melhor modelo por AUC-CV
melhor = max(resultados, key=lambda k: resultados[k]["roc_auc_cv"])
pipeline_final = modelos[melhor]
print(f"\n✓ Melhor modelo: {melhor}")
print(f"  ROC-AUC CV: {resultados[melhor]['roc_auc_cv']:.4f}")


# ── Score de potencial (0–100) ────────────────────────────────────────────────
# Converte a probabilidade do melhor modelo em score 0-100
df["score_potencial"] = (
    pipeline_final.predict_proba(X.fillna(X.median()))[:, 1] * 100
).round(1)

df["classificacao_score"] = pd.cut(
    df["score_potencial"],
    bins=[0, 40, 60, 80, 100],
    labels=["Baixo", "Moderado", "Alto", "Muito Alto"]
)

print(f"\nDistribuição do Score de Potencial:")
print(df["classificacao_score"].value_counts().sort_index().to_string())


# ── Salva modelo e métricas ───────────────────────────────────────────────────
joblib.dump(pipeline_final, f"{OUTPUT_MODELOS}/modelo_score_potencial.pkl")
joblib.dump(le_seg, f"{OUTPUT_MODELOS}/encoder_segmento.pkl")
joblib.dump(le_reg, f"{OUTPUT_MODELOS}/encoder_regiao.pkl")
joblib.dump(le_por, f"{OUTPUT_MODELOS}/encoder_porte.pkl")

metricas = {
    "modelo_selecionado":  melhor,
    "features_usadas":     FEATURES,
    "n_franquias_treino":  len(X_train),
    "n_franquias_teste":   len(X_test),
    "resultados":          resultados,
    "score_medio_base":    round(df["score_potencial"].mean(), 2),
    "score_mediano_base":  round(df["score_potencial"].median(), 2),
}
with open(f"{OUTPUT_MODELOS}/metricas_modelo.json", "w", encoding="utf-8") as f:
    json.dump(metricas, f, ensure_ascii=False, indent=2)


# ── Importância das variáveis ─────────────────────────────────────────────────
modelo_interno = pipeline_final.named_steps["model"]
if hasattr(modelo_interno, "feature_importances_"):
    importancias = modelo_interno.feature_importances_
elif hasattr(modelo_interno, "coef_"):
    importancias = np.abs(modelo_interno.coef_[0])
else:
    importancias = np.ones(len(FEATURES))

df_imp = pd.DataFrame({
    "variavel": FEATURES,
    "importancia": importancias,
}).sort_values("importancia", ascending=False)

# Nomes amigáveis para o relatório
nomes_amigaveis = {
    "pop_log":                    "População do município (log)",
    "pib_norm":                   "PIB per capita",
    "idh":                        "IDH do município",
    "regiao_cod":                 "Região geográfica",
    "inv_log":                    "Investimento inicial (log)",
    "porte_cod":                  "Porte da franquia",
    "segmento_cod":               "Segmento de atuação",
    "anos_mercado":               "Tempo de mercado (anos)",
    "num_unidades":               "Número de unidades",
    "retorno_norm":               "Velocidade de retorno",
    "taxa_sobrevivencia_segmento":"Taxa de sobrevivência do segmento (SEBRAE)",
}
df_imp["variavel_amigavel"] = df_imp["variavel"].map(nomes_amigaveis).fillna(df_imp["variavel"])
df_imp.to_csv(f"{OUTPUT_MODELOS}/importancia_variaveis.csv", index=False)


# ── GRÁFICOS ──────────────────────────────────────────────────────────────────

def g1_importancia():
    top = df_imp.head(10).sort_values("importancia")
    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.barh(top["variavel_amigavel"], top["importancia"],
            color=PALETTE["teal"], edgecolor="white", height=0.65)
    ax.set_title("Importância das variáveis — top 10", fontweight="bold", pad=10)
    ax.set_xlabel("Importância relativa")
    ax.set_facecolor("white")
    for i, (_, row) in enumerate(top.iterrows()):
        ax.text(row["importancia"] + 0.001, i,
                f"{row['importancia']:.3f}", va="center", fontsize=8.5)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_GRAFICOS}/modelo_02_importancia.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ modelo_02_importancia.png")


def g2_score_por_segmento():
    med = df.groupby("segmento")["score_potencial"].agg(["mean","std","count"]).reset_index()
    med = med.sort_values("mean", ascending=True)

    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.barh(med["segmento"], med["mean"],
            xerr=med["std"], color=PALETTE["teal"],
            error_kw={"ecolor": PALETTE["gray"], "capsize": 4},
            edgecolor="white", height=0.6)
    for _, row in med.iterrows():
        idx = list(med["segmento"]).index(row["segmento"])
        ax.text(row["mean"] + 0.5, idx,
                f"{row['mean']:.1f}  (n={int(row['count'])})",
                va="center", fontsize=8.5)
    ax.set_title("Score médio de potencial por segmento", fontweight="bold", pad=10)
    ax.set_xlabel("Score médio (± desvio padrão)")
    ax.set_xlim(0, 115)
    ax.set_facecolor("white")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_GRAFICOS}/modelo_03_score_por_segmento.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ modelo_03_score_por_segmento.png")


def g3_score_por_regiao():
    med = df.groupby("regiao")["score_potencial"].mean().reset_index()
    med = med[med["regiao"] != "Não identificada"].sort_values("score_potencial", ascending=False)

    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor(PALETTE["bg"])
    cores = [PALETTE["teal"], PALETTE["mid"], PALETTE["ok"], PALETTE["warn"], PALETTE["gray"]]
    ax.bar(med["regiao"], med["score_potencial"],
           color=cores[:len(med)], edgecolor="white")
    for i, row in med.iterrows():
        idx = list(med["regiao"]).index(row["regiao"])
        ax.text(idx, row["score_potencial"] + 0.5,
                f"{row['score_potencial']:.1f}", ha="center", fontsize=9)
    ax.set_title("Score médio por região geográfica", fontweight="bold", pad=10)
    ax.set_ylabel("Score médio")
    ax.set_ylim(0, 100)
    ax.set_facecolor("white")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_GRAFICOS}/modelo_04_score_por_regiao.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ modelo_04_score_por_regiao.png")


def g4_distribuicao_score():
    fig, ax = plt.subplots(figsize=(9, 4.5))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.hist(df["score_potencial"], bins=20, color=PALETTE["teal"],
            edgecolor="white", alpha=0.85)
    ax.axvline(df["score_potencial"].mean(), color=PALETTE["navy"],
               linestyle="--", linewidth=1.5,
               label=f"Média: {df['score_potencial'].mean():.1f}")
    ax.axvline(60, color=PALETTE["ok"], linestyle=":", linewidth=1.2, label="Limiar alto (60)")
    ax.axvline(40, color=PALETTE["warn"], linestyle=":", linewidth=1.2, label="Limiar moderado (40)")
    ax.set_title("Distribuição do Score de Potencial de Expansão", fontweight="bold", pad=10)
    ax.set_xlabel("Score (0–100)")
    ax.set_ylabel("Frequência")
    ax.legend(fontsize=9)
    ax.set_facecolor("white")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_GRAFICOS}/modelo_01_real_vs_predito.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ modelo_01_distribuicao_score.png")


print("\nGerando visualizações...")
g1_importancia()
g2_score_por_segmento()
g3_score_por_regiao()
g4_distribuicao_score()


# ── Resumo para o relatório ───────────────────────────────────────────────────
top5_vars = df_imp.head(5)["variavel_amigavel"].tolist()
resumo = f"""# Resumo do Modelo — Score de Potencial de Expansão

## Modelo selecionado
**{melhor}**

## Métricas de avaliação
- ROC-AUC (teste): {resultados[melhor]['roc_auc']:.4f}
- Acurácia (teste): {resultados[melhor]['accuracy']:.4f}
- ROC-AUC (validação cruzada 5-fold): {resultados[melhor]['roc_auc_cv']:.4f}

## Base de dados
- Franquias coletadas: {len(df)} (Portal do Franchising / ABF)
- Features utilizadas: {len(FEATURES)}
- Variável-alvo: sucesso binário (acima da mediana do segmento = 1)

## Variáveis mais importantes
{chr(10).join([f"{i+1}. {v}" for i, v in enumerate(top5_vars)])}

## Distribuição do score
- Média: {df['score_potencial'].mean():.1f}
- Mediana: {df['score_potencial'].median():.1f}
- Score Muito Alto (>80): {(df['score_potencial'] > 80).sum()} franquias
- Score Alto (60–80): {((df['score_potencial'] >= 60) & (df['score_potencial'] <= 80)).sum()} franquias
- Score Moderado (40–60): {((df['score_potencial'] >= 40) & (df['score_potencial'] < 60)).sum()} franquias
- Score Baixo (<40): {(df['score_potencial'] < 40).sum()} franquias

## Nota sobre a variável-alvo
A variável-alvo foi definida como sucesso binário: uma franquia é considerada
bem-sucedida se seu número de unidades por ano de operação está acima da mediana
do seu segmento. Esta definição usa crescimento relativo como proxy de sucesso,
compensando parcialmente o viés de sobrevivência dos dados públicos da ABF.
Os dados de mortalidade empresarial do SEBRAE foram incorporados como feature
adicional para calibrar o modelo em relação às taxas históricas de encerramento
por segmento.
"""

with open(f"{OUTPUT_RELATORIO}/resumo_modelo.md", "w", encoding="utf-8") as f:
    f.write(resumo)

# Salva base final com scores
df.to_csv(f"dados_modelo/franquias_com_score.csv", index=False, encoding="utf-8-sig")
df.to_excel(f"dados_modelo/franquias_com_score.xlsx", index=False)

print(f"\n{'─'*60}")
print("TREINAMENTO CONCLUÍDO")
print(f"  🤖 {OUTPUT_MODELOS}/modelo_score_potencial.pkl")
print(f"  📊 dados_modelo/franquias_com_score.xlsx")
print(f"  📝 {OUTPUT_RELATORIO}/resumo_modelo.md")
print(f"\nPRÓXIMOS PASSOS:")
print("  • Abrir franquias_com_score.xlsx e analisar os scores")
print("  • Usar modelo_score_potencial.pkl na interface de consulta")
print("  • Testar com praças específicas de interesse da Expandir")
print(f"{'─'*60}\n")
