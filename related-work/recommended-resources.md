# Recommended External Resources — Post-LLM Articles & Repositories

Curadoria de papers, repositórios e datasets públicos relevantes a este TCC (*Algorithmic Trading Enhanced by AI: Using News, Geopolitical Events and NLP-Based Sentiment in Forex Decision-Making*). Foco em material **pós-LLM** (2023–2026): trabalhos que pressupõem a existência de FinBERT-class scorers, GPT-4/Claude/Gemini-grade LLMs ou pipelines agênticos. Material pré-LLM (lexicon-only, keyword-matching) é deliberadamente excluído.

Cada item marcado com **(JÁ CITADO)** se já consta no `references.bib`; **(NOVO)** se vale considerar inclusão.

---

## 1. Closest prior art — papers diretos sobre o tema do TCC

### 1.1 Zhang (2025) — *Interpretable Machine Learning for Macro Alpha: A News Sentiment Case Study* **(JÁ CITADO)**

- arXiv: <https://arxiv.org/html/2505.16136v1>
- Sentiment indices diários sobre GDELT via FinBERT, XGBoost classifier, backtest EUR/USD, USD/JPY e UST10Y, 2017–2025.
- Sharpe reportados cost-adjusted: **5,87 EUR/USD, 4,65 USD/JPY, 4,65 Treasuries**.
- Closest prior art da monografia. Já citado no Cap 2 §2.5 e §3.1.

### 1.2 Kirtac & Germano (2024) — *Sentiment Trading with Large Language Models* **(✅ ADOTADO — Cap 5 §subsec:future-tier-a)**

- Venue: **Finance Research Letters, vol. 62, p. 105227 (2024)**
- arXiv preprint: <https://arxiv.org/abs/2412.19245>
- Compara BERT, OPT, FinBERT e Loughran-McDonald em **965.375 artigos** de notícias financeiras US, 2010-01 a 2023-06.
- Acurácias de previsão de retorno reportadas: **OPT 74,4%, BERT 72,5%, FinBERT 72,2%, Loughran-McDonald 50,1%**.
- Long-short portfolio Sharpe ratios: **OPT 3,05; BERT 2,11; FinBERT 2,07**.
- **Escopo: US equities apenas** — não testa Forex.
- **Por que vale citar:** evidência empírica direta de que LLMs frontier-grade superam FinBERT em sentiment financeiro (cf. Sharpe 3,05 vs 2,07). Sustenta a discussão de "Tier A — richer single-agent perception" do Cap 5 (Trabalhos Futuros) deste TCC. A diferença OPT→FinBERT é pedigree para considerar swap do scorer pós-defesa.

### 1.3 FinDPO (Iacovides, Zhou & Mandic, 2025) — *Financial Sentiment Analysis for Algorithmic Trading through Preference Optimization of LLMs* **(✅ ADOTADO — Cap 3 §subsec:rule-significance)**

- arXiv: <https://arxiv.org/abs/2507.18417>
- Primeiro framework finance-specific de LLM via Direct Preference Optimization (DPO).
- Reporta Sharpe **2,0** com custos de **5 bps** e retorno anual **67%**.
- **PDF completo conferido** (`related-work/papers/FinDPO - ...pdf`): backtest sobre **long-short portfolios de ações S&P 500**, não Forex. Logo é calibração-âncora, não comparável direto de FX.
- **Por que vale citar:** Sharpe 2,0 com custos explícitos é número defensável (versus os 5,87 do Zhang) — calibração realista para o que se pode esperar de qualquer estratégia LLM-based após custos.

### 1.4 Event-Aware Sentiment Factors from LLM-Augmented Financial Tweets (2025) **(NOVO — opcional)**

- arXiv: <https://arxiv.org/html/2508.07408v1>
- Sentiment factors derivados de tweets via LLM, transparente e interpretável.
- **Relevância secundária:** twitter data é fonte excluída neste TCC (cf. Cap 3 §3.5 e CLAUDE.md — Twitter/X após 2023 sem acesso público). Mencionar apenas no Cap 5 como direção possível se acesso for restaurado.

### 1.5 Integrating LLMs and Reinforcement Learning for Sentiment-Driven Quantitative Trading (2025) **(NOVO — Cap 5)**

