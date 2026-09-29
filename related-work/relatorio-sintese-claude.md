# Ideias Interessantes a partir dos Trabalhos Correlatos

Levantamento das catorze monografias prévias da USP reunidas em `related-work/`. Esta versão substitui as anteriores e foi produzida a partir de **leitura direta dos PDFs** (capa, sumário, seções de metodologia, tabelas de resultados e conclusões), cruzando os relatórios paralelos `intersting-ideas-codex.md`, `intersting-ideas-kimi.md`, `relatorio-sintese-deepseek.md`, `analise-integracao-monografia.md` e `filtros-adicionais-implementaveis.md`. Cada afirmação numérica abaixo foi conferida contra o respectivo PDF — divergências encontradas nos relatórios paralelos são apontadas explicitamente.

Este TCC: *Algorithmic Trading Enhanced by AI: Using News, Geopolitical Events and NLP-Based Sentiment in Forex Decision-Making* — pares EUR/USD e USD/JPY, janela 2015-02-19 a 2024-12-31, estratégia híbrida com perception agêntica + execução determinística, avaliação CPCV + walk-forward. Cadeia atual: 7 filtros (F1–F7) já especificados na Seção 3.7 da monografia.

Legenda — relevância para esta monografia: **★★★** precedente direto, citação obrigatória; **★★** método ou filtro transferível; **★** inspiração geral / referência opcional.

---

## 1. Trabalhos correlatos por relevância

### ★★★ Claudinei Felix — `Claudinei_Felix.pdf`

**Ficha verificada.** *Explorando a Inteligência Artificial na Previsão de Tendências e Preços no Contexto do Swing Trading: Um Estudo de Caso para Aprimorar Estratégias de Investimento.* ICMC/USP, MBA IA & Big Data, 2024 (40 páginas). Orientadora: Prof.ª Dr.ª Marislei Nishijima. Ficha catalográfica S856m.

**O que faz.** Treina sete classificadores (SVM, XGB, GaussianNB, KNN, SGDClassifier, LGBM, MLP) sobre o IBrX-100 entre 2014-08 e 2024-08, com teste em 2022-01 a 2024-01. Features: ~98 indicadores técnicos por ativo (IFR, MACD, MMA, MME, Heikin-Ashi — fórmulas explícitas p. 27-28) mais oito padrões de candlestick; PCA preservando 95 % da variância; rotulagem manual buy/sell/abstain.

**Resultados (Tabela 10, p. 34, conferidos algarismo por algarismo).**

| Classificador | Melhor configuração | Precisão | Recall | ROC-AUC | Tempo (s) |
|---|---|---|---|---|---|
| **LGBM** | max_depth = 16 | **0,948** | **0,969** | **0,986** | **0,897** |
| XGB | n_estimators=1000, max_depth=10 | 0,946 | 0,969 | 0,985 | 6,805 |
| MLP | 5 camadas | 0,907 | 0,923 | 0,967 | 4,594 |
| SVM | Kernel RBF, gamma auto | 0,867 | 0,907 | 0,940 | 12,679 |
| KNN | K = 9 | 0,814 | 0,893 | 0,895 | 0,143 |
| SGDClassifier | sgd_squared_error_10 | 0,820 | 0,813 | 0,888 | 0,203 |
| GaussianNB | Var smoothing 1e-5 | 0,733 | 0,919 | 0,776 | 0,020 |

LGBM vs. XGB: ROC-AUC 0,986 vs. 0,985 (empate prático), tempo 0,897 s vs. 6,805 s — **LGBM ≈ 7,6× mais rápido** (não 6×, como aparece em DeepSeek e integracao). Justifica a escolha LGBM no meta-learner do presente TCC, especialmente sob o regime CPCV que exige múltiplos refits.

**Citação-chave (Resumo, p. 7, verbatim).** *"Operadores neste mercado utilizam duas abordagens principais como parâmetros para compras ou vendas na sua tomada de decisão. O método de análise técnica/gráfica usa o preço histórico das ações-alvo... O segundo tipo de análise é qualitativa, envolve métricas mais difíceis de quantificar, como perfil da empresa, situação do mercado, fatores políticos e econômicos, informações textuais na forma de novos artigos financeiros, mídias sociais e até publicações de analistas econômicos."*

Felix **reconhece** a classe "informação textual" como input legítimo e **não a implementa**. É o gap-statement perfeito para o Capítulo 1 deste TCC, especialmente por ser do **mesmo programa MBA IA & BD do ICMC/USP**.

**Limitações honestas.** Split único treino/teste (sem walk-forward, sem CPCV); ações Bovespa, não FX; 98 features com ROC-AUC 0,986 acende alarme de overfitting; rotulagem manual em mercado bull period 2014–2024.

**Ações na monografia.**
- **Cap 1 §1.4 (Justification):** citar Felix com a frase verbatim acima como evidência de "lacuna NLP" no programa MBA IA & BD.
- **Cap 3 (Methodology), antes da escolha do meta-learner:** citar o resultado LGBM vs. XGB para justificar LGBM no presente trabalho.
- **Cap 3.4 (Price-only baseline):** reaproveitar o catálogo de 8 padrões de candlestick (Martelo, Estrela Cadente, Engolfo de Alta/Baixa, Doji, Harami, Marubozu, Morning/Evening Star) como vocabulário do **F8 (candlestick-confirmation gate)**.

