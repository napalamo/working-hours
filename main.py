import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import os
import threading
from babel.dates import format_datetime

load_dotenv()

# Функция для отправки POST запроса и получения данных о менеджерах
def fetch_managers_data(url):
    response = requests.post(url, data={'action': 'get_managers'})
    if response.status_code == 200:
        return response.json()
    else:
        return None

# Функция для отправки GET запроса для обновления статуса менеджера
def update_status(url, manager_id, action):
    response = requests.post(url, data={'manager_id': manager_id, 'action': action})
    return response.status_code == 200

# Функция для расчета прошедшего времени с начала рабочего дня или перерыва
def calculate_elapsed_time(start_time_str, timezone_str='Europe/Moscow'):
    # Предполагается, что start_at возвращается в часовом поясе UTC
    utc_zone = pytz.timezone(timezone_str)
    start_time = utc_zone.localize(datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S"))

    # Текущее время также переводится в часовой пояс UTC
    current_time = datetime.now(utc_zone)
    
    elapsed_time = current_time - start_time
    return elapsed_time

# Функция для вывода времени в удобном формате
def format_time(elapsed_time):
    seconds = int(elapsed_time.total_seconds())
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours} час(ов) {minutes:02d} минут"

# Проверяет текущее время по МСК
def is_time_outside_working_hours():
    moscow_tz = pytz.timezone('Europe/Moscow')
    current_time_moscow = datetime.now(moscow_tz).time()

    return current_time_moscow >= datetime.strptime("20:00", "%H:%M").time() or \
           current_time_moscow <= datetime.strptime("10:00", "%H:%M").time()
    
# Основная функция Streamlit
def main():
    st.title("Управление рабочим днём менеджера")

    # URL-адреса для запросов
    url_fetch = os.getenv('API_FETCH_URL')

    # Извлечение менеджера из URL-параметров
    query_params = st.experimental_get_query_params()
    manager_id = query_params.get("manager_id", [None])[0]

    if not manager_id:
        st.error("Пожалуйста, перейдите по уникальной ссылке с вашим ID менеджера.")
        return

    # Получение данных о менеджерах
    managers_data = fetch_managers_data(url_fetch)
    if managers_data:
        selected_manager = next((m for m in managers_data if str(m["manager_id"]) == manager_id), None)

        if selected_manager:
            st.header(f"Менеджер: {selected_manager['manager_name']}")
            col1, col2, col3 = st.columns([5, 1, 1])
            with col1:
                # Отображаем текущую дату и день недели
                now = datetime.now()
                today = format_datetime(now, format="dd.MM.yyyy (EEEE)", locale='ru_RU')
                st.metric(label="Текущая дата", value=today)

                # Создаем плейсхолдер для времени
                time_placeholder = st.empty()

                # Проверяем статус работы менеджера и отображаем соответствующую метрику
                if 'start_at' in selected_manager:
                    elapsed_time = calculate_elapsed_time(selected_manager['start_at'])
                    if selected_manager['working_status'] in ['start_day', 'end_break', None]:
                        st.metric(label="Время работы", value=format_time(elapsed_time))
                    elif selected_manager['working_status'] == 'start_break':
                        st.metric(label="Время перерыва", value=format_time(elapsed_time))
        else:
            st.error("Такого ID менеджера нет")
    else:
        st.error("Такого ID менеджера нет")

    # Размещение кнопок в одной колонке
    if selected_manager:
        col1, col2, col3 = st.columns([6, 1, 1])
        with col1:
            if is_time_outside_working_hours():
                st.warning("Рабочий день завершён. Перезагрузите страницу в 10:00 по МСК")
            elif selected_manager['working_status'] in ['start_day', 'end_break', None]:
                st.button("⛔ Завершить рабочий день", on_click=update_status, args=(url_fetch, selected_manager["manager_id"], "end_day"))
                st.info("Завершить рабочий день можно только 1 раз")
                st.button("▶️ Перерыв", on_click=update_status, args=(url_fetch, selected_manager["manager_id"], "start_break"))
                st.info("Когда вы уходите на перерыв, лиды на вас не распределяются")
            elif selected_manager["working_status"] == "start_break":
                st.button("⏸️Закончить перерыв", on_click=update_status, args=(url_fetch, selected_manager["manager_id"], "end_break"))
                st.info("Пока вы на перерыве, лиды на вас не распределяются")
            elif selected_manager["working_status"] == "end_day" and selected_manager["is_started_today"] == True:
                st.warning("Сегодня больше нельзя встать на смену")
            elif selected_manager["working_status"] == "end_day":
                st.button("🌟 Начать день", on_click=update_status, args=(url_fetch, selected_manager["manager_id"], "start_day"))
                st.info("В течении 10 минут после нажатия на вас начнут распределяться лиды")

if __name__ == "__main__":
    main()
