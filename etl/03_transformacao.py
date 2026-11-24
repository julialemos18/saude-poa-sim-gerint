"""Transformação e carga: staging -> esquema final.

Uso (na raiz do projeto, com o banco ligado e o esquema já criado):
    python etl/03_transformacao.py

Pode ser rodado várias vezes: apaga e recarrega as tabelas finais
(paciente, solicitacao_internacao, obito, vinculo_sintetico).
Não mexe no esquema staging nem nas tabelas de domínio.
Tudo acontece em UMA transação: se algo falhar, nada fica pela metade.
"""
import re
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------
# DECISÕES DO PROJETO (mude aqui se o grupo decidir outra coisa)
# ---------------------------------------------------------------------
# GERINT: um mesmo paciente pode ter várias solicitações, mas um ID que
# aparece mais de 10 vezes é tratado como valor padrão (suspeito).
MAX_REPETICOES_GERINT = 10
# SIM: uma pessoa só morre uma vez; ID que aparece mais de 1 vez é suspeito.
MAX_REPETICOES_SIM = 1
# Fila recalculada acima deste limite (dias) é marcada como inconsistente.
LIMITE_DIAS_FILA = 365

DOM_SEXO = {"MASCULINO", "FEMININO"}
DOM_CARATER = {"URGENCIA", "ELETIVA", "TRANSFERENCIA"}
DOM_TIPO_LEITO = {"ENFADULTO", "ENFPEDIATRICA", "HOSPDIA", "OBSTETRICO",
                  "PSIQUIATRICO", "UTIADULTO", "UTINEONATAL", "UTIPEDIATRICA"}
DOM_TIPO_INTERNACAO = {"PRÓPRIA", "NÃO PRÓPRIA"}
DOM_RACA = {"BRANCA", "PRETA", "PARDA", "AMARELA", "INDÍGENA"}
DOM_ESCOLARIDADE = {"NENHUMA", "DE 1 A 3 ANOS", "DE 4 A 7 ANOS", "DE 8 A 11 ANOS",
                    "COM 12 ANOS OU MAIS", "IGNORADO"}
DOM_CIRCUNSTANCIA = {"ACIDENTE", "SUICÍDIO", "HOMICÍDIO", "OUTROS", "IGNORADO"}
DOM_GESTACAO = {"MENOS DE 22 SEM", "DE 22 A 27 SEM", "DE 28 A 31 SEM",
                "DE 32 A 36 SEM", "DE 37 A 41 SEM", "IGNORADO"}
DOM_GRAVIDEZ = {"ÚNICA", "DUPLA", "TRIPLA OU MAIS"}
DOM_TIPO_OBITO = {"FETAL", "NÃO FETAL"}

REGEX_CID = r"^[A-Z][0-9]{2}[0-9A-Z]?$"


# ---------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------------------
def texto(serie):
    """Tira espaços das pontas e transforma texto vazio em nulo."""
    return serie.astype("string").str.strip().replace("", pd.NA)


def dominio(serie, validos, avisos=None, nome=""):
    """Mantém só os valores permitidos; o resto vira nulo (e é contado)."""
    novo = serie.where(serie.isin(validos), pd.NA)
    if avisos is not None:
        perdidos = int((serie.notna() & novo.isna()).sum())
        if perdidos:
            avisos[nome] = perdidos
    return novo


def limpar_cid(serie):
    """CID em maiúsculas, sem ponto/hífen/espaço; formato inválido vira nulo."""
    s = texto(serie).str.upper().str.replace(r"[.\-\s]", "", regex=True)
    valido = s.str.match(REGEX_CID).fillna(False).astype(bool)
    return s.where(valido, pd.NA)


def para_inteiro(serie):
    """Texto como '29.0' vira inteiro 29; inválido vira nulo."""
    return pd.to_numeric(serie, errors="coerce").round().astype("Int64")


def entre(serie, minimo, maximo):
    """Mantém números dentro do intervalo; fora dele vira nulo."""
    ok = serie.between(minimo, maximo).fillna(False).astype(bool)
    return serie.where(ok, pd.NA)


def sim_nao_para_booleano(serie):
    s = texto(serie).str.upper()
    return s.map({"SIM": True, "NÃO": False, "NAO": False}).astype("boolean")


def para_banco(df):
    """Troca qualquer tipo de 'nulo' do pandas por None (o banco entende)."""
    df = df.astype(object)
    return df.where(df.notna(), None)


