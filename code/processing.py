"""Модуль агрегации и предобработки данных."""
import pandas as pd
import numpy as np


def calculate_student_average(df: pd.DataFrame, grade_prefix: str, exam_prefix: str = None) -> pd.DataFrame:
    """Расчет среднего балла по всем предметам для каждого ученика"""
    df = df.copy()

    grade_columns = [
        col for col in df.columns
        if col.startswith(f'{grade_prefix}_')
           and 'баллы' not in col
           and 'оценка' not in col
           and 'Средний' not in col
    ]

    if grade_columns:
        df['Средний балл'] = df[grade_columns].mean(axis=1, skipna=True)

    if exam_prefix:
        exam_columns = [
            col for col in df.columns
            if exam_prefix in col and '_баллы' in col
        ]

        if exam_columns:
            def calc_exam_avg(row):
                exam_scores = [row[col] for col in exam_columns if pd.notna(row.get(col))]
                return sum(exam_scores) / len(exam_scores) if exam_scores else np.nan

            df['Средний балл экзамена'] = df.apply(calc_exam_avg, axis=1)

    return df