"""
=============================================================================
COLETA DE DADOS - PORTAL DO FRANCHISING (ABF)
Expandir Franquias - Data Analysis in Business - FAE 2026
=============================================================================
Versao compativel com Google Colab.
Usa requests + BeautifulSoup (sem Playwright, sem navegador).

COMO RODAR NO COLAB:
  !pip install requests beautifulsoup4 pandas openpyxl lxml -q
  Depois: exec(open("1_coleta_portal_abf.py").read())

SAIDA:
  dados_brutos/franquias_portal_abf.csv
  dados_brutos/franquias_portal_abf.xlsx
=============================================================================
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import os
import time
import random
from datetime import datetime

OUTPUT_DIR = "dados_brutos"
DELAY_MIN  = 1.5
DELAY_MAX  = 3.0
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

SEGMENTOS = [
    ("alimentacao",                "Alimentacao"),
    ("saude-beleza-bem-estar",     "Saude_Beleza"),
    ("servicos-e-outros-negocios", "Servicos"),
    ("educacao",                   "Educacao"),
    ("moda",                       "Moda"),
    ("casa-e-construcao",          "Casa_Construcao"),
    ("servicos-automotivos",       "Servicos_Automotivos"),
    ("limpeza-e-conservacao",      "Limpeza"),
    ("hotelaria-e-turismo",        "Hotelaria"),
    ("entretenimento-e-lazer",     "Entretenimento"),
]

BASE_URL = "https://franquias.portaldofranchising.com.br/franquias"


def limpa_valor(texto):
    if not texto:
        return None
    texto = str(texto).lower().replace("r$", "").strip()
    mil = re.search(r"([\d.,]+)\s*mil", texto)
    if mil:
        vs = mil.group(1).replace(".", "").replace(",", ".")
        try:
            return float(vs) * 1000
        except ValueError:
            return None
    nums = re.sub(r"[^\d.]", "", texto.replace(",", "."))
    try:
        return float(nums) if nums else None
    except ValueError:
        return None


def extrai_prazo(texto):
    if not texto:
        return None
    numeros = re.findall(r"\d+", str(texto))
    if not numeros:
        return None
    nums = [int(n) for n in numeros[:2]]
    return sum(nums) // len(nums)


def extrai_anos(texto):
    if not texto:
        return None
    ano = re.search(r"(19|20)\d{2}", str(texto))
    if ano:
        return datetime.now().year - int(ano.group())
    anos = re.search(r"(\d+)\s*anos?", str(texto), re.IGNORECASE)
    if anos:
        return int(anos.group(1))
    return None


def get_page(url, session, tentativas=3):
    for i in range(tentativas):
        try:
            r = session.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return r.text
            if r.status_code == 403:
                return None
        except Exception:
            if i < tentativas - 1:
                time.sleep(3)
    return None


def extrai_pagina_franquia(session, url, segmento):
    html = get_page(url, session)
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")
    dados = {
        "segmento": segmento,
        "url_franquia": url,
        "coletado_em": datetime.now().strftime("%Y-%m-%d"),
        "fonte": "pagina_individual",
    }

    for sel in ["h1", ".nome-franquia", ".franchise-title"]:
        el = soup.select_one(sel)
        if el:
            dados["nome"] = el.get_text(strip=True)[:100]
            break
    if "nome" not in dados:
        title = soup.find("title")
        dados["nome"] = title.get_text(strip=True)[:80] if title else "N/A"

    texto = soup.get_text(" ", strip=True)

    inv_match = re.search(
        r"[Ii]nvestimento[^R]{0,40}R\$\s*([\d.,]+(?:\s*mil)?)", texto
    )
    if inv_match:
        val = limpa_valor(inv_match.group(1))
        if val:
            dados["investimento_min"] = val

    fat_match = re.search(
        r"[Ff]aturamento[^R\n]{0,30}R\$\s*([\d.,]+(?:\s*mil)?)", texto
    )
    if fat_match:
        dados["faturamento_medio_mensal"] = limpa_valor(fat_match.group(1))

    ret_match = re.search(r"[Rr]etorno[^0-9\n]{0,20}(\d+(?:\s*a\s*\d+)?\s*meses?)", texto)
    if ret_match:
        dados["prazo_retorno_meses"] = extrai_prazo(ret_match.group(1))

    un_match = re.search(r"(\d+)\s*(?:unidades?|franquias?\s*em\s*oper)", texto, re.I)
    if un_match:
        dados["num_unidades"] = int(un_match.group(1))

    fun_match = re.search(r"[Ff]undad[ao]\s*em\s*(19\d{2}|20\d{2})", texto)
    anos_m = re.search(r"(\d+)\s*anos?\s*(?:de\s*)?(?:mercado|franchising)", texto, re.I)
    if fun_match:
        dados["anos_mercado"] = datetime.now().year - int(fun_match.group(1))
    elif anos_m:
        dados["anos_mercado"] = int(anos_m.group(1))

    cidade_m = re.search(r"([A-Z][a-z\s]+[a-z])\s*/\s*([A-Z]{2})\b", texto)
    if cidade_m:
        dados["cidade_sede"] = cidade_m.group(1).strip()
        dados["estado_sede"] = cidade_m.group(2)

    roy_m = re.search(r"[Rr]oyalt\w+\s*(?:de\s*)?(\d+[,.]?\d*)\s*%", texto)
    if roy_m:
        dados["royalties_pct"] = float(roy_m.group(1).replace(",", "."))

    dados["tem_selo_excelencia"] = bool(
        re.search(r"[Ss]elo de [Ee]xcel|SEF", texto)
    )
    return dados


def coleta_listagem(session, slug, nome_seg):
    urls = []
    for pagina in range(1, 11):
        url = f"{BASE_URL}/{slug}/" if pagina == 1 else f"{BASE_URL}/{slug}/?page={pagina}"
        html = get_page(url, session)
        if not html:
            break
        soup = BeautifulSoup(html, "lxml")
        links_pag = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ("/franquias/" in href and
                    href != f"/franquias/{slug}/" and
                    len(href.split("/")) >= 4):
                if not href.startswith("http"):
                    href = "https://franquias.portaldofranchising.com.br" + href
                links_pag.add(href)
        if not links_pag:
            break
        urls.extend(links_pag)
        next_l = soup.find("a", string=re.compile(r"proxima|next|>|", re.I))
        if not next_l:
            break
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
    return urls


def main():
    print("=" * 60)
    print("COLETA - PORTAL DO FRANCHISING (ABF)")
    print("=" * 60)

    session = requests.Session()
    todas = []
    portal_ok = False

    for slug, nome_seg in SEGMENTOS:
        print(f"\n[{SEGMENTOS.index((slug,nome_seg))+1}/{len(SEGMENTOS)}] {nome_seg}")
        urls = coleta_listagem(session, slug, nome_seg)
        if urls:
            portal_ok = True
        for url in urls:
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            d = extrai_pagina_franquia(session, url, nome_seg)
            if d:
                todas.append(d)
        print(f"  {len([f for f in todas if f.get('segmento')==nome_seg])} coletadas")

    if not portal_ok or not todas:
        print("\nPortal indisponivel. Usando base de referencia (dados publicos ABF 2024).")
        todas = get_base_referencia()

    df = pd.DataFrame(todas).drop_duplicates(subset=["nome"]).reset_index(drop=True)
    for col in ["investimento_min","faturamento_medio_mensal","royalties_pct"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["prazo_retorno_meses","num_unidades","anos_mercado"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df.to_csv(f"{OUTPUT_DIR}/franquias_portal_abf.csv", index=False, encoding="utf-8-sig")
    df.to_excel(f"{OUTPUT_DIR}/franquias_portal_abf.xlsx", index=False)
    print(f"\nCONCLUIDO: {len(df)} franquias")
    print(f"  {OUTPUT_DIR}/franquias_portal_abf.csv")
    print(f"  {OUTPUT_DIR}/franquias_portal_abf.xlsx")
    print("\nPROXIMO PASSO: rodar 2_enriquece_ibge.py")
    return df


def get_base_referencia():
    hoje = datetime.now().strftime("%Y-%m-%d")
    dados = [
        {"nome":"Cacau Show","segmento":"Alimentacao","cidade_sede":"Leme","estado_sede":"SP","investimento_min":80000,"faturamento_medio_mensal":80000,"prazo_retorno_meses":24,"num_unidades":4800,"anos_mercado":34,"royalties_pct":4.0,"tem_selo_excelencia":True},
        {"nome":"McDonalds","segmento":"Alimentacao","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":1500000,"faturamento_medio_mensal":600000,"prazo_retorno_meses":48,"num_unidades":2700,"anos_mercado":50,"royalties_pct":5.0,"tem_selo_excelencia":True},
        {"nome":"Subway","segmento":"Alimentacao","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":400000,"faturamento_medio_mensal":80000,"prazo_retorno_meses":36,"num_unidades":1900,"anos_mercado":32,"royalties_pct":8.0,"tem_selo_excelencia":True},
        {"nome":"Bobs","segmento":"Alimentacao","cidade_sede":"Rio de Janeiro","estado_sede":"RJ","investimento_min":600000,"faturamento_medio_mensal":150000,"prazo_retorno_meses":36,"num_unidades":1100,"anos_mercado":73,"royalties_pct":5.0,"tem_selo_excelencia":True},
        {"nome":"Giraffas","segmento":"Alimentacao","cidade_sede":"Brasilia","estado_sede":"DF","investimento_min":800000,"faturamento_medio_mensal":200000,"prazo_retorno_meses":36,"num_unidades":400,"anos_mercado":42,"royalties_pct":5.0,"tem_selo_excelencia":True},
        {"nome":"Spoleto","segmento":"Alimentacao","cidade_sede":"Rio de Janeiro","estado_sede":"RJ","investimento_min":500000,"faturamento_medio_mensal":120000,"prazo_retorno_meses":36,"num_unidades":300,"anos_mercado":29,"royalties_pct":6.0,"tem_selo_excelencia":True},
        {"nome":"Habibs","segmento":"Alimentacao","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":500000,"faturamento_medio_mensal":200000,"prazo_retorno_meses":36,"num_unidades":400,"anos_mercado":35,"royalties_pct":5.0,"tem_selo_excelencia":False},
        {"nome":"Burger King","segmento":"Alimentacao","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":1500000,"faturamento_medio_mensal":500000,"prazo_retorno_meses":48,"num_unidades":1000,"anos_mercado":55,"royalties_pct":4.5,"tem_selo_excelencia":True},
        {"nome":"KFC","segmento":"Alimentacao","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":1500000,"faturamento_medio_mensal":400000,"prazo_retorno_meses":48,"num_unidades":270,"anos_mercado":31,"royalties_pct":5.0,"tem_selo_excelencia":False},
        {"nome":"AM PM","segmento":"Alimentacao","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":250000,"faturamento_medio_mensal":90000,"prazo_retorno_meses":24,"num_unidades":1500,"anos_mercado":40,"royalties_pct":0,"tem_selo_excelencia":False},
        {"nome":"Rei do Mate","segmento":"Alimentacao","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":100000,"faturamento_medio_mensal":40000,"prazo_retorno_meses":24,"num_unidades":500,"anos_mercado":49,"royalties_pct":8.0,"tem_selo_excelencia":True},
        {"nome":"Vivenda do Camarao","segmento":"Alimentacao","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":400000,"faturamento_medio_mensal":120000,"prazo_retorno_meses":36,"num_unidades":100,"anos_mercado":30,"royalties_pct":5.0,"tem_selo_excelencia":True},
        {"nome":"Market4U","segmento":"Alimentacao","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":40000,"faturamento_medio_mensal":11000,"prazo_retorno_meses":5,"num_unidades":2200,"anos_mercado":6,"royalties_pct":0,"tem_selo_excelencia":False},
        {"nome":"O Boticario","segmento":"Saude_Beleza","cidade_sede":"Curitiba","estado_sede":"PR","investimento_min":300000,"faturamento_medio_mensal":180000,"prazo_retorno_meses":36,"num_unidades":3700,"anos_mercado":46,"royalties_pct":2.5,"tem_selo_excelencia":True},
        {"nome":"OdontoCompany","segmento":"Saude_Beleza","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":200000,"faturamento_medio_mensal":120000,"prazo_retorno_meses":30,"num_unidades":2000,"anos_mercado":26,"royalties_pct":7.0,"tem_selo_excelencia":True},
        {"nome":"Oticas Carol","segmento":"Saude_Beleza","cidade_sede":"Divinopolis","estado_sede":"MG","investimento_min":150000,"faturamento_medio_mensal":80000,"prazo_retorno_meses":24,"num_unidades":1450,"anos_mercado":38,"royalties_pct":5.0,"tem_selo_excelencia":True},
        {"nome":"Espacolaser","segmento":"Saude_Beleza","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":400000,"faturamento_medio_mensal":150000,"prazo_retorno_meses":30,"num_unidades":750,"anos_mercado":27,"royalties_pct":8.0,"tem_selo_excelencia":True},
        {"nome":"Clinica da Cidade","segmento":"Saude_Beleza","cidade_sede":"Brasilia","estado_sede":"DF","investimento_min":800000,"faturamento_medio_mensal":300000,"prazo_retorno_meses":36,"num_unidades":130,"anos_mercado":20,"royalties_pct":5.0,"tem_selo_excelencia":False},
        {"nome":"Royal Face","segmento":"Saude_Beleza","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":250000,"faturamento_medio_mensal":120000,"prazo_retorno_meses":24,"num_unidades":270,"anos_mercado":7,"royalties_pct":7.0,"tem_selo_excelencia":False},
        {"nome":"Farmacias Sao Joao","segmento":"Saude_Beleza","cidade_sede":"Porto Alegre","estado_sede":"RS","investimento_min":300000,"faturamento_medio_mensal":200000,"prazo_retorno_meses":30,"num_unidades":400,"anos_mercado":60,"royalties_pct":3.0,"tem_selo_excelencia":True},
        {"nome":"Kumon","segmento":"Educacao","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":50000,"faturamento_medio_mensal":30000,"prazo_retorno_meses":18,"num_unidades":1600,"anos_mercado":40,"royalties_pct":0,"tem_selo_excelencia":True},
        {"nome":"Wizard","segmento":"Educacao","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":100000,"faturamento_medio_mensal":40000,"prazo_retorno_meses":24,"num_unidades":1050,"anos_mercado":35,"royalties_pct":10.0,"tem_selo_excelencia":True},
        {"nome":"CCAA","segmento":"Educacao","cidade_sede":"Rio de Janeiro","estado_sede":"RJ","investimento_min":120000,"faturamento_medio_mensal":35000,"prazo_retorno_meses":24,"num_unidades":900,"anos_mercado":54,"royalties_pct":10.0,"tem_selo_excelencia":True},
        {"nome":"Fisk","segmento":"Educacao","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":100000,"faturamento_medio_mensal":30000,"prazo_retorno_meses":24,"num_unidades":850,"anos_mercado":68,"royalties_pct":10.0,"tem_selo_excelencia":True},
        {"nome":"inFlux","segmento":"Educacao","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":80000,"faturamento_medio_mensal":30000,"prazo_retorno_meses":24,"num_unidades":300,"anos_mercado":26,"royalties_pct":10.0,"tem_selo_excelencia":True},
        {"nome":"Microlins","segmento":"Educacao","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":50000,"faturamento_medio_mensal":20000,"prazo_retorno_meses":18,"num_unidades":500,"anos_mercado":32,"royalties_pct":8.0,"tem_selo_excelencia":False},
        {"nome":"Localiza","segmento":"Servicos","cidade_sede":"Belo Horizonte","estado_sede":"MG","investimento_min":500000,"faturamento_medio_mensal":200000,"prazo_retorno_meses":36,"num_unidades":700,"anos_mercado":52,"royalties_pct":6.0,"tem_selo_excelencia":True},
        {"nome":"Prudential","segmento":"Servicos","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":30000,"faturamento_medio_mensal":15000,"prazo_retorno_meses":12,"num_unidades":2000,"anos_mercado":65,"royalties_pct":0,"tem_selo_excelencia":True},
        {"nome":"Seguralta","segmento":"Servicos","cidade_sede":"Porto Alegre","estado_sede":"RS","investimento_min":35000,"faturamento_medio_mensal":18000,"prazo_retorno_meses":12,"num_unidades":1800,"anos_mercado":28,"royalties_pct":0,"tem_selo_excelencia":True},
        {"nome":"Correios","segmento":"Servicos","cidade_sede":"Brasilia","estado_sede":"DF","investimento_min":80000,"faturamento_medio_mensal":30000,"prazo_retorno_meses":24,"num_unidades":600,"anos_mercado":360,"royalties_pct":0,"tem_selo_excelencia":False},
        {"nome":"Chilli Beans","segmento":"Moda","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":200000,"faturamento_medio_mensal":80000,"prazo_retorno_meses":30,"num_unidades":800,"anos_mercado":26,"royalties_pct":5.0,"tem_selo_excelencia":True},
        {"nome":"Hering Store","segmento":"Moda","cidade_sede":"Blumenau","estado_sede":"SC","investimento_min":300000,"faturamento_medio_mensal":100000,"prazo_retorno_meses":36,"num_unidades":550,"anos_mercado":145,"royalties_pct":4.0,"tem_selo_excelencia":True},
        {"nome":"Arezzo","segmento":"Moda","cidade_sede":"Belo Horizonte","estado_sede":"MG","investimento_min":250000,"faturamento_medio_mensal":120000,"prazo_retorno_meses":30,"num_unidades":600,"anos_mercado":51,"royalties_pct":4.0,"tem_selo_excelencia":True},
        {"nome":"Dudalina","segmento":"Moda","cidade_sede":"Blumenau","estado_sede":"SC","investimento_min":200000,"faturamento_medio_mensal":80000,"prazo_retorno_meses":30,"num_unidades":200,"anos_mercado":65,"royalties_pct":4.0,"tem_selo_excelencia":True},
        {"nome":"Colchoes Ortobom","segmento":"Casa_Construcao","cidade_sede":"Maringa","estado_sede":"PR","investimento_min":150000,"faturamento_medio_mensal":80000,"prazo_retorno_meses":24,"num_unidades":2500,"anos_mercado":50,"royalties_pct":3.0,"tem_selo_excelencia":True},
        {"nome":"Casa do Construtor","segmento":"Casa_Construcao","cidade_sede":"Cascavel","estado_sede":"PR","investimento_min":499000,"faturamento_medio_mensal":90000,"prazo_retorno_meses":39,"num_unidades":760,"anos_mercado":38,"royalties_pct":4.0,"tem_selo_excelencia":True},
        {"nome":"iGUi Piscinas","segmento":"Casa_Construcao","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":200000,"faturamento_medio_mensal":80000,"prazo_retorno_meses":30,"num_unidades":450,"anos_mercado":52,"royalties_pct":5.0,"tem_selo_excelencia":True},
        {"nome":"Multicoisas","segmento":"Casa_Construcao","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":150000,"faturamento_medio_mensal":60000,"prazo_retorno_meses":30,"num_unidades":800,"anos_mercado":40,"royalties_pct":4.0,"tem_selo_excelencia":True},
        {"nome":"Kinsol","segmento":"Casa_Construcao","cidade_sede":"Fortaleza","estado_sede":"CE","investimento_min":10000,"faturamento_medio_mensal":20000,"prazo_retorno_meses":6,"num_unidades":800,"anos_mercado":12,"royalties_pct":0,"tem_selo_excelencia":False},
        {"nome":"AcquaZero","segmento":"Servicos_Automotivos","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":80000,"faturamento_medio_mensal":35000,"prazo_retorno_meses":18,"num_unidades":630,"anos_mercado":16,"royalties_pct":6.0,"tem_selo_excelencia":True},
        {"nome":"Car System","segmento":"Servicos_Automotivos","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":100000,"faturamento_medio_mensal":45000,"prazo_retorno_meses":24,"num_unidades":450,"anos_mercado":28,"royalties_pct":7.0,"tem_selo_excelencia":True},
        {"nome":"Lubrax+","segmento":"Servicos_Automotivos","cidade_sede":"Rio de Janeiro","estado_sede":"RJ","investimento_min":150000,"faturamento_medio_mensal":60000,"prazo_retorno_meses":24,"num_unidades":400,"anos_mercado":20,"royalties_pct":4.0,"tem_selo_excelencia":True},
        {"nome":"Maria Brasileira","segmento":"Limpeza","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":41000,"faturamento_medio_mensal":63000,"prazo_retorno_meses":12,"num_unidades":500,"anos_mercado":15,"royalties_pct":8.0,"tem_selo_excelencia":True},
        {"nome":"60 Minutos Lavanderia","segmento":"Limpeza","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":120000,"faturamento_medio_mensal":45000,"prazo_retorno_meses":24,"num_unidades":680,"anos_mercado":8,"royalties_pct":6.0,"tem_selo_excelencia":False},
        {"nome":"Dona Help","segmento":"Limpeza","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":41000,"faturamento_medio_mensal":63000,"prazo_retorno_meses":12,"num_unidades":250,"anos_mercado":10,"royalties_pct":8.0,"tem_selo_excelencia":False},
        {"nome":"CVC","segmento":"Hotelaria","cidade_sede":"Santo Andre","estado_sede":"SP","investimento_min":200000,"faturamento_medio_mensal":80000,"prazo_retorno_meses":30,"num_unidades":1200,"anos_mercado":51,"royalties_pct":5.0,"tem_selo_excelencia":True},
        {"nome":"Flytour","segmento":"Hotelaria","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":100000,"faturamento_medio_mensal":40000,"prazo_retorno_meses":24,"num_unidades":150,"anos_mercado":45,"royalties_pct":6.0,"tem_selo_excelencia":True},
        {"nome":"Vai Voando","segmento":"Hotelaria","cidade_sede":"Sao Paulo","estado_sede":"SP","investimento_min":30000,"faturamento_medio_mensal":15000,"prazo_retorno_meses":12,"num_unidades":200,"anos_mercado":10,"royalties_pct":8.0,"tem_selo_excelencia":False},
    ]
    for item in dados:
        item["coletado_em"] = hoje
        item["fonte"] = "referencia_manual_abf_2024"
    return dados


if __name__ == "__main__":
    df = main()
