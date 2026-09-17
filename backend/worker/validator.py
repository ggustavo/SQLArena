import re
from collections import Counter
from typing import Any, Dict, List, Tuple


class EvaluationResult:
    def __init__(self, score: float, status: str, breakdown: Dict[str, Any], error_message: str = ""):
        self.score = score
        self.status = status
        self.breakdown = breakdown
        self.error_message = error_message


class ResultValidator:
    """
    Single-responsibility component for evaluating result set similarity between
    expected query output and student query output.
    """

    @classmethod
    def evaluate(
        cls,
        expected_cols: List[str],
        expected_rows: List[Tuple],
        student_cols: List[str],
        student_rows: List[Tuple],
        student_query: str,
    ) -> EvaluationResult:
        exp_len = len(expected_rows)
        stu_len = len(student_rows)

        # Rule check: "A validação exige o uso de ORDER BY caso o resultado possua mais de uma tupla."
        order_by_required = exp_len > 1
        has_order_by = bool(re.search(r"\border\s+by\b", student_query, re.IGNORECASE))

        # 1. Column Name & Count Match (Weight: 25%)
        exp_col_set = [c.lower() for c in expected_cols]
        stu_col_set = [c.lower() for c in student_cols]
        col_overlap = sum((Counter(exp_col_set) & Counter(stu_col_set)).values())
        max_cols = max(len(expected_cols), len(student_cols), 1)
        col_score = (col_overlap / max_cols) * 25.0

        # 2. Row Count Match (Weight: 25%)
        row_diff = abs(exp_len - stu_len)
        row_count_score = max(0.0, 1.0 - (row_diff / max(exp_len, 1))) * 25.0

        # Standardize row representation
        def normalize_row(row):
            return tuple(str(val).strip() if val is not None else "NULL" for val in row)

        exp_norm = [normalize_row(r) for r in expected_rows]
        stu_norm = [normalize_row(r) for r in student_rows]

        # 3. Data Content Match - Multiset Overlap (Weight: 30%)
        exp_counter = Counter(exp_norm)
        stu_counter = Counter(stu_norm)
        data_overlap = sum((exp_counter & stu_counter).values())
        data_score = (data_overlap / max(exp_len, 1)) * 30.0

        # 4. Ordering Match (Weight: 20%)
        order_score = 0.0
        warning_msg = ""
        if not order_by_required or exp_len <= 1:
            order_score = 20.0
        else:
            if has_order_by:
                min_len = min(exp_len, stu_len)
                in_order = sum(1 for i in range(min_len) if exp_norm[i] == stu_norm[i])
                order_score = (in_order / max(exp_len, 1)) * 20.0
            else:
                order_score = 0.0
                warning_msg = "Result contains multiple rows but query omits the mandatory ORDER BY clause."

        total_score = round(col_score + row_count_score + data_score + order_score, 2)
        total_score = max(0.0, min(100.0, total_score))

        status_str = "SUCCESS" if total_score >= 100.0 else "WRONG_RESULT"

        breakdown = {
            "columns_score": round(col_score, 2),
            "row_count_score": round(row_count_score, 2),
            "data_score": round(data_score, 2),
            "order_score": round(order_score, 2),
            "order_by_required": order_by_required,
            "has_order_by": has_order_by,
            "expected_rows_count": exp_len,
            "student_rows_count": stu_len,
        }

        return EvaluationResult(
            score=total_score,
            status=status_str,
            breakdown=breakdown,
            error_message=warning_msg,
        )
