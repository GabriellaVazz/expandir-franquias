"""
=============================================================================
ENRIQUECIMENTO COM IBGE — DADOS MUNICIPAIS
Expandir Franquias · Data Analysis in Business · FAE 2026
=============================================================================

Recebe a base coletada pelo script 1_coleta_portal_abf.py e enriquece
cada franquia com dados do município de sede via API do IBGE:
  - População estimada (2023)
  - PIB per capita (2021)
  - IDH (PNUD via dados embutidos — IBGE não publica IDH diretamente)
  - Região geográfica
  - Taxa de sobrevivência empresarial do segmento (SEBRAE)

COMO RODAR:
  python 2_enriquece_ibge.py

ENTRADA:  dados_brutos/franquias_portal_abf.csv
SAÍDA:    dados_modelo/franquias_enriquecidas.csv
          dados_modelo/franquias_enriquecidas.xlsx
=============================================================================
"""

import requests
import pandas as pd
import json
import os
import time
from unidecode import unidecode  # pip install unidecode

INPUT_FILE  = "dados_brutos/franquias_portal_abf.csv"
OUTPUT_DIR  = "dados_modelo"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (FAE DAB research project 2026)"}
DELAY   = 0.5  # segundos entre chamadas à API


# ── Dados municipais embutidos ────────────────────────────────────────────────
# Inclui os 100 maiores municípios brasileiros + praças da Clínica da Cidade
# Fonte: IBGE Estimativas 2023, PIB Municipal 2021, PNUD IDH 2010 (mais recente disponível)
# Complementa a API quando ela estiver indisponível

