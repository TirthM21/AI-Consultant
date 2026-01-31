# McKinsey-Style Consulting Deck Generator

Production-ready system for generating Tier-1 consulting presentations using AI orchestration and deterministic slide templates.

## Quick Start

```bash
# Install dependencies
pip install python-pptx matplotlib seaborn google-generativeai

# Generate a deck
python main.py --problem "How should we expand our SaaS business to international markets?" --client "TechCorp"
```

## System Architecture

### Multi-Step Orchestration Pipeline

```
PROBLEM STATEMENT → STEP 1 (Structure) → STEP 2 (Data) → STEP 3 (Content) → STEP 4 (PPTX) → STEP 5 (PDF)
```

#### Step 1: Engagement Structuring (LLM Call #1)
- **Input**: Client problem statement
- **Output**: Slide-by-slide blueprint with McKinsey action titles
- **Key Elements**:
  - Action-oriented slide titles (max 8 words)
  - Single business question per slide
  - Core insight (1 sentence)
  - Required visual type
  - Data requirements

#### Step 2: Data & Analytics Generation (LLM Call #2)
- **Input**: Slide blueprint
- **Output**: Chart-ready datasets and tables
- **Key Elements**:
  - Chart datasets in JSON format
  - Table data with realistic business metrics
  - Explicit assumptions
  - Source attributions

#### Step 3: Slide Content Generation (LLM Call #3)
- **Input**: Blueprint + data
- **Output**: Final slide content
- **Key Elements**:
  - Bullet points (max 5 per slide)
  - Chart captions with insights
  - "So what?" takeaways
  - Call-to-action items

#### Step 4: Slide Rendering (Code Only)
- **Technology**: python-pptx with deterministic templates
- **Features**:
  - Fixed McKinsey slide layouts
  - Professional color palette
  - Generated charts (matplotlib)
  - Footer with confidentiality notice

#### Step 5: PDF Export
- **Method**: LibreOffice headless conversion
- **Output**: Production-ready PDF deck

## File Structure

```
consulting_deck_generator/
├── core/
│   ├── orchestrator.py      # Main pipeline orchestrator
│   ├── models.py           # Data models
│   ├── llm/
│   │   └── client.py       # LLM interface
│   ├── chart_generator.py # Chart creation engine
│   └── templates.py        # Slide templates
├── output/
│   └── exports/           # Generated files
├── main.py                # CLI entry point
└── README.md             # This file
```

## Usage Examples

### Basic Usage
```bash
python main.py --problem "Should we acquire our main competitor?" --client "GlobalTech"
```

### Advanced Usage
```bash
python main.py \\
  --problem "How do we optimize our supply chain for e-commerce growth?" \\
  --client "RetailCorp" \\
  --output-dir "/path/to/output" \\
  --api-key "your-gemini-api-key"
```

## Output Specifications

### PowerPoint (.pptx)
- **Slides**: 10 slides standard deck
- **Layout**: McKinsey action title format
- **Charts**: Programmatically generated from data
- **Styling**: Professional corporate design
- **Footer**: Proprietary & Confidential

### PDF Export
- **Quality**: High-resolution export
- **Compatibility**: Universal PDF format
- **Size**: Optimized for email/attachments

## Slide Templates

### 1. Title Slide
- Client name
- Engagement hypothesis
- Confidential footer

### 2. Two-Column Layout
- Left: Key insights
- Right: Supporting data

### 3. Chart Slide
- Professional chart (bar/line/pie)
- Insight-driven caption
- Strategic title

### 4. Framework/Matrix
- 2x2 competitive positioning
- Strategic quadrants
- Actionable insights

## Chart Types

### Bar Charts
- Market size analysis
- Revenue comparison
- Performance metrics

### Line Charts
- Growth trajectories
- Financial projections
- Trend analysis

### Pie Charts
- Market share breakdown
- Segment distribution
- Portfolio composition

### Frameworks
- 2x2 competitive matrix
- Process flow diagrams
- Strategic frameworks

## Quality Standards

All generated decks meet Tier-1 consulting firm standards:
- **Pyramid Principle**: Main insight first, supporting details below
- **Hypothesis-Driven**: Clear problem statement and solution approach
- **Visual-First**: Charts drive insights, text supports
- **Action-Oriented**: All titles are imperatives (e.g., "Expand Into...")
- **Deterministic**: Consistent formatting, no free-form styling

## Dependencies

```python
# Core dependencies
python-pptx>=0.6.21
matplotlib>=3.6.0
seaborn>=0.11.0
google-generativeai>=0.8.0

# Optional dependencies
libreoffice  # For PDF export
```

## Configuration

Set environment variables:
```bash
export GEMINI_API_KEY="your-api-key"
export OUTPUT_DIR="/path/to/exports"
```

## Example Output Flow

```
Input: "Should we launch a premium subscription tier for our SaaS product?"

Output Deck:
1. Title: "Launch Premium Subscription Tier to Capture High-Value Customers"
2. Problem: "Current Revenue Model Limited to Single Pricing Tiers"
3. Hypothesis: "Premium Tier Will Increase ARPU by 40% While Retaining 85% of Base"
4. Market Analysis: [Bar Chart] Revenue Potential by Segment
5. Competitive Landscape: [Framework] Competitor Pricing Analysis
6. Financial Impact: [Table] 3-Year Revenue Projection
7. Implementation: [Process Flow] Phased Rollout Strategy
8. Risk Mitigation: [Framework] Key Risks & Response Plans
9. KPIs: [Metrics] Success Measurement Framework
10. Next Steps: "Initiate Pilot Program in Q1 with Target Segment"
```

## Production Deployment

### Requirements
- Python 3.8+
- Gemini API access
- LibreOffice (for PDF export)
- 2GB+ RAM minimum

### Performance
- **Generation Time**: 45-90 seconds per deck
- **File Size**: 2-5MB PPTX, 1-3MB PDF
- **Concurrent**: Support for 10+ parallel generations

### Monitoring
- Track success rates
- Monitor API usage
- Log generation times
- Quality assurance checks

## Quality Assurance

Every generated deck includes:
- ✅ McKinsey action titles
- ✅ Pyramid-structured content
- ✅ Data-driven insights
- ✅ Professional visuals
- ✅ Consistent formatting
- ✅ Strategic takeaways

Generated decks are production-ready for client presentations at Tier-1 consulting firms.