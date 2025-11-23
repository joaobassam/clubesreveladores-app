import streamlit as st
import pandas as pd
import plotly.express as px


# =========================================================
# CONFIGURAÇÕES INICIAIS DO APP
# =========================================================
st.set_page_config(
    page_title="Dashboard Jogadores, Clubes e Minutagem",
    layout="wide"
)

st.title("📊 Dashboard de Jogadores, Clubes e Minutagem")


# =========================================================
# FUNÇÃO: FONTE DOS DADOS
# =========================================================
def fonte_dados():
    st.markdown(
        "[**FONTE DOS DADOS: www.ogol.com.br**](https://www.ogol.com.br)"
    )


# =========================================================
# FUNÇÃO: CARREGAMENTO E COMBINAÇÃO DE DADOS
# =========================================================
@st.cache_data
def carregar_dados(path_jogadores: str, path_clubes: str, path_minutos: str):
    """
    Carrega as três bases CSV, renomeia colunas, junta tudo e retorna:
    - df_all: dataset final combinando tudo
    - df_jogadores_clubes: tabela com jogador + clube revelador + país
    - df_clubes: tabela de clubes originais
    """

    # Lê os CSVs
    df_jog = pd.read_csv(path_jogadores)
    df_clu = pd.read_csv(path_clubes)
    df_min = pd.read_csv(path_minutos)

    # Remove colunas de índice que possam ter sido salvas
    df_jog = df_jog.loc[:, ~df_jog.columns.str.contains(r"^Unnamed")]
    df_clu = df_clu.loc[:, ~df_clu.columns.str.contains(r"^Unnamed")]
    df_min = df_min.loc[:, ~df_min.columns.str.contains(r"^Unnamed")]

    # Renomeia colunas para uso interno
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

    # Junta jogador + clube revelador + país
    j_clubes = j.merge(
        c,
        how="left",
        left_on="clube_revelador",
        right_on="clube"
    )

    # Junta minutagem + dados do jogador
    df_all = m.merge(
        j_clubes,
        how="left",
        on="id_jogador",
        suffixes=("", "_j")
    )

    # Junta país do clube atual
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

    # Renomeia finais
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

    # Converte Ano para inteiro (sem casas decimais)
    df_all["Ano"] = pd.to_numeric(df_all["Ano"], errors="coerce")
    df_all["Ano"] = df_all["Ano"].round(0).astype("Int64")

    return df_all, j_clubes, c


# =========================================================
# CARREGAMENTO DE ARQUIVOS
# =========================================================
st.sidebar.header("⚙️ Configuração dos arquivos")

path_jogadores = st.sidebar.text_input(
    "CSV de jogadores",
    "jogadores.csv"
)
path_clubes = st.sidebar.text_input(
    "CSV de clubes",
    "clubes.csv"
)
path_minutos = st.sidebar.text_input(
    "CSV de minutagem",
    "minutos.csv"
)

try:
    df_all, df_jogadores_clubes, df_clubes = carregar_dados(
        path_jogadores, path_clubes, path_minutos
    )
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()


# =========================================================
# FILTROS LATERAIS
# =========================================================
st.sidebar.header("🔍 Filtros Globais")

anos_disp = sorted(df_all["Ano"].dropna().unique())
camp_disp = sorted(df_all["Campeonato"].dropna().unique())
pais_rev_disp = sorted(df_all["pais_clube_revelador"].dropna().unique())
pais_at_disp = sorted(df_all["pais_clube_atual"].dropna().unique())

anos_sel = st.sidebar.multiselect("Ano", anos_disp, default=anos_disp)
camp_sel = st.sidebar.multiselect("Campeonato", camp_disp, default=camp_disp)
pais_rev_sel = st.sidebar.multiselect("País (clube revelador)", ["(Todos)"] + pais_rev_disp, default="(Todos)")
pais_at_sel = st.sidebar.multiselect("País (clube atual)", ["(Todos)"] + pais_at_disp, default="(Todos)")

df_filtrado = df_all.copy()
if anos_sel:
    df_filtrado = df_filtrado[df_filtrado["Ano"].isin(anos_sel)]
if camp_sel:
    df_filtrado = df_filtrado[df_filtrado["Campeonato"].isin(camp_sel)]
