# McKinsey-Style Deck Generator - Installation & Setup

## Requirements Installation

```bash
# Clone or create the directory structure
mkdir consulting_deck_generator
cd consulting_deck_generator

# Install core dependencies
pip install python-pptx matplotlib seaborn google-generativeai pillow

# For PDF export (optional but recommended)
# On Ubuntu/Debian:
sudo apt-get install libreoffice
# On macOS:
brew install --cask libreoffice
# On Windows:
# Download and install LibreOffice from libreoffice.org

# Verify installation
python -c "import pptx, matplotlib, seaborn; print('Dependencies installed successfully')"
```

## Environment Setup

```bash
# Set API key (use your actual key or the one provided)
export GEMINI_API_KEY="AIzaSyAXmT-FxA66LO56tKMs1__2oob-n7eJItE"

# Create output directory
mkdir -p output/exports

# Test the system
python main.py --problem "How should we expand our business internationally?" --client "TestCorp"
```

## Quick Test

```bash
# Generate your first McKinsey-style deck
python main.py \\
  --problem "Should we acquire our main competitor to accelerate market entry?" \\
  --client "GlobalTech Inc"

# Expected output:
# ├── Generated PowerPoint file
# ├── Metadata JSON file
# ├── Console summary
# └── PDF conversion (if LibreOffice installed)
```

## Integration with Existing AI Consultant App

Add this to your Flask app's consultation detail page:

```python
# In app.py, add new route
@app.route('/consultation/<consultation_id>/mckinsey-deck')
@login_required
def generate_mckinsey_deck(consultation_id):
    from consulting_deck_generator.core.orchestrator import DeckOrchestrator
    
    consultation = Consultation.query.get_or_404(consultation_id)
    if consultation.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    orchestrator = DeckOrchestrator(os.environ.get('GEMINI_API_KEY'))
    
    try:
        deck = orchestrator.generate_deck(
            consultation.query, 
            consultation.user.name
        )
        
        # Return the PPTX file
        return send_file(
            deck.pptx_path,
            as_attachment=True,
            download_name=f"mckinsey_deck_{consultation_id[:8]}.pptx"
        )
    except Exception as e:
        flash(f'Deck generation failed: {str(e)}', 'error')
        return redirect(url_for('consultation_detail', consultation_id=consultation_id))
```

## Production Deployment Notes

### Docker Support
```dockerfile
FROM python:3.9-slim

RUN apt-get update && apt-get install -y \\
    libreoffice \\
    python3-dev \\
    build-essential

WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt

CMD ["python", "main.py"]
```

### Cloud Integration
- **AWS**: Use Lambda + S3 for file storage
- **Google Cloud**: Cloud Functions + Cloud Storage
- **Azure**: Functions + Blob Storage

### API Usage
- **Rate Limits**: 60 requests/minute for Gemini
- **Cost**: ~$0.00025 per 1,000 characters
- **Monitoring**: Track generation success/failure rates

## Troubleshooting

### Common Issues
1. **LibreOffice not found**: Install LibreOffice for PDF export
2. **API rate limiting**: Add retry logic with exponential backoff
3. **Memory errors**: Increase available RAM or optimize chart generation
4. **Font issues**: System will fallback to default fonts

### Debug Mode
```python
# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

This system is production-ready for generating Tier-1 consulting quality decks.