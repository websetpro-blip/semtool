"""
Сервис для автоматического выделения минус-слов
Анализ частотности и генерация списков минус-слов как в Key Collector
"""

from collections import Counter
from typing import List, Dict, Set
import re


class MinusWordsExtractor:
    """Класс для извлечения минус-слов из фраз"""
    
    def __init__(self):
        # Стоп-слова которые не могут быть минус-словами
        self.stop_words = {
            'в', 'на', 'с', 'для', 'из', 'по', 'к', 'о', 'и', 'а', 'но',
            'или', 'от', 'до', 'за', 'под', 'над', 'при', 'через', 'у'
        }
    
    def extract_from_group(
        self,
        phrases: List[Dict],
        min_frequency: int = 100,
        rare_threshold: float = 0.1,
        freq_drop_threshold: float = 0.5
    ) -> List[str]:
        """
        Извлечь минус-слова из группы фраз
        
        Args:
            phrases: Список словарей с ключами 'phrase', 'freq_total', 'freq_quotes', 'freq_exact'
            min_frequency: Минимальная частотность для анализа
            rare_threshold: Порог редкости слова (< 10% = редкое)
            freq_drop_threshold: Порог падения частотности (> 50% = минус-слово)
        
        Returns:
            Список минус-слов
        """
        minus_words = set()
        
        # Анализ 1: Слова которые встречаются редко
        word_counter = Counter()
        total_phrases = len(phrases)
        
        for phrase_data in phrases:
            phrase = phrase_data['phrase'].lower()
            words = self._tokenize(phrase)
            for word in words:
                if word not in self.stop_words:
                    word_counter[word] += 1
        
        # Слова которые встречаются меньше rare_threshold
        for word, count in word_counter.items():
            if count / total_phrases < rare_threshold:
                minus_words.add(word)
        
        # Анализ 2: Слова которые сильно снижают частотность
        for phrase_data in phrases:
            phrase = phrase_data['phrase']
            freq_total = phrase_data.get('freq_total', 0)
            freq_exact = phrase_data.get('freq_exact', 0)
            
            # Если точная частотность намного меньше широкой
            if freq_total > min_frequency and freq_exact > 0:
                drop_ratio = (freq_total - freq_exact) / freq_total
                
                if drop_ratio > freq_drop_threshold:
                    # Находим слова которые могут быть причиной падения
                    words = self._tokenize(phrase.lower())
                    rare_words = [w for w in words if word_counter[w] / total_phrases < 0.3]
                    minus_words.update(rare_words)
        
        # Анализ 3: Слова-"паразиты" (купить, цена, стоимость и т.д.)
        suspicious_words = {
            'цена', 'стоимость', 'купить', 'заказать', 'доставка',
            'бесплатно', 'дешево', 'скидка', 'акция', 'распродажа',
            'интернет', 'магазин', 'москва', 'спб', 'отзывы'
        }
        
        for phrase_data in phrases:
            phrase = phrase_data['phrase'].lower()
            words = set(self._tokenize(phrase))
            
            # Если содержит подозрительное слово и низкая точная частотность
            if words & suspicious_words:
                freq_exact = phrase_data.get('freq_exact', 0)
                freq_total = phrase_data.get('freq_total', 0)
                
                if freq_total > 0 and freq_exact / freq_total < 0.3:
                    minus_words.update(words & suspicious_words)
        
        # Убираем стоп-слова из минус-слов
        minus_words -= self.stop_words
        
        return sorted(list(minus_words))
    
    def cross_minus(
        self,
        group_a_phrases: List[str],
        group_b_phrases: List[str]
    ) -> Dict[str, List[str]]:
        """
        Кросс-минусовка между двумя группами
        
        Args:
            group_a_phrases: Фразы группы A
            group_b_phrases: Фразы группы B
        
        Returns:
            {
                'group_a_minus': [...],  # Минус-слова для группы A
                'group_b_minus': [...]   # Минус-слова для группы B
            }
        """
        # Собираем уникальные слова из каждой группы
        words_a = set()
        for phrase in group_a_phrases:
            words_a.update(self._tokenize(phrase.lower()))
        
        words_b = set()
        for phrase in group_b_phrases:
            words_b.update(self._tokenize(phrase.lower()))
        
        # Убираем стоп-слова
        words_a -= self.stop_words
        words_b -= self.stop_words
        
        # Находим уникальные слова каждой группы
        unique_a = words_a - words_b
        unique_b = words_b - words_a
        
        return {
            'group_a_minus': sorted(list(unique_b)),  # Для A минусуем слова из B
            'group_b_minus': sorted(list(unique_a))   # Для B минусуем слова из A
        }
    
    def _tokenize(self, phrase: str) -> List[str]:
        """Разбить фразу на слова"""
        # Удаляем спецсимволы и разбиваем на слова
        words = re.findall(r'\b[а-яёa-z]+\b', phrase.lower())
        return [w for w in words if len(w) > 2]  # Слова длиннее 2 символов
    
    def export_for_direct(
        self,
        minus_words: List[str],
        format_type: str = 'list'
    ) -> str:
        """
        Экспортировать минус-слова в формате Яндекс Директ
        
        Args:
            minus_words: Список минус-слов
            format_type: 'list' или 'line'
        
        Returns:
            Строка для вставки в Директ
        """
        if format_type == 'list':
            # По одному минус-слову на строку
            return '\n'.join([f'-{word}' for word in minus_words])
        else:
            # Все в одну строку через пробел
            return ' '.join([f'-{word}' for word in minus_words])
    
    def analyze_phrase_efficiency(
        self,
        phrase: str,
        freq_total: int,
        freq_quotes: int,
        freq_exact: int
    ) -> Dict[str, any]:
        """
        Анализ эффективности фразы
        
        Returns:
            {
                'efficiency_score': float,  # 0-100
                'suggested_minus': List[str],
                'warnings': List[str]
            }
        """
        warnings = []
        suggested_minus = []
        
        # Расчет эффективности
        if freq_total == 0:
            efficiency_score = 0
        else:
            # Чем ближе freq_exact к freq_total, тем лучше
            efficiency_score = (freq_exact / freq_total) * 100
        
        # Предупреждения
        if freq_total > 1000 and freq_exact < 100:
            warnings.append("Очень большая потеря частотности - нужна минусовка")
        
        if freq_total > 0 and freq_exact / freq_total < 0.1:
            warnings.append("Точная частотность < 10% от широкой - фраза неэффективна")
            
            # Пытаемся найти проблемные слова
            words = self._tokenize(phrase.lower())
            # Ищем "коммерческие" слова
            commercial = {'купить', 'цена', 'стоимость', 'заказать', 'доставка', 'магазин'}
            found = [w for w in words if w in commercial]
            if found:
                suggested_minus.extend(found)
        
        if freq_quotes > 0 and freq_exact / freq_quotes < 0.5:
            warnings.append("Сильная потеря от кавычек к восклицательному знаку")
        
        return {
            'efficiency_score': round(efficiency_score, 2),
            'suggested_minus': suggested_minus,
            'warnings': warnings
        }


