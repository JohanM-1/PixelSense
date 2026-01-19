import os
import sys
import argparse

# Add project root to path so src can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.video_processing import select_roi_from_video, create_focus_crop

def main():
    parser = argparse.ArgumentParser(description="Test Video Cropping Tool")
    parser.add_argument("video_path", help="Path to the input video")
    args = parser.parse_args()
    
    video_path = args.video_path
    output_path = "debug_crop_hud.mp4"
    
    if not os.path.exists(video_path):
        print(f"Error: Video not found at {video_path}")
        return

    print(f"Opening video: {video_path}")
    print("Please select the HUD/Skill area in the popup window.")
    
    try:
        # 1. Seleccionar ROI interactivamente
        roi = select_roi_from_video(video_path)
        
        if roi:
            # 2. Crear recorte (video completo por defecto)
            print(f"Creating full video crop using ROI: {roi}")
            # start_time=None, end_time=None procesa todo el video
            create_focus_crop(video_path, output_path, roi, start_time=None, end_time=None)
            
            print(f"\n✅ Success! Cropped video saved to: {os.path.abspath(output_path)}")
            print("Please check this file to verify it contains exactly what you want the AI to focus on.")
        else:
            print("Operation cancelled by user.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
