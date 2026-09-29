# Ideias dos Livros Clássicos — Triagem Pós-LLM

Levantamento dos livros de trading/quant em `~/Documents/mba/tcc/books/` aplicáveis a este TCC (*Algorithmic Trading Enhanced by AI: Using News, Geopolitical Events and NLP-Based Sentiment in Forex Decision-Making* — EUR/USD e USD/JPY, 2015-02-19 a 2024-12-31, perception agêntica + execução determinística, CPCV + walk-forward).

**Critério de triagem.** Só entra material que continua válido na era LLM. Métodos baseados em **keyword matching** (matching de "plummet/surge/plunge") foram **superados** por scorers contextuais (FinBERT, GPT-4) que captam negação, sarcasmo, qualificadores condicionais e contexto multi-frase. Hard data (positioning, intermarket, options-implied) e métodos estatísticos atemporais (Monte Carlo Permutation, CPCV, shrinkage) permanecem válidos. Dados com latência semanal/mensal (IMM CoT, TIC) são obsoletos no hot path mas relevantes como baseline histórico.

Cada livro foi skim-lido com leitura direta de TOC + capítulos-chave + tabelas; páginas conferidas.

---

## 1. Livros que entram diretamente na metodologia

### ★★★ Aronson (2007) — *Evidence-Based Technical Analysis*

**Citação completa.** David R. Aronson, *Evidence-Based Technical Analysis: Applying the Scientific Method and Statistical Inference to Trading Signals*, Wiley Trading, 2007, 544 p., ISBN 978-0-470-00874-4.

**Atemporal pós-LLM?** **Sim.** Toda a estatística de validação de regras de trading é independente de como o sinal foi gerado. Aplica-se a sinais técnicos, NLP-derivados ou agênticos sem perda.

**Capítulo central — Cap. 6 "Data-Mining Bias: The Fool's Gold of Objective TA" (pp. 255-329).**

- **Definição canônica de data-mining bias (p. 256):** *"the expected difference between the observed performance of the best rule and its expected performance"*. Frase ideal para abrir a Seção 3.10 (Threats to Validity).
- **Cinco fatores que escalam o viés (pp. 295-319):** (i) número de regras testadas; (ii) número de observações; (iii) correlação entre regras; (iv) caudas pesadas nos retornos; (v) variância nos retornos esperados entre regras. Estrutura ideal para uma tabela de ameaças à validade.
- **Correção analítica de Markowitz–Xu (pp. 323-324):** $H' = R + B(H - R)$, com $H$ retorno observado da melhor regra, $R$ média do universo, $B$ shrinkage em $[0, 1]$. Correção post-hoc trivial de aplicar nas Sharpe ratios reportadas.
- **White's Reality Check (pp. 325-327):** bootstrap das daily returns com reposição, demean por regra para impor H₀, distribuição amostral do máximo retorno sobre N regras.
- **Monte Carlo Permutation Test (Tim Masters, pp. 327-329):** pareia output da regra (+1/−1) com retornos de mercado embaralhados *sem reposição*, preservando estrutura de correlação entre regras. Testa H₀ diferente do WRC: "regra-output randomicamente correlacionado com retorno futuro". **Este é o teste a usar neste TCC** porque os filtros F1–F16 compartilham componentes e são correlatos.

**Ação concreta na monografia.**

- **Cap 3 §3.10 (Threats to Validity):** adicionar subseção "Data-mining bias and rule-level significance" citando Aronson como fonte do conceito e do teste. Reportar Monte Carlo Permutation Test (M = 1000 permutations) sobre cada variante da cadeia avaliada no Cap 4.
- **Snippet pronto:**

```latex
A rule that survives walk-forward and combinatorial purged
cross-validation may still owe its observed performance to the
multiple-comparisons inherent in any rule-screening exercise.
\cite{aronson2007evidence} formalises this as data-mining bias,
defined as ``the expected difference between the observed performance
of the best rule and its expected performance'' (p.~256), and shows
that the magnitude of the bias scales with the number of rules tested,
the rule-correlation structure, and the heavy-tailedness of the
return distribution (Ch.~6, pp.~295--319). Following the
\citeauthor{aronson2007evidence} recommendation for correlated rule
universes, each candidate filter combination evaluated in
Chapter~\ref{cap:experimental-evaluation} is subjected to the
Monte~Carlo Permutation Test \cite{aronson2007evidence}[pp.~327--329]
with $M = 1000$ permutations, and only configurations whose observed
Sharpe ratio exceeds the 95th percentile of the permutation
distribution are reported as significant.
```

---

### ★★★ Jansen (2020) — *Machine Learning for Algorithmic Trading, 2nd ed.*

