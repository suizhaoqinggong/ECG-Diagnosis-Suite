"""
PDF Report Generator
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class ReportGenerator:
    """PDF报告生成器"""

    def __init__(self, output_dir: str = "./data/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        diagnosis_result: Dict,
        image_path: Optional[str] = None,
        patient_info: Optional[Dict] = None
    ) -> str:
        """
        生成PDF诊断报告

        Args:
            diagnosis_result: 诊断结果字典
            image_path: ECG图片路径
            patient_info: 患者信息（可选）

        Returns:
            PDF文件路径
        """
        # 创建PDF文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = self.output_dir / f"report_{timestamp}.pdf"

        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # 内容列表
        story = []
        styles = getSampleStyleSheet()

        # 自定义样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=30,
            textColor=colors.HexColor('#2563eb'),
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#1e40af'),
        )

        # 标题
        story.append(Paragraph("ECG智能诊断报告", title_style))
        story.append(Spacer(1, 20))

        # 报告信息
        story.append(Paragraph(
            f"报告生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
            styles['Normal']
        ))
        story.append(Spacer(1, 20))

        # 患者信息（如果提供）
        if patient_info:
            story.append(Paragraph("患者信息", heading_style))
            patient_data = [
                ["姓名", patient_info.get("name", "未提供")],
                ["年龄", patient_info.get("age", "未提供")],
                ["性别", patient_info.get("gender", "未提供")],
            ]
            patient_table = Table(patient_data, colWidths=[2*inch, 3*inch])
            patient_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#dbeafe')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(patient_table)
            story.append(Spacer(1, 20))

        # ECG图片
        if image_path and Path(image_path).exists():
            story.append(Paragraph("心电图", heading_style))
            img = Image(image_path, width=6*inch, height=3*inch)
            story.append(img)
            story.append(Spacer(1, 20))

        # 诊断结果
        story.append(Paragraph("诊断结果", heading_style))

        result_data = [
            ["诊断结果", diagnosis_result.get("prediction", "未知")],
            ["置信度", f"{diagnosis_result.get('confidence', 0)*100:.1f}%"],
            ["严重程度", diagnosis_result.get("severity", "未评估")],
            ["ICD编码", diagnosis_result.get("icd_code", "N/A")],
        ]

        result_table = Table(result_data, colWidths=[2*inch, 4*inch])
        result_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#dbeafe')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        story.append(result_table)
        story.append(Spacer(1, 20))

        # 症状说明
        if diagnosis_result.get("description"):
            story.append(Paragraph("症状说明", heading_style))
            story.append(Paragraph(
                diagnosis_result["description"],
                styles['Normal']
            ))
            story.append(Spacer(1, 20))

        # 健康建议
        if diagnosis_result.get("recommendations"):
            story.append(Paragraph("健康建议", heading_style))
            for i, rec in enumerate(diagnosis_result["recommendations"], 1):
                story.append(Paragraph(f"{i}. {rec}", styles['Normal']))
            story.append(Spacer(1, 30))

        # 免责声明
        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.red,
            alignment=TA_CENTER,
            spaceBefore=20,
        )
        story.append(Paragraph(
            "⚠️ 免责声明",
            ParagraphStyle(
                'DisclaimerTitle',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.red,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
            )
        ))
        story.append(Paragraph(
            "本报告仅供参考，不作为临床诊断依据。如有疑虑，请及时就医咨询专业医生。",
            disclaimer_style
        ))
        story.append(Paragraph(
            "This report is for reference only and should not be used for clinical diagnosis.",
            disclaimer_style
        ))

        # 生成PDF
        doc.build(story)

        return str(pdf_path)


if __name__ == "__main__":
    # 测试代码
    generator = ReportGenerator()

    result = {
        "prediction": "房颤",
        "confidence": 0.92,
        "severity": "中等",
        "icd_code": "I48.0",
        "description": "房颤是一种常见的心律失常，心房跳动不规则且快速。",
        "recommendations": [
            "建议尽快就医心内科",
            "避免剧烈运动和情绪激动",
            "定期监测心率和血压",
        ]
    }

    pdf_path = generator.generate_report(result)
    print(f"✅ 报告已生成: {pdf_path}")