---

### ★★★ Bruno Van Helden — `Bruno_Van_Helden_Monografia.pdf`

**Ficha verificada.** *Uma Análise Fundamentalista e Técnica do Mercado Cambial Latino-Americano.* FEA-USP, graduação em Economia, 2021 (43 páginas).

**O que faz.** Constrói três sinais em horizonte mensal sobre 12 pares cambiais (6 emergentes Latam + 6 desenvolvidos como controle), 2010-01 a 2020-12, dados Bloomberg:

$$
DRJ_t \in \{-1, +1\} \text{ (diferencial de juros reais)},\;
PIB_t \in \{-1, +1\} \text{ (diferencial de crescimento)},\;
RM2_t \in \{-1, +1\} \text{ (crescimento M2/reservas)}
$$
$$
C_t = \frac{DRJ_t + PIB_t + RM2_t}{3} \text{ (fundamentalista combinado, p. 22)},
$$
$$
G_t = \mathrm{sign}\!\left(\frac{MM(5,20) + MM(10,30) + MM(15,40)}{3}\right) \text{ (técnico combinado, p. 28)},
$$
$$
H_t = \mathrm{sign}\!\left(\frac{C_t + G_t}{2}\right) \text{ (híbrido, p. 34)}.
$$

**Resultados da estratégia mista $H_t$ (Tabela 6, p. 35, conferidos):**

| Par | Retorno médio (%) | Desvio padrão | **Sharpe** | Transações/ano |
|---|---|---|---|---|
| BRL | 6,93 | 6,37 | **1,09** | 2,30 |
| PEN | 2,56 | 1,46 | **1,76** | 0,20 |
| CLP | 2,40 | 1,85 | **1,30** | 0,80 |
| COP | 4,15 | 1,43 | **2,90** | 0,20 |
| ARS | 26,09 | 18,55 | **1,41** | 0,10 |
| MXN | 4,48 | 2,46 | **1,82** | 0,60 |
| **EUR** | 0,11 | 0,46 | **0,24** | 0,40 |
| **JPY** | -0,19 | 0,18 | **-1,08** | 2,80 |
| GBP | 0,19 | 0,21 | 0,87 | 2,00 |
| CHF | -0,20 | 0,44 | -0,45 | 0,40 |
| CAD | 0,67 | 0,44 | 1,50 | 0,40 |
| AUD | 2,19 | 1,32 | 1,65 | 0,20 |

**Descoberta crítica para este TCC.** Os pares EUR e JPY contra o USD são exatamente os pares-alvo deste TCC. Van Helden reporta Sharpe **0,24** (EUR) e **-1,08** (JPY) — quase nulo em um par e fortemente negativo no outro. Em contraste, todos os seis pares emergentes Latam têm Sharpe > 1. **A estratégia híbrida macro+técnico de Van Helden, portanto, falha justamente nos pares deste TCC.** Esse é argumento empírico forte para o Capítulo 1: a substituição do termo macro-fundamental pelo termo NLP-derivado é motivada por um déficit documentado nos pares-alvo, não apenas por preferência metodológica.

**Limitações.** Bloomberg-dependente; horizonte mensal com dados macroeconômicos trimestrais (look-ahead bias provável); sem custos de transação; sem walk-forward.

**Ações na monografia.**
- **Cap 1 §1.4 (Justification):** citar Van Helden e mencionar que seu híbrido macro+técnico, embora bem-sucedido em pares Latam, **registra Sharpe -1,08 em USD/JPY e 0,24 em EUR/USD** (Tabela 6, p. 35). Isso é munição empírica direta.
- **Cap 2 §2.5 (Hybrid Approaches):** adicionar Van Helden como ancestral arquitetural — o "padrão de média de sinais" $H_t = \mathrm{sign}((C_t + G_t)/2)$ é exatamente a estrutura que este TCC generaliza, com o termo NLP substituindo o termo macro.
- **Cap 2 Tabela 2.1 (State of the Art):** adicionar linha "Van Helden (2021) — 12 pares FX — média de sinais macro+técnico — sem WF — sign(avg) determinístico".

---

### ★★★ Atila Veiga — `AtilaVeiga.pdf`

**Ficha verificada.** *Aplicação de Algoritmos Heurísticos na Otimização dos Parâmetros de Trading com Pares Cointegrados.* POLI-USP, MBA Engenharia Financeira, 2022 (~113 páginas com anexos Python). Orientador: Bruno Augusto Angélico. Dados cedidos pela Sole Capital (agradecimentos).

**O que faz.** Constrói quatro variantes de otimizadores (Particle Swarm Optimization simples, PSO Linear, PSO ESE/ELS, Algoritmo Genético com seleção estocástica universal) e os aplica à otimização dos parâmetros de entrada / reversão / stop-loss de uma estratégia de pairs trading sobre ações cointegradas da B3. Inicialização por sequência de Sobol (quasi-aleatória), reparo de posições por reflect/shrink/random_shrink.