**Citação completa.** Stefan Jansen, *Machine Learning for Algorithmic Trading: Predictive Models to Extract Signals from Market and Alternative Data for Systematic Trading Strategies with Python*, 2nd ed., Packt Publishing, 2020, 858 p., ISBN 9781839217715.

**Atemporal pós-LLM?** **Sim**, e particularmente bem alinhado: Jansen pré-LLM (2020) mas já cobre Cap. 14 (Text Data for Trading), Cap. 16 (Word Embeddings), Cap. 19 (RNNs for Sentiment). A escolha de framework (CPCV, deflated Sharpe, purging + embargoing) é puramente metodológica.

**Capítulos centrais.**

- **Cap. 6 "The Machine Learning Process" (p. 200):** seção "Purging, embargoing, and combinatorial CV" — implementação CPCV em Python via biblioteca `timeseriescv`. Cita López de Prado 2018 como fonte primária mas dá o caminho operacional.
- **Cap. 8 "ML4T Workflow", pp. 253-265:** checklist de pitfalls (look-ahead, survivorship, outlier control, mark-to-market, transaction costs, decision timing). Arquiteturas `backtrader` e `Zipline` com point-in-time bundles.
- **Cap. 8 referencia Bailey, Borwein, López de Prado (2016) — Deflated Sharpe Ratio + Minimum Backtest Length:** quantifica quantas estratégias independentes podem ser legitimamente testadas antes de a descoberta espúria dominar. **2 anos de dados diários → ~7 estratégias; 5 anos → ~45**. Restrição operacional dura sobre quantas variantes F8–F16 podem ser triadas no período 2015-2024.
- **Cap. 14 Text Data for Trading:** Jansen cobre TF-IDF, BoW, naive bayes, sklearn pipelines para sentimento. Hoje superado por FinBERT/LLM contextuais — citar apenas como evolução histórica.
- **Bibliografia (linha 30407):** cita Araci 2019 (FinBERT) — referência primária já no `references.bib` da monografia.

**Ação concreta na monografia.**

- **Cap 3 §3.8 (Evaluation Protocol):** citar Jansen como implementação operacional do CPCV com a biblioteca `timeseriescv`. Reportar deflated Sharpe alongside vanilla Sharpe.
- **Cap 3 §3.10:** trazer o resultado de Bailey-Borwein-López como limite formal sobre número de variantes F8–F16 testáveis na janela 2015-2024.
- **Snippet pronto:**

```latex
The 10-year evaluation window 2015-02-19 to 2024-12-31 also bounds the
number of strategy variants the present work may legitimately screen.
\cite{bailey2016probability} formalise this as the deflated Sharpe
ratio and the minimum backtest length: at roughly $T = 10$ years of
daily data, the false-discovery threshold permits on the order of
sixty independent strategy variants, beyond which the probability of
backtest overfitting becomes the dominant explanation for any
out-of-sample edge. The ablation set in
Chapter~\ref{cap:experimental-evaluation} is therefore capped at
\textit{N} = X variants, and the headline Sharpe ratios are reported
alongside their deflated counterparts.
```

---

### ★★★ Halls-Moore (2015) — *Successful Algorithmic Trading*

**Citação completa.** Michael L. Halls-Moore, *Successful Algorithmic Trading*, QuantStart, 2015 (self-published).

**Atemporal pós-LLM?** **Sim.** Engenharia de backtester e taxonomia de viéses não dependem de paradigma de sinal.

**Capítulos centrais.**

- **Cap. 3 (Successful Backtesting), pp. 16-17:** taxonomia limpa de quatro viéses — **Optimisation Bias, Look-Ahead Bias, Survivorship Bias, Cognitive (Psychological) Bias**. Mais simples que a enumeração de López de Prado e usável diretamente na Seção 3.10.
- **Cap. 3 §3.3.3 (p. 19) — *Single-venue ECN rule*:** *"Brokers are not obligated to share trade prices ... use single-venue bid-ask quotes."* Restrição direta sobre o pipeline de dados deste TCC: comprometer-se com **uma** corretora de FX (Dukascopy demo per `specs.md`), nunca quote composto.
- **Cap. 14 (pp. 129-141) — Event-driven backtester:** hierarquia de classes `MarketEvent → SignalEvent → OrderEvent → FillEvent`, abstract `DataHandler` "drip feed" (p. 135), `FillEvent` com modelo de comissão IB (p. 133-134). *"With an event-driven backtester there is no lookahead bias as market data receipt is treated as an 'event' that must be acted upon"* (p. 130). Skeleton de classe Python copiável.
- **Cap. 16 §16 (p. 188):** *"technically it is not appropriate to use simple cross-validation techniques on temporally ordered data."* Halls-Moore sinaliza o problema; Jansen Cap. 6 e López de Prado fornecem a solução (CPCV). Citar os três em conjunto fortalece a defesa da escolha de CPCV.

