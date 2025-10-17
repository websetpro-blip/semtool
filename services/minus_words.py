"""
Сервис для автоматического выделения минус-слов
Анализ частотности и генерация списков минус-слов как в Key Collector
"""
from collections import Counter, defaultdict
from typing import List, Dict, Set, Tuple, Iterable
import re

TOKEN_RE = re.compile(r"[a-zA-Zа-яА-Я0-9ёЁ]+", re.U)


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "")] 


class MinusWordsExtractor:
    """Класс для извлечения минус-слов из фраз"""

    def __init__(self):
        # Стоп-слова которые не могут быть минус-словами
        self.stop_words: Set[str] = {
            'в', 'на', 'с', 'для', 'из', 'по', 'к', 'о', 'и', 'а', 'но',
            'или', 'от', 'до', 'за', 'под', 'над', 'при', 'через', 'у',
        }

    def _build_stats(self, phrases: List[Dict]) -> Tuple[Counter, Dict[str, Dict[str, int]]]:
        """Подсчёт статистики встречаемости токенов и их частотностей.
        Возвращает (counter_by_token, freq_by_token), где freq_by_token[token] -> dict
        c ключами: freq_total, freq_exact, freq_quotes (агрегировано по максимальному значению из фраз).
        """
        token_counter: Counter = Counter()
        freq_by_token: Dict[str, Dict[str, int]] = defaultdict(lambda: {"freq_total": 0, "freq_exact": 0, "freq_quotes": 0})
        for row in phrases:
            text = row.get('phrase', '')
            toks = set(tokenize(text))
            ft = int(row.get('freq_total', 0) or 0)
            fe = int(row.get('freq_exact', 0) or 0)
            fq = int(row.get('freq_quotes', 0) or 0)
            for t in toks:
                token_counter[t] += 1
                # агрегируем максимумы, чтобы ориентироваться на "силу" слова
                f = freq_by_token[t]
                if ft > f['freq_total']:
                    f['freq_total'] = ft
                if fe > f['freq_exact']:
                    f['freq_exact'] = fe
                if fq > f['freq_quotes']:
                    f['freq_quotes'] = fq
        return token_counter, freq_by_token

    def extract_from_group(
        self,
        phrases: List[Dict],
        min_frequency: int = 100,
        rare_threshold: float = 0.1,
        freq_drop_threshold: float = 0.5,
    ) -> List[str]:
        """
        Извлечь минус-слова из группы фраз

        Args:
            phrases: Список словарей с ключами 'phrase', 'freq_total', 'freq_quotes', 'freq_exact'
            min_frequency: Минимальная частотность для анализа (freq_total)
            rare_threshold: Порог редкости слова (< 10% = редкое)
            freq_drop_threshold: Порог падения частотности (> 50% = минус-слово)
        """
        token_counter, freq_by_token = self._build_stats(phrases)
        total_phrases = max(1, len(phrases))

        candidates: List[str] = []
        for token, appear in token_counter.items():
            if token in self.stop_words:
                continue
            stats = freq_by_token[token]
            ft, fe, fq = stats['freq_total'], stats['freq_exact'], stats['freq_quotes']
            if ft < min_frequency:
                # очень низкая общая частотность — не берём в минус словами
                continue
            # относительная редкость в группе
            rarity = 1.0 - (appear / total_phrases)
            drop_exact = (ft - fe) / ft if ft else 0.0
            drop_quotes = (ft - fq) / ft if ft else 0.0
            if rarity >= rare_threshold and (drop_exact >= freq_drop_threshold or drop_quotes >= freq_drop_threshold):
                candidates.append(token)

        return sorted(set(candidates))

    def cross_minus_between_groups(
        self,
        groups: Dict[str, List[Dict]],
        rules: Dict[str, Iterable[str]] | None = None,
    ) -> Dict[str, Set[str]]:
        """Кросс-минусовка между группами. Для каждой группы находим слова,
        уникальные для других групп, и предлагаем их заминусовать.
        rules: словарь дополнительных правил по группам {group: [tokens_to_force_minus]}
        """
        group_tokens: Dict[str, Set[str]] = {}
        for g, rows in groups.items():
            toks: Set[str] = set()
            for r in rows:
                toks.update(tokenize(r.get('phrase', '')))
            group_tokens[g] = toks

        result: Dict[str, Set[str]] = {g: set() for g in groups}
        for g, toks in group_tokens.items():
            others = set().union(*[group_tokens[o] for o in group_tokens if o != g]) if len(group_tokens) > 1 else set()
            to_minus = (others - toks) - self.stop_words
            if rules and g in rules:
                to_minus.update(set(rules[g]))
            result[g] = set(sorted(to_minus))
        return result

    def analyze_efficiency(
        self,
        phrases: List[Dict],
    ) -> Dict[str, Dict[str, float]]:
        """Анализ эффективности по частотности: вычисляет падение по exact и quotes.
        Возвращает словарь token -> {freq_total, freq_exact, freq_quotes, drop_exact, drop_quotes}
        """
        _, freq_by_token = self._build_stats(phrases)
        analysis: Dict[str, Dict[str, float]] = {}
        for token, s in freq_by_token.items():
            ft = s['freq_total'] or 0
            fe = s['freq_exact'] or 0
            fq = s['freq_quotes'] or 0
            drop_e = (ft - fe) / ft if ft else 0.0
            drop_q = (ft - fq) / ft if ft else 0.0
            analysis[token] = {
                'freq_total': float(ft),
                'freq_exact': float(fe),
                'freq_quotes': float(fq),
                'drop_exact': round(drop_e, 4),
                'drop_quotes': round(drop_q, 4),
            }
        return analysis

    def recommendations(
        self,
        phrases: List[Dict],
        min_frequency: int = 100,
        rare_threshold: float = 0.1,
        freq_drop_threshold: float = 0.5,
    ) -> Dict[str, List[str]]:
        """Рекомендации по минусованию ключей: выдаёт список кандидатов и аргументы."""
        candidates = self.extract_from_group(
            phrases,
            min_frequency=min_frequency,
            rare_threshold=rare_threshold,
            freq_drop_threshold=freq_drop_threshold,
        )
        analysis = self.analyze_efficiency(phrases)
        # сортируем кандидатов по суммарному падению
        ranked = sorted(
            candidates,
            key=lambda t: (analysis.get(t, {}).get('drop_exact', 0) + analysis.get(t, {}).get('drop_quotes', 0)),
            reverse=True,
        )
        return {
            'candidates': ranked,
            'strong': [t for t in ranked if (analysis.get(t, {}).get('drop_exact', 0) >= 0.6 or analysis.get(t, {}).get('drop_quotes', 0) >= 0.6)],
            'medium': [t for t in ranked if (analysis.get(t, {}).get('drop_exact', 0) >= 0.4 or analysis.get(t, {}).get('drop_quotes', 0) >= 0.4)],
        }

    def auto_export_direct(
        self,
        minus_map: Dict[str, Iterable[str]] | Iterable[str],
    ) -> str:
        """Автоэкспорт для Direct. Возвращает строку с минус-словами по формату.
        minus_map: либо список слов (общие), либо словарь {group: [minus-words]}
        """
        def fmt(words: Iterable[str]) -> str:
            # фильтруем служебные и пустые
            uniq = [w.strip() for w in words if w and w.strip() and w.strip() not in self.stop_words]
            return "-" + " -".join(sorted(set(uniq))) if uniq else ""

        if isinstance(minus_map, dict):
            lines = []
            for g, ws in minus_map.items():
                line = f"{g}: {fmt(ws)}"
                lines.append(line)
            return "\n".join(lines)
        else:
            return fmt(minus_map)  # type: ignore[arg-type]


