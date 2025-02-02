#!/usr/bin/env python3

import re
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter

def extract_dynamic_skills(job_description):
    """
    Dynamically extract potential skills and technical terms from the job description.
    Identifies patterns like programming languages, tools, and common technical phrases.
    """
    # Patterns for skills extraction
    patterns = [
        r"\b[A-Z][a-zA-Z0-9+\-.]*\b",  # Capitalized words (e.g., "Python", "Docker")
        r"\b[A-Za-z]+\s+[a-zA-Z]*\b",  # Multi-word terms (e.g., "Project Management")
        r"\b[A-Za-z0-9\-]+/[A-Za-z0-9\-]+\b"  # Patterns like "GitLab CI/CD"
    ]
    
    # Combine patterns into a single regex
    combined_pattern = "|".join(patterns)
    
    # Extract matches
    matches = re.findall(combined_pattern, job_description)
    
    # Normalize matches (lowercase and deduplicate while preserving original case for display)
    normalized_matches = [match.strip() for match in matches if len(match) > 1]
    
    # Count and rank the most common matches
    skill_counts = Counter(normalized_matches)
    
    # Filter for relevant results based on occurrence
    relevant_skills = [skill for skill, count in skill_counts.items() if count > 1]
    
    return relevant_skills

def generate_wordcloud(skills):
    """
    Generate a word cloud based on the extracted skills.
    """
    if not skills:
        print("No skills identified to generate a word cloud.")
        return
    
    text = " ".join(skills)
    wordcloud = WordCloud(width=800, height=400, background_color="white").generate(text)
    
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.title("Key Skills Word Cloud", fontsize=16)
    plt.show()

def main():
    # Prompt the user for a text file containing the job description
    file_path = input("Enter the path to the text file containing the job description: ").strip()
    
    try:
        # Read the job description from the file
        with open(file_path, 'r') as file:
            job_description = file.read()
        
        # Extract skills dynamically
        skills = extract_dynamic_skills(job_description)
        
        # Display extracted skills
        print("Extracted Key Skills:")
        print(skills)
        
        # Generate word cloud
        generate_wordcloud(skills)
    
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()