**Ação concreta na monografia.**

- **Cap 3 §3.10:** adotar a taxonomia de quatro viéses como estrutura da subseção.
- **Cap 3 §3.5 (Price-Data Pipeline):** justificar a escolha de venue único citando Halls-Moore §3.3.3.
- **Cap 3 §3.9 (Execution Engine):** citar o padrão event-driven de Cap. 14 como fundação de design — o presente engine implementa o mesmo padrão (MarketEvent → SignalEvent → OrderEvent → FillEvent).

---

## 2. Livros que contribuem com filtros / features concretos

### ★★★ Chan (2013) — *Algorithmic Trading: Winning Strategies and Their Rationale*

**Citação completa.** Ernest P. Chan, *Algorithmic Trading: Winning Strategies and Their Rationale*, John Wiley & Sons, 2013, ISBN 9781118460146. Já citado de passagem na monografia.

**Atemporal pós-LLM?** **Sim** nas partes empíricas-quantitativas (cointegração FX, rollover, VIX threshold). A passagem sobre sentiment (RavenPack) é pré-LLM no scorer mas a *arquitetura* (sentiment-as-factor em portfolio sorting) sobrevive.

**Contribuições borrowable.**

- **Cointegração USD.AUD vs USD.CAD via Johansen (Ch. 5, pp. 107-114, Exemplo 5.1):** APR 11%, Sharpe 1.6 (Dez 2009 a Abr 2012). Demonstração empírica de mean-reversion via cointegração em pares FX — paralelo conceitual ao F14 (tradability) do Hô Don Lee mas com aplicação direta em FX. Não substituí, complementa Lee.
- **Rollover swap obrigatório no P&L (Ch. 5, eq. 5.6, pp. 113-114):** diferencial de carry domina retorno multi-dia em FX. Erro estrutural ignorar — entra no Cap 3 (custos de transação) deste TCC.
- **News-sentiment como fator fundamental cross-sectional (Ch. 6, p. 148):** Chan cita Hafez & Xie (2012) reportando APR 52-156% e Sharpe 3.9-5.3 long-top-decile/short-bottom-decile de sentiment em S&P 100. Sharpes acima do plausível são alarme (cf. López de Prado), mas o resultado **valida arquiteturalmente** o uso de sentiment como sinal independente em fusão tardia. **Aviso pós-LLM:** Hafez & Xie usaram RavenPack 2012 (scorer keyword + regra); um replication com FinBERT/GPT-4 deveria reduzir os retornos (menos ruído) mas manter a direção.
- **VIX > 35 como gate de risco (Ch. 8, pp. 184-185):** mean-reversion FSTX cai de APR 13% para 2.6% quando VIX > 35. Linha-base empírica para o filtro F4 / F9 (risk-off gate). Complementa Laidi (que dá VIX↔USD/JPY mas sem cutoff numérico).
- **Stop-loss inadequado para mean-reversion (Ch. 8, p. 182):** F15/F8 deste TCC precisam distinguir pernas de reversão de pernas momentum. Stop-loss simétrico viola a tese de mean-reversion.

**Aplicação ao TCC.**

- **Cap 2 §2.2 ou §2.5:** Chan (Hafez & Xie) como evidência empírica adicional de "sentiment-as-factor" — complemento ao Tetlock 2007 (equities) na motivação do Cap 1.
- **Cap 3 §3.5 (Price Pipeline):** incluir rollover swap por eq. 5.6 no cálculo de retorno overnight.
- **F4 / F9 (risk gate):** VIX > 35 como threshold concreto inicial, com calibração via Aronson MCP test.

---

### ★★★ Laïdi (2009) — *Currency Trading and Intermarket Analysis*

**Citação completa.** Ashraf Laïdi, *Currency Trading and Intermarket Analysis: How to Profit from the Shifting Currents in Global Markets*, Wiley Trading, 2009, 305 p., ISBN 9780470226230.

**Atemporal pós-LLM?** **Sim.** Correlações cross-asset (gold↔USD, VIX↔JPY, S&P↔USD/JPY) são quantidades hard-data, não textuais. Permanecem válidas pós-LLM.

**Cap. 5 "Risk Appetite in the Markets" (pp. 111-135)** é o capítulo mais relevante de todo o conjunto de livros para este TCC, dado que **USD/JPY 2024 é o teste out-of-sample da H1**.

