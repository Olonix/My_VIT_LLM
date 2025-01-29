import os
import time
import json
from datetime import datetime, timedelta
from cashier import Cashier
from client import Client
from dotenv import load_dotenv

def analyze_dialog(api_key, output_file_path, order_file_path=None, client_type="regular"): # Добавлен параметр client_type
    start_time = time.time()
    client = Client(api_key, order_file_path, client_type=client_type) # Передаем client_type в Client
    cashier = Cashier(api_key)

    client_answer = client.get_answer("")

    dialog_text = f"Client: {client_answer}\n"
    counter = 0

    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(f"Client: {client_answer}\n")
        while True:
            cashier_answer = cashier.get_answer(client_answer)
            dialog_text += f"Cashier: {cashier_answer}\n"
            f.write(f"Cashier: {cashier_answer}\n")
            if any(word in cashier_answer.lower() for word in ["bye", "enjoy the meal", "enjoy your meal"]):
                break
            client_answer = client.get_answer(cashier_answer)
            dialog_text += f"Client: {client_answer}\n"
            f.write(f"Client: {client_answer}\n")
            counter += 1
            if counter > 10:
                break

    end_time = time.time()
    duration = timedelta(seconds=end_time - start_time)
    num_tokens = len(dialog_text.split())
    num_chars = len(dialog_text)
    return {
        "order_number": int(output_file_path.split('-')[-1].split('.')[0]) if not "RandomDialog" in output_file_path else output_file_path.split('-')[-1].split('.')[0],
        "start_time": datetime.now().isoformat(),
        "duration": str(duration),
        "num_tokens": num_tokens,
        "num_chars": num_chars
    }

if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv('API_COMPRESSA_KEY')
    orders_dir = "Orders"
    results_dir = "results"
    analysis_file = "analysis.csv"

    os.makedirs(results_dir, exist_ok=True)

    isRandom = False
    start_order = int(input("Введите начальный номер заказа (или -1 для случайной генерации): "))
    if start_order < 0:
        isRandom = True
        end_order = int(input("Введите количество генерируемых диалогов: "))
    else:
        end_order = int(input("Введите конечный номер заказа: "))

    client_type = input("Введите тип клиента (friendly, impatient, indecisive, polite_and_respectful, regular, или оставьте пустым для случайного выбора): ")

    with open(analysis_file, 'a', encoding='utf-8') as f_analysis:
        if os.stat(analysis_file).st_size == 0:
            f_analysis.write("Номер диалога;Время старта;Продолжительность;Количество токенов;Количество символов\n")

        if not isRandom:
            for order_number in range(start_order, end_order + 1):
                filename = f"Order-{order_number:04d}.csv"
                order_file_path = os.path.join(orders_dir, filename)
                if os.path.exists(order_file_path):
                    output_file_path = os.path.join(results_dir, f"Dialog-{order_number:04d}.txt")
                    try:
                        analysis_result = analyze_dialog(api_key, output_file_path, order_file_path, client_type if client_type else None) # Передаем client_type
                        f_analysis.write(f"{int(analysis_result['order_number']):04d};{analysis_result['start_time']};{analysis_result['duration']};{analysis_result['num_tokens']};{analysis_result['num_chars']}\n")
                        print(f"Диалог для заказа {order_number} записан в файл {output_file_path}")
                    except (FileNotFoundError, ValueError, KeyError, Exception) as e:
                        print(f"Ошибка при обработке файла {filename}: {e}")
                else:
                    print(f"Файл {filename} не найден.")
        else:
            for order_number in range(end_order):
                output_file_path = os.path.join(results_dir, f"RandomDialog-{order_number:04d}.txt")
                analysis_result = analyze_dialog(api_key, output_file_path, client_type=client_type if client_type else None)
                f_analysis.write(f"{int(analysis_result['order_number']):04d};{analysis_result['start_time']};{analysis_result['duration']};{analysis_result['num_tokens']};{analysis_result['num_chars']}\n")
                print(f"Диалог №{order_number} записан в файл {output_file_path}")