import os
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="TR - Sistema de Cotações | Transresíduos", layout="wide"
)


# ==========================================
# 1. CARREGAR E UNIFICAR BASES DE FORNECEDORES
# ==========================================
@st.cache_data
def carregar_todos_fornecedores():
    dfs = []

    # 1. Regime Normal
    if os.path.exists("fornecedores_regime_normal .xlsx"):
        df_norm = pd.read_excel("fornecedores_regime_normal .xlsx")
        df_norm["cnpj_cpf"] = df_norm.get("Unnamed: 5", df_norm.get("cnpj_cpf"))
        df_norm["regime_tributario"] = "Lucro Real / Presumido (Regime Regular)"
        dfs.append(
            df_norm[
                [
                    "codigo",
                    "nome_fantasia",
                    "razao_social",
                    "regime_tributario",
                    "cnpj_cpf",
                ]
            ]
        )

    # 2. Simples Nacional
    if os.path.exists("fornecedores_simples_nacional.xlsx"):
        df_simp = pd.read_excel("fornecedores_simples_nacional.xlsx")
        df_simp["regime_tributario"] = "Simples Nacional - Tradicional"
        dfs.append(
            df_simp[
                [
                    "codigo",
                    "nome_fantasia",
                    "razao_social",
                    "regime_tributario",
                    "cnpj_cpf",
                ]
            ]
        )

    # 3. MEI
    if os.path.exists("fornecedores_mei .xlsx"):
        df_mei = pd.read_excel("fornecedores_mei .xlsx")
        df_mei["regime_tributario"] = "MEI"
        dfs.append(
            df_mei[
                [
                    "codigo",
                    "nome_fantasia",
                    "razao_social",
                    "regime_tributario",
                    "cnpj_cpf",
                ]
            ]
        )

    if dfs:
        df_unificado = pd.concat(dfs, ignore_index=True)
        df_unificado.drop_duplicates(subset=["nome_fantasia"], inplace=True)
        return df_unificado
    else:
        st.error("Nenhum arquivo de fornecedor encontrado na pasta do projeto.")
        return pd.DataFrame()


df_fornecedores = carregar_todos_fornecedores()

# ==========================================
# 2. CABEÇALHO DO SISTEMA
# ==========================================
st.title("📦 TR - Sistema de Cotações | Transresíduos")
st.caption(
    "Comparativo Inteligente por Custo Efetivo (Considerando repasse de créditos IBS/CBS)"
)

# ==========================================
# 3. FILTRO E CONSULTA DE FORNECEDORES
# ==========================================
with st.expander(
    f"🔍 Consultar Cadastros ({len(df_fornecedores)} Fornecedores Unificados)",
    expanded=False,
):
    termo_busca = st.text_input(
        "Buscar fornecedor por Nome, Razão Social ou CNPJ:",
        key="key_busca_fornecedor",
    )
    if not df_fornecedores.empty:
        df_exibir = df_fornecedores.copy()
        if termo_busca:
            mask = (
                df_exibir["nome_fantasia"]
                .astype(str)
                .str.contains(termo_busca, case=False, na=False)
                | df_exibir["razao_social"]
                .astype(str)
                .str.contains(termo_busca, case=False, na=False)
                | df_exibir["cnpj_cpf"]
                .astype(str)
                .str.contains(termo_busca, case=False, na=False)
            )
            df_exibir = df_exibir[mask]
        st.dataframe(df_exibir, use_container_width=True)

# ==========================================
# 4. PARÂMETROS TRIBUTÁRIOS (SIDEBAR)
# ==========================================
st.sidebar.header("⚙️ Alíquotas IBS / CBS")
aliq_cheia = (
    st.sidebar.number_input(
        "Alíquota Cheia (Regime Regular / Híbrido %)",
        value=26.5,
        step=0.5,
        key="key_aliq_cheia",
    )
    / 100
)
aliq_simples_red = (
    st.sidebar.number_input(
        "Alíquota Média Repasse Simples (%)",
        value=3.5,
        step=0.5,
        key="key_aliq_simples",
    )
    / 100
)

# ==========================================
# 5. FORMULÁRIO DE COTAÇÃO
# ==========================================
st.subheader("📋 Nova Cotação de Compra")

lista_fornecedores = (
    ["Selecione..."]
    + sorted(df_fornecedores["nome_fantasia"].dropna().tolist())
    if not df_fornecedores.empty
    else ["Selecione..."]
)