- arXiv: <https://arxiv.org/html/2510.10526v1>
- Estende Zhou & Mehra (2025) usando RL para converter sinais LLM em alocação.
- **Relevância:** extensão Tier D do Cap 5 (agent-proposed rule modifications) — não escopo presente, mas direção natural.

### 1.6 Comparing LLMs for Sentiment Analysis in Financial Market News (2025) **(NOVO — opcional)**

- arXiv: <https://arxiv.org/pdf/2510.15929>
- Benchmark head-to-head de LLMs em sentimento financeiro.
- Útil como referência ao escolher scorer da camada de percepção; complementa Lopez-Lira & Tang.

---

## 2. Agentic LLM trading frameworks (referenciados em Cap 2 §2.5)

### 2.1 TradingAgents (Xiao et al., 2024-2025) **(JÁ CITADO)**

- arXiv: <https://arxiv.org/pdf/2412.20138>
- Página: <https://tradingagents-ai.github.io/>
- **Repositório:** <https://github.com/TauricResearch/TradingAgents>
- Framework multi-agente simulando trading firm (analistas, traders, risk managers).
- Já citado e contrastado na Tabela 2.1 do Cap 2.

### 2.2 QuantAgent (Xiong et al., 2025) **(JÁ CITADO)**

- arXiv: <https://arxiv.org/abs/2509.09995>
- Multi-agent HFT framework, decompõe em Indicator/Pattern/Trend/Risk agents.
- Já citado no Cap 2 §2.5.

### 2.3 ATLAS (Papadakis et al., 2025) **(JÁ CITADO)**

- Adaptive prompt-optimisation OPRO em LLM trading agent.
- Já citado no Cap 2 §2.5.

### 2.4 TradingGroup (Tian et al., 2025) **(JÁ CITADO)**

- Specialist agents + self-reflection + automated data synthesis.
- Já citado no Cap 2 §2.5.

---

## 3. Foundational financial LLMs & benchmarks

### 3.1 FinGPT (Yang et al., 2023) **(JÁ CITADO)**

- arXiv: <https://arxiv.org/html/2306.06031v2>
- Site: <https://fingpt.io/>
- **Repositório:** <https://github.com/AI4Finance-Foundation/FinGPT>
- Open-source financial LLM pipeline; código + datasets + fine-tuning recipes.

### 3.2 BloombergGPT (Wu et al., 2023) **(JÁ CITADO)**

- 50B-parameter decoder, treinado em corpus Bloomberg + público.
- Proprietary; FinGPT é o open-source equivalent.

### 3.3 FinLLMs benchmark repository **(NOVO — referência de comparação)**

- **Repositório:** <https://github.com/adlnlp/finllms>
- Benchmarks e datasets para LLMs financeiros.
- Útil se eventual fine-tune/avaliação custom for adicionada em Cap 5.

### 3.4 Golden Touchstone (Wu et al., 2024) **(NOVO — opcional)**

- Bilingual benchmark spanning 8 financial NLP tasks.
- FinGPT reporta F1 87,62% sentiment / 95,50% headline classification (comparable a GPT-4).
- Stock movement prediction acurácia 45–53% — número defensável para baseline.

### 3.5 FinBERT (Araci 2019; Yang 2020) **(JÁ CITADO)**

- Scorer base do pipeline. Repositórios públicos no HuggingFace:
  - <https://huggingface.co/ProsusAI/finbert> (Araci)
  - <https://huggingface.co/yiyanghkust/finbert-tone> (Yang)

---

## 4. Geopolitical risk & event data

### 4.1 Caldara-Iacoviello Geopolitical Risk (GPR) Index **(JÁ CITADO)**

- Paper: <https://www.federalreserve.gov/econres/ifdp/files/ifdp1222.pdf>
- Site: <https://www.matteoiacoviello.com/gpr.htm>
- Dados: <https://www.policyuncertainty.com/gpr.html>
- Country-specific GPR (incluindo US, EU, JP): <https://www.matteoiacoviello.com/gpr_country.htm>
- Headline GPR + decomposição em GPT (threats) e GPA (acts).

### 4.2 GPR & Currency Returns (Liu & Zhang, 2024) **(✅ ADOTADO — Cap 2 §sec:geopolitical)**

