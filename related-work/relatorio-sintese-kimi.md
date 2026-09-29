# Trabalhos Correlatos — Análise Crítica + Especificação de Filtros

> Análise independente dos 15 TCCs em `related-work/`. Parte I: análise crítica para citação na monografia. Parte II: especificação técnica de filtros implementáveis na cadeia determinística. Data: 2026-05-22.
>
> **TCC de destino:** Estratégia híbrida EUR/USD e USD/JPY (2015–2024), 4 sub-modelos LightGBM → meta-learner → cadeia de filtros determinísticos → LEAN backtest, avaliação CPCV + walk-forward.

---

# Parte I — Análise Crítica dos Trabalhos

## 1. Trabalhos Diretamente Relevantes

### 1.1 Claudinei Felix (ICMC/USP, MBA IA & BD, 2024) — `Claudinei_Felix.pdf`

**O que li.** Monografia de 40 páginas do mesmo programa. 7 classificadores (SVM, XGB, LGBM, etc.), ~98 indicadores + 8 padrões candlestick como features binárias, IBrX-100 (2014–2024), PCA 95%. **LGBM**: ROC-AUC 0,986, precisão 0,948, recall 0,969. Tempo de execução ~6× menor que XGBoost.

**Gap declarado no abstract:**
> *"O segundo tipo de análise é qualitativa... informações textuais na forma de novos artigos financeiros, mídias sociais... mas este estudo [...] usa dados de mercado e conhecimentos de operadores transformados em variáveis de entrada."*

**Falhas metodológicas identificadas:**
| Problema | Severidade | Impacto |
|----------|------------|---------|
| Split único treino/teste | 🔴 Grave | ROC-AUC 0,986 com 98 features cheira a overfitting |
| Sem purging/embargo | 🔴 Grave | Leakage temporal provável |
| PCA sem justificativa | 🟡 Médio | Perda de interpretabilidade sem ganho claro |
| Aplicação a ações, não FX | 🟡 Médio | Transferibilidade não garantida |
| Trabalhos relacionados superficial | 🟢 Baixo | Apenas 2 páginas |

**O que aproveito:**

| Elemento | Valor | Uso no TCC |
|----------|-------|------------|
| **Gap declarado de NLP** | ⭐⭐⭐⭐⭐ | Cap 1: "literatura do próprio programa reconhece gap e não fecha" |
| **LGBM vs XGB** | ⭐⭐⭐⭐ | Cap 3: justificativa empírica para escolha de LightGBM (6× mais rápido) |
| **Catálogo candlestick** | ⭐⭐⭐ | Cap 3: 8 padrões (Martelo, Engolfo, Doji, etc.) para F8 |

**Veredito.** Essencial pelo gap declarado. Resultados de LGBM promissores, mas avaliação fraca impede confiança plena. Usar como evidência do gap, não como benchmark metodológico.

---

### 1.2 Átila Veiga (POLI-USP, MBA Eng. Financeira, 2022) — `AtilaVeiga.pdf`

**O que li.** Monografia de 73 páginas — a mais honesta do conjunto. 4 variantes de otimizadores (PSO, GA), 14 funções benchmark, 50 repetições. Aplicação em pairs trading.

**Conclusão textual (abstract):**
> *"Os resultados dos experimentos apresentam evidências inconclusivas; sugerindo que este problema é sujeito a um grande risco de sobreajuste na otimização."*

**Méritos:**
- Validação em duas etapas (benchmark → dados reais)
- Separação treino/teste explícita
- Discussão honesta de limitações
- Walk-forward na análise de cointegração

**Falhas:**
- Espaço de busca pequeno (3 dimensões)
- Implementação própria dos algoritmos (risco de bugs)
- Sem código disponível

**O que aproveito:**

| Elemento | Valor | Uso no TCC |
|----------|-------|------------|
| **Evidência negativa** | ⭐⭐⭐⭐⭐ | Valida decisão de NÃO usar otimização heurística |
| **Cautionary tale** | ⭐⭐⭐⭐⭐ | Ancora abordagem de filtros determinísticos |
| **Estrutura de limitações** | ⭐⭐⭐ | Template para Seção 3.10 |

