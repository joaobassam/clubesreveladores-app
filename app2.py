import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
# CONFIGURAÇÕES INICIAIS
# =========================
st.set_page_config(
    page_title="Dashboard Jogadores, Clubes e Minutagem",
    layout="wide"
)

st.title("📊 Dashboard de Jogadores, Clubes e Minutagem")


# =========================
# FUNÇÃO FONTE DOS DADOS
# =========================
def fonte_dados():
    st.markdown(
        "[**FONTE DOS DADOS: www.ogol.com.br**](https://www.ogol.com.br)"
    )


# =========================
# CARREGAR E COMBINAR DADOS
# =========================
@st.cache_data
def carregar_dados(path_jogadores: str, path_clubes: str, path_minutos: str):
    # Lê os CSVs (separador vírgula por padrão)
    df_jog = pd.read_csv(path_jogadores)
    df_clu = pd.read_csv(path_clubes)
    df_min = pd.read_csv(path_minutos)

    # Remove possíveis colunas de índice salvas no CSV (ex: 'Unnamed: 0')
    df_jog = df_jog.loc[:, ~df_jog.columns.str.contains(r"^Unnamed")]
    df_clu = df_clu.loc[:, ~df_clu.columns.str.contains(r"^Unnamed")]
    df_min = df_min.loc[:, ~df_min.columns.str.contains(r"^Unnamed")]

    # Renomeia para nomes internos mais fáceis
    j = df_jog.rename(columns={
        "Jogador": "nome_jogador",
        "ID": "id_jogador",
        "Clube Revelador": "clube_revelador"
    })

    c = df_clu.rename(columns={
        "Clube": "clube",
        "País": "pais"
    })

    m = df_min.rename(columns={
        "Campeonato": "campeonato",
        "Ano": "ano",
        "Jogador": "nome_jogador",
        "ID": "id_jogador",
        "Clube": "clube_atual",
        "Minutos": "minutos"
    })

    # Tipos
    j["id_jogador"] = j["id_jogador"].astype(str)
    m["id_jogador"] = m["id_jogador"].astype(str)
    m["minutos"] = pd.to_numeric(m["minutos"], errors="coerce").fillna(0)

    # 1) adiciona país do clube revelador (merge jogadores x clubes)
    j_clubes = j.merge(
        c,
        how="left",
        left_on="clube_revelador",
        right_on="clube"
    )

    # 2) junta minutagem com dados do jogador (inclui clube revelador + país)
    df_all = m.merge(
        j_clubes,
        how="left",
        on="id_jogador",
        suffixes=("", "_j")
    )

    # 3) adiciona país do clube atual
    c2 = c.rename(columns={
        "clube": "clube_atual_join",
        "pais": "pais_clube_atual"
    })

    df_all = df_all.merge(
        c2,
        how="left",
        left_on="clube_atual",
        right_on="clube_atual_join"
    )

    # 4) renomeia para nomes finais usados no app
    df_all = df_all.rename(columns={
        "campeonato": "Campeonato",
        "ano": "Ano",
        "nome_jogador": "Nome Jogador",
        "id_jogador": "ID Jogador",
        "clube_atual": "Clube Atual",
        "minutos": "Minutos",
        "clube_revelador": "Clube Revelador",
        "pais": "pais_clube_revelador"
    })

    # Remove colunas auxiliares
    for col in ["nome_jogador_j", "clube", "clube_atual_join"]:
        if col in df_all.columns:
            df_all = df_all.drop(columns=[col])

    # Ano numérico (para ordenar)
    df_all["Ano"] = pd.to_numeric(df_all["Ano"], errors="coerce")

    return df_all, j_clubes, c


# =========================
# CONFIGURAÇÃO DOS ARQUIVOS
# =========================
st.sidebar.header("⚙️ Configuração dos arquivos")

