# Protocolo e decisões

## Problema

Classificar se uma observação de condições operacionais está associada a uma falha rotulada. O contexto de análise de perdas, Lean e TPM ajuda a discutir inspeções e priorização. A base não permite atribuir redução de perdas ao modelo, calcular OEE ou antecipar uma parada com um horizonte definido.

## Dados e integridade

Fonte: [AI4I 2020, UCI](https://doi.org/10.24432/C5HS5C). O CSV original está preservado, com licença CC BY 4.0 e hash em `data/source.json`. São 10.000 observações sintéticas. A aquisição verifica o SHA-256 tanto no cache quanto em um novo download. Uma mudança na fonte interrompe a execução.

A validação verifica esquema, número de linhas, valores ausentes, unicidade de UDI, categorias, alvos binários e entradas finitas e não negativas. Não há imputação, remoção de extremos, balanceamento artificial por duplicação ou correção automática de rótulos. `reports/qualidade.json` e `reports/divergencias_rotulos.csv` registram as verificações; o alvo principal é mantido mesmo quando diverge do OR dos modos. Isso é uma limitação da fonte, não autorização para reconstruir o alvo.

## Entradas e vazamento

| Campo | Unidade/papel | Decisão |
|---|---|---|
| Type | Variante L, M ou H | One-hot encoding |
| Air temperature [K] | kelvin | Entrada numérica |
| Process temperature [K] | kelvin | Entrada numérica |
| Rotational speed [rpm] | rotações/minuto | Entrada numérica |
| Torque [Nm] | newton-metro | Entrada numérica |
| Tool wear [min] | minutos de desgaste da ferramenta | Entrada numérica; não é duração de parada |
| Machine failure | alvo binário | Somente supervisão e avaliação |
| UDI, Product ID | identificadores da observação/produto | Excluídos dos preditores |
| TWF, HDF, PWF, OSF, RNF | indicadores dos modos de falha | Excluídos dos preditores; revelam o desfecho |

Uma lista permitida de seis entradas é mais segura que excluir apenas alguns campos conhecidos. UDI aparece nas exportações somente para auditoria e junção. Não é data nem identificação de máquina. Nenhuma variável derivada das regras sintéticas da fonte foi acrescentada para inflar a avaliação.

## Separação dos dados

Seed 42, split estratificado 60% treino, 20% validação e 20% teste. Primeiro reserva-se o teste; depois separa-se a validação do restante. IDs de cada partição são exportados. EDA orientada a escolhas usa apenas o treino. Escalonamento e codificação ficam dentro de `Pipeline`/`ColumnTransformer` e são ajustados somente no treino.

O split aleatório testa generalização dentro da distribuição sintética. Não há suporte para validação temporal real ou separação por máquina. A geração de temperaturas tem dependência entre registros; misturar observações relacionadas pode tornar a avaliação otimista. A estratificação preserva a proporção do alvo, mas não resolve dependência. Em dados fabris, dividir por tempo/equipamento e considerar janela, horizonte e intervalo de exclusão antes de comparar modelos.

## Comparação enxuta

- **Dummy prior:** score constante igual à prevalência do treino. Com limiar 0,5, classifica todas as observações sem falha. Expõe por que acurácia pode enganar.
- **Regressão logística:** baseline linear interpretável, `class_weight=balanced`, numéricas padronizadas, máximo de 2.000 iterações.
- **Floresta aleatória:** 300 árvores, profundidade máxima 10, mínimo de duas amostras por folha, `balanced_subsample`, uma thread e seed fixa. Captura interações e relações não lineares. Esses parâmetros foram definidos antes do teste; não houve busca de hiperparâmetros.

O mesmo escalonamento é usado para simplicidade do pipeline; árvores não precisam dele. Os pesos de classe aumentam a atenção às falhas sem criar observações sintéticas extras. Scores de modelos com pesos de classe não devem ser apresentados como probabilidades calibradas.

Escolha pela maior **average precision (AP) na validação**. AP é útil com alvo raro porque resume precisão/recall, considerando a prevalência. Não equivale à integral trapezoidal da curva PR. ROC AUC é complementar. Precisão, recall, F2 e matriz de confusão descrevem o limiar operacional. Acurácia fica como contraste com o baseline, não como objetivo.

## Limiar e custo

Depois de escolher o modelo, o limiar minimiza `FP + 10 × FN` na validação, em uma grade 0,01 a 0,99, mais 1,000001 para a opção sem alertas. Empates favorecem menos FP e depois limiar maior. O custo 10:1 é uma hipótese didática em unidades relativas; não são reais nem estimativas fabris. Sensibilidade para razões 1, 5, 10 e 20 é calculada somente na validação.

Um falso alarme pode gerar inspeção desnecessária. Uma falha não detectada pode deixar de sinalizar um caso relevante. A gravidade depende do processo e precisa ser estimada com especialistas. Não se recomenda acionar ou parar equipamento automaticamente por este score.

`reports/selecao.json` é salvo antes da avaliação final. Modelo e limiar ficam congelados, e o modelo continua treinado nas 6.000 observações originais. Não se faz refit em treino+validação porque isso pode alterar a escala dos scores que sustentou a escolha do limiar. O teste avalia apenas o selecionado e o baseline de referência. Curva PR no teste é descritiva; não serve para escolher um novo corte.

## Incerteza e explicação

Intervalos de Wilson de 95% para precisão/recall são aproximações binomiais condicionais ao modelo fixado e à independência. Não medem variação entre treinos nem resolvem dependência sintética. Há poucos positivos no teste, portanto os percentuais têm incerteza relevante.

Importância por permutação, com dez repetições e AP como medida, é calculada na validação. Indica dependência do modelo da variável. Correlação entre entradas pode diluir importâncias. Associação e importância preditiva não provam causalidade; não sustentam recomendações de alterar setpoints industriais.

## Reprodução versus novos experimentos

Reexecutar o mesmo protocolo e conferir resultados é uma verificação de reprodução. Mudar entradas, modelos, seed ou limiar depois de conhecer o teste cria outro experimento e contamina a interpretação do teste como inédito. Registre mudanças e use uma nova avaliação independente para alegar generalização.

Referências técnicas: [prevenção de vazamento em pipelines](https://scikit-learn.org/1.6/common_pitfalls.html), [average precision](https://scikit-learn.org/1.6/modules/generated/sklearn.metrics.average_precision_score.html), [importância por permutação](https://scikit-learn.org/1.6/modules/permutation_importance.html).