**Veredito.** Essencial como evidência negativa. Veiga demonstra que otimização heurística de parâmetros de trading não generaliza.

---

### 1.3 Hô Don Lee (USP, Eng. Produção, 2014) — `HoDonLee TCCPRO14.pdf`

**O que li.** Monografia de ~60 páginas. Pairs trading ADR/ORD, implementação Excel + Bloomberg. Conceito central: **tradability** — distinto de cointegração.

**Componentes do tradability:**
1. Mean drift: medição da migração da média
2. Bootstrap (B=2000) do tempo entre mean crossings
3. Regularização Tikhonov-Miller
4. Bandas de trading por desvio que maximiza lucro

**Falhas graves:**
- Implementação em Excel (frágil, não escalável)
- Amostra de 63 dias (minúscula)
- Dependência total de Bloomberg
- Regularização Tikhonov-Miller (escolha não-padrão)

**O que aproveito:**

| Elemento | Valor | Uso no TCC |
|----------|-------|------------|
| **Conceito de tradability** | ⭐⭐⭐⭐ | "Estatisticamente válido" vs. "operacionalmente negociável" |
| **Mean drift** | ⭐⭐⭐ | Medida de estabilidade de regime |
| **Bootstrap** | ⭐⭐⭐ | Intervalos de confiança não-paramétricos |

**Veredito.** Conceito de tradability é aproveitável; implementação, não.

---

### 1.4 Bruno Van Helden (FEA-USP, Economia, 2021) — `Bruno_Van_Helden_Monografia.pdf`

**O que li.** Monografia de 43 páginas. Três sinais: fundamentalista (DRJ, PIB, RM2), técnico (3 cruzamentos MA), híbrido (média → sign()). 12 pares FX, 2010–2020.

**Resultado:** Sharpe > 1 em todos os 6 emergentes; COP 2,90, BRL 0,61.

**Falhas graves:**
| Problema | Severidade |
|----------|------------|
| Dependência Bloomberg | 🔴 Não reprodutível |
| Sem walk-forward | 🔴 Não mede generalização |
| Sem custos de transação | 🔴 Sharpe inflado |
| Look-ahead bias (PIB trimestral em sinal mensal) | 🔴 Provável viés |

**O que aproveito:**

| Elemento | Valor | Uso no TCC |
|----------|-------|------------|
| **Arquitetura de fusão** | ⭐⭐⭐ | Sinais heterogêneos → média → sign() |
| **Evidência de complementaridade** | ⭐⭐ | Híbrido > isolados em 6/6 |

**Veredito.** Útil como ancestral arquitetural. Citar no Cap. 2 com ressalva metodológica. Não usar como benchmark principal (Zhang 2025 é mais rigoroso).

---

## 2. Trabalhos com Empréstimo Metodológico

### 2.1 José Eduardo Athayde Ferrarini (ICMC/USP, MBA IA & BD, 2025) — `JoseEduardoAthaydeFerrarini_TCC_2025.pdf`

**O que li.** 68 páginas. Compara SBERT, BerTimbau, GPT-4/5, Claude, Gemini. Dataset: 5.700 sintéticas + refinamento manual. Teste: 25 amostras manuais. BerTimbau FT: F1 0,939.

**Aproveito:**
- Schema de aspectos (aspecto, polaridade) → similar a (moeda, direção, evento)
- Dataset sintético + refinamento como estratégia de labeling
- **ROC/Youden J para calibrar thresholds** (p. 51–52)
- Discordância entre modelos como sinal de incerteza

**Limitações:** Domínio distante (feedbacks de software), amostra de teste minúscula (25).

---

### 2.2 Rafael Galo Pugina (ICMC/USP, MBA IA & BD, 2024) — `Rafael_Galo_Pugina.pdf`

