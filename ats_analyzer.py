#!/usr/bin/env python3

import PyPDF2
import spacy
import numpy as np
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import Tuple, List, Dict
import re

class ATSAnalyzer:
    def __init__(self):
        """Initialize the ATS Analyzer with NLP model."""
        self.nlp = spacy.load('en_core_web_sm')
        self.skill_patterns = [
            r'python|java|javascript|c\+\+|sql|aws|azure|docker|kubernetes|react|angular|vue|nodejs|django|flask|fastapi',
            r'machine learning|deep learning|data science|artificial intelligence|nlp|computer vision',
            r'project management|agile|scrum|waterfall|prince2|pmp|itil',
            r'marketing|seo|sem|social media|content marketing|email marketing',
            r'sales|business development|account management|customer success|crm'
        ]

    def read_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file."""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ''
                for page in reader.pages:
                    text += page.extract_text()
                return text
        except Exception as e:
            raise Exception(f"Error reading PDF file: {str(e)}")

    def read_text(self, text_path: str) -> str:
        """Read text file."""
        try:
            with open(text_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            raise Exception(f"Error reading text file: {str(e)}")

    def extract_skills(self, text: str) -> List[str]:
        """Extract skills from text using predefined patterns."""
        skills = []
        for pattern in self.skill_patterns:
            matches = re.findall(pattern, text.lower())
            skills.extend(matches)
        return list(set(skills))

    def extract_keywords(self, text: str, n: int = 20) -> List[Tuple[str, float]]:
        """Extract important keywords using TF-IDF."""
        vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=n
        )
        try:
            tfidf_matrix = vectorizer.fit_transform([text])
            feature_names = vectorizer.get_feature_names_out()
            scores = tfidf_matrix.toarray()[0]
            keyword_scores = list(zip(feature_names, scores))
            return sorted(keyword_scores, key=lambda x: x[1], reverse=True)
        except Exception:
            return []

    def analyze_compatibility(self, job_desc: str, resume: str) -> Dict:
        """Analyze compatibility between job description and resume."""
        # Process both texts
        job_doc = self.nlp(job_desc)
        resume_doc = self.nlp(resume)

        # Extract skills
        job_skills = set(self.extract_skills(job_desc))
        resume_skills = set(self.extract_skills(resume))
        missing_skills = job_skills - resume_skills

        # Extract keywords
        job_keywords = dict(self.extract_keywords(job_desc))
        resume_keywords = dict(self.extract_keywords(resume))

        # Find important missing keywords
        missing_keywords = {
            word: score for word, score in job_keywords.items()
            if word not in resume_keywords
        }

        return {
            'missing_skills': list(missing_skills)[:5],
            'missing_keywords': sorted(
                missing_keywords.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }

def main():
    """Main function to run the ATS analysis."""
    # Initialize analyzer
    analyzer = ATSAnalyzer()

    try:
        # Read input files
        job_desc = analyzer.read_text('job_description.txt')
        resume = analyzer.read_pdf('resume.pdf')

        # Analyze compatibility
        results = analyzer.analyze_compatibility(job_desc, resume)

        # Print results
        print("\nTop 5 Missing Skills (Ranked by Importance):")
        for i, skill in enumerate(results['missing_skills'], 1):
            print(f"{i}. {skill}")

        print("\nTop 5 Missing Keywords (Ranked by Importance):")
        for i, (keyword, score) in enumerate(results['missing_keywords'], 1):
            print(f"{i}. {keyword} (Score: {score:.3f})")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()