# functions для авто-выделения из групп и анализа (по примеру из файла задач)
# Предполагаем унифицированный интерфейс

def func_extract_group(payload: Dict) -> Dict:
    extractor = MinusWordsExtractor()
    phrases: List[Dict] = payload.get('phrases', [])
    params = payload.get('params', {})
    result = extractor.extract_from_group(
        phrases,
        min_frequency=int(params.get('min_frequency', 100)),
        rare_threshold=float(params.get('rare_threshold', 0.1)),
        freq_drop_threshold=float(params.get('freq_drop_threshold', 0.5)),
    )
    return {"minus": result}


def func_cross_minus(payload: Dict) -> Dict:
    extractor = MinusWordsExtractor()
    groups: Dict[str, List[Dict]] = payload.get('groups', {})
    rules = payload.get('rules')
    result = extractor.cross_minus_between_groups(groups, rules)
    # сериализация сетов
    return {g: sorted(list(v)) for g, v in result.items()}


def func_analyze(payload: Dict) -> Dict:
    extractor = MinusWordsExtractor()
    phrases: List[Dict] = payload.get('phrases', [])
    return extractor.analyze_efficiency(phrases)


def func_recommend(payload: Dict) -> Dict:
    extractor = MinusWordsExtractor()
    phrases: List[Dict] = payload.get('phrases', [])
    params = payload.get('params', {})
    return extractor.recommendations(
        phrases,
        min_frequency=int(params.get('min_frequency', 100)),
        rare_threshold=float(params.get('rare_threshold', 0.1)),
        freq_drop_threshold=float(params.get('freq_drop_threshold', 0.5)),
    )


def func_export_direct(payload: Dict) -> Dict:
    extractor = MinusWordsExtractor()
    minus_map = payload.get('minus')
    return {"export": extractor.auto_export_direct(minus_map)}
