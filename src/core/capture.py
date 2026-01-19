import mss
import mss.tools
from PIL import Image
import os

class ScreenCapture:
    def __init__(self):
        self.sct = mss.mss()

    def capture_screen(self, monitor_index: int = 1) -> Image.Image:
        """
        Captura la pantalla completa.
        Soporta: MSS (Nativo Linux/Windows), System Fallback (scrot/gnome-screenshot) y WSL2 (PowerShell).
        """
        try:
            # Intento 1: MSS (Rápido y eficiente para Linux nativo / Windows nativo)
            # En WSL, esto fallará con XGetImage error porque no hay X11 display real del host.
            monitor = self.sct.monitors[0]
            sct_img = self.sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return img
            
        except Exception as e:
            # Detectar si estamos en WSL
            is_wsl = "microsoft" in os.uname().release.lower()
            
            if is_wsl:
                print(f"Warning: MSS failed in WSL ({e}). Trying PowerShell interop...")
                return self._capture_wsl_powershell()
            
            print(f"Warning: MSS capture failed ({e}). Trying system fallback...")
            
            # Intento 2: Fallback para Linux nativo (Wayland/X11 restringido)
            return self._capture_linux_fallback()

    def _capture_wsl_powershell(self) -> Image.Image:
        """
        Usa PowerShell desde WSL para capturar la pantalla de Windows.
        Requiere que powershell.exe esté en el PATH (estándar en WSL).
        """
        temp_path = "/tmp/wsl_capture.png"
        
        # Obtener ruta de Windows para el archivo temporal
        try:
            # En WSL2, \\wsl.localhost\ubuntu\tmp puede dar problemas de permisos con System.Drawing
            # Es MUCHO más seguro guardar en el sistema de archivos de Windows (ej. %TEMP%) y luego copiar/leer.
            win_temp_dir = os.popen("cmd.exe /c echo %TEMP%").read().strip()
            win_temp_path = os.path.join(win_temp_dir, "pixelsense_capture.png")
            
            # Convertir la ruta de Windows a ruta WSL para leerla después
            # Ej: C:\Users\Johan\AppData\Local\Temp -> /mnt/c/Users/Johan/AppData/Local/Temp
            wsl_read_path = os.popen(f"wslpath -u \"{win_temp_dir}\"").read().strip() + "/pixelsense_capture.png"
            
        except Exception as e:
            # Fallback extremo: C:\Temp
            win_temp_path = r"C:\Temp\pixelsense_capture.png"
            wsl_read_path = "/mnt/c/Temp/pixelsense_capture.png"
            os.system("powershell.exe -Command \"New-Item -ItemType Directory -Force -Path C:\\Temp\"")

        # Escapar backslashes para el string de PowerShell
        win_temp_path_escaped = win_temp_path.replace("\\", "\\\\")

        # Script de PowerShell para capturar pantalla completa
        # Nota: [System.Windows.Forms] requiere cargar el assembly explícitamente
        ps_script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen
        $bitmap = New-Object System.Drawing.Bitmap $screen.Bounds.Width, $screen.Bounds.Height
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($screen.Bounds.X, $screen.Bounds.Y, 0, 0, $bitmap.Size)
        
        $bitmap.Save('{win_temp_path_escaped}')
        $graphics.Dispose()
        $bitmap.Dispose()
        """
        
        # Ejecutar PowerShell
        # Usamos subprocess para capturar stderr si falla
        import subprocess
        try:
            # -NonInteractive -NoProfile para evitar bloqueos
            cmd = ["powershell.exe", "-NonInteractive", "-NoProfile", "-Command", ps_script]
            
            # Definir un directorio de trabajo seguro en Windows para evitar warnings de rutas UNC
            # Usamos /mnt/c/Temp si existe, o /mnt/c/Windows/Temp
            safe_cwd = "/mnt/c/Temp" if os.path.exists("/mnt/c/Temp") else "/mnt/c/Windows/Temp"
            
            # Asegurarse de que el directorio existe
            if not os.path.exists(safe_cwd):
                 # Si no existe, usamos el home de Windows (ej /mnt/c/Users/Johan)
                 # Intentamos detectar el usuario actual de Windows
                 try:
                     win_user = os.popen("cmd.exe /c echo %USERNAME%").read().strip()
                     safe_cwd = f"/mnt/c/Users/{win_user}"
                 except:
                     pass

            # En Windows (y WSL interop), la salida puede venir en cp1252 o utf-16, no siempre utf-8.
            # Usamos errors='replace' para evitar crasheos por tildes o caracteres raros en mensajes de error.
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding='cp1252', 
                errors='replace',
                cwd=safe_cwd  # Ejecutar desde un dir de Windows para evitar "CMD.EXE ... UNC path" warning
            )
            
            # Filtrar el warning de UNC path de la salida si ocurre (aunque cwd=safe_cwd debería evitarlo)
            if "CMD.EXE" in result.stderr and "UNC" in result.stderr:
                 # Es solo un warning del shell, no un error real si el script corrió
                 pass
            elif result.returncode != 0:
                 print(f"PowerShell Error: {result.stderr}")
                 raise Exception(f"PowerShell execution failed: {result.stderr}")

        except FileNotFoundError:
             raise Exception("powershell.exe not found in PATH")

        # Leer la imagen desde la ruta WSL
        if os.path.exists(wsl_read_path):
            try:
                img = Image.open(wsl_read_path).convert("RGB")
                return img
            except Exception as e:
                raise Exception(f"Failed to load captured image from {wsl_read_path}: {e}")
        
        raise Exception(f"WSL PowerShell capture failed. Image not found at {wsl_read_path} (Windows path: {win_temp_path})")

    def _capture_linux_fallback(self) -> Image.Image:
        # Usamos gnome-screenshot o scrot si están disponibles
        fallback_filename = "/tmp/pixelsense_capture_fallback.png"
        
        try:
            # Intentar gnome-screenshot (común en Ubuntu/Debian/Fedora modernos)
            ret = os.system(f"gnome-screenshot -f {fallback_filename}")
            if ret != 0:
                    # Intentar scrot (más ligero, común en otros entornos)
                    ret = os.system(f"scrot {fallback_filename}")
            
            if ret == 0 and os.path.exists(fallback_filename):
                img = Image.open(fallback_filename).convert("RGB")
                return img
            else:
                raise Exception("System fallback tools (gnome-screenshot, scrot) failed or not installed.")
                
        except Exception as e2:
            raise Exception(f"Critical: All capture methods failed. System: {e2}")
