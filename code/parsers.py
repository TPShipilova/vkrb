"""Модуль парсинга Excel-файлов с данными об успеваемости."""
import pandas as pd
import numpy as np
import streamlit as st

def parse_grade_9_file(uploaded_file) -> pd.DataFrame:
    """Парсинг файла 9 класса (ОГЭ) - 5-балльная шкала"""
    try:
        df = pd.read_excel(uploaded_file, sheet_name=None)
        all_records = []

        for sheet_name, sheet_df in df.items():
            if sheet_df.empty:
                continue

            class_name = sheet_name.split()[0] if ' ' in sheet_name else sheet_name
            year = '2025' if '2025' in sheet_name else '2024'

            # Ищем столбцы
            name_col = None
            type_col = None
            for col in sheet_df.columns:
                if 'ФИО' in str(col):
                    name_col = col
                if 'Тип' in str(col):
                    type_col = col

            if name_col is None:
                continue

            current_student = None
            current_type = None
            student_data = {}

            for idx, row in sheet_df.iterrows():
                # Новый ученик
                if pd.notna(row[name_col]) and str(row[name_col]).strip() != '':
                    if current_student and student_data:
                        student_data['ФИО'] = current_student
                        student_data['Класс'] = class_name
                        student_data['Год'] = year
                        all_records.append(student_data)

                    current_student = str(row[name_col]).strip()
                    student_data = {}

                # Тип оценки
                if type_col and pd.notna(row.get(type_col)):
                    current_type = str(row.get(type_col)).strip()

                if current_student:
                    for col in sheet_df.columns:
                        if col in [name_col, type_col]:
                            continue

                        col_name = str(col).strip()
                        value = row[col]

                        if pd.isna(value) or col_name in ['Тип оценки', 'ФИО учащегося']:
                            continue

                        # Поиск предмета
                        subject_match = None
                        for subject in ['Русский язык', 'Математика', 'Физика', 'Обществознание',
                                        'Биология', 'Химия', 'Иностранный (английский) язык',
                                        'Информатика', 'История', 'Литература', 'География']:
                            if subject in col_name or col_name == subject:
                                subject_match = subject
                                break

                        if subject_match:
                            # ✅ ОГЭ в 5-балльной шкале (не конвертируем!)
                            if 'ОГЭ' in current_type:
                                try:
                                    oge_score = float(value)
                                    student_data[f'ОГЭ_{subject_match}'] = oge_score
                                    student_data[f'ОГЭ_{subject_match}_баллы'] = oge_score
                                except:
                                    pass
                            # Годовая оценка
                            elif 'Год' in current_type or 'Итог' in current_type:
                                if str(value).strip() not in ['зач', 'зачёт', '']:
                                    try:
                                        student_data[f'Год_{subject_match}'] = float(value)
                                    except:
                                        pass
                            # Триместр
                            elif 'триместр' in current_type:
                                trimester_num = current_type.split()[0] if ' ' in current_type else '1'
                                try:
                                    student_data[f'{trimester_num}_{subject_match}'] = float(value)
                                except:
                                    pass

            if current_student and student_data:
                student_data['ФИО'] = current_student
                student_data['Класс'] = class_name
                student_data['Год'] = year
                all_records.append(student_data)

        return pd.DataFrame(all_records)

    except Exception as e:
        st.error(f"Ошибка при обработке файла 9 класса: {str(e)}")
        return pd.DataFrame()


