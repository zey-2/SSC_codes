# SmallSat Customized Crawler

This Python script downloads Small Satellite Conference papers and extracts metadata (title, date, abstract) into an Excel file.

You can optionally use a test mode to download only three papers for quick testing. Debug output and saving HTML files are now controlled by the logging level (set log_level to logging.DEBUG).

## Features

- Scrapes paper links and dates from the conference schedule
- Downloads each paper's PDF
- Extracts title and abstract from each paper's webpage
- Saves all metadata in an Excel file

## Usage

1. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
2. Run the script:
   ```cmd
   python SmallSat_CustomizedCrawler.py
   ```
   - By default, downloads all 2025 papers and saves results in the `2025/` folder.
   - To quickly test, set `test_flag=True` in the `main()` function call at the bottom of the script. This will download only three papers and exit early.

## Output

- PDFs and debug HTML files are saved in the output directory (e.g., `2025/`)
- Metadata is saved in `papers_2025.xlsx` in the output directory

## Requirements

- Python 3.11+

## Customization

You can customize the script by changing the following arguments in the `main()` function call at the bottom of the script:

- `year`: The conference year to scrape (default: 2025)
- `test_flag`: If True, downloads only three papers for quick testing (default: False)
- `log_level`: Sets the logging level (default: `logging.INFO`). Accepts standard Python logging levels such as `logging.DEBUG`, `logging.INFO`, `logging.WARNING`, etc.

### Example: Enable debug output and save HTML files

```python
main(year=2025, test_flag=False, log_level=logging.DEBUG)
```

Setting `log_level=logging.DEBUG` enables verbose logging and saves HTML debug files for each page.

### Example: Use warning-level logging and progress bar

```python
main(year=2025, test_flag=False, log_level=logging.WARNING)
```

Setting `log_level=logging.WARNING` will show only warnings and errors, and display a progress bar during downloads.
