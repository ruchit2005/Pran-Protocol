"""
Document Q&A Chain - Answer questions about uploaded medical documents
"""
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


class DocumentQAChain:
    """Answer questions about user's uploaded medical documents"""
    
    def __init__(self, llm):
        self.llm = llm
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a medical document analyst helping users understand their medical reports.

IMPORTANT RULES:
1. Base your answers ONLY on the provided document content
2. If the document doesn't contain the information, say "I don't see that information in your document"
3. Explain medical terms in simple language
4. If values are abnormal, mention it clearly
5. DO NOT make treatment recommendations - only explain what's in the document
6. Cite the specific document when answering

Be conversational and helpful. If the user's question is vague, ask for clarification."""),
            ("user", """{context}

User Question: {query}

Provide a clear, helpful answer based on the document content above.""")
        ])
        
        self.chain = self.prompt | self.llm | StrOutputParser()
    
    def run(self, query: str, document_context: str) -> str:
        """
        Answer question about documents
        
        Args:
            query: User's question
            document_context: Full text and analysis from documents
            
        Returns:
            Answer based on document content
        """
        try:
            # Try with full timeout first
            response = self.chain.invoke({
                "query": query,
                "context": document_context
            })
            return response
        except TimeoutError as e:
            # Retry once with summarized context if timeout
            try:
                print(f"   ⚠️ Timeout on first attempt, retrying with summarized context...")
                summarized_context = document_context[:3000] + "\n...[document truncated for faster processing]..."
                response = self.chain.invoke({
                    "query": query,
                    "context": summarized_context
                })
                return response
            except Exception as retry_error:
                return f"I encountered a timeout analyzing your documents. Your document may be too long. Please try asking a more specific question about a particular section."
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                return f"The request timed out while analyzing your document. Please try again or ask a more specific question about a particular test or section."
            return f"I encountered an error analyzing your documents: {error_msg}"


class ConversationalSymptomChecker:
    """Multi-turn symptom checker that asks follow-up questions"""
    
    def __init__(self, llm):
        self.llm = llm
        
        self.assessment_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a medical assistant conducting a symptom assessment. 

YOUR GOAL: Gather enough information to provide accurate recommendations.

CONVERSATION FLOW:
1. If the user's initial message is vague (e.g., "I have burns", "headache", "stomach pain"):
   - Ask MAXIMUM 2 focused questions to understand the most critical details:
     * Severity (mild/moderate/severe) AND Location (where exactly)
     * OR Duration (how long) AND Context (how it started)
   - Combine multiple aspects in ONE question when possible
   - Keep questions natural and conversational

2. After getting answers, respond with:
   ASSESSMENT_COMPLETE: [detailed description of symptoms]

3. DO NOT ask more than 2 follow-up questions total
4. If user provides reasonable detail in their first or second response, mark ASSESSMENT_COMPLETE

EXAMPLES:
User: "I have burns"
You: "I'm sorry to hear that. Can you tell me where the burn is located and how severe it is (just red, or are there blisters)?"

User: "It's on my hand with blisters from a hot pan"
You: "ASSESSMENT_COMPLETE: Second-degree burn on hand with blisters, caused by hot pan contact"

User: "I have a headache"
You: "I'm sorry to hear that. How severe is the pain (1-10) and how long have you had it?"

User: "About 7/10 for 2 days"
You: "ASSESSMENT_COMPLETE: Moderate to severe headache (7/10 intensity) lasting 2 days"

Be empathetic, clear, and professional. Get to recommendations quickly."""),
            ("user", """{conversation_history}

Current message: {query}

Respond naturally. Either ask a follow-up question OR mark as ASSESSMENT_COMPLETE.""")
        ])
        
        self.chain = self.assessment_prompt | self.llm | StrOutputParser()
    
    def run(self, query: str, conversation_history: str = "") -> Dict[str, Any]:
        """
        Process symptom with conversational follow-ups
        
        Returns:
            {
                "needs_followup": bool,
                "response": str,  # Question or final assessment
                "symptoms": list  # Extracted if complete
            }
        """
        try:
            # Count how many bot questions have been asked
            question_count = conversation_history.count("You:") if conversation_history else 0
            
            # Force completion after 2 questions
            if question_count >= 2:
                # Extract symptoms from the conversation and complete
                return {
                    "needs_followup": False,
                    "response": "Based on what you've shared, let me find the best recommendations for you...",
                    "symptoms": [query],  # Use latest user input
                    "complete": True
                }
            
            response = self.chain.invoke({
                "query": query,
                "conversation_history": conversation_history or "New conversation"
            })
            
            # Check if assessment is complete
            if "ASSESSMENT_COMPLETE:" in response:
                symptoms_text = response.split("ASSESSMENT_COMPLETE:")[1].strip()
                return {
                    "needs_followup": False,
                    "response": "Based on what you've shared, let me find the best recommendations for you...",
                    "symptoms": [symptoms_text],
                    "complete": True
                }
            else:
                # Still gathering information
                return {
                    "needs_followup": True,
                    "response": response,
                    "symptoms": [],
                    "complete": False
                }
                
        except Exception as e:
            return {
                "needs_followup": False,
                "response": f"I encountered an error: {str(e)}",
                "symptoms": [],
                "complete": False
            }
