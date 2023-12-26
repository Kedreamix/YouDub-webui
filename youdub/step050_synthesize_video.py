# -*- coding: utf-8 -*-
import json
import os
import subprocess

from loguru import logger


def split_text(input_data,
               punctuations=['，', '；', '：', '。', '？', '！', '\n', '”']):
    # Chinese punctuation marks for sentence ending

    # Function to check if a character is a Chinese ending punctuation
    def is_punctuation(char):
        return char in punctuations

    # Process each item in the input data
    output_data = []
    for item in input_data:
        start = item["start"]
        text = item["translation"]
        speaker = item.get("speaker", "SPEAKER_00")
        original_text = item["text"]
        sentence_start = 0

        # Calculate the duration for each character
        duration_per_char = (item["end"] - item["start"]) / len(text)
        for i, char in enumerate(text):
            # If the character is a punctuation, split the sentence
            if not is_punctuation(char) and i != len(text) - 1:
                continue
            if i - sentence_start < 5 and i != len(text) - 1:
                continue
            if i < len(text) - 1 and is_punctuation(text[i+1]):
                continue
            sentence = text[sentence_start:i+1]
            sentence_end = start + duration_per_char * len(sentence)

            # Append the new item
            output_data.append({
                "start": round(start, 3),
                "end": round(sentence_end, 3),
                "text": original_text,
                "translation": sentence,
                "speaker": speaker
            })

            # Update the start for the next sentence
            start = sentence_end
            sentence_start = i + 1

    return output_data
    
def format_timestamp(seconds):
    """Converts seconds to the SRT time format."""
    millisec = int((seconds - int(seconds)) * 1000)
    hours, seconds = divmod(int(seconds), 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millisec:03}"

def generate_srt(translation, srt_path, speed_up=1):
    translation = split_text(translation)
    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, line in enumerate(translation):
            start = format_timestamp(line['start']/speed_up)
            end = format_timestamp(line['end']/speed_up)
            text = line['translation']
            f.write(f'{i+1}\n')
            f.write(f'{start} --> {end}\n')
            f.write(f'{text}\n\n')
            
def convert_resolution(resolution='1080p'):
    height = int(resolution[:-1])
    width = int(height * 16 / 9)
    return f'{width}x{height}'
    
def synthesize_video(folder, subtitles=True, speed_up=1.05, fps=30, resolution='1080p'):
    if os.path.exists(os.path.join(folder, 'video.mp4')):
        logger.info(f'Video already synthesized in {folder}')
        return
    
    translation_path = os.path.join(folder, 'translation.json')
    input_audio = os.path.join(folder, 'audio_combined.wav')
    input_video = os.path.join(folder, 'download.mp4')
    
    if not os.path.exists(translation_path) or not os.path.exists(input_audio):
        return
    
    with open(translation_path, 'r', encoding='utf-8') as f:
        translation = json.load(f)
        
    srt_path = os.path.join(folder, 'subtitles.srt')
    output_video = os.path.join(folder, 'video.mp4')
    generate_srt(translation, srt_path, speed_up)
    srt_path = srt_path.replace('\\', '/')
    resolution = convert_resolution(resolution)

    video_speed_filter = f"setpts=PTS/{speed_up}"
    audio_speed_filter = f"atempo={speed_up}"
    subtitle_filter = f"subtitles={srt_path}:force_style='FontName=Arial,FontSize=20,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2,WrapStyle=2'"
    
    if subtitles:
        filter_complex = f"[0:v]{video_speed_filter},{subtitle_filter}[v];[1:a]{audio_speed_filter}[a]"
    else:
        filter_complex = f"[0:v]{video_speed_filter}[v];[1:a]{audio_speed_filter}[a]"
    ffmpeg_command = [
        'ffmpeg',
        '-i', input_video,
        '-i', input_audio,
        '-filter_complex', filter_complex,
        '-map', '[v]',
        '-map', '[a]',
        '-r', str(fps),
        '-s', resolution,
        '-c:v', 'libx264',
        '-c:a', 'aac',
        output_video,
        '-y'
    ]
    subprocess.run(ffmpeg_command)
    

def synthesize_all_video_under_folder(folder, subtitles=True, speed_up=1.05, fps=30, resolution='1080p'):
    for root, dirs, files in os.walk(folder):
        if 'download.mp4' in files and 'video.mp4' not in files:
            synthesize_video(root, subtitles=subtitles,
                             speed_up=speed_up, fps=fps, resolution=resolution)
    return f'Synthesized all videos under {folder}'
if __name__ == '__main__':
    folder = r'videos'
    synthesize_all_video_under_folder(folder, subtitles=True)
