# AI Financial Analyst System

Hệ thống tư vấn đầu tư và phân tích tài chính tự động hóa đa chiều (360-degree), được xây dựng dựa trên kiến trúc Multi-Agent của nền tảng MetaGPT. Dự án tập trung giải quyết bài toán xử lý dữ liệu tài chính phi cấu trúc (báo cáo PDF, tin tức thị trường) và dữ liệu có cấu trúc (OHLCV, chỉ báo kỹ thuật) thông qua việc phối hợp linh hoạt năng lực xử lý của nhiều mô hình ngôn ngữ lớn (LLMs).

Hệ thống này đóng vai trò như một bộ máy phân tích chuyên sâu, tự động hóa toàn bộ quy trình từ khâu thu thập dữ liệu thô đến việc ra quyết định của một đội ngũ chuyên gia tài chính.

## 1. Tính năng cốt lõi (Core Features)

* **Kiến trúc Multi-Agent (Cerebrum Orchestrator):** Hệ thống được vận hành bởi một Manager Agent trung tâm. Agent này chịu trách nhiệm phân tích ngữ nghĩa yêu cầu từ người dùng, tự động lập kế hoạch và phân bổ tác vụ chuyên biệt cho các chuyên gia (Sub-agents) cấp dưới theo thời gian thực.
* **Xử lý dữ liệu tài liệu lai (Hybrid PDF Processing):** Hệ thống tự động thu thập và trích xuất báo cáo phân tích tài chính từ nguồn Vietstock. Tích hợp thuật toán nhận diện các trang chứa biểu đồ, đồ thị để xử lý thông qua Vision-Language Model (Gemini VLM), đồng thời chuyển đổi văn bản thuần túy sang định dạng Markdown qua thư viện PyMuPDF. Quy trình này đảm bảo tính toàn vẹn của ngữ cảnh và cấu trúc tài liệu đầu vào cho LLM.
* **Cơ chế luân chuyển LLM thông minh (Smart LLM Rotation):** Dự án tích hợp cơ chế xoay vòng mô hình dự phòng (Failover Mechanism), luân chuyển linh hoạt giữa các nhà cung cấp như Groq (Llama-3), Google (Gemini) và GitHub Models. Cơ chế này tối ưu hóa hạn mức truy cập API (Quota), tự động vượt qua các giới hạn Rate Limit (lỗi HTTP 429) nhằm đảm bảo tính sẵn sàng và ổn định cao cho hệ thống.
* **Quy trình phân tích 360 độ:**
    * **Sentiment Analysis (Phân tích Tâm lý thị trường):** Đánh giá biến động tâm lý thông qua việc xử lý ngôn ngữ tự nhiên trên các bản tin vĩ mô và vi mô.
    * **Quantitative Analysis (Phân tích Định lượng Kỹ thuật):** Truy xuất thông tin doanh nghiệp, phân tích biến động dữ liệu giá lịch sử (OHLCV) và tính toán các chỉ báo kỹ thuật cốt lõi (SMA, RSI).
    * **Fundamental Analysis (Phân tích Cơ bản):** Trích xuất, phân mảnh (Map) và tổng hợp (Reduce) các luận điểm đầu tư, rủi ro, cùng mức giá mục tiêu (Target Price) từ các báo cáo chuyên sâu.
* **Investment Advisor (Cố vấn Đầu tư):** Đối chiếu chéo (Cross-check) dữ liệu từ các luồng phân tích trên để xuất bản báo cáo tư vấn chuyên nghiệp.

## 2. Cấu trúc mã nguồn (Project Structure)

Dự án được tổ chức theo tiêu chuẩn module hóa nhằm tối ưu quá trình bảo trì và mở rộng trong tương lai.

