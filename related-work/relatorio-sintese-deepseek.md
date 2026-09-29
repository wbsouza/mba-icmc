# Trabalhos Correlatos e Catálogo de Filtros — Referência para o Capítulo 3

Documento de consulta para redação da monografia. Duas partes:
1. Análise crítica dos 14 PDFs USP correlatos (Cap. 1 e 2)
2. Catálogo de filtros pós-LLM organizados por fase (Cap. 3 §7)

**Critério de inclusão:** cada filtro deste catálogo usa ferramentas modernas
(LLM contextual, embeddings, detecção algorítmica) e preserva o princípio
atemporal do trabalho original. Implementações baseadas em keyword scan,
desenho manual ou inspeção visual foram descartadas.

Data-base: 2026-05-22.

---

# Parte I — Análise Crítica dos Trabalhos Correlatos USP

Foram lidos 14 PDFs de monografias USP (graduação, MBA e especialização).
Classificação por utilidade para o TCC:

## 1. Trabalhos diretamente relevantes

### 1.1 Van Helden (FEA-USP, Economia, 2021)
**Título.** *Uma Análise Fundamentalista e Técnica do Mercado Cambial
Latino-Americano.*

Constrói três sinais (fundamentalista, técnico, híbrido) sobre 12 pares
cambiais (2010–2020). O modelo híbrido entrega Sharpe > 1 nos 6
emergentes. Arquitetura: sinais heterogêneos mapeados para ±1 → média →
sign(). Estruturalmente idêntica à fusão proposta neste TCC.

**Uso.** Âncora arquitetural para o Capítulo 2 (fusão de sinais heterogêneos).
Limitação: avaliação frágil (período integral, sem walk-forward), dependência
de Bloomberg. Não é benchmark metodológico.

---

### 1.2 Felix (ICMC/USP, MBA IA & BD, 2024)
**Título.** *Swing trading no mercado financeiro: uma abordagem de
machine learning.*

Treina 7 classificadores com 98 indicadores + 8 padrões de candlestick
sobre IBrX-100. Melhor modelo: LGBM (ROC-AUC 0,986). O abstract declara
explicitamente que traders usam "informações textuais na forma de novos
artigos financeiros, mídias sociais e até publicações de analistas econômicos"
— mas o trabalho implementa apenas features de preço.

**Uso.** Evidência de que a lacuna NLP é reconhecida na literatura do
programa (Cap. 1). O LGBM é alternativa computacional ao XGBoost (6×
mais rápido). Catálogo de candlestick patterns como features.

Limitação: split único, sem purging/embargo. ROC-AUC 0,986 em split único
é suspeito. Não é benchmark confiável.

---

### 1.3 Veiga (POLI-USP, MBA Eng. Financeira, 2022)
**Título.** *Otimização de parâmetros de trading com PSO e Algoritmo
Genético — Uma aplicação em pairs trading.*

Implementa 4 variantes de PSO/GA e testa em 14 funções de benchmark
antes de aplicar a pairs trading. Conclusão: "Os resultados dos experimentos
apresentam evidências inconclusivas; sugerindo que este problema é sujeito
a um grande risco de sobreajuste na otimização."

**Uso.** Evidência negativa canônica (Cap. 3 §10): otimização heurística de
parâmetros de trading não generaliza. Justifica a abordagem de filtros
determinísticos com thresholds calibrados por ROC/Youden, não por busca
heurística.

---

### 1.4 Hô Don Lee (POLI-USP, Eng. Produção, 2014)
**Título.** *Pairs trading entre ADRs e ORDs na Bovespa.*

Introduz o conceito de tradability: cointegração estatística ≠ viabilidade
operacional. Componentes: mean drift, bootstrap do tempo entre
cruzamentos, regularização de Tikhonov-Miller, banda de trading que
maximiza lucro esperado.

**Uso.** O conceito de tradability é transferido como gate de viabilidade de
regime (Filtro E9, abaixo). A implementação em Excel de 2014 é obsoleta;
o princípio sobrevive com ATR band + ADF stationarity test + sentiment
stability check.

---

## 2. Trabalhos com empréstimo metodológico parcial

