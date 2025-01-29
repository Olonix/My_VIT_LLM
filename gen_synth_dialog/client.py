import random
import pandas as pd
from langchain_compressa import ChatCompressa
from langchain.schema import HumanMessage, AIMessage

class Client:
    def __init__(self, api_key, order_file_path, client_type=None):
        self.api_key = api_key
        self.order_items = self.load_order(order_file_path) if order_file_path else None
        self.mentioned_items = set()
        self.llm = self.initialize_llm(api_key)
        self.order = []
        self.first_turn = True
        self.messages = []
        self.questions_asked = 0 # Счетчик заданных вопросов
        self.items_for_question = []


        self.client_types = {
    "friendly": """
                A friendly customer approaches the counter in a fast food restaurant.
                You greet the staff with a smile and are excited to order.
                You express gratitude and seem eager to enjoy their meal.""",
    "impatient": """
                An impatient customer walks up to the counter at a fast food restaurant.
                You seem rushed and are not interested in chatting.
                You are eager to get their food and leave as quickly as possible.""",
    "indecisive": """
                An indecisive customer is at the counter, unsure of what to order. 
                You hesitate and seem unsure about what to pick, often second-guessing themselves.""",
    "polite_and_respectful": """
                A polite and respectful customer approaches the counter with a calm demeanor. 
                You are considerate of the staff’s time and are very well-mannered throughout the ordering process. 
                You make their choice quickly, but are thankful and appreciative of the service.""",
    "regular": """
                A regular customer approaches the counter. 
                You know the menu well and order efficiently without unnecessary questions or conversation. 
                You are polite but brief."""
                            }

        self.question_probabilities = {
            "regular": 0.0,
            "friendly": 0.1,
            "impatient": 0.1,
            "polite_and_respectful": 0.2,
            "indecisive": 0.3,
        }

        self.set_client_type(client_type)


    def initialize_llm(self, api_key):
        return ChatCompressa(
            base_url="https://compressa-api.mil-team.ru/v1",
            api_key=api_key,
            temperature=0.4,
            max_tokens=60,
            stream="false"
        )

    def load_order(self, order_file_path):
        try:
            df = pd.read_csv(order_file_path, delimiter=';')
            if df.empty:
                raise ValueError(f"Файл заказов {order_file_path} пуст.")
            order_items = [(row['Item'], row['Quantity']) for _, row in df.iterrows()]
            return [f"{quantity} {item}" for item, quantity in order_items]
        except FileNotFoundError:
            raise FileNotFoundError(f"Файл {order_file_path} не найден.")
        except pd.errors.EmptyDataError:
            raise ValueError(f"Файл {order_file_path} пуст или поврежден.")
        except KeyError as e:
            raise KeyError(f"В файле {order_file_path} отсутствует столбец: {e}")

    def set_client_type(self, client_type):
        if client_type in self.client_types:
            self.client_type = client_type
            self.messages.append(("system", self.client_types[client_type]))
        else:
            self.client_type = random.choice(list(self.client_types.keys()))
            self.messages.append(("system", self.client_types[self.client_type]))

    def get_answer(self, cashier_answer):
        self.messages.append(HumanMessage(content=cashier_answer))

        if self.first_turn:
            self.first_turn = False
            prompt = f"""
                    You are at a fast-food restaurant. 
                    This is your first interaction with the cashier. 
                    Begin the conversation by politely initiating an order. 
                    Do not list items at this time.
                    Do not impersonate the cashier.
                    The cashier will respond, and you will then proceed to place your order. 
                    Do not include 'Customer:' or 'Sure' in your response. 
                    Examples: "May I place an order?", "I'd like to order, please.", "I'm ready to order." 
                    """
            return self._generate_client_response(prompt, [])

        elif self.order_items is None:
            return self._generate_client_response(f"""
                    The cashier said: '{cashier_answer}'. You're ordering food. 
                    Respond naturally according to your personality ({self.client_type}).
                    Do not impersonate the cashier.
                    """, [])

        else:
            unmentioned_items = [item for item in self.order_items if item not in self.mentioned_items]
            if not unmentioned_items:
                return self._generate_client_response("""
                    You have ordered all the items on your list. 
                    Respond with a short, polite closing phrase.
                    Do not impersonate the cashier.
                                                      
                    """, [])

            if self.items_for_question:
                selected_items = self.items_for_question
                self.items_for_question = []
                self.mentioned_items.update(selected_items)
                prompt = self._generate_order_prompt(cashier_answer, selected_items)
                return self._generate_client_response(prompt, selected_items)
            else:
                num_items_to_order = random.randint(1, len(unmentioned_items))
                selected_items = random.sample(unmentioned_items, num_items_to_order)

                question_probability = max(0, self.question_probabilities.get(self.client_type, 0.5) * (1 - self.questions_asked / 3))
                if random.random() < question_probability and self.questions_asked < 3:
                    self.questions_asked += 1
                    item_for_question = random.choice(selected_items)
                    self.items_for_question = selected_items
                    prompt = f"""
                                The cashier said: '{cashier_answer}'. 
                                You have a question about the {item_for_question}.
                                Ask a relevant question about ONLY this item.
                                Remember to include the item next time.
                                Do not order anything in this response.
                                Do not ask about other items.
                                Do not impersonate the cashier.
                            """
                else:
                    self.mentioned_items.update(selected_items)
                    prompt = self._generate_order_prompt(cashier_answer, selected_items)

                return self._generate_client_response(prompt, selected_items)


    def _generate_order_prompt(self, cashier_answer, selected_items):
        order_details = ", ".join(selected_items)
        prompt = f"""
                    The cashier said: '{cashier_answer}'. 
                    Your current order is: {', '.join(self.order)}. 
                    You want to order {order_details}.   
                    Respond naturally, adding this to your order
                    according to your personality ({self.client_type}). 
                    Do not order anything else at this time. Do not invent new items. 
                    Only order items from your predefined list.
                    Do not use closing phrases.
                    Do not impersonate the cashier.
                    """
        return prompt

    def _generate_client_response(self, prompt, selected_items):
        messages = self.messages.copy()
        messages.append(HumanMessage(content=prompt))
        response = self.llm.invoke(messages)
        self.messages.append(AIMessage(content=response.content))
        self.order.extend(selected_items)
        return response.content