# LinuxONE Knowledge Assistant — UI Upgrade Implementation Plan

## Objective

Upgrade the current interface from a **styled form/results page** into a **production-level, mobile-friendly chatbot with evidence-backed answers**, while preserving:

- **LinuxONE orange** as the brand accent
- **Sources** as a core product feature
- **clean side whitespace** suitable for desktop and mobile responsiveness
- a **professional, enterprise-grade** look and feel

---

## Product Direction

Implement the UI as:

> **A production chatbot with evidence-backed answers**

That means:

- conversational layout, not dashboard layout
- unified input composer, not stacked form fields
- answer + sources as a structured response surface
- graceful handling of out-of-scope queries
- no developer/debug-style messaging exposed to users

---

## Core UX Decisions to Lock In

### 1) Composer layout
Use this exact structure:

```text
[ prompt input.............................................. ]
[ topic ]                                   [ send ]
```

This should be implemented as **one unified composer component**, not separate unrelated controls.

---

### 2) Response model
After a user submits a question, the UI should shift into a **conversation-style view**:

```text
[ user message ]
[ assistant response ]

[ tabs: Answer | Sources (n) ]
```

---

### 3) Sources pattern
Use **Option A: tabs** for the response area:

- `Answer`
- `Sources (n)`

The sources section should remain a major product feature and feel tightly connected to the response.

---

### 4) Out-of-scope / no retrieval result behavior
Do **not** show raw error text such as:

- `Error: No relevant info`
- `No chunks found`
- `No relevant context`

Instead, treat this as a **valid product state**, not a system failure.

Use this state instead:

> **No source-backed answer found**  
> I couldn’t find relevant information in the indexed LinuxONE documentation for that question. Try rephrasing your prompt or asking about a LinuxONE-specific topic.

---

## High-Level Implementation Goals

1. Replace the current “form + results cards” structure with a **chat-oriented flow**.
2. Create a **state-aware layout**:
   - empty state
   - active conversation state
   - no-sources state
   - technical error state
3. Make the visual system more **production-grade**.
4. Improve information architecture without overcomplicating the product.

---

## Phase 1 — Establish the Design System

Set this up first so all components inherit the same visual language.

### Tokens / constants to define

#### Spacing scale
Use an 8px-based system:

```text
4, 8, 12, 16, 24, 32, 40, 48
```

#### Border radius
Use a soft-structured geometry system:

- Cards: `14px`
- Inputs / textareas / selects: `12px`
- Buttons: `10px`
- Pills / badges / chips: `999px`

#### Typography
Use **Inter** consistently.

Recommended scale:
- Hero title: `36–40px`, semibold
- Section title: `22–24px`, semibold
- Body: `15–16px`
- Meta text: `13–14px`
- Chip / badge text: `12–13px`

#### Colors
Keep LinuxONE orange as the primary accent.

Also define:
- page background
- surface/card background
- primary text
- secondary text
- border color
- muted background
- disabled control colors
- success/warning/error if applicable

#### Shadows
Keep subtle:
- low blur
- low opacity
- avoid heavy floating card shadows

---

## Phase 2 — Restructure the Page Into States

Create explicit UI states instead of one static page layout.

### State A — Empty state
Used before the first query is submitted.

#### Layout
- header
- hero title/subtitle
- unified composer
- suggested prompts

#### Behavior
This state can remain slightly more open and spacious.

---

### State B — Active conversation state
Used after a query has been submitted.

#### Layout
- header
- compacted top area
- user message
- assistant response
- tabs: `Answer | Sources (n)`
- composer remains available beneath thread or sticky on mobile later

#### Behavior
The hero should no longer dominate once a conversation exists.

---

### State C — No-sources state
Used when retrieval succeeds technically but no strong LinuxONE-backed source is found.

#### Layout
Same layout as active conversation state:
- user message
- assistant “no source-backed answer found” response
- tabs:
  - `Answer`
  - `Sources (0)`

This should not be presented as a crash or failure.

---

### State D — Technical error state
Used only for actual failures:
- network issue
- backend failure
- timeout
- auth failure
- malformed response

Example copy:

> **Something went wrong while retrieving results**  
> Please try again in a moment.

Important: keep this distinct from the no-sources state.

---

## Phase 3 — Rebuild the Composer Component

This is the most important component to upgrade.

### Goal
The composer should feel like a **real chat input**, not a form stack.

### Build a reusable `Composer` component
Suggested internal structure:

```text
Composer
├── Prompt textarea/input
├── Footer row
│   ├── Topic selector
│   └── Send/Search button
└── Suggested prompt chips (empty state only, or contextually shown)
```

### Composer requirements

#### Visual
- One rounded outer shell
- White surface
- Subtle border
- Comfortable internal padding
- Clear focus state
- LinuxONE orange for active submit button

#### Input area
- prominent but controlled height
- placeholder text should be helpful and readable
- avoid a huge blank textarea unless multi-line input is core
- line-height should feel deliberate

#### Footer row
Use exactly this pattern:

```text
[ topic ]                                   [ send ]
```

