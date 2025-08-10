import streamlit as st
import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from elevenlabs import ElevenLabs

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

def generate_rubric(topic, questions, custom_prompt=None):
    """Generate rubric using OpenRouter's Gemini 2.5 Flash model"""
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        st.error("Please set OPENROUTER_API_KEY environment variable")
        return None
    
    questions_text = '\n'.join([f"{i+1}. {q}" for i, q in enumerate(questions)])
    
    if custom_prompt:
        prompt = custom_prompt.format(topic=topic, questions=questions_text)
    else:
        prompt = f"""Create a comprehensive binary rubric for evaluating oral exam responses on the topic: {topic}

Questions to be evaluated:
{questions_text}

Generate a rubric with 6-10 binary criteria (Yes/No) that covers these dimensions:
- Content Knowledge & Accuracy
- Communication & Clarity  
- Critical Thinking & Analysis
- Subject-Specific Skills
- Engagement & Preparation

For each criterion:
1. Provide a clear, specific statement
2. Make it binary (achievable with Yes/No)
3. Ensure it's relevant to {topic}
4. Make it measurable and objective

Format as:
Q1
☐ [Criterion statement]
☐ [Criterion statement]
Q2
☐ [Criterion statement]
☐ [Criterion statement]
etc.
Overall
☐ [Criterion statement]
☐ [Criterion statement]

Focus on criteria that help distinguish between different levels of understanding and preparation."""
    
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
        
        # Parse criteria from the response
        criteria = []
        for line in content.strip().split('\n'):
            line = line.strip()
            if line and ('□' in line or line.startswith('-') or line.startswith('•')):
                # Clean up the criterion
                criterion = line.replace('□', '').replace('-', '').replace('•', '').strip()
                if criterion:
                    criteria.append(criterion)
        
        return criteria
    except Exception as e:
        st.error(f"Error generating rubric: {str(e)}")
        return None

def display_questions():
    """Display generated or uploaded questions with editing capabilities"""
    # Get all questions
    all_questions = []
    if 'generated_questions' in st.session_state:
        all_questions.extend(st.session_state.generated_questions)
    if 'uploaded_questions' in st.session_state:
        all_questions.extend(st.session_state.uploaded_questions)
    
    if all_questions:
        st.header("Questions")
        
        # Initialize editing state
        if 'editing_questions' not in st.session_state:
            st.session_state.editing_questions = False
        
        # Toggle between view and edit modes
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("✏️ Edit Questions" if not st.session_state.editing_questions else "👁️ View Mode", key="edit_questions_btn"):
                st.session_state.editing_questions = not st.session_state.editing_questions
                st.rerun()
        
        if st.session_state.editing_questions:
            st.write("**Edit Mode:** Modify, add, or remove questions below")
            
            # Initialize editing questions if not exists
            if 'editing_questions_list' not in st.session_state:
                st.session_state.editing_questions_list = all_questions.copy()
            
            # Display editable questions
            for i, question in enumerate(st.session_state.editing_questions_list):
                col1, col2 = st.columns([5, 1])
                with col1:
                    new_question = st.text_area(
                        f"Question {i+1}",
                        value=question,
                        key=f"question_{i}",
                        height=60,
                        label_visibility="collapsed"
                    )
                    st.session_state.editing_questions_list[i] = new_question
                with col2:
                    st.write("")  # Spacing
                    if st.button("🗑️", key=f"delete_question_{i}", help="Delete this question"):
                        st.session_state.editing_questions_list.pop(i)
                        st.rerun()
            
            # Add new question
            st.write("---")
            new_question = st.text_area("Add new question:", key="new_question_input", height=60)
            if st.button("➕ Add Question") and new_question.strip():
                st.session_state.editing_questions_list.append(new_question.strip())
                st.rerun()
            
            # Save/Cancel buttons
            st.write("---")
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("💾 Save Changes", type="primary", key="save_questions"):
                    # Filter out empty questions
                    valid_questions = [q for q in st.session_state.editing_questions_list if q.strip()]
                    
                    # Update the original question lists
                    # Clear existing questions
                    if 'generated_questions' in st.session_state:
                        del st.session_state.generated_questions
                    if 'uploaded_questions' in st.session_state:
                        del st.session_state.uploaded_questions
                    
                    # Store all questions as generated questions
                    st.session_state.generated_questions = valid_questions
                    
                    # Clear editing state
                    st.session_state.editing_questions = False
                    if 'editing_questions_list' in st.session_state:
                        del st.session_state.editing_questions_list
                    
                    st.success("Questions updated!")
                    st.rerun()
            with col2:
                if st.button("❌ Cancel", key="cancel_questions"):
                    st.session_state.editing_questions = False
                    if 'editing_questions_list' in st.session_state:
                        del st.session_state.editing_questions_list
                    st.rerun()
        else:
            # View mode
            questions_to_show = []
            if 'generated_questions' in st.session_state:
                questions_to_show.extend([f"{q}" for q in st.session_state.generated_questions])
            if 'uploaded_questions' in st.session_state:
                questions_to_show.extend([f"{q}" for q in st.session_state.uploaded_questions])
            
            for i, question in enumerate(questions_to_show, 1):
                st.write(f"{i}. {question}")
            
            # Option to download all questions
            all_questions_text = '\n'.join([f"{i}. {q.split(' ', 1)[1] if ' ' in q else q}" for i, q in enumerate(questions_to_show, 1)])
            with col2:
                st.download_button(
                    label="📥 Download Questions",
                    data=all_questions_text,
                    file_name=f"oral_exam_questions_{st.session_state.get('topic', 'unknown')}.txt",
                    mime="text/plain"
                )

