# Interesting Ideas From `related-work`

## Method Note

This report is an original analysis written by Codex from a critical reading of the material in `related-work/`. It does not copy the wording, structure, or conclusions of the other reports. The PDFs were used only as source material to extract themes, methodological cues, and possible extensions relevant to the current TCC.

Este documento resume os TCCs e monografias em `related-work/` que têm alguma relação útil com o tema da monografia principal: estratégia híbrida de Forex com sinais técnicos, sentimentais e de eventos, executada por uma cadeia determinística de filtros. O foco aqui não é inventariar tudo, mas separar o que realmente pode ser aproveitado em texto, argumento metodológico ou extensão futura.

## Critério de triagem

- Trabalhos diretamente ligados a trading, câmbio, arbitragem estatística ou combinação de sinais tiveram prioridade.
- Trabalhos de PLN sem ligação com finanças foram avaliados apenas como fonte de ideias de filtragem, calibração e arquitetura de classificação.
- Alguns PDFs parecem ser essencialmente imagem ou tiveram extração textual ruim; nesses casos, eles não entraram na análise substantiva.

## Trabalhos diretamente relevantes

### 1. `Bruno_Van_Helden_Monografia.pdf`

Relação com o TCC atual: alta.

Pontos principais identificados:

- O trabalho compara estratégias fundamentalistas e técnicas no mercado cambial latino-americano.
- A conclusão central é que o modelo combinado, usando análise fundamentalista e técnica em conjunto, foi mais eficiente do que cada abordagem isolada.
- O texto também afirma que o modelo misto apresentou maiores índices de Sharpe e, em média, menor número de transações por ano.

Por que isso é útil:

- Isso reforça a tese central da sua monografia de que sinais heterogêneos podem ser complementares em FX.
- Mesmo sem usar NLP ou GDELT, o trabalho ajuda a sustentar o argumento de que a combinação de famílias de sinal não é um capricho metodológico, mas uma hipótese empiricamente plausível em câmbio.
- Há valor especialmente para o posicionamento do Capítulo 02 ou do início do Capítulo 03: antes mesmo de entrar em FinBERT e GDELT, já existe evidência de que modelos híbridos superam versões isoladas no domínio cambial.

Ressalva metodológica:

- O trabalho é útil como ancestral arquitetural, mas não como referência de protocolo rigoroso no padrão do seu TCC. A avaliação parece bem menos conservadora do que CPCV + embargo + held-out test, então convém citá-lo com cautela metodológica.

Trecho de aproveitamento conceitual:

- A ideia de complementaridade entre análise técnica e fundamentalista pode ser usada como antecessora conceitual da sua proposta, na qual o “fundamentalista” é expandido para uma camada de texto, eventos e regime geopolítico.

Possível uso no texto:

- Inserir como evidência de apoio à lógica híbrida, deixando claro que o seu trabalho dá um passo adicional: em vez de combinar apenas técnica e fundamentos macro tradicionais, combina técnica, padrões, sentimento textual e eventos.

### 2. `Claudinei_Felix.pdf`

Relação com o TCC atual: alta.

Pontos principais identificados:

- O trabalho aplica IA ao problema de previsão de pontos de compra e venda em contexto de swing trading.
- A modelagem usa indicadores técnicos, padrões candlestick e comparação entre vários classificadores, com destaque para LGBM e XGBoost.
- Entre os modelos reportados, o LGBM aparece como opção especialmente atraente por desempenho forte com custo computacional menor.
- O próprio texto reconhece que operadores de mercado também recorrem a informação textual, notícias e publicações de analistas, mas a implementação permanece essencialmente price-side.

Por que isso é útil:

- É um related work muito próximo em espírito: trading sistemático com ML sobre features de mercado, mas ainda sem camada textual realmente incorporada.
- Isso ajuda a explicitar o gap que o seu TCC fecha: sair de uma IA baseada só em indicadores/padrões e avançar para uma arquitetura híbrida com notícias, sentimento e eventos.
- Também reforça a legitimidade de manter o lado técnico forte; o trabalho sugere que a camada de preço não deve ser uma baseline fraca.

Ressalva metodológica:

- Como a avaliação parece baseada em split único, os números fortes de ROC-AUC devem ser tratados mais como evidência sugestiva de engenharia do que como prova robusta de generalização.

Ideias práticas derivadas:

- fortalecer o `pattern filter` com um conjunto mais explícito de padrões candlestick de reversão e continuação;
- considerar um `candlestick-confirmation gate`: sinal textual direcional só vira trade se o lado preço não o contradisser totalmente;
- manter LGBM como referência plausível para eventuais comparações futuras de submodelos ou meta-learner;
- testar Heikin-Ashi e OBV como extensões baratas do lado preço, caso você queira enriquecer a baseline sem mexer na camada textual.

Possível uso no texto:

- No Capítulo 01 ou no início do Capítulo 03, como exemplo de trabalho próximo que já usa IA e análise técnica, mas não incorpora de fato a camada textual que seu TCC propõe.

### 3. `AtilaVeiga.pdf`

Relação com o TCC atual: média para alta.

Pontos principais identificados:

- O trabalho estuda otimização heurística de parâmetros em `pairs trading` com ativos cointegrados.
- O resultado experimental foi inconclusivo e o autor explicitamente atribui isso ao risco de sobreajuste na otimização.
- Na conclusão, o autor diz que, antes de investir em otimizadores pesados, pode ser mais vantajoso melhorar o desenho da estratégia, criar novas regras de montagem e reversão, e sofisticar filtros.
- Ele também sugere algo análogo a `early stopping` para reduzir sobreajuste em otimização.

Por que isso é útil:

- Isso conversa muito bem com a postura metodológica já adotada na sua monografia: disciplinar a validação, evitar exuberância de Sharpe e preferir arquitetura auditável a hiperparametrização agressiva.
- O trabalho funciona como suporte indireto para defender a sua decisão de enfatizar filtros determinísticos e validação conservadora em vez de “espremer” performance por tuning extensivo.

Trechos aproveitáveis como argumento:

- Refinamento de estratégia por desenho de regras e filtros pode ser mais eficiente do que refinamento por otimização pesada.
- Qualquer tentativa de otimizar estratégia de trading sobre processo estocástico exige mecanismos explícitos de controle de sobreajuste.

Possível uso no texto:

- Na seção de ameaças à validade ou justificativa metodológica, como argumento adicional a favor de manter thresholds calibrados com disciplina e evitar uma busca hiperparamétrica muito ampla.

Ideia prática derivada:

- Criar um “filtro de robustez de calibração”, mesmo que apenas como proposta futura: se uma configuração só funciona em subconjuntos estreitos ou é muito sensível a pequenas mudanças de limiar, ela não entra em produção/backtest final.

### 4. `HoDonLee TCCPRO14.pdf`

Relação com o TCC atual: média, mas com ideias práticas fortes.

Pontos principais identificados:

- O trabalho formaliza `pairs trading` estatístico com foco em cointegração, `mean drift`, `tradability` e regras explícitas de entrada/saída.
- O conceito mais útil é o de `tradability`: não basta uma relação teórica; é preciso checar se a série residual preserva grau suficiente de reversão à média para ser negociável.
- O autor destaca que eventos corporativos podem destruir a negociabilidade do par, e que nesses casos a estratégia deve ser evitada.
- O texto também observa que parâmetros como coeficiente de cointegração e desvio máximo não são realmente constantes ao longo do tempo.

Por que isso é útil:

- O conceito de `tradability` pode ser traduzido para o seu contexto como um filtro de “negociabilidade do regime” ou “consistência do contexto”.
- Em vez de cointegração entre ações, o equivalente no seu TCC seria perguntar: o contexto atual ainda preserva as condições sob as quais os sinais da cadeia fazem sentido?

Ideia de filtro adicional inspirada neste trabalho:

- `Tradability / regime viability filter`: só permitir operação quando o ambiente recente mostrar reversão, persistência ou estabilidade mínima coerente com a lógica do sinal. Exemplos possíveis:
- distância controlada da volatilidade atual em relação à distribuição recente;
- ausência de ruptura estrutural muito forte nas últimas `N` barras;
- coerência entre regime técnico, spread, ATR e direção prevista pelo meta-learner;
- estabilidade mínima do score agregado de notícias em uma janela curta, para evitar operar em minutos de ruído textual puro.

Outra ideia forte:

- O paralelo entre “evento corporativo que invalida pair trading” e “evento macro que invalida sinal técnico” é muito natural para o seu TCC.
- Você já tem um `news-context filter` com veto para eventos de alto risco; este trabalho reforça teoricamente a utilidade de um veto estrutural quando o evento muda o regime do ativo.