- **Correlação gold↔USD = −0.84** sobre janela 1999-01 a 2008-05 (Fig. 1.3, p. 7).
- **Painel de correlações rolling 6-meses (Fig. 1.10, pp. 14-15):** EUR/gold ≈ +0.53; **JPY/gold ≈ +0.39** (a menor de todas as G-10); USDX/gold ≈ −0.53.
- **Quadro estrutural (pp. 115-116, Fig. 5.1):** países com superávit de conta corrente (JPY, CHF) têm juros estruturalmente baixos e são funding currencies; países com déficit (USD, GBP, AUD) pagam juros mais altos. Mecanismo do carry trade em uma página.
- **VIX como trigger de unwind do carry USD/JPY (pp. 123-126, Figs. 5.7-5.9):** picos de VIX coincidem com rallies do yen (queda do USD/JPY) por unwind forçado.
- **Correlação USD/JPY ↔ S&P 500 a partir de Junho de 2004 (Fig. 5.5, p. 120):** estruturalmente positiva pós-2004 — *ruptura estrutural antes inexistente*. Importante para regime-aware features.
- **Janela intraday de unwind do yen (p. 123):** ganhos rápidos do yen entre 4 PM EST (fechamento US equity) e 8 PM EST (abertura Tóquio), volume baixo, volatilidade alta. Filtro de horário concreto.
- **Calibração de cauda — 1998 LTCM yen-unwind (pp. 118-119):** dólar caiu de 130.70 para 118.90 em um dia, 7%, maior que o diferencial de juros de 5% entre as moedas. Pior-caso histórico para stress test.

**Aplicação ao TCC.**

- **Cap 1 §1.4:** uma frase invocando Laidi para sustentar a hipótese de que USD/JPY tem comportamento dirigido por risco macro (VIX) — justifica a inclusão de features intermarket.
- **Novo filtro F17 (cross-market risk-off gate):** bloquear posições long USD/JPY quando (a) VIX > 35 *(threshold de Chan)* OU (b) correlação rolling 20-dia gold↔USD ∈ [-1, -0.4] *(faixa de Laidi)* OU (c) horário 21:00-01:00 UTC (janela de unwind do yen). Cláusula AND com a saída do meta-learner.
- **Novo filtro F18 (S&P alignment gate, USD/JPY only, pós-2004):** quando retorno diário do S&P e direção proposta para USD/JPY divergem por mais de 1.5σ, suprimir entrada. **Não aplica ao EUR/USD.**

---

### ★★ Saettele (2008) — *Sentiment in the Forex Market*

**Citação completa.** Jamie Saettele, *Sentiment in the Forex Market: Indicators and Strategies to Profit from Crowd Behavior and Market Extremes*, Wiley Trading, 2008, 211 p., ISBN 9780470208236.

**Atemporal pós-LLM?** **Parcial.** Aproveitar Cap. 5 (indicadores hard-data); **descartar** Cap. 4 (taxonomia de headlines).

**MANTÉM (hard-data positioning, ortogonal ao NLP):**

- **Composite COT + COT Index percentile (Cap. 5, pp. 83-86):** `Composite COT = net speculativo − net comercial`, depois rank-transformado por percentile sobre janela móvel de 52 semanas → índice 0-100. Index = 100 → extremo bullish; Index = 0 → extremo bearish. **Sinal contrarian hard-data, completamente ortogonal a FinBERT.**
- **Regra de três-linhas para extremos de sentimento (p. 91):** virada sinalizada apenas quando COT Index, Spec %Long Ratio Index *e* Comm %Long Ratio Index simultaneamente cruzam 0 ou 100. Lógica de multi-confirmação direta para a cadeia.
- **FXCM Speculative Sentiment Index (SSI, pp. 94-95):** order-book líquido do retail, indicador contrarian, atualizado duas vezes ao dia. "Mais de 50% long favorece fraqueza".
- **Risk-reversal em opções 25-delta como sentimento (pp. 99-100):** `RR = vol call − vol put`, correlação positiva com spot. Série market-implied intraday, ortogonal ao FinBERT.
- **Convenção crítica USD-base vs JPY-base (p. 76):** leituras COT bullish em JPY (futures CME) correspondem a topos no USD/JPY (spot). Convenção essencial para qualquer feature COT em USD/JPY neste TCC.

**DESCARTA (superado por LLM):**

- **Cap. 4 "Using News Headlines to Generate Signals" (pp. 53-67):** taxonomia keyword de "plummet/surge/plunge/soar". Lista de 73 manchetes com reversões empíricas. **Não citar como filtro.** FinBERT/LLM moderno captura o mesmo sinal (manchetes de pico extremo geralmente vêm com qualifiers, conjunturas e contexto que keyword matching perde) com menos ruído. Reconhecer como antecedente histórico apenas no Cap 2 caso seja útil.

**Aplicação ao TCC.**

