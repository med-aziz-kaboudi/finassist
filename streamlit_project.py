import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import openai
import streamlit as st
from dotenv import load_dotenv
from io import BytesIO
from openpyxl import Workbook
from openpyxl.drawing.image import Image as OpenpyxlImage

load_dotenv()

sns.set(style="whitegrid")

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.error("OpenAI API key is not set. Please check your .env file or environment variables.")
else:
    openai.api_key = openai_api_key

def get_chatgpt_analysis(query):
    response = openai.Completion.create(model="text-davinci-003", prompt=query, max_tokens=100)
    return response.choices[0].text if response else "Analysis not available"

def analyze_financial_data(df):
    df['year'] = df['date'].dt.year
    yearly_summary = df.groupby('year').agg({'income': 'sum', 'expenses': 'sum', 'net': 'sum'})
    yearly_summary['status'] = np.where(yearly_summary['net'] > 0, 'Win', 'Loss')
    yearly_summary['win_percentage'] = np.where(yearly_summary['net'] > 0, yearly_summary['net'] / yearly_summary['income'] * 100, 0)
    insights = "Positive performance" if yearly_summary['net'].sum() > 0 else "Negative performance"
    return yearly_summary, insights

def save_plot(fig, filename):
    fig.savefig(filename, format='png')
    plt.close(fig)

def insert_image_to_excel(worksheet, img_path, img_cell):
    img = OpenpyxlImage(img_path)
    worksheet.add_image(img, img_cell)

def to_excel(df, fig_cumulative_path, fig_pie_path):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        workbook = writer.book
        sheet = workbook.active
        if fig_cumulative_path:
            insert_image_to_excel(sheet, fig_cumulative_path, 'A10')
        if fig_pie_path:
            insert_image_to_excel(sheet, fig_pie_path, 'A20')
    processed_data = output.getvalue()
    return processed_data

def chat_with_gpt(prompt):
    response = openai.Completion.create(model="text-davinci-003", prompt=prompt, max_tokens=150)
    return response.choices[0].text.strip() if response else "Sorry, I couldn't generate a response."

st.title("Excel File Analysis")

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = ""

uploaded_file = st.file_uploader("Choose an Excel file (.xlsx, .xls)", type=['xlsx', 'xls'])

if uploaded_file and not st.session_state.chat_history:
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.lower()
    df['date'] = pd.to_datetime(df['date'])
    df['net'] = df['income'] - df['expenses']
    df['cumulative'] = df['net'].cumsum()

    fig_cumulative, ax_cumulative = plt.subplots(figsize=(8, 4))
    sns.lineplot(x='date', y='cumulative', data=df, ax=ax_cumulative, marker='o')
    ax_cumulative.axhline(y=0, color='red', linestyle='--')
    st.pyplot(fig_cumulative)
    cumulative_plot_path = 'cumulative_plot.png'
    save_plot(fig_cumulative, cumulative_plot_path)

    category_summary = df.groupby('category').agg({'net': 'sum'})
    category_summary_positive = category_summary[category_summary['net'] > 0]
    fig_pie, ax_pie = plt.subplots(figsize=(8, 8))
    category_summary_positive.plot.pie(y='net', ax=ax_pie, autopct='%1.1f%%', startangle=140, legend=False)
    st.pyplot(fig_pie)
    pie_plot_path = 'pie_plot.png'
    save_plot(fig_pie, pie_plot_path)

    yearly_summary, insights = analyze_financial_data(df)
    st.write("Yearly Summary:")
    st.dataframe(yearly_summary)

    query = f"Provide a financial analysis summary and suggestions for improvement based on the following data: {insights}"
    ai_analysis = get_chatgpt_analysis(query)
    st.write("AI-Driven Analysis:")
    st.write(ai_analysis)

    df_excel = to_excel(df, cumulative_plot_path, pie_plot_path)
    st.download_button(label="Download Excel Analysis", data=df_excel, file_name="analyzed_data.xlsx", mime="application/vnd.ms-excel")

st.sidebar.title("Chatbot")
user_input = st.sidebar.text_input("Ask me something about the financial analysis")
if st.sidebar.button("Send"):
    response = chat_with_gpt(user_input)
    st.session_state.chat_history += f"You: {user_input}\nBot: {response}\n\n"
    st.sidebar.text_area("Chat History", value=st.session_state.chat_history, height=300, key="chat_history")
