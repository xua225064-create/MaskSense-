import os
import re

def translate_file(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    for vi, en in replacements.items():
        text = text.replace(vi, en)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)

index_replacements = {
    # Fix the corrupted "phân credits"
    "phân credits chéo qua 5 luồng xử lý độc lập và tổng hợp kết quả để đưa ra báo cáo giám định chính xác nhất.": "cross-analyze through 5 independent processing pipelines and synthesize the results to provide the most accurate authentication report.",
    "Chụp hoặc tải ảnh hiệu đề lên, hệ thống Multi-Pipeline AI sẽ ": "Upload or capture a mark image, the Multi-Pipeline AI system will ",
    
    # "Lượt phân credits còn lại:" -> "Analysis credits remaining:"
    "Lượt\n            phân credits còn lại:": "Analysis credits remaining:",
    "Lượt phân credits đầu": "free initial analysis credits",
    "lưu trữ lịch sử phân credits cá": "store personal analysis history",
    "kích hoạt lõi AI thị giác máy tính xử lý ảnh.": "activate the computer vision AI core to process the image.",
    "Hình ảnh được tải lên phục vụ trực tiếp cho thuật toán phân credits.": "Images are uploaded directly to serve the analysis algorithm.",
    "Dữ liệu này sẽ được ẩn": "This data will be hidden",
    "Các báo cáo và kết quả phân credits do AI trả về mang tính tham chiếu và bổ trợ cho công": "Reports and analysis results returned by AI are for reference and support for authentication",
    
    # "Tải lên hình ảnh hiệu đề"
    "Tải lên hình ảnh hiệu đề": "Upload mark image",
    
    # "Phân credits ảnh này"
    "Phân credits ảnh này": "Analyze this image",
    "Phân credits 4-Pipeline": "4-Pipeline Analysis",
    "Phân credits & <span class=\"rm-blue\">Nhận Dạng Hiệu Đề</span>": "Analyze & <span class=\"rm-blue\">Recognize Mark</span>",
    "Bạn đã hết lượt phân credits miễn phí.": "You have run out of free analysis credits.",
    
    # "Hệ thống nhận dạng và phân credits hiệu đề..."
    "Hệ thống nhận dạng và phân credits hiệu đề<br>and analysis system, applying<br>Artificial Intelligence": "Mark recognition and analysis system, applying<br>Artificial Intelligence",
    "Hệ thống nhận dạng và phân credits hiệu đề<br>and analysis system, applying<br>công nghệ Trí tuệ Nhân and computer vision.<br>tính chuyên sâu.": "Mark recognition and analysis system, applying<br>Artificial Intelligence and computer vision<br>technology.",
    "Ứng dụng <strong>trí tuệ nhân tạo</strong> để nhận diện và phân credits hiệu đề trên các": "Apply <strong>artificial intelligence</strong> to recognize and analyze marks on",
    "<strong>Multi-agent AI</strong><span>Phân credits chính xác nguồn gốc": "<strong>Multi-agent AI</strong><span>Accurately analyze origin",
    "Hệ thống tối tân hỗ trợ quy trình giám định, nhận dạng và phân credits hiệu đề trên nền gốm sứ": "State-of-the-art system supporting the authentication, recognition, and analysis of marks on ceramics",
    
    # Credits string
    "vô hạn' : data.packages.enterprise.credits) + ' lượt';": "Unlimited' : data.packages.enterprise.credits) + ' scans';",
    "Total ' + data.packages.pro.credits + ' scans'": "Total ' + data.packages.pro.credits + ' scans'",
    "+${tx.credits} ${isEn ? 'Credits' : 'Lượt'}": "+${tx.credits} Credits",
    
    # "Thư viện hiệu đề Hiển thị 187 samples"
    "Thư viện hiệu\n            đề</span> <span\n                class=\"lib-count-badge\"": "Mark\n            Library</span> <span\n                class=\"lib-count-badge\"",
    "Hiển\n                thị</span>": "Showing</span>",
    "Thư viện hiệu": "Mark Library",
    "đề</span>": "</span>",
    "Hiển": "Showing",
    "thị</span>": "</span>",
    
    # Search placeholder
    "Tìm kiếm niên hiệu, triều đại...": "Search reign title, dynasty...",
    
    "công nghệ Trí tuệ Nhân and computer vision.<br>tính chuyên sâu.": "Artificial Intelligence and computer vision<br>technology.",
}

if __name__ == '__main__':
    translate_file('index.html', index_replacements)
    print("index.html fixed.")
