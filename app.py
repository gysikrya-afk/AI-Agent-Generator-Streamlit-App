import zipfile
import io
import os
import tempfile

import streamlit as st

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import Docx2txtLoader


def clean_code(text):
    """Удаляет лишние markdown-символы ```python из ответа ИИ."""
    return text.replace("```python", "").replace("```", "").strip()


def create_zip(files_dict):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files_dict.items():
            zf.writestr(name, content)
    return buf.getvalue()


st.set_page_config(page_title="Агент", layout="centered")

st.title("ИИ-Агент")

with st.sidebar:
    api_key = st.text_input("Groq API Key", type="password")

    file = st.file_uploader("Загрузите файл", type=["docx"])

if st.button("Начать работу агента"):
    if not api_key:
        st.error("Введите Groq API Key!")
    elif not file:
        st.error("Загрузите документ")
    else:
        with st.spinner("Читаем текст документа..."):
            try:
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".docx"
                ) as tmp_file:
                    tmp_file.write(file.getvalue())
                    tmp_path = tmp_file.name

                loader = Docx2txtLoader(tmp_path)
                data = loader.load()
                task = data[0].page_content
                st.success("Файл успешно прочитан!")

            except Exception as e:
                st.error(f"Ошибка при чтении: {e}")

            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        with st.spinner("Подготовка агента и промпта..."):
            try:
                llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=api_key)
                code_prompt = ChatPromptTemplate.from_template(
                    "Ты Senior Python Developer. Напиши качественный код на Streamlit для следующей задачи: {task}. "
                    "Используй современные методы (st.cache_data, разделение на колонки). Выведи ТОЛЬКО код."
                )
                code_chain = code_prompt | llm | StrOutputParser()
                generated_code = clean_code(code_chain.invoke({"task": task}))

                readme_prompt = ChatPromptTemplate.from_template(
                    "Напиши профессиональный README.md для проекта: {task}. "
                    "Включи разделы: Описание, Установка, Как запустить."
                )
                readme_chain = readme_prompt | llm | StrOutputParser()
                generated_readme = readme_chain.invoke({"task": task})

                req_prompt = ChatPromptTemplate.from_template(
                    "Перечисли необходимые Python библиотеки для этого проекта: {task}. "
                    "Выведи только названия библиотек в формате requirements.txt. Обязательно добавь streamlit."
                )
                req_chain = req_prompt | llm | StrOutputParser()
                generated_reqs = req_chain.invoke({"task": task})

                st.success("Агент всё сделал!")

            except Exception as e:
                st.error("Ошибка при создании агентов или выводе ответа")
                st.exception(e)
                st.stop()

        tab1, tab2, tab3 = st.tabs(["🐍 Код (app.py)", "📄 README", "📋 Зависимости"])

        with tab1:
            st.code(generated_code, language="python")
        with tab2:
            st.markdown(generated_readme)
        with tab3:
            st.code(generated_reqs, language="text")

        st.divider()
        zip_data = create_zip(
            {
                "app.py": generated_code,
                "README.md": generated_readme,
                "requirements.txt": generated_reqs,
            }
        )

        st.download_button(
            label="🎁 Скачать готовый проект (ZIP)",
            data=zip_data,
            file_name="streamlit_project.zip",
            mime="application/zip",
            use_container_width=True,
        )