- Venue: **Journal of Banking & Finance, vol. 161, paper 107097 (2024)**
- ScienceDirect: <https://www.sciencedirect.com/science/article/abs/pii/S0378426624000177>
- **PDF completo conferido:** `related-work/papers/Geopolitical risk and currency returns.pdf` (20 páginas; autores Xi Liu, Tsinghua + Xueyong Zhang, Central University of Finance and Economics).
- Sample: **42 moedas em 5 portfolios, sorted por índice GPR mensal, jun 2002 – dez 2019**; dados mensais (end-of-month).
- Zero-cost strategy comprando moedas de alto GPR e vendendo de baixo GPR: **excess return 5,72% a.a. antes de custos, 4,73% após custos bid-ask** (ambos confirmados no texto completo).
- **Decomposição em risco idiosincrático país-específico vs. risco regional**; GPR factor precificado positivamente em cross-sections amplos de portfolios de moedas e em moedas individuais.
- **Por que vale citar:** evidência empírica direta de que GPR carrega informação cross-sectional em FX, sustentando a inclusão do feature GPR no pipeline da monografia. Pode entrar no Cap 2 §2.4 (Geopolitical Events) como pedigree empírico.

### 4.3 GPR in Currency Markets (Melone & Stathopoulos, 2026) **(✅ ADOTADO — Cap 2 §sec:geopolitical)**

- Venue: **Charles A. Dice Center / Fisher College of Business Working Paper No. 2026-03-003** — date written 27 Feb 2026, posted SSRN 19 Mar 2026; working paper, ainda não peer-reviewed.
- SSRN: <https://ssrn.com/abstract=6438919> — DOI 10.2139/ssrn.6438919
- **PDF local conferido:** `related-work/papers/Geopolitical Risk in Currency Markets.pdf` (80 páginas).
- Ordena moedas por **exposição** (rolling forecast coefficient) dos retornos esperados ao índice global de ameaças geopolíticas (GPT) de Caldara-Iacoviello — não pelo nível de GPR.
- Estratégia dollar-neutral high-minus-low-exposure (GHML): **retorno anualizado 3,28%, alpha anualizado 2,76%** após controlar pelos fatores DOL e CAR de Lustig-Roussanov-Verdelhan (2011). Fator GHML precificado no cross-section.
- Moedas safe-haven têm loading GHML negativo (hedge); moedas geopoliticamente arriscadas, positivo. Loadings **não relacionados** a medidas de policy uncertainty.
- **Por que vale citar:** evidência complementar a Liu & Zhang 2024 por construção distinta (exposure sort vs level sort). Citado em Cap 2 §sec:geopolitical lado a lado com Liu & Zhang.

### 4.4 GPR & Inflation (Caldara, Conlisk et al., 2024) **(NOVO — secundário)**

- Paper: <https://www.matteoiacoviello.com/research_files/GPR_INFLATION_PAPER.pdf>
- Mecanismo GPR → inflação → política monetária → câmbio. Útil para o argumento conceitual.

### 4.5 GDELT Project **(JÁ CITADO)**

- Site: <https://www.gdeltproject.org/>
- Real-time event monitoring, 100+ idiomas. Já é a fonte primária de eventos deste TCC.

### 4.6 IMF GFSR 2025 — Geopolitical risk & financial stability **(NOVO — opcional)**

- IMF Global Financial Stability Report, April/October 2025: <https://www.imf.org/en/publications/gfsr/issues/2025/10/14/global-financial-stability-report-october-2025>
- Chapter 2 (April 2025): geopolitical risks → asset prices → financial stability.
- Documento oficial recente; útil como respaldo da relevância prática da hipótese H1.

---

## 5. Validation & overfitting — methodological rigor

### 5.1 López de Prado (2018) — *Advances in Financial Machine Learning* **(JÁ CITADO)**

- Livro canônico. CPCV + purging + embargo.

### 5.2 Bailey, Borwein, López de Prado, Zhu (2017) — *The Probability of Backtest Overfitting* **(JÁ CITADO)**

- Deflated Sharpe Ratio + minimum backtest length. Já incorporado em §3.10 da monografia.

### 5.3 Implementação CPCV em Python **(NOVO — referência prática)**

