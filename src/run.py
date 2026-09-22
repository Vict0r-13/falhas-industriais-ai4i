"""Execute com python -m src.run na raiz do projeto."""
import json
import platform
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
import scipy
from sklearn.inspection import permutation_importance
from sklearn.metrics import PrecisionRecallDisplay

from src.data import FEATURES, MODES, NUMERIC, ROOT, SEED, TARGET, acquire, split_data
from src.modeling import FN_COST, candidates, choose_threshold, metrics, threshold_table, wilson

COLORS = ["#247d93", "#e17543", "#17324d"]
LABELS = ["Temperatura do ar (K)", "Temperatura do processo (K)", "Rotação (rpm)", "Torque (Nm)", "Desgaste da ferramenta (min)"]


def save_json(path, content):
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def save_csv(frame, path):
    # UTF-8 BOM, vírgulas e ponto decimal: importar no Power BI com locale en-US.
    frame.to_csv(path, index=False, encoding="utf-8-sig", float_format="%.10g")


def save_figure(fig, directory, name):
    fig.savefig(directory / name, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def eda(train, figures, reports):
    """EDA orientada a modelagem restrita ao treino."""
    summary = train.groupby(TARGET)[NUMERIC].agg(["count", "mean", "median", "std"])
    summary.columns = [f"{col}__{stat}" for col, stat in summary.columns]
    save_csv(summary.reset_index(), reports / "eda_treino.csv")
    by_type = train.groupby("Type")[TARGET].agg(registros="size", falhas="sum").reset_index()
    by_type["taxa_falha"] = by_type.falhas / by_type.registros
    save_csv(by_type, reports / "eda_tipo_treino.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    counts = train[TARGET].value_counts().sort_index()
    axes[0].bar(["Sem falha", "Com falha"], counts, color=COLORS[:2])
    for x, count in enumerate(counts):
        axes[0].text(x, count, f"{count:,}".replace(",", "."), ha="center", va="bottom")
    axes[0].set(title="Distribuição do alvo", ylabel="Observações", ylim=(0, counts.max()*1.15))
    axes[1].bar(by_type.Type, 100*by_type.taxa_falha, color=COLORS[0])
    for x, row in by_type.iterrows():
        axes[1].text(x, 100*row.taxa_falha, f"{row.falhas}/{row.registros}", ha="center", va="bottom")
    axes[1].set(title="Falhas por variante de produto", ylabel="Observações com falha (%)", ylim=(0, by_type.taxa_falha.max()*125))
    fig.suptitle("Dados sintéticos • somente treino (6.000 observações)", fontsize=13)
    save_figure(fig, figures, "01_alvo_e_variantes.png")
    fig, axes = plt.subplots(2, 3, figsize=(12, 7), layout="constrained")
    for ax, col, label in zip(axes.flat, NUMERIC, LABELS):
        ax.boxplot([train.loc[train[TARGET] == v, col] for v in [0, 1]], tick_labels=["Sem falha", "Com falha"], showfliers=False)
        ax.set(title=label, ylabel=label.split("(")[-1].rstrip(")"))
    axes.flat[-1].axis("off")
    axes.flat[-1].text(0.05, 0.7, "Associações descritivas.\nNão demonstram causalidade.\n\nPontos extremos ocultos apenas\nno gráfico; nenhuma linha removida.", va="top", fontsize=11)
    fig.suptitle("Condições operacionais por rótulo • somente treino", fontsize=14)
    save_figure(fig, figures, "02_condicoes_operacionais.png")


def write_report(reports, quality, comparison, selected, final, sensitivity, importance):
    train_stats = pd.read_csv(reports / "eda_treino.csv").set_index(TARGET)
    torque_ok = train_stats.loc[0, "Torque [Nm]__median"]
    torque_fail = train_stats.loc[1, "Torque [Nm]__median"]
    speed_ok = train_stats.loc[0, "Rotational speed [rpm]__median"]
    speed_fail = train_stats.loc[1, "Rotational speed [rpm]__median"]
    lines = ["# Resultados calculados", "", "Gerado por `python -m src.run`. Dados sintéticos AI4I 2020, sem evidência de antecipação temporal ou ganho fabril.", "", "## Integridade e população", "",
             f"- {quality['registros']} observações; {quality['falhas']} falhas ({quality['taxa_falha']:.2%}).",
             f"- Ausências: {quality['ausencias']}; duplicatas nas seis entradas: {quality['entradas_duplicadas']}.",
             f"- Rótulo principal diferente do OR dos modos: {quality['divergencias_alvo_modos']} observações. Mantidas com o alvo original; ver `divergencias_rotulos.csv`.",
             "- EDA e importância calculadas, respectivamente, no treino e na validação. O teste permaneceu fora da seleção.", "", "## Achados exploratórios no treino", "",
             f"O torque mediano foi {torque_fail:.1f} Nm nas observações com falha e {torque_ok:.1f} Nm nas sem falha. A rotação mediana foi {speed_fail:.0f} rpm e {speed_ok:.0f} rpm, respectivamente. As distribuições se sobrepõem: nenhuma dessas diferenças cria uma regra determinística ou uma recomendação de ajuste do processo.", "",
             "A classe de falha é minoritária. Contagens e taxas por variante estão no gráfico abaixo; os grupos têm tamanhos diferentes, portanto volume de falhas e taxa de falhas respondem a perguntas distintas.", "", "![Alvo e variantes no treino](figures/01_alvo_e_variantes.png)", "", "## Comparação na validação", "",
             "| Modelo | AP | ROC AUC | Precisão (0,5) | Recall (0,5) |", "|---|---:|---:|---:|---:|"]
    for row in comparison.to_dict("records"):
        lines.append(f"| {row['modelo']} | {row['average_precision']:.4f} | {row['roc_auc']:.4f} | {row['precisao']:.2%} | {row['recall']:.2%} |")
    lines.extend(["", f"Selecionado: **{selected}**, por maior average precision (AP). AP é a média da precisão ponderada pelos incrementos de recall, sem interpolação trapezoidal.", "",
                  f"Limiar **{final['limiar']:.2f}** escolhido na validação para minimizar `FP + {FN_COST} × FN`; empates favorecem menos FP e depois maior limiar. Custo relativo hipotético, sem unidade monetária. O modelo foi mantido ajustado apenas no treino.", "", "## Avaliação final no teste", "",
                  f"Em {final['n']} observações, há {final['falhas']} falhas reais do conjunto sintético.", "",
                  f"- AP: **{final['average_precision']:.4f}**; ROC AUC: **{final['roc_auc']:.4f}**.",
                  f"- Recall: **{final['recall']:.2%}**; precisão dos alertas: **{final['precisao']:.2%}**; F2: **{final['f2']:.4f}**.",
                  f"- {final['tp']} falhas detectadas, {final['fn']} não detectadas, {final['fp']} falsos alarmes e {final['tn']} negativos corretos.",
                  f"- {final['alertas']} alertas ({final['alertas']/final['n']:.2%} das observações); custo relativo: {final['custo_relativo']}.",
                  f"- IC de Wilson 95% do recall: {final['recall_ic95'][0]:.2%} a {final['recall_ic95'][1]:.2%}; da precisão: {final['precisao_ic95'][0]:.2%} a {final['precisao_ic95'][1]:.2%}.",
                  "", "Os intervalos condicionam o modelo e o limiar já fixados e supõem observações independentes. Não incorporam escolha de modelo, variabilidade entre treinos nem dependência da geração sintética.",
                  "", "![Matriz de confusão](figures/04_matriz_confusao.png)", "", "![Precisão e recall](figures/03_precisao_recall.png)", "", "## Sensibilidade de custo (somente validação)", "",
                  "| Custo FN / FP | Limiar | FP | FN | Custo relativo |", "|---:|---:|---:|---:|---:|"])
    for row in sensitivity.to_dict("records"):
        lines.append(f"| {row['custo_fn']} | {row['limiar']:.2f} | {row['fp']} | {row['fn']} | {row['custo_relativo']} |")
    lines.extend(["", "Essa tabela discute políticas alternativas sem ajustar nada no teste. Para aplicação real, estimar custos e capacidade de inspeção com manutenção, operação e segurança.", "", "## Interpretação", "",
                  "As maiores quedas médias de AP após permutação na validação foram:"])
    for row in importance.head(3).to_dict("records"):
        lines.append(f"- {row['variavel']}: {row['queda_ap_media']:.4f} (desvio entre permutações: {row['desvio']:.4f}).")
    lines.extend(["", "Importância por permutação mede dependência do modelo, não efeito causal. Variáveis correlacionadas podem compartilhar importância. Os mecanismos sintéticos tornam parte das relações mais simples que em uma fábrica.", "", "![Condições](figures/02_condicoes_operacionais.png)", "", "## Limites", "",
                  "Não há data/hora, identificação de equipamento, duração de parada ou custos. UDI não é uma linha do tempo. O split aleatório avalia generalização dentro desta base sintética; as temperaturas foram geradas com dependência entre registros, o que pode tornar a estimativa otimista. Uma aplicação real exige validação por equipamento e tempo, horizonte de previsão definido, disponibilidade das variáveis antes da falha, revisão dos rótulos, calibração e monitoramento. Nenhum OEE, economia ou redução de parada foi medido.", "", "Fonte: [UCI AI4I 2020](https://doi.org/10.24432/C5HS5C), licença [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).", ""])
    (reports / "resultados.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    reports = ROOT / "reports"
    figures = reports / "figures"
    powerbi = ROOT / "powerbi/data"
    models_dir = ROOT / "models"
    for directory in [reports, figures, powerbi, models_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold"})
    frame = acquire()
    splits = split_data(frame)
    train, valid, test = [splits[k] for k in ["treino", "validacao", "teste"]]
    membership = pd.concat([part[["UDI"]].assign(conjunto=name) for name, part in splits.items()]).sort_values("UDI")
    save_csv(membership, reports / "particoes.csv")
    eda(train, figures, reports)

    fitted, comparisons, valid_scores = {}, [], {}
    for name, model in candidates().items():
        model.fit(train[FEATURES], train[TARGET])
        score = model.predict_proba(valid[FEATURES])[:, 1]
        fitted[name], valid_scores[name] = model, score
        comparisons.append({"modelo": name, "conjunto": "validacao", **metrics(valid[TARGET], score)})
    comparison = pd.DataFrame(comparisons).sort_values(["average_precision", "modelo"], ascending=[False, True])
    save_csv(comparison, reports / "comparacao_validacao.csv")
    selected = comparison.iloc[0]["modelo"]
    table = threshold_table(valid[TARGET], valid_scores[selected])
    choice = choose_threshold(table)
    threshold = float(choice["limiar"])
    save_csv(table, reports / "limiares_validacao.csv")
    sensitivity = []
    for cost in [1, 5, 10, 20]:
        row = choose_threshold(table, cost)
        sensitivity.append({"custo_fn": cost, "custo_fp": 1, "limiar": row["limiar"], "fp": int(row["fp"]), "fn": int(row["fn"]), "custo_relativo": int(cost*row["fn"] + row["fp"])})
    sensitivity = pd.DataFrame(sensitivity)
    save_csv(sensitivity, reports / "sensibilidade_validacao.csv")
    permutation = permutation_importance(fitted[selected], valid[FEATURES], valid[TARGET], scoring="average_precision", n_repeats=10, random_state=SEED, n_jobs=1)
    importance = pd.DataFrame({"variavel": FEATURES, "queda_ap_media": permutation.importances_mean, "desvio": permutation.importances_std}).sort_values("queda_ap_media", ascending=False)
    save_csv(importance, reports / "importancia_validacao.csv")
    # Trava auditável gravada ANTES de consultar predições/métricas do teste.
    selection = {"modelo": selected, "limiar": threshold, "criterio_modelo": "maior AP na validacao", "custo_fn": FN_COST, "custo_fp": 1, "seed": SEED, "features": FEATURES, "refit": False, "n_treino": len(train), "n_validacao": len(valid), "n_teste": len(test)}
    save_json(reports / "selecao.json", selection)
    joblib.dump({"pipeline": fitted[selected], "limiar": threshold, "features": FEATURES}, models_dir / "modelo.joblib")

    # Avaliação final: somente modelo escolhido e baseline. Nenhuma escolha abaixo.
    test_scores = fitted[selected].predict_proba(test[FEATURES])[:, 1]
    baseline_scores = fitted["baseline"].predict_proba(test[FEATURES])[:, 1]
    final = metrics(test[TARGET], test_scores, threshold)
    final["recall_ic95"] = wilson(final["tp"], final["tp"] + final["fn"])
    final["precisao_ic95"] = wilson(final["tp"], final["tp"] + final["fp"])
    baseline = metrics(test[TARGET], baseline_scores)
    save_json(reports / "metricas_teste.json", {"modelo": selected, "selecionado": final, "baseline": baseline})
    predictions = test[["UDI", "Type", TARGET]].rename(columns={TARGET: "falha_real"}).copy()
    predictions["score_falha"] = test_scores
    predictions["alerta"] = (test_scores >= threshold).astype(int)
    predictions["limiar"] = threshold
    predictions["resultado"] = np.select([(predictions.falha_real == 1) & (predictions.alerta == 1), (predictions.falha_real == 0) & (predictions.alerta == 1), (predictions.falha_real == 1) & (predictions.alerta == 0)], ["TP", "FP", "FN"], default="TN")
    save_csv(predictions.sort_values("UDI"), powerbi / "predicoes_teste.csv")
    save_csv(pd.DataFrame([{"modelo": selected, **{k:v for k,v in final.items() if not isinstance(v, list)}}, {"modelo": "baseline", **baseline}]), powerbi / "metricas_teste.csv")

    fig, ax = plt.subplots(figsize=(7.8, 5.3), layout="constrained")
    PrecisionRecallDisplay.from_predictions(test[TARGET], test_scores, name=selected, ax=ax, color=COLORS[0])
    ax.axhline(test[TARGET].mean(), color="gray", linestyle="--", label=f"Referência: prevalência {test[TARGET].mean():.1%}")
    ax.scatter(final["recall"], final["precisao"], color=COLORS[1], s=65, zorder=3, label=f"Limiar fixado: {threshold:.2f}")
    ax.set(title="Teste reservado • precisão e recall", xlabel="Recall (fração das falhas detectadas)", ylabel="Precisão (fração dos alertas corretos)")
    ax.legend(loc="lower left")
    save_figure(fig, figures, "03_precisao_recall.png")
    fig, ax = plt.subplots(figsize=(6.2, 4.7), layout="constrained")
    matrix = np.array([[final["tn"], final["fp"]], [final["fn"], final["tp"]]])
    ax.imshow(matrix, cmap="Blues")
    for (i, j), value in np.ndenumerate(matrix):
        ax.text(j, i, f"{['TN','FP','FN','TP'][2*i+j]}\n{value}", ha="center", va="center", fontsize=18, color="white" if value > matrix.max()/2 else COLORS[2])
    ax.set(xticks=[0,1], yticks=[0,1], xticklabels=["Sem alerta", "Alerta"], yticklabels=["Sem falha", "Com falha"], xlabel="Classificação", ylabel="Rótulo observado", title=f"Teste: {len(test):,} observações • limiar {threshold:.2f}".replace(",", "."))
    save_figure(fig, figures, "04_matriz_confusao.png")
    fig, ax = plt.subplots(figsize=(8.5, 4.5), layout="constrained")
    shown = importance.sort_values("queda_ap_media")
    ax.barh(shown.variavel, shown.queda_ap_media, xerr=shown.desvio, color=COLORS[0])
    ax.axvline(0, color="gray", linewidth=0.8)
    ax.set(title="Dependência do modelo • somente validação", xlabel="Queda de AP após permutação (média e desvio de 10 repetições)")
    save_figure(fig, figures, "05_importancia.png")

    # Descrição da base completa só após escolhas e teste, para contextualizar o painel.
    divergence = frame[TARGET] != frame[MODES].max(axis=1)
    quality = {"registros": len(frame), "falhas": int(frame[TARGET].sum()), "taxa_falha": float(frame[TARGET].mean()), "ausencias": int(frame.isna().sum().sum()), "entradas_duplicadas": int(frame.duplicated(FEATURES).sum()), "divergencias_alvo_modos": int(divergence.sum())}
    save_json(reports / "qualidade.json", quality)
    save_csv(frame.loc[divergence, ["UDI", TARGET, *MODES]], reports / "divergencias_rotulos.csv")
    observations = frame[["UDI", *FEATURES, TARGET]].merge(membership, on="UDI", validate="one_to_one").rename(columns={TARGET: "falha_real"})
    observations["faixa_desgaste"] = pd.cut(observations["Tool wear [min]"], [-1, 99, 199, np.inf], labels=["0-99 min", "100-199 min", "200+ min"])
    save_csv(observations, powerbi / "observacoes.csv")
    aggregate = observations.groupby(["conjunto", "Type", "faixa_desgaste"], observed=True).agg(registros=("UDI", "size"), falhas=("falha_real", "sum")).reset_index()
    aggregate["taxa_falha"] = aggregate.falhas / aggregate.registros
    save_csv(aggregate, powerbi / "resumo_condicoes.csv")
    save_csv(sensitivity, powerbi / "sensibilidade_validacao.csv")
    save_json(reports / "ambiente.json", {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "scikit_learn": sklearn.__version__, "scipy": scipy.__version__, "matplotlib": matplotlib.__version__, "joblib": joblib.__version__})
    write_report(reports, quality, comparison, selected, final, sensitivity, importance)
    print(json.dumps({"modelo": selected, "limiar": threshold, "teste": final, "qualidade": quality}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
