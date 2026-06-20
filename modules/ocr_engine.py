import os
import sys
import re
import tempfile
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from PIL import Image
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    OCR_LANGUAGES, OCR_GPU, OCR_READER_INSTANCE,
    DATE_PATTERNS, SHELF_LIFE_PATTERNS, CATEGORIES
)


class OCREngine:
    _instance = None
    _reader = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_reader(self):
        global OCR_READER_INSTANCE
        if self._reader is None:
            try:
                import easyocr
                self._reader = easyocr.Reader(OCR_LANGUAGES, gpu=OCR_GPU, verbose=False)
                OCR_READER_INSTANCE = self._reader
            except ImportError:
                raise ImportError(
                    "EasyOCR未安装，请运行: pip install easyocr"
                )
        return self._reader

    def recognize_image(self, image_input, detail: int = 0) -> List[str]:
        reader = self._get_reader()
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"图片文件不存在: {image_input}")
            results = reader.readtext(image_input, detail=detail)
        elif isinstance(image_input, np.ndarray):
            results = reader.readtext(image_input, detail=detail)
        elif isinstance(image_input, Image.Image):
            img_array = np.array(image_input)
            results = reader.readtext(img_array, detail=detail)
        else:
            raise TypeError("不支持的图片输入类型")
        return results

    def recognize_image_with_details(self, image_input) -> List[Tuple]:
        return self.recognize_image(image_input, detail=1)

    def preprocess_image(self, image_path: str) -> np.ndarray:
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"无法读取图片: {image_path}")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = np.ones((2, 2), np.uint8)
        processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        return processed

    def extract_text(self, image_input) -> str:
        results = self.recognize_image(image_input, detail=0)
        return '\n'.join(results)

    def extract_dates(self, text: str) -> List[Dict[str, Any]]:
        dates = []
        seen = set()
        for pattern in DATE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                try:
                    if len(groups) == 3:
                        year = int(groups[0])
                        month = int(groups[1])
                        day = int(groups[2])
                        if year < 100:
                            current_year = datetime.now().year
                            year = current_year - (current_year % 100) + year
                            if year > current_year + 10:
                                year -= 100
                        if 1970 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                            date_str = f"{year:04d}-{month:02d}-{day:02d}"
                            key = (date_str, match.start())
                            if key not in seen:
                                seen.add(key)
                                context = self._get_match_context(text, match.start(), match.end())
                                dates.append({
                                    'date': date_str,
                                    'original': match.group(),
                                    'position': match.start(),
                                    'context': context,
                                    'type': self._classify_date_type(context)
                                })
                except (ValueError, IndexError):
                    continue
        dates.sort(key=lambda x: x['position'])
        return dates

    def extract_shelf_life(self, text: str) -> Optional[Dict[str, Any]]:
        for pattern, multiplier, unit in SHELF_LIFE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = int(match.group(1))
                    return {
                        'value': value,
                        'multiplier': multiplier,
                        'unit': unit,
                        'total_days': value * multiplier,
                        'original': match.group()
                    }
                except (ValueError, IndexError):
                    continue
        return None

    def parse_product_info(self, image_input) -> Dict[str, Any]:
        try:
            preprocessed = None
            if isinstance(image_input, str) and os.path.exists(image_input):
                try:
                    preprocessed = self.preprocess_image(image_input)
                except Exception:
                    pass
            text = self.extract_text(preprocessed if preprocessed is not None else image_input)
            dates = self.extract_dates(text)
            shelf_life = self.extract_shelf_life(text)
            production_date = None
            expiry_date = None
            for d in dates:
                if d['type'] == 'expiry' and expiry_date is None:
                    expiry_date = d['date']
                elif d['type'] == 'production' and production_date is None:
                    production_date = d['date']
            if expiry_date is None and len(dates) >= 2:
                production_date = dates[0]['date']
                expiry_date = dates[-1]['date']
            elif expiry_date is None and len(dates) == 1:
                if production_date is None:
                    production_date = dates[0]['date']
                if shelf_life and production_date:
                    try:
                        prod = datetime.strptime(production_date, '%Y-%m-%d')
                        if shelf_life['unit'] == 'months':
                            import calendar
                            month = prod.month - 1 + shelf_life['value']
                            year = prod.year + month // 12
                            month = month % 12 + 1
                            day = min(prod.day, calendar.monthrange(year, month)[1])
                            expiry = datetime(year, month, day)
                        else:
                            expiry = prod + timedelta(days=shelf_life['total_days'])
                        expiry_date = expiry.strftime('%Y-%m-%d')
                    except (ValueError, OverflowError):
                        expiry_date = dates[0]['date']
                else:
                    expiry_date = dates[0]['date']
            if expiry_date is None:
                expiry_date = ''
            product_name = self._extract_product_name(text, dates)
            category = self._auto_categorize(product_name, text)
            return {
                'success': True,
                'text': text,
                'product_name': product_name,
                'production_date': production_date or '',
                'expiry_date': expiry_date,
                'shelf_life': shelf_life,
                'all_dates': dates,
                'category': category
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': '',
                'product_name': '',
                'production_date': '',
                'expiry_date': '',
                'shelf_life': None,
                'all_dates': [],
                'category': '其他'
            }

    def _get_match_context(self, text: str, start: int, end: int,
                           context_chars: int = 10) -> str:
        ctx_start = max(0, start - context_chars)
        ctx_end = min(len(text), end + context_chars)
        return text[ctx_start:ctx_end].strip()

    def _classify_date_type(self, context: str) -> str:
        context_lower = context.lower()
        expiry_keywords = ['到期', '过期', '保质期至', '有效期至', 'best before',
                           'use by', 'exp', 'expiry', '有效期', '截止']
        production_keywords = ['生产', '生产日期', '制造', 'mfg', 'manufacture', '生产于']
        for kw in expiry_keywords:
            if kw in context_lower:
                return 'expiry'
        for kw in production_keywords:
            if kw in context_lower:
                return 'production'
        return 'unknown'

    def _extract_product_name(self, text: str, dates: List[Dict]) -> str:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        date_positions = set()
        for d in dates:
            for i, line in enumerate(lines):
                if d['original'] in line:
                    date_positions.add(i)
        candidate_lines = []
        for i, line in enumerate(lines):
            if i not in date_positions and 2 <= len(line) <= 30:
                score = self._score_name_line(line)
                candidate_lines.append((score, line))
        if candidate_lines:
            candidate_lines.sort(key=lambda x: x[0], reverse=True)
            return candidate_lines[0][1]
        if lines:
            for line in lines:
                if 2 <= len(line) <= 20:
                    return line
            return lines[0][:20]
        return '未命名物品'

    def _score_name_line(self, line: str) -> float:
        score = 0.0
        if 3 <= len(line) <= 15:
            score += 2.0
        elif 2 <= len(line) <= 20:
            score += 1.0
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', line))
        if has_chinese:
            score += 1.5
        if re.search(r'[a-zA-Z]', line):
            score += 0.5
        if re.search(r'\d', line):
            score -= 0.5
        for cat_info in CATEGORIES.values():
            for kw in cat_info['keywords']:
                if kw in line:
                    score += 2.0
        return score

    def _auto_categorize(self, name: str, text: str = '') -> str:
        combined = name + ' ' + text
        for category, info in CATEGORIES.items():
            if category == '全部' or category == '其他':
                continue
            for keyword in info['keywords']:
                if keyword in combined:
                    return category
        return '其他'
