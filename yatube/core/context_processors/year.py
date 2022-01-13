from datetime import datetime


def year(request):
    """Добавляет в контекст переменную year"""
    return {
        'year': datetime.now().year,
    }