Possível extensão concreta:

- Tornar o `news-context filter` mais explícito como `event-dislocation veto`: em janelas próximas de FOMC, ECB, BOJ, payroll, CPI, guerra/escalada geopolítica ou choque diplomático, a operação é bloqueada ou o limiar terminal é endurecido.

## Trabalhos indiretamente úteis por arquitetura de PLN

### 4. `JoseEduardoAthaydeFerrarini_TCC_2025.pdf`

Relação com o TCC atual: indireta, mas surpreendentemente útil.

Pontos principais identificados:

- O trabalho compara LLMs, SBERT e BerTimbau com `fine-tuning` para classificação de aspectos em feedbacks textuais.
- O autor observa um trade-off claro: modelos com maior revocação capturam mais positivos, mas também elevam falsos positivos; modelos mais específicos acertam mais quando classificam, mas podem perder cobertura.
- O texto sugere combinar modelos com perfis diferentes.
- Há também uma ideia muito reaproveitável: segmentar textos longos por sentença e consolidar os resultados depois.
- O material anexo menciona análise ROC para encontrar o melhor limiar por modelo.

Por que isso é útil:

- Seu pipeline de sentimento também sofre exatamente com esse tipo de trade-off: sensibilidade demais gera ruído; especificidade demais perde notícia relevante.
- Isso fornece base para justificar que o problema não é apenas “classificar sentimento”, mas calibrar o custo relativo de falso positivo e falso negativo.

Ideias práticas derivadas:

- `Confidence filter`: só deixar o score textual entrar na cadeia quando a confiança da inferência exceder um limiar mínimo.
- `Disagreement filter`: quando o léxico Loughran-McDonald e o transformer divergem demais, reduzir peso ou vetar o sinal textual daquele minuto.
- `Sentence-consensus filter`: em vez de usar apenas score agregado por artigo, exigir consistência mínima entre sentenças do mesmo texto. Artigo com polaridade muito fragmentada pode virar sinal fraco ou neutro.
- `Threshold calibration by ROC`: calibrar o limiar de ativação do submodelo de notícias com base em ROC/Youden J na validação, não apenas por convenção.

Observação importante:

- Essa é uma inspiração metodológica, não uma referência temática de mercado. Faz sentido usá-la mais como ideia de extensão da camada de NLP do que como related work central do domínio financeiro.

### 5. `Diogo_Moura_Santos.pdf`

Relação com o TCC atual: indireta.

Pontos principais identificados:

- O trabalho usa pipeline de preparação, normalização, tokenização, embeddings BERT e validação cruzada 10-fold para detecção/categorização de falhas em logs.
- O texto enfatiza a importância da preparação e filtragem dos dados para garantir qualidade.
- O uso de probabilidades derivadas de `softmax` aparece como parte da calibração de predição.

Por que isso é útil:

- Reforça uma ideia simples, mas valiosa para a sua camada textual: pré-processamento e filtro de qualidade do texto importam tanto quanto o classificador.

Ideia prática derivada:

- `Text-quality filter`: descartar ou reduzir o peso de notícias com título/corpo muito curto, ruído excessivo, duplicação extrema, baixa densidade semântica ou metadados incompletos.
- Também reforça a ideia de manter probabilidade calibrada, em vez de empurrar score cru diretamente para decisão.

### 6. `FABIO BIANCARDI AQUINO.pdf`

Relação com o TCC atual: indireta, mas metodologicamente forte.

Pontos principais identificados:

- O trabalho gira em torno de estudo de eventos e detecção de movimentos anômalos associados a insider trading no mercado acionário.
- A peça metodológica útil aqui não é o tema de insider trading em si, mas a lógica de validar se certos eventos realmente carregam conteúdo informacional observável em preço/volume.

Por que isso é útil:

- Essa é uma boa inspiração para validar a sua camada de eventos antes mesmo de olhar para o P&L da estratégia.
- Em vez de assumir que determinada classe GDELT/CAMEO ou determinado regime GPR é útil, você pode verificar se historicamente ela se associa a reação anormal no par.

Limite importante:

- A extração textual desse PDF é fraca. Então eu trataria Biancardi mais como gatilho de ideia metodológica do que como citação forte de conteúdo específico. Se a monografia for citar metodologia de estudo de eventos em detalhe, faz mais sentido apoiar-se também nas referências primárias da literatura de event study.

