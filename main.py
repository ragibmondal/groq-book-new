import streamlit as st
from groq import Groq
import json
import os
from io import BytesIO
from markdown import markdown
from weasyprint import HTML, CSS
import time
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Groqbook", page_icon="📚", layout="wide")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
    
    .stApp {
        font-family: 'Roboto', sans-serif;
    }
    
    h1, h2, h3 {
        color: var(--text-color);
    }
    
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        background-color: #3498db;
        color: white;
    }
    
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        border-radius: 10px;
    }
    
    .book-section {
        background-color: var(--background-color);
        border-left: 5px solid #3498db;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    .book-section h3 {
        color: var(--text-color);
    }
    
    .book-section p {
        color: var(--text-color);
    }
    
    .status-message {
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    
    .info {
        background-color: rgba(209, 236, 241, 0.2);
        color: #d1ecf1;
    }
    
    .success {
        background-color: rgba(212, 237, 218, 0.2);
        color: #d4edda;
    }
    
    .error {
        background-color: rgba(248, 215, 218, 0.2);
        color: #f8d7da;
    }
    
    @media (max-width: 768px) {
        .stColumn {
            flex: 1 1 100% !important;
            width: 100% !important;
        }
    }
</style>

<script>
    // JavaScript to set CSS variables based on the current theme
    const doc = window.parent.document;
    const styleEl = doc.createElement("style");
    doc.head.appendChild(styleEl);
    const setColors = () => {
        const theme = doc.body.getAttribute("data-theme");
        if (theme === "dark") {
            styleEl.innerHTML = `
                :root {
                    --background-color: #2c3e50;
                    --text-color: #ecf0f1;
                }
            `;
        } else {
            styleEl.innerHTML = `
                :root {
                    --background-color: #f8f9fa;
                    --text-color: #2c3e50;
                }
            `;
        }
    };
    const observer = new MutationObserver(() => setColors());
    observer.observe(doc.body, { attributes: true, attributeFilter: ["data-theme"] });
    setColors();
</script>
""", unsafe_allow_html=True)

class GenerationStatistics:
    def __init__(self, input_time=0, output_time=0, input_tokens=0, output_tokens=0, total_time=0, model_name="llama3-8b-8192"):
        self.input_time = input_time
        self.output_time = output_time
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_time = total_time
        self.model_name = model_name

    def get_input_speed(self):
        return self.input_tokens / self.input_time if self.input_time != 0 else 0
    
    def get_output_speed(self):
        return self.output_tokens / self.output_time if self.output_time != 0 else 0
    
    def add(self, other):
        if not isinstance(other, GenerationStatistics):
            raise TypeError("Can only add GenerationStatistics objects")
        
        self.input_time += other.input_time
        self.output_time += other.output_time
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.total_time += other.total_time

    def __str__(self):
        return (f"## Generation Statistics\n"
                f"- **Model**: {self.model_name}\n"
                f"- **Total Time**: {self.total_time:.2f}s\n"
                f"- **Output Speed**: {self.get_output_speed():.2f} tokens/s\n"
                f"- **Total Tokens**: {self.input_tokens + self.output_tokens}\n")

class Book:
    def __init__(self, structure):
        self.structure = structure
        self.contents = {title: "" for title in self.flatten_structure(structure)}
        self.placeholders = {title: st.empty() for title in self.flatten_structure(structure)}


    def flatten_structure(self, structure):
        sections = []
        for title, content in structure.items():
            sections.append(title)
            if isinstance(content, dict):
                sections.extend(self.flatten_structure(content))
        return sections

    def update_content(self, title, new_content):
        self.contents[title] += new_content
        self.display_content(title)

    def display_content(self, title):
        if self.contents[title].strip():
            self.placeholders[title].markdown(
                f"""
                <div class='book-section'>
                    <h3>{title}</h3>
                    <div>{self.contents[title]}</div>
                </div>
                """, 
                unsafe_allow_html=True
            )

    def display_structure(self, structure=None, level=2):
        if structure is None:
            structure = self.structure
        
        for title, content in structure.items():
            if self.contents[title].strip():
                st.markdown(f"<h{level} style='color: var(--text-color);'>{title}</h{level}>", unsafe_allow_html=True)
                self.display_content(title)
            if isinstance(content, dict):
                self.display_structure(content, level + 1)

    def get_markdown_content(self, structure=None, level=1):
        if structure is None:
            structure = self.structure
        
        markdown_content = ""
        for title, content in structure.items():
            if self.contents[title].strip():
                markdown_content += f"{'#' * level} {title}\n{self.contents[title]}\n\n"
            if isinstance(content, dict):
                markdown_content += self.get_markdown_content(content, level + 1)
        return markdown_content

def create_markdown_file(content: str) -> BytesIO:
    markdown_file = BytesIO()
    markdown_file.write(content.encode('utf-8'))
    markdown_file.seek(0)
    return markdown_file

def create_pdf_file(content: str) -> BytesIO:
    html_content = markdown(content, extensions=['extra', 'codehilite'])
    styled_html = f"""
    <html>
        <head>
            <style>
                @page {{ margin: 2cm; }}
                body {{ font-family: Arial, sans-serif; line-height: 1.6; font-size: 12pt; }}
                h1, h2, h3, h4, h5, h6 {{ color: #333366; margin-top: 1em; margin-bottom: 0.5em; }}
                p {{ margin-bottom: 0.5em; }}
                code {{ background-color: #f4f4f4; padding: 2px 4px; border-radius: 4px; font-family: monospace; font-size: 0.9em; }}
                pre {{ background-color: #f4f4f4; padding: 1em; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; }}
                blockquote {{ border-left: 4px solid #ccc; padding-left: 1em; margin-left: 0; font-style: italic; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 1em; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
    </html>
    """
    pdf_buffer = BytesIO()
    HTML(string=styled_html).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer

def generate_book_structure(prompt: str):
    completion = groq_client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[
            {"role": "system", "content": "Write in JSON format:\n\n{\"Title of section goes here\":\"Description of section goes here\",\n\"Title of section goes here\":{\"Title of section goes here\":\"Description of section goes here\",\"Title of section goes here\":\"Description of section goes here\",\"Title of section goes here\":\"Description of section goes here\"}}"},
            {"role": "user", "content": f"Write a comprehensive structure, omiting introduction and conclusion sections (forward, author's note, summary), for a long (>300 page) book on the following subject:\n\n<subject>{prompt}</subject>"}
        ],
        temperature=0.3,
        max_tokens=8000,
        top_p=1,
        stream=False,
        response_format={"type": "json_object"},
        stop=None,
    )

    usage = completion.usage
    statistics = GenerationStatistics(input_time=usage.prompt_time, output_time=usage.completion_time, input_tokens=usage.prompt_tokens, output_tokens=usage.completion_tokens, total_time=usage.total_time, model_name="llama3-70b-8192")

    return statistics, completion.choices[0].message.content

def generate_section(prompt: str):
    stream = groq_client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": "You are an expert writer. Generate a long, comprehensive, structured chapter for the section provided."},
            {"role": "user", "content": f"Generate a long, comprehensive, structured chapter for the following section:\n\n<section_title>{prompt}</section_title>"}
        ],
        temperature=0.3,
        max_tokens=8000,
        top_p=1,
        stream=True,
        stop=None,
    )

    for chunk in stream:
        tokens = chunk.choices[0].delta.content
        if tokens:
            yield tokens
        if x_groq := chunk.x_groq:
            if not x_groq.usage:
                continue
            usage = x_groq.usage
            statistics = GenerationStatistics(input_time=usage.prompt_time, output_time=usage.completion_time, input_tokens=usage.prompt_tokens, output_tokens=usage.completion_tokens, total_time=usage.total_time, model_name="llama3-8b-8192")
            yield statistics

def main():
    st.title("📚 Groqbook: Write Full Books using LLaMa3 on Groq")

    with st.sidebar:
        st.header("Generation Statistics")
        stats_placeholder = st.empty()

    col1, col2 = st.columns([3, 1])

    with col1:
        topic_text = st.text_area("What do you want the book to be about?", "", height=100)
        if st.button("Generate Book", use_container_width=True):
            if len(topic_text) < 10:
                st.error("Book topic must be at least 10 characters long")
            else:
                generate_book(topic_text, stats_placeholder)

    with col2:
        if 'book' in st.session_state:
            markdown_file = create_markdown_file(st.session_state.book.get_markdown_content())
            st.download_button(
                label='Download as Text',
                data=markdown_file,
                file_name='generated_book.txt',
                mime='text/plain',
                use_container_width=True
            )
            
            pdf_file = create_pdf_file(st.session_state.book.get_markdown_content())
            st.download_button(
                label='Download as PDF',
                data=pdf_file,
                file_name='generated_book.pdf',
                mime='application/pdf',
                use_container_width=True
            )

    if 'book' in st.session_state:
        st.header("Generated Book Content")
        st.session_state.book.display_structure()

def generate_book(topic_text, stats_placeholder):
    with st.spinner("Generating book structure..."):
        structure_stats, book_structure = generate_book_structure(topic_text)
        stats_placeholder.markdown(str(structure_stats), unsafe_allow_html=True)

    try:
        book_structure_json = json.loads(book_structure)
        book = Book(book_structure_json)
        st.session_state.book = book

        total_stats = GenerationStatistics(model_name="Combined")

        def stream_section_content(sections):
            for title, content in sections.items():
                if isinstance(content, str):
                    with st.spinner(f"Generating content for: {title}"):
                        content_stream = generate_section(f"{title}: {content}")
                        for chunk in content_stream:
                            if isinstance(chunk, GenerationStatistics):
                                total_stats.add(chunk)
                                stats_placeholder.markdown(str(total_stats), unsafe_allow_html=True)
                            elif chunk is not None:
                                st.session_state.book.update_content(title, chunk)
                elif isinstance(content, dict):
                    stream_section_content(content)

        stream_section_content(book_structure_json)
        st.success("Book generation completed!")

    except json.JSONDecodeError:
        st.error("Failed to decode the book structure. Please try again.")

if __name__ == "__main__":
    main()