def generate_speech(text):
    """Generate speech from text using ElevenLabs flash-v25 model"""
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        st.error("Please set ELEVENLABS_API_KEY environment variable")
        return None
    
    try:
        client = ElevenLabs(api_key=api_key)
        
        # Generate speech using flash-v25 model
        audio = client.text_to_speech.convert(
            text=text,
            model_id="eleven_flash_v2_5",
            voice_id="21m00Tcm4TlvDq8ikWAM"  # Rachel voice - clear and professional
        )
        
        # Convert generator to bytes
        audio_bytes = b""
        for chunk in audio:
            audio_bytes += chunk
            
        return audio_bytes
            
    except Exception as e:
        st.error(f"Error generating speech: {str(e)}")
        return None

def display_voice_interface():
    """Display voice question interface"""
    if ('generated_questions' in st.session_state and st.session_state.generated_questions) or \
       ('uploaded_questions' in st.session_state and st.session_state.uploaded_questions):
        
        st.header("🔊 Text-to-Speech Questions")
        st.write("Select a question to have it read aloud using AI-generated speech.")
        
        # Get all questions
        all_questions = []
        if 'generated_questions' in st.session_state:
            all_questions.extend(st.session_state.generated_questions)
        if 'uploaded_questions' in st.session_state:
            all_questions.extend(st.session_state.uploaded_questions)
        
        if all_questions:
            # Question selection
            selected_question = st.selectbox(
                "Choose a question to read aloud:",
                options=range(len(all_questions)),
                format_func=lambda x: f"{x+1}. {all_questions[x][:60]}{'...' if len(all_questions[x]) > 60 else ''}",
                index=0
            )
            
            # Display selected question
            st.write("**Selected Question:**")
            st.write(f"{selected_question + 1}. {all_questions[selected_question]}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔊 Generate Speech", type="primary"):
                    with st.spinner("Generating speech..."):
                        audio_bytes = generate_speech(all_questions[selected_question])
                        
                        if audio_bytes:
                            st.session_state.generated_audio = audio_bytes
                            st.success("Speech generated successfully!")
                        else:
                            st.error("Failed to generate speech. Please try again.")
            
            with col2:
                if st.button("🗑️ Clear Audio"):
                    if 'generated_audio' in st.session_state:
                        del st.session_state.generated_audio
                    st.rerun()
            
            # Display generated audio
            if 'generated_audio' in st.session_state:
                st.subheader("Generated Speech")
                st.audio(st.session_state.generated_audio, format="audio/mp3")
                
                # Option to download audio
                st.download_button(
                    label="📥 Download Audio",
                    data=st.session_state.generated_audio,
                    file_name=f"question_{selected_question + 1}_audio.mp3",
                    mime="audio/mp3"
                )

