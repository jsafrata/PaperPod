# Product Requirements Document (PRD)

## Product

**Interactive Paper Podcast**

## Version

V1 — Hackathon MVP

## Date

March 25, 2026

---

## 1. Overview

Interactive Paper Podcast turns a research paper into a live, multi-speaker journal-club experience. A user uploads a paper or pastes an arXiv link, and the system generates a short podcast-style discussion between three AI panelists:

* **Host** — frames the discussion and keeps the flow moving
* **Expert** — explains the paper's methods, findings, and significance
* **Skeptic** — challenges assumptions, highlights limitations, and pushes back on weak evidence

Unlike a static summary, the experience is interactive. The user can interrupt at any time to ask questions, request simpler explanations, go deeper on a topic, or enter quiz mode. The system also extracts the paper's original visuals and synchronizes them to the discussion, while optionally generating supplementary AI explainer visuals when the original paper visuals are too dense.

The result is a product that feels like a live AI journal club: audio, speaker portraits/cards, transcript, visuals, and active learning in one interface.

---

## 2. Problem Statement

Research papers are often dense, time-consuming, and inaccessible to readers outside a narrow specialty. Most people who try to read papers encounter one or more of the following problems:

* Too much jargon and unclear explanations
* Difficulty understanding figures, tables, and methodology
* No easy way to ask follow-up questions in context
* Passive consumption with poor retention
* Existing paper tools summarize the paper but do not create an engaging, adaptive learning experience

Users need a faster, more interactive way to understand whether a paper matters, what it claims, what its limitations are, and whether they actually understood it.

---

## 3. Vision

Build the fastest and most engaging way to understand a research paper.

The product should feel like:

* a live journal club
* a technical explainer podcast
* a personal paper tutor
* a lightweight learning platform

For the hackathon MVP, the goal is to deliver a polished, memorable demo that clearly shows a new user experience, not just a paper summarizer with audio.

---

## 4. Goals

### Primary Goals

1. Let a user upload a paper and quickly receive a podcast-style discussion.
2. Let the user interrupt at any point and ask a question in voice or text.
3. Synchronize original paper visuals to the discussion.
4. Support learning interactions such as quiz mode and recap mode.
5. Deliver a polished UI/UX that feels like a real product, not an AI demo.

### Success Criteria for Hackathon MVP

* User can input a paper in under 30 seconds.
* Initial podcast playback starts within a reasonable demo-ready time.
* At least one interruption can be handled live.
* At least one original visual from the paper is shown at the right moment.
* At least one AI-generated explainer visual can be shown when requested.
* Quiz mode works for at least a few questions.
* End recap includes key takeaways and weak spots.

---

## 5. Non-Goals

For the hackathon MVP, we are **not** building:

* a full LMS or course platform
* long-term spaced repetition or persistent multi-session study plans
* classroom collaboration
* instructor dashboards
* enterprise-grade infra or permissions
* support for every paper format under the sun
* fully autonomous multi-agent systems running in parallel
* photorealistic full-body video generation for every speaker turn

---

## 6. Target Users

### Primary Users

* Students trying to understand assigned papers
* Researchers reading outside their immediate field
* Founders, investors, and operators trying to quickly evaluate technical papers
* Journal club participants who want a faster way to prepare

### Secondary Users

* Educators who want papers to be more accessible
* Technical interview candidates reading foundational papers
* Curious learners exploring ML, biology, medicine, or other technical fields

---

## 7. Core User Jobs to Be Done

Users want to:

* understand the main contribution of a paper quickly
* ask clarifying questions without leaving the experience
* see the key figures while hearing the explanation
* know what to trust and what to be skeptical of
* test whether they actually understood the paper
* leave with a concise recap they can remember

---

## 8. Product Principles

1. **Ground everything in the source paper.**
2. **Audio alone is not enough; pair it with visuals and text.**
3. **Interruption must feel natural and fast.**
4. **Generated visuals should support, not replace, original evidence.**
5. **The experience should be elegant, simple, and demo-friendly.**
6. **Short, high-quality interactions beat long, rambling ones.**

---

## 9. User Experience Summary

### Core Experience

The user pastes an arXiv link or uploads a PDF. The system ingests the paper, extracts its structure and visuals, builds a grounded knowledge pack, and starts a podcast-like conversation between a Host, Expert, and Skeptic. Speaker portraits/cards represent each panelist. Live transcript is shown on screen. Relevant paper visuals appear in sync with the conversation. The user can interrupt at any point to ask questions or switch into quiz mode.

