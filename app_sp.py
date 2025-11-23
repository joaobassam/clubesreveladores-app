import os
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

# Caminhos dos arquivos CSV
COMP_PATH = "São Paulo_Base - Competições.csv"
PLAYERS_PATH = "São Paulo_Base - CadastroJogadores.csv"
GAMES_PATH = "São Paulo_Base - Jogos.csv"


# ---------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------
@st.cache_data
def load_data():
    comp = pd.read_csv(COMP_PATH)
    players = pd.read_csv(PLAYERS_PATH)
    games = pd.read_csv(GAMES_PATH)

    # ----- Tratamento de Pontuação com vírgula -----
    comp["Pontuação"] = (
        comp["Pontuação"]
        .astype(str)
        .str.replace(",", ".", regex=False)
    )
    comp["Pontuação"] = pd.to_numeric(comp["Pontuação"], errors="coerce").fillna(0.0)

    # Jogos: garantir tipos numéricos
    num_cols_games = ["Participações", "Títulos", "Jogos", "Vitórias", "Empates", "Derrotas"]
    for c in num_cols_games:
        if c in games.columns:
            games[c] = pd.to_numeric(games[c], errors="coerce").fillna(0)

    if "Ano" in players.columns:
        players["Ano"] = pd.to_numeric(players["Ano"], errors="coerce")

    # IDs como string para evitar confusão
    if "ID" in players.columns:
        players["ID"] = players["ID"].astype(str)
    if "ID" in games.columns:
        games["ID"] = games["ID"].astype(str)

    return comp, players, games