Ideia prática derivada:

- `Event pre-validation filter`: só manter classes de evento que mostrem efeito histórico minimamente consistente sobre EUR/USD ou USD/JPY;
- isso pode aparecer como validação empírica do feature set, não necessariamente como filtro operacional em tempo real.

Possível uso no texto:

- No Capítulo 04, como subseção de validação do bloco de eventos: antes de perguntar se o modelo ficou lucrativo, perguntar se as classes de evento escolhidas de fato mexem com o ativo.

### 7. `Rafael_Galo_Pugina.pdf`

Relação com o TCC atual: indireta.

Pontos principais identificados:

- O trabalho usa embeddings textuais e classificação supervisionada para previsibilidade em outro domínio.
- A principal ideia transferível é a separação entre geração de representação textual e camada de decisão.

Por que isso é útil:

- Isso reforça que sua camada de percepção não precisa depender apenas de um único scorer de sentimento.
- Embeddings tipo SBERT podem funcionar como encoder paralelo, fallback local ou ablação barata ao lado do pipeline com FinBERT/LLM.

Ideia prática derivada:

- tratar embeddings semânticos como feature materializada adicional no parquet;
- comparar, em trabalho futuro, `embedding-based text features` contra `scalar sentiment features`.

### 8. `RAFAEL_HENRIQUE_LEMES__GALVÃO.pdf`

Relação com o TCC atual: baixa e com confiança limitada.

Pontos principais identificados:

- O material disponível sugere relação com HFT, mas a extração textual deste PDF é ruim e não me dá base suficientemente sólida para apoiar empréstimos metodológicos fortes.

Por que isso é útil:

- A ideia de separar resultados por regime de volatilidade continua boa para o seu TCC, mas aqui ela deve ser tratada como recomendação analítica geral, não como algo fortemente ancorado neste PDF específico.

Ideia prática derivada:

- `volatility-regime evaluation split`: reportar desempenho separadamente em períodos de baixa e alta volatilidade;
- isso não exige mudar a estratégia, só melhora a honestidade analítica da avaliação.

## Ideias de filtros extras para a cadeia do TCC

Aqui estão as ideias que mais valem considerar como adição real à cadeia de filtros, mesmo que inicialmente apenas como proposta em trabalho futuro.

### 1. Filtro de `tradability` ou viabilidade do regime

Inspiração principal:

- `HoDonLee TCCPRO14.pdf`

Descrição:

- Antes de aceitar `p_hat_t`, testar se o mercado está num estado minimamente “operável” para o tipo de sinal emitido.

Como poderia funcionar:

- bloquear trade em volatilidade anormal extrema;
- bloquear trade quando o regime técnico mudou abruptamente nas últimas barras;
- bloquear trade quando a direção do meta-learner entra em conflito forte com regime, spread e ATR;
- bloquear trade quando o sinal textual muda de polaridade com frequência excessiva em janela curta.

Valor para o TCC:

- É um filtro bem coerente com a filosofia “agentic perception, deterministic execution”.
- Ajuda a transformar a cadeia em algo mais defensável do que apenas “probabilidade passou do limiar”.

### 2. Filtro de confiança do sinal textual

Inspiração principal:

- `JoseEduardoAthaydeFerrarini_TCC_2025.pdf`
- `Diogo_Moura_Santos.pdf`

Descrição:

- O submodelo de notícias só influencia a fusão ou a cadeia quando a inferência textual passa um limiar mínimo de confiança.

Implementação possível:

- usar margem entre classes do transformer;
- usar entropia da distribuição de probabilidade;
- usar concordância entre FinBERT e Loughran-McDonald como proxy simples de confiança.

Valor para o TCC:

- Reduz ruído de manchetes ambíguas, irônicas, excessivamente descritivas ou pouco informativas.

### 3. Filtro de consenso por sentença/artigo

Inspiração principal:

- `JoseEduardoAthaydeFerrarini_TCC_2025.pdf`

Descrição:

- Em vez de aceitar um score agregado simples do artigo, verificar se as sentenças relevantes apontam em direção razoavelmente coerente.

Implementação possível:

- classificar sentenças individualmente;
- calcular dispersão intra-artigo;
- rebaixar para neutro artigos com alta contradição interna.

