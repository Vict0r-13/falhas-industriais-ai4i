(NomeArquivo as text) as table =>
let
    Fonte = Csv.Document(File.Contents(PastaDados & NomeArquivo), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Cabecalhos = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true])
in
    Cabecalhos
