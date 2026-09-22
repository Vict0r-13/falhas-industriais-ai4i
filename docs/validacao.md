# Registro de validação da entrega

Execução local em Windows, Python 3.12.14. Versões diretas em `reports/ambiente.json`; dependências completas em `requirements-lock.txt`.

## Verificações realizadas

- Pipeline completo executado com os dados oficiais incluídos, gerando todos os relatórios, figuras e exportações.
- Dez testes `unittest` aprovados: contrato de esquema/alvo; rejeição de cache adulterado; aquisição sem cache com resposta ZIP simulada; partições completas, disjuntas e estratificadas; seis entradas e escalonamento ajustado no treino; métricas contra exemplo manual; limiar escolhido na validação; predições do teste reconciliadas com o CSV original; agregados Power BI com numeradores e denominadores preservados; rejeição de entradas inválidas e campos que revelam o alvo.
- `python -m pip check`: sem dependências incompatíveis no ambiente final.
- Inferência de duas observações de exemplo concluída, com resultado em `reports/exemplo_predicoes.csv`.
- Inspeção visual dos cinco PNGs: textos e números legíveis, sem cortes relevantes.
- Após fixar SciPy 1.15.3 para eliminar aviso de compatibilidade do otimizador, o pipeline foi reexecutado. Modelo escolhido, limiar, AP do teste e matriz de confusão permaneceram iguais. Nenhum parâmetro de modelo foi ajustado com base no teste.

Resultado final: floresta aleatória, limiar 0,29, AP 0,64070349, recall 55/68 e precisão 55/122. TP=55, FP=67, FN=13 e TN=1.865.

## O que esta validação não cobre

Não foi executado Power BI Desktop: os arquivos M/DAX e o tema são material de integração. Não há `.pbix`. Os testes de agregação em Python não substituem teste das medidas no motor DAX.

O download real inicial foi realizado na fonte UCI e o CSV recebeu SHA-256 fixado. O teste automatizado do caminho sem cache usa uma resposta simulada contendo os mesmos bytes, sem exigir rede. Não houve avaliação prospectiva, validação em dados empresariais ou medição de efeito operacional.

O repositório público está em [Vict0r-13/falhas-industriais-ai4i](https://github.com/Vict0r-13/falhas-industriais-ai4i), com publicação pelo navegador autenticado. A preparação local original possui Git inicializado sem commit nem remote; para futuras alterações conectadas, use um clone do histórico publicado, conforme `docs/publicacao.md`. O ZIP exclui `.git`, ambientes virtuais, caches e modelos binários. Código, dados públicos, documentação, figuras e resultados permitem regenerar o modelo após instalar as dependências.

O empacotador `scripts/package.py` verifica o CRC do ZIP e compara os bytes de cada membro com o arquivo de origem. A cópia avulsa do README é idêntica à do projeto; seus links relativos funcionam dentro da pasta extraída.