Valor para o TCC:

- Útil especialmente em textos macroeconômicos e geopolíticos, que costumam misturar fato, contexto histórico, citação e opinião.

### 4. Filtro de discordância entre modelos

Inspiração principal:

- `JoseEduardoAthaydeFerrarini_TCC_2025.pdf`

Descrição:

- Quando o léxico e o transformer discordam fortemente, o sinal textual é marcado como incerto.

Implementação possível:

- se `sign(FinBERT) != sign(LM)` e ambos tiverem magnitude alta, reduzir peso do minuto ou vetar o uso daquela observação textual;
- usar a divergência como feature adicional de incerteza.

Valor para o TCC:

- É uma forma simples e elegante de transformar conflito entre scorers em informação útil, em vez de tratá-lo como erro.

### 5. Filtro de deslocamento por evento

Inspiração principal:

- `HoDonLee TCCPRO14.pdf`
- `Bruno_Van_Helden_Monografia.pdf`

Descrição:

- Fortalecer o seu filtro de notícias para não apenas detectar “alto risco”, mas reconhecer explicitamente janelas de deslocamento estrutural.

Implementação possível:

- veto total em minutos próximos de eventos centrais;
- ou endurecimento dinâmico dos thresholds `theta_high` e `theta_low`;
- ou redução forçada de alocação durante eventos com histórico de gap/slippage.

Valor para o TCC:

- Isso aproxima a cadeia do raciocínio operacional de trader real e melhora a defesa de realismo do backtest.

### 6. Filtro de robustez de calibração

Inspiração principal:

- `AtilaVeiga.pdf`

Descrição:

- Rejeitar parametrizações ou regras que dependam de ajuste excessivamente fino.

Implementação possível:

- se pequena variação no limiar gera grande deterioração fora da validação, a regra é considerada frágil;
- usar isso como critério de exclusão de configuração, não apenas como observação ex post.

Valor para o TCC:

- Combina perfeitamente com a crítica a Sharpe exagerado e com a defesa de protocolo conservador.

### 7. Validação prévia das classes de evento

Inspiração principal:

- `FABIO BIANCARDI AQUINO.pdf`

Descrição:

- Antes de consolidar a taxonomia de eventos no pipeline, verificar quais classes realmente mostram algum efeito histórico observável no preço dos pares analisados.

Implementação possível:

- estudar reação média ou retorno anormal em janelas em torno de eventos relevantes;
- descartar classes cujo sinal histórico seja nulo, errático ou indistinguível de ruído.

Valor para o TCC:

- Fortalece muito a defesa metodológica da camada de eventos, porque reduz arbitrariedade na escolha dos features.

### 8. Avaliação estratificada por regime de volatilidade

Inspiração principal:

- boa prática de avaliação, com apoio apenas fraco em `RAFAEL_HENRIQUE_LEMES__GALVÃO.pdf`

Descrição:

- Não é um filtro operacional, mas uma forma melhor de apresentar resultados.

Implementação possível:

- separar métricas em blocos de baixa, média e alta volatilidade;
- verificar se a camada textual/event-driven agrega valor principalmente em janelas turbulentas.

Valor para o TCC:

- Pode revelar onde o híbrido realmente ajuda, em vez de resumir tudo num único Sharpe agregado.

## Tabela de priorização dos filtros sugeridos

Esta tabela resume a minha leitura pragmática das abordagens sugeridas. O foco aqui é: quanto trabalho dá para colocar de pé no projeto atual, e quanto valor isso tende a devolver para a dissertação e para a estratégia.

Escala de esforço:

- `Baixo`: ajuste simples de pipeline, regra ou métrica, sem grande mudança arquitetural.
- `Médio`: exige código novo relevante, calibração e alguma validação adicional.
- `Alto`: exige nova etapa analítica, nova base intermediária ou mudança mais estrutural no pipeline.

Escala de impacto:

- `Alto`: melhora diretamente a defesa metodológica ou a qualidade do sinal.
- `Médio`: tende a ajudar, mas mais como refinamento do que como mudança de jogo.
- `Baixo`: útil como acabamento, sanity check ou trabalho futuro.

