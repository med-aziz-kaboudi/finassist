import requests
import os
from flask import Flask, jsonify, request, render_template_string, send_file
from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.utils.dataframe import dataframe_to_rows
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import seaborn as sns
import io
import numpy as np
from dotenv import load_dotenv
import base64
from retrying import retry
import openai
import uuid
import json



html = '''
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Excel File Analysis</title>
    <style>
        body {
            font-family: 'Roboto', sans-serif;
            text-align: center;
            background-color: #f5f5f5;
            margin: 0;
            padding: 0;
        }

        h1 {
            color: #009961;
            font-weight: bold;
        }

        form {
            margin-bottom: 20px;
        }

        input[type="file"] {
            display: block;
            margin: 20px auto;
            padding: 10px;
            border: 2px dashed #009961;
            border-radius: 5px;
            background-color: #f5f5f5;
            color: #009961;
            outline: none;
            cursor: pointer;
        }

        input[type="submit"] {
            background-color: #009961;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s;
        }

        input[type="submit"]:hover {
            background-color: #0f75bc;
        }

        .container {
            width: 80%;
            margin: auto;
            background-color: #fff;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
            margin-top: 40px;
        }

        img {
            margin-top: 20px;
            max-width: 100%;
            height: auto;
            border-radius: 10px;
        }

        a {
            background-color: #009961;
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            display: inline-block;
            border-radius: 4px;
            transition: background-color 0.3s;
        }

        a:hover {
            background-color: #0f75bc;
        }

        .summary {
            background-color: #f5f5f5;
            padding: 20px;
            border-radius: 10px;
            margin-top: 40px;
            text-align: left;
        }

        .summary table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }

        .summary table, .summary th, .summary td {
            border: 1px solid #ddd;
        }

        .summary th, .summary td {
            padding: 15px;
            text-align: center;
            font-size: 14px;
        }

        .summary th {
            background-color: #009961;
            color: white;
        }

        .ai-analysis {
            border: 1px solid #ddd;
            background-color: #fff;
            padding: 20px;
            margin-top: 40px;
            text-align: left;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        }

         .chat-container {
            display: none;
            position: fixed;
            bottom: 10px;
            right: 10px;
            background: white;
            border: 1px solid #ddd;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            width: 300px;
        }

        #chat-box {
            height: 400px;
            overflow-y: auto;
            margin-bottom: 10px;
            border-bottom: 1px solid #ddd;
            
        }

        #chat-input {
            width: calc(100% - 110px);
            padding: 8px;
            margin-right: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            float: left;
        }

        #send-btn {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 4px;
            cursor: pointer;
            float: right;
        }

        #send-btn:hover {
            background-color: #45a049;
        }

        .chat-btn {
            background-color: #008CBA;
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            display: inline-block;
            border-radius: 4px;
            margin-top: 20px;
        }

        .chat-btn:hover {
            background-color: #005f6a;
        }

        #close-btn {
            background-color: transparent;
            color: #FF0000;
            border: none;
            padding: 5px;
            border-radius: 50%;
            cursor: pointer;
            position: absolute;
            top: 10px;
            right: 10px;
            font-size: 16px;
            line-height: 1;
            transition: background-color 0.3s, color 0.3s;
        }

        #close-btn:hover {
            background-color: #FF0000;
            color: white;
        }
        .echo{
            width: 120px;
            height: 120px;
        }
        .colr{
        color: #FF0000;
        }
         .redirect-button {
            display: inline-block;
            padding: 10px 20px;
            margin: 10px;
            background-color: #DD2222;
            color: white;
            border: none;
            border-radius: 5px;
            text-decoration: none;
            text-align: center;
            cursor: pointer;
        }

        .redirect-button:hover {
            background-color: #BE1E1E;
        }
    </style>
</head>
<body>
    <a href="https://chataifront-b695d6943c96.herokuapp.com/" class="redirect-button">LOG OUT</a>

    <div class="container">
        <img src="{{ url_for('static', filename='images/echominds.png') }}" alt="EchoMinds" class="echo">        <h1>Upload Excel File for Analysis</h1>
        <p class="colr">The file should contain at lease these elements : Date ; Category ; Incomes ; Expenses</p>
        <form action="/analyze" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".xlsx, .xls" required>
            <input type="submit" value="Analyze">
        </form>
        <div>
            {% if plot_url %}
                <img src="{{ plot_url }}" alt="Cumulative Profit/Loss Plot">
            {% endif %}
            {% if pie_chart_url %}
                <img src="{{ pie_chart_url }}" alt="Financial Distribution">
            {% endif %}
        </div>
        {% if summary %}
            <div class="summary">
                <h2>Yearly Summary:</h2>
                <p>{{ summary|safe }}</p>
            </div>
        {% endif %}
        {% if ai_analysis %}
            <div class="ai-analysis">
                <h2>AI-Driven Analysis:</h2>
                <p>{{ ai_analysis|safe }}</p>
            </div>
        {% endif %}
        {% if file_url %}
            <a href="{{ file_url }}" download="analyzed_data.xlsx">Download Analyzed Data</a>
        {% endif %}
    </div>
     <div class="chat-container" id="chat-container">
        <div id="chat-box"></div>
        <input type="text" id="chat-input" placeholder="Type your message...">
        <button id="send-btn" onclick="sendMessage()">Send</button>
        <input type="hidden" id="analysis-id" value="{{ analysis_id }}">
        <button id="close-btn" onclick="toggleChat()">✕</button>
    </div>
    <button class="chat-btn" onclick="toggleChat()">Chat with AI</button>
    <script type="text/javascript">
        function toggleChat() {
            var chatContainer = document.getElementById('chat-container');
            chatContainer.style.display = chatContainer.style.display === 'none' ? 'block' : 'none';
        }
        function sendMessage() {
            var input = document.getElementById('chat-input');
            var message = input.value;
            var analysisId = document.getElementById('analysis-id').value;
            input.value = '';
            if(message) {
                document.getElementById('chat-box').innerHTML += '<div><b>You:</b> ' + message + '</div>';
                fetch('/chat', {
                    method: 'POST',
                    body: JSON.stringify({'message': message, 'analysis_id': analysisId}),
                    headers: {'Content-Type': 'application/json'}
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    document.getElementById('chat-box').innerHTML += '<div><b>FinAssist:</b> ' + data.response + '</div>';
                    var chatBox = document.getElementById('chat-box');
                    chatBox.scrollTop = chatBox.scrollHeight;
                }) 
                .catch(error => {
                    console.error('There has been a problem with your fetch operation:', error);
                    document.getElementById('chat-box').innerHTML += '<div>Error: Unable to get response from AI</div>';
                });
            }
        }
    </script>
</body>
</html>
'''

