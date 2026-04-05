# qa_run.sh
pip install pytest
pytest tests/test_qa_auto.py -v > qa_report.txt
cat qa_report.txt
