# The Darwin Archive
## Digital Twin of Charles Darwin

## Introduction

This project is a timeline-aware digital twin of Charles Darwin. It allows users to hold conversations with Darwin at different stages of his life and receive responses that reflect his knowledge, experiences, and scientific beliefs during that specific period.

Unlike a traditional chatbot, the system does not simply answer questions using modern knowledge and generic style. Instead, it combines historical documents, retrieval-based context, memory, and timeline awareness to recreate Darwin's perspective as accurately as possible. The system is designed to emulate Charles Darwin's knowledge, reasoning process, communication style, and scientific perspective. Its goal is to produce responses that are historically grounded and consistent with Darwin's life and work, making conversations feel as though the user is interacting directly with the scientist. A successful digital twin not only provides accurate information but also approaches questions, forms arguments, and maintains character in a manner consistent with the real individual.


For example:

* Darwin in 1835 discusses observations from the Beagle voyage.
* Darwin in 1840 treats natural selection as a developing private idea.
* Darwin in 1860 confidently discusses the theory after publishing *On the Origin of Species*.
* Darwin in 1870 acknowledges that concepts such as DNA are unknown in his era.

---

# Key Features

### Timeline Awareness

Users can select different years from Darwin's life.

The system adjusts its responses according to:

* Darwin's age
* Major life events
* Published works
* Scientific understanding available at that time

This ensures that Darwin's knowledge evolves realistically throughout the conversation.

---

### Retrieval-Augmented Generation (RAG)

The system uses a Retrieval-Augmented Generation pipeline to ground responses in Darwin's writings.

Instead of relying solely on the language model:

1. Relevant passages are retrieved from Darwin-related documents.
2. These passages are supplied to the model as context.
3. The final response is generated using both the retrieved sources and the user's question.

This reduces hallucinations and keeps responses historically grounded.

---

### Long-Term Memory

The application stores important details from previous conversations.

This allows Darwin to:

* Remember previously discussed topics
* Maintain conversational continuity
* Refer back to earlier interactions

The memory system helps create a more natural and persistent experience.

---

### Historical Persona

A dedicated persona layer controls:

* Vocabulary
* Tone
* Writing style
* Historical accuracy

Responses are generated in a style that reflects Darwin's manner of communication while remaining accessible to modern readers. The system also includes a Letter Mode, which recreates the tone, structure, and language patterns found in Darwin's personal correspondence, allowing users to experience responses in a form closer to his original writings.

---

# System Architecture

The workflow is shown below:

```text

Streamlit Interface
      │
      ▼
User Chooses Mode
      │
      ▼
User Selects Timeline
      │
      ▼
User Asks Question
      │
      ▼
Document Retrieval (RAG)
      │
      ▼
Optimisation Techniques
      │
      ▼
Long-Term Memory
      │
      ▼
Persona Construction
      │
      ▼
Gemini Model
      │
      ▼
Darwin's Response
      │
      ▼
Displayed to User
```

---

# Tech Stack

- Python
- Streamlit + Custom CSS
- Google Gemini API
- Gemini 2.5 Flash
- ChromaDB
- Retrieval-Augmented Generation (RAG)
- Sentence Transformers (`all-MiniLM-L6-v2`)
- Cross-Encoder (`ms-marco-MiniLM-L-6-v2`)
- Vector Embeddings
- Persistent Memory System

# Project Structure


- `app.py`: The main Streamlit application, handling the UI layout, state management, and chat interface.
- `persona.py`: Contains the sophisticated prompt engineering that defines Darwin's persona, knowledge limits, and voice across different historical eras.
- `rag.py`: Manages the ingestion, indexing, and advanced retrieval of Darwin's texts using a hybrid approach (ChromaDB semantic search and BM25 indexing) along with Cross-Encoder reranking.
- `memory.py`: Handles the reading, updating, and saving of user-specific long-term memory.
- `memory_dashboard.py`: Renders the user interface for the memory management dashboard.
- `conversation_summary.py`: Utility for summarizing and injecting contextually relevant conversation history into the model prompts.
- `ingest.py`: Script for ingesting and processing new source texts into the ChromaDB collection.


# Installation Guide

## 1. Clone the Repository

```bash
git clone https://github.com/muskaan-0908/DigitalTwinDarwin.git
cd DigitalTwinDarwin
```

---

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / Mac

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Obtain a Gemini API Key

1. Visit Google AI Studio.
2. Create a Gemini API key.
3. Copy the generated key.

---

## 5. Create a .env File

Create a file named:

```text
.env
```

Add:

```env
GEMINI_API_KEY=your_api_key_here
```

Replace the placeholder with your own API key.

---

## 6. Add Source Documents

Place Darwin-related documents inside the:

```text
data/
```

folder.

These may include:

* Books
* Essays
* Letters
* Notes

---

## 7. Build the Vector Database

Run:

```bash
python ingest.py
```

This step:

* Reads the source documents
* Splits them into chunks
* Generates embeddings
* Stores them inside ChromaDB

This only needs to be repeated when new documents are added.

---

## 8. Launch the Application

Run:

```bash
streamlit run app.py
```

Streamlit will display a local URL similar to:

```text
http://localhost:8501
```

Open that address in your browser.

---

# Example Questions

### 1835

* Tell me about the Galápagos Islands.

### 1840

* What is natural selection?

### 1860

* What is natural selection?

### 1870

* What is DNA?

### 1882

* How would you like to be remembered?

These examples demonstrate timeline awareness and historical consistency.

---

# Future Improvements

Potential extensions include:

* Additional historical figures
* Voice interaction
* Multi-person conversations
* Online deployment
* Enhanced memory ranking
* More factually grounded 
---


