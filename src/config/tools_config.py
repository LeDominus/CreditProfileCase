PAYMENT_TOOL_NAME = "calculate_payment"
MAX_TOOL_CALLS = 3

TOOL_RESULT_TEMPLATE = (
    "Результат инструмента {tool} (точный расчёт, используй эти числа как есть, "
    "не пересчитывай):\n{result_json}\n"
    "Сформулируй финальный ответ пользователю на русском языке на основе этих чисел."
)