**Conclusão honesta (Resumo, p. v, verbatim).** *"Os resultados dos experimentos apresentam evidências inconclusivas; sugerindo que este problema é sujeito a um grande risco de sobreajuste na otimização, exigindo maiores cuidados e futuros estudos."*

Versão em inglês (Abstract): *"The experimental results were mixed, suggesting that this problem is prone to overfitting issues as result of the optimization, which require increased caution and future investigation."*

**Sumário confirmado.** Seção 3.4 Backtest (p. 69), com 3.4.5 "Limitações e problemas do backtest" (p. 72), subdividida em 3.4.5.1 Vieses (p. 72) e 3.4.5.2 Limitações (p. 74). É o template ideal para a Seção 3.10 (Threats to Validity) da monografia em curso.

**Ações na monografia.**
- **Cap 3 §3.10 (Threats to Validity):** citar Veiga como precedente que documenta empiricamente o risco de overfitting em otimização heurística de parâmetros de trading. Justifica a decisão deste TCC de manter regras determinísticas sem busca heurística sobre o sinal vivo.
- **Snippet sugerido (LaTeX):**

```latex
The temptation to optimise strategy parameters via heuristic search
(particle-swarm optimisation, genetic algorithms or analogous methods)
is documented in \cite{veiga2022pairs}, who reports inconclusive results
and severe over-fitting when applying four PSO/GA variants to
inception, reversion and stop-loss thresholds on cointegrated B3 pairs.
That negative evidence motivates the present work's conservative stance:
filter thresholds are calibrated once on the training window and frozen;
no iterative refinement against the validation set is performed.
```

- **Cap 5 (Future Work):** registrar APSO (Adaptive Particle Swarm Optimization, proposto pelo Kimi) como extensão *posterior à* demonstração de resultado defensável com a cadeia determinística.

---

### ★★★ Hô Don Lee — `HoDonLee TCCPRO14.pdf`

**Ficha verificada.** *Aplicação de Métodos Quantitativos no ADR/ORD Pairs Trading.* POLI-USP, Trabalho de Formatura em Engenharia de Produção, 2014 (~90 páginas). Orientador: Prof. Dr. Erik Eduardo Rego.

**O que faz.** Pairs trading estatístico entre ADRs e ORDs na B3, implementação em Excel + Bloomberg add-in.

**Conceito-chave — *tradability* (Seção 4.4, p. 49-52, verbatim).**

> *"Mean drift é um efeito que contribui para o carácter não estacionário da série de spread que diminui o grau de cointegração da série de duas ações, fazendo, por conseguinte, com que a série deixe de ser rentável."* (p. 49)

> *"o foco principal do teste de **tradability** é decidir o grau de desvio da condição ideal que um par pode ter para ainda ser considerado como negociável (tradable). Assim, o teste de tradability consiste em identificar quais propriedades são satisfeitas quando o par é realmente cointegrado e checar se existem tais propriedades em um determinado par selecionado."* (p. 50)

**Decomposição operacional do teste de tradability (p. 50-52, dois passos):**
1. **Coeficiente de cointegração** $\gamma = \mathrm{cov}(r_A, r_B)/\mathrm{var}(r_B)$, escolhido como o maior entre $\gamma_{AB}$ e $\gamma_{BA}$ para minimizar erro de precisão.
2. **Verificação do grau de reversão da média** via **frequência de cruzamento-zero** do spread — quantas vezes a série temporal cruza sua média por unidade de tempo; a inversa dessa frequência mede o tempo médio em posição. Bootstrap com `B = 2000` (Ilustração 9, p. 65) estima a distribuição. Regularização de Tikhonov-Miller (Seção 3.5, p. 43) usada para suavizar a função de lucro.

**Por que importa aqui.** EUR/USD e USD/JPY não são um par cointegrado clássico, mas o *raciocínio* de Lee transplanta limpamente: antes de aceitar uma entrada, verificar se o regime atual ainda preserva as condições sob as quais o sinal faz sentido. Esta é a fundação canônica do **F9 (regime-viability / tradability gate)** especificado pelo DeepSeek. A frequência de cruzamento-zero é uma métrica concreta que pode complementar (ou substituir) o teste ADF na variante mínima de F9.

**Ações na monografia.**
- **Cap 3 §3.7 (Fusion / Filter Chain):** citar Lee ao introduzir F9 como sanity check de regime; usar o conceito de mean drift + frequência de cruzamento-zero como justificativa teórica.
- **Snippet sugerido:**

```latex
The concept of \emph{tradability} introduced by \cite{lee2014adr} ---
verifying that a candidate residual series retains sufficient
mean-reversion to be operationally negotiable, beyond the
statistical test of cointegration --- is adapted here to the regime
viability gate (F9). The mean-drift effect that Lee documents
(\citeyear{lee2014adr}, Section 4.4) translates, in the present FX
context, to the question of whether the current volatility regime,
spread structure and signal stability still satisfy the conditions
under which the deterministic chain was calibrated.
```

---

### ★★ Fabio Biancardi Aquino — `FABIO BIANCARDI AQUINO.pdf`

**Ficha verificada.** *Detecção de Movimentos Anômalos com Características de Insider Trading no Mercado de Ações Brasileiro — Segmento Bovespa.* POLI-USP, MBA Engenharia Financeira, 2018 (37 páginas).