### High-Level Flow

1. User uploads paper or pastes link
2. System processes paper
3. User enters interactive listening screen
4. Podcast starts with speaker portraits/cards, transcript, and visuals
5. User interrupts with a question
6. System answers live and resumes
7. User can ask for a quiz or recap
8. Session ends with takeaways, flashcards, and weak areas

---

## 10. Detailed User Flow

### 10.1 Input

* User lands on homepage
* User pastes arXiv URL or uploads PDF
* User optionally selects:

  * Beginner or technical mode
  * Focus area: overview, methods, results, limitations
  * Whether to include quiz checkpoints
* User clicks **Generate Interactive Podcast**

### 10.2 Processing

System shows progress states:

* Reading paper
* Extracting visuals
* Building explanations
* Generating panel voices
* Preparing quiz questions

### 10.3 Main Listening Experience

The listening screen includes:

* 3 speaker portraits/cards: Host, Expert, Skeptic
* Active speaker highlight
* Live transcript/subtitles
* Original paper figure or table on the side
* Controls: pause, ask, simplify, go deeper, quiz me
* Section progress bar: Intro, Method, Results, Limitations

### 10.4 Interruption

When the user interrupts:

* audio stops immediately
* active transcript pauses
* UI enters live Q&A state
* router selects the best responder
* speaker answers in voice and text
* relevant visual stays or updates
* Host resumes the prior thread after the answer

### 10.5 Learning Mode

User may request:

* "Quiz me"
* "Ask a harder question"
* "Test me on the method"
* "Explain figure 2"
* "What am I weak on?"

System behavior:

* asks short concept or comprehension questions
* evaluates answer quality
* tracks incorrect answers and weak topics within the session
* offers tailored recap or next question

### 10.6 End Session

Final screen shows:

* 3 key takeaways
* 2 major limitations
* 3 flashcards
* weak concepts
* optional follow-up paper suggestion
* saved transcript and Q&A

---

## 11. Functional Requirements

### 11.1 Paper Input

The product must:

* accept PDF upload
* accept arXiv link input
* create a paper session from either input method

### 11.2 Paper Understanding

The product must:

* parse paper structure into sections
* extract core claims, methods, results, and limitations
* build a glossary of important terms
* generate likely user questions
* create a quiz bank

### 11.3 Visual Extraction

The product must:

* extract paper figures and tables
* store captions and section associations
* map visuals to likely podcast moments
* distinguish original paper visuals from generated visuals

### 11.4 Podcast Generation

The product must:

* create a multi-speaker scripted opening discussion
* assign turns to Host, Expert, or Skeptic
* keep turns short and understandable
* produce audio and text for each turn

### 11.5 Live Interaction

The product must:

* allow voice or text interruption during playback
* stop audio immediately on interruption
* answer the question live using grounded paper context
* resume the podcast naturally after answering

### 11.6 Transcript

The product must:

* display live transcript/subtitles
* highlight currently spoken text
* allow the transcript to remain visible during interruption

### 11.7 Speaker Identity UI

The product must:

* display 3 distinct synthetic speaker portraits or cards for Host, Expert, and Skeptic
* visually indicate the active speaker with highlight, glow, waveform, or motion
* avoid lip-sync video generation in the MVP
* keep speaker identity clear through name, role, and consistent styling

### 11.8 Quiz Mode

The product must:

* generate quiz questions from the current section
* accept user answers in text or voice
* give short feedback
* track weak concepts within the session

### 11.9 Visual Generation

The product must:

* generate supplementary explainer visuals when the original paper figure is too dense or insufficient
* clearly label AI-generated visuals
* keep original paper visuals as the source of truth when presenting actual evidence

### 11.10 Recap

The product must:

* generate end-of-session takeaways
* summarize weak spots
* create flashcard-style review items

---

## 12. UX / UI Requirements

### 12.1 UX Goals

The experience should feel:

* polished
* fast
* visually clear
* audio-first but not audio-only
* trustworthy
* easy to interrupt

### 12.2 Core UI Layout

**Top area**

* speaker portraits/cards with active speaker state

**Center-left**

* transcript and current spoken text

**Center-right**

