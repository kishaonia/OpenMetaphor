import subprocess
import sys

def extract_audio_from_video(video_file_path, output_audio_path="output_audio.mp3"):
    """Extracts audio from a video file and saves it as an MP3."""
    
    # Command to extract audio from video
    cmd = ['ffmpeg', '-i', video_file_path, '-q:a', '0', '-map', 'a', output_audio_path]
    
    # Execute the command
    try:
        subprocess.run(cmd, check=True)
        print(f"Audio extracted successfully to {output_audio_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract_audio.py <video_file_path> <output_audio_path>")
        sys.exit(1)
    
    video_file_path = sys.argv[1]
    output_audio_path = sys.argv[2]
    
    extract_audio_from_video(video_file_path, output_audio_path)
