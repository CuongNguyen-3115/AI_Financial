import os
import json
import requests
import feedparser
import re
import html
from datetime import datetime
from bs4 import BeautifulSoup
from dateutil import parser # Thư viện này cực mạnh để đọc mọi loại format ngày tháng
import time

# --- Cấu hình thư mục ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKET_DIR = os.path.join(BASE_DIR, "data", "raw_data", "news", "market")
TICKER_DIR = os.path.join(BASE_DIR, "data", "raw_data", "news", "tickers")

os.makedirs(MARKET_DIR, exist_ok=True)
os.makedirs(TICKER_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

def clean_and_decode_text(raw_text):
    """
    Hàm "chà xát" siêu sạch: Xử lý cả thẻ HTML và lỗi font chữ (VnEconomy)
    """
    if not raw_text:
        return ""
    
    # 1. Fix lỗi thiếu dấu '&' trong HTML Entity của VnEconomy (ví dụ: T#236; -> T&#236;)
    fixed_encoding = re.sub(r'(?<!&)#(\d+);', r'&#\1;', raw_text)
    
    # 2. Giải mã HTML Entities thành chữ tiếng Việt chuẩn (&#236; -> ì)
    decoded_text = html.unescape(fixed_encoding)
    
    # 3. Dùng BeautifulSoup để gỡ toàn bộ thẻ HTML rác (<a>, <img> của CafeF)
    soup = BeautifulSoup(decoded_text, "html.parser")
    clean_text = soup.get_text(separator=" ", strip=True)
    
    # 4. Xóa khoảng trắng thừa
    return re.sub(r'\s+', ' ', clean_text)

def parse_date_flexible(date_str):
    """
    Chuyển đổi mọi loại định dạng ngày tháng (RSS, AJAX, VN, Quốc tế) 
    về đối tượng datetime để so sánh chính xác.
    """
    if not date_str:
        return datetime.min
    try:
        # 1. Thử dùng dateutil.parser (Xử lý tốt RSS: Wed, 06 May...)
        return parser.parse(date_str)
    except:
        try:
            # 2. Thử format thủ công cho CafeF AJAX: 19/03/2026 09:18
            return datetime.strptime(date_str, '%d/%m/%Y %H:%M')
        except:
            try:
                # 3. Thử format cho CafeF AJAX (chỉ ngày): 19/03/2026
                return datetime.strptime(date_str, '%d/%m/%Y')
            except:
                return datetime.now()

def save_news_to_json(new_data, filepath):
    """Lưu dữ liệu, chống trùng và SẮP XẾP CHUẨN THEO THỜI GIAN"""
    existing_data = []
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except:
            pass

    # Gộp dữ liệu và chống trùng bằng link
    existing_links = {item.get('link') for item in existing_data}
    added_count = 0
    for item in new_data:
        if item['link'] and item['link'] not in existing_links:
            existing_data.append(item)
            added_count += 1
            
    # --- BƯỚC QUAN TRỌNG: SẮP XẾP LẠI TOÀN BỘ DANH SÁCH ---
    # Chúng ta dùng parse_date_flexible để so sánh giá trị thời gian thực sự
    existing_data.sort(key=lambda x: parse_date_flexible(x.get('date', '')), reverse=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=4)
        
    return added_count

def fetch_market_news_aggregated():
    """Lấy và làm sạch tin thị trường từ RSS"""
    print("[*] Đang tổng hợp tin tức thị trường (Đa nguồn)...")
    
    rss_sources = [
        {"url": "https://cafef.vn/thi-truong-chung-khoan.rss", "source": "CafeF_RSS"},
    ]
    
    all_market_news = []
    for feed_info in rss_sources:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries:
                title = clean_and_decode_text(entry.get("title", ""))
                # Ở đây ta gọi hàm clean_and_decode_text để dọn sạch lỗi font và thẻ img/a
                summary = clean_and_decode_text(entry.get("description", ""))
                
                if title:
                    all_market_news.append({
                        "date": entry.get("published", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                        "ticker": "MARKET",
                        "title": title,
                        "summary": summary,
                        "link": entry.get("link", ""),
                        "source": feed_info["source"]
                    })
        except Exception as e:
            print(f"  [-] Lỗi lấy RSS từ {feed_info['source']}: {e}")
            
    if all_market_news:
        date_str = datetime.now().strftime("%Y%m%d")
        filepath = os.path.join(MARKET_DIR, f"market_news_{date_str}.json")
        added = save_news_to_json(all_market_news, filepath)
        print(f"  [+] Đã cập nhật {added} tin thị trường SẠCH vào file JSON.")

def fetch_sapo_from_link(url):
    """Truy cập link bài báo và bóc tách thẻ h2 class sapo"""
    try:
        # Nghỉ ngắn để đảm bảo tính an toàn cho crawler
        time.sleep(0.5) 
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        # Tìm thẻ h2 theo class và data-role như bạn đã xác định
        sapo_tag = soup.find('h2', class_='sapo', attrs={"data-role": "sapo"})
        
        if sapo_tag:
            return clean_and_decode_text(sapo_tag.get_text())
    except Exception:
        pass
    return None

def fetch_ticker_news_ajax(ticker: str):
    """
    Lấy tin tức doanh nghiệp qua AJAX và tự động truy cập link để lấy Summary chi tiết
    """
    print(f"[*] Đang lấy tin tức mã: {ticker} (Qua AJAX)")
    ticker_folder = os.path.join(TICKER_DIR, ticker)
    os.makedirs(ticker_folder, exist_ok=True)
    
    ajax_url = "https://cafef.vn/du-lieu/Ajax/Events_RelatedNews_New.aspx"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Referer': f'https://cafef.vn/du-lieu/tin-doanh-nghiep/{ticker.lower()}/event.chn'
    }
    
    # 1. Đọc dữ liệu cũ để tránh cào lại những bài đã có Summary
    date_str_file = datetime.now().strftime("%Y%m")
    filepath = os.path.join(ticker_folder, f"{ticker}_news_{date_str_file}.json")
    existing_links = set()
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                existing_links = {item.get('link') for item in old_data}
        except:
            pass

    ticker_news = []
    
    # Quét tin tức (Type 1) và Sự kiện (Type 2)
    for news_type in ["1"]:
        params = {
            "symbol": ticker,
            "floorID": "0", "configID": "0",
            "PageIndex": "1", "PageSize": "30", "Type": news_type
        }
        
        try:
            response = requests.get(ajax_url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = soup.find_all('li')
            
            for art in articles:
                a_tag = art.find('a')
                if not a_tag: continue
                
                link = a_tag.get('href', '')
                if link.startswith('/'): link = "https://cafef.vn" + link
                
                # Nếu tin này đã có trong database, bỏ qua bước cào Sapo để tiết kiệm thời gian
                if link in existing_links:
                    continue

                title = clean_and_decode_text(a_tag.get_text())
                
                # Trích xuất ngày tháng
                raw_text = art.get_text(strip=True)
                date_match = re.search(r'\d{2}/\d{2}/\d{4}\s\d{2}:\d{2}', raw_text)
                date_val = date_match.group(0) if date_match else datetime.now().strftime("%d/%m/%Y %H:%M")
                
                # --- CHỨC NĂNG BỔ SUNG: Lấy Summary chi tiết ---
                print(f"    [>] Đang truy cập lấy Sapo: {title[:50]}...")
                detail_summary = fetch_sapo_from_link(link)
                
                ticker_news.append({
                    "date": date_val,
                    "ticker": ticker,
                    "title": title,
                    "summary": detail_summary if detail_summary else title,
                    "link": link,
                    "source": f"CafeF_Data_AJAX_Type{news_type}"
                })
                
        except Exception as e:
            print(f"  [-] Lỗi thu thập AJAX (Type {news_type}) cho {ticker}: {e}")

    # Xử lý lưu file
    if ticker_news:
        added = save_news_to_json(ticker_news, filepath)
        if added > 0:
            print(f"  [+] Cập nhật thành công {added} tin tức kèm Summary chi tiết cho {ticker}")
        else:
            print(f"  [+] Không có tin mới nào cần cập nhật cho {ticker}.")
    else:
        print(f"  [!] Không tìm thấy tin tức mới nào cho {ticker}.")

def get_latest_news(ticker: str = None, limit: int = 5) -> list:
    """
    Đọc dữ liệu tin tức mới nhất từ TẤT CẢ các file JSON đã lưu.
    Sắp xếp tổng hợp để đảm bảo luôn trả đủ số lượng 'limit' nếu database có đủ.
    """
    target_dir = os.path.join(TICKER_DIR, ticker) if ticker else MARKET_DIR
    if not os.path.exists(target_dir):
        return []
    
    files = [f for f in os.listdir(target_dir) if f.endswith('.json')]
    if not files:
        return []
    
    all_data = []
    
    # 1. Đọc và gộp dữ liệu từ tất cả các file JSON
    for file_name in files:
        filepath = os.path.join(target_dir, file_name)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_data.extend(data)
        except Exception as e:
            print(f"Lỗi khi đọc file {filepath}: {e}")
            continue

    if not all_data:
        return []

    # 2. Loại bỏ trùng lặp (nếu có bài báo bị lưu lặp giữa các ngày) bằng dictionary comprehension
    unique_data = {item.get('link'): item for item in all_data if item.get('link')}.values()
    all_data_list = list(unique_data)

    # 3. Sắp xếp lại toàn bộ list theo thời gian thực (Mới nhất lên đầu)
    all_data_list.sort(key=lambda x: parse_date_flexible(x.get('date', '')), reverse=True)
    
    # 4. Trả về đúng số lượng limit
    return all_data_list[:limit]

if __name__ == "__main__":
    print(f"{'='*40}\n KHỞI ĐỘNG DATA PIPELINE \n{'='*40}")
    
    fetch_market_news_aggregated()
    
    watch_list = ["FPT", "VCB", "VNM"]
    for t in watch_list:
        fetch_ticker_news_ajax(t)
        
    print(f"{'='*40}\n PIPELINE HOÀN TẤT \n{'='*40}")