**Estado do PDF.** Scaneado em modo imagem, **mas com OCR parcial via Read tool** — abstract recuperado: *"a apresentação de modelos quantitativos capazes de ir na contramão das práticas acima citadas, e com bons resultados do ponto de vista detectivo, é a motivação central desta pesquisa."* Palavras-chave verbatim: *Insider Trading, estudo de eventos, retornos anormais*. Não foi possível conferir números/equações específicas via OCR.

**Empréstimo.** Metodologia padrão de event study (MacKinlay 1997 é a referência canônica) — retornos anormais $AR_t = R_t - (\alpha + \beta R_{M,t})$ relativos a uma janela de estimação, com CAR cumulativo sobre janela de evento simétrica. Aplica-se diretamente para *validar empiricamente o feature de evento geopolítico*: para cada classe de evento (sanção, FOMC, ECB, escalada militar), computar o CAR de EUR/USD em torno do timestamp e exigir significância estatística antes de admitir a classe no feature set.

**Recomendação:** citar **MacKinlay (1997)** como fonte primária da metodologia e Biancardi como aplicação subsequente — o PDF imagem-only de Biancardi torna citações com número de página arriscadas. Esta é a função do **F1 (event-CAR pre-validation)** na tabela consolidada.

**Ações na monografia.**
- **Cap 3 §3.6 (Feature Layer) ou Cap 4 (subseção planejada):** adicionar "Event-study validation of the event feature" como sanity check independente do P&L. Citar MacKinlay (1997) como referência primária; Biancardi como evidência de aplicação no contexto brasileiro.

---

### ★ Rafael Galo Pugina — `Rafael_Galo_Pugina.pdf`

**Ficha verificada.** *Uso de LLMs para a Previsibilidade de Projetos de Desenvolvimento de Software.* ICMC/USP, MBA IA & Big Data, 2024.

**Empréstimo.** SBERT (Sentence-BERT) como camada de embedding semântico determinística, antes de um Random Forest. Cacheável, sem chamada de API. Aplica-se como encoder *paralelo / fallback* ao FinBERT no Cap 3 §3.6 deste TCC. Detecção de duplicatas por cosine similarity como mecanismo de filtro (F13 do DeepSeek).

**Aviso da `analise-integracao-monografia.md`:** o pipeline atual já tem FinBERT + Loughran-McDonald, o que cobre o trabalho de scoring de sentimento. SBERT só agrega como *encoder de novidade / detecção de duplicatas*, não como scorer adicional. Citar apenas se F13 (deduplicação) for adotado.

### ★ José Eduardo Athayde Ferrarini — `JoseEduardoAthaydeFerrarini_TCC_2025.pdf`

**Ficha verificada.** *Uso de LLMs para a Classificação de Aspectos em Feedbacks de Desenvolvedores de Software.* ICMC/USP, MBA IA & Big Data, 2025.

**Empréstimo.** Classificação por aspecto (extrair tuplas *(aspecto, polaridade)* de texto livre) é estruturalmente análoga a extrair *(moeda, direção, horizonte, intensidade)* de notícia. Calibração de threshold por **ROC / Youden J** (p. 51-52 segundo DeepSeek). Aplica-se ao **F13 (Youden-J threshold calibration)** e ao **F11 (scorer-disagreement gate)** do conjunto consolidado de filtros.

### ★ Jean Lourenço da Silva — `Jean_Lourenço_da_Silva.pdf`

**Ficha verificada.** *Análise Comparativa de Modelos Derivados do BERT e LLMs para Extração de Dados em Documentos de Imposto de Renda.* ICMC/USP, MBA IA & Big Data, 2024.

**Empréstimo.** Reporta que BERT fine-tunado se torna competitivo com LLMs de fronteira na faixa de ~10 k amostras rotuladas. Útil como baliza de orçamento *caso* este TCC opte por fine-tune próprio. **Não é o caso atual** — o pipeline usa FinBERT pré-treinado de prateleira. Citação opcional, apenas se a discussão de custo no Cap 3 §3.6 desejar referência ao trade-off.

### ★ Bruna Magrini da Cruz — `Bruna_Magrini_da_Cruz_TCC_2025.pdf`

**Ficha verificada.** *Automated Generation of Troubleshooting Guides from Incident Data Using Large Language Models.* ICMC/USP, MBA IA & Big Data, 2025.

**Empréstimo.** Prompt engineering com schema JSON fixo para extração estruturada de LLM. Aplica-se ao Cap 3 §3.6 ao definir o schema do registro de feature LLM. Útil mas não essencial dado que o pipeline atual já materializa features estruturadas.

### ★ Diogo Moura Santos — `Diogo_Moura_Santos.pdf`

**Ficha verificada.** *Sistema de Detecção e Categorização de Falhas de Infraestrutura.* ICMC/USP, MBA IA & Big Data, 2024.

**Empréstimo.** Detecção de anomalias estilo LogBERT sobre stream textual com timestamp — abstratamente equivalente a detectar rajadas anômalas de notícias. **F12 (text-quality gate)** dele extraído. Trabalho futuro: anomaly score em news stream como feature não-direcional.