| Abordagem | Origem principal | Esforço | Impacto esperado | Maior ganho provável |
| --- | --- | --- | --- | --- |
| `Event pre-validation filter` | `FABIO BIANCARDI AQUINO.pdf` | Alto | Alto | Fortalece a defesa da camada de eventos com validação empírica antes do P&L |
| `Tradability / regime viability filter` | `HoDonLee TCCPRO14.pdf` | Médio | Alto | Evita operar quando o contexto está estruturalmente ruim para a lógica da estratégia |
| `Candlestick-confirmation gate` | `Claudinei_Felix.pdf` | Baixo | Médio-Alto | Reforça a baseline price-side e cria confirmação simples entre preço e texto |
| `Confidence filter` | `JoseEduardoAthaydeFerrarini_TCC_2025.pdf` | Baixo | Alto | Reduz ruído de inferência textual ambígua com custo baixo |
| `Disagreement filter` | `JoseEduardoAthaydeFerrarini_TCC_2025.pdf` | Baixo | Médio-Alto | Usa conflito entre FinBERT e Loughran-McDonald como sinal de incerteza |
| `Sentence-consensus filter` | `JoseEduardoAthaydeFerrarini_TCC_2025.pdf` | Médio | Médio | Melhora qualidade do sinal em artigos longos e internamente contraditórios |
| `Text-quality filter` | `Diogo_Moura_Santos.pdf` | Baixo | Médio | Remove lixo textual e melhora higiene do pipeline |
| `Threshold calibration by ROC/Youden J` | `JoseEduardoAthaydeFerrarini_TCC_2025.pdf` | Baixo | Alto | Dá base estatística melhor para ativação do sinal textual |
| `Event-dislocation veto` | `HoDonLee TCCPRO14.pdf` + seu desenho atual | Baixo-Médio | Alto | Aproxima a estratégia de uma política operacional realista em janelas de choque |
| `Embedding-based text features` | `Rafael_Galo_Pugina.pdf` | Médio | Médio | Abre uma trilha paralela de percepção textual mais barata e reproduzível |
| `Volatility-regime evaluation split` | boa prática analítica | Baixo | Alto | Melhora muito a qualidade da leitura dos resultados no capítulo experimental |
| `Calibration-robustness gate` | `AtilaVeiga.pdf` | Médio | Médio-Alto | Ajuda a evitar conclusões baseadas em limiares frágeis ou superajustados |
| `Heikin-Ashi / OBV` no lado preço | `Claudinei_Felix.pdf` | Baixo | Médio | Enriquece a baseline técnica sem tocar na camada textual |

### Resultado de maior impacto

Se o critério for **maior impacto total para a dissertação**, eu destacaria três itens:

1. `Event pre-validation filter`

Motivo:

- melhora muito a credibilidade metodológica da camada de eventos;
- ajuda a justificar por que certas classes GDELT/GPR entram e outras não;
- enriquece diretamente `../monografia/chapters/04-experimental-evaluation.tex`.

2. `Tradability / regime viability filter`

Motivo:

- é o filtro conceitualmente mais alinhado com a sua arquitetura de execução determinística;
- conversa muito bem com a ideia de veto contextual;
- melhora tanto a estratégia quanto a narrativa metodológica em `03-methodology.tex`.

3. `Confidence filter` + `Threshold calibration by ROC/Youden J`

Motivo:

- provavelmente é o refinamento mais barato com melhor retorno na camada textual;
- reduz ruído sem exigir mudança grande de arquitetura;
- ajuda a defender que a percepção textual não entra crua na decisão.

### Combinação mais eficiente custo-benefício

Se a pergunta for “o que eu implementaria primeiro para maximizar impacto com esforço controlado?”, a minha resposta seria:

1. `Confidence filter`
2. `Threshold calibration by ROC/Youden J`
3. `Candlestick-confirmation gate`
4. `Volatility-regime evaluation split`

Essa combinação tem esforço relativamente baixo e já melhora bastante:

- a qualidade do sinal textual;
- a coerência entre preço e notícia;
- a apresentação dos resultados na dissertação.

## Sugestões de aproveitamento textual na monografia

Nesta seção, "monografia" significa o texto em `../monografia`, especialmente:

- `../monografia/chapters/02-theoretical-foundation.tex`
- `../monografia/chapters/03-methodology.tex`
- `../monografia/chapters/04-experimental-evaluation.tex`
- `../monografia/chapters/05-conclusion.tex`

### A. Related work / fundamentação