if pais_rev_sel and "(Todos)" not in pais_rev_sel:
    df_filtrado = df_filtrado[df_filtrado["pais_clube_revelador"].isin(pais_rev_sel)]
if pais_at_sel and "(Todos)" not in pais_at_sel:
    df_filtrado = df_filtrado[df_filtrado["pais_clube_atual"].isin(pais_at_sel)]


# =========================================================
# ABAS PRINCIPAIS
# =========================================================
tab_geral, tab_jogadores, tab_clubes_rev, tab_campeonatos = st.tabs(
    ["Visão Geral", "Jogadores", "Clubes reveladores", "Campeonatos"]
)


# =========================================================
# 1) VISÃO GERAL
# =========================================================
with tab_geral:
    fonte_dados()
    st.subheader("📈 Visão Geral das Bases (com filtros aplicados)")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Jogadores únicos", df_filtrado["ID Jogador"].nunique())
    col2.metric("Clubes atuais", df_filtrado["Clube Atual"].nunique())
    col3.metric("Clubes reveladores", df_filtrado["Clube Revelador"].nunique())
    col4.metric("Campeonatos", df_filtrado["Campeonato"].nunique())
    col5.metric("Minutos totais", int(df_filtrado["Minutos"].sum()))

    st.markdown("### 🏆 Top clubes reveladores por minutos dos seus formados")

    top_rev = (
        df_filtrado.groupby("Clube Revelador")["Minutos"]
        .sum()
        .reset_index()
        .sort_values("Minutos", ascending=False)
        .head(15)
    )

    fig_top = px.bar(
        top_rev,
        x="Minutos",
        y="Clube Revelador",
        orientation="h",
        title="Top 15 clubes reveladores"
    )
    fig_top.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_top, use_container_width=True)

    # ---------------------------------------------------------
    # NOVA SEÇÃO — TOP 5 CONSOLIDADO POR CAMPEONATO / ANO
    # ---------------------------------------------------------
    st.markdown("### 🏅 Top 5 clubes reveladores por Campeonato/Ano (Tabela Consolidada)")

    camp_ano = (
        df_filtrado
        .groupby(["Campeonato", "Ano", "Clube Revelador"])["Minutos"]
        .sum()
        .reset_index()
    )

    if camp_ano.empty:
        st.info("Nenhum dado disponível para esta seção com os filtros atuais.")
    else:
        # Para cada campeonato, montar uma tabela única
        for camp in sorted(camp_ano["Campeonato"].unique()):
            st.markdown(f"## 📘 {camp}")

            df_c = camp_ano[camp_ano["Campeonato"] == camp].copy()

            anos_camp = sorted(df_c["Ano"].dropna().unique(), reverse=True)

            tabela_linhas = []

            for ano in anos_camp:
                df_ano = df_c[df_c["Ano"] == ano].copy()
                total_ano = df_ano["Minutos"].sum()

                # Top 5
                df_top = (
                    df_ano.sort_values("Minutos", ascending=False)
                    .head(5)
                    .reset_index(drop=True)
                )

                # Montar os 5 colunas (clube + minutos)
                cols_top = []
                for i in range(5):
                    if i < len(df_top):
                        row = df_top.iloc[i]
                        clube = row["Clube Revelador"]
                        mins = int(row["Minutos"])
                        cols_top.append(f"{clube} ({mins:,})".replace(",", "."))
                    else:
                        cols_top.append("—")

                perc = df_top["Minutos"].sum() / total_ano * 100 if total_ano > 0 else 0
                perc_fmt = f"{perc:.1f}%"

                tabela_linhas.append(
                    [int(ano)] + cols_top + [perc_fmt]
                )

            # Criar tabela final
            df_final = pd.DataFrame(
                tabela_linhas,
                columns=["Ano", "🥇 Top 1", "🥈 Top 2", "🥉 Top 3", "Top 4", "Top 5", "% Top 5 / Total"]
            )

            st.dataframe(df_final.reset_index(drop=True), use_container_width=True)


