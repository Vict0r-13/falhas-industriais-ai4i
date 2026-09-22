# Repositório público e atualizações

Endereço: **[Vict0r-13/falhas-industriais-ai4i](https://github.com/Vict0r-13/falhas-industriais-ai4i)**.

O repositório público foi criado na conta Vict0r-13 após verificar a identidade autenticada e a disponibilidade do nome. A publicação usa os arquivos distribuíveis do projeto: código, testes, documentação, resultados, gráficos, kit Power BI e dados públicos com atribuição. Ambientes virtuais, caches, credenciais, modelos binários e arquivos de outros projetos ficam fora do envio.

## Atualizar a partir de uma cópia conectada ao GitHub

Para trabalhar no histórico publicado, clone o repositório em uma pasta nova. A pasta usada na preparação inicial possui Git inicializado sem histórico remoto; não force um push dessa pasta sobre o repositório publicado.

```powershell
git clone https://github.com/Vict0r-13/falhas-industriais-ai4i.git
cd falhas-industriais-ai4i
git status --short
```

Instale as dependências e execute o projeto conforme o README apenas quando precisar reproduzir ou desenvolver a análise. Para enviar alterações futuras, autentique o Git pelo fluxo oficial disponível no computador, configure sua identidade de commit e revise o diff antes do envio. Não coloque senha ou token em arquivos, URLs ou mensagens.

Depois de modificar arquivos dentro do escopo desejado:

```powershell
git diff
git add README.md docs
git diff --cached --stat
git commit -m "Atualiza documentacao do estudo industrial"
git push origin main
```

Adapte a lista de arquivos ao que realmente foi alterado. Nunca use `--force` para substituir trabalho remoto. Preserve `.gitignore` e `.gitattributes`: o CSV original precisa manter os bytes usados no SHA-256.

## Conferir e distribuir

Na página pública, confira README, imagens, scripts, resultados, fonte/licença e kit Power BI. O modelo `.joblib` é regenerado localmente. O material Power BI continua sendo um kit, sem arquivo `.pbix`.

O ZIP portátil e a cópia avulsa do README podem ser atualizados com `python scripts/package.py CAMINHO_DA_PASTA_DE_ENTREGA`. O empacotador seleciona os arquivos permitidos e verifica a integridade. Os links relativos do README avulso funcionam dentro da pasta extraída.

Tópicos do projeto: `data-science`, `machine-learning`, `industrial-analytics`, `python`, `scikit-learn`, `power-bi`.

Esta publicação abrange somente este repositório. Não inclui alterações no perfil ou nos demais projetos, dados empresariais ou alegações de ganho fabril medido.