- **Novo filtro F19 (sentiment-extreme veto):** suprimir entradas quando o triplo `(COT Index, Spec %Long Ratio, Comm %Long Ratio)` se alinha em ≥ 95 ou ≤ 5 contra a direção proposta pelo meta-learner. **Dado o ortogonal ao FinBERT, F19 acrescenta canal de sentimento genuinamente independente — não duplicação.**
- **Feature adicional opcional:** risk-reversal 25-delta como input à fusão (se Dukascopy ou outra fonte oferece dado de opções FX). Saettele pp. 99-100.

---

### ★★ Bulkowski (2005) — *Encyclopedia of Chart Patterns*

**Citação completa.** Thomas N. Bulkowski, *Encyclopedia of Chart Patterns*, 2nd ed., Wiley Trading, 2005, 1035 p., ISBN 978-0-471-66826-8. Já citado em `specs.md`.

**Atemporal pós-LLM?** **Sim.** Padrões de candlestick/chart são features de input ao modelo; o LLM não compete com eles. Quantitativo.

**Conteúdo relevante.**

- **Disclosure de base de dados (pp. 3-4):** 500 + 200 + 300 ações, 1991-2004, 38.500+ amostras, busca manual + computadorizada, exclusão de ações abaixo de $1. Bar de transparência para a descrição de dados na Seção 3.4 deste TCC.
- **Rank methodology (p. 965):** cada padrão recebe 3 sub-ranks — média de rise/decline + break-even failure rate + change após tendência terminar — e a soma é re-rankeada. **Metodologia atemporal de scoring de padrões.**
- **Top padrões por Overall Rank (bull market):** Flags HT (Ch. 22, pp. 350-361) com +69%; HS Tops down breakout (Ch. 26, pp. 405-420) com -22%; Diamond Bottoms (Ch. 11, pp. 179-195) com -21%; Pipe Bottoms (Ch. 35, pp. 536-549) com +45%; Eve-Eve Double Tops (Ch. 20, pp. 321-334) com -18%. Cada um com tabela de performance própria. **Baselines empíricos para o F8 (candlestick-confirmation gate).**
- **Tall-pattern effect (Tabela 63.6, p. 960):** padrões com `altura / preço-breakout` acima da mediana superam padrões "curtos" em aproximadamente 2× (29% vs. 20% para stock-upgrade bull-up). **Aplicação direta:** usar altura do padrão como feature contínua, não flag binário.
- **Throwback/pullback hurts performance (p. 964):** quando há pullback através do nível de breakout dentro de N barras, performance subsequente cai. Filtro adicional ao F8.
- **Aviso de transparência (p. 8):** *"Statistics: I Don't Believe the Numbers"* — Bulkowski explicita que +69% representa "253 perfect trades with no commissions". Bar de honestidade para o Cap 4 (Experimental Evaluation) deste TCC.

**Aplicação ao TCC.**

- **F8 (candlestick-confirmation gate):** refinar com (a) `altura / preço-breakout > mediana histórica do par`, (b) ausência de pullback através do breakout em N barras. **Não cite o número +69% sem contexto** — replica a estatística no próprio dataset deste TCC e reporte com a mesma transparência.

---

### ★★ Henderson (2002) — *Currency Strategy*

**Citação completa.** Callum Henderson, *Currency Strategy: The Practitioner's Guide to Currency Investing, Hedging and Forecasting*, Wiley Finance, 2002, 235 p., ISBN 0-470-84684-4.

**Atemporal pós-LLM?** **Parcial.** Arquitetura e conceitos macro permanecem; dados específicos (IMM CoT semanal, TIC mensal, Salomon Instability Index) **obsoletos** no hot path.

**MANTÉM (arquitetura + conceitos atemporais):**

- **Signal Grid (Cap. 10, Tabela 10.1, p. 204):** decisão por matriz de 4 colunas — *Currency Economics | Flow | Technical | Long-Term Valuation* → Combined signal. Henderson exemplifica com USD/TRL em Jan-2002 (Sell-Sell-Sell-Sell → Sell). **Esta é a versão manual de 2002 da arquitetura de late fusion deste TCC**. Citar como precedente histórico da escolha arquitetural.
- **Speculative Cycle 4-phase model (p. 52):** Phase I fundamentals → trend; Phase II speculators join; Phase III deterioration; Phase IV capitulation. Modelo narrativo de regime, motiva por que features sentiment/event ajudam onde trend-following falha (Phase IV inflection).
- **Risk Appetite Indicators (Tabela 2.1, p. 56):** três regimes — risk-seeking < 40, neutro 40-50, risk-aversion > 50. **JPY explicitamente nomeado como safe-haven funding currency** que recupera quando risk appetite colapsa. Justifica tratar USD/JPY com features regime-aware distintas de EUR/USD.
- **PPP como fair value de longo prazo (p. 18):** Henderson chama PPP candidamente de *"Pretty Poor Predictor"* no curto prazo mas útil em horizonte multi-mensal/anual. Como long-term-valuation anchor opcional.

