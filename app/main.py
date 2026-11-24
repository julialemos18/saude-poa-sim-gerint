"""Painel Streamlit v1 (consultas básicas).

Como rodar (na raiz do projeto, com o banco ligado e a carga feita):
    streamlit run app/main.py
"""
import plotly.express as px
import streamlit as st

from utils import consultar, csv_para_download

st.set_page_config(page_title="SIM + GERINT - Porto Alegre",
                   page_icon="🏥", layout="wide")


# ---------------------------------------------------------------------
# PÁGINAS
# ---------------------------------------------------------------------
def pagina_inicio():
    st.title("Análise de internações (GERINT) e mortalidade (SIM)")
    st.write("Painel com consultas sobre duas bases públicas do SUS em Porto Alegre. "
             "Escolha uma análise no menu à esquerda.")
    st.info(
        "**Leia antes de interpretar os números**\n\n"
        "- As duas bases **não compartilham identificadores confiáveis**; nenhuma "
        "análise nesta versão cruza internações com óbitos.\n"
        "- O **tempo em fila** é o número de dias entre a solicitação e a **autorização** "
        "(a coluna original de horas é inconsistente). Só há data, sem hora.\n"
        "- O SIM cobre 2011 a 2021, e a maior parte do GERINT é de 2025: "
        "os dois conjuntos **não** descrevem o mesmo período."
    )
    c1, c2 = st.columns(2)
    sol = consultar("distribuicao_carater")["solicitacoes"].sum()
    obi = consultar("mortalidade_resumo", inicio="1900-01-01",
                    fim="2100-01-01")["obitos"].iloc[0]
    c1.metric("Solicitações de internação (GERINT)",
              f"{int(sol):,}".replace(",", "."))
    c2.metric("Declarações de óbito (SIM)", f"{int(obi):,}".replace(",", "."))


def pagina_fila_por_leito():
    st.header("Tempo até a autorização, por tipo de leito")
    st.caption("Base GERINT. Dias entre a solicitação e a autorização; "
               "linhas com fila inconsistente ficam de fora.")
    df = consultar("fila_por_leito")
    fig = px.bar(df, x="leito", y=["media_dias", "mediana_dias", "p90_dias"], barmode="group",
                 labels={"value": "dias", "variable": "medida", "leito": "tipo de leito"})
    st.plotly_chart(fig, width="stretch")
    st.dataframe(df, width="stretch", hide_index=True)
    st.caption("A mediana é 0 para a maioria dos leitos: boa parte das solicitações "
               "é autorizada no mesmo dia. Por isso a média e o P90 mostram melhor as esperas longas.")


def pagina_perfil_mortalidade():
    st.header("Perfil sociodemográfico dos óbitos")
    st.caption("Base SIM. Cada dimensão é analisada separadamente.")
    opcoes = {"Raça/cor": ("perfil_raca", "raca"),
              "Escolaridade": ("perfil_escolaridade", "escolaridade"),
              "Faixa etária": ("perfil_faixa_etaria", "faixa_etaria")}
    escolha = st.radio("Dimensão", list(opcoes), horizontal=True)
    consulta, coluna = opcoes[escolha]
    df = consultar(consulta)
    fig = px.bar(df, x=coluna, y="obitos", text="percentual",
                 labels={coluna: escolha, "obitos": "óbitos"})
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(df, width="stretch", hide_index=True)
    st.caption(
        "'NÃO INFORMADO' = campo vazio na fonte; 'IGNORADO' = valor registrado como ignorado.")


def pagina_estabelecimentos():
    st.header("Solicitações por estabelecimento solicitante")
    st.caption("Base GERINT.")
    limite = st.slider("Quantos estabelecimentos mostrar", 5, 50, 15)
    df = consultar("solicitacoes_por_estabelecimento", limite=limite)
    fig = px.bar(df, x="solicitacoes", y="solicitante", orientation="h",
                 hover_data=["municipio_solicitante", "percentual"])
    fig.update_layout(yaxis=dict(autorange="reversed",
                      title=""), height=max(400, 28 * limite))
    st.plotly_chart(fig, width="stretch")
    st.dataframe(df, width="stretch", hide_index=True)