def compute_scores(games_df: pd.DataFrame, comp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Recebe o DataFrame de jogos e o de competições e devolve um DF de jogos
    com as colunas A, B, C, Score (pontuação da linha).
    """
    df = games_df.merge(comp_df, on="Competição", how="left")

    # Garantir tratamento de Pontuação (vírgula, etc.)
    df["Pontuação"] = (
        df["Pontuação"]
        .astype(str)
        .str.replace(",", ".", regex=False)
    )
    df["Pontuação"] = pd.to_numeric(df["Pontuação"], errors="coerce").fillna(0.0)

    # Garantir tipos numéricos nas colunas de jogos
    for c in ["Jogos", "Títulos", "Vitórias", "Empates"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # A = Jogos * Pontuação_competição
    df["A"] = df["Jogos"] * df["Pontuação"]

    # B = Títulos * Pontuação_competição * 10
    df["B"] = df["Títulos"] * df["Pontuação"] * 10

    # C = ((Vitórias*3) + Empates) / (Jogos*3) * A
    df["C"] = 0.0
    mask_jogos_pos = df["Jogos"] > 0
    df.loc[mask_jogos_pos, "C"] = (
        ((df.loc[mask_jogos_pos, "Vitórias"] * 3) + df.loc[mask_jogos_pos, "Empates"])
        / (df.loc[mask_jogos_pos, "Jogos"] * 3)
    ) * df.loc[mask_jogos_pos, "A"]

    # Score final da linha
    df["Score"] = df["A"] + df["B"] + df["C"]
    # Pontuação do jogador deve ser inteira
    df["Score"] = df["Score"].round().astype(int)

    return df


def build_ranking_df(games_df: pd.DataFrame, players_df: pd.DataFrame, comp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Monta o ranking de jogadores com base nos jogos, cadastro e competições.
    """
    scored = compute_scores(games_df, comp_df)

    merged = scored.merge(
        players_df[["ID", "Jogador", "Posição", "Ano"]],
        on=["ID", "Jogador"],
        how="left",
    )

    ranking = (
        merged.groupby(["Jogador", "ID", "Posição", "Ano"], as_index=False)
        .agg(
            Pontuacao_Total=("Score", "sum"),
            Total_Jogos=("Jogos", "sum"),
            Titulos=("Títulos", "sum"),
            Competicoes=("Competição", "nunique"),
        )
    )

    # Ordenar por pontuação
    ranking = ranking.sort_values("Pontuacao_Total", ascending=False, na_position="last")
    ranking["Rank"] = range(1, len(ranking) + 1)

    # Garantir pontuação inteira
    ranking["Pontuacao_Total"] = ranking["Pontuacao_Total"].round().astype(int)

    ranking = ranking[
        [
            "Rank",
            "Jogador",
            "ID",
            "Posição",
            "Ano",
            "Pontuacao_Total",
            "Total_Jogos",
            "Titulos",
            "Competicoes",
        ]
    ]

    return ranking


# ---------------------------------------------------------
# App
# ---------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Ranking São Paulo - Jogadores",
        layout="wide",
    )

    st.title("📊 App São Paulo – Ranking de Jogadores")

    comp_loaded, players_loaded, games_loaded = load_data()

    # Inicializar session_state
    if "comp" not in st.session_state:
        st.session_state["comp"] = comp_loaded.copy()
    if "players" not in st.session_state:
        st.session_state["players"] = players_loaded.copy()
    if "games" not in st.session_state:
        st.session_state["games"] = games_loaded.copy()
    if "last_update" not in st.session_state:
        # Dict: { jogador_id: datetime }
        st.session_state["last_update"] = {}

    comp = st.session_state["comp"]
    players = st.session_state["players"]
    games = st.session_state["games"]

    tab_ranking, tab_jogador, tab_comp = st.tabs(
        ["🏅 Ranking de Jogadores", "👤 Ficha do Jogador", "🏆 Competições"]
    )

    # -----------------------------------------------------
    # Aba 1 – Ranking
    # -----------------------------------------------------
    with tab_ranking:
        st.subheader("🏅 Ranking de Jogadores por Pontuação")

        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            anos_disponiveis = sorted(players["Ano"].dropna().unique().tolist())
            anos_labels = ["Todos"] + [str(int(a)) for a in anos_disponiveis]
            ano_escolhido = st.selectbox("Filtrar por ano (Ano do cadastro):", anos_labels)

        with col2:
            posicoes_disponiveis = sorted(players["Posição"].dropna().unique().tolist())
            posicoes_labels = ["Todas"] + posicoes_disponiveis
            posicao_escolhida = st.selectbox("Filtrar por posição:", posicoes_labels)

        with col3:
            top_n = st.number_input("Mostrar apenas o Top N (0 = todos):", min_value=0, value=50, step=1)

        ranking = build_ranking_df(games, players, comp)

        # Aplicar filtros
        if ano_escolhido != "Todos":
            ano_val = int(ano_escolhido)
            ranking = ranking[ranking["Ano"] == ano_val]

        if posicao_escolhida != "Todas":
            ranking = ranking[ranking["Posição"] == posicao_escolhida]

        if top_n > 0:
            ranking = ranking.head(top_n)

        st.markdown("### 📋 Tabela de Ranking")
        st.dataframe(
            ranking,
            use_container_width=True,
            hide_index=True,
        )

        # Gráfico opcional
        if not ranking.empty:
            st.markdown("### 📈 Pontuação dos Jogadores (Top exibido)")
            fig = px.bar(
                ranking.head(30),
                x="Jogador",
                y="Pontuacao_Total",
                hover_data=["Posição", "Ano"],
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum jogador encontrado com os filtros selecionados.")

    # -----------------------------------------------------
    # Aba 2 – Ficha do Jogador
    # -----------------------------------------------------
    with tab_jogador:
        st.subheader("👤 Ficha do Jogador")

        # Ranking completo (para calcular ranks individuais)
        ranking_full = build_ranking_df(games, players, comp)

        # Filtro de ano para jogadores
        anos_disponiveis = sorted(players["Ano"].dropna().unique().tolist())
        anos_labels = ["Todos"] + [str(int(a)) for a in anos_disponiveis]
        ano_ficha = st.selectbox("Filtrar jogadores por ano (Ano do cadastro):", anos_labels)

        if ano_ficha != "Todos":
            ano_val_ficha = int(ano_ficha)
            players_filtered = players[players["Ano"] == ano_val_ficha].copy()
        else:
            players_filtered = players.copy()

        # Montar lista de jogadores com ID para selectbox
        players_sorted = players_filtered.sort_values("Jogador")

        options = {
            f"{row['Jogador']} ({row['ID']})": row["ID"]
            for _, row in players_sorted.iterrows()
        }

        if not options:
            st.warning("Nenhum jogador encontrado com o filtro de ano selecionado.")
        else:
            label_escolhido = st.selectbox("Selecione o jogador:", list(options.keys()))
            jogador_id_escolhido = options[label_escolhido]

            # Dados do jogador no cadastro (com base no DF completo)
            dados_jogador = players[players["ID"] == jogador_id_escolhido].iloc[0]

            jogador_nome = dados_jogador["Jogador"]
            jogador_pos = dados_jogador["Posição"]
            jogador_ano = dados_jogador["Ano"]

            # ---------- Cálculo dos RANKS ----------
            rank_geral = "-"
            rank_ano = "-"
            rank_pos = "-"

            # Rank geral
            linha_geral = ranking_full[ranking_full["ID"] == jogador_id_escolhido]
            if not linha_geral.empty:
                rank_geral = int(linha_geral.iloc[0]["Rank"])

            # Rank no ano (entre jogadores com mesmo ano)
            if not pd.isna(jogador_ano):
                ranking_ano = ranking_full[ranking_full["Ano"] == jogador_ano].copy()
                if not ranking_ano.empty:
                    ranking_ano = ranking_ano.sort_values("Pontuacao_Total", ascending=False)
                    ranking_ano["Rank_Ano"] = range(1, len(ranking_ano) + 1)
                    linha_ano = ranking_ano[ranking_ano["ID"] == jogador_id_escolhido]
                    if not linha_ano.empty:
                        rank_ano = int(linha_ano.iloc[0]["Rank_Ano"])

            # Rank na posição (entre jogadores da mesma posição em todos os anos)
            if isinstance(jogador_pos, str) and jogador_pos.strip():
                ranking_pos = ranking_full[ranking_full["Posição"] == jogador_pos].copy()
                if not ranking_pos.empty:
                    ranking_pos = ranking_pos.sort_values("Pontuacao_Total", ascending=False)
                    ranking_pos["Rank_Pos"] = range(1, len(ranking_pos) + 1)
                    linha_pos = ranking_pos[ranking_pos["ID"] == jogador_id_escolhido]
                    if not linha_pos.empty:
                        rank_pos = int(linha_pos.iloc[0]["Rank_Pos"])

            # ---------- Cabeçalho da ficha ----------
            col_info1, col_info2, col_info3 = st.columns([2, 1.8, 1.8])
            with col_info1:
                st.markdown(f"**Nome:** {jogador_nome}")
                st.markdown(f"**ID:** {dados_jogador['ID']}")
                st.markdown(f"**Posição:** {jogador_pos}")

            with col_info2:
                ano_str = (
                    str(int(jogador_ano))
                    if not pd.isna(jogador_ano)
                    else "-"
                )
                st.markdown(f"**Ano:** {ano_str}")

                # Campo Status editável
                status_atual = str(dados_jogador.get("Status", "") or "")
                status_opcoes = ["Ativo", "Retirado", "Falecido"]
                if status_atual not in status_opcoes:
                    status_atual = "Ativo"
                novo_status = st.selectbox(
                    "Status:",
                    status_opcoes,
                    index=status_opcoes.index(status_atual),
                )

            with col_info3:
                link = dados_jogador.get("Link", "")
                if isinstance(link, str) and link.strip():
                    st.markdown(f"[🔗 Ver no oGol]({link})")
                else:
                    st.markdown("Sem link cadastrado.")

                # Data da última atualização
                last_update_dict = st.session_state["last_update"]
                if jogador_id_escolhido in last_update_dict:
                    dt = last_update_dict[jogador_id_escolhido]
                    st.markdown(
                        f"**Última atualização nesta sessão:** {dt.strftime('%d/%m/%Y %H:%M')}"
                    )
                else:
                    st.markdown("**Última atualização nesta sessão:** Nunca atualizada.")

            # Linha com os RANKS
            st.markdown("---")
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.markdown(f"**🏅 Rank Geral:** {rank_geral}")
            with col_r2:
                st.markdown(f"**📆 Rank no Ano ({ano_str}):** {rank_ano}")
            with col_r3:
                st.markdown(f"**🎯 Rank na Posição ({jogador_pos}):** {rank_pos}")

            st.markdown("---")

            # Filtrar jogos do jogador (base)
            jogos_jogador = games[games["ID"] == jogador_id_escolhido].copy()

            # --- Pontuação total do jogador ---
            if not jogos_jogador.empty:
                jogos_scored_individual = compute_scores(jogos_jogador, comp)
                pont_total = int(jogos_scored_individual["Score"].sum())
            else:
                pont_total = 0

            st.markdown(f"""
### 🏅 Pontuação Total do Jogador: **{pont_total}**
""")

            st.markdown("### 📋 Lista de Competições / Jogos do Jogador")
            st.markdown(
                "Edite os valores diretamente na tabela abaixo. "
                "Você pode adicionar novas linhas para incluir novas competições."
            )

            # ----- IMPORTANTÍSSIMO: resetar índice para evitar None -----
            jogos_jogador_display = jogos_jogador.reset_index(drop=True)

            # Placeholder para o totalizador acima da tabela
            tot_placeholder = st.empty()

            # Editor de dados
            edited_df = st.data_editor(
                jogos_jogador_display,
                num_rows="dynamic",
                use_container_width=True,
                key="editor_jogador",
            )

            # --- Totalizador da tabela ---
            cols_somar = ["Participações", "Títulos", "Jogos", "Vitórias", "Empates", "Derrotas"]
            cols_existentes = [c for c in cols_somar if c in edited_df.columns]

            if not edited_df.empty and cols_existentes:
                total_row = edited_df[cols_existentes].sum().to_frame().T
                total_row.insert(0, "Competição", "TOTAL GERAL")
                mostrar_cols = ["Competição"] + cols_existentes

                tot_placeholder.dataframe(
                    total_row[mostrar_cols],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                tot_placeholder.info("Nenhum registro para totalizar nesta tabela.")

            st.markdown("### 💾 Salvar alterações")

            col_save1, col_save2 = st.columns([1, 1])

            with col_save1:
                if st.button(
                    "Salvar alterações do jogador e jogos",
                    type="primary",
                ):
                    # ---- Remover linhas totalmente vazias (sem competição) ----
                    if "Competição" in edited_df.columns:
                        edited_df["Competição"] = edited_df["Competição"].astype(str)
                        edited_df = edited_df[
                            edited_df["Competição"].str.strip() != ""
                        ]

                    # ---- Preencher automaticamente Jogador e ID nas novas linhas ----
                    if "Jogador" in edited_df.columns:
                        edited_df["Jogador"] = edited_df["Jogador"].replace("", np.nan)
                        edited_df["Jogador"] = edited_df["Jogador"].fillna(jogador_nome)
                    else:
                        edited_df["Jogador"] = jogador_nome

                    if "ID" in edited_df.columns:
                        edited_df["ID"] = edited_df["ID"].replace("", np.nan)
                        edited_df["ID"] = edited_df["ID"].fillna(jogador_id_escolhido)
                    else:
                        edited_df["ID"] = jogador_id_escolhido

                    # ---- Atualizar STATUS do jogador ----
                    players_df = st.session_state["players"]
                    mask_jog = players_df["ID"] == jogador_id_escolhido
                    players_df.loc[mask_jog, "Status"] = novo_status
                    st.session_state["players"] = players_df

                    # ---- Atualizar jogos do jogador ----
                    df_all = st.session_state["games"]

                    # Remover todas as linhas do jogador atual na base
                    df_all_sem_jogador = df_all[df_all["ID"] != jogador_id_escolhido]

                    # Garantir colunas numéricas
                    for c in ["Participações", "Títulos", "Jogos", "Vitórias", "Empates", "Derrotas"]:
                        if c in edited_df.columns:
                            edited_df[c] = (
                                pd.to_numeric(edited_df[c], errors="coerce")
                                .fillna(0)
                                .astype(int)
                            )

                    # Garantir ID como string
                    edited_df["ID"] = edited_df["ID"].astype(str)

                    # Concatenar de volta
                    st.session_state["games"] = pd.concat(
                        [df_all_sem_jogador, edited_df],
                        ignore_index=True,
                    )

                    # Atualizar "data da última atualização" para este jogador
                    st.session_state["last_update"][jogador_id_escolhido] = datetime.now()

                    # Tentar salvar nos CSVs
                    try:
                        st.session_state["games"].to_csv(GAMES_PATH, index=False)
                        st.session_state["players"].to_csv(PLAYERS_PATH, index=False)
                        st.success(
                            "Alterações salvas na memória e escritas nos CSVs "
                            "(CadastroJogadores e Jogos)."
                        )
                    except Exception as e:
                        st.warning(
                            "Alterações salvas na memória do app, "
                            "mas não foi possível escrever nos arquivos CSV. "
                            "Se estiver rodando na nuvem, faça o download dos CSVs atualizados abaixo."
                        )
                        st.text(f"Detalhe técnico: {e}")

            with col_save2:
                csv_games = st.session_state["games"].to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="⬇️ Baixar CSV de Jogos atualizado",
                    data=csv_games,
                    file_name="São Paulo_Base - Jogos_atualizado.csv",
                    mime="text/csv",
                )

                csv_players = st.session_state["players"].to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="⬇️ Baixar CSV de CadastroJogadores atualizado",
                    data=csv_players,
                    file_name="São Paulo_Base - CadastroJogadores_atualizado.csv",
                    mime="text/csv",
                )

            st.markdown("---")

            # Resumo de pontuação do jogador por competição
            st.markdown("### 📈 Resumo de Pontuação do Jogador (por competição)")

            if not jogos_jogador.empty:
                jogos_scored = compute_scores(jogos_jogador, comp)
                resumo_comp = (
                    jogos_scored.groupby("Competição", as_index=False)
                    .agg(
                        Participações=("Participações", "sum"),
                        Títulos=("Títulos", "sum"),
                        Jogos=("Jogos", "sum"),
                        Vitórias=("Vitórias", "sum"),
                        Empates=("Empates", "sum"),
                        Derrotas=("Derrotas", "sum"),
                        Pontuacao=("Score", "sum"),
                    )
                    .sort_values("Pontuacao", ascending=False)
                )

                # Pontuação inteira
                resumo_comp["Pontuacao"] = resumo_comp["Pontuacao"].round().astype(int)

                st.dataframe(
                    resumo_comp,
                    use_container_width=True,
                    hide_index=True,
                )

                if not resumo_comp.empty:
                    fig2 = px.bar(
                        resumo_comp,
                        x="Competição",
                        y="Pontuacao",
                        hover_data=["Jogos", "Vitórias", "Empates", "Derrotas"],
                    )
                    st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Este jogador ainda não possui registros de jogos no CSV.")

    # -----------------------------------------------------
    # Aba 3 – Competições
    # -----------------------------------------------------
    with tab_comp:
        st.subheader("🏆 Lista de Competições e Pontuações")

        st.markdown(
            "Edite as competições e suas pontuações abaixo. "
            "Você pode adicionar novas linhas para incluir novas competições."
        )

        edited_comp = st.data_editor(
            comp,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_comp",
        )

        col_c1, col_c2 = st.columns([1, 1])

        with col_c1:
            if st.button("Salvar alterações nas competições", type="primary"):
                # Tratar Pontuação (vírgula -> ponto -> número)
                if "Pontuação" in edited_comp.columns:
                    edited_comp["Pontuação"] = (
                        edited_comp["Pontuação"]
                        .astype(str)
                        .str.replace(",", ".", regex=False)
                    )
                    edited_comp["Pontuação"] = pd.to_numeric(
                        edited_comp["Pontuação"],
                        errors="coerce",
                    ).fillna(0.0)

                st.session_state["comp"] = edited_comp

                # Tentar salvar no CSV
                try:
                    st.session_state["comp"].to_csv(COMP_PATH, index=False)
                    st.success("Competições salvas na memória e escritas no CSV.")
                except Exception as e:
                    st.warning(
                        "Competições salvas na memória do app, "
                        "mas não foi possível escrever no arquivo CSV. "
                        "Se estiver rodando na nuvem, faça o download do CSV atualizado abaixo."
                    )
                    st.text(f"Detalhe técnico: {e}")

        with col_c2:
            csv_comp = st.session_state["comp"].to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="⬇️ Baixar CSV de Competições atualizado",
                data=csv_comp,
                file_name="São Paulo_Base - Competições_atualizado.csv",
                mime="text/csv",
            )


if __name__ == "__main__":
    main()

