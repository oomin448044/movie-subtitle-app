import streamlit as st
import google.generativeai as genai
import os
import tempfile
import time
import re
from moviepy import VideoFileClip, TextClip, ColorClip, CompositeVideoClip
from pytubefix import YouTube

# Page configuration
st.set_page_config(page_title="Movie Subtitle App - Burmese", layout="wide")

st.title("🎬 Movie Subtitle App")
st.markdown("Generate **Burmese subtitles** for your videos using AI. Upload a video or paste a YouTube link.")

# Sidebar for Settings
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Enter Gemini API Key:", type="password")
    st.info("Get your API key from Google AI Studio")

# Input Section
tab1, tab2 = st.tabs(["YouTube Link", "Video Upload"])

video_path = None

with tab1:
    youtube_url = st.text_input("Paste YouTube Link here:")
    if youtube_url:
        with st.spinner("Downloading YouTube video..."):
            try:
                yt = YouTube(youtube_url)
                stream = yt.streams.filter(progressive=True, file_extension='mp4').first()
                if stream:
                    video_path = stream.download(output_path=tempfile.gettempdir())
                    st.video(video_path)
                else:
                    st.error("Could not find a suitable video stream.")
            except Exception as e:
                st.error(f"YouTube Download Error: {str(e)}")

with tab2:
    video_file = st.file_uploader("Upload Video (MP4, MOV, AVI):", type=["mp4", "mov", "avi"])
    if video_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
            tmp_video.write(video_file.read())
            video_path = tmp_video.name
        st.video(video_path)

if video_path and api_key:
    if st.button("Generate Subtitled Video"):
        with st.spinner("Processing video with AI..."):
            try:
                genai.configure(api_key=api_key)
                
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
                
                model = genai.GenerativeModel('gemini-2.5-flash', safety_settings=safety_settings)
                
                st.info("Uploading video to Gemini AI...")
                video_file_ai = genai.upload_file(path=video_path)
                
                while video_file_ai.state.name == "PROCESSING":
                    time.sleep(2)
                    video_file_ai = genai.get_file(video_file_ai.name)
                
                st.success("Video uploaded successfully!")
                
                prompt = """
                Analyze this video carefully. Act as a professional Movie Translator.
                
                Translate the original dialogue and narration into BURMESE language.
                - Use natural, spoken Burmese.
                - Format: [MM:SS - MM:SS] Burmese Translation
                - Ensure the timing is precise with the speech in the video.
                - Return only the subtitles in the specified format.
                """
                
                st.info("Generating Burmese subtitles...")
                response = model.generate_content([video_file_ai, prompt])
                
                if not response.candidates or not response.text:
                    st.error("AI could not process this video.")
                else:
                    subtitle_script = response.text
                    st.subheader("Generated Subtitles:")
                    st.write(subtitle_script)
                    
                    st.info("Processing video with subtitles...")
                    video_clip = VideoFileClip(video_path)
                    video_duration = video_clip.duration
                    
                    lines = subtitle_script.strip().split('\n')
                    subtitle_clips = []
                    
                    for line in lines:
                        if not line.strip():
                            continue
                            
                        match = re.search(r'\[(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\]\s*(.*)', line)
                        if match:
                            try:
                                start_str, end_str, text = match.groups()
                                
                                start_parts = start_str.split(':')
                                end_parts = end_str.split(':')
                                
                                start_sec = int(start_parts[0]) * 60 + int(start_parts[1])
                                end_sec = int(end_parts[0]) * 60 + int(end_parts[1])
                                
                                start_sec = max(0, min(start_sec, video_duration))
                                end_sec = max(start_sec, min(end_sec, video_duration))
                                
                                if text.strip() and start_sec < end_sec:
                                    duration = end_sec - start_sec
                                    
                                    bar_height = max(1, int(video_clip.h * 0.12))
                                    black_bar = (ColorClip(size=(int(video_clip.w), bar_height), color=(0, 0, 0))
                                                .with_duration(duration)
                                                .with_position(('center', int(video_clip.h - bar_height - 10)))
                                                .with_start(start_sec)
                                                .with_opacity(0.8))
                                    
                                    subtitle_width = max(1, int(video_clip.w * 0.8))
                                    txt_clip = (TextClip(text=text, font_size=24, color='white', method='caption', size=(subtitle_width, None))
                                               .with_duration(duration)
                                               .with_position(('center', int(video_clip.h - bar_height - 5)))
                                               .with_start(start_sec))
                                    
                                    subtitle_clips.extend([black_bar, txt_clip])
                            except (ValueError, IndexError) as e:
                                st.warning(f"Skipped line: {line}")
                                continue
                    
                    if subtitle_clips:
                        final_video = CompositeVideoClip([video_clip] + subtitle_clips)
                    else:
                        st.warning("No valid subtitles found. Using original video.")
                        final_video = video_clip
                    
                    output_video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                    st.info("Rendering final video... This may take a few minutes.")
                    
                    final_video.write_videofile(
                        output_video_path, 
                        codec="libx264", 
                        audio_codec="aac"
                    )
                    
                    st.success("Video processing complete!")
                    st.video(output_video_path)
                    
                    with open(output_video_path, "rb") as f:
                        st.download_button(
                            label="Download Subtitled Video (MP4)",
                            data=f,
                            file_name="subtitled_movie.mp4",
                            mime="video/mp4"
                        )
                    
                    video_clip.close()
                
                try:
                    genai.delete_file(video_file_ai.name)
                except:
                    pass
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
                with st.expander("Error Details"):
                    import traceback
                    st.code(traceback.format_exc())
                    
elif not api_key and video_path:
    st.warning("Please enter your Gemini API Key in the sidebar.")
elif not video_path:
    st.info("Please upload a video or paste a YouTube link to get started.")
