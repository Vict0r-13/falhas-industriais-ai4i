# Kit de integração Power BI

Este diretório contém dados e especificação para montar o relatório no Power BI Desktop. **Não é um arquivo `.pbix` ou `.pbit`.** As consultas M e medidas DAX foram preparadas para integração; a execução e o layout no Power BI Desktop ainda precisam de validação. Totais, rótulos, partições e denominadores dos CSVs foram verificados em Python.

## Importação e modelo

1. Execute o pipeline Python para atualizar os arquivos de `data/`.
2. No Power Query, crie um parâmetro de texto `PastaDados` contendo o caminho absoluto da pasta `powerbi/data` desta cópia, terminado em `/` ou `\`.
3. Crie uma consulta em branco chamada `LerCSV`, abra o Editor Avançado e cole o conteúdo de `LerCSV.m`.
4. Crie duas consultas em branco chamadas **Observacoes** e **Predicoes**, usando os arquivos M correspondentes. Elas fixam tipos e interpretação decimal `en-US`. Os CSVs usam UTF-8 BOM e vírgula como delimitador.
5. Mantenha **Observacoes** e **Predicoes desconectadas**, com segmentações próprias em cada página. Não sincronize filtros entre elas. Isso evita misturar descrição da base inteira e desempenho do teste.
6. Crie cada medida de `medidas.dax` separadamente, na tabela indicada. Se a instalação usar separadores DAX localizados, adapte as vírgulas conforme a configuração do editor. Formate taxas com uma casa decimal e contagens como inteiros.
7. Opcionalmente importe `tema.json` em Exibição → Temas. Configure as páginas em 16:9.

### Grão e campos

| CSV | Grão | Uso |
|---|---|---|
| observacoes.csv | Uma observação sintética; UDI único; 10.000 linhas | Descrição da base, campos operacionais, alvo, conjunto e faixa de desgaste |
| predicoes_teste.csv | Uma observação reservada; UDI único; 2.000 linhas | Avaliação do modelo selecionado: Type, falha_real, score_falha, alerta, limiar, resultado |
| resumo_condicoes.csv | Conjunto × Type × faixa_desgaste | Agregado alternativo; taxa = soma falhas / soma registros |
| metricas_teste.csv | Um modelo; duas linhas | Resultado global fixo do escolhido e baseline; não responde a filtros de variante |
| sensibilidade_validacao.csv | Uma razão hipotética de custo FN/FP | Comparar políticas na validação; não estimar economia |

Faixas de desgaste: 0–99, 100–199 e 200+ minutos de desgaste acumulado. São grupos descritivos predefinidos, não limites de manutenção. `resultado` assume TP, FP, FN ou TN. `score_falha` é um score do modelo, não probabilidade calibrada. Não criar dimensão calendário com UDI.

## Página 1 — Condições e falhas observadas

Título: **Condições operacionais e falhas**. Subtítulo visível: **AI4I 2020 • dados sintéticos • observações sem calendário**.

- Topo: cartões `Observações`, `Falhas observadas` e `Taxa de falha`.
- Esquerda: filtros da tabela Observacoes para `Type`, `conjunto` e `faixa_desgaste`. Começar sem filtros para contextualizar os 10.000 registros. Para reproduzir a EDA, escolher `conjunto = treino`.
- Centro: barras de `Taxa de falha` por Type; tooltip com numerador e denominador. Barras de taxa por faixa de desgaste, ordenadas 0–99, 100–199, 200+.
- Base: dispersão com torque no eixo X, rotação no Y, UDI nos detalhes e falha_real na legenda, sem agregar UDI. Se houver amostragem pelo visual, informar isso; não usar a nuvem para contar falhas.
- Rodapé: **Associação descritiva. Desgaste não mede parada. Não há OEE ou economia calculados.**

## Página 2 — Qualidade dos alertas no teste

Título: **Avaliação em observações reservadas**. Subtítulo: **Floresta aleatória • limiar 0,29 definido na validação • custo hipotético FN:FP = 10:1**.

- Topo: cartões `Observações avaliadas`, `Falhas no teste`, `Alertas`, `Recall` e `Precisão`.
- Centro esquerdo: matriz com linhas `falha_real`, colunas `alerta`, valores `Observações avaliadas`. Renomear 0/1 visualmente como Sem falha/Com falha e Sem alerta/Alerta, mantendo os números de origem.
- Centro direito: barras de contagem por `resultado`. Usar laranja para FP e FN, azul para TP/TN e rótulos explícitos.
- Base: tabela de inspeção com UDI, Type, falha_real, score_falha, alerta e resultado. Não inserir ação de parada de máquina.
- Filtro opcional de Type vindo **somente de Predicoes**. As contagens e taxas DAX recalculam para o subconjunto. Não filtrar por resultado/alerta/falha_real para comparar taxas de desempenho sem avisar que o denominador mudou.
- AP 0,6407 e ROC AUC 0,9650 podem aparecer em uma nota **Teste completo, sem filtros**. Não usar esses valores fixos como se fossem recalculados por Type. O IC publicado também vale para o teste completo.
- Rodapé: **Classificação de observações sintéticas. Não comprova antecipação de falhas nem ganho fabril.**

Use azul `#247D93`, laranja `#E17543`, texto `#17324D`, fundo claro. Mantenha as definições de FP/FN junto da matriz e contraste legível. Não usar velocímetros de “eficiência”, indicadores financeiros nem linha temporal.

## Reconciliação antes de apresentar

Sem filtros, página 1: **10.000 observações, 339 falhas, taxa de 3,39%**. Página 2: **2.000 observações, 68 falhas, 122 alertas, TP=55, FP=67, FN=13, TN=1.865, recall=80,88%, precisão=45,08%**. Filtro vazio deve exibir taxa em branco, não um sucesso de 100%.

Taxa agregada deve dividir **soma de falhas por soma de registros**. Não tirar a média simples de taxas dos grupos. Não somar as linhas de `metricas_teste.csv` (dois modelos avaliados na mesma população) como se fossem 4.000 observações distintas. UDI serve apenas para rastrear a observação, nunca para agrupar eventos por máquina.

Se o painel mostrar números diferentes, conferir filtros, nomes de consultas, tipos de dados e separador decimal. Após cada atualização do Python, atualizar o Power BI e reconciliar novamente. Só depois salvar o `.pbix` e exportar as duas páginas para apresentação.

Referências: [Csv.Document](https://learn.microsoft.com/en-us/powerquery-m/csv-document) e [DIVIDE](https://learn.microsoft.com/en-us/dax/divide-function-dax). Fonte dos dados: [UCI AI4I 2020](https://doi.org/10.24432/C5HS5C), CC BY 4.0; CSV original preservado e exportações derivadas pelo pipeline.
