"""
Financial AI Chatbot using spaCy NLP
Provides answers to financial questions based on semantic similarity matching
"""

import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Tuple, Optional
import spacy

class FinancialChatbot:
    """AI-powered financial chatbot using spaCy for semantic understanding"""

    def __init__(self, model_name: str = 'en_core_web_md', data_file: str = 'financial_qa_data.json'):
        """
        Initialize the financial chatbot

        Args:
            model_name: spaCy language model to use
            data_file: JSON file containing training Q&A data
        """
        try:
            self.nlp = spacy.load(model_name)
            print(f"Loaded spaCy model: {model_name}")
        except OSError:
            print(f"Model {model_name} not found. Downloading...")
            spacy.cli.download(model_name)
            self.nlp = spacy.load(model_name)

        # Load training data
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                self.qa_data = json.load(f)
            print(f"Loaded {len(self.qa_data)} Q&A pairs from {data_file}")
        except FileNotFoundError:
            print(f"Warning: {data_file} not found. Using empty data.")
            self.qa_data = []

        # Pre-compute vector representations for all questions
        self.question_vectors = []
        self.questions = []
        self.answers = []

        for item in self.qa_data:
            question = item.get('question', '')
            answer = item.get('answer', '')

            if question and answer:
                # Process question with spaCy
                doc = self.nlp(question)
                vector = doc.vector

                self.questions.append(question)
                self.question_vectors.append(vector)
                self.answers.append(answer)

        print(f"Pre-computed vectors for {len(self.questions)} questions")

    def get_semantic_answer(self, user_question: str, top_k: int = 1) -> Tuple[str, float]:
        """
        Find the most semantically similar answer for a user question

        Args:
            user_question: The question asked by the user
            top_k: Number of top similar answers to consider

        Returns:
            Tuple of (answer, confidence_score)
        """
        if not self.question_vectors:
            return "I'm sorry, I don't have information about that question yet.", 0.0

        # Process user question
        user_doc = self.nlp(user_question)
        user_vector = user_doc.vector.reshape(1, -1)

        # Calculate similarities with all training questions
        similarities = []
        for i, q_vector in enumerate(self.question_vectors):
            if q_vector.size > 0:  # Check if vector is not empty
                q_vector_reshaped = q_vector.reshape(1, -1)
                similarity = cosine_similarity(user_vector, q_vector_reshaped)[0][0]
                similarities.append((i, similarity))
            else:
                similarities.append((i, 0.0))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Get top-k results
        top_results = similarities[:top_k]

        # Calculate average confidence
        avg_confidence = np.mean([score for _, score in top_results])

        # If confidence is too low, return a generic response
        if avg_confidence < 0.3:  # 0.3 is a reasonable threshold
            return self._get_generic_response(user_question), avg_confidence

        # Return the best matching answer
        best_idx = top_results[0][0]
        return self.answers[best_idx], avg_confidence

    def _get_generic_response(self, user_question: str) -> str:
        """
        Provide a generic financial advice response when no specific match is found
        """
        generic_responses = [
            "That's an interesting financial question. Based on general financial principles, it's important to consider your financial goals, risk tolerance, and current situation. Consider consulting with a financial advisor for personalized advice.",
            "While I don't have a specific answer for that question, remember that good financial habits include budgeting, saving regularly, investing wisely, and managing debt responsibly. What specific financial goal are you working towards?",
            "That's a complex financial topic. Generally, financial decisions should align with your income level, time horizon, and risk tolerance. Building an emergency fund, reducing high-interest debt, and investing for the long term are universally good practices.",
            "I don't have detailed information about that specific topic, but sound financial planning always involves understanding your needs, setting clear goals, and making informed decisions. Consider reviewing your current financial situation and objectives."
        ]

        # Select response based on question length (simple randomization)
        return generic_responses[hash(user_question) % len(generic_responses)]

    def get_financial_insights(self, user_income: float = 0, item_price: float = 0, emi: float = 0) -> dict:
        """
        Generate financial insights based on user's financial data

        Args:
            user_income: User's monthly income
            item_price: Price of item they're considering
            emi: Monthly EMI for the item

        Returns:
            Dictionary with financial analysis and insights
        """
        insights = {
            'affordability_score': 5.0,
            'risk_assessment': 'Analysis completed',
            'recommendation': 'Please provide more financial details for better analysis',
            'advice': []
        }

        if user_income > 0:
            if emi > 0:
                emi_ratio = (emi / user_income) * 100

                # Calculate affordability score
                if emi_ratio <= 20:
                    insights['affordability_score'] = 9.0
                    insights['risk_assessment'] = "Excellent – This EMI is very comfortable for your income."
                elif emi_ratio <= 30:
                    insights['affordability_score'] = 7.5
                    insights['risk_assessment'] = "Good – EMI is manageable but monitor your expenses."
                elif emi_ratio <= 40:
                    insights['affordability_score'] = 5.0
                    insights['risk_assessment'] = "Caution – EMI may strain your finances. Consider a larger down payment or longer tenure."
                else:
                    insights['affordability_score'] = 2.0
                    insights['risk_assessment'] = "High Risk – EMI exceeds 40% of income. Not advisable."

                # Add specific advice based on the ratio
                if item_price > 0:
                    down_payment = item_price * 0.20  # Assume 20% down payment
                    loan_amount = item_price - down_payment

                    insights['advice'] = [
                        f"You're considering an item worth ₹{item_price:,.0f}",
                        f"Recommended down payment: ₹{down_payment:,.0f} (20%)",
                        f"Estimated loan amount: ₹{loan_amount:,.0f}",
                        ".1f"                        f"Your monthly income: ₹{user_income:,.0f}",
                        ".1f"
                    ]
                else:
                    insights['advice'] = [
                        f"Your monthly income: ₹{user_income:,.0f}",
                        ".1f"
                    ]
            else:
                insights['advice'] = [
                    f"Your monthly income: ₹{user_income:,.0f}",
                    "Consider investing in mutual funds or systematic investment plans for long-term growth."
                ]

        return insights

# Global chatbot instance
_chatbot = None

def get_chatbot() -> FinancialChatbot:
    """Get or create the global chatbot instance"""
    global _chatbot
    if _chatbot is None:
        _chatbot = FinancialChatbot()
    return _chatbot

def answer_financial_question(question: str, user_income: float = 0, item_price: float = 0, emi: float = 0) -> dict:
    """
    Main function to answer financial questions using NLP

    Args:
        question: User's question
        user_income: User's monthly income
        item_price: Price of item they want to purchase
        emi: Monthly EMI

    Returns:
        Dictionary with answer and financial insights
    """
    chatbot = get_chatbot()

    # Get semantic answer
    answer, confidence = chatbot.get_semantic_answer(question)

    # Get financial insights
    insights = chatbot.get_financial_insights(user_income, item_price, emi)

    return {
        'message': answer,
        'confidence': confidence,
        'affordability_score': insights['affordability_score'],
        'risk_assessment': insights['risk_assessment'],
        'recommendation': insights['recommendation'],
        'financial_analysis': insights['advice'],
        'analysis_available': user_income > 0
    }

if __name__ == "__main__":
    # Test the chatbot
    chatbot = FinancialChatbot()

    test_questions = [
        "How should I save money?",
        "What's compound interest?",
        "Should I invest in stocks?",
        "How much emergency fund do I need?"
    ]

    for question in test_questions:
        answer, confidence = chatbot.get_semantic_answer(question)
        print(f"\nQ: {question}")
        print(f"A: {answer}")
        print(".3f")
        print("-" * 50)
