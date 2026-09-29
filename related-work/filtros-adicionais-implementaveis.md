# Filtros Adicionais Implementáveis para a Cadeia

> Especificação técnica de filtros extras que podem ser adicionados à cadeia F1-F7 existente para criar variações de estratégia (ablations ou future work).

---

## F8 — Candlestick Confirmation Gate

**Inspiração:** Claudinei Felix (2024)  
**Tipo:** Gate de execução (AND-clause)  
**Complexidade:** Baixa  
**Dependências:** TA-Lib (já usado no F3)

### Descrição
Antes de permitir uma entrada baseada no sinal NLP ou no meta-learner, verificar se há um padrão candlestick de reversão ou continuação reconhecido nos últimos $k$ candles. Se não houver padrão técnico confirmando a direção, o trade é vetado ou o sinal é marcado como fraco.

### Padrões Implementáveis (TA-Lib)
```python
# Padrões de reversão
CDL_HAMMER          # Martelo (reversão de baixa)
CDL_SHOOTINGSTAR    # Estrela cadente (reversão de alta)
CDL_ENGULFING       # Engolfo (alta ou baixa)
CDL_MORNINGSTAR     # Estrela da manhã (reversão de baixa)
CDL_EVENINGSTAR     # Estrela da noite (reversão de alta)
CDL_DOJI            # Doji (indecisão/possível reversão)

# Padrões de continuação
CDL_HARAMI          # Harami (continuação ou reversão fraca)
CDL_MARUBOZU        # Marubozu (forte continuação)
```

### Implementação
```python
@dataclass
class CandlestickFilterResult(FilterResult):
    pattern_detected: str | None
    pattern_direction: Literal['BULLISH', 'BEARISH', 'NEUTRAL']
    confirmation_score: float  # 0.0 a 1.0

class CandlestickConfirmationFilter(Filter):
    """F8 — Confirmação por padrão candlestick"""
    
    PATTERNS_BULLISH = [
        ('CDL_HAMMER', 1.0),
        ('CDL_MORNINGSTAR', 1.0),
        ('CDL_ENGULFING_BULL', 0.9),
        ('CDL_MARUBOZU_WHITE', 0.8),
    ]
    
    PATTERNS_BEARISH = [
        ('CDL_SHOOTINGSTAR', 1.0),
        ('CDL_EVENINGSTAR', 1.0),
        ('CDL_ENGULFING_BEAR', 0.9),
        ('CDL_MARUBOZU_BLACK', 0.8),
    ]
    
    def __init__(self, lookback: int = 3, min_confirmation: float = 0.7):
        self.lookback = lookback
        self.min_confirmation = min_confirmation
    
    def apply(self, state: ExecutionState) -> FilterResult:
        # Pega candles dos últimos N minutos
        recent_candles = self._get_recent_candles(state.pair, self.lookback)
        
        # Detecta padrões
        patterns = self._detect_patterns(recent_candles)
        
        if not patterns:
            return FilterResult(
                filter_name="F8_CandlestickConfirmation",
                recommendation=Recommendation.ABSTAIN,
                reason=f"Nenhum padrão claro nos últimos {self.lookback} candles",
                confidence=0.0
            )
        
        # Verifica alinhamento com direção proposta
        strongest = max(patterns, key=lambda p: p['strength'])
        alignment = self._check_alignment(strongest, state)
        
        if alignment['score'] >= self.min_confirmation:
            return FilterResult(
                filter_name="F8_CandlestickConfirmation",
                recommendation=Recommendation.PASS,
                reason=f"Padrão {strongest['name']} ({strongest['direction']}) "
                       f"alinhado com sinal (score: {alignment['score']:.2f})",
                confidence=alignment['score'],
                enrichment={'pattern': strongest['name'], 
                           'pattern_strength': strongest['strength']}
            )
        else:
            return FilterResult(
                filter_name="F8_CandlestickConfirmation",
                recommendation=Recommendation.VETO,
                reason=f"Padrão {strongest['name']} contradiz direção do sinal "
                       f"(score: {alignment['score']:.2f} < {self.min_confirmation})",
                confidence=alignment['score'],
                veto=True
            )
```