def motivos_de_rejeicao(indice, regras):
    """Junta, por linha, os motivos pelos quais ela deve ser rejeitada."""
    motivo = pd.Series("", index=indice)
    for condicao, descricao in regras:
        cond = condicao.fillna(False).astype(bool)
        motivo = motivo.where(~cond, motivo + descricao + "; ")
    return motivo


def montar_pacientes(ids, fonte, id_inicial, max_repeticoes):
    """Cria a tabela paciente.

    - ID confiável (não nulo e que não se repete demais): um paciente por ID.
    - ID nulo ou suspeito: um paciente PRÓPRIO por linha (id_confiavel = false);
      o ID original é preservado em id_origem (ou nulo, se não existia).
    Devolve (tabela paciente, id_paciente de cada linha).
    """
    freq = ids.map(ids.value_counts())
    confiavel = (ids.notna() & (freq.fillna(0) <= max_repeticoes)).astype(bool)

    ids_conf = pd.Series(ids[confiavel].unique(), dtype="string")
    ids_nao = ids[~confiavel].reset_index(drop=True)

    pacientes = pd.concat([
        pd.DataFrame({"id_origem": ids_conf, "id_confiavel": True}),
        pd.DataFrame({"id_origem": ids_nao, "id_confiavel": False}),
    ], ignore_index=True)
    pacientes["fonte"] = fonte
    pacientes.insert(0, "id_paciente",
                     range(id_inicial, id_inicial + len(pacientes)))

    n_conf = len(ids_conf)
    mapa = pd.Series(pacientes["id_paciente"].iloc[:n_conf].values,
                     index=ids_conf.astype(object).values)
    por_linha = pd.Series(0, index=ids.index, dtype="int64")
    por_linha.loc[confiavel] = ids[confiavel].astype(object).map(mapa).values
    por_linha.loc[~confiavel] = pacientes["id_paciente"].iloc[n_conf:].values
    return pacientes, por_linha


# ---------------------------------------------------------------------
# GERINT
# ---------------------------------------------------------------------
def transformar_gerint(g, id_inicial):
    avisos = {}
    d = pd.DataFrame(index=g.index)

    d["data_solicitacao"] = pd.to_datetime(
        g["data_solicitacao"], format="%Y-%m-%d", errors="coerce")
    d["data_autorizacao"] = pd.to_datetime(
        g["data_autorizacao"], format="%Y-%m-%d", errors="coerce")
    # data_internacao é mantida como veio (a fonte é inconsistente; ver diagnóstico)
    d["data_internacao"] = pd.to_datetime(
        g["data_internacao"], format="%Y-%m-%d", errors="coerce")

    sexo = texto(g["sexo"]).str.upper().replace(
        {"M": "MASCULINO", "F": "FEMININO"})
    d["sexo"] = dominio(sexo, DOM_SEXO, avisos, "gerint.sexo")
    d["idade"] = entre(para_inteiro(g["idade"]), 0, 120)

    for col in ["municipio_residencia", "solicitante", "municipio_solicitante",
                "executante", "central_regulacao_origem"]:
        d[col] = texto(g[col])

    d["codigo_cid"] = limpar_cid(g["codigo_cid"])
    d["grupo_cid"] = d["codigo_cid"].str[:3]
    d["carater"] = texto(g["carater"]).str.upper()
    d["tipo_internacao"] = dominio(texto(g["tipo_internacao"]).str.upper(),
                                   DOM_TIPO_INTERNACAO, avisos, "gerint.tipo_internacao")
    d["tipo_leito"] = texto(g["tipo_leito"]).str.upper()

    # Fila: valor original guardado; tempo recalculado = autorização - solicitação
    d["horas_na_fila_original"] = para_inteiro(g["horas_na_fila"])
    dias = (d["data_autorizacao"] - d["data_solicitacao"]
            ).dt.days.astype("Int64")
    d["dias_ate_autorizacao"] = dias
    d["fila_inconsistente"] = (dias.isna() | (
        dias.fillna(0) > LIMITE_DIAS_FILA)).astype(bool)

    # Linhas que o banco não aceitaria: vão para o arquivo de rejeitados
    motivo = motivos_de_rejeicao(g.index, [
        (d["data_solicitacao"].isna(), "data_solicitacao invalida"),
        (d["solicitante"].isna(), "solicitante ausente"),
        (~d["carater"].isin(DOM_CARATER), "carater fora do dominio"),
        (~d["tipo_leito"].isin(DOM_TIPO_LEITO), "tipo_leito fora do dominio"),
        (d["data_autorizacao"] < d["data_solicitacao"],
         "autorizacao antes da solicitacao"),
    ])
    recusada = motivo != ""
    rejeitados = g[recusada].assign(motivo=motivo[recusada])

    d = d[~recusada].copy()
    ids = texto(g["identificador_pessoa2"])[~recusada]
    pacientes, id_por_linha = montar_pacientes(
        ids, "GERINT", id_inicial, MAX_REPETICOES_GERINT)
    d.insert(0, "id_paciente", id_por_linha)

    for col in ["data_solicitacao", "data_autorizacao", "data_internacao"]:
        d[col] = d[col].dt.date
    return pacientes, d, rejeitados, avisos