**O que li.** 56 páginas. Random Forest + SBERT para tickets JIRA. Pipeline de 6 passos.

**Aproveito:**
- SBERT como encoder determinístico e barato
- Embeddings cacheáveis em Parquet
- **Detecção de duplicatas por cosine similarity** → F13

---

### 2.3 Jean Lourenço da Silva (ICMC/USP, MBA IA & BD, 2024) — `Jean_Lourenço_da_Silva.pdf`

**O que li.** 50 páginas. NER em documentos fiscais. Ponto de saturação: ~10k amostras.

**Aproveito:** Orçamento para fine-tuning próprio: 10k manchetes ≈ 300–500h manuais.

---

### 2.4 Bruno Henrique de Brito (ICMC/USP, MBA IA & BD, 2025) — `Bruno_Henrique_de_Brito_TCC_2025.pdf`

**O que li.** 61 páginas. Framework conceitual com grafos de conhecimento.

**Aproveito:**
- **Entity gate (F14):** descartar notícias sem entidades pré-registradas
- Knowledge graph completo: fora de escopo (Neo4j)

---

### 2.5 Bruna Magrini da Cruz (ICMC/USP, MBA IA & BD, 2025) — `Bruna_Magrini_da_Cruz_TCC_2025.pdf`

**O que li.** 56 páginas. TF-IDF + K-Means para incidentes de TI, depois LLM para troubleshooting guides.

**Aproveito:**
- Prompt JSON schema fixo
- **Rubrica manual de qualidade (67% / 78%)** → validação de features LLM

---

## 3. Trabalhos Inacessíveis ou Sem Relação

| Trabalho | Status | Veredito |
|----------|--------|----------|
| Biancardi Aquino (2018) | PDF imagem, 0 caracteres extraídos | Não citável |
| Galvão (2015) | PDF imagem, sem OCR | Não citável |
| Goulart (2024) | Terminologia em saúde | Não relacionado |
| Moura Santos (2024) | Classificação de logs genérica | Future work (news burst) |
| Nogueira (2022) | Arte digital e NFTs | Não relacionado |

---

# Parte II — Especificação Técnica dos Filtros

A cadeia atual (F1–F7) opera na Fase 2 (execução). Os filtros abaixo são adições: F8–F12 na Fase 2, F10–F11, F13–F14 na Fase 1 (percepção).

---

## F8 — Gate de Confirmação por Candlestick (Felix, 2024)

**O que faz.** Bloqueia trade se nenhum padrão candlestick confirmatório apareceu nas últimas $k$ velas. O preço precisa "endossar" o sinal do meta-learner.

**Fase:** 2 (execução). **Tipo:** gate AND.

**Entrada:** OHLC das últimas $k$ velas, direção pretendida (BUY/SELL).

**Pseudocódigo:**
```python
import talib

BULLISH = ['CDLHAMMER', 'CDLMORNINGSTAR', 'CDLENGULFING', 
           'CDL3WHITESOLDIERS', 'CDLPIERCING', 'CDLHARAMI']
BEARISH = ['CDLSHOOTINGSTAR', 'CDLEVENINGSTAR', 'CDLENGULFING',
           'CDL3BLACKCROWS', 'CDLDARKCLOUDCOVER', 'CDLHARAMI']

def gate_candlestick(o, h, l, c, direction, k=5):
    patterns = BULLISH if direction == 'BUY' else BEARISH
    for name in patterns:
        result = getattr(talib, name)(o[-k:], h[-k:], l[-k:], c[-k:])
        if direction == 'BUY' and any(r > 0 for r in result[-3:]):
            return True
        if direction == 'SELL' and any(r < 0 for r in result[-3:]):
            return True
    return False
```

**Parâmetros:** `k=5` (janela). Lista expansível até ~60 padrões do TA-Lib.

**Calibração:** Não requer threshold — é booleano. Ablação: testar subconjuntos (só reversão, só continuação).

**Esforço:** ~30 linhas. TA-Lib já no stack. ⭐ (baixo).