### Variações de Estratégia
| Variação | Configuração | Uso |
|----------|--------------|-----|
| F8-Strict | `min_confirmation=0.9`, `lookback=1` | Só entra com padrão muito forte |
| F8-Lenient | `min_confirmation=0.5`, `lookback=5` | Permite padrões mais antigos/fracos |
| F8-ReversalOnly | Só padrões de reversão | Foca em pontos de inflexão |
| F8-ContinuationOnly | Só padrões de continuação | Foca em tendências estabelecidas |

---

## F9 — Regime Viability / Tradability Filter

**Inspiração:** Hô Don Lee (2014) — conceito de "tradability"  
**Tipo:** Gate de execução (AND-clause)  
**Complexidade:** Média  
**Dependências:** Statsmodels (ADF test), numpy

### Descrição
Só permite operação quando o mercado está em um regime "viável" para o tipo de sinal emitido. Inspirado no conceito de tradability de Lee: antes de operar um par, verificar se a série residual preserva propriedades estatísticas mínimas.

### Critérios de Viabilidade
```python
VIABILITY_CRITERIA = {
    'volatility_within_bounds': {
        'description': 'ATR atual dentro de bandas históricas',
        'calculation': 'current_atr < mean_atr + k * std_atr',
        'params': {'window': 60, 'k': 2.0}
    },
    'stationarity_test': {
        'description': 'Série de retornos é estacionária (ADF test)',
        'calculation': 'ADF p-value < 0.05',
        'params': {'window': 100, 'max_pvalue': 0.05}
    },
    'mean_drift_bounded': {
        'description': 'Drift da média móvel controlado',
        'calculation': '|sma_current - sma_lag| / atr < threshold',
        'params': {'sma_fast': 20, 'sma_slow': 50, 'threshold': 0.5}
    },
    'sentiment_stability': {
        'description': 'Sinal textual não oscila excessivamente',
        'calculation': 'std(sentiment_10min) < threshold',
        'params': {'window': 10, 'max_std': 0.3}
    }
}
```

### Implementação
```python
class RegimeViabilityFilter(Filter):
    """F9 — Gate de viabilidade de regime (tradability)"""
    
    def __init__(self, 
                 volatility_window: int = 60,
                 volatility_k: float = 2.0,
                 adf_window: int = 100,
                 adf_max_pvalue: float = 0.05,
                 drift_threshold: float = 0.5,
                 sentiment_stability_window: int = 10,
                 sentiment_max_std: float = 0.3):
        self.params = locals()
    
    def apply(self, state: ExecutionState) -> FilterResult:
        checks = []
        
        # Check 1: Volatilidade dentro de bounds
        atr_current = state.features.get('atr_14')
        atr_history = self._get_historical_atr(state.pair, self.params['volatility_window'])
        atr_mean = np.mean(atr_history)
        atr_std = np.std(atr_history)
        
        vol_ok = atr_current < (atr_mean + self.params['volatility_k'] * atr_std)
        checks.append(('volatility', vol_ok, f"ATR: {atr_current:.4f} vs limite {atr_mean + self.params['volatility_k'] * atr_std:.4f}"))
        
        # Check 2: Estacionariedade (ADF test)
        returns = self._get_recent_returns(state.pair, self.params['adf_window'])
        adf_stat, pvalue = adfuller(returns)[:2]
        stationarity_ok = pvalue < self.params['adf_max_pvalue']
        checks.append(('stationarity', stationarity_ok, f"ADF p-value: {pvalue:.4f}"))
        
        # Check 3: Mean drift
        sma_fast = state.features.get(f'sma_{self.params["sma_fast"]}')
        sma_slow = state.features.get(f'sma_{self.params["sma_slow"]}')
        drift = abs(sma_fast - sma_slow) / atr_current if atr_current > 0 else float('inf')
        drift_ok = drift < self.params['drift_threshold']
        checks.append(('mean_drift', drift_ok, f"Drift: {drift:.2f}"))
        
        # Check 4: Sentiment stability (se houver sinal textual)
        if 'sentiment_score' in state.features:
            sentiment_history = self._get_recent_sentiment(state.pair, self.params['sentiment_stability_window'])
            sentiment_std = np.std(sentiment_history)
            sentiment_ok = sentiment_std < self.params['sentiment_max_std']
            checks.append(('sentiment_stability', sentiment_ok, f"Sentiment std: {sentiment_std:.3f}"))
        
        # Decide
        all_ok = all(c[1] for c in checks)
        
        if all_ok:
            return FilterResult(
                filter_name="F9_RegimeViability",
                recommendation=Recommendation.PASS,
                reason=f"Regime viável: {len(checks)}/{len(checks)} checks OK",
                confidence=1.0,
                enrichment={'viability_checks': {c[0]: c[2] for c in checks}}
            )
        else:
            failed = [c[0] for c in checks if not c[1]]
            return FilterResult(
                filter_name="F9_RegimeViability",
                recommendation=Recommendation.VETO,
                reason=f"Regime inviável: falhou em {', '.join(failed)}",
                confidence=0.0,
                veto=True,
                enrichment={'failed_checks': failed, 'all_checks': {c[0]: c[2] for c in checks}}
            )
```