- `timeseriescv`: <https://pypi.org/project/timeseriescv/> (já mencionado via Jansen)
- Wikipedia overview: <https://en.wikipedia.org/wiki/Purged_cross-validation>
- Tutorial QuantInsti: <https://blog.quantinsti.com/cross-validation-embargo-purging-combinatorial/>
- Tutorial com código: <https://www.quantbeckman.com/p/with-code-combinatorial-purged-cross>

### 5.4 *Backtest Overfitting in the ML Era* (2024) **(NOVO — secundário)**

- ScienceDirect: <https://www.sciencedirect.com/science/article/abs/pii/S0950705124011110>
- Comparação de métodos de teste out-of-sample em ambiente sintético controlado. Útil como pedigree adicional ao MCP test de Aronson em §3.10.

### 5.5 *The 10 Reasons Most Machine Learning Funds Fail* (López de Prado 2018) **(✅ ADOTADO — Cap 3 §subsec:rule-significance)**

- Venue: **The Journal of Portfolio Management, Vol. 44, No. 6, pp. 120-133 (2018)** — DOI 10.3905/jpm.2018.44.6.120
- GARP whitepaper version: <https://www.garp.org/white-paper/the-10-reasons-most-machine-learning-funds-fail>
- SSRN: <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3104816>
- **PDF local conferido:** `related-work/papers/The 10 Reasons Most Machine Learning Funds Fail.pdf` (Author metadata: Lopez de Prado, Marcos; First version Dec 25 2017; revised Jan 27 2018).
- **10 pitfalls verbatim (extraídos do PDF):**
  1. THE SISYPHUS PARADIGM
  2. RESEARCH THROUGH BACKTESTING
  3. CHRONOLOGICAL SAMPLING
  4. INTEGER DIFFERENTIATION
  5. FIXED-TIME HORIZON LABELING
  6. LEARNING SIDE AND SIZE SIMULTANEOUSLY
  7. WEIGHTING OF NON-IID SAMPLES
  8. CROSS-VALIDATION LEAKAGE
  9. WALK-FORWARD (OR HISTORICAL) BACKTESTING
  10. BACKTEST OVERFITTING