**Posição:** Entre F4 (news-context) e F5 (risk-guard).

---

## F9 — Gate de Viabilidade de Regime / Tradability (Lee, 2014)

**O que faz.** Três sub-checagens simultâneas. Se qualquer uma falhar, o mercado não está "operável".

**Fase:** 2 (execução). **Tipo:** gate AND triplo.

**Pseudocódigo:**
```python
from statsmodels.tsa.stattools import adfuller
import numpy as np

VIABILITY = {
    'atr_k': 2.0,          # desvios-padrão para banda do ATR
    'adf_alpha': 0.05,     # significância do teste ADF
    'max_flips': 3,        # máximo de trocas de polaridade do sentimento
    'n_bars': 60,          # janela para ATR e ADF
    'm_bars': 60,          # janela para estabilidade do sinal
}

def gate_tradability(close, atr, sentiment_signs, cfg=VIABILITY):
    # 1. ATR dentro de banda
    atr_mean, atr_std = np.mean(atr), np.std(atr)
    atr_ok = (atr_mean - cfg['atr_k']*atr_std) < atr[-1] < (atr_mean + cfg['atr_k']*atr_std)
    
    # 2. Preço é mean-reverting (ADF)
    adf_p = adfuller(close, autolag='AIC')[1]
    adf_ok = adf_p < cfg['adf_alpha']
    
    # 3. Sinal textual estável
    polarity = np.sign(sentiment_signs)
    flips = np.sum(np.diff(polarity) != 0)
    signal_ok = flips <= cfg['max_flips']
    
    return atr_ok and adf_ok and signal_ok
```

**Calibração:** Varra `atr_k` ∈ {1.0, 1.5, 2.0, 2.5, 3.0} e `max_flips` ∈ {1..6} no validation span. Alternativa conservadora (Veiga): usar defaults sem calibrar.

**Esforço:** ~50 linhas + statsmodels (ADF). ⭐⭐ (médio).

**Posição:** Primeiro gate da Fase 2. Se regime não é operável, não avalia os demais.

---

## F10 — Gate de Confiança do Scorer Textual (Ferrarini, 2025)

**O que faz.** Suprime probabilidade do news sub-model quando FinBERT está incerto. Usa margem do softmax como proxy de confiança.

**Fase:** 1 (percepção). **Tipo:** gate de qualidade.

**Pseudocódigo:**
```python
def gate_confidence(finbert_margin, news_prob, conf_threshold=0.20):
    """finbert_margin = prob_max - prob_second"""
    if finbert_margin < conf_threshold:
        return 0.5       # neutro: não influencia meta-learner
    return news_prob
```

**Parâmetro:** `conf_threshold` ∈ [0, 1]. Típico: 0.15–0.30.

**Calibração:** Varra 0.05–0.50 (passo 0.05) no validation span. Alternativa: Youden's J (Ferrarini, p. 51–52).

**Esforço:** ~10 linhas. Margem já é subproduto da inferência. ⭐.

**Posição:** Entre scorer FinBERT e news sub-model, na Fase 1.

---

## F11 — Gate de Concordância entre Scorers (Ferrarini, 2025)

**O que faz.** Quando FinBERT e Loughran–McDonald discordam na direção e ambos têm convicção alta, reduz peso do sinal textual.

**Fase:** 1 (percepção). **Tipo:** gate de qualidade.

**Pseudocódigo:**
```python
def gate_agreement(finbert_score, lm_score, agreement_magnitude=0.30):
    same_dir = (finbert_score * lm_score) > 0
    both_confident = (abs(finbert_score) > agreement_magnitude 
                      and abs(lm_score) > agreement_magnitude)
    if not same_dir and both_confident:
        return 0.5     # disputa: reduz peso pela metade
    return 1.0         # concordam ou baixa confiança: peso normal
```

**Variações:** `return 0.0` (suprimir totalmente) vs. `return 0.5` (reduzir).

