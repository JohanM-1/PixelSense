import os
import argparse
import logging
from datasets import load_dataset
from PIL import Image
from tqdm import tqdm

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_fiftyone_gui(output_dir: str):
    """
    Downloads the FiftyOne-GUI-Grounding-Train dataset.
    This dataset typically contains 'image' (PIL) and 'ground_truth' (objects).
    """
    logger.info("Downloading FiftyOne-GUI-Grounding-Train dataset...")
    
    # Create target directory
    dataset_path = os.path.join(output_dir, "fiftyone_gui")
    os.makedirs(dataset_path, exist_ok=True)
    
    # Load from Hugging Face
    try:
        ds = load_dataset("harpreetsahota/FiftyOne-GUI-Grounding-Train", split="train")
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        return

    # Save images and metadata
    # Format: 
    #   fiftyone_gui/
    #     images/
    #     annotations.json (COCO style or custom JSON to be parsed later)
    
    images_dir = os.path.join(dataset_path, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    annotations = []
    
    logger.info(f"Processing {len(ds)} samples...")
    for i, item in tqdm(enumerate(ds), total=len(ds)):
        # 1. Save Image
        image = item.get('image')
        if not image:
            continue
            
        file_name = f"fiftyone_{i:05d}.jpg"
        image_path = os.path.join(images_dir, file_name)
        
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(image_path)
        
        # 2. Extract Annotations
        # The structure of 'ground_truth' depends on the dataset. 
        # Inspecting typical HF dataset structure: objects usually have 'bbox' and 'label'.
        # Note: Bboxes in HF are often [x, y, w, h] or [x_min, y_min, x_max, y_max].
        
        # NOTE: This is a placeholder logic. You might need to inspect `item` keys 
        # if the dataset schema differs.
        # Assuming typical 'objects' key or similar.
        # If 'ground_truth' is a string/json, parse it.
        
        # For this specific dataset, we might need to explore structure first.
        # But let's assume we dump the raw item (excluding image object) to JSON
        # so unify_datasets.py can parse it.
        
        meta = {k: v for k, v in item.items() if k != 'image'}
        meta['file_name'] = file_name
        meta['width'] = image.width
        meta['height'] = image.height
        annotations.append(meta)

    # Save all metadata to a single JSON
    with open(os.path.join(dataset_path, "raw_annotations.json"), "w") as f:
        json.dump(annotations, f, indent=2)
        
    logger.info(f"FiftyOne GUI dataset saved to {dataset_path}")

def download_showui_web(output_dir: str):
    """
    Downloads ShowUI_Web dataset.
    """
    logger.info("Downloading ShowUI_Web dataset...")
    dataset_path = os.path.join(output_dir, "showui_web")
    os.makedirs(dataset_path, exist_ok=True)
    
    try:
        ds = load_dataset("showlab/ShowUI_Web", split="train")
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        return

    images_dir = os.path.join(dataset_path, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    annotations = []
    
    logger.info(f"Processing {len(ds)} samples...")
    for i, item in tqdm(enumerate(ds), total=len(ds)):
        image = item.get('image')
        if not image: continue
        
        file_name = f"showui_{i:05d}.jpg"
        image_path = os.path.join(images_dir, file_name)
        
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(image_path)
        
        meta = {k: v for k, v in item.items() if k != 'image'}
        meta['file_name'] = file_name
        meta['width'] = image.width
        meta['height'] = image.height
        annotations.append(meta)
        
    with open(os.path.join(dataset_path, "raw_annotations.json"), "w") as f:
        json.dump(annotations, f, indent=2)
        
    logger.info(f"ShowUI dataset saved to {dataset_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", type=str, default="datasets/raw", help="Root directory for downloads")
    parser.add_argument("--dataset", type=str, choices=["all", "fiftyone", "showui"], default="all")
    args = parser.parse_args()
    
    import json # ensure imported
    
    if args.dataset in ["all", "fiftyone"]:
        download_fiftyone_gui(args.output_dir)
        
    if args.dataset in ["all", "showui"]:
        download_showui_web(args.output_dir)
