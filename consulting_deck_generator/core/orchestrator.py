import os
import json
import uuid
import base64
import io
from datetime import datetime
from typing import Dict, Any, List, Optional

from .models import DeckBlueprint, GeneratedDeck, SlideContent, SlideData
from .llm.client import LLMClient
from .chart_generator import ChartGenerator
from .templates import SlideTemplates

class DeckOrchestrator:
    """Multi-step pipeline orchestrator for McKinsey-style decks"""
    
    def __init__(self, api_key: str):
        self.llm_client = LLMClient(api_key)
        self.chart_generator = ChartGenerator()
        self.templates = SlideTemplates()
        
        # Create output directory
        self.output_dir = "consulting_deck_generator/output/exports"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_deck(self, problem_statement: str, client_name: str = "Client") -> GeneratedDeck:
        """Execute full 5-step pipeline"""
        
        engagement_id = str(uuid.uuid4())
        
        try:
            # STEP 1: Engagement Structuring
            print("Step 1: Structuring engagement blueprint...")
            blueprint_raw = self.llm_client.step1_engagement_structuring(problem_statement)
            
            blueprint = DeckBlueprint(
                engagement_id=engagement_id,
                client_name=client_name,
                problem_statement=problem_statement,
                slides=[],  # Will be populated from blueprint_raw
                hypothesis=blueprint_raw.get('hypothesis', ''),
                methodology=blueprint_raw.get('methodology', '')
            )
            
            # Convert to SlideBlueprint objects
            from .models import SlideBlueprint
            blueprint.slides = [
                SlideBlueprint(
                    slide_id=slide['slide_id'],
                    title=slide['title'],
                    key_question=slide['key_question'],
                    core_insight=slide['core_insight'],
                    visual_type=slide['visual_type'],
                    data_requirements=slide['data_requirements'],
                    position_in_deck=slide['position_in_deck'],
                    slide_template=slide['slide_template']
                )
                for slide in blueprint_raw['slides']
            ]
            
            # STEP 2: Data & Analytics Generation
            print("Step 2: Generating data and analytics...")
            data_raw = self.llm_client.step2_data_generation(blueprint_raw)
            
            # Convert to SlideData objects
            data_slides = []
            for slide_id, slide_data in data_raw['slide_data'].items():
                from .models import SlideData
                data_slides.append(SlideData(
                    slide_id=slide_id,
                    chart_data=slide_data.get('chart_data', {}),
                    table_data=slide_data.get('table_data'),
                    assumptions=slide_data.get('assumptions', []),
                    sources=slide_data.get('sources', []),
                    metrics=slide_data.get('metrics', {})
                ))
            
            # STEP 3: Slide Content Generation
            print("Step 3: Generating slide content...")
            content_raw = self.llm_client.step3_content_generation(blueprint_raw, data_raw)
            
            # Convert to SlideContent objects
            content_slides = []
            for slide_id, slide_content in content_raw['slide_content'].items():
                content_slides.append(SlideContent(
                    slide_id=slide_id,
                    title=slide_content['title'],
                    bullets=slide_content.get('bullets', []),
                    chart_caption=slide_content.get('chart_caption'),
                    so_what_takeaway=slide_content.get('so_what_takeaway'),
                    call_to_action=slide_content.get('call_to_action'),
                    visual_config=slide_content.get('visual_config')
                ))
            
            # STEP 4: Slide Rendering
            print("Step 4: Rendering PowerPoint slides...")
            pptx_path = self._render_powerpoint(blueprint, content_slides, data_slides)
            
            # STEP 5: PDF Export
            print("Step 5: Exporting to PDF...")
            pdf_path = self._export_to_pdf(pptx_path)
            
            # Return complete package
            return GeneratedDeck(
                blueprint=blueprint,
                content_slides=content_slides,
                data_slides=data_slides,
                metadata={
                    'engagement_id': engagement_id,
                    'generated_at': datetime.now().isoformat(),
                    'problem_statement': problem_statement,
                    'client_name': client_name,
                    'total_slides': len(blueprint.slides),
                    'file_size': os.path.getsize(pptx_path)
                },
                pptx_path=pptx_path,
                pdf_path=pdf_path
            )
            
        except Exception as e:
            raise Exception(f"Deck generation failed: {str(e)}")
    
    def _render_powerpoint(self, blueprint: DeckBlueprint, content_slides: List[SlideContent], data_slides: List[SlideData]) -> str:
        """Render PowerPoint using deterministic templates"""
        
        prs = Presentation()
        
        # Sort slides by position
        sorted_slides = sorted(blueprint.slides, key=lambda x: x.position_in_deck)
        
        # Create data lookup
        data_lookup = {slide.slide_id: slide for slide in data_slides}
        content_lookup = {slide.slide_id: slide for slide in content_slides}
        
        for i, slide_blueprint in enumerate(sorted_slides):
            slide_content = content_lookup.get(slide_blueprint.slide_id)
            slide_data = data_lookup.get(slide_blueprint.slide_id)
            
            # Render based on template type
            if i == 0:  # Title slide
                self.templates.create_title_slide(
                    prs, 
                    title=slide_blueprint.title,
                    subtitle=blueprint.hypothesis,
                    client=blueprint.client_name
                )
            elif slide_blueprint.slide_template == "two_column":
                if slide_content:
                    bullets = slide_content.bullets
                    left_col = bullets[:len(bullets)//2] if len(bullets) > 1 else bullets
                    right_col = bullets[len(bullets)//2:] if len(bullets) > 1 else []
                    
                    self.templates.create_two_column_slide(
                        prs,
                        title=slide_blueprint.title,
                        left_content=left_col,
                        right_content=right_col
                    )
            
            elif slide_blueprint.slide_template == "chart_main":
                chart_base64 = None
                if slide_data and slide_data.chart_data:
                    chart_type = slide_blueprint.visual_type
                    
                    if chart_type == "bar_chart":
                        chart_base64 = self.chart_generator.create_bar_chart(
                            slide_data.chart_data, 
                            title=slide_content.visual_config.get('chart_title') if slide_content else None
                        )
                    elif chart_type == "line_chart":
                        chart_base64 = self.chart_generator.create_line_chart(
                            slide_data.chart_data,
                            title=slide_content.visual_config.get('chart_title') if slide_content else None
                        )
                    elif chart_type == "pie_chart":
                        chart_base64 = self.chart_generator.create_pie_chart(
                            slide_data.chart_data,
                            title=slide_content.visual_config.get('chart_title') if slide_content else None
                        )
                
                if chart_base64:
                    caption = slide_content.chart_caption if slide_content else None
                    self.templates.create_chart_slide(
                        prs,
                        title=slide_blueprint.title,
                        chart_base64=chart_base64,
                        caption=caption
                    )
            
            elif slide_blueprint.slide_template == "framework":
                if slide_data and slide_data.chart_data:
                    quadrants = slide_data.chart_data.get('quadrants', [])
                    if quadrants:
                        # Convert to 2x2 framework format
                        framework_data = [
                            quadrants[:2],  # Top row
                            quadrants[2:4]  # Bottom row
                        ] if len(quadrants) >= 4 else [[quadrants[0]]]
                        
                        self.templates.create_framework_slide(
                            prs,
                            title=slide_blueprint.title,
                            framework_data=[[q.get('name', '') for q in row] for row in framework_data]
                        )
        
        # Save PowerPoint
        filename = f"{blueprint.engagement_id}_consulting_deck.pptx"
        pptx_path = os.path.join(self.output_dir, filename)
        prs.save(pptx_path)
        
        return pptx_path
    
    def _export_to_pdf(self, pptx_path: str) -> str:
        """Convert PPTX to PDF using headless LibreOffice or similar"""
        try:
            # Method 1: Using LibreOffice (if available)
            import subprocess
            
            pdf_filename = pptx_path.replace('.pptx', '.pdf')
            
            # Try LibreOffice conversion
            try:
                cmd = [
                    'libreoffice', '--headless', '--convert-to', 'pdf',
                    '--outdir', os.path.dirname(pptx_path),
                    pptx_path
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                
                if os.path.exists(pdf_filename):
                    return pdf_filename
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
            
            # Method 2: Use python-pptx direct approach (placeholder)
            # In production, you'd use a proper conversion service
            print(f"PDF conversion would happen here. PPTX saved at: {pptx_path}")
            return pptx_path  # Return PPTX path for now
            
        except Exception as e:
            print(f"PDF conversion failed: {str(e)}")
            return pptx_path
    
    def get_deck_summary(self, deck: GeneratedDeck) -> Dict[str, Any]:
        """Get summary of generated deck"""
        return {
            'engagement_id': deck.metadata['engagement_id'],
            'client': deck.metadata['client_name'],
            'total_slides': deck.metadata['total_slides'],
            'hypothesis': deck.blueprint.hypothesis,
            'generated_at': deck.metadata['generated_at'],
            'files': {
                'pptx': deck.pptx_path,
                'pdf': deck.pdf_path
            }
        }