### 2.1 Ferrarini (ICMC/USP, MBA IA & BD, 2025)
Classificação de 15 aspectos em feedbacks de desenvolvedores. Compara
SBERT, BerTimbau, GPT-4, GPT-5, Claude, Gemini. 5700 amostras sintéticas
+ 25 manuais para teste.

**Uso.** (a) Schema de prompt engineering estruturado (JSON fixo) —
transferível para extração de features de notícias. (b) Evidência de que ~5k
amostras rotuladas bastam para fine-tuning competitivo. (c) Gate de
confiança + discordância entre scorers como validação de qualidade.

### 2.2 Pugina (ICMC/USP, MBA IA & BD, 2024)
Classificação de tarefas JIRA com SBERT + RF/LR/GB. Pipeline de 6 passos.

**Uso.** SBERT como encoder determinístico e cacheável — útil como fallback
se chamadas a LLM forem proibitivamente caras ou lentas. Embeddings
materializados em Parquet alinham-se com a arquitetura de features
materializadas.

### 2.3 J. L. Silva (ICMC/USP, MBA IA & BD, 2024)
Compara BERT vs LLMs em NER sobre IRPF. Ponto de saturação: ~10k
amostras.

**Uso.** Quantifica o esforço de fine-tuning próprio (≥10k manchetes
rotuladas, 300–500 horas manuais). Reforça a decisão de usar LLM
zero-shot como abordagem primária, com fine-tuning como variação de
ablação.

### 2.4 Brito (ICMC/USP, MBA IA & BD, 2025)
Framework conceitual: grafos de conhecimento (RDF/OWL/SPARQL) como
camada intermediária entre LLM e dados brutos.

**Uso.** Ideia arquitetural para Trabalhos Futuros (Cap. 5): expor GDELT-GKG
como grafo de entidades/relações ao LLM, em vez de texto bruto.

---

## 3. Trabalhos com empréstimo pontual

### 3.1 Cruz (ICMC/USP, MBA IA & BD, 2025)
Prompt engineering + K-Means (ARI 0,71) + rubrica manual de qualidade.
**Uso:** padrão de JSON Schema validation pós-extração.

### 3.2 Moura Santos (ICMC/USP, MBA IA & BD, 2024)
Classificação de logs de servidores. **Uso:** ideia de "anomaly score em news
stream" como feature não-direcional (Trabalhos Futuros).

---

## 4. Trabalhos inacessíveis ou sem relação

- **Biancardi Aquino (2018):** PDF scaneado como imagem, sem OCR.
- **Galvão (2015):** PDF scaneado como imagem, sem OCR.
- **Nogueira (2022):** Arte digital com IA/NFTs. Zero relação.
- **Goulart (2024):** PLN para terminologia em saúde. Zero relação.

---

## 5. Mapeamento para a monografia

| Capítulo | Conteúdo | Fonte |
|----------|----------|-------|
| Cap. 1 | Gap NLP declarado na literatura do programa | Felix |
| Cap. 2 | Arquitetura híbrida FX como ancestral | Van Helden |
| Cap. 3 §2 | Fusão por média de sinais heterogêneos | Van Helden |
| Cap. 3 §4 | Catálogo de indicadores + candlesticks | Felix |
| Cap. 3 §6 | Prompt engineering estruturado (JSON Schema) | Ferrarini, Cruz |
| Cap. 3 §6 | SBERT como encoder fallback | Pugina |
| Cap. 3 §6 | Ponto de saturação ~10k para fine-tuning | J.L. Silva |
| Cap. 3 §7 | Cadeia de filtros (este catálogo) | Todos + livros |
| Cap. 3 §10 | Evidência negativa: otimização heurística falha | Veiga |
| Cap. 5 | Knowledge graph GDELT → LLM | Brito |

---

# Parte II — Catálogo de Filtros Pós-LLM

Os filtros estão organizados por fase e numerados com prefixo: **P** =
Percepção Agêntica (age sobre features textuais/NLP), **E** = Execução
Determinística (age sobre features de preço/indicadores).

Cada ficha contém: origem, princípio atemporal, implementação moderna,
pseudocódigo, parâmetros e esforço estimado (⭐ = trivial, ⭐⭐ = requer
dependência externa, ⭐⭐⭐ = requer calibração estatística).

---

## Fase 1: Percepção Agêntica (filtros sobre NLP)

