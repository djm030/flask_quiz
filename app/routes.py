from flask import jsonify, render_template, request, Blueprint, make_response, redirect, url_for
from .models import Question, Participant, Quiz
from .database import db
import plotly.express as px
import pandas as pd
import plotly
import json

# 'main'이라는 이름의 Blueprint 객체 생성
main = Blueprint('main', __name__)

@main.route('/', methods=['GET'])
def home():
    # 참여자 정보 입력 페이지를 렌더링합니다.
    return render_template('index.html')

@main.route('/participants', methods=['POST'])
def add_participant():
    data = request.get_json()
    new_participant = Participant(name=data['name'], age=data['age'], gender=data['gender'])
    db.session.add(new_participant)
    db.session.commit()

    # 리다이렉션 URL과 참여자 ID를 JSON 응답으로 전송
    return jsonify({"redirect": url_for('main.quiz'), "participant_id": new_participant.id})

@main.route('/quiz')
def quiz():
    # 퀴즈 페이지를 렌더링합니다. 참여자 ID 쿠키가 필요합니다.
    participant_id = request.cookies.get('participant_id')
    if not participant_id:
        # 참여자 ID가 없으면, 홈페이지로 리다이렉션합니다.
        return redirect(url_for('main.home'))
    
    questions = Question.query.all()
    questions_list = [question.content for question in questions]
    return render_template('quiz.html', questions=questions_list)

@main.route('/submit', methods=['POST'])
def submit():
    # 참여자 ID가 필요합니다.
    participant_id = request.cookies.get('participant_id')
    if not participant_id:
        return jsonify({"error": "Participant ID not found"}), 400

    data = request.json
    quizzes = data.get('quizzes', [])

    for quiz in quizzes:
        question_id = quiz.get('question_id')
        chosen_answer = quiz.get('chosen_answer')
        
        # 새 Quiz 인스턴스 생성
        new_quiz_entry = Quiz(
            participant_id=participant_id,
            question_id=question_id,
            chosen_answer=chosen_answer
        )
        # 데이터베이스에 추가
        db.session.add(new_quiz_entry)
    
    # 변경 사항 커밋
    db.session.commit()
    print(url_for('main.show_results'))
    return jsonify({"message": "Quiz answers submitted successfully.","redirect": url_for('main.show_results'),})

@main.route('/questions')
def get_questions():
    questions = Question.query.all()
    questions_list = [{'id': question.id, 'content': question.content} for question in questions]
    return jsonify(questions=questions_list)

@main.route('/results')
def show_results():
    # 데이터베이스에서 데이터 조회
    participants_query = Participant.query.all()
    quizzes_query = Quiz.query.join(Question).all()
    
    # pandas DataFrame으로 변환
    participants_data = [{'age': participant.age, 'gender': participant.gender} for participant in participants_query]
    quizzes_data = [{'question_id': quiz.question_id, 'chosen_answer': quiz.chosen_answer, 'participant_age': quiz.participant.age} for quiz in quizzes_query]
    
    participants_df = pd.DataFrame(participants_data)
    quizzes_df = pd.DataFrame(quizzes_data)

    # Plotly 시각화 생성
    # 예시 1: 나이별 분포 (도넛 차트)
    fig_age = px.pie(participants_df, names='age', hole=0.3, 
                 title='Age Distribution',
                 color_discrete_sequence=px.colors.sequential.RdBu,
                 labels={'age':'Age Group'})
    fig_age.update_traces(textposition='inside', textinfo='percent+label')

    fig_gender = px.pie(participants_df, names='gender', hole=0.3, 
                        title='Gender Distribution',
                        color_discrete_sequence=px.colors.sequential.Purp,
                        labels={'gender':'Gender'})
    fig_gender.update_traces(textposition='inside', textinfo='percent+label')

    quiz_response_figs = {}

    # 각 질문 ID별로 반복하여 그래프 생성
    for question_id in quizzes_df['question_id'].unique():
        filtered_df = quizzes_df[quizzes_df['question_id'] == question_id]
        fig = px.histogram(filtered_df, x='chosen_answer', 
                        title=f'Question {question_id} Responses',
                        color='chosen_answer',
                        barmode='group',
                        category_orders={"chosen_answer": ["yes", "no"]}, # 카테고리 순서 지정
                        color_discrete_map={"yes": "RebeccaPurple", "no": "LightSeaGreen"}) # 컬러 매핑
        fig.update_layout(
            xaxis_title='Chosen Answer',
            yaxis_title='Count',
            plot_bgcolor='rgba(0,0,0,0)', # 배경색 투명
            paper_bgcolor='rgba(0,0,0,0)', # 전체 배경색 투명
            font=dict(
                family="Courier New, monospace",
                size=18,
                color="#7f7f7f"
            ),
            title_font=dict(
                family="Helvetica, Arial, sans-serif",
                size=22,
                color="RebeccaPurple"
            )
        )
        fig.update_traces(marker_line_width=1.5, opacity=0.6) # 투명도와 테두리 두께 조정

        # 생성된 그래프를 딕셔너리에 저장
        quiz_response_figs[f'question_{question_id}'] = fig
    age_quiz_response_figs = {}
        # 나이대를 구분하는 함수
    def age_group(age):
        if age < 20:
            return '10s'
        elif age < 30:
            return '20s'
        elif age < 40:
            return '30s'
        elif age < 50:
            return '40s'
        else:
            return '50s+'

    # 나이대 그룹 열 추가
    quizzes_df['age_group'] = quizzes_df['participant_age'].apply(age_group)

    # 각 질문 ID와 나이대별로 대답 분포를 시각화
    for question_id in quizzes_df['question_id'].unique():
        filtered_df = quizzes_df[quizzes_df['question_id'] == question_id]
        fig = px.histogram(filtered_df, x='age_group', color='chosen_answer',
                        barmode='group', title=f'Question {question_id} Responses by Age Group',
                        labels={'age_group': 'Age Group', 'chosen_answer': 'Chosen Answer'},
                        category_orders={"age_group": ["10s", "20s", "30s", "40s", "50s+"]})

        # 스타일 조정
        fig.update_layout(
            xaxis_title='Age Group',
            yaxis_title='Count',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(
                family="Courier New, monospace",
                size=18,
                color="#7f7f7f"
            ),
            title_font=dict(
                family="Helvetica, Arial, sans-serif",
                size=22,
                color="RebeccaPurple"
            )
        )
        fig.update_traces(marker_line_width=1.5, opacity=0.6)
        age_quiz_response_figs[f'question_{question_id}']=fig
    # 딕셔너리에 저장된 그래프들을 JSON으로 변환
    graphs_json = json.dumps({
        'age_distribution': fig_age,
        'gender_distribution': fig_gender,
        'quiz_responses': quiz_response_figs,
        'age_quiz_response_figs':age_quiz_response_figs
    }, cls=plotly.utils.PlotlyJSONEncoder)

    # 데이터를 results.html에 전달
    return render_template('results.html', graphs_json=graphs_json)