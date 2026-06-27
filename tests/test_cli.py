from jfa_talent_analysis.cli import main


def test_main_prints_version(capsys):
    main()

    captured = capsys.readouterr()
    assert "jfa-talent-analysis" in captured.out