**Calibração:** Varra `agreement_magnitude` de 0.1 a 0.7 (passo 0.1).

**Esforço:** ~15 linhas. Dois scores já existem. ⭐.

**Posição:** Após F10, antes do news sub-model. Composto: F10 → F11 → news_prob ajustada.

---

## F12 — Gate de Consenso entre Sub-Modelos (Veiga, 2022)

**O que faz.** Exige que pelo menos 3 dos 4 sub-modelos concordem na direção do trade. Filtra sinais onde famílias de features divergem.

**Fase:** 2 (execução). **Tipo:** gate AND.

**Pseudocódigo:**
```python
def gate_submodel_consensus(probs, min_agreement=3):
    """probs: [TA_structural, indicators, patterns, news]"""
    directions = []
    for p in probs:
        if p > 0.55:       directions.append(1)
        elif p < 0.45:     directions.append(-1)
        else:              directions.append(0)
    buy_votes = directions.count(1)
    sell_votes = directions.count(-1)
    return max(buy_votes, sell_votes) >= min_agreement
```

**Parâmetros:** `min_agreement` ∈ {2, 3, 4}, banda neutra [0.45, 0.55].

**Calibração:** Testar `min_agreement` e banda neutra no validation span.

**Esforço:** ~20 linhas. As 4 probabilidades já são computadas. ⭐.

**Posição:** Após meta-learner, antes dos gates de execução.

---

## F13 — Gate de Detecção de Duplicatas (Pugina, 2024)

**O que faz.** Descarta notícias que são near-duplicates de artigos já processados (sindicação de agências).

**Fase:** 1 (percepção). **Tipo:** gate de qualidade.

**Pseudocódigo:**
```python
from sklearn.metrics.pairwise import cosine_similarity

def gate_dedup(embedding, recent_embeddings, threshold=0.95, window=100):
    """embedding: vetor SBERT da notícia atual"""
    if len(recent_embeddings) == 0:
        return True  # primeira notícia
    
    # Só compara com as últimas N notícias (janela deslizante)
    recent = recent_embeddings[-window:]
    sims = cosine_similarity([embedding], recent)[0]
    
    return max(sims) < threshold  # True se não é duplicata
```

**Parâmetros:** `threshold=0.95` (cosine similarity), `window=100` (notícias recentes).

**Esforço:** ~15 linhas + sklearn. Requer SBERT (ou TF-IDF como fallback). ⭐⭐.

---

## F14 — Gate de Relevância por Entidade (Brito, 2025)

**O que faz.** Descarta notícias que não mencionam entidades do conjunto pré-registrado para o par (ECB, Fed, EUR, USD, etc.).

**Fase:** 1 (percepção). **Tipo:** gate de filtragem.

**Pseudocódigo:**
```python
ENTITIES = {
    'EURUSD': {'ECB','Fed','EUR','USD','euro','dollar','Lagarde','Powell',
               'inflation','rates','Germany','US','EU','GDP','CPI'},
    'USDJPY': {'BOJ','Fed','JPY','USD','yen','dollar','Ueda','Powell',
               'inflation','rates','Japan','US','GDP','CPI','carry'},
}

def gate_entity(article_text, pair, min_matches=2):
    text = article_text.lower()
    matches = sum(1 for e in ENTITIES[pair] if e.lower() in text)
    return matches >= min_matches
```

**Parâmetros:** `min_matches=2` (evitar falsos positivos com 1 palavra comum).

**Esforço:** ~20 linhas. Substring search, sem dependências. ⭐.

---

# Parte III — Variações de Estratégia

## Estratégia Core (baseline)
`F1 → F2 → F3 → F4 → F5 → F6 → F7`

## Estratégia A — Baseline + Candlestick (esforço mínimo)
`F1 → F2 → F3 → F4 → F8 → F5 → F6 → F7`  
**Hipótese:** Padrões candlestick reduzem falsos positivos. Espera-se menos trades, hit rate maior.