def pagina_carater():
    st.header("Solicitações por caráter")
    st.caption("Base GERINT. Urgência, eletiva ou transferência.")
    df = consultar("distribuicao_carater")
    cols = st.columns(len(df))
    for coluna, (_, linha) in zip(cols, df.iterrows()):
        coluna.metric(linha["carater"], f"{int(linha['solicitacoes']):,}".replace(",", "."),
                      f"{linha['percentual']}%", delta_color="off")
    fig = px.bar(df, x="carater", y="solicitacoes", text="percentual")
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(df, width="stretch", hide_index=True)


def pagina_indicadores_mortalidade():
    st.header("Indicadores de mortalidade")
    st.caption("Base SIM. Filtre o período e exporte os resultados.")
    limites = consultar("periodo_obitos").iloc[0]
    periodo = st.date_input("Período do óbito", value=(limites["inicio"], limites["fim"]),
                            min_value=limites["inicio"], max_value=limites["fim"])
    if len(periodo) != 2:
        st.info("Selecione a data inicial e a final.")
        return
    inicio, fim = periodo
    n_causas = st.slider("Quantas causas mostrar", 5, 30, 10)

    resumo = consultar("mortalidade_resumo", inicio=inicio, fim=fim).iloc[0]
    c = st.columns(4)
    c[0].metric("Óbitos", f"{int(resumo['obitos']):,}".replace(",", "."))
    c[1].metric("Fetais", f"{int(resumo['fetais']):,}".replace(",", "."))
    c[2].metric(
        "Prematuros", f"{int(resumo['prematuros']):,}".replace(",", "."))
    c[3].metric("Mulheres em idade fértil",
                f"{int(resumo['mulheres_idade_fertil']):,}".replace(",", "."))

    por_mes = consultar("mortalidade_por_mes", inicio=inicio, fim=fim)
    st.subheader("Evolução mensal")
    st.plotly_chart(px.line(por_mes, x="mes", y="obitos", markers=True,
                            labels={"mes": "mês", "obitos": "óbitos"}), width="stretch")

    por_causa = consultar("mortalidade_por_causa",
                          inicio=inicio, fim=fim, limite=n_causas)
    st.subheader("Principais causas básicas (categoria CID)")
    fig = px.bar(por_causa, x="grupo_cid", y="obitos", text="percentual",
                 labels={"grupo_cid": "categoria CID", "obitos": "óbitos"})
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    st.plotly_chart(fig, width="stretch")

    st.subheader("Exportar")
    b1, b2 = st.columns(2)
    b1.download_button("Baixar evolução mensal (CSV)", csv_para_download(por_mes),
                       file_name="obitos_por_mes.csv", mime="text/csv")
    b2.download_button("Baixar causas (CSV)", csv_para_download(por_causa),
                       file_name="obitos_por_causa.csv", mime="text/csv")


# ---------------------------------------------------------------------
# MENU
# ---------------------------------------------------------------------
PAGINAS = {
    "Início": pagina_inicio,
    "Fila por tipo de leito": pagina_fila_por_leito,
    "Perfil dos óbitos": pagina_perfil_mortalidade,
    "Solicitações por estabelecimento": pagina_estabelecimentos,
    "Caráter das solicitações": pagina_carater,
    "Indicadores de mortalidade": pagina_indicadores_mortalidade,
}

st.sidebar.title("Menu")
pagina = st.sidebar.radio("Análise", list(
    PAGINAS), label_visibility="collapsed")
st.sidebar.caption(
    "Dados abertos da Prefeitura de Porto Alegre (GERINT e SIM).")
PAGINAS[pagina]()