### ★ Bruno Henrique de Brito — `Bruno_Henrique_de_Brito_TCC_2025.pdf`

**Ficha verificada.** *Integrando Ciência da Informação e Processamento em Linguagem Natural.* ICMC/USP, MBA IA & Big Data, 2025.

**Empréstimo.** Knowledge graph como camada estruturada entre dados brutos e LLM — analogia arquitetural ao perception-execution decoupling deste TCC. **F14 (entity-relevance gate)** dele extraído. Implementação completa de KG está fora de escopo; mencionar no Cap 5 (Future Work).

---

## 2. Trabalhos sem aproveitamento direto

### ★ Marcus Nogueira — *Deep Arte Digital, crIA?*
Arte digital + NFTs. Sem conteúdo transferível para trading.

### ★ Rafael Henrique Lemes Galvão — `RAFAEL_HENRIQUE_LEMES__GALVÃO.pdf`
*High-Frequency Trading: Uma Operação Aplicável no Brasil?* POLI-USP, MBA Engenharia Financeira, 2015 (35 p., conferido na ficha catalográfica). **PDF é scaneado sem camada OCR** — `pdftotext` extrai zero palavras. Citação anterior nesta análise atribuída a Galvão ("o mercado é pequeno, pouco profundo e muito volátil", p. 18) era confabulada por sub-agente; **retratada**. Caso o tema HFT no Brasil seja relevante para o Cap 2, recuperar via aldridge2013, harris2003 ou outras fontes primárias.

### ★ Aila Goulart — `tc5029-Aila-Goulart-Uso.pdf`
*Uso do PLN no Desenvolvimento de um Sistema de Organização do Conhecimento — Documentação em Saúde.* USP, 2024. Domínio remoto (terminologia médica); ferramentas BootCat/AntConc. Sem aproveitamento prático para este TCC.

---

## 3. Cadeia consolidada de filtros (F1–F7 existentes + F8–F16 novos)

A monografia já especifica sete filtros na cadeia determinística (F1–F7, Seção 3.7). Os filtros abaixo (F8–F16) são *adições* a essa cadeia. Numeração alinhada ao `relatorio-sintese-deepseek.md` (Parte II), que fornece pseudocódigo completo, esforço estimado e ordem de implementação para cada um.

| # | Filtro | Fase | Origem | Esforço (DeepSeek) |
|---|---|---|---|---|
| F8 | Candlestick-confirmation gate | Execução (AND) | Felix | ⭐ ~30 linhas |
| F9 | Regime-viability / tradability gate (ATR + ADF + zero-crossing) | Execução (AND) | Hô Don Lee | ⭐⭐ ~50 linhas + statsmodels |
| F10 | Confidence gate (FinBERT softmax margin) | Percepção | Ferrarini | ⭐ ~10 linhas |
| F11 | Scorer-disagreement gate (FinBERT × Loughran-McDonald) | Percepção | Ferrarini | ⭐ ~15 linhas |
| F12 | Text-quality gate (length, dedup, noise) | Pipeline pré-LLM | Moura Santos | ⭐⭐ |
| F13 | Duplicate-detection gate (SBERT cosine) | Percepção | Pugina | ⭐⭐ ~15 linhas + sklearn |
| F14 | Entity-relevance gate (substring matching) | Percepção | Brito | ⭐ ~20 linhas |
| F15 | Submodel-consensus gate (≥ 3 de 4 sub-modelos) | Execução (AND) | (síntese DeepSeek) | ⭐ ~20 linhas |
| F16 | Calibration-robustness criterion (sensibilidade a ±ε) | Configuração offline | Veiga | ⭐⭐ |

### Conjunto mínimo para a primeira execução experimental

Recomendação revisada (combinando este levantamento com `relatorio-sintese-deepseek.md` §7):

1. **F10** (confidence gate) — esforço ⭐, dependência zero, impacto alto. Margem softmax do FinBERT já é subproduto da inferência.
2. **F11** (scorer-disagreement) — esforço ⭐, dependência zero, impacto médio-alto. Aproveita FinBERT + Loughran-McDonald já presentes.
3. **F14** (entity-relevance) — esforço ⭐, dependência zero. Substring matching contra dicionário pré-registrado.
4. **F8** (candlestick) — esforço ⭐. TA-Lib já no stack pelo F3 existente.
5. **F9** (regime-viability) — esforço ⭐⭐, requer statsmodels para ADF. Componente mais valioso do grupo ⭐⭐.

Os filtros F12, F13, F15, F16 podem entrar como ablações no Capítulo 4. **Os filtros que o presente levantamento havia chamado de F1 (event-CAR pre-validation), F2 (densidade de keywords), F5 (news-burst), F6 (cross-pair) em versões anteriores deste documento foram realinhados ou consolidados nesta numeração;** os respectivos números acima são os canônicos a partir desta revisão.

### Estratégias de ablação para o Capítulo 4 (origem: DeepSeek §6)