* synced visual panel showing figure/table or AI explainer visual

**Bottom rail**

* playback controls
* interrupt mic button
* quick actions: simplify, deeper, ask why, quiz me

### 12.3 Design Requirements

* dark, modern, minimal visual style
* high contrast for readability
* animated transitions between speaker states
* visual provenance badges for all visuals
* simple processing state animation
* avoid clutter

### 12.4 Accessibility

* subtitles always visible
* transcript readable without audio
* keyboard-accessible controls where possible
* distinguish speaker identity through both color and label

---

## 13. System Architecture (Hackathon MVP)

### 13.1 High-Level Architecture

1. **Frontend Application**

   * upload flow
   * listening screen
   * speaker portraits/cards
   * transcript
   * visual panel
   * quiz UI

2. **Backend Orchestrator**

   * manages session state
   * routes speaker roles
   * coordinates podcast, Q&A, quiz, and recap states

3. **Paper Ingestion & Understanding Pipeline**

   * PDF/arXiv import
   * section extraction
   * visual extraction
   * knowledge pack generation

4. **Retrieval Layer**

   * stores chunked paper content for grounded live answers

5. **Audio Layer**

   * scripted multi-speaker TTS for podcast segments
   * low-latency live audio for interruption/Q&A

6. **Speaker Identity Layer**

   * renders active speaker portrait/card driven by audio state

7. **Visual Generation Layer**

   * generates supplementary AI visuals when needed

### 13.2 Core Architectural Principle

Ingest the paper once, build a structured knowledge pack, precompute the podcast foundation, and use a live Q&A layer for user-driven interaction.

---

## 14. Core Data Objects

### 14.1 Knowledge Pack

The main structured object produced after paper ingestion.

Fields include:

* paper title
* authors
* section map
* claims
* methods
* results
* limitations
* glossary
* figure list
* likely questions
* quiz bank

### 14.2 Visual Object

Each visual contains:

* visual id
* type: figure, table, generated explainer
* image asset
* caption
* source page
* section association
* provenance label

### 14.3 Session State

Each live session tracks:

* paper id
* active section
* current turn index
* current speaker
* active visual
* transcript history
* quiz history
* weak concepts
* mode: processing, playing, interrupted, live Q&A, quiz, recap

---

## 15. Runtime Flow

### 15.1 Processing Flow

1. receive paper input
2. store source file
3. extract structure and visuals
4. build knowledge pack
5. generate opening dialogue turns
6. generate initial podcast audio
7. start session

### 15.2 Playback Flow

1. frontend plays turn audio
2. active speaker portrait/card animates
3. transcript updates in sync
4. visual panel updates based on turn mapping

### 15.3 Interruption Flow

1. user interrupts via voice or text
2. playback stops
3. backend retrieves relevant paper chunks
4. speaker router selects responder
5. live answer is generated
6. answer is spoken and displayed
7. session resumes from prior point

### 15.4 Quiz Flow

1. user requests quiz
2. orchestrator chooses question based on current section and weak concepts
3. user answers
4. evaluator scores response
5. system provides feedback and updates weak concepts

---

## 16. Agent System

The product uses a multi-agent architecture with 4 consolidated agents coordinated through an orchestrator. Each agent maintains its own context, makes multi-turn decisions, and can invoke tools — they are genuine agents, not single-shot prompt calls.

The system is split into two groups:

* **User-facing speaker agents** that the user experiences directly
* **Background agents** that handle grounding, pacing, visuals, and learning quality behind the scenes

### 16.1 User-Facing Speaker Agents

#### Host Agent

Responsibilities:

* introduce topics and frame the conversation
* guide the flow and transition between sections
* summarize key points
* prompt the user to ask questions or enter quiz mode
* resume the main thread after interruptions

Why it matters: The Host makes the experience feel coherent and podcast-like instead of like a sequence of disconnected explanations.

#### Expert Agent

Responsibilities:

* explain methods and results
* define jargon
* answer technical clarification questions
* connect ideas clearly to the source paper

Why it matters: The Expert is the main explanatory voice and is responsible for making the paper understandable.

#### Skeptic Agent

Responsibilities:

* highlight limitations
* question assumptions and weak baselines
* surface uncertainty
* help the user interpret how much to trust the conclusions

Why it matters: The Skeptic prevents the experience from sounding like a hype machine and gives the product more credibility.