### P1 — Gate de confiança mínima do scorer

**Origem.** Ferrarini (2025) — gate de confiança entre scorers na classificação
de aspectos.

**Princípio.** Se o LLM atribui baixa confiança à própria extração de
sentimento, o dado é ruidoso e não deve influenciar decisões de trading.

**Implementação.** O prompt exige que o LLM retorne um campo `confidence`
(0–1) junto com `direction` e `intensity`. Features com confidence < θ são
descartadas antes de entrar no agregador de sentimento.

```
Parâmetro: θ (threshold de confiança)
Calibração: ROC/Youden no validation span.
Esforço: ⭐
```

---

### P2 — Gate de concordância entre scorers

**Origem.** Ferrarini (2025) — dois scorers independentes (ex.: LLM + FinBERT
fallback) devem concordar na direção.

**Princípio.** Dois modelos com arquiteturas diferentes (transformer genérico
vs. fine-tuned financeiro) dificilmente cometem o mesmo erro.

**Implementação.** Se scorer_1.direction ≠ scorer_2.direction, a feature é
descartada. Se ambos concordam, usa-se a média das confianças.

```
Parâmetro: nenhum (gate booleano).
Esforço: ⭐ (requer dois scorers, um já é fallback planejado).
```

---

### P3 — Gate de validação de schema pós-extração

**Origem.** Cruz (2025) — prompt engineering com JSON Schema fixo; Ferrarini
(2025) — extração de tuplas (aspecto, polaridade).

**Princípio.** O output do LLM deve ser estruturalmente válido antes de
entrar no pipeline. Campos obrigatórios ausentes, tipos errados ou valores
fora do domínio esperado indicam falha na extração.

**Implementação.** Validar o JSON retornado contra um schema com campos
obrigatórios: `currency`, `direction` (−1 a 1), `confidence` (0 a 1),
`event_class`, `certainty` (0 a 1).

```
Parâmetro: schema fixo (não calibrável).
Esforço: ⭐ (jsonschema validate).
```

---

### P4 — Gate de relevância por entidade

**Origem.** Brito (2025) — LLM se abstém quando entidades do grafo não estão
conectadas.

**Princípio.** Notícias que não mencionam entidades relevantes ao par
negociado (ex.: ECB, Fed, EUR, USD, Lagarde, Powell para EUR/USD) são
irrelevantes e devem ser descartadas antes do scoring — economizando
custo de inferência.

**Implementação.** Manter um set de entidades por par. Verificar menção
(substring ou NER) antes de enviar ao LLM. Se zero matches, descartar.

```
Parâmetros: entity_set por par, min_matches (default 1).
Esforço: ⭐ (substring matching; spaCy NER opcional).
```

---

### P5 — Gate de qualidade textual mínima

**Origem.** Pugina (2024) — pré-processamento de tickets JIRA; Moura Santos
(2024) — normalização de logs.

**Princípio.** Artigos muito curtos, com proporção anômala de caracteres
não-alfabéticos ou sem timestamp são ruído e não devem consumir cota de
LLM.

**Implementação.** Descartar artigos com: < 30 palavras, < 70% caracteres
alfabéticos, sem timestamp, source não whitelisted.

```
Parâmetros: min_words, min_alpha_ratio, source_whitelist.
Esforço: ⭐.
```

---

### P6 — Gate de detecção de duplicatas (sindicadas)

**Origem.** Pugina (2024) — remoção de duplicatas em tickets JIRA.

**Princípio.** Agências publicam o mesmo fato com texto quase idêntico
(Reuters ↔ Bloomberg ↔ AFP). Contar cada uma como sinal independente
infla artificialmente o peso do evento.

**Implementação.** Calcular embedding SBERT do artigo. Comparar cosine
similarity com embeddings dos últimos N artigos processados. Se
similaridade > 0.95, é duplicata — descartar.

```
Parâmetros: N (janela de comparação), similarity_threshold.
Esforço: ⭐⭐ (requer modelo SBERT local; se não disponível, TF-IDF como
aproximação barata).
```

---

### P7 — Gate de rajada de notícias (information shock)

**Origem.** Moura Santos (2024) — detecção de anomalias em stream de logs.