| Estratégia | Filtros novos ativos | Hipótese | Métrica-chave |
|---|---|---|---|
| **Baseline** | nenhum | Referência | Sharpe, MDD |
| **A — Candlestick only** | F8 | Menos trades, hit rate ↑ | Hit rate, holding médio |
| **B — Perception quality** | F10 + F11 (+ F12, F13 opcionais) | Sinal textual mais limpo | Contribuição do news sub-model |
| **C — Regime gating** | F9 + F15 | Menos trades, drawdown ↓ | MDD, trades/ano |
| **D — Full hybrid** | F8 + F9 + F10 + F11 + F14 + F15 | Maior Sharpe ajustado a risco | Sharpe, profit factor |

---

## 4. Empréstimos não-filtro (camada de features + arquitetura)

### Features de preço (origem: Felix)
- **LGBM como meta-learner**, justificado por ROC-AUC 0,986 vs. XGBoost 0,985, com tempo ~7,6× menor.
- **Heikin-Ashi** como série paralela de input (fórmula de Felix p. 28).
- **OBV (On Balance Volume)** como feature de confirmação de volume.

### Decisão metodológica registrada — APSO × Veiga
Kimi propõe APSO (Adaptive Particle Swarm Optimization) para otimizar thresholds em walk-forward. Codex argumenta o contrário, citando Veiga. **Decisão deste TCC: posição Codex/Veiga — sem busca heurística no sinal vivo.** APSO fica em Cap 5 (Future Work).

### Variante arquitetural — KG estruturado GDELT → LLM
Pré-processar GDELT-GKG em um knowledge graph estruturado (atores × temas × emoções × Goldstein scale) e usar o grafo como contexto do prompt do LLM. Origem: Kimi/Brito. Custo de infra (Neo4j ou DuckDB-PGQ) provavelmente fora de escopo. **Recomendação:** Cap 5 (Future Work).

### Avaliação estatística adicional
- **Bootstrap (B = 1000)** para intervalos de confiança de Sharpe / hit-rate / drawdown, estratificados por regime de volatilidade.

---

## 5. Plano de melhoria da monografia — por capítulo, com snippets

Síntese final cruzando todos os relatórios paralelos com a leitura direta dos chapters 01–02 e a estrutura prevista do chapter 03. **Esta é a tabela operacional** — cada linha é uma edição auditavelmente justificada.

| # | Capítulo / Seção | O que adicionar | Justificativa | Origem |
|---|---|---|---|---|
| E1 | Cap 1 §1.4 (Justification) | Parágrafo citando Felix (gap NLP no mesmo programa) | Felix reconhece "informações textuais" como input e não implementa | Felix, Resumo p. 7 |
| E2 | Cap 1 §1.4 (Justification) | Frase citando Van Helden: híbrido macro+técnico produz Sharpe **0,24 EUR e -1,08 JPY** | Evidência empírica direta de que falta NLP nos pares-alvo deste TCC | Van Helden, Tabela 6, p. 35 |
| E3 | Cap 2 §2.5 (Hybrid Approaches) | Adicionar Van Helden como ancestral arquitetural; fórmula $H_t = \mathrm{sign}((C_t + G_t)/2)$ | Padrão de "média de sinais" que este TCC generaliza substituindo $C_t$ macro por $C_t$ NLP | Van Helden, p. 34 |
| E4 | Cap 2 Tabela 2.1 (State of the Art) | Linha "Van Helden (2021), 12 pares FX, média macro+técnico, sem WF, sign(avg) determinístico" | Posicionamento completo | Van Helden |
| E5 | Cap 3 §3.4 (Price-only baseline) | Catálogo de 8 padrões de candlestick como vocabulário base | Sólida ancoragem em precedente do mesmo programa | Felix, Tabela 1 |
| E6 | Cap 3 §3.6 (Feature Layer) | Justificativa LGBM com ROC-AUC + tempo (7,6× mais rápido que XGB) | Escolha computacional defensável sob CPCV | Felix, Tabela 10, p. 34 |
| E7 | Cap 3 §3.6 ou §3.7 | Spec do F8 candlestick-confirmation gate | Filtro de baixo custo com precedente | Felix + DeepSeek §5 |
| E8 | Cap 3 §3.7 | Spec do F9 regime-viability gate (com referência a tradability + zero-crossing) | Sanity check de regime; fundamento teórico em Lee | Lee §4.4 + DeepSeek §5 |
| E9 | Cap 3 §3.6 | Spec do F10 confidence gate (FinBERT softmax margin) + F11 disagreement gate | Filtragem de ruído na fonte | Ferrarini + Codex |
| E10 | Cap 3 §3.10 (Threats to Validity) | Parágrafo citando Veiga (overfitting em otimização heurística) + estrutura da Seção 3.4.5 dele | Justifica disciplina de thresholds frozen | Veiga §3.4.5, p. 72-74 |
| E11 | Cap 4 (Evaluation) | Subseção "Event-study validation of the event feature" (MacKinlay + Biancardi) | Validação independente do P&L | MacKinlay 1997 / Biancardi |
| E12 | Cap 4 (Evaluation) | Ablações A/B/C/D conforme tabela da Seção 3 acima | Estrutura de análise por filtro | DeepSeek §6 |
| E13 | Cap 4 (Evaluation) | Reporte estratificado por regime de volatilidade + IC bootstrap | Robustez | Codex + síntese |
| E14 | Cap 5 (Future Work) | APSO; KG GDELT; SBERT dedup; news-anomaly detection | Direções identificadas mas fora de escopo | Kimi / Brito / Pugina / Moura |