- left-aligned topic select
- right-aligned send button
- spacing should feel balanced, not cramped

#### Button behavior
- disabled when input is empty
- active orange when input is valid
- no ambiguous “is this disabled?” state

#### Suggested prompts
- visible primarily in empty state
- style them as lightweight suggestions, not mini-buttons
- use subtle tint / soft outline
- keep spacing consistent
- on mobile, make horizontally scrollable if needed

---

## Phase 4 — Introduce a Conversation Thread Model

This is the structural change that will make the app feel most production-grade.

### Add a lightweight message thread
Even if the app is still functionally one-turn, it should visually feel like a conversation session.

### Minimum thread structure
```text
[ UserMessage ]
[ AssistantResponse ]
```

#### User message
Render the submitted prompt as a user message block above the answer.

This can be visually lightweight:
- compact bubble or message row
- subtle background
- clear distinction from assistant response

#### Assistant response
The assistant response should feel like a message/content block, not just a card labeled “Answer.”

---

## Phase 5 — Replace the Current Answer Card With a Response Surface

### Goal
The answer should feel like:
- source-backed
- conversational
- readable
- productized

### Build an `AssistantResponse` component
Suggested structure:

```text
AssistantResponse
├── Header row
│   ├── assistant label / icon
│   └── utility action(s) if needed
├── Tab nav
│   ├── Answer
│   └── Sources (n)
└── Tab panel content
```

### Answer tab
Should contain:
- formatted answer content
- metadata row
- optional citations or references if supported

#### Improve content rendering
Add proper prose styling:
- line-height: `1.6–1.7`
- paragraph spacing
- list spacing
- heading spacing
- max readable line width

#### Important recommendation
Remove or soften the current strong left orange border on the answer card.

That styling is not terrible, but it still contributes to a “starter UI/template card” feeling.

#### Better replacement
Use one of these:
- a clean response header with small branded icon
- a subtle top accent
- no accent border at all, using typography and spacing to define structure

---

## Phase 6 — Implement Answer / Sources Tabs

### Goal
Make sources feel like a first-class evidence feature, not a separate card dump below the answer.

### Build a tabs component
Tabs:
- `Answer`
- `Sources (n)`

#### Behavior
- default to `Answer`
- switch cleanly to `Sources`
- preserve same container shell for both tabs

This consolidates the response into a single surface and feels much more like a production AI product.

---

## Phase 7 — Upgrade the Sources Experience

### Build a `SourcesPanel` component
This should render source-backed evidence in a scannable way.

### Source item structure
Each source item should contain:
- document title
- file/document name
- relevant page/location info
- match score badge
- optional content type label or section label

### Visual rules
- clean hierarchy
- tighter spacing than current
- match badge aligned consistently
- metadata quieter than title
- avoid heavy borders if spacing can do the work

### Keep
The current concept of sources as a supporting evidence panel is strong. Keep that.

### Improve
Make each source item feel more like part of an intentional evidence system than a generic card list.

---

## Phase 8 — Create a Polished No-Evidence State

### Build a dedicated `NoEvidenceState` component
Do not use generic answer styling for this case.

#### Structure
```text
[ icon ]
No source-backed answer found

I couldn’t find relevant information in the indexed LinuxONE documentation for that question.

Try one of these instead:
[ chip ] LinuxONE security
[ chip ] LinuxONE AI workloads
[ chip ] LinuxONE resiliency
[ chip ] LinuxONE architecture
```

#### Requirements
- same overall response shell as a normal answer
- same tabs structure
- `Sources (0)` should still exist
- recovery path should be obvious
- should feel intentional, not apologetic or broken

---

## Phase 9 — Clean Up the Header

### Keep
- orange brand header
- LinuxONE branding

### Improve
Simplify what is shown there.

#### Current issue
The document/chunk counts in the header feel more like internal status/debug metadata than polished product UI.

#### Change
Move document metadata elsewhere:
- near the sources tab
- in a lightweight dataset info row
- in a secondary information panel
- or behind an info/help affordance

#### Header should contain
- logo/icon
- product name
- minimal utility controls only

The top bar should feel calm and premium.

---

## Phase 10 — Strengthen Typography and Content Styling

### Global typography improvements
Use Inter across the whole interface and standardize text hierarchy.

### For prose/answer rendering
Add a dedicated prose class or content styling system for:
- paragraphs
- lists
- section headings
- inline emphasis
- citations
- links if applicable

#### Target feel
Less “HTML dumped into card,” more “editorially formatted answer.”

This change will do a lot for perceived product quality.

---

## Phase 11 — Refine Chips, Badges, and Metadata

### Suggested prompt chips
Make them more elegant and less CTA-like.

#### Style direction
- softer background tint
- reduced border prominence
- slightly smaller text
- consistent spacing
- scroll/stack nicely on mobile

### Metadata pills
Use consistent styling for:
- latency
- sources count
- model label
- match percentage

#### Rule
Badges and pills should belong to the same component family.

Right now these often become a source of “vibe-coded” inconsistency if not standardized.

---

