#!/usr/bin/env python3
"""
McKinsey-Style Consulting Deck Generator
Production-ready system for generating Tier-1 consulting presentations
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Add core modules to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.orchestrator import DeckOrchestrator

def main():
    parser = argparse.ArgumentParser(description='Generate McKinsey-style consulting deck')
    parser.add_argument('--problem', required=True, help='Client problem statement')
    parser.add_argument('--client', default='Client', help='Client name')
    parser.add_argument('--api-key', help='Gemini API key (or set GEMINI_API_KEY env)')
    parser.add_argument('--output-dir', help='Output directory', default='output/exports')
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.environ.get('GEMINI_API_KEY', 'AIzaSyAXmT-FxA66LO56tKMs1__2oob-n7eJItE')
    
    if not api_key:
        print("Error: Gemini API key required. Set GEMINI_API_KEY or use --api-key")
        sys.exit(1)
    
    print(f"\\n{'='*60}")
    print("McKINSEY-STYLE CONSULTING DECK GENERATOR")
    print(f"{'='*60}")
    print(f"Client: {args.client}")
    print(f"Problem: {args.problem}")
    print(f"Engagement ID: {datetime.now().strftime('%Y%m%d_%H%M%S')}")
    print(f"{'='*60}\\n")
    
    try:
        # Initialize orchestrator
        orchestrator = DeckOrchestrator(api_key)
        
        # Generate the deck
        print("Initiating deck generation pipeline...")
        deck = orchestrator.generate_deck(args.problem, args.client)
        
        # Display results
        summary = orchestrator.get_deck_summary(deck)
        
        print(f"\\n{'='*60}")
        print("DECK GENERATION COMPLETED SUCCESSFULLY")
        print(f"{'='*60}")
        print(f"\\nGenerated Files:")
        print(f"  • PowerPoint: {deck.pptx_path}")
        print(f"  • PDF: {deck.pdf_path or 'Conversion pending'}")
        
        print(f"\\nDeck Summary:")
        print(f"  • Total Slides: {summary['total_slides']}")
        print(f"  • Hypothesis: {summary['hypothesis']}")
        print(f"  • Generated: {summary['generated_at']}")
        
        print(f"\\n{'='*60}")
        print("READY FOR CLIENT PRESENTATION")
        print(f"{'='*60}")
        
        # Save metadata
        metadata_path = os.path.join(
            os.path.dirname(deck.pptx_path), 
            f"{summary['engagement_id']}_metadata.json"
        )
        with open(metadata_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\\nMetadata saved: {metadata_path}")
        
    except Exception as e:
        print(f"\\nERROR: Deck generation failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()