**Princípio.** Um surto súbito de notícias sobre uma moeda indica choque
informacional — o mercado está digerindo informação nova, o spread pode
alargar e a direção é imprevisível.

**Implementação.** Monitorar taxa de chegada de notícias por minuto para
cada par. Se a taxa atual > rolling_mean + k·σ, bloquear sinais naquele
par por M minutos (período de digestão).

```
Parâmetros: k (threshold de desvio), M (minutos de bloqueio), janela rolante.
Esforço: ⭐ (estatística rolante, O(1) por minuto).
```

---

### P8 — Gate de certeza do consenso (contrarian extremo)

**Origem.** Saettele (2008), caps. 3–4. O princípio é atemporal; a
implementação original (keyword scan: "surge", "plummet", "plunge") está
obsoleta.

**Princípio.** Quando o consenso midiático é unânime e de alta convicção, a
informação já está precificada — o movimento provável é reversão. Saettele
documenta com 14 headlines do WSJ e capas da The Economist ("Euroshambles"
→ fundo do EUR/USD; "Let the Dollar Drop" → topo).

**Implementação pós-LLM.** O LLM extrai `certainty` (0–1) além de
`direction`. Se as últimas N notícias sobre um par têm direção unânime
(>80% mesma direção) e certeza média > 0.7, o consenso é extremo.
Neste caso, o sinal agregado de sentimento é **invertido** (contrarian).

```
Parâmetros: N (janela), unanimity_threshold (ex.: 0.8), certainty_threshold
(ex.: 0.7).
Calibração: testar com e sem inversão no validation span.
Esforço: ⭐⭐ (requer campo certainty do LLM; o resto é estatística simples).
```

---

## Fase 2: Execução Determinística (filtros sobre preço/indicadores)

### E1–E7 — Filtros base (já especificados no plano original)

| # | Filtro | Classe |
|---|--------|--------|
| E1 | Alinhamento de tendência (EMA slope) | Trend |
| E2 | Indicador não sobrecomprado/vendido (Stoch/RSI) | Indicator |
| E3 | Padrão de candle/estrutura | Pattern |
| E4 | Contexto de notícias (sentimento alinhado) | News-context |
| E5 | Stop distance ≤ max risk | Risk guard |
| E6 | Exposição máxima não excedida | Capital mgmt |
| E7 | Horário dentro da sessão líquida | Terminal |

Estes são os filtros do baseline determinístico. Os filtros abaixo (E8–E18)
são extensões extraídas dos trabalhos correlatos e dos livros.

---

### E8 — Confirmação por candlestick (AND gate)

**Origem.** Felix (2024) — 8 padrões de candlestick como features.

**Princípio.** Um padrão de candlestick alinhado com a direção do sinal
aumenta a confiança da entrada. Não é um gerador de sinal — é um
confirmador.

**Implementação.** Para BUY: requer martelo, engolfo de alta, ou doji
no suporte. Para SELL: requer estrela cadente, engolfo de baixa, ou
doji na resistência. O padrão é binário: ou confirma ou não.

```
Parâmetro: quais padrões acionam confirmação.
Esforço: ⭐⭐ (TA-Lib detecta os padrões).
```

---

### E9 — Gate de tradability (viabilidade de regime)

**Origem.** Hô Don Lee (2014) — distinção entre cointegração estatística e
viabilidade operacional.

**Princípio.** Um sinal direcional com p_hat > θ não basta — é preciso
verificar se o regime de mercado está operável. Três condições:
1. Volatilidade dentro de banda: ATR atual entre os percentis 20 e 80 do
   histórico (nem flat, nem caótico).
2. Tendência estacionária: ADF test p-value < 0.05 sobre janela de preços
   (não é random walk puro).
3. Sentimento estável: variância do sentimento nas últimas 24h < threshold.

**Implementação.**
```python
def gate_tradability(atr, atr_percentiles, adf_pvalue, sentiment_var):
    vol_ok = atr_percentiles[20] < atr < atr_percentiles[80]
    trend_ok = adf_pvalue < 0.05
    sent_ok = sentiment_var < sentiment_var_threshold
    return vol_ok and trend_ok and sent_ok
```

