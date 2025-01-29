import pandas as pd
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter
from langchain_compressa import ChatCompressa
import re

class Cashier:
    menu_file = "menu.csv"
    menu_data = pd.read_csv(menu_file)
    menu_items = menu_data['Item'].tolist()

    menu_texts = []
    for category, group in menu_data.groupby('Category'):
        items = ', '.join(group['Item'])
        menu_texts.append(f"In our menu in the category {category} we ONLY have: {items}.")
    
    documents = [
        "What would you like to order?",
        "According to your preferences", 
        "I can offer you",
        "Could you please clarify",
        "What kind of drink you would like?",
        "Your order:", 
        "Is everything correct?",
        "Something else?",
    ]

    # documents.extend(menu_texts)
    documents.extend(menu_items)

    def __init__(self, api_key):
        self.api_key = api_key
        self.current_order = []  # Список для хранения текущего заказа
        text_splitter = CharacterTextSplitter(chunk_size=100, chunk_overlap=10)
        docs = text_splitter.split_text(" ".join(self.documents))

        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.vectorstore = FAISS.from_texts(docs, embeddings)


        self.llm = ChatCompressa(
            base_url="https://compressa-api.mil-team.ru/v1",
            api_key=api_key,
            temperature=0,
        )
        
        self.messages = [
            ("system", f"""You are a cashier at the fast food restaurant 'Vkusno i tochka'. 
                          I am a customer who came to 'Vkusno i tochka' to place an order. 
                          Your task is to help me with the order and clarify the details. 
                          If what I say is not on the menu, say you don't have it.
                          Say ONLY the correct names of items on the menu: {self.menu_texts}.
                          In one list: {self.menu_items}.
                          Speak briefly, only to the point. There is NO NEED to list the entire menu."""),
        ]

    def get_answer(self, client_answer):
        # Проверяем, завершен ли заказ
        end_phrases = [
            "that's all", "nothing else", "i'm done", "that will be all",
            "no more", "that's everything", "finish my order", "complete the order",
            "looking forward", "look forward", "that's it", 
            # "next time", "everything sounds correct", 
            "can't wait", "i have everything",
        ]

        # Регулярное выражение для шаблона "Have a * day"
        end_pattern = re.compile(r"have a \w+ day", re.IGNORECASE)

        if any(phrase in client_answer.lower() for phrase in end_phrases) or re.search(end_pattern, client_answer.lower()):
            # Генерируем ответ с финальным заказом
            self.messages.append(("system", f"I finished voicing my order, now analyze all my messages: {self.current_order} and voice his order yourself. It is strictly forbidden to voice anything that is not on the menu. Also, don't forget to say 'enjoy the meal' at the end."))
            self.current_order = []  # Очищаем текущий заказ
        else:
            # Добавляем позицию в текущий заказ
            self.current_order.append(client_answer)

            # Извлечение релевантной информации из базы знаний
            docs = self.vectorstore.similarity_search(client_answer, k=2)  # Ищем 2 наиболее релевантных фрагмента
            context = " ".join([doc.page_content for doc in docs])

            # print(context)

            # Добавляем контекст в сообщения
            self.messages.append(("system", f"Context: {context}"))
            self.messages.append(("human", client_answer))
            self.messages.append(("system", "If what I say is not on the menu, say you don't have it. If I say something similar to what is on the menu, pronounce it exactly as it sounds on the menu."))

         # Генерация ответа
        ai_msg = self.llm.invoke(self.messages)
        response = ai_msg.content

        # Добавляем ответ в историю
        self.messages.append(("assistant", response))

        return response