```text
├── actions/                      # Chứa logic thực thi chi tiết của các Agent
│   ├── audit_action.py           # Tác vụ kiểm toán và đánh giá báo cáo
│   ├── company_info_action.py    # Truy xuất thông tin cơ bản doanh nghiệp
│   ├── news_analysis_action.py   # Phân tích tâm lý từ dữ liệu tin tức thị trường
│   ├── planning_action.py        # Module lập kế hoạch thực thi (dành cho Manager)
│   ├── report_analysis_action.py # Xử lý Map-Reduce cho dữ liệu báo cáo PDF
│   ├── synthesis_action.py       # Tổng hợp và đồng nhất dữ liệu phân tích
│   └── technical_analysis_action.py # Thuật toán xử lý các chỉ báo kỹ thuật
├── config/                       # Thư mục cấu hình hệ thống
│   └── config2.yaml              # Tệp cấu hình mặc định nhằm vượt qua xác thực hệ thống MetaGPT
├── data/                         # Lưu trữ dữ liệu hệ thống
│   ├── financial_reports/        # Tệp PDF báo cáo tài chính gốc truy xuất từ Vietstock
│   ├── processed_data/           # Dữ liệu Markdown đã qua tiền xử lý và cắt nhỏ
│   └── raw_data/                 # Dữ liệu thô (Hồ sơ, tin tức, dữ liệu chuỗi thời gian OHLCV)
├── logs/                         # Hệ thống ghi nhật ký hoạt động (System logs)
├── roles/                        # Định nghĩa cấu hình, hành vi và vai trò của các Agent
│   ├── manager_agent.py          # Trưởng nhóm điều phối (Orchestrator/Cerebrum)
│   ├── sentiment_agent.py        # Chuyên gia phân tích Tâm lý thị trường
│   ├── quant_agent.py            # Chuyên gia phân tích Định lượng kỹ thuật
│   ├── fundamental_agent.py      # Chuyên gia Phân tích Cơ bản
│   ├── investment_advisor.py     # Chuyên gia Cố vấn Đầu tư
│   └── auditor_agent.py          # Kiểm toán viên xác thực dữ liệu chéo
├── tools/                        # Khối công cụ và script hỗ trợ (Utilities)
│   ├── calculate_SMA_RSI.py      # Các thuật toán tính toán chỉ báo kỹ thuật
│   ├── fetch_market_data.py      # Thu thập dữ liệu giá và hồ sơ định lượng công ty
│   ├── fetch_news_data.py        # Trích xuất văn bản tin tức thị trường
│   ├── fetch_report_data.py      # Tự động hóa quá trình tìm kiếm và tải báo cáo PDF
│   └── report_processor.py       # Pipeline chuyển đổi PDF sang Markdown (Hỗ trợ VLM)
├── utils/
│   └── llm_rotator.py            # Lớp đối tượng quản lý và điều phối xoay vòng LLM
├── .env                          # Tệp biến môi trường bảo mật lưu trữ API Keys
└── main.py                       # Tệp khởi chạy toàn bộ hệ thống (Entry point)
```
## 3. Hướng dẫn cài đặt và vận hành (Installation & Setup)

### 3.1. Yêu cầu môi trường
* Ngôn ngữ lập trình: Python 3.9 trở lên.
* Yêu cầu thiết lập môi trường ảo (Virtual Environment) trước khi tiến hành cài đặt các gói phụ thuộc nhằm ngăn ngừa xung đột với các thư viện hệ thống cục bộ.

### 3.2. Cài đặt các gói phụ thuộc (Dependencies)
Kích hoạt môi trường ảo và tiến hành cài đặt các thư viện lõi thông qua trình quản lý gói `pip`:

```bash
pip install -r requirements.txt
```

### 3.3. Thiết lập biến môi trường
Tạo tệp `.env` tại thư mục gốc của dự án và khai báo các thông số bảo mật, định danh mô hình tương ứng với các nền tảng cung cấp API, ví dụ:

```env
# Cấu hình API Google Gemini
GEMINI_API_KEY=your_gemini_api_key
MODEL_ID_1=gemini-1.5-flash
MODEL_ID_2=gemini-1.5-pro

# Cấu hình API Groq
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL_ID_1=llama-3.3-70b-versatile
GROQ_MODEL_ID_6=llama-3.1-8b-instant

# Cấu hình API GitHub Models 
GITHUB_TOKEN=your_github_token
GITHUB_MODEL_ID_1=gpt-4o
```

### 3.4. Khởi chạy hệ thống
Tiến hành khởi chạy hệ thống bằng cách thực thi tệp `main.py`. Quá trình này sẽ tự động kiểm tra cấu hình, phân bổ tác vụ cho các Agent, tìm nạp dữ liệu đa luồng theo thời gian thực và xuất bản báo cáo phân tích toàn diện ra giao diện dòng lệnh.

```bash
python main.py
```

## 4. Kết quả

Hệ thống cung cấp các đầu ra phân tích dưới định dạng Markdown chuyên nghiệp, tối ưu hóa cho việc đọc và lưu trữ kết quả tư vấn. Để có cái nhìn trực quan về năng lực xử lý dữ liệu và chất lượng tư vấn của các Agent trong điều kiện thực tế, một số phản hồi mẫu tiêu biểu đã được trích xuất và tổng hợp tại tệp: **Response.md**.

Người dùng có thể tham khảo tệp này để hiểu rõ hơn về cấu trúc báo cáo tổng hợp, cách thức Agent trích xuất luận điểm đầu tư cũng như cách hệ thống trình bày các chỉ báo kỹ thuật và mục tiêu giá.