**Decisão explícita de NÃO adicionar (origem: `analise-integracao-monografia.md` + verificação direta):**
- SBERT como scorer paralelo a FinBERT — redundante, pipeline já tem FinBERT + Loughran-McDonald.
- Densidade de keywords (Goulart) — overkill dado priorização de fontes (central bank > GDELT > FNSPID).
- Fine-tune próprio de BERT (Silva) — este TCC usa FinBERT de prateleira.
- News-burst anomaly detection (Moura) em produção — vai para Cap 5 (Future Work) apenas.

### Snippets prontos para colar

**E1 + E2 — Cap 1 §1.4 (Justification):**

```latex
A useful in-house antecedent is the recent monograph
\cite{felix2024swing}, produced within the same ICMC/USP MBA programme
as the present work. The author surveys seven machine-learning
classifiers (SVM, XGBoost, LightGBM, MLP, KNN, GaussianNB and
SGDClassifier) on IBrX-100 equities and explicitly states in the
abstract that practitioners also use ``textual information in the form
of news articles, social media and even publications from economic
analysts'', yet the implementation remains price-side only. The
present work closes that gap by building the textual perception layer
that \citeauthor{felix2024swing} identified as future work.

A second relevant precedent is \cite{vanhelden2021latam}, who builds
on 12 FX pairs a hybrid strategy combining a macro-fundamental signal
(real-interest-rate, GDP-growth and M2/reserves differentials) with a
technical signal (averaged moving-average crossovers) via
$H_t = \operatorname{sign}((C_t + G_t)/2)$. The hybrid produces
Sharpe ratios above 1 on all six emerging Latin-American pairs but
\textbf{drops to 0.24 on EUR and to $-1.08$ on JPY against the USD}
(Tabela 6, p.~35). Those two pairs are precisely the targets of the
present work. The empirical failure of the macro-only hybrid on the
target pairs is, in itself, a strong motivation to replace the
macro-fundamental term with an NLP-derived textual term.
```

**E6 — Cap 3 §3.6 (Feature Layer), justificativa LGBM:**

```latex
The meta-learner of the present work is LightGBM, motivated both by
the financial machine-learning recommendations of
\cite{lopezdeprado2018advances} on gradient-boosted ensembles and by
the comparative evidence of \cite{felix2024swing}, who benchmarks
seven classifiers on a similar financial prediction task and reports
ROC-AUC of 0.986 for LightGBM (max\_depth = 16) against 0.985 for
XGBoost (n\_estimators = 1000, max\_depth = 10), with execution
time of 0.897\,s versus 6.805\,s --- roughly a 7.6$\times$ speedup.
That margin is relevant under the combinatorial purged
cross-validation protocol of Section~\ref{sec:evaluation}, which
requires repeated refits per pair.
```

**E10 — Cap 3 §3.10 (Threats to Validity):**

```latex
The temptation to optimise filter thresholds with heuristic search ---
particle-swarm optimisation, genetic algorithms or analogous
metaheuristics --- is documented in \cite{veiga2022pairs}, who applies
four PSO/GA variants to the inception, reversion and stop-loss
parameters of a pairs-trading strategy on cointegrated B3 equities and
reports inconclusive results, attributed by the author to ``a great
risk of over-fitting in the optimisation, requiring increased caution
and future investigation'' (Resumo, p.~v). Section~3.4.5 of that work
is dedicated to backtester biases and limitations and serves as a
template for the present subsection. The negative evidence motivates
the present work's conservative discipline: filter thresholds are
calibrated once on the training window and frozen, with no iterative
refinement against the validation set.
```

---

## 6. Bibliografia consolidada para `monografia/bib/references.bib`

Cada entrada conferida contra capa + ficha catalográfica do PDF. Comprimentos de página verificados.