# =========================================================
# 2) VISÃO JOGADORES
# =========================================================
with tab_jogadores:
    fonte_dados()
    st.subheader("🧑‍💼 Visão por Jogador")

    df_players = (
        df_filtrado[["Nome Jogador", "ID Jogador"]]
        .dropna()
        .drop_duplicates()
        .sort_values(["Nome Jogador", "ID Jogador"])
    )

    if df_players.empty:
        st.warning("Nenhum jogador disponível com os filtros atuais.")
    else:
        df_players["label"] = df_players["Nome Jogador"] + " (ID " + df_players["ID Jogador"].astype(str) + ")"
        jogador_label = st.selectbox("Selecione o jogador", df_players["label"])

        row_sel = df_players[df_players["label"] == jogador_label].iloc[0]
        nome_sel = row_sel["Nome Jogador"]
        id_sel = row_sel["ID Jogador"]

        df_j = df_filtrado[df_filtrado["ID Jogador"] == id_sel].copy()

        st.markdown(f"**Jogador:** {nome_sel}")
        st.markdown(f"**ID:** `{id_sel}`")

        if not df_j.empty:
            clube_rev = df_j["Clube Revelador"].iloc[0]
            pais_rev = df_j["pais_clube_revelador"].iloc[0]
            st.markdown(f"**Clube Revelador:** {clube_rev} ({pais_rev})")

            st.metric("Minutos totais (filtro)", int(df_j["Minutos"].sum()))

            st.markdown("### Minutos por ano")
            by_ano = (
                df_j.groupby("Ano")["Minutos"]
                .sum()
                .reset_index()
            )
            by_ano = by_ano.dropna(subset=["Ano"]).sort_values("Ano")

            # eixo categórico de fato
            by_ano["Ano_str"] = by_ano["Ano"].astype(int).astype(str)

            fig_j = px.bar(
                by_ano,
                x="Ano_str",
                y="Minutos",
                title=f"Minutos por ano — {nome_sel}",
                labels={"Ano_str": "Ano"}
            )
            fig_j.update_xaxes(type="category")  # força eixo categórico
            st.plotly_chart(fig_j, use_container_width=True)

            st.markdown("### Detalhamento")
            df_det = df_j[["Ano", "Campeonato", "Clube Atual", "Minutos"]] \
                .sort_values(["Ano", "Campeonato"])
            st.dataframe(df_det.reset_index(drop=True), use_container_width=True)