```
Parâmetros: percentis da banda ATR, p-value ADF, sentiment_var_threshold.
Calibração: percentis e thresholds no training span.
Esforço: ⭐⭐ (ATR é built-in; ADF requer statsmodels; sentimento é agregado).
```

---

### E10 — Consenso entre indicadores da mesma família

**Origem.** Van Helden (2021) — agrega 3 sinais fundamentalistas em Ct.

**Princípio.** Um indicador isolado gera falsos positivos. Três indicadores
da mesma família (ex.: momentum: RSI, MACD, Stochastic) devem concordar
na direção.

**Implementação.**
```python
def gate_indicator_consensus(rsi_dir, macd_dir, stoch_dir,
                              signal_dir, min_agree=2):
    votes = sum(1 for d in [rsi_dir, macd_dir, stoch_dir]
                if d == signal_dir)
    return votes >= min_agree
```

```
Parâmetro: min_agree (2 de 3).
Esforço: ⭐ (os indicadores já são computados como features; expor direção).
```

---

### E11 — Teto de frequência de trades

**Origem.** Van Helden (2021) — 0,4 a 4,9 trades/ano na estratégia híbrida.

**Princípio.** Excesso de trades corrói retorno por custos de transação e
aumenta probabilidade de whipsaw. Um teto força seletividade.

**Implementação.** Se o número de trades nos últimos D dias úteis > T,
bloquear novas entradas até o próximo período.

```
Parâmetros: T (max trades), D (janela em dias).
Calibração: trade-off entre Sharpe e número de trades no validation span.
Esforço: ⭐.
```

---

### E12 — Confirmação de tendência por Heikin-Ashi

**Origem.** Felix (2024) — Heikin-Ashi como série suavizada.

**Princípio.** Velas Heikin-Ashi eliminam ruído de reversões intradiárias.
K velas HA consecutivas na mesma direção confirmam tendência.

**Implementação.**
```python
def gate_heikin_ashi(ha_open, ha_close, direction, k=3):
    if direction == 'BUY':
        return all(ha_close[-i] > ha_open[-i] for i in range(1, k+1))
    else:
        return all(ha_close[-i] < ha_open[-i] for i in range(1, k+1))
```

```
Parâmetro: k (número de velas consecutivas).
Calibração: grid search 2–5 no validation span.
Esforço: ⭐ (HA é transformação determinística de OHLC, ~10 linhas).
```

---

### E13 — Gate de outlier no espaço de features (PCA)

**Origem.** Felix (2024) — PCA preservando 95% de variância.

**Princípio.** Se o vetor de features atual tem alto erro de reconstrução sob
PCA (calibrado no training span), é um ponto fora da distribuição de
treinamento — o modelo nunca viu nada parecido. Suprimir sinal.

**Implementação.**
```python
def gate_pca_outlier(features, pca, threshold_percentile=95):
    reconstructed = pca.inverse_transform(pca.transform(features))
    error = np.mean((features - reconstructed) ** 2)
    return error < error_threshold
```

```
Parâmetro: threshold (percentil 95 do erro no training span).
Esforço: ⭐⭐ (PCA por walk-forward step; projeção O(n_components) por bar).
```

---

### E14 — Gate de estabilidade do meta-learner pós-retreinamento

**Origem.** Veiga (2022) — monitoramento de convergência dos otimizadores.

**Princípio.** Após cada walk-forward retreinamento, as predições podem
oscilar nos primeiros minutos. Um burn-in ou monitor de variância evita
trades em período instável.

**Implementação.**
```python
def gate_model_stability(p_hat_history, var_threshold=0.05, window=30):
    if len(p_hat_history) < window:
        return True
    return np.var(p_hat_history[-window:]) < var_threshold
```

```
Parâmetros: window (minutos), var_threshold.
Calibração: testar com e sem burn-in no validation span.
Esforço: ⭐.
```

---

### E15 — Concordância entre sub-modelos (nível meta-learner)

**Origem.** Veiga (2022) — compara 4 variantes de otimizadores.

**Princípio.** Se os 4 sub-modelos (TA-structural, indicators, patterns, news)
discordam sobre a direção, o meta-learner está inseguro. Exigir 3 de 4.

