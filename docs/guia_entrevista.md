# Como estudar e defender o projeto

## Apresentação de 60 segundos

“Escolhi um problema industrial próximo da minha experiência com perdas, eficiência e TPM. Usei uma base pública sintética para classificar observações com falha. Separei treino, validação e teste, retirei identificadores e indicadores que revelavam o alvo, comparei um baseline simples com regressão logística e floresta aleatória e escolhi o limiar na validação. No teste, a floresta detectou 55 das 68 falhas, com 67 falsos alarmes. O principal aprendizado foi discutir a relação entre cobertura das falhas e carga de inspeção. Não afirmo previsão antecipada nem economia real, porque a base não permite isso.”

Use essa fala depois de executar o projeto e entender cada decisão. Apresente com transparência a assistência de IA na construção; o valor na entrevista está em verificar, explicar e conseguir modificar o trabalho.

## Quatro sessões de estudo

1. **Dados e contexto, 30–45 minutos:** ler README e dicionário; executar o pipeline; explicar o que representa uma linha, o que é sintético e quais campos faltam para medir paradas.
2. **Estatística e avaliação, 45 minutos:** reconstruir a matriz de confusão a partir do CSV do teste; calcular precisão, recall e custo relativo à mão; comparar com a acurácia do baseline.
3. **Código, 45–60 minutos:** seguir `data.py → modeling.py → run.py`; localizar o split, a lista de entradas, o `fit`, o limiar e a primeira consulta ao teste; rodar os testes.
4. **Comunicação e Power BI, 45–60 minutos:** importar os CSVs, criar as medidas e narrar as duas páginas do painel. Explicar por que 45,1% de precisão pode ser insuficiente para uma operação com pouca capacidade de inspeção.

## Perguntas frequentes

**Por que não usar acurácia para selecionar?** Com poucas falhas, prever sempre “sem falha” acerta quase tudo. Isso não encontra nenhum caso positivo. AP, recall, precisão e erros absolutos mostram o problema.

**Por que retirar os modos de falha?** Eles descrevem o desfecho. Usá-los permitiria ao modelo consultar parte da resposta, produzindo avaliação enganosa. IDs também não representam condições físicas úteis.

**Por que floresta?** A comparação na validação favoreceu a floresta, que consegue representar relações não lineares e interações. Não foi escolhida apenas por parecer mais sofisticada.

**Por que limiar 0,29, e não 0,5?** A validação minimizou um custo hipotético `FP + 10 × FN`. O limiar é uma política dependente dos custos, do modelo e dos dados; não é regra universal.

**O que significa precisão de 45,1%?** Dos 122 alertas do teste, 55 correspondem a falhas rotuladas e 67 são falsos alarmes. Isso não equivale a 45,1% de probabilidade calibrada para cada equipamento.

**Você está prevendo o futuro?** Não há timestamps nem janela entre leitura e falha. É classificação da observação; antecipação temporal precisa de outro desenho e outros dados.

**Qual ganho a empresa teria?** Não foi medido. Seria necessário validar custos, disponibilidade das leituras, capacidade de inspeção e efeito de uma intervenção em piloto controlado.

**Encontrou algum problema nos dados?** Há 27 divergências entre o alvo e o OR dos indicadores de modos. Preservei o rótulo principal, registrei as linhas e tratei isso como limite da fonte.

**Qual próximo passo técnico?** Dados reais com equipamento e tempo, qualidade dos rótulos, horizonte útil, validação temporal/por grupo, calibração e monitoramento em modo observação antes de qualquer automação.

## Exercícios que demonstram domínio

- Reconstruir `55/(55+13)` e `55/(55+67)` e explicar os denominadores.
- Ler a sensibilidade da validação e descrever como o custo de FN muda a política de alertas.
- Explicar por que os intervalos de confiança não validam uma aplicação em outra fábrica.
- Alterar apenas uma visualização ou o painel e verificar que as métricas permanecem iguais. Para experimentar outro modelo, versionar o protocolo e reconhecer que o teste já foi visto.
