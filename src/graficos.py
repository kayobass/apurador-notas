import pandas as pd
import plotly.graph_objects as go


def build_averages_figure(overall_df, period):
    period_df = overall_df[overall_df["Período"] == period].copy()

    if "Média Alvo" not in period_df.columns:
        period_df["Média Alvo"] = 5.0

    plot_marks = period_df["Resultado"].fillna(0.0)
    bar_labels = [
        f"{mark:.1f}" if pd.notna(mark) else "S/N"
        for mark in period_df["Resultado"]
    ]

    colours = [
        "#6c757d" if pd.isna(mark) else ("#2e9e5b" if mark >= target else "#e05252")
        for mark, target in zip(period_df["Resultado"], period_df["Média Alvo"])
    ]

    figure = go.Figure()

    figure.add_trace(go.Bar(
        x=period_df["Disciplina"],
        y=plot_marks,
        text=bar_labels,
        textposition="outside",
        marker_color=colours,
        name="Média",
        customdata=period_df["Média Alvo"],
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Média: %{text}<br>"
            "Média Alvo: %{customdata:.1f}<extra></extra>"
        )
    ))

    figure.add_trace(go.Scatter(
        x=period_df["Disciplina"],
        y=period_df["Média Alvo"],
        mode="markers",
        marker=dict(
            symbol="line-ew",
            size=45,
            line=dict(color="white", width=2.5)
        ),
        name="Média Alvo",
        hoverinfo="skip"
    ))

    figure.update_layout(
        yaxis=dict(
            title="Média",
            range=[0, 11],
            dtick=2,
            gridcolor="rgba(255, 255, 255, 0.1)"
        ),
        xaxis=dict(title=""),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20),
        height=400
    )

    return figure


def build_progression_figure(summary_df, current_partial_average=None, current_period=None):
    plot_df = summary_df.sort_values("Período").copy()
    completed_df = plot_df.dropna(subset=["Média"])

    figure = go.Figure()

    figure.add_trace(go.Scatter(
        x=completed_df["Período"],
        y=completed_df["Média"],
        mode="lines+markers+text",
        text=completed_df["Média"].apply(lambda val: f"{val:.2f}"),
        textposition="top center",
        line=dict(color="#2e9e5b", width=3),
        marker=dict(size=10),
        name="Média Final"
    ))

    if current_partial_average is not None and current_period is not None:
        figure.add_trace(go.Scatter(
            x=[current_period],
            y=[current_partial_average],
            mode="markers+text",
            text=[f"{current_partial_average:.2f} (Parcial)"],
            textposition="top center",
            marker=dict(size=12, color="#f0ad4e", symbol="diamond"),
            name="Em Andamento"
        ))

    figure.add_hline(
        y=5.0,
        line_dash="dot",
        line_color="rgba(255, 255, 255, 0.4)",
        annotation_text="Média 5.0",
        annotation_position="bottom right"
    )

    figure.update_layout(
        title="Evolução da Média Semestral",
        yaxis=dict(title="Média", range=[0, 11], dtick=2, gridcolor="rgba(255, 255, 255, 0.1)"),
        xaxis=dict(title="Período", type="category"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=50, b=20),
        height=380
    )

    return figure


def build_grade_distribution_figure(overall_df):
    marks = overall_df["Resultado"].dropna()

    grade_brackets = {
        "Abaixo de 5.0": int((marks < 5.0).sum()),
        "5.0 a 6.9 (Regular)": int(((marks >= 5.0) & (marks < 7.0)).sum()),
        "7.0 a 8.9 (Bom)": int(((marks >= 7.0) & (marks < 9.0)).sum()),
        "9.0 a 10.0 (Excelente)": int((marks >= 9.0).sum()),
    }

    labels = list(grade_brackets.keys())
    values = list(grade_brackets.values())
    colours = ["#e05252", "#f0ad4e", "#3b82f6", "#2e9e5b"]

    figure = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.5,
                marker=dict(colors=colours),
                textinfo="value+percent",
                hovertemplate="<b>%{label}</b><br>Disciplinas: %{value} (%{percent})<extra></extra>",
            )
        ]
    )

    figure.update_layout(
        title="Distribuição das Notas no Curso",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(l=20, r=20, t=50, b=40),
        height=380,
    )

    return figure