## Phase 12 — Mobile-First Behavior

Since this product is expected to be used heavily on phones, implement mobile intentionally now.

### Mobile priorities

#### Header
- compact height
- minimal controls

#### Composer
- remain usable without becoming a tall stacked form
- topic selector may need to reduce width or move to a secondary row
- send button must remain obvious and thumb-friendly

#### Suggested prompts
- horizontally scrollable chips recommended
- avoid wrapping into awkward multi-line clusters if space gets tight

#### Response area
- tabs should remain easy to tap
- source items should stack cleanly
- content should not feel too dense

#### Optional future enhancement
A sticky bottom composer on mobile would be a strong next step, but it is not required in this pass.

---

## Recommended Component List

Have the agent implement/refactor these components:

```text
AppShell
Header
EmptyState
ConversationView
Composer
TopicSelect
SendButton
SuggestionChips
MessageThread
UserMessage
AssistantResponse
ResponseTabs
AnswerPanel
SourcesPanel
SourceItem
NoEvidenceState
SystemErrorState
MetadataBadge
```

---

## Recommended State Model

Have the agent model UI states explicitly.

```ts
type RetrievalState =
  | 'idle'
  | 'searching'
  | 'answered'
  | 'no_sources'
  | 'error'
```

### Important rule
- `no_sources` is a **valid product result**
- `error` is a **technical failure**

Do not merge these states.

---

## UX Copy to Implement

### Empty state
**Ask Questions About LinuxONE**  
Search indexed LinuxONE documentation and redbooks for source-backed answers.

### Normal answer state
Use the assistant response content as normal.

### No-sources state
**No source-backed answer found**  
I couldn’t find relevant information in the indexed LinuxONE documentation for that question.

**Try one of these instead:**
- LinuxONE architecture
- LinuxONE security
- LinuxONE AI workloads
- LinuxONE resiliency

### Technical error state
**Something went wrong while retrieving results**  
Please try again in a moment.

---

## Execution Order for the Agent

### Step 1 — Design system foundation
- define tokens for spacing, radius, typography, color, border, shadow
- standardize badge/chip/button styles

### Step 2 — Build the unified composer
- replace stacked input UI
- implement exact layout:
  ```text
  [ prompt input.............................................. ]
  [ topic ]                                   [ send ]
  ```
- add correct disabled/active button states

### Step 3 — Add explicit page states
- `idle`
- `answered`
- `no_sources`
- `error`

### Step 4 — Add conversation structure
- render user message above assistant response
- move from “results cards” to conversation surface

### Step 5 — Replace answer + sources stack with tabbed response panel
- `Answer`
- `Sources (n)`

### Step 6 — Implement no-evidence UX
- polished no-sources component
- sources tab still present with `0`

### Step 7 — Simplify header
- preserve orange
- remove debug/internal feeling from metadata placement

### Step 8 — Refine mobile responsiveness
- composer
- chips
- tabs
- source items
- response density

### Step 9 — Polish typography/content rendering
- prose styles
- spacing
- hierarchy
- metadata alignment

---

## Acceptance Criteria

The upgrade is successful when:

1. The UI no longer reads as a **form + output cards** layout.
2. The interface feels like a **chat session**.
3. The composer feels unified and intentional.
4. The answer and sources feel like one connected response system.
5. Out-of-scope queries do **not** look like errors.
6. The app looks credible on both desktop and mobile.
7. LinuxONE orange remains present but controlled.
8. Sources remain a visible differentiator.
9. Header feels premium, not internal-tool-like.
10. The visual system is consistent across buttons, chips, badges, cards, and typography.

---

## Brief Agent Prompt Version

Use this if you want a shorter instruction block for the agent:

```text
Upgrade the current LinuxONE Knowledge Assistant UI from a form/results page into a production-level, mobile-friendly chatbot with evidence-backed answers.

Requirements:
- Preserve LinuxONE orange as the brand accent
- Keep side whitespace; mobile friendliness is important
- Use a unified composer with this structure:
  [ prompt input.............................................. ]
  [ topic ]                                   [ send ]
- After submission, shift to a conversation-style layout:
  [ user message ]
  [ assistant response ]
- Replace the separate answer/sources card stack with tabs:
  - Answer
  - Sources (n)
- Keep sources as a core product feature
- Add explicit UI states:
  - idle
  - answered
  - no_sources
  - error
- Treat “no relevant retrieved content” as a valid product state, not an error
- Replace “Error: No relevant info” with:
  “No source-backed answer found. I couldn’t find relevant information in the indexed LinuxONE documentation for that question.”
- Keep Sources (0) visible in that state
- Simplify the orange header; remove internal/debug-feeling metadata from the header
- Improve typography, spacing, and prose styling so the UI feels production-grade
- Render the user question above the assistant answer so the page feels conversational
- Keep the UI professional, enterprise-grade, and modern
- Build/refactor reusable components for: Header, Composer, MessageThread, UserMessage, AssistantResponse, ResponseTabs, AnswerPanel, SourcesPanel, SourceItem, NoEvidenceState, SystemErrorState
```
