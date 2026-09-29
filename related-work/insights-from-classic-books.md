# Insights de Livros Clássicos — Relevância pós-LLM

> Análise de livros clássicos de trading, filtrada para relevância no contexto pós-transformers (2023+). Apenas conceitos que envelheceram bem ou fundamentam métodos modernos. Data: 2026-05-22.

---

## 1. Evidence-Based Technical Analysis (Aronson, 2007)

### ✅ Relevância: ESSENCIAL

Este livro é **obrigatório** para qualquer trabalho sério de ML em finanças. Não trata de "estratégias" ou "setups", mas de **metodologia científica** para validar sistemas de trading.

#### Data Mining Bias — O Problema Central

> "The historical performance of rules discovered by data mining are upwardly biased."

Aronson demonstrou isso testando 6,400 regras binárias no S&P 500. Quando você testa muitas hipóteses, algumas vão parecer boas por acaso (múltiplas comparações).

**Relevância para o TCC:**
- Justifica o uso de **CPCV** (combinatorial purged cross-validation)
- Justifica **thresholds calibrados por ROC/Youden** em vez de otimizados
- Base para Seção 3.10 (Threats to Validity)

#### Monte Carlo Permutation Test (Masters/Aronson)

Alternativa não-patenteada ao Reality-Check de White (2000):

```
Procedimento:
1. Embaralhar aleatoriamente os retornos (permutação)
2. Aplicar a regra nos dados embaralhados
3. Calcular estatística de performance
4. Repetir N vezes (1,000-10,000)
5. Comparar performance observada vs. distribuição nula
```

**Aplicação:** Pode ser usado para validar a significância estatística dos filtros F8-F14.

#### Train/Test/Validation Split

Aronson enfatiza **três segmentos** quando há otimização de complexidade:
- **Training**: Ajuste dos parâmetros
- **Testing**: Seleção da complexidade (evitar overfitting)
- **Validation**: Estimativa final não-viesada (usado apenas uma vez)

**Nota:** Este é o único livro "clássico" que envelheceu perfeitamente bem — métodos científicos não envelhecem.

---

## 2. Psicologia de Mercado (Conceitos Atemporais)

### ✅ Relevância: PARCIAL

#### Lefèvre (1923) — Reminiscences of a Stock Operator

Citações do trader Jesse Livermore aplicáveis a sistemas algorítmicos:

> "It never was my thinking that made the big money for me. It always was my sitting."

**Insight:** Justifica filtros de "paciência" (F9: Regime Viability) — não operar quando não há edge claro. O valor está em permanecer posicionado quando há edge estatístico, não em operar frequentemente.

**Nota:** Embora seja um livro de narrativa sobre Livermore, a sabedoria contida é atemporal e aplicável a sistemas quantitativos. A ideia de que "sentar" (não operar) é uma habilidade válida justifica filtros de regime que vetam trades em condições desfavoráveis.

---

## 3. O Que FOI REMOVIDO desta Análise

### ❌ Saettele (2008) — Sentiment in the Forex Market

**Motivo da remoção:** A análise de sentimento por keyword matching ("surge", "plunge") foi completamente obsoleta por transformers.

| Aspecto | Saettele (2008) | Estado |
|---------|-----------------|--------|
| NLP | Busca por keywords | ❌ Obsoleto |
| COT Reports | Análise manual semanal | ❌ Muito lento para intraday |
| Intuição contrarian | "Extremos de sentimento → reversão" | ⚠️ Válido, mas implementação superada |

**Decisão:** Não citar. A intuição contrarian já está melhor fundamentada em literatura moderna de behavioral finance (Shiller, Thaler).

### ❌ Nison (1991/2001) — Candlestick Charting

**Motivo da remoção:** A descrição de padrões (hammer, engulfing) é subjetiva e foi substituída por:
- **TA-Lib**: Detecção objetiva de padrões
- **ML**: Aprendizado de padrões não supervisionado

**Decisão:** Não citar como referência teórica. TA-Lib é a referência técnica; Bulkowski (2005) é preferível para estatísticas de padrões.

### ❌ Fitschen (2013) — Building Reliable Trading Systems

**Motivo da remoção:** Embora a arquitetura modular de filtros seja válida, os exemplos específicos ("não entre long na sexta") são regras heurísticas que não generalizam.

**Decisão:** Não citar. A arquitetura de filtros do TCC é inspirada em abordagens modernas de ML systems, não neste livro.

### ❌ Mackay (1841) — Extraordinary Popular Delusions

**Motivo da remoção:** Interesse histórico, mas não adiciona rigor metodológico ao TCC.

---

## 📊 Resumo: O Que Citar no TCC

| Referência | Uso no TCC | Seção |
|------------|------------|-------|
| **Aronson (2007)** | Fundamentação metodológica; data mining bias; validação estatística | Cap 3 §10 (Threats) |
| **Lefèvre (1923)** | Contexto psicológico/histórico sobre "sitting" | Cap 2 (Fundamentação comportamental) |
| **White (2000)** | Reality-Check (contexto) | Nota de rodapé ou Related Work |

---

## 🎯 Justificativa das Remoções

### Critério de Inclusão pós-LLM

Para ser citado, uma referência deve atender a **pelo menos um** dos critérios:

1. **Métodos estatísticos** que não dependem de tecnologia específica (Aronson)
2. **Comportamento humano** que não mudou significativamente (Douglas — opcional)
3. **Dados empíricos** que não foram superados (ex: estatísticas de padrões de Bulkowski)

### O Que Não Passou

- **Keyword-based sentiment analysis**: Substituído por transformers
- **Regras heurísticas fixas**: Substituídas por ML adaptativo
- **Análise visual de padrões**: Substituída por detecção objetiva

---

## Referências Bibliográficas Mantidas

```bibtex
@Book{aronson2007evidence,
  author    = {Aronson, David R.},
  title     = {Evidence-Based Technical Analysis: Applying the Scientific 
               Method and Statistical Inference to Trading Signals},
  publisher = {John Wiley \& Sons},
  year      = {2007},
  address   = {Hoboken, NJ},
  isbn      = {9780470088746}
}

@Book{lefevre1923reminiscences,
  author    = {Lefèvre, Edwin},
  title     = {Reminiscences of a Stock Operator},
  publisher = {George H. Doran Company},
  year      = {1923},
  address   = {New York},
  note      = {Reprinted by Wiley, 1994}
}

@Article{white2000reality,
  author    = {White, Halbert},
  title     = {A Reality Check for Data Snooping},
  journal   = {Econometrica},
  year      = {2000},
  volume    = {68},
  number    = {5},
  pages     = {1097--1126},
  doi       = {10.1111/1468-0262.00158}
}
```

---

*Nota: Este relatório foi filtrado para manter apenas referências que permanecem relevantes no paradigma pós-LLM. Livros com técnicas obsoletas (keyword matching, regras heurísticas fixas) foram removidos.*
