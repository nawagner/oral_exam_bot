import streamlit as st
import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from elevenlabs import ElevenLabs

# Load environment variables from .env file
load_dotenv()

# Available ElevenLabs voices with descriptions
AVAILABLE_VOICES = {
    "onwK4e9ZLuTAKqWW03F9": {
        "name": "Daniel",
        "description": "British male voice - Perfect for a nature documentary"
    },
    "AZnzlk1XvdvUeBnXmlld": {
        "name": "Rachel",
        "description": "A middle-aged female voice with an Africa-American accent - Calm with a hint of rasp"
    },
    "Xb7hH8MSUJpSbSDYk0k2": {
        "name": "Alice",
        "description": "Clear and engaging, friendly woman with a British accent."
    },
    "EXAVITQu4vr4xnSDxMaL": {
        "name": "Bella",
        "description": "American female voice - Youthful and engaging"
    },
    "ErXwobaYiN019PkySvjV": {
        "name": "Antoni",
        "description": "American male voice - Well-rounded and versatile"
    },
    "MF3mGyEYCl7XYWbV9V6O": {
        "name": "Elli",
        "description": "American female voice - Emotional and expressive"
    },
    "TxGEqnHWrfWFTfGW9XjX": {
        "name": "Josh",
        "description": "American male voice - Deep and resonant"
    },
    "VR6AewLTigWG4xSOukaG": {
        "name": "Arnold",
        "description": "American male voice - Crisp and clear"
    }
}

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

Delineate which criteria apply overall and which apply to a specific questions. Do not include any preamble.
Format as:
☐ Criterion # (Overall or Q1/2/etc.) Criterion

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
        criteria_list = []
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line contains a criterion
            is_criterion = False
            criterion = line
            
            # Handle various bullet/checkbox formats
            if '□' in line or '☐' in line or '☑' in line or '✓' in line:
                criterion = line.replace('□', '').replace('☐', '').replace('☑', '').replace('✓', '').strip()
                is_criterion = True
            elif line.startswith(('-', '•', '*', '+')):
                criterion = line[1:].strip()
                is_criterion = True
            elif line[0:2] in ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.'] or line[0:3] in ['10.', '11.', '12.']:
                # Handle numbered lists
                criterion = line.split('.', 1)[1].strip() if '.' in line else line
                is_criterion = True
            elif len(line) > 10 and ('student' in line.lower() or 'demonstrate' in line.lower() or 
                                   'shows' in line.lower() or 'provides' in line.lower() or 
                                   'explains' in line.lower() or 'uses' in line.lower()):
                # Fallback for criterion-like content without explicit formatting
                is_criterion = True
            
            if is_criterion and criterion and len(criterion) > 5:
                # Remove any remaining formatting artifacts
                criterion = criterion.replace('**', '').replace('__', '').strip()
                if criterion and not criterion.endswith(':'):
                    criteria_list.append(criterion)
                    
        return criteria_list
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
    
    # Get selected voice from session state, default to Daniel if not set
    selected_voice_id = st.session_state.get('selected_voice_id', 'onwK4e9ZLuTAKqWW03F9')
    
    try:
        client = ElevenLabs(api_key=api_key)
        
        # Generate speech using flash-v25 model with selected voice
        audio = client.text_to_speech.convert(
            text=text,
            model_id="eleven_flash_v2_5",
            voice_id=selected_voice_id
        )
        
        # Convert generator to bytes
        audio_bytes = b""
        for chunk in audio:
            audio_bytes += chunk
            
        return audio_bytes
            
    except Exception as e:
        st.error(f"Error generating speech: {str(e)}")
        return None

