# Análise de Integração com a Monografia Existente

> Análise crítica do que dos TCCs relacionados REALMENTE acrescenta valor, considerando o que já está escrito nos capítulos 1-3.

---

## Status da Monografia (o que já está coberto)

| Aspecto | Cobertura Atual | Qualidade |
|---------|-----------------|-----------|
| **Posicionamento vs estado da arte** | Tabela 2.1 comparando com Zhang (2025), Xiao/TradingAgents, Papadakis/ATLAS, Tian/TradingGroup, Xiong/QuantAgent | ✅ Excelente |
| **Justificativa híbrida** | Cita Tetlock (2007), Caldara & Iacoviello (2022), Loughran-McDonald (2011) | ✅ Sólida |
| **NLP/FinBERT** | Baseado no curso do MBA (Caseli 2024), Araci (2019), Yang (2020) | ✅ Completo |
| **Validação** | CPCV + embargo (López de Prado 2018), walk-forward | ✅ Rigurosa |
| **Arquitetura** | "Agentic perception, deterministic execution" bem definida | ✅ Clara |
| **Cadeia de filtros** | 7 filtros (F1-F7) já definidos na Seção 3.7 | ✅ Estruturada |

---

## O que é REDUNDANTE (não precisa adicionar)

### ❌ Bruno Van Helden (2021)
**Por que não:** Seu posicionamento vs Zhang (2025) já é suficiente. Van Helden é anterior, menos rigoroso metodologicamente, e cobre mercados emergentes latino-americanos (BRL, ARS, MXN) que não são seu foco. Adicionar não fortalece o argumento.

### ❌ Rafael Galo Pugina (2024) - SBERT
**Por que não:** Você já tem FinBERT + Loughran-McDonald. Adicionar SBERT como "fallback" é distracao - seu pipeline já é suficientemente robusto.

### ❌ Jean Lourenço da Silva (2024) - BERT vs LLM comparison
**Por que não:** Você já cita Araci (2019) e Yang (2020) para FinBERT. A discussão de ~10k amostras é irrelevante porque você não está fazendo fine-tune próprio.

### ❌ Bruna Magrini da Cruz (2025) - Prompt engineering estruturado
**Por que não:** Você já tem a camada de feature extraction definida na Seção 3.6. Não precisa de mais referências de prompt engineering.

### ❌ Diogo Moura Santos (2024) - Anomalia em rajada de notícias
**Por que não:** F5 (news-burst gate) é interessante mas não essencial. Você já tem F4 (news-context filter) que cobre eventos de alto impacto.

### ❌ Aila Goulart (2024) - Densidade de palavras-chave
**Por que não:** Filtro muito granular. Você já tem priorização de fontes (central bank > GDELT > FNSPID) que filtra ruído de forma mais efetiva.

---

## O que REALMENTE ACRESCENTA VALOR

### ✅✅✅ Claudinei Felix (2024) - ALTA RELEVÂNCIA

**Onde adicionar:** Capítulo 1, Seção 1.4 (Justificação) ou Seção 1.5 (Objetivos)

**Por que é único:** Felix é do **mesmo programa (MBA ICMC/USP, 2024)** e trabalha com **swing trading + IA**. O abstract dele explicita o gap que você está fechando:

> *"O segundo tipo de análise é qualitativa, envolve métricas mais difíceis de quantificar... informações textuais na forma de novos artigos financeiros, mídias sociais... mas a implementação se restringe a candlesticks + indicadores"*

**Texto sugerido para adicionar:**
```latex
Recent work at the same institution \cite{felix2024swing} surveyed machine-learning 
classifiers for swing-trading on the IBrX-100 and explicitly noted that textual 
information---news articles, social media, analyst reports---is acknowledged by 
practitioners as a relevant signal class, yet the implementation remained 
price-side only. The present work closes that gap by building the textual 
perception layer that \citeauthor{felix2024swing} identified as future work.
```

**Bônus:** Tabela de performance dele (LGBM ROC-AUC 0,986 vs XGB 0,985) pode justificar sua escolha de LightGBM no Capítulo 3.

---

### ✅✅ Átila Veiga (2022) - RELEVÂNCIA MÉDIA-ALTA

**Onde adicionar:** Capítulo 3, Seção 3.10 (Reproducibility and Threats to Validity)

**Por que é útil:** Veiga é **cautionary tale** da POLI-USP que tentou otimização heurística (PSO/GA) em trading e concluiu que é fortemente susceptível a overfitting. Isso **reforça sua decisão** de não fazer busca agressiva de parâmetros.

**Texto sugerido:**
```latex
The temptation to optimise strategy parameters with heuristic search 
(e.g., genetic algorithms or particle-swarm optimisation) is documented 
in \cite{veiga2022pairs}, who report inconclusive results and severe 
over-fitting when optimising entry/exit thresholds on cointegrated pairs. 
That evidence motivates the present work's conservative stance: thresholds 
are calibrated once on the training window and frozen; no iterative 
refinement against the validation set is performed.
```

---

### ✅✅ Hô Don Lee (2014) - RELEVÂNCIA MÉDIA

**Onde adicionar:** Capítulo 3, Seção 3.7 (Fusion), subseção do F5 (risk-guard filter)