- Citado na §3.10 mapeando 6 dos 10 pitfalls (#2, #3, #7, #8, #9, #10) contra os mecanismos defensivos do TCC.
- Pitfalls #1 (Sisyphus), #4 (integer differentiation), #5 (fixed-time labeling) e #6 (learning side and size) não são endereçados pelo escopo atual; podem entrar como Trabalhos Futuros se relevantes.

---

## 6. Backtest infrastructure

### 6.1 LEAN — QuantConnect open-source engine **(JÁ ADOTADO)**

- **Repositório:** <https://github.com/QuantConnect/Lean>
- Site: <https://www.quantconnect.com/>
- Docs: <https://www.quantconnect.com/docs/v2/lean-engine/getting-started>
- Apache 2.0 licença. C# core, Python algorithm interface. Suporta Forex, Equities, Options, Futures, Crypto.
- 180+ engenheiros, 300+ fundos em produção.
- Adapter OANDA oficial: <https://github.com/QuantConnect/Lean.Brokerages.Oanda>

### 6.2 NautilusTrader **(JÁ MENCIONADO — Cap 5 future-work)**

- <https://github.com/nautechsystems/nautilus_trader>
- Actor-based, Python/Rust. LGPL v3.

### 6.3 Backtrader / Vectorbt / Zipline **(MENCIONADOS no Cap 3 §3.9)**

- Backtrader: GPL v3 (rejeitado por copyleft conflitar com plano comercial).
- Vectorbt: pesquisa apenas, sem live execution.
- Zipline: descontinuado pela Quantopian; mantido por comunidades.

---

## 7. Data sources

### 7.1 Dukascopy Historical Data **(JÁ ADOTADO)**

- <https://www.dukascopy.com/swiss/english/marketwatch/historical/>
- Tick-level free para majors desde 2003. Demo account credentials.

### 7.2 FNSPID Dataset **(JÁ MENCIONADO)**

- Financial News and Stock Price Integration Dataset.
- <https://github.com/Zdong104/FNSPID_Financial_News_Dataset>

### 7.3 CC-News **(JÁ MENCIONADO)**

- Common Crawl News, parte do projeto Common Crawl.
- <https://commoncrawl.org/blog/news-dataset-available>

### 7.4 Reddit Pushshift archives **(JÁ MENCIONADO)**

- Arquivos históricos disponíveis via Academic Torrents:
  - <https://academictorrents.com/details/9c263fc85366c1ef8f5bb9da0203f4c8c8db75f4>
- Acesso à API ao vivo descontinuado em 2023; arquivos pré-2023 ainda recuperáveis.

---

## 8. Other recent surveys (Cap 2 §2.5 enrichment)

### 8.1 *LLMs in Equity Markets: Applications, Techniques, and Insights* (2025) **(NOVO — survey)**

- PubMed/PMC: <https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12421730/>
- Survey acadêmica recente cobrindo LLM em mercados de equity. Útil como referência ao posicionar o presente TCC como extensão FX-específica de tendência maior.

### 8.2 *Evaluation and Benchmarking Suite for Financial LLMs and Agents* (2026) **(NOVO — opcional)**

- arXiv: <https://arxiv.org/html/2602.19073v1>
- FinLLM Leaderboard + AgentOps framework. Relevante para Cap 5 caso pipeline agêntico se torne foco.

---

## 9. Priority recommendations — status final

Triagem por valor real e status de adoção na monografia (verificado contra `build/tcc.pdf`, 77 páginas, em 2026-05-23):

| Recomendação | Onde inserido | Status |
|---|---|---|
| **Kirtac & Germano 2024** (LLM sentiment 965k US-equity articles, OPT Sharpe 3,05 > FinBERT 2,07) | Cap 5 §subsec:future-tier-a | **✅ ADOTADO** |
| **FinDPO (Iacovides, Zhou & Mandic) 2025** (Sharpe 2,0 com custos de 5bps) | Cap 3 §subsec:rule-significance | **✅ ADOTADO** |
| **Liu & Zhang 2024** (GPR currency zero-cost strategy 5,72% a.a. antes custos) | Cap 2 §sec:geopolitical | **✅ ADOTADO** |
| IMF GFSR April/October 2025 (geopolitical risk & financial stability) | — | Skip — opcional, leitura de referência |
| Comparing LLMs sentiment (2025) | — | Skip — Kirtac & Germano cobre |
| LLMs + RL trading (2025) | — | Skip — Tier D não desenvolvido no escopo |
| Event-aware tweets (2025) | — | Skip — Twitter excluído deste TCC |
| FinLLM benchmark suites | — | Skip — não faz benchmark próprio |
| Backtest overfitting ML era (2024) | — | Skip — Aronson + Bailey-Borwein-López já cobrem §3.10 |

**Resumo:** 3 entradas BibTeX adicionadas + 3 inserções prose verificadas contra os respectivos abstracts. Reverificação contra PDFs completos recomendada para qualquer número adicional além do já citado.

---

## 10. BibTeX prontos para inclusão (caso o usuário decida adicionar)

```bibtex
@article{kirtac2024sentiment,
  author    = {Kirtac, Kemal and Germano, Guido},
  title     = {Sentiment Trading with Large Language Models},
  journal   = {Finance Research Letters},
  volume    = {62},
  pages     = {105227},
  year      = {2024},
  doi       = {10.1016/j.frl.2024.105227}
}

@article{iacovides2025findpo,
  author    = {Iacovides, Giorgos and Zhou, Wuyang and Mandic, Danilo},
  title     = {{FinDPO}: Financial Sentiment Analysis for Algorithmic Trading through Preference Optimization of {LLMs}},
  journal   = {arXiv preprint arXiv:2507.18417},
  year      = {2025},
  url       = {https://arxiv.org/abs/2507.18417}
}

@article{liu2024gprcurrency,
  author    = {Liu, Xi and Zhang, Xueyong},
  title     = {Geopolitical Risk and Currency Returns},
  journal   = {Journal of Banking \& Finance},
  volume    = {161},
  pages     = {107097},
  year      = {2024},
  doi       = {10.1016/j.jbankfin.2024.107097}
}
```

Conferido em 2026-05-23 contra os abstracts oficiais — autoria, venue e números do abstract verificados. Para citações que exigirem detalhes além do abstract (e.g. período, sample, custos completos), conferir o PDF completo do paper antes do commit final.

---

*Documento gerado a partir de busca web em 2026-05-23. Material datado pode requerer reverificação antes de citação no corpo da monografia.*
