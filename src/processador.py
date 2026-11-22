import pandas as pd
import numpy as np


def clean_semester_report(semester_df):
    cleaned_df = semester_df.copy()

    mark_columns = [col for col in cleaned_df.columns if col.startswith("Unid.") or col == "Resultado"]

    if mark_columns:
        cleaned_df[mark_columns] = (
            cleaned_df[mark_columns]
            .astype(str)
            .replace(",", ".", regex=True)
            .apply(pd.to_numeric, errors="coerce")
        )

    if "Faltas" in cleaned_df.columns:
        cleaned_df["Faltas"] = pd.to_numeric(cleaned_df["Faltas"], errors="coerce").fillna(0).astype(int)

    unit_columns = [col for col in cleaned_df.columns if col.startswith("Unid.")]
    empty_columns = [col for col in unit_columns if cleaned_df[col].isna().all()]

    if empty_columns:
        cleaned_df = cleaned_df.drop(columns=empty_columns)

    return cleaned_df


def is_period_in_progress(pdf_data: dict, period: str) -> bool:
    period_key = f"periodo_{period}"
    period_df = pdf_data.get(period_key)

    if period_df is None or period_df.empty or "Situação" not in period_df.columns:
        return False

    in_progress = (
        period_df["Situação"]
        .astype(str)
        .str.strip()
        .str.upper()
        .str.startswith("MATRICU")
        .any()
    )

    return bool(in_progress)


def apply_period_settings(period_df, settings_df, period):
    final_df = period_df.copy()

    if settings_df is None or settings_df.empty:
        return final_df

    period_settings = settings_df[settings_df["Período"] == period][
        ["Código", "Total Unid.", "Média Alvo"]
    ]

    if period_settings.empty:
        return final_df

    final_df = final_df.merge(period_settings, on="Código", how="left")

    unit_columns = [col for col in final_df.columns if col.startswith("Unid.")]

    in_progress_mask = final_df["Total Unid."].notna()

    if in_progress_mask.any():
        mark_sum = final_df.loc[in_progress_mask, unit_columns].sum(axis=1)
        completed_units = final_df.loc[in_progress_mask, unit_columns].notna().sum(axis=1)

        result_column = "Resultado"
        partial_average = np.where(completed_units > 0, np.round(mark_sum / completed_units, 2), np.nan)
        final_df.loc[in_progress_mask, result_column] = partial_average

    final_df = final_df.drop(columns=["Total Unid.", "Média Alvo"])

    return final_df


def get_passing_requirements(settings_df):
    if settings_df is None or settings_df.empty:
        return pd.DataFrame()

    source_df = settings_df.copy()
    unit_columns = [col for col in source_df.columns if col.startswith("Unid.")]

    if unit_columns:
        numeric_marks = source_df[unit_columns].apply(
            lambda col: pd.to_numeric(
                col.astype(str).str.replace(",", ".", regex=False).str.strip(),
                errors="coerce"
            )
        )
        current_total_marks = numeric_marks.sum(axis=1)
        completed_units = numeric_marks.notna().sum(axis=1)
    else:
        current_total_marks = pd.Series(0.0, index=source_df.index)
        completed_units = pd.Series(0, index=source_df.index)

    total_units = pd.to_numeric(source_df["Total Unid."], errors="coerce").fillna(3).astype(int)
    target_average = pd.to_numeric(source_df["Média Alvo"], errors="coerce").fillna(5.0).astype(float)

    remaining_units = (total_units - completed_units).clip(lower=0)
    submitted_units_text = completed_units.astype(str) + "/" + total_units.astype(str)

    partial_average = np.where(
        completed_units > 0,
        np.round(current_total_marks / completed_units, 2),
        np.nan
    )

    required_points = target_average * total_units
    remaining_points = (required_points - current_total_marks).clip(lower=0).round(1)

    required_mark_per_remaining_unit = np.where(
        remaining_units > 0,
        np.round(remaining_points / remaining_units, 2),
        0.0
    )

    maximum_achievable_average = np.round((current_total_marks + (remaining_units * 10.0)) / total_units, 2)

    return pd.DataFrame({
        "Período": source_df["Período"],
        "Disciplina": source_df["Disciplina"],
        "Unid. lançadas": submitted_units_text,
        "Média parcial": partial_average,
        "Pontos que faltam": remaining_points,
        "Nota necessária nas restantes": required_mark_per_remaining_unit,
        "Máx. possível": maximum_achievable_average
    })