def transcribe_audio(audio_file):
    """Transcribe audio to text using ElevenLabs Scribe"""
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        st.error("Please set ELEVENLABS_API_KEY environment variable")
        return None
    
    try:
        client = ElevenLabs(api_key=api_key)
        
        # Reset file pointer to beginning
        audio_file.seek(0)
        
        # Transcribe audio using ElevenLabs Scribe
        transcript = client.speech_to_text.convert(
            file=audio_file
        )
        
        return transcript.text
    except Exception as e:
        st.error(f"Error transcribing audio: {str(e)}")
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
            
            # Voice selection
            st.write("**Voice Selection:**")
            
            # Initialize default voice in session state if not exists
            if 'selected_voice_id' not in st.session_state:
                st.session_state.selected_voice_id = "onwK4e9ZLuTAKqWW03F9"  # Default to Daniel
            
            # Create voice options for selectbox
            voice_options = []
            voice_labels = []
            for voice_id, voice_info in AVAILABLE_VOICES.items():
                voice_options.append(voice_id)
                voice_labels.append(f"{voice_info['name']} - {voice_info['description']}")
            
            # Get current index for selectbox
            current_index = voice_options.index(st.session_state.selected_voice_id) if st.session_state.selected_voice_id in voice_options else 0
            
            selected_voice_index = st.selectbox(
                "Choose a voice:",
                options=range(len(voice_options)),
                format_func=lambda x: voice_labels[x],
                index=current_index,
                key="voice_selector"
            )
            
            # Update session state with selected voice
            st.session_state.selected_voice_id = voice_options[selected_voice_index]
            
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
        
        # Speech-to-Text Section
        st.header("🎤 Speech-to-Text")
        st.write("Record audio directly or upload a file of student responses to transcribe to text using AI.")
        
        # Audio input options
        audio_option = st.radio(
            "Choose audio input method:",
            options=["Record Audio", "Upload File"],
            horizontal=True
        )
        
        audio_to_transcribe = None
        audio_source = ""
        
        if audio_option == "Record Audio":
            # Direct audio recording
            recorded_audio = st.audio_input("Record your response:")
            if recorded_audio is not None:
                audio_to_transcribe = recorded_audio
                audio_source = "recorded_audio"
                st.write("**Recorded Audio:**")
                st.audio(recorded_audio)
        
        else:  # Upload File
            # Audio file upload
            uploaded_audio = st.file_uploader(
                "Choose an audio file",
                type=['mp3', 'wav', 'm4a', 'flac', 'ogg', 'webm'],
                help="Upload audio in MP3, WAV, M4A, FLAC, OGG, or WebM format"
            )
            if uploaded_audio is not None:
                audio_to_transcribe = uploaded_audio
                audio_source = uploaded_audio.name.split('.')[0]
                st.write("**Uploaded Audio:**")
                st.audio(uploaded_audio)
        
        if audio_to_transcribe is not None:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔤 Transcribe Audio", type="primary"):
                    with st.spinner("Transcribing audio..."):
                        transcript = transcribe_audio(audio_to_transcribe)
                        
                        if transcript:
                            st.session_state.transcript = transcript
                            st.success("Audio transcribed successfully!")
                        else:
                            st.error("Failed to transcribe audio. Please try again.")
            
            with col2:
                if st.button("🗑️ Clear Transcript"):
                    if 'transcript' in st.session_state:
                        del st.session_state.transcript
                    st.rerun()
            
            # Display transcript
            if 'transcript' in st.session_state:
                st.subheader("Transcribed Text")
                st.text_area(
                    "Transcript:",
                    value=st.session_state.transcript,
                    height=150,
                    help="Transcribed text from the audio file"
                )
                
                # Option to download transcript
                st.download_button(
                    label="📥 Download Transcript",
                    data=st.session_state.transcript,
                    file_name=f"transcript_{audio_source}.txt",
                    mime="text/plain"
                )

def display_rubric():
    """Display generated rubric with editing capabilities"""
    if 'rubric_criteria' in st.session_state:
        st.header("Evaluation Rubric")
        
        # Initialize editing state
        if 'editing_rubric' not in st.session_state:
            st.session_state.editing_rubric = False
        
        # Toggle between view and edit modes
        col1, col2 = st.columns([1, 3])
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
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("💾 Save Changes", type="primary"):
                    # Filter out empty criteria
                    filtered_criteria = [c for c in st.session_state.editing_criteria if c.strip()]
                    
                    st.session_state.rubric_criteria = filtered_criteria
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
            
            for criterion in st.session_state.rubric_criteria:
                st.write(f"☐ {criterion}")
            
            # Option to download rubric
            rubric_lines = [f"☐ {criterion}" for criterion in st.session_state.rubric_criteria]
            rubric_text = '\n'.join(rubric_lines)
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

Delineate which criteria apply overall and which apply to a specific questions. Do not include any preamble.
Format as:
☐ Criterion # (Overall or Q1/2/etc.) Criterion

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
                rubric_criteria = generate_rubric(topic, all_questions, st.session_state.rubric_prompt)
                if rubric_criteria:
                    st.session_state.rubric_criteria = rubric_criteria
                    st.success(f"Generated rubric with {len(rubric_criteria)} criteria!")
                else:
                    st.error("Failed to generate rubric. Please check your API key and prompt.")
    
    display_rubric()
    
    display_voice_interface()
