# 📊 Student Counts & Aggregations

A Streamlit application for processing Excel files to generate student counts aggregated by customizable grouping columns. Built for Junior Achievement of South Florida's data processing needs.

## Features

- **Excel File Upload**: Upload `.xlsx` files for processing
- **Sheet Selection**: Choose from multiple sheets within a workbook
- **Smart Column Detection**: Automatically detects and categorizes columns:
  - Numeric columns for aggregation
  - ZIP codes (5-digit and 9-digit formats)
  - Phone numbers
  - ID formats (X-XXXXXXXX pattern)
  - Date columns
- **Manual Overrides**: Force include or exclude columns from numeric processing
- **Data Cleaning**: 
  - Handles currency symbols ($, €) and percentage signs
  - Trims whitespace
  - Standardizes school type naming conventions
  - Fills missing values with appropriate defaults
- **Aggregation**: Groups data by selected text column and sums numeric values
- **Export**: Download results as an Excel file

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. Clone or download this repository

2. Install required dependencies:
   ```bash
   pip install streamlit pandas openpyxl
   ```

## Usage

1. **Run the application**:
   ```bash
   streamlit run JA_Elevate_App.py
   ```

2. **Upload your Excel file** using the file uploader

3. **Configure settings**:
   - Select the appropriate sheet from your workbook
   - Specify header rows to skip (default: 2)

4. **Review auto-detected columns**:
   - The app automatically identifies numeric vs. text columns
   - Auto-excludes ZIP codes, phone numbers, IDs, and dates from numeric processing

5. **Override column types** (if needed):
   - Force include columns that should be treated as numeric
   - Force exclude columns that shouldn't be aggregated

6. **Select columns**:
   - Choose a **Group By Column** (text) for categorization
   - Choose a **Value Column** (numeric) for aggregation

7. **Generate results** by clicking the "Generate Student Counts" button

8. **Download** the aggregated results as an Excel file

## Data Cleaning Applied

The application automatically applies the following transformations:

| Original Value | Standardized Value |
|----------------|-------------------|
| `PRVT`, `Prvt` | `Private School (includes Montessori, Homeschool, etc)` |
| `Charter School` | `Charter` |
| Empty/NaN (text) | `Empty` |
| Empty/NaN (numeric) | `0` |

## Column Auto-Detection

The app uses pattern matching to identify special column types:

| Type | Pattern | Example |
|------|---------|---------|
| ZIP Code | 5 or 9 digits | `33130`, `33130-1234` |
| Phone Number | Various formats | `555-123-4567`, `(555) 123-4567` |
| ID | X-XXXXXXXX | `1-12345678` |
| Date | Date separators or month names | `2024-01-15`, `Jan 15, 2024` |

## File Structure

```
Streamlit_Apps/
├── JA_Elevate_App.py    # Main application file
└── README.md            # This documentation
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `streamlit` | Web application framework |
| `pandas` | Data manipulation and analysis |
| `openpyxl` | Excel file reading/writing |

## Troubleshooting

### Common Issues

1. **"No numeric columns found"**: 
   - Check if numeric columns contain text or special characters
   - Use "Force Include as Numeric" to override detection

2. **"Error reading sheet"**:
   - Verify the sheet name exists in your Excel file
   - Check that the file is not corrupted

3. **Missing data warnings**:
   - The app fills missing values automatically
   - Consider updating the source Excel file for cleaner data

