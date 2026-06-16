import sys
import os
import time
import json
from pathlib import Path
from tqdm import tqdm

# Add current dir to path
sys.path.insert(0, str(Path(__file__).parent))

from ocr_engine import read_chinese_mark

def run_experiment(image_folder, output_file):
    print(f"Running experiment on images in {image_folder}")
    image_paths = []
    
    # Supported image extensions
    valid_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.webp']
    
    for root, _, files in os.walk(image_folder):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in valid_exts:
                image_paths.append(os.path.join(root, file))
                
    if not image_paths:
        print("No images found!")
        return

    print(f"Found {len(image_paths)} images. Starting OCR process...")
    
    results = []
    start_time = time.time()
    
    for idx, path in enumerate(tqdm(image_paths)):
        with open(path, 'rb') as f:
            img_bytes = f.read()
            
        try:
            # Using deep_mode=True for better accuracy since this is an experiment
            res = read_chinese_mark(img_bytes, deep_mode=True)
            results.append({
                "file_name": os.path.basename(path),
                "text": res.get("text", ""),
                "confidence": res.get("confidence", 0),
                "words": res.get("words", []),
                "database_valid": res.get("database_valid", False),
                "warning": res.get("warning", ""),
                "error": None
            })
        except Exception as e:
            results.append({
                "file_name": os.path.basename(path),
                "text": "",
                "confidence": 0,
                "error": str(e)
            })
            
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Experiment completed in {duration:.2f} seconds.")
    
    # Generate report
    total = len(results)
    with_text = sum(1 for r in results if r["text"])
    valid_db = sum(1 for r in results if r.get("database_valid", False))
    avg_conf = sum(r.get("confidence", 0) for r in results if r.get("text")) / max(1, with_text)
    
    print("\n--- Summary ---")
    print(f"Total images: {total}")
    print(f"Images with text recognized: {with_text} ({(with_text/total)*100:.1f}%)")
    print(f"Images matching database: {valid_db} ({(valid_db/total)*100:.1f}%)")
    print(f"Average confidence of recognized text: {avg_conf:.1%}")
    
    # Save to file
    out_path = Path(output_file)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print(f"Results saved to {output_file}")
    
    # Generate markdown table
    md_path = out_path.with_suffix('.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# OCR Experiment Results\n\n")
        f.write(f"- **Total images:** {total}\n")
        f.write(f"- **Images with text recognized:** {with_text} ({(with_text/total)*100:.1f}%)\n")
        f.write(f"- **Images matching database:** {valid_db} ({(valid_db/total)*100:.1f}%)\n")
        f.write(f"- **Average confidence:** {avg_conf:.1%}\n\n")
        
        f.write("| File Name | Text | Match DB? | Confidence | Warning/Error |\n")
        f.write("|-----------|------|-----------|------------|---------------|\n")
        for r in results:
            err_warn = r.get("error") or r.get("warning") or "-"
            db_match = "Yes" if r.get("database_valid") else "No"
            f.write(f"| {r['file_name']} | {r['text']} | {db_match} | {r.get('confidence', 0):.2f} | {err_warn} |\n")
            
    print(f"Markdown report generated: {md_path}")

if __name__ == "__main__":
    folder = "D:\\MarkSense\\experiment_1\\ảnh thí nghiệm 1"
    output = "D:\\MarkSense\\chinese-ocr-app\\experiment_1_results.json"
    run_experiment(folder, output)