### Variações de Estratégia
| Variação | Critérios Ativos | Uso |
|----------|------------------|-----|
| F9-VolOnly | Só volatilidade | Foco em controle de risco |
| F9-Strict | Todos os critérios | Máxima seleção de regime |
| F9-NewsSensitive | + sentiment stability | Para estratégias news-driven |

---

## F10 — Textual Confidence Gate

**Inspiração:** José Eduardo Ferrarini (2025) + Codex  
**Tipo:** Gate de percepção (pré-fusão)  
**Complexidade:** Baixa  
**Dependências:** Probabilidades do FinBERT (já disponíveis)

### Descrição
Só permite que o sinal textual influencie a decisão quando a confiança da inferência exceder um limiar mínimo. Usa a margem entre classes ou entropia da distribuição softmax do FinBERT.

### Implementação
```python
class TextualConfidenceFilter(Filter):
    """F10 — Gate de confiança do sinal textual"""
    
    CONFIDENCE_METHODS = {
        'margin': 'Diferença entre top-2 probabilidades',
        'entropy': 'Entropia da distribuição (menor = mais confiante)',
        'max_prob': 'Probabilidade da classe vencedora',
        'disagreement': 'Concordância entre FinBERT e L-M'
    }
    
    def __init__(self, 
                 method: str = 'margin',
                 min_margin: float = 0.3,
                 max_entropy: float = 0.8,
                 min_max_prob: float = 0.6):
        self.method = method
        self.thresholds = {
            'margin': min_margin,
            'entropy': max_entropy,
            'max_prob': min_max_prob
        }
    
    def apply(self, state: ExecutionState) -> FilterResult:
        # Pega probabilidades do FinBERT (devem estar no estado)
        probs = state.features.get('finbert_probs')  # [neg, neu, pos]
        
        if probs is None:
            return FilterResult(
                filter_name="F10_TextualConfidence",
                recommendation=Recommendation.ABSTAIN,
                reason="Sem probabilidades do FinBERT disponíveis",
                confidence=None
            )
        
        # Calcula confiança
        if self.method == 'margin':
            sorted_probs = sorted(probs, reverse=True)
            confidence = sorted_probs[0] - sorted_probs[1]
            passed = confidence >= self.thresholds['margin']
            
        elif self.method == 'entropy':
            from scipy.stats import entropy
            confidence = -entropy(probs)  # Negativo para maior = melhor
            passed = confidence <= self.thresholds['entropy']
            
        elif self.method == 'max_prob':
            confidence = max(probs)
            passed = confidence >= self.thresholds['min_max_prob']
        
        if passed:
            return FilterResult(
                filter_name="F10_TextualConfidence",
                recommendation=Recommendation.PASS,
                reason=f"Confiança {self.method}={confidence:.3f} >= limiar",
                confidence=confidence,
                enrichment={'confidence_method': self.method, 'confidence_score': confidence}
            )
        else:
            # Em vez de veto, pode reduzir peso ou marcar como neutro
            return FilterResult(
                filter_name="F10_TextualConfidence",
                recommendation=Recommendation.ABSTAIN,
                reason=f"Confiança insuficiente ({self.method}={confidence:.3f}), "
                       "sinal textual será ignorado",
                confidence=confidence,
                enrichment={'confidence_method': self.method, 'confidence_score': confidence,
                           'action': 'ignore_text_signal'}
            )
```

### Variações
| Variação | Método | Threshold | Comportamento |
|----------|--------|-----------|---------------|
| F10-Strict | margin | 0.5 | Só usa texto se muito confiante |
| F10-Lenient | max_prob | 0.55 | Permite textos marginalmente confiantes |
| F10-Entropy | entropy | 0.6 | Prefere distribuições "pontiagudas" |