def display_rubric():
    """Display generated rubric with editing capabilities"""
    if 'rubric_criteria' in st.session_state:
        st.header("Evaluation Rubric")
        
        # Initialize editing state
        if 'editing_rubric' not in st.session_state:
            st.session_state.editing_rubric = False
        
        # Toggle between view and edit modes
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("✏️ Edit Rubric" if not st.session_state.editing_rubric else "👁️ View Mode"):
                st.session_state.editing_rubric = not st.session_state.editing_rubric
                st.rerun()
        
        if st.session_state.editing_rubric:
            st.write("**Edit Mode:** Modify, add, or remove criteria below")
            
            # Initialize editing criteria if not exists
            if 'editing_criteria' not in st.session_state:
                st.session_state.editing_criteria = st.session_state.rubric_criteria.copy()
            
            # Display editable criteria
            for i, criterion in enumerate(st.session_state.editing_criteria):
                col1, col2 = st.columns([5, 1])
                with col1:
                    new_criterion = st.text_input(
                        f"Criterion {i+1}",
                        value=criterion,
                        key=f"criterion_{i}",
                        label_visibility="collapsed"
                    )
                    st.session_state.editing_criteria[i] = new_criterion
                with col2:
                    if st.button("🗑️", key=f"delete_{i}", help="Delete this criterion"):
                        st.session_state.editing_criteria.pop(i)
                        st.rerun()
            
            # Add new criterion
            st.write("---")
            new_criterion = st.text_input("Add new criterion:", key="new_criterion")
            if st.button("➕ Add Criterion") and new_criterion.strip():
                st.session_state.editing_criteria.append(new_criterion.strip())
                st.rerun()
            
            # Save/Cancel buttons
            st.write("---")
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("💾 Save Changes", type="primary"):
                    # Filter out empty criteria
                    st.session_state.rubric_criteria = [c for c in st.session_state.editing_criteria if c.strip()]
                    st.session_state.editing_rubric = False
                    if 'editing_criteria' in st.session_state:
                        del st.session_state.editing_criteria
                    st.success("Rubric updated!")
                    st.rerun()
            with col2:
                if st.button("❌ Cancel"):
                    st.session_state.editing_rubric = False
                    if 'editing_criteria' in st.session_state:
                        del st.session_state.editing_criteria
                    st.rerun()
        else:
            # View mode
            st.write("Use this binary rubric to evaluate student responses:")
            
            for i, criterion in enumerate(st.session_state.rubric_criteria, 1):
                st.write(f"**{i}.** {criterion}")
            
            # Option to download rubric
            rubric_text = '\n'.join([f"☐ {i}. {criterion}" for i, criterion in enumerate(st.session_state.rubric_criteria, 1)])
            with col2:
                st.download_button(
                    label="📥 Download Rubric",
                    data=rubric_text,
                    file_name=f"oral_exam_rubric_{st.session_state.get('topic', 'unknown')}.txt",
                    mime="text/plain"
                )

st.title("Oral Exam Bot")

st.write("""
Welcome! This application helps educators conduct oral examinations by:

- **Developing standardized questions** based on your chosen subject area
- **Creating comprehensive rubrics** for consistent evaluation
- **Generating follow-up questions** to probe deeper understanding
- **Live exam participation** using speech-to-text and text-to-speech models
- **Customizable personas** to adapt the bot's interaction style as desired         

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
        st.subheader("OR: Upload Your Own Questions")
        
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
    
    # Rubric Generation Section
    if ('generated_questions' in st.session_state and st.session_state.generated_questions) or \
       ('uploaded_questions' in st.session_state and st.session_state.uploaded_questions):
        
        st.header("Rubric Generation")
        
        # Get all questions for rubric generation
        all_questions = []
        if 'generated_questions' in st.session_state:
            all_questions.extend(st.session_state.generated_questions)
        if 'uploaded_questions' in st.session_state:
            all_questions.extend(st.session_state.uploaded_questions)
        
        # Default prompt
        default_prompt = """Create a comprehensive binary rubric for evaluating oral exam responses on the topic: {topic}

Questions to be evaluated:
{questions}

Generate a rubric with 6-10 binary criteria (Yes/No) that covers these dimensions:
- Content Knowledge & Accuracy
- Communication & Clarity  
- Critical Thinking & Analysis
- Subject-Specific Skills
- Engagement & Preparation

For each criterion:
1. Provide a clear, specific statement
2. Make it binary (achievable with Yes/No)
3. Ensure it's relevant to {topic}
4. Make it measurable and objective

Format as:
Q1
☐ [Criterion statement]
☐ [Criterion statement]
Q2
☐ [Criterion statement]
☐ [Criterion statement]
etc.
Overall
☐ [Criterion statement]
☐ [Criterion statement]

Focus on criteria that help distinguish between different levels of understanding and preparation."""
        
        # Initialize prompt in session state if not exists
        if 'rubric_prompt' not in st.session_state:
            st.session_state.rubric_prompt = default_prompt
        
        # Editable prompt section
        with st.expander("Customize Rubric Generation Prompt", expanded=False):
            st.write("Edit the prompt below to customize how the rubric is generated. Binary criteria are used by default as this makes it easier to evaluate if LLM judgments of the student responses are correct. Use `{topic}` and `{questions}` as placeholders.")
            
            custom_prompt = st.text_area(
                "Rubric Generation Prompt",
                value=st.session_state.rubric_prompt,
                height=300,
                help="Use {topic} and {questions} as placeholders that will be replaced with actual values"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Reset to Default"):
                    st.session_state.rubric_prompt = default_prompt
                    st.rerun()
            with col2:
                if st.button("Save Prompt"):
                    st.session_state.rubric_prompt = custom_prompt
                    st.success("Prompt saved!")
        
        # Generate rubric button
        if st.button("Generate Rubric", type="primary"):
            with st.spinner("Generating rubric..."):
                criteria = generate_rubric(topic, all_questions, st.session_state.rubric_prompt)
                if criteria:
                    st.session_state.rubric_criteria = criteria
                    st.success(f"Generated rubric with {len(criteria)} criteria!")
                else:
                    st.error("Failed to generate rubric. Please check your API key and prompt.")
    
    display_rubric()
    
    display_voice_interface()
