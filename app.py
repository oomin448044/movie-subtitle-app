import streamlit as st
import google.generativeai as genai
import os
import tempfile
import time
import re
from moviepy import VideoFileClip, TextClip, ColorClip, CompositeVideoClip
from pytubefix import YouTube

# Page configuration
st.set_page_config(page_title="Web (2): Movie Subtitle App", layout="wide")

st.title("🎬 Web (2): Movie Subtitle App")
st.markdown("Video ထဲက မူရင်းစကားပြောတွေကို **မြန်မာစာတန်းထိုး** အဖြစ် ပြောင်းလဲပေးပါတယ်။")

# Sidebar for Settings
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Enter Gemini API Key:", type="password")
    st.info("API Key မရှိသေးရင် VPN ဖွင့်ပြီး [Google AI Studio](https://aistudio.google.com/app/apikey) မှာ ယူပါ။")

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
                video_path = stream.download(output_path=tempfile.gettempdir())
                st.video(video_path)
            except Exception as e:
                st.error(f"YouTube Download Error: {e}")

with tab2:
    video_file = st.file_uploader("Upload Video (Max 500MB):", type=["mp4", "mov", "avi"])
    if video_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
            tmp_video.write(video_file.read())
            video_path = tmp_video.name
        st.video(video_path)

if video_path and api_key:
    if st.button("Generate Subtitled Video"):
        with st.spinner("AI က Video ကိုကြည့်ပြီး မြန်မာစာတန်းထိုးများ ထုတ်ပေးနေပါတယ်..."):
            try:
                genai.configure(api_key=api_key)
                
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
                
                model = genai.GenerativeModel('models/gemini-1.5-flash', safety_settings=safety_settings)
                
                video_file_ai = genai.upload_file(path=video_path)
                while video_file_ai.state.name == "PROCESSING":
                    time.sleep(2)
                    video_file_ai = genai.get_file(video_file_ai.name)
                
                prompt = """
                Analyze this video carefully. Act as a professional Movie Translator.
                
                Translate the original dialogue and narration into BURMESE language.
                - Use natural, spoken Burmese.
                - Format: [start_time - end_time] Burmese Translation
                - Ensure the timing is precise with the speech in the video.
                """
                
                response = model.generate_content([video_file_ai, prompt])
                
                if not response.candidates:
                    st.error("AI က ဒီ Video ကို ပိတ်ပင်ထားပါတယ် (Blocked)။")
                else:
                    subtitle_script = response.text
                    st.subheader("Generated Subtitles:")
                    st.write(subtitle_script)
                    
                    # Process Video
                    video_clip = VideoFileClip(video_path)
                    video_duration = video_clip.duration
                    
                    lines = subtitle_script.strip().split('\n')
                    subtitle_clips = []
                    
                    for line in lines:
                        match = re.search(r'\[(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\]\s*(.*)', line)
                        if match:
                            start_str, end_str, text = match.groups()
                            start_sec = int(start_str.split(':')[0]) * 60 + int(start_str.split(':')[1])
                            end_sec = int(end_str.split(':')[0]) * 60 + int(end_str.split(':')[1])
                            
                            # Cap timing to video duration
                            start_sec = min(start_sec, video_duration)
                            end_sec = min(end_sec, video_duration)
                            
                            if text.strip() and start_sec < end_sec:
                                duration = end_sec - start_sec
                                
                                # Create Black Bar to cover original subtitles
                                bar_height = int(video_clip.h * 0.12)
                                black_bar = (ColorClip(size=(video_clip.w, bar_height), color=(0, 0, 0))
                                            .with_duration(duration)
                                            .with_position(('center', video_clip.h - bar_height - 10))
                                            .with_start(start_sec)
                                            .with_opacity(0.8))
                                
                                # Create Burmese Subtitle Text
                                txt_clip = (TextClip(text=text, font="Arial", font_size=24, color='white', method='caption', size=(video_clip.w * 0.8, None))
                                           .with_duration(duration)
                                           .with_position(('center', video_clip.h - bar_height - 5))
                                           .with_start(start_sec))
                                
                                subtitle_clips.extend([black_bar, txt_clip])
                    
                    if subtitle_clips:
                        final_video = CompositeVideoClip([video_clip] + subtitle_clips)
                    else:
                        final_video = video_clip
                    
                    output_video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                    final_video.write_videofile(output_video_path, codec="libx264", audio_codec="aac", temp_audiofile="temp-audio.m4a", remove_temp=True)
                    
                    st.success("✅ Subtitled Video Processing Complete!")
                    st.video(output_video_path)
                    with open(output_video_path, "rb") as f:
                        st.download_button("⬇️ Download Subtitled Video (MP4)", f, "my_subtitled_movie.mp4", "video/mp4")
                    
                    video_clip.close()
                
                genai.delete_file(video_file_ai.name)
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
elif not api_key and video_path:
    st.warning("⚠️ Please enter your API Key in the sidebar.")
