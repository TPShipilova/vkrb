"""Модуль визуализации данных через Plotly."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def create_class_statistics_chart(df: pd.DataFrame, grade_column: str = 'Средний балл'):
    """Создание графика распределения оценок по классу"""
    if grade_column not in df.columns:
        return None

    values = df[grade_column].dropna()
    if len(values) == 0:
        return None

    fig = px.histogram(
        df,
        x=grade_column,
        nbins=10,
        title='Распределение средних баллов по классу',
        labels={grade_column: 'Средний балл'},
        color_discrete_sequence=['#636EFA']
    )

    fig.update_layout(showlegend=False, height=400)

    return fig


def create_correlation_scatter(df: pd.DataFrame, col1: str, col2: str):
    """Диаграмма рассеяния для корреляции"""
    if col1 not in df.columns or col2 not in df.columns:
        return None

    mask = df[col1].notna() & df[col2].notna()
    plot_data = df[mask]

    if len(plot_data) < 3:
        return None

    fig = px.scatter(
        plot_data,
        x=col1,
        y=col2,
        hover_data=['ФИО'],
        title='Зависимость между текущей успеваемостью и экзаменом',
        labels={col1: 'Текущая успеваемость', col2: 'Результат экзамена'},
        color_discrete_sequence=['#EF553B']
    )

    fig.update_layout(height=400)

    return fig


def create_discrepancy_chart(df: pd.DataFrame):
    """График расхождений по ученикам"""
    if 'Расхождение (D)' not in df.columns or 'ФИО' not in df.columns:
        return None

    discrepancy_data = df[['ФИО', 'Расхождение (D)']].dropna()

    if len(discrepancy_data) == 0:
        return None

    discrepancy_data['|D|'] = abs(discrepancy_data['Расхождение (D)'])
    discrepancy_data = discrepancy_data.sort_values('|D|', ascending=False)

    fig = px.bar(
        discrepancy_data,
        x='ФИО',
        y='Расхождение (D)',
        title='Расхождения между текущей успеваемостью и экзаменом',
        labels={'Расхождение (D)': 'Показатель расхождения (D)', 'ФИО': 'Ученик'},
        color='Расхождение (D)',
        color_continuous_scale='RdBu'
    )

    fig.add_hline(y=1.0, line_dash="dash", line_color="green", annotation_text="Порог +1")
    fig.add_hline(y=-1.0, line_dash="dash", line_color="red", annotation_text="Порог -1")

    fig.update_layout(height=500, xaxis_tickangle=-45)

    return fig


def create_subject_dynamics_chart(student_data: pd.DataFrame, subject: str, grade_prefix: str, exam_prefix: str):
    """График динамики оценок по предмету для ученика"""
    if len(student_data) == 0:
        return None

    row = student_data.iloc[0]

    # Собираем данные по периодам
    periods = []
    grades = []

    # Триместры и годовая оценка
    for period in ['1', '2', '3', 'Год']:
        col_name = f'{period}_{subject}' if period != 'Год' else f'{grade_prefix}_{subject}'
        if col_name in row.index and pd.notna(row.get(col_name)):
            periods.append(f'{period} триместр' if period != 'Год' else 'Годовая')
            grades.append(float(row[col_name]))

    # Добавляем экзамен
    exam_col = f'{exam_prefix}_{subject}_баллы'
    if exam_col in row.index and pd.notna(row.get(exam_col)):
        periods.append(f'{exam_prefix}')
        # Конвертируем в 5-балльную шкалу для наглядности
        exam_score = float(row[exam_col])
        if exam_prefix == 'ЕГЭ':
            grades.append(exam_score / 20)  # ЕГЭ 100-балльная
        else:
            grades.append(exam_score)  # ОГЭ 5-балльная

    if len(periods) < 2:
        return None

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=periods,
        y=grades,
        mode='lines+markers',
        name=subject,
        line=dict(color='#636EFA', width=3),
        marker=dict(size=10),
        text=[f'{g:.1f}' for g in grades],
        textposition='top center'
    ))

    fig.update_layout(
        title=f'{subject}: динамика оценок',
        xaxis_title='Период',
        yaxis_title='Оценка',
        yaxis=dict(range=[0, 5.5], tickmode='linear', dtick=1),
        height=300,
        showlegend=False,
        hovermode='x unified'
    )

    return fig