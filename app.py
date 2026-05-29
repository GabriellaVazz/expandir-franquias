import streamlit as st
import pandas as pd
import numpy as np
import joblib
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(
    page_title="Score de Potencial · Expandir Franquias",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Força cor primária amarela via variável CSS do Streamlit
st.markdown("""
<style>
:root {
    --primary-color: #F5C645 !important;
    --primary: #F5C645 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* ── FUNDO GERAL ── */
.stApp, [data-testid="stAppViewContainer"] { background: #F7F8FA !important; }
.block-container { padding-top: 1.8rem !important; padding-bottom: 2rem !important; }

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: #0D1B2A !important;
    border-right: 1px solid #1E3450 !important;
}
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] {
    display: none !important;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div { color: #94A3B8 !important; font-size: 12px !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #F1F5F9 !important; }
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: #162032 !important;
    border: 1px solid #1E3450 !important;
    color: #E2E8F0 !important;
    border-radius: 8px !important;
    font-size: 13px !important;
}
[data-testid="stSidebar"] input[type="number"] {
    background: #162032 !important;
    border: 1px solid #1E3450 !important;
    color: #E2E8F0 !important;
    border-radius: 8px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
}
/* Slider: cor controlada pelo config.toml [theme] primaryColor */

/* ── BOTÃO PRINCIPAL ── */
.stButton > button {
    background: #F5C645 !important;
    color: #0D1B2A !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    letter-spacing: 0.04em !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.7rem 1.5rem !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: #C9A030 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(245,198,69,0.35) !important;
}

/* ── DROPDOWN ABERTO (listbox) ── */
[data-testid="stSidebar"] ul[role="listbox"],
[data-testid="stSidebar"] ul[role="listbox"] li,
[data-testid="stSidebar"] ul[role="listbox"] li span,
[data-testid="stSidebar"] ul[role="listbox"] li div {
    background: #F8FAFC !important;
    color: #0D1B2A !important;
    font-size: 13px !important;
}
[data-testid="stSidebar"] ul[role="listbox"] li:hover {
    background: #F1F5F9 !important;
}

/* ── EXPANDER ── */
.streamlit-expanderHeader {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
    font-size: 13px !important;
    color: #475569 !important;
}
.streamlit-expanderContent {
    background: #FFFFFF !important;
    color: #334155 !important;
}
.streamlit-expanderContent p,
.streamlit-expanderContent strong {
    color: #334155 !important;
}

/* ── LABELS DE SEÇÃO ── */
[data-testid="stSidebar"] .sidebar-section-label {
    font-size: 11px !important;
    font-weight: 700 !important;
    color: #CBD5E1 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    margin-bottom: 8px !important;
}
[data-testid="stSidebar"] .sidebar-title {
    font-size: 22px !important;
    font-weight: 800 !important;
    color: #F5C645 !important;
    line-height: 1.2 !important;
    margin-bottom: 4px !important;
}
[data-testid="stSidebar"] .sidebar-subtitle {
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #CBD5E1 !important;
    line-height: 1.4 !important;
    margin-bottom: 0 !important;
}

/* ── HIDE STREAMLIT BRANDING ── */
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── DADOS E ENCODINGS ─────────────────────────────────────────────────────────
SEGMENTO_MAP = {
    "Saúde / Beleza / Bem-Estar":    ("Saude_Beleza",          6, 0.72),
    "Alimentação":                    ("Alimentacao",           0, 0.58),
    "Educação":                       ("Educacao",              2, 0.61),
    "Moda / Vestuário":               ("Moda",                  5, 0.55),
    "Serviços":                       ("Servicos",              7, 0.67),
    "Casa / Construção":              ("Casa_Construcao",       1, 0.65),
    "Serviços Automotivos":           ("Servicos_Automotivos",  8, 0.63),
    "Limpeza":                        ("Limpeza",               4, 0.60),
    "Hotelaria / Turismo":            ("Hotelaria",             3, 0.52),
}

BENCHMARKS = {
    "Saúde / Beleza / Bem-Estar":  {"sobrevivencia": "72%", "crescimento": "15.4% / ano", "mediana_unidades": 980,  "score_mediano": 72},
    "Alimentação":                  {"sobrevivencia": "58%", "crescimento": "11.2% / ano", "mediana_unidades": 1200, "score_mediano": 58},
    "Educação":                     {"sobrevivencia": "61%", "crescimento": "9.8% / ano",  "mediana_unidades": 720,  "score_mediano": 63},
    "Moda / Vestuário":             {"sobrevivencia": "55%", "crescimento": "7.3% / ano",  "mediana_unidades": 430,  "score_mediano": 55},
    "Serviços":                     {"sobrevivencia": "67%", "crescimento": "13.1% / ano", "mediana_unidades": 650,  "score_mediano": 67},
    "Casa / Construção":            {"sobrevivencia": "65%", "crescimento": "10.5% / ano", "mediana_unidades": 510,  "score_mediano": 62},
    "Serviços Automotivos":         {"sobrevivencia": "63%", "crescimento": "12.0% / ano", "mediana_unidades": 390,  "score_mediano": 60},
    "Limpeza":                      {"sobrevivencia": "60%", "crescimento": "8.7% / ano",  "mediana_unidades": 280,  "score_mediano": 58},
    "Hotelaria / Turismo":          {"sobrevivencia": "52%", "crescimento": "6.2% / ano",  "mediana_unidades": 210,  "score_mediano": 50},
}
PORTE_MAP = {
    "Micro — até R$ 130k":            ("Micro (até R$130k)",       1),
    "Médio — R$ 130k a R$ 500k":      ("Médio (R$130k–R$500k)",    2),
    "Grande — acima de R$ 500k":      ("Grande (acima R$500k)",    0),
}
REGIAO_MAP = {
    "Sudeste": 3, "Sul": 4, "Nordeste": 1, "Centro-Oeste": 0, "Norte": 2,
}
MUNICIPIOS = [
    {"nome":"São Paulo","uf":"SP","regiao":"Sudeste","pop":12325000,"pib":62000,"idh":0.805},
    {"nome":"Rio de Janeiro","uf":"RJ","regiao":"Sudeste","pop":6748000,"pib":45000,"idh":0.799},
    {"nome":"Brasília","uf":"DF","regiao":"Centro-Oeste","pop":3059000,"pib":62000,"idh":0.824},
    {"nome":"Salvador","uf":"BA","regiao":"Nordeste","pop":2886000,"pib":24000,"idh":0.759},
    {"nome":"Fortaleza","uf":"CE","regiao":"Nordeste","pop":2428000,"pib":22000,"idh":0.754},
    {"nome":"Belo Horizonte","uf":"MG","regiao":"Sudeste","pop":2315000,"pib":38000,"idh":0.810},
    {"nome":"Manaus","uf":"AM","regiao":"Norte","pop":2063000,"pib":26000,"idh":0.737},
    {"nome":"Curitiba","uf":"PR","regiao":"Sul","pop":1773000,"pib":48000,"idh":0.823},
    {"nome":"Recife","uf":"PE","regiao":"Nordeste","pop":1488000,"pib":28000,"idh":0.772},
    {"nome":"Goiânia","uf":"GO","regiao":"Centro-Oeste","pop":1536000,"pib":35000,"idh":0.799},
    {"nome":"Porto Alegre","uf":"RS","regiao":"Sul","pop":1332000,"pib":50000,"idh":0.805},
    {"nome":"Guarulhos","uf":"SP","regiao":"Sudeste","pop":1379000,"pib":38000,"idh":0.763},
    {"nome":"Campinas","uf":"SP","regiao":"Sudeste","pop":1214000,"pib":52000,"idh":0.805},
    {"nome":"São Luís","uf":"MA","regiao":"Nordeste","pop":1108000,"pib":20000,"idh":0.768},
    {"nome":"Maceió","uf":"AL","regiao":"Nordeste","pop":1012000,"pib":18000,"idh":0.721},
    {"nome":"Campo Grande","uf":"MS","regiao":"Centro-Oeste","pop":916000,"pib":38000,"idh":0.784},
    {"nome":"Natal","uf":"RN","regiao":"Nordeste","pop":890000,"pib":22000,"idh":0.763},
    {"nome":"Teresina","uf":"PI","regiao":"Nordeste","pop":868000,"pib":20000,"idh":0.751},
    {"nome":"São Bernardo do Campo","uf":"SP","regiao":"Sudeste","pop":826000,"pib":58000,"idh":0.805},
    {"nome":"João Pessoa","uf":"PB","regiao":"Nordeste","pop":817000,"pib":22000,"idh":0.763},
    {"nome":"Uberlândia","uf":"MG","regiao":"Sudeste","pop":699000,"pib":45000,"idh":0.789},
    {"nome":"Sorocaba","uf":"SP","regiao":"Sudeste","pop":698000,"pib":42000,"idh":0.798},
    {"nome":"Ribeirão Preto","uf":"SP","regiao":"Sudeste","pop":711000,"pib":48000,"idh":0.800},
    {"nome":"Cuiabá","uf":"MT","regiao":"Centro-Oeste","pop":650000,"pib":42000,"idh":0.785},
    {"nome":"Contagem","uf":"MG","regiao":"Sudeste","pop":663000,"pib":38000,"idh":0.756},
    {"nome":"Aracaju","uf":"SE","regiao":"Nordeste","pop":664000,"pib":26000,"idh":0.770},
    {"nome":"Florianópolis","uf":"SC","regiao":"Sul","pop":508000,"pib":58000,"idh":0.847},
    {"nome":"Joinville","uf":"SC","regiao":"Sul","pop":587000,"pib":52000,"idh":0.809},
    {"nome":"Londrina","uf":"PR","regiao":"Sul","pop":564000,"pib":42000,"idh":0.778},
    {"nome":"Juiz de Fora","uf":"MG","regiao":"Sudeste","pop":560000,"pib":32000,"idh":0.778},
    {"nome":"Belém","uf":"PA","regiao":"Norte","pop":1303000,"pib":18000,"idh":0.746},
    {"nome":"Feira de Santana","uf":"BA","regiao":"Nordeste","pop":613000,"pib":22000,"idh":0.712},
    {"nome":"Niterói","uf":"RJ","regiao":"Sudeste","pop":511000,"pib":55000,"idh":0.837},
    {"nome":"Porto Velho","uf":"RO","regiao":"Norte","pop":539000,"pib":32000,"idh":0.736},
    {"nome":"Caxias do Sul","uf":"RS","regiao":"Sul","pop":535000,"pib":55000,"idh":0.782},
    {"nome":"Maringá","uf":"PR","regiao":"Sul","pop":420000,"pib":48000,"idh":0.808},
    {"nome":"Jundiaí","uf":"SP","regiao":"Sudeste","pop":423000,"pib":62000,"idh":0.822},
    {"nome":"Santos","uf":"SP","regiao":"Sudeste","pop":433000,"pib":58000,"idh":0.840},
    {"nome":"Vitória","uf":"ES","regiao":"Sudeste","pop":365000,"pib":55000,"idh":0.845},
    {"nome":"Blumenau","uf":"SC","regiao":"Sul","pop":353000,"pib":48000,"idh":0.806},
    {"nome":"Cascavel","uf":"PR","regiao":"Sul","pop":347000,"pib":46000,"idh":0.782},
    {"nome":"Palmas","uf":"TO","regiao":"Norte","pop":306000,"pib":32000,"idh":0.788},
    {"nome":"Taguatinga","uf":"DF","regiao":"Centro-Oeste","pop":222598,"pib":48000,"idh":0.818},
    {"nome":"Chapecó","uf":"SC","regiao":"Sul","pop":220000,"pib":48000,"idh":0.790},
    {"nome":"Toledo","uf":"PR","regiao":"Sul","pop":146000,"pib":52000,"idh":0.796},
    {"nome":"Lauro de Freitas","uf":"BA","regiao":"Nordeste","pop":212200,"pib":22000,"idh":0.754},
    {"nome":"Praia Grande","uf":"SP","regiao":"Sudeste","pop":337000,"pib":28000,"idh":0.763},
    {"nome":"Goiânia","uf":"GO","regiao":"Centro-Oeste","pop":1536000,"pib":35000,"idh":0.799},
]
REFS = [
    {"nome":"Óticas Carol",      "seg":"Saúde / Beleza / Bem-Estar","score":97},
    {"nome":"OdontoCompany",     "seg":"Saúde / Beleza / Bem-Estar","score":94},
    {"nome":"O Boticário",       "seg":"Saúde / Beleza / Bem-Estar","score":89},
    {"nome":"Espaçolaser",       "seg":"Saúde / Beleza / Bem-Estar","score":72},
    {"nome":"Clínica da Cidade", "seg":"Saúde / Beleza / Bem-Estar","score":58},
    {"nome":"Cacau Show",        "seg":"Alimentação","score":90},
    {"nome":"Bob's",             "seg":"Alimentação","score":87},
    {"nome":"McDonald's",        "seg":"Alimentação","score":86},
    {"nome":"Giraffas",          "seg":"Alimentação","score":10},
    {"nome":"Habibs",            "seg":"Alimentação","score":5},
    {"nome":"Wizard",            "seg":"Educação","score":87},
    {"nome":"CCAA",              "seg":"Educação","score":87},
    {"nome":"Kumon",             "seg":"Educação","score":82},
    {"nome":"Microlins",         "seg":"Educação","score":6},
    {"nome":"Arezzo",            "seg":"Moda / Vestuário","score":82},
    {"nome":"Chilli Beans",      "seg":"Moda / Vestuário","score":75},
    {"nome":"Hering Store",      "seg":"Moda / Vestuário","score":72},
    {"nome":"Prudential",        "seg":"Serviços","score":86},
    {"nome":"Seguralta",         "seg":"Serviços","score":89},
    {"nome":"Colchões Ortobom",  "seg":"Casa / Construção","score":93},
    {"nome":"Casa do Construtor","seg":"Casa / Construção","score":76},
    {"nome":"AcquaZero",         "seg":"Serviços Automotivos","score":83},
    {"nome":"Maria Brasileira",  "seg":"Limpeza","score":78},
    {"nome":"60 Min. Lavanderia","seg":"Limpeza","score":83},
    {"nome":"CVC",               "seg":"Hotelaria / Turismo","score":94},
    {"nome":"Flytour",           "seg":"Hotelaria / Turismo","score":6},
]
NOMES_PT = {
    "pop_log":"População (log)","pib_norm":"PIB per capita","idh":"IDH do município",
    "regiao_cod":"Região","inv_log":"Investimento inicial","porte_cod":"Porte",
    "segmento_cod":"Segmento","anos_mercado":"Tempo de mercado",
    "num_unidades":"Nº de unidades","retorno_norm":"Prazo de retorno",
    "taxa_sobrevivencia_segmento":"Taxa de sobrevivência",
}

@st.cache_resource
def carregar_modelo():
    p = Path("modelos/modelo_score_potencial.pkl")
    return joblib.load(p) if p.exists() else None

modelo = carregar_modelo()

def montar_input(seg, porte, regiao, pop, pib, idh, inv, anos, unidades, retorno):
    _, seg_cod, taxa = SEGMENTO_MAP[seg]
    _, porte_cod     = PORTE_MAP[porte]
    return pd.DataFrame([{
        "pop_log":                    np.log(max(pop, 1)),
        "pib_norm":                   min(1.0, pib / 80000),
        "idh":                        idh,
        "regiao_cod":                 REGIAO_MAP[regiao],
        "inv_log":                    np.log(max(inv, 1)),
        "porte_cod":                  porte_cod,
        "segmento_cod":               seg_cod,
        "anos_mercado":               anos,
        "num_unidades":               unidades,
        "retorno_norm":               min(1.0, retorno / 60),
        "taxa_sobrevivencia_segmento":taxa,
    }])

def score_cfg(s):
    if s >= 70: return ("Alta probabilidade",   "#16A34A", "#F0FDF4")
    if s >= 45: return ("Potencial moderado",   "#D97706", "#FFFBEB")
    return              ("Baixa probabilidade", "#DC2626", "#FEF2F2")

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding:1rem 0 0.5rem'>
        <div class='sidebar-title'>Expandir Franquias</div>
        <div class='sidebar-subtitle'>Score de Potencial de Expansão</div>
    </div>
    <div style='border-top:1px solid #1E3450;margin:1rem 0'></div>
    """, unsafe_allow_html=True)

    st.markdown("<p class='sidebar-section-label'>Perfil da Franquia</p>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:11px;color:#94A3B8;margin:8px 0 4px'>Segmento</p>", unsafe_allow_html=True)
    seg   = st.selectbox("Segmento", list(SEGMENTO_MAP.keys()), label_visibility="collapsed")
    st.markdown("<p style='font-size:11px;color:#94A3B8;margin:8px 0 4px'>Porte</p>", unsafe_allow_html=True)
    porte = st.selectbox("Porte", list(PORTE_MAP.keys()), index=1, label_visibility="collapsed")

    inv      = st.number_input("Investimento inicial (R$)", 10_000, 5_000_000, 200_000, 10_000)
    anos     = st.slider("Anos de mercado", 1, 50, 8)
    unidades = st.number_input("Nº de unidades ativas", 1, 5000, 30, 1)
    retorno  = st.slider("Prazo de retorno (meses)", 3, 60, 24)

    st.markdown("<div style='border-top:1px solid #1E3450;margin:0.8rem 0'></div>", unsafe_allow_html=True)
    st.markdown("<p class='sidebar-section-label'>Município</p>", unsafe_allow_html=True)

    cidades_labels = [f"{m['nome']} — {m['uf']}" for m in MUNICIPIOS]
    busca = st.text_input("Buscar cidade", placeholder="Digite o nome...", label_visibility="collapsed")
    filtradas = [i for i, l in enumerate(cidades_labels) if busca.lower() in l.lower()] if busca else list(range(len(cidades_labels)))
    idx = st.selectbox("Cidade", filtradas,
                       format_func=lambda i: cidades_labels[i], label_visibility="collapsed")
    cidade = MUNICIPIOS[idx]

    pop = st.number_input("População", 5_000, 20_000_000, int(cidade["pop"]), 10_000)
    pib = st.number_input("PIB per capita (R$)", 5_000, 200_000, int(cidade["pib"]), 1_000)
    idh = st.slider("IDH", 0.40, 0.95, float(cidade["idh"]), 0.01)
    regiao = cidade["regiao"]

    st.markdown(f"<p style='font-size:11px;color:#475569 !important;margin-top:4px'>Região: <b style='color:#F5C645 !important'>{regiao}</b></p>", unsafe_allow_html=True)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    calcular = st.button("Calcular Score →")

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='margin-bottom:1.5rem;padding-bottom:1rem;border-bottom:2px solid #F5C645;
            display:flex;align-items:flex-end;justify-content:space-between'>
    <div>
        <div style='font-size:11px;color:#94A3B8;letter-spacing:0.1em;
                    text-transform:uppercase;margin-bottom:4px'>
            Ferramenta de Apoio à Decisão
        </div>
        <div style='font-size:28px;font-weight:800;color:#0D1B2A;line-height:1'>
            Score de Potencial de Expansão
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── ESTADO INICIAL ────────────────────────────────────────────────────────────
if not calcular:
    cols = st.columns(4)
    itens = [
        ("48","Franquias na base","reais da ABF"),
        ("9","Segmentos","cobertos"),
        (str(len(set(m['regiao'] for m in MUNICIPIOS))),"Regiões","mapeadas"),
        ("0,89","ROC-AUC","validação k=5"),
    ]
    for col,(val,title,sub) in zip(cols,itens):
        col.markdown(f"""
        <div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:14px;
                    padding:1.4rem 1rem;text-align:center;
                    box-shadow:0 1px 3px rgba(0,0,0,0.05)'>
            <div style='font-size:30px;font-weight:800;color:#0D1B2A;line-height:1'>{val}</div>
            <div style='font-size:12px;font-weight:600;color:#475569;margin-top:6px'>{title}</div>
            <div style='font-size:11px;color:#94A3B8'>{sub}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style='margin-top:1.2rem;background:#1E2D3D;border-radius:14px;
                padding:1.4rem 1.8rem;border-left:4px solid #F5C645'>
        <div style='font-size:13px;color:#E2E8F0;line-height:1.8'>
            Preencha o <b style='color:#F5C645'>perfil da franquia</b> e o
            <b style='color:#F5C645'>município</b> na barra lateral, depois clique em
            <b style='color:#FFFFFF'>Calcular Score</b>.<br>
            O resultado é gerado pelo modelo <b style='color:#FFFFFF'>Random Forest</b>
            treinado com 48 franquias reais da ABF, enriquecidas com IBGE e SEBRAE.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── RESULTADO ────────────────────────────────────────────────────────────────
else:
    if modelo is None:
        st.error("Modelo não encontrado em `modelos/modelo_score_potencial.pkl`.")
        st.stop()

    try:
        X     = montar_input(seg, porte, regiao, pop, pib, idh, inv, anos, unidades, retorno)
        score = round(modelo.predict_proba(X)[0][1] * 100)
        label, cor, cor_bg = score_cfg(score)

        # ── ROW 1: score card + perfil ────────────────────────────────────────
        c1, c2 = st.columns([1, 2], gap="medium")

        with c1:
            # Score card cinza escuro com borda e texto amarelo
            st.markdown(f"""
            <div style='background:#1C2B3A;border-radius:16px;
                        border:2px solid #F5C645;
                        padding:2rem 1.5rem;text-align:center;
                        box-shadow:0 4px 24px rgba(0,0,0,0.15)'>
                <div style='font-size:10px;letter-spacing:0.15em;color:#94A3B8;
                            text-transform:uppercase;margin-bottom:0.6rem'>
                    Score de Potencial
                </div>
                <div style='font-size:80px;font-weight:800;color:#F5C645;
                            line-height:1;font-family:"Plus Jakarta Sans",sans-serif'>
                    {score}
                </div>
                <div style='font-size:12px;color:#94A3B8;margin:4px 0 1rem'>de 100 pontos</div>
                <div style='background:#F5C64522;border:1px solid #F5C64555;
                            border-radius:8px;padding:7px 14px;
                            font-size:13px;font-weight:700;color:#F5C645'>
                    {label}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Gauge compacto
            fig = go.Figure(go.Indicator(
                mode="gauge",
                value=score,
                gauge={
                    "axis":{"range":[0,100],"tickwidth":1,
                            "tickfont":{"color":"#475569","size":9}},
                    "bar":{"color":"#F5C645","thickness":0.28},
                    "bgcolor":"#162032",
                    "borderwidth":0,
                    "steps":[
                        {"range":[0,45],  "color":"#1A1200"},
                        {"range":[45,70], "color":"#1A1600"},
                        {"range":[70,100],"color":"#1A1A00"},
                    ],
                    "threshold":{"line":{"color":"#F5C645","width":3},"thickness":0.8,"value":score}
                }
            ))
            fig.update_layout(
                height=190, paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=20,b=0,l=20,r=20),
                font={"color":"#64748B"}
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.markdown(f"""
            <div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:16px;
                        padding:1.5rem 1.8rem;height:100%;
                        box-shadow:0 1px 4px rgba(0,0,0,0.05)'>
                <div style='font-size:10px;letter-spacing:0.1em;text-transform:uppercase;
                            color:#94A3B8;font-weight:700;margin-bottom:1rem'>
                    Perfil analisado
                </div>
                <div style='display:grid;grid-template-columns:1fr 1fr;gap:0'>
                    <div style='padding:10px 0;border-bottom:1px solid #F1F5F9'>
                        <div style='font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.07em'>Segmento</div>
                        <div style='font-size:14px;font-weight:600;color:#0D1B2A;margin-top:2px'>{seg}</div>
                    </div>
                    <div style='padding:10px 0 10px 16px;border-bottom:1px solid #F1F5F9;border-left:1px solid #F1F5F9'>
                        <div style='font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.07em'>Município</div>
                        <div style='font-size:14px;font-weight:600;color:#0D1B2A;margin-top:2px'>{cidade["nome"]} — {cidade["uf"]}</div>
                    </div>
                    <div style='padding:10px 0;border-bottom:1px solid #F1F5F9'>
                        <div style='font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.07em'>Porte</div>
                        <div style='font-size:14px;font-weight:600;color:#0D1B2A;margin-top:2px'>{porte.split("—")[0].strip()}</div>
                    </div>
                    <div style='padding:10px 0 10px 16px;border-bottom:1px solid #F1F5F9;border-left:1px solid #F1F5F9'>
                        <div style='font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.07em'>Região</div>
                        <div style='font-size:14px;font-weight:600;color:#0D1B2A;margin-top:2px'>{regiao}</div>
                    </div>
                    <div style='padding:10px 0;border-bottom:1px solid #F1F5F9'>
                        <div style='font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.07em'>Investimento</div>
                        <div style='font-size:14px;font-weight:600;color:#0D1B2A;margin-top:2px;font-family:"JetBrains Mono",monospace'>R$ {inv:,.0f}</div>
                    </div>
                    <div style='padding:10px 0 10px 16px;border-bottom:1px solid #F1F5F9;border-left:1px solid #F1F5F9'>
                        <div style='font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.07em'>Nº de Unidades</div>
                        <div style='font-size:14px;font-weight:600;color:#0D1B2A;margin-top:2px;font-family:"JetBrains Mono",monospace'>{unidades:,}</div>
                    </div>
                    <div style='padding:10px 0'>
                        <div style='font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.07em'>Anos de Mercado</div>
                        <div style='font-size:14px;font-weight:600;color:#0D1B2A;margin-top:2px'>{anos} anos</div>
                    </div>
                    <div style='padding:10px 0 10px 16px;border-left:1px solid #F1F5F9'>
                        <div style='font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.07em'>IDH · PIB per capita</div>
                        <div style='font-size:14px;font-weight:600;color:#0D1B2A;margin-top:2px;font-family:"JetBrains Mono",monospace'>{idh:.2f} · R$ {pib:,.0f}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ── ROW 2: importância + referências ──────────────────────────────────
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        c3, c4 = st.columns([1,1], gap="medium")

        with c3:
            st.markdown("""
            <div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:16px;
                        padding:1.4rem 1.6rem;box-shadow:0 1px 4px rgba(0,0,0,0.05)'>
            <div style='font-size:10px;letter-spacing:0.1em;text-transform:uppercase;
                        color:#94A3B8;font-weight:700;margin-bottom:0.8rem'>
                Fatores que pesaram no score
            </div>
            """, unsafe_allow_html=True)

            try:
                rf    = modelo.named_steps["model"]
                feats = modelo.named_steps["scaler"].feature_names_in_
                imp   = rf.feature_importances_
                df_imp = (pd.DataFrame({"f":feats,"i":imp})
                          .sort_values("i", ascending=True)
                          .tail(8))
                df_imp["label"] = df_imp["f"].map(lambda x: NOMES_PT.get(x, x))

                fig2 = go.Figure(go.Bar(
                    x=df_imp["i"], y=df_imp["label"],
                    orientation="h",
                    marker=dict(
                        color=df_imp["i"],
                        colorscale=[[0,"#FFF9E6"],[0.5,"#F5C645"],[1,"#C9A030"]],
                    ),
                    text=["{:.1f}%".format(v*100) for v in df_imp["i"]],
                    textposition="outside",
                    textfont=dict(color="#94A3B8", size=10, family="JetBrains Mono"),
                ))
                fig2.update_layout(
                    height=300, paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=0,b=0,l=0,r=70),
                    xaxis=dict(showgrid=False,showticklabels=False,zeroline=False),
                    yaxis=dict(tickfont=dict(color="#475569",size=11,
                                            family="Plus Jakarta Sans")),
                )
                st.plotly_chart(fig2, use_container_width=True)
            except Exception as e:
                st.info(f"Importância não disponível: {e}")

            st.markdown("</div>", unsafe_allow_html=True)

        with c4:
            refs = sorted([r for r in REFS if r["seg"] == seg],
                          key=lambda r: r["score"], reverse=True)
            st.markdown("""
            <div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:16px;
                        padding:1.4rem 1.6rem;box-shadow:0 1px 4px rgba(0,0,0,0.05)'>
            <div style='font-size:10px;letter-spacing:0.1em;text-transform:uppercase;
                        color:#94A3B8;font-weight:700;margin-bottom:0.8rem'>
                Referências do segmento · base ABF
            </div>
            """, unsafe_allow_html=True)

            if refs:
                for r in refs:
                    s = r["score"]
                    rc, _, _ = score_cfg(s)
                    bar_w = int(s * 0.72)
                    st.markdown(f"""
                    <div style='display:flex;align-items:center;justify-content:space-between;
                                padding:8px 0;border-bottom:1px solid #F1F5F9'>
                        <span style='font-size:13px;color:#334155;font-weight:500;flex:1'>{r["nome"]}</span>
                        <div style='display:flex;align-items:center;gap:10px'>
                            <svg width="72" height="6" style="border-radius:4px;overflow:hidden">
                                <rect width="72" height="6" fill="#E2E8F0" rx="3"/>
                                <rect width="{bar_w}" height="6" fill="{rc}" rx="3"/>
                            </svg>
                            <svg width="26" height="18">
                                <text x="26" y="14" text-anchor="end"
                                      font-family="JetBrains Mono, monospace"
                                      font-size="13" font-weight="700"
                                      fill="{rc}">{s}</text>
                            </svg>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown(f"""
                <div style='display:flex;align-items:center;justify-content:space-between;
                            margin-top:8px;padding:10px 14px;
                            background:#F5C64515;border-radius:10px;
                            border:1px solid #F5C64540'>
                    <span style='font-size:13px;font-weight:700;color:#C9A030'>▶ Franquia avaliada</span>
                    <span style='font-size:18px;font-weight:800;color:#C9A030;
                                 font-family:"JetBrains Mono",monospace'>{score}</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Sem referências para este segmento.")

            st.markdown("</div>", unsafe_allow_html=True)

        # ── BENCHMARKS DO SEGMENTO ───────────────────────────────────────────
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        bm = BENCHMARKS.get(seg, {})
        st.markdown(f"""
        <div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:16px;
                    padding:1.2rem 1.6rem;box-shadow:0 1px 4px rgba(0,0,0,0.05)'>
            <div style='font-size:10px;letter-spacing:0.1em;text-transform:uppercase;
                        color:#94A3B8;font-weight:700;margin-bottom:1rem'>
                Benchmarks do Segmento · {seg}
            </div>
            <div style='display:grid;grid-template-columns:repeat(4,1fr);gap:0'>
                <div style='padding:8px 16px 8px 0;border-right:1px solid #F1F5F9'>
                    <div style='font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.07em'>Taxa de sobrevivência (5 anos)</div>
                    <div style='font-size:18px;font-weight:700;color:#0D1B2A !important;margin-top:4px'>{bm.get("sobrevivencia","—")}</div>
                </div>
                <div style='padding:8px 16px;border-right:1px solid #F1F5F9'>
                    <div style='font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.07em'>Crescimento médio de rede</div>
                    <div style='font-size:18px;font-weight:700;color:#F5C645 !important;margin-top:4px'>{bm.get("crescimento","—")}</div>
                </div>
                <div style='padding:8px 16px;border-right:1px solid #F1F5F9'>
                    <div style='font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.07em'>Mediana de unidades</div>
                    <div style='font-size:18px;font-weight:700;color:#0D1B2A !important;margin-top:4px'>{bm.get("mediana_unidades","—")}</div>
                </div>
                <div style='padding:8px 0 8px 16px'>
                    <div style='font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.07em'>Score mediano na base</div>
                    <div style='font-size:18px;font-weight:700;color:#0D1B2A !important;margin-top:4px'>{bm.get("score_mediano","—")}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        with st.expander("ℹ️ O que significam os benchmarks?"):
            st.markdown(f"""
**Taxa de sobrevivência (5 anos)**
Percentual de franquias do segmento *{seg}* que ainda estavam ativas após 5 anos de operação, segundo dados do SEBRAE. Quanto maior, mais resiliente é o modelo de negócio do setor.

**Crescimento médio de rede**
Taxa média anual de expansão do número de unidades das franquias desse segmento na base ABF. Indica o ritmo de crescimento típico do setor — útil para calibrar metas de expansão.

**Mediana de unidades**
Número de unidades que divide ao meio as franquias do segmento: metade das redes tem mais que isso, metade tem menos. Serve como referência de escala "típica" — redes abaixo disso ainda têm muito espaço para crescer.

**Score mediano na base**
O score que o modelo atribui à franquia mediana desse segmento. Use como régua: se a franquia avaliada ficou acima desse número, ela está performando melhor que a média do setor na nossa base.
            """)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        with st.expander("ℹ️ Como o score é calculado"):
            st.markdown("""
**Base de treinamento:** 48 franquias reais da ABF, enriquecidas com dados do IBGE (população, PIB per capita, IDH) e SEBRAE (taxa de sobrevivência por segmento).

**Variável-alvo:** crescimento de unidades acima da mediana do próprio segmento — evita comparar redes de portes diferentes e contorna o viés de sobrevivência dos dados ABF.
            """)

    except Exception as e:
        st.error(f"Erro ao calcular: {e}")

# ── RODAPÉ ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;margin-top:2.5rem;padding-top:1rem;
            border-top:1px solid #E2E8F0;
            font-size:12px;font-family:"Plus Jakarta Sans",sans-serif'>
    <span style='color:#F5C645;font-weight:700'>Expandir Franquias</span>
</div>
""", unsafe_allow_html=True)