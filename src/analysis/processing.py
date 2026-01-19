import json
import re

def map_detail_to_params(detail: str):
    """
    Mapea nivel de detalle a parámetros de muestreo y longitud de salida.
    """
    detail = (detail or "medium").lower()
    if detail in ["low", "bajo"]:
        # Análisis rápido: 1 segmento largo, pocos frames
        return {"fps": 1.0, "max_tokens": 1024, "max_pixels": 480 * 480, "segment_duration": 5}
    if detail in ["medium", "medio"]:
        # Análisis estándar: segmentos de 5s
        return {"fps": 2.0, "max_tokens": 1024, "max_pixels": 720 * 720, "segment_duration": 4}
    if detail in ["high", "alto"]:
        # Análisis detallado: segmentos de 3s
        return {"fps": 1.0, "max_tokens": 1024, "max_pixels": 720 * 720, "segment_duration": 3}
    if detail in ["max", "máximo", "maximo"]:
        # Análisis cuadro a cuadro (casi): segmentos de 2s
        return {"fps": 2.0, "max_tokens": 1024, "max_pixels": 720 * 720, "segment_duration": 2}
    return {"fps": 1.0, "max_tokens": 1024, "max_pixels": 480 * 480, "segment_duration": 5}

def clean_events(events):
    """
    Limpia la lista de eventos:
    1. Elimina duplicados inteligentes (misma key/acción en un intervalo de 1s).
       - Prioriza eventos con descripción más detallada.
    2. Filtra eventos "None" o vacíos a menos que tengan descripción relevante.
    3. Sanitiza nombres y elimina placeholders genéricos.
    """
    cleaned = []
    
    last_event_time = -1.0
    last_key = None
    last_event_data = None
    
    def parse_time(ts_str):
        try:
            parts = ts_str.split(':')
            return float(parts[0]) * 60 + float(parts[1])
        except:
            return 0.0

    def sanitize_text(text):
        if not text: return "Unknown"
        # Eliminar placeholders comunes del prompt
        placeholders = ["Skill Name (if known)", "Skillshot/Point-Click/Self-Buff/Dash"]
        for p in placeholders:
            if p.lower() in text.lower():
                return "Unknown"
        return re.sub(r'[^\x00-\x7F]+', '', text).strip()
        
    def is_better_event(new_event, old_event):
        # Criterios para decidir si el nuevo evento es mejor que el anterior (si son duplicados)
        new_desc = new_event.get("action", "")
        old_desc = old_event.get("action", "")
        
        # 1. Preferir si tiene nombre de skill real
        new_skill_name = new_event.get("skill_used", {}).get("name", "Unknown")
        old_skill_name = old_event.get("skill_used", {}).get("name", "Unknown")
        
        if new_skill_name != "Unknown" and old_skill_name == "Unknown":
            return True
            
        # 2. Preferir descripción más larga
        if len(new_desc) > len(old_desc):
            return True
            
        # 3. Preferir si tiene intención táctica definida
        new_intent = new_event.get("tactical_intent", "None")
        old_intent = old_event.get("tactical_intent", "None")
        if new_intent != "None" and old_intent == "None":
            return True
            
        return False

    for event in events:
        # 1. Filtrar None irrelevantes
        skill = event.get("skill_used", {})
        key = skill.get("key", "None")
        action = event.get("action", "")
        
        if key == "None" and ("standing" in action.lower() or "menu" in action.lower()):
            continue
            
        # 2. Sanitizar
        if "name" in skill:
            skill["name"] = sanitize_text(skill["name"])
        if "type" in skill:
             skill["type"] = sanitize_text(skill["type"])
        if "action" in event:
            event["action"] = sanitize_text(event["action"])
            
        # 3. Deduplicación inteligente
        current_time = parse_time(event.get("timestamp", "00:00"))
        
        is_duplicate = False
        if key != "None" and key == last_key and (current_time - last_event_time) < 1.0:
            is_duplicate = True
            
        if is_duplicate:
            # Si es duplicado, ver si el nuevo es mejor para reemplazar al anterior
            if is_better_event(event, last_event_data):
                # Reemplazar el último evento en la lista limpia
                cleaned[-1] = event
                last_event_data = event
                # No actualizamos last_event_time para mantener la ventana de bloqueo desde el primer evento
        else:
            # No es duplicado, agregar
            cleaned.append(event)
            if key != "None":
                last_event_time = current_time
                last_key = key
                last_event_data = event
            
    return cleaned

def merge_results(segment_results, total_duration, params):
    """Combina los resultados de múltiples segmentos en un reporte final."""
    
    all_events = []
    for res in segment_results:
        if "events" in res:
            all_events.extend(res["events"])
    
    # Limpieza post-procesamiento
    cleaned_events = clean_events(all_events)
            
    # Crear estructura final
    final_report = {
        "summary": "Full match analysis generated from sequential segments.",
        "tactical_analysis": {
            "game_phase": "Calculated from aggregate",
            "total_events": len(cleaned_events)
        },
        "segments": [
            {
                "start": "00:00",
                "end": f"{int(total_duration//60):02d}:{int(total_duration%60):02d}",
                "title": "Full Match Timeline",
                "events": cleaned_events
            }
        ],
        "metrics": {
            "fps": params["fps"],
            "detail": params.get("segment_duration", "unknown"),
            "processed_segments": len(segment_results)
        }
    }
    return json.dumps(final_report, indent=2)
