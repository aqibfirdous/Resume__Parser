from flask import Flask, request, jsonify, render_template
from sentence_transformers import SentenceTransformer, util
from langdetect import detect
import PyPDF2
import docx2txt
import io
import re
import hashlib
from flask_caching import Cache

# Flask app configuration
app = Flask(__name__)
app.config['CACHE_TYPE'] = 'SimpleCache'
cache = Cache(app)

# Load pre-trained Sentence-BERT model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Dynamic keyword dictionary
industry_keywords = {
    "technical_roles": [
        "python", "java", "javascript", "c++", "c#", "php", "ruby", "swift", "r", "go", "typescript", "html", "css",
        "sql", "matlab", "kotlin", "scala", "rust", "bash", "shell", "django", "flask", "spring", "react", "angular",
        "vue.js", "express", "node.js", "ruby on rails", "asp.net", "jquery", "tensorflow", "pytorch", "keras",
        "scikit-learn", "pandas", "numpy", "opencv", "selenium", "bootstrap", "aws", "azure", "google cloud", "docker",
        "kubernetes", "jenkins", "ansible", "terraform", "ci/cd", "git", "github", "gitlab", "bitbucket",
        "elasticsearch", "apache", "nginx", "travis ci", "data mining", "etl", "big data", "machine learning",
        "deep learning", "nlp", "computer vision", "predictive analytics", "artificial intelligence", "hadoop",
        "spark", "tableau", "power bi", "d3.js", "looker", "mysql", "postgresql", "mongodb", "oracle", "cassandra",
        "redis", "mariadb", "sql server", "dynamodb", "sqlite", "firebase", "selenium", "junit", "testng",
        "cucumber", "mocha", "jasmine", "jest", "appium", "postman", "loadrunner", "soapui", "qtp", "jira", "zephyr"
    ],
    "non_technical_roles": [
        "requirements gathering", "process mapping", "stakeholder analysis", "uml", "bpmn", "gap analysis",
        "functional specifications", "swot analysis", "root cause analysis", "process improvement", "as-is/to-be",
        "user stories", "agile", "scrum", "confluence", "roadmap planning", "prioritization", "backlog grooming",
        "sprint planning", "user personas", "wireframing", "mvp", "metrics tracking", "okrs", "kpis", "budgeting",
        "resource allocation", "risk management", "kanban", "manual testing", "automation testing", "defect tracking",
        "bug reporting", "qa strategy", "black-box testing", "white-box testing", "load testing", "uat",
        "regression testing"
    ],
    "business_roles": [
        "market analysis", "competitor analysis", "lead generation", "crm", "sales pipeline", "b2b", "b2c",
        "segmentation", "digital marketing", "seo", "sem", "content marketing", "social media", "branding", "hubspot",
        "salesforce", "google analytics", "a/b testing", "campaign management", "client relations", "ticketing systems",
        "customer feedback", "service desk", "customer lifecycle", "onboarding", "retention", "escalation", "slas",
        "zendesk", "freshdesk", "intercom", "empathy"
    ],
    "executive_roles": [
        "strategic planning", "vision setting", "business development", "growth hacking", "change management",
        "p&l management", "financial modeling", "risk assessment", "stakeholder management", "innovation",
        "organizational design", "leadership", "decision-making", "negotiation", "investor relations", "budgeting",
        "forecasting", "financial analysis", "cash flow management", "cost-benefit analysis", "erp", "procurement",
        "inventory management", "netsuite", "sap", "quickbooks", "excel", "data-driven decision-making"
    ]
}

# Helper: Extract text from file based on extension
def extract_text(file):
    ext = file.filename.split('.')[-1].lower()
    if ext == 'pdf':
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
            return " ".join([page.extract_text() or "" for page in pdf_reader.pages])
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""
    elif ext == 'docx':
        try:
            return docx2txt.process(io.BytesIO(file.read()))
        except Exception as e:
            print(f"Error reading DOCX: {e}")
            return ""
    elif ext == 'txt':
        try:
            return file.read().decode('utf-8')
        except Exception as e:
            print(f"Error reading TXT: {e}")
            return ""
    return ""

def preprocess_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def get_keywords_from_text(text):
    text_words = set(text.split())
    return [kw for role in industry_keywords.values() for kw in role if kw in text_words]

def suggest_improvements(missing_keywords):
    if not missing_keywords:
        return ["Your resume is well-optimized for this role!"]
    tips = ["Consider adding more job-specific keywords to your resume."]
    # Suggest up to 5 missing keywords
    for kw in list(missing_keywords)[:5]:
        tips.append(f"Include keyword: {kw}")
    return tips

# Compute a unique hash for caching based on both texts
def compute_hash(resume_text, job_desc_text):
    hash_input = (resume_text + job_desc_text).encode('utf-8')
    return hashlib.md5(hash_input).hexdigest()

# Cache the semantic score computation
def compute_semantic_score(resume_text, job_desc_text):
    cache_key = f"semantic_{compute_hash(resume_text, job_desc_text)}"
    cached_score = cache.get(cache_key)
    if cached_score is not None:
        return cached_score
    embeddings = model.encode([resume_text, job_desc_text], convert_to_tensor=True)
    similarity = util.pytorch_cos_sim(embeddings[0], embeddings[1])
    score = round(float(similarity.item()) * 100, 2)
    cache.set(cache_key, score, timeout=300)  # Cache for 5 minutes
    return score

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ats_score', methods=['POST'])
def ats_score():
    try:
        resume_file = request.files.get('resume')
        job_desc_file = request.files.get('job_description')
        valid_ext = ['pdf', 'docx', 'txt']

        # Validate file extensions
        if not (resume_file and job_desc_file and
                resume_file.filename.split('.')[-1].lower() in valid_ext and
                job_desc_file.filename.split('.')[-1].lower() in valid_ext):
            return jsonify({'error': 'Invalid file format. Only PDF, DOCX, and TXT files are allowed.'}), 400

        # Extract and preprocess text
        resume_text = preprocess_text(extract_text(resume_file))
        job_desc_text = preprocess_text(extract_text(job_desc_file))

        if not resume_text or not job_desc_text:
            return jsonify({'error': 'Empty resume or job description. Please check the files and try again.'}), 400

        # Ensure language is English
        if detect(resume_text) != 'en' or detect(job_desc_text) != 'en':
            return jsonify({'error': 'Only English text is supported.'}), 400

        # Compute ATS score (using cached results when available)
        ats_score_val = compute_semantic_score(resume_text, job_desc_text)

        # Extract keywords and determine missing keywords
        found_keywords = get_keywords_from_text(resume_text)
        job_keywords = get_keywords_from_text(job_desc_text)
        missing_keywords = set(job_keywords) - set(found_keywords)

        improvement_tips = []
        # Provide tips only if score is below threshold (70)
        if ats_score_val < 70:
            improvement_tips = suggest_improvements(missing_keywords)

        response = {
            'ats_score': ats_score_val,
            'keywords_found': found_keywords,
            'improvement_tips': improvement_tips
        }

        return jsonify(response)
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({'error': 'An error occurred while processing the files. Please try again.'}), 500

if __name__ == "__main__":
    app.run(debug=True)
