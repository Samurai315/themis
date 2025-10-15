from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import io
import json

class ScheduleExporter:
    """Export schedules to various formats"""
    
    @staticmethod
    def export_to_pdf(schedule, metadata, include_stats=True):
        """Export schedule to PDF with formatting"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, 
                               topMargin=0.5*inch, bottomMargin=0.5*inch)
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#3B82F6'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1F2937'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        # Title
        title = Paragraph(f"<b>{metadata.get('title', 'Schedule')}</b>", title_style)
        elements.append(title)
        
        # Metadata section
        meta_text = f"""
        <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
        <b>Status:</b> {metadata.get('status', 'N/A')}<br/>
        <b>Method:</b> {metadata.get('method', 'N/A')}<br/>
        <b>Total Slots:</b> {len(schedule)}<br/>
        """
        if metadata.get('fitness'):
            meta_text += f"<b>Fitness Score:</b> {metadata['fitness']:.2f}<br/>"
        
        elements.append(Paragraph(meta_text, styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Schedule table header
        elements.append(Paragraph("<b>Schedule Timetable</b>", heading_style))
        
        # Prepare table data
        table_data = [['Entity', 'Day', 'Time', 'Room', 'Duration (hrs)']]
        
        for slot in schedule:
            table_data.append([
                str(slot.get('entity_name', slot.get('entity_id', 'N/A')))[:30],
                str(slot.get('day', 'N/A')),
                str(slot.get('time', 'N/A')),
                str(slot.get('room', 'N/A')),
                str(slot.get('duration', 'N/A'))
            ])
        
        # Create table with styling
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            
            # Body styling
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F3F4F6')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Statistics section
        if include_stats and schedule:
            elements.append(PageBreak())
            elements.append(Paragraph("<b>Schedule Statistics</b>", heading_style))
            
            # Calculate statistics
            stats = ScheduleExporter._calculate_statistics(schedule)
            
            # Day distribution
            day_data = [['Day', 'Number of Sessions']]
            for day, count in stats['day_distribution'].items():
                day_data.append([day, str(count)])
            
            day_table = Table(day_data)
            day_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F3F4F6')]),
            ]))
            
            elements.append(Paragraph("<b>Distribution by Day:</b>", styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
            elements.append(day_table)
            elements.append(Spacer(1, 0.2*inch))
            
            # Room utilization
            room_data = [['Room', 'Usage Count']]
            for room, count in stats['room_usage'].items():
                room_data.append([room, str(count)])
            
            room_table = Table(room_data)
            room_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F3F4F6')]),
            ]))
            
            elements.append(Paragraph("<b>Room Utilization:</b>", styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
            elements.append(room_table)
        
        # Constraints section (if available)
        if metadata.get('constraints'):
            elements.append(Spacer(1, 0.3*inch))
            elements.append(Paragraph("<b>Applied Constraints</b>", heading_style))
            
            constraint_data = [['Type', 'Description', 'Weight']]
            for constraint in metadata['constraints'][:10]:  # Limit to 10
                constraint_data.append([
                    str(constraint.get('type', 'N/A')),
                    str(constraint.get('description', 'N/A'))[:40],
                    str(constraint.get('weight', 'N/A'))
                ])
            
            constraint_table = Table(constraint_data, repeatRows=1)
            constraint_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F3F4F6')]),
            ]))
            
            elements.append(constraint_table)
        
        # Footer
        elements.append(Spacer(1, 0.5*inch))
        footer_text = f"Generated by Themis Schedule Optimizer | {datetime.now().strftime('%Y-%m-%d')}"
        elements.append(Paragraph(footer_text, styles['Normal']))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def export_to_excel(schedule, metadata):
        """Export schedule to Excel with multiple sheets"""
        buffer = io.BytesIO()
        
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Main schedule sheet
            if schedule:
                df = pd.DataFrame(schedule)
                # Reorder columns for better readability
                column_order = ['entity_name', 'day', 'time', 'room', 'duration']
                existing_cols = [col for col in column_order if col in df.columns]
                other_cols = [col for col in df.columns if col not in column_order]
                df = df[existing_cols + other_cols]
                
                df.to_excel(writer, sheet_name='Schedule', index=False)
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Schedule']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(str(col))
                    )
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
            
            # Metadata sheet
            meta_df = pd.DataFrame([{
                'Title': metadata.get('title', 'N/A'),
                'Status': metadata.get('status', 'N/A'),
                'Method': metadata.get('method', 'N/A'),
                'Total Slots': len(schedule),
                'Fitness Score': metadata.get('fitness', 'N/A'),
                'Generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }])
            meta_df.to_excel(writer, sheet_name='Metadata', index=False)
            
            # Statistics sheet
            if schedule:
                stats = ScheduleExporter._calculate_statistics(schedule)
                
                # Day distribution
                day_df = pd.DataFrame(list(stats['day_distribution'].items()), 
                                     columns=['Day', 'Count'])
                day_df.to_excel(writer, sheet_name='Day Distribution', index=False)
                
                # Room usage
                room_df = pd.DataFrame(list(stats['room_usage'].items()), 
                                      columns=['Room', 'Count'])
                room_df.to_excel(writer, sheet_name='Room Usage', index=False)
                
                # Time slot distribution
                time_df = pd.DataFrame(list(stats['time_distribution'].items()), 
                                      columns=['Time', 'Count'])
                time_df.to_excel(writer, sheet_name='Time Distribution', index=False)
        
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def export_to_json(schedule, metadata):
        """Export schedule to JSON with metadata"""
        data = {
            "metadata": {
                "title": metadata.get('title', 'Schedule'),
                "status": metadata.get('status', 'N/A'),
                "method": metadata.get('method', 'N/A'),
                "fitness": metadata.get('fitness'),
                "total_slots": len(schedule),
                "exported_at": datetime.now().isoformat(),
                "version": "1.0"
            },
            "schedule": schedule,
            "statistics": ScheduleExporter._calculate_statistics(schedule) if schedule else {}
        }
        
        # Add config if available
        if metadata.get('config_used'):
            data['optimization_config'] = metadata['config_used']
        
        # Add history if available
        if metadata.get('history'):
            data['optimization_history'] = metadata['history']
        
        return json.dumps(data, indent=2, default=str)
    
    @staticmethod
    def export_chart_as_image(fig, width=1200, height=800):
        """Export Plotly chart as PNG"""
        try:
            img_bytes = fig.to_image(format="png", width=width, height=height)
            return img_bytes
        except Exception as e:
            return None
    
    @staticmethod
    def _calculate_statistics(schedule):
        """Calculate statistics from schedule"""
        stats = {
            'day_distribution': {},
            'room_usage': {},
            'time_distribution': {},
            'total_slots': len(schedule),
            'unique_days': set(),
            'unique_rooms': set(),
            'unique_times': set()
        }
        
        for slot in schedule:
            # Day distribution
            day = slot.get('day', 'Unknown')
            stats['day_distribution'][day] = stats['day_distribution'].get(day, 0) + 1
            stats['unique_days'].add(day)
            
            # Room usage
            room = slot.get('room', 'Unknown')
            stats['room_usage'][room] = stats['room_usage'].get(room, 0) + 1
            stats['unique_rooms'].add(room)
            
            # Time distribution
            time = slot.get('time', 'Unknown')
            stats['time_distribution'][time] = stats['time_distribution'].get(time, 0) + 1
            stats['unique_times'].add(time)
        
        # Convert sets to counts
        stats['unique_days'] = len(stats['unique_days'])
        stats['unique_rooms'] = len(stats['unique_rooms'])
        stats['unique_times'] = len(stats['unique_times'])
        
        return stats
    
    @staticmethod
    def create_calendar_view_data(schedule):
        """Prepare data for calendar/timeline visualization"""
        calendar_data = []
        
        for slot in schedule:
            calendar_data.append({
                'Task': slot.get('entity_name', slot.get('entity_id', 'Unknown')),
                'Start': f"{slot.get('day', 'Monday')} {slot.get('time', '09:00')}",
                'Finish': f"{slot.get('day', 'Monday')} {slot.get('time', '09:00')}",
                'Resource': slot.get('room', 'Unknown')
            })
        
        return pd.DataFrame(calendar_data)