```bibtex
@mastersthesis{felix2024swing,
  author       = {Claudinei Felix},
  title        = {Explorando a Intelig{\^e}ncia Artificial na Previs{\~a}o
                  de Tend{\^e}ncias e Pre{\c c}os no Contexto do Swing
                  Trading: Um Estudo de Caso para Aprimorar Estrat{\'e}gias
                  de Investimento},
  school       = {Universidade de S{\~a}o Paulo, ICMC},
  year         = {2024},
  type         = {MBA Monograph (Intelig{\^e}ncia Artificial \& Big Data)},
  note         = {Orientadora: Prof.\,Dr.\,Marislei Nishijima. 40\,p.}
}

@mastersthesis{vanhelden2021latam,
  author       = {Bruno Van Helden},
  title        = {Uma An{\'a}lise Fundamentalista e T{\'e}cnica do Mercado
                  Cambial Latino-Americano},
  school       = {Universidade de S{\~a}o Paulo, FEA},
  year         = {2021},
  type         = {Graduation Monograph (Economia)},
  note         = {43\,p.}
}

@mastersthesis{veiga2022pairs,
  author       = {{\'A}tila da Veiga},
  title        = {Aplica{\c c}{\~a}o de Algoritmos Heur{\'\i}sticos na
                  Otimiza{\c c}{\~a}o dos Par{\^a}metros de Trading com
                  Pares Cointegrados},
  school       = {Universidade de S{\~a}o Paulo, POLI},
  year         = {2022},
  type         = {MBA Monograph (Engenharia Financeira)},
  note         = {Orientador: Prof.\,Dr.\,Bruno Augusto Ang{\'e}lico. {\sim}113\,p.}
}

@mastersthesis{lee2014adr,
  author       = {Ho Don Lee},
  title        = {Aplica{\c c}{\~a}o de M{\'e}todos Quantitativos no ADR/ORD
                  Pairs Trading},
  school       = {Universidade de S{\~a}o Paulo, POLI},
  year         = {2014},
  type         = {Graduation Monograph (Engenharia de Produ{\c c}{\~a}o)},
  note         = {Orientador: Prof.\,Dr.\,Erik Eduardo Rego. {\sim}90\,p.}
}

@mastersthesis{biancardi2018insider,
  author       = {Fabio Biancardi Aquino},
  title        = {Detec{\c c}{\~a}o de Movimentos An{\^o}malos com
                  Caracter{\'\i}sticas de Insider Trading no Mercado de
                  A{\c c}{\~o}es Brasileiro --- Segmento Bovespa},
  school       = {Universidade de S{\~a}o Paulo, POLI, PECE},
  year         = {2018},
  type         = {MBA Monograph (Engenharia Financeira)},
  note         = {Orientador: Prof.\,Dr.\,Bruno Augusto Ang{\'e}lico. 37\,p.}
}

@article{mackinlay1997event,
  author       = {A. Craig MacKinlay},
  title        = {Event Studies in Economics and Finance},
  journal      = {Journal of Economic Literature},
  volume       = {35},
  number       = {1},
  pages        = {13--39},
  year         = {1997}
}
```

Entradas opcionais (citar apenas se F10/F11/F13/F14 ou KG forem efetivamente adotados):

```bibtex
@mastersthesis{ferrarini2025aspectos,
  author       = {Jos{\'e} Eduardo Athayde Ferrarini},
  title        = {Uso de LLMs para a Classifica{\c c}{\~a}o de Aspectos em
                  Feedbacks de Desenvolvedores de Software},
  school       = {Universidade de S{\~a}o Paulo, ICMC},
  year         = {2025},
  type         = {MBA Monograph (IA \& Big Data)}
}

@mastersthesis{pugina2024llms,
  author       = {Rafael Galo Pugina},
  title        = {Uso de LLMs para a Previsibilidade de Projetos de
                  Desenvolvimento de Software},
  school       = {Universidade de S{\~a}o Paulo, ICMC},
  year         = {2024},
  type         = {MBA Monograph (IA \& Big Data)}
}

@mastersthesis{brito2025ciencia,
  author       = {Bruno Henrique de Brito},
  title        = {Integrando Ci{\^e}ncia da Informa{\c c}{\~a}o e
                  Processamento em Linguagem Natural},
  school       = {Universidade de S{\~a}o Paulo, ICMC},
  year         = {2025},
  type         = {MBA Monograph (IA \& Big Data)}
}
```

Pugina, Silva, Cruz, Goulart e Moura Santos só entram inline no Cap 3 caso o filtro respectivo seja adotado.

---

## 7. Notas de verificação

- **Releitura nesta revisão.** Felix (p. 1-7, 25-35), Veiga (p. 1-7, 11-14), Lee (p. 1-8, 11-14, 49-52), Van Helden (p. 21-35). Capas + sumários + tabelas-chave + abstracts conferidos visualmente via Read tool.
- **Correções numéricas em relação a versões anteriores.** (i) LGBM vs. XGB no Felix é **7,6× mais rápido** (0,897 s vs. 6,805 s, Tabela 10, p. 34) — DeepSeek e integracao haviam estimado "6×". (ii) Sharpe do híbrido de Van Helden no JPY é **-1,08** (Tabela 6, p. 35) — nenhum relatório paralelo havia destacado este número, que é o argumento empírico mais forte do conjunto para a justificativa do Cap 1. (iii) Lee tradability é decomposto em coeficiente de cointegração + **frequência de cruzamento-zero** (Seção 4.4, p. 50-52), não apenas ADF como simplificações anteriores sugeriam.
- **Retração sobre Galvão.** PDF é scaneado em imagem (39 páginas, 0 palavras via `pdftotext`); citações específicas atribuídas a ele em versões anteriores eram fabricadas por sub-agente. Caso o tema HFT seja necessário, usar Aldridge 2013 ou Harris 2003 como fontes primárias.
- **Biancardi parcialmente recuperado.** Abstract via OCR (Read tool) confirma palavras-chave *insider trading, estudo de eventos, retornos anormais*. Equações específicas não conferidas; citar MacKinlay 1997 como fonte primária da metodologia de event study.
- **Aviso geral.** Onde este documento cita página específica, a página foi conferida. Para os trabalhos de relevância ★ (Pugina, Ferrarini, Silva, Cruz, Moura Santos, Goulart, Brito), as descrições de método vêm de leitura parcial via Read tool e cruzamento com relatórios paralelos — antes de citação literal na monografia, conferir contra o respectivo PDF original.
