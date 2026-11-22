import pdfplumber
import pandas as pd
import numpy as np
import re


def validate_sigaa_pdf(pdf_file):
    try:
        with pdfplumber.open(pdf_file) as pdf_doc:
            if not pdf_doc.pages:
                return False, "O arquivo PDF enviado está vazio."

            first_page_text = pdf_doc.pages[0].extract_text() or ""

            if not re.search(r"\bSIGAA\b", first_page_text, re.IGNORECASE):
                return False, "O documento enviado não é proveniente do SIGAA."

            report_pattern = re.search(r"RELAT[ÓO]RIO\s+DE\s+NOTAS", first_page_text, re.IGNORECASE)
            if not report_pattern:
                return False, "O documento é do SIGAA, mas não é um 'Relatório de Notas' (pode ser atestado de matrícula ou comprovante de vínculo)."

            mandatory_columns = ["Código", "Disciplina", "Situação"]
            if not all(col in first_page_text for col in mandatory_columns):
                return False, "A estrutura de notas não foi identificada no documento."

            if not re.search(r"\b\d{4}\.\d\b", first_page_text):
                return False, "Nenhum período letivo válido foi encontrado no boletim."

            return True, ""

    except Exception as exc:
        return False, f"Arquivo corrompido ou formato inválido: {str(exc)}"


def extract_pdf_data(pdf_path):
    with pdfplumber.open(pdf_path) as pdf_doc:
        extracted_data = {}
        first_page_text = pdf_doc.pages[0].extract_text() or ""

        if not re.search(r"\bSIGAA\b", first_page_text, re.IGNORECASE):
            raise ValueError("O arquivo enviado não é um relatório de notas válido do SIGAA.")

        student_match = re.search(r"Aluno\(a\):\s*(.*?)\s*-\s*(\d+)", first_page_text)
        if student_match:
            extracted_data["nome"] = student_match.group(1).strip().title()
            extracted_data["matricula"] = student_match.group(2).strip()

        course_match = re.search(r"Curso:\s*(.+)", first_page_text)
        if course_match:
            extracted_data["curso"] = course_match.group(1).strip()

        issuance_match = re.search(r"Emitido\s+em\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})", first_page_text, re.IGNORECASE)
        if issuance_match:
            extracted_data["data_emissao"] = issuance_match.group(1).strip()
            extracted_data["hora_emissao"] = issuance_match.group(2).strip()

        all_periods = []

        for page in pdf_doc.pages:
            page_text = page.extract_text() or ""
            text_without_footer = re.split(r"Situação Final:|Indica que a unidade", page_text)[0]

            page_periods = [
                line.strip()
                for line in text_without_footer.split("\n")
                if re.fullmatch(r"\d{4}\.\d", line.strip())
            ]

            all_tables = page.extract_tables()

            for period, table in zip(page_periods, all_tables):
                period_df = pd.DataFrame(table[1:], columns=table[0])
                extracted_data[f"periodo_{period}"] = period_df
                all_periods.append(period)

        extracted_data["periodos"] = all_periods

    return extracted_data


def get_enrolled_subjects(pdf_data, default_target_average=5.0, min_default_units=3):
    records = []

    for period in pdf_data.get("periodos", []):
        period_key = f"periodo_{period}"

        if period_key not in pdf_data:
            continue

        raw_df = pdf_data[period_key]

        if "Situação" not in raw_df.columns:
            continue

        enrolled_filter = (
            raw_df["Situação"]
            .astype(str)
            .str.strip()
            .str.upper()
            .str.startswith("MATRICU")
        )

        filtered_df = raw_df[enrolled_filter].copy()

        if filtered_df.empty:
            continue

        unit_columns = [col for col in filtered_df.columns if col.startswith("Unid.")]

        filtered_df[unit_columns] = (
            filtered_df[unit_columns]
            .astype(str)
            .replace(",", ".", regex=True)
            .apply(pd.to_numeric, errors="coerce")
        )

        valid_marks = filtered_df[unit_columns].notna().sum(axis=1)
        total_units = valid_marks.apply(lambda quantity: max(quantity, min_default_units))

        filtered_df["Período"] = period
        filtered_df["Total Unid."] = total_units
        filtered_df["Média Alvo"] = default_target_average

        final_columns = ["Período", "Código", "Disciplina"] + unit_columns + ["Total Unid.", "Média Alvo"]
        records.append(filtered_df[final_columns])

    if not records:
        return pd.DataFrame(), {}

    consolidated_df = pd.concat(records, ignore_index=True)

    consolidated_unit_columns = [col for col in consolidated_df.columns if col.startswith("Unid.")]
    columns_to_remove = [
        col for col in consolidated_unit_columns
        if consolidated_df[col].isna().all()
    ]
    if columns_to_remove:
        consolidated_df = consolidated_df.drop(columns=columns_to_remove)

    active_unit_columns = [col for col in consolidated_df.columns if col.startswith("Unid.")]

    column_config = {
        "disabled_columns": ["Período", "Código", "Disciplina"] + active_unit_columns,
    }

    return consolidated_df, column_config