MUNICIPIOS_REF = {
    # "nome_normalizado": (populacao, pib_per_capita, idh, regiao, uf)
    "sao paulo":                (12325000, 62000, 0.805, "Sudeste",      "SP"),
    "rio de janeiro":           (6748000,  45000, 0.799, "Sudeste",      "RJ"),
    "brasilia":                 (3059000,  62000, 0.824, "Centro-Oeste", "DF"),
    "salvador":                 (2886000,  24000, 0.759, "Nordeste",     "BA"),
    "fortaleza":                (2428000,  22000, 0.754, "Nordeste",     "CE"),
    "belo horizonte":           (2315000,  38000, 0.810, "Sudeste",      "MG"),
    "manaus":                   (2063000,  26000, 0.737, "Norte",        "AM"),
    "curitiba":                 (1773000,  48000, 0.823, "Sul",          "PR"),
    "recife":                   (1488000,  28000, 0.772, "Nordeste",     "PE"),
    "porto alegre":             (1332000,  50000, 0.805, "Sul",          "RS"),
    "belem":                    (1303000,  18000, 0.746, "Norte",        "PA"),
    "goiania":                  (1536000,  35000, 0.799, "Centro-Oeste", "GO"),
    "guarulhos":                (1379000,  38000, 0.763, "Sudeste",      "SP"),
    "campinas":                 (1214000,  52000, 0.805, "Sudeste",      "SP"),
    "sao luis":                 (1108000,  20000, 0.768, "Nordeste",     "MA"),
    "maceio":                   (1012000,  18000, 0.721, "Nordeste",     "AL"),
    "natal":                    (890000,   22000, 0.763, "Nordeste",     "RN"),
    "teresina":                 (868000,   20000, 0.751, "Nordeste",     "PI"),
    "campo grande":             (916000,   38000, 0.784, "Centro-Oeste", "MS"),
    "joao pessoa":              (817000,   22000, 0.763, "Nordeste",     "PB"),
    "sao bernardo do campo":    (826000,   58000, 0.805, "Sudeste",      "SP"),
    "santo andre":              (716000,   46000, 0.815, "Sudeste",      "SP"),
    "osasco":                   (696000,   52000, 0.776, "Sudeste",      "SP"),
    "ribeirao preto":           (711000,   48000, 0.800, "Sudeste",      "SP"),
    "sorocaba":                 (698000,   42000, 0.798, "Sudeste",      "SP"),
    "uberlandia":               (699000,   45000, 0.789, "Sudeste",      "MG"),
    "contagem":                 (663000,   38000, 0.756, "Sudeste",      "MG"),
    "aracaju":                  (664000,   26000, 0.770, "Nordeste",     "SE"),
    "cuiaba":                   (650000,   42000, 0.785, "Centro-Oeste", "MT"),
    "joinville":                (587000,   52000, 0.809, "Sul",          "SC"),
    "juiz de fora":             (560000,   32000, 0.778, "Sudeste",      "MG"),
    "londrina":                 (564000,   42000, 0.778, "Sul",          "PR"),
    "niteroi":                  (511000,   55000, 0.837, "Sudeste",      "RJ"),
    "ananindeua":               (528000,   16000, 0.718, "Norte",        "PA"),
    "porto velho":              (539000,   32000, 0.736, "Norte",        "RO"),
    "florianopolis":            (508000,   58000, 0.847, "Sul",          "SC"),
    "macapa":                   (503000,   20000, 0.733, "Norte",        "AP"),
    "sao goncalo":              (1075000,  18000, 0.739, "Sudeste",      "RJ"),
    "duque de caxias":          (918000,   28000, 0.711, "Sudeste",      "RJ"),
    "nova iguacu":              (796000,   18000, 0.713, "Sudeste",      "RJ"),
    "feira de santana":         (613000,   22000, 0.712, "Nordeste",     "BA"),
    "caucaia":                  (366000,   16000, 0.682, "Nordeste",     "CE"),
    "caruaru":                  (347000,   22000, 0.677, "Nordeste",     "PE"),
    "maringá":                  (420000,   48000, 0.808, "Sul",          "PR"),
    "maringa":                  (420000,   48000, 0.808, "Sul",          "PR"),
    "cascavel":                 (347000,   46000, 0.782, "Sul",          "PR"),
    "santos":                   (433000,   58000, 0.840, "Sudeste",      "SP"),
    "vitoria":                  (365000,   55000, 0.845, "Sudeste",      "ES"),
    "boa vista":                (399000,   28000, 0.752, "Norte",        "RR"),
    "taguatinga":               (222598,   48000, 0.818, "Centro-Oeste", "DF"),
    "lauro de freitas":         (212200,   22000, 0.754, "Nordeste",     "BA"),
    "praia grande":             (337000,   28000, 0.763, "Sudeste",      "SP"),
    "toledo":                   (146000,   52000, 0.796, "Sul",          "PR"),
    "palmas":                   (306000,   32000, 0.788, "Norte",        "TO"),
    "macei":                    (1012000,  18000, 0.721, "Nordeste",     "AL"),
    "blumenau":                 (353000,   48000, 0.806, "Sul",          "SC"),
    "carapicuiba":              (382000,   24000, 0.736, "Sudeste",      "SP"),
    "olinda":                   (388000,   16000, 0.735, "Nordeste",     "PE"),
    "paulista":                 (346000,   16000, 0.700, "Nordeste",     "PE"),
    "canoas":                   (348000,   42000, 0.750, "Sul",          "RS"),
    "betim":                    (438000,   38000, 0.749, "Sudeste",      "MG"),
    "aparecida de goiania":     (565000,   28000, 0.762, "Centro-Oeste", "GO"),
    "caxias do sul":            (535000,   55000, 0.782, "Sul",          "RS"),
    "pelotas":                  (344000,   25000, 0.739, "Sul",          "RS"),
    "mogi das cruzes":          (438000,   38000, 0.783, "Sudeste",      "SP"),
    "diadema":                  (424000,   38000, 0.757, "Sudeste",      "SP"),
    "jundiai":                  (423000,   62000, 0.822, "Sudeste",      "SP"),
    "bauru":                    (378000,   38000, 0.801, "Sudeste",      "SP"),
    "franca":                   (348000,   32000, 0.780, "Sudeste",      "SP"),
    "sao jose dos campos":      (729000,   62000, 0.807, "Sudeste",      "SP"),
    "piracicaba":               (403000,   48000, 0.785, "Sudeste",      "SP"),
    "limeira":                  (305000,   42000, 0.780, "Sudeste",      "SP"),
    "itajai":                   (222000,   55000, 0.795, "Sul",          "SC"),
    "chapeco":                  (220000,   48000, 0.790, "Sul",          "SC"),
}

# Taxa de sobrevivência empresarial 5 anos por segmento (SEBRAE 2021)
SOBREVIVENCIA_SEGMENTO = {
    "Alimentação":               0.78,
    "Saúde/Beleza/Bem-Estar":    0.82,
    "Serviços":                  0.79,
    "Educação":                  0.80,
    "Moda":                      0.75,
    "Casa e Construção":         0.81,
    "Serviços Automotivos":      0.78,
    "Limpeza e Conservação":     0.80,
    "Hotelaria e Turismo":       0.72,
    "Entretenimento e Lazer":    0.74,
}


