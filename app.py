import streamlit as st
import openai
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configuração da página
st.set_page_config(
    page_title="Assistente Financeiro IA",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------- CONFIGURAÇÃO DA API -------------------
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    st.error("❌ Chave da OpenAI não encontrada. Defina OPENAI_API_KEY no arquivo .env ou como variável de ambiente.")
    st.stop()

# ------------------- FUNÇÕES AUXILIARES -------------------
def calcular_juros_compostos(valor_inicial, taxa_mensal, meses):
    """Calcula montante e juros compostos"""
    if taxa_mensal < 0 or meses < 0:
        return None
    montante = valor_inicial * (1 + taxa_mensal / 100) ** meses
    juros = montante - valor_inicial
    return montante, juros

def calcular_parcela_price(valor, taxa_juros_anual, parcelas):
    """Cálculo da parcela fixa (Sistema Price)"""
    if taxa_juros_anual == 0:
        return valor / parcelas
    i_mensal = (1 + taxa_juros_anual / 100) ** (1/12) - 1
    parcela = valor * (i_mensal * (1 + i_mensal) ** parcelas) / ((1 + i_mensal) ** parcelas - 1)
    return parcela

def gerar_tabela_sac(valor, taxa_juros_anual, parcelas):
    """Tabela de amortização SAC (Sistema de Amortização Constante)"""
    if taxa_juros_anual == 0:
        amort = valor / parcelas
        saldo = valor
        parcelas_lista = []
        for i in range(1, parcelas + 1):
            juros = 0
            parcela = amort
            saldo -= amort
            parcelas_lista.append([i, parcela, juros, amort, max(0, saldo)])
        return pd.DataFrame(parcelas_lista, columns=["Parcela", "Parcela", "Juros", "Amortização", "Saldo"])
    i_mensal = (1 + taxa_juros_anual / 100) ** (1/12) - 1
    amort = valor / parcelas
    saldo = valor
    parcelas_lista = []
    for i in range(1, parcelas + 1):
        juros = saldo * i_mensal
        parcela = amort + juros
        saldo -= amort
        parcelas_lista.append([i, parcela, juros, amort, max(0, saldo)])
    return pd.DataFrame(parcelas_lista, columns=["Parcela", "Parcela", "Juros", "Amortização", "Saldo"])

def gerar_tabela_price(valor, taxa_juros_anual, parcelas):
    """Tabela de amortização Price (parcela fixa)"""
    if taxa_juros_anual == 0:
        parcela_fixa = valor / parcelas
        saldo = valor
        parcelas_lista = []
        for i in range(1, parcelas + 1):
            juros = 0
            amort = parcela_fixa
            saldo -= amort
            parcelas_lista.append([i, parcela_fixa, juros, amort, max(0, saldo)])
        return pd.DataFrame(parcelas_lista, columns=["Parcela", "Parcela", "Juros", "Amortização", "Saldo"])
    i_mensal = (1 + taxa_juros_anual / 100) ** (1/12) - 1
    parcela_fixa = valor * (i_mensal * (1 + i_mensal) ** parcelas) / ((1 + i_mensal) ** parcelas - 1)
    saldo = valor
    parcelas_lista = []
    for i in range(1, parcelas + 1):
        juros = saldo * i_mensal
        amort = parcela_fixa - juros
        saldo -= amort
        parcelas_lista.append([i, parcela_fixa, juros, amort, max(0, saldo)])
    return pd.DataFrame(parcelas_lista, columns=["Parcela", "Parcela", "Juros", "Amortização", "Saldo"])

def chat_completion(messages):
    """Chama a API do ChatGPT com histórico"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=800,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Erro na API: {str(e)}"

# ------------------- INICIALIZAÇÃO DE ESTADO -------------------
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Olá! Sou seu assistente financeiro IA. 💰\n\nPosso ajudar com:\n• Dúvidas sobre produtos bancários\n• Simulações de investimentos\n• Cálculo de empréstimos e parcelas\n• Educação financeira\n• Comparação de investimentos\n\nComo posso te ajudar hoje?"
    }]

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = datetime.now().strftime("%Y%m%d%H%M%S")

# ------------------- SIDEBAR -------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
    st.title("💰 Assistente Financeiro")
    st.markdown("---")
    
    # Informações do usuário
    st.markdown("### 📌 Sobre")
    st.info("Este assistente usa IA generativa para responder perguntas sobre finanças e realizar cálculos. Lembre-se: as informações são apenas educativas.")
    
    st.markdown("---")
    st.markdown("### 🛠️ Configurações")
    
    # Exibir status da API
    if openai.api_key:
        st.success("✅ API conectada")
    else:
        st.error("❌ API não configurada")
    
    # Botão limpar conversa
    if st.button("🗑️ Limpar conversa", use_container_width=True):
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Conversa reiniciada. Como posso ajudar?"
        }]
        st.rerun()
    
    st.markdown("---")
    st.caption("⚠️ Este assistente não oferece conselhos financeiros profissionais. Consulte um especialista antes de tomar decisões.")

# ------------------- MAIN PAGE (TABS) -------------------
tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat Inteligente", "📊 Calculadoras", "📚 Conhecimento", "📈 Comparador de Investimentos"])

# ------------------- TAB 1: CHAT -------------------
with tab1:
    st.header("💬 Assistente Financeiro")
    st.markdown("Faça perguntas sobre finanças, investimentos, ou peça simulações.")
    
    # Container para mensagens
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                st.chat_message("assistant").write(msg["content"])
    
    # Entrada de texto
    if prompt := st.chat_input("Digite sua pergunta..."):
        # Adiciona mensagem do usuário
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            st.chat_message("user").write(prompt)
        
        # Prepara histórico (últimas 10 mensagens para contexto)
        history = st.session_state.messages[-10:]
        # Ajusta para formato da API
        messages = [{"role": m["role"], "content": m["content"]} for m in history]
        
        # Adiciona contexto de sistema
        system_message = {
            "role": "system",
            "content": """Você é um assistente financeiro especializado. Siga as diretrizes:
- Responda de forma clara, didática e amigável.
- Sempre mencione que não é um conselho financeiro profissional.
- Para cálculos, use exemplos práticos.
- Se o usuário pedir simulações, indique que pode usar as calculadoras na aba 'Calculadoras'.
- Seja conciso e objetivo, mas completo.
- Nunca forneça informações falsas ou enganosas."""
        }
        messages.insert(0, system_message)
        
        with st.spinner("Gerando resposta..."):
            resposta = chat_completion(messages)
        
        # Adiciona resposta
        st.session_state.messages.append({"role": "assistant", "content": resposta})
        with chat_container:
            st.chat_message("assistant").write(resposta)
        
        st.rerun()

# ------------------- TAB 2: CALCULADORAS -------------------
with tab2:
    st.header("📊 Calculadoras Financeiras")
    
    # Opção de calculadora
    calc_type = st.selectbox(
        "Escolha a calculadora",
        ["Juros Compostos", "Parcelamento Price", "Parcelamento SAC", "Meta de Investimento"]
    )
    
    if calc_type == "Juros Compostos":
        st.subheader("📈 Calculadora de Juros Compostos")
        col1, col2, col3 = st.columns(3)
        with col1:
            valor = st.number_input("Valor inicial (R$)", min_value=0.0, value=1000.0, step=100.0)
        with col2:
            taxa = st.number_input("Taxa mensal (%)", min_value=0.0, value=1.0, step=0.1)
        with col3:
            meses = st.number_input("Período (meses)", min_value=1, value=12, step=1)
        
        if st.button("Calcular", key="btn_compostos"):
            montante, juros = calcular_juros_compostos(valor, taxa, meses)
            if montante is None:
                st.error("Valores inválidos")
            else:
                st.success(f"**Montante final:** R$ {montante:,.2f}")
                st.success(f"**Rendimento total:** R$ {juros:,.2f}")
                st.success(f"**Rentabilidade:** {(juros/valor*100):.2f}%")
                
                # Gráfico
                meses_list = list(range(1, meses+1))
                montantes = [calcular_juros_compostos(valor, taxa, m)[0] for m in meses_list]
                fig, ax = plt.subplots()
                ax.plot(meses_list, montantes, marker='o')
                ax.set_title("Crescimento do Investimento")
                ax.set_xlabel("Meses")
                ax.set_ylabel("Montante (R$)")
                ax.grid(True)
                st.pyplot(fig)
                
                # Adicionar ao chat?
                if st.button("Enviar resultado para o chat"):
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"📈 **Simulação de juros compostos:** Com R$ {valor:,.2f} a {taxa}% a.m. por {meses} meses, você teria R$ {montante:,.2f} (rendimento R$ {juros:,.2f})."
                    })
                    st.success("Resultado enviado ao chat!")
    
    elif calc_type == "Parcelamento Price":
        st.subheader("💳 Simulação de Parcelamento (Price)")
        col1, col2, col3 = st.columns(3)
        with col1:
            valor = st.number_input("Valor da compra (R$)", min_value=0.0, value=1000.0, step=100.0)
        with col2:
            taxa_anual = st.number_input("Taxa de juros anual (%)", min_value=0.0, value=12.0, step=1.0)
        with col3:
            parcelas = st.number_input("Número de parcelas", min_value=1, value=6, step=1)
        
        if st.button("Calcular Price"):
            parcela = calcular_parcela_price(valor, taxa_anual, parcelas)
            total = parcela * parcelas
            st.success(f"**Parcela fixa:** R$ {parcela:,.2f}")
            st.success(f"**Total pago:** R$ {total:,.2f}")
            st.success(f"**Juros totais:** R$ {total - valor:,.2f}")
            
            # Tabela de amortização
            df = gerar_tabela_price(valor, taxa_anual, parcelas)
            st.dataframe(df.style.format({"Parcela": "R$ {:.2f}", "Juros": "R$ {:.2f}", "Amortização": "R$ {:.2f}", "Saldo": "R$ {:.2f}"}))
    
    elif calc_type == "Parcelamento SAC":
        st.subheader("🏦 Simulação de Parcelamento (SAC)")
        col1, col2, col3 = st.columns(3)
        with col1:
            valor = st.number_input("Valor do empréstimo (R$)", min_value=0.0, value=100000.0, step=10000.0)
        with col2:
            taxa_anual = st.number_input("Taxa de juros anual (%)", min_value=0.0, value=10.0, step=0.5)
        with col3:
            parcelas = st.number_input("Número de parcelas", min_value=1, value=120, step=12)
        
        if st.button("Calcular SAC"):
            df = gerar_tabela_sac(valor, taxa_anual, parcelas)
            st.dataframe(df.style.format({"Parcela": "R$ {:.2f}", "Juros": "R$ {:.2f}", "Amortização": "R$ {:.2f}", "Saldo": "R$ {:.2f}"}))
            # Resumo
            total_juros = df["Juros"].sum()
            total_pago = valor + total_juros
            st.info(f"**Total de juros:** R$ {total_juros:,.2f}")
            st.info(f"**Total a pagar:** R$ {total_pago:,.2f}")
    
    elif calc_type == "Meta de Investimento":
        st.subheader("🎯 Quanto preciso investir por mês para atingir minha meta?")
        col1, col2, col3 = st.columns(3)
        with col1:
            meta = st.number_input("Meta (R$)", min_value=0.0, value=50000.0, step=1000.0)
        with col2:
            taxa_anual_meta = st.number_input("Taxa de retorno anual (%)", min_value=0.0, value=12.0, step=0.5)
        with col3:
            anos = st.number_input("Período (anos)", min_value=1, value=5, step=1)
        
        if st.button("Calcular aporte mensal"):
            # Converter taxa anual para mensal
            taxa_mensal = (1 + taxa_anual_meta / 100) ** (1/12) - 1
            meses = anos * 12
            # Fórmula do valor futuro de uma série de pagamentos:
            # FV = PMT * ((1 + i)^n - 1) / i
            # PMT = FV * i / ((1 + i)^n - 1)
            if taxa_mensal == 0:
                aporte = meta / meses
            else:
                aporte = meta * taxa_mensal / ((1 + taxa_mensal) ** meses - 1)
            st.success(f"**Aporte mensal necessário:** R$ {aporte:,.2f}")
            st.info(f"Total investido: R$ {aporte * meses:,.2f} | Rendimento esperado: R$ {meta - aporte * meses:,.2f}")

# ------------------- TAB 3: CONHECIMENTO -------------------
with tab3:
    st.header("📚 Conhecimento Financeiro")
    st.markdown("Aprenda os conceitos básicos com a ajuda da IA. Pergunte sobre qualquer tema!")
    
    tema = st.text_input("Sobre o que você quer aprender? (ex: CDB, Tesouro Direto, Ações)")
    if st.button("Explicar", key="btn_knowledge"):
        if tema.strip():
            with st.spinner("Gerando explicação..."):
                messages = [
                    {"role": "system", "content": "Você é um especialista em finanças. Explique de forma clara e didática, como se fosse para um iniciante."},
                    {"role": "user", "content": f"Explique o que é {tema} e como funciona."}
                ]
                resposta = chat_completion(messages)
            st.write(resposta)
        else:
            st.warning("Digite um tema.")

# ------------------- TAB 4: COMPARADOR DE INVESTIMENTOS -------------------
with tab4:
    st.header("📈 Comparador de Investimentos")
    st.markdown("Compare o rendimento de diferentes opções de investimento.")
    
    investimentos = st.multiselect(
        "Escolha até 3 investimentos para comparar",
        ["Poupança", "CDB 100% CDI", "Tesouro Selic", "Tesouro IPCA+", "Fundos DI", "Ações (Ibovespa)"],
        default=["Poupança", "CDB 100% CDI", "Tesouro Selic"]
    )
    
    col1, col2 = st.columns(2)
    with col1:
        valor_inicial_comp = st.number_input("Valor inicial (R$)", min_value=0.0, value=1000.0, step=100.0)
    with col2:
        prazo_meses = st.number_input("Prazo (meses)", min_value=1, value=12, step=1)
    
    # Taxas aproximadas (exemplo)
    taxas = {
        "Poupança": 0.5,  # ao mês
        "CDB 100% CDI": 1.0,
        "Tesouro Selic": 1.0,
        "Tesouro IPCA+": 0.8,
        "Fundos DI": 0.9,
        "Ações (Ibovespa)": 1.2
    }
    
    if st.button("Comparar", key="btn_compare"):
        resultados = []
        for inv in investimentos:
            taxa = taxas.get(inv, 0.5)
            montante, juros = calcular_juros_compostos(valor_inicial_comp, taxa, prazo_meses)
            resultados.append({
                "Investimento": inv,
                "Taxa mensal (%)": taxa,
                "Montante final (R$)": montante,
                "Rendimento (R$)": juros
            })
        df_resultados = pd.DataFrame(resultados)
        st.dataframe(df_resultados.style.format({"Montante final (R$)": "R$ {:.2f}", "Rendimento (R$)": "R$ {:.2f}"}))
        
        # Gráfico
        fig, ax = plt.subplots()
        ax.bar(df_resultados["Investimento"], df_resultados["Montante final (R$)"], color=['gold', 'blue', 'green'])
        ax.set_title("Comparação de Investimentos")
        ax.set_ylabel("Montante final (R$)")
        st.pyplot(fig)

# ------------------- FOOTER -------------------
st.markdown("---")
st.caption("Assistente Financeiro IA | Desenvolvido com Streamlit e OpenAI | Última atualização: Março/2025")
