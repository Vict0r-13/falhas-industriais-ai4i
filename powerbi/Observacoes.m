let
    Fonte = LerCSV("observacoes.csv"),
    Tipos = Table.TransformColumnTypes(Fonte, {
        {"UDI", Int64.Type}, {"Type", type text},
        {"Air temperature [K]", type number}, {"Process temperature [K]", type number},
        {"Rotational speed [rpm]", Int64.Type}, {"Torque [Nm]", type number},
        {"Tool wear [min]", Int64.Type}, {"falha_real", Int64.Type},
        {"conjunto", type text}, {"faixa_desgaste", type text}
    }, "en-US")
in
    Tipos