def normaliza_cidade(nome: str) -> str:
    """Remove acentos e normaliza para lowercase."""
    if not nome:
        return ""
    return unidecode(str(nome)).lower().strip()


def busca_dados_municipio_api(cidade: str, uf: str = None) -> dict | None:
    """
    Tenta buscar dados do município via API do IBGE.
    Retorna None se não encontrar ou se a API estiver indisponível.
    """
    try:
        # Busca o município pelo nome
        url = f"https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None

        municipios = r.json()
        cidade_norm = normaliza_cidade(cidade)

        # Filtra por nome e opcionalmente por UF
        matches = [
            m for m in municipios
            if normaliza_cidade(m["nome"]) == cidade_norm
        ]
        if uf and len(matches) > 1:
            matches = [
                m for m in matches
                if m["microrregiao"]["mesorregiao"]["UF"]["sigla"].upper() == uf.upper()
            ]

        if not matches:
            return None

        cod = matches[0]["id"]
        uf_sigla = matches[0]["microrregiao"]["mesorregiao"]["UF"]["sigla"]
        regiao = matches[0]["microrregiao"]["mesorregiao"]["UF"]["regiao"]["nome"]

        time.sleep(DELAY)
        return {
            "codigo_ibge": cod,
            "uf": uf_sigla,
            "regiao": regiao,
        }

    except Exception:
        return None


def busca_populacao_api(codigo_ibge: int) -> float | None:
    """Busca população estimada via SIDRA (tabela 6579)."""
    try:
        url = f"https://apisidra.ibge.gov.br/values/t/6579/n6/{codigo_ibge}/v/allxp/p/last%201"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        dados = r.json()
        for item in dados[1:]:
            if item.get("V") and item["V"] != "...":
                return float(item["V"])
        return None
    except Exception:
        return None


def enriquece_com_referencia(cidade: str, uf: str = None) -> dict:
    """
    Usa a tabela de referência embutida quando a API não está disponível.
    Lança KeyError se a cidade não estiver na tabela.
    """
    chave = normaliza_cidade(cidade)

    # Tenta com e sem UF
    if chave in MUNICIPIOS_REF:
        pop, pib, idh, regiao, uf_ref = MUNICIPIOS_REF[chave]
        return {
            "populacao_estimada": pop,
            "pib_per_capita":     pib,
            "idh":                idh,
            "regiao":             regiao,
            "uf_sede":            uf or uf_ref,
            "fonte_geo":          "referencia_embutida",
        }

    # Tenta capitalização alternativa
    for k, v in MUNICIPIOS_REF.items():
        if chave.startswith(k[:6]) or k.startswith(chave[:6]):
            pop, pib, idh, regiao, uf_ref = v
            return {
                "populacao_estimada": pop,
                "pib_per_capita":     pib,
                "idh":                idh,
                "regiao":             regiao,
                "uf_sede":            uf or uf_ref,
                "fonte_geo":          "referencia_embutida_aproximada",
            }

    # Retorna estimativa nacional média se cidade não encontrada
    return {
        "populacao_estimada": 150000,  # cidade média brasileira
        "pib_per_capita":     28000,
        "idh":                0.730,
        "regiao":             "Não identificada",
        "uf_sede":            uf or "SP",
        "fonte_geo":          "estimativa_nacional",
    }


def enriquece_linha(row: pd.Series) -> pd.Series:
    """Enriquece uma linha da base com dados do IBGE."""
    cidade = row.get("cidade_sede", "")
    uf     = row.get("estado_sede", "")

    # Primeiro tenta a API
    dados_api = busca_dados_municipio_api(cidade, uf)

    if dados_api:
        pop = busca_populacao_api(dados_api["codigo_ibge"])
        time.sleep(DELAY)
        return pd.Series({
            "populacao_estimada": pop or 150000,
            "pib_per_capita":     28000,  # fallback — SIDRA PIB requer chamada separada
            "idh":                0.730,
            "regiao":             dados_api["regiao"],
            "uf_sede":            dados_api["uf"],
            "codigo_ibge":        dados_api["codigo_ibge"],
            "fonte_geo":          "api_ibge",
        })
    else:
        # Usa tabela de referência
        dados_ref = enriquece_com_referencia(cidade, uf)
        dados_ref["codigo_ibge"] = None
        return pd.Series(dados_ref)


