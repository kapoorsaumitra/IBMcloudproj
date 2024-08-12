import streamlit as st
import os
import requests
from dotenv import load_dotenv
import speech_recognition as sr
import google.generativeai as genai
import pyaudio
import wave
import tempfile
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()

# Get the API keys from environment variables
api_key = os.getenv("GOOGLE_API_KEY")
ibm_api_key = os.getenv("IBM_API_KEY")
ibm_url = os.getenv("IBM_URL")

def speech_to_text():
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    RECORD_SECONDS = 5  # You can adjust this value

    p = pyaudio.PyAudio()

    st.write("Please speak after clicking the 'Start Recording' button.")
    if st.button("Start Recording"):
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)

        st.write("Recording...")

        frames = []

        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(data)

        st.write("Recording finished.")

        stream.stop_stream()
        stream.close()
        p.terminate()

        # Save the recorded audio to a temporary WAV file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
            wf = wave.open(tmpfile.name, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            audio_file = tmpfile.name

        # Use speech recognition on the temporary file
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_file) as source:
            audio = recognizer.record(source)
        
        try:
            text = recognizer.recognize_google(audio)
            st.write("You said: " + text)
            return text
        except sr.UnknownValueError:
            st.write("Sorry, I could not understand the audio.")
            return ""
        except sr.RequestError as e:
            st.write("Could not request results; {0}".format(e))
            return ""
        finally:
            # Clean up the temporary file
            os.unlink(audio_file)

    return ""

def generate_content(text):
    # Configure the Generative AI model with API key
    genai.configure(api_key=api_key)

    # Initialize the GenerativeModel
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Generate content based on the text read from the file
    response = model.generate_content(
        f"You are a sophisticated voice assistant AI named Wall-E. Your role is to provide clear, concise, and helpful responses based on the following input. Ensure your responses are accurate, friendly, and professional. The input is: {text}"
    )

    return response.text


def generate_audio_from_text(text):
    headers = {
        "Content-Type": "application/json",
        "Accept": "audio/wav"
    }
    
    data = {
        "text": text
    }
    
    try:
        logging.info(f"Sending request to IBM TTS API: {ibm_url}")
        response = requests.post(
            f"{ibm_url}/v1/synthesize?voice=en-US_MichaelV3Voice",
            headers=headers,
            auth=("apikey", ibm_api_key),
            json=data,
            timeout=30  # Add a timeout to prevent indefinite waiting
        )
        
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Save the audio content to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
            tmpfile.write(response.content)
            logging.info(f"Audio saved to temporary file: {tmpfile.name}")
            return tmpfile.name
    except requests.exceptions.RequestException as e:
        logging.error(f"Error in IBM TTS API request: {str(e)}")
        st.error(f"An error occurred while generating audio: {str(e)}")
        return None
    
def main():
    st.title("Wall-E: Your Virtual Assistant")
    st.write("Welcome! I'm here to assist you. What would you like to do?")

    text = speech_to_text()
    
    if text:
        with st.spinner("Generating response..."):
            content = generate_content(text)
        
        st.write("Wall-E's response:")
        st.write(content)
        
        with st.spinner("Generating audio..."):
            audio_filename = generate_audio_from_text(content)
        
        if audio_filename:
            try:
                st.audio(audio_filename, format="audio/wav")
            except Exception as e:
                logging.error(f"Error playing audio: {str(e)}")
                st.error("An error occurred while playing the audio. Please try again.")
            finally:
                # Clean up the audio file after playing
                os.unlink(audio_filename)
        else:
            st.warning("Audio generation failed. Please try again or use text input.")

    # Add a text input for manual queries
    user_input = st.text_input("Or type your question here:")
    if user_input:
        with st.spinner("Generating response..."):
            content = generate_content(user_input)
        
        st.write("Wall-E's response:")
        st.write(content)
        
        with st.spinner("Generating audio..."):
            audio_filename = generate_audio_from_text(content)
        
        if audio_filename:
            try:
                st.audio(audio_filename, format="audio/wav")
            except Exception as e:
                logging.error(f"Error playing audio: {str(e)}")
                st.error("An error occurred while playing the audio. Please try again.")
            finally:
                # Clean up the audio file after playing
                os.unlink(audio_filename)
        else:
            st.warning("Audio generation failed. Please try again.")

    # Add a sidebar with additional information
    st.sidebar.title("About Wall-E")
    st.sidebar.write("Wall-E is a sophisticated virtual assistant powered by advanced AI technologies. It can understand your speech, generate helpful responses, and even speak back to you using IBM Watson Text-to-Speech!")
    st.sidebar.image("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS2cCPtWbCTCwBMYJYtv5X7IGmljs-p8EV0Qg&s")
    # Add a fun fact or tip in the sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("Did you know?")
    st.sidebar.write("Wall-E's name is inspired by the lovable robot from the Pixar movie. Just like the movie character, our Wall-E is here to help and make your life easier!")

if __name__ == "__main__":
    main()