path_jogadores = st.sidebar.text_input(
    "Caminho do CSV de jogadores (Jogador,ID,Clube Revelador)",
    "jogadores.csv"
)
path_clubes = st.sidebar.text_input(
    "Caminho do CSV de clubes (Clube,País)",
    "clubes.csv"
)
path_minutos = st.sidebar.text_input(
    "Caminho do CSV de minutagem (Campeonato,Ano,Jogador,ID,Clube,Minutos)",
    "minutos.csv"
)

if not (path_jogadores and path_clubes and path_minutos):
    st.warning("Informe os caminhos dos três arquivos CSV na barra lateral.")
    st.stop()

try:
    df_all, df_jogadores_clubes, df_clubes = carregar_dados(
        path_jogadores, path_clubes, path_minutos
    )
except FileNotFoundError as e:
    st.error(f"Arquivo não encontrado: {e}")
    st.stop()
except Exception as e:
    st.error(f"Erro ao carregar/combinar os dados: {e}")
    st.stop()

# =========================
# FILTROS GERAIS (sidebar)
# =========================
st.sidebar.header("🔍 Filtros Globais")

anos_disponiveis = sorted(df_all["Ano"].dropna().unique().tolist())
campeonatos_disponiveis = sorted(df_all["Campeonato"].dropna().unique().tolist())
paises_reveladores = sorted(df_all["pais_clube_revelador"].dropna().unique().tolist())
paises_atuais = sorted(df_all["pais_clube_atual"].dropna().unique().tolist())

anos_sel = st.sidebar.multiselect("Ano", anos_disponiveis, default=anos_disponiveis)
camp_sel = st.sidebar.multiselect("Campeonato (filtro geral)", campeonatos_disponiveis, default=campeonatos_disponiveis)
pais_rev_sel = st.sidebar.multiselect("País (clube revelador)", ["(Todos)"] + paises_reveladores, default="(Todos)")
pais_atual_sel = st.sidebar.multiselect("País (clube atual)", ["(Todos)"] + paises_atuais, default="(Todos)")

df_filtrado = df_all.copy()
if anos_sel:
    df_filtrado = df_filtrado[df_filtrado["Ano"].isin(anos_sel)]
if camp_sel:
    df_filtrado = df_filtrado[df_filtrado["Campeonato"].isin(camp_sel)]
if pais_rev_sel and "(Todos)" not in pais_rev_sel:
    df_filtrado = df_filtrado[df_filtrado["pais_clube_revelador"].isin(pais_rev_sel)]
if pais_atual_sel and "(Todos)" not in pais_atual_sel:
    df_filtrado = df_filtrado[df_filtrado["pais_clube_atual"].isin(pais_atual_sel)]

# =========================
# TABS PRINCIPAIS (visões)
# =========================
tab_geral, tab_jogadores, tab_clubes_rev, tab_campeonatos = st.tabs(
    ["Visão Geral", "Jogadores", "Clubes reveladores", "Campeonatos"]
)