## Estratégia B — Baseline + Percepção (foco em qualidade textual)
Fase 1: `F10 → F11`  
Fase 2: `F1 → F2 → F3 → F4 → F5 → F6 → F7`  
**Hipótese:** Gates de confiança e concordância melhoram sinal NLP.

## Estratégia C — Baseline + Regime (foco em condições de mercado)
`F9 → F1 → F2 → F3 → F12 → F4 → F5 → F6 → F7`  
**Hipótese:** Operar só em regimes viáveis e com consenso reduz drawdown.

## Estratégia D — Full Hybrid (todos os filtros novos)
Fase 1: `F10 → F11 → F13 → F14`  
Fase 2: `F9 → F1 → F2 → F3 → F8 → F12 → F4 → F5 → F6 → F7`  
**Hipótese:** Múltiplas checagens maximizam Sharpe ajustado a risco (risco: overfiltering).

## Tabela de Ablação para Capítulo 4

| Estratégia | Filtros novos | Esperado | Métrica-chave |
|------------|---------------|----------|---------------|
| Core | Nenhum | Referência | Sharpe, MDD |
| A | F8 | Menos trades, hit rate ↑ | Hit rate, avg holding |
| B | F10, F11 | Sinal textual mais limpo | Contribuição news sub-model |
| C | F9, F12 | Menos trades, drawdown ↓ | MDD, trades/ano |
| D | F8–F14 | Sharpe ↑? (risco: overfilter) | Sharpe, profit factor |

---

# Parte IV — Prioridade de Implementação

Ordenado por relação esforço/impacto:

| # | Filtro | Esforço | Impacto | Dependência | Ordem |
|---|--------|---------|---------|-------------|-------|
| F10 | Confiança do scorer | ⭐ | Alto | Nenhuma | **1º** |
| F11 | Concordância scorers | ⭐ | Médio-alto | Nenhuma | **2º** |
| F14 | Relevância por entidade | ⭐ | Médio | Nenhuma | **3º** |
| F8 | Candlestick | ⭐ | Médio | TA-Lib (já tem) | **4º** |
| F12 | Consenso sub-modelos | ⭐ | Médio | Nenhuma | **5º** |
| F9 | Viabilidade de regime | ⭐⭐ | Alto | statsmodels (ADF) | **6º** |
| F13 | Detecção de duplicatas | ⭐⭐ | Baixo-médio | sklearn | **7º** |

**F10 + F11 + F14:** ~45 linhas, zero dependências novas, implementáveis em uma tarde.

---

# Parte V — Recomendação de Uso na Monografia

| Capítulo | O que entra | De onde |
|----------|-------------|---------|
| Cap. 1 (Introdução) | Gap NLP declarado | Felix |
| Cap. 2 (Fundamentação) | Arquitetura híbrida FX (com ressalvas) | Van Helden |
| Cap. 3 §4 (Price Baseline) | Catálogo candlestick | Felix |
| Cap. 3 §6 (Sentiment) | Prompt JSON Schema, ROC/Youden | Ferrarini, Cruz |
| Cap. 3 §6 (Sentiment) | SBERT fallback, detecção duplicatas | Pugina |
| Cap. 3 §6 (Sentiment) | Ponto saturação ~10k | J.L. Silva |
| Cap. 3 §7 (Filters) | F8 (candlestick), F9 (tradability) | Felix, Lee |
| Cap. 3 §7 (Filters) | F10, F11 (confiança/concordância) | Ferrarini |
| Cap. 3 §7 (Filters) | F12 (consenso), F13 (dedup), F14 (entity) | Veiga, Pugina, Brito |
| Cap. 3 §10 (Threats) | Evidência contra otimização heurística | Veiga |
| Cap. 4 (Avaliação) | Ablações A/B/C/D | Este relatório |
| Cap. 5 (Future Work) | Knowledge graph GDELT, news burst | Brito, Moura Santos |

---

*Análise concluída: 4 trabalhos essenciais, 7 filtros especificados, 5 variações de estratégia para ablação.*
