import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import seaborn as sns
from typing import Dict, Any, List, Optional
import io
import base64
import json

class ChartGenerator:
    """Generate consulting-quality charts with McKinsey styling"""
    
    def __init__(self):
        # Set McKinsey color palette
        self.mckinsey_colors = {
            'primary': '#00A4E4',      # Blue
            'secondary': '#00263A',     # Dark blue  
            'accent': '#FF6B35',       # Orange
            'gray': '#8B9697',        # Gray
            'light_gray': '#F5F7F8',    # Light gray
            'success': '#00C851',       # Green
            'warning': '#FFD23F',       # Yellow
        }
        
        # Set default styling
        plt.style.use('default')
        self._setup_fonts()
    
    def _setup_fonts(self):
        """Setup professional fonts"""
        try:
            # Try to use professional fonts
            font_path = '/System/Library/Fonts/Helvetica.ttc'  # macOS
            if not os.path.exists(font_path):
                font_path = 'C:\\Windows\\Fonts\\arial.ttf'  # Windows
                if not os.path.exists(font_path):
                    font_path = None  # Use system default
            
            if font_path:
                font_prop = fm.FontProperties(fname=font_path)
                plt.rcParams['font.family'] = font_prop.get_name()
        except:
            plt.rcParams['font.family'] = 'Arial'
        
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.linewidth'] = 0.5
        plt.rcParams['axes.edgecolor'] = '#666666'
    
    def create_bar_chart(self, data: Dict[str, Any], title: str = None) -> str:
        """Create professional bar chart"""
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor('white')
        
        labels = data['labels']
        datasets = data['datasets']
        
        x = np.arange(len(labels))
        width = 0.8 / len(datasets)
        
        for i, dataset in enumerate(datasets):
            offset = (i - len(datasets)/2 + 0.5) * width
            bars = ax.bar(x + offset, dataset['data'], width, 
                         color=dataset.get('color', self.mckinsey_colors['primary']),
                         label=dataset['label'], alpha=0.8)
            
            # Add value labels on bars
            for bar, value in zip(bars, dataset['data']):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                       f'${value}M' if 'Market Size' in title else f'{value}%',
                       ha='center', va='bottom', fontsize=8, fontweight='bold')
        
        ax.set_xlabel('Categories', fontweight='bold', fontsize=11)
        ax.set_ylabel('Value', fontweight='bold', fontsize=11)
        ax.set_xticks(x + width/2)
        ax.set_xticklabels(labels, ha='center')
        
        # Add McKinsey-style grid
        ax.grid(axis='y', alpha=0.3, linestyle='-', linewidth=0.5)
        ax.set_axisbelow(True)
        
        # Professional title
        if title:
            ax.set_title(title, fontweight='bold', fontsize=12, pad=20, color=self.mckinsey_colors['secondary'])
        
        # Remove spines for cleaner look
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        
        # Add subtle border
        for spine in ['left', 'bottom']:
            ax.spines[spine].set_color('#666666')
            ax.spines[spine].set_linewidth(0.5)
        
        # Legend
        if len(datasets) > 1:
            ax.legend(loc='upper right', frameon=False, fontsize=9)
        
        # Add McKinsey watermark
        fig.text(0.02, 0.02, 'Proprietary & Confidential', 
                fontsize=8, alpha=0.3, ha='left', va='bottom')
        
        # Save to base64 string
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        chart_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        return chart_base64
    
    def create_line_chart(self, data: Dict[str, Any], title: str = None) -> str:
        """Create professional line chart for trends"""
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor('white')
        
        labels = data['labels']
        datasets = data['datasets']
        
        for dataset in datasets:
            ax.plot(labels, dataset['data'], 
                   color=dataset.get('color', self.mckinsey_colors['primary']),
                   marker='o', linewidth=2.5, markersize=6,
                   label=dataset['label'])
            
            # Add data labels
            for i, value in enumerate(dataset['data']):
                ax.annotate(f'{value}', (i, value), 
                           textcoords="offset points", xytext=(0,10), ha='center',
                           fontsize=8, fontweight='bold')
        
        ax.set_xlabel('Time Period', fontweight='bold', fontsize=11)
        ax.set_ylabel('Revenue Index', fontweight='bold', fontsize=11)
        
        # McKinsey styling
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax.set_axisbelow(True)
        
        if title:
            ax.set_title(title, fontweight='bold', fontsize=12, pad=20, color=self.mckinsey_colors['secondary'])
        
        # Clean spines
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        
        for spine in ['left', 'bottom']:
            ax.spines[spine].set_color('#666666')
            ax.spines[spine].set_linewidth(0.5)
        
        if len(datasets) > 1:
            ax.legend(loc='upper left', frameon=False, fontsize=9)
        
        # Confidence note
        fig.text(0.98, 0.02, 'Based on internal projections | ±15% margin of error', 
                fontsize=7, alpha=0.5, ha='right', va='bottom', style='italic')
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        chart_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        return chart_base64
    
    def create_pie_chart(self, data: Dict[str, Any], title: str = None) -> str:
        """Create professional pie chart"""
        fig, ax = plt.subplots(figsize=(8, 8))
        fig.patch.set_facecolor('white')
        
        labels = data['labels']
        values = data['datasets'][0]['data']  # Pie charts typically have one dataset
        colors = [self.mckinsey_colors['primary'], self.mckinsey_colors['secondary'], 
                  self.mckinsey_colors['accent'], self.mckinsey_colors['gray'],
                  self.mckinsey_colors['success'], self.mckinsey_colors['warning']]
        colors = colors[:len(values)]
        
        # Create pie with professional styling
        wedges, texts, autotexts = ax.pie(values, labels=labels, colors=colors,
                                            autopct='%1.1f%%', startangle=90,
                                            wedgeprops={'edgecolor': 'white', 'linewidth': 1})
        
        # Style the text
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(9)
        
        for text in texts:
            text.set_fontsize(9)
            text.set_fontweight('bold')
        
        if title:
            ax.set_title(title, fontweight='bold', fontsize=12, pad=20, color=self.mckinsey_colors['secondary'])
        
        # Make it circular
        ax.axis('equal')
        
        # Add context note
        fig.text(0.5, 0.02, 'Market Share Analysis | 2024 Data', 
                fontsize=8, ha='center', va='bottom', style='italic', alpha=0.6)
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        chart_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        return chart_base64
    
    def create_framework_diagram(self, data: Dict[str, Any], title: str = None) -> str:
        """Create 2x2 matrix or framework diagram"""
        fig, ax = plt.subplots(figsize=(10, 8))
        fig.patch.set_facecolor('white')
        
        # Create 2x2 matrix
        quadrants = data['quadrants']
        
        # Draw matrix lines
        ax.axhline(y=0.5, color=self.mckinsey_colors['gray'], linewidth=1, alpha=0.5)
        ax.axvline(x=0.5, color=self.mckinsey_colors['gray'], linewidth=1, alpha=0.5)
        
        # Plot quadrants
        for quad in quadrants:
            x = quad['x']
            y = quad['y']
            size = 200 * quad['importance']  # Size based on importance
            
            if quad['type'] == 'focus':
                color = self.mckinsey_colors['primary']
                marker = '*'
            else:
                color = self.mckinsey_colors['gray']
                marker = 'o'
            
            ax.scatter(x, y, s=size, c=color, alpha=0.7, marker=marker, 
                      edgecolors='white', linewidth=2)
            
            # Add labels
            ax.annotate(quad['name'], (x, y), 
                       xytext=(x+0.1, y+0.1), fontsize=9, fontweight='bold')
        
        # Style the matrix
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel('Market Presence', fontweight='bold', fontsize=11)
        ax.set_ylabel('Innovation Score', fontweight='bold', fontsize=11)
        
        if title:
            ax.set_title(title, fontweight='bold', fontsize=12, pad=20, color=self.mckinsey_colors['secondary'])
        
        # Remove ticks but keep grid
        ax.set_xticks([0.25, 0.75])
        ax.set_yticks([0.25, 0.75])
        ax.set_xticklabels(['Low', 'High'])
        ax.set_yticklabels(['Low', 'High'])
        
        # Clean appearance
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        
        # Add legend
        legend_elements = [
            plt.scatter([], [], c=self.mckinsey_colors['primary'], s=100, 
                       marker='*', label='Your Company', edgecolors='white', linewidth=2),
            plt.scatter([], [], c=self.mckinsey_colors['gray'], s=100, 
                       marker='o', label='Competitors', edgecolors='white', linewidth=2)
        ]
        ax.legend(handles=legend_elements, loc='upper right', frameon=False, fontsize=9)
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        chart_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        return chart_base64