### 16.2 Background Agents

#### Orchestrator Agent

Responsibilities:

* decide which speaker agent should respond next based on conversation history and session state
* track the current session mode: podcast, interruption, quiz, recap
* manage session state and conversation flow
* determine when to resume the original thread after a user question
* delegate to background agents as needed

Why it matters: This is the core runtime coordinator. It maintains full conversation context and makes routing decisions that depend on what has happened across the session.

#### Retrieval & Translation Agent

Consolidates: retrieval, glossary, and simplification/depth adjustment

Responsibilities:

* fetch the most relevant paper chunks for live questions
* retrieve adjacent context, prerequisite chunks, captions, and glossary items
* rewrite technical explanations at the right level for the user
* define difficult terms simply
* provide beginner-friendly analogies when requested
* support "simplify" and "go deeper" actions
* maintain context about what the user has already been told to avoid repetition

Why it matters: This keeps live answers grounded in the actual paper while adapting across turns to the user's demonstrated comprehension level.

#### Visual Agent

Consolidates: visual mapping and visual generation

Responsibilities:

* map paper figures and tables to the right discussion turns
* decide when to display an original paper visual
* determine whether a new AI explainer visual would help based on the conversation so far
* generate supplementary visuals when the user requests simplification or when the original figure is too dense
* create simplified flowcharts, concept diagrams, or comparison cards
* label outputs clearly as AI explainer visuals

Why it matters: This creates the synchronized audio-plus-visual learning experience and allows the system to teach, not just display source material.

#### Quiz & Evaluation Agent

Consolidates: quiz generation and answer evaluation

Responsibilities:

* generate questions from the current section
* adapt difficulty based on the user's answers across the session
* focus on methods, claims, results, or limitations depending on user request
* evaluate user answers
* identify weak concepts or misunderstandings
* track incorrect answers and weak topics within the session
* decide whether to continue, review, or increase difficulty

Why it matters: This converts passive listening into active learning with a multi-turn feedback loop that gets harder or easier based on how the user is doing.

### 16.3 MVP Guidance

For the hackathon MVP:

* keep the Host, Expert, and Skeptic as the only visible speaker agents
* run 4 agents total (3 speakers + orchestrator), with Retrieval & Translation, Visual, and Quiz & Evaluation invoked by the orchestrator as needed
* each agent should have its own system prompt, tool access, and session memory
* avoid running all agents as persistent parallel sessions — the orchestrator should activate background agents on demand

### 16.4 Routing Principles

As a default:

* Host handles framing, transitions, recaps, and quiz prompts
* Expert handles explanation, technical clarification, and figure walkthroughs
* Skeptic handles limitations, criticism, and trustworthiness questions
* Retrieval & Translation agent supports simplify/deepen actions behind the scenes
* Quiz & Evaluation agent activates only in learning mode
* Visual agent activates when syncing or generating visuals

This routing should remain simple and predictable in the MVP.

---

## 17. Visual Strategy

### Original Visuals

Use the paper's actual figures and tables whenever discussing:

* model architecture
* benchmark results
* ablations
* experimental setup
* error analysis

### AI-Generated Visuals

Use generated visuals only when the user asks for extra help or when the system detects that a simpler diagram would improve understanding.

Examples:

* simplified architecture diagram
* flowchart of the method
* analogy visual for a hard concept
* comparison card between baseline and proposed method

### Provenance Rule

Every visual shown must be labeled as either:

* **From paper**
* **AI explainer visual**

---

## 18. Speaker Identity Strategy

### Goal

Give the experience a live panel feel without adding fragile real-time avatar video complexity.

### MVP Approach

* Use 3 predesigned synthetic speaker portraits or illustrated cards
* Only the active speaker is highlighted at a time
* Use subtle motion, glow, waveform, and speaker-state animation instead of lip-sync
* Avoid custom avatar creation in MVP

### Why

This keeps the interface polished and expressive while preserving engineering time for the core experience: paper understanding, visual sync, interruption, and quiz mode.

---

## 19. AI / Model Requirements

The system needs model capabilities for:

* document understanding
* grounded summarization
* structured extraction
* question answering
* TTS / multi-speaker audio
* low-latency live interaction
* image generation for supplementary visuals

### Model Usage Pattern

