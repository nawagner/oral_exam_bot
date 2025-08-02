import streamlit as st
import json
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

def generate_questions(topic, num_questions, difficulty_level):
    """Generate questions using OpenRouter's Gemini 2.5 Flash model"""
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        st.error("Please set OPENROUTER_API_KEY environment variable")
        return None
    
    prompt = f"""Generate {num_questions} {difficulty_level.lower()} level oral exam questions for the topic: {topic}

The questions should be:
- Clear and specific
- Appropriate for {difficulty_level.lower()} level understanding
- Suitable for oral examination
- Designed to test comprehension and critical thinking

Return only the questions, one per line, numbered 1., 2., etc."""
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        response = client.chat.completions.create(
            model="google/gemini-2.5-flash",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        content = response.choices[0].message.content
        
        # Parse questions from the response
        questions = []
        for line in content.strip().split('\n'):
            line = line.strip()
            if line and ('.' in line or '?' in line):
                # Remove numbering if present
                if line[0].isdigit():
                    line = line.split('.', 1)[1].strip()
                questions.append(line)
        
        return questions
    except Exception as e:
        st.error(f"Error generating questions: {str(e)}")
        return None

def parse_uploaded_questions(uploaded_file):
    """Parse questions from uploaded file"""
    try:
        if uploaded_file.type == "application/json":
            content = json.loads(uploaded_file.read().decode('utf-8'))
            if isinstance(content, list):
                return content
            elif isinstance(content, dict) and 'questions' in content:
                return content['questions']
            else:
                st.error("JSON file should contain an array of questions or an object with 'questions' key")
                return None
        else:  # text file
            content = uploaded_file.read().decode('utf-8')
            questions = [line.strip() for line in content.split('\n') if line.strip()]
            return questions
    except Exception as e:
        st.error(f"Error parsing file: {str(e)}")
        return None

def display_questions():
    """Display generated or uploaded questions"""
    questions_to_show = []
    
    if 'generated_questions' in st.session_state:
        questions_to_show.extend([f"🤖 {q}" for q in st.session_state.generated_questions])
    
    if 'uploaded_questions' in st.session_state:
        questions_to_show.extend([f"📄 {q}" for q in st.session_state.uploaded_questions])
    
    if questions_to_show:
        st.header("Questions")
        for i, question in enumerate(questions_to_show, 1):
            st.write(f"{i}. {question}")
        
        # Option to download all questions
        all_questions_text = '\n'.join([f"{i}. {q.split(' ', 1)[1]}" for i, q in enumerate(questions_to_show, 1)])
        st.download_button(
            label="Download All Questions",
            data=all_questions_text,
            file_name=f"oral_exam_questions_{st.session_state.get('topic', 'unknown')}.txt",
            mime="text/plain"
        )

st.title("Oral Exam Bot")

st.write("""
Welcome to the Oral Exam Bot! This application helps educators by:

- **Developing standardized questions** based on your chosen subject area
- **Creating comprehensive rubrics** for consistent evaluation
- **Generating follow-up questions** to probe deeper understanding
- **Live exam participation** using speech-to-text and text-to-speech models
- **Customizable personas** to adapt the bot's interaction style as desired

It is designed to support teachers conducting oral exams without full automation.         

Get started by selecting your subject area and exam parameters below.
""")

st.header("Subject Selection")

topic = st.text_input("Enter your exam topic. Be as detailed as feasible.")

if topic:
    st.success(f"Selected topic: {topic}")
    
    st.header("Question Generation")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Generate Questions with AI")
        
        num_questions = st.slider("Number of questions to generate", 1, 20, 5)
        difficulty_level = st.selectbox("Difficulty Level", ["Beginner", "Intermediate", "Advanced"])
        
        if st.button("Generate Questions", type="primary"):
            with st.spinner("Generating questions..."):
                questions = generate_questions(topic, num_questions, difficulty_level)
                if questions:
                    st.session_state.generated_questions = questions
                    st.success(f"Generated {len(questions)} questions!")
                else:
                    st.error("Failed to generate questions. Please check your API key.")
    
    with col2:
        st.subheader("Upload Your Own Questions")
        
        uploaded_file = st.file_uploader(
            "Choose a file with questions",
            type=['txt', 'json'],
            help="Upload a .txt file with one question per line, or a .json file with questions array"
        )
        
        if uploaded_file is not None:
            questions = parse_uploaded_questions(uploaded_file)
            if questions:
                st.session_state.uploaded_questions = questions
                st.success(f"Uploaded {len(questions)} questions!")
            else:
                st.error("Failed to parse questions from file.")
    
    display_questions()