**Implementação.**
```python
def gate_submodel_consensus(probs, min_agree=3):
    directions = [1 if p > 0.55 else -1 if p < 0.45 else 0 for p in probs]
    buy_votes = sum(1 for d in directions if d == 1)
    sell_votes = sum(1 for d in directions if d == -1)
    return max(buy_votes, sell_votes) >= min_agree
```

```
Parâmetro: min_agree (3 de 4) e banda de neutralidade [0.45, 0.55].
Esforço: ⭐ (as probabilidades individuais já são saída do meta-learner).
```

---

### E16 — Gate de mean drift (mercado em tendência direcional forte)

**Origem.** Hô Don Lee (2014) — mean drift no spread residual.

**Princípio.** Se o coeficiente angular da regressão linear sobre o preço
recente é grande (normalizado por σ), o mercado está em tendência
direcional. Sinais contrários à tendência têm baixa probabilidade.

**Implementação.**
```python
def gate_mean_drift(close, threshold=0.5):
    x = np.arange(len(close))
    slope, _, _, _, _ = stats.linregress(x, close)
    normalized = slope / np.std(close)
    return abs(normalized) < threshold
```

```
Parâmetro: threshold, window (barras para regressão).
Calibração: testar thresholds via grid no validation span.
Esforço: ⭐.
```

---

### E17 — Gate de zona de suporte/resistência algorítmica

**Origem.** Nekritin & Peters (2012), caps. 4–5; Martinez (2007), cap. 6.

**Princípio.** Trades executados longe de zonas de suporte/resistência têm
R:R pior e maior probabilidade de whipsaw. A zona é uma *área* onde o
preço reverteu ao menos 2 vezes.

**Implementação (pós-LLM, algorítmica).** Detectar pivots (swing highs/lows)
por *rolling window extremum*. Clusterizar pivots próximos (< 0.3·ATR) em
zonas. Só permitir entrada se preço atual está a menos de 1.5·ATR de uma
zona alinhada com a direção (suporte para BUY, resistência para SELL).

```
Parâmetros: pivot_window, zone_cluster_distance (ATR multiplier),
max_entry_distance (ATR multiplier).
Esforço: ⭐⭐ (detecção de pivots O(n); clusterização offline).
```

---

### E18 — Gate de momentum run (não fadeie tendência forte)

**Origem.** Miner (2008), cap. 2.

**Princípio.** Em tendência forte, osciladores podem permanecer em zona
extrema (>80 ou <20) por dezenas de barras sem reversão. Vender "porque
Stoch está sobrecomprado" é a armadilha clássica de momentum.

**Implementação.**
```python
def gate_momentum_run(stoch, direction, k=8, ob=80, os=20):
    if direction == 'BUY':
        # Se quero comprar, verifico se o mercado está em queda explosiva
        return sum(1 for v in stoch[-k:] if v < os) < k
    else:
        # Se quero vender, verifico se o mercado está em alta explosiva
        return sum(1 for v in stoch[-k:] if v > ob) < k
```

```
Parâmetros: k (barras consecutivas), ob_level, os_level.
Esforço: ⭐.
```

---

## Tabela-resumo e priorização

