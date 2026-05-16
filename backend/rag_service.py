import os
from typing import List, Dict
from langchain_groq import ChatGroq
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama-3.3-70b-versatile"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

class RAGService:
    def __init__(self):
        self.embeddings = None # Lazy load
        self.llm = None       # Lazy load
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        self.vector_store = None
        self.current_video_id = None
        self.chat_memories: Dict[str, List] = {}

    def _ensure_initialized(self):
        """Ensures AI models are loaded only when needed."""
        if not self.embeddings:
            print("--- Initializing Embeddings Model (This may take a moment) ---")
            self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        if not self.llm:
            print("--- Initializing Groq LLM ---")
            if not GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY is missing from .env file!")
            self.llm = ChatGroq(groq_api_key=GROQ_API_KEY, model_name=MODEL_NAME, temperature=0)

    def initialize_vector_store(self, transcript: str, video_id: str, analysis: str = None):
        self._ensure_initialized()
        documents = [Document(page_content=transcript, metadata={"video_id": video_id, "type": "transcript"})]
        if analysis:
            documents.append(Document(page_content=analysis, metadata={"video_id": video_id, "type": "analysis"}))
        
        chunks = self.text_splitter.split_documents(documents)
        persist_directory = f"./data/chroma_{video_id}"
        
        self.vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=persist_directory
        )
        self.current_video_id = video_id
        self.chat_memories[video_id] = []

    def load_vector_store(self, video_id: str):
        self._ensure_initialized()
        persist_directory = f"./data/chroma_{video_id}"
        if os.path.exists(persist_directory):
            self.vector_store = Chroma(
                persist_directory=persist_directory,
                embedding_function=self.embeddings
            )
            self.current_video_id = video_id
            if video_id not in self.chat_memories:
                self.chat_memories[video_id] = []
            return True
        return False

    def generate_response(self, prompt_template: str, transcript: str = "", question: str = "", language: str = "English", response_length: str = "Medium") -> str:
        self._ensure_initialized()
        length_instruction = {
            "Short": "Be extremely concise.",
            "Medium": "Balanced response.",
            "Detailed": "Comprehensive explanation."
        }.get(response_length, "Medium")

        final_prompt = prompt_template.replace("{transcript}", transcript).replace("{question}", question)
        final_prompt = f"LANGUAGE: {language}\nLENGTH: {length_instruction}\n\n{final_prompt}"
        
        response = self.llm.invoke(final_prompt)
        return response.content

    def get_standalone_question(self, video_id: str, question: str) -> str:
        self._ensure_initialized()
        history = self.chat_memories.get(video_id, [])
        if not history:
            return question
            
        history_text = "\n".join([f"{'User' if isinstance(m, HumanMessage) else 'AI'}: {m.content}" for m in history[-5:]])
        
        rephrase_prompt = f"""
        Given history and a follow-up question, rephrase the follow-up question to be a standalone question.
        History: {history_text}
        Follow-up: {question}
        Standalone Question:"""
        
        response = self.llm.invoke(rephrase_prompt)
        return response.content.strip()

    def chat_with_video(self, video_id: str, question: str, language: str = "English") -> str:
        self._ensure_initialized()
        if not self.vector_store:
            return "Transcript not initialized."
        
        standalone_query = self.get_standalone_question(video_id, question)
        retriever = self.vector_store.as_retriever(search_type="mmr", search_kwargs={"k": 8})
        docs = retriever.invoke(standalone_query)
        
        context = "\n\n".join([f"[{doc.metadata.get('type')}]: {doc.page_content}" for doc in docs])
        
        system_prompt = f"""You are an Advanced Video Assistant. Answer in {language} based on Context below.
        Context: {context}"""

        history = self.chat_memories.get(video_id, [])
        messages = [SystemMessage(content=system_prompt)]
        for msg in history[-6:]:
            messages.append(msg)
        messages.append(HumanMessage(content=question))

        response = self.llm.invoke(messages)
        self.chat_memories[video_id].append(HumanMessage(content=question))
        self.chat_memories[video_id].append(AIMessage(content=response.content))
        
        return response.content
