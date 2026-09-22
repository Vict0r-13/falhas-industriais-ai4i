let
    Fonte = LerCSV("predicoes_teste.csv"),
    Tipos = Table.TransformColumnTypes(Fonte, {
        {"UDI", Int64.Type}, {"Type", type text}, {"falha_real", Int64.Type},
        {"score_falha", type number}, {"alerta", Int64.Type},
        {"limiar", type number}, {"resultado", type text}
    }, "en-US")
in
    Tipos