# =========================
# 1) VISÃO GERAL
# =========================
with tab_geral:
    fonte_dados()
    st.subheader("📈 Visão Geral das Bases (com filtros aplicados)")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Jogadores únicos", df_filtrado["ID Jogador"].nunique())
    with col2:
        st.metric("Clubes (atuais)", df_filtrado["Clube Atual"].nunique())
    with col3:
        st.metric("Clubes reveladores", df_filtrado["Clube Revelador"].nunique())
    with col4:
        st.metric("Campeonatos", df_filtrado["Campeonato"].nunique())
    with col5:
        st.metric("Minutos totais", int(df_filtrado["Minutos"].sum()))

    st.markdown("### 🏆 Top clubes reveladores por minutos dos seus formados")
    top_clubes_rev = (
        df_filtrado
        .groupby("Clube Revelador")["Minutos"]
        .sum()
        .reset_index()
        .sort_values("Minutos", ascending=False)
        .head(15)
    )
    fig1 = px.bar(
        top_clubes_rev,
        x="Minutos",
        y="Clube Revelador",
        orientation="h",
        title="Top 15 clubes reveladores por minutagem dos jogadores formados",
    )
    fig1.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig1, use_container_width=True)

    # ---------- Nova seção: Top 5 por Campeonato/Ano ----------
    st.markdown("### 🏅 Top 5 clubes reveladores por Campeonato/Ano")

    camp_ano_clube = (
        df_filtrado
        .groupby(["Campeonato", "Ano", "Clube Revelador"])["Minutos"]
        .sum()
        .reset_index()
    )

    if camp_ano_clube.empty:
        st.info("Não há dados suficientes para montar o ranking por campeonato/ano com os filtros atuais.")
    else:
        for camp in sorted(camp_ano_clube["Campeonato"].unique()):
            st.markdown(f"#### Campeonato: {camp}")
            df_c = camp_ano_clube[camp_ano_clube["Campeonato"] == camp].copy()
            anos_camp = sorted(df_c["Ano"].dropna().unique(), reverse=True)

            for ano in anos_camp:
                df_ca = df_c[df_c["Ano"] == ano].copy()
                total_min = df_ca["Minutos"].sum()

                df_ca = df_ca.sort_values("Minutos", ascending=False).head(5)
                df_ca["Posição"] = range(1, len(df_ca) + 1)
                df_ca["Medalha"] = df_ca["Posição"].map(
                    {1: "🥇", 2: "🥈", 3: "🥉"}
                ).fillna("")
                df_ca["% do total"] = (df_ca["Minutos"] / total_min * 100).round(1)

                df_ca = df_ca[["Posição", "Medalha", "Clube Revelador", "Minutos", "% do total"]]

                st.markdown(f"**Ano {int(ano)}**")
                st.dataframe(df_ca.reset_index(drop=True), use_container_width=True)


# =========================
# 2) JOGADORES (seleção por Nome + ID)
# =========================
with tab_jogadores:
    fonte_dados()
    st.subheader("🧑‍💼 Visão por Jogador")

    df_players = (
        df_filtrado[["Nome Jogador", "ID Jogador"]]
        .dropna()
        .drop_duplicates()
        .sort_values(["Nome Jogador", "ID Jogador"])
    )
    df_players["label"] = df_players["Nome Jogador"] + " (ID " + df_players["ID Jogador"].astype(str) + ")"

    if df_players.empty:
        st.warning("Nenhum jogador disponível com os filtros atuais.")
    else:
        jogador_label_sel = st.selectbox(
            "Selecione um jogador",
            df_players["label"].tolist()
        )

        row_sel = df_players[df_players["label"] == jogador_label_sel].iloc[0]
        jogador_sel = row_sel["Nome Jogador"]
        id_sel = row_sel["ID Jogador"]

        df_jog = df_filtrado[df_filtrado["ID Jogador"] == id_sel].copy()

        if df_jog.empty:
            st.warning("Nenhum registro encontrado para esse jogador com os filtros atuais.")
        else:
            clube_rev = df_jog["Clube Revelador"].iloc[0]
            pais_rev = df_jog["pais_clube_revelador"].iloc[0]

            st.markdown(f"**Jogador:** {jogador_sel}")
            st.markdown(f"**ID do jogador:** `{id_sel}`")
            if pd.notna(pais_rev):
                st.markdown(f"**Clube revelador:** {clube_rev} ({pais_rev})")
            else:
                st.markdown(f"**Clube revelador:** {clube_rev}")

            minutos_totais = int(df_jog["Minutos"].sum())
            st.metric("Minutos totais (filtro atual)", minutos_totais)

            st.markdown("### Minutos por ano")
            by_ano = (
                df_jog.groupby("Ano")["Minutos"]
                .sum()
                .reset_index()
                .sort_values("Ano")
            )
            fig4 = px.bar(
                by_ano,
                x="Ano",
                y="Minutos",
                title=f"Minutos por ano - {jogador_sel}",
            )
            st.plotly_chart(fig4, use_container_width=True)

            st.markdown("### Detalhamento por campeonato/ano/clube")
            df_jog_view = df_jog[["Ano", "Campeonato", "Clube Atual", "Minutos"]]\
                           .sort_values(["Ano", "Campeonato"])
            st.dataframe(df_jog_view.reset_index(drop=True), use_container_width=True)