---

## F11 — Cross-Model Disagreement Gate

**Inspiração:** Codex (Ferrarini)  
**Tipo:** Gate de percepção  
**Complexidade:** Baixa  
**Dependências:** FinBERT + Loughran-McDonald (já têm ambos)

### Descrição
Quando FinBERT e Loughran-McDonald divergem fortemente em sinal (um diz positivo, outro negativo) E ambos têm magnitude alta, marca o sinal como incerto ou veta. Se divergem mas um é fraco, segue o forte.

### Implementação
```python
class DisagreementFilter(Filter):
    """F11 — Gate de discordância entre scorers"""
    
    def __init__(self, 
                 divergence_threshold: float = 0.5,
                 min_magnitude: float = 0.3,
                 on_divergence: Literal['veto', 'reduce_weight', 'ignore'] = 'veto'):
        self.divergence_threshold = divergence_threshold
        self.min_magnitude = min_magnitude
        self.on_divergence = on_divergence
    
    def apply(self, state: ExecutionState) -> FilterResult:
        finbert_score = state.features.get('finbert_sentiment')
        lm_score = state.features.get('loughran_mcdonald_sentiment')
        
        if finbert_score is None or lm_score is None:
            return FilterResult(
                filter_name="F11_Disagreement",
                recommendation=Recommendation.PASS,
                reason="Um dos scorers indisponível, não há divergência para avaliar"
            )
        
        # Calcula divergência
        sign_fb = np.sign(finbert_score)
        sign_lm = np.sign(lm_score)
        
        # Se concordam em sinal, passa
        if sign_fb == sign_lm:
            return FilterResult(
                filter_name="F11_Disagreement",
                recommendation=Recommendation.PASS,
                reason=f"Scorers concordam ({sign_fb:+.2f} vs {sign_lm:+.2f})",
                confidence=1.0,
                enrichment={'agreement': True}
            )
        
        # Divergência detectada - verifica magnitude
        mag_fb = abs(finbert_score)
        mag_lm = abs(lm_score)
        
        strong_divergence = (mag_fb > self.min_magnitude and 
                            mag_lm > self.min_magnitude)
        
        if strong_divergence:
            if self.on_divergence == 'veto':
                return FilterResult(
                    filter_name="F11_Disagreement",
                    recommendation=Recommendation.VETO,
                    reason=f"Divergência forte: FB={finbert_score:+.2f} vs LM={lm_score:+.2f}",
                    confidence=0.0,
                    veto=True,
                    enrichment={'divergence': True, 'strong': True,
                               'disagreement_feature': abs(finbert_score - lm_score)}
                )
            elif self.on_divergence == 'reduce_weight':
                return FilterResult(
                    filter_name="F11_Disagreement",
                    recommendation=Recommendation.PASS,
                    reason=f"Divergência forte, peso reduzido",
                    confidence=0.5,  # Reduz confiança
                    enrichment={'divergence': True, 'weight_reduction': 0.5}
                )
        else:
            # Divergência fraca - segue o scorer mais forte
            dominant = 'FB' if mag_fb > mag_lm else 'LM'
            return FilterResult(
                filter_name="F11_Disagreement",
                recommendation=Recommendation.PASS,
                reason=f"Divergência fraca, segue {dominant}",
                confidence=max(mag_fb, mag_lm),
                enrichment={'divergence': True, 'strong': False, 'dominant': dominant}
            )
```

---

## F12 — Event Pre-Validation Filter (CAR-based)

**Inspiração:** Fabio Biancardi Aquino (2018)  
**Tipo:** Filtro de configuração (offline)  
**Complexidade:** Alta (requer análise prévia)  
**Dependências:** Eventos GDELT + cálculo de retornos anormais

### Descrição
Antes de incluir uma classe de evento GDELT (ex: "sanction", "military conflict") no pipeline, calcula o Cumulative Abnormal Return (CAR) histórico dessa classe. Se não houver efeito significativo (p > 0.05), a classe é excluída.

