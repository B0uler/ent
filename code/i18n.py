import streamlit as st
import json
import os

# --- Кэшированная функция для загрузки локали ---
@st.cache_data
def load_locale(language_code='en'):
    """Загружает JSON-файл локали для указанного языка."""
    locale_path = os.path.join('locales', f'{language_code}.json')
    try:
        with open(locale_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Если файл для языка не найден, возвращаем пустой словарь
        return {}

# --- Основная функция-переводчик ---
def t(key):
    """
    Получает переведенную строку по ключу для текущего языка.
    Язык берется из st.session_state.lang.
    """
    # Устанавливаем язык по умолчанию, если он еще не задан
    if 'lang' not in st.session_state:
        st.session_state.lang = 'en'
    
    # Загружаем словарь локали
    locale_dict = load_locale(st.session_state.lang)
    
    # Возвращаем перевод или сам ключ, если перевод не найден
    return locale_dict.get(key, key)

# --- Виджет для выбора языка ---
def language_selector():
    """Отображает selectbox для выбора языка и обновляет состояние."""
    
    def on_lang_change():
        """Callback-функция для обновления URL и состояния."""
        st.rerun()

    languages = {'Русский': 'ru', 'English': 'en'}
    # Находим текущий язык для отображения в selectbox
    current_lang_name = [name for name, code in languages.items() if code == st.session_state.get('lang', 'en')][0]
    
    selected_language = st.sidebar.selectbox(
        label="Язык / Language", 
        options=languages.keys(), 
        index=list(languages.keys()).index(current_lang_name)
    )
    
    # Если выбор изменился, обновляем состояние и перезапускаем
    if languages[selected_language] != st.session_state.get('lang'):
        st.session_state.lang = languages[selected_language]
        st.rerun()
