"""Математическая модель: дескриптивная статистика, корреляция, Z-оценки."""
import pandas as pd
import numpy as np
from scipy import stats

class StatisticsCalculator:
    """Калькулятор статистик на основе математической модели ВКР"""
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def calculate_descriptive_stats(self, grade_column: str = 'Средний балл') -> dict:
        """Дескриптивная статистика (п. 2.3.1 ВКР)"""
        if grade_column not in self.df.columns:
            return {}

        values = self.df[grade_column].dropna()
        if len(values) == 0:
            return {}

        mean = values.mean()
        variance = values.var()
        std_dev = values.std()
        mode = values.mode().iloc[0] if len(values.mode()) > 0 else None
        median = values.median()

        quality_count = len(values[values >= 4])
        quality_coeff = quality_count / len(values) if len(values) > 0 else 0

        success_count = len(values[values >= 3])
        success_rate = success_count / len(values) if len(values) > 0 else 0

        return {
            'Средний балл': round(mean, 2),
            'Медиана': round(median, 2),
            'Мода': round(mode, 2) if mode else None,
            'Стандартное отклонение': round(std_dev, 2),
            'Качество знаний (%)': round(quality_coeff * 100, 1),
            'Успеваемость (%)': round(success_rate * 100, 1),
            'Количество учеников': len(values)
        }

    def calculate_spearman_correlation(self, col1: str, col2: str) -> dict:
        """Коэффициент ранговой корреляции Спирмена (п. 2.3.2 ВКР)"""
        if col1 not in self.df.columns or col2 not in self.df.columns:
            return {'rho': None, 'p_value': None, 'interpretation': 'Нет данных'}

        mask = self.df[col1].notna() & self.df[col2].notna()
        data = self.df[mask]

        if len(data) < 3:
            return {'rho': None, 'p_value': None, 'interpretation': 'Недостаточно данных'}

        try:
            rho, p_value = stats.spearmanr(data[col1], data[col2])

            if rho >= 0.7:
                interpretation = 'Сильная положительная связь'
            elif rho >= 0.4:
                interpretation = 'Умеренная положительная связь'
            elif rho >= 0:
                interpretation = 'Слабая связь'
            else:
                interpretation = 'Отрицательная связь (требует внимания)'

            return {
                'rho': round(rho, 3),
                'p_value': round(p_value, 4),
                'interpretation': interpretation,
                'n': len(data)
            }
        except Exception as e:
            return {'rho': None, 'p_value': None, 'interpretation': f'Ошибка: {str(e)}'}

    def calculate_z_scores(self, grade_column: str, exam_column: str) -> pd.DataFrame:
        """Расчет Z-оценок для выявления расхождений (п. 2.3.3 ВКР)"""
        df = self.df.copy()
        if grade_column not in df.columns or exam_column not in df.columns:
            return df

        mean_grade = df[grade_column].mean()
        std_grade = df[grade_column].std()
        df['Z_текущая'] = (df[grade_column] - mean_grade) / std_grade if std_grade > 0 else 0

        mean_exam = df[exam_column].mean()
        std_exam = df[exam_column].std()
        df['Z_экзамен'] = (df[exam_column] - mean_exam) / std_exam if std_exam > 0 else 0

        df['Расхождение (D)'] = df['Z_экзамен'] - df['Z_текущая']
        return df

    def get_discrepancy_students(self, threshold: float = 1.0) -> pd.DataFrame:
        """Выявление учеников с расхождениями (п. 2.3.3.3 ВКР)"""
        if 'Расхождение (D)' not in self.df.columns:
            return pd.DataFrame()

        discrepancies = self.df[abs(self.df['Расхождение (D)']) > threshold].copy()
        if len(discrepancies) > 0:
            discrepancies['Тип расхождения'] = discrepancies['Расхождение (D)'].apply(
                lambda x: 'Выше ожидаемого' if x > 0 else 'Ниже ожидаемого'
            )
        return discrepancies