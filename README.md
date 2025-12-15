🤖 AI Finance Agent: Document Extraction and Dashboard
Short Description
A robust, full-stack Python application designed to automate the invoice processing workflow. It uses a Watchdog observer to monitor a file directory, Azure Document Intelligence for structured OCR, and the Gemini API for highly accurate, validated JSON data extraction, all feeding into a real-time PySide6 (Qt) dashboard.

🌟 Key Features
Real-time Monitoring: Uses watchdog to automatically detect new invoice image uploads (.jpg, .png).

Structured Data Pipeline: Leverages Azure Document Intelligence (prebuilt-layout) for high-quality document parsing.

Intelligent Extraction: Employs the Gemini API with strict JSON formatting to extract vendor details, dates, and line-item totals.

Internal Validation: Includes an agent-side check to verify the sum of extracted line items matches the total pre-tax amount.

Live Dashboard: A visually appealing PySide6 UI that displays real-time system logs, a summary of processed invoices, and a cumulative spending chart.

⚙️ Architecture
This is a two-part system designed for concurrent operation:

Backend Agent (agent_runner.py): Runs the file monitor and the core extraction logic (OCR + LLM).

Frontend Dashboard (ui.py): Runs the GUI, handles user interaction, and provides the live data visualization.