app = Flask(__name__)
sns.set(style="whitegrid")

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = openai_api_key

def get_chatgpt_analysis(query):
    response = openai.Completion.create(model="text-davinci-003", prompt=query, max_tokens=200)
    return response['choices'][0]['text'].strip() if response else "No response or unexpected format from AI."

def convert_image_to_base64(img_path):
    with open(img_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:image/png;base64,{encoded_string}"

def insert_image_to_excel(worksheet, img_path, img_cell, width=None, height=None):
    img = Image(img_path)
    if width and height:
        img.width, img.height = width, height
    worksheet.add_image(img, img_cell)

def save_analysis_results(analysis_id, results):
    with open(f"analysis_results_{analysis_id}.json", "w") as file:
        json.dump(results, file)

def get_analysis_results(analysis_id):
    try:
        with open(f"analysis_results_{analysis_id}.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return None

@app.route('/')
def index():
    return render_template_string(html)

@app.route('/analyze', methods=['POST'])
def analyze():
    file = request.files.get('file')
    if file and file.filename:
        analysis_id = str(uuid.uuid4())
        df = pd.read_excel(file)
        df.columns = df.columns.str.lower()
        df['date'] = pd.to_datetime(df['date'])
        df['net'] = df['income'] - df['expenses']
        df['cumulative'] = df['net'].cumsum()
        fig_cumulative, ax_cumulative = plt.subplots(figsize=(8, 4))
        sns.lineplot(x='date', y='cumulative', data=df, ax=ax_cumulative, marker='o')
        ax_cumulative.axhline(y=0, color='red', linestyle='--')
        plt.tight_layout()
        plot_img_path = 'cumulative_plot.png'
        fig_cumulative.savefig(plot_img_path)
        plt.close(fig_cumulative)
        plot_url = convert_image_to_base64(plot_img_path)
        category_summary = df.groupby('category').agg({'net': 'sum'})
        category_summary_positive = category_summary[category_summary['net'] > 0]
        fig_pie, ax_pie = plt.subplots(figsize=(8, 8))
        category_summary_positive.plot.pie(y='net', ax=ax_pie, autopct='%1.1f%%', startangle=140, legend=False)
        plt.tight_layout()
        pie_img_path = 'pie_chart.png'
        fig_pie.savefig(pie_img_path)
        plt.close(fig_pie)
        pie_chart_url = convert_image_to_base64(pie_img_path)
        df['year'] = df['date'].dt.year
        yearly_summary = df.groupby('year').agg({'income': 'sum', 'expenses': 'sum', 'net': 'sum'})
        yearly_summary['win_percentage'] = np.where(yearly_summary['net'] > 0, yearly_summary['net'] / yearly_summary['income'] * 100, 0)
        summary_html = yearly_summary.to_html(classes="table table-striped", float_format='%.2f')
        query = f"Provide a financial analysis summary and suggestions for improvement based on the following data: {summary_html}"
        ai_analysis = get_chatgpt_analysis(query)

        analysis_results = {
            "ai_analysis": ai_analysis,
            "plot_url": plot_url,
            "pie_chart_url": pie_chart_url,
            "summary": summary_html
        }
        save_analysis_results(analysis_id, analysis_results)

        analyzed_file_path = 'analyzed_financial_data.xlsx'
        wb = Workbook()
        ws_data = wb.active
        ws_data.title = "Financial Data"
        for r in dataframe_to_rows(df, index=False, header=True):
            ws_data.append(r)
        insert_image_to_excel(ws_data, plot_img_path, 'A10')
        insert_image_to_excel(ws_data, pie_img_path, 'A40')
        wb.save(analyzed_file_path)
        os.remove(plot_img_path)
        os.remove(pie_img_path)
        file_url = '/download/' + analyzed_file_path
        return render_template_string(html, plot_url=plot_url, pie_chart_url=pie_chart_url, summary=summary_html, ai_analysis=ai_analysis, file_url=file_url, analysis_id=analysis_id)
    return 'Invalid file'

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(filename, as_attachment=True)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data['message'].lower()
    analysis_id = data.get('analysis_id')
    analysis_results = get_analysis_results(analysis_id)

    # Basic interactions dictionary
    basic_interactions = {
        "hello": "Hello! How can I assist you today?",
        "hi": "Hi there! What can I do for you?",
        "hey": "Hey! Need any help?",
        "how are you": "I'm just a bot, but thanks for asking! How can I assist you?",
        "what's up": "Not much, I'm here to help you. What do you need?",
        "bye": "Goodbye! Feel free to reach out if you need more help.",
        "what's your name": "I'm FinAssist. How can I help you?",
        "are you a robot": "I'm an Analisys AI chat bot. I can help you improve your financial stability.",
        "what are you": "I'm an Analisys AI chat bot that can help you improve your financial stability.",
        "more info":"If you want more informations about FinAssit you can visit our website or contact the EchoMinds.",
        "who made you": "I'm an AI called FinAssist made by the amazing team EchoMinds!",
        "contact": "If you have any technical issues or need personalized support, you can contact EchoMinds at echomindsteam@gmail.com.",
        "privacy": "Your financial data is secure with FinAssist. We prioritize privacy and follow strict security measures.",
        "thank you": "You're welcome! If you have any more questions or need further assistance, feel free to reach out.",
        "features": "FinAssist excels at analyzing income, expenses, and more. Ask about specific features to explore its capabilities.",
        "upgrade": "Thinking about advanced features? Consider subscribing to FinAssist plans for enhanced financial analysis tools."
    }

    # Respond to basic interactions
    if user_message in basic_interactions:
        ai_response = basic_interactions[user_message]
    elif 'json' in user_message:
        if analysis_results:
            ai_response = f"You asked about the JSON data. Here's the analysis: {json.dumps(analysis_results)}"
        else:
            ai_response = "It seems there are no JSON analysis results available for your query."
    else:
        if analysis_results:
            full_query = f"{user_message}\n\nPrevious Analysis:\n{analysis_results['ai_analysis']}"
            ai_response = get_chatgpt_analysis(full_query)
        else:
            ai_response = get_chatgpt_analysis(user_message)

    return jsonify({'response': ai_response})

if __name__ == '__main__':
    app.run(debug=True)