def parse_grade_11_file(uploaded_file) -> pd.DataFrame:
    """Парсинг файла 11 класса (ЕГЭ) - 100-балльная шкала"""
    try:
        df_sheets = pd.read_excel(uploaded_file, sheet_name=None)
        all_records = []

        # Список предметов для поиска
        SUBJECTS = [
            'Русский язык', 'Математика', 'Физика', 'Обществознание',
            'Биология', 'Химия', 'Иностранный (английский) язык',
            'Информатика', 'История', 'Литература', 'География'
        ]

        for sheet_name, sheet_df in df_sheets.items():
            if sheet_df.empty or len(sheet_df.columns) < 3:
                continue

            # Определяем класс и год из названия листа
            class_name = sheet_name.split()[0] if ' ' in sheet_name else sheet_name
            year = '2025' if '2025' in sheet_name else '2024'

            # Структура: Колонка 0=ФИО, 1=Класс, 2=Тип оценки, 3+=Предметы
            current_student = None
            student_data = {}

            for idx, row in sheet_df.iterrows():
                # Получаем ФИО (колонка 0)
                name_value = row.iloc[0] if len(row) > 0 else None

                # Если есть ФИО - это новый ученик
                if pd.notna(name_value) and str(name_value).strip() != '':
                    # Сохраняем предыдущего ученика
                    if current_student and student_data:
                        student_data['ФИО'] = current_student
                        student_data['Класс'] = class_name
                        student_data['Год'] = year
                        all_records.append(student_data)

                    current_student = str(name_value).strip()
                    student_data = {'ФИО': current_student}
                    continue

                # Если нет ФИО - продолжаем заполнять данные текущего ученика
                if not current_student:
                    continue

                # Получаем тип оценки (колонка 2)
                type_value = row.iloc[2] if len(row) > 2 else None
                if pd.isna(type_value):
                    continue

                type_str = str(type_value).strip()

                # ОБРАБОТКА СТРОКИ ЕГЭ
                if type_str == 'ЕГЭ':
                    for col_idx in range(3, len(row)):
                        col_name = str(sheet_df.columns[col_idx]).strip()
                        value = row.iloc[col_idx]

                        if pd.isna(value):
                            continue

                        # Ищем предмет в названии колонки
                        subject_match = None
                        for subject in SUBJECTS:
                            if subject in col_name or col_name == subject:
                                subject_match = subject
                                break

                        if subject_match:
                            try:
                                exam_score = float(value)
                                # ✅ Проверяем, что это балл ЕГЭ (0-100)
                                if 0 <= exam_score <= 100:
                                    student_data[f'ЕГЭ_{subject_match}_баллы'] = exam_score
                                    student_data[f'ЕГЭ_{subject_match}_оценка'] = round(exam_score / 20, 2)
                            except:
                                pass

                # ОБРАБОТКА ГОДОВЫХ ОЦЕНОК (10/11 класс)
                elif type_str == 'Год' or type_str == 'Год.оценка':
                    # Получаем класс из колонки 1
                    class_level = row.iloc[1] if len(row) > 1 else None

                    for col_idx in range(3, len(row)):
                        col_name = str(sheet_df.columns[col_idx]).strip()
                        value = row.iloc[col_idx]

                        if pd.isna(value):
                            continue

                        subject_match = None
                        for subject in SUBJECTS:
                            if subject in col_name or col_name == subject:
                                subject_match = subject
                                break

                        if subject_match:
                            try:
                                grade_val = float(value)
                                # Проверяем, что это школьная оценка (1-5)
                                if 1 <= grade_val <= 5:
                                    student_data[f'Год_{subject_match}'] = grade_val
                            except:
                                pass

                # ОБРАБОТКА ТРИМЕСТРОВ
                elif 'триместр' in type_str:
                    trimester_num = type_str.split()[0] if ' ' in type_str else '1'

                    for col_idx in range(3, len(row)):
                        col_name = str(sheet_df.columns[col_idx]).strip()
                        value = row.iloc[col_idx]

                        if pd.isna(value):
                            continue

                        subject_match = None
                        for subject in SUBJECTS:
                            if subject in col_name or col_name == subject:
                                subject_match = subject
                                break

                        if subject_match:
                            try:
                                grade_val = float(value)
                                if 1 <= grade_val <= 5:
                                    student_data[f'{trimester_num}_{subject_match}'] = grade_val
                            except:
                                pass

            # Сохраняем последнего ученика
            if current_student and student_data:
                student_data['ФИО'] = current_student
                student_data['Класс'] = class_name
                student_data['Год'] = year
                all_records.append(student_data)

        result_df = pd.DataFrame(all_records)

        # ОТЛАДКА
        if not result_df.empty:
            st.success(f"✅ Загружено {len(result_df)} учеников 11 класса")

            exam_cols = [col for col in result_df.columns if 'ЕГЭ' in col and '_баллы' in col]
            if exam_cols:
                st.write(f"📊 Найдено предметов с ЕГЭ: {len(exam_cols)}")
                for col in exam_cols[:5]:
                    filled = result_df[col].notna().sum()
                    st.write(f"  `{col}`: {filled} заполненных из {len(result_df)}")
            else:
                st.error("❌ Не найдены колонки с баллами ЕГЭ!")
                st.write(f"Все колонки: {list(result_df.columns)}")

        return result_df

    except Exception as e:
        st.error(f"❌ Ошибка при обработке файла 11 класса: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return pd.DataFrame()