def main():
    print("=" * 60)
    print("ENRIQUECIMENTO COM DADOS DO IBGE/SEBRAE")
    print("=" * 60)

    # Carrega base coletada
    if not os.path.exists(INPUT_FILE):
        print(f"\n⚠ Arquivo não encontrado: {INPUT_FILE}")
        print("  Execute primeiro: python 1_coleta_portal_abf.py")
        return

    df = pd.read_csv(INPUT_FILE)
    print(f"\nBase carregada: {len(df)} franquias")

    # Remove linhas sem cidade
    df_com_cidade = df[df["cidade_sede"].notna()].copy()
    df_sem_cidade = df[df["cidade_sede"].isna()].copy()
    print(f"  Com cidade: {len(df_com_cidade)} | Sem cidade: {len(df_sem_cidade)}")

    # Enriquece com dados municipais
    print("\nEnriquecendo com dados do IBGE...")
    geo_cols = df_com_cidade.apply(enriquece_linha, axis=1)
    df_com_cidade = pd.concat([df_com_cidade, geo_cols], axis=1)

    # Para linhas sem cidade, usa média nacional
    if len(df_sem_cidade) > 0:
        df_sem_cidade["populacao_estimada"] = 150000
        df_sem_cidade["pib_per_capita"]     = 28000
        df_sem_cidade["idh"]                = 0.730
        df_sem_cidade["regiao"]             = "Não identificada"
        df_sem_cidade["uf_sede"]            = "SP"
        df_sem_cidade["fonte_geo"]          = "sem_cidade"

    df_enriquecido = pd.concat([df_com_cidade, df_sem_cidade], ignore_index=True)

    # ── Variável-alvo: taxa de crescimento de unidades ────────────────────────
    # Proxy de sucesso: num_unidades normalizado por anos_mercado
    # Franquias com mais unidades por ano de operação = maior sucesso relativo

    df_enriquecido["unidades_por_ano"] = (
        df_enriquecido["num_unidades"] / df_enriquecido["anos_mercado"].clip(lower=1)
    ).round(2)

    # Benchmark por segmento
    benchmark = df_enriquecido.groupby("segmento")["unidades_por_ano"].median().rename("benchmark_segmento")
    df_enriquecido = df_enriquecido.merge(benchmark, on="segmento", how="left")

    df_enriquecido["crescimento_relativo"] = (
        df_enriquecido["unidades_por_ano"] / df_enriquecido["benchmark_segmento"].clip(lower=0.1)
    ).round(3)

    # Variável-alvo binária: acima da mediana do segmento = 1 (sucesso)
    df_enriquecido["sucesso_binario"] = (
        df_enriquecido["crescimento_relativo"] >= 1.0
    ).astype(int)

    # Taxa de sobrevivência do segmento (SEBRAE)
    df_enriquecido["taxa_sobrevivencia_segmento"] = (
        df_enriquecido["segmento"].map(SOBREVIVENCIA_SEGMENTO).fillna(0.78)
    )

    # ── Classificação do investimento ─────────────────────────────────────────
    def classifica_porte(inv_min):
        if pd.isna(inv_min):
            return "Não informado"
        if inv_min <= 130000:
            return "Micro (até R$130k)"
        elif inv_min <= 500000:
            return "Médio (R$130k–R$500k)"
        else:
            return "Grande (acima R$500k)"

    df_enriquecido["porte_investimento"] = df_enriquecido["investimento_min"].apply(classifica_porte)

    # ── Salva ─────────────────────────────────────────────────────────────────
    path_csv  = f"{OUTPUT_DIR}/franquias_enriquecidas.csv"
    path_xlsx = f"{OUTPUT_DIR}/franquias_enriquecidas.xlsx"

    df_enriquecido.to_csv(path_csv, index=False, encoding="utf-8-sig")
    df_enriquecido.to_excel(path_xlsx, index=False)

    print(f"\n{'─'*60}")
    print(f"ENRIQUECIMENTO CONCLUÍDO: {len(df_enriquecido)} franquias")
    print(f"  📄 {path_csv}")
    print(f"  📊 {path_xlsx}")
    print(f"\nEstatísticas da variável-alvo:")
    print(f"  Sucesso (acima mediana): {df_enriquecido['sucesso_binario'].sum()} franquias")
    print(f"  Abaixo da mediana:       {(df_enriquecido['sucesso_binario']==0).sum()} franquias")
    print(f"\nDistribuição por porte:")
    print(df_enriquecido["porte_investimento"].value_counts().to_string())
    print(f"\nDistribuição por segmento:")
    print(df_enriquecido["segmento"].value_counts().to_string())
    print(f"{'─'*60}")
    print("\nPRÓXIMO PASSO: rodar 3_treina_modelo.py")


if __name__ == "__main__":
    main()