**Por que é útil:** O conceito de **"tradability"** de Lee (testar se série residual preserva reversão à média antes de operar) pode ser adaptado como justificativa para seu F5 (risk-guard filter).

**Texto sugerido:**
```latex
The concept of ``tradability'' introduced by \cite{lee2014adr}---verifying 
that the residual series retains sufficient mean-reversion before committing 
capital---is adapted here to regime viability: the Risk-Guard filter (F5) 
vetoes trades when volatility exceeds historical bands or when the price 
series fails a stationarity test, ensuring the strategy operates only in 
regimes where the signal logic remains valid.
```

---

### ✅ Fabio Biancardi Aquino (2018) - RELEVÂNCIA MÉDIA

**Onde adicionar:** Capítulo 3, Seção 3.6 (Feature Layer), validação de eventos

**Por que é útil:** Metodologia de **estudo de eventos** (event-study) com retornos anormais (CAR) pode ser usada para validar se as classes de eventos GDELT realmente têm impacto antes de incluí-las no modelo.

**Mas atenção:** Isso é mais trabalho. Se não for fazer a validação, não cite.

---

## Filtros Propostos - O que REALMENTE cabe

Você já tem 7 filtros (F1-F7) na cadeia. Análise dos filtros que sugeri:

| Filtro Proposto | Já Coberto? | Decisão |
|-----------------|-------------|---------|
| F1 - Pré-validação por CAR | Parcial (F4 cobre eventos) | ❌ Não adicionar |
| F2 - Confirmação por candlestick | NOVO | ✅ Adicionar como F8 (opcional) |
| F3 - Pré-registro de aspecto | Parcial (F4 já filtra por relevância) | ❌ Não adicionar |
| F4 - Densidade de keywords | Não coberto | ❌ Overkill |
| F5 - Anomalia em rajada | Parcial (F4 cobre eventos de alto impacto) | ❌ Não adicionar |
| F6 - Robustez de calibração | NOVO (metodológico) | ✅ Mencionar na Seção 3.10 |

**Recomendação:** Adicione apenas **F2 (candlestick-confirmation)** como filtro opcional e **F6 (robustez)** como critério metodológico.

---

## Contribuições Específicas do Felix para o Capítulo 4

Felix reporta performance de 7 classificadores. Você pode usar isso para justificar sua escolha de **LightGBM**:

| Classificador | ROC-AUC | Tempo |
|---------------|---------|-------|
| LGBM | 0,986 | 0,9s |
| XGBoost | 0,985 | 6,8s |
| MLP | 0,967 | 4,6s |

**Texto sugerido para Capítulo 3:**
```latex
LightGBM was chosen as the meta-learner following \cite{felix2024swing}, 
who report ROC-AUC of 0.986 with LightGBM versus 0.985 with XGBoost 
on a similar financial prediction task, with execution time approximately 
six times faster---a relevant consideration given the need for multiple 
walk-forward refits in the cross-validation protocol.
```

---

## Resumo da Integração Recomendada

### Citações a ADICIONAR em `references.bib`:

```bibtex
@mastersthesis{felix2024swing,
  author = {Felix, Claudinei},
  title = {Explorando a Intelig{^e}ncia Artificial na Previs{~a}o de 
           Tend{^e}ncias e Pre{ccedil}os no Contexto do Swing Trading},
  school = {Universidade de S{~a}o Paulo, ICMC},
  year = {2024},
  type = {MBA Monograph}
}

@mastersthesis{veiga2022pairs,
  author = {Veiga, {'A}tila da},
  title = {Aplica{ccedil}{~a}o de Algoritmos Heur{\\'\i}sticos na 
           Otimiza{ccedil}{~a}o dos Par{^a}metros de Trading com 
           Pares Cointegrados},
  school = {Universidade de S{~a}o Paulo, POLI},
  year = {2022},
  type = {MBA Monograph}
}
```

### Citações a IGNORAR:
- Van Helden (redundante com Zhang)
- Pugina (redundante com seu pipeline)
- Silva (você não faz fine-tune)
- Cruz (já tem extração estruturada)
- Santos (F5 já cobre)
- Goulart (overkill)

### Modificações no texto:

| Capítulo | Seção | Mudança |
|----------|-------|---------|
| 1 | 1.4 ou 1.5 | +1 parágrafo citando Felix como gap identificado |
| 3 | 3.6 (Feature Layer) | +1 parágrafo justificando LightGBM com Felix |
| 3 | 3.7 (Fusion) | +F8 opcional: candlestick-confirmation gate |
| 3 | 3.10 (Threats) | +1 parágrafo citando Veiga contra otimização agressiva |

---

## Conclusão

Dos 15 TCCs analisados, apenas **2-3** realmente acrescentam valor à sua monografia:

1. **Felix (2024)** - Essencial: gap identificado + justificativa LightGBM
2. **Veiga (2022)** - Útil: cautionary tale para Seção 3.10
3. **Lee (2014)** - Opcional: conceito de tradability para F5

Os demais são ou redundantes com o que você já tem, ou propoem refinamentos que não cabem no escopo (ficam para "future work" se quiser mencionar).

Não vale a pena poluir a monografia com citações que não fortalecem o argumento central.