* one stage for paper understanding and knowledge pack generation
* one stage for script planning and turn generation
* one live stage for interruption/Q&A
* one image generation stage for explainer visuals

---

## 20. Analytics / Demo Metrics

For the MVP, capture lightweight analytics:

* time from upload to first audio
* number of interruptions
* number of quiz interactions
* most requested visual explanations
* sections where users ask the most questions

These metrics help show engagement in a demo or follow-up pitch.

---

## 21. Acceptance Criteria

The MVP is successful if:

* a user can input a paper and get a generated podcast discussion
* at least 3 speaker personas appear in the experience
* transcript is visible during playback
* at least one paper figure appears at the right moment
* at least one interruption is handled live
* at least one quiz interaction works end-to-end
* end recap includes takeaways and weak concepts
* the UI feels polished and coherent throughout the demo

---

## 22. Risks and Mitigations

### Risk: Latency feels too high

**Mitigation:** precompute opening podcast turns, likely follow-up questions, and some visuals.

### Risk: Live answers hallucinate

**Mitigation:** use retrieval from the paper knowledge pack and current section chunks.

### Risk: Figure extraction is messy

**Mitigation:** support a subset of well-formatted PDFs and manually handle demo papers if needed.

### Risk: Speaker rendering adds complexity

**Mitigation:** use prebuilt speaker portrait/card designs and animate one speaker at a time.

### Risk: Product feels gimmicky

**Mitigation:** emphasize grounded explanations, visual sync, and active learning.

---

## 23. MVP Build Priorities

### Must Have

* paper input
* paper understanding pipeline
* 3-speaker scripted opening
* transcript
* 3 speaker portraits/cards with active speaker state
* synced original visuals
* live interruption
* quiz mode
* recap page

### Nice to Have

* AI-generated explainer visual on request
* variable difficulty modes
* follow-up paper recommendation
* saved transcript export

### Out of Scope for Hackathon

* accounts
* collaboration
* persistent cross-session learning history
* instructor analytics dashboard
* full paper comparison mode

---

## 24. Demo Script Recommendation

1. Upload a paper
2. Show processing flow
3. Start podcast with Host, Expert, Skeptic
4. Show figure sync when methods/results are discussed
5. Interrupt with a question
6. Show live explanation with the active speaker card highlighted
7. Ask for a simpler visual
8. Show AI explainer visual next to the original figure
9. Enter quiz mode
10. End with recap and weak concepts

This should be the default live demo flow.

---

## 25. Hackathon Build Order

The MVP should be built in the following sequence so that the team reaches a compelling demo early and layers on polish afterward.

### Hours 0–2: Product shell and UX foundation

* Finalize the paper input flow and core screen layout
* Set up the design system, colors, typography, and motion primitives
* Build the page skeletons for upload, processing, listening, quiz, and recap views
* Stub speaker cards, transcript panel, visual panel, and controls

### Hours 2–6: Paper ingestion and processing pipeline

* Support PDF upload and arXiv link input
* Store the source paper and normalize it into a single ingestion flow
* Extract basic paper metadata, sections, and text chunks
* Build the first processing-state UI with staged progress messages

### Hours 6–10: Knowledge pack and retrieval

* Generate the knowledge pack with summary, methods, results, limitations, glossary, and likely questions
* Chunk the paper for retrieval
* Store figure/table metadata and captions
* Build the first retrieval path for grounded Q&A

### Hours 10–14: Scripted podcast foundation

* Generate the opening multi-speaker discussion turns
* Render transcript blocks for each turn
* Connect speaker turns to speaker portraits/cards
* Add audio playback for scripted turns
* Build section progress state across Intro, Method, Results, and Limitations

### Hours 14–18: Visual sync

* Extract 2–3 strong visuals from the paper
* Map visuals to speaker turns
* Display the correct visual as the discussion advances
* Add provenance badges such as From paper

### Hours 18–24: Live interruption and Q&A

* Add the interrupt button and text input first
* Stop playback cleanly on interruption
* Retrieve relevant paper chunks and generate a grounded answer
* Resume the scripted discussion naturally after the answer
* If voice input is feasible, add it after text interruption works reliably

### Hours 24–30: Quiz mode

* Add a Quiz me action from the current section
* Generate short questions from the active topic
* Accept typed answers first, then voice answers if time allows
* Return simple evaluation and weak-concept feedback

