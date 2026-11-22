import pandas as pd
import streamlit as st

from src.extrator import extract_pdf_data, validate_sigaa_pdf, get_enrolled_subjects
from src.graficos import (
    build_averages_figure,
    build_progression_figure,
    build_grade_distribution_figure,
)
from src.processador import (
    is_period_in_progress,
    calculate_general_metrics,
    get_passing_requirements,
    prepare_complete_data,
    summarise_periods,
)

st.set_page_config(page_title="Apurador de Notas: UFS", page_icon="🎓", layout="wide")
st.title("🎓 Apurador de Notas: UFS")

uploaded_file = st.file_uploader("Envie seu Relatório de Notas (PDF)", type=["pdf"])


if uploaded_file is not None:
    is_valid, error_message = validate_sigaa_pdf(uploaded_file)

    if not is_valid:
        st.error(f"⚠️ Documento incompatível: {error_message}")
        st.stop()

    try:
        with st.spinner("Extraindo tabelas do boletim..."):
            pdf_data = extract_pdf_data(uploaded_file)

            if not pdf_data.get("periodos"):
                st.warning("Nenhum dado de disciplina pôde ser extraído deste relatório.")
                st.stop()

            st.divider()
            col_student, col_course, col_id, col_issued = st.columns([2.2, 2.2, 1.3, 1.3])
            col_student.metric("Aluno(a)", (pdf_data["nome"] or "—").title())
            col_course.metric("Curso", (pdf_data["curso"] or "—").title())
            col_id.metric("Matrícula", pdf_data["matricula"] or "—")
            col_issued.metric("Emitido em", f"{pdf_data['data_emissao']} {pdf_data['hora_emissao']}" if pdf_data.get("data_emissao") else "—")
            st.divider()

            academic_periods = list(pdf_data["periodos"])

            current_semester = academic_periods[0]
            previous_semesters = academic_periods[1:]

            st.header("📋 Notas por período")

            enrolled_df, rules_config = get_enrolled_subjects(pdf_data)
            settings_df = pd.DataFrame()
            requirements_df = pd.DataFrame()

            if not enrolled_df.empty:
                column_configs = {}

                for col in rules_config.get("disabled_columns", []):
                    if col.startswith("Unid."):
                        column_configs[col] = st.column_config.NumberColumn(col, disabled=True, format="%.1f")
                    else:
                        column_configs[col] = st.column_config.Column(col, disabled=True)

                column_configs["Total Unid."] = st.column_config.NumberColumn(
                    "Total Unid. ✏️",
                    min_value=1,
                    max_value=10,
                    step=1,
                    required=True
                )
                column_configs["Média Alvo"] = st.column_config.NumberColumn(
                    "Média Alvo ✏️",
                    min_value=0.0,
                    max_value=10.0,
                    step=0.5,
                    format="%.1f",
                    required=True
                )

                with st.expander("⚙️ Unidades e médias das disciplinas em andamento", expanded=False):
                    settings_df = st.data_editor(
                        enrolled_df,
                        column_config=column_configs,
                        column_order=["Período", "Código", "Disciplina", "Total Unid.", "Média Alvo"],
                        width="stretch",
                        hide_index=True,
                        key="editor_enrolled",
                    )

            if settings_df.empty and not enrolled_df.empty:
                settings_df = enrolled_df

            period_dfs, overall_df = prepare_complete_data(pdf_data, settings_df, default_target_average=5.0)

            with st.expander(f"{current_semester}", expanded=True):
                st.dataframe(period_dfs[current_semester], width="stretch", hide_index=True)
                if is_period_in_progress(pdf_data, current_semester):
                    st.caption("Em disciplinas em andamento, Média é a média parcial (ponderada) das unidades já lançadas.")

            for semester in previous_semesters:
                with st.expander(f"{semester}", expanded=False):
                    st.dataframe(period_dfs[semester], width="stretch", hide_index=True)

            if not settings_df.empty:
                st.divider()
                st.header("🎯 Quanto falta para passar")

                requirements_df = get_passing_requirements(settings_df)
                st.dataframe(
                    requirements_df,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Média parcial": st.column_config.NumberColumn("Média parcial", format="%.2f"),
                        "Pontos que faltam": st.column_config.NumberColumn("Pontos que faltam", format="%.1f"),
                        "Nota necessária nas restantes": st.column_config.NumberColumn("Nota necessária nas restantes", format="%.2f"),
                        "Máx. possível": st.column_config.NumberColumn("Máx. possível", format="%.2f"),
                    }
                )

        st.divider()
        st.header("📁 Resumo")

        general_metrics = calculate_general_metrics(pdf_data, requirements_df)
        summary_df = summarise_periods(pdf_data, settings_df)

        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        metric_col1.metric(
            "Média geral (disciplinas concluídas)",
            f"{general_metrics['overall_average']:.2f}" if general_metrics["overall_average"] is not None else "—"
        )
        metric_col2.metric(
            "Média parcial (em andamento)",
            f"{general_metrics['partial_average']:.2f}" if general_metrics["partial_average"] is not None else "—"
        )
        metric_col3.metric("Disciplinas concluídas", general_metrics["completed_count"])
        metric_col4.metric("Em andamento", general_metrics["in_progress_count"])

        st.dataframe(
            summary_df.sort_values("Período", ascending=False),
            width="stretch",
            hide_index=True,
            column_config={
                "Média": st.column_config.NumberColumn("Média final", format="%.2f")
            }
        )

        st.caption("A média geral é a média simples dos resultados finais (sem ponderar por carga horária/créditos).")

        st.divider()
        st.header("📊 Desempenho")

        selected_period = st.selectbox(
            "Selecione o período para visualizar:",
            options=academic_periods,
            index=0
        )

        averages_fig = build_averages_figure(overall_df, selected_period)
        st.plotly_chart(averages_fig, width="stretch")

        st.divider()

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            active_period = current_semester if is_period_in_progress(pdf_data, current_semester) else None
            progression_fig = build_progression_figure(summary_df, general_metrics["partial_average"], active_period)
            st.plotly_chart(progression_fig, width="stretch")

        with chart_col2:
            distribution_fig = build_grade_distribution_figure(overall_df)
            st.plotly_chart(distribution_fig, width="stretch")

    except Exception as error:
        st.error(f"Ocorreu um erro inesperado ao extrair os dados: {error}")