**DESCARTA (obsoleto pós-LLM/GDELT):**

- **Cap. 3 Flow data list (p. 194):** IMM CoT semanal, US TIC mensal, IIF capital flows trimestral. Todos com lag multi-semana. **Substituídos por GDELT (15-min) + FinBERT intraday** no hot path deste TCC. Reconhecer o pedigree mas não usar como feature.
- **Salomon Smith Barney "Instability Index" (pp. 54-55):** não mais publicado. Substitutos modernos (VIX, MOVE, FRED FSI, GDELT GoldsteinScale + ToneAvg) já citados no plano da monografia.
- **Cap. 4 Charting básico (pp. 85-102):** mainstream, superado por Murphy 1999 + Bulkowski 2005 já citados.
- **Big Mac Index (pp. 22-23):** footnote-quality apenas.

**Aplicação ao TCC.**

- **Cap 2 §2.5 (Hybrid Approaches):** uma frase invocando Henderson Signal Grid p. 204 como antecedente manual da arquitetura de late fusion adotada. Reconhece o caminho intelectual sem importar dados obsoletos.
- **Cap 3 §3.2 (Research Design):** citar Speculative Cycle p. 52 + Risk Appetite Indicators p. 56 ao motivar features regime-aware distintas para USD/JPY (safe-haven funding) vs. EUR/USD.

---

### ★ Twomey (2012) — *Inside the Currency Market*

**Citação completa.** Brian Twomey, *Inside the Currency Market: Mechanics, Valuation, and Strategies*, Bloomberg Financial / Wiley, 2012, 328 p., ISBN 9780470952757.

**Atemporal pós-LLM?** **Sim** nas partes definicionais (Taylor Rule, REER, PPP, Fisher Effect). Não oferece conteúdo estratégico além disso — é enciclopédia de mecânica.

**Conteúdo aproveitável.**

- **Taylor Rule (p. 35):** $i = r^* + \pi + 0.5(\pi - \pi^*) + 0.5(y - y^*)$. Cláusula explícita do benchmark de política monetária.
- **REER / PPP em forma logarítmica (pp. 36-37, 39-40):** $Q_t = S_t - p_t + p_t^*$. Permite benchmark de "fair value" mean-reverting em horizonte longo.
- **Fisher Effect (p. 35):** $(E_1 - E_2)/E_2 \times 100 = i_{\$} - i_{¥}$. Relação juros-câmbio para sanity-check.

**Aplicação ao TCC.**

- **Cap 3 §3.5 ou §3.6:** citações pontuais (uma linha cada) ao apresentar feature de Taylor Rule / REER deviation. Sem desenvolver mais.

---

## 3. Filtros derivados — adições à cadeia consolidada

Numeração continua a do `interesting-ideas-claude-ptbr.md` (F8–F16 já especificados a partir de TCCs). F17–F20 abaixo vêm dos livros.

| # | Filtro | Fase | Origem | Justificativa |
|---|---|---|---|---|
| F17 | **Cross-market risk-off gate** — bloquear posições long USD/JPY se (a) VIX > 35 OU (b) corr rolling 20-dia gold↔USD ∈ [-1, -0.4] OU (c) horário 21:00-01:00 UTC | Execução, AND | Laïdi pp. 115-126 + Chan p. 184 | Captura unwind de carry-trade em risk-off |
| F18 | **S&P alignment gate (USD/JPY only, pós-2004)** — bloquear entrada se retorno diário S&P e direção proposta USD/JPY divergem > 1.5σ | Execução, AND | Laïdi p. 120 Fig. 5.5 | Aproveita ruptura estrutural USD/JPY↔S&P pós-2004 |
| F19 | **Sentiment-extreme veto via positioning** — suprimir entrada quando triplo (COT Index, Spec %Long, Comm %Long) ≥ 95 ou ≤ 5 contra direção proposta | Execução, AND | Saettele p. 91 | Hard-data positioning ortogonal ao FinBERT |
| F20 | **Data-mining significance gate** — antes de admitir configuração ao Cap 4, exigir Sharpe acima do 95-percentil do Monte Carlo Permutation Test (M = 1000) | Configuração offline | Aronson pp. 327-329 | Correção formal de multiple-comparisons em universo de regras correlatas |

**Recomendação operacional.** F20 é metodológico, não de runtime — entra na pipeline de avaliação. F17, F18, F19 são gates AND aplicados após o meta-learner; F19 deve ter prioridade sobre F17/F18 porque é o único que adiciona um canal de sentimento genuinamente independente.

