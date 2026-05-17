"""Пользовательский интерфейс Streamlit."""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from config import ANALYSIS_SUBJECTS
from parsers import parse_grade_9_file, parse_grade_11_file
from processing import calculate_student_average
from statistics import StatisticsCalculator
from visualizations import (create_class_statistics_chart, create_correlation_scatter,
                            create_discrepancy_chart, create_subject_dynamics_chart)


def run_app():
    st.title("📊 Школьная Аналитика")
    st.markdown("""
    Система сопоставительного анализа результатов промежуточного и итогового контроля
    *На основе математической модели ВКР (дескриптивная статистика, корреляция Спирмена, Z-оценки)*
    """)

    # === БОКОВАЯ ПАНЕЛЬ ===
    st.sidebar.header("⚙️ Настройки")
    grade_level = st.sidebar.selectbox("Класс", options=["9 класс (ОГЭ)", "11 класс (ЕГЭ)"],
                                       help="Выберите класс для анализа")

    st.sidebar.subheader("📁 Загрузка данных")
    uploaded_file_1 = st.sidebar.file_uploader("Файл 2024-2025 год (.xlsx)", type=['xlsx'], key="file1")
    uploaded_file_2 = st.sidebar.file_uploader("Файл для сравнения (опционально)", type=['xlsx'], key="file2",
                                               help="Загрузите второй файл для сравнения по годам")

    discrepancy_threshold = st.sidebar.slider("Порог расхождений (D)", min_value=0.5, max_value=2.0, value=1.0,
                                              step=0.1, help="Значение D > порога считается значимым расхождением")

    if uploaded_file_1 is None:
        st.info("👈 Загрузите файл с данными в боковой панели для начала работы")
        return

    # === ОБРАБОТКА ДАННЫХ ===
    with st.spinner("Обработка данных..."):
        if "9 класс" in grade_level:
            df_1 = parse_grade_9_file(uploaded_file_1)
            exam_prefix = "ОГЭ"
            grade_prefix = "Год"
        else:
            df_1 = parse_grade_11_file(uploaded_file_1)
            exam_prefix = "ЕГЭ"
            grade_prefix = "Год"

        if df_1.empty:
            st.error("Не удалось обработать файл. Проверьте формат данных.")
            return

        df_1 = calculate_student_average(df_1, grade_prefix, exam_prefix)

        if uploaded_file_2:
            df_2 = parse_grade_9_file(uploaded_file_2) if "9 класс" in grade_level else parse_grade_11_file(
                uploaded_file_2)
            if not df_2.empty:
                df_2 = calculate_student_average(df_2, grade_prefix)
                df_1['Год'] = '2024-2025'
                df_2['Год'] = '2023-2024'
                combined_df = pd.concat([df_1, df_2], ignore_index=True)
                st.success(f"Данные за 2 года объединены: {len(combined_df)} записей")
            else:
                combined_df = df_1.copy()
                df_1['Год'] = '2024-2025'
        else:
            combined_df = df_1.copy()
            df_1['Год'] = '2024-2025'

        if 'Средний балл' not in combined_df.columns:
            st.error("Не удалось рассчитать средний балл. Проверьте данные в файле.")
            st.stop()

    # === ВКЛАДКИ ===
    tab1, tab2, tab3 = st.tabs(["📈 Статистика по классу", "👤 Ученик", "⚠️ Расхождения"])

    # === ВКЛАДКА 1: СТАТИСТИКА ===
    with tab1:
        st.header("Статистика по классу")

        available_classes = sorted(combined_df['Класс'].unique())
        selected_class = st.selectbox("Выберите класс", available_classes)

        class_data = combined_df[combined_df['Класс'] == selected_class].copy()

        if len(class_data) == 0:
            st.warning("Нет данных для выбранного класса")
            return

        calculator = StatisticsCalculator(class_data)

        # Дескриптивная статистика
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Количество учеников", len(class_data))

        with col2:
            if 'Средний балл' in class_data.columns:
                avg_grade = class_data['Средний балл'].mean()
                if pd.notna(avg_grade):
                    st.metric("Средний балл класса", f"{avg_grade:.2f}")

        with col3:
            if 'Средний балл' in class_data.columns:
                quality = len(class_data[class_data['Средний балл'] >= 4]) / len(class_data) * 100
                st.metric("Качество знаний", f"{quality:.1f}%")

        # Подробная дескриптивная статистика
        st.subheader("📊 Дескриптивная статистика")

        desc_stats = calculator.calculate_descriptive_stats('Средний балл')

        if desc_stats:
            stats_df = pd.DataFrame(list(desc_stats.items()), columns=['Показатель', 'Значение'])
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
        else:
            st.warning("Не удалось рассчитать статистику")

        # График распределения
        st.subheader("📈 Распределение оценок")

        chart = create_class_statistics_chart(class_data, 'Средний балл')
        if chart:
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.info("Нет данных для построения графика")

        # Средний балл за экзамен (только по сданным предметам)
        st.subheader("📝 Средний балл за экзамен")

        exam_score_cols = [col for col in class_data.columns if exam_prefix in col and '_баллы' in col]

        if exam_score_cols:
            # Расчет среднего по фактически сданным экзаменам
            def calc_student_exam_avg(row):
                scores = [row[col] for col in exam_score_cols if pd.notna(row.get(col))]
                if len(scores) > 0:
                    return sum(scores) / len(scores)
                return np.nan

            class_data['Средний ЕГЭ'] = class_data.apply(calc_student_exam_avg, axis=1)

            exam_avg = class_data['Средний ЕГЭ'].mean()
            if pd.notna(exam_avg):
                st.metric(f"Средний балл за {exam_prefix} (по сданным предметам)", f"{exam_avg:.1f}")

            # График распределения средних баллов за экзамен
            exam_avg_data = class_data.dropna(subset=['Средний ЕГЭ']).copy()

            if len(exam_avg_data) > 0:
                try:
                    import plotly.graph_objects as go

                    exam_avg_chart = go.Figure(data=[
                        go.Histogram(
                            x=exam_avg_data['Средний ЕГЭ'],
                            nbinsx=10,
                            marker_color='#EF553B',
                            opacity=0.75
                        )
                    ])

                    exam_avg_chart.update_layout(
                        title=f'Распределение средних баллов за {exam_prefix}',
                        xaxis_title='Средний балл',
                        yaxis_title='Количество учеников',
                        height=400,
                        showlegend=False
                    )

                    st.plotly_chart(exam_avg_chart, use_container_width=True)
                except Exception as e:
                    st.warning(f"Не удалось построить график: {str(e)}")

        # Сравнение по годам (если есть)
        if 'Год' in class_data.columns and class_data['Год'].nunique() > 1:
            st.subheader("📅 Сравнение по годам")

            if 'Средний балл' in class_data.columns:
                year_comparison = class_data.groupby('Год')['Средний балл'].agg(['mean', 'std', 'count']).round(2)
                st.dataframe(year_comparison, use_container_width=True)

                try:
                    import plotly.express as px
                    fig = px.box(
                        class_data,
                        x='Год',
                        y='Средний балл',
                        title='Сравнение успеваемости по годам',
                        labels={'Средний балл': 'Средний балл', 'Год': 'Учебный год'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.warning(f"Не удалось построить график: {str(e)}")
                    try:
                        import plotly.graph_objects as go
                        years = class_data['Год'].unique()
                        fig = go.Figure()
                        for year in years:
                            year_data = class_data[class_data['Год'] == year]['Средний балл'].dropna()
                            fig.add_trace(go.Box(
                                y=year_data,
                                name=str(year)
                            ))
                        fig.update_layout(title='Сравнение успеваемости по годам')
                        st.plotly_chart(fig, use_container_width=True)
                    except:
                        st.info("График временно недоступен")
            else:
                st.warning("Нет данных о среднем балле для сравнения")

        st.subheader("🔗 Корреляция успеваемости и экзамена")

        # Ищем предметы с экзаменационными баллами
        exam_score_cols = [col for col in class_data.columns if exam_prefix in col and '_баллы' in col]
        grade_cols = [col for col in class_data.columns if grade_prefix in col and 'баллы' not in col]

        if exam_score_cols and grade_cols and 'Средний балл' in class_data.columns:
            # Берем первый предмет с экзаменом
            sample_exam = exam_score_cols[0]
            sample_subject = sample_exam.replace(f'{exam_prefix}_', '').replace('_баллы', '')
            sample_grade = f'{grade_prefix}_{sample_subject}'

            # Проверка наличия данных
            st.write(f"📌 Предмет для анализа: **{sample_subject}**")
            st.write(f"Колонка экзамена: `{sample_exam}` ({len(class_data[sample_exam].dropna())} записей)")
            st.write(
                f"Колонка оценки: `{sample_grade}` ({len(class_data[sample_grade].dropna()) if sample_grade in class_data.columns else 0} записей)")

            if sample_grade in class_data.columns:
                corr_result = calculator.calculate_spearman_correlation(sample_grade, sample_exam)

                corr_col1, corr_col2 = st.columns(2)

                with corr_col1:
                    if corr_result['rho']:
                        st.metric("Коэффициент Спирмена (ρ)", f"{corr_result['rho']}")
                    else:
                        st.metric("Коэффициент Спирмена (ρ)", "N/A")

                with corr_col2:
                    st.metric("Интерпретация", corr_result['interpretation'])

                scatter_chart = create_correlation_scatter(class_data, sample_grade, sample_exam)
                if scatter_chart:
                    st.plotly_chart(scatter_chart, use_container_width=True)
                    st.caption(f"Предмет: {sample_subject}, N={corr_result.get('n', 0)}")
            else:
                st.warning(f"Колонка {sample_grade} не найдена в данных")
        else:
            st.info("Нет данных для расчета корреляции")
            st.write(f"Найдено колонок с экзаменом: {len(exam_score_cols)}")
            st.write(f"Найдено колонок с оценками: {len(grade_cols)}")

        # Таблица с данными
        st.subheader("📋 Данные по ученикам")

        display_columns = ['ФИО', 'Класс', 'Средний балл']
        if 'Средний балл экзамена' in class_data.columns:
            display_columns.append('Средний балл экзамена')
        exam_score_cols_display = [col for col in class_data.columns if exam_prefix in col and '_баллы' in col][:5]
        display_columns.extend(exam_score_cols_display)

        display_columns = [col for col in display_columns if col in class_data.columns]

        st.dataframe(class_data[display_columns].round(2), use_container_width=True, hide_index=True)

    # === ВКЛАДКА 2: УЧЕНИК ===
    with tab2:
        st.header("Данные по ученику")
        all_students = sorted(combined_df['ФИО'].unique())
        selected_student = st.selectbox("Выберите ученика", all_students)
        student_data = combined_df[combined_df['ФИО'] == selected_student]

        if len(student_data) == 0: return

        for idx, row in student_data.iterrows():
            st.subheader(f"📚 {row['ФИО']} ({row.get('Класс', 'N/A')})")
            if 'Год' in row and pd.notna(row['Год']): st.caption(f"Учебный год: {row['Год']}")

            c1, c2, c3 = st.columns(3)
            with c1:
                avg_grade = row.get('Средний балл')
                st.metric("Средний балл", f"{float(avg_grade):.2f}" if pd.notna(avg_grade) else "N/A")
            with c2:
                avg_exam = row.get('Средний балл экзамена')
                st.metric(f"Средний {exam_prefix}", f"{float(avg_exam):.1f}" if pd.notna(avg_exam) else "N/A")
            with c3:
                exam_count = sum(1 for col in student_data.columns if
                                 exam_prefix in col and '_баллы' in col and pd.notna(row.get(col)))
                st.metric("Сдано экзаменов", exam_count)

            st.subheader("📈 Динамика оценок по предметам")
            available_subjects = []
            for subject in ['Русский язык', 'Математика', 'Физика', 'Обществознание', 'Биология', 'Химия',
                            'Иностранный (английский) язык']:
                if any(col in student_data.columns and pd.notna(row.get(col)) for col in
                       [f'{p}_{subject}' if p != 'Год' else f'{grade_prefix}_{subject}' for p in
                        ['1', '2', '3', 'Год']]):
                    available_subjects.append(subject)

            if available_subjects:
                for subject in available_subjects:
                    chart = create_subject_dynamics_chart(student_data, subject, grade_prefix, exam_prefix)
                    if chart: st.plotly_chart(chart, use_container_width=True)

    # === ВКЛАДКА 3: РАСХОЖДЕНИЯ ===
    with tab3:
        st.header("Расхождения между текущей успеваемостью и экзаменом")
        st.markdown("""
        **Методика расчета:**
        1. Для каждого ученика рассчитываются Z-оценки по текущей успеваемости и экзамену
        2. Вычисляется показатель расхождения: **D = Z_экзамен — Z_текущая**
        3. Ученики с |D| > порога требуют педагогического внимания
        """)

        available_classes = sorted(combined_df['Класс'].unique())
        selected_class = st.selectbox("Выберите класс для анализа расхождений",
                                      available_classes, key="discrepancy_class")

        class_data = combined_df[combined_df['Класс'] == selected_class].copy()

        if len(class_data) == 0:
            st.warning("Нет данных для выбранного класса")
            return

        exam_score_cols = [col for col in class_data.columns if exam_prefix in col and '_баллы' in col]
        grade_cols = [col for col in class_data.columns if
                      grade_prefix in col and 'баллы' not in col and 'Средний' not in col]

        # Отладочная информация
        with st.expander("🔍 Диагностика данных", expanded=False):
            st.write(f"**Всего учеников:** {len(class_data)}")
            st.write(f"**Предметов с экзаменом:** {len(exam_score_cols)}")
            if exam_score_cols:
                for col in exam_score_cols:
                    subject = col.replace(f'{exam_prefix}_', '').replace('_баллы', '')
                    filled = class_data[col].notna().sum()
                    st.write(f"  📌 {subject}: {filled} учеников сдавали из {len(class_data)}")

        if not exam_score_cols:
            st.error("❌ Не найдены колонки с баллами экзамена!")
            return
        if not grade_cols:
            st.error("❌ Не найдены колонки с годовыми оценками!")
            return

        st.subheader("📊 Анализ по предметам")
        subject_tabs = st.tabs([col.replace(f'{exam_prefix}_', '').replace('_баллы', '')
                                for col in exam_score_cols[:5]])

        calculator = StatisticsCalculator(class_data)
        all_discrepancies = {}

        for idx, exam_col in enumerate(exam_score_cols[:5]):
            subject = exam_col.replace(f'{exam_prefix}_', '').replace('_баллы', '')
            grade_col = f'{grade_prefix}_{subject}'

            with subject_tabs[idx]:
                st.markdown(f"### {subject}")

                # Расчет Z-оценок на основе данных всего класса
                enriched_data = calculator.calculate_z_scores('Средний балл', exam_col)

                # Оставляем только тех, кто реально сдавал экзамен и имеет годовую оценку
                valid_data = enriched_data[
                    (enriched_data[exam_col].notna()) &
                    (enriched_data.get(grade_col, pd.Series(dtype=float)).notna())
                    ].copy()

                if len(valid_data) < 3:
                    st.warning("Недостаточно данных для анализа (минимум 3 ученика с обоими результатами)")
                    continue

                st.info(f"📊 Анализируется {len(valid_data)} учеников (сдавали {exam_prefix})")

                # Прямая фильтрация расхождений из обогащенного DataFrame
                discrepancy_students = pd.DataFrame()
                if 'Расхождение (D)' in valid_data.columns:
                    mask = abs(valid_data['Расхождение (D)']) > discrepancy_threshold
                    discrepancy_students = valid_data[mask].copy()
                    if len(discrepancy_students) > 0:
                        discrepancy_students['Тип расхождения'] = discrepancy_students['Расхождение (D)'].apply(
                            lambda x: 'Выше ожидаемого' if x > 0 else 'Ниже ожидаемого'
                        )

                all_discrepancies[subject] = discrepancy_students

                # Метрики
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Сдавали экзамен", len(valid_data))
                with col2:
                    above = len(discrepancy_students[discrepancy_students['Расхождение (D)'] > 0]) if len(
                        discrepancy_students) > 0 else 0
                    st.metric("Выше ожидаемого", above)
                with col3:
                    below = len(discrepancy_students[discrepancy_students['Расхождение (D)'] < 0]) if len(
                        discrepancy_students) > 0 else 0
                    st.metric("Ниже ожидаемого", below)

                # График расхождений (передаем valid_data, где уже есть колонка D)
                st.markdown("##### График расхождений")
                discrepancy_chart = create_discrepancy_chart(valid_data)
                if discrepancy_chart:
                    st.plotly_chart(discrepancy_chart, use_container_width=True)

                # Таблица с расхождениями
                st.markdown("##### Ученики с расхождениями")
                if len(discrepancy_students) > 0:
                    display_cols = ['ФИО', 'Средний балл', exam_col, grade_col, 'Z_текущая', 'Z_экзамен',
                                    'Расхождение (D)', 'Тип расхождения']
                    display_cols = [col for col in display_cols if col in discrepancy_students.columns]

                    discrepancy_students['|D|'] = abs(discrepancy_students['Расхождение (D)'])
                    discrepancy_students = discrepancy_students.sort_values('|D|', ascending=False)

                    st.dataframe(discrepancy_students[display_cols].round(3), use_container_width=True, hide_index=True)

                    # Рекомендации
                    st.markdown("##### 💡 Рекомендации")
                    above_students = discrepancy_students[discrepancy_students['Расхождение (D)'] > 0]['ФИО'].tolist()
                    below_students = discrepancy_students[discrepancy_students['Расхождение (D)'] < 0]['ФИО'].tolist()

                    if above_students:
                        with st.expander(f"🟢 Выше ожидаемого ({len(above_students)} учеников)"):
                            st.write("Возможные причины:")
                            st.write("- Ученик хорошо подготовился к экзамену")
                            st.write("- Текущие оценки были занижены")
                            st.write("**Ученики:** " + ", ".join(above_students[:10]))

                    if below_students:
                        with st.expander(f"🔴 Ниже ожидаемого ({len(below_students)} учеников)", expanded=True):
                            st.write("Возможные причины:")
                            st.write("- Стресс на экзамене")
                            st.write("- Пробелы в подготовке")
                            st.write("**Рекомендуется:** Индивидуальная работа")
                            st.write("**Ученики:** " + ", ".join(below_students[:10]))
                else:
                    st.success("✅ Значимых расхождений не выявлено")

        # ОБЩАЯ СТАТИСТИКА ПО ВСЕМ ПРЕДМЕТАМ
        st.divider()
        st.subheader("📈 Сводная статистика по всем предметам")

        if all_discrepancies:
            summary_data = []
            for subject, discrepancies in all_discrepancies.items():
                exam_col = f'{exam_prefix}_{subject}_баллы'
                total_students = class_data[exam_col].notna().sum()

                if len(discrepancies) > 0:
                    above = len(discrepancies[discrepancies['Расхождение (D)'] > 0])
                    below = len(discrepancies[discrepancies['Расхождение (D)'] < 0])
                else:
                    above = 0
                    below = 0

                summary_data.append({
                    'Предмет': subject,
                    'Сдавали экзамен': total_students,
                    'Выше ожидаемого': above,
                    'Ниже ожидаемого': below,
                    'Всего расхождений': above + below
                })

            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True, hide_index=True)

            import plotly.express as px
            fig = px.bar(
                summary_df,
                x='Предмет',
                y=['Выше ожидаемого', 'Ниже ожидаемого'],
                title='Распределение расхождений по предметам',
                barmode='group',
                color_discrete_sequence=['#28a745', '#dc3545']
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных для сводной статистики")