"""Prompt templates for knowledge pack extraction."""

KNOWLEDGE_PACK_SYSTEM_PROMPT = """You are an expert research paper analyst. Your job is to read an academic paper and produce a comprehensive, structured knowledge pack that will be used to generate an interactive podcast discussion about the paper.

Be thorough but concise. Ground every claim in the actual paper — do not speculate or add information not in the paper. Use clear, accessible language."""

KNOWLEDGE_PACK_USER_PROMPT = """Analyze the attached research paper and produce a structured knowledge pack with the following fields:

1. **title**: The paper's title
2. **authors**: List of author names
3. **one_sentence_summary**: A single sentence capturing the core contribution
4. **sections**: For each major section, provide:
   - section_title: the section name
   - key_points: 2-4 bullet points summarizing the section
   - importance: why this section matters (1 sentence)
5. **core_claims**: 3-5 main claims the paper makes
6. **methods**: For each method/technique:
   - name: method name
   - description: what it does (2-3 sentences)
   - why_chosen: why the authors chose this approach
7. **results**: For each key result:
   - finding: what was found
   - evidence: the specific metric/table/figure supporting it
   - confidence: how strong the evidence is (strong/moderate/weak)
8. **limitations**: 3-5 limitations (stated or implied)
9. **glossary**: 8-12 important technical terms with:
   - term: the term
   - definition: clear definition
   - analogy: a simple analogy for non-experts (optional)
10. **likely_questions**: 5-10 questions a reader would likely ask
11. **figure_descriptions**: For each figure/table mentioned:
    - figure_label: e.g. "Figure 1"
    - what_it_shows: what the figure depicts
    - key_takeaway: the main insight from this figure

{difficulty_instruction}

Return ONLY valid JSON matching this structure. No markdown, no code blocks, just the JSON object."""

BEGINNER_INSTRUCTION = "Adjust explanations for a beginner audience: use simple language, provide analogies, avoid unnecessary jargon."
TECHNICAL_INSTRUCTION = "Maintain technical precision: include mathematical details, specific metrics, and nuanced methodological points."