### Hours 30–36: AI explainer visuals

* Add on-demand generation of supplementary explainer visuals
* Keep original paper visuals as the default evidence layer
* Clearly label generated visuals as AI explainer visual

### Hours 36–42: Recap and session close

* Generate key takeaways, limitations, flashcards, and weak concepts
* Build the recap screen
* Add replay/jump-back behavior and transcript persistence for the session

### Hours 42–48: Polish and demo hardening

* Improve motion, spacing, loading states, and visual hierarchy
* Add a canned demo paper and precompute its best outputs
* Cache the opening discussion and key visuals for the demo
* Tighten prompt quality and reduce latency hot spots
* Rehearse the demo flow end to end

### If time gets tight

Cut in this order:

1. voice interruption before text interruption
2. AI-generated visuals before original paper visual sync
3. voice answers in quiz mode before typed answers
4. advanced recap personalization before a simple recap

---

## 26. Tech Stack

The MVP stack should optimize for speed of implementation, polished UI, and reliable demos.

### Frontend

* **Next.js** for the app shell and routing
* **React** for UI composition
* **TypeScript** for safer iteration under time pressure
* **Tailwind CSS** for rapid styling
* **Framer Motion** for speaker-state transitions and loading polish
* **Lucide React** for lightweight iconography
* **React PDF** or a lightweight PDF preview component for source viewing when needed
* **Howler.js** or native HTML5 audio for podcast playback and control

### Backend

* **FastAPI** for a fast Python backend that works well with model orchestration and PDF tooling
* **Uvicorn** as the ASGI server
* **Pydantic** for structured request/response schemas
* **Celery** or a lightweight background-job queue only if asynchronous processing becomes necessary; otherwise keep processing inline for the MVP

### Data and storage

* **Postgres** for papers, sessions, transcript history, quiz attempts, and recap data
* **Redis** for session state, playback state, and short-lived caches
* **Supabase Storage** or **Google Cloud Storage** for PDFs, extracted visuals, and generated assets

### AI / model layer

* **Gemini Files API** for paper upload and reusable file references
* **Gemini document understanding** for parsing PDFs and generating the knowledge pack
* **Gemini structured output** for clean JSON objects such as knowledge packs, turn plans, and quiz questions
* **Gemini TTS** for scripted multi-speaker podcast segments
* **Gemini Live API** for interruption, live Q&A, and optional voice input/output loops
* **Nano Banana / Gemini image generation** for supplementary explainer visuals

### Retrieval and search

* **pgvector** in Postgres for lightweight vector retrieval without adding another major service
* Sentence/chunk embeddings generated during paper processing and stored per section/figure/caption block

### PDF and visual extraction

* **PyMuPDF (fitz)** for extracting page images, figures, tables, bounding boxes, and captions
* **pdfplumber** as a fallback for text/table extraction when needed
* Optional small image-processing utilities in **Pillow** for cropping figures and preparing display assets

### Auth and hosting

* For the hackathon MVP, skip full auth unless required
* **Vercel** for frontend deployment
* **Render**, **Railway**, or **Fly.io** for the FastAPI backend
* Use environment-managed API keys and keep the deploy path simple

### Analytics and monitoring

* **PostHog** for lightweight product analytics and event logging
* Basic app logs plus request timing to identify latency bottlenecks during the demo

### Design system choices

* Dark theme by default
* One accent color per active speaker state pattern
* Rounded card-based layout for upload, transcript, and visual panes
* Motion used sparingly for active speaker changes, processing states, and quiz feedback

---

## 27. Future Roadmap

After MVP, potential expansions include:

* compare two papers
* classroom mode
* saved study decks
* spaced repetition
* domain-specific modes for ML, biology, medicine, finance, etc.
* instructor-facing paper assignment mode
* more advanced personalized learning profiles

---

## 28. Final Product Positioning

### Internal Positioning

An interactive AI journal club that turns research papers into live, visual, quiz-enabled learning experiences.

### External Positioning

**Paste a paper and watch an AI panel discuss it live — with talking speaker portraits/cards, synced figures, real-time Q&A, and quiz mode.**

---

## 29. Summary

The hackathon MVP should not try to be a complete research platform. It should aim to deliver one unmistakably strong experience:

**A beautiful, interactive paper podcast where users can listen, watch, interrupt, learn, and leave with real understanding.**