| # | Filtro | Fase | Origem | Esforço | Impacto esperado |
|---|--------|------|--------|---------|------------------|
| P1 | Confiança do scorer | 1 | Ferrarini | ⭐ | Remove ruído de baixa qualidade |
| P2 | Concordância entre scorers | 1 | Ferrarini | ⭐ | Reduz falsos positivos |
| P3 | Validação de schema JSON | 1 | Cruz, Ferrarini | ⭐ | Garante input íntegro |
| P4 | Relevância por entidade | 1 | Brito | ⭐ | Economiza custo LLM + reduz ruído |
| P5 | Qualidade textual mínima | 1 | Pugina, Moura Santos | ⭐ | Filtro básico de spam |
| P6 | Detecção de duplicatas | 1 | Pugina | ⭐⭐ | Evita overcounting de eventos |
| P7 | Rajada de notícias | 1 | Moura Santos | ⭐ | Protege em choques informacionais |
| P8 | Certeza do consenso (contrarian) | 1 | Saettele (atualizado) | ⭐⭐ | Captura exaustão de tendência |
| E1–E7 | Filtros base | 2 | Plano original | ⭐ | Baseline determinístico |
| E8 | Confirmação por candlestick | 2 | Felix | ⭐⭐ | Confirmação de entrada |
| E9 | Tradability (viabilidade) | 2 | Hô Don Lee | ⭐⭐ | Evita regimes inoperáveis |
| E10 | Consenso entre indicadores | 2 | Van Helden | ⭐ | Reduz falsos positivos técnicos |
| E11 | Teto de frequência | 2 | Van Helden | ⭐ | Protege capital |
| E12 | Heikin-Ashi | 2 | Felix | ⭐ | Confirmação de tendência |
| E13 | PCA outlier | 2 | Felix | ⭐⭐ | Protege em regimes nunca vistos |
| E14 | Estabilidade pós-retreinamento | 2 | Veiga | ⭐ | Evita trades em período instável |
| E15 | Consenso entre sub-modelos | 2 | Veiga | ⭐ | Fortalece confiança do sinal |
| E16 | Mean drift | 2 | Hô Don Lee | ⭐ | Evita sinais contra tendência forte |
| E17 | Zonas de S/R algorítmicas | 2 | Nekritin, Martinez | ⭐⭐ | Melhora R:R das entradas |
| E18 | Momentum run | 2 | Miner | ⭐ | Evita a armadilha clássica |

**Ordem de implementação recomendada:**

1. Primeiro dia: P1, P3, P4, P5 (4 filtros, ~30 linhas, zero novas dependências)
2. Segundo dia: E10, E11, E12, E14, E16, E18 (6 filtros, ~60 linhas, zero novas dependências)
3. Terceiro dia: E15, E8 (2 filtros, ~20 linhas, TA-Lib já no stack)
4. Quarta dia: P8 + E9 + E13 (3 filtros, ~80 linhas, requerem PCA/ADF/LLM certainty)
5. Quinto dia: P6 + P7 + E17 (3 filtros, ~100 linhas, requerem SBERT + clusterização)

---

## Variações de estratégia para o Capítulo 4

Para ablação no Capítulo 4, testar quatro configurações:

| Variação | Filtros ativos | Hipótese |
|----------|----------------|----------|
| A (baseline) | E1–E7 apenas | Filtros mínimos; medir Sharpe base |
| B (+percepção) | A + P1–P8 | Filtros de NLP melhoram qualidade do sinal textual |
| C (+execução) | A + E8–E18 | Filtros técnicos melhoram timing das entradas |
| D (full) | A + P1–P8 + E8–E18 | Efeito combinado; risco de overfiltering |

A variação D pode sofrer de *overfiltering* — poucos trades passam por
todos os gates e a amostra de trades é pequena demais para inferência
estatística (alerta de Veiga, 2022). Reportar número de trades por variação.

---

## O que foi excluído e por quê

| Filtro excluído | Razão |
|-----------------|-------|
| Keyword scan ("surge", "plummet") | Substituído por P8 (LLM certainty contextual) |
| COT positioning extreme | COT é para futuros, spot FX não tem contrapartida direta |
| Trend line drawing quality rules | Visual/manual; substituído por detecção algorítmica de zonas (E17) |
| Big Shadow closing quality | Incluído no E8 (candlestick patterns via TA-Lib) |
| Bootstrap time-to-reversal (F20) | Complexidade desproporcional ao benefício; E9 (tradability) cobre |
| Opening range breakout timing | FX é 24h; conceito de "opening range" não se aplica |
| Chandelier Exit stop filter | Gestão de posição, não filtro de entrada; pertence à camada de execução |
| Volume/open interest confirmation | FX spot não tem volume centralizado; tick count é proxy fraco |
| Multiple time frame separate rules | Já está implícito nas features multi-TF que alimentam o meta-learner |

---

## Referência rápida de siglas

| Sigla | Significado |
|-------|-------------|
| ADF | Augmented Dickey-Fuller test (estacionariedade) |
| ATR | Average True Range (volatilidade) |
| CPCV | Combinatorial Purged Cross-Validation |
| HA | Heikin-Ashi (velas suavizadas) |
| PCA | Principal Component Analysis |
| ROC | Receiver Operating Characteristic |
| SBERT | Sentence-BERT (embeddings semânticos) |
| S/R | Suporte / Resistência |
| Stoch | Stochastic Oscillator |
