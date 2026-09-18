@echo off
echo Running Synthetic Degradation Engine and Evaluation Benchmark...
python evaluation/evaluate.py
echo.
echo Benchmark complete! Output written to evaluation/results/benchmark_results.json
pause
