# tools/report_processor.py
import os
import re
import sys
import json
import time
import fitz  # PyMuPDF
import pymupdf4llm
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --- Cấu hình đường dẫn ---
BASE_DIR = Path(__file__).parent.parent
REPORT_DIR = BASE_DIR / "data" / "financial_reports"
MARKDOWN_DIR = BASE_DIR / "data" / "processed_data"
os.makedirs(MARKDOWN_DIR, exist_ok=True)

load_dotenv()

# --- Khởi tạo Gemini Client cho VLM ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# Danh sách Model Rotation để backup
MODEL_POOL = [
    os.getenv("MODEL_ID_1", "gemini-3.1-flash-lite-preview"),
    os.getenv("MODEL_ID_2", "gemini-2.5-flash"),
    os.getenv("MODEL_ID_3", "gemini-3-flash-preview"),
    os.getenv("MODEL_ID_4", "gemini-2.5-flash-lite")
]

VLM_PROMPT = """
Bạn là một chuyên gia phân tích báo cáo tài chính. 
Trang này chứa các biểu đồ, đồ thị hoặc bảng biểu phức tạp về mã chứng khoán.
Nhiệm vụ của bạn:
1. Trích xuất chính xác các số liệu quan trọng trong bảng biểu.
2. Mô tả xu hướng của các biểu đồ kỹ thuật hoặc biểu đồ kết quả kinh doanh.
3. Trình bày lại toàn bộ nội dung dưới dạng Markdown chuẩn.
4. Giữ nguyên các thuật ngữ chuyên môn tài chính.
"""

def is_complex_page(page):
    """
    Xác định trang có cần dùng VLM hay không dựa trên số lượng ảnh và bản vẽ.
    """
    images = page.get_images(full=True)
    drawings = page.get_drawings()
    # Nếu có ảnh hoặc nhiều hơn 15 thành phần đồ họa (thường là biểu đồ)
    return len(images) > 0 or len(drawings) > 15

def call_vlm_for_page(pdf_path, page_index):
    """
    Sử dụng cơ chế Rotation để gọi Gemini VLM đọc trang PDF.
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_index]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_data = pix.tobytes("png")
        
        # Bắt đầu vòng lặp xoay vòng model
        for model_id in MODEL_POOL:
            try:
                print(f"      [VLM] Đang thử với model: {model_id}...")
                response = client.models.generate_content(
                    model=model_id,
                    contents=[
                        VLM_PROMPT,
                        types.Part.from_bytes(data=img_data, mime_type="image/png")
                    ]
                )
                if response and response.text:
                    return response.text
            except Exception as model_err:
                # Nếu lỗi do cạn Quota (429) hoặc Token limit, ghi log và thử model tiếp theo
                print(f"      [!] Model {model_id} gặp lỗi hoặc hết Quota. Đang chuyển model backup...")
                continue # Nhảy sang model tiếp theo trong vòng lặp
                
        print(f"  [-] Tất cả model trong Pool đều thất bại tại trang {page_index}.")
        return ""
        
    except Exception as e:
        print(f"  [-] Lỗi nghiêm trọng khi xử lý trang {page_index}: {e}")
        return ""

def convert_pdf_to_markdown(pdf_path):
    """
    Chuyển đổi PDF sang Markdown bằng chiến lược Hybrid (VLM + Text Extraction).
    """
    pdf_path = Path(pdf_path)
    output_md_path = MARKDOWN_DIR / f"{pdf_path.stem}.md"
    
    if output_md_path.exists():
        print(f"[*] Đã tìm thấy file Markdown: {output_md_path.name}")
        with open(output_md_path, "r", encoding="utf-8") as f:
            return f.read()

    print(f"[*] Đang xử lý PDF sang Markdown: {pdf_path.name}")
    doc = fitz.open(pdf_path)
    full_md_content = []

    for i in range(len(doc)):
        print(f"    [>] Đang xử lý trang {i+1}/{len(doc)}...")
        page = doc[i]
        
        if is_complex_page(page):
            # Sử dụng VLM cho trang phức tạp
            md_text = call_vlm_for_page(pdf_path, i)
        else:
            # Sử dụng pymupdf4llm cho trang text thuần túy
            md_text = pymupdf4llm.to_markdown(str(pdf_path), pages=[i])
            
        full_md_content.append(md_text)
        # Nghỉ ngắn để tránh Rate Limit API nếu dùng VLM liên tục
        time.sleep(1)

    final_md = "\n\n---\n\n".join(full_md_content)
    
    # Lưu lại để làm cache
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(final_md)
        
    return final_md

def header_slicing(markdown_text):
    """
    Cắt nhỏ file Markdown dựa trên các tiêu đề (#, ##) để tối ưu Token.
    """
    # Tìm các đoạn bắt đầu bằng dấu # (Heading 1 hoặc Heading 2)
    chunks = re.split(r'\n(?=# )', markdown_text)
    
    cleaned_chunks = []
    for chunk in chunks:
        content = chunk.strip()
        if content:
            cleaned_chunks.append(content)
            
    # Nếu kết quả quá ít mảnh, thử chia nhỏ hơn bằng Heading 2
    if len(cleaned_chunks) <= 1:
        chunks = re.split(r'\n(?=## )', markdown_text)
        cleaned_chunks = [c.strip() for c in chunks if c.strip()]
        
    return cleaned_chunks

def process_report_for_llm(pdf_path):
    """
    Quy trình tổng lực: Chuyển đổi -> Cắt nhỏ dữ liệu.
    Trả về danh sách các chunks Markdown đã được tối ưu.
    """
    if not pdf_path or not os.path.exists(pdf_path):
        return []
        
    md_text = convert_pdf_to_markdown(pdf_path)
    chunks = header_slicing(md_text)
    
    print(f"[+] Hoàn tất xử lý báo cáo. Tổng số mảnh dữ liệu (chunks): {len(chunks)}")
    return chunks

if __name__ == "__main__":
    # Test nhanh với một file PDF bất kỳ trong thư mục reports
    test_files = list(REPORT_DIR.glob("*.pdf"))
    if test_files:
        sample_chunks = process_report_for_llm(test_files[0])
        if sample_chunks:
            print("\n--- MẢNH DỮ LIỆU ĐẦU TIÊN ---")
            print(sample_chunks[0][:500] + "...")