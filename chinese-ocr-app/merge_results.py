import pandas as pd
import json
import os

def create_combined_report():
    print("Loading data...")
    
    # Load System Results
    sys_path = r"D:\MarkSense\chinese-ocr-app\experiment_1_results.json"
    with open(sys_path, 'r', encoding='utf-8') as f:
        sys_data = json.load(f)
    df_sys = pd.DataFrame(sys_data)
    
    # Rename and select columns from system
    df_sys = df_sys[['file_name', 'text', 'confidence', 'database_valid', 'warning', 'error']].copy()
    df_sys.rename(columns={
        'text': 'System_Res',
        'confidence': 'System_Conf',
        'database_valid': 'System_DB_Match'
    }, inplace=True)
    
    # Load ChatGPT Results
    path_gpt = r"D:\MarkSense\thực nghiệm 1 (chat gpt).xlsx"
    df_gpt = pd.read_excel(path_gpt)
    df_gpt = df_gpt[['file_name', 'chu_han_best', 'confidence', 'notes ngắn']].copy()
    df_gpt.rename(columns={
        'chu_han_best': 'ChatGPT_Res',
        'confidence': 'ChatGPT_Conf',
        'notes ngắn': 'ChatGPT_Notes'
    }, inplace=True)
    
    # Load Gemini Results (Header is on the second row)
    path_gemini = r"D:\MarkSense\thực nghiệm 1 (gemini).xlsx"
    df_gemini = pd.read_excel(path_gemini, header=1)
    df_gemini = df_gemini[['file_name', 'chu_han_best', 'confidence', 'notes ngắn']].copy()
    df_gemini.rename(columns={
        'chu_han_best': 'Gemini_Res',
        'confidence': 'Gemini_Conf',
        'notes ngắn': 'Gemini_Notes'
    }, inplace=True)
    
    # Clean file names if necessary (sometimes they have leading/trailing spaces)
    df_sys['file_name'] = df_sys['file_name'].astype(str).str.strip()
    df_gpt['file_name'] = df_gpt['file_name'].astype(str).str.strip()
    df_gemini['file_name'] = df_gemini['file_name'].astype(str).str.strip()
    
    print("Merging data...")
    # Merge all DataFrames based on file_name
    df_merged = pd.merge(df_sys, df_gpt, on='file_name', how='outer')
    df_merged = pd.merge(df_merged, df_gemini, on='file_name', how='outer')
    
    # Output file
    output_excel = r"D:\MarkSense\chinese-ocr-app\Combined_Experiment_Results.xlsx"
    
    print("Calculating Summary...")
    # Summary Sheet
    total_images = len(df_merged)
    
    def count_non_empty(series):
        # Count values that aren't empty string, NaN, or 'Không rõ', 'Không có', etc
        return series.replace(['', 'Không rõ', 'Không có chữ', 'Không_Đọc_Được'], pd.NA).dropna().shape[0]
        
    system_detected = count_non_empty(df_merged['System_Res'])
    gpt_detected = count_non_empty(df_merged['ChatGPT_Res'])
    gemini_detected = count_non_empty(df_merged['Gemini_Res'])
    
    summary_data = {
        'Metric': ['Total Images', 'Images Detected by System', 'Images Detected by ChatGPT', 'Images Detected by Gemini', 'System DB Matches'],
        'Count': [
            total_images, 
            system_detected,
            gpt_detected,
            gemini_detected,
            df_merged['System_DB_Match'].sum()
        ],
        'Percentage': [
            "100%",
            f"{(system_detected/total_images)*100:.1f}%",
            f"{(gpt_detected/total_images)*100:.1f}%",
            f"{(gemini_detected/total_images)*100:.1f}%",
            f"{(df_merged['System_DB_Match'].sum()/total_images)*100:.1f}%"
        ]
    }
    df_summary = pd.DataFrame(summary_data)
    
    print("Saving to Excel...")
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        df_merged.to_excel(writer, sheet_name='Detailed Results', index=False)
        
    print(f"DONE! Report saved to {output_excel}")

if __name__ == '__main__':
    create_combined_report()
