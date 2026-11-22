# 🎓 Apurador de Notas - UFS

Um painel interativo feito em **Streamlit** para extrair, analisar e simular o desempenho acadêmico a partir do **Relatório de Notas** oficial em PDF emitido pelo SIGAA da Universidade Federal de Sergipe (UFS).

---

## 🚀 Funcionalidades

- **Extração Automática:** Lê o PDF do SIGAA e organiza os períodos letivos, disciplinas, faltas e notas das unidades.
- **🎯 Quanto Falta Para Passar:** Calcula exatamente quantos pontos e qual nota você precisa tirar nas avaliações restantes para atingir sua meta (com editor interativo para personalizar a média alvo e a quantidade de unidades por matéria).
- **📋 Resumo e Métricas:** Média geral do curso, média parcial do período em andamento, total de disciplinas concluídas e taxa de aprovações/reprovações.
- **📊 Visualizações Interativas:**
  - Gráfico de notas por período comparadas com a meta.
  - Linha do tempo da evolução da média semestral.
  - Gráfico de pizza com a distribuição das notas por faixa de desempenho.

---

## 🛠️ Tecnologias Utilizadas

- **[Python](https://www.python.org/)** (Linguagem base)
- **[Streamlit](https://streamlit.io/)** (Interface web e reatividade)
- **[pdfplumber](https://github.com/jsvine/pdfplumber)** (Leitura e extração das tabelas do PDF)
- **[Pandas](https://pandas.pydata.org/)** & **[NumPy](https://numpy.org/)** (Tratamento e cálculo de dados)
- **[Plotly](https://plotly.com/python/)** (Gráficos interativos)

---

## 💻 Como Executar

### 1. Pré-requisitos
Certifique-se de ter o **Python 3.10+** instalado em seu computador.

### 2. Instalação

Abra o terminal na pasta do projeto e instale as dependências:

```bash
pip install -r requirements.txt
```

### 3. Rodar a Aplicação

Inicie o servidor local do Streamlit:

```bash
streamlit run app.py
```

O navegador abrirá automaticamente em `http://localhost:8501`. Basta enviar o seu PDF do SIGAA e acompanhar seus resultados!