# =========================
# 3) CLUBES REVELADORES
# =========================
with tab_clubes_rev:
    fonte_dados()
    st.subheader("🏟️ Visão por Clube Revelador")

    # filtro prévio por país do clube revelador
    paises_clube_rev = sorted(df_filtrado["pais_clube_revelador"].dropna().unique().tolist())
    pais_clube_rev_sel = st.selectbox(
        "Filtrar por país do clube revelador",
        ["(Todos)"] + paises_clube_rev
    )

    df_clubes_view = df_filtrado.copy()
    if pais_clube_rev_sel != "(Todos)":
        df_clubes_view = df_clubes_view[df_clubes_view["pais_clube_revelador"] == pais_clube_rev_sel]

    clubes_lista = sorted(df_clubes_view["Clube Revelador"].dropna().unique().tolist())

    if not clubes_lista:
        st.warning("Nenhum clube revelador disponível com os filtros atuais.")
    else:
        clube_sel = st.selectbox("Selecione um clube revelador", clubes_lista)

        df_clube = df_clubes_view[df_clubes_view["Clube Revelador"] == clube_sel].copy()

        if df_clube.empty:
            st.warning("Nenhum registro encontrado para esse clube revelador com os filtros atuais.")
        else:
            pais_clube = df_clube["pais_clube_revelador"].iloc[0]
            st.markdown(f"**País do clube revelador:** {pais_clube}")

            minutos_clube = int(df_clube["Minutos"].sum())
            jogadores_unicos = df_clube["ID Jogador"].nunique()
            clubes_atuais_unicos = df_clube["Clube Atual"].nunique()

            col1, col2, col3 = st.columns(3)
            col1.metric("Minutos totais (filtro atual)", minutos_clube)
            col2.metric("Jogadores formados", jogadores_unicos)
            col3.metric("Clubes em que atuaram", clubes_atuais_unicos)

            st.markdown("### Minutos dos jogadores formados por este clube, ao longo dos anos")
            by_ano_clube = (
                df_clube.groupby("Ano")["Minutos"]
                .sum()
                .reset_index()
                .sort_values("Ano")
            )
            fig5 = px.bar(
                by_ano_clube,
                x="Ano",
                y="Minutos",
                title=f"Minutos por ano - formados em {clube_sel}",
            )
            st.plotly_chart(fig5, use_container_width=True)

            st.markdown("### Jogadores formados neste clube (com minutos, campeonato e ano)")
            df_jogs_clube = (
                df_clube
                .groupby(["Nome Jogador", "Ano", "Campeonato", "Clube Atual"])["Minutos"]
                .sum()
                .reset_index()
                .sort_values(["Ano", "Minutos"], ascending=[True, False])
            )
            st.dataframe(df_jogs_clube.reset_index(drop=True), use_container_width=True)

            st.markdown("### Minutos dos formados por clube em que atuaram")
            by_clube_atual = (
                df_clube.groupby("Clube Atual")["Minutos"]
                .sum()
                .reset_index()
                .sort_values("Minutos", ascending=False)
            )
            st.dataframe(by_clube_atual.reset_index(drop=True), use_container_width=True)