Vale mencionar `Bruno_Van_Helden_Monografia.pdf` como evidência de que, no domínio cambial, a combinação de sinais heterogêneos já mostrou complementaridade, ainda que em moldura anterior à NLP financeira moderna.

Relevância para `../monografia`:

- entra naturalmente em `02-theoretical-foundation.tex` como antecedente de estratégia híbrida em FX;
- também ajuda a abrir `03-methodology.tex`, na parte de posicionamento relativo ao prior art;
- deve ser citado com a ressalva de que o seu TCC usa um protocolo de validação mais rigoroso.

### B. Metodologia

`AtilaVeiga.pdf` e `HoDonLee TCCPRO14.pdf` podem aparecer como suporte para duas decisões metodológicas:

- a preferência por regras e filtros auditáveis sobre otimização agressiva de parâmetros;
- a necessidade de um mecanismo explícito de veto quando o contexto deixa de ser negociável.

`Claudinei_Felix.pdf` é útil para mostrar um estado intermediário da literatura aplicada: IA + indicadores + padrões já aparece, mas ainda sem a incorporação sistemática de notícias, sentimento e eventos. Ele também sugere um empréstimo barato para experimentação: comparar LGBM com o meta-learner atual ou usá-lo em alguma ablação do lado preço.

Relevância para `../monografia`:

- `AtilaVeiga.pdf` fortalece `03-methodology.tex` na justificativa contra tuning agressivo e em favor de desenho disciplinado;
- `HoDonLee TCCPRO14.pdf` fortalece `03-methodology.tex` na defesa de um filtro explícito de viabilidade de regime / contexto;
- `Claudinei_Felix.pdf` pode entrar no começo de `03-methodology.tex` como contraste com trabalhos que já usam ML no lado preço, mas não incorporam camada textual;
- se você quiser uma melhoria de engenharia de baixo risco, Felix também conversa com a implementação do baseline price-only descrita na metodologia.

### C. Trabalhos futuros

As melhores extensões futuras inspiradas em `related-work/` parecem ser:

- filtro de `tradability` do regime;
- filtro de confiança textual;
- análise por sentença com consolidação intra-artigo;
- calibração de limiar por ROC/Youden J;
- filtro de discordância entre scorers.

Relevância para `../monografia`:

- essas ideias entram melhor em `05-conclusion.tex`, na parte de roadmap e extensões futuras;
- se você não quiser inflar o escopo da implementação, pode mantê-las fora do núcleo de `03-methodology.tex` e registrá-las como próxima iteração natural.

### D. Avaliação experimental

Há dois reaproveitamentos particularmente bons para o Capítulo 04:

- usar a inspiração de `FABIO BIANCARDI AQUINO.pdf` para justificar uma validação prévia das classes de evento;
- reportar resultados por regime de volatilidade, não só no agregado, como melhoria geral de leitura dos resultados.

Relevância para `../monografia`:

- o ponto de Biancardi ajuda diretamente a enriquecer `04-experimental-evaluation.tex`, criando uma subseção de validação do bloco de eventos;
- a estratificação por volatilidade também melhora `04-experimental-evaluation.tex`, porque mostra onde o híbrido realmente agrega valor;
- ambos os itens são mais relevantes para o capítulo experimental do que para a fundamentação.

### E. Mapeamento curto de relevância

Se a pergunta for "o que é mais relevante para a monografia em `../monografia`?", a ordem hoje é:

1. `Bruno_Van_Helden_Monografia.pdf`: mais relevante para `02-theoretical-foundation.tex` e para o posicionamento de `03-methodology.tex`.
2. `Claudinei_Felix.pdf`: mais relevante para a justificativa do gap do trabalho e para fortalecer a baseline price-only em `03-methodology.tex`.
3. `AtilaVeiga.pdf`: mais relevante para a defesa metodológica em `03-methodology.tex` e para ameaças à validade.
4. `HoDonLee TCCPRO14.pdf`: mais relevante para justificar um filtro de viabilidade de regime em `03-methodology.tex`.
5. `FABIO BIANCARDI AQUINO.pdf`: mais relevante para enriquecer `04-experimental-evaluation.tex`.
6. `JoseEduardoAthaydeFerrarini_TCC_2025.pdf` e `Diogo_Moura_Santos.pdf`: mais relevantes como refinamento da camada textual e discussão de extensões, não como eixo central da fundamentação financeira.