opcoes_regime = [
    "Lucro Real / Presumido (Regime Regular)",
    "Simples Nacional — Híbrido (Crédito Cheio)",
    "Simples Nacional - Tradicional",
    "MEI",
]

col1, col2, col3 = st.columns(3)


def render_coluna_fornecedor(num, col):
    with col:
        st.markdown(f"### Fornecedor 0{num}")
        nome = st.selectbox(
            f"Selecione o Fornecedor {num}",
            options=lista_fornecedores,
            key=f"key_f{num}",
        )

        regime_padrao = opcoes_regime[0]
        if nome != "Selecione...":
            r_encontrado = df_fornecedores.loc[
                df_fornecedores["nome_fantasia"] == nome, "regime_tributario"
            ].values
            if len(r_encontrado) > 0 and r_encontrado[0] in opcoes_regime:
                regime_padrao = r_encontrado[0]

        idx_padrao = (
            opcoes_regime.index(regime_padrao)
            if regime_padrao in opcoes_regime
            else 0
        )

        regime = st.selectbox(
            f"Regime Tributário F{num}",
            options=opcoes_regime,
            index=idx_padrao,
            key=f"key_r{num}",
        )
        preco = st.number_input(
            f"Preço Bruto F{num} (R$)",
            min_value=0.0,
            step=10.0,
            key=f"key_p{num}",
        )
        prazo = st.number_input(
            f"Prazo F{num} (dias)", min_value=0, step=1, key=f"key_pz{num}"
        )

        return nome, regime, preco, prazo


f1, r1, p1, pz1 = render_coluna_fornecedor(1, col1)
f2, r2, p2, pz2 = render_coluna_fornecedor(2, col2)
f3, r3, p3, pz3 = render_coluna_fornecedor(3, col3)

# ==========================================
# 6. CÁLCULO E ANÁLISE DE MELHOR OPÇÃO
# ==========================================
if st.button(
    "📊 Gerar Comparativo de Cotação",
    type="primary",
    key="key_btn_comparativo",
):
    dados = []
    for nome, regime, preco, prazo in [
        (f1, r1, p1, pz1),
        (f2, r2, p2, pz2),
        (f3, r3, p3, pz3),
    ]:
        if nome != "Selecione..." and preco > 0:
            # Cálculo de Crédito
            if regime in [
                "Lucro Real / Presumido (Regime Regular)",
                "Simples Nacional — Híbrido (Crédito Cheio)",
            ]:
                credito_pct = aliq_cheia
            elif regime == "Simples Nacional - Tradicional":
                credito_pct = aliq_simples_red
            else:  # MEI
                credito_pct = 0.0

            val_credito = preco * credito_pct
            custo_efetivo = preco - val_credito

            cnpj = df_fornecedores.loc[
                df_fornecedores["nome_fantasia"] == nome, "cnpj_cpf"
            ].values
            cnpj_str = cnpj[0] if len(cnpj) > 0 else "-"

            dados.append({
                "Fornecedor": nome,
                "CNPJ/CPF": cnpj_str,
                "Regime": regime,
                "Preço Bruto (R$)": f"R$ {preco:,.2f}",
                "Crédito Imposto (R$)": f"R$ {val_credito:,.2f}",
                "Custo Efetivo Líquido (R$)": f"R$ {custo_efetivo:,.2f}",
                "Prazo": f"{prazo} dias",
                "Custo_Num": custo_efetivo,
            })

    if dados:
        resumo_df = pd.DataFrame(dados)
        st.subheader("📋 Comparativo Tributário e Custo Real")
        st.table(resumo_df.drop(columns=["Custo_Num"]))

        vencedor = min(dados, key=lambda x: x["Custo_Num"])
        st.success(
            f"🏆 **Melhor Opção de Compra:** {vencedor['Fornecedor']} ({vencedor['Regime']})\n\n"
            f"• **Preço Bruto:** {vencedor['Preço Bruto (R$)']} | **Crédito Gerado:** {vencedor['Crédito Imposto (R$)']} | **Custo Real Líquido:** **{vencedor['Custo Efetivo Líquido (R$)']}**"
        )
    else:
        st.warning(
     import os
            "Selecione os fornecedores e informe os preços para calcular a melhor opção."import os
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="TR - Sistema de Cotações | Transresíduos", layout="wide"
)


