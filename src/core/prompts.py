"""Prompt templates for the Q&A RAG agent."""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


RAG_SYSTEM_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a helpful Q&A assistant. Answer the user's question using ONLY "
        "the provided context below. If the context does not contain enough "
        "information, say so clearly.\n\n"
        "For every claim you make, cite the source document name and page "
        "(if available) in parentheses.\n\n"
        "Context:\n{context}",
    ),
    MessagesPlaceholder("chat_history"),
    ("human", "{question}"),
])


FALLBACK_SYSTEM_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a helpful Q&A assistant. The user asked a question but no "
        "relevant documents were found in the knowledge base. Answer from "
        "your general knowledge to the best of your ability.\n\n"
        "Start your answer by briefly noting that no matching documents were "
        "found, then provide your best answer.",
    ),
    MessagesPlaceholder("chat_history"),
    ("human", "{question}"),
])


WEB_SEARCH_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a helpful Q&A assistant. Answer the user's question using "
        "the web search results provided below. Cite the source URL for "
        "each claim you make.\n\n"
        "Web Search Results:\n{context}",
    ),
    MessagesPlaceholder("chat_history"),
    ("human", "{question}"),
])


DIRECT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a helpful assistant. Answer the user's question from your "
        "general knowledge clearly and concisely.",
    ),
    MessagesPlaceholder("chat_history"),
    ("human", "{question}"),
])