# =========================
# 4) CAMPEONATOS
# =========================
with tab_campeonatos:
    fonte_dados()
    st.subheader("🏆 Visão por Campeonato")

    campeonatos_lista = sorted(df_all["Campeonato"].dropna().unique().tolist())
    if not campeonatos_lista:
        st.warning("Nenhum campeonato encontrado na base.")
    else:
        camp_escolhido = st.selectbox("Selecione um campeonato", campeonatos_lista)

        # df_camp_full: sempre com todos os clubes reveladores (respeitando filtros globais)
        df_camp_full = df_filtrado[df_filtrado["Campeonato"] == camp_escolhido].copy()

        if df_camp_full.empty:
            st.warning("Nenhum registro para esse campeonato com os filtros atuais (anos/países).")
            st.stop()

        # ======== FILTRO DE CLUBE REVELADOR (opcional) ========
        clubes_rev_disp = sorted(df_camp_full["Clube Revelador"].dropna().unique().tolist())
        clube_rev_sel = st.selectbox(
            "Filtrar por clube revelador (opcional)",
            ["(Todos)"] + clubes_rev_disp
        )

        # df_camp: usado para métricas e detalhamento (respeita filtro do clube se houver)
        df_camp = df_camp_full.copy()
        if clube_rev_sel != "(Todos)":
            df_camp = df_camp[df_camp["Clube Revelador"] == clube_rev_sel]

        # ======== Métricas gerais ========
        minutos_totais = int(df_camp["Minutos"].sum())
        anos_camp = df_camp["Ano"].nunique()
        clubes_revs = df_camp["Clube Revelador"].nunique()

        col1, col2, col3 = st.columns(3)
        col1.metric("Minutos totais", minutos_totais)
        col2.metric("Anos no filtro", anos_camp)
        col3.metric("Clubes reveladores", clubes_revs)

        # ===============================
        # Função de destaque do Δ
        # ===============================
        def highlight_variation(val):
            if pd.isna(val):
                return "color: black"
            if val > 0:   # melhorou (subiu posições)
                return "color: blue; font-weight: bold"
            if val < 0:   # piorou (caiu posições)
                return "color: red; font-weight: bold"
            return "color: black"

        # ===============================
        # Controle Top N
        # ===============================
        st.markdown("## 📊 Ranking por Ano dos Clubes Reveladores")

        col_top_flag, col_top_n = st.columns([1, 1.5])
        with col_top_flag:
            top_n_enabled = st.checkbox("Mostrar apenas o Top N por ano", value=False)
        top_n = None
        with col_top_n:
            if top_n_enabled:
                top_n = st.number_input(
                    "Valor de N (Top N)",
                    min_value=1,
                    max_value=1000,
                    value=10,
                    step=1
                )

        # ===========================================================
        # RANKING POR ANO + VARIAÇÃO DE POSIÇÃO VS ANO ANTERIOR
        # ===========================================================

        # Ranking bruto (sempre com TODOS os clubes reveladores do campeonato)
        ranking = (
            df_camp_full
            .groupby(["Ano", "Clube Revelador"])["Minutos"]
            .sum()
            .reset_index()
        )

        # anos_cron: ordem cronológica (crescente)
        anos_cron = sorted(ranking["Ano"].dropna().unique().tolist())
        # anos_disp: ordem de exibição (mais recente para mais antigo)
        anos_disp = sorted(anos_cron, reverse=True)

        # Função para montar ranking de um ano
        def ranking_ano_func(ano_val):
            tmp = ranking[ranking["Ano"] == ano_val].copy()
            tmp = tmp.sort_values("Minutos", ascending=False)
            tmp["Posição"] = range(1, len(tmp) + 1)
            tmp["Posição"] = tmp["Posição"].astype("Int64")
            return tmp

        # Construção ano a ano (com base em todos os clubes)
        ranking_anual = {}
        for ano in anos_cron:
            ranking_anual[ano] = ranking_ano_func(ano)

        # Mostrar rankings ano a ano (tabelas separadas, 2 por linha)
        for i in range(0, len(anos_disp), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j >= len(anos_disp):
                    break
                ano = anos_disp[i + j]
                with cols[j]:
                    st.markdown(f"### 🗓️ Ranking — Ano {ano}")

                    df_rank = ranking_anual[ano].copy()

                    # Descobrir ano anterior (cronológico) para comparar
                    idx_cron = anos_cron.index(ano)
                    if idx_cron > 0:
                        ano_ant = anos_cron[idx_cron - 1]
                        df_prev = ranking_anual[ano_ant][["Clube Revelador", "Posição"]]\
                                  .rename(columns={"Posição": "Posição_ant"})

                        df_rank = df_rank.merge(df_prev, on="Clube Revelador", how="left")
                        # Δ posição: positivo = melhora (subiu), negativo = piora (caiu)
                        df_rank["Δ Posição"] = df_rank["Posição_ant"] - df_rank["Posição"]
                        df_rank["Δ Posição"] = df_rank["Δ Posição"].astype("Int64")
                    else:
                        df_rank["Posição_ant"] = pd.NA
                        df_rank["Δ Posição"] = pd.Series([pd.NA] * len(df_rank), dtype="Int64")

                    # Se filtro de clube revelador estiver ativo, manter só esse clube,
                    # mas usando posição/delta calculados no ranking completo
                    if clube_rev_sel != "(Todos)":
                        df_rank = df_rank[df_rank["Clube Revelador"] == clube_rev_sel]
                    else:
                        # aplicar Top N apenas quando não há filtro de clube
                        if top_n is not None:
                            df_rank = df_rank.sort_values("Posição").head(int(top_n))

                    df_rank = df_rank[["Posição", "Clube Revelador", "Minutos", "Δ Posição"]]
                    df_rank = df_rank.reset_index(drop=True)

                    st.dataframe(
                        df_rank.style.applymap(
                            highlight_variation, subset=["Δ Posição"]
                        ),
                        use_container_width=True
                    )

        # ===========================================================
        # Comparação entre dois anos (movimentação no ranking)
        # ===========================================================
        st.markdown("## 🔄 Comparação entre anos (movimentação no ranking)")

        anos_camp_disponiveis = anos_cron
        if len(anos_camp_disponiveis) < 2:
            st.info("Só existe um ano disponível — não é possível comparar rankings.")
        else:
            colA, colB = st.columns(2)
            with colA:
                ano_ref = st.selectbox("Ano de referência", anos_camp_disponiveis, index=0)
            with colB:
                ano_comp = st.selectbox("Ano de comparação", anos_camp_disponiveis, index=len(anos_camp_disponiveis)-1)

            if ano_ref == ano_comp:
                st.info("Selecione anos diferentes.")
            else:
                rank_ref = ranking_anual[ano_ref][["Clube Revelador", "Posição"]].rename(
                    columns={"Posição": "Posição_ref"}
                )
                rank_comp = ranking_anual[ano_comp][["Clube Revelador", "Posição"]].rename(
                    columns={"Posição": "Posição_comp"}
                )

                comp = pd.merge(rank_ref, rank_comp, on="Clube Revelador", how="outer")

                comp["Posição_ref"] = comp["Posição_ref"].astype("Int64")
                comp["Posição_comp"] = comp["Posição_comp"].astype("Int64")

                # Δ posição: positivo = melhora, negativo = piora
                comp["Δ Posição"] = comp["Posição_ref"] - comp["Posição_comp"]
                comp["Δ Posição"] = comp["Δ Posição"].astype("Int64")

                # Se filtro de clube revelador estiver ativo, mostrar só esse clube
                if clube_rev_sel != "(Todos)":
                    comp = comp[comp["Clube Revelador"] == clube_rev_sel]
                else:
                    # aplica Top N na comparação também (sobre o ano de comparação)
                    if top_n is not None:
                        comp = comp.sort_values("Posição_comp", na_position="last")
                        comp = comp.head(int(top_n))

                comp = comp.sort_values("Posição_comp", na_position="last")
                comp = comp.reset_index(drop=True)

                st.markdown(
                    "**Interpretação:** valores **positivos** em `Δ Posição` = clube subiu no ranking (melhorou); "
                    "**negativos** = caiu (piorou)."
                )

                st.dataframe(
                    comp.style.applymap(
                        highlight_variation, subset=["Δ Posição"]
                    ),
                    use_container_width=True
                )

        # ===========================================================
        # Detalhamento
        # ===========================================================
        st.markdown("### 📄 Detalhamento (Ano / Clube revelador / Clube atual / Jogador / Minutos)")

        df_det = df_camp[["Ano", "Clube Revelador", "Clube Atual", "Nome Jogador", "Minutos"]]\
                 .sort_values(["Ano", "Clube Revelador", "Clube Atual", "Nome Jogador"])

        st.dataframe(df_det.reset_index(drop=True), use_container_width=True)
