### FINDING_3: correctness: skills/report-tokens/scripts/run-analysis.sh:1031-1049
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] create_report_issue() only unlinks the temp body file in finally after a successful with/write; write failures can leak delete=False temp files. A disk-full or I/O error during f.write(body) exits before finally, leaving larch-report-tokens-body-* on disk. Assign body_path on open and always unlink in finally/except, or use delete=True with an explicit flush before gh reads the file.
- **Suggested revision**: Address the concern above.