# ==========================================
# 1. CARREGAR E UNIFICAR BASES DE FORNECEDORES
# ==========================================
@st.cache_data
def carregar_todos_fornecedores():
    dfs = []

    # 1. Regime Normal
    if os.path.exists("fornecedores_regime_normal .xlsx"):
        df_norm = pd.read_excel("fornecedores_regime_normal .xlsx")
        df_norm["cnpj_cpf"] = df_norm.get("Unnamed: 5", df_norm.get("cnpj_cpf"))
        df_norm["regime_tributario"] = "Lucro Real / Presumido (Regime Regular)"
        dfs.append(
            df_norm[
                [
                    "codigo",
                    "nome_fantasia",
                    "razao_social",
                    "regime_tributario",
                    "cnpj_cpf",
                ]
            ]
        )

    # 2. Simples Nacional
    if os.path.exists("fornecedores_simples_nacional.xlsx"):
        df_simp = pd.read_excel("fornecedores_simples_nacional.xlsx")
        df_simp["regime_tributario"] = "Simples Nacional - Tradicional"
        dfs.append(
            df_simp[
                [
                    "codigo",
                    "nome_fantasia",
                    "razao_social",
                    "regime_tributario",
                    "cnpj_cpf",
                ]
            ]
        )

    # 3. MEI
    if os.path.exists("fornecedores_mei .xlsx"):
        df_mei = pd.read_excel("fornecedores_mei .xlsx")
        df_mei["regime_tributario"] = "MEI"
        dfs.append(
            df_mei[
                [
                    "codigo",
                    "nome_fantasia",
                    "razao_social",
                    "regime_tributario",
                    "cnpj_cpf",
                ]
            ]
        )

    if dfs:
        df_unificado = pd.concat(dfs, ignore_index=True)
        df_unificado.drop_duplicates(subset=["nome_fantasia"], inplace=True)
        return df_unificado
    else:
        st.error("Nenhum arquivo de fornecedor encontrado na pasta do projeto.")
        return pd.DataFrame()


df_fornecedores = carregar_todos_fornecedores()

# ==========================================
# 2. CABEÇALHO DO SISTEMA
# ==========================================
st.title("📦 TR - Sistema de Cotações | Transresíduos")
st.caption(
    "Comparativo Inteligente por Custo Efetivo (Considerando repasse de créditos IBS/CBS)"
)

# ==========================================
# 3. FILTRO E CONSULTA DE FORNECEDORES
# ==========================================
with st.expander(
    f"🔍 Consultar Cadastros ({len(df_fornecedores)} Fornecedores Unificados)",
    expanded=False,
):
    termo_busca = st.text_input(
        "Buscar fornecedor por Nome, Razão Social ou CNPJ:",
        key="key_busca_fornecedor",
    )
    if not df_fornecedores.empty:
        df_exibir = df_fornecedores.copy()
        if termo_busca:
            mask = (
                df_exibir["nome_fantasia"]
                .astype(str)
                .str.contains(termo_busca, case=False, na=False)
                | df_exibir["razao_social"]
                .astype(str)
                .str.contains(termo_busca, case=False, na=False)
                | df_exibir["cnpj_cpf"]
                .astype(str)
                .str.contains(termo_busca, case=False, na=False)
            )
            df_exibir = df_exibir[mask]
        st.dataframe(df_exibir, use_container_width=True)

# ==========================================
# 4. PARÂMETROS TRIBUTÁRIOS (SIDEBAR)
# ==========================================
st.sidebar.header("⚙️ Alíquotas IBS / CBS")
aliq_cheia = (
    st.sidebar.number_input(
        "Alíquota Cheia (Regime Regular / Híbrido %)",
        value=26.5,
        step=0.5,
        key="key_aliq_cheia",
    )
    / 100
)
aliq_simples_red = (
    st.sidebar.number_input(
        "Alíquota Média Repasse Simples (%)",
        value=3.5,
        step=0.5,
        key="key_aliq_simples",
    )
    / 100
)

# ==========================================
# 5. FORMULÁRIO DE COTAÇÃO
# ==========================================
st.subheader("📋 Nova Cotação de Compra")

lista_fornecedores = (
    ["Selecione..."]
    + sorted(df_fornecedores["nome_fantasia"].dropna().tolist())
    if not df_fornecedores.empty
    else ["Selecione..."]
)