### Implementação (Offline)
```python
class EventPrevalidation:
    """F12 — Pré-validação de eventos por CAR (roda offline, não em tempo real)"""
    
    def __init__(self, estimation_window: int = 60, event_window: int = 5):
        self.estimation_window = estimation_window
        self.event_window = event_window
    
    def calculate_car(self, 
                      event_dates: list[datetime],
                      prices: pd.Series,
                      market_prices: pd.Series) -> dict:
        """
        Calcula CAR para uma classe de evento.
        
        Returns:
            {'mean_car': float, 't_stat': float, 'p_value': float, 
             'significant': bool, 'n_events': int}
        """
        cars = []
        
        for event_date in event_dates:
            # Janela de estimação (pré-evento)
            est_start = event_date - timedelta(days=self.estimation_window)
            est_end = event_date - timedelta(days=1)
            
            # Calcula alpha e beta do market model
            stock_returns = prices.loc[est_start:est_end].pct_change().dropna()
            market_returns = market_prices.loc[est_start:est_end].pct_change().dropna()
            
            beta, alpha = np.polyfit(market_returns, stock_returns, 1)
            
            # Janela de evento
            event_start = event_date - timedelta(days=self.event_window//2)
            event_end = event_date + timedelta(days=self.event_window//2)
            
            actual_returns = prices.loc[event_start:event_end].pct_change().sum()
            expected_returns = alpha + beta * market_prices.loc[event_start:event_end].pct_change().sum()
            
            abnormal_return = actual_returns - expected_returns
            cars.append(abnormal_return)
        
        # Teste t
        mean_car = np.mean(cars)
        se_car = np.std(cars) / np.sqrt(len(cars))
        t_stat = mean_car / se_car if se_car > 0 else 0
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=len(cars)-1))
        
        return {
            'mean_car': mean_car,
            't_stat': t_stat,
            'p_value': p_value,
            'significant': p_value < 0.05,
            'n_events': len(cars)
        }
    
    def filter_event_classes(self, 
                           event_classes: list[str],
                           min_significant_events: int = 10) -> list[str]:
        """Filtra classes de evento, mantendo só as com CAR significativo"""
        valid_classes = []
        
        for event_class in event_classes:
            events = self._get_events_by_class(event_class)
            
            if len(events) < min_significant_events:
                logger.info(f"{event_class}: apenas {len(events)} eventos, descartado")
                continue
            
            car_result = self.calculate_car(events, self.prices, self.market_prices)
            
            if car_result['significant']:
                valid_classes.append(event_class)
                logger.info(f"{event_class}: CAR={car_result['mean_car']:.4f}, "
                           f"p={car_result['p_value']:.4f} - MANTIDO")
            else:
                logger.info(f"{event_class}: CAR={car_result['mean_car']:.4f}, "
                           f"p={car_result['p_value']:.4f} - DESCARTADO")
        
        return valid_classes
```

---

## Configurações de Estratégia Recomendadas

### Estratégia Core (sua atual)
F1 → F2 → F3 → F4 → F5 → F6 → F7

### Estratégia A (Technical Confirmation)
F1 → F2 → F3 → **F8** → F4 → F5 → F6 → F7  
*Adiciona confirmação candlestick - mais conservadora*

### Estratégia B (Quality Control)
F1 → F2 → F3 → **F10** → **F11** → F4 → F5 → F6 → F7  
*Só usa texto se confiante e scorers concordam - menos trades, melhor qualidade*

### Estratégia C (Regime-Aware)
F1 → **F9** → F2 → F3 → F4 → F5 → F6 → F7  
*Filtra por viabilidade de regime antes de tudo - evita operar em caos*

### Estratégia D (Full Validation)
F1 → F2 → F3 → **F8** → **F10** → **F11** → F4 → F5 → F6 → F7  
*Todas as checagens - mais seletiva, menor drawdown potencial*

### Estratégia E (Event-Validated)
*(Pré-processada com F12)*  
F1 → F2 → F3 → F4 (só eventos CAR-significativos) → F5 → F6 → F7  
*Usa apenas eventos que historicamente tiveram impacto*

---

## Prioridade de Implementação

| Filtro | Esforço | Impacto Esperado | Prioridade |
|--------|---------|------------------|------------|
| F8 (Candlestick) | Baixo | Médio | ⭐⭐⭐⭐⭐ |
| F10 (Confidence) | Baixo | Alto | ⭐⭐⭐⭐⭐ |
| F11 (Disagreement) | Baixo | Médio-Alto | ⭐⭐⭐⭐ |
| F9 (Regime) | Médio | Alto | ⭐⭐⭐⭐ |
| F12 (CAR) | Alto | Médio | ⭐⭐⭐ |

---

*Especificação para implementação dos filtros adicionais*