---

## 4. Bibliografia consolidada para `monografia/bib/references.bib`

```bibtex
@book{aronson2007evidence,
  author    = {David R. Aronson},
  title     = {Evidence-Based Technical Analysis: Applying the Scientific
               Method and Statistical Inference to Trading Signals},
  series    = {Wiley Trading},
  publisher = {John Wiley \& Sons},
  address   = {Hoboken, NJ},
  year      = {2007},
  isbn      = {978-0-470-00874-4}
}

@book{jansen2020ml4t,
  author    = {Stefan Jansen},
  title     = {Machine Learning for Algorithmic Trading: Predictive Models
               to Extract Signals from Market and Alternative Data for
               Systematic Trading Strategies with Python},
  edition   = {2nd},
  publisher = {Packt Publishing},
  address   = {Birmingham, UK},
  year      = {2020},
  isbn      = {978-1-83921-771-5}
}

@book{hallsmoore2015,
  author    = {Michael L. Halls-Moore},
  title     = {Successful Algorithmic Trading},
  publisher = {QuantStart},
  address   = {London, UK},
  year      = {2015},
  note      = {Self-published, available at \url{https://www.quantstart.com/}}
}

@book{chan2013algo,
  author    = {Ernest P. Chan},
  title     = {Algorithmic Trading: Winning Strategies and Their Rationale},
  publisher = {John Wiley \& Sons},
  address   = {Hoboken, NJ},
  year      = {2013},
  isbn      = {978-1-118-46014-6}
}

@book{laidi2009intermarket,
  author    = {Ashraf La{\"\i}di},
  title     = {Currency Trading and Intermarket Analysis: How to Profit
               from the Shifting Currents in Global Markets},
  series    = {Wiley Trading},
  publisher = {John Wiley \& Sons},
  address   = {Hoboken, NJ},
  year      = {2009},
  isbn      = {978-0-470-22623-0}
}

@book{saettele2008sentiment,
  author    = {Jamie Saettele},
  title     = {Sentiment in the Forex Market: Indicators and Strategies to
               Profit from Crowd Behavior and Market Extremes},
  series    = {Wiley Trading},
  publisher = {John Wiley \& Sons},
  address   = {Hoboken, NJ},
  year      = {2008},
  isbn      = {978-0-470-20823-6}
}

@book{henderson2002currency,
  author    = {Callum Henderson},
  title     = {Currency Strategy: The Practitioner's Guide to Currency
               Investing, Hedging and Forecasting},
  series    = {Wiley Finance},
  publisher = {John Wiley \& Sons},
  address   = {Chichester, UK},
  year      = {2002},
  isbn      = {0-470-84684-4}
}

@article{bailey2016probability,
  author    = {David H. Bailey and Jonathan M. Borwein and
               Marcos L{\'o}pez de Prado and Qiji Jim Zhu},
  title     = {The Probability of Backtest Overfitting},
  journal   = {Journal of Computational Finance},
  volume    = {20},
  number    = {4},
  pages     = {39--69},
  year      = {2017}
}

@book{bulkowski2005encyclopedia,
  author    = {Thomas N. Bulkowski},
  title     = {Encyclopedia of Chart Patterns},
  edition   = {2nd},
  series    = {Wiley Trading},
  publisher = {John Wiley \& Sons},
  address   = {Hoboken, NJ},
  year      = {2005},
  isbn      = {978-0-471-66826-8}
}

@book{twomey2012inside,
  author    = {Brian Twomey},
  title     = {Inside the Currency Market: Mechanics, Valuation, and
               Strategies},
  series    = {Bloomberg Financial},
  publisher = {John Wiley \& Sons},
  address   = {Hoboken, NJ},
  year      = {2012},
  isbn      = {978-0-470-95275-7}
}
```

---

## 5. Plano de edição da monografia (extensão de E1–E14 do arquivo de TCCs correlatos)

Sequência completa de edições derivadas dos livros, complementando as edições E1–E14 do arquivo `interesting-ideas-claude-ptbr.md`:

| # | Capítulo / Seção | O que adicionar | Origem |
|---|---|---|---|
| L1 | Cap 1 §1.4 | Uma frase invocando Laïdi para suportar a hipótese de que USD/JPY tem dinâmica risk-on/risk-off | Laïdi pp. 115-126 |
| L2 | Cap 2 §2.5 | Henderson Signal Grid p. 204 como precedente manual da arquitetura de late fusion | Henderson |
| L3 | Cap 2 §2.5 ou §2.2 | Chan (Hafez & Xie 2012) como evidência empírica de sentiment-as-factor em FX/equities | Chan p. 148 |
| L4 | Cap 3 §3.2 (Research Design) | Speculative Cycle + Risk Appetite Indicators motivam features regime-aware diferenciadas EUR vs JPY | Henderson pp. 52, 56 |
| L5 | Cap 3 §3.5 (Price Pipeline) | Single-venue ECN rule de Halls-Moore §3.3.3 justifica commit a uma corretora | Halls-Moore p. 19 |
| L6 | Cap 3 §3.5 | Rollover swap (eq. 5.6 de Chan) na fórmula de retorno overnight | Chan pp. 113-114 |
| L7 | Cap 3 §3.6 ou §3.7 | F17–F19 conforme tabela 3 acima | Laïdi + Saettele |
| L8 | Cap 3 §3.8 (Evaluation Protocol) | CPCV via `timeseriescv` de Jansen + Deflated Sharpe Bailey-Borwein-López | Jansen Cap. 6 + Cap. 8 |
| L9 | Cap 3 §3.9 (Execution Engine) | Padrão event-driven (MarketEvent → SignalEvent → OrderEvent → FillEvent) de Halls-Moore Cap. 14 | Halls-Moore pp. 129-141 |
| L10 | Cap 3 §3.10 (Threats to Validity) | Subseção "Data-mining bias and rule-level significance" com Aronson Cap. 6 + Monte Carlo Permutation Test (F20) | Aronson pp. 255-329 |
| L11 | Cap 3 §3.10 | Taxonomia de quatro viéses de Halls-Moore (Optimisation / Look-Ahead / Survivorship / Cognitive) como estrutura da seção | Halls-Moore pp. 16-17 |
| L12 | Cap 3 §3.10 | Cap formal sobre número de variantes triáveis via Bailey-Borwein-López (~60 estratégias em 10 anos) | Jansen Cap. 8 |
| L13 | Cap 4 (Experimental Evaluation) | Reportar Sharpe e Deflated Sharpe; aplicar MCP test (M = 1000) sobre cada configuração | Aronson + Jansen |

**Decisão explícita de NÃO importar (pós-LLM obsoleto):**

- Saettele Cap. 4 (headline keyword taxonomy "plummet/surge/plunge") — superado por FinBERT contextual scoring.
- Henderson Cap. 3 flow data (IMM CoT semanal, TIC mensal, Salomon Instability Index) — substituídos por GDELT 15-min + FinBERT no hot path; mencionar apenas como pedigree intelectual no Cap 2.
- Saettele lista de 73 manchetes empíricas — exemplar antiquado de keyword analysis; não citar como filtro.
- Henderson Cap. 4 charting básico — superado por Murphy 1999 + Bulkowski 2005, já citados.

---

## 6. Síntese — qual livro contribui mais para qual aspecto

| Aspecto da monografia | Livro principal | Por que |
|---|---|---|
| Threats to Validity (§3.10) | **Aronson 2007** | MCP test + Markowitz-Xu shrinkage + 5-factor bias decomposition; estatística atemporal |
| Protocolo de avaliação (§3.8) | **Jansen 2020** | CPCV via `timeseriescv` + Deflated Sharpe + minimum backtest length |
| Engine de execução (§3.9) | **Halls-Moore 2015** | Event-driven class hierarchy, single-venue ECN, taxonomia 4-bias |
| Features intermarket USD/JPY | **Laïdi 2009** | Carry-trade mechanism, VIX↔JPY, S&P↔JPY pós-2004, gold↔USD -0.84 |
| Canal de sentimento hard-data | **Saettele 2008** Cap. 5 | COT Composite + SSI + risk-reversals — ortogonal a FinBERT |
| Justificativa arquitetural de late fusion | **Henderson 2002** Cap. 10 | Signal Grid p. 204 — protótipo manual de 2002 da arquitetura |
| Features de padrões de candle | **Bulkowski 2005** | Rank methodology + estatísticas empíricas + tall-pattern + throwback effects |
| Custos FX + cointegração baseline | **Chan 2013** | Eq. 5.6 rollover + Exemplo 5.1 Johansen FX + VIX > 35 threshold |
| Definições macro (Taylor Rule, REER) | **Twomey 2012** | Citação pontual definicional, sem desenvolver |
| Sentiment-as-factor evidência | **Chan 2013** Cap. 6 | Hafez & Xie 2012 (RavenPack) — citar como pedigree, replicar com FinBERT |

**Recomendação operacional final.** Concentrar esforço de leitura nos quatro livros centrais — **Aronson, Jansen, Halls-Moore, Laïdi**. Os demais (Saettele, Bulkowski, Henderson, Chan, Twomey) entram com citações pontuais ou via filtros derivados; não justificam leitura cover-to-cover.
