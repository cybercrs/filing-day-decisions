"""Scenario and decision content for Filing Day Decisions."""

from __future__ import annotations


def option(
    text: str,
    feedback: str,
    impacts: dict[str, int],
    *,
    correct: bool = False,
) -> dict[str, object]:
    return {
        "text": text,
        "feedback": feedback,
        "impacts": impacts,
        "correct": correct,
    }


ROUNDS = [
    {
        "slug": "rulebook",
        "eyebrow": "Round 1 of 6 · The reporting rulebook",
        "title": "Know who does what",
        "scenario": (
            "Gem City Goods is preparing its annual financial report. Three messages arrive "
            "from people asking who establishes, oversees, and checks financial reporting."
        ),
        "goal": "Connect GAAP, FASB, SEC, and PCAOB to their distinct roles.",
        "reflection_question": "Why is it useful to separate standard setting, market oversight, and audit oversight?",
        "reflection_answer": (
            "The separate roles create checks and balances. FASB develops the reporting rules, "
            "the SEC oversees the public-market reporting environment, and the PCAOB oversees "
            "public-company audit work. Together, those roles strengthen consistency and trust."
        ),
        "questions": [
            {
                "id": "rulebook-fasb",
                "concept": "Standard setting",
                "prompt": "The controller asks which organization is the primary U.S. accounting standard setter.",
                "options": [
                    option(
                        "Financial Accounting Standards Board (FASB)",
                        "Correct. FASB is the primary private-sector body that establishes U.S. accounting standards.",
                        {"confidence": 7, "comparability": 3},
                        correct=True,
                    ),
                    option(
                        "Securities and Exchange Commission (SEC)",
                        "The SEC oversees U.S. financial markets, but FASB is the primary accounting standard setter.",
                        {"confidence": -3},
                    ),
                    option(
                        "Public Company Accounting Oversight Board (PCAOB)",
                        "The PCAOB focuses on auditing standards and audit-firm performance, not GAAP standard setting.",
                        {"confidence": -3},
                    ),
                ],
                "explanation": "GAAP needs a standard-setting body so companies have a common reporting foundation.",
            },
            {
                "id": "rulebook-sec",
                "concept": "Regulatory oversight",
                "prompt": "An investor asks which U.S. government agency oversees financial markets and accounting standard-setting bodies.",
                "options": [
                    option(
                        "Securities and Exchange Commission (SEC)",
                        "Correct. The SEC is the federal agency with this oversight responsibility.",
                        {"confidence": 7, "usefulness": 2},
                        correct=True,
                    ),
                    option(
                        "Financial Accounting Standards Board (FASB)",
                        "FASB establishes accounting standards, but it is not the government market regulator.",
                        {"confidence": -3},
                    ),
                    option(
                        "Public Company Accounting Oversight Board (PCAOB)",
                        "The PCAOB oversees public-company auditing, but the SEC is the government agency responsible for financial-market oversight.",
                        {"confidence": -4},
                    ),
                ],
                "explanation": "The SEC protects the public-interest role of financial reporting in U.S. markets.",
            },
            {
                "id": "rulebook-pcaob",
                "concept": "Audit oversight",
                "prompt": "The audit committee asks which body determines auditing standards and reviews audit firms' performance.",
                "options": [
                    option(
                        "Public Company Accounting Oversight Board (PCAOB)",
                        "Correct. The PCAOB is responsible for public-company audit oversight.",
                        {"confidence": 7, "faithfulness": 3},
                        correct=True,
                    ),
                    option(
                        "Financial Accounting Standards Board (FASB)",
                        "FASB sets accounting standards rather than reviewing the performance of auditing firms.",
                        {"confidence": -3},
                    ),
                    option(
                        "Securities and Exchange Commission (SEC)",
                        "The SEC has market oversight, but the PCAOB has this specific audit-focused role.",
                        {"confidence": -2},
                    ),
                ],
                "explanation": "Accounting standards guide the report; auditing standards guide the independent examination of it.",
            },
        ],
    },
    {
        "slug": "relevance",
        "eyebrow": "Round 2 of 6 · Useful information",
        "title": "Decide what matters",
        "scenario": (
            "Management has collected more information than users need. Your job is to keep "
            "information that can make a difference to a lender or investor's decision."
        ),
        "goal": "Apply predictive value, confirmatory value, and materiality.",
        "reflection_question": "Can the same dollar error be material to one company but not another? Why?",
        "reflection_answer": (
            "Yes. Materiality depends on whether the item could influence a user's decision in "
            "that company's circumstances. The company's size, the size of the item, and the "
            "nature of the information can all matter."
        ),
        "questions": [
            {
                "id": "relevance-predictive",
                "concept": "Predictive value",
                "prompt": "Which item would best help a lender form expectations about next quarter's cash collections?",
                "options": [
                    option(
                        "Current customer orders and the recent collection pattern",
                        "Correct. These facts can help the lender form expectations about future cash collections.",
                        {"usefulness": 8, "timeliness": 2},
                        correct=True,
                    ),
                    option(
                        "Last quarter's total sales, with no information about current orders or collections",
                        "Past sales provide context, but by themselves they are less useful for predicting next quarter's cash collections than current orders and recent collection behavior.",
                        {"usefulness": -4},
                    ),
                    option(
                        "The historical cost of the company's delivery vehicles",
                        "The vehicles' recorded cost is accounting information, but it does not help the lender estimate next quarter's customer cash collections.",
                        {"usefulness": -4},
                    ),
                ],
                "explanation": "Relevant information has predictive value when it helps users form expectations about the future.",
            },
            {
                "id": "relevance-confirmatory",
                "concept": "Confirmatory value",
                "prompt": "Last quarter, management predicted $90,000 of sales. Which information has the clearest confirmatory value?",
                "options": [
                    option(
                        "Actual sales for the quarter were $88,000",
                        "Correct. Actual results allow users to confirm or revise their earlier expectations.",
                        {"usefulness": 8, "faithfulness": 2},
                        correct=True,
                    ),
                    option(
                        "Management now predicts $95,000 of sales for next quarter",
                        "This new forecast may have predictive value, but it does not confirm whether last quarter's $90,000 forecast was accurate.",
                        {"usefulness": -4},
                    ),
                    option(
                        "Customer orders received during the first week of the new quarter",
                        "New-quarter orders may help predict future sales, but they do not directly compare last quarter's forecast with last quarter's actual result.",
                        {"usefulness": -2},
                    ),
                ],
                "explanation": "Confirmatory value helps users confirm or correct prior expectations.",
            },
            {
                "id": "relevance-materiality",
                "concept": "Materiality",
                "prompt": "How should the team decide whether an error is material?",
                "options": [
                    option(
                        "Ask whether omitting or misstating it could influence a user's decision in this company's circumstances",
                        "Correct. Materiality is company-specific and depends on whether the information could influence decisions.",
                        {"usefulness": 7, "faithfulness": 3},
                        correct=True,
                    ),
                    option(
                        "Treat every error as material, regardless of size or circumstances",
                        "Errors should be corrected, but materiality specifically considers whether an item could influence decisions.",
                        {"usefulness": -2},
                    ),
                    option(
                        "Use one universal dollar amount for every company",
                        "Materiality is company-specific, so a universal cutoff can ignore important context.",
                        {"usefulness": -4, "faithfulness": -2},
                    ),
                ],
                "explanation": "A modest amount for a large company might be significant for a much smaller company—or important because of its nature.",
            },
        ],
    },
    {
        "slug": "faithful",
        "eyebrow": "Round 3 of 6 · Credible reporting",
        "title": "Tell the whole story",
        "scenario": (
            "The first report draft looks polished, but polished is not the same as faithful. "
            "Review it for completeness, neutrality, and material error."
        ),
        "goal": "Recognize the three ingredients of faithful representation.",
        "reflection_question": "Why can each sentence in a report be factually accurate while the report as a whole is still misleading?",
        "reflection_answer": (
            "A report can use accurate sentences yet omit an important obligation, unfavorable "
            "result, or other fact. Faithful representation requires a complete and neutral picture, "
            "not merely individual statements that are technically true."
        ),
        "questions": [
            {
                "id": "faithful-complete",
                "concept": "Completeness",
                "draft_paragraph": (
                    "Gem City Goods maintained a stable capital structure throughout the year. "
                    "Routine vendor balances were paid according to normal terms, and management "
                    "reports that the company has no significant long-term obligations that would "
                    "affect its financial flexibility."
                ),
                "fact": (
                    "The company signed a $425,000 bank loan that is payable over the next five years."
                ),
                "prompt": "Which quality of faithful representation is most directly violated?",
                "options": [
                    option(
                        "Completeness",
                        "Correct. Important information has been omitted from the report.",
                        {"faithfulness": 8, "confidence": 2},
                        correct=True,
                    ),
                    option(
                        "Neutrality",
                        "The wording may favor management, but the most direct problem is that a significant obligation is missing from the report.",
                        {"faithfulness": -4},
                    ),
                    option(
                        "Consistency",
                        "Consistency concerns using accounting methods from period to period; the direct problem here is omitted information.",
                        {"faithfulness": -4},
                    ),
                ],
                "explanation": "A complete depiction includes the important information users need to understand what happened.",
            },
            {
                "id": "faithful-neutral",
                "concept": "Neutrality",
                "draft_paragraph": (
                    "Sales increased 4% during the year, demonstrating strong, broad-based customer "
                    "demand and positioning the company for continued growth. Management views the "
                    "increase as evidence that customers remain highly satisfied with the product line."
                ),
                "fact": (
                    "Product returns increased 18% and repeat-customer orders declined 6% during "
                    "the same period."
                ),
                "prompt": "How should the draft disclosure be revised?",
                "options": [
                    option(
                        "Use balanced wording that does not steer users toward management's preferred conclusion",
                        "Correct. Neutral information is not slanted toward one position or outcome.",
                        {"faithfulness": 8, "confidence": 2},
                        correct=True,
                    ),
                    option(
                        "Keep the conclusion but add that management expects returns to decline next period",
                        "A favorable forecast does not correct wording that currently overstates the strength of demand.",
                        {"faithfulness": -5, "confidence": -2},
                    ),
                    option(
                        "Move the return information to a later page while leaving the conclusion unchanged",
                        "Changing the location of the unfavorable evidence does not make the conclusion balanced.",
                        {"usefulness": -3},
                    ),
                ],
                "explanation": "Neutral presentation avoids selecting or wording information to favor one side.",
            },
            {
                "id": "faithful-error",
                "concept": "Free from material error",
                "draft_paragraph": (
                    "At year-end, Gem City Goods reported accounts payable of $1,500. Management "
                    "used this balance when calculating total current liabilities and preparing the "
                    "financial statements for release."
                ),
                "fact": (
                    "The accounts payable control account and supplier statements both show a "
                    "balance of $15,000."
                ),
                "prompt": "How should the draft disclosure be revised before the report is released?",
                "options": [
                    option(
                        "Correct the amount and recheck the supporting records before release",
                        "Correct. A material error should be fixed before users rely on the report.",
                        {"faithfulness": 8, "confidence": 3},
                        correct=True,
                    ),
                    option(
                        "Leave the amount and describe it as an estimate in the notes",
                        "A verified payable is not an estimate; describing the error differently does not correct the material misstatement.",
                        {"faithfulness": -6, "confidence": -3},
                    ),
                    option(
                        "Use $1,500 in the statements but correct the supplier detail after the filing",
                        "The financial statements should agree with the supporting records before users rely on them.",
                        {"faithfulness": -6, "usefulness": -3},
                    ),
                ],
                "explanation": "Free from material error means the description and process are accurate enough for users to rely on them.",
            },
        ],
    },
    {
        "slug": "enhance",
        "eyebrow": "Round 4 of 6 · Make useful information better",
        "title": "Strengthen the report",
        "scenario": (
            "The core information is relevant and faithfully represented. Now improve how well "
            "users can compare, check, receive, and understand it."
        ),
        "goal": "Distinguish comparability, consistency, verifiability, timeliness, and understandability.",
        "reflection_question": "Can an enhancing quality rescue information that is irrelevant or not faithfully represented?",
        "reflection_answer": (
            "No. Comparability, verifiability, timeliness, and understandability make useful "
            "information better, but they cannot make irrelevant or misleading information useful. "
            "Relevance and faithful representation remain the foundation."
        ),
        "questions": [
            {
                "id": "enhance-compare-consistent",
                "concept": "Comparability and consistency",
                "prompt": "Which statement correctly distinguishes comparability from consistency?",
                "options": [
                    option(
                        "Comparability helps compare different companies; consistency helps compare the same company across periods",
                        "Correct. Both support comparison, but they focus on different comparison settings.",
                        {"comparability": 9, "usefulness": 2},
                        correct=True,
                    ),
                    option(
                        "Comparability focuses on one company across periods; consistency focuses on different companies in the same period",
                        "This reverses the usual distinction: consistency is the same company across periods, while comparability often concerns different companies.",
                        {"comparability": -5},
                    ),
                    option(
                        "Comparability requires identical reported amounts; consistency requires identical business results each year",
                        "Useful comparisons do not require companies to report identical numbers or achieve identical results.",
                        {"comparability": -4},
                    ),
                ],
                "explanation": "A justified accounting change may occur, but explaining it helps users understand why results differ.",
            },
            {
                "id": "enhance-verifiable",
                "concept": "Verifiability",
                "prompt": "Which action most improves verifiability?",
                "options": [
                    option(
                        "Keep supporting records so independent reviewers using the same method can reach similar results",
                        "Correct. Verifiability is strengthened when informed independent observers can obtain similar results.",
                        {"confidence": 7, "faithfulness": 3},
                        correct=True,
                    ),
                    option(
                        "Have the finance team agree on an estimate without preserving the calculation or evidence",
                        "Internal agreement without documentation does not allow an independent observer to repeat the work.",
                        {"confidence": -5},
                    ),
                    option(
                        "Use management's preferred estimate and label it reasonable without showing the method",
                        "Calling an estimate reasonable does not make the method or supporting evidence independently checkable.",
                        {"confidence": -4, "usefulness": -2},
                    ),
                ],
                "explanation": "Verifiability does not require perfect agreement, but independent observers should be able to reach similar conclusions.",
            },
            {
                "id": "enhance-timely",
                "concept": "Timeliness",
                "prompt": "The annual report is accurate but arrives after the lender has already made its decision. Which quality suffered?",
                "options": [
                    option(
                        "Timeliness",
                        "Correct. Information must arrive while it can still influence a decision.",
                        {"timeliness": 10, "usefulness": 2},
                        correct=True,
                    ),
                    option(
                        "Verifiability",
                        "The report may be supportable, but the specific failure is that it reached the lender after the decision.",
                        {"timeliness": -5},
                    ),
                    option(
                        "Understandability",
                        "The scenario does not indicate that the report was unclear; it indicates that the report arrived too late to be useful.",
                        {"timeliness": -5},
                    ),
                ],
                "explanation": "Even accurate information loses usefulness when decision-makers receive it too late.",
            },
            {
                "id": "enhance-understandable",
                "concept": "Understandability",
                "prompt": "Which revision best improves understandability without removing important facts?",
                "options": [
                    option(
                        "Use clear labels, concise explanations, and a logical presentation",
                        "Correct. Clear, concise organization helps reasonably informed users interpret the report.",
                        {"usefulness": 8, "confidence": 2},
                        correct=True,
                    ),
                    option(
                        "Replace explanations with unexplained abbreviations",
                        "Unexplained abbreviations make information harder to interpret.",
                        {"usefulness": -5},
                    ),
                    option(
                        "Omit a major obligation because it is difficult to explain",
                        "Understandability never justifies leaving out important information.",
                        {"faithfulness": -5, "usefulness": -3},
                    ),
                ],
                "explanation": "Understandability improves presentation; it does not permit oversimplifying away material information.",
            },
        ],
    },
    {
        "slug": "assumptions",
        "eyebrow": "Round 5 of 6 · Reporting assumptions",
        "title": "Draw the reporting boundaries",
        "scenario": (
            "Before preparing the statements, the team must decide which events enter the "
            "accounting records and what time period the report covers."
        ),
        "goal": "Apply the monetary unit and periodicity assumptions to simple events.",
        "reflection_question": "What useful information might matter to users even though it is not recorded as a dollar transaction?",
        "reflection_answer": (
            "Examples include the experience of a newly hired employee, customer satisfaction, "
            "employee morale, or a strong product idea. These facts may influence decisions, but "
            "they are not recorded as accounting transactions until a measurable monetary event occurs."
        ),
        "questions": [
            {
                "id": "assumption-monetary",
                "concept": "Monetary unit assumption",
                "prompt": "Which event can be included in the accounting records because it is expressed in money?",
                "options": [
                    option(
                        "The company paid employees $12,000 for work performed",
                        "Correct. The payment is a measurable monetary transaction.",
                        {"faithfulness": 7, "usefulness": 2},
                        correct=True,
                    ),
                    option(
                        "The company signed an employment offer stating a $60,000 annual salary, but the employee has not started work",
                        "The salary amount is known, but no employee service or wage payment has occurred yet to create a recorded expense or liability.",
                        {"faithfulness": -3},
                    ),
                    option(
                        "Management estimates that an experienced new salesperson could increase next year's sales by $20,000",
                        "A forecasted benefit is not a completed monetary transaction that belongs in the accounting records.",
                        {"faithfulness": -3},
                    ),
                ],
                "explanation": "The monetary unit assumption limits accounting records to transactions that can be expressed in money.",
            },
            {
                "id": "assumption-order",
                "concept": "Monetary unit assumption",
                "prompt": "Gem City Goods merely orders $4,000 of inventory; nothing has been delivered yet. Should the order itself be recorded as a completed purchase?",
                "options": [
                    option(
                        "No. An order alone is not yet a completed monetary transaction",
                        "Correct. No goods have been received and no completed purchase has occurred.",
                        {"faithfulness": 7, "confidence": 2},
                        correct=True,
                    ),
                    option(
                        "Yes. Record inventory and accounts payable when the purchasing manager approves the order",
                        "Internal approval and a purchase order do not mean the inventory has been received or a payable has been created.",
                        {"faithfulness": -5},
                    ),
                    option(
                        "Yes. Record a prepaid inventory asset because the price and supplier are known",
                        "Knowing the price and supplier does not create a prepaid asset when no payment has been made and no goods have been received.",
                        {"faithfulness": -6, "confidence": -2},
                    ),
                ],
                "explanation": "A dollar amount on an order does not by itself make the order a completed recordable purchase.",
            },
            {
                "id": "assumption-periodicity",
                "concept": "Periodicity assumption",
                "prompt": "Why can Gem City Goods prepare monthly, quarterly, and annual financial statements even though the business continues operating?",
                "options": [
                    option(
                        "The periodicity assumption allows the life of the business to be divided into artificial reporting periods",
                        "Correct. Useful reports can cover defined periods even though the business continues.",
                        {"timeliness": 8, "comparability": 3},
                        correct=True,
                    ),
                    option(
                        "The monetary unit assumption assigns each transaction to whichever reporting period management prefers",
                        "The monetary unit assumption concerns measurement in money; it does not establish reporting periods or permit arbitrary cutoffs.",
                        {"timeliness": -4},
                    ),
                    option(
                        "The full disclosure principle lets management change the reporting period whenever results would look more favorable",
                        "Full disclosure does not permit opportunistic reporting-period changes; periodicity allows useful reports for defined periods.",
                        {"timeliness": -5, "usefulness": -2},
                    ),
                ],
                "explanation": "Periodicity makes timely monthly, quarterly, or annual reporting possible.",
            },
        ],
    },
    {
        "slug": "principles",
        "eyebrow": "Round 6 of 6 · Measurement and disclosure",
        "title": "Finish the filing",
        "scenario": (
            "One final review remains: choose the appropriate measurement idea and decide "
            "whether users need additional information in the notes."
        ),
        "goal": "Distinguish historical cost, fair value, and full disclosure.",
        "reflection_question": "How can historical cost and fair value tell users different things about the same asset?",
        "reflection_answer": (
            "Historical cost tells users what the company originally paid. Fair value, when required, "
            "focuses on a current market-based exit price. The two amounts answer different questions, "
            "which is why the measurement basis must be applied and explained appropriately."
        ),
        "questions": [
            {
                "id": "principle-cost",
                "concept": "Historical cost principle",
                "prompt": "A delivery van was purchased for $28,000. Under the historical cost principle, what amount establishes its original recorded cost?",
                "options": [
                    option(
                        "$28,000, the amount paid to acquire it",
                        "Correct. Historical cost begins with the asset's original acquisition cost.",
                        {"faithfulness": 7, "comparability": 2},
                        correct=True,
                    ),
                    option(
                        "$31,000, the van's estimated current selling price",
                        "A current selling price reflects a fair-value idea, not the van's original historical cost.",
                        {"faithfulness": -5},
                    ),
                    option(
                        "$12,000, the amount management expects to receive when the van is sold in five years",
                        "An expected future resale amount is not the original acquisition cost used by the historical cost principle.",
                        {"faithfulness": -5},
                    ),
                ],
                "explanation": "Historical cost records an asset based on the price paid when it was acquired.",
            },
            {
                "id": "principle-fair",
                "concept": "Fair value principle",
                "prompt": "When a reporting requirement calls for fair value, which amount is the focus?",
                "options": [
                    option(
                        "The current price that would be received to sell an asset or paid to settle a liability",
                        "Correct. Fair value focuses on a current market-based amount.",
                        {"usefulness": 7, "faithfulness": 2},
                        correct=True,
                    ),
                    option(
                        "The asset's original purchase price, even if market conditions have changed",
                        "Original purchase price is the focus of historical cost, not a current fair-value measurement.",
                        {"faithfulness": -4},
                    ),
                    option(
                        "The amount the company would charge a related party in a specially negotiated transaction",
                        "A special related-party price may not represent the market-based exit price used for fair value.",
                        {"faithfulness": -5, "confidence": -2},
                    ),
                ],
                "explanation": "Historical cost looks back to acquisition; fair value focuses on a current exit price when GAAP calls for it.",
            },
            {
                "id": "principle-disclosure",
                "concept": "Full disclosure principle",
                "prompt": "A significant event is not obvious from the statement totals but could change how users interpret them. What should the company do?",
                "options": [
                    option(
                        "Provide sufficient explanation in the financial statements or related notes",
                        "Correct. Full disclosure supplies details that could make a difference to users.",
                        {"usefulness": 6, "faithfulness": 5, "confidence": 2},
                        correct=True,
                    ),
                    option(
                        "Include it only in an internal management report because the financial statements already show the totals",
                        "Internal reporting does not replace disclosure to external users when the information could affect their decisions.",
                        {"faithfulness": -6, "usefulness": -4},
                    ),
                    option(
                        "Wait to disclose it until the event has a final dollar amount and no uncertainty remains",
                        "Uncertainty does not automatically eliminate disclosure; users may need information about a significant event before its final outcome is known.",
                        {"faithfulness": -5, "timeliness": -3},
                    ),
                ],
                "explanation": "Full disclosure means providing the details users need to understand circumstances and events that could affect decisions.",
            },
        ],
    },
]


ALL_QUESTIONS = [question for round_data in ROUNDS for question in round_data["questions"]]
