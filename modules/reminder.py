import os
import sys
import random
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import REMINDER_THRESHOLD_DAYS, CONSUMPTION_SUGGESTIONS, CATEGORIES
from modules.database import Database


def calculate_days_remaining(expiry_date_str: str) -> int:
    try:
        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        today = date.today()
        delta = expiry_date - today
        return delta.days
    except (ValueError, TypeError):
        return 999


def format_days_remaining(days: int) -> Tuple[str, str]:
    if days < 0:
        return f"已过期{abs(days)}天", "expired"
    elif days == 0:
        return "今天到期", "critical"
    elif days == 1:
        return "明天到期", "warning"
    elif days <= REMINDER_THRESHOLD_DAYS:
        return f"剩余{days}天", "warning"
    elif days <= 7:
        return f"剩余{days}天", "notice"
    elif days <= 30:
        return f"剩余{days}天", "normal"
    else:
        months = days // 30
        if months >= 12:
            years = months // 12
            return f"剩余{years}年", "safe"
        return f"剩余{months}个月", "safe"


def get_category_icon(category: str) -> str:
    if category in CATEGORIES:
        return CATEGORIES[category]['icon']
    return '📦'


class ReminderEngine(QObject):
    reminder_triggered = pyqtSignal(list)
    check_completed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        self._daily_timer = QTimer(self)
        self._daily_timer.timeout.connect(self._check_and_remind)
        self._shown_reminders = set()

    def start(self):
        self._check_and_remind()
        self._daily_timer.start(60 * 60 * 1000)

    def stop(self):
        if self._daily_timer.isActive():
            self._daily_timer.stop()

    def _check_and_remind(self):
        try:
            expiring_items = self.db.get_expiring_items(within_days=REMINDER_THRESHOLD_DAYS)
            new_reminders = []
            for item in expiring_items:
                if item['id'] not in self._shown_reminders:
                    days_remaining = calculate_days_remaining(item['expiry_date'])
                    suggestion = self.generate_suggestion(item, days_remaining)
                    reminder = {
                        'item': item,
                        'days_remaining': days_remaining,
                        'suggestion': suggestion,
                        'formatted_days': format_days_remaining(days_remaining)[0]
                    }
                    new_reminders.append(reminder)
                    self._shown_reminders.add(item['id'])
            stats = self.db.get_stats()
            self.check_completed.emit(stats)
            if new_reminders:
                self.reminder_triggered.emit(new_reminders)
        except Exception as e:
            print(f"[ReminderEngine] 检查出错: {e}")

    def force_check(self):
        self._shown_reminders.clear()
        self._check_and_remind()

    def generate_suggestion(self, item: Dict[str, Any], days_remaining: int) -> str:
        category = item.get('category', '其他')
        name = item.get('name', '物品')
        if category not in CONSUMPTION_SUGGESTIONS:
            category = '其他'
        suggestions = CONSUMPTION_SUGGESTIONS[category]
        suggestion = random.choice(suggestions)
        if days_remaining < 0:
            prefix = f"⚠️ 您的{name}已过期{abs(days_remaining)}天，建议检查后处理，"
        elif days_remaining == 0:
            prefix = f"您的{name}今天到期，"
        elif days_remaining == 1:
            prefix = f"您的{name}将于明天到期，"
        else:
            prefix = f"您的{name}将于{days_remaining}天后到期，"
        return prefix + suggestion

    def get_item_suggestion(self, item: Dict[str, Any]) -> str:
        days_remaining = calculate_days_remaining(item['expiry_date'])
        return self.generate_suggestion(item, days_remaining)

    def get_all_expiring_with_suggestions(self, threshold_days: int = None) -> List[Dict[str, Any]]:
        if threshold_days is None:
            threshold_days = REMINDER_THRESHOLD_DAYS
        items = self.db.get_expiring_items(within_days=threshold_days)
        result = []
        for item in items:
            days_remaining = calculate_days_remaining(item['expiry_date'])
            suggestion = self.generate_suggestion(item, days_remaining)
            formatted_days, status = format_days_remaining(days_remaining)
            result.append({
                'item': item,
                'days_remaining': days_remaining,
                'formatted_days': formatted_days,
                'status': status,
                'suggestion': suggestion,
                'icon': get_category_icon(item.get('category', '其他'))
            })
        return result
