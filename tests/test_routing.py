from mf_chat.routing import Intent, classify_message, wants_indexed_fund_directory


def test_classify_advice() -> None:
    assert classify_message("What is the best fund for me?") == Intent.REFUSE_ADVICE
    assert classify_message("Should I buy this mutual fund?") == Intent.REFUSE_ADVICE
    assert (
        classify_message("which Mutual fund should i be investing in") == Intent.REFUSE_ADVICE
    )


def test_classify_personal() -> None:
    assert classify_message("What is my PAN linked account?") == Intent.REFUSE_PERSONAL


def test_classify_fact() -> None:
    assert classify_message("What is the expense ratio?") == Intent.FACT


def test_portfolio_turnover_is_fact_not_advice() -> None:
    assert classify_message("Portfolio turnover / AUM") == Intent.FACT


def test_wants_indexed_fund_directory() -> None:
    assert wants_indexed_fund_directory("Give me links of all the funds")
    assert wants_indexed_fund_directory("List all indexed schemes")
    assert wants_indexed_fund_directory("what all mutual funds can you answer about")
    assert wants_indexed_fund_directory("Which mutual funds can you help with?")
    assert not wants_indexed_fund_directory("What is the exit load?")