opcoes_regime = [
    "Lucro Real / Presumido (Regime Regular)",
    "Simples Nacional — Híbrido (Crédito Cheio)",
    "Simples Nacional - Tradicional",
    "MEI",
]

col1, col2, col3 = st.columns(3)


def render_coluna_fornecedor(num, col):
    with col:
        st.markdown(f"### Fornecedor 0{num}")
        nome = st.selectbox(
            f"Selecione o Fornecedor {num}",
            options=lista_fornecedores,
            key=f"key_f{num}",
        )

        regime_padrao = opcoes_regime[0]
        if nome != "Selecione...":
            r_encontrado = df_fornecedores.loc[
                df_fornecedores["nome_fantasia"] == nome, "regime_tributario"
            ].values
            if len(r_encontrado) > 0 and r_encontrado[0] in opcoes_regime:
                regime_padrao = r_encontrado[0]

        idx_padrao = (
            opcoes_regime.index(regime_padrao)
            if regime_padrao in opcoes_regime
            else 0
        )

        regime = st.selectbox(
            f"Regime Tributário F{num}",
            options=opcoes_regime,
            index=idx_padrao,
            key=f"key_r{num}",
        )
        preco = st.number_input(
            f"Preço Bruto F{num} (R$)",
            min_value=0.0,
            step=10.0,
            key=f"key_p{num}",
        )
        prazo = st.number_input(
            f"Prazo F{num} (dias)", min_value=0, step=1, key=f"key_pz{num}"
        )

        return nome, regime, preco, prazo


f1, r1, p1, pz1 = render_coluna_fornecedor(1, col1)
f2, r2, p2, pz2 = render_coluna_fornecedor(2, col2)
f3, r3, p3, pz3 = render_coluna_fornecedor(3, col3)

# ==========================================
# 6. CÁLCULO E ANÁLISE DE MELHOR OPÇÃO
# ==========================================
if st.button(
    "📊 Gerar Comparativo de Cotação",
    type="primary",
    key="key_btn_comparativo",
):
    dados = []
    for nome, regime, preco, prazo in [
        (f1, r1, p1, pz1),
        (f2, r2, p2, pz2),
        (f3, r3, p3, pz3),
    ]:
        if nome != "Selecione..." and preco > 0:
            # Cálculo de Crédito
            if regime in [
                "Lucro Real / Presumido (Regime Regular)",
                "Simples Nacional — Híbrido (Crédito Cheio)",
            ]:
                credito_pct = aliq_cheia
            elif regime == "Simples Nacional - Tradicional":
                credito_pct = aliq_simples_red
            else:  # MEI
                credito_pct = 0.0

            val_credito = preco * credito_pct
            custo_efetivo = preco - val_credito

            cnpj = df_fornecedores.loc[
                df_fornecedores["nome_fantasia"] == nome, "cnpj_cpf"
            ].values
            cnpj_str = cnpj[0] if len(cnpj) > 0 else "-"

            dados.append({
                "Fornecedor": nome,
                "CNPJ/CPF": cnpj_str,
                "Regime": regime,
                "Preço Bruto (R$)": f"R$ {preco:,.2f}",
                "Crédito Imposto (R$)": f"R$ {val_credito:,.2f}",
                "Custo Efetivo Líquido (R$)": f"R$ {custo_efetivo:,.2f}",
                "Prazo": f"{prazo} dias",
                "Custo_Num": custo_efetivo,
            })

    if dados:
        resumo_df = pd.DataFrame(dados)
        st.subheader("📋 Comparativo Tributário e Custo Real")
        st.table(resumo_df.drop(columns=["Custo_Num"]))

        vencedor = min(dados, key=lambda x: x["Custo_Num"])
        st.success(
            f"🏆 **Melhor Opção de Compra:** {vencedor['Fornecedor']} ({vencedor['Regime']})\n\n"
            f"• **Preço Bruto:** {vencedor['Preço Bruto (R$)']} | **Crédito Gerado:** {vencedor['Crédito Imposto (R$)']} | **Custo Real Líquido:** **{vencedor['Custo Efetivo Líquido (R$)']}**"
        )
    else:
        st.warning(
            "Selecione os fornecedores e informe os preços para calcular a melhor opção."
        )
        )