# ---------------------------------------------------------------------
# SIM
# ---------------------------------------------------------------------
def transformar_sim(s, id_inicial):
    avisos = {}
    d = pd.DataFrame(index=s.index)

    # A fonte só tem mês/ano: usamos o dia 01 (precisão limitada, documentada)
    obito = pd.to_datetime(s["obito"], format="%m/%Y", errors="coerce")
    nasc = pd.to_datetime(s["nascimento"], format="%m/%Y", errors="coerce")
    d["data_obito"] = obito
    d["data_nascimento"] = nasc

    meses = (obito.dt.year - nasc.dt.year) * \
        12 + (obito.dt.month - nasc.dt.month)
    d["idade_obito"] = entre((meses // 12).astype("Int64"), 0, 120)

    d["sexo"] = dominio(texto(s["sexo"]).str.upper(),
                        DOM_SEXO, avisos, "sim.sexo")
    d["raca"] = dominio(texto(s["raca"]).str.upper(),
                        DOM_RACA, avisos, "sim.raca")
    d["escolaridade"] = dominio(texto(s["escolaridade"]).str.upper(),
                                DOM_ESCOLARIDADE, avisos, "sim.escolaridade")
    d["gestacao"] = dominio(texto(s["gestacao"]).str.upper(),
                            DOM_GESTACAO, avisos, "sim.gestacao")
    d["gravidez"] = dominio(texto(s["gravidez"]).str.upper(),
                            DOM_GRAVIDEZ, avisos, "sim.gravidez")
    d["tipo_obito"] = texto(s["tipo_obito"]).str.upper()
    d["circunstancia_obito"] = dominio(texto(s["circunstancia_obito"]).str.upper(),
                                       DOM_CIRCUNSTANCIA, avisos, "sim.circunstancia_obito")
    d["cid_causa_basica"] = limpar_cid(s["cid_causa_basica"])
    d["grupo_cid"] = d["cid_causa_basica"].str[:3]
    d["obito_prematuro"] = sim_nao_para_booleano(s["obito_prematuro"])
    d["obito_mulher_idade_fertil"] = sim_nao_para_booleano(
        s["obito_mulher_idade_fertil"])

    motivo = motivos_de_rejeicao(s.index, [
        (d["data_obito"].isna(), "data_obito invalida"),
        (~d["tipo_obito"].isin(DOM_TIPO_OBITO), "tipo_obito fora do dominio"),
        (d["data_nascimento"] > d["data_obito"], "nascimento depois do obito"),
    ])
    recusada = motivo != ""
    rejeitados = s[recusada].assign(motivo=motivo[recusada])

    d = d[~recusada].copy()
    ids = texto(s["identificador_pessoa2"])[~recusada]
    pacientes, id_por_linha = montar_pacientes(
        ids, "SIM", id_inicial, MAX_REPETICOES_SIM)
    d.insert(0, "id_paciente", id_por_linha)

    for col in ["data_obito", "data_nascimento"]:
        d[col] = d[col].dt.date
    return pacientes, d, rejeitados, avisos


# ---------------------------------------------------------------------
# PROGRAMA PRINCIPAL
# ---------------------------------------------------------------------
def gravar(df, tabela, conn):
    para_banco(df).to_sql(tabela, conn, if_exists="append", index=False,
                          chunksize=2000, method="multi")


def main(engine=None):
    from sqlalchemy import text
    if engine is None:
        from db import get_engine
        engine = get_engine()

    g = pd.read_sql("SELECT * FROM staging.stg_gerint", engine)
    s = pd.read_sql("SELECT * FROM staging.stg_sim", engine)
    print(f"Staging lido: GERINT {len(g)} linhas, SIM {len(s)} linhas")

    pac_g, solic, rej_g, av_g = transformar_gerint(g, 1)
    pac_s, obito, rej_s, av_s = transformar_sim(s, len(pac_g) + 1)
    pacientes = pd.concat([pac_g, pac_s], ignore_index=True)

    with engine.begin() as conn:  # uma transação só
        conn.execute(text("TRUNCATE vinculo_sintetico, obito, solicitacao_internacao, "
                          "paciente RESTART IDENTITY CASCADE"))
        gravar(pacientes[["id_paciente", "id_origem",
               "fonte", "id_confiavel"]], "paciente", conn)
        # Como informamos os id_paciente manualmente, acertamos o contador do banco
        conn.execute(text("SELECT setval(pg_get_serial_sequence('paciente','id_paciente'), "
                          "(SELECT MAX(id_paciente) FROM paciente))"))
        gravar(solic, "solicitacao_internacao", conn)
        gravar(obito, "obito", conn)

        # Conferência: se algo não bater, dá erro e NADA é gravado
        n_pac = conn.execute(text("SELECT COUNT(*) FROM paciente")).scalar()
        n_sol = conn.execute(
            text("SELECT COUNT(*) FROM solicitacao_internacao")).scalar()
        n_obi = conn.execute(text("SELECT COUNT(*) FROM obito")).scalar()
        assert n_pac == len(
            pacientes), f"paciente: esperado {len(pacientes)}, banco {n_pac}"
        assert n_sol == len(
            g) - len(rej_g), f"solicitacao: esperado {len(g)-len(rej_g)}, banco {n_sol}"
        assert n_obi == len(
            s) - len(rej_s), f"obito: esperado {len(s)-len(rej_s)}, banco {n_obi}"

    # Relatório
    docs = RAIZ / "docs"
    docs.mkdir(exist_ok=True)
    for nome, rej in [("gerint", rej_g), ("sim", rej_s)]:
        arq = docs / f"rejeitados_{nome}.csv"
        if len(rej):
            rej.to_csv(arq, index=False, sep=";", encoding="utf-8")
        elif arq.exists():
            arq.unlink()

    dias = solic["dias_ate_autorizacao"].dropna().astype(float)
    linhas = [
        "# Relatório da transformação e carga\n",
        "| Tabela | Linhas no staging | Carregadas | Rejeitadas |",
        "|---|---|---|---|",
        f"| solicitacao_internacao (GERINT) | {len(g)} | {n_sol} | {len(rej_g)} |",
        f"| obito (SIM) | {len(s)} | {n_obi} | {len(rej_s)} |",
        f"\n**Pacientes criados:** {n_pac} no total",
        f"- GERINT: {int(pac_g['id_confiavel'].sum())} com ID confiável e "
        f"{int((~pac_g['id_confiavel']).sum())} sem (ID nulo ou suspeito)",
        f"- SIM: {int(pac_s['id_confiavel'].sum())} com ID confiável e "
        f"{int((~pac_s['id_confiavel']).sum())} sem (ID nulo ou suspeito)",
        f"\n**Fila recalculada** (data_autorizacao − data_solicitacao, em dias): "
        f"{int(solic['fila_inconsistente'].sum())} linhas marcadas como inconsistentes "
        f"(sem data de autorização ou acima de {LIMITE_DIAS_FILA} dias).",
        f"- Entre as demais: mediana {dias.median():.0f}, P90 {dias.quantile(.9):.0f}, "
        f"P99 {dias.quantile(.99):.0f}; {(dias == 0).mean()*100:.1f}% no mesmo dia.",
    ]
    avisos = {**av_g, **av_s}
    if avisos:
        linhas.append("\n**Valores fora do domínio transformados em nulo:**")
        linhas += [f"- {k}: {v}" for k, v in avisos.items()]
    (docs / "relatorio_transformacao.md").write_text("\n".join(linhas) +
                                                     "\n", encoding="utf-8")

    print("\n".join(linhas))
    print("\nOK. Relatório em docs/relatorio_transformacao.md")


if __name__ == "__main__":
    main()
