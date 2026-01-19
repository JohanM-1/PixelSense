import os
import argparse
import logging
import json
import sys

# Add project root to path so src can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.video_processing import download_video, select_roi_from_video, get_video_duration
from src.analysis.pipeline import VideoAnalyzer

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    print("\n🎬 PixelSense Video Analysis Tool (Sliding Window Mode)")
    print("======================================================")
    
    parser = argparse.ArgumentParser(description="PixelSense Video Analysis Tool")
    parser.add_argument("video_path", nargs="?", help="URL del video o ruta local del archivo")
    parser.add_argument("--detail", "-d", default="medium", choices=["low", "medium", "high", "max"], help="Nivel de detalle del análisis")
    args = parser.parse_args()

    # Selección de video
    if args.video_path:
        video_source = args.video_path
        detail_level = args.detail
    else:
        video_source = input("\nIngrese la URL del video o la ruta local del archivo: ").strip()
        detail_level = input("Nivel de detalle (low/medium/high/max) [medium]: ").strip() or "medium"
    
    video_path = ""
    if video_source.startswith("http"):
        try:
            video_path = download_video(video_source)
        except Exception as e:
            logger.error(f"Error descargando video: {e}")
            return
    else:
        video_path = os.path.abspath(video_source)
        if not os.path.exists(video_path):
            logger.error(f"El archivo {video_path} no existe.")
            return

    logger.info(f"Video ready at: {video_path}")
    
    # === ROI SELECTION (Optional Focus) ===
    # En modo no interactivo (si se corre por CLI sin input), esto podría fallar si se espera input.
    # Pero el script original usaba input(), así que lo mantenemos.
    # Si args.video_path se pasó, asumimos que puede ser interactivo a menos que se modifique.
    # Para mantener compatibilidad exacta, preguntamos.
    
    # Check if running in a non-interactive mode or just ask as before.
    # Use try-except for EOFError just in case input is piped.
    use_focus = False
    try:
        use_focus = input("Do you want to select a HUD focus area? (y/n) [n]: ").lower().strip() == 'y'
    except EOFError:
        pass

    roi = None
    if use_focus:
        try:
            print("Opening video for ROI selection...")
            roi = select_roi_from_video(video_path)
            if roi:
                print(f"HUD Focus Area Selected: {roi}")
        except Exception as e:
            logger.error(f"Failed to select ROI: {e}")

    # Obtener duración para segmentar (Solo para mostrar info)
    duration = get_video_duration(video_path)
    print(f"📹 Video Duration: {duration:.2f}s")
    
    # Initialize Analyzer
    analyzer = VideoAnalyzer()
    
    print(f"✂️  Starting analysis with detail level: {detail_level}")
    
    # Run Analysis
    final_json, segment_results = analyzer.analyze_video(video_path, detail=detail_level, roi=roi)
    
    if final_json:
        print("\n✅ Final Analysis Result:\n")
        print(final_json)
        
        with open("video_analysis_result.json", "w") as f:
            f.write(final_json)
            print("\nResult saved to video_analysis_result.json")

        # Guardar logs crudos
        logs_data = {
            "detail_level": detail_level,
            "video_duration": duration,
            "segments": segment_results
        }
        with open("analysis_logs.json", "w") as f:
            json.dump(logs_data, f, indent=2)
            print("Raw logs saved to analysis_logs.json")
    else:
        print("Analysis failed.")

    # Limpieza
    if video_source.startswith("http") and os.path.exists(video_path):
        os.remove(video_path)
        logger.info("Temporary video file removed.")

if __name__ == "__main__":
    main()
