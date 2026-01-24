import cv2
import os
import logging
import yt_dlp

logger = logging.getLogger(__name__)

def select_roi_from_video(video_path):
    """
    Abre el primer frame del video y permite al usuario seleccionar una región de interés (ROI).
    Retorna (x, y, w, h).
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise ValueError("Could not read the first frame of the video.")

    print("\nControls:\n- Draw a rectangle with the mouse.\n- Press SPACE or ENTER to confirm.\n- Press c to cancel selection.")
    
    # Abrir ventana para seleccionar ROI
    # cv2.selectROI es una función nativa muy útil para esto
    # showCrosshair=True muestra una cruz para guiar
    # fromCenter=False permite dibujar desde una esquina
    roi = cv2.selectROI("Select Focus Area (HUD)", frame, showCrosshair=True, fromCenter=False)
    
    # Cerrar ventana
    cv2.destroyAllWindows()
    
    # roi es una tupla (x, y, w, h)
    # Si el usuario cancela, suele devolver (0,0,0,0)
    if roi == (0, 0, 0, 0):
        print("Selection cancelled.")
        return None
        
    print(f"ROI selected: {roi}")
    return roi

def create_focus_crop(video_path, output_path, roi, start_time=None, end_time=None):
    """
    Recorta el video basado en el ROI seleccionado y opcionalmente un rango de tiempo.
    Usa OpenCV para leer y escribir, lo cual es eficiente para recortes simples.
    """
    x, y, w, h = roi
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Could not open video.")

    # Obtener propiedades del video original
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Configurar escritor de video
    # Usamos mp4v como codec genérico
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
    
    # Calcular frames de inicio y fin si se especifican tiempos
    start_frame = 0
    end_frame = total_frames
    
    if start_time is not None:
        start_frame = int(start_time * fps)
    if end_time is not None:
        end_frame = int(end_time * fps)
        
    # Moverse al frame inicial
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    current_frame = start_frame
    print(f"Processing crop... {output_path}")
    
    while cap.isOpened() and current_frame < end_frame:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Recortar
        # Nota: frame es numpy array [y:y+h, x:x+w]
        crop_frame = frame[y:y+h, x:x+w]
        
        # Escribir
        out.write(crop_frame)
        
        current_frame += 1
        
    cap.release()
    out.release()
    print("Crop created successfully.")
    return output_path

def get_video_duration(video_path):
    """Obtiene la duración del video usando cv2."""
    try:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        duration = frame_count / fps
        cap.release()
        return duration
    except ImportError:
        logger.warning("OpenCV not found, using default duration estimation.")
        return 10.0
    except Exception as e:
        logger.warning(f"Could not determine video duration: {e}")
        return 10.0

def download_video(url: str, output_path: str = "temp_video.mp4") -> str:
    """Descarga un video desde una URL usando yt-dlp."""
    if os.path.exists(output_path):
        os.remove(output_path)
        
    ydl_opts = {
        'format': 'best[ext=mp4]',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
    }
    
    logger.info(f"Downloading video from {url}...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    return os.path.abspath(output_path)

def extract_frames(video_path: str, output_dir: str, num_frames: int = 100) -> list:
    """
    Extracts N evenly spaced frames from the video and saves them to the output directory.
    Returns a list of filenames.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Could not open video.")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Handle cases where frame count is not available
    if total_frames <= 0:
        logger.warning("Could not determine total frames.")
        # Try to read one frame to check if video is valid at least
        ret, _ = cap.read()
        if not ret:
             cap.release()
             raise ValueError("Video seems empty or invalid.")
        # If we can't get total frames easily, we might just read sequentially (inefficient for long videos but safe)
        # For now, let's assume we can get it or fail.
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    step = max(1, total_frames // num_frames)
    
    saved_files = []
    
    for i in range(num_frames):
        frame_idx = i * step
        if frame_idx >= total_frames:
            break
            
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if ret:
            filename = f"frame_{i:03d}.jpg"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, frame)
            saved_files.append(filename)
            
    cap.release()
    return saved_files
