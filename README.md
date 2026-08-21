# Filing Day Decisions

Filing Day Decisions is a six-round Streamlit simulation about financial reporting concepts. Students act as the final reviewer for a fictional company's annual financial report and make connected decisions about:

- GAAP, FASB, SEC, and PCAOB roles
- relevance, predictive value, confirmatory value, and materiality
- completeness, neutrality, and freedom from material error
- comparability, consistency, verifiability, timeliness, and understandability
- the monetary unit and periodicity assumptions
- historical cost, fair value, and full disclosure

The activity intentionally uses straightforward events and reporting judgments rather than complicated transactions.

## Run locally

Python 3.11 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Open the local URL shown by Streamlit, normally `http://localhost:8501`.

## Run the automated checks

The content and scoring checks use Python's standard-library test runner:

```bash
python -m unittest discover -s tests -v
```

## Deploy with GitHub and Streamlit Community Cloud

1. Create a GitHub repository and add this project at the repository root.
2. Commit and push the files to the desired deployment branch.
3. In Streamlit Community Cloud, create a new app from the repository.
4. Select `streamlit_app.py` as the entrypoint.
5. Deploy. No secrets or external services are required for this draft.

Community Cloud installs the Python packages declared in `requirements.txt`. The visual theme is defined in `.streamlit/config.toml`.

## Project structure

```text
.
├── .github/workflows/tests.yml     # GitHub content/scoring checks
├── .streamlit/config.toml          # Streamlit theme and server settings
├── app/
│   ├── content.py                  # Rounds, questions, and feedback
│   └── engine.py                   # Pure scoring and summary logic
├── tests/test_engine.py            # Automated content/scoring tests
├── requirements.txt                # Deployment dependency declaration
└── streamlit_app.py                # Community Cloud entrypoint and UI
```

## Visual identity

The design uses a University of Dayton-inspired red and blue palette. It does not bundle or reproduce an official University logo or other protected mark.