# =========================================================
# 3) VISÃO CLUBES REVELADORES
# =========================================================
with tab_clubes_rev:
    fonte_dados()
    st.subheader("🏟️ Visão por Clube Revelador")

    # Filtro por país do clube revelador
    pais_rev_lst = sorted(df_filtrado["pais_clube_revelador"].dropna().unique())
    pais_rev_filtro = st.selectbox("Filtrar por país do clube revelador", ["(Todos)"] + pais_rev_lst)

    df_cr = df_filtrado.copy()
    if pais_rev_filtro != "(Todos)":
        df_cr = df_cr[df_cr["pais_clube_revelador"] == pais_rev_filtro]

    clubes_disp = sorted(df_cr["Clube Revelador"].dropna().unique())

    if not clubes_disp:
        st.warning("Nenhum clube revelador disponível com os filtros atuais.")
    else:
        clube_sel = st.selectbox("Clube revelador", clubes_disp)
        df_c = df_cr[df_cr["Clube Revelador"] == clube_sel].copy()

        if df_c.empty:
            st.warning("Nenhum registro para esse clube com os filtros atuais.")
        else:
            pais_clube = df_c["pais_clube_revelador"].iloc[0]
            st.markdown(f"**País:** {pais_clube}")

            col1, col2, col3 = st.columns(3)
            col1.metric("Minutos totais", int(df_c["Minutos"].sum()))
            col2.metric("Jogadores formados", df_c["ID Jogador"].nunique())
            col3.metric("Clubes onde atuaram", df_c["Clube Atual"].nunique())

            # Gráfico de minutos por ano (sem ano decimal)
            st.markdown("### Minutos ao longo dos anos")
            by_ano = df_c.groupby("Ano")["Minutos"].sum().reset_index()
            by_ano = by_ano.dropna(subset=["Ano"]).sort_values("Ano")
            by_ano["Ano_str"] = by_ano["Ano"].astype(int).astype(str)

            fig_cr = px.bar(
                by_ano,
                x="Ano_str",
                y="Minutos",
                title=f"Minutos por ano — formados em {clube_sel}",
                labels={"Ano_str": "Ano"}
            )
            fig_cr.update_xaxes(type="category")  # força eixo categórico
            st.plotly_chart(fig_cr, use_container_width=True)

            # ------------------------------------------
            # Posição do clube revelador nos campeonatos
            # (logo abaixo do gráfico)
            # ------------------------------------------
            st.markdown("### 🏅 Posição do clube revelador nos campeonatos")

            rank_cr = (
                df_cr.groupby(["Campeonato", "Ano", "Clube Revelador"])["Minutos"]
                .sum()
                .reset_index()
            )

            if rank_cr.empty:
                st.info("Não há dados suficientes para montar o ranking com os filtros atuais.")
            else:
                linhas = []

                for (camp, ano), df_grp in rank_cr.groupby(["Campeonato", "Ano"]):
                    df_grp = df_grp.sort_values("Minutos", ascending=False).reset_index(drop=True)
                    df_grp["Posição"] = df_grp.index + 1

                    linha_clube = df_grp[df_grp["Clube Revelador"] == clube_sel]
                    if not linha_clube.empty:
                        pos = int(linha_clube["Posição"].iloc[0])
                        medalha = {1: "🥇", 2: "🥈", 3: "🥉"}.get(pos, "")
                        pos_fmt = f"{medalha} {pos}" if medalha else str(pos)

                        linhas.append({
                            "Campeonato": camp,
                            "Ano": int(ano) if pd.notna(ano) else ano,
                            "Posição": pos_fmt
                        })

                if not linhas:
                    st.info("O clube selecionado não aparece nos rankings dos campeonatos com os filtros atuais.")
                else:
                    df_pos = pd.DataFrame(linhas)
                    df_pos = df_pos.sort_values(["Ano", "Campeonato"], ascending=[False, True])
                    st.dataframe(df_pos.reset_index(drop=True), use_container_width=True)

            # Jogadores formados
            st.markdown("### Jogadores formados neste clube (com minutos, campeonato e ano)")
            df_jogs = (
                df_c.groupby(["Nome Jogador", "Ano", "Campeonato", "Clube Atual"])["Minutos"]
                .sum()
                .reset_index()
                .sort_values(["Ano", "Minutos"], ascending=[True, False])
            )
            st.dataframe(df_jogs.reset_index(drop=True), use_container_width=True)

            # Clubes onde atuaram
            st.markdown("### Clubes onde atuaram (minutos somados)")
            by_atual = (
                df_c.groupby("Clube Atual")["Minutos"]
                .sum()
                .reset_index()
                .sort_values("Minutos", ascending=False)
            )
            st.dataframe(by_atual.reset_index(drop=True), use_container_width=True)