## Força da evidência

Nem todo trabalho aqui serve do mesmo jeito para a monografia. A distinção prática é:

- `Bruno_Van_Helden_Monografia.pdf`, `Claudinei_Felix.pdf`, `AtilaVeiga.pdf` e `HoDonLee TCCPRO14.pdf` são os melhores para sustentar argumento ou desenho metodológico.
- `JoseEduardoAthaydeFerrarini_TCC_2025.pdf`, `Diogo_Moura_Santos.pdf` e `Rafael_Galo_Pugina.pdf` são melhores como empréstimo de arquitetura de NLP e calibração, não como evidência financeira.
- `FABIO BIANCARDI AQUINO.pdf` é melhor como inspiração de validação do bloco de eventos do que como citação textual forte, por causa da limitação de extração do PDF.
- `RAFAEL_HENRIQUE_LEMES__GALVÃO.pdf` continua fraco demais para sustentar coisa importante sozinho.

## Material que parece menos útil para este TCC

Os seguintes trabalhos continuam parecendo laterais demais para o corpo principal, embora possam render ideias pontuais:

- `Bruna_Magrini_da_Cruz_TCC_2025.pdf`
- `Bruno_Henrique_de_Brito_TCC_2025.pdf`
- `Jean_Lourenço_da_Silva.pdf`
- `tc5029-Aila-Goulart-Uso.pdf`

Eles servem mais como repertório metodológico de NLP e estruturação de saída do que como related work central da monografia.

## Prioridade prática

Se a ideia for melhorar o TCC com o menor custo e o maior retorno argumentativo, a ordem mais forte hoje me parece ser:

1. Citar `Bruno_Van_Helden_Monografia.pdf` e `Claudinei_Felix.pdf` para fortalecer o enquadramento do related work em trading híbrido / AI trading.
2. Testar, se houver tempo, uma ablação barata com LGBM ou ao menos registrar isso como comparação recomendada, porque é um empréstimo de baixo custo vindo de `Claudinei_Felix.pdf`.
3. Incorporar de `AtilaVeiga.pdf` e `HoDonLee TCCPRO14.pdf` a defesa de filtros auditáveis, veto de contexto e cautela com otimização excessiva.
4. Trazer de `FABIO BIANCARDI AQUINO.pdf` a ideia de validar empiricamente as classes de evento.
5. Reportar resultados por regime de volatilidade como melhoria analítica geral, sem depender fortemente do PDF do Galvão.
6. Deixar os refinamentos de NLP mais finos (`confidence`, `disagreement`, `sentence-consensus`) como extensões fortes, mas secundárias frente ao núcleo financeiro-metodológico.

## Síntese final

Se eu tivesse que resumir em uma linha o melhor aproveitamento de `related-work/`, seria este:

- `Bruno_Van_Helden_Monografia.pdf` ajuda a sustentar a tese híbrida;
- `Claudinei_Felix.pdf` ajuda a mostrar o ponto exato em que a literatura próxima ainda para no price-side;
- `Claudinei_Felix.pdf` também rende o empréstimo mais barato de implementação: reforço do lado preço e comparação com LGBM;
- `AtilaVeiga.pdf` ajuda a sustentar a cautela contra sobreajuste e a primazia de filtros/arquitetura sobre tuning agressivo;
- `HoDonLee TCCPRO14.pdf` oferece a melhor ideia de filtro extra: um mecanismo de `tradability` ou viabilidade do regime;
- `FABIO BIANCARDI AQUINO.pdf` oferece a melhor ideia de validação para o bloco de eventos;
- separar desempenho por regime de volatilidade continua sendo uma boa melhoria de leitura dos resultados, mas eu a trato agora como recomendação analítica geral, não como ponto forte sustentado pelo PDF do Galvão;
- `JoseEduardoAthaydeFerrarini_TCC_2025.pdf` oferece a melhor ideia para a camada de NLP: confiança, segmentação por sentença e calibração de limiar;
- `Diogo_Moura_Santos.pdf` reforça a importância de filtro de qualidade textual e probabilidades calibradas.

O melhor filtro novo, se for para escolher só um, é:

- `tradability / regime viability filter`.

O melhor refinamento para a camada de notícias, se for para escolher só um, é:

- `confidence + disagreement filter` entre FinBERT e Loughran-McDonald.