# Пример использования
if __name__ == "__main__":
    extractor = MinusWordsExtractor()
    
    # Тестовые фразы
    test_phrases = [
        {'phrase': 'купить телефон', 'freq_total': 10000, 'freq_quotes': 5000, 'freq_exact': 500},
        {'phrase': 'телефон цена', 'freq_total': 8000, 'freq_quotes': 4000, 'freq_exact': 400},
        {'phrase': 'ремонт телефона', 'freq_total': 3000, 'freq_quotes': 2000, 'freq_exact': 1500},
        {'phrase': 'телефон samsung', 'freq_total': 15000, 'freq_quotes': 10000, 'freq_exact': 8000},
    ]
    
    # Извлекаем минус-слова
    minus_words = extractor.extract_from_group(test_phrases)
    
    print("Найденные минус-слова:")
    for word in minus_words:
        print(f"  -{word}")
    
    # Анализ эффективности
    print("\nАнализ фраз:")
    for phrase_data in test_phrases:
        result = extractor.analyze_phrase_efficiency(
            phrase_data['phrase'],
            phrase_data['freq_total'],
            phrase_data.get('freq_quotes', 0),
            phrase_data['freq_exact']
        )
        print(f"\n{phrase_data['phrase']}:")
        print(f"  Эффективность: {result['efficiency_score']}%")
        if result['warnings']:
            print(f"  Предупреждения: {', '.join(result['warnings'])}")
        if result['suggested_minus']:
            print(f"  Рекомендуем минусовать: {', '.join(result['suggested_minus'])}")