# =========================================================
# 4) VISÃO CAMPEONATOS
# =========================================================
with tab_campeonatos:
    fonte_dados()
    st.subheader("🏆 Visão por Campeonato")

    campeonatos = sorted(df_filtrado["Campeonato"].dropna().unique())
    if not campeonatos:
        st.warning("Nenhum campeonato encontrado com os filtros atuais.")
    else:
        camp_sel = st.selectbox("Selecione o campeonato", campeonatos)

        df_camp_full = df_filtrado[df_filtrado["Campeonato"] == camp_sel].copy()
        if df_camp_full.empty:
            st.warning("Nenhum registro para esse campeonato com os filtros atuais.")
        else:
            # Filtro opcional por clube revelador
            clubes_rev = sorted(df_camp_full["Clube Revelador"].dropna().unique())
            clube_filtro = st.selectbox(
                "Filtrar por clube revelador (opcional)",
                ["(Todos)"] + clubes_rev
            )

            df_camp = df_camp_full.copy()
            if clube_filtro != "(Todos)":
                df_camp = df_camp[df_camp["Clube Revelador"] == clube_filtro]

            col1, col2, col3 = st.columns(3)
            col1.metric("Minutos totais", int(df_camp["Minutos"].sum()))
            col2.metric("Anos disponíveis", df_camp["Ano"].nunique())
            col3.metric("Clubes reveladores", df_camp["Clube Revelador"].nunique())

            # Função para destacar Δ Posição
            def highlight_variation(val):
                if pd.isna(val):
                    return ""
                if val > 0:   # melhorou (subiu posições)
                    return "color: blue; font-weight: bold"
                if val < 0:   # piorou (caiu posições)
                    return "color: red; font-weight: bold"
                return ""

            # Controle Top N
            st.markdown("## 📊 Rankings por Ano")

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

            # Ranking base (sempre usando df_camp_full para posições consistentes)
            ranking = (
                df_camp_full.groupby(["Ano", "Clube Revelador"])["Minutos"]
                .sum()
                .reset_index()
            )

            if ranking.empty:
                st.info("Não há dados suficientes para rankings com os filtros atuais.")
            else:
                # Mapa clube -> país para montar "Clube (País)"
                club_pais = (
                    df_camp_full[["Clube Revelador", "pais_clube_revelador"]]
                    .drop_duplicates()
                )

                anos_ord = sorted(ranking["Ano"].dropna().unique(), reverse=True)

                # função para gerar ranking de um ano
                def ranking_ano(ano):
                    df_r = ranking[ranking["Ano"] == ano].copy()
                    df_r = df_r.sort_values("Minutos", ascending=False).reset_index(drop=True)
                    df_r["Posição"] = df_r.index + 1
                    df_r["Posição"] = df_r["Posição"].astype("Int64")

                    # anexa país e cria coluna "Clube Revelador (País)"
                    df_r = df_r.merge(club_pais, on="Clube Revelador", how="left")

                    def make_name(row):
                        if pd.notna(row["pais_clube_revelador"]):
                            return f'{row["Clube Revelador"]} ({row["pais_clube_revelador"]})'
                        else:
                            return row["Clube Revelador"]

                    df_r["Clube Revelador (País)"] = df_r.apply(make_name, axis=1)

                    return df_r

                # dicionário ano -> ranking com nome + país
                ranking_dict = {ano: ranking_ano(ano) for ano in sorted(anos_ord)}

                # ordem cronológica crescente para achar "ano anterior"
                anos_cron = sorted(ranking["Ano"].dropna().unique())

                # Exibir rankings ano a ano em layout 2 colunas
                for i in range(0, len(anos_ord), 2):
                    cols = st.columns(2)
                    for j in range(2):
                        if i + j >= len(anos_ord):
                            break
                        ano = anos_ord[i + j]
                        with cols[j]:
                            st.markdown(f"### 🗓️ {ano}")

                            df_r = ranking_dict[ano].copy()

                            # Localiza ano anterior cronológico
                            idx = anos_cron.index(ano)
                            if idx > 0:
                                ano_ant = anos_cron[idx - 1]
                                df_prev = ranking_dict[ano_ant][["Clube Revelador", "Posição"]].copy()
                                df_prev = df_prev.rename(columns={"Posição": "Pos_ant"})
                                df_r = df_r.merge(df_prev, on="Clube Revelador", how="left")
                                df_r["Δ Posição"] = df_r["Pos_ant"] - df_r["Posição"]
                                df_r["Δ Posição"] = df_r["Δ Posição"].astype("Int64")
                            else:
                                df_r["Pos_ant"] = pd.NA
                                df_r["Δ Posição"] = pd.Series([pd.NA] * len(df_r), dtype="Int64")

                            # Se filtro de clube estiver ativo, manter só ele (mas posição continua do ranking completo)
                            if clube_filtro != "(Todos)":
                                df_r = df_r[df_r["Clube Revelador"] == clube_filtro]
                            else:
                                # aplicar Top N só quando não filtramos um clube específico
                                if top_n is not None:
                                    df_r = df_r.sort_values("Posição").head(int(top_n))

                            df_r = df_r[["Posição", "Clube Revelador (País)", "Minutos", "Δ Posição"]]
                            df_r = df_r.reset_index(drop=True)

                            st.dataframe(
                                df_r.style.applymap(highlight_variation, subset=["Δ Posição"]),
                                use_container_width=True
                            )

            # --------------------------------------------------------
            # DETALHAMENTO FINAL DO CAMPEONATO
            # --------------------------------------------------------
            st.markdown("### 📄 Detalhamento do Campeonato")

            df_det = (
                df_camp[["Ano", "Clube Revelador", "Clube Atual", "Nome Jogador", "Minutos"]]
                .sort_values(["Ano", "Clube Revelador", "Clube Atual", "Nome Jogador"])
            )

            st.dataframe(df_det.reset_index(drop=True), use_container_width=True)