def prepare_complete_data(pdf_data, settings_df, default_target_average=5.0):
    period_dfs = {}
    all_period_records = []

    for period in pdf_data.get("periodos", []):
        cleaned_df = clean_semester_report(pdf_data[f"periodo_{period}"].copy())
        processed_df = apply_period_settings(cleaned_df, settings_df, period)

        period_dfs[period] = processed_df

        temp_df = processed_df.copy()
        temp_df["Período"] = period
        all_period_records.append(temp_df)

    if not all_period_records:
        return period_dfs, pd.DataFrame()

    overall_df = pd.concat(all_period_records, ignore_index=True)

    if settings_df is not None and not settings_df.empty:
        target_settings = settings_df[["Período", "Código", "Média Alvo"]]
        overall_df = overall_df.merge(target_settings, on=["Período", "Código"], how="left")
    else:
        overall_df["Média Alvo"] = np.nan

    overall_df["Média Alvo"] = overall_df["Média Alvo"].fillna(default_target_average)

    overall_df["Resultado"] = pd.to_numeric(
        overall_df["Resultado"].astype(str).str.replace(",", ".", regex=False),
        errors="coerce"
    )

    return period_dfs, overall_df


def summarise_periods(pdf_data, settings_df):
    summary_dict = {}

    for period in pdf_data.get("periodos", []):
        cleaned_period_df = clean_semester_report(pdf_data[f"periodo_{period}"].copy())
        processed_period_df = apply_period_settings(cleaned_period_df, settings_df, period)

        subject_count = int(processed_period_df["Código"].nunique())
        absence_count = int(pd.to_numeric(processed_period_df["Faltas"], errors="coerce").fillna(0).sum())

        status_series = processed_period_df["Situação"].astype(str).str.strip().str.upper()
        passed_count = int(status_series.str.startswith("AP").sum())
        failed_count = int(status_series.str.startswith("RE").sum())
        in_progress_count = int(status_series.str.startswith("MATRICU").sum())

        if is_period_in_progress(pdf_data, period):
            final_average = None
        else:
            result_series = pd.to_numeric(processed_period_df["Resultado"], errors="coerce")
            final_average = round(float(result_series.mean()), 2) if result_series.notna().any() else None

        summary_dict[period] = {
            "Disciplinas": subject_count,
            "Média": final_average,
            "Aprovadas": passed_count,
            "Reprovadas": failed_count,
            "Em Andamento": in_progress_count,
            "Faltas": absence_count,
        }

    summary_df = pd.DataFrame.from_dict(summary_dict, orient="index")
    summary_df.index.name = "Período"

    return summary_df.reset_index()


def calculate_general_metrics(pdf_data, requirements_df=None):
    completed_results = []
    completed_count = 0

    for period in pdf_data.get("periodos", []):
        cleaned_df = clean_semester_report(pdf_data[f"periodo_{period}"].copy())
        status_series = cleaned_df["Situação"].astype(str).str.strip().str.upper()

        completed_filter = status_series.str.startswith(("AP", "RE"))
        completed_count += int(completed_filter.sum())

        numeric_results = pd.to_numeric(cleaned_df.loc[completed_filter, "Resultado"], errors="coerce").dropna()
        completed_results.extend(numeric_results.tolist())

    overall_average = round(sum(completed_results) / len(completed_results), 2) if completed_results else None

    if requirements_df is not None and not requirements_df.empty:
        in_progress_count = len(requirements_df)
        partial_averages = pd.to_numeric(requirements_df["Média parcial"], errors="coerce").dropna()
        partial_average = round(float(partial_averages.mean()), 2) if not partial_averages.empty else None
    else:
        in_progress_count = 0
        partial_average = None

    return {
        "media_geral": overall_average,
        "media_parcial": partial_average,
        "concluidas": completed_count,
        "em_andamento": in_progress_count,
        "overall_average": overall_average,
        "partial_average": partial_average,
        "completed_count": completed_count,
        "in_progress_count": in_progress_count,
    }
